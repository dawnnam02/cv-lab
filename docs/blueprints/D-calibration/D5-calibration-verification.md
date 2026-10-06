# D5. 캘리브레이션 검증 · 이력 관리

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: D. 캘리브레이션

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-01 ~ 2026-12-14 (W9-10) |
| 우선순위 | 긴급 |
| 트랙 | 실험·품질 |
| 선행 요소 | [D1 카메라 내부](D1-camera-intrinsics.md) · [D2 레이저 평면](D2-laser-plane.md) · [D3 스캔 축](D3-scan-axis.md) · [H1 점→격자 변환](../H-analysis/H1-gridding.md) · [F3 저장 형식·메타데이터](../F-acquisition/F3-data-storage.md) · [C6 온도](../C-mechanics/C6-temperature.md) |
| 후행 요소 | [D4 센서↔G코드 좌표](D4-sensor-to-gcode.md) · [I1 측정 불확도](../I-reliability/I1-uncertainty.md) · [I2 측정시스템분석](../I-reliability/I2-msa.md) · [K1 일정·마일스톤](../K-management/K1-schedule.md) · [K4 위험 관리](../K-management/K4-risks.md) |
| 관련 마일스톤 | **M2** — 게이지 블록 단차 오차 < 10 µm. **통과하지 못하면 본 실험으로 넘어가지 않음** (K1 진행/중단 판단) |

---

## 1. 목적

D1~D3 로 만든 센서가 **실제로 몇 µm 정확도로 재는지**를 인증된 기준물(게이지 블록, 정반, 정밀 구)로 확인하고, 그 결과를 **캘리브레이션 ID 와 함께 기록**해서 이후 모든 측정이 "어느 캘리브레이션으로, 얼마나 믿을 수 있는 상태에서" 이뤄졌는지 추적 가능하게 만드는 것입니다.

- 캘리브레이션 각 단계의 잔차(D1 재투영, D2 평면 잔차, D3 구 잔차)는 **내부 일관성**만 보여 줍니다. 최종 정확도는 **외부 기준물**로만 증명됩니다.
- M2 는 프로젝트 전체의 진행/중단 관문입니다. 센서가 목표 정밀도를 내지 못하면 이후 데이터는 의미가 없습니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 게이지 블록이란
양쪽 측정면 사이 거리가 매우 정밀하게 만들어진 강철(또는 세라믹) 블록입니다.
- 정밀도 등급은 ISO 3650 에서 K, 0, 1, 2 등급으로 나뉩니다. 각 블록의 **인증서에 명목값과의 편차**(예: +0.12 µm)가 적혀 있으면 그 값을 참값에 반영합니다.
- 게이지 블록 길이는 **20 °C 기준**으로 정의됩니다(ISO 1 기준 온도). 강철 열팽창계수 약 11.5 µm/(m·°C) 이므로 10 mm 블록이 22.4 °C 이면 +0.28 µm 길어집니다. 이 과제의 기준(10 µm)에 비하면 작지만 **온도는 반드시 기록**합니다(C6).

### 2.2 단차(Step height)를 재는 이유
레이저 삼각측량의 핵심 출력은 높이입니다. 정반 위에 높이 1, 2, 5, 10 mm 블록을 놓고 "블록 윗면 − 정반 면"을 재면 **높이 배율 오차(직선성)**와 **치우침**을 한 번에 봅니다. 높이가 클수록 오차가 커진다면 레이저 평면(D2)이나 보드 칸 크기(D1-8) 문제입니다.

### 2.3 반짝이는 게이지 블록 문제 (중요)
강철·세라믹 게이지 블록 표면은 거울처럼 연마(래핑)되어 있어 **레이저가 정반사**되고, 카메라 쪽으로 빛이 거의 오지 않거나 포화가 생깁니다(E1).
- **권장 대응**: 블록 윗면과 주변 정반을 **같은 번에 얇고 균일하게 무광 코팅**(스캔용 승화형 스프레이 등)합니다. 단차는 두 면의 **차이**라서 같은 두께의 코팅은 대부분 상쇄됩니다.
- 상쇄되지 않는 항목(평면도, 구 지름: 지름 + 2×코팅 두께)은 코팅 두께를 별도로 측정해 보정하거나 불확도에 넣습니다(E1).
- 코팅 두께 차이(위·아래 면)는 불확도 요인으로 기록합니다 (예: ±2 µm, 실측으로 확인).

### 2.4 측정 항목과 합격 기준 (BLUEPRINT D5)
| 검증 항목 | 기준물 | 합격 기준 |
|---|---|---|
| 단차 높이 | 게이지 블록 (1, 2, 5, 10 mm 단차) | 오차 < 10 µm |
| 평면도 | 광학 평판 / 정밀 석정반 | 높이 P-V < 10 µm |
| 구 지름 | 지름 인증 세라믹 구 | 지름 오차 < 15 µm |
| 길이 (X, Y) | 게이지 블록 길이 | 오차 < 0.1 % |

오차는 BLUEPRINT A1 규칙대로 **측정값 − 기준값** 이며, + 는 "더 크게 잼"입니다.

### 2.5 평면도를 그대로 P-V 로 재면 안 되는 이유
점 수십만 개에 노이즈 σ = 5 µm 가 있으면 최댓값 − 최솟값은 노이즈만으로 40~50 µm 가 됩니다. 그래서 평면 맞춤 잔차를 **0.5 mm × 0.5 mm 칸으로 평균**한 뒤(칸당 625점 → 노이즈 약 0.2 µm) P-V 를 계산합니다. 이 규칙은 결정 사항(D5-4)으로 고정해 보고서에 적습니다.

