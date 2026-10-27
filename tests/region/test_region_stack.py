"""RG5 종류 · PRIME · RG6 시야 · RG7 비트와 코드 · RG8 비율 · RG9 T15 연결 · RG12 저장."""
import inspect
import os
import tempfile

import numpy as np
import pytest

from cvlab.gcode import GCodeParams, parse_text
from cvlab.judge import JudgeParams, judge_print_fine
from cvlab.judge.aggregate import EXCLUSION_CODES, aggregate_exclusion_code, aggregate_to_cells
from cvlab.judge.verdict import EXCLUSION_NAMES
from cvlab.region import (REASON_BITS, REASON_CODE, RegionParams, RegionStack, build_region, codes_from_bits,
                          coverage_mask, plan_passes)
from cvlab.region.stack import SUMMARY_COLUMNS, region_cells
from region_helpers import aligned_ref, block, built_hand, built_tower, parse_lines

B = REASON_BITS


def _rule(v: int) -> int:
    """§6.2 우선순위를 글 그대로 옮긴 기준 함수."""
    if v & B["no_material"]:
        return 4 if v & B["prime"] else 5
    for name, c in (("type", 4), ("fov", 3), ("depth", 6), ("occlusion", 2), ("edge", 1)):
        if v & B[name]:
            return c
    return 0


def test_region_codes_priority_all_combinations():
    v = np.arange(128, dtype=np.uint8)
    assert codes_from_bits(v).tolist() == [_rule(int(x)) for x in v]
    # R-3: 심도 밖 = judge 코드 6 "심도 밖" (J-2). 코드 9 (기타)는 영역 쪽에서 내지 않음
    assert REASON_CODE["depth"] == 6 and EXCLUSION_NAMES[6] == "심도 밖"
    assert set(REASON_CODE.values()) <= set(EXCLUSION_CODES) and 9 not in codes_from_bits(v).tolist()


def test_region_region_iff_bits0_iff_code0_all_layers():
    for rs in (built_hand("H20_block.gcode")[3], built_tower(50, x1=2.0)[3]):
        for n in range(rs.n_layers):
            reg, code, bits = rs.region(n), rs.exclusion_code(n), rs.reasons(n)
            assert code.dtype == np.int8 and bits.dtype == np.uint8 and reg.dtype == bool
            assert np.array_equal(reg, bits == 0) and np.array_equal(reg, code == 0)
            assert set(np.unique(code).tolist()) <= set(EXCLUSION_CODES)


def test_region_no_material_code5_and_material_only_bits():
    r, g, ref, rs = built_tower(10)
    n = 9
    nomat = np.isnan(ref.height_at_layer(n))
    bits = rs.reasons(n)
    assert np.array_equal((bits & B["no_material"]) > 0, nomat)
    assert (rs.exclusion_code(n)[nomat] == 5).all()
    other = B["edge"] | B["occlusion"] | B["fov"] | B["type"] | B["depth"]
    assert not (bits[nomat] & other).any()


def _skirt_brim_ironing():
    L = ["G21", "G90", "M83", ";TYPE:Skirt", "G0 X0 Y-0.6 Z0.2", "G1 X10 Y-0.6 E0.5"]
    L += block(0, 10, 0, 10, 0.2, type_name="Brim")
    L += block(2, 8, 2, 8, 0.4, type_name="Outer wall")
    L += block(3, 7, 3, 7, 0.4, type_name="Ironing")
    return parse_lines(L)


def test_region_type_exclusion_skirt_brim_and_object_on_brim():
    r = _skirt_brim_ironing()
    g, ref = aligned_ref(r)
    rs = build_region(r, ref)
    assert set(ref.type_names) >= {"SKIRT", "BRIM", "WALL-OUTER", "IRONING"}
    tb = (rs.reasons(1) & B["type"]) > 0
    xs = g["x0_mm"] + np.arange(g["nx"]) * g["res_mm"]
    ys = g["y0_mm"] + np.arange(g["ny"]) * g["res_mm"]
    X, Y = np.meshgrid(xs, ys)
    # 선 끝 반원 사이 (x 2.0–2.2 · 7.8–8.0)는 발자국 틈으로 아래 브림이 보임 (T4a 캡슐 정의). 그 안쪽만 봄
    inside = (X > 2.21) & (X < 7.79) & (Y > 2.05) & (Y < 7.95)
    ring = ((X < 1.95) | (X > 8.05) | (Y < 1.95) | (Y > 8.05)) & ~np.isnan(ref.height_at_layer(1))
    assert not tb[inside].any()          # 브림 위에 올라온 물체는 물체 칸
    assert tb[ring].all()                # 꼭대기가 브림 · 스커트인 칸은 type
    assert (rs.exclusion_code(1)[ring] == 4).all()


