# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""시뮬레이터 설정 읽기 (config/sim/*.yaml)와 데이터 뿌리 정하기."""
from __future__ import annotations

import copy
import csv
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SIM_CONFIG_DIR = ROOT / "config" / "sim"
SCENARIO_YAML = ROOT / "config" / "scenarios" / "판정시나리오_v1.yaml"
MANIFEST = ROOT / "data" / "gcode_samples" / "MANIFEST.csv"

TOP_KEYS = {"paths", "clock", "run", "grid", "specimens", "judge", "thermal", "gauge_thermal", "z_axis", "deposition",
            "optics", "camera", "motion", "steps", "bed", "calib", "refs"}


def _load(path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_default(path=None) -> dict:
    cfg = _load(path or SIM_CONFIG_DIR / "default.yaml")
    bad = set(cfg) - TOP_KEYS
    if bad:
        raise ValueError(f"default.yaml 모르는 키: {sorted(bad)}")
    return cfg


def load_factors(path=None) -> dict:
    return _load(path or SIM_CONFIG_DIR / "factors.yaml")["factors"]


def load_campaign(path) -> dict:
    c = _load(path)
    if set(c) != {"campaign"}:
        raise ValueError("캠페인 설정 최상위 키는 campaign 하나")
    return c["campaign"]


def load_scenarios(path=None) -> dict:
    y = _load(path or SCENARIO_YAML)
    return {"kinds": y["kinds"], "scenarios": {s["name"]: s for s in y["scenarios"]}}


def merged(cfg: dict, overrides: dict | None) -> dict:
    """얕은 두 단 병합 (절 → 키). 원본은 바꾸지 않음."""
    out = copy.deepcopy(cfg)
    for sec, vals in (overrides or {}).items():
        if isinstance(vals, dict):
            out.setdefault(sec, {}).update(vals)
        else:
            out[sec] = vals
    return out


def specimen_gcode(cfg: dict, name: str) -> tuple[Path, str | None]:
    """시편 이름 → (G코드 경로, 기대 sha256)."""
    s = cfg["specimens"][name]
    if "gcode" in s:
        return ROOT / s["gcode"], s.get("sha256")
    with open(MANIFEST, encoding="utf-8") as fh:
        for m in csv.DictReader(fh):
            if m["이름"] == s["manifest"]:
                return ROOT / m["로컬경로"], m["sha256"]
    raise KeyError(f"MANIFEST에 {s['manifest']} 없음")


def _inside(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def data_roots(cfg: dict, out_root=None) -> tuple[Path, Path]:
    """(raw 뿌리, truth 뿌리). out_root를 주면 그 아래 raw · truth. 저장소 안이면 오류."""
    if out_root is not None:
        raw, truth = Path(out_root) / "raw", Path(out_root) / "truth"
    else:
        p = cfg.get("paths", {})
        if not p.get("raw_root") or not p.get("truth_root"):
            raise ValueError("데이터 뿌리가 설정에 없음: config/sim/default.yaml paths 또는 --out-root")
        raw, truth = Path(p["raw_root"]), Path(p["truth_root"])
    for q in (raw, truth):
        if _inside(q, ROOT):
            raise ValueError(f"데이터 뿌리가 저장소 안: {q} (OneDrive 저장소에는 쓰지 않음)")
    if _inside(raw, truth) or _inside(truth, raw):
        raise ValueError("raw와 truth 뿌리는 서로 안에 있으면 안 됨 (참값 분리)")
    return raw, truth
