# D1. 카메라 내부 캘리브레이션

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: D. 캘리브레이션

| 항목 | 내용 |
|---|---|
| 기간 | 2026-11-17 ~ 2026-11-30 (W7-8) |
| 우선순위 | 높음 |
| 트랙 | 하드웨어 |
| 선행 요소 | [B4 카메라](../B-optics/B4-camera.md) · [B5 렌즈](../B-optics/B5-lens.md) · [B7 광학 필터](../B-optics/B7-filter.md) · [C4 좌표계 체계](../C-mechanics/C4-coordinate-frames.md) |
| 후행 요소 | [D2 레이저 평면](D2-laser-plane.md) · [F1 레이저 라인 중심 추출](../F-acquisition/F1-line-extraction.md) · [D5 검증·이력 관리](D5-calibration-verification.md) · [I1 측정 불확도](../I-reliability/I1-uncertainty.md) |
| 관련 마일스톤 | **M1** — 재투영 오차 < 0.2 px, 레이저 평면 잔차 < 5 µm |

---

## 1. 목적

카메라와 렌즈가 가진 고유한 성질(초점거리, 영상 중심, 렌즈 왜곡)을 숫자로 구해서, **영상 속 픽셀 하나를 "카메라에서 나가는 정확한 광선(빛의 직선)" 으로 바꿀 수 있게** 만드는 것이 목적입니다.

- 이 결과(K 행렬 + 왜곡계수)가 없으면 D2에서 레이저 평면을 구할 수 없고, 픽셀이 3D 점이 되지 않습니다.
- 렌즈 왜곡을 보정하지 않으면 영상 가장자리에서 높이가 휘어 보입니다. 평평한 판이 "그릇 모양"으로 측정되는 식입니다.
- 이 요소가 끝나면 `camera_intrinsics.yaml` 한 파일이 남고, 이후 모든 삼각측량 계산이 이 파일을 읽습니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 핀홀 카메라 모델
카메라를 "바늘구멍 하나 + 뒤쪽 스크린"으로 단순화한 모델입니다. 카메라 좌표계 {C}에서 3D 점 (X, Y, Z)가 영상 픽셀 (u, v)로 가는 식은 다음과 같습니다.

```
x = X / Z,   y = Y / Z                 ← 정규화 좌표 (깊이로 나눔)
(x, y) → 렌즈 왜곡 적용 → (x_d, y_d)
u = fx · x_d + cx
v = fy · y_d + cy
```

| 기호 | 이름 | 의미 | 이 과제 예상값 (B1 예시 부품) |
|---|---|---|---|
| fx, fy | 초점거리 [px] | 렌즈 초점거리 ÷ 픽셀 크기 | 25 mm ÷ 3.45 µm ≈ **7246 px** |
| cx, cy | 영상 중심(주점) [px] | 광축이 센서와 만나는 점 | 영상 중앙(720, 540) 근처, ±수십 px |
| k1, k2, k3 | 방사 왜곡 | 중심에서 멀어질수록 휘는 정도 (술통형·실패형) | 저왜곡 렌즈는 \|k1\| ≈ 0.01~0.3 |
| p1, p2 | 접선 왜곡 | 렌즈가 센서와 살짝 기울어 생기는 왜곡 | 10⁻⁴ 수준 |

이 값들을 3×3 행렬로 묶은 것이 **카메라 행렬 K** 입니다.

```
K = [[fx,  0, cx],
     [ 0, fy, cy],
     [ 0,  0,  1]]
```

### 2.2 왜곡의 크기 감 잡기
방사 왜곡은 `x_d = x · (1 + k1·r² + k2·r⁴ + k3·r⁶)` 꼴입니다(r = 중심으로부터의 정규화 거리).
- 이 과제 카메라는 초점거리가 길어서(7246 px) 영상 구석에서도 r ≈ 900/7246 ≈ **0.12** 밖에 안 됩니다.
- k1 = −0.12 이면 구석에서 위치가 k1·r² ≈ −0.19 % → 약 **1.7 px** 밀립니다.
- B1 계산에서 픽셀 1개 이동 = 높이 약 **27.6 µm** 이므로, 왜곡 1.7 px 를 무시하면 구석에서 수십 µm 높이 오차가 생깁니다.
- 반대로 r 이 작으니 r⁴, r⁶ 항(k2, k3)은 거의 영향이 없고 **데이터로 구분해 낼 수도 없습니다.** 그래서 k2, k3 는 0 으로 고정하는 것을 권장합니다(4장 결정 D1-3).

### 2.3 재투영 오차 (Reprojection error)
캘리브레이션 결과로 보드 코너의 3D 좌표를 다시 영상에 투영했을 때, 실제 검출된 코너 위치와 몇 픽셀 차이 나는지의 RMS입니다.
- **< 0.2 px** 좋음, **< 0.5 px** 허용 (BLUEPRINT D1 기준).
- 0.2 px 는 높이로 환산하면 대략 0.2 × 27.6 ≈ 5.5 µm 수준의 "광선 방향 오차"입니다.
- **주의**: 재투영 오차가 작다고 결과가 정확하다는 보장은 없습니다. 사진이 한쪽에만 몰려 있으면 오차는 작게 나와도 영상 다른 곳에서는 틀립니다. 그래서 **커버리지**와 **hold-out(캘리브레이션에 안 쓴 사진) 검사**를 함께 봅니다.

