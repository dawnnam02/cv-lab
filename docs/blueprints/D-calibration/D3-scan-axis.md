# D3. 스캔 축 캘리브레이션

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: D. 캘리브레이션

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-01 ~ 2026-12-14 (W9-10) |
| 우선순위 | 높음 |
| 트랙 | 하드웨어 |
| 선행 요소 | [D2 레이저 평면](D2-laser-plane.md) · [C1 스캔 이동 장치](../C-mechanics/C1-scan-stage.md) · [C4 좌표계 체계](../C-mechanics/C4-coordinate-frames.md) · [F2 획득 파라미터](../F-acquisition/F2-acquisition-params.md) |
| 후행 요소 | [D5 검증·이력 관리](D5-calibration-verification.md) · [D4 센서↔G코드 좌표](D4-sensor-to-gcode.md) · [H1 점→격자 변환](../H-analysis/H1-gridding.md) · [I1 측정 불확도](../I-reliability/I1-uncertainty.md) |
| 관련 마일스톤 | **M2** — 게이지 블록 단차 오차 < 10 µm (D5) |

---

## 1. 목적

레이저 선 하나는 단면 한 줄만 측정합니다. 스테이지로 시편(또는 센서)을 움직여 여러 줄을 모아야 면이 되는데, 이때 필요한 두 가지를 구합니다.

1. **스캔 방향 벡터 s** — 스테이지가 실제로 움직이는 방향 (카메라 좌표계 {C} 기준, 단위 벡터)
2. **배율 k [mm/카운트]** — 엔코더(또는 트리거) 한 카운트당 실제 이동 거리

두 값을 합친 **스캔 벡터 v = k·s** 로, 카운트 c 에서 찍은 프로파일 점 X_C 를 시편에 고정된 좌표 `Y = X_C + c·v` 로 옮깁니다. 그다음 측정 좌표계 {M} 의 축을 정의해서 H1(높이맵)로 넘깁니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 왜 방향과 배율을 따로 재야 하나
| 오류 | 결과 | 예시 크기 |
|---|---|---|
| 배율 k 가 0.4 % 틀림 | Y(스캔 방향) 치수가 0.4 % 틀림 | 50 mm 에서 200 µm |
| 스캔 방향이 레이저 평면 법선과 수평으로 0.5° 틀어짐 (yaw) | 형상이 평행사변형으로 기움(전단): X 위치가 스캔 거리에 비례해 밀림 | 50 mm 스캔에서 X 가 436 µm 밀림 |
| 스캔 방향이 위아래로 0.3° 기욺 (pitch) | 높이가 스캔 거리에 비례해 기울어짐 | 50 mm 스캔에서 262 µm |

pitch 기울기는 H3(바닥 평면 기준화)에서 일부 보정되지만, 측정 좌표 자체가 틀리면 XY 형상이 함께 틀어지므로 D3 에서 바로잡는 것이 원칙입니다.

### 2.2 구(볼)를 쓰는 이유
구는 어느 방향에서 봐도 표면이 중심에서 반지름 R 만큼 떨어져 있습니다. 스캔 벡터 v 가 틀리면 점군이 **타원체(찌그러진 구)** 가 되므로, "모든 점이 반지름 R 인 구 위에 있어야 한다"는 조건 하나로 v 의 세 성분을 모두 풀 수 있습니다.

```
미지수: v (3개) + 구 중심 C_j (구마다 3개)
잔차:   | X_C + c·v − C_j | − R        (R 은 인증서의 반지름으로 고정)
```
이것을 `scipy.optimize.least_squares` 로 한 번에 풉니다. 반지름 R 이 배율의 기준(자) 역할을 하므로 **인증된 정밀 구**를 써야 합니다.

