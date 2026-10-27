"""명세 필드표 → config/spec/fields_v1.0.csv · rules_v1.0.csv · SOURCE.txt (세부청사진 T6 SV4 · SV5).

손으로 옮겨 적지 않는다. 명세가 바뀌면 이 스크립트를 다시 돌린다.
fields·rules CSV는 두 번 돌려도 같은 바이트다. SOURCE.txt는 뽑은 시각 줄만 달라진다.

    PYTHONPATH=src python scripts/extract_spec_schema.py
    PYTHONPATH=src python scripts/extract_spec_schema.py --exclude-groups ""      # 명령줄 기본 제외 없음 (명세 표기는 그대로)
    PYTHONPATH=src python scripts/extract_spec_schema.py --check                  # 다시 뽑은 결과와 파일이 같은지만 봄
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cvlab.io import spec_schema as ss  # noqa: E402
from cvlab.io import rules as rl  # noqa: E402

SPEC = ROOT / "docs" / "하드웨어-데이터-명세.md"
OUT = ROOT / "config" / "spec"
KST = timezone(timedelta(hours=9))


def build(spec: Path, exclude: dict[str, str]) -> dict[str, bytes]:
    fields = ss.extract(spec, exclude)
    rules = rl.build_rules(fields)
    sha = ss.sha256_file(spec)
    now = datetime.now(KST).isoformat(timespec="seconds")
    n = {g: sum(f["group"] == g for f in fields) for g in ss.GROUPS}
    # 명세 표기 사유가 명령줄 기본 사유보다 먼저 (SV13)
    excl = dict(ss.spec_excluded_groups(spec.read_text(encoding="utf-8")))
    for g, why in exclude.items():
        excl.setdefault(g, why)
    st = {s: sum(r["status"] == s for r in rules) for s in ("구현", "비활성", "보류")}
    source = "\n".join([
        f"spec_file: docs/{spec.name}",
        f"spec_sha256: {sha}",
        f"extracted_at: {now}",
        f"fields: {len(fields)} ({', '.join(f'{g} {n[g]}' for g in ss.GROUPS)})",
        f"excluded_groups: {', '.join(f'{g} ({why})' for g, why in sorted(excl.items())) or '-'}",
        f"rules: {len(rules)} (구현 {st['구현']}, 비활성 {st['비활성']}, 보류 {st['보류']})",
        "extractor: scripts/extract_spec_schema.py (cvlab.io.spec_schema, cvlab.io.rules)",
        "",
    ])
    return {
        "fields_v1.0.csv": ss.to_csv_bytes(fields, ss.FIELD_COLUMNS),
        "rules_v1.0.csv": ss.to_csv_bytes(rules, rl.RULE_COLUMNS),
        "SOURCE.txt": source.encode("utf-8"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--exclude-groups", default=",".join(ss.DEFAULT_EXCLUDED_GROUPS),
                    help="묶음 단위로 끌 묶음 (쉼표). 기본 blt (D-14). 빈 글자면 모두 켬")
    ap.add_argument("--check", action="store_true", help="쓰지 않고 기존 파일과 같은지만 봄 (다르면 1)")
    a = ap.parse_args(argv)
    groups = [g.strip() for g in a.exclude_groups.split(",") if g.strip()]
    bad = [g for g in groups if g not in ss.GROUPS]
    if bad:
        print(f"모르는 묶음: {bad}", file=sys.stderr)
        return 2
    exclude = {g: ss.DEFAULT_EXCLUDED_GROUPS.get(g, "명령줄 --exclude-groups") for g in groups}
    try:
        files = build(Path(a.spec), exclude)
    except ss.SpecError as e:
        print(f"추출 실패: {e}", file=sys.stderr)
        return 2
    fields = ss.extract(Path(a.spec), exclude)
    unc = rl.uncovered_sentences(fields, rl.build_rules(fields))
    if unc:
        print(f"미분류 문장 {len(unc)}개 (rules.py에 손 규칙·보류·설명문을 더할 것):", file=sys.stderr)
        for f, s in unc:
            print(f"  {f}: {s}", file=sys.stderr)
    out = Path(a.out)
    if a.check:
        def strip_time(b: bytes) -> bytes:
            return b"\n".join(x for x in b.split(b"\n") if not x.startswith(b"extracted_at:"))
        diff = [k for k, v in files.items()
                if not (out / k).exists() or strip_time((out / k).read_bytes()) != strip_time(v)]
        print("같음" if not diff else f"다름: {diff}")
        return 1 if diff else 0
    out.mkdir(parents=True, exist_ok=True)
    for k, v in files.items():
        (out / k).write_bytes(v)
    print(files["SOURCE.txt"].decode("utf-8").strip())
    print(f"미분류 문장: {len(unc)}")
    return 1 if unc else 0


if __name__ == "__main__":
    sys.exit(main())
