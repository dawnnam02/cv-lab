# J4. 시각화 · 리포트

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: J. 소프트웨어

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-29 ~ 2027-01-11 (W13-14) |
| 우선순위 | 보통 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [J3 합성 테스트](J3-synthetic-tests.md), [G4 평가 마스크](../G-reference/G4-evaluation-masks.md), [H5 높이 지표](../H-analysis/H5-height-metrics.md), [H6 윤곽 지표](../H-analysis/H6-contour-metrics.md), [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) (H5–H7과 같은 기간 병행), [J2 설정·재현성](J2-config-reproducibility.md) |
| 후행 요소 | [H8 통계](../H-analysis/H8-statistics.md), [I1 불확도](../I-reliability/I1-uncertainty.md), [I3 교차검증](../I-reliability/I3-cross-validation.md), [K5 산출물·논문](../K-management/K5-deliverables-paper.md) |
| 관련 마일스톤 | **M4** (W14 말): 시편 1개 전체 파이프라인 완주 — 이 요소의 리포트 묶음이 M4의 눈에 보이는 산출물 |

## 1. 목적

- 시편 하나를 처리하면 **같은 규칙으로 그린 그림 4장(편차 히트맵 · 마스크 오버레이 · 히스토그램 · 단면 프로파일) + 지표 CSV 1개**가 자동으로 생기게 합니다.
- 모든 시편 결과를 **`results/summary.csv` 한 표**에 한 줄씩 모아 H8 통계와 논문 표의 원본으로 씁니다.
- 그림이 사람을 속이지 않도록 색 규칙을 고정합니다: **발산형 컬러맵 `RdBu_r`, 0 = 흰색, 범위 ±0.2 mm 대칭·고정, 빨강 = + = 재료 과다, 파랑 = − = 재료 부족**(청사진 A1 부호 규칙). 시편마다 색 범위가 바뀌면 시편끼리 비교할 수 없습니다.
- 논문용 품질(300 dpi 이상, 축 라벨에 단위)을 처음부터 만족시켜 K5 단계에서 그림을 다시 그리지 않게 합니다.

## 2. 배경 지식 (초보자용)

**matplotlib 기본 구조**: `fig, ax = plt.subplots()` 로 종이(`fig`)와 그림 영역(`ax`)을 만들고, `ax.imshow`, `ax.hist`, `ax.plot` 으로 그린 뒤 `fig.savefig("파일.png", dpi=300)` 로 저장합니다. 스크립트에서는 화면 창을 띄우지 않도록 **`matplotlib.use("Agg")`** 를 맨 위에 둡니다(서버·자동 처리에서 창 때문에 멈추는 일 방지). 저장 후 `plt.close(fig)` 를 하지 않으면 시편 100개를 처리할 때 메모리가 계속 늘어납니다.

**컬러맵 3종류**

| 종류 | 예 | 언제 |
|---|---|---|
| 순차형(sequential) | `viridis`, `gray` | 높이 자체(0 → 최대) |
| **발산형(diverging)** | **`RdBu_r`**, `coolwarm` | **편차처럼 0을 기준으로 +/−가 있는 값** |
| 범주형(qualitative) | `tab10` | 조건 구분 |

`RdBu` 는 빨강 → 흰색 → 파랑 순서이고, 끝의 `_r` 은 뒤집기(reverse)입니다. `RdBu_r` 은 **음수 = 파랑, 0 = 흰색, 양수 = 빨강**이 됩니다. `vmin=-0.2, vmax=+0.2` 처럼 **대칭**으로 주어야 0이 정확히 흰색에 옵니다. `vmin=-0.05, vmax=0.2` 처럼 비대칭이면 0이 연한 파랑으로 보여 "재료 부족"으로 오해합니다. `jet`·`rainbow` 같은 무지개 컬러맵은 밝기가 고르지 않아 없는 경계가 보이므로 쓰지 않습니다.

**고정 범위와 범위 밖 값**: 색 범위를 ±0.2 mm로 고정하면 0.3 mm 같은 값은 가장 진한 빨강으로 잘립니다(clipping). 그래서 ① 컬러바 양 끝을 화살표(`extend="both"`)로 그려 "범위 밖 있음"을 표시하고 ② 잘린 비율(`clipped_pct`)을 CSV에 기록합니다. 잘린 비율이 1 %를 넘으면 범위를 바꾸지 말고 그 시편을 따로 확인합니다(범위는 전체 실험에서 하나).

**NaN의 색**: 측정이 안 된 칸이나 평가에서 뺀 칸(G4 `M_eval` 밖)은 **회색**으로 칠합니다. 흰색으로 두면 "오차 0"과 구분이 안 됩니다.

**마스크 오버레이**: 기준 마스크 `M_ref`(G코드가 재료를 요구한 곳)와 측정 마스크 `M_meas`(실제로 재료가 있는 곳)를 겹쳐 칠합니다. 청사진 J4 규칙: **기준만 = 파랑(미충진), 측정만 = 빨강(과충진), 겹침 = 회색.** 이 문서는 측정 무효 칸(NaN)을 **노랑**으로 추가 표시합니다. 윤곽 지표(H6)는 `M_valid` 만 적용하고 경계 띠(`M_edge`)는 빼지 않는다는 G4 규칙을 그림에도 그대로 씁니다.

**히스토그램**: 평가 영역 편차값들의 분포입니다. 공차선(±0.1 mm, 검정 점선), 평균(초록), P95|e|(주황)를 함께 그리면 "치우침 / 흩어짐 / 최악"을 한 그림으로 봅니다(청사진 A1: 평균 하나만 보고하지 않기). 막대 폭도 **0.005 mm로 고정**해야 시편끼리 모양을 비교할 수 있습니다.

