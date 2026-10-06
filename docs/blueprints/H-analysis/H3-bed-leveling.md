# H3. 바닥(베드) 평면 기준화

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: H. 처리·분석

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-01 ~ 2026-12-14 (W9-10) |
| 우선순위 | 보통 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [H1 점 → 격자 변환](H1-gridding.md), [H2 이상치·노이즈](H2-outliers.md), [C2 측정 시점](../C-mechanics/C2-measurement-timing.md) (베드 위 측정), [C4 좌표계 체계](../C-mechanics/C4-coordinate-frames.md) |
| 후행 요소 | [H4 정합](H4-registration.md), [H5 높이 지표](H5-height-metrics.md), [H7 치수·형상 지표](H7-dimensional-metrics.md), [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) (단차·평면도 판정) |
| 관련 마일스톤 | M4: 시편 1개 전체 파이프라인 완주 (W13-14). M2(게이지 블록 단차, W9-10)의 높이 기준도 이 단계에서 잡습니다 |

---

## 1. 목적

측정 좌표 {M} 에서 **베드(프린터 바닥판) 표면을 찾아 Z = 0 으로 맞추고 기울기를 없앱니다.**

- FDM 은 첫 층을 베드 표면 기준으로 쌓기 때문에(오토레벨링), **베드 표면 = G코드 Z 기준** 입니다. 베드를 Z = 0 으로 맞추면 측정 높이를 G코드 높이와 바로 비교할 수 있습니다 (H5).
- 이후 정합(H4)에서 남는 자유도는 **X 이동, Y 이동, Z축 회전(yaw)** 3개뿐이 됩니다.

이 요소에서 정할 것:
1. 베드 영역을 어떻게 고를지 (시편·클립·이물 제외)
2. RANSAC 평면 맞춤의 문턱값·반복 수·시드
3. 기울기를 **점군 회전**으로 없앨지, **평면 빼기**로 없앨지
4. 베드가 휘어 있을 때의 처리 (국소 기준)

---

## 2. 배경 지식 (초보자용)

### 2.1 평면의 식
평면은 `n·X + d = 0` 으로 씁니다. `n = (a, b, c)` 는 평면에 수직인 **단위 법선**, `d` 는 원점에서의 거리 관련 상수입니다.
점 X 에서 평면까지의 (부호 있는) 거리는 `n·X + d` 입니다.
- **기울기 각도** = 법선과 +Z 축 사이의 각 = `arccos(n_z)`.

### 2.2 최소제곱 평면과 그 약점
모든 점에 평면을 맞추면(SVD) 시편 윗면, 클립, 먼지까지 함께 맞춰 평면이 위로 끌려 올라갑니다. 베드만 골라내야 합니다.

### 2.3 RANSAC — "다수결" 평면 찾기 (Fischler & Bolles, 1981)
1. 점 3개를 무작위로 뽑아 평면을 만든다.
2. 그 평면에서 거리 `thr` 이내인 점(정상점, inlier)의 수를 센다.
3. 1~2 를 N 번 반복해서 정상점이 가장 많은 평면을 고른다.
4. 그 정상점들 전체로 최소제곱 평면을 다시 맞춘다.

필요한 반복 수는 다음 식으로 계산합니다 (w: 정상점 비율, s = 3, p: 성공 확률).
```
N = log(1 − p) / log(1 − w³)        w = 0.5, p = 0.999 → N = 52
```
이 문서는 여유 있게 **N = 500** 을 씁니다 (w = 0.25 에서도 p > 0.999).

문턱값 `thr` 은 센서 노이즈 σ 의 약 3배로 잡습니다: σ = 5 µm → **thr = 15 µm**.

### 2.4 두 단계로 베드 찾기
시편을 미리 알 수 없으므로 두 번 맞춥니다.
1. 1단계: 모든 유효 칸에 RANSAC → 가장 넓은 평면(보통 베드).
2. 베드 위로 **첫 층 높이의 절반(0.1 mm)** 보다 높은 칸 = 시편·클립 → **1 mm 만큼 넓혀서** 제외.
3. 2단계: 남은 칸으로 RANSAC 다시 → 최종 베드 평면.

