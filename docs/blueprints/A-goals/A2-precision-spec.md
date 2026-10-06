# A2. 요구 정밀도와 센서 사양 도출

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: A. 목표·요구사항

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-06 ~ 2026-10-19 (W1-2) |
| 우선순위 | 긴급 |
| 트랙 | 관리·기획 |
| 선행 요소 | [A1 오차의 정의](A1-error-definition.md) · [A3 가공 공정 확정](A3-process.md) |
| 후행 요소 | [B1 삼각측량 원리](../B-optics/B1-triangulation-principle.md) · [B2 기하 배치](../B-optics/B2-geometry.md) · [B3 상용 vs 자작](../B-optics/B3-commercial-vs-diy.md) · [B4 카메라](../B-optics/B4-camera.md) · [B5 렌즈](../B-optics/B5-lens.md) · [C1 스캔 이동 장치](../C-mechanics/C1-scan-stage.md) · [E3 시편 설계](../E-specimen/E3-test-artifact.md) · [G3 마스크·높이맵](../G-reference/G3-mask-heightmap.md) · [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) · [I1 불확도](../I-reliability/I1-uncertainty.md) · [I2 MSA](../I-reliability/I2-msa.md) · [K1 일정](../K-management/K1-schedule.md) |
| 관련 마일스톤 | **M0** (2026-10-19: 사양표 + 부품 목록 확정). 사양표의 Z 값은 **M2**(게이지 블록 단차 오차 < 10 µm)와 **M5**(%GRR < 30 %, 목표 < 10 %)에서 실측으로 검증 |

---

## 1. 목적

"어느 정도 크기의 오차를 볼 것인가"(A1)에서 출발해, 센서가 갖춰야 할 성능을 **숫자로 거꾸로 계산**한 **목표 사양표**를 만듭니다. 사양표에는 최소한 다음 다섯 값이 들어갑니다.

1. **Z 반복성** (예: ≤ 5 µm, 1σ)
2. **X·Y 점 간격** (예: ≈ 0.02 mm)
3. **측정 폭 FOV_x** (예: ≥ 20 mm)
4. **측정 깊이 범위** (예: ≥ 25 mm, 시편 높이 20 mm + 25 % 여유)
5. **스캔 시간** (예: 시편 1개 ≤ 30 s)

이 사양표는 W2 말(M0)까지 확정되어 B 영역의 부품 선정, B3의 상용/자작 판단, K3 예산의 기준이 됩니다. 센서 노이즈가 측정하려는 오차와 비슷하면 결과는 노이즈일 뿐이므로, 이 단계에서 **"이 센서로 이 오차를 구분할 수 있는가"** 를 먼저 따져 봅니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 비슷해 보이지만 다른 네 단어

| 용어 | 뜻 | 비유 | 이 과제에서 확인하는 곳 |
|---|---|---|---|
| **분해능 (resolution)** | 구별할 수 있는 가장 작은 변화(눈금 간격) | 자의 눈금이 1 mm 인지 0.5 mm 인지 | B1 공식 δz, δx |
| **반복성 (repeatability)** | 같은 것을 같은 조건에서 여러 번 쟀을 때의 흩어짐(표준편차) | 같은 자로 10번 쟀을 때 값이 얼마나 다른가 | C7 정지 평판 100장, I2 |
| **정확도 / 치우침 (accuracy / bias)** | 참값과의 평균 차이 | 자 자체가 0.3 mm 늘어나 있음 | D5 게이지 블록, I2 |
| **불확도 (uncertainty)** | 결과가 참값 주위에서 흩어질 수 있는 범위(모든 요인 합성) | "±0.016 mm (k=2)" | I1 |

**핵심**: 분해능이 좋다고 반복성이 좋은 것은 아닙니다. 이론 서브픽셀 분해능은 2.8 µm 이어도, 실제로는 스펙클 노이즈 때문에 반복성이 5~15 µm 가 되는 경우가 흔합니다(청사진 B1). 그래서 사양표의 Z 항목은 **분해능이 아니라 반복성**으로 적고, 실측으로 검증합니다.

### 2.2 10 : 1 규칙과 4 : 1 규칙
측정 장비의 반복성(또는 분해능)은 **측정하려는 오차 크기의 1/10** 이 이상적입니다. 최소한 **1/4** 은 확보합니다.

