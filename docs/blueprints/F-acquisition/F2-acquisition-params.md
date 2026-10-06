# F2. 획득 파라미터

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: F. 데이터 획득

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-01 ~ 2026-12-14 (W9-10) |
| 우선순위 | 보통 |
| 트랙 | 하드웨어 |
| 선행 요소 | [F1 레이저 라인 중심 추출](F1-line-extraction.md) · [B4 카메라](../B-optics/B4-camera.md) · [B6 레이저 광원](../B-optics/B6-laser.md) · [C1 스캔 이동 장치](../C-mechanics/C1-scan-stage.md) · [C5 주변광](../C-mechanics/C5-ambient-light.md) · [C8 레이저 안전](../C-mechanics/C8-laser-safety.md) |
| 후행 요소 | [F3 저장 형식·메타데이터](F3-data-storage.md) · [D3 스캔 축 캘리브레이션](../D-calibration/D3-scan-axis.md) · [D5 캘리브레이션 검증](../D-calibration/D5-calibration-verification.md) · [E1 표면 광학 특성](../E-specimen/E1-surface-optics.md) · [I2 MSA](../I-reliability/I2-msa.md) |
| 관련 마일스톤 | M2 (게이지 블록 단차 오차 < 10 µm — 고정된 획득 파라미터로 측정해야 함) |

---

## 1. 목적

노출 시간, 게인, 레이저 출력, ROI(읽는 행 범위), 스캔 간격·속도, 프레임 평균 횟수를 **수치 기준으로 정하고 하나의 묶음(획득 프로파일, `ACQ-ID`)으로 고정**합니다.

- 같은 장비라도 노출이 다르면 중심 추출 정밀도(F1)가 2~6배 달라집니다 (6.2 노출 스윕: RMS 0.44 px → 0.07 px).
- BLUEPRINT 원칙: **한 실험 세트 안에서는 모든 파라미터를 고정**합니다. 바꾸면 그 자체가 실험 변수가 됩니다. 그래서 파라미터 묶음에 ID 를 붙이고 모든 스캔 메타데이터(F3)에 기록합니다.
- 이 요소가 끝나면: 기준 재료(회색 불투명 PLA, E1)와 게이지 블록에 대해 검증된 `config/acquisition/ACQ-2026-12-xx-A.yaml` 이 있고, 촬영 전 자동 점검 스크립트가 동작해야 합니다.

## 2. 배경 지식 (초보자용)

**노출 시간(exposure, µs)** 은 셔터가 열려 있는 시간입니다. 길수록 밝지만, 움직이는 중이면 번지고, 너무 길면 **포화**(255에서 잘림)됩니다. 산업용 카메라에서는 밝기가 노출 시간에 거의 비례합니다 (포화 전까지).

**게인(gain, dB)** 은 신호를 전자적으로 증폭합니다. 신호와 노이즈를 같이 키우므로 **정밀도는 좋아지지 않습니다**. 노출과 레이저 출력을 먼저 올리고, 게인은 0 dB 를 기본으로 합니다.

**레이저 출력** 은 밝기를 올리는 다른 방법이지만 안전 등급(C8, Class 2 ≤ 1 mW 권장) 안에서만 조절합니다. 출력을 바꾸면 선 두께와 스펙클도 미세하게 바뀝니다.

**포화가 왜 나쁜가** (F1 참고): ① 3점 맞춤 방법은 계통 오차(합성 실험 −0.47 px ≈ −13 µm), ② 밝기 기반 신뢰도 판단 불가, ③ 실제 센서는 포화 근처에서 비선형·번짐. → **규칙: 열별 피크의 99 % 값(P99) ≤ 최댓값의 90 %**, 목표는 60~85 %.

**어두우면 왜 나쁜가**: 신호 대비 노이즈가 커집니다. 6.2 결과에서 피크 20 % 일 때 RMS 0.44 px, 84 % 일 때 0.07 px 입니다.

**ROI(Region Of Interest)**: 센서 전체 1080 행 중 레이저가 지나갈 수 있는 행만 읽으면 전송량이 줄어 프레임 속도가 올라갑니다. 필요한 행 수는 B1 공식으로 계산합니다.

```
1 mm 높이당 이미지 이동량 = M · sinθ / p      (B1 예: 0.25 × 0.5 / 0.00345 mm = 36.2 px/mm)
ROI 행 수 = 측정 깊이 범위[mm] × 36.2 + 위아래 여유 20 px × 2
          = 15 mm × 36.2 + 40 ≈ 584 행
```

**번짐(motion blur) 한계**: 연속 이동 스캔에서는 노출 동안 스테이지가 움직입니다. 이동 거리를 **스캔 간격의 10 % 이하**로 두면 무시할 수 있습니다.

```
노출 상한 = 간격 × 0.1 / 속도 = 0.02 mm × 0.1 / 2 mm/s = 1 ms = 1000 µs
필요 fps  = 속도 / 간격 = 2 / 0.02 = 100 fps (B4)
```