def test_region_ironing_included():
    r = _skirt_brim_ironing()
    g, ref = aligned_ref(r)
    rs = build_region(r, ref, RegionParams(edge_band_mm=0.05))
    xs = g["x0_mm"] + np.arange(g["nx"]) * g["res_mm"]
    ys = g["y0_mm"] + np.arange(g["ny"]) * g["res_mm"]
    ix, iy = int(np.argmin(abs(xs - 5.0))), int(np.argmin(abs(ys - 5.0)))
    assert ref.type_names[ref.type_at(1)[iy, ix]] == "IRONING"
    assert rs.region(1)[iy, ix]


def test_region_prime_painted_code4():
    text = "\n".join(["G21", "G90", "M83", "G0 X0 Y-0.6 Z0.2", "G1 X10 Y-0.6 E0.5", ";LAYER:0"]
                     + block(0, 10, 0, 10, 0.2) + [";LAYER:1"] + block(0, 10, 0, 10, 0.4))
    r = parse_text(text, GCodeParams(line_width_mm=0.4))
    assert (r.segments.type == "PRIME").sum() == 1
    g, ref = aligned_ref(r)
    rs = build_region(r, ref)
    assert rs.info["prime"]["n_segments_in_grid"] == 1 and rs.info["prime"]["n_cells"] > 0
    for n in range(rs.n_layers):
        bits = rs.reasons(n)
        pr = (bits & B["prime"]) > 0
        assert pr.sum() == rs.info["prime"]["n_cells"]
        assert ((bits[pr] & B["no_material"]) > 0).all() and (rs.exclusion_code(n)[pr] == 4).all()
    s = rs.summary()
    assert (s.bit_prime[s.layer_idx >= 0] == rs.info["prime"]["n_cells"]).all()


def test_region_plan_passes_counts_and_layout():
    P = lambda W, H, **kw: plan_passes((0.0, W, 0.0, H), **kw)
    # n = max(1, ⌈(W − 2) ÷ 18⌉): 한 패스가 20 mm, 둘이 38 mm, 셋이 56 mm까지
    assert len(P(20.0, 40.0)) == 1 and len(P(0.0, 0.0)) == 1
    assert len(P(20.01, 40.0)) == 2 and len(P(38.0, 40.0)) == 2 and len(P(38.01, 40.0)) == 3
    assert len(P(20.0, 40.01)) == 2 and len(P(20.0, 78.0)) == 2 and len(P(20.0, 78.01)) == 3
    assert len(P(20.0, 200.0, extend_scan_len=True)) == 1
    ps = P(30.0, 10.0)
    assert [p["scan_pass_idx"] for p in ps] == [0, 1] and ps[0]["x1_mm"] - ps[1]["x0_mm"] == pytest.approx(2.0)
    assert (ps[0]["x0_mm"] + ps[1]["x1_mm"]) / 2 == pytest.approx(15.0)       # 가운데 맞춤
    assert ps[0]["x1_mm"] - ps[0]["x0_mm"] == pytest.approx(20.0)
    assert (ps[0]["y0_mm"] + ps[0]["y1_mm"]) / 2 == pytest.approx(5.0) and ps[0]["y1_mm"] - ps[0]["y0_mm"] == 40.0
    e = P(18.0, 70.0, extend_scan_len=True)[0]
    assert (e["y0_mm"], e["y1_mm"]) == (0.0, 70.0)


