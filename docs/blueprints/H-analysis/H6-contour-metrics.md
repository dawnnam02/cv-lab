# H6. 2D 윤곽 지표 (마스크 비교)

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: H. 처리·분석

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-29 ~ 2027-01-11 (W13-14) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [H4 정합](H4-registration.md), [G3 마스크·기준 높이맵](../G-reference/G3-mask-heightmap.md), [G4 비교 영역(마스킹)](../G-reference/G4-evaluation-masks.md), [G2 비드 형상 모델](../G-reference/G2-bead-model.md), [E2 가림·엣지 효과](../E-specimen/E2-occlusion-edges.md) |
| 후행 요소 | [H7 치수·형상 지표](H7-dimensional-metrics.md), [H8 통계 분석](H8-statistics.md), [J4 시각화·리포트](../J-software/J4-visualization-report.md), [I3 교차검증](../I-reliability/I3-cross-validation.md) (현미경 윤곽과 비교) |
| 관련 마일스톤 | M4: 시편 1개 전체 파이프라인 완주 (W13-14) |

---

## 1. 목적

위에서 본 **모양(윤곽)** 이 G코드 기준과 얼마나 다른지 수치로 나타냅니다. 높이(H5)와 달리 여기서는 **경계 자체가 주인공**입니다.

| 지표 | 묻는 질문 |
|---|---|
| IoU, Dice | 두 영역이 얼마나 겹치나? (0~1) |
| 과충진 / 미충진 면적 [mm²] | 남는 재료와 빠진 재료가 각각 얼마나 되나? |
| 평균 부호 윤곽 거리 [µm] | 경계가 평균적으로 바깥(+)으로 나왔나, 안(−)으로 들어갔나? |
| HD95 [µm] | 경계가 "대부분" 얼마나 멀리까지 벗어났나? |
| Hausdorff [µm] | 가장 멀리 벗어난 곳은? (이상치 민감) |
| 문턱 민감도 | 측정 마스크를 만드는 높이 기준을 바꾸면 결과가 얼마나 변하나? |

(A = 기준 `M_ref` / 설계 다각형, B = 측정 `M_meas` / 측정 등고선)

---

## 2. 배경 지식 (초보자용)

### 2.1 IoU 와 Dice
```
IoU  = |A ∩ B| / |A ∪ B|               (겹친 넓이 ÷ 합친 넓이)
Dice = 2|A ∩ B| / (|A| + |B|)           (항상 Dice ≥ IoU,  Dice = 2·IoU / (1 + IoU))
```
- 절반만 겹친 같은 크기 사각형 두 개: IoU = 1/3, Dice = 1/2 (`test_절반_겹친_사각형의_IoU는_3분의1`, J3 예시).
- **크기 효과**: 경계가 모두 +50 µm 밀려도 2 mm 사각형은 IoU 0.907, 20 mm 사각형은 0.990 입니다 (6.2 데모). 크기가 다른 형상끼리는 IoU 가 아니라 **윤곽 거리(µm)** 로 비교합니다.

### 2.2 측정 마스크는 "문턱"으로 만든다 (G4)
측정 높이맵에서 "재료가 있다"고 판단하는 기준:
```
M_meas = H_meas > (해당 층 Z − h/2)          예: 최상층 Z = 1.0 mm, h = 0.2 mm → 0.9 mm
```
이 기준이 왜 Z − h/2 일까요? G2 비드 단면은 옆면이 반지름 h/2 인 반원이고, 그 반원의 중심 높이가 Z − h/2 입니다. 즉 **비드가 가장 옆으로 튀어나온 높이**가 Z − h/2 입니다.
하지만 실제 센서는 경계를 흐리게 보기 때문에(E2, 레이저 선 두께·스펙클), 문턱을 조금만 바꿔도 경계 위치가 달라질 수 있습니다 → **민감도 확인 필수** (청사진 H6: 기준값 ±20 %). 이 문서에서는 `h/2` 오프셋을 ±20 % 바꿉니다 (0.92 / 0.90 / 0.88 mm).