**프레임 평균**: 정지 상태에서 N장을 평균하면 **랜덤 노이즈는 1/√N** 로 줄어듭니다. 하지만 **스펙클 노이즈**(레이저가 거친 표면에 만드는 얼룩)는 정지 상태에서 매번 같은 무늬이므로 **줄지 않습니다**. 6.2 의 시뮬레이션이 이것을 보여 줍니다: 64장 평균으로 반복성은 0.077 → 0.010 px 로 좋아지지만, 정답 대비 오차는 0.104 → 0.062 px 에서 멈춥니다. "반복성이 좋다 = 정확하다"가 아닙니다.

**감마·자동 기능**: 많은 카메라에 감마 보정, 자동 노출, 자동 게인, 샤프닝, 노이즈 제거가 있습니다. 이들은 밝기를 **비선형**으로 바꾸거나 프레임마다 바꿔서 중심 추출을 치우치게 합니다. **모두 끄고 감마 = 1.0** 으로 둡니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 · 파일 | 설명 |
|---|---|---|---|
| 입력 | F1 추출 함수 | `src/cvlab/triangulation.py` | 노출별 정밀도 평가에 사용 |
| 입력 | 광학 배치 값 | M, θ, p (B1·B2 결정값) | ROI 계산 |
| 입력 | 스캔 사양 | 간격 0.02 mm, 속도, 길이 (C1) | fps·노출 상한 계산 |
| 입력 | 기준 시료 | 회색 불투명 PLA 평판, 게이지 블록 | 노출 결정 대상 (E1, D5) |
| 산출물 | 획득 프로파일 | `config/acquisition/ACQ-2026-12-10-A.yaml` | 6.3 의 YAML 형식 |
| 산출물 | 점검 모듈 | `src/cvlab/acquisition/params.py` | `exposure_report`, `suggest_exposure`, `roi_rows`, `max_exposure_us`, `check_frame_positions` |
| 산출물 | 프로파일 점검 스크립트 | `scripts/check_acq_profile.py` | 촬영 전 규칙 위반 검사 |
| 산출물 | 노출 스윕 결과 | `results/F2/exposure_sweep_<date>.csv` | 노출 × (피크 %, 포화 %, 반복성 px) |
| 산출물 | 프레임 평균 결과 | `results/F2/frame_avg_<date>.csv` | N × (반복성, 평판 잔차) |
| 산출물 | 획득 점검 로그 | `results/F2/acq_check_log.csv` | 세션마다 노출 점검 결과 한 줄 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 노출 목표 | 피크 30~100 % | **열별 피크 P99 = 60~85 % (상한 90 %)** | 6.2 스윕: 84 % 에서 CoG 0.071 px, 포화 시작(100 %) 직전이 최선 |
| 게인 | 0~24 dB | **0 dB** (부득이하면 ≤ 6 dB) | 게인은 노이즈도 같이 키움 |
| 픽셀 형식 | Mono8 / Mono10·12 | **Mono12** (대역폭이 부족하면 Mono8) | 양자화 노이즈 감소 (B4) |
| 감마·자동 노출·자동 게인·샤프닝 | 켬 / 끔 | **모두 끔, 감마 1.0** | 비선형 → 중심 치우침 |
| 레이저 출력 | 0~100 % | 안전 등급 안에서 **노출이 번짐 한계를 넘지 않게** 조합 | C8, 번짐 한계 1000 µs |
| ROI | 전체 / 필요 행만 | **측정 깊이 + 위아래 20 px** (예: 584 행) | 전송량 ↓ → fps ↑ |
| 스캔 방식 | 연속 + 위치 트리거 / 스텝 & 촬영 | **연속 + 위치(엔코더) 트리거** 기본, 반복성 실험·검증은 스텝도 가능 | C1. 시간 간격 촬영은 속도 변동 오차 |
| 스캔 간격 | 0.01 / 0.02 / 0.05 mm | **0.02 mm** (X 분해능과 맞춤) | A2, C1 |
| 스캔 속도 | 1~5 mm/s | **2 mm/s** (100 fps) | 노출 상한 1000 µs 와 카메라 fps 여유 |
| 프레임 평균 N | 1 / 4 / 16 | 연속: **1** (금지), 스텝: **4** | 6.2: N=4 에서 정답 대비 RMS 0.104 → 0.074 px, 16 이상은 개선 미미(스펙클 한계) |
| 스텝 정지 후 대기 | 0.1~0.5 s | **0.2 s** (C7 진동 측정 후 조정) | C1 |
| 워밍업 | 0~60 분 | **30 분** (카메라·레이저) | C6, B6 |

## 5. 수행 절차

1. **카메라 설정 정리 (W9 월, 0.5일)**
   - [ ] 카메라 설정 프로그램(제조사 뷰어)에서 자동 노출·자동 게인·감마·샤프닝·노이즈 제거 끔, 픽셀 형식 Mono12 확인
   - [ ] 설정을 카메라 내부 "사용자 설정(User Set)"에 저장하고 부팅 시 자동 적용되게 함
   - [ ] 6.4 의 SDK 예시 구조로 Python 에서도 같은 값을 매번 다시 써 넣고, 다시 읽어서 일치하는지 확인 (값을 읽어 메타데이터에 기록)
2. **ROI·fps 계산 (W9 월, 0.5일)**
   - [ ] B1 결정값으로 `roi_rows()` 계산 → 측정 깊이 범위(시편 최대 높이 + 여유) 확정
   - [ ] ROI 를 설정한 상태에서 카메라가 실제로 내는 최대 fps 측정 (10 초 촬영 후 프레임 수 ÷ 10)
   - [ ] 필요 fps(100)가 실측 최대 fps 의 80 % 이하인지 확인. 아니면 속도를 낮춤
