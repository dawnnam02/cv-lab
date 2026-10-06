# G5. CAD 기준과의 관계 — 오차 원인 분리

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: G. G코드 기준 모델 (마스킹)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-11-03 ~ 2026-11-16 (W5-6) |
| 우선순위 | 낮음 (선택 확장) |
| 트랙 | 소프트웨어 |
| 선행 요소 | [G3 마스크·높이맵](G3-mask-heightmap.md) · [G4 평가 마스크](G4-evaluation-masks.md) · [G2 비드 모델](G2-bead-model.md) · [E3 시편 설계](../E-specimen/E3-test-artifact.md) · [A1 오차의 정의](../A-goals/A1-error-definition.md) |
| 후행 요소 | [H5 높이 지표](../H-analysis/H5-height-metrics.md) · [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) · [H8 통계 분석](../H-analysis/H8-statistics.md) · [I1 불확도](../I-reliability/I1-uncertainty.md) · [K5 산출물·논문](../K-management/K5-deliverables-paper.md) |
| 관련 마일스톤 | **M6** (최종 보고서의 "오차 원인 분리" 절). W5–6에는 코드와 합성 검증만, 실제 적용은 본 실험(W18–21) 데이터로 |

---

## 1. 목적

```
설계 CAD(STL) ──(슬라이싱 오차)──▶ G코드 ──(장비·공정 오차)──▶ 실제 형상
```

이 과제의 주 기준은 **G코드**입니다. G코드를 기준으로 하면 슬라이서가 만든 차이를 빼고 **장비·공정 오차**만 볼 수 있습니다. 하지만 사용자(설계자)에게 중요한 것은 결국 **CAD 대비 총 오차**입니다. 이 요소는 CAD 기준을 함께 계산해서

```
총 오차 (측정 − CAD) = 슬라이싱 오차 (G코드 − CAD) + 공정 오차 (측정 − G코드)
```

로 **원인을 분리**하는 방법을 정합니다. 부호 규칙은 A1과 같습니다: **측정값(또는 하위 단계) − 기준값(상위 단계), + 는 재료 과다**.

우선순위가 낮은 선택 확장이므로, W5–6에는 **해석적으로 정의되는 단순 형상(원기둥)** 으로 코드와 계산을 검증하는 데까지만 합니다.

## 2. 배경 지식 (초보자용)

**슬라이싱 오차의 대표 원인 3가지**

| 원인 | 설명 | 크기 예 |
|---|---|---|
| **STL 다각형화** | CAD의 곡면을 삼각형(평면 조각)으로 근사. 원이 정N각형이 됨 | 반지름 r, N각형의 최대 안쪽 이탈(현 처짐) = r(1 − cos(π/N)). r = 5 mm, N = 32 → **0.024 mm** |
| **층 양자화 (Z)** | 높이가 층높이 h의 배수로만 표현됨 | CAD 5.07 mm, h = 0.2 → G코드 5.0 또는 5.2 mm → **−0.07 또는 +0.13 mm** |
| **경로 생성 규칙** | 외벽 경로를 윤곽에서 w/2 안쪽에 놓음, 구멍 보정, 모서리 둥글림, 얇은 벽 생략 | 모서리 반지름 ≈ w/2 = 0.21 mm |

**층 양자화 규칙**: 많은 슬라이서는 각 층의 **중간 높이**(z_k − h/2)에서 모델을 자릅니다. 자른 면에 모델이 있으면 그 층을 출력합니다. CAD 높이 5.07 mm, h = 0.2이면 25번째 층(윗면 5.0, 자르는 높이 4.9)은 출력되고 26번째 층(자르는 높이 5.1)은 출력되지 않으므로 G코드 윗면 = 5.0 mm입니다. 슬라이서마다 규칙이 다르므로(가변 층높이, "slice closing radius" 등) **반드시 G코드의 실제 마지막 Z로 확인**합니다.

