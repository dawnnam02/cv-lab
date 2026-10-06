# I1. 측정 불확도 (GUM 방식)

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: I. 측정 신뢰성 검증

| 항목 | 내용 |
|---|---|
| 기간 | 2027-01-12 ~ 2027-02-01 (W15-17) |
| 우선순위 | 높음 |
| 트랙 | 실험·품질 |
| 선행 요소 | [D2 레이저 평면](../D-calibration/D2-laser-plane.md) · [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) · [C6 온도](../C-mechanics/C6-temperature.md) · [E1 표면 광학 특성](../E-specimen/E1-surface-optics.md) · [H4 정합](../H-analysis/H4-registration.md) · [H5 높이 지표](../H-analysis/H5-height-metrics.md) · [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) · [I2 MSA](I2-msa.md) (같은 기간 병행, 반복성 값 공급) |
| 후행 요소 | [H8 통계 분석](../H-analysis/H8-statistics.md) · [I3 교차검증](I3-cross-validation.md) · [K5 산출물·논문](../K-management/K5-deliverables-paper.md) |
| 관련 마일스톤 | M5 (MSA·불확도 완료, %GRR < 30 %) |

## 1. 목적

이 요소의 목적은 **"우리 센서로 잰 높이·치수 값이 참값에서 얼마나 벗어나 있을 수 있는가"를 숫자 하나(확장불확도 U)로 정하는 것**입니다.

- 결과를 "높이 오차 −0.050 mm" 가 아니라 **"−0.050 ± 0.016 mm (k = 2)"** 처럼 보고할 수 있게 합니다.
- `|오차| < U` 이면 "측정 장비로는 구분할 수 없는 수준"으로 판정합니다. 가공 오차와 측정 오차를 가르는 기준이 됩니다.
- H8에서 "통계적으로 유의하지만 U보다 작은 차이"를 걸러 내는 기준값을 줍니다.
- I3 교차검증에서 "두 장비의 차이가 이 정도 안에 들어와야 한다"는 기대 범위를 줍니다.

**만들 것은 두 가지 예산**입니다.
1. **높이(Z) 예산**: 단차 높이·높이 오차(H5)용. BLUEPRINT 예시 기준 u_c ≈ 8 µm, U ≈ 16 µm.
2. **XY 길이 예산**: 치수·윤곽 지표(H6, H7)용. 경계 추출과 격자 크기가 지배적이라 Z보다 큽니다(예: U ≈ 21 µm).

## 2. 배경 지식 (초보자용)

### 2.1 오차와 불확도는 다릅니다

| 용어 | 뜻 | 예 |
|---|---|---|
| **오차 (error)** | 측정값 − 참값. 참값을 모르면 알 수 없음 | 게이지 블록 10.000 mm를 10.004 mm로 잼 → 오차 +4 µm |
| **불확도 (uncertainty)** | "참값이 측정값 주변 어느 범위에 있을지"의 크기 | 10.004 ± 0.016 mm |
| **보정 (correction)** | 알고 있는 계통 오차를 빼 주는 값 | 치우침 +4 µm를 알면 측정값에서 4 µm를 뺌 |

알고 있는 치우침(bias)은 **보정해서 없애고**, 보정 후에도 남는 "모르는 정도"만 불확도로 남깁니다. 보정하지 않기로 했다면 그 치우침을 불확도에 넣어야 합니다(흔한 누락).

### 2.2 측정 모델

불확도 계산은 "측정 결과가 어떤 입력들로 만들어지는가"라는 식(측정 모델)에서 시작합니다. 이 과제의 높이 오차 측정 모델은 다음과 같이 씁니다.

```
e = (H_meas − H_ref) + δ_cal + δ_rep + δ_surf + c_T·ΔT + δ_reg + δ_stage + δ_gauge
```

- `H_meas − H_ref` : H5에서 계산한 높이 오차 (부호: 측정 − 기준, + = 재료 과다)
- `δ_…` : 각 요인이 만드는 "모르는 작은 편차". 평균값(추정값)은 0, 크기만 불확도로 평가합니다.
- `c_T` : **감도계수**. 입력 1 단위가 바뀔 때 결과가 얼마나 바뀌는지입니다.

### 2.3 A형과 B형

| 구분 | 구하는 방법 | 이 과제의 예 | 자유도 ν |
|---|---|---|---|
| **A형** | 반복 측정의 통계 (표준편차) | 10회 반복 스캔, 10회 재정합 | n − 1 |
| **B형** | 인증서, 사양서, 물리 계산, 과거 실험 | 게이지 블록 인증서, 스테이지 직진도 사양, 온도 기록 범위 | 보통 ∞ |

A형이 "더 좋은" 것이 아닙니다. 둘 다 **표준불확도 u (표준편차 1개 크기)** 로 바꾼 뒤 똑같이 합칩니다.

A형에서 주의: 본 실험에서 **한 번만 스캔한 값**을 쓰면 u = s (표준편차 그대로)이고, **n회 평균한 값**을 쓰면 u = s/√n 입니다. 반복 실험을 10회 했다고 무조건 √10 으로 나누면 안 됩니다. 계산기의 `n_avg` 가 이것을 뜻합니다.

### 2.4 B형: 범위(±a)를 표준불확도로 바꾸는 법

사양서에는 보통 "±5 µm" 처럼 **범위**만 적혀 있습니다. 그 범위 안에서 값이 어떻게 퍼져 있다고 볼지(분포)를 정하고 나눕니다.

