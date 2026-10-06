# B5. 렌즈

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: B. 측정 원리·광학 설계

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-13 ~ 2026-11-02 (W2-4) |
| 우선순위 | 보통 |
| 트랙 | 하드웨어 |
| 선행 요소 | [B1 원리](B1-triangulation-principle.md) · [B2 기하 배치](B2-geometry.md) · [B4 카메라](B4-camera.md) (센서 크기·픽셀·마운트) |
| 후행 요소 | [B7 필터](B7-filter.md) (필터 나사 규격) · [D1 카메라 내부 캘리브레이션](../D-calibration/D1-camera-intrinsics.md) · [D2 레이저 평면](../D-calibration/D2-laser-plane.md) · [D5 검증·이력](../D-calibration/D5-calibration-verification.md) (재교정 조건) |
| 관련 마일스톤 | M0 (부품 목록 확정, 2026-10-19) · 렌즈 설치·잠금 2026-11-02 |

> B3 에서 상용 프로파일러를 골랐다면 렌즈는 내장되어 있으므로 이 문서는 **해당 없음**입니다. 다만 7절 "잠금 상태 점검"의 개념(기준 대상 정기 측정)은 D5·I2 에서 그대로 씁니다.

## 1. 목적

- B1·B2 에서 정한 작동거리(WD 125 mm)·FOV(약 20 mm)·조리개(f/8)를 만족하는 **C-마운트 저왜곡 머신비전 렌즈**를 고릅니다.
- 렌즈가 센서 픽셀(3.45 µm)을 충분히 분해하는지, 회절·왜곡이 측정에 주는 영향이 얼마인지 **숫자로** 확인합니다.
- 설치 후 **초점·조리개를 잠그고 표시**하며, "렌즈가 돌아가지 않았는지"를 영상으로 점검하는 절차를 만듭니다. 렌즈가 1° 라도 돌아가면 캘리브레이션을 다시 해야 하기 때문입니다 (BLUEPRINT B5).

## 2. 배경 지식 (초보자용)

### 2.1 렌즈 용어

| 용어 | 뜻 | 이 과제의 값 |
|---|---|---|
| 초점거리 f | 렌즈 굴절 능력. 클수록 좁고 크게 보임 | 25 mm |
| 작동거리 WD | 렌즈 앞~물체 거리(설계 계산에서는 근사로 렌즈 중심 기준) | 125 mm |
| 최소 촬영 거리 MOD | 렌즈가 초점을 맞출 수 있는 가장 가까운 거리 | **WD 125 mm 보다 짧아야 함** (사양서 확인) |
| 조리개 f/N | 빛이 들어오는 구멍 크기. N 이 클수록 구멍이 작음 | f/8 (B2) |
| 이미지 서클 | 렌즈가 선명하게 맺는 원의 지름 | 센서 대각(6.21 mm) 이상 |
| 왜곡 (distortion) | 직선이 휘어 보이는 정도, 가장자리에서 % | < 0.1 % 권장 |
| C-마운트 | 산업용 카메라 렌즈 나사 규격 (플랜지 거리 17.526 mm) | 카메라와 일치 |
| 필터 나사 | 렌즈 앞 필터를 돌려 끼우는 나사 지름 | B7 필터 주문에 필요 |

### 2.2 초점거리 고르는 공식

```
f ≈ WD × 센서크기 / (FOV + 센서크기)        (BLUEPRINT B5)
```

센서 가로 4.97 mm, WD 125 mm, FOV 20 mm → f ≈ 24.9 mm → 시판 **25 mm** 렌즈. 시판 초점거리는 정해진 값(12, 16, 25, 35, 50 mm 등)만 있으므로, 고른 뒤에는 **WD 를 미세 조정**해서 FOV 를 맞춥니다 (6.1절 표).

### 2.3 해상력과 회절

- 센서가 구별할 수 있는 가장 촘촘한 무늬는 **나이퀴스트 주파수** `1 / (2p)` = 145 lp/mm (3.45 µm 픽셀) 입니다. 렌즈가 이 정도를 분해하지 못하면 선이 뭉개집니다. 렌즈 사양서의 "대응 픽셀 크기" 또는 "MP 등급"을 확인합니다.
- 조리개를 조이면 **회절** 때문에 점이 퍼집니다. 퍼짐 원(에어리 원반) 지름 ≈ `2.44 · λ · N · (1 + M)`. 450 nm, f/8 에서 약 3.2 px, f/11 에서 4.4 px 입니다. 레이저 선 두께 목표(3~7 px, B6)와 비슷한 크기라서 **f/11 보다 더 조이는 것은 피합니다**.

