"""층별 판정 영역 (RegionStack) 만들기 (RG5 – RG12).

build_region은 G코드 (ParseResult) · 정답 지도 (RefStack) · 설정만 받는다. 측정값을 받는 인자가 없다 (MF-JDG-03).

이유 비트 (uint8, 겹침 허용) → T15 코드 (int8, 칸마다 하나, §6.2 우선순위):
  출력물 없는 칸: PRIME이 덮으면 4, 아니면 5.
  출력물 있는 칸: type (4) > fov (3) > depth (6) > occlusion (2) > edge (1). 이유가 없으면 영역 칸, 코드 0.
  depth는 T15 코드표 6 "심도 밖" (J-2, 7ae82ce). 처음 판은 9 (기타)였음 (팀장검증 5차 R-3).

식힌 재측정 비교 영역 (post_region, 팀장검증 5차 R-2): 마지막 층 비트에서 엣지 비트만 좁은 띠
(max(2·res, α·반폭·ΔT) [추정])로 바꾼 것. type · fov · depth · occlusion · 출력물 없음은 그대로 뺀다.
좁은 띠로도 0칸이면 엣지를 빼지 않는다 (P-A, 규칙 이름을 info["post_rule"]에 남김). 판정 영역 (region)은 그대로.
"""
from __future__ import annotations

import json
import math
import time
from fractions import Fraction

import numpy as np
import pandas as pd

from cvlab.gcode import GCodeError
from cvlab.judge import JudgeParams, LayerInput
from cvlab.judge.aggregate import cell_factor

from .coverage import coverage_mask, pass_counts, plan_passes
from .grid import is_aligned, object_bbox
from .masks import edge_band, edge_band_update, grow, predict_occlusion, prime_mask
from .params import RegionParams

REASON_BITS = {"edge": 1, "occlusion": 2, "fov": 4, "type": 8, "no_material": 16, "depth": 32, "prime": 64}
REASON_CODE = {"edge": 1, "occlusion": 2, "fov": 3, "type": 4, "no_material": 5, "depth": 6, "prime": 4}
POST_RULE_NARROW = "P-B 좁은 엣지 띠"
POST_RULE_EDGE_IN = "P-A 엣지 포함"
# 출력물 있는 칸의 우선순위 (앞이 이김)
MATERIAL_PRIORITY = ("type", "fov", "depth", "occlusion", "edge")
SUMMARY_COLUMNS = ["layer_idx", "layer_z_mm", "n_material", "n_region", "region_pct",
                   "bit_edge", "bit_occlusion", "bit_fov", "bit_type", "bit_depth", "bit_prime",
                   "code_1", "code_2", "code_3", "code_4", "code_5", "code_6",
                   "n_region_cell02", "n_region_cell04"]
PLAN_COLUMNS = ["layer_idx", "layer_z_mm", "spread_mm", "n_heights", "depth_pct", "recover_cells_B",
                "extra_scan_s_B"]
_B = REASON_BITS
_N_BITS = 7
_V = np.arange(128)
_MAT_V = (_V & _B["no_material"]) == 0
_OBJ_V = _MAT_V & ((_V & _B["type"]) == 0)


def codes_from_bits(bits) -> np.ndarray:
    """이유 비트 → T15 주 코드 (§6.2 우선순위)."""
    b = np.asarray(bits, np.uint8)
    code = np.zeros(b.shape, np.int8)
    nomat = (b & _B["no_material"]) > 0
    for name in reversed(MATERIAL_PRIORITY):  # 낮은 우선순위부터 칠해 높은 것이 덮음
        code[((b & _B[name]) > 0) & ~nomat] = REASON_CODE[name]
    code[nomat] = REASON_CODE["no_material"]
    code[nomat & ((b & _B["prime"]) > 0)] = REASON_CODE["prime"]
    return code


_CODE_LUT = codes_from_bits(np.arange(128, dtype=np.uint8))


def _edge_width(result) -> float:
    hw = result.header.get("line_widths") or {}
    for key in ("WALL-OUTER", "DEFAULT"):
        if hw.get(key):
            return float(hw[key])
    p = result.params
    if p is not None and p.line_width_mm:
        return float(p.line_width_mm)
    raise GCodeError("엣지 띠 선폭을 모름: 머리말 WALL-OUTER · DEFAULT 없고 config line_width_mm도 비어 있음")