| 분포 | 언제 쓰나 | u = | ±1 µm 일 때 u |
|---|---|---|---|
| **직사각형(균일)** | "±a 안 어디든 같은 확률" — 모를 때 기본값 | a/√3 | 0.577 µm |
| 삼각형 | 가운데일 가능성이 더 높다는 근거가 있을 때 | a/√6 | 0.408 µm |
| U자(아크사인) | 주기적으로 오가는 값 (에어컨 on/off 온도) | a/√2 | 0.707 µm |
| 정규 (인증서) | "U = 0.4 µm, k = 2" 처럼 주어질 때 | U/k | – |
| 분해능 | 눈금·격자 간격 δ (전체 폭) | δ/√12 | – |

### 2.5 합성, 자유도, 확장

1. **합성 표준불확도** (요인들이 서로 독립일 때): `u_c = √( Σ (c_i · u_i)² )`
   - 제곱해서 더하므로 **가장 큰 요인 1~2개가 거의 전부**를 결정합니다. 작은 요인을 아무리 줄여도 u_c는 거의 안 변합니다.
   - 두 요인이 같은 원인을 공유하면(상관) 공분산 항 `2·c_i·c_j·u_i·u_j·r_ij` 가 추가됩니다. 이 과제에서는 **같은 원인을 두 번 세지 않도록 요인을 나누는 것**으로 피합니다 (§8).
2. **유효 자유도** (Welch–Satterthwaite): `ν_eff = u_c⁴ / Σ( (c_i u_i)⁴ / ν_i )`. A형 요인의 반복 수가 적으면 ν_eff가 작아지고, 포함인자 k가 2보다 커집니다.
3. **확장불확도** `U = k · u_c`. k는 t-분포에서 포함확률 95.45 %에 해당하는 값이며, ν_eff가 크면 ≈ 2입니다. BLUEPRINT 규칙대로 **k = 2 (약 95 %)** 로 보고하되, ν_eff < 30이면 t-분포 k를 씁니다.

### 2.6 감도계수 예: 온도

PLA 시편 높이 20 mm, 열팽창계수 α ≈ 68 µm/(m·°C):
`c_T = α · H = 68×10⁻⁶ /°C × 20 mm = 1.36 µm/°C`.
실내 온도 기록이 ±2.5 °C 범위에서 변했다면 u(T) = 2.5/√3 = 1.44 °C → 기여 c_T·u(T) = 1.96 µm.

감도계수를 식으로 구하기 어려우면 **수치 실험**으로 구합니다. 파이프라인 입력(예: 마커 중심 좌표)을 +u 만큼 바꿔 다시 돌리고, 결과가 변한 양 ÷ 입력 변화량을 c로 씁니다.

### 2.7 몬테카를로 방법 (JCGM 101, GUM 보충문서 1)

GUM 공식은 "결과 분포가 정규에 가깝다"고 가정합니다. 직사각형 분포 요인이 크게 지배하면 이 가정이 깨질 수 있습니다. 몬테카를로 방법은 각 입력을 분포에서 **10⁶번 무작위로 뽑아** 결과 분포를 직접 만들고, 그 95 % 구간을 GUM 구간과 비교합니다. 두 구간 끝점 차이가 허용값 δ 이하이면 GUM 결과를 그대로 써도 됩니다.

## 3. 입력과 산출물

| 구분 | 항목 | 출처 / 파일 | 형식 |
|---|---|---|---|
| 입력 | 반복성 원자료 (시편 고정 10회 스캔) | I2 `results/msa/repeatability_*.csv` | CSV, µm |
| 입력 | 레이저 평면 맞춤 잔차 RMS | D2 `config/calibration/CAL-…/laser_plane.yaml` | YAML |
| 입력 | 정합 Z 잔차 (10회 재정합) | H4 `results/registration/*_fre.csv` | CSV |
| 입력 | 표면 영향 실험 결과 | E1 실험 기록 | CSV/표 |
| 입력 | 온도 기록 | F3 메타데이터 `room_temp_C` | JSON |
| 입력 | 게이지 블록 인증서, 스테이지 사양서 | 스캔 PDF | PDF |
| 산출물 | 높이 예산 정의 | `config/uncertainty/budget_height.yaml` | YAML |
| 산출물 | XY 길이 예산 정의 | `config/uncertainty/budget_xy_length.yaml` | YAML |
| 산출물 | 예산표 | `results/uncertainty/budget_height_table.csv`, `budget_xy_length_table.csv` | CSV (UTF-8 BOM, 엑셀 호환) |
| 산출물 | 요약 (u_c, ν_eff, k, U, MC 비교) | `results/uncertainty/budget_*_summary.json` | JSON |
| 산출물 | 계산기 코드 + 테스트 | `src/cvlab/uncertainty.py`, `tests/test_uncertainty_budget.py` | Python |
| 산출물 | 불확도 보고서 1~2쪽 | `docs/reports/I1_uncertainty_<CAL-ID>.md` | Markdown |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 측정량 정의 | ① 격자 한 점의 높이 오차 ② 평면 영역 중앙값 높이 ③ 단차 높이 | **③ 단차 높이 + ② 영역 중앙값**을 각각 예산화 | 점 하나는 스펙클 영향이 커서 U가 과대. 본 실험 지표(H5, H7)와 같은 단위로 맞춰야 함 |
| 예산 개수 | Z 하나 / Z + XY | **Z, XY 길이 2개** | 오차 요인이 완전히 다름 (BLUEPRINT I1 "XY 방향 예산도 따로") |
| 포함인자 | k = 2 고정 / t-분포 k | **ν_eff ≥ 30이면 k = 2, 미만이면 t-분포 k** | 반복 수가 적을 때 과소평가 방지 |
| 반복성의 n_avg | 1 / 평균 횟수 | **본 실험에서 실제 평균한 횟수** (기본 1) | √n 오적용 방지 |
| 표면 영향 | 무시 / B형 직사각형 / 보정 후 잔여 | **E1에서 구한 최대 차이를 반폭 a로 하는 직사각형** | 재료 고정(회색 PLA)이지만 잔여 영향이 큼 |
| 알려진 치우침 | 보정 / 불확도에 포함 | **I2에서 유의하면 보정**, 보정 불확도를 요인으로 추가 | GUM 원칙: 알려진 계통 효과는 보정 |
| 상관 처리 | 공분산 계산 / 요인 재구성 | **요인 재구성(같은 원인 한 번만)** | 초보자가 공분산을 정확히 추정하기 어려움 |
| MC 검증 | 생략 / 수행 | **수행 (M = 10⁶)**, 1초 내외 | 직사각형 요인이 40 % 가까이 기여 |
| 수치 허용 자릿수 n_dig | 1 / 2 | **2로 계산, 판정은 §7 규칙** | 보고는 U를 유효숫자 2자리로 함 |
| 보고 반올림 | 반올림 / 올림 | **유효숫자 2자리, 경계면 올림** | 불확도는 과소보고보다 과대보고가 안전 |

