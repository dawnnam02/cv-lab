"""스키마 추출·규칙표 시험 (SV4 · SV5 · SV13 · v1.0 재동기화)."""

import re

import pytest

from infra_helpers import ROOT, SPEC, SPEC_DIR, load_script, schema
from cvlab.io import rules as rl
from cvlab.io import spec_schema as ss


def test_infra_schema_sync():
    """명세 지문이 SOURCE.txt와 같아야 함. 다르면 extract_spec_schema.py로 다시 뽑을 것."""
    from cvlab.io.schema_files import source_sha
    assert ss.sha256_file(SPEC) == source_sha(SPEC_DIR)


def test_field_rows_match_spec():
    text = SPEC.read_text(encoding="utf-8")
    names = re.findall(r"^\| `((?:frame|pos|cal|ref|meta|blt|rep|truth)\.[a-z0-9_]+)` \|", text, re.M)
    fields, _, _ = schema()
    assert [f["field"] for f in fields] == names
    assert len(fields) == 254  # v1.0 동결 (T1 3차): 2차 245 + 새 필드 8, v1.2: + truth.material_offset_um
    assert sum(f["group"] == "truth" for f in fields) == 27
    assert not any(f["group"] == "blt" for f in fields)


def test_extract_is_deterministic():
    mod = load_script("extract_spec_schema")
    a = mod.build(SPEC, dict(ss.DEFAULT_EXCLUDED_GROUPS))
    b = mod.build(SPEC, dict(ss.DEFAULT_EXCLUDED_GROUPS))
    for k in ("fields_v1.0.csv", "rules_v1.0.csv"):
        assert a[k] == b[k]
        assert a[k] == (SPEC_DIR / k).read_bytes(), f"{k}가 저장본과 다름: 다시 뽑을 것"


def test_no_unclassified_sentence():
    fields = ss.extract(SPEC, ss.DEFAULT_EXCLUDED_GROUPS)
    assert rl.uncovered_sentences(fields, rl.build_rules(fields)) == []


def test_every_cover_snippet_is_used():
    """손 규칙의 covers 글자가 실제 명세 문장과 맞는지 (오타로 헛도는 연결 방지)."""
    fields = ss.extract(SPEC, ss.DEFAULT_EXCLUDED_GROUPS)
    sent = {}
    for f in fields:
        sent.setdefault(f["field"], []).extend(ss.split_sentences(f["rule_text"]))
    for r in rl.build_rules(fields):
        for c in filter(None, r["covers"].split(";;")):
            fld, snip = c.split(":", 1)
            assert any(snip in s for s in sent.get(fld, [])), (r["rule_id"], c)


def test_req_dtype_for_every_active_raw_field():
    fields, rules, _ = schema()
    ids = {r["rule_id"] for r in rules if r["status"] == "구현"}
    for f in fields:
        if f["group"] == "truth" or f["excluded"] == "true":
            continue
        assert f"DTYPE.{f['field']}" in ids
        if f["req"] in ("필수", "조건부"):
            assert f"REQ.{f['field']}" in ids
        if f["regex"]:
            assert f"REGEX.{f['field']}" in ids
        if f["enum"]:
            assert f"ENUM.{f['field']}" in ids
        if f["min"] or f["max"]:
            assert f"RANGE.{f['field']}" in ids


def test_hand_rules_are_implemented():
    """규칙표의 구현 손 규칙 ID가 검증기 코드에 있고, 코드가 내는 ID는 규칙표에 있음."""
    _, rules, _ = schema()
    src = (ROOT / "src" / "cvlab" / "io" / "validate.py").read_text(encoding="utf-8")
    emitted = set(re.findall(r'emit\(\s*"([A-Z][A-Z0-9-]+-\d+)"', src)) | set(re.findall(r'\("[a-z_]+", "([A-Z]-[A-Z]{3}-\d+)"\)', src))
    hand = {r["rule_id"] for r in rules if r["status"] == "구현" and r["kind"] not in ("REQ", "DTYPE", "REGEX", "ENUM", "RANGE")
            and not r["rule_id"].startswith("CROSS-EMPTY.")}
    assert hand - emitted == set(), sorted(hand - emitted)
    assert emitted - {r["rule_id"] for r in rules} == set()
    for r in rules:
        if r["status"] == "보류":
            assert r["reason"].strip(), r["rule_id"]


