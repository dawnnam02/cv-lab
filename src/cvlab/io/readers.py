"""스캔 폴더 하나 읽기 (F3, 명세 §1·§2·§5).

자료형은 명세 필드표대로 바꾼다. 결측은 JSON이면 None, 표면 NaN(실수)·<NA>(정수·참거짓·문자열)이다.
`data/_truth` 아래는 열지 않는다.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd

from cvlab.io.validate import check_path_allowed

PD_DTYPES = {"int": "Int64", "int64": "Int64", "float": "float64", "bool": "boolean", "str": "string"}


def _dtypes(fields: list[dict], group: str) -> dict[str, str]:
    return {f["field"].split(".", 1)[1]: f["dtype"] for f in fields if f["group"] == group}


def read_csv_typed(path: str | Path, fields: list[dict], group: str) -> pd.DataFrame:
    """명세 CSV를 자료형대로 읽는다. 빈 칸 → 결측. 'true'/'false' → bool."""
    check_path_allowed(path)
    dts = _dtypes(fields, group)
    text = Path(path).read_bytes().decode("utf-8")
    raw = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    out = {}
    for col in raw.columns:
        dt = dts.get(col, "str")
        s = raw[col].replace("", pd.NA)
        if dt == "bool":
            s = s.map({"true": True, "false": False}, na_action="ignore")
        elif dt in ("int", "int64"):
            s = pd.to_numeric(s, errors="raise")
        elif dt == "float":
            s = pd.to_numeric(s, errors="raise").astype("float64")
        out[col] = s.astype(PD_DTYPES.get(dt, "string"))
    return pd.DataFrame(out, columns=list(raw.columns))


def read_meta(path: str | Path) -> dict:
    check_path_allowed(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_scan(scan_dir: str | Path, fields: list[dict]) -> dict:
    """스캔 폴더 하나: {'meta': dict, 'frames': DataFrame, 'pos': DataFrame, 'dir': Path}."""
    check_path_allowed(scan_dir)
    d = Path(scan_dir)
    return {
        "dir": d,
        "meta": read_meta(d / "meta.json"),
        "frames": read_csv_typed(d / "frames_index.csv", fields, "frame"),
        "pos": read_csv_typed(d / "position_log.csv", fields, "pos"),
    }
