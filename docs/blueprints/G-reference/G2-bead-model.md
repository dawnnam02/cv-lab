# G2. 비드(선) / 공구 형상 모델

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: G. G코드 기준 모델 (마스킹)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-11-03 ~ 2026-11-16 (W5-6) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [G1 G코드 파싱](G1-gcode-parsing.md) · [A3 가공 공정 확정](../A-goals/A3-process.md) · [A1 오차의 정의](../A-goals/A1-error-definition.md) |
| 후행 요소 | [G3 마스크·높이맵](G3-mask-heightmap.md) · [G4 평가 마스크](G4-evaluation-masks.md) · [H7 치수·형상 지표(선폭)](../H-analysis/H7-dimensional-metrics.md) · [E3 시편 설계(단일 선 트랙)](../E-specimen/E3-test-artifact.md) |
| 관련 마일스톤 | **M3** (기준 모델 완성 → 합성 데이터 테스트), K1 W5–6 소프트웨어 목표 "기준 높이맵·마스크(G2–G4)" |

---

## 1. 목적

G코드의 선분은 **두께가 없는 선**입니다. 실제 출력물(또는 가공물)과 비교하려면 각 선분에 **폭과 높이(단면 형상)** 를 입혀야 합니다. 이 요소에서는
1. FDM 비드의 **단면 모델**(사각형 + 양 끝 반원)과 그 단면적 공식을 코드로 만들고,
2. 선폭을 **명목값(슬라이서 설정)** 과 **압출량 기반 값(w_eff, G코드의 E에서 역산)** 두 가지로 구해 비교하며,
3. CNC 공정일 때를 대비해 **공구 반경 오프셋(평엔드밀)** 과 **볼엔드밀 단면**도 같은 방식으로 다룹니다.

여기서 정한 선폭 `w` 와 층높이 `h` 는 G3의 `buffer(w/2)` 와 G4의 경계 띠 폭(`w/2 + 2·δx`), H7의 선폭 비교 기준으로 그대로 쓰입니다.

## 2. 배경 지식 (초보자용)

**비드(bead)** 는 노즐에서 나온 플라스틱 한 줄입니다. 노즐이 층높이 h만큼 위에서 눌러 주기 때문에 단면이 납작한 모양이 됩니다. Slic3r 계열 슬라이서는 이 단면을 다음처럼 근사합니다.

```
      ┌──────────────┐  ← 윗면 높이 = 층 Z (노즐 높이)
     (                )  ← 양 끝 반원 (지름 h)
      └──────────────┘  ← 아랫면 = Z − h
      |<---- w ----->|
단면적 A = (w − h)·h + π·(h/2)²
```

- w = 0.42 mm, h = 0.20 mm 이면 A = 0.22 × 0.2 + π × 0.01 = **0.075416 mm²**
- 필라멘트 지름 d_f = 1.75 mm의 단면적은 π × 0.875² = **2.40528 mm²**
- 따라서 경로 1 mm마다 필요한 E는 A / 2.40528 = **0.03135 mm** 입니다. 10 mm 선이면 E = 0.3135 (G1 시험 G코드의 값).

**거꾸로 계산 (압출량 기반 선폭)**: G코드에 적힌 ΔE와 선분 길이 L을 알면
```
부피 V = ΔE · π(d_f/2)²        단면적 A = V / L        선폭 w_eff = (A − π h²/4) / h + h
```
즉 **G코드가 "실제로 의도한" 선폭**을 선분마다 구할 수 있습니다. 슬라이서는 겹침(overlap), 얇은 벽 보정, 첫 층 선폭(보통 더 넓음)처럼 명목값과 다른 선폭을 자주 씁니다. 이것을 모르고 명목값만 쓰면 기준이 틀어집니다.

**flow(압출 배율)** 가 1.05이면 단면적이 5 % 늘지만, 반원 부분(π h²/4)은 그대로이므로 선폭은 **약 4.5 %** 만 늘어납니다 (6절 실행 결과 0.4389 mm).

**필라멘트 지름의 영향**: 계산에 쓴 d_f가 실제와 0.03 mm 다르면 단면적이 약 ±3.4 % 달라지고, 선폭은 **±0.013 mm** 달라집니다. 이 값은 측정하려는 선폭 오차(A2: ±0.04 mm)의 1/3이나 되므로, **필라멘트 지름을 마이크로미터로 실측**해야 합니다.

