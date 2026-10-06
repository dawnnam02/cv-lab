# H7. 치수 · 형상 지표

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: H. 처리·분석

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-29 ~ 2027-01-11 (W13-14) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [H4 정합](H4-registration.md), [H6 윤곽 지표](H6-contour-metrics.md) (등고선 점), [H3 바닥 평면 기준화](H3-bed-leveling.md), [G2 비드 형상 모델](../G-reference/G2-bead-model.md), [G1 G코드 파싱](../G-reference/G1-gcode-parsing.md) (경로 선분), [E3 시편 설계](../E-specimen/E3-test-artifact.md) |
| 후행 요소 | [H8 통계 분석](H8-statistics.md), [I3 교차검증](../I-reliability/I3-cross-validation.md) (마이크로미터·현미경과 비교), [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) (단차·평면도·구 지름), [J4 시각화·리포트](../J-software/J4-visualization-report.md) |
| 관련 마일스톤 | M4: 시편 1개 전체 파이프라인 완주 (W13-14) |

---

## 1. 목적

E3 시편의 각 형상에서 **설계값과 직접 비교할 수 있는 숫자(mm, %, µm)** 를 뽑습니다. 높이 지도(H5)나 윤곽 거리(H6)보다 공정 엔지니어에게 익숙한 언어입니다.

| 지표 | 대상 형상 (E3) | 방법 | 결과 |
|---|---|---|---|
| 지름, 원형도 | 원기둥·구멍 Ø2/4/6/10 | 원 맞춤 (대수적 → 기하학적) | 지름 오차 µm·%, 원형도 µm |
| 길이·폭 | 얇은 벽, 슬롯 | 마주 보는 경계에 직선 맞춤 | 폭 오차 µm |
| 단차 높이 | 계단 피라미드 | 각 면 중앙값 차 (경계 띠 제외) | 단차 오차 µm |
| 평면도 | 넓은 윗면 | 평면 맞춤 잔차 P-V (+ 강건 P-V) | µm |
| 모서리 반경 | 90°/60°/30° 모서리 | 모서리 경계 점에 원호 맞춤 | 반경 mm |
| **선(비드) 폭** | 단일 선 트랙 | 경로에 수직한 단면 → **반높이 폭(FWHM)** | 폭 오차 µm |
| 경로 이탈 | 단일 선 트랙 | 단면 중심 − G코드 경로 | µm (경로 왼쪽 +) |
| 위치 | 핀 격자 5 × 5 | 핀 중심 (ΔX, ΔY) 벡터 | 위치 오차 화살표 지도 |

---

## 2. 배경 지식 (초보자용)

### 2.1 원 맞춤 두 가지
- **대수적(Kåsa) 맞춤**: 원의 식 `x² + y² + Dx + Ey + F = 0` 이 D, E, F 에 대해 **직선(선형)** 이라는 점을 이용해 한 번에 풉니다. 빠르고 초깃값이 필요 없습니다. 하지만 **호의 일부만 보이면 반지름이 작게 치우칩니다** (6.2 데모: 90° 호에서 지름 −13.5 µm).
- **기하학적 맞춤**: 각 점에서 원까지의 실제 거리 `|p − c| − r` 의 제곱합을 최소화합니다(`least_squares`). 반복 계산이 필요하므로 Kåsa 결과를 초깃값으로 씁니다. 이것이 표준적인 **최소제곱원(LSC)** 입니다.
- 권장: **항상 Kåsa → 기하학적 두 단계**. 둘의 차이가 크면 점이 호 일부에만 몰렸다는 신호입니다.

### 2.2 원형도(진원도)
`원형도 = 최대 반경 − 최소 반경` (LSC 중심 기준). ISO 1101 의 정식 정의는 두 동심원 사이 간격이 최소가 되는 **최소 영역(MZC)** 방식이라 LSC 값보다 같거나 작습니다. 이 과제에서는 LSC 기준으로 계산하고 보고서에 "LSC 기준"이라고 적습니다.
노이즈도 원형도에 더해집니다: 노이즈 σ 3 µm, 점 600개면 노이즈만으로 약 ±3σ → 15~20 µm 가 더해질 수 있습니다 (6.2 데모: 형상 20 µm → 측정 31.8 µm). 원형도는 **노이즈 바닥값**(완전한 원 게이지·핀 게이지를 측정한 값)과 함께 보고합니다.

### 2.3 단차 높이와 평면도
- **단차**: 윗면과 아랫면에서 경계 0.25 mm 를 깎아낸 안쪽 칸들의 **중앙값** 차이. 경계 스파이크(E2)에 영향을 받지 않습니다.
- **평면도**: 최소제곱 평면을 뺀 잔차의 **최대 − 최소(P-V)**. 점이 많을수록, 스파이크가 하나만 있어도 커집니다. 그래서 **강건 P-V (99.5 % − 0.5 %)** 를 함께 보고합니다 (6.2 데모: 스파이크 1개로 P-V 104 µm, 강건 P-V 28 µm).

