"""J-3 (팀장검증 5차): 식힌 재측정 비교 영역 = post 영역. 판정은 그대로 (D-06).

지도 값은 시험용 입력이며 측정값이 아니다.
"""
import os
import sys

import numpy as np
import pytest

from cvlab.judge import LayerInput, judge_print, judge_print_fine
from judge_maps import layer, params


def _two_layers(last_region):
    """층 0: 전부 판정 영역 (Δ 0). 층 1: 마지막 층, 판정 영역은 last_region, Δ는 전 칸 0.05 (영역 밖도 측정됨)."""
    return [layer(np.zeros((4, 4)), 0), layer(np.full((4, 4), 0.05), 1, region=last_region)]


def test_j3_last_region_zero_post_region_compares():
    # 마지막 층 판정 영역 0칸, post 영역 6칸 → 예전 (last ∩ post)은 None, 이제 6칸 비교
    ls = _two_layers(np.zeros((4, 4), bool))
    pr = np.zeros((4, 4), bool); pr[1:3, 0:3] = True
    post = layer(np.full((4, 4), 0.02), 1, region=pr, state="cooled")
    r = judge_print(ls, params(), post=post, post_rule="P-B 좁은 엣지 띠")
    c = r.cooled
    assert c["status"] == "비교 가능" and c["comparable"] is True
    assert c["n_compare"] == 6 and c["n_post_region"] == 6 and c["n_last_region"] == 0
    assert c["difference"]["n"] == 6
    assert c["difference"]["mean_um"] == pytest.approx(-30.0)
    assert c["post_rule"] == "P-B 좁은 엣지 띠"
    assert not any("비교 불가" in w for w in r.warnings)


def test_j3_verdict_unchanged_by_post_and_cmp():
    # 판정 결과 불변 (D-06): post 유무 · delta_cmp_mm 값과 무관
    pr = np.zeros((4, 4), bool); pr[0, :] = True
    lr = np.ones((4, 4), bool); lr[0, :] = False
    base = _two_layers(lr)
    r0 = judge_print(base, params())
    wild = np.full((4, 4), 9.0)                         # 판정에 쓰이면 불합격이 될 값
    cmp_layers = [base[0], LayerInput(1, "in_process", base[1].delta_mm, lr, delta_cmp_mm=wild)]
    post = layer(np.full((4, 4), 0.02), 1, region=pr, state="cooled")
    r1 = judge_print(cmp_layers, params(), post=post)
    assert r0.verdict == r1.verdict == "pass"
    assert r0.counts == r1.counts and r0.per_layer == r1.per_layer
    assert r0.method_a == r1.method_a and r0.metrics == r1.metrics
    # 비교는 delta_cmp_mm을 씀 (0.02 − 9.0)
    assert r1.cooled["difference"]["mean_um"] == pytest.approx(-8980.0)
    assert r1.cooled["post_rule"] is None


def test_j3_post_region_zero_is_not_comparable():
    ls = _two_layers(np.ones((4, 4), bool))
    post = layer(np.full((4, 4), 0.02), 1, region=np.zeros((4, 4), bool), state="cooled")
    r = judge_print(ls, params(), post=post, post_rule="P-A 엣지 포함")
    c = r.cooled
    assert c["status"] == "비교 불가" and c["comparable"] is False
    assert c["n_compare"] == 0 and c["difference"] is None
    assert c["post_rule"] == "P-A 엣지 포함"
    assert any("비교 불가" in w and "post 영역이 0칸" in w for w in r.warnings)
    assert r.verdict == judge_print(ls, params()).verdict


def test_j3_fine_keeps_measurement_outside_region():
    # 고운 격자: 마지막 층 판정 영역 0칸이어도 영역 밖 측정 Δ를 post 영역으로 묶어 비교 (0.2 mm 칸 4개)
    ny, nx = 20, 40
    l0 = layer(np.zeros((ny, nx)), 0)
    l1 = layer(np.full((ny, nx), 0.05), 1, region=np.zeros((ny, nx), bool))
    pr = np.zeros((ny, nx), bool); pr[0:20, 0:40] = True       # 0.2 mm 칸 2행 × 4열
    post = layer(np.full((ny, nx), 0.02), 1, region=pr, state="cooled")
    out = judge_print_fine([l0, l1], params(), res_mm=0.02, post=post, post_rule="P-B 좁은 엣지 띠")
    base = judge_print_fine([l0, l1], params(), res_mm=0.02)
    c = out["primary"].cooled
    assert c["n_compare"] == 8 and c["status"] == "비교 가능"
    assert c["difference"]["mean_um"] == pytest.approx(-30.0)
    assert out["alt"].cooled["n_compare"] == 2                  # 0.4 mm 칸 1행 × 2열
    for k in ("primary", "alt"):
        assert out[k].verdict == base[k].verdict and out[k].counts == base[k].counts


def test_j3_fine_nan_outside_region_not_comparable():
    # 앞 단계가 영역 밖 Δ를 NaN으로 지우면 비교 칸 0 → 비교 불가 (문서 §17: 측정값은 영역 밖에도 남길 것)
    ny, nx = 20, 40
    reg = np.zeros((ny, nx), bool); reg[10:, :] = True
    a = np.where(reg, 0.05, np.nan)
    l1 = layer(a, 0, region=reg)
    pr = ~reg
    post = layer(np.full((ny, nx), 0.02), 0, region=pr, state="cooled")
    c = judge_print_fine([l1], params(), res_mm=0.02, post=post)["primary"].cooled
    assert c["status"] == "비교 불가" and c["n_compare"] == 0 and c["n_post_region"] == 4


# ---- caliper (D-19, _local 파일이 있을 때만)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "region"))
from region_helpers import CALIPER  # noqa: E402


@pytest.mark.skipif(not os.path.exists(CALIPER), reason="_local/ D-19 파일 없음")
def test_j3_caliper_last_layer_compares():
    from region_helpers import built_local
    r, g, ref, rs = built_local(CALIPER)
    n = rs.n_layers - 1
    assert int(rs.region(n).sum()) == 0
    shape = (rs.grid["ny"], rs.grid["nx"])
    last = rs.layer_input(n, np.zeros(shape))                     # 시험용 Δ (측정값 아님)
    post = rs.post_input(np.full(shape, -0.005))
    out = judge_print_fine([last], params(), res_mm=rs.grid["res_mm"], post=post,
                           post_rule=rs.info["post_rule"])
    base = judge_print_fine([last], params(), res_mm=rs.grid["res_mm"])
    c = out["primary"].cooled
    assert c["difference"] is not None and c["n_compare"] > 0
    assert c["n_compare"] == rs.info["post_region_cell02"]
    assert out["alt"].cooled["n_compare"] == rs.info["post_region_cell04"]
    assert c["post_rule"] == rs.info["post_rule"]
    assert c["difference"]["mean_um"] == pytest.approx(-5.0)
    for k in ("primary", "alt"):
        assert out[k].verdict == base[k].verdict and out[k].counts == base[k].counts
