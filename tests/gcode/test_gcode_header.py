"""GC6 머리말 · GC7 압출량 대조 · 설정 파일."""
import hashlib

import pytest

from cvlab.gcode import GCodeParams, parse_file, parse_text
from cvlab.gcode.header import map_flavor
from gcode_helpers import CONFIG, P042, PRE, hand


def test_flavor_mapping():
    assert map_flavor("Marlin") == "marlin" and map_flavor("marlin2") == "marlin"
    assert map_flavor("klipper") == "klipper" and map_flavor("reprapfirmware") == "reprap"
    assert map_flavor("Griffin") == "other" and map_flavor(None) is None


def test_prusa_mimic_header():
    h = parse_file(hand("H12"), P042).header
    assert (h["slicer_name"], h["gcode_flavor"]) == ("PrusaSlicer", "marlin")
    assert h["nozzle_dia_mm"] == 0.4 and h["filament_d_mm"] == 1.75 and h["layer_h_mm"] == 0.2
    assert h["line_widths"]["WALL-OUTER"] == 0.42 and h["line_width_mm"] == 0.45


def test_cura_mimic_header():
    r = parse_file(hand("H13"), P042)
    assert r.header["slicer_name"] == "Cura_SteamEngine" and r.header["layers_declared"] == len(r.layers)


def test_missing_header_values_none_and_warned():
    r = parse_text(PRE + "G1 X110 Y100 E0.3\n")
    assert r.header["slicer_name"] is None and r.header["gcode_flavor"] is None
    assert any("slicer_name" in w for w in r.warnings)
    assert r.filament_diff_pct is None


def test_sha256_of_file_bytes():
    f = hand("H19")
    r = parse_file(f, P042)
    assert r.header["gcode_sha256"] == hashlib.sha256(open(f, "rb").read()).hexdigest()


def test_filament_diff_within_1pct():
    for k in ("H12", "H13", "H23"):
        r = parse_file(hand(k), P042)
        assert r.filament_diff_pct is not None and abs(r.filament_diff_pct) <= 1.0, k


def test_layer_count_header_priority():
    r = parse_file(hand("H22"), P042)
    assert r.header["layers_declared_all"] == {"total layers count": 2, "total layer number": 4}
    assert r.header["layers_declared"] == 2


def test_config_yaml_loads_and_rejects_unknown_key():
    p = GCodeParams.from_yaml(CONFIG)
    assert p == GCodeParams()
    with pytest.raises(ValueError):
        GCodeParams.from_dict({"gcode": {"arc_seg": 0.1}})
    with pytest.raises(ValueError):
        GCodeParams(allow_commands=[{"name": "M999", "reason": ""}])
    with pytest.raises(ValueError):
        GCodeParams(layer_source="maybe")
