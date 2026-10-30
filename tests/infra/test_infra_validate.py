"""검증기 시험 (SV6 · SV7 · SV8 · v1.0 재동기화 · 팀장검증 5차 S-4 · S-5)."""

import json

import pytest

from infra_helpers import ROOT, disk_campaign, fake_repo, load_script, schema, selftest_report
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
    got = {h[1] for h in st.hand_faults()} | {w[1] for w in st.warn_tests()} | {s[1] for s in st.switch_tests()} \
        | {t[2] for t in st.truth_tests() if t[2]} | ({"W-REF-25"} if any(t[2] for t in st.ratio_tests()) else set())
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
    R = ["--repo-root", str(fake_repo())]
    assert cli.main([str(good), "--report", str(rep)] + R) == 0
    assert json.loads(rep.read_text(encoding="utf-8"))["summary"]["n_warn"] == 0
    meta = good / "sessions" / st.SESSION / st.SR / "L000" / "meta.json"
    orig = meta.read_bytes()
    try:
        meta.write_bytes(orig.replace(b'"tolerance_mm": 0.2,', b'"tolerance_mm": 0.25,'))
        assert cli.main([str(good), "--report", str(rep)] + R) == 1
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
        assert cli.main([str(good), "--report", str(rep), "--repo-root", str(fake_repo())]) == 0
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


def test_bltouch_folder_is_unknown():
    """SV13: 명세 8절에서 bltouch/ 폴더가 빠짐 (D-14) → 모르는 폴더 (FILE-01)."""
    fields, rules, fc = schema()
    files = st.serialize(st.normal_model(), fc)
    files[f"sessions/{st.SESSION}/bltouch/BLT-2026-11-20-A/probe_points.csv"] = b"session_id\nBLT-2026-11-20-A\n"
    got = {f.rule_id for f in Validator(fields, rules, fc, repo_exists=st.repo_exists).run(MemFS(files), st.CAMPAIGN)}
    assert got == {"FILE-01"}


def test_d21_switch_default_on():
    """D-21 채택: X4 (W-REF-11) · X7 (W-MET-56)은 기본 켬 (WARN), disabled_rules로 끄면 안 나옴. 그 밖 ID는 끌 수 없음."""
    fields, rules, fc = schema()
    for name, rid, fm in st.switch_tests():
        m = st.normal_model()
        fm(m)
        files = st.serialize(m, fc)
        on = [f for f in Validator(fields, rules, fc, repo_exists=st.repo_exists).run(MemFS(files), st.CAMPAIGN) if f.rule_id == rid]
        off = {f.rule_id for f in Validator(fields, rules, fc, disabled_rules={rid}, repo_exists=st.repo_exists).run(MemFS(files), st.CAMPAIGN)}
        assert on and all(f.severity == "WARN" for f in on) and rid not in off, name
    with pytest.raises(KeyError):
        Validator(fields, rules, fc, enabled_rules={"X-NOPE-01"})
    with pytest.raises(KeyError):
        Validator(fields, rules, fc, disabled_rules={"X-MET-25"})  # 판정 거부 X1 (ERROR)은 끌 수 없음
    from cvlab.config import load_config
    assert load_config()["validate"] == {"enable_rules": [], "disable_rules": []}


def test_truth_judgement_matches_pass_pct():
    fields, rules, fc = schema()
    v = Validator(fields, rules, fc)
    for name, obj, rid, ctx in st.truth_tests():
        got = {f.rule_id for f in v.check_truth(obj, ctx=ctx)}
        assert got == ({rid} if rid else set()), name
    # ctx 없이 (캠페인 사실 모름) 부른 옛 방식: judgement ⇔ pass_pct와 값 모양만 봄
    assert {f.rule_id for f in v.check_truth({"judgement": "pass", "pass_pct": 97.0})} == set()


def test_truth_ctx_from_run_matches_selftest():
    """run() 뒤 truth_ctx (T3가 check_truth에 쓰는 캠페인 사실)가 정상 표본 기대값과 같음."""
    fields, rules, fc = schema()
    v = Validator(fields, rules, fc, repo_exists=st.repo_exists)
    assert v.run(MemFS(st.serialize(st.normal_model(), fc)), st.CAMPAIGN) == []
    assert v.truth_ctx == st.truth_context()
    assert v.check_truth(st.normal_truth()) == []


