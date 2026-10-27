# 결과 T4a 대조표 · G코드 해석과 층별 정답 높이 지도 1차

> 세부청사진: [세부청사진_T4a_G코드해석](세부청사진_T4a_G코드해석.md) (커밋 67b0f92) · 담당: 기준모델 worker (Opus 5.5, medium)

## 시작 확인 (2026-10-27)

| 항목 | 확인 내용 |
|---|---|
| 브랜치·HEAD | `claude/lidar-error-measurement-blueprint-vq1ofq` · `22f6540` (지시서 커밋 67b0f92 뒤에 Plane 커밋 1개) |
| `git status --short` 기준선 | ` M .gitignore` · ` M scripts/method_screening/{rules,scoring,screen,simulate,specs}.py` · ` M tests/test_method_screening.py` · `?? config/ data/ docs/0_방법탐색/결과_v3/ docs/운영/plane/_check_20261027*/ docs/운영/결과_T15_대조표.md docs/운영/결과_T6_대조표.md pyproject.toml requirements.txt results/ scripts/method_screening/v3.py src/` (T6·T15가 이미 쓰는 중) |
| 입력 파일 | G1–G4 요소 청사진, `docs/측정-실패사례.md`, `docs/하드웨어-데이터-명세.md`, `docs/프린터-펌웨어-선정.md`, `docs/테스트-G코드-후보.md` 모두 있음 |
| 사용자 선택 | 대기 (메인 지시: 아직 고르지 않음, 복사 금지) |
| Python · numpy · pandas | 3.14.4 · 2.4.4 · 3.0.2 (PyYAML 6.0.3, matplotlib 3.11.2, pytest 9.1.1) |
| 소유 표 | 5절 읽음. T6 (`src/cvlab/__init__.py`·pyproject 등)·T15 (`src/cvlab/judge/`) 경로와 후보 폴더는 건드리지 않음. `PYTHONPATH=src`로 돌림 |
| 마감 | 전체 11-04, 후보 실행 (GC12)은 사용자 선택 뒤 |

**V2 파일 지문 (시작)**

```
133408005565c3b58c82c6e6ced4ee3821b09039699d3fb4489887d99673b676  scripts/method_screening/figures.py
9fd40186be949b4301b546769b164e198197cf42df08ddc4dd615a691b111296  scripts/method_screening/rules.py
3062bf911679c6cb1ee1539c6fcd3c5764bf2214af1cc77b88f5ad6b7cf00bd1  scripts/method_screening/scoring.py
d953d60c6256151eae8120c121fc8ebaaf3cf831d25a66e702ab350ccaab576b  scripts/method_screening/screen.py
843b30694b606b90aa355b152ef7af351d8ab16df497943046834a52505ada9d  scripts/method_screening/simulate.py
64c8bf9962dd1b6c2c3975a457612a2dbf2eac935cd9da6a4b6df30f8a07bb0d  scripts/method_screening/specs.py
e84a6a1c457e54f908c55f3be795d406dd24b4730183a8f4f9781c078480571a  scripts/method_screening/v3.py
6e89d4e71d4bfb5680125e6ba7afef472b41410a3f93b0e50fff4d3189ff1f49  tests/test_method_screening.py
```

**검증 명령 ④ (후보 폴더 지문, 시작)**