## 5. 수행 절차

**1. 측정 모델과 측정량 확정 (W15, 1월 12~13일)**
- [ ] 높이: "10 mm 게이지 블록 단차 높이 오차", "15×15 mm 평면 윗면 중앙값 높이 오차" 2개 측정량을 문장으로 정의
- [ ] XY: "10 mm 게이지 블록 X 길이", "Ø6 mm 원기둥 지름" 측정량 정의
- [ ] §2.2 형태의 측정 모델 식을 보고서 초안에 기록

**2. 오차 요인 목록 작성 (W15, 1월 13~14일)**
- [ ] 아래 후보에서 출발하여 원인-결과(피시본) 그림을 그림: 기준물, 캘리브레이션(D1, D2, D3), 반복성(센서 노이즈+스펙클), 표면(E1), 온도(C6), 진동(C7), 정합(H4), 스테이지(C1), 바닥 평면 기준화(H3), 격자화(H1), 엣지(E2), 무광 코팅 두께(E1, 사용 시)
- [ ] 같은 원인이 두 요인에 중복되지 않는지 확인 (예: "반복성"에 진동이 이미 포함되면 진동 요인을 따로 넣지 않음)
- [ ] 예비 크기를 대략 적고, 가장 큰 요인의 **1/5 미만**(제곱 기여 4 % 미만)인 요인은 "평가했으나 무시 가능"으로 표에 남김 (지우지 말 것)

**3. A형 데이터 수집 (W15~W16, I2와 같은 세션에서)**
- [ ] 반복성: 게이지 블록 단차를 고정한 채 **연속 10회** 스캔 (I2 반복성 시험과 공유)
- [ ] 정합: 같은 스캔 데이터로 마커 정합을 **10회** 재실행(마커 점 무작위 부분 샘플 80 %) → Z 잔차 표준편차
- [ ] 캘리브레이션 잔차: D2 결과 파일에서 RMS와 점 개수(자유도) 복사
- [ ] 원자료 CSV를 `data/processed/uncertainty/` 에 저장하고 YAML에 `data:` 또는 `std:`, `dof:` 로 입력

**4. B형 값 수집 (W16, 1월 19~21일)**
- [ ] 게이지 블록 인증서의 U와 k (예: 0.4 µm, k = 2)
- [ ] 스테이지 직진도 사양 (예: ±5 µm 전 행정) → 직사각형
- [ ] 온도: F3 메타데이터에서 측정 기간 실내 온도 최솟값·최댓값 → 반폭 a = (최대 − 최소)/2
- [ ] 표면 영향: E1 실험의 "회색 PLA vs 무광 코팅 기준"의 최대 차이 → 반폭 a
- [ ] 각 값의 근거 문서(쪽 번호)를 YAML 주석에 적음

**5. 감도계수 결정 (W16)**
- [ ] 단위가 µm인 요인은 c = 1
- [ ] 온도: c_T = α · H (µm/°C). 높이 20 mm PLA → 1.36, 길이 10 mm PLA → 0.68
- [ ] 식이 없는 요인: 입력을 +u 만큼 바꿔 파이프라인을 재실행, c = Δ결과/Δ입력 (예: 마커 중심을 Z로 +5 µm 이동 → 단차 결과 변화)

**6. 계산 (W16, 1월 22~25일)**
- [ ] `python -m cvlab.uncertainty config/uncertainty/budget_height.yaml` 실행
- [ ] 기여율 열에서 **상위 2개 요인이 무엇인지** 확인. 이 요인이 개선 대상
- [ ] u_c가 A2 목표(Z 반복성 5 µm의 2배 이내 수준)와 비교해 납득되는지 검토

**7. 몬테카를로 검사 (W17)**
- [ ] M = 1,000,000으로 실행, 95 % 구간 비교
- [ ] §7 판정 규칙에 따라 GUM U 또는 MC 구간을 보고값으로 채택

**8. XY 예산 (W17)**
- [ ] 같은 절차를 `budget_xy_length.yaml` 로 반복
- [ ] 격자 간격 0.02 mm의 양자화 δ/√12 = 5.8 µm가 들어가는지 확인 (경계 직선 맞춤이 여러 점을 쓰면 줄어들 수 있으나, 보수적으로 유지)

**9. 교차 확인과 문서화 (W17, 1월 29일~2월 1일)**
- [ ] D5 검증 결과(단차 오차 < 10 µm)가 U(≈ 16 µm) 안에 드는지 확인. 넘으면 빠진 요인이 있음
- [ ] 보고서 `docs/reports/I1_uncertainty_<CAL-ID>.md` 작성: 측정 모델, 예산표, 기여율 그림, MC 비교, 보고 규칙
- [ ] **재계산 조건** 기록: 재교정(D5), 재료 변경(E1), 장비 이동 시 예산 다시 계산