### 2.6 캘리브레이션 ID 와 이력 관리
- 캘리브레이션마다 ID `CAL-YYYY-MM-DD-A` (같은 날 두 번째면 `-B`).
- 모든 측정 메타데이터(F3 의 `calibration_id`)에 ID 를 적어 "이 데이터는 어떤 캘리브레이션으로 계산되었나"를 추적합니다.
- 기준 마커 조립 상태는 별도 ID `FID-…` (D4).

### 2.7 재교정 조건 (BLUEPRINT D5)
1. 렌즈·레이저·카메라를 건드렸을 때 (초점·조리개·필터·마운트)
2. 장비를 옮겼을 때
3. **일일 점검이 관리 한계를 벗어났을 때** (I2 안정성, 6.2 코드)
4. 정기: 월 1회

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식·위치 | 설명 |
|---|---|---|---|
| 입력 | 캘리브레이션 묶음 | `config/calibration/CAL-2026-12-08-A/` (`camera_intrinsics.yaml`, `laser_plane.yaml`, `scan_axis.yaml`) | D1~D3 |
| 입력 | 검증 스캔 높이맵 | `data/processed/verify/CAL-2026-12-08-A/step.npy`, `flat.npy`, `len_x.npy`, `len_y.npy` (격자 0.02 mm, NaN = 없음) | H1 로 만든 {M} 높이맵 |
| 입력 | 구 점군 | `.../sphere.npy` (N×3, mm) | Ø 6 mm 인증 구 |
| 입력 | 기준물 배치·인증값 | `config/verification_layout.yaml` | ROI(mm), 명목값, 인증 편차 |
| 입력 | 환경 | 실내·블록 온도 (0.1 °C) | C6 |
| 산출물 | **항목별 검증표** | `config/calibration/CAL-2026-12-08-A/verification_CAL-2026-12-08-A.csv` | item, 기준, 측정, 오차, 기준, 판정, 점 수 |
| 산출물 | 요약 | `verification_CAL-2026-12-08-A.yaml` | 종합 판정 + 메타데이터 |
| 산출물 | 그림 | `verification_CAL-2026-12-08-A.png` | 높이맵 + 항목별 오차/기준 비율 막대 |
| 산출물 | **이력** | `config/calibration/calibration_history.csv` | 캘리브레이션마다 한 줄 누적 |
| 산출물 | 일일 점검 기록 | `config/calibration/daily_check_log.csv` | 날짜, ID, 5 mm 단차 오차, 관리 한계 이탈 여부 |

---

## 4. 결정 사항

| ID | 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|---|
| D5-1 | 단차 기준물 | 강철 / 세라믹 게이지 블록 | 보유한 것 사용 + **무광 코팅** | 정반사 대책 (2.3) |
| D5-2 | 단차 값 | – | 1, 2, 5, 10 mm | BLUEPRINT D5. 측정 깊이 범위 전체 확인 |
| D5-3 | 단차 계산법 | 평균 차 / **정반 평면 맞춤 + 윗면 중앙값** | 후자 | 기울기 보정 + 이상치에 강함 |
| D5-4 | 평면도 계산 | 원시 P-V / **0.5 mm 칸 평균 후 P-V** | 칸 평균 | 노이즈가 P-V 를 부풀림 (2.5) |
| D5-5 | 경계 제외 폭 | 0.25 / **0.3** / 0.5 mm | 0.3 mm | E2 엣지 효과. J2 기본 `edge_band_mm: 0.25` 보다 약간 넓게 |
| D5-6 | 길이 경계 정의 | 최외곽 칸 / **반높이(50 %) 교차 서브셀 보간** | 반높이 | 칸 크기(20 µm)보다 정밀 |
| D5-7 | 기준값 | 명목값 / **명목 + 인증 편차** | 인증 편차 반영 | 기준물 오차를 측정 오차로 착각하지 않기 |
| D5-8 | 일일 점검 | 없음 / **세션 시작마다 5 mm 단차 1회** | 5 mm 단차 | I2 안정성. 5분 이내로 끝나는 항목 |
| D5-9 | 관리 한계 | 고정값 / **처음 20회 평균 ± 3σ** | ±3σ | 장비 고유 변동 기준 |
| D5-10 | 재교정 주기 | – | 월 1회 + 2.7 조건 | BLUEPRINT D5 |

---

## 5. 수행 절차

1. **준비 (W9)**
   - [ ] 게이지 블록 1, 2, 5, 10 mm(단차용), 15 mm·30 mm(길이용), Ø 6 mm 인증 구, 정반·광학 평판 준비. 인증서 편차를 `verification_layout.yaml` 에 입력
   - [ ] 블록 세척(무수 알코올) → 실온에서 **2시간 이상** 온도 안정화(손으로 잡은 블록은 팽창)
   - [ ] 무광 코팅이 필요하면 블록·정반을 같은 번에 코팅, 코팅 두께를 마이크로미터로 측정·기록
   - [ ] 장비 30분 워밍업
2. **단차 스캔**
   - [ ] 블록 4개를 스캔 방향(y)으로 나란히, 블록 사이 정반이 보이게 배치. **키 큰 블록 뒤(+y)는 카메라 그림자(h·tan30° ≈ 0.58 h)** 가 생기므로 간격을 6~8 mm 확보
   - [ ] 측정 조건은 본 실험과 동일(F2): 피치 0.02 mm, 노출, 레이저 출력
   - [ ] 3회 반복 스캔
