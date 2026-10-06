# D2. 레이저 평면 캘리브레이션

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: D. 캘리브레이션

| 항목 | 내용 |
|---|---|
| 기간 | 2026-11-17 ~ 2026-11-30 (W7-8) |
| 우선순위 | 긴급 |
| 트랙 | 하드웨어 |
| 선행 요소 | [D1 카메라 내부](D1-camera-intrinsics.md) · [B2 기하 배치](../B-optics/B2-geometry.md) · [B6 레이저 광원](../B-optics/B6-laser.md) · [F1 레이저 라인 중심 추출](../F-acquisition/F1-line-extraction.md) · [C8 레이저 안전](../C-mechanics/C8-laser-safety.md) |
| 후행 요소 | [D3 스캔 축](D3-scan-axis.md) · [D5 검증·이력 관리](D5-calibration-verification.md) · [I1 측정 불확도](../I-reliability/I1-uncertainty.md) · [J3 합성 데이터 테스트](../J-software/J3-synthetic-tests.md) |
| 관련 마일스톤 | **M1** — 재투영 오차 < 0.2 px, 레이저 평면 맞춤 잔차 < 5 µm |

---

## 1. 목적

카메라 좌표계 {C}에서 **레이저가 만드는 빛의 평면** 방정식 `n·X + d = 0` 을 구합니다.

- D1 덕분에 픽셀 하나는 "카메라에서 나가는 광선"이 되었지만, 광선 위의 **어느 거리**인지는 아직 모릅니다.
- 레이저 선 위의 점은 반드시 레이저 평면 위에 있으므로, **광선과 레이저 평면의 교점 = 3D 점**입니다. 이것이 레이저 삼각측량의 계산 핵심입니다.
- 이 요소의 정확도가 곧 **높이 측정 정확도의 상한**입니다. 그래서 영역 D 에서 우선순위가 "긴급"입니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 평면의 방정식
3D 공간의 평면은 단위 법선 벡터 n(평면에 수직인 방향, 길이 1)과 상수 d 로 `n·X + d = 0` 처럼 씁니다. 점 X 를 넣었을 때 `n·X + d` 값은 **평면까지의 부호 있는 거리[mm]**입니다. 이 값으로 맞춤 잔차를 계산합니다.

### 2.2 광선-평면 교점 (삼각측량 계산)
1. 레이저 중심 픽셀 (u, v) → `cv2.undistortPoints` 로 왜곡 제거 → 정규 좌표 (x, y)
2. 광선 방향 r = (x, y, 1). 광선 위 점은 X = t·r (t > 0)
3. 평면에 대입: n·(t·r) + d = 0 → **t = −d / (n·r)** → X = t·r

### 2.3 평면 타깃 방법 (방법 A, 권장)이 동작하는 원리
- 보드 자세를 `cv2.solvePnP` 로 구하면 "보드 평면"을 {C} 좌표로 압니다.
- 같은 자세에서 레이저를 켜고 찍으면, 레이저 선 픽셀의 광선과 **보드 평면**의 교점 = 레이저 선 위의 3D 점입니다.
- 한 자세는 3D **직선** 하나만 줍니다. 직선 하나로는 평면이 정해지지 않으므로 **여러 자세, 특히 서로 다른 높이**에서 직선을 모아야 합니다.

### 2.4 "퇴화(degenerate)" — 잔차는 작은데 틀린 평면
모든 자세를 같은 높이·거의 수평으로 두면 직선들이 거의 한 줄로 겹칩니다. 평면은 그 직선 주위로 "경첩처럼" 돌아갈 수 있어서, 맞춤 잔차는 작아도 **다른 높이에서는 높이가 틀립니다.** 6.1 코드의 [2]번이 바로 이 경우이며, 잔차 1.28 µm 로 좋아 보이지만 높이 10 mm 에서 −6.3 µm 계통 오차가 납니다. 이를 알아보는 지표가 SVD 특이값 비 `s1/s2` 입니다(작을수록 퇴화에 가까움).

### 2.5 방법 B: 룩업 테이블(LUT)
정밀 수직 스테이지가 있으면 평판을 알려진 높이(0, 0.5, 1.0 … mm)로 옮기며 열 u 마다 레이저 행 v 를 기록하고 `z = 다항식(u, v)` 로 맞춥니다. 렌즈 왜곡까지 한꺼번에 흡수하지만, 스테이지 정확도가 그대로 결과 정확도가 되고 X 방향은 따로 교정해야 합니다. 이 문서는 BLUEPRINT 권장대로 **방법 A** 를 주 방법으로 하고, 방법 B 는 수직 스테이지가 있을 때의 교차 확인용으로 둡니다.

