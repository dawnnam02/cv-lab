# 세부청사진 T4a · G코드 해석과 층별 정답 높이 지도 1차

> **개정 2026-10-27 (3차 검증 정정 + D-19):** GC3 처리 범위를 시작 · 압출 사이 (G-1 위치 다시 정하기) · 끝 구간으로 나눔, GC7 순 ΔE 정의, PRIME 처리, GC12를 D-19 선택 · 실제 위치 (`data/gcode_samples/MANIFEST.csv`, 그림 `results/gcode_t4a_gc12/`)로 맞추고 unknown 0 조건과 G-1 경고의 관계 정리, 속도 기준 GC16 추가. 결과는 §12.
> 상위: [청사진_가상데이터단계](청사진_가상데이터단계.md) §2.1 (워크플로우 1단계 정답) · §4.1 (T4a · T4b) · §4.3 (T4a) · §5 · 작성: 2026-10-27 총괄 팀장 · 상태: **완료 (10-27, 98bbcdf). [팀장검증 3차](팀장검증_3차.md) 통과, 후속 G-1 – G-3 (94cc48b) · GC12 (d323dac) 끝**
> **T4를 둘로 나눔 (청사진은 고치지 않음, 메인에게 보고).** T4a = G1 파싱 · G2 비드 모델 · G3 층별 정답 높이 지도를 **사용자 G코드 없이** 만드는 1차. T4b = G4 판정 영역, 사용자 G코드 맞춤 (다시 슬라이스 필요 여부 포함), 측정 격자와의 정렬. T4b는 사용자 G코드와 T5 점검 뒤에 따로 세부청사진을 씁니다.
> **일정 앞당김.** 청사진 T4는 11-05 ~ 11-17 (T5 뒤)입니다. 사용자 지시 (10-27) "선행 작업 없이 병렬로 진행할 수 있는 작업 진행해."에 따라 T4a를 **10-27에 시작**합니다 (9일 앞당김).
> **시험 G코드 (메인 지시 10-27 반영).** 공개 G코드는 따로 모으지 않습니다. 다른 worker가 내려받는 후보 (`data/gcode_candidates/`, 보고서 `docs/테스트-G코드-후보.md`)를 씁니다. 후보 폴더는 **읽기 전용**입니다. **사용자가 고른 파일만** `data/gcode_samples/`로 복사해 씁니다.
> **사용자 선택 (D-19, 10-27).** 첫 파이프라인 시험 `voron24_test_box`, 판정 시험 `caliper_pyramid`. 라이선스 [미상]이라 `data/gcode_samples/_local/` (gitignore)에만 복사하고 커밋하지 않습니다.
> 함께 도는 작업: [T6 저장소 골격·검증기](세부청사진_T6_저장소골격·검증기.md) · [T15 합격 판정](세부청사진_T15_합격판정.md). **5절 소유 표를 지킵니다.**

| 항목 | 내용 |
|---|---|
| Plane | G1 · G2 · G3 (G4는 T4b). 상태 바꾸기는 메인 몫 |
| 담당 | 기준모델 담당 (청사진 §5.1), Opus 5.5, effort medium. **같은 담당이 G코드 후보 작업 중이면 그 작업을 끝낸 뒤 시작하거나 새 worker 인스턴스로** (한 worker 한 작업, §5.1). 독립 검증: 팀장 |
| 기간 | 2026-10-27 ~ 11-04 → **10-27에 모두 끝남** (후보 실행 S5 · S7도 D-19 선택 당일) |
| 선행 | 없음으로 시작 (손 G코드). 후보 실행은 ① 후보 보고서 ② 사용자 선택 (메인이 받아 전달) |
| 후행 | T4b (G4 · 사용자 G코드) · T5 (G코드 점검이 이 파서를 씀) · T3 (참 형상 = 정답 + 출력 오차, 층 표를 씀) · T9 · T10 (정답 높이 지도와 격자) |
| 산출물 | 5절 "T4a 소유" 경로 · `docs/G코드-해석.md` · `docs/운영/결과_T4a_대조표.md` |

## 1. 목적

G코드 한 파일을 읽어 다음 셋을 만듭니다.

1. **선분 표 (G1).** 노즐이 어디서 어디로, 몇 번째 층에서, 어떤 경로 종류로, 재료를 얼마나 내며 움직였는지.
2. **층 표.** 층 번호 (0부터), 층 Z, 층 높이, 그 층의 G코드 줄 범위. 명세 `meta.layer_idx` · `meta.layer_z_mm` · `meta.gcode_line_start` · `meta.gcode_line_end` · `meta.layer_count`가 이 표에서 나옵니다.
3. **층별 정답 높이 지도 (G2 · G3).** 층 n까지 출력했을 때 위에서 본 윗면 높이 Z_ref(x, y, n), {G} Z, 베드 면 = 0. 층마다 재는 실측 지도와 같은 격자 (§6.1).

정답이 틀리면 판정 전체가 틀립니다. 측정 오차와 구분할 방법도 없습니다 (MF-GCD-04 · 05 · 06, S5). 그래서 방언을 못 읽으면 조용히 넘어가지 않고 멈추는 쪽으로 만듭니다.

## 2. 목표 (완료 기준)

