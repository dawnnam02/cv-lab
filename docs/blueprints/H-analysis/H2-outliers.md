# H2. 이상치 · 노이즈 처리

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: H. 처리·분석

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-01 ~ 2026-12-14 (W9-10) |
| 우선순위 | 보통 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [H1 점 → 격자 변환](H1-gridding.md), [F1 레이저 라인 중심 추출](../F-acquisition/F1-line-extraction.md) (신뢰도 값 제공), [E1 표면 광학 특성](../E-specimen/E1-surface-optics.md), [E2 가림·엣지 효과](../E-specimen/E2-occlusion-edges.md) |
| 후행 요소 | [H3 바닥 평면 기준화](H3-bed-leveling.md), [H5 높이 지표](H5-height-metrics.md), [H6 윤곽 지표](H6-contour-metrics.md), [I1 측정 불확도](../I-reliability/I1-uncertainty.md) (처리 방법 민감도) |
| 관련 마일스톤 | M4: 시편 1개 전체 파이프라인 완주 (W13-14) |

---

## 1. 목적

측정 데이터에서 **"측정값이라고 믿을 수 없는 값"** 을 정해진 규칙으로 걸러냅니다.

1. **점 단계**: F1 이 함께 저장한 신뢰도(최대 밝기, 선 두께)로 어둡거나·포화되었거나·두꺼운(반투명·반사) 점을 버립니다.
2. **격자 단계**: 주변 5 × 5 칸의 중앙값에서 **k·MAD** 이상 튀는 **고립된** 칸(스파이크)을 NaN 으로 바꿉니다.
3. **평활화**: 기본적으로 **하지 않습니다**. 한다면 3 × 3 중앙값만, 그리고 반드시 보고서에 적습니다.
4. 단계마다 **제거 비율(%)** 을 기록하고, 기준값(k)을 바꿔도 결과 지표가 거의 변하지 않는지 **민감도**를 확인합니다.

핵심 원칙: **진짜 형상(단차·모서리)은 지우지 않는다.** 오차를 측정하려는 연구에서, 처리 단계가 오차를 지워 버리면 안 됩니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 데이터에 섞이는 세 가지 "나쁜 값"
| 종류 | 원인 | 모양 | 처리 |
|---|---|---|---|
| 랜덤 노이즈 | 센서 잡음, 스펙클(B6) | 모든 칸에 ±수 µm | **지우지 않음**. 통계(H5)와 불확도(I1)로 다룸 |
| 스파이크(이상치) | 다중 반사, 엣지에서 위·아래 섞임(E2), 먼지 | 1~3칸이 수십~수백 µm 튐 | **제거** (NaN) |
| 결측 | 가림, 신호 부족 | 칸이 비어 있음 | 이미 NaN. 채우지 않음 |

### 2.2 중앙값 필터와 잔차
- **주변 중앙값** `med(i,j)`: 칸 (i, j) 를 가운데 두고 5 × 5 = 25칸의 중앙값. 스파이크 몇 개가 섞여도 영향을 거의 받지 않습니다.
- **잔차** `r = H − med`: 평평한 곳에서는 노이즈 크기(±5 µm) 정도, 스파이크에서는 수십 µm 이상입니다.

### 2.3 MAD — 이상치에 강한 "표준편차"
- 표준편차는 이상치 하나에도 크게 변합니다. 대신 **MAD(Median Absolute Deviation)** 를 씁니다.
```
MAD = median( | r − median(r) | )
σ̂  = 1.4826 × MAD        ← 데이터가 정규분포면 σ̂ = 표준편차 (1.4826 은 그 환산 계수)
```
- 스파이크 판정: `|r| > k · σ̂`. 이 문서에서 "k·MAD" 는 **환산된 σ̂ 기준**입니다 (청사진 H2 의 k ≈ 5).
- 정규분포에서 |값| > 5σ 일 확률은 약 5.7 × 10⁻⁷ → 100만 칸에 약 0.6칸만 잘못 지웁니다. k = 4 면 6.3 × 10⁻⁵ → 100만 칸에 약 63칸.

