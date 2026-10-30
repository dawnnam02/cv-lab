# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""광학 · 카메라 (S3): 해석해 시편 (MF-SIM-06), 단면 명목값 (§6.3), 스펙클, 가림, 잡음 · 시각."""
from __future__ import annotations

import math

import numpy as np
import pytest

from cvlab.sim.camera import Sensor, frame_times
from cvlab.sim.optics import (LineRenderer, PlaneSurface, Speckle, checker_texture, geometry_truth, make_geometry,
                              render_plane)
from cvlab.sim.scene import Bed, Block, Scene
from cvlab.sim.seeds import SeedTree
from cvlab.sim.simconfig import load_default

CFG = load_default()
O = CFG["optics"]
G = make_geometry(O)
UM_PER_PX = 1000.0 / abs(G.dv_dz())
COLS = slice(200, 1080)


def centroid(img, lo=15, hi=25):
    """시험용 기준 무게중심 (문턱 없이 꼭대기 −lo … +hi 행 창, 주변광 뺀 값). 처리 코드가 아님."""
    img = img - O["ambient"]
    pk = img.argmax(0)
    rows = np.arange(img.shape[0])[:, None]
    w = np.where((rows >= pk - lo) & (rows <= pk + hi), img, 0.0)
    s = w.sum(0)
    return np.where(s > 0, (w * rows).sum(0) / np.where(s > 0, s, 1.0), np.nan) + G.roi_y0


def true_v_cols(r, z=0.0):
    xs = np.linspace(-11.5, 11.5, 23001)
    uu, vv = r.true_v(xs, z)
    return np.interp(np.arange(G.width), uu, vv)


def test_geometry_nominal_numbers():
    assert G.K[0, 0] == pytest.approx(3173.4, abs=0.5)           # f (1 + M) ÷ 3 µm
    assert UM_PER_PX == pytest.approx(31.6, abs=0.1)              # 명세 9절 · T7a의 31.6 µm/px
    lp = G.laser_plane_c()
    assert lp[:3] == pytest.approx([0.0, -math.cos(math.pi / 6), 0.5], abs=1e-9)
    t = geometry_truth(make_geometry(O, SeedTree(3).child("g").rng()))
    assert abs(np.linalg.norm(t["laser_plane"][:3]) - 1) < 1e-6 and abs(np.linalg.norm(t["scan_axis"]) - 1) < 1e-6
    assert abs(np.linalg.det(np.array(t["t_g_m"])[:3, :3]) - 1) < 1e-9 and len(t["cam_dist"]) == 8


def test_projection_roundtrip_with_distortion():
    g = make_geometry(O, SeedTree(4).child("g").rng())
    u = np.array([5.0, 640.0, 1270.0, 300.0])
    v = np.array([280.0, 400.0, 520.0, 795.0])
    d = g.ray_s(u, v)
    P = g.C_s[None, :] + 40.0 * d
    u2, v2, _ = g.project_s(P)
    assert np.max(np.abs(u2 - u)) < 1e-6 and np.max(np.abs(v2 - v)) < 1e-6


def test_flat_plane_centroid_matches_projection():
    """해석해 (MF-SIM-06): 꼬리 · 스펙클 없는 평면 → 렌더 중심 = 참 투영 (0.02 px 안)."""
    r = LineRenderer(G, O, dict(subsurface_scatter=False, speckle=False))
    img, info = r.render_line(PlaneSurface(heights=(0.0,)), np.zeros(3), with_info=True)
    d = (centroid(img) - true_v_cols(r))[COLS]
    assert abs(np.nanmean(d)) < 0.02 and np.nanstd(d) < 0.02
    assert img.max() == pytest.approx(1.0 + O["ambient"], rel=1e-6)
    assert info["valid_cols"] > 1200


def test_step_0p2_recovered():
    """해석해 단차 0.200 mm: 두 면의 렌더 중심 차를 높이로 바꾸면 0.200 ± 0.002 mm."""
    r = LineRenderer(G, O, dict(subsurface_scatter=False, speckle=False))
    img, _ = r.render_line(PlaneSurface(edges_x=(0.0,), heights=(0.0, 0.2)), np.zeros(3))
    c = centroid(img)
    xs = np.linspace(-11.5, 11.5, 23001)
    for z, cols in ((0.0, slice(200, 560)), (0.2, slice(720, 1080))):
        uu, vv = r.true_v(xs, z)
        d = (c - np.interp(np.arange(G.width), uu, vv))[cols]
        assert np.nanmax(np.abs(d)) < 0.05


def test_subsurface_bias_nominal_and_stress():
    out = {}
    for name, sw in (("nom", dict(speckle=False)), ("stress", dict(speckle=False, subsurface_stress=True))):
        r = LineRenderer(G, O, sw)
        img, _ = r.render_line(PlaneSurface(heights=(0.0,)), np.zeros(3))
        out[name] = float(np.nanmean((centroid(img) - true_v_cols(r))[COLS])) * UM_PER_PX
    assert 4.4 <= out["nom"] <= 13.9            # T2 MF-MAT-01 (출처 1 표 2)
    assert 41.0 <= out["stress"] <= 51.0        # T7a 스트레스 (τ 2 px)


