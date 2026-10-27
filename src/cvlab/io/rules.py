"""규칙표 만들기 (세부청사진 T6 §6.2).

- 자동 규칙: 필드표에서 뽑은 값으로 REQ · DTYPE · REGEX · ENUM · RANGE를 만든다.
- 손 규칙: 자동으로 못 옮긴 "검증 규칙" 문장을 CROSS · FILE · CSV · JSON · LEAK · WARN 규칙이나 보류로 잇는다.
- 설명문: 검사할 내용이 없는 문장 (예시·근거·기본값 설명)은 NOTES에 사유와 함께 둔다.

`uncovered_sentences()`가 빈 목록이어야 SV5 "미분류 0"이다.
"""

from __future__ import annotations

import re

from cvlab.io.spec_schema import split_sentences

RULE_COLUMNS = [
    "rule_id", "kind", "fields", "severity", "status", "condition", "params",
    "message", "reason", "covers",
]

# ---------------------------------------------------------------------------
# 조건부 필드의 조건 (명세 "검증 규칙" 칸 원문). validate.COND_FUNCS가 같은 키로 구현한다.
# 값: (조건 원문, 조건이 거짓이면 빈 칸이어야 하는지)
#   명세 §0.1: "조건부 = 검증 규칙 칸에 적은 조건일 때 필수, 아니면 빈 칸"
# ---------------------------------------------------------------------------
CONDITIONS: dict[str, tuple[str, bool]] = {
    "frame.file": ("meta.raw_saved = true", True),
    "frame.sha256": ("frame.file이 있으면", True),
    "frame.t_cam_ns": ("카메라가 시각을 줌 (파일 안 한 행이라도 값이 있으면 모든 행)", False),
    "frame.cam_seq": ("카메라가 줌 (파일 안 한 행이라도 값이 있으면 모든 행)", False),
    "frame.trig_pulse_idx": ("frame.trigger_mode = hw이고 frame.laser_on = true", True),
    "frame.gate_on": ("frame.trigger_mode = gate", True),
    "pos.mesh_dz_mm": ("meta.mesh_enabled = true", True),
    "pos.clock_offset_ns": ("pos.clock = mcu", True),
    "cal.target_rows": ("cal.target_type = charuco", True),
    "cal.target_cols": ("cal.target_type = charuco", True),
    "cal.target_square_mm": ("cal.target_type = charuco", True),
    "cal.target_marker_mm": ("cal.target_type = charuco", True),
    "cal.target_dict": ("cal.target_type = charuco", True),
    "cal.target_flatness_um": ("cal.target_type ∈ {charuco, flat_plate}", True),
    "cal.image_file": ("cal.record_type = image", True),
    "cal.exposure_us": ("cal.image_file이 있으면", True),
    "cal.cmd_z_mm": ("cal.kind = D2", True),
    "cal.cmd_move_mm": ("cal.kind = D3", True),
    "cal.feature_id": ("cal.kind = D4", True),
    "cal.feature_x_mm": ("cal.kind = D4", True),
    "cal.feature_y_mm": ("cal.kind = D4", True),
    "cal.nozzle_touch_z_mm": ("cal.record_type = nozzle_touch", True),
    "cal.gauge_nominal_mm": ("cal.target_type = filler_gauge", True),
    "cal.gauge_measured_mm": ("cal.target_type = filler_gauge", True),
    "cal.gauge_u_um": ("cal.target_type = filler_gauge", True),
    "cal.gauge_block_id": ("cal.target_type ∈ {step_gauge, filler_gauge}", True),
    "cal.gauge_block_height_mm": ("cal.target_type = step_gauge", True),
    "cal.gauge_block_u_um": ("cal.target_type = step_gauge", True),
    "cal.material_offset_um": ("cal.target_type = material_sample", True),
    "cal.material_offset_u_um": ("cal.target_type = material_sample", True),
    "cal.reproj_rms_px": ("cal_results.csv의 cal.kind = D1 행", True),
    "cal.plane_rms_um": ("cal_results.csv의 cal.kind = D2 행", True),
    "ref.scan_id": ("ref.kind ∈ {bed_marker, ref_tower, step_gauge}", True),
    "ref.layer_idx": ("ref.kind ∈ {bed_marker, ref_tower, step_gauge}", True),
    "ref.marker_id": ("ref.kind = bed_marker", True),
    "ref.marker_x_mm": ("ref.kind = bed_marker", True),
    "ref.marker_y_mm": ("ref.kind = bed_marker", True),
    # 명세에 "그 밖은 빈 칸"이 없고 다른 기준 (daily_ref 등)도 교정 ID를 적을 수 있어 빈 칸은 검사하지 않음
    "ref.calibration_id": ("ref.kind ∈ {bed_bare, bed_marker, ref_tower, step_gauge, feeler} (그 밖은 비어도 됨)", False),
    "ref.gauge_block_id": ("ref.kind ∈ {step_gauge, feeler}", True),
    "ref.gauge_height_mm": ("ref.kind ∈ {step_gauge, feeler}", True),
    "ref.gauge_temp_c": ("ref.kind = step_gauge (feeler면 선택: 검사 안 함)", True),
    "ref.line_peak_pct": ("ref.kind ∈ {daily_ref, static_repeat, bed_marker, ref_tower, step_gauge}", True),
    "meta.layer_time_s": ("meta.timing = layer", True),
    "meta.step_edge_angle_deg": ("meta.specimen_role = aux_step", True),
    "meta.camera_temp_c": ("meta.source = virtual (실측은 센서 유무를 몰라 선택)", False),
    "meta.bed_mesh_file": ("meta.mesh_enabled = true", True),
    "meta.paired_scan_id": ("meta.thermal_state = cooled", True),
    "meta.cool_wait_s": ("meta.thermal_state = cooled", True),
    "meta.sim_version": ("meta.source = virtual", True),
    "meta.sim_seed": ("meta.source = virtual", True),
    # frames_index.csv를 읽은 뒤 스캔 교차 검사에서 봄 (meta.json을 읽을 때는 모름)
    "meta.trigger_period_s": ("이 스캔의 frame.trigger_mode = hw", True),
    "rep.scan_id": ("design_executed.csv (실행 뒤)", True),
    "rep.noise_seed": ("가상 캠페인 (캠페인 ID 첫 글자 V)", True),
    "rep.truth_id": ("가상 캠페인 (캠페인 ID 첫 글자 V)", True),
}

# 필수지만 예외가 있는 필드
SPECIAL_REQ = {
    "meta.specimen_temp_c": "source = real이고 meta.notes에 'specimen_temp_c 없음:'이 있을 때만 null 허용",
}

NONEMPTY_PHRASES = ("빈 문자열 아님", "빈 문자열 허용 안 함")
ISO_RE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$"

# ---------------------------------------------------------------------------
# 손 규칙. (rule_id, kind, severity, status, fields, covers, message, reason)
# covers: "필드:문장 일부" 를 ';;'로 잇는다. 그 필드의 검증 규칙 문장 중 이 글자를 담은 문장을 이 규칙이 맡는다.
# ---------------------------------------------------------------------------
H = []


def _h(rid, kind, sev, status, fields, covers, message, reason=""):
    H.append((rid, kind, sev, status, fields, covers, message, reason))