**층높이와 윗면**: G코드 층의 Z는 노즐 끝 높이입니다. 그 층 비드의 **윗면 ≈ Z**, 아랫면 = Z − h 입니다. 첫 층의 h는 Z 자체(예: 0.2 mm)입니다.

**CNC**: 공구 중심이 경로를 따라가면 **공구 반지름만큼 두꺼운 띠**가 깎입니다. 평엔드밀은 바닥이 평평하고, 볼엔드밀은 경로에서 d만큼 떨어진 곳의 바닥이 `z = z_tip + R − √(R² − d²)` 로 올라갑니다. `G41`(왼쪽)/`G42`(오른쪽)는 기계가 경로를 반지름만큼 자동으로 옮기라는 명령입니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 설명 |
|---|---|---|---|
| 입력 | `data/processed/<시편ID>/segments.parquet` | 표 | G1 선분 표 |
| 입력 | 필라멘트 지름 실측값 | 숫자 [mm] | 마이크로미터, 1 m 간격 10곳 평균·표준편차 |
| 입력 | 슬라이서 프로파일 | `.3mf`/`.ini` | 명목 선폭(종류별, 첫 층 별도), 층높이, flow |
| 산출물 | `src/cvlab/bead_model.py` | Python 모듈 | 6.1절 코드 |
| 산출물 | `data/processed/<시편ID>/segments_w.parquet` | 표 | G1 표 + `h, A, w_eff` 열 |
| 산출물 | `results/<시편ID>/width_summary.csv` | CSV | 경로 종류별 w_eff 평균·표준편차·명목 대비 비율 |
| 산출물 | `config/default.yaml` 의 `gcode:` 절 | YAML | `line_width_mm`, `layer_height_mm`, `filament_diameter_mm`, `width_model` |

`config/default.yaml` 추가 예 (J2와 같은 키 사용):
```yaml
gcode:
  line_width_mm: 0.42
  layer_height_mm: 0.2
  filament_diameter_mm: 1.75      # 실측값으로 교체 (예: 1.742)
  width_model: nominal            # nominal | extrusion
  w_eff_min_len_mm: 0.5           # 이보다 짧은 선분은 w_eff 계산 제외
```

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 단면 모델 | 사각형 / 사각형+반원 / 타원 | **사각형+반원** | Slic3r 계열 슬라이서가 E 계산에 쓰는 모델과 같음 → w_eff 역산이 정확 |
| 선폭 모델 (G3 기준용) | 명목(`nominal`) / 압출량 기반(`extrusion`) | **둘 다 계산**, 주 결과는 `nominal`, `extrusion` 은 민감도 분석 | BLUEPRINT 부록1 #12. 두 기준의 결과 차이가 곧 "선폭 모델 불확도" |
| w_eff 계산 최소 길이 | 0.2 / 0.5 / 1.0 mm | **0.5 mm** | 짧은 선분은 E 반올림(소수 5자리)의 상대 잡음이 크고, 슬라이서의 연결·보정 선은 의도적으로 다른 폭을 써서 평균을 흐림 |
| 필라멘트 지름 | 명목 1.75 / 실측 | **실측 평균** (10곳) | 0.03 mm 차이 → 선폭 0.013 mm 차이 |
| 첫 층 선폭 | 다른 층과 같게 / 별도 | **G코드 w_eff 로 확인 후 별도 값 사용** | 대부분 슬라이서가 첫 층을 더 넓게(예: 120 %) 출력 |
| 층높이 h | 설정값 / Z 차이 | **Z 차이**(층별 중앙 Z의 차) | 가변 층높이, 첫 층 두께가 자동 반영 |
| CNC 공구 모델 | 평엔드밀 / 볼엔드밀 | 공구에 맞춤 | 공구 반지름은 **실측값**(공구 현미경 또는 시험 절삭 홈 폭) |

## 5. 수행 절차

1. **필라멘트 지름 실측 (W5 첫날, 30분)**
   - [ ] 마이크로미터(분해능 1 µm)로 1 m 간격 10곳, 각 위치에서 90° 돌려 2번 측정 → 20개 값
   - [ ] 평균, 표준편차를 10절 양식에 기록. 표준편차 > 0.02 mm 이면 그 필라멘트는 본 실험에 쓰지 않음
2. **단면 모델 코드 확인 (W5, 반나절)**
   - [ ] 6.1절 `bead_model.py` 작성, 6.2절 [1] 출력에서 A = 0.07542 mm², E/mm = 0.03135 확인
   - [ ] `bead_profile` 출력 [2]가 2절 그림(가운데 평평, 양 끝 반원)과 맞는지 확인
