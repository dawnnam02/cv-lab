"""정상·경계·고장 표본을 만들어 검증기를 시험한다 (세부청사진 T6 §6.3, SV7 · SV8).

표본 값은 **형식 시험용**이다. 측정값이 아니다. 부록 B 값을 쓰고, 프레임 수만 줄였다
(스캔 길이 40 → 0.2 mm, 프레임 2010 → 12장, ROI 1280 × 256 → 32 × 16, 층 20 → 2).
표본은 저장소에 쓰지 않는다. 정상 표본만 임시 폴더(tempfile)에 한 번 써서 디스크 경로로도 검사하고 지운다.
"""

from __future__ import annotations

import copy
import io
import json
import math
import pickle
import tempfile
import time
from pathlib import Path

import numpy as np

from cvlab.io.hashing import sha256_bytes
from cvlab.io.validate import COND_FUNCS, DirFS, MemFS, Validator

CAMPAIGN = "VC-2026-11-20-A"
SESSION = "PS-2026-11-20-A"
SR = "S01_r01"
CAL = "CAL-2026-11-20-A"
AUTO = "__AUTO_SHA__"
# 저장소 뿌리 기준 파일 (명세 0.1절, FILE-17 · 18). 자체 시험은 디스크를 보지 않고 이 목록으로 있음을 정한다
REPO_FILES = {"data/gcode/S01_user_part.gcode", "data/gcode/S01_profile.ini"}


def repo_exists(rel: str) -> bool:
    return rel in REPO_FILES


class Raw(str):
    """CSV 칸에 그대로 쓸 글자 (고장 표본용)."""


DROP = object()  # 고장: 열(키) 자체를 없앰


def drop_column(files: dict[str, bytes], fname: str, col: str) -> None:
    """이름이 fname인 CSV 파일 중 첫 파일에서 열 col을 없앤다."""
    for k in sorted(files):
        if k.endswith("/" + fname):
            lines = files[k].decode("utf-8").split("\n")
            head = lines[0].split(",")
            if col not in head:
                continue
            i = head.index(col)
            files[k] = "\n".join(",".join(c for j, c in enumerate(ln.split(",")) if j != i) if ln else ln
                                 for ln in lines).encode("utf-8")
            return
    raise KeyError((fname, col))