### 2.4 비드 폭 — 반높이 폭(FWHM)
단일 선 트랙을 G코드 경로에 **수직으로 자른 단면 프로파일**을 봅니다.
```
         ___________          ← 꼭대기 (top)
        /           \
   ----+-------------+----    ← 반높이 = 바닥 + (꼭대기 − 바닥)/2
      /               \
 ____/                 \____  ← 바닥 (base)
     |<--- FWHM --->|
```
- 바닥 = 프로파일 양 끝 15 % 의 중앙값, 꼭대기 = 최고점 근처(90 % 이상) 점들에 맞춘 포물선의 최고값 (최댓값 한 점은 노이즈 때문에 높게 치우침).
- 교차점은 이웃 샘플 사이 **선형 보간**으로 서브샘플 위치를 구합니다.
- **경로 이탈** = (왼쪽 교차점 + 오른쪽 교차점)/2. 진행 방향의 **왼쪽을 +** 로 정합니다.

**중요한 함정**: 위에서 본 G2 비드(가운데 사각형 + 양옆 반원)는 반원의 중심 높이(h/2)에서 높이가 **뚝 떨어집니다**. 그 높이가 하필 반높이라서, FWHM 은 격자·흐림에 따라 명목 폭보다 약 10 µm 작게 나옵니다 (6.2 데모: 명목 0.420 mm 모델 → FWHM 0.4106 mm).
→ 규칙: **측정 FWHM 을 명목 폭과 직접 비교하지 말고, 같은 방법으로 처리한 기준 모델(G3 기준 높이맵)의 FWHM 과 비교**합니다. 그러면 방법의 치우침이 상쇄됩니다 (데모: 폭 오차 +30.1 µm, 참값 +30 µm). 25 % 높이 폭도 같은 방식으로 함께 보고하면 단면 모양 변화를 볼 수 있습니다.

### 2.5 위치 오차 지도
핀 격자(5 × 5, 간격 20 mm) 각 핀의 중심을 원 맞춤으로 구하고, 설계 중심과의 차이 벡터 (ΔX, ΔY) 를 화살표로 그립니다. 화살표는 µm 크기라 **확대 배율을 그림에 적습니다** (J4).
- 전체에서 닮음 변환(이동·회전·배율, H4 Umeyama)을 빼면 **남는 무늬**가 장비의 성질을 드러냅니다. 예: X·Y 축이 직각이 아니면 잔차가 "y 가 클수록 x 가 +" 인 전단 무늬가 됩니다 (6.4 데모: 직각도 0.05° 를 0.0506° 로 복원).

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 내용 |
|---|---|---|---|
| 입력 | `<scan_id>_heightmap_G.npy` + `_grid_G.json` | float32 | H4 후 측정 높이맵 |
| 입력 | `<gcode>_heightmap_ref_G.npy` | float32 | G3 기준 높이맵 (비드 폭 비교용 기준 모델 포함) |
| 입력 | `<scan_id>_contour_dist.npz` | npz | H6 측정 등고선 점 (원·직선 맞춤용) |
| 입력 | E3 형상 목록 `features.csv` | CSV | feature_id, 종류(circle/hole/wall/slot/step/flat/track/pin), 설계값, 관련 다각형/선분 ID |
| 입력 | G1 경로 선분 | CSV/npz | 단일 선 트랙의 시작·끝 좌표 (비드 단면 위치) |
| 산출 | `<scan_id>_H7_dimensions.csv` | CSV | 형상별 1행: 종류, 설계값, 측정값, 오차(µm, %), 보조값(원형도, 강건 P-V, n_points 등) |
| 산출 | `<scan_id>_H7_bead_sections.csv` | CSV | 단면별: 경로 ID, 위치 s, FWHM_meas, FWHM_ref, 폭 오차, 경로 이탈, 비드 높이, FW25 |
| 산출 | `<scan_id>_H7_pins.csv` | CSV | 핀별: 설계 (x, y), 측정 (x, y), ΔX, ΔY, 잔차(닮음 제거 후) |
| 산출 | `<scan_id>_H7_position_map.png` | PNG | 위치 오차 / 닮음 제거 잔차 화살표 지도 (배율 표기) |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 원 맞춤 | Kåsa / 기하학적 / 최소영역 | **Kåsa → 기하학적 (LSC)** | 2.1 절. 최소영역은 선택 확장 |
| 원 맞춤 점 | 래스터 경계 칸 / **H6 서브픽셀 등고선** | **서브픽셀 등고선** | 양자화 감소 |
| 원 경계 높이 | Z − h/2 / 50 % | **H6 과 같은 규칙** (Z − h/2) + 민감도 | 지표 간 일관성 |
| 원형도 정의 | LSC / MZC | **LSC** (명시) | 구현 단순, 보고서에 정의 기재 |
| 폭 | 래스터 폭 / **두 직선 맞춤 거리** | **직선 맞춤** | 서브픽셀, 평행도도 확인 가능 |
| 단차 | 평균 차 / **중앙값 차** | **중앙값 차, 경계 0.25 mm 제외** | 스파이크 강건, 청사진 H7 |
| 평면도 | P-V / 강건 P-V / RMS | **P-V + 강건 P-V(99.5 − 0.5 %) + RMS** 모두 | 2.3 절 |
| 비드 폭 높이 | **50 % (FWHM)** / 25 % | **FWHM 주 지표**, 25 % 보조 | 청사진 H7 |
| 비드 폭 비교 대상 | 명목 폭 / **같은 방법으로 처리한 기준 모델** | **기준 모델 FWHM** (명목·압출량 기반 w 각각으로 만든 모델) | 2.4 절 함정 |
| 단면 간격·개수 | — | **경로 10 mm 당 20개 (0.5 mm 간격)**, 양 끝 1 mm 제외 | 시작·끝 압출 과도 구간 제외 |
| 단면 샘플 간격 | 0.02 / **0.005** mm | **0.005 mm** (이중선형 보간) | 교차점 보간 안정 |
| 경로 이탈 부호 | 오른쪽 + / **왼쪽 +** | **진행 방향 왼쪽 +** | 수학 관례(법선 = 방향을 반시계 90°) |

