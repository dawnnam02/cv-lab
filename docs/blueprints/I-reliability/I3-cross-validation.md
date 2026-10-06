# I3. 독립 장비와의 교차검증

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: I. 측정 신뢰성 검증

| 항목 | 내용 |
|---|---|
| 기간 | 2027-02-02 ~ 2027-03-01 (W18-21) |
| 우선순위 | 보통 |
| 트랙 | 실험·품질 |
| 선행 요소 | [I1 측정 불확도](I1-uncertainty.md) · [I2 MSA](I2-msa.md) · [E3 시편 설계](../E-specimen/E3-test-artifact.md) · [H5 높이 지표](../H-analysis/H5-height-metrics.md) · [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) · [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) |
| 후행 요소 | [H8 통계 분석](../H-analysis/H8-statistics.md) · [K5 산출물·논문](../K-management/K5-deliverables-paper.md) |
| 관련 마일스톤 | M6 (최종 보고서) |

## 1. 목적

I1(불확도)과 I2(MSA)는 **우리 장비 스스로** 평가한 결과입니다. 빠진 요인이 있어도 스스로는 알기 어렵습니다. I3는 **원리가 다른 독립 장비**(접촉식 마이크로미터, 하이트 게이지, CMM, 공초점 현미경 등)로 같은 시편의 같은 형상을 재서, 두 결과가 **불확도 범위 안에서 일치하는지** 확인합니다.

구체적인 목표
1. 레이저 삼각측량 결과와 기준 장비 결과의 **평균 차이(계통 차이)** 와 **일치 한계(LoA)** 를 µm 단위로 제시 (Bland–Altman).
2. I1에서 구한 U가 현실적인지 확인: 차이의 약 95 %가 `±√(U_laser² + U_ref²)` 안에 들어와야 합니다 (E_n 수 ≤ 1).
3. 표면(PLA, E1)에서만 생기는 차이가 있는지, 형상 크기에 따라 차이가 커지는지(비례 치우침) 확인.
4. 논문 5장 "측정 시스템 검증"의 핵심 그림 1장(Bland–Altman 플롯)과 표 1개를 만듭니다 (K5).

## 2. 배경 지식 (초보자용)

### 2.1 상관계수만으로는 부족합니다

두 장비 값을 산점도로 그리면 거의 일직선(r = 0.999)이 나오는 경우가 많습니다. 하지만 **모든 값이 0.05 mm씩 크게 나와도 r = 0.999** 입니다. 상관은 "같이 움직이는지"를 볼 뿐 "같은 값을 주는지"를 보지 않습니다. 형상 크기 범위(0.2~5 mm)가 넓으면 상관은 저절로 커집니다. 그래서 BLUEPRINT는 **Bland–Altman 방법**을 씁니다.

### 2.2 Bland–Altman 방법 (1986)

같은 대상 i를 두 장비로 잰 값 (L_i, R_i) 에 대해

```
차이     d_i = L_i − R_i           (부호: 레이저 − 기준. + 면 레이저가 크게 잼)
평균     m_i = (L_i + R_i) / 2
평균 차이   d̄ = mean(d)            → 계통 차이 (치우침)
차이 SD    s = std(d, ddof=1)      → 무작위 불일치
일치 한계   LoA = d̄ ± 1.96·s      → 새 측정 쌍의 약 95 %가 들어갈 범위
```

- 그림: 가로축 m_i, 세로축 d_i. 선 3개(d̄, 상·하 LoA)를 그립니다.
- **d̄ 의 95 % CI**: `d̄ ± t·s/√n`. 0을 포함하지 않으면 계통 차이가 있다는 뜻입니다.
- **LoA 의 95 % CI**: 표준오차 `√(3s²/n)` 를 써서 `LoA ± t·√(3s²/n)` (Bland & Altman 1986의 근사).
- **비례 치우침**: d를 m에 회귀했을 때 기울기가 0과 다르면 "크기가 클수록 차이가 커짐"을 뜻합니다. 원인은 보통 배율 오차(D3, D2)입니다.

