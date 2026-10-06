# F1. 레이저 라인 중심 추출 (서브픽셀)

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: F. 데이터 획득

| 항목 | 내용 |
|---|---|
| 기간 | 2026-11-17 ~ 2026-11-30 (W7-8) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [B1 삼각측량 원리](../B-optics/B1-triangulation-principle.md) · [B4 카메라](../B-optics/B4-camera.md) · [B6 레이저 광원](../B-optics/B6-laser.md) · [J1 소프트웨어 구조](../J-software/J1-software-structure.md) |
| 후행 요소 | [D2 레이저 평면 캘리브레이션](../D-calibration/D2-laser-plane.md) · [F2 획득 파라미터](F2-acquisition-params.md) · [H2 이상치·노이즈 처리](../H-analysis/H2-outliers.md) · [I2 MSA](../I-reliability/I2-msa.md) · [J3 합성 데이터 테스트](../J-software/J3-synthetic-tests.md) |
| 관련 마일스톤 | M1 (재투영 < 0.2 px, 평면 잔차 < 5 µm — 레이저 평면 잔차는 F1 정밀도에 직접 의존) |

---

## 1. 목적

카메라 이미지의 **각 열(u)마다 레이저 선의 중심 행 위치(v)를 1픽셀보다 정밀하게(서브픽셀)** 찾는 코드를 만들고, 그 정밀도를 **정답을 아는 합성 이미지**와 **정지 평판 반복 촬영**으로 숫자로 증명합니다.

- 이 요소의 출력 `v(u)` 는 D2(레이저 평면)에서 3D 점으로 바뀌므로, 여기서 생긴 오차는 **그대로 높이 오차**가 됩니다.
- B1 계산 예(δz = 27.6 µm/px)에서 A2 목표 Z 반복성 5 µm 를 얻으려면 중심 추출의 반복성이 **약 0.18 px 이하**여야 합니다 (5 / 27.6 ≈ 0.18).
- 이 요소가 끝나면: ① 방법 선택(권장: **무게중심 CoG**), ② 파라미터(threshold, half_win, guide_band) 확정, ③ 점마다 **신뢰도 정보(피크 밝기, 선 폭, 포화 픽셀 수)** 를 함께 내보내는 함수가 준비되어 있어야 합니다.

## 2. 배경 지식 (초보자용)

**이미지는 숫자 표입니다.** 흑백 카메라 이미지는 `img[v, u]` 처럼 행(v, 세로)과 열(u, 가로)로 접근하는 2차원 배열이고, 각 칸의 값이 밝기(8-bit면 0~255, 12-bit면 0~4095, 단위 DN = Digital Number)입니다.

**레이저 선의 단면.** 한 열(u)을 위에서 아래로 읽으면 밝기가 종 모양(가우시안)으로 솟았다가 내려갑니다. 이 종의 **가운데**가 우리가 찾는 v 입니다.

```
밝기
 200 |        ██
 150 |      ██████
 100 |     ████████
  50 |   ████████████
   8 |▁▁▁████████████▁▁▁   ← 배경(bg)
     +------------------- 행 v
          ↑ 중심은 두 픽셀 사이(예: 100.37)일 수 있다
```

**서브픽셀이 왜 가능한가?** 종 모양이 3~7픽셀에 걸쳐 퍼져 있으면, 양옆 픽셀의 밝기 비율을 보고 중심이 픽셀 사이 어디쯤인지 계산할 수 있습니다. 그래서 선이 **너무 얇아도(1~2 px) 너무 두꺼워도(> 10 px) 불리합니다** (B6: 3~7 px 권장).

**방법 4가지 (+1)**

| 방법 | 계산 | 직관 |
|---|---|---|
| 최대 픽셀 | `argmax` | 가장 밝은 칸의 번호. 항상 정수 → 1 px 단위 계단 |
| 무게중심(CoG) | `Σ v·w / Σ w`, w = 밝기 − 문턱값 | 시소의 균형점. 여러 픽셀을 써서 노이즈가 평균됨 |
| 포물선 3점 | 피크와 위·아래 1칸에 포물선 | 꼭짓점 위치 = 중심 |
| 가우시안 3점 | 밝기에 log 를 씌운 뒤 포물선 | 가우시안의 log 는 정확히 포물선 → 노이즈가 없으면 정확 |
| Steger(1998) | 2차 미분(헤시안)이 가장 음수인 방향에서 1차 미분 = 0 인 점 | 선의 "능선"을 미분으로 찾음. 곡선·잡음에 강함 |

**가우시안 3점 공식** (a, b, c = 피크 위·피크·아래 픽셀의 배경 뺀 밝기, p = 피크 행)

```
δ = ( ln a − ln c ) / ( 2 · (ln a − 2 ln b + ln c) )
v = p + δ            (δ 는 −0.5 ~ +0.5 사이여야 정상)
```

**포화(saturation)** 는 밝기가 센서 최댓값(255)에 닿아 잘린 상태입니다. 종의 꼭대기가 평평해지므로 **3점 방법은 크게 틀리고**, 밝기 정보가 사라져 신뢰도 판단도 어려워집니다. 그래서 BLUEPRINT 규칙은 "최대 밝기 ≤ 센서 최댓값의 90 %" 입니다.