주의: **시편 윗면이 베드보다 넓게 찍히면** 1단계가 시편 윗면을 "베드"로 고릅니다. 스캔 영역에 베드가 충분히 들어오도록(시편 면적의 2배 이상) 하거나, `candidate` 로 스캔 가장자리만 후보로 줍니다.

### 2.5 기울기 없애기: 회전 vs 빼기
| 방법 | 하는 일 | 문제 |
|---|---|---|
| **평면 빼기** | `H − (평면 높이)` | 높이는 맞지만, 높이 h 인 점이 XY 로 `h·tanα` 만큼 **밀린 채** 남음 |
| **점군 회전 (권장)** | 법선을 +Z 로 돌리는 회전 R 을 점군에 적용 → H1 다시 격자화 | 계산이 조금 늘어남 (수 초) |

높이 h 와 기울기 α 에 따른 XY 밀림 `h·tanα`:

| 기울기 α | h = 2 mm | h = 10 mm | h = 20 mm |
|---|---|---|---|
| 0.05° | 1.7 µm | 8.7 µm | 17.5 µm |
| 0.1° | 3.5 µm | 17.5 µm | 34.9 µm |
| 0.3° | 10.5 µm | 52.4 µm | 104.7 µm |
| 1.0° | 34.9 µm | 174.6 µm | 349.1 µm |

높이 방향 오차 `h(1/cosα − 1)` 는 10 mm, 0.3° 에서도 0.14 µm 로 무시할 수 있습니다. **문제는 XY 밀림**이고, 이것은 높이에 비례하므로 H4 정합(일정한 이동)으로 지워지지 않습니다. 그래서 **점군 회전을 기본**으로 합니다.

