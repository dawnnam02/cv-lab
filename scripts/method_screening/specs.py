"""specs.py — 후보 사양 CSV 읽기 (청사진 0_방법탐색 4.1절 열 + 8.1절 mode·cal_class).

- docs/0_방법탐색/후보-사양_*.csv 를 모두 읽어 합친다 (1차 A–D, 2차 E1–E10). 파일마다 열이 달라도 되고,
  없는 열은 NaN(문자 열은 빈 값)으로 채운다.
- 빈 값·숫자 아닌 값('~10', '5,000,000', '500만 원', '≤5 µm', '추정 5', '5(추정)')을 견딘다.
- 범위 표기('5~10', '5-10', '5 µm ~ 10 µm', '5~10만')는 보수적인 쪽을 쓴다: 기본은 큰 쪽.
  단 값이 클수록 유리한 열(CONSERVATIVE_MIN: max_slope·depth·fov·in_situ)은 작은 쪽.
- 같은 id 가 두 번 나오면(같은 파일이든 다른 파일이든) ValueError 로 멈춘다.
- 읽을 수 없는 행(열 개수 초과, id 없음, mode·cal_class 값 오류)은 경고만 내고 건너뛴다.
  건너뛴 행은 DataFrame.attrs['skipped'] = [(id, 파일, 사유), ...] 에 남는다 (screen.py 가 입력경고.txt 로 씀).
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
           "cost_krw", "access", "surface_dep", "in_situ", "safety", "learn_weeks", "sources",
           "mode", "cal_class"]
NUMERIC = ["z_sigma_um", "xy_step_um", "xy_blur_um", "fov_mm", "depth_mm", "edge_loss_um",
           "max_slope_deg", "time_min", "cost_krw", "surface_dep", "in_situ", "learn_weeks"]
# 선택 숫자 열 (있을 때만 씀): 선 단면 장비(mode line_profiler)의 주사 속도 [µm/s]·줄당 이동 시간 [s]
OPTIONAL_NUMERIC = ["scan_speed_um_s", "line_overhead_s"]
TEXT = ["id", "name", "config", "access", "safety", "sources", "mode", "cal_class"]
# 범위 표기에서 작은 쪽이 보수적인 열 (값이 클수록 유리)
CONSERVATIVE_MIN = {"max_slope_deg", "depth_mm", "fov_mm", "in_situ"}

# 청사진 8.1절 허용값. 빈 값(1차 A–D CSV 처럼 열이 없음) → simulate.py 의 id 목록 상수로 판정.
MODES = ("area", "line_profiler", "raster_point", "point_probe", "2d", "indirect")
CAL_CLASSES = ("calibrated", "industrial", "diy", "printer_axis")

# 접촉식 판정: 청사진 3절 그룹 '접촉식' = M01–M04. 1차(M01–M23)는 이 목록으로만 판정한다.
# 2차(M24–)와 그 밖의 id 는 이름·구성 낱말로 판정: 강한 접촉 낱말 → 광학 낱말 → 일반 접촉 낱말 순.
# 선택 열 'probe'('contact' / 'optical')가 있으면 그 값이 우선한다.
CONTACT_IDS = {"M01", "M02", "M03", "M04"}
FIRST_ROUND_IDS = {f"M{i:02d}" for i in range(1, 24)}
CONTACT_STRONG = ["접촉식", "접촉 프로브", "터치 프로브", "스캐닝 프로브", "촉침", "stylus", "contracer",
                  "거칠기", "인디케이터", "indicator", "리니어 게이지", "하이트게이지"]
OPTICAL_WORDS = ["비접촉", "레이저", "laser", "광학", "optical", "카메라", "camera", "영상", "현미경",
                 "공초점", "간섭", "구조광", "스캐너", "x선", "x-ray"]
CONTACT_WORDS = ["접촉", "cmm", "3차원 측정기", "캘리퍼", "마이크로미터", "다이얼", "bltouch", "로드셀"]

_NUM_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_MULT_RE = r"(억|천만|만|천)?"
_RANGE_RE = re.compile(r"(\d+\.?\d*|\.\d+)\s*" + _MULT_RE + r"\s*[a-zA-Zµμ%°㎛㎜/원\s]*?\s*"
                       r"(?:~|∼|〜|～|-|to|에서)\s*\+?(\d+\.?\d*|\.\d+)\s*" + _MULT_RE)
_MULT = {"억": 1e8, "천만": 1e7, "만": 1e4, "천": 1e3, None: 1.0, "": 1.0}


def to_num(v, prefer: str = "max") -> float:
    """문자열에서 숫자를 뽑는다. '500만' → 5e6, '1.2억' → 1.2e8, '추정 5' → 5. 실패하면 NaN.
    범위 '5~10' · '5-10' · '5 µm ~ 10 µm' 는 prefer='max' 면 큰 쪽(기본, 보수적), 'min' 이면 작은 쪽."""
    if v is None:
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v) if np.isfinite(v) else np.nan
    s = str(v).strip().replace(",", "").replace("−", "-").replace("–", "-").replace("—", "-")
    if not s or s.lower() in ("nan", "none", "na", "n/a", "-", "?"):
        return np.nan
    m = _NUM_RE.search(s)
    if not m:
        return np.nan
    r = None if ("e" in m.group(0).lower()) else _RANGE_RE.search(s, m.start())
    if r is not None and r.start() == m.start() + (1 if m.group(0)[0] in "+-" else 0):
        f1, f2 = _MULT[r.group(2)], _MULT[r.group(4)]
        if r.group(2) is None and r.group(4) is not None:      # '5~10만' → 5만 ~ 10만
            f1 = f2
        a = float(r.group(1)) * f1 * (-1 if m.group(0).startswith("-") else 1)
        b = float(r.group(3)) * f2
        return min(a, b) if prefer == "min" else max(a, b)
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


def _read_one(path: str, bad: list | None = None) -> pd.DataFrame:
    """CSV 한 개. 열 개수가 머리글보다 많은 행은 건너뛰고 bad 에 (첫 칸, 사유) 를 남긴다."""
    last = None
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        got = []

        def on_bad(fields, _got=got):
            _got.append((str(fields[0]).strip() if fields else "", f"열 {len(fields)}개 (머리글보다 많음)"))
            return None

        try:
            df = pd.read_csv(path, dtype=str, encoding=enc, keep_default_na=False,
                             skipinitialspace=True, engine="python", on_bad_lines=on_bad)
        except UnicodeDecodeError as e:
            last = e
            continue
        if bad is not None:
            bad.extend(got)
        return df
    raise last


def is_contact(row) -> bool:
    p = str(row.get("probe", "") or "").strip().lower()
    if p in ("contact", "접촉"):
        return True
    if p in ("optical", "광학", "2d"):
        return False
    rid = str(row["id"]).upper()
    if rid in CONTACT_IDS:
        return True
    if rid in FIRST_ROUND_IDS:
        return False
    text = (str(row.get("name", "")) + " " + str(row.get("config", ""))).lower()
    if any(w.lower() in text for w in CONTACT_STRONG):
        return True
    if any(w.lower() in text for w in OPTICAL_WORDS):
        return False
    return any(w.lower() in text for w in CONTACT_WORDS)


def id_sort_key(rid: str):
    """'M2' < 'M10' < 'M100' 이 되게 (접두 글자, 숫자, 나머지)."""
    m = re.fullmatch(r"([A-Za-z]*)(\d+)(.*)", str(rid))
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (str(rid), -1, "")


def _clean_choice(v):
    s = str(v if v is not None else "").strip().lower()
    return "" if s in ("", "nan", "none", "na", "-") else s


def load_specs(paths) -> pd.DataFrame:
    """CSV 경로 목록 → 정리된 DataFrame (id 순, M2 < M10 < M100). 빈 목록이면 ValueError.
    id 중복은 ValueError. 읽을 수 없는 행은 경고 후 건너뛰고 attrs['skipped'] 에 남긴다."""
    paths = list(paths)
    if not paths:
        raise ValueError("사양 CSV 가 없습니다.")
    frames, skipped = [], []
    for p in paths:
        bad = []
        df = _read_one(p, bad)
        df.columns = [str(c).strip().lower() for c in df.columns]
        df["_src"] = os.path.basename(p)
        frames.append(df)
        skipped += [(i, os.path.basename(p), why) for i, why in bad]
    df = pd.concat(frames, ignore_index=True, sort=False)
    for c in COLUMNS + OPTIONAL_NUMERIC:
        if c not in df.columns:
            df[c] = np.nan
    df["id"] = df["id"].astype(str).str.strip().str.upper()
    noid = df["id"].eq("") | df["id"].str.lower().isin(["nan", "none"])
    for _, r in df[noid].iterrows():
        nm = str(r.get("name", "") or "").strip()
        if nm and nm.lower() != "nan":
            skipped.append(("(id 없음: " + nm[:30] + ")", r["_src"], "id 없음"))
    df = df[~noid].copy()
    dup = df["id"][df["id"].duplicated(keep=False)]
    if len(dup):
        where = {i: sorted(set(df.loc[df["id"] == i, "_src"])) for i in dup.unique()}
        raise ValueError(f"중복 id {where} — 사양 CSV 를 고친 뒤 다시 실행하세요.")
    # mode·cal_class: 빈 값은 허용 (id 목록 상수로 판정), 허용값 밖이면 그 행을 건너뜀
    for c, allowed in (("mode", MODES), ("cal_class", CAL_CLASSES)):
        df[c] = df[c].map(_clean_choice)
        badv = df[c].ne("") & ~df[c].isin(allowed)
        for _, r in df[badv].iterrows():
            skipped.append((r["id"], r["_src"], f"{c} '{r[c]}' 은 허용값 {list(allowed)} 밖"))
        df = df[~badv].copy()
    for c in NUMERIC + OPTIONAL_NUMERIC:
        pref = "min" if c in CONSERVATIVE_MIN else "max"
        df[c] = df[c].map(lambda v, _p=pref: to_num(v, _p))
    df["measures_z"] = df["measures_z"].map(to_bool01)
    for c in TEXT:
        df[c] = df[c].astype(str).str.strip().replace({"nan": ""})
    df["access"] = df["access"].str.lower()
    df["contact"] = df.apply(is_contact, axis=1)
    for rid, src, why in skipped:
        warnings.warn(f"[입력] {src} 의 행 '{rid}' 건너뜀: {why}")
    df = df.iloc[sorted(range(len(df)), key=lambda k: id_sort_key(df["id"].iloc[k]))].reset_index(drop=True)
    df.attrs["skipped"] = skipped
    return df


def find_spec_files(spec_dir: str):
    return sorted(glob.glob(os.path.join(spec_dir, "후보-사양_*.csv")))
