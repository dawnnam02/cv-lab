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
    rows, imgs = [], {}
    n = n_on + n_off
    for i in range(n):
        img = png_bytes(seed0 + i)
        f = f"frames/{i:06d}.png"
        imgs[f] = img
        rows.append({
            "scan_id": scan_id, "layer_idx": layer_idx, "frame_idx": i, "file": f, "sha256": sha256_bytes(img),
            "t_cam_ns": 1_000_000 + i * DT, "t_host_ns": t0 + (i + 1) * DT, "cam_seq": 1201 + i,
            "exposure_us": 800.0, "gain_db": 0.0, "bit_depth": 8, "pixel_format": "GRAY8", "lossy": False,
            "roi_x0_px": 0, "roi_y0_px": 272, "roi_w_px": 32, "roi_h_px": 16,
            "laser_on": not (laser_off_first and i < n_off), "trigger_mode": "free", "dropped_before": 0,
            "saturated_px": 0, "sensor_temp_c": 41.5,
        })
    return rows, imgs


def _pos(scan_id, layer_idx, layer_end, S, z_top):
    E = S + 83_333_333  # 0.2 mm ÷ 2.4 mm/s [계산]
    off = S - 1_000_000
    base = {"scan_id": scan_id, "x_mm": 110.0, "e_mm": 152.331, "layer_idx": layer_idx, "pass_idx": 0, "mesh_dz_mm": 0.012,
            "clock_offset_ns": None, "acc_x_mm_s2": None, "acc_y_mm_s2": None, "acc_z_mm_s2": None}
    rows = [
        dict(base, t_ns=layer_end, clock="host", source="cmd", y_mm=90.0, z_mm=z_top - 2.0, feed_mm_s=40.0, event="layer_change"),
        dict(base, t_ns=S, clock="host", source="cmd", y_mm=90.0, z_mm=z_top, feed_mm_s=2.4, event="scan_start"),
    ]
    for j in range(1, 4):
        rows.append(dict(base, t_ns=1_000_000 + j * DT, clock="mcu", source="report", y_mm=round(90.0 + 0.02 * j, 4), z_mm=z_top,
                         feed_mm_s=2.4, event="none", clock_offset_ns=off, acc_x_mm_s2=12.5, acc_y_mm_s2=-3.1, acc_z_mm_s2=0.8))
    rows.append(dict(base, t_ns=E, clock="host", source="cmd", y_mm=90.2, z_mm=z_top, feed_mm_s=2.4, event="scan_end"))
    return rows


def _ref(ref_id, kind, scan_id, layer_idx, t_start, seed, marker=True):
    frows, imgs = _frames(scan_id or "S00_r00", layer_idx if layer_idx is not None else 0, t_start - DT, 2, 0, seed, False)
    row = {"ref_id": ref_id, "kind": kind, "scan_id": scan_id, "layer_idx": layer_idx, "n_frames": 2, "frames_dir": "frames/",
           "marker_id": "MK01" if marker else None, "marker_x_mm": 60.0 if marker else None, "marker_y_mm": 90.0 if marker else None,
           "t_start_ns": t_start, "calibration_id": CAL, "line_peak_pct": 72.0 if marker else None,
           "note": "층 끝 마커 MK01 재측정" if marker else "출력 전 베드 기준"}
    return {"index": [row], "frames": frows, "images": imgs}