| 번호 | 완료 기준 | 측정 방법 |
|---|---|---|
| GC1 | **파서 기본 (G1).** G0 · G1 · G2 · G3 (I·J 중심과 R, 시계·반시계, 전체 원, 현 길이 ≤ 0.1 mm), G90 · G91, M82 · M83, G92 (X Y Z E), G20 · G21, G28, G10 · G11 (펌웨어 리트랙트), `N`줄 번호·`*`체크섬, `;`·`( )` 주석, `\r\n`, 공백 없는 단어 (`G1X10Y5E.3`), 소문자. 선분 표 열은 §4 고정 | 명령 ① · ② |
| GC2 | **선분 종류 (MF-GCD-06).** extrude (XY 이동 + E 증가) · travel · retract · unretract · wipe (XY 이동 + E 감소) · zmove. 정답 경로는 extrude만. E 증분이 0 이하인 이동은 경로가 아님 | 명령 ① |
| GC3 | **모르는 명령 (MF-GCD-04, 3차 검증 정정).** 명령을 세 목록 (움직임 · 상태 · 움직임 없음)으로 나누고, 밖이면 셈. 처리는 위치에 따라 다름: ① **첫 압출 전 (시작 구간)** 매크로 (`PRINT_START` 등)는 통과 + 경고 ② **압출 사이**는 엄격 모드 (기본)에서 **위치 다시 정하기 규칙 (G-1, §6.2)** 을 만족하면 통과 + 경고 (줄 번호 · 매크로 이름), 못 맞추면 `GCodeError` ③ **마지막 압출 뒤 (끝 구간)** 는 경고만 (정답 경로에 닿지 않음. 예: voron24 2906줄 `END_PRINT`). G · M · T 꼴의 모르는 코드는 위치와 상관없이 바로 오류 (H16 `M999X`). `config/gcode.yaml` 허용 목록에 이유와 함께 더할 수 있으나 기본은 `[]`. `TIMELAPSE_TAKE_FRAME`은 허용 목록에 넣지 않고 G-1 규칙으로 처리 | 명령 ① · ② |
| GC4 | **층 정하기 (MF-GCD-05).** ① 주석 기준 (PrusaSlicer `;LAYER_CHANGE` + `;Z:`, Cura `;LAYER:n`, Orca·Bambu `; CHANGE_LAYER` + `; Z_HEIGHT:`) ② 압출 Z 기준 (압출 선분이 있는 Z, 오름차순) 둘 다 계산해 층 수와 층 Z가 같아야 통과. 다르면 기본 오류. 층 번호는 압출 있는 층만 0부터. Z hop은 층을 늘리지 않음. 가변 층 높이 지원. 한 층 안 압출 Z가 둘 이상 (차 > 0.0001 mm)이면 오류 (나선·비평면). Z가 내려가는 압출 (순차 출력)이면 오류 | 명령 ① · ② |
| GC5 | **층 표.** 열: `layer_idx, layer_z_mm, layer_h_mm, gcode_line_start, gcode_line_end, n_extrude, extrude_len_mm, sum_de_mm, types`. 층 높이 = 이번 층 Z − 앞 층 Z (첫 층은 첫 층 Z). 줄 범위 규칙 §6.3. 다음 층 시작 줄 > 이번 층 끝 줄 | 명령 ① |
| GC6 | **머리말 읽기.** 슬라이서 이름·판, 방언 원문, 명세 값 `meta.gcode_flavor` ∈ {marlin, klipper, reprap, other}로 옮긴 값 (옮김 표는 문서 §1), 선언 층 수, 선언 필라멘트 길이, 노즐 지름, 선폭, 층 높이, 필라멘트 지름, 파일 SHA-256. 못 찾으면 None과 경고 | 명령 ① · ③ |
| GC7 | **압출량 대조 (G1 기준).** ΣΔE와 슬라이서 선언 필라멘트 길이의 차 ≤ 1 %. **ΣΔE = 층 줄 범위 안 모든 선분의 ΔE 합** (압출 + 리트랙트 · 되밀기 · 와이프가 서로 상쇄된 순 사용량). 시작 퍼지선 (PRIME)과 마지막 압출 뒤 끝 G코드의 ΔE는 뺌 (슬라이서 선언 길이가 이것들을 세지 않음. 파일 전체 합은 simple_cura +7.9 % · caliper +8.2 %로 어긋남). 선언이 없으면 `[미상]` | 명령 ③ |
| GC8 | **비드 모델 (G2).** 단면 사각형 + 양 끝 반원: A = (w − h)·h + π·h²/4 (w ≥ h에서만). `bead_area(0.42, 0.2)` = 0.0754159 ± 1e-6 mm² (G2 표). 역산 `width_from_area`가 1e-9 안에서 되돌아감. 압출량 기반 선폭 w_eff (0.5 mm보다 짧은 선분 뺌). **정답 높이 정의 (MF-GCD-01): 기본은 층 Z (노즐 끝 Z = 비드 윗면, flat).** 대안 (비드 단면 윗면 모양)은 민감도용 함수로만. 첫 층 눌림 (MF-GCD-03)은 넣지 않고 첫 층 두께를 층 표에 따로 둠 | 명령 ① |
| GC9 | **층별 정답 높이 지도 (G3).** §6.1 격자, 범위 = 압출 선분 (PRIME 제외, §6.4) 경계 상자 + 1 mm. 층 n 발자국 = 층 n 압출 선분마다 캡슐 (거리 ≤ w/2) 안의 칸. Z_ref(x, y, n) = 그 칸을 덮은 층 k ≤ n 중 가장 높은 z_k, 없으면 NaN. 꼭대기 층 번호 (없으면 −1)·경로 종류 지도도 냄. 저장 `npz` (층 마스크는 `np.packbits`), 다시 읽으면 배열이 모두 같음 | 명령 ① |
| GC10 | **지도 해석해 시험.** ① 정해진 칸의 높이가 층 Z와 1e-9 mm 안 ② 선분 하나의 발자국 면적 vs L·w + π(w/2)² 상대 차 ≤ 1 % ③ 선폭 간격으로 나란한 채움 안쪽 빈칸 0 ④ 같은 입력 두 번 → `np.array_equal` ⑤ L자처럼 비대칭인 모양에서 위아래·좌우가 선분 좌표와 같음 | 명령 ① |
| GC11 | **손 G코드 ≥ 18개 (§6.5).** `data/gcode_samples/hand/H01_*.gcode` …, 기대값 표 `data/gcode_samples/hand/기대값.csv` (열 고정: `파일, 항목, 기대값, 허용차, 근거식`). 슬라이서 형식을 흉내 낸 파일은 이름에 `_mimic`을 붙이고 "실제 슬라이서 출력 아님"을 표에 적음 | 명령 ② |
| GC12 | **사용자가 고른 후보 G코드 (D-19, 실제 위치로 정정).** 고른 파일만 `data/gcode_samples/public/` (재배포 허락이 확인된 것) 또는 `data/gcode_samples/_local/` (허락 없음·[미상], Git 밖)으로 **복사**. 목록은 **`data/gcode_samples/MANIFEST.csv`** (커밋 대상, 고정 7열 `파일, sha256, 원래경로, 출처URL, 라이선스, 고른날짜, 위치`를 반드시 포함. 더한 열 `이름 · 슬라이서 · 방언 · 층수 · 최대Z_mm · 역할 · 로컬경로`는 허용. 위치는 `public` 또는 `_local`, 출처·라이선스는 `docs/테스트-G코드-후보.md`에서 옮김). 파일마다: 모르는 명령 0 (허용 목록이면 이유. G-1과의 관계는 §6.8), 체크섬 불량 0, 층 수 주석 = 압출 Z (= 선언 층 수가 있으면 그것도), 층 Z와 주석 Z 차 ≤ 0.0001 mm, GC7, 파싱 시간 기록, 첫·가운데·마지막 층 정답 지도 그림. **그림 · 지도 · 층 표는 `results/gcode_t4a_gc12/` (gitignore)** 에 둠: 라이선스 미상 파일에서 나온 산출물이라 커밋하지 않고, 수치만 `docs/G코드-해석.md`에 적음. D-19: `voron24_test_box` · `caliper_pyramid` 둘 다 `_local` | 명령 ③ · ⑤ |
| GC13 | **후보 폴더 그대로.** `data/gcode_candidates/`의 파일 목록과 SHA-256이 시작과 끝에 같고, T4a가 그 안에 만든 파일 0 | 명령 ④ |
| GC14 | **문서.** `docs/G코드-해석.md` 절 0–9 (§4 목차). MF-GCD-01–08 대응표 (T4a에서 처리 · T4b · T15 · T5 중 어디서), T4b에 넘길 것, 방언 → 명세 값 옮김 표 | 명령 ⑥ |
| GC15 | **시험·차단.** `tests/gcode/` 시험 함수 ≥ 30개 모두 통과, 120 s 이내. `cvlab.judge` · `cvlab.io` · `cvlab.sim` import 0, `_truth` 언급 0, 소유 위반 0 | 명령 ① · ⑦ · ⑧ |
| GC16 | **정답 지도 속도 (G-2, 3차 검증 뒤 추가).** voron24_test_box `build_reference` ≤ 15 s. 새 방식과 1차 방식 (`method="window"`, 남겨 둠)의 `footprint` · `type_at`이 H20 · H21 · voron24 모든 층에서 `np.array_equal`. 150층 voron_design_cube 시간 기록 | §12 · 시험 `test_band_equals_window_*` |

## 3. 입력

