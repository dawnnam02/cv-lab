"""재현성: 시드 고정, git 상태, 실행 기록 manifest.json (세부청사진 T6 SV10, J2).

- 난수는 `np.random.default_rng(seed)`로 만든 Generator를 함수 인자로 넘긴다 (전역 시드 안 씀).
- git은 읽기 명령만 쓴다 (`rev-parse`, `status --porcelain`). git이 없으면 "unknown".
- 결과 폴더는 덮어쓰지 않는다.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from importlib import metadata
from pathlib import Path

import numpy as np
import yaml

from cvlab.io.hashing import sha256_file

DEFAULT_SEED = 42  # J2 결정: random_seed 42
KST = timezone(timedelta(hours=9))
LIBS = ("numpy", "scipy", "pandas", "matplotlib", "pytest", "PyYAML", "Pillow")


def make_rng(seed: int | None = None) -> np.random.Generator:
    return np.random.default_rng(DEFAULT_SEED if seed is None else seed)


def git_info(cwd: str | Path | None = None) -> dict:
    """{'commit': 40자 또는 'unknown', 'dirty': bool 또는 'unknown'}."""
    try:
        c = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=20)
        if c.returncode != 0:
            return {"commit": "unknown", "dirty": "unknown"}
        s = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, timeout=60)
        dirty = bool(s.stdout.strip()) if s.returncode == 0 else "unknown"
        return {"commit": c.stdout.strip(), "dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": "unknown", "dirty": "unknown"}


def lib_versions() -> dict:
    out = {}
    for name in LIBS:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = "missing"
    return out


def now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def build_manifest(command: list[str] | str, seed: int, inputs: list[str | Path], config: dict,
                   timestamp: str | None = None, git: dict | None = None, run_name: str = "") -> dict:
    """manifest 사전. timestamp·git을 넘기면 그 값을 쓴다 (시험용)."""
    return {
        "run_name": run_name,
        "timestamp": timestamp or now_iso(),
        "git": git if git is not None else git_info(),
        "random_seed": seed,
        "command": command if isinstance(command, str) else " ".join(command),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "libraries": lib_versions(),
        "inputs": {Path(p).as_posix(): sha256_file(p) for p in sorted(map(str, inputs))},
        "config": config,
    }


def manifest_bytes(manifest: dict) -> bytes:
    return (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def start_run(results_dir: str | Path, run_name: str, command: list[str] | str, seed: int,
              inputs: list[str | Path], config: dict, timestamp: str | None = None, git: dict | None = None) -> Path:
    """results/<run_name>/ 를 새로 만들고 manifest.json · config_resolved.yaml을 쓴다. 이미 있으면 FileExistsError."""
    out = Path(results_dir) / run_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(exist_ok=False)
    m = build_manifest(command, seed, inputs, config, timestamp, git, run_name)
    with open(out / "manifest.json", "xb") as f:
        f.write(manifest_bytes(m))
    with open(out / "config_resolved.yaml", "x", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=True)
    return out
