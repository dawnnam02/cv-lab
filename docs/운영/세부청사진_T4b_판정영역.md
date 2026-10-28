# 세부청사진 T4b · 판정 영역 (G4)

> 상위: [청사진_가상데이터단계](청사진_가상데이터단계.md) §2.1 (1 정답) · §2.3 (D-20 R2 · R6) · §4.1 · §4.3 (T4b) · §5.2 · 작성: 2026-10-27 총괄 팀장 · 상태: **완료 (4e2a369, 5차 조건부 통과) · 후속 R-1–R-3 끝 (116f9cd, 6차 통과)** · **정정 2026-10-28 (팀장검증 6차): 5차 §7에서 미룬 명령 ② 두 줄, 코드 9 → 6, §6.9 키 4개, RG13 · RG15 시간 문구, RG16 (post 영역) 추가. 결과는 §12**
> **일정 앞당김.** 청사진 일정은 11-05 ~ 11-17 (T5 뒤)입니다. 사용자 지시 (10-27) "선행 작업 없이 병렬로 진행할 수 있는 작업 진행해."에 따라 **10-27에 시작해 11-02에 마감**합니다 (9일 앞당김). T5 · T7a와 동시에 돕니다.
> **청사진과 다른 점 (청사진은 고치지 않음, 메인에게 보고).**
> ① 선행 T5를 기다리지 않습니다. D-19 두 파일 (`data/gcode_samples/_local/`)을 그대로 씁니다. T5가 다시 슬라이스를 권하면 새 G코드로 같은 코드를 다시 돌립니다.
> ② 범위에서 뺀 것: 측정 격자 정렬 (T9 실측 지도와 맞추기, T9 · T10), 다시 슬라이스 판단 (T5). 넣은 것: 판정 격자 원점을 0.4 mm 배수로 맞추는 함수 (청사진 §4.3).
> ③ T15 코드표 (`EXCLUSION_CODES` 0 · 1 · 2 · 3 · 4 · 5 · 9)에 "심도 밖"이 없습니다. 이 작업에서는 **9 (기타)로 내보내고 세부 이유는 이유 비트에 남깁니다.** 코드 6 "심도 밖"을 judge에 더하는 일은 T15 후속 J-2로 따로 합니다 (팀장 승인. 이 작업은 `src/cvlab/judge/`를 고치지 않음).
> ④ 청사진 §5.1은 T4b와 T5를 같은 기준모델 담당에게 날짜를 나눠 줍니다. 지금은 동시에 돌아서 **다른 worker 인스턴스**입니다. T4b 담당은 T5의 시나리오 산출물을 읽지 않습니다 (판정 영역을 넣은 오차에 맞춰 고르는 일을 막음, MF-JDG-03).
> **명세가 바뀌는 중.** T1 2차 결과가 884daac (10-27 20:40)로 들어왔지만 상태는 "2차 보완 끝, 팀장 검토 전"입니다. 팀장 검토 뒤 더 바뀔 수 있고, T1 worker가 아직 고칠 수 있습니다. 같은 때 T6 후속 worker가 `src/cvlab/io/`를 새 명세에 맞추는 중입니다 (10-27 20:52 확인). 둘 다 읽기만 합니다. 이 작업이 쓰는 명세 값 (`meta.triang_angle_deg` · `meta.scan_length_mm` · `meta.scan_speed_mm_s` · `meta.scan_pass_idx` (X를 바꾼 줄 번호) · 0.4절 좌표계)이 바뀌면 대조표에 적고 팀장에게 알립니다. 명세 값은 `config/region.yaml` 한 곳에만 두고 코드에 박지 않습니다.
> 함께 도는 작업: [T5 G코드 점검·시나리오](세부청사진_T5_G코드점검·시나리오.md) · [T7a 레이저 선 추출](세부청사진_T7a_레이저선추출.md). **§5 소유 표를 지킵니다.**

| 항목 | 내용 |
|---|---|
| Plane | G4 (D-17 재구성 뒤 목표 2 "정답 만들기"의 단계 줄). 상태 바꾸기는 메인 몫 |
| 담당 | 기준모델 담당 (새 인스턴스), Opus 5.5, effort medium. 독립 검증: 팀장 |
| 기간 | 2026-10-27 ~ 11-02 |
| 선행 | 없음으로 시작. T4a (완료, `src/cvlab/gcode/`) · T15 (완료, `src/cvlab/judge/`)는 읽기·import만 |
| 후행 | T15 · T10 (판정에 영역을 넣음) · T9 (실측 지도를 같은 격자로) · T3 (판정 시험 데이터의 영역) · T5 후속 (기대 판정 재계산) |
| 산출물 | §4 경로 · `docs/판정-영역.md` · `docs/운영/결과_T4b_대조표.md` |

## 1. 목적

정답 높이 지도 (T4a)의 칸을 층마다 **판정에 넣는 칸과 빼는 칸**으로 가르고, 뺀 칸마다 이유를 남깁니다. 결과는 T15 `judge_print_fine`이 그대로 받는 형식입니다.

- 판정 영역은 **G코드와 센서 기하만으로 미리** 정합니다. 측정값을 보고 칸을 빼지 않습니다. 결함이 많은 자리를 골라 빼서 불량이 합격으로 나가는 일 (MF-JDG-03, S5)을 막기 위해서입니다. 측정 결측은 T15가 유효 칸 비율 (D-20 R2, 90 %)로 따로 셉니다.
- 측정이 원래 못 하는 칸 (가림·심도 밖·시야 밖)을 영역에 남기면 유효 칸 비율이 떨어져 "측정 불충분"이 잦아집니다. 그래서 예측할 수 있는 결측은 영역에서 빼고, 뺀 넓이를 이유별로 보고합니다.
- caliper_pyramid의 심도 문제 (T4a GC12: 41개 층, 마지막 층 물체 넓이의 62 %)를 숫자로 처리하고 처리안을 냅니다.

## 2. 목표 (완료 기준)