### 2.3 BLUEPRINT 의 "두 위치" 방법과의 관계
BLUEPRINT D3 는 "구 하나를 스캔하고, 알려진 거리만큼 옮겨 다시 스캔 → 중심 이동량 ÷ 명령 이동량" 방법을 소개합니다. 이 방법은 **직관적인 확인용**으로 아주 좋습니다(5장 4단계). 다만 각 스캔의 점군을 만들 때 이미 v 가 필요하므로, 주 계산은 2.2 의 **동시 맞춤**으로 하고 "두 위치" 방법으로 배율을 교차 확인합니다.

### 2.4 측정 좌표계 {M} 정의 (C4 와 일치)
| 축 | 정의 |
|---|---|
| 원점 | 카메라 광축이 레이저 평면과 만나는 점 |
| y_M | 스캔 방향 s |
| z_M | 레이저 평면 안에서 카메라 쪽("위")을 향하는 방향을 s 에 수직이 되게 만든 것 |
| x_M | y_M × z_M (오른손 좌표계, 대략 레이저 선 방향) |

`X_M = R_M_C · (X_C + c·v − origin)`. 측정값의 축 방향이 맞는지는 C4 의 **비대칭 L자 시편**으로 눈으로 확인합니다.

### 2.5 선형 모델의 한계
`Y = X_C + c·v` 는 "스테이지가 완벽한 직선으로, 일정한 간격으로 움직인다"는 가정입니다. 스테이지의 직진도, 피치·요 각도 변화(아베 오차), 리드나사 주기 오차는 이 모델이 담지 못합니다. 그래서 **잔차를 카운트 c 에 대해 그려 보고** 주기적 패턴이나 경향이 있는지 확인합니다(7장).

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식·위치 | 설명 |
|---|---|---|---|
| 입력 | 카메라·레이저 평면 | `camera_intrinsics.yaml`, `laser_plane.yaml` (D1, D2) | 프로파일 → X_C 변환 |
| 입력 | 구 판(볼 플레이트) 스캔 | `data/raw/calib/CAL-2026-12-08-A/d3/ballplate_r01.npz` (u, v, 밝기, count) | Ø 8 mm 무광 세라믹 구 3개, FOV 가로로 분산 |
| 입력 | 구 인증서 | 반지름(지름) 인증값과 불확도 | 예: Ø 8.000 mm |
| 입력 | 스테이지 설정 | 명목 피치 0.020 mm/카운트, 스캔 방향(+), 속도 | C1, F2 |
| 산출물 | **스캔 축 파일** | `config/calibration/CAL-2026-12-08-A/scan_axis.yaml` | v, k, s, 비직교 각, R_M_C, 원점, 잔차 |
| 산출물 | 잔차 그래프 | `.../d3_residual_vs_count.png` | 선형 모델 한계 확인 |
| 산출물 | 반복 결과표 | `.../d3_repeat.csv` (회차, k, 비직교각, 잔차) | 3회 반복 재현성 |

> 캘리브레이션 ID: D3 가 끝나면 D1·D2·D3 결과를 한 폴더에 묶어 **새 ID `CAL-2026-12-08-A`** 를 붙입니다. D1·D2 파일은 그대로 복사하고, D5 검증은 이 묶음 ID 에 대해 합니다.

---

## 4. 결정 사항

| ID | 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|---|
| D3-1 | 기준물 | 구 1개 / **구 3개 판** / 게이지 블록 | 구 3개 (FOV 좌·중·우) | 한 번 스캔으로 방향·배율 + 위치 의존성까지 |
| D3-2 | 구 크기·재질 | Ø 5~10 mm, **무광 세라믹** | Ø 8 mm, 반지름 인증 | 반짝이는 강구는 레이저가 튐 (C3, E1) |
| D3-3 | 반지름 처리 | 함께 추정 / **인증값 고정** | 고정 | 반지름이 배율의 기준. 함께 풀면 v 와 상관되어 불안정 |
| D3-4 | 스캔 길이 | 구 지름만 / **구 지름 + 앞뒤 4 mm** | 16 mm 이상 | 구 전체 단면 + 바닥 확보 |
| D3-5 | 스캔 방향 | 왕복 / **단방향(+)** | 단방향 | 백래시 제외 (C1) |
| D3-6 | 촬영 방식 | 시간 간격 / **엔코더 위치 트리거** / 스텝 & 촬영 | 위치 트리거 | 속도 변동이 배율 오차가 되지 않음 (C1) |
| D3-7 | 반복 수 | 1 / **3** | 3회 | k 재현성 확인, 평균 사용 |
| D3-8 | 비직교 처리 | 무시 / **v 에 포함** | 포함 | 0.5° 만 틀어져도 50 mm 스캔에서 X 가 436 µm 밀림 (2.1절) |