**한글 글꼴**: matplotlib 기본 글꼴(DejaVu Sans)에는 한글이 없어 □□로 깨집니다. 이 문서의 그림은 **라벨을 영어로** 쓰고(논문 투고에도 유리), 한글이 꼭 필요하면 6.3절 글꼴 설정을 씁니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 / 위치 | 설명 |
|---|---|---|---|
| 입력 | 기준 높이맵 `H_ref` | `data/processed/<scan_id>/ref_height.npy` | G3, {G} 좌표계, 0.02 mm 격자 |
| 입력 | 측정 높이맵 `H_meas` | `data/processed/<scan_id>/meas_height.npy` | H1–H4 후, 같은 격자, 결측 = NaN |
| 입력 | 마스크 `M_ref`, `M_meas`, `M_valid`, `M_eval` | `masks.npz` (bool 배열 4개) | G4 정의 |
| 입력 | 격자 좌표 `xs`, `ys` | `grid.npz` | 칸 중심 좌표 [mm] |
| 입력 | 설정 | `config_resolved.yaml` | `tolerance_mm`, `edge_band_mm` (J2) |
| 산출물 | 편차 히트맵 | `results/<scan_id>/<scan_id>_heatmap.png` | 300 dpi, `RdBu_r`, ±0.2 mm 고정, NaN 회색 |
| 산출물 | 마스크 오버레이 | `<scan_id>_overlay.png` | 파랑/빨강/회색/노랑 |
| 산출물 | 편차 히스토그램 | `<scan_id>_hist.png` | 0.005 mm 구간 고정, 공차·평균·P95 선 |
| 산출물 | 단면 프로파일 | `<scan_id>_profile.png` | 기준 점선 vs 측정 실선 |
| 산출물 | 시편 지표 | `<scan_id>_metrics.csv` | 1행 19열 (아래 열 목록) |
| 산출물 | 전체 요약표 | `results/summary.csv` | 시편당 1행, 같은 `scan_id` 는 최신으로 교체 |
| 산출물 | 위치 오차 지도 | `results/position_quiver.png` | 핀 격자 화살표, 확대 배율 표기 |
| 산출물 | 조건 비교 | `results/condition_compare.png` | 시편 단위 요약값 점그림 |

`metrics.csv` 열: `scan_id, calibration_id, n, mean_mm, std_mm, rms_mm, mae_mm, p95_abs_mm, max_abs_mm, within_tol_pct, iou, dice, overfill_mm2, underfill_mm2, invalid_pct, eval_area_pct, clipped_pct, tol_mm, vlim_mm`

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 편차 컬러맵 | `jet` / `viridis` / **`RdBu_r`** / `coolwarm` | `RdBu_r` | 청사진 J4. 0 중심 발산형, 색약 사용자도 빨강/파랑 대비는 구분 가능 |
| 색 범위 | 시편별 자동 / **전체 고정 ±0.2 mm** | ±0.2 mm (= 공차 0.1 mm의 2배) | 시편 비교 가능. 공차 경계(±0.1)가 색 중간 밝기에 와서 눈에 잘 띔 |
| 범위 밖 값 | 숨김 / **컬러바 화살표 + 비율 기록** | `extend="both"` + `clipped_pct` | 잘린 사실을 숨기지 않음 |
| NaN 색 | 흰색 / **회색(0.75)** | 회색 | 흰색은 "오차 0"과 혼동 |
| 히트맵에 표시할 영역 | 전체 / **`M_eval` 만** | `M_eval` 만 (나머지 회색) | 지표 계산 영역과 그림 영역 일치 |
| 히스토그램 구간 | 자동 / **0.005 mm 고정, ±0.2 mm** | 고정 81개 경계 | 시편끼리 비교 |
| 오버레이 색 | — | 기준만 파랑, 측정만 빨강, 겹침 회색, 무효 노랑 | 청사진 J4 + 무효 영역 명시 |
| 그림 라벨 언어 | 한글 / **영어** | 영어 (+ 단위 `[mm]`) | 글꼴 문제 없음, 논문 그대로 사용 |
| 해상도·형식 | 100 dpi PNG / **300 dpi PNG** / PDF·SVG | 300 dpi PNG, 논문 최종본만 PDF 추가 | 청사진 J4 "300 dpi 이상" |
| 요약표 갱신 | 무조건 추가 / **같은 scan_id 교체** | 교체 | 재처리 시 중복 행 방지 (H8 표본 수 왜곡 방지) |
| 조건 비교 그림 | 점 수십만 개 상자그림 / **시편 단위 점그림** | 1점 = 1시편 + 평균 막대 | H8 유사반복 방지, n이 작을 때(3) 상자그림은 오해 소지 |
| 위치 오차 화살표 | 실제 크기 / **확대(×50)** + 범례 화살표 | ×50, 0.1 mm 기준 화살표 | 0.1 mm 오차는 20 mm 격자에서 안 보임. 배율은 반드시 그림에 표기 |
| PDF 묶음 보고서 | 지금 / **나중(선택)** | M4는 PNG+CSV, PDF는 W22 이후 필요 시 | 초보 팀 작업량 조절 |

## 5. 수행 절차

**1단계 (W13, 1일차) — 데이터 연결 확인**
- [ ] 한 시편(`S01_r01`)의 `H_ref`, `H_meas`, 마스크 4개, `xs`, `ys` 를 불러와 shape가 모두 같은지 확인 (예: 700×700).
- [ ] `H_meas` 의 결측이 NaN인지(0이 아닌지), 단위가 mm인지(최댓값 ≈ 시편 높이) 확인.

