# H4. 정합 (Registration) — 좌표계 맞추기

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: H. 처리·분석

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-15 ~ 2026-12-28 (W11-12) |
| 우선순위 | **긴급** |
| 트랙 | 소프트웨어 |
| 선행 요소 | [H3 바닥 평면 기준화](H3-bed-leveling.md), [C3 지그·기준 마커](../C-mechanics/C3-fiducials.md), [C4 좌표계 체계](../C-mechanics/C4-coordinate-frames.md), [D4 센서↔G코드 좌표](../D-calibration/D4-sensor-to-gcode.md), [G3 마스크·기준 높이맵](../G-reference/G3-mask-heightmap.md), [H1 격자 변환](H1-gridding.md) |
| 후행 요소 | [H5 높이 지표](H5-height-metrics.md), [H6 윤곽 지표](H6-contour-metrics.md), [H7 치수·형상 지표](H7-dimensional-metrics.md), [J3 합성 데이터 테스트](../J-software/J3-synthetic-tests.md), [I1 측정 불확도](../I-reliability/I1-uncertainty.md) (정합 불확도 항목) |
| 관련 마일스톤 | **M3**: 합성 데이터에서 변형을 허용오차 내 복원 (W11-12) |

---

## 1. 목적

측정 데이터({M})를 G코드 좌표({G})로 옮기고, 남은 차이를 **위치 오차 · 배율(수축) 오차 · 형상 오차**로 **나누어** 보고합니다.

| 단계 | 방법 | 결과 |
|---|---|---|
| 방법 1: 절대 위치 기준 | 기준 마커(구) 중심 → Kabsch 강체 정합 | `T_G_M`, 정합 잔차 FRE |
| 방법 2: 최적 맞춤 | 측정 형상을 설계 형상에 최대한 겹침 | 남은 이동·회전 = **위치 오차** (ΔX, ΔY, Δyaw) |
| 닮음 맞춤 | 이동 + 회전 + **배율** | **배율(수축) 오차** (%) |
| 형상 | 방법 2 정합 뒤에 남는 차이 | H5·H6·H7 지표의 입력 |

이 요소의 가장 중요한 규칙 두 가지 (청사진 H4):
1. **최적 맞춤(ICP 등) 결과만으로 오차를 보고하지 않는다** → 위치 오차가 0 으로 사라집니다.
2. **형상 비교용 정합에 배율을 허용하지 않는다** → 수축 오차가 사라집니다. 배율은 **따로 추정해서 결과로 보고**합니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 변환의 종류와 자유도
| 변환 | 2D 자유도 | 바뀌는 것 | 이 과제에서 |
|---|---|---|---|
| 이동 | 2 (tx, ty) | 위치 | |
| **강체(rigid, Euclidean)** | 3 (tx, ty, yaw) | 위치 + 방향 | **기본 정합** |
| **닮음(similarity)** | 4 (+ 배율 s) | + 크기 | **배율 추정 전용** |
| 아핀(affine) | 6 | + 기울어짐(전단) | 쓰지 않음 (오차를 흡수함) |

H3 에서 Z 와 기울기(2개)를 이미 맞췄으므로 남은 자유도는 **X, Y, yaw 3개**입니다. 자유도를 더 허용하면 그만큼의 오차가 "정합"이라는 이름으로 사라집니다.

### 2.2 변환 행렬 이름 규칙 (C4)
`T_G_M` = "M 좌표의 점을 G 좌표로 바꾸는 변환". 점 하나에 대해 `p_G = R·p_M + t` 입니다. 이름의 오른쪽 글자(M)가 입력, 왼쪽(G)이 출력입니다.

### 2.3 기준 마커 = 구 (C3)
구는 어느 방향에서 봐도 중심이 같아서, **윗부분만 보여도 중심을 계산**할 수 있습니다.
- 잔차: `‖p − c‖ − R` (점에서 중심까지 거리 − 반지름)
- **반지름 R 을 알려진 값으로 고정**하고 중심 c(3개 값)만 찾습니다 (`scipy.optimize.least_squares`).
- 이유: 윗부분(극각 30° 이내)만 보이면 "작은 구가 낮게" 있는 것과 "큰 구가 높게" 있는 것이 거의 구분되지 않습니다. 반지름을 같이 추정하면 **중심 Z 가 크게 흔들립니다** (6.2 데모: 표준편차 3.0 µm → 고정 시 0.12 µm).
- 반지름을 잘못 넣으면 중심 Z 가 그만큼 치우치지만 **X, Y 는 거의 영향이 없습니다** (6.2 데모: +10 µm 오입력 → Z −10.7 µm, XY 변화 없음). 그래도 인증서의 지름을 씁니다.

### 2.4 Kabsch 알고리즘 — 대응점으로 회전·이동 구하기 (Kabsch, 1976)
마커 중심 4개를 {M} 에서 측정했고({A}), {G} 에서의 위치({B})를 압니다(C3 좌표 교정). `B ≈ R·A + t` 를 최소제곱으로 푸는 방법:
1. 두 점 집합의 **무게중심**을 각각 빼서 원점에 모은다.
2. 공분산 행렬 `Σ (a_i)(b_i)ᵀ` 을 만든다.
3. SVD 로 분해해서 회전 `R = V·D·Uᵀ` 를 얻는다. `D` 는 **거울 반전(행렬식 −1)을 막는 보정**.
4. `t = b̄ − R·ā`.
배율까지 구하는 확장이 **Umeyama (1991)** 방법입니다 (`kabsch(..., with_scale=True)`).

### 2.5 FRE 와 TRE — "마커가 잘 맞았다" ≠ "시편이 잘 맞았다"
- **FRE (Fiducial Registration Error)**: 정합 후 마커 중심끼리의 거리 RMS. 청사진 기준 **수 µm ~ 10 µm**.
- **TRE (Target Registration Error)**: 관심 대상(시편) 위치에서의 실제 오차. 직접 알 수 없습니다.
- 마커가 적으면 FRE 가 작아도 TRE 는 클 수 있습니다 (마커 4개면 정합이 마커에 "맞춰져" FRE 가 작게 나옴). 그래서 **하나 빼고 정합한 뒤 뺀 마커를 예측하는 LOO(leave-one-out) 오차**를 TRE 의 현실적인 추정으로 함께 보고합니다.
- 마커 배치 원칙(Fitzpatrick 등, 1998): **시편을 둘러싸도록 넓게**, 일직선이 아니게. 시편이 마커들의 무게중심에 가까울수록 TRE 가 작습니다.