---

## 5. 수행 절차

1. **형상 목록 작성 (E3 담당과, 0.5일)**
   - [ ] `features.csv` 에 형상별 종류·설계값·영역 다각형 ID·경로 선분 ID 정리
2. **모듈 구현·테스트 (1.5일)**
   - [ ] 6.1 `h7_dimensional.py` → `src/cvlab/metrics.py`
   - [ ] `pytest -q test_h7.py` 통과 (완전한 원, 가우시안 FWHM = 2.3548σ, 단차)
3. **합성 데모로 확인 (0.5일)**
   - [ ] 6.2·6.4 데모: 지름 오차 ≤ 1 µm (전체 원), 폭 ≤ 1 µm, 단차 ≤ 1 µm, 비드 폭 오차 복원 ≤ 2 µm, 직각도 복원 ≤ 0.005°
4. **원·구멍 (1일)**
   - [ ] H6 등고선 점을 형상 영역별로 잘라 Kåsa → 기하학적 맞춤
   - [ ] Kåsa 와 기하학적 지름 차이 > 5 µm 인 형상은 가림(E2)으로 호가 잘렸는지 확인
   - [ ] 핀 게이지(인증 지름)로 노이즈 바닥 원형도 측정 → 기록
5. **단차·평면도 (0.5일)**
   - [ ] 계단 피라미드 각 단차 → 설계 0.2/0.4/1/2 mm 대비 오차
   - [ ] 넓은 윗면 평면도 3종 값
6. **비드 폭·경로 이탈 (1일)**
   - [ ] 단일 선 트랙마다 단면 20개 → FWHM_meas, 같은 위치의 FWHM_ref(명목 w 모델, 압출량 w_eff 모델 각각)
   - [ ] 트랙 방향(0°, 45°, 90° 등)별 평균 폭 오차·경로 이탈 표
7. **위치 지도 (0.5일)**
   - [ ] 핀 중심 → ΔX, ΔY 표 → 닮음 성분(배율·회전) 분리 → 잔차 화살표 지도
8. **교차검증 준비 (I3 연계)**
   - [ ] 마이크로미터로 단차·폭, 현미경으로 비드 폭을 잴 형상 3~5개 선정

---

## 6. Python 구현

### 6.1 모듈 `h7_dimensional.py`