# CSV · JSON 형식 (명세 §0.5)
_h("CSV-01", "CSV", "ERROR", "구현", "", "", "UTF-8 BOM이 있음 (명세 §0.5: BOM 없음)")
_h("CSV-02", "CSV", "ERROR", "구현", "", "", "줄 끝이 \\r\\n (명세 §0.5: \\n)")
_h("CSV-03", "CSV", "ERROR", "구현", "", "", "머리글 열 순서가 필드표 순서와 다르거나 열이 빠짐")
_h("CSV-04", "CSV", "ERROR", "구현", "", "", "필드표에 없는 열")
_h("CSV-05", "CSV", "ERROR", "구현", "", "", "결측을 NaN·nan·null·None·NA로 씀 (명세 §0.5: 빈 칸)")
_h("CSV-06", "CSV", "ERROR", "구현", "", "", "머리글에 묶음 접두어가 붙음 (명세 §0.1)")
_h("CSV-07", "CSV", "ERROR", "구현", "", "", "행의 칸 수가 머리글과 다름")
_h("CSV-08", "CSV", "ERROR", "구현", "", "", "UTF-8로 읽히지 않음")
_h("JSON-01", "JSON", "ERROR", "구현", "", "", "필드표에 없는 키")
_h("JSON-02", "JSON", "ERROR", "구현", "", "", "키에 묶음 접두어가 붙음 (명세 §0.1)")
_h("JSON-03", "JSON", "ERROR", "구현", "", "", "필드표의 키가 빠짐 (선택 필드도 null로 있어야 함, 명세 B.1-2)")
_h("JSON-04", "JSON", "ERROR", "구현", "", "", "JSON으로 읽히지 않음 (UTF-8·BOM·문법)")
_h("JSON-05", "JSON", "ERROR", "구현", "", "", "최상위가 JSON 객체가 아님")
# 읽는 데는 지장이 없는 표기 규칙이라 WARN (팀장검증_3차 S-2)
_h("JSON-06", "JSON", "WARN", "구현", "", "", "들여쓰기가 2칸이 아님 (명세 §0.5: 들여쓰기 2칸)")
_h("JSON-07", "JSON", "WARN", "구현", "", "", "ASCII 밖 글자를 \\uXXXX로 씀 (명세 §0.5: ensure_ascii=False)")
# H-FMT-01 (소수 4자리)은 SV13에서 뺌: 명세 §0.5가 "정밀도 규칙, 쓰는 쪽 규칙, 검증기가 검사하지 않음"으로 정함

# 정보 차단 (청사진 §5.2, 명세 §0.1)
_h("LEAK-01", "LEAK", "ERROR", "구현", "", "", "data/raw 아래 파일에 truth 키·열이 있음 (truth. · truth_ 로 시작)")
_h("LEAK-02", "LEAK", "ERROR", "구현", "", "", "data/raw 아래에 truth.json · _truth 폴더 · 참 높이맵 파일이 있음")

# 폴더·이름 (명세 §8)
_h("FILE-01", "FILE", "ERROR", "구현", "", "", "§8 폴더 트리에 없는 파일·폴더")
_h("FILE-02", "FILE", "ERROR", "구현", "", "", "폴더·파일 이름이 §8 이름 규칙 정규식과 맞지 않음")
_h("FILE-03", "FILE", "ERROR", "구현", "", "", "고정 파일이 없음 (스캔 폴더 meta.json·frames_index.csv·position_log.csv, 기준 폴더 ref_index.csv·frames_index.csv "
   "(+ 움직이며 찍는 기준 bed_bare·bed_marker·ref_tower·step_gauge·feeler는 position_log.csv), 교정 폴더 cal_manifest.csv, MSA 폴더 design.csv)")
_h("FILE-04", "FILE", "ERROR", "구현", "meta.timing;meta.scan_pass_idx", "meta.timing:시편·반복마다 post 스캔 (scan_pass_idx = 0)이 정확히 1개",
   "시편·반복 폴더에 post 스캔 (scan_pass_idx = 0)이 정확히 1개가 아님 (§8, D-06)")
_h("FILE-05", "FILE", "ERROR", "구현", "meta.session_id;meta.specimen_id;meta.repeat;meta.layer_idx;meta.timing;meta.scan_pass_idx",
   "meta.session_id:폴더 이름과 같음",
   "스캔 폴더 경로에서 뽑은 세션·시편·반복·층·줄 번호 (_pNN)가 meta 값과 다름 (§8 경로 일치)")
_h("FILE-06", "FILE", "ERROR", "구현", "frame.file", "frame.file:파일이 실제로 있음", "frame.file이 가리키는 영상이 없음")
_h("FILE-07", "FILE", "ERROR", "구현", "frame.sha256", "frame.sha256:다시 계산한 값과 같음", "frame.sha256이 영상 파일 지문과 다름")
_h("FILE-08", "FILE", "ERROR", "구현", "frame.roi_w_px;frame.roi_h_px",
   "frame.roi_w_px:영상 파일 폭과 같음;;frame.roi_h_px:영상 파일 높이와 같음", "영상 크기가 ROI 폭·높이와 다름")
_h("FILE-09", "FILE", "ERROR", "구현", "frame.bit_depth", "frame.bit_depth:8비트 그릇 PNG면 8;;frame.bit_depth:화소 최댓값",
   "PNG 그릇 비트와 bit_depth가 안 맞거나 화소 최댓값 > 2^bit_depth − 1")
_h("FILE-10", "FILE", "ERROR", "구현", "meta.files_sha256", "meta.files_sha256:불러올 때 다시 계산해 같아야 함",
   "meta.files_sha256의 파일 목록·지문이 스캔 폴더 실제 파일과 다름")
_h("FILE-11", "FILE", "ERROR", "구현", "cal.cal_id", "cal.cal_id:폴더 이름과 같음", "cal.cal_id가 교정 폴더 이름과 다름")
_h("FILE-12", "FILE", "ERROR", "구현", "cal.image_file", "cal.image_file:파일 있음", "cal.image_file이 가리키는 파일이 없음")
_h("FILE-13", "FILE", "ERROR", "구현", "ref.frames_dir", "ref.frames_dir:폴더 있음", "ref.frames_dir 폴더가 없음")
_h("FILE-14", "FILE", "ERROR", "구현", "meta.bed_mesh_file", "meta.bed_mesh_file:파일 있음", "meta.bed_mesh_file이 세션 폴더에 없음")
_h("FILE-15", "FILE", "ERROR", "구현", "meta.raw_saved", "meta.raw_saved:true면 frames/ 또는 frames.npz 있음;;meta.raw_saved:false면 영상 없음",
   "raw_saved = true인데 frames/·frames.npz가 없거나, false인데 영상이 있음")
_h("FILE-16", "FILE", "ERROR", "구현", "rep.study_id", "rep.study_id:폴더 이름과 같음", "rep.study_id가 MSA 폴더 이름과 다름")
# SV13 (T1 2차): 저장소 뿌리 기준 경로 (명세 0.1절). 저장소 뿌리를 모르면 (캠페인이 data/raw/ 아래가 아니고 --repo-root도 없음) 검사하지 않음
_h("FILE-17", "FILE", "ERROR", "구현", "meta.gcode_file", "meta.gcode_file:저장소 뿌리 기준으로 파일 있음",
   "meta.gcode_file이 저장소 뿌리 기준으로 없음 (명세 0.1절)")
_h("FILE-18", "FILE", "ERROR", "구현", "meta.slicer_profile_file", "meta.slicer_profile_file:저장소 뿌리 기준으로 파일 있음",
   "meta.slicer_profile_file이 저장소 뿌리 기준으로 없음 (명세 0.1절)")
_h("FILE-19", "FILE", "ERROR", "구현", "ref.ref_id", "ref.ref_id:기준 폴더 이름과 같음", "ref.ref_id가 기준 폴더 이름과 다름 (명세 0.1 · 8절)")

# frame 교차 (§1)
_h("X-FRM-01", "CROSS", "ERROR", "구현", "frame.scan_id;meta.scan_id", "frame.scan_id:파일 안 모든 행이 같고",
   "frame.scan_id가 파일 안에서 다르거나 meta.scan_id와 다름")
_h("X-FRM-02", "CROSS", "ERROR", "구현", "frame.layer_idx;meta.layer_idx",
   "frame.layer_idx:파일 안 모든 행이 같음;;frame.layer_idx:스캔 폴더에서는",
   "frame.layer_idx가 파일 안에서 다르거나, 스캔 폴더에서 meta.layer_idx와 다름 (-1 포함)")
