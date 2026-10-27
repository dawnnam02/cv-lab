"""T7a 설정 시험 (config/triangulation.yaml)."""
from pathlib import Path

import pytest
import yaml

from cvlab.triangulation import TriParams

CFG = Path(__file__).resolve().parents[2] / "config" / "triangulation.yaml"


def test_yaml_defaults_equal_dataclass_defaults():
    assert TriParams.from_yaml(CFG) == TriParams()


def test_yaml_single_top_key_and_no_calibration():
    doc = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    assert list(doc) == ["triangulation"]
    for k in ("K", "dist", "laser_plane", "T_G_M", "T_S_C", "scan_axis"):
        assert k not in doc["triangulation"]


def test_unknown_key_rejected():
    with pytest.raises(ValueError, match="모르는 키"):
        TriParams.from_dict({"method": "cog", "halfwin": 5})


def test_bad_values_rejected():
    for bad in ({"method": "foo"}, {"threshold_k_sigma": 0}, {"guide_win_cols": 50}, {"half_win_px": 0}):
        with pytest.raises(ValueError):
            TriParams.from_dict(bad)


def test_yaml_wrong_top_key(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text("tri:\n  method: cog\n", encoding="utf-8")
    with pytest.raises(ValueError):
        TriParams.from_yaml(p)
