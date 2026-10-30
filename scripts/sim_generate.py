# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""가상 센서 시뮬레이터 실행기 (T3).

S1–S2 범위:
  참값만 SM2 대조:  --truth-only --base reference --scenarios all [--out-root DIR] [--with-nuisance --seed N]
  캠페인 (뼈대):    --campaign config/sim/campaign_small.yaml --seed N [--workers W] [--out-root DIR]
  평가용 경로:      --eval --campaign ... (시드는 환경 변수 CVLAB_EVAL_SEED에서만, 없으면 오류)

요약 줄: `SIM {json}` (키 고정: campaign, seed_tag, specimens, layers, scans, frames, bytes_raw, bytes_disk,
runtime_s, faults, blind), SM2 대조는 `SM2 {"rows", "match", "mismatch", ...}`.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cvlab.sim.campaign import compare_sm2, expected_rows, factor_switches, run_shape_campaign, truth_all  # noqa: E402
from cvlab.sim.seeds import check_seed, eval_seed_from_env  # noqa: E402
from cvlab.sim.simconfig import ROOT, data_roots, load_campaign, load_default, load_factors  # noqa: E402

SIM_KEYS = ["campaign", "seed_tag", "specimens", "layers", "scans", "frames", "bytes_raw", "bytes_disk",
            "runtime_s", "faults", "blind"]


def sim_line(d: dict) -> str:
    return "SIM " + json.dumps({k: d.get(k) for k in SIM_KEYS}, ensure_ascii=False)


def run_truth_only(a, cfg) -> int:
    t0 = time.time()
    if a.scenarios != "all":
        raise SystemExit("S2: --scenarios all만 지원")
    only = a.specimens.split(",") if a.specimens else None
    truth = truth_all(cfg, base=a.base, factors=None, seed=None, workers=a.workers, only=only)
    exp = [e for e in expected_rows() if only is None or e["specimen"] in only]
    rep = compare_sm2(truth, exp) if a.base == "reference" else None
    if a.out_root:
        out = Path(a.out_root)
        out.mkdir(parents=True, exist_ok=True)
        with open(out / f"sm2_truth_{a.base}.csv", "w", encoding="utf-8", newline="\n") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["scenario", "specimen", "base", "n_layers", "n_region_cells", "truth_pass_pct", "truth_judgement"])
            for t in truth:
                w.writerow([t["scenario"], t["specimen"], t["base"], t["n_layers"], t["n_region_cells"],
                            f"{t['pass_pct']:.4f}", t["judgement"]])
    print(sim_line(dict(campaign="truth-only", seed_tag=None, specimens=sorted({t["specimen"] for t in truth}),
                        layers=sum({t["specimen"]: t["n_layers"] for t in truth}.values()), scans=0, frames=0, bytes_raw=0, bytes_disk=0,
                        runtime_s=round(time.time() - t0, 1), faults=[], blind=False)))
    if rep is not None:
        print("SM2 " + json.dumps(rep, ensure_ascii=False))
    if a.with_nuisance:
        if a.seed is None:
            raise SystemExit("--with-nuisance는 --seed가 필요함")
        f = factor_switches(load_factors())
        tn = truth_all(cfg, base=a.base, factors=f, seed=check_seed(a.seed), workers=a.workers, only=only)
        by = {(t["scenario"], t["specimen"]): t for t in truth}
        flips = [[t["scenario"], t["specimen"], by[(t["scenario"], t["specimen"])]["judgement"], t["judgement"]]
                 for t in tn if by[(t["scenario"], t["specimen"])]["judgement"] != t["judgement"]]
        dmax = max(abs(t["pass_pct"] - by[(t["scenario"], t["specimen"])]["pass_pct"]) for t in tn)
        print("SM2N " + json.dumps(dict(rows=len(tn), flips=flips, max_pass_pct_change=round(dmax, 4),
                                        factors=sorted(k for k, v in f.items() if v)), ensure_ascii=False))
    return 0 if rep is None or rep["match"] == rep["rows"] else 1


def run_campaign(a, cfg) -> int:
    t0 = time.time()
    if a.eval:
        seed = eval_seed_from_env()
    else:
        if a.seed is None:
            raise SystemExit("--seed가 필요함 (개발용). 평가용은 --eval + 환경 변수")
        seed = check_seed(a.seed)
    camp = load_campaign(a.campaign)
    raw_root, truth_root = data_roots(cfg, a.out_root)
    if a.shape_only:
        s = run_shape_campaign(cfg, camp, seed, truth_root, workers=a.workers, blind=a.eval)
        s["runtime_s"] = round(time.time() - t0, 1)
        print(sim_line(s))
        return 0
    from cvlab.sim.writer import Writer
    s = Writer(cfg, camp, seed, raw_root, truth_root, blind=a.eval).run()
    s["runtime_s"] = round(time.time() - t0, 1)
    print(sim_line(s))
    rep, ctx = validate_raw(Path(s["raw"]))
    print("VALID " + json.dumps(rep, ensure_ascii=False))
    print("TRUTH " + json.dumps(check_truth_file(Path(s["truth"]), ctx), ensure_ascii=False))
    return 0