_h("X-FRM-03", "CROSS", "ERROR", "구현", "frame.frame_idx", "frame.frame_idx:첫 행 0", "frame_idx가 0부터 1씩 늘지 않음")
_h("X-FRM-04", "CROSS", "ERROR", "구현", "frame.file;frame.frame_idx", "frame.file:숫자 6자리", "frame.file의 숫자 6자리가 frame_idx와 다름")
_h("X-FRM-05", "CROSS", "ERROR", "구현", "frame.t_cam_ns", "frame.t_cam_ns:있으면 행마다 증가", "t_cam_ns가 행마다 늘지 않음")
_h("X-FRM-06", "CROSS", "ERROR", "구현", "frame.t_host_ns", "frame.t_host_ns:이전 행보다 큼", "t_host_ns가 이전 행보다 크지 않음")
_h("X-FRM-07", "CROSS", "ERROR", "구현", "frame.cam_seq", "frame.cam_seq:이전 행보다 큼", "cam_seq가 이전 행보다 크지 않음")
_h("X-FRM-08", "CROSS", "ERROR", "구현", "frame.exposure_us;meta.fps", "frame.exposure_us:1e6 ÷", "노출 > 1e6 ÷ meta.fps")
_h("X-FRM-09", "CROSS", "ERROR", "구현", "frame.exposure_us", "frame.exposure_us:스캔 안에서 모두 같음", "스캔 안에서 노출이 다름 (자동 노출)")
_h("X-FRM-10", "CROSS", "ERROR", "구현", "frame.gain_db", "frame.gain_db:스캔 안에서 모두 같음", "스캔 안에서 게인이 다름 (자동 게인)")
_h("X-FRM-11", "CROSS", "ERROR", "구현", "frame.pixel_format", "frame.pixel_format:스캔 안에서 같음", "스캔 안에서 pixel_format이 다름")
_h("X-FRM-12", "CROSS", "ERROR", "구현", "frame.lossy;frame.pixel_format", "frame.lossy:MJPG이면 true", "lossy가 pixel_format = MJPG와 맞지 않음")
_h("X-FRM-13", "CROSS", "ERROR", "구현", "frame.roi_x0_px;frame.roi_w_px;meta.cam_res_w_px",
   "frame.roi_x0_px:x + `frame.roi_w_px`;;frame.roi_w_px:1 ≤ x ≤", "ROI가 센서 폭을 넘음 (x0 + w > cam_res_w)")
_h("X-FRM-14", "CROSS", "ERROR", "구현", "frame.roi_y0_px;frame.roi_h_px;meta.cam_res_h_px",
   "frame.roi_y0_px:x + `frame.roi_h_px`;;frame.roi_h_px:1 ≤ x ≤", "ROI가 센서 높이를 넘음 (y0 + h > cam_res_h)")
_h("X-FRM-15", "CROSS", "ERROR", "구현", "frame.laser_on", "frame.laser_on:스캔마다 false 행", "스캔에 laser_on = false (배경) 행이 없음")
_h("X-FRM-16", "CROSS", "ERROR", "구현", "frame.trigger_mode", "frame.trigger_mode:스캔 안에서 같음", "스캔 안에서 trigger_mode가 다름")
_h("X-FRM-17", "CROSS", "ERROR", "구현", "frame.dropped_before;frame.cam_seq", "frame.dropped_before:이번 cam_seq",
   "dropped_before ≠ 이번 cam_seq − 이전 cam_seq − 1")
_h("X-FRM-18", "CROSS", "ERROR", "구현", "frame.saturated_px;frame.roi_w_px;frame.roi_h_px", "frame.saturated_px:roi_w × roi_h",
   "saturated_px > roi_w × roi_h")
_h("H-FRM-19", "보류", "WARN", "보류", "frame.lossy", "frame.lossy:처리 코드가 경고",
   "lossy = true면 처리 코드가 경고", "처리 코드 (T7) 몫. 데이터 검증 규칙이 아님")
# SV13 (T1 2차)
_h("X-FRM-20", "CROSS", "ERROR", "구현", "frame.layer_idx;ref.layer_idx", "frame.layer_idx:기준 촬영 폴더에서는",
   "기준 촬영 폴더의 frame.layer_idx가 ref.layer_idx와 다름 (ref.layer_idx가 빈 칸이면 -1이어야 함)")
_h("X-FRM-21", "CROSS", "ERROR", "구현", "frame.trig_pulse_idx", "frame.trig_pulse_idx:값이 있는 행끼리 증가",
   "trig_pulse_idx가 값이 있는 행끼리 늘지 않음")
_h("X-FRM-22", "CROSS", "ERROR", "구현", "frame.trig_pulse_idx;frame.dropped_before", "frame.trig_pulse_idx:앞 값과의 차",
   "trig_pulse_idx 앞 값과의 차 − 1 ≠ dropped_before")
_h("X-FRM-23", "CROSS", "ERROR", "구현", "frame.gate_on", "frame.gate_on:스캔 안에서 true 행이",
   "gate_on = true 행이 한 덩어리가 아님 (중간에 끊김)")

# pos 교차 (§2)
_h("X-POS-01", "CROSS", "ERROR", "구현", "pos.scan_id;meta.scan_id", "pos.scan_id:`meta.scan_id`와 같음", "pos.scan_id가 meta.scan_id와 다름")
_h("X-POS-02", "CROSS", "ERROR", "구현", "pos.t_ns", "pos.t_ns:같은 clock·source 안에서 증가", "같은 clock·source 안에서 t_ns가 늘지 않음")
_h("X-POS-03", "CROSS", "ERROR", "구현", "pos.x_mm", "pos.x_mm:스캔 구간에서 변화", "스캔 구간 x_mm 변화 > 0.01")
_h("X-POS-04", "CROSS", "ERROR", "구현", "pos.y_mm", "pos.y_mm:단조", "스캔 구간 y_mm가 출처별로 단조가 아님")
_h("X-POS-05", "CROSS", "ERROR", "구현", "pos.z_mm", "pos.z_mm:스캔 구간 변화", "스캔 구간 z_mm (source = cmd) 변화 > 0.001")
_h("X-POS-06", "CROSS", "ERROR", "구현", "pos.e_mm", "pos.e_mm:변화 0;;pos.e_mm:그 구간에 값이 하나 이하면",
   "스캔 구간에서 값이 있는 행끼리 e_mm가 변함 (스캔 중 압출)")
_h("X-POS-07", "CROSS", "ERROR", "구현", "pos.feed_mm_s;meta.scan_speed_mm_s", "pos.feed_mm_s:±5 %", "스캔 구간 feed 평균이 scan_speed ±5 % 밖")
_h("X-POS-08", "CROSS", "ERROR", "구현", "pos.layer_idx;meta.layer_idx", "pos.layer_idx:스캔 폴더에서는",
   "스캔 폴더의 pos.layer_idx ≠ meta.layer_idx (-1 포함)")
_h("X-POS-09", "CROSS", "ERROR", "구현", "pos.event", "pos.event:스캔마다 scan_start 1개", "scan_start·scan_end가 1개씩이 아니거나 scan_start가 먼저가 아님")
_h("X-POS-10", "CROSS", "ERROR", "구현", "pos.acc_x_mm_s2;pos.acc_y_mm_s2;pos.acc_z_mm_s2", "pos.acc_x_mm_s2:있으면 acc_y·acc_z도",
   "acc_x가 있는데 acc_y·acc_z 중 빈 칸이 있음")
# SV13 (T1 2차)
_h("X-POS-11", "CROSS", "ERROR", "구현", "pos.layer_idx;pos.scan_id;frame.layer_idx;frame.scan_id", "pos.layer_idx:기준 촬영 폴더에서는",
   "기준 폴더 position_log의 scan_id·layer_idx가 그 기준 frames_index와 다름 (명세 4절)")
_h("X-POS-12", "CROSS", "ERROR", "구현", "pos.pass_idx", "pos.pass_idx:scan_start~scan_end 사이에서 값이 0부터",
   "스캔 구간 pass_idx가 0부터 빈 번호 없이 늘지 않음")
_h("X-POS-13", "CROSS", "ERROR", "구현", "pos.event;meta.timing", "pos.event:resume은",
   "resume이 layer 스캔의 scan_end 뒤 0–1개가 아님 (post 스캔에 있거나, 2개 이상이거나, scan_end 앞)")
_h("X-POS-14", "CROSS", "ERROR", "구현", "pos.event;pos.t_ns;meta.timing", "pos.event:cool_start · cool_end는",
   "cool_start·cool_end가 post 스캔에 각 1개가 아니거나 (layer 스캔에 있음 포함) cool_start < cool_end ≤ scan_start가 아님")

