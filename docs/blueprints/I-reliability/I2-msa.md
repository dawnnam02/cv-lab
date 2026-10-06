# I2. 측정시스템분석 (MSA)

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: I. 측정 신뢰성 검증

| 항목 | 내용 |
|---|---|
| 기간 | 2027-01-12 ~ 2027-02-01 (W15-17) |
| 우선순위 | 긴급 |
| 트랙 | 실험·품질 |
| 선행 요소 | [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) · [C3 지그·기준마커](../C-mechanics/C3-fiducials.md) · [F2 획득 파라미터](../F-acquisition/F2-acquisition-params.md) · [E3 시편 설계](../E-specimen/E3-test-artifact.md) · [H5 높이 지표](../H-analysis/H5-height-metrics.md) · [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) |
| 후행 요소 | [I1 측정 불확도](I1-uncertainty.md) (반복성·재현성 값 공급) · [I3 교차검증](I3-cross-validation.md) · [H8 통계 분석](../H-analysis/H8-statistics.md) · [K5 산출물·논문](../K-management/K5-deliverables-paper.md) |
| 관련 마일스톤 | **M5**: %GRR < 30 % (목표 < 10 %) |

## 1. 목적

측정 시스템(센서 + 지그 + 소프트웨어 + 사람)이 **본 실험(W18~21)에 쓸 만한지** 다섯 가지 성질로 판정합니다.

| 성질 | 질문 | 이 요소의 결과물 |
|---|---|---|
| 치우침 (Bias) | 평균적으로 참값보다 크게/작게 재는가? | 치우침 µm + 95 % CI + 보정 여부 |
| 직선성 (Linearity) | 1 mm를 잴 때와 20 mm를 잴 때 치우침이 같은가? | 회귀식 `bias = a + b·h` |
| 안정성 (Stability) | 오늘과 다음 주의 결과가 같은가? | I-MR 관리도 + 관리 한계 (D5 재교정 신호) |
| 반복성 (Repeatability) | 같은 사람이 그대로 다시 재면 얼마나 흩어지나? | σ_EV |
| 재현성 (Reproducibility) | 사람이 바뀌고, 시편을 떼었다 다시 붙이면? | σ_AV |

이 다섯을 모아 **Gage R&R(%GRR, ndc)** 로 종합 판정하고, **M5 통과 여부(%GRR < 30 %)** 를 결정합니다. M5를 통과하지 못하면 본 실험으로 넘어가지 않습니다 (K1의 진행/중단 원칙과 같음).

## 2. 배경 지식 (초보자용)

### 2.1 측정값의 흩어짐은 어디서 오나

어떤 시편을 측정했을 때 값이 다른 이유는 세 가지로 나눌 수 있습니다.

```
전체 변동(TV)² = 시편 간 진짜 차이(PV)² + 측정 시스템 변동(GRR)²
GRR² = 반복성(EV)² + 재현성(AV)²
```

- **EV (Equipment Variation, 반복성)**: 같은 사람, 같은 시편, 같은 장착 상태에서 연속 측정했을 때의 흩어짐. 센서 노이즈, 스펙클, 진동이 원인.
- **AV (Appraiser Variation, 재현성)**: 측정자(또는 재장착)가 바뀔 때 생기는 차이. 시편 놓는 위치, 고정 나사 조이는 힘, 소프트웨어에서 ROI 고르는 습관 등.
- **PV (Part Variation)**: 시편끼리 정말로 다른 정도. 이것은 측정 시스템이 **구별해 내야 할 신호**입니다.

### 2.2 %GRR과 ndc

- `%GRR = 100 · σ_GRR / σ_TV` (AIAG 정의, 표준편차 비율. 분산 비율이 아님에 주의)
  - < 10 % 우수, 10~30 % 조건부(용도·비용에 따라 허용), > 30 % 부적합 (BLUEPRINT I2 기준)
- `ndc (구별 범주 수) = ⌊1.41 · σ_PV / σ_GRR⌋` : 측정 시스템이 시편들을 몇 개의 "등급"으로 확실히 나눌 수 있는지. **≥ 5** 이어야 합니다.
- `%P/T = 100 · 6σ_GRR / (USL − LSL)` : 공차 대비 비율. 시편 간 차이가 원래 작은 경우 %GRR이 나쁘게 나오므로 **공차 기준으로도 함께 보고**합니다. A2의 치수 공차 ±0.1 mm → 공차 폭 200 µm.

### 2.3 ANOVA(분산분석)로 성분을 나누는 법

시편 p개 × 측정자 o명 × 반복 r회의 **교차 설계**에서 ANOVA 표의 평균제곱(MS)으로 분산 성분을 구합니다 (AIAG MSA 4판).

| 성분 | 식 |
|---|---|
| 반복성 σ²_EV | MS_E (잔차) |
| 교호작용 σ²_PO | (MS_PO − MS_E) / r |
| 측정자 σ²_O | (MS_O − MS_PO) / (p·r) |
| 시편 σ²_P | (MS_P − MS_PO) / (o·r) |
| 재현성 σ²_AV | σ²_O + σ²_PO |