---

## 5. 수행 절차

1. **준비**
   - [ ] D2 완료 확인 (같은 광학 상태)
   - [ ] 구 판을 스테이지에 고정, 구 3개가 FOV 의 좌(−6 mm)·중(0)·우(+6 mm)에 오도록 배치
   - [ ] 구 표면 청소 (지문·먼지 = 형상 오차)
   - [ ] 스테이지 원점 복귀 후 **스캔 시작점보다 2 mm 뒤**에서 출발 (백래시 제거 접근)
2. **스캔 (3회 반복)**
   - [ ] 피치 0.020 mm, 길이 16 mm 이상, 위치 트리거
   - [ ] 각 회차 사이에 판을 건드리지 않음. 회차별 실내 온도 기록
3. **계산**
   - [ ] 프로파일 → X_C (D2 함수)
   - [ ] 초깃값 v0 = 0.020 × (레이저 평면 법선) 으로 점군 → 구별로 영역 나누기(구 번호)
   - [ ] 동시 맞춤으로 v, C_j 추정 → k, s, 비직교 각 계산
   - [ ] 잔차 RMS, 카운트별 잔차 그래프 확인
4. **교차 확인 ("두 위치" 방법)**
   - [ ] 스테이지를 명령으로 정확히 10.000 mm 옮긴 뒤 같은 구판을 다시 스캔
   - [ ] 추정한 v 로 만든 두 점군에서 구 중심 이동량 계산 → |이동량 − 10.000| < 10 µm
5. **저장과 {M} 정의**
   - [ ] `scan_axis.yaml` 저장, D1·D2 파일과 함께 `CAL-2026-12-08-A` 폴더로 묶음
   - [ ] L자 시편을 한 번 스캔해 x·y 가 뒤집히지 않았는지 확인 (C4)
   - [ ] D5 검증으로 진행 (Y 방향 게이지 블록 길이 포함)

---

## 6. Python 구현

### 6.1 구 3개 동시 맞춤 (`d3_scan_axis.py`)
D2 와 같은 기하 배치에서, 스테이지가 0.5° (yaw)·0.3° (pitch) 틀어지고 0.4 % 더 이동하는 "숨은 정답"을 만든 뒤, 구 3개의 합성 스캔(약 60만 점, 노이즈 4 µm)에서 이를 되찾습니다.

