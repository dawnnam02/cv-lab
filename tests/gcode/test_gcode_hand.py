"""GC11 손 G코드와 기대값.csv · GC12 사용자가 고른 후보 (없으면 skip)."""
import csv
import glob
import os

import pytest

from cvlab.gcode import parse_file
from gcode_helpers import HAND, ROOT, SAMPLES, evaluate, expected_rows

ROWS = expected_rows()


def test_hand_files_at_least_18_and_all_have_expectations():
    files = sorted(glob.glob(os.path.join(HAND, "H*.gcode")))
    assert len(files) >= 18
    keys = {r["파일"] for r in ROWS}
    assert all(os.path.basename(f).split("_")[0] in keys for f in files)
    assert all(r["근거식"].strip() for r in ROWS)


def test_expected_csv_header_fixed():
    with open(os.path.join(HAND, "기대값.csv"), encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == ["파일", "항목", "기대값", "허용차", "근거식"]


def test_mimic_files_marked():
    for f in glob.glob(os.path.join(HAND, "*_mimic.gcode")):
        first = open(f, encoding="utf-8").readline()
        assert "실제 슬라이서 출력 아님" in first, f


@pytest.mark.parametrize("row", ROWS, ids=[f"{r['파일']}-{r['항목']}" for r in ROWS])
def test_expected_value(row):
    actual, ok = evaluate(row)
    assert ok, f"{row['파일']} {row['항목']}: 기대 {row['기대값']} ± {row['허용차']}, 실제 {actual}"


def _picked():
    out = []
    for sub in ("public", "_local"):
        for ext in ("*.gcode", "*.gco"):
            out += glob.glob(os.path.join(SAMPLES, sub, ext))
    return sorted(out)


def test_picked_samples_pass_checks():
    files = _picked()
    if not files:
        pytest.skip("사용자 선택 대기")
    for f in files:
        r = parse_file(f)
        s = r.summary()
        assert s["unknown"] == 0 and s["checksum_bad"] == 0, f
        assert s["layers_comment"] == s["layers_z"], f
        if s["layers_declared"] is not None:
            assert s["layers_declared"] == s["layers_z"], f
        assert s["z_max_diff_mm"] is None or s["z_max_diff_mm"] <= 1e-4, f
        assert s["filament_diff_pct"] is None or abs(s["filament_diff_pct"]) <= 1.0, f


def test_manifest_matches_local_copies():
    """MANIFEST.csv (커밋 대상)는 늘 있음. 복사본이 있는 행만 지문 대조 (클론에는 _local 이 없음)."""
    import hashlib
    m = os.path.join(SAMPLES, "MANIFEST.csv")
    if not os.path.exists(m):
        pytest.skip("MANIFEST 없음 (사용자 선택 대기)")
    with open(m, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    need = ["파일", "sha256", "원래경로", "출처URL", "라이선스", "고른날짜", "위치"]
    assert rows and all(r[k].strip() for r in rows for k in need)
    assert not [r for r in rows if r["위치"] == "public" and "미상" in r["라이선스"]]
    for r in rows:
        cp = os.path.join(SAMPLES, r["위치"], r["파일"])
        if os.path.exists(cp):
            assert hashlib.sha256(open(cp, "rb").read()).hexdigest() == r["sha256"], cp


def _script():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gcode_reference_script", os.path.join(ROOT, "scripts", "gcode_reference.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_summary_and_outputs(tmp_path, capsys):
    f = os.path.join(HAND, "H20_block.gcode")
    rc = _script().main([f, "--summary", "--out", str(tmp_path), "--csv", "--npz"])
    out = capsys.readouterr().out
    assert rc == 0
    assert any(l.startswith("SUMMARY {") for l in out.splitlines())
    assert list(tmp_path.glob("*_layers.csv")) and list(tmp_path.glob("*_ref.npz"))


def test_script_refuses_allow_without_reason(tmp_path, capsys):
    rc = _script().main([os.path.join(HAND, "H16_unknown_cmd.gcode"), "--summary", "--allow", "M999"])
    assert rc == 2
    rc = _script().main([os.path.join(HAND, "H16_unknown_cmd.gcode"), "--summary", "--allow", "M999=시험"])
    assert rc == 0 and '"M999": 1' in capsys.readouterr().out