- 계산 결과가 음수이면 0으로 둡니다 (진짜 값이 0에 가깝다는 뜻).
- **교호작용 p > 0.25** 이면 교호작용이 없다고 보고 오차항에 합칩니다(pooling). AIAG가 쓰는 관례입니다.
- "교호작용"이란 "측정자 A는 높은 시편에서만 더 크게 잰다" 같은 효과입니다.

### 2.4 치우침과 직선성

- **치우침** = 평균(측정 − 기준). 같은 게이지 블록을 25회 재고, 1-표본 t-검정으로 0과 다른지 봅니다. 유의하면 **보정**하고, 보정 불확도를 I1에 넣습니다.
- **직선성**: 높이가 다른 블록 5개(1, 2, 5, 10, 20 mm)에서 치우침을 구하고 `bias = a + b·h` 회귀를 합니다. 기울기 b가 0과 유의하게 다르면 "배율 오차"가 있다는 뜻이고, 원인은 보통 레이저 평면(D2)이나 Z 방향 배율입니다.

### 2.5 안정성과 I-MR 관리도

세션마다 기준 시편을 1번 재서 값 하나(개별값 I)를 얻고, 이웃 값과의 차이(이동범위 MR)를 함께 그립니다.

```
MR̄ = 이동범위 평균,  σ̂ = MR̄ / 1.128
I 관리도:  CL = x̄,   UCL/LCL = x̄ ± 3σ̂  (= x̄ ± 2.66·MR̄)
MR 관리도: UCL = 3.267·MR̄
```

관리 한계는 **처음 20 세션(기준 기간)** 으로 정하고 이후에는 고정합니다. 이상 신호 규칙은 ① 한계 밖 1점, ② 중심선 한쪽에 연속 8점, ③ MR이 MR_UCL 초과 입니다. 신호가 나오면 D5의 재교정 조건에 해당합니다.

## 3. 입력과 산출물

| 구분 | 항목 | 파일 / 형식 |
|---|---|---|
| 입력 | 게이지 블록 세트 (1, 2, 5, 10, 20 mm, 인증서) | 인증서 PDF |
| 입력 | 안정성용 기준 시편 1개 (게이지 블록 단차 2 mm 또는 금속 단차 시편) | 실물, ID `REF-STEP-01` |
| 입력 | Gage R&R 시편 10개 (E3 계단 피라미드, 유량 90~110 % 로 일부러 다르게 출력) | 실물, ID `GRR-P01`~`P10` |
| 입력 | 처리 파이프라인과 설정 | `config/default.yaml` (고정, git 해시 기록) |
| 산출물 | 치우침 원자료 | `results/msa/bias_10mm.csv` (열: trial, meas_um, ref_um) |
| 산출물 | 직선성 원자료 | `results/msa/linearity.csv` (열: ref_mm, trial, meas_dev_um) |
| 산출물 | 안정성 기록 (계속 추가) | `results/msa/stability_log.csv` (열: session, date, cal_id, value_um) |
| 산출물 | 관리도 그림 | `results/msa/stability_imr.png` |
| 산출물 | Gage R&R 원자료 | `results/msa/grr_data.csv` (열: part, operator, trial, y) |
| 산출물 | 요약 | `results/msa/msa_summary.csv` |
| 산출물 | MSA 보고서 | `docs/reports/I2_msa_<CAL-ID>.md` (M5 판정 포함) |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| Gage R&R 측정 특성 | 점 높이 / 단차 높이 / 지름 / RMS | **2 mm 단차 높이 오차 (주)**, Ø6 지름 오차 (보조) | 본 실험 핵심 지표(H5, H7)와 같아야 의미가 있음 |
| 설계 규모 | 5×2×2 ~ 10×3×3 | **10 시편 × 3 측정자 × 3 반복 = 90 스캔** | AIAG 표준 규모. 스캔 1회 ≈ 4분(장착 포함) → 약 6시간, 3일에 나눔 |
| "측정자"의 의미 | 사람만 / 사람 + 재장착 | **사람 + 매 반복마다 재장착** | 실제 본 실험은 매번 시편을 놓고 측정하므로 재장착 영향 포함 |
| 측정자 수가 1명뿐일 때 | – | 측정자 대신 **"날짜(3일)"** 를 요인으로 | 재현성 성분을 다른 방식으로 확보 |
| 판정 기준 | %GRR(TV) / %P/T | **둘 다 보고, M5 판정은 %GRR** | BLUEPRINT M5 기준이 %GRR |
| 교호작용 합침 기준 | α = 0.05 / 0.25 | **0.25** | AIAG 관례 (보수적으로 교호작용을 남김) |
| 치우침 반복 수 | 10 / 25 | **25회** | t-검정 검정력. 2 µm 치우침을 σ = 4 µm에서 검출하려면 n ≈ 25~35 |
| 직선성 기준 높이 | 3점 / 5점 | **1, 2, 5, 10, 20 mm × 10회** | BLUEPRINT I2 표 |
| 안정성 측정 빈도 | 매일 / 매 세션 | **매 측정 세션 시작 시 1회 (3스캔 평균)** | BLUEPRINT I2. 세션 단위 이상을 잡기 위함 |
| 안정성 기준 기간 | 10 / 20 / 25 세션 | **20 세션** | 관리 한계 추정 안정성. W15~17에 하루 1~2 세션이면 확보 가능 |