```
필요 반복성(이상) = 보려는 오차 / 10
필요 반복성(최소) = 보려는 오차 / 4
```
- 예: 층 높이 오차 ±0.02 mm (20 µm) → 이상 2 µm, 최소 5 µm
- 4:1 보다 나쁘면 측정값의 흩어짐 대부분이 장비 때문이 되어, 조건 간 차이를 통계적으로 구분하기 어렵습니다.

### 2.3 샘플링 규칙 (XY 점 간격)
가장 작은 형상에 **최소 5~10개 점**이 찍혀야 그 형상의 폭·모양을 잴 수 있습니다.
```
점 간격 상한 = 가장 작은 형상 크기 / 5
점 간격 권장 = 가장 작은 형상 크기 / 10
```
- 예: 선폭 0.4 mm → 상한 0.08 mm, 권장 0.04 mm. 선폭 오차(±0.04 mm)까지 보려면 더 촘촘한 **0.02 mm** 를 권장합니다(청사진 A2).
- 점 간격이 X(카메라 픽셀 방향)와 Y(스캔 방향)에서 같으면 격자가 정사각형이 되어 처리가 쉽습니다(C1, G3).

### 2.4 공차와 %GRR의 관계
측정시스템분석(I2)의 공차 기준 **%GRR = 6·σ_GRR / (공차 폭)** 입니다(공차 폭 = 2 × ±공차). 공차 ±0.1 mm 이면 공차 폭 0.2 mm 이므로
- %GRR < 10 % (우수) → σ_GRR ≤ 3.3 µm
- %GRR < 30 % (조건부) → σ_GRR ≤ 10 µm

즉 **Z 반복성 목표 5 µm** 는 공차 ±0.1 mm 기준으로 "조건부 합격은 충분, 우수에는 약간 부족"한 수준입니다. 6장 두 번째 코드로 직접 계산해 봅니다.

### 2.5 사양표 숫자가 다른 숫자로 이어지는 흐름
```
A1 보려는 오차 ──10:1/4:1──▶ Z 반복성 목표 ──B1 공식──▶ 배율 M, 각도 θ, 픽셀 크기
A1 가장 작은 형상 ──5~10점──▶ XY 간격 ──▶ 카메라 해상도/배율, 스캔 간격 ──▶ fps
E3 시편 크기 ──여유──▶ FOV, 깊이 범위 ──▶ 렌즈 f, WD
XY 간격 + 스캔 속도 ──▶ fps(B4) ──▶ 스캔 시간, 데이터 용량(F3)
```

---

## 3. 입력과 산출물