**2단계 (W13, 1–2일차) — 리포트 모듈**
- [ ] 6.1절 `report.py` 를 `src/cvlab/report.py` 로 저장.
- [ ] `python report.py` 로 합성 데모 실행 → `results/` 아래 PNG 8장, CSV 3개 생성 확인.
- [ ] 히트맵을 열어 **0 근처가 흰색**, 양수가 빨강인지 확인. S01(+0.03 mm 과다)은 연한 빨강, S02(−0.06 mm 부족)는 연한 파랑이어야 함.

**3단계 (W13, 3일차) — 색 규칙 검증**
- [ ] 6.4절 테스트 실행 → `2 passed`.
- [ ] 두 시편 히트맵을 나란히 놓고 컬러바 눈금이 **완전히 같은지**(−0.20 ~ +0.20) 확인.
- [ ] 의도적으로 +0.3 mm 영역을 넣은 합성 시편으로 `clipped_pct > 0`, 컬러바 화살표가 보이는지 확인.

**4단계 (W13, 4–5일차) — 실제 파이프라인 연결**
- [ ] J1 `run_pipeline.py` 에 `report` 단계 추가: 입력 = `ref_height.npy`, `meas_height.npy`, `masks.npz`, 출력 = `<scan_id>_metrics.csv` 외 PNG 4장.
- [ ] `meta` 인자에 J2 manifest의 `calibration_id`, `git.commit`, 시편 조건(속도·온도 등)을 넣어 요약표 열로 남김.
- [ ] 단면 위치 `profile_y_mm` 를 시편 설계(E3)에 맞게 설정 (예: 계단 피라미드 중심선).

**5단계 (W14, 1–2일차) — 추가 그림 2종**
- [ ] 6.2절 `figures_extra.py` 로 위치 오차 화살표 지도(핀 격자 5×5, 간격 20 mm)와 조건 비교 점그림 작성.
- [ ] 화살표 배율(×50)과 0.1 mm 기준 화살표가 그림 안에 있는지 확인.
- [ ] 조건 비교 그림의 y축이 0에서 시작하는지(차이 과장 방지) 확인.

**6단계 (W14, 3일차) — 실측 시편 1개 완주 (M4)**
- [ ] 실측 시편 1개를 J1 실행기로 처음부터 끝까지 처리 → 리포트 묶음 생성.
- [ ] 리포트를 보고 "이상해 보이는 곳"을 3개 이상 적고, 각각이 측정 문제(E1·E2)인지 공정 오차인지 1차 판단.
- [ ] `eval_area_pct` 가 80 % 미만이면 G4 평가 영역과 E2 가림을 재검토하고 보고서에 함께 적기.

**7단계 (W14, 4–5일차) — 리포트 점검표 운영**
- [ ] 10절 리포트 점검표를 매 시편 적용.
- [ ] `summary.csv` 열 이름·단위를 논문 표(K5) 형식과 맞춤.

## 6. Python 구현

### 6.1 시편 리포트 — `src/cvlab/report.py`