### 2.3 일치 여부를 정하는 기준 (사전에 정함)

Bland–Altman 방법은 "얼마나 다른가"를 보여 줄 뿐, 합격 기준은 **측정 전에** 정해야 합니다. 이 과제에서는 불확도를 기준으로 씁니다.

```
E_n = (L − R) / √(U_laser² + U_ref²)        U: k = 2 확장불확도
|E_n| ≤ 1  → 두 결과가 불확도 안에서 일치
```

E_n 수는 숙련도 시험(ISO/IEC 17043)에서 쓰는 표준 지표입니다. I1 예산이 맞다면 쌍의 약 95 %가 |E_n| ≤ 1 이어야 합니다. 많이 넘으면 **I1 예산에 빠진 요인이 있거나 보정하지 않은 치우침이 있는 것**입니다. (`|E_n| ≤ 1` 은 `|d| ≤ √(U_laser² + U_ref²)` 와 같은 조건이라 두 비율은 항상 같게 나옵니다.)

### 2.4 기준 장비 고르기

| 장비 | 비교 항목 | 정밀도 (대략) | 주의 |
|---|---|---|---|
| 디지털 마이크로미터 | 두께, 높이 | ±1~2 µm | 측정력으로 PLA가 눌릴 수 있음 → 래칫 사용, 일정한 힘 |
| 디지털 캘리퍼스 | 외형 치수 | ±20 µm | 레이저 U(≈ 16~21 µm)와 비슷 → 기준 장비로는 부족, 대략 확인용 |
| 하이트 게이지 / 다이얼 게이지 | 단차 높이 | ±2~10 µm | 석정반 위에서, 같은 위치를 찍도록 표시 |
| 광학 현미경 + 스케일 | 선폭, 모서리 | 배율에 따라 µm 수준 | 초점 위치에 따라 경계 판정이 달라짐 |
| **CMM, 공초점 현미경, 백색광 간섭계** | 3D 형상 전체 | sub-µm~수 µm | 학내 공동기기원 예약 필요(대기 1~3주) |

**기준 장비 원칙**: 기준 장비의 U가 레이저 U의 **1/3 이하**(예: 16 µm의 1/3 ≈ 5 µm 이하)여야 차이의 대부분이 레이저 쪽에서 온다고 해석할 수 있습니다. 캘리퍼스는 이 조건을 만족하지 못합니다.

### 2.5 "같은 것"을 재고 있는지 (측정량 일치)

두 장비가 **같은 위치에서 같은 정의로** 재지 않으면 차이가 측정량 정의의 차이일 뿐입니다.
- 단차 높이: 레이저는 "계단 두 평면의 경계 띠를 뺀 영역 중앙값 차이"(H7). CMM도 **같은 영역에서 여러 점(예: 평면당 9점)** 을 찍어 평면 맞춤 후 거리를 구합니다.
- 접촉식 탐침은 구 반경(예: 1 mm)만큼 좁은 홈 바닥에 닿지 못하고, 광학식은 반투명 표면 아래에서 반사될 수 있습니다. 두 방식 모두 측정 가능한 형상만 비교합니다.

## 3. 입력과 산출물

