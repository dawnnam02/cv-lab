# H8. 통계 분석

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: H. 처리·분석

| 항목 | 내용 |
|---|---|
| 기간 | 2027-01-12 ~ 2027-02-01 (W15-17) |
| 우선순위 | 보통 |
| 트랙 | 실험·품질 |
| 선행 요소 | [H5 높이 지표](H5-height-metrics.md), [H6 윤곽 지표](H6-contour-metrics.md), [H7 치수·형상 지표](H7-dimensional-metrics.md), [I1 측정 불확도](../I-reliability/I1-uncertainty.md) (실질적 의미 판단 기준 U), [E3 시편 설계](../E-specimen/E3-test-artifact.md) |
| 후행 요소 | [I2 MSA](../I-reliability/I2-msa.md) (분산 성분·반복성 자료 공유), [I3 교차검증](../I-reliability/I3-cross-validation.md), [J4 시각화·리포트](../J-software/J4-visualization-report.md), [K5 산출물·논문 구성](../K-management/K5-deliverables-paper.md) |
| 관련 마일스톤 | M6: 최종 보고서 (W22-24). 이 기간(W15-17)에 분석 계획·코드를 완성하고, 본 실험(W18-21) 데이터에 그대로 적용합니다 |

---

## 1. 목적

"조건 A 와 조건 B 의 오차가 **정말로** 다른가?", "차이가 **얼마나** 큰가?", "그 차이가 측정 장비로 **구분할 수 있는** 크기인가?" 에 답합니다.

이 요소의 산출물:
1. **실험 계획**: 조건 수, 시편 수, 스캔 반복 수, 무작위 실행 순서표
2. **분석 단위 규칙**: 시편 1개 = 요약값 1개 (유사반복 금지)
3. **분석 코드**: 신뢰구간, t-검정, 일원·이원 분산분석(statsmodels), 정규성·등분산 확인, 비모수 대안, 효과크기, 사후검정, 검정력
4. **판단 규칙**: 통계적으로 유의 + **차이 > 측정 불확도 U (I1)** 일 때만 "실질적 차이"

---

## 2. 배경 지식 (초보자용)

### 2.1 실험의 층 구조
```
조건 (예: 인쇄 속도 30 / 60 / 90 mm/s)
 └─ 시편 (조건마다 3개 이상 출력)          ← 출력할 때마다 달라지는 "진짜 흩어짐"
     └─ 스캔 (시편마다 3회 측정)           ← 측정 장비의 흩어짐 (I2 반복성)
         └─ 격자 칸 (수십만 개)            ← 서로 상관된 값들. 독립 표본 아님
```
조건 효과를 판단할 때 비교해야 하는 흩어짐은 **시편 간 흩어짐**입니다. 스캔을 여러 번 하는 것은 측정 노이즈를 줄이고 반복성을 확인하기 위함이지, 표본 수를 늘리는 것이 아닙니다.

### 2.2 유사반복(pseudo-replication)
높이맵 칸 수십만 개를 표본으로 t-검정하면 p 값이 10⁻³⁰⁰ 처럼 작아집니다. 이웃 칸이 서로 비슷하고(공간 상관), 같은 시편의 칸들은 그 시편 고유의 치우침을 공유하기 때문입니다.
6.3 데모: **참 차이가 0** 인데 칸 단위 검정은 300번 중 **98 %** 에서 "유의"라고 판정합니다. 시편 단위 검정은 7 % (이론값 5 %) 입니다.
→ **규칙: 스캔 3회 평균 → 시편 요약값 1개 → 그 값들로 검정** (청사진 H8).

### 2.3 신뢰구간
평균 ± `t(0.975, n−1) × s / √n`. 시편 3개면 t = 4.303 이라서, 같은 표준편차라도 시편 10개(t = 2.262)일 때보다 구간이 약 3.5배 넓습니다 (√n 효과 포함). **시편 3개의 신뢰구간은 넓다**는 것을 결과 해석에 반영합니다.

### 2.4 어떤 검정을 쓰나
| 상황 | 기본 (정규성 OK) | 대안 (정규성 의심) |
|---|---|---|
| 두 조건 | **Welch t-검정** (`equal_var=False`) | Mann–Whitney U |
| 세 조건 이상, 요인 1개 | **일원 분산분석** + Tukey HSD | Kruskal–Wallis (+ Dunn 등) |
| 요인 2개 (예: 속도 × 온도) | **이원 분산분석** (교호작용 포함) | 변환(로그) 후 분산분석, 또는 순열검정 |
| 같은 시편을 두 방법으로 (장비 비교) | 대응 t-검정 / Bland–Altman (I3) | Wilcoxon 부호순위 |