3. **합성 G코드로 역산 검증 (W5, 반나절)**
   - [ ] G1의 `synthetic_gcode.py` 로 flow 1.00 / 1.05 두 파일 생성 → w_eff 평균이 0.4200 / 0.4389 mm인지 확인
4. **실제 슬라이서 G코드에 적용 (W5–6, 1일)**
   - [ ] 시편 G코드에 `add_effective_width()` 적용, `width_summary.csv` 저장
   - [ ] 종류별 `ratio_to_nominal` 이 0.95~1.05 밖이면 슬라이서 설정(첫 층 선폭, 외벽 선폭, 겹침)을 확인하고 이유를 기록
   - [ ] 층 0과 나머지 층을 나눠서도 계산 (`df[df.layer == 0]`)
5. **선폭 모델 정하기 (W6, 반나절)**
   - [ ] 명목값과 w_eff 평균 차이가 0.01 mm 이하면 `nominal` 로 충분. 넘으면 `extrusion` 을 주 모델로 바꾸는 것을 지도교수와 협의
   - [ ] 결정과 근거를 `config/default.yaml` 주석과 10절 양식에 기록
6. **(CNC 공정일 때만) 공구 모델 (W6, 1일)**
   - [ ] 공구 지름 실측, 6.2절 [4] 예처럼 `cutter_comp_path` 로 G41/G42 경로를 만들어 윤곽 이탈 면적 0 확인
   - [ ] 볼엔드밀이면 `ball_endmill_depth` 로 단면 높이 프로파일 생성 → G3 높이맵에 사용

## 6. Python 구현

### 6.1 비드·공구 모델 모듈 — `src/cvlab/bead_model.py`

```python
"""
bead_model.py — G2. 비드(선) / 공구 형상 모델

FDM : 선분에 폭 w, 높이 h를 입힌다 (사각형 + 양 끝 반원 단면, Slic3r 계열 근사)
CNC : 공구 반경만큼 경로를 두껍게(오프셋) 만들어 깎이는 영역을 구한다
"""
import math

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


# ---------------- FDM 비드 단면 ----------------
def bead_area(w, h):
    """단면적 A = (w − h)·h + π·(h/2)²  [mm²]   (w ≥ h 일 때만 유효)"""
    return (w - h) * h + math.pi * (h / 2) ** 2


def width_from_area(A, h):
    """A 와 h 로부터 선폭 역산: w = (A − π h²/4)/h + h"""
    return (A - math.pi * h ** 2 / 4) / h + h


def filament_area(d_f):
    return math.pi * (d_f / 2) ** 2


def e_per_mm(w, h, d_f, flow=1.0):
    """선 1 mm를 그을 때 필요한 E [mm 필라멘트 / mm 경로]"""
    return flow * bead_area(w, h) / filament_area(d_f)


def bead_profile(d, w, h, z_top):
    """
    비드 중심선에서 가로로 d [mm] 떨어진 곳의 윗면 높이.
    가운데 평평한 폭 (w−h), 양쪽은 반지름 h/2 반원. 비드 밖은 NaN.
    """
    d = np.abs(np.asarray(d, dtype=float))
    flat = (w - h) / 2
    z = np.full(d.shape, np.nan)
    z[d <= flat] = z_top
    side = (d > flat) & (d <= w / 2)
    z[side] = z_top - h / 2 + np.sqrt((h / 2) ** 2 - (d[side] - flat) ** 2)
    return z


def layer_heights(segments):
    """층마다 층높이 h = (이 층 Z) − (아래 층 Z). 첫 층은 Z 자체."""
    ex = segments[segments.kind == "extrude"]
    z_by_layer = ex.groupby("layer").z1.median().sort_index()
    h = z_by_layer.diff()
    h.iloc[0] = z_by_layer.iloc[0]
    return pd.DataFrame({"z": z_by_layer, "h": h.round(4)})


def add_effective_width(segments, d_f, min_len=0.5):
    """
    압출 선분마다 h, 단면적 A, 압출량 기반 선폭 w_eff 를 추가.
    min_len 보다 짧은 선분은 E 반올림 잡음이 커서 w_eff = NaN 으로 둠.
    """
    df = segments[segments.kind == "extrude"].copy()
    lh = layer_heights(segments)
    df["h"] = df.layer.map(lh.h)
    df["A"] = df.de * filament_area(d_f) / df.length          # V / L
    df["w_eff"] = (df.A - math.pi * df.h ** 2 / 4) / df.h + df.h
    df.loc[df.length < min_len, "w_eff"] = np.nan
    return df


def width_summary(df, w_nominal):
    """경로 종류별 w_eff 통계와 명목값 대비 비율"""
    g = df.dropna(subset=["w_eff"]).groupby("type").agg(
        n=("w_eff", "size"),
        len_mm=("length", "sum"),
        w_mean=("w_eff", "mean"),
        w_std=("w_eff", "std"),
        w_min=("w_eff", "min"),
        w_max=("w_eff", "max"))
    g["ratio_to_nominal"] = g.w_mean / w_nominal
    return g.round(4)


# ---------------- CNC 공구 모델 ----------------
def flat_endmill_removed(path_xy, tool_d):
    """평엔드밀: 공구 중심 경로를 반경만큼 두껍게 → 깎여 나가는 영역"""
    return LineString(path_xy).buffer(tool_d / 2, quad_segs=32)


def cutter_comp_path(path_xy, tool_d, side):
    """
    G41(왼쪽)/G42(오른쪽) 공구 반경 보정 흉내:
    프로그램 경로(완성 윤곽)를 공구 반경만큼 옮긴 '공구 중심' 경로.
    shapely offset_curve: 양수 = 진행 방향 왼쪽.
    """
    r = tool_d / 2
    dist = r if side == "G41" else -r
    return LineString(path_xy).offset_curve(dist, quad_segs=32, join_style="round")


def ball_endmill_depth(d, tool_d, z_tip):
    """볼엔드밀이 지나간 자리의 바닥 높이: 경로에서 d 떨어진 곳 z = z_tip + R − sqrt(R² − d²)"""
    R = tool_d / 2
    d = np.abs(np.asarray(d, dtype=float))
    z = np.full(d.shape, np.nan)
    m = d <= R
    z[m] = z_tip + R - np.sqrt(R ** 2 - d[m] ** 2)
    return z
```

