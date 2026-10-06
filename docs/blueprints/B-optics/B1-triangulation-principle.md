# B1. 레이저 삼각측량 원리와 핵심 공식

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: B. 측정 원리·광학 설계

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-06 ~ 2026-10-19 (W1-2) |
| 우선순위 | 높음 |
| 트랙 | 하드웨어 |
| 선행 요소 | [A2 요구 정밀도와 사양 도출](../A-goals/A2-precision-spec.md) (목표 Z 반복성·XY 간격·FOV) |
| 후행 요소 | [B2 기하 배치](B2-geometry.md) · [B4 카메라](B4-camera.md) · [B5 렌즈](B5-lens.md) · [B6 레이저](B6-laser.md) · [D2 레이저 평면 캘리브레이션](../D-calibration/D2-laser-plane.md) · [F1 라인 중심 추출](../F-acquisition/F1-line-extraction.md) · [I1 측정 불확도](../I-reliability/I1-uncertainty.md) |
| 관련 마일스톤 | M0 (사양표 + 부품 목록 확정, 2026-10-19) |

## 1. 목적

- 레이저 삼각측량이 **왜 높이를 잴 수 있는지**를 그림과 식으로 이해하고, 팀 전원이 같은 기호·같은 단위로 말할 수 있게 합니다.
- BLUEPRINT B1의 공식(배율 M, δx, δz, FOV, Z 범위)을 **Python 계산기**로 만들어, 부품 후보(카메라·렌즈·각도)를 숫자로 비교합니다.
- 공식이 "근사"라는 점을 **핀홀 카메라 시뮬레이션으로 직접 확인**해서, 어디까지 믿어도 되는지(유효 범위)를 정리합니다.
- 결과물인 **"광학 설계 사양표"** 는 B2~B7 부품 선정과 M0 마일스톤의 근거가 됩니다.

## 2. 배경 지식 (초보자용)

### 2.1 삼각형으로 높이를 재는 원리

```
        카메라 (렌즈 중심)
          ●
           \  θ (레이저 빛줄기와 카메라 광축 사이 각)
            \
   레이저    \
     │        \
     │         \        ← 물체가 Δz 높아지면, 레이저가 닿는 점이
     ▼          \          레이저 빛줄기를 따라 Δz 위로 올라간다
  ───●───────────●────  ← 카메라에서 보면 그 점이 "옆으로" 움직인 것처럼 보인다
     물체 표면
```

1. 레이저는 **수직 아래로** 얇은 빛의 면(레이저 평면)을 쏩니다. 물체 위에는 **빛의 선**이 생깁니다.
2. 카메라는 레이저와 **θ 각도만큼 기울어진** 위치에서 그 선을 찍습니다.
3. 물체가 Δz 높아지면 빛이 닿는 점이 레이저 빛줄기를 따라 Δz 올라갑니다. 이 이동 중 **카메라 광축에 수직인 성분**은 `Δz · sinθ` 입니다. 카메라는 광축에 수직인 움직임만 "옆으로 이동"으로 봅니다.
4. 렌즈는 물체 쪽 길이를 배율 M 만큼 줄여 센서에 맺습니다. 따라서 센서 위 이동은 `M · Δz · sinθ` [mm]입니다.
5. 픽셀 크기 p로 나누면 이미지 속 이동 픽셀 수가 됩니다: `Δv = M · Δz · sinθ / p`
6. 거꾸로 "1픽셀 이동 = 몇 µm 높이?" 를 풀면 **δz = p / (M · sinθ)** 입니다. 이것이 Z 분해능 공식입니다.

### 2.2 기호와 단위 (팀 공통 규칙)

| 기호 | 뜻 | 단위 | 기준안 값 |
|---|---|---|---|
| f | 렌즈 초점거리 | mm | 25 |
| WD | 렌즈~측정점 거리 (카메라 광축 방향) | mm | 125 |
| M | 광학 배율 = 센서 위 길이 / 물체 위 길이 ≈ f / (WD − f) | 무차원 | 0.25 |
| p | 카메라 픽셀 한 변 길이 | µm | 3.45 |
| θ | 레이저 빛줄기와 카메라 광축 사이 각 (**바닥과의 각이 아님**) | ° | 30 |
| k | 서브픽셀 배수 (선 중심을 1/k 픽셀까지 찾음) | 무차원 | 5~20 (설계 계산은 10) |
| u, v | 이미지 가로(열)·세로(행) 좌표. u는 레이저 선 방향, v는 높이에 따라 움직이는 방향 | px | – |

