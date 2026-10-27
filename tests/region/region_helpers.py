"""T4b 시험 도우미: 합성 G코드 글 만들기와 무거운 빌드 캐시.

손 시험용 G코드 파일은 새로 만들지 않고, 글을 만들어 parse_text에 넣는다 (세부청사진 §3).
"""
from __future__ import annotations

import functools
import os

from cvlab.gcode import GCodeParams, build_reference, parse_file, parse_text
from cvlab.region import aligned_grid, build_region, object_bbox

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HAND = os.path.join(ROOT, "data", "gcode_samples", "hand")
LOCAL = os.path.join(ROOT, "data", "gcode_samples", "_local")
VORON = os.path.join(LOCAL, "test_box_25mm_PLA_3m17s.gcode")
CALIPER = os.path.join(LOCAL, "caliper pyramid test.prusaproject_0.6n_0.35mm_PLA_MK3SMMU2S_16m.gcode")
REGION_YAML = os.path.join(ROOT, "config", "region.yaml")
GCODE_YAML = os.path.join(ROOT, "config", "gcode.yaml")


def block(x0, x1, y0, y1, z, w=0.4, type_name=None):
    """x0–x1 × y0–y1 사각형을 X 방향 선으로 채운 G코드 줄 (명령 ②와 같은 생성기)."""
    out, y, d = [], y0 + w / 2, 1
    if type_name:
        out.append(f";TYPE:{type_name}")
    while y <= y1 - w / 2 + 1e-9:
        a, b = (x0 + w / 2, x1 - w / 2) if d > 0 else (x1 - w / 2, x0 + w / 2)
        out += [f"G0 X{a:.3f} Y{y:.3f} Z{z:.3f}", f"G1 X{b:.3f} Y{y:.3f} E0.5"]
        y += w
        d = -d
    return out


def tower_text(top_k, x1=10.0, y_top=5.0):
    """바닥 0–x1 × 0–10 (Z 0.2) 위에 0–x1 × 0–y_top 탑 (Z 0.2·k, k = 2 … top_k).
    x1 = 10이면 명령 ②의 합성 탑과 같은 G코드. 심도 시험은 x1 = 2로 칸 수를 줄여 빠르게 돈다."""
    L = ["G21", "G90", "M83"] + block(0, x1, 0, 10, 0.2)
    for k in range(2, top_k + 1):
        L += block(0, x1, 0, y_top, round(0.2 * k, 4))
    return "\n".join(L)


def parse_lines(lines, w=0.4):
    return parse_text("\n".join(lines), GCodeParams(line_width_mm=w))


def tower(top_k, **kw):
    return parse_text(tower_text(top_k, **kw), GCodeParams(line_width_mm=0.4))


def aligned_ref(result):
    g = aligned_grid(*object_bbox(result))
    return g, build_reference(result, grid=g)


@functools.lru_cache(maxsize=None)
def built_tower(top_k, camera_side="both", x1=10.0):
    from cvlab.region import RegionParams
    r = tower(top_k, x1=x1)
    g, ref = aligned_ref(r)
    return r, g, ref, build_region(r, ref, RegionParams(camera_side=camera_side))


@functools.lru_cache(maxsize=None)
def built_hand(name):
    r = parse_file(os.path.join(HAND, name))
    g, ref = aligned_ref(r)
    return r, g, ref, build_region(r, ref)


@functools.lru_cache(maxsize=None)
def built_local(path):
    """D-19 파일 한 번만 만든다 (caliper 약 40 s). 시험 여러 개가 함께 씀."""
    r = parse_file(path)
    g, ref = aligned_ref(r)
    return r, g, ref, build_region(r, ref)
