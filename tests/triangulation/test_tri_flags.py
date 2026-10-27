"""T7a 포화 · 다중 피크 · 선 없음 · 품질 지표 · 표시 비트 시험 (LX4 – LX7)."""
import numpy as np
import pytest

from cvlab.triangulation import FLAG, TriParams, extract_centers, line_quality
from tri_synth import SCENARIOS, make_vtrue, synth


def _bit(fl, name):
    return (fl & FLAG[name]) > 0


def test_flag_values_fixed():
    assert FLAG == {"no_line": 1, "low_peak": 2, "wide": 4, "saturated": 8, "multi_peak": 16, "edge_window": 32}


def test_saturated_bias_and_bit():
    """LX4: 피크 1600 → 1023 잘림. cog |bias| < 0.05 px, 포화 화소 있는 열 100 % saturated."""
    img, vt, lc = synth("saturated_10bit")
    v, fl = extract_centers(img, "cog", bit_depth=10)
    assert abs(np.nanmean(v - vt)) < 0.05
    has_sat = (img >= 1023).any(axis=0)
    assert has_sat.mean() > 0.99
    assert _bit(fl, "saturated")[has_sat].all()


def test_gauss3_excludes_saturated_pixels():
    """3점 방법은 포화에서 −0.47 px (F1 §6.2). gauss3는 포화 화소를 빼고 맞추므로 작아야 함."""
    img, vt, lc = synth("saturated_10bit")
    v3, _ = extract_centers(img, "gauss3", bit_depth=10)
    vp, _ = extract_centers(img, "parabola3", bit_depth=10)
    assert abs(np.nanmean(vp - vt)) > 0.2
    assert abs(np.nanmean(v3 - vt)) < 0.05


def test_saturation_value_follows_bit_depth():
    """포화값 = 2^bit_depth − 1 (그릇 최댓값이 아님). 1023 화소는 12비트로 보면 포화가 아님."""
    img, vt, lc = synth("saturated_10bit")
    _, f10 = extract_centers(img, "cog", bit_depth=10)
    _, f12 = extract_centers(img, "cog", bit_depth=12)
    assert _bit(f10, "saturated").mean() > 0.99 and not _bit(f12, "saturated").any()


def test_reflection_guided_p95_and_multi_bit():
    """LX5: 21열 가짜 피크 (1.5배, +12 px). 안내 켬 P95 < 0.3 px, 그 열 multi_peak ≥ 95 %. 끄면 틀림."""
    img, vt, lc = synth("reflection_10bit")
    u0, u1 = SCENARIOS["reflection_10bit"]["reflection"][:2]
    v, fl = extract_centers(img, "cog", bit_depth=10)
    e = np.abs(v - vt)[u0:u1]
    assert np.percentile(e, 95) < 0.3
    assert _bit(fl, "multi_peak")[u0:u1].mean() >= 0.95
    v0, fl0 = extract_centers(img, "cog", params=TriParams(guide_band_px=None), bit_depth=10)
    assert np.percentile(np.abs(v0 - vt)[u0:u1], 95) > 5
    assert _bit(fl0, "multi_peak")[u0:u1].mean() >= 0.95


@pytest.mark.parametrize("name", [n for n in SCENARIOS if n.startswith("refl_u")])
def test_reflection_sites_on_sloped_line(name):
    """T-1: 반사 자리 5곳 × ±12 px (선 기울기 −0.19 – +0.17 px/열). 3장 모아 21열 P95 < 0.2 px,
    multi_peak ≥ 95 %. 고치기 전에는 u 100 · 600 · 1100에서 가짜 피크로 감 (P95 ≈ 12 px, 팀장검증 5차 §4.4)."""
    u0, u1 = SCENARIOS[name]["reflection"][:2]
    errs, mp = [], []
    for k in range(3):
        img, vt, _ = synth(name, rng=300 + k)
        v, fl = extract_centers(img, "cog", bit_depth=10)
        errs.append(np.abs(v - vt)[u0:u1])
        mp.append(_bit(fl, "multi_peak")[u0:u1])
    assert np.percentile(np.concatenate(errs), 95) < 0.2
    assert np.concatenate(mp).mean() >= 0.95


def test_guide_keeps_step_columns_without_reflection():
    """T-1 회귀: 반사 없는 기본 8비트 영상 10장 (bench 씨앗)에서 25 px 단차 열 (u 499 · 500)도 값이 맞아야 함.
    봉우리 문턱을 전체 문턱으로만 두면 외톨이 잡음 화소로 단차 열이 안내선에서 빠지고, 메운 중간값이
    중앙값을 뒤집어 1열이 NaN · 1열이 4.5 px 틀렸음 (씨앗 SEED + 4 · SEED + 5)."""
    from tri_synth import SEED

    for k in range(10):
        img, vt, _ = synth("f1_basic_8bit", rng=SEED + k)
        v, _ = extract_centers(img, "cog", bit_depth=8)
        assert np.isfinite(v).all() and np.abs(v - vt).max() < 1.0