def test_parse_examples():
    assert ss.parse_range("0 < x ≤ 1e6 ÷ `meta.fps`. 스캔 안에서 모두 같음") == ("0", "<", "", "")
    assert ss.parse_range("abs(x) ≤ 2.0") == ("-2.0", "≤", "2.0", "≤")
    assert ss.parse_range("= 0.20 (D-05 고정)") == ("0.20", "=", "0.20", "=")
    assert ss.parse_range("−180 < x ≤ 180") == ("-180", "<", "180", "≤")
    assert ss.parse_range("1 ≤ x. kind = static_repeat면 x ≥ 100") == ("1", "≤", "", "")
    # v1.1: ref.gauge_height_mm 범위 문장이 따로 나뉨 → 특례 없이 뽑힘. v1.0 특례 (범위 뒤 쉼표 조건)는 지워서
    # 쉼표로 붙은 위 끝은 다른 필드 끝처럼 비움 (아래 끝만)
    assert ss.parse_range("필수. 0 ≤ x ≤ 60. x = 0은 GB-00 (베드 면)일 때만이고, GB-00이면 x = 0") == ("0", "≤", "60", "≤")
    assert ss.parse_range("필수. 0 ≤ x ≤ 60, x = 0은 GB-00 (베드 면)일 때만") == ("0", "≤", "", "")
    assert ss.parse_enum("값 ∈ {klipper, marlin} [대기: T14]. 관계") == ("klipper,marlin", True)
    assert ss.parse_regex("target = top_face면 정규식 `^S$`") == ""
    assert ss.parse_regex("정규식 `^a$` 또는 `^b$`. 끝") == "^a$||^b$"


def test_blt_excluded_by_spec():
    """SV13: 명세 6절이 blt를 제외로 표기 (D-14). 사유는 명세 절, blt 필드·규칙 0, 비활성은 D-21 대기 2개뿐."""
    text = SPEC.read_text(encoding="utf-8")
    assert ss.spec_excluded_groups(text) == {"blt": "명세 6절 제외 표기 (D-14)"}
    # 본문에 `pos.pass_idx` 같은 이름이 있어도 다른 묶음은 제외로 읽지 않음
    assert ss.spec_excluded_groups("제외 묶음: blt. `pos.x` `meta.y`\n") == {"blt": "명세 '제외 묶음' 표기"}
    _, rules, fc = schema()
    assert not any("blt." in r["fields"] for r in rules)
    assert [r["rule_id"] for r in rules if r["status"] == "비활성"] == []  # v1.0: D-21 채택으로 X4 · X7 기본 켬
    assert not any(k.startswith("probe_") for k in fc)
    assert "blt (명세 6절" in (SPEC_DIR / "SOURCE.txt").read_text(encoding="utf-8")


def test_sv13_held_rules():
    """SV13 보류 정리: 구현으로 옮긴 것 · 설명문으로 옮긴 것 · 그대로 보류."""
    _, rules, _ = schema()
    ids = {r["rule_id"]: r for r in rules}
    for gone in ("H-FMT-01", "H-CAL-15", "H-CAL-16", "H-MET-21", "H-MET-22", "H-MET-35", "H-MET-53"):
        assert gone not in ids, gone
    for kept in ("H-MET-23", "H-MET-28", "H-MET-31"):
        assert ids[kept]["status"] == "보류"
    for new in ("FILE-17", "FILE-18", "REGEX.meta.layer_macro_version", "CROSS-EMPTY.cal.image_file",
                "CROSS-EMPTY.cal.nozzle_touch_z_mm", "X-TRU-01"):
        assert ids[new]["status"] == "구현", new
    assert ids["ENUM.meta.firmware_name"]["severity"] == "ERROR"  # [대기: T14] 풀림
    for d21 in ("W-REF-11", "W-MET-56"):
        assert ids[d21]["severity"] == "WARN" and "D-21" in ids[d21]["reason"]
        assert ids[d21]["status"] == "구현"  # v1.0: D-21 채택 · 기본 켬


