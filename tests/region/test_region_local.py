"""D-19 두 파일 (data/gcode_samples/_local/, Git 밖). 없으면 이 시험들만 skip.

caliper 기대값은 T4a GC12 (docs/G코드-해석.md §6): 심도 밖 층 41, 마지막 층 물체 넓이의 62 %.
"""
import csv
import hashlib
import os

import pytest

from region_helpers import CALIPER, ROOT, VORON, built_local

pytestmark = pytest.mark.skipif(not (os.path.exists(CALIPER) and os.path.exists(VORON)),
                                reason="_local/ D-19 파일 없음 (MANIFEST 지문·출처로 받아야 함)")


def _depth(rs):
    st = rs.layer_stats()
    layers = [s["layer_idx"] for s in st if s["n_depth_object"] > 0]
    last = st[-1]
    return layers, 100.0 * last["n_depth_object"] / last["n_object"]


def test_region_local_manifest_sha():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "gcode_samples", "MANIFEST.csv"), encoding="utf-8")))
    for path in (VORON, CALIPER):
        row = next(r for r in rows if r["파일"] == os.path.basename(path))
        assert hashlib.sha256(open(path, "rb").read()).hexdigest() == row["sha256"]


def test_region_caliper_depth_41_layers_62_pct():
    r, g, ref, rs = built_local(CALIPER)
    layers, pct = _depth(rs)
    assert len(layers) == 41 and layers[0] == 23
    assert abs(pct - 62.0) <= 1.0
    assert rs.info["band_mm"] == pytest.approx(0.38) and rs.info["step_mm"] == pytest.approx(0.1)


def test_region_caliper_coverage_and_skirt_type():
    r, g, ref, rs = built_local(CALIPER)
    assert rs.info["coverage_final_top_pct"] == pytest.approx(100.0)
    assert "SKIRT" in ref.type_names and rs.summary().bit_type.iloc[-1] > 0
    # 스커트를 뺀 격자는 T4a 기본 격자 (2790 × 1735)보다 작음
    assert g["ny"] * g["nx"] < 2790 * 1735
    assert rs.info["build_s"] <= 120.0


def test_region_voron_no_depth_and_speed():
    r, g, ref, rs = built_local(VORON)
    layers, pct = _depth(rs)
    assert layers == [] and pct == 0.0
    assert rs.info["coverage_final_top_pct"] == pytest.approx(100.0)
    assert rs.info["build_s"] <= 30.0
    assert rs.info["passes_xy"] == [2, 1]