def _validator():
    from cvlab.config import load_owned
    from cvlab.io.schema_files import load
    from cvlab.io.validate import Validator
    from cvlab.sim.specdefs import SCHEMA_CHECK_SPEC
    fields, rules, file_cols = load(check_spec=SCHEMA_CHECK_SPEC)   # V-4 (11-07) 전: v1.1 스키마로 봄
    vcfg = load_owned(str(ROOT / "config" / "default.yaml"))["validate"]
    return Validator(fields, rules, file_cols, set(), set(vcfg["enable_rules"]), repo_root=ROOT,
                     disabled_rules=set(vcfg["disable_rules"]))


def validate_raw(raw_dir: Path) -> tuple[dict, dict]:
    """T6 검증기 (cvlab.io)로 raw를 봄. 돌려줌: (요약 · 규칙별 개수, 참값 검사용 캠페인 사실)."""
    from collections import Counter
    from cvlab.io.validate import DirFS, summarize
    v = _validator()
    f = v.run(DirFS(raw_dir), raw_dir.name)
    s = summarize(f)
    by = Counter(f"{x.severity} {x.rule_id}" for x in f)
    return {"error": s["n_error"], "warn": s["n_warn"], "rules": dict(sorted(by.items()))}, v.truth_ctx


def check_truth_file(truth_dir: Path, ctx: dict | None) -> dict:
    v = _validator()
    recs = json.loads((truth_dir / "truth.json").read_text(encoding="utf-8"))
    hm = sorted(p.name for p in (truth_dir / "heightmaps").glob("*.npy"))
    ok = all((r["judgement"] == "pass") == (r["pass_pct"] >= 95) for r in recs)
    files_ok = all((truth_dir / r["heightmap_file"]).is_file() for r in recs)
    try:
        f = v.check_truth(recs, "truth.json", ctx=ctx)
    except KeyError as e:  # 검증기 코드와 규칙표가 어긋난 상태 (V-4 재동기화 중)
        return {"records": len(recs), "findings": None, "error": f"검증기 규칙표 어긋남: {e}", "heightmaps": len(hm),
                "heightmap_files_ok": files_ok, "judgement_rule_ok": ok}
    return {"records": len(recs), "findings": len(f), "rules": sorted({x.rule_id for x in f}),
            "heightmaps": len(hm), "heightmap_files_ok": files_ok, "judgement_rule_ok": ok}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--truth-only", action="store_true")
    ap.add_argument("--base", default="reference", choices=["reference", "deposition"])
    ap.add_argument("--scenarios", default="all")
    ap.add_argument("--specimens", default=None, help="쉼표로 구분한 시편 이름 (기본 전부)")
    ap.add_argument("--with-nuisance", action="store_true", help="열 · Z축 스위치를 켠 참 판정과 비교 (참고)")
    ap.add_argument("--campaign", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--shape-only", action="store_true", help="참 높이맵 · 계획만 (S2 뼈대)")
    ap.add_argument("--check-truth", default=None, help="캠페인 ID: 참값 검사만 (팀장 명령 ④)")
    ap.add_argument("--truth-root", default=None)
    a = ap.parse_args(argv)
    cfg = load_default()
    if a.workers is None:
        a.workers = int(cfg["run"]["workers"])
    if a.truth_only:
        return run_truth_only(a, cfg)
    if a.check_truth:
        raw_root, truth_root = data_roots(cfg, a.out_root)
        troot = Path(a.truth_root) if a.truth_root else truth_root
        _, ctx = validate_raw(raw_root / a.check_truth) if (raw_root / a.check_truth).is_dir() else (None, None)
        print("TRUTH " + json.dumps(check_truth_file(troot / a.check_truth, ctx), ensure_ascii=False))
        return 0
    if a.campaign:
        try:
            return run_campaign(a, cfg)
        except (RuntimeError, ValueError, FileExistsError) as e:
            print(f"오류: {e}", file=sys.stderr)
            return 2
    ap.error("--truth-only 또는 --campaign 중 하나")
    return 2


if __name__ == "__main__":
    sys.exit(main())