| 입력 | 경로 | 쓰는 곳 |
|---|---|---|
| 요소 청사진 | `docs/blueprints/G-reference/G1-gcode-parsing.md` (§2 슬라이서 주석, §4 결정, §6 코드·시험 예, §8 흔한 실수) · `G2-bead-model.md` (§4 결정, §7 기준) · `G3-mask-heightmap.md` (§4 격자·경계 규칙, §7 기준) · `G4-evaluation-masks.md` (T4b에 넘길 것만) | GC1–GC10 |
| 실패사례 | `docs/측정-실패사례.md` 3.13 MF-GCD-01–08 | GC2–GC4 · GC8 · GC14 |
| 명세 | `docs/하드웨어-데이터-명세.md` §5 `meta.layer_idx` · `layer_count` · `layer_z_mm` · `gcode_line_start` · `gcode_line_end` · `gcode_file` · `gcode_sha256` · `slicer_name` · `gcode_flavor` · `layer_h_mm` · `nozzle_dia_mm` · `top_layers` · `infill_angle_deg` | GC5 · GC6 |
| 프린터·펌웨어 1차 결과 | `docs/프린터-펌웨어-선정.md` (Voron Trident + Klipper 1순위, 완성품 Sovol SV08. **확정 아님**) | 방언 우선순위 (Klipper · Marlin) |
| 후보 G코드 | `data/gcode_candidates/` (읽기 전용) · `docs/테스트-G코드-후보.md` (출처·라이선스·추천) | GC12 |
| 사용자 선택 | 메인이 전달 | GC12 |

- 슬라이서를 실행해 새 G코드를 만들지 않습니다 (이 PC에 Bambu Studio가 있어도 쓰지 않음). 공개 G코드를 따로 내려받지 않습니다.
- 저장소 밖 G코드 (예: 다른 프로젝트 폴더의 파일)는 사용자 G코드인지 확인되지 않았으므로 읽지 않습니다.

## 4. 산출물

| 경로 | 내용 |
|---|---|
| `src/cvlab/gcode/__init__.py` | 아래 이름을 내보냄 |
| `src/cvlab/gcode/params.py` | `GCodeParams` (기본값·검사·`from_dict`) |
| `src/cvlab/gcode/parser.py` | 모달 상태 파서, 원호 펼치기, 체크섬, 명령 목록 |
| `src/cvlab/gcode/layers.py` | 층 정하기 두 방법과 대조, 층 표 |
| `src/cvlab/gcode/header.py` | 슬라이서·방언·선언값 읽기 |
| `src/cvlab/gcode/bead.py` | 비드 단면, w_eff |
| `src/cvlab/gcode/grid.py` | 격자 JSON (§6.1) |
| `src/cvlab/gcode/reference.py` | 층별 정답 높이 지도 `RefStack` |
| `config/gcode.yaml` | 최상위 키 `gcode` 하나 (§6.6) |
| `scripts/gcode_reference.py` | 파일 하나 → 요약 한 줄 + (선택) 층 표 CSV · 지도 npz · 그림. 출력 폴더가 `data/gcode_candidates/` 안이면 거부 |
| `tests/gcode/test_gcode_*.py` (+ 도우미 `tests/gcode/gcode_*.py`) | 시험 |
| `data/gcode_samples/hand/` | 손 G코드 + `기대값.csv` + `README.md` |
| `data/gcode_samples/public/` · `_local/` · `MANIFEST.csv` | 사용자가 고른 후보 복사본 (D-19 두 파일은 `_local/`, Git 밖)과 목록 `data/gcode_samples/MANIFEST.csv` (커밋) |
| `results/gcode_t4a_gc12/` | 고른 후보의 층 표 CSV · 정답 지도 npz · 첫·가운데·마지막 층 그림 (Git 밖, 커밋하지 않음) |
| `docs/G코드-해석.md` · `docs/G코드-해석_자료/` | 문서. `_자료/`는 손 G코드처럼 재배포 문제가 없는 것만 (고른 후보에서 나온 그림은 `results/`) |
| `docs/운영/결과_T4a_대조표.md` | 시작 확인 · 종료 대조 |

**공개 이름 (이 이름은 바꾸지 않음, 검증 명령이 씀).**

```python
parse_text(text, params=None) -> ParseResult
parse_file(path, params=None) -> ParseResult          # 파일 바이트 SHA-256 포함
# ParseResult: .segments (DataFrame)  .layers (DataFrame)  .header (dict)  .unknown (dict 명령→횟수)
#              .warnings (list)  .n_lines  .n_checksum_bad
# segments 열: line_no, layer_idx, type, kind, arc, x0_mm, y0_mm, z0_mm, x1_mm, y1_mm, z1_mm, de_mm, length_mm, feed_mm_s
bead_area(w_mm, h_mm); width_from_area(A_mm2, h_mm); effective_width(segments, filament_d_mm, min_len_mm=0.5)
make_grid(xmin, xmax, ymin, ymax, res_mm=0.02, margin_mm=1.0) -> dict      # §6.1 격자 JSON
build_reference(result, grid=None, params=None) -> RefStack
# RefStack: .grid  .z_layers  .footprint(n)  .height_at_layer(n)  .top_layer_at(n)  .type_at(n)  .save(path)  RefStack.load(path)
GCodeError   # 엄격 모드 오류
```

`docs/G코드-해석.md` 목차 (절 번호 고정):

```
# G코드 해석과 층별 정답 높이 지도 (1차)
## 0. 요약
## 1. 입력과 방언
## 2. 파서 규칙
## 3. 층 정하기
## 4. 비드 모델과 정답 높이 정의
## 5. 층별 정답 높이 지도
## 6. 시험 결과
## 7. MF-GCD 대응표
## 8. T4b에 넘길 것
## 9. 한계
```

## 5. 쓰기 범위 (병렬 충돌 방지, 세 작업 공통 표)

| 경로 | T6 | T15 | T4a |
|---|---|---|---|
| `pyproject.toml` · `requirements.txt` (새로) | **만듦** | 읽기만 | 읽기만 |
| `.gitignore` · `README.md` (있음) | **줄 추가만** | 읽기만 | 읽기만 |
| `src/cvlab/__init__.py` | **만듦** (하위 import 금지) | 읽기만 | 읽기만 |
| `src/cvlab/config.py` · `src/cvlab/repro.py` · `src/cvlab/io/**` | **만듦** | import하지 않음 | import하지 않음 |
| `src/cvlab/judge/**` | - | **만듦** | - |
| `src/cvlab/gcode/**` | - | - | **만듦** |
| `config/default.yaml` · `config/README.md` · `config/spec/**` | **만듦** | 읽기만 | 읽기만 |
| `config/judge.yaml` | 읽기만 | **만듦** | - |
| `config/gcode.yaml` | 읽기만 | - | **만듦** |
| `scripts/check_env.py` · `extract_spec_schema.py` · `validate_dataset.py` | **만듦** | - | - |
| `scripts/judge_sensitivity.py` | - | **만듦** | - |
| `scripts/gcode_reference.py` | - | - | **만듦** |
| `tests/infra/**` · `tests/judge/**` · `tests/gcode/**` | infra | judge | gcode |
| `data/raw/.gitkeep` · `data/processed/.gitkeep` · `results/.gitkeep` | **만듦** | - | - |
| `data/gcode_samples/**` | - | - | **만듦** |
| `data/gcode_candidates/**` (G코드 후보 worker 소유) | 손대지 않음 | 손대지 않음 | **읽기만** |
| 문서·대조표 | `docs/명세-검증기.md` · `결과_T6_대조표.md` | `docs/판정-규칙.md` · `docs/판정-규칙_자료/**` · `결과_T15_대조표.md` | `docs/G코드-해석.md` · `docs/G코드-해석_자료/**` · `결과_T4a_대조표.md` |