### 2.4 왜곡과 캘리브레이션

- 왜곡 0.1 % 렌즈는 FOV 가장자리(중심에서 9.9 mm)에서 약 10 µm 위치가 틀어집니다. 이 오차는 D1 캘리브레이션이 대부분 보정하지만, **원래 왜곡이 작을수록 보정 잔차도 작습니다**.
- 왜곡 모형(OpenCV 의 k1, k2, p1, p2, k3)은 렌즈 상태(초점·조리개)마다 다릅니다. 그래서 캘리브레이션 뒤에는 렌즈를 건드리면 안 됩니다.

### 2.5 텔레센트릭 렌즈 (선택지)

물체 쪽 텔레센트릭 렌즈는 거리가 바뀌어도 배율이 그대로입니다. B1 에서 본 "높이 0 → 20 mm 에서 X 배율 16 % 변화" 같은 원근 효과가 없습니다. 단점: FOV 가 렌즈 앞 지름보다 작아야 하므로 FOV 20 mm 면 대구경이 필요하고, 크고 무겁고 비쌉니다(**견적 필요**). 기울어진 카메라에서는 Scheimpflug 조건과 함께 써야 효과가 큽니다. **1단계에서는 일반 고정 초점 렌즈 + 캘리브레이션**을 권장합니다.

### 2.6 파장과 초점

일반 머신비전 렌즈는 가시광 전체를 기준으로 설계됩니다. 405 nm 처럼 짧은 파장에서는 초점 위치가 조금 다르고(색수차) 투과율이 떨어질 수 있습니다. 그래서 **초점은 반드시 레이저 빛(필터 장착 상태)으로 맞춥니다**. 백색 조명으로 맞추고 레이저로 측정하면 선이 흐릴 수 있습니다.

## 3. 입력과 산출물

| 구분 | 항목 | 형식 / 파일 | 비고 |
|---|---|---|---|
| 입력 | 센서 크기·픽셀·마운트 | `config/hardware/camera.yaml` (B4) | 4.97×3.73 mm, 3.45 µm, C-마운트 |
| 입력 | WD·FOV·조리개·초점 높이 | `optical_design.yaml` (B1·B2) | 125 mm, 20 mm, f/8, Z 6 mm |
| 입력 | 레이저 파장 | B6 | 405 또는 450 nm |
| 산출물 | 렌즈 계산 스크립트 | `scripts/design/b5_lens.py` | 6.1절 |
| 산출물 | 잠금 점검 스크립트 | `scripts/checks/b5_lock_check.py` | 6.2절 |
| 산출물 | 렌즈 후보 비교표 | `results/design/B5_lens_candidates.csv` | 10절 |
| 산출물 | 렌즈 설치 기록 + 사진 | `config/hardware/lens.yaml`, `docs/photos/lens_lock_YYYYMMDD.jpg` | 잠금 나사·테이프 표시 사진 |
| 산출물 | 잠금 기준 영상 | `data/raw/reference/lens_lock_ref.png` | 정기 점검의 기준 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 렌즈 종류 | 고정 초점 C-마운트 / 줌 / 텔레센트릭 | **고정 초점 C-마운트 저왜곡** | 안정성(줌은 움직이는 부품 많음), 비용 |
| 초점거리 | 16 / 25 / 35 mm | **25 mm** | 6.1절: WD 125 에서 FOV 19.9 mm, dx 13.8 µm |
| 왜곡 | < 0.1 % / < 0.5 % | **< 0.1 %** | 가장자리 위치 오차 약 10 µm 이하 (보정 전) |
| 해상력 등급 | 픽셀 3.45 µm 대응 이상 | **3.45 µm(또는 더 작은 픽셀) 대응 표기 제품** | 나이퀴스트 145 lp/mm |
| 이미지 서클 | 센서 대각 이상 | **≥ 2/3" (약 11 mm)** 대응 | 센서 대각 6.21 mm, 주변부 화질 여유 |
| MOD | – | **≤ 100 mm** | WD 125 mm 에 여유. 부족하면 접사링 필요(배율·왜곡 바뀜) |
| 잠금 방식 | 잠금 나사 / 없음 | **초점·조리개 각각 잠금 나사 필수** | BLUEPRINT B5 |
| 운용 조리개 | f/4 ~ f/11 | **f/8** (필요 시 f/11) | B2 맞교환: 초점 범위 10.2 mm, 스펙클 11.5 µm |
| 텔레센트릭 | 1단계 / 2단계 검토 | **2단계 선택 사항** | 비용·크기. 원근은 D2 캘리브레이션으로 처리 |