- 코드 내부에서 각도는 **라디안**입니다. `np.sin(30)` 은 30 라디안의 사인이므로 틀립니다. 반드시 `np.sin(np.radians(30))` 으로 씁니다.
- 길이는 mm 를 기본으로 하되, 픽셀 크기·분해능처럼 작은 값은 µm 로 적고 **변수 이름에 단위**를 붙입니다(`pixel_um`, `wd_mm`).

### 2.3 공식 모음 (BLUEPRINT B1과 동일)

```
M        = f / (WD − f)
δx       = p / M                         X 방향(레이저 선 방향) 한 픽셀의 물체 위 폭
δz       = p / (M · sinθ)                v 방향 1픽셀 이동에 해당하는 높이
δz_eff   ≈ δz / k                        서브픽셀 중심 추출 후 (이론)
FOV_x    = N_가로픽셀 · p / M
Z_range  ≈ N_세로픽셀 · p / (M · sinθ)    (이론값. 실제로는 초점심도에 제한됨 → B2)
```

- **Y 방향(스캔 방향) 간격은 카메라가 아니라 스캔 이동 장치가 정합니다** ([C1](../C-mechanics/C1-scan-stage.md)). 보통 δx와 같게(예: 0.02 mm) 맞춥니다.
- θ가 커지면 sinθ가 커져서 δz는 작아집니다(좋아짐). 대신 가림(그림자)이 늘고 Z 범위가 줄어듭니다 → [B2](B2-geometry.md).

### 2.4 이 공식이 "근사"인 이유 세 가지

1. **원근 효과**: 물체가 카메라에 가까워지면 배율 M이 커집니다. 그래서 v와 z의 관계가 완전한 직선이 아닙니다. 기준안에서 0~20 mm 높이 구간을 직선으로 놓으면 최대 약 0.6 mm 높이에 해당하는 어긋남이 생깁니다(6절 코드로 확인). → 실제 측정에서는 **이 공식으로 높이를 계산하지 않고**, [D2](../D-calibration/D2-laser-plane.md)의 "광선–레이저 평면 교점" 계산이나 LUT 교정을 씁니다. 이 공식은 **설계(부품 고르기)용**입니다.
2. **렌즈 왜곡**: 실제 렌즈는 직선을 약간 휘게 찍습니다 → [D1](../D-calibration/D1-camera-intrinsics.md)에서 보정합니다.
3. **서브픽셀 k의 한계**: k=10 이라는 가정은 센서 노이즈만 있을 때의 이야기입니다. 레이저 빛이 거친 표면에서 만드는 **스펙클(반짝이 얼룩)** 이 선 중심을 무작위로 흔들어서, 기준안에서는 단일 점 높이 노이즈가 대략 5~15 µm 로 커집니다. 이 한계는 [B6](B6-laser.md)·[B2](B2-geometry.md)에서 계산합니다.

### 2.5 "분해능", "반복성", "정확도"는 다릅니다

| 용어 | 뜻 | 이 요소에서 다루는 범위 |
|---|---|---|
| 분해능 | 구별 가능한 최소 변화 (δz, δx) | 공식으로 계산 (설계값) |
| 반복성 | 같은 대상을 반복 측정할 때의 흩어짐 (표준편차) | 스펙클·노이즈 추정만, 실측은 [I2](../I-reliability/I2-msa.md) |
| 정확도 | 참값과의 차이 (치우침 포함) | 캘리브레이션 후 [D5](../D-calibration/D5-calibration-verification.md) 에서 확인 |

설계 계산에서 좋은 분해능이 나와도 반복성·정확도가 보장되지는 않습니다. A2의 "Z 반복성 ≤ 5 µm" 은 **실측으로 확인할 목표**이고, B1은 "적어도 분해능 측면에서 불가능하지 않다"를 보이는 단계입니다.