| 구분 | 항목 | 파일 / 형식 |
|---|---|---|
| 입력 | 비교용 시편 6개 (E3 시편, 본 실험 시편 중 무작위 선정) | ID `S01`~`S06` |
| 입력 | 레이저 결과 (H5, H7 지표) | `results/<scan_id>/metrics.csv` |
| 입력 | 기준 장비 결과 + 장비 교정성적서 | `data/cross_validation/ref_<장비>_<날짜>.csv`, PDF |
| 입력 | 레이저 U (I1), 기준 장비 U | `results/uncertainty/budget_*_summary.json`, 성적서 |
| 산출물 | 짝 데이터 | `data/cross_validation/pairs.csv` (열: specimen, feature, laser_um, ref_um) |
| 산출물 | 차이·E_n 포함 결과 | `results/cross_validation/pairs_with_diff.csv` |
| 산출물 | Bland–Altman 그림 (300 dpi) | `results/cross_validation/bland_altman.png` |
| 산출물 | 요약표 | `results/cross_validation/summary.csv` (n, d̄, CI, s, LoA, LoA CI, 비례 기울기, E_n 비율) |
| 산출물 | 교차검증 보고서 | `docs/reports/I3_cross_validation.md` |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 기준 장비 | 마이크로미터 / 하이트 게이지 / CMM / 공초점 | **높이: 마이크로미터·하이트 게이지 (필수) + CMM 또는 공초점 (가능하면)** | BLUEPRINT 부록1 #17. 저렴한 장비로 전체, 고급 장비로 대표 시편 |
| 비교 형상 | 전부 / 대표 | **단차 0.2, 0.4, 1, 2 mm + 두께 5 mm (높이 5종)**, CMM 사용 시 Ø6 지름·10 mm 길이 추가 | 범위 0.2~5 mm 확보 → 비례 치우침 검출 |
| 쌍 개수 | 10 / 30 / 100 | **최소 30쌍 (시편 6 × 형상 5)** | n = 30이면 LoA CI 반폭 ≈ 0.65·s. 100쌍이면 0.35·s |
| 합격 기준 | LoA 폭 / E_n | **E_n: 쌍의 ≥ 90 %가 \|E_n\| ≤ 1**, 그리고 d̄ CI가 ±U_laser 안 | 불확도 예산과 직접 연결. 30쌍의 표본 변동을 고려해 90 % |
| 치우침 보정 | 보정 전/후 | **둘 다 보고** | 보정의 효과를 보여 주는 것도 결과 |
| 반복 측정 처리 | 쌍마다 1회 / 반복 평균 | **각 장비 3회 평균값을 쌍으로** | 평균하면 U도 바뀌므로 I1 `n_avg = 3` 으로 재계산한 U 사용 |
| 같은 형상 반복 쌍 | 독립 취급 / 반복측정 방법 | 같은 형상을 여러 번 쌍으로 넣으면 **Bland–Altman 반복측정 방법(1999, 2007)** 사용 | 독립이 아닌 쌍을 독립으로 보면 LoA가 좁게 나옴 (유사반복) |
| 측정 순서 | 레이저 먼저 / 무작위 | **레이저 먼저 (비접촉), 접촉식 나중** | 접촉식 탐침이 PLA 표면에 자국을 남길 수 있음 |

## 5. 수행 절차

**1. 계획과 예약 (W18, 2월 2~4일)**
- [ ] 공동기기원 CMM/공초점 현미경 예약 (W19~20 사이 2~4시간 2회). 교정성적서 사본 요청
- [ ] 비교 시편 6개 무작위 선정 (`rng = numpy.random.default_rng(2027)`), 비교 형상 5종 목록 확정
- [ ] 측정 위치 표시도 작성: 각 단차의 측정 영역(예: 각 평면 중앙 3×3 mm)을 그림으로 정의

**2. 측정량 정의 맞추기 (W18, 2월 5~6일)**
- [ ] 레이저 지표(H7)의 평가 영역과 CMM 측정점 배치를 같게 설정
- [ ] 마이크로미터·하이트 게이지는 같은 영역 중앙을 3회 측정해 평균
- [ ] 측정 환경 온도 기록 (두 장비가 다른 방이면 각각 기록, 20 °C에서 차이가 크면 열팽창 보정)

**3. 레이저 측정 (W18~19, 2월 6~10일)**
- [ ] 시편당 3회 스캔(매번 재장착), 세션 시작 시 I2 안정성 관리도 확인 (신호 있으면 중지)
- [ ] 3회 평균을 `laser_um` 으로 기록

