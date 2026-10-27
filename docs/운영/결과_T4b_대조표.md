# 결과 대조표 T4b · 판정 영역 (G4)

> 세부청사진: [세부청사진_T4b_판정영역](세부청사진_T4b_판정영역.md) (커밋 9687174) · 담당: 기준모델 담당 (T4b 인스턴스, Opus 5.5 medium) · 문서: [판정-영역](../판정-영역.md)

## 시작 확인 (2026-10-27 21:01)

| 항목 | 확인 |
|---|---|
| 브랜치 · HEAD | `claude/lidar-error-measurement-blueprint-vq1ofq` · `9687174` |
| `git status --short` 기준선 | V2 미커밋 (`scripts/method_screening/` 5개 M · `v3.py` ?? · `tests/test_method_screening.py` M · `docs/0_방법탐색/결과_v3/` ??), T6 후속 작업 중 (`src/cvlab/io/rules.py` · `selftest.py` · `spec_schema.py` · `validate.py` M). 그 밖 변경 없음 |
| V2 지문 (명령 ⑦) | figures `13340800…` · rules `9fd40186…` · scoring `3062bf91…` · screen `d953d60c…` · simulate `843b3069…` · specs `64c8bf99…` · v3 `e84a6a1c…` · test_method_screening `6e89d4e7…` |
| 명세 상태 | `docs/하드웨어-데이터-명세.md` sha256 `79aca87f835a75750b3f1fa32e96fdbe2d1bafa457c9361e3d39651902c96d96`, 1 294줄, 수정 2026-10-27 20:36:21, `git diff --stat HEAD` 변경 없음 (884daac와 같음) |
| 쓰는 명세 값 | `meta.triang_angle_deg` 30.0 (5절) · `meta.scan_length_mm` 40.0 · `meta.scan_speed_mm_s` 2.4 · `meta.scan_pass_idx` (X를 바꾼 줄 번호, 2절) · `meta.scan_axis` +Y · 0.4절 스캔 = 프린터 Y |
| 입력 파일 | §3 입력 모두 있음 (G4 · E2 요소 청사진, `docs/G코드-해석.md`, `src/cvlab/gcode/`, `src/cvlab/judge/`, 명세, `docs/프린터-펌웨어-선정.md` §9, `docs/측정-실패사례.md`, `data/gcode_samples/hand/` 27개) |
| `_local/` 두 파일 지문 | voron24_test_box `d3d18d44…` = MANIFEST · caliper_pyramid `0fab35b2…` = MANIFEST (같음) |
| 판 | Python 3.14.4 · numpy 2.4.4 · scipy 1.18.0 · pandas 3.0.2 · matplotlib 3.11.2 |
| 소유 표 (§5) | 읽음. 쓰기는 `src/cvlab/region/` · `tests/region/` · `config/region.yaml` · `scripts/region_mask.py` · `docs/판정-영역*` · 이 대조표만. T5 시나리오 산출물 (`docs/판정-시나리오*` · `config/scenarios/` · `scripts/scenario_expected.py`)은 읽지 않음. T5 · T7a 경로는 건드리지 않음. `cvlab.io` · `cvlab.config` · `cvlab.sim` import 안 함 |
| 마감 | 전체 11-02 |

**목표를 내 말로 (RG1 – RG15)**