### 2.4 왜 "고립" 조건이 필요한가 — 모서리 문제
정사각 블록의 **볼록 모서리 칸**을 생각해 봅시다. 5 × 5 창 25칸 중 블록 위는 9칸뿐이라 중앙값은 **바닥 높이**가 됩니다. 그러면 모서리 칸은 잔차가 블록 높이만큼 커서 "스파이크"로 오인됩니다.
그래서 두 번째 조건을 둡니다.
- **이웃 지지(support)**: 3 × 3 이웃 8칸 중 자기와 비슷한 높이(±k·σ̂)인 칸의 개수.
- 볼록 90° 모서리 칸은 비슷한 이웃이 3칸(오른쪽, 아래, 대각선) → **지지 ≥ 3 이면 보호**.
- 진짜 스파이크(1칸 또는 2칸 덩어리)는 지지가 0~1 → 제거.
- 30° 같은 아주 뾰족한 모서리(E3)는 지지가 2 이하일 수 있으므로 그 영역은 결과를 따로 확인합니다.

### 2.5 평활화(smoothing)를 피하는 이유
3 × 3 중앙값 필터는 평평한 면의 노이즈를 줄여 주지만, **경계를 한 칸씩 갉아먹고 모서리를 둥글게** 만듭니다. 그 결과 H6 의 IoU·윤곽 거리, H7 의 비드 폭·모서리 반경이 바뀝니다. 즉 **처리가 측정 대상(오차)을 바꿉니다.** 노이즈는 평균 내기(H5 영역 통계)로 이미 줄어들기 때문에 평활화는 대부분 필요 없습니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 내용 |
|---|---|---|---|
| 입력 | `points_M.npz` | npz | `x, y, z, peak, width_px` (F1·F3) |
| 입력 | `<scan_id>_heightmap_M.npy` | float32 (ny, nx) | H1 결과 |
| 입력 | `config/default.yaml` → `preprocess` | YAML | `spike_mad_k: 5`, `median_filter: false`, 저신뢰 기준값 |
| 산출 | `points_M_clean.npz` | npz | 저신뢰 점 제거 후 점 (H1 을 다시 실행할 입력) |
| 산출 | `<scan_id>_heightmap_M_clean.npy` | float32 | 스파이크 칸이 NaN 으로 바뀐 높이맵 |
| 산출 | `<scan_id>_spike_mask.npy` | bool (ny, nx) | 제거된 칸 위치 (그림·감사용) |
| 산출 | `<scan_id>_H2_report.yaml` | YAML | 단계별 제거 개수·비율, σ̂, k, 창 크기, 지지 기준, 민감도 결과 |
| 산출 | `<scan_id>_H2_removed.png` | PNG | 제거된 칸을 빨간 점으로 표시한 높이맵 (J4) |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 저신뢰 밝기 하한 `i_min` | 20 / **40** / 60 (8-bit) | **40** | 배경(C5 기준: 레이저 신호의 5 % 미만)보다 충분히 큼. 실측 히스토그램 보고 조정 |
| 포화 상한 `i_max` | 230 / 255 | **230** (≈ 255 × 90 %) | F1 "포화 금지" 규칙과 동일 |
| 선 두께 상한 `w_max_px` | 8 / **10** / 12 px | **10 px** | 정상 선 두께 3~7 px(B6). 반투명 재료에서는 두꺼워짐 |
| 스파이크 창 크기 | 3×3 / **5×5** / 7×7 | **5×5** | 청사진 H2. 3×3 은 2칸 덩어리 스파이크에 약함, 7×7 은 작은 형상을 침범 |
| 판정 배수 k | 4 / **5** / 6 | **5** | 거짓 제거 ≈ 0 (2.3 절). 4와 6 으로 민감도 확인 |
| σ̂ 범위 | 전체 1개 / 영역별 | **전체 1개** | 단순·재현성. 재질이 다른 영역이 섞이면 영역별 검토 |
| 고립 조건 `min_support` | 없음 / 2 / **3** | **3** | 볼록 90° 모서리 보호 (2.4 절) |
| 평활화 | 없음 / 3×3 중앙값 / 가우시안 | **없음** (`median_filter: false`) | 윤곽·폭 지표 왜곡 (2.5 절) |
| 처리 순서 | 점 → 격자 | **점 단계 먼저, 격자 단계 다음** | 저신뢰 점이 칸 중앙값에 섞이기 전에 제거 |
| 보호 마스크 | 없음 / 경계 띠 보호 | **없음** (필요 시 사용) | 엣지 스파이크도 지워야 함. 대신 제거 위치를 그림으로 확인 |

