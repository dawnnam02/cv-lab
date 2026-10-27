"""스키마 추출·규칙표 시험 (SV4 · SV5 · SV13)."""

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
    assert len(fields) == 248
    assert sum(f["group"] == "truth" for f in fields) == 22


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
    assert ss.parse_enum("값 ∈ {klipper, marlin} [대기: T14]. 관계") == ("klipper,marlin", True)
    assert ss.parse_regex("target = top_face면 정규식 `^S$`") == ""
    assert ss.parse_regex("정규식 `^a$` 또는 `^b$`. 끝") == "^a$||^b$"


def test_blt_group_switch():
    """blt는 기본으로 꺼짐 (D-14). 끄지 않고 뽑으면 blt 자동 규칙이 구현 상태가 됨."""
    _, rules, _ = schema()
    blt = [r for r in rules if r["fields"].startswith("blt.")]
    assert blt and all(r["status"] == "비활성" for r in blt)
    assert not any(r["kind"] == "CROSS" and "blt." in r["fields"] and not r["rule_id"].startswith("CROSS-EMPTY") for r in rules)
    on = ss.extract(SPEC, {})
    assert all(f["excluded"] == "false" for f in on)
    on_rules = rl.build_rules(on)
    assert any(r["rule_id"] == "DTYPE.blt.t_ns" and r["status"] == "구현" for r in on_rules)


def test_bad_cell_count_fails(tmp_path):
    p = tmp_path / "spec.md"
    p.write_text("| `meta.x` | 뜻 | - | str | 필수 | 예 |\n", encoding="utf-8")
    with pytest.raises(ss.SpecError):
        ss.extract(p)
