"""scoring.py — 실험 4: 점수화·민감도·조합안 (청사진 0_방법탐색 2.3절, 4.4절).

각 기준을 CSV 값·시뮬레이션 결과에서 1~5점으로 바꾸는 규칙은 아래 상수에 모두 적었다.
구간표 (상한, 점수): 값 ≤ 상한 인 첫 구간의 점수. 어느 구간에도 안 들면 마지막 '그 밖' 점수.
"""
from __future__ import annotations

import itertools
import os

import numpy as np
import pandas as pd

from simulate import ERROR_TYPES, GRADE_RANK

# ---------------------------------------------------------------- 가중치 (%) — 청사진 2.3절 그대로
WEIGHTS = {"precision": 20, "types": 15, "cost": 15, "learn": 15, "speed": 10,
           "surface": 10, "in_situ": 5, "verify": 5, "novelty": 5}
CRIT_KO = {"precision": "정밀도 여유", "types": "오차 종류", "cost": "비용", "learn": "구축·학습 난이도",
           "speed": "속도·자동화", "surface": "재질 의존성", "in_situ": "공정 중 측정",
           "verify": "검증 용이성", "novelty": "연구 기여도"}

# ---------------------------------------------------------------- 점수 규칙
# 정밀도 여유: 그룹(높이·윤곽·치수)별 판정량/4:1 한계 비율 중 '두 번째로 좋은' 값
# (통과 조건이 2종 이상이므로). 0.4 = 10:1 한계(4:1 한계의 0.4배).
PRECISION_BINS = [(0.25, 5), (0.40, 4), (0.70, 3), (1.00, 2)]
PRECISION_ELSE = 1
# 그룹 판정 규칙: (오차 종류 목록, 'max' = 나쁜 쪽 / 'min' = 좋은 쪽)
#  높이 = 국소높이 (단차는 참고), 윤곽 = 국소선폭 (전체 선폭·경계는 참고), 치수 = 구멍지름·길이40 중 나쁜 쪽
GROUP_RULES = {"높이": (["국소높이"], "max"), "윤곽": (["국소선폭"], "max"),
               "치수": (["구멍지름", "길이40"], "max")}
# 오차 종류: 4:1 이상 통과한 종류 수 (참고 지표 단차·선폭·경계 제외)
TYPE_COUNT_TYPES = ["국소높이", "국소선폭", "구멍지름", "길이40", "위치"]
TYPES_SCORE = {5: 5, 4: 4, 3: 3, 2: 2, 1: 1, 0: 1}
# 비용 [원]: own·조합은 구축비, outsource·lab 은 1회 이용료
COST_BINS_OWN = [(300_000, 5), (1_000_000, 4), (2_500_000, 3), (5_000_000, 2)]
COST_BINS_PER_USE = [(50_000, 5), (100_000, 4), (200_000, 3), (300_000, 2)]
COST_ELSE = 1
# 구축·학습 난이도: learn_weeks [주]
LEARN_BINS = [(0.5, 5), (1, 4), (2, 3), (4, 2)]
LEARN_ELSE = 1
# 속도·자동화: time_min [분] (시편 1개)
SPEED_BINS = [(5, 5), (15, 4), (30, 3), (60, 2)]
SPEED_ELSE = 1
# 재질 의존성: 6 − surface_dep (1 낮음 → 5점)
# 공정 중 측정: in_situ 0 = 불가, 1 = 구조상 가능, 2 = 실사용·연구 사례 있음
IN_SITU_SCORE = {0: 1, 1: 3, 2: 5}
# 값이 없을 때: 보수적으로 1점
MISSING_SCORE = 1
# 수동 점수(검증 용이성·연구 기여도) 파일이 없거나 값이 없을 때
MANUAL_DEFAULT = 3
SENS_FACTORS = (0.5, 1.5)          # 가중치 ±50 %

# 선 단면 장비: CSV 의 time_min 은 '단면 몇 줄' 기준이라 면 측정 시간이 아니다.
# 국소높이·국소선폭은 면 래스터 모델값을 쓰므로, 속도 점수도 면 래스터 시간으로 다시 계산한다.
#  면 래스터 시간 = 줄 수 × (줄 길이 / 주사 속도 + 줄당 이동·복귀 시간), 줄 간격 = xy_step
#  주사 속도 100 µm/s: DektakXT 일반 측정 설정(1 mm 주사에 약 10 s) 수준.
#    M02.md 의 '40 mm 한 줄 주사·이동 4분'(≈ 170 µm/s, 이동 포함)과 같은 크기.
#  줄당 이동·복귀 20 s: 스테이지 복귀·안정화 가정.
LINE_PROFILER = {"M02": {"scan_speed_um_s": 100.0, "overhead_s": 20.0}}
SPEC_AREA_MM = (20.0, 40.0)        # 시편 20 × 40 mm, 줄은 40 mm 방향


