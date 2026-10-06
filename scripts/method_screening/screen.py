"""screen.py — 측정 방법 후보 적합성 판정 (청사진 docs/0_방법탐색/README.md 실험 2·3·4).

실행 (cv-lab 폴더에서):
    python scripts/method_screening/screen.py --mc 50
    python scripts/method_screening/screen.py --mc 10 --spec scripts/method_screening/_sample_spec.csv

입력: docs/0_방법탐색/후보-사양_*.csv 전부 (청사진 4.1절 열). 없으면 _sample_spec.csv 로 시험 실행하고
      결과는 scripts/method_screening/_sample_out/ 에 쓴다 (실제 결과 폴더를 더럽히지 않게).
출력: docs/0_방법탐색/결과/ 규칙판정.csv · 시뮬레이션.csv · 점수.csv · 민감도.csv · 조합.csv · 그림 PNG

모듈: specs.py(입력) · rules.py(실험 2) · simulate.py(실험 3, 모델 가정 A1–A9) · scoring.py(실험 4)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rules  # noqa: E402
import scoring  # noqa: E402
import simulate as sim  # noqa: E402
from specs import find_spec_files, load_specs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))                  # cv-lab
SPEC_DIR = os.path.join(ROOT, "docs", "0_방법탐색")
OUT_DIR = os.path.join(SPEC_DIR, "결과")
SAMPLE_SPEC = os.path.join(HERE, "_sample_spec.csv")
SAMPLE_OUT = os.path.join(HERE, "_sample_out")
MANUAL_PATH = os.path.join(SPEC_DIR, "수동점수.csv")


def run_sims(df, n_mc, seed, log=print):
    sims, notes = {}, {}
    for i, row in df.iterrows():
        rid = row["id"]
        m, nt = sim.model_from_row(row)
        t0 = time.time()
        if m is None:
            sims[rid] = sim.unmeasurable_summary()
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    sims[rid], _ = sim.simulate(m, n_mc=n_mc, seed=seed * 1000 + i)
                except MemoryError:
                    sims[rid] = sim.unmeasurable_summary()
                    nt.append("메모리 부족 → 측정 불가")
            if m.measures_z and np.isfinite(m.depth):
                for key, name in (("step", "단차"), ("line", "선폭"), ("hole", "구멍지름"), ("pin", "위치")):
                    if not sim.depth_ok(m, key):
                        nt.append(f"{name} 패치 높이 {sim.PATCH_RELIEF[key]:g} µm > depth {m.depth:g} µm")
        notes[rid] = nt
        g = " ".join(f"{k}:{v['grade']}" for k, v in sims[rid].items())
        log(f"  {rid:6s} {time.time() - t0:6.1f} s  {g}")
    return sims, notes


def sim_table(df, sims, notes):
    recs = []
    for rid in df["id"]:
        for name, s in sims[rid].items():
            recs.append({"id": rid, "error_type": name, "group": s["group"], "truth_um": s["truth_um"],
                         "bias_um": s["bias_um"], "2sd_um": s["sd2_um"], "Q_um": s["Q_um"],
                         "lim_4to1_um": s["lim4_um"], "lim_10to1_um": s["lim10_um"], "판정": s["grade"],
                         "valid_frac": s["valid_frac"], "note": "; ".join(notes.get(rid, []))})
    return pd.DataFrame(recs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mc", type=int, default=50, help="몬테카를로 반복 수 (기본 50)")
    ap.add_argument("--spec", nargs="*", help="사양 CSV 경로 (생략하면 docs/0_방법탐색/후보-사양_*.csv)")
    ap.add_argument("--out", help="출력 폴더")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ids", nargs="*", help="이 id 만 계산")
    ap.add_argument("--manual", default=MANUAL_PATH, help="수동 점수 CSV (id,verify,novelty)")
    ap.add_argument("--no-fig", action="store_true")
    a = ap.parse_args(argv)

    paths = a.spec if a.spec else find_spec_files(SPEC_DIR)
    out = a.out
    if not paths:
        print(f"[경고] {SPEC_DIR} 에 후보-사양_*.csv 가 없어 시험용 {SAMPLE_SPEC} 로 실행합니다.")
        paths = [SAMPLE_SPEC]
    if out is None:
        out = SAMPLE_OUT if all(os.path.abspath(p) == SAMPLE_SPEC for p in paths) else OUT_DIR
    os.makedirs(out, exist_ok=True)

    df = load_specs(paths)
    if a.ids:
        df = df[df["id"].isin(a.ids)].reset_index(drop=True)
    print(f"사양 {len(df)}행 ({', '.join(os.path.basename(p) for p in paths)}) → {out}")

    # 실험 2 ---------------------------------------------------------------
    rt = rules.judge(df)
    rt.to_csv(os.path.join(out, "규칙판정.csv"), index=False, encoding="utf-8-sig")

    # 실험 3 ---------------------------------------------------------------
    t0 = time.time()
    print(f"시뮬레이션 (MC {a.mc}회)")
    sims, notes = run_sims(df, a.mc, a.seed)
    print(f"  합계 {time.time() - t0:.1f} s")
    st = sim_table(df, sims, notes)
    st.to_csv(os.path.join(out, "시뮬레이션.csv"), index=False, encoding="utf-8-sig")

    # 실험 4 ---------------------------------------------------------------
    manual = scoring.load_manual(a.manual)
    rows = {r["id"]: r.to_dict() for _, r in df.iterrows()}
    rtab = {r["id"]: r.to_dict() for _, r in rt.iterrows()}
    srecs, pool = [], {}
    for rid in df["id"]:
        ok1, n1, ratios = scoring.precision_pass(sims[rid])
        sc = scoring.score_items(rows[rid], sims[rid], manual.get(rid, {}))
        rok = bool(rtab[rid]["rule_ok"])
        rec = {"id": rid, "name": rows[rid]["name"], "pass_budget": rtab[rid]["pass_budget"],
               "pass_safety": rtab[rid]["pass_safety"], "pass_gcode": rtab[rid]["pass_gcode"],
               "pass_precision": ok1, "n_groups_4to1": n1, "pass_all": rok and ok1}
        for g, r in ratios.items():
            rec[f"ratio_{g}"] = r
        for k in scoring.WEIGHTS:
            rec[f"s_{k}"] = sc[k]
        rec["score"] = scoring.total(sc)
        srecs.append(rec)
        if rec["pass_all"]:
            pool[rid] = sc
    sdf = pd.DataFrame(srecs)
    sdf["rank_all"] = sdf["score"].rank(ascending=False, method="min").astype(int)
    sdf["rank_pass"] = np.nan
    m = sdf["pass_all"]
    sdf.loc[m, "rank_pass"] = sdf.loc[m, "score"].rank(ascending=False, method="min")
    sdf = sdf.sort_values(["pass_all", "score"], ascending=[False, False])
    sdf.to_csv(os.path.join(out, "점수.csv"), index=False, encoding="utf-8-sig")

    # 조합
    cand = [rid for rid in df["id"] if (not scoring.precision_pass(sims[rid])[0]) and rtab[rid]["rule_ok"]]
    combos = scoring.find_combos(cand, rows, sims, manual, rtab, rules.BUDGET_OWN_KRW, rules.BUDGET_OUTSOURCE_KRW)
    cdf = pd.DataFrame([{k: v for k, v in c.items() if k != "_scores"} for c in combos])
    if len(cdf):
        cdf["valid"] = cdf["pass_precision"] & (cdf["budget_ok"] != "탈락")
        cdf = cdf.sort_values(["valid", "score"], ascending=[False, False])
        for c in combos:
            if c["pass_precision"] and c["budget_ok"] != "탈락":
                pool[c["combo"]] = c["_scores"]
    else:
        cdf = pd.DataFrame(columns=["combo", "a", "b", "pass_precision", "budget_ok", "score", "valid"])
    cdf.to_csv(os.path.join(out, "조합.csv"), index=False, encoding="utf-8-sig")

    # 민감도: 통과 후보 + 유효 조합. 2개 미만이면 전체 단일 후보로 대신 (pool_basis 열에 기록)
    basis = "통과 후보+유효 조합"
    if len(pool) < 2:
        basis = "전체 후보(통과 후보 2개 미만)"
        pool = dict(pool)
        for rid in df["id"]:
            pool.setdefault(rid, scoring.score_items(rows[rid], sims[rid], manual.get(rid, {})))
    sens = scoring.sensitivity(pool)
    sens.insert(0, "pool_basis", basis)
    sens.index.name = "id"
    sens.to_csv(os.path.join(out, "민감도.csv"), encoding="utf-8-sig")

    if not a.no_fig:
        import figures
        figures.q_bars(st, os.path.join(out, "그림1_판정량.png"))
        figures.score_rank(sdf, cdf, os.path.join(out, "그림2_점수순위.png"))
        figures.sens_range(sens, os.path.join(out, "그림3_민감도.png"))

    # 요약 출력
    print("\n== 요약 ==")
    for rid in df["id"]:
        r = sdf[sdf["id"] == rid].iloc[0]
        g = ", ".join(f"{k} {sims[rid][k]['grade']} (Q={sims[rid][k]['Q_um']:.1f})"
                      for k in sim.TYPE_NAMES if k != "경계")
        print(f"{rid}: 예산 {r.pass_budget} / 안전 {r.pass_safety} / G코드 {r.pass_gcode} / "
              f"정밀도 {'통과' if r.pass_precision else '탈락'}({r.n_groups_4to1}종) / 점수 {r.score:.2f}")
        print(f"   {g}")
    nv = int(cdf["valid"].sum()) if len(cdf) else 0
    print(f"조합 {len(cdf)}개 중 유효 {nv}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