**4. 기준 장비 측정 (W19~20, 2월 10~20일)**
- [ ] 마이크로미터/하이트 게이지: 형상마다 3회, 평균을 `ref_um`
- [ ] CMM/공초점: 같은 시편 중 최소 2~3개 (가능하면 6개 전부)
- [ ] 기준 장비 U를 성적서에서 확인 (예: 하이트 게이지 U = 3 µm, k = 2)

**5. 분석 (W20, 2월 21~22일)**
- [ ] `pairs.csv` 작성 후 `bland_altman.py` 실행 (보정 전 / I2 치우침 보정 후)
- [ ] 판정: d̄ CI, LoA, 비례 치우침 p, E_n 비율
- [ ] 차이 정규성(Shapiro p > 0.05) 확인. 정규가 아니면 LoA 대신 차이의 2.5 %·97.5 % 백분위수도 보고

**6. 불일치 원인 조사 (W20~21, 필요 시)**
- [ ] E_n 비율 < 90 %: 형상별로 차이를 나누어 봄 → 특정 형상(예: 0.2 mm 단차)에서만 크면 엣지 효과(E2)·평가 영역 문제
- [ ] d̄ 유의: I2 치우침 보정이 적용되었는지 확인, 표면 침투(E1) 의심 → 무광 코팅 시편으로 재비교
- [ ] 비례 치우침 유의: Z 배율(D2)·스캔축 배율(D3) 재검토
- [ ] 원인과 수정 사항을 I1 예산에 반영(요인 추가 또는 값 수정)

**7. 보고 (W21, 2월 23일~3월 1일)**
- [ ] Bland–Altman 그림(보정 후), 요약표, 형상별 차이 표
- [ ] 논문 5장 초안 문단 작성 (K5): "레이저와 CMM의 평균 차이는 … µm (95 % CI …), 일치 한계 …"

## 6. Python 구현

### 6.1 Bland–Altman 분석 스크립트

`src/cvlab/cross_validation.py` (아래는 합성 데이터로 단독 실행 가능한 형태). 합성 데이터의 **참값**: 레이저 치우침 +6 µm, 레이저 무작위 σ = 8 µm, 기준 장비 σ = 1.5 µm, 시편 6개 × 형상 5종 = 30쌍.