## 3. 입력과 산출물

| 구분 | 항목 | 형식 / 파일 | 비고 |
|---|---|---|---|
| 입력 | 목표 사양 (Z 반복성, XY 간격, FOV, 측정 깊이) | A2 사양표 `docs/design/A2_target_spec.yaml` | 예: 5 µm / 0.02 mm / 20 mm / 시편 높이 + 여유 |
| 입력 | 카메라 후보 사양 (픽셀 크기, 해상도) | 제조사 사양서 PDF | B4와 공유 |
| 입력 | 렌즈 후보 (초점거리) | 사양서 | B5와 공유 |
| 산출물 | 사양 계산기 | `scripts/design/b1_spec.py` | 6절 코드 |
| 산출물 | 원근 비선형 검증 스크립트 | `scripts/design/b1_pinhole.py` | 6절 코드 |
| 산출물 | 단위 테스트 | `tests/test_b1_spec.py` | pytest |
| 산출물 | 후보 비교표 | `results/design/B1_candidates.csv` | 후보 ≥ 3개, 각 행에 합격 여부 |
| 산출물 | 광학 설계 사양표 (확정안) | `config/hardware/optical_design.yaml` | 10절 양식. B2~B7, D 영역이 참조 |
| 산출물 | 1쪽 요약 (원리 그림 + 공식 + 기준안 수치) | `docs/design/B1_principle.md` | 팀 세미나 자료 겸용 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 기준 배치 | (a) 레이저 수직 + 카메라 경사 / (b) 카메라 수직 + 레이저 경사 | **(a)** | 높이가 변해도 측정 XY 위치가 그대로 → 높이맵 생성이 쉬움 (BLUEPRINT B2) |
| θ 정의 | 레이저–광축 사이 각 / 바닥–광축 사이 각 | **레이저–광축 사이 각** | 공식의 sinθ 가 이 정의 기준. 문서·코드 전체에 통일 |
| 설계용 서브픽셀 배수 k | 5 / 10 / 20 | **10 (보수적 점검은 5)** | BLUEPRINT의 현실 범위 5~20 의 중간. k=5 로도 목표의 2배 이내인지 함께 확인 |
| 설계 합격선 (Z) | δz/k ≤ 목표 / ≤ 목표의 0.6배 | **δz/10 ≤ 목표 Z 반복성 × 0.6 (= 3 µm)** | 스펙클·진동·온도 몫으로 40 % 여유를 남김 |
| 설계 합격선 (X) | δx ≤ 목표 XY 간격 | **δx ≤ 20 µm** | A2: XY 간격 ≈ 0.02 mm |
| 설계 합격선 (FOV) | ≥ 목표 / ≥ 목표 × 0.98 | **FOV_x ≥ 19.6 mm** (20 mm 의 98 %) | 기준안 19.87 mm 를 허용. 시편은 FOV 안에 들어가게 설계 ([E3](../E-specimen/E3-test-artifact.md)) |
| 실제 높이 계산 방식 | 선형 공식 / 광선–평면 교점 / LUT | **광선–평면 교점 (D2)** | 선형 공식은 원근 비선형 때문에 0~20 mm 에서 최대 0.6 mm 어긋남 |
| 기준안 부품 조합 | 1.6 MP(3.45 µm) + f25 + WD125 + θ30° / 5 MP(2.74 µm) 등 | **1.6 MP + f25 + WD 125 + θ 30°** | 모든 합격선 통과, 데이터량이 적어 초보에게 다루기 쉬움 (B4에서 최종 확정) |

## 5. 수행 절차

1. **원리 학습과 공식 손계산 (W1, 2026-10-06 ~ 10-09)**
   - [ ] 2.1절 그림을 종이에 직접 그리고, Δz → Δz·sinθ → M·Δz·sinθ → /p 의 4단계를 말로 설명해 본다.
   - [ ] 기준안(f 25, WD 125, p 3.45, θ 30°, 1440×1080) 수치를 **계산기로 손계산**: M = 0.25, δx = 13.8 µm, δz = 27.6 µm, FOV_x ≈ 19.9 mm, Z 범위 ≈ 29.8 mm.
   - [ ] 2.5절의 분해능/반복성/정확도 차이를 팀 회의에서 1분씩 설명한다.
