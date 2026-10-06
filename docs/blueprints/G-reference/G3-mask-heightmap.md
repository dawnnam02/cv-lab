# G3. 층별 마스크 · 기준 높이맵 생성

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: G. G코드 기준 모델 (마스킹)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-11-03 ~ 2026-11-16 (W5-6) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [G1 G코드 파싱](G1-gcode-parsing.md) · [G2 비드 모델](G2-bead-model.md) · [A2 요구 정밀도(격자 간격)](../A-goals/A2-precision-spec.md) · [J2 설정·재현성](../J-software/J2-config-reproducibility.md) |
| 후행 요소 | [G4 평가 마스크](G4-evaluation-masks.md) · [G5 CAD 관계](G5-cad-relation.md) · [H1 점→격자](../H-analysis/H1-gridding.md) · [H4 정합](../H-analysis/H4-registration.md) · [H5 높이 지표](../H-analysis/H5-height-metrics.md) · [H6 윤곽 지표](../H-analysis/H6-contour-metrics.md) · [J3 합성 테스트](../J-software/J3-synthetic-tests.md) · [C2 층별 측정](../C-mechanics/C2-measurement-timing.md) |
| 관련 마일스톤 | **M3** (합성 데이터 테스트의 정답 H_ref 제공), M4 (시편 1개 전체 파이프라인) |

---

## 1. 목적

G1의 선분 표와 G2의 비드 폭을 이용해, 측정 높이맵과 **같은 격자** 위에 다음을 만듭니다.

| 이름 | 모양 | 뜻 |
|---|---|---|
| `layer_masks[k]` | (층 수, ny, nx) bool | 층 k에서 재료가 있어야 할 칸 = True |
| `H_ref` | (ny, nx) float32 | 위에서 내려다본 **있어야 할 최상단 높이** [mm]. 재료 없음 = NaN |
| `T_ref` | (ny, nx) int8 | 최상단 층에서 그 칸을 만든 **경로 종류** 코드 (G4의 `M_type` 재료) |
| `L_ref` | (ny, nx) int16 | 최상단 층 번호 (층별 분석, C2 층별 측정용) |

이 결과는 **"정답(기준)"** 입니다. 여기서 1 칸(0.02 mm)이 밀리면 모든 윤곽 지표가 0.02 mm 틀어집니다. 그래서 이 문서는 **격자 규칙**과 **경계 칸 처리**를 특히 엄격하게 정합니다.

## 2. 배경 지식 (초보자용)

**폴리곤 → 마스크**: shapely로 선분을 `buffer(w/2)` 하면 "선폭만큼 두꺼운 영역(폴리곤)"이 됩니다. 한 층의 모든 선분 영역을 `union_all` 로 합치면 그 층의 재료 영역입니다. 이 영역에 격자의 각 칸 중심이 들어가는지(`contains_xy`)를 판정하면 True/False 마스크가 됩니다.

**높이맵**: 층을 아래(Z 작은 것)부터 차례로 칠하면서 그 층 마스크가 True인 칸에 그 층 Z를 덮어씁니다. 마지막에 남는 값이 최상단 높이입니다.

**격자 규칙 (이 프로젝트 전체 공통, H1도 동일하게)**

```
배열 H[iy, ix]        행(iy) = Y 방향, 열(ix) = X 방향
칸 중심 좌표          x = x0 + ix·res,   y = y0 + iy·res    (x0, y0 는 res 의 정수배)
칸 하나가 덮는 범위    [x − res/2, x + res/2] × [y − res/2, y + res/2]
그림 그릴 때          plt.imshow(H, origin="lower", extent=grid.extent())
```
- BLUEPRINT G3 예시의 `np.arange(x_min, x_max, res)` 와 같은 규칙입니다(칸 중심 = arange 값).
- `origin="lower"` 를 빼면 그림이 **위아래로 뒤집혀** 보입니다. 배열 첫 행이 Y가 가장 작은 곳이기 때문입니다.

**경계 칸 문제**: G코드 좌표는 대개 0.01 mm 단위 숫자입니다(예: 외벽 바깥 경계 X = 10.00). 칸 중심도 0.02의 배수이므로 **경계가 칸 중심에 정확히 걸리는 일이 흔합니다**. `contains_xy` 는 경계 위의 점을 "밖"으로 판정하므로 양쪽 경계에서 한 칸씩 빠져 면적이 체계적으로 작아집니다. 10 mm 정사각형이면 −0.4 %입니다. 해결책: 판정점을 아주 조금(EPS = 1e-6 mm) +x, +y 로 옮기면 "왼쪽 경계는 포함, 오른쪽 경계는 제외" 하는 **반열림 규칙**이 되어 평균적으로 치우침이 없어집니다(6.3절 테스트 `test_square_raster_area_exact_on_aligned_edges`).