def test_region_fov_forced_single_pass():
    """30 mm 폭 블록에 패스 하나 (x_c = 15)를 강제하면 |x − 15| > 10 칸이 모두 시야 밖."""
    r = parse_lines(["G21", "G90", "M83"] + block(0, 30, 0, 10, 0.2))
    g, ref = aligned_ref(r)
    one = [{"x0_mm": 5.0, "x1_mm": 25.0, "y0_mm": -15.0, "y1_mm": 25.0}]
    rs = build_region(r, ref, passes=one)
    xs = g["x0_mm"] + np.arange(g["nx"]) * g["res_mm"]
    mat = ~np.isnan(ref.height_at_layer(0))
    fov = (rs.reasons(0) & B["fov"]) > 0
    far = mat & (np.abs(xs - 15.0) > 10.0 + 1e-9)[None, :]
    assert fov[far].all() and not fov[mat & ~far].any()
    assert (rs.exclusion_code(0)[far] == 3).all()
    # 기본 패스 계획 (폭 30 → 2개)이면 시야 밖 없음
    rs2 = build_region(r, ref)
    assert rs2.info["passes_xy"] == [2, 1] and not ((rs2.reasons(0) & B["fov"]) > 0).any()
    assert coverage_mask(g, rs2.passes)[mat].all()


def test_region_summary_columns_and_totals():
    rs = built_tower(50, x1=2.0)[3]
    s = rs.summary()
    assert list(s.columns) == SUMMARY_COLUMNS
    assert len(s) == rs.n_layers + 1 and s.layer_idx.iloc[-1] == -1
    body, tot = s[s.layer_idx >= 0], s.iloc[-1]
    for c in SUMMARY_COLUMNS[2:]:
        if c != "region_pct":
            assert tot[c] == body[c].sum()
    assert tot.region_pct == pytest.approx(100.0 * tot.n_region / tot.n_material)
    cells = rs.grid["nx"] * rs.grid["ny"]
    codes = body[[f"code_{c}" for c in (1, 2, 3, 4, 5, 6)]].sum(axis=1) + body.n_region
    assert (codes == cells).all()                                  # 주 코드는 겹치지 않음
    assert "code_9" not in s.columns and tot.code_6 > 0            # R-3 (합성 탑 50층은 심도 밖 있음)
    assert (body.n_region + body.code_1 + body.code_2 + body.code_3 + body.code_6
            + body.bit_type <= body.n_material).all()


def test_region_cells_equal_t15_aggregate():
    rs = built_tower(50, x1=2.0)[3]
    for n in (0, 20, 49):
        reg = rs.region(n)
        for f in (10, 20):
            _, _, rc = aggregate_to_cells(np.zeros(reg.shape), None, reg, f, region_fill_min=1.0)
            assert region_cells(reg, f, 1.0) == int(rc.sum())
            _, _, rc5 = aggregate_to_cells(np.zeros(reg.shape), None, reg, f, region_fill_min=0.5)
            assert region_cells(reg, f, 0.5) == int(rc5.sum())


def test_region_type_incremental_equals_type_at():
    """build_region의 층별 종류 (덮어쓰기)는 공개 type_at과 같음: _type_codes를 숨긴 판과 결과 비교."""
    r = _skirt_brim_ironing()
    g, ref = aligned_ref(r)

    class Public:
        def __init__(self, ref):
            self.grid, self.z_layers, self.type_names = ref.grid, ref.z_layers, ref.type_names
            self.n_layers, self.footprint, self.type_at = ref.n_layers, ref.footprint, ref.type_at

    a, b = build_region(r, ref), build_region(r, Public(ref))
    for n in range(a.n_layers):
        assert np.array_equal(a.reasons(n), b.reasons(n))


def test_region_build_signature_has_no_measurement():
    names = list(inspect.signature(build_region).parameters)
    assert names == ["result", "ref", "params", "passes"]


def test_region_t15_link_pass_and_counts():
    r, g, ref, rs = built_tower(10)
    Ls = [rs.layer_input(k, np.where(rs.region(k), 0.0, np.nan)) for k in range(rs.n_layers)]
    post = rs.post_input(np.where(rs.region(rs.n_layers - 1), 0.0, np.nan))
    jp = JudgeParams(T_mm=0.2, U_mm=0.0209, U_source="T4b 시험")
    out = judge_print_fine(Ls, jp, res_mm=g["res_mm"], post=post)
    assert out["primary"].verdict == "pass" and out["alt"].verdict == "pass"
    s = rs.summary()
    assert out["primary"].counts["n_region"] == s.n_region_cell02.iloc[-1]
    assert out["alt"].counts["n_region"] == s.n_region_cell04.iloc[-1]
    # 뺀 이유별 칸 수 = 고운 코드를 판정 칸으로 묶은 값 (T15 aggregate_exclusion_code 규칙)
    by = {name: 0 for name in EXCLUSION_NAMES.values()}
    for k in range(rs.n_layers):
        reg = rs.region(k)
        _, _, rc = aggregate_to_cells(np.zeros(reg.shape), None, reg, 10, region_fill_min=1.0)
        code = aggregate_exclusion_code(rs.exclusion_code(k), 10)
        for c, name in EXCLUSION_NAMES.items():
            by[name] += int(((code == c) & ~rc).sum())
    got = dict(out["primary"].exclusions["by_code"])
    assert got.pop("이유 없음") == 0 and got == by
    assert out["primary"].cooled is not None and out["primary"].cooled["layer_idx"] == rs.n_layers - 1


