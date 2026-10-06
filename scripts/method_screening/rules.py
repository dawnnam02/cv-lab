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

# 안전: X선, 레이저 Class 3B, Class 4 → own 이면 탈락 (외부 의뢰만 허용)
_SAFETY_PATTERNS = [
    re.compile(r"x\s*-?\s*선|x\s*-?\s*ray|엑스선|방사선", re.I),
    re.compile(r"3\s*b|iii\s*b", re.I),
    re.compile(r"(?<![\w.\-])(?:4|iv)(?![\w.])", re.I),     # 'Class 4', '4', 'IV' (낱말 단위)
]


def safety_hit(text: str) -> str | None:
    t = str(text or "")
    if not t.strip():
        return None
    names = ["X선", "3B", "4"]
    for name, p in zip(names, _SAFETY_PATTERNS):
        if name == "4":
            # 'IEC 60825-1:2014' 같은 규격 번호의 숫자에 걸리지 않게 낱말 단위로 본다
            t2 = re.sub(r"\d{3,}[\d\-:.]*", " ", t)
            if p.search(t2):
                return name
        elif p.search(t):
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
    return {"pass_budget": pb, "pass_safety": ps, "pass_gcode": pg, "사유": "; ".join(reasons)}


def judge(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["id", "name", "access", "cost_krw", "safety", "xy_step_um", "fov_mm"]].copy()
    res = df.apply(judge_row, axis=1, result_type="expand")
    out = pd.concat([out, res], axis=1)
    out["rule_ok"] = ~(out[["pass_budget", "pass_safety", "pass_gcode"]] == "탈락").any(axis=1)
    return out
