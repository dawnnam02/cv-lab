# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""움직임 (LM-T14-3) · 교정 (D1–D5) · 기준 · 반복 (S4)."""
from __future__ import annotations

import csv
import re
from collections import Counter

import numpy as np
import pytest

from cvlab.sim.calib import block_parts
from cvlab.sim.motion import check_same_z, choose_steps
from cvlab.sim.refs import two_step_rule
from cvlab.sim.shape import load_specimen
from cvlab.sim.simconfig import ROOT, SIM_CONFIG_DIR, load_campaign, load_default
from cvlab.sim.timeline import build_timeline

CFG = load_default()
LAYER_TABLE = ROOT / "docs" / "프린터-펌웨어-선정_자료"


@pytest.fixture(scope="module")
def tl():
    camp = load_campaign(SIM_CONFIG_DIR / "campaign_voron24.yaml")
    z = [round(0.2 * (k + 1), 4) for k in range(16)]                    # voron24 층 Z (T14 층표와 같음)
    bbox = dict(xmin=162.45, xmax=187.55, ymin=162.45, ymax=187.55)     # 25.1 mm 상자 [세부청사진 §6.11]
    return build_timeline(CFG, camp, 11, camp["specimens"][0], z, bbox)


@pytest.mark.parametrize("name", ["voron24", "caliper"])
def test_step_choice_matches_t14_layer_table(name):
    st = CFG["steps"]
    rows = list(csv.DictReader(open(LAYER_TABLE / f"층표_{name}.csv", encoding="utf-8")))
    bad = []
    for r in rows:
        i1, i2 = choose_steps(float(r["z_n_mm"]), st)
        if (st["ids"][i1], st["ids"][i2]) != (r["h1_id"], r["h2_id"]):
            bad.append(r["layer"])
    assert bad == [] and len(rows) in (16, 64)


def test_same_z_and_event_order(tl):
    for r in tl.layers + [tl.post]:
        assert check_same_z(r["lines"] + r["steps"]) <= 0.001
        assert len(r["steps"]) == 2
    first = [e["event"] for e in tl.layers[3]["lines"][0].rows if e["event"] != "none"]
    assert first == ["layer_change", "m400_done", "scan_start", "scan_end", "resume"]
    other = [e["event"] for e in tl.layers[3]["lines"][1].rows if e["event"] != "none"]
    assert other == ["m400_done", "scan_start", "scan_end"]
    L = tl.layers[3]
    t = [L["lines"][0].scan_start_ns, L["lines"][1].scan_start_ns, L["steps"][0].scan_start_ns, L["steps"][1].scan_start_ns]
    assert t == sorted(t)                                   # 시편 줄 → 낮은 단 → 높은 단
    h = [CFG["steps"]["height_mm"][S.gauge_idx] for S in L["steps"]]
    assert h[0] < h[1]


def test_post_rules(tl):
    p = tl.post
    ev0 = [e["event"] for e in p["lines"][0].rows if e["event"] != "none"]
    assert ev0 == ["cool_start", "cool_end", "m400_done", "scan_start", "scan_end"]
    for L in p["lines"][1:] + p["steps"]:
        assert not {"cool_start", "cool_end", "resume", "motor_off"} & {e["event"] for e in L.rows}
    assert all(e["pass_idx"] == 0 for L in p["lines"] for e in L.rows)
    assert p["scan_ids"] == ["S01_r01", "S01_r01_p01"] and p["layer"] == len(tl.layers) - 1
    t_cs = [e["t_ns"] for e in p["lines"][0].rows if e["event"] in ("cool_start", "cool_end")]
    assert t_cs[1] - t_cs[0] >= CFG["thermal"]["post_wait_s"] * 1e9 and t_cs[1] <= p["lines"][0].scan_start_ns


def test_scan_segment_rows(tl):
    v = CFG["motion"]["scan_speed_mm_s"]
    for L in tl.layers[5]["lines"] + tl.layers[5]["steps"]:
        seg = [r for r in L.rows if L.scan_start_ns <= r["t_ns"] <= L.scan_end_ns]
        for src in ("cmd", "plan"):
            ys = [r["y_mm"] for r in sorted(seg, key=lambda r: r["t_ns"]) if r["source"] == src]
            assert np.all(np.diff(ys) >= 0)
        xs = [r["x_mm"] for r in seg]
        assert max(xs) - min(xs) <= 0.01
        assert abs(np.mean([r["feed_mm_s"] for r in seg]) - v) <= 0.05 * v
        assert L.n_pulses == sum(1 for r in L.rows if r["source"] == "plan")
        assert all(r["mesh_dz_mm"] is not None and abs(r["mesh_dz_mm"]) <= 2.0 for r in L.rows)
        ts = [r["t_ns"] for r in L.rows]
        assert ts == sorted(ts)


def test_actual_z_close_to_command(tl):
    for r in tl.layers:
        for L in r["lines"]:
            d = L.z_nozzle_act - L.z_cmd
            assert np.all(np.abs(d) < 0.1)                 # 메시 + Z축 오차 (수십 µm)
            assert np.ptp(d) < 0.02                        # 한 줄 안에서는 메시 기울기 몫만


