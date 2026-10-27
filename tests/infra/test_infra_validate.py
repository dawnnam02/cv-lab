"""검증기 시험 (SV6 · SV7 · SV8)."""

import json

import pytest

from infra_helpers import disk_campaign, load_script, schema, selftest_report
from cvlab.io import selftest as st
from cvlab.io.validate import MemFS, PathRefused, Validator, check_path_allowed


def test_selftest_detects_all_faults():
    s = selftest_report()["summary"]
    fields, _, _ = schema()
    n_raw = sum(f["group"] != "truth" and f["excluded"] != "true" for f in fields)
    assert s["n_hand"] >= 30
    assert s["n_fault"] >= n_raw * 2 + 30
    missed = [r for r in selftest_report()["faults"] if not r["detected"]]
    assert missed == []
    assert s["rate"] == 100.0


def test_every_hand_rule_has_a_fault_sample():
    """구현한 손 규칙 (CROSS · FILE · CSV · JSON · LEAK · WARN)마다 고장·경고 표본이 하나 이상."""
    _, rules, _ = schema()
    got = {h[1] for h in st.hand_faults()} | {w[1] for w in st.warn_tests()}
    hand = [r["rule_id"] for r in rules if r["status"] == "구현" and r["kind"] not in ("REQ", "DTYPE", "REGEX", "ENUM", "RANGE")
            and not r["rule_id"].startswith("CROSS-EMPTY.")]
    assert [h for h in hand if h not in got] == []


def test_normal_and_boundary_have_no_error():
    rep = selftest_report()
    assert rep["summary"]["normal_error"] == 0, rep["normal_error"][:5]
    assert rep["summary"]["boundary_error"] == 0, rep["boundary_local"][:5]
    assert rep["boundary_combined_fields"] > 0


def test_warn_rules_fire():
    rep = selftest_report()
    assert rep["summary"]["warn_ok"] == rep["summary"]["warn_n"]
    assert rep["normal_warn"] == []


def test_cli_exit_codes(tmp_path):
    cli = load_script("validate_dataset")
    good = disk_campaign()
    rep = tmp_path / "r.json"
    assert cli.main([str(good), "--report", str(rep)]) == 0
    assert json.loads(rep.read_text(encoding="utf-8"))["summary"]["n_warn"] == 0
    meta = good / "sessions" / st.SESSION / st.SR / "L000" / "meta.json"
    orig = meta.read_bytes()
    try:
        meta.write_bytes(orig.replace(b'"tolerance_mm": 0.2,', b'"tolerance_mm": 0.25,'))
        assert cli.main([str(good), "--report", str(rep)]) == 1
    finally:
        meta.write_bytes(orig)
    rows = json.loads(rep.read_text(encoding="utf-8"))["findings"]
    assert rows and set(rows[0]) == {"rule_id", "severity", "file", "row", "field", "value", "message"}
    assert any(r["rule_id"] == "RANGE.meta.tolerance_mm" for r in rows)
    assert cli.main([str(tmp_path / "없는폴더")]) == 2
    assert cli.main([]) == 2


def test_json_indent4_is_warn_on_disk(tmp_path):
    """들여쓰기 4칸 meta.json은 JSON-06 WARN만 나오고 종료 코드 0 (팀장검증_3차 S-2 표본)."""
    cli = load_script("validate_dataset")
    good = disk_campaign()
    meta = good / "sessions" / st.SESSION / st.SR / "L000" / "meta.json"
    orig = meta.read_bytes()
    rep = tmp_path / "r.json"
    try:
        meta.write_bytes((json.dumps(json.loads(orig), indent=4, ensure_ascii=False) + "\n").encode("utf-8"))
        assert cli.main([str(good), "--report", str(rep)]) == 0
    finally:
        meta.write_bytes(orig)
    rows = json.loads(rep.read_text(encoding="utf-8"))["findings"]
    assert [(r["rule_id"], r["severity"], r["value"]) for r in rows] == [("JSON-06", "WARN", "4칸")]