| 구분 | 항목 | 형식·파일명 | 비고 |
|---|---|---|---|
| 입력 | 오차 정의서 (주요 오차 종류, 공차) | `docs/decisions/A1-error-definition.md` | A1 산출물 |
| 입력 | 공정 결정 (층 높이, 선폭, 최소 형상) | `docs/decisions/A3-process-decision.md` | A3 산출물. FDM 기본 0.2 mm 층, 0.42 mm 선폭 |
| 입력 | 시편 크기 초안 | E3 초안(가로·세로·높이 mm) | 최종 E3 설계 전이므로 가정값 사용 |
| 입력 | 부품 후보 사양 (픽셀 크기, 해상도, 초점거리) | 제조사 데이터시트 PDF | B4, B5 |
| 산출물 | **목표 사양표** | `docs/decisions/A2-target-spec.yaml` + 같은 내용의 표 `A2-target-spec.md` | M0 필수 산출물 |
| 산출물 | 사양 계산 스크립트 | `tools/a2_spec.py` (6장 코드) | 값이 바뀌면 재실행 |
| 산출물 | 후보 구성 비교표 | `docs/decisions/A2-candidates.csv` | 후보별 dx, dz, FOV, Z 범위, 만족 여부 |
| 산출물 | 설정 반영 | `config/default.yaml` 의 `grid.resolution_mm: 0.02`, `metrics.tolerance_mm: 0.1` | J2 |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| Z 반복성 정의 | 단일점 σ / 평면 평균 σ / 2σ / 3σ | **정지 평판을 100회 연속 측정했을 때 격자점별 높이 표준편차(1σ)의 중앙값** | C7 점검 절차와 같은 방법. 데이터시트의 "2σ" 표기와 혼동 방지 |
| Z 반복성 목표 | 2 / 5 / 10 µm | **≤ 5 µm** (1σ) | 층 높이 오차 ±20 µm 의 4:1, 치수 ±0.1 mm 의 20:1 |
| XY 점 간격 | 0.01 / 0.02 / 0.04 mm | **0.02 mm** (X 픽셀 간격과 Y 스캔 간격 동일) | 선폭 0.4 mm 에 20점, 선폭 오차 ±0.04 mm 의 2점/오차 |
| FOV_x | 15 / 20 / 30 mm | **≥ 20 mm** | 시편 폭 18 mm + 양쪽 1 mm 여유. 이보다 크면 이어 붙이기 필요(E3) |
| 측정 깊이 범위 | 10 / 25 / 40 mm | **≥ 25 mm** (실제 초점심도 기준) | 시편 높이 20 mm + 25 % 여유 (B2) |
| 스캔 속도 / 시간 | 1 / 2 / 5 mm/s | **2 mm/s**, 40 mm 스캔 20 s, 50 mm 스캔 25 s | fps = 2 / 0.02 = 100 fps (B4) |
| 정확도(치우침) 목표 | 5 / 10 / 20 µm | **게이지 블록 단차 오차 < 10 µm** | M2 통과 기준 (D5) |
| 확장불확도 목표 | ≤ 공차/4 / ≤ 공차/10 | **U(k=2) ≤ 25 µm** (공차 ±0.1 mm 의 1/4) | I1 예시 예산 ≈ 16 µm 로 달성 가능 수준 |
| %GRR 목표 | < 10 / < 30 % | **< 30 % 필수, < 10 % 목표** | M5, I2 |
| 사양 미달 시 대응 | 장비 교체 / 목표 재정의 | **M2 결과로 판단**: 배율·각도 재설계 또는 "보려는 오차" 범위 재정의 | K4 첫 번째 위험 |

---

## 5. 수행 절차

### 단계 1. 측정 목표 목록 작성 (W1 화–수)
- [ ] A1 주요 오차 종류마다 "보려는 오차 크기(±mm)"와 "가장 작은 형상 크기(mm)"를 표로 작성
- [ ] FDM 기본값: 층 높이 오차 ±0.02 mm, 선폭 오차 ±0.04 mm(선 0.40 mm), 치수 오차 ±0.1 mm(최소 형상 Ø 2 mm)
- [ ] 각 목표가 Z 방향인지 XY 방향인지 표시

### 단계 2. 10:1 / 4:1 규칙으로 필요 반복성 계산 (W1 목)
- [ ] 6장 `a2_spec.py` 의 `targets` 를 연구실 값으로 수정 후 실행
- [ ] Z 관련 목표 중 가장 엄격한 값을 Z 반복성 "이상/최소" 로 채택 (예: 2 µm / 5 µm)
- [ ] 이상(10:1) 값이 자작 센서로 비현실적이면(< 5 µm) **최소(4:1) 값을 목표**로 하고, 해당 오차 종류는 "경계 수준 측정"으로 표시

### 단계 3. 샘플링 규칙으로 XY 간격 결정 (W1 목)
- [ ] 가장 작은 형상 / 10 = 권장 간격 계산 (선폭 0.4 → 0.04 mm)
- [ ] 선폭 오차까지 볼 경우 0.02 mm 로 강화
- [ ] X(픽셀) 간격과 Y(스캔) 간격을 동일하게 설정 → `grid.resolution_mm: 0.02`

### 단계 4. FOV, 깊이 범위, 스캔 시간 결정 (W1 금)
- [ ] FOV = 시편 폭 + 2 mm (양쪽 1 mm) 이상 → 18 mm 시편이면 20 mm
- [ ] 깊이 범위 = 시편 높이 × 1.25 이상 → 20 mm 시편이면 25 mm
- [ ] fps = 스캔 속도 / 스캔 간격 → 2 mm/s ÷ 0.02 mm = 100 fps
- [ ] 프레임 수 = 스캔 길이 / 간격 → 40 mm ÷ 0.02 = 2000 장, 시간 20 s
- [ ] 데이터 용량 추정: ROI 1440×200 px, 8 bit 저장 시 1프레임 288 kB × 2000 = **약 576 MB/스캔** (12 bit를 16 bit로 저장하면 약 1.15 GB) → F3 저장 계획에 전달

