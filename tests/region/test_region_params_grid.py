"""RG1 격자 원점 맞춤 · 설정 (RegionParams)."""
from fractions import Fraction

import numpy as np
import pytest
import yaml

from cvlab.gcode import build_reference, parse_file
from cvlab.gcode.grid import cell_centers, value_at
from cvlab.region import RegionParams, aligned_grid, is_aligned, object_bbox
from region_helpers import GCODE_YAML, HAND, REGION_YAML, block, parse_lines


def test_region_params_yaml_equals_defaults():
    assert RegionParams.from_yaml(REGION_YAML).to_dict() == RegionParams().to_dict()


def test_region_params_unknown_key_and_top_key():
    with pytest.raises(ValueError, match="모르는 키"):
        RegionParams.from_dict({"res_mm": 0.02, "dof_mmm": 8})
    with pytest.raises(ValueError, match="최상위 키"):
        import tempfile, os
        p = os.path.join(tempfile.mkdtemp(), "x.yaml")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("masks:\n  res_mm: 0.02\n")
        RegionParams.from_yaml(p)


def test_region_params_validation():
    for bad in ({"camera_side": "-x"}, {"theta_deg": 0}, {"dof_mm": -1}, {"cell_mm": 0.41},
                {"occlusion_grow_cells": 1.5}, {"pass_overlap_mm": 20.0}, {"exclude_types": "SKIRT"}):
        with pytest.raises(ValueError):
            RegionParams.from_dict(bad)


def test_region_res_matches_gcode_yaml():
    g = yaml.safe_load(open(GCODE_YAML, encoding="utf-8"))["gcode"]
    r = yaml.safe_load(open(REGION_YAML, encoding="utf-8"))["region"]
    assert Fraction(str(g["grid_res_mm"])) == Fraction(str(r["res_mm"]))
    assert r["margin_mm"] == g["grid_margin_mm"]


@pytest.mark.parametrize("bbox", [(100.0, 110.08, 100.0, 110.08), (-3.217, 41.9, 0.013, 7.77),
                                  (114.371, 135.629, 83.871, 126.322), (0.0, 0.0, 0.0, 0.0)])
def test_region_aligned_grid_origin_and_size(bbox):
    g = aligned_grid(*bbox)
    for k in ("x0_mm", "y0_mm"):
        assert (Fraction(str(g[k])) / Fraction("0.4")).denominator == 1
    assert g["nx"] % 20 == 0 and g["ny"] % 20 == 0
    assert is_aligned(g)
    xs, ys = cell_centers(g)
    # 경계 상자 + 여유 1 mm를 덮음
    assert xs[0] <= bbox[0] - 1.0 + 1e-9 and xs[-1] >= bbox[1] + 1.0 - 1e-9
    assert ys[0] <= bbox[2] - 1.0 + 1e-9 and ys[-1] >= bbox[3] + 1.0 - 1e-9
    # 원점은 내림이므로 0.4 mm보다 더 멀리 가지 않음
    assert bbox[0] - 1.0 - xs[0] < 0.4 + 1e-9


@pytest.mark.parametrize("name", ["H20_block.gcode", "H21_lshape.gcode"])
def test_region_aligned_grid_same_reference_height(name):
    r = parse_file(f"{HAND}/{name}")
    ref0 = build_reference(r)  # T4a 기본 격자
    g = aligned_grid(*object_bbox(r))
    ref1 = build_reference(r, grid=g)
    n = ref0.n_layers - 1
    h0, h1 = ref0.height_at_layer(n), ref1.height_at_layer(n)
    xs, ys = cell_centers(ref0.grid)
    rng = np.random.default_rng(4)
    for ix, iy in zip(rng.integers(0, len(xs), 400), rng.integers(0, len(ys), 400)):
        a = value_at(ref0.grid, h0, xs[ix], ys[iy])
        b = value_at(g, h1, xs[ix], ys[iy])
        assert (np.isnan(a) and np.isnan(b)) or a == b
    # 넓이도 같음
    assert int((~np.isnan(h0)).sum()) == int((~np.isnan(h1)).sum())


def test_region_object_bbox_excludes_skirt_and_half_width():
    lines = ["G21", "G90", "M83", ";TYPE:Skirt"] + [
        "G0 X-20 Y-20 Z0.2", "G1 X40 Y-20 E1", "G1 X40 Y40 E1"] + block(0, 10, 0, 10, 0.2, type_name="Outer wall")
    r = parse_lines(lines)
    bb = object_bbox(r)
    assert bb == pytest.approx((0.0, 10.0, 0.0, 10.0), abs=1e-9)  # 끝점 0.2–9.8 + 선폭 반 0.2
    bb_all = object_bbox(r, exclude_types=())
    assert bb_all[0] == pytest.approx(-20.2) and bb_all[3] == pytest.approx(40.2)
