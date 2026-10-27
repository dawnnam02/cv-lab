"""명세 필드표를 기계가 읽는 표로 뽑는다 (세부청사진 T6 §6.1).

손으로 옮겨 적지 않는다. `docs/하드웨어-데이터-명세.md`의 필드표 행을 정규식으로 찾고,
"검증 규칙" 칸에서 정규식·허용 값·수치 범위를 뽑는다. 뽑지 못한 문장은
`cvlab.io.rules`의 손 규칙(CROSS·FILE)이나 보류로 잇는다.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path

GROUPS = ("frame", "pos", "cal", "ref", "meta", "blt", "rep", "truth")

ROW_RE = re.compile(r"^\| `((?:frame|pos|cal|ref|meta|blt|rep|truth)\.[a-z0-9_]+)` \|", re.M)

# 묶음별 기본 파일 (명세 §0.2). 묶음 안에서 파일마다 열이 다르면 FILE_COLUMNS가 정한다.
GROUP_FILES = {
    "frame": "frames_index.csv",
    "pos": "position_log.csv",
    "cal": "cal_manifest.csv;cal_results.csv",
    "ref": "ref_index.csv",
    "meta": "meta.json",
    "blt": "",  # 명세 6절: 제외 (D-14), 파일 없음
    "rep": "design.csv;design_executed.csv",
    "truth": "truth.json",
}

# D-14 BLTouch 교차검증 제외. 명세 T1 2차 (2026-10-27)부터 6절 제목에 "제외 (D-14)"가 붙고 blt 필드표가 없다.
# 명세 표기가 있으면 `spec_excluded_groups()`의 사유 (명세 절)가 이 사유보다 먼저다.
DEFAULT_EXCLUDED_GROUPS = {"blt": "D-14 BLTouch 교차검증 제외 (팀장 지시 2026-10-27)"}

FIELD_COLUMNS = [
    "field", "group", "meaning", "unit", "dtype", "req", "example", "rule_text",
    "regex", "enum", "enum_pending", "min", "min_op", "max", "max_op",
    "file", "excluded", "excluded_reason", "order",
]

NUM = r"[−-]?\d+(?:\.\d+)?(?:e\d+)?|2\^63"


class SpecError(ValueError):
    """명세를 읽지 못함 (칸 수가 7이 아님 등)."""


def _num(s: str) -> str:
    """명세 숫자 표기를 CSV에 쓸 문자열로 (유니코드 빼기 → '-', 2^63 → 정수)."""
    s = s.replace("−", "-")
    if s == "2^63":
        return str(2 ** 63)
    return s


def split_sentences(rule_text: str) -> list[str]:
    """검증 규칙 칸을 문장으로 나눈다 ('. ' 기준, 소수점은 그대로)."""
    parts = re.split(r"\.\s+(?=\S)", rule_text.strip())
    out = []
    for p in parts:
        p = p.strip().rstrip(".").strip()
        if p:
            out.append(p)
    return out


def _strip_note(s: str) -> str:
    """괄호 주석 '(M54: …)' 등을 뗀다."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()


def parse_regex(rule_text: str) -> str:
    """'정규식 `…`' (+ '또는 `…`')을 뽑는다. 조건부 정규식('…면 정규식')은 뽑지 않는다."""
    pats: list[str] = []
    for m in re.finditer(r"(\S*)\s*정규식 ((?:`[^`]+`(?:\s*또는\s*)?)+)", rule_text):
        prefix = m.group(1)
        if prefix.endswith("면"):
            continue
        pats.extend(re.findall(r"`([^`]+)`", m.group(2)))
    return "||".join(pats)


def parse_enum(rule_text: str) -> tuple[str, bool]:
    """'값 ∈ {…}' 또는 '값 = v'를 뽑는다. 뒤에 '[대기: T14]'가 붙으면 대기 표시."""
    m = re.search(r"값 ∈ \{([^}]*)\}(\s*\[대기:[^\]]*\])?", rule_text)
    if m:
        vals = [v.strip() for v in m.group(1).split(",")]
        return ",".join(vals), bool(m.group(2))
    for sent in split_sentences(rule_text):
        m = re.match(r"^값 = (\S+)$", sent)
        if m:
            return m.group(1), False
    return "", False


def parse_range(rule_text: str) -> tuple[str, str, str, str]:
    """수치 범위를 뽑는다. 다른 필드를 가리키는 쪽 끝은 비운다 (CROSS 규칙 몫).

    조건이 붙은 문장('…면 x ≥ 100')은 뽑지 않는다.
    """
    for sent in split_sentences(rule_text):
        s = _strip_note(sent)
        if "면 " in s.split("x")[0] if "x" in s else False:
            continue
        m = re.match(rf"^({NUM}) (<|≤) x (<|≤) ({NUM})$", s)
        if m:
            return _num(m.group(1)), m.group(2), _num(m.group(4)), m.group(3)
        m = re.match(rf"^({NUM}) (<|≤) x(?: (<|≤) (.+))?$", s)
        if m:
            return _num(m.group(1)), m.group(2), "", ""
        m = re.match(rf"^x (≥|>) ({NUM})$", s)
        if m:
            return _num(m.group(2)), "≤" if m.group(1) == "≥" else "<", "", ""
        m = re.match(rf"^abs\(x\) ≤ ({NUM})$", s)
        if m:
            c = _num(m.group(1))
            return "-" + c, "≤", c, "≤"
        m = re.match(rf"^= ({NUM})$", s)
        if m:
            v = _num(m.group(1))
            return v, "=", v, "="
    return "", "", "", ""


