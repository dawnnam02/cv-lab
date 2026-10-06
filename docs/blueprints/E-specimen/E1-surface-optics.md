# E1. 표면 광학 특성 — 재료·색이 측정값을 얼마나 바꾸는가

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: E. 측정 대상(시편)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-29 ~ 2027-01-11 (W13-14) |
| 우선순위 | 높음 |
| 트랙 | 실험·품질 |
| 선행 요소 | [B6 레이저 광원](../B-optics/B6-laser.md) · [B7 광학 필터](../B-optics/B7-filter.md) · [F1 레이저 라인 중심 추출](../F-acquisition/F1-line-extraction.md) · [F2 획득 파라미터](../F-acquisition/F2-acquisition-params.md) · [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) · [H3 바닥 평면 기준화](../H-analysis/H3-bed-leveling.md) |
| 후행 요소 | [E3 시편 설계](./E3-test-artifact.md) (재료 확정) · [I1 측정 불확도](../I-reliability/I1-uncertainty.md) (표면 영향 성분) · [I2 MSA](../I-reliability/I2-msa.md) · [H8 통계 분석](../H-analysis/H8-statistics.md) |
| 관련 마일스톤 | M4 (시편 1개 전체 파이프라인 완주) — 본 실험 재료가 이 요소에서 확정되어야 함 |

---

## 1. 목적

레이저 삼각측량은 **표면에서 산란되어 카메라로 돌아온 빛의 위치**로 높이를 계산합니다. 그래서 모양이 같아도 **재료·색·광택이 다르면 측정 높이가 달라집니다.** 이 요소의 목적은 세 가지입니다.

1. **본 실험 재료를 데이터로 확정**합니다. 기본 권장은 청사진대로 "회색 불투명 PLA 고정"이며, 이 실험으로 그 선택이 맞는지 숫자로 확인합니다.
2. **표면 영향의 크기를 µm 단위로 정량화**해서 I1 불확도 예산의 "표면 영향(재료·색)" 행(u_surface)을 채웁니다. 청사진 예시값 5 µm를 **실측값으로 교체**하는 것이 이 요소의 핵심 산출물입니다.
3. **무광 코팅 두께**를 측정해서, 코팅을 쓸 경우 보정값과 그 불확도를 확보합니다.

부가 효과: 재료·색 효과 자체가 독립된 연구 결과(논문의 "측정 시스템 검증" 또는 "고찰: 표면 의존성" 절)가 됩니다.

## 2. 배경 지식 (초보자용)

### 2.1 빛이 표면에서 하는 일 — 세 가지 경우

```
 (a) 무광 불투명 (이상적)     (b) 반투명               (c) 광택
     레이저 ↓                    레이저 ↓                 레이저 ↓
  ────────●────────          ────────●────────         ────────●────────
     빛이 표면에서 사방으로      빛이 속으로 파고들어      빛이 거울처럼 한 방향으로만
     고르게 흩어짐(난반사)       넓게 퍼진 뒤 나옴         튕김(정반사)
  → 선이 가늘고 중심 정확      → 선이 두껍고 중심이       → 카메라 방향에 따라 너무 밝거나
                                 '아래쪽'으로 밀림          (포화) 아예 안 보임(누락)
```

- **(b) 반투명 = 부피 산란(subsurface scattering)**: 빛이 재료 안 수십~수백 µm까지 들어갔다가 나옵니다. 카메라는 빛이 나온 "덩어리"의 중심을 표면으로 착각하므로 **표면이 실제보다 낮게** 측정됩니다. 부호 규칙(오차 = 측정값 − 기준값)으로 쓰면 **− 쪽 계통 오차(재료 부족처럼 보임)**입니다. 이것은 반복해도 줄지 않는 **치우침(bias)**이라서 특히 위험합니다.
- **(c) 광택 = 정반사**: 일부 각도에서 빛이 카메라로 직접 들어와 **포화**(밝기 최댓값에 붙음)되고, 다른 곳에서는 신호가 없어 **NaN(측정값 없음)**이 됩니다. 가짜 반사점도 생깁니다.
- **어두운 색(검정)**: 흡수가 커서 신호가 약합니다 → 랜덤 노이즈가 커집니다(치우침보다는 흩어짐 문제).
- **파장 영향**: 청색(405~450 nm)은 적색(650 nm)보다 플라스틱 속으로 덜 파고들어 (b)의 치우침이 작은 경향이 있습니다 (B6).

### 2.2 무광 코팅 스프레이

표면에 얇은 흰 가루막을 입혀 (a)처럼 만듭니다. 대신 **코팅 두께만큼 표면이 올라갑니다**(+ 쪽 오차, 재료 과다처럼 보임). 종류:
- **비파괴검사(NDT)용 현상제**: 잘 지워지지 않음. 두께가 분사 횟수·거리에 따라 달라짐.
- **승화형 스캔 스프레이**: 시간이 지나면 저절로 사라짐 → **분사 후 경과 시간**에 따라 두께가 변하므로 시간을 꼭 기록.

두께는 제품과 분사 방법에 따라 달라지므로 **추정하지 말고 직접 측정**합니다 (게이지 블록 전후 비교).

