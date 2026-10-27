"""C12 채점 (판정 정확도). 참 판정은 인자로만 받고 파일을 열지 않는다."""
from __future__ import annotations

from typing import Any, Sequence

PRED = ("pass", "fail", "hold", "insufficient")
TRUE = ("pass", "fail", "borderline")


def _label(x: Any) -> str:
    return getattr(x, "verdict", x)


def score_c12(pred: Sequence[Any], true: Sequence[str]) -> dict:
    """혼동표와 C12 기준.

    필수: 참 fail → 예측 pass = 0건. 안: 참 pass → 예측 fail ≤ 참 pass 수의 5 % (정수 비교).
    pred 원소는 문자열 또는 .verdict가 있는 JudgeResult.
    """
    p = [_label(x) for x in pred]
    t = list(true)
    if len(p) != len(t):
        raise ValueError(f"pred {len(p)}개 ≠ true {len(t)}개")
    bad_p = sorted({x for x in p if x not in PRED})
    bad_t = sorted({x for x in t if x not in TRUE})
    if bad_p or bad_t:
        raise ValueError(f"모르는 판정: pred {bad_p}, true {bad_t}")
    conf = {tt: {pp: 0 for pp in PRED} for tt in TRUE}
    for pp, tt in zip(p, t):
        conf[tt][pp] += 1
    n = len(p)
    n_true_pass = sum(conf["pass"].values())
    false_pass = conf["fail"]["pass"]
    false_fail = conf["pass"]["fail"]
    n_hold = sum(conf[tt]["hold"] for tt in TRUE)
    n_ins = sum(conf[tt]["insufficient"] for tt in TRUE)
    return {
        "n": n,
        "confusion": conf,
        "false_pass": false_pass,
        "false_fail": false_fail,
        "false_fail_rate": (false_fail / n_true_pass) if n_true_pass else None,
        "hold_rate": (n_hold / n) if n else None,
        "insufficient_rate": (n_ins / n) if n else None,
        "borderline_pred": dict(conf["borderline"]),
        "true_fail_to_insufficient": conf["fail"]["insufficient"],
        "c12_required_ok": false_pass == 0,
        "c12_target_ok": false_fail * 100 <= 5 * n_true_pass,
    }
