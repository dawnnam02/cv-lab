# 세부청사진 T5 · 사용자 G코드 점검과 판정 시험 시나리오 (E3)

> 상위: [청사진_가상데이터단계](청사진_가상데이터단계.md) §1.2 (D-16 조건 C1–C3) · §2.2 (C12) · §2.3 · §4.1 · §4.2 · §4.3 (T5) · §5.2 · 작성: 2026-10-27 총괄 팀장 · 상태: **착수 전 (메인 확인 대기)**
> **일정 앞당김.** 청사진 일정은 11-02 ~ 11-04 (G0 직전)입니다. 사용자 지시 (10-27) "선행 작업 없이 병렬로 진행할 수 있는 작업 진행해."에 따라 **10-27에 시작해 10-31에 마감**합니다 (6일 앞당김). T4b · T7a와 동시에 돕니다.
> **청사진과 다른 점 (청사진은 고치지 않음, 메인에게 보고).**
> ① 선행 T2: 2차 결과 (91f305c, 팀장 검증 전)의 값을 씁니다. 팀장 검증에서 값이 바뀌면 그 값만 고칩니다.
> ② 산출 문서를 둘로 나눕니다. **점검 문서 (`docs/G코드-점검.md`)는 공개**, **시나리오 문서 · 설정 · 계산 스크립트는 처리 담당 열람 금지** (청사진 §5.2 "어떤 출력 오차를 넣었는지 처리 담당에게 알리지 않음").
> ③ 기대 판정은 **임시 판정 영역** (출력물 − 제외 종류 − 심도 밖)으로 계산합니다. T4b 판정 영역이 나오면 다시 계산합니다 (후속 T5-2, 11-03, 반나절).
> ④ 청사진 §5.1은 T5와 T4b를 같은 기준모델 담당에게 줍니다. 지금은 동시에 돌아서 **다른 worker 인스턴스**입니다. 이 인스턴스는 시나리오를 알기 때문에 **뒤에 처리 작업 (T4b · T7–T12)을 맡지 않습니다.**
> ⑤ 참 판정 값은 **pass · fail 둘**입니다 (T1 세부청사진 A19 ④, 팀장 확정. 명세 884daac 부록 A에 반영됨: pass ⇔ `truth.pass_pct` ≥ 95). 경계는 시나리오 이름과 의도로 표시합니다. `score_c12`는 참 값 borderline도 받지만 이 작업은 쓰지 않습니다.
> **명세가 바뀌는 중.** T1 2차 결과가 884daac (10-27 20:40)로 들어왔지만 상태는 "2차 보완 끝, 팀장 검토 전"입니다. 팀장 검토 뒤 더 바뀔 수 있고, T1 worker가 아직 고칠 수 있습니다. T6 후속 worker도 `src/cvlab/io/`를 고치는 중입니다. 둘 다 읽기만 합니다. 이 작업이 쓰는 명세 값 (`truth.print_error_params` · `truth.judgement` · `truth.pass_pct` · `meta.specimen_role` (`public_gcode` 들어옴) · `meta.zero_ref_method` (step_gauge 들어옴, z_only는 판정 거부 X2) · `meta.scan_pass_idx` (X를 바꾼 줄 번호) · `meta.scan_length_mm` · 9절 스캔 횟수 식 · 0.4절 높이 식)이 바뀌면 대조표에 적고 팀장에게 알립니다.
> **사용자 G코드 (D-10, 경로 대기).** 작업 중에 메인이 경로를 주면 같은 점검을 한 열 더 합니다. 시나리오 기대 판정에도 시편으로 더합니다.
> 함께 도는 작업: [T4b 판정 영역](세부청사진_T4b_판정영역.md) · [T7a 레이저 선 추출](세부청사진_T7a_레이저선추출.md). **§5 소유 표를 지킵니다.**

| 항목 | 내용 |
|---|---|
| Plane | E3 "사용자 G코드 점검과 판정 시나리오" (D-17 재구성 뒤 목표 2 "정답 만들기"의 단계 줄). 상태 바꾸기는 메인 몫 |
| 담당 | 기준모델 담당 (새 인스턴스), Opus 5.5, effort medium. 독립 검증: 팀장 |
| 기간 | 2026-10-27 ~ 10-31 (후속 T5-2: T4b 뒤 11-03) |
| 선행 | 없음으로 시작. T4a (완료, 파서) · T15 (완료, 판정 함수) · T14 2차 (75a5561, SV08 · LM-T14-2) · T2 2차 (91f305c) |
| 후행 | T3 (시나리오를 주입해 판정 시험 데이터를 만듦) · T4b (패스 수 대조) · T14 (매크로 패스·기준물 배치) · T1 (n_pass · specimen_role 숫자) · C12 판정 (T10) |
| 산출물 | §4 경로 · `docs/운영/결과_T5_대조표.md` |

## 1. 목적

두 가지를 합니다.

1. **G코드 점검.** 테스트 G코드 두 개 (D-19: `voron24_test_box` · `caliper_pyramid`)가 이 측정 (시야 20 mm · 스캔 40 mm · 심도 8 mm · 모든 층 스캔 D-18 · SV08 + Klipper)에 맞는지 점검표로 확인하고, SV08용으로 다시 슬라이스할 때 무엇이 바뀌어야 하는지 요구서로 씁니다. 슬라이서는 돌리지 않습니다.
2. **판정 시험 시나리오.** 합격 · 경계 · 불합격이 나오는 출력 오차를 종류 × 강도 표로 정하고, 각 시나리오의 기대 판정을 T15 함수로 미리 계산합니다. 표는 T3 시뮬레이터가 그대로 주입할 수 있는 파라미터 형식입니다. C12 (참 불합격을 합격으로 0건)를 시험하는 재료입니다.

## 2. 목표 (완료 기준)

### 2.1 G코드 점검 (공개)