### 2.3 래스터 마스크 vs 서브픽셀 윤곽
- **래스터(칸) 마스크**: 칸마다 True/False. 경계가 칸 단위(0.02 mm)로 계단 모양입니다. IoU·면적은 이걸로 계산합니다.
- **서브픽셀 윤곽**: 높이맵에서 높이 = 문턱인 선을 칸 사이 선형 보간으로 찾습니다(`contourpy`). 경계 위치를 칸보다 훨씬 정밀하게 얻습니다. 윤곽 거리는 이걸로 계산합니다.
- **기준 경계**는 래스터가 아니라 **G3 의 설계 다각형(shapely)** 을 그대로 씁니다 → 기준 쪽 양자화 오차가 없습니다.
- 주의: G코드 좌표는 10.000 같은 딱 떨어지는 값이 많아, 경계가 **칸 중심 위에 정확히** 놓이기 쉽습니다. 그러면 경계와 평행한 칸 한 줄이 문턱을 한꺼번에 넘나들어 **면적·IoU 가 계단식으로 크게** 바뀝니다 (6.2 데모). 윤곽 거리는 이 영향을 받지 않습니다.

### 2.4 윤곽 거리의 두 방향과 부호
- **B → A** (`d_BA`): 측정 등고선 위의 점마다 기준 경계까지 최단 거리. **기준 다각형 밖이면 + (재료 과다)**, 안이면 −. 평균 부호 윤곽 거리는 이것의 평균입니다 (청사진 정의).
- **A → B** (`d_AB`): 기준 경계를 0.02 mm 간격으로 샘플링한 점마다 측정 등고선까지 거리. 부호는 "그 점의 측정 높이 > 문턱이면 +" (재료가 기준 경계를 넘어섰음).
- 한 방향만 보면 놓치는 것이 있습니다. 예: 측정에서 **통째로 빠진 작은 핀**은 측정 등고선이 없으니 B→A 에는 안 나타나고 A→B 에만 큰 값으로 나타납니다.
- **HD95** = max(P95|d_BA|, P95|d_AB|), **Hausdorff** = max(max|d_BA|, max|d_AB|). (HD95 정의는 문헌마다 조금씩 다르므로 보고서에 이 정의를 적습니다.)

### 2.5 Hausdorff 는 왜 HD95 와 같이 보고하나
실(stringing) 한 가닥, 먼지 하나가 경계에서 0.5 mm 떨어져 있으면 Hausdorff 는 500 µm 가 되지만 HD95 는 거의 변하지 않습니다. 두 값을 같이 보고, 차이가 크면 "국소 이상"이 있다는 신호로 씁니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 내용 |
|---|---|---|---|
| 입력 | `<scan_id>_heightmap_G.npy` + `_grid_G.json` | float32 | H4 후 측정 높이맵 ({G}, G3 격자) |
| 입력 | G3 층 다각형 (`<gcode>_layer_<k>.wkt`) | WKT | 기준 경계 (설계, 서브픽셀 정확) |
| 입력 | `M_ref`, `M_valid`, `M_type` | bool npy | G3/G4 |
| 입력 | 층 Z, 층 높이 h | YAML/JSON | G1·G2 (예: Z = 1.0, h = 0.2) |
| 산출 | `<scan_id>_H6_contour_metrics.csv` | CSV | 형상(영역)별 1행: level, iou, dice, over_mm2, under_mm2, mean_signed_um, mean_abs_um, hd95_um, hausdorff_um, n_meas_pts, n_ref_pts |
| 산출 | `<scan_id>_H6_threshold_sensitivity.csv` | CSV | 문턱 0.8 / 1.0 / 1.2 배 (+ 50 % 높이) 별 같은 지표 |
| 산출 | `<scan_id>_contour_dist.npz` | npz | 측정 등고선 점 좌표와 d_BA (그림·H7 용) |
| 산출 | 그림 (J4) | PNG | 마스크 오버레이(기준만 파랑, 측정만 빨강, 겹침 회색) / 윤곽 거리 색 지도 (±0.2 mm, `RdBu_r`) |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 측정 마스크 문턱 | Z − h/2 / 높이 50 % / Otsu 자동 | **Z − h/2** (G4 정의) + 민감도 | G2 비드 모델의 최대 폭 높이 |
| 민감도 범위 | ±10 / **±20** % | **h/2 오프셋 ±20 %** (+ 50 % 높이 참고값) | 청사진 H6 |
| 기준 경계 표현 | 래스터 마스크 / **설계 다각형** | **설계 다각형** (거리), 래스터 (IoU·면적) | 기준 쪽 양자화 제거 |
| 측정 경계 표현 | 래스터 경계 칸 / **서브픽셀 등고선** | **서브픽셀 등고선** | 2.3 절 |
| HD95 정의 | B→A 만 / **양방향 최대** | **양방향 최대** | 빠진 형상까지 포착 (2.4 절) |
| 기준 경계 샘플 간격 | 0.01 / **0.02** / 0.05 mm | **격자 간격과 같게 (0.02)** | 점 수 균형 |
| `M_edge` 적용 | 적용 / **미적용** | **미적용**, 단 `M_valid` 는 적용 | 청사진 G4: 윤곽은 경계가 핵심 |
| 크기가 다른 형상 비교 | IoU / **윤곽 거리** | **윤곽 거리 µm** | 2.1 크기 효과 |
| 결측 칸 처리 | 0 으로 / **NaN 유지(등고선 끊김)** | **NaN 유지** | 가림을 경계로 오인하지 않음 |
| 형상별 계산 | 전체만 / **형상별** | **형상별** (E3 ID) + 전체 | 원인 분석 |

