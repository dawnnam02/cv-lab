# B4. 카메라

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: B. 측정 원리·광학 설계

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-13 ~ 2026-11-02 (W2-4) |
| 우선순위 | 높음 |
| 트랙 | 하드웨어 |
| 선행 요소 | [B1 원리](B1-triangulation-principle.md) · [B2 기하 배치](B2-geometry.md) · [B3 상용 vs 자작](B3-commercial-vs-diy.md) · [A2 요구 정밀도](../A-goals/A2-precision-spec.md) |
| 후행 요소 | [B5 렌즈](B5-lens.md) · [B7 필터](B7-filter.md) · [C1 스캔 이동 장치](../C-mechanics/C1-scan-stage.md) (트리거) · [D1 카메라 내부 캘리브레이션](../D-calibration/D1-camera-intrinsics.md) · [F1 라인 중심 추출](../F-acquisition/F1-line-extraction.md) · [F2 획득 파라미터](../F-acquisition/F2-acquisition-params.md) · [F3 저장 형식](../F-acquisition/F3-data-storage.md) |
| 관련 마일스톤 | M0 (부품 목록 확정, 2026-10-19) · 수입 검사 완료 2026-11-02 |

> B3 에서 **상용 프로파일러**를 골랐다면 이 문서는 "카메라 선정" 대신 **프로파일러의 프로파일 속도·ROI·트리거 사양 확인**(3·4절 표의 같은 항목)과 7절 수입 검사 중 해당 항목만 수행합니다.

## 1. 목적

- 측정 정밀도와 속도를 만족하는 **산업용 카메라 1종**을 사양 근거와 함께 선정합니다 (M0, 2026-10-19).
- 필요한 프레임 속도, ROI(읽는 행 범위), 노출 상한, 데이터 전송량을 **계산으로** 정합니다.
- 카메라가 도착하면(W3~4) **수입 검사**(암흑 노이즈, 핫픽셀, 트리거 누락, ROI 속도)를 해서 "이 카메라로 캘리브레이션(D1, W7)을 시작해도 된다"를 확인합니다.

## 2. 배경 지식 (초보자용)

### 2.1 카메라 선택 기준 (BLUEPRINT B4 확장)

| 항목 | 권장 | 이유 |
|---|---|---|
| 셔터 | **글로벌 셔터 (필수)** | 롤링 셔터는 위에서 아래로 줄마다 다른 시각에 찍어서, 움직이며 찍으면 선이 휘어짐 |
| 색상 | **모노크롬** | 컬러 센서(Bayer)는 픽셀 4개 중 1~2개만 레이저 색을 받아 해상도·감도가 떨어짐 |
| 해상도 | 1.3~5 MP | B1: 1.6 MP(1440×1080) 로 FOV 19.9 mm, δx 13.8 µm |
| 픽셀 크기 | 2.5~5.5 µm | 작을수록 분해능 ↑, 대신 픽셀당 빛 ↓ (노이즈 ↑) |
| 비트 깊이 | **10~12 bit 지원** | 어두운 표면에서 서브픽셀 정밀도 ↑ (6.2절) |
| 프레임 속도 | 계산값 이상 (ROI 사용 시) | 6.1절 |
| 트리거 | **하드웨어 트리거 입력** (광절연 입력 권장) | 엔코더 펄스마다 촬영 (C1) |
| 인터페이스·SDK | USB3 Vision 또는 GigE Vision, **Python SDK·예제 제공** | 초보 팀은 Python 예제 유무가 결정적 |
| 마운트 | **C-마운트** | 머신비전 렌즈 선택 폭이 넓음 (B5) |

### 2.2 사양서에서 봐야 할 숫자 (EMVA 1288 데이터)

많은 산업용 카메라 제조사는 **EMVA 1288** 이라는 표준 방식으로 센서 성능을 공개합니다. 같은 기준으로 측정한 값이라 제품끼리 비교할 수 있습니다.

