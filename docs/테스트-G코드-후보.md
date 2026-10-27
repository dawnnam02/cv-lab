# 테스트 G코드 후보

> 작성: 2026-10-27 기준모델 worker · 대조표: [결과_G코드후보_대조표](운영/결과_G코드후보_대조표.md)
> 사용자 지시: "테스트할 만한 G코드를 몇 개 받아와서 보고하면, 내가 보고 어떤 G코드로 테스트를 돌릴지 결정할게."
> 최종 선택은 사용자가 함. 이 문서는 고를 재료만 정리함.

## 0. 요약

- 내려받은 .gcode 7개: `data/gcode_candidates/<후보이름>/` (원본 파일 이름 그대로)
- 슬라이서: OrcaSlicer 5개 · PrusaSlicer 1개 · Cura 1개
- 방언: Klipper 4개 (그중 Voron 프로필 2개) · Marlin 3개 (Prusa MK3S · Ender-3 V2 · JGMaker R1)
- 모든 수치는 파일을 직접 파싱해 얻음 (스크립트: 스크래치패드 `gcode_cand/parse_gcode.py`, `zlist.py`)
- 추천: 1위 `voron24_test_box` · 2위 `caliper_pyramid` · 3위 `voron_design_cube` (6절)

## 1. 후보 한눈에

| 이름 | 형상 | 슬라이서 · 방언 | 층 수 · 최대 Z | 물체 XY (mm) | 측정 적합성 한 줄 |
|---|---|---|---|---|---|
| `voron24_test_box` | 25 mm 사각 판 (두께 3.2) | Orca 2.4.2 · Klipper (Voron 2.4 프로필) | 16 · 3.2 | 24.6 × 24.6 | 평탄 92 %, 스캔 2회, 272초. 첫 파이프라인 시험에 가장 쉬움 |
| `caliper_pyramid` | 계단 블록 + 낮은 틀 (2부품) | PrusaSlicer 2.5.0 · Marlin (Prusa MK3S+) | 64 · 22.25 | 20.6 × 41.8 | 0.35 mm 계단이 허용오차 0.2 mm 근처라 경계 시험에 좋음. 홈 깊이 15 mm는 심도 초과 |
| `voron_design_cube` | 30 mm 큐브, 가운데 원형 구멍·로고 | Orca 2.2.0 · Klipper (Voron Microwave 프로필) | 150 · 30.0 | 29.6 × 29.6 | Voron 실사용 출력. 스캔 2회, 150층이라 스캔만 85분 |
| `xyz_cube_10mm` | 10 mm 보정 큐브 (윗면 X 음각) | Orca 2.3.1 · Klipper (Flashforge AD5M Pro) | 50 · 10.0 | 9.6 × 9.6 | 스캔 1회. 면적 100 mm²로 작아 측정점이 적음 |
| `simple_cura` | 지름 약 20 mm 원형 테 + 살 + 가운데 기둥 | Cura 5.3.1 · Marlin (Ender-3 V2) | 18 · 5.04 | 19.6 × 19.6 | Marlin·`;LAYER:`·절대 E 방언 비교용. 곡선 경계, 높이 8 mm 미만 |
| `benchy_helix` | 3DBenchy (곡면·경사·돌출) | Orca 2.3.1 · Klipper (Flashforge AD5M Pro) | 240 · 48.0 | 59.6 × 30.6 | 스트레스 시험용. 스캔 3회, 스캔만 204분, 평탄 31 % |
| `orca_calib_cube` | 20 mm 보정 큐브 (XYZ 글자) | Orca 2.2.0-rc · Marlin (JGMaker R1) | 37 (헤더는 100) · 20.0 | 19.6 × 19.6 | **중간 층이 잘린 시험용 파일** (Z 5.6 → 18.4 건너뜀). 해석기 오류 감지 시험에만 |

- 층 수 = 물체 압출이 1 mm 넘게 있는 Z 값 개수. 스커트·브림·시작 퍼지선은 뺌.
- 물체 XY = 같은 기준의 압출 범위.

## 2. 출처와 라이선스