---

## 5. 수행 절차

1. **기준 다각형 준비 (0.5일)**
   - [ ] G3 에서 최상층(또는 비교 층) 다각형을 WKT 로 저장, 스커트·브림 제외(G4 `M_type`)
   - [ ] 형상별(E3 ID) 다각형으로 나누기 (`shapely` `intersection` 으로 영역 분할)
2. **모듈 구현·단위 테스트 (1일)**
   - [ ] 6.1 `h6_contour_metrics.py` → `src/cvlab/metrics.py`
   - [ ] `pytest -q test_h6.py` 통과 (IoU 1/3, 균일 +50 µm 윤곽 거리)
3. **합성 데모로 동작 이해 (0.5일)**
   - [ ] 6.2 데모 실행, 문턱에 따른 변화와 크기 효과 확인
4. **실측 시편 적용 (1일)**
   - [ ] `M_meas = H > Z − h/2`, `M_valid` 적용 후 IoU·Dice·면적
   - [ ] 등고선 추출 → 양방향 거리 → 평균 부호·HD95·Hausdorff
   - [ ] 마스크 오버레이와 윤곽 거리 지도 그림 저장
5. **문턱 민감도 (0.5일)**
   - [ ] 0.8 / 1.0 / 1.2 배 + 50 % 높이로 반복, CSV 저장
   - [ ] 평균 부호 거리 변화가 7장 기준을 넘으면 보고서에 "문턱 의존" 명시
6. **경계 흐림 보정 근거 확보 (I3 연계, 0.5일)**
   - [ ] 대표 시편 1개를 광학 현미경으로 외곽 치수 측정 → 문턱별 측정 경계 중 어느 것이 현미경과 가장 가까운지 기록
7. **형상별 표 작성 (0.5일)**
   - [ ] 형상별 CSV 행, Hausdorff − HD95 > 100 µm 인 형상에 "국소 이상" 표시

---

## 6. Python 구현

### 6.1 모듈 `h6_contour_metrics.py`