### 2.4 Zhang 방법 — 평평한 보드를 여러 각도로 찍는 이유
평평한 판 위의 점들은 Z = 0 이라서 판과 영상 사이가 "호모그래피"(3×3 행렬)로 연결됩니다. 서로 다른 기울기의 사진이 3장 이상이면 K를 풀 수 있고, 실제로는 20~40장을 찍어 최소제곱으로 정밀하게 구합니다. OpenCV `cv2.calibrateCamera` 가 이 방법을 구현합니다.

### 2.5 체커보드 vs ChArUco
| 타깃 | 특징 |
|---|---|
| 체커보드 | 단순. 단, **보드 전체가 사진 안에 다 들어와야** 검출됨. 칸 수는 한쪽 짝수·한쪽 홀수(예: 9×6 칸)로 해서 180° 회전 모호성을 피함 |
| **ChArUco** (권장) | 체커보드 흰 칸에 ArUco 마커가 들어 있어 **일부만 보여도** 코너 번호를 앎 → 영상 구석까지 코너를 채우기 쉬움 |

### 2.6 이 과제에서 특히 중요한 것: 보드 칸 크기의 정확도
보드 칸 크기(예: 1.500 mm)가 0.1 % 틀리면 K는 거의 변하지 않지만, **보드까지의 거리(자세)가 0.1 % 틀려지고**, 이 자세로 구하는 D2 레이저 평면 → 최종 높이도 약 0.1 % 틀어집니다 (10 mm 단차에서 10 µm). 그래서 보드 칸 크기는 **인쇄 명목값이 아니라 실측값**을 쓰고, 최종 확인은 D5 게이지 블록으로 합니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식·위치 | 설명 |
|---|---|---|---|
| 입력 | 캘리브레이션 타깃 | ChArUco 9×6 칸, 칸 1.5 mm, 마커 1.1 mm (권장) | 유리·세라믹 등 평평한 기판. 칸 크기 실측값 기록 |
| 입력 | 보드 사진 | `data/raw/calib/CAL-2026-11-24-A/d1_views/view_000.png` … (25~40장) | 8-bit 또는 16-bit **무압축 PNG**. JPEG 금지 |
| 입력 | 렌즈 상태 기록 | 초점·조리개 잠금, 필터 장착 사진 | 측정 때와 같은 상태여야 함 |
| 산출물 | **카메라 내부 파라미터** | `config/calibration/CAL-2026-11-24-A/camera_intrinsics.yaml` | K, 왜곡계수, RMS, 사진 수, 보드 사양, 렌즈 상태 |
| 산출물 | 사진별 오차표 | `.../d1_per_view.csv` (열: view, rms_px, used) | 제외한 사진과 이유 |
| 산출물 | 커버리지 그림 | `.../d1_coverage.png` | 모든 코너를 한 영상에 찍은 산점도 |
| 산출물 | 기록지 | 10장 양식 (YAML) | 날짜, 온도, 담당, 판정 |

---

## 4. 결정 사항

| ID | 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|---|
| D1-1 | 타깃 종류 | 체커보드 / **ChArUco** / 원형 격자 | ChArUco | 부분 가림에도 검출 → FOV 구석까지 코너 확보 |
| D1-2 | 타깃 크기·칸 크기 | 칸 1.0 / **1.5** / 2.0 mm | 9×6 칸 × 1.5 mm (13.5 × 9 mm) | FOV(약 20 × 15 mm)의 60~70 %. 영상에서 칸 하나 ≈ 108 px 로 코너 검출이 안정 |
| D1-3 | 왜곡 모델 | 5계수 전부 / **k1, p1, p2 (k2=k3=0 고정)** / 8계수 | k1, p1, p2 | 장초점 렌즈라 r ≤ 0.12, k2·k3 는 구분 불가. 시험에서 k2 를 풀면 k1 이 정답 −0.120 대신 −0.176 으로 틀어짐 |
| D1-4 | 사진 수 | 15 / **25** / 40 | 25장 (+ hold-out 5장) | 20장 미만이면 파라미터 표준편차가 커짐 |
| D1-5 | 자세 분포 | – | 3×3 위치 × 기울기 3종(0°, ±15°, ±30°) | 중앙·구석·기울기 모두 포함해야 fx 와 cx·왜곡이 분리됨 |
| D1-6 | 조명 | 실내등 / **레이저와 같은 파장의 확산 LED** | 확산 LED | 대역통과 필터를 단 채로 찍어야 하므로 |
| D1-7 | 노출 | – | 흰 칸 밝기 = 최대값의 70~90 %, 포화 픽셀 0 % | 포화되면 코너 위치가 밀림 |
| D1-8 | 칸 크기 값 | 인쇄 명목값 / **실측값** | 실측(측정 현미경·영상측정기 등으로 전체 피치 측정) | 칸 크기 오차가 그대로 높이 배율 오차가 됨 (2.6절) |