## 5. 수행 절차

**1. 준비 (W15, 1월 12~13일)**
- [ ] 장비 30분 워밍업 규칙 확인 (C6, B6)
- [ ] 측정자 3명 지정 (K2 역할 분담), 작업표준서 1쪽 작성: 시편 놓는 법, 고정 방법, 스캔 명령, 파일 이름 규칙(F3)
- [ ] Gage R&R 시편 10개 출력: 계단 피라미드(E3)를 유량 90, 92, …, 110 %로 출력하여 단차 오차 범위가 약 ±100 µm에 걸치게 함
- [ ] 모든 시편에 ID 각인, 측정 순서 무작위표 생성 (`numpy.random.default_rng(42).permutation`)

**2. 반복성 단독 시험 (W15, 1월 14일)**
- [ ] 10 mm 게이지 블록 단차를 고정, **연속 10회** 스캔 → 표준편차 s (I1 반복성 입력)
- [ ] 합격 목표: s ≤ 5 µm (A2 목표 Z 반복성)

**3. 치우침 시험 (W15, 1월 14~15일)**
- [ ] 10 mm 블록을 **25회** 측정 (5회마다 재장착)
- [ ] `bias_study` 실행 → bias, 95 % CI, p
- [ ] p < 0.05 이면 보정값으로 채택하고 `config/default.yaml` 의 `z_bias_correction_um` 에 기록, 보정 불확도(= CI 반폭/1.96)를 I1에 추가

**4. 직선성 시험 (W15~16, 1월 16~19일)**
- [ ] 1, 2, 5, 10, 20 mm 블록 각 10회 (블록 순서 무작위)
- [ ] `linearity_study` 실행 → 기울기 b와 95 % CI
- [ ] 기울기 CI가 0을 포함하지 않으면: 20 mm에서의 예측 치우침 `a + 20b` 를 계산, **5 µm 이상이면 D2 레이저 평면 재교정** 검토, 미만이면 회귀식으로 보정

**5. 안정성 관리도 시작 (W15부터 계속, 본 실험 끝까지)**
- [ ] 매 세션 시작 시 `REF-STEP-01` 3스캔 평균 → `stability_log.csv` 한 줄 추가
- [ ] 20 세션 모이면 관리 한계 확정 (그전에는 임시 한계: x̄ ± 3·5 µm)
- [ ] 이상 신호 발생 시: 그 세션 측정 중단 → 원인 조사(렌즈 잠금, 레이저 워밍업, 온도) → D5 재교정 → 새 CAL-ID로 관리도 다시 시작

**6. Gage R&R 본 시험 (W16, 1월 20~23일, 3일)**
- [ ] 1일차: 측정자 A, B, C가 각자 10개 시편을 무작위 순서로 1회씩 (= 1 trial)
- [ ] 2일차, 3일차: 2nd, 3rd trial. 측정자는 **이전 결과를 보지 않음** (블라인드)
- [ ] 각 스캔마다 시편을 떼었다 다시 장착
- [ ] 파이프라인으로 2 mm 단차 높이 오차 계산 → `grr_data.csv`

**7. 분석과 판정 (W17, 1월 26~29일)**
- [ ] `gage_rr_anova` 실행 → %EV, %AV, %GRR, ndc, %P/T
- [ ] 판정: %GRR < 10 % 우수 / 10~30 % 조건부(M5 통과, 개선 계획 기록) / > 30 % 부적합(M5 미통과)
- [ ] %EV ≫ %AV 이면 장비(노이즈·스펙클) 개선, %AV ≫ %EV 이면 작업표준·지그 개선
- [ ] σ_EV, σ_AV 값을 I1 예산의 반복성·재현성 요인에 반영

**8. 보고 (W17, 1월 30일~2월 1일)**
- [ ] `docs/reports/I2_msa_<CAL-ID>.md` 작성: 설계, 원자료 위치, ANOVA 표, 관리도 그림, 판정, M5 결과
- [ ] 지도교수 검토 후 M5 통과 기록 (K1)

## 6. Python 구현

### 6.1 MSA 계산 모듈

`src/cvlab/msa.py` (아래는 합성 데이터로 단독 실행 가능한 형태). 합성 데이터의 **참값**: 치우침 +4 µm, 직선성 `2 + 0.5·h` µm, 26번째 세션부터 +12 µm 이동, Gage R&R 참 σ = 시편 50 / 측정자 2 / 교호작용 1 / 반복 4 µm.