```python
"""report.py — 시편 1개의 그림 4장 + 지표 CSV + 전체 요약표 한 줄 (J4).

실행:  python report.py            → 합성 시편 2개(S01_r01, S02_r01)로 데모 리포트 생성
실제 사용: report_specimen(...) 에 H_ref, H_meas, 마스크를 넘기면 된다.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")                     # 화면 없이 파일로만 저장 (서버·스크립트용)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapely
from scipy import ndimage
from shapely.geometry import box
from shapely.ops import unary_union

DPI = 300                                 # 논문용 그림 최소 해상도 (청사진 J4)
VLIM_MM = 0.2                             # 히트맵 색 범위 ±0.2 mm — 모든 시편 공통 고정


# ---------------------------------------------------------------- 지표
def height_metrics(e, tol):
    """e: 평가 영역 편차(1D, NaN 없음). 청사진 H5 지표."""
    return {
        "n": int(e.size),
        "mean_mm": float(e.mean()),
        "std_mm": float(e.std(ddof=1)),
        "rms_mm": float(np.sqrt((e ** 2).mean())),
        "mae_mm": float(np.abs(e).mean()),
        "p95_abs_mm": float(np.percentile(np.abs(e), 95)),
        "max_abs_mm": float(np.abs(e).max()),
        "within_tol_pct": float(100 * (np.abs(e) <= tol).mean()),
    }


def iou_dice(A, B):
    inter, union = (A & B).sum(), (A | B).sum()
    return inter / union, 2 * inter / (A.sum() + B.sum())


# ---------------------------------------------------------------- 그림 4종
def plot_deviation_heatmap(dev, extent, path, title, vlim=VLIM_MM):
    """발산형 히트맵: 0 = 흰색, ±vlim 고정, NaN(평가 제외·결측) = 회색."""
    cmap = plt.get_cmap("RdBu_r").with_extremes(bad="0.75")   # NaN 칸 = 밝은 회색
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    im = ax.imshow(dev, cmap=cmap, vmin=-vlim, vmax=vlim, origin="lower",
                   extent=extent, interpolation="nearest")
    cb = fig.colorbar(im, ax=ax, extend="both")   # 범위 밖 값은 끝 화살표로 표시
    cb.set_label("Deviation (meas - ref) [mm]   + = excess")
    ax.set_xlabel("X [mm]"); ax.set_ylabel("Y [mm]")
    ax.set_title(title, fontsize=9)
    ax.set_aspect("equal")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def plot_mask_overlay(M_ref, M_meas, M_valid, extent, path, title):
    """기준만 = 파랑, 측정만 = 빨강, 겹침 = 회색, 둘 다 없음 = 흰색, 측정 무효(NaN) = 노랑."""
    rgb = np.ones(M_ref.shape + (3,))
    M_ref, M_meas = M_ref & M_valid, M_meas & M_valid          # 무효 칸은 비교에서 제외 (G4)
    rgb[M_ref & M_meas] = (0.55, 0.55, 0.55)
    rgb[M_ref & ~M_meas] = (0.15, 0.35, 0.85)    # 미충진 (있어야 하는데 없음)
    rgb[~M_ref & M_meas] = (0.85, 0.15, 0.15)    # 과충진 (없어야 하는데 있음)
    rgb[~M_valid] = (1.0, 0.85, 0.3)             # 측정 무효 (결측·가림)
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.imshow(rgb, origin="lower", extent=extent, interpolation="nearest")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=(0.15, 0.35, 0.85), label="ref only (under-fill)"),
                       Patch(color=(0.85, 0.15, 0.15), label="meas only (over-fill)"),
                       Patch(color=(0.55, 0.55, 0.55), label="both"),
                       Patch(color=(1.0, 0.85, 0.3), label="invalid (NaN)")],
              loc="upper right", fontsize=7)
    ax.set_xlabel("X [mm]"); ax.set_ylabel("Y [mm]"); ax.set_title(title, fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def plot_histogram(e, m, tol, path, title, vlim=VLIM_MM):
    """편차 분포 + 공차선(±tol, 검정 점선) + 평균(초록) + P95(주황)."""
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    bins = np.linspace(-vlim, vlim, 81)                     # 0.005 mm 폭 고정 → 시편끼리 비교 가능
    ax.hist(np.clip(e, -vlim, vlim), bins=bins, color="0.6")
    for x in (-tol, tol):
        ax.axvline(x, color="k", ls="--", lw=1, label=f"tol ±{tol}" if x > 0 else None)
    ax.axvline(m["mean_mm"], color="tab:green", lw=1.5, label=f"mean {m['mean_mm']:+.4f}")
    for s in (-1, 1):
        ax.axvline(s * m["p95_abs_mm"], color="tab:orange", lw=1.2,
                   label=f"P95|e| {m['p95_abs_mm']:.4f}" if s == 1 else None)
    ax.set_xlabel("Deviation (meas - ref) [mm]"); ax.set_ylabel("Count (grid cells)")
    ax.set_title(title + f"   tol ±{tol} mm, in-tol {m['within_tol_pct']:.1f} %", fontsize=8)
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def plot_profile(H_ref, H_meas, xs, ys, y_mm, path, title):
    """한 행(Y = y_mm) 단면: 기준 점선, 측정 실선."""
    r = int(np.argmin(np.abs(ys - y_mm)))
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ax.plot(xs, H_ref[r], "k--", lw=1, label="reference (G-code)")
    ax.plot(xs, H_meas[r], "tab:red", lw=0.8, label="measured")
    ax.set_xlabel("X [mm]"); ax.set_ylabel("Z [mm]")
    ax.set_title(title + f"   profile at Y = {ys[r]:.2f} mm", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


# ---------------------------------------------------------------- 리포트
def report_specimen(scan_id, H_ref, H_meas, M_ref, M_meas, M_valid, M_eval, xs, ys,
                    out_root, tol=0.1, meta=None, profile_y_mm=3.5):
    """시편 1개 → results/<scan_id>/ 에 PNG 4장 + metrics.csv, results/summary.csv 갱신."""
    out = Path(out_root) / scan_id
    out.mkdir(parents=True, exist_ok=True)
    res = xs[1] - xs[0]
    extent = (xs[0] - res / 2, xs[-1] + res / 2, ys[0] - res / 2, ys[-1] + res / 2)

    dev = H_meas - H_ref
    dev_eval = np.where(M_eval, dev, np.nan)                  # 평가 영역 밖은 NaN(회색)
    e = dev_eval[~np.isnan(dev_eval)]
    m = height_metrics(e, tol)
    A, B = M_ref & M_valid, M_meas & M_valid                  # 윤곽 지표: M_valid 적용, M_edge 미적용
    iou, dice = iou_dice(A, B)
    cell = res * res
    row = {"scan_id": scan_id, **(meta or {}), **m,
           "iou": float(iou), "dice": float(dice),
           "overfill_mm2": float((B & ~A).sum() * cell),
           "underfill_mm2": float((A & ~B).sum() * cell),
           "invalid_pct": float(100 * (~M_valid).mean()),
           "eval_area_pct": float(100 * M_eval.sum() / M_ref.sum()),   # 평가 영역 비율 (G4)
           "clipped_pct": float(100 * (np.abs(e) > VLIM_MM).mean()),   # 색 범위 밖 비율
           "tol_mm": tol, "vlim_mm": VLIM_MM}

    t = f"{scan_id}"
    plot_deviation_heatmap(dev_eval, extent, out / f"{scan_id}_heatmap.png", t)
    plot_mask_overlay(M_ref, M_meas, M_valid, extent, out / f"{scan_id}_overlay.png", t)
    plot_histogram(e, m, tol, out / f"{scan_id}_hist.png", t)
    plot_profile(H_ref, H_meas, xs, ys, profile_y_mm, out / f"{scan_id}_profile.png", t)

    pd.DataFrame([row]).to_csv(out / f"{scan_id}_metrics.csv", index=False, float_format="%.5f")
    summary = Path(out_root) / "summary.csv"
    df = pd.DataFrame([row])
    if summary.exists():                                      # 같은 scan_id 는 최신 결과로 교체
        old = pd.read_csv(summary)
        df = pd.concat([old[old["scan_id"] != scan_id], df], ignore_index=True)
    df.to_csv(summary, index=False, float_format="%.5f")
    return row


# ---------------------------------------------------------------- 합성 데모 데이터
def demo_specimen(seed, overfill_mm, dz_mm, tilt_mm_per_mm, res=0.02):
    rng = np.random.default_rng(seed)
    n = int(round(14 / res))
    xs = ys = (np.arange(n) + 0.5) * res
    X, Y = np.meshgrid(xs, ys)
    ref = unary_union([box(2, 2, 12, 5), box(2, 2, 5, 12)])   # L자 블록 윤곽
    meas = ref.buffer(overfill_mm, join_style="mitre")         # 윤곽이 overfill 만큼 커짐
    M_ref, inside = shapely.contains_xy(ref, X, Y), shapely.contains_xy(meas, X, Y)
    H_ref = np.where(M_ref, 2.0, 0.0)
    H_meas = np.where(inside, 2.0 + dz_mm + tilt_mm_per_mm * (X - 7), 0.0)
    H_meas += rng.normal(0, 0.005, H_meas.shape)
    H_meas[rng.random(H_meas.shape) < 0.02] = np.nan            # 결측 2 %
    valid = ~np.isnan(H_meas)
    M_meas = (H_meas > 1.0) & valid
    edge_px = int(round(0.25 / res))                            # 경계 띠 0.25 mm (G4 M_edge)
    M_eval = ndimage.binary_erosion(M_ref, iterations=edge_px) & valid
    return H_ref, H_meas, M_ref, M_meas, valid, M_eval, xs, ys


if __name__ == "__main__":
    out_root = Path("results")
    cases = {"S01_r01": (0, 0.05, 0.03, 0.004), "S02_r01": (1, 0.10, -0.06, -0.008)}
    for sid, (seed, of, dz, tilt) in cases.items():
        H_ref, H_meas, M_ref, M_meas, M_valid, M_eval, xs, ys = demo_specimen(seed, of, dz, tilt)
        row = report_specimen(sid, H_ref, H_meas, M_ref, M_meas, M_valid, M_eval, xs, ys, out_root,
                              tol=0.1, meta={"calibration_id": "CAL-2026-10-06-A"})
        print(f"{sid}: mean {row['mean_mm']:+.4f}  RMS {row['rms_mm']:.4f}  "
              f"P95 {row['p95_abs_mm']:.4f}  IoU {row['iou']:.4f}  과충진 {row['overfill_mm2']:.2f} mm²  "
              f"평가영역 {row['eval_area_pct']:.1f} %  범위밖 {row['clipped_pct']:.2f} %")
    for p in sorted(out_root.rglob("*")):
        if p.is_file():
            print(f"  {p}  {p.stat().st_size / 1024:.0f} KB")
```