| 번호 | 완료 기준 | 측정 방법 |
|---|---|---|
| RG1 | **격자 원점 맞춤.** `aligned_grid`가 낸 격자는 x0_mm · y0_mm이 0.4 mm (`cell_mm_alt`, D-20 R1)의 정수배이고 nx · ny가 20 (= 0.4 ÷ 0.02)의 배수. 같은 {G} 점에서 맞춘 격자의 정답 높이 = T4a 기본 격자의 정답 높이 (`value_at`, 차 0). `object_bbox`는 스커트·브림·서포트·PRIME-TOWER를 빼고 정할 수 있음 | 시험 · 명령 ② |
| RG2 | **엣지 띠 (이유 edge, 코드 1).** 층 n 정답 높이 (출력물 없음 = 베드 0)에서 3 × 3 이웃의 높이 차가 `step_mm`을 넘는 칸이 경계, 경계에서 거리 ≤ `edge_band_mm`인 칸이 띠 (G4 거리 변환 방식). 기본 `step_mm` = 최소 층 높이 ÷ 2, `edge_band_mm` = 외벽 선폭 ÷ 2 + 2 × res (E2 · G4). H20 가운데 줄에서 한쪽 띠 칸 수 = (띠 ÷ res) + 1 ± 1 | 시험 · 명령 ② |
| RG3 | **가림 예측 (이유 occlusion, 코드 2).** 레이저 수직, 카메라는 수직에서 θ (`meta.triang_angle_deg`, 30°) 기울어 **±Y 쪽** (명세 0.4: 레이저 선 = {S} x = 프린터 X, 스캔 = 프린터 Y). 칸 p에서 카메라 쪽으로 s 간 곳의 높이 > z_p + s ÷ tanθ면 가림. 높이 h 단차 뒤 그림자 길이 h·tanθ ± 1칸. 예측 그림자를 2칸 넓힘 (E2). `camera_side` ∈ {+y, −y, both}, 기본 both | 시험 · 명령 ② |
| RG4 | **심도 밖 (이유 depth, 코드 6 — J-2 · R-3 뒤. 처음 지시는 9).** 층 n에서 Z_ref(x, y, n) < z_n + `dof_top_mm` − `dof_mm`이면 심도 밖. 기본 `dof_mm` 8.0 (청사진 §1), `dof_top_mm` 0.0 [추정]. 비교는 nm 정수. caliper_pyramid: 심도 밖 칸이 있는 층 수 = 41, 마지막 층 심도 밖 넓이 ÷ 물체 넓이 (스커트 뺌) = 62 % ± 1 %p (T4a GC12 값). 다르면 이유를 문서에. `dof_top_mm` ± 1 mm 민감도 | 시험 · 명령 ② · ③ |
| RG5 | **경로 종류·PRIME (이유 type · prime, 코드 4).** 꼭대기 층 종류 (`type_at(n)`)가 `exclude_types` (기본 SKIRT · BRIM · SUPPORT · PRIME-TOWER, G4)면 뺌. PRIME 선분 (`segments` 종류 PRIME, 층 −1)은 격자 안이면 캡슐로 칸을 칠해 이유 prime. IRONING은 넣음 (근거를 문서 §6에). 출력물 없는 칸은 이유 no_material (코드 5) | 시험 |
| RG6 | **시야 밖 (이유 fov, 코드 3).** §6.5 스캔 패스 약속 (T5와 같은 규칙)으로 패스 사각형을 만들고, 어느 패스에도 칸 중심이 들지 않으면 시야 밖. 패스를 인자로 직접 줄 수도 있음. voron24 · caliper 기본 패스 수를 문서에 적음 (팀장이 T5 값과 대조). 패스 하나를 강제하면 \|x − x_c\| > 10 mm 칸이 모두 시야 밖 | 시험 · 명령 ③ |
| RG7 | **이유 비트와 코드.** 칸마다 이유 비트 (uint8, §6.2, 겹침 허용)와 주 코드 (int8, T15 코드표) 둘 다. 주 코드는 §6.2 우선순위. 영역 칸 ⇔ 비트 0 ⇔ 코드 0. 코드 값 ⊂ `cvlab.judge.aggregate.EXCLUSION_CODES` | 시험 |
| RG8 | **판정 영역 비율.** 층마다 · 전체 층 합산 (D-08과 같은 가중): 출력물 칸, 영역 칸, 영역 비율 = 영역 ÷ 출력물, 이유별 칸 수 (비트 기준, 겹침 허용)와 주 코드별 칸 수 (겹침 없음). 판정 칸 0.2 · 0.4 mm로 묶은 영역 칸 수 (`region_fill_min` 1.0, D-20 R6). `summary()` 열 고정 (§6.8) | 시험 · 명령 ③ |
| RG9 | **T15 연결.** `layer_input(n, delta_mm)`이 `cvlab.judge.LayerInput`을 만듦 (오류 없이). 영역 안 Δ = 0, 밖 NaN으로 모든 층을 `judge_print_fine` (U 0.0209 mm)에 넣으면 주 판정 pass. 결과의 뺀 이유별 칸 수가 `summary()`를 판정 칸으로 묶은 값과 같음. 식힌 재측정 (post)은 **RG16 post 영역**을 씀 (5차 R-2 · J-3. 처음 지시는 마지막 층 판정 영역) | 시험 · 명령 ② |
| RG10 | **caliper 심도 처리안.** A안 (심도 밖은 영역에서 뺌)과 B안 (높이를 나눠 스캔) 비교표: 층마다 심도 밖 비율, 필요한 스캔 높이 수 (⌈윗면 높이 폭 ÷ 심도⌉), B안 추가 시간, B안으로 되찾는 칸 (심도 이유만 있는 칸. 가림 등 다른 이유가 같이 있으면 못 되찾음). A안의 **최종 윗면 덮임률** (§6.7, 기대 100 %). 권장안과 근거 | 명령 ③ · 문서 §9 |
| RG11 | **결정 기록.** MF-GCD-02 (결: 정답 지도에 안 넣음, 판정 칸 평균이 맡음), MF-GCD-03 (첫 층 눌림: 안 넣음, 보고서 주의), MF-GCD-07 (아이롱: 넣음), MF-JDG-03 (영역은 기하만으로, 측정값을 안 봄) 처리와 근거. 바꾸면 팀장에게 먼저 | 문서 §11 |
| RG12 | **저장·재현.** `RegionStack.save` → `load` 뒤 영역 · 코드 · 비트 배열이 모두 같음 (`np.packbits`). 같은 입력 두 번 → `np.array_equal`. 스크립트 요약 줄 `REGION {json}` (§4) | 시험 · 명령 ③ |
| RG13 | **속도.** voron24 모든 층 `build_region` ≤ 30 s, caliper (물체 격자) ≤ 120 s [추정 목표]. 넘으면 시간과 원인을 적음. **판정은 명령 ③ REGION 줄 `build_s`로만, 잴 때 CPU 부하를 함께 적음** (5차 R-1) | 명령 ③ |
| RG14 | **문서.** `docs/판정-영역.md` 절 0–13 (§4 목차). 두 파일 결과 수치, 코드표, 우선순위, 처리안 | 명령 ④ |
| RG16 | **식힌 재측정 비교 영역 (5차 R-2, 116f9cd).** `RegionStack.post_region()`: 마지막 층 출력물 칸에서 type · fov · depth · occlusion · 출력물 없음은 빼고, 엣지는 좁은 띠 max(2 × res, α × 반폭 × ΔT) [추정]만 뺌. 0칸이면 엣지 포함 (P-A)으로 넘어가고 규칙 이름 (`info["post_rule"]`)을 남김. `post_input`이 이 영역 · 코드를 넘김. caliper 띠 0.0433 mm · 고운 288 360 · 0.2 mm 940 · 0.4 mm 72칸, voron24 판정 칸 141 760 그대로. 스크립트 `POST {json}` 줄 | 시험 · 명령 ③ |
| RG15 | **시험·차단.** `tests/region/` 시험 함수 ≥ 30개 모두 통과 (`_local/`이 없으면 해당 시험만 skip). **시험 안에 시간 단정문을 두지 않음** (시간은 RG13대로 부하와 함께 기록, 5차 R-1). import는 `cvlab.gcode` · `cvlab.judge`만. `cvlab.io` · `cvlab.sim` import 0, `_truth` · T5 시나리오 경로 언급 0. 소유 위반 0, V2 지문 같음, `src/cvlab/gcode` · `src/cvlab/judge` 변경 0 | 명령 ① · ⑤ · ⑥ |