- **정규성**: 분산분석 **잔차**에 Shapiro–Wilk + Q-Q 플롯. 표본이 작으면(n ≤ 5/조건) 검정력이 낮아 "정규성 기각 안 됨 ≠ 정규"임을 기억합니다.
- **등분산**: Levene 검정. 다르면 Welch 방식 사용.
- 비모수 검정은 표본이 아주 작으면 **도달 가능한 최소 p 값**이 있습니다 (조건 3개 × 3개 Kruskal–Wallis 는 약 0.027). 6.2 데모에서 Kruskal p = 0.0273 이 바로 그 값입니다.

### 2.5 효과크기 — "얼마나 다른가"
- **Cohen's d** = (평균 차) / (합동 표준편차). 표본이 작으면 크게 나오므로 **Hedges' g**(보정) 를 함께 씁니다.
- **η²** = 요인 제곱합 / 전체 제곱합 (설명된 비율). 표본이 작으면 과대 → **ω²** 를 함께 씁니다. 이원 분산분석에서는 **부분 η²** 를 씁니다.
- p 값은 "차이가 있다/없다"만, 효과크기는 "얼마나"를 말합니다. 논문 표에는 둘 다 넣습니다.

### 2.6 다중 비교
조건 3개를 두 개씩 비교하면 3번 검정합니다. 각각 α = 0.05 면 하나라도 우연히 유의할 확률이 약 14 %. **Tukey HSD** (모든 쌍) 또는 Holm 보정을 씁니다.

### 2.7 실질적 의미 — 불확도와 비교 (청사진 H8 판단 규칙)
통계적으로 유의해도 **차이가 측정 불확도 U (I1, 예: 높이 16 µm, k = 2)** 보다 작으면 "측정 장비로 구분할 수 있는 차이"라고 주장하지 않습니다. 6.2 데모의 v60 vs v90 (차이 15.7 µm, p = 0.025) 이 그런 경우입니다.
(엄밀히는 두 평균 차이의 불확도를 따로 계산해야 합니다. 두 조건에 공통인 계통 요인(교정 등)은 차이에서 상쇄되고, 독립 요인은 √2 배가 됩니다 → I1 에서 "차이용 불확도"를 별도로 정리하면 더 정확합니다.)

### 2.8 검정력 — 시편을 몇 개 만들어야 하나
검정력 = 실제로 차이가 있을 때 그것을 찾아낼 확률 (보통 0.8 목표).
6.2 데모: α = 0.05, 검정력 0.8 기준으로 **d = 2 이면 조건당 6개, d = 1.5 면 9개** 가 필요하고, **조건당 3개로는 d ≥ 3.07 인 아주 큰 차이만** 확실히 찾습니다.
→ 청사진의 최소 "시편 ≥ 3 × 스캔 ≥ 3" 은 지키되, **예비 실험(W15)에서 시편 간 표준편차를 추정해 필요한 시편 수를 계산**하고, 예산(K3)이 허락하면 조건당 5~6개로 늘립니다.