**반사(가짜 피크)** 는 광택면이나 주변 벽에서 튄 빛이 같은 열의 다른 행에 또 하나의 밝은 점을 만드는 현상입니다. 그 열에서 가짜가 더 밝으면 `argmax` 가 가짜를 고릅니다. 이웃 열과 이어지는 쪽을 고르는 **연속성 안내(guide)** 가 필요합니다.

**벡터화.** Python의 `for` 문으로 1440개 열을 하나씩 처리하면 느립니다. numpy는 "모든 열을 한꺼번에" 계산하는 배열 연산을 제공합니다. 이 문서의 코드는 `for u in range(W)` 없이 작성되어 1080×1440 이미지 한 장을 수 ms 안에 처리합니다 (100 fps 예산 = 10 ms/장, B4).

**픽셀 → 높이 환산.** B1 배치(M = 0.25, θ = 30°, p = 3.45 µm)에서 1 px = 27.6 µm 높이입니다. 즉 **0.1 px 오차 = 2.8 µm 높이 오차**입니다. 이 문서의 모든 px 결과에 27.6 을 곱하면 µm 로 바뀝니다 (배치가 바뀌면 B1 공식으로 다시 계산).

## 3. 입력과 산출물

| 구분 | 이름 | 형식 · 파일 | 설명 |
|---|---|---|---|
| 입력 | 레이저 이미지 | `uint8`/`uint16` 배열 (H, W), 개발 중에는 `data/raw/<scan_id>/frames/000000.png` | 모노크롬, 대역통과 필터 장착 상태 (B7) |
| 입력 | 배경 이미지(선택) | 레이저 끈 상태 평균 이미지 `.npy` | C5 배경 차감용 |
| 입력 | 파라미터 | `config/default.yaml` 의 `line_extraction:` 블록 | threshold, half_win, guide_band, method |
| 산출물 | 추출 모듈 | `src/cvlab/triangulation.py` (함수 `extract_cog`, `extract_gauss3`, `extract_steger1d`, `find_peak_rows`, `line_quality`) | 6절 코드 |
| 산출물 | 단위 테스트 | `tests/test_line_extraction.py` | pytest 5개 이상 통과 |
| 산출물 | 방법 비교표 | `results/F1/method_comparison.csv` | 시나리오 × 방법 × (유효%, bias, std, RMS, P95) |
| 산출물 | 반복성 결과 | `results/F1/repeatability_<date>.csv` | 정지 평판 100장, 열별 std |
| 산출물 | 프레임별 출력(후속 단계로 전달) | 프레임마다 `v`(float32, NaN=검출 실패), `peak`(uint16), `width`(float32) → F3 의 `<scan_id>_profiles.npz` | 신뢰도 정보 포함 |
| 산출물 | 결정 기록 | `docs/decisions/F1-method.md` 또는 실험노트 1쪽 | 선택한 방법과 근거 수치 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 기본 중심 추출 방법 | 최대 픽셀 / CoG / 포물선·가우시안 3점 / Steger | **CoG** (비교·검증용으로 Steger 1D 유지) | 합성 실험에서 RMS 0.073 px (3점 방법 0.19 px), 포화에도 치우침 없음, 1080×1440 한 장 약 4 ms |
| CoG 창 크기 `half_win` | 3 / 5 / 7 px | **≈ 1.5 × 선 두께(FWHM)**, FWHM 3.5 px이면 5 | 창이 작으면 꼬리를 잘라 치우침, 크면 노이즈·반사 섞임 |
| 문턱값 `threshold` | 고정 DN / 배경 + k·σ | **배경 중앙값 + 5·σ_배경** (8-bit 에서 보통 20~40 DN) | 배경 노이즈가 가중치에 섞이면 중심이 창 가운데로 끌려감 |
| 반사 대응 | 없음 / 연속성 안내 / 동적계획법 경로 | **연속성 안내 (guide_win = 51 열, guide_band = 8 px)** | 21열짜리 반사에서 RMS 6.9 px → 0.07 px. 구현이 간단 |
| 신뢰도 필터 | 없음 / 피크·폭·포화 기준 | **피크 < 3·threshold, 폭 > 2 × 정상폭, 포화 픽셀 ≥ 1 이면 저신뢰 표시** | 반투명·반사·포화 점을 H2 에서 제거하기 위해 (값은 저장하고 표시만) |
| 배경 차감 | 안 함 / 레이저 끈 평균 이미지 빼기 | 주변광 비율(C5)이 2 % 넘으면 차감 | 균일하지 않은 주변광은 CoG 를 치우치게 함 |
| 출력 자료형 | float64 / float32 | **float32** (NaN = 검출 실패) | 0.001 px 정밀도로 충분, 용량 절반 |
| 이미지 비트 깊이 | 8 / 10·12-bit | 가능하면 **12-bit (Mono12)** | 양자화 노이즈 감소, 저신호에서 유리 (B4) |

## 5. 수행 절차

1. **환경 준비 (W7 월, 0.5일)**
   - [ ] `src/cvlab/triangulation.py`, `tests/test_line_extraction.py` 파일 생성 (J1 구조)
   - [ ] 6.1 코드를 붙여 넣고 `python line_extraction.py` 실행 → 6.2 기대 출력과 비교 (숫자가 ±10 % 안이면 정상, 난수·PC 차이)