| 항목 | 뜻 | 이 과제에서의 의미 |
|---|---|---|
| 양자효율 QE (405/450 nm 에서) | 들어온 광자 중 전자로 바뀌는 비율 | 청색 레이저(B6)에서 QE 가 낮은 센서는 어두움. **파장별 그래프 확인** |
| 포화 용량 (saturation capacity) | 한 픽셀이 담을 수 있는 최대 전자 수 | 클수록 샷 노이즈 대비 신호가 커짐 |
| 시간 암흑 노이즈 (temporal dark noise) | 빛이 없을 때의 흔들림 [e⁻] | 어두운 표면에서 중요 |
| 동적 범위 (dynamic range) | 포화 / 노이즈 | 밝은 면과 어두운 면이 같이 있을 때 |

### 2.3 프레임 속도, ROI, 노출 시간의 관계

- **필요 프레임 속도** = 스캔 속도 / 스캔 간격. 예: 2 mm/s ÷ 0.02 mm = **100 fps** (BLUEPRINT B4).
- 카메라 최대 fps 는 **읽는 행 수에 반비례**하는 경우가 많습니다. 레이저 선은 측정 깊이 범위에 해당하는 행에만 나타나므로, 그 행만 읽는 **ROI** 를 설정하면 fps 가 올라가고 데이터도 줄어듭니다.
- 필요 행 수 = 측정 깊이 × M × sinθ / p. 기준안(12 mm 깊이)이면 435 행 → 여유 20 % 포함 528 행.
- **노출 시간 상한**: 노출하는 동안 스테이지가 움직이면 선이 Y 방향으로 번집니다. 번짐을 스캔 간격의 1/4 이하로 두면 `노출 ≤ 0.25 × 0.02 mm ÷ 2 mm/s = 2.5 ms`.
- 스텝 & 촬영 방식(C1)에서는 노출 상한이 없지만, 진동이 가라앉을 때까지 대기(예: 0.2 s)해야 합니다.

### 2.4 웹캠으로 시작하면 안 되는 이유

웹캠(UVC)은 자동 노출·자동 화이트밸런스·영상 압축·롤링 셔터 때문에 같은 장면을 찍어도 밝기와 선 위치가 매번 달라집니다. **원리 실습(W1~2, 책상 위 데모)** 용으로만 쓰고 측정 데이터에는 쓰지 않습니다 (BLUEPRINT B4 흔한 실수).

## 3. 입력과 산출물