---

## 5. 수행 절차

1. **준비 (W7 첫 주, 약 1일)**
   - [ ] 카메라·레이저 전원 켜고 **30분 워밍업** (C6)
   - [ ] 측정용 초점 맞춤 → 초점·조리개 잠금 나사 고정 → 테이프로 위치 표시 (B5). 조리개 f/8 권장
   - [ ] 대역통과 필터 장착 상태 확인 (B7)
   - [ ] 타깃 칸 크기 실측: 양 끝 코너 간 거리(약 12 mm)를 재서 칸 크기 = 거리 ÷ 칸 수. 3회 평균, 0.001 mm 단위 기록
   - [ ] 타깃 평면도 확인: 정반 위에 놓고 다이얼 게이지나 하이트 게이지로 9점 측정, P-V ≤ 10 µm
2. **촬영 계획**
   - [ ] FOV 를 3×3 칸으로 나누고 각 칸 중심에 보드 중심을 두는 위치 9곳
   - [ ] 위치마다 기울기 3종: 수평, X축 ±15~30°, Y축 ±15~30° → 27장 + hold-out 5장
   - [ ] 측정 깊이 범위(예: 0~10 mm) 안에서 높이도 바꾸기 (스페이서 사용)
3. **촬영**
   - [ ] 사진마다 흰 칸 밝기 70~90 %, 포화 0 % 확인 (6.3 코드가 자동 표시)
   - [ ] 손으로 들고 찍지 말 것 — 스탠드에 고정 후 촬영 (흔들림 = 코너 번짐)
   - [ ] 파일명 `view_000.png` … 순번, 자세 메모를 CSV에 기록
4. **코너 검출 및 1차 계산**
   - [ ] 6.1 코드 실행 → 사용 가능한 사진 수 ≥ 20, 커버리지 ≥ 90 %
   - [ ] `cv2.calibrateCameraExtended` 로 K, dist, 사진별 RMS 계산
5. **이상 사진 제거 후 재계산**
   - [ ] 사진별 RMS 가 0.5 px 초과 또는 중앙값의 2배 초과인 사진 제외 (최대 20 %까지만)
   - [ ] 재계산 → RMS < 0.2 px 확인
6. **독립 검증**
   - [ ] hold-out 5장으로 재투영 RMS 계산 → 캘리브레이션 RMS 의 1.5배 이하
   - [ ] fx 표준편차가 fx 의 0.2 % 이하 (예: 7246 px 에서 ≤ 14 px)
7. **저장과 기록**
   - [ ] YAML 저장, 캘리브레이션 ID 부여 (`CAL-YYYY-MM-DD-A`)
   - [ ] 10장 기록지 작성, 원본 사진은 `data/raw` 에 보관 (수정 금지)
   - [ ] 2주 안에 같은 절차를 한 번 더 하여 재현성 확인 (fx 차이 < 0.3 %)

---

## 6. Python 구현

필요 라이브러리: `numpy`, `opencv-python-headless`(또는 `opencv-python`), `pyyaml`. 아래 코드는 모두 하드웨어 없이 실행해 확인했습니다 (OpenCV 5.0, numpy 2.x).

### 6.1 합성 체커보드로 전체 과정 실행 (`d1_camera_calib.py`)
"정답을 아는 가짜 카메라"로 체커보드 사진 25장을 그린 뒤, OpenCV 가 정답을 되찾는지 확인합니다. 렌즈 왜곡까지 포함해 그리기 때문에 실제와 같은 코드 경로를 탑니다.