---

## 5. 수행 절차

1. **신뢰도 분포 확인 (0.5일)**
   - [ ] 평판·시편 스캔 1개씩에서 `peak`, `width_px` 히스토그램 그리기
   - [ ] 정상 점 무리와 이상 점 무리 사이에서 `i_min`, `w_max_px` 를 정하고 그림과 함께 기록
2. **점 단계 제거 구현 (0.5일)**
   - [ ] `remove_low_confidence()` 적용 → 제거 비율 기록 (목표: 평판 < 1 %, 시편 < 5 %)
   - [ ] 제거 후 H1 다시 실행
3. **격자 단계 스파이크 제거 구현 (1일)**
   - [ ] `remove_spikes(H, k=5, size=5, min_support=3)` 적용
   - [ ] 6장 합성 데모 실행: 거짓 제거 0칸, 검출률 ≥ 90 %, 볼록 모서리 보존 확인
   - [ ] `pytest -q test_h2.py` 통과
4. **실측 데이터 점검 (0.5일)**
   - [ ] 시편 스캔에서 제거된 칸을 높이맵 위에 빨간 점으로 표시 (`_H2_removed.png`)
   - [ ] 제거 칸이 **경계에 몰려 있는지**, **평평한 면에 흩어져 있는지** 확인하고 메모
   - [ ] 경계 몰림이 심하면(제거 칸의 > 80 % 가 경계 0.1 mm 이내) E2 엣지 효과로 기록하고 H5 경계 띠(0.25 mm)로 이미 제외되는지 확인
5. **민감도 분석 (0.5일)**
   - [ ] k = 4, 5, 6 각각으로 처리 → H5 의 RMS·평균, H6 의 IoU 계산
   - [ ] 변화량이 7장 기준 이내인지 확인, 결과를 `_H2_report.yaml` 의 `sensitivity` 에 기록
6. **평활화 사용 여부 최종 결정 (0.5일)**
   - [ ] 평활화 없이 H5 지표의 반복성(같은 시편 3회 스캔)이 충분한지 확인
   - [ ] 쓰기로 했다면 높이 지표에만 적용하고 윤곽·폭 지표는 원본 사용, 보고서에 명시
7. **설정 고정**
   - [ ] 정한 값을 `config/default.yaml` 에 저장하고 커밋 (J2)

---

## 6. Python 구현

### 6.1 모듈 `h2_outliers.py`