| 번호 | 완료 기준 | 측정 방법 |
|---|---|---|
| CK1 | **대상과 지문.** D-19 두 파일 (`data/gcode_samples/_local/`)의 SHA-256 = `MANIFEST.csv`. 시험용 평판 `plate20` (§6.9)을 스크립트로 만들어 `docs/G코드-점검_자료/plate20.gcode`에 둠. 명세 `meta.specimen_role` 값 (D-19 파일은 `public_gcode` 예정)을 파일마다 적음 | 명령 ① |
| CK2 | **점검표 빈칸 0.** §6.1 항목 24줄 × 파일 (voron24 · caliper, 사용자 G코드가 오면 한 열 더). 칸마다 값 또는 `[미상]` + 이유, 근거 (G코드 줄 번호 · `[계산]` 식 · `[출처]`) | 명령 ② |
| CK3 | **크기 · 패스.** 물체 경계 상자 (§6.2, T4b와 같은 약속) 폭 × 높이와 시야 20 mm · 스캔 40 mm 비교. 패스 수를 세 경우로: 그대로 (0°), 90° 돌림, `extend_scan_len` (Y를 스캔 길이로 덮음). 권장 방향 | 명령 ① · ② |
| CK4 | **층 · 심도 · 0점.** 층 수 (주석 · 압출 Z · 선언), 층 높이 (첫 층 · 나머지 · 가변 여부), 최대 Z, 윗면 높이 폭 > 8 mm인 층 수 (caliper는 T4a 값 41과 대조), `bed_marker` 가능 여부 (명세 0.4: 8 mm를 넘는 층은 불가) → 권장 `meta.zero_ref_method` (step_gauge · bed_marker · ref_tower 중, z_only는 판정 거부 X2) | 명령 ① |
| CK5 | **스캔 시간 (D-18 모든 층).** §6.3 두 식 (LM-T14-2 실제 이동 · 명세 9절 순수 스캔)으로 층당 시간과 출력 전체 추가 시간 (+ 식힌 재측정 대기). 패스 수 경우별 | 명령 ① · ② |
| CK6 | **방언 · 펌웨어.** 파일마다 명령 종류별 개수 표 (G · M · T · 매크로). SV08 + Klipper에서 그대로 못 쓰거나 설정이 필요한 명령 목록 (개수 · 첫 줄 번호 · 처리 방법 · 근거). 근거 없는 칸은 `[추정]` · `[미상]` | 명령 ② |
| CK7 | **다시 슬라이스 요구서.** 파일마다 필요 여부 (예/아니오)와 §6.5 항목별 "지금 값 (줄 번호) → SV08 요구 값 → 근거 → 필수/권장". 슬라이서 실행 없이 글로만 | 명령 ② |
| CK8 | **기준물 · 게이지 배치 (D-16 C1 · C2 · C3).** LM-T14-2 기본 배치 (블록 0.2 · 5 · 10 · 15 · 20 mm, `ref_xs` 230–330, `ref_y0` 165)와 물체 위치·이동 경로가 겹치는지. **C1 (심도 안 계단 두 개, 간격 약 3 mm 이하)과 LM-T14-2 (블록 간격 5 mm, 층마다 블록 하나만 스캔)가 맞는지 판정**. 필러게이지 0.2 · 0.3 · 0.4 mm와 기준 탑 자리 | 명령 ② · 문서 §7 |
| CK9 | **보조 시편 필요 여부.** 필요 / 불필요와 이유 (E3 축소 D-11: 필요할 때만). 필요하면 모양 · 크기 요구만 (G코드는 만들지 않음) | 문서 §8 |
| CK10 | **문서.** `docs/G코드-점검.md` 절 0–9 (§4 목차). 넘길 것 (T4b · T3 · T14 · T1) 목록 | 명령 ② |

### 2.2 판정 시험 시나리오 (처리 담당 열람 금지)

| 번호 | 완료 기준 | 측정 방법 |
|---|---|---|
| SC1 | **참 판정 규칙.** `truth.judgement` ∈ {pass, fail}. pass ⇔ `truth_pass_pct` ≥ 95. `truth_pass_pct` = 참 Δ로 U = 0 (방식 A) 판정한 합격점 비율, 판정 칸 0.2 mm (D-20 R1), 전체 층 합산 (D-08), 측정 당시 (D-06). 경계는 의도 B와 이름으로. C12 채점의 참 값은 `truth.judgement`, 경계 행은 따로 보고 | 명령 ④ |
| SC2 | **오차 종류 사전 ≥ 6종.** 이름 고정: `z_offset` · `z_scale` · `local` · `warp` · `missing_layer` · `extrusion` (더해도 됨). 종류마다 매개변수 (단위 접미사), 참 Δ 식 Δ_true(x, y, n), **보이는 Δ 식 Δ_seen** (명세 0.4 높이 식과 베드 기준 스캔 0점으로 유도, `[계산]`), `observable` ∈ {yes, partial, step_gauge_only}, 물리 원인, T2 MF ID | 명령 ③ · 문서 §2 |
| SC3 | **시나리오 ≥ 19개.** 종류마다 P · B · F 하나 이상 + `NOM-P00`. 이름 정규식 `^[A-Z]{3}-[PBF]\d{2}$` (네 번째 뒤 글자 = 의도). 위치는 물체 경계 상자 기준 상대값 (u, v ∈ [0, 1]), 층은 상대값 (0 – 1) → 다시 슬라이스해도 같은 뜻 | 명령 ③ |
| SC4 | **T3 주입 형식.** `config/scenarios/판정시나리오_v1.yaml` (§6.6 고정 키). `print_error_params`는 명세 부록 A `truth.print_error_params` 꼴 그대로: `{"scenario": 이름, 종류: {매개변수: 값}}` | 명령 ③ |
| SC5 | **기대 판정 계산.** `scripts/scenario_expected.py`가 T15 함수 (`fine_to_cell_layer` · `judge_print`)로 시편 3개 (plate20 · voron24 · caliper) × 시나리오를 계산. U 20.9 µm (주, D-15), 14.6 µm (D-16 계단 기준물, 조건 C1–C3 전제), 0 (참). 판정 칸 0.2 (주) · 0.4 (보조). 결과 `docs/판정-시나리오_자료/기대판정.csv` (§6.8 열 고정) | 명령 ① · ④ |
| SC6 | **의도 = 기대 판정.** 판정 대상 행 (step_gauge off에서 observable yes · partial, on에서 step_gauge_only)은 P → pass (보이는 합격점 ≥ 98 %), B → hold, F → fail (보이는 불합격점 ≥ 10 %)이 **100 %**. 한 시편에서 안 맞는 행은 강도를 고치거나, 그 시편에서 그 시나리오를 빼고 이유를 적음 | 명령 ④ |
| SC7 | **경계 행 구성.** 판정 대상 B 행 중 참 pass ≥ 2, 참 fail ≥ 2 (시편마다). 참 불합격이 보류 띠에 드는 경우를 C12로 시험하기 위해 | 명령 ④ |
| SC8 | **보이지 않는 오차 (C12 위험).** `z_scale` F 행을 step_gauge off · on 두 줄로: off면 보이는 판정 pass · 참 fail (C12 위반이 예상되는 행), on이면 fail. 이 결과를 D-14 · D-16과 묶어 문서 §6에 | 명령 ④ · 문서 §6 |
| SC9 | **전체 층 합산의 희석 (D-08 · R7).** 한 층에만 있는 국소 결함이 전체 판정을 불합격으로 바꾸려면 넓이가 얼마여야 하는지, R7 층 경고 (한 층 불합격점 > 50 %)가 뜨는 넓이는 얼마인지 시편별 표. 국소 결함 F 시나리오는 여러 층에 걸치게 설계 | 문서 §7 |
| SC10 | **블라인드.** 시나리오 YAML · 문서 · 계산 스크립트 첫 줄에 "처리 담당 (T4b · T7–T12) 열람 금지". 평가용 세트 (시드 · 배정 · 정확한 강도)는 만들지 않음 (팀장이 T3 때 따로). 문서에는 개발용 목록과 평가 세트 설계 원칙 (강도 범위만) | 명령 ③ · 문서 §8 |
| SC11 | **문서.** `docs/판정-시나리오.md` 절 0–10 (§4 목차) | 명령 ⑤ |
| SC12 | **스크립트 · 차단.** 스크립트 두 개 오류 0, `scenario_expected.py` ≤ 15분. 슬라이서 · `subprocess` 0. import는 `cvlab.gcode` · `cvlab.judge`만. `_truth` 0. 소유 위반 0, V2 지문 같음 | 명령 ① · ⑥ · ⑦ · ⑧ |

