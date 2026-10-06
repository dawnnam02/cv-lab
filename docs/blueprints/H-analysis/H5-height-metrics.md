# H5. 높이 오차 지표

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: H. 처리·분석

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-29 ~ 2027-01-11 (W13-14) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [H4 정합](H4-registration.md), [G3 마스크·기준 높이맵](../G-reference/G3-mask-heightmap.md), [G4 비교 영역(마스킹)](../G-reference/G4-evaluation-masks.md), [H3 바닥 평면 기준화](H3-bed-leveling.md), [E2 가림·엣지 효과](../E-specimen/E2-occlusion-edges.md), [A1 오차의 정의](../A-goals/A1-error-definition.md) |
| 후행 요소 | [H8 통계 분석](H8-statistics.md), [I1 측정 불확도](../I-reliability/I1-uncertainty.md), [I2 MSA](../I-reliability/I2-msa.md), [J4 시각화·리포트](../J-software/J4-visualization-report.md) |
| 관련 마일스톤 | M4: 시편 1개 전체 파이프라인 완주 (W13-14) |

---

## 1. 목적

{G} 좌표의 같은 격자 위에서 칸마다 **높이 편차 `e = H_meas − H_ref`** 를 계산하고, 평가 마스크 `M_eval` 안에서 **치우침 · 흩어짐 · 최악값 · 공차 만족률**을 하나의 표로 요약합니다.

- 부호 규칙 (A1): **+ = 재료 과다(측정이 더 높음), − = 재료 부족**.
- 전체 하나로만 계산하지 않고 **영역별**(E3 형상별, G4 경로 종류별, 층별)로 나눠 계산합니다. 원인 분석에 필요합니다.
- 결과는 시편 하나당 CSV 한 장(`_H5_height_metrics.csv`)으로 저장되어 H8 통계의 입력이 됩니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 지표 하나로는 부족한 이유
+0.1 mm 와 −0.1 mm 가 반씩 있으면 평균은 0 이지만 RMS 는 0.1 mm 입니다 (`test_평균이_상쇄되는_경우`). 그래서 항상 세 종류를 같이 봅니다.

| 묻는 질문 | 지표 | 수식 |
|---|---|---|
| 전체적으로 높은가, 낮은가? (치우침) | 평균 `mean` | `Σe / n` |
| 얼마나 들쭉날쭉한가? (흩어짐) | 표준편차 `std` (n−1) | `√(Σ(e−ē)²/(n−1))` |
| 종합 크기 | **RMS** | `√(Σe²/n)`. `RMS² = 평균² + 표준편차²(n 으로 나눈 것)` |
| 평균적인 크기 | MAE | `Σ|e| / n` |
| 대부분에서 최악 | **P95(\|e\|)** | \|e\| 를 크기순으로 놓았을 때 95 % 지점 |
| 정말 최악 | max \|e\| | 이상치 하나로 결정됨 → 참고용 |
| 쓸 만한가? | 공차 만족률 | \|e\| ≤ 공차(예: 0.1 mm) 인 칸의 비율 % |
| 어느 쪽으로 치우친 최악인가? | P5(e), P95(e) | 부호 있는 하위·상위 5 % |

### 2.2 평가 마스크 `M_eval` (G4)
```
M_eval = M_ref ∧ M_valid ∧ M_type ∧ ¬M_edge
```
- `M_ref`: 재료가 있어야 할 곳 (G3)
- `M_valid`: 측정값이 있는 곳 (NaN 아님, H2 제거 후)
- `M_type`: 스커트·브림·서포트 제외 (G4)
- `M_edge`: **경계에서 0.25 mm 이내의 띠** (J2 설정 `edge_band_mm: 0.25`). 경계에서는 엣지 효과(E2)로 높이가 뭉개지므로 높이 지표에서 뺍니다. 경계 자체는 H6 에서 따로 평가합니다.
- 이 문서의 코드에서는 `M_area = M_ref ∧ M_type ∧ ¬M_edge`(기하학적 평가 영역)를 먼저 만들고, 측정 유효성(`M_valid`)은 함수 안에서 적용합니다. 그래야 **커버리지 = 평가해야 할 칸 중 실제로 잰 칸의 비율**을 계산할 수 있습니다.