### 2.6 최적 맞춤(방법 2)의 세 가지 구현
| 구현 | 원리 | 장점 | 주의 |
|---|---|---|---|
| **A. 윤곽 ↔ 설계 경계 최소제곱 (권장)** | 측정 높이맵의 등고선(서브픽셀) 점들과 G3 설계 다각형 경계 사이 거리 제곱합 최소화 (`least_squares`, 강건 손실 `soft_l1`) | 격자 양자화가 없고, 배율도 같은 틀에서 추정 | 국부 결함이 넓으면 결함 쪽으로 끌림 |
| B. OpenCV ECC | `cv2.findTransformECC(MOTION_EUCLIDEAN)` 로 영상 상관 최대화 | 빠르고 간단 | **이진 마스크**로 하면 ±반 칸(±10 µm @0.02 mm) 모호함. **면적비율 마스크**를 써야 서브픽셀 |
| C. ICP (Besl & McKay, 1992) | 가장 가까운 점 짝짓기 ↔ 강체 변환 반복 | 3D 점군에 일반적 | (선택) Open3D `registration_icp`. 이 문서 코드는 Open3D 없이 동작 |

> 이진 마스크 함정: 설계 경계가 격자 칸 중심 위에 정확히 걸리면, 반 칸 안에서 어디로 옮겨도 이진 마스크가 똑같아서 ECC 가 반 칸(25 µm @0.05 mm) 틀린 답에서 멈춥니다. 이 문서 작성 중 실제로 확인한 현상이며, 그래서 `fractional_mask()`(칸을 덮는 면적 비율 0~1)를 씁니다.

### 2.7 위치 오차는 "어느 점에서" 잰 것인가
회전은 원점을 중심으로 돌기 때문에, 원점에서 25 mm 떨어진 부품은 0.5° 회전만으로도 약 220 µm 이동한 것처럼 보입니다. 그래서 위치 오차는 **부품 기준점 c (예: 부품 설계 중심)에서의 이동량 (dx, dy)** 과 회전 yaw 로 보고합니다 (`pose_at`).
모델: `측정 = s·R(yaw)·(설계 − c) + c + (dx, dy)`.

### 2.8 데이텀(datum) 형상 — 위치·배율은 "핀 중심"으로
넓은 벽의 과충진 같은 **형상 결함은 최적 맞춤을 끌어당겨** 위치 오차에 섞입니다 (6.3 데모: 80 µm 결함 → 윤곽 강체 맞춤 dx 가 31 µm 틀어짐). 반면 **핀·구멍의 중심**은 둘레 전체의 평균이라 한쪽 결함에 덜 민감합니다. 그래서:
- **위치·배율 보고값 = 데이텀 형상(핀 격자, E3)의 중심들에 닮음 변환** (권장)
- 윤곽 최적 맞춤 = 형상 지표용 정렬 + 교차 확인
- 두 값의 차이가 15 µm 를 넘으면 형상 결함이 정합에 새어 들어간 것으로 보고 원인을 기록합니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 내용 |
|---|---|---|---|
| 입력 | `points_Mlevel.npz` | npz | H3 수평화 점군 |
| 입력 | `config/fiducials_G_<버전>.yaml` | YAML | 마커 ID 별 {G} 좌표 (C3 좌표 교정 결과, 버전 ID 포함) |
| 입력 | `config/default.yaml` → `registration.fiducial_radius_mm` | YAML | 4.0 (인증서 값으로 교체) |
| 입력 | G3 산출물: 층별 다각형(`*.wkt` 또는 pickle), `_grid_G.json`, 기준 높이맵 | — | 설계 경계·격자 |
| 입력 | 데이텀 형상 목록 (E3) | CSV | 핀/구멍 ID, 설계 중심 (x, y), 지름 |
| 산출 | `<scan_id>_T_G_M.json` | JSON | R(2×2), t, 회전°, 마커별 잔차, **FRE**, **LOO 최대**, 구 맞춤 잔차, 사용 마커 버전 |
| 산출 | `points_G.npz` | npz | {G} 로 옮긴 점군 |
| 산출 | `<scan_id>_heightmap_G.npy` + `_grid_G.json` | float32 | **G3 와 같은 격자**로 다시 격자화한 측정 높이맵 (H5~H7 입력) |
| 산출 | `<scan_id>_H4_pose.csv` | CSV | 방법별 dx, dy [µm], yaw [°], 배율 — 핀 닮음 / 윤곽 닮음 / 윤곽 강체 / ECC |
| 산출 | `<scan_id>_T_best.json` | JSON | 형상 지표용 최적 맞춤 변환 (강체) |
| 산출 | `<scan_id>_H4_report.yaml` | YAML | 10장 양식 |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 마커 종류·개수 | 구 3 / **구 4** / 구 6 | **무광 세라믹 구 4개** | C3 권장. 4개면 LOO 확인 가능 |
| 구 맞춤 | 반지름 자유 / **반지름 고정** | **고정** | 2.3 절, 6.2 데모 |
| 구 맞춤 사용 영역 | 전체 / **수평반경 < 0.75R** | **< 0.75R** | 가파른 옆면은 데이터가 나쁨 (E2) |
| 마커 정합 자유도 | 2D 강체(3) / 3D 강체(6) | **2D 강체** (3D 는 점검용) | H3 이후 남은 자유도 3개. 마커 중심 Z 의 흩어짐은 H3 점검 지표로 기록 |
| 측정 → {G} 옮기는 방식 | 높이맵 회전·보간 / **점군 변환 후 재격자화** | **점군 변환 후 재격자화** | 보간 1회 감소 (H1) |
| 최적 맞춤 구현 | **윤곽 최소제곱** / ECC / ICP | **윤곽 최소제곱 (A)**, ECC 는 교차 확인 | 2.6 절 |
| 강건 손실 | 없음 / **soft_l1 (f_scale 20 µm)** | **soft_l1, 0.02 mm** | 국부 결함 영향 감소 |
| 위치·배율 보고값 | 윤곽 맞춤 / **데이텀 중심 닮음** | **데이텀(핀) 중심 닮음** | 2.8 절. 핀이 없는 시편은 윤곽 닮음 |
| 위치 오차 기준점 c | 원점 / **부품 설계 중심** | **부품 설계 중심** | 2.7 절 |
| 형상 지표용 정렬 | 강체 / 닮음 | **강체** (배율 효과는 형상에 남김) | 청사진 H4: 배율은 숨기지 않고 따로 보고 |
| 등고선 높이 | 판 높이의 50 % / Z − h/2 | 정합용 **50 %**, 형상 지표는 H6 규칙 | 정합은 경계 위치만 필요. 50 % 가 경계 흐림에 가장 덜 민감 |

---

## 5. 수행 절차

1. **좌표·파일 규약 확정 (W11 1일차)**
   - [ ] `T_G_M` JSON 필드(R, t, frame_from="M", frame_to="G", fiducial_version) 확정
   - [ ] C3 담당자에게서 `fiducials_G_<버전>.yaml` 수령, 마커 ID 순서 확인