3. **주변광 점검 (W9 화, 0.5일)** — C5 완료 기준 재확인
   - [ ] 측정 노출로 레이저 끈 이미지 16장 → `exposure_report(..., dark=...)` 의 `dark_ratio_pct` < 5 %
4. **노출 결정 (W9 화~수, 1.5일)**
   - [ ] 기준 재료(회색 PLA 평판)에서 노출 200 µs 로 시작 → `suggest_exposure` 로 2~3회 반복 조정 → 피크 P99 60~85 %
   - [ ] 게이지 블록(금속, 더 밝거나 반사 가능)과 검정·흰색 시편도 같은 노출에서 포화되지 않는지 확인. 재료마다 노출이 달라야 하면 **재료별 ACQ-ID 를 따로** 만듦
   - [ ] 노출이 번짐 한계(1000 µs)를 넘으면 레이저 출력 ↑ (안전 등급 확인) 또는 속도 ↓
5. **실측 노출 스윕 (W9 목~금, 1.5일)**
   - [ ] 정지 평판, 노출 5단계(목표의 0.25, 0.5, 0.75, 1.0, 1.3배) × 각 50장
   - [ ] 단계마다 열별 v 표준편차 중앙값(F1 6.4 방식)과 포화 열 % 를 `results/F2/exposure_sweep_<date>.csv` 로 저장
   - [ ] 반복성이 가장 좋은 노출이 포화 직전인지 확인 (6.2 합성 결과와 같은 경향인지)
6. **프레임 평균 효과 (W10 월, 1일)** — 스텝 모드 사용 시
   - [ ] 정지 평판, N = 1, 4, 16 각각 10회 반복
   - [ ] ① 반복성(열별 std) ② 평판 평면 맞춤 잔차 RMS 를 비교 → ①은 1/√N 로 줄고 ②는 바닥이 생기는지 확인 (②의 바닥 = 스펙클 + 평판 자체 형상)
7. **스캔 동작 확인 (W10 화~수, 1.5일)**
   - [ ] 50 mm 연속 스캔 3회, 프레임마다 엔코더 위치 기록 → `check_frame_positions` 로 빠진 프레임 0, 역방향 0 확인
   - [ ] 기대 프레임 수: 50 / 0.02 + 1 = 2501 장 (시작·끝 포함). 실제 수와 다르면 트리거 설정 점검
   - [ ] 간격 표준편차(µm)를 기록 → 간격의 1/10(2 µm) 이하가 목표
8. **고정과 문서화 (W10 목~금, 1일)**
   - [ ] 확정값을 `config/acquisition/ACQ-2026-12-10-A.yaml` 로 저장, `scripts/check_acq_profile.py` 통과
   - [ ] 세션 시작 점검 절차(워밍업 → 주변광 → 노출 점검 1장 → 기록) 1쪽 작성, 장비 옆에 부착
   - [ ] F3 메타데이터에 `acq_id` 와 실제 읽어 온 노출·게인 값을 넣도록 연결

## 6. Python 구현

### 6.1 획득 파라미터 점검 모듈 (`acq_params.py`)

노출·포화 점검, 권장 노출 계산, ROI·노출 상한 계산, 프레임 위치 점검, 그리고 합성 이미지로 노출 스윕과 프레임 평균 효과를 보여 줍니다. 앞의 함수들(`exposure_report` ~ `check_frame_positions`)은 실제 카메라 이미지에도 그대로 씁니다.