```python
"""bland_altman.py — 레이저 삼각측량 센서 vs 독립 장비(CMM 등) 일치도 분석

입력 CSV 열: specimen, feature, laser_um, ref_um   (같은 형상을 두 장비로 잰 값, µm)
차이 d = laser − ref  (부호 규칙: 측정 − 기준. + 이면 레이저가 크게 잼)

사용법:  python bland_altman.py [pairs.csv] --U-laser 16 --U-ref 3 --out results/cross_validation
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

plt.rcParams["axes.unicode_minus"] = False


def bland_altman(laser, ref, alpha=0.05):
    """Bland & Altman (1986) 일치도: 평균 차이, 일치 한계(LoA), 각각의 95 % 신뢰구간"""
    laser, ref = np.asarray(laser, float), np.asarray(ref, float)
    d = laser - ref
    m = (laser + ref) / 2
    n = d.size
    dbar, s = d.mean(), d.std(ddof=1)
    tq = stats.t.ppf(1 - alpha / 2, n - 1)
    se_mean = s / np.sqrt(n)                      # 평균 차이의 표준오차
    se_loa = np.sqrt(3 * s ** 2 / n)              # 일치 한계의 근사 표준오차 (Bland & Altman 1986)
    loa_lo, loa_hi = dbar - 1.96 * s, dbar + 1.96 * s
    # 비례 치우침: 차이가 크기(평균)에 따라 변하는지 회귀로 확인
    reg = stats.linregress(m, d)
    sw_p = stats.shapiro(d).pvalue                 # 차이의 정규성
    return {"n": n, "mean_diff": dbar, "sd_diff": s,
            "mean_ci": (dbar - tq * se_mean, dbar + tq * se_mean),
            "loa": (loa_lo, loa_hi),
            "loa_lo_ci": (loa_lo - tq * se_loa, loa_lo + tq * se_loa),
            "loa_hi_ci": (loa_hi - tq * se_loa, loa_hi + tq * se_loa),
            "prop_slope": reg.slope, "prop_p": reg.pvalue,
            "shapiro_p": sw_p, "d": d, "m": m}


def en_numbers(laser, ref, U_laser, U_ref):
    """E_n = (x_lab − x_ref) / √(U_lab² + U_ref²)  (k=2 확장불확도 사용). |E_n| ≤ 1 이면 일치"""
    return (np.asarray(laser) - np.asarray(ref)) / np.hypot(U_laser, U_ref)


def plot_ba(r, path, accept=None, title="Bland-Altman: laser vs CMM"):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(r["m"] / 1000, r["d"], s=22, color="#1f77b4", zorder=3)
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(r["mean_diff"], color="#d62728", label=f"mean diff {r['mean_diff']:+.1f} um")
    ax.axhspan(*r["mean_ci"], color="#d62728", alpha=0.12)
    for v, ci in ((r["loa"][0], r["loa_lo_ci"]), (r["loa"][1], r["loa_hi_ci"])):
        ax.axhline(v, color="#555555", ls="--")
        ax.axhspan(*ci, color="gray", alpha=0.12)
    ax.plot([], [], color="#555555", ls="--",
            label=f"LoA [{r['loa'][0]:+.1f}, {r['loa'][1]:+.1f}] um")
    if accept is not None:
        for v in (-accept, accept):
            ax.axhline(v, color="#2ca02c", ls=":")
        ax.plot([], [], color="#2ca02c", ls=":", label=f"expected +/-{accept:.1f} um")
    ax.set_xlabel("mean of two instruments [mm]")
    ax.set_ylabel("laser - reference [um]")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def make_synthetic(seed=7):
    """시편 6개 × 형상 5종(단차 0.2/0.4/1/2 mm, 두께 5 mm) = 30쌍.
    참값을 만든 뒤 레이저(치우침 +6 µm, σ 8 µm)와 CMM(σ 1.5 µm)으로 '측정'."""
    rng = np.random.default_rng(seed)
    nominal = {"step_0.2": 200, "step_0.4": 400, "step_1": 1000, "step_2": 2000, "thick_5": 5000}
    rows = []
    for s in range(1, 7):
        for f, nom in nominal.items():
            true = nom + rng.normal(0, 25)                       # 가공 편차 (시편마다 다름)
            rows.append({"specimen": f"S{s:02d}", "feature": f,
                         "laser_um": true + 6 + rng.normal(0, 8),
                         "ref_um": true + rng.normal(0, 1.5)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", help="짝 데이터 CSV (없으면 합성 데이터)")
    ap.add_argument("--U-laser", type=float, default=16.0, help="레이저 확장불확도 U (k=2) [um], I1")
    ap.add_argument("--U-ref", type=float, default=3.0, help="기준 장비 확장불확도 U (k=2) [um]")
    ap.add_argument("--bias-corr", type=float, default=0.0,
                    help="I2 치우침 연구로 구한 레이저 보정값 [um] (레이저 값에서 뺌)")
    ap.add_argument("--out", default="results/cross_validation")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.csv) if args.csv else make_synthetic()
    df["laser_um"] = df["laser_um"] - args.bias_corr      # 보정 전/후를 따로 실행해 비교
    r = bland_altman(df["laser_um"], df["ref_um"])
    df["diff_um"] = r["d"]
    df["En"] = en_numbers(df["laser_um"], df["ref_um"], args.U_laser, args.U_ref)
    # I1 예산이 맞다면 차이의 약 95 % 가 ±√(U_laser² + U_ref²) 안에 들어와야 한다
    expected = np.hypot(args.U_laser, args.U_ref)

    print(f"n = {r['n']} 쌍 (레이저 보정값 {args.bias_corr:+.1f} um 적용)")
    print(f"평균 차이 = {r['mean_diff']:+.2f} um, 95 % CI [{r['mean_ci'][0]:+.2f}, {r['mean_ci'][1]:+.2f}]")
    print(f"차이 SD = {r['sd_diff']:.2f} um")
    print(f"일치 한계 LoA = [{r['loa'][0]:+.2f}, {r['loa'][1]:+.2f}] um")
    print(f"  하한 95 % CI [{r['loa_lo_ci'][0]:+.2f}, {r['loa_lo_ci'][1]:+.2f}], "
          f"상한 95 % CI [{r['loa_hi_ci'][0]:+.2f}, {r['loa_hi_ci'][1]:+.2f}]")
    print(f"비례 치우침 기울기 = {r['prop_slope'] * 1000:+.2f} um/mm (p = {r['prop_p']:.3f})")
    print(f"차이 정규성 Shapiro p = {r['shapiro_p']:.3f}")
    print(f"|E_n| <= 1 비율 = {100 * (df['En'].abs() <= 1).mean():.0f} %  (기대 >= 95 %)")
    print(f"예상 범위 ±{expected:.1f} um 안의 차이 비율 = "
          f"{100 * (df['diff_um'].abs() <= expected).mean():.0f} %")

    df.to_csv(out / "pairs_with_diff.csv", index=False)
    plot_ba(r, out / "bland_altman.png", accept=expected)
    print(f"저장: {out / 'pairs_with_diff.csv'}, {out / 'bland_altman.png'}")


if __name__ == "__main__":
    main()
```