2. **합성 데이터로 방법 비교 (W7 월~화, 1.5일)**
   - [ ] 시나리오 5개(기본, 저신호 50 DN, 포화 400 DN, 스펙클 10 %, 반사) × 방법 5개 × 20장 실행
   - [ ] 결과를 `results/F1/method_comparison.csv` 로 저장 (`pandas.DataFrame.to_csv`)
   - [ ] 선 두께 σ = 0.8, 1.5, 3.0 px 로 바꿔 CoG·가우시안 3점 RMS 가 어떻게 변하는지 추가 확인 (얇은 선에서 3점 방법이 상대적으로 좋아지는지)
3. **파라미터 결정 (W7 수, 1일)**
   - [ ] `half_win` 3, 4, 5, 7 에 대해 기본 시나리오 RMS 비교 → 최소가 되는 값 선택
   - [ ] `threshold` 를 배경 + 3σ, 5σ, 8σ 로 바꿔 저신호 시나리오 RMS 와 유효 % 비교
   - [ ] 결정값을 `config/default.yaml` 에 기록
4. **단위 테스트 (W7 목, 0.5일)**
   - [ ] 6.3 의 pytest 5개 통과 (`python -m pytest -q tests/test_line_extraction.py`)
   - [ ] 경계 사례 추가: 이미지 맨 위/맨 아래 행에 레이저가 걸린 경우 NaN 또는 정상값이 나오는지
5. **실제 이미지 첫 적용 (W7 금 ~ W8 월, 1.5일)** — D1 캘리브레이션과 같은 주에 카메라가 준비됨
   - [ ] 평판(석정반 또는 게이지 블록 윗면) 위 레이저 선 이미지 10장 촬영, 노출은 피크 60~85 % (F2)
   - [ ] 추출 결과 `v(u)` 를 이미지 위에 빨간 점으로 겹쳐 그려서 눈으로 확인 (`matplotlib`, `savefig`)
   - [ ] 열별 `width` 히스토그램 → 정상 폭(중앙값) 기록. 이 값의 2배를 "두꺼운 선" 기준으로 사용
6. **반복성 측정 (W8 화, 1일)**
   - [ ] 장비 30분 워밍업 (C6), 평판 고정, 같은 설정으로 **100장** 연속 촬영
   - [ ] 6.4 코드로 열별 표준편차 → 중앙값·95 % 값 계산, µm 로 환산해서 기록 (10절 양식)
   - [ ] 시간 순서대로 열 평균 v 를 그려서 드리프트(서서히 움직임)가 있는지 확인 → 있으면 C6/C7 문제로 기록
7. **반사·저신뢰 처리 확인 (W8 수, 1일)**
   - [ ] 금속 공구나 광택 테이프를 FOV 가장자리에 두어 반사 피크를 일부러 만들고, `guide_band` 켠/끈 결과 비교
   - [ ] 저신뢰 점 비율(%)을 기록 (H2 에서 제거 비율의 출발값)
8. **속도 확인과 마무리 (W8 목~금, 1.5일)**
   - [ ] 실제 해상도 1장 처리 시간 측정 → 10 ms 이하인지 (100 fps 실시간 처리 시). 실시간이 아니면 촬영 후 일괄 처리로 결정해도 됨
   - [ ] 결정 기록 1쪽 작성 (방법, 파라미터, 합성·실측 수치)
   - [ ] D2 담당자에게 함수 사용법 전달 (입력·출력·NaN 의미)

## 6. Python 구현

### 6.1 추출 모듈 + 방법 비교 실행 (`line_extraction.py`)

정답 v 를 알고 만든 합성 이미지로 5가지 방법을 비교합니다. 실제 프로젝트에서는 함수 부분만 `src/cvlab/triangulation.py` 에 옮기고, `if __name__ == "__main__":` 아래 실험 부분은 `scripts/` 나 노트북에서 실행합니다.

