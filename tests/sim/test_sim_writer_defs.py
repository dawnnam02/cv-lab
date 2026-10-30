# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""쓰기 상수 (v1.2 초안 `_qNN` · 이름 규칙) · ChArUco 판 · PNG (T3-1). 무거운 캠페인 쓰기는 명령 ③ · ⑥으로 봄."""
from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from cvlab.sim.optics import charuco_texture, load_aruco_bits
from cvlab.sim.simconfig import ROOT
from cvlab.sim.specdefs import SCAN_ID_RE, file_columns, layer_dir, scan_id
from cvlab.sim.writer import png_bytes


def test_scan_ids_with_repeat():
    assert scan_id("S01", 1, "L008") == "S01_r01_L008"
    assert scan_id("S01", 1, "L008", 0, 1) == "S01_r01_L008_q01"
    assert scan_id("S01", 1, "L008", 1, 2) == "S01_r01_L008_p01_q02"
    assert scan_id("S01", 1, "post") == "S01_r01" and scan_id("S01", 1, "post", 1) == "S01_r01_p01"
    assert layer_dir("L008", 0, 3) == "L008_q03" and layer_dir("post", 1) == "post_p01"
    with pytest.raises(ValueError):
        layer_dir("post", 0, 1)                      # post에는 _q 없음 (V12-2)
    assert all(SCAN_ID_RE.match(s) for s in ("S01_r01_L000_q01", "S02_r03"))


def test_columns_from_schema():
    c = file_columns()
    assert c["meta.json"][0] == "scan_id" and len(c["meta.json"]) == 118
    assert "trig_pulse_idx" in c["frames_index.csv"] and "pass_idx" in c["position_log.csv"]


def test_aruco_table_and_board():
    bits = load_aruco_bits()
    assert len(bits) == 50 and bits[0].tolist() == [[1, 0, 1, 1], [0, 1, 0, 1], [0, 0, 1, 1], [0, 0, 1, 0]]
    head = (ROOT / "config" / "sim" / "aruco_dict_4x4_50.csv").read_text(encoding="utf-8").splitlines()[:3]
    assert any("OpenCV 4.13.0" in h and "Apache" in h for h in head)
    tex = charuco_texture(1.5, 6, 9, 1.1, bits)
    W, H = 13.5, 9.0
    assert tex(np.array([-W / 2 + 0.05]), np.array([H / 2 - 0.05]))[0] < 0.2      # 왼쪽 위 칸 검정
    assert tex(np.array([-W / 2 + 1.5 + 0.05]), np.array([H / 2 - 0.05]))[0] > 0.8  # 그 옆 흰 칸 (마커 테 밖)
    # 마커 0 (첫 흰 칸) 안쪽 비트를 읽으면 비트표와 같음
    cell = 1.1 / 6
    x0 = -W / 2 + 1.5 + 0.2
    y0 = H / 2 - 0.2
    got = [[int(tex(np.array([x0 + (c + 1.5) * cell]), np.array([y0 - (r + 1.5) * cell]))[0] > 0.5) for c in range(4)]
           for r in range(4)]
    assert got == bits[0].tolist()


def test_png_level_fixed_and_no_time_chunk():
    img = (np.arange(256 * 64) % 251).astype(np.uint8).reshape(64, 256)
    a, b = png_bytes(img, 3), png_bytes(img, 3)
    assert a == b and b"tIME" not in a
    assert np.array_equal(np.array(Image.open(io.BytesIO(a))), img)
    i16 = (img.astype(np.uint16) * 4)
    assert np.array_equal(np.array(Image.open(io.BytesIO(png_bytes(i16, 3)))), i16)


def test_png_threads_same_bytes():
    """T3-2: PNG 인코딩을 스레드로 겹쳐도 결과 바이트 · 순서가 같음."""
    from types import SimpleNamespace
    from cvlab.sim.writer import Writer
    w = SimpleNamespace(cfg={"camera": {"png_threads": 2}}, png_level=3)
    imgs = [((np.arange(64 * 256) + k) % 251).astype(np.uint8).reshape(64, 256) for k in range(6)]
    futs = [Writer._png_async(w, im) for im in imgs]
    assert [f.result() for f in futs] == [png_bytes(im, 3) for im in imgs]
    w._pool.shutdown()


def test_no_opencv_in_sim_paths():
    pat = re.compile(r"^\s*(import cv2|from cv2)", re.M)
    files = list((ROOT / "src" / "cvlab" / "sim").glob("*.py")) + [ROOT / "scripts" / "sim_generate.py"] + \
        list((ROOT / "tests" / "sim").glob("*.py"))
    assert [f.name for f in files if pat.search(Path(f).read_text(encoding="utf-8"))] == []
