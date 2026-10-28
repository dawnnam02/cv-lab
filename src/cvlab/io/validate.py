"""명세 검증기: 캠페인 폴더가 하드웨어 데이터 명세를 지켰는지 검사한다 (세부청사진 T6 SV6–SV8).

- 규칙은 `config/spec/rules_v1.0.csv` (또는 `rules.build_rules`)에서 온다. 상태가 `구현`인 규칙만 결과를 낸다.
- 폴더는 `DirFS` (디스크) 또는 `MemFS` (메모리, 자체 시험용)로 읽는다.
- `data/_truth` 아래는 열지 않는다 (경로 거부는 `scripts/validate_dataset.py`와 `check_path_allowed`).
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path, PurePosixPath

from cvlab.io.hashing import sha256_bytes, is_sha256_hex

# 결측 표시로 쓰면 안 되는 글자 (명세 §0.5). 소문자 none은 허용 값(pos.event 등)이라 넣지 않는다.
MISSING_MARKERS = {"NaN", "nan", "NAN", "null", "NULL", "None", "NA", "N/A"}
INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$|^[+-]?inf$")

NAME_RES = {
    "campaign": re.compile(r"^[VR]C-\d{4}-\d{2}-\d{2}-[A-Z]$"),
    "session": re.compile(r"^PS-\d{4}-\d{2}-\d{2}-[A-Z]$"),
    "specrep": re.compile(r"^S\d{2}_r\d{2}$"),
    # 명세 8절 (T1 2차): 한 층을 여러 줄로 재면 _pNN (= meta.scan_pass_idx, 0이면 안 붙임)
    "layer": re.compile(r"^L\d{3}(_p\d{2})?$|^post(_p\d{2})?$"),
    "frame": re.compile(r"^\d{6}\.png$"),
    "cal": re.compile(r"^CAL-\d{4}-\d{2}-\d{2}-[A-Z]$"),
    # 명세 8절 (T1 2차, T6 반영점 3): d1–d5 아래 하위 폴더 한 단계까지
    "calimg": re.compile(r"^d[1-5]/([a-z0-9_]+/)?[a-z0-9_]+\.png$"),
    # 명세 v1.0 (T1 3차): 숫자는 세션 안 순번, 3자리를 넘으면 4자리까지
    "ref": re.compile(r"^REF-[A-Z]{3}-\d{3,4}$"),
    "msa": re.compile(r"^MSA-\d{2}$"),
}
REF_ABBR = {"bed_bare": "BED", "background": "BKG", "dark": "DRK", "bed_marker": "MRK",
            "ref_tower": "TWR", "step_gauge": "STG", "feeler": "FLR", "daily_ref": "DAY", "static_repeat": "STA"}
# 움직이며 찍는 기준: 기준 폴더에 position_log.csv도 둠 (명세 4절)
MOVING_REF = {"bed_bare", "bed_marker", "ref_tower", "step_gauge", "feeler"}
# 판정 거부 X4 · X7 (D-21 채택 10-27, 기본 켬). 끌 수 있는 규칙은 이 둘뿐:
# --disable-rule 또는 config/default.yaml validate.disable_rules
D21_RULES = ("W-REF-11", "W-MET-56")
# 두 단 비 경고 W-REF-25 (명세 v1.1 4절)는 끌 수 있는 목록에 넣지 않음 (사용자 결정 대기 규칙이 아니고, T3 정상 캠페인 경고 0)
SWITCHABLE_OFF = set(D21_RULES)
# 두 단 비 경고 (명세 v1.1 4절): C1 ε × d ≤ 4 µm (T2 5.4절 a = 4 µm 행), σ = 기준물 스캔 잡음 1.5 µm (T2 [추정], 고정값)
TWO_STEP_LIMIT_UM = 4.0
TWO_STEP_SIGMA_UM = 1.5
TRUTH_MAP_RE = re.compile(r"^T-S\d{2}_(L\d{3}|post)\.npy$")
# 참값 temp_c 층 키 (명세 v1.1 부록 A): L + 층 3자리 또는 post, _pNN 없음
TEMP_KEY_RE = re.compile(r"^L\d{3}$|^post$")
GB_RE = re.compile(r"^GB-\d{2}(\.\d{1,3})?(\+\d{2}(\.\d{1,3})?)*$")
MF_RE = re.compile(r"^MF-[A-Z]{3}-\d{2}$")
LAYER_REFS = ("bed_marker", "ref_tower", "step_gauge")  # 층에 매인 기준 (명세 4절)


def gauge_sum(gid: str) -> float | None:
    """GB- ID의 공칭 높이 합 (+로 나눈 숫자를 소수까지 더함, GB-02+01.8+01.5 = 5.3). 형식이 아니면 None."""
    if not isinstance(gid, str) or not GB_RE.match(gid):
        return None
    return round(sum(float(p) for p in gid[3:].split("+")), 6)


class PathRefused(ValueError):
    """정보 차단: data/_truth 아래 경로."""


def check_path_allowed(path: str | Path) -> None:
    """경로 문자열에 `_truth` 부분이 있으면 열지 않고 거부한다."""
    parts = [p.lower() for p in re.split(r"[\\/]+", str(path)) if p]
    if "_truth" in parts:
        raise PathRefused(f"_truth 경로는 열지 않음: {path}")
    try:
        resolved = Path(path).resolve(strict=False)
        if "_truth" in [p.lower() for p in resolved.parts]:
            raise PathRefused(f"_truth 경로는 열지 않음: {path}")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 파일 시스템
# ---------------------------------------------------------------------------
class DirFS:
    """디스크 폴더. 파일마다 한 번만 읽는다 (Windows에서 파일 열기가 느림)."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._cache: dict[str, bytes] = {}

    def files(self) -> list[str]:
        out = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            d = Path(dirpath)
            rel = d.relative_to(self.root).as_posix()
            pre = "" if rel == "." else rel + "/"
            for fn in filenames:
                out.append(pre + fn)
            if not dirnames and not filenames and pre:
                out.append(pre)
        return sorted(out)

    def read(self, rel: str) -> bytes:
        if rel not in self._cache:
            self._cache[rel] = (self.root / rel).read_bytes()
        return self._cache[rel]


class MemFS:
    def __init__(self, files: dict[str, bytes]):
        self.data = files

    def files(self) -> list[str]:
        return sorted(self.data)

    def read(self, rel: str) -> bytes:
        return self.data[rel]


@dataclass
class Finding:
    rule_id: str
    severity: str
    file: str
    row: int | None
    field: str
    value: str
    message: str


# ---------------------------------------------------------------------------
# 값 읽기
# ---------------------------------------------------------------------------
_BAD = object()


def parse_csv_value(s: str, dtype: str):
    """CSV 문자열 → 값. '' → None, 자료형 위반 → _BAD."""
    if s == "":
        return None
    if dtype in ("int", "int64"):
        return int(s) if INT_RE.match(s) else _BAD
    if dtype == "float":
        if not FLOAT_RE.match(s):
            return _BAD
        v = float(s)
        return _BAD if math.isnan(v) else v
    if dtype == "bool":
        return {"true": True, "false": False}.get(s, _BAD)
    if dtype == "str":
        return s
    return _BAD


def parse_json_value(v, dtype: str):
    if v is None:
        return None
    if dtype in ("int", "int64"):
        return v if isinstance(v, int) and not isinstance(v, bool) else _BAD
    if dtype == "float":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return _BAD
        return _BAD if isinstance(v, float) and math.isnan(v) else float(v)
    if dtype == "bool":
        return v if isinstance(v, bool) else _BAD
    if dtype == "str":
        return v if isinstance(v, str) else _BAD
    if dtype == "list":
        return v if isinstance(v, list) else _BAD
    if dtype == "dict":
        return v if isinstance(v, dict) else _BAD
    return _BAD


def is_missing(raw) -> bool:
    return raw is None or (isinstance(raw, str) and raw == "")


def _iso(s):
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def _numval(s: str):
    """스키마의 범위 끝값 문자열 → 수 (정수 표기면 int: 2^63 같은 큰 수를 정확히 비교)."""
    return int(s) if INT_RE.match(s) else float(s)


def _cmp(v: float, op: str, bound: float, lower: bool) -> bool:
    if op == "=":
        return abs(v - bound) <= 1e-12 * max(1.0, abs(bound))
    if lower:
        return v >= bound if op == "≤" else v > bound
    return v <= bound if op == "≤" else v < bound


# ---------------------------------------------------------------------------
# 조건부 필드의 조건 (rules.CONDITIONS와 같은 키). 참·거짓·None (모름)
# ---------------------------------------------------------------------------
def _m(ctx, k):
    meta = ctx.get("meta") or {}
    return meta.get(k)


def _r(ctx, k):
    return ctx["row"].get(k)


def _any_raw(ctx, k):
    return any(not is_missing(r.get(k, "")) for r in ctx.get("raw_rows", []))


COND_FUNCS = {
    "frame.file": lambda c: None if _m(c, "raw_saved") is None else _m(c, "raw_saved") is True,
    "frame.sha256": lambda c: not is_missing(c["raw"].get("file", "")),
    "frame.t_cam_ns": lambda c: True if _any_raw(c, "t_cam_ns") else None,
    "frame.cam_seq": lambda c: True if _any_raw(c, "cam_seq") else None,
    "frame.trig_pulse_idx": lambda c: None if _r(c, "trigger_mode") is None or _r(c, "laser_on") is None
    else (_r(c, "trigger_mode") == "hw" and _r(c, "laser_on") is True),
    "frame.gate_on": lambda c: None if _r(c, "trigger_mode") is None else _r(c, "trigger_mode") == "gate",
    "pos.mesh_dz_mm": lambda c: None if _m(c, "mesh_enabled") is None else _m(c, "mesh_enabled") is True,
    "pos.clock_offset_ns": lambda c: None if _r(c, "clock") is None else _r(c, "clock") == "mcu",
    "cal.target_rows": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "charuco",
    "cal.target_cols": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "charuco",
    "cal.target_square_mm": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "charuco",
    "cal.target_marker_mm": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "charuco",
    "cal.target_dict": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "charuco",
    "cal.target_flatness_um": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") in ("charuco", "flat_plate"),
    "cal.image_file": lambda c: None if _r(c, "record_type") is None else _r(c, "record_type") == "image",
    "cal.exposure_us": lambda c: not is_missing(c["raw"].get("image_file", "")),
    "cal.cmd_z_mm": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "D2",
    "cal.cmd_move_mm": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "D3",
    "cal.feature_id": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "D4",
    "cal.feature_x_mm": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "D4",
    "cal.feature_y_mm": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "D4",
    "cal.nozzle_touch_z_mm": lambda c: None if _r(c, "record_type") is None else _r(c, "record_type") == "nozzle_touch",
    "cal.gauge_block_id": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") in ("step_gauge", "filler_gauge"),
    "cal.gauge_block_height_mm": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "step_gauge",
    "cal.gauge_block_u_um": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "step_gauge",
    "cal.material_offset_um": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "material_sample",
    "cal.material_offset_u_um": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "material_sample",
    "cal.material": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "material_sample",
    "cal.color": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "material_sample",
    "cal.gauge_nominal_mm": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "filler_gauge",
    "cal.gauge_measured_mm": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "filler_gauge",
    "cal.gauge_u_um": lambda c: None if _r(c, "target_type") is None else _r(c, "target_type") == "filler_gauge",
    "cal.reproj_rms_px": lambda c: None if _r(c, "kind") is None else (c["file"] == "cal_results.csv" and _r(c, "kind") == "D1"),
    "cal.plane_rms_um": lambda c: None if _r(c, "kind") is None else (c["file"] == "cal_results.csv" and _r(c, "kind") == "D2"),
    "ref.scan_id": lambda c: None if _r(c, "kind") is None else _r(c, "kind") in ("bed_marker", "ref_tower", "step_gauge"),
    # v1.0: 층 기준 3종 + 출력 전 기준 (bed_bare · feeler = -1)은 필수, 그 밖은 선택 (None = 검사 안 함)
    "ref.layer_idx": lambda c: True if _r(c, "kind") in LAYER_REFS + ("bed_bare", "feeler") else None,
    "ref.scan_pass_idx": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "bed_bare",
    "ref.calibration_id": lambda c: True if _r(c, "kind") in MOVING_REF else None,
    "ref.gauge_block_id": lambda c: None if _r(c, "kind") is None else _r(c, "kind") in ("step_gauge", "feeler"),
    "ref.gauge_height_mm": lambda c: None if _r(c, "kind") is None else _r(c, "kind") in ("step_gauge", "feeler"),
    "ref.gauge_temp_c": lambda c: None if _r(c, "kind") in (None, "feeler") else _r(c, "kind") == "step_gauge",
    "ref.marker_id": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "bed_marker",
    "ref.marker_x_mm": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "bed_marker",
    "ref.marker_y_mm": lambda c: None if _r(c, "kind") is None else _r(c, "kind") == "bed_marker",
    "ref.line_peak_pct": lambda c: None if _r(c, "kind") is None else _r(c, "kind") in ("daily_ref", "static_repeat", "bed_marker", "ref_tower", "step_gauge"),
    "meta.layer_time_s": lambda c: None if _r(c, "timing") is None else _r(c, "timing") == "layer",
    "meta.step_edge_angle_deg": lambda c: None if _r(c, "specimen_role") is None else _r(c, "specimen_role") == "aux_step",
    "meta.camera_temp_c": lambda c: True if _r(c, "source") == "virtual" else None,
    "meta.bed_mesh_file": lambda c: None if _r(c, "mesh_enabled") is None else _r(c, "mesh_enabled") is True,
    "meta.paired_scan_id": lambda c: None if _r(c, "thermal_state") is None else _r(c, "thermal_state") == "cooled",
    "meta.cool_wait_s": lambda c: None if _r(c, "thermal_state") is None else _r(c, "thermal_state") == "cooled",
    "meta.sim_version": lambda c: None if _r(c, "source") is None else _r(c, "source") == "virtual",
    # v1.0: 블라인드면 null (값은 truth.scan_seeds)
    "meta.sim_seed": lambda c: None if _r(c, "source") is None else (
        False if _r(c, "source") != "virtual" or _r(c, "blind") is True else (None if _r(c, "blind") is None else True)),
    # frames_index.csv를 읽은 뒤 _scan_cross에서 REQ · CROSS-EMPTY를 냄
    "meta.trigger_period_s": lambda c: None,
    "rep.scan_id": lambda c: c["file"] == "design_executed.csv",
    # v1.0: 같은 캠페인 meta.blind = true면 빈 칸 (blind를 모르면 가상 여부만 봄)
    "rep.noise_seed": lambda c: False if c.get("blind") is True else c.get("virtual"),
    "rep.truth_id": lambda c: c.get("virtual"),
}