```python
"""msa.py — 측정시스템분석(MSA): 치우침 · 직선성 · 안정성(I-MR) · Gage R&R(ANOVA)

모든 값의 단위는 µm, 부호는 '측정값 − 기준값' (+ = 재료 과다 / 크게 측정됨).
합성 데이터(정답을 아는 데이터)로 먼저 돌려 보고, 실제 데이터는 같은 형식의 CSV 로 바꿔 넣는다.

사용법:  python msa.py --out results/msa
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # 화면 없이 PNG 로만 저장
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

plt.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------- 1. 치우침
def bias_study(meas, ref, alpha=0.05):
    """같은 기준물을 n회 측정 → 치우침 = 평균(측정 − 기준), 0 과 다른지 t-검정"""
    d = np.asarray(meas, float) - ref
    n = d.size
    bias, s = d.mean(), d.std(ddof=1)
    se = s / np.sqrt(n)
    t_stat = bias / se
    p = 2 * stats.t.sf(abs(t_stat), n - 1)
    half = stats.t.ppf(1 - alpha / 2, n - 1) * se
    return {"n": n, "bias": bias, "s_repeat": s, "t": t_stat, "p": p,
            "ci_low": bias - half, "ci_high": bias + half,
            "significant": bool(p < alpha)}


# ---------------------------------------------------------------- 2. 직선성
def linearity_study(df):
    """df: 열 ref_mm, meas_dev_um (= 측정 − 기준, µm). 치우침 = a + b·기준높이 회귀"""
    model = smf.ols("meas_dev_um ~ ref_mm", data=df).fit()
    ci = model.conf_int()
    return {"intercept": model.params["Intercept"], "slope_um_per_mm": model.params["ref_mm"],
            "slope_ci": tuple(ci.loc["ref_mm"]), "p_slope": model.pvalues["ref_mm"],
            "p_intercept": model.pvalues["Intercept"], "r2": model.rsquared, "model": model}


# ---------------------------------------------------------------- 3. 안정성 (I-MR 관리도)
def imr_limits(x_baseline):
    """기준 기간 데이터로 I-MR 관리 한계 계산 (n=2 이동범위: d2=1.128, D4=3.267)"""
    x = np.asarray(x_baseline, float)
    mr_bar = np.abs(np.diff(x)).mean()
    center = x.mean()
    sigma = mr_bar / 1.128                         # 단기 표준편차 추정
    return {"CL": center, "UCL": center + 3 * sigma, "LCL": center - 3 * sigma,
            "MR_bar": mr_bar, "MR_UCL": 3.267 * mr_bar, "sigma": sigma}


def imr_violations(x, lim, run=8):
    """규칙 1: 관리 한계 밖 / 규칙 2: 중심선 한쪽에 연속 run 점 → 위반 인덱스 목록"""
    x = np.asarray(x, float)
    out = set(np.where((x > lim["UCL"]) | (x < lim["LCL"]))[0])
    side = np.sign(x - lim["CL"])
    for i in range(run - 1, len(x)):
        w = side[i - run + 1:i + 1]
        if abs(w.sum()) == run:                    # 모두 +1 이거나 모두 −1
            out.add(i)
    mr = np.abs(np.diff(x))
    out |= {i + 1 for i in np.where(mr > lim["MR_UCL"])[0]}
    return sorted(int(i) for i in out)


def plot_imr(x, lim, viol, n_base, path):
    x = np.asarray(x, float)
    idx = np.arange(1, len(x) + 1)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    a1.plot(idx, x, "o-", color="#1f77b4", ms=4)
    a1.plot(idx[viol], x[viol], "o", color="#d62728", ms=8, mfc="none", label="violation")
    for key, ls in (("CL", "-"), ("UCL", "--"), ("LCL", "--")):
        a1.axhline(lim[key], color="gray", ls=ls)
    a1.axvline(n_base + 0.5, color="k", lw=0.8, ls=":")
    a1.set_ylabel("step height deviation [um]")
    a1.set_title("I chart (reference specimen, each session)")
    a1.legend(loc="upper left")
    mr = np.r_[np.nan, np.abs(np.diff(x))]
    a2.plot(idx, mr, "s-", color="#2ca02c", ms=4)
    a2.axhline(lim["MR_bar"], color="gray")
    a2.axhline(lim["MR_UCL"], color="gray", ls="--")
    a2.set_ylabel("moving range [um]")
    a2.set_xlabel("session #")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- 4. Gage R&R (교차, ANOVA)
def gage_rr_anova(df, tol_width=None, alpha_int=0.25):
    """df: 열 part, operator, y (교차 설계, 균형). AIAG MSA 4판 ANOVA 방법.
    tol_width: 공차 폭(USL−LSL, µm). 주면 %P/T 도 계산.
    교호작용 p > alpha_int 이면 교호작용을 오차항에 합침(pooling)."""
    p_, o_ = df["part"].nunique(), df["operator"].nunique()
    r_ = len(df) // (p_ * o_)
    model = smf.ols("y ~ C(part) + C(operator) + C(part):C(operator)", data=df).fit()
    tab = sm.stats.anova_lm(model, typ=2)
    tab["MS"] = tab["sum_sq"] / tab["df"]
    MSP = tab.loc["C(part)", "MS"]
    MSO = tab.loc["C(operator)", "MS"]
    MSPO = tab.loc["C(part):C(operator)", "MS"]
    MSE = tab.loc["Residual", "MS"]
    p_int = tab.loc["C(part):C(operator)", "PR(>F)"]
    pooled = bool(p_int > alpha_int)
    if pooled:                                     # 교호작용이 무시할 만하면 오차에 합침
        ss = tab.loc["C(part):C(operator)", "sum_sq"] + tab.loc["Residual", "sum_sq"]
        dfp = tab.loc["C(part):C(operator)", "df"] + tab.loc["Residual", "df"]
        MSE = ss / dfp
        var_int = 0.0
        var_op = max((MSO - MSE) / (p_ * r_), 0.0)
        var_part = max((MSP - MSE) / (o_ * r_), 0.0)
    else:
        var_int = max((MSPO - MSE) / r_, 0.0)
        var_op = max((MSO - MSPO) / (p_ * r_), 0.0)
        var_part = max((MSP - MSPO) / (o_ * r_), 0.0)
    var_ev = MSE                                   # 반복성 (장비 변동)
    var_av = var_op + var_int                      # 재현성 (측정자 변동)
    var_grr = var_ev + var_av
    var_tv = var_grr + var_part
    sd = {k: np.sqrt(v) for k, v in
          dict(EV=var_ev, AV=var_av, GRR=var_grr, PV=var_part, TV=var_tv).items()}
    res = {"p": p_, "o": o_, "r": r_, "p_interaction": p_int, "pooled": pooled, "sd": sd,
           "%EV": 100 * sd["EV"] / sd["TV"], "%AV": 100 * sd["AV"] / sd["TV"],
           "%GRR": 100 * sd["GRR"] / sd["TV"], "%PV": 100 * sd["PV"] / sd["TV"],
           "ndc": int(np.floor(1.41 * sd["PV"] / sd["GRR"])) if sd["GRR"] > 0 else np.inf,
           "anova": tab}
    if tol_width:
        res["%P/T"] = 100 * 6 * sd["GRR"] / tol_width
    return res


def grr_verdict(pct):
    return "우수(<10 %)" if pct < 10 else ("조건부(10~30 %)" if pct <= 30 else "부적합(>30 %)")


# ---------------------------------------------------------------- 합성 데이터
def make_synthetic(rng):
    data = {}
    # (1) 10 mm 게이지 블록 25회: 참 치우침 +4 µm, 반복성 σ=4 µm
    data["bias"] = 10_000 + 4 + rng.normal(0, 4, 25)              # µm 단위 측정값
    # (2) 직선성: 1,2,5,10,20 mm × 10회, 참 치우침 = 2 + 0.5·h[mm] µm
    rows = []
    for h in [1, 2, 5, 10, 20]:
        for _ in range(10):
            rows.append({"ref_mm": h, "meas_dev_um": 2 + 0.5 * h + rng.normal(0, 4)})
    data["lin"] = pd.DataFrame(rows)
    # (3) 안정성: 30 세션 (1~20 기준기간, 26번째부터 +12 µm 이동 = 렌즈 풀림 가정)
    x = 3 + rng.normal(0, 3, 30)
    x[25:] += 12
    data["stab"] = x
    # (4) Gage R&R: 시편 10 × 측정자 3 × 반복 3 (참 σ: 시편 50, 측정자 2, 교호 1, 반복 4 µm)
    sig = {"part": 50.0, "operator": 2.0, "inter": 1.0, "repeat": 4.0}
    part_eff = rng.normal(0, sig["part"], 10)
    op_eff = rng.normal(0, sig["operator"], 3)
    int_eff = rng.normal(0, sig["inter"], (10, 3))
    rows = []
    for i in range(10):
        for j in range(3):
            for k in range(3):
                y = 30 + part_eff[i] + op_eff[j] + int_eff[i, j] + rng.normal(0, sig["repeat"])
                rows.append({"part": f"P{i+1:02d}", "operator": "ABC"[j], "trial": k + 1, "y": y})
    data["grr"] = pd.DataFrame(rows)
    data["grr_true_sigma"] = sig
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/msa")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    d = make_synthetic(rng)

    b = bias_study(d["bias"], ref=10_000)
    print("[1] 치우침 (10 mm 게이지 블록, n=25)")
    print(f"    bias = {b['bias']:+.2f} um, 95 % CI [{b['ci_low']:+.2f}, {b['ci_high']:+.2f}], "
          f"t = {b['t']:.2f}, p = {b['p']:.4f} → {'유의함' if b['significant'] else '유의하지 않음'}")

    lin = linearity_study(d["lin"])
    lo, hi = lin["slope_ci"]
    print("[2] 직선성 (1, 2, 5, 10, 20 mm × 10회)")
    print(f"    bias = {lin['intercept']:.2f} + {lin['slope_um_per_mm']:.3f}·h  "
          f"(기울기 95 % CI [{lo:.3f}, {hi:.3f}] um/mm, p = {lin['p_slope']:.2e}, R² = {lin['r2']:.2f})")

    n_base = 20
    lim = imr_limits(d["stab"][:n_base])
    viol = imr_violations(d["stab"], lim)
    plot_imr(d["stab"], lim, viol, n_base, out / "stability_imr.png")
    print("[3] 안정성 I-MR (기준기간 20 세션)")
    print(f"    CL = {lim['CL']:.2f}, UCL = {lim['UCL']:.2f}, LCL = {lim['LCL']:.2f}, "
          f"MR_UCL = {lim['MR_UCL']:.2f} um")
    print(f"    위반 세션 번호: {[i + 1 for i in viol]}")

    g = gage_rr_anova(d["grr"], tol_width=200.0)       # 공차 ±0.1 mm → 폭 200 µm
    d["grr"].to_csv(out / "grr_data.csv", index=False)
    print("[4] Gage R&R (시편 10 × 측정자 3 × 반복 3, ANOVA)")
    print(g["anova"][["df", "sum_sq", "MS", "F", "PR(>F)"]].round(3).to_string())
    print(f"    교호작용 p = {g['p_interaction']:.3f} → {'오차에 합침' if g['pooled'] else '유지'}")
    t = d["grr_true_sigma"]
    print(f"    σ_EV = {g['sd']['EV']:.2f} (참 {t['repeat']}), σ_AV = {g['sd']['AV']:.2f} "
          f"(참 {np.hypot(t['operator'], t['inter']):.2f}), σ_PV = {g['sd']['PV']:.1f} (참 {t['part']})")
    print(f"    %EV = {g['%EV']:.1f} %, %AV = {g['%AV']:.1f} %, %GRR = {g['%GRR']:.1f} % "
          f"→ {grr_verdict(g['%GRR'])}, ndc = {g['ndc']}, %P/T = {g['%P/T']:.1f} %")

    summary = pd.DataFrame([
        {"study": "bias", "value": b["bias"], "p": b["p"]},
        {"study": "linearity_slope_um_per_mm", "value": lin["slope_um_per_mm"], "p": lin["p_slope"]},
        {"study": "stability_violations", "value": len(viol), "p": np.nan},
        {"study": "%GRR", "value": g["%GRR"], "p": np.nan},
        {"study": "ndc", "value": g["ndc"], "p": np.nan},
    ])
    summary.to_csv(out / "msa_summary.csv", index=False)
    print(f"저장: {out / 'msa_summary.csv'}, {out / 'grr_data.csv'}, {out / 'stability_imr.png'}")


if __name__ == "__main__":
    main()
```