## 3. 입력

| 입력 | 경로 | 쓰는 곳 |
|---|---|---|
| 요소 청사진 | `docs/blueprints/G-reference/G4-evaluation-masks.md` (§2 마스크 정의, §4 결정, §6.1 코드 예, §8 흔한 실수) · `docs/blueprints/E-specimen/E2-occlusion-edges.md` (§4 결정: 띠 폭 규칙, 그림자 2칸 넓힘, 형상 방향) | RG2 · RG3 · RG5 |
| T4a 문서 | `docs/G코드-해석.md` §5 (격자 약속) · §6 (caliper 심도 41층 · 62 %) · §8 (T4b에 넘길 것) · §9 | RG1 · RG4 · RG10 |
| T4a 코드 | `src/cvlab/gcode/` (`parse_file` · `build_reference` · `RefStack` · `make_grid` · `grid.value_at` · `reference.capsule_cells`) | 전부 |
| T15 | `docs/판정-규칙.md` §3 · §4 (판정 영역 인터페이스, 코드표) · `src/cvlab/judge/` (`LayerInput` · `judge_print_fine` · `fine_to_cell_layer` · `aggregate.EXCLUSION_CODES`) | RG7 – RG9 |
| 명세 (읽기만, 바뀌는 중, 884daac 기준) | `docs/하드웨어-데이터-명세.md` 0.4절 (좌표계, 스캔 = Y) · 2절 "스캔 줄과 반복" (한 스캔 = X를 고정한 한 줄, 여러 줄은 `meta.scan_pass_idx`, 같은 줄 반복은 `pos.pass_idx`) · 5절 `meta.triang_angle_deg` · `meta.scan_length_mm` · `meta.scan_speed_mm_s` · `meta.scan_axis` | RG3 · RG6 |
| 펌웨어 | `docs/프린터-펌웨어-선정.md` §9 (LM-T14-2: `scan_x` 한 줄 스캔, `scan_len` 40, `lead_in` 5, 시야 20 mm) | RG6 · RG10 |
| 실패사례 | `docs/측정-실패사례.md` MF-JDG-03 · MF-GCD-02 · 03 · 07 · 08 · MF-OPT-01 · 02 · 04 · 05 · 06 | RG10 · RG11 |
| G코드 | `data/gcode_samples/hand/*.gcode` (읽기만) · `data/gcode_samples/_local/` (D-19 두 파일, 읽기만, 없으면 skip) | 시험 |

- 손 시험용 G코드는 `data/gcode_samples/`에 새로 만들지 않습니다. 시험 도우미 (`tests/region/region_*.py`)가 G코드 글을 만들어 `parse_text`에 넣습니다.

## 4. 산출물

| 경로 | 내용 |
|---|---|
| `src/cvlab/region/__init__.py` | 아래 공개 이름을 내보냄 |
| `src/cvlab/region/params.py` | `RegionParams` (기본값 = `config/region.yaml`, 모르는 키 오류, `from_dict` · `from_yaml`) |
| `src/cvlab/region/grid.py` | `object_bbox` · `aligned_grid` |
| `src/cvlab/region/masks.py` | `edge_band` · `predict_occlusion` · `depth_out` · 종류·PRIME 칠하기 |
| `src/cvlab/region/coverage.py` | `plan_passes` · `coverage_mask` |
| `src/cvlab/region/stack.py` | `build_region` · `RegionStack` |
| `config/region.yaml` | 최상위 키 `region` 하나 (§6.9) |
| `scripts/region_mask.py` | G코드 하나 → 요약 줄 `REGION {json}` + (선택) 층별 표 CSV · 영역 npz · 그림. 출력 폴더 기본 `results/region_t4b/` (Git 밖). `data/` 아래 쓰기 거부 |
| `tests/region/test_region_*.py` (+ 도우미 `tests/region/region_*.py`) | 시험 |
| `docs/판정-영역.md` · `docs/판정-영역_자료/` | 문서. 자료 폴더는 손 G코드·합성 G코드에서 나온 것만. D-19 파일 (라이선스 [미상])에서 나온 그림·지도는 `results/region_t4b/`에, 수치만 문서에 |
| `docs/운영/결과_T4b_대조표.md` | 시작 확인 · 종료 대조 |

**공개 이름 (바꾸지 않음, 검증 명령이 씀).**

```python
RegionParams.from_dict(d) ; RegionParams.from_yaml(path)          # path의 최상위 키 region
object_bbox(result, exclude_types=("SKIRT","BRIM","SUPPORT","PRIME-TOWER")) -> (xmin, xmax, ymin, ymax)  # 선폭 반 포함 (§6.5)
aligned_grid(xmin, xmax, ymin, ymax, res_mm=0.02, cell_mm=0.4, margin_mm=1.0) -> dict   # 격자 JSON (T4a 약속)
plan_passes(bbox, fov_mm=20.0, scan_len_mm=40.0, overlap_mm=2.0, extend_scan_len=False) -> list[dict]
    # 패스마다 {"x0_mm","x1_mm","y0_mm","y1_mm"} ({G})
coverage_mask(grid, passes) -> bool[ny, nx]
edge_band(height_mm, res_mm, band_mm, step_mm) -> bool[ny, nx]         # height: NaN = 베드 0으로 봄
predict_occlusion(height_mm, res_mm, theta_deg, camera_side) -> bool    # 넓히기 전
depth_out(height_mm, z_layer_mm, dof_mm, top_mm) -> bool
build_region(result, ref, params=None, passes=None) -> RegionStack       # 측정값을 받지 않음
# RegionStack: .grid  .n_layers  .z_layers  .passes  .params
#   .region(n) -> bool  .exclusion_code(n) -> int8  .reasons(n) -> uint8
#   .summary() -> DataFrame (§6.8)  .save(path)  RegionStack.load(path)
#   .layer_input(n, delta_mm, thermal_state="in_process") -> cvlab.judge.LayerInput
REASON_BITS = {"edge": 1, "occlusion": 2, "fov": 4, "type": 8, "no_material": 16, "depth": 32, "prime": 64}
```

