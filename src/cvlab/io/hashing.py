"""SHA-256 도우미 (F3, 명세 frame.sha256 · meta.files_sha256)."""

from __future__ import annotations

import hashlib
from pathlib import Path

HEX64 = frozenset("0123456789abcdef")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def is_sha256_hex(s: object) -> bool:
    return isinstance(s, str) and len(s) == 64 and set(s) <= HEX64


def sha256_tree(root: str | Path, exclude: tuple[str, ...] = ()) -> dict[str, str]:
    """폴더 안 파일별 지문 {상대 경로 ('/' 구분): sha256}. 정렬된 순서."""
    root = Path(root)
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if rel in exclude:
                continue
            out[rel] = sha256_file(p)
    return out