2. **모듈 구현 (2일)**
   - [ ] 6.1 `h4_registration.py` 를 `src/cvlab/registration.py` 로 이동
   - [ ] `pytest -q test_h4.py` 6개 통과 (Kabsch·Umeyama·픽셀↔mm·부호)
3. **구 맞춤 검증 (0.5일)**
   - [ ] 6.2 데모: 반지름 고정 시 중심 Z 표준편차 < 0.5 µm 확인
   - [ ] 실측: 같은 구 10회 스캔 → 중심 반복성 (x, y, z 표준편차) 기록 → I1 에 전달
4. **합성 데이터 종합 시험 = M3 (2일)**
   - [ ] 6.3 데모(결함 없음)에서 7장 M3 기준 통과 확인
   - [ ] J3 의 변형값(이동 (0.20, −0.10) mm, 회전 0.5°, 배율 0.996)을 그대로 사용
   - [ ] 노이즈 σ 를 5 → 10 → 20 µm 로 올려 어디서 기준을 못 맞추는지 기록 (알고리즘 한계)
   - [ ] 결함 있음 경우도 실행해 방법 간 차이(형상 결함 누설) 크기를 기록
5. **실측 적용 (2일)**
   - [ ] 마커 4개가 함께 찍힌 시편 스캔 → `T_G_M`, FRE, LOO 기록 (FRE ≤ 10 µm 아니면 원인 조사)
   - [ ] 점군을 {G} 로 옮겨 G3 격자로 재격자화 → 기준 마스크와 겹쳐 그려 육안 확인 (L자 방향)
   - [ ] 핀 중심 닮음 / 윤곽 닮음 / 윤곽 강체 / ECC 네 결과를 `_H4_pose.csv` 에 저장
6. **반복성 (1일)**
   - [ ] 같은 시편 3회 스캔(재장착 포함 1회)의 dx, dy, yaw, 배율 표준편차 기록
7. **문서화**
   - [ ] `_H4_report.yaml` 작성, M3 결과를 K1 일정표에 보고

---

## 6. Python 구현

### 6.1 모듈 `h4_registration.py`

```python
"""H4. 정합(registration) 모듈: 구 중심 맞춤, Kabsch/Umeyama, FRE, ECC 최적 맞춤.
최종적으로는 src/cvlab/registration.py 로 옮깁니다. 단위 mm, 내부 각도는 라디안."""
import numpy as np
import cv2
import shapely
import contourpy
from scipy.optimize import least_squares


# ---------- 1. 기준 마커(구) 중심 ----------
def fit_sphere_algebraic(P):
    """선형 구 맞춤 (반지름도 추정). 초깃값 용도."""
    A = np.hstack([2 * P, np.ones((len(P), 1))])
    b = (P ** 2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(sol[3] + c @ c))


def fit_sphere_fixed_radius(P, radius, c0=None):
    """반지름을 알려진 값으로 고정하고 중심만 추정 (기하학적 최소제곱).
    잔차 = (점~중심 거리) − 반지름. 반환: 중심, 잔차 RMS, 중심 표준불확도(추정)"""
    if c0 is None:
        top = P[np.argmax(P[:, 2])]
        c0 = top - [0, 0, radius]                  # 꼭대기 점 바로 아래를 초깃값으로
    fun = lambda c: np.linalg.norm(P - c, axis=1) - radius
    r = least_squares(fun, c0, method="lm")
    res = r.fun
    dof = max(len(P) - 3, 1)
    s2 = (res ** 2).sum() / dof
    cov = s2 * np.linalg.inv(r.jac.T @ r.jac)      # 선형 근사 공분산
    return r.x, float(np.sqrt(np.mean(res ** 2))), np.sqrt(np.diag(cov))


def sphere_cap_points(P, approx_xy, radius, rho_max_frac=0.75):
    """대략 위치 근처에서 구 윗부분 점만 고른다 (수평거리 < 0.75R; 가파른 옆면은 데이터 품질이 나쁨)."""
    near = np.linalg.norm(P[:, :2] - approx_xy, axis=1) < 1.5 * radius
    Q = P[near]
    top = Q[np.argmax(Q[:, 2])]
    keep = np.linalg.norm(Q[:, :2] - top[:2], axis=1) < rho_max_frac * radius
    return Q[keep]


# ---------- 2. 대응점 정합: Kabsch (강체) / Umeyama (닮음) ----------
def kabsch(A, B, with_scale=False):
    """대응점 A, B (N,dim) → B ≈ s·R·A + t.  dim = 2 또는 3.
    with_scale=False: 강체 (Kabsch 1976), True: 닮음 (Umeyama 1991)"""
    A = np.asarray(A, float); B = np.asarray(B, float)
    ca, cb = A.mean(0), B.mean(0)
    A0, B0 = A - ca, B - cb
    U, S, Vt = np.linalg.svd(A0.T @ B0)
    D = np.eye(A.shape[1]); D[-1, -1] = np.sign(np.linalg.det(Vt.T @ U.T))   # 거울 반전 방지
    R = Vt.T @ D @ U.T
    s = (S * np.diag(D)).sum() / (A0 ** 2).sum() if with_scale else 1.0
    t = cb - s * R @ ca
    return R, t, s


def apply(R, t, s, P):
    return s * P @ R.T + t


def fre(A, B, R, t, s=1.0):
    """정합 잔차(FRE): 변환 후 대응점 거리의 RMS, 그리고 점별 거리"""
    d = np.linalg.norm(apply(R, t, s, A) - B, axis=1)
    return float(np.sqrt(np.mean(d ** 2))), d


def leave_one_out(A, B):
    """마커 하나를 빼고 정합 → 뺀 마커의 예측 오차. 실제 목표 오차(TRE)의 현실적 추정치."""
    errs = []
    for i in range(len(A)):
        m = np.arange(len(A)) != i
        R, t, s = kabsch(A[m], B[m])
        errs.append(np.linalg.norm(apply(R, t, s, A[i:i + 1])[0] - B[i]))
    return np.array(errs)


# ---------- 3. 최적 맞춤 (A): 측정 윤곽 ↔ 설계 경계, scipy 최소제곱 [권장] ----------
def contour_points(H, grid, level):
    """높이맵에서 높이 = level 인 등고선을 서브픽셀로 추출 (선형 보간). NaN 칸은 건너뜀. 반환 (N,2) mm"""
    Hm = np.ma.masked_invalid(H)
    lines = contourpy.contour_generator(grid["xs"], grid["ys"], Hm).lines(level)
    return np.vstack(lines) if lines else np.empty((0, 2))


def fit_contour_to_polygon(pts, ref_poly, center, scale=False, f_scale=0.02):
    """측정 윤곽점 pts 를 설계 경계(ref_poly.boundary)에 맞추는 변환을 찾는다.
    모델(설계 → 측정):  m = s·R(yaw)·(x − c) + c + (dx, dy)
      → dx, dy 는 '부품 기준점 c 에서의' 이동량, yaw 는 회전, s 는 배율(scale=True 일 때만)
    loss='soft_l1': 국부 결함(과충진 등)에 끌려가지 않도록 큰 잔차의 영향을 줄인다."""
    c = np.asarray(center, float)
    bd = ref_poly.boundary

    def to_design(p):
        dx, dy, th = p[:3]; s = p[3] if scale else 1.0
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        return ((pts - c - [dx, dy]) @ R) / s + c          # 측정점을 설계 좌표로 되돌림

    fun = lambda p: shapely.distance(shapely.points(to_design(p)), bd)
    p0 = [0, 0, 0, 1.0] if scale else [0, 0, 0]
    r = least_squares(fun, p0, loss="soft_l1", f_scale=f_scale, x_scale=[0.1, 0.1, 0.01] + ([0.001] if scale else []))
    out = {"dx": float(r.x[0]), "dy": float(r.x[1]), "yaw_deg": float(np.degrees(r.x[2])),
           "scale": float(r.x[3]) if scale else 1.0, "rms_um": float(1000 * np.sqrt(np.mean(r.fun ** 2)))}
    return out, to_design(r.x)


def signed_distance_to_polygon(pts, poly):
    """윤곽점 → 다각형 경계까지 거리. 바깥(재료 과다) +, 안쪽(재료 부족) −  (A1 부호 규칙)"""
    P = shapely.points(pts)
    d = shapely.distance(P, poly.boundary)
    return np.where(shapely.contains(poly, P), -d, d)


# ---------- 4. 최적 맞춤 (B): 영상 ECC (OpenCV) [빠른 교차 확인용] ----------
def fractional_mask(poly, grid, ss=5):
    """칸마다 다각형이 덮는 '면적 비율'(0~1). 이진 마스크보다 경계 정보가 풍부해 서브픽셀 정합이 된다."""
    X, Y = np.meshgrid(grid["xs"], grid["ys"])
    acc = np.zeros(X.shape)
    offs = ((np.arange(ss) + 0.5) / ss - 0.5) * grid["res"]
    for ox in offs:
        for oy in offs:
            acc += shapely.contains_xy(poly, X + ox, Y + oy)
    return (acc / ss ** 2).astype(np.float32)


def ecc_euclidean(template, image, n_iter=200, eps=1e-8, gauss=5):
    """cv2.findTransformECC (MOTION_EUCLIDEAN). template(p) ≈ image(W·p) 를 만족하는 W(2×3, 픽셀)."""
    W = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, n_iter, eps)
    cc, W = cv2.findTransformECC(template.astype(np.float32), image.astype(np.float32), W,
                                 cv2.MOTION_EUCLIDEAN, crit, None, gauss)
    return W.astype(float), float(cc)


def pixel_warp_to_mm(W, origin, res):
    """픽셀 좌표(열, 행) 변환 W → mm 좌표 변환 (R, t).  P_mm = origin + res·p_px.
    유도: P' = R·P + (res·t_px + (I − R)·origin)"""
    R = W[:, :2]; t_px = W[:, 2]
    o = np.asarray(origin, float)
    return R, res * t_px + (np.eye(2) - R) @ o


def warp_image(img, W, order="linear"):
    """image 를 template 격자로 되돌려 놓기 (W 의 역방향 적용)."""
    flag = cv2.INTER_LINEAR if order == "linear" else cv2.INTER_NEAREST
    h, w = img.shape
    return cv2.warpAffine(img.astype(np.float32), W.astype(np.float32), (w, h),
                          flags=flag + cv2.WARP_INVERSE_MAP, borderValue=0)


def pose_at(R, t, c, s=1.0):
    """2D 변환 P' = s·R·P + t 를 '점 c 에서의 이동량(dx, dy) + 회전각(°)' 으로 표현.
    회전·배율은 원점 기준이므로, 원점에서 먼 부품은 이동량이 달라 보인다 → 항상 부품 기준점에서 보고"""
    c = np.asarray(c, float)
    dx, dy = s * R @ c + t - c
    return float(dx), float(dy), float(np.degrees(np.arctan2(R[1, 0], R[0, 0])))
```