### 2.6 이 과제 기하 배치에서의 숫자
- 레이저 수직, 카메라 30° 경사, 작동 거리 125 mm (B1, B2).
- 레이저 선 두께 σ = 30 µm → 영상에서 약 5 px (B6 권장 3~7 px).
- 측정 깊이 범위 예: −2 ~ +10 mm (시편 높이 + 여유). 자세 높이는 이 범위의 **80 % 이상**을 덮어야 합니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식·위치 | 설명 |
|---|---|---|---|
| 입력 | 카메라 내부 파라미터 | `config/calibration/CAL-2026-11-24-A/camera_intrinsics.yaml` | D1 결과 |
| 입력 | 레이저 끈 사진 | `data/raw/calib/CAL-2026-11-24-A/d2/pose_00_off.png` … | 자세마다 1장, 보드 코너 검출용 |
| 입력 | 레이저 켠 사진 | `.../d2/pose_00_on.png` … | 같은 자세, 레이저만 켬. 같은 노출 |
| 입력 | 자세 기록 | `.../d2/poses.csv` (pose, 스페이서 높이 mm, 기울기) | 높이 분포 확인용 |
| 산출물 | **레이저 평면** | `config/calibration/CAL-2026-11-24-A/laser_plane.yaml` | n(3), d [mm], 잔차 RMS, 점 수, 자세 높이 |
| 산출물 | 3D 점 모음 | `.../d2_points.npy` (N×3, mm) | 재분석·불확도 계산용 |
| 산출물 | 평판 높이 검사표 | `.../d2_plate_check.csv` (z, 평균 오차 µm, P-V µm) | 6.1 [3]번 결과 |

---

## 4. 결정 사항