### 단계 5. 공차 · %GRR 과의 정합성 확인 (W2 월)
- [ ] 6장 `a2_grr_link.py` 실행: 공차 ±0.1 mm, %GRR < 10 % → σ ≤ 3.3 µm, < 30 % → σ ≤ 10 µm
- [ ] Z 반복성 목표(5 µm)가 %GRR 30 % 조건(10 µm)을 여유 있게 만족하는지 확인
- [ ] 확장불확도 목표 U(k=2) ≤ 25 µm 기재

### 단계 6. 후보 구성으로 실현 가능성 점검 (W2 화–수)
- [ ] B1 공식으로 후보 카메라·렌즈·각도 조합마다 dx, dz(1 px), dz(서브픽셀 1/10), FOV, 이론 Z 범위 계산
- [ ] 결과를 `A2-candidates.csv` 에 저장, 각 사양 만족/미달 표시
- [ ] **dz 서브픽셀 이론값 ≤ 목표의 1/2** 이 되도록 선택 (이론값이 그대로 나오지 않기 때문. 예: 목표 5 µm → 이론 ≤ 2.5~3 µm)
- [ ] FOV가 근소하게 미달(예: 19.87 mm)하면 WD를 늘리거나 시편 폭을 줄이는 방안 중 선택

### 단계 7. 사양표 확정 및 공유 (W2 목–금, 2026-10-19까지)
- [ ] 10장 양식으로 `A2-target-spec.yaml` 작성, 버전 v1.0
- [ ] 각 값 옆에 "검증 방법·시점"(M1/M2/M5) 기재
- [ ] 팀 회의에서 B 영역 담당자에게 인계, 지도교수 승인
- [ ] K1 일정의 M0 체크 항목에 "사양표 확정" 표시

---

## 6. Python 구현

### 6.1 목표 사양 역산 + 후보 구성 점검 (`a2_spec.py`)

측정 목표 목록에서 10:1/4:1 규칙과 샘플링 규칙으로 필요한 값을 계산하고, B1의 삼각측량 공식으로 후보 구성이 사양을 만족하는지 확인합니다.

