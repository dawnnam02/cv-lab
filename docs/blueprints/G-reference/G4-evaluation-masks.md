# G4. 비교 영역(마스킹) 정의

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: G. G코드 기준 모델 (마스킹)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-11-03 ~ 2026-11-16 (W5-6) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [G3 마스크·높이맵](G3-mask-heightmap.md) · [G1 G코드 파싱(경로 종류)](G1-gcode-parsing.md) · [E2 가림·엣지 효과](../E-specimen/E2-occlusion-edges.md) · [B2 기하 배치(카메라 각도 θ)](../B-optics/B2-geometry.md) · [F1 라인 추출(신뢰도)](../F-acquisition/F1-line-extraction.md) |
| 후행 요소 | [H1 점→격자](../H-analysis/H1-gridding.md) · [H5 높이 지표](../H-analysis/H5-height-metrics.md) · [H6 윤곽 지표](../H-analysis/H6-contour-metrics.md) · [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) · [J3 합성 테스트](../J-software/J3-synthetic-tests.md) · [J4 시각화](../J-software/J4-visualization-report.md) |
| 관련 마일스톤 | **M4** (시편 1개 전체 파이프라인 완주: 평가 마스크와 커버리지 보고 포함) |

---

## 1. 목적

**"어디를 비교하고, 어디를 비교하지 않을지"** 를 칸 단위로 정하는 마스크들을 만듭니다. 이 과제에서 말하는 **"마스킹"의 핵심**입니다.

같은 측정 데이터라도 평가 영역을 어떻게 잡느냐에 따라 RMS가 몇 배 달라집니다(6.2절 결과: 경계 띠 포함 시 최대 오차 0.444 mm, 제외 시 노이즈 수준). 그래서 마스크 정의를 **코드와 숫자로 고정**하고, 보고서에는 **평가 영역이 기준 면적의 몇 %인지**를 항상 함께 적습니다.

## 2. 배경 지식 (초보자용)

**마스크** 는 True/False 2D 배열입니다. 두 마스크의 "그리고(AND)"는 `A & B`, "또는(OR)"는 `A | B`, "아님(NOT)"은 `~A` 로 계산합니다. 수식의 ∧, ∨, ¬ 과 같습니다.

| 마스크 | 정의 (BLUEPRINT G4) | 이 문서의 구현 |
|---|---|---|
| `M_ref` | G코드 기준 마스크 | `~isnan(H_ref)` (위에서 본 기준 영역) 또는 `layer_masks[k]` |
| `M_meas` | 측정 높이 > (해당 층 Z − h/2) | `H_meas > z_level − h/2`, NaN은 False. 기본 z_level = 첫 층 Z |
| `M_valid` | 측정이 유효한 곳 | `~isnan(H_meas)` ∧ (신뢰도 ≥ 기준) ∧ (선택: 가림 예측 아님) |
| `M_type` | 경로 종류 필터 | `T_ref` 가 SKIRT·BRIM·SUPPORT·PRIME-TOWER가 아닌 곳 (또는 지정 종류만) |
| `M_edge` | 경계에서 일정 폭 띠 | 높이가 h/2 이상 바뀌는 칸(윤곽+내부 단차)에서 거리 ≤ 0.25 mm |
| **`M_eval`** | 높이 지표용 | **`M_ref & M_valid & M_type & ~M_edge`** |

- **윤곽 지표(H6)** 는 경계가 핵심이므로 `M_edge` 를 빼지 않고 `M_ref` 와 `M_meas` 를 직접 비교합니다. 단 **`M_valid` 는 적용**합니다(측정 안 된 칸을 "재료 없음"으로 착각하지 않도록. 6.2절 그림의 주황색 띠).

**경계 띠 폭 정하기**: E2의 규칙 "선폭의 절반 + 2·δx" → 0.42/2 + 2 × 0.02 = **0.25 mm** (J2 `masks.edge_band_mm: 0.25`).
- 선폭의 절반: 비드 양 끝 반원 때문에 경계 근처 윗면이 둥급니다(G3 `rounded` 모드 참고).
- 2·δx: 측정 격자 1~2칸에 위·아래 높이가 섞여 생기는 스파이크.