### 6.2 실행 예시와 기대 출력

**(a) 보정 전**

```bash
python bland_altman.py --U-laser 16 --U-ref 3 --out results/cross_validation
```

```text
n = 30 쌍 (레이저 보정값 +0.0 um 적용)
평균 차이 = +7.91 um, 95 % CI [+5.18, +10.64]
차이 SD = 7.32 um
일치 한계 LoA = [-6.43, +22.26] um
  하한 95 % CI [-11.17, -1.70], 상한 95 % CI [+17.52, +26.99]
비례 치우침 기울기 = -0.00 um/mm (p = 0.996)
차이 정규성 Shapiro p = 0.387
|E_n| <= 1 비율 = 83 %  (기대 >= 95 %)
예상 범위 ±16.3 um 안의 차이 비율 = 83 %
저장: results/cross_validation/pairs_with_diff.csv, results/cross_validation/bland_altman.png
```

**(b) I2 치우침 보정(+6 µm) 후**

```bash
python bland_altman.py --bias-corr 6 --out results/cross_validation_corr
```

```text
n = 30 쌍 (레이저 보정값 +6.0 um 적용)
평균 차이 = +1.91 um, 95 % CI [-0.82, +4.64]
차이 SD = 7.32 um
일치 한계 LoA = [-12.43, +16.26] um
  하한 95 % CI [-17.17, -7.70], 상한 95 % CI [+11.52, +20.99]
비례 치우침 기울기 = -0.00 um/mm (p = 0.996)
차이 정규성 Shapiro p = 0.387
|E_n| <= 1 비율 = 100 %  (기대 >= 95 %)
예상 범위 ±16.3 um 안의 차이 비율 = 100 %
저장: results/cross_validation_corr/pairs_with_diff.csv, results/cross_validation_corr/bland_altman.png
```