```python
# a2_spec.py — 측정 목표(오차·형상 크기)에서 센서 목표 사양을 거꾸로 계산
import numpy as np
import yaml

# ---------------- 1) 측정 목표 (연구실에서 채우는 값) ----------------
targets = [
    # 이름, 보려는 오차 크기(±mm), 방향, 가장 작은 형상 크기(mm)
    {"name": "층 높이 오차", "error_mm": 0.02, "axis": "Z", "feature_mm": None},
    {"name": "선폭 오차",    "error_mm": 0.04, "axis": "XY", "feature_mm": 0.40},
    {"name": "치수 오차",    "error_mm": 0.10, "axis": "XYZ", "feature_mm": 2.0},
]
specimen = {"size_x_mm": 18.0, "size_y_mm": 40.0, "height_mm": 20.0}
scan_speed_mm_s = 2.0          # 스캔 이동 속도 가정


def required(err_mm, ratio):
    """ratio:1 규칙 → 필요한 반복성/분해능 [µm]"""
    return err_mm / ratio * 1000


rows = []
for t in targets:
    r = {"목표": t["name"], "오차[µm]": t["error_mm"] * 1000,
         "이상(10:1)[µm]": required(t["error_mm"], 10),
         "최소(4:1)[µm]": required(t["error_mm"], 4)}
    if t["feature_mm"]:
        # 가장 작은 형상에 5~10점 → 점 간격 상한
        r["점간격 상한(5점)[mm]"] = t["feature_mm"] / 5
        r["점간격 권장(10점)[mm]"] = t["feature_mm"] / 10
    rows.append(r)

for r in rows:
    print(r)

# Z 반복성 목표: Z 관련 목표 중 가장 엄격한 '이상' 값과 '최소' 값
z_ideal = min(r["이상(10:1)[µm]"] for r, t in zip(rows, targets) if "Z" in t["axis"])
z_min = min(r["최소(4:1)[µm]"] for r, t in zip(rows, targets) if "Z" in t["axis"])
pitch_max = min(r.get("점간격 권장(10점)[mm]", 9e9) for r in rows)

# 측정 폭/깊이: 시편 + 여유(양쪽 1 mm, 깊이 +25 %)
fov_req = specimen["size_x_mm"] + 2.0
depth_req = specimen["height_mm"] * 1.25

# 스캔 시간 = Y 길이 / 속도, 프레임 수·fps
pitch = 0.02
fps = scan_speed_mm_s / pitch
n_frames = int(np.ceil(specimen["size_y_mm"] / pitch))
scan_time = specimen["size_y_mm"] / scan_speed_mm_s

spec = {
    "z_repeatability_um": {"target": 5.0, "ideal_10to1": round(z_ideal, 1), "min_4to1": round(z_min, 1)},
    "xy_pitch_mm": {"target": pitch, "upper_limit": round(pitch_max, 3)},
    "fov_x_mm_min": fov_req,
    "depth_range_mm_min": depth_req,
    "scan": {"speed_mm_s": scan_speed_mm_s, "fps": fps,
             "frames": n_frames, "time_s": scan_time},
}
print("\n[목표 사양]")
print(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False))


# ---------------- 2) 후보 구성이 사양을 만족하는지 (B1 공식) ----------------
def triangulation_spec(f_mm, wd_mm, pixel_um, n_cols, n_rows, theta_deg, subpixel=10):
    M = f_mm / (wd_mm - f_mm)
    s = np.sin(np.radians(theta_deg))
    return {"dx_um": pixel_um / M,
            "dz_1px_um": pixel_um / (M * s),
            "dz_sub_um": pixel_um / (M * s) / subpixel,
            "fov_x_mm": n_cols * pixel_um / M / 1000,
            "z_range_mm": n_rows * pixel_um / (M * s) / 1000}


cand = triangulation_spec(25, 125, 3.45, 1440, 1080, 30)
checks = {
    "XY 간격(dx ≤ 20 µm)": cand["dx_um"] <= pitch * 1000,
    "FOV ≥ %.0f mm" % fov_req: cand["fov_x_mm"] >= fov_req,
    "Z 범위(이론) ≥ %.0f mm" % depth_req: cand["z_range_mm"] >= depth_req,
    "dz 서브픽셀(이론) ≤ 5 µm": cand["dz_sub_um"] <= 5.0,
}
print("[후보: f25, WD125, 3.45 µm, 1440×1080, 30°]")
for k, v in cand.items():
    print("  %-11s = %.2f" % (k, v))
for k, ok in checks.items():
    print("  %-26s %s" % (k, "만족" if ok else "미달"))
```

**줄별 핵심 설명**
- `targets`: 연구실이 직접 채우는 부분입니다. `feature_mm` 은 그 오차를 보려는 형상의 가장 작은 크기이며, 해당 없으면 `None`.
- `required(err_mm, ratio)`: 오차를 `ratio` 로 나누고 1000을 곱해 µm 로 바꿉니다.
- `z_ideal`, `z_min`: 방향(`axis`)에 "Z" 가 들어 있는 목표 중 **가장 엄격한(가장 작은)** 값을 고릅니다.
- `fov_req`, `depth_req`: 시편 크기에 여유를 더한 값. 여유 비율은 4장 결정 표와 같습니다.
- `yaml.safe_dump(..., allow_unicode=True)`: 사양을 사람이 읽기 쉬운 YAML로 출력. 같은 내용을 파일로 저장하면 그대로 사양표가 됩니다.
- `triangulation_spec`: 청사진 B1 함수와 같은 공식(`M = f/(WD−f)`, `δz = p/(M·sinθ)`)입니다.
- `checks`: 사양마다 만족/미달을 판정합니다. "Z 범위(이론)"은 픽셀 수로만 계산한 값이므로 실제 초점심도는 B2에서 따로 확인해야 합니다.