```python
"""H7. 치수·형상 지표 모듈. 최종적으로 src/cvlab/metrics.py 에 합칩니다. 단위 mm."""
import numpy as np
from scipy.optimize import least_squares
from scipy.ndimage import binary_erosion, map_coordinates


# ---------- 원: 지름, 원형도 ----------
def fit_circle_kasa(P):
    """대수적(Kåsa) 원 맞춤: x²+y² + Dx + Ey + F = 0 을 선형 최소제곱으로. 빠르지만 짧은 호에서 치우침."""
    A = np.column_stack([P[:, 0], P[:, 1], np.ones(len(P))])
    b = -(P ** 2).sum(axis=1)
    D, E, F = np.linalg.lstsq(A, b, rcond=None)[0]
    c = np.array([-D / 2, -E / 2])
    return c, float(np.sqrt(c @ c - F))


def fit_circle_geometric(P, c0=None, r0=None):
    """기하학적 원 맞춤: Σ(|p−c| − r)² 최소화 (ISO 최소제곱원, LSC). Kåsa 결과를 초깃값으로."""
    if c0 is None:
        c0, r0 = fit_circle_kasa(P)
    fun = lambda q: np.linalg.norm(P - q[:2], axis=1) - q[2]
    q = least_squares(fun, [*c0, r0], method="lm").x
    return q[:2], float(q[2])


def roundness(P, c):
    """원형도(진원도) 근사 = 최대 반경 − 최소 반경 (최소제곱원 중심 기준).
    ISO 1101 의 '최소 영역' 방식보다 약간 크게 나온다 → 보고서에 'LSC 기준'이라고 명시."""
    r = np.linalg.norm(P - c, axis=1)
    return float(r.max() - r.min())


# ---------- 직선: 길이·폭 ----------
def fit_line_tls(P):
    """전체 최소제곱(TLS) 직선: 중심점 + 단위 방향벡터"""
    c = P.mean(axis=0)
    _, _, Vt = np.linalg.svd(P - c)
    return c, Vt[0]


def width_between_edges(P1, P2):
    """마주 보는 두 경계 점군 사이 폭: 각 점군에 직선 → 상대 점들까지 수직거리 평균(양방향 평균)"""
    def mean_dist(Pa, Pb):
        c, u = fit_line_tls(Pa)
        n = np.array([-u[1], u[0]])
        return np.abs((Pb - c) @ n).mean()
    return float(0.5 * (mean_dist(P1, P2) + mean_dist(P2, P1)))


# ---------- 높이: 단차, 평면도 ----------
def step_height(H, mask_hi, mask_lo, res, band_mm=0.25):
    """단차 = (윗면 중앙값) − (아랫면 중앙값). 각 면은 경계에서 band_mm 만큼 깎아낸 안쪽만 사용."""
    it = max(1, int(round(band_mm / res)))
    hi = binary_erosion(mask_hi, iterations=it) & np.isfinite(H)
    lo = binary_erosion(mask_lo, iterations=it) & np.isfinite(H)
    return float(np.median(H[hi]) - np.median(H[lo])), int(hi.sum()), int(lo.sum())


def flatness(H, mask, xs, ys):
    """최소제곱 평면을 빼고 남은 잔차의 P-V (최대−최소) 와 강건 P-V (99.5 %−0.5 %).
    P-V 는 점 하나의 스파이크에도 커지므로 둘 다 보고한다."""
    X, Y = np.meshgrid(xs, ys)
    m = mask & np.isfinite(H)
    A = np.column_stack([X[m], Y[m], np.ones(m.sum())])
    coef = np.linalg.lstsq(A, H[m], rcond=None)[0]
    res = H[m] - A @ coef
    tilt_deg = np.degrees(np.arctan(np.hypot(coef[0], coef[1])))
    return {"pv_um": 1000 * float(res.max() - res.min()),
            "pv_robust_um": 1000 * float(np.percentile(res, 99.5) - np.percentile(res, 0.5)),
            "rms_um": 1000 * float(res.std()), "tilt_deg": float(tilt_deg)}


# ---------- 선(비드) 폭: 단면 프로파일 + 반높이 폭(FWHM) ----------
def cross_section(H, xs, ys, p0, p1, s, half_len=0.6, step=0.005):
    """선분 p0→p1 위 위치 s(0~1)에서 경로에 수직인 단면 프로파일. 반환: 수직거리 d(왼쪽 +), 높이 z"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    u = (p1 - p0) / np.linalg.norm(p1 - p0)
    n = np.array([-u[1], u[0]])                          # 진행 방향의 왼쪽이 + 방향
    d = np.arange(-half_len, half_len + step / 2, step)
    pts = p0 + s * (p1 - p0) + d[:, None] * n
    res = xs[1] - xs[0]
    rc = np.vstack([(pts[:, 1] - ys[0]) / res, (pts[:, 0] - xs[0]) / res])
    z = map_coordinates(H, rc, order=1, cval=np.nan)     # 이중선형 보간 (NaN 칸 근처는 NaN)
    return d, z


def fwhm(d, z, level_frac=0.5, base_frac=0.15):
    """반높이 폭(level_frac=0.5). 바닥 = 양 끝 base_frac 구간의 중앙값,
    꼭대기 = 최댓값 근처(90 % 이상) 점들에 맞춘 포물선의 최고값
      (최댓값 하나만 쓰면 노이즈 때문에 높게 치우침. 평평한 윗면이든 뾰족한 봉우리든 동작).
    반환: 폭, 중심 위치(경로 이탈량, 왼쪽 +), 비드 높이(꼭대기−바닥)"""
    if np.any(~np.isfinite(z)):
        return np.nan, np.nan, np.nan
    k = max(2, int(len(z) * base_frac))
    base = np.median(np.r_[z[:k], z[-k:]])
    sel = z >= base + 0.9 * (z.max() - base)
    if sel.sum() >= 3:
        a2, a1, a0 = np.polyfit(d[sel], z[sel], 2)
        ds = d[sel]
        dv = np.clip(-a1 / (2 * a2), ds.min(), ds.max()) if a2 < 0 else ds[np.argmax(np.polyval([a2, a1, a0], ds))]
        top = np.polyval([a2, a1, a0], dv)
    else:
        top = z.max()
    half = base + level_frac * (top - base)
    above = np.where(z >= half)[0]
    i0, i1 = above[0], above[-1]
    # 왼쪽/오른쪽 교차점을 선형 보간으로 서브샘플 정밀도로
    xl = d[i0 - 1] + (half - z[i0 - 1]) * (d[i0] - d[i0 - 1]) / (z[i0] - z[i0 - 1])
    xr = d[i1] + (half - z[i1]) * (d[i1 + 1] - d[i1]) / (z[i1 + 1] - z[i1])
    return float(xr - xl), float(0.5 * (xl + xr)), float(top - base)
```

### 6.2 데모 `demo_h7.py` (원·폭·단차·평면도·비드)