실행 예시와 기대 출력:
```text
$ python report.py
S01_r01: mean +0.0241  RMS 0.0270  P95 0.0468  IoU 0.9695  과충진 1.57 mm²  평가영역 80.0 %  범위밖 0.00 %
S02_r01: mean -0.0481  RMS 0.0532  P95 0.0918  IoU 0.9266  과충진 3.96 mm²  평가영역 80.1 %  범위밖 0.00 %
  results/S01_r01/S01_r01_heatmap.png  315 KB
  results/S01_r01/S01_r01_hist.png  105 KB
  results/S01_r01/S01_r01_metrics.csv  0 KB
  results/S01_r01/S01_r01_overlay.png  106 KB
  results/S01_r01/S01_r01_profile.png  79 KB
  results/S02_r01/S02_r01_heatmap.png  322 KB
  results/S02_r01/S02_r01_hist.png  101 KB
  results/S02_r01/S02_r01_metrics.csv  0 KB
  results/S02_r01/S02_r01_overlay.png  107 KB
  results/S02_r01/S02_r01_profile.png  81 KB
  results/summary.csv  0 KB
```
`results/S01_r01/S01_r01_metrics.csv`:
```text
scan_id,calibration_id,n,mean_mm,std_mm,rms_mm,mae_mm,p95_abs_mm,max_abs_mm,within_tol_pct,iou,dice,overfill_mm2,underfill_mm2,invalid_pct,eval_area_pct,clipped_pct,tol_mm,vlim_mm
S01_r01,CAL-2026-10-06-A,102018,0.02410,0.01207,0.02695,0.02410,0.04679,0.06948,100.00000,0.96952,0.98452,1.57120,0.00000,2.02837,80.01412,0.00000,0.10000,0.20000
```
PNG는 1560×1260 픽셀, 300 dpi(5.2×4.2 inch)로 저장됩니다.