## 5. 수행 절차

1. **계산과 사양 정리 (W2, 2026-10-13 ~ 10-14)**
   - [ ] 6.1절 스크립트를 실행해 이상 초점거리, 후보별 FOV·dx, 필요한 WD 를 확인한다.
   - [ ] "렌즈 최소 요구표" 작성: f 25 mm, C-마운트, 왜곡 < 0.1 %, 3.45 µm 대응, 이미지 서클 ≥ 센서 대각, MOD ≤ 100 mm, 조리개 범위에 f/8~f/11 포함, 초점·조리개 잠금 나사, 필터 나사 규격 표기.
2. **후보 비교와 선정 (W2, 10-14 ~ 10-16)**
   - [ ] 후보 2종 이상을 10절 표로 비교하고 사양서를 `docs/procurement/datasheets/` 에 저장한다.
   - [ ] 필터 나사 규격(예: M25.5, M27, M30.5 등 제품마다 다름)을 B7 담당에게 전달한다.
   - [ ] M0 회의에서 카메라와 함께 확정하고 주문한다 (K3 렌즈 범위 대략 20만~60만 원, **견적 필요**).
3. **수령 검사 (W3~W4)**
   - [ ] 마운트 체결, 잠금 나사 동작, 조리개 눈금 확인.
   - [ ] WD 125 mm 에서 초점이 맞는지 확인 (MOD 문제 없는지).
   - [ ] 격자·체커 타깃으로 왜곡 간이 확인: 화면 가장자리의 직선이 눈에 띄게 휘지 않는지 (정량은 D1).
4. **초점 맞추기와 잠금 (W4, B7 필터 장착 후, 2026-10-27 ~ 11-02)**
   - [ ] 카메라·렌즈·필터를 B2 배치대로 브래킷에 고정한다.
   - [ ] 조리개를 **f/8 로 맞추고 먼저 잠근다**.
   - [ ] 평판을 측정 깊이 중간 높이(Z ≈ 6 mm, B2)에 놓고 레이저를 켠 상태로, 이미지 속 선 두께(FWHM)가 가장 얇아지는 곳에 초점을 맞춘다.
   - [ ] 초점 링을 잠그고, 렌즈 링과 몸통에 **걸쳐서 테이프·페인트 마커로 선**을 긋는다 (돌아가면 선이 어긋나 보임). 사진을 찍어 저장한다.
   - [ ] 고정 타깃의 **잠금 기준 영상**(레이저 끔, 일정 조명)을 찍어 `lens_lock_ref.png` 로 저장한다.
5. **잠금 상태 점검 운영 (W5 이후 계속)**
   - [ ] 매 측정 세션 시작 시 같은 타깃을 같은 조건으로 찍고 6.2절 스크립트로 비교한다.
   - [ ] 이동 > 0.1 px 또는 선명도 변화 > 5 % 이면 원인(브래킷 충격, 렌즈 링 회전)을 확인하고 D5 재교정 조건으로 처리한다.
   - [ ] 결과를 D5 이력표에 1줄씩 기록한다.

## 6. Python 구현

### 6.1 렌즈 선택·해상력·왜곡 계산 (`b5_lens.py`)