## 6. Python 구현

### 6.1 예산 정의 파일 (YAML)

`config/uncertainty/budget_height.yaml` — BLUEPRINT I1 표의 요인을 원자료 형태로 적은 것입니다.

```yaml
# 높이 측정 불확도 예산 (config/uncertainty/budget_height.yaml)
# 단위: 측정량(출력)은 µm. 각 요인의 입력 단위는 unit_in 에 적고, c(감도계수)로 µm 로 바꾼다.
measurand: "단차 높이 오차 e = H_meas - H_ref (10 mm 게이지 블록 단차, 회색 PLA 표면 포함)"
unit: um
result: -50.0               # H5 에서 얻은 측정 결과 (예: 평균 높이 오차 -50 µm)
coverage_probability: 0.9545 # k ≈ 2 에 해당
components:
  - name: 기준물(게이지 블록) 인증
    type: B
    distribution: normal     # 인증서: U = 0.4 µm (k = 2)
    expanded: 0.4
    k: 2
    unit_in: um
    c: 1.0
  - name: 캘리브레이션 맞춤 잔차
    type: A
    std: 3.0                 # D2 평면 맞춤 잔차 RMS
    n_avg: 1
    dof: 50
    unit_in: um
    c: 1.0
  - name: 반복성 (센서 노이즈 + 스펙클)
    type: A                  # 시편 고정, 10회 연속 스캔한 단차 높이 편차 [µm]
    data: [3.1, -4.2, 5.8, 0.6, -5.9, 3.4, -1.2, 4.7, -2.9, -0.4]
    n_avg: 1                 # 실제 본 실험에서는 1회 스캔 값을 쓰므로 1
    unit_in: um
    c: 1.0
  - name: 표면 영향 (재료·색)
    type: B
    distribution: rectangular  # E1 실험: 회색 PLA vs 무광 코팅 차이 최대 ±8.66 µm
    half_width: 8.66
    unit_in: um
    c: 1.0
  - name: 온도
    type: B
    distribution: rectangular  # 실내 온도 기록 범위 ±2.5 °C
    half_width: 2.5
    unit_in: degC
    c: 1.36                    # = 68e-6 /°C × 20 mm × 1000 µm/mm  [µm/°C]
  - name: 정합 (Z 방향)
    type: A
    std: 2.0                 # H4 마커 정합 Z 잔차, 10회 재정합 표준편차
    n_avg: 1
    dof: 9
    unit_in: um
    c: 1.0
  - name: 스테이지 직진도
    type: B
    distribution: rectangular  # 사양서: 직진도 ±5 µm (전 행정)
    half_width: 5.0
    unit_in: um
    c: 1.0
```

### 6.2 계산기

`src/cvlab/uncertainty.py` (아래는 단독 실행 가능한 형태)