# ---------------------------------------------------------------------------
# 영상
# ---------------------------------------------------------------------------
def png_bytes(seed: int, w: int = 32, h: int = 16, peak: int = 200) -> bytes:
    from PIL import Image
    rng = np.random.default_rng(seed)
    a = rng.integers(0, 40, size=(h, w), dtype=np.uint8)
    a[h // 2, :] = peak
    buf = io.BytesIO()
    Image.fromarray(a, mode="L").save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 정상 표본 모형
# ---------------------------------------------------------------------------
FPS = 120.0
DT = 8_333_333


def _frames(scan_id, layer_idx, t0, n_on, n_off, seed0, laser_off_first=True):
    """하드웨어 트리거 (hw, T14): 레이저 켬 행마다 펄스 번호, 끔 (배경) 행은 빈 칸."""
    rows, imgs = [], {}
    n = n_on + n_off
    pulse = 0
    for i in range(n):
        img = png_bytes(seed0 + i)
        f = f"frames/{i:06d}.png"
        imgs[f] = img
        on = not (laser_off_first and i < n_off)
        rows.append({
            "scan_id": scan_id, "layer_idx": layer_idx, "frame_idx": i, "file": f, "sha256": sha256_bytes(img),
            "t_cam_ns": 1_000_000 + i * DT, "t_host_ns": t0 + (i + 1) * DT, "cam_seq": 1201 + i,
            "exposure_us": 800.0, "gain_db": 0.0, "bit_depth": 8, "pixel_format": "GRAY8", "lossy": False,
            "roi_x0_px": 0, "roi_y0_px": 272, "roi_w_px": 32, "roi_h_px": 16,
            "laser_on": on, "trigger_mode": "hw", "trig_pulse_idx": pulse if on else None, "gate_on": None,
            "dropped_before": 0, "saturated_px": 0, "sensor_temp_c": 41.5,
        })
        pulse += 1 if on else 0
    return rows, imgs


def _pos(scan_id, layer_idx, layer_end, S, z_top, post=False, x=110.0):
    """post=True면 식힌 재측정 첫 줄 (cool_start · cool_end 있음, v1.0: 다른 post 줄에는 없음)."""
    E = S + 83_333_333  # 0.2 mm ÷ 2.4 mm/s [계산]
    off = S - 1_000_000
    base = {"scan_id": scan_id, "x_mm": x, "e_mm": 152.331, "layer_idx": layer_idx, "pass_idx": 0, "mesh_dz_mm": 0.012,
            "clock_offset_ns": None, "acc_x_mm_s2": None, "acc_y_mm_s2": None, "acc_z_mm_s2": None}
    rows = [dict(base, t_ns=layer_end, clock="host", source="cmd", y_mm=90.0, z_mm=z_top - 2.0, feed_mm_s=40.0, event="layer_change")]
    if post:  # 식힌 재측정: cool_start < cool_end ≤ scan_start (T14)
        rows.append(dict(base, t_ns=layer_end + 1_000_000_000, clock="host", source="cmd", y_mm=90.0, z_mm=z_top - 2.0,
                         feed_mm_s=0.0, event="cool_start"))
        rows.append(dict(base, t_ns=S - 1_000_000_000, clock="host", source="cmd", y_mm=90.0, z_mm=z_top - 2.0,
                         feed_mm_s=0.0, event="cool_end"))
    rows.append(dict(base, t_ns=S, clock="host", source="cmd", y_mm=90.0, z_mm=z_top, feed_mm_s=2.4, event="scan_start"))
    for j in range(1, 4):
        rows.append(dict(base, t_ns=1_000_000 + j * DT, clock="mcu", source="report", y_mm=round(90.0 + 0.02 * j, 4), z_mm=z_top,
                         feed_mm_s=2.4, event="none", clock_offset_ns=off, acc_x_mm_s2=12.5, acc_y_mm_s2=-3.1, acc_z_mm_s2=0.8))
    rows.append(dict(base, t_ns=E, clock="host", source="cmd", y_mm=90.2, z_mm=z_top, feed_mm_s=2.4, event="scan_end"))
    return rows


def _refpos(scan_id, layer_idx, t_start, z, x=60.0):
    """움직이며 찍는 기준의 position_log.csv (명세 4절): 스캔 구간 두 행."""
    base = {"scan_id": scan_id or "S00_r00", "clock": "host", "source": "cmd", "x_mm": x, "z_mm": z, "e_mm": 152.331,
            "feed_mm_s": 2.4, "layer_idx": layer_idx if layer_idx is not None else -1, "pass_idx": 0, "mesh_dz_mm": 0.012,
            "clock_offset_ns": None, "acc_x_mm_s2": None, "acc_y_mm_s2": None, "acc_z_mm_s2": None}
    return [dict(base, t_ns=t_start - DT, y_mm=90.0, event="scan_start"),
            dict(base, t_ns=t_start + 2 * DT, y_mm=90.02, event="scan_end")]


# 기준물 (형식 시험용 값, 부록 B.4 · B.5 · LM-T14-3 배정과 같은 꼴). GB-00 = 베드 면 (높이 0, cal 행 없음)
GB_ID, GB_H = "GB-01.2", 1.2008   # 블록게이지 1.2 mm 하나
FG_ID, FG_H = "FG-0.20", 0.203    # 필러게이지 0.20 (feeler)
FG5_ID, FG5_H = "FG-0.50", 0.5021  # 필러게이지 0.50 (아래 단)
BED_ID = "GB-00"
# 층마다 두 단 (낮은 단 h2, 높은 단 h1). 층 Z 1.2 · 1.4 mm에서 0 < h1 − h2 ≤ 3.04, h1 ≤ Z, Z − h2 ≤ 8.0 [계산]
STEPS = {"L000": ((BED_ID, 0.0), (FG5_ID, FG5_H)), "L001": ((FG5_ID, FG5_H), (GB_ID, GB_H)),
         "post": ((FG5_ID, FG5_H), (GB_ID, GB_H))}
PASS_X = {0: 110.0, 1: 130.0}  # 줄 번호별 스캔 X (bed_bare도 같은 X에서 잼)


def _ref(ref_id, kind, scan_id, layer_idx, t_start, seed, marker=True, z=None, gauge=None, pass_idx=None, x=60.0):
    frows, imgs = _frames(scan_id or "S00_r00", layer_idx if layer_idx is not None else -1, t_start - DT, 2, 0, seed, False)
    gid, gh = gauge if gauge else ((FG_ID, FG_H) if kind == "feeler" else (None, None))
    row = {"ref_id": ref_id, "kind": kind, "scan_id": scan_id, "layer_idx": layer_idx, "scan_pass_idx": pass_idx,
           "n_frames": 2, "frames_dir": "frames/",
           "marker_id": "MK01" if marker else None, "marker_x_mm": 60.0 if marker else None, "marker_y_mm": 90.0 if marker else None,
           "t_start_ns": t_start, "calibration_id": CAL,
           "gauge_block_id": gid, "gauge_height_mm": gh,
           "gauge_temp_c": 45.0 if kind == "step_gauge" else None,  # feeler면 선택 (비워 둠)
           "line_peak_pct": 72.0 if (marker or kind == "step_gauge") else None,
           "note": {"bed_marker": "층 끝 마커 MK01 재측정", "step_gauge": "같은 Z 계단 기준물", "feeler": "출력 전 필러게이지",
                    "bed_bare": "출력 전 베드 기준"}.get(kind, "-")}
    out = {"index": [row], "frames": frows, "images": imgs}
    if kind in ("bed_bare", "bed_marker", "ref_tower", "step_gauge", "feeler"):
        out["pos"] = _refpos(scan_id, layer_idx, t_start, z if z is not None else 3.0, x)
    return out


def _meta(lay, layer_idx, layer_z, layer_end, S, dt_text, post=False, pass_idx=0):
    p = f"_p{pass_idx:02d}" if pass_idx else ""
    m = {
        "scan_id": (f"{SR}" if post else f"{SR}_L{layer_idx:03d}") + p, "scan_pass_idx": pass_idx,
        "campaign_id": CAMPAIGN, "session_id": SESSION,
        "source": "virtual", "spec_version": "1.1", "specimen_id": "S01", "specimen_role": "user_gcode", "repeat": 1,
        "datetime": dt_text, "operator": "sim", "notes": "-",
        "timing": "post" if post else "layer", "layer_idx": layer_idx, "layer_count": 2, "layer_z_mm": layer_z,
        "gcode_line_start": 1 + 100 * layer_idx, "gcode_line_end": 100 + 100 * layer_idx,
        "layer_end_t_ns": layer_end, "scan_start_t_ns": S, "wait_after_layer_s": (S - layer_end) / 1e9,
        "pause_added_s": 0.0 if post else 35.0, "layer_time_s": None if post else 45.0,
        "scan_z_hop_mm": 2.0, "scan_axis": "+Y", "scan_x_mm": PASS_X[pass_idx], "scan_y0_mm": 90.0,
        "process": "FDM", "printer_model": "sovol-sv08", "printer_kinematics": "corexy", "bed_motion": "fixed",
        "z_drive": "belt", "z_motor_count": 4, "z_level_method": "qgl", "probe_type": "inductive_pressure",
        "firmware": "sovol-klipper-unknown", "firmware_fork": "vendor", "mesh_enabled": True,
        "control_group": "none", "enclosure": True, "slicer_profile_file": "data/gcode/S01_profile.ini",
        "gcode_file": "data/gcode/S01_user_part.gcode",
        "gcode_sha256": "3f5a0c1e9b7d2a4f6e8c0b1d3f5a7c9e1b3d5f7a9c1e3b5d7f9a1c3e5b7d9f1a",
        "material": "PLA", "color": "gray", "translucency": "opaque", "filament_lot": "sim",
        "nozzle_dia_mm": 0.4, "layer_h_mm": 0.2, "top_layers": 4, "infill_angle_deg": 45.0, "step_edge_angle_deg": None,
        "nozzle_temp_c": 30.0 if post else 205.0, "bed_temp_c": 25.0 if post else 60.0, "room_temp_c": 22.4,
        "room_humidity_pct": 45.0, "camera_temp_c": 38.0, "laser_temp_c": 40.0,
        "specimen_temp_c": 23.1 if post else 55.0, "part_fan_pct": 100.0, "ambient_light": "enclosure_dark",
        # v1.0: 줄마다 bed_bare (줄 0 → REF-BED-001, 줄 1 → REF-BED-002)
        "bed_ref_id": f"REF-BED-{pass_idx + 1:03d}", "z_offset_mm": -0.15, "zero_ref_method": "step_gauge",
        "bed_mesh_file": "printer/bed_mesh.json", "thermal_state": "cooled" if post else "in_process",
        "paired_scan_id": f"{SR}_L001{p}" if post else None, "cool_wait_s": (S - layer_end) / 1e9 if post else None,
        "tolerance_mm": 0.20, "slicer_name": "SLICER-A 0.0", "gcode_flavor": "klipper", "firmware_name": "klipper",
        "firmware_version": "unknown", "host_software": "moonraker unknown", "layer_macro_version": "LM-T14-3",
        "shaper_freq_x_hz": 48.6, "shaper_freq_y_hz": None, "trigger_pin": "cam_trig", "trigger_period_s": 0.008333,
        "sensor_model": "M54-nozzle-line-v1", "cam_model": "OV9281", "cam_shutter": "global", "cam_interface": "sim",
        "cam_pixel_um": 3.0, "cam_res_w_px": 1280, "cam_res_h_px": 800, "lens_f_mm": 8.0, "lens_f_number": 4.0,
        "lens_focus_locked": True, "wd_mm": 50.0, "magnification": 0.19, "laser_wavelength_nm": 450.0,
        "laser_power_mw": 1.0, "laser_power_pct": 60.0, "laser_class": "2", "triang_angle_deg": 30.0,
        "filter_center_nm": 450.0, "filter_fwhm_nm": 10.0, "exposure_set_us": 800.0, "gain_set_db": 0.0,
        "frame_avg_n": 1, "scan_speed_mm_s": 2.4, "scan_pitch_mm": 0.02, "scan_length_mm": 0.2, "fps": FPS,
        "n_frames": 12, "raw_saved": True, "proc_time_s": None, "acq_id": "ACQ-2026-11-20-A",
        "calibration_id": CAL, "fid_id": None, "frames_doc_version": "C4-1.0", "software_git": "ff4b01b",
        "files_sha256": AUTO, "sim_version": "sim-0.1.0", "sim_seed": 20261120, "injected_factors": ["MF-SYN-01"],
        "blind": False,
    }
    return m


def normal_model() -> dict:
    """최소 정상 캠페인 (명세 v1.0, LM-T14-3 꼴): 세션 1, 시편·반복 1, 층 2 + post.

    마지막 층과 post는 두 줄 (`L001_p01` · `post_p01`, 스캔 X 130), 줄마다 bed_bare (REF-BED-001 · 002),
    층마다 첫 줄 스캔에 베드 마커 1개와 두 단 계단 기준물 2개 (그 층 모든 줄 뒤 같은 Z). ref_id는 세션 안 순번 001부터.
    """
    scans = {}
    seed = 1000
    # (폴더, 층, 층 Z, 층 끝 ns, 대기 s, datetime, post, 줄). 층 Z는 형식 시험용 값 (두 단 높이보다 높게)
    plan = [("L000", 0, 1.2, 100_000_000_000, 15, "2026-11-20T14:20:00+09:00", False, 0),
            ("L001", 1, 1.4, 300_000_000_000, 15, "2026-11-20T14:24:00+09:00", False, 0),
            ("L001_p01", 1, 1.4, 300_000_000_000, 20, "2026-11-20T14:24:05+09:00", False, 1),
            ("post", 1, 1.4, 300_000_000_000, 1800, "2026-11-20T14:57:00+09:00", True, 0),
            ("post_p01", 1, 1.4, 300_000_000_000, 1810, "2026-11-20T14:57:10+09:00", True, 1)]
    n_mrk = n_stg = 0
    for lay, li, z, le, wait_s, dtt, post, pidx in plan:
        S = le + wait_s * 1_000_000_000
        meta = _meta(lay, li, z, le, S, dtt, post, pidx)
        sid = meta["scan_id"]
        frows, imgs = _frames(sid, li, S, 10, 2, seed)
        seed += 100
        scans[lay] = {"meta": meta, "frames": frows, "images": imgs, "refs": {},
                      "pos": _pos(sid, li, le, S, z + 2.0, post and pidx == 0, PASS_X[pidx])}
        if pidx == 0:  # 층에 매인 기준은 그 층 첫 줄 스캔과 짝 (명세 4절)
            n_mrk += 1
            mrk = f"REF-MRK-{n_mrk:03d}"
            scans[lay]["refs"][mrk] = _ref(mrk, "bed_marker", sid, li, frows[0]["t_host_ns"] - 5_000_000_000, seed)
        seed += 100
    # 두 단 (LM-T14-3: 그 층 모든 줄 → 낮은 단 → 높은 단, Z를 움직이지 않음). 스캔 구간 Z = 층 Z + 2.0 (D-16)
    for lay, last in (("L000", "L000"), ("L001", "L001_p01"), ("post", "post_p01")):
        sc, m = scans[lay], scans[lay]["meta"]
        t0 = scans[last]["frames"][-1]["t_host_ns"]
        for k, g in enumerate(STEPS[lay]):
            n_stg += 1
            stg = f"REF-STG-{n_stg:03d}"
            sc["refs"][stg] = _ref(stg, "step_gauge", m["scan_id"], m["layer_idx"], t0 + (k + 1) * 1_000_000_000, seed,
                                   marker=False, z=m["layer_z_mm"] + 2.0, gauge=g)
            seed += 50
    # 출력 전 기준: 줄마다 bed_bare (같은 X), 필러게이지. 층 번호 -1 (출력 전 부호)
    sref = {"REF-BED-001": _ref("REF-BED-001", "bed_bare", None, -1, 50_000_000_000, 9000, marker=False, pass_idx=0, x=PASS_X[0]),
            "REF-BED-002": _ref("REF-BED-002", "bed_bare", None, -1, 52_000_000_000, 9050, marker=False, pass_idx=1, x=PASS_X[1]),
            "REF-FLR-001": _ref("REF-FLR-001", "feeler", None, -1, 60_000_000_000, 9100, marker=False)}
    calrow = {"cal_id": CAL, "kind": None, "created": None, "record_type": "image", "target_type": None, "target_rows": None,
              "target_cols": None,
              "target_square_mm": None, "target_marker_mm": None, "target_dict": None, "target_flatness_um": None,
              "pose_idx": 0, "image_file": None, "laser_on": False, "exposure_us": 800.0, "cmd_z_mm": None, "cmd_move_mm": None,
              "feature_id": None, "feature_x_mm": None, "feature_y_mm": None, "nozzle_touch_z_mm": None,
              "gauge_nominal_mm": None, "gauge_measured_mm": None, "gauge_u_um": None,
              "gauge_block_id": None, "gauge_block_height_mm": None, "gauge_block_u_um": None,
              "material_offset_um": None, "material_offset_u_um": None, "material": None, "color": None, "temp_c": 22.4,
              "result_file": None, "valid_from": "2026-11-20T12:00:00+09:00", "valid_until": "2026-12-20T12:00:00+09:00",
              "invalidated_by": "none"}
    rf = f"config/calibration/{CAL}/"
    man = [
        dict(calrow, kind="D1", created="2026-11-20T10:15:00+09:00", target_type="charuco", target_rows=6, target_cols=9,
             target_square_mm=1.5, target_marker_mm=1.1, target_dict="DICT_4X4_50", target_flatness_um=5.0,
             image_file="d1/view_000.png", result_file=rf + "camera_intrinsics.yaml"),
        dict(calrow, kind="D2", created="2026-11-20T10:40:00+09:00", target_type="flat_plate", target_flatness_um=5.0,
             image_file="d2/pose_00_off.png", cmd_z_mm=1.0, result_file=rf + "laser_plane.yaml"),
        dict(calrow, kind="D2", created="2026-11-20T10:40:05+09:00", target_type="flat_plate", target_flatness_um=5.0,
             image_file="d2/pose_00_on.png", laser_on=True, cmd_z_mm=1.0, result_file=rf + "laser_plane.yaml"),
        dict(calrow, kind="D2", created="2026-11-20T10:41:00+09:00", target_type="flat_plate", target_flatness_um=5.0,
             pose_idx=1, image_file="d2/pose_01_off.png", cmd_z_mm=2.0, result_file=rf + "laser_plane.yaml"),
        dict(calrow, kind="D2", created="2026-11-20T10:41:05+09:00", target_type="flat_plate", target_flatness_um=5.0,
             pose_idx=1, image_file="d2/pose_01_on.png", laser_on=True, cmd_z_mm=2.0, result_file=rf + "laser_plane.yaml"),
        dict(calrow, kind="D3", created="2026-11-20T11:00:00+09:00", target_type="none", image_file="d3/move_00.png",
             laser_on=True, cmd_move_mm=0.02, result_file=rf + "scan_axis.yaml"),
        dict(calrow, kind="D4", created="2026-11-20T11:10:00+09:00", target_type="coord_plate", image_file="d4/plate_scan/p02_03.png",
             laser_on=True, feature_id="P02_03", feature_x_mm=104.0, feature_y_mm=96.0,
             result_file=rf + "nozzle_sensor.yaml"),
        # 노즐 접촉 기록: 영상 없는 행 (record_type = nozzle_touch, laser_on false, 노출 빈 칸)
        dict(calrow, kind="D4", created="2026-11-20T11:12:00+09:00", record_type="nozzle_touch", target_type="coord_plate",
             exposure_us=None, feature_id="P02_03", feature_x_mm=104.0, feature_y_mm=96.0, nozzle_touch_z_mm=2.03,
             result_file=rf + "nozzle_sensor.yaml"),
        dict(calrow, kind="D5", created="2026-11-20T11:30:00+09:00", target_type="filler_gauge", image_file="d5/gauge_0p20/g_000.png",
             laser_on=True, gauge_nominal_mm=0.2, gauge_measured_mm=FG_H, gauge_u_um=1.0, gauge_block_id=FG_ID, temp_c=22.5,
             result_file=rf + "verification.yaml"),
        # 계단 기준물 (D-16): 윗면 영상 + 블록 높이 마이크로미터 실측
        dict(calrow, kind="D5", created="2026-11-20T11:40:00+09:00", target_type="step_gauge", pose_idx=1,
             image_file="d5/step_gauge/gb_01_000.png", laser_on=True, gauge_block_id=GB_ID, gauge_block_height_mm=GB_H,
             gauge_block_u_um=2.0, result_file=rf + "verification.yaml"),
        dict(calrow, kind="D5", created="2026-11-20T11:42:00+09:00", record_type="micrometer", target_type="step_gauge", pose_idx=1,
             exposure_us=None, gauge_block_id=GB_ID, gauge_block_height_mm=GB_H, gauge_block_u_um=2.0,
             result_file=rf + "verification.yaml"),
        # 재료 치우침 조각: 두께 실측 (영상 없는 행). 재료·색 = 스캔 meta.material · meta.color (v1.0)
        dict(calrow, kind="D5", created="2026-11-20T11:50:00+09:00", record_type="micrometer", target_type="material_sample",
             pose_idx=2, exposure_us=None, material_offset_um=-6.2, material_offset_u_um=2.0, material="PLA", color="gray",
             result_file=rf + "verification.yaml"),
        # 아래 단으로 쓰는 필러게이지 0.50 (v1.0, LM-T14-3)
        dict(calrow, kind="D5", created="2026-11-20T11:35:00+09:00", target_type="filler_gauge", pose_idx=3,
             image_file="d5/gauge_0p50/g_000.png", laser_on=True, gauge_nominal_mm=0.5, gauge_measured_mm=FG5_H, gauge_u_um=1.0,
             gauge_block_id=FG5_ID, temp_c=22.5, result_file=rf + "verification.yaml"),
    ]
    res = []
    for k, f, extra in (("D1", "camera_intrinsics", {"reproj_rms_px": 0.12}), ("D2", "laser_plane", {"plane_rms_um": 3.0}),
                        ("D3", "scan_axis", {}), ("D4", "nozzle_sensor", {}), ("D5", "verification", {})):
        res.append(dict({"cal_id": CAL, "kind": k, "result_file": rf + f + ".yaml", "reproj_rms_px": None, "plane_rms_um": None,
                         "valid_from": "2026-11-20T12:00:00+09:00", "valid_until": "2026-12-20T12:00:00+09:00",
                         "invalidated_by": "none"}, **extra))
    calimgs = {r["image_file"]: png_bytes(5000 + i) for i, r in enumerate(man) if r["image_file"]}
    rep = {"study_id": "MSA-01", "operator": "sim_A", "remount": False, "rehome": True, "interval_s": 60.0,
           "session_id": SESSION, "scan_id": None}
    design = [
        dict(rep, specimen_id="S01", part_idx=0, repeat_idx=1, run_order=3, noise_seed=1001, truth_id="T-S01"),
        dict(rep, specimen_id="S01", part_idx=0, repeat_idx=2, run_order=2, noise_seed=1002, truth_id="T-S01"),
        dict(rep, specimen_id="S02", part_idx=1, repeat_idx=1, run_order=4, noise_seed=1003, truth_id="T-S02"),
        dict(rep, specimen_id="S02", part_idx=1, repeat_idx=2, run_order=1, noise_seed=1004, truth_id="T-S02"),
    ]
    executed = copy.deepcopy(design)
    for r, s in zip(executed, ("S01_r01_L000", "S01_r01_L001", "S02_r01_L000", "S02_r01")):
        r["scan_id"] = s
    return {
        "campaign": CAMPAIGN,
        "cal": {CAL: {"cal_manifest.csv": man, "cal_results.csv": res, "images": calimgs}},
        "msa": {"MSA-01": {"design.csv": design, "design_executed.csv": executed}},
        "sessions": {SESSION: {"printer": {"bed_mesh.json": b'{\n  "mesh": [[0.0, 0.012], [0.01, 0.02]]\n}\n'},
                               "refs": sref, "scans": {SR: scans}}},
    }


# ---------------------------------------------------------------------------
# 직렬화
# ---------------------------------------------------------------------------
def fmt(v) -> str:
    if isinstance(v, Raw):
        return str(v)
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v) if math.isfinite(v) else ("inf" if v > 0 else "-inf")
    return str(v)