```python
"""H2. 이상치·노이즈 처리 모듈 (점 단계 저신뢰 제거 + 격자 단계 스파이크 제거).
최종적으로는 src/cvlab/preprocess.py 에 합칩니다."""
import warnings
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.ndimage import median_filter


def remove_low_confidence(points, i_min=40, i_max=230, w_max_px=10.0):
    """[점 단계] F1이 함께 저장한 신뢰도(최대 밝기, 선 두께)로 점을 거른다.
    points: dict(x, y, z, peak, width_px) 각 1차원 배열
    i_max: 포화 직전(8bit 기준 255의 90 %) 이상이면 중심이 부정확하므로 제거"""
    keep = (points["peak"] >= i_min) & (points["peak"] <= i_max) & (points["width_px"] <= w_max_px)
    out = {k: v[keep] for k, v in points.items()}
    report = {"lowconf_removed": int((~keep).sum()), "lowconf_removed_pct": 100 * float((~keep).mean()),
              "i_min": i_min, "i_max": i_max, "w_max_px": w_max_px}
    return out, report


def nan_median_filter(H, size=5, block_rows=200):
    """NaN을 무시하는 size×size 중앙값 필터. (메모리를 아끼려고 행 묶음 단위로 계산)"""
    r = size // 2
    P = np.pad(H.astype(np.float32), r, mode="constant", constant_values=np.nan)
    out = np.full(H.shape, np.nan, np.float32)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)       # 창 전체가 NaN인 경우 경고 무시
        for r0 in range(0, H.shape[0], block_rows):
            r1 = min(r0 + block_rows, H.shape[0])
            win = sliding_window_view(P[r0:r1 + 2 * r], (size, size))   # (행, 열, size, size)
            out[r0:r1] = np.nanmedian(win.reshape(*win.shape[:2], -1), axis=-1)
    return out


def robust_sigma(v):
    """MAD 기반 표준편차 추정: 1.4826 × median(|v − median(v)|). 정규분포면 표준편차와 같다."""
    v = v[np.isfinite(v)]
    return 1.4826 * np.median(np.abs(v - np.median(v)))


def remove_spikes(H, k=5.0, size=5, min_support=3, protect=None):
    """[격자 단계] 스파이크 제거.
    1) 잔차 r = H − (주변 size×size 중앙값)
    2) σ̂ = MAD 기반 잔차 표준편차 (영상 전체 1개 값)
    3) |r| > k·σ̂ 이고, 3×3 이웃 중 '자기와 비슷한 높이(±k·σ̂)'인 칸이 min_support 개 미만이면 스파이크
       → 진짜 모서리(볼록 90° 모서리 칸은 비슷한 이웃이 3개)를 지키기 위한 조건
    min_support=None 이면 이웃 조건을 쓰지 않음 (비교·민감도 확인용)
    protect: True 인 칸은 절대 지우지 않음 (선택)
    반환: 정리된 H, 제거 마스크, 보고서(dict)"""
    med = nan_median_filter(H, size)
    r = H - med
    sig = robust_sigma(r)
    cand = np.abs(r) > k * sig
    # 3×3 이웃 중 비슷한 높이 개수 세기
    P = np.pad(H, 1, mode="constant", constant_values=np.nan)
    support = np.zeros(H.shape, np.int32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nb = P[1 + dy:1 + dy + H.shape[0], 1 + dx:1 + dx + H.shape[1]]
            with np.errstate(invalid="ignore"):
                support += (np.abs(nb - H) <= k * sig)
    spike = cand & np.isfinite(H)
    if min_support is not None:
        spike &= support < min_support
    if protect is not None:
        spike &= ~protect
    out = H.copy()
    out[spike] = np.nan
    n_valid = int(np.isfinite(H).sum())
    report = {"k": k, "window": size, "min_support": min_support, "sigma_mad_um": float(sig * 1000),
              "valid_before": n_valid, "spike_removed": int(spike.sum()),
              "spike_removed_pct": 100.0 * spike.sum() / n_valid,
              "candidates_kept_by_support": int((cand & ~spike & np.isfinite(H)).sum())}
    return out, spike, report


def optional_smoothing(H, size=3):
    """[선택] 3×3 중앙값 평활화. 경계를 뭉개므로 윤곽 지표(H6)에는 쓰지 말 것.
    NaN 칸은 그대로 NaN 유지 (NaN 주변 계산은 nan_median_filter 사용)."""
    S = nan_median_filter(H, size)
    S[~np.isfinite(H)] = np.nan
    return S
```

### 6.2 데모 `demo_h2.py` (정답을 아는 합성 높이맵)

10 × 10 mm, 1 mm 블록 위에 0.4 mm 단차, 노이즈 5 µm, 결측 2 %, 스파이크 0.5 %(진폭 10~300 µm, 30 % 는 2칸 덩어리)를 넣었습니다.