### 6.2 수치 확인 예제 — `notebooks/g2_example.py`

G1의 `gcode_parser.py`, `synthetic_gcode.py` 가 같은 폴더(또는 import 가능한 위치)에 있어야 합니다.

```python
"""g2_example.py — 비드 모델 수치 확인 + 합성 G코드에서 선폭 역산 + CNC 예시"""
import math

import numpy as np
from shapely.geometry import Polygon

from bead_model import (bead_area, width_from_area, filament_area, e_per_mm,
                        bead_profile, add_effective_width, width_summary,
                        flat_endmill_removed, cutter_comp_path, ball_endmill_depth)
from gcode_parser import parse_gcode_text
from synthetic_gcode import make_block_gcode

w, h, d_f = 0.42, 0.20, 1.75
A = bead_area(w, h)
print(f"[1] 단면적 A = {A:.5f} mm², 필라멘트 단면 = {filament_area(d_f):.5f} mm²")
print(f"    E/mm = {e_per_mm(w, h, d_f):.5f}  → 10 mm 선 E = {10 * e_per_mm(w, h, d_f):.4f} mm")
print(f"    역산 w = {width_from_area(A, h):.4f} mm")

# 필라멘트 지름 오차가 w_eff 에 주는 영향 (실제 1.72 mm인데 1.75로 계산했다면?)
for d_true in (1.72, 1.75, 1.78):
    A_true = A * filament_area(d_true) / filament_area(d_f)   # 같은 E로 실제 나간 부피
    print(f"    실제 지름 {d_true} mm → 실제 w = {width_from_area(A_true, h):.4f} mm")

# 비드 단면 프로파일 (윗면 Z = 0.2)
d = np.array([0.0, 0.10, 0.11, 0.15, 0.20, 0.21, 0.25])
print("[2] bead_profile:", np.round(bead_profile(d, w, h, 0.2), 4).tolist())

# 합성 G코드에서 선폭 역산: flow 1.00 / 1.05
for flow in (1.00, 1.05):
    seg = parse_gcode_text(make_block_gcode(flow=flow)).segments
    df = add_effective_width(seg, d_f)
    print(f"[3] flow={flow:.2f}")
    print(width_summary(df, w)[["n", "w_mean", "w_std", "ratio_to_nominal"]].to_string())

# CNC: 10x10 mm 사각 포켓 윤곽을 Ø3 평엔드밀로 안쪽(G41, 반시계 진행 시 왼쪽=안쪽) 가공
contour = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]       # 반시계 방향
center_path = cutter_comp_path(contour, 3.0, "G41")
removed = flat_endmill_removed(list(center_path.coords), 3.0)
pocket = Polygon(contour)
print(f"[4] 공구 중심 경로 범위 = {np.round(center_path.bounds, 3).tolist()}")
print(f"    깎인 띠 면적 = {removed.area:.3f} mm², "
      f"윤곽 이탈(포켓 밖으로 깎임) = {removed.difference(pocket).area:.4f} mm²")
print("[5] 볼엔드밀 Ø6, 바닥 z=-1: d=0,1,2,3 →",
      np.round(ball_endmill_depth([0, 1, 2, 3], 6.0, -1.0), 4).tolist())
```

