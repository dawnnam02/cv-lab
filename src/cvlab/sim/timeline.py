# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""캠페인 시간표 (S4): 교정 → 세션 기준 → 층마다 출력 + LM-T14-3 → 식힌 재측정. 영상은 아직 없음 (S5 writer).

돌려주는 것은 명세 필드 이름의 행 (ref · cal · rep)과 줄 객체 (motion.ScanLine: 위치 로그 행 · 펄스 시각 ·
실제 노즐 위치)와 참값 조각이다. writer는 이 시간표를 따라 장면을 바꾸며 프레임을 렌더하고 파일을 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .calib import cal_plan, gauge_truth, make_gauges
from .clock import VirtualClock
from .motion import MacroSim, ZModel, choose_steps, line_plan
from .optics import geometry_truth, make_geometry
from .refs import RefIds, msa_design, ref_row
from .scene import Bed
from .seeds import SeedTree
from .shape import gauge_temperature


@dataclass
class Timeline:
    campaign_id: str
    session_id: str
    cal_id: str
    geometry: object
    bed: object
    gauges: object
    cal_rows: list
    cal_jobs: list
    session_refs: list = field(default_factory=list)     # (ref 행, ScanLine 또는 None)
    layers: list = field(default_factory=list)           # 층마다 dict
    post: dict | None = None
    msa: tuple | None = None
    truth: dict = field(default_factory=dict)
    t_print0_s: float = 0.0      # 세션 시작 (기준물 온도 시계 0) 가상 경과 초
    boot_ns: int = 0             # 호스트 단조 시계 = 가상 경과 + boot


def scan_id_of(sid: str, rep: int, layer_key: str, spass: int, q: int = 0) -> str:
    from .specdefs import scan_id
    return scan_id(sid, rep, layer_key, spass, q)