| 번호 | 한 줄 |
|---|---|
| RG1 | 판정 격자 원점을 0.4 mm 배수로 내리고 크기를 20칸 배수로 올려, 0.2 · 0.4 mm 칸 경계가 출력마다 같은 자리에 오게 한다 |
| RG2 | 3 × 3 이웃 높이 차가 층 높이 반을 넘는 칸을 경계로 보고, 거리 변환으로 띠 폭 안의 칸을 뺀다 |
| RG3 | 카메라가 ±Y 쪽 30°에 있다고 보고 시선이 막히는 칸을 예측해 2칸 넓혀 뺀다 |
| RG4 | 층 Z에서 심도 8 mm 아래의 윗면을 심도 밖으로 빼고 코드 9 + 비트 depth로 남긴다. caliper 41층 · 62 % 대조 |
| RG5 | 꼭대기 층이 스커트·브림·서포트·PRIME-TOWER면 빼고, 퍼지선 자리는 prime, 출력물 없는 칸은 no_material |
| RG6 | 시야 20 mm · 스캔 40 mm · 겹침 2 mm로 패스를 깔고 어느 패스에도 안 드는 칸을 뺀다 |
| RG7 | 칸마다 이유 비트 (겹침)와 우선순위로 고른 T15 코드 하나를 낸다 |
| RG8 | 층별 · 전체 영역 비율과 이유별 · 코드별 칸 수, 0.2 · 0.4 mm 판정 칸 수를 표로 낸다 |
| RG9 | T15 `LayerInput`을 만들어 `judge_print_fine`에 그대로 넣을 수 있게 한다 |
| RG10 | caliper 심도 문제를 A안 (빼기) · B안 (높이 나눠 스캔)으로 숫자 비교하고 권장안을 낸다 |
| RG11 | 결 · 첫 층 눌림 · 아이롱 · 측정값 안 보기 결정을 근거와 함께 적는다 |
| RG12 | 저장 · 불러오기 · 재현이 비트 단위로 같다 |
| RG13 | voron24 30 s, caliper 120 s 안에 만든다 |
| RG14 | `docs/판정-영역.md` 절 0–13 |
| RG15 | 시험 30개 이상 통과, 정보 차단 · 소유 · V2 지문 · 완료 패키지 변경 0 |

## 종료 대조 (2026-10-27 21:53)

| 목표 항목 | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| RG1 격자 원점 | H20 원점 ÷ 0.4 = 247 · 247 (정수), nx · ny 20 배수 True. 기본 격자와 정답 높이 차 0 (H20 · H21 무작위 400점, 출력물 칸 수 같음). caliper 격자 2240 × 1180 (스커트 뺌) | 명령 ② · 시험 `test_region_aligned_grid_*` | ○ |
| RG2 엣지 띠 | 자동 띠 voron24 0.24 · caliper 0.38 · H20 0.25 mm, step 0.1. H20 **가운데 줄 (y 105) 한쪽 13칸**. 명령 ②는 252.5칸 (아래 "명령 ② 차이") | 시험 · 문서 §3 | ○ (명령 ② 항목은 △) |
| RG3 가림 | 그림자 1.02 mm (탑 끝 y 4.8 기준, 기대 1.039 ± 0.02), 넓힘 +2칸 (51 → 53). side 3종 voron24 67.1 · 67.1 · 63.7 %, caliper 10.4 · 10.4 · 10.1 %. 명령 ②는 0.82 mm · 45칸 (아래) | 시험 · 문서 §4 | ○ (명령 ② 항목은 △) |
| RG4 심도 | caliper 층 **41** (층 23부터), 마지막 층 **61.9 %** (62 ± 1). 합성 탑 9층 · 51.9 %. dof_top −1: 64층 · 70.4 % · 덮임률 72.1 %, +1: 43층 · 61.9 % · 100 % | 명령 ② · ③ · 문서 §5 | ○ |
| RG5 종류 · PRIME | 제외 종류 4종 (caliper SKIRT 60 832 924칸). PRIME caliper 6개 중 격자 안 0 (위치 모름 1), 합성 시험 격자 안 퍼지선 코드 4. IRONING 넣음 | 시험 · 문서 §6 | ○ |
| RG6 시야 | voron24 **2 × 1**, caliper **2 × 2** 패스. 패스 하나 강제 시 \|x − 15\| > 10 칸 모두 코드 3 | 명령 ③ · 시험 | ○ (T5 대조는 팀장) |
| RG7 비트 · 코드 | 128가지 비트 조합 전부 §6.2 규칙과 같음, 영역 ⇔ 비트 0 ⇔ 코드 0 (모든 층), 코드 ⊂ EXCLUSION_CODES. 우선순위 · 코드 시험 4개 | 시험 | ○ |
| RG8 영역 비율 | voron24 63.7 %, caliper 10.1 % (전체 합산). 0.2 mm 칸 141 760 · 110 896, 0.4 mm 32 003 · 22 061. `summary()` 열 고정 | 명령 ③ · 문서 §8 | ○ |
| RG9 T15 연결 | H20 · 합성 탑 `judge_print_fine` pass (주 · 보조), 영역 칸 = summary 합, 이유별 칸 수 = 묶은 코드 (이유 없음 0), post (cooled) 연결 | 명령 ② · 시험 | ○ |
| RG10 caliper 처리안 | A안 덮임률 **100 %** (132 851칸). B안 되찾는 칸 2 108 700 = 심도 밖 물체 칸의 **8.6 %**, 추가 4 425 s ≈ **74분**. **권장 A안** | 문서 §9 | ○ |
| RG11 결정 기록 | GCD-02 (결 안 넣음) · 03 (첫 층 눌림 안 넣음, 보고 주의) · 07 (아이롱 넣음) · JDG-03 (측정값 인자 없음, 시험) | 문서 §11 | ○ |
| RG12 저장 · 재현 | save → load 뒤 비트 · 영역 · 코드 · summary 같음 (packbits 비트 평면 7장), 두 번 만들어 `array_equal` | 시험 | ○ |
| RG13 속도 | voron24 10.2 – 11.2 s, caliper 38.0 s (혼자) · 77.4 s (기기 부하 때). 처음 판 113 s에서 줄임 | 명령 ③ · 문서 §8 | ○ |
| RG14 문서 | 절 0–13 누락 없음, 키워드 13개 모두 True, 근거 태그 39 | 명령 ④ | ○ |
| RG15 시험 · 차단 | 시험 함수 42개 (펼쳐 46) 모두 통과 72.9 s (skip 0). 부하 때 158 – 167 s도 나옴. grep 0건 (exit 1), 소유 위반 0, V2 지문 같음, 완료 패키지 변경 0 | 명령 ① · ⑤ · ⑥ · ⑦ | ○ (시간은 기기 부하에 따라 △) |

