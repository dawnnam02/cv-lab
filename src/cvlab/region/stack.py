"""층별 판정 영역 (RegionStack) 만들기 (RG5 – RG12).

build_region은 G코드 (ParseResult) · 정답 지도 (RefStack) · 설정만 받는다. 측정값을 받는 인자가 없다 (MF-JDG-03).

이유 비트 (uint8, 겹침 허용) → T15 코드 (int8, 칸마다 하나, §6.2 우선순위):
  출력물 없는 칸: PRIME이 덮으면 4, 아니면 5.
  출력물 있는 칸: type (4) > fov (3) > depth (9) > occlusion (2) > edge (1). 이유가 없으면 영역 칸, 코드 0.
  depth는 T15 코드표에 "심도 밖"이 없어 9 (기타)로 낸다. 코드 6 추가는 T15 후속 J-2.
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
from .masks import edge_band_update, grow, predict_occlusion, prime_mask
from .params import RegionParams

REASON_BITS = {"edge": 1, "occlusion": 2, "fov": 4, "type": 8, "no_material": 16, "depth": 32, "prime": 64}
REASON_CODE = {"edge": 1, "occlusion": 2, "fov": 3, "type": 4, "no_material": 5, "depth": 9, "prime": 4}
# 출력물 있는 칸의 우선순위 (앞이 이김)
MATERIAL_PRIORITY = ("type", "fov", "depth", "occlusion", "edge")
SUMMARY_COLUMNS = ["layer_idx", "layer_z_mm", "n_material", "n_region", "region_pct",
                   "bit_edge", "bit_occlusion", "bit_fov", "bit_type", "bit_depth", "bit_prime",
                   "code_1", "code_2", "code_3", "code_4", "code_5", "code_9",
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
                 info: dict, stats: list):
        self.grid = dict(grid)
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
        """cvlab.judge.LayerInput. 식힌 재측정 (cooled)은 마지막 층 영역을 그대로 씀 (§6.4)."""
        d = np.asarray(delta_mm, float)
        if d.shape != self._shape:
            raise ValueError(f"delta 모양 {d.shape} ≠ 격자 {self._shape}")
        if thermal_state == "cooled" and n != self.n_layers - 1:
            raise ValueError("식힌 재측정 (cooled)은 마지막 층 영역만 씀")
        return LayerInput(layer_idx=int(n), thermal_state=thermal_state, delta_mm=d,
                          region=self.region(n), exclusion_code=self.exclusion_code(n))

    def post_input(self, delta_mm) -> LayerInput:
        return self.layer_input(self.n_layers - 1, delta_mm, thermal_state="cooled")

    # ---- 저장
    def save(self, path) -> None:
        size = self._shape[0] * self._shape[1]
        planes = np.zeros((self.n_layers, _N_BITS, (size + 7) // 8), np.uint8)
        for n, b in enumerate(self._bits):
            flat = b.ravel()
            for j in range(_N_BITS):
                planes[n, j] = np.packbits(((flat >> j) & 1).astype(bool))
        np.savez_compressed(
            path, grid=np.array(json.dumps(self.grid)), z_layers=self.z_layers, planes=planes,
            passes=np.array(json.dumps(self.passes)), params=np.array(json.dumps(self.params.to_dict())),
            info=np.array(json.dumps(self.info, ensure_ascii=False)),
            stats=np.array(json.dumps(self._stats, ensure_ascii=False)))

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
            return cls(grid, d["z_layers"], bits, json.loads(str(d["passes"])),
                       RegionParams.from_dict(json.loads(str(d["params"]))),
                       json.loads(str(d["info"])), json.loads(str(d["stats"])))


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
        for c in (1, 2, 3, 4, 5, 9):
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
        "build_s": round(time.perf_counter() - t0, 3),
    }
    return RegionStack(grid, z, bits_all, passes, p, info, stats)