```python
"""H6. 2D 윤곽 지표 모듈. 최종적으로 src/cvlab/metrics.py 에 합칩니다.
A = 기준(M_ref / 설계 다각형), B = 측정(M_meas / 측정 등고선). 거리 부호: 기준 바깥(재료 과다) +."""
import numpy as np
import shapely
import contourpy
from shapely.geometry import MultiLineString
from scipy.ndimage import map_coordinates


def mask_metrics(A, B, res, valid=None):
    """래스터 마스크 지표. valid(측정 유효 칸)가 있으면 그 안에서만 비교."""
    if valid is not None:
        A, B = A & valid, B & valid
    inter, union = (A & B).sum(), (A | B).sum()
    return {"iou": inter / union, "dice": 2 * inter / (A.sum() + B.sum()),
            "over_mm2": (B & ~A).sum() * res ** 2,      # 과충진: 있으면 안 되는 곳의 재료
            "under_mm2": (A & ~B).sum() * res ** 2,     # 미충진: 있어야 하는데 빠진 재료
            "ref_mm2": A.sum() * res ** 2, "meas_mm2": B.sum() * res ** 2}


def measured_contours(H, xs, ys, level):
    """측정 높이맵의 등고선(높이 = level)을 서브픽셀 선들로 추출. NaN 칸은 건너뜀."""
    lines = contourpy.contour_generator(xs, ys, np.ma.masked_invalid(H)).lines(level)
    return [ln for ln in lines if len(ln) >= 2]


def sample_boundary(poly, step):
    """다각형 경계(바깥 + 구멍)를 step 간격 점으로 샘플링"""
    pts = []
    for ring in [poly.exterior, *poly.interiors] if poly.geom_type == "Polygon" else \
            [r for p in poly.geoms for r in [p.exterior, *p.interiors]]:
        d = np.arange(0, ring.length, step)
        pts.append(shapely.get_coordinates(shapely.line_interpolate_point(ring, d)))
    return np.vstack(pts)


def contour_distances(ref_poly, lines, H, xs, ys, level, step):
    """양방향 윤곽 거리 [mm].
    d_BA: 측정 등고선 점 → 기준 경계 (부호: 기준 다각형 밖 +)
    d_AB: 기준 경계 점 → 측정 등고선 (부호: 그 위치의 측정 높이 > level 이면 + = 재료가 기준 경계를 넘어감)"""
    pB = np.vstack(lines)
    P = shapely.points(pB)
    dBA = shapely.distance(P, ref_poly.boundary)
    dBA = np.where(shapely.contains(ref_poly, P), -dBA, dBA)
    pA = sample_boundary(ref_poly, step)
    dAB = shapely.distance(shapely.points(pA), MultiLineString([ln for ln in lines]))
    res = xs[1] - xs[0]
    rc = np.vstack([(pA[:, 1] - ys[0]) / res, (pA[:, 0] - xs[0]) / res])     # (행, 열) 실수 인덱스
    h_at = map_coordinates(np.nan_to_num(H, nan=-1.0), rc, order=1)          # 이중선형 보간
    dAB = np.where(h_at > level, dAB, -dAB)
    return dBA, dAB


def contour_metrics(dBA, dAB):
    a, b = np.abs(dBA), np.abs(dAB)
    return {"mean_signed_um": 1000 * dBA.mean(),               # 경계가 평균적으로 바깥(+)/안(−)
            "mean_abs_um": 1000 * a.mean(),
            "hd95_um": 1000 * max(np.percentile(a, 95), np.percentile(b, 95)),   # 양방향 95 % 중 큰 값
            "hausdorff_um": 1000 * max(a.max(), b.max()),
            "n_meas_pts": int(len(dBA)), "n_ref_pts": int(len(dAB))}


def rasterize(poly, xs, ys):
    X, Y = np.meshgrid(xs, ys)
    return shapely.contains_xy(poly, X, Y)
```

### 6.2 데모 `demo_h6.py` (정답을 아는 합성 윤곽)

기준: 10 × 10 mm 사각형 + Ø4 구멍, 최상층 Z = 1.0 mm, 층 높이 h = 0.2 mm.
정답: 모든 경계가 **+50 µm 과충진**, 볼록 모서리는 반경 ≈ 0.35 mm 로 뭉개짐, 경계 밖 0.5 mm 지점에 실(stringing) 한 가닥.
측정 높이맵: 경계 근처는 G2 반원 옆면 모양, 센서 흐림 σ 20 µm, 노이즈 5 µm, 격자 0.02 mm.