**거리 변환(distance transform)**: 모든 칸에 대해 "가장 가까운 경계 칸까지의 거리"를 한 번에 계산하는 함수(`scipy.ndimage.distance_transform_edt`)입니다. 거리 ≤ 0.25 mm 인 칸이 경계 띠입니다. BLUEPRINT가 언급한 **침식(binary erosion)** 방식은 "기준 영역을 원판으로 깎아낸 차이"로 윤곽 안쪽 띠만 얻습니다. 내부 단차(예: 계단 피라미드)까지 잡으려면 거리 변환 방식이 필요합니다.

**가림(occlusion) 예측**: 레이저는 수직, 카메라는 수직에서 θ 기울어 있다고 하면, 칸 p에서 카메라 쪽으로 s만큼 간 곳의 높이가 `z_p + s/tanθ` 보다 높으면 p는 카메라에서 안 보입니다. 높이 h 단차 뒤 그림자 폭은 `h·tanθ` (E2). θ = 30°, h = 0.4 mm → 0.231 mm. 예측 가림과 실제 누락을 비교하면 **"예상된 누락"** 과 **"예상 밖 누락"(표면 반사·반투명 등 다른 원인)** 을 구분할 수 있습니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 설명 |
|---|---|---|---|
| 입력 | `ref_r0.02_nominal.npz` | NumPy | G3의 `H_ref, T_ref, L_ref, layer_masks` + 격자 JSON |
| 입력 | `data/processed/<스캔ID>/heightmap.npy` + 격자 JSON | NumPy | H1·H2·H3·H4 처리 후 {G} 좌표의 측정 높이맵 `H_meas` (같은 격자) |
| 입력 | `data/processed/<스캔ID>/confidence.npy` (선택) | NumPy | F1 신뢰도(최대 밝기 등)를 격자화한 것 |
| 입력 | `config/default.yaml` → `masks:` | YAML | `edge_band_mm: 0.25`, `step_mm`, `exclude_types`, `conf_min`, `camera_theta_deg`, `camera_side` |
| 산출물 | `src/cvlab/masks.py` | Python 모듈 | 6.1절 코드 |
| 산출물 | `data/processed/<스캔ID>/masks.npz` | NumPy (packbits) | `M_ref, M_meas, M_valid, M_type, M_edge, M_eval` + `shape`, 격자 JSON |
| 산출물 | `results/<스캔ID>/coverage.csv` | CSV | 기준 면적, 무효, 경계 띠, 평가 영역 (칸 수, mm², %) |
| 산출물 | `results/<스캔ID>/g4_masks.png` | PNG | 측정 높이맵, 마스크 오버레이(J4 색 규칙), M_eval |

`config/default.yaml` 의 `masks:` 절 확장 예:
```yaml
masks:
  edge_band_mm: 0.25          # = w/2 + 2·res  (E2, J2)
  step_mm: 0.1                # 높이 경계 판정 = h/2
  exclude_types: [SKIRT, BRIM, SUPPORT, PRIME-TOWER]
  conf_min: null              # F1 신뢰도 기준 (정해지면 숫자)
  camera_theta_deg: 30        # B2 배치
  camera_side: "-x"           # {G} 좌표에서 카메라가 있는 쪽
  exclude_predicted_occlusion: false
```

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 경계 띠 폭 | 0.1 / 0.25 / 0.5 mm | **0.25 mm** | E2 규칙(w/2 + 2δx), J2 값. 단차 h에서 그림자 폭 h·tanθ보다 넓어야 함(0.4 mm 단차 → 0.231 mm) |
| 경계 정의 | 윤곽만(침식) / 윤곽+내부 단차(거리 변환) | **거리 변환, 단차 기준 h/2** | 계단·원기둥 위 단차의 엣지 스파이크도 제외 |
| 제외 경로 종류 | 없음 / 스커트·브림·서포트 | **SKIRT, BRIM, SUPPORT, PRIME-TOWER** | BLUEPRINT 부록1 #14. 시편이 아닌 부속 구조 |
| 종류별 분석 | 전체만 / 외벽·채움 분리 | **둘 다** | H5 "영역별 계산" 권장. `include=['WALL-OUTER']` |
| `M_meas` 높이 기준 | z_level − h/2 (h/2 = 0.1 mm) | 첫 층 윤곽: z_level = 첫 층 Z | BLUEPRINT 정의. H6에서 ±20 % 민감도 분석 |
| 가림 예측 영역 처리 | 무시 / 보고만 / `M_valid` 에서 제외 | **보고만** (기본), 필요 시 제외 | 실제로 측정된 칸을 버리지 않기 위해. 예상 밖 누락 비율은 반드시 보고 |
| 커버리지 경고 기준 | – | 평가 영역 < 기준의 **50 %** → "대표성 낮음" 표시, 무효 > **10 %** → 원인 조사 | 측정 불가 영역이 크면 결과가 일부 영역만 대표 |
| 저장 형식 | bool `.npy` / packbits `.npz` | **packbits npz** | 크기 1/8, 마스크 6개를 한 파일에 |

