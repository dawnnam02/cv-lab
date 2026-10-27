"""한 번 쓰기 보호 (F3 원본 불변, 명세 §0.1 · §0.5 "덮어쓰기 금지").

폴더나 파일이 이미 있으면 FileExistsError. 고칠 일이 생기면 새 ID로 다시 만든다.
"""

from __future__ import annotations

import json
from pathlib import Path

from cvlab.io.validate import check_path_allowed


def create_dir_once(path: str | Path) -> Path:
    """새 폴더를 만든다. 이미 있으면 FileExistsError (부모 폴더는 만들어 줌)."""
    check_path_allowed(path)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.mkdir(exist_ok=False)
    return p


def write_bytes_once(path: str | Path, data: bytes) -> Path:
    """새 파일에 쓴다. 이미 있으면 FileExistsError ('xb' 모드)."""
    check_path_allowed(path)
    p = Path(path)
    with open(p, "xb") as f:
        f.write(data)
    return p


def write_json_once(path: str | Path, obj) -> Path:
    """명세 §0.5: 들여쓰기 2칸, ensure_ascii=False, 줄 끝 \\n."""
    return write_bytes_once(path, (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def write_csv_once(path: str | Path, rows: list[dict], columns: list[str]) -> Path:
    """명세 §0.5: UTF-8 BOM 없음, 줄 끝 \\n, 결측 빈 칸, 참거짓 소문자."""
    def cell(v):
        if v is None:
            return ""
        if isinstance(v, bool):
            return "true" if v else "false"
        s = repr(v) if isinstance(v, float) else str(v)
        return '"' + s.replace('"', '""') + '"' if any(c in s for c in ',"\n') else s
    lines = [",".join(columns)] + [",".join(cell(r.get(c)) for c in columns) for r in rows]
    return write_bytes_once(path, ("\n".join(lines) + "\n").encode("utf-8"))