읽는 법
- (a) 평균 차이 +7.9 µm의 CI [+5.2, +10.6]가 0을 포함하지 않습니다 → 레이저가 계통적으로 크게 잽니다. E_n 비율 83 %로 기준(≥ 90 %) 미달입니다. **I1 예산에 보정하지 않은 치우침이 빠져 있는 상황**을 재현한 것입니다.
- (b) 치우침을 보정하면 CI가 0을 포함하고, E_n 비율 100 %로 합격입니다. 차이 SD 7.3 µm는 그대로입니다. 보정은 치우침만 없애고 무작위 흩어짐은 줄이지 못합니다.
- 비례 치우침 기울기 ≈ 0 (p = 0.996): 0.2 mm~5 mm 범위에서 배율 문제는 없습니다.
- LoA 상한 CI 반폭이 약 ±4.7 µm입니다. 30쌍으로는 LoA 자체가 이 정도 불확실하다는 뜻입니다.

생성되는 그림 `bland_altman.png`: 가로축은 두 장비 평균(mm), 세로축은 차이(µm)입니다. 빨간 실선과 띠는 평균 차이와 95 % CI, 회색 점선과 띠는 LoA와 CI, 녹색 점선은 I1에서 기대한 범위 ±√(U_laser² + U_ref²) = ±16.3 µm입니다. 녹색 점선이 LoA 바깥에 있으면 I1 예산과 실제가 일치하는 것입니다.

### 6.3 실제 데이터로 실행

```bash
# data/cross_validation/pairs.csv 열: specimen,feature,laser_um,ref_um
python bland_altman.py data/cross_validation/pairs.csv --U-laser 16 --U-ref 3 --bias-corr 0
```

`laser_um`, `ref_um` 은 **같은 단위(µm)** 의 측정값 자체(예: 단차 높이 1003.2)입니다. 오차(측정 − G코드 기준)를 넣어도 차이 d는 같지만, 가로축이 형상 크기가 아니게 되어 비례 치우침을 볼 수 없으므로 측정값을 넣습니다.

## 7. 검증 방법과 완료 기준

| 항목 | 지표 | 합격 기준 |
|---|---|---|
| 데이터 규모 | 쌍 개수 n | ≥ 30쌍 (높이), CMM 사용 시 치수 ≥ 10쌍 추가 |
| 계통 차이 | d̄ 의 95 % CI | **CI가 ±U_laser(예: ±16 µm) 안에 완전히 들어감**. 0을 포함하지 않으면 원인 기록 |
| 불확도 일치 | \|E_n\| ≤ 1 비율 | **≥ 90 %** (기대 95 %) |
| 무작위 불일치 | 차이 SD s | s ≤ √(u_laser² + u_ref²) × 1.3 (예: √(8.1² + 1.5²) × 1.3 ≈ 10.7 µm) |
| 비례 치우침 | 기울기 p | p ≥ 0.05, 또는 유의할 때 기울기 × 5 mm < 5 µm |
| 정규성 | Shapiro p | ≥ 0.05 (미달 시 백분위수 LoA 병기) |
| 기준 장비 적합성 | U_ref / U_laser | ≤ 1/3 |
| 보고 | 그림·표·보고서 | 300 dpi 그림, 요약표, 보정 전/후 결과 모두 존재 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 상관계수·R²만 보고 | "r = 0.999로 일치"라고 썼지만 실제로 +8 µm 계통 차이 | Bland–Altman과 E_n으로 보고 |
| 차이 부호를 섞어 씀 | 그림과 표의 치우침 방향이 반대 | 항상 `레이저 − 기준` (+ = 레이저가 큼) |
| 기준 장비가 레이저보다 부정확 | 캘리퍼스(±20 µm)와 비교해 "일치" 판정 | U_ref ≤ U_laser/3 장비 사용, 캘리퍼스는 참고로만 |
| 서로 다른 위치·정의로 측정 | 특정 형상만 차이가 크고 원인 불명 | 측정 위치 표시도, 같은 평가 영역·알고리즘 |
| 같은 형상 반복값을 독립 쌍으로 넣음 | n이 커 보이고 LoA가 좁게 나옴 | 반복은 평균해서 1쌍, 또는 반복측정용 Bland–Altman |
| 합격 기준을 결과를 보고 정함 | 결과에 맞춰 기준이 느슨해짐 | §4 기준을 측정 전 보고서 초안에 기록 |
| 접촉식 측정력으로 PLA 눌림 | 마이크로미터 값이 수 µm 작음 | 래칫/일정 측정력, 비접촉 측정 먼저 |
| 두 장비의 온도가 다름 | 계통 차이 수 µm | 온도 기록, 필요시 20 °C 환산 |
| 보정 전 결과를 숨김 | 검증 과정이 불투명 | 보정 전/후 둘 다 보고 |