def test_speckle_point_and_cell_sigma():
    """MF-OPT-03: 한 점 1σ 7.2 µm, 판정 칸 (프레임 10 × 열 13) 평균 2.9 µm, 각각 ±50 % 안."""
    r = LineRenderer(G, O, dict(subsurface_scatter=False))
    base, _ = r.render_line(PlaneSurface(heights=(0.0,)), np.zeros(3))
    sp = Speckle(O["speckle_contrast"], O["speckle_corr_u_px"], O["speckle_corr_v_px"], O["speckle_rho_frame"],
                 SeedTree(9).child("sp").rng(), base.shape)
    lit = np.flatnonzero((base - O["ambient"]).any(axis=1))
    band = (int(lit[0]), int(lit[-1]) + 1)          # 렌더와 같은 선 둘레 행만 (T3-2 2차)
    cs = np.array([centroid((base - O["ambient"]) * sp.next(band) + O["ambient"]) for _ in range(40)])[:, COLS]
    d = (cs - cs.mean(0)) * UM_PER_PX
    cells = [np.nanmean(d[f:f + 10, c:c + 13]) for f in range(0, 40, 10) for c in range(0, 870, 13)]
    assert 3.6 <= np.nanstd(d) <= 10.8
    assert 1.45 <= np.nanstd(cells) <= 4.35
    zb = sp.z[band[0]:band[1]]
    assert 0.9 < float(zb.std()) < 1.1 and abs(float(zb.mean())) < 0.1   # 고정 정규화로도 단위 분산


def test_camera_side_occlusion():
    bed = Bed(dict(CFG["bed"], mesh_enabled=False))
    O_g = np.array([175.0, 175.0, 0.0])
    open_scene = Scene(bed)
    wall = Scene(bed, blocks=[Block("W", 160.0, 190.0, 173.5, 174.5, 3.0)])
    r = LineRenderer(G, O, dict(speckle=False))
    a, ia = r.render_line(open_scene, O_g - [0, 0, float(bed.surface(175.0, 175.0))], with_info=True)
    b, ib = r.render_line(wall, O_g - [0, 0, float(bed.surface(175.0, 175.0))], with_info=True)
    assert ia["valid_cols"] > 1200 and ib["valid_cols"] < 50
    assert (b - O["ambient"]).max() < 0.05 * (a - O["ambient"]).max()


def test_plane_target_render():
    import dataclasses
    K = G.K.copy()
    K[:2] /= 4.0
    g = dataclasses.replace(G, K=K, width=320, height=200)   # 시험 시간을 줄인 1/4 크기 카메라
    img = render_plane(g, np.eye(3), np.array([0.0, 0.0, 0.0]), checker_texture(1.5, 6, 9, 1.1), supersample=1)
    assert img.shape == (g.height, g.width)
    assert img.min() < 0.15 and img.max() > 0.45


def test_sensor_noise_levels_and_bits():
    rng = SeedTree(1).child("fpn").rng()
    s = Sensor.create(CFG["camera"], G.width, G.height, rng)
    irr = np.full((G.roi_h, G.width), 0.5)
    img, sat = s.expose(irr, G.roi_y0, SeedTree(1).child("n").rng())
    assert img.dtype == np.uint8 and sat == 0
    assert img.mean() == pytest.approx(0.5 * 0.7 * 255, abs=2.0)
    assert 1.2 < img.std() < 3.0                       # 산탄 + PRNU (약 1.9 DN)
    dark, _ = s.expose(np.zeros_like(irr), G.roi_y0, SeedTree(1).child("n2").rng(), shutter_open=False)
    assert dark.mean() < 1.0
    _, sat2 = s.expose(np.full_like(irr, 2.0), G.roi_y0, SeedTree(1).child("n3").rng())
    assert sat2 > 0.99 * irr.size
    img2, _ = s.expose(irr, G.roi_y0, SeedTree(1).child("n").rng())
    assert np.array_equal(img, img2)                   # 같은 갈래 → 같은 영상
    s10 = Sensor.create(dict(CFG["camera"], bit_depth=10), G.width, G.height, rng)
    i10, _ = s10.expose(irr, G.roi_y0, SeedTree(1).child("n").rng())
    assert i10.dtype == np.uint16 and i10.max() <= 1023 and s10.pixel_format == "GRAY10"


def test_frame_times_and_drops():
    t = 10 ** 12 + np.arange(1000, dtype=np.int64) * 8_333_333
    idx, th, drop = frame_times(t, CFG["camera"], SeedTree(2).child("t").rng())
    assert len(idx) == 1000 and np.all(np.diff(th) > 0) and drop.sum() == 0 and th[0] > t[0]
    idx, th, drop = frame_times(t, CFG["camera"], SeedTree(2).child("t").rng(), drop_prob=0.05)
    assert drop.sum() == 1000 - len(idx) > 0 and np.all(np.diff(idx) - 1 == drop[1:])
