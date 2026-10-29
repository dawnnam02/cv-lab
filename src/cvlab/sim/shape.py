# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""참 출력 형상 (세부청사진 §6.1 ① · §6.2, SM1 · SM2 · SM3).

참 높이 H(x, y, n) ({G} Z, 베드 = 0, 층 n 스캔 당시):

    H = Zact[top'] + B + E − S

- top: 층 n까지 덮어 쓴 꼭대기 층 번호 (cvlab.gcode 정답 지도의 footprint). top' = 빠진 층 (missing_layer)이
  있으면 그 칸만 k − 1 (명령 Z가 맞고 압출만 멈춤).
- Zact[k]: 층 k를 쌓을 때 노즐의 실제 Z. 명령 Z × (1 + g) + 워블 + 층마다 무작위 + 프레임 드리프트 (출력 시각),
  걸음 양자화. g = z_axis.gain_ppm + 시나리오 z_scale (T5 §5 ②: z_scale은 참 형상과 센서를 같이 밂).
- B: 바탕 꼴. reference = 0 (T4a 정답 지도 그대로, flat 비드). deposition = 자체 비드 단면 (stadium) 꼭대기 차이
  + 비드 치우침 (MF-GCD-01 · 02).
- E: 시나리오의 더하는 오차 (z_offset · local · warp · extrusion). 식은 T5 YAML kinds 그대로.
- S: 열 수축 (MF-THM-05). 층 n 당시 온도장 T(z) = T_low + (T_top − T_low) exp(−(z_n − z) ÷ L)에서
  S = α ∫₀^Z (T_solid − T(z)) dz. 식은 뒤 (post): 시편 전체가 T_end로 → S = α Z (T_solid − T_end).

참 판정 (truth.judgement): Δ = H − Z_ref (Z_ref = 정답 지도 꼭대기 높이), 판정 영역 안을 0.2 mm 칸으로 묶어
U = 0 (방식 A)으로 센 합격점 비율 ≥ 95 % ⇔ pass (명세 부록 A, T5 §1). 계산은 cvlab.judge.
판정 영역은 T5 stand-in-v1과 같은 정의 (출력물 − 제외 종류 − 심도 밖)를 여기서 따로 셈 (처리 쪽 영역 코드는 안 씀).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import ndimage

from cvlab.gcode import build_reference, make_grid, parse_file
from cvlab.gcode.reference import segment_widths
from cvlab.judge import LayerInput, fine_to_cell_layer, judge_print, load_params

from .simconfig import ROOT, specimen_gcode

JUDGE_YAML = ROOT / "config" / "judge.yaml"
KNOWN_KINDS = ("z_offset", "z_scale", "local", "warp", "missing_layer", "extrusion")
SHAPE_FACTORS = ("layer_thermal_field", "z_axis_error", "frame_drift", "bead_model_bias", "bead_texture")
NUISANCE_OFF = {k: False for k in SHAPE_FACTORS}


# ---------------------------------------------------------------- 시편
@dataclass
class Specimen:
    name: str
    path: Path
    sha256: str
    result: object
    ref: object
    grid: dict
    bbox: dict
    xs: np.ndarray
    ys: np.ndarray
    exc_codes: list
    widths: np.ndarray = field(repr=False, default=None)

    @property
    def n_layers(self) -> int:
        return self.ref.n_layers

    @property
    def z_layers(self) -> np.ndarray:
        return self.ref.z_layers


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def object_bbox(result, excluded) -> dict:
    """제외 종류를 뺀 압출 끝점 + 가장 넓은 선폭 반 (시나리오 loc_rel의 기준 상자, T5 YAML 머리말)."""
    e = result.extrusions()
    w = segment_widths(result, result.params)
    m = ~e["type"].isin(list(excluded)).to_numpy()
    if not m.any():
        raise ValueError("제외 종류를 빼면 압출이 없음")
    xs = np.concatenate([e.x0_mm[m], e.x1_mm[m]])
    ys = np.concatenate([e.y0_mm[m], e.y1_mm[m]])
    half = float(np.max(w[m])) / 2.0
    return dict(xmin=float(xs.min()) - half, xmax=float(xs.max()) + half,
                ymin=float(ys.min()) - half, ymax=float(ys.max()) + half)


def specimen_from_result(name, result, cfg, path=Path("."), sha="") -> Specimen:
    excl = cfg["judge"]["excluded_types"]
    b = object_bbox(result, excl)
    res = cfg["grid"]["res_mm"]
    grid = make_grid(b["xmin"], b["xmax"], b["ymin"], b["ymax"], res, cfg["grid"]["margin_mm"])
    ref = build_reference(result, grid=grid)
    xs = grid["x0_mm"] + np.arange(grid["nx"]) * res
    ys = grid["y0_mm"] + np.arange(grid["ny"]) * res
    exc = [i for i, t in enumerate(ref.type_names) if t in excl]
    return Specimen(name, Path(path), sha, result, ref, grid, b, xs, ys, exc,
                    widths=segment_widths(result, result.params))


def load_specimen(cfg: dict, name: str) -> Specimen:
    path, want = specimen_gcode(cfg, name)
    got = file_sha256(path)
    if want and got != want:
        raise ValueError(f"{name} G코드 지문이 다름: {got[:12]}… ≠ {want[:12]}…")
    return specimen_from_result(name, parse_file(path), cfg, path, got)


# ---------------------------------------------------------------- 시나리오 (출력 오차)
def scenario_kinds(pep: dict) -> dict:
    if "scenario" not in pep:
        raise ValueError("print_error_params에 scenario 키가 없음")
    kinds = {k: v for k, v in pep.items() if k != "scenario"}
    bad = set(kinds) - set(KNOWN_KINDS)
    if bad:
        raise ValueError(f"모르는 오차 종류: {sorted(bad)}")
    return kinds


def layer_of(rel: float, nL: int) -> int:
    return int(round(rel * (nL - 1)))


class PrintError:
    """T5 YAML kinds 식 그대로. 위치 · 층은 상대값 (경계 상자, 층 번호 = round(rel × (층 수 − 1)))."""

    def __init__(self, pep: dict, spec: Specimen, n_layers: int | None = None):
        self.pep = pep
        self.kinds = scenario_kinds(pep)
        b, xs, ys = spec.bbox, spec.xs, spec.ys
        W, H = b["xmax"] - b["xmin"], b["ymax"] - b["ymin"]
        nL = spec.n_layers if n_layers is None else n_layers
        self.gain = self.kinds.get("z_scale", {}).get("gain_ppm", 0.0) * 1e-6
        self.static = np.zeros((len(ys), len(xs)))
        k = self.kinds
        if "z_offset" in k:
            self.static += k["z_offset"]["dz_um"] / 1000.0
        if "warp" in k:
            U = ((xs - b["xmin"]) / W)[None, :]
            V = ((ys - b["ymin"]) / H)[:, None]
            self.static += (k["warp"]["lift_um"] / 1000.0) * ((U - 0.5) ** 2 + (V - 0.5) ** 2) / 0.5
        if "extrusion" in k:
            p = k["extrusion"]
            ph = 2 * np.pi * (xs[None, :] + ys[:, None]) / (math.sqrt(2) * p["ripple_period_mm"])
            self.static += p["dz_um"] / 1000.0 + (p["ripple_um"] / 1000.0) * np.sin(ph)
        self.local = None
        if "local" in k:
            p = k["local"]
            cx, cy = b["xmin"] + p["loc_rel"][0] * W, b["ymin"] + p["loc_rel"][1] * H
            r2 = (xs[None, :] - cx) ** 2 + (ys[:, None] - cy) ** 2
            self.local = ((p["amp_um"] / 1000.0) * np.exp(-r2 / (2 * p["sigma_mm"] ** 2)),
                          layer_of(p["layer_from_rel"], nL), layer_of(p["layer_to_rel"], nL))
        self.missing = None
        if "missing_layer" in k:
            p = k["missing_layer"]
            cx, cy = b["xmin"] + p["loc_rel"][0] * W, b["ymin"] + p["loc_rel"][1] * H
            inside = (xs[None, :] - cx) ** 2 + (ys[:, None] - cy) ** 2 <= p["radius_mm"] ** 2
            kk = max(1, layer_of(p["layer_rel"], nL))
            self.missing = (inside, kk, kk + int(p["n_layers"]) - 1)

    def effective_top(self, top: np.ndarray, sl=None) -> np.ndarray:
        if self.missing is None:
            return top
        inside, k0, k1 = self.missing
        if sl is not None:
            inside = inside[sl]
        hit = inside & (top >= k0) & (top <= k1)
        return np.where(hit, k0 - 1, top)

    def additive(self, top: np.ndarray, sl=None) -> np.ndarray:
        st = self.static if sl is None else self.static[sl]
        if self.local is None:
            return st
        g, k0, k1 = self.local
        if sl is not None:
            g = g[sl]
        return st + np.where((top >= k0) & (top <= k1), g, 0.0)


# ---------------------------------------------------------------- Z축
class ZAxis:
    """층마다 노즐 실제 Z (MF-MEC-04 · CAL-05 · THM-08). 출력과 센서에 같이 들어감."""

    def __init__(self, zcfg: dict, z_layers, t_print_s, extra_gain: float, rng, on_axis: bool, on_drift: bool):
        zl = np.asarray(z_layers, float)
        g = extra_gain + (zcfg["gain_ppm"] * 1e-6 if on_axis else 0.0)
        self.params = {"gain_ppm": round(g * 1e6, 6),
                       "scenario_gain_ppm": round(extra_gain * 1e6, 6),
                       "nonrep_sigma_um": zcfg["nonrep_sigma_um"] if on_axis else 0.0,
                       "wobble_amp_um": zcfg["wobble_amp_um"] if on_axis else 0.0,
                       "wobble_period_mm": zcfg["wobble_period_mm"],
                       "step_um": zcfg["step_um"] if on_axis else 0.0,
                       "frame_drift_um_per_h": zcfg["frame_drift_um_per_h"] if on_drift else 0.0}
        p = self.params
        phase = float(rng.uniform(0, 2 * np.pi)) if rng is not None else 0.0
        nonrep = (rng.normal(0.0, p["nonrep_sigma_um"], len(zl)) if (rng is not None and p["nonrep_sigma_um"] > 0)
                  else np.zeros(len(zl)))
        self.nonrep_um = nonrep
        self.phase = phase
        self.t_print_s = np.asarray(t_print_s, float)
        za = zl * (1.0 + g)
        za = za + p["wobble_amp_um"] / 1000.0 * np.sin(2 * np.pi * zl / p["wobble_period_mm"] + phase)
        za = za + nonrep / 1000.0 + p["frame_drift_um_per_h"] / 1000.0 * self.t_print_s / 3600.0
        if p["step_um"] > 0:
            za = np.round(za / (p["step_um"] / 1000.0)) * (p["step_um"] / 1000.0)
        self.layer_actual = za

    def truth_params(self) -> dict:
        d = dict(self.params)
        d["nonrep_um"] = [round(float(v), 4) for v in self.nonrep_um]
        d["wobble_phase_rad"] = round(self.phase, 6)
        return d


# ---------------------------------------------------------------- 열
class Thermal:
    """층별 온도장 · 수축 (MF-THM-05, SM3). on=False면 수축 0."""

    def __init__(self, tcfg: dict, on: bool):
        self.c = dict(tcfg)
        self.on = on
        self.alpha = tcfg["cte_um_per_m_c"] * 1e-6

    def top_temp(self, wait_s: float) -> float:
        c = self.c
        return c["t_low_c"] + (c["t_solid_c"] - c["t_low_c"]) * math.exp(-wait_s / c["tau_top_s"])

    def temp_at(self, z, zn: float, wait_s: float):
        c = self.c
        return c["t_low_c"] + (self.top_temp(wait_s) - c["t_low_c"]) * np.exp(-(zn - np.asarray(z)) / c["depth_mm"])

    def shrink(self, Z: np.ndarray, zn: float, wait_s: float) -> np.ndarray:
        """층 n 당시 높이 Z 기둥의 줄어든 몫 (mm, ≥ 0)."""
        if not self.on:
            return np.zeros_like(Z)
        c = self.c
        L, ts, tl = c["depth_mm"], c["t_solid_c"], c["t_low_c"]
        tt = self.top_temp(wait_s)
        Zc = np.clip(Z, 0.0, None)
        integ = (ts - tl) * Zc - (tt - tl) * L * (np.exp(-np.clip(zn - Zc, 0.0, None) / L) - math.exp(-zn / L))
        return self.alpha * integ

    def post_temp(self) -> float:
        c = self.c
        return c["t_room_c"] + (c["t_low_c"] - c["t_room_c"]) * math.exp(-c["post_wait_s"] / c["tau_bulk_s"])

    def post_shrink(self, Z: np.ndarray) -> np.ndarray:
        if not self.on:
            return np.zeros_like(Z)
        return self.alpha * np.clip(Z, 0.0, None) * (self.c["t_solid_c"] - self.post_temp())


def gauge_temperature(gcfg: dict, t_s: float) -> float:
    """계단 기준물 (강철) 온도: 실내에서 가열 베드 쪽으로 지수 접근 [추정 모델]."""
    return gcfg["t_start_c"] + (gcfg["t_end_c"] - gcfg["t_start_c"]) * (1.0 - math.exp(-t_s / gcfg["tau_s"]))


def gauge_height(h20_mm: float, temp_c: float, cte_um_per_m_c: float) -> float:
    """20 °C 참 높이 → 그 온도의 높이 (강철 팽창)."""
    return h20_mm * (1.0 + cte_um_per_m_c * 1e-6 * (temp_c - 20.0))


# ---------------------------------------------------------------- 바탕 꼴 deposition
def stadium_offset(d: np.ndarray, w: np.ndarray, h: np.ndarray) -> np.ndarray:
    """비드 단면 꼭대기 − 층 Z (≤ 0). 가운데 (w − h) 평평, 양쪽 지름 h 반원."""
    flat = np.clip((w - h) / 2.0, 0.0, None)
    r = h / 2.0
    e = np.clip(d - flat, 0.0, None)
    e = np.minimum(e, r)
    return -(r - np.sqrt(np.clip(r * r - e * e, 0.0, None)))


def _seg_dist(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    t = np.where(L2 > 0, ((px - x0) * dx + (py - y0) * dy) / np.where(L2 > 0, L2, 1.0), 0.0)
    t = np.clip(t, 0.0, 1.0)
    return np.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def deposition_offset(spec: Specimen, k: int, dcfg: dict, texture: bool, bias: bool) -> np.ndarray:
    """층 k 비드 꼭대기 − 층 Z (mm), 층 k footprint 안만 뜻 있음 (밖은 0)."""
    fp = spec.ref.footprint(k)
    out = np.zeros(fp.shape)
    if not fp.any():
        return out
    zl = spec.z_layers
    hk = float(zl[k] - (zl[k - 1] if k > 0 else 0.0))
    off_bias = 0.0
    if bias:
        off_bias = dcfg["bead_bias_um"] / 1000.0 + (dcfg["flow_ratio"] - 1.0) * hk
    if not texture:
        out[fp] = off_bias
        return out
    g = spec.grid
    res = g["res_mm"]
    e = spec.result.extrusions()
    sel = np.flatnonzero(e["layer_idx"].to_numpy() == k)
    x0 = e.x0_mm.to_numpy()[sel]; y0 = e.y0_mm.to_numpy()[sel]
    x1 = e.x1_mm.to_numpy()[sel]; y1 = e.y1_mm.to_numpy()[sel]
    wk = spec.widths[sel]
    iy_fp, ix_fp = np.nonzero(fp)
    pad = int(math.ceil(float(wk.max()) / res)) + 2
    ya, yb = max(iy_fp.min() - pad, 0), min(iy_fp.max() + pad + 1, fp.shape[0])
    xa, xb = max(ix_fp.min() - pad, 0), min(ix_fp.max() + pad + 1, fp.shape[1])
    sub = (yb - ya, xb - xa)
    segid = np.full(sub, -1, np.int64)
    L = np.hypot(x1 - x0, y1 - y0)
    n = np.maximum(np.ceil(L / (res / 2.0)).astype(int) + 1, 2)
    sid = np.repeat(np.arange(len(sel)), n)
    t = np.concatenate([np.linspace(0.0, 1.0, m) for m in n])
    px = x0[sid] + t * (x1 - x0)[sid]
    py = y0[sid] + t * (y1 - y0)[sid]
    ix = np.rint((px - g["x0_mm"]) / res).astype(int) - xa
    iy = np.rint((py - g["y0_mm"]) / res).astype(int) - ya
    ok = (ix >= 0) & (ix < sub[1]) & (iy >= 0) & (iy < sub[0])
    segid[iy[ok], ix[ok]] = sid[ok]
    _, (ny_i, nx_i) = ndimage.distance_transform_edt(segid < 0, return_indices=True)
    near = segid[ny_i, nx_i]
    fps = fp[ya:yb, xa:xb]
    yy, xx = np.nonzero(fps)
    s = near[yy, xx]
    cx = g["x0_mm"] + (xx + xa) * res
    cy = g["y0_mm"] + (yy + ya) * res
    d = _seg_dist(cx, cy, x0[s], y0[s], x1[s], y1[s])
    prof = stadium_offset(d, wk[s], np.full(len(s), hk))
    out[yy + ya, xx + xa] = prof + off_bias
    return out


# ---------------------------------------------------------------- 엔진
def layer_times(spec_cfg: dict, nL: int) -> tuple[np.ndarray, np.ndarray]:
    """(층 k 출력 끝 시각, 층 k 첫 줄 스캔 시작 시각) 출력 시작 기준 s. S4에서 위치 로그 시각으로 바꿈."""
    lp, ps = spec_cfg["layer_print_s"], spec_cfg["pause_s"]
    k = np.arange(nL)
    end = (k + 1) * lp + k * ps
    return end, end


@dataclass
class ScenarioRun:
    name: str
    pep: dict
    err: PrintError
    zaxis: ZAxis
    cells: list = field(default_factory=list)
    snap: np.ndarray | None = None


def stand_in_region(top, tcode, zl, zn, exc_codes, dof_mm) -> np.ndarray:
    """T5 stand-in-v1: 출력물 칸 − 꼭대기 제외 종류 − 심도 밖 (z_n − Z_ref > 심도, nm 정수 비교)."""
    has = top >= 0
    Z = np.where(has, zl[np.maximum(top, 0)], zn)
    depth_nm = np.rint((zn - Z) * 1e6).astype(np.int64)
    return has & ~np.isin(tcode, exc_codes) & (depth_nm <= int(round(dof_mm * 1e6)))


def true_judge_params():
    return load_params(JUDGE_YAML, U_mm=0.0, U_source="참 판정, 방식 A (U = 0)")


def simulate_specimen(spec: Specimen, cfg: dict, peps: list, base: str = "reference",
                      factors: dict | None = None, seed_tree=None, layers=None, on_heightmap=None,
                      n_print_layers: int | None = None) -> list:
    """시나리오 여러 개를 한 번의 층 순회로 계산. 시나리오마다 참 판정 · 참값 사전을 돌려줌.

    factors: 스위치 켬/끔 (SHAPE_FACTORS). None이면 모두 끔 (참값만 · SM2 대조 모드).
    seed_tree: 무작위 성분 (Z축 층마다 무작위) 갈래. 없으면 무작위 성분 0.
    layers: 참 높이맵을 넘길 층 번호 목록 (None = 모두). 판정은 늘 모든 층.
    on_heightmap(scenario, key, H): key = 층 번호 또는 "post". H는 float32.
    n_print_layers: 앞 몇 층에서 출력을 멈춘 것으로 봄 (작은 캠페인). None = G코드 모든 층.
    """
    if base not in ("reference", "deposition"):
        raise ValueError(f"바탕 꼴은 reference · deposition: {base}")
    f = dict(NUISANCE_OFF)
    f.update(factors or {})
    bad = set(f) - set(SHAPE_FACTORS)
    if bad:
        raise ValueError(f"모르는 스위치: {sorted(bad)}")
    if cfg["judge"]["region_source"] != "stand-in-v1":
        raise NotImplementedError("T5-2 판정 영역 배열은 아직 없음 (region_source = stand-in-v1만)")
    nL = spec.n_layers if n_print_layers is None else int(n_print_layers)
    if not 1 <= nL <= spec.n_layers:
        raise ValueError(f"출력 층 수 범위 밖: {nL} (1–{spec.n_layers})")
    zl = spec.z_layers[:nL]
    scfg = cfg["specimens"].get(spec.name, {"layer_print_s": 20.0, "pause_s": 30.0})
    t_end, _ = layer_times(scfg, nL)
    wait = float(cfg["thermal"]["wait_first_pass_s"])
    thermal = Thermal(cfg["thermal"], f["layer_thermal_field"])
    P0 = true_judge_params()
    res, cell = cfg["grid"]["res_mm"], cfg["judge"]["cell_mm"]
    dof = cfg["grid"]["depth_of_field_mm"]
    runs = []
    for pep in peps:
        err = PrintError(pep, spec, nL)
        rng = seed_tree.child(spec.name, "z_axis").rng() if seed_tree is not None else None
        za = ZAxis(cfg["z_axis"], zl, t_end, err.gain, rng, f["z_axis_error"], f["frame_drift"])
        runs.append(ScenarioRun(pep["scenario"], pep, err, za))
    ny, nx = spec.grid["ny"], spec.grid["nx"]
    top = np.full((ny, nx), -1, np.int32)
    excl = np.zeros((ny, nx), bool)
    Zref = np.zeros((ny, nx))
    offs = np.zeros((ny, nx))
    tcodes = spec.ref._type_codes  # cvlab.gcode 저장 형식 (읽기만, RefStack.type_at과 같은 값 · T5와 같은 요령)
    want = set(range(nL)) if layers is None else set(layers)
    fcell = int(round(cell / res))
    dof_nm = int(round(dof * 1e6))
    region_cells = []
    layer_temp = []
    last_H = {}
    for n in range(nL):
        fp = spec.ref.footprint(n)
        idx = np.flatnonzero(fp.ravel())
        top.ravel()[idx] = n
        excl.ravel()[idx] = np.isin(tcodes[n], spec.exc_codes)
        zn = float(zl[n])
        Zref.ravel()[idx] = zn
        if base == "deposition":
            dn = deposition_offset(spec, n, cfg["deposition"], f["bead_texture"], f["bead_model_bias"])
            offs[fp] = dn[fp]
        has = top >= 0
        # T5 stand-in-v1: 출력물 칸 − 꼭대기 제외 종류 − 심도 밖 (z_n − Z_ref > 심도, nm 정수 비교)
        region = has & ~excl & (np.rint((zn - Zref) * 1e6).astype(np.int64) <= dof_nm)
        layer_temp.append(round(thermal.top_temp(wait) if thermal.on else thermal.c["t_solid_c"], 3))
        sl = _cell_crop(region, fcell)
        if sl is not None:
            region_cells.append(int(region.sum()))
        need_full_any = (on_heightmap is not None and n in want) or n == nL - 1
        for r in runs:
            if r.err.missing is not None and n == r.err.missing[1] - 1:
                r.snap = offs.copy()
            if need_full_any:
                H = _height(r, top, offs, has, thermal, zn, wait, final=False)
                Hc = H[sl] if sl is not None else None
            elif sl is not None:
                Hc = _height(r, top[sl], offs[sl], has[sl], thermal, zn, wait, final=False, sl=sl)
            if sl is not None:
                rc = region[sl]
                d = np.where(rc, Hc - Zref[sl], np.nan)
                r.cells.append(fine_to_cell_layer(LayerInput(n, "in_process", d, rc), res, cell, P0))
            if on_heightmap is not None and n in want:
                on_heightmap(r.name, n, H.astype(np.float32))
            if n == nL - 1:
                last_H[r.name] = H
    out = []
    for r in runs:
        jr = judge_print(r.cells, P0)
        npass, nvalid = jr.counts["n_pass"], jr.counts["n_valid"]
        judgement = "pass" if npass * 100 >= cfg["judge"]["pass_min_pct"] * nvalid else "fail"
        has = top >= 0
        Hp = _height(r, top, offs, has, thermal, float(zl[-1]), wait, final=True)
        if on_heightmap is not None:
            on_heightmap(r.name, "post", Hp.astype(np.float32))
        out.append(dict(
            scenario=r.name, specimen=spec.name, base=base, n_layers=len(r.cells),
            n_region_cells=int(jr.counts["n_region"]), n_valid=int(nvalid), n_pass=int(npass),
            pass_pct=float(jr.pct["pass_pct"]), judgement=judgement,
            print_error_params=r.pep, z_axis_error_params=r.zaxis.truth_params(),
            thermal_params=(dict(cte_um_per_m_c=thermal.c["cte_um_per_m_c"], layer_temp_c=layer_temp,
                                 t_solid_c=thermal.c["t_solid_c"], t_low_c=thermal.c["t_low_c"],
                                 depth_mm=thermal.c["depth_mm"], tau_top_s=thermal.c["tau_top_s"],
                                 wait_s=wait, post_temp_c=round(thermal.post_temp(), 3))
                            if thermal.on else {}),
            post_minus_last_mean_um=float(np.mean((Hp - last_H[r.name])[has]) * 1000.0) if has.any() else 0.0,
            region_cells_per_layer=region_cells,
        ))
    return out


def _cell_crop(region: np.ndarray, f: int):
    """판정 영역을 덮는 판정 칸 경계 맞춤 창 (칸 f개 단위, 배열 끝 칸 버림 규칙은 aggregate와 같음).
    창 밖에는 영역 칸이 없으므로 창 안에서 센 칸 수 · 값이 전체 배열로 센 것과 같다."""
    rows = np.flatnonzero(region.any(axis=1))
    if rows.size == 0:
        return None
    cols = np.flatnonzero(region.any(axis=0))
    ny, nx = (region.shape[0] // f) * f, (region.shape[1] // f) * f
    y0, x0 = (rows[0] // f) * f, (cols[0] // f) * f
    y1 = min(-(-(rows[-1] + 1) // f) * f, ny)
    x1 = min(-(-(cols[-1] + 1) // f) * f, nx)
    if y1 <= y0 or x1 <= x0:
        return None
    return (slice(int(y0), int(y1)), slice(int(x0), int(x1)))


def _height(r: ScenarioRun, top, offs, has, thermal: Thermal, zn: float, wait: float, final: bool,
            sl=None) -> np.ndarray:
    """참 높이 (모듈 머리말 식). sl을 주면 top · offs · has는 그 창의 조각이고 결과도 창 크기."""
    topx = r.err.effective_top(top, sl)
    za = r.zaxis.layer_actual
    zgeom = np.where(topx >= 0, za[np.maximum(topx, 0)], 0.0)
    H = zgeom + r.err.additive(top, sl)
    if r.snap is not None:
        H += np.where(topx != top, r.snap if sl is None else r.snap[sl], offs)
    elif offs.any():
        H += offs
    if thermal.on:
        H -= thermal.post_shrink(zgeom) if final else thermal.shrink(zgeom, zn, wait)
    return np.where(has, H, 0.0)