### 2.9 무작위화
출력·측정 순서를 조건별로 몰아서 하면(예: 월요일 v30, 화요일 v90), 날짜에 따른 온도·노즐 마모·캘리브레이션 변화가 조건 효과처럼 보입니다. **시드를 고정한 무작위 순서표**로 진행합니다 (J2 재현성).

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 내용 |
|---|---|---|---|
| 입력 | `data/experiments.csv` | CSV | scan_id, specimen_id, condition(요인들), repeat, 날짜, 순서 (F3) |
| 입력 | `results/*/*_H5_height_metrics.csv`, `_H6_*.csv`, `_H7_*.csv` | CSV | 스캔 단위 지표 |
| 입력 | I1 불확도 예산 | YAML | 지표별 확장불확도 U (k = 2) |
| 산출 | `results/run_order.csv` | CSV | 무작위 실행 순서 (시드 기록) |
| 산출 | `results/summary_scans.csv` | CSV | 모든 스캔 × 지표 (긴 형식: scan_id, specimen_id, 요인, metric, region, value) |
| 산출 | `results/summary_specimens.csv` | CSV | 시편 단위 요약 (스캔 평균, 스캔 표준편차, n_scans) — **분석 단위** |
| 산출 | `results/stats_<metric>.csv` | CSV | 조건별 평균·95 % CI, 검정 결과(통계량, p, 보정 p), 효과크기, 가정 확인 p, U 대비 판단 |
| 산출 | `results/anova_<metric>.txt` | 텍스트 | 분산분석표 전문 |
| 산출 | `results/power_plan.csv` | CSV | 효과크기별 필요 시편 수 |
| 산출 | 그림 (J4) | PNG | 시편 단위 점그림 + 평균·CI, 잔차 Q-Q 플롯, 교호작용 그림 |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 분석 단위 | 칸 / 스캔 / **시편** | **시편** (스캔 평균) | 2.2 유사반복 |
| 반복 수 | 시편 3 × 스캔 3 / **예비실험 후 결정** | 최소 **3 × 3** (청사진), 목표 조건당 시편 **5~6** | 2.8 검정력 |
| 주 지표 (반응변수) | H5 평균·RMS, H6 평균 부호 윤곽 거리, H7 주요 치수 | 연구 질문별 **사전에 1~3개 지정** | 지표를 많이 보면 우연히 유의한 것이 생김 |
| 두 조건 검정 | Student t / **Welch t** | **Welch** | 등분산 가정 불필요, 손해 거의 없음 |
| 다조건 검정 | **일원/이원 ANOVA (statsmodels)** | ANOVA + Tukey HSD | 청사진 H8 |
| 정규성 확인 | Shapiro–Wilk + **Q-Q 플롯** | 둘 다 (잔차 기준) | 작은 표본에서 검정만으로는 부족 |
| 비모수 대안 | Mann–Whitney, Kruskal–Wallis | 정규성 의심 시 **병행 보고** | 결론 견고성 확인 |
| 효과크기 | d, g, η², ω², 부분 η² | **g 와 ω²** (본문), d·η² (부록) | 소표본 보정 |
| 유의수준 | 0.05 / 0.01 | **0.05** (양측), 다중비교 보정 | 관례 |
| 실질적 의미 기준 | 없음 / **I1 의 U** | **\|차이\| > U** | 청사진 H8 판단 규칙 |
| 순서 | 조건별 묶음 / **무작위** | **무작위, 시드 42** | 2.9 |
| 혼합모형 | 사용 / **선택** | 시편 단위 분석이 기본, 스캔 단위 혼합모형(MixedLM)은 확인용 | 초보자에게 해석이 쉬운 방법 우선 |

---

## 5. 수행 절차

1. **분석 계획서 작성 (W15, 1일)** — 데이터 보기 **전에** 고정
   - [ ] 연구 질문 → 요인·수준 → 주 지표 1~3개 → 검정 방법 → 판단 규칙(유의 + U) 을 한 쪽으로 문서화
   - [ ] 지도교수 확인 후 날짜와 함께 저장 (나중에 바꾸면 변경 이유 기록)
2. **예비 실험·검정력 (W15, 2일)**
   - [ ] 기준 조건으로 시편 3개 × 스캔 3회 → 시편 간 표준편차 s_between 추정
   - [ ] 관심 있는 최소 차이 Δ (예: U 의 1.5배 = 24 µm) → d = Δ / s_between → `TTestIndPower` 로 필요 시편 수 계산 → `power_plan.csv`
   - [ ] K3 예산·K1 일정과 맞춰 최종 시편 수 결정
3. **실행 순서표 (W15, 0.5일)**
   - [ ] `run_order()` 로 출력 순서 생성 (시드 42), 측정 순서도 별도 무작위화
   - [ ] `experiments.csv` 에 순서·날짜 열 추가
4. **집계 코드 (W16, 2일)**
   - [ ] 모든 스캔의 H5~H7 CSV 를 읽어 `summary_scans.csv` (긴 형식) 생성
   - [ ] `specimen_summary()` 로 `summary_specimens.csv` 생성, 스캔 표준편차가 I2 반복성과 비슷한지 확인
5. **분석 코드 (W16~17, 3일)**
   - [ ] 6장 함수로 조건별 평균·CI, Welch t / ANOVA, Tukey, 효과크기, 가정 확인, 비모수 병행
   - [ ] U 대비 판단 열 추가, `stats_<metric>.csv` 저장
   - [ ] 합성 데이터(6.2·6.3·6.4) 로 코드가 정답을 내는지 확인, `pytest -q test_h8.py` 통과
6. **그림 (W17, 1일)**
   - [ ] 시편 단위 점그림 + 평균 ± 95 % CI, Q-Q 플롯, 이원 교호작용 그림 (J4)
7. **본 실험 적용 (W18~21)**
   - [ ] 데이터가 들어올 때마다 같은 스크립트로 갱신, 계획서와 다른 분석은 "탐색적"으로 표시

---

## 6. Python 구현

### 6.1 모듈 `h8_statistics.py`

