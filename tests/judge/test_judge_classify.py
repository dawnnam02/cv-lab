import math

import numpy as np
import pytest

from cvlab.judge import FAIL, HOLD, NODATA, PASS, classify_cells, thresholds_nm
from judge_maps import T, U


def test_m02_boundary_values():
    # |Δ| = 0.170 · 0.170001 · 0.230 · 0.230001, 양·음 부호
    v = np.array([0.170, 0.170001, 0.230, 0.230001])
    exp = [PASS, HOLD, HOLD, FAIL]
    assert classify_cells(v, T, U).tolist() == exp
    assert classify_cells(-v, T, U).tolist() == exp


def test_float_subtraction_does_not_move_boundary():
    # 실수 뺄셈이면 0.2 − 0.171 = 0.028999999999999998, 0.2 + 0.141 = 0.34099999999999997
    assert 0.029 > 0.2 - 0.171 and 0.341 > 0.2 + 0.141
    assert classify_cells([0.029], 0.2, 0.171)[0] == PASS      # 실수 비교였다면 보류
    assert classify_cells([0.341], 0.2, 0.141)[0] == HOLD      # 실수 비교였다면 불합격
    assert classify_cells([0.17], 0.2, 0.03)[0] == PASS
    # T2 기본 RSS U = 31.7 µm: 합격 ≤ 0.1683, 불합격 > 0.2317
    v = [0.1683, 0.168301, 0.2317, 0.231701]
    assert classify_cells(v, 0.2, 0.0317).tolist() == [PASS, HOLD, HOLD, FAIL]


def test_thresholds_nm_values():
    assert thresholds_nm(0.2, 0.03) == (170000, 230000)
    assert thresholds_nm(0.2, 0.0669) == (133100, 266900)
    assert thresholds_nm(0.2, 0.0) == (200000, 200000)


def test_m09_sign_symmetry():
    rng = np.random.default_rng(1)
    d = rng.normal(0.15, 0.06, size=(30, 30))
    assert np.array_equal(classify_cells(d, T, U), classify_cells(-d, T, U))


def test_m10_u_zero_equals_method_a():
    v = np.array([0.0, 0.199999, 0.2, 0.200001, -0.2, -0.200001])
    c = classify_cells(v, T, 0.0)
    assert c.tolist() == [PASS, PASS, PASS, FAIL, PASS, FAIL]
    assert (c != HOLD).all()


@pytest.mark.parametrize("bad", [-0.001, 0.2, 0.25, float("nan"), None])
def test_m11_bad_u_errors(bad):
    with pytest.raises(ValueError):
        classify_cells([0.0], T, bad)


def test_nan_is_nodata_inf_rejected():
    c = classify_cells([[np.nan, 0.0]], T, U)
    assert c.tolist() == [[NODATA, PASS]]
    with pytest.raises(ValueError):
        classify_cells([np.inf], T, U)


def test_classify_dtype_shape():
    d = np.zeros((3, 4))
    c = classify_cells(d, T, U)
    assert c.dtype == np.int8 and c.shape == (3, 4)
    assert not math.isnan(float(c.sum()))