2. **사양 계산기 작성 (W1, Python 첫 실습)**
   - [ ] 6.1절 `b1_spec.py` 를 그대로 입력해서 실행하고, 출력이 6.1절 기대 출력과 같은지 확인한다.
   - [ ] 손계산 값과 출력값이 소수 첫째 자리까지 일치하는지 확인한다.
   - [ ] 6.3절 테스트를 `pytest` 로 실행해서 3개 모두 통과시킨다.
3. **후보 조합 비교 (W1 ~ W2)**
   - [ ] B4·B5 후보에서 카메라 2종 이상 × 렌즈 2종 이상 × 각도 3개(20°, 30°, 40°)를 `candidates` 목록에 넣는다.
   - [ ] 결과를 `df.to_csv("results/design/B1_candidates.csv")` 로 저장한다.
   - [ ] 합격선(4절)을 모두 통과하는 조합에 표시하고, 통과 조합이 없으면 A2 담당자와 목표 재조정 회의를 잡는다.
4. **근사의 유효 범위 확인 (W2)**
   - [ ] 6.2절 `b1_pinhole.py` 를 실행해서 "공식 감도 = 수치 감도" 를 확인한다 (차이 < 0.5 %).
   - [ ] 목표 측정 깊이(예: 12 mm)에서 직선 근사 오차를 기록한다 → D2 에서 비선형 보정이 필요한 근거로 넘긴다.
   - [ ] z = 0, 10, 20 mm 에서 X 배율 변화(기준안 약 16 %)를 기록한다 → D2·[H1](../H-analysis/H1-gridding.md) 에서 X 좌표도 높이별로 계산해야 하는 근거.
5. **노이즈 → 높이 환산표 작성 (W2)**
   - [ ] 선 중심 노이즈 0.05 / 0.1 / 0.3 px 이 높이로 몇 µm 인지 표로 만든다 (기준안: 1.4 / 2.8 / 8.3 µm).
   - [ ] B6의 스펙클 추정값(기준안 450 nm, f/8: 단일 점 약 11.5 µm)과 나란히 적고, "단일 점 반복성 목표는 어렵고, 면 평균 지표로 5 µm 를 노린다" 같은 해석을 1~2문장으로 남긴다.
6. **광학 설계 사양표 확정 (W2 말, 2026-10-16 까지 초안)**
   - [ ] 10절 YAML 양식으로 `config/hardware/optical_design.yaml` 을 작성한다.
   - [ ] B2(각도·거리), B4(카메라), B5(렌즈) 담당자 확인 서명(이름·날짜)을 받는다.
   - [ ] M0 회의(2026-10-19 주)에서 발표하고 버전 `v1.0` 으로 고정한다. 이후 수정은 버전을 올리고 이유를 적는다.

## 6. Python 구현

### 6.1 사양 계산기 (`b1_spec.py`)

BLUEPRINT B1 함수를 확장해서 **목표 사양 합격 여부**까지 표로 보여 줍니다. 처음 Python을 쓰는 사람은 숫자만 바꿔 가며 실행해 보는 것부터 시작합니다.