```python
"""uncertainty_budget.py — GUM 방식 불확도 예산 계산기 (+ JCGM 101 몬테카를로 검사)

사용법:
    python uncertainty_budget.py config/uncertainty/budget_height.yaml --out results/uncertainty
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

# 분포별 "반폭 a → 표준불확도 u" 나누는 수 (GUM 4.3.7, 4.3.9)
DIVISOR = {
    "rectangular": np.sqrt(3),   # 균일분포: 어디든 같은 확률, u = a/√3
    "triangular": np.sqrt(6),    # 삼각분포: 가운데가 더 그럴듯함, u = a/√6
    "u_shaped": np.sqrt(2),      # U자(아크사인) 분포: 주기적 온도 변동 등, u = a/√2
}


def standard_uncertainty(comp):
    """요인 하나 → (입력 단위의 표준불확도 u_x, 자유도 ν, 평가 설명)"""
    if comp["type"] == "A":
        n_avg = comp.get("n_avg", 1)              # 실제 결과가 몇 회 평균인지
        if "data" in comp:                        # 원자료가 있으면 직접 표준편차 계산
            x = np.asarray(comp["data"], dtype=float)
            s = x.std(ddof=1)                     # 표본표준편차 (n-1 로 나눔)
            dof = len(x) - 1
            how = f"s={s:.3f} (n={len(x)}), /√{n_avg}"
        else:
            s, dof = comp["std"], comp.get("dof", np.inf)
            how = f"s={s:.3f} (ν={dof}), /√{n_avg}"
        return s / np.sqrt(n_avg), dof, how
    dist = comp["distribution"]
    dof = comp.get("dof", np.inf)                 # B형은 보통 무한대로 둔다
    if dist == "normal":                          # 인증서: U 와 k 가 주어짐
        return comp["expanded"] / comp["k"], dof, f"U={comp['expanded']}/k={comp['k']}"
    if dist == "resolution":                      # 분해능(눈금) δ → δ/√12
        return comp["resolution"] / np.sqrt(12), dof, f"δ={comp['resolution']}/√12"
    a = comp["half_width"]
    return a / DIVISOR[dist], dof, f"a={a}/{DIVISOR[dist]:.3f}"


def gum_budget(cfg):
    """예산표(DataFrame)와 요약(dict) 반환"""
    rows = []
    for comp in cfg["components"]:
        u_x, dof, how = standard_uncertainty(comp)
        c = comp.get("c", 1.0)
        rows.append({"요인": comp["name"], "형": comp["type"], "평가": how,
                     "u_x": u_x, "단위": comp.get("unit_in", cfg["unit"]),
                     "c": c, "u_i": abs(c) * u_x, "dof": dof})
    df = pd.DataFrame(rows)
    uc = np.sqrt((df["u_i"] ** 2).sum())          # 합성 표준불확도 (독립 가정)
    df["기여율_%"] = 100 * df["u_i"] ** 2 / uc ** 2
    # Welch–Satterthwaite 유효 자유도 (GUM G.4.1)
    denom = sum(u ** 4 / d for u, d in zip(df["u_i"], df["dof"]) if np.isfinite(d))
    nu_eff = np.inf if denom == 0 else uc ** 4 / denom
    p = cfg.get("coverage_probability", 0.9545)
    k = stats.t.ppf((1 + p) / 2, nu_eff) if np.isfinite(nu_eff) else stats.norm.ppf((1 + p) / 2)
    summary = {"result": cfg.get("result", 0.0), "u_c": uc, "nu_eff": nu_eff,
               "p": p, "k": k, "U": k * uc}
    return df, summary


def monte_carlo(cfg, M=1_000_000, seed=42, typeA_t=False):
    """JCGM 101 방식: 각 입력을 분포에서 M번 뽑아 Y = result + Σ c_i·δX_i 의 분포를 만든다"""
    rng = np.random.default_rng(seed)
    y = np.full(M, float(cfg.get("result", 0.0)))
    for comp in cfg["components"]:
        u_x, dof, _ = standard_uncertainty(comp)
        c = comp.get("c", 1.0)
        if comp["type"] == "A":
            if typeA_t and np.isfinite(dof):      # JCGM 101 6.4.9: 척도 t 분포 (꼬리가 두꺼움)
                dx = u_x * rng.standard_t(dof, M)
            else:
                dx = rng.normal(0, u_x, M)
        elif comp["distribution"] == "normal":
            dx = rng.normal(0, u_x, M)
        elif comp["distribution"] == "rectangular":
            a = comp["half_width"]
            dx = rng.uniform(-a, a, M)
        elif comp["distribution"] == "triangular":
            a = comp["half_width"]
            dx = rng.triangular(-a, 0, a, M)
        elif comp["distribution"] == "u_shaped":
            a = comp["half_width"]
            dx = a * np.sin(rng.uniform(0, 2 * np.pi, M))
        elif comp["distribution"] == "resolution":
            d = comp["resolution"]
            dx = rng.uniform(-d / 2, d / 2, M)
        else:
            raise ValueError(f"모르는 분포: {comp['distribution']}")
        y += c * dx
    return y


def compare_gum_mc(summary, y, p=0.95, n_dig=2):
    """JCGM 101 8절 방식 비교: 같은 포함확률 p 의 구간 끝점 차이가 δ 이하이면 GUM 결과 '유효'"""
    uc = summary["u_c"]
    nu = summary["nu_eff"]
    k_p = stats.t.ppf((1 + p) / 2, nu) if np.isfinite(nu) else stats.norm.ppf((1 + p) / 2)
    lo_g, hi_g = summary["result"] - k_p * uc, summary["result"] + k_p * uc
    lo_m, hi_m = np.quantile(y, [(1 - p) / 2, (1 + p) / 2])   # 확률 대칭 구간
    # 수치 허용오차 δ (JCGM 101 7.9.2): u_c 를 유효숫자 n_dig 자리로 쓸 때 마지막 자리의 절반
    l = int(np.floor(np.log10(uc))) - (n_dig - 1)
    delta = 0.5 * 10 ** l
    d_low, d_high = abs(lo_g - lo_m), abs(hi_g - hi_m)
    return {"p": p, "GUM": (lo_g, hi_g), "MC": (lo_m, hi_m), "u_MC": y.std(ddof=1),
            "delta": delta, "d_low": d_low, "d_high": d_high,
            "valid": bool(d_low <= delta and d_high <= delta),
            "gum_wider": bool(lo_g <= lo_m and hi_g >= hi_m)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("budget_yaml")
    ap.add_argument("--out", default="results/uncertainty")
    ap.add_argument("--mc", type=int, default=1_000_000, help="몬테카를로 반복 수 (0이면 생략)")
    ap.add_argument("--typeA-t", action="store_true", help="A형 입력을 t 분포로 샘플링")
    ap.add_argument("--ndig", type=int, default=2, help="u_c 의 의미 있는 유효숫자 자릿수 (1 또는 2)")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.budget_yaml).read_text(encoding="utf-8"))
    df, s = gum_budget(cfg)
    pd.set_option("display.width", 140)
    print(f"측정량: {cfg['measurand']}")
    print(df.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\n합성 표준불확도 u_c = {s['u_c']:.2f} {cfg['unit']}")
    print(f"유효 자유도 ν_eff = {s['nu_eff']:.0f}")
    print(f"포함인자 k = {s['k']:.3f} (p = {s['p']})")
    print(f"확장불확도 U = {s['U']:.1f} {cfg['unit']}")
    print(f"보고: e = {s['result']:.0f} ± {s['U']:.0f} {cfg['unit']} (k = {s['k']:.2f}, 약 95 %)")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.budget_yaml).stem
    df.to_csv(out / f"{stem}_table.csv", index=False, encoding="utf-8-sig")
    result = {k: float(v) for k, v in s.items()}

    if args.mc > 0:
        y = monte_carlo(cfg, M=args.mc, typeA_t=args.typeA_t)
        cmp = compare_gum_mc(s, y, n_dig=args.ndig)
        print(f"\n[몬테카를로 M={args.mc:,}] u_MC = {cmp['u_MC']:.2f}")
        print(f"  95 % 구간 GUM = [{cmp['GUM'][0]:.2f}, {cmp['GUM'][1]:.2f}]")
        print(f"  95 % 구간 MC  = [{cmp['MC'][0]:.2f}, {cmp['MC'][1]:.2f}]")
        print(f"  끝점 차이 = {cmp['d_low']:.3f}, {cmp['d_high']:.3f}  (허용 δ = {cmp['delta']:.3f})")
        if cmp["valid"]:
            print("  판정: GUM 결과 유효 (MC 와 일치)")
        elif cmp["gum_wider"]:
            print("  판정: δ 초과, 단 GUM 구간이 MC 를 포함(보수적) → GUM U 보고 + MC 구간 병기")
        else:
            print("  판정: δ 초과, GUM 구간이 더 좁음 → MC 구간을 보고")
        result["mc"] = {k: (list(map(float, v)) if isinstance(v, tuple) else
                            (bool(v) if isinstance(v, bool) else float(v)))
                        for k, v in cmp.items()}
    (out / f"{stem}_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {out / (stem + '_table.csv')}, {out / (stem + '_summary.json')}")


if __name__ == "__main__":
    main()
```

