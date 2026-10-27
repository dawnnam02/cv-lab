import math

import numpy as np
import pytest

from cvlab.judge import aggregate_to_cells, cell_factor
from cvlab.judge.aggregate import aggregate_exclusion_code
from judge_maps import texture_fine


def test_cell_factor_integer_or_error():
    assert cell_factor(0.2, 0.02) == 10
    assert cell_factor(0.4, 0.02) == 20
    for bad in (0.25, 0.03, 0.01):
        with pytest.raises(ValueError):
            cell_factor(bad, 0.02)


def test_factor_must_be_integer():
    d = np.zeros((20, 20))
    with pytest.raises(ValueError):
        aggregate_to_cells(d, None, None, 2.5)
    with pytest.raises(ValueError):
        aggregate_to_cells(d, None, None, 0)
    out = aggregate_to_cells(d, None, None, 10.0)
    assert out[0].shape == (2, 2)


def test_m12_fill_49_vs_50():
    # 10 × 10 묶음 하나, Δ 있는 고운 칸 49개 → 무효 칸, 50개 → 유효 칸 (값은 유효 칸 평균)
    base = np.arange(100, dtype=float).reshape(10, 10) / 1000.0
    d49 = base.copy(); d49.flat[49:] = np.nan
    d50 = base.copy(); d50.flat[50:] = np.nan
    c49, v49, r49 = aggregate_to_cells(d49, None, None, 10)
    c50, v50, r50 = aggregate_to_cells(d50, None, None, 10)
    assert r49[0, 0] and r50[0, 0]
    assert not v49[0, 0] and math.isnan(c49[0, 0])
    assert v50[0, 0]
    assert c50[0, 0] == pytest.approx(np.mean(np.arange(50)) / 1000.0, abs=1e-15)  # 0.0245


def test_edge_blocks_dropped():
    d = np.zeros((25, 37))
    c, v, r = aggregate_to_cells(d, None, None, 10)
    assert c.shape == (2, 3) and v.all() and r.all()


def test_region_fill_min():
    d = np.zeros((10, 10))
    reg = np.ones((10, 10), bool); reg[0, 0] = False
    _, v1, r1 = aggregate_to_cells(d, None, reg, 10, region_fill_min=1.0)
    _, v2, r2 = aggregate_to_cells(d, None, reg, 10, region_fill_min=0.99)
    assert not r1[0, 0] and not v1[0, 0]
    assert r2[0, 0] and v2[0, 0]


def test_median_stat():
    d = np.zeros((10, 10)); d[0, :3] = 1.0   # 평균 0.03, 중앙값 0
    cm, _, _ = aggregate_to_cells(d, None, None, 10, stat="mean")
    cd, _, _ = aggregate_to_cells(d, None, None, 10, stat="median")
    assert cm[0, 0] == pytest.approx(0.03)
    assert cd[0, 0] == 0.0


def test_m13_texture_cell_02_vs_04():
    fine = texture_fine()
    c2, _, _ = aggregate_to_cells(fine, None, None, 10)
    c4, _, _ = aggregate_to_cells(fine, None, None, 20)
    amp = 0.025 / (10 * math.sin(math.pi / 20))          # 0.015981
    assert amp == pytest.approx(0.015981, abs=5e-7)
    assert c2[0].tolist() == pytest.approx([0.10 + amp, 0.10 - amp, 0.10 + amp, 0.10 - amp], abs=1e-12)
    assert c4[0].tolist() == pytest.approx([0.10, 0.10], abs=1e-12)


def test_exclusion_code_aggregate():
    code = np.zeros((20, 20), np.int8)
    code[:10, :10] = 1
    code[:10, 10:] = 2; code[0, 10:15] = 3
    code[10:, :10] = 0
    code[10:, 10:] = 9
    out = aggregate_exclusion_code(code, 10)
    assert out.tolist() == [[1, 2], [0, 9]]
    with pytest.raises(ValueError):
        aggregate_exclusion_code(np.full((10, 10), 7), 10)