```python
"""H6 데모: 정답을 아는 합성 윤곽 (전체 +50 um 과충진, 모서리 r 0.3 mm 뭉개짐, 실 한 가닥)."""
import numpy as np
import shapely
from shapely.geometry import box, Point
from scipy.ndimage import gaussian_filter
from h6_contour_metrics import (mask_metrics, measured_contours, contour_distances,
                                contour_metrics, rasterize)

rng = np.random.default_rng(6)
res, Z, h = 0.02, 1.0, 0.2                                    # 격자, 최상층 Z, 층 높이
r = h / 2                                                     # 비드 옆면 반원 반지름
xs = np.arange(-2, 12, res); ys = np.arange(-2, 12, res)
X, Y = np.meshgrid(xs, ys)

ref = box(0, 0, 10, 10).difference(Point(5, 5).buffer(2.0, quad_segs=64))   # G3 기준: 10 mm 사각 + Ø4 구멍
actual = ref.buffer(-0.3).buffer(0.35, quad_segs=32)          # 정답: 경계 +50 um, 볼록 모서리 r≈0.35
actual = actual.union(Point(10.5, 3.0).buffer(0.04))          # 실(stringing) 한 가닥: 경계 밖 0.5 mm 지점

# 측정 높이맵: 경계 근처는 비드 옆면 반원 모양(G2) → 센서 흐림 σ 20 um → 노이즈 5 um
P = shapely.points(X.ravel(), Y.ravel())
inside = shapely.contains(actual, P)
dist = shapely.distance(P, actual.boundary)
delta = np.where(inside, -dist, dist).reshape(X.shape)        # 실제 경계에서의 부호 거리 (+ 바깥)
H = np.where(delta <= -r, Z, Z - r + np.sqrt(np.clip(r ** 2 - (delta + r) ** 2, 0, None)))
H[delta > 0] = 0.0
H = gaussian_filter(H, 0.02 / res) + rng.normal(0, 0.005, H.shape)

A = rasterize(ref, xs, ys)
print("문턱(level)      IoU     Dice  과충진mm²  미충진mm²  평균부호[um]  HD95[um]  Hausdorff[um]")
for name, level in [("Z−h/2 ×0.8", Z - 0.8 * r), ("Z−h/2 (기본)", Z - r), ("Z−h/2 ×1.2", Z - 1.2 * r), ("높이 50 %", 0.5 * Z)]:
    B = H > level
    mm = mask_metrics(A, B, res)
    lines = measured_contours(H, xs, ys, level)
    dBA, dAB = contour_distances(ref, lines, H, xs, ys, level, step=res)
    cm = contour_metrics(dBA, dAB)
    print(f"{name:<12} {level:5.3f}  {mm['iou']:.4f}  {mm['dice']:.4f}  {mm['over_mm2']:8.3f}  {mm['under_mm2']:8.3f}"
          f"  {cm['mean_signed_um']:+10.1f}  {cm['hd95_um']:8.1f}  {cm['hausdorff_um']:10.1f}")

# 크기 효과: 같은 +50 um 과충진이라도 작은 형상은 IoU 가 훨씬 낮다
print("\n크기 효과 (모든 경계 +50 um):")
for L in (2.0, 5.0, 20.0):
    sq = box(0, 0, L, L)
    g = np.arange(-1, L + 1, 0.005)
    a, b = rasterize(sq, g, g), rasterize(sq.buffer(0.05, join_style="mitre"), g, g)
    print(f"  {L:4.0f} mm 정사각형: IoU {mask_metrics(a, b, 0.005)['iou']:.4f}, 평균 윤곽 거리 +50.0 um (동일)")
```

```text
$ python3 demo_h6.py
문턱(level)      IoU     Dice  과충진mm²  미충진mm²  평균부호[um]  HD95[um]  Hausdorff[um]
Z−h/2 ×0.8   0.920  0.9920  0.9960     0.650     0.052       +16.4      20.2       111.2
Z−h/2 (기본)   0.900  0.9834  0.9916     1.431     0.048       +19.2      23.4       108.4
Z−h/2 ×1.2   0.880  0.9831  0.9915     1.454     0.047       +21.1      25.8       105.7
높이 50 %      0.500  0.9713  0.9855     2.555     0.024       +49.2      51.9       526.4

크기 효과 (모든 경계 +50 um):
     2 mm 정사각형: IoU 0.9070, 평균 윤곽 거리 +50.0 um (동일)
     5 mm 정사각형: IoU 0.9612, 평균 윤곽 거리 +50.0 um (동일)
    20 mm 정사각형: IoU 0.9901, 평균 윤곽 거리 +50.0 um (동일)
```

**결과 읽는 법**
- **문턱이 Z − h/2 (0.90 mm)** 일 때 평균 부호 윤곽 거리는 +19.2 µm 로, 참값 +50 µm 보다 작습니다. 반원 옆면의 가장 바깥 점이 정확히 0.90 mm 높이에 있는데, 센서 흐림(σ 20 µm)이 그 바로 바깥의 0 높이와 섞이면서 0.90 mm 등고선이 약 30 µm 안쪽으로 들어왔기 때문입니다.
- **50 % 높이(0.50 mm)** 에서는 +49.2 µm 로 참값에 가깝습니다. 하지만 이 문턱에서는 실 한 가닥까지 "재료"로 잡혀 Hausdorff 가 526 µm 로 튑니다 (HD95 는 51.9 µm 로 거의 그대로).
- **IoU 가 0.9834 → 0.9920 으로 크게 변한 이유** (문턱 0.90 → 0.92): 사각형 경계가 격자 칸 중심 위에 정확히 놓여, 경계와 평행한 칸 한 줄(둘레 40 mm × 0.02 mm ≈ 0.8 mm²)이 한꺼번에 문턱을 넘나들었습니다. 과충진 면적 차이 1.431 − 0.650 = 0.78 mm² 가 이것입니다. 같은 변화에서 서브픽셀 윤곽 거리는 19.2 → 16.4 µm 로 완만하게 변했습니다 → **윤곽 거리가 더 안정적인 주 지표**입니다.
- Hausdorff 105~111 µm 는 뭉개진 볼록 모서리에서 나옵니다(설계 모서리 꼭짓점이 측정 등고선에서 가장 멀다).
- **크기 효과**: 같은 +50 µm 인데 IoU 가 0.907(2 mm) ~ 0.990(20 mm) 로 다릅니다.