요약 줄 키 (고정): `file, gcode_sha256, layers, grid_ny_nx, passes, band_mm, step_mm, camera_side, dof_mm, dof_top_mm, region_pct_total, region_cells_cell02_total, depth_layers, last_layer_depth_pct_object, coverage_final_top_pct, build_s`.

`docs/판정-영역.md` 목차 (절 번호 고정):

```
# 판정 영역 (G4)
## 0. 요약
## 1. 입력과 격자 (원점 맞춤)
## 2. 제외 이유와 코드표 (비트, T15 코드, 우선순위)
## 3. 엣지 띠
## 4. 가림 예측
## 5. 심도 밖
## 6. 경로 종류 · PRIME · 출력물 없음
## 7. 시야 밖과 스캔 패스
## 8. 판정 영역 비율 (두 테스트 G코드)
## 9. caliper_pyramid 심도 처리안 (A · B 비교, 권장)
## 10. T15 연결
## 11. MF 대응과 결정 기록
## 12. 넘길 것 (T5 · T9 · T10 · T15 · T3)
## 13. 한계
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

**모두 금지:** `scripts/method_screening/**` · `tests/test_method_screening.py` · `docs/0_방법탐색/**` (V2 미커밋, 읽기만) · 청사진 · 다른 세부청사진 · 점검일지 · `docs/운영/plane/**` · 요소 청사진 (`docs/blueprints/**`, 읽기만) · `pyproject.toml` · `requirements.txt` · `src/cvlab/__init__.py` · `data/gcode_candidates/**` · **`data/_truth/**`와 `src/cvlab/sim/**` (읽기도 금지)** · `tests/**/__init__.py` · `conftest.py` (만들지 않음).

- 시험 파일·도우미 이름은 `test_region_*.py` · `region_*.py`로 시작합니다 (pytest 기본 import 방식에서 이름 겹침을 피함). 자기 폴더만 돌립니다.
- `cvlab.gcode`에 꼭 더해야 할 함수가 보이면 **고치지 말고 멈춰서 팀장에게** 알립니다. 지금 필요한 것은 모두 공개 함수로 됩니다: 층마다 꼭대기 층은 `footprint(k)`를 차례로 덮어 한 번에 구하고 (`height_at_layer(n)`을 층마다 부르면 층 수의 제곱만큼 느림), PRIME 칠하기는 `reference.capsule_cells`를 씁니다.
- 설정은 `config/region.yaml`을 `yaml.safe_load`로 직접 읽습니다. `cvlab.config`는 import하지 않습니다.

## 6. 설계 규칙

### 6.1 격자

| 항목 | 규칙 |
|---|---|
| 약속 | T4a와 같음: {G} mm, `A[iy, ix]`, 칸 중심 x = x0_mm + ix·res_mm, 격자 JSON `{"frame": "G", "x0_mm", "y0_mm", "res_mm", "nx", "ny"}`, res 0.02 mm |
| 원점 맞춤 | x0_mm · y0_mm = 0.4 mm 정수배 (내림), nx · ny = 20의 배수 (올림). 그러면 0.2 · 0.4 mm 판정 칸 경계가 출력마다 같은 {G} 자리에 오고, 가장자리 묶음이 잘려 버려지는 칸이 없음 (`aggregate_to_cells`는 f칸이 안 차는 묶음을 버림) |
| 비교 | 정수배 판정은 `Fraction(str(x))`로. 실수 나머지로 하지 않음 |
| 범위 | 기본 = `object_bbox` (판정 대상 종류의 압출 경계, §6.5) + `margin_mm`. caliper는 스커트를 빼서 격자가 2790 × 1735보다 작아짐. 스커트가 격자 밖이면 지도에 안 들어감 (`capsule_cells`가 자름) |
| 정답 지도 | `build_reference(result, grid=aligned)`로 다시 만듦. T4a 코드는 그대로 |

### 6.2 이유 비트 · T15 코드 · 우선순위

| 이유 | 비트 | T15 코드 | 뜻 |
|---|---|---|---|
| edge | 1 | 1 엣지 띠 | 높이 경계에서 띠 폭 안 |
| occlusion | 2 | 2 가림 예측 | 카메라 시선이 더 높은 곳에 막힘 (2칸 넓힘 뒤) |
| fov | 4 | 3 시야 밖 | 어느 스캔 패스에도 안 듦 |
| type | 8 | 4 제외 경로 종류 | 꼭대기 종류가 `exclude_types` |
| no_material | 16 | 5 출력물 없음 | 그 층까지 출력물 없음 (Z_ref NaN) |
| depth | 32 | **9 기타 (J-2 뒤 6)** | 심도 밖 |
| prime | 64 | 4 제외 경로 종류 | 시작 퍼지선이 덮은 칸 |

- **주 코드 우선순위.** 출력물 없는 칸: PRIME이 덮으면 4, 아니면 5. 출력물 있는 칸: type (4) > fov (3) > depth (9) > occlusion (2) > edge (1). 구조로 빠지는 이유를 측정 때문에 빠지는 이유보다 앞에 둡니다. 이유가 없으면 영역 칸, 코드 0.
- 비트는 모든 이유를 남깁니다 (보고서 "뺀 자리 지도", MF-JDG-03). 코드는 T15가 칸마다 하나만 받기 때문에 우선순위로 고릅니다.
- 판정 칸으로 묶을 때 코드는 T15 `aggregate_exclusion_code`가 정합니다 (묶음 안 가장 많은 코드). T4b는 고운 격자 코드만 냅니다.

### 6.3 엣지 띠 · 가림

| 항목 | 규칙 | 근거 |
|---|---|---|
| 높이 | 층 n의 Z_ref, NaN은 0 (베드) | G4 §6.1 |
| 경계 | 3 × 3 이웃 (최대 − 최소) > `step_mm` | G4 · E2 (단차 기준 h/2) |
| 띠 | `scipy.ndimage.distance_transform_edt(~경계) × res ≤ band_mm` | G4 |
| 기본값 | `step_mm` = 최소 층 높이 ÷ 2 (voron24 0.1, caliper 0.1 [계산: 첫 층 0.2 ÷ 2]). `edge_band_mm` = 외벽 선폭 ÷ 2 + 2 × res. 선폭은 머리말 WALL-OUTER → DEFAULT → `result.params.line_width_mm` 순, 모두 없으면 오류 | E2 §4 |
| 띠 민감도 | 0.15 · 0.25 · 0.35 mm와 자동값의 영역 비율을 문서 §3 표로 (확정은 실측 지도가 생긴 뒤 E2 안정 구간 규칙으로, T9 · T10) | E2 §4 |
| 가림 방향 | 카메라는 ±Y. G4 §6.1 예시의 `camera_side: "-x"`는 명세 0.4 (스캔 = Y)와 맞지 않아 쓰지 않음. 문서 §13에 G4 바꿀 점으로 적음 (G4는 고치지 않음) | 명세 0.4 · E2 §4 "그림자는 Y 방향" |
| 가림 쪽 | 장착 방향 [미상] (T14 §13 9단계 뒤 정함) → 기본 both (두 쪽 그림자의 합). +y · −y · both 영역 비율을 문서 §4에 | [추정] 보수적으로 |
| 넓힘 | 예측 그림자를 2칸 넓힌 뒤 이유 occlusion | E2 §4 (θ 오차로 1–2칸 어긋남) |
| 레이저 그림자 | 레이저가 수직이라 수평 윗면에는 없음. 문서에 한 줄 | 청사진 §1 |

### 6.4 심도 밖

| 항목 | 규칙 |
|---|---|
| 창 | 층 n 스캔에서 잴 수 있는 높이 = [z_n + `dof_top_mm` − `dof_mm`, z_n + `dof_top_mm`]. 기본 [z_n − 8, z_n] (T4a GC12와 같은 정의라 41층 · 62 %와 바로 대조) |
| 비교 | rint(높이 × 10⁶) 정수로. 창 아래 끝과 같으면 창 안 (≤) |
| 가정 | `dof_top_mm` 0 = 센서가 지금 윗면을 심도 위 끝에 두도록 장착 [추정]. 실제 값은 장착 뒤 D4 교정 (T8)과 `meta.scan_z_hop_mm`에 달림 → ± 1 mm 민감도 (심도 밖 층 수 · 마지막 층 비율)를 문서 §5에 |
| 식힌 재측정 | 같은 센서 거리로 재므로 (LM-T14-2 `COOL_RESCAN`) 마지막 층 영역을 그대로 씀 |

### 6.5 스캔 패스 약속 (T5와 같은 글, 서로 독립 구현 → 팀장이 대조)

| 항목 | 규칙 |
|---|---|
| 경계 상자 B | 판정 대상 종류 (exclude_types 밖) 압출 선분 끝점의 경계 상자를, 그 선분들 선폭 최댓값의 반만큼 넓힌 것. 폭 W (X), 높이 H (Y) |
| X 패스 수 | n_x = max(1, ⌈(W − o) ÷ (F − o)⌉). F = `fov_mm` 20 (청사진 §1), o = `pass_overlap_mm` 2 (MF-GCD-08 "2 mm 겹치게") |
| Y 패스 수 | n_y = max(1, ⌈(H − o) ÷ (L − o)⌉), L = `scan_len_mm` 40 (M54 · LM-T14-2). `extend_scan_len: true`면 n_y = 1, L = H |
| 배치 | 덮는 폭 S_x = n_x·F − (n_x − 1)·o를 B 가운데에 맞춤. 패스 i는 [c_x − S_x/2 + i(F − o), 그 + F]. Y도 같음 |
| 시야 안 | 칸 중심이 어느 패스 사각형 안 (경계 포함) |

- X 패스 i는 명세의 스캔 줄 번호 `meta.scan_pass_idx` = i (0부터)에 대응합니다. Y를 나눈 패스는 명세에 따로 번호가 없으므로 문서 §12에서 T1에 넘깁니다.
- 지금 매크로 (LM-T14-2)는 층마다 한 줄 (`scan_x` 고정)만 훑습니다. 패스가 여럿 필요하면 T14 매크로가 바뀌어야 한다는 점을 문서 §12에 넘깁니다.

### 6.6 경로 종류 · PRIME · 출력물 없음

- 종류는 꼭대기 층 종류 (`type_at(n)`, 이름은 `ref.type_names`)로 정합니다. 아래층 브림 위에 물체가 올라오면 물체 칸입니다.
- PRIME은 정답 지도에 없습니다 (T4a G-3). 퍼지선 칸이 격자 안이면 그 선분의 캡슐을 칠해 이유 prime으로 둡니다. 격자 밖이면 개수만 문서에 적습니다.
- IRONING은 판정에 넣습니다. 아이롱은 그 층 윗면을 다시 펴는 경로라 높이 정의 (층 Z, flat)가 그대로입니다. 바꾸려면 팀장에게.

### 6.7 판정 영역 비율 · 최종 윗면 덮임률

- 영역 비율 = 영역 칸 ÷ 출력물 칸 (그 층 Z_ref가 NaN이 아닌 칸). 분모에 베드 칸을 넣지 않습니다.
- 전체 합산은 층마다 칸 수를 더한 비율입니다 (D-08 판정과 같은 가중).
- **최종 윗면 덮임률.** 분모: 마지막 층 지도의 출력물 칸 중, 그 칸의 마지막 윗면이 생긴 층 k에서 type · fov · edge 이유가 없는 칸. 분자: 그중 그 윗면이 드러난 층 (k ≤ n, 꼭대기 층 = k) 가운데 한 층 이상에서 영역 칸인 칸.
  - 층마다 재면 (D-18) 윗면은 생긴 층에서 가장 높은 면이라 심도 밖도, 가림도 될 수 없습니다. 그래서 A안 덮임률은 100 %가 나와야 합니다. 100 %가 아니면 원인을 적습니다 (`dof_top_mm` < 0 같은 설정).
  - 이 값이 100 %면 A안은 판정 못 하는 윗면을 만들지 않고, 같은 면을 다시 보는 횟수만 줄입니다.

### 6.8 `summary()` 열 (고정)

`layer_idx, layer_z_mm, n_material, n_region, region_pct, bit_edge, bit_occlusion, bit_fov, bit_type, bit_depth, bit_prime, code_1, code_2, code_3, code_4, code_5, code_6, n_region_cell02, n_region_cell04` + 마지막에 `layer_idx = -1` 전체 합산 행. (6차 정정: `code_9` → `code_6`, 5차 R-3)

- `bit_*`는 출력물 칸 중 그 비트가 켜진 칸 수 (겹침 허용). `code_*`는 주 코드별 칸 수 (출력물 없는 칸의 코드 4 · 5 포함). `n_region_cell0x`는 T15 `aggregate_to_cells`와 같은 규칙 (`region_fill_min` 1.0)으로 묶은 영역 칸 수.

### 6.9 `config/region.yaml`

```yaml
region:
  res_mm: 0.02             # G3 결정. config/gcode.yaml grid_res_mm과 같아야 함 (다르면 오류)
  cell_mm: 0.4             # 원점 맞춤 단위 = judge cell_mm_alt (D-20 R1)
  margin_mm: 1.0           # T4a grid_margin_mm
  exclude_types: [SKIRT, BRIM, SUPPORT, PRIME-TOWER]   # G4 §4 결정
  edge_band_mm: null       # null = 외벽 선폭/2 + 2·res (E2 · G4)
  step_mm: null            # null = 최소 층 높이/2 (E2)
  theta_deg: 30.0          # meta.triang_angle_deg (청사진 §1, M54)
  camera_side: both        # +y | -y | both. 명세 0.4 스캔 = Y. 장착 방향 [미상]
  occlusion_grow_cells: 2  # E2 §4
  dof_mm: 8.0              # 청사진 §1 (M54 8.4 [계산])
  dof_top_mm: 0.0          # [추정] 지금 층 윗면 = 심도 위 끝. D4 교정 뒤 확정
  fov_mm: 20.0             # 청사진 §1 (M54 20.2 [계산])
  scan_len_mm: 40.0        # M54 · LM-T14-2 scan_len
  pass_overlap_mm: 2.0     # MF-GCD-08
  extend_scan_len: false   # true면 Y는 스캔 길이를 늘려 패스 1개
  lead_in_mm: 5.0          # (worker 추가, 5차 받아들임) LM-T14-2 lead_in. B안 추가 시간 계산에만
  scan_speed_mm_s: 2.4     # (worker 추가, 5차 받아들임) meta.scan_speed_mm_s. B안 추가 시간 계산에만
  post_edge_band_mm: null  # (R-2) post 영역 엣지 띠. null = max(2·res, α·반폭·ΔT) [추정]
  post_delta_t_c: 30.0     # (R-2) 식힘 온도차 ΔT [추정]. post 띠 자동값에만