| 이름 | 파일 (원본 이름) | 출처 URL | 라이선스 |
|---|---|---|---|
| `voron24_test_box` | `test_box_25mm_PLA_3m17s.gcode` | https://github.com/JerrettDavis/Voron24-Klipper/blob/main/docs/orca-profile/test_box_25mm_PLA_3m17s.gcode | [미상] 저장소에 LICENSE 없음 |
| `caliper_pyramid` | `caliper pyramid test.prusaproject_0.6n_0.35mm_PLA_MK3SMMU2S_16m.gcode` | https://github.com/pvillano/OpenSCAD-is-not-a-fad/blob/main/001%20completed/caliper_pyramid/caliper%20pyramid%20test.prusaproject_0.6n_0.35mm_PLA_MK3SMMU2S_16m.gcode | [미상] 저장소에 LICENSE 없음 |
| `voron_design_cube` | `Voron_Design_Cube_v7_PLA-F_20m58s.gcode` | https://github.com/Xiar1/Voron/blob/main/VORON%20BACKUPS/Microwave%202.0/printer_data/gcodes/Voron_Design_Cube_v7_PLA-F_20m58s.gcode | [미상] 저장소에 LICENSE 없음. 모델은 Voron Design 큐브 (모델 라이선스 확인 안 함) |
| `xyz_cube_10mm` | `xyz-10mm-calibration-cube.gcode` | https://github.com/prestonbrown/helixscreen/blob/main/assets/test_gcodes/xyz-10mm-calibration-cube.gcode | 저장소 GPL-3.0. 모델 자체 라이선스 [미상] |
| `simple_cura` | `SimpleCuraTest.gcode` | https://github.com/prestonbrown/helixscreen/blob/main/assets/test_gcodes/SimpleCuraTest.gcode | 저장소 GPL-3.0. 모델 [미상] |
| `benchy_helix` | `3DBenchy.gcode` | https://github.com/prestonbrown/helixscreen/blob/main/assets/test_gcodes/3DBenchy.gcode | 저장소 GPL-3.0. 3DBenchy 모델 자체 라이선스는 이번에 확인 안 함 [미상] |
| `orca_calib_cube` | `orcaslicer-2.2.0-rc-calibration-cube.gcode` | https://github.com/HoffmanEngineering/Slic3rPostProcessingUploader/blob/main/PrintLog.SlicerSettings.Tests/TestData/OrcaSlicer/orcaslicer-2.2.0-rc-calibration-cube.gcode | 저장소 MIT. 모델 [미상] |

- LICENSE 없는 저장소 파일은 내부 시험용으로만 쓰고, 저장소에 다시 올리거나 배포하지 않는 편이 안전함.
- `data/gcode_candidates/`는 커밋하지 않았음 (git 쓰기 금지 범위).

## 3. 파싱 결과

### 3.1 슬라이서 · 프로필 · 방언

