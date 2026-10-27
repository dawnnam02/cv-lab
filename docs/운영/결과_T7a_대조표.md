# 결과 T7a 대조표 · 레이저 선 추출 1차와 좌표계

> 세부청사진: [세부청사진_T7a_레이저선추출](세부청사진_T7a_레이저선추출.md) (커밋 9687174) · 담당: 광학처리 담당 worker (Opus 5.5) · 독립 검증: 팀장
> 이 문서의 정확도 숫자는 모두 **단순 합성 영상** 결과입니다. 하드웨어 성능이나 C4 · C5 (교정 · 종단 정확도)의 증거가 아닙니다.

## 시작 확인 (2026-10-27)

| 항목 | 확인 내용 |
|---|---|
| 브랜치 · HEAD | `claude/lidar-error-measurement-blueprint-vq1ofq` · `9687174` (세부청사진 커밋) |
| `git status --short` 기준선 | M: `scripts/method_screening/{rules,scoring,screen,simulate,specs}.py` · `src/cvlab/io/{rules,selftest,spec_schema,validate}.py` · `tests/test_method_screening.py`. ??: `docs/0_방법탐색/결과_v3/` · `scripts/method_screening/v3.py`. 모두 남의 작업 (V2 · T6 후속), 손대지 않음 |
| 명령 ⑧ V2 지문 (시작) | 8개 파일, 전체 값은 아래 원문 |
| 명세 상태 (시작) | sha256 `79aca87f835a75750b3f1fa32e96fdbe2d1bafa457c9361e3d39651902c96d96`, 1294줄, 수정 2026-10-27 20:36:21, `git diff --stat HEAD` 빈 출력 (작업 트리 = 884daac 판) |
| 1절 frame 필드 | 필드표 26개. `SPEC_FRAME_COLUMNS` 후보 9개 (`frame_idx` · `file` · `laser_on` · `bit_depth` · `roi_x0_px` · `roi_y0_px` · `roi_w_px` · `roi_h_px` · `t_host_ns`) 모두 있음. 조건부 `trig_pulse_idx` · `gate_on` 있음. 주의: 명세에서 `frame.file`은 "조건부" (`meta.raw_saved` = false면 빈 칸). 세부청사진 §6.9는 필수 열로 둠 → 열 자체는 필수로 검사하고 값이 빈 행은 `load_frame`에서 오류 (§8에 적음) |
| §3 입력 파일 | F1 · C4 · B1 · B2 · D1–D5 요소 청사진, 명세, 펌웨어 문서 (§9 층 변경 매크로 · 경로 ⓐ), 실패사례 (MF-OPT-02 · 06, MF-SIM-03, MF-SYN-06) 모두 있음 |
| 패키지 판 | Python 3.14.4 · numpy 2.4.4 · scipy 1.18.0 · pandas 3.0.2 · Pillow 12.2.0 · PyYAML 6.0.3. `cv2` · `skimage`는 쓰지 않음 |
| 소유 · 차단 | §5 소유 표 읽음. T4b · T5 경로를 건드리지 않음. `data/_truth/` · `src/cvlab/sim/` · T5 시나리오 산출물 (`docs/판정-시나리오*` · `config/scenarios/` · `scripts/scenario_expected.py`)은 열지 않음. `cvlab.io` · `cvlab.config` 등 import 안 함. git 쓰기 · pip install 안 함 |
| 마감 | 전체 11-03 |

명령 ⑧ 시작 출력 원문:

```
133408005565c3b58c82c6e6ced4ee3821b09039699d3fb4489887d99673b676 *scripts/method_screening/figures.py
9fd40186be949b4301b546769b164e198197cf42df08ddc4dd615a691b111296 *scripts/method_screening/rules.py
3062bf911679c6cb1ee1539c6fcd3c5764bf2214af1cc77b88f5ad6b7cf00bd1 *scripts/method_screening/scoring.py
d953d60c6256151eae8120c121fc8ebaaf3cf831d25a66e702ab350ccaab576b *scripts/method_screening/screen.py
843b30694b606b90aa355b152ef7af351d8ab16df497943046834a52505ada9d *scripts/method_screening/simulate.py
64c8bf9962dd1b6c2c3975a457612a2dbf2eac935cd9da6a4b6df30f8a07bb0d *scripts/method_screening/specs.py
e84a6a1c457e54f908c55f3be795d406dd24b4730183a8f4f9781c078480571a *scripts/method_screening/v3.py
6e89d4e71d4bfb5680125e6ba7afef472b41410a3f93b0e50fff4d3189ff1f49 *tests/test_method_screening.py
```

### 목표를 내 말로 (LX1 – LX15)

