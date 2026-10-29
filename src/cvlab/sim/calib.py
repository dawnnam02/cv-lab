# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""교정 원자료 (세부청사진 §6.6, SM7). 명세 3절 cal_manifest 필드 이름 그대로의 행 + 렌더 작업 목록 + 참값.

- 기준물: 블록은 ID 숫자 (밀착 블록 공칭)마다 참 높이 = 공칭 + 균일 ± block_dev, 밀착 면마다 0–contact 더함.
  필러 잎은 공칭 + 균일 ± feeler_dev. 마이크로미터 행 = 교정 온도의 참 높이 + N(0, u) (u = 표준불확도).
- D1 ChArUco 자세 ≥ 20 (전체 프레임), D2 평판 높이 ≥ 8 (켬 · 끔 짝, 같은 노출), D3 이동 ≥ 10,
  D4 노즐 접촉 + 원기둥 판 스캔, D5 필러 4 (영상 + 두께) · 블록 단 8 (마이크로미터 + 윗면 스캔) · 재료 조각.
- 영상 렌더는 작업 목록 (job)으로만 남김. 실제 그리기 · 파일 쓰기는 writer (S5)가 이 목록으로 함.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np

CAL_FIELDS = ["cal_id", "kind", "created", "record_type", "target_type", "target_rows", "target_cols",
              "target_square_mm", "target_marker_mm", "target_dict", "target_flatness_um", "pose_idx", "image_file",
              "laser_on", "exposure_us", "cmd_z_mm", "cmd_move_mm", "feature_id", "feature_x_mm", "feature_y_mm",
              "nozzle_touch_z_mm", "gauge_nominal_mm", "gauge_measured_mm", "gauge_u_um", "gauge_block_id",
              "gauge_block_height_mm", "gauge_block_u_um", "material_offset_um", "material_offset_u_um", "material",
              "color", "temp_c", "result_file", "valid_from", "valid_until", "invalidated_by"]
RESULT_FILES = {"D1": "camera_intrinsics.yaml", "D2": "laser_plane.yaml", "D3": "scan_axis.yaml",
                "D4": "nozzle_offset.yaml", "D5": "verification.yaml"}


def block_parts(gid: str) -> list[float]:
    """GB-02+01.8+01.5 → [2.0, 1.8, 1.5]. GB-00 → []."""
    if not re.fullmatch(r"GB-\d{2}(\.\d{1,3})?(\+\d{2}(\.\d{1,3})?)*", gid):
        raise ValueError(f"블록 ID 형식이 아님: {gid}")
    parts = [float(p) for p in gid[3:].split("+")]
    return [] if parts == [0.0] else parts


@dataclass
class Gauges:
    """13단 참 높이 (20 °C) · 교정값. 키는 단 ID."""
    true20: dict = field(default_factory=dict)
    measured: dict = field(default_factory=dict)
    u_um: dict = field(default_factory=dict)
    cte: float = 11.5

    def true_at(self, gid: str, temp_c: float) -> float:
        return self.true20[gid] * (1.0 + self.cte * 1e-6 * (temp_c - 20.0))

    def cal_height(self, gid: str) -> float:
        return 0.0 if gid == "GB-00" else self.measured[gid]


def make_gauges(steps: dict, gcfg: dict, rng, cal_temp_c: float) -> Gauges:
    g = Gauges(cte=gcfg["cte_um_per_m_c"])
    for gid, nom in zip(steps["ids"], steps["height_mm"]):
        if gid == "GB-00":
            g.true20[gid] = 0.0
            continue
        if gid.startswith("FG-"):
            t = nom + rng.uniform(-steps["feeler_dev_mm"], steps["feeler_dev_mm"])
            u = steps["feeler_u_um"]
        else:
            parts = block_parts(gid)
            t = sum(p + rng.uniform(-1, 1) * steps["block_dev_um"] / 1000.0 for p in parts)
            t += sum(rng.uniform(0, steps["contact_um"] / 1000.0) for _ in range(len(parts) - 1))
            u = steps["block_u_um"]
        g.true20[gid] = float(t)
        g.u_um[gid] = float(u)
        g.measured[gid] = round(float(g.true_at(gid, cal_temp_c) + rng.normal(0.0, u / 1000.0)), 4)
    return g


