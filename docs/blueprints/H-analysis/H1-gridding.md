# H1. 점 → 격자(높이맵) 변환

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: H. 처리·분석

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-01 ~ 2026-12-14 (W9-10) |
| 우선순위 | 보통 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [F1 레이저 라인 중심 추출](../F-acquisition/F1-line-extraction.md), [D2 레이저 평면](../D-calibration/D2-laser-plane.md), [D3 스캔 축](../D-calibration/D3-scan-axis.md), [F3 저장 형식](../F-acquisition/F3-data-storage.md), [G3 마스크·기준 높이맵](../G-reference/G3-mask-heightmap.md) (같은 격자 규칙), [J2 설정·재현성](../J-software/J2-config-reproducibility.md) |
| 후행 요소 | [H2 이상치·노이즈](H2-outliers.md), [H3 바닥 평면 기준화](H3-bed-leveling.md), [H4 정합](H4-registration.md), [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) (게이지 블록 단차 계산에 사용) |
| 관련 마일스톤 | M4: 시편 1개 전체 파이프라인 완주 (W13-14). 같은 기간의 M2(게이지 블록 단차 오차 < 10 µm)도 이 코드로 높이맵을 만들어 판정합니다 |

---

## 1. 목적

삼각측량(D2)과 스캔 축 결합(D3)으로 얻은 **흩어진 3D 점 (x, y, z)** 를 **가로·세로 간격이 일정한 2D 배열(높이맵)** 로 바꿉니다.
이후의 모든 단계(H2 이상치, H3 수평화, H4 정합, H5~H7 지표)는 높이맵을 입력으로 받습니다.

이 요소가 끝나면 다음이 보장되어야 합니다.

1. 높이맵의 **칸(cell) 위치 규칙이 G3 기준 높이맵과 똑같다** (원점, 간격, 칸 중심 규칙, 배열 순서).
2. 칸 값은 그 칸에 들어온 점들의 **중앙값**이고, 점이 없는 칸은 **NaN** 이다 (보간하지 않음).
3. 칸마다 **점 개수(count)** 를 함께 저장해서, "측정이 얼마나 촘촘했는지"를 나중에 확인할 수 있다.
4. 격자 정보(원점·간격·좌표계 이름)가 **JSON 파일로 함께 저장**된다.

---

## 2. 배경 지식 (초보자용)

### 2.1 점군과 높이맵
- **점군(point cloud)**: `(x, y, z)` 점들의 목록입니다. 순서도 간격도 제각각입니다.
- **높이맵(height map)**: 바닥을 바둑판처럼 나누고, 칸마다 높이 하나를 적은 표(2D 배열)입니다. 위에서 본 형상만 담으므로 **2.5D** 라고 부릅니다. 벽의 옆면이나 처마 밑은 담을 수 없습니다.
- 바둑판으로 바꾸는 이유: G코드 기준(G3)도 바둑판이므로 **칸끼리 그대로 빼면** 오차 지도가 됩니다 (`e = H_meas − H_ref`).

### 2.2 칸 중심과 칸 경계
간격 `res = 0.02 mm`, 원점 `x0 = 0` 이면 다음과 같습니다.

```
칸 번호 i      :    0        1        2
칸 중심 xs[i]  :  0.00     0.02     0.04          ← G3 의 np.arange(x0, x1, res) 와 같은 값
칸 경계        : -0.01 | 0.01 | 0.03 | 0.05       ← 중심 ± res/2
```
- 우리 규칙: **xs, ys = 칸 중심 좌표**, 경계 = 중심 ± res/2.
- 이 규칙을 G3 과 다르게 잡으면 측정과 기준이 **반 칸(10 µm) 어긋난 채로** 비교됩니다. 이런 오차는 눈으로 찾기 어렵습니다.