### 6.3 실행 예시와 기대 출력

```bash
python uncertainty_budget.py budget_height.yaml --out results/uncertainty
```

```text
측정량: 단차 높이 오차 e = H_meas - H_ref (10 mm 게이지 블록 단차, 회색 PLA 표면 포함)
                요인 형                  평가   u_x   단위     c   u_i    dof  기여율_%
    기준물(게이지 블록) 인증 B           U=0.4/k=2 0.200   um 1.000 0.200    inf  0.061
      캘리브레이션 맞춤 잔차 A s=3.000 (ν=50), /√1 3.000   um 1.000 3.000 50.000 13.709
반복성 (센서 노이즈 + 스펙클) A s=3.927 (n=10), /√1 3.927   um 1.000 3.927  9.000 23.495
      표면 영향 (재료·색) B        a=8.66/1.732 5.000   um 1.000 5.000    inf 38.079
                온도 B         a=2.5/1.732 1.443 degC 1.360 1.963    inf  5.870
         정합 (Z 방향) A  s=2.000 (ν=9), /√1 2.000   um 1.000 2.000  9.000  6.093
          스테이지 직진도 B         a=5.0/1.732 2.887   um 1.000 2.887    inf 12.694

합성 표준불확도 u_c = 8.10 um
유효 자유도 ν_eff = 144
포함인자 k = 2.017 (p = 0.9545)
확장불확도 U = 16.3 um
보고: e = -50 ± 16 um (k = 2.02, 약 95 %)

[몬테카를로 M=1,000,000] u_MC = 8.10
  95 % 구간 GUM = [-66.01, -33.99]
  95 % 구간 MC  = [-65.68, -34.31]
  끝점 차이 = 0.335, 0.325  (허용 δ = 0.050)
  판정: δ 초과, 단 GUM 구간이 MC 를 포함(보수적) → GUM U 보고 + MC 구간 병기

저장: results/uncertainty/budget_height_table.csv, results/uncertainty/budget_height_summary.json
```

읽는 법
- u_c = 8.10 µm, U = 16.3 µm로 BLUEPRINT 예시(≈ 8.2, ≈ 16 µm)와 같은 수준입니다. 차이는 온도·직진도 값을 원자료(범위 ÷ √3)에서 다시 계산했기 때문입니다.
- **표면 영향이 38 %로 가장 크고, 반복성이 23 %** 입니다. 개선하려면 이 둘을 먼저 줄여야 합니다. 게이지 블록 인증(0.06 %)은 아무리 좋은 블록을 사도 의미가 없습니다.
- MC 구간이 GUM 구간보다 0.3 µm 정도 좁습니다. 직사각형 요인이 커서 결과 분포의 꼬리가 정규분포보다 짧기 때문입니다. GUM 쪽이 보수적이므로 GUM U를 보고합니다.

A형 입력을 t 분포로 뽑는 JCGM 101의 엄격한 방식(`--typeA-t`)으로 돌리면 반대로 MC가 더 넓어집니다. 이 경우는 MC 구간을 보고합니다.

```text
[몬테카를로 M=1,000,000] u_MC = 8.45
  95 % 구간 GUM = [-66.01, -33.99]
  95 % 구간 MC  = [-66.40, -33.59]
  끝점 차이 = 0.384, 0.393  (허용 δ = 0.050)
  판정: δ 초과, GUM 구간이 더 좁음 → MC 구간을 보고
```

### 6.4 XY 길이 예산 예시

```yaml
# XY 길이 측정 불확도 예산 (config/uncertainty/budget_xy_length.yaml)
measurand: "X 방향 길이 오차 (10 mm 게이지 블록 길이, 경계 직선 맞춤 H7)"
unit: um
result: 0.0
coverage_probability: 0.9545
components:
  - {name: 기준물 길이 인증, type: B, distribution: normal, expanded: 0.2, k: 2, unit_in: um, c: 1.0}
  - {name: 배율(스케일) 잔차 ±0.05 %, type: B, distribution: rectangular, half_width: 5.0, unit_in: um, c: 1.0}
  - {name: 경계 추출 반복성, type: A, std: 6.0, dof: 9, n_avg: 1, unit_in: um, c: 1.0}
  - {name: 격자 양자화 0.02 mm, type: B, distribution: resolution, resolution: 20.0, unit_in: um, c: 1.0}
  - {name: 엣지 효과 (E2), type: B, distribution: rectangular, half_width: 10.0, unit_in: um, c: 1.0}
  - {name: 온도 ±2.5 °C, type: B, distribution: rectangular, half_width: 2.5, unit_in: degC, c: 0.68}
```