**모서리 미세 틈**: 외벽과 내벽이 정확히 선폭 간격이면, 사각 모서리에서 외벽 안쪽(뾰족한 모서리)과 내벽 바깥(둥근 모서리) 사이에 아주 작은 빈틈(약 0.01 mm²)이 생깁니다. 실제 출력에서는 눌린 플라스틱이 메우므로, 기준에서도 **형태학적 닫힘**(`buffer(+c).buffer(−c)`, c = 0.05 mm)으로 메웁니다. 이 처리는 폭 2c = 0.1 mm 미만의 틈만 메우므로 E3 시편의 가장 좁은 슬롯(0.2 mm)은 그대로 남습니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 설명 |
|---|---|---|---|
| 입력 | `segments_w.parquet` | 표 | G1 선분 표 + G2 `w_eff` |
| 입력 | `config/default.yaml` | YAML | `grid.resolution_mm: 0.02`, `gcode.line_width_mm`, `gcode.width_model`, `reference.close_mm: 0.05`, `reference.edge_model: flat` |
| 산출물 | `src/cvlab/reference_model.py` | Python 모듈 | 6.1절 코드 (J1의 `reference_model.py`; G2 함수는 `bead_model.py` 로 분리) |
| 산출물 | `data/processed/<시편ID>/ref_r0.02_nominal.npz` | NumPy 압축 | `H_ref, T_ref, L_ref, layer_masks_packed, z_layers, h_layers, layer_ids, grid(JSON), meta(JSON)` |
| 산출물 | `data/processed/<시편ID>/ref_r0.02_extrusion.npz` | 위와 같음 | 압출량 기반 선폭 버전 (민감도 분석) |
| 산출물 | `results/<시편ID>/g3_reference.png` | PNG | 기준 높이맵 + 경로 종류 지도 |
| 산출물 | `tests/test_reference_model.py` | pytest | 6.3절 |