```python
# b1_spec.py — 레이저 삼각측량 사양 계산기 (B1)
# 실행: python b1_spec.py
import numpy as np
import pandas as pd


def triangulation_spec(f_mm, wd_mm, pixel_um, n_cols, n_rows, theta_deg, subpixel=10):
    """BLUEPRINT B1 공식을 그대로 계산한다. 반환값은 딕셔너리(이름: 값)."""
    M = f_mm / (wd_mm - f_mm)                      # 광학 배율 (얇은 렌즈 근사)
    s = np.sin(np.radians(theta_deg))              # sinθ
    dz_1px = pixel_um / (M * s)                    # 픽셀 1개 이동에 해당하는 높이 [µm]
    return {
        "배율 M": round(M, 4),
        "dx [um]": round(pixel_um / M, 2),
        "dz 1px [um]": round(dz_1px, 2),
        "dz 서브픽셀 [um]": round(dz_1px / subpixel, 2),
        "FOV_x [mm]": round(n_cols * pixel_um / M / 1000, 2),
        "Z 범위(이론) [mm]": round(n_rows * pixel_um / (M * s) / 1000, 2),
    }


def check_against_target(spec, dz_target_um=5.0, dx_target_um=20.0, fov_target_mm=20.0):
    """A2 목표 사양과 비교해서 합격(True)/불합격(False)을 돌려준다."""
    return {
        "Z 목표 충족": spec["dz 서브픽셀 [um]"] <= dz_target_um,
        "X 간격 충족": spec["dx [um]"] <= dx_target_um,
        "FOV 충족": spec["FOV_x [mm]"] >= fov_target_mm * 0.98,   # 2 % 여유는 허용
    }


if __name__ == "__main__":
    # 부품 후보 조합: (이름, f[mm], WD[mm], 픽셀[µm], 가로px, 세로px, θ[°])
    candidates = [
        ("기준안 1.6MP f25 30°", 25, 125, 3.45, 1440, 1080, 30),
        ("각도 20°",            25, 125, 3.45, 1440, 1080, 20),
        ("각도 40°",            25, 125, 3.45, 1440, 1080, 40),
        ("5MP 2.74um f25",     25, 125, 2.74, 2448, 2048, 30),
        ("f16 (넓은 FOV)",      16, 125, 3.45, 1440, 1080, 30),
    ]
    rows = []
    for name, f, wd, p, nc, nr, th in candidates:
        spec = triangulation_spec(f, wd, p, nc, nr, th)
        rows.append({"후보": name, **spec, **check_against_target(spec)})
    df = pd.DataFrame(rows).set_index("후보")
    pd.set_option("display.width", 200)
    print(df.T.to_string())
```

실행 예시와 기대 출력:

```
$ python b1_spec.py
후보            기준안 1.6MP f25 30° 각도 20° 각도 40° 5MP 2.74um f25 f16 (넓은 FOV)
배율 M                       0.25   0.25   0.25           0.25       0.1468
dx [um]                    13.8   13.8   13.8          10.96         23.5
dz 1px [um]                27.6  40.35  21.47          21.92        47.01
dz 서브픽셀 [um]               2.76   4.03   2.15           2.19          4.7
FOV_x [mm]                19.87  19.87  19.87          26.83        33.84
Z 범위(이론) [mm]             29.81  43.58  23.19          44.89        50.77
Z 목표 충족                    True   True   True           True         True
X 간격 충족                    True   True   True           True        False
FOV 충족                     True   True   True           True         True
```

읽는 법: "각도 20°" 는 Z 범위가 넓지만 δz 가 커집니다(나빠짐). "f16" 은 FOV 가 넓지만 dx = 23.5 µm 로 X 간격 목표(20 µm)를 넘어 불합격입니다. 5 MP 후보는 모두 합격이지만 데이터량이 약 3.2배이므로 B4 에서 속도·용량과 함께 판단합니다.

### 6.2 핀홀 시뮬레이션으로 공식 검증 (`b1_pinhole.py`)

카메라를 "구멍 하나로 빛이 들어오는 상자(핀홀)"로 단순화하고, 레이저 평면 위 점을 실제로 투영해서 공식과 비교합니다.