def _file_columns(text: str) -> dict[str, list[str]]:
    """명세 본문에 적힌 파일별 열 구성 (cal_results.csv)."""
    out: dict[str, list[str]] = {}
    m = re.search(r"`calibration/<cal_id>/cal_results.csv`[^\n]*?열: ([^\n]*?)\. 단계", text)
    if m:
        out["cal_results.csv"] = [f.split(".", 1)[1] for f in re.findall(r"`(cal\.[a-z0-9_]+)`", m.group(1))]
    return out


def spec_excluded_groups(text: str) -> dict[str, str]:
    """명세가 묶음을 제외로 표기했는지 본다 (SV13).

    표기 형식: 절 제목 `## 6. … (blt) — 제외 (D-14)` 또는 본문 줄 `제외 묶음: blt.`
    사유는 명세 절 번호와 제목 괄호 안 결정 번호로 적는다.
    """
    out = {}
    listed: set[str] = set()
    for m in re.finditer(r"^제외 묶음: ([a-z]+(?:, [a-z]+)*)\.", text, re.M):
        listed.update(x.strip() for x in m.group(1).split(","))
    for g in GROUPS:
        h = re.search(rf"^## (\d+)\. [^\n]*\({g}\)[^\n]*제외(?: \(([^)]*)\))?", text, re.M)
        if h:
            out[g] = f"명세 {h.group(1)}절 제외 표기" + (f" ({h.group(2)})" if h.group(2) else "")
        elif g in listed:
            out[g] = "명세 '제외 묶음' 표기"
    return out


def extract(spec_path: str | Path, exclude_groups: dict[str, str] | None = None) -> list[dict]:
    """명세 파일에서 필드 행을 뽑는다. 칸 수가 7이 아니면 SpecError."""
    text = Path(spec_path).read_text(encoding="utf-8")
    excl = dict(spec_excluded_groups(text))
    if exclude_groups:
        for g, why in exclude_groups.items():
            excl.setdefault(g, why)
    rows: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        if not ROW_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) != 7:
            raise SpecError(f"칸 수 {len(cells)} (7이어야 함): {line[:80]}")
        name = cells[0].strip("`")
        if name in seen:
            raise SpecError(f"필드 이름 중복: {name}")
        seen.add(name)
        group = name.split(".", 1)[0]
        rule_text = cells[6]
        regex = parse_regex(rule_text)
        enum, pending = parse_enum(rule_text)
        mn, mnop, mx, mxop = parse_range(rule_text)
        rows.append({
            "field": name, "group": group, "meaning": cells[1], "unit": cells[2],
            "dtype": cells[3], "req": cells[4], "example": cells[5], "rule_text": rule_text,
            "regex": regex, "enum": enum, "enum_pending": "true" if pending else "false",
            "min": mn, "min_op": mnop, "max": mx, "max_op": mxop,
            "file": GROUP_FILES[group],
            "excluded": "true" if group in excl else "false",
            "excluded_reason": excl.get(group, ""),
            "order": str(len(rows)),
        })
    if not rows:
        raise SpecError("필드 행을 하나도 찾지 못함")
    return rows


def file_columns(spec_path: str | Path) -> dict[str, list[str]]:
    """파일별 열 목록 (접두어 뺀 이름, 필드표 순서). 고정 파일 이름은 명세 8절."""
    text = Path(spec_path).read_text(encoding="utf-8")
    fields = extract(spec_path)
    by_group: dict[str, list[str]] = {g: [] for g in GROUPS}
    for r in fields:
        by_group[r["group"]].append(r["field"].split(".", 1)[1])
    extra = _file_columns(text)
    out: dict[str, list[str]] = {}
    out["frames_index.csv"] = by_group["frame"]
    out["position_log.csv"] = by_group["pos"]
    out["ref_index.csv"] = by_group["ref"]
    out["design.csv"] = by_group["rep"]
    out["design_executed.csv"] = by_group["rep"]
    out["meta.json"] = by_group["meta"]
    res = extra.get("cal_results.csv", [])
    out["cal_results.csv"] = [c for c in by_group["cal"] if c in res]
    out["cal_manifest.csv"] = [c for c in by_group["cal"] if c not in ("reproj_rms_px", "plane_rms_um")]
    return out


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_csv_bytes(rows: list[dict], columns: list[str]) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in columns})
    return buf.getvalue().encode("utf-8")


def load_fields(csv_path: str | Path) -> list[dict]:
    with open(csv_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