```python
"""
line_extraction.py — 레이저 라인 중심 추출 (F1)
최종 위치(권장): src/cvlab/triangulation.py 의 일부

이미지 규칙: img[v, u]  (행 = v = 세로, 열 = u = 가로)
레이저 선은 대체로 가로 방향 → 열(u)마다 중심 행(v)을 하나 찾는다.
"""
import time
import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.special import erf


# ---------------------------------------------------------------------------
# 1) 정답을 아는 합성 레이저 이미지 만들기
# ---------------------------------------------------------------------------
def make_truth(W=400, base=100.0):
    """열마다 레이저 중심의 '정답' 행 위치 (완만한 곡선 + 15 px 단차)"""
    u = np.arange(W)
    v = base + 20.0 * np.sin(2 * np.pi * u / W)
    v[250:320] += 15.0                      # 시편 윗면 같은 단차
    return v


def synth_laser_image(v_true, H=200, amp=180.0, sigma=1.5, bg=8.0,
                      read_noise=2.0, shot=True, max_dn=255,
                      speckle=0.0, reflection=None, rng=None):
    """
    v_true     : (W,) 열마다 정답 중심 [px]
    amp        : 피크 밝기 [DN]. max_dn 을 넘으면 포화(잘림)
    sigma      : 가우시안 폭 [px]. 선 두께(FWHM) = 2.355*sigma
    speckle    : 스펙클 곱셈 노이즈 대비(0이면 없음, 0.1 = 10 %)
    reflection : (u0, u1, dv, 배율) → u0~u1 열에 v_true+dv 위치로 가짜 반사 피크
    반환: uint8 또는 uint16 이미지 (H, W)
    """
    rng = np.random.default_rng(rng)
    W = v_true.size
    edges = np.arange(H + 1)[:, None] - 0.5          # 픽셀 경계 (H+1, 1)

    def gauss_pixels(center, a):
        # 픽셀 면적에 대해 적분한 가우시안 (실제 센서처럼 픽셀 평균값)
        z = (edges - center[None, :]) / (np.sqrt(2) * sigma)
        cdf = 0.5 * (1 + erf(z))
        return a * (cdf[1:] - cdf[:-1]) * np.sqrt(2 * np.pi) * sigma

    img = bg + gauss_pixels(v_true, amp)
    if reflection is not None:
        u0, u1, dv, k = reflection
        refl = np.zeros_like(img)
        refl[:, u0:u1] = gauss_pixels(v_true + dv, amp * k)[:, u0:u1]
        img = img + refl
    if speckle > 0:                                  # 고정 패턴(정지 상태면 매번 같음)
        img = bg + (img - bg) * rng.normal(1.0, speckle, img.shape).clip(0.2)
    if shot:                                         # 광자 산탄 노이즈 (근사)
        img = img + rng.normal(0, 1, img.shape) * np.sqrt(np.maximum(img, 0))
    img = img + rng.normal(0, read_noise, img.shape)  # 읽기 노이즈
    img = np.clip(np.round(img), 0, max_dn)          # 양자화 + 포화
    return img.astype(np.uint8 if max_dn <= 255 else np.uint16)


# ---------------------------------------------------------------------------
# 2) 피크(대략 위치) 찾기 — 반사 대비 '연속성 안내' 포함
# ---------------------------------------------------------------------------
def find_peak_rows(img, guide_band=None, guide_win=51):
    """
    열마다 가장 밝은 행 번호(정수)를 반환.
    guide_band(px)를 주면: 1차 argmax 를 열 방향 중앙값 필터로 매끄럽게 만든 '안내선'
    ±guide_band 안에서만 다시 최대값을 찾는다 → 짧은 반사 피크 무시.
    """
    f = img.astype(np.float32)
    p = f.argmax(axis=0)
    if guide_band is None:
        return p
    guide = median_filter(p.astype(np.float32), size=guide_win, mode="nearest")
    rows = np.arange(f.shape[0])[:, None]
    outside = np.abs(rows - guide[None, :]) > guide_band
    f = np.where(outside, -1.0, f)
    return f.argmax(axis=0)


def _take(f, rows):
    """f[rows[u], u] 를 열마다 한 번에 꺼내기 (rows 는 범위 안으로 잘라서 사용)"""
    r = np.clip(rows, 0, f.shape[0] - 1)
    return f[r, np.arange(f.shape[1])]


# ---------------------------------------------------------------------------
# 3) 중심 추출 방법 4+1가지 (모두 벡터화: for 문 없음)
# ---------------------------------------------------------------------------
def extract_max(img, threshold=30, **kw):
    """최대 밝기 픽셀 (정수 위치) — 비교용"""
    f = img.astype(np.float32)
    p = find_peak_rows(img, **kw)
    v = p.astype(np.float64)
    v[_take(f, p) <= threshold] = np.nan
    return v


def extract_cog(img, threshold=30, half_win=5, **kw):
    """무게중심(CoG): 피크 ±half_win 창, (밝기 − threshold) 를 가중치로 사용"""
    f = img.astype(np.float32)
    H, W = f.shape
    p = find_peak_rows(img, **kw)
    offs = np.arange(-half_win, half_win + 1)[:, None]      # (2k+1, 1)
    rows = p[None, :] + offs                                 # (2k+1, W)
    valid_row = (rows >= 0) & (rows < H)
    vals = f[np.clip(rows, 0, H - 1), np.arange(W)[None, :]]
    w = np.where(valid_row, np.maximum(vals - threshold, 0), 0)
    s = w.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (w * rows).sum(axis=0) / s
    v[(s <= 0) | (_take(f, p) <= threshold)] = np.nan
    return v


def extract_parabola3(img, threshold=30, **kw):
    """포물선 3점 맞춤: 피크와 위·아래 이웃 1픽셀"""
    f = img.astype(np.float64)
    p = find_peak_rows(img, **kw)
    a, b, c = _take(f, p - 1), _take(f, p), _take(f, p + 1)
    den = a - 2 * b + c
    with np.errstate(invalid="ignore", divide="ignore"):
        d = 0.5 * (a - c) / den
    v = p + d
    bad = (b <= threshold) | (den >= 0) | (np.abs(d) > 1) | (p == 0) | (p == f.shape[0] - 1)
    v[bad] = np.nan
    return v


def extract_gauss3(img, threshold=30, bg=None, **kw):
    """가우시안 3점 맞춤: 밝기에 로그를 취한 뒤 포물선 맞춤 (가우시안이면 정확)"""
    f = img.astype(np.float64)
    if bg is None:
        bg = np.median(f, axis=0)                 # 열마다 배경 밝기 추정
    g = np.maximum(f - bg, 0.5)                   # log(0) 방지
    p = find_peak_rows(img, **kw)
    la, lb, lc = np.log(_take(g, p - 1)), np.log(_take(g, p)), np.log(_take(g, p + 1))
    den = la - 2 * lb + lc
    with np.errstate(invalid="ignore", divide="ignore"):
        d = 0.5 * (la - lc) / den
    v = p + d
    bad = (_take(f, p) <= threshold) | (den >= 0) | (np.abs(d) > 1) | (p == 0) | (p == f.shape[0] - 1)
    v[bad] = np.nan
    return v


def extract_steger1d(img, threshold=30, sigma_s=1.5, **kw):
    """
    Steger 방법의 1차원 단순화: 가우시안 미분 필터로 r'(v), r''(v) 를 구하고
    r'(v)=0 이 되는 서브픽셀 위치 t = -r'/r'' 를 피크 근처에서 계산.
    (원래 Steger 는 2D 헤시안의 고유벡터 방향으로 계산 → 선이 많이 기울면 그쪽이 정확)
    """
    f = img.astype(np.float64)
    g0 = gaussian_filter1d(f, sigma_s, axis=0, order=0)
    g1 = gaussian_filter1d(f, sigma_s, axis=0, order=1)
    g2 = gaussian_filter1d(f, sigma_s, axis=0, order=2)
    p = find_peak_rows(g0, **kw)                 # 매끄럽게 한 이미지에서 피크
    d1, d2 = _take(g1, p), _take(g2, p)
    with np.errstate(invalid="ignore", divide="ignore"):
        t = -d1 / d2
    v = p + t
    v[(_take(f, p) <= threshold) | (d2 >= 0) | (np.abs(t) > 1)] = np.nan
    return v


def line_quality(img, v, max_dn=255):
    """점마다 신뢰도 정보: 피크 밝기, 반높이 폭(FWHM, px), 포화 픽셀 수"""
    f = img.astype(np.float32)
    peak = f.max(axis=0)
    bg = np.median(f, axis=0)
    half = bg + (peak - bg) / 2
    width = (f >= half[None, :]).sum(axis=0).astype(np.float32)   # 대략적 FWHM
    n_sat = (f >= max_dn).sum(axis=0)
    return {"peak": peak, "width": width, "n_sat": n_sat}


METHODS = {
    "max": extract_max,
    "cog": extract_cog,
    "parabola3": extract_parabola3,
    "gauss3": extract_gauss3,
    "steger1d": extract_steger1d,
}


def error_stats(v_est, v_true):
    e = v_est - v_true
    ok = ~np.isnan(e)
    e = e[ok]
    return {
        "valid%": 100 * ok.mean(),
        "bias": e.mean(),
        "std": e.std(ddof=1),
        "rms": np.sqrt((e ** 2).mean()),
        "p95": np.percentile(np.abs(e), 95),
    }


# ---------------------------------------------------------------------------
# 4) 실행: 시나리오별 비교표
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    v_true = make_truth()
    scenarios = {
        "기본(피크180)": dict(amp=180),
        "저신호(피크50)": dict(amp=50),
        "포화(피크400)": dict(amp=400),
        "스펙클10%": dict(amp=180, speckle=0.10),
        "반사피크": dict(amp=180, reflection=(60, 81, 30, 1.3)),
    }
    print(f"{'시나리오':<14}{'방법':<10}{'유효%':>7}{'bias':>8}{'std':>8}{'RMS':>8}{'P95':>8}   [px]")
    for name, kw in scenarios.items():
        errs = {m: [] for m in METHODS}
        for seed in range(20):                       # 20장 평균 통계
            img = synth_laser_image(v_true, rng=seed, **kw)
            for m, fn in METHODS.items():
                errs[m].append(fn(img, threshold=30) - v_true)
        for m in METHODS:
            e = np.concatenate(errs[m])
            s = error_stats(e, np.zeros_like(e))
            print(f"{name:<14}{m:<10}{s['valid%']:7.1f}{s['bias']:8.3f}{s['std']:8.3f}"
                  f"{s['rms']:8.3f}{s['p95']:8.3f}")
        print()

    # 반사 시나리오: 연속성 안내(guide_band) 를 켜면?
    img = synth_laser_image(v_true, amp=180, reflection=(60, 81, 30, 1.3), rng=0)
    for gb in (None, 8):
        s = error_stats(extract_cog(img, guide_band=gb), v_true)
        print(f"반사피크 CoG guide_band={gb}: RMS={s['rms']:.3f} px, P95={s['p95']:.3f} px")

    # 품질 정보 예
    q = line_quality(synth_laser_image(v_true, amp=400, rng=1), v_true)
    print(f"포화 이미지: 포화 픽셀이 있는 열 {100 * (q['n_sat'] > 0).mean():.0f} %, "
          f"평균 선폭 {q['width'].mean():.1f} px")

    # 속도: 실제 크기(1080 x 1440) 1장
    big_truth = 540 + 30 * np.sin(np.arange(1440) / 200)
    big = synth_laser_image(big_truth, H=1080, amp=180, rng=2)
    for m in ("cog", "gauss3", "steger1d"):
        t0 = time.perf_counter()
        for _ in range(5):
            METHODS[m](big)
        print(f"{m:<9} 1080x1440 1장: {(time.perf_counter() - t0) / 5 * 1000:6.1f} ms")
```