### 2.3 배열의 행과 열
- `H[iy, ix]`: **첫 번째 번호가 행(= y)**, 두 번째가 열(= x)입니다. 수학의 (x, y) 순서와 반대입니다.
- `scipy.stats.binned_statistic_2d(x, y, ...)` 는 결과를 `(nx, ny)` 모양으로 돌려줍니다. 그래서 **반드시 `.T`(전치)** 를 해야 `(ny, nx)` 가 됩니다. 이것을 빠뜨리면 그림이 대각선으로 뒤집히는데, 정사각형 시편에서는 티가 나지 않습니다 → **비대칭 L자 시편으로 확인**합니다 (C4).

### 2.4 왜 평균이 아니라 중앙값인가
한 칸에 `1.00, 1.01, 9.99` (마지막은 반사로 튄 값)가 들어오면 평균은 4.0, 중앙값은 1.01 입니다. 중앙값은 이상치 하나에 끌려가지 않습니다.
단, 점이 1~2개뿐인 칸에서는 중앙값도 평균과 같으므로, 스파이크 제거는 H2에서 이웃 칸과 비교해 따로 합니다.

### 2.5 한 칸에 점이 몇 개 들어오나
B1 예시 센서는 X 방향 점 간격 δx ≈ 13.8 µm, 스캔 간격(C1) 0.02 mm 입니다. 0.02 × 0.02 mm 칸에는
X 방향으로 0.02 / 0.0138 ≈ 1.45개, Y 방향으로 1줄 → **칸당 평균 약 1.45개 (1개 또는 2개)** 가 들어옵니다.
스테이지가 µm 단위로 흔들리면 어떤 칸은 0개가 됩니다 (아래 데모에서 약 0.6 %).
- 격자 간격을 점 간격보다 **작게** 잡으면 빈 칸(NaN)이 대량으로 생깁니다. **격자 간격 ≥ max(δx, 스캔 간격)** 이 원칙입니다.

### 2.6 NaN 은 "모름"이다
점이 없는 칸을 주변 값으로 채우면(보간) 그 값은 **측정값이 아니라 추측**입니다. 가림(E2) 때문에 비어 있는 곳을 채우면, 오차가 있는지 없는지도 모르는 곳에 "오차 0"을 만들어 냅니다. 그래서 지표 계산용 높이맵은 **NaN 그대로** 두고, 보기 좋은 그림이 필요할 때만 따로 채운 사본을 만듭니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 내용 |
|---|---|---|---|
| 입력 | `data/processed/<scan_id>/points_M.npz` | numpy npz | `x, y, z` (mm, {M} 좌표), `peak`, `width_px` (F1 신뢰도) |
| 입력 | `config/default.yaml` → `grid.resolution_mm` | YAML | 격자 간격 (권장 0.02) |
| 입력 | G3 의 `<gcode>_grid_G.json` | JSON | 최종 비교용 {G} 격자 원점·간격·크기 (H4 이후 사용) |
| 산출 | `<scan_id>_heightmap_M.npy` | float32, (ny, nx) | 칸별 중앙값 높이 [mm], 빈 칸 NaN |
| 산출 | `<scan_id>_count_M.npy` | int32, (ny, nx) | 칸별 점 개수 |
| 산출 | `<scan_id>_grid_M.json` | JSON | `frame, x0_mm, y0_mm, res_mm, nx, ny, cell_reference="center", array_order="H[iy, ix]"` |
| 산출 | `<scan_id>_H1_report.yaml` | YAML | 점 개수, 커버리지 %, 칸당 점 수 분포, 실행 시간, 코드 커밋 |
| 산출 | `<scan_id>_H1_preview.png` | PNG | **그림 전용**(NaN을 가장 가까운 값으로 채운) 미리보기. 지표 계산에 쓰지 않음 |
| 산출(H4 후) | `<scan_id>_heightmap_G.npy` 외 | 위와 같음 | 점군을 T_G_M 으로 옮긴 뒤 **G3 격자로 다시 격자화**한 결과 (`frame="G"`) |