### 6.2 실행 예시와 기대 출력

```bash
python msa.py --out results/msa
```

```text
[1] 치우침 (10 mm 게이지 블록, n=25)
    bias = +3.86 um, 95 % CI [+2.49, +5.23], t = 5.80, p = 0.0000 → 유의함
[2] 직선성 (1, 2, 5, 10, 20 mm × 10회)
    bias = 2.78 + 0.420·h  (기울기 95 % CI [0.294, 0.546] um/mm, p = 2.26e-08, R² = 0.48)
[3] 안정성 I-MR (기준기간 20 세션)
    CL = 2.69, UCL = 8.15, LCL = -2.77, MR_UCL = 6.71 um
    위반 세션 번호: [26, 27, 28, 29, 30]
[4] Gage R&R (시편 10 × 측정자 3 × 반복 3, ANOVA)
                       df      sum_sq         MS        F  PR(>F)
C(part)               9.0  135263.924  15029.325  982.998   0.000
C(operator)           2.0      27.793     13.897    0.909   0.408
C(part):C(operator)  18.0     301.641     16.758    1.096   0.378
Residual             60.0     917.357     15.289      NaN     NaN
    교호작용 p = 0.378 → 오차에 합침
    σ_EV = 3.95 (참 4.0), σ_AV = 0.00 (참 2.24), σ_PV = 40.8 (참 50.0)
    %EV = 9.6 %, %AV = 0.0 %, %GRR = 9.6 % → 우수(<10 %), ndc = 14, %P/T = 11.9 %
저장: results/msa/msa_summary.csv, results/msa/grr_data.csv, results/msa/stability_imr.png
```