### 2.3 "단차"는 재료 효과를 숨긴다

같은 재료의 두 면 높이 차이(단차)를 재면, 두 면 모두 같은 양만큼 밀리므로 **치우침이 상쇄**됩니다. 그래서 단차 정확도가 좋다고 재료 효과가 없다는 뜻이 아닙니다. 재료 효과를 보려면 **다른 기준면(베드) 대비 절대 높이 = 두께**를 재서 마이크로미터 값과 비교해야 합니다. 이 실험은 두 가지를 모두 잽니다.
- **두께 오차** `e_t = (레이저로 잰 윗면 높이 − 베드 평면) − 마이크로미터 두께` → 재료 효과가 드러남
- **단차 오차** `e_s = 레이저 단차 − 마이크로미터 단차` → 재료 효과가 상쇄되는지 확인용

주의: 베드 표면 자체도 광학 치우침이 있습니다. 모든 시편을 **같은 베드 시트, 같은 위치**에서 재면 베드 치우침은 모든 재료에 공통이므로 **재료 간 비교는 공정**합니다. 절대값은 "베드 기준"이라고 명시합니다.

### 2.4 접촉식과 광학식의 "표면" 정의가 다름

마이크로미터 앤빌은 표면의 **가장 높은 봉우리**에 닿고, 레이저는 일정 면적의 **평균 높이**를 봅니다. FDM 윗면에는 선 자국(요철)이 있으므로 마이크로미터 두께가 약간 더 크게 나옵니다 → 모든 재료에 비슷한 **− 치우침**이 섞입니다. 그래서 **재료 간 차이**를 주로 해석하고, 기준 재료(GRY)의 절대 치우침은 불확도로 처리합니다. 윗면 품질 설정(다림질 ironing 등)은 모든 시편에서 **같게 고정**합니다.

### 2.5 통계 용어 한 줄 정리

- **요인/수준**: "표면"이라는 요인에 GRY·WHT·BLK·NAT·SLK 5개 수준이 있다.
- **이원 분산분석(two-way ANOVA)**: 두 요인(표면, 코팅)이 결과에 영향을 주는지, 둘이 서로 얽혀 있는지(교호작용)를 한 번에 검정.
- **대응표본 t-검정**: 같은 시편의 "코팅 전 vs 후"처럼 짝지어진 두 값 비교.
- **유사반복 주의**: 수십만 개 격자점이 아니라 **시편 하나당 요약값 하나**를 분석 단위로 씁니다 (H8).

## 3. 입력과 산출물

| 구분 | 항목 | 형식 / 파일명 | 비고 |
|---|---|---|---|
| 입력 | 검증된 캘리브레이션 | `config/calibration/CAL-YYYY-MM-DD-X/` | D5 일일 점검 통과 상태 |
| 입력 | 획득 파라미터 기본값 | `config/default.yaml` 의 acquisition 절 | F2. 실험 중 **고정** |
| 입력 | 레이저 라인 추출 + 신뢰도 | `triangulation.py` (F1) | 점마다 최대 밝기·선 두께 저장 필요 |
| 입력 | 필라멘트 5종 | GRY / WHT / BLK / NAT / SLK | 같은 제조사 계열이면 좋음 (제조사 차이 혼입 방지) |
| 입력 | 디지털 마이크로미터, 게이지 블록(5 mm) | – | I3 기준 장비 |
| 산출물 | 실험 설계표 | `data/experiments/E1_design.csv` | 6절 코드로 생성, 90행 |
| 산출물 | 쿠폰 CAD·G코드 | `data/gcode/E1_coupon_v1.stl`, `E1_coupon_v1_<재료>.gcode`, `E1_coupon_v1.ini`(슬라이서 프로파일) | 재료별 G코드는 온도 설정만 다르게 |
| 산출물 | 마이크로미터 기준값 | `data/experiments/E1_reference_micrometer.csv` | 시편 x 위치 x 3회 |
| 산출물 | 스캔 원본·메타데이터 | `data/raw/E1S01_r01/`, `E1S01_r01.json` | F3 규칙, `notes` 에 코팅 여부·분사 후 경과 분 |
| 산출물 | 스캔별 요약 지표 | `results/E1/E1_results.csv` | 10절 양식 |
| 산출물 | 코팅 두께 기록 | `results/E1/E1_coating.yaml` | t, u, 제품명, 분사 조건 |
| 산출물 | 분석 결과 | `results/E1/E1_summary.csv`, `E1_anova.csv`, `E1_boxplot.png` | 표면 x 코팅 요약, 분산분석표, 상자그림(J4 규칙) |
| 산출물 | 결론 메모 (1쪽) | `docs/notes/E1_conclusion.md` | 재료 확정, u_surface 값, 코팅 사용 여부 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 표면 요인 수준 | 3종(GRY·NAT·BLK) / 5종(+WHT·SLK) | **5종** (재료 확보가 어려우면 최소 3종) | 반투명·광택·어두움·밝음을 모두 덮어야 E1 표의 4가지 경우를 검증 가능 |
| 코팅 요인 | 없음 / 없음+무광 코팅 | **없음 + 무광 코팅** (같은 시편에 전→후) | 같은 시편 전후 비교(대응 설계)라서 시편 수를 절반으로 줄임. 코팅은 되돌릴 수 없으므로 **무코팅 스캔을 모두 끝낸 뒤** 코팅 |
| 반복 수 | 시편 2 x 스캔 2 / **3 x 3** / 5 x 3 | **표면당 시편 3개 x 코팅 상태당 스캔 3회** | H8 최소 기준. 15 시편, 90 스캔 |
| 노출 정책 | 고정 / 재료별 최적 | **주 실험은 고정**, 보조로 재료별 최적 노출 1세트(시편 1개 x 3회) | 고정해야 "재료 효과"만 보임(F2 원칙). 보조 세트는 "현실적으로 보정 가능한가" 판단용 |
| 레이저 파장 | 고정 / 405·650 비교 | **고정** (B6에서 고른 파장). 모듈이 2개면 선택 실험 | 요인을 늘리면 스캔 수가 2배 |
| 쿠폰 형상 | 평판 / **2단 평판** | **16 x 16 mm, 왼쪽 절반 두께 3.0 mm · 오른쪽 절반 4.0 mm** (단차 1.0 mm, 단차 벽이 Y(스캔) 방향과 나란) | 두께(재료 효과)와 단차(상쇄 확인)를 한 번에. FOV 19.9 mm 안에 베드가 양쪽 1.95 mm씩 보임(H3 기준면) |
| 판정 기준 (무코팅 사용 가능) | – | **\|치우침\| ≤ 10 µm, 반복성 σ ≤ 5 µm, 표면 노이즈 RMS ≤ 8 µm, 유효점 ≥ 98 %** | 10 µm = D5 단차 합격 기준, 5 µm = A2 Z 반복성 목표 |
| 표면 치우침 처리 | 보정(빼기) / 불확도로 포함 | **\|b\| ≤ 10 µm 이면 보정하지 않고 u_surface = √(b²/3 + SE²) 로 I1에 포함.** 더 크면 보정 + 보정 불확도 포함 | 작은 치우침을 보정하면 보정값의 불확도가 새로 생겨 이득이 적음 |
| 코팅 사용 여부 (본 실험) | 사용 / 미사용 | **미사용** (GRY가 판정 통과 시) | 코팅은 두께 불균일·시간 변화라는 새 오차원을 만듦 |
| 기준값 측정 위치 | 1점 / 3점 평균 | **각 절반의 중앙 5 x 5 mm 안 3점 평균** | 레이저 평가 영역과 같은 곳 |