```python
"""H7 데모: 원·폭·단차·평면도·비드 폭을 정답을 아는 합성 데이터로 확인."""
import numpy as np
from h7_dimensional import (fit_circle_kasa, fit_circle_geometric, roundness, width_between_edges,
                            step_height, flatness, cross_section, fwhm)

rng = np.random.default_rng(7)

# 1) 구멍 Ø6.000, 3엽(lobe) 변형 ±10 um, 노이즈 3 um, 전체 원주 600점
t = rng.uniform(0, 2 * np.pi, 600)
r = 3.0 + 0.010 * np.cos(3 * t) + rng.normal(0, 0.003, t.size)
P = np.column_stack([10 + r * np.cos(t), 20 + r * np.sin(t)])
(c1, r1), (c2, r2) = fit_circle_kasa(P), fit_circle_geometric(P)
print(f"[원 전체] 지름 Kåsa {2*r1:.4f}, 기하 {2*r2:.4f} mm (참 6.0000) | 원형도 {roundness(P, c2)*1000:.1f} um (형상 20 um + 노이즈)")

# 2) 90° 호만 보일 때 (가림), 노이즈 10 um → 대수적 맞춤의 치우침
t = rng.uniform(0, np.pi / 2, 200)
r = 3.0 + rng.normal(0, 0.010, t.size)
P = np.column_stack([r * np.cos(t), r * np.sin(t)])
(c1, r1), (c2, r2) = fit_circle_kasa(P), fit_circle_geometric(P)
print(f"[원 90° 호] 지름 Kåsa {2*r1:.4f}, 기하 {2*r2:.4f} mm (참 6.0000)")

# 3) 얇은 벽 폭 2.030 mm: 양쪽 경계 점 (노이즈 5 um)
y = np.linspace(0, 10, 300)
E1 = np.column_stack([0.0 + rng.normal(0, 0.005, y.size), y])
E2 = np.column_stack([2.030 + rng.normal(0, 0.005, y.size), y])
print(f"[폭] {width_between_edges(E1, E2):.4f} mm (참 2.0300)")

# 4) 단차: 아랫면 1.000, 윗면 1.400 (설계 0.4), 경계 흐림 + 노이즈 5 um
res = 0.02
xs = np.arange(0, 10, res); ys = np.arange(0, 6, res)
X, Y = np.meshgrid(xs, ys)
hi = X >= 5.0
H = np.where(hi, 1.400, 1.000) + rng.normal(0, 0.005, X.shape)
H[np.abs(X - 5.0) < 0.06] = 1.2 + rng.normal(0, 0.1, (np.abs(X - 5.0) < 0.06).sum())   # 경계 스파이크
dh, n_hi, n_lo = step_height(H, hi, ~hi, res, band_mm=0.25)
print(f"[단차] {dh*1000:.1f} um (설계 400, 참 400) — 윗면 {n_hi}칸, 아랫면 {n_lo}칸 사용")

# 5) 평면도: 15×15 mm 윗면, 0.05° 기울기 + 가운데 8 um 볼록 + 노이즈 5 um + 스파이크 1개
xs = np.arange(0, 15, res); ys = np.arange(0, 15, res)
X, Y = np.meshgrid(xs, ys)
H = 2.0 + np.tan(np.radians(0.05)) * X + 0.008 * np.exp(-((X - 7.5) ** 2 + (Y - 7.5) ** 2) / 2 / 3.0 ** 2)
H += rng.normal(0, 0.005, H.shape); H[100, 100] += 0.08
f = flatness(H, np.ones_like(H, bool), xs, ys)
print(f"[평면도] P-V {f['pv_um']:.1f} um, 강건 P-V {f['pv_robust_um']:.1f} um, 잔차 RMS {f['rms_um']:.2f} um, "
      f"기울기 {f['tilt_deg']:.4f}° (제거됨)")

# 6) 단일 비드: 30° 방향 경로. G2 기준 선폭 0.420, 실제 0.450 (h 0.2), 실제 중심은 왼쪽으로 +30 um 이탈
def bead_heightmap(X, Y, p0, p1, w, hb, off):
    """G2 단면(가운데 사각형 + 양옆 반원)을 위에서 본 높이맵. off = 경로 왼쪽(+)으로의 중심 이탈"""
    u = (p1 - p0) / np.linalg.norm(p1 - p0); nrm = np.array([-u[1], u[0]])
    a = np.abs((X - p0[0]) * nrm[0] + (Y - p0[1]) * nrm[1] - off)
    core = w / 2 - hb / 2
    Hb = np.where(a <= core, hb, hb / 2 + np.sqrt(np.clip((hb / 2) ** 2 - (a - core) ** 2, 0, None)))
    Hb[a > w / 2] = 0.0
    return Hb

p0, p1 = np.array([2.0, 2.0]), np.array([2.0 + 10 * np.cos(np.radians(30)), 2.0 + 10 * np.sin(np.radians(30))])
xs = np.arange(0, 14, res); ys = np.arange(0, 9, res)
X, Y = np.meshgrid(xs, ys)
H_ref = bead_heightmap(X, Y, p0, p1, w=0.420, hb=0.2, off=0.0)              # G3 기준 높이맵 (명목 선폭)
H_meas = bead_heightmap(X, Y, p0, p1, w=0.450, hb=0.2, off=0.030) + rng.normal(0, 0.003, X.shape)
S = np.linspace(0.1, 0.9, 20)                                                # 경로를 따라 단면 20개
for lf in (0.5, 0.25):
    Wm, Cm, Tm = np.array([fwhm(*cross_section(H_meas, xs, ys, p0, p1, s), level_frac=lf) for s in S]).T
    Wr, Cr, _ = np.array([fwhm(*cross_section(H_ref, xs, ys, p0, p1, s), level_frac=lf) for s in S]).T
    print(f"[비드 {int(lf*100)} % 높이 폭] 측정 {Wm.mean():.4f} ± {Wm.std(ddof=1):.4f}, 기준 {Wr.mean():.4f} mm "
          f"→ 폭 오차 {(Wm - Wr).mean()*1000:+.1f} um (참 +30.0), 경로 이탈 {(Cm - Cr).mean()*1000:+.1f} um (참 +30.0)")
```

