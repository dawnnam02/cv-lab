"""G2 · 비드 모델.

단면 = 사각형 + 양 끝 반원 (스타디움): A = (w − h)·h + π·h²/4  (w ≥ h)
정답 높이 기본 정의 (MF-GCD-01) = 층 Z (노즐 끝 Z = 비드 윗면, flat).
bead_profile_height는 민감도용 대안일 뿐 정답 지도에는 쓰지 않는다.
첫 층 눌림 (MF-GCD-03)은 넣지 않는다 (층 표의 첫 층 두께로만 둠).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def bead_area(w_mm: float, h_mm: float) -> float:
    if h_mm <= 0 or w_mm < h_mm:
        raise ValueError("bead_area는 w ≥ h > 0에서만")
    return (w_mm - h_mm) * h_mm + math.pi * h_mm ** 2 / 4.0


def width_from_area(A_mm2: float, h_mm: float) -> float:
    """bead_area의 역함수. A < π h²/4 + 0 (w < h)이면 ValueError."""
    if h_mm <= 0:
        raise ValueError("h는 0보다 커야 함")
    w = (A_mm2 - math.pi * h_mm ** 2 / 4.0) / h_mm + h_mm
    if w < h_mm - 1e-12:
        raise ValueError("넓이가 너무 작아 w < h")
    return w


def _layer_heights(segments: pd.DataFrame) -> dict:
    e = segments[(segments.kind == "extrude") & (segments.layer_idx >= 0)]
    zs = e.groupby("layer_idx")["z1_mm"].min().sort_index()
    out, prev = {}, 0.0
    for k, z in zs.items():
        out[int(k)] = float(z) - prev
        prev = float(z)
    return out


def effective_width(segments: pd.DataFrame, filament_d_mm: float, min_len_mm: float = 0.5) -> pd.Series:
    """압출량 기반 선폭 w_eff (선분마다). 압출이 아니거나 min_len보다 짧으면 NaN.

    A_e = ΔE · π (d_f/2)² / L,  w_eff = width_from_area(A_e, 층 높이)
    """
    if not filament_d_mm or filament_d_mm <= 0:
        raise ValueError("필라멘트 지름이 필요함")
    hmap = _layer_heights(segments)
    af = math.pi * (filament_d_mm / 2.0) ** 2
    out = np.full(len(segments), np.nan)
    for i, (kind, li, L, de) in enumerate(zip(segments.kind, segments.layer_idx,
                                              segments.length_mm, segments.de_mm)):
        if kind != "extrude" or li < 0 or not (L >= min_len_mm) or li not in hmap:
            continue
        h = hmap[li]
        try:
            out[i] = width_from_area(de * af / L, h)
        except ValueError:
            pass
    return pd.Series(out, index=segments.index, name="w_eff_mm")


def bead_profile_height(d_mm, w_mm: float, h_mm: float, z_mm: float):
    """민감도용 대안: 비드 중심선에서 옆으로 d만큼 떨어진 곳의 단면 윗면 높이.

    가운데 평평한 부분 (|d| ≤ (w−h)/2)은 z, 양 끝 반원 부분은 z − h/2 + √((h/2)² − (|d| − (w−h)/2)²).
    비드 밖은 NaN.
    """
    d = np.abs(np.asarray(d_mm, float))
    half_flat = (w_mm - h_mm) / 2.0
    r = h_mm / 2.0
    t = d - half_flat
    out = np.where(t <= 0, z_mm, z_mm - r + np.sqrt(np.clip(r * r - t * t, 0, None)))
    return np.where(d <= w_mm / 2.0 + 1e-12, out, np.nan)
