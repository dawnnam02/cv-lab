"""RG2 엣지 띠 · RG3 가림 · RG4 심도 (층 하나 마스크 함수)."""
import math

import numpy as np
import pytest

from cvlab.region import REASON_BITS, RegionParams, build_region, depth_out, edge_band, predict_occlusion
from cvlab.region.masks import edge_band_update, grow, height_boundary
from region_helpers import aligned_ref, built_hand, built_tower, parse_lines, block


def _col(g, x):
    return int(round((x - g["x0_mm"]) / g["res_mm"]))


def _ys(g):
    return g["y0_mm"] + np.arange(g["ny"]) * g["res_mm"]


def test_region_edge_band_h20_middle_row():
    """H20 가운데 줄 (y = 105) 한쪽 띠 칸 = 0.25 ÷ 0.02 + 1 = 13.5 ± 1."""
    r, g, ref, rs = built_hand("H20_block.gcode")
    assert rs.info["band_mm"] == pytest.approx(0.25) and rs.info["step_mm"] == pytest.approx(0.1)
    n = rs.n_layers - 1
    fp = ~np.isnan(ref.height_at_layer(n))
    iy = int(round((105.0 - g["y0_mm"]) / g["res_mm"]))
    one_side = (fp[iy].sum() - rs.region(n)[iy].sum()) / 2
    assert 12.5 <= one_side <= 14.5


def test_region_edge_band_internal_step_and_threshold():
    h = np.full((60, 200), 0.2)
    h[:, 100:] = 0.4                      # 0.2 mm 단차 (x 칸 100)
    eb = edge_band(h, 0.02, 0.25, 0.1)
    row = eb[30]
    assert row[100 - 13:100 + 13].all() and not row[:100 - 14].any() and not row[100 + 14:].any()
    # 단차가 step 이하이면 경계가 아님 (같으면 경계 아님: > 비교)
    h2 = np.full((60, 200), 0.2)
    h2[:, 100:] = 0.3
    assert not edge_band(h2, 0.02, 0.25, 0.1).any()
    assert not edge_band(np.full((10, 10), np.nan), 0.02, 0.25, 0.1).any()


def test_region_edge_band_nan_is_bed():
    h = np.full((40, 40), np.nan)
    h[10:30, 10:30] = 0.2
    b = height_boundary(h, 0.1)
    assert b[20, 9] and b[20, 10] and not b[20, 20]


def test_region_edge_band_update_equals_full():
    """층마다 바뀐 칸 근처만 다시 계산한 띠 = 전체 계산 (H21 · 합성 탑)."""
    for r, g, ref in [built_hand("H21_lshape.gcode")[:3], built_tower(12)[:3]]:
        prev = None
        top = np.full((g["ny"], g["nx"]), -1)
        for n in range(ref.n_layers):
            fp = ref.footprint(n)
            h = ref.height_at_layer(n)
            prev = edge_band_update(h, prev, fp, g["res_mm"], 0.25, 0.1)
            assert np.array_equal(prev, edge_band(h, g["res_mm"], 0.25, 0.1)), n


def test_region_occlusion_shadow_length_tower():
    """탑 (Z 2.0) 뒤 바닥 (Z 0.2): 그림자 = 1.8 × tan 30° = 1.039 mm (± 1칸). 탑 끝 y = 4.8 (생성기 선 간격)."""
    r, g, ref, _ = built_tower(10)
    h = ref.height_at_layer(9)
    ix = _col(g, 5.0)
    ys = _ys(g)
    top_edge = ys[h[:, ix] == 2.0].max()
    occ = predict_occlusion(h, g["res_mm"], 30.0, "-y")
    col = occ[:, ix] & (ys > top_edge) & (ys < 9.0)
    assert col.sum() * g["res_mm"] == pytest.approx(1.8 * math.tan(math.radians(30)), abs=0.02 + 1e-9)
    assert ys[col].min() == pytest.approx(top_edge + g["res_mm"])