### 6.2 보조 데모 `demo_h4_sphere.py` — 반지름 고정의 효과

반지름 4 mm 구의 꼭대기 극각 30° 이내(수평 반경 2 mm)만 보이고, 높이 노이즈 5 µm, 점 1,500개를 200번 반복했습니다.

```python
"""H4 보조 데모: 구의 윗부분만 보일 때 '반지름 고정'이 왜 필요한가 (200회 반복 실험)."""
import numpy as np
from h4_registration import fit_sphere_algebraic, fit_sphere_fixed_radius

rng = np.random.default_rng(1)
R, c_true = 4.0, np.array([10.0, 20.0, 4.0])

def cap_points(n=1500, max_polar_deg=30, noise=0.005):
    """구 꼭대기에서 극각 30° 이내(수평 반경 2 mm)만 보이는 점들 + 높이 노이즈"""
    cos_min = np.cos(np.radians(max_polar_deg))
    u = rng.uniform(cos_min, 1, n); phi = rng.uniform(0, 2 * np.pi, n)     # 구면 위 균일 분포
    s = np.sqrt(1 - u ** 2)
    P = c_true + R * np.column_stack([s * np.cos(phi), s * np.sin(phi), u])
    P[:, 2] += rng.normal(0, noise, n)
    return P

err_free, err_fix, r_free, err_wrongR = [], [], [], []
for _ in range(200):
    P = cap_points()
    c1, r1 = fit_sphere_algebraic(P)
    c2, _, _ = fit_sphere_fixed_radius(P, R)
    c3, _, _ = fit_sphere_fixed_radius(P, R + 0.010)          # 반지름을 10 um 틀리게 넣으면?
    err_free.append(c1 - c_true); err_fix.append(c2 - c_true); r_free.append(r1); err_wrongR.append(c3 - c_true)
for name, e in [("반지름 자유", err_free), ("반지름 고정", err_fix), ("반지름 +10um 오입력", err_wrongR)]:
    e = np.array(e) * 1000
    print(f"{name:<14}: 중심 오차 평균 (x,y,z) = ({e[:,0].mean():+.2f}, {e[:,1].mean():+.2f}, {e[:,2].mean():+.2f}) um, "
          f"표준편차 = ({e[:,0].std():.2f}, {e[:,1].std():.2f}, {e[:,2].std():.2f}) um")
print(f"반지름 자유 추정값: {np.mean(r_free):.4f} ± {np.std(r_free):.4f} mm (참 4.0000)")
```

