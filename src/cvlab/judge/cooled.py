"""식힌 재측정 (D-06): 판정에는 쓰지 않고 마지막 층과의 차이만 보고한다."""
from __future__ import annotations

import math

import numpy as np


def cooled_difference(delta_last_mm, delta_post_mm, region=None) -> dict | None:
    """차이 = Δ_post − Δ_last (µm). 둘 다 값이 있고 판정 영역 안인 칸만. 공통 칸이 없으면 None."""
    a = np.asarray(delta_last_mm, dtype=float)
    b = np.asarray(delta_post_mm, dtype=float)
    if a.shape != b.shape:
        raise ValueError(f"식힌 재측정 모양 {b.shape} ≠ 마지막 층 모양 {a.shape}")
    m = np.isfinite(a) & np.isfinite(b)
    if region is not None:
        m &= np.asarray(region, dtype=bool)
    if not m.any():
        return None
    d = (b[m] - a[m]) * 1000.0
    return {
        "n": int(d.size),
        "mean_um": float(np.mean(d)),
        "median_um": float(np.median(d)),
        "p05_um": float(np.percentile(d, 5)),
        "p95_um": float(np.percentile(d, 95)),
        "max_abs_um": float(np.max(np.abs(d))),
    }


def cooling_criterion(height_mm, specimen_temp_c, room_temp_c, alpha_um_per_m_c=68.0,
                      delta_max_um=5.0) -> dict:
    """'식었다' 기준 (D-20 R4 확정, docs/판정-규칙.md §8).

    남은 수축 δ = α · H · ΔT, ΔT = 시편 윗면 온도 − 실내 온도.
    ΔT_max = δ_max ÷ (α · H). 판정은 바꾸지 않고 충족 여부만 보고한다.
    """
    vals = {"height_mm": height_mm, "specimen_temp_c": specimen_temp_c, "room_temp_c": room_temp_c}
    missing = [k for k, v in vals.items() if v is None or not math.isfinite(float(v))]
    if missing:
        return {"ok": None, "missing": missing, "delta_max_um": float(delta_max_um),
                "alpha_um_per_m_c": float(alpha_um_per_m_c)}
    H = float(height_mm)
    if H <= 0:
        raise ValueError("height_mm: 0보다 커야 함")
    um_per_c = alpha_um_per_m_c * H / 1000.0          # µm/(m·°C) × mm → µm/°C
    dT = float(specimen_temp_c) - float(room_temp_c)
    dT_max = float(delta_max_um) / um_per_c
    residual = um_per_c * max(dT, 0.0)
    return {
        "ok": bool(residual <= delta_max_um),
        "missing": [],
        "height_mm": H,
        "delta_T_c": dT,
        "delta_T_max_c": dT_max,
        "um_per_c": um_per_c,
        "residual_shrink_um": residual,
        "delta_max_um": float(delta_max_um),
        "alpha_um_per_m_c": float(alpha_um_per_m_c),
    }