```text
$ python3 demo_h7.py
[원 전체] 지름 Kåsa 5.9993, 기하 5.9993 mm (참 6.0000) | 원형도 31.8 um (형상 20 um + 노이즈)
[원 90° 호] 지름 Kåsa 5.9865, 기하 5.9955 mm (참 6.0000)
[폭] 2.0304 mm (참 2.0300)
[단차] 400.0 um (설계 400, 참 400) — 윗면 62376칸, 아랫면 62376칸 사용
[평면도] P-V 104.2 um, 강건 P-V 27.8 um, 잔차 RMS 5.40 um, 기울기 0.0501° (제거됨)
[비드 50 % 높이 폭] 측정 0.4406 ± 0.0048, 기준 0.4106 mm → 폭 오차 +30.1 um (참 +30.0), 경로 이탈 +30.1 um (참 +30.0)
[비드 25 % 높이 폭] 측정 0.4560 ± 0.0053, 기준 0.4260 mm → 폭 오차 +30.0 um (참 +30.0), 경로 이탈 +30.0 um (참 +30.0)
```

**결과 읽는 법**
- **원 전체**: 두 맞춤 모두 지름 5.9993 mm (참 6.0000). 원형도 31.8 µm 는 넣은 3엽 변형 20 µm 에 노이즈(3 µm, 600점)가 더해진 값 → 노이즈 바닥값을 함께 보고해야 하는 이유.
- **90° 호**: Kåsa 는 지름을 13.5 µm 작게, 기하학적 맞춤은 4.5 µm 작게 냅니다. 가림으로 호가 잘리는 구멍에서는 반드시 기하학적 맞춤을 씁니다.
- **단차**: 경계 스파이크(±100 µm)를 넣었는데도 경계 0.25 mm 제외 + 중앙값으로 400.0 µm 를 정확히 얻었습니다.
- **평면도**: 스파이크 하나(80 µm)로 P-V 가 104 µm 가 되었지만, 강건 P-V 는 28 µm(볼록 8 µm + 노이즈 범위)입니다. 기울기 0.05° 는 평면 맞춤으로 제거되었습니다.
- **비드**: 측정 FWHM 0.4406 mm 를 명목 0.45 와 비교하면 −9 µm 처럼 보이지만, 같은 방법으로 처리한 기준 모델(명목 0.42 mm → FWHM 0.4106 mm)과 비교하면 **폭 오차 +30.1 µm**(참 +30 µm)로 정확합니다. 경로 이탈 +30.1 µm 도 정확합니다.

### 6.3 단위 테스트 `test_h7.py`

```python
"""H7 단위 테스트. 실행: pytest -q test_h7.py"""
import numpy as np
from h7_dimensional import fit_circle_kasa, fit_circle_geometric, roundness, fwhm, step_height


def test_완전한_원():
    t = np.linspace(0, 2 * np.pi, 50, endpoint=False)
    P = np.column_stack([1 + 2.5 * np.cos(t), -3 + 2.5 * np.sin(t)])
    for c, r in (fit_circle_kasa(P), fit_circle_geometric(P)):
        assert np.allclose(c, [1, -3]) and abs(r - 2.5) < 1e-9
    assert roundness(P, np.array([1, -3])) < 1e-9


def test_가우시안_FWHM은_2점3548_시그마():
    d = np.linspace(-1, 1, 2001)
    z = np.exp(-d ** 2 / (2 * 0.1 ** 2))
    w, c, h = fwhm(d, z)
    assert abs(w - 2.3548 * 0.1) < 1e-4 and abs(c) < 1e-9 and abs(h - 1) < 1e-3


def test_단차():
    H = np.zeros((100, 100)); H[:, 50:] = 0.4
    hi = np.zeros_like(H, bool); hi[:, 50:] = True
    dh, _, _ = step_height(H, hi, ~hi, res=0.02)
    assert abs(dh - 0.4) < 1e-12
```

```text
$ python3 -m pytest -q test_h7.py
3 passed in 0.xxs
```

### 6.4 보조 데모 `demo_h7_pins.py` — 위치 오차 화살표 지도

같은 폴더에 H4 문서의 `h4_registration.py` 가 있어야 합니다. 그림은 파일로만 저장합니다 (`matplotlib.use("Agg")`).