## 5. 수행 절차

1. **모듈 작성 (W5, 1일)**
   - [ ] 6.1절 `masks.py` 작성, 6.3절 테스트 3개 통과
2. **합성 측정 데이터로 확인 (W5–6, 1일)** — 실제 측정은 W9 이후에 나오므로 이 단계는 합성 데이터로 합니다
   - [ ] 6.2절 실행: 과압출(선폭 0.46) + 높이 +0.03 mm + 노이즈 5 µm + 결측 2 % + 카메라 가림(θ = 30°)
   - [ ] `M_eval` 안 평균 오차가 +30.0 µm, 표준편차 5.0 µm로 **정답을 그대로 복원**하는지 확인
   - [ ] 경계 띠를 포함하면 최대 |e| 가 0.4 mm 이상으로 커지는 것을 확인 (경계 띠가 왜 필요한지)
3. **커버리지 표 자동화 (W6, 반나절)**
   - [ ] `coverage.csv` 를 스캔마다 저장, 평가 영역 % 가 50 % 미만이면 경고 출력
4. **가림 예측 검증 (W6, 반나절)**
   - [ ] B2에서 정한 θ와 카메라 방향으로 `predict_occlusion` 실행 → 합성 데이터에서 "예측 가림 칸 중 실제 무효" ≥ 85 % 확인 (실행 결과 89.7 %)
   - [ ] 실제 측정이 생기면(W9 이후) 같은 수치를 계산해 10절 양식에 기록. "예상 밖 누락"이 2 %를 넘으면 E1(표면) 문제를 의심
5. **시각화 (W6, 반나절)**
   - [ ] J4 색 규칙: 기준만 = 파랑, 측정만 = 빨강, 겹침 = 회색, 무효 = 주황
6. **실제 데이터 적용 (W13–14, M4 시점)**
   - [ ] 첫 실측 시편으로 커버리지 표·그림 생성, M4 보고에 포함

## 6. Python 구현

### 6.1 마스크 모듈 — `src/cvlab/masks.py`