**결과 읽는 법 (S01_r01)**
- 합성 조건: 높이 +0.03 mm, X 방향 기울기 0.004 mm/mm, 윤곽 0.05 mm 확대(과충진), 노이즈 5 µm, 결측 2 %.
- `mean_mm = +0.0241`: L자 블록의 평가 영역 평균 X가 7 mm 중심보다 왼쪽에 있어서 기울기 성분이 평균을 0.006 mm 끌어내림 → 0.03 − 0.006 ≈ 0.024. **평균 하나만 보면 기울기를 놓칩니다** → 히트맵에서 왼쪽→오른쪽으로 진해지는 빨강으로 보입니다.
- `overfill_mm2 = 1.57`: 둘레 40 mm × 0.05 mm = 2.0 mm²가 기대값이지만, 0.02 mm 격자에서는 0.05 mm 확대가 **2칸(0.04 mm)** 으로만 잡혀 40 × 0.04 × 0.98(유효 칸) ≈ 1.57 mm²입니다. **격자 간격보다 작은 윤곽 오차는 칸 단위로 양자화된다**는 점을 보고서 한계에 적습니다(청사진 H6 주의 사항과 같은 맥락).
- `underfill_mm2 = 0`: 윤곽을 키우기만 했으므로 미충진이 없어야 정상 → 결측(NaN)을 미충진으로 잘못 세지 않았다는 확인이기도 합니다.
- `eval_area_pct = 80.0`: 경계 0.25 mm 띠를 빼고 결측 2 %를 빼면 기준 면적의 80 %만 높이 지표에 쓰였다는 뜻입니다(G4: 평가 영역 비율 항상 보고).

### 6.2 추가 그림 — `scripts/figures_extra.py`

```python
"""figures_extra.py — 위치 오차 화살표 지도 + 조건 비교 점그림 (J4 표의 나머지 2종).

실행: python figures_extra.py  → results/position_quiver.png, results/condition_compare.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path("results")
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(0)

# ---- 1) 위치 오차 지도: 5×5 핀 격자, 간격 20 mm (E3), 오차 = 측정 중심 − G코드 중심
gx, gy = np.meshgrid(np.arange(5) * 20.0 + 20, np.arange(5) * 20.0 + 20)
# 합성 예: 수축 0.4 % (중심 (60, 60) 쪽으로 끌려감) + X 방향 0.05 mm 치우침 + 노이즈 10 µm
dx = -0.004 * (gx - 60) + 0.05 + rng.normal(0, 0.01, gx.shape)
dy = -0.004 * (gy - 60) + rng.normal(0, 0.01, gy.shape)
SCALE = 50                                    # 화살표 확대 배율 — 그림에 반드시 표시
fig, ax = plt.subplots(figsize=(4.8, 4.6))
ax.plot(gx, gy, "k+", ms=6)
q = ax.quiver(gx, gy, dx * SCALE, dy * SCALE, angles="xy", scale_units="xy", scale=1,
              color="tab:red", width=0.006)
ax.quiverkey(q, 0.72, 0.04, 0.1 * SCALE, "0.1 mm", labelpos="E", coordinates="axes")
ax.set_xlim(5, 115); ax.set_ylim(5, 115); ax.set_aspect("equal")
ax.set_xlabel("X [mm] (G-code frame)"); ax.set_ylabel("Y [mm]")
ax.set_title(f"Position error (meas - ref), arrows x{SCALE}", fontsize=9, loc="left")
fig.tight_layout(); fig.savefig(OUT / "position_quiver.png", dpi=300); plt.close(fig)
print(f"위치 오차 RMS = {np.sqrt((dx**2 + dy**2).mean()) * 1000:.1f} µm, "
      f"최대 = {np.hypot(dx, dy).max() * 1000:.1f} µm")

# ---- 2) 조건 비교: 시편 단위 요약값(RMS)만 점으로 (H8 유사반복 방지)
df = pd.DataFrame({
    "condition": np.repeat(["speed40", "speed60", "speed80"], 3),
    "specimen": [f"S{i:02d}" for i in range(1, 10)],
    "rms_mm": np.r_[rng.normal(0.025, 0.003, 3), rng.normal(0.032, 0.003, 3),
                    rng.normal(0.045, 0.004, 3)],
})
conds = list(dict.fromkeys(df["condition"]))
fig, ax = plt.subplots(figsize=(4.8, 3.4))
for i, c in enumerate(conds):
    v = df.loc[df["condition"] == c, "rms_mm"].to_numpy()
    ax.plot(np.full(v.size, i) + rng.uniform(-0.08, 0.08, v.size), v, "o",
            color="tab:blue", alpha=0.8)
    ax.hlines(v.mean(), i - 0.25, i + 0.25, color="k", lw=2)          # 평균 막대
ax.set_xticks(range(len(conds)), conds)
ax.set_ylim(0, None)                                                   # 0 기준 → 과장 방지
ax.set_ylabel("Height RMS per specimen [mm]")
ax.set_title("n = 3 specimens per condition (1 dot = 1 specimen)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "condition_compare.png", dpi=300); plt.close(fig)
print(df.groupby("condition")["rms_mm"].agg(["count", "mean", "std"]).round(4))
```

실행 예시:
```text
$ python figures_extra.py
위치 오차 RMS = 164.6 µm, 최대 = 265.6 µm
           count    mean     std
condition                       
speed40        3  0.0241  0.0025
speed60        3  0.0318  0.0032
speed80        3  0.0449  0.0041
```
위치 오차 지도에서 화살표가 모두 중앙(60, 60) 쪽을 향하면 **수축(배율 < 1)**, 모두 같은 방향이면 **평행 이동**입니다. 이 예는 0.4 % 수축 + X 방향 0.05 mm 이동을 넣었으므로, 화살표가 중앙을 향하면서 전체가 약간 오른쪽으로 치우쳐 보입니다(H4 배율·위치 오차 분리 보고와 대응).

### 6.3 (선택) 한글 글꼴 설정