```python
"""
acq_params.py — 획득 파라미터 점검 도구 (F2)
최종 위치(권장): src/cvlab/acquisition/params.py
(1) 노출/포화 점검   (2) 노출 권장값 계산   (3) ROI·노출 한계 계산
(4) 노출 스윕 시뮬레이션   (5) 프레임 평균 효과 시뮬레이션 (랜덤 노이즈 vs 스펙클)
"""
import math
import numpy as np
from scipy.special import erf


# ---------------------------------------------------------------------------
# (1) 노출·포화 점검 — 실제 카메라 이미지에도 그대로 사용
# ---------------------------------------------------------------------------
def exposure_report(img, max_dn=255, dark=None, min_peak_frac=0.30, max_peak_frac=0.90):
    """
    img  : 레이저 켠 이미지 (H, W)
    dark : 같은 설정, 레이저 끈 이미지 여러 장 (N, H, W) 또는 1장 (H, W). 없으면 생략
           여러 장을 평균하면 픽셀 랜덤 노이즈는 줄고 '진짜 주변광'만 남는다 (C5 점검용)
    판정 기준(F2 권장):
      - 열별 피크 P99 ≤ 90 % × max_dn      (포화 금지, BLUEPRINT F1)
      - 포화 픽셀이 있는 열 = 0 %            (허용 최대 0.5 %)
      - 열별 피크 중앙값 ≥ 30 % × max_dn     (너무 어두우면 노이즈 ↑)
      - (레이저 끈 평균 이미지 최댓값 − 흑레벨) < 레이저 신호의 5 %  (C5)
    """
    f = img.astype(np.float64)
    peak = f.max(axis=0)
    rep = {
        "peak_med_frac": float(np.median(peak) / max_dn),
        "peak_p99_frac": float(np.percentile(peak, 99) / max_dn),
        "sat_col_pct": float(100 * (peak >= max_dn).mean()),
    }
    ok = (rep["peak_p99_frac"] <= max_peak_frac and rep["sat_col_pct"] <= 0.5
          and rep["peak_med_frac"] >= min_peak_frac)
    if dark is not None:
        d = np.asarray(dark, np.float64)
        d = d.mean(axis=0) if d.ndim == 3 else d
        black = np.median(d)                                  # 흑레벨(오프셋)
        signal = np.median(peak) - black
        rep["dark_ratio_pct"] = float(100 * (d.max() - black) / signal)
        ok = ok and rep["dark_ratio_pct"] < 5.0
    rep["ok"] = bool(ok)
    return rep


def suggest_exposure(exposure_us, img, max_dn=255, target_frac=0.75, bg=None):
    """
    밝기가 노출 시간에 비례한다고 보고, 열별 피크 P99 가 target_frac × max_dn 이
    되도록 노출을 다시 계산. 포화 상태면 비례식이 성립하지 않으므로 절반으로 줄이고 다시 측정.
    """
    f = img.astype(np.float64)
    peak = f.max(axis=0)
    if (peak >= max_dn).mean() > 0.005:
        return exposure_us * 0.5, "포화 → 노출 1/2 로 줄여서 다시 촬영"
    if bg is None:
        bg = np.median(f)
    p99 = np.percentile(peak, 99) - bg
    new = exposure_us * (target_frac * max_dn - bg) / max(p99, 1.0)
    return new, "비례 계산"


# ---------------------------------------------------------------------------
# (2) ROI 행 수와 노출 시간 상한 계산
# ---------------------------------------------------------------------------
def roi_rows(z_range_mm, M, theta_deg, pixel_um, margin_px=20):
    """측정 깊이 범위를 덮는 데 필요한 행 수 (B1: 1 px = p/(M sinθ) 높이)"""
    px_per_mm = M * math.sin(math.radians(theta_deg)) / (pixel_um / 1000)
    return math.ceil(z_range_mm * px_per_mm) + 2 * margin_px, px_per_mm


def max_exposure_us(speed_mm_s, pitch_mm, blur_frac=0.1):
    """연속 스캔 중 노출 동안 이동 거리 ≤ pitch × blur_frac 이 되게 하는 노출 상한"""
    return pitch_mm * blur_frac / speed_mm_s * 1e6


def check_frame_positions(stage_y_mm, pitch_mm, tol_frac=0.25):
    """
    프레임마다 기록된 스테이지 위치로 '빠진 프레임'과 '간격 불균일'을 검사.
    간격이 pitch × (1 ± tol_frac) 를 벗어나면 문제로 센다.
    """
    gaps = np.diff(stage_y_mm)
    big = gaps > 1.5 * pitch_mm                 # 간격이 1.5배 이상 = 프레임이 빠짐
    missing = int((np.round(gaps[big] / pitch_mm) - 1).sum())
    irregular = int(np.sum(np.abs(gaps / pitch_mm - 1) > tol_frac))
    backward = int(np.sum(gaps <= 0))           # 역방향 이동(백래시·왕복 스캔)
    return {"n_frames": len(stage_y_mm), "missing": missing,
            "irregular_gaps": irregular, "backward": backward,
            "pitch_mean_mm": float(gaps.mean()), "pitch_std_um": float(gaps.std() * 1000)}


# ---------------------------------------------------------------------------
# 합성 이미지 (F1 과 같은 모델의 간단 버전) + CoG
# ---------------------------------------------------------------------------
def synth(v_true, H, amp, sigma=1.5, bg=8.0, read_noise=2.0, max_dn=255,
          speckle_pattern=None, rng=None):
    rng = np.random.default_rng(rng)
    edges = np.arange(H + 1)[:, None] - 0.5
    z = (edges - v_true[None, :]) / (np.sqrt(2) * sigma)
    cdf = 0.5 * (1 + erf(z))
    sig = amp * (cdf[1:] - cdf[:-1]) * np.sqrt(2 * np.pi) * sigma
    if speckle_pattern is not None:          # 정지 장면: 매 프레임 같은 스펙클
        sig = sig * speckle_pattern
    img = bg + sig
    img = img + rng.normal(0, 1, img.shape) * np.sqrt(img) + rng.normal(0, read_noise, img.shape)
    return np.clip(np.round(img), 0, max_dn)


def cog(img, threshold=30, half_win=5):
    H, W = img.shape
    p = img.argmax(axis=0)
    rows = p[None, :] + np.arange(-half_win, half_win + 1)[:, None]
    inside = (rows >= 0) & (rows < H)
    vals = img[np.clip(rows, 0, H - 1), np.arange(W)[None, :]]
    w = np.where(inside, np.maximum(vals - threshold, 0), 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (w * rows).sum(axis=0) / w.sum(axis=0)
    v[img.max(axis=0) <= threshold] = np.nan
    return v


def gauss3(img, bg=8.0):
    g = np.maximum(img - bg, 0.5)
    p = np.clip(img.argmax(axis=0), 1, img.shape[0] - 2)
    u = np.arange(img.shape[1])
    la, lb, lc = np.log(g[p - 1, u]), np.log(g[p, u]), np.log(g[p + 1, u])
    with np.errstate(invalid="ignore", divide="ignore"):
        d = 0.5 * (la - lc) / (la - 2 * lb + lc)
    d[np.abs(d) > 1] = np.nan
    return p + d


def fmt(rep):
    """보기 좋게 출력하기 위한 도우미"""
    return ", ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                     for k, v in rep.items())


if __name__ == "__main__":
    H, W = 200, 400
    v_true = 100 + 20 * np.sin(2 * np.pi * np.arange(W) / W)

    # ---- (2) ROI · 노출 상한 (B1 계산 예의 값 사용) ----
    rows, ppm = roi_rows(z_range_mm=15, M=0.25, theta_deg=30, pixel_um=3.45)
    print(f"1 mm 높이 = {ppm:.1f} px 이동 → 15 mm 깊이 범위 ROI = {rows} 행 (전체 1080 행 중)")
    print(f"2 mm/s, 간격 0.02 mm 일 때 노출 상한 = {max_exposure_us(2.0, 0.02):.0f} µs")

    # ---- 프레임 위치 점검: 50 mm 스캔 중 3장이 빠진 경우 ----
    y = np.arange(2500) * 0.02 + np.random.default_rng(5).normal(0, 0.0005, 2500)
    y = np.delete(y, [700, 701, 1800])
    print("프레임 위치 점검:", fmt(check_frame_positions(y, 0.02)))

    # ---- (1) 노출 점검 + 권장 노출 ----
    gain_dn_per_us = 0.2                       # 가정: 노출 1 µs 당 피크 0.2 DN
    img = synth(v_true, H, amp=gain_dn_per_us * 1500, rng=0)
    dark = np.stack([synth(v_true, H, amp=0, rng=10 + i) for i in range(16)])  # 레이저 끈 16장
    print("\n노출 1500 µs:", fmt(exposure_report(img, dark=dark)))
    new, why = suggest_exposure(1500, img)
    print(f"  → 권장 노출 {new:.0f} µs ({why})")
    img2 = synth(v_true, H, amp=gain_dn_per_us * new, rng=2)
    new2, why2 = suggest_exposure(new, img2)
    print(f"노출 {new:.0f} µs:", fmt(exposure_report(img2, dark=dark)))
    print(f"  → 권장 노출 {new2:.0f} µs ({why2})")

    # ---- (4) 노출 스윕: 노출에 따른 중심 추출 오차 ----
    print("\n노출[µs] 피크%  포화열%  CoG_RMS[px]  가우스3점_RMS[px]")
    for exp_us in (150, 300, 600, 900, 1100, 1300, 2000):
        e_c, e_g, rep = [], [], None
        for s in range(10):
            im = synth(v_true, H, amp=gain_dn_per_us * exp_us, rng=100 + s)
            rep = rep or exposure_report(im)
            e_c.append(cog(im) - v_true)
            e_g.append(gauss3(im) - v_true)
        rc = np.sqrt(np.nanmean(np.concatenate(e_c) ** 2))
        rg = np.sqrt(np.nanmean(np.concatenate(e_g) ** 2))
        print(f"{exp_us:8d} {100 * rep['peak_p99_frac']:5.0f} {rep['sat_col_pct']:8.1f} "
              f"{rc:12.3f} {rg:16.3f}")

    # ---- (5) 프레임 평균: 랜덤 노이즈는 줄고 스펙클은 남는다 ----
    pattern = np.random.default_rng(42).normal(1.0, 0.10, (H, W)).clip(0.2)  # 고정 스펙클
    print("\nN장평균  반복성(열별 std 중앙값)[px]  정답대비 RMS[px]")
    for N in (1, 4, 16, 64):
        results = []
        for rep_i in range(8):                 # 같은 조건 8번 반복 측정
            rng = np.random.default_rng(1000 * N + rep_i)
            avg = np.mean([synth(v_true, H, amp=150, speckle_pattern=pattern, rng=rng)
                           for _ in range(N)], axis=0)
            results.append(cog(avg))
        R = np.stack(results)
        rep_std = np.median(np.nanstd(R, axis=0, ddof=1))
        rms = np.sqrt(np.nanmean((R - v_true) ** 2))
        print(f"{N:6d} {rep_std:24.4f} {rms:18.4f}")
```