| 이름 | 슬라이서 · 버전 | 대상 프린터 프로필 | flavor | 매크로·방언 단서 | 층 변경 표시 | E 모드 |
|---|---|---|---|---|---|---|
| `voron24_test_box` | OrcaSlicer 2.4.2 | Voron 2.4r2 350 0.4 nozzle | klipper | `START_PRINT` · `END_PRINT` · `SET_PRINT_STATS_INFO` 16 · `EXCLUDE_OBJECT_*` · `SET_VELOCITY_LIMIT` · `G10/G11` (펌웨어 리트랙션) | `;LAYER_CHANGE` 32 · `;Z:` 32 · `SET_PRINT_STATS_INFO` 16 | 상대 (`M83`) |
| `caliper_pyramid` | PrusaSlicer 2.5.0+win64 | Prusa MK3S+ MMU2S 0.6 nozzle | marlin | `M862.3`·`M862.1` (Prusa 기종 확인) · `M115 U3.11.0` · `G80` (메시) · `M900` · `M73` | `;LAYER_CHANGE` 64 · `;Z:` 64 · `;AFTER_LAYER_CHANGE` 64 | 상대 (`M83`) |
| `voron_design_cube` | OrcaSlicer 2.2.0 | Voron Microwave 0.4 nozzle (베드 250 × 245) | klipper | `PRINT_START` · `PRINT_END` · `EXCLUDE_OBJECT_*` · `SET_PRESSURE_ADVANCE` · `SET_VELOCITY_LIMIT` | `;LAYER_CHANGE` 150 · `;Z:` 150 · `;AFTER_LAYER_CHANGE` 150 | 상대 (`M83`) |
| `xyz_cube_10mm` | OrcaSlicer 2.3.1 | Flashforge Adventurer 5M Pro 0.4 Nozzle | klipper | `START_PRINT` · `END_PRINT` · `SET_PRINT_STATS_INFO` 51 · `TIMELAPSE_TAKE_FRAME` 50 · `EXCLUDE_OBJECT_*` · `M117` | `;LAYER_CHANGE` 50 · `;Z:` 50 · `;AFTER_LAYER_CHANGE` 50 · `SET_PRINT_STATS_INFO` 51 | 상대 (`M83`) |
| `simple_cura` | Cura_SteamEngine 5.3.1 | Creality Ender-3 V2 (definition `creality_ender3`) | Marlin (`;FLAVOR:Marlin`) | `M420 S1` (메시 켜기) · `G10/G11` 59/58 · `M117` · `M73` · 시작 퍼지선 X0.1 Y20→200 | `;LAYER:` 18 (+ `;LAYER_COUNT:18`) | 절대 (`M82`) |
| `benchy_helix` | OrcaSlicer 2.3.1 | Flashforge Adventurer 5M Pro 0.4 Nozzle | klipper | `xyz_cube_10mm`과 같은 매크로 · `G3` 279개 (나선 Z홉, 압출 없음) | `;LAYER_CHANGE` 240 · `;Z:` 240 · `;AFTER_LAYER_CHANGE` 240 · `SET_PRINT_STATS_INFO` 241 | 상대 (`M83`) |
| `orca_calib_cube` | OrcaSlicer 2.2.0-rc | JGMaker R1 (Generic Marlin Printer) | marlin | `M204` · `M73`. 매크로 없음 | `;LAYER_CHANGE` 36 · `;Z:` 36 · `;AFTER_LAYER_CHANGE` 36 | 상대 (`M83`) |

### 3.2 형상 · 재료 · 크기

| 이름 | 층 높이 (첫 층) | 층 수 | 최대 Z | 물체 XY 범위 (mm) | 노즐 | 압출 폭 | 재료 | 파일 크기 | 예상 시간 (주석) |
|---|---|---|---|---|---|---|---|---|---|
| `voron24_test_box` | 0.2 (0.2) | 16 | 3.2 | X 162.7–187.3 · Y 162.7–187.3 | 0.4 | 0.4 | PLA | 109,477 B | 3m 17s |
| `caliper_pyramid` | 0.35 (0.2) | 64 | 22.25 | X 114.71–135.29 · Y 84.21–125.98 | 0.6 | 0.65 (외벽 0.68) | PLA | 274,433 B | 15m 48s |
| `voron_design_cube` | 0.2 (0.2) | 150 | 30.0 | X 110.2–139.8 · Y 107.7–137.3 | 0.4 | 0.4 | PLA-F (Likesilk) | 2,242,417 B | 20m 58s |
| `xyz_cube_10mm` | 0.2 (0.2) | 50 | 10.0 | X −4.79–4.79 · Y −4.79–4.79 (원점 중심 베드) | 0.4 | 0.42 (내벽 0.45) | PLA | 160,642 B | 5m 23s |
| `simple_cura` | 0.28 (0.28) | 18 | 5.04 | X 105.22–124.78 · Y 105.21–124.79 | [미상] 파일에 없음 | [미상] 파일에 없음 | [미상] 재료 이름 없음 (노즐 195/200 °C) | 240,251 B | 7m (`;TIME:420`) |
| `benchy_helix` | 0.2 (0.2) | 240 | 48.0 | X −29.79–29.79 · Y −15.29–15.29 (원점 중심 베드) | 0.4 | 0.42 (내벽 0.45) | PLA | 2,943,775 B | 36m 25s |
| `orca_calib_cube` | 0.2 (0.2) | 37 (헤더 100) | 20.0 | X 105.2–124.8 · Y 105.2–124.8 | 0.4 | 0.4 | PLA | 191,977 B | 21m 59s (잘리기 전 기준) |