```python
"""
masks.py — G4. 비교 영역(마스킹) 정의

M_ref   : 기준 마스크 (G3 H_ref 가 NaN 이 아닌 곳, 또는 특정 층 마스크)
M_meas  : 측정 마스크 (측정 높이 > 기준 높이 수준 − h/2)
M_valid : 측정 유효 (NaN·저신뢰 제외, 선택: 가림 예측 영역 제외)
M_type  : 경로 종류 필터 (스커트·브림·서포트 제외)
M_edge  : 높이 경계(윤곽 + 내부 단차) 주변 띠
M_eval  : 높이 지표용 = M_ref ∧ M_valid ∧ M_type ∧ ¬M_edge
부호 규칙: 오차 = 측정값 − 기준값 (+ = 재료 과다)
"""
import math

import numpy as np
import pandas as pd
from scipy import ndimage

from reference_model import TYPE_CODES

EXCLUDE_DEFAULT = ("SKIRT", "BRIM", "SUPPORT", "PRIME-TOWER")


def mask_ref(H_ref):
    return ~np.isnan(H_ref)


def mask_meas(H_meas, z_level, h):
    """측정 높이가 (z_level − h/2) 보다 높은 곳. NaN 은 False"""
    with np.errstate(invalid="ignore"):
        return np.nan_to_num(H_meas, nan=-np.inf) > (z_level - h / 2)


def mask_valid(H_meas, conf=None, conf_min=None, occluded=None):
    m = ~np.isnan(H_meas)
    if conf is not None and conf_min is not None:
        m &= np.nan_to_num(conf, nan=0) >= conf_min        # F1 신뢰도(최대 밝기 등)
    if occluded is not None:
        m &= ~occluded                                      # 가림 예측 영역 제외(선택)
    return m


def mask_type(T_ref, exclude=EXCLUDE_DEFAULT, include=None):
    """include 를 주면 그 종류만(예: ['WALL-OUTER']), 아니면 exclude 를 뺀 나머지"""
    if include is not None:
        return np.isin(T_ref, [TYPE_CODES[t] for t in include])
    return ~np.isin(T_ref, [TYPE_CODES[t] for t in exclude])


def edge_band(H_ref, res, band_mm, step_mm):
    """
    높이가 step_mm 이상 바뀌는 경계(시편 윤곽 + 내부 단차)에서 band_mm 이내인 칸.
    1) 3x3 이웃의 (최대 − 최소) > step_mm 인 칸 = 경계 칸 (단차 양쪽 1칸씩)
    2) 경계 칸까지의 거리(distance transform) ≤ band_mm 인 칸 = 띠
    """
    Hf = np.nan_to_num(H_ref, nan=0.0)                       # 재료 없음 = 베드 높이 0
    rng = ndimage.maximum_filter(Hf, size=3) - ndimage.minimum_filter(Hf, size=3)
    edge = rng > step_mm
    dist = ndimage.distance_transform_edt(~edge) * res      # 가장 가까운 경계 칸까지 [mm]
    return dist <= band_mm


def edge_band_erosion(M_ref, res, band_mm):
    """(비교용) 윤곽 안쪽 띠만: M_ref 를 원판으로 깎아낸 차이. 내부 단차는 못 잡음"""
    r = int(round(band_mm / res))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = xx ** 2 + yy ** 2 <= r ** 2
    return M_ref & ~ndimage.binary_erosion(M_ref, structure=disk, border_value=0)


def predict_occlusion(H_ref, res, theta_deg, cam_side="+x"):
    """
    카메라 그림자 예측 (레이저는 수직, 카메라는 수직에서 theta 기울어 cam_side 쪽에 있다고 가정).
    칸 p 에서 카메라 쪽으로 s 만큼 간 곳의 높이가 z_p + s/tanθ 보다 높으면 p 는 안 보임.
    E2: 깊이 h 인 단차 뒤 그림자 폭 ≈ h·tanθ
    """
    Hf = np.nan_to_num(H_ref, nan=0.0)
    if cam_side == "-x":
        return predict_occlusion(H_ref[:, ::-1], res, theta_deg)[:, ::-1]
    if cam_side in ("+y", "-y"):
        H2 = H_ref.T if cam_side == "+y" else H_ref[::-1].T
        occ = predict_occlusion(H2, res, theta_deg).T
        return occ if cam_side == "+y" else occ[::-1]
    t = math.tan(math.radians(theta_deg))
    kmax = int(math.ceil((Hf.max() - Hf.min()) * t / res))
    occ = np.zeros(Hf.shape, bool)
    for k in range(1, kmax + 1):
        # Hf[:, k:] = 카메라 쪽으로 k칸 떨어진 높이
        occ[:, :-k] |= Hf[:, k:] > Hf[:, :-k] + k * res / t
    return occ


def build_eval_masks(H_ref, T_ref, H_meas, res, h, band_mm=0.25, step_mm=None,
                     conf=None, conf_min=None, occluded=None,
                     exclude=EXCLUDE_DEFAULT, include=None, z_level=None):
    """모든 마스크와 커버리지 표를 한 번에 만든다"""
    step_mm = h / 2 if step_mm is None else step_mm
    z_level = h if z_level is None else z_level                 # 기본: 첫 층 윤곽
    M = {}
    M["M_ref"] = mask_ref(H_ref)
    M["M_meas"] = mask_meas(H_meas, z_level, h)
    M["M_valid"] = mask_valid(H_meas, conf, conf_min, occluded)
    M["M_type"] = mask_type(T_ref, exclude, include)
    M["M_edge"] = edge_band(H_ref, res, band_mm, step_mm)
    M["M_eval"] = M["M_ref"] & M["M_valid"] & M["M_type"] & ~M["M_edge"]
    a = res * res
    ref = M["M_ref"] & M["M_type"]                              # 평가 대상 경로 종류의 기준 면적
    n_ref = ref.sum()
    rows = [
        ("기준 면적 (M_ref ∧ M_type)", n_ref),
        ("  측정 무효 (¬M_valid)", (ref & ~M["M_valid"]).sum()),
        ("  경계 띠 (M_edge, 유효 중)", (ref & M["M_valid"] & M["M_edge"]).sum()),
        ("평가 영역 M_eval", M["M_eval"].sum()),
    ]
    cov = pd.DataFrame(rows, columns=["항목", "칸 수"])
    cov["면적_mm2"] = (cov["칸 수"] * a).round(3)
    cov["기준 대비_%"] = (100 * cov["칸 수"] / max(n_ref, 1)).round(2)
    return M, cov


def save_masks(path, M, grid_json, meta_json="{}"):
    """마스크는 bool → packbits 로 1/8 크기 저장"""
    ny, nx = M["M_ref"].shape
    np.savez_compressed(path, shape=np.array([ny, nx]), grid=grid_json, meta=meta_json,
                        **{k: np.packbits(v, axis=-1) for k, v in M.items()})
```