**모두 금지:** `scripts/method_screening/**` · `tests/test_method_screening.py` · `docs/0_방법탐색/**` (V2 미커밋, 읽기만) · 청사진·명세·실패사례·프린터 선정·요소 청사진·다른 세부청사진 · `docs/테스트-G코드-후보.md` (읽기만) · `docs/운영/plane/**` · `docs/운영/점검일지.md` · **`data/_truth/**`와 `src/cvlab/sim/**` (읽기도 금지)** · `tests/**/__init__.py`, `conftest.py` (만들지 않음).

- 시험 파일·도우미 이름은 `test_gcode_*.py` · `gcode_*.py`로 시작합니다 (pytest 기본 import 방식에서 이름 겹침 오류를 피함). 자기 폴더만 돌립니다.
- T6의 공통 파일이 아직 없어도 `PYTHONPATH=src`로 돌면 됩니다. T6를 기다리지 않습니다.
- 설정은 `config/gcode.yaml`을 `yaml.safe_load`로 직접 읽어 `GCodeParams.from_dict`에 넘깁니다. T6의 `cvlab.config`는 import하지 않습니다.
- `data/gcode_samples/_local/`은 T6가 `.gitignore`에 넣습니다. 그 전에 복사하더라도 커밋은 메인 몫이라 문제없습니다.
- 시험은 `data/gcode_samples/`만 씁니다. 후보 폴더 경로를 시험 코드에 넣지 않습니다. 고른 파일이 아직 없으면 그 시험은 `pytest.skip` (사유 "사용자 선택 대기"). `_local/`이 없는 클론에서도 GC12 시험은 skip, MANIFEST 시험은 통과해야 합니다.
- `results/gcode_t4a_gc12/`는 `.gitignore`의 `results/*`로 무시됩니다. 소유 표에는 없지만 T4a가 쓰는 Git 밖 출력 폴더로 봅니다.

## 6. 설계 규칙

### 6.1 격자 약속 (T15와 같은 글)

| 항목 | 약속 |
|---|---|
| 좌표 | {G}, mm. 높이는 {G} Z, 베드 면 = 0 |
| 배열 순서 | `A[iy, ix]` (G3 · C4) |
| 칸 중심 | x = x0_mm + ix·res_mm, y = y0_mm + iy·res_mm. x0_mm · y0_mm은 res_mm의 정수배 (내림) |
| 격자 JSON | `{"frame": "G", "x0_mm": …, "y0_mm": …, "res_mm": …, "nx": …, "ny": …}` |
| 값 없음 | float 배열은 NaN, 마스크는 bool, 꼭대기 층 번호 없음은 −1 |
| 고운 격자 | res_mm = 0.02 (G3 결정). T15 판정 칸은 이 격자를 정수 배로 묶음 (0.2 mm = 10칸) |

- 그림은 `origin="lower"`와 격자 범위 (`extent`)로 그립니다 (G3 흔한 실수).

### 6.2 파서 규칙 (G1 결정 유지, 다른 점만)

| 규칙 | 내용 | 근거 |
|---|---|---|
| 원호 | 현 길이 ≤ `arc_seg_mm` 0.1 mm. I·J는 시작점 기준 상대값. R < 0은 긴 원호 | G1 §4 |
| G90/G91과 E | `g9x_sets_e` 기본 true (Marlin 동작), M82/M83이 덮어씀. Klipper 동작은 공식 문서로 확인해 문서 §2에 적음 ([확인 필요]) | G1 §4 |
| 체크섬 틀린 줄 | 쓰지 않고 셈. 0이 아니면 경고 | G1 §4 |
| G10/G11 | 펌웨어 리트랙트. 길이를 모르므로 E는 바꾸지 않고 종류만 기록 | G1 · MF-GCD-04 |
| 명령 목록 | 움직임 (G0–G3, G28, G92), 상태 (G90/G91, M82/M83, G20/G21), 움직임 없음 (온도·팬·진행률·가속 설정 등). 목록은 코드 한 곳에 두고 문서 §2에 표로 | MF-GCD-04 |
| 경로 종류 이름 | 슬라이서 이름 → 표준 이름 (G1 `TYPE_ALIASES` 방식). 모르는 이름은 대문자 그대로 두고 경고. 아이롱은 `IRONING`으로 따로 (MF-GCD-07) | G1 §2 |
| 압출 사이 매크로 (G-1, 3차 검증 뒤) | 엄격 모드에서 압출 사이 매크로 (EDGE 포함) 뒤, 다음 압출 전에 ① 절대 좌표 G0/G1로 X · Y · Z가 모두 한 번 이상 정해지고 ② E가 상대 모드 (M83 · G91 Marlin식)이거나 G92 E가 있으면 통과 + 경고 (줄 번호 · 매크로 이름). 세지 않는 것: 상대 이동, `G92 X/Y/Z`, 매크로 앞 `G92 E`, 압출하는 줄 자신의 좌표. 매크로 뒤 `G28`로 홈 잡은 축은 다시 정해야 함. 매크로가 또 오면 처음부터 다시 셈. 못 맞추면 `GCodeError` | 3차 검증 §3.6 · 매크로 속을 믿지 않아도 위치를 아는 상태이면 정답이 틀릴 수 없음 |
| 끝 구간 | 마지막 압출 뒤 명령은 경고만 (`END_PRINT` · `M702` 등) | 3차 검증 §3.6 ③ |

### 6.3 층과 줄 범위

| 항목 | 규칙 |
|---|---|
| 층 Z | 그 층 압출 선분 Z (모두 같아야 함, 차 ≤ 0.0001 mm) |
| 줄 범위 (주석 있음) | 층 n 시작 = 층 n 표시 줄. 층 n 끝 = 층 n+1 표시 줄 − 1. 마지막 층 끝 = 그 층 마지막 압출 줄 |
| 줄 범위 (주석 없음) | 층 n 시작 = 층 n−1 마지막 압출 줄 + 1 (층 0은 첫 압출 앞 마지막 Z 이동 줄). 끝은 위와 같음 |
| 압출 없는 주석 층 | 층으로 세지 않고 경고 (예: 이동만 있는 층) |
| 층 번호 | 0부터, 압출 있는 층만 |
| 대조 | 주석 기준과 압출 Z 기준이 층 수·층 Z 모두 같아야 통과. `layer_source: comment` 또는 `z`로 바꾸면 경고를 남기고 한쪽만 씀 |

- 명세 `meta.layer_z_mm` 규칙 (G코드 층 Z와 차 ≤ 0.0001 mm)과 같은 허용차를 씁니다.

### 6.4 정답 높이 지도

