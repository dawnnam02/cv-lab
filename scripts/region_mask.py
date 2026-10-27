"""G코드 파일 하나 → 판정 영역 요약 한 줄 (REGION {json}) · 식힘 비교 영역 한 줄 (POST {json}) + (선택) 층별 표 CSV · 처리안 표 · 영역 npz · 그림.

예) PYTHONPATH=src python scripts/region_mask.py file.gcode --summary --out results/region_t4b --csv --npz --png
출력 폴더 기본 results/region_t4b/ (Git 밖). data/ 아래 쓰기는 거부한다.
측정값은 받지 않는다 (G코드 · 정답 지도 · 설정만, MF-JDG-03).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from fractions import Fraction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

FORBIDDEN_OUT = os.path.join(ROOT, "data")
SUMMARY_KEYS = ["file", "gcode_sha256", "layers", "grid_ny_nx", "passes", "band_mm", "step_mm", "camera_side",
                "dof_mm", "dof_top_mm", "region_pct_total", "region_cells_cell02_total", "depth_layers",
                "last_layer_depth_pct_object", "coverage_final_top_pct", "build_s"]
# 주 코드 그림 색 (dataviz 기본 범주 팔레트 순서). 0 = 영역
CODE_COLORS = {0: "#d9d9d6", 1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a", 4: "#eda100", 5: "#ffffff", 6: "#6250d6"}
CODE_LABELS = {0: "판정 영역", 1: "1 엣지 띠", 2: "2 가림 예측", 3: "3 시야 밖", 4: "4 제외 종류·PRIME",
               5: "5 출력물 없음", 6: "6 심도 밖"}
POST_KEYS = ["post_rule", "post_band_mm", "post_delta_t_c", "post_n_region", "post_region_cell02",
             "post_region_cell04"]


def out_is_forbidden(out_dir: str) -> bool:
    a = os.path.normcase(os.path.realpath(out_dir))
    b = os.path.normcase(os.path.realpath(FORBIDDEN_OUT))
    return a == b or a.startswith(b + os.sep)


def summary_line(path, rs) -> dict:
    s = rs.summary()
    st = rs.layer_stats()
    tot = s.iloc[-1]
    last = st[-1]
    info = rs.info
    return {
        "file": os.path.basename(path),
        "gcode_sha256": info["gcode_sha256"],
        "layers": rs.n_layers,
        "grid_ny_nx": [rs.grid["ny"], rs.grid["nx"]],
        "passes": {"x": info["passes_xy"][0], "y": info["passes_xy"][1], "total": info["n_passes"]},
        "band_mm": round(info["band_mm"], 6),
        "step_mm": round(info["step_mm"], 6),
        "camera_side": info["camera_side"],
        "dof_mm": info["dof_mm"],
        "dof_top_mm": info["dof_top_mm"],
        "region_pct_total": round(float(tot.region_pct), 3),
        "region_cells_cell02_total": int(tot.n_region_cell02),
        "depth_layers": sum(1 for x in st if x["n_depth_object"] > 0),
        "last_layer_depth_pct_object": round(100.0 * last["n_depth_object"] / last["n_object"], 3)
        if last["n_object"] else 0.0,
        "coverage_final_top_pct": round(info["coverage_final_top_pct"], 3),
        "build_s": info["build_s"],
    }


def plan_extra(rs) -> dict:
    """처리안 비교 합계: A안 덮임률, B안 되찾는 칸 비율, 추가 시간."""
    t = rs.depth_plan()
    tot = t.iloc[-1]
    st = rs.layer_stats()
    nd = sum(s["n_depth_object"] for s in st)
    no = sum(s["n_object"] for s in st)
    return {"A_coverage_final_top_pct": round(rs.info["coverage_final_top_pct"], 3),
            "depth_cells_object": nd, "object_cells": no,
            "depth_pct_object_all_layers": round(100.0 * nd / no, 3) if no else 0.0,
            "B_recover_cells": int(tot.recover_cells_B),
            "B_recover_pct_of_depth": round(100.0 * tot.recover_cells_B / nd, 3) if nd else 0.0,
            "B_recover_pct_of_object": round(100.0 * tot.recover_cells_B / no, 3) if no else 0.0,
            "B_max_heights": int(tot.n_heights),
            "B_layers_needing_split": int((t.n_heights.iloc[:-1] > 1).sum()),
            "B_extra_s": round(float(tot.extra_scan_s_B), 1),
            "B_extra_min": round(float(tot.extra_scan_s_B) / 60.0, 2)}


def save_png(rs, ref, path_png, layer):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    from matplotlib.patches import Patch
    import numpy as np

    from cvlab.gcode.grid import extent
    from cvlab.region import REASON_BITS

    for fam in ("Malgun Gothic", "NanumGothic"):
        try:
            matplotlib.font_manager.findfont(fam, fallback_to_default=False)
            plt.rcParams["font.family"] = fam
            break
        except Exception:
            pass
    plt.rcParams["axes.unicode_minus"] = False
    codes = [0, 1, 2, 3, 4, 5, 6]
    idx = {c: i for i, c in enumerate(codes)}
    code = rs.exclusion_code(layer)
    img = np.vectorize(idx.get)(code)
    cmap = ListedColormap([CODE_COLORS[c] for c in codes])
    norm = BoundaryNorm(np.arange(len(codes) + 1) - 0.5, len(codes))
    bits = rs.reasons(layer)
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), constrained_layout=True)
    h = ref.height_at_layer(layer)
    ext = extent(rs.grid)
    im = axes[0].imshow(h, origin="lower", extent=ext, cmap="Blues")
    fig.colorbar(im, ax=axes[0], shrink=0.7, label="정답 높이 mm")
    axes[0].set_title(f"층 {layer} 정답 높이 (Z {rs.z_layers[layer]:.2f})")
    axes[1].imshow(img, origin="lower", extent=ext, cmap=cmap, norm=norm, interpolation="nearest")
    axes[1].set_title("주 코드 (T15)")
    axes[1].legend(handles=[Patch(facecolor=CODE_COLORS[c], edgecolor="#888", label=CODE_LABELS[c]) for c in codes],
                   loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8, frameon=False)
    # 겹친 이유: 심도 · 가림 · 엣지를 RGB로
    rgb = np.ones(code.shape + (3,))
    for name, col in (("edge", (0.16, 0.47, 0.84)), ("occlusion", (0.92, 0.41, 0.20)), ("depth", (0.38, 0.31, 0.84))):
        m = (bits & REASON_BITS[name]) > 0
        rgb[m] = rgb[m] * 0.45 + np.array(col) * 0.55
    rgb[(bits & REASON_BITS["no_material"]) > 0] = 1.0
    axes[2].imshow(rgb, origin="lower", extent=ext, interpolation="nearest")
    axes[2].set_title("이유 비트 겹침 (엣지 파랑 · 가림 주황 · 심도 보라)")
    for p in rs.passes:
        for ax in axes[1:]:
            ax.add_patch(matplotlib.patches.Rectangle((p["x0_mm"], p["y0_mm"]), p["x1_mm"] - p["x0_mm"],
                                                      p["y1_mm"] - p["y0_mm"], fill=False, ec="#444", lw=1, ls="--"))
    for ax in axes:
        ax.set_xlabel("X mm {G}")
        ax.set_ylabel("Y mm {G} (스캔 방향)")
    fig.savefig(path_png, dpi=110)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("gcode")
    ap.add_argument("--summary", action="store_true", help="REGION {json} 한 줄 출력")
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "region_t4b"), help="출력 폴더")
    ap.add_argument("--csv", action="store_true", help="층별 표 · 처리안 표 CSV")
    ap.add_argument("--npz", action="store_true", help="영역 npz (RegionStack.save)")
    ap.add_argument("--png", action="store_true", help="마지막 층 (또는 --layer) 코드 · 비트 그림")
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--plan", action="store_true", help="처리안 합계 PLAN {json} 한 줄")
    ap.add_argument("--sens", action="store_true", help="민감도 (dof_top ±1, 띠 폭, camera_side) SENS 줄")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "region.yaml"))
    ap.add_argument("--gcode-config", default=os.path.join(ROOT, "config", "gcode.yaml"))
    ap.add_argument("--line-width", type=float, default=None, help="머리말에 선폭이 없을 때")
    ap.add_argument("--camera-side", default=None)
    ap.add_argument("--dof-top", type=float, default=None)
    a = ap.parse_args(argv)

    if out_is_forbidden(a.out):
        print("오류: 출력 폴더가 data/ 아래입니다. results/ 등 다른 곳을 고르세요.", file=sys.stderr)
        return 2
    # 무거운 import (numpy · scipy · pandas)는 쓰기 거부 확인 뒤
    from cvlab.gcode import GCodeError, GCodeParams, build_reference, parse_file
    from cvlab.region import RegionParams, aligned_grid, build_region, object_bbox
    try:
        gp = GCodeParams.from_yaml(a.gcode_config)
        rp = RegionParams.from_yaml(a.config)
        if Fraction(str(gp.grid_res_mm)) != Fraction(str(rp.res_mm)):
            raise ValueError(f"config/region.yaml res_mm {rp.res_mm} ≠ config/gcode.yaml grid_res_mm {gp.grid_res_mm}")
        if a.line_width is not None:
            gp.line_width_mm = a.line_width
            gp.validate()
        over = {}
        if a.camera_side is not None:
            over["camera_side"] = a.camera_side
        if a.dof_top is not None:
            over["dof_top_mm"] = a.dof_top
        if over:
            rp = RegionParams.from_dict({**rp.to_dict(), **over})
        t0 = time.perf_counter()
        r = parse_file(a.gcode, gp)
        g = aligned_grid(*object_bbox(r, rp.exclude_types), res_mm=rp.res_mm, cell_mm=rp.cell_mm,
                         margin_mm=rp.margin_mm)
        ref = build_reference(r, grid=g)
        t_ref = time.perf_counter() - t0
        rs = build_region(r, ref, rp)
    except (GCodeError, ValueError, OSError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    stem = os.path.splitext(os.path.basename(a.gcode))[0].replace(" ", "_")
    wants_files = a.csv or a.npz or a.png or a.sens
    if wants_files:
        os.makedirs(a.out, exist_ok=True)
    if a.summary:
        print("REGION " + json.dumps(summary_line(a.gcode, rs), ensure_ascii=False))
        # 식힌 재측정 비교 영역 (R-2). REGION 줄 키는 고정이라 따로 한 줄
        print("POST " + json.dumps({k: rs.info[k] for k in POST_KEYS}, ensure_ascii=False))
    print(f"# 정답 지도 {t_ref:.1f} s, 판정 영역 {rs.info['build_s']:.1f} s, 격자 {g['ny']} × {g['nx']}, "
          f"PRIME {rs.info['prime']}", file=sys.stderr)
    if a.plan:
        print("PLAN " + json.dumps(plan_extra(rs), ensure_ascii=False))
    if a.csv:
        rs.summary().to_csv(os.path.join(a.out, f"{stem}_layers.csv"), index=False, encoding="utf-8")
        rs.depth_plan().to_csv(os.path.join(a.out, f"{stem}_depth_plan.csv"), index=False, encoding="utf-8")
    if a.npz:
        rs.save(os.path.join(a.out, f"{stem}_region.npz"))
    if a.png:
        layer = rs.n_layers - 1 if a.layer is None else a.layer
        save_png(rs, ref, os.path.join(a.out, f"{stem}_L{layer:03d}.png"), layer)
    if a.sens:
        rows = []
        base = rp.to_dict()
        cases = [("dof_top_mm", -1.0), ("dof_top_mm", 1.0), ("edge_band_mm", 0.15), ("edge_band_mm", 0.25),
                 ("edge_band_mm", 0.35), ("camera_side", "+y"), ("camera_side", "-y")]
        for k, v in cases:
            rsk = build_region(r, ref, RegionParams.from_dict({**base, k: v}))
            d = summary_line(a.gcode, rsk)
            row = {"key": k, "value": v, "region_pct_total": d["region_pct_total"],
                   "region_cells_cell02_total": d["region_cells_cell02_total"], "depth_layers": d["depth_layers"],
                   "last_layer_depth_pct_object": d["last_layer_depth_pct_object"],
                   "coverage_final_top_pct": d["coverage_final_top_pct"], "build_s": d["build_s"]}
            rows.append(row)
            print("SENS " + json.dumps(row, ensure_ascii=False))
        import csv
        with open(os.path.join(a.out, f"{stem}_sens.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