```
f99f651353607b43bcb241554f6cbd55afb7c6a4381597a5e98e020dffcbf05f  data/gcode_candidates/benchy_helix/3DBenchy.gcode
0fab35b2c7d9387be1517fb9679071cad5374fc4e9af4f6f0287f69f86487f9f  data/gcode_candidates/caliper_pyramid/caliper pyramid test.prusaproject_0.6n_0.35mm_PLA_MK3SMMU2S_16m.gcode
6fd9cfef152dab7d5c1226993d65fba1bc67818f8366c22fa206ff29dd72dfad  data/gcode_candidates/orca_calib_cube/orcaslicer-2.2.0-rc-calibration-cube.gcode
9364b6109ecf14e9d34865bc71726dbeb165f20adb65f0d86ce94a420a1751a9  data/gcode_candidates/simple_cura/SimpleCuraTest.gcode
d3d18d442ec8b141c1da8fc4175d393862d0caaa3ca977bda6cd286a78551230  data/gcode_candidates/voron24_test_box/test_box_25mm_PLA_3m17s.gcode
2e73a849768a0bd3701d537f3caba5e12a9aacdbc247ca47c23768a498eca32e  data/gcode_candidates/voron_design_cube/Voron_Design_Cube_v7_PLA-F_20m58s.gcode
02076f64c7d4e9b437c4a1ecf5b62fb5c557a0cdfa5cae35985c72eb224db65b  data/gcode_candidates/xyz_cube_10mm/xyz-10mm-calibration-cube.gcode
파일 수: 7
```

**목표를 내 말로**

| 번호 | 한 줄 |
|---|---|
| GC1 | 흔한 G코드 문법 (직선·원호·좌표 모드·E 모드·단위·원점·펌웨어 리트랙트·체크섬·주석·붙여 쓴 단어·소문자)을 모두 읽어 선분 표로 만든다 |
| GC2 | 선분마다 압출·이동·리트랙트·되밀기·와이프·Z 이동을 가르고, 정답 경로는 압출만 쓴다 |
| GC3 | 모르는 명령은 세고, 압출 사이에 끼면 멈춘다. 허용 목록은 이유를 달아야 한다 |
| GC4 | 층을 주석과 압출 Z 두 방법으로 정해 맞지 않으면 멈춘다. Z hop·가변 층은 받고, 나선·순차 출력은 멈춘다 |
| GC5 | 층 표 9열과 G코드 줄 범위를 규칙대로 낸다 |
| GC6 | 머리말에서 슬라이서·방언·선언값을 읽고, 없으면 None과 경고를 남긴다 |
| GC7 | 압출 합과 슬라이서 선언 필라멘트 길이가 1 % 안인지 본다 |
| GC8 | 비드 단면 넓이·역산·실효 선폭을 만들고, 정답 높이는 층 Z (flat)로 정한다 |
| GC9 | 층 n까지의 윗면 높이 지도를 고운 격자에 만들고 저장·읽기가 같게 한다 |
| GC10 | 지도를 손계산 값 다섯 가지로 시험한다 |
| GC11 | 손 G코드 18개 이상과 기대값 표를 만든다 |
| GC12 | 사용자가 고른 후보만 복사해 돌린다. 지금은 대기 |
| GC13 | 후보 폴더는 시작과 끝에 지문이 같고 그 안에 아무것도 만들지 않는다 |
| GC14 | `docs/G코드-해석.md` 절 0–9와 MF-GCD 대응표를 쓴다 |
| GC15 | 시험 30개 이상 모두 통과 (120 s 안), 금지 import·소유 위반 0 |

**쓰기 범위 메모.** 팀장 지시문에는 쓸 곳이 `src/cvlab/gcode/` · `tests/gcode/` · `config/gcode.yaml` · `scripts/gcode_reference.py` · 대조표로 적혀 있음. 세부청사진 5절 소유 표는 여기에 `data/gcode_samples/hand/` (손 G코드, GC11)와 `docs/G코드-해석.md` (GC14)를 더함. 이 둘은 다른 작업과 겹치지 않고 검증 명령 ②·⑥이 요구하므로 만든다. 후보 복사 (`public/`·`_local/`)는 하지 않는다.

## 종료 대조 (2026-10-27, 1차. 세부청사진 마감 11-04보다 앞당겨 마침)