### 6.2 실행 예시와 기대 출력

```bash
python acq_params.py
```

```text
1 mm 높이 = 36.2 px 이동 → 15 mm 깊이 범위 ROI = 584 행 (전체 1080 행 중)
2 mm/s, 간격 0.02 mm 일 때 노출 상한 = 1000 µs
프레임 위치 점검: n_frames=2497, missing=3, irregular_gaps=2, backward=0, pitch_mean_mm=0.020, pitch_std_um=1.149

노출 1500 µs: peak_med_frac=1.000, peak_p99_frac=1.000, sat_col_pct=100.000, dark_ratio_pct=1.569, ok=False
  → 권장 노출 750 µs (포화 → 노출 1/2 로 줄여서 다시 촬영)
노출 750 µs: peak_med_frac=0.608, peak_p99_frac=0.710, sat_col_pct=0.000, dark_ratio_pct=2.636, ok=True
  → 권장 노출 794 µs (비례 계산)

노출[µs] 피크%  포화열%  CoG_RMS[px]  가우스3점_RMS[px]
     150    20      0.0        0.443            0.488
     300    34      0.0        0.172            0.344
     600    60      0.0        0.095            0.244
     900    84      0.0        0.071            0.196
    1100   100      1.8        0.063            0.176
    1300   100     65.2        0.057            0.163
    2000   100    100.0        0.049            0.559

N장평균  반복성(열별 std 중앙값)[px]  정답대비 RMS[px]
     1                   0.0770             0.1039
     4                   0.0396             0.0740
    16                   0.0196             0.0653
    64                   0.0098             0.0624
```