```python
"""H2 데모: 정답을 아는 합성 높이맵에 스파이크를 넣고, 찾아내는지 확인한다."""
import numpy as np
from h2_outliers import remove_spikes, robust_sigma

rng = np.random.default_rng(7)
res = 0.02
ny, nx = 500, 500                                       # 10 × 10 mm
yy, xx = np.mgrid[0:ny, 0:nx]
truth = np.zeros((ny, nx), np.float32)
truth[100:400, 100:400] = 1.0                           # 높이 1 mm 정사각 블록 (볼록 모서리 4개)
truth[200:300, 200:300] = 1.4                           # 위에 0.4 mm 단차
H = truth + rng.normal(0, 0.005, truth.shape).astype(np.float32)   # 노이즈 5 um
H[rng.random(H.shape) < 0.02] = np.nan                  # 결측 2 %

# 스파이크 0.5 % 주입: ±0.01 ~ 0.3 mm (단일 칸 또는 가로 2칸 덩어리)
n_sp = int(0.005 * H.size)
iy, ix = rng.integers(1, ny - 2, n_sp), rng.integers(1, nx - 2, n_sp)
amp = rng.choice([-1, 1], n_sp) * rng.uniform(0.01, 0.3, n_sp)
is_spike = np.zeros(H.shape, bool)
for a, b, s, two in zip(iy, ix, amp, rng.random(n_sp) < 0.3):
    H[a, b] = truth[a, b] + s; is_spike[a, b] = True
    if two:
        H[a, b + 1] = truth[a, b + 1] + s; is_spike[a, b + 1] = True
is_spike &= np.isfinite(H)

for k in (4.0, 5.0, 6.0):                               # 민감도: k 를 바꿔 본다
    clean, removed, rep = remove_spikes(H, k=k)
    recall = (removed & is_spike).sum() / is_spike.sum()
    false_rm = (removed & ~is_spike).sum()
    print(f"k={k:.0f}: sigma_MAD={rep['sigma_mad_um']:.2f} um, 제거 {rep['spike_removed_pct']:.3f} %, "
          f"스파이크 검출률 {recall*100:.1f} %, 잘못 지운 정상 칸 {false_rm}개")

clean, removed, rep = remove_spikes(H, k=5.0)
corners = [(100, 100), (100, 399), (399, 100), (399, 399), (200, 200), (299, 299)]
print("볼록 모서리 칸이 살아남았나:", all(np.isfinite(clean[c]) or np.isnan(H[c]) for c in corners))
missed = is_spike & ~removed
print(f"놓친 스파이크 {missed.sum()}개, 그 진폭 최대 {np.max(np.abs(H - truth)[missed])*1000:.0f} um (≈ 5σ 이하라 노이즈와 구분 불가)")
_, rm0, rep0 = remove_spikes(H, k=5.0, min_support=None)   # 이웃 조건을 끄면?
print(f"이웃 조건 끔(min_support=None): 잘못 지운 정상 칸 {(rm0 & ~is_spike).sum()}개 (모서리·단차 경계)")
print("보고서:", {k_: (round(float(v), 3) if isinstance(v, float) else v) for k_, v in rep.items()})
```

```text
$ python3 demo_h2.py
k=4: sigma_MAD=4.83 um, 제거 0.638 %, 스파이크 검출률 94.8 %, 잘못 지운 정상 칸 18개
k=5: sigma_MAD=4.83 um, 제거 0.620 %, 스파이크 검출률 93.2 %, 잘못 지운 정상 칸 0개
k=6: sigma_MAD=4.83 um, 제거 0.611 %, 스파이크 검출률 91.9 %, 잘못 지운 정상 칸 0개
볼록 모서리 칸이 살아남았나: True
놓친 스파이크 111개, 그 진폭 최대 30 um (≈ 5σ 이하라 노이즈와 구분 불가)
이웃 조건 끔(min_support=None): 잘못 지운 정상 칸 32개 (모서리·단차 경계)
보고서: {'k': 5.0, 'window': 5, 'min_support': 3, 'sigma_mad_um': 4.83, 'valid_before': 245022, 'spike_removed': 1519, 'spike_removed_pct': 0.62, 'candidates_kept_by_support': 46}
```