```python
"""
D3. 스캔 축 캘리브레이션 — 정밀 구(볼) 3개를 한 번 스캔해서
    스캔 방향 벡터 s 와 배율 k [mm/카운트] 를 동시에 구하는 예제 (합성 데이터)
---------------------------------------------------------------------------
모델:  카운트 c 에서 찍은 레이저 점 X_C(c) (카메라 좌표, D2 결과)
       → 시편에 붙은 좌표로  Y = X_C + c · v ,   v = k · s  (3성분 벡터)
       구 표면 위의 점이므로 |Y − C_j| = R (구 반지름, 인증값)
미지수: v (3개) + 구 중심 C_j (구마다 3개)  →  scipy least_squares 로 한 번에 추정
실행:  python3 d3_scan_axis.py
"""
import numpy as np
import yaml
from scipy.optimize import least_squares

rng = np.random.default_rng(3)

# ------------------------------------------------------------- D2 결과 (카메라 좌표계 레이저 평면)
THETA = np.radians(30); WD = 125.0
cam = np.array([0.0, -WD * np.sin(THETA), WD * np.cos(THETA)])
zc = -cam / np.linalg.norm(cam); xc = np.cross([0, -1.0, 0], zc); xc /= np.linalg.norm(xc)
R_CW = np.vstack([xc, np.cross(zc, xc), zc]); t_CW = -R_CW @ cam      # 합성용 기하 (D2 와 같음)
N_PLANE = R_CW @ np.array([0, 1.0, 0]); D_PLANE = -N_PLANE @ t_CW     # n·X + d = 0

# ------------------------------------------------------------- 합성용 '정답' 스테이지
PITCH_NOM = 0.020                                   # 명목 스캔 간격 [mm/카운트]
K_TRUE = PITCH_NOM * 1.004                          # 실제는 0.4 % 더 이동 (리드 오차 등)
yaw, pitch = np.radians(0.5), np.radians(0.3)       # 스테이지가 레이저 평면 법선에서 틀어진 각도
s_W = np.array([np.sin(yaw), np.cos(yaw) * np.cos(pitch), np.sin(pitch)])
S_TRUE = R_CW @ s_W                                  # 카메라 좌표계 스캔 방향
V_TRUE = K_TRUE * S_TRUE

R_BALL = 4.000                                       # Ø 8 mm 세라믹 구 (인증 반지름)
CENTERS_W = np.array([[-6.0, 4.0, 4.0], [0.0, 5.0, 4.0], [6.0, 6.0, 4.0]])   # 판 위 구 3개 (세계 좌표)
N_COUNTS = 800                                       # 800 카운트 x 0.02 mm = 16 mm 스캔
NOISE_UM = 4.0                                       # 깊이 방향 노이즈 σ [µm]


def synth_scan():
    """카운트마다 레이저 평면과 구의 교선(원) 중 카메라·레이저 모두에 보이는 부분을 점으로 생성"""
    up_C = R_CW @ np.array([0, 0, 1.0])              # 레이저가 오는 방향(위)
    pts, cnt, ball_id = [], [], []
    for c in range(N_COUNTS):
        for j, cw in enumerate(CENTERS_W):
            Cc = R_CW @ cw + t_CW - c * V_TRUE       # 이 순간 센서가 보는 구 중심 (시편이 −v 방향으로 감)
            h = Cc @ N_PLANE + D_PLANE               # 구 중심 ~ 레이저 평면 거리
            if abs(h) >= R_BALL:
                continue
            r = np.sqrt(R_BALL**2 - h**2)            # 단면 원 반지름
            ctr = Cc - h * N_PLANE                   # 단면 원 중심
            a = np.cross(N_PLANE, up_C); a /= np.linalg.norm(a)
            b = np.cross(N_PLANE, a)
            if b @ up_C < 0:
                b = -b
            n_pts = max(int(2 * np.pi * r / 0.0138), 8)        # 열 간격 13.8 µm 수준
            phi = np.linspace(0, 2 * np.pi, n_pts, endpoint=False)
            P = ctr + r * (np.outer(np.cos(phi), a) + np.outer(np.sin(phi), b))
            normal = (P - Cc) / R_BALL
            to_cam = -P / np.linalg.norm(P, axis=1, keepdims=True)
            vis = (normal @ up_C > 0.17) & ((normal * to_cam).sum(1) > 0.17)   # 80° 넘게 비스듬한 곳 제외
            P = P[vis]
            ray = P / np.linalg.norm(P, axis=1, keepdims=True)
            P = P + ray * rng.normal(0, NOISE_UM / 1000, (len(P), 1))     # 광선 방향 노이즈
            pts.append(P); cnt.append(np.full(len(P), c)); ball_id.append(np.full(len(P), j))
    return np.vstack(pts), np.concatenate(cnt), np.concatenate(ball_id)


# ------------------------------------------------------------- 실제 파이프라인 함수
def fit_sphere_linear(P):
    """구 맞춤 (반지름도 추정, 선형 최소제곱) → 중심, 반지름"""
    A = np.hstack([2 * P, np.ones((len(P), 1))])
    sol, *_ = np.linalg.lstsq(A, (P**2).sum(1), rcond=None)
    c = sol[:3]
    return c, np.sqrt(sol[3] + c @ c)


def build_cloud(X_C, counts, v):
    """프로파일 점 + 스캔 이동 → 시편 고정 좌표 (카메라 축 방향 그대로)"""
    return X_C + counts[:, None] * v


def estimate_scan_vector(X_C, counts, ball_id, R, v0):
    """v 와 구 중심들을 동시에 추정. R(반지름)은 인증값으로 고정"""
    n_ball = ball_id.max() + 1
    Y0 = build_cloud(X_C, counts, v0)
    c0 = [fit_sphere_linear(Y0[ball_id == j])[0] for j in range(n_ball)]
    x0 = np.concatenate([v0] + c0)

    def residual(x):
        v, C = x[:3], x[3:].reshape(-1, 3)
        Y = build_cloud(X_C, counts, v)
        return np.linalg.norm(Y - C[ball_id], axis=1) - R

    sol = least_squares(residual, x0, x_scale="jac")
    J = sol.jac                                         # 불확도 추정: 공분산 ≈ σ² (JᵀJ)⁻¹
    sigma2 = (sol.fun**2).sum() / (len(sol.fun) - len(x0))
    cov = np.linalg.inv(J.T @ J) * sigma2
    return sol.x[:3], sol.x[3:].reshape(-1, 3), sol.fun, cov[:3, :3]


def measurement_frame(n, d, s):
    """측정 좌표계 {M}: y = 스캔 방향, z = 레이저 평면 안의 '위', x = y × z (오른손 좌표계)"""
    r0 = np.array([0, 0, 1.0])                          # 광축
    origin = r0 * (-d / (r0 @ n))                       # 광축이 레이저 평면과 만나는 점
    up = -r0 - (-r0 @ n) * n                            # 카메라 쪽 방향을 레이저 평면에 투영
    e_y = s / np.linalg.norm(s)
    e_z = up - (up @ e_y) * e_y; e_z /= np.linalg.norm(e_z)
    e_x = np.cross(e_y, e_z)
    return np.vstack([e_x, e_y, e_z]), origin           # X_M = R_MC (Y − origin)


def main():
    X_C, counts, ball_id = synth_scan()
    print(f"합성 스캔: 점 {len(X_C):,} 개, 카운트 {N_COUNTS}, 구 {ball_id.max()+1} 개")

    n = N_PLANE if N_PLANE @ V_TRUE > 0 else -N_PLANE   # 초깃값: '스캔 = 레이저 평면에 수직'
    v0 = PITCH_NOM * n
    v, C, res, cov_v = estimate_scan_vector(X_C, counts, ball_id, R_BALL, v0)
    k = np.linalg.norm(v); s = v / k
    nonortho = np.degrees(np.arccos(np.clip(s @ n, -1, 1)))
    print(f"배율 k = {k*1000:.4f} µm/카운트 (정답 {K_TRUE*1000:.4f}, 명목 {PITCH_NOM*1000:.1f}) "
          f"→ 명목 대비 {100*(k/PITCH_NOM-1):+.3f} %")
    print(f"스캔 방향과 레이저 평면 법선 사이 각 = {nonortho:.3f}° "
          f"(정답 {np.degrees(np.arccos(S_TRUE @ n)):.3f}°)")
    print(f"방향 오차 = {np.degrees(np.arctan2(np.linalg.norm(np.cross(s, S_TRUE)), s @ S_TRUE))*3600:.1f} arcsec, "
          f"맞춤 잔차 RMS = {res.std()*1000:.2f} µm, k 표준불확도 = {np.sqrt(cov_v.diagonal()).max()*1e6:.2f} nm/카운트")

    # 검증 1: 추정한 v 로 만든 점군에 반지름 자유 구 맞춤 → 반지름이 인증값과 같아야 함
    for label, vv in (("명목 v0 사용", v0), ("추정 v 사용", v)):
        Y = build_cloud(X_C, counts, vv)
        radii = [fit_sphere_linear(Y[ball_id == j])[1] for j in range(3)]
        cs = [fit_sphere_linear(Y[ball_id == j])[0] for j in range(3)]
        d13 = np.linalg.norm(cs[2] - cs[0]); d13_true = np.linalg.norm(CENTERS_W[2] - CENTERS_W[0])
        print(f"  [{label}] 반지름 오차 = {', '.join(f'{(r-R_BALL)*1000:+.1f}' for r in radii)} µm, "
              f"구1-구3 중심거리 오차 = {(d13-d13_true)*1000:+.1f} µm")

    # 민감도: 구 반지름 인증값이 2 µm 틀렸다면 k 는 얼마나 변하나?
    v_b, *_ = estimate_scan_vector(X_C, counts, ball_id, R_BALL + 0.002, v0)
    print(f"  [민감도] 반지름 +2 µm 가정 → k 변화 {100*(np.linalg.norm(v_b)/k-1):+.4f} %")

    R_MC, origin = measurement_frame(n, D_PLANE, s)
    out = {
        "calibration_id": "CAL-2026-12-08-A",
        "element": "D3",
        "scan_vector_C_mm_per_count": v.round(9).tolist(),
        "scale_mm_per_count": round(float(k), 9),
        "direction_C": s.round(9).tolist(),
        "nonorthogonality_deg": round(float(nonortho), 4),
        "R_M_C": R_MC.round(9).tolist(),
        "origin_C_mm": origin.round(6).tolist(),
        "sphere_radius_mm": R_BALL,
        "fit_rms_um": round(float(res.std() * 1000), 3),
        "scan_direction_rule": "항상 + 방향 단방향 스캔",
    }
    with open("scan_axis.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False)
    print("저장: scan_axis.yaml")


if __name__ == "__main__":
    main()
```

