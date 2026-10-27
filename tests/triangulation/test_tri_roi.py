"""T7a ROI · 비트 깊이 시험 (LX9, T-3)."""
import numpy as np
import pytest

from cvlab.triangulation import METHODS, extract_centers, line_quality, roi_to_full
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


def test_bit_depth_required_for_uint16_and_validation():
    """T-3: uint16 영상에서 bit_depth를 빠뜨리면 ValueError (extract_centers · line_quality 모두).
    uint8 (→ 8) · 실수 (포화 없음)는 None을 받음. 허용 밖 값 (11)은 오류."""
    img16, _, _ = synth("saturated_10bit")
    assert img16.dtype == np.uint16
    with pytest.raises(ValueError, match="bit_depth"):
        extract_centers(img16, "cog")
    v, _ = extract_centers(img16, "cog", bit_depth=10)
    with pytest.raises(ValueError, match="bit_depth"):
        line_quality(img16, v, None)
    with pytest.raises(ValueError):
        extract_centers(img16, "cog", bit_depth=11)
    img8, _, _ = synth(dict(SCENARIOS["f1_basic_8bit"], peak=400))
    assert img8.dtype == np.uint8
    v8a, f8a = extract_centers(img8, "cog")
    v8b, f8b = extract_centers(img8, "cog", bit_depth=8)
    assert np.array_equal(f8a, f8b) and np.array_equal(v8a, v8b, equal_nan=True)
    assert line_quality(img8, v8a, None)["n_sat"].sum() > 0


def test_8bit_png_via_load_frame_needs_bit_depth(tmp_path):
    """T-3: 8비트 PNG를 load_frame으로 읽으면 uint16. bit_depth=8을 넘기면 255 포화가 saturated로 켜지고,
    빠뜨리면 (예전처럼 10비트로 짐작해 포화를 놓치는 대신) ValueError."""
    from PIL import Image

    from cvlab.triangulation import load_frame

    vt = make_vtrue(200, 64, step=None, amp=6.0)
    img8, _, _ = synth(dict(SCENARIOS["f1_basic_8bit"], peak=400), v_true=vt, rng=21, h=64)
    assert img8.dtype == np.uint8 and img8.max() == 255
    (tmp_path / "frames").mkdir()
    Image.fromarray(img8).save(tmp_path / "frames" / "000000.png")
    f = load_frame(tmp_path, {"file": "frames/000000.png", "roi_h_px": 64, "roi_w_px": 200})
    assert f.dtype == np.uint16 and np.array_equal(f, img8)
    v, fl = extract_centers(f, "cog", bit_depth=8)
    assert ((fl & 8) > 0).mean() > 0.99 and abs(np.nanmean(v - vt)) < 0.05
    with pytest.raises(ValueError, match="bit_depth"):
        extract_centers(f, "cog")


def test_8bit_saturation_255():
    cfg = dict(SCENARIOS["f1_basic_8bit"], peak=400)
    img, vt, _ = synth(cfg)
    assert img.dtype == np.uint8 and img.max() == 255
    v, fl = extract_centers(img, "cog", bit_depth=8)
    assert ((fl & 8) > 0).mean() > 0.99 and abs(np.nanmean(v - vt)) < 0.05
