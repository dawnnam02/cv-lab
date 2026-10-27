"""스캔 패스와 시야 밖 (RG6, 세부청사진 §6.5 약속. T5와 같은 글, 서로 독립 구현).

- 경계 상자 B = object_bbox (판정 대상 압출 끝점 상자 + 선폭 최댓값의 반). 폭 W (X), 높이 H (Y).
- X 패스 수 n_x = max(1, ⌈(W − o) ÷ (F − o)⌉), F = fov_mm, o = overlap_mm.
- Y 패스 수 n_y = max(1, ⌈(H − o) ÷ (L − o)⌉), L = scan_len_mm. extend_scan_len이면 n_y = 1, L = H.
- 덮는 폭 S = n·F − (n − 1)·o를 B 가운데에 맞춤. 패스 i = [c − S/2 + i(F − o), 그 + F].
- 시야 안 = 칸 중심이 어느 패스 사각형 안 (경계 포함).
X 패스 번호 i = 명세 meta.scan_pass_idx. Y를 나눈 번호 (y_part_idx)는 명세에 없음 (문서 §12).
"""
from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

_TOL_MM = 1e-9


def _F(x) -> Fraction:
    # 상자 폭은 실수 뺄셈이라 1e-9 mm로 반올림한 뒤 분수로 (18.000000000000004 → 18)
    return Fraction(str(round(float(x), 9)))


def n_passes(width_mm: float, span_mm: float, overlap_mm: float) -> int:
    W, F, o = _F(width_mm), _F(span_mm), _F(overlap_mm)
    if F <= o:
        raise ValueError("패스 폭은 겹침보다 커야 함")
    return max(1, math.ceil((W - o) / (F - o)))


def _axis(lo: float, hi: float, span: float, overlap: float, n: int) -> list:
    c = (lo + hi) / 2.0
    S = n * span - (n - 1) * overlap
    return [(c - S / 2.0 + i * (span - overlap), c - S / 2.0 + i * (span - overlap) + span) for i in range(n)]


def plan_passes(bbox, fov_mm: float = 20.0, scan_len_mm: float = 40.0, overlap_mm: float = 2.0,
                extend_scan_len: bool = False) -> list:
    """패스 목록. 패스마다 {"x0_mm","x1_mm","y0_mm","y1_mm","scan_pass_idx","y_part_idx"} ({G} mm)."""
    xmin, xmax, ymin, ymax = (float(v) for v in bbox)
    if not (xmax >= xmin and ymax >= ymin):
        raise ValueError("경계 상자가 잘못됨")
    W, H = xmax - xmin, ymax - ymin
    nx = n_passes(W, fov_mm, overlap_mm)
    if extend_scan_len:
        ny, L = 1, max(H, 0.0)
        ys = [(ymin, ymax)]
    else:
        ny, L = n_passes(H, scan_len_mm, overlap_mm), scan_len_mm
        ys = _axis(ymin, ymax, L, overlap_mm, ny)
    xs = _axis(xmin, xmax, fov_mm, overlap_mm, nx)
    out = []
    for i, (a, b) in enumerate(xs):
        for j, (c, d) in enumerate(ys):
            out.append({"x0_mm": float(a), "x1_mm": float(b), "y0_mm": float(c), "y1_mm": float(d),
                        "scan_pass_idx": i, "y_part_idx": j})
    return out


def pass_counts(passes) -> tuple:
    """(X 패스 수, Y 패스 수)."""
    if not passes:
        return (0, 0)
    return (len({p.get("scan_pass_idx", i) for i, p in enumerate(passes)}),
            len({p.get("y_part_idx", 0) for p in passes}))


def coverage_mask(grid: dict, passes) -> np.ndarray:
    """칸 중심이 어느 패스 사각형 안 (경계 포함)이면 True."""
    xs = grid["x0_mm"] + np.arange(grid["nx"]) * grid["res_mm"]
    ys = grid["y0_mm"] + np.arange(grid["ny"]) * grid["res_mm"]
    out = np.zeros((grid["ny"], grid["nx"]), bool)
    for p in passes:
        inx = (xs >= p["x0_mm"] - _TOL_MM) & (xs <= p["x1_mm"] + _TOL_MM)
        iny = (ys >= p["y0_mm"] - _TOL_MM) & (ys <= p["y1_mm"] + _TOL_MM)
        out |= iny[:, None] & inx[None, :]
    return out