읽는 법
- **치우침**: +3.86 µm (참 +4)이고 CI가 0을 포함하지 않으므로 유의합니다 → 보정 대상.
- **직선성**: 기울기 0.42 µm/mm (참 0.5)가 유의합니다. 20 mm에서는 약 2.78 + 8.4 = 11 µm 치우침이 예상되므로 §5-4 기준(5 µm)에 걸려 D2 재검토 대상입니다.
- **안정성**: 26~30 세션이 모두 UCL(8.15 µm) 밖입니다. 일부러 넣은 +12 µm 이동을 정확히 잡았습니다. 실제라면 26번째 세션에서 측정을 멈추고 재교정합니다.
- **Gage R&R**: 교호작용 p = 0.378 > 0.25 이므로 합쳤습니다. %GRR 9.6 % → 우수, ndc 14 ≥ 5 → M5 통과.
- σ_AV가 0.00으로 나온 것은 오류가 아닙니다. 측정자가 3명뿐이라 측정자 분산 추정이 매우 불안정하고, 이번 표본에서는 MS_O가 MS_E보다 작아 0으로 잘렸습니다. 참값(2.24 µm)이 반복성(4 µm)보다 작으면 자주 생깁니다. 아래 §6.3 모의실험에서 평균적으로는 참값을 되찾는 것을 확인합니다.
- statsmodels ANOVA 표의 F 값은 모두 잔차 MS로 나눈 값입니다(고정효과 기준). 분산 성분 계산은 위 §2.3 식을 따르므로 영향이 없습니다.