```python
# b5_lens.py — 렌즈 초점거리 선택, 표준 초점거리 비교, 해상력·회절·왜곡 점검 (B5)
# 실행: python b5_lens.py
import numpy as np
import pandas as pd

pixel_um = 3.45
n_cols, n_rows = 1440, 1080
sensor_w = n_cols * pixel_um / 1000            # 센서 가로 [mm] = 4.97
sensor_h = n_rows * pixel_um / 1000            # 센서 세로 [mm]
sensor_diag = np.hypot(sensor_w, sensor_h)     # 대각선 → 렌즈 이미지 서클이 이보다 커야 함
WD = 125.0                                     # 목표 작동거리 [mm]
FOV_target = 20.0                              # 목표 측정 폭 [mm]
lam_um = 0.45                                  # 레이저 파장 [µm]

# 1) 공식으로 이상적인 초점거리 계산 (B5: f ≈ WD × 센서크기 / (FOV + 센서크기))
f_ideal = WD * sensor_w / (FOV_target + sensor_w)
print(f"센서 {sensor_w:.2f} x {sensor_h:.2f} mm, 대각 {sensor_diag:.2f} mm")
print(f"이상적 초점거리 f = {f_ideal:.1f} mm")

# 2) 시판 표준 초점거리 후보별 결과 (WD 고정 / FOV 고정 두 경우)
rows = []
for f in (12, 16, 25, 35, 50):
    M_fixwd = f / (WD - f)
    wd_for_fov = f * (FOV_target + sensor_w) / sensor_w     # FOV를 20 mm로 맞추려면 필요한 WD
    rows.append({
        "f [mm]": f,
        "WD=125 일 때 FOV [mm]": round(sensor_w / M_fixwd, 1),
        "WD=125 일 때 dx [um]": round(pixel_um / M_fixwd, 1),
        "FOV=20 맞추는 WD [mm]": round(wd_for_fov, 0),
    })
print(pd.DataFrame(rows).to_string(index=False))

# 3) 해상력 점검: 센서 나이퀴스트 vs 회절 차단 주파수 (이미지 쪽)
nyq = 1000 / (2 * pixel_um)                    # [lp/mm]
M = 25 / (WD - 25)
print(f"\n센서 나이퀴스트 주파수: {nyq:.0f} lp/mm (렌즈가 이 주파수를 분해하는지 사양서 확인)")
for N in (4, 8, 11, 16):
    n_eff = N * (1 + M)                         # 근접 촬영의 유효 F수
    cutoff = 1000 / (lam_um * n_eff)            # 회절 차단 주파수 [lp/mm]
    airy_px = 2.44 * lam_um * n_eff / pixel_um
    print(f"f/{N:<2}: 유효 F수 {n_eff:5.2f}, 회절 차단 {cutoff:4.0f} lp/mm, 에어리 원반 {airy_px:4.1f} px")

# 4) 왜곡이 X 위치에 주는 영향 (캘리브레이션 '전' 크기 → D1 으로 보정해야 하는 양)
half_fov = sensor_w / M / 2
for dist_pct in (0.05, 0.1, 0.5, 1.0):
    print(f"왜곡 {dist_pct:4.2f} % → FOV 가장자리({half_fov:.1f} mm)에서 X 오차 ≈ {half_fov * dist_pct / 100 * 1000:5.1f} um")
```

실행 예시와 기대 출력:

```
$ python b5_lens.py
센서 4.97 x 3.73 mm, 대각 6.21 mm
이상적 초점거리 f = 24.9 mm
 f [mm]  WD=125 일 때 FOV [mm]  WD=125 일 때 dx [um]  FOV=20 맞추는 WD [mm]
     12                 46.8                32.5                60.0
     16                 33.8                23.5                80.0
     25                 19.9                13.8               126.0
     35                 12.8                 8.9               176.0
     50                  7.5                 5.2               251.0

센서 나이퀴스트 주파수: 145 lp/mm (렌즈가 이 주파수를 분해하는지 사양서 확인)
f/4 : 유효 F수  5.00, 회절 차단  444 lp/mm, 에어리 원반  1.6 px
f/8 : 유효 F수 10.00, 회절 차단  222 lp/mm, 에어리 원반  3.2 px
f/11: 유효 F수 13.75, 회절 차단  162 lp/mm, 에어리 원반  4.4 px
f/16: 유효 F수 20.00, 회절 차단  111 lp/mm, 에어리 원반  6.4 px
왜곡 0.05 % → FOV 가장자리(9.9 mm)에서 X 오차 ≈   5.0 um
왜곡 0.10 % → FOV 가장자리(9.9 mm)에서 X 오차 ≈   9.9 um
왜곡 0.50 % → FOV 가장자리(9.9 mm)에서 X 오차 ≈  49.7 um
왜곡 1.00 % → FOV 가장자리(9.9 mm)에서 X 오차 ≈  99.4 um
```

읽는 법: 25 mm 렌즈는 WD 125 mm 에서 FOV 19.9 mm 로 목표에 맞습니다. FOV 를 정확히 20 mm 로 만들려면 WD 를 126 mm 로 1 mm 늘리면 됩니다. f/16 은 회절 원반이 6.4 px 로 커지고 회절 차단 주파수(111 lp/mm)가 나이퀴스트(145 lp/mm)보다 낮아지므로 쓰지 않습니다. 왜곡 1 % 렌즈는 가장자리에서 약 0.1 mm 가 틀어져 측정 목표(XY 0.02 mm)의 5배이므로, 보정에 지나치게 의존하게 됩니다.