```python
"""H8. 통계 분석 모듈. 최종적으로 src/cvlab/stats.py 에 합칩니다.
분석 단위 = 시편 1개당 요약값 1개 (스캔 반복은 먼저 평균)."""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.power import TTestIndPower


def specimen_summary(scans, value, cond="condition", spec="specimen"):
    """스캔 단위 표 → 시편 단위 표. 같은 시편의 반복 스캔은 평균 (반복 스캔 흩어짐도 함께 기록)."""
    g = scans.groupby([cond, spec])[value]
    return g.agg(value="mean", scan_sd="std", n_scans="count").reset_index().rename(columns={"value": value})


def mean_ci(x, conf=0.95):
    """평균 ± t 분포 신뢰구간 (반폭 = t × s/√n)"""
    x = np.asarray(x, float); n = len(x)
    half = stats.t.ppf(0.5 + conf / 2, n - 1) * x.std(ddof=1) / np.sqrt(n)
    return x.mean(), x.mean() - half, x.mean() + half


def cohens_d(x, y):
    """Cohen's d (합동 표준편차) 와 소표본 보정 Hedges' g"""
    x, y = np.asarray(x, float), np.asarray(y, float)
    nx, ny = len(x), len(y)
    sp = np.sqrt(((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / (nx + ny - 2))
    d = (x.mean() - y.mean()) / sp
    return d, d * (1 - 3 / (4 * (nx + ny) - 9))


def one_way_anova(df, value, factor):
    """일원 분산분석 (statsmodels) + 효과크기 η², ω² + 잔차 정규성(Shapiro) + 등분산(Levene)"""
    model = smf.ols(f"{value} ~ C({factor})", data=df).fit()
    tab = anova_lm(model, typ=2)
    ss_f, ss_e = tab["sum_sq"].iloc[0], tab["sum_sq"].iloc[1]
    df_f, ms_e = tab["df"].iloc[0], ss_e / tab["df"].iloc[1]
    eta2 = ss_f / (ss_f + ss_e)
    omega2 = (ss_f - df_f * ms_e) / (ss_f + ss_e + ms_e)
    groups = [g[value].values for _, g in df.groupby(factor)]
    return {"table": tab, "eta2": eta2, "omega2": omega2,
            "shapiro_p": stats.shapiro(model.resid).pvalue,
            "levene_p": stats.levene(*groups).pvalue,
            "kruskal_p": stats.kruskal(*groups).pvalue}


def run_order(conditions, n_specimens, seed=42):
    """출력·측정 순서 무작위화 표 (시드 고정 → 재현 가능)"""
    rows = [(c, f"{c}_s{i+1}") for c in conditions for i in range(n_specimens)]
    perm = np.random.default_rng(seed).permutation(len(rows))
    return pd.DataFrame([rows[i] for i in perm], columns=["condition", "specimen"]).rename_axis("order").reset_index()
```

### 6.2 데모 `demo_h8.py` — 3조건 × 시편 3개 × 스캔 3회

조건별 참 평균 높이 오차(치우침)는 −10 / +5 / +25 µm, 시편 간 표준편차 4 µm, 스캔 반복 표준편차 1 µm 로 만들었습니다.

