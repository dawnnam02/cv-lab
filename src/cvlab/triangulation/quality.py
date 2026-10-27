"""레이저 선 품질 지표와 표시 비트 (docs/레이저선-추출.md §6).

값은 지우지 않고 표시만 합니다. 버릴지는 T9 (H2)가 정합니다.
"""
from __future__ import annotations

import numpy as np

FLAG = {"no_line": 1, "low_peak": 2, "wide": 4, "saturated": 8, "multi_peak": 16, "edge_window": 32}


def line_quality(img, v, bit_depth, params=None) -> dict:
    """열마다 품질 지표.

    img : [H, W] 영상 (uint8 · uint16 · float). v : [W] 중심 행 (ROI 좌표, NaN 허용).
    bit_depth : `frame.bit_depth` (포화값 = 2^bit_depth − 1). None이면 그릇으로 추정.
    반환 키: peak_dn (창 안 원시 최댓값, DN), fwhm_px, n_sat (창 안 포화 화소 수),
    n_peaks (문턱 넘는 봉우리 수, 열 전체), snr ((피크 − 배경) / σ_배경).
    v가 NaN인 열은 그 열 최대 화소 자리를 중심으로 잽니다.
    """
    from . import _core
    from .params import TriParams

    params = params or TriParams()
    a = _core.as_image(img)
    sat = _core.sat_level(a, bit_depth)
    f = a
    H, W = f.shape
    v = np.asarray(v, dtype=np.float64)
    if v.shape != (W,):
        raise ValueError(f"v 길이 {v.shape} ≠ 영상 폭 {W}")
    ok = np.isfinite(v)
    p = np.where(ok, np.rint(np.nan_to_num(v)), _core.argmax_rows(f)).astype(np.int64)
    p = np.clip(p, 0, H - 1)
    st = _core.column_stats(f, p, params, valid_hint=ok)
    hw = st["half_win"]
    rows = p[None, :] + np.arange(-hw, hw + 1)[:, None]
    inb = (rows >= 0) & (rows < H)
    raw = _core.gather(a, rows).astype(np.float64)
    raw = np.where(inb, raw, -np.inf)
    peak_dn = raw.max(axis=0)
    n_sat = ((raw >= sat) & inb).sum(axis=0)
    fwin = np.where(inb, _core.gather(f, rows).astype(np.float64), -np.inf).max(axis=0)
    snr = (fwin - st["bg"]) / st["sigma"]
    n_peaks = _core.count_peaks(f, st["thr"])
    return {
        "peak_dn": peak_dn.astype(np.float32),
        "fwhm_px": st["fwhm"].astype(np.float32),
        "n_sat": n_sat.astype(np.int32),
        "n_peaks": n_peaks.astype(np.int32),
        "snr": snr.astype(np.float32),
    }