**덧셈이 항상 성립하는 이유**: 같은 칸에서 `(측정 − G) + (G − CAD) = 측정 − CAD` 는 단순한 항등식입니다. 그래서 분해 자체는 언제나 맞습니다. 중요한 것은 **세 높이맵이 모두 정의된 같은 칸(같은 평가 영역)** 에서 계산하는 것입니다. 영역이 다르면 평균값끼리 더해지지 않습니다.

**주의 — 상쇄**: 6.2절 결과처럼 슬라이싱 오차(지름 −0.031 mm)와 공정 오차(+0.040 mm)가 부호가 반대면 총 오차(+0.009 mm)가 작아 보입니다. **총 오차만 보면 "정확하다"고 잘못 결론**내릴 수 있다는 것이 이 분해의 가장 큰 가치입니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 설명 |
|---|---|---|---|
| 입력 | 시편 CAD | 해석식(원기둥·직육면체 치수) 또는 `data/cad/<시편ID>.step/.stl` | E3 시편 설계 원본 |
| 입력 | G코드 기준 | `ref_r0.02_nominal.npz` (G3) | H_gc |
| 입력 | 측정 높이맵 | `heightmap.npy` (H1–H4 처리 후 {G} 좌표) | H_meas |
| 입력 | 평가 마스크 | `masks.npz` (G4) | 경계 띠 등 |
| 산출물 | `src/cvlab/cad_reference.py` | Python 모듈 | 6.1절 코드 |
| 산출물 | `data/processed/<시편ID>/cad_r0.02.npz` | NumPy | CAD 높이맵 H_cad (G코드 기준과 같은 격자) |
| 산출물 | `results/<스캔ID>/decomposition_height.csv` | CSV | slicing / process / total 의 평균·표준편차·n |
| 산출물 | `results/<스캔ID>/decomposition_dims.csv` | CSV | 치수(지름, 높이, 폭)별 CAD / G코드 / 측정 / 세 가지 차이 |
| 산출물 | `results/slicing_error_<시편ID>.csv` | CSV | 측정 없이 계산되는 슬라이싱 오차표 (시편 설계 단계에서 미리 확인) |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| G5 수행 여부 | 생략 / 단순 형상만 / 전 시편 | **단순 형상(원기둥, 직육면체, 계단)만** | 우선순위 낮음. 해석식 CAD로 충분하고 STL 처리 라이브러리가 필요 없음 |
| CAD 표현 | 해석식 / STL 메쉬 | **해석식** (원·사각형 치수) | 정답이 정확함. 복잡 형상은 STL 단면을 얻는 별도 라이브러리(예: trimesh)가 필요 → 확장 과제 |
| 비교 영역 | 각 높이맵의 자기 영역 / 공통 영역 | **세 맵 공통 영역 − 경계 띠(0.25 mm)** | 덧셈 분해가 평균에서도 성립 |
| 지름 계산 | 면적 등가 지름 / 원 맞춤 | 면적 등가(빠름, 이 문서), 보고용은 **H7 원 맞춤과 함께** | 면적 등가는 형상 전체 평균, 원 맞춤은 경계 점 기반 |
| CAD 높이 선택 | 층높이 배수 / 임의 | **E3 시편 높이는 층높이 배수로 설계** (예: 5.0 mm) + 의도적 비배수 시편 1개 | 배수로 하면 Z 양자화 오차 0 → 공정 오차만 남음. 비배수 1개로 슬라이서 규칙 확인 |
| STL 해상도 | 기본 / 세밀 | **세밀**: 현 처짐 ≤ 0.005 mm 로 내보내기 | 0.024 mm(N = 32)는 측정 목표(±0.04 mm)의 절반 이상 |

## 5. 수행 절차

1. **해석식 CAD 높이맵 함수 (W5, 반나절)**
   - [ ] 6.1절 `cad_reference.py` 작성. 원기둥 외에 E3에 필요한 직육면체·계단 함수도 같은 방식으로 추가