def test_session_refs(tl):
    kinds = Counter(r["kind"] for r, _ in tl.session_refs)
    assert kinds == {"bed_bare": 2, "feeler": 4, "background": 1, "dark": 1, "static_repeat": 1}
    beds = [(r, L) for r, L in tl.session_refs if r["kind"] == "bed_bare"]
    assert [r["scan_pass_idx"] for r, _ in beds] == [0, 1]
    assert [L.x_nozzle for _, L in beds] == [L.x_nozzle for L in tl.layers[0]["lines"]]
    for r, L in tl.session_refs:
        assert r["layer_idx"] == -1 and re.fullmatch(r"REF-[A-Z]{3}-\d{3,4}", r["ref_id"])
        if L is not None:
            assert all(e["layer_idx"] == -1 for e in L.rows)
    fl = [r for r, _ in tl.session_refs if r["kind"] == "feeler"]
    assert sorted(r["gauge_block_id"] for r in fl) == ["FG-0.20", "FG-0.30", "FG-0.40", "FG-0.50"]
    t_first_layer = tl.layers[0]["t_layer_end_ns"]
    assert all(r["t_start_ns"] < t_first_layer for r, _ in tl.session_refs if r["kind"] in ("bed_bare", "feeler"))


def test_step_refs_two_step_rules(tl):
    ids = []
    conflicts = []
    for r in tl.layers + [tl.post]:
        rows = r["step_refs"]
        assert len(rows) == 2 and rows[0]["gauge_block_id"] != rows[1]["gauge_block_id"]
        assert all(x["scan_id"] == r["scan_ids"][0] and x["layer_idx"] == r["layer"] for x in rows)
        h2, h1 = rows[0]["gauge_height_mm"], rows[1]["gauge_height_mm"]
        u = [2.0 if x["gauge_block_id"].startswith("GB") and x["gauge_block_id"] != "GB-00" else 1.0 for x in rows]
        chk = two_step_rule(h1, h2, r["z_top"], *u)
        nom_h1 = CFG["steps"]["height_mm"][CFG["steps"]["ids"].index(rows[1]["gauge_block_id"])]
        if not chk["rule_ok"]:
            # 알려진 충돌 (대조표 '명세에 반영할 점' ①): 공칭 h1 = 층 Z인 층에서 교정값이 공칭보다 크면 h1 ≤ 층 Z가 깨짐
            assert abs(nom_h1 - r["z_top"]) < 1e-9 and 0 < h1 - r["z_top"] <= 0.02, (r["layer"], chk)
            conflicts.append(r["layer"])
        assert chk["ratio_ok"], (r["layer"], chk)
        assert all(x["gauge_temp_c"] is not None for x in rows)
        ids += [x["ref_id"] for x in rows]
    assert ids == [f"REF-STG-{i:03d}" for i in range(1, len(ids) + 1)]
    temps = tl.truth["gauge_temp_params"]["temp_c"]
    assert set(temps) == {f"L{n:03d}" for n in range(len(tl.layers))} | {"post"}
    assert all(-10 <= t <= 130 for t in temps.values())


def test_msa_repeats(tl):
    mid = len(tl.layers) // 2
    reps = tl.layers[mid]["repeats"]
    assert len(reps) == CFG["refs"]["msa_repeats"] - 1
    assert [L.rows[0]["pass_idx"] for L in reps] == list(range(1, len(reps) + 1))
    design, executed = tl.msa
    assert len(design) == 5 and len({d["noise_seed"] for d in design}) == 5
    assert sorted(d["run_order"] for d in design) == [1, 2, 3, 4, 5]
    assert all(d["scan_id"] is None for d in design) and all(e["scan_id"] == f"S01_r01_L{mid:03d}" for e in executed)
    assert all(d["truth_id"] == "T-S01" for d in design)


def test_calibration_rows(tl):
    rows = tl.cal_rows
    k = Counter(r["kind"] for r in rows)
    assert k["D1"] >= 20 and k["D3"] >= 10
    d2 = [r for r in rows if r["kind"] == "D2"]
    assert len({r["pose_idx"] for r in d2}) >= 8 and len(d2) == 2 * len({r["pose_idx"] for r in d2})
    for p in {r["pose_idx"] for r in d2}:
        pair = [r for r in d2 if r["pose_idx"] == p]
        assert {r["laser_on"] for r in pair} == {True, False} and len({r["exposure_us"] for r in pair}) == 1
    zs = [r["cmd_z_mm"] for r in d2]
    assert max(zs) - min(zs) <= 8.0
    keys = [(r["kind"], r["pose_idx"], r["laser_on"]) for r in rows]
    assert len(keys) == len(set(keys))
    for r in rows:
        if r["record_type"] == "image":
            assert re.fullmatch(r"d[1-5]/([a-z0-9_]+/)?[a-z0-9_]+\.png", r["image_file"])
            assert r["image_file"][1] == r["kind"][1]
        else:
            assert r["image_file"] is None and r["laser_on"] is False
    touch = [r for r in rows if r["record_type"] == "nozzle_touch"]
    assert len(touch) == 9 and all(re.fullmatch(r"P\d{2}_\d{2}", r["feature_id"]) for r in touch)
    mic = [r for r in rows if r["record_type"] == "micrometer" and r["target_type"] == "step_gauge"]
    assert len(mic) == 8
    fg = {r["gauge_block_id"] for r in rows if r["target_type"] == "filler_gauge"}
    assert fg == {"FG-0.20", "FG-0.30", "FG-0.40", "FG-0.50"}
    mat = [r for r in rows if r["target_type"] == "material_sample"]
    assert mat and all(r["material"] == "PLA" and r["color"] == "gray" and abs(r["material_offset_um"]) <= 100 for r in mat)
    assert len({r["valid_from"] for r in rows}) == 1 and all(r["valid_from"] >= r["created"] for r in rows)