def raster_time_min(row) -> float:
    rid = str(row.get("id", ""))
    p = LINE_PROFILER.get(rid)
    step = row.get("xy_step_um", np.nan)
    if p is None or not np.isfinite(step) or step <= 0:
        return np.nan
    n_lines = SPEC_AREA_MM[0] * 1000 / step
    t_line = SPEC_AREA_MM[1] * 1000 / p["scan_speed_um_s"] + p["overhead_s"]
    return n_lines * t_line / 60.0


def _bin(v, bins, other):
    if v is None or not np.isfinite(v):
        return MISSING_SCORE
    for hi, s in bins:
        if v <= hi:
            return s
    return other


def group_ratios(sim: dict) -> dict:
    """그룹별 (판정량 / 4:1 한계). 측정 불가 = inf. 치수는 두 종류 중 나쁜 쪽."""
    out = {}
    for g, (types, mode) in GROUP_RULES.items():
        rs = []
        for t in types:
            s = sim[t]
            rs.append(s["Q_um"] / s["lim4_um"] if np.isfinite(s["Q_um"]) else np.inf)
        out[g] = max(rs) if mode == "max" else min(rs)
    return out


def precision_pass(sim: dict):
    """통과 조건 1: 높이·윤곽·치수 중 2종 이상 4:1 통과."""
    r = group_ratios(sim)
    n = sum(v <= 1.0 for v in r.values())
    return n >= 2, n, r


def score_items(row: dict, sim: dict, manual: dict) -> dict:
    r = sorted(group_ratios(sim).values())
    second = r[1]
    s = {}
    s["precision"] = _bin(second, PRECISION_BINS, PRECISION_ELSE) if np.isfinite(second) else 1
    n_types = sum(GRADE_RANK[sim[t]["grade"]] >= 2 for t in TYPE_COUNT_TYPES)
    s["types"] = TYPES_SCORE[n_types]
    access = str(row.get("access", "")).lower()
    bins = COST_BINS_OWN if access == "own" else COST_BINS_PER_USE
    s["cost"] = _bin(row.get("cost_krw", np.nan), bins, COST_ELSE)
    s["learn"] = _bin(row.get("learn_weeks", np.nan), LEARN_BINS, LEARN_ELSE)
    s["speed"] = _bin(row.get("time_min", np.nan), SPEED_BINS, SPEED_ELSE)
    sd = row.get("surface_dep", np.nan)
    s["surface"] = int(np.clip(6 - round(sd), 1, 5)) if np.isfinite(sd) else MISSING_SCORE
    ins = row.get("in_situ", np.nan)
    s["in_situ"] = IN_SITU_SCORE.get(int(round(ins)), MISSING_SCORE) if np.isfinite(ins) else MISSING_SCORE
    s["verify"] = manual.get("verify", MANUAL_DEFAULT)
    s["novelty"] = manual.get("novelty", MANUAL_DEFAULT)
    s["_n_types"] = n_types
    s["_second_ratio"] = second
    return s


def total(scores: dict, weights=WEIGHTS) -> float:
    wsum = sum(weights.values())
    return sum(weights[k] * scores[k] for k in weights) / wsum


def load_manual(path: str) -> dict:
    """수동점수.csv (열: id,verify,novelty) → {id: {'verify': x, 'novelty': y}}. 없으면 {}."""
    if not os.path.exists(path):
        return {}
    from specs import _read_one, to_num
    df = _read_one(path)
    df.columns = [c.strip().lower() for c in df.columns]
    out = {}
    for _, r in df.iterrows():
        d = {}
        for k in ("verify", "novelty"):
            v = to_num(r.get(k, np.nan))
            if np.isfinite(v):
                d[k] = float(np.clip(v, 1, 5))
        out[str(r.get("id", "")).strip()] = d
    return out


# ---------------------------------------------------------------- 조합안
def combine_sims(sa: dict, sb: dict) -> tuple[dict, dict]:
    """종류별로 판정량이 더 좋은 쪽을 고른다 → (조합 sim, {종류: 고른 id 위치 0/1})."""
    out, who = {}, {}
    for name, *_ in ERROR_TYPES:
        a, b = sa[name], sb[name]
        qa = a["Q_um"] if np.isfinite(a["Q_um"]) else np.inf
        qb = b["Q_um"] if np.isfinite(b["Q_um"]) else np.inf
        pick = 0 if (GRADE_RANK[a["grade"]], -qa) >= (GRADE_RANK[b["grade"]], -qb) else 1
        out[name] = (a, b)[pick]
        who[name] = pick
    return out, who