## 3. 입력

| 입력 | 경로 | 쓰는 곳 |
|---|---|---|
| G코드 | `data/gcode_samples/_local/` (D-19 두 파일, 읽기만) · `data/gcode_samples/MANIFEST.csv` · `docs/테스트-G코드-후보.md` (출처 · 라이선스) | CK1 – CK8 |
| T4a | `docs/G코드-해석.md` §1 (방언 옮김 표) · §2 (명령 목록) · §6 (두 파일 결과, caliper 41층) · §8 (caliper 주의) · `src/cvlab/gcode/` (import) | CK2 – CK6 · SC5 |
| T14 2차 | `docs/프린터-펌웨어-선정.md` §1 (두 파일 다시 슬라이스 단서) · §9 (LM-T14-2 매크로 · 슬라이서에 넣는 줄 · 층당 시간) · §11 (Klipper 방언 요구) · §14 (출처) | CK5 – CK8 |
| 판정 | `docs/판정-규칙.md` · `src/cvlab/judge/` (import) · 청사진 §2.3 (D-15 · D-16 · D-20) | SC1 · SC5 – SC9 |
| 실패사례 | `docs/측정-실패사례.md` 3.13 MF-GCD · 3.14 MF-JDG · MF-MEC-04 (Z축) · MF-CAL-05 · 5.2 (판정 거부 X1–X7) · 5.4 (조건 C1–C3) | SC2 · SC8 · CK8 |
| 명세 (읽기만, 바뀌는 중, 884daac 기준) | `docs/하드웨어-데이터-명세.md` 0.1 (계단 기준물 · 스캔 폴더 `_pNN`) · 0.4 (높이 식, 0점) · 2절 "스캔 줄과 반복" · 5절 (`meta.scan_pass_idx` · `meta.specimen_role` · `meta.zero_ref_method`) · 9절 (스캔 횟수 식) · 부록 A (`truth.*`) · T1 세부청사진 §11 A19 | CK4 · CK5 · SC1 · SC2 · SC4 |
| 요소 청사진 | `docs/blueprints/E-specimen/E3-test-artifact.md` (보조 시편 판단) · `E2-occlusion-edges.md` (형상 방향 · 간격) | CK9 |

- 웹 검색은 Klipper 명령 지원 확인에만, **10회 이하**. T14 문서 §14 출처를 먼저 씁니다.
- 슬라이서를 실행하지 않습니다 (이 PC에 Bambu Studio가 있어도). G코드를 내려받지 않습니다. 저장소 밖 G코드를 읽지 않습니다 (사용자 G코드는 메인이 경로를 줄 때만).

## 4. 산출물

| 경로 | 공개 | 내용 |
|---|---|---|
| `docs/G코드-점검.md` | 공개 | 점검 문서 |
| `docs/G코드-점검_자료/점검표.csv` · `plate20.gcode` | 공개 | 점검표 원자료 (열: `항목, 파일, 값, 근거`), 시험용 평판 G코드 |
| `scripts/gcode_check.py` | 공개 | 파일마다 요약 줄 `CHECK {json}` + 점검표 CSV |
| `docs/판정-시나리오.md` | **열람 금지** | 시나리오 문서 |
| `docs/판정-시나리오_자료/기대판정.csv` · `희석표.csv` | **열람 금지** | 기대 판정, 희석 표 |
| `config/scenarios/판정시나리오_v1.yaml` | **열람 금지** | T3 주입 형식 |
| `scripts/scenario_expected.py` | **열람 금지** | 기대 판정 계산. 요약 줄 `SCEN {json}` |
| `results/t5/` | Git 밖 | D-19 파일에서 나온 그림 (라이선스 [미상]이라 커밋 폴더에 두지 않음) |
| `docs/운영/결과_T5_대조표.md` | 운영 | 시작 확인 · 종료 대조 |

- `CHECK` 키 (고정): `file, sha256, slicer, flavor, printer_profile, nozzle_mm, layers, layer_h_first_mm, layer_h_mm, z_max_mm, bbox_w_mm, bbox_h_mm, passes, passes_rot90, passes_extend, scan_s_per_layer, scan_total_min, depth_layers, unknown, klipper_issues, reslice`.
- `SCEN` 키 (고정): `n_kinds, n_scenarios, specimens, rows, mismatches, c12_risk_rows, runtime_s`.

`docs/G코드-점검.md` 목차 (절 번호 고정):