| 항목 | 규칙 | 근거 |
|---|---|---|
| 발자국 | 압출 선분 (x0, y0) → (x1, y1)에서 칸 중심까지 거리 ≤ w/2 + 1e-9 mm | 캡슐 = G2 단면의 위에서 본 모양. 선폭 간격 채움에 틈이 안 생기게 닫힌 경계 |
| 선폭 w | 기본 명목 선폭 (머리말, 종류별). 없으면 `config/gcode.yaml`. `width_model: extrusion`이면 w_eff | G2 §4 |
| 높이 | flat: 그 층 Z (MF-GCD-01 기본 정의). 첫 층 눌림·비드 볼록·결은 넣지 않음 | G3 §4 · MF-GCD-01 · 02 · 03 |
| 층 n 지도 | 꼭대기 층 번호 L_n(x, y) = max{k ≤ n : 발자국_k ∋ (x, y)}, Z_ref = z[L_n], 없으면 NaN | 층별 측정 (D-04) |
| 경로 종류 | 꼭대기 층의 종류. 겹치면 FILL → SKIN → WALL-INNER → WALL-OUTER → 스커트·서포트 순으로 뒤가 이김 | G3 §4 |
| 뺄 것 | 층 안의 경로는 없음. 스커트·브림·서포트도 지도에 넣음. 판정에서 빼는 일은 G4 (T4b). **예외: 첫 층 표시 앞 시작 퍼지선은 종류 PRIME · 층 −1로 `segments`에 남기고 층 표 · 정답 지도 · 격자 범위에서 뺌** (넣으면 격자가 베드 전체가 되고 층 Z가 어긋남). T4b는 PRIME을 "출력물 있으나 판정 밖"으로 씀. 층 표시가 없는 파일은 퍼지선이 첫 층과 같은 Z면 층 0에 섞이고, 더 높은 Z면 "Z 내려감" 오류 (한계, 문서 §9) | G3 흔한 실수 · 3차 검증 §3.6 ② |
| 메모리 | 층마다 발자국을 `np.packbits`로 저장, 높이는 그때 계산 | G3 §8 |

### 6.5 손 G코드 (최소 목록, 더해도 됨)

값은 시험용 입력이며 출력물 설계가 아닙니다. 기대값은 손계산이고 `기대값.csv`에 식을 적습니다.

| 파일 | 내용 | 기대 (손계산) |
|---|---|---|
| H01 | 10 mm 정사각형 둘레 (G1 §6.3 SQUARE 꼴) | 압출 선분 4개, 길이 합 40.000 mm |
| H02 | G91 상대 XYZ + M83 상대 E | H01과 같은 선분 |
| H03 | G92 E0 반복 (M82) | 가짜 리트랙트 0, ΣΔE = 선분 E 합 |
| H04 | G20 (inch) | X1 → 25.4 mm |
| H05 | G2 · G3 사분원, I·J와 R 두 방식, r = 10 mm | 길이 5π = 15.70796 mm (오차 < 0.001), 끝점 1 µm 안, 두 방식 같음 |
| H06 | G2 전체 원 (I만, 끝점 = 시작점), r = 5 mm | 길이 10π = 31.41593 mm, 현 ≤ 0.1 mm |
| H07 | 리트랙트·되밀기·와이프 | 종류 retract · unretract · wipe 각 1, 경로 아님 |
| H08 | G10 · G11 | 종류만 기록, E 바뀜 없음 |
| H09 | `N` + `*` 체크섬 (맞는 줄, 틀린 줄) | 틀린 줄 1개 셈·안 씀 |
| H10 | 주석 없는 2층 + 층 사이 Z hop 0.4 mm | 층 2개, Z hop이 층을 늘리지 않음 |
| H11 | 가변 층 Z 0.20 · 0.35 · 0.45 | 층 높이 0.20 · 0.15 · 0.10 |
| H12_mimic | PrusaSlicer 꼴 표시 (`;LAYER_CHANGE`, `;Z:`, `;TYPE:External perimeter`) | 주석·Z 두 방법 일치, 종류 WALL-OUTER |
| H13_mimic | Cura 꼴 (`;FLAVOR:Marlin`, `;LAYER_COUNT:`, `;LAYER:0`, `;TYPE:WALL-OUTER`) | 방언 marlin, 선언 층 수 = 층 수 |
| H14_mimic | Orca·Bambu 꼴 (`; CHANGE_LAYER`, `; Z_HEIGHT:`) | 두 방법 일치 |
| H15_mimic | Klipper 꼴 (`PRINT_START`, `EXCLUDE_OBJECT_DEFINE`, `SET_PRINT_STATS_INFO CURRENT_LAYER=`) | 시작 구간 매크로 통과, 층 일치 |
| H16 | 첫 압출 뒤 모르는 명령 `M999X` | 엄격 모드 `GCodeError`, 허용 목록에 넣으면 통과 + 셈 |
| H17 | 두 번째 물체에서 Z가 내려감 (순차 출력) | `GCodeError` |
| H18 | 나선 (한 층 안 Z 계속 증가) | `GCodeError` |
| H19 | `\r\n`, 소문자, 공백 없는 단어, 주석 안 `E` 글자 | H01과 같은 선분 |
| H20 | 10 × 10 mm 블록 2층, 선폭 0.42 mm 간격 채움 | 층 0 · 1 지도의 정해진 칸 높이 = 0.20 · 0.40 mm, 안쪽 빈칸 0 |
| H21 | L자 2층 | 지도 방향이 선분 좌표와 같음 |
| H22–H24 (`_mimic`) | worker가 더함: 한 층에 층 표시 두 번 (Orca 꼴) · Cura 시작 퍼지선 · 나선 Z hop | `기대값.csv`의 식 |
| H25_mimic | 압출 사이 매크로 → 바로 압출 (G-1) | `GCodeError` |
| H26_mimic | 매크로 → X · Y만 절대 이동 (G-1) | `GCodeError` (메시지에 "다시 정하지 않은 축 Z") |
| H27_mimic | M82 → 매크로 → M83 + X · Y · Z 절대 (G-1) | 통과 + 경고 |

### 6.6 `config/gcode.yaml`

```yaml
gcode:
  arc_seg_mm: 0.1              # G1 결정
  g9x_sets_e: true             # G1 결정 (Marlin 동작). Klipper는 문서 확인 뒤 적음
  strict_unknown: true         # MF-GCD-04
  allow_commands: []           # 예: [{name: M73, reason: "진행률 표시, 움직임 없음"}]. TIMELAPSE_TAKE_FRAME은 넣지 않음 (G-1 규칙으로 처리)
  layer_source: both           # both | comment | z  (MF-GCD-05)
  layer_z_tol_mm: 0.0001       # 명세 meta.layer_z_mm 규칙
  line_width_mm: null          # 머리말 값 우선. 없으면 실행 때 지정
  filament_diameter_mm: null   # 머리말 값 우선. G2는 실측 평균을 권함
  w_eff_min_len_mm: 0.5        # G2 결정
  width_model: nominal         # G2 결정 (nominal | extrusion)
  height_model: flat           # G3 결정, MF-GCD-01 기본 정의
  grid_res_mm: 0.02            # G3 결정
  grid_margin_mm: 1.0          # 팀장 안
```

- 모르는 키는 오류입니다. 값마다 주석 근거를 유지합니다.

### 6.7 MF-GCD 대응 (문서 §7의 출발점)

