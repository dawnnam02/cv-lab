"""T7a ROI · 비트 깊이 시험 (LX9)."""
import numpy as np
import pytest

from cvlab.triangulation import METHODS, extract_centers, roi_to_full
from tri_synth import SCENARIOS, make_vtrue, synth


def test_roi_to_full_adds_offset():
    v = np.array([1.25, np.nan, 100.0], np.float32)
    out = roi_to_full(v, 272)
    assert out.dtype == np.float32
    assert out[0] == np.float32(273.25) and np.isnan(out[1]) and out[2] == 372


@pytest.mark.parametrize("sc", ["f1_basic_8bit", "nominal_10bit"])
@pytest.mark.parametrize("method", METHODS)
def test_crop_matches_full_frame(sc, method):
    """전체 800행 영상에서 잘라 낸 ROI의 결과 + roi_y0 = 전체 영상 결과 (차 < 1e-4 px)."""
    y0, h = 272, 256
    vt_full = make_vtrue(1280, 800, amp=40.0) - 400 + y0 + h / 2
    full, _, _ = synth(sc, v_true=vt_full, rng=11, h=800)
    roi = full[y0:y0 + h]
    bit = SCENARIOS[sc]["bit"]
    vf, ff = extract_centers(full, method, bit_depth=bit)
    vr, fr = extract_centers(roi, method, bit_depth=bit)
    both = np.isfinite(vf) & np.isfinite(vr)
    assert both.mean() > 0.99
    assert np.array_equal(np.isfinite(vf), np.isfinite(vr))
    assert np.abs(roi_to_full(vr, y0)[both] - vf[both]).max() < 1e-4


def test_10bit_in_16bit_container_low_aligned():
    """10비트 값은 16비트 그릇 아래 비트 (0–1023). 8비트 그릇에 10비트라고 하면 오류."""
    img, vt, _ = synth("nominal_10bit")
    assert img.dtype == np.uint16 and img.max() <= 1023
    v, _ = extract_centers(img, "cog", bit_depth=10)
    assert np.nanmax(np.abs(v - vt)) < 0.5
    with pytest.raises(ValueError):
        extract_centers(np.clip(img, 0, 255).astype(np.uint8), "cog", bit_depth=10)


def test_bit_depth_inference_and_validation():
    img8, _, _ = synth("saturated_10bit")
    _, fl_given = extract_centers(img8, "cog", bit_depth=10)
    _, fl_inf = extract_centers(img8, "cog")          # uint16, 최댓값 1023 → 10비트로 추정
    assert np.array_equal(fl_given, fl_inf)
    with pytest.raises(ValueError):
        extract_centers(img8, "cog", bit_depth=11)


def test_8bit_saturation_255():
    cfg = dict(SCENARIOS["f1_basic_8bit"], peak=400)
    img, vt, _ = synth(cfg)
    assert img.dtype == np.uint8 and img.max() == 255
    v, fl = extract_centers(img, "cog", bit_depth=8)
    assert ((fl & 8) > 0).mean() > 0.99 and abs(np.nanmean(v - vt)) < 0.05