### 3.3 파싱하다 발견한 함정 (해석기 시험에 쓸 만함)

| 이름 | 발견 | 해석기에 주는 뜻 |
|---|---|---|
| `voron24_test_box` | 헤더 `total layer number: 32`, `;LAYER_CHANGE` 32회인데 실제 Z는 16개. 사용자 층 변경 G코드에도 `;LAYER_CHANGE`를 넣어 표시가 두 번씩 나옴 | 층 수는 표시 개수 말고 Z 값으로 세야 함 |
| `orca_calib_cube` | Z 5.6 다음이 18.4. 헤더는 100층·20 mm | 층 누락 감지 시험 재료. 정답 지도용으로는 부적합 |
| `simple_cura` | 헤더 `;MINX/MAXX` 94.4–135.6은 스커트 포함 범위. 시작 퍼지선이 `;TYPE` 없이 압출됨 | `;TYPE:` 기준으로 물체만 골라야 함 |
| `caliper_pyramid` | 전체 압출 범위 X 0–240 · Y −3–131.9 (프라임·퍼지 포함). `;TYPE:Custom`·`Skirt/Brim` 빼면 물체만 남음 | 같은 처리 필요 |
| `benchy_helix` · `xyz_cube_10mm` | `G3 Z.. I.. J.. P1` 나선 Z홉. 압출 없음 | G2/G3을 무시하면 안 되고 Z 변화만이라도 반영해야 함 |
| `xyz_cube_10mm` · `benchy_helix` | 베드 원점이 가운데 (−110~110) | 좌표계 원점이 프로필마다 다름 |

## 4. 측정 적합성

기준: 시야 20 mm (스캔 폭) · 스캔 길이 40 mm · 심도 8 mm · 한 번 스캔 약 17초.
분할 수 = 물체 XY를 20 × 40 직사각형으로 덮는 최소 개수 (두 방향 중 적은 쪽).

| 이름 | 분할 수 | 평탄 비율 | 최대 Z > 8 mm | 최종 윗면 높이차 | 스캔 시간 (층 × 17 s) | 분할 반영 | 판정 시험 적합도 |
|---|---|---|---|---|---|---|---|
| `voron24_test_box` | 2 (24.6 > 20) | 0.92 | 아니오 (3.2) | 0 (한 높이) | 272 s (4.5분) | 544 s (9.1분) | 상. 정답이 평면이라 합격·불합격 결함을 넣고 빼기 쉬움 |
| `caliper_pyramid` | 3 (Y 41.8). 계단 블록만이면 1 | 0.07 | 예 (22.25) | 0.2 → 22.25. 블록 안에서 홈 6.85 ↔ 꼭대기 22.25 = 15.4 mm | 1,088 s (18.1분) | 3,264 s (54.4분) | 상. 0.35 mm 계단 1단을 빼거나 더하면 경계·불합격 시나리오가 됨. 단, 홈 바닥은 심도 밖 |
| `voron_design_cube` | 2 (29.6) | 0.72 | 예 (30.0) | 14.4 → 30.0 = 15.6 mm (구멍 바닥 ↔ 윗면) | 2,550 s (42.5분) | 5,100 s (85분) | 중. 윗면이 넓고 평평해 좋지만 구멍 바닥은 심도 밖, 시간 김 |
| `xyz_cube_10mm` | 1 | 0.56 | 예 (10.0) | 9.0 ↔ 10.0 = 1.0 mm (X 음각) | 850 s (14.2분) | 850 s | 중. 1회 스캔이 장점. 면적 100 mm²라 95 % 비율이 몇 점에 좌우됨 |
| `simple_cura` | 1 | 0.42 | 아니오 (5.04) | 2.24 → 5.04 = 2.8 mm | 306 s (5.1분) | 306 s | 중. 곡선 경계와 낮은 살로 경계 시나리오 가능. Marlin 방언 비교용으로 가치 큼 |
| `benchy_helix` | 3 | 0.31 | 예 (48.0) | 6.6 → 48.0 = 41.4 mm | 4,080 s (68분) | 12,240 s (204분) | 하. 곡면이 많아 정답 자체가 복잡. 해석기·시뮬레이터 부하 시험용 |
| `orca_calib_cube` | 1 | 0.76 | 예 (20.0) | 0.6 → 20.0 (잘린 파일이라 의미 약함) | 629 s | 629 s | 하. 층이 잘려 정답 지도로 못 씀 |