```

- 모르는 키는 오류입니다. 값마다 주석 근거를 유지합니다.

### 6.10 caliper 처리안 비교 (문서 §9 표 열)

`layer_idx, layer_z_mm, spread_mm (z_n − 물체 최저 윗면), n_heights (⌈spread ÷ dof⌉, 최소 1), depth_pct (물체 넓이 기준), recover_cells_B (심도 이유만 있는 칸), extra_scan_s_B ((n_heights − 1) × 패스 수 × (lead_in 5 + scan_len) ÷ 2.4)`. 합계 행. 시간 상수는 LM-T14-2 (`lead_in` 5 mm, 2.4 mm/s) [출처: docs/프린터-펌웨어-선정.md §9].

- 권장안은 숫자로 고릅니다: A안 덮임률, B안이 되찾는 칸 비율, B안 추가 시간. 가림 그림자 (15 mm 단차면 15 × tan 30° ≈ 8.7 mm [계산])가 깊은 홈 바닥을 덮으면 B안으로도 못 되찾습니다.

## 7. 단계

| 단계 | 날짜 | 할 일 | 끝난 표시 |
|---|---|---|---|
| S1 | 10-27 | 시작 확인 (§10). `params` · `grid` (RG1) · 종류·PRIME·출력물 없음 (RG5) · 패스 (RG6) | 대조표 · 시험 |
| S2 | 10-28 | 엣지 띠 (RG2) · 가림 (RG3), 합성 단차 시험 | 명령 ② 일부 |
| S3 | 10-29 | 심도 (RG4) · `build_region` · 코드·비트 (RG7) · 비율 (RG8) | 명령 ① |
| S4 | 10-30 | T15 연결 (RG9) · 저장 (RG12) · 스크립트, 두 테스트 G코드 실행, caliper 처리안 (RG10) | 명령 ③ |
| S5 | 10-31 | 문서 (RG11 · RG14), 속도 (RG13) | 명령 ④ |
| S6 | 11-01 ~ 11-02 | 검증 명령 전부, "종료 대조" → 팀장 검증 | 대조표 |

## 8. 검증

### 8.1 검증 명령 (Git Bash에 그대로 붙여 넣기)

① 시험

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m pytest tests/region -q -p no:cacheprovider -rs --durations=5 2>&1 | tail -15 && echo '--- 시험 함수 수' && cat tests/region/test_region_*.py | grep -c -E "^def test_"
```