실행: `python g2_example.py` → 기대 출력 (실제 실행 결과)
```text
[1] 단면적 A = 0.07542 mm², 필라멘트 단면 = 2.40528 mm²
    E/mm = 0.03135  → 10 mm 선 E = 0.3135 mm
    역산 w = 0.4200 mm
    실제 지름 1.72 mm → 실제 w = 0.4072 mm
    실제 지름 1.75 mm → 실제 w = 0.4200 mm
    실제 지름 1.78 mm → 실제 w = 0.4330 mm
[2] bead_profile: [0.2, 0.2, 0.2, 0.1917, 0.1436, 0.1, nan]
[3] flow=1.00
              n  w_mean  w_std  ratio_to_nominal
type                                            
FILL        114    0.42    0.0               1.0
SKIRT         4    0.42    0.0               1.0
WALL-INNER   24    0.42    0.0               1.0
WALL-OUTER   24    0.42    0.0               1.0
[3] flow=1.05
              n  w_mean  w_std  ratio_to_nominal
type                                            
FILL        114  0.4389    0.0            1.0449
SKIRT         4  0.4389    0.0            1.0449
WALL-INNER   24  0.4389    0.0            1.0449
WALL-OUTER   24  0.4388    0.0            1.0449
[4] 공구 중심 경로 범위 = [1.5, 1.5, 8.5, 8.5]
    깎인 띠 면적 = 82.066 mm², 윤곽 이탈(포켓 밖으로 깎임) = 0.0000 mm²
[5] 볼엔드밀 Ø6, 바닥 z=-1: d=0,1,2,3 → [-1.0, -0.8284, -0.2361, 2.0]
```

**출력 읽는 법**
- [1] 지름 실측이 1.72 mm인데 1.75로 계산하면, 같은 E로 실제 나온 선폭은 0.4072 mm입니다. 기준(0.42)과 0.013 mm 차이가 **측정 전부터** 생깁니다.
- [3] FILL의 n이 114인 이유: 지그재그 채움의 줄 사이 연결 선(약 0.40 mm)은 0.5 mm 미만이라 제외됐습니다.
- [3] flow 1.05에서 비율이 1.0449로, 5 %가 아닌 약 4.5 %입니다 (2절 설명).
- [4] 반시계 방향 윤곽에 G41(왼쪽 보정)을 쓰면 공구 중심이 안쪽 1.5 mm로 들어가고, 포켓 밖으로 깎인 면적이 0입니다. 깎인 띠 면적 82.066 mm² ≈ 100 − 4² − 4 × (1.5² − π·1.5²/4) = 82.068 (원을 다각형으로 근사해서 0.002 차이) (모서리에 반지름 1.5 mm 둥근 부분이 남음).
- [5] 볼엔드밀 반지름 3 mm 밖(d = 3)은 바닥이 공구 끝보다 R(3 mm)만큼 높습니다. 즉 그 위치는 공구 윤곽의 가장자리입니다.

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 단면적 공식 | `bead_area(0.42, 0.2)` | 0.0754159 ± 1e-6 mm² (pytest: G3 문서의 `test_bead_area_roundtrip`) |
| 역산 일관성 | `width_from_area(bead_area(w,h), h)` | w와 1e-9 이내 일치 |
| 합성 G코드 역산 | flow 1.00 합성 G코드 | 모든 종류 w_eff 평균 0.420 ± 0.001 mm, 표준편차 < 0.001 mm |
| flow 감도 | flow 1.05 합성 G코드 | w_eff = 0.4389 ± 0.001 mm |
| 실제 G코드 | 시편 G코드 `width_summary` | 종류별 비율이 0.95~1.05 이내, 벗어나면 이유가 기록되어 있음 |
| 필라멘트 지름 | 마이크로미터 20점 | 표준편차 ≤ 0.02 mm, 평균값이 config에 반영됨 |
| CNC 오프셋 | 정사각 포켓 예 | 공구 중심 경로 범위 [1.5, 8.5], 포켓 밖 면적 < 1e-6 mm² |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 필라멘트 지름 1.75 고정 사용 | w_eff가 모든 종류에서 같은 비율로 틀림 | 실측 평균 사용, 롤을 바꾸면 다시 측정 |
| 첫 층도 h = 0.2로 계산 | 첫 층 두께가 0.3이면 첫 층 w_eff가 크게 나옴 | h는 층별 Z 차이로 계산 (`layer_heights`) |
| 짧은 선분의 w_eff를 평균에 포함 | 표준편차가 비정상적으로 큼, 최솟값·최댓값 극단 | `min_len=0.5` 필터, 길이 가중 평균 고려 |
| w < h 인 설정에서 공식 사용 | w_eff가 음수 또는 이상값 | 공식은 w ≥ h 에서만 유효. 브리지(공중 출력)는 원형 단면(A = π w²/4)으로 따로 처리 |
| 선폭 = 노즐 지름이라고 가정 | 기준 폭이 0.02~0.05 mm 작음 | 슬라이서 설정 선폭(보통 노즐의 105~120 %) 확인 |
| 상대 E(M83)와 절대 E(M82) 혼동 | ΔE가 누적값이라 w_eff가 층마다 증가 | G1 파서의 `de` 열만 사용 |
| CNC 공구 반경 보정을 두 번 적용 | 형상이 공구 지름만큼 작음 | G코드에 G41/G42가 있으면 이미 기계가 보정함. CAM 출력이 "공구 중심 경로"인지 "윤곽 경로"인지 확인 |
| offset_curve 방향 착각 | 포켓이 바깥으로 커짐 | shapely `offset_curve` 양수 = 진행 방향 왼쪽. 6.2절 [4]의 "포켓 밖 면적 0" 검사로 확인 |