def test_region_depth_code6_reaches_judge():
    """R-3: 심도 밖 칸이 judge by_code "심도 밖"으로 들어가고 "기타"는 0 (합성 탑 50층, x1 = 2)."""
    r, g, ref, rs = built_tower(50, x1=2.0)
    Ls = [rs.layer_input(k, np.where(rs.region(k), 0.0, np.nan)) for k in range(rs.n_layers)]
    jp = JudgeParams(T_mm=0.2, U_mm=0.0209, U_source="T4b 시험")
    by = judge_print_fine(Ls, jp, res_mm=g["res_mm"])["primary"].exclusions["by_code"]
    assert by["심도 밖"] > 0 and by["기타"] == 0 and by["이유 없음"] == 0


def _post_parts(rs):
    n = rs.n_layers - 1
    return n, rs.reasons(n), rs.post_reasons(), rs.post_region(), rs.region(n)


def test_region_post_region_rules():
    """R-2: post 영역 = 마지막 층 출력물 칸에서 type · fov · depth · occlusion · 출력물 없음은 그대로 빼고,
    엣지는 좁은 띠 (자동 max(2·res, α·반폭·ΔT))만 뺌. 판정 영역 (region)은 바뀌지 않음."""
    for rs in (built_tower(10)[3], built_tower(50, x1=2.0)[3], built_hand("H20_block.gcode")[3]):
        n, bits, pb, pr, reg = _post_parts(rs)
        keep = B["type"] | B["fov"] | B["depth"] | B["occlusion"] | B["no_material"] | B["prime"]
        assert np.array_equal(pb & keep, bits & keep)                 # 엣지 밖 이유는 그대로
        assert not (pb & ~bits & B["edge"]).any()                     # 좁은 띠 ⊂ 원래 띠
        assert (pr | ~reg).all() and pr.sum() > reg.sum()             # post ⊇ 판정 영역, 더 넓음
        assert np.array_equal(pr, pb == 0)
        assert np.array_equal(rs.post_exclusion_code() == 0, pr)
        assert set(np.unique(rs.post_exclusion_code()).tolist()) <= set(EXCLUSION_CODES)
        assert rs.info["post_rule"] == "P-B 좁은 엣지 띠" and rs.info["post_n_region"] == int(pr.sum())
        assert rs.info["post_band_mm"] == pytest.approx(0.04)          # 작은 물체: 2·res가 이김
        assert rs.info["post_region_cell02"] == region_cells(pr, 10, 1.0)
        assert np.array_equal(reg, rs.reasons(n) == 0)                # 판정 영역은 그대로


def test_region_post_band_auto_and_fallback():
    from cvlab.region.stack import post_band_auto
    p = RegionParams()
    # caliper 경계 상자 긴 변 42.451 mm → 68e-6 × 21.2255 × 30 = 0.0433 mm (팀장검증 5차 §3.4)
    assert post_band_auto(p, (114.371, 135.629, 83.871, 126.322), 0.02) == pytest.approx(0.0433, abs=1e-4)
    assert post_band_auto(p, (0.0, 10.0, 0.0, 10.0), 0.02) == pytest.approx(0.04)
    # 좁은 띠도 영역을 다 덮을 만큼 넓으면 엣지 포함 (P-A)으로 넘어가고 규칙 이름을 남김
    r, g, ref, _ = built_tower(10)
    wide = build_region(r, ref, RegionParams(post_edge_band_mm=50.0))
    n, bits, pb, pr, reg = _post_parts(wide)
    assert wide.info["post_rule"] == "P-A 엣지 포함" and pr.sum() > 0
    assert not (pb & B["edge"]).any() and np.array_equal(pr, (bits & ~np.uint8(B["edge"])) == 0)


