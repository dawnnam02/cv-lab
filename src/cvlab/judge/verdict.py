"""출력물 판정 (D-05–D-08).

- 입력은 층마다 판정 칸 격자 위 Δ (mm)와 판정 영역 (bool).
- 전체 층의 유효 칸을 합쳐서 센다 (층별 비율의 평균이 아님, D-08).
- 순서: 측정 불충분 → 합격 (합격점 ≥ 95 %) → 불합격 (불합격점 > 5 %) → 보류. 비율은 정수 곱셈으로 비교.
- 판정에는 thermal_state = in_process 층만 받는다 (D-06, MF-JDG-05).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Sequence

import numpy as np

from .aggregate import (EXCLUSION_CODES, aggregate_exclusion_code, aggregate_mask_any,
                        aggregate_to_cells, cell_factor)
from .classify import FAIL, HOLD, PASS, classify_cells, thresholds_nm, to_nm
from .cooled import cooled_difference, cooling_criterion
from .params import JudgeParams

VERDICTS = ("pass", "hold", "insufficient", "fail")
VERDICT_RANK = {v: i for i, v in enumerate(VERDICTS)}  # 합격 < 보류 < 측정 불충분 < 불합격
EXCLUSION_NAMES = {1: "엣지 띠", 2: "가림 예측", 3: "시야 밖", 4: "제외 경로 종류", 5: "출력물 없음", 9: "기타"}

NOTE_VIRTUAL = ("해석 주의. 가상 데이터로 얻은 U와 판정 정확도는 \"알고리즘이 시뮬레이터가 넣은 오차를 얼마나 "
                "복원하는가\"입니다. 하드웨어 성능의 증거가 아닙니다.")
NOTE_BLIND = ("측정이 못 보는 오차. 프린터 Z축·프레임 드리프트처럼 출력과 측정이 함께 가진 오차는 이 측정이 "
              "스스로 보지 못합니다. 그 몫은 U 예산에 그대로 두었습니다 (D-14).")
NOTE_HOLD = "보류는 재측정 또는 사람이 판단합니다. 재측정은 무작위 몫만 줄입니다 (청사진 §2.3)."


@dataclass
class LayerInput:
    layer_idx: int
    thermal_state: str
    delta_mm: Any
    region: Any
    outlier: Any = None
    exclusion_code: Any = None

    def __post_init__(self) -> None:
        if isinstance(self.layer_idx, bool) or not isinstance(self.layer_idx, (int, np.integer)):
            raise ValueError(f"layer_idx: 정수가 아님 ({self.layer_idx!r})")
        self.layer_idx = int(self.layer_idx)
        if self.layer_idx < 0:
            raise ValueError("layer_idx: 음수")
        self.delta_mm = np.asarray(self.delta_mm, dtype=float)
        if self.delta_mm.ndim != 2:
            raise ValueError(f"층 {self.layer_idx}: delta_mm은 2차원이어야 함")
        if np.isinf(self.delta_mm).any():
            raise ValueError(f"층 {self.layer_idx}: delta_mm에 무한대 값")
        r = np.asarray(self.region)
        if r.dtype != bool:
            raise ValueError(f"층 {self.layer_idx}: region은 bool 배열이어야 함")
        if r.shape != self.delta_mm.shape:
            raise ValueError(f"층 {self.layer_idx}: region 모양 {r.shape} ≠ delta 모양 {self.delta_mm.shape}")
        self.region = r
        if self.outlier is not None:
            o = np.asarray(self.outlier)
            if o.dtype != bool or o.shape != r.shape:
                raise ValueError(f"층 {self.layer_idx}: outlier는 같은 모양의 bool 배열이어야 함")
            self.outlier = o
        if self.exclusion_code is not None:
            c = np.asarray(self.exclusion_code)
            if c.shape != r.shape:
                raise ValueError(f"층 {self.layer_idx}: exclusion_code 모양이 다름")
            if not np.isin(c, EXCLUSION_CODES).all():
                raise ValueError(f"층 {self.layer_idx}: exclusion_code가 코드표 {EXCLUSION_CODES} 밖")
            if (r & (c != 0)).any():
                raise ValueError(f"층 {self.layer_idx}: 판정 영역 안 칸에 0이 아닌 exclusion_code")
            self.exclusion_code = c.astype(np.int8)


@dataclass
class JudgeResult:
    verdict: str
    counts: dict
    pct: dict
    per_layer: list
    method_a: dict
    outlier_variants: dict | None
    cooled: dict | None
    metrics: dict
    exclusions: dict
    warnings: list
    params: dict
    thresholds: dict
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return _jsonable({
            "verdict": self.verdict, "counts": self.counts, "pct": self.pct,
            "per_layer": self.per_layer, "method_a": self.method_a,
            "outlier_variants": self.outlier_variants, "cooled": self.cooled,
            "metrics": self.metrics, "exclusions": self.exclusions, "warnings": self.warnings,
            "params": self.params, "thresholds": self.thresholds, "notes": self.notes,
        })

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False, **kw)


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, Fraction):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    return x


# --- 순수 규칙 --------------------------------------------------------------

def decide(n_region: int, n_valid: int, n_pass: int, n_fail: int, params: JudgeParams) -> str:
    """칸 수에서 판정 하나. 모든 비교는 정수 곱셈."""
    v = params.pct("valid_min_pct")
    p = params.pct("pass_min_pct")
    f = params.pct("fail_max_pct")
    if n_region == 0 or n_valid == 0:
        return "insufficient"
    if n_valid * 100 * v.denominator < v.numerator * n_region:
        return "insufficient"
    if n_pass * 100 * p.denominator >= p.numerator * n_valid:
        return "pass"
    if n_fail * 100 * f.denominator > f.numerator * n_valid:
        return "fail"
    return "hold"


def _pct(n: int, d: int) -> float | None:
    return None if d == 0 else 100.0 * n / d


def _metrics(vals_mm: np.ndarray, T_mm: float) -> dict:
    """H5 대표 지표. 단위 µm. 부호 + = 실측이 높음."""
    n = int(vals_mm.size)
    if n == 0:
        return {"n": 0, "mean_um": None, "std_um": None, "rms_um": None, "p95_abs_um": None,
                "max_abs_um": None, "p05_um": None, "p95_um": None, "within_T_pct": None}
    e = vals_mm * 1000.0
    a = np.abs(e)
    within = int((to_nm(np.abs(vals_mm)) <= int(np.rint(T_mm * 1e6))).sum())
    return {
        "n": n,
        "mean_um": float(np.mean(e)),
        "std_um": float(np.std(e, ddof=1)) if n >= 2 else None,
        "rms_um": float(np.sqrt(np.mean(e * e))),
        "p95_abs_um": float(np.percentile(a, 95)),
        "max_abs_um": float(np.max(a)),
        "p05_um": float(np.percentile(e, 5)),
        "p95_um": float(np.percentile(e, 95)),
        "within_T_pct": 100.0 * within / n,
    }


def _count_variant(layers: Sequence[LayerInput], params: JudgeParams, U_mm: float, drop_outliers: bool):
    """변형 하나 (이상치 제외 여부)에 대한 층별·전체 칸 수."""
    per = []
    tot = dict(n_region=0, n_valid=0, n_pass=0, n_hold=0, n_fail=0)
    vals = []
    for L in layers:
        valid = L.region & np.isfinite(L.delta_mm)
        if drop_outliers and L.outlier is not None:
            valid &= ~L.outlier
        cls = classify_cells(np.where(valid, L.delta_mm, np.nan), params.T_mm, U_mm)
        c = dict(n_region=int(L.region.sum()), n_valid=int(valid.sum()),
                 n_pass=int((cls == PASS).sum()), n_hold=int((cls == HOLD).sum()),
                 n_fail=int((cls == FAIL).sum()))
        for k in tot:
            tot[k] += c[k]
        v = L.delta_mm[valid]
        vals.append(v)
        per.append((L, c, v))
    allv = np.concatenate(vals) if vals else np.zeros(0)
    verdict = decide(tot["n_region"], tot["n_valid"], tot["n_pass"], tot["n_fail"], params)
    return verdict, tot, per, allv


def _pct_block(c: dict) -> dict:
    return {
        "valid_pct": _pct(c["n_valid"], c["n_region"]),
        "pass_pct": _pct(c["n_pass"], c["n_valid"]),
        "hold_pct": _pct(c["n_hold"], c["n_valid"]),
        "fail_pct": _pct(c["n_fail"], c["n_valid"]),
    }


def judge_print(layers: Sequence[LayerInput], params: JudgeParams, post: LayerInput | None = None, *,
                height_mm: float | None = None, specimen_temp_c: float | None = None,
                room_temp_c: float | None = None) -> JudgeResult:
    """출력물 하나를 판정한다.

    post: 식힌 재측정 (thermal_state = cooled, 마지막 층과 같은 layer_idx). 판정을 바꾸지 않음.
    height_mm · specimen_temp_c · room_temp_c: '식었다' 기준 안 계산용 (없으면 미상으로 보고).
    """
    if not isinstance(params, JudgeParams):
        raise ValueError("params: JudgeParams가 아님")
    params.require_ready()
    U = float(params.U_mm)
    layers = list(layers)
    if not layers:
        raise ValueError("층이 없음")
    seen = set()
    for L in layers:
        if not isinstance(L, LayerInput):
            raise ValueError("layers: LayerInput이 아닌 값")
        if L.thermal_state != "in_process":
            raise ValueError(f"층 {L.layer_idx}: thermal_state = {L.thermal_state!r}. 판정에는 in_process만 받음 "
                             "(D-06, MF-JDG-05). 식힌 재측정은 post 인자로 넣을 것")
        if L.layer_idx in seen:
            raise ValueError(f"층 {L.layer_idx}: 같은 layer_idx가 두 번 들어옴 (패스 합치기는 앞 단계 몫)")
        seen.add(L.layer_idx)
    layers.sort(key=lambda L: L.layer_idx)
    warns: list[str] = []

    has_outlier = any(L.outlier is not None and L.outlier.any() for L in layers)
    before = _count_variant(layers, params, U, drop_outliers=False)
    if has_outlier:
        after = _count_variant(layers, params, U, drop_outliers=True)
        if params.outlier_primary == "before":
            primary_name = "before"
        elif params.outlier_primary == "after":
            primary_name = "after"
        else:  # worse: 덜 유리한 쪽, 같으면 제외 전 (데이터를 빼지 않은 쪽)
            primary_name = "after" if VERDICT_RANK[after[0]] > VERDICT_RANK[before[0]] else "before"
        primary = after if primary_name == "after" else before
        differ = before[0] != after[0]
        if differ:
            warns.append(f"이상치 처리에 따라 판정이 바뀜: 제외 전 {before[0]}, 제외 후 {after[0]}. "
                         f"주 판정은 {primary_name} ({params.outlier_primary}) (MF-JDG-03)")
        outlier_variants = {
            "before": {"verdict": before[0], "counts": before[1], "pct": _pct_block(before[1])},
            "after": {"verdict": after[0], "counts": after[1], "pct": _pct_block(after[1])},
            "primary": primary_name, "rule": params.outlier_primary, "differ": differ,
            "n_outlier_cells": int(sum(int((L.outlier & L.region).sum()) for L in layers if L.outlier is not None)),
        }
    else:
        primary, outlier_variants = before, None
    verdict, counts, per, allv = primary

    # 층별 표와 경고 (MF-JDG-06)
    wp = params.pct("layer_fail_warn_pct")
    per_layer = []
    for L, c, v in per:
        row = {"layer_idx": L.layer_idx, **c, **_pct_block(c), "metrics": _metrics(v, params.T_mm)}
        row["warn_fail"] = bool(c["n_valid"] > 0 and c["n_fail"] * 100 * wp.denominator > wp.numerator * c["n_valid"])
        if row["warn_fail"]:
            warns.append(f"층 {L.layer_idx}: 불합격점 {row['fail_pct']:.1f} % > {float(wp):g} % "
                         "(전체 합산 판정에 묻힐 수 있음, MF-JDG-06)")
        if c["n_region"] > 0 and c["n_valid"] == 0:
            warns.append(f"층 {L.layer_idx}: 판정 영역은 있으나 유효 칸이 없음")
        per_layer.append(row)

    # 방식 A (참고): |Δ| ≤ T 비율, 95 % 규칙
    va, ca, _, _ = _count_variant(layers, params, 0.0, drop_outliers=(primary is not before))
    method_a = {"verdict": va, "counts": ca, "pct": _pct_block(ca),
                "rule": "합격점 |Δ| ≤ T, 합격점 ≥ pass_min_pct 이면 합격 (가드밴드 없음, 참고용)"}
    if va == "pass" and verdict in ("hold", "fail"):
        warns.append(f"방식 A는 합격, 방식 B는 {verdict}: 경계 근처 점이 많음 (MF-JDG-07)")

    # 뺀 이유별 칸 수 (MF-JDG-03)
    excl = {"region_cells": counts["n_region"], "no_delta_in_region": counts["n_region"] - counts["n_valid"],
            "by_code": None}
    if any(L.exclusion_code is not None for L in layers):
        by = {EXCLUSION_NAMES[k]: 0 for k in EXCLUSION_NAMES}
        unexplained = 0
        for L in layers:
            if L.exclusion_code is None:
                unexplained += int((~L.region).sum())
                continue
            out = ~L.region
            for k, name in EXCLUSION_NAMES.items():
                by[name] += int((out & (L.exclusion_code == k)).sum())
            unexplained += int((out & (L.exclusion_code == 0)).sum())
        by["이유 없음"] = unexplained
        excl["by_code"] = by
        if unexplained:
            warns.append(f"판정 영역 밖인데 이유 코드가 0인 칸 {unexplained}개")

    if verdict == "insufficient":
        if counts["n_region"] == 0:
            warns.append("판정 영역이 비어 있음 → 측정 불충분")
        else:
            warns.append(f"유효 칸 {counts['n_valid']}/{counts['n_region']} < {float(params.pct('valid_min_pct')):g} % → 측정 불충분")

    # 식힌 재측정 (D-06): 판정과 무관
    cooled = None
    if post is not None:
        if not isinstance(post, LayerInput):
            raise ValueError("post: LayerInput이 아님")
        if post.thermal_state != "cooled":
            raise ValueError(f"post: thermal_state = {post.thermal_state!r}. 식힌 재측정은 cooled여야 함")
        last = layers[-1]
        if post.layer_idx != last.layer_idx:
            raise ValueError(f"post: layer_idx {post.layer_idx} ≠ 마지막 층 {last.layer_idx}")
        diff = cooled_difference(last.delta_mm, post.delta_mm, region=last.region & post.region)
        if diff is None:
            warns.append("식힌 재측정: 마지막 층과 공통 유효 칸이 없음")
        crit = cooling_criterion(height_mm, specimen_temp_c, room_temp_c,
                                 params.cooled_alpha_um_per_m_c, params.cooled_delta_max_um)
        if crit["ok"] is False:
            warns.append(f"식힘 부족: 남은 수축 {crit['residual_shrink_um']:.1f} µm > {crit['delta_max_um']:g} µm "
                         f"(ΔT {crit['delta_T_c']:.1f} °C > ΔT_max {crit['delta_T_max_c']:.1f} °C)")
        elif crit["ok"] is None:
            warns.append(f"식힘 기준 판단 못 함: {', '.join(crit['missing'])} 없음")
        cooled = {"layer_idx": last.layer_idx, "difference": diff, "criterion": crit,
                  "note": "차이 = Δ_post − Δ_last (µm). 음수면 식으면서 낮아짐. 판정을 바꾸지 않음 (D-06)"}

    t_pass, t_fail = thresholds_nm(params.T_mm, U)
    thresholds = {"t_pass_nm": t_pass, "t_fail_nm": t_fail, "T_nm": int(np.rint(params.T_mm * 1e6)),
                  "pass_band_mm": [0.0, t_pass / 1e6], "hold_band_mm": [t_pass / 1e6, t_fail / 1e6],
                  "band_um": 2 * U * 1000.0, "band_pct_of_T": 2 * U / params.T_mm * 100.0}
    metrics = {"all": _metrics(allv, params.T_mm)}
    return JudgeResult(
        verdict=verdict, counts=counts, pct=_pct_block(counts), per_layer=per_layer, method_a=method_a,
        outlier_variants=outlier_variants, cooled=cooled, metrics=metrics, exclusions=excl,
        warnings=warns, params=params.to_dict(), thresholds=thresholds,
        notes=[NOTE_VIRTUAL, NOTE_BLIND, NOTE_HOLD],
    )


def fine_to_cell_layer(L: LayerInput, res_mm: float, cell_mm: float, params: JudgeParams) -> LayerInput:
    """고운 격자 층을 판정 칸 층으로 묶는다 (§6.2–6.3). 이상치는 묶음 안에 하나라도 있으면 그 칸을 이상치로."""
    f = cell_factor(cell_mm, res_mm)
    d, valid, region = aggregate_to_cells(L.delta_mm, None, L.region, f, stat=params.cell_stat,
                                          fill_min=params.cell_fill_min, region_fill_min=params.region_fill_min)
    outlier = None
    if L.outlier is not None:
        outlier = aggregate_mask_any(L.outlier & L.region, f) & region
    code = None
    if L.exclusion_code is not None:
        code = np.where(region, 0, aggregate_exclusion_code(L.exclusion_code, f)).astype(np.int8)
    return LayerInput(L.layer_idx, L.thermal_state, d, region, outlier=outlier, exclusion_code=code)


def judge_print_fine(layers_fine: Sequence[LayerInput], params: JudgeParams, res_mm: float = 0.02,
                     post: LayerInput | None = None, **kw) -> dict:
    """고운 격자 입력을 주 칸 (cell_mm)과 보조 칸 (cell_mm_alt)으로 각각 판정 (MF-JDG-04)."""
    out = {}
    for key, cm in (("primary", params.cell_mm), ("alt", params.cell_mm_alt)):
        ls = [fine_to_cell_layer(L, res_mm, cm, params) for L in layers_fine]
        pc = fine_to_cell_layer(post, res_mm, cm, params) if post is not None else None
        r = judge_print(ls, params, pc, **kw)
        r.params = {**r.params, "cell_mm_used": cm, "res_mm": res_mm}
        out[key] = r
    if out["primary"].verdict != out["alt"].verdict:
        out["primary"].warnings.append(
            f"칸 크기에 따라 판정이 바뀜: {params.cell_mm} mm {out['primary'].verdict}, "
            f"{params.cell_mm_alt} mm {out['alt'].verdict} (MF-JDG-04)")
    return out
