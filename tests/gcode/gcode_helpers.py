"""T4a 시험 도우미: 손 G코드 경로, 기대값 표, 짧은 G코드 조각."""
from __future__ import annotations

import csv
import glob
import math
import os

import numpy as np

from cvlab.gcode import GCodeError, GCodeParams, build_reference, effective_width, parse_file
from cvlab.gcode.grid import index_of, value_at

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HAND = os.path.join(ROOT, "data", "gcode_samples", "hand")
SAMPLES = os.path.join(ROOT, "data", "gcode_samples")
CONFIG = os.path.join(ROOT, "config", "gcode.yaml")
P042 = GCodeParams(line_width_mm=0.42)

PRE = "G21\nG90\nM83\nG28\nG1 Z0.2 F600\nG1 X100 Y100 F3000\n"


def hand(key: str) -> str:
    hits = sorted(glob.glob(os.path.join(HAND, f"{key}_*.gcode")))
    assert hits, f"손 G코드 {key} 없음"
    return hits[0]


def expected_rows() -> list[dict]:
    with open(os.path.join(HAND, "기대값.csv"), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def ext(r):
    return r.extrusions()


_CACHE: dict = {}


def parsed(f):
    """P042로 파싱한 결과 (같은 파일은 한 번만, 시험 시간 줄임)."""
    if ("p", f) not in _CACHE:
        _CACHE[("p", f)] = parse_file(f, P042)
    return _CACHE[("p", f)]


def ref_of(f):
    if ("r", f) not in _CACHE:
        _CACHE[("r", f)] = build_reference(parsed(f), params=P042)
    return _CACHE[("r", f)]


def _floats(s: str) -> list[float]:
    return [float(v) for v in s.split(";")]


def _close(a, b, tol) -> bool:
    return abs(float(a) - float(b)) <= float(tol) + 1e-12


def evaluate(row: dict):
    """기대값.csv 한 행을 실제 값과 견줘 (실제값, 통과) 반환."""
    key, item, exp, tol = row["파일"], row["항목"], row["기대값"], row["허용차"] or "0"
    f = hand(key)
    if item == "오류":
        try:
            parse_file(f, P042)
        except GCodeError as e:
            return str(e), True
        return "오류 없음", False
    if item.startswith("허용 목록"):
        p = GCodeParams(allow_commands=[{"name": "M999", "reason": "시험: 지어낸 명령"}])
        r = parse_file(f, p)
        return r.allowed, r.allowed.get("M999") == int(exp)
    r = parsed(f)
    e = ext(r)
    s = r.segments
    if item == "압출 선분 수":
        v = int(e["line_no"].nunique()); return v, v == int(exp)
    if item == "압출 길이 합_mm":
        v = float(e.length_mm.sum()); return v, _close(v, exp, tol)
    if item == "ΣΔE_mm":
        return r.sum_de_mm, _close(r.sum_de_mm, exp, tol)
    if item in ("층 Z_mm", "층 높이_mm"):
        col = "layer_z_mm" if item == "층 Z_mm" else "layer_h_mm"
        v = r.layers[col].tolist(); ex = _floats(exp)
        return v, len(v) == len(ex) and all(_close(a, b, tol) for a, b in zip(v, ex))
    if item == "층 수":
        v = len(r.layers)
        ok = v == int(exp) and r.layer_check["layers_z"] == v
        if r.layer_check["layers_comment"] is not None:
            ok = ok and r.layer_check["layers_comment"] == v
        return v, ok
    if item in ("층 시작 줄", "층 끝 줄", "층0 시작 줄"):
        col = "gcode_line_end" if item == "층 끝 줄" else "gcode_line_start"
        v = r.layers[col].tolist()
        if item == "층0 시작 줄":
            return v[0], v[0] == int(exp)
        return v, v == [int(x) for x in exp.split(";")]
    if item.endswith(" 수") and item.split()[0] in ("retract", "unretract", "wipe"):
        v = int((s.kind == item.split()[0]).sum()); return v, v == int(exp)
    if item == "PRIME 선분 수":
        v = int((s.type == "PRIME").sum()); return v, v == int(exp) and (s[s.type == "PRIME"].layer_idx == -1).all()
    if item == "선분 좌표 = H01":
        a = ext(parsed(hand("H01")))[["x0_mm", "y0_mm", "x1_mm", "y1_mm"]].to_numpy()
        b = e[["x0_mm", "y0_mm", "x1_mm", "y1_mm"]].to_numpy()
        return b.tolist(), a.shape == b.shape and np.allclose(a, b, atol=1e-9)
    if item.startswith("첫 압출 "):
        col = item.split()[-1]
        v = float(e.iloc[0][col]); return v, _close(v, exp, tol)
    if item.startswith("원호 ") and "끝점" in item:
        n = int(item.split()[1])
        lines = sorted(e["line_no"].unique())
        last = e[e.line_no == lines[n - 1]].iloc[-1]
        target = {1: (100.0, 110.0), 2: (110.0, 120.0)}[n]
        v = math.hypot(last.x1_mm - target[0], last.y1_mm - target[1]); return v, v <= float(tol) + 1e-12
    if item == "두 원호 길이 차_mm":
        g = e.groupby("line_no").length_mm.sum().to_numpy()
        v = abs(g[0] - g[1]); return v, v <= float(tol)
    if item == "최대 현_mm":
        v = float(e[e.arc].length_mm.max()); return v, v <= float(exp) + 1e-12
    if item == "체크섬 불량":
        return r.n_checksum_bad, r.n_checksum_bad == int(exp)
    if item == "층0 종류":
        v = r.layers.types.iloc[0]; return v, v == exp
    if item == "슬라이서":
        v = r.header["slicer_name"]; return v, v == exp
    if item == "방언":
        v = r.header["gcode_flavor"]; return v, v == exp
    if item == "선언 층 수":
        v = r.header["layers_declared"]; return v, v == int(exp)
    if item == "필라멘트 차_%":
        v = r.filament_diff_pct; return v, v is not None and abs(v) <= float(tol)
    if item == "주석 Z 최대 차_mm":
        v = r.layer_check["z_max_diff_mm"]; return v, v is not None and v <= float(tol)
    if item == "모르는 명령":
        k, n = exp.split("=")
        return r.unknown, r.unknown == {k: int(n)}
    if item == "원호 travel 선분 있음":
        v = int(((s.kind == "travel") & s.arc).sum()); return v, (v > 0) == bool(int(exp))
    if item.startswith("격자 x0_mm"):
        ref = ref_of(f)
        v = ref.grid["x0_mm"]; return v, _close(v, exp, tol)
    if item.startswith("층") and "높이 (" in item:
        n = int(item[1]); x, y = map(float, item.split("(")[1].split(")")[0].split(","))
        ref = ref_of(f)
        iy, ix = index_of(ref.grid, x, y)
        v = float(ref.height_at_layer(n)[iy, ix]); return v, _close(v, exp, tol)
    if item.startswith("층0 안쪽 빈칸"):
        ref = ref_of(f)
        h = ref.height_at_layer(0)
        iy0, ix0 = index_of(ref.grid, 100.3, 100.3)
        iy1, ix1 = index_of(ref.grid, 109.7, 109.7)
        v = int(np.isnan(h[iy0:iy1 + 1, ix0:ix1 + 1]).sum()); return v, v == int(exp)
    if item == "w_eff_mm":
        w = effective_width(r.segments, 1.75, 0.5).dropna()
        v = float(w.median()); return v, len(w) > 0 and float((w - float(exp)).abs().max()) <= float(tol)
    if item.startswith("층0 발자국 x 범위"):
        ref = ref_of(f)
        cols = np.flatnonzero(ref.footprint(0).any(axis=0))
        xs = ref.grid["x0_mm"] + cols * ref.grid["res_mm"]
        ex = _floats(exp)
        return (xs.min(), xs.max()), _close(xs.min(), ex[0], tol) and _close(xs.max(), ex[1], tol)
    if item.startswith("발자국 ("):
        x, y = map(float, item.split("(")[1].split(")")[0].split(","))
        ref = ref_of(f)
        v = int(value_at(ref.grid, ref.footprint(0), x, y, False)); return v, v == int(exp)
    raise KeyError(f"평가 방법이 없는 항목: {key} {item}")