### 2.3 단차 경계도 "경계"다
계단 피라미드처럼 윗면끼리 만나는 단차에서도 엣지 효과가 생깁니다. 그래서 `M_ref` 의 바깥 경계뿐 아니라 **기준 높이가 바뀌는 모든 경계**에 띠를 둡니다 (`step_edge_band`).

### 2.4 칸 수가 많다고 정밀한 것이 아니다
한 영역에 칸이 10만 개 있어도, 이웃 칸끼리 상관되어 있어 "독립된 측정 10만 번"이 아닙니다. 그래서 H5 는 지표를 **계산만** 하고, 신뢰구간·검정은 H8 에서 **시편 단위**로 합니다. `std/√n` 같은 값을 H5 표에 넣지 않습니다.

### 2.5 공차는 어디서 오나
`tolerance_mm: 0.1` (J2) 은 출발값입니다. A2 요구사양에서 정한 공차로 바꾸고, 공차가 측정 불확도 U(I1) 보다 충분히 커야(≥ 4U) 공차 만족률이 의미가 있습니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 내용 |
|---|---|---|---|
| 입력 | `<scan_id>_heightmap_G.npy` + `_grid_G.json` | float32 | H4 후 G3 격자의 측정 높이맵 |
| 입력 | `<gcode>_heightmap_ref_G.npy` | float32 | G3 기준 높이맵 (재료 없는 곳 NaN) |
| 입력 | `M_type`, 영역 라벨 (E3 형상 ID, 경로 종류, 층) | bool / int npy | G4 산출물 |
| 입력 | `config/default.yaml` | YAML | `masks.edge_band_mm: 0.25`, `metrics.tolerance_mm: 0.1` |
| 산출 | `<scan_id>_H5_height_metrics.csv` | CSV | 영역별 1행: n, area_mm2, coverage_pct, mean_um, std_um, rms_um, mae_um, p05_um, p95_um, p95_abs_um, max_abs_um, within_tol_pct, flag |
| 산출 | `<scan_id>_error_map_G.npy` | float32 | `e = H_meas − H_ref` (평가 영역 밖 NaN) |
| 산출 | `<scan_id>_tol_classes.npy` | int8/float | −1 부족 / 0 공차 안 / +1 과다 (그림용) |
| 산출 | `<scan_id>_H5_edge_sensitivity.csv` | CSV | 경계 띠 폭 0, 0.05, 0.1, 0.25, 0.5 mm 별 n, RMS, max |
| 산출 | 그림 (J4) | PNG | 편차 히트맵 `RdBu_r`, ±0.2 mm 고정, 0 = 흰색 / 히스토그램 + 공차선 |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 편차 부호 | 기준 − 측정 / **측정 − 기준** | **측정 − 기준** | A1 부호 규칙 (+ 재료 과다) |
| 경계 띠 폭 | 0.1 / **0.25** / 0.5 mm | **0.25 mm** | J2 설정값. 청사진 E2 "선폭의 절반 + 2·δx" ≈ 0.21 + 0.03 mm. 6장 데모에서 0.1 mm 이상이면 RMS 가 안정 |
| 단차 경계 | 바깥 경계만 / **모든 높이 경계** | **모든 높이 경계** | 2.3 절 |
| 대표 지표 (논문 본문) | **평균 + RMS + P95(\|e\|)** + 공차 만족률 | 이 4개 | A1 "치우침 + 흩어짐 + 최악" |
| 최댓값 | 본문 / 부록 | **부록·참고** | 이상치 한 칸에 좌우됨 |
| std 자유도 | n / **n−1** | **n−1** (표), 검산은 n | 관례. RMS 관계식은 n 기준 |
| 영역 최소 칸 수 | 100 / **500** / 1000 | **500칸 (0.2 mm²)** 미만이면 `CHECK` | 작은 영역은 몇 칸의 엣지 효과에 좌우 |
| 최소 커버리지 | 70 / **80** / 90 % | **80 %** 미만이면 `CHECK` | G4 "평가 영역 비율 보고" |
| 보고 단위 | mm / **µm** | **µm** (소수 1~2자리) | 오차 크기가 수~수십 µm |
| 영역 나누기 | 전체만 / **전체 + 형상별 + 경로 종류별 (+ 층별)** | 모두 | 청사진 H5 |