### 6.2 잠금 상태 점검 (`b5_lock_check.py`)

```python
# b5_lock_check.py — 렌즈 잠금 후 '초점·위치가 변하지 않았는지' 점검 (B5)
# 방법: 고정된 타깃(ChArUco 보드 등)을 같은 조건으로 찍은 기준 영상과 오늘 영상을 비교
#   ① 위상 상관(cv2.phaseCorrelate)으로 영상 이동량 [px]
#   ② 라플라시안 분산(선명도)의 변화율 [%] → 초점이 돌아갔는지
# 여기서는 합성 영상(0.30, -0.20 px 이동 + 약간 흐림)으로 함수를 검증한다.
# 실행: python b5_lock_check.py
import numpy as np
import cv2


def make_target(h=480, w=640, seed=5):
    """무작위 체커 무늬 비슷한 고대비 타깃 영상"""
    rng = np.random.default_rng(seed)
    small = (rng.random((h // 16, w // 16)) > 0.5).astype(np.float32)
    img = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return cv2.GaussianBlur(img, (0, 0), 1.0) * 200 + 20


def sharpness(img):
    return cv2.Laplacian(img.astype(np.float32), cv2.CV_32F).var()


def lock_check(ref, cur, shift_tol_px=0.1, sharp_tol_pct=5.0):
    win = cv2.createHanningWindow(ref.shape[::-1], cv2.CV_32F)
    (dx, dy), _ = cv2.phaseCorrelate(ref.astype(np.float32), cur.astype(np.float32), win)
    dx, dy = round(dx, 3) + 0.0, round(dy, 3) + 0.0              # -0.00 표시 방지
    d_sharp = 100 * (sharpness(cur) - sharpness(ref)) / sharpness(ref)
    ok = np.hypot(dx, dy) <= shift_tol_px and abs(d_sharp) <= sharp_tol_pct
    return dx, dy, d_sharp, ok


if __name__ == "__main__":
    ref = make_target()
    M = np.float32([[1, 0, 0.30], [0, 1, -0.20]])                      # 알려진 이동
    moved = cv2.warpAffine(ref, M, ref.shape[::-1], flags=cv2.INTER_CUBIC,
                           borderMode=cv2.BORDER_REFLECT)
    blurred = cv2.GaussianBlur(moved, (0, 0), 0.6)                     # 초점이 약간 돌아간 상황
    for name, cur in (("같은 영상", ref.copy()), ("이동+흐림", blurred)):
        dx, dy, ds, ok = lock_check(ref, cur)
        print(f"{name:8s}: 이동 dx={dx:+.2f} px, dy={dy:+.2f} px, 선명도 변화 {ds:+6.1f} % → {'통과' if ok else '재교정 필요'}")
```

실행 예시와 기대 출력:

```
$ python b5_lock_check.py
같은 영상   : 이동 dx=+0.00 px, dy=+0.00 px, 선명도 변화   +0.0 % → 통과
이동+흐림   : 이동 dx=+0.28 px, dy=-0.23 px, 선명도 변화  -32.9 % → 재교정 필요
```