def build_timeline(cfg: dict, camp: dict, seed: int, spec_entry: dict, z_layers, bbox: dict,
                   zparams: dict | None = None, switches: dict | None = None, blind: bool = False) -> Timeline:
    """시편 하나 캠페인 시간표. z_layers: 출력한 층 Z (명령). zparams: shape가 쓴 Z축 참값 (같은 모델)."""
    tree = SeedTree(seed)
    sw = dict(pulse_delay=False)
    sw.update(switches or {})
    clock = VirtualClock(cfg["clock"]["start_iso"])
    geom = make_geometry(cfg["optics"], tree.child("geometry").rng(), lens_residual=sw.get("lens_residual", True))
    bed = Bed(cfg["bed"], tree.child("bed").rng(), zero_error=sw.get("bed_zero_error", True), mesh=sw.get("bed_mesh_z"))
    gauges = make_gauges(cfg["steps"], cfg["gauge_thermal"], tree.child("gauges").rng(), cfg["calib"]["room_temp_c"])
    mo = cfg["optics"]["materials"]["pla"]
    bias_um = mo["beta"] * mo["delta_um"]  # 재료 치우침 참값 (무게중심 기준, 모델 문서 §3.3)
    cal_rows, cal_jobs = cal_plan(cfg, camp["calibration_id"], clock, gauges, tree.child("calib").rng(), bias_um,
                                  geom.offset_g)
    tl = Timeline(camp["campaign_id"], camp["session_id"], camp["calibration_id"], geom, bed, gauges, cal_rows, cal_jobs)
    zp = dict(zparams or {"gain_ppm": 0.0, "nonrep_sigma_um": cfg["z_axis"]["nonrep_sigma_um"],
                          "frame_drift_um_per_h": cfg["z_axis"]["frame_drift_um_per_h"]})
    zm = ZModel(zp, tree.child("z_scan").rng(), bed)
    gcfg = cfg["gauge_thermal"]
    trng = tree.child("thermistor").rng()
    true_temp = {}

    def gauge_temp(t_s):
        T = gauge_temperature(gcfg, max(t_s, 0.0))
        true_temp["last"] = T
        return T + float(trng.normal(0.0, 0.2))  # 서미스터 [추정 0.2 °C]

    ms = MacroSim(cfg["motion"], cfg["steps"], clock, zm, cfg["optics"]["nozzle_sensor_offset_mm"], sw, gauge_temp)
    ids = RefIds()
    sid, rep = spec_entry["specimen_id"], int(spec_entry["repeat"])
    passes = int(camp["passes_per_layer"])
    xs, y0, L = line_plan(bbox, cfg["motion"], passes)
    st = cfg["steps"]
    cal = camp["calibration_id"]
    nb = int(cfg["camera"]["background_frames"])   # 스캔마다 레이저 끈 배경 프레임 (n_frames = 펄스 + nb)
    # 세션 기준 (출력 전). 기준물 온도는 세션 시작 (베드 가열)부터 셈
    ms.t_print0_s = clock.elapsed_s
    tl.t_print0_s, tl.boot_ns = ms.t_print0_s, ms.boot_ns
    beds, feelers = ms.preprint(xs, y0, L)
    for i, b in enumerate(beds):
        tl.session_refs.append((ref_row(ids.next("bed_bare"), "bed_bare", b.scan_start_ns, b.n_pulses + nb, cal,
                                        layer_idx=-1, scan_pass_idx=i, note=f"출력 전 베드 기준 줄 {i}"), b))
    for f in feelers:
        gid = st["ids"][f.gauge_idx]
        tl.session_refs.append((ref_row(ids.next("feeler"), "feeler", f.scan_start_ns, f.n_pulses + nb, cal,
                                        layer_idx=-1, gauge_id=gid, gauge_h=gauges.cal_height(gid),
                                        gauge_temp=f.gauge_temp_c, note=f"출력 전 필러게이지 {gid[3:]}"), f))
    rc = cfg["refs"]
    for kind, n in (("background", rc["bkg_frames"]), ("dark", rc["dark_frames"]), ("static_repeat", rc["static_frames"])):
        t0 = ms.host_ns()
        tl.session_refs.append((ref_row(ids.next(kind), kind, t0, n, cal if kind == "static_repeat" else None,
                                        layer_idx=-1, note=f"세션 시작 {kind}"), None))
        clock.advance(n * cfg["motion"]["trigger_period_s"] + 1.0)
    # 층마다
    nL = len(z_layers)
    mid = nL // 2
    temps = {}
    sc = cfg["specimens"][spec_entry["name"]] if spec_entry["name"] in cfg["specimens"] else {"layer_print_s": 20.0}
    for n, zt in enumerate(z_layers):
        r = ms.layer(n, float(zt), xs, y0, L, sc["layer_print_s"],
                     print_xy=((bbox["xmin"] + bbox["xmax"]) / 2, (bbox["ymin"] + bbox["ymax"]) / 2),
                     repeats=(rc["msa_repeats"] - 1) if n == mid else 0)
        key = f"L{n:03d}"
        r["scan_ids"] = [scan_id_of(sid, rep, key, i) for i in range(passes)]
        r["repeat_ids"] = [scan_id_of(sid, rep, key, 0, q) for q in range(1, len(r["repeats"]) + 1)]
        r["layer"], r["z_top"] = n, float(zt)
        r["step_refs"] = []
        for S in r["steps"]:
            gid = st["ids"][S.gauge_idx]
            r["step_refs"].append(ref_row(ids.next("step_gauge"), "step_gauge", S.scan_start_ns, S.n_pulses + nb, cal,
                                          scan_id=r["scan_ids"][0], layer_idx=n, gauge_id=gid,
                                          gauge_h=gauges.cal_height(gid), gauge_temp=S.gauge_temp_c,
                                          note=f"층 {n} 같은 Z {'낮은 단 h2' if S is r['steps'][0] else '높은 단 h1'}"))
        if r["steps"]:
            temps[key] = round(true_temp["last"], 3)
        tl.layers.append(r)
    # 식힌 재측정
    last = nL - 1
    p = ms.cool_rescan(last, float(z_layers[-1]), xs, y0, L, cfg["thermal"]["post_wait_s"])
    p["scan_ids"] = [scan_id_of(sid, rep, "post", i) for i in range(passes)]
    p["layer"], p["z_top"] = last, float(z_layers[-1])
    p["step_refs"] = []
    for S in p["steps"]:
        gid = st["ids"][S.gauge_idx]
        p["step_refs"].append(ref_row(ids.next("step_gauge"), "step_gauge", S.scan_start_ns, S.n_pulses + nb, cal,
                                      scan_id=p["scan_ids"][0], layer_idx=last, gauge_id=gid,
                                      gauge_h=gauges.cal_height(gid), gauge_temp=S.gauge_temp_c,
                                      note="식힌 재측정 같은 Z 두 단"))
    if p["steps"]:
        temps["post"] = round(true_temp["last"], 3)
    tl.post = p
    # 같은 층 반복 (MSA-01): 가운데 층 첫 줄
    mid_r = tl.layers[mid]
    tl.msa = msa_design("MSA-01", sid, camp["session_id"], [mid_r["scan_ids"][0]] + mid_r["repeat_ids"],
                        rc["msa_repeats"], tree, f"T-{sid}", rc["msa_operator"], blind=blind)
    used = [st["ids"][S.gauge_idx] for r in tl.layers + [p] for S in r["steps"]]
    tl.truth = dict(geometry_truth(geom), **gauge_truth(gauges, used),
                    gauge_temp_params={"cte_um_per_m_c": gcfg["cte_um_per_m_c"], "temp_c": temps},
                    bed=bed.truth(), z_scan_moves_um=zm.moves, material_bias_um=round(bias_um, 4))
    return tl