def test_file_faults_on_disk():
    """FILE-06 · 07 · 10 고장을 디스크 폴더 (DirFS)로 돌림. 고친 파일은 되돌림 (팀장검증_3차 S-3)."""
    from cvlab.io.validate import DirFS
    fields, rules, fc = schema()
    good = disk_campaign()
    scan = good / "sessions" / st.SESSION / st.SR / "L000"
    png5, png4, meta = scan / "frames" / "000005.png", scan / "frames" / "000004.png", scan / "meta.json"

    def run():
        return {f.rule_id for f in Validator(fields, rules, fc).run(DirFS(good), st.CAMPAIGN) if f.severity == "ERROR"}

    def bad_hash(b):
        m = json.loads(b)
        k = sorted(m["files_sha256"])[0]
        m["files_sha256"][k] = "0" * 64
        return (json.dumps(m, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    cases = [
        ("FILE-06", png5, None),  # 프레임 파일 지움
        ("FILE-07", png4, lambda b: b[:-20] + bytes([b[-20] ^ 0xFF]) + b[-19:]),  # PNG 한 바이트
        ("FILE-10", meta, bad_hash),  # files_sha256 지문 하나 틀림
    ]
    for rid, path, edit in cases:
        orig = path.read_bytes()
        try:
            if edit is None:
                path.unlink()
            else:
                path.write_bytes(edit(orig))
            got = run()
        finally:
            path.write_bytes(orig)
        assert rid in got, (rid, sorted(got))
    assert run() == set()


def test_truth_path_refused_without_opening(tmp_path, monkeypatch):
    cli = load_script("validate_dataset")
    t = tmp_path / "data" / "_truth" / st.CAMPAIGN
    t.mkdir(parents=True)
    (t / "truth.json").write_text("{}", encoding="utf-8")
    opened = []
    import builtins
    real_open = builtins.open
    monkeypatch.setattr(builtins, "open", lambda f, *a, **k: (opened.append(str(f)), real_open(f, *a, **k))[1])
    assert cli.main([str(t)]) == 2
    assert not any("_truth" in o for o in opened)
    with pytest.raises(PathRefused):
        check_path_allowed("data\\_truth\\x")


def test_blt_enabled_checks_probe_files():
    """blt를 켜면 probe_points.csv 자동 규칙이 돈다 (기본은 꺼짐)."""
    fields, rules, fc = schema()
    from cvlab.io import rules as rl
    from cvlab.io import spec_schema as ss
    from infra_helpers import SPEC
    on = ss.extract(SPEC, {})
    on_rules = rl.build_rules(on)
    files = st.serialize(st.normal_model(), fc)
    cols = fc["probe_points.csv"]
    row = dict.fromkeys(cols, "")
    row.update(session_id="BLT-2026-11-20-A", t_ns="abc")
    files[f"sessions/{st.SESSION}/bltouch/BLT-2026-11-20-A/probe_points.csv"] = st.csv_bytes([row], cols)
    off = {f.rule_id for f in Validator(fields, rules, fc).run(MemFS(files), st.CAMPAIGN)}
    assert not any(r.startswith(("DTYPE.blt", "REQ.blt")) for r in off) and "FILE-01" not in off
    got = {f.rule_id for f in Validator(on, on_rules, fc, {"blt"}).run(MemFS(files), st.CAMPAIGN)}
    assert "DTYPE.blt.t_ns" in got and "REQ.blt.probe_model" in got


def test_csv_cache_does_not_hide_findings():
    """같은 검증기로 같은 고장 표본을 두 번 돌려도 결과가 같음."""
    fields, rules, fc = schema()
    v = Validator(fields, rules, fc)
    m = st.normal_model()
    st._scan(m)["frames"][3]["exposure_us"] = 801.0
    files = st.serialize(m, fc)
    a = [(f.rule_id, f.row) for f in v.run(MemFS(files), st.CAMPAIGN)]
    b = [(f.rule_id, f.row) for f in v.run(MemFS(files), st.CAMPAIGN)]
    assert a == b and ("X-FRM-09", None) in a
