"""rules.py — 실험 2: 통과 조건 1차 판정 (청사진 0_방법탐색 2.2절, 4.2절).

판정값: '통과' / '탈락' / '조건부' / '확인필요'(값이 없어 판단 못 함).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

BUDGET_OWN_KRW = 5_000_000        # own(구입·자작) 구축비 상한 (K3 확정 전 임시)
BUDGET_LAB_KRW = 5_000_000        # lab(학내 장비): 이용료를 own 상한으로 본다 (임시 해석)
BUDGET_OUTSOURCE_KRW = 300_000    # outsource: 시편 1개 1회 의뢰비 상한
SPECIMEN_MIN_MM = 20.0            # 시편 20 × 40 mm 의 짧은 변. fov 가 이보다 작으면 이어 붙이기 필요
# 실현성 (비교-선정.md 4.1절): 시편 1개 측정 ≤ 1 근무일. 선 단면 장비는 면 래스터 시간으로 판정.
FEASIBLE_MAX_MIN = 480.0

# 안전: X선, 레이저 Class 3B, Class 4 → own 이면 탈락 (외부 의뢰만 허용)
# 'Class 1, 4 mW' 처럼 등급이 아닌 숫자 4 에 걸리지 않게, 4 는 반드시 'Class'/'등급' 바로 뒤에서만 본다.
_SAFETY_PATTERNS = [
    ("X선", re.compile(r"x\s*선|x\s*-?\s*ray|엑스선", re.I)),
    ("3B", re.compile(r"(?<![0-9A-Za-z])(?:class\s*)?(?:3\s*b|iii\s*b)(?![0-9A-Za-z])", re.I)),
    ("Class 4", re.compile(r"(?:class|클래스|등급)\s*(?:4|iv)(?![0-9A-Za-z.])", re.I)),
]


def safety_hit(text: str) -> str | None:
    t = str(text or "")
    for name, p in _SAFETY_PATTERNS:
        if p.search(t):
            return name
    return None


def judge_row(r) -> dict:
    reasons = []
    access = str(r.get("access", "")).lower()
    cost = r.get("cost_krw", np.nan)

    # 예산
    if not np.isfinite(cost):
        pb = "확인필요"
        reasons.append("예산: cost_krw 없음")
    elif access == "outsource":
        pb = "통과" if cost <= BUDGET_OUTSOURCE_KRW else "탈락"
        reasons.append(f"예산: 의뢰 1회 {cost:,.0f}원 {'≤' if pb == '통과' else '>'} {BUDGET_OUTSOURCE_KRW:,}원")
    elif access in ("own", "lab"):
        lim = BUDGET_OWN_KRW if access == "own" else BUDGET_LAB_KRW
        pb = "통과" if cost <= lim else "탈락"
        reasons.append(f"예산({access}): {cost:,.0f}원 {'≤' if pb == '통과' else '>'} {lim:,}원")
    else:
        pb = "확인필요"
        reasons.append(f"예산: access '{access}' 알 수 없음")

    # 안전
    hit = safety_hit(r.get("safety", ""))
    if hit and access == "own":
        ps = "탈락"
        reasons.append(f"안전: '{hit}' 해당 + own → 외부 의뢰만 허용")
    elif hit:
        ps = "통과"
        reasons.append(f"안전: '{hit}' 해당이나 {access} (자체 운용 아님)")
    elif not str(r.get("safety", "")).strip():
        ps = "확인필요"
        reasons.append("안전: safety 없음")
    else:
        ps = "통과"

    # G코드 정합 (measures_z 와 무관하게 XY 정합 가능하면 통과)
    step, fov = r.get("xy_step_um", np.nan), r.get("fov_mm", np.nan)
    if not np.isfinite(step) or step <= 0:
        pg = "탈락"
        reasons.append("G코드: XY 점 좌표 없음(xy_step 없음) → 좌표계 정합 불가")
    elif not np.isfinite(fov):
        pg = "확인필요"
        reasons.append("G코드: fov 없음")
    elif fov < SPECIMEN_MIN_MM:
        pg = "조건부"
        reasons.append(f"G코드: fov {fov:g} mm < {SPECIMEN_MIN_MM:g} mm → 이어 붙이기·래스터 필요")
    else:
        pg = "통과"

    # 실현성: 시편 1개 측정 시간 ≤ 480분. 선 단면 장비는 면 래스터 시간(scoring.raster_time_min)
    pf, t_used, by_raster = feasible_time(r)
    if pf == "확인필요":
        reasons.append("실현성: time_min 없음")
    elif pf == "탈락" or by_raster:
        what = "선 단면 장비 면 래스터 " if by_raster else ""
        reasons.append(f"실현성: {what}{t_used:,.0f}분 {'≤' if pf == '통과' else '>'} {FEASIBLE_MAX_MIN:g}분")
    return {"pass_budget": pb, "pass_safety": ps, "pass_gcode": pg, "pass_feasible": pf,
            "time_min_feasible": t_used, "사유": "; ".join(reasons)}


def feasible_time(r) -> tuple[str, float, bool]:
    """→ (판정, 판정에 쓴 시간 [분], 면 래스터 시간을 썼는지)."""
    from scoring import raster_time_min
    tr = raster_time_min(r)
    if np.isfinite(tr):
        t, by_raster = tr, True
    else:
        by_raster = False
        try:
            t = float(r.get("time_min", np.nan))
        except (TypeError, ValueError):
            t = np.nan
    if not np.isfinite(t):
        return "확인필요", np.nan, by_raster
    return ("통과" if t <= FEASIBLE_MAX_MIN else "탈락"), t, by_raster


def judge(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["id", "name"] + [c for c in ("mode",) if c in df.columns] + \
        ["access", "cost_krw", "safety", "xy_step_um", "fov_mm", "time_min"]
    out = df[cols].copy()
    res = df.apply(judge_row, axis=1, result_type="expand")
    out = pd.concat([out, res], axis=1)
    out["rule_ok"] = ~(out[["pass_budget", "pass_safety", "pass_gcode", "pass_feasible"]] == "탈락").any(axis=1)
    return out