```
# 사용자 G코드 점검 (D-19 테스트 G코드)
## 0. 요약
## 1. 점검 대상 (지문 · 역할)
## 2. 점검표
## 3. 크기 · 스캔 패스 · 시간
## 4. 층 · 심도 · 0점 이어 가기
## 5. 방언과 SV08 · Klipper 호환
## 6. 다시 슬라이스 요구서
## 7. 기준물 · 게이지 배치 (D-16 C1–C3)
## 8. 보조 시편 필요 여부
## 9. 넘길 것과 한계
```

`docs/판정-시나리오.md` 목차 (절 번호 고정, 첫 줄은 열람 금지 표시):

```
> 처리 담당 (T4b · T7–T12) 열람 금지. 판정 시험 개발용 목록 (청사진 §5.2)
# 판정 시험 시나리오
## 0. 요약
## 1. 참 판정 규칙
## 2. 오차 종류 사전
## 3. 시나리오 표
## 4. 기대 판정 (U 20.9 · 14.6 · 0 µm, 칸 0.2 · 0.4 mm)
## 5. T3 주입 형식
## 6. 보이지 않는 오차와 C12 (D-14 · D-16)
## 7. 전체 층 합산의 희석 (D-08 · R7)
## 8. 평가 세트 설계 원칙 (블라인드)
## 9. T4b 판정 영역으로 다시 계산 (T5-2)
## 10. 한계
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

- T5는 `src/` 아래에 코드를 만들지 않습니다. 계산은 `scripts/`의 두 파일로만 합니다. pytest 시험은 만들지 않고, 스크립트에 `--check` (기존 산출물 재검사) 모드를 둡니다.
- T4b 산출물을 읽지 않습니다 (패스 수 대조를 독립으로 하기 위해). 임시 판정 영역은 T5가 따로 만듭니다 (§6.7).

## 6. 설계 규칙

### 6.1 점검표 항목 (최소 24줄, 더해도 됨)

| # | 항목 | # | 항목 |
|---|---|---|---|
| 1 | 파일 · 지문 (MANIFEST 대조) | 13 | 윗면 높이 폭 > 8 mm인 층 수 |
| 2 | 슬라이서 · 판 | 14 | 스커트 · 브림 · PRIME · 서포트 · 아이롱 유무 |
| 3 | 방언 (`meta.gcode_flavor` 옮긴 값) | 15 | 모르는 명령 · 압출 사이 매크로 (T4a 파서 결과) |
| 4 | 프린터 프로필 (머리말 printer_model · settings_id) | 16 | SV08 + Klipper에서 그대로 못 쓰는 명령 (개수) |
| 5 | 노즐 지름 vs SV08 기본 | 17 | 펌웨어 리트랙트 (G10/G11) · 원호 (G2/G3) → Klipper 설정 요구 |
| 6 | 선폭 (외벽 · 기본) | 18 | 시작 · 끝 매크로 이름 |
| 7 | 층 수 (주석 · 압출 Z · 선언) | 19 | 층 변경 칸에 `SCAN_LAYER`를 넣을 자리 (줄 번호) |
| 8 | 층 높이 (첫 층 · 나머지 · 가변) | 20 | 끝 G코드에 마지막 층 스캔 + `COOL_RESCAN`을 넣을 자리 |
| 9 | 최대 Z vs 심도 8 mm → `bed_marker` 가능 여부 | 21 | 베드 좌표 · 물체 위치 (SV08 베드로 옮길 양) |
| 10 | 물체 경계 상자 W × H (§6.2) vs 시야 20 · 스캔 40 | 22 | 필러게이지 · 기준 탑 · 계단 기준물 자리 (D-16 C1 · C2) |
| 11 | 패스 수 (0° · 90° · extend) | 23 | 다시 슬라이스 필요 (예/아니오) |
| 12 | 층당 스캔 시간 · 전체 추가 시간 (D-18) | 24 | `meta.specimen_role` |

### 6.2 스캔 패스 약속 (T4b와 같은 글, 서로 독립 구현 → 팀장이 대조)

| 항목 | 규칙 |
|---|---|
| 경계 상자 B | 판정 대상 종류 (SKIRT · BRIM · SUPPORT · PRIME-TOWER 밖, 층 ≥ 0) 압출 선분 끝점의 경계 상자를, 그 선분들 선폭 최댓값의 반만큼 넓힌 것. 폭 W (X), 높이 H (Y) |
| X 패스 수 | n_x = max(1, ⌈(W − o) ÷ (F − o)⌉). F = 20 mm (청사진 §1), o = 2 mm (MF-GCD-08) |
| Y 패스 수 | n_y = max(1, ⌈(H − o) ÷ (L − o)⌉), L = 40 mm (M54 · LM-T14-2). extend 경우는 n_y = 1, L = H |
| 90° 돌림 | W와 H를 바꿔 같은 식 |
| 계산 | 올림은 nm 정수 (rint(× 10⁶))로 해서 경계 실수 오차를 피함 |

### 6.3 스캔 시간 식

| 식 | 내용 | 근거 |
|---|---|---|
| ① 실제 이동 (LM-T14-2) | 층당 = n_x · n_y · (5 + L) ÷ 2.4 + (5 + 20) ÷ 2.4 (계단 기준물 한 번) + 5 s (이동) | `lead_in` 5 mm · 2.4 mm/s · `ref_len` 20 mm [출처: docs/프린터-펌웨어-선정.md §9], 이동 5 s [추정, 같은 곳] |
| ② 순수 스캔 (명세 9절) | 층당 = 줄 수 (n_x · n_y) × L ÷ 2.4 (40 mm면 16.7 s) | 명세 9절 스캔 횟수 식 (줄 = `meta.scan_pass_idx`) |
| 전체 추가 | 층 수 × 층당 + 식힌 재측정 (대기 1,800 s + 스캔 한 번) | D-18 · D-06 · `COOL_RESCAN` 기본 1,800 s [추정, T14 §9] |

- 패스가 둘 이상이면 LM-T14-2 매크로 (층마다 `scan_x` 한 줄)가 바뀌어야 합니다. 이것을 T14에 넘길 것으로 적습니다.

### 6.4 방언 · Klipper 점검

- 명령은 파일 글을 줄마다 읽어 첫 단어로 셉니다 (주석 · 체크섬 뺌). T4a 파서의 `unknown` · 경고와 같이 적습니다.
- "그대로 못 씀"의 판정 근거는 Klipper 공식 문서 (T14 §14 [출처 1])를 우선합니다. 예상 후보: `M862.x` · `G80` · `M702` · `M900` (Prusa · Marlin 전용), `G10`/`G11` (`[firmware_retraction]` 필요), `G2`/`G3` (`[gcode_arcs]` 필요). 목록은 파일에서 실제로 센 것만 씁니다.

### 6.5 다시 슬라이스 요구서 (문서 §6 표 열)

`항목, 지금 값 (줄 번호), SV08 요구 값, 근거, 필수/권장`. 최소 항목: 노즐 · 선폭 · 층 높이 · 베드 좌표와 물체 위치 · 방향 (패스 수) · 시작/끝 매크로 · 층 변경 칸 (`SCAN_LAYER LAYER={layer_num - 1}`) · 끝 G코드 (마지막 층 스캔 + `COOL_RESCAN`) · 펌웨어 리트랙트 · 방언 · 기준 탑 물체 추가 (8 mm 넘는 출력, `ref_tower`) · 계단 기준물 · 필러게이지 자리 비우기 (D-16 C2).

### 6.6 시나리오 YAML (`config/scenarios/판정시나리오_v1.yaml`)

```yaml
# 처리 담당 (T4b · T7–T12) 열람 금지. 판정 시험 개발용 목록 (청사진 §5.2)
version: 1
truth_rule: "pass ⇔ truth_pass_pct ≥ 95 (U = 0, 칸 0.2 mm, 전체 층 합산 D-08, 측정 당시 D-06). T1 A19 ④"
kinds:
  z_offset:
    params: {dz_um: "출력 전체 높이 이동, + = 높음"}
    delta_true: "Δ = dz (모든 층 · 모든 칸)"
    delta_seen: "(명세 0.4 식과 베드 기준 스캔 0점으로 유도해 적음)"
    observable: yes            # yes | partial | step_gauge_only
    cause: "(물리 원인)"
    mf: [MF-...]
  # z_scale · local · warp · missing_layer · extrusion 도 같은 키