**실행 예시와 기대 출력** (약 7초)

```
$ python3 d3_scan_axis.py
합성 스캔: 점 602,976 개, 카운트 800, 구 3 개
배율 k = 20.0802 µm/카운트 (정답 20.0800, 명목 20.0) → 명목 대비 +0.401 %
스캔 방향과 레이저 평면 법선 사이 각 = 0.582° (정답 0.583°)
방향 오차 = 8.1 arcsec, 맞춤 잔차 RMS = 2.67 µm, k 표준불확도 = 0.24 nm/카운트
  [명목 v0 사용] 반지름 오차 = -10.7, -8.9, -7.2 µm, 구1-구3 중심거리 오차 = -18.7 µm
  [추정 v 사용] 반지름 오차 = -0.0, -0.1, -0.1 µm, 구1-구3 중심거리 오차 = -0.0 µm
  [민감도] 반지름 +2 µm 가정 → k 변화 +0.0124 %
저장: scan_axis.yaml
```

**출력 읽는 법**
- 배율 20.0802 µm/카운트 → 정답 20.0800 과 0.001 % 이내. 명목(20.0)과 +0.401 % 차이가 바로 보정해야 할 배율 오차입니다.
- 비직교 각 0.582° 를 찾아냈습니다 (yaw 0.5° 와 pitch 0.3° 의 합성).
- 명목 v0 를 그대로 쓰면 구 반지름이 −7 ~ −11 µm, 구 사이 거리가 −18.7 µm 틀립니다. 추정 v 를 쓰면 0.1 µm 이내로 돌아옵니다.
- 반지름 인증값이 2 µm 틀리면 k 가 0.012 % 바뀝니다 → 50 mm 에서 6 µm. **구 인증 불확도가 배율 불확도로 그대로 넘어가므로** I1 불확도 예산에 넣습니다.