명세 시작 · 끝 지문: 같음 (`79aca87f…`, `git diff --stat` 변경 없음). 이 작업이 쓰는 필드 영향 없음. HEAD는 작업 중 다른 작업 커밋으로 `c80e251`까지 이동 (T5 · T6 · T7a, 이 작업 파일과 무관).

**청사진과 다르게 한 것 (팀장 확인 필요)**

1. `config/region.yaml`에 §6.9 목록에 없는 키 2개를 더함: `lead_in_mm: 5.0` (LM-T14-2) · `scan_speed_mm_s: 2.4` (`meta.scan_speed_mm_s`). B안 추가 시간 계산에만 쓰며, 명세 값을 코드에 박지 않으려고 이 파일에 둠.
2. 층별 종류는 `RefStack._type_codes` (비공개 속성)를 **읽기만** 해서 덮어쓴다 (공개 `type_at`을 층마다 부르면 층 수 제곱). 공개 함수만 쓰는 판과 결과가 같음을 시험으로 확인 (`test_region_type_incremental_equals_type_at`). `src/cvlab/gcode/`는 고치지 않음. 공개 함수 추가는 T4a 쪽 판단.
3. 요약 줄 `passes` 값은 `{"x", "y", "total"}` 객체로 냄.
4. 진행 규칙 위반 1건: `src/cvlab/region/stack.py`의 층 반복 부분을 한 번 파이썬 스크립트 (heredoc)로 바꿔 씀 (Edit 도구 규칙 위반). 이후 수정은 모두 Edit. 결과는 시험 46개로 확인.

**명령 ② 차이 (명령 쪽 가정 문제, 코드는 기대대로)**

- H20 "가운데 줄": `argmax(fp.sum(1))`이 첫 최댓값 줄 y = 100.22 (아래 가장자리에서 0.22 mm, 띠 안)를 골라 252.5칸. 둘째 층이 세로 선이라 505칸인 줄이 많고 첫 줄이 가장자리다. y = 105 줄은 13칸 (기대 13.5 ± 1).
- 합성 탑: 생성기가 0–5 mm를 선 간격 0.4로 채워 탑 끝이 y = 4.8. 명령은 y > 5.0만 세서 0.82 mm. 탑 끝 기준 1.02 mm (기대 1.039 ± 0.02). 넓힌 뒤 45칸 = 41 + 2 (그림자 끝) + 2 (바닥 끝 y 10의 베드 그림자가 넓혀져 들어옴).
- 심도 9층 · 51.9 %, T15 pass, 원점 · 코드 줄은 기대와 같음.

**검증 명령 실행 결과 (요약)**