2. **합성 검증 (W6, 1일)**
   - [ ] 6.2절 실행 → 슬라이싱 −0.07, 공정 −0.03, 총 −0.10 mm, 그리고 slicing + process = total 이 표에서 정확히 성립하는지 확인
   - [ ] 32각형 STL의 G코드 지름이 이론값 9.968 mm(32각형 면적 등가 지름)과 0.001 mm 이내인지 확인
   - [ ] G코드 윤곽 − CAD 원 최솟값이 이론 현 처짐(−0.0241 mm)과 같은지 확인
3. **시편 설계에 반영 (W6, E3 담당자와 1시간)**
   - [ ] E3 시편 높이를 층높이의 배수로, STL 내보내기 현 처짐 ≤ 0.005 mm 로 정함
   - [ ] 슬라이싱 오차표(`slicing_error_<시편ID>.csv`)를 측정 전에 미리 만들어 E3 문서에 첨부
4. **본 실험 데이터 적용 (W18–21)**
   - [ ] 조건별 시편마다 `decomposition_height.csv`, `decomposition_dims.csv` 생성
   - [ ] H8 분석 단위 규칙(시편 하나당 요약값 하나)을 그대로 따름
5. **보고 (W22–24, M6)**
   - [ ] 논문 3장(기준 모델) 또는 6장(결과)에 "총 오차 = 슬라이싱 + 공정" 막대그래프(누적 막대, 부호 표시)

## 6. Python 구현

### 6.1 모듈 — `src/cvlab/cad_reference.py`

```python
"""
cad_reference.py — G5. CAD 기준과 G코드 기준을 함께 써서 오차 원인 분리

  총 오차   = 측정 − CAD
  슬라이싱 오차 = G코드 기준 − CAD     (측정 없이 계산 가능: 순수 소프트웨어 효과)
  공정 오차  = 측정 − G코드 기준      (이 과제의 주 결과)
  → 총 오차 = 슬라이싱 오차 + 공정 오차  (같은 칸·같은 영역에서 항상 성립)
"""
import math

import numpy as np
import pandas as pd
from scipy import ndimage


def cylinder_cad_heightmap(grid, cx, cy, r, height):
    """해석적 CAD: 반지름 r, 높이 height 원기둥. 밖은 NaN"""
    X, Y = np.meshgrid(grid.xs, grid.ys)
    inside = (X - cx) ** 2 + (Y - cy) ** 2 < r ** 2
    H = np.full(X.shape, np.nan)
    H[inside] = height
    return H


def slicer_layer_count(height_cad, h, first_h=None):
    """
    단순 슬라이싱 규칙: 층 k 의 '자르는 높이'(층 중간) z_k − h/2 가 CAD 높이보다 낮으면 그 층을 만든다.
    실제 슬라이서마다 규칙이 다르므로 G코드의 마지막 Z와 반드시 대조할 것.
    """
    first_h = h if first_h is None else first_h
    n, z = 0, 0.0
    while True:
        hk = first_h if n == 0 else h
        if z + hk / 2 >= height_cad:
            return n, round(z, 6)
        z += hk
        n += 1


def equiv_diameter(mask, res, fill_holes=True):
    """
    마스크 면적과 같은 면적의 원 지름 = 2·sqrt(A/π).
    바깥 지름이 목적이므로 내부의 작은 틈(고리 사이 틈 등)은 메우고 계산 (fill_holes)
    """
    if fill_holes:
        mask = ndimage.binary_fill_holes(mask)
    return 2 * math.sqrt(mask.sum() * res * res / math.pi)


def decompose_height(H_cad, H_gc, H_meas, region):
    """region 안의 칸에서 세 가지 높이 차이의 평균/표준편차 [mm]"""
    out = []
    for name, a, b in (("slicing (G - CAD)", H_gc, H_cad),
                       ("process (meas - G)", H_meas, H_gc),
                       ("total (meas - CAD)", H_meas, H_cad)):
        e = (a - b)[region]
        e = e[~np.isnan(e)]
        out.append({"term": name, "mean_mm": e.mean(), "std_mm": e.std(ddof=1), "n": e.size})
    return pd.DataFrame(out)


def decompose_scalar(name, cad, gcode, meas):
    """치수 하나(지름 등)의 분해: 슬라이싱 + 공정 = 총"""
    return {"feature": name, "CAD": cad, "Gcode": gcode, "meas": meas,
            "slicing": gcode - cad, "process": meas - gcode, "total": meas - cad}
```

