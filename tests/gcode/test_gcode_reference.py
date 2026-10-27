"""GC8 비드 모델 · GC9 정답 지도 · GC10 해석해 시험."""
import math

import numpy as np
import pytest

from cvlab.gcode import (GCodeParams, RefStack, bead_area, bead_profile_height, build_reference,
                         effective_width, make_grid, parse_file, parse_text, width_from_area)
from cvlab.gcode.grid import index_of, value_at
from gcode_helpers import P042, PRE, hand


def test_bead_area_value_and_inverse():
    assert bead_area(0.42, 0.2) == pytest.approx(0.0754159, abs=1e-6)
    for w, h in ((0.42, 0.2), (0.45, 0.15), (0.68, 0.35), (0.2, 0.2)):
        assert abs(width_from_area(bead_area(w, h), h) - w) < 1e-9
    with pytest.raises(ValueError):
        bead_area(0.1, 0.2)


def test_effective_width_skips_short_segments():
    t = PRE + "G1 X110 Y100 E0.31354\nG1 X110.3 Y100 E0.01\n"
    w = effective_width(parse_text(t).segments, 1.75, 0.5)
    assert w.notna().sum() == 1
    assert w.dropna().iloc[0] == pytest.approx(0.42, abs=1e-4)


def test_bead_profile_alternative_only():
    z = bead_profile_height([0.0, 0.11, 0.21, 0.3], 0.42, 0.2, 0.4)
    assert z[0] == 0.4 and z[1] == 0.4 and z[2] == pytest.approx(0.3) and np.isnan(z[3])
    with pytest.raises(ValueError):
        GCodeParams(height_model="profile")  # 정답 지도 높이는 flat만


def test_grid_contract():
    g = make_grid(100.013, 110.0, 99.99, 105.0, 0.02, 1.0)
    assert g["frame"] == "G" and g["res_mm"] == 0.02
    assert g["x0_mm"] == pytest.approx(99.0) and g["y0_mm"] == pytest.approx(98.98)
    assert abs(g["x0_mm"] / 0.02 - round(g["x0_mm"] / 0.02)) < 1e-9
    assert g["x0_mm"] + (g["nx"] - 1) * 0.02 >= 111.0 - 1e-9


def test_height_equals_layer_z_exactly():
    r = parse_file(hand("H20"), P042)
    ref = build_reference(r, params=P042)
    for n, z in ((0, 0.2), (1, 0.4)):
        h = ref.height_at_layer(n)
        iy, ix = index_of(ref.grid, 105.0, 105.0)
        assert abs(h[iy, ix] - z) <= 1e-9
        vals = h[np.isfinite(h)]
        assert set(np.unique(vals).tolist()) <= {0.2, 0.4}  # 높이는 층 Z 값 그대로 (flat)


def test_single_segment_footprint_area():
    t = PRE + "G1 X110 Y100 E0.31354\n"
    r = parse_text(t, P042)
    ref = build_reference(r, params=P042)
    w, L = 0.42, 10.0
    area = ref.footprint(0).sum() * ref.grid["res_mm"] ** 2
    expect = L * w + math.pi * (w / 2) ** 2
    assert abs(area - expect) / expect <= 0.01


def test_parallel_fill_no_holes():
    r = parse_file(hand("H20"), P042)
    ref = build_reference(r, params=P042)
    for n in (0, 1):
        h = ref.height_at_layer(n)
        iy0, ix0 = index_of(ref.grid, 100.3, 100.3)
        iy1, ix1 = index_of(ref.grid, 109.7, 109.7)
        assert not np.isnan(h[iy0:iy1 + 1, ix0:ix1 + 1]).any()


def test_deterministic():
    r = parse_file(hand("H20"), P042)
    a, b = build_reference(r, params=P042), build_reference(r, params=P042)
    assert np.array_equal(a.height_at_layer(1), b.height_at_layer(1), equal_nan=True)
    assert np.array_equal(a.top_layer_at(1), b.top_layer_at(1))


def test_lshape_orientation():
    r = parse_file(hand("H21"), P042)
    ref = build_reference(r, params=P042)
    fp = ref.footprint(0)
    on = lambda x, y: bool(value_at(ref.grid, fp, x, y, False))
    assert on(109, 100) and on(100, 104.5)
    assert not on(100, 109) and not on(109, 105) and not on(104.5, 100.5)
    # A[iy, ix]: 긴 다리 (X 방향 10 mm)는 열 방향으로 길다
    rows, cols = np.nonzero(fp)
    assert (cols.max() - cols.min()) > (rows.max() - rows.min())


def test_top_layer_and_heights_layered():
    t = (PRE + "G1 X110 Y100 E0.31354\nG1 Z0.4\nG1 X100 Y100\nG1 X105 Y100 E0.15677\n")
    ref = build_reference(parse_text(t, P042), params=P042)
    top = ref.top_layer_at(1)
    assert top[index_of(ref.grid, 102, 100)] == 1 and top[index_of(ref.grid, 108, 100)] == 0
    assert value_at(ref.grid, top, 105, 103, -1) == -1
    h0 = ref.height_at_layer(0)
    assert h0[index_of(ref.grid, 102, 100)] == pytest.approx(0.2)