def auto_band_step(result, res_mm: float) -> tuple:
    """(edge_band_mm, step_mm) 자동값: 외벽 선폭/2 + 2·res, 최소 층 높이/2 (E2 §4)."""
    band = _edge_width(result) / 2.0 + 2.0 * res_mm
    lh = result.layers["layer_h_mm"].to_numpy(float)
    lh = lh[np.isfinite(lh) & (lh > 0)]
    if lh.size == 0:
        raise GCodeError("층 높이를 모름 (step_mm 자동값을 못 정함)")
    return round(band, 9), round(float(lh.min()) / 2.0, 9)


def _same(a, b) -> bool:
    return Fraction(str(float(a))) == Fraction(str(float(b)))


class RegionStack:
    def __init__(self, grid: dict, z_layers, bits: list, passes: list, params: RegionParams,
                 info: dict, stats: list, post_edge=None):
        self.grid = dict(grid)
        # 마지막 층 post 엣지 띠 (출력물 칸만, P-A면 모두 False). None = 옛 저장 파일 (R-2 전)
        self._post_edge = None if post_edge is None else np.asarray(post_edge, bool)
        self.z_layers = np.asarray(z_layers, float)
        self._bits = bits
        self.passes = [dict(p) for p in passes]
        self.params = params
        self.info = dict(info)
        self._stats = [dict(s) for s in stats]
        self._shape = (grid["ny"], grid["nx"])

    @property
    def n_layers(self) -> int:
        return len(self.z_layers)

    def _check(self, n: int) -> None:
        if not (0 <= n < self.n_layers):
            raise IndexError(f"층 번호 {n} 범위 밖 (0–{self.n_layers - 1})")

    def reasons(self, n: int) -> np.ndarray:
        self._check(n)
        return self._bits[n].copy()

    def region(self, n: int) -> np.ndarray:
        self._check(n)
        return self._bits[n] == 0

    def exclusion_code(self, n: int) -> np.ndarray:
        self._check(n)
        return codes_from_bits(self._bits[n])

    # ---- 식힌 재측정 비교 영역 (R-2)
    def post_reasons(self) -> np.ndarray:
        """마지막 층 이유 비트에서 엣지 비트만 좁은 띠 (P-B) 또는 없음 (P-A)으로 바꾼 것."""
        if self._post_edge is None:
            raise ValueError("post 엣지 띠가 없음 (R-2 전 저장 파일). build_region으로 다시 만들 것")
        b = self._bits[self.n_layers - 1] & np.uint8(~_B["edge"] & 0xFF)
        return b | self._post_edge.view(np.uint8)

    def post_region(self) -> np.ndarray:
        """식힌 재측정 비교 영역 (bool, 격자 모양). 판정 영역 region(마지막 층)을 포함한다."""
        return self.post_reasons() == 0

    def post_exclusion_code(self) -> np.ndarray:
        """post_region 밖 칸의 T15 코드 (int8, 영역 안 0). 우선순위는 codes_from_bits와 같음."""
        return codes_from_bits(self.post_reasons())

    # ---- 표
    def summary(self) -> pd.DataFrame:
        rows = [{k: s[k] for k in SUMMARY_COLUMNS} for s in self._stats]
        tot = {k: int(sum(r[k] for r in rows)) for k in SUMMARY_COLUMNS[2:] if k != "region_pct"}
        tot.update(layer_idx=-1, layer_z_mm=float("nan"),
                   region_pct=(100.0 * tot["n_region"] / tot["n_material"]) if tot["n_material"] else float("nan"))
        df = pd.DataFrame(rows + [tot], columns=SUMMARY_COLUMNS)
        return df

    def depth_plan(self) -> pd.DataFrame:
        """caliper 처리안 비교 (§6.10). A안 = 심도 밖을 뺌, B안 = 높이를 나눠 스캔."""
        p = self.params
        per_height_s = sum((p.lead_in_mm + (q["y1_mm"] - q["y0_mm"])) / p.scan_speed_mm_s for q in self.passes)
        rows = []
        for s in self._stats:
            sp = s["spread_mm"]
            if sp is None or not np.isfinite(sp):
                nh = 1
            else:
                nh = max(1, math.ceil(Fraction(int(round(sp * 1e6)), int(round(p.dof_mm * 1e6)))))
            rows.append({"layer_idx": s["layer_idx"], "layer_z_mm": s["layer_z_mm"], "spread_mm": sp,
                         "n_heights": nh,
                         "depth_pct": (100.0 * s["n_depth_object"] / s["n_object"]) if s["n_object"] else 0.0,
                         "recover_cells_B": s["recover_cells_B"], "extra_scan_s_B": (nh - 1) * per_height_s})
        no = sum(s["n_object"] for s in self._stats)
        nd = sum(s["n_depth_object"] for s in self._stats)
        tot = {"layer_idx": -1, "layer_z_mm": float("nan"), "spread_mm": float("nan"),
               "n_heights": max((r["n_heights"] for r in rows), default=1),
               "depth_pct": (100.0 * nd / no) if no else 0.0,
               "recover_cells_B": int(sum(r["recover_cells_B"] for r in rows)),
               "extra_scan_s_B": float(sum(r["extra_scan_s_B"] for r in rows))}
        return pd.DataFrame(rows + [tot], columns=PLAN_COLUMNS)

    def layer_stats(self) -> list:
        return [dict(s) for s in self._stats]

    # ---- T15 연결
    def layer_input(self, n: int, delta_mm, thermal_state: str = "in_process") -> LayerInput:
        """cvlab.judge.LayerInput. 식힌 재측정 (cooled)은 마지막 층 번호로, 영역은 post_region (R-2)."""
        d = np.asarray(delta_mm, float)
        if d.shape != self._shape:
            raise ValueError(f"delta 모양 {d.shape} ≠ 격자 {self._shape}")
        if thermal_state == "cooled":
            if n != self.n_layers - 1:
                raise ValueError("식힌 재측정 (cooled)은 마지막 층 번호만 씀")
            return LayerInput(layer_idx=int(n), thermal_state=thermal_state, delta_mm=d,
                              region=self.post_region(), exclusion_code=self.post_exclusion_code())
        return LayerInput(layer_idx=int(n), thermal_state=thermal_state, delta_mm=d,
                          region=self.region(n), exclusion_code=self.exclusion_code(n))

    def post_input(self, delta_mm) -> LayerInput:
        """식힌 재측정 LayerInput (layer_idx = 마지막 층, thermal_state = cooled, region = post_region())."""
        return self.layer_input(self.n_layers - 1, delta_mm, thermal_state="cooled")

    # ---- 저장
    def save(self, path) -> None:
        size = self._shape[0] * self._shape[1]
        planes = np.zeros((self.n_layers, _N_BITS, (size + 7) // 8), np.uint8)
        for n, b in enumerate(self._bits):
            flat = b.ravel()
            for j in range(_N_BITS):
                planes[n, j] = np.packbits(((flat >> j) & 1).astype(bool))
        extra = {}
        if self._post_edge is not None:
            extra["post_edge"] = np.packbits(self._post_edge.ravel())
        np.savez_compressed(
            path, grid=np.array(json.dumps(self.grid)), z_layers=self.z_layers, planes=planes,
            passes=np.array(json.dumps(self.passes)), params=np.array(json.dumps(self.params.to_dict())),
            info=np.array(json.dumps(self.info, ensure_ascii=False)),
            stats=np.array(json.dumps(self._stats, ensure_ascii=False)), **extra)

    @classmethod
    def load(cls, path) -> "RegionStack":
        with np.load(path, allow_pickle=False) as d:
            grid = json.loads(str(d["grid"]))
            size = grid["ny"] * grid["nx"]
            planes = d["planes"]
            bits = []
            for n in range(planes.shape[0]):
                b = np.zeros(size, np.uint8)
                for j in range(_N_BITS):
                    b |= (np.unpackbits(planes[n, j], count=size).astype(np.uint8) << j)
                bits.append(b.reshape(grid["ny"], grid["nx"]))
            pe = None
            if "post_edge" in d.files:
                pe = np.unpackbits(d["post_edge"], count=size).astype(bool).reshape(grid["ny"], grid["nx"])
            return cls(grid, d["z_layers"], bits, json.loads(str(d["passes"])),
                       RegionParams.from_dict(json.loads(str(d["params"]))),
                       json.loads(str(d["info"])), json.loads(str(d["stats"])), post_edge=pe)


def region_cells(region, f: int, fill_min: float) -> int:
    """판정 칸 (f × f 고운 칸)으로 묶은 영역 칸 수. T15 aggregate_to_cells의 region_cell과 같은 규칙
    (가장자리 덜 찬 묶음은 버림, 영역 비율 ≥ fill_min을 분수로 비교). 시험으로 aggregate_to_cells와 대조."""
    r = np.asarray(region, bool)
    ny, nx = r.shape[0] // f, r.shape[1] // f
    if ny == 0 or nx == 0:
        return 0
    n_reg = r[: ny * f, : nx * f].reshape(ny, f, nx, f).sum(axis=(1, 3))
    fr = Fraction(str(fill_min))
    return int((n_reg * fr.denominator >= fr.numerator * (f * f)).sum())


def build_region(result, ref, params: RegionParams | None = None, passes=None) -> RegionStack:
    """G코드 · 정답 지도 · 설정만으로 층별 판정 영역을 만든다 (측정값 없음, MF-JDG-03)."""
    t0 = time.perf_counter()
    p = params or RegionParams()
    grid = ref.grid
    if not _same(grid["res_mm"], p.res_mm):
        raise ValueError(f"정답 지도 격자 res {grid['res_mm']} ≠ region res_mm {p.res_mm}")
    if result.params is not None and not _same(result.params.grid_res_mm, p.res_mm):
        raise ValueError(f"gcode grid_res_mm {result.params.grid_res_mm} ≠ region res_mm {p.res_mm}")
    res = float(grid["res_mm"])
    band_auto, step_auto = auto_band_step(result, res)
    band = p.edge_band_mm if p.edge_band_mm is not None else band_auto
    step = p.step_mm if p.step_mm is not None else step_auto
    bbox = object_bbox(result, p.exclude_types)
    if passes is None:
        passes = plan_passes(bbox, p.fov_mm, p.scan_len_mm, p.pass_overlap_mm, p.extend_scan_len)
    passes = [dict(q) for q in passes]
    cov = coverage_mask(grid, passes)
    prime, prime_info = prime_mask(result, grid)
    f02 = cell_factor(JudgeParams.cell_mm, res)
    f04 = cell_factor(JudgeParams.cell_mm_alt, res)
    fill = JudgeParams.region_fill_min  # D-20 R6 (1.0)
    z = ref.z_layers
    N = ref.n_layers
    shape = (grid["ny"], grid["nx"])

    top_final = np.full(shape, -1, np.int32)
    for k in range(N):
        top_final[ref.footprint(k)] = k

    top = np.full(shape, -1, np.int32)
    tcode = np.full(shape[0] * shape[1], -1, np.int16)
    own_codes = getattr(ref, "_type_codes", None)  # 읽기만. 없으면 공개 type_at (층 수 제곱만큼 느림)
    denom = np.zeros(shape, bool)
    covered = np.zeros(shape, bool)
    eb = None
    znm = np.rint(z * 1e6).astype(np.int64)
    ex_codes = np.array([i for i, t in enumerate(ref.type_names) if t.upper() in set(p.exclude_types)], np.int16)
    prime_u8 = prime.view(np.uint8)
    cov_out = ~cov
    bits_all, stats = [], []
    for n in range(N):
        fpn = ref.footprint(n)
        top[fpn] = n
        mat = top >= 0
        nomat = ~mat
        topc = np.clip(top, 0, None)
        h = np.where(mat, z[topc], np.nan)
        if own_codes is not None:
            tcode[np.flatnonzero(fpn.ravel())] = own_codes[n]  # type_at(n)과 같은 덮어쓰기 (시험으로 대조)
            tc = tcode.reshape(shape)
        else:
            tc = ref.type_at(n)
        tm = (np.isin(tc, ex_codes) if ex_codes.size else np.zeros(shape, bool)) & mat
        # 심도 밖: depth_out(h, z_n, dof, top)과 같은 식을 층 번호로 (nm 정수 비교, 시험으로 대조)
        lo = int(np.rint((z[n] + p.dof_top_mm - p.dof_mm) * 1e6))
        hi = int(np.rint((z[n] + p.dof_top_mm) * 1e6))
        dep = ((znm < lo) | (znm > hi))[topc] & mat
        occ = grow(predict_occlusion(h, res, p.theta_deg, p.camera_side), p.occlusion_grow_cells) & mat
        eb = edge_band_update(h, eb, fpn, res, band, step)  # edge_band(h)와 같음 (시험으로 대조)
        b = (nomat.view(np.uint8) << 4)
        b |= (nomat.view(np.uint8) & prime_u8) << 6
        b |= tm.view(np.uint8) << 3
        b |= (mat & cov_out).view(np.uint8) << 2
        b |= dep.view(np.uint8) << 5
        b |= occ.view(np.uint8) << 1
        b |= (eb & mat).view(np.uint8)
        bits_all.append(b)

        region = b == 0
        cnt = np.bincount(b.ravel(), minlength=128)
        s = {"layer_idx": n, "layer_z_mm": float(z[n]), "n_material": int(cnt[_MAT_V].sum()),
             "n_region": int(cnt[0])}
        s["region_pct"] = 100.0 * s["n_region"] / s["n_material"] if s["n_material"] else float("nan")
        for name in ("edge", "occlusion", "fov", "type", "depth"):
            s[f"bit_{name}"] = int(cnt[_MAT_V & ((_V & _B[name]) > 0)].sum())
        s["bit_prime"] = int(cnt[(_V & _B["prime"]) > 0].sum())  # 퍼지선은 출력물 없는 칸에만 있음
        for c in (1, 2, 3, 4, 5, 6):
            s[f"code_{c}"] = int(cnt[_CODE_LUT == c].sum())
        s["n_region_cell02"] = region_cells(region, f02, fill)
        s["n_region_cell04"] = region_cells(region, f04, fill)
        s["n_object"] = int(cnt[_OBJ_V].sum())
        s["n_depth_object"] = int(cnt[_OBJ_V & ((_V & _B["depth"]) > 0)].sum())
        s["n_depth_cells"] = int(cnt[(_V & _B["depth"]) > 0].sum())
        obj = mat & ~tm
        s["spread_mm"] = round(float(z[n] - z[top[obj].min()]), 9) if s["n_object"] else None
        s["recover_cells_B"] = int(cnt[_B["depth"]])
        stats.append(s)

        exposed = mat & (top == top_final)
        birth = exposed & (top == n)
        denom |= birth & ((b & (_B["type"] | _B["fov"] | _B["edge"])) == 0)
        covered |= exposed & region

    post_edge, post = _post_band(p, bbox, res, step, h if N else None, mat if N else None,
                                 bits_all[-1] if N else None, f02, f04, fill, shape)

    nd = int(denom.sum())
    nc = int((covered & denom).sum())
    npx, npy = pass_counts(passes)
    info = {
        "gcode_sha256": result.header.get("gcode_sha256"),
        "band_mm": float(band), "step_mm": float(step), "band_auto_mm": band_auto, "step_auto_mm": step_auto,
        "camera_side": p.camera_side, "dof_mm": p.dof_mm, "dof_top_mm": p.dof_top_mm,
        "bbox_mm": [round(v, 6) for v in bbox], "passes_xy": [npx, npy], "n_passes": len(passes),
        "aligned": is_aligned(grid, p.cell_mm), "prime": prime_info,
        "coverage_denominator": nd, "coverage_covered": nc,
        "coverage_final_top_pct": (100.0 * nc / nd) if nd else float("nan"),
        **post,
        "build_s": round(time.perf_counter() - t0, 3),
    }
    return RegionStack(grid, z, bits_all, passes, p, info, stats, post_edge=post_edge)


def post_band_auto(params: RegionParams, bbox, res_mm: float) -> float:
    """post 엣지 띠 자동값 = max(2·res, α·반폭·ΔT) [추정] (팀장검증 5차 §3.4 · R-2).

    α = JudgeParams.cooled_alpha_um_per_m_c (µm/(m·°C)), 반폭 = 물체 경계 상자 긴 변의 반 (mm), ΔT = post_delta_t_c.
    """
    half = max(bbox[1] - bbox[0], bbox[3] - bbox[2]) / 2.0
    shrink = JudgeParams.cooled_alpha_um_per_m_c * 1e-6 * half * params.post_delta_t_c
    return round(max(2.0 * res_mm, shrink), 9)


def _post_band(p, bbox, res, step, h, mat, b_last, f02, f04, fill, shape):
    """마지막 층 post 엣지 띠와 info 항목. 좁은 띠로 0칸이면 P-A (엣지 안 뺌)."""
    band = p.post_edge_band_mm if p.post_edge_band_mm is not None else post_band_auto(p, bbox, res)
    rule = POST_RULE_NARROW
    if h is None:  # 층 없음
        pe = np.zeros(shape, bool)
        reg = np.zeros(shape, bool)
    else:
        base = b_last & np.uint8(~_B["edge"] & 0xFF)  # 엣지 비트만 지운 마지막 층 비트
        pe = edge_band(h, res, band, step) & mat
        reg = (base | pe.view(np.uint8)) == 0
        if not reg.any():
            pe = np.zeros(shape, bool)
            reg = base == 0
            rule = POST_RULE_EDGE_IN
    info = {"post_rule": rule, "post_band_mm": float(band), "post_delta_t_c": p.post_delta_t_c,
            "post_n_region": int(reg.sum()),
            "post_region_cell02": region_cells(reg, f02, fill), "post_region_cell04": region_cells(reg, f04, fill)}
    return pe, info