| ID | 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|---|
| D2-1 | 교정 방식 | **A: 평면 타깃** / B: LUT | A | 추가 장비 불필요, 기하 모델이 명확 (BLUEPRINT 부록 1 #10) |
| D2-2 | 자세 수 | 6 / **8~12** | 8 이상 | BLUEPRINT 최소 6. 이상치 제거 후에도 6 이상 남도록 |
| D2-3 | 자세 높이 분포 | 한 높이 / **깊이 범위의 80 % 이상** | −2 ~ +10 mm 에 고르게 | 2.4절 퇴화 방지 |
| D2-4 | 보드 기울기 | 0° / **±15°** / ±30° | ±15° | 높이 변화도 추가로 만들고, 피사계 심도 안에 머무름 |
| D2-5 | 레이저 위치 | 체커 칸 위 / **흰 띠 위** | 보드 가장자리 흰 영역 또는 흰 칸 위 | 검은 칸 위에서는 밝기가 바뀌어 중심이 밀림 |
| D2-6 | 라인 중심 추출 | 최대 픽셀 / **무게중심(CoG)** / 가우시안 | CoG (F1 과 동일) | 측정 때와 **같은 알고리즘**이어야 함 |
| D2-7 | 이상치 처리 | 없음 / **3σ 제거 후 재맞춤** | 3σ | 반사·가장자리 점 제거 |
| D2-8 | 노출 | – | 레이저 피크 = 최대값의 60~90 %, 포화 0 % | 포화 시 CoG 중심이 평탄해져 오차 |
| D2-9 | 평면 부호 규칙 | – | n 의 z 성분 < 0 (카메라 쪽을 향함) | 파일마다 부호가 뒤집히는 실수 방지 |

---

## 5. 수행 절차

1. **준비 (0.5일)**
   - [ ] D1 완료 확인 (RMS < 0.2 px), 렌즈·필터 상태 그대로
   - [ ] 레이저 **30분 워밍업**, 보안 조치 확인 (C8: Class 2, 빔 아래 방향)
   - [ ] 높이 스페이서 준비: 0, 2, 4, 6, 8, 10 mm (게이지 블록이나 정밀 블록)
2. **자세별 촬영 (자세당 약 3분, 총 8~12 자세)**
   - [ ] 보드를 스페이서 위에 놓고, 레이저 선이 보드의 흰 영역을 가로지르게 배치
   - [ ] 레이저 **끈** 사진 1장 → 코너 검출 성공 확인
   - [ ] 보드를 건드리지 않고 레이저 **켠** 사진 1장 (필요하면 5장 평균)
   - [ ] `poses.csv` 에 높이·기울기 기록
   - [ ] 높이 −2 ~ +10 mm, 기울기 ±15° 범위가 고르게 채워졌는지 확인
3. **계산**
   - [ ] 각 자세: `solvePnP` → 보드 평면, CoG 로 v(u) 추출 → 광선-평면 교점
   - [ ] 전체 점에 SVD 평면 맞춤 → 3σ 제거 → 재맞춤
   - [ ] 잔차 RMS < 5 µm, 자세별 평균 잔차 |·| < 2 µm 확인 (특정 자세만 크면 그 자세 재촬영)
4. **독립 검사**
   - [ ] 평판(또는 게이지 블록 윗면)을 0 / 5 / 10 mm 높이에 두고 측정 → 평균 높이 오차와 폭 방향 기울기(P-V) 확인
   - [ ] (선택) 자세 하나씩 빼고 다시 맞춘 평면으로 10 mm 높이 예측 → 변화 < 2 µm
5. **저장**
   - [ ] `laser_plane.yaml` 저장 (D1 과 같은 캘리브레이션 ID)
   - [ ] 3D 점 `d2_points.npy` 저장, 기록지 작성

---

## 6. Python 구현

### 6.1 합성 데이터로 전체 과정 (`d2_laser_plane.py`)
정답 레이저 평면을 아는 가짜 장치를 만들고, 보드 자세 8개에서 **레이저 선 사진을 실제로 그린 다음** F1 무게중심 추출 → 교점 → 평면 맞춤을 거쳐 정답을 되찾는지 확인합니다. [2]에서는 일부러 나쁜 자세 배치를 만들어 차이를 보여 줍니다.

```python
"""
D2. 레이저 평면 캘리브레이션 (방법 A: 평면 타깃) — 합성 데이터로 끝까지 실행
-------------------------------------------------------------------------
흐름: 보드 자세 8개 → (레이저 끈 사진) 코너 → solvePnP 로 보드 평면
                     → (레이저 켠 사진) 열마다 레이저 중심 v(u) 추출 (F1 무게중심)
                     → 픽셀을 광선으로 바꿔 보드 평면과 교차 → 레이저 위 3D 점
                     → 모든 점에 평면 맞춤(SVD) → n, d  (n·X + d = 0, 카메라 좌표계 {C}, mm)
실제 실험에서는 make_* 합성 함수 대신 사진 파일을 읽고, K·dist 는 D1 의 YAML 에서 읽습니다.
실행:  python3 d2_laser_plane.py
"""
import numpy as np
import cv2
import yaml

rng = np.random.default_rng(7)

# ------------------------------------------------------------------ 카메라 (D1 결과라고 가정)
W, H = 1440, 1080
K = np.array([[7246.4, 0, 723.2], [0, 7246.4, 535.5], [0, 0, 1]])
DIST = np.array([-0.12, 0.0, 2e-4, -1e-4, 0.0])

# ------------------------------------------------------------------ 합성용 '정답' 기하 배치
THETA = np.radians(30)                    # 삼각측량 각도 (B2 권장 30°)
WD = 125.0                                # 카메라 ~ 측정점 거리 [mm]


def look_at(cam_pos, target, up_hint):
    """카메라 위치·바라보는 점으로 R_C_W, t_C_W 계산 (X_C = R X_W + t)"""
    z = target - cam_pos; z /= np.linalg.norm(z)                 # 광축
    x = np.cross(up_hint, z); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.vstack([x, y, z])
    return R, -R @ cam_pos


# 세계 좌표 {W}: 레이저 평면 = (y_W = 0) 평면, z_W = 위쪽. 레이저는 수직으로 아래를 비춤
CAM_POS = np.array([0.0, -WD * np.sin(THETA), WD * np.cos(THETA)])
R_CW, t_CW = look_at(CAM_POS, np.zeros(3), up_hint=np.array([0.0, -1.0, 0.0]))
N_TRUE = R_CW @ np.array([0.0, 1.0, 0.0])                        # 카메라 좌표계의 레이저 평면 법선
D_TRUE = -N_TRUE @ t_CW                                          # n·X + d = 0

# 체커보드 (D1 과 같은 보드)
SQ_MM, INNER = 1.5, (8, 5)
OBJ = np.array([[(i + 1) * SQ_MM, (j + 1) * SQ_MM, 0.0] for j in range(INNER[1]) for i in range(INNER[0])])
BOARD_W, BOARD_H = 9 * SQ_MM, 6 * SQ_MM

# 모든 픽셀의 광선은 카메라에만 의존 → 한 번만 계산해서 재사용
_u, _v = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64))
_pix = np.stack([_u.ravel(), _v.ravel()], 1).reshape(-1, 1, 2)
RAYS_ALL = np.hstack([cv2.undistortPoints(_pix, K, DIST).reshape(-1, 2), np.ones((W * H, 1))])


def make_board_pose(z_world, tilt_max_deg=15):
    """보드 중심이 세계 높이 z_world 에 오고, 레이저 선이 보드를 가로지르도록 자세 생성 → R_CB, t_CB"""
    ax, ay, az = np.radians(rng.uniform(-tilt_max_deg, tilt_max_deg, 3) * [1, 1, 0.6])
    R_WB = cv2.Rodrigues(np.array([ax, 0, 0]))[0] @ cv2.Rodrigues(np.array([0, ay, 0]))[0] \
        @ cv2.Rodrigues(np.array([0, 0, az]))[0]
    centre_W = np.array([rng.uniform(-2, 2), rng.uniform(-1.5, 1.5), z_world])
    t_WB = centre_W - R_WB @ np.array([BOARD_W / 2, BOARD_H / 2, 0])
    return R_CW @ R_WB, R_CW @ t_WB + t_CW


def make_laser_image(R_CB, t_CB, size=(BOARD_W, BOARD_H), sigma_mm=0.03, peak=200, noise=2.0):
    """보드 위에 비친 레이저 선 사진을 합성 (선 두께 σ=30 µm → 영상에서 약 5 px 두께)"""
    n_b, p_b = R_CB[:, 2], t_CB
    lam = (n_b @ p_b) / (RAYS_ALL @ n_b)
    X = RAYS_ALL * lam[:, None]                                   # 보드 위 3D 점 (카메라 좌표)
    Xb = (X - p_b) @ R_CB                                         # 보드 좌표
    on_board = (Xb[:, 0] > 0) & (Xb[:, 0] < size[0]) & (Xb[:, 1] > 0) & (Xb[:, 1] < size[1])
    dist_to_laser = X @ N_TRUE + D_TRUE                           # 레이저 평면까지 거리 [mm]
    I = peak * np.exp(-0.5 * (dist_to_laser / sigma_mm) ** 2) * on_board
    img = I.reshape(H, W) + 8 + rng.normal(0, noise, (H, W))      # 배경 8 + 노이즈
    return np.clip(img, 0, 255).astype(np.uint8)


def make_corner_pixels(R_CB, t_CB, noise_px=0.05):
    """레이저 끈 사진에서 검출된 코너라고 가정 (투영 + 0.05 px 검출 노이즈)"""
    p, _ = cv2.projectPoints(OBJ, cv2.Rodrigues(R_CB)[0], t_CB, K, DIST)
    return (p.reshape(-1, 2) + rng.normal(0, noise_px, (len(OBJ), 2))).astype(np.float32)


# ------------------------------------------------------------------ 실제 파이프라인 함수들
def extract_laser_line(img, threshold=30, half_win=5):
    """F1 무게중심(CoG) 방식: 열(u)마다 레이저 중심 행 v (서브픽셀). 없으면 NaN"""
    img = img.astype(np.float32)
    Hh, Ww = img.shape
    peak = img.argmax(axis=0)
    v = np.full(Ww, np.nan)
    for u in range(Ww):
        if img[peak[u], u] <= threshold:
            continue
        r0, r1 = max(peak[u] - half_win, 0), min(peak[u] + half_win + 1, Hh)
        w = img[r0:r1, u] - threshold
        w[w < 0] = 0
        v[u] = r0 + (w * np.arange(r1 - r0)).sum() / w.sum()
    return v


def pixels_to_rays(u, v):
    """픽셀 (u, v) → 카메라 원점에서 나가는 광선 방향 (x, y, 1). 렌즈 왜곡 제거 포함"""
    pts = np.stack([u, v], 1).reshape(-1, 1, 2).astype(np.float64)
    xy = cv2.undistortPoints(pts, K, DIST).reshape(-1, 2)
    return np.hstack([xy, np.ones((len(xy), 1))])


def intersect_rays_plane(rays, n, d):
    """광선 X = t·ray 와 평면 n·X + d = 0 의 교점"""
    t = -d / (rays @ n)
    return rays * t[:, None]


def fit_plane(P):
    """점들(N,3)에 평면 맞춤 → 단위 법선 n, 상수 d, 특이값 s (s[1]/s[2] 가 작으면 퇴화)"""
    c = P.mean(axis=0)
    _, s, Vt = np.linalg.svd(P - c, full_matrices=False)
    n = Vt[-1]
    if n[2] > 0:                       # 부호 통일: 법선이 카메라 쪽(−Z)을 향하도록
        n = -n
    return n, -n @ c, s


def calibrate_laser_plane(heights_world, tilt_max_deg=15, verbose=True):
    all_pts, per_pose = [], []
    for k, z in enumerate(heights_world):
        R_CB, t_CB = make_board_pose(z, tilt_max_deg)
        corners = make_corner_pixels(R_CB, t_CB)                   # ① 레이저 끈 사진 → 코너
        ok, rvec, tvec = cv2.solvePnP(OBJ, corners, K, DIST)       # ② 보드 자세
        R_est = cv2.Rodrigues(rvec)[0]
        n_b = R_est[:, 2]; d_b = -n_b @ tvec.ravel()               #    보드 평면 (카메라 좌표)
        img = make_laser_image(R_CB, t_CB)                         # ③ 레이저 켠 사진
        v = extract_laser_line(img)
        u = np.arange(W, dtype=np.float64)
        good = ~np.isnan(v)
        P = intersect_rays_plane(pixels_to_rays(u[good], v[good]), n_b, d_b)   # ④ 3D 점
        all_pts.append(P)
        per_pose.append((z, good.sum()))
        if verbose:
            print(f"  자세 {k}: 보드 높이 {z:+5.1f} mm, 레이저 점 {good.sum():4d} 개")
    P = np.vstack(all_pts)
    n, d, s = fit_plane(P)
    res = P @ n + d                                                 # 점-평면 부호 거리 [mm]
    keep = np.abs(res) < 3 * res.std()                              # 3σ 넘는 점 제거 후 재맞춤
    n, d, s = fit_plane(P[keep])
    res = P[keep] @ n + d
    return n, d, s, res, P[keep]


def measure_flat_plate(z_world, n, d):
    """높이 z_world 인 20 x 10 mm 수평 평판을 측정 → (평균 높이 오차 µm, 폭 방향 높이 P-V µm)"""
    t_CB = R_CW @ np.array([-10.0, -5.0, z_world]) + t_CW
    v = extract_laser_line(make_laser_image(R_CW, t_CB, size=(20.0, 10.0)))
    u = np.arange(W, dtype=np.float64); g = ~np.isnan(v)
    Pc = intersect_rays_plane(pixels_to_rays(u[g], v[g]), n, d)    # 추정한 레이저 평면 사용
    Pw = (Pc - t_CW) @ R_CW                                         # 세계 좌표로 (검증용)
    err = (Pw[:, 2] - z_world) * 1000
    slope = np.polyfit(Pw[:, 0], err, 1)                            # 폭(x) 방향 기울기
    pv = abs(slope[0]) * (Pw[:, 0].max() - Pw[:, 0].min())
    return err.mean(), pv


def main():
    print("[1] 높이를 다양하게 둔 8개 자세")
    heights = [-2, 0, 2, 4, 6, 8, 10, 1]
    n, d, s, res, P = calibrate_laser_plane(heights)
    if n @ N_TRUE < 0:
        n_true, d_true = -N_TRUE, -D_TRUE
    else:
        n_true, d_true = N_TRUE, D_TRUE
    ang = np.degrees(np.arccos(np.clip(n @ n_true, -1, 1)))
    # 측정 중심(광축이 평면과 만나는 점)에서 두 평면의 거리 차이
    ray0 = np.array([0, 0, 1.0])
    gap = abs((-d / (ray0 @ n)) - (-d_true / (ray0 @ n_true)))
    print(f"    평면 맞춤 잔차 RMS = {res.std()*1000:.2f} µm  (D2 기준 < 5 µm)")
    print(f"    정답 대비 법선 각도 차 = {ang*3600:.1f} arcsec, 광축상 거리 차 = {gap*1000:.1f} µm")
    print(f"    특이값 비 s1/s2 = {s[1]/s[2]:.0f}  (클수록 평면이 잘 정해짐)")

    print("[2] (나쁜 예) 8개 자세를 모두 같은 높이(0 mm), 거의 수평(±1°)으로 둔 경우")
    n2, d2, s2, res2, _ = calibrate_laser_plane([0] * 8, tilt_max_deg=1, verbose=False)
    if n2 @ n_true < 0:
        n2 = -n2
    ang2 = np.degrees(np.arccos(np.clip(n2 @ n_true, -1, 1)))
    print(f"    잔차 RMS = {res2.std()*1000:.2f} µm 인데도 법선 각도 차 = {ang2*3600:.0f} arcsec, "
          f"s1/s2 = {s2[1]/s2[2]:.0f}  → 잔차만 보면 속는다!")

    print("[3] 검증: 높이 0 / 5 / 10 mm 수평 평판을 두 평면(좋은 예·나쁜 예)으로 측정")
    rows = []
    for z in (0.0, 5.0, 10.0):
        e_good, pv_good = measure_flat_plate(z, n, d)
        rows.append((z, e_good, pv_good))
        e_bad, pv_bad = measure_flat_plate(z, n2 if d2 * d > 0 else -n2, d2 if d2 * d > 0 else -d2)
        print(f"    z = {z:4.1f} mm | 좋은 예: 평균 오차 {e_good:+6.1f} µm, 기울기 P-V {pv_good:5.1f} µm"
              f" | 나쁜 예: {e_bad:+6.1f} µm, P-V {pv_bad:5.1f} µm")

    out = {
        "calibration_id": "CAL-2026-11-24-A",
        "element": "D2",
        "frame": "C (camera), mm",
        "plane_normal": n.round(9).tolist(),
        "plane_d_mm": round(float(d), 6),
        "fit_rms_um": round(float(res.std() * 1000), 3),
        "n_points": int(len(P)),
        "n_poses": len(heights),
        "pose_heights_mm": heights,
        "intrinsics_file": "camera_intrinsics.yaml",
    }
    with open("laser_plane.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False)
    np.save("d2_points.npy", P)                                     # 3D 점 (N,3) mm
    np.savetxt("d2_plate_check.csv", np.array(rows), delimiter=",", fmt="%.3f",
               header="z_mm,mean_err_um,pv_um", comments="")
    print("저장: laser_plane.yaml, d2_points.npy, d2_plate_check.csv")


if __name__ == "__main__":
    main()
```

**실행 예시와 기대 출력** (약 5초)

```
$ python3 d2_laser_plane.py
[1] 높이를 다양하게 둔 8개 자세
  자세 0: 보드 높이  -2.0 mm, 레이저 점  761 개
  자세 1: 보드 높이  +0.0 mm, 레이저 점  764 개
  자세 2: 보드 높이  +2.0 mm, 레이저 점  791 개
  자세 3: 보드 높이  +4.0 mm, 레이저 점  794 개
  자세 4: 보드 높이  +6.0 mm, 레이저 점  802 개
  자세 5: 보드 높이  +8.0 mm, 레이저 점  825 개
  자세 6: 보드 높이 +10.0 mm, 레이저 점  841 개
  자세 7: 보드 높이  +1.0 mm, 레이저 점  786 개
    평면 맞춤 잔차 RMS = 1.10 µm  (D2 기준 < 5 µm)
    정답 대비 법선 각도 차 = 39.8 arcsec, 광축상 거리 차 = 2.8 µm
    특이값 비 s1/s2 = 3572  (클수록 평면이 잘 정해짐)
[2] (나쁜 예) 8개 자세를 모두 같은 높이(0 mm), 거의 수평(±1°)으로 둔 경우
    잔차 RMS = 1.28 µm 인데도 법선 각도 차 = 76 arcsec, s1/s2 = 29  → 잔차만 보면 속는다!
[3] 검증: 높이 0 / 5 / 10 mm 수평 평판을 두 평면(좋은 예·나쁜 예)으로 측정
    z =  0.0 mm | 좋은 예: 평균 오차   -2.4 µm, 기울기 P-V   1.3 µm | 나쁜 예:   -0.2 µm, P-V   1.4 µm
    z =  5.0 mm | 좋은 예: 평균 오차   -0.9 µm, 기울기 P-V   1.2 µm | 나쁜 예:   -3.4 µm, P-V   1.3 µm
    z = 10.0 mm | 좋은 예: 평균 오차   +0.4 µm, 기울기 P-V   1.3 µm | 나쁜 예:   -6.3 µm, P-V   1.3 µm
저장: laser_plane.yaml, d2_points.npy, d2_plate_check.csv
```

**출력 읽는 법**
- [1] 잔차 1.10 µm, 5 mm 평판 오차 −0.9 µm. 합성 데이터에는 스펙클이 없어 실제보다 작습니다. 실제는 잔차 3~5 µm 를 예상합니다(BLUEPRINT I1 예시 3 µm).
- [2] 잔차(1.28 µm)만 보면 [1]과 비슷하지만 `s1/s2` 가 3572 → 29 로 크게 떨어지고, 10 mm 높이에서 −6.3 µm 오차가 납니다. **자세 높이를 다양하게** 해야 하는 이유입니다.
- [3] 0 mm 에서는 나쁜 예도 정확합니다. 보드를 놓았던 높이에서만 맞고 멀어질수록 틀어지는 것이 퇴화의 전형적 증상입니다.

### 6.2 단위 테스트 (`test_d2_triangulation.py`, pytest)
J3 의 "삼각측량: 알려진 평면 위 점을 투영한 합성 픽셀 → 원래 3D 점 복원" 테스트입니다.

```python
"""D2 단위 테스트: 레이저 평면 위의 알려진 3D 점 → 픽셀로 투영 → 다시 3D 로 복원 (J3)"""
import numpy as np
import cv2
from d2_laser_plane import K, DIST, N_TRUE, D_TRUE, pixels_to_rays, intersect_rays_plane, fit_plane


def test_pixel_roundtrip():
    rng = np.random.default_rng(0)
    a = np.cross(N_TRUE, [1.0, 0, 0]); a /= np.linalg.norm(a)
    b = np.cross(N_TRUE, a)
    p0 = np.array([0, 0, -D_TRUE / N_TRUE[2]])             # 광축이 레이저 평면과 만나는 점 (FOV 중앙)
    P = p0 + rng.uniform(-8, 8, (200, 1)) * a + rng.uniform(-8, 8, (200, 1)) * b
    uv, _ = cv2.projectPoints(P, np.zeros(3), np.zeros(3), K, DIST)
    uv = uv.reshape(-1, 2)
    Q = intersect_rays_plane(pixels_to_rays(uv[:, 0], uv[:, 1]), N_TRUE, D_TRUE)
    assert np.abs(Q - P).max() < 1e-4                      # 0.1 µm 이내로 복원


def test_fit_plane_exact():
    rng = np.random.default_rng(1)
    P = np.c_[rng.uniform(-5, 5, (100, 2)), np.zeros(100)] + [0, 0, 120]
    n, d, s = fit_plane(P)
    assert abs(abs(n[2]) - 1) < 1e-12 and abs(abs(d) - 120) < 1e-9
```

```
$ python3 -m pytest -q test_d2_triangulation.py
2 passed
```

### 6.3 실제 데이터에 적용할 때 바꿀 부분
- `K`, `DIST` → `yaml.safe_load(open("camera_intrinsics.yaml"))` 의 `camera_matrix`, `dist_coeffs` 로 교체
- `make_corner_pixels` → 레이저 끈 사진에서 `cv2.findChessboardCornersSB` (또는 ChArUco 검출, D1 6.2)
- `make_laser_image` → `cv2.imread("pose_00_on.png", cv2.IMREAD_GRAYSCALE)`. 배경 차감을 하려면 `cv2.subtract(on, off)` 를 먼저 적용 (C5)
- `extract_laser_line` 의 `threshold`, `half_win` 은 **F1 과 같은 값**을 설정 파일(J2)에서 읽기

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 | 6.1 합성 결과 |
|---|---|---|---|
| 평면 맞춤 잔차 RMS | `res.std()` | **< 5 µm** (목표 Z 정밀도의 절반 이하) | 1.10 µm |
| 자세 높이 범위 | `poses.csv` | 측정 깊이 범위의 ≥ 80 % (예: 12 mm 중 ≥ 9.6 mm) | 12 mm (−2 ~ +10) |
| 퇴화 지표 | 특이값 비 s1/s2 | 같은 장치에서 기록한 이전 값의 50 % 이상 (참고 지표) | 3572 |
| 평판 높이 검사 | 0 / 5 / 10 mm 평판 평균 오차 | \|오차\| < 5 µm (각 높이) | −2.4 / −0.9 / +0.4 µm |
| 폭 방향 기울기 | 평판 높이의 x 방향 1차 맞춤 P-V | < 5 µm | 1.3 µm |
| 단위 테스트 | pytest | 모두 통과 | 2 passed |
| 최종 | D5 게이지 블록 단차 | < 10 µm | D5 참조 |

**완료 판정**: 위 표가 모두 합격하고 `laser_plane.yaml` 이 D1 과 같은 ID 폴더에 저장되면 완료 (M1 의 두 번째 조건).

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 모든 자세를 같은 높이에 둠 | 잔차는 작은데 높은 곳에서 높이가 틀림 | 높이 −2 ~ +10 mm 고르게, s1/s2 확인 |
| 레이저 끈/켠 사진 사이에 보드가 움직임 | 그 자세 잔차만 큼 (수십 µm) | 보드 고정, 같은 자세 재촬영. 자세별 평균 잔차 확인 |
| 레이저가 검은 칸을 지나감 | 선이 끊기거나 중심이 밀림 | 흰 영역 위로 지나가게 배치 (D2-5) |
| 레이저 피크 포화 | 잔차가 크고 줄무늬 형태 오차 | 노출·출력을 낮춰 피크 60~90 % |
| D1 과 다른 광학 상태 | D5 에서 일정 비율 높이 오차 | 같은 초점·조리개·필터. 바뀌면 D1 부터 다시 |
| 측정 때와 다른 라인 추출 알고리즘 사용 | 측정값에 계통 오차 | F1 과 같은 함수·파라미터 사용 |
| 평면 부호 혼동 (n, d 둘 다 뒤집힘) | 다른 코드에서 거리 부호 반대 | n_z < 0 규칙 (D2-9), YAML 에 명시 |
| `undistortPoints` 빠뜨림 | 영상 가장자리에서 높이 휨 | `pixels_to_rays` 함수만 사용 |
| 워밍업 없이 바로 촬영 | 레이저 지향이 흔들려 자세 간 불일치 | 30분 워밍업 (B6) |

---

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 스펙클로 잔차가 5 µm 를 넘음 | 중 | 높음 | 무광 흰 타깃 사용, 레이저 켠 사진 5장 평균은 효과 제한적(F2). 보드 미세 이동 촬영 평균 고려 |
| 보드 표면과 인쇄층 두께 차이 | 중 | 중 | 레이저가 닿는 면과 코너 인쇄면이 같은 높이인지 확인 (인쇄층 두께 수 µm) |
| 레이저 평면이 시간에 따라 기욺 (마운트 열변형) | 중 | 높음 | 레이저 마운트 단단히, 일일 점검(D5 관리도) |
| 피사계 심도 밖 자세 | 중 | 중 | 기울기 ±15°, 높이 범위를 실제 측정 범위로 제한 |
| 레이저 안전사고 | 낮음 | 매우 높음 | Class 2, 반사 보드 각도 주의 (C8) |

---

## 10. 기록 양식

`config/calibration/CAL-2026-11-24-A/d2_record.yaml`

```yaml
calibration_id: CAL-2026-11-24-A
element: D2
date: 2026-11-27
operator: ""
room_temp_C: null
laser: {wavelength_nm: null, power_pct: null, warmup_min: 30}
exposure_us: null
line_extraction: {method: cog, threshold: 30, half_win: 5}   # F1 과 동일해야 함
poses:            # 자세마다 한 줄
  - {pose: 0, spacer_mm: -2, tilt_deg: [0, 0], n_points: null, mean_res_um: null}
result:
  plane_normal: [null, null, null]
  plane_d_mm: null
  fit_rms_um: null
  s1_over_s2: null
plate_check_um: {z0: null, z5: null, z10: null}
decision: ""
notes: ""
```

`d2/poses.csv`

| pose | spacer_mm | tilt_x_deg | tilt_y_deg | off_image | on_image | n_points | mean_res_um | 비고 |
|---|---|---|---|---|---|---|---|---|
| 0 | −2 | 0 | 0 | pose_00_off.png | pose_00_on.png |  |  |  |

---

## 11. 참고 자료

- OpenCV 공식 문서: `solvePnP`, `undistortPoints` (calib3d 모듈), "Camera Calibration" 튜토리얼
- Z. Zhang, "A Flexible New Technique for Camera Calibration" (2000) — 보드 자세 추정의 기초
- 구조광/레이저 선 센서 캘리브레이션 교과서 주제: "line-structured light sensor calibration", "light-plane calibration with planar target"
- 최소제곱 평면 맞춤과 SVD (선형대수 교과서의 total least squares)
- C. Steger, "An Unbiased Detector of Curvilinear Structures" (1998) — F1 의 고급 라인 중심 추출
- 상위 기준: [BLUEPRINT.md D2, B1, F1](../../BLUEPRINT.md)