**이 결과가 주는 실무 규칙**
1. 문턱은 G4 정의(Z − h/2)를 기본으로 하되, **50 % 높이 결과를 함께 기록**하고, 어느 쪽이 실제 경계에 가까운지는 현미경 교차검증(I3)으로 정합니다.
2. 결론(조건 A 가 B 보다 과충진이 크다 등)이 **모든 문턱에서 같은 방향**인지 확인합니다. 방향이 바뀌면 결론을 내리지 않습니다.

### 6.3 단위 테스트 `test_h6.py`

```python
"""H6 단위 테스트 (J3 IoU 예시 포함). 실행: pytest -q test_h6.py"""
import numpy as np
from shapely.geometry import box
from h6_contour_metrics import mask_metrics, contour_distances, contour_metrics


def test_절반_겹친_사각형의_IoU는_3분의1():
    A = np.zeros((10, 20), bool); A[:, 0:10] = True
    B = np.zeros((10, 20), bool); B[:, 5:15] = True
    m = mask_metrics(A, B, res=0.1)
    assert abs(m["iou"] - 1 / 3) < 1e-12 and abs(m["dice"] - 0.5) < 1e-12
    assert abs(m["over_mm2"] - 0.5) < 1e-12 and abs(m["under_mm2"] - 0.5) < 1e-12


def test_균일하게_큰_사각형의_윤곽거리():
    res = 0.01
    xs = ys = np.arange(-1, 6, res)
    X, Y = np.meshgrid(xs, ys)
    H = np.where((abs(X - 2) <= 2.05) & (abs(Y - 2) <= 2.05), 1.0, 0.0)   # 기준 4×4 보다 사방 +50 um
    ref = box(0, 0, 4, 4)
    import contourpy
    lines = contourpy.contour_generator(xs, ys, H).lines(0.5)
    dBA, dAB = contour_distances(ref, lines, H, xs, ys, 0.5, step=res)
    m = contour_metrics(dBA, dAB)
    assert abs(m["mean_signed_um"] - 50) < 6          # 격자 양자화(±res/2) 이내
    assert np.all(dAB > 0)                             # 기준 경계는 모두 측정 재료 안 → +
```

```text
$ python3 -m pytest -q test_h6.py
2 passed in 0.xxs
```

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| IoU·Dice 계산 | 반 겹침 사각형 (pytest) | IoU = 1/3, Dice = 1/2 (정확히) |
| 윤곽 거리 부호·크기 | 균일 +50 µm 사각형, 흐림 없음 (pytest) | 평균 부호 +50 ± 6 µm, d_AB 모두 + |
| 문턱 민감도 (실측) | 0.8 / 1.0 / 1.2 배 | 평균 부호 거리 변화 ≤ 10 µm 또는 I1 의 XY 확장불확도 이하. 초과 시 보고서에 명시 |
| IoU 민감도 (실측) | 0.8 / 1.0 / 1.2 배 | 변화 ≤ 0.01 (초과 시 2.3 절 격자 정렬 영향 확인) |
| 50 % 높이 비교 | 실측 | 평균 부호 거리 차이를 기록 (기준 아님, I3 판단 자료) |
| 현미경 교차검증 (I3) | 대표 시편 외곽 치수 | 채택한 문턱의 치수 차이 ≤ 20 µm |
| 반복성 | 같은 시편 3회 | 평균 부호 거리 표준편차 ≤ 5 µm, IoU ≤ 0.002 |
| 단위 테스트 | `pytest test_h6.py` | 전부 통과 |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 기준도 래스터 마스크로 경계 추출 | 거리 결과가 ±10 µm 계단 모양으로 흔들림 | 기준은 설계 다각형 사용 |
| 측정 경계를 래스터 경계 칸 중심으로 | 반 칸(10 µm) 안쪽으로 치우침 | 서브픽셀 등고선 사용 |
| 한 방향 거리만 계산 | 통째로 빠진 작은 형상을 놓침 | 양방향 HD95·Hausdorff |
| 부호 규칙 반대 | 과충진이 −로 나옴 | 기준 밖 + (A1), pytest 로 확인 |
| `M_edge` 를 윤곽 지표에 적용 | 경계를 지워 놓고 경계를 평가 | 윤곽 지표에는 `M_valid` 만 |
| NaN 을 0 으로 채움 | 가림 영역 가장자리가 가짜 경계로 잡힘 | `masked_invalid` 로 등고선 끊기 |
| 크기가 다른 형상의 IoU 비교 | 작은 형상이 늘 나빠 보임 | 윤곽 거리로 비교 |
| 문턱 하나로만 결론 | 다른 연구실 문턱에서는 결론이 뒤집힘 | 민감도 표와 50 % 높이 결과 함께 보고 |
| 평활화(H2)한 높이맵 사용 | 모서리가 실제보다 더 둥글게 | 윤곽 지표는 평활화 전 높이맵 사용 |
| Hausdorff 만 보고 | 먼지 하나로 시편 평가가 바뀜 | HD95 를 주 지표로 |