생성되는 관리도 `results/msa/stability_imr.png`: 위는 세션별 값과 CL·UCL·LCL, 아래는 이동범위입니다. 점선 세로줄 왼쪽 20점이 기준 기간입니다.

### 6.3 계산기 검증: 모의실험 300회

`tests/check_grr_sim.py` — 참 분산 성분을 알고 만든 데이터 300세트에 계산기를 돌려 평균이 참값과 맞는지 확인합니다 (약 6초). 저장소에서는 `from cvlab.msa import gage_rr_anova` 로 바꿉니다.

```python
# check_grr_sim.py — Gage R&R 계산기가 '참 분산 성분'을 평균적으로 되찾는지 300회 모의실험
import numpy as np
import pandas as pd
from msa import gage_rr_anova

rng = np.random.default_rng(0)
true = {"part": 50.0, "operator": 2.0, "inter": 1.0, "repeat": 4.0}
P, O, R = 10, 3, 3
est = []
for _ in range(300):
    pe, oe = rng.normal(0, true["part"], P), rng.normal(0, true["operator"], O)
    ie = rng.normal(0, true["inter"], (P, O))
    y = (pe[:, None, None] + oe[None, :, None] + ie[:, :, None]
         + rng.normal(0, true["repeat"], (P, O, R)))
    i, j, k = np.meshgrid(range(P), range(O), range(R), indexing="ij")
    df = pd.DataFrame({"part": i.ravel(), "operator": j.ravel(), "y": y.ravel()})
    g = gage_rr_anova(df, alpha_int=1.0)          # 1.0 → 절대 합치지 않음(검증용)
    est.append({k2: g["sd"][k2] ** 2 for k2 in ("EV", "AV", "PV")} | {"zeroAV": g["sd"]["AV"] == 0})
e = pd.DataFrame(est)
print(f"반복성 분산  평균 {e.EV.mean():6.1f}  (참 {true['repeat']**2:.1f})")
print(f"재현성 분산  평균 {e.AV.mean():6.1f}  (참 {true['operator']**2 + true['inter']**2:.1f})")
print(f"시편 분산    평균 {e.PV.mean():6.0f}  (참 {true['part']**2:.0f})")
print(f"재현성이 0 으로 잘린 비율: {100 * e.zeroAV.mean():.0f} %")
```

```text
반복성 분산  평균   16.2  (참 16.0)
재현성 분산  평균    5.2  (참 5.0)
시편 분산    평균   2461  (참 2500)
재현성이 0 으로 잘린 비율: 5 %
```

시편 분산 평균(2461)이 참값(2500)보다 약간 작은 것은 시편이 10개뿐이라 생기는 표본 변동입니다(300회 평균의 표준오차 ≈ 2500·√(2/9)/√300 ≈ 68). 모두 ±10 % 안이면 계산기는 정상입니다.

## 7. 검증 방법과 완료 기준

| 항목 | 지표 | 합격 기준 | 불합격 시 |
|---|---|---|---|
| 계산기 | §6.3 모의실험 | EV, AV, PV 분산 평균이 참값 ±10 % 이내 | 코드 수정 |
| 반복성 | 10회 연속 s | **s ≤ 5 µm** (A2) | F2 노출·프레임 평균 재조정, C7 진동 점검 |
| 치우침 | \|bias\| 와 CI | \|bias\| ≤ 5 µm 이고, 유의하면 보정 적용 | D2/D5 재교정 |
| 직선성 | 20 mm에서 예측 치우침 | **\|a + 20b\| ≤ 5 µm** 또는 회귀 보정 적용 후 잔여 ≤ 5 µm | D2 레이저 평면 재교정 |
| 안정성 | I-MR 신호 | 기준 기간 20 세션 중 신호 0개 | 원인 제거 후 기준 기간 재수집 |
| Gage R&R | %GRR | **< 30 % (M5)**, 목표 < 10 % | 아래 개선 후 재시험 |
| 구별 능력 | ndc | **≥ 5** | 시편 범위를 넓히거나 GRR 감소 |
| 공차 대비 | %P/T (공차 폭 200 µm) | ≤ 30 % | 공차 재정의(A2) 검토 |
| 기록 | 원자료 CSV, 그림, 보고서 | §3 산출물 전부 존재 | – |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 시편 10개를 모두 같은 조건으로 출력 | σ_PV가 작아 %GRR이 40 % 이상, ndc 1~2 | 유량 90~110 %처럼 일부러 범위를 넓힌 시편 사용, %P/T 함께 보고 |
| 측정자가 이전 측정값을 봄 | 반복값이 비정상적으로 비슷, σ_EV 과소 | 블라인드 순서표, 결과는 분석 담당만 열람 |
| 재장착 없이 반복 | 반복성만 좋아 보이고 본 실험에서 산포 증가 | 매 측정마다 떼었다 다시 장착 |
| 측정 순서를 시편 순서대로 | 시간 드리프트가 시편 효과로 섞임 | 무작위 순서 (seed 기록) |
| %GRR을 분산 비율로 계산 | 값이 훨씬 작게 나옴 (9.6 % 대신 0.9 %) | AIAG 정의는 **표준편차 비율** |
| 음수 분산을 그대로 사용 | √ 계산에서 NaN | 0으로 자르고 보고서에 "0으로 절단" 표기 |
| 관리 한계를 매번 새 데이터로 다시 계산 | 서서히 생기는 드리프트를 못 잡음 | 기준 기간 한계를 고정, 재교정 때만 새로 정함 |
| 관리 한계를 사양 공차와 혼동 | "공차 안이니 괜찮다"며 이상 신호 무시 | 관리 한계는 "평소와 다른지", 공차는 "합격인지" — 별개 |
| 높이맵 점들을 반복으로 취급 | n이 수십만, p값 0 | 스캔 1회 = 값 1개 (H8 유사반복 주의) |
| 치우침이 유의한데 보정 안 함 | I3에서 평균 차이가 유의 | 보정 + I1 반영 |