```text
$ python3 demo_h4_sphere.py
반지름 자유        : 중심 오차 평균 (x,y,z) = (+0.04, +0.02, +3.58) um, 표준편차 = (0.46, 0.47, 3.00) um
반지름 고정        : 중심 오차 평균 (x,y,z) = (+0.04, +0.02, -0.01) um, 표준편차 = (0.46, 0.47, 0.12) um
반지름 +10um 오입력 : 중심 오차 평균 (x,y,z) = (+0.03, +0.02, -10.71) um, 표준편차 = (0.46, 0.48, 0.12) um
반지름 자유 추정값: 3.9967 ± 0.0028 mm (참 4.0000)
```

- 반지름을 자유롭게 두면 중심 Z 가 평균 +3.6 µm 치우치고 표준편차 3.0 µm 로 흔들립니다. 고정하면 0.12 µm.
- 반지름을 10 µm 틀리게 넣으면 Z 만 약 10 µm 틀어지고 X, Y 는 변하지 않습니다.

### 6.3 종합 데모 `demo_h4.py` — 위치·배율·형상 분리 (M3 합성 시험)

시나리오 (모든 값은 정답을 알고 만든 것):
- 설계: 24 × 20 mm L자 판(높이 2 mm) + Ø3 핀 4개(높이 4 mm), 마커 구 4개(R = 4 mm)
- 실제 출력: 부품 중심 c = (20, 16) 기준 **배율 0.996, 회전 +0.5°, 이동 (+0.20, −0.10) mm**. 두 번째 경우에는 왼쪽 벽 10 mm 구간에 **80 µm 과충진 결함** 추가
- 센서 좌표 {M}: {G} 를 2° 회전하고 (−3, 4) mm 이동한 좌표 (코드는 모름). 마커의 {G} 좌표는 ±5 µm 불확실(C3 교정 오차 모사)
- 측정: 0.025 mm 간격 점, 노이즈 5 µm → 0.05 mm 격자 (데모 속도용. 실제는 0.02 mm)

같은 폴더에 `h1_gridding.py`, `h4_registration.py` 가 있어야 합니다. 실행 시간 약 10초.