| 번호 | 한 줄 |
|---|---|
| LX1 | `extract_centers` 하나로 6개 방법 (max · cog · parabola3 · gauss3 · gaussfit · steger)을 고르고, 열마다 v (float32, 없으면 NaN)와 표시 비트를 돌려준다 |
| LX2 | 8비트 · 10비트 기본 영상에서 cog 치우침 0.02 px 미만, RMS 0.15 px 미만, 전 열 유효. 무잡음에서 gauss3 최대 오차 0.05 px 미만 |
| LX3 | 13개 시나리오 × 방법 비교표를 고정 열 CSV로 남기고, RMS를 µm로도 적는다 |
| LX4 | 포화 영상에서 기본 방법 치우침 0.05 px 미만, 포화 열은 모두 saturated 비트 |
| LX5 | 21열 반사에서 연속성 안내를 켜면 P95 0.3 px 미만, 그 열 multi_peak 비트 95 % 이상, 끈 결과도 적는다 |
| LX6 | 레이저 없는 200열에서 값을 하나도 내지 않고 모두 no_line 비트 |
| LX7 | 열마다 peak_dn · fwhm_px · n_sat · n_peaks · snr 지표, 비트 6개 각각을 켜는 시험 |
| LX8 | 꼬리 있는 단면에서 방법별 치우침을 보고만 한다 (부호 · 크기 문서화) |
| LX9 | ROI 결과 + roi_y0 = 전체 영상 결과 (1e-4 px 안), 8 · 10비트, 포화값 = 2^bit − 1 |
| LX10 | 기본 방법 ROI 한 장 15 ms, 전체 한 장 30 ms 이하 (중앙값 20회) |
| LX11 | `docs/좌표계.md` 절 0–9, 명세 0.4와 같은 좌표계 표와 고리별 교정값 · 단계 · 필드 |
| LX12 | `Tf` 거부 규칙, 왕복 1e-9, OpenCV 왜곡 식 일치 · 풀기 왕복, `image_to_G` 1e-6 mm, 교정값 빠지면 오류 |
| LX13 | 얇은 읽기: PNG 8 · 16비트와 npz, 필수 열은 한 상수, 빠지면 열 이름을 담은 ValueError |
| LX14 | `docs/레이저선-추출.md` 절 0–10, 기본 방법을 숫자로 고른 근거 |
| LX15 | 시험 30개 이상 120 s 안 통과, 금지 import · 경로 언급 0, 소유 위반 0, V2 지문 같음 |

## 종료 대조 (2026-10-27 21:38, 1차 끝. 마감 11-03 전 조기 제출)

| 목표 항목 | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| LX1 방법 | 6개 (max · cog · parabola3 · gauss3 · gaussfit · steger), `extract_centers` 하나. v float32 (NaN) · flags uint8 | `test_output_types_all_methods` · `test_methods_tuple_fixed` | 통과 |
| LX2 기본 정확도 | cog 8비트 bias −0.0002 / RMS 0.0717 px, 10비트 −0.0003 / 0.0714 px, 유효 100 %. gauss3 무잡음 최대 0.00002 px | 명령 ② | 통과 |
| LX3 비교표 | 시나리오 13 × 방법 6 × 안내 켬 · 끔 = 156행, 열 고정. 정지 100장 열별 std 중앙값 cog 0.0714 px (≈ 2.3 µm) | 명령 ② · `docs/레이저선-추출_자료/방법비교.csv` | 통과 |
| LX4 포화 | cog bias −0.0001 px, 포화 열 `saturated` 100 % | 명령 ② · `test_saturated_bias_and_bit` | 통과 |
| LX5 반사 | 21열 기준 안내 켬 P95 0.149 px · 끔 12.09 px, `multi_peak` 100 % | 명령 ② · `test_reflection_guided_p95_and_multi_bit` | 통과 |
| LX6 선 없음 | 200열 × 10장 값 0 (모든 방법), `no_line` 100 %. 배경 + 1σ 신호도 전부 NaN | 명령 ② · 시험 2개 | 통과 |
| LX7 품질 지표 | 5종 (peak_dn · fwhm_px · n_sat · n_peaks · snr), 비트 6개 각각 켜는 시험 있음 | `test_tri_flags.py` | 통과 |
| LX8 비가우시안 | skewed bias (보고만): max +1.29, cog +1.62, parabola3 +1.30, gauss3 +1.30, gaussfit +1.52, steger +1.43 px (꼬리 쪽 +v, 41 – 51 µm) | 문서 §4 | 보고 |
| LX9 ROI · 비트 | 전체 800행 vs ROI + 272: 6방법 × 8 · 10비트 차 < 1e-4 px (시험 통과). 포화값 2^bit − 1 (10 vs 12비트 시험) | `test_crop_matches_full_frame` · 명령 ③ | 통과 |
| LX10 속도 | cog ROI ⓐ 11.2 ms · ⓑ 15.6 ms, 전체 ⓐ 17.5 ms · ⓑ 25.3 ms (ⓐ 보통 부하, ⓑ 다른 프로세스 CPU 100 % 중, 문서 CSV = ⓑ). 부하 없이 cProfile 약 9 · 15 ms | 명령 ② · 문서 §4 · §7 | **조건부**: 문서 CSV의 ROI 15.6 ms > 15. 부하 없을 때 명령 ② 재실행 필요 |
| LX11 좌표계 문서 | 절 0–9, 다섯 좌표계 표 = 명세 0.4 (줄마다 대조), 고리별 교정값 · 단위 · D1–D4 · 명세 필드, 높이 식 관계 | 명령 ⑤ | 통과 |
| LX12 변환 뼈대 | 이름 T_G_S, 왕복 4.3e-14, 거부 3종 (○), 왜곡 식 차 0, 풀기 왕복 9.7e-13, 영상 u 212–1082 · v 317–475, {G} 오차 8.8e-11 mm, 빠진 교정값 (○) | 명령 ④ · `test_tri_frames.py` · `test_tri_geometry.py` | 통과 |
| LX13 얇은 읽기 | PNG 16 · 8비트 · npz, uint16, 필수 열 9개 각각 빠지면 그 이름 담은 ValueError, 모르는 열 통과, `laser_on` bool. 명령 ③: 읽기 3행 · 끈 1행 · 픽셀 같음 · uint16 · (○) True | 명령 ③ · `test_tri_reader.py` | 통과 |
| LX14 추출 문서 | 절 0–10, §7에 §6.5 규칙 단계별 숫자 → cog | 명령 ⑤ | 통과 |
| LX15 시험 · 차단 | 시험 함수 58개 (매개변수 포함 93건) 통과, 11 – 22 s. grep exit=1, 소유 위반 [], V2 지문 시작과 같음 | 명령 ① · ⑥ · ⑦ · ⑧ | 통과 |