### 6.2 실행 예시와 기대 출력

```bash
python line_extraction.py
```

```text
시나리오          방법            유효%    bias     std     RMS     P95   [px]
기본(피크180)     max         100.0  -0.011   0.382   0.382   0.748
기본(피크180)     cog         100.0   0.001   0.073   0.073   0.143
기본(피크180)     parabola3   100.0   0.002   0.199   0.199   0.405
기본(피크180)     gauss3      100.0   0.002   0.192   0.192   0.389
기본(피크180)     steger1d    100.0   0.002   0.079   0.079   0.155

저신호(피크50)     max         100.0  -0.023   0.534   0.534   1.026
저신호(피크50)     cog         100.0   0.003   0.211   0.211   0.415
저신호(피크50)     parabola3   100.0   0.001   0.381   0.381   0.760
저신호(피크50)     gauss3      100.0   0.001   0.368   0.368   0.738
저신호(피크50)     steger1d    100.0   0.003   0.170   0.170   0.333

포화(피크400)     max         100.0  -0.973   0.299   1.018   1.458
포화(피크400)     cog         100.0   0.000   0.051   0.051   0.098
포화(피크400)     parabola3   100.0  -0.473   0.299   0.559   0.958
포화(피크400)     gauss3      100.0  -0.473   0.299   0.559   0.958
포화(피크400)     steger1d    100.0   0.000   0.055   0.055   0.108

스펙클10%        max         100.0  -0.004   0.467   0.467   0.942
스펙클10%        cog         100.0   0.002   0.094   0.094   0.185
스펙클10%        parabola3   100.0   0.002   0.300   0.300   0.611
스펙클10%        gauss3      100.0   0.002   0.288   0.288   0.584
스펙클10%        steger1d    100.0   0.002   0.113   0.113   0.222

반사피크          max         100.0   1.560   6.697   6.876  29.407
반사피크          cog         100.0   1.572   6.684   6.866  29.895
반사피크          parabola3   100.0   1.573   6.689   6.871  29.717
반사피크          gauss3      100.0   1.573   6.688   6.870  29.726
반사피크          steger1d    100.0   1.576   6.692   6.875  29.892

반사피크 CoG guide_band=None: RMS=6.875 px, P95=29.916 px
반사피크 CoG guide_band=8: RMS=0.071 px, P95=0.133 px
포화 이미지: 포화 픽셀이 있는 열 100 %, 평균 선폭 4.7 px
cog       1080x1440 1장:    4.2 ms
gauss3    1080x1440 1장:   52.0 ms
steger1d  1080x1440 1장:   94.4 ms
```