**결과 읽는 법**
- **프레임 위치 점검**: 2500장 중 3장이 빠진 것을 `missing=3` 으로 찾아냅니다. `irregular_gaps=2` 는 간격이 튄 곳이 2군데라는 뜻입니다 (연속 2장이 빠진 곳 1 + 1장이 빠진 곳 1).
- **노출 1500 µs**: 모든 열이 포화(`sat_col_pct=100`) → 불합격, 노출 절반 권장. **750 µs**: 피크 P99 71 %, 포화 0 %, 주변광 2.6 % → 합격. 다시 계산하면 794 µs 를 권하지만 차이가 작으므로 750 µs 로 고정해도 됩니다 (조정은 2~3회에서 멈춤).
- **노출 스윕**: 피크 20 % → 84 % 로 올리면 CoG RMS 가 0.443 → 0.071 px 로 6배 좋아집니다. 1100 µs 이상에서 포화 열이 생기고 가우시안 3점은 2000 µs 에서 0.559 px 로 급격히 나빠집니다. 합성 모델은 포화를 대칭으로 자르기 때문에 CoG 는 계속 좋아 보이지만, 실제 센서에서는 그렇지 않으므로 **90 % 규칙을 지킵니다** (F1 6.2 설명).
- **프레임 평균**: 반복성은 N 이 4배가 될 때마다 정확히 절반(1/√N)이 되지만, 정답 대비 RMS 는 0.062 px 근처에서 멈춥니다. 그 바닥이 고정 스펙클이 만든 오차입니다.

### 6.3 획득 프로파일(YAML) 점검 (`scripts/check_acq_profile.py`)

```python
"""획득 프로파일(YAML)을 읽어 규칙 위반을 검사 — 촬영 전에 매번 실행"""
import math
import yaml

PROFILE_TEXT = """
acq_id: ACQ-2026-12-10-A        # 획득 파라미터 묶음 ID (바꾸면 B, C ... 로 올림)
camera:
  pixel_format: Mono12
  exposure_us: 800
  gain_db: 0.0
  gamma: 1.0                     # 반드시 1.0 (선형)
  auto_exposure: false
  auto_gain: false
  roi: {offset_y: 248, height: 584, offset_x: 0, width: 1440}
  max_fps_at_roi: 220            # 카메라 사양서/실측값 (예시)
laser:
  power_pct: 60
  warmup_min: 30
scan:
  mode: continuous               # continuous | step
  pitch_mm: 0.02
  speed_mm_s: 2.0
  length_mm: 50
  frame_avg_n: 1                 # step 모드에서만 > 1
  settle_s: 0.2                  # step 모드 정지 후 대기
"""


def check_profile(p):
    c, s = p["camera"], p["scan"]
    msgs = []
    fps = s["speed_mm_s"] / s["pitch_mm"]                     # B4: fps = 속도 / 간격
    exp_limit = s["pitch_mm"] * 0.1 / s["speed_mm_s"] * 1e6    # 노출 중 이동 ≤ 간격의 10 %
    if s["mode"] == "continuous":
        if c["exposure_us"] > exp_limit:
            msgs.append(f"노출 {c['exposure_us']} µs > 번짐 한계 {exp_limit:.0f} µs")
        if c["exposure_us"] > 1e6 / fps:
            msgs.append("노출이 프레임 주기보다 김")
        if fps > 0.8 * c["max_fps_at_roi"]:
            msgs.append(f"필요 {fps:.0f} fps > 카메라 여유 한계 {0.8 * c['max_fps_at_roi']:.0f} fps")
        if s["frame_avg_n"] != 1:
            msgs.append("연속 이동 모드에서는 프레임 평균 금지 (위치가 섞임)")
    if c["gamma"] != 1.0 or c["auto_exposure"] or c["auto_gain"]:
        msgs.append("감마 1.0, 자동 노출/게인 끔 이어야 함")
    if c["gain_db"] > 6:
        msgs.append("게인 6 dB 초과 — 노출·레이저 출력을 먼저 올릴 것")
    if p["laser"]["warmup_min"] < 30:
        msgs.append("레이저 워밍업 30분 미만")
    n_frames = math.floor(s["length_mm"] / s["pitch_mm"]) + 1
    if s["mode"] == "continuous":
        t_scan = s["length_mm"] / s["speed_mm_s"]
    else:
        t_scan = n_frames * (s["settle_s"] + s["frame_avg_n"] * c["exposure_us"] * 1e-6)
    return fps, n_frames, t_scan, msgs


p = yaml.safe_load(PROFILE_TEXT)
fps, n, t, msgs = check_profile(p)
print(f"{p['acq_id']}: 필요 {fps:.0f} fps, 프레임 {n} 장, 스캔 시간 {t:.0f} s")
print("문제 없음" if not msgs else "문제: " + "; ".join(msgs))

# 스텝 모드로 바꾸면?
p["scan"].update(mode="step", frame_avg_n=4)
fps, n, t, msgs = check_profile(p)
print(f"step, 4장 평균: 프레임 위치 {n} 곳, 예상 스캔 시간 {t:.0f} s ({t / 60:.1f} 분, 이동 시간 제외)")
```