### 6.2 원기둥 Ø10 × 5.07 mm 분해 예제 — `notebooks/g5_example.py`

G1~G4의 `gcode_parser.py`, `bead_model.py`, `reference_model.py`, `masks.py` 가 필요합니다. 32각형 STL을 슬라이싱한 것과 같은 G코드(동심원 고리 채움)를 직접 만들고, 과압출(선폭 0.46)과 윗면 처짐(−0.03 mm)을 넣은 합성 측정값과 비교합니다.

```python
"""g5_example.py — 원기둥 Ø10 × 5.07 mm: CAD vs G코드 vs (합성)측정 → 오차 원인 분리"""
import math

import numpy as np
import pandas as pd
import shapely

from bead_model import e_per_mm
from cad_reference import (cylinder_cad_heightmap, slicer_layer_count, equiv_diameter,
                           decompose_height, decompose_scalar)
from gcode_parser import parse_gcode_text
from masks import edge_band
from reference_model import make_grid, build_reference, segment_polygon

CX, CY, R_CAD, H_CAD = 50.0, 50.0, 5.0, 5.07     # CAD 원기둥
N_FACET = 32                                      # STL 다각형 면 수 (거칠게 내보낸 STL 가정)
W, H, DF = 0.42, 0.2, 1.75


def ngon_ring(apothem):
    """정N각형(꼭짓점이 CAD 원 위, 면이 원에 내접)을 안쪽으로 줄인 경로. apothem = 중심~변 거리"""
    Rv = apothem / math.cos(math.pi / N_FACET)    # 꼭짓점까지 거리
    ang = [2 * math.pi * i / N_FACET for i in range(N_FACET + 1)]
    return [(CX + Rv * math.cos(a), CY + Rv * math.sin(a)) for a in ang]


def make_cylinder_gcode():
    n_layers, z_top = slicer_layer_count(H_CAD, H)
    a0 = R_CAD * math.cos(math.pi / N_FACET)      # STL 다각형의 apothem
    epm = e_per_mm(W, H, DF)
    out = ["G21", "G90", "M83", "G92 E0"]
    for k in range(n_layers):
        out += [f";LAYER:{k}", f"G0 Z{H * (k + 1):.3f}"]
        i = 0
        while a0 - W / 2 - i * W > W / 2:          # 동심원 고리: 외벽, 내벽, 채움
            t = "WALL-OUTER" if i == 0 else ("WALL-INNER" if i == 1 else "FILL")
            ring = ngon_ring(a0 - W / 2 - i * W)
            out += [f";TYPE:{t}", f"G0 X{ring[0][0]:.4f} Y{ring[0][1]:.4f}"]
            for (xa, ya), (xb, yb) in zip(ring[:-1], ring[1:]):
                out.append(f"G1 X{xb:.4f} Y{yb:.4f} E{epm * math.hypot(xb - xa, yb - ya):.5f}")
            i += 1
        out += [f"G0 X{CX - 0.05:.4f} Y{CY:.4f}",   # 가운데 남은 작은 구멍 메우기
                f"G1 X{CX + 0.05:.4f} Y{CY:.4f} E{epm * 0.1:.5f}"]
    return "\n".join(out) + "\n", n_layers, z_top


g, n_layers, z_top = make_cylinder_gcode()
print(f"슬라이싱: {n_layers}층, 마지막 층 윗면 Z = {z_top:.2f} mm (CAD {H_CAD} mm)")
seg = parse_gcode_text(g).segments
grid = make_grid(seg, res=0.02, margin=1.0)
H_gc = build_reference(seg, grid, W)["H_ref"].astype(float)
H_cad = cylinder_cad_heightmap(grid, CX, CY, R_CAD, H_CAD)

# 합성 측정: 선폭 0.46 (과압출, 한쪽 +0.02 mm), 윗면 −0.03 mm 처짐, 노이즈 5 µm
rng = np.random.default_rng(0)
H_meas = build_reference(seg, grid, 0.46)["H_ref"].astype(float) - 0.03
H_meas += rng.normal(0, 0.005, H_meas.shape)

# 1) 높이: 세 마스크가 모두 있고 경계 띠(0.25 mm)가 아닌 곳에서만
region = ~np.isnan(H_cad) & ~np.isnan(H_gc) & ~np.isnan(H_meas)
region &= ~edge_band(H_gc, grid.res, 0.25, H / 2)
print(decompose_height(H_cad, H_gc, H_meas, region).round(4).to_string(index=False))

# 2) 지름(면적 등가)
D = decompose_scalar("diameter_eq", equiv_diameter(~np.isnan(H_cad), grid.res),
                     equiv_diameter(~np.isnan(H_gc), grid.res),
                     equiv_diameter(H_meas > H / 2, grid.res))
print(pd.DataFrame([D]).round(4).to_string(index=False))

# 3) 슬라이싱 윤곽 오차의 범위: G코드 영역 경계가 CAD 원에서 얼마나 벗어나는지 (+ = 바깥)
ex = seg[(seg.kind == "extrude") & (seg.layer == n_layers - 1)]
poly = segment_polygon(ex, W)
pts = shapely.get_coordinates(shapely.segmentize(poly.exterior, 0.01))
dr = np.hypot(pts[:, 0] - CX, pts[:, 1] - CY) - R_CAD
sag = R_CAD * (1 - math.cos(math.pi / N_FACET))
print(f"G코드 윤곽 − CAD 원: min {dr.min():+.4f}, max {dr.max():+.4f} mm "
      f"(이론 현 처짐 sagitta = {sag:.4f} mm)")
```