### 6.2 합성 측정 데이터로 확인 — `notebooks/g4_example.py`

G1의 `gcode_parser.py`, `synthetic_gcode.py`, G3의 `reference_model.py` 가 필요합니다.

```python
"""g4_example.py — 합성 '측정' 높이맵으로 평가 마스크 만들기 + 커버리지 표 + 그림"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gcode_parser import parse_gcode_text
from reference_model import make_grid, build_reference, TYPE_CODES
from masks import (build_eval_masks, predict_occlusion, edge_band_erosion, save_masks)
from synthetic_gcode import make_block_gcode

W, H_LAYER, RES = 0.42, 0.2, 0.02
rng = np.random.default_rng(42)
seg = parse_gcode_text(make_block_gcode()).segments
grid = make_grid(seg, res=RES)
ref = build_reference(seg, grid, W)
H_ref, T_ref = ref["H_ref"], ref["T_ref"]

# ---- 합성 측정값: 선폭 0.46 (과압출) + 높이 +0.03, 노이즈 5 µm, 결측 2 %, 카메라 가림 ----
H_meas = build_reference(seg, grid, 0.46)["H_ref"].astype(float)
H_meas = np.nan_to_num(H_meas, nan=0.0) + 0.03 * ~np.isnan(H_meas)   # 베드 = 0
H_meas += rng.normal(0, 0.005, H_meas.shape)
occ_true = predict_occlusion(H_meas, RES, theta_deg=30, cam_side="-x")
H_meas[occ_true] = np.nan                                  # 카메라에서 안 보이는 곳
H_meas[rng.random(H_meas.shape) < 0.02] = np.nan            # 무작위 결측 2 %

occ_pred = predict_occlusion(H_ref, RES, theta_deg=30, cam_side="-x")
M, cov = build_eval_masks(H_ref, T_ref, H_meas, RES, H_LAYER, band_mm=0.25)
print(cov.to_string(index=False))

# 가림 예측 검증
invalid = ~M["M_valid"]
print(f"가림 예측 면적 {occ_pred.sum() * RES**2:.3f} mm², 실제(합성) 가림 {occ_true.sum() * RES**2:.3f} mm²")
print(f"예측 가림 칸 중 실제 무효 {100 * (occ_pred & invalid).sum() / occ_pred.sum():.1f} %, "
      f"M_ref 안 '예상 밖 누락' {100 * (M['M_ref'] & invalid & ~occ_pred).sum() / M['M_ref'].sum():.2f} %")

# 경계 띠: 거리변환 방식 vs 침식 방식 (윤곽 안쪽만)
e1 = M["M_edge"] & M["M_ref"]
e2 = edge_band_erosion(M["M_ref"], RES, 0.25)
print(f"경계 띠(안쪽) 칸 수: 거리변환 {e1.sum()}, 침식 {e2.sum()} "
      f"(거리변환은 내부 단차 띠도 포함)")

# 높이 오차 (H5 미리보기): M_eval 안에서만
e = (H_meas - H_ref)[M["M_eval"]]
print(f"M_eval 안 높이 오차: mean {e.mean() * 1000:+.1f} µm, std {e.std(ddof=1) * 1000:.1f} µm, "
      f"n = {e.size}")
e_all = (H_meas - H_ref)[M["M_ref"] & M["M_valid"]]
print(f"(비교) 경계 띠 포함 시: mean {np.nanmean(e_all) * 1000:+.1f} µm, "
      f"max|e| {np.nanmax(np.abs(e_all)):.3f} mm")

save_masks("block_test_masks.npz", M, grid.to_json())

fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
ax[0].imshow(H_meas, origin="lower", extent=grid.extent(), cmap="viridis")
ax[0].set_title("synthetic H_meas (NaN = white)")
ov = np.ones(M["M_ref"].shape + (3,))
ov[M["M_ref"] & ~M["M_meas"]] = (0.2, 0.4, 1.0)            # 기준만 = 파랑
ov[~M["M_ref"] & M["M_meas"]] = (1.0, 0.2, 0.2)            # 측정만 = 빨강
ov[M["M_ref"] & M["M_meas"]] = (0.6, 0.6, 0.6)             # 겹침 = 회색
ov[~M["M_valid"]] = (1.0, 0.8, 0.2)                         # 측정 무효 = 주황 (윤곽 비교에서 제외)
ax[1].imshow(ov, origin="lower", extent=grid.extent())
ax[1].set_title("ref only=blue, meas only=red, both=grey, invalid=orange")
ax[2].imshow(M["M_eval"], origin="lower", extent=grid.extent(), cmap="gray")
ax[2].set_title("M_eval")
for a in ax:
    a.set_xlim(8.5, 21.5); a.set_ylim(8.5, 21.5); a.set_xlabel("X [mm]"); a.set_ylabel("Y [mm]")
fig.savefig("g4_masks.png", dpi=120, bbox_inches="tight")
print("saved g4_masks.png")
```