## 5. 수행 절차

> 총 10 작업일 기준. W13-14는 E3과 겹치므로 **1~3일 차에 E1 쿠폰을 먼저 출력**하고, 판정 결과(5일 차)를 E3 출력 재료에 반영합니다.

1. **실험 설계표 만들기 (1일 차, 0.5일)**
   - [ ] 6.1 코드로 `E1_design.csv` 생성 (시드 42 고정, 시드값을 결론 메모에 기록)
   - [ ] 표면 x 코팅 칸마다 스캔 9회인지 확인 (출력 마지막 표)
   - [ ] 시편 ID(E1S01~E1S15)를 시편 **바닥면**에 유성펜으로 표시 (윗면은 측정면이므로 금지)
2. **쿠폰 출력 (1~3일 차)**
   - [ ] CAD: 16 x 16 mm, 두께 3.0/4.0 mm 2단. 단차 벽을 Y 방향과 나란히 배치
   - [ ] 슬라이서 프로파일 1개로 고정: 층 높이 0.2 mm, 선폭 0.42 mm, 윗면 층 수 5, 다림질(ironing) **끔**, 채움 20 %. 재료별로 바꾸는 것은 노즐·베드 온도뿐
   - [ ] `print_order` 순서대로 출력. 출력마다 노즐 온도·실내 온도를 기록
   - [ ] 출력 후 **실온까지 식힌 뒤**(C6) 베드에서 떼지 말지 결정: 이 실험은 재료 효과가 목적이므로 떼어서 **측정대의 같은 베드 시트 위 같은 위치(지그 모서리)**에 놓고 잼
3. **기준값 측정 (3일 차)**
   - [ ] 실내 온도 20±1 °C 확인, 시편을 측정실에 1시간 이상 둠
   - [ ] 마이크로미터로 각 절반 중앙 5 x 5 mm 안 3점 x 3회 측정 → `E1_reference_micrometer.csv`
   - [ ] 마이크로미터 영점을 측정 시작·끝에 확인 (차이 > 1 µm 이면 재측정)
4. **무코팅 스캔 45회 (4일 차)**
   - [ ] 레이저·카메라 30분 워밍업 → D5 일일 점검(기준 시편) 통과 확인 → `calibration_id` 기록
   - [ ] 노출·게인·레이저 출력은 **GRY 시편에서 정한 값으로 고정** (최대 밝기가 포화의 70~80 %)
   - [ ] `run_order` 순서대로 스캔. 스캔마다 시편을 지그에서 뺐다가 다시 놓음
   - [ ] 스캔마다 포화 픽셀 비율(%)과 레이저 선 두께 중앙값(px)을 메타데이터에 저장
   - [ ] (보조) 재료별 최적 노출로 각 재료 시편 1개 x 3회 추가 스캔, `notes: exposure_optimized`