def test_region_post_input_uses_post_region():
    r, g, ref, rs = built_tower(10)
    n = rs.n_layers - 1
    d = np.zeros((g["ny"], g["nx"]))
    P = rs.post_input(d)
    assert P.layer_idx == n and P.thermal_state == "cooled"
    assert np.array_equal(P.region, rs.post_region()) and np.array_equal(P.exclusion_code, rs.post_exclusion_code())
    L = rs.layer_input(n, d)
    assert np.array_equal(L.region, rs.region(n))                     # 진행 중 층은 판정 영역 그대로
    # judge 연결: post가 받아들여지고 판정은 바뀌지 않음
    Ls = [rs.layer_input(k, np.where(rs.region(k), 0.0, np.nan)) for k in range(rs.n_layers)]
    jp = JudgeParams(T_mm=0.2, U_mm=0.0209, U_source="T4b 시험")
    a = judge_print_fine(Ls, jp, res_mm=g["res_mm"])
    b = judge_print_fine(Ls, jp, res_mm=g["res_mm"], post=rs.post_input(np.where(rs.post_region(), 0.0, np.nan)))
    assert a["primary"].verdict == b["primary"].verdict == "pass"
    assert a["primary"].counts == b["primary"].counts


def test_region_layer_input_checks():
    rs = built_tower(10)[3]
    with pytest.raises(ValueError):
        rs.layer_input(0, np.zeros((3, 3)))
    with pytest.raises(ValueError):
        rs.layer_input(0, np.zeros((rs.grid["ny"], rs.grid["nx"])), thermal_state="cooled")
    L = rs.layer_input(3, np.zeros((rs.grid["ny"], rs.grid["nx"])))
    assert L.layer_idx == 3 and L.thermal_state == "in_process" and np.array_equal(L.region, rs.region(3))


def test_region_save_load_and_repeat():
    r, g, ref, rs = built_tower(12)
    p = os.path.join(tempfile.mkdtemp(), "region.npz")
    rs.save(p)
    back = RegionStack.load(p)
    assert back.grid == rs.grid and back.n_layers == rs.n_layers and back.passes == rs.passes
    assert back.params.to_dict() == rs.params.to_dict()
    for n in range(rs.n_layers):
        assert np.array_equal(back.reasons(n), rs.reasons(n))
        assert np.array_equal(back.region(n), rs.region(n))
        assert np.array_equal(back.exclusion_code(n), rs.exclusion_code(n))
    assert back.summary().equals(rs.summary())
    assert np.array_equal(back.post_reasons(), rs.post_reasons()) and back.info == rs.info
    again = build_region(r, ref)
    for n in range(rs.n_layers):
        assert np.array_equal(again.reasons(n), rs.reasons(n))


def test_region_final_top_coverage():
    """A안 (심도 밖은 뺌) 최종 윗면 덮임률 100 %. dof_top < 0이면 지금 윗면이 생긴 층에서 창 위로 벗어남.
    바닥 (Z 0.2)은 뒤 층에서 창에 들어와 덮이지만 마지막 층 탑 윗면은 끝내 못 덮여 100 % 아래."""
    r, g, ref, rs = built_tower(50, x1=2.0)
    assert rs.info["coverage_final_top_pct"] == pytest.approx(100.0)
    low = build_region(r, ref, RegionParams(dof_top_mm=-1.0))
    assert 0.0 < low.info["coverage_final_top_pct"] < 100.0


def test_region_depth_plan_columns():
    rs = built_tower(50, x1=2.0)[3]
    t = rs.depth_plan()
    assert list(t.columns) == ["layer_idx", "layer_z_mm", "spread_mm", "n_heights", "depth_pct",
                               "recover_cells_B", "extra_scan_s_B"]
    last = t[t.layer_idx == 49].iloc[0]
    assert last.spread_mm == pytest.approx(9.8) and last.n_heights == 2
    assert last.extra_scan_s_B == pytest.approx(1 * (5.0 + 40.0) / 2.4)  # 패스 1개
    assert t[t.layer_idx == 0].iloc[0].n_heights == 1
    tot = t.iloc[-1]
    assert tot.recover_cells_B == t.recover_cells_B.iloc[:-1].sum()
