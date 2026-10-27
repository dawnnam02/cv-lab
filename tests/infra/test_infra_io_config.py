"""읽기·쓰기 도우미 (SV9), 설정·재현성 (SV10), 환경 점검 (SV3) 시험."""

import json

import numpy as np
import pandas as pd
import pytest
import yaml

from infra_helpers import ROOT, disk_campaign, load_script, schema
from cvlab import config as cfgmod
from cvlab import repro
from cvlab.io import hashing, readers, writeonce
from cvlab.io import selftest as st


def test_read_scan_types(tmp_path):
    fields, _, fc = schema()
    sc = readers.read_scan(disk_campaign() / "sessions" / st.SESSION / st.SR / "L000", fields)
    fr, pos = sc["frames"], sc["pos"]
    assert str(fr["frame_idx"].dtype) == "Int64" and str(fr["laser_on"].dtype) == "boolean"
    assert str(fr["exposure_us"].dtype) == "float64" and fr["laser_on"].tolist()[:3] == [False, False, True]
    assert pos["t_ns"].max() > 2 ** 31  # int64 그대로
    assert pd.isna(pos["clock_offset_ns"][0]) and not pd.isna(pos["clock_offset_ns"][2])
    assert sc["meta"]["layer_time_s"] == 45.0 and sc["meta"]["paired_scan_id"] is None
    rows = [dict(st.normal_model()["sessions"][st.SESSION]["scans"][st.SR]["L000"]["frames"][0])]
    rows[0].update(saturated_px=None, sensor_temp_c=None)
    p = tmp_path / "frames_index.csv"
    p.write_bytes(st.csv_bytes(rows, fc["frames_index.csv"]))
    one = readers.read_csv_typed(p, fields, "frame")
    assert pd.isna(one["saturated_px"][0]) and np.isnan(one["sensor_temp_c"][0])


def test_write_once_refuses_existing(tmp_path):
    d = writeonce.create_dir_once(tmp_path / "raw" / "S01_r01" / "L000")
    with pytest.raises(FileExistsError):
        writeonce.create_dir_once(d)
    p = writeonce.write_json_once(d / "meta.json", {"a": "한글", "b": None})
    assert p.read_bytes() == '{\n  "a": "한글",\n  "b": null\n}\n'.encode("utf-8")
    with pytest.raises(FileExistsError):
        writeonce.write_json_once(d / "meta.json", {})
    c = writeonce.write_csv_once(d / "x.csv", [{"a": True, "b": None, "c": 0.02}], ["a", "b", "c"])
    assert c.read_bytes() == b"a,b,c\ntrue,,0.02\n"
    with pytest.raises(FileExistsError):
        writeonce.write_bytes_once(c, b"")


def test_sha256_helpers(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc")
    want = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert hashing.sha256_file(p) == hashing.sha256_bytes(b"abc") == want
    assert hashing.is_sha256_hex(want) and not hashing.is_sha256_hex(want.upper())
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "g.txt").write_bytes(b"")
    assert set(hashing.sha256_tree(tmp_path)) == {"f.bin", "d/g.txt"}


def test_load_config_default():
    cfg = cfgmod.load_config()
    assert cfg["run"]["random_seed"] == 42 and cfg["grid"]["res_mm"] == 0.02 and cfg["grid"]["frame"] == "G"


def _cfg_dir(tmp_path, extra=None):
    d = tmp_path / "config"
    d.mkdir()
    (d / "default.yaml").write_text((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    for name, text in (extra or {}).items():
        (d / name).write_text(text, encoding="utf-8")
    return d


def test_duplicate_top_key_is_error(tmp_path):
    d = _cfg_dir(tmp_path, {"judge.yaml": "judge: {T_mm: 0.2}\n", "zzz.yaml": "grid: {res_mm: 0.1, frame: G}\n"})
    with pytest.raises(cfgmod.ConfigError, match="둘 다"):
        cfgmod.load_config(d)


def test_unknown_key_in_owned_section_is_error(tmp_path):
    d = _cfg_dir(tmp_path)
    data = yaml.safe_load((d / "default.yaml").read_text(encoding="utf-8"))
    data["run"]["seed"] = 1
    (d / "default.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(cfgmod.ConfigError, match="모르는 키"):
        cfgmod.load_config(d)


def test_other_sections_are_not_checked_here(tmp_path):
    d = _cfg_dir(tmp_path, {"gcode.yaml": "gcode: {anything: 1}\n"})
    assert cfgmod.load_config(d)["gcode"] == {"anything": 1}


def test_unsafe_yaml_is_rejected(tmp_path):
    d = _cfg_dir(tmp_path, {"x.yaml": "x: !!python/object/apply:os.system ['echo hi']\n"})
    with pytest.raises(yaml.YAMLError):
        cfgmod.load_config(d)


def test_rng_seed_reproducible():
    a = repro.make_rng().random(5).tobytes()
    b = repro.make_rng(42).random(5).tobytes()
    c = repro.make_rng(7).random(5).tobytes()
    assert a == b != c


def test_manifest_same_bytes_and_no_overwrite(tmp_path):
    inp = tmp_path / "in.csv"
    inp.write_bytes(b"x\n1\n")
    cfg = cfgmod.load_config()
    kw = dict(command=["python", "x.py"], seed=42, inputs=[inp], config=cfg,
              timestamp="2026-11-20T14:20:00+09:00", git={"commit": "abc", "dirty": False})
    r1 = repro.start_run(tmp_path / "results", "run1", **kw)
    r2 = repro.start_run(tmp_path / "results", "run2", **kw)
    m1, m2 = (r / "manifest.json" for r in (r1, r2))
    assert m1.read_bytes().replace(b"run1", b"run2") == m2.read_bytes()
    man = json.loads(m1.read_text(encoding="utf-8"))
    assert {"timestamp", "git", "random_seed", "command", "python", "libraries", "inputs", "config"} <= set(man)
    assert man["timestamp"].endswith("+09:00") and man["inputs"][inp.as_posix()] == hashing.sha256_file(inp)
    with pytest.raises(FileExistsError):
        repro.start_run(tmp_path / "results", "run1", **kw)


def test_git_info_unknown_outside_repo(tmp_path):
    g = repro.git_info(tmp_path)
    assert g == {"commit": "unknown", "dirty": "unknown"}
    g2 = repro.git_info(ROOT)
    assert g2["commit"] == "unknown" or len(g2["commit"]) == 40


def test_check_env(tmp_path, capsys):
    mod = load_script("check_env")
    assert mod.main([]) == 0
    req = tmp_path / "req.txt"
    req.write_text("numpy==0.0.1\n", encoding="utf-8")
    assert mod.main(["--requirements", str(req)]) == 1
    assert "다름" in capsys.readouterr().out


def test_init_has_no_subpackage_import():
    src = (ROOT / "src" / "cvlab" / "__init__.py").read_text(encoding="utf-8")
    assert "__version__ = \"0.1.0\"" in src
    assert not [ln for ln in src.splitlines() if ln.strip().startswith(("import ", "from "))]