5. **코팅 두께 측정 (5일 차 오전)**
   - [ ] 5 mm 게이지 블록 위에 같은 지그로 10회 스캔 (코팅 전)
   - [ ] 제품 사용법대로 분사. **분사 거리·횟수·시간**을 고정하고 기록 (예: "거리 고정, 왕복 2회")
   - [ ] 건조 후 10회 스캔 (코팅 후). 승화형은 분사 후 경과 시간(분)을 스캔마다 기록
   - [ ] 6.2 코드의 `coating_thickness()` 로 t, u 계산 → `E1_coating.yaml`
6. **시편 코팅 + 코팅 스캔 45회 (5일 차 오후)**
   - [ ] 15개 시편에 게이지 블록과 **같은 조건**으로 분사 (같은 사람, 같은 날)
   - [ ] 승화형이면 분사 후 일정 시간 창(예: 30~120분) 안에 스캔을 마치도록 순서 계획
   - [ ] `run_order` 46~90 순서대로 스캔
7. **지표 계산 (6~7일 차)**
   - [ ] H3 RANSAC으로 베드 평면 → Z=0
   - [ ] 각 절반 중앙 5 x 5 mm에서 높이 **중앙값** → 두께, 두 절반 차이 → 단차
   - [ ] 같은 영역에서 평면 맞춤 잔차 RMS → `noise_um`, NaN이 아닌 비율 → `valid_pct`
   - [ ] 오차 = 측정값 − 마이크로미터값 (µm), `E1_results.csv` 에 기록
8. **분석 (8일 차)**
   - [ ] 6.2 코드에서 합성 데이터 대신 `E1_results.csv` 를 읽도록 바꿔 실행
   - [ ] 요약표·분산분석표·대응 t-검정·판정·u_surface 를 저장
   - [ ] 상자그림: x = 표면, 색 = 코팅, y = 시편 단위 두께 오차 (J4 규칙, 0 기준선)
9. **결론과 전달 (9~10일 차)**
   - [ ] 본 실험 재료 확정 → E3 출력에 반영
   - [ ] u_surface → I1 불확도 예산표의 "표면 영향" 행 교체
   - [ ] 재료별 신뢰도 문턱값(밝기 하한, 선 두께 상한)을 F1 설정에 반영 (예: 선 두께 > GRY 중앙값의 1.5배 → 저신뢰)
   - [ ] 결론 메모 1쪽 작성, 지도교수 검토

## 6. Python 구현

### 6.1 실험 설계표 생성기 (`scripts/e1_design.py`)

```python
"""E1 표면 광학 실험 - 실험 설계표(순서 무작위화) 생성기
실행: python e1_design.py            -> E1_design.csv 생성
"""
import numpy as np
import pandas as pd

SEED = 42                      # 무작위 순서를 재현하기 위한 시드 (J2 규칙)
N_SPECIMEN_PER_SURFACE = 3     # 표면 수준마다 시편 3개 (H8: 시편 >= 3)
N_SCAN = 3                     # 코팅 상태마다 스캔 3회 (H8: 스캔 >= 3)

# 실험 요인 1: 표면(재료·색). 코드는 짧고 영문으로 -> 파일·그림에서 쓰기 편함
SURFACES = {
    "GRY": "회색 불투명 PLA (기준 재료)",
    "WHT": "흰색 불투명 PLA",
    "BLK": "검정 PLA",
    "NAT": "내추럴(반투명) PLA",
    "SLK": "실크(광택) PLA",
}
# 실험 요인 2: 무광 코팅. 코팅은 되돌릴 수 없으므로 '무코팅 스캔 전부 -> 코팅 -> 코팅 스캔'
COATINGS = ["NONE", "MATTE"]


def make_design(seed=SEED):
    rng = np.random.default_rng(seed)

    # 1) 시편 목록 + 출력 순서 무작위화 (시간에 따른 노즐 마모·온도 변화가 표면 효과와 섞이지 않게)
    specimens = [(s, k) for s in SURFACES for k in range(1, N_SPECIMEN_PER_SURFACE + 1)]
    print_order = rng.permutation(len(specimens)) + 1
    spec_rows = []
    for i, (surf, k) in enumerate(specimens):
        spec_rows.append({
            "specimen_id": f"E1S{i + 1:02d}",
            "surface": surf,
            "surface_desc": SURFACES[surf],
            "replicate": k,
            "print_order": int(print_order[i]),
        })
    spec = pd.DataFrame(spec_rows)

    # 2) 스캔 목록: 코팅 단계(phase)마다 (시편 x 반복) 순서를 따로 무작위화
    scan_rows = []
    for phase, coat in enumerate(COATINGS):
        jobs = [sid for sid in spec.specimen_id for _ in range(N_SCAN)]   # 시편마다 3번씩
        count = {sid: 0 for sid in spec.specimen_id}
        for j in rng.permutation(len(jobs)):
            sid = jobs[j]
            count[sid] += 1                        # 실제로 측정되는 순서대로 반복 번호 부여
            rep = count[sid] + phase * N_SCAN      # 무코팅 r01~r03, 코팅 r04~r06
            scan_rows.append({"scan_id": f"{sid}_r{rep:02d}", "specimen_id": sid,
                              "coating": coat, "repeat": rep})
    scans = pd.DataFrame(scan_rows)
    scans.insert(0, "run_order", np.arange(1, len(scans) + 1))
    design = scans.merge(spec, on="specimen_id")
    design = design.sort_values("run_order").reset_index(drop=True)
    # 측정 후 채울 빈 칸 (F3 메타데이터와 같은 이름)
    for col in ["datetime", "operator", "calibration_id", "room_temp_C", "exposure_us",
                "laser_power_pct", "notes"]:
        design[col] = ""
    return spec, design


if __name__ == "__main__":
    spec, design = make_design()
    design.to_csv("E1_design.csv", index=False, encoding="utf-8-sig")  # 엑셀에서 한글 안 깨지게
    print("시편 수:", len(spec), "/ 스캔 수:", len(design))
    print(spec.sort_values("print_order")[["print_order", "specimen_id", "surface"]]
          .head(5).to_string(index=False))
    print(design[["run_order", "scan_id", "surface", "coating"]].head(6).to_string(index=False))
    # 균형 확인: 표면 x 코팅 칸마다 스캔 수가 같아야 함 (모두 9)
    print(design.groupby(["surface", "coating"]).size().unstack())
```

