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


# --- J-1: 문턱 합 < 100 거부 -------------------------------------------------

class _UncheckedThresholds:
    """검사를 건너뛴 문턱 (J-1 이전 동작 재현용). decide는 pct()만 쓴다."""

    def __init__(self, pass_min, fail_max, valid_min=90):
        from fractions import Fraction
        self._v = {"pass_min_pct": Fraction(pass_min), "fail_max_pct": Fraction(fail_max),
                   "valid_min_pct": Fraction(valid_min)}

    def pct(self, name):
        return self._v[name]


def test_j1_problem_case_reproduced_without_check():
    from cvlab.judge import decide
    # 100칸: 합격 92 · 보류 0 · 불합격 8 → 문턱 90 · 5면 합격·불합격이 함께 참
    n, n_pass, n_fail = 100, 92, 8
    assert n_pass * 100 >= 90 * n and n_fail * 100 > 5 * n
    assert decide(n, n, n_pass, n_fail, _UncheckedThresholds(90, 5)) == "pass"  # 고치기 전 결과


def test_j1_sum_below_100_rejected():
    with pytest.raises(ValueError, match=r"pass_min_pct \+ fail_max_pct < 100"):
        JudgeParams(pass_min_pct=90, fail_max_pct=5)
    with pytest.raises(ValueError, match="< 100"):
        JudgeParams(pass_min_pct=94.5, fail_max_pct=5)
    with pytest.raises(ValueError, match="< 100"):
        JudgeParams.from_dict({"judge": {"pass_min_pct": 90}})
    with pytest.raises(ValueError, match="< 100"):
        load_params(ROOT / "config" / "judge.yaml", pass_min_pct=90)


def test_j1_sum_at_or_above_100_allowed_and_default_unchanged():
    from cvlab.judge import decide
    JudgeParams(pass_min_pct=90, fail_max_pct=10)
    JudgeParams(pass_min_pct=95.5, fail_max_pct=4.5)
    JudgeParams(pass_min_pct=97, fail_max_pct=5)
    p = load_params(ROOT / "config" / "judge.yaml")
    assert (p.pass_min_pct, p.fail_max_pct) == (95, 5)
    # 기본값 (95 · 5): 같은 칸 수는 불합격, 경계 M03 · M04 · M05 그대로
    assert decide(100, 100, 92, 8, p) == "fail"
    assert decide(200, 200, 190, 0, p) == "pass"
    assert decide(200, 200, 188, 10, p) == "hold"
    assert decide(200, 200, 189, 11, p) == "fail"
    # 합 100 경계 (90 · 10): 합격·불합격이 함께 참인 조합 없음
    q = JudgeParams(pass_min_pct=90, fail_max_pct=10)
    for n in range(1, 41):
        for n_pass in range(n + 1):
            for n_fail in range(n - n_pass + 1):
                assert not (n_pass * 100 >= 90 * n and n_fail * 100 > 10 * n)
                v = decide(n, n, n_pass, n_fail, q)
                assert v == ("pass" if n_pass * 100 >= 90 * n else "fail" if n_fail * 100 > 10 * n else "hold")


def test_check_u_accepts_numpy_scalars():
    import numpy as np
    from cvlab.judge.params import check_U
    assert check_U(0.2, np.float32(0.0317)) == pytest.approx(0.0317, abs=1e-7)
    assert check_U(0.2, np.float64(0.0317)) == 0.0317
    with pytest.raises(ValueError, match="NaN"):
        check_U(0.2, np.float32("nan"))
    with pytest.raises(ValueError, match="숫자가 아님"):
        check_U(0.2, np.bool_(True))