# ---------------------------------------------------------------------------
# 검증기
# ---------------------------------------------------------------------------
class Validator:
    def __init__(self, fields: list[dict], rules: list[dict], file_cols: dict[str, list[str]],
                 enabled_groups: set[str] | None = None, enabled_rules: set[str] | None = None,
                 repo_root: str | Path | None = None, repo_exists=None, disabled_rules: set[str] | None = None):
        """enabled_groups: 명세에서 제외한 묶음을 켬 (지금은 없음, blt 필드표가 명세에서 빠짐).
        enabled_rules: 상태 '비활성' 손 규칙을 ID로 켬 (v1.0에서 비활성 규칙 0개).
        disabled_rules: 기본 켬 규칙 중 끌 수 있는 것 (SWITCHABLE_OFF = D-21 X4 · X7)을 ID로 끔. 그 밖 ID는 KeyError.
        repo_root · repo_exists: 저장소 뿌리 기준 경로 (meta.gcode_file 등) 검사. 둘 다 없으면 FILE-17 · 18을 건너뜀
        (CLI는 늘 뿌리를 정해 넘김: 기본은 검증기 저장소 cv-lab, 팀장검증 5차 S-5).
        """
        self.fields = {f["field"]: f for f in fields}
        self.file_cols = file_cols
        self.enabled = set(enabled_groups or ())
        self.enabled_rules = set(enabled_rules or ())
        self.disabled_rules = set(disabled_rules or ())
        self.rules = {r["rule_id"]: r for r in rules}
        unknown = self.enabled_rules - set(self.rules)
        if unknown:
            raise KeyError(f"규칙표에 없는 규칙 ID를 켜려 함: {sorted(unknown)}")
        bad_off = self.disabled_rules - SWITCHABLE_OFF
        if bad_off:
            raise KeyError(f"끌 수 없는 규칙 ID (끌 수 있는 것: {sorted(SWITCHABLE_OFF)}): {sorted(bad_off)}")
        if repo_exists is None and repo_root is not None:
            root = Path(repo_root)
            repo_exists = lambda rel: (root / rel).is_file()  # noqa: E731
        self.repo_exists = repo_exists
        self.active: set[str] = set()
        for r in rules:
            auto = r["kind"] in ("REQ", "DTYPE", "REGEX", "ENUM", "RANGE") or r["rule_id"].startswith("CROSS-EMPTY.")
            grp = r["fields"].split(".", 1)[0] if auto else ""
            if r["status"] == "구현" \
                    or (r["status"] == "비활성" and auto and grp in self.enabled and r["condition"] != "(조건 미구현)") \
                    or (r["status"] == "비활성" and r["rule_id"] in self.enabled_rules):
                self.active.add(r["rule_id"])
        self.active -= self.disabled_rules
        self.truth_ctx: dict | None = None
        self._vrules: dict[str, list] = {}
        self._png_cache: dict[str, tuple] = {}
        self._csv_cache: dict[tuple, tuple] = {}

    # -- 결과 ---------------------------------------------------------------
    def emit(self, rid, file="", row=None, field="", value="", message=None):
        if rid not in self.rules:
            raise KeyError(f"규칙표에 없는 규칙 ID: {rid}")
        if rid not in self.active:
            return
        r = self.rules[rid]
        v = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
        self.out.append(Finding(rid, r["severity"], file, row, field, v[:200], message or r["message"]))

    # -- 진입점 -------------------------------------------------------------
    def run(self, fs, campaign_name: str) -> list[Finding]:
        self.out: list[Finding] = []
        self.fs = fs
        self.campaign = campaign_name
        m = NAME_RES["campaign"].match(campaign_name)
        if not m:
            self.emit("FILE-02", campaign_name, message="캠페인 폴더 이름이 정규식과 맞지 않음")
        self.virtual = (campaign_name[0] == "V") if m else None
        self.paths = fs.files()
        self.all_scans: list[dict] = []   # 모든 세션의 스캔 (meta 있는 것)
        self.all_ref_rows: list[dict] = []  # 모든 세션의 기준 행
        self.blind = None
        self._walk()
        self._calibration()
        self._sessions()
        self._campaign_cross()
        # MSA는 캠페인 blind를 안 뒤에 읽음 (rep.noise_seed 조건, v1.0)
        self._msa()
        # v1.1: temp_c 키 집합 = step_gauge 기준이 있는 층 (L + ref.layer_idx 3자리), post 스캔과 짝인 두 단은 post
        timing = {x["meta"].get("scan_id"): x["meta"].get("timing") for x in self.all_scans if x["meta"].get("scan_id")}
        glayers = set()
        for r in self.all_ref_rows:
            if r["kind"] != "step_gauge":
                continue
            if r["scan_id"] is not None and timing.get(r["scan_id"]) == "post":
                glayers.add("post")
            elif isinstance(r["layer_idx"], int) and r["layer_idx"] >= 0:
                glayers.add(f"L{r['layer_idx']:03d}")
        self.truth_ctx = {
            "gauge_layers": sorted(glayers),
            "has_step_gauge": any(r["kind"] == "step_gauge" for r in self.all_ref_rows),
            "gauge_ids": sorted({r["gauge_block_id"] for r in self.all_ref_rows if r["kind"] == "step_gauge"
                                 and isinstance(r["gauge_block_id"], str) and r["gauge_block_id"].startswith("GB-")
                                 and r["gauge_block_id"] != "GB-00"}),
            "blind": self.blind,
            "scan_ids": sorted({x["meta"].get("scan_id") for x in self.all_scans if x["meta"].get("scan_id")}),
            "factors": sorted({f for x in self.all_scans for f in (x["meta"].get("injected_factors") or [])
                               if isinstance(f, str)}),
        }
        return self.out

    def _campaign_cross(self):
        """캠페인 전체를 보는 규칙 (v1.0): 블라인드 값 일치, 재료 조각 ↔ 스캔 재료·색."""
        metas = [x["meta"] for x in self.all_scans]
        blinds = {m.get("blind") for m in metas if isinstance(m.get("blind"), bool)}
        if len(blinds) > 1:
            self.emit("X-MET-67", "sessions", None, "meta.blind", "true,false")
        self.blind = next(iter(blinds)) if len(blinds) == 1 else None
        # X-CAL-26: material_sample 행의 재료·색 = 그 cal_id를 쓰는 스캔의 재료·색
        for cid, rows in sorted(self.cal_rows.items()):
            used = {(m.get("material"), m.get("color")) for m in metas if m.get("calibration_id") == cid}
            for i, r in enumerate(rows):
                if r.get("target_type") != "material_sample" or r.get("material") is None or r.get("color") is None:
                    continue
                if used and (r["material"], r["color"]) not in used:
                    self.emit("X-CAL-26", f"calibration/{cid}/cal_manifest.csv", None, "cal.material",
                              f"{r['material']},{r['color']} ≠ 스캔 {sorted(used, key=str)}")

    def check_truth(self, obj: dict, path: str = "truth.json", ctx: dict | None = None) -> list[Finding]:
        """참값 객체 (부록 A truth) 하나를 본다. data/raw 검사와 따로 부른다 (T3 시뮬레이터가 참값을 쓴 뒤).

        파일을 열지 않는다: 호출하는 쪽이 이미 읽은 사전을 넘긴다 (정보 차단, 청사진 §5.2).
        ctx: 캠페인 쪽 사실 {has_step_gauge, gauge_ids, blind, scan_ids, factors}. 없으면 같은 검증기의 마지막 run() 값
        (`truth_ctx`). 둘 다 없으면 필수 · 키 집합 규칙 (X-TRU-02 · 03 · 04의 캠페인 대조)은 건너뛰고 값 모양만 봄.
        """
        self.out = []
        ctx = ctx if ctx is not None else self.truth_ctx
        recs = obj if isinstance(obj, list) else [obj]
        for i, t in enumerate(recs):
            row = i if isinstance(obj, list) else None
            j, p = t.get("judgement"), t.get("pass_pct")
            if j in ("pass", "fail") and isinstance(p, (int, float)) and not isinstance(p, bool):
                if (j == "pass") != (p >= 95):
                    self.emit("X-TRU-01", path, row, "truth.judgement", f"{j}, {p}")
            self._truth_v10(t, path, row, ctx)
        return self.out

    def _truth_v10(self, t: dict, path: str, row, ctx: dict | None):
        """v1.0 새 참값 필드 (부록 A): 계단 기준물 · 블라인드 · 요인 · 필러게이지."""
        def num(v):
            return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

        # X-TRU-02 계단 기준물
        hs, tp = t.get("gauge_block_heights_mm"), t.get("gauge_temp_params")
        if ctx is not None:
            if ctx.get("has_step_gauge") and (not isinstance(hs, dict) or not isinstance(tp, dict)):
                self.emit("X-TRU-02", path, row, "truth.gauge_block_heights_mm", "없음", "step_gauge 기준이 있는데 참값이 없음")
            if not ctx.get("has_step_gauge") and (hs is not None or tp is not None):
                self.emit("X-TRU-02", path, row, "truth.gauge_block_heights_mm", "값 있음", "step_gauge 기준이 없는데 null이 아님")
        if isinstance(hs, dict):
            for k, v in hs.items():
                s = gauge_sum(k)
                if s is None or k == "GB-00" or not num(v) or abs(v - s) > 0.02 + 1e-12:
                    self.emit("X-TRU-02", path, row, "truth.gauge_block_heights_mm", f"{k}: {v}")
            if ctx is not None:
                miss = [g for g in ctx.get("gauge_ids", []) if g not in hs]
                if miss:
                    self.emit("X-TRU-02", path, row, "truth.gauge_block_heights_mm", miss, "기준이 쓴 블록 ID가 빠짐")
        if isinstance(tp, dict) and "cte_um_per_m_c" not in tp:
            self.emit("X-TRU-02", path, row, "truth.gauge_temp_params", list(tp), "키 cte_um_per_m_c가 없음")
        # v1.1: 열 모델을 켜면 (cte ≠ 0) temp_c 필수. 키 = L### · post (_pNN 없음), 키 집합 = step_gauge 층 + post, 값 −10–130
        if isinstance(tp, dict):
            cte, tc = tp.get("cte_um_per_m_c"), tp.get("temp_c")
            on = num(cte) and cte != 0
            if on and not isinstance(tc, dict):
                self.emit("X-TRU-02", path, row, "truth.gauge_temp_params", list(tp), "열 모델을 켰는데 (cte ≠ 0) temp_c dict가 없음")
            if "temp_c" in tp and not isinstance(tc, dict):
                if not on:
                    self.emit("X-TRU-02", path, row, "truth.gauge_temp_params", tc, "temp_c가 dict가 아님")
            elif isinstance(tc, dict):
                badk = [k for k in tc if not TEMP_KEY_RE.match(k)]
                if badk:
                    self.emit("X-TRU-02", path, row, "truth.gauge_temp_params", badk[:5], "temp_c 키가 L### · post가 아님 (_pNN 금지)")
                badv = [k for k, v in tc.items() if not (num(v) and -10 <= v <= 130)]
                if badv:
                    self.emit("X-TRU-02", path, row, "truth.gauge_temp_params", {k: tc[k] for k in badv[:5]},
                              "temp_c 값이 −10 ≤ x ≤ 130 수가 아님")
                if on and ctx is not None and "gauge_layers" in ctx and set(tc) != set(ctx["gauge_layers"]):
                    self.emit("X-TRU-02", path, row, "truth.gauge_temp_params", sorted(set(tc) ^ set(ctx["gauge_layers"]))[:5],
                              "temp_c 키 집합 ≠ step_gauge 기준이 있는 층 (+ post)")
        # X-TRU-03 블라인드
        ss, sf = t.get("scan_seeds"), t.get("scan_factors")
        if ctx is not None and ctx.get("blind") is not None:
            if ctx["blind"] and (not isinstance(ss, dict) or not isinstance(sf, dict)):
                self.emit("X-TRU-03", path, row, "truth.scan_seeds", "없음", "blind = true인데 참값이 없음")
            if not ctx["blind"] and (ss is not None or sf is not None):
                self.emit("X-TRU-03", path, row, "truth.scan_seeds", "값 있음", "blind = false인데 null이 아님")
        for name, d in (("scan_seeds", ss), ("scan_factors", sf)):
            if not isinstance(d, dict):
                continue
            if ctx is not None and ctx.get("scan_ids") and set(d) != set(ctx["scan_ids"]):
                self.emit("X-TRU-03", path, row, f"truth.{name}", sorted(set(d) ^ set(ctx["scan_ids"]))[:5], "키 집합 ≠ 캠페인 스캔 ID")
            for k, v in d.items():
                if name == "scan_seeds":
                    ok = isinstance(v, dict) and isinstance(v.get("sim_seed"), int) and not isinstance(v.get("sim_seed"), bool) \
                        and 0 <= v["sim_seed"] < 2 ** 63 and (v.get("noise_seed") is None or (
                            isinstance(v["noise_seed"], int) and not isinstance(v["noise_seed"], bool) and 0 <= v["noise_seed"] < 2 ** 63))
                else:
                    ok = isinstance(v, list) and all(isinstance(e, str) and MF_RE.match(e) for e in v)
                if not ok:
                    self.emit("X-TRU-03", path, row, f"truth.{name}", f"{k}: {v}")
        # X-TRU-04 요인 파라미터 키 = 주입 요인 합집합 (blind면 scan_factors 값의 합집합)
        fp = t.get("factor_params")
        if isinstance(fp, dict):
            want = None
            if isinstance(sf, dict) and (ctx is None or ctx.get("blind") is not False):
                want = {e for v in sf.values() if isinstance(v, list) for e in v}
            elif ctx is not None and ctx.get("blind") is False:
                want = set(ctx.get("factors", []))
            if want is not None and set(fp) != want:
                self.emit("X-TRU-04", path, row, "truth.factor_params", sorted(set(fp) ^ want)[:5])
        # X-TRU-05 필러게이지 참 두께
        gt = t.get("gauge_thickness_mm")
        if isinstance(gt, dict):
            for k, v in gt.items():
                if k not in ("0.20", "0.30", "0.40", "0.50") or not num(v) or abs(v - float(k)) > 0.02 + 1e-12:
                    self.emit("X-TRU-05", path, row, "truth.gauge_thickness_mm", f"{k}: {v}")

    # -- 트리 ---------------------------------------------------------------
    def _walk(self):
        self.cal_dirs: dict[str, list[str]] = {}
        self.msa_dirs: dict[str, list[str]] = {}
        self.sessions: dict[str, dict] = {}
        for p in self.paths:
            parts = p.rstrip("/").split("/")
            low = [x.lower() for x in parts]
            if "_truth" in low or parts[-1] == "truth.json" or "heightmaps" in low or TRUTH_MAP_RE.match(parts[-1]):
                self.emit("LEAK-02", p, message="참값 파일·폴더가 data/raw 아래에 있음")
                continue
            top = parts[0]
            if top == "calibration" and len(parts) >= 3:
                if not NAME_RES["cal"].match(parts[1]):
                    self.emit("FILE-02", p, message="교정 폴더 이름이 정규식과 맞지 않음")
                    continue
                rest = "/".join(parts[2:])
                if rest in ("cal_manifest.csv", "cal_results.csv") or NAME_RES["calimg"].match(rest):
                    self.cal_dirs.setdefault(parts[1], []).append(rest)
                elif re.match(r"^d[1-5]/", rest):
                    self.emit("FILE-02", p, message="교정 원자료 영상 이름이 정규식과 맞지 않음")
                else:
                    self.emit("FILE-01", p)
            elif top == "msa" and len(parts) == 3:
                if not NAME_RES["msa"].match(parts[1]):
                    self.emit("FILE-02", p, message="MSA 폴더 이름이 정규식과 맞지 않음")
                elif parts[2] in ("design.csv", "design_executed.csv"):
                    self.msa_dirs.setdefault(parts[1], []).append(parts[2])
                else:
                    self.emit("FILE-01", p)
            elif top == "sessions" and len(parts) >= 3:
                sid = parts[1]
                if not NAME_RES["session"].match(sid):
                    self.emit("FILE-02", p, message="세션 폴더 이름이 정규식과 맞지 않음")
                    continue
                s = self.sessions.setdefault(sid, {"printer": [], "refs": {}, "specreps": {}})
                sub = parts[2]
                if sub == "printer" and len(parts) >= 4:
                    s["printer"].append("/".join(parts[3:]))
                elif sub == "reference" and len(parts) >= 4:
                    self._add_ref(s["refs"], parts[3], parts[4:], p)
                # bltouch/ 폴더는 명세 8절에서 빠짐 (D-14): FILE-01
                elif NAME_RES["specrep"].match(sub) and len(parts) >= 5:
                    lay = parts[3]
                    if not NAME_RES["layer"].match(lay):
                        self.emit("FILE-02", p, message="층 폴더 이름이 정규식과 맞지 않음 (L### 또는 post, 뒤에 _pNN)")
                        continue
                    sr = s["specreps"].setdefault(sub, {})
                    sc = sr.setdefault(lay, {"files": [], "refs": {}})
                    rest = parts[4:]
                    if rest[0] == "reference" and len(rest) >= 2:
                        self._add_ref(sc["refs"], rest[1], rest[2:], p)
                    elif len(rest) == 1 and rest[0] in ("meta.json", "frames_index.csv", "position_log.csv", "frames.npz"):
                        sc["files"].append(rest[0])
                    elif rest[0] == "frames" and len(rest) == 2:
                        if NAME_RES["frame"].match(rest[1]):
                            sc["files"].append("frames/" + rest[1])
                        else:
                            self.emit("FILE-02", p, message="프레임 파일 이름이 정규식과 맞지 않음")
                    elif p.endswith("/") and rest == ["frames"]:
                        sc["files"].append("frames/")
                    else:
                        self.emit("FILE-01", p)
                elif NAME_RES["specrep"].match(sub) or re.match(r"^S\d", sub):
                    if not NAME_RES["specrep"].match(sub):
                        self.emit("FILE-02", p, message="시편·반복 폴더 이름이 정규식과 맞지 않음")
                    else:
                        self.emit("FILE-01", p)
                else:
                    self.emit("FILE-01", p)
            else:
                self.emit("FILE-01", p)

    def _add_ref(self, refs, ref_id, rest, p):
        if not NAME_RES["ref"].match(ref_id):
            self.emit("FILE-02", p, message="기준 폴더 이름이 정규식과 맞지 않음")
            return
        r = refs.setdefault(ref_id, [])
        rel = "/".join(rest)
        if rel in ("ref_index.csv", "frames_index.csv", "position_log.csv", "frames/", "frames.npz"):
            r.append(rel)
        elif len(rest) == 2 and rest[0] == "frames" and NAME_RES["frame"].match(rest[1]):
            r.append(rel)
        elif len(rest) == 2 and rest[0] == "frames":
            self.emit("FILE-02", p, message="프레임 파일 이름이 정규식과 맞지 않음")
        else:
            self.emit("FILE-01", p)

    # -- CSV ---------------------------------------------------------------
    def read_csv(self, path: str, fname: str, group: str, ctx_base: dict):
        """CSV 형식 검사 + 필드 검사. (typed_rows, raw_rows).

        같은 내용·같은 조건이면 결과를 다시 쓴다 (자체 시험에서 표본 수백 개를 빨리 돌리려고).
        필드 검사가 보는 바깥 값은 virtual, blind (rep), meta.raw_saved, meta.mesh_enabled뿐이라 그것만 열쇠에 넣는다.
        """
        data = self.fs.read(path)
        meta = ctx_base.get("meta") or {}
        key = (path, fname, group, sha256_bytes(data), ctx_base.get("virtual"), ctx_base.get("blind"),
               meta.get("raw_saved"), meta.get("mesh_enabled"))
        hit = self._csv_cache.get(key)
        if hit is not None:
            found, typed, raw = hit
            self.out.extend(found)
            return typed, raw
        n0 = len(self.out)
        typed, raw = self._read_csv(data, path, fname, group, ctx_base)
        self._csv_cache[key] = (list(self.out[n0:]), typed, raw)
        return typed, raw

    def _read_csv(self, data: bytes, path: str, fname: str, group: str, ctx_base: dict):
        if data.startswith(b"\xef\xbb\xbf"):
            self.emit("CSV-01", path)
            data = data[3:]
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            self.emit("CSV-08", path)
            return [], []
        if "\r\n" in text:
            self.emit("CSV-02", path)
            text = text.replace("\r\n", "\n")
        lines = list(csv.reader(io.StringIO(text, newline="")))
        if not lines:
            self.emit("CSV-03", path, message="머리글이 없음")
            return [], []
        header = lines[0]
        expected = self.file_cols[fname]
        known = []
        for i, col in enumerate(header):
            if col.lower().startswith("truth") and col not in expected:  # rep.truth_id는 명세 필드
                self.emit("LEAK-01", path, None, col, col)
            elif "." in col and col.split(".", 1)[0] in ("frame", "pos", "cal", "ref", "meta", "blt", "rep", "truth"):
                self.emit("CSV-06", path, None, col, col)
                if col.split(".", 1)[1] in expected:
                    known.append(col.split(".", 1)[1])
                    continue
            elif col not in expected:
                self.emit("CSV-04", path, None, col, col)
            known.append(col)
        bare = [c.split(".", 1)[1] if "." in c else c for c in header]
        if [c for c in bare if c in expected] != expected:
            self.emit("CSV-03", path, None, "", ",".join(header)[:200])
        for c in expected:
            if c not in bare:
                self.emit(f"REQ.{group}.{c}", path, None, f"{group}.{c}", "", "열이 없음")
        raw_rows = []
        for ln, cells in enumerate(lines[1:], start=2):
            if len(cells) != len(header):
                self.emit("CSV-07", path, ln, "", str(len(cells)))
                continue
            rr = {}
            for col, val in zip(known, cells):
                if col in expected:
                    rr[col] = val
            for col in expected:
                rr.setdefault(col, "")
            raw_rows.append((ln, rr))
        typed_rows = []
        just_raw = [rr for _, rr in raw_rows]
        for ln, rr in raw_rows:
            for col, val in rr.items():
                if val in MISSING_MARKERS:
                    self.emit("CSV-05", path, ln, f"{group}.{col}", val)
            ctx = dict(ctx_base, file=fname, raw=rr, raw_rows=just_raw)
            typed_rows.append(self.check_record(rr, group, expected, path, ln, ctx, csv_mode=True))
        return typed_rows, just_raw

    # -- 필드 검사 (REQ · DTYPE · REGEX · ENUM · RANGE · CROSS-EMPTY) --------
    def check_record(self, raw: dict, group: str, cols: list[str], path: str, ln, ctx: dict, csv_mode: bool) -> dict:
        typed = {}
        bad = set()
        for col in cols:
            fd = self.fields[f"{group}.{col}"]
            v = raw.get(col)
            pv = parse_csv_value(v, fd["dtype"]) if csv_mode else parse_json_value(v, fd["dtype"])
            if pv is _BAD:
                self.emit(f"DTYPE.{fd['field']}", path, ln, fd["field"], v)
                bad.add(col)
                typed[col] = None
            else:
                if fd["dtype"] == "str" and pv is not None and pv == "":
                    pv = None
                typed[col] = pv
        ctx = dict(ctx, row=typed, raw=raw)
        for col in cols:
            name = f"{group}.{col}"
            fd = self.fields[name]
            v = raw.get(col)
            missing = is_missing(v) and col not in bad
            if fd["req"] == "필수":
                if missing:
                    if name == "meta.specimen_temp_c" and typed.get("source") == "real" and \
                            "specimen_temp_c 없음:" in (typed.get("notes") or ""):
                        pass
                    else:
                        self.emit(f"REQ.{name}", path, ln, name, "")
            elif fd["req"] == "조건부" and name in COND_FUNCS:
                c = COND_FUNCS[name](ctx)
                if c is True and missing:
                    self.emit(f"REQ.{name}", path, ln, name, "")
                elif c is False and not is_missing(v) and f"CROSS-EMPTY.{name}" in self.rules:
                    self.emit(f"CROSS-EMPTY.{name}", path, ln, name, v)
            pv = typed.get(col)
            if pv is None:
                continue
            self._value_rules(fd, pv, path, ln)
        return typed

    def _compile_value_rules(self, name: str, fd: dict) -> list:
        """필드 하나의 REGEX · ENUM · RANGE 검사를 미리 만든다 (활성 규칙만)."""
        out = []
        rid = f"REGEX.{name}"
        if rid in self.active:
            pats = [re.compile(p) for p in self.rules[rid]["params"].split("||")]

            def regex_ok(pv, pats=pats):
                items = pv if isinstance(pv, list) else [pv]
                return all(isinstance(it, str) and any(p.search(it) for p in pats) for it in items)
            out.append((rid, regex_ok))
        rid = f"ENUM.{name}"
        if rid in self.active:
            allowed = self.rules[rid]["params"].split(",")
            dt = fd["dtype"]
            if dt == "bool":
                ok_set = {a == "true" for a in allowed if a in ("true", "false")}
                out.append((rid, lambda pv, s=ok_set: pv in s))
            elif dt in ("int", "int64"):
                ints = {int(a) for a in allowed}
                out.append((rid, lambda pv, s=ints: pv in s))
            elif dt == "float":
                fl = [float(a) for a in allowed]
                out.append((rid, lambda pv, fl=fl: any(abs(pv - a) <= 1e-9 for a in fl)))
            else:
                st = set(allowed)
                out.append((rid, lambda pv, s=st: pv in s))
        rid = f"RANGE.{name}"
        if rid in self.active:
            if self.rules[rid]["params"] == "finite":
                f = lambda pv: math.isfinite(pv)  # noqa: E731
            else:
                lo = (fd["min_op"], _numval(fd["min"])) if fd["min"] else None
                hi = (fd["max_op"], _numval(fd["max"])) if fd["max"] else None

                def f(pv, lo=lo, hi=hi):
                    return (math.isfinite(pv) and (lo is None or _cmp(pv, lo[0], lo[1], True))
                            and (hi is None or _cmp(pv, hi[0], hi[1], False)))
            out.append((rid, lambda pv, f=f: not (isinstance(pv, (int, float)) and not isinstance(pv, bool)) or f(pv)))
        return out

    def _value_rules(self, fd, pv, path, ln):
        name = fd["field"]
        checks = self._vrules.get(name)
        if checks is None:
            checks = self._vrules[name] = self._compile_value_rules(name, fd)
        for rid, ok in checks:
            if not ok(pv):
                self.emit(rid, path, ln, name, pv)

    # -- JSON (meta.json) --------------------------------------------------
    def read_meta(self, path: str, ctx_base: dict):
        """meta.json 검사. read_csv처럼 같은 내용·같은 조건 (virtual)이면 결과를 다시 쓴다 (v1.0 표본이 스캔 5개라 자체 시험 속도)."""
        data = self.fs.read(path)
        key = ("meta", path, sha256_bytes(data), ctx_base.get("virtual"))
        hit = self._csv_cache.get(key)
        if hit is not None:
            found, typed = hit
            self.out.extend(found)
            return dict(typed) if typed is not None else None
        n0 = len(self.out)
        typed = self._read_meta(data, path, ctx_base)
        self._csv_cache[key] = (list(self.out[n0:]), dict(typed) if typed is not None else None)
        return typed

    def _read_meta(self, data: bytes, path: str, ctx_base: dict):
        try:
            if data.startswith(b"\xef\xbb\xbf"):
                raise ValueError("BOM")
            obj = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.emit("JSON-04", path)
            return None
        if not isinstance(obj, dict):
            self.emit("JSON-05", path)
            return None
        self._json_format(path, data.decode("utf-8"), obj)
        cols = self.file_cols["meta.json"]
        raw = {}
        for k, v in obj.items():
            if k.lower().startswith("truth"):
                self.emit("LEAK-01", path, None, k, k)
            elif "." in k and k.split(".", 1)[0] in ("frame", "pos", "cal", "ref", "meta", "blt", "rep", "truth"):
                self.emit("JSON-02", path, None, k, k)
                if k.split(".", 1)[1] in cols:
                    raw[k.split(".", 1)[1]] = v
            elif k not in cols:
                self.emit("JSON-01", path, None, k, k)
            else:
                raw[k] = v
        for c in cols:
            if c not in raw:
                if c not in obj and f"meta.{c}" not in obj:
                    self.emit("JSON-03", path, None, f"meta.{c}", "")
                    self.emit(f"REQ.meta.{c}", path, None, f"meta.{c}", "", "키가 없음")
                raw[c] = None
        return self.check_record(raw, "meta", cols, path, None, dict(ctx_base, file="meta.json"), csv_mode=False)

    def _json_format(self, path: str, text: str, obj: dict):
        """명세 §0.5 JSON 표기: 들여쓰기 2칸 (JSON-06), ensure_ascii=False (JSON-07). 둘 다 WARN."""
        lines = [ln for ln in text.split("\n") if ln.strip()]
        lead = [ln[:len(ln) - len(ln.lstrip(" \t"))] for ln in lines[1:]]
        pos = [len(w) for w in lead if w]
        if any("\t" in w for w in lead):
            self.emit("JSON-06", path, None, "", "탭", "들여쓰기에 탭이 있음 (명세 §0.5: 들여쓰기 2칸)")
        elif obj and not pos:
            self.emit("JSON-06", path, None, "", "한 줄", "들여쓰기 없이 한 줄로 씀 (명세 §0.5: 들여쓰기 2칸)")
        elif pos and (min(pos) != 2 or any(n % 2 for n in pos)):
            n = min(pos) if min(pos) != 2 else next(n for n in pos if n % 2)
            self.emit("JSON-06", path, None, "", f"{n}칸", f"들여쓰기 {n}칸이 있음 (명세 §0.5: 2칸 단위)")
        for m in re.finditer(r"\\+u([0-9a-fA-F]{4})", text):
            if (len(m.group(0)) - 5) % 2 == 1 and int(m.group(1), 16) >= 0x80:
                self.emit("JSON-07", path, None, "", m.group(0)[-6:])
                break

    # -- PNG ---------------------------------------------------------------
    def _png(self, data: bytes):
        key = sha256_bytes(data)
        if key not in self._png_cache:
            from PIL import Image
            try:
                im = Image.open(io.BytesIO(data))
                im.load()
                mode = im.mode
                bits = 8 if mode in ("L", "P", "1") else 16 if mode.startswith("I;16") or mode == "I" else None
                chans = len(im.getbands())
                ext = im.getextrema()
                mx = ext[1] if isinstance(ext, tuple) and not isinstance(ext[0], tuple) else max(e[1] for e in ext)
                self._png_cache[key] = (key, im.size[0], im.size[1], bits, chans, mx)
            except Exception:
                self._png_cache[key] = (key, None, None, None, None, None)
        return self._png_cache[key]

    # -- 프레임 색인 -----------------------------------------------------------
    def check_frames(self, base: str, files: list[str], rows: list[dict], meta: dict | None, scan_id_expect,
                     layer_expect, is_scan: bool, index_path: str):
        """frames_index.csv 교차·파일 검사. base = 스캔(또는 기준) 폴더 경로."""
        P = index_path
        if not rows:
            return
        sids = {r["scan_id"] for r in rows if r["scan_id"] is not None}
        if len(sids) > 1 or (scan_id_expect is not None and sids and sids != {scan_id_expect}):
            self.emit("X-FRM-01", P, None, "frame.scan_id", ",".join(sorted(sids)))
        lays = {r["layer_idx"] for r in rows if r["layer_idx"] is not None}
        if len(lays) > 1 or (is_scan and layer_expect is not None and lays and lays != {layer_expect}):
            self.emit("X-FRM-02", P, None, "frame.layer_idx", ",".join(map(str, sorted(lays))))
        elif not is_scan and layer_expect is not None and lays and lays != {layer_expect}:
            # 기준 촬영 폴더: = ref.layer_idx, ref.layer_idx가 빈 칸이면 -1 (호출하는 쪽이 -1을 넘김)
            self.emit("X-FRM-20", P, None, "frame.layer_idx", ",".join(map(str, sorted(lays))))
        # 트리거 펄스 번호 (T14): 값이 있는 행끼리 증가, 차 − 1 = dropped_before
        prev_pulse = None
        for i, r in enumerate(rows):
            tp = r.get("trig_pulse_idx")
            if tp is None:
                continue
            if prev_pulse is not None:
                if tp <= prev_pulse:
                    self.emit("X-FRM-21", P, i + 2, "frame.trig_pulse_idx", tp)
                elif r["dropped_before"] is not None and tp - prev_pulse - 1 != r["dropped_before"]:
                    self.emit("X-FRM-22", P, i + 2, "frame.trig_pulse_idx", tp)
            prev_pulse = tp
        # 게이트: true 행이 한 덩어리
        g = [r.get("gate_on") for r in rows]
        on = [i for i, v in enumerate(g) if v is True]
        if on and any(g[i] is not True for i in range(on[0], on[-1] + 1)):
            self.emit("X-FRM-23", P, None, "frame.gate_on", f"{on[0]}~{on[-1]}")
        fidx = [r["frame_idx"] for r in rows]
        if fidx != list(range(len(rows))):
            self.emit("X-FRM-03", P, None, "frame.frame_idx", ",".join(map(str, fidx[:20])))
        prev = {}
        for i, r in enumerate(rows):
            ln = i + 2
            f = r["file"]
            if f is not None and r["frame_idx"] is not None:
                m = re.search(r"(\d{6})(\.png)?$", f)
                if m and int(m.group(1)) != r["frame_idx"]:
                    self.emit("X-FRM-04", P, ln, "frame.file", f)
            if f is not None:
                if f.startswith("frames.npz#"):
                    if "frames.npz" not in files:
                        self.emit("FILE-06", P, ln, "frame.file", f)
                elif f not in files:
                    self.emit("FILE-06", P, ln, "frame.file", f)
                else:
                    data = self.fs.read(f"{base}/{f}")
                    key, w, h, bits, chans, mx = self._png(data)
                    if r["sha256"] is not None and key != r["sha256"]:
                        self.emit("FILE-07", P, ln, "frame.sha256", r["sha256"])
                    if w is not None:
                        if (r["roi_w_px"] is not None and w != r["roi_w_px"]) or (r["roi_h_px"] is not None and h != r["roi_h_px"]):
                            self.emit("FILE-08", P, ln, "frame.roi_w_px", f"{w}x{h}")
                        bd = r["bit_depth"]
                        if bd is not None:
                            if chans != 1 or (bits == 8 and bd != 8) or (bits == 16 and bd == 8) or bits is None \
                                    or mx > 2 ** bd - 1:
                                self.emit("FILE-09", P, ln, "frame.bit_depth", bd)
                    else:
                        self.emit("FILE-09", P, ln, "frame.file", f, "PNG로 읽히지 않음")
            for k, rid in (("t_cam_ns", "X-FRM-05"), ("t_host_ns", "X-FRM-06"), ("cam_seq", "X-FRM-07")):
                if r[k] is not None:
                    if k in prev and prev[k] is not None and r[k] <= prev[k]:
                        self.emit(rid, P, ln, f"frame.{k}", r[k])
            if i > 0 and r["cam_seq"] is not None and prev.get("cam_seq") is not None and r["dropped_before"] is not None:
                if r["dropped_before"] != r["cam_seq"] - prev["cam_seq"] - 1:
                    self.emit("X-FRM-17", P, ln, "frame.dropped_before", r["dropped_before"])
            prev = {k: r[k] for k in ("t_cam_ns", "t_host_ns", "cam_seq")}
            if r["lossy"] is not None and r["pixel_format"] is not None:
                if r["lossy"] != (r["pixel_format"] == "MJPG"):
                    self.emit("X-FRM-12", P, ln, "frame.lossy", r["lossy"])
            if meta:
                if r["exposure_us"] is not None and meta.get("fps"):
                    if r["exposure_us"] > 1e6 / meta["fps"]:
                        self.emit("X-FRM-08", P, ln, "frame.exposure_us", r["exposure_us"])
                W, Hh = meta.get("cam_res_w_px"), meta.get("cam_res_h_px")
                if W is not None and r["roi_x0_px"] is not None and r["roi_w_px"] is not None and r["roi_x0_px"] + r["roi_w_px"] > W:
                    self.emit("X-FRM-13", P, ln, "frame.roi_x0_px", r["roi_x0_px"])
                if Hh is not None and r["roi_y0_px"] is not None and r["roi_h_px"] is not None and r["roi_y0_px"] + r["roi_h_px"] > Hh:
                    self.emit("X-FRM-14", P, ln, "frame.roi_y0_px", r["roi_y0_px"])
            if r["saturated_px"] is not None and r["roi_w_px"] is not None and r["roi_h_px"] is not None:
                if r["saturated_px"] > r["roi_w_px"] * r["roi_h_px"]:
                    self.emit("X-FRM-18", P, ln, "frame.saturated_px", r["saturated_px"])
        for k, rid in (("exposure_us", "X-FRM-09"), ("gain_db", "X-FRM-10"), ("pixel_format", "X-FRM-11"), ("trigger_mode", "X-FRM-16")):
            vals = {r[k] for r in rows if r[k] is not None}
            if len(vals) > 1:
                self.emit(rid, P, None, f"frame.{k}", ",".join(map(str, sorted(vals, key=str))))
        if is_scan and not any(r["laser_on"] is False for r in rows):
            self.emit("X-FRM-15", P, None, "frame.laser_on", "")

    # -- 교정 ---------------------------------------------------------------
    def _calibration(self):
        self.cal_rows: dict[str, list[dict]] = {}
        for cid, files in sorted(self.cal_dirs.items()):
            base = f"calibration/{cid}"
            if "cal_manifest.csv" not in files:
                self.emit("FILE-03", base, message="cal_manifest.csv가 없음")
            allrows = []
            for fn in ("cal_manifest.csv", "cal_results.csv"):
                if fn not in files:
                    continue
                P = f"{base}/{fn}"
                rows, _ = self.read_csv(P, fn, "cal", {"virtual": self.virtual})
                for i, r in enumerate(rows):
                    ln = i + 2
                    if r["cal_id"] is not None and r["cal_id"] != cid:
                        self.emit("FILE-11", P, ln, "cal.cal_id", r["cal_id"])
                    if r.get("valid_from") and r.get("created") is not None:
                        a, b = _iso(r["valid_from"]), _iso(r["created"])
                        if a and b and a < b:
                            self.emit("X-CAL-09", P, ln, "cal.valid_from", r["valid_from"])
                    if r.get("valid_until") and r.get("valid_from"):
                        a, b = _iso(r["valid_until"]), _iso(r["valid_from"])
                        if a and b and a <= b:
                            self.emit("X-CAL-10", P, ln, "cal.valid_until", r["valid_until"])
                    if fn == "cal_results.csv":
                        if r.get("reproj_rms_px") is not None and r["reproj_rms_px"] >= 0.2:
                            self.emit("W-CAL-11", P, ln, "cal.reproj_rms_px", r["reproj_rms_px"])
                        if r.get("plane_rms_um") is not None and r["plane_rms_um"] >= 5:
                            self.emit("W-CAL-12", P, ln, "cal.plane_rms_um", r["plane_rms_um"])
                        continue
                    if r["target_cols"] is not None and r["target_square_mm"] is not None and r["target_cols"] * r["target_square_mm"] > 20.2:
                        self.emit("X-CAL-01", P, ln, "cal.target_square_mm", r["target_square_mm"])
                    if r["target_marker_mm"] is not None and r["target_square_mm"] is not None and r["target_marker_mm"] >= r["target_square_mm"]:
                        self.emit("X-CAL-02", P, ln, "cal.target_marker_mm", r["target_marker_mm"])
                    if r["image_file"] is not None:
                        m = re.match(r"^d([1-5])/", r["image_file"])
                        if m and r["kind"] is not None and r["kind"] != f"D{m.group(1)}":
                            self.emit("X-CAL-04", P, ln, "cal.image_file", r["image_file"])
                        if r["image_file"] not in files:
                            self.emit("FILE-12", P, ln, "cal.image_file", r["image_file"])
                    if r["gauge_measured_mm"] is not None and r["gauge_nominal_mm"] is not None and abs(r["gauge_measured_mm"] - r["gauge_nominal_mm"]) > 0.02 + 1e-12:
                        self.emit("X-CAL-08", P, ln, "cal.gauge_measured_mm", r["gauge_measured_mm"])
                    # SV13 (T1 2차): 원자료 종류 · 기준물
                    rt, tt, kd = r["record_type"], r["target_type"], r["kind"]
                    if rt == "nozzle_touch" and kd is not None and kd != "D4":
                        self.emit("X-CAL-17", P, ln, "cal.record_type", rt)
                    if rt == "micrometer" and tt is not None and tt not in ("filler_gauge", "step_gauge", "material_sample"):
                        self.emit("X-CAL-18", P, ln, "cal.record_type", rt)
                    if tt in ("filler_gauge", "step_gauge", "material_sample") and kd is not None and kd != "D5":
                        self.emit("X-CAL-19", P, ln, "cal.target_type", tt)
                    if rt is not None and rt != "image" and r["laser_on"] is True:
                        self.emit("X-CAL-20", P, ln, "cal.laser_on", True)
                    gb = r["gauge_block_id"]
                    if gb is not None and gb.startswith("FG-") and r["gauge_nominal_mm"] is not None:
                        try:
                            if abs(float(gb[3:]) - r["gauge_nominal_mm"]) > 1e-9:
                                self.emit("X-CAL-21", P, ln, "cal.gauge_block_id", gb)
                        except ValueError:
                            pass  # 형식은 REGEX가 봄
                    if gb is not None and gb.startswith("GB-") and r["gauge_block_height_mm"] is not None:
                        # v1.0: ID 숫자를 소수까지 읽어 더함 (GB-01.4+01.1 = 2.5)
                        s = gauge_sum(gb)
                        if s is not None and abs(r["gauge_block_height_mm"] - s) > 0.02 + 1e-12:
                            self.emit("X-CAL-22", P, ln, "cal.gauge_block_height_mm", r["gauge_block_height_mm"])
                    # v1.0: cal 쪽 step_gauge ⇔ GB-, filler_gauge ⇔ FG-, GB-00은 cal 행 없음 (T6 질문 3)
                    if gb is not None and (gb == "GB-00" or (tt == "step_gauge" and not gb.startswith("GB-"))
                                           or (tt == "filler_gauge" and not gb.startswith("FG-"))):
                        self.emit("X-CAL-25", P, ln, "cal.gauge_block_id", gb)
                if fn == "cal_manifest.csv":
                    seen = set()
                    for i, r in enumerate(rows):
                        k = (r["cal_id"], r["kind"], r["pose_idx"], r["laser_on"])
                        if k in seen:
                            self.emit("X-CAL-03", P, i + 2, "cal.pose_idx", r["pose_idx"])
                        seen.add(k)
                    d2 = [r for r in rows if r["kind"] == "D2"]
                    poses: dict = {}
                    for r in d2:
                        poses.setdefault(r["pose_idx"], []).append(r)
                    zs = {}
                    for pidx, rs in poses.items():
                        if {r["laser_on"] for r in rs} != {True, False}:
                            self.emit("X-CAL-05", P, None, "cal.laser_on", f"pose {pidx}")
                        ex = {r["exposure_us"] for r in rs if r["exposure_us"] is not None}
                        if len(ex) > 1:
                            self.emit("X-CAL-06", P, None, "cal.exposure_us", f"pose {pidx}")
                        z = {r["cmd_z_mm"] for r in rs if r["cmd_z_mm"] is not None}
                        if len(z) > 1:
                            self.emit("X-CAL-07", P, None, "cal.cmd_z_mm", f"pose {pidx}")
                        if z:
                            zs[pidx] = min(z)
                    vals = list(zs.values())
                    if len(set(vals)) != len(vals) or (vals and max(vals) - min(vals) > 8.0):
                        self.emit("X-CAL-07", P, None, "cal.cmd_z_mm", ",".join(map(str, vals)))
                    heights: dict = {}
                    for i, r in enumerate(rows):
                        if r["gauge_block_id"] is not None and r["gauge_block_height_mm"] is not None:
                            h0 = heights.setdefault((r["cal_id"], r["gauge_block_id"]), r["gauge_block_height_mm"])
                            if abs(h0 - r["gauge_block_height_mm"]) > 1e-12:
                                self.emit("X-CAL-23", P, i + 2, "cal.gauge_block_height_mm", r["gauge_block_height_mm"])
                    # v1.0: 한 cal_id 안 material_sample 행의 (material, color)는 하나뿐
                    mats = {(r["material"], r["color"]) for r in rows
                            if r["target_type"] == "material_sample" and r["material"] is not None and r["color"] is not None}
                    if len(mats) > 1:
                        self.emit("X-CAL-27", P, None, "cal.material", sorted(mats))
                allrows += rows
            self.cal_rows[cid] = allrows

    # -- MSA ---------------------------------------------------------------
    def _msa(self):
        for sid, files in sorted(self.msa_dirs.items()):
            base = f"msa/{sid}"
            if "design.csv" not in files:
                self.emit("FILE-03", base, message="design.csv가 없음")
            for fn in ("design.csv", "design_executed.csv"):
                if fn not in files:
                    continue
                P = f"{base}/{fn}"
                rows, _ = self.read_csv(P, fn, "rep", {"virtual": self.virtual, "blind": self.blind})
                part, truth, seen, seeds, orders = {}, {}, set(), set(), []
                for i, r in enumerate(rows):
                    ln = i + 2
                    if r["study_id"] is not None and r["study_id"] != sid:
                        self.emit("FILE-16", P, ln, "rep.study_id", r["study_id"])
                    sp = r["specimen_id"]
                    if sp is not None and r["part_idx"] is not None:
                        if part.setdefault(sp, r["part_idx"]) != r["part_idx"]:
                            self.emit("X-REP-01", P, ln, "rep.part_idx", r["part_idx"])
                    if sp is not None and r["truth_id"] is not None:
                        if truth.setdefault(sp, r["truth_id"]) != r["truth_id"]:
                            self.emit("X-REP-07", P, ln, "rep.truth_id", r["truth_id"])
                    k = (r["part_idx"], r["session_id"], r["operator"], r["repeat_idx"])
                    if k in seen:
                        self.emit("X-REP-02", P, ln, "rep.repeat_idx", r["repeat_idx"])
                    seen.add(k)
                    if r["noise_seed"] is not None:
                        if r["noise_seed"] in seeds:
                            self.emit("X-REP-06", P, ln, "rep.noise_seed", r["noise_seed"])
                        seeds.add(r["noise_seed"])
                    if r["run_order"] is not None:
                        if r["run_order"] > len(rows) or r["run_order"] in orders:
                            self.emit("X-REP-04", P, ln, "rep.run_order", r["run_order"])
                        orders.append(r["run_order"])
                    if fn == "design_executed.csv" and r["remount"] is True and r["scan_id"] is not None and "_L" in r["scan_id"]:
                        self.emit("X-REP-03", P, ln, "rep.remount", "true")

    # -- 세션·스캔 -------------------------------------------------------------
    def _read_ref(self, base, files, ctx_meta):
        """기준 폴더 하나: ref_index.csv 행들과 frames_index 행들."""
        out = {"rows": [], "frames": [], "pos": [], "base": base}
        folder = base.rsplit("/", 1)[-1]
        for fx in ("ref_index.csv", "frames_index.csv"):
            if fx not in files:
                self.emit("FILE-03", base, message=f"{fx}가 없음")
        if "ref_index.csv" in files:
            out["rows"], _ = self.read_csv(f"{base}/ref_index.csv", "ref_index.csv", "ref", {"virtual": self.virtual})
        if "frames_index.csv" in files:
            out["frames"], _ = self.read_csv(f"{base}/frames_index.csv", "frames_index.csv", "frame",
                                             {"virtual": self.virtual, "meta": ctx_meta})
        kinds = {r["kind"] for r in out["rows"] if r["kind"] is not None}
        if "position_log.csv" in files:
            out["pos"], _ = self.read_csv(f"{base}/position_log.csv", "position_log.csv", "pos",
                                          {"virtual": self.virtual, "meta": ctx_meta})
        elif kinds & MOVING_REF:
            self.emit("FILE-03", base, message="움직이며 찍는 기준인데 position_log.csv가 없음 (명세 4절)")
        # 기준 위치 로그의 scan_id · layer_idx = 그 기준 frames_index (명세 4절)
        if out["pos"] and out["frames"]:
            fs_ids = {r["scan_id"] for r in out["frames"] if r["scan_id"] is not None}
            fl = {r["layer_idx"] for r in out["frames"] if r["layer_idx"] is not None}
            for i, r in enumerate(out["pos"]):
                if (r["scan_id"] is not None and fs_ids and r["scan_id"] not in fs_ids) or \
                        (r["layer_idx"] is not None and fl and r["layer_idx"] not in fl):
                    self.emit("X-POS-11", f"{base}/position_log.csv", i + 2, "pos.layer_idx", f"{r['scan_id']},{r['layer_idx']}")
        for i, r in enumerate(out["rows"]):
            ln = i + 2
            if r["ref_id"] is not None and r["ref_id"] != folder:
                self.emit("FILE-19", f"{base}/ref_index.csv", ln, "ref.ref_id", r["ref_id"])
            if r["ref_id"] is not None and r["kind"] is not None:
                if r["ref_id"][4:7] != REF_ABBR.get(r["kind"], "?"):
                    self.emit("X-REF-01", f"{base}/ref_index.csv", ln, "ref.ref_id", r["ref_id"])
            gb = r["gauge_block_id"]
            # v1.0: step_gauge는 GB- (블록 · 베드 면) 또는 FG- (아래 단 필러게이지), feeler는 FG-
            if gb is not None and ((r["kind"] == "step_gauge" and not gb.startswith(("GB-", "FG-")))
                                   or (r["kind"] == "feeler" and not gb.startswith("FG-"))):
                self.emit("X-REF-13", f"{base}/ref_index.csv", ln, "ref.gauge_block_id", gb)
            if r["n_frames"] is not None:
                if r["n_frames"] != len(out["frames"]):
                    self.emit("X-REF-05", f"{base}/ref_index.csv", ln, "ref.n_frames", r["n_frames"])
                if r["kind"] == "static_repeat" and r["n_frames"] < 100:
                    self.emit("X-REF-06", f"{base}/ref_index.csv", ln, "ref.n_frames", r["n_frames"])
            if r["frames_dir"] is not None:
                d = r["frames_dir"].rstrip("/")
                if not any(f == d + "/" or f.startswith(d + "/") for f in files):
                    self.emit("FILE-13", f"{base}/ref_index.csv", ln, "ref.frames_dir", r["frames_dir"])
            # v1.0: 출력 전 기준은 -1, 층에 매인 기준은 0 ≤ x
            li = r["layer_idx"]
            if li is not None and ((r["kind"] in ("bed_bare", "feeler") and li != -1) or (r["kind"] in LAYER_REFS and li < 0)):
                self.emit("X-REF-17", f"{base}/ref_index.csv", ln, "ref.layer_idx", li)
            # v1.0: GB-00 (베드 면) ⇔ 높이 0
            h = r["gauge_height_mm"]
            if h is not None and gb is not None and ((gb == "GB-00") != (h == 0)):
                self.emit("X-REF-23", f"{base}/ref_index.csv", ln, "ref.gauge_height_mm", f"{gb}, {h}")
        return out

    def _sessions(self):
        for sid, s in sorted(self.sessions.items()):
            sbase = f"sessions/{sid}"
            scans = []
            for sr, layers in sorted(s["specreps"].items()):
                for lay, sc in sorted(layers.items()):
                    scans.append(self._read_scan(sid, sr, lay, sc))
            first_meta = next((x["meta"] for x in scans if x["meta"]), None)
            srefs = {rid: self._read_ref(f"{sbase}/reference/{rid}", files, first_meta) for rid, files in sorted(s["refs"].items())}
            for x in scans:
                for rid, files in sorted(x["refs_files"].items()):
                    x["refs"][rid] = self._read_ref(f"{x['base']}/reference/{rid}", files, x["meta"])
            self._session_cross(sid, s, scans, srefs)

    def _read_scan(self, sid, sr, lay, sc):
        base = f"sessions/{sid}/{sr}/{lay}"
        x = {"sid": sid, "sr": sr, "lay": lay, "base": base, "meta": None, "frames": [], "pos": [],
             "files": sc["files"], "refs_files": sc["refs"], "refs": {}}
        for fx in ("meta.json", "frames_index.csv", "position_log.csv"):
            if fx not in sc["files"]:
                self.emit("FILE-03", base, message=f"{fx}가 없음")
        if "meta.json" in sc["files"]:
            x["meta"] = self.read_meta(f"{base}/meta.json", {"virtual": self.virtual})
        meta = x["meta"] or {}
        ctx = {"virtual": self.virtual, "meta": meta}
        if "frames_index.csv" in sc["files"]:
            x["frames"], _ = self.read_csv(f"{base}/frames_index.csv", "frames_index.csv", "frame", ctx)
        if "position_log.csv" in sc["files"]:
            x["pos"], _ = self.read_csv(f"{base}/position_log.csv", "position_log.csv", "pos", ctx)
        allfiles = self._scan_all_files(base)
        self.check_frames(base, allfiles, x["frames"], meta, meta.get("scan_id"), meta.get("layer_idx"), True,
                          f"{base}/frames_index.csv")
        self._scan_cross(x, allfiles)
        return x

    def _scan_all_files(self, base):
        pre = base + "/"
        return [p[len(pre):] for p in self.paths if p.startswith(pre)]

    def _scan_cross(self, x, allfiles):
        meta, base = x["meta"], x["base"]
        M = f"{base}/meta.json"
        if not meta:
            return
        g = meta.get
        # 경로 일치 (FILE-05)
        srm = re.match(r"^S(\d{2})_r(\d{2})$", x["sr"])
        bad = []
        if g("session_id") is not None and g("session_id") != x["sid"]:
            bad.append("session_id")
        if srm and g("specimen_id") is not None and g("specimen_id") != "S" + srm.group(1):
            bad.append("specimen_id")
        if srm and g("repeat") is not None and g("repeat") != int(srm.group(2)):
            bad.append("repeat")
        lm = re.match(r"^(L(\d{3})|post)(?:_p(\d{2}))?$", x["lay"])
        if lm and lm.group(1) == "post":
            if g("timing") is not None and g("timing") != "post":
                bad.append("timing")
        elif lm:
            if g("layer_idx") is not None and g("layer_idx") != int(lm.group(2)):
                bad.append("layer_idx")
            if g("timing") is not None and g("timing") != "layer":
                bad.append("timing")
        if lm and g("scan_pass_idx") is not None and g("scan_pass_idx") != int(lm.group(3) or 0):
            bad.append("scan_pass_idx")
        if bad:
            self.emit("FILE-05", M, None, ";".join("meta." + b for b in bad), x["lay"])
        sid = g("scan_id")
        if sid is not None and g("scan_pass_idx") is not None:
            pm = re.search(r"_p(\d{2})$", sid)
            if (g("scan_pass_idx") == 0 and pm) or (g("scan_pass_idx") > 0 and (not pm or int(pm.group(1)) != g("scan_pass_idx"))):
                self.emit("X-MET-54", M, None, "meta.scan_id", sid)
        # 저장소 뿌리 기준 파일 (명세 0.1절)
        if self.repo_exists is not None:
            if isinstance(g("gcode_file"), str) and not self.repo_exists(g("gcode_file")):
                self.emit("FILE-17", M, None, "meta.gcode_file", g("gcode_file"))
            if isinstance(g("slicer_profile_file"), str) and not self.repo_exists(g("slicer_profile_file")):
                self.emit("FILE-18", M, None, "meta.slicer_profile_file", g("slicer_profile_file"))
        if sid is not None and g("timing") is not None:
            m = re.match(r"^S\d{2}_r\d{2}(?:_L(\d{3}))?(?:_p\d{2})?$", sid)
            if m:
                if g("timing") == "layer" and (m.group(1) is None or (g("layer_idx") is not None and int(m.group(1)) != g("layer_idx"))):
                    self.emit("X-MET-01", M, None, "meta.scan_id", sid)
                if g("timing") == "post" and m.group(1) is not None:
                    self.emit("X-MET-01", M, None, "meta.scan_id", sid)
        if g("campaign_id") is not None and g("source") is not None:
            if (g("campaign_id")[0] == "V") != (g("source") == "virtual"):
                self.emit("X-MET-02", M, None, "meta.campaign_id", g("campaign_id"))
        if sid is not None and g("specimen_id") is not None and sid[:3] != g("specimen_id"):
            self.emit("X-MET-03", M, None, "meta.specimen_id", g("specimen_id"))
        if sid is not None and g("repeat") is not None:
            m = re.match(r"^S\d{2}_r(\d{2})", sid)
            if m and int(m.group(1)) != g("repeat"):
                self.emit("X-MET-04", M, None, "meta.repeat", g("repeat"))
        if g("timing") is not None and g("thermal_state") is not None:
            if (g("timing") == "layer") != (g("thermal_state") == "in_process"):
                self.emit("X-MET-05", M, None, "meta.thermal_state", g("thermal_state"))
        if g("layer_idx") is not None and g("layer_count") is not None and g("layer_idx") >= g("layer_count"):
            self.emit("X-MET-06", M, None, "meta.layer_idx", g("layer_idx"))
        if g("gcode_line_start") is not None and g("gcode_line_end") is not None and g("gcode_line_start") > g("gcode_line_end"):
            self.emit("X-MET-09", M, None, "meta.gcode_line_start", g("gcode_line_start"))
        if g("layer_end_t_ns") is not None and g("scan_start_t_ns") is not None:
            if g("layer_end_t_ns") >= g("scan_start_t_ns"):
                self.emit("X-MET-11", M, None, "meta.layer_end_t_ns", g("layer_end_t_ns"))
            if g("wait_after_layer_s") is not None:
                if abs(g("wait_after_layer_s") - (g("scan_start_t_ns") - g("layer_end_t_ns")) / 1e9) > 0.001 + 1e-9:
                    self.emit("X-MET-13", M, None, "meta.wait_after_layer_s", g("wait_after_layer_s"))
        pa = g("pause_added_s")
        if pa is not None and g("timing") == "layer" and g("scan_length_mm") and g("scan_speed_mm_s"):
            if pa < g("scan_length_mm") / g("scan_speed_mm_s"):
                self.emit("X-MET-14", M, None, "meta.pause_added_s", pa)
        if pa is not None and g("timing") == "post" and pa != 0:
            self.emit("X-MET-14", M, None, "meta.pause_added_s", pa)
        if pa is not None and g("layer_time_s") and pa / g("layer_time_s") > 1:
            self.emit("W-MET-15", M, None, "meta.layer_time_s", g("layer_time_s"))
        if g("scan_z_hop_mm") is not None and g("scan_z_hop_mm") < 1.0:
            self.emit("W-MET-16", M, None, "meta.scan_z_hop_mm", g("scan_z_hop_mm"))
        if g("control_group") not in (None, "none") and g("timing") is not None and g("timing") != "post":
            self.emit("X-MET-19", M, None, "meta.control_group", g("control_group"))
        if g("ambient_light") == "enclosure_dark" and g("enclosure") is False:
            self.emit("X-MET-20", M, None, "meta.enclosure", False)
        if g("layer_h_mm") is not None and g("nozzle_dia_mm") is not None and g("layer_h_mm") > g("nozzle_dia_mm"):
            self.emit("X-MET-24", M, None, "meta.layer_h_mm", g("layer_h_mm"))
        if g("thermal_state") == "cooled" and g("cool_wait_s") is not None and g("wait_after_layer_s") is not None:
            if abs(g("cool_wait_s") - g("wait_after_layer_s")) > 0.001 + 1e-9:
                self.emit("X-MET-34", M, None, "meta.cool_wait_s", g("cool_wait_s"))
        fw = g("firmware")
        if fw is not None and g("firmware_name") is not None and g("firmware_version") is not None:
            # [<제조사>-]<firmware_name>-<판>[-<git 해시 7자리>] (T14, 명세 13절)
            core = re.escape(f"{g('firmware_name')}-{g('firmware_version')}")
            fm = re.fullmatch(rf"([a-z0-9]+-)?{core}(-[0-9a-f]{{7}})?", fw)
            if not fm:
                self.emit("X-MET-36", M, None, "meta.firmware", fw)
            elif fm.group(1) and g("firmware_fork") is not None and g("firmware_fork") != "vendor":
                self.emit("X-MET-59", M, None, "meta.firmware", fw)
        if g("bed_motion") == "y" and g("scan_axis") is not None and g("scan_axis") not in ("+X", "-X"):
            self.emit("W-MET-57", M, None, "meta.scan_axis", g("scan_axis"))
        if g("zero_ref_method") == "z_only":
            self.emit("W-MET-63", M, None, "meta.zero_ref_method", "z_only")
        if g("source") == "real" and g("lens_focus_locked") is False:
            self.emit("W-MET-38", M, None, "meta.lens_focus_locked", False)
        if g("laser_power_mw") is not None and g("laser_power_mw") > 1.0:
            self.emit("W-MET-39", M, None, "meta.laser_power_mw", g("laser_power_mw"))
        if g("filter_center_nm") is not None and g("laser_wavelength_nm") is not None and abs(g("filter_center_nm") - g("laser_wavelength_nm")) > 20:
            self.emit("X-MET-40", M, None, "meta.filter_center_nm", g("filter_center_nm"))
        if g("frame_avg_n") is not None and g("scan_speed_mm_s") and g("scan_speed_mm_s") > 0 and g("frame_avg_n") != 1:
            self.emit("X-MET-43", M, None, "meta.frame_avg_n", g("frame_avg_n"))
        sp, fps, pitch = g("scan_speed_mm_s"), g("fps"), g("scan_pitch_mm")
        if sp is not None and fps is not None and pitch is not None and abs(sp - fps * pitch) > 0.01 * sp + 1e-12:
            self.emit("X-MET-44", M, None, "meta.scan_speed_mm_s", sp)
        if g("n_frames") is not None:
            if "frames_index.csv" in x["files"] and g("n_frames") != len(x["frames"]):
                self.emit("X-MET-45", M, None, "meta.n_frames", g("n_frames"))
            if g("scan_length_mm") and pitch and g("n_frames") < round(g("scan_length_mm") / pitch, 9):
                self.emit("X-MET-46", M, None, "meta.n_frames", g("n_frames"))
        if (g("source") == "real" or g("blind") is True) and g("injected_factors"):
            self.emit("X-MET-51", M, None, "meta.injected_factors", g("injected_factors"))
        if g("source") == "real" and g("blind") is True:
            self.emit("X-MET-66", M, None, "meta.blind", True)
        # 영상 존재 (FILE-15)
        imgs = [f for f in allfiles if f.startswith("frames/") and f != "frames/"] + [f for f in allfiles if f == "frames.npz"]
        if g("raw_saved") is True and not imgs:
            self.emit("FILE-15", M, None, "meta.raw_saved", True)
        if g("raw_saved") is False and imgs:
            self.emit("FILE-15", M, None, "meta.raw_saved", False)
        # files_sha256
        fs = g("files_sha256")
        if isinstance(fs, dict):
            if not all(isinstance(k, str) and k and not k.startswith("/") and "\\" not in k and ".." not in k.split("/") for k in fs) \
                    or not all(is_sha256_hex(v) for v in fs.values()):
                self.emit("X-MET-50", M, None, "meta.files_sha256", list(fs)[:5])
            actual = {f for f in allfiles if not f.endswith("/") and f != "meta.json"}
            if set(fs) != actual:
                self.emit("FILE-10", M, None, "meta.files_sha256", sorted(set(fs) ^ actual)[:5], "파일 목록이 실제와 다름")
            else:
                for k in sorted(actual):
                    if fs[k] != sha256_bytes(self.fs.read(f"{base}/{k}")):
                        self.emit("FILE-10", M, None, "meta.files_sha256", k, "지문이 실제 파일과 다름")
        # 프레임 ↔ meta
        fr = x["frames"]
        if fr:
            exps = [r["exposure_us"] for r in fr if r["exposure_us"] is not None]
            if g("exposure_set_us") is not None and exps and any(abs(e - g("exposure_set_us")) > 0.01 * g("exposure_set_us") + 1e-12 for e in exps):
                self.emit("X-MET-41", M, None, "meta.exposure_set_us", g("exposure_set_us"))
            gains = [r["gain_db"] for r in fr if r["gain_db"] is not None]
            if g("gain_set_db") is not None and gains and any(gg != g("gain_set_db") for gg in gains):
                self.emit("X-MET-42", M, None, "meta.gain_set_db", g("gain_set_db"))
            r0 = fr[0]
            if g("cam_interface") == "usb2" and fps and r0["roi_w_px"] and r0["roi_h_px"] and r0["bit_depth"]:
                if r0["roi_w_px"] * r0["roi_h_px"] * r0["bit_depth"] / 8 * fps > 60e6:
                    self.emit("X-MET-37", M, None, "meta.cam_interface", "usb2")
            # 트리거 (T14): 이 스캔의 frame.trigger_mode로 trigger_pin · trigger_period_s 조건을 봄
            modes = {r["trigger_mode"] for r in fr if r["trigger_mode"] is not None}
            if len(modes) == 1:
                mode = next(iter(modes))
                pin = g("trigger_pin")
                if pin is not None and ((mode in ("hw", "gate")) == (pin == "none")):
                    self.emit("X-MET-60", M, None, "meta.trigger_pin", pin)
                tp = g("trigger_period_s")
                if mode == "hw" and tp is None:
                    self.emit("REQ.meta.trigger_period_s", M, None, "meta.trigger_period_s", "", "trigger_mode = hw인데 칸이 빔")
                if mode != "hw" and tp is not None:
                    self.emit("CROSS-EMPTY.meta.trigger_period_s", M, None, "meta.trigger_period_s", tp)
        tp = g("trigger_period_s")
        if tp is not None and fps:
            if abs(tp * fps - 1) > 0.001 + 1e-12:
                self.emit("X-MET-61", M, None, "meta.trigger_period_s", tp)
        # 위치 로그
        self._pos_cross(x)

    def _pos_cross(self, x):
        meta, rows = x["meta"], x["pos"]
        P = f"{x['base']}/position_log.csv"
        M = f"{x['base']}/meta.json"
        if not rows:
            return
        g = meta.get
        last = {}
        for i, r in enumerate(rows):
            ln = i + 2
            if r["scan_id"] is not None and g("scan_id") is not None and r["scan_id"] != g("scan_id"):
                self.emit("X-POS-01", P, ln, "pos.scan_id", r["scan_id"])
            k = (r["clock"], r["source"])
            if r["t_ns"] is not None:
                if k in last and r["t_ns"] <= last[k]:
                    self.emit("X-POS-02", P, ln, "pos.t_ns", r["t_ns"])
                last[k] = r["t_ns"]
            if r["layer_idx"] is not None and g("layer_idx") is not None and r["layer_idx"] != g("layer_idx"):
                self.emit("X-POS-08", P, ln, "pos.layer_idx", r["layer_idx"])
            if r["acc_x_mm_s2"] is not None and (r["acc_y_mm_s2"] is None or r["acc_z_mm_s2"] is None):
                self.emit("X-POS-10", P, ln, "pos.acc_x_mm_s2", r["acc_x_mm_s2"])

        host = _host_t
        ev = [r["event"] for r in rows]
        starts = [r for r in rows if r["event"] == "scan_start"]
        ends = [r for r in rows if r["event"] == "scan_end"]
        cs = [r for r in rows if r["event"] == "cool_start"]
        ce = [r for r in rows if r["event"] == "cool_end"]
        post0 = g("timing") == "post" and g("scan_pass_idx") in (0, None)  # post 첫 줄 (v1.0: cool 이벤트는 여기만)
        # 식힘·재개 이벤트 (T14). v1.0: belt면 post 첫 줄은 cool_start ~ scan_end, 다른 post 줄은 전체에 motor_off 없음
        if g("z_drive") == "belt" and g("timing") == "post" and "motor_off" in ev:
            if not post0:
                self.emit("X-MET-58", P, None, "pos.event", "motor_off (post 다른 줄)")
            else:
                a = host(cs[0]) if len(cs) == 1 else None
                b = host(ends[0]) if len(ends) == 1 else None
                for r in rows:
                    t = host(r)
                    if r["event"] == "motor_off" and (a is None or b is None or t is None or a <= t <= b):
                        self.emit("X-MET-58", P, rows.index(r) + 2, "pos.event", "motor_off (cool_start ~ scan_end)")
                        break
        if g("timing") == "post" and "resume" in ev:
            self.emit("X-POS-13", P, None, "pos.event", "post 스캔에 resume")
        if (g("timing") == "layer" or (g("timing") == "post" and not post0)) and (cs or ce):
            self.emit("X-POS-14", P, None, "pos.event", "post 첫 줄이 아닌 스캔에 cool_start·cool_end")
        if g("timing") == "post" and any(r["pass_idx"] not in (None, 0) for r in rows):
            self.emit("X-POS-15", P, None, "pos.pass_idx", sorted({r["pass_idx"] for r in rows if r["pass_idx"] is not None}))
        if post0:
            if len(cs) != 1 or len(ce) != 1:
                self.emit("X-POS-14", P, None, "pos.event", f"cool_start {len(cs)}, cool_end {len(ce)}")
            elif len(starts) == 1:
                a, b, s0 = host(cs[0]), host(ce[0]), host(starts[0])
                if None not in (a, b, s0) and not (a < b <= s0):
                    self.emit("X-POS-14", P, None, "pos.event", "cool_start < cool_end ≤ scan_start 아님")
        if len(starts) != 1 or len(ends) != 1:
            self.emit("X-POS-09", P, None, "pos.event", f"scan_start {len(starts)}, scan_end {len(ends)}")
            return
        S, E = host(starts[0]), host(ends[0])
        if S is None or E is None:
            return
        if S >= E or rows.index(starts[0]) > rows.index(ends[0]):
            self.emit("X-POS-09", P, None, "pos.event", "scan_end가 scan_start보다 먼저")
            return
        if g("timing") == "layer":
            rs = [i for i, r in enumerate(rows) if r["event"] == "resume"]
            ie = rows.index(ends[0])
            if len(rs) > 1 or any(i < ie for i in rs) or any(host(rows[i]) is not None and host(rows[i]) < E for i in rs):
                self.emit("X-POS-13", P, None, "pos.event", f"resume {len(rs)}개")
        if g("scan_start_t_ns") is not None and g("scan_start_t_ns") != S:
            self.emit("X-MET-12", M, None, "meta.scan_start_t_ns", g("scan_start_t_ns"))
        if g("scan_y0_mm") is not None and starts[0]["y_mm"] is not None and abs(g("scan_y0_mm") - starts[0]["y_mm"]) > 0.01 + 1e-9:
            self.emit("X-MET-18", M, None, "meta.scan_y0_mm", g("scan_y0_mm"))
        seg = [r for r in rows if host(r) is not None and S <= host(r) <= E]
        xs = [r["x_mm"] for r in seg if r["x_mm"] is not None]
        if xs and max(xs) - min(xs) > 0.01 + 1e-9:
            self.emit("X-POS-03", P, None, "pos.x_mm", f"{min(xs)}~{max(xs)}")
        if xs and g("scan_x_mm") is not None and abs(sum(xs) / len(xs) - g("scan_x_mm")) > 0.01 + 1e-9:
            self.emit("X-MET-17", M, None, "meta.scan_x_mm", g("scan_x_mm"))
        bysrc: dict = {}
        for r in sorted(seg, key=host):
            if r["y_mm"] is not None:
                bysrc.setdefault(r["source"], []).append(r["y_mm"])
        for src, ys in bysrc.items():
            d = [b - a for a, b in zip(ys, ys[1:])]
            if not (all(v >= 0 for v in d) or all(v <= 0 for v in d)):
                self.emit("X-POS-04", P, None, "pos.y_mm", f"source {src}")
        zs = [r["z_mm"] for r in seg if r["source"] == "cmd" and r["z_mm"] is not None]
        x["seg_z"] = zs
        if zs and max(zs) - min(zs) > 0.001 + 1e-9:
            self.emit("X-POS-05", P, None, "pos.z_mm", f"{min(zs)}~{max(zs)}")
        pas = [r["pass_idx"] for r in sorted(seg, key=host) if r["pass_idx"] is not None]
        if pas and (pas[0] != 0 or any(b - a not in (0, 1) for a, b in zip(pas, pas[1:]))):
            self.emit("X-POS-12", P, None, "pos.pass_idx", ",".join(map(str, pas[:20])))
        es = [r["e_mm"] for r in seg if r["e_mm"] is not None]
        if es and max(es) != min(es):
            self.emit("X-POS-06", P, None, "pos.e_mm", f"{min(es)}~{max(es)}")
        fe = [r["feed_mm_s"] for r in seg if r["feed_mm_s"] is not None]
        if fe and g("scan_speed_mm_s"):
            if abs(sum(fe) / len(fe) - g("scan_speed_mm_s")) > 0.05 * g("scan_speed_mm_s") + 1e-12:
                self.emit("X-POS-07", P, None, "pos.feed_mm_s", sum(fe) / len(fe))

    def _session_cross(self, sid, s, scans, srefs):
        sbase = f"sessions/{sid}"
        metas = [x for x in scans if x["meta"]]
        by_id = {x["meta"].get("scan_id"): x for x in metas if x["meta"].get("scan_id")}
        # post 정확히 1개 (FILE-04)
        for sr, layers in sorted(s["specreps"].items()):
            n = sum(1 for x in metas if x["sr"] == sr and x["meta"].get("timing") == "post" and x["meta"].get("scan_pass_idx") in (0, None))
            if n != 1:
                self.emit("FILE-04", f"{sbase}/{sr}", None, "meta.timing", str(n))
        # 줄 번호 (scan_pass_idx): 같은 시편·반복·층 (post끼리) 안에서 0부터 빈 번호 없이
        passes: dict = {}
        for x in metas:
            m = x["meta"]
            if m.get("scan_pass_idx") is None or m.get("timing") is None:
                continue
            key = (x["sr"], "post" if m["timing"] == "post" else m.get("layer_idx"))
            passes.setdefault(key, []).append(m["scan_pass_idx"])
        for (sr, lay), ps in sorted(passes.items(), key=str):
            if sorted(ps) != list(range(len(ps))):
                self.emit("X-MET-55", f"{sbase}/{sr}", None, "meta.scan_pass_idx", f"{lay}: {sorted(ps)}")
        # 모든 층 스캔 (D-18, 판정 거부 X7). D-21 대기라 기본 끔 (W-MET-56)
        for sr in sorted(s["specreps"]):
            ins = [x["meta"] for x in metas if x["sr"] == sr and x["meta"].get("thermal_state") == "in_process"]
            counts = {m.get("layer_count") for m in ins if m.get("layer_count") is not None}
            if ins and len(counts) == 1:
                have = {m.get("layer_idx") for m in ins}
                miss = [i for i in range(next(iter(counts))) if i not in have]
                if miss:
                    self.emit("W-MET-56", f"{sbase}/{sr}", None, "meta.layer_idx", f"빠진 층 {miss[:20]}")
        # 세션 기준 (bed_bare)
        bed = [(rid, r) for rid, ref in srefs.items() for r in ref["rows"] if r["kind"] == "bed_bare"]
        layer_scans = [x for x in metas if x["meta"].get("timing") == "layer" and x["meta"].get("layer_idx") is not None]
        if metas:
            first_end = None
            if layer_scans:
                mi = min(x["meta"]["layer_idx"] for x in layer_scans)
                ends = [x["meta"]["layer_end_t_ns"] for x in layer_scans if x["meta"]["layer_idx"] == mi and x["meta"].get("layer_end_t_ns") is not None]
                first_end = min(ends) if ends else None
            if not bed:
                self.emit("X-REF-02", f"{sbase}/reference", None, "ref.kind", "bed_bare 없음")
            elif first_end is not None:
                # v1.0: 줄마다 bed_bare가 있으므로 하나하나 출력 전이어야 함
                for rid_, r in bed:
                    if r["t_start_ns"] is not None and r["t_start_ns"] >= first_end:
                        self.emit("X-REF-02", f"{sbase}/reference/{rid_}/ref_index.csv", None, "ref.t_start_ns", "첫 층보다 늦음")
            # v1.0: bed_bare 줄 번호는 0부터 빈 번호 없이, 스캔 줄 번호 최댓값까지 (X-REF-21)
            bps = {r["scan_pass_idx"] for _, r in bed if r["scan_pass_idx"] is not None}
            sps = [x["meta"]["scan_pass_idx"] for x in metas if isinstance(x["meta"].get("scan_pass_idx"), int)]
            if bed and (bps != set(range(len(bps))) or (sps and max(sps) >= len(bps))):
                self.emit("X-REF-21", f"{sbase}/reference", None, "ref.scan_pass_idx", f"bed_bare {sorted(bps)}, 스캔 최대 {max(sps) if sps else '-'}")
            if first_end is not None:
                for rid, ref in srefs.items():
                    for r in ref["rows"]:
                        if r["kind"] == "feeler" and r["t_start_ns"] is not None and r["t_start_ns"] >= first_end:
                            self.emit("X-REF-10", f"{ref['base']}/ref_index.csv", None, "ref.t_start_ns", r["t_start_ns"])
        bed_ids = {r["ref_id"] for _, r in bed}
        bed_rows = {r["ref_id"]: r for _, r in bed}
        for key, rid in (("z_offset_mm", "X-MET-27"), ("bed_mesh_file", "X-MET-32")):
            vals = {json.dumps(x["meta"].get(key)) for x in metas if x["meta"].get(key) is not None}
            if len(vals) > 1:
                self.emit(rid, sbase, None, f"meta.{key}", ",".join(sorted(vals)))
        # v1.0: bed_ref_id는 같은 scan_pass_idx끼리 같은 값 (줄마다 bed_bare)
        bypass: dict = {}
        for x in metas:
            m = x["meta"]
            if m.get("bed_ref_id") is not None:
                bypass.setdefault(m.get("scan_pass_idx"), set()).add(m["bed_ref_id"])
        for p, vals in sorted(bypass.items(), key=str):
            if len(vals) > 1:
                self.emit("X-MET-26", sbase, None, "meta.bed_ref_id", f"줄 {p}: {','.join(sorted(vals))}")
        all_refs = []
        for rid, ref in srefs.items():
            for r in ref["rows"]:
                all_refs.append((ref, r, None))
        for x in scans:
            for rid, ref in x["refs"].items():
                for r in ref["rows"]:
                    all_refs.append((ref, r, x))
        self.all_scans += metas
        self.all_ref_rows += [r for _, r, _x in all_refs]
        # 같은 시편·반복·층 (post끼리) 묶음과 그 첫 줄 스캔 (scan_pass_idx 0)
        groups_lp: dict = {}
        for x in metas:
            m = x["meta"]
            if m.get("timing") in ("layer", "post"):
                groups_lp.setdefault((x["sr"], "post" if m["timing"] == "post" else m.get("layer_idx")), []).append(x)
        first_of = {k: next((y for y in v if y["meta"].get("scan_pass_idx") == 0), None) for k, v in groups_lp.items()}

        def base_of(x):
            m = x["meta"]
            return first_of.get((x["sr"], "post" if m.get("timing") == "post" else m.get("layer_idx")))

        cal_ids = set(self.cal_dirs)
        for x in metas:
            m, M = x["meta"], f"{x['base']}/meta.json"
            if m.get("bed_ref_id") is not None and m["bed_ref_id"] not in bed_ids:
                self.emit("X-MET-25", M, None, "meta.bed_ref_id", m["bed_ref_id"])
            elif m.get("bed_ref_id") is not None and isinstance(m.get("scan_pass_idx"), int):
                br = bed_rows[m["bed_ref_id"]]
                if br["scan_pass_idx"] is not None and br["scan_pass_idx"] != m["scan_pass_idx"]:
                    self.emit("X-MET-64", M, None, "meta.bed_ref_id", f"{m['bed_ref_id']} 줄 {br['scan_pass_idx']} ≠ {m['scan_pass_idx']}")
            zr = m.get("zero_ref_method")
            # 층 기준은 그 층 첫 줄 스캔과 짝 (v1.0): 다른 줄 스캔은 첫 줄 스캔의 짝 기준을 봄
            b = base_of(x) or x
            bid = b["meta"].get("scan_id")
            pairs = {r["kind"] for _, r, _x in all_refs if r["scan_id"] is not None and r["scan_id"] == bid}
            if zr == "bed_marker":
                if (m.get("layer_z_mm") is not None and m["layer_z_mm"] > 8.0) or "bed_marker" not in pairs:
                    self.emit("X-MET-29", M, None, "meta.zero_ref_method", zr)
            if zr == "ref_tower" and "ref_tower" not in pairs:
                self.emit("X-MET-30", M, None, "meta.zero_ref_method", zr)
            if zr == "step_gauge" and "step_gauge" not in pairs:
                self.emit("X-MET-62", M, None, "meta.zero_ref_method", zr)
            # X4 (D-21 채택, 기본 켬, WARN): bed_bare 기준의 교정 ID = 이 스캔 교정 ID
            if m.get("bed_ref_id") is not None and m.get("calibration_id") is not None:
                for _rid, r in bed:
                    if r["ref_id"] == m["bed_ref_id"] and r["calibration_id"] is not None and r["calibration_id"] != m["calibration_id"]:
                        self.emit("W-REF-11", M, None, "meta.calibration_id", f"{m['calibration_id']} ≠ {r['calibration_id']}")
            if m.get("mesh_enabled") is True and m.get("bed_mesh_file") is not None:
                if not m["bed_mesh_file"].startswith("printer/") or m["bed_mesh_file"][len("printer/"):] not in s["printer"]:
                    self.emit("FILE-14", M, None, "meta.bed_mesh_file", m["bed_mesh_file"])
            if m.get("paired_scan_id") is not None:
                y = by_id.get(m["paired_scan_id"])
                ok = (y is not None and y["sr"] == x["sr"] and y["meta"].get("thermal_state") == "in_process"
                      and m.get("layer_count") is not None and y["meta"].get("layer_idx") == m["layer_count"] - 1
                      and y["meta"].get("scan_pass_idx") == m.get("scan_pass_idx"))  # v1.0: 같은 줄 번호끼리 짝
                if not ok:
                    self.emit("X-MET-33", M, None, "meta.paired_scan_id", m["paired_scan_id"])
            cid = m.get("calibration_id")
            if cid is not None:
                if cid not in cal_ids:
                    self.emit("X-MET-48", M, None, "meta.calibration_id", cid)
                else:
                    dt = _iso(m.get("datetime"))
                    crs = self.cal_rows.get(cid, [])
                    if dt:
                        for r in crs:
                            a = _iso(r.get("valid_from")) if r.get("valid_from") else None
                            b = _iso(r.get("valid_until")) if r.get("valid_until") else None
                            if (a and dt < a) or (b and dt >= b):
                                self.emit("X-MET-49", M, None, "meta.datetime", m.get("datetime"))
                                break
                    if any(r.get("invalidated_by") not in (None, "none") for r in crs):
                        self.emit("W-CAL-13", M, None, "meta.calibration_id", cid)
        # 층 순서 (세션·시편·반복 안)
        groups: dict = {}
        for x in layer_scans:
            groups.setdefault(x["sr"], []).append(x)
        for sr, xs in groups.items():
            xs = sorted(xs, key=lambda y: y["meta"]["layer_idx"])
            for a, b in zip(xs, xs[1:]):
                ma, mb = a["meta"], b["meta"]
                if ma["layer_idx"] < mb["layer_idx"] and ma.get("layer_z_mm") is not None and mb.get("layer_z_mm") is not None \
                        and not mb["layer_z_mm"] > ma["layer_z_mm"]:
                    self.emit("X-MET-07", f"{b['base']}/meta.json", None, "meta.layer_z_mm", mb["layer_z_mm"])
                if mb["layer_idx"] == ma["layer_idx"] + 1 and ma.get("gcode_line_end") is not None and mb.get("gcode_line_start") is not None \
                        and not ma["gcode_line_end"] < mb["gcode_line_start"]:
                    self.emit("X-MET-10", f"{a['base']}/meta.json", None, "meta.gcode_line_end", ma["gcode_line_end"])
        # 기준 ↔ 스캔
        last_peak: dict = {}
        for ref, r, owner in sorted(all_refs, key=lambda t: (t[1]["t_start_ns"] is None, t[1]["t_start_ns"] or 0)):
            Rp = f"{ref['base']}/ref_index.csv"
            y = by_id.get(r["scan_id"]) if r["scan_id"] is not None else None
            if owner is not None and owner["meta"] and r["scan_id"] is not None and r["scan_id"] != owner["meta"].get("scan_id"):
                self.emit("X-REF-08", Rp, None, "ref.scan_id", r["scan_id"])
            if y is not None:
                ym = y["meta"]
                if r["kind"] == "bed_marker" and ym.get("layer_z_mm") is not None and ym["layer_z_mm"] > 8.0:
                    self.emit("X-REF-03", Rp, None, "ref.scan_id", r["scan_id"])
                if r["layer_idx"] is not None and ym.get("layer_idx") is not None and r["layer_idx"] != ym["layer_idx"]:
                    self.emit("X-REF-04", Rp, None, "ref.layer_idx", r["layer_idx"])
                if r["t_start_ns"] is not None and y["frames"] and y["frames"][0]["t_host_ns"] is not None:
                    if abs(r["t_start_ns"] - y["frames"][0]["t_host_ns"]) > 600e9:
                        self.emit("X-REF-07", Rp, None, "ref.t_start_ns", r["t_start_ns"])
                if r["kind"] == "step_gauge":
                    # v1.0: x ≤ 짝 스캔 layer_z_mm (같은 높이 허용, 4절 C2)
                    if r["gauge_height_mm"] is not None and ym.get("layer_z_mm") is not None and r["gauge_height_mm"] > ym["layer_z_mm"] + 1e-12:
                        self.emit("X-REF-15", Rp, None, "ref.gauge_height_mm", r["gauge_height_mm"])
                # v1.0: 층 기준의 짝 스캔은 그 층 첫 줄 (scan_pass_idx = 0)
                if r["kind"] in LAYER_REFS and ym.get("scan_pass_idx") not in (None, 0):
                    self.emit("X-REF-24", Rp, None, "ref.scan_id", r["scan_id"])
            # 기준물 ID · 높이 ↔ 교정 (같은 캠페인 cal_manifest.csv). GB-00 (베드 면)은 cal 행 없음 (높이 0은 X-REF-23)
            gb = r["gauge_block_id"]
            if gb is not None and gb != "GB-00" and r["kind"] in ("step_gauge", "feeler"):
                crs = [c for rows_ in self.cal_rows.values() for c in rows_ if c.get("gauge_block_id") == gb]
                if not crs:
                    self.emit("X-REF-12", Rp, None, "ref.gauge_block_id", gb)
                elif r["gauge_height_mm"] is not None:
                    # v1.0: 높이 출처는 ID 접두로 (GB- 블록 → gauge_block_height_mm, FG- → gauge_measured_mm)
                    key = "gauge_block_height_mm" if gb.startswith("GB-") else "gauge_measured_mm"
                    vals = [c[key] for c in crs if c.get(key) is not None]
                    if vals and not any(abs(v - r["gauge_height_mm"]) <= 1e-9 for v in vals):
                        self.emit("X-REF-14", Rp, None, "ref.gauge_height_mm", r["gauge_height_mm"])
            if r["line_peak_pct"] is not None and r["kind"] is not None:
                p = last_peak.get(r["kind"])
                if p is not None and r["line_peak_pct"] < 0.8 * p:
                    self.emit("W-REF-09", Rp, None, "ref.line_peak_pct", r["line_peak_pct"])
                last_peak[r["kind"]] = r["line_peak_pct"]
        self._session_v10(sid, sbase, metas, by_id, all_refs, bed, groups_lp, first_of)
        # 기준 프레임 색인
        for ref, r, owner in all_refs:
            base = ref["base"]
            files = [p[len(base) + 1:] for p in self.paths if p.startswith(base + "/")]
            meta = owner["meta"] if owner and owner["meta"] else (metas[0]["meta"] if metas else None)
            self.check_frames(base, files, ref["frames"], meta, r["scan_id"] if r["scan_id"] is not None else "S00_r00",
                              r["layer_idx"] if r["layer_idx"] is not None else -1, False, f"{base}/frames_index.csv")


    def _session_v10(self, sid, sbase, metas, by_id, all_refs, bed, groups_lp, first_of):
        """v1.0 (T1 3차, LM-T14-3) 세션 규칙: 두 단 · 같은 Z (행마다) · post 줄 집합 · ref_id 순번 · 줄마다 bed_bare."""
        # post 줄 번호 집합 = 마지막 층 timing = layer 스캔의 줄 번호 집합 (X-MET-65)
        for sr in sorted({x["sr"] for x in metas}):
            ms = [x["meta"] for x in metas if x["sr"] == sr]
            lc = {m.get("layer_count") for m in ms if isinstance(m.get("layer_count"), int)}
            if len(lc) != 1:
                continue
            last = next(iter(lc)) - 1
            lp = {m.get("scan_pass_idx") for m in ms if m.get("timing") == "layer" and m.get("layer_idx") == last}
            pp = {m.get("scan_pass_idx") for m in ms if m.get("timing") == "post"}
            if lp and pp and lp != pp:
                self.emit("X-MET-65", f"{sbase}/{sr}", None, "meta.scan_pass_idx",
                          f"post {sorted(pp, key=str)} ≠ 층 {last} {sorted(lp, key=str)}")
        # ref_id: 세션 안 유일 (X-REF-19), 같은 약어 안 001부터 빈 번호 없이 t_start_ns 순서 (X-REF-18)
        seen: dict = {}
        byab: dict = {}
        for ref, r, _o in all_refs:
            rid = r["ref_id"]
            if rid is None:
                continue
            seen.setdefault(rid, []).append(ref["base"])
            m = re.match(r"^REF-([A-Z]{3})-(\d+)$", rid)
            if m:
                byab.setdefault(m.group(1), []).append((r["t_start_ns"], int(m.group(2))))
        for rid, bases in sorted(seen.items()):
            if len(bases) > 1:
                self.emit("X-REF-19", f"{bases[1]}/ref_index.csv", None, "ref.ref_id", rid)
        for ab, items in sorted(byab.items()):
            nums = [n for _t, n in sorted(items, key=lambda t: (t[0] is None, t[0] or 0, t[1]))]
            if nums != list(range(1, len(nums) + 1)):
                self.emit("X-REF-18", sbase, None, "ref.ref_id", f"REF-{ab}: {nums[:20]}")
        # 줄마다 bed_bare: 기준 위치 로그 스캔 구간 x 평균 = 그 기준을 가리키는 스캔의 scan_x_mm (X-REF-22)
        for ref, r, _o in all_refs:
            if r["kind"] != "bed_bare" or not ref["pos"]:
                continue
            xs = [p["x_mm"] for p in scan_segment(ref["pos"]) if p["x_mm"] is not None]
            if not xs:
                continue
            mx = sum(xs) / len(xs)
            for x in metas:
                m = x["meta"]
                if m.get("bed_ref_id") == r["ref_id"] and m.get("scan_x_mm") is not None and abs(mx - m["scan_x_mm"]) > 0.01 + 1e-9:
                    self.emit("X-REF-22", f"{ref['base']}/position_log.csv", None, "pos.x_mm", f"{mx:.4f} vs {m['scan_x_mm']}")
                    break
        # 두 단 규칙 (X-REF-20)과 같은 Z 행마다 (X-REF-16): 층 (post 포함)마다 첫 줄 스캔 기준
        for key, xs in sorted(groups_lp.items(), key=str):
            b = first_of.get(key)
            if b is None:
                continue
            bm = b["meta"]
            bid = bm.get("scan_id")
            stg = [(ref, r) for ref, r, _o in all_refs if r["kind"] == "step_gauge" and r["scan_id"] is not None and r["scan_id"] == bid]
            if bm.get("zero_ref_method") == "step_gauge" and stg:
                z = bm.get("layer_z_mm")
                hs = [r["gauge_height_mm"] for _, r in stg]
                ids = [r["gauge_block_id"] for _, r in stg]
                bad = None
                if len(stg) != 2:
                    bad = f"step_gauge {len(stg)}행 (2행이어야 함)"
                elif ids[0] is not None and ids[0] == ids[1]:
                    bad = f"두 단 ID가 같음 {ids[0]}"
                elif None not in hs:
                    h1, h2 = max(hs), min(hs)
                    if not (0 < h1 - h2 <= 3.04 + 1e-9):
                        bad = f"h1 − h2 = {h1 - h2:.4f} (0 < 차 ≤ 3.04)"
                    elif z is not None and (h1 > z + 1e-12 or z - h2 > 8.0 + 1e-9):
                        bad = f"h1 {h1}, h2 {h2}, 층 Z {z} (h1 ≤ Z, Z − h2 ≤ 8.0)"
                if bad:
                    self.emit("X-REF-20", f"{b['base']}/meta.json", None, "ref.kind", bad)
                elif len(stg) == 2 and None not in hs and z is not None:
                    self._two_step_ratio(b, [r for _, r in stg], z)
            if stg or bm.get("zero_ref_method") == "step_gauge":
                bz = scan_segment_z(b["pos"])
                if not bz:
                    continue
                z0 = sum(bz) / len(bz)
                logs = [(f"{y['base']}/position_log.csv", y["pos"]) for y in xs if y is not b] + \
                       [(f"{ref['base']}/position_log.csv", ref["pos"]) for ref, _r in stg]
                for P, rows in logs:
                    for zz in scan_segment_z(rows):
                        if abs(zz - z0) > 0.001 + 1e-9:
                            self.emit("X-REF-16", P, None, "pos.z_mm", f"{zz} vs 기준 {z0:.4f}")
                            break

    def _gauge_u_um(self, r) -> float | None:
        """두 단 한 단의 교정 표준불확도 (µm). GB- 블록 = cal.gauge_block_u_um, FG- 잎 = cal.gauge_u_um, GB-00 · 모르면 None.

        같은 ID cal 행이 여럿이면 그 기준의 교정 ID (`ref.calibration_id`) 행을 먼저 쓰고, 값이 여럿이면 큰 값 (엄한 쪽).
        """
        gid = r["gauge_block_id"]
        if not isinstance(gid, str) or gid == "GB-00" or not gid.startswith(("GB-", "FG-")):
            return None
        key = "gauge_block_u_um" if gid.startswith("GB-") else "gauge_u_um"
        own = self.cal_rows.get(r["calibration_id"], []) if r["calibration_id"] is not None else []
        for rows in (own, [c for rows_ in self.cal_rows.values() for c in rows_]):
            vals = [c[key] for c in rows if c.get("gauge_block_id") == gid and isinstance(c.get(key), (int, float))
                    and not isinstance(c.get(key), bool) and math.isfinite(c[key])]
            if vals:
                return max(vals)
        return None

    def _two_step_ratio(self, b, pair: list[dict], z: float):
        """두 단 비 경고 (W-REF-25, 명세 v1.1 4절): d ÷ (h1 − h2) ≤ 4 µm ÷ √(2σ² + 2u²).

        두 단 규칙 (X-REF-20)을 통과한 층 (post 포함)만 부른다. d = 층 Z − h1, σ = 1.5 µm (고정),
        u = 두 단 교정 표준불확도 중 큰 값 (GB-00은 cal 행이 없어 다른 단 값). u를 하나도 모르면 보지 않음 (X-REF-12가 잡음).
        """
        hi, lo = (pair[0], pair[1]) if pair[0]["gauge_height_mm"] >= pair[1]["gauge_height_mm"] else (pair[1], pair[0])
        h1, h2 = hi["gauge_height_mm"], lo["gauge_height_mm"]
        us = [u for u in (self._gauge_u_um(hi), self._gauge_u_um(lo)) if u is not None]
        if not us or h1 - h2 <= 0:
            return
        u = max(us)
        limit = TWO_STEP_LIMIT_UM / math.sqrt(2 * TWO_STEP_SIGMA_UM ** 2 + 2 * u ** 2)
        ratio = (z - h1) / (h1 - h2)
        if ratio > limit + 1e-9:
            self.emit("W-REF-25", f"{b['base']}/meta.json", None, "ref.gauge_height_mm",
                      f"층 Z {z}, h1 {h1} ({hi['gauge_block_id']}), h2 {h2} ({lo['gauge_block_id']}), u {u} µm: "
                      f"비 {ratio:.4f} > 문턱 {limit:.4f}")


