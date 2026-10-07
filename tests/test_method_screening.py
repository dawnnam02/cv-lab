"""방법 탐색 시뮬레이션 자기 검증 (청사진 0_방법탐색 6절 완료 기준).

이상 모델(잡음 0, 흐림 0, step = 2 µm)에서 넣은 오차를 ±1 µm 안에서 복원해야 한다.
실행: python -m pytest tests/test_method_screening.py -v
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "method_screening"))

import rules  # noqa: E402
import simulate as sim  # noqa: E402
from specs import to_num  # noqa: E402

TOL = 1.0  # µm
TRUTH = {"단차": sim.STEP_ERR, "선폭": sim.LINE_ERR, "구멍지름": sim.HOLE_ERR, "경계": -sim.HOLE_ERR / 2}


@pytest.fixture(scope="module")
def ideal_3d_runs():
    m = sim.Model(z_sigma=0, xy_step=2, xy_blur=0, edge_loss=0, max_slope=90, measures_z=True)
    _, runs = sim.simulate(m, n_mc=3, seed=11)
    return runs


@pytest.fixture(scope="module")
def ideal_2d_runs():
    m = sim.Model(z_sigma=0, xy_step=2, xy_blur=0, edge_loss=0, max_slope=90, measures_z=False)
    summ, runs = sim.simulate(m, n_mc=6, seed=12)
    return summ, runs


@pytest.mark.parametrize("name", ["단차", "선폭", "구멍지름", "경계"])
def test_이상모델_3D_모든_회차_복원(ideal_3d_runs, name):
    for r in ideal_3d_runs:
        assert r[name] == pytest.approx(TRUTH[name], abs=TOL)


def test_이상모델_3D_위치_복원(ideal_3d_runs):
    for r in ideal_3d_runs:
        assert r["위치"][0] == pytest.approx(sim.POS_ERR[0], abs=TOL)
        assert r["위치"][1] == pytest.approx(sim.POS_ERR[1], abs=TOL)


@pytest.mark.parametrize("name", ["선폭", "구멍지름", "경계"])
def test_이상모델_2D_치우침_복원(ideal_2d_runs, name):
    """2D 는 이진 마스크라 회차마다 양자화(±1칸)가 남는다 → 회차 평균(치우침)이 ±1 µm,
    각 회차는 ±1칸(2 µm) 안."""
    summ, runs = ideal_2d_runs
    assert summ[name]["bias_um"] == pytest.approx(0.0, abs=TOL)
    for r in runs:
        assert r[name] == pytest.approx(TRUTH[name], abs=2.0)


def test_이상모델_2D_위치_복원(ideal_2d_runs):
    summ, runs = ideal_2d_runs
    e = np.array([r["위치"] for r in runs]) - np.array(sim.POS_ERR)
    assert np.abs(e.mean(axis=0)).max() <= TOL


def test_2D는_단차_측정불가(ideal_2d_runs):
    summ, _ = ideal_2d_runs
    assert summ["단차"]["grade"] == "측정 불가"


def test_이상모델_판정은_10대1(ideal_3d_runs):
    m = sim.Model(z_sigma=0, xy_step=2, xy_blur=0, edge_loss=0, max_slope=90, measures_z=True)
    summ, _ = sim.simulate(m, n_mc=3, seed=13)
    for name in ("단차", "선폭", "구멍지름", "위치"):
        assert summ[name]["grade"] == "10:1 통과"


def test_점측정_후보는_오류없이_측정불가():
    """점 간격 5 mm 같은 점 측정을 격자 모델로 돌려도 예외 없이 끝나고, 점 부족 지표는 '측정 불가'."""
    m = sim.Model(z_sigma=2, xy_step=5000, xy_blur=1500, measures_z=True, contact=True)
    summ, _ = sim.simulate(m, n_mc=3, seed=1)
    assert summ["선폭"]["grade"] == "측정 불가"
    assert summ["국소선폭"]["grade"] == "측정 불가"
    assert summ["국소높이"]["grade"] == "측정 불가"
    assert summ["구멍지름"]["grade"] in ("측정 불가", "불합격")   # 점 몇 개로 맞춰지면 큰 오차로 불합격


def test_측정깊이_초과_패치는_측정불가():
    m = sim.Model(z_sigma=0.1, xy_step=20, xy_blur=2, measures_z=True, contact=True, depth=500)
    summ, _ = sim.simulate(m, n_mc=2, seed=1)
    assert summ["구멍지름"]["grade"] == "측정 불가"     # 판 두께 1000 µm > 500 µm
    assert summ["단차"]["grade"] != "측정 불가"          # 단차 패치 400 µm ≤ 500 µm


def test_판정등급_경계값():
    assert sim.grade(2.0, 5, 2) == "10:1 통과"
    assert sim.grade(5.0, 5, 2) == "4:1 통과"
    assert sim.grade(5.1, 5, 2) == "불합격"
    assert sim.grade(np.nan, 5, 2) == "측정 불가"


def test_안전_규칙():
    assert rules.safety_hit("Class 2 (IEC 60825-1:2014)") is None
    assert rules.safety_hit("Class 3B") == "3B"
    assert rules.safety_hit("레이저 Class 4") == "Class 4"
    assert rules.safety_hit("Class 1, 4 mW") is None
    assert rules.safety_hit("4 mW 다이오드") is None
    assert rules.safety_hit("X-ray CT") == "X선"
    assert rules.safety_hit("class IIIb") == "3B"
    assert rules.safety_hit("X선 허가 필요") == "X선"
    r = {"access": "own", "cost_krw": 1e6, "safety": "X선", "xy_step_um": 50, "fov_mm": 100}
    assert rules.judge_row(r)["pass_safety"] == "탈락"
    r["access"] = "outsource"
    r["cost_krw"] = 2e5
    out = rules.judge_row(r)
    assert out["pass_safety"] == "통과" and out["pass_budget"] == "통과"


def test_숫자_읽기():
    assert np.isnan(to_num("NA"))
    assert to_num("5,000,000") == 5e6
    assert to_num("500만 원") == 5e6
    assert to_num("~10 µm") == 10


# ---------------------------------------------------------------- 새 지표 (국소높이·국소선폭·길이40)
def test_이상모델_국소높이_모든_셀_복원(ideal_3d_runs):
    for r in ideal_3d_runs:
        cells = np.asarray(r["국소높이"])
        assert cells.size == 100
        assert np.abs(cells).max() <= TOL


def test_이상모델_국소선폭_모든_구간_복원(ideal_3d_runs):
    for r in ideal_3d_runs:
        seg = np.asarray(r["국소선폭"])
        assert seg.size == 18
        assert np.abs(seg - sim.LINE_ERR).max() <= TOL


def test_이상모델_길이40_복원():
    """이상 모델(u_s 0, seam 없음): 치우침 0, 2σ 는 경계 양자화 2개뿐(2·√2·2/√12 = 1.63 µm)."""
    m = sim.Model(z_sigma=0, xy_step=2, xy_blur=0, measures_z=True, u_s=0.0, fov=np.inf)
    summ, _ = sim.simulate(m, n_mc=2, seed=3, cons=True)
    assert summ["길이40"]["bias_um"] == pytest.approx(0.0, abs=TOL)
    assert summ["길이40"]["sd2_um"] == pytest.approx(2 * np.sqrt(2) * 2 / np.sqrt(12), abs=1e-9)
    assert summ["길이40"]["grade"] == "10:1 통과"


def test_이상모델_보수시나리오도_복원():
    """보수 시나리오라도 잡음 0, u_s 0, seam 없음이면 새 지표 3개가 ±1 µm."""
    m = sim.Model(z_sigma=0, xy_step=2, xy_blur=0, measures_z=True, u_s=0.0, fov=np.inf)
    summ, runs = sim.simulate(m, n_mc=2, seed=4, cons=True)
    for r in runs:
        assert np.abs(np.asarray(r["국소높이"])).max() <= TOL
        assert np.abs(np.asarray(r["국소선폭"]) - sim.LINE_ERR).max() <= TOL
    for name in ("국소높이", "국소선폭"):
        assert summ[name]["Q_um"] <= TOL


def test_보수_상관잡음_분산_유지():
    """상관 성분의 표준편차가 지정값(z/√2)과 맞는지."""
    rng = np.random.default_rng(0)
    vals = []
    for _ in range(40):
        F = sim.CorrField(rng, 0, 5000, 0, 5000, 3.0)
        vals.append(F(np.array([2500.0]), np.array([2500.0]))[0])
    assert np.std(vals) == pytest.approx(3.0, rel=0.3)


def test_seam_수():
    assert sim.Model(fov=19900).n_seams == 2
    assert sim.Model(fov=50000).n_seams == 0
    assert sim.Model(fov=2800).n_seams == 14


def test_점측정_해석판정():
    m = sim.Model(z_sigma=1.5, xy_step=1000, xy_blur=500, measures_z=True, contact=True,
                  u_s=20e-6, point=True)
    summ, _ = sim.simulate(m, cons=True)
    assert summ["국소높이"]["grade"] == "측정 불가"        # xy_step ≥ 200 µm
    assert summ["국소선폭"]["grade"] == "측정 불가"        # 볼 지름 1 mm > 0.4 mm
    assert summ["구멍지름"]["sd2_um"] == pytest.approx(2 * np.hypot(1.5 * 0.5, 4000 * 20e-6))
    assert summ["구멍지름"]["note"] == "해석 판정"


# ---------------------------------------------------------------- 팀장 결정 반영 (래스터·배율·선 단면 장비)
def _row(rid, **kw):
    base = {"id": rid, "z_sigma_um": 2.0, "xy_step_um": 40.0, "xy_blur_um": 45.0, "fov_mm": 0.05,
            "depth_mm": 10.0, "measures_z": 1.0, "edge_loss_um": 0.0, "max_slope_deg": 60.0,
            "access": "own", "contact": False}
    base.update(kw)
    return base


def test_래스터_점센서는_seam_0_축잡음_5um():
    m, _ = sim.model_from_row(_row("M07"))
    assert m.raster and m.n_seams == 0
    assert m.u_s == pytest.approx(500e-6) and m.cal_class == "printer_axis"
    ctx = sim.make_ctx(m, np.random.default_rng(0), True)
    assert ctx.jit == pytest.approx(5.0)
    assert sim.make_ctx(m, np.random.default_rng(0), False).jit == 0.0


def test_M18은_seam_유지_배율_printer_axis():
    m, _ = sim.model_from_row(_row("M18", fov_mm=1.35, xy_step_um=1.1))
    assert not m.raster and m.n_seams == 29
    assert m.cal_class == "printer_axis" and m.u_s == pytest.approx(500e-6)


def test_M04_교정계측기_20ppm():
    m, _ = sim.model_from_row(_row("M04", xy_step_um=5000, fov_mm=150))
    assert m.u_s == pytest.approx(20e-6)


def test_diy_배율_민감도():
    m5, _ = sim.model_from_row(_row("M05", fov_mm=19.9))
    m1, _ = sim.model_from_row(_row("M05", fov_mm=19.9), diy_ppm=100)
    assert m5.u_s == pytest.approx(500e-6) and m1.u_s == pytest.approx(100e-6)


def test_선단면장비_면래스터_시간():
    import scoring
    t = scoring.raster_time_min({"id": "M02", "xy_step_um": 1.0})
    assert t == pytest.approx(20000 * (400 + 20) / 60)
    assert np.isnan(scoring.raster_time_min({"id": "M05", "xy_step_um": 20.0}))


# ---------------------------------------------------------------- 2차 후보 확장 (mode·cal_class·실현성·병렬·입력)
def test_mode열_대응():
    m, _ = sim.model_from_row(_row("M200", mode="raster_point"))
    assert m.raster and m.n_seams == 0 and m.xy_jitter == pytest.approx(5.0)
    m, nt = sim.model_from_row(_row("M201", mode="point_probe", xy_step_um=1000))
    assert m.point and "해석 판정" in nt
    m, nt = sim.model_from_row(_row("M202", mode="2d", measures_z=1.0))
    assert not m.measures_z and m.z_sigma == 0.0
    m, _ = sim.model_from_row(_row("M203", mode="area", fov_mm=19.9))
    assert not m.raster and not m.point and m.n_seams == 2
    # mode 열이 비면 1차 id 목록 상수
    assert sim.resolve_mode(_row("M07", mode="")) == ("raster_point", "id목록")
    assert sim.resolve_mode(_row("M01")) == ("point_probe", "id목록")
    assert sim.resolve_mode(_row("M02")) == ("line_profiler", "id목록")
    assert sim.resolve_mode(_row("M20", measures_z=0.0)) == ("2d", "id목록")
    assert sim.resolve_mode(_row("M07", mode="area")) == ("area", "csv")    # 열 값이 우선
    # cal_class 열이 id 목록보다 우선, 없으면 id 목록
    m, _ = sim.model_from_row(_row("M05", cal_class="calibrated"))
    assert m.u_s == pytest.approx(20e-6) and m.cal_class == "calibrated"
    m, _ = sim.model_from_row(_row("M300", cal_class="industrial"))
    assert m.u_s == pytest.approx(100e-6)
    m1, _ = sim.model_from_row(_row("M300", cal_class="diy"), diy_ppm=100)
    assert m1.u_s == pytest.approx(100e-6)


def test_line_profiler_면래스터_시간_기본값과_CSV값():
    import scoring
    t_def = scoring.raster_time_min({"id": "M226", "mode": "line_profiler", "xy_step_um": 10.0})
    assert t_def == pytest.approx(2000 * (400 + 20) / 60)                  # M02 기본값 100 µm/s, 20 s
    t_csv = scoring.raster_time_min({"id": "M226", "mode": "line_profiler", "xy_step_um": 10.0,
                                     "scan_speed_um_s": 1000.0, "line_overhead_s": 5.0})
    assert t_csv == pytest.approx(2000 * (40 + 5) / 60)
    assert np.isnan(scoring.raster_time_min({"id": "M02", "mode": "area", "xy_step_um": 1.0}))


def test_indirect_건너뛰기():
    import screen
    m, nt = sim.model_from_row(_row("M117", mode="indirect"))
    assert m is None and any("간접 지표" in x for x in nt)
    res = screen.run_candidate((_row("M117", mode="indirect"), 5, 0))
    assert res["mode"] == "indirect"
    assert any("간접 지표" in x for x in res["notes"])
    for sc in (screen.SC_OPT, screen.SC_C500, screen.SC_C100):
        assert all(v["grade"] == "측정 불가" for v in res["sims"][sc].values())
    assert res["sec"] < 2.0                                                  # 시뮬레이션을 돌리지 않음


def test_pass_feasible():
    base = {"access": "lab", "cost_krw": 5e4, "safety": "없음", "xy_step_um": 1.0, "fov_mm": 55}
    assert rules.judge_row(dict(base, id="M900", time_min=480))["pass_feasible"] == "통과"
    assert rules.judge_row(dict(base, id="M900", time_min=481))["pass_feasible"] == "탈락"
    assert rules.judge_row(dict(base, id="M900", time_min=np.nan))["pass_feasible"] == "확인필요"
    # 선 단면 장비: CSV 시간(60분)이 아니라 면 래스터 시간(약 140,000분)으로 판정
    out = rules.judge_row(dict(base, id="M02", time_min=60))
    assert out["pass_feasible"] == "탈락" and out["time_min_feasible"] == pytest.approx(140000)
    out = rules.judge_row(dict(base, id="M926", mode="line_profiler", time_min=60))
    assert out["pass_feasible"] == "탈락"
    import pandas as pd
    df = pd.DataFrame([dict(base, id="M900", name="a", time_min=30), dict(base, id="M02", name="b", time_min=60)])
    rt = rules.judge(df).set_index("id")
    assert bool(rt.loc["M900", "rule_ok"]) and not bool(rt.loc["M02", "rule_ok"])


def test_병렬_순차_결과_일치():
    import pandas as pd
    import screen
    rows = [_row("M501", xy_step_um=60.0, xy_blur_um=60.0, fov_mm=100.0, z_sigma_um=3.0),
            _row("M502", xy_step_um=80.0, xy_blur_um=80.0, fov_mm=10.0, measures_z=0.0, z_sigma_um=np.nan),
            _row("M503", mode="indirect")]
    df = pd.DataFrame(rows)
    quiet = lambda *a, **k: None   # noqa: E731
    s1, n1, _ = screen.run_sims(df, 2, 7, log=quiet, workers=1)
    s2, n2, _ = screen.run_sims(df, 2, 7, log=quiet, workers=2)
    for sc in s1:
        for rid in df["id"]:
            for t, v in s1[sc][rid].items():
                w = s2[sc][rid][t]
                assert v["grade"] == w["grade"]
                for k in ("Q_um", "bias_um", "sd2_um"):
                    assert (np.isnan(v[k]) and np.isnan(w[k])) or v[k] == w[k]
    assert n1 == n2
    # 시드는 행 순서와 무관 (id 로 정함)
    s3, _, _ = screen.run_sims(df.iloc[::-1].reset_index(drop=True), 2, 7, log=quiet, workers=1)
    assert s3[screen.SC_C500]["M501"]["국소높이"]["Q_um"] == s1[screen.SC_C500]["M501"]["국소높이"]["Q_um"]


def test_범위_추정_숫자_읽기():
    assert to_num("5~10") == 10
    assert to_num("5-10") == 10
    assert to_num("5 ~ 10 µm") == 10
    assert to_num("5 µm ~ 10 µm") == 10
    assert to_num("5–10") == 10
    assert to_num("5~10", prefer="min") == 5
    assert to_num("추정 5") == 5
    assert to_num("5(추정)") == 5
    assert to_num("약 3~4만 원") == 40000
    assert to_num("300만~500만") == 5e6
    assert to_num("-5") == -5
    assert to_num("1e-3") == pytest.approx(1e-3)
    assert np.isnan(to_num("추정"))


def test_사양_CSV_열차이_건너뛰기_중복(tmp_path):
    from specs import load_specs
    a = tmp_path / "후보-사양_A.csv"
    a.write_text("id,name,z_sigma_um,xy_step_um,max_slope_deg,access\n"
                 "M01,하나,1.5,1000,60~80,lab\n", encoding="utf-8")
    e = tmp_path / "후보-사양_E1.csv"
    e.write_text("id,name,z_sigma_um,xy_step_um,mode,cal_class,access\n"
                 "M24,둘,추정 2~3,10,area,industrial,own\n"
                 "M25,셋,1,10,area,diy,own,남는칸\n"
                 "M26,넷,1,10,면,diy,own\n"
                 "M27,다섯,1,10,,,own\n", encoding="utf-8")
    with pytest.warns(UserWarning):
        df = load_specs([str(a), str(e)])
    assert list(df["id"]) == ["M01", "M24", "M27"]
    skipped = {i for i, _, _ in df.attrs["skipped"]}
    assert skipped == {"M25", "M26"}
    r = df.set_index("id")
    assert r.loc["M24", "z_sigma_um"] == 3 and r.loc["M01", "max_slope_deg"] == 60   # 범위: 보수적인 쪽
    assert r.loc["M01", "mode"] == "" and r.loc["M24", "cal_class"] == "industrial"
    assert np.isnan(r.loc["M01", "fov_mm"])                                       # 없는 열은 NaN
    d = tmp_path / "후보-사양_E2.csv"
    d.write_text("id,name\nM24,중복\n", encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        load_specs([str(a), str(e), str(d)])