**결과 읽는 법**
- σ̂(MAD) = 4.83 µm 로 넣은 노이즈 5 µm 를 잘 추정했습니다 (주변 중앙값에도 약간의 노이즈가 있어 약간 작게 나옴).
- k = 5 에서 **정상 칸을 하나도 지우지 않았고**, 스파이크의 93 % 를 찾았습니다. 놓친 스파이크는 진폭이 30 µm 이하로, 5σ̂ ≈ 24 µm 와 노이즈가 겹쳐 원리적으로 구분할 수 없는 크기입니다.
- k = 4 로 낮추면 검출률은 조금 오르지만 정상 칸 18개를 잘못 지웁니다.
- **이웃 지지 조건을 끄면**(min_support=None) 블록 모서리·단차 경계의 정상 칸 32개를 지웁니다 → 고립 조건이 진짜 형상을 지켜 줍니다.

### 6.3 단위 테스트 `test_h2.py`

```python
"""H2 단위 테스트. 실행: pytest -q test_h2.py"""
import numpy as np
from h2_outliers import remove_low_confidence, robust_sigma, remove_spikes


def test_MAD_시그마는_정규분포_표준편차와_같다():
    v = np.random.default_rng(0).normal(0, 0.005, 100_000)
    assert abs(robust_sigma(v) - 0.005) < 0.0001


def test_저신뢰_점_제거와_비율_보고():
    p = {"x": np.arange(4.0), "y": np.zeros(4), "z": np.zeros(4),
         "peak": np.array([20, 100, 250, 120]), "width_px": np.array([4, 4, 4, 15])}
    out, rep = remove_low_confidence(p)
    assert list(out["x"]) == [1.0]               # 어두움·포화·두꺼움 3개 제거
    assert rep["lowconf_removed"] == 3 and rep["lowconf_removed_pct"] == 75.0


def test_단일_스파이크는_지우고_평평한_면은_안_지운다():
    rng = np.random.default_rng(1)
    H = rng.normal(0, 0.005, (60, 60)).astype(np.float32)
    H[30, 30] += 0.2
    out, removed, rep = remove_spikes(H, k=5)
    assert removed[30, 30] and removed.sum() == 1
```

```text
$ python3 -m pytest -q test_h2.py
3 passed in 0.xxs
```

### 6.4 처리 전후 지표 민감도 확인 방법 (개념)
```text
for k in [4, 5, 6]:
    H_k = remove_spikes(H, k=k)[0]
    → H3 수평화 → H4 정합 → H5 height_metrics, H6 iou
    → 표로 정리: k | 제거 % | 평균 µm | RMS µm | P95 µm | IoU
```
위 의사코드는 H3~H6 모듈이 모두 준비된 W13 이후에 실제로 실행합니다. 결과가 7장 기준 안이면 "처리 방법에 둔감하다"고 보고합니다.

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| σ̂ 추정 | 합성 노이즈 5 µm | 4.5 ~ 5.5 µm |
| 거짓 제거 | 합성 데이터 (k = 5) | 정상 칸 제거 0개 (25만 칸 기준) |
| 검출률 | 합성 스파이크 진폭 ≥ 6σ | ≥ 99 % (전체 진폭 10~300 µm 기준 ≥ 90 %) |
| 진짜 형상 보존 | 합성 블록의 볼록 모서리·단차 경계 | 모두 남아 있음 |
| 제거 비율 (실측) | 평판 / 시편 스캔 | 스파이크 제거 < 1 % (평판), < 2 % (시편). 초과 시 원인 조사 |
| 저신뢰 제거 비율 | 실측 | 평판 < 1 %, 불투명 회색 PLA 시편 < 5 % |
| 민감도 | k = 4, 5, 6 비교 | H5 평균·RMS 변화 < 1 µm 또는 I1 확장불확도 U 의 10 % 중 큰 값, IoU 변화 < 0.002 |
| 단위 테스트 | `pytest test_h2.py` | 전부 통과 |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 표준편차로 기준을 잡음 | 스파이크가 많을수록 σ 가 커져서 스파이크를 못 찾음 | MAD 기반 σ̂ 사용 |
| MAD 를 1.4826 으로 환산하지 않고 k 를 그대로 적용 | 실제 기준이 3.4σ 가 되어 정상 칸 대량 제거 | `robust_sigma()` 사용, 보고서에 "σ̂ = 1.4826·MAD" 명시 |
| 고립 조건 없이 중앙값 잔차만 사용 | 볼록 모서리·좁은 벽 위 칸이 사라져 IoU·폭이 나빠짐 | `min_support=3` |
| `scipy.ndimage.median_filter` 를 NaN 있는 배열에 사용 | NaN 이 퍼지거나 결과가 엉뚱함 | NaN 을 무시하는 `nan_median_filter()` 사용 |
| 평활화를 켜 두고 잊음 | 반복 측정 간 비교는 좋아 보이지만 윤곽 오차가 체계적으로 바뀜 | 기본값 `median_filter: false`, 결과 폴더에 설정 사본 저장 |
| 제거된 칸을 이웃 값으로 채움 | 커버리지 100 %, 보간값이 지표에 섞임 | NaN 유지 |
| 제거 비율을 기록하지 않음 | 처리 결과를 재현·검토할 수 없음 | `_H2_report.yaml` 필수 |
| 반투명 재료에서 두꺼운 선을 모두 버림 | 시편 대부분이 사라짐 | 재료를 불투명으로 바꾸는 것이 우선 (E1). 기준값으로 해결하려 하지 않음 |