| 목표 항목 | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| GC1 파서 기본 | G0–G3 (I·J·R, 시계·반시계, 전체 원, 현 ≤ 0.1), G90/G91, M82/M83, G92, G20/G21, G28, G10/G11, N·체크섬, `;`·`( )`, `\r\n`, 붙여 쓴 단어, 소문자. 선분 표 14열 고정. 파서 시험 25개 + 손 G코드 H01–H09·H19 | 명령 ① · ② | 통과 |
| GC2 선분 종류 | 6종 (extrude · travel · retract · unretract · wipe · zmove), 경로는 extrude만 | 명령 ① (`test_kinds_six`, H07) | 통과 |
| GC3 모르는 명령 | 목록 다섯 (움직임·상태·움직임 없음·시작/끝 구간만·모름). 엄격 모드 오류, 허용 목록 기본 0개 (이유 필수). H16 오류, 허용하면 통과 + 셈 | 명령 ② (H16) | 통과 |
| GC4 층 정하기 | 주석·압출 Z 두 방법 대조. H10 (Z hop) · H11 (가변) · H17 (순차, 오류) · H18 (나선, 오류) · H22 (겹친 표시) · H23 (퍼지선 PRIME) · H24 (나선 Z홉) | 명령 ② | 통과 |
| GC5 층 표 | 열 9개, 줄 범위 규칙 §6.3 (주석 있음·없음), 다음 층 시작 > 이번 층 끝 | 명령 ① (`test_layer_table_columns_and_order`, `test_line_ranges_no_comment_rule`) | 통과 |
| GC6 머리말 | 슬라이서 4종 (Orca · Prusa · Cura · Bambu) 이름·판, 방언 옮김 표 (marlin · klipper · reprap · other), 선언 층 수·필라멘트·노즐·선폭·층 높이·필라멘트 지름·SHA-256. 없으면 None + 경고 | 문서 §1 | 통과 |
| GC7 압출량 | ΣΔE = 층 범위 안 순 ΔE. 손 H12 · H13 · H23 차 ≤ 1 %. 후보 탐색 (참고): 6개 모두 \|차\| ≤ 0.002 % | 명령 ① · 문서 §6 | 통과 (후보는 참고) |
| GC8 비드 모델 | `bead_area(0.42,0.2)` = 0.0754159, 역산 < 1e-9, w_eff (0.5 mm 미만 뺌, H20에서 0.42 ± 1e-4), 정답 높이 = 층 Z (flat), 대안 `bead_profile_height`는 민감도용 | 명령 ② | 통과 |
| GC9 정답 지도 | `RefStack` (footprint · height_at_layer · top_layer_at · type_at · save · load), npz 다시 읽으면 발자국·높이·종류 모두 같음 | 명령 ① (`test_save_load_roundtrip`) | 통과 |
| GC10 해석해 | ① 높이 = 층 Z (1e-9) ② 선분 하나 면적 상대 차 ≤ 1 % ③ 선폭 간격 채움 안쪽 빈칸 0 ④ 두 번 → `array_equal` ⑤ L자 방향 | 명령 ① | 통과 |
| GC11 손 G코드 | 24개 (`_mimic` 7개: H12 · H13 · H14 · H15 · H22 · H23 · H24), 기대값 78행, 식 빈 행 0 | 명령 ② | 통과 |
| GC12 고른 후보 | 대기 (사용자 선택 없음, 복사 0, MANIFEST 없음) | 명령 ③ · ⑤ | 대기 |
| GC13 후보 폴더 | 시작·끝 지문 7개 같음, 만든 파일 0 (탐색 출력은 스크래치패드) | 명령 ④ | 통과 |
| GC14 문서 | `docs/G코드-해석.md` 절 0–9, MF-GCD 8개, 근거 태그 18개 | 명령 ⑥ | 통과 |
| GC15 시험·차단 | 시험 함수 66개 (펼쳐 143개): 142 통과 · 1 skip (사용자 선택 대기), 10–14 s. 금지 import·`_truth`·후보 경로 0, 소유 위반 0, V2 지문 8개 같음 | 명령 ① · ⑦ · ⑧ | 통과 |

**검증 명령 실행 결과 (요약)**