```python
# b1_pinhole.py — 핀홀 카메라 모형으로 B1 공식(δz = p / (M·sinθ))을 수치로 검증 (B1)
# 실행: python b1_pinhole.py
import numpy as np

f_mm, WD, p_mm, theta_deg = 25.0, 125.0, 0.00345, 30.0
th = np.radians(theta_deg)

M = f_mm / (WD - f_mm)                 # 배율 0.25
b = M * WD                             # 렌즈~센서 거리(상거리) = 31.25 mm
fpx = b / p_mm                         # 핀홀 모형의 초점거리 [픽셀]

# 좌표: 레이저 평면 = x-z 평면(y=0), 레이저는 -z 방향(수직)으로 쏨.
# 카메라 중심은 y-z 평면에서 z축과 θ 기울어진 방향으로 WD 만큼 떨어져 있음.
C = np.array([0.0, WD * np.sin(th), WD * np.cos(th)])
d = -C / np.linalg.norm(C)             # 광축 방향 (원점을 바라봄)
ex = np.array([1.0, 0.0, 0.0])         # 이미지 가로(u) 방향 = 레이저 선 방향 X
ey = np.cross(d, ex)                   # 이미지 세로(v) 방향


def project(x, z):
    """레이저 평면 위 점 (x, 0, z) [mm] → 이미지 좌표 (u, v) [픽셀, 중심 기준]"""
    P = np.stack([x, np.zeros_like(x), z], axis=-1) - C
    depth = P @ d
    return fpx * (P @ ex) / depth, fpx * (P @ ey) / depth


# 1) 원점에서의 감도: 높이 1 µm 변화 → v 몇 픽셀 이동?
dz = 0.001
_, v0 = project(np.array([0.0]), np.array([0.0]))
_, v1 = project(np.array([0.0]), np.array([dz]))
sens_num = abs(v1[0] - v0[0]) / dz                    # [px/mm]
sens_formula = M * np.sin(th) / p_mm                  # [px/mm]
print(f"감도(수치)   : {sens_num:8.2f} px/mm -> 1px = {1000/sens_num:6.2f} um")
print(f"감도(B1 공식): {sens_formula:8.2f} px/mm -> 1px = {1000/sens_formula:6.2f} um")

# 2) 높이 0~20 mm 범위에서 v(z)가 직선에서 얼마나 벗어나는가 (원근 비선형)
z = np.linspace(0, 20, 201)
_, v = project(np.zeros_like(z), z)
coef = np.polyfit(z, v, 1)
resid = v - np.polyval(coef, z)
print(f"0~20 mm 직선 근사 최대 벗어남: {np.abs(resid).max():.1f} px "
      f"(= 약 {np.abs(resid).max() / sens_formula:.2f} mm 높이)")

# 3) 같은 이동량이라도 높이에 따라 배율이 달라짐 (X 방향 원근)
for zz in (0.0, 10.0, 20.0):
    u_a, _ = project(np.array([-5.0]), np.array([zz]))
    u_b, _ = project(np.array([5.0]), np.array([zz]))
    print(f"z={zz:4.1f} mm 에서 X 10 mm 길이의 이미지 길이: {u_b[0]-u_a[0]:7.1f} px")

# 4) 서브픽셀 노이즈 → 높이 노이즈 환산
for sigma_v in (0.05, 0.1, 0.3):
    print(f"선 중심 노이즈 {sigma_v:4.2f} px -> 높이 노이즈 {sigma_v / sens_formula * 1000:5.1f} um")
```

실행 예시와 기대 출력:

```
$ python b1_pinhole.py
감도(수치)   :    36.23 px/mm -> 1px =  27.60 um
감도(B1 공식):    36.23 px/mm -> 1px =  27.60 um
0~20 mm 직선 근사 최대 벗어남: 21.7 px (= 약 0.60 mm 높이)
z= 0.0 mm 에서 X 10 mm 길이의 이미지 길이:   724.6 px
z=10.0 mm 에서 X 10 mm 길이의 이미지 길이:   778.6 px
z=20.0 mm 에서 X 10 mm 길이의 이미지 길이:   841.2 px
선 중심 노이즈 0.05 px -> 높이 노이즈   1.4 um
선 중심 노이즈 0.10 px -> 높이 노이즈   2.8 um
선 중심 노이즈 0.30 px -> 높이 노이즈   8.3 um
```

해석:
- 원점 근처에서는 공식과 시뮬레이션이 **완전히 같습니다** (27.60 µm/px). 공식은 설계용으로 믿어도 됩니다.
- 그러나 0~20 mm 구간을 한 직선으로 보면 21.7 px(약 0.6 mm) 어긋납니다. **높이 계산을 선형 공식으로 하면 안 되는 이유**입니다.
- 같은 10 mm 길이가 높이에 따라 724.6 → 841.2 px 로 커집니다. X 좌표도 높이마다 다르게 환산해야 합니다(D2 의 광선–평면 교점 방식이 이를 자동으로 처리).