### 6.2 잔차-카운트 그래프 (선형 모델 점검)
6.1 파일과 같은 폴더에서 실행합니다.

```python
"""
D3 보충: 선형 스캔 모델 점검 — 구 맞춤 잔차를 카운트 구간별로 평균해서 경향·주기 오차를 찾음
d3_scan_axis.py 와 같은 폴더에서 실행:  python3 d3_residual_plot.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import d3_scan_axis as d3

X_C, counts, ball_id = d3.synth_scan()
n = d3.N_PLANE if d3.N_PLANE @ d3.V_TRUE > 0 else -d3.N_PLANE
v, C, res, _ = d3.estimate_scan_vector(X_C, counts, ball_id, d3.R_BALL, d3.PITCH_NOM * n)

bins = np.arange(0, counts.max() + 100, 100)              # 100 카운트(2 mm)씩 구간 (점이 있는 범위만)
idx = np.digitize(counts, bins) - 1
means = np.array([res[idx == b].mean() * 1000 if np.any(idx == b) else np.nan for b in range(len(bins) - 1)])
print("구간별 평균 잔차 [µm]:", np.round(means, 2))
print(f"최대 |구간 평균| = {np.nanmax(np.abs(means)):.2f} µm  (기준 < 2 µm)")

fig, ax = plt.subplots(figsize=(7, 3))
sel = np.random.default_rng(0).choice(len(res), 20000, replace=False)   # 점이 많으므로 2만 개만 표시
ax.plot(counts[sel], res[sel] * 1000, ".", ms=1, alpha=0.3, label="residual")
ax.plot((bins[:-1] + bins[1:]) / 2, means, "o-", color="tab:red", label="bin mean")
ax.axhline(0, color="k", lw=0.8)
ax.set_xlabel("encoder count"); ax.set_ylabel("sphere residual [um]"); ax.legend()
fig.tight_layout(); fig.savefig("d3_residual_vs_count.png", dpi=150)
print("저장: d3_residual_vs_count.png")
```