```python
"""H8 데모: 3조건 × 시편 3개 × 스캔 3회 합성 실험 → 시편 단위 통계."""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.power import TTestIndPower
from h8_statistics import specimen_summary, mean_ci, cohens_d, one_way_anova, run_order

rng = np.random.default_rng(8)
U_HEIGHT = 16.0                                            # I1 확장불확도 (k=2) [um] — 실제 값으로 교체

# 0) 무작위 실행 순서
print(run_order(["v30", "v60", "v90"], 3).head(4).to_string(index=False), "\n...")

# 1) 합성 스캔 데이터: 조건별 참 평균 높이 오차(bias) −10 / +5 / +25 um
true_mean = {"v30": -10.0, "v60": 5.0, "v90": 25.0}
rows = []
for cond, mu in true_mean.items():
    for s in range(1, 4):
        spec_mu = mu + rng.normal(0, 4.0)                   # 시편 간 차이 (출력마다 다름) σ 4 um
        for r in range(1, 4):
            rows.append({"condition": cond, "specimen": f"{cond}_s{s}", "scan": r,
                         "mean_um": spec_mu + rng.normal(0, 1.0)})   # 스캔 반복 σ 1 um
scans = pd.DataFrame(rows)
spec = specimen_summary(scans, "mean_um")
print(spec.round(2).to_string(index=False))

# 2) 조건별 평균 ± 95 % 신뢰구간 (n = 시편 3개)
for cond, g in spec.groupby("condition"):
    m, lo, hi = mean_ci(g["mean_um"])
    print(f"{cond}: 평균 {m:+6.1f} um, 95 % CI [{lo:+6.1f}, {hi:+6.1f}]")

# 3) 일원 분산분석 + 가정 확인 + 사후검정
res = one_way_anova(spec, "mean_um", "condition")
print(res["table"].round(4).to_string())
print(f"η² = {res['eta2']:.3f}, ω² = {res['omega2']:.3f}, Shapiro p = {res['shapiro_p']:.3f}, "
      f"Levene p = {res['levene_p']:.3f}, (비모수) Kruskal p = {res['kruskal_p']:.4f}")
tk = pairwise_tukeyhsd(spec["mean_um"], spec["condition"])
for row in tk.summary().data[1:]:
    g1, g2, diff, p = row[0], row[1], row[2], row[3]
    verdict = "불확도보다 큼" if abs(diff) > U_HEIGHT else "불확도 이내 → 실질적 차이 판단 보류"
    print(f"  {g1} vs {g2}: 차이 {diff:+6.2f} um, 보정 p = {p:.4f}, |차이| vs U={U_HEIGHT:.0f} um: {verdict}")

# 4) 두 조건 t-검정 (Welch) + 효과크기
a = spec.loc[spec.condition == "v30", "mean_um"]; b = spec.loc[spec.condition == "v60", "mean_um"]
t = stats.ttest_ind(b, a, equal_var=False)
d, g = cohens_d(b, a)
print(f"v60 vs v30 Welch t = {t.statistic:.2f}, p = {t.pvalue:.4f}, Cohen d = {d:.2f}, Hedges g = {g:.2f}")

# 5) 검정력: 시편 수를 몇 개로 해야 하나 (양측 α = 0.05, 검정력 0.8)
pw = TTestIndPower()
for es in (1.0, 1.5, 2.0, 3.0):
    print(f"  효과크기 d = {es:.1f} → 조건당 시편 {int(np.ceil(pw.solve_power(effect_size=es, alpha=0.05, power=0.8)))}개 필요")
print(f"  조건당 3개로 80 % 검정력이 되는 최소 d = {pw.solve_power(nobs1=3, alpha=0.05, power=0.8):.2f}")
```

```text
$ python3 demo_h8.py
 order condition specimen
     0       v60   v60_s1
     1       v30   v30_s1
     2       v90   v90_s2
     3       v30   v30_s3 
...
condition specimen  mean_um  scan_sd  n_scans
      v30   v30_s1   -17.97     0.58        3
      v30   v30_s2   -19.33     0.93        3
      v30   v30_s3    -5.47     0.72        3
      v60   v60_s1     8.93     1.08        3
      v60   v60_s2     4.93     1.19        3
      v60   v60_s3     6.11     1.13        3
      v90   v90_s1    24.47     0.24        3
      v90   v90_s2    17.22     1.92        3
      v90   v90_s3    25.50     1.17        3
v30: 평균  -14.3 um, 95 % CI [ -33.2,   +4.7]
v60: 평균   +6.7 um, 95 % CI [  +1.6,  +11.8]
v90: 평균  +22.4 um, 95 % CI [ +11.2,  +33.6]
                 sum_sq   df        F  PR(>F)
C(condition)  2028.6339  2.0  36.6715  0.0004
Residual       165.9570  6.0      NaN     NaN
η² = 0.924, ω² = 0.888, Shapiro p = 0.479, Levene p = 0.699, (비모수) Kruskal p = 0.0273
  v30 vs v60: 차이 +20.91 um, 보정 p = 0.0067, |차이| vs U=16 um: 불확도보다 큼
  v30 vs v90: 차이 +36.65 um, 보정 p = 0.0003, |차이| vs U=16 um: 불확도보다 큼
  v60 vs v90: 차이 +15.74 um, 보정 p = 0.0245, |차이| vs U=16 um: 불확도 이내 → 실질적 차이 판단 보류
v60 vs v30 Welch t = 4.58, p = 0.0344, Cohen d = 3.74, Hedges g = 2.99
  효과크기 d = 1.0 → 조건당 시편 17개 필요
  효과크기 d = 1.5 → 조건당 시편 9개 필요
  효과크기 d = 2.0 → 조건당 시편 6개 필요
  효과크기 d = 3.0 → 조건당 시편 4개 필요
  조건당 3개로 80 % 검정력이 되는 최소 d = 3.07
```

