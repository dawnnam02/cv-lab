"""U 민감도 표와 칸 크기 민감도 표 (T15 JD13).

시나리오 분포는 시험용 가정이며 측정값이 아니다.
실행: PYTHONPATH=src python scripts/judge_sensitivity.py
출력: docs/판정-규칙_자료/민감도_U.csv · 칸크기_민감도.csv
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

from cvlab.judge import JudgeParams, LayerInput, aggregate_to_cells, judge_print

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "판정-규칙_자료"
SEED = 20261027
T_MM = 0.20

# U 값 (µm)과 출처. 판정용 U는 T12 (C8)에서 정한다. 여기 값은 문서 값을 옮기거나 격자로 둔 것.
U_SOURCES = {u: "격자 값 (0–100 µm, 5 µm 간격)" for u in range(0, 101, 5)}
U_SOURCES.update({
    13.0: "팀장검증 2차 §3.3 단계 4 (+ 재료 치우침 교정, GUM)",
    14.6: "팀장검증 2차 §3.3 단계 3 (+ 계단 기준물 D-16, GUM)",
    20.9: "팀장검증 2차 §3.3 단계 2 (열 기울기를 U에서 뺌, GUM)",
    21.0: "청사진 §2.3 메모 (D-15 합산 규칙, 약 21 µm)",
    26.1: "팀장검증 2차 §3.3 단계 1 (합산 규칙 정리, GUM)",
    31.7: "T2 측정-실패사례 5.2 기본 시나리오 (치우침 RSS)",
    66.9: "T2 측정-실패사례 5.2 기본 시나리오 (선형 합)",
})
U_SOURCES[15] = "격자 값 · 청사진 §2.3 메모 (계단 기준물까지 약 15 µm)"
U_SOURCES[20] = "격자 값 · T2 MF-JDG-07 목표 20 µm"
U_SOURCES[50] = "격자 값 · 청사진 §2.3 4:1 전제 상한 50 µm"
U_LIST = sorted({float(u) for u in U_SOURCES})

COLS = ["scenario", "n_cells", "seed", "U_um", "U_source", "band_um", "band_pct_of_T", "pass_pct", "hold_pct",
        "fail_pct", "verdict", "pass_pct_analytic", "hold_pct_analytic", "fail_pct_analytic"]


def phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def p_abs_le(a: float, mu: float, sigma: float) -> float:
    """P(|Δ| ≤ a), Δ ~ N(μ, σ)."""
    if a < 0:
        return 0.0
    return phi((a - mu) / sigma) - phi((-a - mu) / sigma)


def texture_fine(rng, n_fine: int, res: float = 0.02) -> np.ndarray:
    """B1: 0.10 + 0.025·sin(2πx/0.4) + N(0, 0.005), x = 0.01, 0.03, … (고운 칸 중심)."""
    x = res / 2 + res * np.arange(n_fine)
    row = 0.10 + 0.025 * np.sin(2 * np.pi * x / 0.4)
    return row[None, :] + rng.normal(0.0, 0.005, size=(n_fine, n_fine))


def scenarios():
    """(이름, 판정 칸 Δ, 정규분포 (μ, σ) 또는 None)."""
    out = []
    for name, mu, sigma in (("N1", 0.0, 0.05), ("N2", 0.12, 0.04), ("N3", 0.20, 0.03)):
        rng = np.random.default_rng(SEED)
        out.append((name, rng.normal(mu, sigma, size=(1000, 1000)), (mu, sigma)))
    rng = np.random.default_rng(SEED)
    fine = texture_fine(rng, 2000)
    cell, _, _ = aggregate_to_cells(fine, None, None, 10)
    out.append(("B1", cell, None))
    return out, fine


def fmt(x: float) -> str:
    return f"{x:.8f}"


def judge_row(delta, U_um: float, src: str):
    p = JudgeParams(T_mm=T_MM, U_mm=U_um / 1000.0, U_source=src)
    L = LayerInput(0, "in_process", delta, np.ones(delta.shape, bool))
    return judge_print([L], p)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scen, fine = scenarios()
    rows = []
    for name, delta, dist in scen:
        n = int(delta.size)
        for U_um in U_LIST:
            src = U_SOURCES[U_um]          # 15.0 == 15 이라 같은 키
            r = judge_row(delta, U_um, src)
            c = r.counts
            row = {
                "scenario": name, "n_cells": n, "seed": SEED, "U_um": repr(U_um), "U_source": src,
                "band_um": repr(2 * U_um), "band_pct_of_T": repr(2 * U_um / 200 * 100),
                "pass_pct": fmt(100 * c["n_pass"] / c["n_valid"]),
                "hold_pct": fmt(100 * c["n_hold"] / c["n_valid"]),
                "fail_pct": fmt(100 * c["n_fail"] / c["n_valid"]),
                "verdict": r.verdict,
                "pass_pct_analytic": "", "hold_pct_analytic": "", "fail_pct_analytic": "",
            }
            if dist is not None:
                mu, sigma = dist
                pp = p_abs_le(T_MM - U_um / 1000, mu, sigma)
                pf = 1.0 - p_abs_le(T_MM + U_um / 1000, mu, sigma)
                row["pass_pct_analytic"] = fmt(100 * pp)
                row["hold_pct_analytic"] = fmt(100 * (1 - pp - pf))
                row["fail_pct_analytic"] = fmt(100 * pf)
            rows.append(row)
    with open(OUT / "민감도_U.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    # 칸 크기 민감도 (MF-JDG-04): B1을 0.2 · 0.4 mm 칸으로, 팀장 U 후보마다.
    # B1_016: 같은 결을 0.06 mm 올린 시험용 가정 (기준 0.16 mm). 결이 경계에 걸릴 때 칸 크기 효과를 보이려고 더함.
    crow = []
    for sname, shift in (("B1", 0.0), ("B1_016", 0.06)):
      for U_um in (31.7, 66.9, 26.1, 20.9, 14.6, 13.0):
        for cell_mm, f in ((0.2, 10), (0.4, 20)):
            cell, _, _ = aggregate_to_cells(fine + shift, None, None, f)
            r = judge_row(cell, U_um, U_SOURCES[U_um])
            c = r.counts
            crow.append({
                "scenario": sname, "cell_mm": cell_mm, "n_cells": int(cell.size), "seed": SEED, "U_um": U_um,
                "U_source": U_SOURCES[U_um],
                "pass_pct": fmt(100 * c["n_pass"] / c["n_valid"]), "hold_pct": fmt(100 * c["n_hold"] / c["n_valid"]),
                "fail_pct": fmt(100 * c["n_fail"] / c["n_valid"]), "verdict": r.verdict,
                "cell_min_mm": fmt(float(np.nanmin(cell))), "cell_max_mm": fmt(float(np.nanmax(cell))),
                "cell_std_um": fmt(float(np.nanstd(cell, ddof=1) * 1000)),
            })
    with open(OUT / "칸크기_민감도.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(crow[0].keys()))
        w.writeheader()
        w.writerows(crow)

    print(f"민감도_U.csv {len(rows)}행 (시나리오 {len(scen)} × U {len(U_LIST)}), 칸크기_민감도.csv {len(crow)}행")
    lead = [66.9, 31.7, 26.1, 20.9, 14.6, 13.0]
    print("팀장 U 후보별 보류 비율 (%)")
    print("U_um  " + "  ".join(f"{s:>8}" for s, _, _ in scen))
    for u in lead:
        vals = [next(r for r in rows if r["scenario"] == s and float(r["U_um"]) == u) for s, _, _ in scen]
        print(f"{u:<5} " + "  ".join(f"{float(v['hold_pct']):8.3f}" for v in vals)
              + "   판정 " + "/".join(v["verdict"] for v in vals))


if __name__ == "__main__":
    main()