---

## 9. 위험 요소

- **경계 흐림의 계통 오차**: 6.2 처럼 센서 흐림만으로 경계가 수십 µm 안쪽으로 잡힐 수 있습니다. 이 값은 측정 대상의 오차가 아니라 측정 방법의 성질입니다. I3 현미경 비교와 I1 의 XY 불확도 예산에 넣습니다.
- **가림(E2)**: 카메라 반대쪽 벽 아래는 그림자라 경계가 NaN 에 걸려 끊깁니다. 끊긴 구간 길이를 기록하고(측정 등고선 길이 ÷ 기준 둘레), 70 % 미만이면 그 형상의 윤곽 지표를 `CHECK` 로 표시합니다.
- **2.5D 한계**: 벽이 기울거나 오버행이 있으면 위에서 본 윤곽은 최상단 윤곽일 뿐입니다. 층별 측정(C2 2단계)에서 층 마스크와 비교하면 보완됩니다.
- **문턱이 다른 층에 걸림**: 계단 시편에서 Z − h/2 문턱은 그 층에만 맞습니다. 층(형상)마다 자기 Z 로 문턱을 따로 정합니다.

---

## 10. 기록 양식

`_H6_contour_metrics.csv` 열
```text
scan_id,specimen_id,feature_id,layer_z_mm,level_mm,level_rule,iou,dice,over_mm2,under_mm2,ref_mm2,meas_mm2,mean_signed_um,mean_abs_um,hd95_um,hausdorff_um,n_meas_pts,n_ref_pts,contour_coverage_pct,flag
```
`level_rule` 값: `Z-h/2`, `Z-0.8h/2`, `Z-1.2h/2`, `50pct`

문턱 민감도 요약표

| 형상 | 문턱 규칙 | IoU | 평균 부호 µm | HD95 µm | Hausdorff µm | 결론 방향 동일? |
|---|---|---|---|---|---|---|
| | Z − 0.8·h/2 | | | | | |
| | Z − h/2 | | | | | |
| | Z − 1.2·h/2 | | | | | |
| | 50 % 높이 | | | | | |

---

## 11. 참고 자료

- Jaccard, P. (1912). The distribution of the flora in the alpine zone. *New Phytologist* — IoU(Jaccard 지수)의 원전
- Dice, L. R. (1945). Measures of the amount of ecologic association between species. *Ecology*, 26(3).
- Huttenlocher, D. P., Klanderman, G. A., & Rucklidge, W. J. (1993). Comparing images using the Hausdorff distance. *IEEE TPAMI*, 15(9).
- shapely 2.x 문서: `shapely.distance`, `shapely.contains`, `line_interpolate_point`; contourpy 문서 (`contour_generator`); OpenCV 문서: `cv2.findContours`, `cv2.distanceTransform` (래스터 방식 대안); SciPy 문서: `scipy.spatial.cKDTree`, `scipy.ndimage.map_coordinates`
- 청사진 관련 절: [BLUEPRINT](../../BLUEPRINT.md) H6, G2, G4, E2, J4
