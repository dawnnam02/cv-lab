"""T7a 추출 방법 시험 (LX1 · LX2 · LX8). 단순 합성 영상만 씀 (tri_synth, T3 시뮬레이터가 아님)."""
import numpy as np
import pytest

from cvlab.triangulation import METHODS, TriParams, extract_centers
from tri_synth import SCENARIOS, synth


def _err(sc, method, rng=0, **kw):
    img, vt, lc = synth(sc, rng=rng)
    v, fl = extract_centers(img, method, bit_depth=SCENARIOS[sc]["bit"], **kw)
    return v, fl, (v.astype(np.float64) - vt)[lc]


def test_methods_tuple_fixed():
    assert METHODS == ("max", "cog", "parabola3", "gauss3", "gaussfit", "steger")


@pytest.mark.parametrize("method", METHODS)
def test_output_types_all_methods(method):
    img, vt, lc = synth("nominal_10bit", rng=1)
    v, fl = extract_centers(img, method=method, bit_depth=10)
    assert v.dtype == np.float32 and v.shape == (img.shape[1],)
    assert fl.dtype == np.uint8 and fl.shape == (img.shape[1],)
    assert np.isfinite(v).mean() > 0.99


def test_unknown_method_rejected():
    img, _, _ = synth("nominal_10bit")
    with pytest.raises(ValueError):
        extract_centers(img, method="centroid")


@pytest.mark.parametrize("sc", ["f1_basic_8bit", "nominal_10bit"])
def test_cog_basic_accuracy(sc):
    """F1 7절 #1: |bias| < 0.02 px, RMS < 0.15 px, 유효 100 %."""
    v, fl, e = _err(sc, "cog")
    assert np.isfinite(e).all()
    assert abs(e.mean()) < 0.02
    assert np.sqrt((e ** 2).mean()) < 0.15


def test_gauss3_noiseless_exact():
    """F1 7절 #2: 무잡음에서 gauss3 최대 오차 < 0.05 px."""
    v, fl, e = _err("noiseless_10bit", "gauss3")
    assert np.isfinite(e).all() and np.abs(e).max() < 0.05


@pytest.mark.parametrize("method", ["cog", "gaussfit", "steger"])
def test_subpixel_methods_beat_max(method):
    _, _, e_max = _err("nominal_10bit", "max")
    _, _, e = _err("nominal_10bit", method)
    assert np.sqrt(np.nanmean(e ** 2)) < 0.5 * np.sqrt(np.nanmean(e_max ** 2))


def test_cog_uses_threshold_subtracted_weights():
    """문턱을 빼지 않으면 창 가운데로 끌림 (F1 §8). 한 열 손 계산과 비교."""
    img = np.full((40, 1), 10.0)
    img[18:23, 0] = [20, 60, 100, 80, 20]
    p = TriParams(half_win_px=3, guide_band_px=None)
    v, fl = extract_centers(img, "cog", params=p)
    rows = np.arange(17, 24)
    vals = img[17:24, 0]
    thr = 10.0 + 5 * 0.5                 # MAD = 0 → σ 바닥 0.5 DN
    w = np.maximum(vals - thr, 0)
    assert abs(v[0] - (w * rows).sum() / w.sum()) < 1e-5


def test_background_frame_subtraction():
    """레이저 끈 프레임을 빼면 기울어진 주변광이 있어도 치우침이 작음."""
    img, vt, lc = synth("nominal_10bit", rng=2)
    ramp = (np.arange(img.shape[0])[:, None] * 1.5 + 0 * np.arange(img.shape[1])[None, :]).astype(np.uint16)
    v, _ = extract_centers(img + ramp, "cog", background=ramp, bit_depth=10)
    e = v - vt
    assert abs(np.nanmean(e)) < 0.02 and np.sqrt(np.nanmean(e ** 2)) < 0.15


def test_float_image_accepted():
    img, vt, lc = synth("noiseless_10bit")
    assert img.dtype.kind == "f"
    v, _ = extract_centers(img, "cog")
    assert np.nanmax(np.abs(v - vt)) < 0.01


def test_skewed_profile_bias_positive_and_reported():
    """LX8 (보고만): 꼬리 (+v 쪽) 단면에서 모든 서브픽셀 방법이 +v 쪽으로 치우침. 문턱 없음, 부호만 확인."""
    for m in ("cog", "gauss3", "steger"):
        _, _, e = _err("skewed_10bit", m)
        assert np.nanmean(e) > 0.3


def test_steger_low_signal_runs():
    _, _, e = _err("low_10bit", "steger")
    assert np.isfinite(e).mean() == 1.0 and np.sqrt(np.mean(e ** 2)) < 0.3


def test_fast_row_argmax_equals_numpy():
    """속도용 묶음 argmax가 np.argmax(axis=0)와 같은 값 (같은 값이면 첫 행)."""
    from cvlab.triangulation import _core

    rng = np.random.default_rng(0)
    for h in (3, 15, 16, 17, 256, 801):
        a = rng.integers(0, 5, (h, 300)).astype(np.uint16)
        assert np.array_equal(_core.argmax_rows(a), a.argmax(axis=0))
        f = rng.normal(size=(h, 300)).astype(np.float32)
        assert np.array_equal(_core.argmax_rows(f), f.argmax(axis=0))