**실행 예시와 기대 출력**
```
$ python3 a2_spec.py
{'목표': '층 높이 오차', '오차[µm]': 20.0, '이상(10:1)[µm]': 2.0, '최소(4:1)[µm]': 5.0}
{'목표': '선폭 오차', '오차[µm]': 40.0, '이상(10:1)[µm]': 4.0, '최소(4:1)[µm]': 10.0, '점간격 상한(5점)[mm]': 0.08, '점간격 권장(10점)[mm]': 0.04}
{'목표': '치수 오차', '오차[µm]': 100.0, '이상(10:1)[µm]': 10.0, '최소(4:1)[µm]': 25.0, '점간격 상한(5점)[mm]': 0.4, '점간격 권장(10점)[mm]': 0.2}

[목표 사양]
z_repeatability_um:
  target: 5.0
  ideal_10to1: 2.0
  min_4to1: 5.0
xy_pitch_mm:
  target: 0.02
  upper_limit: 0.04
fov_x_mm_min: 20.0
depth_range_mm_min: 25.0
scan:
  speed_mm_s: 2.0
  fps: 100.0
  frames: 2000
  time_s: 20.0

[후보: f25, WD125, 3.45 µm, 1440×1080, 30°]
  dx_um       = 13.80
  dz_1px_um   = 27.60
  dz_sub_um   = 2.76
  fov_x_mm    = 19.87
  z_range_mm  = 29.81
  XY 간격(dx ≤ 20 µm)          만족
  FOV ≥ 20 mm                미달
  Z 범위(이론) ≥ 25 mm           만족
  dz 서브픽셀(이론) ≤ 5 µm         만족
```

**해석**: 청사진 B1의 예시 구성은 FOV가 19.87 mm 로 목표 20 mm 에 **0.13 mm 부족**합니다. WD를 125 → 128 mm 정도로 늘려 배율을 약간 낮추거나(dx·dz도 함께 커짐), 시편 폭을 17 mm 로 줄이는 방안 중 하나를 B2/E3와 협의해 결정합니다. 이렇게 "근소한 미달"을 숫자로 미리 발견하는 것이 이 요소의 목적입니다. 또한 dz 서브픽셀 2.76 µm 는 **이론값**이며 실제 반복성은 5~15 µm 일 수 있으므로 M2/M5에서 실측합니다.

### 6.2 공차와 %GRR 목표에서 허용 σ 역산 (`a2_grr_link.py`)

```python
# a2_grr_link.py — 공차(±tol)와 %GRR 목표에서 허용 가능한 측정 표준편차를 역산
tol_list_mm = [0.05, 0.10, 0.20]        # 양쪽 공차 ±tol
grr_targets = {"우수(<10 %)": 0.10, "조건부(<30 %)": 0.30}

print("공차 ±tol | %GRR 목표 | 허용 σ_GRR [µm] | 허용 반복성 2σ [µm]")
for tol in tol_list_mm:
    width = 2 * tol                      # 공차 폭 = USL − LSL
    for name, g in grr_targets.items():
        sigma = g * width / 6 * 1000     # %GRR = 6σ / 공차폭  →  σ = %GRR·공차폭/6
        print("  ±%.2f mm | %-10s | %6.1f          | %6.1f" % (tol, name, sigma, 2 * sigma))
```

- `%GRR = 6σ / 공차폭` 을 σ에 대해 풀어 `σ = %GRR × 공차폭 / 6` 으로 계산합니다.
- "허용 반복성 2σ" 열은 데이터시트가 2σ 기준으로 반복성을 표기할 때 비교하기 위한 값입니다.

**실행 예시와 기대 출력**
```
$ python3 a2_grr_link.py
공차 ±tol | %GRR 목표 | 허용 σ_GRR [µm] | 허용 반복성 2σ [µm]
  ±0.05 mm | 우수(<10 %)  |    1.7          |    3.3
  ±0.05 mm | 조건부(<30 %) |    5.0          |   10.0
  ±0.10 mm | 우수(<10 %)  |    3.3          |    6.7
  ±0.10 mm | 조건부(<30 %) |   10.0          |   20.0
  ±0.20 mm | 우수(<10 %)  |    6.7          |   13.3
  ±0.20 mm | 조건부(<30 %) |   20.0          |   40.0
```

**해석**: 공차 ±0.1 mm 에서 Z σ = 5 µm 이면 %GRR ≈ 15 % (조건부). 반복성만 5 µm 이고 재현성(재장착·측정자) 성분이 더해지면 σ_GRR 은 더 커지므로, **반복성 목표 5 µm 는 여유가 크지 않은 값**임을 사양표에 명시합니다.

---

## 7. 검증 방법과 완료 기준