```
$ python3 d3_residual_plot.py
구간별 평균 잔차 [µm]: [-0.01  0.01 -0.01 -0.    0.02]
최대 |구간 평균| = 0.02 µm  (기준 < 2 µm)
저장: d3_residual_vs_count.png
```

### 6.3 실제 데이터에 적용할 때 바꿀 부분
- `synth_scan()` → 저장된 프로파일 묶음(`.npz`, F3)을 읽고 D2 의 `pixels_to_rays` + `intersect_rays_plane` 으로 X_C 계산. `counts` 는 엔코더 카운트(또는 트리거 번호)
- `ball_id` → 초깃값 v0 로 만든 점군에서 구 3개 근처 점을 고르는 영역 지정(예: x 좌표 구간 3개, 바닥 위 1 mm 이상인 점)
- 바닥 판 점, 구 아래쪽 가장자리(앙각 < 10°) 점은 제외 — 엣지 효과(E2)

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 | 6.1 합성 결과 |
|---|---|---|---|
| 맞춤 잔차 RMS | 동시 맞춤 잔차 | < 5 µm | 2.67 µm |
| 잔차 경향 | 6.2 그래프, 카운트 구간별 평균 | 구간 평균 \|·\| < 2 µm, 주기 패턴 없음 | 최대 0.02 µm (6.2) |
| 반지름 재현 | 추정 v 로 만든 점군에서 반지름 자유 맞춤 | \|R − R_인증\| < 2 µm | ≤ 0.1 µm |
| 구 중심 간 거리 | 구1–구3 거리 vs 판 인증(또는 CMM) 값 | < 10 µm | 0.0 µm |
| 배율 재현성 | 3회 반복 k 의 표준편차 | < 0.02 % | (실측 시 기록) |
| 두 위치 교차 확인 | 10.000 mm 이동 후 중심 이동량 | \|차이\| < 10 µm | (실측 시 기록) |
| Y 길이 | D5 게이지 블록 30 mm 를 스캔 방향으로 | 오차 < 0.1 % | D5 참조 (+9.8 µm) |