```text
ACQ-2026-12-10-A: 필요 100 fps, 프레임 2501 장, 스캔 시간 25 s
문제 없음
step, 4장 평균: 프레임 위치 2501 곳, 예상 스캔 시간 508 s (8.5 분, 이동 시간 제외)
```

실제 사용 시에는 `PROFILE_TEXT` 대신 `yaml.safe_load(open("config/acquisition/ACQ-2026-12-10-A.yaml", encoding="utf-8"))` 로 읽습니다. BLUEPRINT B4 의 "50 mm 스캔 2500장"은 근삿값이고, 시작·끝 위치를 모두 찍으면 2501장입니다.

### 6.4 카메라 설정 적용 — 예시 구조 (하드웨어 SDK 필요, 그대로 실행 불가)

아래는 **구조만 보여 주는 의사 코드**입니다. `open_camera`, `cam.set`, `cam.get` 은 실제 함수가 아닙니다. 설정 이름(`ExposureTime`, `Gain`, `Gamma`, `ExposureAuto`, `GainAuto`, `PixelFormat`, `OffsetY`, `Height`, `TriggerMode`, `TriggerSource`)은 GenICam SFNC(표준 기능 이름 규약)의 이름이며, 대부분의 산업용 카메라가 따르지만 **사용하는 카메라의 SDK 문서에서 정확한 이름과 호출 방법을 반드시 확인**해야 합니다.

```python
# 예시 구조 (하드웨어 SDK 필요, 그대로 실행 불가)
import yaml

prof = yaml.safe_load(open("config/acquisition/ACQ-2026-12-10-A.yaml", encoding="utf-8"))
c = prof["camera"]

cam = open_camera(serial="XXXXXXXX")          # ← 제조사 SDK 의 카메라 열기 함수로 교체
settings = [                                  # 순서 중요: 자동 기능을 먼저 끈다
    ("ExposureAuto", "Off"),
    ("GainAuto", "Off"),
    ("PixelFormat", c["pixel_format"]),
    ("Gamma", c["gamma"]),
    ("Gain", c["gain_db"]),
    ("ExposureTime", c["exposure_us"]),
    ("Height", c["roi"]["height"]),           # ROI: 높이를 먼저 줄이고 오프셋 설정
    ("OffsetY", c["roi"]["offset_y"]),
    ("TriggerMode", "On"),
    ("TriggerSource", "Line0"),               # 엔코더/스테이지 펄스가 들어오는 입력선
]
applied = {}
for name, value in settings:
    cam.set(name, value)                      # ← SDK 의 설정 쓰기
    applied[name] = cam.get(name)             # ← 실제 적용된 값을 다시 읽음 (반올림될 수 있음)

# 읽어 온 값을 F3 메타데이터에 그대로 기록 (요청값이 아니라 '실제값')
print(applied)
```

## 7. 검증 방법과 완료 기준

| # | 검증 항목 | 방법 | 합격 기준 |
|---|---|---|---|
| 1 | 포화 | 기준 재료·게이지 블록 이미지 `exposure_report` | 피크 P99 ≤ 90 %, 포화 열 ≤ 0.5 % (목표 0 %) |
| 2 | 신호 크기 | 같은 보고서 | 피크 중앙값 ≥ 30 % (목표 60~85 %) |
| 3 | 주변광 | 레이저 끈 16장 평균 | `dark_ratio_pct` < 5 % (C5) |
| 4 | 설정 고정 | SDK 로 다시 읽은 값 vs YAML | 자동 노출·게인 꺼짐, 감마 1.0, 노출 차이 < 1 % |
| 5 | 번짐 | 노출 × 속도 | ≤ 스캔 간격의 10 % (예: ≤ 2 µm) |
| 6 | 프레임 누락 | 50 mm 연속 스캔 3회 `check_frame_positions` | missing = 0, backward = 0, 간격 std ≤ 2 µm |
| 7 | fps 여유 | 필요 fps / 실측 최대 fps | ≤ 0.8 |
| 8 | 노출-정밀도 관계 | 실측 노출 스윕 | 선택한 노출의 반복성이 스윕 최솟값의 1.2배 이내 |
| 9 | 반복성 (F1 연계) | 정지 평판 100장, 선택한 파라미터 | 열별 std 중앙값 ≤ 0.18 px (목표), ≤ 0.36 px (허용) |