3. **평면도·길이·구 스캔**
   - [ ] 정반(또는 광학 평판) 빈 영역 20 × 30 mm
   - [ ] 15 mm 블록을 X 방향, 30 mm 블록을 Y(스캔) 방향으로 눕혀 스캔
   - [ ] Ø 6 mm 구 스캔
4. **계산과 판정**
   - [ ] H1 으로 높이맵 생성 (보간 없음, NaN 유지)
   - [ ] 6.1 스크립트 실행 → CSV·YAML·PNG·이력 한 줄
   - [ ] 3회 반복의 평균 오차와 표준편차 기록 (반복성 참고값, I2 로 이어짐)
5. **불합격 시 원인 조사 순서**
   - [ ] 단차 오차가 높이에 비례 → D2 (자세 높이 분포), D1-8 (보드 칸 크기)
   - [ ] 단차 오차가 일정한 치우침 → 코팅 두께 차, 정반 영역 선택, 경계 제외 폭
   - [ ] Y 길이만 불합격 → D3 배율 k
   - [ ] X 길이만 불합격 → D1 fx, D2
   - [ ] 평면도만 불합격 → 렌즈 왜곡(D1), 스테이지 직진도(D3 6.2)
   - [ ] 원인 수정 후 해당 요소부터 다시 → 새 캘리브레이션 ID
6. **기록과 운영**
   - [ ] 합격 시 `calibration_history.csv` 에 PASS, 해당 ID 를 "현재 사용" 으로 지정
   - [ ] 다음 날부터 세션 시작마다 일일 점검(6.2) → 20회 쌓이면 관리 한계 확정
   - [ ] M2 판정을 K1 일정표에 기록

---

## 6. Python 구현

### 6.1 검증 리포트 스크립트 (`d5_verification_report.py`)
합성 높이맵에 **숨은 장비 오차**(높이 배율 +0.03 %, X 배율 −0.02 %, Y 배율 +0.03 %, 노이즈 5 µm, 경계 섞임, 카메라 그림자, 결측 1 %)를 넣고, 검증 스크립트가 이를 찾아내며 판정·기록하는지 확인합니다.