```text
측정량: X 방향 길이 오차 (10 mm 게이지 블록 길이, 경계 직선 맞춤 H7)
                요인 형                 평가   u_x   단위     c   u_i   dof  기여율_%
         기준물 길이 인증 B          U=0.2/k=2 0.100   um 1.000 0.100   inf  0.009
배율(스케일) 잔차 ±0.05 % B        a=5.0/1.732 2.887   um 1.000 2.887   inf  7.442
         경계 추출 반복성 A s=6.000 (ν=9), /√1 6.000   um 1.000 6.000 9.000 32.151
    격자 양자화 0.02 mm B         δ=20.0/√12 5.774   um 1.000 5.774   inf 29.769
        엣지 효과 (E2) B       a=10.0/1.732 5.774   um 1.000 5.774   inf 29.769
        온도 ±2.5 °C B        a=2.5/1.732 1.443 degC 0.680 0.981   inf  0.860

합성 표준불확도 u_c = 10.58 um
유효 자유도 ν_eff = 87
포함인자 k = 2.029 (p = 0.9545)
확장불확도 U = 21.5 um
보고: e = 0 ± 21 um (k = 2.03, 약 95 %)

[몬테카를로 M=1,000,000] u_MC = 10.58
  95 % 구간 GUM = [-21.03, 21.03]
  95 % 구간 MC  = [-20.51, 20.51]
  끝점 차이 = 0.526, 0.521  (허용 δ = 0.500)
  판정: δ 초과, 단 GUM 구간이 MC 를 포함(보수적) → GUM U 보고 + MC 구간 병기

저장: results/uncertainty/budget_xy_length_table.csv, results/uncertainty/budget_xy_length_summary.json
```

XY는 경계 추출 반복성, 격자 양자화, 엣지 효과 세 요인이 비슷하게 지배합니다. 격자를 0.01 mm로 줄이면 양자화 기여가 2.9 µm로 반감되지만 데이터는 4배가 됩니다 (G3, H1과 같이 결정).

### 6.5 단위 테스트 (pytest)

`tests/test_uncertainty_budget.py` — 정답을 손으로 알 수 있는 입력으로 계산기를 검사합니다. (아래는 계산기와 같은 폴더에서 실행하는 형태이며, 저장소에서는 `from cvlab.uncertainty import …` 로 바꿉니다.)

```python
# tests/test_uncertainty_budget.py — 정답을 아는 입력으로 계산기를 검사
import numpy as np
import pytest
from uncertainty_budget import standard_uncertainty, gum_budget, monte_carlo


@pytest.mark.parametrize("comp, expected", [
    ({"type": "B", "distribution": "rectangular", "half_width": np.sqrt(3)}, 1.0),
    ({"type": "B", "distribution": "triangular", "half_width": np.sqrt(6)}, 1.0),
    ({"type": "B", "distribution": "u_shaped", "half_width": np.sqrt(2)}, 1.0),
    ({"type": "B", "distribution": "resolution", "resolution": np.sqrt(12)}, 1.0),
    ({"type": "B", "distribution": "normal", "expanded": 2.0, "k": 2}, 1.0),
    ({"type": "A", "data": [1, 2, 3, 4, 5], "n_avg": 1}, np.std([1, 2, 3, 4, 5], ddof=1)),
    ({"type": "A", "std": 4.0, "n_avg": 4}, 2.0),
])
def test_standard_uncertainty(comp, expected):
    u, _, _ = standard_uncertainty(comp)
    assert u == pytest.approx(expected, rel=1e-12)


def test_combined_3_4_5():
    # 3, 4 → 합성 5 (피타고라스), B형만이면 k = 2.000 (정규분포 95.45 %)
    cfg = {"unit": "um", "components": [
        {"name": "a", "type": "B", "distribution": "normal", "expanded": 6, "k": 2},
        {"name": "b", "type": "B", "distribution": "normal", "expanded": 8, "k": 2}]}
    df, s = gum_budget(cfg)
    assert s["u_c"] == pytest.approx(5.0)
    assert s["k"] == pytest.approx(2.0, abs=1e-3)
    assert df["기여율_%"].sum() == pytest.approx(100.0)


@pytest.mark.parametrize("dist", ["rectangular", "triangular", "u_shaped"])
def test_mc_std_matches_gum(dist):
    cfg = {"unit": "um", "components": [
        {"name": "x", "type": "B", "distribution": dist, "half_width": 3.0, "c": 2.0}]}
    _, s = gum_budget(cfg)
    y = monte_carlo(cfg, M=400_000, seed=1)
    assert y.std() == pytest.approx(s["u_c"], rel=0.01)
```

```bash
python -m pytest -q tests/test_uncertainty_budget.py
```

```text
11 passed in 1.30s
```

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 계산기 정확성 | §6.5 pytest | 11개 테스트 모두 통과 |
| 요인 완전성 | 피시본 그림의 모든 가지가 예산표에 "포함" 또는 "무시 가능(근거)"으로 존재 | 누락 0개 |
| 높이 예산 크기 | u_c, U 계산 | **U(k=2) ≤ 20 µm** (A2 치수 공차 ±0.1 mm의 1/5 이하, 4:1 규칙 만족) |
| XY 예산 크기 | 같은 방법 | U(k=2) ≤ 25 µm |
| D5와의 일관성 | 게이지 블록 단차 오차(D5)가 \|e\| ≤ U 인지 | 1, 2, 5, 10 mm 단차 **4개 모두** 만족 |
| MC 비교 | §6.3 판정 | "유효" 또는 "GUM이 보수적" (GUM이 더 좁으면 MC 구간 채택) |
| 유효 자유도 | ν_eff 출력 | ν_eff ≥ 30 (미만이면 A형 반복 수를 늘림) |
| I3 사후 검증 | Bland–Altman 차이가 ±√(U_laser² + U_ref²) 안 | 차이의 **≥ 90 %** (n=30 표본 변동 고려, 기대값 95 %) |
| 문서화 | 보고서·YAML·CSV·CAL-ID 기록 | 3개 파일 + 보고서 존재, CAL-ID 일치 |

