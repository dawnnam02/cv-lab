# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""참 형상 (S2): 시나리오 식 · Z축 · 열 · 바탕 꼴 · 참 판정."""
from __future__ import annotations

import math

import numpy as np
import pytest

from cvlab.sim.seeds import SeedTree
from cvlab.sim.shape import (Thermal, ZAxis, gauge_height, gauge_temperature, simulate_specimen,
                             stadium_offset)
from sim_helpers import plate_specimen


def _maps(spec, cfg, pep, **kw):
    got = {}
    res = simulate_specimen(spec, cfg, [pep], on_heightmap=lambda s, k, H: got.__setitem__(k, H), **kw)[0]
    return res, got


@pytest.fixture(scope="module")
def plate():
    return plate_specimen(3)


def test_nominal_reference_equals_gcode(plate):
    cfg, spec = plate
    res, m = _maps(spec, cfg, {"scenario": "NOM-P00"})
    for n in range(3):
        fp = spec.ref.top_layer_at(n) >= 0
        assert np.allclose(m[n][fp], spec.z_layers[n], atol=1e-6)
        assert np.all(m[n][~fp] == 0.0)
    assert res["judgement"] == "pass" and res["pass_pct"] == 100.0
    assert res["thermal_params"] == {} and res["z_axis_error_params"]["gain_ppm"] == 0.0


def test_z_offset_and_judgement_edges(plate):
    cfg, spec = plate
    fp = spec.ref.top_layer_at(2) >= 0
    for dz, want in ((190, "pass"), (210, "fail")):
        res, m = _maps(spec, cfg, {"scenario": "X", "z_offset": {"dz_um": dz}})
        assert np.allclose(m[2][fp] - spec.z_layers[2], dz / 1000.0, atol=1e-6)
        assert res["judgement"] == want


def test_z_scale_moves_heights(plate):
    cfg, spec = plate
    res, m = _maps(spec, cfg, {"scenario": "X", "z_scale": {"gain_ppm": 10000}})
    fp = spec.ref.top_layer_at(2) >= 0
    assert np.allclose(m[2][fp], spec.z_layers[2] * 1.01, atol=1e-6)
    assert res["z_axis_error_params"]["scenario_gain_ppm"] == 10000


def test_warp_center_and_corner(plate):
    cfg, spec = plate
    _, m = _maps(spec, cfg, {"scenario": "X", "warp": {"lift_um": 400}})
    d = m[2] - spec.z_layers[2]
    fp = spec.ref.top_layer_at(2) >= 0
    b = spec.bbox
    iy = int(round(((b["ymin"] + b["ymax"]) / 2 - spec.grid["y0_mm"]) / 0.02))
    ix = int(round(((b["xmin"] + b["xmax"]) / 2 - spec.grid["x0_mm"]) / 0.02))
    assert abs(d[iy, ix]) < 0.002
    assert d[fp].max() <= 0.4 + 1e-9 and d[fp].max() > 0.35


def test_missing_layer_drops_to_layer_below(plate):
    cfg, spec = plate
    pep = {"scenario": "X", "missing_layer": {"layer_rel": 0.5, "n_layers": 1, "radius_mm": 1000.0,
                                              "loc_rel": [0.5, 0.5]}}
    res, m = _maps(spec, cfg, pep)
    fp = spec.ref.top_layer_at(1) >= 0
    assert np.allclose(m[1][fp], spec.z_layers[0], atol=1e-6)   # 층 1이 빠짐 → 층 0 높이
    fp2 = spec.ref.footprint(2)
    assert np.allclose(m[2][fp2], spec.z_layers[2], atol=1e-6)  # 위층이 덮으면 사라짐


def test_unknown_kind_and_base():
    cfg, spec = plate_specimen(1)
    with pytest.raises(ValueError):
        simulate_specimen(spec, cfg, [{"scenario": "X", "bogus": {}}])
    with pytest.raises(ValueError):
        simulate_specimen(spec, cfg, [{"scenario": "X"}], base="flat")
    with pytest.raises(ValueError):
        simulate_specimen(spec, cfg, [{"scenario": "X"}], factors={"nope": True})


def test_thermal_closed_form_matches_numeric():
    cfg, _ = plate_specimen(1)
    th = Thermal(cfg["thermal"], True)
    Z, zn, wait = 12.0, 20.0, 6.0
    z = np.linspace(0, Z, 200001)
    integrand = cfg["thermal"]["t_solid_c"] - th.temp_at(z, zn, wait)
    num = th.alpha * np.trapezoid(integrand, z)
    assert abs(float(th.shrink(np.array([Z]), zn, wait)[0]) - num) < 1e-9