## 9. 위험 요소

- **M5 미통과 (%GRR > 30 %)**: 본 실험(W18) 시작이 늦어집니다. 대응: %EV가 크면 프레임 평균·노출(F2), 레이저 출력, 차광(C5) 개선 / %AV가 크면 키네마틱 지그(C3)와 작업표준 개선. 개선 후 재시험에 약 1주 필요 → K4 위험표에 1주 버퍼 확보.
- **측정자 인원 부족**: 2~4명 연구실에서 3명을 모으기 어려울 수 있습니다. 측정자 2명 + 날짜 요인 또는 측정자 1명 × 3일(재장착 포함)로 대체하고 보고서에 명시합니다.
- **시편 자체 변화**: PLA 시편이 3일 동안 흡습·크리프로 수 µm 변할 수 있습니다. 시편을 데시케이터에 보관하고, 안정성 기준 시편은 금속(게이지 블록 조합)을 씁니다.
- **겨울 실내 온도 변동**: 1월 난방으로 일간 온도가 3 °C 이상 변하면 안정성 관리도에 주기성이 보입니다. 측정 시 온도 기록(F3)을 같이 그려 확인합니다.
- **캘리브레이션 변경**: MSA 도중 재교정하면 결과가 섞입니다. MSA 기간 중 CAL-ID를 하나로 고정하고, 바뀌면 그 이후 데이터만으로 다시 분석합니다.

## 10. 기록 양식

**Gage R&R 원자료** (`results/msa/grr_data.csv`)

```csv
part,operator,trial,y,scan_id,date,cal_id,room_temp_C
GRR-P01,A,1,,,,,
```

**안정성 기록** (`results/msa/stability_log.csv`)

```csv
session,date,cal_id,operator,room_temp_C,value_um,signal,action
1,2027-01-12,,,,,,
```

**치우침·직선성 원자료** (`results/msa/linearity.csv`)

```csv
ref_mm,ref_cert_um,trial,meas_mm,meas_dev_um,scan_id
1,,1,,,
```

**MSA 판정표**

| 항목 | 값 | 기준 | 판정 | 비고 |
|---|---|---|---|---|
| 반복성 s [µm] | | ≤ 5 | | |
| 치우침 [µm] (95 % CI) | | \|bias\| ≤ 5 | | 보정 여부: |
| 직선성 기울기 [µm/mm] (p) | | 20 mm 예측 ≤ 5 µm | | |
| 안정성 신호 수 | | 0 | | |
| %EV / %AV | | – | | |
| %GRR | | < 30 % (목표 < 10 %) | | |
| ndc | | ≥ 5 | | |
| %P/T | | ≤ 30 % | | |
| **M5** | | | 통과 / 미통과 | 검토자: |

## 11. 참고 자료

- AIAG, *Measurement Systems Analysis (MSA) Reference Manual*, 4th edition (2010)
- ISO 22514-7, *Statistical methods in process management — Capability and performance — Part 7: Capability of measurement processes*
- D. C. Montgomery, *Introduction to Statistical Quality Control* (관리도, I-MR, Gage R&R ANOVA 장)
- NIST/SEMATECH *e-Handbook of Statistical Methods* (Gauge R&R, 관리도 장)
- ISO 7870-2, *Control charts — Part 2: Shewhart control charts*
- statsmodels 문서: `statsmodels.formula.api.ols`, `statsmodels.stats.anova.anova_lm`
- 상위 문서: [BLUEPRINT.md I2](../../BLUEPRINT.md#i2-측정시스템분석-msa)