> 같은 함수가 **두 번** 쓰입니다. ① {M} 격자: H2·H3·마커 찾기용, ② {G} 격자: H4 의 `T_G_M` 을 점군에 적용한 뒤 최종 비교용. ②에서는 높이맵을 회전·보간하지 않고 **점을 옮겨서 다시 격자화**합니다(보간 두 번을 피함).

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 격자 간격 | 0.01 / **0.02** / 0.04 mm | **0.02 mm** | A2 목표 XY 간격, G3 와 동일. δx(13.8 µm)·스캔 간격(20 µm)보다 작으면 빈 칸이 급증 |
| 칸 대표값 | 평균 / **중앙값** / 최댓값 / 최솟값 | **중앙값** | 이상치에 강함 (BLUEPRINT H1). 최댓값은 2.5D 윗면 개념과 맞지만 스파이크에 취약 |
| 칸 위치 규칙 | 칸 중심 / 칸 왼쪽 아래 모서리 | **칸 중심** | G3 `np.arange(x0, x1, res)` 를 중심으로 해석. 두 문서가 같은 함수 `make_grid` 를 공유 |
| 최소 점 수 | 1 / 2 / 3 | **1** (개수는 저장) | 칸당 1~2개가 정상이므로 2 이상으로 하면 절반이 NaN. 대신 `count` 를 저장해 나중에 걸러낼 수 있게 함 |
| 빈 칸 처리 | NaN / 보간 | **NaN** | 보간값은 측정값이 아님 (E2) |
| 격자화 좌표계 | {M}만 / {G}만 / **둘 다** | **둘 다** | {M}: 전처리용, {G}: 최종 비교 (C4 "비교는 항상 {G}에서") |
| 저장 자료형 | float64 / **float32** | 높이 **float32**, 좌표 float64 | float32 의 20 mm 근처 표현 간격 ≈ 0.002 µm 로 충분, 용량 절반 |
| 격자 범위 | 점 범위 자동 / **G3 범위 고정** | 최종 비교는 **G3 범위** | 측정과 기준 배열 모양이 같아야 칸끼리 뺄 수 있음 |

---

## 5. 수행 절차

1. **격자 규칙 합의 (W9 첫날, 0.5일)**
   - [ ] G3 담당자와 `make_grid()` 를 공용 모듈(`src/cvlab/preprocess.py`)에 두기로 합의
   - [ ] `config/default.yaml` 의 `grid.resolution_mm: 0.02` 확인
   - [ ] JSON 필드 이름(`x0_mm, y0_mm, res_mm, nx, ny, frame`) 확정
2. **모듈 작성 (1일)**
   - [ ] 6장의 `h1_gridding.py` 를 `src/cvlab/preprocess.py` 로 옮김
   - [ ] `binned_statistic_2d` 결과에 `.T` 적용 여부를 코드 리뷰에서 한 번 더 확인
3. **합성 데이터 검증 (0.5일)**
   - [ ] 6장 데모 실행: 커버리지 ≥ 98 %, 내부 칸 오차 평균 |·| < 0.5 µm, RMS ≈ σ/√(칸당 점 수) 확인
   - [ ] 비대칭 L자에서 `H(x=9, y=3) ≈ 2`, `H(x=9, y=6) ≈ 0` 확인 (축 뒤집힘 없음)
   - [ ] `pytest -q test_h1.py` 3개 통과
4. **실측 평판 데이터 확인 (0.5일)**
   - [ ] 광학 평판 또는 석정반을 스캔 → 높이맵 생성 → 커버리지 ≥ 99 %, 칸당 점 수 분포 기록
   - [ ] `count == 0` 칸이 줄무늬 모양이면 스테이지 트리거 누락(C1) 의심 → 하드웨어 담당에게 전달
5. **게이지 블록 단차에 적용 (M2 연계, 0.5일)**
   - [ ] D5 게이지 블록 스캔을 격자화 → H3 수평화 → H7 `step_height` 로 단차 계산 (경계 0.25 mm 제외)
