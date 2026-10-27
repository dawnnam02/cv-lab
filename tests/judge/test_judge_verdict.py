import json

import numpy as np
import pytest

from cvlab.judge import JudgeParams, LayerInput, decide, judge_print, judge_print_fine
from judge_maps import counts_map, layer, params, texture_fine


def test_m01_all_zero():
    r = judge_print([layer(np.zeros((10, 10)))], params())
    assert r.verdict == "pass"
    assert r.pct["pass_pct"] == 100.0
    assert r.counts == {"n_region": 100, "n_valid": 100, "n_pass": 100, "n_hold": 0, "n_fail": 0}


def test_m03_pass_exactly_95():
    r = judge_print([layer(counts_map(190, 10, 0, (10, 20)))], params())
    assert r.verdict == "pass" and r.pct["pass_pct"] == 95.0


def test_m04_hold_fail_exactly_5():
    r = judge_print([layer(counts_map(188, 2, 10, (10, 20)))], params())
    assert r.verdict == "hold"
    assert r.pct["pass_pct"] == 94.0 and r.pct["fail_pct"] == 5.0


def test_m05_fail_over_5():
    r = judge_print([layer(counts_map(189, 0, 11, (10, 20)))], params())
    assert r.verdict == "fail" and r.pct["fail_pct"] == 5.5


def test_m06_valid_90_boundary():
    a90 = np.r_[np.zeros(90), np.full(10, np.nan)].reshape(10, 10)
    a89 = np.r_[np.zeros(89), np.full(11, np.nan)].reshape(10, 10)
    assert judge_print([layer(a90)], params()).verdict == "pass"
    r = judge_print([layer(a89)], params())
    assert r.verdict == "insufficient" and r.counts["n_valid"] == 89


def test_m07_outside_region_ignored():
    a = np.zeros((10, 10))
    reg = np.ones((10, 10), bool)
    reg[:, 8:] = False
    a[:, 8] = np.nan
    a[:, 9] = 5.0
    r = judge_print([layer(a, region=reg)], params())
    assert r.verdict == "pass"
    assert r.counts["n_region"] == 80 and r.counts["n_valid"] == 80 and r.counts["n_fail"] == 0
    assert r.metrics["all"]["max_abs_um"] == 0.0


def test_m08_pooled_not_layer_average():
    ls = [layer(np.full((1, 10), 0.3), 0), layer(np.zeros((33, 30)), 1)]
    r = judge_print(ls, params())
    assert r.verdict == "pass"
    assert r.counts["n_valid"] == 1000 and r.counts["n_fail"] == 10
    assert r.pct["pass_pct"] == 99.0
    assert r.per_layer[0]["warn_fail"] and not r.per_layer[1]["warn_fail"]
    assert any("층 0" in w and "MF-JDG-06" in w for w in r.warnings)
    # 층 비율 평균이었다면 50 % → 합격일 수 없음
    assert np.mean([L["pass_pct"] for L in r.per_layer]) == 50.0


def test_m15_duplicate_layer_error():
    with pytest.raises(ValueError, match="두 번"):
        judge_print([layer(np.zeros((2, 2)), 3), layer(np.zeros((2, 2)), 3)], params())


def test_m17_empty_region_insufficient():
    r = judge_print([layer(np.zeros((5, 5)), region=np.zeros((5, 5), bool))], params())
    assert r.verdict == "insufficient" and r.counts["n_region"] == 0
    assert any("비어" in w for w in r.warnings)


def test_pass_and_fail_never_both():
    p = params()
    for n in range(1, 61):
        for n_pass in range(n + 1):
            for n_fail in range(n - n_pass + 1):
                ok_pass = n_pass * 100 >= 95 * n
                ok_fail = n_fail * 100 > 5 * n
                assert not (ok_pass and ok_fail)
                v = decide(n, n, n_pass, n_fail, p)
                assert v == ("pass" if ok_pass else "fail" if ok_fail else "hold")


def test_layer_order_independent():
    a = [layer(counts_map(9, 0, 1, (2, 5)), 2), layer(np.zeros((4, 5)), 0), layer(np.zeros((3, 3)), 1)]
    r1 = judge_print(a, params())
    r2 = judge_print(list(reversed(a)), params())
    assert r1.verdict == r2.verdict and r1.counts == r2.counts
    assert [L["layer_idx"] for L in r1.per_layer] == [0, 1, 2]


def test_method_a_reported():
    # 보류 값 0.2 = T → 방식 A에서는 합격점
    r = judge_print([layer(counts_map(188, 2, 10, (10, 20)))], params())
    assert r.method_a["verdict"] == "pass"
    assert r.method_a["counts"]["n_pass"] == 190 and r.method_a["counts"]["n_hold"] == 0
    assert any("방식 A" in w for w in r.warnings)