- ① `46 passed in 72.85s`, 함수 42개, skip 0 (가장 긴 것 caliper 시험 40.4 s).
- ② 원점 [247, 247] · 20 배수 True / H20 252.5 (위 차이) / 코드 True · True / T15 pass {n_region 4136} / 그림자 0.82 (위 차이) / 넓힌 뒤 45 (위 차이) / 심도 9층 / 마지막 층 51.9 %.
- ③ caliper `depth_layers` 41 · `last_layer_depth_pct_object` 61.882 · `coverage_final_top_pct` 100.0 · `build_s` 38.0 · passes 2 × 2. voron24 `depth_layers` 0 · 100.0 · `build_s` 11.2 · passes 2 × 1. 쓰기 거부 "(○)".
- ④ 절 누락 [] · 키워드 모두 True · 근거 태그 39.
- ⑤ grep exit=1, 완료 패키지 변경 0.
- ⑥ 위반 [] (T4b 파일 17개, V2 파일 그대로).
- ⑦ V2 지문 시작과 같음.

**남은 문제**

- caliper 마지막 층 판정 영역 0칸 (경사 블록 윗면 전부 엣지 띠) → 식힌 재측정 비교가 빈다. T15에서 정할 일 (문서 §12).
- caliper 전체 영역 비율 10.1 %: 판정 시험 파일로 쓰기에 영역이 작다 (T5 다시 슬라이스 판단에 참고).
- 장착 방향 (`camera_side`) · `dof_top_mm`는 [추정]. 실측 지도와 대조 전.
- 시험 시간은 기기 부하 (OneDrive 동기화 등)에 따라 73 – 167 s로 흔들림. 120 s 목표는 부하 없을 때만 충족.

## 후속 R-1 · R-2 · R-3 시작 확인 (2026-10-28)

> 기준: [팀장검증_5차](팀장검증_5차.md) §3 · §6 R-1 · R-2 · R-3. HEAD `0f16275` (팀장검증 5차). 남의 미커밋 변경 (T14 · T7a 대조표, 펌웨어 문서, V2 `scripts/method_screening/`)은 건드리지 않음.

| ID | 내 말로 | 완료 기준 |
|---|---|---|
| R-1 | 시험에서 `build_s <= 120` · `<= 30` 단정문을 뺀다. 속도는 REGION 줄 `build_s`로만 본다 | CPU 부하와 무관하게 tests/region 통과 |
| R-2 | 식힌 재측정 비교 영역 `post_region()`: 마지막 층 출력물 칸에서 type · fov · depth · occlusion은 계속 빼고, 엣지는 좁은 띠 max(2 × res, α × 반폭 × ΔT) [추정]만 뺀다. 0칸이면 엣지 포함 (P-A)으로 넘어가고 규칙 이름을 남긴다. `post_input`이 이 영역을 넘긴다. 판정 영역 (`region()`)은 그대로 | caliper post 0.2 mm 칸 약 940, voron24 판정 · 칸 수 그대로, 문서 §9 한 줄 |
| R-3 | `REASON_CODE["depth"]` 9 → 6, `summary()` 열 `code_9` → `code_6`, 시험 · 문서 §2 · §12 | judge 연결 시험 통과, caliper "기타" 0 |

쓰기 범위: `src/cvlab/region/` · `tests/region/` · `config/region.yaml` · `scripts/region_mask.py` · `docs/판정-영역.md` · 이 대조표. judge 코드는 읽기만.

## 후속 R-1 · R-2 · R-3 종료 대조 (2026-10-28)