scenarios:
  - name: NOM-P00
    intent: pass               # pass | borderline | fail (이름 네 번째 뒤 글자 P · B · F와 같아야 함)
    specimens: [plate20, voron24_test_box, caliper_pyramid]
    print_error_params: {scenario: NOM-P00}
  - name: OFS-B01
    intent: borderline
    specimens: [plate20, voron24_test_box, caliper_pyramid]
    print_error_params: {scenario: OFS-B01, z_offset: {dz_um: 190}}
```

- 키는 고정입니다: 최상위 `version · truth_rule · kinds · scenarios`, 종류마다 `params · delta_true · delta_seen · observable · cause · mf`, 시나리오마다 `name · intent · specimens · print_error_params`.
- 매개변수 이름은 명세 단위 접미사 규칙 (`_um` · `_mm` · `_ppm` · `_rel`)을 따릅니다. 위치는 `loc_rel: [u, v]`, 층 범위는 `layer_from_rel` · `layer_to_rel`.
- 강도 값은 "시험용 가정, 측정값 아님"이고 고른 이유 (T · U와의 관계)를 문서 §3에 씁니다.

### 6.7 종류별 지침 (식은 worker가 정하고 문서에 근거)

| 종류 | 참 Δ (뼈대) | 관측 (지침) |
|---|---|---|
| `z_offset` | Δ = dz (팀장 손 검사가 이 정의를 씀, 바꾸지 않음) | 0점을 같은 센서의 베드 기준 스캔으로 잡으면 보임 (명세 0.4). 유도를 적음 |
| `z_scale` | Δ = g × Z_ref(x, y, n) (`gain_ppm`) | Z축 오차는 출력과 측정이 함께 가져 베드 기준 스캔 뒤 대부분 빠짐 → `step_gauge_only` (청사진 §1.2, MF-CAL-05). 남는 몫을 식으로 |
| `local` | 층 범위의 각 층 윗면, 같은 XY에 가우시안 함몰 (−) · 돌기 (+). `amp_um` · `sigma_mm` · `loc_rel` · 층 범위 | yes |
| `warp` | 물체 가운데에서 먼 곳이 들림 (거리의 제곱 꼴 등), 시작 층부터 | 베드에서 들뜬 몫이 보이는지 유도 (yes 또는 partial) |
| `missing_layer` | 층 k가 빠짐. 회복형 (k층 노출 윗면만 −h_k) · 누적형 (k층 위 모두 −h_k) | 원인별로 다름 (압출 멈춤은 보임, Z 건너뜀은 Z축이라 `step_gauge_only`) |
| `extrusion` | 윗면 일정 이동 `dz_um` + 결 `ripple_um` · `ripple_period_mm` | yes. 결은 판정 칸 평균으로 줄어듦 (T15 M13) |

### 6.8 기대 판정 계산 (`scripts/scenario_expected.py`)

| 단계 | 규칙 |
|---|---|
| 정답 | `parse_file` → 물체 경계 상자 + 1 mm로 `make_grid` (0.02 mm) → `build_reference(result, grid=…)` |
| 층 | 꼭대기 층은 `footprint(k)`를 차례로 덮어 한 번에 구함 (`height_at_layer(n)`을 층마다 부르면 층 수 제곱만큼 느림) |
| 임시 판정 영역 | 출력물 칸 − 꼭대기 종류 ∈ {SKIRT, BRIM, SUPPORT, PRIME-TOWER} − 심도 밖 (z_n − Z_ref > 8.000 mm, nm 정수). 엣지 띠 · 가림 · 시야는 넣지 않음 → `region_source = stand-in-v1` |
| Δ | 시나리오마다 층마다 Δ_true, Δ_seen. 영역 밖 NaN |
| 묶기 | 층마다 `fine_to_cell_layer` (0.2 · 0.4 mm)로 판정 칸 층을 만들고 고운 배열은 버림 (메모리) |
| 판정 | `judge_print`: U 0.0209 (`U_source` "D-15 기본 U 20.9 µm, T12 전 참고값"), 0.0146 ("D-16 계단 기준물, 조건 C1–C3 전제"), 0 ("참 판정, 방식 A") |
| 기대 판정 열 (고정) | `scenario, specimen, kind, intent, observable, step_gauge, n_layers, n_region_cells, truth_pass_pct, truth_judgement, seen_pass_pct, seen_hold_pct, seen_fail_pct, verdict_U20_9, verdict_U14_6, verdict_alt04_U20_9, region_source` |
| step_gauge | `step_gauge_only` 종류는 off (Δ_seen 그대로) · on (Δ_seen = Δ_true) 두 줄. 나머지는 off 한 줄 |

### 6.9 시험용 평판 `plate20`

- 20 × 20 mm, 선 간격 0.4 mm 지그재그, 선폭 0.4 mm, 층 0.2 mm × 10층 (Z 0.2 – 2.0), 위치 X 165 – 185 · Y 165 – 185 (SV08 베드 가운데 근처, 자리표시). 머리말 첫 줄 "스크립트가 만든 시험용 평판, 실제 슬라이서 출력 아님".
- 같은 입력이면 같은 바이트 (재현). 라이선스 문제가 없어 커밋 대상이고, T3도 같은 평판을 쓸 수 있습니다.

## 7. 단계

| 단계 | 날짜 | 할 일 | 끝난 표시 |
|---|---|---|---|
| S1 | 10-27 | 시작 확인 (§10). `gcode_check.py` (CK1 · CK3 – CK6), plate20 | 명령 ① |
| S2 | 10-28 | 점검표 · 다시 슬라이스 요구서 · 기준물 배치 · 보조 시편 (CK2 · CK7 – CK9), 점검 문서 | 명령 ② |
| S3 | 10-29 | 오차 종류 사전 · 시나리오 YAML (SC1 – SC4 · SC10) | 명령 ③ |
| S4 | 10-30 | `scenario_expected.py`, 기대 판정 · 희석 표, 강도 조정 (SC5 – SC9) | 명령 ④ |
| S5 | 10-31 | 시나리오 문서 (SC11), 검증 명령 전부, "종료 대조" → 팀장 검증 | 대조표 |
| T5-2 | 11-03 (T4b 뒤) | T4b `RegionStack`으로 기대 판정 다시 계산 (`region_source = T4b`), 의도 불일치가 생기면 강도 조정. 대조표에 "후속" 절 | 명령 ④ |

## 8. 검증

### 8.1 검증 명령 (Git Bash에 그대로 붙여 넣기)

① 스크립트 실행

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 PYTHONPATH=src python scripts/gcode_check.py --summary 2>&1 | grep -E "^CHECK|Error|오류"; echo '--- 기대 판정'; time (PYTHONIOENCODING=utf-8 PYTHONPATH=src python scripts/scenario_expected.py 2>&1 | grep -E "^SCEN|Error|오류")
```