**완료 판정**: 1~7 모두 합격 + 8·9 결과가 기록되어 있고, `ACQ-ID` YAML 이 저장소에 커밋되어 있으면 완료입니다. 이 프로파일로 D3·D5(M2) 측정을 진행합니다.

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 자동 노출을 켜 둠 | 시편마다 밝기가 달라지고 같은 시편 반복 측정값이 흔들림 | ExposureAuto/GainAuto Off, 매 세션 다시 읽어 확인 |
| 감마가 1.0 이 아님 | CoG 중심이 피크 쪽으로 치우침, 선 두께가 다르게 보임 | Gamma 1.0 (또는 감마 기능 끔) |
| 밝게 보이려고 게인 ↑ | 이미지는 밝지만 반복성이 나빠짐 | 게인 0 dB, 노출·레이저 출력으로 조정 |
| 화면이 "보기 좋게" 노출 조정 | 레이저 선이 하얗게 포화 | 숫자(P99 ≤ 90 %)로 판단, 눈으로 판단 금지 |
| 연속 이동에서 프레임 평균 | 서로 다른 위치가 섞여 형상이 번짐 | 연속 모드 N = 1, 평균은 스텝 모드만 |
| 시간 간격(타이머)으로 촬영 | Y 치수 오차, 가속·감속 구간 왜곡 | 엔코더 위치 트리거 또는 위치 기록 후 사용 |
| 금속 게이지 블록과 PLA 를 같은 노출로 측정 | 금속에서 포화 또는 PLA 에서 신호 부족 | 재료별 노출 확인, 필요 시 재료별 ACQ-ID |
| 실험 도중 노출 변경을 기록하지 않음 | 나중에 결과 차이의 원인을 모름 | 바꾸면 새 ACQ-ID, 메타데이터 자동 기록 |
| 워밍업 없이 측정 | 첫 10~20분 동안 높이가 서서히 변함 | 30분 워밍업, 세션 시작 점검 기록 |
| ROI 를 시편 높이에 꼭 맞춤 | 높은 형상이나 베드 기울기에서 선이 ROI 밖으로 나가 NaN | 위아래 여유 20 px 이상 |

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 번짐 한계 안에서 충분한 밝기를 얻지 못함 (어두운 재료) | 중 | 중 | 속도 ↓ (1 mm/s → 노출 상한 2000 µs), 레이저 출력 ↑(안전 등급 내), 렌즈 조리개 조정 시 D1·D2 재교정 필요 |
| 같은 FOV 안에 밝은 곳·어두운 곳이 섞여 단일 노출 불가 | 중 | 중 | 다중 노출(HDR) 후 열마다 포화되지 않은 노출 선택 — 스캔 시간 2~3배, E1 에서 평가 |
| 카메라 대역폭 부족으로 프레임 누락 | 중 | 높음 | ROI 축소, Mono8, 속도 ↓, 누락 검사(7절 #6) 자동화 |
| 레이저 출력이 시간에 따라 변함 | 중 | 중 | 워밍업 30분, 세션 중 피크 밝기 추이를 로그로 남겨 ±10 % 넘으면 경고 |
| 파라미터 변경이 기록되지 않음 | 중 | 높음 | 촬영 스크립트가 카메라에서 실제값을 읽어 메타데이터에 자동 기록 (F3) |

## 10. 기록 양식

**획득 프로파일 (`config/acquisition/ACQ-2026-12-10-A.yaml`)** — 6.3 의 `PROFILE_TEXT` 형식을 그대로 사용합니다. 아래 항목을 추가로 적습니다.

```yaml
acq_id: ACQ-2026-12-10-A
decided_on: 2026-12-10
decided_by: student_A
material: gray_opaque_PLA      # 이 프로파일이 검증된 재료
calibration_id: CAL-2026-11-30-A
evidence:
  exposure_sweep: results/F2/exposure_sweep_2026-12-04.csv
  frame_avg: results/F2/frame_avg_2026-12-07.csv
  peak_p99_pct: null            # 측정값 기입
  dark_ratio_pct: null
  repeatability_px: null
```

**노출 스윕 결과 (`results/F2/exposure_sweep_<date>.csv`)**

```csv
date,material,exposure_us,gain_db,laser_pct,n_frames,peak_med_pct,peak_p99_pct,sat_col_pct,rep_std_med_px,rep_std_med_um,note
```

**세션 시작 점검 로그 (`results/F2/acq_check_log.csv`)**

```csv
date,time,operator,acq_id,warmup_min,room_temp_C,peak_p99_pct,sat_col_pct,dark_ratio_pct,ok,note
```

## 11. 참고 자료

- EMVA 1288 표준 (European Machine Vision Association) — 카메라 감도·노이즈·포화·선형성 측정과 표기 방법
- GenICam SFNC (Standard Features Naming Convention) — `ExposureTime`, `Gain`, `TriggerSource` 등 카메라 설정 이름 규약
- 사용하는 카메라 제조사의 SDK 사용 설명서와 Python 예제 (노출·ROI·트리거·User Set 저장)
- 레이저 삼각측량의 스펙클 한계: R. G. Dorsch, G. Häusler, J. M. Herrmann, "Laser triangulation: fundamental uncertainty in distance measurement", Applied Optics, 1994
- IEC 60825-1 — 레이저 제품 안전 등급 (C8 연계)
- 상위 문서 [BLUEPRINT.md](../../BLUEPRINT.md) B1(배율·δz), B4(fps 계산), C1(트리거·스캔 방향), F2 절