6. **격자 간격 민감도 (0.5일)**
   - [ ] 같은 스캔을 0.02 / 0.04 mm 로 격자화해 단차·평면도 결과 비교 → 차이 < 2 µm 이면 0.02 유지
7. **산출물 저장 규칙 적용 (0.5일)**
   - [ ] `save_heightmap()` 으로 `.npy + .json` 저장, `_H1_report.yaml` 작성 (10장 양식)
   - [ ] 결과 폴더에 설정 파일 사본·git 커밋 해시 저장 (J2)

---

## 6. Python 구현

### 6.1 모듈 `h1_gridding.py`

```python
"""H1. 점(x, y, z) → 균일 격자 높이맵 변환 모듈.
최종적으로는 src/cvlab/preprocess.py 에 합칩니다.
좌표 단위는 모두 mm 입니다."""
import json
import numpy as np
from scipy.stats import binned_statistic_2d


def make_grid(x_min, x_max, y_min, y_max, res):
    """격자 정의를 만든다.
    xs, ys = 각 칸의 '중심' 좌표 (G3의 np.arange(x0, x1, res) 와 같은 규칙).
    칸 경계(edges)는 중심 ± res/2 이다.
    np.arange(0, 12, 0.02) 처럼 실수 간격을 쓰면 반올림 때문에 개수가 1개 달라질 수 있으므로
    개수를 먼저 정수로 정하고 x_min + res·i 로 만든다."""
    nx = int(np.floor((x_max - x_min) / res + 1e-9))
    ny = int(np.floor((y_max - y_min) / res + 1e-9))
    xs = x_min + res * np.arange(nx)
    ys = y_min + res * np.arange(ny)
    x_edges = np.append(xs - res / 2, xs[-1] + res / 2)
    y_edges = np.append(ys - res / 2, ys[-1] + res / 2)
    return {"xs": xs, "ys": ys, "x_edges": x_edges, "y_edges": y_edges, "res": float(res)}


def grid_points(x, y, z, grid, statistic="median", min_count=1):
    """점들을 격자 칸에 모아 칸마다 대표 높이(기본: 중앙값)를 계산한다.
    반환: H (ny, nx) float32, count (ny, nx) int32, spread (ny, nx) float32
      - H[행, 열] = H[y 인덱스, x 인덱스]  (G3 meshgrid 와 같은 배치)
      - 점이 min_count 개 미만인 칸은 NaN (보간하지 않음)
      - spread = 칸 안 점들의 표준편차 (칸 내부 흩어짐, 품질 확인용)"""
    x = np.asarray(x, float); y = np.asarray(y, float); z = np.asarray(z, float)
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)        # NaN 점은 버림
    x, y, z = x[ok], y[ok], z[ok]
    bins = [grid["x_edges"], grid["y_edges"]]
    # 주의: binned_statistic_2d 결과는 (nx, ny) 모양 → 반드시 .T 로 (ny, nx) 로 바꾼다
    stat = binned_statistic_2d(x, y, z, statistic=statistic, bins=bins).statistic.T
    cnt = binned_statistic_2d(x, y, None, statistic="count", bins=bins).statistic.T
    spr = binned_statistic_2d(x, y, z, statistic="std", bins=bins).statistic.T
    H = stat.astype(np.float32)
    H[cnt < min_count] = np.nan
    return H, cnt.astype(np.int32), spr.astype(np.float32)


def coverage_pct(H, roi=None):
    """관심 영역(roi, bool 배열) 안에서 값이 있는 칸의 비율 [%]"""
    valid = np.isfinite(H)
    if roi is None:
        roi = np.ones_like(valid)
    return 100.0 * (valid & roi).sum() / roi.sum()


def save_heightmap(prefix, H, count, grid, frame, extra=None):
    """높이맵(.npy) + 점 개수(.npy) + 격자 정보(.json) 저장.
    격자 원점·간격이 없으면 높이맵은 '숫자 그림'일 뿐이므로 반드시 함께 저장한다."""
    np.save(f"{prefix}_heightmap_{frame}.npy", H)
    np.save(f"{prefix}_count_{frame}.npy", count)
    info = {"frame": frame, "x0_mm": float(grid["xs"][0]), "y0_mm": float(grid["ys"][0]),
            "res_mm": grid["res"], "nx": int(len(grid["xs"])), "ny": int(len(grid["ys"])),
            "cell_reference": "center", "array_order": "H[iy, ix]",
            "statistic": "median", "nan_meaning": "no_points"}
    info.update(extra or {})
    with open(f"{prefix}_grid_{frame}.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return info


def fill_for_display_only(H):
    """[그림 전용] NaN 칸을 가장 가까운 값으로 채운다. 지표 계산에 절대 쓰지 말 것."""
    from scipy.ndimage import distance_transform_edt
    nan = ~np.isfinite(H)
    idx = distance_transform_edt(nan, return_distances=False, return_indices=True)
    return H[tuple(idx)]
```