② 점검 문서 구조 · 점검표 빈칸

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import re, csv
t = open('docs/G코드-점검.md', encoding='utf-8').read()
print('절 누락', [h for h in map(str, range(10)) if not re.search(r'^## %s\. ' % h, t, re.M)])
m = re.search(r'^## 2\. [^\n]*\n(.*?)(?=^## )', t, re.M | re.S)
rows = [l for l in (m.group(1) if m else '').splitlines() if l.startswith('|')][2:]
print('점검표 행', len(rows), '/ 빈 칸 있는 행', [r.split('|')[1].strip() for r in rows if any(c.strip() == '' for c in r.strip().strip('|').split('|'))])
for k in ['voron24_test_box', 'caliper_pyramid', 'SV08', 'LM-T14-2', 'D-16', 'C1', 'C2', 'D-18', 'bed_marker', 'public_gcode', '다시 슬라이스', '보조 시편', '41']:
    print(k, k in t)
C = list(csv.DictReader(open('docs/G코드-점검_자료/점검표.csv', encoding='utf-8')))
print('점검표.csv 행', len(C), '/ 값·근거 빈 행', [(r['항목'], r['파일']) for r in C if not r['값'].strip() or not r['근거'].strip()])
print('근거 태그 수', len(re.findall(r'\[(계산|추정|미상|출처|확인 필요)', t)))
EOF
```

③ 시나리오 YAML

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import yaml, re, collections
p = 'config/scenarios/판정시나리오_v1.yaml'
print('첫 줄 열람 금지', '열람 금지' in open(p, encoding='utf-8').readline())
for q in ['docs/판정-시나리오.md', 'scripts/scenario_expected.py']:
    print(q, '첫 3줄 열람 금지', any('열람 금지' in l for l in open(q, encoding='utf-8').readlines()[:3]))
Y = yaml.safe_load(open(p, encoding='utf-8')); K, S = Y['kinds'], Y['scenarios']
print('최상위 키', sorted(Y), '/ 종류', sorted(K), '/ 시나리오', len(S))
print('필수 종류 빠짐', sorted({'z_offset', 'z_scale', 'local', 'warp', 'missing_layer', 'extrusion'} - set(K)))
print('사전 키 빠짐', [k for k, v in K.items() if not {'params', 'delta_true', 'delta_seen', 'observable', 'cause', 'mf'} <= set(v)])
print('observable 값 밖', [k for k, v in K.items() if v.get('observable') not in ('yes', 'partial', 'step_gauge_only')])
print('이름 위반', [s['name'] for s in S if not re.fullmatch(r'[A-Z]{3}-[PBF]\d{2}', s['name'])])
print('의도·글자 불일치', [s['name'] for s in S if {'P': 'pass', 'B': 'borderline', 'F': 'fail'}.get(s['name'][4]) != s['intent']])
print('scenario 키 ≠ 이름', [s['name'] for s in S if s['print_error_params'].get('scenario') != s['name']])
print('사전에 없는 종류', [s['name'] for s in S for k in s['print_error_params'] if k != 'scenario' and k not in K])
c = collections.defaultdict(set)
for s in S:
    for k in s['print_error_params']:
        if k != 'scenario': c[k].add(s['intent'])
print('P·B·F 모자란 종류', [k for k in K if c[k] != {'pass', 'borderline', 'fail'}])
print('NOM-P00 있음', any(s['name'] == 'NOM-P00' for s in S))
EOF
```