def _host_t(r):
    """위치 로그 행의 호스트 시계 시각 (mcu는 clock_offset_ns를 더함). 모르면 None."""
    if r["t_ns"] is None:
        return None
    if r["clock"] == "host":
        return r["t_ns"]
    if r["clock"] == "mcu" and r["clock_offset_ns"] is not None:
        return r["t_ns"] + r["clock_offset_ns"]
    return None


def scan_segment(rows: list[dict]) -> list[dict]:
    """위치 로그의 스캔 구간 (scan_start ~ scan_end, 호스트 시각) 행. 구간 표시가 없으면 모든 행."""
    starts = [r for r in rows if r["event"] == "scan_start"]
    ends = [r for r in rows if r["event"] == "scan_end"]
    if len(starts) == 1 and len(ends) == 1 and _host_t(starts[0]) is not None and _host_t(ends[0]) is not None:
        S, E = _host_t(starts[0]), _host_t(ends[0])
        return [r for r in rows if _host_t(r) is not None and S <= _host_t(r) <= E]
    return list(rows)


def scan_segment_z(rows: list[dict]) -> list[float]:
    """위치 로그의 스캔 구간 명령 Z (source = cmd). report · plan · steps 행은 쓰지 않음 (명세 4절)."""
    return [r["z_mm"] for r in scan_segment(rows) if r["source"] == "cmd" and r["z_mm"] is not None]


def summarize(findings: list[Finding]) -> dict:
    err = [f for f in findings if f.severity == "ERROR"]
    warn = [f for f in findings if f.severity == "WARN"]
    return {"n_error": len(err), "n_warn": len(warn), "rule_ids": sorted({f.rule_id for f in findings})}


def findings_to_json(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