| 확인 항목 | 방법 | 합격 기준 | 시점 |
|---|---|---|---|
| 사양표 완성 | 파일 확인 | Z 반복성, XY 간격, FOV, 깊이 범위, 스캔 시간 5개 값이 **숫자와 단위**로 기재 | M0 (2026-10-19) |
| 규칙 일관성 | `a2_spec.py` 재실행 | Z 목표 ≤ 4:1 값, XY 간격 ≤ 최소 형상/10 | M0 |
| 후보 실현성 | 후보 비교표 | 선정 후보가 모든 사양 "만족" (이론 dz 서브픽셀 ≤ 목표의 1/2 권장) | M0 |
| Z 반복성 실측 | 정지 평판 100회 측정 (C7) | 격자점별 σ 의 중앙값 ≤ 5 µm | M1~M2 |
| XY 간격 실측 | 게이지/스케일 측정, 스테이지 엔코더 | 실제 X 픽셀 간격 0.020 mm ± 10 %, Y 스캔 간격 0.020 mm ± 5 % | M2 |
| 정확도 | 게이지 블록 단차 (D5) | 단차 오차 < 10 µm | **M2** (불통과 시 본 실험 진행 금지) |
| FOV·깊이 실측 | 평판을 깊이 방향으로 이동하며 측정 | 폭 ≥ 20 mm, 유효 깊이 ≥ 25 mm 에서 반복성 ≤ 목표의 1.5배 | M2 |
| 측정시스템 | Gage R&R (I2) | %GRR < 30 % (목표 < 10 %), ndc ≥ 5 | **M5** |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 분해능(이론 서브픽셀 값)을 반복성으로 착각 | 사양표에 2.8 µm 라고 적었는데 실측 σ가 10 µm | 사양표 Z 항목은 "반복성(1σ, 실측)"으로 정의, 이론값은 참고 열로 분리 |
| 1σ/2σ/3σ 기준 혼동 | 데이터시트 비교 시 2~3배 차이 | 모든 값에 기준(1σ)을 명시, 6.2 표의 2σ 열 활용 |
| 가장 작은 형상을 잊고 큰 형상 기준으로 간격 결정 | 선폭·얇은 벽이 2~3점에만 걸려 폭 측정 불가 | 최소 형상 / 10 규칙, 선폭 0.4 mm → 0.02~0.04 mm |
| X 간격과 Y 간격을 다르게 설정 | 격자가 직사각형 → 마스크·지표 계산에서 축별 왜곡 | 두 간격을 같은 값(0.02 mm)으로 |
| FOV를 시편 크기와 딱 맞춤 | 시편 가장자리가 잘리거나, 마커가 FOV 밖 | 양쪽 1 mm 이상 여유, 기준 마커(C3)까지 FOV 안에 들어오는지 확인 |
| 깊이 범위를 픽셀 수로만 계산 | 시편 위·아래가 초점 밖에서 흐려져 노이즈 증가 | 초점심도로 실측(B2), 조리개 f/8~f/11 |
| fps와 노출 시간 충돌을 무시 | 100 fps 인데 노출 15 ms 필요 → 불가능 | 노출 ≤ 1/fps 의 80 % (100 fps → ≤ 8 ms), 부족하면 속도를 낮춤 |
| 데이터 용량 계산 누락 | 하루 측정 후 디스크가 가득 참 | 단계 4의 용량 계산 → F3 에 전달 |
| 사양 미달을 M2 이후에야 발견 | 본 실험 일정 붕괴 | 이 요소에서 후보 점검, M2에서 진행/중단 판단 |

---

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 자작 센서의 실제 Z 반복성이 5 µm 를 넘음 (스펙클) | 중~높음 | 높음 | 청색 레이저(B6), 가우시안 중심 추출(F1), 여러 프레임 평균. 그래도 미달이면 층 높이 오차 목표를 ±0.05 mm 로 재정의 (K4) |
| 표면 재료 영향(반투명)이 반복성보다 큰 계통 오차를 만듦 | 높음 | 높음 | 회색 불투명 PLA 고정 (E1), 불확도 예산에 포함 |
| FOV와 분해능의 맞교환으로 두 사양을 동시에 만족하는 부품이 없음 | 중 | 중 | 시편 폭 축소 또는 해상도 높은 카메라. 비용 증가분은 K3에서 견적 |
| 스테이지 직진도·피치 오차가 Z 오차로 나타남 (아베 오차) | 중 | 중 | C1 스테이지 사양 확인, D3에서 실측 |
| 사양표가 너무 늦게 확정되어 부품 주문 지연 | 중 | 중 | 2026-10-19 확정 엄수, 미정 값은 "잠정"으로 표시하고 주문 진행 |