- 평탄 비율: 위에서 본 높이 지도를 0.5 mm 칸으로 만들고, 둘레 3 × 3 칸이 모두 같은 층 높이인 칸의 비율. 선을 칸에 찍는 근사라 실제보다 조금 낮게 나옴 [근사].
- 최종 윗면 높이차: 다 쌓은 뒤 위에서 보이는 물체 표면의 최저~최고. 층마다 스캔하면 대부분 층에서는 이보다 작음. 8 mm를 넘으면 마지막 층들에서 깊은 곳이 심도 밖으로 나감.
- 스캔 시간은 출력 시간에 더해지는 몫.

## 5. 슬라이스 필요 후보 (STL·SCAD만, 받지 않음)

| 이름 | 형상 | 출처 URL | 라이선스 | 메모 |
|---|---|---|---|---|
| 5mm Calibration Steps | 5 mm 단차 계단 [이름으로 추정] | https://github.com/paulhayes/CADModels/blob/master/TestObjects/5mm_Calibration_Steps.stl | [미상] 저장소에 LICENSE 없음 | Git LFS 파일. 크기·형상 직접 확인 못 함 |
| SteppingXY | XY 계단 보정 시편 [이름으로 추정] | https://github.com/openbikesensor/OpenBikeSensor3dPrintableCase/blob/main/export/Calibration/SteppingXY.stl | 저장소 LGPL-3.0 | 형상 직접 확인 못 함 |
| caliper pyramid (원본) | 2위 후보의 원본 모델 | https://github.com/pvillano/OpenSCAD-is-not-a-fad/tree/main/001%20completed/caliper_pyramid | [미상] | `caliper pyramid.scad` · `main part.stl` · `insert.stl` 있음. Trident Klipper 프로필로 다시 슬라이스하면 2위의 방언 문제가 풀림 |

## 6. 추천 (결정은 사용자)

| 순위 | 후보 | 이유 한 줄 |
|---|---|---|
| 1 | `voron24_test_box` | Voron·Klipper 프로필 그대로이고, 16층·평탄 92 %라 정답 지도가 단순해 파이프라인 첫 시험과 결함 주입이 가장 쉬움 |
| 2 | `caliper_pyramid` | 0.35 mm 계단이 허용오차 0.2 mm와 맞붙어 합격·경계·불합격을 한 시편에서 만들 수 있음 (Marlin이라 방언 비교도 겸함, Trident용은 원본 STL 재슬라이스) |
| 3 | `voron_design_cube` | 실제 Voron 사용자 출력으로 넓은 평면 + 구멍 + 150층이라 분할 스캔·심도 초과·장시간 조건을 함께 시험 |

- 덧붙임: Marlin 방언 처리만 따로 보려면 `simple_cura` (Cura·`;LAYER:`·절대 E)가 가장 작고 빠름.

## 7. 받지 못한 것

| 대상 | 이유 |
|---|---|
| gcode-thumb 저장소의 Cura·Orca 3DBenchy 9종 (MIT) | Git LFS 포인터 (132 B)만 있어 실제 G코드가 아님 |
| pyGCodeDecode 예제 `benchy.gcode` 등 (MIT) | Git LFS 포인터 |
| helixscreen `Night Spirit_v1_2_og.gcode` (45.5 MB) · `vaso_voronoi_V2_abajo.gcode` (36.4 MB) | 30 MB 초과 규칙 |
| Voron 공식 저장소의 Design Cube STL | Voron-Trident 저장소 트리에서 찾지 못함. 대신 사용자 출력 G코드 (3위)를 받음 |
| Prusa·Printables 공식 페이지 G코드 | 조사 횟수 한도 안에서 GitHub에 있는 실제 출력 파일을 우선함 |
