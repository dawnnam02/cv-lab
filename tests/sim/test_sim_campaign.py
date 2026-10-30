# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""작은 캠페인 뼈대 · 재현 · 블라인드 · SM2 일부 (S1–S2)."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from cvlab.sim.campaign import build_plan, compare_sm2, expected_rows, run_shape_campaign, truth_all
from cvlab.sim.simconfig import ROOT, SIM_CONFIG_DIR, load_campaign, load_default

SMALL = SIM_CONFIG_DIR / "campaign_small.yaml"
SCAN_RE = re.compile(r"^S\d{2}_r\d{2}(_L\d{3})?(_p\d{2})?$")
DIR_RE = re.compile(r"^S\d{2}_r\d{2}/(L\d{3}(_p\d{2})?|post(_p\d{2})?)$")


def _tree_digest(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_plan_names_times_seeds():
    cfg = load_default()
    camp = dict(load_campaign(SMALL), passes_per_layer=2)
    plan = build_plan(cfg, camp, 11, {"plate20": 10})
    ids = [s["scan_id"] for s in plan["scans"]]
    assert ids == ["S01_r01_L000", "S01_r01_L000_p01", "S01_r01_L001", "S01_r01_L001_p01", "S01_r01", "S01_r01_p01"]
    assert all(SCAN_RE.match(i) for i in ids) and all(DIR_RE.match(s["folder"]) for s in plan["scans"])
    t = [s["t_start_ns"] for s in plan["scans"]]
    assert t == sorted(t) and len(set(t)) == len(t)
    assert plan["scans"][-2]["t_start_ns"] - plan["scans"][-3]["t_start_ns"] >= cfg["thermal"]["post_wait_s"] * 1e9
    assert len({s["truth_sim_seed"] for s in plan["scans"]}) == len(ids)
    assert len(plan["seed_tag"]) == 8 and "seed" not in plan


def test_plan_blind_empties_raw_side():
    cfg = load_default()
    camp = load_campaign(SMALL)
    dev = build_plan(cfg, camp, 11, {"plate20": 10})
    bl = build_plan(cfg, camp, 11, {"plate20": 10}, blind=True)
    assert bl["blind"] and all(s["raw_sim_seed"] is None and s["raw_noise_seed"] is None for s in bl["scans"])
    assert [s["truth_sim_seed"] for s in bl["scans"]] == [s["raw_sim_seed"] for s in dev["scans"]]
    other = build_plan(cfg, camp, 12, {"plate20": 10})
    assert [s["truth_sim_seed"] for s in other["scans"]] != [s["truth_sim_seed"] for s in dev["scans"]]


def test_small_campaign_reproducible(tmp_path):
    cfg = load_default()
    camp = load_campaign(SMALL)
    a = run_shape_campaign(cfg, camp, 20261029, tmp_path / "a", workers=1)
    b = run_shape_campaign(cfg, camp, 20261029, tmp_path / "b", workers=4)
    da = _tree_digest(Path(a["out"]))
    db = _tree_digest(Path(b["out"]))
    assert da == db
    assert sorted(da) == ["heightmaps/T-S01_L000.npy", "heightmaps/T-S01_L001.npy", "heightmaps/T-S01_post.npy",
                          "sim_plan.json", "truth_shape.json"]
    # 다른 시드 → 다른 값은 test_zaxis_seeded_and_off (Z축 무작위) · 명령 ⑥ (캠페인 전체 지문)으로 봄 (시험 시간)
    with pytest.raises(FileExistsError):
        run_shape_campaign(cfg, camp, 20261029, tmp_path / "a")


def test_print_layers_rule():
    from cvlab.sim.campaign import resolve_layers
    assert resolve_layers({"print_layers": "all"}, 3) == [0, 1, 2]
    assert resolve_layers({"print_layers": 2}, 10) == [0, 1]
    for bad in (0, 11, [0, 2], True):
        with pytest.raises(ValueError):
            resolve_layers({"print_layers": bad}, 10)


def test_sim_imports_no_processing_package():
    bad = re.compile(r"cvlab\.(triangulation|region|calibration|heightmap|preprocess|registration)|"
                     r"from\s+\.\.\s*(triangulation|region)")
    files = list((ROOT / "src" / "cvlab" / "sim").glob("*.py")) + [ROOT / "scripts" / "sim_generate.py"]
    hits = [f.name for f in files if bad.search(f.read_text(encoding="utf-8"))]
    assert hits == []


def test_no_eval_seed_in_repo_files():
    pat = re.compile(r"CVLAB_EVAL_SEED *= *[0-9]|eval_seed *: *[0-9]")
    paths = list((ROOT / "src" / "cvlab" / "sim").glob("*.py")) + list(SIM_CONFIG_DIR.glob("*.yaml"))
    assert [p.name for p in paths if pat.search(p.read_text(encoding="utf-8"))] == []


def test_sm2_subset_plate20_matches_t5():
    cfg = load_default()
    cfg["specimens"] = {"plate20": cfg["specimens"]["plate20"]}
    from cvlab.sim import campaign as cm
    scen = cm.load_scenarios()["scenarios"]
    pick = ["NOM-P00", "OFS-B01", "OFS-B02", "MSL-F01"]
    spec = cm.load_specimen(cfg, "plate20")
    truth = cm.simulate_specimen(spec, cfg, [scen[n]["print_error_params"] for n in pick])
    exp = [e for e in expected_rows() if e["specimen"] == "plate20" and e["scenario"] in pick]
    rep = compare_sm2(truth, exp)
    assert rep["match"] == rep["rows"] == 4 and rep["max_pass_pct_diff"] < 1e-3


def test_compare_sm2_reports_mismatch():
    exp = [{"scenario": "A", "specimen": "p", "step_gauge": "off", "truth_pass_pct": "100.0", "truth_judgement": "pass"},
           {"scenario": "B", "specimen": "p", "step_gauge": "off", "truth_pass_pct": "10.0", "truth_judgement": "fail"}]
    truth = [{"scenario": "A", "specimen": "p", "pass_pct": 90.0, "judgement": "fail"}]
    rep = compare_sm2(truth, exp)
    assert rep["match"] == 0 and rep["mismatch"][0][:2] == ["A", "p"] and rep["missing"] == [["B", "p", "off"]]