## 9. 위험 요소

- **단면 모델 자체의 한계**: 실제 비드는 인접 비드와 눌려 합쳐지고, 냉각 수축으로 모서리가 둥글어집니다. 단면 모델 오차는 수 µm~수십 µm 수준이며, 이는 "공정 오차"로 측정될지 "기준 모델 오차"로 볼지 정의 문제입니다. → 보고서에 "기준 = Slic3r 계열 사각형+반원 단면 모델" 이라고 명시합니다.
- **슬라이서 E 계산 방식 차이**: 일부 슬라이서·설정(체적 압출 `M200`, 가변 선폭 Arachne 등)은 E를 다른 식으로 만듭니다. M200이 G코드에 있으면 E 단위가 mm³이므로 `filament_area` 를 곱하지 않습니다.
- **필라멘트 지름 변동**: 롤 안에서 ±0.02~0.05 mm 변동이 흔합니다. 이것은 공정 오차의 원인 중 하나이므로, 측정 결과 해석 시 필라멘트 지름 로그를 함께 봅니다.
- **CNC 공구 마모·런아웃**: 공구 실효 지름은 회전 흔들림(런아웃)으로 명목보다 커집니다. 시험 절삭 홈 폭으로 실효 지름을 구해서 씁니다.

## 10. 기록 양식

필라멘트 지름 측정표 (`results/filament_<롤ID>.csv`):
```csv
roll_id,date,operator,position_m,angle_deg,diameter_mm
PLA-GRAY-01,2026-11-03,student_A,0,0,
PLA-GRAY-01,2026-11-03,student_A,0,90,
PLA-GRAY-01,2026-11-03,student_A,1,0,
```

선폭 모델 결정 기록:

| 날짜 | 시편ID | 종류 | 명목 w [mm] | w_eff 평균 [mm] | w_eff 표준편차 | 비율 | 첫 층 w_eff | 결정(nominal/extrusion) | 근거 | 확인자 |
|---|---|---|---|---|---|---|---|---|---|---|
| | | WALL-OUTER | | | | | | | | |
| | | WALL-INNER | | | | | | | | |
| | | FILL / SKIN | | | | | | | | |

## 11. 참고 자료

- Slic3r / PrusaSlicer 문서의 "Flow Math" (사각형+반원 단면 모델과 압출량 계산)
- RepRap Wiki "Triffid Hunter's Calibration Guide" (필라멘트 지름·압출 배율 보정)
- shapely 2.x 공식 문서: `buffer`, `offset_curve`, `LineString`
- LinuxCNC 문서: Cutter Radius Compensation (G40, G41, G42)
- Marlin Firmware 문서: M200 (체적 압출)