```python
"""
D5. 캘리브레이션 검증 리포트 — 게이지 블록 단차·평면도·길이·구 지름 → 합격/불합격 + 이력 기록
--------------------------------------------------------------------------------------
* 입력: {M} 좌표 높이맵 (H1 결과, 격자 0.02 mm, NaN = 측정 없음) + 기준물 배치(ROI) + 인증값
* 출력: verification_<CAL-ID>.csv (항목별 표), verification_<CAL-ID>.yaml (요약),
        calibration_history.csv (한 줄 추가), verification_<CAL-ID>.png (그림)
* 이 예제는 합성 높이맵으로 실행됩니다. 실제로는 synth_* 대신 np.load("...npy") 로 읽으세요.
실행:  python3 d5_verification_report.py
"""
import csv
import datetime as dt
import os
import numpy as np
import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares

rng = np.random.default_rng(5)
RES = 0.02                                  # 격자 간격 [mm]
CAL_ID = "CAL-2026-12-08-A"
CRITERIA = {"step_um": 10.0, "flatness_um": 10.0, "sphere_diam_um": 15.0, "length_pct": 0.1}
EDGE_BAND_MM = 0.3                          # 경계에서 제외할 띠 폭 (E2 엣지 효과)
THETA = np.radians(30)                      # 삼각측량 각도 (가림 계산용)

# 측정 장비의 '숨은' 오차 (합성용 정답) — 검증이 이것을 잡아내야 함
TRUE_Z_SCALE, TRUE_X_SCALE, TRUE_Y_SCALE = 1.0003, 0.9998, 1.0003
NOISE_UM = 5.0


# ============================================================ 합성 데이터 생성 (실제에선 불필요)
def synth_heightmap(nx, ny, boxes, tilt=(0.0004, -0.0003)):
    """boxes: [(x0, x1, y0, y1, h), ...] 직육면체 기준물. 경계 칸은 섞인 높이(mixed pixel),
    +y 쪽 뒤편은 카메라 그림자(h·tanθ)로 NaN. 바닥은 살짝 기울어진 정반."""
    x = (np.arange(nx) + 0.5) * RES / TRUE_X_SCALE              # 칸 i 의 '실제' 물리 위치
    y = (np.arange(ny) + 0.5) * RES / TRUE_Y_SCALE              # (측정값 = 참값 × 배율 이 되도록)
    X, Y = np.meshgrid(x, y)
    Hm = tilt[0] * X + tilt[1] * Y
    shadow = np.zeros_like(Hm, bool)
    for x0, x1, y0, y1, h in boxes:
        fx = np.clip(np.minimum(X - x0, x1 - X) / RES + 0.5, 0, 1)   # 경계 칸 섞임 비율
        fy = np.clip(np.minimum(Y - y0, y1 - Y) / RES + 0.5, 0, 1)
        Hm = Hm + h * TRUE_Z_SCALE * fx * fy
        shadow |= (Y > y1 + RES) & (Y < y1 + h * np.tan(THETA)) & (X > x0) & (X < x1)
    Hm = Hm + rng.normal(0, NOISE_UM / 1000, Hm.shape)
    Hm[shadow] = np.nan
    Hm[rng.random(Hm.shape) < 0.01] = np.nan                       # 무작위 결측 1 %
    return Hm


def synth_sphere_cap(R_true=3.0, n=8000):
    th = np.radians(rng.uniform(30, 90, n)); ph = rng.uniform(0, 2 * np.pi, n)
    d = np.stack([np.cos(th) * np.cos(ph), np.cos(th) * np.sin(ph), np.sin(th)], 1)
    P = d * (R_true + rng.normal(0, NOISE_UM / 1000, (n, 1)))
    return P * [TRUE_X_SCALE, TRUE_Y_SCALE, TRUE_Z_SCALE]


# ============================================================ 검증 계산 함수 (실제 사용)
def roi_mask(shape, x0, x1, y0, y1, shrink=0.0):
    """mm 단위 사각 영역 → 불리언 마스크. shrink 만큼 안쪽으로 줄임(경계 띠 제외)"""
    ny, nx = shape
    x = (np.arange(nx) + 0.5) * RES; y = (np.arange(ny) + 0.5) * RES
    X, Y = np.meshgrid(x, y)
    return (X > x0 + shrink) & (X < x1 - shrink) & (Y > y0 + shrink) & (Y < y1 - shrink)


def fit_plane_robust(H, mask, n_iter=3, k=3.0):
    """마스크 안의 점에 z = a x + b y + c 맞춤, 3σ 넘는 점 제외하며 반복 → (a, b, c), 잔차"""
    ny, nx = H.shape
    X, Y = np.meshgrid((np.arange(nx) + 0.5) * RES, (np.arange(ny) + 0.5) * RES)
    m = mask & ~np.isnan(H)
    for _ in range(n_iter):
        A = np.column_stack([X[m], Y[m], np.ones(m.sum())])
        coef, *_ = np.linalg.lstsq(A, H[m], rcond=None)
        r = H[m] - A @ coef
        keep = np.abs(r) < k * r.std()
        idx = np.flatnonzero(m)
        m = m.copy(); m.flat[idx[~keep]] = False
    plane = coef[0] * X + coef[1] * Y + coef[2]
    return plane, H - plane, m


def step_heights(H, base_rois, steps):
    """steps: [{'name','roi','nominal_mm','cert_dev_um'}]. 단차 = 윗면 중앙값 − 바닥 평면(같은 위치)"""
    base = np.zeros(H.shape, bool)
    for r in base_rois:
        base |= roi_mask(H.shape, *r, shrink=EDGE_BAND_MM)
    plane, _, _ = fit_plane_robust(H, base)
    rows = []
    for s in steps:
        m = roi_mask(H.shape, *s["roi"], shrink=EDGE_BAND_MM) & ~np.isnan(H)
        meas = np.median(H[m] - plane[m])
        ref = s["nominal_mm"] + s["cert_dev_um"] / 1000           # 인증서 편차 반영한 참값
        rows.append({"item": f"단차 {s['name']}", "reference_mm": ref, "measured_mm": meas,
                     "error_um": (meas - ref) * 1000, "criterion": f"|e| < {CRITERIA['step_um']:.0f} µm",
                     "pass": abs(meas - ref) * 1000 < CRITERIA["step_um"], "n_points": int(m.sum())})
    return rows


def flatness(H, roi, cell_mm=0.5):
    """평면도: 평면 맞춤 잔차를 0.5 mm 칸으로 평균(노이즈 제거) 후 P-V"""
    m = roi_mask(H.shape, *roi, shrink=EDGE_BAND_MM)
    _, resid, used = fit_plane_robust(H, m)
    k = int(round(cell_mm / RES))
    r = np.where(used, resid, np.nan)
    ny, nx = (r.shape[0] // k) * k, (r.shape[1] // k) * k
    blocks = r[:ny, :nx].reshape(ny // k, k, nx // k, k)
    with np.errstate(all="ignore"):
        cellmean = np.nanmean(blocks, axis=(1, 3))
        cnt = np.sum(~np.isnan(blocks), axis=(1, 3))
    cellmean = cellmean[cnt > 0.5 * k * k]                       # 반 이상 채워진 칸만
    pv = (cellmean.max() - cellmean.min()) * 1000
    return {"item": "평면도 (정반)", "reference_mm": 0.0, "measured_mm": pv / 1000, "error_um": pv,
            "criterion": f"P-V < {CRITERIA['flatness_um']:.0f} µm", "pass": pv < CRITERIA["flatness_um"],
            "n_points": int(used.sum())}


def edge_positions(profile, level):
    """1D 프로파일에서 level 을 처음 넘는 곳과 마지막으로 넘는 곳 (선형 보간 서브셀)"""
    above = profile > level
    idx = np.flatnonzero(above)
    if len(idx) < 2:
        return np.nan, np.nan
    i0, i1 = idx[0], idx[-1]
    def cross(a, b):                                            # 칸 a(아래)와 b(위) 사이 교차점
        za, zb = profile[a], profile[b]
        if np.isnan(za) or np.isnan(zb):
            return np.nan
        return a + (level - za) / (zb - za) * (b - a)
    left = cross(i0 - 1, i0) if i0 > 0 else np.nan
    right = cross(i1 + 1, i1) if i1 < len(profile) - 1 else np.nan
    return left, right


def block_length(H, axis, nominal_mm, height_mm, band, cert_dev_um=0.0):
    """게이지 블록 길이 (측정면 사이 거리). axis='x' → 행마다, 'y' → 열마다 양 끝 경계를 찾음"""
    lines = H if axis == "x" else H.T
    lo, hi = int(band[0] / RES), int(band[1] / RES)              # 사용할 행(열) 범위
    lengths = []
    for prof in lines[lo:hi]:
        l, r = edge_positions(prof, height_mm / 2)              # 반높이(50 %) 경계
        if not (np.isnan(l) or np.isnan(r)):
            lengths.append((r - l) * RES)
    meas = np.median(lengths)
    ref = nominal_mm + cert_dev_um / 1000
    pct = 100 * (meas - ref) / ref
    return {"item": f"길이 {axis.upper()} ({nominal_mm:g} mm 블록)", "reference_mm": ref, "measured_mm": meas,
            "error_um": (meas - ref) * 1000, "criterion": f"|e| < {CRITERIA['length_pct']}%",
            "pass": abs(pct) < CRITERIA["length_pct"], "n_points": len(lengths)}


def sphere_diameter(P, cert_diam_mm):
    """반지름 자유 구 맞춤 → 지름"""
    A = np.hstack([2 * P, np.ones((len(P), 1))])
    sol, *_ = np.linalg.lstsq(A, (P**2).sum(1), rcond=None)
    c0 = sol[:3]; r0 = np.sqrt(sol[3] + c0 @ c0)
    f = lambda x: np.linalg.norm(P - x[:3], axis=1) - x[3]
    x = least_squares(f, np.r_[c0, r0]).x
    d = 2 * x[3]
    return {"item": "구 지름", "reference_mm": cert_diam_mm, "measured_mm": d,
            "error_um": (d - cert_diam_mm) * 1000, "criterion": f"|e| < {CRITERIA['sphere_diam_um']:.0f} µm",
            "pass": abs(d - cert_diam_mm) * 1000 < CRITERIA["sphere_diam_um"], "n_points": len(P)}


# ============================================================ 리포트 저장
def write_report(rows, meta, H_step, out_dir="."):
    overall = all(r["pass"] for r in rows)
    tag = meta["calibration_id"]
    with open(os.path.join(out_dir, f"verification_{tag}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
    summary = dict(meta, overall_pass=overall,
                   items={r["item"]: {"error_um": round(float(r["error_um"]), 2), "pass": bool(r["pass"])} for r in rows})
    with open(os.path.join(out_dir, f"verification_{tag}.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(summary, f, allow_unicode=True, sort_keys=False)
    hist = os.path.join(out_dir, "calibration_history.csv")
    new = not os.path.exists(hist)
    with open(hist, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["calibration_id", "verified_at", "operator", "room_temp_C", "overall_pass",
                        "max_step_err_um", "flatness_um", "notes"])
        steps = [abs(r["error_um"]) for r in rows if r["item"].startswith("단차")]
        flat = [r["error_um"] for r in rows if r["item"].startswith("평면도")]
        w.writerow([tag, meta["verified_at"], meta["operator"], meta["room_temp_C"], overall,
                    round(max(steps), 2), round(flat[0], 2), meta.get("notes", "")])
    # 그림: 왼쪽 높이맵, 오른쪽 항목별 오차/기준 비율
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    im = ax[0].imshow(H_step, origin="lower", cmap="viridis",
                      extent=[0, H_step.shape[1] * RES, 0, H_step.shape[0] * RES], aspect="auto")
    fig.colorbar(im, ax=ax[0], label="z [mm]")
    ax[0].set_xlabel("x [mm]"); ax[0].set_ylabel("y [mm]"); ax[0].set_title("step scan (M frame)")
    ratio = []
    for r in rows:
        lim = {"단": CRITERIA["step_um"], "평": CRITERIA["flatness_um"], "구": CRITERIA["sphere_diam_um"]}.get(r["item"][0])
        ratio.append(abs(r["error_um"]) / lim if lim else abs(r["error_um"] / 1000 / r["reference_mm"] * 100) / CRITERIA["length_pct"])
    ax[1].barh(range(len(rows)), ratio, color=["tab:green" if r["pass"] else "tab:red" for r in rows])
    ax[1].axvline(1.0, color="k", ls="--"); ax[1].set_yticks(range(len(rows)))
    ax[1].set_yticklabels([f"item {i+1}" for i in range(len(rows))])
    ax[1].set_xlabel("|error| / criterion (pass < 1)"); ax[1].set_title(f"{tag}: {'PASS' if overall else 'FAIL'}")
    fig.tight_layout(); fig.savefig(os.path.join(out_dir, f"verification_{tag}.png"), dpi=150); plt.close(fig)
    return overall


def main():
    # ---- 1) 단차 스캔: 1, 2, 5, 10 mm 블록을 y 방향으로 나란히 (x 방향은 FOV 20 mm 전체를 덮음)
    layout = {"x": (0, 20), "blocks": [("1 mm", 3, 12, 1.0, +0.10), ("2 mm", 16, 25, 2.0, -0.05),
                                       ("5 mm", 29, 38, 5.0, +0.12), ("10 mm", 44, 53, 10.0, +0.20)]}
    boxes = [(-5, 25, y0, y1, h) for _, y0, y1, h, _ in layout["blocks"]]
    H_step = synth_heightmap(1000, 3100, boxes)                     # 20 x 62 mm
    base_rois = [(0, 20, 0, 3), (0, 20, 12 + 0.58, 16), (0, 20, 25 + 1.16, 29),
                 (0, 20, 38 + 2.89, 44), (0, 20, 53 + 5.78, 62)]   # 블록 사이 정반 (그림자 제외)
    steps = [{"name": n, "roi": (0, 20, y0, y1), "nominal_mm": h, "cert_dev_um": dev}
             for n, y0, y1, h, dev in layout["blocks"]]
    rows = step_heights(H_step, base_rois, steps)
    # ---- 2) 평면도: 정반(또는 광학 평판) 빈 영역 20 x 30 mm 스캔
    H_flat = synth_heightmap(1000, 1500, [])
    rows.append(flatness(H_flat, (0, 20, 0, 30)))
    # ---- 3) 길이: 15 mm 블록을 X 방향, 30 mm 블록을 Y(스캔) 방향으로 눕혀서 스캔 (높이 9 mm)
    H_lx = synth_heightmap(1000, 1000, [(2.5, 17.5, -5, 25, 9.0)])
    rows.append(block_length(H_lx, "x", 15.0, 9.0, band=(5, 15), cert_dev_um=+0.15))
    H_ly = synth_heightmap(1000, 2000, [(-5, 25, 4, 34, 9.0)])
    rows.append(block_length(H_ly, "y", 30.0, 9.0, band=(5, 15), cert_dev_um=-0.10))
    # ---- 4) 구 지름: Ø 6.000 mm 세라믹 구 (인증 편차 0)
    rows.append(sphere_diameter(synth_sphere_cap(3.0), 6.000))

    meta = {"calibration_id": CAL_ID, "verified_at": dt.date(2026, 12, 10).isoformat(),
            "operator": "student_A", "room_temp_C": 22.4, "gauge_block_temp_C": 22.3,
            "files": ["camera_intrinsics.yaml", "laser_plane.yaml", "scan_axis.yaml"],
            "notes": "합성 데이터 시연"}
    if os.path.exists("calibration_history.csv"):
        os.remove("calibration_history.csv")                       # 시연을 위해 매번 새로 (실제로는 지우지 말 것!)
    overall = write_report(rows, meta, H_step)
    print(f"{'항목':<22}{'기준[mm]':>10}{'측정[mm]':>11}{'오차[µm]':>10}  판정")
    for r in rows:
        print(f"{r['item']:<22}{r['reference_mm']:>10.4f}{r['measured_mm']:>11.4f}{r['error_um']:>+10.2f}  "
              f"{'합격' if r['pass'] else '불합격'} ({r['criterion']})")
    print(f"종합: {'PASS → 이 캘리브레이션으로 측정 진행' if overall else 'FAIL → 원인 조사 후 재교정'}")
    print(f"저장: verification_{CAL_ID}.csv / .yaml / .png, calibration_history.csv")


if __name__ == "__main__":
    main()
```