```python
"""H7 보조 데모: 핀 격자(5×5, 간격 20 mm) 위치 오차 화살표 지도.
H4 의 kabsch(닮음)로 배율·회전을 뺀 뒤 남는 패턴(예: X·Y 축 직각도 오차)을 본다."""
import numpy as np
import matplotlib
matplotlib.use("Agg")                                    # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt
from h4_registration import kabsch, apply

rng = np.random.default_rng(12)
gx, gy = np.meshgrid(np.arange(5) * 20.0 + 60, np.arange(5) * 20.0 + 60)    # 베드 중앙 80 mm 영역
design = np.column_stack([gx.ravel(), gy.ravel()])
c = design.mean(axis=0)
# 정답: 배율 0.996 (수축) + X·Y 축 직각도 오차 0.05° (y 가 클수록 x 가 밀림) + 이동 + 핀 중심 측정 노이즈 3 um
skew = np.tan(np.radians(0.05))
actual = c + 0.996 * (design - c)
actual[:, 0] += skew * (design[:, 1] - c[1])
actual += [0.08, -0.03] + rng.normal(0, 0.003, actual.shape)

err = actual - design                                    # {G} 기준 위치 오차 벡터 [mm]
R, t, s = kabsch(design, actual, with_scale=True)        # 전체 이동·회전·배율 성분
resid = actual - apply(R, t, s, design)                  # 남는 국소 패턴
print(f"위치 오차 크기: 평균 {np.linalg.norm(err, axis=1).mean()*1000:.1f} um, 최대 {np.linalg.norm(err, axis=1).max()*1000:.1f} um")
print(f"닮음 성분: 배율 {s:.5f} (참 0.99600), 회전 {np.degrees(np.arctan2(R[1,0], R[0,0])):+.4f}°")
print(f"닮음 제거 후 잔차: RMS {np.sqrt((resid**2).sum(1).mean())*1000:.1f} um, 최대 {np.linalg.norm(resid, axis=1).max()*1000:.1f} um")
# 잔차의 '직각도' 성분: x 잔차를 y 에 대해 회귀한 기울기의 두 배가 전단(직각도) 각도에 해당 (회전 성분이 절반을 가져감)
slope = np.polyfit(design[:, 1] - c[1], resid[:, 0], 1)[0]
print(f"잔차 x-y 기울기 {slope*1e6:.0f} um/m → 직각도 오차 추정 {np.degrees(2*slope):.4f}° (참 0.0500°)")

fig, ax = plt.subplots(1, 2, figsize=(9, 4.2))
for a, v, title in [(ax[0], err, "position error (x500)"), (ax[1], resid, "residual after similarity (x2000)")]:
    k = 500 if a is ax[0] else 2000
    a.quiver(design[:, 0], design[:, 1], v[:, 0] * k, v[:, 1] * k, angles="xy", scale_units="xy", scale=1)
    a.set_aspect("equal"); a.set_xlabel("X [mm]"); a.set_ylabel("Y [mm]"); a.set_title(title)            # 한글 제목은 한글 글꼴 설정 후 (J4)
fig.tight_layout(); fig.savefig("S00_r01_H7_position_map.png", dpi=150)
print("그림 저장: S00_r01_H7_position_map.png")
```

```text
$ python3 demo_h7_pins.py
위치 오차 크기: 평균 167.9 um, 최대 336.2 um
닮음 성분: 배율 0.99598 (참 0.99600), 회전 -0.0251°
닮음 제거 후 잔차: RMS 18.0 um, 최대 26.5 um
잔차 x-y 기울기 442 um/m → 직각도 오차 추정 0.0506° (참 0.0500°)
그림 저장: S00_r01_H7_position_map.png
```