```python
"""
D1. 카메라 내부 캘리브레이션 — 합성(가짜) 체커보드 영상으로 끝까지 실행해 보는 예제
-------------------------------------------------------------------------------
* 하드웨어 없이 실행됩니다. "정답 카메라"(K_true, dist_true)로 체커보드 사진 25장을
  컴퓨터로 그린 뒤, OpenCV 캘리브레이션이 그 정답을 되찾는지 확인합니다.
* 실제 실험에서는 render_view() 대신 cv2.imread() 로 찍은 사진을 읽으면 됩니다.
실행:  python3 d1_camera_calib.py
"""
import numpy as np
import cv2
import yaml

rng = np.random.default_rng(42)          # 난수 시드 고정 → 매번 같은 결과 (J2 재현성)

# ---------------------------------------------------------------- 1. 정답 카메라 (합성용)
W, H = 1440, 1080                         # 영상 크기 [px] (BLUEPRINT B1 예시 카메라)
PIX_MM = 0.00345                          # 픽셀 크기 3.45 µm
F_MM = 25.0                               # 렌즈 초점거리 25 mm
fx = fy = F_MM / PIX_MM                   # 초점거리를 픽셀 단위로 → 약 7246 px
K_TRUE = np.array([[fx, 0, W / 2 + 3.2],
                   [0, fy, H / 2 - 4.5],
                   [0, 0, 1]])
DIST_TRUE = np.array([-0.12, 0.0, 2e-4, -1e-4, 0.0])   # k1, k2, p1, p2, k3

# ---------------------------------------------------------------- 2. 체커보드 정의
SQUARES = (9, 6)                          # 칸 수 (가로 9, 세로 6) → 한쪽은 홀수: 180° 회전 모호성 방지
INNER = (SQUARES[0] - 1, SQUARES[1] - 1)  # 내부 코너 수 (8, 5) ← OpenCV에는 이 값을 넘김
SQ_MM = 1.5                               # 한 칸 크기 1.5 mm (FOV 약 20 x 15 mm 에 맞춤)
TEX_MM_PER_PX = 0.01                      # 그림용 텍스처 해상도 10 µm/px
MARGIN_MM = 1.5                           # 보드 바깥 흰 여백 (검출에 필요)


def make_checkerboard_texture():
    """흰 여백이 있는 체커보드 그림(텍스처)을 만듦. 보드 좌표 (0,0) = 첫 내부 코너"""
    bw = SQUARES[0] * SQ_MM + 2 * MARGIN_MM
    bh = SQUARES[1] * SQ_MM + 2 * MARGIN_MM
    tw, th = int(round(bw / TEX_MM_PER_PX)), int(round(bh / TEX_MM_PER_PX))
    xs = (np.arange(tw) + 0.5) * TEX_MM_PER_PX - MARGIN_MM   # 텍스처 픽셀 → 보드 mm (왼쪽 위 모서리 기준)
    ys = (np.arange(th) + 0.5) * TEX_MM_PER_PX - MARGIN_MM
    X, Y = np.meshgrid(xs, ys)
    inside = (X >= 0) & (X < SQUARES[0] * SQ_MM) & (Y >= 0) & (Y < SQUARES[1] * SQ_MM)
    black = ((np.floor(X / SQ_MM) + np.floor(Y / SQ_MM)) % 2 == 0) & inside
    tex = np.full((th, tw), 230, np.float32)   # 흰색 230 (포화 방지)
    tex[black] = 25                            # 검정 25
    return tex


def board_object_points():
    """보드 좌표계(mm)에서 내부 코너의 3D 좌표. Z = 0 (평평한 판)"""
    obj = np.zeros((INNER[0] * INNER[1], 3), np.float32)
    gx, gy = np.meshgrid(np.arange(INNER[0]), np.arange(INNER[1]))
    obj[:, 0] = (gx.ravel() + 1) * SQ_MM       # 첫 내부 코너 = 칸 1개 안쪽
    obj[:, 1] = (gy.ravel() + 1) * SQ_MM
    return obj


def render_view(tex, rvec, tvec, K, dist, blur_sigma=0.8, noise_sigma=2.0):
    """카메라 픽셀마다 '어느 보드 지점이 보이는지' 역추적해서 사진을 그림 (렌즈 왜곡 포함)"""
    u, v = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64))
    pts = np.stack([u.ravel(), v.ravel()], axis=1).reshape(-1, 1, 2)
    xy = cv2.undistortPoints(pts, K, dist).reshape(-1, 2)          # 왜곡 제거한 정규 좌표
    rays = np.hstack([xy, np.ones((len(xy), 1))])                  # 광선 방향 (x, y, 1)
    R, _ = cv2.Rodrigues(rvec)
    n, t = R[:, 2], tvec.ravel()                                   # 보드 평면 법선, 보드 원점
    lam = (n @ t) / (rays @ n)                                     # 광선-보드 평면 교점 거리
    Xc = rays * lam[:, None]                                       # 카메라 좌표계 3D 점
    Xb = (Xc - t) @ R                                              # 보드 좌표계로 (R^T (X - t))
    map_x = ((Xb[:, 0] + MARGIN_MM) / TEX_MM_PER_PX - 0.5).reshape(H, W).astype(np.float32)
    map_y = ((Xb[:, 1] + MARGIN_MM) / TEX_MM_PER_PX - 0.5).reshape(H, W).astype(np.float32)
    img = cv2.remap(tex, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=120)
    img = cv2.GaussianBlur(img, (0, 0), blur_sigma)                # 렌즈 흐림
    img = img + rng.normal(0, noise_sigma, img.shape)              # 센서 노이즈
    return np.clip(img, 0, 255).astype(np.uint8)


def synthetic_poses(n_views=25):
    """FOV 중앙·모서리, 기울기 ±30° 를 고루 섞은 보드 자세 (rvec, tvec) 목록"""
    poses = []
    cx_b, cy_b = SQUARES[0] * SQ_MM / 2, SQUARES[1] * SQ_MM / 2      # 보드 중심 (보드 좌표)
    for i in range(n_views):
        ax = np.radians(rng.uniform(-30, 30))                        # X축 기울기
        ay = np.radians(rng.uniform(-30, 30))                        # Y축 기울기
        az = np.radians(rng.uniform(-10, 10))                        # 화면 내 회전
        R = cv2.Rodrigues(np.array([ax, 0, 0]))[0] @ cv2.Rodrigues(np.array([0, ay, 0]))[0] \
            @ cv2.Rodrigues(np.array([0, 0, az]))[0]
        centre = np.array([rng.uniform(-2.5, 2.5), rng.uniform(-1.5, 1.5), rng.uniform(122, 128)])
        t = centre - R @ np.array([cx_b, cy_b, 0.0])                 # 보드 중심이 centre 에 오도록
        poses.append((cv2.Rodrigues(R)[0], t.reshape(3, 1)))
    return poses


def detect_corners(img):
    """체커보드 내부 코너를 서브픽셀로 검출. 실패하면 None"""
    ok, corners = cv2.findChessboardCornersSB(img, INNER, flags=cv2.CALIB_CB_ACCURACY)
    return corners.reshape(-1, 2).astype(np.float32) if ok else None   # 모양 (N, 2) 로 통일


def coverage_percent(all_corners, grid=(4, 3)):
    """영상을 4x3 칸으로 나눴을 때 코너가 한 번이라도 찍힌 칸의 비율(%)"""
    pts = np.vstack([c.reshape(-1, 2) for c in all_corners])
    gx = np.clip((pts[:, 0] / W * grid[0]).astype(int), 0, grid[0] - 1)
    gy = np.clip((pts[:, 1] / H * grid[1]).astype(int), 0, grid[1] - 1)
    return 100.0 * len(set(zip(gx, gy))) / (grid[0] * grid[1])


def main():
    tex = make_checkerboard_texture()
    obj = board_object_points()
    obj_list, img_list = [], []
    for i, (rvec, tvec) in enumerate(synthetic_poses(25)):
        img = render_view(tex, rvec, tvec, K_TRUE, DIST_TRUE)
        if i == 0:
            cv2.imwrite("d1_example_view.png", img)                  # 사진 한 장 저장 (눈으로 확인용)
        c = detect_corners(img)
        if c is None:
            print(f"view {i:02d}: 검출 실패 → 제외")
            continue
        obj_list.append(obj)
        img_list.append(c)
    print(f"사용한 사진: {len(img_list)} 장, 영상 커버리지: {coverage_percent(img_list):.0f} %")

    # ------------------------------------------------ 캘리브레이션
    # 장초점(25 mm) 저왜곡 렌즈는 영상 가장자리에서도 r 이 작아서 k2, k3 를 따로 구분해 낼 수 없음
    # → k2, k3 를 0 으로 고정하고 k1, p1, p2 만 추정 (결정 사항 D1-3)
    flags = cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3
    rms, K, dist, rvecs, tvecs, std_in, std_ex, per_view = cv2.calibrateCameraExtended(
        obj_list, img_list, (W, H), None, None, flags=flags)
    dist = dist.ravel()
    print(f"재투영 오차 RMS = {rms:.3f} px   (D1 기준: < 0.2 좋음, < 0.5 허용)")
    print(f"fx = {K[0,0]:.1f} (정답 {K_TRUE[0,0]:.1f}) ± {std_in[0,0]:.1f}")
    print(f"fy = {K[1,1]:.1f} (정답 {K_TRUE[1,1]:.1f}) ± {std_in[1,0]:.1f}")
    print(f"cx = {K[0,2]:.1f} (정답 {K_TRUE[0,2]:.1f}) ± {std_in[2,0]:.1f}")
    print(f"cy = {K[1,2]:.1f} (정답 {K_TRUE[1,2]:.1f}) ± {std_in[3,0]:.1f}")
    print(f"k1 = {dist[0]:+.4f} (정답 {DIST_TRUE[0]:+.4f}) ± {std_in[4,0]:.4f}")
    worst = int(np.argmax(per_view))
    print(f"사진별 RMS 최대 = {per_view.max():.3f} px (view {worst}) → 0.5 px 넘는 사진은 빼고 다시 계산")

    # ------------------------------------------------ 검증: 캘리브레이션에 안 쓴 새 사진 5장 (hold-out)
    errs, dz = [], []
    for rvec_t, tvec_t in synthetic_poses(5):
        c = detect_corners(render_view(tex, rvec_t, tvec_t, K_TRUE, DIST_TRUE))
        if c is None:
            continue
        ok, rv, tv = cv2.solvePnP(obj, c, K, dist)                  # 새 사진의 보드 자세 추정
        proj = cv2.projectPoints(obj, rv, tv, K, dist)[0].reshape(-1, 2)
        errs.append(np.sqrt(((proj - c) ** 2).sum(axis=1).mean()))
        # 보드 중심점까지의 거리(Z) 비교. 코너 번호 순서가 180° 뒤집혀 검출될 수 있으므로 '중심'으로 비교
        ctr = obj.mean(axis=0)
        z_est = (cv2.Rodrigues(rv)[0] @ ctr + tv.ravel())[2]
        z_true = (cv2.Rodrigues(rvec_t)[0] @ ctr + tvec_t.ravel())[2]
        dz.append(abs(z_est - z_true) * 1000)                       # [µm]
    print(f"hold-out 재투영 RMS 평균 = {np.mean(errs):.3f} px, 보드 거리(Z) 오차 최대 = {max(dz):.0f} µm")

    # ------------------------------------------------ 결과 저장 (YAML)
    out = {
        "calibration_id": "CAL-2026-11-24-A",
        "element": "D1",
        "image_size": [W, H],
        "camera_matrix": K.round(4).tolist(),
        "dist_coeffs": dist.round(6).tolist(),            # [k1, k2, p1, p2, k3]
        "dist_model": "k1,p1,p2 (k2,k3 fixed=0)",
        "rms_reprojection_px": round(float(rms), 4),
        "n_views": len(img_list),
        "board": {"type": "chessboard", "squares": list(SQUARES), "square_mm": SQ_MM},
        "lens_state": {"focus": "locked", "aperture": "f/8 locked", "filter": "bandpass 450nm"},
    }
    with open("camera_intrinsics.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False)
    print("저장: camera_intrinsics.yaml")


if __name__ == "__main__":
    main()
```