(속도 ms 값은 PC 성능에 따라 다릅니다. 나머지 숫자는 난수 시드가 고정되어 있어 거의 같게 나와야 합니다.)

**결과 읽는 법**
- **기본**: CoG RMS 0.073 px(≈ 2.0 µm) 로 가장 좋습니다. 3점 방법들은 픽셀 3개만 써서 노이즈를 덜 평균하므로 0.19 px 입니다. 최대 픽셀은 0.38 px 로, 서브픽셀이 아닌 방법은 쓰면 안 되는 이유가 보입니다.
- **저신호(피크 50 DN)**: 모든 방법이 2~3배 나빠집니다 → 노출을 올려야 합니다 (F2). 이때 Steger 1D(가우시안 평활 포함)가 CoG 보다 약간 좋습니다.
- **포화(피크 400 → 255로 잘림)**: 3점 방법은 bias −0.47 px (≈ −13 µm) 로 **계통 오차**가 생깁니다. CoG 는 합성 이미지가 위아래 대칭으로 잘리기 때문에 괜찮아 보이지만, 실제 센서는 포화 근처에서 비선형·번짐(blooming)이 있고 스펙클 때문에 잘린 모양이 비대칭이 되므로 **이 결과를 믿고 포화를 허용하면 안 됩니다.**
- **반사**: 21개 열에서 가짜 피크가 더 밝으면 모든 방법이 30 px 가까이 틀립니다 (P95 ≈ 29 px). `guide_band=8` 을 켜면 RMS 0.071 px 로 회복합니다.
- **스펙클 10 %**: CoG 0.094 px. 스펙클은 실제 측정에서 가장 큰 노이즈원이고 프레임 평균으로 줄지 않습니다 (F2).

### 6.3 단위 테스트 (`tests/test_line_extraction.py`)

```python
"""tests/test_line_extraction.py — F1 단위 테스트 (pytest 로 실행)"""
import numpy as np
from line_extraction import (make_truth, synth_laser_image, extract_cog,
                             extract_gauss3, extract_steger1d)


def test_cog_accuracy_basic():
    v_true = make_truth()
    img = synth_laser_image(v_true, amp=180, rng=0)
    e = extract_cog(img) - v_true
    assert np.isnan(e).mean() == 0            # 모든 열에서 검출
    assert abs(np.nanmean(e)) < 0.02          # 치우침 < 0.02 px
    assert np.sqrt(np.nanmean(e ** 2)) < 0.15  # RMS < 0.15 px


def test_no_laser_gives_nan():
    img = np.full((200, 400), 8, np.uint8)    # 레이저 없는 이미지
    assert np.isnan(extract_cog(img, threshold=30)).all()


def test_gauss3_exact_without_noise():
    # 노이즈 0, 포화 없음 → 가우시안 3점은 거의 정확해야 함
    v_true = make_truth()
    img = synth_laser_image(v_true, amp=180, bg=0, read_noise=0, shot=False,
                            max_dn=65535, rng=0)
    e = extract_gauss3(img, bg=0) - v_true
    assert np.nanmax(np.abs(e)) < 0.05


def test_reflection_guided():
    v_true = make_truth()
    img = synth_laser_image(v_true, amp=180, reflection=(60, 81, 30, 1.3), rng=0)
    e = extract_cog(img, guide_band=8) - v_true
    assert np.nanpercentile(np.abs(e), 95) < 0.3


def test_steger_runs():
    v_true = make_truth()
    img = synth_laser_image(v_true, amp=180, rng=3)
    e = extract_steger1d(img) - v_true
    assert np.sqrt(np.nanmean(e ** 2)) < 0.15
```