---

## 5. 수행 절차

1. **입력 정렬 확인 (0.5일)**
   - [ ] `H_meas` 와 `H_ref` 의 격자 JSON(원점·간격·크기)이 같은지 자동 검사
   - [ ] 기준 높이 값 집합(층 Z 들)을 출력해 G2/G3 설정(층 높이 0.2 mm)과 맞는지 확인
2. **마스크 구성 (1일)**
   - [ ] G4 의 `M_ref`, `M_type` 불러오기
   - [ ] `step_edge_band(H_ref, 0.25, res)` 로 `M_edge` 생성 → `M_area = M_ref & M_type & ~M_edge`
   - [ ] 마스크를 높이맵 위에 겹쳐 그려 확인 (J4)
3. **지표 계산 (0.5일)**
   - [ ] `metrics_by_region()` 으로 전체 + 형상별 + 경로 종류별 표 생성
   - [ ] `flag == CHECK` 인 영역은 원인(작은 면적/가림)을 메모
4. **경계 띠 민감도 (0.5일)**
   - [ ] 0, 0.05, 0.1, 0.25, 0.5 mm 로 RMS 변화 표 작성 → 0.25 mm 에서 RMS 가 안정 구간(0.1~0.5 mm 사이 변화 < 2 µm 또는 < 10 %)인지 확인
5. **합성 데이터 검증 (0.5일)**
   - [ ] 6장 데모: 영역별 평균이 넣은 치우침(+10, −20, +30, −15 µm)을 ±1 µm 안에서 복원하는지 확인
   - [ ] `pytest -q test_h5.py` 통과
6. **실측 시편 1개 완주 (M4, 1일)**
   - [ ] H1 → H2 → H3 → H4 → H5 를 스크립트(`scripts/run_analysis.py`) 한 번으로 실행
   - [ ] CSV 와 히트맵·히스토그램 저장, 결과 요약 1쪽 작성
7. **반복 스캔 비교 (0.5일)**
   - [ ] 같은 시편 3회 스캔의 영역별 평균·RMS 차이 기록 → I2 반복성에 전달

---

## 6. Python 구현

### 6.1 모듈 `h5_height_metrics.py`

