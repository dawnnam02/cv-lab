# 세부청사진 T7a · 레이저 선 추출 1차 (F1)와 좌표계 (C4)

> 상위: [청사진_가상데이터단계](청사진_가상데이터단계.md) §1 (측정 방식) · §2.1 (2 실측) · §4.1 (T7) · §4.3 (T7) · §5.2 · 작성: 2026-10-27 총괄 팀장 · 상태: **착수 전 (메인 확인 대기)**
> **일정 앞당김.** 청사진 T7은 11-25 ~ 12-04 (G1 · T3 뒤)입니다. 사용자 지시 (10-27) "선행 작업 없이 병렬로 진행할 수 있는 작업 진행해."에 따라 시뮬레이터 없이 할 수 있는 몫만 떼어 **10-27에 시작해 11-03에 마감**합니다 (29일 앞당김). T4b · T5와 동시에 돕니다.
> **청사진과 다른 점 (청사진은 고치지 않음, 메인에게 보고).**
> ① **T7을 둘로 나눕니다.** T7a (지금) = F1 선 중심 추출 (worker가 만든 단순 합성 영상으로) + C4 좌표계 문서와 변환 함수 뼈대 (교정값은 인자로). T7b (G1 뒤, 11-25 ~) = 시뮬레이터 데이터로 정지 평판 100장 반복성 표 · 채점기 기준 프로파일 오차 표 · 교정값을 넣은 삼각측량. 청사진 §4.3 T7 완료 기준 두 개는 T7b에 남습니다.
> ② 산출물 경로: 모듈 `src/cvlab/triangulation.py` → 패키지 `src/cvlab/triangulation/`. 세 작업이 동시에 코드를 써서 폴더 단위로 소유를 나누기 위해서입니다 (T15와 같은 이유).
> ③ 카메라: F1 요소 청사진 예시 (1080 × 1440 · 8비트)가 아니라 **OV9281 1280 × 800 · 10비트** (청사진 §1, 명세 `frame.bit_depth` 예시 10)를 기준으로 합니다. F1 기준 숫자와 비교하려고 8비트 시나리오 하나를 같이 돌립니다.
> ④ 이 작업의 정확도 숫자는 "단순 합성 영상에서 알고리즘이 어떻게 도는가"입니다. **C4 · C5 (교정 · 종단 정확도)의 증거가 아닙니다.** 그 판정은 T3 평가용 세트와 채점기로만 합니다 (청사진 §5.2).
> **명세가 바뀌는 중.** T1 2차 결과가 884daac (10-27 20:40)로 들어왔지만 상태는 "2차 보완 끝, 팀장 검토 전"입니다. 1절 frame 묶음도 바뀌었습니다 (`frame.trigger_mode`에 gate, 새 필드 `frame.trig_pulse_idx` · `frame.gate_on`). 팀장 검토 뒤 더 바뀔 수 있고, T6 후속 worker가 `src/cvlab/io/`를 새 명세에 맞추는 중입니다. 둘 다 읽기만 합니다. **읽기 함수는 얇게** 만들고, 쓰는 필드 이름은 한 상수 (`SPEC_FRAME_COLUMNS`)에만 둡니다. 끝날 때 명세를 다시 보고 바뀐 필드를 대조표에 적습니다.
> **정보 차단 (이 작업은 처리 담당).** `data/_truth/`와 `src/cvlab/sim/`은 읽지 않습니다 (생기더라도). T5 시나리오 산출물 (`docs/판정-시나리오*` · `config/scenarios/` · `scripts/scenario_expected.py`)도 읽지 않습니다. 명세 부록 A의 `truth.*` **필드 정의 (뜻)** 는 좌표계 문서를 위해 읽어도 됩니다. 값이 든 파일은 열지 않습니다.
> 함께 도는 작업: [T4b 판정 영역](세부청사진_T4b_판정영역.md) · [T5 G코드 점검·시나리오](세부청사진_T5_G코드점검·시나리오.md). **§5 소유 표를 지킵니다.**

| 항목 | 내용 |
|---|---|
| Plane | F1 · C4 (D-17 재구성 뒤 목표 3 "실측 만들기"의 단계 줄). 상태 바꾸기는 메인 몫 |
| 담당 | 광학처리 담당 (청사진 §5.1, 이번이 첫 투입), Opus 5.5, effort medium. 독립 검증: 팀장 |
| 기간 | 2026-10-27 ~ 11-03 |
| 선행 | 없음. 명세 1절 (frame) · 0.4절 (좌표계, 높이 식)은 읽기만 |
| 후행 | T7b (시뮬레이터 데이터로 정확도) · T8 (D1 · D2 · D3 · D4 교정값이 이 변환 뼈대의 인자를 채움) · T9 (점 → 높이 지도) · T6 SV13 (명세 동결 뒤 읽기 함수 대조) |
| 산출물 | §4 경로 · `docs/운영/결과_T7a_대조표.md` |

## 1. 목적

1. **선 중심 추출 (F1).** 원시 프레임 (1280 × 800 모노, ROI 가능)의 **열 u마다** 레이저 선 중심 행 v를 서브픽셀로 찾습니다. 방법 여러 개를 같은 시험 영상에서 비교하고 기본 방법을 숫자로 고릅니다. 포화 · 다중 피크 (반사) · 선 없음을 처리하고, 점마다 품질 지표와 표시 비트를 남깁니다.
2. **좌표계 (C4).** {I}{C}{S}{M}{G} 다섯 좌표계를 명세 0.4절과 맞춰 문서로 정의하고, 영상 점을 {G} 점으로 바꾸는 변환 사슬을 함수 뼈대로 만듭니다. 교정값은 모두 인자로 받습니다 (기본값 없음). 실제 교정은 T8입니다.
3. **얇은 읽기.** 명세 frame 묶음 (`frames_index.csv` + `frames/*.png` 또는 `frames.npz`)을 읽는 최소 함수.

선 중심 오차는 그대로 높이 오차가 됩니다 (F1 §1). 1 px은 약 31.6 µm 높이입니다 [계산: 3 µm ÷ (배율 0.19 × sin 30°), §6.6 가정]. 그래서 치우침 (bias)을 0.02 px (약 0.6 µm) 아래로 묶습니다.

## 2. 목표 (완료 기준)