### 6.2 데모 `demo_h1.py` (합성 L자 시편)

```python
"""H1 데모: 합성 스캔 점 → 0.02 mm 높이맵. 정답을 알고 있으므로 결과를 검증할 수 있다."""
import numpy as np
from h1_gridding import make_grid, grid_points, coverage_pct, save_heightmap

rng = np.random.default_rng(42)
dx, pitch, sigma = 0.0138, 0.02, 0.005      # 센서 X 점간격 13.8 um, 스캔 간격 20 um, 노이즈 5 um

def true_height(x, y):
    """비대칭 L자 시편: 높이 2.0 mm (축 방향 확인용). 나머지는 베드(0)."""
    arm_x = (x >= 2) & (x < 10) & (y >= 2) & (y < 4)     # +X 방향 긴 팔
    arm_y = (x >= 2) & (x < 4) & (y >= 2) & (y < 7)      # +Y 방향 짧은 팔
    return np.where(arm_x | arm_y, 2.0, 0.0)

# 1) 합성 점 생성: 프로파일(한 줄) = 같은 y, x 는 13.8 um 간격
xs_line = np.arange(0, 12, dx)
ys_scan = np.arange(0, 9, pitch) + rng.normal(0, 0.001, size=len(np.arange(0, 9, pitch)))  # 스테이지 흔들림 1 um
X, Y = np.meshgrid(xs_line, ys_scan)
Z = true_height(X, Y) + rng.normal(0, sigma, X.shape)
drop = rng.random(X.shape) < 0.01                       # 1 % 점 누락(신호 없음)
Z[drop] = np.nan
print(f"점 개수: {X.size:,} (누락 {drop.mean()*100:.1f} %)")

# 2) 격자화
grid = make_grid(0, 12, 0, 9, 0.02)
H, cnt, spr = grid_points(X.ravel(), Y.ravel(), Z.ravel(), grid)
print("높이맵 모양 (ny, nx):", H.shape)
print("칸당 점 개수 분포:", {int(k): int(v) for k, v in zip(*np.unique(cnt, return_counts=True))})
print(f"커버리지: {coverage_pct(H):.2f} %")

# 3) 정답과 비교 (단차 경계에서 0.1 mm 이상 떨어진 칸만)
GX, GY = np.meshgrid(grid["xs"], grid["ys"])
T = true_height(GX, GY)
from scipy.ndimage import binary_erosion, binary_dilation
top = T > 1
interior = binary_erosion(top, iterations=5) | ~binary_dilation(top, iterations=5)
d = (H - T)[interior & np.isfinite(H)]
print(f"내부 칸 오차: 평균 {d.mean()*1000:+.2f} um, RMS {np.sqrt((d**2).mean())*1000:.2f} um")

# 4) 축 방향 확인: +X 끝(x=9, y=3)은 높고, +Y 끝 반대편(x=9, y=6)은 낮아야 한다
ix = lambda v: int(round((v - grid["xs"][0]) / grid["res"]))
iy = lambda v: int(round((v - grid["ys"][0]) / grid["res"]))
print("H(x=9,y=3) =", round(float(H[iy(3), ix(9)]), 3), "/ H(x=9,y=6) =", round(float(H[iy(6), ix(9)]), 3),
      "/ H(x=3,y=6) =", round(float(H[iy(6), ix(3)]), 3))

info = save_heightmap("S00_r01", H, cnt, grid, frame="M", extra={"scan_id": "S00_r01"})
print("저장:", info["nx"], "x", info["ny"], "격자, 원점", (info["x0_mm"], info["y0_mm"]))
```