---

## 10. 기록 양식

### 10.1 목표 사양표 (`docs/decisions/A2-target-spec.yaml`)

```yaml
version: "1.0"
date: "2026-10-19"
approved_by: ""
process: FDM                 # A3
tolerance_mm: 0.1            # A1
targets:                     # 측정 목표 (A1 기반)
  - {name: 층 높이 오차, error_mm: 0.02, axis: Z,  feature_mm: null}
  - {name: 선폭 오차,    error_mm: 0.04, axis: XY, feature_mm: 0.40}
  - {name: 치수 오차,    error_mm: 0.10, axis: XYZ, feature_mm: 2.0}
spec:
  z_repeatability_um_1sigma: {target: 5.0, verify: "C7 정지 평판 100회, M2"}
  xy_pitch_mm:               {target: 0.02, verify: "D3 스캔축, 게이지, M2"}
  fov_x_mm_min:              {target: 20.0, verify: "평판 폭 측정, M1"}
  depth_range_mm_min:        {target: 25.0, verify: "깊이별 반복성, M2"}
  scan_time_s_max:           {target: 30,   verify: "40 mm 스캔 시간 측정, M2"}
  step_accuracy_um:          {target: 10,   verify: "게이지 블록 단차, D5, M2"}
  expanded_uncertainty_um_k2: {target: 25,  verify: "I1 불확도 예산, M5"}
  grr_pct:                   {required: 30, goal: 10, verify: "I2 Gage R&R, M5"}
scan:
  speed_mm_s: 2.0
  fps: 100
  frames_per_scan: 2000
  est_data_per_scan_MB: 576  # ROI 1440x200, 8 bit
notes: "dz 서브픽셀 이론값은 참고값, 실측 반복성으로 판정"
```

### 10.2 후보 구성 비교표 (`A2-candidates.csv`)

```csv
candidate_id,f_mm,wd_mm,pixel_um,n_cols,n_rows,theta_deg,dx_um,dz_1px_um,dz_sub_um,fov_x_mm,z_range_mm,meets_xy,meets_fov,meets_depth,meets_z,note
C01,25,125,3.45,1440,1080,30,13.80,27.60,2.76,19.87,29.81,Y,N,Y,Y,FOV 0.13 mm 부족
C02,,,,,,,,,,,,,,,,
```

### 10.3 실측 검증 기록

| 사양 항목 | 목표 | 실측값 | 측정일 | 방법·데이터 경로 | 판정 | 비고 |
|---|---|---|---|---|---|---|
| Z 반복성 (1σ) | ≤ 5 µm | | | | | |
| X 픽셀 간격 | 0.020 mm | | | | | |
| Y 스캔 간격 | 0.020 mm | | | | | |
| FOV_x | ≥ 20 mm | | | | | |
| 유효 깊이 | ≥ 25 mm | | | | | |
| 단차 오차 | < 10 µm | | | | | |
| %GRR | < 30 % | | | | | |

---

## 11. 참고 자료

- JCGM 200:2012, *International vocabulary of metrology (VIM)* — 분해능, 반복성, 정확도 정의
- JCGM 100:2008, *Guide to the expression of uncertainty in measurement (GUM)* — 확장불확도, 포함인자 k
- ISO 5725-1/-2, *Accuracy (trueness and precision) of measurement methods and results* — 반복성·재현성 개념
- AIAG, *Measurement Systems Analysis (MSA) Reference Manual* — %GRR, ndc, 측정 장비 분해능 10:1 경험칙
- ISO 14253-1, *GPS — Inspection by measurement of workpieces and measuring equipment — Decision rules* — 공차와 측정 불확도를 고려한 합부 판정
- 교과서 주제: 측정공학(측정 시스템 사양), 디지털 신호의 표본화(샘플링) 기초, 머신비전 광학(배율, 초점심도)
- PyYAML 문서: https://pyyaml.org/wiki/PyYAMLDocumentation
