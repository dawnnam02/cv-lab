"""고운 격자 (0.02 mm) → 판정 칸 묶기.

- 판정 칸 (jy, jx)는 고운 칸 iy ∈ [jy·f, (jy+1)·f), ix ∈ [jx·f, (jx+1)·f)를 묶는다. 배열 순서 A[iy, ix].
- 가장자리에서 f칸이 안 차는 묶음은 버린다 (판정 영역 밖).
- 영역 칸: 묶음 안 판정 영역 고운 칸 비율 ≥ region_fill_min.
- 유효 칸: 영역 칸 중, 영역 안 고운 칸 가운데 Δ 있는 칸 비율 ≥ fill_min.
- 칸 값: 영역 안 유효한 고운 칸 Δ의 평균 (선택 median).
- 비율 비교는 분수로 정확히 한다.
"""
from __future__ import annotations

import warnings
from fractions import Fraction

import numpy as np

EXCLUSION_CODES = (0, 1, 2, 3, 4, 5, 6, 9)  # 6 심도 밖 (J-2에서 더함, T4b §2 · §5)


def cell_factor(cell_mm: float, res_mm: float) -> int:
    """칸 크기 ÷ 격자 간격이 정수면 그 정수, 아니면 ValueError."""
    if not (res_mm > 0 and cell_mm > 0):
        raise ValueError("cell_mm · res_mm는 0보다 커야 함")
    ratio = Fraction(str(cell_mm)) / Fraction(str(res_mm))
    if ratio.denominator != 1 or ratio < 1:
        raise ValueError(f"칸 크기 {cell_mm} mm ÷ 격자 간격 {res_mm} mm = {float(ratio)} 가 1 이상의 정수가 아님")
    return int(ratio)


def _check_factor(factor) -> int:
    if isinstance(factor, bool):
        raise ValueError("factor: 정수가 아님")
    if isinstance(factor, (int, np.integer)):
        f = int(factor)
    elif isinstance(factor, float) and factor.is_integer():
        f = int(factor)
    else:
        raise ValueError(f"factor: 정수가 아님 ({factor!r})")
    if f < 1:
        raise ValueError(f"factor: 1 이상이어야 함 ({f})")
    return f


def _blocks(a: np.ndarray, f: int) -> np.ndarray:
    ny, nx = a.shape[0] // f, a.shape[1] // f
    return a[: ny * f, : nx * f].reshape(ny, f, nx, f)


def aggregate_to_cells(delta_fine_mm, valid_fine=None, region_fine=None, factor=10, stat="mean",
                       fill_min=0.5, region_fill_min=1.0):
    """(delta_cell_mm, valid_cell, region_cell)을 돌려준다.

    delta_cell_mm은 유효 칸만 값이 있고 나머지는 NaN. valid_cell ⊂ region_cell.
    """
    d = np.asarray(delta_fine_mm, dtype=float)
    if d.ndim != 2:
        raise ValueError("delta_fine_mm: 2차원 배열이어야 함")
    f = _check_factor(factor)
    if stat not in ("mean", "median"):
        raise ValueError(f"stat: mean 또는 median ({stat!r})")
    if not (0 < fill_min <= 1) or not (0 < region_fill_min <= 1):
        raise ValueError("fill_min · region_fill_min은 (0, 1] 범위")
    valid = np.isfinite(d) if valid_fine is None else (np.asarray(valid_fine, dtype=bool) & np.isfinite(d))
    region = np.ones(d.shape, bool) if region_fine is None else np.asarray(region_fine, dtype=bool)
    if valid.shape != d.shape or region.shape != d.shape:
        raise ValueError("valid_fine · region_fine 모양이 delta_fine_mm과 다름")
    ny, nx = d.shape[0] // f, d.shape[1] // f
    if ny == 0 or nx == 0:
        empty_f = np.zeros((ny, nx))
        return np.full((ny, nx), np.nan), empty_f.astype(bool), empty_f.astype(bool)

    use = valid & region
    n_reg = _blocks(region, f).sum(axis=(1, 3))
    n_use = _blocks(use, f).sum(axis=(1, 3))

    rf = Fraction(str(region_fill_min))
    vf = Fraction(str(fill_min))
    region_cell = n_reg * rf.denominator >= rf.numerator * (f * f)
    valid_cell = region_cell & (n_reg > 0) & (n_use * vf.denominator >= vf.numerator * n_reg) & (n_use > 0)

    if stat == "mean":
        s = _blocks(np.where(use, d, 0.0), f).sum(axis=(1, 3))
        with np.errstate(invalid="ignore", divide="ignore"):
            val = s / n_use
    else:
        b = _blocks(np.where(use, d, np.nan), f).transpose(0, 2, 1, 3).reshape(ny, nx, f * f)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            val = np.nanmedian(b, axis=2)
    delta_cell = np.where(valid_cell, val, np.nan)
    return delta_cell, valid_cell, region_cell


def aggregate_mask_any(mask_fine, factor) -> np.ndarray:
    """묶음 안에 True가 하나라도 있으면 True (이상치 칸 표시용)."""
    m = np.asarray(mask_fine, dtype=bool)
    return _blocks(m, _check_factor(factor)).any(axis=(1, 3))


def aggregate_exclusion_code(code_fine, factor) -> np.ndarray:
    """묶음 안 0이 아닌 코드 중 가장 많은 것 (같으면 작은 코드). 0이 아닌 코드가 없으면 0."""
    c = np.asarray(code_fine)
    bad = ~np.isin(c, EXCLUSION_CODES)
    if bad.any():
        raise ValueError(f"exclusion_code: 코드표 {EXCLUSION_CODES} 밖 값 {sorted(set(np.unique(c[bad]).tolist()))}")
    f = _check_factor(factor)
    nz = [k for k in EXCLUSION_CODES if k != 0]
    counts = np.stack([_blocks(c == k, f).sum(axis=(1, 3)) for k in nz], axis=0)
    best = np.asarray(nz, dtype=np.int8)[np.argmax(counts, axis=0)]
    return np.where(counts.max(axis=0) > 0, best, 0).astype(np.int8)
