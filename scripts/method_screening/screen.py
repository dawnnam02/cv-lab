"""screen.py — 측정 방법 후보 적합성 판정 (청사진 docs/0_방법탐색/README.md 실험 2·3·4).

실행 (cv-lab 폴더에서):
    python scripts/method_screening/screen.py --mc 50                 # 병렬 (기본 workers = CPU 수 − 1)
    python scripts/method_screening/screen.py --mc 50 --workers 1     # 순차 (결과는 병렬과 같음)
    python scripts/method_screening/screen.py --mc 10 --spec scripts/method_screening/_sample_spec.csv

입력: docs/0_방법탐색/후보-사양_*.csv 전부 (1차 A–D + 2차 E1–E10, 청사진 4.1절 열 + 8.1절 mode·cal_class).
      없으면 _sample_spec.csv 로 시험 실행하고 결과는 scripts/method_screening/_sample_out/ 에 쓴다.
출력: docs/0_방법탐색/결과/ 규칙판정.csv · 시뮬레이션.csv · 점수.csv · 민감도.csv · 조합.csv · 보수100_신규통과.csv
      · 입력경고.txt · 그림1_판정량.png (+ 그룹별 그림1_판정량_높이/윤곽/치수.png) · 그림2_점수순위.png (상위 30) · 그림3_민감도.png
난수: 후보마다 시드 = seed × 1000 + (id 숫자 − 1). 같은 시드면 병렬·순차, 후보 구성과 무관하게 같은 결과.

모듈: specs.py(입력) · rules.py(실험 2) · simulate.py(실험 3, 모델 가정 A1–A9) · scoring.py(실험 4)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import warnings
import zlib

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


SC_OPT, SC_C500, SC_C100 = "낙관", "보수-500", "보수-100"
DIY_ALT_PPM = 100        # 배율 민감도: 자작·비계측(diy) 등급을 기준 격자판으로 교정한 경우 (D5·C3)
NEAR_MISS = 1.3          # 판정량 / 4:1 기준이 1 초과 ~ 이 값 이하면 '경계'(아깝게 탈락)
MAIN_TYPES = ("국소높이", "국소선폭", "구멍지름", "길이40", "위치")


def seed_index(rid):
    """후보별 난수 시드 오프셋. 'M07' → 6 처럼 id 숫자 − 1 (1차 실행의 '정렬 순번'과 같은 값).
    숫자가 없는 id 는 crc32 로 정한다. 행 순서·병렬 여부와 무관하게 같은 id 는 같은 시드를 쓴다."""
    m = re.fullmatch(r"[A-Za-z]*0*(\d+)", str(rid))
    if m:
        return max(int(m.group(1)) - 1, 0)
    return 900 + zlib.crc32(str(rid).encode("utf-8")) % 100


def run_candidate(task):
    """후보 1개의 낙관 · 보수-500 · 보수-100 시뮬레이션 (병렬 작업 단위, spawn 에서 pickle 가능).
    task = (row dict, n_mc, 시드). → dict(id, sims {시나리오: 요약}, notes, mode, cal_class, sec)."""
    row, n_mc, sd = task
    rid = row["id"]
    t0 = time.time()
    mode, msrc = sim.resolve_mode(row)
    msrc = row.get("mode_src", msrc) or msrc          # screen.main 이 미리 정한 출처 (csv / id목록)
    m, nt = sim.model_from_row(row)
    out = {SC_OPT: None, SC_C500: None, SC_C100: None}
    cal = ""
    if m is None:
        for sc in out:
            out[sc] = sim.unmeasurable_summary()
    else:
        cal = m.cal_class or f"(access 기본 {m.u_s * 1e6:g} ppm)"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                parts = None if m.point else sim.build_parts(m)
                out[SC_OPT], _ = sim.simulate(m, n_mc=n_mc, seed=sd, cons=False, parts=parts)
                out[SC_C500], _ = sim.simulate(m, n_mc=n_mc, seed=sd, cons=True, parts=parts)
                if m.cal_class == "diy":
                    m100, _ = sim.model_from_row(row, diy_ppm=DIY_ALT_PPM)
                    out[SC_C100], _ = sim.simulate(m100, n_mc=n_mc, seed=sd, cons=True, parts=parts)
                else:
                    out[SC_C100] = out[SC_C500]
                del parts
            except MemoryError:
                for sc in out:
                    out[sc] = sim.unmeasurable_summary()
                nt.append("메모리 부족 → 측정 불가")
        if m.measures_z and np.isfinite(m.depth) and not m.point:
            for key, name in (("flat", "국소높이"), ("step", "단차"), ("line", "선폭"),
                              ("hole", "구멍지름"), ("pin", "위치")):
                if not sim.depth_ok(m, key):
                    nt.append(f"{name} 패치 높이 {sim.PATCH_RELIEF[key]:g} µm > depth {m.depth:g} µm")
        nt.append(f"배율 {m.cal_class or '기본'} {m.u_s * 1e6:g} ppm, seam {m.n_seams}개")
        if mode == "line_profiler":
            tr = scoring.raster_time_min(dict(row, mode=mode))
            nt.append("선 단면 장비(면 측정은 래스터 가정"
                      + (f", 면 래스터 {tr:,.0f} 분)" if np.isfinite(tr) else ")"))
    if mode != "area" or msrc == "csv":
        nt.append(f"mode {mode} ({msrc})")
    return {"id": rid, "sims": out, "notes": nt, "mode": mode, "cal_class": cal, "sec": time.time() - t0}


def _task_cost(row):
    """대략의 계산량 (먼저 무거운 후보를 보내 병렬 대기 시간을 줄인다)."""
    st = row.get("xy_step_um", np.nan)
    if not np.isfinite(st) or st <= 0 or sim.resolve_mode(row)[0] in ("indirect", "point_probe"):
        return 0.0
    return 1.0 / max(st, sim.TRUTH_GRID) ** 2


def default_workers():
    return max(1, (os.cpu_count() or 2) - 1)


def run_sims(df, n_mc, seed, log=print, workers=1):
    """후보마다 낙관 · 보수-500 · 보수-100. 보수-100 은 diy 등급만 다시 계산하고 나머지는 보수-500 과 같다.
    패치(흐림 계산)는 한 번 만들어 같이 쓴다. workers > 1 이면 후보 단위로 multiprocessing(spawn).
    시드는 후보 id 로 정해지므로(seed_index) 병렬·순차 결과가 같다.
    → (sims {시나리오: {id: 요약}}, notes {id: [..]}, meta {id: {mode, cal_class, sec}})"""
    sims = {SC_OPT: {}, SC_C500: {}, SC_C100: {}}
    notes, meta = {}, {}
    tasks = []
    for i, row in df.iterrows():
        d = row.to_dict()
        tasks.append((d, n_mc, seed * 1000 + seed_index(d["id"])))
    order = sorted(range(len(tasks)), key=lambda k: -_task_cost(tasks[k][0]))
    n = len(tasks)
    t_start = time.time()

    def take(res, k):
        rid = res["id"]
        for sc in sims:
            sims[sc][rid] = res["sims"][sc]
        notes[rid] = res["notes"]
        meta[rid] = {"mode": res["mode"], "cal_class": res["cal_class"], "sec": res["sec"]}
        g = " ".join(f"{t}:{res['sims'][SC_C500][t]['grade']}" for t in ("국소높이", "국소선폭", "구멍지름", "길이40"))
        log(f"  [{k:3d}/{n}] {rid:6s} {res['sec']:6.1f} s  (경과 {time.time() - t_start:6.0f} s)  [보수-500] {g}")

    if workers <= 1 or n <= 1:
        for k, j in enumerate(order, 1):
            take(run_candidate(tasks[j]), k)
    else:
        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=min(workers, n)) as pool:
            for k, res in enumerate(pool.imap_unordered(run_candidate, [tasks[j] for j in order], chunksize=1), 1):
                take(res, k)
    return sims, notes, meta


def sim_table(df, sims_all, notes, meta=None):
    recs = []
    meta = meta or {}
    for sc, sims in sims_all.items():
        for rid in df["id"]:
            mt = meta.get(rid, {})
            for name, s in sims[rid].items():
                nt = notes.get(rid, [])
                if s.get("note"):
                    nt = [s["note"]] + [x for x in nt if x != s["note"]]
                ratio = s["Q_um"] / s["lim4_um"] if np.isfinite(s["Q_um"]) else np.nan
                near = "경계" if (np.isfinite(ratio) and 1.0 < ratio <= NEAR_MISS) else ""
                recs.append({"scenario": sc, "id": rid, "mode": mt.get("mode", ""),
                             "cal_class": mt.get("cal_class", ""), "error_type": name, "group": s["group"],
                             "truth_um": s["truth_um"], "bias_um": s["bias_um"], "2sd_um": s["sd2_um"],
                             "Q_um": s["Q_um"], "lim_4to1_um": s["lim4_um"], "lim_10to1_um": s["lim10_um"],
                             "Q/4to1": ratio, "판정": s["grade"], "경계표시": near,
                             "valid_frac": s["valid_frac"], "note": "; ".join(nt)})
    return pd.DataFrame(recs)


def evaluate(df, rows, rtab, sims, manual, scenario, meta=None):
    """점수·조합 (한 시나리오). → (점수 DataFrame, 조합 DataFrame, 민감도용 pool)
    pass_all = 규칙(예산·안전·G코드·실현성) 탈락 없음 + 정밀도 2종 이상."""
    srecs, pool = [], {}
    meta = meta or {}
    for rid in df["id"]:
        ok1, n1, ratios = scoring.precision_pass(sims[rid])
        sc = scoring.score_items(rows[rid], sims[rid], manual.get(rid, {}))
        rok = bool(rtab[rid]["rule_ok"])
        rec = {"id": rid, "name": rows[rid]["name"], "scenario": scenario,
               "mode": meta.get(rid, {}).get("mode", ""), "cal_class": meta.get(rid, {}).get("cal_class", ""),
               "pass_budget": rtab[rid]["pass_budget"],
               "pass_safety": rtab[rid]["pass_safety"], "pass_gcode": rtab[rid]["pass_gcode"],
               "pass_feasible": rtab[rid]["pass_feasible"],
               "pass_precision": ok1, "n_groups_4to1": n1, "pass_all": rok and ok1}
        for g, r in ratios.items():
            rec[f"ratio_{g}"] = r
        for t in MAIN_TYPES:
            rec[f"{t}_판정"] = sims[rid][t]["grade"]
        rec["time_min_used"] = rows[rid].get("time_min", np.nan)
        rec["time_note"] = rows[rid].get("_time_note", "")
        for k in scoring.WEIGHTS:
            rec[f"s_{k}"] = sc[k]
        rec["score"] = scoring.total(sc)
        srecs.append(rec)
        if rec["pass_all"]:
            pool[rid] = sc
    sdf = pd.DataFrame(srecs)
    sdf["rank_all"] = sdf["score"].rank(ascending=False, method="min").astype(int)
    sdf["rank_pass"] = np.nan
    msk = sdf["pass_all"]
    sdf.loc[msk, "rank_pass"] = sdf.loc[msk, "score"].rank(ascending=False, method="min")
    sdf = sdf.sort_values(["pass_all", "score"], ascending=[False, False])
    cand = [rid for rid in df["id"] if (not scoring.precision_pass(sims[rid])[0]) and rtab[rid]["rule_ok"]]
    combos = scoring.find_combos(cand, rows, sims, manual, rtab, rules.BUDGET_OWN_KRW, rules.BUDGET_OUTSOURCE_KRW,
                                 time_max=rules.FEASIBLE_MAX_MIN)
    cdf = pd.DataFrame([{k: v for k, v in c.items() if k != "_scores"} for c in combos])

    def _valid(c):
        return bool(c["pass_precision"]) and c["budget_ok"] != "탈락" and c.get("feasible") != "탈락"

    if len(cdf):
        cdf["valid"] = [_valid(c) for c in combos]
        cdf = cdf.sort_values(["valid", "score"], ascending=[False, False])
        for c in combos:
            if _valid(c):
                pool[c["combo"]] = c["_scores"]
    else:
        cdf = pd.DataFrame(columns=["combo", "a", "b", "pass_precision", "budget_ok", "score", "valid"])
    cdf.insert(0, "scenario", scenario)
    return sdf, cdf, pool


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mc", type=int, default=50, help="몬테카를로 반복 수 (기본 50)")
    ap.add_argument("--spec", nargs="*", help="사양 CSV 경로 (생략하면 docs/0_방법탐색/후보-사양_*.csv)")
    ap.add_argument("--out", help="출력 폴더")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ids", nargs="*", help="이 id 만 계산")
    ap.add_argument("--manual", default=MANUAL_PATH, help="수동 점수 CSV (id,verify,novelty)")
    ap.add_argument("--no-fig", action="store_true")
    ap.add_argument("--workers", type=int, default=default_workers(),
                    help=f"병렬 프로세스 수 (기본 CPU 수 − 1 = {default_workers()}, 1 = 순차)")
    a = ap.parse_args(argv)

    paths = a.spec if a.spec else find_spec_files(SPEC_DIR)
    out = a.out
    if not paths:
        print(f"[경고] {SPEC_DIR} 에 후보-사양_*.csv 가 없어 시험용 {SAMPLE_SPEC} 로 실행합니다.")
        paths = [SAMPLE_SPEC]
    if out is None:
        out = SAMPLE_OUT if all(os.path.abspath(p) == SAMPLE_SPEC for p in paths) else OUT_DIR
    os.makedirs(out, exist_ok=True)

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        df = load_specs(paths)
    for w in wlist:
        print(f"[경고] {w.message}")
    skipped = list(df.attrs.get("skipped", []))
    write_input_warnings(os.path.join(out, "입력경고.txt"), paths, skipped, len(df))
    if a.ids:
        want = {str(i).strip().upper() for i in a.ids}
        df = df[df["id"].isin(want)].reset_index(drop=True)
    # mode 를 한 번 정해 모든 단계(규칙·시뮬레이션·점수)가 같은 값을 쓰게 한다
    df["mode_src"] = [sim.resolve_mode(r)[1] for _, r in df.iterrows()]
    df["mode"] = [sim.resolve_mode(r)[0] for _, r in df.iterrows()]
    print(f"사양 {len(df)}행 ({', '.join(os.path.basename(p) for p in paths)}) → {out}"
          + (f" · 건너뛴 행 {len(skipped)}개 (입력경고.txt)" if skipped else ""))
    print("  mode: " + ", ".join(f"{k} {v}" for k, v in df["mode"].value_counts().items()))

    # 실험 2 ---------------------------------------------------------------
    rt = rules.judge(df)
    rt.to_csv(os.path.join(out, "규칙판정.csv"), index=False, encoding="utf-8-sig")

    # 실험 3 ---------------------------------------------------------------
    t0 = time.time()
    print(f"시뮬레이션 (MC {a.mc}회, 시나리오 {SC_OPT}/{SC_C500}/{SC_C100}, workers {a.workers})")
    sims_all, notes, meta = run_sims(df, a.mc, a.seed, workers=a.workers)
    print(f"  합계 {time.time() - t0:.1f} s")
    st = sim_table(df, sims_all, notes, meta)
    st.to_csv(os.path.join(out, "시뮬레이션.csv"), index=False, encoding="utf-8-sig")

    # 실험 4 (기준 = 보수-500) -----------------------------------------------
    manual = scoring.load_manual(a.manual)
    rows = {}
    for _, r in df.iterrows():
        d = r.to_dict()
        tr = scoring.raster_time_min(d)
        if np.isfinite(tr):          # 선 단면 장비: 속도 점수에 면 래스터 시간 사용
            d["_time_note"] = f"선 단면 장비(면 측정은 래스터 가정): CSV {d.get('time_min')} 분 -> {tr:,.0f} 분"
            d["time_min"] = tr
        rows[r["id"]] = d
    rtab = {r["id"]: r.to_dict() for _, r in rt.iterrows()}
    sdf, cdf, pool = evaluate(df, rows, rtab, sims_all[SC_C500], manual, SC_C500, meta)
    sdf.to_csv(os.path.join(out, "점수.csv"), index=False, encoding="utf-8-sig")
    cdf.to_csv(os.path.join(out, "조합.csv"), index=False, encoding="utf-8-sig")

    # 보수-100 에서 새로 통과하는 후보·조합
    sdf1, cdf1, _ = evaluate(df, rows, rtab, sims_all[SC_C100], manual, SC_C100, meta)
    base_ok = set(sdf.loc[sdf["pass_all"], "id"])
    base_cv = set(cdf.loc[cdf["valid"], "combo"]) if len(cdf) else set()
    new_c = sdf1[sdf1["pass_all"] & ~sdf1["id"].isin(base_ok)].copy()
    new_c["kind"], new_c["name_or_combo"] = "후보", new_c["id"]
    if len(cdf1):
        new_k = cdf1[cdf1["valid"] & ~cdf1["combo"].isin(base_cv)].copy()
        new_k["kind"], new_k["name_or_combo"] = "조합", new_k["combo"]
    else:
        new_k = pd.DataFrame()
    keep = ["kind", "name_or_combo", "score", "pass_budget", "pass_gcode", "budget_ok", "gcode",
            "cost_krw", "time_min"] + [f"{t}_판정" for t in MAIN_TYPES]
    newdf = pd.concat([new_c, new_k], ignore_index=True, sort=False)
    newdf = newdf[[c for c in keep if c in newdf.columns]] if len(newdf) else pd.DataFrame(columns=keep)
    newdf.to_csv(os.path.join(out, "보수100_신규통과.csv"), index=False, encoding="utf-8-sig")

    # 민감도: 보수-500 통과 후보 + 유효 조합. 2개 미만이면 전체 단일 후보로 대신
    basis = "통과 후보+유효 조합 (보수-500)"
    if len(pool) < 2:
        basis = "전체 후보(통과 후보 2개 미만)"
        pool = dict(pool)
        for rid in df["id"]:
            pool.setdefault(rid, scoring.score_items(rows[rid], sims_all[SC_C500][rid], manual.get(rid, {})))
    sens = scoring.sensitivity(pool)
    sens.insert(0, "pool_basis", basis)
    sens.index.name = "id"
    sens.to_csv(os.path.join(out, "민감도.csv"), encoding="utf-8-sig")

    if not a.no_fig:
        import figures
        figures.q_bars(st, os.path.join(out, "그림1_판정량.png"))
        for g, fname in figures.GROUP_FILES.items():
            figures.q_group(st, g, os.path.join(out, fname))
        figures.score_rank(sdf, cdf, os.path.join(out, "그림2_점수순위.png"), top=figures.RANK_TOP)
        figures.sens_range(sens, os.path.join(out, "그림3_민감도.png"))

    # 요약 출력
    sims = sims_all[SC_C500]
    print("\n== 요약 (보수-500) ==")
    for rid in df["id"]:
        r = sdf[sdf["id"] == rid].iloc[0]
        g = ", ".join(f"{k} {sims[rid][k]['grade']} (Q={sims[rid][k]['Q_um']:.1f})" for k in MAIN_TYPES)
        print(f"{rid}: 예산 {r.pass_budget} / 안전 {r.pass_safety} / G코드 {r.pass_gcode} / "
              f"실현성 {r.pass_feasible} / 정밀도 {'통과' if r.pass_precision else '탈락'}({r.n_groups_4to1}종) / "
              f"최종 {'통과' if r.pass_all else '탈락'} / 점수 {r.score:.2f}")
        print(f"   {g}")
    nv = int(cdf["valid"].sum()) if len(cdf) else 0
    print(f"조합 {len(cdf)}개 중 유효 {nv}개 / 보수-100 신규 통과 {len(newdf)}건")
    return 0


def write_input_warnings(path, paths, skipped, n_rows):
    """건너뛴 행 목록 (없어도 파일을 써서 이전 실행의 경고가 남지 않게 한다)."""
    lines = [f"입력 파일 {len(paths)}개: " + ", ".join(os.path.basename(p) for p in paths),
             f"읽은 후보 {n_rows}행 · 건너뛴 행 {len(skipped)}개", ""]
    if skipped:
        lines.append("id\t파일\t사유")
        lines += [f"{i}\t{src}\t{why}" for i, src, why in skipped]
        lines += ["", "건너뛴 id: " + ", ".join(str(i) for i, _, _ in skipped)]
    else:
        lines.append("건너뛴 행 없음")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