**실행 예시와 기대 출력** (약 30초 소요)

```
$ python3 d1_camera_calib.py
사용한 사진: 25 장, 영상 커버리지: 100 %
재투영 오차 RMS = 0.063 px   (D1 기준: < 0.2 좋음, < 0.5 허용)
fx = 7241.0 (정답 7246.4) ± 6.7
fy = 7241.0 (정답 7246.4) ± 6.3
cx = 730.9 (정답 723.2) ± 9.4
cy = 539.1 (정답 535.5) ± 6.0
k1 = -0.1233 (정답 -0.1200) ± 0.0074
사진별 RMS 최대 = 0.131 px (view 23) → 0.5 px 넘는 사진은 빼고 다시 계산
hold-out 재투영 RMS 평균 = 0.051 px, 보드 거리(Z) 오차 최대 = 97 µm
저장: camera_intrinsics.yaml
```

**출력 읽는 법**
- RMS 0.063 px → 기준 0.2 px 보다 충분히 작음 (합성 데이터라 실제보다 좋게 나옴; 실제는 0.1~0.3 px 예상).
- fx 가 정답과 5 px(0.07 %) 다르지만 표준편차 ±6.7 px 범위 안입니다. 장초점 렌즈에서는 fx 와 "보드까지의 거리"가 서로 잘 구분되지 않아 생기는 현상입니다.
- hold-out 보드 거리 오차 97 µm 는 바로 이 fx 오차(0.07 % × 125 mm ≈ 90 µm) 때문입니다. **D2 레이저 평면도 같은 K 로 구하므로 이 오차는 대부분 상쇄**되지만, 남는 영향은 D5 게이지 블록 검증으로 반드시 확인합니다.
- k1 = −0.1233 ± 0.0074 로 정답 −0.120 과 일치합니다. (k2 까지 풀면 −0.176 으로 틀어졌던 것이 결정 D1-3 의 근거입니다.)