④ 기대 판정 CSV

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import csv, collections
R = list(csv.DictReader(open('docs/판정-시나리오_자료/기대판정.csv', encoding='utf-8')))
cols = ['scenario', 'specimen', 'kind', 'intent', 'observable', 'step_gauge', 'n_layers', 'n_region_cells', 'truth_pass_pct', 'truth_judgement', 'seen_pass_pct', 'seen_hold_pct', 'seen_fail_pct', 'verdict_U20_9', 'verdict_U14_6', 'verdict_alt04_U20_9', 'region_source']
print('빠진 열', [c for c in cols if c not in R[0]], '/ 행', len(R), '/ 시편', sorted({r['specimen'] for r in R}))
print('참 판정 값 밖', [(r['scenario'], r['specimen']) for r in R if r['truth_judgement'] not in ('pass', 'fail')])
print('참 판정 규칙 위반', [(r['scenario'], r['specimen']) for r in R if (float(r['truth_pass_pct']) >= 95) != (r['truth_judgement'] == 'pass')])
J = lambda r: (r['step_gauge'] == 'off' and r['observable'] in ('yes', 'partial')) or (r['step_gauge'] == 'on' and r['observable'] == 'step_gauge_only')
E = {'pass': 'pass', 'borderline': 'hold', 'fail': 'fail'}
print('의도 불일치', [(r['scenario'], r['specimen'], r['verdict_U20_9']) for r in R if J(r) and r['verdict_U20_9'] != E[r['intent']]])
print('P 여유 < 98', [(r['scenario'], r['specimen']) for r in R if J(r) and r['intent'] == 'pass' and float(r['seen_pass_pct']) < 98])
print('F 여유 < 10', [(r['scenario'], r['specimen']) for r in R if J(r) and r['intent'] == 'fail' and float(r['seen_fail_pct']) < 10])
print('경계 행 참 판정 (시편별)', dict(collections.Counter((r['specimen'], r['truth_judgement']) for r in R if J(r) and r['intent'] == 'borderline')))
print('C12 위험 행 (보이는 pass · 참 fail)', [(r['scenario'], r['specimen'], r['step_gauge']) for r in R if r['verdict_U20_9'] == 'pass' and r['truth_judgement'] == 'fail'])
print('합 100 위반', [(r['scenario'], r['specimen']) for r in R if abs(sum(float(r[k]) for k in ['seen_pass_pct', 'seen_hold_pct', 'seen_fail_pct']) - 100) > 1e-6])
EOF
```

⑤ 시나리오 문서 구조

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import re
t = open('docs/판정-시나리오.md', encoding='utf-8').read()
print('첫 줄 열람 금지', '열람 금지' in t.splitlines()[0])
print('절 누락', [h for h in map(str, range(11)) if not re.search(r'^## %s\. ' % h, t, re.M)])
for k in ['A19', 'D-08', 'D-14', 'D-15', 'D-16', 'R7', 'C12', 'step_gauge_only', 'stand-in-v1', 'T5-2', '시험용 가정', '하드웨어 성능의 증거가 아닙니다']:
    print(k, k in t)
print('근거 태그 수', len(re.findall(r'\[(계산|추정|미상|출처|확인 필요)', t)))
EOF
```