def test_blind_campaign_is_clean():
    """meta.blind = true (평가용) 캠페인: sim_seed null · injected_factors [] · rep.noise_seed 빈 칸이면 ERROR 0."""
    fields, rules, fc = schema()
    m = st.normal_model()
    for sc in m["sessions"][st.SESSION]["scans"][st.SR].values():
        sc["meta"].update(blind=True, sim_seed=None, injected_factors=[])
    for rows in m["msa"]["MSA-01"].values():
        for r in rows:
            r["noise_seed"] = None
    v = Validator(fields, rules, fc, repo_exists=st.repo_exists)
    assert v.run(MemFS(st.serialize(m, fc)), st.CAMPAIGN) == []
    assert v.truth_ctx["blind"] is True
    assert v.check_truth(st.normal_truth(True), ctx=st.truth_context(True)) == []


def test_gauge_height_equal_layer_z_is_allowed():
    """C2 두 줄 (v1.2 4절): 공칭 ≤ 층 Z (허용차 0.0001, 같은 높이 허용), 교정 ≤ 층 Z + 0.02. 넘으면 X-REF-15만 (X-REF-20은 겹쳐 내지 않음)."""
    fields, rules, fc = schema()
    v = Validator(fields, rules, fc, repo_exists=st.repo_exists)

    def run(z):
        m = st.normal_model()
        st._scan(m)["meta"]["layer_z_mm"] = z  # L000 높은 단 FG-0.50: 공칭 0.5, 교정 0.5021
        return {f.rule_id for f in v.run(MemFS(st.serialize(m, fc)), st.CAMPAIGN)}
    for z in (st.FG5_H, 0.5, 0.4999):  # 교정 = Z · 공칭 = Z · 공칭 = Z + 0.0001 (교정은 Z + 0.0022 ≤ Z + 0.02)
        got = run(z)
        assert "X-REF-15" not in got and "X-REF-20" not in got and "W-REF-25" not in got, z
    for z in (0.4998, 0.49):  # 공칭 0.5 > Z + 0.0001
        got = run(z)
        assert "X-REF-15" in got and "X-REF-20" not in got, z
    # 정상 쪽 끝값 표본 (selftest.c2_tests): 오류 · 경고 0
    for name, fm in st.c2_tests():
        m = st.normal_model()
        fm(m)
        assert v.run(MemFS(st.serialize(m, fc)), st.CAMPAIGN) == [], name


def test_v11_two_step_ratio_rule():
    """명세 v1.1 4절 두 단 비 경고 (W-REF-25): 문턱 값, 양성 · 음성 · 경계, 두 단 규칙 실패 층 · 첫 줄 없는 층은 건너뜀, 끌 수 없음."""
    from cvlab.io import validate as vd
    lim = lambda u: vd.TWO_STEP_LIMIT_UM / (2 * vd.TWO_STEP_SIGMA_UM ** 2 + 2 * u ** 2) ** 0.5  # noqa: E731
    assert round(lim(2.0), 3) == 1.131 and round(lim(1.0), 3) == 1.569
    assert round(1.2 / 0.7, 3) == 1.714 and round((1.0 - 0.5021) / 0.5021, 3) == 0.992  # 6차 예 · B.4
    gap = st.GB_H - st.FG5_H
    assert (1.9912 - st.GB_H) / gap < lim(2.0) < (1.9914 - st.GB_H) / gap  # 경계 표본이 문턱 바로 아래 · 위
    fields, rules, fc = schema()
    v = Validator(fields, rules, fc, repo_exists=st.repo_exists)
    for name, fm, want in st.ratio_tests():
        m = st.normal_model()
        fm(m)
        out = v.run(MemFS(st.serialize(m, fc)), st.CAMPAIGN)
        w = [f for f in out if f.rule_id == "W-REF-25"]
        assert bool(w) == want and all(f.severity == "WARN" for f in w), name
        assert not [f for f in out if f.severity == "ERROR"], name

    def six(m):
        st.set_gauge_height(m, st.GB_ID, 1.2)
        st.set_gauge_height(m, st.FG5_ID, 0.5)
        st.set_layer_z(m, 1, 2.4)
    L001 = f"/{st.SR}/L001/"
    # 두 단 규칙 실패 층 (L001 두 단 중 하나 빠짐): X-REF-20만, 그 층 두 단 비는 안 봄 (post는 그대로 경고)
    m = st.normal_model()
    six(m)
    st._scan(m, "L001")["refs"].pop("REF-STG-003")
    out = v.run(MemFS(st.serialize(m, fc)), st.CAMPAIGN)
    assert "X-REF-20" in {f.rule_id for f in out}
    assert not [f for f in out if f.rule_id == "W-REF-25" and L001 in f.file]
    assert [f for f in out if f.rule_id == "W-REF-25" and f"/{st.SR}/post/" in f.file]
    # 첫 줄 스캔 없는 층 (L001 줄 0을 줄 2로): X-MET-55, 그 층 두 단 · 두 단 비는 안 봄
    m = st.normal_model()
    six(m)
    st._scan(m, "L001")["meta"].update(scan_pass_idx=2, scan_id=f"{st.SR}_L001_p02")
    out = v.run(MemFS(st.serialize(m, fc)), st.CAMPAIGN)
    assert "X-MET-55" in {f.rule_id for f in out}
    assert not [f for f in out if f.rule_id == "W-REF-25" and "L001" in f.file]
    # 끌 수 있는 목록에 없음 (D-21 X4 · X7만)
    assert "W-REF-25" not in vd.SWITCHABLE_OFF
    with pytest.raises(KeyError):
        Validator(fields, rules, fc, disabled_rules={"W-REF-25"})