```python
"""H4 데모: 정답을 아는 합성 데이터로 '위치 오차 / 배율 오차 / 형상 오차'를 분리한다.
같은 폴더에 h1_gridding.py, h4_registration.py 가 있어야 한다."""
import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import box, Point
from scipy import ndimage
from h1_gridding import make_grid, grid_points
from h4_registration import (fit_sphere_fixed_radius, sphere_cap_points, kabsch, apply, fre,
                             leave_one_out, contour_points, fit_contour_to_polygon,
                             signed_distance_to_polygon, fractional_mask, ecc_euclidean,
                             pixel_warp_to_mm, pose_at)

R_BALL, NOISE, RES = 4.0, 0.005, 0.05           # 마커 반지름 4 mm, 센서 노이즈 5 um, 격자 0.05 mm(데모 속도용)
TRUE = {"dx": 0.20, "dy": -0.10, "yaw_deg": 0.5, "scale": 0.996}   # 정답 (J3 합성 테스트 값)

# ---- 설계(G코드) 좌표 {G} ----
markers_G = np.array([[-5, -5, 4.0], [45, -5, 4.0], [45, 35, 4.0], [-5, 30, 4.0]])   # 일직선이 아님
base_G = box(8, 6, 32, 26).difference(box(26, 20, 32.1, 26.1))      # L자 판 (축 방향 확인용)
pins_G = np.array([[12, 10], [28, 10], [12, 22], [20, 22]], float)  # Ø3 핀 4개 (데이텀 형상)
c_part = np.array([20.0, 16.0])                                     # 위치 오차를 표현할 부품 기준점
# ---- 센서 좌표 {M} = G 를 2° 회전 + (−3, 4) mm 이동 (코드는 이 값을 모른다) ----
th = np.radians(2.0)
R_MG = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]); t_MG = np.array([-3.0, 4.0])


def run(with_defect, seed=2026):
    rng = np.random.default_rng(seed)
    # C3 좌표 교정으로 '알고 있는' 마커 위치는 참값과 ±5 um 정도 다르다 (현실적인 FRE)
    markers_known = markers_G.copy(); markers_known[:, :2] += rng.normal(0, 0.005, (4, 2))

    # ---- 실제 출력 = 설계 + 위치 오차 + 배율 오차 (+ 형상 결함) ----
    def printed(geom):
        g = affinity.scale(geom, TRUE["scale"], TRUE["scale"], origin=tuple(c_part))
        g = affinity.rotate(g, TRUE["yaw_deg"], origin=tuple(c_part))
        return affinity.translate(g, TRUE["dx"], TRUE["dy"])
    defect = box(7.92, 10, 8.0, 20)                                   # 왼쪽 벽 10 mm 구간 80 um 과충진
    base_P = printed(base_G.union(defect) if with_defect else base_G)
    pins_P = [printed(Point(p).buffer(1.5, quad_segs=64)) for p in pins_G]

    def true_height_G(x, y):
        z = np.where(shapely.contains_xy(base_P, x, y), 2.0, 0.0)        # 판 높이 2 mm
        for pin in pins_P:
            z = np.where(shapely.contains_xy(pin, x, y), 4.0, z)        # 핀 높이 4 mm
        for m in markers_G:                                             # 마커 구 윗면
            rho2 = (x - m[0]) ** 2 + (y - m[1]) ** 2
            z = np.where(rho2 < R_BALL ** 2, m[2] + np.sqrt(np.clip(R_BALL ** 2 - rho2, 0, None)), z)
        return z

    def scan(xmin, xmax, ymin, ymax, step=0.025):
        """{M} 의 규칙 위치에서 측정한 (N,3) 점 (높이는 G 로 되돌려 계산 + 노이즈)"""
        gx, gy = np.meshgrid(np.arange(xmin, xmax, step), np.arange(ymin, ymax, step))
        PM = np.column_stack([gx.ravel(), gy.ravel()])
        PG = (PM - t_MG) @ R_MG
        return np.column_stack([PM, true_height_G(PG[:, 0], PG[:, 1]) + rng.normal(0, NOISE, len(PM))])

    # ===== 1단계 (방법 1): 마커 구 중심 → T_G_M =====
    cent_M = []
    for mx, my in markers_G[:, :2] @ R_MG.T + t_MG:                    # 대략 위치 (화면에서 찍어도 됨)
        cap = sphere_cap_points(scan(mx - 5, mx + 5, my - 5, my + 5), np.array([mx, my]), R_BALL)
        c_fix, rms, _ = fit_sphere_fixed_radius(cap, R_BALL)
        cent_M.append(c_fix)
    cent_M = np.array(cent_M)
    R2, t2, _ = kabsch(cent_M[:, :2], markers_known[:, :2])           # M → G 강체 (x, y, yaw)
    fre_rms, _ = fre(cent_M[:, :2], markers_known[:, :2], R2, t2)
    loo = leave_one_out(cent_M[:, :2], markers_known[:, :2])
    print(f"[1] 마커: 구 잔차 RMS {rms*1000:.2f} um, T_G_M 회전 {np.degrees(np.arctan2(R2[1, 0], R2[0, 0])):+.4f}°"
          f" (참 -2.0000°), FRE {fre_rms*1000:.2f} um, LOO 최대 {loo.max()*1000:.2f} um")

    # ===== 2단계: 점군을 G 로 옮긴 뒤 G 격자(G3 과 같은 격자)에서 다시 격자화 =====
    grid = make_grid(5.0, 35.0, 3.0, 29.0, RES)
    cm = np.array([[5, 3], [35, 3], [35, 29], [5, 29]]) @ R_MG.T + t_MG
    P = scan(cm[:, 0].min(), cm[:, 0].max(), cm[:, 1].min(), cm[:, 1].max())
    PG = np.column_stack([apply(R2, t2, 1.0, P[:, :2]), P[:, 2]])
    H, _, _ = grid_points(*PG.T, grid)
    X, Y = np.meshgrid(grid["xs"], grid["ys"])

    # ===== 3단계 (방법 2): 남은 위치·배율 오차를 네 가지로 추정 =====
    rows = []
    lab, n = ndimage.label(np.nan_to_num(H) > 3.0)                      # (a) 데이텀: 핀 중심 + Umeyama 닮음
    pm = np.array([[X[lab == i].mean(), Y[lab == i].mean()] for i in range(1, n + 1)])
    pm = pm[[np.argmin(np.linalg.norm(pm - p, axis=1)) for p in pins_G]]
    Rs, ts, s = kabsch(pins_G, pm, with_scale=True)
    rows.append(("핀 4개 닮음 (권장)", *pose_at(Rs, ts, c_part, s), s))
    pts = contour_points(H, grid, level=1.0)                            # (b),(c) 윤곽 ↔ 설계 경계
    pts = pts[shapely.distance(shapely.points(pts), base_G.boundary) < 1.0]
    si, pts_si = fit_contour_to_polygon(pts, base_G, c_part, scale=True)
    eu, pts_eu = fit_contour_to_polygon(pts, base_G, c_part, scale=False)
    rows.append(("윤곽 닮음 맞춤", si["dx"], si["dy"], si["yaw_deg"], si["scale"]))
    rows.append(("윤곽 강체 맞춤", eu["dx"], eu["dy"], eu["yaw_deg"], 1.0))
    A_ref = fractional_mask(base_G, grid)                               # (d) OpenCV ECC (강체)
    B = np.clip(np.nan_to_num(H) / 2.0, 0, 1).astype(np.float32); B[np.nan_to_num(H) > 3.0] = 1.0
    W, _ = ecc_euclidean(A_ref, B)
    Rb, tb = pixel_warp_to_mm(W, (grid["xs"][0], grid["ys"][0]), RES)
    rows.append(("ECC 강체 맞춤", *pose_at(Rb, tb, c_part), 1.0))
    print(f"    {'방법':<14} {'dx[um]':>8} {'dy[um]':>8} {'yaw[°]':>8} {'배율':>8}")
    for name, dx, dy, yaw, sc in rows:
        print(f"    {name:<14} {dx*1000:+8.1f} {dy*1000:+8.1f} {yaw:+8.4f} {sc:8.5f}")
    print(f"    {'정답':<14} {TRUE['dx']*1000:+8.1f} {TRUE['dy']*1000:+8.1f} {TRUE['yaw_deg']:+8.4f} {TRUE['scale']:8.5f}")

    # ===== 4단계: 형상 오차 = 최적 맞춤 후 남는 윤곽 거리 (+ 바깥 = 재료 과다) =====
    left = lambda q: (q[:, 0] < 9) & (q[:, 1] > 10.5) & (q[:, 1] < 19.5)
    d_eu = signed_distance_to_polygon(pts_eu, base_G)
    d_si = signed_distance_to_polygon(pts_si, base_G)
    print(f"[4] 강체 맞춤 후 |d| P95 {np.percentile(abs(d_eu), 95)*1000:.1f} um (배율 효과 포함), "
          f"닮음 맞춤 후 |d| P95 {np.percentile(abs(d_si), 95)*1000:.1f} um, "
          f"왼쪽 벽 평균(닮음 후) {d_si[left(pts_si)].mean()*1000:+.1f} um")
    d_raw = signed_distance_to_polygon(pts, base_G)
    print(f"[함정] 최적 맞춤 없이 형상 지표를 보면 |d| P95 {np.percentile(abs(d_raw), 95)*1000:.1f} um "
          f"(위치 오차가 형상 오차로 섞임)")


for flag in (False, True):
    print("=== 형상 결함", "있음 (왼쪽 벽 80 um 과충진) ===" if flag else "없음 (J3 정답 확인용) ===")
    run(with_defect=flag)
```

```text
$ python3 demo_h4.py
=== 형상 결함 없음 (J3 정답 확인용) ===
[1] 마커: 구 잔차 RMS 4.23 um, T_G_M 회전 -2.0033° (참 -2.0000°), FRE 5.24 um, LOO 최대 11.55 um
    방법               dx[um]   dy[um]   yaw[°]       배율
    핀 4개 닮음 (권장)     +199.5    -97.7  +0.4976  0.99631
    윤곽 닮음 맞춤         +196.9    -98.1  +0.4955  0.99598
    윤곽 강체 맞춤         +201.5    -91.1  +0.4969  1.00000
    ECC 강체 맞춤        +200.8    -94.9  +0.5009  1.00000
    정답               +200.0   -100.0  +0.5000  0.99600
[4] 강체 맞춤 후 |d| P95 63.0 um (배율 효과 포함), 닮음 맞춤 후 |d| P95 19.8 um, 왼쪽 벽 평균(닮음 후) -0.4 um
[함정] 최적 맞춤 없이 형상 지표를 보면 |d| P95 299.8 um (위치 오차가 형상 오차로 섞임)
=== 형상 결함 있음 (왼쪽 벽 80 um 과충진) ===
[1] 마커: 구 잔차 RMS 4.23 um, T_G_M 회전 -2.0033° (참 -2.0000°), FRE 5.24 um, LOO 최대 11.55 um
    방법               dx[um]   dy[um]   yaw[°]       배율
    핀 4개 닮음 (권장)     +199.5    -97.7  +0.4976  0.99631
    윤곽 닮음 맞춤         +185.9    -97.7  +0.4875  0.99653
    윤곽 강체 맞춤         +168.9    -90.2  +0.4508  1.00000
    ECC 강체 맞춤        +179.8    -95.0  +0.4874  1.00000
    정답               +200.0   -100.0  +0.5000  0.99600
[4] 강체 맞춤 후 |d| P95 77.8 um (배율 효과 포함), 닮음 맞춤 후 |d| P95 64.0 um, 왼쪽 벽 평균(닮음 후) +61.5 um
[함정] 최적 맞춤 없이 형상 지표를 보면 |d| P95 249.7 um (위치 오차가 형상 오차로 섞임)
```