### 6.2 ChArUco 버전 (`d1_charuco.py`, 권장 타깃)
6.1 파일과 같은 폴더에 두고 실행합니다. 렌더러를 재사용해 ChArUco 보드를 그립니다.

```python
"""
D1 보충: ChArUco 보드 버전 (권장 타깃). d1_camera_calib.py 와 같은 폴더에 두고 실행.
보드 일부가 화면 밖으로 나가도 보이는 코너만으로 캘리브레이션할 수 있다는 점이 장점.
실행:  python3 d1_charuco.py
"""
import numpy as np
import cv2
import d1_camera_calib as d1          # 합성 카메라·렌더러 재사용

SQ, MK = 1.5, 1.1                      # 칸 1.5 mm, ArUco 마커 1.1 mm
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
board = cv2.aruco.CharucoBoard((9, 6), SQ, MK, dictionary)
detector = cv2.aruco.CharucoDetector(board)

# 보드 그림 생성: 1 px = 10 µm → 여백(MARGIN 1.5 mm)을 포함해 d1 렌더러 텍스처 규격에 맞춤
px = int(round(SQ / d1.TEX_MM_PER_PX))
board_img = board.generateImage((9 * px, 6 * px), marginSize=0)
m = int(round(d1.MARGIN_MM / d1.TEX_MM_PER_PX))
tex = cv2.copyMakeBorder(board_img, m, m, m, m, cv2.BORDER_CONSTANT, value=255).astype(np.float32)
tex = 25 + tex / 255 * 205             # 검정 25, 흰색 230 (포화 방지)

obj_list, img_list = [], []
for rvec, tvec in d1.synthetic_poses(15):
    img = d1.render_view(tex, rvec, tvec, d1.K_TRUE, d1.DIST_TRUE)
    ch_corners, ch_ids, _, _ = detector.detectBoard(img)
    if ch_ids is None or len(ch_ids) < 12:          # 코너 12개 미만인 사진은 버림
        continue
    obj, imgp = board.matchImagePoints(ch_corners, ch_ids)   # 보드 3D 좌표 ↔ 영상 좌표 짝 맞추기
    obj_list.append(obj)
    img_list.append(imgp)

rms, K, dist, _, _ = cv2.calibrateCamera(obj_list, img_list, (d1.W, d1.H), None, None,
                                         flags=cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3)
print(f"ChArUco 사용 사진 {len(img_list)} 장, 재투영 RMS = {rms:.3f} px, "
      f"fx = {K[0,0]:.0f} (정답 {d1.K_TRUE[0,0]:.0f}), k1 = {dist.ravel()[0]:+.3f}")
```

