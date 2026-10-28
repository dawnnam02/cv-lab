"""판정 거부 X1–X7 (J-2, D-21). 메타 값은 시험용 가정이며 실측 기록이 아니다."""
import json

import numpy as np
import pytest

from cvlab.judge import META_FIELDS as F
from cvlab.judge import REJECT_CODES, LayerInput, judge_print, judge_print_fine
from cvlab.judge.aggregate import EXCLUSION_CODES, aggregate_exclusion_code
from judge_maps import counts_map, layer, params

SES = "PS-2026-11-20-A"
CAL = "CAL-2026-11-20-A"


def good_meta(n=3, layer_count=None):
    """모든 대책을 갖춘 메타 (거부 조건 0)."""
    scans = [{
        F["scan_id"]: f"S01_r01_L{k:03d}", F["session_id"]: SES, F["layer_idx"]: k,
        F["layer_count"]: n if layer_count is None else layer_count, F["layer_macro_version"]: "LM-T14-3",
        F["layer_end_t_ns"]: 5_000_000_000 + k * 10**9, F["thermal_state"]: "in_process",
        F["bed_ref_id"]: "REF-BED-001", F["zero_ref_method"]: "step_gauge", F["mesh_enabled"]: True,
        F["bed_mesh_file"]: "printer/bed_mesh.json", F["calibration_id"]: CAL,
    } for k in range(n)]
    refs = [{F["ref_id"]: "REF-BED-001", F["ref_kind"]: "bed_bare", F["ref_calibration_id"]: CAL,
             F["ref_t_start_ns"]: 1_000_000_000, F["ref_session_id"]: SES}]
    return {"scans": scans, "refs": refs}


def layers(n=3, a=None):
    a = np.zeros((10, 10)) if a is None else a
    return [layer(a, k) for k in range(n)]


def rejected(meta, code, ls=None):
    r = judge_print(layers() if ls is None else ls, params(), meta=meta)
    assert r.verdict == "insufficient", r.reject
    assert code in r.reject["codes"] and r.reject["rejected"]
    assert r.reject["reference_verdict"] == "pass"  # 거부가 없었다면 나왔을 참고 판정
    assert any(f"판정 거부 {code}" in w for w in r.warnings) or code == "X6"
    return r


def test_field_names_follow_spec():
    assert all(v.split(".")[0] in ("meta", "ref", "rep") for v in F.values())
    assert list(REJECT_CODES) == [f"X{i}" for i in range(1, 8)]


def test_no_reject_keeps_existing_verdicts():
    for a, want in ((np.zeros((10, 20)), "pass"), (counts_map(188, 2, 10, (10, 20)), "hold"),
                    (counts_map(189, 0, 11, (10, 20)), "fail")):
        r0 = judge_print(layers(3, a), params())
        r = judge_print(layers(3, a), params(), meta=good_meta())
        assert r.verdict == r0.verdict == want
        assert r.counts == r0.counts and r.reject["codes"] == [] and r.reject["meta_checked"]
        assert not any("판정 거부" in w for w in r.warnings)


def test_no_meta_is_not_checked_but_warned():
    r = judge_print(layers(), params())
    assert r.verdict == "pass" and r.reject["codes"] == [] and r.reject["meta_checked"] is False
    assert r.reject["not_checked"] == ["X1", "X2", "X3", "X4", "X7"]
    assert any("메타데이터 없음" in w for w in r.warnings)


@pytest.mark.parametrize("case", ["no_id", "not_bed_bare", "other_session", "unknown_ref", "after_print", "two_ids"])
def test_x1_bed_reference(case):
    m = good_meta()
    s, ref = m["scans"][1], m["refs"][0]
    if case == "no_id":
        s[F["bed_ref_id"]] = None
    elif case == "not_bed_bare":
        ref[F["ref_kind"]] = "bed_marker"
    elif case == "other_session":
        ref[F["ref_session_id"]] = "PS-2026-11-19-A"
    elif case == "unknown_ref":
        s[F["bed_ref_id"]] = "REF-BED-009"
    elif case == "after_print":
        ref[F["ref_t_start_ns"]] = 6_000_000_000  # 첫 층 끝 5e9 뒤
    elif case == "two_ids":
        m["refs"].append({**ref, F["ref_id"]: "REF-BED-002"})
        s[F["bed_ref_id"]] = "REF-BED-002"
    rejected(m, "X1")