| 구분 | 항목 | 형식 / 파일 | 비고 |
|---|---|---|---|
| 입력 | 광학 설계 사양표 | `config/hardware/optical_design.yaml` (B1·B2) | 픽셀 크기, 해상도, M, θ, 측정 깊이 |
| 입력 | 스캔 속도·간격·길이 | C1 초안 | 기준: 2 mm/s, 0.02 mm, 50 mm |
| 입력 | 예산 | K3 (카메라 대략 50만~150만 원, **견적 필요**) | |
| 산출물 | 요구 사양 계산 스크립트 | `scripts/design/b4_camera_req.py` | 6.1절 |
| 산출물 | 카메라 후보 비교표 (2종 이상) | `results/design/B4_camera_candidates.csv` | 10절 양식 |
| 산출물 | 선정 카메라 사양 기록 | `config/hardware/camera.yaml` | 모델, 시리얼, 펌웨어, SDK 버전 |
| 산출물 | 수입 검사 데이터 | `data/raw/acceptance/camera/<날짜>/dark_*.npy`, `trigger_log.csv` | 원본 보존 |
| 산출물 | 수입 검사 보고 | `results/acceptance/B4_camera_report.md` | 7절 기준 합격/불합격 |
| 산출물 | 카메라 제어 모듈 (뼈대) | `src/cvlab/acquisition/camera.py` | 6.4절 구조 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 셔터 | 글로벌 / 롤링 | **글로벌** | 연속 스캔 중 선 휨 방지 |
| 색상 | 모노 / 컬러 | **모노** | 감도·해상도 |
| 해상도·픽셀 | 1.6 MP 3.45 µm / 5 MP 2.74 µm / 기타 | **1.6 MP, 3.45 µm** (기준안) | B1 합격선 충족, 데이터량이 5 MP 의 약 1/3 |
| 비트 깊이 (운용) | 8 bit / 12 bit | **12 bit 지원 모델, 운용은 Mono12 기본** | 어두운 면(피크 5 %)에서 중심 오차 0.048 → 0.035 px (6.2절) |
| ROI | 전체 / 측정 깊이만 | **측정 깊이 행 + 20 %** (기준 528 행) | fps ↑, 전송량 156 → 76 MB/s |
| 인터페이스 | USB3 Vision / GigE Vision | **USB3** (케이블 ≤ 3 m 가능 시) | 전송 여유 큼. 거리가 멀면 GigE |
| 트리거 | 소프트웨어 / 하드웨어 | **하드웨어 (엔코더 또는 스텝 신호)** | 위치 기반 촬영 (C1) |
| 촬영 방식 (초기) | 연속 + 위치 트리거 / 스텝 & 촬영 | **스텝 & 촬영으로 시작 → 연속으로 확장** | 초보에게 단순, 노출 제약 없음 |
| SDK | 제조사 Python SDK / GenICam 범용 라이브러리 | **제조사 Python SDK** (예제 확인 후) | 문서·지원 |

## 5. 수행 절차

1. **요구 사양 계산 (W2, 2026-10-13 ~ 10-14)**
   - [ ] 6.1절 스크립트에 B1·B2·C1 값을 넣어 fps, ROI 행 수, 노출 상한, 전송량을 계산한다.
   - [ ] 결과를 "카메라 최소 요구표"로 정리: 글로벌 셔터, 모노, ≥ 1440×1080, 픽셀 2.5~5.5 µm, ROI 528 행에서 ≥ 100 fps(여유 포함 ≥ 150 fps 권장), 12 bit, 하드웨어 트리거, Python SDK.
2. **후보 조사 (W2, 10-14 ~ 10-16)**
   - [ ] 조건을 만족하는 후보 **2종 이상**을 찾아 10절 비교표를 채운다. 사양서·EMVA 1288 데이터 PDF 를 `docs/procurement/datasheets/` 에 저장한다.
   - [ ] 각 후보로 B1 계산기(`b1_spec.py`)를 다시 돌려 합격선을 확인한다.
   - [ ] 405/450 nm 에서의 QE 를 그래프에서 읽어 기록한다 (B6 파장 결정과 연동).
   - [ ] 공급사에 견적·납기·Python 예제 제공 여부를 확인한다.
3. **선정과 주문 (W2 말 ~ W3 초, 10-16 ~ 10-20)**
   - [ ] 비교표와 근거를 M0 회의(10-19 주)에 보고하고 1종을 확정한다.
   - [ ] 렌즈(B5)·필터(B7)·트리거 케이블·전원·USB3 케이블(잠금형 나사 커넥터 권장)을 함께 주문한다.
4. **소프트웨어 준비 (도착 전, W3)**
   - [ ] 제조사 SDK 를 설치하고 예제 프로그램으로 가상 카메라(지원 시) 또는 시뮬레이션 모드를 실행해 본다.
   - [ ] 6.4절 구조로 `camera.py` 뼈대를 작성한다 (노출·게인·ROI·트리거·픽셀 형식 설정 함수).
