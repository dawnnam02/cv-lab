"""저장된 스키마·규칙표 읽기와 명세 지문 대조."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from cvlab.io import spec_schema as ss

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "docs" / "하드웨어-데이터-명세.md"
SPEC_DIR = ROOT / "config" / "spec"


class SchemaError(RuntimeError):
    """스키마 파일이 없거나 명세 지문이 다름."""


def _read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def source_sha(spec_dir: Path = SPEC_DIR) -> str:
    t = (spec_dir / "SOURCE.txt").read_text(encoding="utf-8")
    m = re.search(r"^spec_sha256: ([0-9a-f]{64})$", t, re.M)
    if not m:
        raise SchemaError("SOURCE.txt에 spec_sha256이 없음")
    return m.group(1)


def load(spec_dir: Path = SPEC_DIR, spec: Path = SPEC, check_spec: bool = True):
    """(fields, rules, file_cols). 명세 지문이 SOURCE.txt와 다르면 SchemaError."""
    try:
        fields = _read(spec_dir / "fields_v1.0.csv")
        rules = _read(spec_dir / "rules_v1.0.csv")
    except OSError as e:
        raise SchemaError(f"스키마 파일을 못 읽음: {e}") from e
    if check_spec:
        if not spec.exists():
            raise SchemaError(f"명세 파일 없음: {spec}")
        if ss.sha256_file(spec) != source_sha(spec_dir):
            raise SchemaError("명세 지문이 SOURCE.txt와 다름: scripts/extract_spec_schema.py로 다시 뽑을 것")
    return fields, rules, ss.file_columns(spec)