읽는 법: 알려진 이동 (0.30, −0.20) px 을 흐림이 섞인 상태에서도 대략 복원하고, 선명도가 33 % 떨어진 것을 잡아냅니다. 실제 사용 시에는 `ref = cv2.imread("data/raw/reference/lens_lock_ref.png", cv2.IMREAD_UNCHANGED)` 처럼 읽고 오늘 영상과 비교합니다. **조명이 다르면 선명도 값도 바뀌므로** 기준 영상과 같은 조명·노출로 찍습니다.

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 설계 적합성 | 6.1절 + 사양서 | f 25 mm, FOV_x 19.6~20.5 mm (WD 조정 포함), 왜곡 < 0.1 % 표기, MOD ≤ 100 mm |
| 해상력 | 사양서 | 3.45 µm 이하 픽셀 대응 표기 |
| 초점 품질 | 레이저 선 두께 | 측정 깊이 범위(0~12 mm)에서 선 두께 ≤ 8 px (B2 기준과 동일) |
| 잠금 기록 | 사진·`lens.yaml` | 조리개·초점 잠금, 테이프 표시 사진, 날짜·작업자 기록 |
| 잠금 점검 반복성 | 기준 영상 10회 연속 촬영 후 6.2절 | 이동 노이즈(표준편차) ≤ 0.02 px, 선명도 변동 ≤ 2 % (점검 기준 0.1 px·5 % 보다 충분히 작음) |
| 왜곡 (정량) | D1 결과 | 재투영 오차 RMS < 0.2 px (D1 기준) |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 캘리브레이션 후 초점 링을 만짐 | 높이·치수가 체계적으로 틀림 | 잠금 나사 + 테이프 표시, 6.2절 정기 점검, 건드렸으면 D1·D2 재수행 |
| 백색광으로 초점 맞춤 | 레이저 선이 두껍고 흐림 | 필터 장착 + 레이저 빛으로 초점 |
| 초점을 Z=0 에 맞춤 | 높은 곳 흐림 | 측정 깊이 중간 높이(Z ≈ 6 mm)에 맞춤 |
| MOD 확인 없이 구매 | WD 125 mm 에서 초점이 안 맞음 | 사양서 MOD 확인. 접사링을 쓰면 배율·왜곡이 바뀌므로 B1 재계산 |
| 이미지 서클이 작은 렌즈 | 화면 모서리가 어둡고 흐림 | 센서 형식 대응(이미지 서클) 확인 |
| 필터 나사 규격 모름 | 필터를 못 끼움 | 렌즈 선정 직후 B7 에 규격 전달 |
| 조리개를 측정마다 바꿈 | 캘리브레이션 무효 | 조리개도 잠금. 바꿀 필요가 있으면 재교정 계획 수립 |

## 9. 위험 요소

- **렌즈 링 풀림**: 진동·충격으로 링이 조금씩 돌 수 있습니다. 잠금 나사가 있어도 정기 점검(6.2절)이 필요합니다. 점검 결과는 [I2](../I-reliability/I2-msa.md) 안정성 관리도와 함께 봅니다.
- **청색 파장 성능**: 405 nm 에서 투과율·해상력이 사양서(가시광 기준)보다 낮을 수 있습니다. 수령 후 레이저 빛으로 선 두께를 실측해서 확인합니다.
- **텔레센트릭 필요성 재부상**: 높은 시편에서 원근 오차 보정이 불충분하면 2단계에서 텔레센트릭이 필요할 수 있습니다. 비용·납기를 [K4](../K-management/K4-risks.md) 에 등록합니다.
- **납기**: 렌즈가 늦으면 초점·잠금(W4) → D1(W7) 이 밀립니다. 재고 확인 후 주문합니다.

## 10. 기록 양식

렌즈 후보 비교표 (`results/design/B5_lens_candidates.csv`)

| 후보 | 초점거리[mm] | 마운트 | 대응 센서 형식 | 대응 픽셀[µm] | 왜곡[%] | MOD[mm] | 조리개 범위 | 잠금 나사 | 필터 나사 | 견적(원) | 납기(주) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | |

`config/hardware/lens.yaml`

```yaml
model: ""
serial: ""
focal_length_mm: 25
mount: C
filter_thread: ""                # 예: M27x0.5 (B7 로 전달)
aperture_f_number: 8
focus_height_mm: 6.0             # 초점 맞춘 평판 높이
working_distance_mm: 125
locked:
  date: null
  operator: ""
  aperture_locked: false
  focus_locked: false
  tape_mark_photo: docs/photos/lens_lock_YYYYMMDD.jpg
  reference_image: data/raw/reference/lens_lock_ref.png
lock_checks:                     # 세션마다 한 줄 (D5 이력과 연동)
  - {date: null, dx_px: null, dy_px: null, sharpness_change_pct: null, result: null}
```

## 11. 참고 자료

- E. Hecht, *Optics* — 얇은 렌즈, 회절, 에어리 원반
- W. J. Smith, *Modern Optical Engineering* — 초점심도, 텔레센트릭 광학, 렌즈 사양 읽기
- OpenCV 공식 문서 "Camera Calibration" 튜토리얼 — 왜곡 모형(k1, k2, p1, p2, k3)
- OpenCV 공식 문서 `cv2.phaseCorrelate`, `cv2.Laplacian` 함수 설명
- 머신비전 렌즈 제조사 기술 자료의 "lens selection / working distance / MTF" 해설 (선택한 제조사 문서)