5. **수입 검사 (도착 후 W3~W4, 11-02 까지)**
   - [ ] 외관·시리얼 번호 기록, 펌웨어 버전 기록 → `camera.yaml`.
   - [ ] **암흑 시험**: 렌즈 캡 + 실험 노출(예: 800 µs)·게인 0 dB 로 100장 → 6.3절 스크립트로 시간 노이즈, DSNU, 핫픽셀 계산.
   - [ ] **트리거 시험**: 함수 발생기 또는 스테이지 컨트롤러에서 펄스 1000개(100 Hz) → 받은 프레임 수와 프레임 번호 연속성 확인 (누락 0).
   - [ ] **ROI 속도 시험**: ROI 528 행, Mono12 에서 실제 최대 fps 측정 (60초 연속, 누락 0).
   - [ ] **선형성 간이 시험**: 고정된 레이저 선을 노출 100, 200, 400, 800 µs 로 찍어 피크 밝기가 노출에 비례하는지 (상관 R² ≥ 0.99, 포화 전 구간).
   - [ ] 결과를 `B4_camera_report.md` 에 정리하고 합격 판정.
6. **설정 고정 (W4 말)**
   - [ ] 자동 노출·자동 게인·감마·샤프닝 등 **모든 자동/보정 기능 끄기**를 확인하고 설정을 `config/hardware/camera.yaml` 에 저장한다.
   - [ ] 카메라를 브래킷에 고정한 뒤 이 설정으로 D1 을 시작할 수 있음을 D 담당에게 알린다.

## 6. Python 구현

### 6.1 요구 사양 계산 (`b4_camera_req.py`)

```python
# b4_camera_req.py — 카메라 요구 사양 계산: fps, ROI 행 수, 노출 상한, 데이터량 (B4)
# 실행: python b4_camera_req.py
import numpy as np

# ---- 입력 (A2, B1, B2, C1 에서 가져온 값) ----
pixel_um = 3.45
n_cols, n_rows = 1440, 1080
M = 0.25
theta_deg = 30
z_range_mm = 12.0          # 필요한 측정 깊이 범위 (시편 높이 + 여유)
scan_pitch_mm = 0.02       # 스캔 간격
scan_speed_mm_s = 2.0      # 스캔 속도
scan_length_mm = 50.0      # 스캔 길이
blur_fraction = 0.25       # 노출 중 이동량을 스캔 간격의 몇 배까지 허용할지
bit_depth = 8              # 저장 비트 수 (8 또는 16 컨테이너에 12bit)

# ---- 계산 ----
fps_needed = scan_speed_mm_s / scan_pitch_mm
rows_needed = int(np.ceil(z_range_mm * M * np.sin(np.radians(theta_deg)) / (pixel_um / 1000)))
rows_roi = int(np.ceil(rows_needed * 1.2 / 16) * 16)   # 20 % 여유 + 16행 단위 반올림(카메라 제약 흔함)
exposure_max_us = blur_fraction * scan_pitch_mm / scan_speed_mm_s * 1e6
n_frames = int(scan_length_mm / scan_pitch_mm)
bytes_per_px = 1 if bit_depth == 8 else 2
mb_per_s_full = fps_needed * n_cols * n_rows * bytes_per_px / 1e6
mb_per_s_roi = fps_needed * n_cols * rows_roi * bytes_per_px / 1e6
gb_per_scan_roi = n_frames * n_cols * rows_roi * bytes_per_px / 1e9

print(f"필요 프레임 속도          : {fps_needed:.0f} fps")
print(f"측정 깊이 {z_range_mm} mm 에 필요한 행 : {rows_needed} 행 -> ROI {rows_roi} 행 권장")
print(f"노출 시간 상한(흐림 {blur_fraction}·간격): {exposure_max_us:.0f} us")
print(f"스캔 1회 프레임 수        : {n_frames} 장, 소요 {scan_length_mm / scan_speed_mm_s:.0f} s")
print(f"전송량 (전체 프레임)      : {mb_per_s_full:.0f} MB/s")
print(f"전송량 (ROI)              : {mb_per_s_roi:.0f} MB/s")
print(f"스캔 1회 원본 용량 (ROI)  : {gb_per_scan_roi:.2f} GB")
print("참고: USB3 실효 대역 ≈ 300~400 MB/s, GigE ≈ 100~115 MB/s (대략)")
```