```python
"""korean_font.py — 그림에 한글 라벨을 쓰고 싶을 때 (선택)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# OS별 대표 한글 글꼴: Windows = Malgun Gothic, macOS = AppleGothic, Linux = NanumGothic(설치 필요)
candidates = ["Malgun Gothic", "AppleGothic", "NanumGothic"]
installed = {f.name for f in font_manager.fontManager.ttflist}
found = [c for c in candidates if c in installed]
if found:
    plt.rcParams["font.family"] = found[0]
    plt.rcParams["axes.unicode_minus"] = False      # 한글 글꼴에서 '−' 기호 깨짐 방지
    print("한글 글꼴 사용:", found[0])
else:
    print("한글 글꼴 없음 → 그림 라벨은 영어로 유지 (기본 DejaVu Sans)")
```

실행 예시 (한글 글꼴이 없는 Linux 서버):
```text
한글 글꼴 없음 → 그림 라벨은 영어로 유지 (기본 DejaVu Sans)
```
Windows에서는 `한글 글꼴 사용: Malgun Gothic` 이 출력됩니다. 이 코드는 `report.py` 의 `matplotlib.use("Agg")` 바로 아래에 붙여 씁니다.

### 6.4 테스트 — `tests/test_report.py`

```python
"""J4 리포트 테스트: 파일이 생기는지, 요약표가 중복 없이 갱신되는지, 색 규칙이 지켜지는지."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from report import VLIM_MM, demo_specimen, report_specimen


def test_files_and_summary(tmp_path):
    data = demo_specimen(seed=0, overfill_mm=0.05, dz_mm=0.03, tilt_mm_per_mm=0.0)
    for _ in range(2):                                   # 같은 시편을 두 번 리포트
        row = report_specimen("S01_r01", *data, out_root=tmp_path, tol=0.1)
    d = tmp_path / "S01_r01"
    for kind in ("heatmap", "overlay", "hist", "profile"):
        p = d / f"S01_r01_{kind}.png"
        assert p.exists() and p.stat().st_size > 10_000   # 빈 그림이 아님
    assert (d / "S01_r01_metrics.csv").exists()
    summary = pd.read_csv(tmp_path / "summary.csv")
    assert len(summary) == 1                             # 중복 행 없음
    assert abs(row["mean_mm"] - 0.03) < 0.002            # 넣은 +0.03 mm 복원 (부호 + = 과다)
    assert row["underfill_mm2"] == 0.0                   # 윤곽을 키웠으므로 미충진 없음


def test_zero_is_white_and_range_symmetric():
    c = plt.get_cmap("RdBu_r")(0.5)                      # vmin=-v, vmax=+v 에서 0 의 위치
    assert min(c[:3]) > 0.95                             # 거의 흰색
    assert VLIM_MM == 0.2
```

실행 예시:
```text
$ python -m pytest tests/test_report.py -q
..                                                                       [100%]
2 passed in 4.91s
```

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 파일 생성 | `report_specimen` 1회 | PNG 4장(각 > 10 KB) + `metrics.csv` 1개 + `summary.csv` 갱신 |
| 해상도 | PNG 속성 확인 | 300 dpi, 축 라벨 전부에 단위(`[mm]`) |
| 0 = 흰색 | 컬러맵 0.5 위치 RGB | 세 채널 모두 > 0.95 (테스트 통과) |
| 범위 고정 | 서로 다른 시편 2개 히트맵 | 컬러바 −0.20 ~ +0.20 동일 |
| 부호 | +0.03 mm 합성 시편 | `mean_mm` = +0.030 ± 0.002, 히트맵 빨강 |
| NaN 표시 | 결측 2 % 합성 시편 | 히트맵 회색 점, 오버레이 노랑 점, `invalid_pct` ≈ 2.0 |
| 결측 ≠ 미충진 | 윤곽 확대만 한 시편 | `underfill_mm2` = 0 |
| 요약표 중복 | 같은 시편 2회 리포트 | `summary.csv` 행 수 1 |
| 범위 밖 표시 | +0.3 mm 영역 포함 시편 | `clipped_pct` > 0, 컬러바 끝 화살표 |
| 처리 시간 | 700×700 시편 1개 | ≤ 10 s (그림 4장 포함) |
| M4 | 실측 시편 1개 | J1 실행기 한 번으로 리포트 묶음 완성, 10절 점검표 전 항목 체크 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| `imshow` 기본 컬러맵(viridis) 사용 | + / − 구분이 안 됨 | `cmap="RdBu_r"` 명시 |
| `vmin`, `vmax` 미지정 | 시편마다 색 범위가 달라 비교 불가, 노이즈만 있는 시편도 진한 색 | `vmin=-0.2, vmax=0.2` 고정 |
| 비대칭 범위 | 0이 흰색이 아님 → 정상 영역이 부족처럼 보임 | 항상 ±같은 값 |
| `RdBu` (뒤집지 않음) 사용 | 빨강 = 부족으로 반대 의미 | `RdBu_r`, 컬러바 라벨에 "+ = excess" |
| `origin` 미지정 | Y축이 뒤집혀 그림이 상하 반전 | `origin="lower"` + `extent` (mm) |
| NaN을 0으로 채운 뒤 그림 | 결측 영역이 흰색(오차 0)으로 보임 | NaN 유지, `with_extremes(bad=...)` 로 회색 |
| 결측을 미충진으로 계산 | `underfill_mm2` 과대, IoU 과소 | 윤곽 지표 전에 `M_ref & M_valid`, `M_meas & M_valid` |
| 히스토그램 구간 자동 | 시편마다 막대 폭이 달라 모양 비교 불가 | `np.linspace(-0.2, 0.2, 81)` 고정 |
| `plt.close` 누락 | 시편 수십 개 처리 시 메모리 부족 경고 | 저장 직후 `plt.close(fig)` |
| `plt.show()` 를 스크립트에 둠 | 창이 뜨고 멈춤, 서버에서 에러 | `matplotlib.use("Agg")` + `savefig` 만 |
| 72 dpi로 저장 | 논문 심사에서 해상도 지적 | `dpi=300` |
| 요약표에 행을 계속 추가 | 같은 시편이 여러 번 → H8 표본 수 부풀림 | `scan_id` 기준 교체 |
| 화살표 배율 미표기 | 0.1 mm 오차가 10 mm처럼 보여 오해 | 제목에 "×50", 기준 화살표 `quiverkey` |
| y축이 0에서 시작하지 않는 막대·점그림 | 조건 간 작은 차이가 과장됨 | `set_ylim(0, None)` |