def gauge_truth(g: Gauges, used_block_ids) -> dict:
    thick = {gid[3:]: round(g.true20[gid], 6) for gid in g.true20 if gid.startswith("FG-")}
    blocks = {gid: round(g.true20[gid], 6) for gid in sorted(set(used_block_ids)) if gid.startswith("GB-") and gid != "GB-00"}
    return {"gauge_thickness_mm": thick, "gauge_block_heights_mm": blocks or None}


def _row(**kw) -> dict:
    r = {k: None for k in CAL_FIELDS}
    r.update(kw)
    return r


def cal_plan(cfg: dict, cal_id: str, clock, gauges: Gauges, rng, material_bias_um: float,
             nozzle_offset_true, plate_top_mm: float = 5.0) -> tuple[list, list]:
    """(cal_manifest 행 목록, 렌더 작업 목록). 행 순서 = 만든 시각 순서."""
    c, o, cam = cfg["calib"], cfg["optics"], cfg["camera"]
    T = c["room_temp_c"]
    rows, jobs = [], []
    base = dict(cal_id=cal_id, temp_c=T, invalidated_by="none")
    valid_from = None

    def stamp(kind, **kw):
        r = _row(**base, kind=kind, created=clock.iso(), result_file=f"config/calibration/{cal_id}/{RESULT_FILES[kind]}",
                 **kw)
        rows.append(r)
        return r

    cz = c["charuco"]
    for i in range(c["d1_poses"]):  # D1: 기울기 · 위치 다양
        ax, ay = np.radians(rng.uniform(-25, 25, 2))
        t = [float(rng.uniform(-3, 3)), float(rng.uniform(-2, 2)), float(rng.uniform(-3.0, 3.0))]
        stamp("D1", record_type="image", target_type="charuco", target_rows=cz["rows"], target_cols=cz["cols"],
              target_square_mm=cz["square_mm"], target_marker_mm=cz["marker_mm"], target_dict=cz["dict"],
              target_flatness_um=cz["flatness_um"], pose_idx=i, image_file=f"d1/view_{i:03d}.png", laser_on=False,
              exposure_us=cam["exposure_us"])
        jobs.append({"kind": "D1", "image_file": f"d1/view_{i:03d}.png", "tilt_rad": [float(ax), float(ay)], "t_s": t})
        clock.advance(20.0)
    hop = cfg["motion"]["z_hop_mm"]
    zs = np.linspace(plate_top_mm + hop - 3.5, plate_top_mm + hop + 3.5, c["d2_heights"])
    for i, z in enumerate(zs):  # D2: 평판 높이별 끔 · 켬 짝 (같은 노출)
        for on in (False, True):
            f = f"d2/pose_{i:02d}_{'on' if on else 'off'}.png"
            stamp("D2", record_type="image", target_type="flat_plate", target_flatness_um=c["flat_plate_flatness_um"],
                  pose_idx=i, image_file=f, laser_on=on, exposure_us=cam["exposure_us"], cmd_z_mm=round(float(z), 4))
            jobs.append({"kind": "D2", "image_file": f, "cmd_z_mm": float(z), "plate_top_mm": plate_top_mm, "laser_on": on})
            clock.advance(5.0)
    for i in range(c["d3_moves"]):  # D3: 스캔 축으로 명령 이동
        mv = round(0.5 * i, 4)
        f = f"d3/move_{i:02d}.png"
        stamp("D3", record_type="image", target_type="coord_plate", pose_idx=i, image_file=f, laser_on=False,
              exposure_us=cam["exposure_us"], cmd_move_mm=mv)
        jobs.append({"kind": "D3", "image_file": f, "cmd_move_mm": mv})
        clock.advance(5.0)
    nr, nc = c["d4_features"]
    k = 0
    for a in range(nr):  # D4: 원기둥마다 노즐 접촉 행
        for b in range(nc):
            fx, fy = 100.0 + b * c["d4_pitch_mm"], 100.0 + a * c["d4_pitch_mm"]
            touch = plate_top_mm + c["d4_cyl_h_mm"] + rng.normal(0.0, c["touch_sigma_um"] / 1000.0)
            stamp("D4", record_type="nozzle_touch", target_type="none", pose_idx=k, laser_on=False,
                  feature_id=f"P{a:02d}_{b:02d}", feature_x_mm=fx, feature_y_mm=fy,
                  nozzle_touch_z_mm=round(float(touch), 4))
            k += 1
            clock.advance(10.0)
    plate_len = nr * c["d4_pitch_mm"] + 4.0
    n_plate = int(round(plate_len / (cfg["motion"]["scan_speed_mm_s"] * cfg["motion"]["trigger_period_s"])))
    jobs.append({"kind": "D4", "scan": "plate_scan", "frames": n_plate, "pose_idx0": k,
                 "features": [[100.0 + b * c["d4_pitch_mm"], 100.0 + a * c["d4_pitch_mm"]] for a in range(nr) for b in range(nc)],
                 "cyl_h_mm": c["d4_cyl_h_mm"], "cyl_d_mm": c["d4_cyl_d_mm"], "plate_top_mm": plate_top_mm})
    n_g = int(round(c["gauge_scan_len_mm"] / (cfg["motion"]["scan_speed_mm_s"] * cfg["motion"]["trigger_period_s"])))
    pose = 0
    for gid, nom in zip(cfg["steps"]["ids"], cfg["steps"]["height_mm"]):  # D5 필러: 영상 + 두께 한 행
        if not gid.startswith("FG-"):
            continue
        sub = f"gauge_{gid[3:].replace('.', 'p')}"
        for fi in range(n_g):
            stamp("D5", record_type="image", target_type="filler_gauge", pose_idx=pose, laser_on=True,
                  image_file=f"d5/{sub}/g{fi:04d}.png", exposure_us=cam["exposure_us"], gauge_nominal_mm=nom,
                  gauge_measured_mm=gauges.measured[gid], gauge_u_um=gauges.u_um[gid], gauge_block_id=gid)
            pose += 1
        jobs.append({"kind": "D5", "scan": sub, "gauge_id": gid, "frames": n_g})
        clock.advance(30.0)
    for gid in cfg["steps"]["ids"]:  # D5 블록 단: 마이크로미터 행 + 윗면 스캔 영상
        if not gid.startswith("GB-") or gid == "GB-00":
            continue
        stamp("D5", record_type="micrometer", target_type="step_gauge", pose_idx=pose, laser_on=False,
              gauge_block_id=gid, gauge_block_height_mm=gauges.measured[gid], gauge_block_u_um=gauges.u_um[gid])
        pose += 1
        sub = "step_gauge"
        tag = gid[3:].replace("+", "_").replace(".", "p").lower()
        for fi in range(n_g):
            stamp("D5", record_type="image", target_type="step_gauge", pose_idx=pose, laser_on=True,
                  image_file=f"d5/{sub}/gb_{tag}_{fi:04d}.png", exposure_us=cam["exposure_us"], gauge_block_id=gid,
                  gauge_block_height_mm=gauges.measured[gid], gauge_block_u_um=gauges.u_um[gid])
            pose += 1
        jobs.append({"kind": "D5", "scan": sub, "gauge_id": gid, "frames": n_g})
        clock.advance(30.0)
    mu = c["material_u_um"]  # 재료 조각: 마이크로미터 행 + 스캔 (치우침 값은 같은 조각의 모든 행에 같음)
    moff = round(float(-material_bias_um + rng.normal(0.0, mu)), 2)
    stamp("D5", record_type="micrometer", target_type="material_sample", pose_idx=pose, laser_on=False,
          material_offset_um=moff, material_offset_u_um=mu, material=c["material"], color=c["color"])
    pose += 1
    for fi in range(n_g):
        stamp("D5", record_type="image", target_type="material_sample", pose_idx=pose, laser_on=True,
              image_file=f"d5/material/m{fi:04d}.png", exposure_us=cam["exposure_us"], material=c["material"],
              color=c["color"], material_offset_um=moff, material_offset_u_um=mu)
        pose += 1
    jobs.append({"kind": "D5", "scan": "material", "frames": n_g})
    clock.advance(60.0)
    valid_from = clock.iso()
    for r in rows:
        r["valid_from"] = valid_from
    return rows, jobs