실행 결과 (같은 폴더에 `h1_gridding.py` 를 두고 실행):

```text
$ python3 demo_h1.py
점 개수: 391,500 (누락 1.0 %)
높이맵 모양 (ny, nx): (450, 600)
칸당 점 개수 분포: {0: 1532, 1: 149795, 2: 118673}
커버리지: 99.43 %
내부 칸 오차: 평균 +0.01 um, RMS 4.42 um
H(x=9,y=3) = 1.996 / H(x=9,y=6) = -0.004 / H(x=3,y=6) = 2.0
저장: 600 x 450 격자, 원점 (0.0, 0.0)
```

**결과 읽는 법**
- 칸당 점 개수가 1개 또는 2개이고, 0개(빈 칸)가 1,532칸(0.57 %) 있습니다. 스테이지 흔들림 1 µm 때문에 어떤 줄은 옆 칸으로 넘어갔기 때문입니다.
- 내부 칸 오차 RMS 4.42 µm 는 노이즈 5 µm 가 칸당 평균 1.4개 점의 중앙값으로 줄어든 값입니다 (5/√1.45 ≈ 4.2 µm). 평균 +0.01 µm 로 치우침이 없습니다.
- `H(x=9, y=3) ≈ 2.0` (긴 팔 위), `H(x=9, y=6) ≈ 0` (팔 바깥) → 행·열이 뒤바뀌지 않았습니다.

### 6.3 단위 테스트 `test_h1.py` (J3)

```python
"""H1 단위 테스트 (J3). 실행: pytest -q test_h1.py"""
import numpy as np
from h1_gridding import make_grid, grid_points


def test_축_방향과_배열_순서():
    # x=0.5 근처에만 높은 점 하나 → H[행=y, 열=x] 위치에 나타나야 함
    g = make_grid(0, 1, 0, 2, 0.1)              # nx=10, ny=20
    H, cnt, _ = grid_points([0.52], [1.51], [7.0], g)
    assert H.shape == (20, 10)
    iy, ix = np.argwhere(np.isfinite(H))[0]
    assert (iy, ix) == (15, 5)                  # y=1.5 → 15번째 행, x=0.5 → 5번째 열


def test_중앙값은_이상치에_강함():
    g = make_grid(0, 1, 0, 1, 0.5)
    x = [0.1, 0.1, 0.1]; y = [0.1, 0.1, 0.1]; z = [1.00, 1.01, 9.99]   # 한 점이 스파이크
    H, cnt, _ = grid_points(x, y, z, g)
    assert cnt[0, 0] == 3 and abs(H[0, 0] - 1.01) < 1e-6


def test_빈칸은_NaN():
    g = make_grid(0, 1, 0, 1, 0.5)
    H, cnt, _ = grid_points([0.1], [0.1], [1.0], g)
    assert np.isnan(H[1, 1]) and cnt[1, 1] == 0
```

```text
$ python3 -m pytest -q test_h1.py
3 passed in 0.xxs
```

### 6.4 실제 데이터에 쓸 때