```bash
python -m pytest -q test_line_extraction.py
```

```text
.....                                                                    [100%]
5 passed in 0.55s
```

### 6.4 반복성 점검 (정지 평판 100장)

실제 측정에서는 `frames` 를 카메라에서 받은 100장으로 바꾸면 됩니다.

```python
"""F1 반복성 점검: 정지한 평판을 100장 찍었다고 가정 → 열마다 v 의 표준편차"""
import numpy as np
from line_extraction import synth_laser_image, extract_cog

DZ_PER_PX_UM = 27.6          # B1 계산 예: 1 px 이동 = 27.6 µm 높이

rng = np.random.default_rng(7)
v_flat = np.full(400, 120.0) + np.linspace(0, 3, 400)   # 살짝 기운 평판
# 실제 측정에서는 frames = [카메라에서 받은 100장]
frames = [synth_laser_image(v_flat, amp=180, rng=rng) for _ in range(100)]
V = np.stack([extract_cog(f) for f in frames])           # (100, 400)

col_std = np.nanstd(V, axis=0, ddof=1)                   # 열마다 표준편차 [px]
print(f"열별 표준편차 중앙값 : {np.median(col_std):.3f} px "
      f"= {np.median(col_std) * DZ_PER_PX_UM:.1f} µm")
print(f"열별 표준편차 95 %   : {np.percentile(col_std, 95):.3f} px "
      f"= {np.percentile(col_std, 95) * DZ_PER_PX_UM:.1f} µm")
print(f"검출 실패(NaN) 비율 : {100 * np.isnan(V).mean():.2f} %")
```

```text
열별 표준편차 중앙값 : 0.073 px = 2.0 µm
열별 표준편차 95 %   : 0.081 px = 2.2 µm
검출 실패(NaN) 비율 : 0.00 %
```

합성 이미지에는 스펙클·진동이 없으므로 2 µm 수준이 나옵니다. **실제 장비에서는 5~15 µm 가 흔합니다** (BLUEPRINT B1 표). 실측값이 합성값보다 크게 나쁘면 그 차이가 스펙클·진동·레이저 흔들림의 크기입니다.

### 6.5 실제 이미지에서 결과 겹쳐 보기 (그림 저장)

```python
import numpy as np
import matplotlib
matplotlib.use("Agg")                       # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt
from line_extraction import make_truth, synth_laser_image, extract_cog, line_quality

img = synth_laser_image(make_truth(), amp=180, reflection=(60, 81, 30, 1.3), rng=0)
# 실제 이미지라면: img = cv2.imread("data/raw/S00_r01/frames/000000.png", cv2.IMREAD_UNCHANGED)
v = extract_cog(img, guide_band=8)
q = line_quality(img, v)

fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
ax[0].imshow(img, cmap="gray", aspect="auto")
ax[0].plot(np.arange(v.size), v, "r.", ms=1)
ax[0].set_ylabel("v [px]")
ax[1].plot(q["width"], label="선 폭 [px]")
ax[1].plot(q["peak"] / 255 * 10, label="피크 밝기 (×10/255)")
ax[1].set_xlabel("u [px]")
ax[1].legend()
fig.savefig("f1_overlay.png", dpi=150)
print("저장: f1_overlay.png")
```

```text
저장: f1_overlay.png
```

(한글 범례가 네모로 보이면 matplotlib 한글 글꼴 설정이 필요합니다. 범례를 영어로 써도 됩니다.)

## 7. 검증 방법과 완료 기준

| # | 검증 항목 | 방법 | 합격 기준 |
|---|---|---|---|
| 1 | 합성 기본 정확도 | 6.1, 피크 180 DN, σ 1.5 px, 20장 | CoG \|bias\| < 0.02 px, RMS < 0.15 px, 유효 100 % |
| 2 | 무노이즈 정확성 | 6.3 `test_gauss3_exact_without_noise` | 최대 오차 < 0.05 px |
| 3 | 반사 처리 | 6.3 `test_reflection_guided` | P95 < 0.3 px |
| 4 | 레이저 없는 열 | 6.3 `test_no_laser_gives_nan` | 전부 NaN (가짜 값 0 개) |
| 5 | 실측 반복성 | 정지 평판 100장, 열별 std 중앙값 | **목표 ≤ 0.18 px (≈ 5 µm)**, 허용 ≤ 0.36 px (≈ 10 µm) — B1 배치 기준 |
| 6 | 실측 검출률 | 평판 100장 | 유효 점 ≥ 99 % (평판 FOV 안 열 기준) |
| 7 | 처리 속도 | 실제 해상도 1장 | CoG ≤ 10 ms/장 (실시간 시) 또는 2500장 일괄 ≤ 60 s |
| 8 | 눈 확인 | 6.5 겹쳐 그리기 | 선 위에 점이 붙어 있고, 반사 위치로 튀는 점 없음 |