def _meta(lay, layer_idx, layer_z, layer_end, S, dt_text, post=False):
    m = {
        "scan_id": f"{SR}" if post else f"{SR}_L{layer_idx:03d}", "campaign_id": CAMPAIGN, "session_id": SESSION,
        "source": "virtual", "spec_version": "1.0", "specimen_id": "S01", "specimen_role": "user_gcode", "repeat": 1,
        "datetime": dt_text, "operator": "sim", "notes": "-",
        "timing": "post" if post else "layer", "layer_idx": layer_idx, "layer_count": 2, "layer_z_mm": layer_z,
        "gcode_line_start": 1 + 100 * layer_idx, "gcode_line_end": 100 + 100 * layer_idx,
        "layer_end_t_ns": layer_end, "scan_start_t_ns": S, "wait_after_layer_s": (S - layer_end) / 1e9,
        "pause_added_s": 0.0 if post else 35.0, "layer_time_s": None if post else 45.0,
        "scan_z_hop_mm": 2.0, "scan_axis": "+Y", "scan_x_mm": 110.0, "scan_y0_mm": 90.0,
        "process": "FDM", "printer_model": "PRINTER-A", "firmware": "klipper-unknown", "mesh_enabled": True,
        "control_group": "none", "enclosure": True, "slicer_profile_file": "data/gcode/S01_profile.ini",
        "gcode_file": "data/gcode/S01_user_part.gcode",
        "gcode_sha256": "3f5a0c1e9b7d2a4f6e8c0b1d3f5a7c9e1b3d5f7a9c1e3b5d7f9a1c3e5b7d9f1a",
        "material": "PLA", "color": "gray", "translucency": "opaque", "filament_lot": "sim",
        "nozzle_dia_mm": 0.4, "layer_h_mm": 0.2, "top_layers": 4, "infill_angle_deg": 45.0, "step_edge_angle_deg": None,
        "nozzle_temp_c": 30.0 if post else 205.0, "bed_temp_c": 25.0 if post else 60.0, "room_temp_c": 22.4,
        "room_humidity_pct": 45.0, "camera_temp_c": 38.0, "laser_temp_c": 40.0,
        "specimen_temp_c": 23.1 if post else 55.0, "part_fan_pct": 100.0, "ambient_light": "enclosure_dark",
        "bed_ref_id": "REF-BED-001", "z_offset_mm": -0.15, "zero_ref_method": "bed_marker",
        "bed_mesh_file": "printer/bed_mesh.json", "thermal_state": "cooled" if post else "in_process",
        "paired_scan_id": f"{SR}_L001" if post else None, "cool_wait_s": (S - layer_end) / 1e9 if post else None,
        "tolerance_mm": 0.20, "slicer_name": "SLICER-A 0.0", "gcode_flavor": "marlin", "firmware_name": "klipper",
        "firmware_version": "unknown", "host_software": "none", "layer_macro_version": "LM-0.0",
        "sensor_model": "M54-nozzle-line-v1", "cam_model": "OV9281", "cam_shutter": "global", "cam_interface": "sim",
        "cam_pixel_um": 3.0, "cam_res_w_px": 1280, "cam_res_h_px": 800, "lens_f_mm": 8.0, "lens_f_number": 4.0,
        "lens_focus_locked": True, "wd_mm": 50.0, "magnification": 0.19, "laser_wavelength_nm": 450.0,
        "laser_power_mw": 1.0, "laser_power_pct": 60.0, "laser_class": "2", "triang_angle_deg": 30.0,
        "filter_center_nm": 450.0, "filter_fwhm_nm": 10.0, "exposure_set_us": 800.0, "gain_set_db": 0.0,
        "frame_avg_n": 1, "scan_speed_mm_s": 2.4, "scan_pitch_mm": 0.02, "scan_length_mm": 0.2, "fps": FPS,
        "n_frames": 12, "raw_saved": True, "proc_time_s": None, "acq_id": "ACQ-2026-11-20-A",
        "calibration_id": CAL, "fid_id": None, "frames_doc_version": "C4-1.0", "software_git": "ff4b01b",
        "files_sha256": AUTO, "sim_version": "sim-0.1.0", "sim_seed": 20261120, "injected_factors": ["MF-SYN-01"],
    }
    return m


