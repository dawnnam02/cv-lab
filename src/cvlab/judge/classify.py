"""점 분류 (가드밴드 방식 B, D-07).

합격점 |Δ| ≤ T − U, 불합격점 |Δ| > T + U, 그 사이 보류점.
경계 비교는 1 nm 단위로 반올림한 정수로 한다 (실수 뺄셈 오차가 경계를 바꾸지 않게).
"""
from __future__ import annotations

import numpy as np

from .params import check_U

PASS, HOLD, FAIL, NODATA = 1, 0, -1, -9
NM_PER_MM = 1_000_000


def to_nm(x_mm) -> np.ndarray:
    """mm 값을 nm 정수 (int64)로. NaN은 넣지 말 것."""
    return np.rint(np.asarray(x_mm, dtype=float) * NM_PER_MM).astype(np.int64)


def thresholds_nm(T_mm: float, U_mm: float) -> tuple[int, int]:
    """(t_pass, t_fail) nm 정수. t_pass = rint((T−U)·10⁶), t_fail = rint((T+U)·10⁶)."""
    T = float(T_mm)
    U = float(U_mm)
    t_pass = int(np.rint((T - U) * NM_PER_MM))
    t_fail = int(np.rint((T + U) * NM_PER_MM))
    return t_pass, t_fail


def classify_cells(delta_mm, T_mm: float, U_mm: float) -> np.ndarray:
    """칸마다 1 합격점, 0 보류점, −1 불합격점, −9 값 없음 (NaN). 결과는 int8, 입력과 같은 모양."""
    if not (np.isfinite(T_mm) and float(T_mm) > 0):
        raise ValueError(f"T_mm: 0보다 큰 유한한 값이어야 함 ({T_mm!r})")
    U = check_U(T_mm, U_mm)
    d = np.asarray(delta_mm, dtype=float)
    if np.isinf(d).any():
        raise ValueError("delta_mm: 무한대 값이 있음")
    t_pass, t_fail = thresholds_nm(T_mm, U)
    nan = np.isnan(d)
    q = np.zeros(d.shape, dtype=np.int64)
    q[~nan] = to_nm(np.abs(d[~nan]))
    out = np.full(d.shape, HOLD, dtype=np.int8)
    out[q <= t_pass] = PASS
    out[q > t_fail] = FAIL
    out[nan] = NODATA
    return out