def test_v10_resync_rules():
    """v1.0 동결 (T1 3차) 재동기화: 새 필드 · 정규식 · 허용 값 · 범위 · 새 규칙 · 보류 정리."""
    fields, rules, _ = schema()
    fd = {f["field"]: f for f in fields}
    ids = {r["rule_id"]: r for r in rules}
    for new in ("cal.material", "cal.color", "ref.scan_pass_idx", "meta.blind", "truth.gauge_block_heights_mm",
                "truth.gauge_temp_params", "truth.scan_seeds", "truth.scan_factors"):
        assert new in fd, new
    assert fd["ref.ref_id"]["regex"] == r"^REF-[A-Z]{3}-\d{3,4}$"
    assert fd["meta.bed_ref_id"]["regex"] == r"^REF-BED-\d{3,4}$"
    assert fd["meta.paired_scan_id"]["regex"].endswith(r"(_p\d{2})?$")
    gb = r"^GB-\d{2}(\.\d{1,3})?(\+\d{2}(\.\d{1,3})?)*$||^FG-0\.[2345]0$"
    assert fd["cal.gauge_block_id"]["regex"] == gb and fd["ref.gauge_block_id"]["regex"] == gb
    assert "0.50" in fd["cal.gauge_nominal_mm"]["enum"].split(",")
    assert (fd["ref.gauge_height_mm"]["min"], fd["ref.gauge_height_mm"]["min_op"], fd["ref.gauge_height_mm"]["max"]) == ("0", "≤", "60")
    assert (fd["ref.layer_idx"]["min"], fd["ref.layer_idx"]["min_op"]) == ("-1", "≤")
    for rid in ("REQ.ref.scan_pass_idx", "CROSS-EMPTY.ref.scan_pass_idx", "REQ.cal.material", "CROSS-EMPTY.cal.color",
                "ENUM.meta.blind", "X-POS-15", "X-CAL-25", "X-CAL-26", "X-CAL-27", "X-REF-17", "X-REF-18", "X-REF-19", "X-REF-20",
                "X-REF-21", "X-REF-22", "X-REF-23", "X-REF-24", "X-MET-64", "X-MET-65", "X-MET-66", "X-MET-67",
                "X-TRU-02", "X-TRU-03", "X-TRU-04", "X-TRU-05"):
        assert ids[rid]["status"] == "구현", rid
    assert "H-CAL-24" not in ids  # 재료 교차 규칙 구현 (X-CAL-26 · 27)
    assert "CROSS-EMPTY.ref.layer_idx" not in ids  # bed_bare · feeler는 빈 칸이 아니라 -1 (X-REF-17)
    assert sum(r["status"] == "보류" for r in rules) == 9


def test_v11_resync_rules():
    """v1.1 (V-1) 재동기화: 필드 그대로, spec_version 허용 값, 두 단 비 경고 규칙, gauge_height_mm 범위 (특례 없이)."""
    fields, rules, _ = schema()
    fd = {f["field"]: f for f in fields}
    ids = {r["rule_id"]: r for r in rules}
    # 지문 · 허용 값 정확한 꼴은 v1.2 시험 (test_v12_resync_rules)이 봄. 여기서는 v1.1 값이 그대로 허용되는지만
    assert {"1.0", "1.1"} <= set(fd["meta.spec_version"]["enum"].split(",")) and ids["ENUM.meta.spec_version"]["severity"] == "ERROR"
    assert (fd["ref.gauge_height_mm"]["min"], fd["ref.gauge_height_mm"]["max"], fd["ref.gauge_height_mm"]["max_op"]) == ("0", "60", "≤")
    assert ids["W-REF-25"]["severity"] == "WARN" and ids["W-REF-25"]["status"] == "구현"
    assert "SWITCHABLE_OFF" in ids["W-REF-25"]["reason"]  # 끌 수 있는 목록에 넣지 않은 이유를 규칙표에 남김
    for rid in ("W-REF-11", "W-MET-56"):
        assert "검증기는 경고" in ids[rid]["reason"]
    assert "temp_c" in ids["X-TRU-02"]["message"]


