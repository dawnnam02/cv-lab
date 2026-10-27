# 처리 담당 (T4b · T7–T12) 열람 금지. 판정 시험 개발용 기대 판정 계산 (청사진 §5.2)
"""판정 시험 시나리오의 기대 판정 (T5, SC5–SC9).

- 시나리오: config/scenarios/판정시나리오_v1.yaml. 시편: plate20 (docs/G코드-점검_자료/plate20.gcode) ·
  MANIFEST의 D-19 두 파일.
- 정답 높이: cvlab.gcode (parse_file → 경계 상자 + 1 mm 격자 0.02 mm → build_reference).
- 임시 판정 영역 (stand-in-v1): 출력물 칸 − 꼭대기 종류 ∈ {SKIRT, BRIM, SUPPORT, PRIME-TOWER} − 심도 밖
  (z_n − Z_ref > 8.000 mm, nm 정수). 엣지 띠 · 가림 · 시야는 넣지 않음. T4b 판정 영역으로 다시 계산은 T5-2.
- 판정: cvlab.judge (fine_to_cell_layer · judge_print). U 20.9 µm (주) · 14.6 µm · 0 (참), 칸 0.2 · 0.4 mm.
- 출력: docs/판정-시나리오_자료/기대판정.csv · 희석표.csv, 요약 줄 `SCEN {json}`.
- 실행: PYTHONPATH=src python scripts/scenario_expected.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import yaml

from cvlab.gcode import build_reference, make_grid, parse_file
from cvlab.gcode.reference import segment_widths
from cvlab.judge import LayerInput, fine_to_cell_layer, judge_print, load_params

ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "config" / "scenarios" / "판정시나리오_v1.yaml"
JUDGE_YAML = ROOT / "config" / "judge.yaml"
MANIFEST = ROOT / "data" / "gcode_samples" / "MANIFEST.csv"
PLATE = ROOT / "docs" / "G코드-점검_자료" / "plate20.gcode"
OUT_DIR = ROOT / "docs" / "판정-시나리오_자료"
CSV_OUT = OUT_DIR / "기대판정.csv"
DIL_OUT = OUT_DIR / "희석표.csv"

RES = 0.02
DEPTH_NM = 8_000_000
EXCLUDED = ("SKIRT", "BRIM", "SUPPORT", "PRIME-TOWER")
REGION_SOURCE = "stand-in-v1"
COLS = ["scenario", "specimen", "kind", "intent", "observable", "step_gauge", "n_layers", "n_region_cells",
        "truth_pass_pct", "truth_judgement", "seen_pass_pct", "seen_hold_pct", "seen_fail_pct",
        "verdict_U20_9", "verdict_U14_6", "verdict_alt04_U20_9", "region_source"]
EXPECT = {"pass": "pass", "borderline": "hold", "fail": "fail"}

P209 = load_params(JUDGE_YAML, U_mm=0.0209, U_source="D-15 기본 U 20.9 µm, T12 전 참고값")
P146 = load_params(JUDGE_YAML, U_mm=0.0146, U_source="D-16 계단 기준물, 조건 C1–C3 전제")
P0 = load_params(JUDGE_YAML, U_mm=0.0, U_source="참 판정, 방식 A")


def specimens() -> dict:
    out = {"plate20": PLATE}
    with open(MANIFEST, encoding="utf-8") as fh:
        for m in csv.DictReader(fh):
            out[m["이름"]] = ROOT / m["로컬경로"]
    return out


def object_bbox(r) -> dict:
    e = r.extrusions()
    w = segment_widths(r, r.params)
    m = ~e["type"].isin(EXCLUDED).to_numpy()
    xs = np.concatenate([e.x0_mm[m], e.x1_mm[m]]); ys = np.concatenate([e.y0_mm[m], e.y1_mm[m]])
    half = float(np.max(w[m])) / 2.0
    return dict(xmin=float(xs.min()) - half, xmax=float(xs.max()) + half,
                ymin=float(ys.min()) - half, ymax=float(ys.max()) + half)


# ---- 오차 종류별 Δ_true, Δ_seen (근거: YAML kinds · 문서 §2) ----------------------
def deltas(kind: str, p: dict, ctx: dict):
    """(Δ_true, Δ_seen) mm 배열 (판정 영역 밖은 아래에서 NaN). ctx: 층 n의 고운 배열들."""
    Z, zn, top, U, V, X, Y = ctx["Z"], ctx["zn"], ctx["top"], ctx["U"], ctx["V"], ctx["X"], ctx["Y"]
    zero = np.zeros_like(Z)
    if kind == "z_offset":
        d = zero + p["dz_um"] / 1000.0
        return d, d
    if kind == "z_scale":
        g = p["gain_ppm"] * 1e-6
        return g * Z, -g * (zn - Z)
    if kind == "local":
        nL = ctx["nL"]
        k0 = int(round(p["layer_from_rel"] * (nL - 1))); k1 = int(round(p["layer_to_rel"] * (nL - 1)))
        cx = ctx["b"]["xmin"] + p["loc_rel"][0] * ctx["W"]; cy = ctx["b"]["ymin"] + p["loc_rel"][1] * ctx["H"]
        r2 = (X - cx) ** 2 + (Y - cy) ** 2
        g = (p["amp_um"] / 1000.0) * np.exp(-r2 / (2 * p["sigma_mm"] ** 2))
        d = np.where((top >= k0) & (top <= k1), g, 0.0)
        return d, d
    if kind == "warp":
        rho2 = ((U - 0.5) ** 2 + (V - 0.5) ** 2) / 0.5
        d = (p["lift_um"] / 1000.0) * rho2
        return d, d
    if kind == "missing_layer":
        nL = ctx["nL"]
        k = max(1, int(round(p["layer_rel"] * (nL - 1))))
        m = int(p["n_layers"])
        cx = ctx["b"]["xmin"] + p["loc_rel"][0] * ctx["W"]; cy = ctx["b"]["ymin"] + p["loc_rel"][1] * ctx["H"]
        inside = (X - cx) ** 2 + (Y - cy) ** 2 <= p["radius_mm"] ** 2
        zl = ctx["z_layers"]
        hit = inside & (top >= k) & (top <= k + m - 1)
        d = np.where(hit, zl[k - 1] - Z, 0.0)
        return d, d
    if kind == "extrusion":
        per = p["ripple_period_mm"]
        d = p["dz_um"] / 1000.0 + (p["ripple_um"] / 1000.0) * np.sin(2 * np.pi * (X + Y) / (math.sqrt(2) * per))
        return d, d
    raise ValueError(f"모르는 오차 종류 {kind}")


def run_specimen(name: str, path: Path, scen: list, kinds: dict) -> tuple[list, dict]:
    r = parse_file(path)
    b = object_bbox(r)
    grid = make_grid(b["xmin"], b["xmax"], b["ymin"], b["ymax"], RES, 1.0)
    ref = build_reference(r, grid=grid)
    ny, nx = grid["ny"], grid["nx"]
    xs = grid["x0_mm"] + np.arange(nx) * RES; ys = grid["y0_mm"] + np.arange(ny) * RES
    X, Y = np.meshgrid(xs, ys)
    W, H = b["xmax"] - b["xmin"], b["ymax"] - b["ymin"]
    U = (X - b["xmin"]) / W; V = (Y - b["ymin"]) / H
    exc = [i for i, t in enumerate(ref.type_names) if t in EXCLUDED]
    zl = ref.z_layers
    nL = ref.n_layers
    top = np.full((ny, nx), -1, np.int32)
    tc = np.full((ny, nx), -1, np.int16)
    tcodes = ref._type_codes  # cvlab.gcode 저장 형식 (읽기만, type_at과 같은 값)
    acc = {}
    for s in scen:
        kind = next((k for k in s["print_error_params"] if k != "scenario"), None)
        sgo = kind is not None and kinds[kind]["observable"] == "step_gauge_only"
        acc[s["name"]] = dict(kind=kind, sgo=sgo, t02=[], s02=[], s04=[], t04=[])
    region_cells = []   # 층마다 0.2 칸 영역 수 (희석표)
    used_layers = 0
    for n in range(nL):
        fp = ref.footprint(n)
        top[fp] = n
        tc.ravel()[np.flatnonzero(fp.ravel())] = tcodes[n]
        has = top >= 0
        Z = np.where(has, zl[np.maximum(top, 0)], np.nan)
        zn = float(zl[n])
        depth_nm = np.rint((zn - np.where(has, Z, zn)) * 1e6).astype(np.int64)
        region = has & ~np.isin(tc, exc) & (depth_nm <= DEPTH_NM)
        if not region.any():
            continue
        used_layers += 1
        ctx = dict(Z=np.where(has, Z, 0.0), zn=zn, top=top, U=U, V=V, X=X, Y=Y, b=b, W=W, H=H, nL=nL, z_layers=zl)
        first = True
        for s in scen:
            a = acc[s["name"]]
            if a["kind"] is None:
                dt = ds = np.zeros((ny, nx))
            else:
                dt, ds = deltas(a["kind"], s["print_error_params"][a["kind"]], ctx)
            dt = np.where(region, dt, np.nan)
            Lt = LayerInput(n, "in_process", dt, region)
            ct02 = fine_to_cell_layer(Lt, RES, 0.2, P209)
            a["t02"].append(ct02)
            if first:
                region_cells.append(int(ct02.region.sum())); first = False
            if ds is dt or a["kind"] in (None, "z_offset", "local", "warp", "missing_layer", "extrusion"):
                a["s02"].append(ct02)
                a["s04"].append(fine_to_cell_layer(Lt, RES, 0.4, P209))
            else:
                Ls = LayerInput(n, "in_process", np.where(region, ds, np.nan), region)
                a["s02"].append(fine_to_cell_layer(Ls, RES, 0.2, P209))
                a["s04"].append(fine_to_cell_layer(Ls, RES, 0.4, P209))
                a["t04"].append(fine_to_cell_layer(Lt, RES, 0.4, P209))
    rows = []
    for s in scen:
        a = acc[s["name"]]
        tr = judge_print(a["t02"], P0)
        tp = tr.pct["pass_pct"]
        tj = "pass" if tr.counts["n_pass"] * 100 >= 95 * tr.counts["n_valid"] else "fail"
        obs = kinds[a["kind"]]["observable"] if a["kind"] else "yes"
        variants = [("off", a["s02"], a["s04"])]
        if a["sgo"]:
            variants.append(("on", a["t02"], a["t04"]))
        for sg, l02, l04 in variants:
            r1 = judge_print(l02, P209)
            r2 = judge_print(l02, P146)
            r3 = judge_print(l04, P209)
            rows.append(dict(
                scenario=s["name"], specimen=name, kind=a["kind"] or "none", intent=s["intent"], observable=obs,
                step_gauge=sg, n_layers=used_layers, n_region_cells=r1.counts["n_region"],
                truth_pass_pct=round(tp, 4), truth_judgement=tj,
                seen_pass_pct=round(r1.pct["pass_pct"], 4), seen_hold_pct=round(r1.pct["hold_pct"], 4),
                seen_fail_pct=abs(round(100.0 - round(r1.pct["pass_pct"], 4) - round(r1.pct["hold_pct"], 4), 4)),
                verdict_U20_9=r1.verdict, verdict_U14_6=r2.verdict, verdict_alt04_U20_9=r3.verdict,
                region_source=REGION_SOURCE,
                _warn_layers=sum(1 for L in r1.per_layer if L["warn_fail"]),
            ))
    rc = np.array(region_cells)
    N = int(rc.sum())
    dil = dict(specimen=name, n_layers=used_layers, total_cells=N,
               layer_cells_min=int(rc.min()), layer_cells_median=float(np.median(rc)), layer_cells_max=int(rc.max()),
               fail_area_one_layer_mm2=round(0.05 * N * 0.04, 2),
               layer_area_median_mm2=round(float(np.median(rc)) * 0.04, 2),
               whole_layers_to_fail=int(math.floor(0.05 * N / float(np.median(rc))) + 1),
               r7_area_median_layer_mm2=round(0.5 * float(np.median(rc)) * 0.04, 2),
               single_layer_can_fail="예" if 0.05 * N < rc.max() else "아니오")
    return rows, dil


def judged(r: dict) -> bool:
    return (r["step_gauge"] == "off" and r["observable"] in ("yes", "partial")) or \
           (r["step_gauge"] == "on" and r["observable"] == "step_gauge_only")


def mismatches(rows: list) -> list:
    bad = []
    for r in rows:
        if not judged(r):
            continue
        if r["verdict_U20_9"] != EXPECT[r["intent"]]:
            bad.append((r["scenario"], r["specimen"], r["step_gauge"], "의도", r["verdict_U20_9"]))
        elif r["intent"] == "pass" and float(r["seen_pass_pct"]) < 98:
            bad.append((r["scenario"], r["specimen"], r["step_gauge"], "P 여유", r["seen_pass_pct"]))
        elif r["intent"] == "fail" and float(r["seen_fail_pct"]) < 10:
            bad.append((r["scenario"], r["specimen"], r["step_gauge"], "F 여유", r["seen_fail_pct"]))
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="기존 기대판정.csv 재검사만 (다시 계산 안 함)")
    ap.add_argument("--only", default=None, help="시편 하나만 (조정용, 파일 안 씀)")
    a = ap.parse_args(argv)
    t0 = time.time()
    Y = yaml.safe_load(open(YAML_PATH, encoding="utf-8"))
    kinds, scen = Y["kinds"], Y["scenarios"]
    if a.check:
        rows = list(csv.DictReader(open(CSV_OUT, encoding="utf-8")))
    else:
        rows, dils = [], []
        for name, path in specimens().items():
            if a.only and name != a.only:
                continue
            sc = [s for s in scen if name in s["specimens"]]
            rr, dl = run_specimen(name, path, sc, kinds)
            rows += rr; dils.append(dl)
        if a.only:
            for r in rows:
                print(r["scenario"], r["step_gauge"], r["intent"], r["verdict_U20_9"], r["truth_judgement"],
                      r["truth_pass_pct"], r["seen_pass_pct"], r["seen_hold_pct"], r["seen_fail_pct"], r["_warn_layers"])
            print("mismatch", mismatches(rows))
            return 0
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(CSV_OUT, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)
        with open(DIL_OUT, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(dils[0]))
            w.writeheader(); w.writerows(dils)
    c12 = [(r["scenario"], r["specimen"], r["step_gauge"]) for r in rows
           if r["verdict_U20_9"] == "pass" and r["truth_judgement"] == "fail"]
    print("SCEN " + json.dumps(dict(
        n_kinds=len(kinds), n_scenarios=len(scen), specimens=sorted({r["specimen"] for r in rows}),
        rows=len(rows), mismatches=mismatches(rows), c12_risk_rows=c12, runtime_s=round(time.time() - t0, 1)),
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