# cal 교차 (§3)
_h("X-CAL-01", "CROSS", "ERROR", "구현", "cal.target_square_mm;cal.target_cols", "cal.target_square_mm:target_cols × x", "target_cols × target_square_mm > 20.2 (시야 폭)")
_h("X-CAL-02", "CROSS", "ERROR", "구현", "cal.target_marker_mm;cal.target_square_mm", "cal.target_marker_mm:0 < x <", "target_marker_mm ≥ target_square_mm")
_h("X-CAL-03", "CROSS", "ERROR", "구현", "cal.pose_idx", "cal.pose_idx:조합이 유일", "(cal_id, kind, pose_idx, laser_on) 중복")
_h("X-CAL-04", "CROSS", "ERROR", "구현", "cal.image_file;cal.kind", "cal.image_file:앞 숫자가", "image_file 앞 숫자가 kind 숫자와 다름")
_h("X-CAL-05", "CROSS", "ERROR", "구현", "cal.laser_on", "cal.laser_on:D2는 같은 pose_idx", "D2 pose_idx에 laser_on true·false 짝이 없음")
_h("X-CAL-06", "CROSS", "ERROR", "구현", "cal.exposure_us", "cal.exposure_us:D2는 같은 pose_idx", "D2 같은 pose_idx 켬·끔 노출이 다름")
_h("X-CAL-07", "CROSS", "ERROR", "구현", "cal.cmd_z_mm", "cal.cmd_z_mm:자세마다 다르고", "D2 cmd_z_mm가 자세마다 다르지 않거나 범위 폭 > 8.0")
_h("X-CAL-08", "CROSS", "ERROR", "구현", "cal.gauge_measured_mm;cal.gauge_nominal_mm", "cal.gauge_measured_mm:abs(x − 공칭)", "abs(gauge_measured − nominal) > 0.02")
_h("X-CAL-09", "CROSS", "ERROR", "구현", "cal.valid_from;cal.created", "cal.valid_from:≥ `cal.created`", "valid_from < created")
_h("X-CAL-10", "CROSS", "ERROR", "구현", "cal.valid_until;cal.valid_from", "cal.valid_until:있으면 >", "valid_until ≤ valid_from")
_h("W-CAL-11", "CROSS", "WARN", "구현", "cal.reproj_rms_px", "cal.reproj_rms_px:판정 < 0.2", "D1 재투영 RMS ≥ 0.2 px (청사진 C4 판정 기준)")
_h("W-CAL-12", "CROSS", "WARN", "구현", "cal.plane_rms_um", "cal.plane_rms_um:옛 M1 기준", "D2 평면 RMS ≥ 5 µm (옛 M1 기준)")
_h("W-CAL-13", "CROSS", "WARN", "구현", "cal.invalidated_by;meta.calibration_id", "cal.invalidated_by:none이 아니면",
   "무효화된 교정 (invalidated_by ≠ none)을 쓴 스캔")
_h("H-CAL-14", "보류", "ERROR", "보류", "cal.result_file", "cal.result_file:교정이 끝나면 파일 있음",
   "교정이 끝나면 result_file 있음", "결과 파일은 데이터 폴더 밖 저장소 config/calibration/ 기준이라 캠페인 폴더만으로 못 봄")
# H-CAL-15 · 16은 SV13에서 뺌: cal.record_type이 생겨 REQ · CROSS-EMPTY (조건부)로 구현
_h("X-CAL-17", "CROSS", "ERROR", "구현", "cal.record_type;cal.kind", "cal.record_type:nozzle_touch는 kind = D4에서만",
   "record_type = nozzle_touch인데 kind ≠ D4")
_h("X-CAL-18", "CROSS", "ERROR", "구현", "cal.record_type;cal.target_type", "cal.record_type:micrometer는",
   "record_type = micrometer인데 target_type ∉ {filler_gauge, step_gauge, material_sample}")
_h("X-CAL-19", "CROSS", "ERROR", "구현", "cal.target_type;cal.kind", "cal.target_type:filler_gauge · step_gauge · material_sample은 kind = D5",
   "target_type이 filler_gauge·step_gauge·material_sample인데 kind ≠ D5")
_h("X-CAL-20", "CROSS", "ERROR", "구현", "cal.laser_on;cal.record_type", "cal.laser_on:`cal.record_type` ≠ image면 false",
   "영상이 아닌 행 (record_type ≠ image)인데 laser_on = true")
_h("X-CAL-21", "CROSS", "ERROR", "구현", "cal.gauge_block_id;cal.gauge_nominal_mm", "cal.gauge_block_id:FG면 숫자",
   "FG- 숫자가 gauge_nominal_mm와 다름")
_h("X-CAL-22", "CROSS", "ERROR", "구현", "cal.gauge_block_height_mm;cal.gauge_block_id", "cal.gauge_block_height_mm:블록 공칭 합과 차",
   "블록 교정 높이와 GB- 공칭 합의 차 > 0.02 mm (명세 [추정])")
_h("X-CAL-23", "CROSS", "ERROR", "구현", "cal.gauge_block_height_mm;cal.gauge_block_id;cal.cal_id", "cal.gauge_block_height_mm:같은 cal_id 안",
   "같은 cal_id 안 같은 gauge_block_id인데 gauge_block_height_mm가 다름")
_h("H-CAL-24", "보류", "ERROR", "보류", "cal.material_offset_um", "cal.material_offset_um:조각은 같은 캠페인;;cal.material_offset_um:재료가 여럿이면",
   "재료 조각이 스캔과 같은 필라멘트, 재료마다 cal_id 따로",
   "cal 행에 재료·색 필드가 없어 meta.material·meta.color와 데이터로 대조할 수 없음 (T1에 넘김)")

# ref 교차 (§4)
_h("X-REF-01", "CROSS", "ERROR", "구현", "ref.ref_id;ref.kind", "ref.ref_id:가운데 세 글자;;ref.kind:ref_id 약어와 맞음", "ref_id 가운데 세 글자가 kind 약어와 다름")
_h("X-REF-02", "CROSS", "ERROR", "구현", "ref.kind;ref.t_start_ns;meta.layer_end_t_ns", "ref.kind:bed_bare는 세션마다",
   "세션에 bed_bare가 없거나 bed_bare 시각이 첫 층 layer_end_t_ns보다 늦음")
_h("X-REF-03", "CROSS", "ERROR", "구현", "ref.scan_id;meta.layer_z_mm", "ref.scan_id:kind = bed_marker면 그 스캔", "bed_marker 짝 스캔의 layer_z_mm > 8.0")
_h("X-REF-04", "CROSS", "ERROR", "구현", "ref.layer_idx;ref.scan_id;meta.layer_idx", "ref.layer_idx:ref.scan_id가 있으면",
   "ref.layer_idx가 짝 스캔 meta.layer_idx와 다름")
_h("X-REF-05", "CROSS", "ERROR", "구현", "ref.n_frames", "ref.n_frames:frames_index.csv 행 수", "ref.n_frames ≠ 기준 frames_index.csv 행 수")
_h("X-REF-06", "CROSS", "ERROR", "구현", "ref.n_frames;ref.kind", "ref.n_frames:static_repeat면", "static_repeat인데 n_frames < 100")
_h("X-REF-07", "CROSS", "ERROR", "구현", "ref.t_start_ns", "ref.t_start_ns:짝 스캔이 있으면", "짝 스캔 첫 프레임과 기준 시각 차이 > 600 s")
_h("X-REF-08", "CROSS", "ERROR", "구현", "ref.scan_id", "ref.scan_id:층마다 그 층 스캔과 짝",
   "층별 기준 (스캔 폴더 안)의 ref.scan_id가 그 스캔 meta.scan_id와 다름")
_h("W-REF-09", "CROSS", "WARN", "구현", "ref.line_peak_pct", "ref.line_peak_pct:20 % 넘게 낮으면 경고",
   "같은 kind 이전 값보다 line_peak_pct가 20 % 넘게 낮음 (광학창 오염 추세)")
# SV13 (T1 2차)
_h("X-REF-10", "CROSS", "ERROR", "구현", "ref.kind;ref.t_start_ns;meta.layer_end_t_ns", "ref.kind:feeler도 출력 전",
   "feeler 기준 시각이 그 세션 첫 층 layer_end_t_ns보다 늦음 (출력 전이어야 함)")
_h("W-REF-11", "CROSS", "WARN", "비활성", "ref.calibration_id;meta.calibration_id;meta.bed_ref_id",
   "ref.calibration_id:kind = bed_bare면 그 기준을;;meta.calibration_id:그 스캔의 `meta.bed_ref_id`가 가리키는",
   "bed_bare 기준의 ref.calibration_id ≠ 그 기준을 가리키는 스캔의 meta.calibration_id (판정 거부 X4)",
   "D-21 대기 (X4 채택은 사용자 결정 전). 기본 끔. 켜기: validate_dataset.py --enable-rule W-REF-11 또는 config/default.yaml validate.enable_rules")