```python
"""H5. 높이 오차 지표 모듈. 최종적으로 src/cvlab/metrics.py 에 합칩니다.
부호 규칙: e = H_meas − H_ref  (+ 재료 과다, − 재료 부족). 입력 단위 mm, 보고 단위 um."""
import numpy as np
import pandas as pd
from scipy.ndimage import distance_transform_edt


def edge_band(M_ref, width_mm, res):
    """기준 마스크 경계에서 width_mm 이내인 칸 (안쪽 + 바깥쪽 모두). G4 의 M_edge."""
    if width_mm <= 0:
        return np.zeros_like(M_ref, bool)
    d_in = distance_transform_edt(M_ref) * res       # 안쪽 칸 → 가장 가까운 바깥 칸까지 거리
    d_out = distance_transform_edt(~M_ref) * res     # 바깥 칸 → 가장 가까운 안쪽 칸까지 거리
    return (M_ref & (d_in <= width_mm)) | (~M_ref & (d_out <= width_mm))


def step_edge_band(H_ref, width_mm, res, min_step=0.05):
    """기준 높이맵 안의 '단차' 경계 띠 (윗면끼리의 경계도 엣지 효과가 생기므로 제외 대상)"""
    band = np.zeros(H_ref.shape, bool)
    levels = np.unique(np.round(H_ref[np.isfinite(H_ref)], 4))
    for z in levels:                                  # 높이 단계마다 그 영역의 경계 띠를 합침
        band |= edge_band(np.isclose(H_ref, z, atol=min_step / 2), width_mm, res)
    return band


def height_metrics(e, tol=0.1, res=None):
    """e: 평가할 편차 값들(1차원, mm). 반환: 지표 dict (um 단위)"""
    e = e[np.isfinite(e)]
    if e.size == 0:
        return {"n": 0}
    a = np.abs(e)
    out = {"n": int(e.size),
           "mean_um": 1000 * e.mean(),                         # 치우침(bias)
           "std_um": 1000 * e.std(ddof=1),                     # 흩어짐
           "rms_um": 1000 * np.sqrt(np.mean(e ** 2)),          # 종합 크기
           "mae_um": 1000 * a.mean(),
           "p05_um": 1000 * np.percentile(e, 5),              # 부호 있는 하위 5 % (재료 부족 쪽)
           "p95_um": 1000 * np.percentile(e, 95),             # 부호 있는 상위 5 % (재료 과다 쪽)
           "p95_abs_um": 1000 * np.percentile(a, 95),
           "max_abs_um": 1000 * a.max(),
           "within_tol_pct": 100 * float((a <= tol).mean())}
    if res is not None:
        out["area_mm2"] = e.size * res ** 2
    return out


def metrics_by_region(H_meas, H_ref, M_area, regions, res, tol=0.1, min_cells=500):
    """M_area: 기하학적 평가 영역 = M_ref ∧ M_type ∧ ¬M_edge (측정 유효성은 아직 미적용)
    regions: {이름: bool 마스크}. 영역마다 (영역 ∧ M_area ∧ 측정값 있음) 에서 지표 계산 → 표(DataFrame).
    coverage_pct = 평가해야 할 칸 중 실제 측정값이 있던 칸의 비율 (가림·결측 정도)."""
    E = H_meas - H_ref
    rows = []
    for name, R in {"ALL": np.ones_like(M_area), **regions}.items():
        m = R & M_area                                             # 평가해야 할 칸
        possible = int(m.sum())
        row = {"region": name, **height_metrics(E[m], tol, res)}   # NaN 은 height_metrics 안에서 빠짐
        row["coverage_pct"] = 100 * row["n"] / possible if possible else 0.0
        row["flag"] = "OK" if row["n"] >= min_cells and row["coverage_pct"] >= 80 else "CHECK"
        rows.append(row)
    return pd.DataFrame(rows).round(3)


def tolerance_classes(H_meas, H_ref, M_eval, tol):
    """그림용 3단계 지도: −1 = 공차보다 낮음(부족), 0 = 공차 안, +1 = 공차보다 높음(과다), NaN = 평가 안 함"""
    E = H_meas - H_ref
    C = np.full(E.shape, np.nan)
    m = M_eval & np.isfinite(E)
    C[m] = np.where(E[m] > tol, 1, np.where(E[m] < -tol, -1, 0))
    return C
```

### 6.2 데모 `demo_h5.py` (계단 피라미드, 영역별 정답 치우침)

12 × 12 mm 계단 피라미드(층 높이 1.0 → 1.2 → 1.6 → 2.6 mm, 단차 0.2 / 0.4 / 1.0 mm)에 영역별로 다른 치우침을 넣고, 경계를 40 µm 폭으로 뭉개고, 노이즈 5 µm, 각 단차 +X 쪽에 0.4 mm 폭 그림자(결측)를 넣었습니다.