**실행 예시와 기대 출력**

```
$ python e1_design.py
시편 수: 15 / 스캔 수: 90
 print_order specimen_id surface
           1       E1S05     WHT
           2       E1S13     SLK
           3       E1S10     NAT
           4       E1S04     WHT
           5       E1S11     NAT
 run_order   scan_id surface coating
         1 E1S10_r01     NAT    NONE
         2 E1S13_r01     SLK    NONE
         3 E1S07_r01     BLK    NONE
         4 E1S09_r01     BLK    NONE
         5 E1S03_r01     GRY    NONE
         6 E1S06_r01     WHT    NONE
coating  MATTE  NONE
surface             
BLK          9     9
GRY          9     9
NAT          9     9
SLK          9     9
WHT          9     9
```

- 시드가 같으면 누가 몇 번 실행해도 같은 순서가 나옵니다(재현성). 시드를 바꾸면 순서가 바뀝니다.
- `E1_design.csv` 의 빈 칸(datetime, operator …)은 측정하면서 채웁니다.

### 6.2 결과 분석 (`scripts/e1_analysis.py`) — 합성 데이터로 먼저 연습

합성 데이터의 "정답"은 코드 맨 위 `TRUE` 에 있습니다 (예: 반투명 NAT은 −85 µm, 코팅 두께 12 µm). 분석이 이 값을 되찾는지 확인한 뒤 실제 데이터에 씁니다 (J3의 정신).