| ID | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| R-1 | `test_region_local.py`의 `build_s <= 120` · `<= 30` 단정문 삭제 (시험 이름 `test_region_voron_no_depth_and_speed` → `test_region_voron_no_depth`). tests/region 안 시간 단정문 0건 (grep `build_s`는 REGION 키 목록 · 주석뿐). 속도는 REGION 줄 `build_s`로만 판정 (문서 §8) | 시험 · 문서 §8 | ○ (CPU 95 % 이상 재현은 안 함, 아래) |
| R-2 | `RegionStack.post_region()` · `post_reasons()` · `post_exclusion_code()` 신설. `post_input` · `layer_input(..., "cooled")`가 이 영역 · 코드를 넘김. 띠 자동값 max(2·res, α·반폭·ΔT) [추정], 0칸이면 P-A. **caliper: 띠 0.0433 mm, 고운 288 360 · 0.2 mm 940 · 0.4 mm 72칸 (팀장 값과 같음)**, 마지막 층 판정 영역 0 그대로. voron24: 0.2 mm 판정 칸 합 141 760 그대로, post 15 348칸. `config/region.yaml`에 `post_edge_band_mm: null` · `post_delta_t_c: 30.0` 추가. 저장 npz에 `post_edge` 비트 평면 추가 (옛 파일은 불러오되 post 호출 때 오류). 스크립트에 `POST {json}` 줄 (REGION 줄 키는 그대로). 문서 §9 덮임률 분모 한 줄, §10 · §12 갱신 | 시험 `test_region_post_*` · `test_region_caliper_post_region_r2` · 문서 §0 · §9 · §10 | ○ |
| R-3 | `REASON_CODE["depth"]` = 6, `summary()` 열 `code_9` → `code_6`, 그림 범례 6. 128 조합 시험이 9를 안 냄 확인. judge 연결: 합성 탑 by_code "심도 밖" > 0 · "기타" 0 (시험 `test_region_depth_code6_reaches_judge`). **caliper 전 층 `judge_print_fine`: pass, 주 칸 by_code 심도 밖 251 488 · 기타 0 · 이유 없음 0** (스크래치 실행, 팀장 기대와 같음) | 시험 · 문서 §0 · §2 · §5 · §8 · §12 | ○ |

**시험**: `python -m pytest tests/region -q` → **51 passed in 90.34 s** (skip 0). 돌리기 전 · 뒤 CPU 부하 68 % · 56 % (Win32_Processor LoadPercentage). `tests/judge` 91 passed (judge 코드는 고치지 않음, `git diff src/cvlab/judge` 없음).

**J-3에 넘길 인터페이스** (cvlab.region.RegionStack)

| 이름 | 반환 | 뜻 |
|---|---|---|
| `post_region()` | `np.ndarray` bool, 격자 (ny, nx) | 식힌 재측정 비교 영역. `region(마지막 층)`을 포함 |
| `post_exclusion_code()` | `np.ndarray` int8, (ny, nx) | 영역 밖 칸의 T15 코드 (영역 안 0, 값 ⊂ {1 … 6}) |
| `post_reasons()` | `np.ndarray` uint8, (ny, nx) | 마지막 층 비트에서 엣지 비트만 좁은 띠로 바꾼 것 |
| `post_input(delta_mm)` | `cvlab.judge.LayerInput` (layer_idx = 마지막 층, thermal_state = "cooled", region = `post_region()`, exclusion_code = `post_exclusion_code()`) | `judge_print_fine(..., post=...)`에 그대로 |
| `info["post_rule"]` · `["post_band_mm"]` · `["post_n_region"]` · `["post_region_cell02"]` · `["post_region_cell04"]` · `["post_delta_t_c"]` | str · float · int | 규칙 이름 ("P-B 좁은 엣지 띠" / "P-A 엣지 포함")과 칸 수. 결과 보고에 규칙 이름을 남길 때 씀 |

- J-3에서 바꿀 곳 (읽기만 함): `verdict.py` `judge_print`의 `cooled_difference(last.delta_mm, post.delta_mm, region=last.region & post.region)`. 지금은 마지막 층 판정 영역과 교집합이라 caliper에서 계속 `cooled = None` (스크래치 실행에서 확인). `region=post.region`으로 바꾸고, 진행 중 마지막 층 Δ가 판정 영역 밖에서 NaN이면 두 Δ 유효 칸 교집합으로 줄어든다는 점을 J-3이 정해야 함 (진행 중 측정을 판정 영역 밖에도 남기는지).
- `fine_to_cell_layer`로 0.2 mm로 묶으면 caliper post 940칸 (`region_fill_min` 1.0).

**남은 것 · 확인 못 한 것**

- R-1 완료 기준의 "CPU 95 % 이상에서 통과"는 과열 우려로 부하를 일부러 걸지 않았다. 시험에 시간 단정문이 없어 부하로 실패할 길은 없음 (grep 근거).
- α · ΔT · 반폭 정의는 [추정]. caliper 반폭 = 경계 상자 긴 변 42.451 ÷ 2 = 21.23 mm (팀장 21 mm).
- 세부청사진 T4b §6.8 `code_9` 문구 · RG15 문구 수정은 팀장 몫 (이 작업 쓰기 범위 밖).
- Python 파일은 모두 Edit 도구로 고침 (heredoc · sed 0건). 대조표 덧붙이기만 heredoc.