```python
"""H5 데모: 계단 피라미드(E3)에 영역별로 다른 높이 오차를 넣고, 영역별 지표가 정답을 찾는지 확인."""
import numpy as np
from scipy.ndimage import gaussian_filter
from h5_height_metrics import step_edge_band, metrics_by_region, height_metrics

rng = np.random.default_rng(5)
res = 0.02
n = 600                                                    # 12 × 12 mm
yy, xx = (np.mgrid[0:n, 0:n] + 0.5) * res
ctr = 6.0
def square(half):                                          # 중심 (6,6) 정사각형 마스크
    return (abs(xx - ctr) < half) & (abs(yy - ctr) < half)

# 기준 높이맵 (G3 결과라고 가정): 1층 1.0 → 단차 0.2 / 0.4 / 1.0 mm
steps = {"S1_base": (5.0, 1.0), "S2": (3.5, 1.2), "S3": (2.0, 1.6), "S4_top": (1.0, 2.6)}
H_ref = np.full((n, n), np.nan)
regions = {}
for name, (half, z) in steps.items():
    H_ref[square(half)] = z
for name, (half, z) in steps.items():
    regions[name] = np.isclose(H_ref, z)
M_ref = np.isfinite(H_ref)

# 측정 높이맵 = 기준 + 영역별 치우침(정답) + 엣지 뭉개짐 + 노이즈 + 그림자 결측
bias = {"S1_base": +0.010, "S2": -0.020, "S3": +0.030, "S4_top": -0.015}
H_true = np.where(M_ref, H_ref, 0.0)
for name, b in bias.items():
    H_true[regions[name]] += b
H_meas = gaussian_filter(H_true, sigma=0.04 / res)         # 엣지에서 40 um 폭으로 뭉개짐
H_meas += rng.normal(0, 0.005, H_meas.shape)
for name, (half, z) in steps.items():                      # 각 단차 +X 쪽 벽 바로 아래 0.4 mm 그림자(가림)
    shadow = (xx > ctr + half) & (xx < ctr + half + 0.4) & (abs(yy - ctr) < half)
    H_meas[shadow] = np.nan

valid = np.isfinite(H_meas)
for w in (0.0, 0.05, 0.1, 0.25, 0.5):                       # 경계 띠 폭 민감도
    M_eval = M_ref & valid & ~step_edge_band(H_ref, w, res)
    m = height_metrics((H_meas - H_ref)[M_eval], tol=0.1)
    print(f"경계 띠 {w:4.2f} mm: n={m['n']:6d}, RMS {m['rms_um']:6.2f} um, max|e| {m['max_abs_um']:7.1f} um")

M_area = M_ref & ~step_edge_band(H_ref, 0.25, res)          # J2 설정 edge_band_mm: 0.25
df = metrics_by_region(H_meas, H_ref, M_area, regions, res, tol=0.1)
M_eval = M_area & valid                                      # G4 의 M_eval
cols = ["region", "n", "area_mm2", "coverage_pct", "mean_um", "std_um", "rms_um", "p95_abs_um", "max_abs_um", "within_tol_pct", "flag"]
print(df[cols].to_string(index=False))
r = df.iloc[0]
print(f"검산: RMS² = mean² + std²(ddof=0) → {r.rms_um**2:.2f} ≈ {r.mean_um**2 + (r.std_um**2)*(r.n-1)/r.n:.2f}")
print(f"평가 영역 비율: {100 * M_eval.sum() / M_ref.sum():.1f} % (M_ref 대비)")
df.to_csv("S00_r01_H5_height_metrics.csv", index=False)
```

```text
$ python3 demo_h5.py
경계 띠 0.00 mm: n=237000, RMS  55.55 um, max|e|   640.0 um
경계 띠 0.05 mm: n=223928, RMS  21.59 um, max|e|   211.8 um
경계 띠 0.10 mm: n=204470, RMS  17.84 um, max|e|    49.6 um
경계 띠 0.25 mm: n=159384, RMS  17.53 um, max|e|    49.6 um
경계 띠 0.50 mm: n= 74420, RMS  15.78 um, max|e|    44.8 um
 region      n  area_mm2  coverage_pct  mean_um  std_um  rms_um  p95_abs_um  max_abs_um  within_tol_pct flag
    ALL 159384    63.754        96.841    0.680  17.514  17.527      30.410      49.625           100.0   OK
S1_base  84036    33.614        96.776   10.000   4.990  11.176      18.220      31.793           100.0   OK
     S2  54636    21.854        97.155  -20.009   5.011  20.627      28.273      41.816           100.0   OK
     S3  14936     5.974        94.916   29.963   5.029  30.382      38.271      49.625           100.0   OK
 S4_top   5776     2.310       100.000  -14.949   4.986  15.759      22.983      35.632           100.0   OK
검산: RMS² = mean² + std²(ddof=0) → 307.20 ≈ 307.20
평가 영역 비율: 63.8 % (M_ref 대비)
```

