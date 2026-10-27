"""층 하나의 제외 마스크 (RG2 – RG5). 입력은 정답 높이 지도와 G코드뿐 (측정값 없음, MF-JDG-03).

모든 함수는 배열 A[iy, ix] (T4a 격자 약속)를 받는다. 높이 NaN = 출력물 없음 (베드 0으로 봄).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from cvlab.gcode import GCodeError
from cvlab.gcode.reference import capsule_cells

_TOL_MM = 1e-9


def _nm(a) -> np.ndarray:
    return np.rint(np.asarray(a, float) * 1e6).astype(np.int64)


def bed_height(height_mm) -> np.ndarray:
    h = np.asarray(height_mm, float)
    return np.where(np.isnan(h), 0.0, h)


def height_boundary(height_mm, step_mm: float) -> np.ndarray:
    """3 × 3 이웃의 (최대 − 최소) > step_mm 인 칸. 비교는 nm 정수."""
    hn = _nm(bed_height(height_mm))
    mx = ndimage.maximum_filter(hn, size=3, mode="nearest")
    mn = ndimage.minimum_filter(hn, size=3, mode="nearest")
    return (mx - mn) > int(np.rint(step_mm * 1e6))


def edge_band(height_mm, res_mm: float, band_mm: float, step_mm: float) -> np.ndarray:
    """경계에서 거리 ≤ band_mm 인 칸 (경계 포함). G4 거리 변환 방식."""
    b = height_boundary(height_mm, step_mm)
    if not b.any():
        return np.zeros(b.shape, bool)
    # 거리가 band보다 먼 칸은 필요 없으므로 경계 상자 + 띠 폭 안만 계산 (결과는 전체 계산과 같음)
    r = int(math.ceil(band_mm / res_mm)) + 1
    iy, ix = np.nonzero(b)
    y0, y1 = max(iy.min() - r, 0), min(iy.max() + r + 1, b.shape[0])
    x0, x1 = max(ix.min() - r, 0), min(ix.max() + r + 1, b.shape[1])
    out = np.zeros(b.shape, bool)
    d = ndimage.distance_transform_edt(~b[y0:y1, x0:x1]) * res_mm
    out[y0:y1, x0:x1] = d <= band_mm + _TOL_MM
    return out


def edge_band_update(height_mm, prev_band, changed, res_mm: float, band_mm: float, step_mm: float) -> np.ndarray:
    """앞 층 띠 prev_band에서 높이가 바뀐 칸 (changed) 근처만 다시 계산한 띠. 결과는 edge_band와 같다.

    경계는 바뀐 칸 ± 1칸에서만 바뀐다 (C = 그 상자). 띠는 C에서 r칸 안 (W)에서만 바뀌고,
    W 안 칸의 띠를 정하는 경계는 W ± r (E) 안에 있다. r = ⌈band ÷ res⌉ + 1.
    """
    ch = np.asarray(changed, bool)
    if prev_band is None:
        return edge_band(height_mm, res_mm, band_mm, step_mm)
    out = prev_band.copy()
    if not ch.any():
        return out
    ny, nx = ch.shape
    r = int(math.ceil(band_mm / res_mm)) + 1
    iy, ix = np.nonzero(ch)
    cy0, cy1, cx0, cx1 = iy.min() - 1, iy.max() + 2, ix.min() - 1, ix.max() + 2
    wy0, wy1, wx0, wx1 = max(cy0 - r, 0), min(cy1 + r, ny), max(cx0 - r, 0), min(cx1 + r, nx)
    ey0, ey1, ex0, ex1 = max(wy0 - r, 0), min(wy1 + r, ny), max(wx0 - r, 0), min(wx1 + r, nx)
    # 경계 필터가 창 가장자리에서도 전체 계산과 같도록 1칸 더 붙여 계산
    fy0, fy1, fx0, fx1 = max(ey0 - 1, 0), min(ey1 + 1, ny), max(ex0 - 1, 0), min(ex1 + 1, nx)
    h = np.asarray(height_mm, float)[fy0:fy1, fx0:fx1]
    b = height_boundary(h, step_mm)[ey0 - fy0:ey1 - fy0, ex0 - fx0:ex1 - fx0]
    if b.any():
        d = ndimage.distance_transform_edt(~b) * res_mm
        be = d <= band_mm + _TOL_MM
    else:
        be = np.zeros(b.shape, bool)
    out[wy0:wy1, wx0:wx1] = be[wy0 - ey0:wy1 - ey0, wx0 - ex0:wx1 - ex0]
    return out


def predict_occlusion(height_mm, res_mm: float, theta_deg: float, camera_side: str) -> np.ndarray:
    """카메라 시선이 더 높은 곳에 막히는 칸 (넓히기 전).

    레이저는 수직, 카메라는 수직에서 θ 기울어 ±Y 쪽 (명세 0.4: 스캔 = 프린터 Y).
    칸 p에서 카메라 쪽으로 s 간 곳 높이 > z_p + s / tanθ 이면 가림.
    -y: 카메라가 -Y 쪽 → p보다 작은 y의 칸을 본다. 식을 바꾸면
        max_{u < y} (H(u) + u·k) > H(y) + y·k,  k = 1/tanθ  (열마다 누적 최댓값 한 번).
    """
    if camera_side not in ("+y", "-y", "both"):
        raise ValueError(f"camera_side: {camera_side!r}")
    h = bed_height(height_mm)
    k = 1.0 / math.tan(math.radians(theta_deg))
    y = (np.arange(h.shape[0], dtype=float) * res_mm)[:, None]
    out = np.zeros(h.shape, bool)
    if h.shape[0] < 2:
        return out
    if camera_side in ("-y", "both"):
        v = h + y * k
        cm = np.maximum.accumulate(v, axis=0)
        out[1:] |= cm[:-1] > v[1:] + _TOL_MM          # 앞 줄까지의 최댓값 (자기 칸 뺌)
    if camera_side in ("+y", "both"):
        w = h - y * k
        cm = np.maximum.accumulate(w[::-1], axis=0)[::-1]
        out[:-1] |= cm[1:] > w[:-1] + _TOL_MM          # 뒤 줄부터의 최댓값
    return out


def grow(mask, cells: int) -> np.ndarray:
    """정사각 이웃 (8방향)으로 cells칸 넓힘."""
    m = np.asarray(mask, bool)
    if cells <= 0 or not m.any():
        return m.copy()
    return ndimage.binary_dilation(m, structure=np.ones((3, 3), bool), iterations=int(cells))


def depth_out(height_mm, z_layer_mm: float, dof_mm: float, top_mm: float) -> np.ndarray:
    """층 n 스캔의 심도 창 [z_n + top − dof, z_n + top] 아래에 있는 출력물 칸.

    비교는 nm 정수. 창 아래 끝과 같으면 창 안. NaN (출력물 없음)은 False.
    창 위 (높이 > z_n + top)는 층마다 재면 생기지 않음 (윗면 ≤ z_n). top < 0이면 위로 벗어나는 칸도 심도 밖.
    """
    h = np.asarray(height_mm, float)
    mat = ~np.isnan(h)
    hn = np.where(mat, _nm(np.where(mat, h, 0.0)), 0)
    lo = int(np.rint((z_layer_mm + top_mm - dof_mm) * 1e6))
    hi = int(np.rint((z_layer_mm + top_mm) * 1e6))
    return mat & ((hn < lo) | (hn > hi))


def type_mask(type_codes, type_names, exclude_types) -> np.ndarray:
    """꼭대기 층 종류 코드 (type_at, −1 = 없음)가 exclude_types인 칸."""
    tc = np.asarray(type_codes)
    ex = {str(t).upper() for t in exclude_types}
    bad = [i for i, t in enumerate(type_names) if str(t).upper() in ex]
    if not bad:
        return np.zeros(tc.shape, bool)
    return np.isin(tc, bad)


def prime_width(result) -> float:
    """퍼지선 선폭: 머리말 첫 층 → 기본 → config line_width_mm. 모두 없으면 오류."""
    hw = result.header.get("line_widths") or {}
    for key in ("FIRST_LAYER", "DEFAULT"):
        if hw.get(key):
            return float(hw[key])
    p = result.params
    if p is not None and p.line_width_mm:
        return float(p.line_width_mm)
    raise GCodeError("퍼지선 선폭을 모름: 머리말에 없고 config line_width_mm도 비어 있음")


def prime_mask(result, grid: dict) -> tuple:
    """PRIME 압출 선분 (층 −1)이 덮는 격자 칸 (캡슐, T4a 발자국과 같은 식).

    반환 (mask, info). info = {n_segments, n_segments_in_grid, n_cells}.
    """
    s = result.segments
    sel = s[(s.kind == "extrude") & (s.type == "PRIME")]
    mask = np.zeros((grid["ny"], grid["nx"]), bool)
    n_in = n_nan = 0
    if len(sel):
        r = prime_width(result) / 2.0
        for x0, y0, x1, y1 in sel[["x0_mm", "y0_mm", "x1_mm", "y1_mm"]].to_numpy(float):
            if not np.isfinite([x0, y0, x1, y1]).all():
                n_nan += 1  # 위치를 모르는 퍼지 압출 (T4a 경고 "위치 모르는 압출 … PRIME으로 둠")
                continue
            cells = capsule_cells(grid, float(x0), float(y0), float(x1), float(y1), r)
            if cells is None or len(cells[0]) == 0:
                continue
            mask[cells[0], cells[1]] = True
            n_in += 1
    return mask, {"n_segments": int(len(sel)), "n_segments_in_grid": n_in, "n_unknown_pos": n_nan,
                  "n_cells": int(mask.sum())}