## 9. 위험 요소

- **고급 장비 접근 불가** (공동기기원 예약 지연, 비용): 마이크로미터·하이트 게이지만으로 높이 교차검증을 하고, XY 치수는 광학 현미경 + 스테이지 마이크로미터로 대체합니다. 보고서에 한계로 명시합니다. 예약은 W15(1월)에 미리 문의합니다.
- **본 실험(W18~21)과 같은 기간**: 레이저 장비 사용 시간이 겹칩니다. 교차검증용 레이저 스캔은 본 실험 세션 끝에 시편당 3회씩 붙여서 수행합니다.
- **불일치가 크게 나옴**: I1 예산 수정과 재분석이 필요해 M6(보고서)가 밀릴 수 있습니다. W20 중반까지 1차 분석을 끝내서 W21에 원인 조사 시간을 확보합니다.
- **시편 손상**: 접촉식 측정 후 표면 자국이 생기면 이후 레이저 측정에 영향을 줍니다. 레이저 먼저, 접촉식은 마지막에 합니다.
- **표면 효과 의존**: 금속 게이지 블록에서는 일치하지만 PLA에서는 안 맞을 수 있습니다. 이 경우 그것 자체가 E1 표면 영향의 정량 결과이므로 별도로 보고합니다.

## 10. 기록 양식

**짝 데이터** (`data/cross_validation/pairs.csv`)

```csv
specimen,feature,laser_um,ref_um,laser_n,ref_n,ref_instrument,ref_U_um,laser_scan_ids,ref_date,room_temp_C,notes
S01,step_0.2,,,3,3,height_gauge,3.0,,,,
```

**기준 장비 측정 기록**

| 날짜 | 장비 (모델·관리번호) | 교정성적서 번호 / 유효기간 | U (k=2) | 시편 | 형상 | 1회 | 2회 | 3회 | 평균 | 온도 [°C] | 측정자 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | |

**교차검증 요약표** (`results/cross_validation/summary.csv` 와 같은 내용)

| 조건 | n | d̄ [µm] (95 % CI) | s [µm] | LoA [µm] | 비례 기울기 [µm/mm] (p) | \|E_n\| ≤ 1 비율 | 판정 |
|---|---|---|---|---|---|---|---|
| 보정 전 | | | | | | | |
| 보정 후 | | | | | | | |

## 11. 참고 자료

- J. M. Bland, D. G. Altman, "Statistical methods for assessing agreement between two methods of clinical measurement", *The Lancet*, 1986
- J. M. Bland, D. G. Altman, "Measuring agreement in method comparison studies", *Statistical Methods in Medical Research*, 1999 (반복측정 처리)
- J. M. Bland, D. G. Altman, "Agreement between methods of measurement with multiple observations per individual", *Journal of Biopharmaceutical Statistics*, 2007
- ISO/IEC 17043, *Conformity assessment — General requirements for proficiency testing* (E_n 수)
- ISO 10360 시리즈, *Geometrical product specifications (GPS) — Acceptance and reverification tests for coordinate measuring systems (CMS)* (CMM 성능 확인)
- JCGM 100:2008 (GUM) — U 계산 (I1)
- 상위 문서: [BLUEPRINT.md I3](../../BLUEPRINT.md#i3-독립-장비와의-교차검증)