실행 예시와 기대 출력:

```
$ python b4_camera_req.py
필요 프레임 속도          : 100 fps
측정 깊이 12.0 mm 에 필요한 행 : 435 행 -> ROI 528 행 권장
노출 시간 상한(흐림 0.25·간격): 2500 us
스캔 1회 프레임 수        : 2500 장, 소요 25 s
전송량 (전체 프레임)      : 156 MB/s
전송량 (ROI)              : 76 MB/s
스캔 1회 원본 용량 (ROI)  : 1.90 GB
참고: USB3 실효 대역 ≈ 300~400 MB/s, GigE ≈ 100~115 MB/s (대략)
```

읽는 법: 전체 프레임(1080 행)을 100 fps 로 읽으면 156 MB/s 로 GigE(대략 100~115 MB/s)를 넘습니다. ROI(528 행)를 쓰면 76 MB/s 로 줄어 두 인터페이스 모두 가능합니다. 12 bit 로 저장하면(2바이트 컨테이너) 전송량이 2배가 되므로 `bit_depth = 12` 로 바꿔 다시 확인합니다.

### 6.2 비트 깊이와 밝기가 중심 정밀도에 주는 영향 (`b4_bitdepth.py`)

```python
# b4_bitdepth.py — 비트 깊이·밝기가 서브픽셀 중심 정밀도에 주는 영향 시뮬레이션 (B4)
# 가우시안 모양 레이저 단면 + 광자(샷) 노이즈 + 읽기 노이즈 → 양자화 → 무게중심 → 오차 표준편차
# 실행: python b4_bitdepth.py
import numpy as np

rng = np.random.default_rng(0)
FULL_WELL_E = 10000      # 포화 전자 수 (카메라 사양서 'saturation capacity', 예시 값)
READ_NOISE_E = 3.0       # 읽기 노이즈 [전자] (예시 값)
SIGMA_PX = 1.2           # 레이저 단면 가우시안 σ [px] → 두께(FWHM) ≈ 2.8 px
N_TRIAL = 3000


def centroid_std(peak_fraction, bits):
    """피크 밝기가 포화의 peak_fraction 배일 때 무게중심 오차 표준편차 [px]"""
    rows = np.arange(-8, 9)
    true_c = rng.uniform(-0.5, 0.5, N_TRIAL)                       # 참 중심 (무작위 서브픽셀 위치)
    profile = np.exp(-0.5 * ((rows[None, :] - true_c[:, None]) / SIGMA_PX) ** 2)
    electrons = rng.poisson(profile * peak_fraction * FULL_WELL_E).astype(float)
    electrons += rng.normal(0, READ_NOISE_E, electrons.shape)
    levels = 2 ** bits - 1
    dn = np.clip(np.round(electrons / FULL_WELL_E * levels), 0, levels)   # 디지털 값(DN)
    thr = 0.1 * dn.max(axis=1, keepdims=True)                     # 피크의 10 % 를 문턱값으로
    w = np.clip(dn - thr, 0, None)
    est = (w * rows).sum(axis=1) / w.sum(axis=1)
    return np.std(est - true_c)


if __name__ == "__main__":
    print("피크 밝기(포화 대비) |  8bit 오차[px] | 12bit 오차[px]")
    for frac in (0.05, 0.2, 0.5, 0.85):
        s8, s12 = centroid_std(frac, 8), centroid_std(frac, 12)
        print(f"        {frac * 100:4.0f} %      |     {s8:.4f}     |     {s12:.4f}")
```

실행 예시와 기대 출력:

