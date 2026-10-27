"""격자 약속 (세부청사진 §6.1, T15와 같은 글).

좌표 {G} mm, 배열 A[iy, ix], 칸 중심 x = x0_mm + ix·res_mm. x0_mm·y0_mm은 res_mm의 정수배 (내림).
"""
from __future__ import annotations

import math

import numpy as np


def make_grid(xmin: float, xmax: float, ymin: float, ymax: float,
              res_mm: float = 0.02, margin_mm: float = 1.0) -> dict:
    if not (xmax >= xmin and ymax >= ymin) or res_mm <= 0:
        raise ValueError("격자 범위가 잘못됨")
    ix0 = math.floor((xmin - margin_mm) / res_mm + 1e-9)
    iy0 = math.floor((ymin - margin_mm) / res_mm + 1e-9)
    ix1 = math.ceil((xmax + margin_mm) / res_mm - 1e-9)
    iy1 = math.ceil((ymax + margin_mm) / res_mm - 1e-9)
    return {"frame": "G", "x0_mm": round(ix0 * res_mm, 10), "y0_mm": round(iy0 * res_mm, 10),
            "res_mm": float(res_mm), "nx": int(ix1 - ix0 + 1), "ny": int(iy1 - iy0 + 1)}


def cell_centers(grid: dict):
    x = grid["x0_mm"] + np.arange(grid["nx"]) * grid["res_mm"]
    y = grid["y0_mm"] + np.arange(grid["ny"]) * grid["res_mm"]
    return x, y


def extent(grid: dict) -> tuple:
    """matplotlib imshow(origin='lower', extent=...)용 칸 가장자리 범위."""
    h = grid["res_mm"] / 2.0
    x0, y0 = grid["x0_mm"], grid["y0_mm"]
    return (x0 - h, x0 + (grid["nx"] - 1) * grid["res_mm"] + h,
            y0 - h, y0 + (grid["ny"] - 1) * grid["res_mm"] + h)


def index_of(grid: dict, x: float, y: float) -> tuple:
    """(x, y)에 가장 가까운 칸 (iy, ix)."""
    return (int(round((y - grid["y0_mm"]) / grid["res_mm"])), int(round((x - grid["x0_mm"]) / grid["res_mm"])))


def value_at(grid: dict, arr, x: float, y: float, fill=np.nan):
    """배열 A[iy, ix]에서 (x, y) 칸 값. 격자 밖이면 fill."""
    iy, ix = index_of(grid, x, y)
    if 0 <= iy < grid["ny"] and 0 <= ix < grid["nx"]:
        return arr[iy, ix]
    return fill