def test_reflection_on_steep_line():
    """T-1: 기울기 0.3 px/열 직선 + 21열 반사 (−12 px, 1.6배). 안내선이 반사 쪽으로 끌리지 않아야 함."""
    vt = 128 + 0.3 * (np.arange(1280) - 640)
    vt = np.clip(vt, 30, 226)
    cfg = dict(SCENARIOS["nominal_10bit"], reflection=(400, 421, -12.0, 1.6))
    img, _, _ = synth(cfg, v_true=vt, rng=9)
    v, fl = extract_centers(img, "cog", bit_depth=10)
    assert np.percentile(np.abs(v - vt)[400:421], 95) < 0.2
    assert _bit(fl, "multi_peak")[400:421].mean() >= 0.95


def test_no_line_zero_fake_and_bit():
    """LX6: 레이저 없는 200열에서 값 0개, no_line 100 %."""
    img, vt, lc = synth("no_line_10bit")
    assert (~lc).sum() == 200
    for m in ("max", "cog", "gauss3", "steger"):
        v, fl = extract_centers(img, m, bit_depth=10)
        assert np.isfinite(v[~lc]).sum() == 0
        assert _bit(fl, "no_line")[~lc].all()
        assert np.isfinite(v[lc]).mean() == 1.0


def test_weak_signal_below_threshold_is_nan():
    """문턱 아래 약한 신호 (피크 = 배경 + 약 1σ)도 NaN + no_line."""
    cfg = dict(SCENARIOS["nominal_10bit"], peak=14)
    img, vt, lc = synth(cfg, rng=5)
    v, fl = extract_centers(img, "cog", bit_depth=10)
    assert np.isfinite(v).sum() == 0 and _bit(fl, "no_line").all()


def test_low_peak_bit():
    img, vt, lc = synth("low_10bit")
    _, fl = extract_centers(img, "cog", bit_depth=10)
    assert _bit(fl, "low_peak").mean() > 0.95
    img2, _, _ = synth("nominal_10bit")
    _, fl2 = extract_centers(img2, "cog", bit_depth=10)
    assert _bit(fl2, "low_peak").mean() < 0.01


def test_wide_bit():
    """일부 열 (u 100–159)만 선 두께 σ 4 px → 정상 폭 (σ 1.5)의 2배 넘음 → wide."""
    vt = make_vtrue()
    a, _, _ = synth("nominal_10bit", v_true=vt, rng=3)
    b, _, _ = synth(dict(SCENARIOS["nominal_10bit"], sigma=4.0), v_true=vt, rng=4)
    img = a.copy()
    img[:, 100:160] = b[:, 100:160]
    _, fl = extract_centers(img, "cog", bit_depth=10)
    assert _bit(fl, "wide")[100:160].mean() > 0.95
    assert _bit(fl, "wide")[400:1200].mean() < 0.01


def test_edge_window_bit():
    """선이 ROI 위 끝 (v ≈ 1.5)에 걸리면 창이 잘림 → edge_window."""
    vt = np.full(200, 1.5)
    img, _, _ = synth(dict(SCENARIOS["nominal_10bit"]), v_true=vt, rng=6, h=64)
    _, fl = extract_centers(img, "cog", bit_depth=10)
    assert _bit(fl, "edge_window").all()
    vt2 = np.full(200, 32.0)
    img2, _, _ = synth(dict(SCENARIOS["nominal_10bit"]), v_true=vt2, rng=6, h=64)
    _, fl2 = extract_centers(img2, "cog", bit_depth=10)
    assert not _bit(fl2, "edge_window").any()


def test_flags_mark_but_keep_values():
    """값은 지우지 않고 표시만 (F1 §4): 포화 · 반사 열도 v는 유한."""
    img, vt, lc = synth("saturated_10bit")
    v, fl = extract_centers(img, "cog", bit_depth=10)
    assert np.isfinite(v[_bit(fl, "saturated")]).all()


def test_line_quality_keys_and_values():
    """LX7: 지표 5종. 기본 영상에서 FWHM ≈ 2.355 σ, 피크 ≈ 720 + 배경, 봉우리 1개, 포화 0."""
    img, vt, lc = synth("nominal_10bit")
    v, _ = extract_centers(img, "cog", bit_depth=10)
    q = line_quality(img, v, 10)
    assert set(q) == {"peak_dn", "fwhm_px", "n_sat", "n_peaks", "snr"}
    for k in q:
        assert q[k].shape == (img.shape[1],)
    assert 3.3 < np.median(q["fwhm_px"]) < 4.0
    assert 650 < np.median(q["peak_dn"]) < 800
    assert np.median(q["n_peaks"]) == 1 and q["n_sat"].sum() == 0
    assert np.median(q["snr"]) > 20


def test_line_quality_saturation_and_peaks():
    img, vt, _ = synth("saturated_10bit")
    v, _ = extract_centers(img, "cog", bit_depth=10)
    q = line_quality(img, v, 10)
    assert (q["n_sat"] >= 1).mean() > 0.99 and q["peak_dn"].max() == 1023
    img2, vt2, _ = synth("reflection_10bit")
    v2, _ = extract_centers(img2, "cog", bit_depth=10)
    q2 = line_quality(img2, v2, 10)
    assert (q2["n_peaks"][900:921] >= 2).all()