| ID | T4a에서 하는 것 | 남는 곳 |
|---|---|---|
| MF-GCD-01 비드 꼭대기 정의 | 기본 정의 = 층 Z (flat), 대안 함수 | 비드 오프셋 교정은 보조 시편 (T5 · E3) |
| MF-GCD-02 결 | 비드 간격·선폭·채움 방향을 층 표·머리말에 남김 | 판정 칸 크기 T15, 결을 지도에 넣을지 T4b |
| MF-GCD-03 첫 층 눌림 | 첫 층 두께를 따로 둠 | 정답 모델에 넣을지 T15 · T4b |
| MF-GCD-04 방언 | 모르는 명령 세기·멈춤, 원호 펼치기, 펌웨어 리트랙트 | 사용자 G코드 방언 확인 T5 |
| MF-GCD-05 층 | 두 방법 대조, 가변 층, Z hop | 측정 층 Z와 자동 대조 T10 |
| MF-GCD-06 가짜 면 | extrude만 경로, M82/M83, 와이프 제외 | - |
| MF-GCD-07 아이롱 | `IRONING` 종류로 표시 | 정답 높이에 넣을지 T4b |
| MF-GCD-08 여러 번 스캔 | 출력 범위만 층 표에 | 스캔 나누기 T5 · T4b |

### 6.8 GC12 "모르는 명령 0"과 G-1 경고의 관계 (3차 검증 뒤 정리)

`summary()["unknown"]`은 목록 밖 명령을 위치와 상관없이 셉니다. 그래서 시작 구간에서 통과한 매크로와 G-1로 통과한 매크로도 unknown에 들어갑니다. 팀장 재실행 (10-27): `xyz_cube_10mm` unknown 50 = G-1 통과 49 + 시작 구간 통과 1 (줄 129), `benchy_helix` 240 = 239 + 1.

| 고른 파일 | GC12 판정 |
|---|---|
| unknown 0인 파일 (D-19 두 파일: voron24 · caliper 모두 unknown 0, G-1 경고 0) | 원래 조건 그대로 (unknown = 0). 시험 `test_picked_samples_pass_checks`도 그대로 |
| G-1로 통과하는 매크로가 있는 파일 (xyz_cube · benchy 같은 것을 나중에 고를 때) | 조건을 "엄격 모드로 `GCodeError` 없이 파싱 + unknown의 명령이 모두 매크로 꼴 (G · M · T 꼴 아님)이고, 그 횟수 = 시작·끝 구간 통과 경고 수 + G-1 통과 경고 수"로 바꿈. 시험도 이에 맞게 고침 (T4a 몫, 그 파일을 고를 때) |

- G-1 경고는 오류가 아니라 "위치를 아는 상태에서 넘어간 매크로"의 기록입니다. 다만 매크로 안에서 모드 (G91 · M82 · 단위)를 바꾸고 되돌리지 않으면 이 규칙으로 못 잡으므로 (문서 §9), 경고 수를 대조표와 보고서에 그대로 남깁니다.
- 허용 목록 (`allow_commands`)에 이유와 함께 넣은 명령은 원래 문장대로 셈에 남되 GC12를 막지 않습니다.

## 7. 단계

| 단계 | 날짜 | 할 일 | 끝난 표시 |
|---|---|---|---|
| S1 | 10-27 | 시작 확인 (§10). 후보 폴더 지문 기록. 손 G코드 H01–H09 | 대조표 · 파일 |
| S2 | 10-28 ~ 10-29 | 파서·선분 종류·모르는 명령·층 정하기·층 표, H10–H19, 시험 | 명령 ① · ② |
| S3 | 10-30 | 머리말·압출량 대조. 후보 보고서가 있으면 후보를 **읽기만** 해서 개발 실행 (출력은 `$TEMP`) | 명령 ① |
| S4 | 10-31 ~ 11-01 | 비드 모델, 정답 높이 지도, H20 · H21, 해석해 시험 | 명령 ① |
| S5 | 11-02 ~ 11-03 | 사용자 선택을 받으면 고른 파일 복사·`MANIFEST.csv`·실행·그림. 선택이 없으면 GC12 "대기" | 명령 ③ · ⑤ |
| (실제) | 10-27 | 1차 S1–S6 끝 (98bbcdf). 3차 검증 후속 G-1 – G-3 (94cc48b). D-19 선택 당일 S7 "후보 반영" 절 (d323dac) | 대조표 |
| S6 | 11-04 | 문서, 검증 명령 전부, "종료 대조" → 팀장 검증 | 대조표 |
| S7 | 선택 도착 때 | S6 뒤에 선택이 오면 S5만 하고 대조표에 "후보 반영" 절 | 대조표 절 |

## 8. 검증

### 8.1 검증 명령 (Git Bash에 그대로 붙여 넣기)

① 시험

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m pytest tests/gcode -q -p no:cacheprovider -rs --durations=5 2>&1 | tail -20 && echo '--- 시험 함수 수' && cat tests/gcode/test_gcode_*.py | grep -c -E "^def test_"
```

② 손 G코드와 기대값 (팀장이 손계산과 대조)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python - <<'EOF'
import csv,glob,math,os
from cvlab.gcode import parse_file, bead_area, width_from_area, GCodeError
H=sorted(glob.glob('data/gcode_samples/hand/H*.gcode')); print('손 G코드',len(H))
E=list(csv.DictReader(open('data/gcode_samples/hand/기대값.csv',encoding='utf-8')))
print('기대값 행',len(E),'/ 식 빈 행',[r['파일'] for r in E if not r['근거식'].strip()])
print('기대값 없는 파일',[os.path.basename(h) for h in H if not any(r['파일'] in h for r in E)])
def ext(f):
    r=parse_file(f); s=r.segments; e=s[s.kind=='extrude']; return r,e
r,e=ext(glob.glob('data/gcode_samples/hand/H01*.gcode')[0]); print('H01 압출',len(e),'길이 합',round(e.length_mm.sum(),6),'기대 4 · 40.0')
r,e=ext(glob.glob('data/gcode_samples/hand/H05*.gcode')[0]); print('H05 원호 길이 합',round(e.length_mm.sum(),6),'기대',round(2*5*math.pi,6),'(사분원 2개 = 2 × 5π)')
r,e=ext(glob.glob('data/gcode_samples/hand/H11*.gcode')[0]); print('H11 층 Z',r.layers.layer_z_mm.round(6).tolist(),'층 높이',r.layers.layer_h_mm.round(6).tolist())
for k in ['H16','H17','H18']:
    try: parse_file(glob.glob('data/gcode_samples/hand/%s*.gcode'%k)[0]); print(k,'오류 안 남 (✗)')
    except GCodeError as x: print(k,'오류 남 (○)',str(x)[:60])
print('bead_area(0.42,0.2)',round(bead_area(0.42,0.2),7),'기대 0.0754159 / 역산',abs(width_from_area(bead_area(0.42,0.2),0.2)-0.42)<1e-9)
EOF
```

- H05 기대값 줄은 H05에 사분원 두 개 (I·J 하나, R 하나)를 넣은 경우입니다. 구성이 다르면 `기대값.csv`의 식으로 대조합니다.