def test_metrics_values():
    a = np.array([[0.1, -0.1, 0.05, 0.25]])
    r = judge_print([layer(a)], params())
    m = r.metrics["all"]
    e = a.ravel() * 1000
    assert m["n"] == 4
    assert m["mean_um"] == pytest.approx(75.0)
    assert m["std_um"] == pytest.approx(np.std(e, ddof=1))
    assert m["rms_um"] == pytest.approx(np.sqrt(np.mean(e ** 2)))
    assert m["max_abs_um"] == pytest.approx(250.0)
    assert m["p95_abs_um"] == pytest.approx(np.percentile(np.abs(e), 95))
    assert m["within_T_pct"] == 75.0
    assert r.per_layer[0]["metrics"]["n"] == 4


def test_to_dict_json_roundtrip(tmp_path):
    r = judge_print([layer(np.r_[np.zeros(95), np.full(5, np.nan)].reshape(10, 10))],
                    params(U_source="T2 5.2 기본 RSS 31.7 µm", U_mm=0.0317))
    path = tmp_path / "r.json"
    path.write_text(r.to_json(indent=1), encoding="utf-8")
    d = json.loads(path.read_text(encoding="utf-8"))
    assert d["params"]["T_mm"] == 0.2 and d["params"]["U_mm"] == 0.0317
    assert d["params"]["U_source"] == "T2 5.2 기본 RSS 31.7 µm"
    for k in ("pass_min_pct", "fail_max_pct", "valid_min_pct", "cell_mm", "cell_mm_alt", "layer_fail_warn_pct"):
        assert k in d["params"]
    assert d["thresholds"]["t_pass_nm"] == 168300 and d["thresholds"]["t_fail_nm"] == 231700
    assert any("하드웨어 성능의 증거가 아닙니다" in n for n in d["notes"])
    assert any("측정이 못 보는 오차" in n for n in d["notes"])


def test_exclusion_counts():
    reg = np.ones((4, 5), bool); reg[:, 0] = False; reg[0, 1] = False
    code = np.zeros((4, 5), np.int8); code[:, 0] = 1; code[0, 1] = 2
    a = np.zeros((4, 5)); a[3, 4] = np.nan
    r = judge_print([layer(a, region=reg, exclusion_code=code)], params())
    by = r.exclusions["by_code"]
    assert by["엣지 띠"] == 4 and by["가림 예측"] == 1 and by["이유 없음"] == 0
    assert r.exclusions["no_delta_in_region"] == 1


def test_exclusion_code_inside_region_error():
    code = np.zeros((2, 2), np.int8); code[0, 0] = 1
    with pytest.raises(ValueError):
        layer(np.zeros((2, 2)), exclusion_code=code)
    with pytest.raises(ValueError):
        layer(np.zeros((2, 2)), region=np.zeros((2, 2), bool), exclusion_code=np.full((2, 2), 6))


def test_u_source_required():
    with pytest.raises(ValueError, match="U_source"):
        judge_print([layer(np.zeros((2, 2)))], JudgeParams(U_mm=0.03))
    with pytest.raises(ValueError, match="U_source"):
        judge_print([layer(np.zeros((2, 2)))], JudgeParams(U_mm=0.03, U_source="  "))
    with pytest.raises(ValueError, match="U_mm"):
        judge_print([layer(np.zeros((2, 2)))], JudgeParams(U_source="x"))


def test_unknown_thermal_state_error():
    with pytest.raises(ValueError):
        judge_print([layer(np.zeros((2, 2)), state="hot")], params())


def test_layer_warn_threshold_exact():
    r = judge_print([layer(counts_map(5, 0, 5, (2, 5)), 0), layer(counts_map(4, 0, 6, (2, 5)), 1),
                     layer(np.zeros((100, 10)), 2)], params())
    assert [L["warn_fail"] for L in r.per_layer] == [False, True, False]


def test_judge_print_fine_primary_and_alt():
    fine = texture_fine(amp=0.12)                 # 0.2 mm 칸 0.10 ± 0.0767 (보류 칸 생김), 0.4 mm 칸 0.10
    L = LayerInput(0, "in_process", fine, np.ones(fine.shape, bool))
    out = judge_print_fine([L], params(), res_mm=0.02)
    # 고운 20 × 40 → 0.2 mm 칸 2 × 4, 0.4 mm 칸 1 × 2
    assert out["primary"].counts["n_valid"] == 8 and out["alt"].counts["n_valid"] == 2
    assert out["primary"].counts["n_hold"] == 4
    assert out["primary"].verdict == "hold" and out["alt"].verdict == "pass"
    assert any("MF-JDG-04" in w for w in out["primary"].warnings)
    assert out["alt"].params["cell_mm_used"] == 0.4


def test_empty_layer_list_error():
    with pytest.raises(ValueError):
        judge_print([], params())