```python
import os
import numpy as np
from h1_gridding import make_grid, grid_points, coverage_pct, save_heightmap

scan_id = "S03_r02"
d = np.load(f"data/processed/{scan_id}/points_M.npz")             # F3 형식 (x, y, z, peak, width_px)
grid = make_grid(d["x"].min(), d["x"].max(), d["y"].min(), d["y"].max(), 0.02)
H, cnt, spr = grid_points(d["x"], d["y"], d["z"], grid)
os.makedirs(f"results/{scan_id}", exist_ok=True)
info = save_heightmap(f"results/{scan_id}/{scan_id}", H, cnt, grid, frame="M",
                      extra={"scan_id": scan_id, "calibration_id": "CAL-2026-10-06-A"})
print(info["nx"], "x", info["ny"], "칸, 커버리지", round(coverage_pct(H), 2), "%")
```

```text
$ python3 make_fixture.py && python3 usage_h1.py
499 x 399 칸, 커버리지 100.0 %
```

`make_fixture.py` 는 위 예시를 실행해 보기 위한 가짜 `points_M.npz`(10 × 8 mm, 가운데 1 mm 높이 띠)를 만드는 스크립트입니다. 실제로는 F3 단계의 파일을 씁니다 (실행 전 `data/processed/S03_r02/` 폴더를 만들어 둡니다).

```python
# 문서 6.4 실행용 가짜 실측 파일 생성 (규칙적인 스캔: X 13.8 um, Y 20 um 간격)
import numpy as np
rng = np.random.default_rng(0)
X, Y = np.meshgrid(np.arange(0, 10, 0.0138), np.arange(0, 8, 0.02) + 0.003)
x, y = X.ravel(), Y.ravel()
z = np.where((x > 3) & (x < 7), 1.0, 0.0) + rng.normal(0, 0.005, x.size)
np.savez("data/processed/S03_r02/points_M.npz", x=x, y=y, z=z,
         peak=rng.integers(50, 200, x.size), width_px=rng.uniform(3, 6, x.size))
```

- 점이 수백만 개여도 `binned_statistic_2d` 의 중앙값 계산은 100만 칸 기준 약 1.5초입니다 (이 문서 작성 환경에서 측정).

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 축·배열 순서 | 비대칭 L자 합성 데이터 + 실측 L자 시편 | 긴 팔이 +X, 짧은 팔이 +Y 에 나타남 (육안 + 자동 검사) |
| 치우침 | 합성 데이터 내부 칸 오차 평균 | \|평균\| < 0.5 µm |
| 노이즈 전달 | 합성 데이터 내부 칸 오차 RMS | σ/√(칸당 평균 점 수) 의 ±15 % 이내 (데모: 4.42 vs 4.2 µm) |
| 커버리지 | 평판(빈 곳 없는 면) 실측 스캔 | ≥ 99 % (합성: ≥ 98 %) |
| 격자 일치 | `_grid_G.json` 과 G3 격자 JSON 비교 | `x0, y0, res, nx, ny` 완전 일치 (차이 < 1e-9 mm) |
| 격자 간격 민감도 | 0.02 vs 0.04 mm 단차·평면도 | 차이 < 2 µm |
| 단위 테스트 | `pytest test_h1.py` | 전부 통과 |
| 실행 시간 | 20 × 20 mm, 0.02 mm | < 10 s |
| 완료 판정 | 위 항목 모두 + 10장 기록 양식 작성 | — |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| `binned_statistic_2d` 결과를 전치하지 않음 | 배열 모양이 (nx, ny), 그림이 대각선으로 뒤집힘 | `.statistic.T` 사용, L자 시편 테스트 |
| 칸 경계를 `np.arange(x0, x1+res, res)` 로 만들어 G3 과 반 칸 어긋남 | 모든 경계에서 한쪽 방향으로 일정한 윤곽 오차 (≈ res/2 = 10 µm) | `make_grid()` 공용 사용, 칸 중심 규칙 문서화 |
| 실수 간격 `np.arange` 로 개수가 1개 달라짐 | 기준과 측정 배열 모양이 달라 뺄셈 오류 | 개수를 정수로 먼저 계산 (`make_grid` 방식) |
| 빈 칸을 보간으로 채움 | 가림 영역에서 오차가 0에 가깝게 나옴, 커버리지 100 % 로 보고 | 지표용은 NaN 유지, 보간은 `fill_for_display_only` 로 그림에만 |
| 평균 사용 | 반사 스파이크 근처 칸이 크게 튐 | 중앙값 사용 |
| 격자 간격을 점 간격보다 작게 설정 (예: 0.01 mm) | 줄무늬 모양 NaN 이 30~50 % | 격자 ≥ max(δx, 스캔 간격) |
| {M} 높이맵을 회전·보간해서 {G} 로 옮김 | 경계가 한 번 더 뭉개짐, 윤곽 지표 악화 | 점군에 `T_G_M` 적용 후 G3 격자로 다시 격자화 |
| 격자 정보 없이 `.npy` 만 저장 | 몇 달 뒤 원점·간격을 몰라 재사용 불가 | `save_heightmap()` 으로 JSON 동시 저장 |
| NaN 점(F1 에서 레이저 없음)을 그대로 넣음 | `binned_statistic_2d` 결과가 NaN 으로 오염 | 입력 단계에서 `np.isfinite` 로 제거 (코드에 포함) |