@pytest.mark.parametrize("value", ["z_only", None, "", "manual"])
def test_x2_zero_ref_method(value):
    m = good_meta()
    m["scans"][0][F["zero_ref_method"]] = value
    r = rejected(m, "X2")
    assert r.reject["codes"] == ["X2"]


def test_x3_mesh_file():
    m = good_meta()
    m["scans"][2][F["bed_mesh_file"]] = None
    rejected(m, "X3")
    # 메시를 끈 세션 (False로 적힘)은 메시 표가 없어도 통과
    m2 = good_meta()
    for s in m2["scans"]:
        s[F["mesh_enabled"]], s[F["bed_mesh_file"]] = False, None
    assert judge_print(layers(), params(), meta=m2).verdict == "pass"


@pytest.mark.parametrize("case", ["differ", "scan_missing", "ref_missing"])
def test_x4_calibration_id(case):
    m = good_meta()
    if case == "differ":
        m["scans"][1][F["calibration_id"]] = "CAL-2026-11-21-B"
    elif case == "scan_missing":
        m["scans"][1][F["calibration_id"]] = None
    else:
        m["refs"][0][F["ref_calibration_id"]] = None
    r = rejected(m, "X4")
    assert r.reject["codes"] == ["X4"]


def test_x5_thermal_state():
    m = good_meta()
    m["scans"][2][F["thermal_state"]] = "cooled"
    rejected(m, "X5")
    m = good_meta()
    m["scans"][0][F["thermal_state"]] = None
    rejected(m, "X5")
    # 판정 층에 메타 행이 없음 (열 상태 모름)
    m = good_meta(3)
    m["scans"].pop()
    r = judge_print(layers(3), params(), meta=m)
    assert r.verdict == "insufficient" and "X5" in r.reject["codes"]
    assert "층 2: 스캔 메타 행 없음" in r.reject["reasons"]["X5"][0]
    # LayerInput 열 상태가 없음 → X5 (메타 없이도)
    r = judge_print([layer(np.zeros((4, 4)), 0, state=None)], params())
    assert r.verdict == "insufficient" and r.reject["codes"] == ["X5"]
    # cooled LayerInput은 지금처럼 오류 (M14 그대로, 식힌 재측정은 post로)
    with pytest.raises(ValueError, match="post"):
        judge_print([layer(np.zeros((4, 4)), 0, state="cooled")], params(), meta=good_meta(1))


def test_x6_is_r2_valid_ratio():
    a89 = np.r_[np.zeros(89), np.full(11, np.nan)].reshape(10, 10)
    a90 = np.r_[np.zeros(90), np.full(10, np.nan)].reshape(10, 10)
    r = judge_print([layer(a89)], params(), meta=good_meta(1))
    assert r.verdict == "insufficient" and r.reject["codes"] == ["X6"]
    assert r.reject["reference_verdict"] == "insufficient"  # R2 그 자체라 참고 판정도 같음
    assert "89/100" in r.reject["reasons"]["X6"][0]
    r = judge_print([layer(a90)], params(), meta=good_meta(1))
    assert r.verdict == "pass" and r.reject["codes"] == []
    # 메타 없이도 X6은 늘 검사
    assert judge_print([layer(a89)], params()).reject["codes"] == ["X6"]


@pytest.mark.parametrize("case", ["missing_layer", "no_count", "mixed_count", "over_count", "no_scans"])
def test_x7_layer_count(case):
    m = good_meta(3)
    ls = layers(3)
    if case == "missing_layer":  # G코드 4층인데 3층만 스캔
        m = good_meta(3, layer_count=4)
    elif case == "no_count":
        for s in m["scans"]:
            s[F["layer_count"]] = None
    elif case == "mixed_count":
        m["scans"][0][F["layer_count"]] = 4
    elif case == "over_count":
        m = good_meta(3, layer_count=2)
    else:
        m["scans"] = []
    r = rejected(m, "X7", ls)
    if case == "missing_layer":
        assert "빠진 층 [3]" in r.reject["reasons"]["X7"][0] and "LM-T14-3" in r.reject["reasons"]["X7"][0]


def test_x7_missing_middle_layer_between_judged():
    m = good_meta(3)
    ls = [layer(np.zeros((5, 5)), k) for k in (0, 2)]
    m["scans"].pop(1)
    r = judge_print(ls, params(), meta=m)
    assert r.verdict == "insufficient" and r.reject["codes"] == ["X7"]