**결과 읽는 법**
- **시편 표**: 스캔 표준편차(0.2~1.9 µm)는 시편 간 차이(같은 조건 안에서 수 µm~10 µm 이상)보다 훨씬 작습니다 → 스캔을 더 하는 것보다 **시편을 더 만드는 것**이 결론을 단단하게 합니다.
- **v30 의 95 % CI [−33.2, +4.7]**: 시편 하나(v30_s3)가 다른 둘과 13 µm 떨어져 있고, n = 3 이라 t = 4.303 이 곱해져 구간이 매우 넓습니다.
- **ANOVA**: F = 36.7, p = 0.0004, ω² = 0.89 → 조건이 시편 간 변동의 대부분을 설명합니다. 잔차 정규성(Shapiro p = 0.48)과 등분산(Levene p = 0.70)에 문제 신호가 없습니다. Kruskal p = 0.0273 은 이 표본 크기에서 가능한 최솟값 수준입니다(2.4 절).
- **Tukey**: v60 vs v90 은 p = 0.025 로 유의하지만 차이 15.7 µm 가 U = 16 µm 보다 작아 **"실질적 차이 판단 보류"** 입니다. 이런 경우 시편 수를 늘리거나 불확도를 줄여야 결론을 낼 수 있습니다.
- **Cohen d = 3.74 → Hedges g = 2.99**: 시편 3개씩이면 d 가 크게 부풀려지므로 g 를 보고합니다.
- **검정력**: 조건당 3개로는 d ≥ 3.07 만 80 % 확률로 찾습니다.

### 6.3 데모 `demo_h8_pseudo.py` — 유사반복의 위험

```python
"""H8 데모: 유사반복(pseudo-replication). 두 조건의 '참 차이 = 0' 인데 격자 칸을 표본으로 쓰면?"""
import numpy as np
from scipy import stats
from scipy.ndimage import gaussian_filter

rng = np.random.default_rng(11)

def specimen_error_map(n=100, res=0.02, corr_mm=0.3):
    """시편 1개의 높이 오차 지도 [um]: 시편 고유 치우침(σ 5 um) + 공간 상관 잡음(상관 길이 0.3 mm)"""
    field = gaussian_filter(rng.normal(0, 1, (n, n)), corr_mm / res)
    field *= 4.0 / field.std()                         # 공간 잡음 크기 4 um
    return rng.normal(0, 5.0) + field

def one_experiment(n_spec=3):
    A = [specimen_error_map() for _ in range(n_spec)]  # 조건 A 시편 3개
    B = [specimen_error_map() for _ in range(n_spec)]  # 조건 B 시편 3개 (참 차이 0)
    p_cell = stats.ttest_ind(np.concatenate([a.ravel() for a in A]),
                             np.concatenate([b.ravel() for b in B])).pvalue    # 잘못: 칸 = 표본 (3만 개씩)
    p_spec = stats.ttest_ind([a.mean() for a in A], [b.mean() for b in B]).pvalue   # 올바름: 시편 = 표본
    return p_cell, p_spec

p_cell, p_spec = one_experiment()
p_txt = f"{p_cell:.1e}" if p_cell > 0 else "< 1e-300 (컴퓨터가 0으로 표시)"
print(f"한 번의 실험: 칸 단위 p = {p_txt}  vs  시편 단위 p = {p_spec:.3f}")
P = np.array([one_experiment() for _ in range(300)])
print(f"300회 반복 시 '유의(p<0.05)' 판정 비율 (참 차이 0 이므로 5 % 근처여야 정상):")
print(f"  칸 단위 {100*(P[:,0] < 0.05).mean():.1f} %   /   시편 단위 {100*(P[:,1] < 0.05).mean():.1f} %")
```

```text
$ python3 demo_h8_pseudo.py
한 번의 실험: 칸 단위 p = < 1e-300 (컴퓨터가 0으로 표시)  vs  시편 단위 p = 0.458
300회 반복 시 '유의(p<0.05)' 판정 비율 (참 차이 0 이므로 5 % 근처여야 정상):
  칸 단위 98.3 %   /   시편 단위 7.3 %
```

- 참 차이가 0 인데 칸 단위 검정은 거의 항상(98 %) "유의"합니다. 시편 단위는 7 % 로 이론값 5 % 근처입니다 (300회 반복의 표준오차 약 1.3 %p).

### 6.4 데모 `demo_h8_twoway.py` — 이원 분산분석과 교호작용