```
$ python b4_bitdepth.py
피크 밝기(포화 대비) |  8bit 오차[px] | 12bit 오차[px]
           5 %      |     0.0481     |     0.0354
          20 %      |     0.0202     |     0.0185
          50 %      |     0.0133     |     0.0131
          85 %      |     0.0110     |     0.0109
```

읽는 법: 선이 충분히 밝으면(피크 50 % 이상) 8 bit 와 12 bit 차이는 거의 없습니다. 어두운 표면(피크 5 %)에서는 12 bit 가 약 25 % 좋습니다. 또 **밝기를 포화 직전(85 %)까지 올리는 것이 비트 깊이보다 훨씬 효과가 큽니다** (0.048 → 0.011 px). 이 시뮬레이션에는 스펙클이 없으므로 실제 오차는 더 큽니다 (B6). 포화(100 %)는 중심을 왜곡하므로 피크는 90 % 이하로 맞춥니다 (F1).

### 6.3 수입 검사: 암흑 영상 분석 (`b4_dark_test.py`)

```python
# b4_dark_test.py — 카메라 수입 검사: 암흑 영상으로 시간 노이즈, 고정 패턴, 핫픽셀 계산 (B4)
# 실제: 렌즈 캡을 씌우고 실험과 같은 노출·게인으로 100장 촬영 → frames (100, H, W) 배열
# 여기서는 합성 데이터로 함수가 맞게 동작하는지 확인한다. (정답: 노이즈 2.0 DN, 핫픽셀 25개)
# 실행: python b4_dark_test.py
import numpy as np


def make_synthetic_dark(n=100, h=120, w=160, seed=7):
    rng = np.random.default_rng(seed)
    offset = 16 + rng.normal(0, 0.8, (h, w))               # 픽셀마다 조금 다른 바탕값 (고정 패턴)
    hot_idx = rng.choice(h * w, 25, replace=False)
    offset.flat[hot_idx] += 60                              # 핫픽셀 25개
    frames = offset[None] + rng.normal(0, 2.0, (n, h, w))   # 시간 노이즈 σ = 2.0 DN
    return np.clip(np.round(frames), 0, 4095)


def dark_report(frames, hot_k=6.0):
    mean_img = frames.mean(axis=0)                          # 픽셀별 평균 (고정 패턴)
    temporal = frames.std(axis=0, ddof=1).mean()            # 픽셀별 시간 표준편차의 평균
    med = np.median(mean_img)
    mad = np.median(np.abs(mean_img - med)) * 1.4826        # 이상치에 강한 표준편차 추정
    hot = mean_img > med + hot_k * max(mad, 1e-9)
    dsnu = mean_img[~hot].std()                             # 핫픽셀 뺀 고정 패턴 흩어짐
    return {"바탕 평균[DN]": round(float(med), 2), "시간 노이즈[DN]": round(float(temporal), 2),
            "고정 패턴 DSNU[DN]": round(float(dsnu), 2), "핫픽셀 수": int(hot.sum()),
            "핫픽셀 비율[%]": round(100 * hot.mean(), 3)}


if __name__ == "__main__":
    frames = make_synthetic_dark()
    for k, v in dark_report(frames).items():
        print(f"{k:16s}: {v}")
```

실행 예시와 기대 출력 (합성 데이터의 정답: 노이즈 2.0 DN, 핫픽셀 25개):

```
$ python b4_dark_test.py
바탕 평균[DN]       : 15.99
시간 노이즈[DN]      : 2.01
고정 패턴 DSNU[DN]  : 0.82
핫픽셀 수           : 25
핫픽셀 비율[%]       : 0.13
```

실제 카메라에서는 `frames = np.stack([...100장...])` 을 만든 뒤 `dark_report(frames)` 만 호출합니다. 데이터는 `np.save("data/raw/acceptance/camera/2026-10-28/dark_800us_0dB.npy", frames)` 로 원본을 보존합니다.

### 6.4 카메라 제어 모듈 구조 — 예시 구조(하드웨어 SDK 필요, 그대로 실행 불가)