```python
"""E1 표면 광학 실험 - 결과 분석 (지금은 '정답을 아는' 합성 데이터로 연습)
실행: python e1_analysis.py
실제 데이터가 생기면 make_synthetic_results() 대신 pd.read_csv("E1_results.csv") 를 씁니다.
부호 규칙: 오차 = 측정값 - 기준값 (+ = 재료 과다, - = 재료 부족)
"""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

rng = np.random.default_rng(42)

# ---------- 합성 데이터의 '정답' (실제 실험에서는 모르는 값) ----------
TRUE = {  # 표면: (두께 치우침 µm, 스캔 반복 σ µm, 표면 노이즈 µm, 유효점 %, 라인 두께 px)
    "GRY": (-3, 3, 5, 99.5, 4.5),
    "WHT": (-6, 3, 5, 99.6, 4.8),
    "BLK": (+1, 7, 11, 97.0, 4.2),
    "NAT": (-85, 12, 9, 98.5, 9.5),   # 반투명: 빛이 속으로 파고들어 표면이 낮게 측정됨
    "SLK": (-10, 9, 14, 88.0, 4.0),   # 광택: 정반사로 누락이 많음
}
COAT_TRUE_UM = 12.0     # 무광 코팅 실제 두께 (합성 정답)
COATED = (-2, 3, 5, 99.5, 4.5)  # 코팅 후에는 표면 종류와 무관하게 비슷해진다고 가정


def make_synthetic_results():
    """E1_design.csv 와 같은 구조(15 시편 x 6 스캔)의 가짜 측정 결과"""
    rows = []
    for i, surf in enumerate(np.repeat(list(TRUE), 3)):
        sid = f"E1S{i + 1:02d}"
        spec_effect = rng.normal(0, 4)            # 시편마다 다른 표면 상태(결·광택) 차이 (µm)
        for rep in range(1, 7):
            coat = "NONE" if rep <= 3 else "MATTE"
            b, s, n, v, lw = TRUE[surf] if coat == "NONE" else COATED
            if coat == "MATTE":
                b = b + COAT_TRUE_UM              # 코팅 두께만큼 재료가 '추가'된 것처럼 보임
            rows.append({
                "scan_id": f"{sid}_r{rep:02d}", "specimen_id": sid, "surface": surf,
                "coating": coat,
                # 두께 오차 = (레이저 측정 두께) - (마이크로미터 두께, 코팅 전 측정)
                "thick_err_um": b + spec_effect + rng.normal(0, s),
                # 단차 오차 = 같은 재료 두 면의 높이 차이 -> 재료 치우침이 상쇄되어 작음
                "step_err_um": rng.normal(0, s * 0.8),
                "noise_um": n * rng.uniform(0.9, 1.1),          # 평면 맞춤 잔차 RMS
                "valid_pct": min(100, v + rng.normal(0, 0.4)),  # 유효 점 비율
                "line_px": lw * rng.uniform(0.95, 1.05),        # 이미지 속 레이저 선 두께
            })
    return pd.DataFrame(rows)


def coating_thickness(before, after):
    """게이지 블록에 스프레이 전/후 각 10회 측정 -> 코팅 두께와 표준불확도"""
    t = after.mean() - before.mean()
    u = np.sqrt(before.var(ddof=1) / len(before) + after.var(ddof=1) / len(after))
    return t, u


if __name__ == "__main__":
    df = make_synthetic_results()

    # 1) 코팅 두께 (게이지 블록 위, 스캐너로 10회씩)
    gb_before = 5000 + rng.normal(0, 3, 10)                  # µm, 5 mm 게이지 블록
    gb_after = 5000 + COAT_TRUE_UM + rng.normal(0, 3, 10)
    t_coat, u_coat = coating_thickness(gb_before, gb_after)
    print(f"[코팅 두께] t = {t_coat:.1f} µm, u = {u_coat:.1f} µm")
    df["thick_err_corr_um"] = df.thick_err_um - np.where(df.coating == "MATTE", t_coat, 0)

    # 2) 유사반복 방지: 스캔 3회를 평균해 '시편 x 코팅' 당 값 1개로 줄임 (H8)
    spec = (df.groupby(["specimen_id", "surface", "coating"], as_index=False)
              .agg(bias=("thick_err_corr_um", "mean"), rep_sd=("thick_err_um", "std"),
                   step=("step_err_um", "mean"), noise=("noise_um", "mean"),
                   valid=("valid_pct", "mean"), line_px=("line_px", "mean")))

    # 3) 표면 x 코팅 요약표
    summ = (spec.groupby(["surface", "coating"])
                .agg(n=("bias", "size"), bias_mean=("bias", "mean"), bias_sd=("bias", "std"),
                     rep_sd=("rep_sd", lambda x: np.sqrt((x ** 2).mean())),  # 합동 반복성
                     step=("step", "mean"), noise=("noise", "mean"),
                     valid=("valid", "mean"), line_px=("line_px", "mean"))
                .round(1))
    print(summ.to_string())

    # 4) 이원 분산분석 (시편 단위 값으로)
    model = smf.ols("bias ~ C(surface) * C(coating)", data=spec).fit()
    print(anova_lm(model, typ=2).round(4).to_string())

    # 5) 표면마다 코팅 효과: 같은 시편의 전/후 비교 -> 대응표본 t-검정
    for surf in TRUE:
        w = spec[spec.surface == surf].pivot(index="specimen_id", columns="coating", values="bias")
        d = w["MATTE"] - w["NONE"]
        p = stats.ttest_rel(w["MATTE"], w["NONE"]).pvalue
        print(f"[코팅 효과] {surf}: 평균 변화 {d.mean():+.1f} µm (p = {p:.3f})")

    # 6) 판정: 무코팅 상태에서 쓸 수 있는 재료인가? (기준은 4장 결정 사항 참고)
    ok = summ.xs("NONE", level="coating")
    verdict = ((ok.bias_mean.abs() <= 10) & (ok.rep_sd <= 5) &
               (ok.noise <= 8) & (ok.valid >= 98))
    print("[판정] 무코팅 사용 가능:", [str(s) for s in ok.index[verdict]])

    # 7) I1 불확도 예산에 넣을 '표면 영향' B형 성분 (보정하지 않고 둘 때)
    g = spec[(spec.surface == "GRY") & (spec.coating == "NONE")].bias
    b, se = g.mean(), g.std(ddof=1) / np.sqrt(len(g))
    u_surf = np.sqrt(b ** 2 / 3 + se ** 2)     # 직사각형 분포 ±|b| + 추정 불확도
    print(f"[I1 입력] 회색 PLA 치우침 {b:+.1f} µm, u_surface = {u_surf:.1f} µm")
```

**실행 예시와 기대 출력**