```python
"""H8 보조 데모: 이원 분산분석 (속도 2수준 × 노즐 온도 2수준, 조건당 시편 4개) — 교호작용 포함."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

rng = np.random.default_rng(21)
rows = []
for speed in ("v30", "v90"):
    for temp in ("T200", "T220"):
        # 참 효과: 속도 +15 um, 온도 +5 um, 고속·고온 조합에서만 +10 um 추가 (교호작용)
        mu = 10 + (15 if speed == "v90" else 0) + (5 if temp == "T220" else 0) \
             + (10 if (speed, temp) == ("v90", "T220") else 0)
        for s in range(4):
            rows.append({"speed": speed, "temp": temp, "rms_um": mu + rng.normal(0, 3.0)})
df = pd.DataFrame(rows)                                   # 시편 단위 요약값 16행
model = smf.ols("rms_um ~ C(speed) * C(temp)", data=df).fit()
tab = anova_lm(model, typ=2)
tab["eta2_partial"] = tab["sum_sq"] / (tab["sum_sq"] + tab.loc["Residual", "sum_sq"])
tab.loc["Residual", "eta2_partial"] = np.nan              # 잔차 행에는 효과크기가 없음
print(tab.round(4).to_string())
print(df.groupby(["speed", "temp"])["rms_um"].mean().unstack().round(1))
```

```text
$ python3 demo_h8_twoway.py
                     sum_sq    df         F  PR(>F)  eta2_partial
C(speed)          1725.5410   1.0  131.7320  0.0000        0.9165
C(temp)            215.8298   1.0   16.4770  0.0016        0.5786
C(speed):C(temp)   130.9960   1.0   10.0006  0.0082        0.4546
Residual           157.1865  12.0       NaN     NaN           NaN
temp   T200  T220
speed            
v30    11.3  13.0
v90    26.4  39.4
```

- 속도·온도 주효과와 함께 **교호작용(p = 0.008)** 이 유의합니다. 평균표를 보면 고속(v90)에서만 온도 효과가 커집니다(26.4 → 39.4 µm) → "온도 효과"를 하나의 숫자로 요약하면 안 되고, 속도 수준별로 나눠 보고합니다.

### 6.5 단위 테스트 `test_h8.py`

```python
"""H8 단위 테스트. 실행: pytest -q test_h8.py"""
import numpy as np
import pandas as pd
from h8_statistics import mean_ci, cohens_d, specimen_summary, run_order


def test_신뢰구간_손계산과_일치():
    m, lo, hi = mean_ci([10.0, 12.0, 14.0])          # s = 2, n = 3, t(0.975, 2) = 4.303
    assert m == 12.0 and abs((hi - m) - 4.3027 * 2 / np.sqrt(3)) < 1e-3


def test_효과크기():
    d, g = cohens_d([2.0, 3.0, 4.0], [0.0, 1.0, 2.0])  # 평균 차 2, 합동 sd 1
    assert abs(d - 2.0) < 1e-12 and g < d


def test_시편_요약은_스캔을_평균():
    df = pd.DataFrame({"condition": ["A"] * 3, "specimen": ["A_s1"] * 3, "rms_um": [1.0, 2.0, 3.0]})
    s = specimen_summary(df, "rms_um")
    assert len(s) == 1 and s.rms_um.iloc[0] == 2.0 and s.n_scans.iloc[0] == 3


def test_실행순서는_시드로_재현():
    assert run_order(["a", "b"], 3, seed=1).equals(run_order(["a", "b"], 3, seed=1))
```

```text
$ python3 -m pytest -q test_h8.py
4 passed in 0.xxs
```

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 신뢰구간 계산 | 손계산 예 (pytest) | 반폭 = 4.3027 × s/√3 (오차 < 10⁻³) |
| 효과크기 | 손계산 예 (pytest) | d = 2.0 정확, g < d |
| 유사반복 방지 | 6.3 데모 300회 | 시편 단위 거짓 유의율 2~9 % (이론 5 %) |
| 집계 무결성 | `summary_specimens.csv` | 모든 시편의 n_scans = 계획값, 누락·중복 0 |
| 분석 계획 준수 | 계획서 vs 최종 분석 | 주 지표·검정 방법이 계획서와 일치 (변경 시 사유 기록) |
| 가정 확인 | 모든 ANOVA | 잔차 Q-Q 플롯 저장, Shapiro·Levene p 기록, 비모수 결과 병행 |
| 실질적 의미 | 모든 유의한 차이 | U 대비 판단 열이 채워져 있음 |
| 검정력 계획 | 예비 실험 후 | `power_plan.csv` 와 최종 시편 수 결정 근거 기록 |
| 재현성 | 같은 입력으로 재실행 | 결과 파일이 완전히 동일 (시드 고정) |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 칸·점을 표본으로 검정 | p < 10⁻¹⁰⁰, 모든 것이 유의 | 시편 요약값으로 검정 (6.3) |
| 스캔 반복을 독립 표본으로 셈 | n 이 3배로 부풀어 p 가 작아짐 | 스캔은 평균 후 시편 1개 = 1값 |
| p 값만 보고 | 차이 크기를 알 수 없음 | 평균 차, 95 % CI, g, ω² 함께 |
| 유의 = 의미 있음 | 불확도보다 작은 차이를 결론으로 | U 대비 판단 규칙 |
| 데이터를 본 뒤 지표·검정 선택 | 우연히 유의한 결과만 보고(p-hacking) | 분석 계획서 사전 고정 |
| 다중 비교 무보정 | 쌍 비교 중 하나가 우연히 유의 | Tukey HSD 또는 Holm |
| 정규성 검정 통과 = 정규 | 소표본에서 검정력 부족 | Q-Q 플롯 + 비모수 병행 |
| 교호작용 무시 | 주효과 해석이 조건에 따라 틀림 | 이원 ANOVA 에 `*` 로 교호작용 포함, 평균표 확인 |
| 조건별로 몰아서 출력·측정 | 날짜 효과가 조건 효과로 둔갑 | 무작위 순서표 |
| 이상한 시편을 조용히 제외 | 결과가 좋아 보이지만 재현 불가 | 제외 기준을 계획서에 미리 정하고, 제외 시 사유와 포함 결과도 보고 |

