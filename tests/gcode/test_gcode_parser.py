"""GC1 파서 기본 · GC2 선분 종류 · GC3 모르는 명령."""
import math

import numpy as np
import pytest

from cvlab.gcode import GCodeError, GCodeParams, parse_text
from cvlab.gcode.parser import SEG_COLUMNS, checksum_ok, command_class, normalize_type
from gcode_helpers import PRE


def kinds(text, **kw):
    return parse_text(text, GCodeParams(**kw)).segments.kind.tolist()


def test_segment_columns_fixed():
    r = parse_text(PRE + "G1 X110 Y100 E0.5\n")
    assert list(r.segments.columns) == SEG_COLUMNS


def test_kinds_six():
    t = PRE + ("G1 X110 Y100 E0.5\nG1 E-0.8\nG1 X110 Y110\nG1 E0.8\n"
               "G1 X100 Y110 E0.5\nG1 X101 Y110 E-0.2\nG1 Z0.6\nG1 Z0.2\nG1 X100 Y100 E0.5\n")
    k = parse_text(t).segments
    assert set(k.kind) == {"extrude", "travel", "retract", "unretract", "wipe", "zmove"}
    assert (k[k.kind == "extrude"].de_mm > 0).all()


def test_only_extrude_is_path():
    r = parse_text(PRE + "G1 X110 Y100 E0.5\nG1 X120 Y100 E0\nG1 X121 Y100 E-0.1\n")
    e = r.extrusions()
    assert len(e) == 1 and e.iloc[0].x1_mm == 110


def test_g90_g91_and_m82_m83():
    t = "G21\nG90\nM82\nG92 X0 Y0 Z0 E0\nG1 Z0.2\nG1 X10 E1\nG91\nG1 X10 E1\nG90\nM82\nG1 X30 E3\n"
    s = parse_text(t).extrusions()
    assert s.x1_mm.tolist() == [10, 20, 30]
    assert np.allclose(s.de_mm, [1, 1, 1])  # G91이 E도 상대로 (g9x_sets_e), 다시 G90·M82 절대


def test_g9x_sets_e_false_klipper_style():
    # M83 뒤 G90: Marlin식은 E가 절대로 바뀜, Klipper식 (false)은 상대 유지
    t = "G90\nG92 X0 Y0 Z0.2 E0\nM83\nG90\nG1 X10 E0.5\nG1 X20 E0.5\n"
    marlin = parse_text(t, GCodeParams(g9x_sets_e=True)).extrusions()
    klipper = parse_text(t, GCodeParams(g9x_sets_e=False)).extrusions()
    assert len(marlin) == 1  # 두 번째 줄은 절대 E 0.5 → ΔE 0 (travel)
    assert len(klipper) == 2


def test_g92_resets_position():
    t = "G90\nM83\nG92 X0 Y0 Z0.2\nG1 X10 E0.4\nG92 X100 Y100\nG1 X110 E0.4\n"
    s = parse_text(t).extrusions()
    assert s.x0_mm.tolist() == [0, 100] and s.x1_mm.tolist() == [10, 110]


def test_g28_makes_position_unknown():
    with pytest.raises(GCodeError):
        parse_text("G90\nM83\nG92 X0 Y0 Z0.2\nG28 X\nG1 Y10 E0.5\n")


def test_g20_inch_units():
    s = parse_text("G90\nM83\nG92 X0 Y0 Z0.2\nG20\nG1 X1 E0.01\n").extrusions()
    assert s.iloc[0].x1_mm == pytest.approx(25.4) and s.iloc[0].de_mm == pytest.approx(0.254)


def test_arc_ij_and_r_same():
    a = parse_text(PRE.replace("X100 Y100", "X110 Y100") + "G3 X100 Y110 I-10 J0 E0.5\n").extrusions()
    b = parse_text(PRE.replace("X100 Y100", "X110 Y100") + "G3 X100 Y110 R10 E0.5\n").extrusions()
    assert len(a) == len(b)
    assert np.allclose(a[["x1_mm", "y1_mm"]].to_numpy(), b[["x1_mm", "y1_mm"]].to_numpy(), atol=1e-9)
    assert a.length_mm.sum() == pytest.approx(5 * math.pi, abs=1e-3)


def test_arc_negative_r_long_way():
    s = parse_text(PRE.replace("X100 Y100", "X110 Y100") + "G3 X100 Y110 R-10 E0.5\n").extrusions()
    assert s.length_mm.sum() == pytest.approx(15 * math.pi, abs=2e-3)  # 270°


