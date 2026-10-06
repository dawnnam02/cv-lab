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
    """점 간격 5 mm 같은 점 측정: 선폭·구멍 점 부족 → 예외 없이 '측정 불가'."""
    m = sim.Model(z_sigma=2, xy_step=5000, xy_blur=1500, measures_z=True, contact=True)
    summ, _ = sim.simulate(m, n_mc=3, seed=1)
    assert summ["선폭"]["grade"] == "측정 불가"
    assert summ["구멍지름"]["grade"] == "측정 불가"


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
    assert rules.safety_hit("레이저 Class 4") == "4"
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