```
$ python3 d1_charuco.py
ChArUco 사용 사진 15 장, 재투영 RMS = 0.133 px, fx = 7251 (정답 7246), k1 = -0.137
```

> OpenCV 4.7 이후(5.x 포함)는 `cv2.aruco.CharucoDetector` 와 `board.matchImagePoints` 를 씁니다. 인터넷의 오래된 예제(`cv2.aruco.interpolateCornersCharuco`, `calibrateCameraCharuco`)는 새 버전에서 동작하지 않을 수 있습니다.

### 6.3 실제 사진 폴더 읽기 (`d1_load_real.py`)
실제 실험에서는 렌더링 대신 사진 파일을 읽습니다. 사진마다 검출 성공 여부와 포화 비율을 출력합니다.

```python
"""
D1 보충: 실제로 찍은 사진 폴더(d1_views/*.png)를 읽어 코너를 검출하고 결과를 표로 남기는 부분.
d1_camera_calib.py 의 board_object_points, INNER 를 재사용합니다.
실행:  python3 d1_load_real.py d1_views
"""
import glob
import sys
import cv2
import numpy as np
import d1_camera_calib as d1

folder = sys.argv[1] if len(sys.argv) > 1 else "d1_views"
obj_list, img_list, names = [], [], []
for path in sorted(glob.glob(f"{folder}/*.png")):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)          # 반드시 흑백으로 읽기
    sat = (img >= 250).mean() * 100                       # 포화 픽셀 비율 [%]
    c = d1.detect_corners(img)
    print(f"{path}: 코너 {'검출' if c is not None else '실패'}, 포화 {sat:.2f} %, 최대 밝기 {img.max()}")
    if c is not None:
        obj_list.append(d1.board_object_points()); img_list.append(c); names.append(path)
print(f"사용 가능 사진 {len(img_list)} 장 (권장 20~40 장)")
```

```
$ python3 d1_load_real.py d1_views        # 6.1 이 저장한 d1_example_view.png 를 d1_views/view_000.png 로 복사해 시험
d1_views/view_000.png: 코너 검출, 포화 0.00 %, 최대 밝기 238
사용 가능 사진 1 장 (권장 20~40 장)
```

### 6.4 카메라에서 직접 촬영 — 예시 구조 (하드웨어 SDK 필요, 그대로 실행 불가)

```python
# 예시 구조: 제조사 SDK 이름·함수는 카메라마다 다르므로 실제 SDK 문서에 맞게 바꿀 것
# cam = vendor_sdk.open_first_camera()
# cam.set("ExposureTime", 2000)       # µs, 흰 칸이 최대값의 70~90 %가 되도록
# cam.set("Gain", 0)                  # 게인은 0 (노이즈 최소)
# cam.set("PixelFormat", "Mono8")     # 또는 Mono12 → 16-bit PNG 로 저장
# for i in range(32):
#     input(f"{i}번 자세로 보드를 놓고 Enter")
#     img = cam.grab()                # numpy 2D 배열
#     cv2.imwrite(f"d1_views/view_{i:03d}.png", img)
```

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 | 6.1 합성 결과 |
|---|---|---|---|
| 재투영 오차 RMS | `calibrateCameraExtended` 반환값 | **< 0.2 px** (허용 < 0.5 px) | 0.063 px |
| 사진별 최대 RMS | `perViewErrors` | < 0.5 px 이고 중앙값의 2배 이하 | 0.131 px |
| 영상 커버리지 | 4×3 칸 중 코너가 찍힌 칸 비율 | ≥ 90 % | 100 % |
| hold-out 재투영 | 안 쓴 사진 5장, `solvePnP` 후 재투영 | ≤ 캘리브레이션 RMS × 1.5 | 0.051 px |
| 파라미터 불확도 | `stdDeviationsIntrinsics` | σ(fx)/fx ≤ 0.2 %, σ(cx), σ(cy) ≤ 15 px | 0.09 %, 9.4 px, 6.0 px |
| 재현성 | 독립 2회 캘리브레이션 비교 | fx 차이 < 0.3 %, k1 차이 < 0.02 | (실측 시 기록) |
| 최종 영향 | D2 → D5 게이지 블록 단차 | 오차 < 10 µm | D5 참조 |

