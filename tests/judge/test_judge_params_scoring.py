from pathlib import Path

import pytest

from cvlab.judge import JudgeParams, load_params, score_c12

ROOT = Path(__file__).resolve().parents[2]


def test_config_yaml_loads_and_requires_u():
    p = load_params(ROOT / "config" / "judge.yaml")
    assert p.T_mm == 0.20 and p.U_mm is None and p.U_source is None
    assert (p.pass_min_pct, p.fail_max_pct, p.valid_min_pct) == (95, 5, 90)
    assert p.cell_mm == 0.2 and p.cell_mm_alt == 0.4
    with pytest.raises(ValueError):
        p.require_ready()
    q = load_params(ROOT / "config" / "judge.yaml", U_mm=0.0317, U_source="T2 5.2 기본 RSS")
    q.require_ready()


def test_from_dict_unknown_key_and_bad_values():
    with pytest.raises(ValueError, match="모르는"):
        JudgeParams.from_dict({"judge": {"T_mm": 0.2, "toleranse": 1}})
    with pytest.raises(ValueError):
        JudgeParams(T_mm=0)
    with pytest.raises(ValueError):
        JudgeParams(pass_min_pct=101)
    with pytest.raises(ValueError):
        JudgeParams(cell_stat="max")
    with pytest.raises(ValueError):
        JudgeParams(outlier_primary="best")
    assert JudgeParams.from_dict({"T_mm": 0.2, "U_mm": 0.02, "U_source": "x"}).U_mm == 0.02


def test_score_c12_basic():
    s = score_c12(["pass", "hold", "fail", "pass"], ["pass", "pass", "fail", "fail"])
    assert s["false_pass"] == 1 and not s["c12_required_ok"]
    assert s["false_fail_rate"] == 0.0 and s["c12_target_ok"]
    assert s["hold_rate"] == 0.25 and s["insufficient_rate"] == 0.0
    assert s["confusion"]["fail"]["pass"] == 1


def test_score_c12_target_boundary():
    true = ["pass"] * 20 + ["fail"] * 3 + ["borderline"] * 2
    pred1 = ["fail"] + ["pass"] * 19 + ["fail", "insufficient", "hold"] + ["hold", "pass"]
    s1 = score_c12(pred1, true)
    assert s1["false_fail"] == 1 and s1["c12_target_ok"]          # 1/20 = 5 % ≤ 5 %
    assert s1["c12_required_ok"] and s1["true_fail_to_insufficient"] == 1
    assert s1["borderline_pred"]["hold"] == 1 and s1["borderline_pred"]["pass"] == 1
    pred2 = ["fail", "fail"] + ["pass"] * 18 + pred1[20:]
    assert not score_c12(pred2, true)["c12_target_ok"]             # 2/20 = 10 %


def test_score_c12_bad_input():
    with pytest.raises(ValueError):
        score_c12(["pass"], ["pass", "fail"])
    with pytest.raises(ValueError):
        score_c12(["ok"], ["pass"])
    with pytest.raises(ValueError):
        score_c12(["pass"], ["hold"])