def test_v11_spec_version_values():
    """명세 v1.2: meta.spec_version ∈ {1.0, 1.1, 1.2}. 옛 판 데이터도 같은 규칙으로 통과, 1.3은 ENUM."""
    fields, rules, fc = schema()
    v = Validator(fields, rules, fc, repo_exists=st.repo_exists)
    for val, want in (("1.2", set()), ("1.1", set()), ("1.0", set()), ("1.3", {"ENUM.meta.spec_version"})):
        m = st.normal_model()
        for sc in m["sessions"][st.SESSION]["scans"][st.SR].values():
            sc["meta"]["spec_version"] = val
        assert {f.rule_id for f in v.run(MemFS(st.serialize(m, fc)), st.CAMPAIGN)} == want, val


def test_v12_same_layer_repeat():
    """명세 v1.2 같은 층 반복 (_qNN): 정상 표본의 L001_q01은 위반 0, 첫 줄 · 줄 번호 · 개수에서 빠지고 같은 Z에는 듦."""
    fields, rules, fc = schema()
    v = Validator(fields, rules, fc, repo_exists=st.repo_exists)
    m = st.normal_model()
    q = st._scan(m, "L001_q01")
    assert q["meta"]["scan_id"] == f"{st.SR}_L001_q01" and q["meta"]["scan_pass_idx"] == 0 and q["refs"] == {}
    assert {r["pass_idx"] for r in q["pos"]} == {1}
    assert [r["scan_id"] for r in m["msa"]["MSA-01"]["design_executed.csv"]][:2] == [f"{st.SR}_L001", f"{st.SR}_L001_q01"]
    assert v.run(MemFS(st.serialize(m, fc)), st.CAMPAIGN) == []
    # _q 스캔을 빼면 (첫 측정만) 그대로 정상: 반복 없는 옛 판 꼴 (pos.pass_idx 모두 0)
    m2 = st.normal_model()
    m2["sessions"][st.SESSION]["scans"][st.SR].pop("L001_q01")
    m2["msa"]["MSA-01"]["design_executed.csv"][1]["scan_id"] = f"{st.SR}_L001_p01"
    assert v.run(MemFS(st.serialize(m2, fc)), st.CAMPAIGN) == []
    # 7차 V-4 고장 목록이 모두 v1.2 손 고장에 있음
    names = " | ".join(h[0] for h in st._v12_hand_faults())
    for key in ("층 Z + 0.0201", "공칭 h1 > 층 Z", "_q01 스캔인데 pos.pass_idx 0", "ref.scan_id가 _q 스캔", "post에 _q",
                "_q 스캔만"):
        assert key in names, key
    assert any(not want and "d < 0" in name for name, _f, want in st.ratio_tests())