**완료 판정**: 위 표가 모두 합격하고 `scan_axis.yaml` 이 `CAL-2026-12-08-A` 폴더에 저장되면 완료. M2 판정은 D5 에서 합니다.

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 반짝이는 강구 사용 | 구 꼭대기에 포화·결측, 반지름이 이상하게 나옴 | 무광 세라믹 구 (D3-2) |
| 반지름까지 함께 추정 | k 가 회차마다 크게 흔들림 | 인증 반지름 고정 (D3-3) |
| 시간 간격 촬영 + 속도 변동 | 구가 스캔 방향으로 찌그러짐, k 재현성 나쁨 | 엔코더 위치 트리거 |
| 왕복 스캔 | 두 방향 결과가 백래시만큼 어긋남 | 단방향, 출발 전 2 mm 접근 이동 |
| 구 아래쪽 가장자리 점 포함 | 잔차가 크고 반지름이 커짐 | 앙각 10° 미만 점 제외 |
| 카운트 부호 반대 | L자 시편이 거울상으로 나옴 | `Y = X_C + c·v` 의 부호를 L자 시편으로 확인 후 고정 |
| 프린터 축을 스캔 축으로 쓰면서 스텝/mm 를 믿음 | Y 치수가 수 0.1 % 틀림 | 반드시 D3 로 k 를 측정해서 사용 |
| 스캔 축을 D2 이전에 교정 | 레이저 평면이 바뀌면 v 도 무효 | 순서 D1 → D2 → D3 |

---

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 스테이지 직진도·각도 오차가 큼 (선형 모델 부족) | 중 | 높음 | 잔차-카운트 그래프에서 확인. 크면 카운트별 보정표(LUT) 추가 또는 스테이지 교체 |
| 프린터 축 사용 시 스텝 손실·벨트 늘어짐 | 중 | 높음 | 3회 반복 재현성 확인, 스텝 & 촬영 방식 고려 |
| 정밀 구·인증서 확보 지연 | 중 | 중 | W7 까지 발주. 임시로 마이크로미터로 지름을 잰 무광 구 사용(불확도 증가 기록) |
| 온도 변화로 리드나사 길이 변화 | 낮음 | 중 | 온도 기록, ±1 °C 이내에서 교정·측정 (C6) |

---

## 10. 기록 양식

`config/calibration/CAL-2026-12-08-A/d3_record.yaml`

```yaml
calibration_id: CAL-2026-12-08-A
element: D3
includes: {D1: CAL-2026-11-24-A, D2: CAL-2026-11-24-A}
date: 2026-12-08
operator: ""
room_temp_C: null
stage: {type: "", nominal_pitch_mm: 0.020, direction: "+", trigger: encoder, speed_mm_s: null}
spheres:
  certified_diameter_mm: 8.000
  certificate_uncertainty_um: null
  positions_note: "FOV 좌·중·우"
repeats:
  - {run: 1, k_um_per_count: null, nonortho_deg: null, fit_rms_um: null}
  - {run: 2, k_um_per_count: null, nonortho_deg: null, fit_rms_um: null}
  - {run: 3, k_um_per_count: null, nonortho_deg: null, fit_rms_um: null}
two_position_check: {commanded_mm: 10.000, measured_mm: null, diff_um: null}
L_specimen_axis_check: ""     # 정상 / 뒤집힘
decision: ""
notes: ""
```

`d3_repeat.csv`

| run | k_um_per_count | nonortho_deg | fit_rms_um | max_bin_resid_um | room_temp_C |
|---|---|---|---|---|---|
| 1 |  |  |  |  |  |

---

## 11. 참고 자료

- SciPy 공식 문서: `scipy.optimize.least_squares` (비선형 최소제곱, 야코비안)
- 구 맞춤(sphere fitting)과 기하 맞춤(geometric fitting) — ISO 10360 계열 좌표측정기 성능 시험에서 구·볼 플레이트를 쓰는 방식 참고
- 아베 오차(Abbe error)와 직진도 — 정밀 기계 설계 교과서 주제
- 레이저 선 스캐너의 "scan direction calibration", "motion axis calibration" 주제
- 상위 기준: [BLUEPRINT.md D3, C1, C4](../../BLUEPRINT.md)