파일 이름에 **격자 간격과 선폭 모델**을 넣어서, 다른 설정으로 만든 기준과 섞이지 않게 합니다. `meta` 에는 G코드 SHA-256, 설정 파일 사본, git 커밋 해시를 넣습니다(J2).

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 격자 간격 `res` | 0.01 / 0.02 / 0.05 mm | **0.02 mm** | A2 XY 점 간격과 동일(BLUEPRINT 부록1 #13). 측정 격자와 반드시 같게 |
| 칸 좌표 규칙 | 칸 중심 / 칸 모서리 | **칸 중심 = x0 + i·res**, x0는 res 정수배 | BLUEPRINT `np.arange` 와 일치, H1과 공유 |
| 경계 판정 | `contains_xy` / `intersects_xy` / EPS 이동 | **contains_xy + EPS(1e-6 mm)** | 반열림 규칙 → 면적 치우침 제거 |
| 래스터화 방법 | shapely `contains_xy` / OpenCV `fillPoly` | **contains_xy** (정확), fillPoly는 미리보기용 | fillPoly는 50~100배 빠르지만 경계 1칸 치우침(+0.3 % 면적) |
| 닫힘 반경 `close_mm` | 0 / 0.05 / 0.1 mm | **0.05 mm** | 모서리 미세 틈 제거, 0.1 mm 이상 틈은 유지 |
| 높이 모델 `edge` | `flat` / `rounded` | **flat** (주), rounded는 민감도 분석 | BLUEPRINT G3 방식. rounded는 경계 0.1 mm 안쪽만 최대 0.056 mm 낮춤 → G4 경계 띠(0.25 mm)가 어차피 제외 |
| 경로 종류 우선순위 | 마지막 칠한 종류가 이김 | FILL → SKIN → WALL-INNER → **WALL-OUTER** → 서포트·스커트 | 외벽이 겹치면 외벽으로 표시 → 외벽 평가 영역이 줄지 않음 |
| 계산 범위 | 전체 층 / 최상단 N층 | 기본 전체, 느리면 캐시 | 81만 칸 기준 층당 약 0.2 s |
| 재료 없음 표시 | NaN / 0 | **NaN** | 0(베드)과 "재료 없음"을 구분. 비교할 때 필요하면 `np.nan_to_num(H_ref, nan=0)` |

## 5. 수행 절차

1. **격자 규칙 합의 (W5 첫날, 1시간)**
   - [ ] 2절 격자 규칙을 H1 담당자와 함께 읽고 `docs/` 에 합의 기록 (`x0, y0, res, nx, ny` 를 JSON으로 함께 저장한다는 것까지)
2. **모듈 작성 (W5, 2일)**
   - [ ] 6.1절 `reference_model.py` 작성
   - [ ] 6.3절 테스트 4개 통과 (`4 passed`)
3. **합성 시편으로 확인 (W5, 1일)**
   - [ ] 6.2절 실행 → H_ref (12,15) = 1.20, (18,15) = 0.80, 스커트 (7,15) = 0.20, 빈 곳 NaN
   - [ ] 0층 래스터 면적 vs 폴리곤 면적 차이 |·| < 0.1 % (실행 결과 −0.003 %)
   - [ ] `close_mm=0` 과 비교해 블록 안쪽 NaN 칸이 0이 되는지 확인
   - [ ] 그림에서 위아래·좌우가 G1 경로 그림과 같은 방향인지 확인 (L자 같은 비대칭 시편이면 더 확실)
4. **실제 시편 G코드 적용 (W6, 1일)**
   - [ ] `nominal`, `extrusion` 두 버전 npz 저장
   - [ ] 두 버전의 0층 마스크 IoU 계산 → 0.99 미만이면 G2 선폭 결정을 다시 검토
   - [ ] 실행 시간 기록 (층 수, 칸 수, 초)
5. **저장·읽기 확인 (W6, 반나절)**
   - [ ] `load_reference()` 로 다시 읽어 `layer_masks`, `H_ref` NaN 위치가 완전히 같은지 (`저장/읽기 일치: True`)
6. **속도 대책 (필요할 때만)**
   - [ ] 층 수 × 칸 수가 1억을 넘으면: (a) 비교할 층만 계산, (b) 층별 결과를 `cache/<sha256>_<층>.npy` 로 저장, (c) 폴리곤 경계 상자(bounds) 안의 칸만 판정하는 방식으로 개선

## 6. Python 구현

### 6.1 기준 모델 모듈 — `src/cvlab/reference_model.py`

```python
"""
reference_model.py — G3. 층별 마스크 · 기준 높이맵 생성

격자 규칙 (H1과 반드시 같아야 함)
  - 배열 H[iy, ix]: 행 = Y, 열 = X.  iy 가 커질수록 Y 증가 (그림은 origin="lower")
  - 칸 중심 좌표: x = x0 + ix·res,  y = y0 + iy·res   (x0, y0 = 첫 칸의 '중심', res의 정수배)
    → BLUEPRINT G3의 np.arange(x_min, x_max, res) 와 같은 규칙. 칸 하나는 [x − res/2, x + res/2]
  - 경계 위 판정: 칸 중심이 폴리곤 경계에 정확히 놓이면 contains_xy는 '밖'으로 판정 →
    면적이 체계적으로 작아짐. 판정점을 EPS(1e-6 mm)만큼 +x,+y로 옮겨 [a, b) 반열림 규칙처럼 만듦
"""
import json
import math
from dataclasses import dataclass, asdict

import numpy as np
import shapely
from scipy import ndimage

# 같은 픽셀에 여러 경로 종류가 겹치면 나중 것이 이김 → 외벽이 가장 마지막
TYPE_CODES = {"NONE": 0, "FILL": 1, "SKIN": 2, "WALL-INNER": 3, "WALL-OUTER": 4,
              "SKIRT": 5, "BRIM": 6, "SUPPORT": 7, "PRIME-TOWER": 8, "OTHER": 9}
PAINT_ORDER = ["FILL", "SKIN", "OTHER", "WALL-INNER", "WALL-OUTER",
               "SUPPORT", "PRIME-TOWER", "BRIM", "SKIRT"]


@dataclass
class GridSpec:
    x0: float
    y0: float
    res: float
    nx: int
    ny: int

    @property
    def xs(self):
        return self.x0 + np.arange(self.nx) * self.res

    @property
    def ys(self):
        return self.y0 + np.arange(self.ny) * self.res

    def index(self, x, y):
        """좌표 [mm] → (행 iy, 열 ix). 격자 밖이면 IndexError"""
        ix = int(round((x - self.x0) / self.res))
        iy = int(round((y - self.y0) / self.res))
        if not (0 <= ix < self.nx and 0 <= iy < self.ny):
            raise IndexError(f"({x}, {y}) is outside the grid")
        return iy, ix

    def extent(self):
        """matplotlib imshow(extent=...) 용: 칸 가장자리 기준"""
        r = self.res
        return [self.x0 - r / 2, self.x0 + (self.nx - 0.5) * r,
                self.y0 - r / 2, self.y0 + (self.ny - 0.5) * r]

    def to_json(self):
        return json.dumps(asdict(self))


def make_grid(segments, res=0.02, margin=1.0):
    """압출 선분 범위 + 여유(margin)를 덮는 격자. 원점은 res 배수로 맞춤(측정 격자와 공유하기 쉽게)"""
    ex = segments[segments.kind == "extrude"]
    xmin = min(ex.x0.min(), ex.x1.min()) - margin
    xmax = max(ex.x0.max(), ex.x1.max()) + margin
    ymin = min(ex.y0.min(), ex.y1.min()) - margin
    ymax = max(ex.y0.max(), ex.y1.max()) + margin
    x0 = math.floor(xmin / res) * res
    y0 = math.floor(ymin / res) * res
    nx = int(math.ceil((xmax - x0) / res)) + 1
    ny = int(math.ceil((ymax - y0) / res)) + 1
    return GridSpec(round(x0, 6), round(y0, 6), res, nx, ny)


def segment_polygon(segs, w_nominal, width_mode="nominal", close_mm=0.05):
    """
    선분들을 선폭만큼 두껍게(buffer) 만들어 하나의 영역으로 합침 (shapely 2.x 벡터 연산)
    close_mm: 형태학적 닫힘(+c 팽창 후 −c 수축). 벽 모서리의 미세 틈(< 2c 폭)만 메움.
              0 이면 끔. 시편의 가장 좁은 슬롯(E3: 0.2 mm)보다 2c가 충분히 작아야 함.
    """
    if len(segs) == 0:
        return shapely.Polygon()
    coords = np.stack([segs[["x0", "y0"]].values, segs[["x1", "y1"]].values], axis=1)
    lines = shapely.linestrings(coords)                       # (N, 2점, 2좌표)
    if width_mode == "extrusion" and "w_eff" in segs:
        w = segs.w_eff.fillna(w_nominal).values               # 짧은 선분 등 NaN은 명목값
    else:
        w = np.full(len(segs), w_nominal)
    polys = shapely.buffer(lines, w / 2, quad_segs=8)        # 양 끝 반원(round cap)
    poly = shapely.union_all(polys)
    if close_mm > 0:
        poly = poly.buffer(close_mm, quad_segs=8).buffer(-close_mm, quad_segs=8)
    return poly


EPS = 1e-6   # [mm] 경계 판정용 미세 이동 (res 0.02 mm의 5만분의 1)


def rasterize(poly, grid):
    """폴리곤 → 불리언 마스크 (칸 중심이 폴리곤 안이면 True)"""
    X, Y = np.meshgrid(grid.xs + EPS, grid.ys + EPS)
    shapely.prepare(poly)                                     # 반복 판정 가속
    return shapely.contains_xy(poly, X, Y)


def build_reference(segments, grid, w_nominal, width_mode="nominal", edge="flat",
                    close_mm=0.05):
    """
    반환: dict
      H_ref   (ny,nx) float32 : 기준 높이 [mm], 재료 없는 곳 NaN
      T_ref   (ny,nx) int8    : 최상단 층의 경로 종류 코드 (TYPE_CODES)
      L_ref   (ny,nx) int16   : 최상단 층 번호, 없음 = -1
      layer_masks (n_layer,ny,nx) bool, z_layers, h_layers
    edge="rounded" 이면 층 윤곽 근처를 비드 반원 단면(G2)으로 낮춤 (민감도 분석용)
    """
    ex = segments[segments.kind == "extrude"]
    z_by_layer = ex.groupby("layer").z1.median().sort_values()   # Z 순서 = 쌓이는 순서
    layers = list(z_by_layer.index)
    zs = z_by_layer.values
    hs = np.diff(np.concatenate([[0.0], zs]))
    H = np.full((grid.ny, grid.nx), np.nan, dtype=np.float32)
    T = np.zeros((grid.ny, grid.nx), dtype=np.int8)
    L = np.full((grid.ny, grid.nx), -1, dtype=np.int16)
    masks = np.zeros((len(layers), grid.ny, grid.nx), dtype=bool)
    for k, (lay, z, h) in enumerate(zip(layers, zs, hs)):
        segs = ex[ex.layer == lay]
        m = rasterize(segment_polygon(segs, w_nominal, width_mode, close_mm), grid)
        masks[k] = m
        if edge == "rounded":
            # 마스크 안쪽 칸에서 윤곽까지 거리 δ [mm] (칸 중심 기준이라 res/2 보정)
            delta = ndimage.distance_transform_edt(m) * grid.res - grid.res / 2
            zt = np.full(m.shape, z)
            near = m & (delta < h / 2)
            zt[near] = z - h / 2 + np.sqrt(np.clip((h / 2) ** 2 - (h / 2 - delta[near]) ** 2, 0, None))
            H[m] = zt[m]
        else:
            H[m] = z                                          # 위층이 아래층을 덮어씀
        L[m] = k
        # 경로 종류 지도: 이 층에서 덮인 칸은 일단 OTHER로, 종류별로 다시 칠함
        T[m] = TYPE_CODES["OTHER"]
        tt = segs.type.where(segs.type.isin(list(TYPE_CODES)), "OTHER")  # 모르는 종류·None → OTHER
        for t in PAINT_ORDER:
            st = segs[tt == t]
            if len(st):
                mt = rasterize(segment_polygon(st, w_nominal, width_mode, close_mm), grid)
                T[mt] = TYPE_CODES[t]
    return {"H_ref": H, "T_ref": T, "L_ref": L, "layer_masks": masks,
            "z_layers": zs, "h_layers": hs, "layer_ids": np.array(layers)}


def save_reference(path, ref, grid, meta=None):
    """npz 하나에 모두 저장. 층 마스크는 packbits로 1/8 크기"""
    np.savez_compressed(
        path, H_ref=ref["H_ref"], T_ref=ref["T_ref"], L_ref=ref["L_ref"],
        layer_masks_packed=np.packbits(ref["layer_masks"], axis=-1),
        z_layers=ref["z_layers"], h_layers=ref["h_layers"], layer_ids=ref["layer_ids"],
        grid=grid.to_json(), meta=json.dumps(meta or {}, ensure_ascii=False))


def load_reference(path):
    d = np.load(path)
    grid = GridSpec(**json.loads(str(d["grid"])))
    ref = {k: d[k] for k in ("H_ref", "T_ref", "L_ref", "z_layers", "h_layers", "layer_ids")}
    ref["layer_masks"] = np.unpackbits(d["layer_masks_packed"], axis=-1,
                                       count=grid.nx).astype(bool)
    return ref, grid, json.loads(str(d["meta"]))
```

### 6.2 합성 시편으로 확인 — `notebooks/g3_example.py`

G1의 `gcode_parser.py`, `synthetic_gcode.py` 가 필요합니다.

```python
"""g3_example.py — 합성 G코드 → 층 마스크 · 기준 높이맵, 정확도·시간 확인"""
import time

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shapely

from gcode_parser import parse_gcode_text
from reference_model import (make_grid, segment_polygon, rasterize, build_reference,
                             save_reference, load_reference, TYPE_CODES)
from synthetic_gcode import make_block_gcode

W = 0.42
seg = parse_gcode_text(make_block_gcode()).segments
grid = make_grid(seg, res=0.02, margin=1.0)
print("grid:", grid.to_json(), "→ 칸 수", grid.nx * grid.ny)

t0 = time.perf_counter()
ref = build_reference(seg, grid, W)
print(f"build_reference: {time.perf_counter() - t0:.2f} s, 층 {len(ref['z_layers'])}개")

H = ref["H_ref"]
def at(x, y):                                  # 좌표 → 배열 칸 (행=y, 열=x)
    return H[grid.index(x, y)]
print(f"H_ref (12,15)={at(12, 15):.2f}  (18,15)={at(18, 15):.2f}  "
      f"(7,15)={at(7, 15):.2f}  (6.5,6.5)={at(6.5, 6.5)}")

# 블록 안쪽(10.3~19.7 mm)에 NaN 구멍이 있는지: close_mm=0 과 비교
iy0, ix0 = grid.index(10.3, 10.3); iy1, ix1 = grid.index(19.7, 19.7)
ref_open = build_reference(seg, grid, W, close_mm=0.0)
for name, r in (("close_mm=0.05", ref), ("close_mm=0   ", ref_open)):
    holes = np.isnan(r["H_ref"][iy0:iy1 + 1, ix0:ix1 + 1]).sum()
    print(f"{name}: 블록 안쪽 NaN 칸 {holes}")

# 래스터 면적 vs 폴리곤 정확 면적 (0층)
ex = seg[seg.kind == "extrude"]
poly0 = segment_polygon(ex[ex.layer == 0], W)
raster_area = ref["layer_masks"][0].sum() * grid.res ** 2
print(f"0층 면적: 폴리곤 {poly0.area:.3f} mm², 래스터 {raster_area:.3f} mm², "
      f"차이 {100 * (raster_area - poly0.area) / poly0.area:+.3f} %")

# 대안: OpenCV fillPoly 래스터화 (빠름) 와 일치도 비교
def rasterize_cv2(poly, grid, shift=4):
    m = np.zeros((grid.ny, grid.nx), np.uint8)
    s = 2 ** shift                                         # 1/16 픽셀 정밀도
    def pix(ring):
        xy = np.asarray(ring.coords)
        u = (xy[:, 0] - grid.x0) / grid.res * s           # 칸 중심 = 정수 픽셀 좌표
        v = (xy[:, 1] - grid.y0) / grid.res * s
        return np.round(np.stack([u, v], 1)).astype(np.int32)
    for p in getattr(poly, "geoms", [poly]):              # 폴리곤마다 따로 칠한 뒤 OR
        tmp = np.zeros_like(m)                            # (구멍 안의 다른 폴리곤이 지워지지 않게)
        cv2.fillPoly(tmp, [pix(p.exterior)], 1, lineType=cv2.LINE_8, shift=shift)
        for hole in p.interiors:                          # 구멍은 0으로 다시 칠함
            cv2.fillPoly(tmp, [pix(hole)], 0, lineType=cv2.LINE_8, shift=shift)
        m |= tmp
    return m.astype(bool)

t0 = time.perf_counter(); m_sh = rasterize(poly0, grid); t_sh = time.perf_counter() - t0
t0 = time.perf_counter(); m_cv = rasterize_cv2(poly0, grid); t_cv = time.perf_counter() - t0
iou = (m_sh & m_cv).sum() / (m_sh | m_cv).sum()
print(f"contains_xy {t_sh * 1000:.0f} ms, cv2.fillPoly {t_cv * 1000:.1f} ms, IoU={iou:.5f}, "
      f"불일치 칸 {(m_sh ^ m_cv).sum()}, cv2 면적 차이 "
      f"{100 * (m_cv.sum() * grid.res ** 2 - poly0.area) / poly0.area:+.2f} %")

# 저장 → 다시 읽기 확인
save_reference("block_test_ref.npz", ref, grid, meta={"gcode": "block_test.gcode", "w": W})
ref2, grid2, meta = load_reference("block_test_ref.npz")
same = np.array_equal(ref2["layer_masks"], ref["layer_masks"]) and \
       np.array_equal(np.isnan(ref2["H_ref"]), np.isnan(H))
print("저장/읽기 일치:", same, meta)

# 그림: 기준 높이맵 + 경로 종류 지도
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
im = ax[0].imshow(H, origin="lower", extent=grid.extent(), cmap="viridis")
fig.colorbar(im, ax=ax[0], label="H_ref [mm]")
ax[0].set_title("reference heightmap")
im2 = ax[1].imshow(np.ma.masked_equal(ref["T_ref"], 0), origin="lower",
                   extent=grid.extent(), cmap="tab10", vmin=0, vmax=9)
ax[1].set_title("top-layer type (1=FILL 3=WALL-IN 4=WALL-OUT 5=SKIRT)")
for a in ax:
    a.set_xlabel("X [mm]"); a.set_ylabel("Y [mm]"); a.set_aspect("equal")
fig.savefig("g3_reference.png", dpi=120, bbox_inches="tight")
print("saved g3_reference.png")

# rounded 모드: 윤곽 근처 높이만 바뀌는지
ref_r = build_reference(seg, grid, W, edge="rounded")
d = ref_r["H_ref"] - H
print(f"rounded - flat: 바뀐 칸 {np.count_nonzero(d[~np.isnan(d)])}, 최솟값 {np.nanmin(d):.3f} mm")
```

실행 결과 (시간 값은 PC마다 다름):
```text
grid: {"x0": 6.0, "y0": 6.0, "res": 0.02, "nx": 901, "ny": 901} → 칸 수 811801
build_reference: 1.62 s, 층 6개
H_ref (12,15)=1.20  (18,15)=0.80  (7,15)=0.20  (6.5,6.5)=nan
close_mm=0.05: 블록 안쪽 NaN 칸 0
close_mm=0   : 블록 안쪽 NaN 칸 109
0층 면적: 폴리곤 126.805 mm², 래스터 126.801 mm², 차이 -0.003 %
contains_xy 98 ms, cv2.fillPoly 1.3 ms, IoU=0.98692, 불일치 칸 4180, cv2 면적 차이 +0.34 %
저장/읽기 일치: True {'gcode': 'block_test.gcode', 'w': 0.42}
saved g3_reference.png
rounded - flat: 바뀐 칸 44208, 최솟값 -0.056 mm
```

**결과 해석과 시간 메모**
- 6층·81만 칸 기준 `build_reference` 약 1.5 s. 같은 조건에서 **50층은 약 10.5 s** 측정됨 → **층당 약 0.2 s** (층 마스크 1회 + 경로 종류별 래스터화 3~4회).
- 실제 시편(예: 20×20 mm, 칸 100만 개, 100층)은 약 20~30 s 예상입니다. 반복 실행할 때는 6.1절 `save_reference` 결과를 다시 읽어 씁니다.
- `cv2.fillPoly` 는 약 1 ms로 매우 빠르지만 경계 칸을 포함하는 규칙 때문에 면적이 +0.34 % 크고 IoU 0.987입니다. **지표 계산용 기준으로는 쓰지 않고**, 수만 층짜리 큰 출력물의 빠른 미리보기에만 씁니다.
- `rounded` 모드는 4만여 칸(층 윤곽에서 h/2 = 0.1 mm 이내)을 최대 0.056 mm 낮춥니다. G4 경계 띠(0.25 mm) 안쪽이라 높이 지표에는 영향이 거의 없지만, H6·H7 경계 지표의 민감도 분석에 씁니다.

### 6.3 단위 테스트 — `tests/test_reference_model.py`

```python
"""tests/test_reference_model.py — G2·G3 단위 테스트"""
import math

import numpy as np
import pytest
import shapely

from bead_model import bead_area, width_from_area, add_effective_width
from gcode_parser import parse_gcode_text
from reference_model import GridSpec, rasterize, build_reference, make_grid
from synthetic_gcode import make_block_gcode


def test_bead_area_roundtrip():
    A = bead_area(0.42, 0.2)
    assert A == pytest.approx(0.0754159, abs=1e-6)
    assert width_from_area(A, 0.2) == pytest.approx(0.42)


def test_effective_width_from_synthetic_gcode():
    seg = parse_gcode_text(make_block_gcode(flow=1.0)).segments
    w = add_effective_width(seg, 1.75).w_eff.dropna()
    assert w.mean() == pytest.approx(0.42, abs=1e-3)


def test_square_raster_area_exact_on_aligned_edges():
    # 경계가 칸 중심(0.02 배수)에 정확히 놓이는 최악의 경우에도 면적이 정확해야 함
    grid = GridSpec(0.0, 0.0, 0.02, 600, 600)
    m = rasterize(shapely.box(2.0, 2.0, 10.0, 10.0), grid)
    assert m.sum() * 0.02 ** 2 == pytest.approx(64.0, rel=1e-9)


def test_block_heights():
    seg = parse_gcode_text(make_block_gcode()).segments
    grid = make_grid(seg, res=0.02)
    H = build_reference(seg, grid, 0.42)["H_ref"]
    assert H[grid.index(12, 15)] == pytest.approx(1.2)
    assert H[grid.index(18, 15)] == pytest.approx(0.8)
    assert math.isnan(H[grid.index(6.5, 6.5)])
```
실행: `pytest -q tests/test_reference_model.py` → `....                                                                     [100%]
4 passed in 1.88s`

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 단위 테스트 | `pytest -q tests/test_reference_model.py` | 4개 모두 통과 |
| 경계 정렬 면적 | 칸 중심에 경계가 걸린 8×8 mm 정사각형 | 면적 64.000 mm² (상대오차 < 1e-9) |
| 층 면적 | 래스터 면적 vs shapely 폴리곤 면적 | 층마다 |차이| < 0.1 % |
| 높이 값 | 합성 시편 지정 위치 | 정답과 1e-6 mm 이내 (float32 저장 오차 수준) |
| 내부 빈틈 | 합성 시편 블록 안쪽 NaN 칸 수 | 0 |
| 방향 | 비대칭(L자) 시편의 H_ref 그림 vs G1 경로 그림 | 상하·좌우 일치 |
| 재현성 | 같은 G코드·설정으로 두 번 생성 | `np.array_equal` 로 완전히 같음 |
| 저장 | save → load | 모든 배열 동일 |
| 선폭 모델 차이 | nominal vs extrusion 0층 마스크 IoU | ≥ 0.99 (미만이면 G2 재검토) |
| 속도 | 실제 시편 | 기록됨(층당 시간), 전체 5분 이내 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| `imshow` 에 `origin="lower"` 빠뜨림 | 그림이 위아래 뒤집힘 → 정합(H4)에서 180° 틀린 답 | 항상 `origin="lower", extent=grid.extent()` |
| `H[x, y]` 로 인덱싱 | 엉뚱한 칸 값 | 순서는 `H[iy, ix]`, 좌표 변환은 `grid.index(x, y)` 사용 |
| 측정 격자와 다른 원점·간격 | 0.01 mm 같은 반 칸 어긋남, IoU 저하 | 같은 `GridSpec` JSON을 H1에서 읽어 사용 |
| 층 번호 순서로 칠함 | 층 주석 순서와 Z 순서가 다르면 아래층이 위층을 덮음 | Z 순서로 정렬(`sort_values`) 후 칠함 |
| 스커트·서포트를 높이맵에서 빼버림 | 측정에는 스커트가 있는데 기준에는 없어 "과충진"으로 잡힘 | 높이맵에는 모두 넣고, 평가 제외는 G4 `M_type` 에서 |
| 경계 판정 규칙 미고려 | 면적이 −0.4 % 치우침 | EPS 이동 (6.1절) |
| 닫힘 반경을 크게(0.2 mm 이상) | 좁은 슬롯·틈이 기준에서 사라짐 | `close_mm` ≤ (최소 틈 폭)/4 |
| 마스크를 float로 저장 | 파일 크기 32배 | bool → `np.packbits` |
| NaN과 0 혼동 | 바닥(0)이 "재료 없음"으로, 또는 반대로 처리 | 기준 H_ref는 NaN 유지, 비교 시에만 명시적으로 변환 |

## 9. 위험 요소

- **기준 모델 = 근사**: 사각형+반원 단면, 평평한 윗면 가정은 실제 비드의 굴곡(줄무늬, 수 µm~수십 µm)을 무시합니다. 윗면 높이 오차의 일부는 "모델 오차"입니다. → `flat` 과 `rounded`, `nominal` 과 `extrusion` 4가지 조합으로 지표를 계산해서 차이를 기준 모델 불확도로 I1에 넣습니다.
- **처짐·오버행**: 아래층이 없는 곳(브리지, 오버행)은 기준에서 "있어야 함"이지만 실제로는 처집니다. 위에서 보는 2.5D 측정으로는 윗면만 보이므로, 이런 형상은 E3 시편에서 피하거나 별도 분석합니다.
- **대용량·시간**: 큰 출력물(100 mm × 100 mm, 0.02 mm 격자 = 2500만 칸)은 메모리(float32 높이맵 100 MB, 층 마스크는 packbits 후 층당 3 MB)와 시간이 문제입니다. 측정 FOV 범위만 계산합니다.
- **격자 규칙 불일치**: H1 구현자가 다른 규칙(칸 모서리 원점)을 쓰면 반 칸(0.01 mm) 체계 오차가 모든 결과에 섞입니다. J3 합성 테스트에서 "변형 없음" 입력의 IoU = 1.000을 확인해 잡아냅니다.

## 10. 기록 양식

기준 생성 기록 (`data/processed/<시편ID>/ref_log.csv`, 생성할 때마다 한 줄):
```csv
date,specimen_id,gcode_sha256,res_mm,width_model,line_width_mm,close_mm,edge_model,n_layers,nx,ny,runtime_s,layer0_area_err_pct,inner_nan_cells,git_commit,operator
2026-11-10,S03,,0.02,nominal,0.42,0.05,flat,,,,,,,,
```

검토 체크리스트:

| 항목 | 결과 | 확인자 |
|---|---|---|
| 그림 방향이 G1 경로 그림과 일치 | ☐ | |
| 층 면적 차이 < 0.1 % (모든 층) | ☐ | |
| nominal vs extrusion IoU ≥ 0.99 | ☐ | |
| 격자 JSON이 H1과 같은 규칙 | ☐ | |

## 11. 참고 자료

- shapely 2.x 공식 문서: `buffer`, `union_all`, `prepare`, `contains_xy`, `linestrings` (Vectorized operations 장)
- NumPy 공식 문서: `meshgrid`, `packbits` / `unpackbits`, `savez_compressed`
- SciPy 공식 문서: `scipy.ndimage.distance_transform_edt`
- OpenCV 공식 문서: `cv2.fillPoly` (shift 인자에 의한 서브픽셀 좌표)
- matplotlib 공식 문서: `imshow` 의 `origin`, `extent` 설명 ("origin and extent in imshow")