def test_v12_resync_rules():
    """v1.2 (V-3) 재동기화 (V-4): 지문, 필드 254, _q 정규식 · 층 폴더, pos.pass_idx 범위, spec_version 허용 값, 새 손 규칙."""
    from cvlab.io import validate as vd
    fields, rules, _ = schema()
    fd = {f["field"]: f for f in fields}
    ids = {r["rule_id"]: r for r in rules}
    src = (SPEC_DIR / "SOURCE.txt").read_text(encoding="utf-8")
    assert "spec_sha256: bc63f84322c67b8aeb0b83539e1038015a976e2c47e160d8b21058f01aeea08f" in src
    assert "fields: 254 (" in src and "truth 27" in src
    q = r"^S\d{2}_r\d{2}(_L\d{3})?(_p\d{2})?(_q\d{2})?$"
    for f in ("frame.scan_id", "pos.scan_id", "meta.scan_id", "rep.scan_id"):
        assert fd[f]["regex"] == q and ids[f"REGEX.{f}"]["params"] == q, f
    # 짝 ID는 _q 꼬리 없음 (v1.1 그대로)
    assert fd["ref.scan_id"]["regex"] == r"^S\d{2}_r\d{2}(_L\d{3})?(_p\d{2})?$"
    assert fd["meta.paired_scan_id"]["regex"] == r"^S\d{2}_r\d{2}_L\d{3}(_p\d{2})?$"
    assert ids["RANGE.pos.pass_idx"]["params"] == "0 ≤ x ≤ 99"
    assert fd["meta.spec_version"]["enum"] == "1.0,1.1,1.2"
    assert "truth.material_offset_um" in fd and fd["truth.material_offset_um"]["dtype"] == "dict"
    for rid in ("X-MET-68", "X-REP-08", "X-REP-09", "X-TRU-06"):
        assert ids[rid]["status"] == "구현" and ids[rid]["severity"] == "ERROR", rid
    assert "공칭" in ids["X-REF-15"]["message"] and "0.02" in ids["X-REF-15"]["message"]
    assert "X-REF-15" in ids["X-REF-20"]["message"]  # C2는 X-REF-15에 맡김 (겹쳐 내지 않음)
    assert "d = 층 Z − h1 < 0" in ids["W-REF-25"]["message"]
    assert "_q" in ids["X-POS-12"]["message"] and "scan_start~scan_end" not in ids["X-POS-12"]["covers"]
    # 층 폴더 정규식 (명세 8절): post에는 _q 없음
    lay = vd.NAME_RES["layer"]
    for ok in ("L004", "L008_q01", "L008_p01_q01", "post", "post_p01"):
        assert lay.match(ok), ok
    for bad in ("post_q01", "post_p01_q01", "L008_q1", "L008_q01_p01"):
        assert not lay.match(bad), bad
    assert vd.gauge_nominal("GB-02+01.8+01.5") == 5.3 and vd.gauge_nominal("FG-0.50") == 0.5 and vd.gauge_nominal("GB-00") == 0.0
    assert (vd.C2_NOMINAL_TOL_MM, vd.C2_CAL_TOL_MM) == (0.0001, 0.02)


def test_bad_cell_count_fails(tmp_path):
    p = tmp_path / "spec.md"
    p.write_text("| `meta.x` | 뜻 | - | str | 필수 | 예 |\n", encoding="utf-8")
    with pytest.raises(ss.SpecError):
        ss.extract(p)