- ① `142 passed, 1 skipped in 10.42s` · `SKIPPED [1] test_gcode_hand.py:50: 사용자 선택 대기` · 시험 함수 수 66
- ② 손 G코드 24 · 기대값 행 78 · 식 빈 행 [] · 기대값 없는 파일 [] · H01 압출 4 길이 합 40.0 · H05 원호 길이 합 31.415797 (기대 31.415927, 허용 0.001) · H11 층 Z [0.2, 0.35, 0.45] 층 높이 [0.2, 0.15, 0.1] · H16 · H17 · H18 오류 남 (○) · bead_area 0.0754159, 역산 True
- ③ 출력 없음 (선택 대기)
- ④ 시작 절의 지문 7줄과 같음, 파일 수 7
- ⑤ `MANIFEST 없음 (사용자 선택 대기면 정상)`
- ⑥ 절 누락 [] · MF-GCD 빠짐 [] · 키워드 6개 True · 근거 태그 수 18
- ⑦ `grep exit=1` · 스크립트 언급은 20줄 `FORBIDDEN_OUT = ...  # 쓰기 거부` 하나. `--out data/gcode_candidates/x` → 거부 (rc 2) 확인
- ⑧ 위반 [] · V2 지문 시작과 같음

**후보 7개 탐색 실행 (읽기만, 참고. 출력은 스크래치패드)**

| 후보 | 결과 | 이유·값 |
|---|---|---|
| voron24_test_box | 통과 | 층 16 = 16 = 선언 16 (표시 32개 중 압출 없는 16개 뺌), 필라멘트 +0.0001 % |
| caliper_pyramid | 통과 | 층 64 = 64 (선언 없음), 퍼지선 PRIME, 필라멘트 −0.0001 % |
| voron_design_cube | 통과 | 층 150 = 150 = 150, 필라멘트 +0.0001 %, 파싱 4.9 s |
| simple_cura | 통과 | 층 18 = 18 = 18, 퍼지선 2개 PRIME, 필라멘트 0.0 % |
| xyz_cube_10mm | 멈춤 | 줄 230 `TIMELAPSE_TAKE_FRAME` 뒤 압출 (엄격 모드). 허용하면 층 50 = 50 = 50, +0.0015 % |
| benchy_helix | 멈춤 | 줄 2098 `TIMELAPSE_TAKE_FRAME` 뒤 압출. 허용하면 층 240 = 240 = 240, 0.0 % |
| orca_calib_cube | 멈춤 | 층 표시 줄 3462 안에 압출 Z 5.6과 18.4 (중간 층이 잘린 파일, 의도대로 감지) |

- voron24 정답 지도 (0.02 mm) + 그림: 약 100 s, 방향·모양 정상 (상자 테두리·대각 채움).

**세부청사진과 다르게 한 것**

- ΣΔE 정의를 "층 줄 범위 안 순 ΔE"로 정함 (파일 전체 합은 퍼지선 때문에 simple_cura +7.9 %, caliper +8.2 %).
- 첫 층 표시 앞 압출은 PRIME (층 −1)으로 두고 층 대조와 지도에서 뺌 (§6.4 "뺄 것 없음"과 다름: 퍼지선이 들어가면 격자가 베드 전체가 되고 층 Z도 어긋남).
- GC3 "첫 압출 뒤 모르는 매크로는 오류"를 "압출 사이면 오류, 마지막 압출 뒤는 경고"로 좁힘 (`END_PRINT` 때문).
- 손 G코드를 21개에서 24개로 늘림 (후보 함정 H22–H24).

남은 문제:
1. GC12 대기: 사용자 선택 뒤 복사·MANIFEST·그림 (S5).
2. `TIMELAPSE_TAKE_FRAME`을 허용 목록에 넣을지 (Klipper timelapse 매크로가 위치를 되돌리는지 [확인 필요]).
3. Klipper의 G90/G91 E 동작과 원호 P 뜻 [확인 필요]. 후보 파일에는 영향 없음.
4. 정답 지도 속도 (voron24 약 100 s, 150층 이상은 안 돌려 봄).
5. `width_model: extrusion`에서 w_eff가 명목값보다 아주 조금 작으면 채움 사이 가운데 칸 줄이 빔.