def combo_row(ra: dict, rb: dict) -> dict:
    """조합의 CSV 값: 비용·시간·학습은 합, 재질 의존성은 나쁜 쪽(최대), 공정 중은 좋은 쪽(최대)."""
    def ssum(k):
        v = [ra.get(k, np.nan), rb.get(k, np.nan)]
        return float(np.sum(v)) if all(np.isfinite(v)) else np.nan

    acc = {str(ra.get("access", "")).lower(), str(rb.get("access", "")).lower()}
    return {"cost_krw": ssum("cost_krw"), "time_min": ssum("time_min"), "learn_weeks": ssum("learn_weeks"),
            "surface_dep": np.nanmax([ra.get("surface_dep", np.nan), rb.get("surface_dep", np.nan)]),
            "in_situ": np.nanmax([ra.get("in_situ", np.nan), rb.get("in_situ", np.nan)]),
            "access": "own" if "own" in acc else ("outsource" if acc == {"outsource"} else "lab")}


def combo_budget_ok(ra, rb, budget_own, budget_out):
    own_sum = 0.0
    for r in (ra, rb):
        c = r.get("cost_krw", np.nan)
        a = str(r.get("access", "")).lower()
        if not np.isfinite(c):
            return None
        if a == "outsource":
            if c > budget_out:
                return False
        else:
            own_sum += c
    return own_sum <= budget_own


def find_combos(ids, rows, sims, manual, rule_tab, budget_own, budget_out):
    """통과 조건 1을 혼자 못 맞추는 (규칙 탈락 없는) 후보끼리 2개 조합을 모두 본다."""
    res = []
    for a, b in itertools.combinations(ids, 2):
        csim, who = combine_sims(sims[a], sims[b])
        ok, n, ratios = precision_pass(csim)
        crow = combo_row(rows[a], rows[b])
        ma, mb = manual.get(a, {}), manual.get(b, {})
        cm = {k: np.mean([ma.get(k, MANUAL_DEFAULT), mb.get(k, MANUAL_DEFAULT)]) for k in ("verify", "novelty")}
        sc = score_items(crow, csim, cm)
        bud = combo_budget_ok(rows[a], rows[b], budget_own, budget_out)
        gc = {rule_tab[a]["pass_gcode"], rule_tab[b]["pass_gcode"]}
        rec = {"combo": f"{a}+{b}", "a": a, "b": b, "pass_precision": ok, "n_groups_4to1": n,
               "budget_ok": {True: "통과", False: "탈락", None: "확인필요"}[bud],
               "gcode": "조건부" if "조건부" in gc else ("확인필요" if "확인필요" in gc else "통과")}
        for name, *_ in ERROR_TYPES:
            rec[f"{name}_판정"] = csim[name]["grade"]
            rec[f"{name}_Q_um"] = csim[name]["Q_um"]
            rec[f"{name}_담당"] = (a, b)[who[name]]
        rec.update({k: crow[k] for k in ("cost_krw", "time_min", "learn_weeks")})
        for k in WEIGHTS:
            rec[f"s_{k}"] = sc[k]
        rec["score"] = total(sc)
        rec["_scores"] = sc
        res.append(rec)
    return res


# ---------------------------------------------------------------- 민감도
def sensitivity(pool: dict) -> pd.DataFrame:
    """pool = {이름: 점수 dict}. 각 가중치를 ×0.5, ×1.5 로 바꾼 18 경우 + 기준의 순위."""
    scen = {"기준": dict(WEIGHTS)}
    for k in WEIGHTS:
        for f in SENS_FACTORS:
            w = dict(WEIGHTS)
            w[k] = WEIGHTS[k] * f
            scen[f"{CRIT_KO[k]}×{f:g}"] = w
    tab = {}
    for sname, w in scen.items():
        sc = pd.Series({n: total(s, w) for n, s in pool.items()})
        tab[sname] = sc.rank(ascending=False, method="min").astype(int)
    df = pd.DataFrame(tab)
    df.insert(0, "base_score", pd.Series({n: total(s) for n, s in pool.items()}))
    ranks = df[list(scen)]
    df.insert(1, "base_rank", ranks["기준"])
    df.insert(2, "min_rank", ranks.min(axis=1))
    df.insert(3, "max_rank", ranks.max(axis=1))
    df.insert(4, "top3_count", (ranks <= 3).sum(axis=1))
    df.insert(5, "n_scenarios", ranks.shape[1])
    return df.sort_values(["base_rank", "max_rank"])