**실행 예시와 기대 출력** (약 7초)

```
$ python3 d5_verification_report.py
항목                        기준[mm]     측정[mm]    오차[µm]  판정
단차 1 mm                   1.0001     1.0003     +0.21  합격 (|e| < 10 µm)
단차 2 mm                   1.9999     2.0006     +0.65  합격 (|e| < 10 µm)
단차 5 mm                   5.0001     5.0015     +1.39  합격 (|e| < 10 µm)
단차 10 mm                 10.0002    10.0030     +2.80  합격 (|e| < 10 µm)
평면도 (정반)                  0.0000     0.0015     +1.49  합격 (P-V < 10 µm)
길이 X (15 mm 블록)          15.0001    14.9981     -2.00  합격 (|e| < 0.1%)
길이 Y (30 mm 블록)          29.9999    30.0097     +9.84  합격 (|e| < 0.1%)
구 지름                      6.0000     5.9979     -2.11  합격 (|e| < 15 µm)
종합: PASS → 이 캘리브레이션으로 측정 진행
저장: verification_CAL-2026-12-08-A.csv / .yaml / .png, calibration_history.csv
```

**출력 읽는 법**
- 단차 오차가 1 → 10 mm 로 갈수록 +0.2 → +2.8 µm 로 **높이에 비례**해 커집니다. 숨겨 둔 높이 배율 +0.03 %(10 mm 에서 +3 µm)를 정확히 잡아낸 것입니다. 실제 장비에서 이런 비례 경향이 크면 D2·D1-8 을 의심합니다.
- 길이 X −2.0 µm(−0.013 %), Y +9.8 µm(+0.033 %) → 숨겨 둔 X −0.02 %, Y +0.03 % 와 일치. 합격이지만 Y 의 +0.03 % 는 D3 배율 보정 여지로 기록해 둡니다.
- 평면도 1.5 µm 는 0.5 mm 칸 평균 후 값입니다(원시 P-V 는 노이즈 때문에 수십 µm).
- 생성 파일: `verification_CAL-2026-12-08-A.csv` 의 내용은 아래와 같습니다.