def test_reject_overrides_fail_and_lists_all_codes_in_order():
    m = good_meta()
    s = m["scans"][0]
    s[F["zero_ref_method"]], s[F["bed_ref_id"]], s[F["bed_mesh_file"]] = "z_only", None, None
    a = counts_map(189, 0, 11, (10, 20))
    r = judge_print(layers(3, a), params(), meta=m)
    assert r.verdict == "insufficient" and r.reject["codes"] == ["X1", "X2", "X3"]
    assert r.reject["reference_verdict"] == "fail"
    assert r.reject["reference_U"] == {"U_um": 30.0, "U_source": "시험용 가정 (손계산)"}
    assert "92.4" in r.reject["note"]
    d = json.loads(r.to_json())
    assert d["verdict"] == "insufficient" and d["reject"]["codes"] == ["X1", "X2", "X3"]


def test_reasons_capped_with_total():
    n = 15
    m = good_meta(n)
    for s in m["scans"]:
        s[F["zero_ref_method"]] = "z_only"
    r = judge_print(layers(n, np.zeros((3, 3))), params(), meta=m)
    assert r.reject["n_reasons"]["X2"] == n and len(r.reject["reasons"]["X2"]) == 11
    assert any("외 14건" in w for w in r.warnings)


def test_bad_meta_shape_is_error():
    with pytest.raises(ValueError, match="모르는 키"):
        judge_print(layers(), params(), meta={"scan": []})
    with pytest.raises(ValueError, match="행 목록"):
        judge_print(layers(), params(), meta={"scans": {"a": 1}})


def test_fine_passes_meta_through():
    a = np.zeros((20, 40))
    fine = [LayerInput(k, "in_process", a, np.ones(a.shape, bool)) for k in range(2)]
    m = good_meta(2)
    out = judge_print_fine(fine, params(), res_mm=0.02, meta=m)
    assert out["primary"].verdict == out["alt"].verdict == "pass"
    m["scans"][1][F["calibration_id"]] = "CAL-2026-11-21-B"
    out = judge_print_fine(fine, params(), res_mm=0.02, meta=m)
    assert out["primary"].reject["codes"] == out["alt"].reject["codes"] == ["X4"]


# ---- J-4: 명세 v1.0 (한 층 여러 줄 · 줄마다 bed_bare · post) ----

def v10_meta(n=3, passes=2, post=True):
    """명세 v1.0 꼴 정상 메타: 층 n개 × 줄 passes개, 줄 p → REF-BED-00(p+1), post는 마지막 층 줄마다 (cooled)."""
    def row(k, p, timing):
        lay = timing == "layer"
        return {
            F["scan_id"]: (f"S01_r01_L{k:03d}" if lay else "S01_r01") + (f"_p{p:02d}" if p else ""),
            F["session_id"]: SES, F["layer_idx"]: k, F["scan_pass_idx"]: p, F["timing"]: timing,
            F["layer_count"]: n, F["layer_macro_version"]: "LM-T14-3",
            F["layer_end_t_ns"]: 5_000_000_000 + k * 10**9,
            F["thermal_state"]: "in_process" if lay else "cooled",
            F["bed_ref_id"]: f"REF-BED-{p + 1:03d}", F["zero_ref_method"]: "step_gauge", F["mesh_enabled"]: True,
            F["bed_mesh_file"]: "printer/bed_mesh.json", F["calibration_id"]: CAL,
        }
    scans = [row(k, p, "layer") for k in range(n) for p in range(passes)]
    if post:
        scans += [row(n - 1, p, "post") for p in range(passes)]
    refs = [{F["ref_id"]: f"REF-BED-{p + 1:03d}", F["ref_kind"]: "bed_bare", F["ref_scan_pass_idx"]: p,
             F["ref_calibration_id"]: CAL, F["ref_t_start_ns"]: 1_000_000_000 + p, F["ref_session_id"]: SES}
            for p in range(passes)]
    return {"scans": scans, "refs": refs}


def _find(m, k, p, timing="layer"):
    return next(s for s in m["scans"] if s[F["layer_idx"]] == k and s[F["scan_pass_idx"]] == p
                and s[F["timing"]] == timing)


def test_j4_field_names():
    assert F["scan_pass_idx"] == "meta.scan_pass_idx" and F["timing"] == "meta.timing"
    assert F["ref_scan_pass_idx"] == "ref.scan_pass_idx"