def test_thermal_magnitudes_in_t2_range():
    cfg, _ = plate_specimen(1)
    th = Thermal(cfg["thermal"], True)
    s_in = float(th.shrink(np.array([20.0]), 20.0, cfg["thermal"]["wait_first_pass_s"])[0]) * 1000
    s_post = float(th.post_shrink(np.array([20.0]))[0]) * 1000
    assert 13.6 <= s_in <= 34.0          # T2 MF-THM-05 ① 20 mm에서 14–34 µm
    assert 40.0 <= s_post <= 60.0        # 청사진 §1.2 · MF-THM-05 ② 약 50 µm
    assert s_post > s_in
    assert np.all(Thermal(cfg["thermal"], False).shrink(np.array([20.0]), 20.0, 6.0) == 0)
    assert th.top_temp(1e9) == pytest.approx(cfg["thermal"]["t_low_c"])


def test_thermal_on_in_simulation_lowers_and_post_lower(plate):
    cfg, spec = plate
    res, m = _maps(spec, cfg, {"scenario": "NOM-P00"}, factors={"layer_thermal_field": True})
    fp = spec.ref.top_layer_at(2) >= 0
    assert np.all(m[2][fp] < spec.z_layers[2])
    assert np.all(m["post"][fp] < m[2][fp])
    assert res["post_minus_last_mean_um"] < 0
    assert len(res["thermal_params"]["layer_temp_c"]) == spec.n_layers


def test_gauge_thermal():
    cfg, _ = plate_specimen(1)
    g = cfg["gauge_thermal"]
    assert gauge_temperature(g, 0) == g["t_start_c"]
    assert gauge_temperature(g, 600) < gauge_temperature(g, 3600) < g["t_end_c"]
    assert gauge_height(20.0, 30.0, 11.5) == pytest.approx(20.0 * (1 + 11.5e-6 * 10))


def test_zaxis_seeded_and_off():
    cfg, _ = plate_specimen(1)
    zl = np.array([0.2, 0.4, 0.6])
    off = ZAxis(cfg["z_axis"], zl, [10, 20, 30], 0.0, None, False, False)
    assert np.array_equal(off.layer_actual, zl)
    a = ZAxis(cfg["z_axis"], zl, [10, 20, 30], 0.0, SeedTree(5).child("z").rng(), True, True)
    b = ZAxis(cfg["z_axis"], zl, [10, 20, 30], 0.0, SeedTree(5).child("z").rng(), True, True)
    c = ZAxis(cfg["z_axis"], zl, [10, 20, 30], 0.0, SeedTree(6).child("z").rng(), True, True)
    assert np.array_equal(a.layer_actual, b.layer_actual) and not np.array_equal(a.layer_actual, c.layer_actual)
    assert np.all(np.abs(a.layer_actual - zl) < 0.05)


def test_stadium_profile():
    w, h = np.array([0.45]), np.array([0.2])
    assert stadium_offset(np.array([0.0]), w, h)[0] == 0.0
    assert stadium_offset(np.array([0.225]), w, h)[0] == pytest.approx(-0.1)
    s = 0.45 - 0.2 * (1 - math.pi / 4)  # 이웃 비드 간격 (넓이 맞춤)
    valley = -stadium_offset(np.array([s / 2]), w, h)[0] * 1000
    assert 20 < valley < 60                # 골 깊이 수십 µm (T2 MF-GCD-02 결 ±10–25 µm와 같은 크기)


def test_deposition_base(plate):
    cfg, spec = plate
    fp = spec.ref.top_layer_at(2) >= 0
    _, ref = _maps(spec, cfg, {"scenario": "NOM-P00"})
    _, dep = _maps(spec, cfg, {"scenario": "NOM-P00"}, base="deposition", factors={"bead_texture": True})
    d = dep[2][fp] - ref[2][fp]
    assert d.max() <= 1e-9 and d.mean() < -0.005 and d.min() >= -0.1 - 1e-6
    _, flat = _maps(spec, cfg, {"scenario": "NOM-P00"}, base="deposition", factors={"bead_texture": False})
    assert np.allclose(flat[2], ref[2])
    c2 = dict(cfg); c2["deposition"] = dict(cfg["deposition"], bead_bias_um=30.0)
    _, bias = _maps(spec, c2, {"scenario": "NOM-P00"}, base="deposition",
                    factors={"bead_texture": False, "bead_model_bias": True})
    assert np.allclose(bias[2][fp] - ref[2][fp], 0.03, atol=1e-6)