def test_repo_root_default_is_cvlab_for_outside_data(tmp_path):
    """S-5: 데이터가 저장소 밖 (…/cvlab_data/raw/<id>)이어도 FILE-17 · 18을 건너뛰지 않음. 기본 뿌리 = cv-lab, 보고에 적음."""
    cli = load_script("validate_dataset")
    fields, rules, fc = schema()
    camp = tmp_path / "cvlab_data" / "raw" / st.CAMPAIGN
    st.write_tree(st.serialize(st.normal_model(), fc), camp)
    rep = tmp_path / "r.json"
    code = cli.main([str(camp), "--report", str(rep)])
    out = json.loads(rep.read_text(encoding="utf-8"))
    assert out["repo_root"] == str(ROOT) and out["repo_root_source"].startswith("기본")
    missing = {rel for rel in st.REPO_FILES if not (ROOT / rel).is_file()}
    got = {r["rule_id"] for r in out["findings"]}
    assert ("FILE-17" in got) == ("data/gcode/S01_user_part.gcode" in missing)
    assert ("FILE-18" in got) == ("data/gcode/S01_profile.ini" in missing)
    assert got <= {"FILE-17", "FILE-18"} and code == (1 if missing else 0)
    # --repo-root로 바꾸면 그 뿌리 기준 (표본 G코드가 있는 임시 저장소) → 통과
    assert cli.main([str(camp), "--report", str(rep), "--repo-root", str(fake_repo())]) == 0
    assert json.loads(rep.read_text(encoding="utf-8"))["repo_root_source"] == "--repo-root"
    assert cli.main([str(camp), "--enable-rule", "X-NOPE-01"]) == 2


def _cfg(tmp_path, validate_text: str):
    """default.yaml 사본의 validate 절만 바꾼 파일."""
    src = (ROOT / "config" / "default.yaml").read_text(encoding="utf-8")
    head = src.split("\nvalidate:")[0]
    p = tmp_path / "default.yaml"
    p.write_text(head + "\nvalidate:\n" + validate_text, encoding="utf-8")
    return p


def test_cli_config_typo_key_exit2(tmp_path, capsys):
    """S-4: validate 절 오타 키 (enable_rule) · 모르는 키는 조용히 넘기지 않고 종료 코드 2."""
    cli = load_script("validate_dataset")
    good = disk_campaign()
    p = _cfg(tmp_path, "  enable_rule: [W-REF-11]\n  disable_rules: []\n")
    assert cli.main([str(good), "--config", str(p), "--repo-root", str(fake_repo())]) == 2
    assert "모르는 키 ['enable_rule']" in capsys.readouterr().err
    p = _cfg(tmp_path, "  enable_rules: []\n  disable_rules: []\n  disable_rule: [W-MET-56]\n")
    assert cli.main([str(good), "--config", str(p), "--repo-root", str(fake_repo())]) == 2
    assert "disable_rule" in capsys.readouterr().err


def test_cli_config_disable_list_checked(tmp_path, capsys):
    """S-4: 끄는 목록 (disable_rules)도 목록 아님 · 끌 수 없는 ID면 종료 코드 2, 맞게 쓰면 그 규칙만 꺼짐."""
    cli = load_script("validate_dataset")
    fields, rules, fc = schema()
    R = ["--repo-root", str(fake_repo())]
    p = _cfg(tmp_path, "  enable_rules: []\n  disable_rules: W-MET-56\n")
    assert cli.main([str(disk_campaign()), "--config", str(p)] + R) == 2
    assert "list" in capsys.readouterr().err
    p = _cfg(tmp_path, "  enable_rules: []\n  disable_rules: [X-MET-25]\n")
    assert cli.main([str(disk_campaign()), "--config", str(p)] + R) == 2
    assert "끌 수 없는 규칙" in capsys.readouterr().err
    # X7 (층 L000 빠짐) 표본: 기본은 W-MET-56 WARN, 설정으로 끄면 안 나옴
    m = st.normal_model()
    st.switch_tests()[1][2](m)
    camp = tmp_path / "x7" / st.CAMPAIGN
    st.write_tree(st.serialize(m, fc), camp)
    rep = tmp_path / "r.json"
    cli.main([str(camp), "--report", str(rep)] + R)
    assert "W-MET-56" in {r["rule_id"] for r in json.loads(rep.read_text(encoding="utf-8"))["findings"]}
    p = _cfg(tmp_path, "  enable_rules: []\n  disable_rules: [W-MET-56]\n")
    cli.main([str(camp), "--report", str(rep), "--config", str(p)] + R)
    out = json.loads(rep.read_text(encoding="utf-8"))
    assert "W-MET-56" not in {r["rule_id"] for r in out["findings"]} and out["disabled_rules"] == ["W-MET-56"]


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
