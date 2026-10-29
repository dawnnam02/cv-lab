# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""캠페인 조립 (세부청사진 §6.1 ⑧ · §6.8). S1–S2 뼈대: 계획 (스캔 목록 · 가상 시각 · 시드) + 참 높이맵.

광학 · 카메라 (S3), 위치 로그 · 교정 · 기준 (S4), raw 쓰기 · 검증기 (S5)는 이 뼈대에 붙인다.
결과는 작업자 수와 무관해야 하므로, 시드는 시드 나무 경로로만 정하고 파일은 주 프로세스가 정한 순서로 쓴다.
"""
from __future__ import annotations

import csv
import io
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from .clock import VirtualClock
from .seeds import SeedTree, seed_tag
from .shape import SHAPE_FACTORS, load_specimen, simulate_specimen
from .simconfig import ROOT, load_factors, load_scenarios

EXPECTED_CSV = ROOT / "docs" / "판정-시나리오_자료" / "기대판정.csv"


# ---------------------------------------------------------------- 계획
def layer_dirs(n_layers_total: int, layers, passes: int) -> list[tuple]:
    """[(층 키, 층 번호 또는 None, 줄 번호, 폴더 이름)] 층 순서 → 줄 순서, 끝에 post 줄들."""
    out = []
    for n in layers:
        for p in range(passes):
            out.append((f"L{n:03d}", n, p, f"L{n:03d}" + (f"_p{p:02d}" if p else "")))
    for p in range(passes):
        out.append(("post", None, p, "post" + (f"_p{p:02d}" if p else "")))
    return out


def resolve_layers(spec_entry: dict, n_layers: int) -> list[int]:
    """출력한 층 번호 목록. print_layers = all 또는 앞 N층 (작은 캠페인은 그 층에서 출력을 멈춘 것으로 봄).
    모든 층을 스캔하므로 (D-18) 층을 건너뛰는 목록은 받지 않음 (빠진 층은 고장 X7로만)."""
    v = spec_entry.get("print_layers", "all")
    if v == "all":
        return list(range(n_layers))
    if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= n_layers:
        raise ValueError(f"print_layers가 잘못됨: {v!r} (all 또는 1–{n_layers})")
    return list(range(v))


def build_plan(cfg: dict, camp: dict, seed: int, n_layers_of: dict, blind: bool = False) -> dict:
    """스캔 계획. 시각은 가상 시계 (§6.8), 시드는 시드 나무 (캠페인 → 시편 · 반복 → 층 → 줄 → 성분).

    blind면 raw 쪽 값 (raw_*)에서 시드 · 요인을 비우고 참값 쪽 (truth_*)에만 둠 (명세 v1.1, §6.9).
    """
    tree = SeedTree(seed)
    clock = VirtualClock(cfg["clock"]["start_iso"])
    passes = int(camp["passes_per_layer"])
    scans = []
    for se in camp["specimens"]:
        name, sid, rep = se["name"], se["specimen_id"], int(se["repeat"])
        sc = cfg["specimens"][name]
        nL = n_layers_of[name]
        layers = resolve_layers(se, nL)
        folder = f"{sid}_r{rep:02d}"
        per_pass = float(sc["pause_s"]) / (passes + 1)  # 줄마다 + 기준물 두 단 몫 [추정, S4에서 위치 로그로 바꿈]
        for key, n, p, d in layer_dirs(nL, layers, passes):
            if key == "post" and p == 0:
                clock.advance(cfg["thermal"]["post_wait_s"])
            elif p == 0:
                clock.advance(sc["layer_print_s"])
            br = tree.child(sid, rep, key, p)
            scan_id = folder + ("" if key == "post" else f"_{key}") + (f"_p{p:02d}" if p else "")
            sim_seed, noise_seed = br.int_seed(), br.child("noise").int_seed()
            scans.append(dict(
                scan_id=scan_id, specimen_id=sid, specimen=name, repeat=rep, layer_key=key, layer_idx=n,
                pass_idx=p, folder=f"{folder}/{d}", t_start_ns=clock.t_ns, datetime=clock.iso(),
                raw_sim_seed=None if blind else sim_seed, raw_noise_seed=None if blind else noise_seed,
                truth_sim_seed=sim_seed, truth_noise_seed=noise_seed))
            clock.advance(per_pass)
            if key != "post" and p == passes - 1:
                clock.advance(per_pass)  # 기준물 두 단 · 레인 · resume
    return dict(campaign_id=camp["campaign_id"], session_id=camp["session_id"], seed_tag=seed_tag(seed),
                blind=bool(blind), base=camp["base"], passes_per_layer=passes, scans=scans)


# ---------------------------------------------------------------- 참 형상
def factor_switches(factors_cfg: dict) -> dict:
    return {k: bool(v["enabled"]) for k, v in factors_cfg.items() if k in SHAPE_FACTORS}


def _specimen_job(args):
    cfg, se, base, factors, seed, scen_pep, n_layers = args
    spec = load_specimen(cfg, se["name"])
    layers = resolve_layers(se, spec.n_layers)
    maps = {}

    def keep(_name, key, H):
        maps[key] = H

    tree = SeedTree(seed).child(se["specimen_id"], int(se["repeat"]))
    res = simulate_specimen(spec, cfg, [scen_pep], base=base, factors=factors, seed_tree=tree,
                            layers=layers, on_heightmap=keep, n_print_layers=len(layers))[0]
    res["gcode_sha256"] = spec.sha256
    res["heightmap_origin_mm"] = [spec.grid["x0_mm"], spec.grid["y0_mm"]]
    res["heightmap_step_mm"] = spec.grid["res_mm"]
    res["layer_count"] = len(layers)
    return se["specimen_id"], res, {k: maps[k] for k in list(layers) + ["post"]}


def npy_bytes(a: np.ndarray) -> bytes:
    b = io.BytesIO()
    np.save(b, np.ascontiguousarray(a), allow_pickle=False)
    return b.getvalue()


def json_bytes(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")


def run_shape_campaign(cfg: dict, camp: dict, seed: int, truth_root: Path, workers: int = 1,
                       blind: bool = False) -> dict:
    """참 높이맵 (층별 + post)과 계획 · 형상 참값을 truth 뿌리에 씀. 이미 있으면 오류 (쓰기 한 번)."""
    scen = load_scenarios()["scenarios"]
    factors = factor_switches(load_factors())
    jobs = []
    for se in camp["specimens"]:
        if se["scenario"] not in scen:
            raise KeyError(f"시나리오 {se['scenario']} 없음")
        if se["name"] not in scen[se["scenario"]]["specimens"]:
            raise ValueError(f"시나리오 {se['scenario']}는 {se['name']}에 쓰지 않음 (T5 YAML specimens)")
        jobs.append((cfg, se, camp["base"], factors, seed, scen[se["scenario"]]["print_error_params"], None))
    if workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as ex:
            results = list(ex.map(_specimen_job, jobs))
    else:
        results = [_specimen_job(j) for j in jobs]
    n_total = {se["name"]: r[1]["layer_count"] for se, r in zip(camp["specimens"], results)}
    plan = build_plan(cfg, camp, seed, n_total, blind=blind)
    out = Path(truth_root) / camp["campaign_id"]
    out.mkdir(parents=True, exist_ok=False)
    (out / "heightmaps").mkdir()
    nbytes = 0
    shape_truth = {}
    for (sid, res, maps) in results:
        tid = f"T-{sid}"
        for key in sorted(maps, key=lambda k: (k == "post", k if k == "post" else int(k))):
            fn = f"{tid}_post.npy" if key == "post" else f"{tid}_L{int(key):03d}.npy"
            data = npy_bytes(maps[key])
            with open(out / "heightmaps" / fn, "xb") as fh:
                fh.write(data)
            nbytes += len(data)
        shape_truth[tid] = {k: res[k] for k in (
            "specimen", "base", "gcode_sha256", "heightmap_origin_mm", "heightmap_step_mm", "print_error_params",
            "thermal_params", "z_axis_error_params", "judgement", "pass_pct", "n_valid", "n_pass", "layer_count")}
    for name, obj in (("truth_shape.json", shape_truth), ("sim_plan.json", plan)):
        data = json_bytes(obj)
        with open(out / name, "xb") as fh:
            fh.write(data)
        nbytes += len(data)
    return dict(campaign=camp["campaign_id"], seed_tag=plan["seed_tag"],
                specimens=[se["specimen_id"] for se in camp["specimens"]],
                layers=sum(len(m) - 1 for _, _, m in results), scans=len(plan["scans"]), frames=0,
                bytes_raw=0, bytes_disk=nbytes, faults=[], blind=bool(blind), out=str(out))


# ---------------------------------------------------------------- SM2 대조
def expected_rows(path=EXPECTED_CSV) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sm2_job(args):
    cfg, name, peps, base, factors, seed = args
    spec = load_specimen(cfg, name)
    tree = SeedTree(seed) if seed is not None else None
    return simulate_specimen(spec, cfg, peps, base=base, factors=factors, seed_tree=tree)


def truth_all(cfg: dict, base: str = "reference", factors: dict | None = None, seed: int | None = None,
              workers: int = 1, only: list | None = None) -> list[dict]:
    """세 시편 × 해당 시나리오의 참 판정 (참값만 모드)."""
    scen = load_scenarios()["scenarios"]
    names = [n for n in cfg["specimens"] if only is None or n in only]
    jobs = [(cfg, n, [s["print_error_params"] for s in scen.values() if n in s["specimens"]], base, factors, seed)
            for n in names]
    if workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as ex:
            res = list(ex.map(_sm2_job, jobs))
    else:
        res = [_sm2_job(j) for j in jobs]
    return [r for rs in res for r in rs]


def compare_sm2(truth: list[dict], expected: list[dict]) -> dict:
    by = {(t["scenario"], t["specimen"]): t for t in truth}
    mism, diffs, missing = [], [], []
    for e in expected:
        t = by.get((e["scenario"], e["specimen"]))
        if t is None:
            missing.append([e["scenario"], e["specimen"], e["step_gauge"]])
            continue
        diffs.append(abs(t["pass_pct"] - float(e["truth_pass_pct"])))
        if t["judgement"] != e["truth_judgement"]:
            mism.append([e["scenario"], e["specimen"], e["step_gauge"], t["judgement"], e["truth_judgement"]])
    return dict(rows=len(expected), match=len(expected) - len(mism) - len(missing), mismatch=mism,
                missing=missing, max_pass_pct_diff=round(max(diffs) if diffs else 0.0, 6))
