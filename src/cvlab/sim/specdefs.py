# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""writer가 쓰는 명세 상수 한 곳 (명세 v1.2 초안, 팀장검증 7차 §5 · §7).

명세 v1.2 (V-3, 11-05)와 검증기 재동기화 (V-4, 11-07)가 끝나면 **이 파일만** 맞춘다.
- 열 순서: 검증기 스키마 (`cvlab.io.schema_files.load()`의 file_cols)를 그대로 씀 → 재동기화되면 저절로 따라감.
- 판 · 정규식 · 이름 규칙 · 반복 `_qNN` · C2 공차는 아래 상수.
"""
from __future__ import annotations

import re
from functools import lru_cache

SPEC_VERSION = "1.2"            # 명세 v1.2 (403bf95, bc63f843…) · 검증기 V-4 (b77811f, 규칙 911) 뒤 (V12-7)
SPEC_DRAFT = "v1.2 (팀장검증 7차 §7: V12-1 C2 두 줄, V12-2 _qNN, V12-3 ChArUco 규약, V12-6 material_offset_um)"

# 이름 규칙 (명세 8절 + V12-2)
CAMPAIGN_RE = re.compile(r"^VC-\d{4}-\d{2}-\d{2}-[A-Z]$")
SCAN_ID_RE = re.compile(r"^S\d{2}_r\d{2}(_L\d{3})?(_p\d{2})?(_q\d{2})?$")
LAYER_DIR_RE = re.compile(r"^(L\d{3}(_p\d{2})?(_q\d{2})?|post(_p\d{2})?)$")
REF_ID_FMT = "REF-{abbr}-{n:03d}"
NO_PAIR_SCAN_ID = "S00_r00"     # 짝 스캔 없는 기준의 frame · pos scan_id (명세 4절)
C2_CAL_TOL_MM = 0.02            # V12-1: 교정 h1 ≤ 층 Z + 0.02 (공칭 h1 ≤ 층 Z)

FILES = {"meta": "meta.json", "frames": "frames_index.csv", "pos": "position_log.csv", "ref": "ref_index.csv",
         "cal": "cal_manifest.csv", "design": "design.csv", "executed": "design_executed.csv",
         "truth": "truth.json", "mesh": "printer/bed_mesh.json"}


def layer_dir(layer_key: str, spass: int = 0, q: int = 0) -> str:
    """층 폴더 이름. layer_key = 'L004' 또는 'post'. `_q`는 timing = layer만 (V12-2)."""
    if layer_key == "post" and q:
        raise ValueError("post 스캔에는 _q 반복이 없음 (V12-2)")
    name = layer_key + (f"_p{spass:02d}" if spass else "") + (f"_q{q:02d}" if q else "")
    if not LAYER_DIR_RE.match(name):
        raise ValueError(f"층 폴더 이름이 규칙과 다름: {name}")
    return name


def scan_id(specimen_id: str, repeat: int, layer_key: str, spass: int = 0, q: int = 0) -> str:
    base = f"{specimen_id}_r{repeat:02d}"
    d = layer_dir(layer_key, spass, q)
    sid = base + d[len("post"):] if layer_key == "post" else base + "_" + d   # post 스캔 ID에는 층 부분이 없음
    if not SCAN_ID_RE.match(sid):
        raise ValueError(f"스캔 ID가 규칙과 다름: {sid}")
    return sid


@lru_cache(maxsize=1)
def file_columns() -> dict:
    """{파일 이름: 열 목록 (묶음 접두어 뺀 이름, 필드표 순서)} — 검증기 스키마에서."""
    from cvlab.io.schema_files import load
    _, _, fc = load(check_spec=SCHEMA_CHECK_SPEC)
    return {k: list(v) for k, v in fc.items()}


# 스키마 지문 검사 (명세 ↔ config/spec). V-3 커밋 뒤 V-4 전 짧은 사이에만 False로 썼고, V-4 (b77811f) 뒤 True.
SCHEMA_CHECK_SPEC = True