@pytest.mark.parametrize("passes,post", [(2, False), (2, True), (1, True), (3, True)])
def test_j4_v10_multi_pass_no_reject(passes, post):
    """팀장 재현 (6차 §6.1): 층 3 × 두 줄, 줄마다 bed_bare, post 포함 → 거부 0, 판정 그대로."""
    for a, want in ((np.zeros((10, 20)), "pass"), (counts_map(188, 2, 10, (10, 20)), "hold"),
                    (counts_map(189, 0, 11, (10, 20)), "fail")):
        r0 = judge_print(layers(3, a), params())
        r = judge_print(layers(3, a), params(), meta=v10_meta(3, passes, post))
        assert r.verdict == r0.verdict == want, r.reject
        assert r.reject["codes"] == [] and r.reject["meta_checked"] and r.counts == r0.counts


@pytest.mark.parametrize("case", ["one_scan_wrong", "pass1_points_pass0", "ref_pass_missing",
                                  "ref_pass_wrong", "bad_scan_pass", "post_wrong"])
def test_j4_x1_per_pass(case):
    m = v10_meta()
    if case == "one_scan_wrong":  # 줄 1 스캔 하나만 줄 0 기준
        _find(m, 1, 1)[F["bed_ref_id"]] = "REF-BED-001"
    elif case == "pass1_points_pass0":  # 줄 1 전부 줄 0 기준 (줄 안에선 한 값이지만 다른 줄 bed_bare)
        for s in m["scans"]:
            if s[F["scan_pass_idx"]] == 1:
                s[F["bed_ref_id"]] = "REF-BED-001"
    elif case == "ref_pass_missing":  # bed_bare 줄 번호 빈 칸 → 줄 0으로 봄 → 줄 1 스캔과 안 맞음
        m["refs"][1][F["ref_scan_pass_idx"]] = None
    elif case == "ref_pass_wrong":
        m["refs"][1][F["ref_scan_pass_idx"]] = 0
    elif case == "bad_scan_pass":
        _find(m, 2, 1)[F["scan_pass_idx"]] = -1
    else:  # post 행도 X1은 그대로 봄
        _find(m, 2, 1, "post")[F["bed_ref_id"]] = "REF-BED-001"
    r = rejected(m, "X1")
    assert r.reject["codes"] == ["X1"], r.reject
    if case == "one_scan_wrong":
        reasons = " ".join(r.reject["reasons"]["X1"])
        assert "줄 1" in reasons and "여러 개" in reasons and "같은 줄 bed_bare 아님" in reasons


def test_j4_post_rows_not_x5_x7():
    m = v10_meta()
    # post 행은 cooled가 정상이고 층 수에 안 셈: layer_count 빈 칸이어도 X7 아님
    for s in m["scans"]:
        if s[F["timing"]] == "post":
            s[F["layer_count"]] = None
    r = judge_print(layers(), params(), meta=m)
    assert r.verdict == "pass" and r.reject["codes"] == [], r.reject
    # 줄 0 + post 하나 (팀장 재현 3행) → 거부 0
    m = v10_meta(3, 1, post=True)
    assert judge_print(layers(), params(), meta=m).reject["codes"] == []
    # post 행이 마지막 층 layer 행을 대신하지 못함: 층 2 layer 행을 빼면 X5 · X7 그대로
    m = v10_meta()
    m["scans"] = [s for s in m["scans"] if not (s[F["layer_idx"]] == 2 and s[F["timing"]] == "layer")]
    r = judge_print(layers(), params(), meta=m)
    assert r.verdict == "insufficient" and r.reject["codes"] == ["X5", "X7"], r.reject
    # timing = layer인데 cooled인 행은 X5 그대로 (timing 빈 칸도 layer로 봄, J-2 시험 그대로)
    m = v10_meta(post=False)
    _find(m, 1, 0)[F["thermal_state"]] = "cooled"
    assert rejected(m, "X5").reject["codes"] == ["X5"]
    # post 행의 교정 ID가 다르면 X4는 그대로
    m = v10_meta()
    _find(m, 2, 0, "post")[F["calibration_id"]] = "CAL-2026-11-21-B"
    assert rejected(m, "X4").reject["codes"] == ["X4"]


def test_code6_depth_out_of_range():
    assert 6 in EXCLUSION_CODES
    a = np.zeros((4, 4))
    reg = np.ones((4, 4), bool)
    reg[:, 3] = False
    code = np.where(reg, 0, 6).astype(np.int8)
    r = judge_print([layer(a, region=reg, exclusion_code=code)], params())
    assert r.exclusions["by_code"]["심도 밖"] == 4 and r.exclusions["by_code"]["기타"] == 0
    # 묶기: 6과 9가 같은 수면 작은 코드 (6)
    f = np.array([[6, 9], [0, 0]], np.int8)
    assert aggregate_exclusion_code(f, 2).tolist() == [[6]]