실행 결과:
```text
                    항목    칸 수  면적_mm2  기준 대비_%
기준 면적 (M_ref ∧ M_type) 249891  99.956   100.00
      측정 무효 (¬M_valid)  10329   4.132     4.13
   경계 띠 (M_edge, 유효 중)  31403  12.561    12.57
          평가 영역 M_eval 208159  83.264    83.30
가림 예측 면적 10.000 mm², 실제(합성) 가림 10.780 mm²
예측 가림 칸 중 실제 무효 89.7 %, M_ref 안 '예상 밖 누락' 2.12 %
경계 띠(안쪽) 칸 수: 거리변환 104657, 침식 90403 (거리변환은 내부 단차 띠도 포함)
M_eval 안 높이 오차: mean +30.0 µm, std 5.0 µm, n = 208159
(비교) 경계 띠 포함 시: mean +30.6 µm, max|e| 0.444 mm
saved g4_masks.png
```

**결과 읽는 법**
- 기준 면적 99.956 mm²(10×10 mm 블록에서 외벽 모서리 반원 때문에 0.04 mm² 작음). 스커트는 `M_type` 으로 빠져서 들어 있지 않습니다.
- 평가 영역은 기준의 **83.3 %** 입니다. 경계 띠가 12.6 %, 무효가 4.1 %(무작위 결측 2 % + 단차 뒤 카메라 그림자)입니다.
- 카메라 그림자(0.4 mm 단차 뒤 0.231 mm 폭)는 경계 띠(0.25 mm) 안에 있어서 `M_eval` 에는 영향이 없습니다. 이것이 띠 폭을 h·tanθ 보다 넓게 잡는 이유입니다.
- `M_eval` 안의 오차는 정답(+0.030 mm, σ 0.005 mm)과 같습니다. 경계 띠까지 포함하면 최대 |e| 가 0.444 mm로, 과압출로 넓어진 경계가 "높이 오차"로 잘못 섞입니다(그 부분은 H6 윤곽 지표로 따로 평가).
- 그림 `g4_masks.png` 가운데: 측정만(빨강)이 블록 둘레에 얇게 보이고(선폭 0.46 → 한쪽 0.02 mm 넓음), 단차 오른쪽의 주황 띠는 가림 때문에 측정되지 않은 칸입니다. `M_valid` 를 적용하지 않으면 이 띠가 "미충진"으로 잘못 계산됩니다.