def clone(model: dict) -> dict:
    """표본 모형 깊은 복사 (pickle이 copy.deepcopy보다 빠름)."""
    return pickle.loads(pickle.dumps(model, protocol=pickle.HIGHEST_PROTOCOL))


_CSV_CACHE: dict[tuple, bytes] = {}


def csv_bytes(rows: list[dict], cols: list[str]) -> bytes:
    """행 → CSV 바이트. repr이 같으면 출력도 같으므로 repr을 열쇠로 다시 씀."""
    key = (repr(rows), tuple(cols))
    hit = _CSV_CACHE.get(key)
    if hit is None:
        hit = _CSV_CACHE[key] = _csv_bytes(rows, cols)
        if len(_CSV_CACHE) > 4096:
            _CSV_CACHE.clear()
    return hit


def _csv_bytes(rows: list[dict], cols: list[str]) -> bytes:
    lines = [",".join(cols)]
    for r in rows:
        cells = []
        for c in cols:
            s = fmt(r.get(c))
            if any(ch in s for ch in ',"\n'):
                s = '"' + s.replace('"', '""') + '"'
            cells.append(s)
        lines.append(",".join(cells))
    return ("\n".join(lines) + "\n").encode("utf-8")


def serialize(model: dict, file_cols: dict) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for cid, c in model["cal"].items():
        b = f"calibration/{cid}"
        for fn in ("cal_manifest.csv", "cal_results.csv"):
            if fn in c:
                out[f"{b}/{fn}"] = csv_bytes(c[fn], file_cols[fn])
        for rel, img in c["images"].items():
            out[f"{b}/{rel}"] = img
    for sid, s in model["msa"].items():
        for fn, rows in s.items():
            out[f"msa/{sid}/{fn}"] = csv_bytes(rows, file_cols[fn])

    def put_ref(base, ref):
        out[f"{base}/ref_index.csv"] = csv_bytes(ref["index"], file_cols["ref_index.csv"])
        out[f"{base}/frames_index.csv"] = csv_bytes(ref["frames"], file_cols["frames_index.csv"])
        if "pos" in ref:
            out[f"{base}/position_log.csv"] = csv_bytes(ref["pos"], file_cols["position_log.csv"])
        for rel, img in ref["images"].items():
            out[f"{base}/{rel}"] = img

    for sess, s in model["sessions"].items():
        sb = f"sessions/{sess}"
        for rel, data in s["printer"].items():
            out[f"{sb}/printer/{rel}"] = data
        for rid, ref in s["refs"].items():
            put_ref(f"{sb}/reference/{rid}", ref)
        for sr, layers in s["scans"].items():
            for lay, sc in layers.items():
                b = f"{sb}/{sr}/{lay}"
                files = {"frames_index.csv": csv_bytes(sc["frames"], file_cols["frames_index.csv"]),
                         "position_log.csv": csv_bytes(sc["pos"], file_cols["position_log.csv"])}
                for rel, img in sc["images"].items():
                    files[rel] = img
                for rid, ref in sc["refs"].items():
                    sub = {}
                    rb = f"reference/{rid}"
                    sub[f"{rb}/ref_index.csv"] = csv_bytes(ref["index"], file_cols["ref_index.csv"])
                    sub[f"{rb}/frames_index.csv"] = csv_bytes(ref["frames"], file_cols["frames_index.csv"])
                    if "pos" in ref:
                        sub[f"{rb}/position_log.csv"] = csv_bytes(ref["pos"], file_cols["position_log.csv"])
                    for rel, img in ref["images"].items():
                        sub[f"{rb}/{rel}"] = img
                    files.update(sub)
                meta = dict(sc["meta"])
                if meta.get("files_sha256") == AUTO:
                    meta["files_sha256"] = {k: sha256_bytes(v) for k, v in sorted(files.items())}
                files["meta.json"] = (json.dumps(meta, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
                for rel, data in files.items():
                    out[f"{b}/{rel}"] = data
    return out


def write_tree(files: dict[str, bytes], root: Path) -> None:
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


# ---------------------------------------------------------------------------
# 표본 안 필드 위치
# ---------------------------------------------------------------------------
def csv_locations(model: dict, group: str):
    """(행 dict, 파일 이름) 목록. 그 묶음의 모든 행."""
    out = []
    if group == "frame":
        for s in model["sessions"].values():
            for layers in s["scans"].values():
                for sc in layers.values():
                    out += [(r, "frames_index.csv", sc) for r in sc["frames"]]
    elif group == "pos":
        for s in model["sessions"].values():
            for layers in s["scans"].values():
                for sc in layers.values():
                    out += [(r, "position_log.csv", sc) for r in sc["pos"]]
    elif group == "cal":
        for c in model["cal"].values():
            for fn in ("cal_manifest.csv", "cal_results.csv"):
                out += [(r, fn, None) for r in c.get(fn, [])]
    elif group == "ref":
        for s in model["sessions"].values():
            for ref in s["refs"].values():
                out += [(r, "ref_index.csv", None) for r in ref["index"]]
            for layers in s["scans"].values():
                for sc in layers.values():
                    for ref in sc["refs"].values():
                        out += [(r, "ref_index.csv", sc) for r in ref["index"]]
    elif group == "rep":
        for st in model["msa"].values():
            for fn, rows in st.items():
                out += [(r, fn, None) for r in rows]
    elif group == "meta":
        for s in model["sessions"].values():
            for layers in s["scans"].values():
                for sc in layers.values():
                    out.append((sc["meta"], "meta.json", sc))
    return out


def first_present(model, field):
    group, col = field.split(".", 1)
    for row, fn, sc in csv_locations(model, group):
        if col in row and row[col] is not None:
            return row, fn, sc
    for row, fn, sc in csv_locations(model, group):
        if col in row:
            return row, fn, sc
    return None


# ---------------------------------------------------------------------------
# 자동 고장
# ---------------------------------------------------------------------------
def _num(s: str):
    return int(s) if s.lstrip("-").isdigit() else float(s)


def dtype_bad(dtype: str, json_mode: bool):
    if json_mode:
        return {"int": 1.5, "int64": 1e9, "float": "1.0", "bool": "true", "str": 123, "list": "x", "dict": []}[dtype]
    return {"int": Raw("1.5"), "int64": Raw("1e9"), "float": Raw("abc"), "bool": Raw("TRUE")}.get(dtype)


def auto_faults(fields: list[dict], rules: dict) -> list[tuple]:
    """(이름, 기대 규칙 ID, 필드, 값, 앞조건 패치)."""
    out = []
    for f in fields:
        if f["group"] == "truth" or f["excluded"] == "true":
            continue
        name, dt = f["field"], f["dtype"]
        jm = f["group"] == "meta"
        # 필수 비우기
        rid = f"REQ.{name}"
        if rid in rules and f["req"] in ("필수", "조건부"):
            pre = {}
            if name == "meta.step_edge_angle_deg":
                pre = {"specimen_role": "aux_step"}
            if name == "frame.gate_on":
                pre = {"trigger_mode": "gate"}  # 정상 표본은 hw라 조건을 참으로 만듦
            out.append((f"비움 {name}", rid, name, None if jm else Raw(""), pre))
        elif rid in rules and f["req"] == "선택":
            out.append((f"열·키 없앰 {name}", rid, name, DROP, {}))
        # 자료형
        bad = dtype_bad(dt, jm)
        if bad is not None:
            out.append((f"자료형 {name}", f"DTYPE.{name}", name, bad, {}))
        # 범위
        if f["min"] or f["max"]:
            isint = dt in ("int", "int64")
            for side in ("min", "max"):
                b, op = f[side], f[side + "_op"]
                if not b:
                    continue
                bv = _num(b)
                d = 1 if isint else 0.01 * max(1.0, abs(float(bv)))
                if op == "<":
                    v = bv
                elif side == "min":
                    v = bv - d
                else:
                    v = bv + d
                v = int(v) if isint else float(v)
                out.append((f"범위 {side} {name}", f"RANGE.{name}", name, v if jm else Raw(fmt(v)), {}))
        elif f"RANGE.{name}" in rules and rules[f"RANGE.{name}"]["params"] == "finite":
            out.append((f"무한 {name}", f"RANGE.{name}", name, float("inf") if jm else Raw("inf"), {}))
        # 허용 값
        rid = f"ENUM.{name}"
        if rid in rules and rules[rid]["severity"] == "ERROR" and rules[rid]["params"] != "true,false":
            v = {"int": 9, "int64": 9, "float": 0.25}.get(dt, "zzz")
            out.append((f"허용 밖 {name}", rid, name, v if jm else Raw(fmt(v)), {}))
        # 정규식
        rid = f"REGEX.{name}"
        if rid in rules:
            p = rules[rid]["params"]
            v = "   " if p == r"\S" else "BAD!"
            if dt == "list":
                v = ["BAD"]
            out.append((f"형식 {name}", rid, name, v if jm else Raw(v), {}))
    return out


def apply_field(model, field, value, pre=None):
    m = clone(model)
    loc = first_present(m, field)
    if loc is None:
        raise KeyError(field)
    row, fn, sc = loc
    if pre:
        row.update(pre)
    row[field.split(".", 1)[1]] = value
    return m


# ---------------------------------------------------------------------------
# 손 고장 (§6.3 후보에서 고름)
# ---------------------------------------------------------------------------
def _scan(m, lay="L000"):
    return m["sessions"][SESSION]["scans"][SR][lay]


def _file_edit(path_end, fn):
    def f(files):
        k = next(k for k in files if k.endswith(path_end))
        files[k] = fn(files[k])
    return f


def hand_faults() -> list[tuple]:
    """(이름, 기대 규칙 ID, 모형 고침 함수 또는 None, 바이트 고침 함수 또는 None)."""
    H = []

    def mod(name, rid, fm=None, fb=None):
        H.append((name, rid, fm, fb))

    L0 = f"sessions/{SESSION}/{SR}/L000"
    mod("scan_id가 파일마다 다름", "X-FRM-01", lambda m: _scan(m)["frames"][3].update(scan_id="S01_r01_L009"))
    mod("층 폴더 L004인데 meta.layer_idx 1", "FILE-05",
        lambda m: m["sessions"][SESSION]["scans"][SR].update(L004=m["sessions"][SESSION]["scans"][SR].pop("L001")))
    mod("post/ 없음", "FILE-04", lambda m: m["sessions"][SESSION]["scans"][SR].pop("post"))
    mod("post 스캔 둘", "FILE-04", lambda m: _scan(m, "L001")["meta"].update(timing="post", thermal_state="cooled"))
    mod("paired_scan_id가 마지막 층이 아님", "X-MET-33", lambda m: _scan(m, "post")["meta"].update(paired_scan_id=f"{SR}_L000"))
    mod("세션 안 z_offset_mm 다름", "X-MET-27", lambda m: _scan(m, "L001")["meta"].update(z_offset_mm=-0.1))
    mod("bed_ref_id가 가리키는 기준이 bed_bare 아님", "X-MET-25",
        lambda m: m["sessions"][SESSION]["refs"]["REF-BED-001"]["index"][0].update(kind="background"))
    mod("tolerance_mm 0.25", "RANGE.meta.tolerance_mm", lambda m: _scan(m)["meta"].update(tolerance_mm=0.25))
    mod("wait_after_layer_s 식 불일치", "X-MET-13", lambda m: _scan(m)["meta"].update(wait_after_layer_s=16.0))
    mod("n_frames ≠ 행 수", "X-MET-45", lambda m: _scan(m)["meta"].update(n_frames=13))
    mod("프레임 파일 하나 지움", "FILE-06", None, lambda fs: fs.pop(f"{L0}/frames/000005.png"))
    mod("PNG 한 바이트 바꿈", "FILE-07", None,
        _file_edit("L000/frames/000004.png", lambda b: b[:-20] + bytes([b[-20] ^ 0xFF]) + b[-19:]))
    mod("files_sha256 불일치", "FILE-10",
        lambda m: _scan(m)["meta"].update(files_sha256={k: "0" * 64 for k in ["frames_index.csv"]}))
    mod("frame_idx 건너뜀", "X-FRM-03", lambda m: _scan(m)["frames"][3].update(frame_idx=4))
    mod("t_host_ns 감소", "X-FRM-06", lambda m: _scan(m)["frames"][5].update(t_host_ns=_scan(m)["frames"][4]["t_host_ns"] - 1))
    mod("scan_start 0개", "X-POS-09", lambda m: _scan(m)["pos"][1].update(event="none"))
    mod("scan_start 2개", "X-POS-09", lambda m: _scan(m)["pos"][2].update(event="scan_start"))
    mod("노출이 스캔 안에서 다름", "X-FRM-09", lambda m: _scan(m)["frames"][6].update(exposure_us=801.0))
    mod("laser_on = false 행 없음", "X-FRM-15", lambda m: [r.update(laser_on=True) for r in _scan(m)["frames"]])
    mod("캠페인 VC인데 source = real", "X-MET-02", lambda m: _scan(m)["meta"].update(source="real"))
    mod("source = virtual인데 sim_seed 없음", "REQ.meta.sim_seed", lambda m: _scan(m)["meta"].update(sim_seed=None))
    mod("timing layer인데 thermal_state cooled", "X-MET-05", lambda m: _scan(m)["meta"].update(thermal_state="cooled"))
    mod("결측을 NaN으로 씀", "CSV-05", lambda m: _scan(m)["frames"][2].update(saturated_px=Raw("NaN")))
    mod("TRUE 대문자", "DTYPE.frame.lossy", lambda m: _scan(m)["frames"][2].update(lossy=Raw("TRUE")))
    mod("BOM", "CSV-01", None, _file_edit("L000/frames_index.csv", lambda b: b"\xef\xbb\xbf" + b))
    mod("열 순서 바꿈", "CSV-03", None, _file_edit("L000/frames_index.csv", _swap_cols01))
    mod("모르는 열", "CSV-04", None, _file_edit("L000/position_log.csv", _add_col))
    mod("meta.json에 truth_judgement 키", "LEAK-01", lambda m: _scan(m)["meta"].update(truth_judgement="pass"))
    mod("data/raw 안 truth.json", "LEAK-02", None, lambda fs: fs.update({"truth.json": b"{}"}))
    mod("int64에 지수 표기", "DTYPE.frame.t_host_ns", lambda m: _scan(m)["frames"][2].update(t_host_ns=Raw("4.99e9")))
    mod("머리글 묶음 접두어", "CSV-06", None,
        _file_edit("L000/frames_index.csv", lambda b: b.replace(b"scan_id,layer_idx", b"frame.scan_id,layer_idx", 1)))
    mod("meta.json 키에 접두어", "JSON-02", lambda m: _scan(m)["meta"].update({"meta.scan_id": _scan(m)["meta"].pop("scan_id")}))
    mod("줄 끝 CRLF", "CSV-02", None, _file_edit("L000/position_log.csv", lambda b: b.replace(b"\n", b"\r\n")))
    mod("게인이 스캔 안에서 다름", "X-FRM-10", lambda m: _scan(m)["frames"][6].update(gain_db=1.0))
    mod("bed_bare가 첫 층보다 늦음", "X-REF-02",
        lambda m: m["sessions"][SESSION]["refs"]["REF-BED-001"]["index"][0].update(t_start_ns=150_000_000_000))
    mod("교정 ID가 캠페인에 없음", "X-MET-48", lambda m: _scan(m)["meta"].update(calibration_id="CAL-2026-11-21-A"))
    mod("datetime이 교정 유효 기간 밖", "X-MET-49", lambda m: _scan(m)["meta"].update(datetime="2027-01-01T00:00:00+09:00"))
    mod("layer_z_mm가 층 따라 안 커짐", "X-MET-07", lambda m: _scan(m, "L001")["meta"].update(layer_z_mm=0.2))
    mod("기준 n_frames ≠ 행 수", "X-REF-05", lambda m: next(iter(_scan(m)["refs"].values()))["index"][0].update(n_frames=3))
    mod("D2 자세에 레이저 끔 행 없음", "X-CAL-05", lambda m: m["cal"][CAL]["cal_manifest.csv"].pop(1))
    mod("run_order 중복", "X-REP-04", lambda m: m["msa"]["MSA-01"]["design.csv"][0].update(run_order=2))
    mod("cal_id가 폴더 이름과 다름", "FILE-11", lambda m: m["cal"][CAL]["cal_manifest.csv"][0].update(cal_id="CAL-2026-11-20-B"))
    mod("dropped_before 불일치", "X-FRM-17", lambda m: _scan(m)["frames"][4].update(dropped_before=1))
    mod("스캔 폴더에 모르는 파일", "FILE-01", None, lambda fs: fs.update({f"{L0}/notes.txt": b"x"}))
    mod("meta.json 키 빠짐", "JSON-03", lambda m: _scan(m)["meta"].pop("laser_temp_c"))
    mod("meta.json 모르는 키", "JSON-01", lambda m: _scan(m)["meta"].update(foo=1))
    mod("frame.file 번호 ≠ frame_idx", "X-FRM-04", lambda m: _scan(m)["frames"][4].update(file="frames/000005.png"))
    mod("scan_start_t_ns ≠ 위치 로그", "X-MET-12", lambda m: _scan(m)["meta"].update(scan_start_t_ns=_scan(m)["meta"]["scan_start_t_ns"] + 1))
    mod("스캔 중 압출", "X-POS-06", lambda m: _scan(m)["pos"][3].update(e_mm=152.5))
    mod("lossy true인데 GRAY8", "X-FRM-12", lambda m: _scan(m)["frames"][3].update(lossy=True))
    mod("JSON 문법 오류", "JSON-04", None, _file_edit("L000/meta.json", lambda b: b[:-3]))
    mod("data/raw 안 _truth 폴더", "LEAK-02", None, lambda fs: fs.update({"_truth/x.json": b"{}"}))
    mod("대조군인데 층별 스캔", "X-MET-19", lambda m: _scan(m)["meta"].update(control_group="dwell_only"))
    mod("noise_seed 중복", "X-REP-06", lambda m: m["msa"]["MSA-01"]["design.csv"][1].update(noise_seed=1001))
    mod("bed_marker 짝 기준 없음", "X-MET-29", lambda m: (_scan(m)["meta"].update(zero_ref_method="bed_marker"), _scan(m)["refs"].clear()))
    mod("세션 bed_bare 없음", "X-REF-02", lambda m: m["sessions"][SESSION]["refs"].clear())
    mod("scan_speed ≠ fps × pitch", "X-MET-44", lambda m: _scan(m)["meta"].update(scan_speed_mm_s=2.5))
    mod("firmware ≠ name-version", "X-MET-36", lambda m: _scan(m)["meta"].update(firmware="klipper"))
    mod("cool_wait ≠ wait_after_layer", "X-MET-34", lambda m: _scan(m, "post")["meta"].update(cool_wait_s=1700.0))
    mod("raw_saved false인데 영상 있음", "FILE-15", lambda m: _scan(m)["meta"].update(raw_saved=False))
    mod("메시 파일 없음", "FILE-14", lambda m: m["sessions"][SESSION]["printer"].clear())
    mod("ROI가 센서 폭을 넘음", "X-FRM-13", lambda m: _scan(m)["meta"].update(cam_res_w_px=16))
    mod("영상 크기 ≠ ROI", "FILE-08", lambda m: [r.update(roi_w_px=33) for r in _scan(m)["frames"]])
    mod("8비트 PNG인데 bit_depth 10", "FILE-09", lambda m: [r.update(bit_depth=10, pixel_format="GRAY10") for r in _scan(m)["frames"]])
    mod("조건 거짓인데 값 있음 (host 행 clock_offset)", "CROSS-EMPTY.pos.clock_offset_ns",
        lambda m: _scan(m)["pos"][0].update(clock_offset_ns=5))
    H.extend(_more_hand_faults())
    return H


def _more_hand_faults() -> list[tuple]:
    """구현한 손 규칙마다 고장 표본이 하나 이상 있게 더한 것."""
    H = []

    def mod(name, rid, fm=None, fb=None):
        H.append((name, rid, fm, fb))

    S = lambda m, lay="L000": _scan(m, lay)  # noqa: E731
    fr = lambda m: S(m)["frames"]  # noqa: E731
    po = lambda m: S(m)["pos"]  # noqa: E731
    me = lambda m, lay="L000": S(m, lay)["meta"]  # noqa: E731
    man = lambda m: m["cal"][CAL]["cal_manifest.csv"]  # noqa: E731
    res = lambda m: m["cal"][CAL]["cal_results.csv"]  # noqa: E731
    sref = lambda m, lay="L000": next(iter(S(m, lay)["refs"].values()))["index"][0]  # noqa: E731
    des = lambda m, fn="design.csv": m["msa"]["MSA-01"][fn]  # noqa: E731
    L0 = f"sessions/{SESSION}/{SR}/L000"

    def setall(rows, **kw):
        for r in rows:
            r.update(kw)

    mod("frame.layer_idx가 파일 안에서 다름", "X-FRM-02", lambda m: fr(m)[3].update(layer_idx=1))
    mod("t_cam_ns가 늘지 않음", "X-FRM-05", lambda m: fr(m)[4].update(t_cam_ns=fr(m)[3]["t_cam_ns"]))
    mod("cam_seq가 늘지 않음", "X-FRM-07", lambda m: fr(m)[4].update(cam_seq=fr(m)[3]["cam_seq"]))
    mod("노출 > 1e6 ÷ fps", "X-FRM-08", lambda m: (setall(fr(m), exposure_us=9000.0), me(m).update(exposure_set_us=9000.0)))
    mod("pixel_format이 스캔 안에서 다름", "X-FRM-11", lambda m: fr(m)[4].update(pixel_format="GRAY10"))
    mod("ROI가 센서 높이를 넘음", "X-FRM-14", lambda m: me(m).update(cam_res_h_px=100))
    mod("trigger_mode가 스캔 안에서 다름", "X-FRM-16", lambda m: fr(m)[4].update(trigger_mode="sw"))
    mod("saturated_px > ROI 화소 수", "X-FRM-18", lambda m: fr(m)[4].update(saturated_px=1000))
    mod("pos.scan_id ≠ meta.scan_id", "X-POS-01", lambda m: po(m)[2].update(scan_id="S01_r01_L009"))
    mod("같은 clock·source에서 t_ns 안 늚", "X-POS-02", lambda m: po(m)[3].update(t_ns=po(m)[2]["t_ns"]))
    mod("스캔 중 X 이동", "X-POS-03", lambda m: po(m)[3].update(x_mm=110.5))
    mod("스캔 중 Y가 단조 아님", "X-POS-04", lambda m: po(m)[3].update(y_mm=89.0))
    mod("스캔 중 명령 Z 변함", "X-POS-05", lambda m: po(m)[5].update(z_mm=po(m)[5]["z_mm"] + 0.01))
    mod("스캔 구간 feed 평균이 ±5 % 밖", "X-POS-07", lambda m: setall(po(m)[1:], feed_mm_s=3.0))
    mod("pos.layer_idx ≠ meta.layer_idx", "X-POS-08", lambda m: po(m)[2].update(layer_idx=5))
    mod("acc_x만 있고 acc_y 빔", "X-POS-10", lambda m: po(m)[2].update(acc_y_mm_s2=None))
    mod("ChArUco 보드가 시야보다 큼", "X-CAL-01", lambda m: man(m)[0].update(target_square_mm=2.5))
    mod("마커 ≥ 칸", "X-CAL-02", lambda m: man(m)[0].update(target_marker_mm=1.6))
    mod("(cal_id, kind, pose, laser_on) 중복", "X-CAL-03", lambda m: man(m)[2].update(laser_on=False))
    mod("image_file 숫자 ≠ kind", "X-CAL-04", lambda m: man(m)[0].update(image_file="d2/view_000.png"))
    mod("D2 켬·끔 노출 다름", "X-CAL-06", lambda m: man(m)[2].update(exposure_us=900.0))
    mod("D2 cmd_z가 자세마다 같음", "X-CAL-07", lambda m: (man(m)[3].update(cmd_z_mm=1.0), man(m)[4].update(cmd_z_mm=1.0)))
    mod("게이지 실측 − 공칭 > 0.02", "X-CAL-08", lambda m: _cal_row(m, "filler_gauge").update(gauge_measured_mm=0.23))
    mod("valid_from < created", "X-CAL-09", lambda m: man(m)[0].update(valid_from="2026-11-20T09:00:00+09:00"))
    mod("valid_until ≤ valid_from", "X-CAL-10", lambda m: res(m)[0].update(valid_until="2026-11-20T11:00:00+09:00"))
    mod("ref_id 약어 ≠ kind", "X-REF-01", lambda m: sref(m).update(ref_id="REF-BKG-000"))
    mod("bed_marker 짝 스캔이 8 mm 위", "X-REF-03", lambda m: me(m).update(layer_z_mm=9.0))
    mod("ref.layer_idx ≠ 짝 스캔", "X-REF-04", lambda m: sref(m).update(layer_idx=1))
    mod("static_repeat인데 100장 미만", "X-REF-06", lambda m: sref(m).update(kind="static_repeat", ref_id="REF-STA-000"))
    mod("기준과 짝 스캔 시각 차 > 600 s", "X-REF-07", lambda m: sref(m).update(t_start_ns=fr(m)[0]["t_host_ns"] - 700_000_000_000))
    mod("층별 기준의 scan_id가 다른 스캔", "X-REF-08", lambda m: sref(m).update(scan_id="S01_r01_L001"))
    mod("scan_id 층 번호 ≠ layer_idx", "X-MET-01", lambda m: me(m).update(scan_id="S01_r01_L005"))
    mod("specimen_id ≠ scan_id 앞 세 글자", "X-MET-03", lambda m: me(m).update(specimen_id="S02"))
    mod("repeat ≠ scan_id rNN", "X-MET-04", lambda m: me(m).update(repeat=2))
    mod("layer_idx ≥ layer_count", "X-MET-06", lambda m: me(m, "L001").update(layer_count=1))
    mod("gcode_line_start > end", "X-MET-09", lambda m: me(m).update(gcode_line_start=150))
    mod("gcode_line_end ≥ 다음 층 start", "X-MET-10", lambda m: me(m).update(gcode_line_end=150))
    mod("layer_end ≥ scan_start", "X-MET-11", lambda m: me(m).update(layer_end_t_ns=me(m)["scan_start_t_ns"] + 1))
    mod("pause_added < 스캔 시간", "X-MET-14", lambda m: me(m).update(pause_added_s=0.05))
    mod("scan_x ≠ 위치 로그 X 평균", "X-MET-17", lambda m: me(m).update(scan_x_mm=110.5))
    mod("scan_y0 ≠ scan_start Y", "X-MET-18", lambda m: me(m).update(scan_y0_mm=90.5))
    mod("enclosure_dark인데 외함 없음", "X-MET-20", lambda m: me(m).update(enclosure=False))
    mod("layer_h > nozzle_dia", "X-MET-24", lambda m: me(m).update(layer_h_mm=0.5))
    mod("세션 안 bed_ref_id 다름", "X-MET-26", lambda m: me(m, "L001").update(bed_ref_id="REF-BED-002"))
    mod("ref_tower인데 짝 기준 없음", "X-MET-30", lambda m: me(m).update(zero_ref_method="ref_tower"))
    mod("세션 안 bed_mesh_file 다름", "X-MET-32", lambda m: me(m, "L001").update(bed_mesh_file="printer/bed_mesh_b.json"))
    mod("usb2 대역폭 초과", "X-MET-37", lambda m: (me(m).update(cam_interface="usb2"),
                                                setall(fr(m), roi_w_px=1280, roi_h_px=512, roi_x0_px=0, roi_y0_px=0)))
    mod("필터 중심 − 파장 > 20 nm", "X-MET-40", lambda m: me(m).update(filter_center_nm=480.0))
    mod("노출 설정 ≠ 프레임 노출", "X-MET-41", lambda m: me(m).update(exposure_set_us=820.0))
    mod("게인 설정 ≠ 프레임 게인", "X-MET-42", lambda m: me(m).update(gain_set_db=1.0))
    mod("이동 스캔인데 frame_avg_n 2", "X-MET-43", lambda m: me(m).update(frame_avg_n=2))
    mod("n_frames < 길이 ÷ 간격", "X-MET-46", lambda m: me(m).update(scan_length_mm=1.0))
    mod("files_sha256 키가 절대 경로", "X-MET-50", lambda m: me(m).update(files_sha256={"/abs/x": "z"}))
    mod("실측인데 주입 요인 있음", "X-MET-51", lambda m: me(m).update(source="real"))
    mod("같은 시편 part_idx 다름", "X-REP-01", lambda m: des(m)[1].update(part_idx=5))
    mod("(part, session, operator, repeat) 중복", "X-REP-02", lambda m: des(m)[1].update(repeat_idx=1))
    mod("층별 스캔인데 remount true", "X-REP-03", lambda m: des(m, "design_executed.csv")[0].update(remount=True))
    mod("같은 시편 truth_id 다름", "X-REP-07", lambda m: des(m)[1].update(truth_id="T-S09"))
    mod("기준 폴더 이름 형식 틀림", "FILE-02",
        lambda m: m["sessions"][SESSION]["refs"].update({"REF-bed-001": m["sessions"][SESSION]["refs"].pop("REF-BED-001")}))
    mod("position_log.csv 없음", "FILE-03", None, lambda fs: fs.pop(f"{L0}/position_log.csv"))
    mod("교정 영상 없음", "FILE-12", None, lambda fs: fs.pop(f"calibration/{CAL}/d1/view_000.png"))
    mod("ref.frames_dir 폴더 없음", "FILE-13", lambda m: sref(m).update(frames_dir="frames2/"))
    mod("study_id ≠ 폴더", "FILE-16", lambda m: des(m)[0].update(study_id="MSA-02"))
    mod("행 칸 수 ≠ 머리글", "CSV-07", None, _file_edit("L000/frames_index.csv", _extra_cell))
    mod("UTF-8 아님", "CSV-08", None, _file_edit("L000/position_log.csv", lambda b: b + b"\xff\xfe\n"))
    mod("meta.json 최상위가 배열", "JSON-05", None, _file_edit("L000/meta.json", lambda b: b"[]\n"))
    # v1.0: bed_bare · feeler는 -1 (빈 칸 아님) → X-REF-17 (옛 CROSS-EMPTY.ref.layer_idx)
    mod("bed_bare인데 layer_idx 0", "X-REF-17",
        lambda m: m["sessions"][SESSION]["refs"]["REF-BED-001"]["index"][0].update(layer_idx=0))
    mod("in_process인데 paired_scan_id 있음", "CROSS-EMPTY.meta.paired_scan_id", lambda m: me(m).update(paired_scan_id="S01_r01_L001"))
    mod("D1 행에 cmd_z_mm", "CROSS-EMPTY.cal.cmd_z_mm", lambda m: man(m)[0].update(cmd_z_mm=1.0))
    mod("설계 파일에 scan_id", "CROSS-EMPTY.rep.scan_id", lambda m: des(m)[0].update(scan_id="S01_r01_L000"))
    mod("user_gcode인데 단차 각", "CROSS-EMPTY.meta.step_edge_angle_deg", lambda m: me(m).update(step_edge_angle_deg=0.0))
    mod("raw_saved false인데 frame.file 있음", "CROSS-EMPTY.frame.file", lambda m: me(m).update(raw_saved=False))
    H.extend(_sv13_hand_faults())
    return H


def _cal_row(m, target_type, record_type=None):
    """교정 목록에서 target_type (와 record_type)이 맞는 첫 행."""
    return next(r for r in m["cal"][CAL]["cal_manifest.csv"]
                if r["target_type"] == target_type and (record_type is None or r["record_type"] == record_type))


def _sv13_hand_faults() -> list[tuple]:
    """SV13 (T1 2차 명세)에서 새로 만든 규칙마다 고장 표본."""
    H = []

    def mod(name, rid, fm=None, fb=None):
        H.append((name, rid, fm, fb))

    S = lambda m, lay="L000": _scan(m, lay)  # noqa: E731
    fr = lambda m: S(m)["frames"]  # noqa: E731
    po = lambda m, lay="L000": S(m, lay)["pos"]  # noqa: E731
    me = lambda m, lay="L000": S(m, lay)["meta"]  # noqa: E731
    # 높은 단 (h1, 교정 행이 있는 FG-0.50 · GB-01.2)
    stg = lambda m, lay="L000": [r for r in S(m, lay)["refs"].values() if r["index"][0]["kind"] == "step_gauge"][-1]  # noqa: E731
    bed = lambda m: m["sessions"][SESSION]["refs"]["REF-BED-001"]  # noqa: E731
    flr = lambda m: m["sessions"][SESSION]["refs"]["REF-FLR-001"]  # noqa: E731
    man = lambda m: m["cal"][CAL]["cal_manifest.csv"]  # noqa: E731
    SB = f"sessions/{SESSION}"

    def setall(rows, **kw):
        for r in rows:
            r.update(kw)

    def rename_layer(m, old, new):
        sc = m["sessions"][SESSION]["scans"][SR]
        sc[new] = sc.pop(old)

    def add_pass(m):
        sc = m["sessions"][SESSION]["scans"][SR]
        c = clone(sc["L001"])  # 줄 0, 1이 이미 있음 → 줄 3을 더해 2가 빠지게
        c["meta"].update(scan_pass_idx=3, scan_id=f"{SR}_L001_p03")
        setall(c["frames"], scan_id=f"{SR}_L001_p03")
        setall(c["pos"], scan_id=f"{SR}_L001_p03")
        c["refs"] = {}
        c["meta"]["zero_ref_method"] = "z_only"
        sc["L001_p03"] = c

    # 폴더·파일
    mod("gcode_file이 저장소에 없음", "FILE-17", lambda m: me(m).update(gcode_file="data/gcode/none.gcode"))
    mod("slicer_profile_file이 저장소에 없음", "FILE-18", lambda m: me(m).update(slicer_profile_file="data/gcode/none.ini"))
    mod("ref_id ≠ 기준 폴더 이름", "FILE-19", lambda m: stg(m)["index"][0].update(ref_id="REF-STG-009"))
    mod("움직이는 기준에 position_log.csv 없음", "FILE-03", None, lambda fs: fs.pop(f"{SB}/reference/REF-BED-001/position_log.csv"))
    mod("층 폴더 _p01인데 scan_pass_idx 0", "FILE-05", lambda m: rename_layer(m, "L001", "L001_p01"))
    mod("층 폴더 이름 _p 세 자리", "FILE-02", lambda m: rename_layer(m, "L001", "L001_p001"))
    mod("post 줄 번호 1만 있음 (pass 0 없음)", "FILE-04", lambda m: me(m, "post").update(scan_pass_idx=1, scan_id=f"{SR}_p01"))
    # frame
    mod("기준 frames layer_idx ≠ ref.layer_idx (빈 칸이면 -1)", "X-FRM-20", lambda m: setall(bed(m)["frames"], layer_idx=0))
    mod("trig_pulse_idx가 늘지 않음", "X-FRM-21", lambda m: fr(m)[5].update(trig_pulse_idx=fr(m)[4]["trig_pulse_idx"]))
    mod("trig_pulse 차 − 1 ≠ dropped_before", "X-FRM-22", lambda m: [r.update(trig_pulse_idx=r["trig_pulse_idx"] + 1) for r in fr(m)[5:]])
    mod("gate_on 덩어리가 끊김", "X-FRM-23",
        lambda m: (setall(fr(m), trigger_mode="gate", trig_pulse_idx=None, gate_on=True), fr(m)[6].update(gate_on=False),
                   me(m).update(trigger_period_s=None)))
    mod("레이저 끔 행에 trig_pulse_idx", "CROSS-EMPTY.frame.trig_pulse_idx", lambda m: fr(m)[0].update(trig_pulse_idx=0))
    mod("hw인데 gate_on 값", "CROSS-EMPTY.frame.gate_on", lambda m: fr(m)[3].update(gate_on=True))
    # pos
    mod("기준 위치 로그 layer_idx ≠ frames", "X-POS-11", lambda m: setall(bed(m)["pos"], layer_idx=0))
    mod("스캔 구간 pass_idx 건너뜀", "X-POS-12", lambda m: po(m)[3].update(pass_idx=2))
    mod("post 스캔에 resume", "X-POS-13", lambda m: po(m, "post")[4].update(event="resume"))
    mod("cool_end 없음", "X-POS-14", lambda m: po(m, "post")[2].update(event="none"))
    mod("cool_end가 scan_start 뒤", "X-POS-14", lambda m: po(m, "post")[2].update(t_ns=me(m, "post")["scan_start_t_ns"] + 1))
    mod("벨트 Z인데 식힌 재측정 중 motor_off", "X-MET-58", lambda m: po(m, "post")[4].update(event="motor_off"))
    # cal
    mod("nozzle_touch인데 kind D3", "X-CAL-17", lambda m: _cal_row(m, "coord_plate", "nozzle_touch").update(kind="D3"))
    mod("micrometer인데 target_type flat_plate", "X-CAL-18", lambda m: _cal_row(m, "material_sample").update(target_type="flat_plate"))
    mod("filler_gauge인데 kind D4", "X-CAL-19", lambda m: _cal_row(m, "filler_gauge").update(kind="D4"))
    mod("영상 없는 행인데 laser_on true", "X-CAL-20", lambda m: _cal_row(m, "step_gauge", "micrometer").update(laser_on=True))
    mod("FG 숫자 ≠ 공칭", "X-CAL-21", lambda m: _cal_row(m, "filler_gauge").update(gauge_block_id="FG-0.30"))
    mod("블록 높이 − 공칭 > 0.02", "X-CAL-22",
        lambda m: [r.update(gauge_block_height_mm=1.05) for r in man(m) if r["gauge_block_id"] == GB_ID])
    mod("같은 블록 높이 다름", "X-CAL-23", lambda m: _cal_row(m, "step_gauge", "micrometer").update(gauge_block_height_mm=1.0010))
    mod("micrometer 행에 image_file", "CROSS-EMPTY.cal.image_file",
        lambda m: _cal_row(m, "step_gauge", "micrometer").update(image_file="d5/step_gauge/gb_01_000.png"))
    mod("image 행에 nozzle_touch_z_mm", "CROSS-EMPTY.cal.nozzle_touch_z_mm",
        lambda m: _cal_row(m, "coord_plate", "image").update(nozzle_touch_z_mm=2.0))
    # ref
    mod("feeler가 첫 층보다 늦음", "X-REF-10", lambda m: flr(m)["index"][0].update(t_start_ns=150_000_000_000))
    mod("기준물 ID가 교정에 없음", "X-REF-12", lambda m: stg(m)["index"][0].update(gauge_block_id="GB-02"))
    mod("feeler인데 GB-", "X-REF-13", lambda m: flr(m)["index"][0].update(gauge_block_id=GB_ID))
    mod("기준물 높이 ≠ cal 교정값", "X-REF-14", lambda m: stg(m)["index"][0].update(gauge_height_mm=1.0))
    mod("기준물 높이 > 짝 층 Z", "X-REF-15", lambda m: me(m).update(layer_z_mm=0.5))  # h1 0.5021 > 0.5
    mod("기준물 Z ≠ 스캔 Z (> 0.001)", "X-REF-16", lambda m: setall(stg(m)["pos"], z_mm=stg(m)["pos"][0]["z_mm"] + 0.01))
    mod("bed_bare에 gauge_temp_c", "CROSS-EMPTY.ref.gauge_temp_c", lambda m: bed(m)["index"][0].update(gauge_temp_c=22.0))
    # meta
    mod("scan_pass_idx 0인데 scan_id에 _p", "X-MET-54", lambda m: me(m).update(scan_id=f"{SR}_L000_p01"))
    mod("L001 줄 번호 0, 1, 3 (2 빠짐)", "X-MET-55", add_pass)
    mod("제조사 접두사인데 mainline", "X-MET-59", lambda m: me(m).update(firmware_fork="mainline"))
    mod("hw인데 trigger_pin none", "X-MET-60", lambda m: me(m).update(trigger_pin="none"))
    mod("trigger_period × fps ≠ 1", "X-MET-61", lambda m: me(m).update(trigger_period_s=0.01))
    mod("step_gauge인데 짝 기준 없음", "X-MET-62", lambda m: (S(m)["refs"].pop("REF-STG-001"), S(m)["refs"].pop("REF-STG-002")))
    mod("free 트리거인데 trigger_period_s 값", "CROSS-EMPTY.meta.trigger_period_s",
        lambda m: (setall(fr(m), trigger_mode="free", trig_pulse_idx=None), me(m).update(trigger_pin="none")))
    H.extend(_v10_hand_faults())
    return H


def _v10_hand_faults() -> list[tuple]:
    """명세 v1.0 (T1 3차, 2026-10-28 동결)에서 새로 만들거나 바꾼 규칙마다 고장 표본."""
    H = []

    def mod(name, rid, fm=None, fb=None):
        H.append((name, rid, fm, fb))

    S = lambda m, lay="L000": _scan(m, lay)  # noqa: E731
    me = lambda m, lay="L000": S(m, lay)["meta"]  # noqa: E731
    po = lambda m, lay="L000": S(m, lay)["pos"]  # noqa: E731
    refs = lambda m: m["sessions"][SESSION]["refs"]  # noqa: E731
    stgs = lambda m, lay="L000": [r for r in S(m, lay)["refs"].values() if r["index"][0]["kind"] == "step_gauge"]  # noqa: E731
    mrk = lambda m, lay="L000": next(r for r in S(m, lay)["refs"].values() if r["index"][0]["kind"] == "bed_marker")  # noqa: E731
    man = lambda m: m["cal"][CAL]["cal_manifest.csv"]  # noqa: E731
    layers = lambda m: m["sessions"][SESSION]["scans"][SR]  # noqa: E731

    def setall(rows, **kw):
        for r in rows:
            r.update(kw)

    def rename_ref(d, old, new):
        d[new] = d.pop(old)
        d[new]["index"][0]["ref_id"] = new

    def blind_all(m, keep=()):
        """캠페인 전체를 블라인드로 (정상 블라인드 꼴). keep에 든 것은 일부러 남김."""
        for sc in layers(m).values():
            sc["meta"].update(blind=True)
            if "sim_seed" not in keep:
                sc["meta"].update(sim_seed=None)
            if "injected_factors" not in keep:
                sc["meta"].update(injected_factors=[])
        if "noise_seed" not in keep:
            for rows in m["msa"]["MSA-01"].values():
                setall(rows, noise_seed=None)

    # 위치 로그 (post)
    mod("post 스캔 위치 로그에 pass_idx 1", "X-POS-15", lambda m: po(m, "post_p01")[4].update(pass_idx=1))
    mod("post 둘째 줄에 cool_start", "X-POS-14", lambda m: po(m, "post_p01")[0].update(event="cool_start"))
    mod("벨트 Z인데 post 둘째 줄에 motor_off", "X-MET-58", lambda m: po(m, "post_p01")[0].update(event="motor_off"))
    # 교정
    mod("step_gauge 행이 FG-", "X-CAL-25", lambda m: _cal_row(m, "step_gauge", "micrometer").update(gauge_block_id="FG-0.50"))
    mod("cal 행에 GB-00", "X-CAL-25",
        lambda m: [r.update(gauge_block_id="GB-00", gauge_block_height_mm=0.0001) for r in man(m) if r["gauge_block_id"] == GB_ID])
    mod("소수 블록 높이 − 공칭 합 > 0.02 (GB-01.4+01.1 = 2.5)", "X-CAL-22",
        lambda m: _cal_row(m, "step_gauge", "micrometer").update(gauge_block_id="GB-01.4+01.1", gauge_block_height_mm=2.53))
    mod("재료 조각 재료 ≠ 스캔 재료", "X-CAL-26", lambda m: _cal_row(m, "material_sample").update(material="PETG"))
    mod("재료 조각 색 ≠ 스캔 색", "X-CAL-26", lambda m: _cal_row(m, "material_sample").update(color="black"))
    mod("한 cal_id에 재료 조각 (재료, 색) 둘", "X-CAL-27",
        lambda m: man(m).append(dict(_cal_row(m, "material_sample"), pose_idx=4, color="black")))
    # 기준
    mod("층 기준 (마커) layer_idx -1", "X-REF-17", lambda m: mrk(m)["index"][0].update(layer_idx=-1))
    mod("feeler layer_idx 0", "X-REF-17", lambda m: refs(m)["REF-FLR-001"]["index"][0].update(layer_idx=0))
    mod("ref_id 순번이 t_start 순서와 다름", "X-REF-18",
        lambda m: mrk(m, "L001")["index"][0].update(t_start_ns=mrk(m)["index"][0]["t_start_ns"] - 1_000_000_000))
    mod("ref_id 순번에 빈 번호 (MRK-003 → 004)", "X-REF-18", lambda m: rename_ref(S(m, "post")["refs"], "REF-MRK-003", "REF-MRK-004"))
    mod("세션 안 같은 ref_id 둘", "X-REF-19", lambda m: rename_ref(S(m, "L001")["refs"], "REF-MRK-002", "REF-MRK-001"))
    mod("두 단 중 하나 빠짐", "X-REF-20", lambda m: S(m, "L001")["refs"].pop("REF-STG-003"))
    mod("두 단 ID가 같음", "X-REF-20", lambda m: stgs(m, "L001")[0]["index"][0].update(gauge_block_id=GB_ID, gauge_height_mm=GB_H))
    mod("두 단 간격 > 3.04", "X-REF-20", lambda m: stgs(m, "L001")[1]["index"][0].update(gauge_height_mm=3.6))
    mod("층 Z − 낮은 단 > 8.0", "X-REF-20", lambda m: me(m).update(layer_z_mm=8.1))
    mod("두 단이 셋", "X-REF-20",
        lambda m: S(m, "post")["refs"].update({"REF-STG-007": _ref("REF-STG-007", "step_gauge", f"{SR}", 1,
                                                                    3_000_000_000_000, 7700, marker=False, z=3.4, gauge=(BED_ID, 0.0))}))
    mod("bed_bare 줄 1 없음", "X-REF-21", lambda m: refs(m).pop("REF-BED-002"))
    mod("bed_bare 줄 번호 0, 2", "X-REF-21", lambda m: refs(m)["REF-BED-002"]["index"][0].update(scan_pass_idx=2))
    mod("bed_bare 위치 X ≠ 그 줄 scan_x", "X-REF-22", lambda m: setall(refs(m)["REF-BED-002"]["pos"], x_mm=120.0))
    mod("GB-00인데 높이 ≠ 0", "X-REF-23", lambda m: stgs(m)[0]["index"][0].update(gauge_height_mm=0.001))
    mod("GB-00 아닌데 높이 0", "X-REF-23", lambda m: refs(m)["REF-FLR-001"]["index"][0].update(gauge_height_mm=0.0))
    mod("층 기준 짝 스캔이 둘째 줄", "X-REF-24", lambda m: mrk(m, "L001")["index"][0].update(scan_id=f"{SR}_L001_p01"))
    mod("FG 단 높이 ≠ cal gauge_measured_mm", "X-REF-14", lambda m: stgs(m)[1]["index"][0].update(gauge_height_mm=0.6))
    mod("step_gauge 단이 GB-·FG- 아님 (형식 통과 못 하는 값)", "X-REF-13",
        lambda m: stgs(m)[1]["index"][0].update(gauge_block_id="XX-01"))
    # 같은 Z (행마다)
    mod("둘째 줄 스캔 Z가 첫 줄과 0.002 다름", "X-REF-16",
        lambda m: [r.update(z_mm=r["z_mm"] + 0.002) for r in po(m, "L001_p01") if r["event"] != "layer_change"])
    mod("기준 로그 한 행만 0.0015 다름 (평균은 0.001 안)", "X-REF-16",
        lambda m: stgs(m)[0]["pos"][1].update(z_mm=stgs(m)[0]["pos"][1]["z_mm"] + 0.0015))
    # meta
    mod("bed_ref_id 줄 번호 ≠ 스캔 줄 번호", "X-MET-64", lambda m: me(m, "L001_p01").update(bed_ref_id="REF-BED-001"))
    mod("같은 줄 번호인데 bed_ref_id 다름", "X-MET-26", lambda m: me(m, "post_p01").update(bed_ref_id="REF-BED-001"))
    mod("post 줄 집합 ≠ 마지막 층 줄 집합", "X-MET-65", lambda m: layers(m).pop("post_p01"))
    mod("post 둘째 줄 짝이 첫 줄 스캔", "X-MET-33", lambda m: me(m, "post_p01").update(paired_scan_id=f"{SR}_L001"))
    mod("실측인데 blind true", "X-MET-66", lambda m: me(m).update(source="real", blind=True))
    mod("캠페인 안 blind 값이 섞임", "X-MET-67", lambda m: me(m).update(blind=True, sim_seed=None, injected_factors=[]))
    mod("blind인데 injected_factors 남김", "X-MET-51", lambda m: blind_all(m, keep=("injected_factors",)))
    mod("blind인데 sim_seed 남김", "CROSS-EMPTY.meta.sim_seed", lambda m: blind_all(m, keep=("sim_seed",)))
    mod("blind인데 rep.noise_seed 남김", "CROSS-EMPTY.rep.noise_seed", lambda m: blind_all(m, keep=("noise_seed",)))
    mod("material_sample인데 color 빔", "REQ.cal.color", lambda m: _cal_row(m, "material_sample").update(color=None))
    mod("filler_gauge 행에 material", "CROSS-EMPTY.cal.material", lambda m: _cal_row(m, "filler_gauge").update(material="PLA"))
    mod("feeler에 scan_pass_idx", "CROSS-EMPTY.ref.scan_pass_idx", lambda m: refs(m)["REF-FLR-001"]["index"][0].update(scan_pass_idx=0))
    H.extend(_v11_hand_faults())
    return H


def _v11_hand_faults() -> list[tuple]:
    """명세 v1.1 (V-1, 2026-10-28)에서 바뀐 규칙마다 ERROR 고장 표본. 두 단 비 (WARN)는 ratio_tests()."""
    H = []

    def mod(name, rid, fm=None, fb=None):
        H.append((name, rid, fm, fb))

    refs = lambda m: m["sessions"][SESSION]["refs"]  # noqa: E731

    def msa_only(m):
        """스캔 없이 msa/만 있는 가상 캠페인 (blind를 알 수 없음 → false로 봄) + noise_seed 한 칸 비움."""
        m["sessions"].clear()
        m["msa"]["MSA-01"]["design.csv"][0].update(noise_seed=None)

    mod("spec_version 1.2 (정규식은 맞고 허용 값 밖)", "ENUM.meta.spec_version", lambda m: _scan(m)["meta"].update(spec_version="1.2"))
    mod("bed_bare layer_idx 빈 칸 (v1.1: 필수이고 −1)", "REQ.ref.layer_idx", lambda m: refs(m)["REF-BED-001"]["index"][0].update(layer_idx=None))
    mod("feeler layer_idx 빈 칸 (v1.1: 필수이고 −1)", "REQ.ref.layer_idx", lambda m: refs(m)["REF-FLR-001"]["index"][0].update(layer_idx=None))
    mod("스캔 없는 가상 MSA 캠페인에 noise_seed 빔 (v1.1: blind = false로 봄)", "REQ.rep.noise_seed", msa_only)
    return H


def set_layer_z(m, layer_idx: int, z: float) -> None:
    """층 번호가 layer_idx인 모든 스캔 (post 포함)의 층 Z를 z로: meta.layer_z_mm, 스캔 · 그 층 기준 위치 로그 Z를 같은 만큼 옮김."""
    for sc in m["sessions"][SESSION]["scans"][SR].values():
        if sc["meta"]["layer_idx"] != layer_idx:
            continue
        dz = z - sc["meta"]["layer_z_mm"]
        sc["meta"]["layer_z_mm"] = z
        for r in sc["pos"]:
            r["z_mm"] = round(r["z_mm"] + dz, 6)
        for ref in sc["refs"].values():
            for r in ref.get("pos", []):
                r["z_mm"] = round(r["z_mm"] + dz, 6)


def set_gauge_height(m, gid: str, h: float) -> None:
    """기준물 gid의 교정 높이를 h로: cal 행 (GB- gauge_block_height_mm, FG- gauge_measured_mm)과 그 ID를 쓰는 모든 기준 행."""
    key = "gauge_block_height_mm" if gid.startswith("GB-") else "gauge_measured_mm"
    for r in m["cal"][CAL]["cal_manifest.csv"]:
        if r["gauge_block_id"] == gid:
            r[key] = h
    for sc in m["sessions"][SESSION]["scans"][SR].values():
        for ref in sc["refs"].values():
            if ref["index"][0]["gauge_block_id"] == gid:
                ref["index"][0]["gauge_height_mm"] = h


def ratio_tests() -> list[tuple]:
    """두 단 비 경고 W-REF-25 (명세 v1.1 4절). (이름, 모형 고침, WARN이 나와야 하는지).

    문턱 = 4 ÷ √(2 × 1.5² + 2u²): u 2 µm → 1.13137, u 1 µm → 1.56893 [계산]. 모두 ERROR 0이어야 함 (형식은 맞는 데이터).
    - 양성: 6차 예. h1 1.2 (GB-01.2) · h2 0.5 (FG-0.50) · 층 Z 2.4 → 비 1.2 ÷ 0.7 = 1.714, u = max(2, 1) = 2 → 1.131 넘음 (L001 · post)
    - 음성: B.4. h1 0.5021 (FG-0.50, u 1) · h2 0 (GB-00, 다른 단 값 1) · 층 Z 1.0 → 비 0.4979 ÷ 0.5021 = 0.992 < 1.569 (L000)
    - 경계: L001 h1 1.2008 · h2 0.5021 (간격 0.6987), u 2. 층 Z 1.9912 → 비 1.13124 (아래), 1.9914 → 1.13153 (위)
    - u는 cal 값: L000 (FG-0.50 · GB-00)에서 FG-0.50 `cal.gauge_u_um`을 1 → 2로 올리면 문턱 1.569 → 1.131, 정상 L000 비 1.390이 넘음
      (u = 두 단 중 큰 값이라 GB-00 = 다른 단 값 규칙은 결과를 바꾸지 않음)
    """
    def six(m):
        set_gauge_height(m, GB_ID, 1.2)
        set_gauge_height(m, FG5_ID, 0.5)
        set_layer_z(m, 1, 2.4)

    def fg5_u2(m):
        for r in m["cal"][CAL]["cal_manifest.csv"]:
            if r["gauge_block_id"] == FG5_ID:
                r["gauge_u_um"] = 2.0
    return [
        ("6차 예 (h1 1.2 · h2 0.5 · 층 Z 2.4, 비 1.714 > 1.131)", six, True),
        ("B.4 (h1 0.5021 · h2 GB-00 · 층 Z 1.0, 비 0.992 < 1.569)", lambda m: set_layer_z(m, 0, 1.0), False),
        ("경계 아래 (u 2, 층 Z 1.9912, 비 1.13124 < 1.13137)", lambda m: set_layer_z(m, 1, 1.9912), False),
        ("경계 위 (u 2, 층 Z 1.9914, 비 1.13153 > 1.13137)", lambda m: set_layer_z(m, 1, 1.9914), True),
        ("u는 cal 값 (FG-0.50 u 1 → 2, L000 비 1.390 > 1.131)", fg5_u2, True),
    ]


def _extra_cell(b: bytes) -> bytes:
    lines = b.decode("utf-8").split("\n")
    lines[1] = lines[1] + ",x"
    return "\n".join(lines).encode("utf-8")


def _swap_cols01(b: bytes) -> bytes:
    lines = b.decode("utf-8").split("\n")
    out = []
    for ln in lines:
        if not ln:
            out.append(ln)
            continue
        c = ln.split(",")
        c[0], c[1] = c[1], c[0]
        out.append(",".join(c))
    return "\n".join(out).encode("utf-8")


def _add_col(b: bytes) -> bytes:
    lines = b.decode("utf-8").split("\n")
    return "\n".join((ln + (",extra" if i == 0 else ",1")) if ln else ln for i, ln in enumerate(lines)).encode("utf-8")


META_L000 = f"sessions/{SESSION}/{SR}/L000/meta.json"


def _redump_meta(**kw):
    """L000 meta.json을 다른 표기로 다시 씀 (값은 그대로, meta.json은 files_sha256 밖)."""
    def f(fs):
        fs[META_L000] = (json.dumps(json.loads(fs[META_L000].decode("utf-8")), **kw) + "\n").encode("utf-8")
    return f


def warn_tests() -> list[tuple]:
    """경고 규칙이 실제로 나오는지 (이름, 기대 규칙 ID, 모형 고침[, 바이트 고침])."""
    return [
        ("meta.json 들여쓰기 4칸", "JSON-06", None, _redump_meta(indent=4, ensure_ascii=False)),
        ("meta.json 한글을 \\u로", "JSON-07", lambda m: _scan(m)["meta"].update(notes="한글 메모"),
         _redump_meta(indent=2, ensure_ascii=True)),
        ("D1 재투영 RMS 0.25", "W-CAL-11", lambda m: m["cal"][CAL]["cal_results.csv"][0].update(reproj_rms_px=0.25)),
        ("D2 평면 RMS 6", "W-CAL-12", lambda m: m["cal"][CAL]["cal_results.csv"][1].update(plane_rms_um=6.0)),
        ("무효화된 교정", "W-CAL-13", lambda m: m["cal"][CAL]["cal_results.csv"][2].update(invalidated_by="remount")),
        ("작은 층", "W-MET-15", lambda m: _scan(m)["meta"].update(layer_time_s=10.0)),
        ("Z hop 0.5", "W-MET-16", lambda m: _scan(m)["meta"].update(scan_z_hop_mm=0.5)),
        ("실측인데 초점 고정 안 함", "W-MET-38", lambda m: _scan(m)["meta"].update(source="real", lens_focus_locked=False)),
        ("레이저 1.5 mW", "W-MET-39", lambda m: _scan(m)["meta"].update(laser_power_mw=1.5)),
        ("line_peak 20 % 넘게 떨어짐", "W-REF-09", lambda m: next(iter(_scan(m, "L001")["refs"].values()))["index"][0].update(line_peak_pct=50.0)),
        # ENUM.meta.firmware_name은 T1 2차에서 [대기: T14]가 풀려 ERROR (자동 고장 "허용 밖")로 옮김
        ("베드가 Y로 움직이는데 scan_axis +Y", "W-MET-57", lambda m: _scan(m)["meta"].update(bed_motion="y")),
        ("zero_ref_method z_only (판정 거부 X2)", "W-MET-63",
         lambda m: (_scan(m)["meta"].update(zero_ref_method="z_only"))),
    ]


def switch_tests() -> list[tuple]:
    """끌 수 있는 기본 켬 규칙 (D-21 채택 X4 · X7). (이름, 규칙 ID, 모형 고침). 기본으로 WARN이 나오고, 끄면 안 나와야 함."""
    def drop_layer0(m):
        sc = m["sessions"][SESSION]["scans"][SR]
        sc.pop("L000")
    return [
        ("X4 bed_bare 교정 ID ≠ 스캔 교정 ID", "W-REF-11",
         lambda m: m["sessions"][SESSION]["refs"]["REF-BED-001"]["index"][0].update(calibration_id="CAL-2026-11-19-A")),
        ("X7 층 L000 빠짐", "W-MET-56", drop_layer0),
    ]


def truth_context(blind: bool = False) -> dict:
    """정상 표본 캠페인의 참값 대조용 사실 (Validator.run 뒤 truth_ctx와 같아야 함, 시험이 맞춰 봄)."""
    ids = ["S01_r01", "S01_r01_L000", "S01_r01_L001", "S01_r01_L001_p01", "S01_r01_p01"]
    # v1.1: temp_c 키 집합 = step_gauge 기준이 있는 층 (L000 · L001) + post 두 단
    return {"gauge_layers": ["L000", "L001", "post"], "has_step_gauge": True, "gauge_ids": [GB_ID], "blind": blind, "scan_ids": ids,
            "factors": [] if blind else ["MF-SYN-01"]}


def normal_truth(blind: bool = False) -> dict:
    """정상 표본에 맞는 참값 객체의 v1.0 관련 키 (형식 시험용 값, 부록 A 예시 꼴)."""
    t = {"judgement": "pass", "pass_pct": 97.0,
         "gauge_thickness_mm": {"0.20": 0.2031, "0.50": 0.5021},
         "gauge_block_heights_mm": {GB_ID: 1.2006},
         "gauge_temp_params": {"cte_um_per_m_c": 11.5, "temp_c": {"L000": 45.0, "L001": 45.0, "post": 23.0}},
         "scan_seeds": None, "scan_factors": None, "factor_params": {"MF-SYN-01": {"dt_ns": 10_000_000}}}
    if blind:
        ids = truth_context(True)["scan_ids"]
        t["scan_seeds"] = {s: {"sim_seed": 7310045 + i, "noise_seed": None} for i, s in enumerate(ids)}
        t["scan_factors"] = {s: ["MF-SYN-01"] for s in ids}
    return t


def truth_tests() -> list[tuple]:
    """참값 객체 검사 (Validator.check_truth). (이름, 참값, 기대 규칙 ID 또는 None, 캠페인 사실 ctx)."""
    N = normal_truth
    ctx, bctx = truth_context(), truth_context(True)

    def w(base, **kw):
        t = clone(base)
        t.update(kw)
        return t
    return [
        ("정상 pass 97", N(), None, ctx),
        ("정상 fail 94.9", w(N(), judgement="fail", pass_pct=94.9), None, ctx),
        ("경계 pass 95", w(N(), pass_pct=95.0), None, ctx),
        ("정상 블라인드", N(True), None, bctx),
        ("pass인데 90", w(N(), pass_pct=90.0), "X-TRU-01", ctx),
        ("fail인데 95", w(N(), judgement="fail", pass_pct=95.0), "X-TRU-01", ctx),
        # v1.0 (T1 3차)
        ("step_gauge 있는데 블록 참 높이 null", w(N(), gauge_block_heights_mm=None), "X-TRU-02", ctx),
        ("블록 참 높이 − ID 합 > 0.02", w(N(), gauge_block_heights_mm={GB_ID: 1.23}), "X-TRU-02", ctx),
        ("블록 참 높이 키에 GB-00", w(N(), gauge_block_heights_mm={GB_ID: 1.2006, "GB-00": 0.0}), "X-TRU-02", ctx),
        ("기준물 열 모델에 cte 키 없음", w(N(), gauge_temp_params={"temp_c": {}}), "X-TRU-02", ctx),
        # v1.1 (V-1): temp_c 키 L### · post, _pNN 금지, 키 집합 = step_gauge 층 + post, 값 −10–130
        ("열 모델 끔 (cte 0, temp_c 없음)", w(N(), gauge_temp_params={"cte_um_per_m_c": 0.0}), None, ctx),
        ("temp_c 경계 −10 · 130", w(N(), gauge_temp_params={"cte_um_per_m_c": 11.5, "temp_c": {"L000": -10.0, "L001": 130, "post": 23.0}}),
         None, ctx),
        ("열 모델 켬인데 temp_c 없음", w(N(), gauge_temp_params={"cte_um_per_m_c": 11.5}), "X-TRU-02", ctx),
        ("temp_c 키에 _p01", w(N(), gauge_temp_params={"cte_um_per_m_c": 11.5,
                                                       "temp_c": {"L000": 45.0, "L001": 45.0, "L001_p01": 45.0, "post": 23.0}}), "X-TRU-02", ctx),
        ("temp_c 키 post_p01", w(N(), gauge_temp_params={"cte_um_per_m_c": 11.5,
                                                        "temp_c": {"L000": 45.0, "L001": 45.0, "post_p01": 23.0}}), "X-TRU-02", ctx),
        ("temp_c 키 집합에 post 빠짐", w(N(), gauge_temp_params={"cte_um_per_m_c": 11.5, "temp_c": {"L000": 45.0, "L001": 45.0}}),
         "X-TRU-02", ctx),
        ("temp_c 키에 기준 없는 층 L005", w(N(), gauge_temp_params={"cte_um_per_m_c": 11.5,
                                                                "temp_c": {"L000": 45.0, "L001": 45.0, "L005": 45.0, "post": 23.0}}), "X-TRU-02", ctx),
        ("temp_c 값 130.5", w(N(), gauge_temp_params={"cte_um_per_m_c": 11.5, "temp_c": {"L000": 45.0, "L001": 130.5, "post": 23.0}}),
         "X-TRU-02", ctx),
        ("temp_c가 dict 아님", w(N(), gauge_temp_params={"cte_um_per_m_c": 11.5, "temp_c": [45.0]}), "X-TRU-02", ctx),
        ("blind인데 scan_seeds null", w(N(True), scan_seeds=None), "X-TRU-03", bctx),
        ("blind 아닌데 scan_factors 값", w(N(), scan_factors=N(True)["scan_factors"]), "X-TRU-03", ctx),
        ("scan_seeds 키 집합 ≠ 스캔 ID", w(N(True), scan_seeds={"S01_r01": {"sim_seed": 1, "noise_seed": None}}), "X-TRU-03", bctx),
        ("factor_params 키 ≠ 주입 요인", w(N(), factor_params={"MF-SYN-02": {}}), "X-TRU-04", ctx),
        ("blind인데 factor_params 키 ≠ scan_factors 합집합", w(N(True), factor_params={}), "X-TRU-04", bctx),
        ("필러 참 두께 키 0.60", w(N(), gauge_thickness_mm={"0.60": 0.6}), "X-TRU-05", ctx),
    ]


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------
def run_selftest(fields: list[dict], rules_list: list[dict], file_cols: dict, disk: bool = True) -> dict:
    """disk=True면 정상 표본을 임시 폴더에도 써서 디스크 경로로 한 번 더 검사한다."""
    rules = {r["rule_id"]: r for r in rules_list}
    V = Validator(fields, rules_list, file_cols, repo_exists=repo_exists)

    def check(files):
        return V.run(MemFS(files), CAMPAIGN)

    t0 = time.perf_counter()
    base = normal_model()
    files = serialize(base, file_cols)
    # 정상: 메모리 + 디스크 (임시 폴더)
    normal = check(files)
    normal_disk = []
    if disk:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "raw" / CAMPAIGN
            write_tree(files, root)
            normal_disk = V.run(DirFS(root), CAMPAIGN)
    rep = {"normal_error": [f for f in normal + normal_disk if f.severity == "ERROR"],
           "normal_warn": [f for f in normal + normal_disk if f.severity == "WARN"]}

    timing = {"정상": time.perf_counter() - t0}
    t0 = time.perf_counter()
    # 경계: RANGE 끝값 (≤ · =)을 한 필드씩, 그 필드 파일의 모든 행에 넣음
    bvals = []
    for f in fields:
        if f["group"] == "truth" or f["excluded"] == "true" or not (f["min"] or f["max"]):
            continue
        for side in ("min", "max"):
            if f[side] and f[side + "_op"] in ("≤", "="):
                v = _num(f[side])
                v = int(v) if f["dtype"] in ("int", "int64") else float(v)
                bvals.append((f["field"], v))
    boundary_local, boundary_cross, kept = [], {}, []
    for name, v in bvals:
        m = clone(base)
        group, col = name.split(".", 1)
        locs = [(r, fn, sc) for r, fn, sc in csv_locations(m, group) if col in r and r[col] is not None]
        for r, fn, sc in locs:
            r[col] = v
        fnd = check(serialize(m, file_cols))
        local = [x for x in fnd if x.severity == "ERROR" and x.field == name and x.rule_id.split(".", 1)[0] in ("REQ", "DTYPE", "REGEX", "ENUM", "RANGE")]
        boundary_local += [(name, v, x.rule_id) for x in local]
        errs = [x for x in fnd if x.severity == "ERROR"]
        if errs:
            boundary_cross[f"{name}={v}"] = sorted({x.rule_id for x in errs})
        else:
            kept.append((name, v))
    # 서로 부딪히지 않는 끝값을 한 표본에 모음 (같은 필드는 하나만)
    m = clone(base)
    used = set()
    combo = []
    for name, v in kept:
        if name in used:
            continue
        group, col = name.split(".", 1)
        trial = clone(m)
        for r, fn, sc in csv_locations(trial, group):
            if col in r and r[col] is not None:
                r[col] = v
        if not [x for x in check(serialize(trial, file_cols)) if x.severity == "ERROR"]:
            m = trial
            used.add(name)
            combo.append((name, v))
    boundary_combined = [x for x in check(serialize(m, file_cols)) if x.severity == "ERROR"]
    rep.update(boundary_n=len(bvals), boundary_local=boundary_local, boundary_cross=boundary_cross,
               boundary_combined_fields=len(combo), boundary_combined_error=boundary_combined)
    timing["경계"] = time.perf_counter() - t0

    # 고장
    t0 = time.perf_counter()
    results = []
    for name, rid, field, value, pre in auto_faults(fields, rules):
        if value is DROP:
            group, col = field.split(".", 1)
            if group == "meta":
                m = clone(base)
                del _scan(m)["meta"][col]
                fs = serialize(m, file_cols)
            else:
                fs = serialize(base, file_cols)
                drop_column(fs, first_present(base, field)[1], col)
            fnd = check(fs)
        else:
            fnd = check(serialize(apply_field(base, field, value, pre), file_cols))
        ids = {x.rule_id for x in fnd if x.severity == "ERROR"}
        results.append({"kind": "자동", "name": name, "expected": rid, "detected": rid in ids, "got": sorted(ids)[:12]})
    timing["자동고장"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    for name, rid, fm, fb in hand_faults():
        m = clone(base)
        if fm:
            fm(m)
        fs = serialize(m, file_cols)
        if fb:
            fb(fs)
        fnd = check(fs)
        ids = {x.rule_id for x in fnd if x.severity == "ERROR"}
        results.append({"kind": "손", "name": name, "expected": rid, "detected": rid in ids, "got": sorted(ids)[:12]})
    warns = []
    for name, rid, fm, *fb in warn_tests():
        m = clone(base)
        if fm:
            fm(m)
        fs = serialize(m, file_cols)
        for f in fb:
            f(fs)
        fnd = check(fs)
        ids = {x.rule_id for x in fnd if x.severity == "WARN"}
        warns.append({"name": name, "expected": rid, "detected": rid in ids})
    # 기본 켬 규칙 (D-21 채택 X4 · X7): 기본으로 WARN이 나오고, disabled_rules로 끄면 안 나와야 함
    for name, rid, fm in switch_tests():
        m = clone(base)
        fm(m)
        fs = serialize(m, file_cols)
        on_ids = {x.rule_id for x in check(fs) if x.severity == "WARN"}
        off = Validator(fields, rules_list, file_cols, disabled_rules={rid}, repo_exists=repo_exists)
        off_ids = {x.rule_id for x in off.run(MemFS(fs), CAMPAIGN)}
        warns.append({"name": f"[스위치] {name}", "expected": rid, "detected": rid in on_ids and rid not in off_ids})
    # 두 단 비 경고 (v1.1): 양성은 W-REF-25가 나와야, 음성 · 경계 아래는 안 나와야 통과. 모두 ERROR 0 (형식은 맞는 데이터)
    for name, fm, want in ratio_tests():
        m = clone(base)
        fm(m)
        fnd = check(serialize(m, file_cols))
        got = any(x.rule_id == "W-REF-25" for x in fnd)
        errs = sorted({x.rule_id for x in fnd if x.severity == "ERROR"})
        warns.append({"name": f"[두 단 비] {name}", "expected": "W-REF-25" if want else "W-REF-25 없음",
                      "detected": got == want and not errs, "errors": errs})
    # 참값 (부록 A): judgement ⇔ pass_pct, v1.0 새 참값 필드 (캠페인 사실 ctx와 대조)
    for name, obj, rid, tctx in truth_tests():
        ids = {x.rule_id for x in V.check_truth(obj, ctx=tctx) if x.severity == "ERROR"}
        if rid is None:
            if ids:
                rep["normal_error"].extend(V.check_truth(obj, ctx=tctx))
        else:
            results.append({"kind": "손", "name": f"[참값] {name}", "expected": rid, "detected": rid in ids, "got": sorted(ids)})
    timing["손고장·경고"] = time.perf_counter() - t0
    rep.update(faults=results, warns=warns, timing_s={k: round(v, 2) for k, v in timing.items()})
    n = len(results)
    d = sum(r["detected"] for r in results)
    rep["summary"] = {
        "normal_error": len(rep["normal_error"]),
        "boundary_error": len(boundary_local) + len(boundary_combined),
        "n_fault": n, "n_auto": sum(r["kind"] == "자동" for r in results), "n_hand": sum(r["kind"] == "손" for r in results),
        "n_detected": d, "rate": 100.0 * d / n if n else 0.0,
        "warn_ok": sum(w["detected"] for w in warns), "warn_n": len(warns),
    }
    s = rep["summary"]
    rep["line"] = (f"SELFTEST 정상위반={s['normal_error']} 경계위반={s['boundary_error']} 고장={n} 탐지={d} "
                   f"탐지율={s['rate']:.1f}% 경고확인={s['warn_ok']}")
    return rep
