"""판정 시험 도우미. 지도 값은 시험용 입력이며 측정값이 아니다."""
import numpy as np

from cvlab.judge import JudgeParams, LayerInput

T = 0.20
U = 0.03


def params(U_mm=U, **kw):
    return JudgeParams(T_mm=T, U_mm=U_mm, U_source=kw.pop("U_source", "시험용 가정 (손계산)"), **kw)


def layer(a, idx=0, region=None, state="in_process", **kw):
    a = np.asarray(a, dtype=float)
    if region is None:
        region = np.ones(a.shape, bool)
    return LayerInput(layer_idx=idx, thermal_state=state, delta_mm=a, region=np.asarray(region, bool), **kw)


def counts_map(n_pass, n_hold, n_fail, shape, v_pass=0.0, v_hold=0.2, v_fail=0.3):
    """정해진 개수의 합격·보류·불합격 값을 가진 지도 (U = 0.03 기준)."""
    a = np.r_[np.full(n_pass, v_pass), np.full(n_hold, v_hold), np.full(n_fail, v_fail)]
    assert a.size == shape[0] * shape[1]
    return a.reshape(shape)


def texture_fine(amp=0.025, base=0.10, period=0.4, nx=40, ny=20, res=0.02):
    """결 지도 M13: Δ = base + amp·sin(2πx/period), x = 0.01, 0.03, … (고운 칸 중심)."""
    x = res / 2 + res * np.arange(nx)
    row = base + amp * np.sin(2 * np.pi * x / period)
    return np.tile(row, (ny, 1))