```
item,reference_mm,measured_mm,error_um,criterion,pass,n_points
단차 1 mm,1.0001,1.00031,0.20798,|e| < 10 µm,True,403308
단차 2 mm,1.99995,2.0006,0.65495,|e| < 10 µm,True,403312
단차 5 mm,5.00012,5.00151,1.38893,|e| < 10 µm,True,403372
단차 10 mm,10.0002,10.003,2.79665,|e| < 10 µm,True,403406
평면도 (정반),0.0,0.00149,1.49106,P-V < 10 µm,True,1407206
길이 X (15 mm 블록),15.00015,14.99815,-2.00145,|e| < 0.1%,True,477
길이 Y (30 mm 블록),29.9999,30.00974,9.84186,|e| < 0.1%,True,488
구 지름,6.0,5.99789,-2.11273,|e| < 15 µm,True,8000
```

### 6.2 일일 점검 관리도 (`d5_daily_check.py`)
세션 시작마다 5 mm 단차를 한 번 재서 기록하고, 처음 20회로 만든 관리 한계(평균 ± 3σ)를 벗어나면 측정을 멈추고 재교정합니다. 합성 기록에서는 23일째 렌즈가 살짝 풀린 상황(+9 µm 이동)을 넣었습니다.

```python
"""
D5 보충: 일일 점검 관리도 (I2 안정성). 매 세션 시작 때 5 mm 게이지 블록 단차를 1회 측정해 기록하고,
처음 20회로 만든 관리 한계(평균 ± 3σ)를 벗어나면 '재교정 필요' 를 알립니다.
실행:  python3 d5_daily_check.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(8)
# 합성 기록: 25일 동안의 5 mm 단차 오차 [µm]. 23일째 렌즈가 살짝 풀렸다고 가정 (+9 µm 이동)
err = rng.normal(0.8, 1.5, 25)
err[22:] += 9.0
log = pd.DataFrame({"date": pd.date_range("2026-12-14", periods=25, freq="D").strftime("%Y-%m-%d"),
                    "calibration_id": "CAL-2026-12-08-A", "step5_error_um": err.round(2)})

base = log["step5_error_um"].iloc[:20]                # 기준 기간 (처음 20회)
center, sigma = base.mean(), base.std(ddof=1)
ucl, lcl = center + 3 * sigma, center - 3 * sigma
log["out_of_control"] = (log["step5_error_um"] > ucl) | (log["step5_error_um"] < lcl)
log["out_of_spec"] = log["step5_error_um"].abs() >= 10.0      # D5 합격 기준 자체를 넘음

print(f"중심선 {center:+.2f} µm, 관리 한계 [{lcl:+.2f}, {ucl:+.2f}] µm")
print(log.tail(5).to_string(index=False))
first = log.loc[log["out_of_control"], "date"]
print("첫 이탈일:", first.iloc[0] if len(first) else "없음", "→ 측정 중단, 원인 조사·재교정")
log.to_csv("daily_check_log.csv", index=False)
```

