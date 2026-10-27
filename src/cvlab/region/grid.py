"""판정 격자: 대상 경계 상자와 원점 맞춤 (RG1, 세부청사진 §6.1 · §6.5).

격자 약속은 T4a와 같음: {G} mm, A[iy, ix], 칸 중심 x = x0_mm + ix·res_mm.
원점 맞춤: x0_mm · y0_mm = cell_mm (0.4)의 정수배 (내림), nx · ny = cell_mm ÷ res_mm (20)의 배수 (올림).
정수배 계산은 Fraction(str(x))로 한다 (실수 나머지 안 씀).
"""
from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

from cvlab.gcode import GCodeError, GCodeParams
from cvlab.gcode.reference import segment_widths

from .params import DEFAULT_EXCLUDE


def _F(x) -> Fraction:
    return Fraction(str(float(x)))


def target_segments(result, exclude_types=DEFAULT_EXCLUDE, params: GCodeParams | None = None):
    """판정 대상 압출 선분 (층 ≥ 0, 종류가 exclude_types 밖)과 그 선폭."""
    p = params or result.params or GCodeParams()
    seg = result.extrusions()
    w = segment_widths(result, p)
    ex = {str(t).upper() for t in exclude_types}
    keep = ~seg["type"].isin(ex).to_numpy()
    return seg[keep], w[keep]


def object_bbox(result, exclude_types=DEFAULT_EXCLUDE, params: GCodeParams | None = None) -> tuple:
    """판정 대상 압출 선분 끝점의 경계 상자를 그 선분들 선폭 최댓값의 반만큼 넓힌 것 (§6.5).

    반환 (xmin, xmax, ymin, ymax), {G} mm. 대상 선분이 없으면 GCodeError.
    """
    seg, w = target_segments(result, exclude_types, params)
    if seg.empty:
        raise GCodeError("판정 대상 종류의 압출 선분이 없음 (모두 exclude_types)")
    h = float(np.max(w)) / 2.0
    xs = np.concatenate([seg.x0_mm.to_numpy(float), seg.x1_mm.to_numpy(float)])
    ys = np.concatenate([seg.y0_mm.to_numpy(float), seg.y1_mm.to_numpy(float)])
    return (float(xs.min() - h), float(xs.max() + h), float(ys.min() - h), float(ys.max() + h))


def aligned_grid(xmin: float, xmax: float, ymin: float, ymax: float,
                 res_mm: float = 0.02, cell_mm: float = 0.4, margin_mm: float = 1.0) -> dict:
    """원점을 cell_mm 배수로 내리고 칸 수를 (cell_mm ÷ res_mm) 배수로 올린 격자 JSON."""
    if not (xmax >= xmin and ymax >= ymin):
        raise ValueError("격자 범위가 잘못됨")
    fr, fc, fm = _F(res_mm), _F(cell_mm), _F(margin_mm)
    if fr <= 0 or fc <= 0 or fm < 0:
        raise ValueError("res_mm · cell_mm는 0보다 크고 margin_mm은 0 이상")
    f = fc / fr
    if f.denominator != 1:
        raise ValueError(f"cell_mm {cell_mm} ÷ res_mm {res_mm}가 정수가 아님")
    f = int(f)

    def axis(lo, hi):
        a = _F(lo) - fm
        b = _F(hi) + fm
        k0 = math.floor(a / fc)
        o = k0 * fc
        n = math.ceil((b - o) / fr) + 1
        n = int(math.ceil(n / f) * f)
        return o, n

    x0, nx = axis(xmin, xmax)
    y0, ny = axis(ymin, ymax)
    return {"frame": "G", "x0_mm": float(x0), "y0_mm": float(y0), "res_mm": float(res_mm),
            "nx": int(nx), "ny": int(ny)}


def is_aligned(grid: dict, cell_mm: float = 0.4) -> bool:
    """격자 원점이 cell_mm 배수이고 칸 수가 cell_mm ÷ res_mm 배수인지."""
    fc = _F(cell_mm)
    f = fc / _F(grid["res_mm"])
    if f.denominator != 1:
        return False
    f = int(f)
    return ((_F(grid["x0_mm"]) / fc).denominator == 1 and (_F(grid["y0_mm"]) / fc).denominator == 1
            and grid["nx"] % f == 0 and grid["ny"] % f == 0)