---

## 9. 위험 요소

- **시편 수 부족**: 예산·시간 때문에 조건당 3개에 머물면 중간 크기 효과는 찾지 못합니다(2.8). "차이를 찾지 못함"을 "차이가 없음"으로 쓰지 않고, 탐지 가능한 최소 효과(d ≈ 3)를 함께 적습니다.
- **측정 장비 변화**: 본 실험 기간(4주) 동안 캘리브레이션이 틀어지면 시간 효과가 생깁니다. I2 안정성 관리도로 감시하고, 재교정 전후를 공변량(블록)으로 넣는 것을 검토합니다.
- **시편 간 변동의 원인 혼입**: 필라멘트 롤, 베드 위치(중앙/가장자리)가 조건과 겹치면 효과가 섞입니다. 베드 위치도 무작위화하거나 요인으로 기록합니다.
- **지표 간 상관**: H5 RMS 와 H6 윤곽 거리가 같은 원인(과압출)에 반응하면, 두 지표에서 각각 유의한 것은 독립된 두 증거가 아닙니다. 해석에서 이를 밝힙니다.

---

## 10. 기록 양식

분석 계획서 (YAML, 데이터 보기 전에 작성)
```yaml
plan_id: STAT-PLAN-2027-01-12
research_question: "인쇄 속도가 윗면 높이 치우침에 영향을 주는가"
factors:
  speed: [v30, v60, v90]
response_metrics:                     # 주 지표 1~3개
  - {name: mean_um, source: H5, region: top_surface}
  - {name: mean_signed_um, source: H6, feature: outer_contour}
replication: {specimens_per_condition: 5, scans_per_specimen: 3}
analysis_unit: specimen
tests: {primary: one_way_anova, posthoc: tukey_hsd, nonparametric: kruskal}
alpha: 0.05
effect_sizes: [hedges_g, omega2]
practical_threshold: {source: I1, U_um: 16, k: 2}
exclusion_rules: "스캔 커버리지 < 80 % 또는 FRE > 10 um 인 스캔은 재측정"
random_seed: 42
approved_by: ""
date: 2027-01-12
```

결과 요약표 (지표마다 1장)

| 비교 | 평균 차 µm | 95 % CI | 통계량 | p (보정) | g / ω² | \|차이\| vs U | 결론 |
|---|---|---|---|---|---|---|---|
| v30 vs v60 | | | | | | | |
| v30 vs v90 | | | | | | | |
| v60 vs v90 | | | | | | | |

---

## 11. 참고 자료

- Hurlbert, S. H. (1984). Pseudoreplication and the design of ecological field experiments. *Ecological Monographs*, 54(2).
- Montgomery, D. C. *Design and Analysis of Experiments* (Wiley) — 무작위화, 분산분석, 검정력
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.) — d, 검정력
- Hedges, L. V. (1981). Distribution theory for Glass's estimator of effect size and related estimators. *Journal of Educational Statistics*, 6(2).
- Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality. *Biometrika*, 52.
- statsmodels 문서: `statsmodels.formula.api.ols`, `statsmodels.stats.anova.anova_lm`, `pairwise_tukeyhsd`, `TTestIndPower`, (선택) `MixedLM`
- SciPy 문서: `scipy.stats.ttest_ind`, `shapiro`, `levene`, `kruskal`, `mannwhitneyu`, `t`
- JCGM 100:2008 (GUM) — 불확도와 비교하는 판단 (I1)
- 청사진 관련 절: [BLUEPRINT](../../BLUEPRINT.md) H8, I1, I2, K1, K3