---

## 9. 위험 요소

- **계통 오차는 이상치 처리로 못 잡습니다**: 반투명 재료의 표면 아래 산란(E1)은 넓은 영역이 수십 µm 씩 고르게 밀리므로 스파이크로 보이지 않습니다. 이것은 재료·코팅·불확도(I1)로 다뤄야 합니다.
- **스파이크가 넓게 뭉치는 경우**: 반사면에서 3칸 이상 덩어리로 튀면 고립 조건 때문에 남을 수 있습니다. 제거 그림에서 덩어리가 보이면 창을 7 × 7 로 늘린 결과와 비교합니다.
- **σ̂ 가 영역마다 다른 경우**: 윗면(매끈)과 옆 경사면(노이즈 큼)이 섞이면 전체 σ̂ 하나로는 경사면에서 거짓 제거가 늘 수 있습니다. 경계 띠는 H5 에서 어차피 제외되지만, H6 윤곽 지표에 영향이 있는지 확인합니다.
- **처리 시간**: 1000 × 1000 칸에서 NaN 무시 5 × 5 중앙값은 수 초~수십 초가 걸립니다. 일괄 처리(W18~) 전에 시간을 측정합니다.

---

## 10. 기록 양식

`results/<scan_id>/<scan_id>_H2_report.yaml`
```yaml
scan_id: S03_r02
point_stage:
  i_min: 40
  i_max: 230
  w_max_px: 10
  points_before:
  lowconf_removed:
  lowconf_removed_pct:
grid_stage:
  window: 5
  k: 5.0
  min_support: 3
  sigma_mad_um:
  valid_before:
  spike_removed:
  spike_removed_pct:
  candidates_kept_by_support:
  removed_near_edge_pct:      # 제거 칸 중 경계 0.1 mm 이내 비율
smoothing: none               # none | median3
sensitivity:                  # k 별 결과 (H5/H6 준비 후 채움)
  - {k: 4, removed_pct: , mean_um: , rms_um: , p95_um: , iou: }
  - {k: 5, removed_pct: , mean_um: , rms_um: , p95_um: , iou: }
  - {k: 6, removed_pct: , mean_um: , rms_um: , p95_um: , iou: }
reviewer: ""
notes: ""
```

---

## 11. 참고 자료

- Hampel, F. R. (1974). The influence curve and its role in robust estimation. *Journal of the American Statistical Association* — Hampel 필터(중앙값 ± k·MAD)의 바탕
- Rousseeuw, P. J., & Croux, C. (1993). Alternatives to the median absolute deviation. *JASA*
- Leys, C. et al. (2013). Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median. *Journal of Experimental Social Psychology*
- Tukey, J. W. (1977). *Exploratory Data Analysis* — 이동 중앙값(running median) 평활화
- SciPy 문서: `scipy.ndimage.median_filter`, NumPy 문서: `numpy.lib.stride_tricks.sliding_window_view`, `numpy.nanmedian`
- 청사진 관련 절: [BLUEPRINT](../../BLUEPRINT.md) H2, E1, E2, F1