### 6.3 단위 테스트 (`tests/test_b1_spec.py`)

`b1_spec.py` 와 같은 폴더(또는 `PYTHONPATH` 로 찾을 수 있는 곳)에 두고 `pytest -q` 로 실행합니다.

```python
# test_b1_spec.py — b1_spec.py 의 계산이 손계산과 같은지 확인하는 단위 테스트
import numpy as np
from b1_spec import triangulation_spec


def test_reference_design():
    s = triangulation_spec(25, 125, 3.45, 1440, 1080, 30)
    assert s["배율 M"] == 0.25
    assert abs(s["dx [um]"] - 13.8) < 0.01
    assert abs(s["dz 1px [um]"] - 27.6) < 0.01
    assert abs(s["FOV_x [mm]"] - 19.87) < 0.01


def test_angle_in_degrees():
    # 각도를 도(°)로 넣는지 확인: 90° 이면 sinθ = 1 → dz = dx
    s = triangulation_spec(25, 125, 3.45, 1440, 1080, 90)
    assert np.isclose(s["dz 1px [um]"], s["dx [um]"], atol=0.01)


def test_larger_angle_better_dz():
    a = triangulation_spec(25, 125, 3.45, 1440, 1080, 20)
    b = triangulation_spec(25, 125, 3.45, 1440, 1080, 40)
    assert b["dz 1px [um]"] < a["dz 1px [um]"]
```

기대 출력:

```
$ pytest -q test_b1_spec.py
...                                                                      [100%]
3 passed in 0.34s
```

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 기준안 계산 재현 | 손계산 vs `b1_spec.py` | M = 0.25, δx = 13.8 µm, δz = 27.6 µm, FOV_x = 19.87 mm 가 소수 첫째 자리까지 일치 |
| 공식의 국소 정확성 | `b1_pinhole.py` 감도 비교 | 공식과 수치 감도 차이 < 0.5 % |
| 단위 테스트 | `pytest` | 3개 모두 통과 |
| 후보 비교 범위 | `B1_candidates.csv` | 후보 ≥ 3개, 각도 ≥ 3개 수준 포함 |
| 설계 합격선 | 4절 기준 | 확정안이 δz/10 ≤ 3 µm, δx ≤ 20 µm, FOV_x ≥ 19.6 mm 모두 충족 |
| 비선형 정량화 | `b1_pinhole.py` | 목표 깊이 범위에서 직선 근사 최대 오차가 기록되어 D2 로 전달됨 |
| 문서화 | `optical_design.yaml` | B2·B4·B5 담당 확인 + 버전 v1.0, M0 회의록에 첨부 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 각도를 도(°)로 `np.sin` 에 넣음 | δz 가 음수이거나 엉뚱하게 큼 (sin 30 rad = −0.99) | `np.radians()` 사용. 6.3절 테스트가 잡아냄 |
| µm 와 mm 혼용 | FOV 가 19870 mm 처럼 1000배 틀림 | 변수명에 단위 붙이기(`pixel_um`), 출력에 단위 표기 |
| θ 를 바닥 기준 각으로 착각 | θ=60° 로 넣어 δz 를 실제보다 좋게 계산 | 2.2절 정의 확인. 설계 그림에 각도 기준선 표시 |
| WD 를 렌즈 앞면부터 잼 | 실제 배율이 계산과 수 % 다름 | WD 는 설계 단계에선 근사로 쓰고, 실제 배율은 D1 결과(초점거리 px)로 확인 |
| k=20 서브픽셀을 당연시 | 설계상 1~2 µm, 실측 10 µm 이상 | k=5 보수 점검 병행, 스펙클 한계(B6) 함께 기록 |
| 선형 공식으로 실측 높이 계산 | 높은 곳일수록 높이·X 치수가 수백 µm 틀림 | 실측은 D2 방식만 사용 (6.2절 근거) |
| Y 분해능을 카메라 세로 픽셀로 착각 | 스캔 간격 설계를 빠뜨림 | Y 간격 = 스캔 간격 (C1). 사양표에 별도 칸 |
| 분해능 = 정확도로 보고 | 검토에서 "검증 안 된 수치" 지적 | 사양표에 "설계값(분해능)" 표기, 실측은 D5·I2 |