실행 결과 (약 10 s, 25층 × 2회 기준 모델 생성):
```text
슬라이싱: 25층, 마지막 층 윗면 Z = 5.00 mm (CAD 5.07 mm)
              term  mean_mm  std_mm      n
 slicing (G - CAD)    -0.07   0.000 171498
process (meas - G)    -0.03   0.005 171498
total (meas - CAD)    -0.10   0.005 171498
    feature    CAD  Gcode    meas  slicing  process  total
diameter_eq 9.9987  9.968 10.0077  -0.0308   0.0398  0.009
G코드 윤곽 − CAD 원: min -0.0241, max -0.0020 mm (이론 현 처짐 sagitta = 0.0241 mm)
```

**결과 읽는 법**
- **높이**: 슬라이싱 −0.07 mm(층 양자화) + 공정 −0.03 mm(처짐) = 총 −0.10 mm. 세 값이 같은 171,498칸에서 계산되어 정확히 더해집니다.
- **지름**: CAD 9.9987 mm는 10 mm 원을 0.02 mm 격자로 표본화한 값입니다(격자 양자화 −1.3 µm). G코드 9.968 mm는 32각형 면적 등가 지름(이론 9.9679)과 같습니다. 측정 10.0077 mm는 선폭이 한쪽 0.02 mm 넓어진 효과(+0.04)를 보여 줍니다.
- **상쇄**: 지름의 총 오차는 +0.009 mm로 작지만, 실제로는 슬라이싱 −0.031 mm와 공정 +0.040 mm가 상쇄된 결과입니다.
- **윤곽 이탈 범위**: G코드 윤곽은 CAD 원보다 최대 0.0241 mm 안쪽(면 가운데, 이론 현 처짐과 일치), 최소 약 0.002 mm 안쪽(꼭짓점 근처; 외벽 모서리가 반지름 w/2로 둥글어져 꼭짓점에 완전히 닿지 않음)입니다.

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 덧셈 분해 | 6.2절 높이 표 | slicing + process − total 의 절댓값 < 1e-9 mm (같은 칸) |
| 층 양자화 | `slicer_layer_count(5.07, 0.2)` | (25, 5.0). 실제 슬라이서 G코드 마지막 Z와 일치 여부를 별도 기록 |
| STL 다각형 효과 | 32각형 G코드 면적 등가 지름 | 이론 9.9679 mm와 0.001 mm 이내 |
| 현 처짐 | G코드 윤곽 − CAD 원 최솟값 | 이론 r(1 − cos(π/N)) 과 0.001 mm 이내 |
| 공정 오차 복원 | 합성 측정(높이 −0.03, 선폭 +0.04) | 높이 −0.030 ± 0.001 mm, 지름 +0.040 ± 0.002 mm |
| 실제 시편 (M6) | 본 실험 원기둥 시편 | 분해표가 모든 조건·시편에 대해 존재하고, 보고서 그림에 반영 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 세 오차를 서로 다른 영역에서 평균 | slicing + process ≠ total | 공통 영역 하나로 계산 (`region`) |
| CAD 원점과 G코드 원점 불일치 | 슬라이싱 오차에 큰 위치 오차 섞임 | 슬라이서에서 모델 위치(베드 중심 이동 등)를 확인해 CAD 좌표를 G코드 좌표로 옮김 |
| CAD 높이를 층 배수로 가정 | 슬라이싱 Z 오차를 공정 오차로 오인 | G코드 마지막 Z 확인, `slicer_layer_count` 와 대조 |
| 지름을 내부 틈 포함 면적으로 계산 | 등가 지름이 0.01 mm 이상 작게 나옴 | `fill_holes=True` (바깥 지름 목적) |
| 거친 STL로 시편 출력 | 슬라이싱 오차가 공정 오차만큼 큼 | STL 현 처짐 ≤ 0.005 mm |
| 총 오차만 보고 | 상쇄된 원인이 숨음 | 분해표 + 누적 막대그래프 |
| 슬라이서 설정(수평 확장, 구멍 보정)을 모름 | 설명되지 않는 일정한 XY 오프셋 | 슬라이서 프로파일 파일을 함께 보관(E3), 설정값 기록 |