아래는 GenICam 표준 기능 이름(SFNC: `ExposureTime`, `Gain`, `PixelFormat`, `TriggerMode` 등)을 쓰는 **구조 예시**입니다. `sdk` 부분은 선택한 제조사 SDK 의 실제 함수로 바꿔야 합니다.

```python
# src/cvlab/acquisition/camera.py — 예시 구조 (제조사 SDK 로 바꿔 구현)
import yaml


class AreaCamera:                                  # 면(area) 카메라. "라인스캔 카메라"와 다름
    def __init__(self, sdk_device):
        self.dev = sdk_device                       # 제조사 SDK 의 장치 객체

    def apply_config(self, path="config/hardware/camera.yaml"):
        cfg = yaml.safe_load(open(path, encoding="utf-8"))
        n = self.dev.nodes                          # GenICam 노드 접근 (SDK 마다 문법 다름)
        n["ExposureAuto"] = "Off"                   # 자동 노출 끄기 (필수)
        n["GainAuto"] = "Off"
        n["PixelFormat"] = cfg["pixel_format"]      # 예: "Mono12"
        n["ExposureTime"] = cfg["exposure_us"]      # µs
        n["Gain"] = cfg["gain_db"]
        n["Height"] = cfg["roi"]["height"]          # ROI: 높이 → 오프셋 순서로 설정
        n["OffsetY"] = cfg["roi"]["offset_y"]
        n["TriggerMode"] = "On"
        n["TriggerSource"] = cfg["trigger"]["source"]       # 예: "Line0"
        n["TriggerActivation"] = cfg["trigger"]["activation"]  # 예: "RisingEdge"

    def grab(self, n_frames, timeout_ms=1000):
        """트리거마다 1장씩 받아 (영상, 프레임 번호, 타임스탬프) 목록으로 돌려줌"""
        out = []
        for _ in range(n_frames):
            buf = self.dev.fetch(timeout_ms)        # SDK 함수 이름은 제조사마다 다름
            out.append((buf.image.copy(), buf.frame_id, buf.timestamp))
        return out
```

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 요구 사양 충족 (설계) | 6.1절 + 사양서 | 글로벌·모노·12 bit·하드웨어 트리거·Python SDK 모두 "예", ROI 528 행에서 사양 fps ≥ 150 |
| B1 합격선 | `b1_spec.py` | 선정 모델로 δz/10 ≤ 3 µm, δx ≤ 20 µm, FOV_x ≥ 19.6 mm |
| 암흑 시간 노이즈 | 6.3절 | 사양서(EMVA) 값의 1.5배 이하 |
| 핫픽셀 | 6.3절 | ≤ 0.1 % 이고 ROI 중앙 영역에 군집(3×3 이상) 없음 |
| 트리거 누락 | 펄스 1000개 | 누락 0, 프레임 번호 연속 |
| ROI 연속 촬영 | 60초 | 실제 fps ≥ 필요 fps × 1.2 (= 120), 누락 0 |
| 노출 선형성 | 노출 4단계 | 피크 밝기 vs 노출 R² ≥ 0.99 |
| 설정 고정 | `camera.yaml` | 자동 기능 모두 Off 확인, 설정 파일로 재현 가능 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 자동 노출·자동 게인 켜진 채 측정 | 스캔 중 밝기가 바뀌고 중심 위치가 흔들림 | `ExposureAuto=Off`, `GainAuto=Off` 를 코드에서 강제, 시작 시 값 기록 |
| 감마·샤프닝·노이즈 저감 켜짐 | 선 단면이 비대칭 → 중심 치우침 | 모든 영상 보정 기능 Off (사양서의 ISP 항목 확인) |
| 8 bit 로 저장하면서 12 bit 라고 기록 | 메타데이터와 실제 불일치 | 저장 시 `dtype`·최댓값 자동 검사 |
| USB 허브·긴 케이블 사용 | 프레임 누락, 연결 끊김 | 메인보드 직결 포트, 규격 케이블, 트리거 시험으로 확인 |
| ROI 를 바꾼 뒤 캘리브레이션 재사용 | 픽셀 좌표가 오프셋만큼 어긋남 | **ROI 는 D1 전에 확정**. 바꾸면 v 좌표에 `OffsetY` 를 더해 전체 센서 좌표로 저장 |
| 소프트웨어 트리거로 연속 스캔 | 위치 간격이 들쭉날쭉 (속도 변동) | 하드웨어(엔코더) 트리거 또는 스텝 & 촬영 |
| 포화된 상태로 측정 | 선 피크가 평평 → 중심 부정확 | 피크 ≤ 90 % 규칙 (F1), 포화 픽셀 수 자동 계산 |
| 컬러 카메라 구매 | 해상도·감도 저하 | 주문서에 "Mono" 명시, 모델명 재확인 |