```
$ python3 d5_daily_check.py
중심선 +0.67 µm, 관리 한계 [-4.37, +5.72] µm
      date   calibration_id  step5_error_um  out_of_control  out_of_spec
2027-01-03 CAL-2026-12-08-A            1.34           False        False
2027-01-04 CAL-2026-12-08-A            1.19           False        False
2027-01-05 CAL-2026-12-08-A            7.34            True        False
2027-01-06 CAL-2026-12-08-A           10.34            True         True
2027-01-07 CAL-2026-12-08-A            9.62            True        False
첫 이탈일: 2027-01-05 → 측정 중단, 원인 조사·재교정
```

**읽는 법**: 2027-01-05 의 7.34 µm 는 합격 기준(10 µm) 안이지만 **관리 한계(+5.72 µm)를 벗어났습니다**. 합격 기준을 넘기 하루 전에 이상을 잡아낸 것이 관리도의 장점입니다. 이 날짜 이후 측정 데이터는 재교정 후 재측정 대상으로 표시합니다.

### 6.3 실제 데이터에 적용할 때 바꿀 부분
- `synth_heightmap(...)` → `np.load("step.npy")` 등. 높이맵의 원점이 ROI 좌표와 맞도록 H1 의 격자 원점 정보를 함께 읽기
- `layout`, `base_rois`, 인증 편차 → `config/verification_layout.yaml` 에서 읽기 (J2 원칙: 코드에 숫자를 박지 않음)
- `os.remove("calibration_history.csv")` 줄은 **반드시 삭제** (시연용)

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 | 6.1 합성 결과 |
|---|---|---|---|
| 단차 1, 2, 5, 10 mm | 정반 평면 맞춤 + 윗면 중앙값 | 각 \|오차\| **< 10 µm** | +0.21 / +0.65 / +1.39 / +2.80 µm |
| 평면도 | 0.5 mm 칸 평균 후 P-V | **< 10 µm** | 1.49 µm |
| 길이 X (15 mm) | 반높이 경계 서브셀 | \|오차\| **< 0.1 %** (15 µm) | −2.00 µm (−0.013 %) |
| 길이 Y (30 mm) | 반높이 경계 서브셀 | \|오차\| **< 0.1 %** (30 µm) | +9.84 µm (+0.033 %) |
| 구 지름 (Ø 6 mm) | 반지름 자유 구 맞춤 | \|오차\| **< 15 µm** | −2.11 µm |
| 반복성 | 단차 3회 반복 표준편차 | < 3 µm (참고, I2 로 정식 평가) | (실측 시 기록) |
| 기록 완결성 | CSV·YAML·PNG·이력 한 줄 | 4개 파일 모두 존재, ID 일치 | 생성 확인 |