### 6.3 단위 테스트 — `tests/test_masks.py`

```python
"""tests/test_masks.py — G4 단위 테스트"""
import math

import numpy as np
import pytest

from masks import edge_band, predict_occlusion, mask_meas

RES = 0.01


def step_map():
    # X < 5 mm: 높이 1.0, X ≥ 5 mm: 0 (베드) → 단차 1 mm
    xs = np.arange(1000) * RES
    H = np.where(xs < 5.0, 1.0, np.nan)
    return np.tile(H, (50, 1))


def test_edge_band_width():
    band = edge_band(step_map(), RES, band_mm=0.25, step_mm=0.1)
    width = band[25].sum() * RES
    # 경계 칸 2개(양쪽 1칸) + 양쪽 0.25 mm → 약 0.52 mm
    assert width == pytest.approx(0.52, abs=0.021)


def test_occlusion_shadow_length():
    occ = predict_occlusion(step_map(), RES, theta_deg=30, cam_side="-x")
    # 카메라가 -x 쪽 → 높은 쪽(X<5) 오른편 베드에 그림자, 길이 = 1.0·tan30° = 0.577 mm
    assert occ[25].sum() * RES == pytest.approx(math.tan(math.radians(30)), abs=0.011)


def test_mask_meas_nan_is_false():
    H = np.array([[np.nan, 0.05, 0.15]])
    assert mask_meas(H, 0.2, 0.2).tolist() == [[False, False, True]]
```
실행: `pytest -q tests/test_masks.py` → `...                                                                      [100%]
3 passed in 0.62s`

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 단위 테스트 | `pytest -q tests/test_masks.py` | 3개 통과 |
| 경계 띠 폭 | 1 mm 단차 합성 맵 | 띠 폭 0.52 ± 0.02 mm (양쪽 0.25 + 경계 칸) |
| 가림 그림자 | 1 mm 단차, θ = 30° | 0.577 ± 0.011 mm (= tan 30°) |
| 정답 복원 | 6.2절 합성 데이터 | `M_eval` 평균 +30.0 ± 0.5 µm, 표준편차 5.0 ± 0.5 µm |
| 가림 예측 | 6.2절 | 예측 가림 칸 중 실제 무효 ≥ 85 % |
| 커버리지 보고 | 모든 스캔 | `coverage.csv` 존재, 평가 영역 %가 보고서 표에 기재 |
| 마스크 저장 | `masks.npz` 로드 후 `np.unpackbits(..., count=nx)` | 원래 마스크와 동일 |
| 정의 일치 | 코드 리뷰 | `M_eval = M_ref & M_valid & M_type & ~M_edge` 가 BLUEPRINT와 문자 그대로 일치 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| NaN을 보간으로 채운 뒤 비교 | 측정 안 된 곳의 "오차"가 생김 | 보간 금지(E2, H1). `M_valid` 로 제외 |
| `M_valid` 없이 윤곽 비교 | 가림 띠가 "미충진"으로 잡힘 (6.2절 주황 띠) | H6에서도 `M_valid` 적용 |
| 경계 띠를 윤곽에만 적용 | 계단 단차의 스파이크가 높이 오차에 섞임 | 거리 변환 + 높이 단차 기준(`step_mm = h/2`) |
| 경계 띠를 너무 넓게(1 mm 이상) | 작은 형상(Ø2 mm 원기둥, 얇은 벽)이 통째로 사라짐 | 형상별 평가 영역 % 확인, 0 %인 형상은 보고서에 "평가 불가" 명시 |
| 평가 영역 % 미보고 | 일부 영역만 측정된 결과가 전체처럼 보임 | `coverage.csv` 자동 생성 |
| 마스크 연산에 `and`/`or` 사용 | `ValueError: truth value of an array is ambiguous` | 배열에는 `&`, `|`, `~` 사용 |
| `~` 를 int 배열에 사용 | 0 → −1 같은 엉뚱한 값 | 마스크는 항상 `dtype=bool` |
| 카메라 방향(`camera_side`) 반대로 | 그림자 예측이 반대쪽에 그려짐 | 실제 스캔의 누락 위치와 한 번 대조해서 고정 |
| 측정과 기준 격자 불일치 | 마스크 연산에서 shape 오류, 또는 반 칸 어긋남 | 같은 격자 JSON 사용(G3 2절) |