## 9. 위험 요소

- **납기 지연**: 카메라 도착이 W6(2026-11-16)을 넘기면 D1(W7) 이 늦어집니다. → 주문 시 납기 확인, 재고 모델 우선. 지연 시 W5~6 에 원리 실습용 대체 카메라로 소프트웨어(F1)만 먼저 진행.
- **청색 파장 감도 부족**: 일부 센서는 405 nm QE 가 낮습니다. B6 에서 405 nm 를 고르면 QE 를 반드시 확인하고, 낮으면 450 nm 로 조정합니다.
- **SDK 호환성**: Python 버전·OS 와 SDK 지원 범위가 맞지 않을 수 있습니다. 구매 전 지원 Python 버전을 확인하고 [J2](../J-software/J2-config-reproducibility.md) 의 가상환경에 맞춥니다.
- **발열**: 카메라 하우징이 데워지며 센서·렌즈 위치가 미세하게 변합니다. 30분 워밍업(C6) 후 측정합니다.

## 10. 기록 양식

카메라 후보 비교표 (`results/design/B4_camera_candidates.csv`)

| 후보 | 셔터 | 모노 | 해상도 | 픽셀[µm] | 최대 비트 | QE@405 | QE@450 | 포화용량[e⁻] | 암흑노이즈[e⁻] | fps(전체) | fps(ROI 528) | 트리거 | 인터페이스 | Python SDK | 견적(원) | 납기(주) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | | | | | |

`config/hardware/camera.yaml`

```yaml
model: ""
serial: ""
firmware: ""
sdk: {name: "", version: ""}
interface: USB3
pixel_um: 3.45
sensor: {cols: 1440, rows: 1080}
pixel_format: Mono12
exposure_us: 800
gain_db: 0
roi: {offset_y: 0, height: 528}     # 측정 깊이 0~12 mm 에 맞춰 조정
trigger: {mode: "On", source: "Line0", activation: "RisingEdge"}
auto_functions_off: [ExposureAuto, GainAuto, Gamma, Sharpness]
acceptance:
  date: null
  temporal_dark_noise_dn: null
  dsnu_dn: null
  hot_pixel_pct: null
  trigger_test: {pulses: 1000, frames: null}
  roi_fps_measured: null
  exposure_linearity_r2: null
  result: null                      # PASS / FAIL
```

## 11. 참고 자료

- EMVA 1288 Standard for Characterization of Image Sensors and Cameras (European Machine Vision Association)
- GenICam 표준과 SFNC (Standard Features Naming Convention), USB3 Vision·GigE Vision 표준 (A3 / EMVA 관리)
- 선택한 카메라 제조사의 Python SDK 문서와 예제
- OpenCV 공식 문서 "Camera Calibration" 튜토리얼 (D1 연계)
- 영상 센서 기초: 샷 노이즈·읽기 노이즈·양자화 (영상처리·광학 계측 교과서의 "image sensor noise" 단원)