② 손 시험 (H20 엣지 띠 · 합성 단차 가림 · 합성 탑 심도 · 원점 · T15 연결)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python - <<'EOF'
import math, yaml, numpy as np
from fractions import Fraction
from cvlab.gcode import parse_file, parse_text, build_reference, GCodeParams
from cvlab.region import RegionParams, build_region, aligned_grid, object_bbox, predict_occlusion, REASON_BITS
from cvlab.judge import JudgeParams, judge_print_fine
from cvlab.judge.aggregate import EXCLUSION_CODES
base = yaml.safe_load(open('config/region.yaml', encoding='utf-8'))['region']
def P(**kw): return RegionParams.from_dict({**base, **kw})
def block(x0, x1, y0, y1, z, w=0.4):
    out, y, d = [], y0 + w/2, 1
    while y <= y1 - w/2 + 1e-9:
        a, b = (x0 + w/2, x1 - w/2) if d > 0 else (x1 - w/2, x0 + w/2)
        out += [f'G0 X{a:.3f} Y{y:.3f} Z{z:.3f}', f'G1 X{b:.3f} Y{y:.3f} E0.5']; y += w; d = -d
    return out
def tower(top_k):
    L = ['G21', 'G90', 'M83'] + block(0, 10, 0, 10, 0.2)
    for k in range(2, top_k + 1): L += block(0, 10, 0, 5, round(0.2 * k, 4))
    return parse_text('\n'.join(L), GCodeParams(line_width_mm=0.4))
