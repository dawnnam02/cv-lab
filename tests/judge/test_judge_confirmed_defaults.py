"""D-20 (2026-10-27) 확정 규칙 R1–R7과 코드·설정 기본값이 같은지 확인한다.

규칙 문서: docs/판정-규칙.md §14. U 기본값은 코드에 두지 않는다 (MF-JDG-01, D-15 참고값은 문서에만).
"""
import inspect
from pathlib import Path

import numpy as np

from cvlab.judge import JudgeParams, cooling_criterion, judge_print, load_params
from judge_maps import layer, params

ROOT = Path(__file__).resolve().parents[2]

# D-20 확정값 (R1–R7)
CONFIRMED = {
    "cell_mm": 0.2,                 # R1 주 판정 칸
    "cell_mm_alt": 0.4,             # R1 함께 보고
    "valid_min_pct": 90,            # R2 측정 불충분 문턱
    "outlier_primary": "worse",     # R3 덜 유리한 쪽이 주 판정
    "cooled_delta_max_um": 5.0,     # R4 δ_max
    "cooled_alpha_um_per_m_c": 68.0,  # R4 α
    "region_fill_min": 1.0,         # R6 묶음 전부가 영역
    "cell_fill_min": 0.5,           # R6 채움 ≥ 50 %
    "cell_stat": "mean",            # R6 칸 값은 평균
    "layer_fail_warn_pct": 50,      # R7 층 경고 문턱
}


def test_code_and_config_defaults_match_d20():
    code = JudgeParams()
    cfg = load_params(ROOT / "config" / "judge.yaml")
    for key, want in CONFIRMED.items():
        assert getattr(code, key) == want, f"코드 기본값 {key}"
        assert getattr(cfg, key) == want, f"config/judge.yaml {key}"
    # cooling_criterion 함수 기본 인자도 R4와 같아야 함
    sig = inspect.signature(cooling_criterion)
    assert sig.parameters["alpha_um_per_m_c"].default == 68.0
    assert sig.parameters["delta_max_um"].default == 5.0
    # D-15: U는 코드·설정에 고정하지 않음 (20.9 µm는 참고값으로 문서에만)
    assert code.U_mm is None and code.U_source is None
    assert cfg.U_mm is None and cfg.U_source is None


def test_r5_no_specimen_temp_warns_only():
    """R5: 시편 온도가 없으면 '판단 못 함' 경고만, 판정은 그대로."""
    ls = [layer(np.zeros((4, 4)), 0), layer(np.full((4, 4), 0.01), 1)]
    post = layer(np.full((4, 4), 0.005), 1, state="cooled")
    r0 = judge_print(ls, params())
    r1 = judge_print(ls, params(), post=post, height_mm=20.0, specimen_temp_c=None, room_temp_c=25.0)
    assert r1.verdict == r0.verdict == "pass"
    assert any("식힘 기준 판단 못 함" in w and "specimen_temp_c" in w for w in r1.warnings)