```
$ python e1_analysis.py
[코팅 두께] t = 13.0 µm, u = 1.3 µm
                 n  bias_mean  bias_sd  rep_sd  step  noise  valid  line_px
surface coating                                                            
BLK     MATTE    3       -5.5      4.7     2.9  -0.3    5.0   99.4      4.4
        NONE     3        2.5      9.8     9.9  -0.7   11.0   97.1      4.3
GRY     MATTE    3       -5.9      5.0     1.5   0.4    4.9   99.4      4.5
        NONE     3       -6.9      4.8     1.9  -0.5    5.0   99.5      4.5
NAT     MATTE    3       -0.9     10.2     1.8   0.4    4.9   99.6      4.5
        NONE     3      -76.8      6.3    14.1   2.8    9.1   98.2      9.6
SLK     MATTE    3       -3.5      5.0     2.7  -1.4    5.1   99.6      4.5
        NONE     3       -9.1      4.8     8.0  -0.8   13.8   88.1      4.0
WHT     MATTE    3       -3.1      3.8     2.1   1.1    5.0   99.3      4.5
        NONE     3       -7.0      2.1     2.6  -0.2    5.1   99.6      4.8
                          sum_sq    df        F  PR(>F)
C(surface)             5663.6429   4.0  37.6850     0.0
C(coating)             1849.9756   1.0  49.2378     0.0
C(surface):C(coating)  6972.0045   4.0  46.3906     0.0
Residual                751.4460  20.0      NaN     NaN
[코팅 효과] GRY: 평균 변화 +1.0 µm (p = 0.301)
[코팅 효과] WHT: 평균 변화 +4.0 µm (p = 0.058)
[코팅 효과] BLK: 평균 변화 -8.0 µm (p = 0.249)
[코팅 효과] NAT: 평균 변화 +76.0 µm (p = 0.006)
[코팅 효과] SLK: 평균 변화 +5.6 µm (p = 0.053)
[판정] 무코팅 사용 가능: ['GRY', 'WHT']
[I1 입력] 회색 PLA 치우침 -6.9 µm, u_surface = 4.8 µm
```

**출력 읽는 법**
- `bias_mean` (코팅 두께 보정 후): NAT 무코팅이 −76.8 µm → 정답 −85 µm를 시편 3개의 출력 편차 범위 안에서 되찾았습니다. 코팅 후에는 −0.9 µm로 거의 사라집니다.
- `step` 은 모든 재료에서 ±3 µm 이내 → **단차는 재료 효과를 숨긴다**(2.3절)는 것을 보여 줍니다.
- `line_px`: NAT만 9.6 px로 GRY(4.5 px)의 2배 → 실제 데이터에서도 **선 두께가 반투명의 신호**입니다. F1 저신뢰 판정에 씁니다.
- 분산분석에서 교호작용(`C(surface):C(coating)`)이 유의 → "코팅 효과는 재료마다 다르다"(NAT에서 매우 큼, GRY에서 거의 없음).
- 시편 수가 3개라 p값의 검정력이 낮습니다(WHT p = 0.058). **유의하지 않다 ≠ 효과가 없다**입니다. 효과 크기(µm)를 I1 불확도와 비교해 판단합니다 (H8 판단 규칙).
- 실제 데이터에 쓸 때는 `df = make_synthetic_results()` 를 `df = pd.read_csv("results/E1/E1_results.csv")` 로 바꾸고 게이지 블록 값도 실제 측정값 배열로 바꿉니다.

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 설계 균형 | 설계표의 표면 x 코팅 칸별 스캔 수 | 모든 칸 = 9 |
| 분석 코드 검증 | 6.2 합성 데이터 실행 | NAT 무코팅 치우침을 정답(−85 µm) ± 15 µm 안에서, 코팅 두께를 ± 2 µm 안에서 복원 |
| 데이터 완결성 | 처리된 스캔 수 / 90 | ≥ 95 % (결측 스캔은 사유 기록) |
| 기준값 품질 | 마이크로미터 3회 반복 표준편차 | ≤ 2 µm |
| 코팅 두께 | 게이지 블록 전후 10회씩 | 표준불확도 u ≤ 2 µm |
| 기준 재료 판정 | GRY 무코팅 요약값 | \|치우침\| ≤ 10 µm, 반복성 σ ≤ 5 µm, 노이즈 RMS ≤ 8 µm, 유효점 ≥ 98 % |
| 단차 상쇄 확인 | 재료별 단차 오차 평균 | 모든 재료 \|평균\| ≤ 10 µm (넘으면 단차 벽 근처 엣지·가림 문제 의심 → E2) |
| 결과 전달 | I1 예산표, F1 설정, E3 재료 | 세 곳 모두 갱신되고 결론 메모에 링크 |

**완료 정의**: 위 표가 모두 합격이고, 결론 메모에 "본 실험 재료 = ○○, u_surface = ○.○ µm, 코팅 = 사용/미사용"이 적혀 있으면 E1 완료입니다. GRY가 판정에 실패하면 → 레이저 파장(B6)·노출(F2) 재검토 또는 코팅 사용 결정 후 해당 부분만 재실험합니다.

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 재료 순서대로 출력·측정 (GRY 전부 → WHT 전부 …) | 시간에 따른 온도·노즐 변화가 재료 효과로 둔갑 | 6.1 설계표의 무작위 순서를 그대로 따름 |
| 재료마다 노출을 바꿈 | 재료 효과와 노출 효과가 섞여 해석 불가 | 주 실험은 노출 고정, 최적 노출은 별도 보조 세트 |
| 단차 정확도만 보고 "재료 영향 없음" 결론 | NAT도 단차는 정확 | 반드시 **두께(베드 기준 절대 높이)** 로 판정 (2.3절) |
| 코팅 두께를 0으로 가정 | 코팅 후 모든 재료가 + 쪽으로 이동 | 게이지 블록 전후 측정값으로 보정, u_coat를 불확도에 포함 |
| 승화형 스프레이 경과 시간 미기록 | 같은 시편인데 스캔마다 수 µm씩 낮아짐 | 분사 시각과 스캔 시각을 메타데이터에 기록, 시간 창 안에서만 스캔 |
| 9개 스캔값을 독립 표본으로 t-검정 | p값이 지나치게 작음 | 시편 단위 평균으로 줄여 분석 (6.2의 2단계) |
| 시편 윗면에 ID 표시·지문 | 국부적 튀는 값, 광택 변화 | ID는 바닥면, 장갑 착용, 윗면 비접촉 |
| 반투명 시편 아래 배경이 바뀜 | 같은 시편인데 위치마다 다른 치우침 | 항상 같은 베드 시트·같은 위치에 놓기 |
| 포화된 스캔을 그대로 사용 | 광택(SLK) 시편의 중심이 평평하게 잘려 오차 | 포화 픽셀 비율 기록, 포화 점은 F1에서 저신뢰 처리 |

