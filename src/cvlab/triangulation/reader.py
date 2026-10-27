"""명세 frame 묶음 얇은 읽기 (명세 1절, 884daac 기준).

명세가 아직 바뀌는 중이라 일부러 얇게 둡니다: 필드 이름은 `SPEC_FRAME_COLUMNS` 한 곳에만,
허용 값 검사는 하지 않음 (T6 검증기 몫), 아무것도 쓰지 않음. 통합은 T6 SV13 · T9.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# 명세 1절 frame 필드 중 이 모듈이 쓰는 것: 이름 → (형, 필수 여부). 필드 이름은 여기에만 둡니다.
# 필수 = 이 모듈이 읽으려면 열이 있어야 함. 조건부 열은 있으면 형 변환, 없어도 오류 아님.
SPEC_FRAME_COLUMNS = {
    "frame_idx": ("int", True),
    "file": ("str", True),
    "laser_on": ("bool", True),
    "bit_depth": ("int", True),
    "roi_x0_px": ("int", True),
    "roi_y0_px": ("int", True),
    "roi_w_px": ("int", True),
    "roi_h_px": ("int", True),
    "t_host_ns": ("int", True),
    "trig_pulse_idx": ("int", False),
    "gate_on": ("bool", False),
}
INDEX_FILE = "frames_index.csv"


def _required():
    return [k for k, (_, req) in SPEC_FRAME_COLUMNS.items() if req]


def _to_bool(s: pd.Series, name: str) -> pd.Series:
    m = {"true": True, "false": False}
    low = s.str.strip().str.lower()
    bad = low.notna() & ~low.isin(list(m))
    if bad.any():
        raise ValueError(f"열 {name}: true/false가 아닌 값 {sorted(set(s[bad]))[:5]}")
    out = low.map(m)
    return out.astype(bool) if out.notna().all() else out.astype("boolean")


def _to_int(s: pd.Series, name: str) -> pd.Series:
    st = s.str.strip()
    try:
        out = pd.to_numeric(st, errors="raise")
    except (ValueError, TypeError) as e:
        raise ValueError(f"열 {name}: 정수가 아닌 값 ({e})") from None
    if out.notna().all():
        if not np.all(np.asarray(out) == np.round(np.asarray(out))):
            raise ValueError(f"열 {name}: 정수가 아닌 값")
        return out.astype(np.int64)
    return out.astype("Int64")


def read_frames_index(scan_dir) -> pd.DataFrame:
    """`<scan_dir>/frames_index.csv`를 읽음. 필수 열이 없으면 그 열 이름을 담은 ValueError.

    쓰는 열만 형 변환 (int · bool), 모르는 열은 문자열 그대로 통과.
    """
    path = Path(scan_dir) / INDEX_FILE
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8")
    miss = [c for c in _required() if c not in df.columns]
    if miss:
        raise ValueError(f"{path}: 필수 열이 없음 {miss}")
    for name, (kind, _) in SPEC_FRAME_COLUMNS.items():
        if name not in df.columns:
            continue
        if kind == "int":
            df[name] = _to_int(df[name], name)
        elif kind == "bool":
            df[name] = _to_bool(df[name], name)
    return df


def load_frame(scan_dir, row) -> np.ndarray:
    """색인 한 행의 영상 → uint16 [roi_h_px, roi_w_px]. 8비트 PNG도 uint16으로 (값은 그대로).

    `frames/NNNNNN.png` (Pillow) 또는 `frames.npz#fNNNNNN`. 크기가 ROI와 다르면 ValueError.
    """
    scan_dir = Path(scan_dir)
    file = row["file"]
    if file is None or (isinstance(file, float) and np.isnan(file)) or pd.isna(file) or str(file).strip() == "":
        raise ValueError("이 행의 file이 비어 있음 (meta.raw_saved = false?)")
    file = str(file).strip()
    if "#" in file:
        npz, key = file.split("#", 1)
        with np.load(scan_dir / npz, allow_pickle=False) as z:
            if key not in z.files:
                raise ValueError(f"{npz}에 키 {key} 없음")
            a = np.asarray(z[key])
    else:
        from PIL import Image

        with Image.open(scan_dir / file) as im:
            mode = im.mode
            a = np.array(im)
        if mode not in ("L", "I;16", "I;16B", "I;16L", "I"):
            raise ValueError(f"{file}: 1채널 8 · 16비트 PNG가 아님 (mode {mode})")
    if a.ndim != 2:
        raise ValueError(f"{file}: 2차원 영상이 아님 {a.shape}")
    if a.dtype.kind not in "ui" or (a.size and (int(a.min()) < 0 or int(a.max()) > 65535)):
        raise ValueError(f"{file}: 16비트 범위를 벗어난 값 또는 정수가 아님")
    a = a.astype(np.uint16)
    h, w = int(row["roi_h_px"]), int(row["roi_w_px"])
    if a.shape != (h, w):
        raise ValueError(f"{file}: 크기 {a.shape} ≠ roi_h_px × roi_w_px ({h}, {w})")
    return a