**판정 규칙 (보고할 때)**
- `|e| > U` : "측정 장비 불확도를 넘는 가공 오차가 있다"
- `|e| ≤ U` : "측정 장비로 구분할 수 없는 수준" — "오차 없음"이라고 쓰지 않습니다.
- 공차 합격/불합격 판정이 필요하면 ISO 14253-1의 결정 규칙처럼 공차 한계에서 U만큼 안쪽(보호대, guard band)을 합격 구간으로 씁니다.

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| A형 반복성을 무조건 √n으로 나눔 | u_c가 비현실적으로 작음 (예: 3 µm) → I3에서 차이가 U 밖으로 많이 나감 | 본 실험이 실제로 평균한 횟수만 `n_avg` 에 입력 |
| 같은 원인을 두 번 셈 | 반복성(진동 포함) + 진동 요인 따로 → U 과대 | 요인마다 "무엇을 포함하는지" 한 줄 설명 쓰기 |
| 알려진 치우침을 보정도 안 하고 불확도에도 안 넣음 | I3 Bland–Altman 평균 차이가 0에서 유의하게 벗어남 | I2 치우침이 유의하면 보정하고, 보정값의 불확도를 요인으로 추가 |
| 사양서 "±a"를 그대로 u로 씀 | u가 √3배 과대 | 분포를 정하고 a/√3 등으로 변환 |
| 인증서 U를 k로 안 나눔 | 기준물 기여 2배 | "U = …, k = 2" 이면 u = U/2 |
| 단위 혼용 (°C, mm, µm) | 온도 기여가 1000배 | 입력 단위(`unit_in`)와 c의 단위를 함께 적고 출력은 항상 µm |
| 격자 점 하나의 불확도를 영역 지표에 씀 | 영역 평균 결과에 U가 과대 | 측정량(점/영역/단차)을 먼저 정의하고 그에 맞는 반복성 사용 |
| 예산을 한 번 만들고 갱신 안 함 | 재교정 후에도 옛 U 사용 | 요약 JSON에 CAL-ID 기록, CAL-ID가 바뀌면 재계산 |
| 표면 영향을 빼먹음 | 게이지 블록(금속, 무광 처리)으로는 U 안이지만 PLA 시편에서 교차검증 실패 | E1 실험값을 반드시 B형으로 포함 |

## 9. 위험 요소

- **U가 목표보다 큼** (예: 30 µm 이상): 0.2 mm 층 높이의 ±0.02 mm 오차는 구분 불가가 됩니다. 대응: 기여율 상위 요인 개선(표면 → 재료·코팅, 반복성 → 프레임 평균·노출, F2), 또는 연구 범위를 "±0.05 mm 이상 오차"로 재정의 (K4).
- **표면 영향 값의 근거 부족**: E1 실험이 늦어지면 표면 요인을 추정할 수 없습니다. 대응: W13~14의 E1 결과를 W15 시작 전까지 확정하도록 K1 일정에서 관리, 없으면 보수적으로 a = 15 µm 가정 후 표시.
- **I2와 일정 충돌**: 반복성 데이터가 I2에서 나오므로 I2가 늦으면 I1도 늦습니다. 같은 측정 세션에서 두 요소의 데이터를 함께 얻도록 계획합니다.
- **온도 통제 실패**: 겨울(1월) 난방 on/off로 실내 온도가 ±3 °C 이상 흔들리면 U자 분포로 바꾸고 기여를 다시 계산합니다.
- **상관 요인 존재**: 캘리브레이션과 정합이 같은 마커 데이터를 쓰는 경우 상관이 생길 수 있습니다. 확인되면 하나로 합쳐 수치 실험으로 평가합니다.

## 10. 기록 양식

**빈 예산 YAML 템플릿** (`config/uncertainty/budget_<측정량>.yaml`)

```yaml
measurand: ""            # 측정량 한 문장
unit: um
result: 0.0              # 측정 결과 (H5/H7)
coverage_probability: 0.9545
calibration_id: ""       # 예: CAL-2027-01-11-A
date: ""                 # 예: 2027-01-25
author: ""
components:
  - name: ""
    type: A              # A | B
    data: []             # A형 원자료 (또는 std + dof)
    n_avg: 1
    unit_in: um
    c: 1.0
    basis: ""            # 근거 (파일명, 인증서 번호, 쪽)
  - name: ""
    type: B
    distribution: rectangular   # normal | rectangular | triangular | u_shaped | resolution
    half_width: 0.0
    unit_in: um
    c: 1.0
    basis: ""
```

**예산 검토 기록표**

| 날짜 | CAL-ID | 측정량 | u_c [µm] | ν_eff | k | U [µm] | 최대 기여 요인 (%) | MC 판정 | 검토자 |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

**요인 근거표**

| 요인 | 형 | 원자료/근거 위치 | 분포 | 값 | c | u_i [µm] | 포함 여부 (무시 시 이유) |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 11. 참고 자료

- JCGM 100:2008, *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* (GUM)
- JCGM 101:2008, *Evaluation of measurement data — Supplement 1 to the GUM — Propagation of distributions using a Monte Carlo method*
- JCGM 200:2012, *International vocabulary of metrology (VIM)*, 3rd edition
- ISO 14253-1, *Geometrical product specifications (GPS) — Inspection by measurement of workpieces and measuring equipment — Part 1: Decision rules for verifying conformity or nonconformity with specifications*
- ISO/IEC Guide 98-3 (GUM의 ISO 판)
- EURAMET / UKAS 등 측정 불확도 해설 문서 (예: UKAS M3003, *The Expression of Uncertainty and Confidence in Measurement*)
- 상위 문서: [BLUEPRINT.md I1](../../BLUEPRINT.md#i1-측정-불확도-gum-방식)