**완료 판정**: 위 표의 앞 5개 항목이 모두 합격이고 YAML 파일과 기록지가 저장되면 D1 완료. 최종 확정은 D5 통과 시점입니다.

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 종이에 인쇄한 보드를 그냥 사용 | RMS 가 0.5 px 이상, 날마다 결과가 다름 | 유리·세라믹·금속 복합판 등 평평한 기판에 고정. 평면도 ≤ 10 µm 확인 |
| 캘리브레이션 후 초점·조리개를 만짐 | D5 단차 오차가 갑자기 커짐 | 잠금 나사 + 테이프 표시. 만졌으면 D1부터 다시 |
| 필터 없이 캘리브레이션하고 측정 때 필터 장착 | 수 µm~수십 µm 계통 오차 | 측정과 **완전히 같은 광학 상태**에서 촬영 (B7) |
| 보드를 영상 중앙에만 둠 | RMS 는 작은데 구석에서 높이가 휨 | 커버리지 ≥ 90 %, 구석 사진 필수 |
| 기울기 없이 정면 사진만 | fx, cx 가 불안정 (표준편차 큼) | ±15~30° 기울인 사진 포함 |
| 왜곡 계수를 모두 풀기 | 학습한 영역 밖에서 왜곡 보정이 크게 틀림 | k2, k3 고정 (D1-3) |
| JPEG 저장 | 코너가 블록 노이즈로 흔들림 | PNG/TIFF 무압축 |
| 흰 칸이 포화 | 코너가 검은 칸 쪽으로 밀림 | 흰 칸 70~90 %, 포화 0 % |
| `detect_corners` 결과 모양 혼동 ((N,1,2) vs (N,2)) | 오차가 수백 px 로 나오는 버그 | 코드처럼 `reshape(-1, 2)` 로 통일 |
| 칸 크기를 인쇄 명목값으로 입력 | 모든 높이가 일정 비율로 틀어짐 | 칸 크기 실측 (D1-8) |

---

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 평평하고 정밀한 소형 타깃 확보 지연 | 중 | 높음 | W5 까지 발주. 임시로 금속판에 인쇄 필름 부착 후 평면도·칸 크기 실측 |
| 대역통과 필터 때문에 보드가 너무 어두움 | 높음 | 중 | 레이저 파장 LED 확산 조명, 노출 시간 증가 |
| 피사계 심도가 얕아 기울인 보드 일부가 흐림 | 중 | 중 | 조리개 f/8~f/11, 기울기 ±20° 로 줄이고 사진 수 늘리기 |
| fx 와 거리의 상관(장초점) | 높음 | 중 | 깊이 방향으로도 보드 위치를 바꿈. 최종은 D5 로 확인 |
| 충격·온도로 렌즈가 미세하게 움직임 | 중 | 높음 | 일일 점검(D5 관리도), 재교정 조건 준수 |

---

## 10. 기록 양식

`config/calibration/CAL-2026-11-24-A/d1_record.yaml`

```yaml
calibration_id: CAL-2026-11-24-A
element: D1
date: 2026-11-24
operator: ""                # 이름
room_temp_C: null           # 0.1 °C 단위
warmup_min: 30
camera_serial: ""
lens: {focal_mm: 25, aperture: "f/8", focus_locked: true, tape_mark: true}
filter: {center_nm: null, fwhm_nm: null, installed: true}
target:
  type: charuco            # charuco | chessboard
  squares: [9, 6]
  square_nominal_mm: 1.5
  square_measured_mm: null  # 실측값 (평균 3회)
  flatness_pv_um: null
images: {captured: null, used: null, holdout: 5, folder: "data/raw/calib/CAL-2026-11-24-A/d1_views"}
result:
  rms_px: null
  max_view_rms_px: null
  coverage_pct: null
  holdout_rms_px: null
  fx_px: null
  fx_std_px: null
  k1: null
decision: ""                # 합격 / 재촬영
notes: ""
```

사진별 기록 `d1_per_view.csv`

| view | 위치(3×3) | 기울기 | 높이 [mm] | rms_px | used | 제외 사유 |
|---|---|---|---|---|---|---|
| 000 | 중앙 | 0° | 0 |  |  |  |
| 001 | 좌상 | X +20° | 0 |  |  |  |

---

## 11. 참고 자료

- OpenCV 공식 문서: "Camera Calibration" 튜토리얼 (calib3d 모듈), "Detection of ChArUco Boards" 튜토리얼
- Z. Zhang, "A Flexible New Technique for Camera Calibration", IEEE Transactions on Pattern Analysis and Machine Intelligence, 2000 (Zhang's method)
- R. Hartley, A. Zisserman, *Multiple View Geometry in Computer Vision* — 핀홀 모델, 호모그래피
- Brown–Conrady 렌즈 왜곡 모델 (방사·접선 왜곡)
- J.-Y. Bouguet, Camera Calibration Toolbox for MATLAB 문서 — 캘리브레이션 실무 팁(커버리지, 사진 수)
- 이 문서의 상위 기준: [BLUEPRINT.md D1, B1, B5](../../BLUEPRINT.md)
