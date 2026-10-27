import numpy as np
import pytest

from cvlab.judge import cooling_criterion, judge_print
from judge_maps import layer, params


def _m16():
    a = np.zeros((10, 10)); a.flat[:6] = 0.5
    out = np.zeros((10, 10), bool); out.flat[:6] = True
    return a, out


def test_m16_outlier_changes_verdict():
    a, out = _m16()
    r = judge_print([layer(a, outlier=out)], params())
    ov = r.outlier_variants
    assert ov["before"]["verdict"] == "fail"        # 불합격 6 % > 5 %
    assert ov["after"]["verdict"] == "pass"         # 유효 94/100 ≥ 90 %, 전부 합격
    assert ov["differ"] and ov["primary"] == "before"
    assert r.verdict == "fail"
    assert any("이상치" in w for w in r.warnings)


def test_outlier_primary_rule_options():
    a, out = _m16()
    assert judge_print([layer(a, outlier=out)], params(outlier_primary="after")).verdict == "pass"
    assert judge_print([layer(a, outlier=out)], params(outlier_primary="before")).verdict == "fail"


def test_outlier_worse_order_insufficient_over_hold():
    # 제외 후 유효 칸이 90 % 아래로 → 측정 불충분이 보류보다 덜 유리
    a = np.zeros((10, 10)); a.flat[:15] = 0.2    # 보류 15 %
    out = np.zeros((10, 10), bool); out.flat[:15] = True
    r = judge_print([layer(a, outlier=out)], params())
    assert r.outlier_variants["before"]["verdict"] == "hold"
    assert r.outlier_variants["after"]["verdict"] == "insufficient"
    assert r.verdict == "insufficient"


def test_outlier_no_change_no_warning():
    a = np.zeros((10, 10))
    out = np.zeros((10, 10), bool); out[0, 0] = True
    r = judge_print([layer(a, outlier=out)], params())
    assert not r.outlier_variants["differ"] and r.verdict == "pass"
    assert not any("이상치" in w for w in r.warnings)
    assert judge_print([layer(a)], params()).outlier_variants is None


def test_m14_cooled_rejected():
    with pytest.raises(ValueError, match="MF-JDG-05"):
        judge_print([layer(np.zeros((2, 2)), state="cooled")], params())


def test_m14_post_same_verdict_and_difference():
    ls = [layer(np.zeros((4, 4)), 0), layer(np.full((4, 4), 0.05), 1)]
    post_a = np.full((4, 4), 0.02); post_a[0, 0] = np.nan
    post = layer(post_a, 1, state="cooled")
    r0 = judge_print(ls, params())
    r1 = judge_print(ls, params(), post=post, height_mm=20.0, specimen_temp_c=30.0, room_temp_c=25.0)
    assert r0.verdict == r1.verdict and r0.counts == r1.counts
    d = r1.cooled["difference"]
    assert d["n"] == 15
    assert d["mean_um"] == pytest.approx(-30.0) and d["median_um"] == pytest.approx(-30.0)
    assert d["max_abs_um"] == pytest.approx(30.0)
    c = r1.cooled["criterion"]
    assert c["ok"] is False                           # 1.36 µm/°C × 5 °C = 6.8 µm > 5 µm
    assert any("식힘 부족" in w for w in r1.warnings)


def test_post_must_match_last_layer():
    ls = [layer(np.zeros((2, 2)), 0), layer(np.zeros((2, 2)), 1)]
    with pytest.raises(ValueError):
        judge_print(ls, params(), post=layer(np.zeros((2, 2)), 0, state="cooled"))
    with pytest.raises(ValueError):
        judge_print(ls, params(), post=layer(np.zeros((2, 2)), 1, state="in_process"))
    with pytest.raises(ValueError):
        judge_print(ls, params(), post=layer(np.zeros((3, 2)), 1, state="cooled"))


def test_cooled_no_common_cells():
    ls = [layer(np.zeros((2, 2)), 0)]
    r = judge_print(ls, params(), post=layer(np.full((2, 2), np.nan), 0, state="cooled"))
    assert r.cooled["difference"] is None
    assert any("공통" in w for w in r.warnings)
    assert r.cooled["criterion"]["ok"] is None


def test_cooling_criterion_example():
    c = cooling_criterion(20.0, 28.0, 25.0)
    assert c["um_per_c"] == pytest.approx(1.36)
    assert c["delta_T_max_c"] == pytest.approx(5 / 1.36)      # 3.68 °C
    assert c["residual_shrink_um"] == pytest.approx(4.08)
    assert c["ok"] is True
    assert cooling_criterion(None, 28.0, 25.0)["ok"] is None