⑥ 정보 차단 · 슬라이서 실행 없음

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && grep -n -E "cvlab\.(io|sim|region|triangulation|config|repro)|_truth|subprocess|os\.system|Popen|slicer.*\.exe|orca-slicer|bambu-studio|prusa-slicer" scripts/gcode_check.py scripts/scenario_expected.py; echo "grep exit=$? (1이면 0건)"; git status --porcelain src/cvlab/gcode src/cvlab/judge data/gcode_samples config/gcode.yaml config/judge.yaml | grep -v __pycache__; echo "완료 패키지 · 샘플 변경 줄 수 (0이어야 함): $(git status --porcelain src/cvlab/gcode src/cvlab/judge data/gcode_samples config/gcode.yaml config/judge.yaml | grep -v __pycache__ | wc -l)"; echo "T5가 만든 src 파일 (없어야 함): $(git status --porcelain -uall src | grep -v __pycache__ | grep -v -E 'src/cvlab/(region|triangulation|io)/' | wc -l)"
```

⑦ 소유 검사 (세 작업 공통, T4b · T7a 세부청사진과 같은 명령)

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

판정: ① `CHECK` 2줄 (사용자 G코드가 오면 3줄), 오류 없음, `SCEN`의 `mismatches` 빈 목록, 시간 ≤ 15분. ② 절 누락 빈 목록, 점검표 행 ≥ 24, 빈 칸 행 · 빈 CSV 행 빈 목록, 키워드 모두 True. ③ 열람 금지 표시 3곳 True, 빠짐 · 위반 · 불일치 모두 빈 목록, NOM-P00 True, 시나리오 ≥ 19. ④ 빠진 열 · 값 밖 · 규칙 위반 · 의도 불일치 · 여유 부족 · 합 위반 빈 목록, 경계 행 참 pass · fail 각 ≥ 2 (시편마다), C12 위험 행은 `z_scale` · off 행만. ⑤ 절 누락 빈 목록, 키워드 모두 True. ⑥ grep exit=1, 변경 줄 0. ⑦ 위반 빈 목록. ⑧ 시작 값과 같음.

### 8.2 팀장 검사

- voron24 · caliper의 경계 상자 · 패스 수 (0° · 90° · extend) · 층당 시간을 팀장이 따로 계산해 `CHECK` 값과 대조합니다 (팀장 사전 계산값은 점검일지에 적음). T4b `REGION`의 `passes`와도 대조합니다.
- 점검표에서 G코드 줄 번호를 인용한 칸 3개를 골라 원문 줄을 직접 엽니다 (3/3).
- plate20의 `z_offset` 행을 팀장이 손으로 판정합니다: dz ≤ 179.1 µm → pass, ≤ 220.9 µm → hold, 그 위 fail (U 20.9 µm, T = 200 µm [계산: T ∓ U]), 참 판정은 dz ≤ 200 µm → pass. CSV의 `verdict_U20_9` · `truth_judgement`와 대조합니다.
- `z_scale`의 Δ_seen 유도를 명세 0.4 높이 식으로 다시 따라가 봅니다. "Z축 오차는 베드 기준 스캔으로 빠지지 않는 몫이 Z에 따라 남고, 측정은 그것을 못 본다"는 결론이 식과 맞는지 봅니다.
- CK8의 C1 판정 (LM-T14-2 블록 간격 5 mm · 한 블록만 스캔 vs 계단 두 개가 심도 안)을 팀장이 따로 판단해 맞춥니다. 어긋나면 T14 · T3로 넘길 지시안을 씁니다.
- 시나리오 파일 세 곳의 열람 금지 표시, 평가용 세트 (시드 · 배정)가 저장소에 없는지 봅니다.

## 9. 금지 사항

- 슬라이서를 실행하지 않습니다. G코드를 내려받지 않습니다. `data/gcode_candidates/`와 `data/gcode_samples/`를 고치지 않습니다 (plate20은 `docs/G코드-점검_자료/`에).
- 평가용 세트 (팀장만 시드를 아는 세트)를 만들지 않습니다. 시나리오 산출물을 처리 담당이 읽을 경로 (`src/` · `tests/` · 공개 문서)에 복사하지 않습니다. 공개 점검 문서에는 시나리오 내용을 쓰지 않습니다.
- `data/_truth/`와 `src/cvlab/sim/`을 읽지 않습니다. T4b 산출물을 읽지 않습니다. `cvlab.io` · `cvlab.config`를 import하지 않습니다.
- 본인 확정 (D-05 – D-08 · D-15 · D-16 · D-18 · D-20)을 바꾸지 않습니다. 판정 함수를 고쳐 쓰지 않고 T15 공개 함수만 부릅니다.
- 숫자를 지어내지 않습니다. 점검 값은 G코드 줄 번호 · `[계산]` · `[출처]` · `[추정]` · `[미상]` 중 하나를 붙입니다. 시나리오 강도는 "시험용 가정"으로 표시합니다.
- V2 미커밋 파일을 고치거나 되돌리지 않습니다. git 쓰기 명령을 쓰지 않습니다 (읽기만). `pip install` · 유료 API · Plane 수정을 하지 않습니다. 웹 검색은 10회 이하.
- §5 소유 표 밖의 파일을 만들거나 고치지 않습니다. E3 요소 청사진은 고치지 않습니다.
- 범위를 바꾸고 싶으면 (예: 보조 시편 G코드를 직접 만들기) 멈추고 팀장에게 보고합니다.

## 10. 시작 확인 항목

`docs/운영/결과_T5_대조표.md`를 만들고 "시작 확인" 절에 적은 뒤 시작합니다. (대조표는 공개 경로라 시나리오 내용은 "SC 항목 완료 여부"만 적고 강도 · 식은 적지 않습니다.)

- [ ] 브랜치 · HEAD, `git status --short` 기준선, 명령 ⑧ 출력 (V2 지문)
- [ ] 명세 상태: `sha256sum docs/하드웨어-데이터-명세.md`, 줄 수, 수정 시각, `git diff --stat HEAD -- docs/하드웨어-데이터-명세.md` (끝날 때 다시 재서 비교). 부록 A `truth.judgement` 값이 지금 pass · fail · borderline인지 pass · fail인지 적기
- [ ] 목표 CK1 – CK10 · SC1 – SC12를 자기 말로 한 줄씩
- [ ] §3 입력 파일이 모두 있는지. `_local/` 두 파일 지문 = MANIFEST
- [ ] 사용자 G코드 상태 (메인에게 확인: 대기 · 경로)
- [ ] Python · numpy · pandas · PyYAML 판
- [ ] §5 소유 표를 읽었고 T4b · T7a 경로를 건드리지 않으며 T4b 산출물을 읽지 않는다는 확인. 이 작업 뒤 처리 작업 (T4b · T7–T12)을 맡지 않는다는 확인
- [ ] 마감: 10-31 (T5-2는 T4b 뒤 11-03)

## 11. 종료 대조표 양식

```markdown
## 종료 대조 (2026-10-31 HH:MM)

| 목표 항목 | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| CK1 대상 · 지문 | 2파일 지문 같음, plate20 생성 | 명령 ① | |
| CK2 점검표 | n줄 × m파일, 빈칸 0 | 명령 ② | |
| CK3 크기 · 패스 | voron24 a × b (90° c × d), caliper … | 명령 ① | |
| CK4 층 · 심도 · 0점 | caliper 심도 층 n (41), 권장 zero_ref_method | 명령 ① | |
| CK5 스캔 시간 | 층당 s, 전체 분 (식 ① · ②) | 명령 ① · 문서 §3 | |
| CK6 방언 | 못 쓰는 명령 n종 | 문서 §5 | |
| CK7 다시 슬라이스 | voron24 예/아니오, caliper 예/아니오, 항목 n | 문서 §6 | |
| CK8 기준물 배치 | C1 판정, C2 겹침 없음/있음 | 문서 §7 | |
| CK9 보조 시편 | 필요/불필요, 이유 | 문서 §8 | |
| CK10 점검 문서 | 절 0–9 | 명령 ② | |
| SC1 참 판정 규칙 | pass · fail, ≥ 95 | 명령 ④ | |
| SC2 종류 사전 | n종, observable 분포 | 명령 ③ | |
| SC3 시나리오 | n개 (P a · B b · F c) | 명령 ③ | |
| SC4 주입 형식 | 키 고정, print_error_params 꼴 | 명령 ③ | |
| SC5 기대 판정 | 시편 3 × n행, t분 | 명령 ① · ④ | |
| SC6 의도 일치 | 불일치 0, 여유 부족 0 | 명령 ④ | |
| SC7 경계 행 | 시편별 참 pass a · fail b | 명령 ④ | |
| SC8 보이지 않는 오차 | z_scale off pass · 참 fail, on fail | 명령 ④ | |
| SC9 희석 | 시편별 넓이 표 | 문서 §7 | |
| SC10 블라인드 | 표시 3곳, 평가 세트 없음 | 명령 ③ | |
| SC11 시나리오 문서 | 절 0–10 | 명령 ⑤ | |
| SC12 스크립트 · 차단 | 오류 0, grep 0, 소유 위반 0, V2 지문 같음 | 명령 ① · ⑥ · ⑦ · ⑧ | |

명세 시작 · 끝 지문: (같음 / 바뀜 + 영향 필드)
검증 명령 실행 결과: (①–⑧ 출력. ③ · ④ 출력은 대조표에 붙이지 말고 "통과/위반 n건"만. 시나리오 내용이 공개 경로에 남지 않게)
남은 문제: (없으면 "없음")
```