- 위치 오차 자체는 최대 336 µm 로 크지만 대부분 **배율(수축)** 성분입니다. 닮음 변환을 빼면 잔차 RMS 18 µm 가 남고, 그 무늬에서 X·Y 직각도 오차 0.0506° (참 0.05°)를 읽어낼 수 있습니다.
- 닮음 맞춤이 직각도 오차의 절반을 "회전"(−0.025°)으로 가져가므로, 잔차 기울기의 2배가 직각도입니다.

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 원 지름 (합성, 전체 원) | 6.2 데모 | \|오차\| ≤ 1 µm |
| 원 지름 (합성, 90° 호) | 6.2 데모, 기하학적 맞춤 | \|오차\| ≤ 10 µm (Kåsa 와의 차이 기록) |
| 폭·단차 (합성) | 6.2 데모 | \|오차\| ≤ 1 µm |
| 비드 폭 오차 복원 (합성) | 기준 모델 대비 | \|복원 − 참\| ≤ 2 µm, 경로 이탈 ≤ 2 µm |
| 직각도 복원 (합성) | 6.4 데모 | ≤ 0.005° |
| 단위 테스트 | `pytest test_h7.py` | 전부 통과 |
| 실측 단차 (M2/D5 연계) | 게이지 블록 1, 2 mm 단차 | 오차 < 10 µm |
| 실측 구 지름 (D5 연계) | 인증 세라믹 구 | 지름 오차 < 15 µm |
| 실측 반복성 | 같은 시편 3회 | 지름·폭 표준편차 ≤ 5 µm, 단차 ≤ 3 µm |
| 교차검증 (I3) | 마이크로미터·현미경 | 단차·폭 차이 ≤ 20 µm (차이는 Bland–Altman 으로 보고) |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 대수적(Kåsa) 결과만 사용 | 가려진 구멍 지름이 체계적으로 작음 | 기하학적 맞춤까지 수행 |
| 원형도를 노이즈 바닥 없이 보고 | 완벽한 구멍도 원형도 20 µm 로 보임 | 핀 게이지로 노이즈 바닥 측정·병기 |
| 단차를 평균으로 계산 | 경계 스파이크에 따라 수 µm 흔들림 | 중앙값 + 경계 띠 제외 |
| 평면도를 P-V 하나로 | 먼지 하나로 평면도가 수 배 | 강건 P-V·RMS 병기 |
| FWHM 을 명목 폭과 직접 비교 | 모든 비드가 10 µm 가늘다는 잘못된 결론 | 같은 처리를 거친 기준 모델 FWHM 과 비교 |
| 꼭대기를 최댓값 한 점으로 | 노이즈만큼 반높이가 올라가 폭이 좁아짐 | 포물선 꼭대기 (코드에 포함) |
| 단면을 경로 시작·끝 근처에서 추출 | 압출 시작 뭉침으로 폭이 큼 | 양 끝 1 mm 제외 |
| 경로 이탈 부호를 형상마다 다르게 | 방향별 비교 불가 | 진행 방향 왼쪽 + 로 통일 |
| 위치 화살표에 배율 미표시 | µm 오차가 mm 처럼 보임 | 그림 제목에 "x500" 처럼 표기 |
| 위치 오차와 배율을 섞어 해석 | 수축을 "가장자리 위치 오차"로 오해 | 닮음 성분 분리 후 잔차 지도 |

---

## 9. 위험 요소

- **가림(E2)**: 원기둥·구멍의 카메라 반대쪽 경계가 잘려 원 맞춤이 호 일부에만 의존할 수 있습니다. 구멍은 특히 안쪽 벽이 보이지 않아 위쪽 가장자리만 측정됩니다 → "구멍 지름 = 윗면 가장자리 지름"으로 정의를 명시합니다.
- **경계 정의 의존성**: 지름·폭은 H6 의 문턱 규칙에 따라 수십 µm 달라질 수 있습니다(H6 6.2). 같은 규칙을 모든 시편에 적용하고, 절대값은 I3 교차검증으로 확인합니다.
- **얇은 형상의 샘플링 부족**: 0.4 mm 비드는 0.02 mm 격자에서 20칸, 반원 옆면은 각 5칸입니다(A2 의 "5~10점" 규칙의 하한 근처). 폭 반복성이 나쁘면 격자·스캔 간격을 줄이는 것을 검토합니다.
- **반투명 재료(E1)**: 빛이 퍼져 비드 단면이 넓고 낮게 측정됩니다. 폭 오차가 재료 탓일 수 있으므로 E1 실험 결과와 함께 해석합니다.

---

## 10. 기록 양식

`_H7_dimensions.csv` 열
```text
scan_id,specimen_id,feature_id,feature_type,design_value_mm,measured_mm,error_um,error_pct,aux_name,aux_value,n_points,method,level_rule,flag
```
예: `S03_r02,S03,H6mm,hole,6.000,5.987,-13.0,-0.217,roundness_lsc_um,24.1,812,geometric,Z-h/2,OK`

`_H7_bead_sections.csv` 열
```text
scan_id,track_id,track_angle_deg,s,fwhm_meas_mm,fwhm_ref_nominal_mm,fwhm_ref_extrusion_mm,width_err_nominal_um,width_err_extrusion_um,path_dev_um,bead_height_mm,fw25_meas_mm,fw25_ref_mm
```

노이즈 바닥 기록표

| 날짜 | 기준물 | 인증 지름 mm | 측정 지름 mm | 원형도(LSC) µm | 평면도 강건 P-V µm | 비고 |
|---|---|---|---|---|---|---|
| | 핀 게이지 Ø6 | | | | – | |
| | 광학 평판 | – | – | – | | |

---

## 11. 참고 자료

- Kåsa, I. (1976). A circle fitting procedure and its error analysis. *IEEE Transactions on Instrumentation and Measurement*, IM-25(1).
- Chernov, N. (2010). *Circular and Linear Regression: Fitting Circles and Lines by Least Squares*. CRC Press.
- ISO 1101 (기하공차: 진원도·평면도 정의), ISO 12181 (진원도), ISO 12781 (평면도)
- SciPy 문서: `scipy.optimize.least_squares`, `scipy.ndimage.map_coordinates`, `scipy.ndimage.binary_erosion`; matplotlib 문서: `Axes.quiver`
- NIST 적층제조 표준 시편(AM Test Artifact) 관련 공개 자료 — 형상별 측정 항목 참고 (E3)
- 청사진 관련 절: [BLUEPRINT](../../BLUEPRINT.md) H7, G2, E2, E3, I3, J4