## 9. 위험 요소

- **필라멘트 로트 차이**: 같은 "회색 PLA"라도 로트·제조사에 따라 안료·투명도가 다릅니다 → 본 실험용 필라멘트를 **같은 로트로 충분히(예: 본 실험 전체 분량) 미리 확보**하고 로트 번호를 기록합니다.
- **GRY도 판정 실패**: 청색 레이저인데도 치우침이 크면 B6 파장·출력, B7 필터, F1 문턱값을 재검토해야 하므로 M4가 늦어집니다 → 4일 차에 GRY 시편 3개 결과를 **먼저** 계산해서 조기 경보로 씁니다.
- **코팅 두께 불균일**: 분사 방향에 따라 단차 벽 근처에 코팅이 몰릴 수 있습니다 → 코팅 상태 지표는 중앙 5 x 5 mm 영역만 사용합니다.
- **접촉식 기준의 한계**: 마이크로미터는 봉우리, 레이저는 평균을 봅니다(2.4절). 기준 재료의 절대 치우침에는 이 정의 차이가 섞여 있다고 보고서에 명시합니다. 가능하면 대표 시편 1~2개를 공초점 현미경 등 광학식 독립 장비로 교차 확인합니다 (I3).
- **일정 겹침**: E3과 같은 주에 진행되므로, 재료 판정이 늦어지면 E3 출력도 밀립니다 → E3 첫 출력은 기본 권장 재료(GRY)로 진행하고, E1 결과가 다르면 재출력합니다.

## 10. 기록 양식

**`results/E1/E1_results.csv` (스캔 1회 = 1행)**

```csv
scan_id,specimen_id,surface,coating,repeat,datetime,operator,calibration_id,room_temp_C,exposure_us,laser_power_pct,minutes_after_spray,saturated_pct,thick_err_um,step_err_um,noise_um,valid_pct,line_px,notes
E1S01_r01,E1S01,GRY,NONE,1,,,,,,,,,,,,,,
```

**`data/experiments/E1_reference_micrometer.csv`**

```csv
specimen_id,half,point,trial,thickness_mm,micrometer_zero_ok,room_temp_C,operator
E1S01,L,1,1,,,,
```

**`results/E1/E1_coating.yaml`**

```yaml
coating_id: COAT-2027-01-02-A
product: ""                 # 제품명 (라벨 그대로)
type: ""                    # ndt_developer | sublimating
spray_procedure: ""         # 거리, 왕복 횟수, 방향
spray_time: ""              # 분사 시각 (ISO 8601)
gauge_block_mm: 5.0
n_before: 10
n_after: 10
thickness_um: null          # t
u_thickness_um: null        # u (표준불확도)
calibration_id: ""
room_temp_C: null
notes: ""
```

**결론 메모 (`docs/notes/E1_conclusion.md`) 표**

| 항목 | 값 |
|---|---|
| 본 실험 재료 (제조사·색·로트) | |
| GRY 무코팅 치우침 b [µm] / 반복성 σ [µm] | |
| u_surface [µm] (I1 입력) | |
| 코팅 사용 여부 / 코팅 두께 t ± u [µm] | |
| F1 저신뢰 문턱값 (밝기 하한, 선 두께 상한) | |
| 설계표 시드 / 분석 코드 커밋 해시 | |

## 11. 참고 자료

- JCGM 100:2008 (GUM) — Evaluation of measurement data: Guide to the expression of uncertainty in measurement (B형 불확도, 직사각형 분포)
- VDI/VDE 2634 Part 2 — Optical 3-D measuring systems: Optical systems based on area scanning (광학 측정 시스템 검증 방법의 참고)
- ISO 10360-8 — Geometrical product specifications (GPS): Acceptance and reverification tests for CMMs with optical distance sensors
- NIST/SEMATECH e-Handbook of Statistical Methods — 실험 설계(DOE), 분산분석 장
- D. C. Montgomery, *Design and Analysis of Experiments* (Wiley) — 요인 설계, 무작위화, 반복
- statsmodels 공식 문서 — `ols`, `anova_lm`; SciPy 공식 문서 — `scipy.stats.ttest_rel`
- 상위 문서: [BLUEPRINT.md](../../BLUEPRINT.md) E1, B6, F1, F2, H8, I1