## 9. 위험 요소

- **±0.2 mm가 실제 오차에 맞지 않을 가능성**: 실측 결과가 대부분 ±0.02 mm 안이면 히트맵이 거의 흰색이 됩니다. W14에 실측 시편 3개를 본 뒤 **한 번만** 범위를 정하고(예: ±0.1 mm), 본 실험 내내 고정합니다. 바꾸면 이전 그림을 모두 다시 생성합니다. 범위는 J2 설정(`vlim_mm`)으로 옮기는 것을 권장합니다.
- **그림만 보고 결론**: 히트맵은 공간 분포를 보는 도구일 뿐이고, 결론은 `summary.csv` 숫자 + 불확도(I1)로 냅니다. 히트맵의 연한 색 차이가 확장불확도(예시 16 µm)보다 작으면 의미를 두지 않습니다.
- **색각 이상**: 빨강·초록 조합은 피하고(히스토그램 평균선 초록은 단독 선이라 허용), 중요한 구분은 선 모양(점선/실선)과 라벨로도 표시합니다.
- **대용량 그림**: 0.02 mm 격자로 50×50 mm 시편이면 2500×2500 칸입니다. 300 dpi 5 inch 그림(1500 픽셀)보다 칸이 많아 일부가 생략되어 보입니다. 국부 확대 그림을 추가하거나 `interpolation="nearest"` 를 유지해 값이 섞이지 않게 합니다.
- **요약표 열 변경**: 열을 추가·삭제하면 이전 행과 합칠 때 빈 칸이 생깁니다. 열 목록을 J2 설정처럼 고정하고, 바꿀 때는 모든 시편을 재처리합니다.

## 10. 기록 양식

**시편 리포트 점검표** (시편마다 1부, `results/<scan_id>/CHECK.md`)

| # | 항목 | 확인 |
|---|---|---|
| 1 | 히트맵 컬러바 −0.20 ~ +0.20 mm, 라벨에 "+ = excess" | [ ] |
| 2 | 0 근처가 흰색, NaN이 회색 | [ ] |
| 3 | 오버레이 4색(파랑·빨강·회색·노랑) 범례 있음 | [ ] |
| 4 | 히스토그램에 공차선·평균·P95 표시 | [ ] |
| 5 | 단면 위치(Y mm)가 제목에 있음 | [ ] |
| 6 | `eval_area_pct` ≥ 80 % (미만이면 사유 기록) | [ ] |
| 7 | `clipped_pct` ≤ 1 % (초과면 사유 기록) | [ ] |
| 8 | `calibration_id`, git 커밋이 요약표·manifest에 있음 | [ ] |
| 9 | 이상 부위 메모 (위치, 추정 원인: 측정 / 공정) | |

**요약표 열 정의** (`results/summary_columns.csv`)
```csv
column,unit,source_element,description
scan_id,-,F3,시편ID_반복번호
calibration_id,-,D5,캘리브레이션 ID
n,cells,H5,평가 칸 수
mean_mm,mm,H5,평균 편차 (측정-기준, +=과다)
std_mm,mm,H5,표준편차 (ddof=1)
rms_mm,mm,H5,RMS
mae_mm,mm,H5,평균 절대 오차
p95_abs_mm,mm,H5,|e| 95 백분위수
max_abs_mm,mm,H5,|e| 최댓값
within_tol_pct,%,H5,공차 만족률
iou,-,H6,M_valid 적용 IoU
dice,-,H6,Dice
overfill_mm2,mm2,H6,과충진 면적
underfill_mm2,mm2,H6,미충진 면적
invalid_pct,%,G4,측정 무효 칸 비율 (전체 격자 대비)
eval_area_pct,%,G4,평가 영역 / 기준 영역
clipped_pct,%,J4,색 범위 밖 비율
tol_mm,mm,J2,적용 공차
vlim_mm,mm,J4,히트맵 색 범위
```

**그림 ↔ 논문 대응표** (K5)

| 논문 그림/표 번호 | 파일 | scan_id | 결과 폴더 (J2) | 비고 |
|---|---|---|---|---|
| | | | | |

## 11. 참고 자료

- Matplotlib 문서 — "Choosing Colormaps in Matplotlib" (순차형·발산형·범주형 분류, `RdBu`, 무지개 컬러맵 문제)
- Matplotlib 문서 — `matplotlib.pyplot.imshow` (`origin`, `extent`, `interpolation`), `Figure.colorbar` (`extend`), `Axes.quiver`, `Axes.quiverkey`, `Colormap.with_extremes`
- Matplotlib 문서 — "Backends" (`Agg` 비대화형 백엔드)
- pandas 문서 — "10 minutes to pandas", `DataFrame.to_csv`, `pandas.concat`
- Crameri, Shephard, Heron, "The misuse of colour in science communication", Nature Communications (2020)
- Rougier, Droettboom, Bourne, "Ten Simple Rules for Better Figures", PLOS Computational Biology (2014)