**완료 판정**: 1~4 와 7 은 W7 안에, 5·6·8 은 W8 안에 통과해야 합니다. 5 를 통과하지 못하면 F2(노출·평균)와 C7(진동)을 먼저 점검하고, 그래도 안 되면 M1 회의에서 B 영역(배율·각도) 재검토를 안건으로 올립니다.

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 최대 픽셀(`argmax`)만 사용 | 높이맵에 27.6 µm 간격의 계단 무늬 | CoG 이상 서브픽셀 방법 사용 |
| 문턱값을 빼지 않고 CoG | 중심이 창 가운데(피크 정수 위치) 쪽으로 끌려 주기적 오차 | `w = max(밝기 − threshold, 0)` |
| 창 없이 열 전체로 CoG | 반사·주변광이 섞여 큰 오차 | 피크 ±half_win 창만 사용 |
| 행·열 혼동 (`img[u, v]`) | 결과가 전부 NaN 이거나 엉뚱한 모양 | 이 문서 규칙: `img[v, u]`, 열마다 v 하나 |
| 8-bit 로 저장된 이미지를 다시 정수 연산 | 오버플로 (250 + 10 = 4) | 계산 전 `astype(np.float32)` |
| 포화 이미지를 그대로 사용 | 3점 방법 계통 오차 −0.47 px, 신뢰도 정보 상실 | F2 노출 점검 (피크 P99 ≤ 90 %) |
| 검출 실패를 0 으로 저장 | 높이맵에 깊은 구멍(가짜 오차) | 반드시 NaN 사용 (E2·H1 원칙) |
| 합성 결과만 보고 정밀도 발표 | 실제 측정에서 3~5배 나쁨 | 실측 반복성(7절 #5)을 함께 보고 |
| Steger 2D 를 처음부터 구현 | 1주 이상 소요, 일정 지연 | CoG 로 시작, Steger 는 비교용(1D) → 필요 시 확장 |

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 실측 반복성이 목표(0.18 px)보다 나쁨 (스펙클) | 중 | 높음 | 청색 레이저(B6), 선을 약간 두껍게(σ↑), 스캔 방향으로 이웃 프로파일 평균(H1 격자 중앙값) — 단 XY 분해능 손실 기록 |
| 반투명 재료에서 선이 두꺼워지고 중심이 밀림 | 높음 | 높음 | 선 폭 신뢰도 필터 + E1 실험으로 계통 오차 정량화, 재료 고정 |
| 반사가 넓은 열 범위(guide_win/2 이상)에 걸침 | 중 | 중 | guide_win 확대, 편광 필터(B7), 또는 이웃 열 연속성 기반 동적계획법 경로 탐색으로 확장 |
| 카메라 준비 지연으로 실측 단계가 W8 를 넘김 | 중 | 중 | 합성 검증(1~4)은 하드웨어 없이 먼저 완료, 실측 항목은 F2 기간(W9)으로 이월하고 기록 |
| 처리 속도 부족 | 낮음 | 낮음 | ROI 로 행 수 축소(F2), 촬영 후 일괄 처리 |

## 10. 기록 양식

**방법 비교 결과 (`results/F1/method_comparison.csv`)**

```csv
date,scenario,method,n_images,threshold,half_win,guide_band,valid_pct,bias_px,std_px,rms_px,p95_px,note
2026-11-18,기본(피크180),cog,20,30,5,,100.0,0.001,0.073,0.073,0.143,합성
```

**실측 반복성 기록 (`results/F1/repeatability_<date>.csv` 와 실험노트)**

| 항목 | 값 |
|---|---|
| 날짜 / 측정자 | |
| 캘리브레이션 ID (참고) | |
| 대상 (평판 종류) | |
| 노출 [µs] / 게인 [dB] / 레이저 [%] | |
| 워밍업 시간 [분] | |
| 촬영 장수 | 100 |
| 방법 / threshold / half_win | CoG / / |
| 열별 std 중앙값 [px] / [µm] | / |
| 열별 std 95 % [px] / [µm] | / |
| 검출률 [%] | |
| 정상 선 폭(중앙값) [px] | |
| 판정 (목표 ≤ 0.18 px) | 합격 / 허용 / 불합격 |

**설정 파일 블록 (`config/default.yaml`)**

```yaml
line_extraction:
  method: cog            # cog | gauss3 | steger1d
  threshold_dn: 30       # 배경 + 5σ 로 정한 값
  half_win_px: 5         # ≈ 1.5 × FWHM
  guide_band_px: 8       # 반사 대응 (null 이면 끔)
  guide_win_cols: 51
  low_conf:
    min_peak_dn: 90      # 3 × threshold
    max_width_factor: 2.0
    reject_saturated: true
```

## 11. 참고 자료

- C. Steger, "An Unbiased Detector of Curvilinear Structures", IEEE Transactions on Pattern Analysis and Machine Intelligence, 1998 — Steger 방법 원 논문
- R. B. Fisher, D. K. Naidu, "A Comparison of Algorithms for Subpixel Peak Detection" (1996) — CoG·가우시안·포물선 등 피크 검출 방법 비교
- 레이저 스트라이프(라인) 중심 추출 정확도 비교 연구들 (검색어: "laser stripe center extraction subpixel comparison")
- 레이저 스펙클 노이즈와 삼각측량 정밀도 한계 (검색어: "speckle noise laser triangulation uncertainty", R. G. Dorsch 외 1994 Applied Optics 논문이 대표적)
- NumPy 공식 문서: "Broadcasting", "Indexing on ndarrays" (벡터화의 기초)
- SciPy 공식 문서: `scipy.ndimage.gaussian_filter1d`, `scipy.ndimage.median_filter`
- 상위 문서 [BLUEPRINT.md](../../BLUEPRINT.md) B1(δz 공식), B6(선 두께), F1 절