_h("X-REF-12", "CROSS", "ERROR", "구현", "ref.gauge_block_id;cal.gauge_block_id", "ref.gauge_block_id:같은 캠페인",
   "ref.gauge_block_id가 같은 캠페인 cal_manifest.csv의 cal.gauge_block_id에 없음")
_h("X-REF-13", "CROSS", "ERROR", "구현", "ref.gauge_block_id;ref.kind", "ref.gauge_block_id:step_gauge면 GB-로",
   "step_gauge인데 GB-로, feeler인데 FG-로 시작하지 않음")
_h("X-REF-14", "CROSS", "ERROR", "구현", "ref.gauge_height_mm;cal.gauge_block_height_mm;cal.gauge_measured_mm",
   "ref.gauge_height_mm:step_gauge면 = 그 블록",
   "ref.gauge_height_mm ≠ cal 교정값 (step_gauge: gauge_block_height_mm, feeler: gauge_measured_mm, 차 > 1e-9)")
_h("X-REF-15", "CROSS", "ERROR", "구현", "ref.gauge_height_mm;meta.layer_z_mm", "ref.gauge_height_mm:kind = step_gauge면 x <",
   "step_gauge 높이 ≥ 짝 스캔 layer_z_mm (노즐 충돌)")
_h("X-REF-16", "CROSS", "ERROR", "구현", "ref.kind;pos.z_mm", "meta.zero_ref_method:step_gauge면 짝",
   "step_gauge 기준 위치 로그의 스캔 구간 Z (cmd)가 짝 스캔 스캔 구간 Z와 0.001 mm 넘게 다름 (같은 Z 연속 측정, 명세 4절)")

# meta 교차 (§5)
_h("X-MET-01", "CROSS", "ERROR", "구현", "meta.scan_id;meta.timing;meta.layer_idx",
   "meta.scan_id:timing = layer면;;meta.scan_id:timing = post면", "scan_id의 _L 부분이 timing·layer_idx와 맞지 않음")
_h("X-MET-02", "CROSS", "ERROR", "구현", "meta.campaign_id;meta.source", "meta.campaign_id:첫 글자 V", "캠페인 첫 글자 V ⇔ source = virtual 위반")
_h("X-MET-03", "CROSS", "ERROR", "구현", "meta.specimen_id;meta.scan_id", "meta.specimen_id:scan_id 앞 세 글자", "specimen_id ≠ scan_id 앞 세 글자")
_h("X-MET-04", "CROSS", "ERROR", "구현", "meta.repeat;meta.scan_id", "meta.repeat:scan_id의 rNN", "repeat ≠ scan_id의 rNN")
_h("X-MET-05", "CROSS", "ERROR", "구현", "meta.timing;meta.thermal_state",
   "meta.timing:layer ⇔;;meta.thermal_state:timing = layer ⇔ in_process", "timing과 thermal_state가 짝이 아님 (layer ⇔ in_process, post ⇔ cooled)")
_h("X-MET-06", "CROSS", "ERROR", "구현", "meta.layer_idx;meta.layer_count", "meta.layer_idx:0 ≤ x <", "layer_idx ≥ layer_count")
_h("X-MET-07", "CROSS", "ERROR", "구현", "meta.layer_z_mm;meta.layer_idx", "meta.layer_z_mm:layer_idx가 크면 더 큼",
   "같은 세션·시편·반복에서 층이 높은데 layer_z_mm가 더 크지 않음")
_h("H-MET-08", "보류", "ERROR", "보류", "meta.layer_z_mm", "meta.layer_z_mm:G코드 해당 층 Z",
   "abs(layer_z_mm − G코드 층 Z) ≤ 0.0001", "G코드 해석 (T4a) 결과가 있어야 함. T6는 cvlab.gcode를 import하지 않음 (소유 표)")
_h("X-MET-09", "CROSS", "ERROR", "구현", "meta.gcode_line_start;meta.gcode_line_end",
   "meta.gcode_line_start:≤ `meta.gcode_line_end`;;meta.gcode_line_end:x ≥ gcode_line_start", "gcode_line_start > gcode_line_end")
_h("X-MET-10", "CROSS", "ERROR", "구현", "meta.gcode_line_end", "meta.gcode_line_end:다음 층", "gcode_line_end ≥ 다음 층 gcode_line_start")
_h("X-MET-11", "CROSS", "ERROR", "구현", "meta.layer_end_t_ns;meta.scan_start_t_ns", "meta.layer_end_t_ns:0 < x <", "layer_end_t_ns ≥ scan_start_t_ns")
_h("X-MET-12", "CROSS", "ERROR", "구현", "meta.scan_start_t_ns;pos.t_ns;pos.event", "meta.scan_start_t_ns:position_log의 scan_start",
   "scan_start_t_ns ≠ position_log scan_start 행의 호스트 시각")
_h("X-MET-13", "CROSS", "ERROR", "구현", "meta.wait_after_layer_s;meta.scan_start_t_ns;meta.layer_end_t_ns",
   "meta.wait_after_layer_s:abs(x − (scan_start_t_ns", "wait_after_layer_s ≠ (scan_start − layer_end) ÷ 1e9 (±0.001)")
_h("X-MET-14", "CROSS", "ERROR", "구현", "meta.pause_added_s;meta.timing;meta.scan_length_mm;meta.scan_speed_mm_s",
   "meta.pause_added_s:timing = layer면;;meta.pause_added_s:post면 0", "pause_added_s가 layer면 scan_length ÷ speed 미만, post면 0이 아님")
_h("W-MET-15", "CROSS", "WARN", "구현", "meta.layer_time_s;meta.pause_added_s", "meta.layer_time_s:작은 층 경고", "pause_added_s ÷ layer_time_s > 1 (작은 층, T2 MF-PRC-11)")
_h("W-MET-16", "CROSS", "WARN", "구현", "meta.scan_z_hop_mm", "meta.scan_z_hop_mm:1.0 미만이면 긁힘 경고", "scan_z_hop_mm < 1.0 (긁힘, T2 MF-PRC-04)")
_h("X-MET-17", "CROSS", "ERROR", "구현", "meta.scan_x_mm;pos.x_mm", "meta.scan_x_mm:position_log 스캔 구간", "scan_x_mm와 스캔 구간 x_mm 평균 차이 > 0.01")
_h("X-MET-18", "CROSS", "ERROR", "구현", "meta.scan_y0_mm;pos.y_mm", "meta.scan_y0_mm:position_log scan_start 행", "scan_y0_mm와 scan_start 행 y_mm 차이 > 0.01")
_h("X-MET-19", "CROSS", "ERROR", "구현", "meta.control_group;meta.timing", "meta.control_group:none이 아니면", "control_group ≠ none인데 timing ≠ post")
_h("X-MET-20", "CROSS", "ERROR", "구현", "meta.enclosure;meta.ambient_light", "meta.enclosure:ambient_light = enclosure_dark면", "ambient_light = enclosure_dark인데 enclosure ≠ true")
# H-MET-21 · 22는 SV13에서 FILE-18 · FILE-17로 구현 (명세 0.1절: 저장소 뿌리 기준)
_h("H-MET-23", "보류", "ERROR", "보류", "meta.gcode_sha256", "meta.gcode_sha256:실제 파일 지문과 같음",
   "gcode_sha256 = 실제 파일 지문", "사용자 G코드 미수령 (D-10 대기). 지문 대조는 정답 G코드가 정해진 뒤 (파일 있음은 FILE-17)")
_h("X-MET-24", "CROSS", "ERROR", "구현", "meta.layer_h_mm;meta.nozzle_dia_mm", "meta.layer_h_mm:0.04 ≤ x ≤", "layer_h_mm > nozzle_dia_mm")
_h("X-MET-25", "CROSS", "ERROR", "구현", "meta.bed_ref_id;ref.ref_id;ref.kind",
   "meta.bed_ref_id:같은 세션 `reference/`;;meta.bed_ref_id:없거나 bed_bare가 아니면 판정 거부 X1",
   "bed_ref_id가 같은 세션 reference/의 bed_bare 기준을 가리키지 않음 (판정 거부 X1)")
