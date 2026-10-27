"""tests/infra 공통 도우미 (이름 앞에 infra_를 붙여 다른 시험 폴더와 안 겹치게 함)."""

from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "하드웨어-데이터-명세.md"
SPEC_DIR = ROOT / "config" / "spec"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def load_script(name: str):
    """scripts/<name>.py를 모듈로 읽는다."""
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"infra_script_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@functools.lru_cache(maxsize=1)
def schema():
    from cvlab.io.schema_files import load
    return load()


@functools.lru_cache(maxsize=1)
def selftest_report():
    """메모리 표본만 (디스크 표본은 disk_campaign()이 한 번 씀: Windows 파일 열기가 느려서)."""
    from cvlab.io.selftest import run_selftest
    return run_selftest(*schema(), disk=False)


@functools.lru_cache(maxsize=1)
def fake_repo() -> Path:
    """표본 meta.gcode_file · slicer_profile_file (selftest.REPO_FILES)이 있는 임시 저장소 뿌리 (CLI --repo-root용).

    CLI 기본 뿌리는 cv-lab 저장소인데 거기에는 표본 G코드가 없어 FILE-17 · 18이 나오는 것이 맞다 (S-5).
    """
    import atexit
    import shutil
    import tempfile
    from cvlab.io import selftest as st
    td = Path(tempfile.mkdtemp(prefix="cvlab_repo_"))
    atexit.register(shutil.rmtree, td, True)
    for rel in st.REPO_FILES:
        (td / rel).parent.mkdir(parents=True, exist_ok=True)
        (td / rel).write_bytes(b"; gcode\n")
    return td


@functools.lru_cache(maxsize=1)
def disk_campaign() -> Path:
    """정상 표본을 임시 폴더에 한 번 쓴다. 시험이 끝나면 지운다."""
    import atexit
    import shutil
    import tempfile
    from cvlab.io import selftest as st
    td = Path(tempfile.mkdtemp(prefix="cvlab_infra_"))
    atexit.register(shutil.rmtree, td, True)
    root = td / "raw" / st.CAMPAIGN
    st.write_tree(st.serialize(st.normal_model(), schema()[2]), root)
    return root