def test_region_occlusion_sides_and_theta():
    h = np.zeros((300, 5))
    h[100:150] = 2.0
    ym = predict_occlusion(h, 0.02, 30.0, "-y")[:, 2]
    yp = predict_occlusion(h, 0.02, 30.0, "+y")[:, 2]
    both = predict_occlusion(h, 0.02, 30.0, "both")[:, 2]
    assert ym[150:].sum() == math.floor(2.0 * math.tan(math.radians(30)) / 0.02 - 1e-9) and not ym[:100].any()
    assert yp[:100].sum() == ym[150:].sum() and not yp[150:].any()
    assert np.array_equal(both, ym | yp)
    y45 = predict_occlusion(h, 0.02, 45.0, "-y")[:, 2]
    assert y45[150:].sum() == 99  # s < h·tan45 = 2.0 mm → 99칸 (2.00은 같아서 안 막힘)
    assert not predict_occlusion(np.full((50, 50), 0.4), 0.02, 30, "both").any()


def test_region_occlusion_grow_two_cells():
    m = np.zeros((20, 20), bool)
    m[10, 10] = True
    g2 = grow(m, 2)
    assert g2.sum() == 25 and g2[8, 8] and g2[12, 12] and not g2[7, 10]
    r, g, ref, rs = built_tower(10, "-y")
    h = ref.height_at_layer(9)
    ix = _col(g, 5.0)
    ys = _ys(g)
    raw = predict_occlusion(h, g["res_mm"], 30.0, "-y")[:, ix]
    bits = (rs.reasons(9)[:, ix] & REASON_BITS["occlusion"]) > 0
    floor = (ys > 4.8) & (ys < 9.0)  # 바닥 끝 (y 10)의 베드 그림자는 뺌
    assert bits[floor].sum() == raw[floor].sum() + 2


def test_region_depth_out_window():
    h = np.array([[np.nan, 0.2, 2.0, 2.000001, 10.0, 10.000001]])
    d = depth_out(h, 10.0, 8.0, 0.0)
    assert d.tolist() == [[False, True, False, False, False, True]]  # 창 [2.0, 10.0], 아래 끝 포함
    d2 = depth_out(h, 10.0, 8.0, -1.0)  # 창 [1.0, 9.0]: 10.0 윗면도 벗어남
    assert d2.tolist() == [[False, True, False, False, True, True]]


def test_region_depth_tower_9_layers_half():
    """합성 탑 Z 10.0 (50층): 심도 밖 층 = Z 8.4 – 10.0 = 9층, 마지막 층 약 50 % (바닥 y 5–10 노출)."""
    r, g, ref, rs = built_tower(50, x1=2.0)
    layers = [k for k in range(rs.n_layers) if ((rs.reasons(k) & REASON_BITS["depth"]) > 0).any()]
    assert len(layers) == 9 and rs.z_layers[layers[0]] == pytest.approx(8.4)
    s = rs.summary()
    last = s[s.layer_idx == rs.n_layers - 1].iloc[0]
    assert 45.0 <= last.bit_depth / last.n_material * 100 <= 55.0


def test_region_depth_fast_path_equals_depth_out():
    r, g, ref, rs = built_tower(50, x1=2.0)
    for n in (40, 41, 45, 49):
        h = ref.height_at_layer(n)
        d = depth_out(h, rs.z_layers[n], 8.0, 0.0)
        assert np.array_equal(d, (rs.reasons(n) & REASON_BITS["depth"]) > 0)


def test_region_depth_top_sensitivity():
    """창 [z + top − 8, z + top]. top −1: 지금 윗면이 창 위로 벗어나 모든 층. +1: 창 아래 끝이 z − 7로 올라 Z ≥ 7.4 (14층)."""
    out = {}
    r, g, ref, _ = built_tower(50, x1=2.0)
    for top in (-1.0, 0.0, 1.0):
        rs = build_region(r, ref, RegionParams(dof_top_mm=top))
        out[top] = sum(int(((rs.reasons(k) & REASON_BITS["depth"]) > 0).any()) for k in range(rs.n_layers))
    assert out[-1.0] == 50 and out[0.0] == 9 and out[1.0] == 14
