"""GC4 층 정하기 · GC5 층 표."""
import pytest

from cvlab.gcode import GCodeError, GCodeParams, parse_file, parse_text
from cvlab.gcode.layers import LAYER_COLUMNS
from gcode_helpers import P042, PRE, hand

SQ = "G1 X110 Y100 E0.3\nG1 X110 Y110 E0.3\nG1 X100 Y110 E0.3\nG1 X100 Y100 E0.3\n"


def test_layer_table_columns_and_order():
    r = parse_file(hand("H12"), P042)
    assert list(r.layers.columns) == LAYER_COLUMNS
    L = r.layers
    assert (L.gcode_line_start.iloc[1:].to_numpy() > L.gcode_line_end.iloc[:-1].to_numpy()).all()
    assert L.layer_idx.tolist() == list(range(len(L)))


def test_zhop_does_not_add_layer():
    r = parse_file(hand("H10"), P042)
    assert r.layers.layer_z_mm.tolist() == pytest.approx([0.2, 0.4])


def test_variable_layer_heights():
    r = parse_file(hand("H11"), P042)
    assert r.layers.layer_h_mm.tolist() == pytest.approx([0.2, 0.15, 0.1], abs=1e-9)


def test_comment_and_z_must_agree():
    t = PRE.replace("G1 Z0.2 F600\n", "") + ";LAYER_CHANGE\n;Z:0.2\nG1 Z0.2\n" + SQ + "G1 Z0.4\n" + SQ
    with pytest.raises(GCodeError, match="층 수 불일치|둘 이상"):
        parse_text(t)


def test_comment_z_value_mismatch_error():
    t = "G21\nG90\nM83\nG28\n;LAYER_CHANGE\n;Z:0.25\nG1 Z0.2\nG1 X100 Y100\n" + SQ
    with pytest.raises(GCodeError, match="주석 Z"):
        parse_text(t)


def test_layer_source_z_skips_comment_check():
    t = "G21\nG90\nM83\nG28\n;LAYER_CHANGE\n;Z:0.25\nG1 Z0.2\nG1 X100 Y100\n" + SQ
    r = parse_text(t, GCodeParams(layer_source="z"))
    assert len(r.layers) == 1 and any("layer_source=z" in w for w in r.warnings)


def test_sequential_print_error():
    with pytest.raises(GCodeError, match="내려감"):
        parse_file(hand("H17"), P042)


def test_helix_error():
    with pytest.raises(GCodeError, match="나선"):
        parse_file(hand("H18"), P042)


def test_double_markers_counted_once():
    r = parse_file(hand("H22"), P042)
    assert len(r.layers) == 2 and r.header["layers_declared"] == 2
    assert any("압출 없는 층 표시 2개" in w for w in r.warnings)


def test_purge_before_first_marker_is_prime():
    r = parse_file(hand("H23"), P042)
    s = r.segments
    assert (s.type == "PRIME").sum() == 2 and (s[s.type == "PRIME"].layer_idx == -1).all()
    assert r.layers.layer_z_mm.tolist() == pytest.approx([0.28, 0.56])


def test_helix_zhop_travel_not_layer():
    r = parse_file(hand("H24"), P042)
    s = r.segments
    assert len(r.layers) == 2 and ((s.kind == "travel") & s.arc).any()
    assert s[s.arc].z1_mm.max() == pytest.approx(0.6)


def test_line_ranges_no_comment_rule():
    r = parse_file(hand("H10"), P042)
    # 줄 1 주석, 6 G1 Z0.2, 8–11 층0 압출, 12 hop, 15–18 층1 압출
    assert r.layers.gcode_line_start.tolist() == [6, 12]
    assert r.layers.gcode_line_end.tolist() == [11, 18]


def test_non_extrude_rows_get_layer_by_range():
    r = parse_file(hand("H07"), P042)
    s = r.segments
    assert (s[s.kind.isin(["retract", "unretract"])].layer_idx == 0).all()
    assert s[s.kind == "wipe"].layer_idx.iloc[0] == -1  # 마지막 압출 줄 뒤