명세 시작 · 끝 지문: **같음** (sha256 `79aca87f…c96d96`, 1294줄, 수정 10-27 20:36:21). 1절 frame 필드 바뀜 없음 → `SPEC_FRAME_COLUMNS` 그대로. HEAD는 그사이 남의 커밋으로 9687174 → 68a6d34 (T6 SV13) → fcec589 (T5)로 움직였으나 명세 파일은 같음.

검증 명령 실행 결과 (요약):

```
① 93 passed in 11.18 s (부하 중 21.75 s) / 시험 함수 수 58
② 빠진 열 [] / 문서 CSV와 행 수 156 156 / 빠진 시나리오 [] / 방법 6개 / 기본 방법 cog
   f1_basic_8bit cog |bias| 0.00022 rms 0.07181 valid 100 · nominal_10bit cog |bias| 0.0003 rms 0.0714 valid 100
   noiseless gauss3 max 2e-05 · 포화 |bias| 8e-05 · 반사 켬 p95 0.15026 / 끔 12.09 · 선 없음 fake 0
   속도 ROI 22.39 ms / 전체 28.53 ms (이 실행은 CPU 100 % 부하 중, 임시 CSV) · 비가우시안 bias 1.62391
③ 기본 cog / 유효 100.0 % / 없는 열 값 0 / bias 0.001 px / RMS 0.0676 px / no_line True
   읽기 행 3 / 끈 행 1 / 픽셀 같음 True / uint16 / 필수 열 빠지면 오류 (○) True
④ 이름 T_G_S / 왕복 4.26e-14 / 잘못된 곱 · 거울 · 배율 거부 (○) / 왜곡 식 차 0.0 / 풀기 왕복 9.7e-13
   영상 범위 u 212–1082 v 317–475 / {G} 최대 오차 8.78e-11 mm / 교정값 빠지면 오류 (○)
⑤ 두 문서 절 누락 [] · 키워드 없음 [] · 근거 태그 17 · 4
⑥ grep exit=1 (0건)
⑦ T7a 파일 22개 모두 T7a 소유, 위반 []
⑧ 8개 지문 시작과 같음
```

남은 문제:

1. **LX10 속도 (조건부).** 문서 CSV는 다른 프로세스 (PID 12540, 이 작업 것이 아님)가 CPU 100 %를 쓰는 중에 만들어져 cog ROI 15.6 ms (기준 15 ms)를 넘음. 보통 부하 실행에서는 11.2 ms. 부하 없을 때 명령 ②를 다시 돌려 CSV를 갱신해야 함 (`python tests/triangulation/tri_bench.py`, 약 1 – 2분).
2. 꼬리 있는 단면에서 모든 방법이 +1.3 – 1.6 px (≈ 41 – 51 µm) 치우침. τ 2 px는 이 작업의 가정 [추정]. T7b에서 T3 단면으로 다시 재고, D2 교정이 흡수하는지 봐야 함.
3. 명세와 다른 점 (docs/좌표계.md §8): ③ {M} 축 방향을 {S}와 같게 두고 스캔 축 a_S를 따로 씀 (팀장 확인 필요), ⑦ `frame.file` 조건부 vs 필수 열. 명세는 고치지 않음.
4. `extract_centers`에 키워드 인자 `bit_depth=`를 더함 (공개 이름 표에는 없음, 기존 호출은 그대로 됨). 안 넘기면 그릇으로 추정하므로 T9는 `frame.bit_depth`를 꼭 넘겨야 함.
5. 그림 (선택 산출물)은 만들지 않음.