## 9. 위험 요소

- **범위 확대 위험**: 복잡한 STL을 다루기 시작하면 메쉬 처리(단면, 레이 캐스팅)에 시간이 많이 듭니다. 우선순위가 낮은 요소이므로 **해석식 단순 형상으로 제한**하고, 일정 지연 시(K4) 가장 먼저 생략합니다.
- **CAD 대비 측정은 정합 방식에 민감**: CAD 좌표와 G코드 좌표의 관계는 슬라이서의 모델 배치로 결정됩니다. 이 관계가 틀리면 슬라이싱 오차에 위치 오차가 섞입니다.
- **슬라이서 내부 규칙의 불투명성**: 가변 선폭(Arachne 등), 자동 구멍 보정은 버전마다 바뀝니다. 슬라이싱 오차는 "그 슬라이서 버전·설정에서의 값"으로만 보고합니다.

## 10. 기록 양식

`results/<스캔ID>/decomposition_dims.csv`:
```csv
scan_id,feature,CAD_mm,Gcode_mm,meas_mm,slicing_mm,process_mm,total_mm,method,region_cells,note
S05_r01,cyl10_diameter_eq,10.000,,,,,,area_equivalent,,
S05_r01,cyl10_top_height,5.000,,,,,,median_in_region,,
```

슬라이싱 조건 기록:

| 시편ID | CAD 파일 / 해석식 | STL 현 처짐 [mm] | 슬라이서·버전 | 층높이 | 수평 확장 / 구멍 보정 설정 | G코드 마지막 Z | 확인자 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 11. 참고 자료

- STL 형식과 곡면 다각형화(chordal tolerance) — 주요 CAD 프로그램의 STL 내보내기 설정 문서
- Slic3r / PrusaSlicer 문서: 층 자르기 방식, "XY size compensation", "Slice closing radius"
- Ultimaker Cura 문서: "Horizontal Expansion", "Hole Horizontal Expansion"
- NIST, Additive Manufacturing Test Artifact (시편 설계 참고, BLUEPRINT E3)
- shapely 2.x 공식 문서: `segmentize`, `get_coordinates`
- SciPy 공식 문서: `scipy.ndimage.binary_fill_holes`