③ 고른 후보 G코드 실행 (S5 뒤. 요약 줄 형식 `SUMMARY {json}` 고정)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && for f in data/gcode_samples/public/*.gcode data/gcode_samples/public/*.gco data/gcode_samples/_local/*.gcode data/gcode_samples/_local/*.gco; do [ -f "$f" ] || continue; echo "=== $f"; PYTHONIOENCODING=utf-8 PYTHONPATH=src python scripts/gcode_reference.py "$f" --summary --out "$TEMP/t4a_out" 2>&1 | grep -E "^SUMMARY|Error|오류"; done
```

판정용 요약 키: `lines, unknown (0), checksum_bad (0), layers_comment = layers_z (= layers_declared가 있으면 같음), z_max_diff_mm ≤ 0.0001, filament_diff_pct ≤ 1 (또는 null + [미상]), parse_s, gcode_sha256`.

④ 후보 폴더 그대로 (시작 때 출력을 대조표에 붙이고, 끝에 다시 돌려 같아야 함)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && find data/gcode_candidates -type f -print0 | sort -z | xargs -0 sha256sum | sed 's/ \*/  /' && echo "파일 수: $(find data/gcode_candidates -type f | wc -l)"
```

⑤ 복사본 목록 (GC12)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import csv,hashlib,os
m='data/gcode_samples/MANIFEST.csv'
if not os.path.exists(m): raise SystemExit('MANIFEST 없음 (사용자 선택 대기면 정상)')
R=list(csv.DictReader(open(m,encoding='utf-8')))
sha=lambda p: hashlib.sha256(open(p,'rb').read()).hexdigest()
for r in R:
    cp=os.path.join('data/gcode_samples',r['위치'],r['파일'])
    print(r['파일'],'| 복사본 있음',os.path.exists(cp),'| 원본과 같음',os.path.exists(r['원래경로']) and os.path.exists(cp) and sha(cp)==sha(r['원래경로'])==r['sha256'],'| 라이선스',r['라이선스'] or '빈칸','| 위치',r['위치'])
print('빈 칸 있는 행',[r['파일'] for r in R if any(not r[k].strip() for k in ['파일','sha256','원래경로','출처URL','라이선스','고른날짜','위치'])])
print('허락 미상인데 public',[r['파일'] for r in R if r['위치']=='public' and ('미상' in r['라이선스'] or not r['라이선스'].strip())])
EOF
```

⑥ 문서 구조

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import re
t=open('docs/G코드-해석.md',encoding='utf-8').read()
print('절 누락',[h for h in map(str,range(10)) if not re.search(r'^## %s\. '%h,t,re.M)])
print('MF-GCD 빠짐',['MF-GCD-%02d'%i for i in range(1,9) if 'MF-GCD-%02d'%i not in t])
for k in ['marlin','klipper','T4b','flat','layer_z_mm','gcode_line_start']: print(k,k in t)
print('근거 태그 수',len(re.findall(r'\[(계산|추정|미상|출처|확인 필요)',t)))
EOF
```

⑦ 정보 차단·독립

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && grep -rn -E "cvlab\.(judge|io|sim|config|repro)|_truth|gcode_candidates" src/cvlab/gcode tests/gcode; echo "grep exit=$? (1이면 0건)"; echo '--- 스크립트 안 후보 폴더 언급 (쓰기 거부 코드만 있어야 함)'; grep -n "gcode_candidates" scripts/gcode_reference.py
```

⑧ 소유 검사 (세 작업 공통, T6 세부청사진 명령 ⑧의 소유 부분과 같음)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import re,subprocess
own=[('T6',('pyproject.toml','requirements.txt','.gitignore','README.md','src/cvlab/__init__.py','src/cvlab/config.py','src/cvlab/repro.py','src/cvlab/io/','config/default.yaml','config/README.md','config/spec/','scripts/check_env.py','scripts/extract_spec_schema.py','scripts/validate_dataset.py','tests/infra/','data/raw/.gitkeep','data/processed/.gitkeep','results/.gitkeep','docs/명세-검증기.md','docs/운영/결과_T6_대조표.md')),
('T15',('src/cvlab/judge/','tests/judge/','config/judge.yaml','scripts/judge_sensitivity.py','docs/판정-규칙.md','docs/판정-규칙_자료/','docs/운영/결과_T15_대조표.md')),
('T4a',('src/cvlab/gcode/','tests/gcode/','config/gcode.yaml','scripts/gcode_reference.py','data/gcode_samples/','docs/G코드-해석.md','docs/G코드-해석_자료/','docs/운영/결과_T4a_대조표.md')),
('V2',('scripts/method_screening/','tests/test_method_screening.py','docs/0_방법탐색/')),
('운영',('docs/운영/','docs/검토-기록.md','docs/테스트-G코드-후보.md','data/gcode_candidates/'))]
out=subprocess.run(['git','-c','core.quotepath=false','status','--porcelain','-uall'],capture_output=True,text=True,encoding='utf-8').stdout
bad=[]
for l in out.splitlines():
    p=l[3:].strip().strip('"').split(' -> ')[-1]
    if '__pycache__' in p: continue
    o=next((n for n,ps in own if any(p==x or p.startswith(x) for x in ps)),'소유자 없음')
    print(o.ljust(6),l[:2],p)
    if o=='소유자 없음' or p.endswith('conftest.py') or re.search(r'^tests/.*__init__\.py$',p): bad.append(p)