def test_gauge_truth_tolerances(tl):
    g, t = tl.gauges, tl.truth
    assert set(t["gauge_thickness_mm"]) == {"0.20", "0.30", "0.40", "0.50"}
    assert all(abs(v - float(k)) <= 0.02 for k, v in t["gauge_thickness_mm"].items())
    for gid, v in t["gauge_block_heights_mm"].items():
        assert abs(v - sum(block_parts(gid))) <= 0.02
    for gid, m in g.measured.items():
        assert abs(m - g.true20[gid]) <= 5 * g.u_um[gid] / 1000.0 + 0.0005
    assert block_parts("GB-02+01.8+01.5") == [2.0, 1.8, 1.5] and block_parts("GB-00") == []
    with pytest.raises(ValueError):
        block_parts("GB-2")


def test_pulse_delay_switch_moves_actual_not_plan():
    camp = load_campaign(SIM_CONFIG_DIR / "campaign_small.yaml")
    bbox = dict(xmin=165.0, xmax=185.0, ymin=165.0, ymax=185.0)
    z = [0.2, 0.4]
    a = build_timeline(CFG, camp, 3, camp["specimens"][0], z, bbox)
    b = build_timeline(CFG, camp, 3, camp["specimens"][0], z, bbox, switches={"pulse_delay": True})
    La, Lb = a.layers[0]["lines"][0], b.layers[0]["lines"][0]
    v = CFG["motion"]["scan_speed_mm_s"]
    dy = Lb.y_nozzle_act - La.y_nozzle_act
    assert np.allclose(dy, v * CFG["motion"]["pulse_start_delay_on_ms"] * 1e-3, atol=1e-9)
    pa = [r["y_mm"] for r in La.rows if r["source"] == "plan"]
    pb = [r["y_mm"] for r in Lb.rows if r["source"] == "plan"]
    assert pa == pb
    assert a.layers[0]["scan_ids"] == ["S01_r01_L000"] and a.post["scan_ids"] == ["S01_r01"]
    c = build_timeline(CFG, camp, 3, camp["specimens"][0], z, bbox,
                       switches={"lens_residual": False, "bed_zero_error": False, "bed_mesh_z": False})
    assert c.truth["cam_dist"][5:] == [0.0, 0.0, 0.0] and a.truth["cam_dist"][5:] != [0.0, 0.0, 0.0]
    assert float(c.bed.surface(10.0, 300.0)) == 0.0 and all(r["mesh_dz_mm"] is None for r in c.layers[0]["lines"][0].rows)


def test_timeline_frame_renders_gauge_line(tl):
    """시간표 · 장면 · 광학 · 카메라를 잇는 한 프레임: 층 8 높은 단 스캔 첫 펄스에서 블록 윗면 선이 ROI 안에 보임."""
    from cvlab.sim.camera import Sensor
    from cvlab.sim.optics import LineRenderer
    from cvlab.sim.scene import Block, Scene
    from cvlab.sim.seeds import SeedTree
    r = tl.layers[8]
    S = r["steps"][1]
    st = CFG["steps"]
    gid = st["ids"][S.gauge_idx]
    x = st["laser_x_mm"][S.gauge_idx]
    blk = Block(gid, x - 4.5, x + 4.5, st["y0_mm"] - 5, st["y0_mm"] + 25, tl.gauges.true_at(gid, 25.0))
    scene = Scene(tl.bed, blocks=[blk])
    O_g = np.array([S.x_nozzle, S.y_nozzle_act[0], S.z_nozzle_act[0]]) + tl.geometry.offset_g
    img, info = LineRenderer(tl.geometry, CFG["optics"]).render_line(scene, O_g, with_info=True)
    sensor = Sensor.create(CFG["camera"], tl.geometry.width, tl.geometry.height, SeedTree(1).child("fpn").rng())
    frame, sat = sensor.expose(img, tl.geometry.roi_y0, SeedTree(1).child("f").rng())
    assert info["valid_cols"] > 300 and frame.max() > 60 and sat < 0.05 * frame.size   # 강철 확산 0.5 → 꼭대기 약 90 DN
