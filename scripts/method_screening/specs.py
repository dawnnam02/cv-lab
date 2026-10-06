"""specs.py — 후보 사양 CSV 읽기 (청사진 0_방법탐색 4.1절 열 그대로).

- docs/0_방법탐색/후보-사양_*.csv 를 모두 읽어 합친다.
- 빈 값·숫자 아닌 값('~10', '5,000,000', '500만 원', '≤5 µm')을 견딘다: 첫 숫자만 뽑고, 못 뽑으면 NaN.
- 같은 id 가 여러 파일에 있으면 나중 파일의 행을 쓰고 경고를 남긴다.
"""
from __future__ import annotations

import glob
import os
import re
import warnings

import numpy as np
import pandas as pd

COLUMNS = ["id", "name", "config", "z_sigma_um", "xy_step_um", "xy_blur_um", "fov_mm",
           "depth_mm", "measures_z", "edge_loss_um", "max_slope_deg", "time_min",
           "cost_krw", "access", "surface_dep", "in_situ", "safety", "learn_weeks", "sources"]
NUMERIC = ["z_sigma_um", "xy_step_um", "xy_blur_um", "fov_mm", "depth_mm", "edge_loss_um",
           "max_slope_deg", "time_min", "cost_krw", "surface_dep", "in_situ", "learn_weeks"]
TEXT = ["id", "name", "config", "access", "safety", "sources"]

# 접촉식 판정: 청사진 3절 그룹 '접촉식' = M01–M04. 그 밖의 id 는 이름·구성 낱말로 판정.
# (선택 열 'probe' 가 있으면 'contact' / 'optical' 값이 우선한다.)
CONTACT_IDS = {"M01", "M02", "M03", "M04"}
CONTACT_WORDS = ["접촉", "촉침", "stylus", "cmm", "3차원 측정기", "캘리퍼", "마이크로미터",
                 "하이트게이지", "다이얼", "bltouch", "로드셀"]

_NUM_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def to_num(v) -> float:
    """문자열에서 첫 숫자를 뽑는다. '500만' → 5e6, '1.2억' → 1.2e8. 실패하면 NaN."""
    if v is None:
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v) if np.isfinite(v) else np.nan
    s = str(v).strip().replace(",", "").replace("−", "-").replace("–", "-")
    if not s or s.lower() in ("nan", "none", "na", "n/a", "-", "?"):
        return np.nan
    m = _NUM_RE.search(s)
    if not m:
        return np.nan
    x = float(m.group(0))
    tail = s[m.end():m.end() + 3]
    if tail.startswith("억"):
        x *= 1e8
    elif tail.startswith("천만"):
        x *= 1e7
    elif tail.startswith("만"):
        x *= 1e4
    elif tail.startswith("천"):
        x *= 1e3
    return x


def to_bool01(v) -> float:
    """measures_z 같은 0/1 열. '1','yes','o','예','가능' → 1, '0','no','x','아니오','불가' → 0."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).strip().lower()
    if s in ("1", "1.0", "y", "yes", "o", "true", "예", "가능", "있음"):
        return 1.0
    if s in ("0", "0.0", "n", "no", "x", "false", "아니오", "불가", "없음"):
        return 0.0
    x = to_num(s)
    return float(x > 0.5) if np.isfinite(x) else np.nan


def _read_one(path: str) -> pd.DataFrame:
    last = None
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return pd.read_csv(path, dtype=str, encoding=enc, keep_default_na=False,
                               skipinitialspace=True)
        except UnicodeDecodeError as e:
            last = e
    raise last


def is_contact(row) -> bool:
    p = str(row.get("probe", "") or "").strip().lower()
    if p in ("contact", "접촉"):
        return True
    if p in ("optical", "광학", "2d"):
        return False
    if str(row["id"]).upper() in CONTACT_IDS:
        return True
    if re.fullmatch(r"M\d\d", str(row["id"]).upper()):
        return False
    text = (str(row.get("name", "")) + " " + str(row.get("config", ""))).lower()
    return any(w.lower() in text for w in CONTACT_WORDS)


def load_specs(paths) -> pd.DataFrame:
    """CSV 경로 목록 → 정리된 DataFrame (id 순). 빈 목록이면 ValueError."""
    paths = list(paths)
    if not paths:
        raise ValueError("사양 CSV 가 없습니다.")
    frames = []
    for p in paths:
        df = _read_one(p)
        df.columns = [str(c).strip().lower() for c in df.columns]
        df["_src"] = os.path.basename(p)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True, sort=False)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df["id"] = df["id"].astype(str).str.strip()
    df = df[df["id"].ne("") & df["id"].str.lower().ne("nan")].copy()
    dup = df["id"][df["id"].duplicated(keep="last")].unique()
    if len(dup):
        warnings.warn(f"중복 id {list(dup)}: 나중 파일의 행을 씁니다.")
    df = df.drop_duplicates("id", keep="last")
    for c in NUMERIC:
        df[c] = df[c].map(to_num)
    df["measures_z"] = df["measures_z"].map(to_bool01)
    for c in TEXT:
        df[c] = df[c].astype(str).str.strip().replace({"nan": ""})
    df["access"] = df["access"].str.lower()
    df["contact"] = df.apply(is_contact, axis=1)
    return df.sort_values("id").reset_index(drop=True)


def find_spec_files(spec_dir: str):
    return sorted(glob.glob(os.path.join(spec_dir, "후보-사양_*.csv")))