def normal_model() -> dict:
    """최소 정상 캠페인: 세션 1, 시편·반복 1, 층 2 + post."""
    scans = {}
    seed = 1000
    plan = [("L000", 0, 0.2, 100_000_000_000, "2026-11-20T14:20:00+09:00", False),
            ("L001", 1, 0.4, 300_000_000_000, "2026-11-20T14:24:00+09:00", False),
            ("post", 1, 0.4, 300_000_000_000, "2026-11-20T14:57:00+09:00", True)]
    for lay, li, z, le, dtt, post in plan:
        S = le + (1_800_000_000_000 if post else 15_000_000_000)
        meta = _meta(lay, li, z, le, S, dtt, post)
        sid = meta["scan_id"]
        frows, imgs = _frames(sid, li, S, 10, 2, seed)
        seed += 100
        ref_id = f"REF-MRK-{len(scans):03d}"
        scans[lay] = {"meta": meta, "frames": frows, "images": imgs, "pos": _pos(sid, li, le, S, z + 2.0),
                      "refs": {ref_id: _ref(ref_id, "bed_marker", sid, li, frows[0]["t_host_ns"] - 5_000_000_000, seed)}}
        seed += 100
    sref = {"REF-BED-001": _ref("REF-BED-001", "bed_bare", None, None, 50_000_000_000, 9000, marker=False)}
    calrow = {"cal_id": CAL, "kind": None, "created": None, "target_type": None, "target_rows": None, "target_cols": None,
              "target_square_mm": None, "target_marker_mm": None, "target_dict": None, "target_flatness_um": None,
              "pose_idx": 0, "image_file": None, "laser_on": False, "exposure_us": 800.0, "cmd_z_mm": None, "cmd_move_mm": None,
              "feature_id": None, "feature_x_mm": None, "feature_y_mm": None, "nozzle_touch_z_mm": None,
              "gauge_nominal_mm": None, "gauge_measured_mm": None, "gauge_u_um": None, "temp_c": 22.4,
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
        dict(calrow, kind="D4", created="2026-11-20T11:10:00+09:00", target_type="coord_plate", image_file="d4/plate_00.png",
             laser_on=True, feature_id="P02_03", feature_x_mm=104.0, feature_y_mm=96.0, nozzle_touch_z_mm=2.03,
             result_file=rf + "nozzle_sensor.yaml"),
        dict(calrow, kind="D5", created="2026-11-20T11:30:00+09:00", target_type="filler_gauge", image_file="d5/gauge_0p20_000.png",
             laser_on=True, gauge_nominal_mm=0.2, gauge_measured_mm=0.203, gauge_u_um=1.0, temp_c=22.5,
             result_file=rf + "verification.yaml"),
    ]
    res = []
    for k, f, extra in (("D1", "camera_intrinsics", {"reproj_rms_px": 0.12}), ("D2", "laser_plane", {"plane_rms_um": 3.0}),
                        ("D3", "scan_axis", {}), ("D4", "nozzle_sensor", {}), ("D5", "verification", {})):
        res.append(dict({"cal_id": CAL, "kind": k, "result_file": rf + f + ".yaml", "reproj_rms_px": None, "plane_rms_um": None,
                         "valid_from": "2026-11-20T12:00:00+09:00", "valid_until": "2026-12-20T12:00:00+09:00",
                         "invalidated_by": "none"}, **extra))
    calimgs = {r["image_file"]: png_bytes(5000 + i) for i, r in enumerate(man)}
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
            if name in ("cal.image_file", "cal.nozzle_touch_z_mm"):
                pass  # 조건을 데이터로 못 정함 (보류)
            else:
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
    mod("bed_marker 짝 기준 없음", "X-MET-29", lambda m: _scan(m)["refs"].clear())
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
    mod("게이지 실측 − 공칭 > 0.02", "X-CAL-08", lambda m: man(m)[7].update(gauge_measured_mm=0.23))
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
    mod("bed_bare인데 layer_idx 있음", "CROSS-EMPTY.ref.layer_idx",
        lambda m: m["sessions"][SESSION]["refs"]["REF-BED-001"]["index"][0].update(layer_idx=0))
    mod("in_process인데 paired_scan_id 있음", "CROSS-EMPTY.meta.paired_scan_id", lambda m: me(m).update(paired_scan_id="S01_r01_L001"))
    mod("D1 행에 cmd_z_mm", "CROSS-EMPTY.cal.cmd_z_mm", lambda m: man(m)[0].update(cmd_z_mm=1.0))
    mod("설계 파일에 scan_id", "CROSS-EMPTY.rep.scan_id", lambda m: des(m)[0].update(scan_id="S01_r01_L000"))
    mod("user_gcode인데 단차 각", "CROSS-EMPTY.meta.step_edge_angle_deg", lambda m: me(m).update(step_edge_angle_deg=0.0))
    mod("raw_saved false인데 frame.file 있음", "CROSS-EMPTY.frame.file", lambda m: me(m).update(raw_saved=False))
    return H


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


def warn_tests() -> list[tuple]:
    """경고 규칙이 실제로 나오는지 (이름, 기대 규칙 ID, 모형 고침)."""
    return [
        ("D1 재투영 RMS 0.25", "W-CAL-11", lambda m: m["cal"][CAL]["cal_results.csv"][0].update(reproj_rms_px=0.25)),
        ("D2 평면 RMS 6", "W-CAL-12", lambda m: m["cal"][CAL]["cal_results.csv"][1].update(plane_rms_um=6.0)),
        ("무효화된 교정", "W-CAL-13", lambda m: m["cal"][CAL]["cal_results.csv"][2].update(invalidated_by="remount")),
        ("작은 층", "W-MET-15", lambda m: _scan(m)["meta"].update(layer_time_s=10.0)),
        ("Z hop 0.5", "W-MET-16", lambda m: _scan(m)["meta"].update(scan_z_hop_mm=0.5)),
        ("실측인데 초점 고정 안 함", "W-MET-38", lambda m: _scan(m)["meta"].update(source="real", lens_focus_locked=False)),
        ("레이저 1.5 mW", "W-MET-39", lambda m: _scan(m)["meta"].update(laser_power_mw=1.5)),
        ("line_peak 20 % 넘게 떨어짐", "W-REF-09", lambda m: next(iter(_scan(m, "L001")["refs"].values()))["index"][0].update(line_peak_pct=50.0)),
        ("펌웨어 이름 허용 밖 [대기: T14]", "ENUM.meta.firmware_name", lambda m: _scan(m)["meta"].update(firmware_name="zzz", firmware="zzz-unknown")),
    ]


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------
def run_selftest(fields: list[dict], rules_list: list[dict], file_cols: dict, disk: bool = True) -> dict:
    """disk=True면 정상 표본을 임시 폴더에도 써서 디스크 경로로 한 번 더 검사한다."""
    rules = {r["rule_id"]: r for r in rules_list}
    V = Validator(fields, rules_list, file_cols)

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
    for name, rid, fm in warn_tests():
        m = clone(base)
        fm(m)
        fnd = check(serialize(m, file_cols))
        ids = {x.rule_id for x in fnd if x.severity == "WARN"}
        warns.append({"name": name, "expected": rid, "detected": rid in ids})
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