_h("X-MET-26", "CROSS", "ERROR", "구현", "meta.bed_ref_id", "meta.bed_ref_id:세션 안 모든 스캔이 같은 값", "세션 안 bed_ref_id가 다름")
_h("X-MET-27", "CROSS", "ERROR", "구현", "meta.z_offset_mm", "meta.z_offset_mm:세션 안 모든 스캔이 같은 값", "세션 안 z_offset_mm가 다름 (0점이 바뀜)")
_h("H-MET-28", "보류", "ERROR", "보류", "meta.z_offset_mm", "meta.z_offset_mm:펌웨어 값의 부호",
   "펌웨어 부호를 명세 부호로 바꿔 적음", "부호 바꾸는 법이 부록 D에서 [T14 대기]")
_h("X-MET-29", "CROSS", "ERROR", "구현", "meta.zero_ref_method;meta.layer_z_mm;ref.kind",
   "meta.zero_ref_method:bed_marker면", "bed_marker인데 layer_z_mm > 8.0이거나 짝 bed_marker 기준이 없음")
_h("X-MET-30", "CROSS", "ERROR", "구현", "meta.zero_ref_method;ref.kind", "meta.zero_ref_method:ref_tower면", "ref_tower인데 짝 ref_tower 기준이 없음")
_h("H-MET-31", "보류", "ERROR", "보류", "meta.bed_mesh_file", "meta.bed_mesh_file:펌웨어가 낸 원본 그대로",
   "메시 표가 펌웨어 원본 형식", "형식이 부록 D에서 [T14 대기]")
_h("X-MET-32", "CROSS", "ERROR", "구현", "meta.bed_mesh_file", "meta.bed_mesh_file:세션 안 모든 스캔이 같은 값", "세션 안 bed_mesh_file이 다름")
_h("X-MET-33", "CROSS", "ERROR", "구현", "meta.paired_scan_id;meta.layer_count;meta.thermal_state",
   "meta.paired_scan_id:같은 세션·시편·반복의 스캔", "paired_scan_id가 같은 세션·시편·반복의 마지막 층 in_process 스캔이 아님")
_h("X-MET-34", "CROSS", "ERROR", "구현", "meta.cool_wait_s;meta.wait_after_layer_s", "meta.cool_wait_s:abs(x −", "abs(cool_wait_s − wait_after_layer_s) > 0.001")
# H-MET-35는 SV13에서 설명문 (NOTES)으로: 명세가 "판정 규칙 R4 · R5, 보고에만 씀"으로 정함
_h("X-MET-36", "CROSS", "ERROR", "구현", "meta.firmware;meta.firmware_name;meta.firmware_version",
   "meta.firmware_name:13절;;meta.firmware:이름 부분 = `meta.firmware_name`;;meta.firmware:`meta.firmware_name`·`meta.firmware_version`과 맞음"
   ";;meta.firmware:형식 `[<제조사>-]",
   "meta.firmware가 [<제조사>-]<firmware_name>-<firmware_version>[-<git 7자리>] 형식과 맞지 않음 (13절)")
_h("X-MET-37", "CROSS", "ERROR", "구현", "meta.cam_interface;frame.roi_w_px;frame.roi_h_px;frame.bit_depth;meta.fps",
   "meta.cam_interface:usb2면 9절 대역폭 검사", "usb2인데 ROI × 비트 × fps가 60 MB/s (9절 이론값)를 넘음")
_h("W-MET-38", "CROSS", "WARN", "구현", "meta.lens_focus_locked;meta.source", "meta.lens_focus_locked:실측에서 false면 검증 경고", "실측인데 lens_focus_locked = false")
_h("W-MET-39", "CROSS", "WARN", "구현", "meta.laser_power_mw", "meta.laser_power_mw:넘으면 C8 안전 경고", "laser_power_mw > 1.0 (C8 안전 경고)")
_h("X-MET-40", "CROSS", "ERROR", "구현", "meta.filter_center_nm;meta.laser_wavelength_nm", "meta.filter_center_nm:abs(x −", "abs(filter_center − laser_wavelength) > 20")
_h("X-MET-41", "CROSS", "ERROR", "구현", "meta.exposure_set_us;frame.exposure_us", "meta.exposure_set_us:frame.exposure_us 값들과", "exposure_set_us와 frame.exposure_us 차이 > 1 %")
_h("X-MET-42", "CROSS", "ERROR", "구현", "meta.gain_set_db;frame.gain_db", "meta.gain_set_db:frame.gain_db 값들과 같음", "gain_set_db ≠ frame.gain_db")
_h("X-MET-43", "CROSS", "ERROR", "구현", "meta.frame_avg_n;meta.scan_speed_mm_s", "meta.frame_avg_n:이동 스캔이면 1", "이동 스캔 (scan_speed > 0)인데 frame_avg_n ≠ 1")
_h("X-MET-44", "CROSS", "ERROR", "구현", "meta.scan_speed_mm_s;meta.fps;meta.scan_pitch_mm", "meta.scan_speed_mm_s:abs(x − fps", "abs(scan_speed − fps × pitch) > 0.01 × scan_speed")
_h("X-MET-45", "CROSS", "ERROR", "구현", "meta.n_frames", "meta.n_frames:frames_index.csv 행 수와 같음", "n_frames ≠ frames_index.csv 행 수")
_h("X-MET-46", "CROSS", "ERROR", "구현", "meta.n_frames;meta.scan_length_mm;meta.scan_pitch_mm", "meta.n_frames:≥ scan_length_mm", "n_frames < scan_length ÷ pitch")
_h("H-MET-47", "보류", "ERROR", "보류", "meta.raw_saved", "meta.raw_saved:처리 결과(프로파일)를 따로 보관",
   "raw_saved = false면 프로파일을 따로 보관", "프로파일 저장 형식이 미정 (명세 14절 11, T6·T7)")
_h("X-MET-48", "CROSS", "ERROR", "구현", "meta.calibration_id", "meta.calibration_id:같은 캠페인 calibration/", "calibration_id가 같은 캠페인 calibration/에 없음")
_h("X-MET-49", "CROSS", "ERROR", "구현", "meta.calibration_id;meta.datetime;cal.valid_from;cal.valid_until",
   "meta.calibration_id:datetime이 cal.valid_from", "스캔 datetime이 교정 유효 기간 밖")
_h("X-MET-50", "CROSS", "ERROR", "구현", "meta.files_sha256", "meta.files_sha256:키 = 상대 경로", "files_sha256 키가 상대 경로가 아니거나 값이 64자 16진수가 아님")
_h("X-MET-51", "CROSS", "ERROR", "구현", "meta.injected_factors;meta.source", "meta.injected_factors:source = real이면 빈 목록", "실측인데 injected_factors가 빈 목록이 아님")
_h("H-MET-52", "보류", "ERROR", "보류", "meta.slicer_name", "meta.slicer_name:G코드 머리말에서 읽고",
   "slicer_name = G코드 머리말 값", "G코드 해석 (T4a) 결과가 있어야 함")
# H-MET-53은 SV13에서 뺌: 명세가 정규식 `^LM-T14-\d+$`을 줘 REGEX 자동 규칙으로 구현
# SV13 (T1 2차)
_h("X-MET-54", "CROSS", "ERROR", "구현", "meta.scan_id;meta.scan_pass_idx", "meta.scan_id:`meta.scan_pass_idx` = 0이면",
   "scan_id의 _p 부분이 scan_pass_idx와 맞지 않음 (0이면 _p 없음, 1 이상이면 _p 숫자 = scan_pass_idx)")
_h("X-MET-55", "CROSS", "ERROR", "구현", "meta.scan_pass_idx",
   "meta.scan_pass_idx:같은 시편·반복·층;;meta.scan_pass_idx:줄이 하나면 0",
   "같은 시편·반복·층 (post끼리)의 scan_pass_idx가 0부터 빈 번호 없이 이어지지 않음")
_h("W-MET-56", "CROSS", "WARN", "비활성", "meta.layer_idx;meta.layer_count;meta.thermal_state", "meta.layer_idx:모든 층 스캔 (D-18)",
   "같은 시편·반복의 in_process 스캔에 0 ~ layer_count − 1 층이 다 있지 않음 (판정 거부 X7)",
   "D-21 대기 (X7 채택은 사용자 결정 전). 기본 끔. 켜기: validate_dataset.py --enable-rule W-MET-56 또는 config/default.yaml validate.enable_rules")
_h("W-MET-57", "CROSS", "WARN", "구현", "meta.bed_motion;meta.scan_axis",
   "meta.bed_motion:y면 `meta.scan_axis`;;meta.scan_axis:베드가 Y로 움직이는 프린터면",
   "bed_motion = y인데 scan_axis가 ±X가 아님 (권장 위반, T2 MF-MEC-10)")