print('--- 위반',bad)
EOF
```

판정: ① 모두 통과 (D-19 두 파일이 `_local/`에 있으면 skip 0, 없는 클론에서는 "사용자 선택 대기" 1개만), 함수 ≥ 30, 120 s 이내. ② 손 G코드 ≥ 18, 식 빈 행·기대값 없는 파일 빈 목록, 줄마다 기대와 같음, H16–H18 "(○)", bead 두 값 맞음. ③ 고른 파일마다 요약 키가 판정 조건 안 (선택 대기면 출력 없음). ④ 시작과 끝 출력이 같음. ⑤ 복사본·원본 같음 True, 빈 칸·허락 미상 public 빈 목록. ⑥ 절 누락·MF-GCD 빠짐 빈 목록, 키워드 True. ⑦ grep exit=1, 스크립트 언급은 쓰기 거부 줄만. ⑧ 위반 빈 목록.

### 8.2 팀장 검사

- 손 G코드 3개 (H05 · H10 · H20)를 열어 기대값을 팀장이 손으로 다시 계산합니다. 3/3.
- 고른 후보 하나에서 층 3개 (첫 · 가운데 · 마지막)의 G코드 줄 범위를 열어, 층 표의 Z · 시작 줄 · 끝 줄이 원문과 같은지 봅니다.
- 고른 후보마다 unknown 수와 G-1 · 시작·끝 구간 경고 수를 맞춰 봅니다 (§6.8).
- 정답 지도 그림 하나를 G코드 경로 그림과 겹쳐 방향 (위아래·좌우)을 봅니다.
- `scripts/gcode_reference.py`에 `--out data/gcode_candidates/x`를 주어 거부되는지 봅니다.

## 9. 금지 사항

- 공개 G코드를 따로 내려받지 않습니다. 슬라이서를 실행해 G코드를 만들지 않습니다.
- `data/gcode_candidates/`는 읽기만 합니다. 파일을 옮기거나 지우거나 고치지 않고, 그 안에 결과를 쓰지 않습니다. 사용자가 고른 파일만 `data/gcode_samples/`로 복사합니다 (원본은 그대로).
- 저장소 밖 G코드를 읽지 않습니다 (사용자 G코드로 확인된 것만, 메인이 경로를 줄 때).
- 숫자를 지어내지 않습니다. 설정 값은 요소 청사진 결정·명세 규칙·`[추정]` (이유) 중 하나를 붙입니다. 손 G코드 값은 "시험용 입력"으로 표시합니다. 슬라이서 형식을 흉내 낸 파일은 `_mimic`으로 표시합니다.
- `data/_truth/`와 `src/cvlab/sim/`을 읽지 않습니다. `cvlab.judge` · `cvlab.io` · `cvlab.config`를 import하지 않습니다.
- V2 미커밋 파일을 고치거나 되돌리지 않습니다. git 쓰기 명령을 쓰지 않습니다 (읽기만).
- `pip install` · 유료 API · Plane 수정을 하지 않습니다.
- 5절 소유 표 밖의 파일을 만들거나 고치지 않습니다. G1–G4 요소 청사진은 고치지 않고 문서 §9에 바꿀 점을 목록으로만 적습니다.
- 범위를 바꾸고 싶으면 (예: G4를 당겨 하기) 멈추고 팀장에게 보고합니다.

## 10. 시작 확인 항목

`docs/운영/결과_T4a_대조표.md`를 만들고 "시작 확인" 절에 적은 뒤 시작합니다.

- [ ] 브랜치·HEAD, `git status --short` 기준선, V2 파일 지문 `sha256sum scripts/method_screening/*.py tests/test_method_screening.py` (끝날 때 다시 재서 같아야 함)
- [ ] 목표 GC1–GC15를 자기 말로 한 줄씩
- [ ] §3 입력 파일이 모두 있는지. `docs/테스트-G코드-후보.md`가 있는지, 없으면 "후보 작업 진행 중"
- [ ] 검증 명령 ④ 출력 (후보 폴더 지문, 0개여도 적음)
- [ ] 사용자 선택 상태 (메인에게 확인: 대기·고른 파일 이름)
- [ ] Python·numpy·pandas 판
- [ ] 5절 소유 표를 읽었고 T6 · T15 경로와 후보 폴더를 건드리지 않는다는 확인
- [ ] 마감: 전체 11-04, 후보 실행은 선택 뒤

## 11. 종료 대조표 양식

```markdown
## 종료 대조 (2026-11-04 HH:MM)

| 목표 항목 | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| GC1 파서 기본 | 명령 n종, 시험 n개 | 명령 ① · ② | |
| GC2 선분 종류 | 6종, 경로는 extrude만 | 명령 ① | |
| GC3 모르는 명령 | 엄격 모드 오류, 허용 목록 n개 (이유) | 명령 ② (H16) | |
| GC4 층 정하기 | 두 방법 대조, H10 · H11 · H17 · H18 | 명령 ② | |
| GC5 층 표 | 열 9개, 줄 범위 규칙 | 명령 ① | |
| GC6 머리말 | 슬라이서 n종 옮김 표 | 문서 §1 | |
| GC7 압출량 | 파일별 차 % (또는 [미상]) | 명령 ③ | |
| GC8 비드 모델 | bead_area · 역산 · w_eff · 정답 높이 정의 | 명령 ② | |
| GC9 정답 지도 | 저장·읽기 같음 | 명령 ① | |
| GC10 해석해 | 다섯 시험 통과 | 명령 ① | |
| GC11 손 G코드 | n개 (_mimic m개), 기대값 행 k | 명령 ② | |
| GC12 고른 후보 | 파일 n개 (public a · _local b) 또는 "대기" | 명령 ③ · ⑤ | |
| GC13 후보 폴더 | 시작·끝 지문 같음 | 명령 ④ | |
| GC14 문서 | 절 0–9, MF-GCD 8개 | 명령 ⑥ | |
| GC15 시험·차단 | n개 통과 t s, import·_truth 0, 소유 위반 0, V2 지문 같음 | 명령 ① · ⑦ · ⑧ | |

검증 명령 실행 결과: (①–⑧ 출력 붙여 넣기)
남은 문제: (없으면 "없음")
```

## 12. 3차 검증과 후속 결과 (2026-10-27)

| 항목 | 결과 | 근거 |
|---|---|---|
| 1차 산출물 | GC1–GC11 · GC13–GC15 ○, GC12 대기였음. 손 G코드 H05 · H10 · H20 손계산 3/3, voron24 층 0 · 7 · 15 줄 범위 원문 3/3, L자 방향 ○, 후보 폴더 쓰기 거부 rc 2 | [팀장검증 3차](팀장검증_3차.md) §3 (98bbcdf) |
| worker가 다르게 정한 것 | ① 순 ΔE (GC7) · ③ 끝 구간 경고만 (GC3) · ④ 산출물 생성 받아들임. ② PRIME은 조건부 → G-3로 문서 반영. 이 문서를 그에 맞춰 고침 (GC3 · GC7 · GC9 · §6.2 · §6.4) | 3차 §3.6 |
| G-1 | 압출 사이 매크로는 위치 다시 정하기 규칙. 손 G코드 H25 · H26 오류, H27 통과 + 경고. xyz_cube 50층 · benchy 240층 통과 (팀장 재실행으로 층 수 · 경고 수 확인) | 94cc48b |
| G-2 (GC16) | voron24 `build_reference` 1.46 s (worker) · **1.52 s (팀장 재측정)**, 기준 15 s. 1차 방식과 `np.array_equal` 시험 (`test_band_equals_window_*`, 무작위 선분 308개 포함). caliper 3.14 s (팀장) · 4.2 s (worker), voron_design_cube 150층 18.35 s (worker) · 22.80 s (팀장, 기기 부하 차) | 94cc48b · 이 개정 |
| G-3 | 문서 §8에 PRIME · 격자 원점 · 격자 간격 두 곳, §9에 층 표시 없는 파일의 퍼지선 | 94cc48b |
| GC12 (D-19) | voron24 · caliper를 `_local/`로 복사 (원본과 sha256 같음, 팀장 확인), `data/gcode_samples/MANIFEST.csv` 2행 (라이선스 [미상], 위치 `_local`). 둘 다 unknown 0 · 체크섬 불량 0, 층 16 = 16 = 16 · 64 = 64 (선언 없음), Z 차 0.0, 필라멘트 +0.0001 % · −0.0001 %. 그림·지도는 `results/gcode_t4a_gc12/` 6개 (Git 밖) | d323dac · 팀장 재실행 |
| 세부청사진과 달랐던 것 | MANIFEST 위치 (`public/` → `data/gcode_samples/`), 그림 위치 (`docs/G코드-해석_자료/` → `results/gcode_t4a_gc12/`). **메인 지시 쪽으로 이 문서를 맞춤** (GC12 · §4 · 명령 ⑤) | 메인 정정 요청 10-27 |
| 팀장 재확인 (결정 반영 때) | 세 시험 폴더 251 passed 0 skipped (gcode 157) | 이 개정 |
| T4b · T5로 넘긴 것 | ① caliper_pyramid는 41개 층 (층 23, Z ≈ 8.25부터)에서 홈 바닥이 심도 8 mm 밖, 마지막 층은 물체 넓이 62 %가 심도 밖 → 판정 영역에서 빼거나 나눠 스캔 ② 스커트 · 브림이 정답 지도에 남아 격자 2790 × 1735 → G4가 판정 영역에서 뺌 ③ caliper는 Prusa MK3S · 노즐 0.6 · Marlin용 → T14 1순위 기종으로 다시 슬라이스할지 T5가 판단 ④ 판정 칸 경계는 격자 원점을 따름 (0.4 mm 배수 맞춤) ⑤ 격자 간격 설정이 `default.yaml` · `gcode.yaml` 두 곳 (T10 통합 때 하나로) | 결과_T4a_대조표 · 3차 §3.5 |