## 9. 위험 요소

- **목표와 물리 한계의 충돌**: A2 의 Z 반복성 5 µm 는 기준안의 스펙클 단일 점 한계(약 10~15 µm, B6 계산)보다 작습니다. 면 평균 지표(단차, 평면 중앙값)로는 달성 가능성이 있지만 단일 점 반복성으로는 어렵습니다. → M0 에서 "어떤 지표의 반복성인지"를 명확히 적고, M2([D5](../D-calibration/D5-calibration-verification.md))에서 실측으로 판정합니다.
- **설계값 과신**: 계산기 출력은 이상적인 조건의 값입니다. 실제 성능은 캘리브레이션 품질, 표면([E1](../E-specimen/E1-surface-optics.md)), 진동([C7](../C-mechanics/C7-vibration.md))에 좌우됩니다.
- **부품 사양 변경**: 납기 문제로 다른 카메라·렌즈를 사게 되면 모든 수치가 바뀝니다. 계산기를 다시 돌리고 사양표 버전을 올립니다.
- **학습 부담**: W1 에 Python 기초([K6](../K-management/K6-learning-roadmap.md))와 동시에 진행하므로, 코드는 6.1절만 먼저 완성하고 6.2절은 W2 로 미뤄도 됩니다.

## 10. 기록 양식

`config/hardware/optical_design.yaml` (확정 사양표)

```yaml
version: v1.0
date: 2026-10-19
author: ""
reviewed_by: {B2: "", B4: "", B5: ""}
target_spec_ref: docs/design/A2_target_spec.yaml
layout: laser_vertical_camera_tilted      # (a) 배치
theta_deg: 30                             # 레이저-광축 사이 각
camera: {model: "", pixel_um: 3.45, n_cols: 1440, n_rows: 1080}
lens: {model: "", f_mm: 25}
working_distance_mm: 125
design_values:                            # b1_spec.py 출력 그대로
  magnification: 0.25
  dx_um: 13.8
  dz_1px_um: 27.6
  dz_subpixel_k10_um: 2.76
  fov_x_mm: 19.87
  z_range_theory_mm: 29.81
nonlinearity:                             # b1_pinhole.py 출력
  linear_fit_max_dev_mm_over_0_20mm: 0.60
  x_scale_change_pct_over_0_20mm: 16.1
noise_budget_note: "단일 점 스펙클 약 11.5 um (B6). 면 평균 지표로 5 um 목표"
pass_fail: {z: true, x: true, fov: true}
change_log:
  - {version: v1.0, date: 2026-10-19, reason: "초안 확정 (M0)"}
```

후보 비교 기록 (`results/design/B1_candidates.csv` 열 구성)

| 후보 | 배율 M | dx [um] | dz 1px [um] | dz 서브픽셀 [um] | FOV_x [mm] | Z 범위(이론) [mm] | Z 목표 충족 | X 간격 충족 | FOV 충족 | 비고 |
|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | |

## 11. 참고 자료

- G. Häusler 연구진의 레이저 삼각측량 스펙클 한계 논문: R. G. Dorsch, G. Häusler, J. M. Herrmann, "Laser triangulation: fundamental uncertainty in distance measurement", *Applied Optics* (1994)
- R. Hartley, A. Zisserman, *Multiple View Geometry in Computer Vision* — 핀홀 카메라 모형, 투영 행렬
- E. Hecht, *Optics* — 얇은 렌즈 공식, 배율
- OpenCV 공식 문서 "Camera Calibration and 3D Reconstruction" (calib3d 모듈) — 핀홀 모형과 왜곡 모형
- VDI/VDE 2634 (광학 3D 측정 시스템 검증 지침), ISO 10360-8 (광학 거리 센서를 쓰는 좌표측정기 성능 시험) — 성능 표현 방식 참고
- JCGM 100:2008 (GUM, 측정 불확도 표현 지침) — 분해능을 불확도 요인으로 다루는 법 (I1 연계)