_h("X-MET-58", "CROSS", "ERROR", "구현", "meta.z_drive;meta.timing;pos.event", "meta.z_drive:belt면 식힌 재측정 동안",
   "z_drive = belt인 post 스캔 위치 로그에 motor_off가 있음 (식힌 재측정 동안 모터 유지, T2 MF-SYN-09)")
_h("X-MET-59", "CROSS", "ERROR", "구현", "meta.firmware;meta.firmware_fork", "meta.firmware:제조사 접두사는",
   "meta.firmware에 제조사 접두사가 있는데 firmware_fork ≠ vendor")
_h("X-MET-60", "CROSS", "ERROR", "구현", "meta.trigger_pin;frame.trigger_mode", "meta.trigger_pin:이 스캔의",
   "trigger_mode ∈ {hw, gate}인데 trigger_pin = none이거나, 그 밖인데 trigger_pin ≠ none")
_h("X-MET-61", "CROSS", "ERROR", "구현", "meta.trigger_period_s;meta.fps", "meta.trigger_period_s:abs(x ×",
   "abs(trigger_period_s × fps − 1) > 0.001")
_h("X-MET-62", "CROSS", "ERROR", "구현", "meta.zero_ref_method;ref.kind", "meta.zero_ref_method:step_gauge면 짝",
   "zero_ref_method = step_gauge인데 짝 step_gauge 기준이 없음")
_h("W-MET-63", "CROSS", "WARN", "구현", "meta.zero_ref_method", "meta.zero_ref_method:z_only는",
   "zero_ref_method = z_only (기록은 되나 판정 거부 X2, 판정 단계 몫)")

# rep 교차 (§7)
_h("X-REP-01", "CROSS", "ERROR", "구현", "rep.part_idx;rep.specimen_id", "rep.part_idx:같은 specimen_id면 같음", "같은 specimen_id인데 part_idx가 다름")
_h("X-REP-02", "CROSS", "ERROR", "구현", "rep.repeat_idx", "rep.repeat_idx:유일", "(part_idx, session_id, operator, repeat_idx) 중복")
_h("X-REP-03", "CROSS", "ERROR", "구현", "rep.remount;rep.scan_id", "rep.remount:층별 측정에서", "remount = true인데 실행 스캔이 post가 아님 (design_executed)")
_h("X-REP-04", "CROSS", "ERROR", "구현", "rep.run_order", "rep.run_order:1 ≤ x ≤ 행 수;;rep.run_order:중복 없음", "run_order가 행 수보다 크거나 중복")
_h("H-REP-05", "보류", "WARN", "보류", "rep.run_order", "rep.run_order:행 순서와 다름",
   "행 순서와 다른 무작위 순서 권장", "권장 사항이라 위반 기준이 없음")
_h("X-REP-06", "CROSS", "ERROR", "구현", "rep.noise_seed", "rep.noise_seed:같은 study 안에서 행마다 다름", "같은 study 안 noise_seed 중복")
_h("X-REP-07", "CROSS", "ERROR", "구현", "rep.truth_id;rep.specimen_id", "rep.truth_id:같은 specimen_id면 같음", "같은 specimen_id인데 truth_id가 다름")

# truth (부록 A). data/raw 검사에서는 열지 않음: Validator.check_truth()로 참값 객체만 따로 봄 (T3 시뮬레이터가 씀)
_h("X-TRU-01", "CROSS", "ERROR", "구현", "truth.judgement;truth.pass_pct", "",
   "truth.judgement = pass ⇔ truth.pass_pct ≥ 95 위반 (부록 A)")

# 다른 필드의 REQ 규칙이 맡는 문장 (규칙은 자동 생성, 여기서는 덮는 문장만 적음)
EXTRA_COVERS = {
    "REQ.meta.step_edge_angle_deg": "meta.specimen_role:aux_step이면 단차 필드",
    "REQ.meta.paired_scan_id": "meta.thermal_state:cooled면",
    "REQ.pos.mesh_dz_mm": "meta.mesh_enabled:true면 position_log에",
    "REQ.meta.specimen_temp_c": "meta.specimen_temp_c:source = real이고 온도 센서가 없을 때만",
    "CROSS-EMPTY.frame.file": "meta.raw_saved:false면 영상 없음",
    "RANGE.meta.tolerance_mm": "meta.tolerance_mm:다른 값이면 검증 실패",
    "REGEX.meta.injected_factors": "meta.injected_factors:원소마다 정규식",
    "CROSS-EMPTY.ref.layer_idx": "ref.layer_idx:kind ∈ {bed_bare, feeler}면 빈 칸",
    "REQ.pos.source": "pos.source:모든 행에 있음",
    "REGEX.meta.firmware": "meta.firmware:정규식 `^([a-z0-9]+-)?",
}

# 설명문 (검사할 내용 없음). (필드, 문장 일부, 사유)
NOTES = [
    ("meta.specimen_role", "기본 user_gcode", "기본값 설명"),
    ("meta.timing", "기본은 layer", "기본값 설명 (D-04)"),
    ("meta.scan_z_hop_mm", "C2 권장 2 mm", "권장값 근거"),
    ("meta.scan_axis", "M54 기본 +Y", "기본값 근거"),
    ("meta.printer_model", "예: sovol-sv08", "예시 설명 (T14)"),
    ("meta.printer_model", "가상은 흉내 낸 기종 이름", "작성 안내"),
    ("meta.gcode_file", "예시 이름은 자리표시", "예시 설명 (D-10)"),
    ("meta.step_edge_angle_deg", "90에 가까우면", "현상 설명 (T2 MF-MEC-13), 기준 없음"),
    ("meta.laser_temp_c", "허용 온도는 [미상]", "출처 표시"),
    ("meta.slicer_name", "예시는 자리표시", "예시 설명 (D-10)"),
    ("meta.gcode_flavor", "예시는 자리표시", "예시 설명"),
    ("meta.firmware_version", "모르면 \"unknown\"", "작성 안내. 빈 문자열 금지는 REGEX(nonempty)가 맡음"),
    ("meta.host_software", "직접 연결이면 \"none\"", "작성 안내"),
    # SV13 (T1 2차)
    ("frame.saturated_px", "판정 영역의 결측 원인", "쓰임 설명 (판정 거부 X6은 판정 단계 몫)"),
    ("frame.saturated_px", "값을 비우면 원시 영상에서 다시 셈", "처리 코드 안내 (선택 필드라 빈 칸 허용)"),
    ("pos.event", "probe는 프린터 레벨링 프로브 동작", "값 뜻 설명 (D-14)"),
    ("meta.scan_axis", "SV08 · Voron은 +Y", "기종별 값 예시"),
    ("meta.printer_kinematics", "SV08 = corexy", "기종별 값 예시 (T14)"),
    ("meta.bed_motion", "SV08 · Voron 2.4 = fixed", "기종별 값 예시 (T14)"),
    ("meta.z_drive", "SV08 = belt", "기종별 값 예시 (T14 [추정])"),
    ("meta.z_motor_count", "SV08 · Voron 2.4 = 4", "기종별 값 예시 (T14)"),
    ("meta.z_level_method", "SV08 = qgl", "기종별 값 예시 (T14)"),
    ("meta.probe_type", "SV08 = inductive_pressure", "기종별 값 예시 (T14, 측정 검증에 안 씀 D-14)"),
    ("meta.firmware", "판을 모르면 unknown", "작성 안내"),
    ("meta.firmware_fork", "SV08 기본 = vendor", "기종별 값 예시 (T14)"),
    ("meta.firmware_version", "Sovol 포크 판은 [미상]", "출처 표시 (T14)"),
    ("meta.host_software", "Klipper는 Moonraker", "작성 안내 (T14)"),
    ("meta.z_offset_mm", "meta가 스캔마다 있으므로", "설계 설명 (T2 MF-SYN-13 · GCD-03, 검사는 X-MET-27)"),
    ("meta.thermal_state", "판정에는 in_process만", "판정 단계 (T15) 몫. 판정 거부 X5는 데이터 검증 규칙이 아님"),
    ("meta.cool_wait_s", "식었다고 보는 기준은 판정 규칙 R4 · R5", "판정 규칙 몫 (D-20, 보고에만 씀). 옛 H-MET-35"),
    ("meta.layer_macro_version", "지금 판은 LM-T14-2", "현재 값 안내 (T14)"),
    ("meta.layer_macro_version", "판정 거부 X7 (빠진 층)을 볼 때 함께 봄", "쓰임 설명 (X7 검사는 W-MET-56)"),
    ("meta.shaper_freq_x_hz", "장착 뒤 다시 재지 않았으면 null", "작성 안내 (선택 필드라 null 허용)"),
    ("meta.trigger_pin", "실제 핀 이름은 [미상]", "출처 표시 (T14)"),
    ("meta.filter_fwhm_nm", "실제 값은 [미상]", "출처 표시"),
    ("meta.fps", "단위 프레임/s", "단위 설명"),
    ("meta.proc_time_s", "실시간 처리를 안 했으면 null", "작성 안내 (선택 필드라 null 허용)"),
]