## 9. 위험 요소

- **평가 영역의 선택 편향**: 측정이 잘 되는 평평한 윗면만 남고, 오차가 큰 경계·모서리가 빠지면 결과가 실제보다 좋아 보입니다. → 높이 지표(M_eval)와 윤곽 지표(경계 포함)를 **항상 같이 보고**합니다(A1).
- **경계 띠 폭에 대한 결과 민감도**: 띠 폭 0.15 / 0.25 / 0.35 mm로 바꿔 H5 지표가 얼마나 변하는지 확인하고, 변화가 크면(예: RMS 20 % 이상) 보고서에 명시합니다.
- **경로 종류 지도의 정확도**: 슬라이서 주석이 틀리거나 없으면 `M_type` 이 틀립니다. G1에서 `types` 목록을 확인합니다.
- **가림 예측 모델 단순화**: 카메라를 무한히 먼 곳에 있다고(평행 광선) 가정합니다. 실제 카메라는 가까워서 FOV 가장자리에서 각도가 수 도 달라집니다. 예측은 참고용으로만 쓰고 기본은 "보고만" 합니다.

## 10. 기록 양식

`results/<스캔ID>/coverage.csv` (자동 생성, 6.1절 `cov` 표):
```csv
항목,칸 수,면적_mm2,기준 대비_%
기준 면적 (M_ref ∧ M_type),,,100.00
  측정 무효 (¬M_valid),,,
  경계 띠 (M_edge, 유효 중),,,
평가 영역 M_eval,,,
```

스캔별 마스크 요약 (`results/summary_masks.csv`, 스캔마다 한 줄):
```csv
scan_id,specimen_id,edge_band_mm,step_mm,exclude_types,eval_pct,invalid_pct,predicted_occl_mm2,occl_hit_pct,unexpected_missing_pct,warning,operator,date
S03_r01,S03,0.25,0.1,"SKIRT;BRIM;SUPPORT;PRIME-TOWER",,,,,,,,
```

## 11. 참고 자료

- SciPy 공식 문서: `scipy.ndimage.distance_transform_edt`, `binary_erosion`, `maximum_filter`, `minimum_filter`
- NumPy 공식 문서: Boolean array indexing, `packbits`
- 레이저 삼각측량 가림(occlusion) 일반 설명: 광삼각법 변위센서 제조사 기술 자료의 "shadowing / occlusion" 항목
- BLUEPRINT E2 (가림·엣지 효과), H6 (윤곽 지표) 절