**완료 판정 = M2 통과**: 위 표의 기준 항목이 모두 합격하고 이력에 PASS 가 기록되면 완료. 하나라도 불합격이면 5장 5단계 원인 조사 → 해당 요소 재교정 → 새 ID 로 D5 반복. **M2 를 통과하기 전에는 본 실험(W18~)용 측정을 하지 않습니다.**

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 래핑된 게이지 블록을 그대로 스캔 | 윗면 결측·포화, 단차가 수십 µm 틀림 | 블록·정반 동시 무광 코팅 (2.3) |
| 손으로 잡은 직후 측정 | 큰 블록일수록 + 오차 | 장갑·집게 사용, 2시간 안정화 |
| 인증 편차 무시 | 기준물 오차를 장비 오차로 착각 | 참값 = 명목 + 인증 편차 (D5-7) |
| 경계 띠를 빼지 않음 | 단차 중앙값이 경계 섞임에 끌림 | 0.3 mm 제외 (D5-5) |
| 그림자 영역을 정반 ROI 에 포함 | NaN 이 많거나 평면 맞춤 이상 | 블록 뒤 h·tan30° 제외 (코드의 `base_rois`) |
| 원시 P-V 로 평면도 판정 | 평면도가 항상 불합격 | 칸 평균 후 P-V (D5-4) |
| 검증 후 렌즈를 만짐 | 이후 데이터 전체가 무효 | 잠금 + 일일 점검. 만졌으면 새 ID 로 재교정 |
| 측정 메타데이터에 캘리브레이션 ID 누락 | 어떤 보정으로 계산했는지 추적 불가 | F3 JSON 의 `calibration_id` 필수 항목화 |
| 이력 파일 덮어쓰기 | 과거 검증 결과 유실 | 추가(append) 전용, Git 으로 관리, 3-2-1 백업 |
| 합격 기준 근처 값을 반복 측정해 좋은 값만 보고 | 신뢰성 훼손 | 모든 반복을 기록하고 평균으로 판정 |

---

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| M2 불통과 (센서 정밀도 부족) | 중 | 높음 | W10 에 조기 판정 → 배율·각도 재설계 또는 목표 오차 재정의 (K4) |
| 무광 코팅 두께 불균일 | 중 | 중 | 같은 번 코팅, 두께 실측, 불확도에 반영 (E1) |
| 게이지 블록·인증 구 확보 지연 | 중 | 높음 | W5 까지 확보. 공동기기원·협력 연구실 대여 검토 |
| 온도 변동 (난방·햇빛) | 중 | 중 | 0.1 °C 기록, ±1 °C 이내에서 검증 (C6) |
| 검증 스크립트 자체의 버그 | 낮음 | 높음 | 합성 데이터(숨은 오차를 아는 데이터)로 먼저 확인 — 6.1 이 그 역할 (J3) |
| 이력 관리 소홀로 ID 혼동 | 중 | 중 | 폴더 = ID, 측정 메타데이터 필수 항목, 주간 점검 |

---

## 10. 기록 양식

`config/calibration/calibration_history.csv` (누적, 수정 금지)

```csv
calibration_id,verified_at,operator,room_temp_C,overall_pass,max_step_err_um,flatness_um,notes
CAL-2026-12-08-A,2026-12-10,student_A,22.4,True,2.8,1.49,합성 데이터 시연
```

`config/verification_layout.yaml` (기준물 배치·인증값)

```yaml
grid_mm: 0.02
edge_band_mm: 0.3
criteria: {step_um: 10, flatness_um: 10, sphere_diam_um: 15, length_pct: 0.1}
step_scan:
  file: step.npy
  base_rois_mm:                     # [x0, x1, y0, y1] 정반 영역 (그림자 제외)
    - [0, 20, 0, 3]
    - [0, 20, 12.58, 16]
  blocks:
    - {name: "1 mm", roi_mm: [0, 20, 3, 12], nominal_mm: 1.0, cert_dev_um: null, serial: ""}
    - {name: "2 mm", roi_mm: [0, 20, 16, 25], nominal_mm: 2.0, cert_dev_um: null, serial: ""}
flatness: {file: flat.npy, roi_mm: [0, 20, 0, 30], cell_mm: 0.5}
length:
  - {axis: x, file: len_x.npy, nominal_mm: 15.0, height_mm: 9.0, band_mm: [5, 15], cert_dev_um: null}
  - {axis: y, file: len_y.npy, nominal_mm: 30.0, height_mm: 9.0, band_mm: [5, 15], cert_dev_um: null}
sphere: {file: sphere.npy, cert_diameter_mm: 6.000}
coating: {used: false, thickness_um: null, method: ""}
temperature: {room_C: null, gauge_block_C: null}
```

검증 1회 기록지 (회차별)

| 날짜 | 캘리브레이션 ID | 회차 | 단차 1 | 단차 2 | 단차 5 | 단차 10 | 평면도 | 길이 X | 길이 Y | 구 지름 | 실내 °C | 판정 | 담당 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |

재교정 사유 기록

| 날짜 | 이전 ID | 새 ID | 사유 (렌즈 접촉 / 이동 / 관리도 이탈 / 정기) | 조치 | 담당 |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

---

## 11. 참고 자료

- ISO 3650 *Geometrical product specifications (GPS) — Length standards — Gauge blocks* — 게이지 블록 등급·편차
- ISO 1 *GPS — Standard reference temperature for the specification of geometrical and dimensional properties* — 20 °C 기준 온도
- JCGM 100 (GUM) *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* — I1 불확도 연계
- AIAG *Measurement Systems Analysis (MSA) Reference Manual* — 안정성 관리도, Gage R&R (I2)
- ISO 10360 계열 (좌표측정기 성능 시험) — 구·게이지 블록을 이용한 길이 측정 오차 시험 개념
- Shewhart 관리도 (평균 ± 3σ) — 통계적 공정 관리 교과서 주제
- 상위 기준: [BLUEPRINT.md D5, I1, I2, K1](../../BLUEPRINT.md)