**결과 읽는 법**
- **경계 띠 민감도**: 띠가 없으면 RMS 55.6 µm, 최대 640 µm (경계에서 뭉개진 값). 띠 0.1 mm 부터 RMS 가 약 17.5 µm 로 안정되고, 0.25 mm 에서도 거의 같습니다 → 0.25 mm 가 안전한 선택입니다. 0.5 mm 에서 RMS 가 15.8 µm 로 더 줄어든 것은 엣지가 아니라 **작은 윗면 영역이 통째로 빠지면서 영역 구성이 바뀌었기** 때문입니다 (n 이 절반 이하). 띠를 너무 넓히면 대표성이 떨어집니다.
- **영역별 평균**이 정답(+10.0, −20.0, +30.0, −15.0 µm)을 0.1 µm 안에서 복원했고, 영역별 표준편차는 노이즈 5 µm 와 같습니다.
- **ALL 행의 평균 +0.68 µm**: 영역별 +와 −가 상쇄되어 "오차가 거의 없다"처럼 보입니다. 반면 ALL 의 표준편차·RMS(17.5 µm)는 영역 간 차이를 드러냅니다 → **영역별 표가 반드시 필요한 이유**입니다.
- **커버리지**: 그림자 때문에 S1~S3 는 95~97 % 입니다. S4_top 은 가장 위라 그림자가 없어 100 % 입니다.
- 검산: RMS² = 평균² + 표준편차²(n 기준) 가 일치합니다.

### 6.3 단위 테스트 `test_h5.py`

```python
"""H5 단위 테스트. 실행: pytest -q test_h5.py"""
import numpy as np
from h5_height_metrics import height_metrics, edge_band


def test_부호와_기본지표():
    e = np.array([0.01, -0.01, 0.03, np.nan])          # mm, NaN 은 자동 제외
    m = height_metrics(e, tol=0.02)
    assert m["n"] == 3 and abs(m["mean_um"] - 10.0) < 1e-9
    assert abs(m["rms_um"] ** 2 - (100 + 100 + 900) / 3) < 1e-6
    assert abs(m["within_tol_pct"] - 200 / 3) < 1e-9


def test_평균이_상쇄되는_경우():
    m = height_metrics(np.array([0.1, -0.1]))
    assert abs(m["mean_um"]) < 1e-9 and abs(m["rms_um"] - 100) < 1e-9   # 평균 0, RMS 100 um


def test_경계띠_폭():
    M = np.zeros((50, 50), bool); M[10:40, 10:40] = True
    band = edge_band(M, 0.04, res=0.02)                 # 경계 양쪽 2칸
    assert band[10, 20] and band[11, 20] and not band[12, 20] and band[9, 20] and band[8, 20] and not band[7, 20]
```