**결과 읽는 법**
- **[1] 마커 정합**: FRE 5.2 µm 는 마커 좌표에 넣은 ±5 µm 불확실성과 같은 크기입니다. LOO 최대 11.6 µm 가 TRE 의 현실적인 상한 추정입니다.
- **결함 없음 (M3 판정용)**: 핀 닮음 (−0.5, +2.3) µm, yaw −0.002°, 배율 +3.1 × 10⁻⁴ / 윤곽 닮음 (−3.1, +1.9) µm, yaw −0.005°, 배율 −2 × 10⁻⁵ → 모두 7장 M3 기준 안입니다.
- **윤곽 강체 맞춤의 dy −91.1 µm**: 강체 맞춤은 배율을 모르므로, 0.4 % 수축이 L자의 비대칭 모양과 섞여 이동량이 약 9 µm 달라졌습니다. **배율이 있는 시편에서 "위치 오차"는 닮음 맞춤 또는 데이텀으로 구해야** 하는 이유입니다.
- **결함 있음**: 핀 결과는 그대로이지만(핀은 벽 결함을 보지 않음), 윤곽 닮음은 dx −14 µm, 윤곽 강체는 −31 µm, ECC 는 −26 µm 만큼 결함 쪽으로 끌렸습니다 → 2.8 절의 "데이텀 우선" 근거.
- **[4] 형상**: 결함이 없을 때 닮음 맞춤 후 \|d\| P95 = 19.8 µm 는 0.05 mm 격자의 등고선 양자화 수준입니다. 강체 맞춤 후 63 µm 는 수축(배율) 효과가 형상에 남은 것이며, 이것이 청사진이 말하는 "배율을 숨기지 않은" 형상 오차입니다. 결함이 있으면 왼쪽 벽 평균이 +61.5 µm 로 나타납니다(참 +80 µm 중 일부는 맞춤이 끌려가며 흡수).
- **[함정]**: 최적 맞춤 없이 형상 지표를 계산하면 \|d\| P95 가 250~300 µm 로, 위치 오차(≈ 220 µm)가 형상 오차처럼 보입니다.

### 6.4 단위 테스트 `test_h4.py`

```python
"""H4 단위 테스트 (J3 '정합' 항목). 실행: pytest -q test_h4.py"""
import numpy as np
from shapely.geometry import box
from h4_registration import kabsch, apply, fre, pixel_warp_to_mm, pose_at, signed_distance_to_polygon


def rot(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])


def test_Kabsch_2D_강체_복원():
    A = np.array([[0, 0], [50, 0], [50, 40], [0, 35]], float)
    B = A @ rot(0.7).T + [0.3, -0.2]
    R, t, s = kabsch(A, B)
    assert np.allclose(R, rot(0.7)) and np.allclose(t, [0.3, -0.2]) and s == 1.0
    assert fre(A, B, R, t)[0] < 1e-9


def test_Umeyama_배율_복원():
    A = np.random.default_rng(0).uniform(0, 40, (6, 2))
    B = 0.996 * A @ rot(-1.0).T + [1.0, 2.0]
    R, t, s = kabsch(A, B, with_scale=True)
    assert abs(s - 0.996) < 1e-12


def test_Kabsch_3D_거울반전_방지():
    A = np.random.default_rng(1).normal(size=(5, 3))
    R, t, _ = kabsch(A, A)
    assert np.isclose(np.linalg.det(R), 1.0)


def test_픽셀변환_mm변환_일치():
    origin, res = np.array([5.0, 3.0]), 0.05
    R_true, t_true = rot(0.5), np.array([0.2, -0.1])
    # mm 변환 → 픽셀 변환으로 바꾼 뒤 다시 mm 로 되돌리면 같아야 함
    t_px = (t_true - (np.eye(2) - R_true) @ origin) / res
    R, t = pixel_warp_to_mm(np.hstack([R_true, t_px[:, None]]), origin, res)
    assert np.allclose(R, R_true) and np.allclose(t, t_true)


def test_기준점에서의_이동량():
    dx, dy, yaw = pose_at(rot(90), np.zeros(2), [1.0, 0.0])
    assert np.allclose([dx, dy, yaw], [-1.0, 1.0, 90.0])


def test_부호규칙_바깥은_플러스():
    sq = box(0, 0, 10, 10)
    d = signed_distance_to_polygon(np.array([[10.05, 5.0], [9.9, 5.0]]), sq)
    assert np.allclose(d, [0.05, -0.1])
```

```text
$ python3 -m pytest -q test_h4.py
6 passed in 0.xxs
```

---

## 7. 검증 방법과 완료 기준

### 7.1 M3 합격 기준 (합성 데이터, 결함 없음, 노이즈 5 µm)

| 항목 | 기준 | 데모 결과 (핀 닮음 / 윤곽 닮음) |
|---|---|---|
| 구 중심 (반지름 고정) | 중심 오차 ≤ 1 µm (x, y, z) | 0.04 / 0.02 / 0.01 µm (평균), 표준편차 ≤ 0.5 µm |
| T_G_M 회전 | 오차 ≤ 0.01° | 0.0033° |
| FRE | ≤ 10 µm | 5.2 µm |
| LOO 최대 | ≤ 15 µm | 11.6 µm |
| 위치 dx, dy (기준점 c) | 각 \|오차\| ≤ 10 µm | (−0.5, +2.3) / (−3.1, +1.9) µm |
| yaw | \|오차\| ≤ 0.01° | −0.0024° / −0.0045° |
| 배율 | \|오차\| ≤ 5 × 10⁻⁴ (0.05 %) | +3.1 × 10⁻⁴ / −0.2 × 10⁻⁴ |
| 방법 간 일치 | 핀 닮음 vs 윤곽 닮음 위치 차이 ≤ 15 µm | 2.6 µm |

### 7.2 실측 기준