---

## 9. 위험 요소

- **스테이지 트리거 누락(C1)**: 프로파일 한 줄이 빠지면 높이맵에 가로 NaN 줄이 생깁니다. 커버리지 지표가 떨어지는지 매 스캔 자동 확인합니다 (`coverage_pct` < 98 % → 경고).
- **스캔 간격 ≠ 격자 간격**: 엔코더 배율(D3)이 1 % 틀리면 Y 간격이 0.0202 mm 가 되어 100칸마다 빈 줄이 생깁니다. 빈 칸 패턴이 주기적이면 D3 를 다시 확인합니다.
- **대용량**: 50 × 50 mm 를 0.02 mm 로 격자화하면 625만 칸, float32 25 MB 입니다. 점이 1,000만 개 이상이면 메모리 2~3 GB 가 필요할 수 있으니 영역을 나눠 처리합니다.
- **2.5D 한계**: 돌출부 아래(오버행)는 높이맵에 담기지 않습니다. 시편 설계(E3)에서 오버행을 피합니다.
- **좌표계 혼동**: `_M` 과 `_G` 파일이 섞이면 오차 지도 전체가 어긋납니다. 파일 이름과 JSON 의 `frame` 필드를 항상 함께 확인합니다.

---

## 10. 기록 양식

`results/<scan_id>/<scan_id>_H1_report.yaml`
```yaml
scan_id: S03_r02
frame: M                  # M 또는 G
calibration_id: CAL-2026-10-06-A
git_commit: ""
grid:
  x0_mm:
  y0_mm:
  res_mm: 0.02
  nx:
  ny:
input_points: 0           # NaN 제거 전
input_points_finite: 0
statistic: median
min_count: 1
count_histogram: {0: , 1: , 2: , 3+: }
coverage_pct:             # 관심 영역 기준
coverage_roi: "M_ref dilated 1 mm"   # 무엇을 기준으로 계산했는지
runtime_s:
notes: ""
```

주간 점검표

| 날짜 | scan_id | 격자 간격 | 커버리지 % | 빈 칸 패턴 (없음/점/줄무늬) | 0.02 vs 0.04 단차 차이 µm | 확인자 |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 11. 참고 자료

- SciPy 문서: `scipy.stats.binned_statistic_2d`, `scipy.ndimage.distance_transform_edt`
- NumPy 문서: "NumPy: the absolute basics for beginners", 배열 인덱싱(Indexing on ndarrays)
- ISO 25178-2 (면 표면 조직: 용어·정의·매개변수) — 높이맵 형태의 면 측정 데이터 개념
- 청사진 관련 절: [BLUEPRINT](../../BLUEPRINT.md) H1, C4 좌표계, E2 가림, G3 격자 규칙