def _auto_text_kind(sentence: str) -> str | None:
    """자동 규칙이 맡는 문장 종류. 못 맡으면 None."""
    s = re.sub(r"\s*\([^)]*\)\s*$", "", sentence).strip()
    if re.fullmatch(r"정규식 (`[^`]+`( 또는 )?)+( 로 시작)?", s):
        return "REGEX"
    if re.fullmatch(r"값 ∈ \{[^}]*\}(\s*\[대기:[^\]]*\])?", s) or re.fullmatch(r"값 = \S+", s):
        return "ENUM"
    if (re.fullmatch(r"[−\-\d.e^]+ [<≤] x( [<≤] [−\-\d.e^]+)?", s) or re.fullmatch(r"x [≥>] [\d.]+", s)
            or re.fullmatch(r"abs\(x\) ≤ [\d.]+", s) or re.fullmatch(r"= [\d.]+", s)):
        return "RANGE"
    if s == "유한값":
        return "FINITE"
    if s in NONEMPTY_PHRASES or s.startswith("쓸 말이 없으면"):
        return "NONEMPTY"
    if s.startswith("ISO 8601"):
        return "ISO"
    if s == "true 또는 false":
        return "BOOL"
    return None


def build_rules(fields: list[dict]) -> list[dict]:
    """필드표에서 규칙표를 만든다."""
    rules: list[dict] = []

    def add(**kw):
        r = {k: "" for k in RULE_COLUMNS}
        r.update(kw)
        rules.append(r)

    for f in fields:
        if f["group"] == "truth":
            continue
        name = f["field"]
        off = f["excluded"] == "true"
        st = "비활성" if off else "구현"
        why_off = f["excluded_reason"] if off else ""
        req = f["req"]
        if req == "필수":
            cond = SPECIAL_REQ.get(name, "")
            add(rule_id=f"REQ.{name}", kind="REQ", fields=name, severity="ERROR", status=st, condition=cond,
                message="필수 칸이 빔", reason=why_off)
        elif req == "선택":
            add(rule_id=f"REQ.{name}", kind="REQ", fields=name, severity="ERROR", status=st,
                condition="선택: 열(키)은 있어야 하고 값은 비어도 됨 (명세 §0.1: 없으면 빈 칸·null)",
                message="선택 필드의 열(키)이 없음", reason=why_off)
        elif req == "조건부":
            ctext, empty = CONDITIONS.get(name, ("", False))
            if off and not ctext:
                add(rule_id=f"REQ.{name}", kind="REQ", fields=name, severity="ERROR", status="비활성",
                    condition="(조건 미구현)", message="조건이 참인데 칸이 빔", reason=why_off)
            else:
                add(rule_id=f"REQ.{name}", kind="REQ", fields=name, severity="ERROR", status=st, condition=ctext,
                    message="조건이 참인데 칸이 빔", reason=why_off)
                if empty:
                    cf = [x for x in dict.fromkeys(re.findall(r"\b(?:frame|pos|cal|ref|meta|rep)\.[a-z0-9_]+", ctext)) if x != name]
                    add(rule_id=f"CROSS-EMPTY.{name}", kind="CROSS", fields=";".join([name] + cf), severity="ERROR", status=st,
                        condition=ctext, message="조건이 거짓인데 값이 있음 (명세 §0.1: 아니면 빈 칸)", reason=why_off)
        add(rule_id=f"DTYPE.{name}", kind="DTYPE", fields=name, severity="ERROR", status=st, params=f["dtype"],
            message=f"자료형이 {f['dtype']}가 아님", reason=why_off)
        if f["regex"]:
            add(rule_id=f"REGEX.{name}", kind="REGEX", fields=name, severity="ERROR", status=st, params=f["regex"],
                message="정규식과 맞지 않음", reason=why_off)
        if f["enum"]:
            pend = f["enum_pending"] == "true"
            add(rule_id=f"ENUM.{name}", kind="ENUM", fields=name, severity="WARN" if pend else "ERROR", status=st,
                params=f["enum"], message="허용 값 밖" + (" (허용 값 [대기: T14], 경고)" if pend else ""), reason=why_off)
        if f["min"] or f["max"]:
            p = f"{f['min']} {f['min_op']} x {f['max_op']} {f['max']}".strip()
            add(rule_id=f"RANGE.{name}", kind="RANGE", fields=name, severity="ERROR", status=st, params=p,
                message="범위 밖", reason=why_off)
        kinds = {_auto_text_kind(s) for s in split_sentences(f["rule_text"])}
        if "FINITE" in kinds and not (f["min"] or f["max"]):
            add(rule_id=f"RANGE.{name}", kind="RANGE", fields=name, severity="ERROR", status=st, params="finite",
                message="유한값이 아님 (inf)", reason=why_off)
        if "NONEMPTY" in kinds:
            add(rule_id=f"REGEX.{name}", kind="REGEX", fields=name, severity="ERROR", status=st, params=r"\S",
                message="빈 문자열 (공백만 있음)", reason=why_off)
        if "ISO" in kinds:
            add(rule_id=f"REGEX.{name}", kind="REGEX", fields=name, severity="ERROR", status=st, params=ISO_RE,
                message="ISO 8601 (시간대 포함) 형식이 아님", reason=why_off)
        if "BOOL" in kinds and not f["enum"]:
            add(rule_id=f"ENUM.{name}", kind="ENUM", fields=name, severity="ERROR", status=st, params="true,false",
                message="true·false가 아님", reason=why_off)

    for rid, kind, sev, status, flds, covers, msg, reason in H:
        add(rule_id=rid, kind=kind, fields=flds, severity=sev, status=status, message=msg, reason=reason, covers=covers)
    for r in rules:
        if r["rule_id"] in EXTRA_COVERS:
            r["covers"] = ";;".join(x for x in (r["covers"], EXTRA_COVERS[r["rule_id"]]) if x)
    return rules


def _covers(rules: list[dict]) -> list[tuple[str, str, str]]:
    out = []
    for r in rules:
        for c in filter(None, r["covers"].split(";;")):
            f, snip = c.split(":", 1)
            out.append((r["rule_id"], f, snip))
    return out


def classify_sentences(fields: list[dict], rules: list[dict]) -> list[dict]:
    """검사 대상 raw 필드의 검증 규칙 문장마다 맡은 규칙을 찾는다."""
    cov = _covers(rules)
    ids = {r["rule_id"] for r in rules}
    out = []
    for f in fields:
        if f["group"] == "truth" or f["excluded"] == "true":
            continue
        name = f["field"]
        for s in split_sentences(f["rule_text"]):
            who: list[str] = []
            k = _auto_text_kind(s)
            if k:
                rid = {"FINITE": "RANGE", "NONEMPTY": "REGEX", "ISO": "REGEX", "BOOL": "ENUM"}.get(k, k) + "." + name
                if rid in ids:
                    who.append(rid)
            if f["req"] == "조건부" and re.search(r"필수", s) and f"REQ.{name}" in ids:
                who.append(f"REQ.{name}")
            if f["req"] == "조건부" and re.search(r"빈 칸|null", s) and f"CROSS-EMPTY.{name}" in ids:
                who.append(f"CROSS-EMPTY.{name}")
            for rid, cf, snip in cov:
                if cf == name and snip in s:
                    who.append(rid)
            for nf, snip, why in NOTES:
                if nf == name and snip in s:
                    who.append("NOTE: " + why)
            out.append({"field": name, "sentence": s, "rules": who})
    return out


def uncovered_sentences(fields: list[dict], rules: list[dict]) -> list[tuple[str, str]]:
    return [(c["field"], c["sentence"]) for c in classify_sentences(fields, rules) if not c["rules"]]