# 1) 원점 · H20 엣지 띠
r = parse_file('data/gcode_samples/hand/H20_block.gcode'); g = aligned_grid(*object_bbox(r))
print('원점 ÷ 0.4', [Fraction(str(g[k])) / Fraction('0.4') for k in ('x0_mm', 'y0_mm')], '/ nx·ny 20 배수', g['nx'] % 20 == 0 and g['ny'] % 20 == 0)
ref = build_reference(r, grid=g); rs = build_region(r, ref, P()); n = rs.n_layers - 1
fp = ~np.isnan(ref.height_at_layer(n)); reg = rs.region(n)
rows = fp.sum(1); top = np.flatnonzero(rows == rows.max()); iy = int(top[len(top) // 2])  # 6차 정정: argmax는 가장자리 줄을 고를 수 있어 최댓값 줄들의 가운데
print('H20 가운데 줄 발자국', int(fp[iy].sum()), '영역', int(reg[iy].sum()), '한쪽 띠 칸', (fp[iy].sum() - reg[iy].sum()) / 2, '(기대 0.25/0.02 + 1 = 13.5 ± 1, 6차 실행 13.0)')
print('코드 ⊂ T15 코드표', set(np.unique(rs.exclusion_code(n)).tolist()) <= set(EXCLUSION_CODES), '/ 영역 ⇔ 코드 0', bool(((rs.exclusion_code(n) == 0) == reg).all()))
Ls = [rs.layer_input(k, np.where(rs.region(k), 0.0, np.nan)) for k in range(rs.n_layers)]
out = judge_print_fine(Ls, JudgeParams(T_mm=0.2, U_mm=0.0209, U_source='T4b 검증'), res_mm=g['res_mm'])
print('T15 연결 판정', out['primary'].verdict, '(기대 pass)', out['primary'].counts)
# 2) 가림: 탑 y 0–5 (Z 2.0), 바닥 y 0–10 (Z 0.2), 카메라 -y
t = tower(10); gt = aligned_grid(*object_bbox(t)); rt = build_reference(t, grid=gt); h = rt.height_at_layer(9)
occ = predict_occlusion(h, gt['res_mm'], 30.0, '-y'); ix = int(round((5.0 - gt['x0_mm']) / gt['res_mm']))
ys = gt['y0_mm'] + np.arange(gt['ny']) * gt['res_mm']
behind = (ys > 4.8 + 1e-9) & (ys < 9.0)  # 6차 정정: block(0,10,0,5)는 y ≤ 4.8까지 깔아 탑 끝 = 4.8. 탑 뒤 출력물 칸만 셈
col = occ[:, ix] & behind & ~np.isnan(h[:, ix])
print('그림자 길이', round(col.sum() * gt['res_mm'], 3), 'mm (기대 51칸 = 1.02 mm, 연속식', round(1.8 * math.tan(math.radians(30)), 3), '의 이산값)')
rst = build_region(t, rt, P(camera_side='-y')); bits = rst.reasons(9)
print('넓힌 뒤 칸 수', int(((bits & REASON_BITS['occlusion']) > 0)[:, ix][behind].sum()), '(기대 51 +', base['occlusion_grow_cells'], '= 53)')
# 3) 심도: 탑을 Z 10.0까지 (50층)
d = tower(50); gd = aligned_grid(*object_bbox(d)); rd = build_reference(d, grid=gd); rsd = build_region(d, rd, P())
nd = sum(int(((rsd.reasons(k) & REASON_BITS['depth']) > 0).any()) for k in range(rsd.n_layers))
print('심도 밖 층 수', nd, '(기대 9: Z 8.4–10.0)')
s = rsd.summary(); last = s[s.layer_idx == rsd.n_layers - 1].iloc[0]
print('마지막 층 심도 밖 ÷ 출력물', round(last.bit_depth / last.n_material * 100, 1), '% (기대 약 50, 바닥 노출 y 5–10)')
EOF
```

③ 테스트 G코드 실행 (`_local/`이 있을 때. 요약 줄 형식 `REGION {json}` 고정)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && for f in data/gcode_samples/_local/*.gcode; do [ -f "$f" ] || continue; echo "=== $f"; PYTHONIOENCODING=utf-8 PYTHONPATH=src python scripts/region_mask.py "$f" --summary --out "$TEMP/t4b_out" 2>&1 | grep -E "^REGION|^POST|Error|오류"; done; echo '--- data/ 아래 쓰기 거부 확인 (오류가 나야 정상)'; PYTHONIOENCODING=utf-8 PYTHONPATH=src python scripts/region_mask.py data/gcode_samples/hand/H20_block.gcode --summary --out data/x 2>&1 | tail -1; ls data/x 2>/dev/null && echo '거부 안 됨 (✗)' || echo '거부됨 (○)'
```

판정용: caliper `depth_layers` 41, `last_layer_depth_pct_object` 62 ± 1, `coverage_final_top_pct` 100 (아니면 문서에 원인), voron24 `depth_layers` 0, 두 파일 `build_s` ≤ 120 (voron24 ≤ 30), `passes`는 팀장이 T5 값과 대조.

④ 문서 구조

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import re
t = open('docs/판정-영역.md', encoding='utf-8').read()
print('절 누락', [h for h in map(str, range(14)) if not re.search(r'^## %s\. ' % h, t, re.M)])
for k in ['MF-JDG-03', 'MF-GCD-02', 'MF-GCD-03', 'MF-GCD-07', 'MF-GCD-08', 'MF-OPT-01', 'MF-OPT-04', 'J-2', '41', '덮임률', 'camera_side', '우선순위', '하드웨어 성능의 증거가 아닙니다']:
    print(k, k in t)
print('근거 태그 수', len(re.findall(r'\[(계산|추정|미상|출처|확인 필요)', t)))
EOF
```

⑤ 정보 차단·독립

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && grep -rn -E "cvlab\.(io|sim|triangulation|config|repro)|_truth|scenarios|판정-시나리오|scenario_expected|gcode_candidates" src/cvlab/region tests/region scripts/region_mask.py config/region.yaml; echo "grep exit=$? (1이면 0건)"; git status --porcelain src/cvlab/gcode src/cvlab/judge config/gcode.yaml config/judge.yaml data/gcode_samples | grep -v __pycache__; echo "완료 패키지 변경 줄 수 (0이어야 함): $(git status --porcelain src/cvlab/gcode src/cvlab/judge config/gcode.yaml config/judge.yaml data/gcode_samples | grep -v __pycache__ | wc -l)"
```

⑥ 소유 검사 (세 작업 공통, T5 · T7a 세부청사진과 같은 명령)

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

⑦ V2 지문 (시작과 끝에 같아야 함)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && sha256sum scripts/method_screening/*.py tests/test_method_screening.py
```

판정: ① 모두 통과 (`_local/`이 있으면 skip 0), 함수 ≥ 30 (시간은 판정에 안 씀, 부하와 함께 기록). ② 원점 몫이 정수, 20 배수 True, 한쪽 띠 칸 12.5–14.5, 코드 두 줄 True, T15 연결 pass, 그림자 51칸 = 1.02 mm (± 1칸), 넓힌 뒤 53칸 (± 1), 심도 밖 층 9, 마지막 층 약 50 %. (6차 정정: 5차 §3.1 손계산대로 H20 줄 고르기 · 탑 끝 4.8 mm를 고침) ③ 위 판정용 값. 쓰기 거부 "(○)". ④ 절 누락 빈 목록, 키워드 모두 True. ⑤ grep exit=1, 변경 줄 0. ⑥ 위반 빈 목록 (T5 · T7a 파일은 그 소유로 보이면 정상). ⑦ 시작 값과 같음.

### 8.2 팀장 검사

- 명령 ②의 합성 탑 G코드에서 그림자 길이와 심도 밖 층 수를 팀장이 손으로 다시 계산합니다 (1.8 × tan 30° = 1.0392 mm, Z 8.4–10.0 = 9층).
- caliper 마지막 층의 이유 비트 그림 (`results/region_t4b/`)을 G코드 경로 그림과 겹쳐, 홈 바닥이 depth, 높은 블록 뒤 Y쪽 띠가 occlusion, 스커트가 type으로 칠해졌는지 봅니다.
- `plan_passes`가 낸 voron24 · caliper 패스 수를 T5 `CHECK` 줄의 패스 수와 대조합니다 (같은 약속 §6.5, 서로 독립 구현). 다르면 둘 중 어느 쪽이 약속과 다른지 판정합니다.
- `build_region` 코드에서 측정값을 받는 인자가 없는지, 주 코드 우선순위가 §6.2와 같은지 코드를 직접 읽습니다.
- 최종 윗면 덮임률이 100 %인지, 아니면 그 이유가 문서에 있는지 봅니다. A안 · B안 권장 근거의 숫자를 표에서 다시 셉니다.
- 대조표의 명세 시작·끝 지문을 비교해 명세가 바뀌었으면 이 작업이 쓰는 필드가 영향을 받는지 봅니다.

## 9. 금지 사항

- 측정값 (실측 지도, Δ)을 보고 판정 영역을 정하지 않습니다. `build_region`은 G코드 · 정답 지도 · 설정만 받습니다.
- `src/cvlab/gcode/` · `src/cvlab/judge/` · `data/gcode_samples/`를 고치지 않습니다. T15 코드표를 바꾸지 않습니다 (심도는 9, J-2는 따로).
- T5 시나리오 산출물 (`docs/판정-시나리오*` · `config/scenarios/` · `scripts/scenario_expected.py`)과 `data/_truth/` · `src/cvlab/sim/`을 읽지 않습니다. `cvlab.io` · `cvlab.config`를 import하지 않습니다.
- 슬라이서를 실행하지 않습니다. G코드를 내려받지 않습니다. D-19 파일에서 나온 그림·지도는 커밋 대상 폴더에 두지 않습니다 (`results/`만).
- 숫자를 지어내지 않습니다. 설정 값은 결정 번호 · 청사진 · 요소 청사진 · `[추정]` (이유) 중 하나를 붙입니다.
- V2 미커밋 파일을 고치거나 되돌리지 않습니다. git 쓰기 명령을 쓰지 않습니다 (읽기만). `pip install` · 유료 API · Plane 수정을 하지 않습니다.
- §5 소유 표 밖의 파일을 만들거나 고치지 않습니다. G4 · E2 요소 청사진은 고치지 않고 문서 §13에 바꿀 점을 적습니다.
- 범위를 바꾸고 싶으면 (예: 측정 격자 정렬까지) 멈추고 팀장에게 보고합니다.

## 10. 시작 확인 항목

`docs/운영/결과_T4b_대조표.md`를 만들고 "시작 확인" 절에 적은 뒤 시작합니다.

- [ ] 브랜치 · HEAD, `git status --short` 기준선, 명령 ⑦ 출력 (V2 지문)
- [ ] 명세 상태: `sha256sum docs/하드웨어-데이터-명세.md`, 줄 수, 수정 시각, `git diff --stat HEAD -- docs/하드웨어-데이터-명세.md` (끝날 때 다시 재서 비교)
- [ ] 목표 RG1 – RG15를 자기 말로 한 줄씩
- [ ] §3 입력 파일이 모두 있는지. `data/gcode_samples/_local/`의 두 파일 지문이 `MANIFEST.csv`와 같은지
- [ ] Python · numpy · scipy 판
- [ ] §5 소유 표를 읽었고 T5 · T7a 경로를 건드리지 않으며 T5 시나리오 산출물을 읽지 않는다는 확인
- [ ] 마감: 전체 11-02

## 11. 종료 대조표 양식

```markdown
## 종료 대조 (2026-11-0X HH:MM)

| 목표 항목 | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| RG1 격자 원점 | 0.4 배수 · 20 배수, 높이 차 0 | 명령 ② · 시험 | |
| RG2 엣지 띠 | 자동 띠 voron24 a · caliper b mm, H20 한쪽 n칸 | 명령 ② | |
| RG3 가림 | 그림자 x mm (기대 1.039), 넓힘 2칸, side 3종 비율 | 명령 ② · 문서 §4 | |
| RG4 심도 | caliper 층 n (41), 마지막 층 p % (62), ± 1 mm 민감도 | 명령 ③ · 문서 §5 | |
| RG5 종류 · PRIME | 제외 종류 n종, PRIME 칸 n, IRONING 넣음 | 시험 | |
| RG6 시야 | voron24 a × b, caliper c × d 패스 | 명령 ③ | |
| RG7 비트 · 코드 | 우선순위 시험 n개 | 시험 | |
| RG8 영역 비율 | voron24 x %, caliper y % (전체 합산, 0.2 mm 칸 n) | 명령 ③ · 문서 §8 | |
| RG9 T15 연결 | judge_print_fine pass, 이유별 칸 수 일치 | 명령 ② | |
| RG10 caliper 처리안 | 덮임률 x %, B안 되찾는 칸 y %, 추가 z 분, 권장 | 문서 §9 | |
| RG11 결정 기록 | GCD-02 · 03 · 07 · JDG-03 | 문서 §11 | |
| RG12 저장 · 재현 | load 같음, 두 번 같음 | 시험 | |
| RG13 속도 | voron24 t s, caliper t s | 명령 ③ | |
| RG14 문서 | 절 0–13 | 명령 ④ | |
| RG15 시험 · 차단 | n개 통과 t s, grep 0, 소유 위반 0, V2 지문 같음, 완료 패키지 변경 0 | 명령 ① · ⑤ · ⑥ · ⑦ | |

명세 시작 · 끝 지문: (같음 / 바뀜 + 영향 필드)
검증 명령 실행 결과: (①–⑦ 출력 붙여 넣기)
남은 문제: (없으면 "없음")
```

## 12. 후속 결과 (5차 · 6차)

| 항목 | 결과 | 근거 |
|---|---|---|
| 1차 산출물 (4e2a369) | RG1–RG14 ○, RG15 △ (시험 안 시간 단정문이 부하 때 실패) | [팀장검증 5차](팀장검증_5차.md) §3 |
| R-1 | `tests/region` 시간 단정문 0 (다섯 폴더 grep 0), voron24 141 760칸 단정문으로 바꿈 | 116f9cd · [6차](팀장검증_6차.md) §7 |
| R-2 → RG16 | 팀장이 POST 줄을 다시 냄: caliper P-B 0.04330 mm (= 68e-6 × 21.2255 × 30) · 288 360 · 940 · 72칸, voron24 0.04 mm · 15 348 · 3 707칸 (판정 칸 141 760 그대로) | 6차 §1 · §7.1 |
| R-3 | `code_6` (마지막 행 24 626 619 고운 칸), `code_9` 없음 | 6차 §7.1 |
| J-3 연결 | `judge_print`가 post 영역 ∩ 두 Δ 유효 칸으로 비교, caliper 비교 칸 940 · 72 (T15 시험) | 6939ef0 · 6차 §6.3 |
| 명령 ② 정정 | H20 13.0칸, 그림자 51칸 = 1.02 mm, 넓힌 뒤 53칸 (팀장이 고친 명령으로 실행) | 6차 §7.2 |
| 다음 | T5-2 (T4b 판정 영역 · post 영역으로 기대 판정 다시 계산, T3 S2 안), T10 (마지막 층 Δ를 영역 밖까지 남겨 `delta_cmp_mm`으로) | 세부청사진 T3 §12 |
