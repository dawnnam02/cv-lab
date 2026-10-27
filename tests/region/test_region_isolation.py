"""RG15 정보 차단 · 스크립트 쓰기 거부."""
import os
import re
import subprocess
import sys

from region_helpers import HAND, ROOT

OWN = [os.path.join(ROOT, "src", "cvlab", "region"), os.path.join(ROOT, "tests", "region"),
       os.path.join(ROOT, "scripts", "region_mask.py"), os.path.join(ROOT, "config", "region.yaml")]
# 찾는 글을 이 파일 (과 컴파일된 .pyc)에 그대로 남기지 않도록 실행 중에 조각을 이어 붙임 (상수 접기 피함)
_PARTS = [["cvlab", r"\.(io|sim|triangulation|config|repro)"], ["_tr", "uth"], ["scen", "arios"],
          ["판정-시나", "리오"], ["scenario", "_expected"], ["gcode_", "candidates"]]
BANNED = re.compile("|".join("".join(p) for p in _PARTS))


def _files():
    for p in OWN:
        if os.path.isdir(p):
            for d, _, fs in os.walk(p):
                for f in fs:
                    if f.endswith((".py", ".yaml")):
                        yield os.path.join(d, f)
        else:
            yield p


def test_region_no_forbidden_imports_or_paths():
    hits = []
    for f in _files():
        for i, line in enumerate(open(f, encoding="utf-8"), 1):
            if BANNED.search(line):
                hits.append(f"{f}:{i}")
    assert hits == []


def test_region_imports_only_gcode_judge():
    pat = re.compile(r"^\s*(?:from|import)\s+cvlab\.?(\w*)")
    for f in _files():
        if not f.endswith(".py"):
            continue
        for line in open(f, encoding="utf-8"):
            m = pat.match(line)
            if m:
                assert m.group(1) in ("gcode", "judge", "region"), (f, line)


def test_region_script_refuses_data_out(tmp_path):
    out = os.path.join(ROOT, "data", "_t4b_should_not_exist")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=os.path.join(ROOT, "src"))
    p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "region_mask.py"),
                        os.path.join(HAND, "H20_block.gcode"), "--summary", "--out", out],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert p.returncode != 0 and "오류" in p.stderr and not os.path.exists(out)
    p2 = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "region_mask.py"),
                         os.path.join(HAND, "H20_block.gcode"), "--summary", "--out", str(tmp_path), "--csv"],
                        capture_output=True, text=True, encoding="utf-8", env=env)
    assert p2.returncode == 0, p2.stderr
    line = [l for l in p2.stdout.splitlines() if l.startswith("REGION ")]
    assert len(line) == 1
    import json
    d = json.loads(line[0][7:])
    assert list(d) == ["file", "gcode_sha256", "layers", "grid_ny_nx", "passes", "band_mm", "step_mm",
                       "camera_side", "dof_mm", "dof_top_mm", "region_pct_total", "region_cells_cell02_total",
                       "depth_layers", "last_layer_depth_pct_object", "coverage_final_top_pct", "build_s"]
    assert os.path.exists(os.path.join(str(tmp_path), "H20_block_layers.csv"))
