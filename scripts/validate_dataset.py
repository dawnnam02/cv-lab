"""명세 검증기 CLI (세부청사진 T6 SV6).

    PYTHONPATH=src python scripts/validate_dataset.py data/raw/VC-2026-11-20-A [--report out.json]
    PYTHONPATH=src python scripts/validate_dataset.py --selftest [--report out.json]
    PYTHONPATH=src python scripts/validate_dataset.py data/raw/VC-… --enable-rule W-REF-11 --enable-rule W-MET-56   # D-21 대기 X4 · X7 켬

종료 코드: 0 통과 (ERROR 0) · 1 위반 · 2 사용법·스키마 오류.
`data/_truth` 아래 경로는 열지 않고 2로 끝낸다 (청사진 §5.2).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cvlab.io.validate import PathRefused, check_path_allowed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="캠페인 폴더가 하드웨어 데이터 명세를 지켰는지 검사")
    ap.add_argument("campaign", nargs="?", help="캠페인 폴더 (data/raw/<campaign_id>)")
    ap.add_argument("--report", help="보고 JSON 경로")
    ap.add_argument("--selftest", action="store_true", help="정상·경계·고장 표본 자체 시험")
    ap.add_argument("--enable-group", action="append", default=[], help="명세가 제외한 묶음을 켬 (지금은 없음: blt 필드표가 명세에서 빠짐)")
    ap.add_argument("--enable-rule", action="append", default=[],
                    help="기본으로 꺼 둔 규칙을 켬 (D-21 대기: W-REF-11 = X4, W-MET-56 = X7). config/default.yaml validate.enable_rules와 합침")
    ap.add_argument("--repo-root", help="meta.gcode_file 등 저장소 뿌리 기준 경로를 볼 저장소 뿌리. "
                                        "없으면 캠페인이 <뿌리>/data/raw/<campaign_id>일 때 그 뿌리, 아니면 검사 안 함")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    if not a.selftest and not a.campaign:
        print("캠페인 폴더를 주거나 --selftest를 쓸 것", file=sys.stderr)
        return 2
    if a.campaign:
        try:
            check_path_allowed(a.campaign)
        except PathRefused as e:
            print(f"거부: {e}", file=sys.stderr)
            return 2
    if a.report:
        try:
            check_path_allowed(a.report)
        except PathRefused as e:
            print(f"거부: {e}", file=sys.stderr)
            return 2

    from cvlab.io.schema_files import SchemaError, load
    from cvlab.io.validate import DirFS, Validator, findings_to_json, summarize
    try:
        fields, rules, file_cols = load()
    except SchemaError as e:
        print(f"스키마 오류: {e}", file=sys.stderr)
        return 2

    if a.selftest:
        from cvlab.io.selftest import run_selftest
        rep = run_selftest(fields, rules, file_cols)
        s = rep["summary"]
        miss = [r for r in rep["faults"] if not r["detected"]]
        for r in miss[:30]:
            print(f"놓침: [{r['kind']}] {r['name']} 기대 {r['expected']} 실제 {r['got']}")
        for f in rep["normal_error"][:20]:
            print(f"정상 표본 위반: {f.rule_id} {f.file} {f.row} {f.field} {f.value}")
        for x in rep["boundary_local"][:20]:
            print(f"경계 위반: {x}")
        for f in rep["boundary_combined_error"][:20]:
            print(f"경계 합본 위반: {f.rule_id} {f.file} {f.field} {f.value}")
        for w in rep["warns"]:
            if not w["detected"]:
                print(f"경고 안 나옴: {w['name']} 기대 {w['expected']}")
        print(f"자동 고장 {s['n_auto']} + 손 고장 {s['n_hand']} = {s['n_fault']}, 경계 끝값 {rep['boundary_n']}개 "
              f"(합본에 {rep['boundary_combined_fields']}개), 정상 경고 {len(rep['normal_warn'])}건, 경고 시험 {s['warn_n']}개")
        if a.report:
            out = {"summary": s, "line": rep["line"], "faults": rep["faults"], "warns": rep["warns"],
                   "boundary_cross": rep["boundary_cross"],
                   "normal_error": findings_to_json(rep["normal_error"]), "normal_warn": findings_to_json(rep["normal_warn"])}
            Path(a.report).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(rep["line"])
        ok = s["normal_error"] == 0 and s["boundary_error"] == 0 and s["n_detected"] == s["n_fault"] and s["warn_ok"] == s["warn_n"]
        return 0 if ok else 1

    root = Path(a.campaign)
    if not root.is_dir():
        print(f"폴더가 아님: {root}", file=sys.stderr)
        return 2
    try:
        # T6 소유 config/default.yaml의 validate 절만 읽음 (다른 담당 yaml이 바뀌어도 검증기가 멈추지 않게)
        import yaml
        with open(ROOT / "config" / "default.yaml", encoding="utf-8") as fh:
            cfg_rules = list(((yaml.safe_load(fh) or {}).get("validate") or {}).get("enable_rules") or [])
    except (OSError, yaml.YAMLError, AttributeError) as e:  # 설정 오류는 사용법 오류로
        print(f"설정 오류: {e}", file=sys.stderr)
        return 2
    repo = Path(a.repo_root) if a.repo_root else None
    if repo is None:
        p = root.resolve()
        if p.parent.name == "raw" and p.parent.parent.name == "data":
            repo = p.parent.parent.parent
    try:
        v = Validator(fields, rules, file_cols, set(a.enable_group), set(a.enable_rule) | set(cfg_rules), repo_root=repo)
    except KeyError as e:
        print(f"사용법 오류: {e}", file=sys.stderr)
        return 2
    findings = v.run(DirFS(root), root.name)
    s = summarize(findings)
    for f in findings[:50]:
        print(f"{f.severity} {f.rule_id} {f.file}:{f.row or ''} {f.field} {f.value!r} {f.message}")
    print(f"ERROR {s['n_error']} · WARN {s['n_warn']}")
    if a.report:
        Path(a.report).write_text(json.dumps({"campaign": root.name, "summary": s, "findings": findings_to_json(findings)},
                                             ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if s["n_error"] else 0


if __name__ == "__main__":
    sys.exit(main())