| 항목 | 방법 | 기준 |
|---|---|---|
| FRE | 매 스캔 | ≤ 10 µm (초과 시 마커 오염·구 맞춤·C3 교정 확인) |
| 마커 중심 Z 흩어짐 | 4개 중심 Z 표준편차 | ≤ 10 µm (크면 H3 수평화 또는 마커 높이 불균일) |
| 정합 반복성 | 같은 시편 3회 (재장착 1회 포함) | dx, dy 표준편차 ≤ 5 µm, yaw ≤ 0.005°, 배율 ≤ 2 × 10⁻⁴ |
| 축 방향 | L자 시편 겹쳐 그리기 | 육안으로 뒤집힘·뒤바뀜 없음 |
| 단위 테스트 | `pytest test_h4.py` | 전부 통과 |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| ICP·ECC 결과만으로 오차 보고 | 위치 오차가 늘 0 근처 | 마커 정합(방법 1) 후 최적 맞춤 변환량을 위치 오차로 보고 |
| 형상 정합에 배율 허용 | 수축이 사라져 형상 오차가 작게 보임 | 형상용은 강체, 배율은 따로 보고 |
| 회전을 원점 기준으로 보고 | 작은 회전인데 이동이 수백 µm 로 보임 | `pose_at(…, c)` 로 부품 기준점에서 보고 |
| `R` 의 방향(M→G / G→M) 혼동 | 정합 후 오차가 두 배로 커짐 | 이름 규칙 `T_G_M`, 마커 중심에 적용해 FRE 로 확인 |
| Kabsch 에서 행렬식 보정 누락 | 드물게 거울상 회전(좌우 반전) | `D` 보정 포함 (`test_Kabsch_3D_거울반전_방지`) |
| 구 반지름을 자유 추정 | 마커 Z 가 수 µm 씩 흔들려 H3 점검 실패 | 반지름 고정, 인증 지름 사용 |
| 반짝이는 강구 사용 | 구 맞춤 잔차 RMS 가 수십 µm | 무광 세라믹 구 (C3) |
| 이진 마스크로 ECC | ±반 칸 치우침, 결과가 격자에 따라 바뀜 | 면적비율 마스크 또는 윤곽 최소제곱 |
| 높이맵을 회전·보간해서 {G} 로 | 경계가 뭉개져 H6 지표 악화 | 점군 변환 후 G3 격자로 재격자화 |
| 마커를 시편 한쪽에만 배치 | FRE 는 작은데 시편 반대편 TRE 가 큼 | 시편을 둘러싸게 배치, LOO 확인 |
| 픽셀 ↔ mm 변환 시 원점 처리 누락 | 회전이 있을 때만 이동량이 틀림 | `pixel_warp_to_mm` 의 `(I − R)·origin` 항 (`test_픽셀변환_mm변환_일치`) |

---

## 9. 위험 요소

- **G코드 ↔ 마커 좌표 관계 불확실 (청사진 K4)**: C3 좌표 교정판의 정확도가 곧 위치 오차 측정의 하한입니다. 교정판 원기둥 중심 25개 평균으로 마커 좌표를 구하고, 그 불확도를 I1 의 "정합" 항목에 넣습니다.
- **마커 이동**: 마커가 지그에서 µm 단위로 움직이면 모든 위치 오차가 같이 틀어집니다. 매 세션 기준 시편(I2 안정성)의 위치 오차를 관리도로 봅니다.
- **형상 결함의 누설**: 2.8 절. 데이텀이 없는 시편에서는 위치 오차에 "형상 결함 영향 가능" 주석을 답니다.
- **큰 초기 오차**: 윤곽 최소제곱·ECC 는 초깃값이 실제와 수백 µm 이내일 때 수렴합니다. 마커 정합을 먼저 하므로 보통 문제없지만, 마커 정합이 실패하면 최적 맞춤도 엉뚱한 답을 낼 수 있습니다. 수렴 후 IoU 가 0.95 미만이면 경고합니다.
- **2.5D 한계**: 정합은 위에서 본 경계만 씁니다. 벽이 기울어진 형상은 등고선 높이에 따라 경계가 달라집니다(H6 민감도).

---

## 10. 기록 양식

`results/<scan_id>/<scan_id>_H4_report.yaml`
```yaml
scan_id: S03_r02
fiducial_version: FID-2026-12-20-A
fiducial_radius_mm: 4.0
sphere_fit:
  - {id: F1, n_points: , rms_um: , center_M: [ , , ]}
  - {id: F2, n_points: , rms_um: , center_M: [ , , ]}
  - {id: F3, n_points: , rms_um: , center_M: [ , , ]}
  - {id: F4, n_points: , rms_um: , center_M: [ , , ]}
T_G_M: {R: [[ , ], [ , ]], t_mm: [ , ], yaw_deg: }
fre_um:
loo_max_um:
marker_z_std_um:
reference_point_c_mm: [20.0, 16.0]
pose:                                  # 단위 dx, dy um / yaw deg
  datum_similarity: {dx: , dy: , yaw: , scale: }
  contour_similarity: {dx: , dy: , yaw: , scale: }
  contour_rigid: {dx: , dy: , yaw: }
  ecc_rigid: {dx: , dy: , yaw: , cc: }
reported_position: datum_similarity
reported_scale: datum_similarity
method_disagreement_um:                # 핀 vs 윤곽 닮음 위치 차이
form_alignment: contour_rigid
notes: ""
```

`_H4_pose.csv` 열 구성
```text
scan_id,method,dx_um,dy_um,yaw_deg,scale,rms_um,n_points
```

---

## 11. 참고 자료

- Kabsch, W. (1976). A solution for the best rotation to relate two sets of vectors. *Acta Crystallographica A*, 32.
- Arun, K. S., Huang, T. S., & Blostein, S. D. (1987). Least-squares fitting of two 3-D point sets. *IEEE TPAMI*, 9(5).
- Umeyama, S. (1991). Least-squares estimation of transformation parameters between two point patterns. *IEEE TPAMI*, 13(4).
- Besl, P. J., & McKay, N. D. (1992). A method for registration of 3-D shapes. *IEEE TPAMI*, 14(2). (ICP)
- Fitzpatrick, J. M., West, J. B., & Maurer, C. R. (1998). Predicting error in rigid-body point-based registration. *IEEE Transactions on Medical Imaging*, 17(5). (FRE·TRE)
- Evangelidis, G. D., & Psarakis, E. Z. (2008). Parametric image alignment using enhanced correlation coefficient maximization. *IEEE TPAMI*, 30(10). (ECC)
- SciPy 문서: `scipy.optimize.least_squares` (loss="soft_l1"); OpenCV 문서: `cv2.findTransformECC`, `cv2.warpAffine`; shapely 2.x 문서: `shapely.distance`, `shapely.affinity`; contourpy 문서
- (선택) Open3D 튜토리얼: "ICP registration" — Open3D 를 설치한 경우 3D 점군 ICP 교차 확인용
- 청사진 관련 절: [BLUEPRINT](../../BLUEPRINT.md) H4, C3, C4, D4, J3, K4