| 번호 | 완료 기준 | 측정 방법 |
|---|---|---|
| LX1 | **방법 ≥ 5개, 한 함수로.** `extract_centers(img, method=…)`: `max` · `cog` · `parabola3` · `gauss3` · `steger` (필수) + `gaussfit` (선택). 출력 `v` float32 (ROI 행 좌표, 못 찾으면 NaN)와 `flags` uint8 (§6.4) | 시험 |
| LX2 | **기본 정확도 (F1 7절 #1 · #2).** `f1_basic_8bit` · `nominal_10bit` (§6.3)에서 `cog` \|bias\| < 0.02 px, RMS < 0.15 px, 유효 100 %. `noiseless_10bit`에서 `gauss3` 최대 오차 < 0.05 px | 명령 ② |
| LX3 | **비교표.** `docs/레이저선-추출_자료/방법비교.csv` (§6.3 시나리오 전부 × 방법, 열 고정). RMS를 µm로 바꾼 열 (§6.6 환산). 정지 100장 열별 표준편차 중앙값 (보고만) | 명령 ② |
| LX4 | **포화.** `saturated_10bit` (피크 1600 DN → 1023에서 잘림)에서 기본 방법 \|bias\| < 0.05 px, 포화 화소가 있는 열에 `saturated` 비트 100 % | 명령 ② · 시험 |
| LX5 | **다중 피크 (반사, F1 7절 #3).** `reflection_10bit` (21열, 진짜 선보다 밝은 가짜 피크)에서 연속성 안내를 켠 기본 방법 P95 < 0.3 px. 그 열의 `multi_peak` 비트 ≥ 95 %. 안내를 끈 결과도 함께 적음 | 명령 ② · 시험 |
| LX6 | **선 없음 (F1 7절 #4).** `no_line_10bit`의 레이저 없는 열 200개에서 값 낸 수 0 (가짜 값 0 %), `no_line` 비트 100 %. 문턱 아래 약한 신호도 NaN + 비트 | 명령 ② · 시험 |
| LX7 | **품질 지표.** `line_quality`: 열마다 `peak_dn` · `fwhm_px` · `n_sat` · `n_peaks` · `snr`. 표시 비트 6개 (§6.4) 각각을 켜는 시험이 하나 이상 | 시험 |
| LX8 | **가우시안이 아닌 단면 (모델 분리의 작은 판).** `skewed_10bit` (가우시안 ⊗ 한쪽 지수 꼬리)에서 방법마다 bias를 보고. 통과 문턱은 없음. 문서에 "T7b에서 T3 단면으로 다시 잼"과 꼬리 쪽 치우침의 부호 · 크기 | 명령 ② · 문서 §4 |
| LX9 | **ROI · 비트.** `roi_to_full(v, roi_y0_px)` = v + roi_y0. 전체 영상에서 잘라 낸 ROI의 결과를 전체 행 좌표로 바꾸면 전체 영상 결과와 같음 (차 < 1e-4 px). 8비트 · 10비트 (16비트 그릇, 아래 비트 정렬) 모두. 포화값 = 2^bit_depth − 1 | 시험 · 명령 ③ |
| LX10 | **속도 (F1 7절 #7).** 기본 방법 ROI 1280 × 256 한 장 ≤ 15 ms, 전체 1280 × 800 한 장 ≤ 30 ms (= 2,000장 60 s) [추정: F1 기준을 이 PC numpy에 맞춤]. 중앙값 20회. 다른 방법은 보고만 | 명령 ② |
| LX11 | **좌표계 문서.** `docs/좌표계.md` 절 0–9 (§4 목차). 다섯 좌표계 표가 명세 0.4절과 같음 ({S} x = 레이저 선 = 프린터 X, {M} y = 스캔 = 프린터 Y, z 위 +). 이름 규칙 `T_<to>_<from>`. 사슬의 고리마다 교정값 이름 · 단위 · 정하는 교정 단계 (D1 – D5) · 명세 필드 (뜻). 명세 0.4절 높이 식과의 관계 (Z_n · d_s · 메시 항은 T9) | 명령 ⑤ |
| LX12 | **변환 뼈대.** `Tf`: 이름 안 맞는 곱 · det(R) ≠ +1 · 직교 아님 → ValueError (100 %), 왕복 < 1e-9 mm. `distort_points` = OpenCV 순서 (k1, k2, p1, p2, k3) 식과 차 < 1e-12, `undistort_points` 왕복 < 1e-9 (정규 좌표). `image_to_G`가 합성 기하에서 {G} 점을 1e-6 mm 안으로 되찾음. 교정값이 빠지면 오류 (기본값 없음) | 명령 ④ · 시험 |
| LX13 | **얇은 읽기.** `read_frames_index(scan_dir)` · `load_frame(scan_dir, row)`: PNG 16비트 · 8비트와 `frames.npz#f000000`. 필수 열은 `SPEC_FRAME_COLUMNS` 한 곳, 모르는 열은 그대로 통과, 필수 열이 없으면 그 열 이름을 담은 ValueError. `laser_on`은 bool로. 시험은 `tmp_path`에서만 (`data/raw/`에 쓰지 않음) | 시험 · 명령 ③ |
| LX14 | **추출 문서.** `docs/레이저선-추출.md` 절 0–10 (§4 목차). 기본 방법과 설정값을 숫자로 고른 근거 (§6.5) | 명령 ⑤ |
| LX15 | **시험 · 차단.** `tests/triangulation/` 시험 함수 ≥ 30개 모두 통과, 120 s 이내. `cvlab.gcode` · `cvlab.judge` · `cvlab.io` · `cvlab.sim` · `cvlab.region` import 0. `cv2` · `skimage` import 0 (`requirements.txt` 밖). `_truth` · 시나리오 경로 언급 0. 소유 위반 0, V2 지문 같음 | 명령 ① · ⑥ · ⑦ · ⑧ |

## 3. 입력

| 입력 | 경로 | 쓰는 곳 |
|---|---|---|
| 요소 청사진 | `docs/blueprints/F-acquisition/F1-line-extraction.md` (§4 결정: CoG 기본, 창 1.5 × FWHM, 문턱 배경 + 5σ, 연속성 안내 51열 · 8 px, 신뢰도 기준 · §6 코드 예 · §7 기준 · §8 흔한 실수) · `docs/blueprints/C-mechanics/C4-coordinate-frames.md` (§2 좌표계 표 · §4 결정 · §6 `Tf` 예 · §7 기준) · `B1-triangulation-principle.md` · `B2-geometry.md` · `D1` – `D4` (교정값 이름) | LX1 – LX12 |
| 명세 (읽기만, 바뀌는 중, 884daac 기준) | `docs/하드웨어-데이터-명세.md` 0.3 (단위) · 0.4 (좌표계 · 높이 식 · 시계 표의 트리거 펄스 번호) · 1절 (frame 필드표, `frame.trig_pulse_idx` 포함) · 5절 (`meta.cam_res_*` · `meta.magnification` · `meta.triang_angle_deg` · `meta.scan_pitch_mm`) · 부록 A (`truth.cam_k` · `cam_dist` · `laser_plane` · `scan_axis` · `t_g_m` · `nozzle_sensor_offset_mm`의 **뜻만**) | LX9 · LX11 – LX13 |
| 청사진 | §1 측정 방식 (OV9281 1280 × 800 · 3 µm, f8 f/4, WD 50 mm, 배율 0.19, 450 nm 수직 + 카메라 30°, 시야 약 20 mm, 심도 약 8 mm) · §8 공통 규칙 (단위 · 각도 · 좌표) | 전부 |
| 펌웨어 | `docs/프린터-펌웨어-선정.md` §9 프레임 시각 경로 (ⓐ 펄스 번호 → y = y0 + 0.02 mm × k) | LX11 (스캔 위치 s의 출처) |
| 실패사례 | `docs/측정-실패사례.md` MF-OPT-02 (엣지 혼합) · MF-OPT-06 (다중 반사) · MF-SIM-03 (이상치 꼬리) · MF-SYN-06 (모션 블러) · MF-DAT 묶음 | LX4 – LX8 문서 |

- 시험 영상은 **worker가 직접 만든 단순 합성 영상**만 씁니다 (§6.3). 다른 데이터는 없습니다.

## 4. 산출물

| 경로 | 내용 |
|---|---|
| `src/cvlab/triangulation/__init__.py` | 아래 공개 이름을 내보냄 |
| `src/cvlab/triangulation/params.py` | `TriParams` (기본값 = `config/triangulation.yaml`, 모르는 키 오류) |
| `src/cvlab/triangulation/extract.py` | 방법 6개 · 연속성 안내 · `extract_centers` · `roi_to_full` |
| `src/cvlab/triangulation/quality.py` | `line_quality` · `FLAG` |
| `src/cvlab/triangulation/frames.py` | `Tf` (C4) |
| `src/cvlab/triangulation/geometry.py` | `distort_points` · `undistort_points` · `pixel_to_ray` · `intersect_plane` · `image_to_G` · `CALIB_KEYS` |
| `src/cvlab/triangulation/reader.py` | `SPEC_FRAME_COLUMNS` · `read_frames_index` · `load_frame` |
| `config/triangulation.yaml` | 최상위 키 `triangulation` 하나 (§6.10) |
| `tests/triangulation/test_tri_*.py` | 시험 |
| `tests/triangulation/tri_synth.py` | 단순 합성 영상 만들기 (시험 도우미. 첫 줄 "T3 시뮬레이터가 아님") |
| `tests/triangulation/tri_bench.py` | 방법 비교 실행 → `방법비교.csv` (pytest가 모으지 않는 이름) |
| `docs/레이저선-추출.md` · `docs/레이저선-추출_자료/방법비교.csv` (+ 그림) | 추출 문서와 자료 |
| `docs/좌표계.md` | 좌표계 문서 |
| `docs/운영/결과_T7a_대조표.md` | 시작 확인 · 종료 대조 |

**공개 이름 (바꾸지 않음, 검증 명령이 씀).**

```python
METHODS = ("max", "cog", "parabola3", "gauss3", "gaussfit", "steger")
TriParams.from_dict(d) ; TriParams.from_yaml(path)                    # 최상위 키 triangulation
extract_centers(img, method="cog", params=None, background=None) -> (v: float32[W], flags: uint8[W])
    # img: uint8/uint16 [H, W], 행 = v, 열 = u. v는 ROI 행 좌표. background: 레이저 끈 프레임 (선택)
roi_to_full(v, roi_y0_px) -> float32[W]
line_quality(img, v, bit_depth, params=None) -> dict   # 키 peak_dn, fwhm_px, n_sat, n_peaks, snr (열마다 배열)
FLAG = {"no_line": 1, "low_peak": 2, "wide": 4, "saturated": 8, "multi_peak": 16, "edge_window": 32}
Tf(to, frm, R=np.eye(3), t=(0, 0, 0)) ; Tf.from_matrix(to, frm, M4) ; .name ("T_G_M") ; .M (4×4)
    ; A @ B (A.frm == B.to일 때만) ; .inv() ; .apply(P[N, 3])
distort_points(xy[N, 2], dist) ; undistort_points(xy_d[N, 2], dist)   # 정규 좌표, dist = (k1, k2, p1, p2[, k3])
pixel_to_ray(uv[N, 2], K, dist) -> 단위 벡터 [N, 3] ({C})
intersect_plane(rays[N, 3], plane[4]) -> 점 [N, 3] ({C})             # plane = [nx, ny, nz, d], n·p + d = 0, |n| = 1
image_to_G(uv_full[N, 2], scan_s_mm, calib) -> 점 [N, 3] ({G})
CALIB_KEYS = ("K", "dist", "laser_plane_C", "T_S_C", "scan_axis_C", "T_G_M")   # 빠지면 오류
SPEC_FRAME_COLUMNS ; read_frames_index(scan_dir) -> DataFrame ; load_frame(scan_dir, row) -> uint16[H, W]
```

`docs/레이저선-추출.md` 목차 (절 번호 고정):

```
# 레이저 선 중심 추출 (1차, 합성 영상)
## 0. 요약
## 1. 입력 영상 ({I}, ROI, 비트 깊이)
## 2. 방법 (식과 구현)
## 3. 합성 시험 영상 (만든 방법, 시뮬레이터가 아님)
## 4. 방법 비교 결과
## 5. 포화 · 다중 피크 · 선 없음
## 6. 품질 지표와 표시 비트
## 7. 기본 방법과 설정값 결정
## 8. px → 높이 환산
## 9. T7b · T8 · T9에 넘길 것
## 10. 한계
```

`docs/좌표계.md` 목차 (절 번호 고정):

```
# 좌표계 {I}{C}{S}{M}{G}
## 0. 요약
## 1. 다섯 좌표계
## 2. 이름 규칙 (T_to_from)
## 3. 영상 → {G} 변환 사슬 (고리별 교정값과 출처)
## 4. 높이 식 (명세 0.4)과의 관계
## 5. 격자 약속 (A[iy, ix], 칸 중심)
## 6. 단위 · 각도 · 부호
## 7. 실측 때 축 검사 (L자 시편)
## 8. 명세 · 요소 청사진과 다른 점
## 9. 한계
```

## 5. 쓰기 범위 (병렬 충돌 방지, 세 작업 공통 표)

| 경로 | T4b | T5 | T7a |
|---|---|---|---|
| `src/cvlab/region/**` · `tests/region/**` · `config/region.yaml` · `scripts/region_mask.py` | **만듦** | - | - |
| `docs/판정-영역.md` · `docs/판정-영역_자료/**` · `docs/운영/결과_T4b_대조표.md` | **만듦** | 읽지 않음 | - |
| `docs/G코드-점검.md` · `docs/G코드-점검_자료/**` · `scripts/gcode_check.py` · `docs/운영/결과_T5_대조표.md` | - | **만듦** | - |
| `docs/판정-시나리오.md` · `docs/판정-시나리오_자료/**` · `config/scenarios/**` · `scripts/scenario_expected.py` (처리 담당 열람 금지) | **읽기 금지** | **만듦** | **읽기 금지** |
| `src/cvlab/triangulation/**` · `tests/triangulation/**` · `config/triangulation.yaml` | - | - | **만듦** |
| `docs/레이저선-추출.md` · `docs/레이저선-추출_자료/**` · `docs/좌표계.md` · `docs/운영/결과_T7a_대조표.md` | - | - | **만듦** |
| `src/cvlab/gcode/**` · `config/gcode.yaml` · `data/gcode_samples/**` (T4a 완료) | 읽기·import | 읽기·import | 읽지 않음 |
| `src/cvlab/judge/**` · `config/judge.yaml` (T15 완료) | 읽기·import | 읽기·import | 읽지 않음 |
| `src/cvlab/io/**` · `src/cvlab/config.py` · `config/default.yaml` · `config/spec/**` (T6 완료. **T6 후속 worker가 `io/` · `config/spec/` · `config/default.yaml`을 고치는 중일 수 있음**, 10-27 20:52 확인) | 읽기만, import 안 함 | 읽기만, import 안 함 | 읽기만, import 안 함 |
| `docs/하드웨어-데이터-명세.md` · `docs/운영/결과_T1_대조표.md` (**T1 2차 worker가 고치는 중**) | 읽기만 | 읽기만 | 읽기만 |
| Git 밖 출력 (`results/`는 `.gitignore`) | `results/region_t4b/` | `results/t5/` | `results/tri_t7a/` |

**모두 금지:** `scripts/method_screening/**` · `tests/test_method_screening.py` · `docs/0_방법탐색/**` (V2 미커밋, 읽기만) · 청사진 · 다른 세부청사진 · 점검일지 · `docs/운영/plane/**` · 요소 청사진 (`docs/blueprints/**`, 읽기만) · `pyproject.toml` · `requirements.txt` · `src/cvlab/__init__.py` · `data/raw/**` (쓰기 금지, 원본 불변) · **`data/_truth/**`와 `src/cvlab/sim/**` (읽기도 금지)** · `tests/**/__init__.py` · `conftest.py` (만들지 않음).

- 시험 파일 · 도우미 이름은 `test_tri_*.py` · `tri_*.py`로 시작합니다 (pytest 기본 import 방식에서 이름 겹침을 피함). 자기 폴더만 돌립니다.
- 의존성은 `requirements.txt`에 있는 것만 씁니다 (numpy · scipy · pandas · matplotlib · PyYAML · Pillow). 이 PC에 OpenCV (`cv2`)가 깔려 있어도 쓰지 않습니다. 왜곡 풀기도 numpy로 합니다.
- T6 `cvlab.io.readers`를 import하지 않습니다. 명세 동결 (G0) 전에 묶이지 않게 얇은 읽기 함수를 따로 둡니다. 통합은 T6 SV13 · T9 몫입니다.

## 6. 설계 규칙

### 6.1 영상 좌표와 ROI

| 항목 | 규칙 | 근거 |
|---|---|---|
| {I} | 왼쪽 위 화소 중심이 (0, 0). u = 열 (오른쪽 +), v = 행 (아래 +), px | 명세 0.4 · C4 |
| 선 방향 | 레이저 선은 대략 가로 (u를 따라)로 놓이고, 높이가 바뀌면 v가 바뀜. 그래서 열마다 v 하나 | 명세 1절 `frame.roi_h_px` "높이 방향 행 수" |
| ROI | 영상은 ROI만 저장될 수 있음. 함수는 ROI 행 좌표를 내고, 전체 행 좌표는 `roi_to_full`로 (+ `frame.roi_y0_px`). u도 `roi_x0_px`만큼 밀림 (문서에 적음) | 명세 1절 |
| 비트 | 10 · 12비트는 16비트 그릇, 아래 비트 정렬. 포화값 = 2^`frame.bit_depth` − 1 (그릇 최댓값이 아님) | 명세 1절 |
| 자료형 | v는 float32, 못 찾으면 NaN (0이나 −1로 결측을 나타내지 않음) | F1 §4 · 명세 0.5 |

### 6.2 방법

| 방법 | 내용 | 근거 |
|---|---|---|
| 공통 앞 단계 | 배경: 레이저 끈 프레임이 있으면 빼고, 없으면 열마다 창 밖 화소의 중앙값 · MAD로 추정. 문턱 = 배경 중앙값 + k·σ (k = 5). 대략 피크 = 열마다 최대 행, 연속성 안내 (중앙값 필터 51열, 띠 ± 8 px) | F1 §4 |
| `max` | 최대 화소 행 (서브픽셀 아님, 비교용) | F1 |
| `cog` | 대략 피크 ± half_win 창 안에서 (I − 문턱)⁺ 가중 평균. half_win 기본 = ⌈1.5 × FWHM⌉ | F1 §4 |
| `parabola3` | 피크와 이웃 두 화소에 포물선 | F1 |
| `gauss3` | 세 화소 로그값에 포물선 (가우시안 3점) | F1 |
| `gaussfit` | 창 안 가우시안 + 상수 최소제곱 (열마다 반복 몇 번, 벡터로) | 선택 |
| `steger` | 1차원 가우시안 미분 (σ_s 1.5 px)의 0 교차 | F1 · Steger |
| 포화 처리 | 포화 화소가 있는 열은 `saturated` 비트. 맞춤형 방법 (`gauss3` · `gaussfit`)은 포화 화소를 빼고 맞춤 (따로 시험) | F1 §6.2 결과 (3점 방법 −0.47 px) |

### 6.3 합성 시험 영상 (`tests/triangulation/tri_synth.py`)

- **T3 시뮬레이터가 아닙니다.** T3 코드를 보거나 흉내 내지 않습니다. 단면 · 잡음 모델은 F1 §6.1과 같은 단순형입니다.
- 화소 넓이로 적분한 가우시안 (오차함수 차), 산탄 잡음 σ = √(gain × DN) (8비트 gain 1, 10비트 gain 4 DN/e [추정: 같은 전자 수를 4배 DN으로]), 읽기 잡음, 반올림, 잘림. 시드 `np.random.default_rng(20261027)`.
- 참 중심 v_true(u): 가운데 + 40 px 사인 + 25 px 단차 (u 500 – 700). 폭 W = 1280, ROI 높이 H = 256 (가운데 128).

| 시나리오 | 비트 | σ px | 피크 DN | 배경 DN | 읽기 잡음 DN | 그 밖 |
|---|---|---|---|---|---|---|
| `f1_basic_8bit` | 8 | 1.5 | 180 | 8 | 2 | F1 §6.1 기본과 같은 값 (비교용) |
| `nominal_10bit` | 10 | 1.5 | 720 | 32 | 8 | 위의 10비트 판 |
| `low_10bit` | 10 | 1.5 | 200 | 32 | 8 | 저신호 |
| `saturated_10bit` | 10 | 1.5 | 1600 | 32 | 8 | 1023에서 잘림 |
| `reflection_10bit` | 10 | 1.5 | 720 | 32 | 8 | 21열에 v_true + 12 px 위치로 1.5배 밝은 가짜 피크 |
| `sigma08_10bit` · `sigma30_10bit` | 10 | 0.8 · 3.0 | 720 | 32 | 8 | 선 두께 |
| `skewed_10bit` | 10 | 1.5 | 720 | 32 | 8 | 가우시안 ⊗ 한쪽 지수 꼬리 (τ 2 px, +v 쪽) [추정: 부피 산란 꼴] |
| `noiseless_10bit` | 10 | 1.5 | 720 | 32 | 0 | 잡음 · 반올림 끔 |
| `no_line_10bit` | 10 | 1.5 | 720 | 32 | 8 | u 300 – 499 (200열) 레이저 없음 |
| `static100_10bit` | 10 | 1.5 | 720 | 32 | 8 | 같은 v_true 100장, 잡음만 다름 → 열별 표준편차 중앙값 (보고만) |
| `speed_roi_10bit` · `speed_full_10bit` | 10 | 1.5 | 720 | 32 | 8 | 1280 × 256 · 1280 × 800, 20회 중앙값 ms |

- `방법비교.csv` 열 (고정): `scenario, bit_depth, sigma_px, peak_dn, method, guided, n_cols, valid_pct, fake_pct, bias_px, std_px, rms_px, p95_px, max_px, rms_um, ms_per_frame`. `guided`는 0 · 1. `fake_pct` = 선이 없는 열 중 값을 낸 비율 (다른 시나리오는 0). `rms_um` = `rms_px` × 환산 (§6.6).

### 6.4 표시 비트

| 비트 | 이름 | 켜는 조건 (기본) | 근거 |
|---|---|---|---|
| 1 | `no_line` | 문턱 넘는 화소 없음 → v NaN | F1 §7 #4 |
| 2 | `low_peak` | 피크 < 3 × 문턱 | F1 §4 |
| 4 | `wide` | FWHM > 2 × 정상 폭 (정상 폭 = 그 영상 FWHM 중앙값) | F1 §4 |
| 8 | `saturated` | 창 안 포화 화소 ≥ 1 | F1 §4 |
| 16 | `multi_peak` | 문턱 넘는 봉우리 ≥ 2이고 둘째가 첫째의 30 % 넘음 [추정] | MF-OPT-06 |
| 32 | `edge_window` | 창이 ROI 위 · 아래 끝에 걸림 | [추정] 끝에서 창이 잘리면 치우침 |

- 값은 지우지 않고 표시만 합니다 (F1 §4 "저장하고 표시만"). 버릴지는 T9 (H2)가 정합니다.

### 6.5 기본 방법 고르는 규칙

1. LX2 문턱을 넘는 방법만 후보 (`nominal_10bit` \|bias\| < 0.02 px, RMS < 0.15 px).
2. 후보 중 `saturated_10bit` \|bias\| < 0.05 px, `reflection_10bit` (안내 켬) P95 < 0.3 px, 속도 (LX10)를 모두 넘는 것.
3. 그중 `nominal_10bit` RMS가 가장 작은 것. 차이가 0.01 px 안이면 더 단순한 방법 (F1 권장 `cog`).
4. 결정과 숫자를 문서 §7에, 값을 `config/triangulation.yaml`에 적습니다.

### 6.6 px → 높이 환산

- 높이 Δz가 바뀌면 점이 레이저 평면 (수직) 위로 Δz 움직이고, 광축에 수직인 성분은 Δz·sin θ (θ = 레이저 평면과 광축 사이 30°)입니다. 영상에서는 배율 M = 0.19를 곱하고 화소 3 µm로 나눕니다.
- 1 px ≈ 3 µm ÷ (0.19 × sin 30°) = 31.6 µm [계산, 텔레센트릭 근사 · 샤임플러그 · 렌즈 왜곡 무시]. F1 요소 청사진의 0.18 px ≈ 5 µm (약 27.8 µm/px)는 다른 배치라 쓰지 않습니다. 정확한 값은 D2 교정 뒤 (T8) 영상 위치마다 다릅니다.

### 6.7 좌표계와 변환 사슬

| 좌표계 | 원점 · 축 (명세 0.4 · C4 그대로) |
|---|---|
| {I} | 왼쪽 위 화소 중심, u 오른쪽, v 아래, px |
| {C} | 렌즈 광학 중심, OpenCV 규칙 (x 영상 오른쪽, y 영상 아래, z 보는 방향), mm |
| {S} | 레이저 평면 위 기준점, x 레이저 선 방향, z 위, y = 레이저 평면 법선 (스캔 방향). {S}의 x–z 평면 = 레이저 평면 |
| {M} | 스캔 시작 위치의 {S} 원점, y 스캔 진행 방향 + |
| {G} | 프린터 원점 (G28 뒤), 베드 면 Z = 0, 노즐 끝 기준 |

| 고리 | 함수 | 교정값 (인자) | 정하는 단계 | 명세 필드 (뜻) |
|---|---|---|---|---|
| {I} → {C} 광선 | `pixel_to_ray` | `K` (3 × 3, px), `dist` | D1 | `truth.cam_k` · `truth.cam_dist` |
| 광선 ∩ 레이저 평면 | `intersect_plane` | `laser_plane_C` [nx, ny, nz, d] | D2 | `truth.laser_plane` |
| {C} → {S} | `Tf.apply` | `T_S_C` | D2 | (평면과 선 방향에서 만듦) |
| {S} → {M} | p_M = p_S + s · a_S, a_S = R_S_C · `scan_axis_C` | `scan_axis_C`, 프레임마다 스캔 위치 s (mm, 스캔 시작에서 잰 거리) | D3 · 위치 로그 | `truth.scan_axis` · 트리거 경로 ⓐ면 s = `meta.scan_speed_mm_s` × `frame.trig_pulse_idx` × `meta.trigger_period_s` (시작 Y `meta.scan_y0_mm`, 방향 `meta.scan_axis`, 명세 1절), 그 밖은 `pos.y_mm` 보간 (T9) |
| {M} → {G} | `Tf.apply` | `T_G_M` | D4 · 위치 로그 | `truth.t_g_m` · `truth.nozzle_sensor_offset_mm` |

- `image_to_G(uv, s, calib) = T_G_M · (T_S_C · (광선 ∩ 평면) + s · a_S)`. 이 부호와 식을 바꾸지 않습니다 (검증 명령 ④가 씀).
- 명세 0.4 높이 식 h(p) = Z_n + d_s(p) + [m(x_n, y_n) − m(x_p, y_p)]과의 관계 (Z_n · 베드 기준 스캔 0점 · 메시 항은 T9 H3에서 더함)를 문서 §4에 적습니다. 이 작업은 메시 항을 넣지 않습니다.
- 교정값에 기본값을 두지 않습니다. `calib`에 `CALIB_KEYS`가 하나라도 없으면 오류. `T_S_C` · `T_G_M`은 `Tf`이고 이름이 맞아야 합니다 (`T_S_C.name == "T_S_C"`).

### 6.8 `Tf` 규칙 (C4 §6)

- det(R) = +1 ± 1e-6, RᵀR = I ± 1e-6이 아니면 ValueError (거울 · 배율 거부).
- `A @ B`는 `A.frm == B.to`일 때만, 결과 이름 `T_<A.to>_<B.frm>`. 아니면 ValueError.
- `.inv()` 이름은 `T_<frm>_<to>`. `.apply(P)`는 [N, 3] · [3] 둘 다 받음.

### 6.9 왜곡과 얇은 읽기

| 항목 | 규칙 |
|---|---|
| 왜곡 식 | OpenCV 순서: r² = x² + y², x_d = x(1 + k1 r² + k2 r⁴ + k3 r⁶) + 2p1 xy + p2(r² + 2x²), y_d = y(…) + p1(r² + 2y²) + 2p2 xy. k3가 없으면 0 |
| 풀기 | 반복 (뉴턴 또는 고정점, 최대 50회, 허용 1e-12). 수렴하지 않으면 경고 + 그 점 NaN |
| 필수 열 | `SPEC_FRAME_COLUMNS`: `frame_idx` · `file` · `laser_on` · `bit_depth` · `roi_x0_px` · `roi_y0_px` · `roi_w_px` · `roi_h_px` · `t_host_ns` (명세 1절, 884daac 기준). `trig_pulse_idx` · `gate_on` 등 조건부 열은 있으면 형 변환해 넘기고, 없어도 오류가 아님 |
| 읽기 | `pandas.read_csv(dtype=str)` 뒤 쓰는 열만 형 변환 (`true`/`false` → bool, 정수). 허용 값 검사는 하지 않음 (T6 검증기 몫) |
| 영상 | `frames/NNNNNN.png` (Pillow, 16비트는 mode `I;16` → uint16) · `frames.npz#fNNNNNN`. 크기가 `roi_h_px` × `roi_w_px`와 다르면 ValueError |
| 쓰기 | 읽기 함수는 아무것도 쓰지 않음. 시험은 `tmp_path`에 가짜 스캔 폴더를 만듦 |

### 6.10 `config/triangulation.yaml`

```yaml
triangulation:
  method: cog                  # §6.5 규칙으로 확정 (F1 권장 cog)
  threshold_k_sigma: 5.0       # F1 §4: 배경 중앙값 + 5σ
  half_win_px: null            # null = ⌈1.5 × FWHM⌉ (F1 §4)
  guide_win_cols: 51           # F1 §4
  guide_band_px: 8             # F1 §4
  low_peak_factor: 3.0         # F1 §4
  wide_factor: 2.0             # F1 §4
  multi_peak_ratio: 0.3        # [추정] 둘째 봉우리 / 첫째
  steger_sigma_px: 1.5         # F1
  gaussfit_max_iter: 10        # [추정]
```

- 모르는 키는 오류입니다. 값마다 주석 근거를 유지합니다. 교정값은 이 파일에 넣지 않습니다 (T8 결과 YAML).

## 7. 단계

| 단계 | 날짜 | 할 일 | 끝난 표시 |
|---|---|---|---|
| S1 | 10-27 | 시작 확인 (§10). `tri_synth.py`, 방법 6개 (LX1), 기본 시험 (LX2) | 대조표 · 시험 |
| S2 | 10-28 | 포화 · 다중 피크 · 선 없음 · 품질 비트 (LX4 – LX7), ROI · 비트 (LX9) | 시험 |
| S3 | 10-29 | `tri_bench.py` · `방법비교.csv` (LX3 · LX8 · LX10), 기본 방법 결정 (§6.5) | 명령 ② |
| S4 | 10-30 | `Tf` · 왜곡 · 광선 · 평면 · `image_to_G` (LX12) | 명령 ④ |
| S5 | 10-31 | 얇은 읽기 (LX13) | 명령 ③ |
| S6 | 11-01 ~ 11-02 | 문서 두 개 (LX11 · LX14), 명세 다시 확인 | 명령 ⑤ |
| S7 | 11-03 | 검증 명령 전부, "종료 대조" → 팀장 검증 | 대조표 |

## 8. 검증

### 8.1 검증 명령 (Git Bash에 그대로 붙여 넣기)

① 시험

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m pytest tests/triangulation -q -p no:cacheprovider -rs --durations=5 2>&1 | tail -15 && echo '--- 시험 함수 수' && cat tests/triangulation/test_tri_*.py | grep -c -E "^def test_"
```

② 방법 비교표 (다시 만들고 기준 확인)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python tests/triangulation/tri_bench.py --out "$TEMP/t7a_bench.csv" 2>&1 | tail -3 && PYTHONIOENCODING=utf-8 python - <<'EOF'
import csv, os, yaml
R = list(csv.DictReader(open(os.path.join(os.environ['TEMP'], 't7a_bench.csv'), encoding='utf-8')))
D = list(csv.DictReader(open('docs/레이저선-추출_자료/방법비교.csv', encoding='utf-8')))
cols = ['scenario', 'bit_depth', 'sigma_px', 'peak_dn', 'method', 'guided', 'n_cols', 'valid_pct', 'fake_pct', 'bias_px', 'std_px', 'rms_px', 'p95_px', 'max_px', 'rms_um', 'ms_per_frame']
print('빠진 열', [c for c in cols if c not in R[0]], '/ 문서 CSV와 행 수', len(R), len(D))
need = ['f1_basic_8bit', 'nominal_10bit', 'low_10bit', 'saturated_10bit', 'reflection_10bit', 'sigma08_10bit', 'sigma30_10bit', 'skewed_10bit', 'noiseless_10bit', 'no_line_10bit', 'static100_10bit', 'speed_roi_10bit', 'speed_full_10bit']
print('빠진 시나리오', [s for s in need if not any(r['scenario'] == s for r in R)], '/ 방법', sorted({r['method'] for r in R}))
M = yaml.safe_load(open('config/triangulation.yaml', encoding='utf-8'))['triangulation']['method']; print('기본 방법', M)
def g(s, m, gd=None):
    c = [r for r in R if r['scenario'] == s and r['method'] == m and (gd is None or r['guided'] == gd)]
    return c[0] if c else None
f = lambda r, k: float(r[k]) if r else float('nan')
for s in ['f1_basic_8bit', 'nominal_10bit']:
    r = g(s, 'cog', '1'); print(s, 'cog |bias|', abs(f(r, 'bias_px')), '< 0.02 / rms', f(r, 'rms_px'), '< 0.15 / valid', f(r, 'valid_pct'), '= 100')
r = g('noiseless_10bit', 'gauss3', '1'); print('noiseless gauss3 max', f(r, 'max_px'), '< 0.05')
r = g('saturated_10bit', M, '1'); print('포화 기본 |bias|', abs(f(r, 'bias_px')), '< 0.05')
r = g('reflection_10bit', M, '1'); r0 = g('reflection_10bit', M, '0'); print('반사 안내 켬 p95', f(r, 'p95_px'), '< 0.3 / 끔 p95', f(r0, 'p95_px'))
r = g('no_line_10bit', M, '1'); print('선 없음 fake', f(r, 'fake_pct'), '= 0')
r = g('speed_roi_10bit', M); r2 = g('speed_full_10bit', M); print('속도 ROI', f(r, 'ms_per_frame'), 'ms ≤ 15 / 전체', f(r2, 'ms_per_frame'), 'ms ≤ 30')
r = g('skewed_10bit', M, '1'); print('비가우시안 기본 bias (보고만)', f(r, 'bias_px'))
EOF
```

③ 팀장 독립 영상 (worker 생성기가 아닌 상승 코사인 단면, ROI 오프셋 272, 선 없는 열 40개) · 얇은 읽기

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python - <<'EOF'
import os, csv, tempfile, yaml, numpy as np
from PIL import Image
from cvlab.triangulation import extract_centers, roi_to_full, read_frames_index, load_frame, FLAG
rng = np.random.default_rng(7); W, H, y0 = 1280, 256, 272; u = np.arange(W)
v_full = y0 + 128 + 40 * np.sin(2 * np.pi * u / W * 1.5) + np.where((u > 500) & (u < 700), 25.0, 0.0); v_roi = v_full - y0
rows = np.arange(H)[:, None]; img = np.zeros((H, W))
for sft in (np.arange(5) - 2) / 5:
    d = rows + sft - v_roi[None, :]; img += np.where(np.abs(d) < 3.5, 0.5 * (1 + np.cos(np.pi * d / 3.5)), 0.0) / 5
img = 40 + 700 * img; img = img + rng.normal(0, 1, img.shape) * np.sqrt(4 * np.maximum(img, 0)) + rng.normal(0, 8, img.shape)
img = np.clip(np.round(img), 0, 1023).astype(np.uint16); img[:, 100:140] = np.clip(np.round(40 + rng.normal(0, 8, (H, 40))), 0, 1023).astype(np.uint16)
M = yaml.safe_load(open('config/triangulation.yaml', encoding='utf-8'))['triangulation']['method']
v, flags = extract_centers(img, method=M); vf = roi_to_full(v, y0); ok = np.isfinite(vf); m = np.ones(W, bool); m[100:140] = False
e = vf[m & ok] - v_full[m & ok]
print('기본', M, '/ 유효', round(100 * ok[m].mean(), 2), '% (≥ 99) / 없는 열에서 값 낸 수', int(ok[~m].sum()), '(0)')
print('bias', round(float(e.mean()), 4), 'px (|·| < 0.05) / RMS', round(float(np.sqrt((e ** 2).mean())), 4), 'px (< 0.2)')
print('없는 열 no_line 비트', bool(((flags[~m] & FLAG['no_line']) > 0).all()))
d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'frames')); imgs = [img, img[::-1].copy(), (img // 4).astype(np.uint16)]
rs = []
for i, a in enumerate(imgs):
    Image.fromarray(a).save(os.path.join(d, 'frames', '%06d.png' % i))
    rs.append(dict(scan_id='S01_r01_L004', layer_idx=4, frame_idx=i, file='frames/%06d.png' % i, t_host_ns=1000 + i, exposure_us=800.0, gain_db=0.0, bit_depth=10, pixel_format='GRAY10', lossy='false', roi_x0_px=0, roi_y0_px=y0, roi_w_px=W, roi_h_px=H, laser_on='false' if i == 2 else 'true', trigger_mode='gate', dropped_before=0, future_col='x'))
with open(os.path.join(d, 'frames_index.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rs[0])); w.writeheader(); w.writerows(rs)
df = read_frames_index(d)
print('읽기 행', len(df), '/ 레이저 끈 행', int((~df['laser_on'].astype(bool)).sum()), '(1) / 픽셀 같음', all(np.array_equal(load_frame(d, df.iloc[i]), imgs[i]) for i in range(3)), '/ dtype', load_frame(d, df.iloc[0]).dtype)
with open(os.path.join(d, 'frames_index.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=[k for k in rs[0] if k != 'roi_y0_px']); w.writeheader(); w.writerows([{k: v for k, v in r.items() if k != 'roi_y0_px'} for r in rs])
try: read_frames_index(d); print('필수 열 빠져도 읽힘 (✗)')
except ValueError as x: print('필수 열 빠지면 오류 (○)', 'roi_y0_px' in str(x))
EOF
```

④ 좌표계 · 변환 (팀장이 따로 쓴 왜곡 식과 합성 기하로)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python - <<'EOF'
import numpy as np
from cvlab.triangulation import Tf, distort_points, undistort_points, image_to_G
def rot(ax, ay, az):
    cx, sx, cy, sy, cz, sz = np.cos(ax), np.sin(ax), np.cos(ay), np.sin(ay), np.cos(az), np.sin(az)
    return np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
rng = np.random.default_rng(3)
A = Tf('G', 'M', rot(0.01, -0.02, 0.5), (100, 90, 0)); B = Tf('M', 'S', rot(0.1, 0.2, 0.3), (1, 5, -2)); C = A @ B
p = rng.normal(0, 10, (100, 3)); print('이름', C.name, '(T_G_S) / 왕복 최대', float(np.abs(C.inv().apply(C.apply(p)) - p).max()), '(< 1e-9)')
for k, bad in [('잘못된 곱', lambda: B @ A), ('거울', lambda: Tf('G', 'M', np.diag([1., 1., -1.]), (0, 0, 0))), ('배율', lambda: Tf('G', 'M', 2 * np.eye(3), (0, 0, 0)))]:
    try: bad(); print(k, '거부 안 됨 (✗)')
    except ValueError: print(k, '거부 (○)')
k1, k2, p1, p2, k3 = -0.05, 0.01, 0.001, -0.0005, 0.002; dist = np.array([k1, k2, p1, p2, k3])
def dref(xy):
    x, y = xy[:, 0], xy[:, 1]; r2 = x * x + y * y; rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
    return np.c_[x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x), y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y]
xy = rng.uniform(-0.2, 0.2, (1000, 2))
print('왜곡 식 차', float(np.abs(distort_points(xy, dist) - dref(xy)).max()), '(< 1e-12) / 풀기 왕복', float(np.abs(undistort_points(dref(xy), dist) - xy).max()), '(< 1e-9)')
c, s30 = np.cos(np.radians(30)), np.sin(np.radians(30))
R_C_S = np.array([[1, 0, 0], [0, -c, -s30], [0, s30, -c]]); T_C_S = Tf('C', 'S', R_C_S, (0, 0, 50.0))
K = np.array([[2666.7, 0, 640], [0, 2666.7, 400], [0, 0, 1.]]); n = R_C_S[:, 1]; plane = np.r_[n, -n @ np.array([0, 0, 50.0])]
T_G_M = Tf('G', 'M', rot(0.002, -0.001, 0.003), (175.0, 155.0, 2.0)); s = 3.0
P_S = np.c_[rng.uniform(-8, 8, 300), np.zeros(300), rng.uniform(-3, 3, 300)]
P_C = T_C_S.apply(P_S); xd = dref(P_C[:, :2] / P_C[:, 2:3]); uv = np.c_[K[0, 0] * xd[:, 0] + K[0, 2], K[1, 1] * xd[:, 1] + K[1, 2]]
P_G = T_G_M.apply(P_S + s * np.array([0, 1.0, 0]))
calib = dict(K=K, dist=dist, laser_plane_C=plane, T_S_C=T_C_S.inv(), scan_axis_C=n, T_G_M=T_G_M)
print('영상 범위 u', round(uv[:, 0].min()), '–', round(uv[:, 0].max()), 'v', round(uv[:, 1].min()), '–', round(uv[:, 1].max()))
print('영상 → {G} 최대 오차', float(np.abs(image_to_G(uv, s, calib) - P_G).max()), 'mm (< 1e-6)')
try: image_to_G(uv, s, {k: v for k, v in calib.items() if k != 'dist'}); print('교정값 빠져도 돎 (✗)')
except (KeyError, ValueError): print('교정값 빠지면 오류 (○)')
EOF
```

⑤ 문서 구조

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import re
for p, n, keys in [('docs/레이저선-추출.md', 11, ['cog', 'gauss3', 'steger', 'saturated', 'multi_peak', 'no_line', '31.6', 'T7b', 'T3 시뮬레이터가 아님', 'C4 · C5']),
                   ('docs/좌표계.md', 10, ['{I}', '{C}', '{S}', '{M}', '{G}', 'T_G_M', 'D1', 'D2', 'D3', 'D4', '레이저 선', '프린터 Y', 'A[iy, ix]', '0.4'])]:
    t = open(p, encoding='utf-8').read()
    print(p, '절 누락', [h for h in map(str, range(n)) if not re.search(r'^## %s\. ' % h, t, re.M)])
    print('  키워드 없음', [k for k in keys if k not in t], '/ 근거 태그', len(re.findall(r'\[(계산|추정|미상|출처|확인 필요)', t)))
EOF
```

⑥ 정보 차단 · 의존성

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && grep -rn -E "cvlab\.(gcode|judge|io|sim|region|config|repro)|_truth|scenarios|판정-시나리오|scenario_expected|import cv2|from cv2|skimage|data/raw" src/cvlab/triangulation tests/triangulation config/triangulation.yaml; echo "grep exit=$? (1이면 0건)"
```

⑦ 소유 검사 (세 작업 공통, T4b · T5 세부청사진과 같은 명령)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import re, subprocess
own = [('T4b', ('src/cvlab/region/', 'tests/region/', 'config/region.yaml', 'scripts/region_mask.py', 'docs/판정-영역.md', 'docs/판정-영역_자료/', 'docs/운영/결과_T4b_대조표.md')),
('T5', ('docs/G코드-점검.md', 'docs/G코드-점검_자료/', 'docs/판정-시나리오.md', 'docs/판정-시나리오_자료/', 'config/scenarios/', 'scripts/gcode_check.py', 'scripts/scenario_expected.py', 'docs/운영/결과_T5_대조표.md')),
('T7a', ('src/cvlab/triangulation/', 'tests/triangulation/', 'config/triangulation.yaml', 'docs/레이저선-추출.md', 'docs/레이저선-추출_자료/', 'docs/좌표계.md', 'docs/운영/결과_T7a_대조표.md')),
('T1-2차', ('docs/하드웨어-데이터-명세.md', 'docs/운영/결과_T1_대조표.md')),
('T6-후속', ('src/cvlab/io/', 'config/spec/', 'config/default.yaml', 'scripts/validate_dataset.py', 'scripts/extract_spec_schema.py', 'tests/infra/', 'docs/명세-검증기.md', 'docs/운영/결과_T6_대조표.md')),
('V2', ('scripts/method_screening/', 'tests/test_method_screening.py', 'docs/0_방법탐색/')),
('운영', ('docs/운영/세부청사진_', 'docs/운영/청사진_', 'docs/운영/점검일지.md', 'docs/운영/팀장검증'))]
done = ('src/cvlab/gcode/', 'src/cvlab/judge/', 'src/cvlab/__init__.py', 'src/cvlab/config.py', 'src/cvlab/repro.py', 'config/gcode.yaml', 'config/judge.yaml', 'data/gcode_samples/', 'pyproject.toml', 'requirements.txt')
out = subprocess.run(['git', '-c', 'core.quotepath=false', 'status', '--porcelain', '-uall'], capture_output=True, text=True, encoding='utf-8').stdout
bad = []
for l in out.splitlines():
    p = l[3:].strip().strip('"').split(' -> ')[-1]
    if '__pycache__' in p: continue
    if p.startswith(done): print('완료물'.ljust(7), l[:2], p); bad.append(p); continue
    o = next((n for n, ps in own if any(p == x or p.startswith(x) for x in ps)), '소유자 없음')
    print(o.ljust(7), l[:2], p)
    if o == '소유자 없음' or p.endswith('conftest.py') or re.search(r'^tests/.*__init__\.py$', p): bad.append(p)
print('--- 위반', bad)
EOF
```

⑧ V2 지문 (시작과 끝에 같아야 함)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && sha256sum scripts/method_screening/*.py tests/test_method_screening.py
```

판정: ① 모두 통과, 함수 ≥ 30, 120 s 이내. ② 빠진 열 · 시나리오 빈 목록, 문서 CSV와 행 수 같음, 줄마다 기준 안 (비가우시안은 보고만). ③ 유효 ≥ 99 %, 없는 열 값 0, \|bias\| < 0.05 px, RMS < 0.2 px, no_line True, 읽기 행 3 · 끈 행 1 · 픽셀 같음 True · uint16, 필수 열 오류 "(○) True". ④ 이름 T_G_S, 왕복 < 1e-9, 거부 셋 "(○)", 왜곡 차 < 1e-12, 풀기 < 1e-9, 영상 범위가 0–1279 · 0–799 안, {G} 오차 < 1e-6 mm, 빠진 교정값 "(○)". ⑤ 절 누락 · 키워드 없음 빈 목록. ⑥ grep exit=1. ⑦ 위반 빈 목록. ⑧ 시작 값과 같음.

### 8.2 팀장 검사

- 명령 ③의 독립 영상 (상승 코사인 단면, worker 생성기와 다른 꼴)에서 기본 방법이 기준을 넘는지 봅니다. 넘지 못하면 worker 합성 영상에만 맞춘 것인지 원인을 따집니다 (역범죄의 작은 판).
- 명령 ④의 기하는 팀장이 따로 정한 것입니다 (카메라 광축이 레이저 평면과 30°, {S} 원점이 렌즈 앞 50 mm, 평면 [0, −0.866, 0.5, −25]는 명세 부록 A 예시와 같음). 이 기하에서 {G} 오차가 1e-6 mm 안이면 사슬의 부호와 순서가 §6.7과 같다고 봅니다.
- `extract_centers`의 `cog` 코드를 읽어 문턱을 뺀 가중치 (I − 문턱)⁺를 쓰는지, 창이 ROI 끝에 걸리면 `edge_window`를 켜는지 봅니다.
- `방법비교.csv`에서 `f1_basic_8bit` 행을 F1 §6.2 기대 출력 (cog RMS 0.073 px)과 비교합니다. 크게 다르면 (2배 넘게) 생성기나 방법의 차이를 문서에서 찾습니다.
- `docs/좌표계.md`의 다섯 좌표계 표를 명세 0.4절 표와 줄마다 대조합니다. C4 요소 청사진 (`{S}` y = 스캔 방향)과 명세가 다른 곳이 있으면 문서 §8에 있는지 봅니다.
- 대조표의 명세 시작·끝 지문을 비교해 1절 frame 필드가 바뀌었으면 `SPEC_FRAME_COLUMNS`가 그에 맞는지 봅니다.

## 9. 금지 사항

- `data/_truth/` · `src/cvlab/sim/` · T5 시나리오 산출물을 읽지 않습니다. T3 코드가 생겨도 보지 않습니다. 시험 영상은 직접 만든 단순 합성 영상만 씁니다.
- 합성 영상으로 얻은 숫자를 C4 · C5 (교정 · 종단 정확도) 결과로 쓰지 않습니다. 문서마다 "단순 합성 영상, 하드웨어 성능의 증거가 아님"을 적습니다.
- 교정값을 코드나 설정에 기본값으로 넣지 않습니다 (예시 값은 시험 코드 안에서만, "시험용 가정"으로 표시).
- `cv2` · `skimage` 등 `requirements.txt` 밖 패키지를 쓰지 않습니다. `pip install`을 하지 않습니다. `cvlab.gcode` · `cvlab.judge` · `cvlab.io` · `cvlab.config`를 import하지 않습니다.
- `data/raw/`에 쓰지 않습니다. 명세를 고치지 않고, 명세와 다른 점은 문서 §8과 대조표에 적어 팀장에게 넘깁니다.
- 숫자를 지어내지 않습니다. 설정 값은 F1 결정 · 명세 · `[계산]` · `[추정]` (이유) 중 하나를 붙입니다.
- V2 미커밋 파일을 고치거나 되돌리지 않습니다. git 쓰기 명령을 쓰지 않습니다 (읽기만). 유료 API · Plane 수정을 하지 않습니다.
- §5 소유 표 밖의 파일을 만들거나 고치지 않습니다. F1 · C4 요소 청사진은 고치지 않고 문서에 바꿀 점을 적습니다.
- 범위를 바꾸고 싶으면 (예: 삼각측량 교정까지) 멈추고 팀장에게 보고합니다.

## 10. 시작 확인 항목

`docs/운영/결과_T7a_대조표.md`를 만들고 "시작 확인" 절에 적은 뒤 시작합니다.

- [ ] 브랜치 · HEAD, `git status --short` 기준선, 명령 ⑧ 출력 (V2 지문)
- [ ] 명세 상태: `sha256sum docs/하드웨어-데이터-명세.md`, 줄 수, 수정 시각, `git diff --stat HEAD -- docs/하드웨어-데이터-명세.md`. 1절 frame 필드표의 필드 수와 `SPEC_FRAME_COLUMNS` 후보 열이 모두 있는지 (끝날 때 다시 재서 비교)
- [ ] 목표 LX1 – LX15를 자기 말로 한 줄씩
- [ ] §3 입력 파일이 모두 있는지
- [ ] Python · numpy · scipy · pandas · Pillow 판, `cv2`를 쓰지 않는다는 확인
- [ ] §5 소유 표를 읽었고 T4b · T5 경로를 건드리지 않으며 `data/_truth/` · `src/cvlab/sim/` · T5 시나리오 산출물을 읽지 않는다는 확인
- [ ] 마감: 전체 11-03

## 11. 종료 대조표 양식

```markdown
## 종료 대조 (2026-11-03 HH:MM)

| 목표 항목 | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| LX1 방법 | n개, 한 함수 | 시험 | |
| LX2 기본 정확도 | cog bias · RMS (8비트 · 10비트), gauss3 무잡음 최대 | 명령 ② | |
| LX3 비교표 | 시나리오 13 × 방법 n, 정지 100장 std 중앙값 | 명령 ② | |
| LX4 포화 | 기본 bias, saturated 비트 % | 명령 ② | |
| LX5 반사 | 안내 켬 p95 · 끔 p95, multi_peak % | 명령 ② | |
| LX6 선 없음 | fake 0, no_line % | 명령 ② | |
| LX7 품질 지표 | 지표 5종, 비트 6개 시험 | 시험 | |
| LX8 비가우시안 | 방법별 bias (보고만) | 문서 §4 | |
| LX9 ROI · 비트 | 전체 = ROI + y0 차, 8 · 10비트 | 시험 · 명령 ③ | |
| LX10 속도 | ROI ms, 전체 ms | 명령 ② | |
| LX11 좌표계 문서 | 절 0–9, 명세 0.4와 대조 | 명령 ⑤ | |
| LX12 변환 뼈대 | 거부 3종, 왕복, 왜곡, {G} 오차 | 명령 ④ | |
| LX13 얇은 읽기 | PNG · npz, 필수 열 오류 | 명령 ③ · 시험 | |
| LX14 추출 문서 | 절 0–10, 기본 방법 근거 | 명령 ⑤ | |
| LX15 시험 · 차단 | n개 통과 t s, grep 0, 소유 위반 0, V2 지문 같음 | 명령 ① · ⑥ · ⑦ · ⑧ | |

명세 시작 · 끝 지문: (같음 / 바뀜 + 영향 필드)
검증 명령 실행 결과: (①–⑧ 출력 붙여 넣기)
남은 문제: (없으면 "없음")
```
