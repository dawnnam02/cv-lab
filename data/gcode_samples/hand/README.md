# 손 G코드 (T4a 시험용 입력)

- 모든 값은 **시험용 입력**이며 출력물 설계가 아님. 기대값은 손계산이고 식은 `기대값.csv`의 `근거식` 열에 있음.
- 이름에 `_mimic`이 붙은 파일은 슬라이서 형식을 흉내 낸 것으로 **실제 슬라이서 출력 아님**.
- E 값: E = bead_area(w, h)·L / A_f, A_f = π·(1.75/2)², 소수 다섯째 자리 반올림.
- 후보 G코드의 함정을 옮긴 파일: H22 (voron24_test_box 겹친 층 표시), H23 (simple_cura 퍼지선), H24 (benchy·xyz 나선 Z홉·가운데 원점).

| 파일 | 내용 (첫 줄 주석) |
|---|---|
| `H01_square.gcode` | H01 10 mm 정사각형 둘레 (시험용 입력) |
| `H02_relative.gcode` | H02 G91 상대 XYZ + M83 상대 E (시험용 입력) |
| `H03_g92_absE.gcode` | H03 M82 절대 E + G92 E0 반복 (시험용 입력) |
| `H04_inch.gcode` | H04 G20 인치 (시험용 입력) |
| `H05_arcs.gcode` | H05 사분원 두 개: G3 I·J, G2 R (r = 10, 시험용 입력) |
| `H06_fullcircle.gcode` | H06 G2 전체 원 I만 (r = 5, 시험용 입력) |
| `H07_retract_wipe.gcode` | H07 리트랙트·되밀기·와이프 (시험용 입력) |
| `H08_fw_retract.gcode` | H08 펌웨어 리트랙트 G10·G11 (시험용 입력) |
| `H09_checksum.gcode` | H09 N + * 체크섬, N8 줄만 틀림 (시험용 입력) |
| `H10_zhop.gcode` | H10 주석 없는 2층 + 층 사이 Z hop 0.4 mm (시험용 입력) |
| `H11_variable.gcode` | H11 가변 층 Z 0.20 · 0.35 · 0.45 (시험용 입력) |
| `H12_prusa_mimic.gcode` | H12_mimic PrusaSlicer 꼴 흉내 (실제 슬라이서 출력 아님, 시험용 입력) |
| `H13_cura_mimic.gcode` | H13_mimic Cura 꼴 흉내 (실제 슬라이서 출력 아님, 시험용 입력) |
| `H14_bambu_mimic.gcode` | H14_mimic Orca·Bambu 꼴 흉내 (실제 슬라이서 출력 아님, 시험용 입력) |
| `H15_klipper_mimic.gcode` | H15_mimic Klipper 꼴 흉내 (실제 슬라이서 출력 아님, 시험용 입력) |
| `H16_unknown_cmd.gcode` | H16 첫 압출 뒤 모르는 명령 (시험용 입력) |
| `H17_sequential.gcode` | H17 순차 출력: 두 번째 물체에서 Z가 내려감 (시험용 입력) |
| `H18_helix.gcode` | H18 나선: 압출하면서 Z가 계속 오름 (시험용 입력) |
| `H19_crlf_lower.gcode` | H19 CRLF, 소문자, 붙여 쓴 단어, 주석 안 E (시험용 입력) |
| `H20_block.gcode` | H20 10 × 10 mm 블록 2층, 선폭 0.42 간격 채움 (시험용 입력) |
| `H21_lshape.gcode` | H21 L자 2층 (긴 다리 +X 10 mm, 짧은 다리 +Y 5 mm, 시험용 입력) |
| `H22_double_marker_mimic.gcode` | H22_mimic Orca 꼴: 층 표시가 두 번씩 (실제 슬라이서 출력 아님, 시험용 입력) |
| `H23_cura_purge_mimic.gcode` | H23_mimic Cura 꼴: ;TYPE 없는 시작 퍼지선 (실제 슬라이서 출력 아님, 시험용 입력) |
| `H24_helix_hop_mimic.gcode` | H24_mimic Orca 꼴: 압출 없는 G3 나선 Z홉, 베드 원점 가운데 (실제 슬라이서 출력 아님, 시험용 입력) |