def test_type_priority_wall_over_fill():
    t = PRE + ";TYPE:Outer wall\nG1 X110 Y100 E0.31354\n;TYPE:Sparse infill\nG1 X100 Y100 E0.31354\n"
    ref = build_reference(parse_text(t, P042), params=P042)
    tc = ref.type_at(0)[index_of(ref.grid, 105, 100)]
    assert ref.type_names[tc] == "WALL-OUTER"


def test_save_load_roundtrip(tmp_path):
    r = parse_file(hand("H20"), P042)
    ref = build_reference(r, params=P042)
    p = tmp_path / "ref.npz"
    ref.save(p)
    back = RefStack.load(p)
    assert back.grid == ref.grid and np.array_equal(back.z_layers, ref.z_layers)
    for n in range(ref.n_layers):
        assert np.array_equal(back.footprint(n), ref.footprint(n))
        assert np.array_equal(back.height_at_layer(n), ref.height_at_layer(n), equal_nan=True)
        assert np.array_equal(back.type_at(n), ref.type_at(n))


def test_prime_not_in_map_and_center_origin():
    ref = build_reference(parse_file(hand("H23"), P042), params=P042)
    assert ref.grid["x0_mm"] >= 93.98  # 퍼지선 x 0.1은 빠짐
    ref2 = build_reference(parse_file(hand("H24"), P042), params=P042)
    assert ref2.grid["x0_mm"] == pytest.approx(-6.0)
    assert ref2.footprint(1)[index_of(ref2.grid, -5, 0)]


def test_extrusion_width_model():
    from cvlab.gcode.reference import segment_widths
    p = GCodeParams(width_model="extrusion")
    r = parse_file(hand("H20"), p)
    w = segment_widths(r, p)
    assert np.all(np.abs(w - 0.42) <= 1e-4)  # E 반올림 5자리 → w_eff 0.419995
    # w가 0.42보다 아주 조금 작으면 선 사이 가운데 줄 (거리 정확히 0.21) 칸이 빔: 문서 §9 한계
    ref_n = build_reference(r, params=GCodeParams())
    ref_e = build_reference(r)
    assert ref_e.footprint(0).sum() <= ref_n.footprint(0).sum()


# ---------------------------------------------------------------- G-2 빠른 판 = 1차 판 (비트 단위)
from cvlab.gcode.reference import capsule_cells, capsule_window  # noqa: E402


def _window_cells(grid, *a):
    w = capsule_window(grid, *a)
    if w is None:
        return None
    sy, sx, m = w
    iy, ix = np.nonzero(m)
    return iy + sy.start, ix + sx.start


def test_band_equals_window_random_segments():
    """옛 함수 capsule_window와 새 함수 capsule_cells가 같은 칸을 고름 (각도·길이·끝 걸침·점 선분)."""
    rng = np.random.default_rng(20261027)
    grid = make_grid(0.0, 30.0, 0.0, 20.0, 0.02, 1.0)
    cases = [(5.0, 5.0, 5.0, 5.0, 0.21), (0.0, 0.0, 30.0, 20.0, 0.21), (10.0, 3.0, 10.0, 18.0, 0.225),
             (2.0, 7.0, 28.0, 7.0, 0.2), (-3.0, -3.0, 2.0, 1.0, 0.3), (40.0, 40.0, 45.0, 41.0, 0.2),
             (10.0, 10.0, 10.000000000001, 15.0, 0.21), (3.0, 4.0, 23.0, 4.0000000001, 0.21)]
    for _ in range(300):
        x0, y0 = rng.uniform(-2, 32), rng.uniform(-2, 22)
        L, a = rng.choice([0.05, 0.5, 3.0, 25.0]), rng.uniform(0, 2 * math.pi)
        cases.append((x0, y0, x0 + L * math.cos(a), y0 + L * math.sin(a), rng.uniform(0.1, 0.4)))
    for c in cases:
        old, new = _window_cells(grid, *c), capsule_cells(grid, *c)
        if old is None:
            assert new is None, c
            continue
        a = np.zeros((grid["ny"], grid["nx"]), bool); a[old] = True
        b = np.zeros_like(a); b[new] = True
        assert np.array_equal(a, b), c


@pytest.mark.parametrize("key", ["H20", "H21", "H23", "H24", "H05"])
def test_band_equals_window_build_reference(key):
    """같은 입력으로 1차 판 (window)과 빠른 판 (band) 정답 지도가 모든 층에서 같음."""
    r = parse_file(hand(key), P042)
    a, b = build_reference(r, params=P042, method="window"), build_reference(r, params=P042, method="band")
    assert a.grid == b.grid and np.array_equal(a.z_layers, b.z_layers) and a.type_names == b.type_names
    for n in range(a.n_layers):
        assert np.array_equal(a.footprint(n), b.footprint(n))
        assert np.array_equal(a.type_at(n), b.type_at(n))
    with pytest.raises(ValueError):
        build_reference(r, params=P042, method="fast")
