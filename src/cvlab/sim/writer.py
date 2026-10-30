# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""쓰기 (세부청사진 §6.1 ⑦, S5). 명세 형식 raw (data/raw/<campaign>) + 참값 (data/_truth/<campaign>)을 따로 씀.

- 명세 판 · 이름 규칙 · 반복 `_qNN` · C2 공차는 `specdefs` 한 곳 (v1.2 초안). 열 순서는 검증기 스키마.
- 파일은 모두 한 번 쓰기 (`cvlab.io.writeonce`), 이미 있으면 오류. 스캔 폴더는 reference/ 를 먼저 쓰고 meta.json을
  마지막에 써서 `meta.files_sha256`이 그 폴더 모든 파일을 담게 함.
- PNG는 압축 수준 고정 (설정 `camera.png_level`, 기본 3), 시각 조각 없음. JSON 키 순서는 열 순서 그대로.
- raw에는 참값 글자를 쓰지 않음 (참값 · 시뮬레이터 내부 값은 truth 뿌리에만).
"""
from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from cvlab.io.writeonce import create_dir_once, write_bytes_once, write_csv_once, write_json_once

from .camera import Sensor, frame_times
from .clock import VirtualClock
from .optics import (LineRenderer, PlaneSurface, Speckle, charuco_texture, dots_texture, load_aruco_bits,
                     render_plane, rot_xyz)
from .scene import Bed, Block, Scene, mesh_json_bytes
from .seeds import SeedTree, seed_tag
from .shape import gauge_temperature, load_specimen, simulate_specimen
from .simconfig import ROOT, load_factors, load_scenarios, merged
from .specdefs import FILES, NO_PAIR_SCAN_ID, SPEC_VERSION, file_columns, layer_dir
from .timeline import build_timeline

SWITCH_DEFAULTS = {"speckle": True, "subsurface_scatter": True, "subsurface_stress": False, "hot_gloss": True,
                   "occlusion": True, "room_light": False}


def png_bytes(img: np.ndarray, level: int) -> bytes:
    b = io.BytesIO()
    if img.dtype not in (np.uint8, np.uint16):
        raise ValueError(f"PNG는 uint8 · uint16만: {img.dtype}")
    Image.fromarray(img).save(b, format="PNG", compress_level=int(level), optimize=False)   # uint8 → L, uint16 → I;16
    return b.getvalue()


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _fl(v, nd=4):
    return None if v is None else round(float(v), nd)


class Writer:
    def __init__(self, cfg: dict, camp: dict, seed: int, raw_root, truth_root, blind: bool = False,
                 switches: dict | None = None):
        self.cfg = merged(cfg, camp.get("overrides"))
        self.camp = camp
        self.seed = seed
        self.tree = SeedTree(seed)
        self.blind = blind
        self.raw_root, self.truth_root = Path(raw_root), Path(truth_root)
        fac = load_factors()
        self.factors = fac
        self.sw = {k: bool(v["enabled"]) for k, v in fac.items()}
        self.sw.update(switches or {})
        self.cols = file_columns()
        self.png_level = int(self.cfg["camera"].get("png_level", 3))
        self.stats = {"frames": 0, "bytes_raw": 0, "bytes_disk": 0, "scans": 0, "files": 0}
        self.valid_ratio = []

    def _png_async(self, img):
        """PNG 인코딩을 스레드 2개에 넘김 (zlib은 GIL을 놓음 → 렌더와 겹침). 결과 바이트는 순서 · 내용 그대로."""
        if self.__dict__.get("_pool") is None:
            from concurrent.futures import ThreadPoolExecutor
            self._pool = ThreadPoolExecutor(max_workers=int(self.cfg["camera"].get("png_threads", 2)))
        return self._pool.submit(png_bytes, img, self.png_level)

    # 시각 ---------------------------------------------------------------
    def wall_iso(self, host_ns: int) -> str:
        c = VirtualClock(self.cfg["clock"]["start_iso"])
        c.advance((host_ns - self.tl.boot_ns) / 1e9)
        return c.iso("milliseconds")

    # 파일 ---------------------------------------------------------------
    def _wb(self, path: Path, data: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        write_bytes_once(path, data)
        self.stats["bytes_disk"] += len(data)
        self.stats["files"] += 1

    def _wcsv(self, path: Path, rows: list, key: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        write_csv_once(path, rows, self.cols[key])
        self.stats["files"] += 1

    # 준비 ---------------------------------------------------------------
    def prepare(self):
        cfg, camp = self.cfg, self.camp
        if len(camp["specimens"]) != 1:
            raise NotImplementedError("S5 writer: 캠페인당 시편 하나 (여러 시편은 S6)")
        se = camp["specimens"][0]
        self.se = se
        self.spec = load_specimen(cfg, se["name"])
        n_print = self.spec.n_layers if se.get("print_layers", "all") == "all" else int(se["print_layers"])
        self.n_layers = n_print
        scen = load_scenarios()["scenarios"][se["scenario"]]
        self.maps = {}
        shape_sw = {k: self.sw[k] for k in ("layer_thermal_field", "z_axis_error", "frame_drift", "bead_model_bias",
                                            "bead_texture")}
        st = self.tree.child(se["specimen_id"], int(se["repeat"]))
        self.shape = simulate_specimen(self.spec, cfg, [scen["print_error_params"]], base=camp["base"], factors=shape_sw,
                                       seed_tree=st, on_heightmap=lambda s, k, H: self.maps.__setitem__(k, H),
                                       n_print_layers=n_print)[0]
        zp = dict(self.shape["z_axis_error_params"])
        tl_sw = {k: self.sw[k] for k in ("pulse_delay", "lens_residual", "bed_zero_error") if k in self.sw}
        tl_sw["bed_mesh_z"] = self.sw.get("bed_mesh_z", True)
        self.tl = build_timeline(cfg, camp, self.seed, se, self.spec.z_layers[:n_print], self.spec.bbox, zparams=zp,
                                 switches=tl_sw, blind=self.blind)
        g = self.tl.geometry
        rsw = {k: self.sw.get(k, v) for k, v in SWITCH_DEFAULTS.items()}
        self.renderer = LineRenderer(g, cfg["optics"], rsw)
        gf = dataclasses.replace(g, roi_y0=0, roi_h=g.height)
        self.renderer_full = LineRenderer(gf, cfg["optics"], rsw)
        self.geom_full = gf
        self.sensor = Sensor.create(cfg["camera"], g.width, g.height, self.tree.child("camera", "fpn").rng())
        self.injected = sorted({m for k, v in self.factors.items() if self.sw.get(k) for m in v["mf"]})
        # 반복 (MSA) 스캔의 잡음 시드 = design 행 값 (rep.noise_seed와 같게)
        self.msa_noise = {r["scan_id"]: r["noise_seed"] for r in self.tl.msa[1]} if not self.blind else {}
        msa_seeds = {}
        for d, e in zip(*self.tl.msa):
            msa_seeds[e["scan_id"]] = self.tree.child("msa", d["study_id"], d["repeat_idx"]).int_seed()
        self.msa_seed_true = msa_seeds
        self.layers_parse = self.spec.result.layers
        self.scan_seeds = {}

    # 장면 ---------------------------------------------------------------
    def gauge_temp_true(self, host_ns: int) -> float:
        t = (host_ns - self.tl.boot_ns) / 1e9 - self.tl.t_print0_s
        return gauge_temperature(self.cfg["gauge_thermal"], max(t, 0.0))

    def blocks(self, host_ns: int) -> list:
        st, T = self.cfg["steps"], self.gauge_temp_true(host_ns)
        wx, wy = st["footprint_mm"]
        out = []
        for gid, x in zip(st["ids"], st["laser_x_mm"]):
            if gid == "GB-00":
                continue
            out.append(Block(gid, x - wx / 2, x + wx / 2, st["y0_mm"] - 5.0, st["y0_mm"] - 5.0 + wy,
                             self.tl.gauges.true_at(gid, T)))
        return out

    def scene_for(self, key, host_ns: int, z_top: float | None = None, specimen: bool = True) -> Scene:
        """key: 'L004' · 'post' (참 높이맵 키는 층 번호 정수 · 'post')."""
        if isinstance(key, str) and key.startswith("L"):
            key = int(key[1:])
        H = self.maps.get(key) if specimen else None
        hot = None
        if specimen and key != "post" and z_top is not None:
            hot = z_top - 0.6 * float(self.layers_parse["layer_h_mm"].iloc[int(key)])
        g = self.spec.grid
        return Scene(self.tl.bed, hmap=H, origin=(g["x0_mm"], g["y0_mm"]), step=g["res_mm"],
                     blocks=self.blocks(host_ns), hot_above_mm=hot)

    # 프레임 -------------------------------------------------------------
    def _frame_row(self, scan_id, layer_idx, idx, t_host, laser_on, pulse, dropped, sat, trig="hw"):
        c = self.cfg["camera"]
        g = self.tl.geometry
        return dict(scan_id=scan_id, layer_idx=layer_idx, frame_idx=idx, file=f"frames/{idx:06d}.png", sha256=None,
                    t_cam_ns=None, t_host_ns=int(t_host), cam_seq=None, exposure_us=float(c["exposure_us"]),
                    gain_db=float(c["gain_db"]), bit_depth=int(c["bit_depth"]), pixel_format=self.sensor.pixel_format,
                    lossy=False, roi_x0_px=0, roi_y0_px=g.roi_y0, roi_w_px=g.width, roi_h_px=g.roi_h,
                    laser_on=laser_on, trigger_mode=trig, trig_pulse_idx=pulse, gate_on=None,
                    dropped_before=int(dropped), saturated_px=int(sat), sensor_temp_c=float(c["sensor_temp_c"]))

    def line_frames(self, L, scene, scan_id: str, layer_idx: int, noise_seed: int, spk_seed: int):
        """(파일 목록 [(이름, 바이트)], frames_index 행, 유효 열 비율 평균, 최대 밝기 %)."""
        c, g, T = self.cfg["camera"], self.tl.geometry, self.cfg["motion"]["trigger_period_s"]
        rng = np.random.default_rng(noise_seed)
        spk = Speckle(self.cfg["optics"]["speckle_contrast"], self.cfg["optics"]["speckle_corr_u_px"],
                      self.cfg["optics"]["speckle_corr_v_px"], self.cfg["optics"]["speckle_rho_frame"],
                      np.random.default_rng(spk_seed), (g.roi_h, g.width))
        files, rows = [], []
        nb = int(c["background_frames"])
        bkg_irr, _ = self.renderer.render_line(scene, np.zeros(3), laser_on=False)
        t0 = L.t_m400_ns + int(round(self.cfg["motion"]["gcode_roundtrip_s"] * 1e9))
        peak = 0
        for i in range(nb):  # 도움닫기 동안 레이저 끈 배경
            img, sat = self.sensor.expose(bkg_irr, g.roi_y0, rng)
            rows.append(self._frame_row(scan_id, layer_idx, i, t0 + int(round((i + 1) * T * 1e9)), False, None, 0, sat))
            files.append((f"frames/{i:06d}.png", self._png_async(img)))
        keep, th, drop = frame_times(L.t_pulse_ns, c, rng, c.get("drop_prob_on", 0.0) if self.sw.get("frame_drop") else 0.0)
        valid = []
        for j, k in enumerate(keep):
            O = np.array([L.x_nozzle, L.y_nozzle_act[k], L.z_nozzle_act[k]]) + g.offset_g
            irr, info = self.renderer.render_line(scene, O, speckle=spk, with_info=True)
            valid.append(info["valid_cols"] / g.width)
            img, sat = self.sensor.expose(irr, g.roi_y0, rng)
            peak = max(peak, int(img.max()))
            idx = nb + j
            rows.append(self._frame_row(scan_id, layer_idx, idx, th[j], True, int(k), drop[j], sat))
            files.append((f"frames/{idx:06d}.png", self._png_async(img)))
        files = [(n, f.result()) for n, f in files]   # PNG 인코딩은 스레드에서 렌더와 겹침 (같은 바이트)
        for r, (_, b) in zip(rows, files):
            r["sha256"] = sha(b)
        self.stats["frames"] += len(rows)
        self.stats["bytes_raw"] += len(rows) * g.width * g.roi_h * (1 if self.sensor.max_dn <= 255 else 2)
        return files, rows, float(np.mean(valid)) if valid else 0.0, 100.0 * peak / self.sensor.max_dn

    def static_frames(self, kind: str, n: int, scan_id: str, noise_seed: int, host_ns: int):
        """배경 · 암흑 · 정지 반복 (자유 실행, 펄스 없음). 정지라 스펙클 무늬도 같음 → 한 번 렌더."""
        g = self.tl.geometry
        rng = np.random.default_rng(noise_seed)
        scene = Scene(self.tl.bed, blocks=[])
        O = np.array([100.0, 100.0, float(self.tl.bed.surface(100.0, 100.0)) + float(self.tl.bed.mesh(100.0, 100.0))])
        O = O + g.offset_g - np.array([0.0, 0.0, g.offset_g[2]])  # 정지 반복은 초점면을 베드에
        laser = kind == "static_repeat"
        irr, _ = self.renderer.render_line(scene, O, laser_on=laser,
                                           speckle=Speckle(self.cfg["optics"]["speckle_contrast"], 3.0, 1.7, 1.0,
                                                           np.random.default_rng(noise_seed + 1), (g.roi_h, g.width))
                                           if laser else None)
        files, rows, peak = [], [], 0
        T = self.cfg["motion"]["trigger_period_s"]
        for i in range(n):
            img, sat = self.sensor.expose(irr, g.roi_y0, rng, shutter_open=(kind != "dark"))
            peak = max(peak, int(img.max()))
            rows.append(self._frame_row(scan_id, -1, i, host_ns + int(round((i + 1) * T * 1e9)), laser, None, 0, sat,
                                        trig="free"))
            files.append((f"frames/{i:06d}.png", self._png_async(img)))
        files = [(nm, f.result()) for nm, f in files]
        for r, (_, b) in zip(rows, files):
            r["sha256"] = sha(b)
        self.stats["frames"] += n
        self.stats["bytes_raw"] += n * g.width * g.roi_h
        return files, rows, 100.0 * peak / self.sensor.max_dn

    # 위치 로그 ------------------------------------------------------------
    @staticmethod
    def pos_rows(L, scan_id: str, layer_idx: int | None = None) -> list:
        out = []
        for r in L.rows:
            rr = dict(r, scan_id=scan_id, clock_offset_ns=None, acc_x_mm_s2=None, acc_y_mm_s2=None, acc_z_mm_s2=None)
            if layer_idx is not None:
                rr["layer_idx"] = layer_idx
            out.append(rr)
        return out

    # meta -----------------------------------------------------------------
    def meta(self, *, scan_id, spass, timing, layer_idx, L, frames_rows, files_sha, sim_seed, layer_end_ns,
             pause_s, paired=None):
        cfg, sp, se = self.cfg, self.spec, self.se
        lay = self.layers_parse.iloc[layer_idx]
        hdr = sp.result.header
        o, cam, mo = cfg["optics"], cfg["camera"], cfg["motion"]
        first_t = frames_rows[0]["t_host_ns"]
        wait = (L.scan_start_ns - layer_end_ns) / 1e9
        th = self.shape["thermal_params"]
        spec_temp = (th.get("post_temp_c") if timing == "post" else (th.get("layer_temp_c") or [None] * 999)[layer_idx]) \
            if th else cfg["thermal"]["t_room_c"]
        gpath = sp.path.resolve().relative_to(ROOT.resolve()).as_posix()
        m = {k: None for k in self.cols["meta.json"]}
        m.update(
            scan_id=scan_id, scan_pass_idx=spass, campaign_id=self.camp["campaign_id"], session_id=self.camp["session_id"],
            source="virtual", spec_version=SPEC_VERSION, specimen_id=se["specimen_id"], specimen_role="public_gcode",
            repeat=int(se["repeat"]), datetime=self.wall_iso(first_t), operator="sim_A", notes="-", timing=timing,
            layer_idx=int(layer_idx), layer_count=int(self.n_layers), layer_z_mm=_fl(lay["layer_z_mm"]),
            gcode_line_start=int(lay["gcode_line_start"]), gcode_line_end=int(lay["gcode_line_end"]),
            layer_end_t_ns=int(layer_end_ns), scan_start_t_ns=int(L.scan_start_ns), wait_after_layer_s=round(wait, 6),
            pause_added_s=round(pause_s, 6) if timing == "layer" else 0.0,
            layer_time_s=float(cfg["specimens"][se["name"]]["layer_print_s"]) if timing == "layer" else None,
            scan_z_hop_mm=float(mo["z_hop_mm"]), scan_axis="+Y", scan_x_mm=_fl(L.x_nozzle), scan_y0_mm=_fl(L.y0_nozzle),
            process="FDM", printer_model="sovol-sv08", printer_kinematics="corexy", bed_motion="fixed", z_drive="belt",
            z_motor_count=4, z_level_method="qgl", probe_type="inductive_pressure", firmware="sovol-klipper-unknown",
            firmware_fork="vendor", mesh_enabled=bool(self.tl.bed.mesh_on), control_group="none", enclosure=True,
            slicer_profile_file=gpath, gcode_file=gpath, gcode_sha256=sp.sha256, material=cfg["calib"]["material"],
            color=cfg["calib"]["color"], translucency="opaque", filament_lot="SIM-LOT-01",
            nozzle_dia_mm=float(hdr.get("nozzle_dia_mm") or 0.4), layer_h_mm=_fl(lay["layer_h_mm"]),
            top_layers=int(hdr.get("top_layers") or 0), infill_angle_deg=float(hdr.get("infill_angle_deg") or 0.0),
            nozzle_temp_c=float(mo["nozzle_temp_c"]), bed_temp_c=float(mo["bed_temp_c"]),
            room_temp_c=float(cfg["thermal"]["t_room_c"]), camera_temp_c=float(cam["sensor_temp_c"]),
            specimen_temp_c=_fl(spec_temp, 3), part_fan_pct=100.0,
            ambient_light="room_light" if self.sw.get("room_light") else "enclosure_dark",
            bed_ref_id=self.bed_ref_ids[spass], z_offset_mm=0.0, zero_ref_method="step_gauge",
            bed_mesh_file=FILES["mesh"] if self.tl.bed.mesh_on else None,
            thermal_state="cooled" if timing == "post" else "in_process", paired_scan_id=paired,
            cool_wait_s=round(wait, 6) if timing == "post" else None, tolerance_mm=0.2,
            slicer_name=str(hdr.get("slicer_name") or "unknown"), gcode_flavor=hdr.get("gcode_flavor") or "other",
            firmware_name="klipper", firmware_version="unknown", host_software="moonraker",
            layer_macro_version=mo["macro_version"], trigger_pin="PLACEHOLDER_PIN", trigger_period_s=float(mo["trigger_period_s"]),
            sensor_model="sim-laser-triangulation-m54", cam_model="OV9281", cam_shutter="global", cam_interface="sim",
            cam_pixel_um=float(o["pixel_um"]), cam_res_w_px=int(o["sensor_w_px"]), cam_res_h_px=int(o["sensor_h_px"]),
            lens_f_mm=float(o["focal_mm"]), lens_f_number=float(o["f_number"]), lens_focus_locked=True,
            wd_mm=float(o["working_distance_mm"]), magnification=0.19, laser_wavelength_nm=450.0, laser_power_mw=1.0,
            laser_class="2", triang_angle_deg=float(o["triang_angle_deg"]), filter_center_nm=450.0, filter_fwhm_nm=10.0,
            exposure_set_us=float(cam["exposure_us"]), gain_set_db=float(cam["gain_db"]), frame_avg_n=1,
            scan_speed_mm_s=float(mo["scan_speed_mm_s"]), scan_pitch_mm=0.02, scan_length_mm=_fl(L.length),
            fps=float(cam["fps"]), n_frames=len(frames_rows), raw_saved=True, acq_id=self.acq_id,
            calibration_id=self.camp["calibration_id"], frames_doc_version="1", software_git=self.git,
            files_sha256=files_sha, sim_version=cfg["run"]["sim_version"],
            sim_seed=None if self.blind else int(sim_seed), injected_factors=[] if self.blind else self.injected,
            blind=bool(self.blind))
        return m

    # 스캔 폴더 ----------------------------------------------------------
    def write_scan_folder(self, folder: Path, files, frame_rows, pos_rows, meta_fn):
        create_dir_once(folder)
        for name, b in files:
            self._wb(folder / name, b)
        self._wcsv(folder / FILES["frames"], frame_rows, "frames_index.csv")
        self._wcsv(folder / FILES["pos"], pos_rows, "position_log.csv")
        fs = {}
        for p in sorted(folder.rglob("*")):
            if p.is_file() and p.name != "meta.json":
                fs[p.relative_to(folder).as_posix()] = sha(p.read_bytes())
        meta = meta_fn(fs)
        write_json_once(folder / FILES["meta"], {k: meta[k] for k in self.cols["meta.json"]})
        self.stats["scans"] += 1

    def write_ref_folder(self, folder: Path, ref_row: dict, files, frame_rows, pos_rows=None):
        create_dir_once(folder)
        for name, b in files:
            self._wb(folder / name, b)
        self._wcsv(folder / FILES["frames"], frame_rows, "frames_index.csv")
        if pos_rows is not None:
            self._wcsv(folder / FILES["pos"], pos_rows, "position_log.csv")
        self._wcsv(folder / FILES["ref"], [ref_row], "ref_index.csv")

    # 전체 ---------------------------------------------------------------
    def run(self) -> dict:
        from cvlab.repro import git_info
        gi = git_info(ROOT)
        self.git = (gi["commit"][:12] if gi["commit"] != "unknown" else "0000000") + ("-dirty" if gi["dirty"] is True else "")
        self.prepare()
        cfg, camp, tl = self.cfg, self.camp, self.tl
        cid = camp["campaign_id"]
        self.acq_id = "ACQ-" + cid[3:]
        raw = self.raw_root / cid
        create_dir_once(raw)
        self.write_calibration(raw / "calibration" / camp["calibration_id"])
        ses = raw / "sessions" / camp["session_id"]
        self._wb(ses / FILES["mesh"], mesh_json_bytes(tl.bed))
        sid, rep = self.se["specimen_id"], int(self.se["repeat"])
        # 세션 기준
        self.bed_ref_ids = {}
        for row, L in tl.session_refs:
            kind = row["kind"]
            nseed = self.tree.child("ref", row["ref_id"]).int_seed()
            if L is not None:
                sc = self.scene_for(None, L.scan_start_ns, specimen=False)
                files, frs, vr, peak = self.line_frames(L, sc, NO_PAIR_SCAN_ID, -1, nseed, nseed + 7)
                pos = self.pos_rows(L, NO_PAIR_SCAN_ID, -1)
                if kind == "bed_bare":
                    self.bed_ref_ids[row["scan_pass_idx"]] = row["ref_id"]
            else:
                files, frs, peak = self.static_frames(kind, row["n_frames"], NO_PAIR_SCAN_ID, nseed, row["t_start_ns"])
                pos = None
            row = dict(row, n_frames=len(frs), t_start_ns=frs[0]["t_host_ns"],
                       line_peak_pct=round(peak, 2) if kind in ("static_repeat",) else None)
            self.write_ref_folder(ses / "reference" / row["ref_id"], row, files, frs, pos)
        # 층 스캔
        folder_sr = ses / f"{sid}_r{rep:02d}"
        last_ids = {}
        for r in tl.layers:
            n, key = r["layer"], f"L{r['layer']:03d}"
            pause_s = (r["t_resume_ns"] - r["t_layer_end_ns"]) / 1e9
            # 두 단 기준 (첫 줄 폴더 안) 먼저 렌더
            ref_items = self._step_items(r, key)
            for i, L in enumerate(r["lines"]):
                scan = r["scan_ids"][i]
                last_ids[i] = scan
                self._write_specimen_scan(folder_sr / layer_dir(key, i), L, scan, i, "layer", n, key, r["z_top"],
                                          r["t_layer_end_ns"], pause_s, ref_items if i == 0 else [])
            for q, L in enumerate(r["repeats"], start=1):
                scan = r["repeat_ids"][q - 1]
                self._write_specimen_scan(folder_sr / layer_dir(key, 0, q), L, scan, 0, "layer", n, key, r["z_top"],
                                          r["t_layer_end_ns"], pause_s, [], q=q)
        p = tl.post
        last = tl.layers[-1]
        ref_items = self._step_items(p, "post")
        for i, L in enumerate(p["lines"]):
            self._write_specimen_scan(folder_sr / layer_dir("post", i), L, p["scan_ids"][i], i, "post", p["layer"], "post",
                                      p["z_top"], last["t_layer_end_ns"], 0.0, ref_items if i == 0 else [],
                                      paired=last["scan_ids"][i])
        # MSA
        msa = raw / "msa" / "MSA-01"
        self._wcsv(msa / FILES["design"], tl.msa[0], "design.csv")
        self._wcsv(msa / FILES["executed"], tl.msa[1], "design_executed.csv")
        truth = self.write_truth()
        return dict(campaign=cid, seed_tag=seed_tag(self.seed), specimens=[sid], layers=self.n_layers,
                    scans=self.stats["scans"], frames=self.stats["frames"], bytes_raw=self.stats["bytes_raw"],
                    bytes_disk=self.stats["bytes_disk"], faults=[], blind=bool(self.blind), raw=str(raw),
                    truth=str(self.truth_root / cid), valid_ratio_min=round(min(self.valid_ratio), 4) if self.valid_ratio else None,
                    truth_records=len(truth))

    def _step_items(self, r, key):
        items = []
        for S, row in zip(r["steps"], r["step_refs"]):
            nseed = self.tree.child("ref", row["ref_id"]).int_seed()
            sc = self.scene_for(key, S.scan_start_ns, r["z_top"], specimen=True)
            files, frs, vr, peak = self.line_frames(S, sc, row["scan_id"], r["layer"], nseed, nseed + 7)
            row = dict(row, n_frames=len(frs), t_start_ns=frs[0]["t_host_ns"], line_peak_pct=round(peak, 2))
            items.append((row, files, frs, self.pos_rows(S, row["scan_id"], r["layer"])))
        return items

    def _write_specimen_scan(self, folder, L, scan, spass, timing, layer_idx, key, z_top, layer_end_ns, pause_s,
                             ref_items, paired=None, q=0):
        br = self.tree.child("scan", scan)
        sim_seed = br.int_seed()
        noise_seed = self.msa_seed_true.get(scan, br.child("noise").int_seed())
        self.scan_seeds[scan] = {"sim_seed": sim_seed, "noise_seed": noise_seed}
        sc = self.scene_for(key, L.scan_start_ns, z_top, specimen=True)
        files, frs, vr, _ = self.line_frames(L, sc, scan, layer_idx, noise_seed, br.child("speckle").int_seed())
        self.valid_ratio.append(vr)
        pos = self.pos_rows(L, scan)
        create_dir_once(folder)
        for row, rfiles, rfrs, rpos in ref_items:
            self.write_ref_folder(folder / "reference" / row["ref_id"], row, rfiles, rfrs, rpos)

        def meta_fn(fs):
            return self.meta(scan_id=scan, spass=spass, timing=timing, layer_idx=layer_idx, L=L, frames_rows=frs,
                             files_sha=fs, sim_seed=sim_seed, layer_end_ns=layer_end_ns, pause_s=pause_s, paired=paired)
        for name, b in files:
            self._wb(folder / name, b)
        self._wcsv(folder / FILES["frames"], frs, "frames_index.csv")
        self._wcsv(folder / FILES["pos"], pos, "position_log.csv")
        fs = {p.relative_to(folder).as_posix(): sha(p.read_bytes()) for p in sorted(folder.rglob("*"))
              if p.is_file() and p.name != "meta.json"}
        meta = meta_fn(fs)
        write_json_once(folder / FILES["meta"], {k: meta[k] for k in self.cols["meta.json"]})
        self.stats["scans"] += 1

    # 교정 ---------------------------------------------------------------
    def write_calibration(self, folder: Path):
        cfg, tl = self.cfg, self.tl
        create_dir_once(folder)
        g, gf = tl.geometry, self.geom_full
        rng = self.tree.child("calib", "noise").rng()
        bits = load_aruco_bits()
        cz = cfg["calib"]["charuco"]
        tex_c = charuco_texture(cz["square_mm"], cz["rows"], cz["cols"], cz["marker_mm"], bits)
        tex_d = dots_texture(1.0, 0.4)
        rows_by_file = {r["image_file"]: r for r in tl.cal_rows if r["image_file"]}
        pitch = cfg["motion"]["scan_speed_mm_s"] * cfg["motion"]["trigger_period_s"]
        for job in tl.cal_jobs:
            k = job["kind"]
            if k == "D1":
                irr = render_plane(gf, rot_xyz(job["tilt_rad"][0], job["tilt_rad"][1], 0.0), np.array(job["t_s"]), tex_c)
                self._cal_img(folder, job["image_file"], irr, 0, rng)
            elif k == "D2":
                plate = PlaneSurface(heights=(job["plate_top_mm"],), material="bed")
                O = np.array([150.0, 150.0, job["cmd_z_mm"]]) + g.offset_g
                irr, _ = self.renderer_full.render_line(plate, O, laser_on=job["laser_on"])
                self._cal_img(folder, job["image_file"], irr, 0, rng)
            elif k == "D3":
                irr = render_plane(gf, np.eye(3), np.array([0.0, -job["cmd_move_mm"], 0.0]), tex_d)
                self._cal_img(folder, job["image_file"], irr, 0, rng)
            elif k == "D4":
                surf = _cylinder_plate(job)
                for fi in range(job["frames"]):
                    O = np.array([job["x_mm"], job["y_start_mm"] + fi * pitch, job["plate_top_mm"] + job["cyl_h_mm"]])
                    irr, _ = self.renderer.render_line(surf, O)
                    self._cal_img(folder, f"d4/plate_scan/f{fi:05d}.png", irr, g.roi_y0, rng)
            elif k == "D5":
                gid = job.get("gauge_id")
                if gid:
                    h = tl.gauges.true_at(gid, cfg["calib"]["room_temp_c"])
                    surf = Scene(Bed(dict(cfg["bed"], mesh_enabled=False), zero_error=False),
                                 blocks=[Block(gid, 140.0, 160.0, 130.0, 170.0, h)])
                else:  # 재료 조각 (시편과 같은 PLA 산란)
                    h = 2.0
                    surf = Scene(Bed(dict(cfg["bed"], mesh_enabled=False), zero_error=False),
                                 blocks=[Block("MAT", 140.0, 160.0, 130.0, 170.0, h, material="pla")])
                names = [f for f in rows_by_file if f.startswith(f"d5/{job['scan']}/")]
                if gid and job["scan"] == "step_gauge":
                    names = [f for f in names if rows_by_file[f]["gauge_block_id"] == gid]
                for fi, name in enumerate(sorted(names)):
                    O = np.array([150.0, 140.0 + fi * pitch, h]) + g.offset_g - np.array([0, 0, g.offset_g[2]])
                    irr, _ = self.renderer.render_line(surf, O)
                    self._cal_img(folder, name, irr, g.roi_y0, rng)
        self._wcsv(folder / FILES["cal"], tl.cal_rows, "cal_manifest.csv")

    def _cal_img(self, folder, name, irr, roi_y0, rng):
        img, _ = self.sensor.expose(irr, roi_y0, rng)
        self._wb(folder / name, png_bytes(img, self.png_level))
        self.stats["bytes_raw"] += img.size

    # 참값 ---------------------------------------------------------------
    def write_truth(self) -> list:
        tl, sh = self.tl, self.shape
        out = self.truth_root / self.camp["campaign_id"]
        create_dir_once(out)
        tid = f"T-{self.se['specimen_id']}"
        g = self.spec.grid
        fac_params = {}
        for k, v in self.factors.items():
            if self.sw.get(k):
                for m in v["mf"]:
                    fac_params.setdefault(m, {})[k] = self._factor_value(k)
        tg = {k: tl.truth[k] for k in ("cam_k", "cam_dist", "laser_plane", "scan_axis", "t_g_m", "nozzle_sensor_offset_mm",
                                       "gauge_thickness_mm", "gauge_block_heights_mm", "gauge_temp_params")}
        recs = []
        keys = list(range(self.n_layers)) + ["post"]
        for key in keys:
            fn = f"heightmaps/{tid}_post.npy" if key == "post" else f"heightmaps/{tid}_L{key:03d}.npy"
            b = io.BytesIO()
            np.save(b, np.ascontiguousarray(self.maps[key]), allow_pickle=False)
            self._wb(out / fn, b.getvalue())
            rec = dict(campaign_id=self.camp["campaign_id"], truth_id=tid, sim_version=self.cfg["run"]["sim_version"],
                       seed=int(self.seed), heightmap_file=fn, heightmap_origin_mm=[g["x0_mm"], g["y0_mm"]],
                       heightmap_step_mm=g["res_mm"], **tg,
                       scan_seeds=self.scan_seeds if self.blind else None,
                       scan_factors={s: self.injected for s in self.scan_seeds} if self.blind else None,
                       step_heights_mm=None, gcode_sha256=self.spec.sha256, print_error_params=sh["print_error_params"],
                       thermal_params=sh["thermal_params"], z_axis_error_params=sh["z_axis_error_params"],
                       judgement=sh["judgement"], pass_pct=round(sh["pass_pct"], 6), factor_params=fac_params,
                       # v1.2 V12-6: 재료 치우침 참값 {재료: {색: µm}} = 레이저 높이 − 두께 (산란으로 음수)
                       material_offset_um={self.cfg["calib"]["material"]: {
                           self.cfg["calib"]["color"]: round(-tl.truth["material_bias_um"], 4)}})
            recs.append(rec)
        write_json_once(out / FILES["truth"], recs)
        extra = {"bed": tl.truth["bed"], "z_scan_moves_um": tl.truth["z_scan_moves_um"],
                 "material_bias_um": tl.truth["material_bias_um"], "valid_ratio_mean_per_scan": self.valid_ratio,
                 "scan_seeds": self.scan_seeds, "switches": self.sw}
        write_json_once(out / "sim_truth_extra.json", extra)
        return recs

    def _factor_value(self, name):
        c = self.cfg
        table = {"layer_thermal_field": c["thermal"], "z_axis_error": c["z_axis"], "frame_drift": c["z_axis"],
                 "bead_model_bias": c["deposition"], "bead_texture": c["deposition"], "bed_zero_error": c["bed"],
                 "bed_mesh_z": c["bed"], "frame_drop": {"drop_prob": c["camera"]["drop_prob_on"]},
                 "pulse_delay": {"delay_ms": c["motion"]["pulse_start_delay_on_ms"]}}
        o = c["optics"]
        table.update(subsurface_scatter=o["materials"], subsurface_stress={"tau_px": o["stress_tail_px"], "beta": o["stress_beta"]},
                     hot_gloss={"gain": o["hot_gloss_gain"]}, speckle={"contrast": o["speckle_contrast"]},
                     occlusion={}, lens_residual={"dist_k": o["dist_k"]}, room_light={"level": o["room_light"]})
        return table.get(name, {})


def _cylinder_plate(job) -> Scene:
    """D4 교정 판: 평판 + 원기둥 (참 높이맵)."""
    step = 0.02
    xs = [f[0] for f in job["features"]]
    ys = [f[1] for f in job["features"]]
    x0, y0 = min(xs) - 15.0, min(ys) - 15.0
    nx, ny = int((max(xs) - x0 + 15.0) / step), int((max(ys) - y0 + 15.0) / step)
    X = x0 + np.arange(nx) * step
    Y = y0 + np.arange(ny) * step
    H = np.full((ny, nx), job["plate_top_mm"], dtype=np.float32)
    r = job["cyl_d_mm"] / 2
    for fx, fy in job["features"]:
        m = (X[None, :] - fx) ** 2 + (Y[:, None] - fy) ** 2 <= r * r
        H[m] = job["plate_top_mm"] + job["cyl_h_mm"]
    bed = Bed({"size_mm": [350.0, 350.0], "tilt_x_deg": 0.0, "tilt_y_deg": 0.0, "bowl_um": 0.0, "mesh_n": 3,
               "probe_sigma_um": 0.0, "mesh_enabled": False}, zero_error=False)
    return Scene(bed, hmap=H, origin=(x0, y0), step=step)