```text
$ python3 -m pytest -q test_h5.py
3 passed in 0.xxs
```

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 영역별 치우침 복원 | 합성 계단 (데모) | 각 영역 \|평균 − 정답\| ≤ 1 µm |
| 흩어짐 복원 | 합성, 노이즈 5 µm | 영역별 std 4.5 ~ 5.5 µm |
| 관계식 검산 | RMS² = mean² + std²(n) | 상대 차이 < 10⁻⁶ |
| 경계 띠 안정성 | 0.1 / 0.25 / 0.5 mm 비교 (실측) | 0.1 → 0.25 mm 사이 RMS 변화 < 2 µm 또는 < 10 % |
| 격자 일치 검사 | 측정·기준 JSON | 불일치 시 실행 중단 (자동) |
| 커버리지 보고 | 모든 영역 | CSV 에 coverage_pct 포함, < 80 % 면 `CHECK` |
| 반복성 (실측) | 같은 시편 3회 스캔, 영역별 평균 | 표준편차 ≤ 3 µm (A2 Z 반복성 목표 5 µm 이내) |
| M4 | 시편 1개 H1→H5 완주 | CSV + 그림 2종 + 요약 1쪽 |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 평균 하나만 보고 | +와 −가 상쇄되어 "오차 0" | 평균 + RMS + P95 + 공차 만족률 동시 보고 |
| `기준 − 측정` 으로 계산 | 과충진이 −로 나와 해석이 반대 | `e = H_meas − H_ref` 고정, 단위 테스트로 부호 확인 |
| NaN 을 0 으로 바꿔 계산 | 가림 영역에서 큰 음의 오차가 생김 | `np.isfinite` 로 제외 (함수에 포함) |
| 경계 띠 없이 계산 | max \|e\| 가 수백 µm, RMS 가 3배 | `step_edge_band` 적용 |
| 경계 띠를 바깥 경계에만 적용 | 계단 시편에서 단차마다 큰 오차 | 모든 높이 경계에 적용 |
| 칸 수로 신뢰구간 계산 (`std/√n`) | 신뢰구간이 0.01 µm 처럼 비현실적으로 좁음 | H5 는 기술 통계만, 추론은 H8 시편 단위 |
| 크기가 다른 영역의 지표를 그대로 비교 | 작은 영역이 엣지 영향으로 늘 나빠 보임 | 면적·n 함께 표시, 최소 칸 수 기준 |
| 서포트·스커트 포함 | 평균이 이상하게 치우침 | G4 `M_type` 적용 |
| 히트맵 색 범위를 시편마다 자동 | 시편끼리 색 비교 불가 | ±0.2 mm 고정, 0 = 흰색 (J4) |

---

## 9. 위험 요소

- **기준 높이 자체의 오차**: G3 기준 높이맵은 "층 Z = 윗면" 가정입니다(G2). 첫 층 눌림, 슬라이서의 Z 오프셋, 프린터 Z-오프셋이 있으면 모든 영역에 같은 치우침이 생깁니다. 모든 영역의 평균이 같은 방향으로 비슷하게 치우치면 이 가능성을 먼저 확인합니다.
- **표면 영향(E1)**: 반투명 재료는 레이저가 표면 아래에서 산란해 높이가 낮게 측정됩니다(수십 µm). H5 결과의 치우침이 재료 탓인지 공정 탓인지는 E1 실험과 I1 불확도로 구분합니다.
- **평가 영역의 대표성**: 가림이 심한 형상(좁은 홈 등)은 커버리지가 낮아 지표가 남은 부분만 대표합니다. 커버리지와 함께 보고하지 않으면 과대 해석됩니다.
- **최상층만 보는 한계**: 공정 후 측정(C2 1단계)은 윗면만 봅니다. 내부 층 오차는 층별 측정(2단계)에서 같은 함수를 층 마스크로 반복 적용해 얻습니다.

---

## 10. 기록 양식

`_H5_height_metrics.csv` 열 (한 시편·스캔 = 여러 행)
```text
scan_id,specimen_id,region,n,area_mm2,coverage_pct,mean_um,std_um,rms_um,mae_um,p05_um,p95_um,p95_abs_um,max_abs_um,within_tol_pct,flag,edge_band_mm,tolerance_mm,calibration_id,git_commit
```

시편 요약 기록표 (보고서 1쪽 요약용)

| 영역 | 면적 mm² | 커버리지 % | 평균 µm | RMS µm | P95(\|e\|) µm | 공차 만족 % | 비고 |
|---|---|---|---|---|---|---|---|
| ALL | | | | | | | |
| 윗면 | | | | | | | |
| 외벽 | | | | | | | |
| 채움 | | | | | | | |

---

## 11. 참고 자료

- ISO 25178-2 (면 표면 조직 매개변수: Sa, Sq 등 — RMS·평균 절대값과 같은 개념의 면 지표)
- JCGM 100:2008 (GUM) — 측정 결과와 불확도 표기 방식 (I1 연계)
- NumPy 문서: `numpy.percentile`, `numpy.nanmean`; SciPy 문서: `scipy.ndimage.distance_transform_edt`; pandas 문서: "10 minutes to pandas"
- 청사진 관련 절: [BLUEPRINT](../../BLUEPRINT.md) H5, A1, E2, G4, J4