### 2.6 베드가 휘었을 때
가열 베드·얇은 스프링강 시트는 수십 µm 휘어 있을 수 있습니다. 프린터의 메쉬 레벨링은 노즐을 베드 굴곡에 맞춰 움직이므로, **시편 바로 아래의 베드 높이**가 그 시편의 진짜 기준입니다.
- 베드 평면 잔차의 **강건 P-V(99.5 % − 0.5 %)** 가 20 µm 를 넘으면 → **시편 둘레 1~4 mm 고리**에만 평면을 맞춥니다(국소 기준, `ring_candidate`).
- 더 정밀하게는 빈 베드를 미리 스캔한 **베드 지도**를 빼는 방법이 있지만, 시편 아래는 측정할 수 없어 보간이 필요하므로 보조 방법으로만 씁니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 내용 |
|---|---|---|---|
| 입력 | `<scan_id>_heightmap_M_clean.npy` + `_grid_M.json` | float32 | H2 결과 높이맵 (베드 찾기용) |
| 입력 | `points_M_clean.npz` | npz | H2 결과 점군 (회전 적용 대상) |
| 입력 | `config/default.yaml` → `bed` (추가 제안) | YAML | `ransac_thr_mm: 0.015`, `n_iter: 500`, `first_layer_mm: 0.2`, `margin_mm: 1.0`, `random_seed: 42` |
| 산출 | `<scan_id>_bed_plane.json` | JSON | 법선 n, d, 기울기 °, 정상점 %, 잔차 RMS·P-V, 사용 칸 수, 국소 기준 여부 |
| 산출 | `<scan_id>_T_level.npy` | float64 4×4 | 수평화 변환 (회전 R + Z 이동). {M} → {M'} (수평화된 측정 좌표) |
| 산출 | `points_Mlevel.npz` | npz | 수평화된 점군 (H4 의 입력) |
| 산출 | `<scan_id>_heightmap_Mlevel.npy` + JSON | float32 | 수평화 후 다시 격자화한 높이맵 |
| 산출 | `<scan_id>_bed_residual.png` | PNG | 베드 잔차 지도 (휘어짐 확인용, J4 발산형 컬러맵 ±20 µm) |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 평면 맞춤 방법 | 최소제곱 / **RANSAC + 최소제곱 재맞춤** | **RANSAC + 재맞춤** | 시편·클립·먼지 자동 배제 (청사진 H3) |
| 정상점 문턱 `thr` | 10 / **15** / 25 µm | **15 µm** (≈ 3σ) | σ 5 µm 기준. 실측 σ 가 다르면 3σ 로 재설정 |
| 반복 수 | 52 (이론) / **500** | **500** | 정상점 25 % 까지 안전, 시간 영향 작음 (표본 5만 점으로 평가) |
| 시드 | 고정 / 무작위 | **고정 (42)** | J2 재현성 |
| 시편 제외 문턱 | 0.05 / **0.1** / 0.2 mm | **첫 층 높이의 1/2 (0.1 mm)** | G4 의 `M_meas` 문턱과 같은 원리 |
| 제외 여유 | 0.5 / **1.0** / 2.0 mm | **1.0 mm** | 엣지 효과·브림 잔여물 배제 |
| 기울기 제거 | 평면 빼기 / **점군 회전** | **점군 회전** | 2.5 절 XY 밀림 |
| 베드 휘어짐 기준 | 전역 평면 / 국소 고리 / 베드 지도 | 강건 P-V ≤ 20 µm: **전역**, 초과: **국소 고리 1~4 mm** | 메쉬 레벨링 특성 |
| Z = 0 정의 | 베드 표면 / 첫 층 윗면 | **베드 표면** | G코드 Z 기준과 일치 (청사진 H3) |

---

## 5. 수행 절차

1. **설정 추가 (0.5일)**
   - [ ] `config/default.yaml` 에 `bed:` 항목(4장 값) 추가, 시드 42
2. **모듈 구현·합성 검증 (1일)**
   - [ ] 6장 `h3_bed_leveling.py` 를 `src/cvlab/preprocess.py` 에 추가
   - [ ] 데모 실행: 기울기 오차 < 0.002°, 회전 방식 XY 밀림이 평면 빼기보다 작음(높이 의존 성분 제거) 확인
   - [ ] `pytest -q test_h3.py` 통과 (이상치 40 % 에서도 평면 복원)
3. **빈 베드 스캔 (하드웨어 담당과 함께, 0.5일)**
   - [ ] 시편 없이 베드 전체 스캔 → 평면 잔차 RMS·강건 P-V 기록 → 베드 휘어짐 수준 파악
   - [ ] 강건 P-V > 20 µm 이면 국소 고리 기준을 기본으로 채택하고 기록
4. **시편 스캔에 적용 (0.5일)**
   - [ ] 2단계 RANSAC → `_bed_plane.json` 저장
   - [ ] 베드 영역 마스크를 그림으로 확인: 시편·클립·브림이 빠졌는지
   - [ ] `level_points()` → H1 다시 격자화 → `_heightmap_Mlevel.npy`
5. **게이지 블록 단차 (M2 연계, 0.5일)**
   - [ ] 측정대 위 게이지 블록 스캔을 같은 방식으로 수평화 → H7 `step_height` → 단차 오차 < 10 µm 확인
6. **반복성 확인 (0.5일)**
   - [ ] 같은 시편 3회 스캔의 기울기·d 값 비교: 기울기 차이 < 0.005°, 베드 높이 차이 < 2 µm
7. **문서화**
   - [ ] 10장 기록 양식 작성, 베드 잔차 그림 저장

---

## 6. Python 구현

### 6.1 모듈 `h3_bed_leveling.py`

```python
"""H3. 바닥(베드) 평면 기준화 모듈: RANSAC 평면 맞춤 + 기울기 보정.
최종적으로는 src/cvlab/preprocess.py 에 합칩니다. 단위 mm."""
import numpy as np
from scipy.ndimage import binary_dilation


def fit_plane_svd(P):
    """최소제곱 평면 (SVD). 반환: 단위 법선 n (+Z 쪽), 상수 d  (n·X + d = 0)"""
    c = P.mean(axis=0)
    _, _, Vt = np.linalg.svd(P - c, full_matrices=False)
    n = Vt[-1]
    if n[2] < 0:
        n = -n                                    # 법선이 항상 위(+Z)를 향하게
    return n, -n @ c


def ransac_plane(P, thr=0.015, n_iter=500, seed=42, max_points=50_000):
    """RANSAC 평면 맞춤 (Fischler & Bolles 1981).
    P: (N,3) 점, thr: 평면까지 거리가 이 값 이하면 '정상점(inlier)' [mm]
    1) 무작위 3점 → 평면  2) 정상점 개수 세기  3) 가장 많은 평면 선택  4) 정상점 전체로 SVD 재맞춤
    max_points: 점이 많으면 후보 평면 평가는 무작위 표본으로만 한다(속도). 최종 재맞춤은 전체 점 사용."""
    rng = np.random.default_rng(seed)             # 시드 고정 → 재현성 (J2)
    S = P if len(P) <= max_points else P[rng.choice(len(P), max_points, replace=False)]
    best_count, best_in = -1, None
    for _ in range(n_iter):
        A, B, C = S[rng.choice(len(S), 3, replace=False)]
        n = np.cross(B - A, C - A)
        norm = np.linalg.norm(n)
        if norm < 1e-12:                          # 세 점이 일직선이면 건너뜀
            continue
        n /= norm
        inl = np.abs((S - A) @ n) < thr
        if inl.sum() > best_count:
            best_count, best_in = inl.sum(), inl
    n, d = fit_plane_svd(S[best_in])
    inl = np.abs(P @ n + d) < thr                 # 재맞춤 평면으로 정상점 다시 판정
    n, d = fit_plane_svd(P[inl])
    return n, d, inl


def ransac_iterations(inlier_ratio, p_success=0.999, s=3):
    """필요 반복 횟수 N = log(1−p) / log(1−w^s)"""
    return int(np.ceil(np.log(1 - p_success) / np.log(1 - inlier_ratio ** s)))


def heightmap_to_points(H, grid, mask=None):
    """높이맵 칸 중심 좌표 → (N,3) 점 배열"""
    X, Y = np.meshgrid(grid["xs"], grid["ys"])
    m = np.isfinite(H) if mask is None else (mask & np.isfinite(H))
    return np.column_stack([X[m], Y[m], H[m]])


def estimate_bed_plane(H, grid, first_layer_mm=0.2, margin_mm=1.0, thr=0.015,
                       n_iter=500, seed=42, candidate=None):
    """2단계 베드 평면 추정.
    1단계: (candidate 영역의) 모든 유효 칸에 RANSAC → 가장 큰 평면 = 베드라고 가정
    2단계: 베드 위 first_layer/2 보다 높은 칸 = 시편 → margin_mm 만큼 넓혀서 제외 → 다시 RANSAC"""
    cand = np.isfinite(H) if candidate is None else (candidate & np.isfinite(H))
    n, d, _ = ransac_plane(heightmap_to_points(H, grid, cand), thr, n_iter, seed)
    X, Y = np.meshgrid(grid["xs"], grid["ys"])
    above = -(n[0] * X + n[1] * Y + d) / n[2]     # 각 칸 위치의 베드 평면 높이
    part = np.isfinite(H) & (H - above > first_layer_mm / 2)
    part = binary_dilation(part, iterations=int(round(margin_mm / grid["res"])))
    bed = cand & ~part
    P = heightmap_to_points(H, grid, bed)
    n, d, inl = ransac_plane(P, thr, n_iter, seed)
    res = P @ n + d                               # 정상점의 평면 거리(잔차)
    report = {"tilt_deg": float(np.degrees(np.arccos(n[2]))),
              "normal": [float(v) for v in n], "d_mm": float(d),
              "bed_cells": int(len(P)), "inlier_pct": float(100 * inl.mean()),
              "bed_rms_um": float(1000 * np.sqrt(np.mean(res[inl] ** 2))),
              "bed_pv_um": float(1000 * (res[inl].max() - res[inl].min()))}
    return n, d, bed, report


def rotation_to_z(n):
    """법선 n 을 +Z 축 (0,0,1)로 보내는 최소 회전 행렬 (로드리게스 공식)"""
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(n, z); s = np.linalg.norm(v); c = n @ z
    if s < 1e-15:
        return np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - c) / s ** 2)


def level_points(P, n, d):
    """[권장] 점군을 회전 + 이동해서 베드 평면을 정확히 Z=0 으로 만든다.
    이후 H1 격자화를 다시 하면 기울기에 의한 XY 밀림이 없다."""
    R = rotation_to_z(n)
    Q = P @ R.T
    Q[:, 2] += d                                  # 회전 후 평면은 z = −d → 0 으로 이동
    return Q, R


def level_heightmap_subtract(H, grid, n, d):
    """[간이] 높이맵에서 평면 높이를 빼기만 한다. 높이 h 인 점이 XY로 h·tan(기울기) 만큼 밀린 채 남는다."""
    X, Y = np.meshgrid(grid["xs"], grid["ys"])
    return H - (-(n[0] * X + n[1] * Y + d) / n[2])


def ring_candidate(part_mask, res, inner_mm=1.0, outer_mm=4.0):
    """[베드가 휘었을 때] 시편 둘레 inner~outer mm 고리 영역만 베드 후보로 쓴다 (국소 기준).
    estimate_bed_plane(..., candidate=ring_candidate(...)) 처럼 사용."""
    outer = binary_dilation(part_mask, iterations=int(round(outer_mm / res)))
    inner = binary_dilation(part_mask, iterations=int(round(inner_mm / res)))
    return outer & ~inner
```

### 6.2 데모 `demo_h3.py` (0.3° 기울어진 베드 + 10 mm 블록 + 클립)

같은 폴더에 H1 문서의 `h1_gridding.py` 가 있어야 합니다.

```python
"""H3 데모: 0.3° 기울어진 베드 위 10 mm 높이 블록. 클립·이물 이상치 포함."""
import numpy as np
from h1_gridding import make_grid, grid_points
from h3_bed_leveling import (estimate_bed_plane, level_points, level_heightmap_subtract,
                             rotation_to_z, heightmap_to_points, ransac_iterations)

rng = np.random.default_rng(3)
res = 0.05
# 1) 참 좌표(베드=Z0)에서 점 생성: 30×30 mm 베드 + 중심 (15,15) 의 10×10 mm 블록(높이 10 mm)
g = np.arange(0, 30, 0.025)
X, Y = np.meshgrid(g, g)
Z = np.where((abs(X - 15) < 5) & (abs(Y - 15) < 5), 10.0, 0.0)
clip = (X < 4) & (Y > 22)                                   # 왼쪽 위 모서리에 베드 클립(이상치)
Z[clip] += 0.8
P_true = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

# 2) 센서 좌표 {M}: 베드가 0.3° 기울고 0.5 mm 떠 있음 + 노이즈 5 um
tilt_axis = np.array([0.6, 0.8, 0.0])                       # 기울기 회전축 (XY 평면 안)
a = np.radians(0.3)
n_tilted = np.cos(a) * np.array([0, 0, 1.0]) + np.sin(a) * np.cross(tilt_axis, [0, 0, 1.0])
R_tilt = rotation_to_z(n_tilted).T                          # Z축 → n_tilted 로 기울이는 회전
P_M = P_true @ R_tilt.T + [0, 0, 0.5]
P_M[:, 2] += rng.normal(0, 0.005, len(P_M))

grid = make_grid(0.5, 29.5, 0.5, 29.5, res)
H, cnt, _ = grid_points(*P_M.T, grid)
print("RANSAC 필요 반복 (정상점 50 %, 성공확률 99.9 %):", ransac_iterations(0.5))

# 3) 베드 평면 추정
n, d, bed, rep = estimate_bed_plane(H, grid)
print(f"추정 기울기 {rep['tilt_deg']:.4f}° (정답 0.3000°), 법선 오차 "
      f"{np.degrees(np.arccos(np.clip(n @ n_tilted, -1, 1)))*3600:.2f} 각초")
print(f"베드 칸 {rep['bed_cells']}, 정상점 {rep['inlier_pct']:.1f} %, 잔차 RMS {rep['bed_rms_um']:.2f} um, "
      f"P-V {rep['bed_pv_um']:.1f} um")

# 4) 두 가지 보정 비교: 블록 윗면 점들의 높이와 XY 중심 (참값: 높이 10, 중심 (15, 15))
H_sub = level_heightmap_subtract(H, grid, n, d)              # 간이: 높이맵에서 평면 빼기
Q, R = level_points(P_M, n, d)                               # 권장: 점군 회전 후 다시 격자화
H_rot, _, _ = grid_points(*Q.T, grid)
top = Z.ravel() > 5                                          # 블록 윗면에서 온 점들
z_sub = P_M[:, 2] - (-(n[0] * P_M[:, 0] + n[1] * P_M[:, 1] + d) / n[2])
for name, xy, z, Hl in [("평면 빼기", P_M[top, :2], z_sub[top], H_sub),
                        ("점군 회전", Q[top, :2], Q[top, 2], H_rot)]:
    cx, cy = xy.mean(axis=0)
    bed_l = Hl[bed & np.isfinite(Hl)]
    print(f"[{name}] 윗면 높이 {np.median(z):.4f} mm, XY 중심 밀림 ({(cx-15)*1000:+.1f}, {(cy-15)*1000:+.1f}) um, "
          f"베드 높이 중앙값 {np.median(bed_l)*1000:+.2f} um")
print(f"예상 밀림 크기 h·tan(0.3°) = {10*np.tan(a)*1000:.1f} um")
```

```text
$ python3 demo_h3.py
RANSAC 필요 반복 (정상점 50 %, 성공확률 99.9 %): 52
추정 기울기 0.3005° (정답 0.3000°), 법선 오차 1.91 각초
베드 칸 264443, 정상점 100.0 %, 잔차 RMS 2.73 um, P-V 25.0 um
[평면 빼기] 윗면 높이 10.0001 mm, XY 중심 밀림 (+41.9, -31.4) um, 베드 높이 중앙값 +0.01 um
[점군 회전] 윗면 높이 10.0000 mm, XY 중심 밀림 (-2.2, +1.6) um, 베드 높이 중앙값 +0.03 um
예상 밀림 크기 h·tan(0.3°) = 52.4 um
```

**결과 읽는 법**
- 기울기를 0.3005° 로 찾았습니다 (법선 방향 오차 약 2 각초 ≈ 0.0005°). 클립(0.8 mm 튀어나온 이상치)은 시편 제외 단계에서 빠졌습니다.
- 베드 잔차 RMS 2.73 µm 는 노이즈 5 µm 가 칸당 약 4점(0.025 mm 점 간격, 0.05 mm 격자)의 중앙값으로 줄어든 값입니다. P-V 25 µm 는 26만 칸 중 가장 큰 값과 작은 값의 차이라서 RMS 의 약 9배가 됩니다 → **P-V 는 점이 많을수록 커지므로 강건 P-V 와 함께 봅니다.**
- **평면 빼기**: 블록 윗면 높이(10.0001 mm)는 맞지만 XY 중심이 (+41.9, −31.4) µm, 크기 52.4 µm 밀렸습니다. 예상값 `10·tan 0.3° = 52.4 µm` 와 정확히 같습니다.
- **점군 회전**: 밀림이 (−2.2, +1.6) µm 로 줄었습니다. 남은 2.7 µm 는 센서 Z 방향으로 준 0.5 mm 오프셋이 회전 후 XY 로 조금 새어 나온 **높이와 무관한 일정한 이동**(0.5 mm × sin 0.3° ≈ 2.6 µm)이라서, H4 정합에서 함께 흡수됩니다.

### 6.3 단위 테스트 `test_h3.py`

```python
"""H3 단위 테스트. 실행: pytest -q test_h3.py"""
import numpy as np
from h3_bed_leveling import ransac_plane, rotation_to_z, level_points


def test_이상치_40퍼센트에서도_평면을_찾는다():
    rng = np.random.default_rng(0)
    xy = rng.uniform(0, 30, (5000, 2))
    z = 0.002 * xy[:, 0] - 0.001 * xy[:, 1] + 0.3 + rng.normal(0, 0.003, 5000)
    out = rng.random(5000) < 0.4
    z[out] += rng.uniform(0.1, 2.0, out.sum())        # 40 % 는 위로 튄 이상치(이물, 시편)
    n, d, inl = ransac_plane(np.column_stack([xy, z]), thr=0.01)
    a, b = -n[0] / n[2], -n[1] / n[2]
    assert abs(a - 0.002) < 2e-5 and abs(b + 0.001) < 2e-5
    assert abs(-d / n[2] - 0.3) < 0.001


def test_회전행렬은_법선을_Z축으로_보낸다():
    n = np.array([0.01, -0.02, 1.0]); n /= np.linalg.norm(n)
    R = rotation_to_z(n)
    assert np.allclose(R @ n, [0, 0, 1], atol=1e-12)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12) and np.isclose(np.linalg.det(R), 1)


def test_수평화_후_평면은_Z0():
    n = np.array([0.0, 0.01, 1.0]); n /= np.linalg.norm(n); d = -0.5 * n[2]
    P = np.array([[x, y, (-d - n[0] * x - n[1] * y) / n[2]] for x in range(5) for y in range(5)], float)
    Q, _ = level_points(P, n, d)
    assert np.abs(Q[:, 2]).max() < 1e-9


def test_고리_후보영역():
    from h3_bed_leveling import ring_candidate
    part = np.zeros((200, 200), bool); part[80:120, 80:120] = True
    ring = ring_candidate(part, res=0.1, inner_mm=1.0, outer_mm=3.0)
    assert not ring[100, 100] and not ring[100, 125] and ring[100, 135] and not ring[100, 155]
```

```text
$ python3 -m pytest -q test_h3.py
4 passed in 0.xxs
```

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 기울기 복원 | 합성 0.3° (데모) | 오차 < 0.002° |
| 베드 높이 | 합성, 수평화 후 베드 칸 중앙값 | \|값\| < 1 µm |
| 이상치 내성 | 합성, 이상치 40 % (pytest) | 기울기 계수 오차 < 2 × 10⁻⁵, 높이 < 1 µm |
| 높이 의존 XY 밀림 제거 | 합성 10 mm 블록 | 회전 방식 잔여 밀림 < 5 µm (평면 빼기 52 µm 대비) |
| 실측 베드 평면 잔차 | 빈 베드 스캔 | RMS ≤ 2 × 센서 σ. 강건 P-V 기록 (20 µm 초과 시 국소 기준) |
| 반복성 | 같은 시편 3회 | 기울기 차이 < 0.005°, 베드 높이 차이 < 2 µm |
| M2 연계 | 게이지 블록 단차 (H7) | 오차 < 10 µm |
| 단위 테스트 | `pytest test_h3.py` | 전부 통과 |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 시편까지 포함해 최소제곱 평면 | 베드가 Z=0 보다 위로 잡혀 모든 높이 오차가 −쪽으로 치우침 | RANSAC + 시편 제외 2단계 |
| 시편 윗면이 베드보다 넓은데 1단계를 전체로 실행 | 시편 윗면이 Z=0 이 되어 높이가 수 mm 틀림 | 스캔 영역에 베드를 충분히 포함, 또는 `candidate` 로 가장자리 지정 |
| 문턱 `thr` 을 너무 작게 (예: 3 µm) | 정상점 비율이 낮아 평면이 불안정, 매번 결과가 다름 | 3σ 로 설정, 시드 고정 |
| 평면 빼기만 사용 | 높은 형상일수록 위치·윤곽 오차가 한 방향으로 생김 | 점군 회전 후 다시 격자화 |
| 법선 방향(위/아래) 혼동 | 수평화 후 높이가 모두 음수 | 법선을 항상 +Z 쪽으로 (코드에 포함) |
| 베드 휘어짐 무시 | 시편 위치에 따라 높이 치우침이 다름 | 빈 베드 잔차 지도 확인, 필요 시 국소 고리 |
| 마커 받침·지그를 베드로 착각 | 국소적으로 이상한 기울기 | 베드 마스크 그림을 매번 확인 |
| 첫 층 Z-오프셋(베이비스텝) 기록 누락 | 모든 시편의 높이가 일정량(예: +30 µm) 치우쳐도 원인을 모름 | 프린터 Z-오프셋을 메타데이터(F3)에 기록 |

---

## 9. 위험 요소

- **베드 위 측정이 아닐 때**: 시편을 떼어 별도 측정대에서 재면(C2) 베드가 없습니다. 이때는 시편 바닥면이 측정대에 닿아 있으므로 **측정대 표면**을 같은 방식으로 Z=0 으로 잡고, "베드 기준"과 차이(첫 층 눌림, 휘어짐)를 해석에 적습니다.
- **반사·반투명 베드**: 유리·PEI 베드는 레이저가 비치거나 반사되어 베드 점이 부족할 수 있습니다. 베드 정상점이 1만 점 미만이면 경고합니다. 무광 테이프 조각 몇 개를 기준 영역으로 붙이는 방법도 있습니다(두께는 기록).
- **열 변형**: 가열 베드를 끈 직후에는 베드 모양이 시간에 따라 변합니다(C6). 식힌 뒤 측정하는 규칙을 지킵니다.
- **스테이지 직진도**: 스캔 축이 휘어 있으면(C1) 베드가 원통처럼 휘어 보입니다. 빈 베드 잔차가 스캔 방향으로 일정한 곡선이면 스테이지 문제를 의심합니다.

---

## 10. 기록 양식

`results/<scan_id>/<scan_id>_bed_plane.json` 에 들어갈 항목 (YAML 로 표현)
```yaml
scan_id: S03_r02
method: ransac_two_stage        # ransac_two_stage | ring_local
ransac_thr_mm: 0.015
n_iter: 500
random_seed: 42
first_layer_mm: 0.2
margin_mm: 1.0
ring_mm: null                   # 국소 기준이면 [1.0, 4.0]
normal: [ , , ]
d_mm:
tilt_deg:
bed_cells:
inlier_pct:
bed_rms_um:
bed_pv_um:
bed_pv_robust_um:               # 99.5 % − 0.5 %
leveling: rotate_points         # rotate_points | subtract_plane
printer_z_offset_mm:            # 프린터 설정값 (F3 메타데이터와 동일)
notes: ""
```

반복성 기록표

| 날짜 | 시편 | 스캔 | 기울기 ° | d [mm] | 베드 RMS µm | 강건 P-V µm | 국소 기준 여부 |
|---|---|---|---|---|---|---|---|
| | | r01 | | | | | |
| | | r02 | | | | | |
| | | r03 | | | | | |

---

## 11. 참고 자료

- Fischler, M. A., & Bolles, R. C. (1981). Random sample consensus: a paradigm for model fitting with applications to image analysis and automated cartography. *Communications of the ACM*, 24(6).
- Hartley, R., & Zisserman, A. *Multiple View Geometry in Computer Vision* — RANSAC 반복 수 식
- NumPy 문서: `numpy.linalg.svd`; SciPy 문서: `scipy.ndimage.binary_dilation`
- (선택) Open3D 문서: `PointCloud.segment_plane` — 같은 RANSAC 평면 분할 기능. 이 문서의 코드는 Open3D 없이 동작합니다.
- 청사진 관련 절: [BLUEPRINT](../../BLUEPRINT.md) H3, C2, C4, C6
