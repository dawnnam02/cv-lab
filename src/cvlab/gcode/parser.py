"""G1 · G코드 모달 상태 파서.

한 줄씩 읽으며 위치·모드·단위·경로 종류를 기억하고, 노즐 움직임을 선분 표로 만든다.
원호는 현 길이 arc_seg_mm 이하의 직선으로 펼친다.
모르는 명령은 세고, 압출 사이에 끼면 엄격 모드에서 멈춘다 (MF-GCD-04).
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .params import GCodeError, GCodeParams

# ---------------------------------------------------------------- 명령 목록 (코드 한 곳)
# 움직임: 위치나 E를 바꿈
MOTION = frozenset({"G0", "G1", "G2", "G3", "G28", "G92", "G10", "G11"})
# 상태: 뒤 줄의 해석을 바꿈
STATE = frozenset({"G90", "G91", "M82", "M83", "G20", "G21", "G17"})
# 움직임 없음: 온도·팬·진행률·가속·표시 등. 위치와 E를 바꾸지 않음
NOMOTION = frozenset({
    "G4", "M18", "M84", "M73", "M104", "M105", "M106", "M107", "M109", "M117", "M118",
    "M140", "M141", "M190", "M191", "M201", "M203", "M204", "M205", "M207", "M220", "M221",
    "M300", "M400", "M420", "M115", "M572", "M862.1", "M862.3", "M900", "M403",
    # Klipper 확장 (움직임 없음)
    "SET_VELOCITY_LIMIT", "SET_PRESSURE_ADVANCE", "SET_PRINT_STATS_INFO",
    "EXCLUDE_OBJECT_DEFINE", "EXCLUDE_OBJECT_START", "EXCLUDE_OBJECT_END",
    "SET_FAN_SPEED", "SET_HEATER_TEMPERATURE", "TEMPERATURE_WAIT", "RESPOND", "SET_RETRACTION",
})
# 시작·끝 구간에서만 통과 (머리를 움직이지만 압출 사이가 아니면 정답과 무관)
EDGE_ONLY = frozenset({"START_PRINT", "PRINT_START", "END_PRINT", "PRINT_END", "G80", "G29", "M702"})
# T<n> (공구 선택)도 EDGE_ONLY로 다룸
TEXT_COMMANDS = frozenset({"M117", "M118"})

# 슬라이서 경로 종류 이름 → 표준 이름 (G1 TYPE_ALIASES 방식, Orca 이름 더함)
TYPE_ALIASES = {
    # Cura
    "WALL-OUTER": "WALL-OUTER", "WALL-INNER": "WALL-INNER", "SKIN": "SKIN", "FILL": "FILL",
    "SKIRT": "SKIRT", "SUPPORT": "SUPPORT", "SUPPORT-INTERFACE": "SUPPORT", "SUPPORT-INFILL": "SUPPORT",
    "SUPPORT-ROOF": "SUPPORT", "SUPPORT-BOTTOM": "SUPPORT", "PRIME-TOWER": "PRIME-TOWER",
    # PrusaSlicer · SuperSlicer · OrcaSlicer · Bambu
    "EXTERNAL PERIMETER": "WALL-OUTER", "OUTER WALL": "WALL-OUTER", "OVERHANG PERIMETER": "WALL-OUTER",
    "OVERHANG WALL": "WALL-OUTER", "PERIMETER": "WALL-INNER", "INNER WALL": "WALL-INNER",
    "SOLID INFILL": "SKIN", "TOP SOLID INFILL": "SKIN", "BOTTOM SURFACE": "SKIN", "TOP SURFACE": "SKIN",
    "INTERNAL SOLID INFILL": "SKIN", "BRIDGE INFILL": "SKIN", "BRIDGE": "SKIN", "INTERNAL BRIDGE": "SKIN",
    "INTERNAL INFILL": "FILL", "SPARSE INFILL": "FILL", "GAP FILL": "FILL", "GAP INFILL": "FILL",
    "SKIRT/BRIM": "SKIRT", "BRIM": "BRIM", "SUPPORT MATERIAL": "SUPPORT",
    "SUPPORT MATERIAL INTERFACE": "SUPPORT", "SUPPORT INTERFACE": "SUPPORT", "SUPPORT TRANSITION": "SUPPORT",
    "WIPE TOWER": "PRIME-TOWER", "PRIME TOWER": "PRIME-TOWER",
    "IRONING": "IRONING", "CUSTOM": "CUSTOM",
}
STANDARD_TYPES = ("FILL", "SKIN", "WALL-INNER", "WALL-OUTER", "SKIRT", "BRIM", "SUPPORT",
                  "PRIME-TOWER", "IRONING", "CUSTOM", "UNTYPED", "PRIME")

SEG_COLUMNS = ["line_no", "layer_idx", "type", "kind", "arc", "x0_mm", "y0_mm", "z0_mm",
               "x1_mm", "y1_mm", "z1_mm", "de_mm", "length_mm", "feed_mm_s"]
KINDS = ("extrude", "travel", "retract", "unretract", "wipe", "zmove")

_EPS_XY = 1e-9
_EPS_E = 1e-9
_CMD_RE = re.compile(r"^([GMT])0*(\d+)(?:\.(\d+))?")
_WORD_RE = re.compile(r"([A-Z])([-+]?(?:\d+\.?\d*|\.\d+))?")
_PAREN_RE = re.compile(r"\([^)]*\)")
_N_RE = re.compile(r"^\s*N\d+\s*", re.I)
_LAYER_CURA_RE = re.compile(r"^LAYER:\s*(-?\d+)\s*$")
_Z_RE = re.compile(r"^(?:Z|Z_HEIGHT):\s*([-+]?\d*\.?\d+)\s*$")
_TYPE_RE = re.compile(r"^(?:TYPE|FEATURE):\s*(.+?)\s*$")


def normalize_type(raw: str) -> str:
    key = raw.strip().upper()
    return TYPE_ALIASES.get(key, key)


def checksum_ok(line: str) -> bool | None:
    """`N12 G1 X1*85` 꼴 체크섬. '*' 없으면 None. '*' 앞 모든 글자 XOR."""
    if "*" not in line:
        return None
    body, _, cs = line.rpartition("*")
    try:
        expected = int(cs.strip())
    except ValueError:
        return False
    calc = 0
    for ch in body:
        calc ^= ord(ch)
    return calc == expected


def command_class(cmd: str) -> str:
    if cmd in MOTION:
        return "motion"
    if cmd in STATE:
        return "state"
    if cmd in NOMOTION:
        return "nomotion"
    if cmd in EDGE_ONLY or re.fullmatch(r"T\d+", cmd):
        return "edge"
    return "unknown"


@dataclass
class ParseResult:
    segments: pd.DataFrame
    layers: pd.DataFrame
    header: dict
    unknown: dict
    warnings: list
    n_lines: int
    n_checksum_bad: int
    allowed: dict = field(default_factory=dict)
    markers: list = field(default_factory=list)
    layer_check: dict = field(default_factory=dict)
    sum_de_mm: float = 0.0
    filament_diff_pct: float | None = None
    params: GCodeParams | None = None

    def extrusions(self) -> pd.DataFrame:
        s = self.segments
        return s[(s.kind == "extrude") & (s.layer_idx >= 0)]

    def summary(self) -> dict:
        lc = self.layer_check
        return {
            "lines": self.n_lines,
            "unknown": int(sum(self.unknown.values())),
            "unknown_names": dict(self.unknown),
            "allowed": dict(self.allowed),
            "checksum_bad": self.n_checksum_bad,
            "layers_comment": lc.get("layers_comment"),
            "layers_z": lc.get("layers_z"),
            "layers_declared": self.header.get("layers_declared"),
            "layer_source_used": lc.get("source"),
            "z_max_diff_mm": lc.get("z_max_diff_mm"),
            "sum_de_mm": round(self.sum_de_mm, 6),
            "filament_declared_mm": self.header.get("filament_used_mm"),
            "filament_diff_pct": None if self.filament_diff_pct is None else round(self.filament_diff_pct, 4),
            "slicer": self.header.get("slicer_name"),
            "slicer_version": self.header.get("slicer_version"),
            "gcode_flavor": self.header.get("gcode_flavor"),
            "n_warnings": len(self.warnings),
            "gcode_sha256": self.header.get("gcode_sha256"),
        }


class _State:
    def __init__(self) -> None:
        self.x = self.y = self.z = math.nan
        self.e = 0.0
        self.abs_xyz = True
        self.abs_e = True
        self.unit = 1.0
        self.feed = math.nan
        self.type = "UNTYPED"
        self.marker = -1


def _parse_words(rest: str, line_no: int) -> dict:
    words: dict = {}
    for letter, val in _WORD_RE.findall(rest):
        if letter in ("G", "M") and val:
            raise GCodeError(f"줄 {line_no}: 한 줄에 명령이 둘 이상 ({letter}{val})")
        words[letter] = None if val in ("", None) else float(val)
    return words


def parse_text(text: str, params: GCodeParams | None = None, *, sha256: str | None = None) -> ParseResult:
    from .header import parse_header
    from .layers import assign_layers

    p = params or GCodeParams()
    allowed_names = p.allowed_names
    lines = text.splitlines()
    st = _State()
    rows: list = []
    warnings: list = []
    unknown: dict = {}
    allowed: dict = {}
    markers: list = []           # [line_no, z_comment or None, style]
    n_bad = 0
    first_extrude_seen = False
    pending: list = []           # 첫 압출 뒤 만난 위치 불명 명령 (line, cmd)
    arc_p_warned = False
    g9x_flip_warned = False
    unknown_pos_prime: list = []  # 첫 층 표시 앞, 위치를 모르는 압출 줄

    def e_relative() -> bool:
        if p.g9x_sets_e:
            return not st.abs_e
        return (not st.abs_e) or (not st.abs_xyz)  # Klipper식 [확인 필요]

    def add_row(line_no, kind, arc, x0, y0, z0, x1, y1, z1, de):
        nonlocal first_extrude_seen
        if kind == "extrude":
            if pending:
                msg = "; ".join(f"줄 {ln} {c}" for ln, c in pending)
                if p.strict_unknown:
                    raise GCodeError(f"줄 {line_no}: 위치를 바꿀 수 있는 명령 뒤에 압출 ({msg})")
                warnings.append(f"압출 사이 명령 무시 ({msg})")
                pending.clear()
            if not all(map(math.isfinite, (x0, y0, z0, x1, y1, z1))):
                if st.marker >= 0:
                    raise GCodeError(f"줄 {line_no}: 위치를 모르는 채로 압출 (G28 뒤 절대 이동 없음 등)")
                # 첫 층 표시 앞 (시작 퍼지선): 층 표시가 끝내 없으면 assign_layers에서 오류
                unknown_pos_prime.append(line_no)
            elif abs(z1 - z0) > p.layer_z_tol_mm:
                raise GCodeError(f"줄 {line_no}: 한 선분 안에서 Z가 바뀌는 압출 (나선·비평면)")
            first_extrude_seen = True
        length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2) \
            if all(map(math.isfinite, (x0, y0, z0, x1, y1, z1))) else math.nan
        rows.append((line_no, -1, st.type, kind, arc, x0, y0, z0, x1, y1, z1, de, length, st.feed, st.marker))

    def classify(dxy, dz, de):
        if not math.isfinite(dxy):
            dxy = 1.0 if (math.isnan(dxy)) else dxy
        if dxy > _EPS_XY:
            return "extrude" if de > _EPS_E else ("wipe" if de < -_EPS_E else "travel")
        if de < -_EPS_E:
            return "retract"
        if de > _EPS_E:
            return "unretract"
        if (math.isfinite(dz) and abs(dz) > _EPS_XY) or (math.isnan(dz)):
            return "zmove"
        return None

    for line_no, raw in enumerate(lines, start=1):
        code, _, comment = raw.partition(";")
        comment = comment.strip()
        if comment:
            cu = comment.upper()
            if cu in ("LAYER_CHANGE", "CHANGE_LAYER"):
                markers.append([line_no, None, cu])
                st.marker = len(markers) - 1
            else:
                m = _LAYER_CURA_RE.match(cu)
                if m:
                    markers.append([line_no, None, "LAYER:n"])
                    st.marker = len(markers) - 1
                else:
                    m = _Z_RE.match(cu)
                    if m and markers and markers[-1][1] is None and line_no - markers[-1][0] <= 5:
                        markers[-1][1] = float(m.group(1))
                    else:
                        m = _TYPE_RE.match(comment)
                        if m:
                            st.type = normalize_type(m.group(1))
                            if st.type not in STANDARD_TYPES:
                                w = f"모르는 경로 종류 이름 {st.type} (대문자 그대로 둠)"
                                if w not in warnings:
                                    warnings.append(w)
        code = _PAREN_RE.sub(" ", code)
        if not code.strip():
            continue
        ck = checksum_ok(code)
        if ck is False:
            n_bad += 1
            warnings.append(f"줄 {line_no}: 체크섬 틀림, 쓰지 않음")
            continue
        if ck is True:
            code = code.rpartition("*")[0]
        code = _N_RE.sub("", code).strip()
        if not code:
            continue
        up = code.upper()
        m = _CMD_RE.match(up)
        if m:
            cmd = f"{m.group(1)}{int(m.group(2))}" + (f".{m.group(3)}" if m.group(3) else "")
            rest = up[m.end():]
        else:
            cmd = up.split()[0]
            rest = ""
        cls = command_class(cmd)
        if cmd in allowed_names:
            allowed[cmd] = allowed.get(cmd, 0) + 1
            continue
        if cls in ("unknown", "edge"):
            if cls == "unknown":
                unknown[cmd] = unknown.get(cmd, 0) + 1
                is_macro = not re.fullmatch(r"[GMT]\d+(\.\d+)?", cmd)
                if not is_macro and p.strict_unknown:
                    raise GCodeError(f"줄 {line_no}: 모르는 명령 {cmd} (허용 목록에 이유와 함께 넣으면 통과)")
            if not first_extrude_seen:
                if cls == "unknown":
                    warnings.append(f"줄 {line_no}: 시작 구간의 모르는 명령 {cmd} 통과")
            else:
                pending.append((line_no, cmd))
            continue
        if cls == "nomotion" or cmd in TEXT_COMMANDS:
            continue
        if cmd == "G17":
            continue
        words = _parse_words(rest.replace(" ", "").replace("\t", ""), line_no)

        if cmd in ("G90", "G91"):
            st.abs_xyz = cmd == "G90"
            if p.g9x_sets_e:
                if st.abs_e != st.abs_xyz and not g9x_flip_warned:
                    warnings.append(f"줄 {line_no}: {cmd}가 E 모드도 바꿈 (g9x_sets_e=true, Marlin식)")
                    g9x_flip_warned = True
                st.abs_e = st.abs_xyz
            continue
        if cmd in ("M82", "M83"):
            st.abs_e = cmd == "M82"
            continue
        if cmd in ("G20", "G21"):
            st.unit = 25.4 if cmd == "G20" else 1.0
            continue
        if cmd == "G92":
            if not any(k in words for k in "XYZE"):
                st.x = st.y = st.z = 0.0
                st.e = 0.0
            for k in "XYZE":
                if k in words and words[k] is not None:
                    v = words[k] * st.unit
                    setattr(st, k.lower(), v)
            continue
        if cmd == "G28":
            axes = [k for k in "XYZ" if k in words]
            for k in axes or ["X", "Y", "Z"]:
                setattr(st, k.lower(), math.nan)
            continue
        if cmd in ("G10", "G11"):
            if words:
                raise GCodeError(f"줄 {line_no}: {cmd}에 매개변수가 있음 (펌웨어 리트랙트가 아닐 수 있음)")
            kind = "retract" if cmd == "G10" else "unretract"
            add_row(line_no, kind, False, st.x, st.y, st.z, st.x, st.y, st.z, 0.0)
            continue

        # ---- G0 · G1 · G2 · G3
        if "F" in words and words["F"] is not None:
            st.feed = words["F"] * st.unit / 60.0

        def target(k):
            cur = getattr(st, k.lower())
            if k not in words or words[k] is None:
                return cur
            v = words[k] * st.unit
            return v if st.abs_xyz else cur + v

        x1, y1, z1 = target("X"), target("Y"), target("Z")
        de = 0.0
        if "E" in words and words["E"] is not None:
            v = words["E"] * st.unit
            if e_relative():
                de = v
                st.e += v
            else:
                de = v - st.e
                st.e = v
        x0, y0, z0 = st.x, st.y, st.z

        if cmd in ("G0", "G1"):
            dxy = math.hypot(x1 - x0, y1 - y0) if all(map(math.isfinite, (x0, y0, x1, y1))) else (
                0.0 if ("X" not in words and "Y" not in words) else math.nan)
            dz = (z1 - z0) if (math.isfinite(z0) and math.isfinite(z1)) else (0.0 if "Z" not in words else math.nan)
            kind = classify(dxy, dz, de)
            if kind is not None:
                add_row(line_no, kind, False, x0, y0, z0, x1, y1, z1, de)
            st.x, st.y, st.z = x1, y1, z1
            continue

        # 원호
        if not all(map(math.isfinite, (x0, y0))):
            raise GCodeError(f"줄 {line_no}: 시작 위치를 모르는 원호")
        if not all(map(math.isfinite, (x1, y1))):
            raise GCodeError(f"줄 {line_no}: 끝 위치를 모르는 원호")
        cw = cmd == "G2"
        if "P" in words:
            if de > _EPS_E:
                raise GCodeError(f"줄 {line_no}: P (바퀴 수) 원호 압출은 지원하지 않음")
            if not arc_p_warned:
                warnings.append(f"줄 {line_no}: 압출 없는 원호의 P 무시 (한 바퀴로 펼침, 정답 경로와 무관)")
                arc_p_warned = True
        if "R" in words and words["R"] is not None and "I" not in words and "J" not in words:
            r_signed = words["R"] * st.unit
            r = abs(r_signed)
            d = math.hypot(x1 - x0, y1 - y0)
            if d < 1e-12:
                raise GCodeError(f"줄 {line_no}: R 원호의 시작점과 끝점이 같음")
            if d > 2 * r + 1e-6:
                raise GCodeError(f"줄 {line_no}: R이 현의 절반보다 작음")
            h = math.sqrt(max(r * r - d * d / 4.0, 0.0))
            mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            ux, uy = -(y1 - y0) / d, (x1 - x0) / d
            best = None
            for sgn in (1.0, -1.0):
                cx, cy = mx + sgn * h * ux, my + sgn * h * uy
                sw = _sweep(x0, y0, x1, y1, cx, cy, cw)
                ok = sw <= math.pi + 1e-9 if r_signed > 0 else sw >= math.pi - 1e-9
                if ok and best is None:
                    best = (cx, cy)
            cx, cy = best
        else:
            if "I" not in words and "J" not in words:
                raise GCodeError(f"줄 {line_no}: 원호에 I·J도 R도 없음")
            cx = x0 + (words.get("I") or 0.0) * st.unit
            cy = y0 + (words.get("J") or 0.0) * st.unit
        r0 = math.hypot(x0 - cx, y0 - cy)
        r1 = math.hypot(x1 - cx, y1 - cy)
        if abs(r0 - r1) > 0.05:
            raise GCodeError(f"줄 {line_no}: 원호 반지름 불일치 {abs(r0 - r1):.4f} mm")
        if abs(r0 - r1) > 0.005:
            warnings.append(f"줄 {line_no}: 원호 반지름 차 {abs(r0 - r1):.4f} mm")
        sweep = _sweep(x0, y0, x1, y1, cx, cy, cw)
        n = max(1, math.ceil(r0 * sweep / p.arc_seg_mm - 1e-9))
        a0 = math.atan2(y0 - cy, x0 - cx)
        sgn = -1.0 if cw else 1.0
        zz0 = z0
        px, py, pz = x0, y0, z0
        for k in range(1, n + 1):
            if k == n:
                qx, qy, qz = x1, y1, z1
            else:
                a = a0 + sgn * sweep * k / n
                qx, qy = cx + r0 * math.cos(a), cy + r0 * math.sin(a)
                qz = zz0 + (z1 - zz0) * k / n if (math.isfinite(zz0) and math.isfinite(z1)) else z1
            dek = de / n
            dz = (qz - pz) if (math.isfinite(qz) and math.isfinite(pz)) else 0.0
            kind = classify(math.hypot(qx - px, qy - py), dz, dek)
            if kind is not None:
                add_row(line_no, kind, True, px, py, pz, qx, qy, qz, dek)
            px, py, pz = qx, qy, qz
        st.x, st.y, st.z = x1, y1, z1

    for ln, c in pending:
        warnings.append(f"줄 {ln}: 끝 구간 명령 {c} 통과 (뒤에 압출 없음)")
    if unknown_pos_prime:
        if not markers:
            raise GCodeError(f"줄 {unknown_pos_prime[0]}: 위치를 모르는 채로 압출 (층 표시가 없어 시작 구간으로 볼 수 없음)")
        warnings.append(f"첫 층 표시 앞 위치 모르는 압출 {len(unknown_pos_prime)}개 (줄 {unknown_pos_prime[0]}…), PRIME으로 둠")

    df = pd.DataFrame(rows, columns=SEG_COLUMNS + ["_marker"])
    if df.empty:
        df = pd.DataFrame({c: pd.Series(dtype=float) for c in SEG_COLUMNS + ["_marker"]})
    df = df.astype({"line_no": "int64", "layer_idx": "int64", "arc": bool, "_marker": "int64"})
    header = parse_header(lines)
    if sha256 is not None:
        header["gcode_sha256"] = sha256
    else:
        header["gcode_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for k in ("slicer_name", "gcode_flavor", "layers_declared", "filament_used_mm", "nozzle_dia_mm",
              "line_width_mm", "layer_h_mm", "filament_d_mm"):
        if header.get(k) is None:
            warnings.append(f"머리말에 {k} 없음 (None)")
    if len(set(header.get("layers_declared_all", {}).values())) > 1:
        warnings.append(f"머리말 층 수 값이 서로 다름 {header['layers_declared_all']} → "
                        f"{header['layers_declared']} 씀 (total layers count > LAYER_COUNT > total layer number)")
    if n_bad:
        warnings.append(f"체크섬 틀린 줄 {n_bad}개")

    df, layers, check = assign_layers(df, markers, p, warnings)
    # ΣΔE (GC7) = 층 줄 범위 안 모든 ΔE의 합 (압출 + 리트랙트·되밀기·와이프 상쇄).
    # 시작 퍼지선 (PRIME)·끝 G코드 리트랙트는 층 밖이라 빠짐. 후보 4개에서 선언값과 0.01 % 안 (문서 §2).
    sum_de = float(df.loc[df["layer_idx"] >= 0, "de_mm"].sum()) if len(df) else 0.0
    declared = header.get("filament_used_mm")
    diff = None if not declared else (sum_de - declared) / declared * 100.0
    df = df[SEG_COLUMNS].reset_index(drop=True)
    return ParseResult(segments=df, layers=layers, header=header, unknown=unknown, warnings=warnings,
                       n_lines=len(lines), n_checksum_bad=n_bad, allowed=allowed, markers=markers,
                       layer_check=check, sum_de_mm=sum_de, filament_diff_pct=diff, params=p)


def _sweep(x0, y0, x1, y1, cx, cy, cw: bool) -> float:
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    sw = (a0 - a1) if cw else (a1 - a0)
    sw %= 2 * math.pi
    if sw < 1e-9 and math.hypot(x1 - x0, y1 - y0) < 1e-9:
        sw = 2 * math.pi  # 끝점 = 시작점이면 한 바퀴
    return sw


def parse_file(path, params: GCodeParams | None = None) -> ParseResult:
    with open(path, "rb") as fh:
        data = fh.read()
    sha = hashlib.sha256(data).hexdigest()
    text = data.decode("utf-8", errors="replace")
    r = parse_text(text, params, sha256=sha)
    r.header["gcode_file"] = str(path)
    return r