def test_arc_cw_direction():
    # G2 (시계) 중심 (100,100), (110,100) → (100,90): 아래로 돎
    s = parse_text(PRE.replace("X100 Y100", "X110 Y100") + "G2 X100 Y90 I-10 J0 E0.5\n").extrusions()
    assert (s.y1_mm <= 100 + 1e-9).all()
    assert s.length_mm.max() <= 0.1 + 1e-12


def test_arc_radius_mismatch_error():
    with pytest.raises(GCodeError):
        parse_text(PRE.replace("X100 Y100", "X110 Y100") + "G3 X100 Y111 I-10 J0 E0.5\n")


def test_checksum_and_line_numbers():
    body = "N3 G1 X5"
    c = 0
    for ch in body:
        c ^= ord(ch)
    assert checksum_ok(f"{body}*{c}") is True
    assert checksum_ok(f"{body}*{(c + 1) % 256}") is False
    assert checksum_ok("G1 X5") is None


def test_comments_paren_and_semicolon_and_lowercase():
    t = "g21\ng90\nm83\ng92x100y100z0.2\ng1x110y100e.3 ; E9\nG1 (E7) X110 Y110 E0.3\n"
    r = parse_text(t)
    assert np.allclose(r.extrusions().de_mm, [0.3, 0.3])


def test_crlf_same_as_lf():
    t = PRE + "G1 X110 Y100 E0.5\nG1 X110 Y110 E0.5\n"
    a = parse_text(t).segments
    b = parse_text(t.replace("\n", "\r\n")).segments
    assert a.equals(b)


def test_fw_retract_g10_g11():
    s = parse_text(PRE + "G1 X110 Y100 E0.5\nG10\nG1 X110 Y110\nG11\nG1 X100 Y110 E0.5\n").segments
    assert s.kind.tolist().count("retract") == 1 and s.kind.tolist().count("unretract") == 1
    assert (s[s.kind.isin(["retract", "unretract"])].de_mm == 0).all()


def test_g10_with_params_is_error():
    with pytest.raises(GCodeError):
        parse_text(PRE + "G10 P0 S200\n")


def test_command_lists():
    assert command_class("G1") == "motion" and command_class("M83") == "state"
    assert command_class("M104") == "nomotion" and command_class("SET_VELOCITY_LIMIT") == "nomotion"
    assert command_class("T0") == "edge" and command_class("PRINT_START") == "edge"
    assert command_class("M999") == "unknown"


def test_unknown_after_first_extrusion_strict_error():
    with pytest.raises(GCodeError):
        parse_text(PRE + "G1 X110 Y100 E0.5\nM999\nG1 X110 Y110 E0.5\n")


def test_unknown_allowed_with_reason_counts():
    p = GCodeParams(allow_commands=[{"name": "M999", "reason": "시험"}])
    r = parse_text(PRE + "G1 X110 Y100 E0.5\nM999\nG1 X110 Y110 E0.5\n", p)
    assert r.allowed == {"M999": 1} and len(r.extrusions()) == 2


def test_macro_between_extrusions_error_but_start_end_ok():
    ok = parse_text("PRINT_START\nMY_MACRO\n" + PRE + "G1 X110 Y100 E0.5\nG1 E-1\nMY_END\nPRINT_END\n")
    assert ok.unknown == {"MY_MACRO": 1, "MY_END": 1}
    with pytest.raises(GCodeError):
        parse_text(PRE + "G1 X110 Y100 E0.5\nMY_MACRO\nG1 X110 Y110 E0.5\n")


def test_non_strict_counts_and_warns():
    r = parse_text(PRE + "G1 X110 Y100 E0.5\nM999\nG1 X110 Y110 E0.5\n", GCodeParams(strict_unknown=False))
    assert r.unknown == {"M999": 1} and any("M999" in w for w in r.warnings)


def test_type_aliases():
    assert normalize_type("External perimeter") == "WALL-OUTER"
    assert normalize_type("Outer wall") == "WALL-OUTER"
    assert normalize_type("Sparse infill") == "FILL"
    assert normalize_type("Ironing") == "IRONING"
    r = parse_text(PRE + ";TYPE:Mystery\nG1 X110 Y100 E0.5\n")
    assert r.extrusions().type.iloc[0] == "MYSTERY" and any("MYSTERY" in w for w in r.warnings)


def test_two_commands_one_line_error():
    with pytest.raises(GCodeError):
        parse_text("G90 G1 X10\n")
