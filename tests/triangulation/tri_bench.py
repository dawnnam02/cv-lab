"""T7a 방법 비교 실행 → 방법비교.csv (pytest가 모으지 않는 이름).

단순 합성 영상 (tri_synth, T3 시뮬레이터가 아님) 으로 잰 숫자입니다. 하드웨어 성능 · C4 · C5의 증거가 아닙니다.

실행 (저장소 뿌리에서):
    PYTHONPATH=src python tests/triangulation/tri_bench.py --out docs/레이저선-추출_자료/방법비교.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tri_synth import SCENARIOS, SEED, synth  # noqa: E402

from cvlab.triangulation import METHODS, TriParams, extract_centers  # noqa: E402

COLS = ["scenario", "bit_depth", "sigma_px", "peak_dn", "method", "guided", "n_cols", "valid_pct", "fake_pct",
        "bias_px", "std_px", "rms_px", "p95_px", "max_px", "rms_um", "ms_per_frame"]
# [계산] 1 px ≈ 3 µm ÷ (배율 0.19 × sin 30°) (세부청사진 T7a §6.6, 텔레센트릭 근사)
UM_PER_PX = 3.0 / (0.19 * math.sin(math.radians(30)))
N_FRAMES = 10          # 시나리오마다 장 수 (1280열 × 10장 = 12,800점). static100은 100장
N_SPEED = 20           # 속도 시나리오 반복 수 (중앙값)


def _eval_cols(name, line_cols):
    cfg = SCENARIOS[name]
    if "reflection" in cfg:                       # 반사 시나리오는 가짜 피크가 있는 21열만 잼 (전체 열이면 P95가 가림)
        u0, u1 = cfg["reflection"][:2]
        m = np.zeros_like(line_cols)
        m[u0:u1] = True
        return m
    return line_cols


def run(out_path, n_frames=N_FRAMES):
    rows = []
    params = {1: TriParams(), 0: TriParams(guide_band_px=None)}
    for si, name in enumerate(SCENARIOS):
        cfg = SCENARIOS[name]
        speed = name.startswith("speed_")
        nf = 100 if name.startswith("static100") else (1 if speed else n_frames)
        frames = []
        for k in range(nf):
            img, vt, lc = synth(name, rng=SEED + 1000 * si + k)
            frames.append((img, vt, lc))
        bit = cfg["bit"]
        for method in METHODS:
            for g in (1, 0):
                errs, fakes, times, V = [], [], [], []
                for img, vt, lc in frames:
                    reps = N_SPEED if speed else 1
                    for _ in range(reps):
                        t0 = time.perf_counter()
                        v, fl = extract_centers(img, method, params=params[g], bit_depth=bit)
                        times.append(time.perf_counter() - t0)
                    ev = _eval_cols(name, lc)
                    errs.append((v.astype(np.float64) - vt)[ev])
                    fakes.append(np.isfinite(v[~lc]))
                    V.append(v.astype(np.float64))
                e = np.concatenate(errs)
                ok = np.isfinite(e)
                ee = e[ok]
                fk = np.concatenate(fakes)
                if name.startswith("static100"):
                    std = float(np.median(np.nanstd(np.stack(V), axis=0, ddof=1)))   # 열별 표준편차 중앙값
                else:
                    std = float(ee.std(ddof=1)) if ee.size > 1 else float("nan")
                rms = float(np.sqrt(np.mean(ee ** 2))) if ee.size else float("nan")
                rows.append(dict(
                    scenario=name, bit_depth=bit, sigma_px=cfg["sigma"], peak_dn=cfg["peak"], method=method, guided=g,
                    n_cols=int(_eval_cols(name, frames[0][2]).sum()), valid_pct=round(100 * ok.mean(), 3),
                    fake_pct=round(100 * fk.mean(), 3) if fk.size else 0.0,
                    bias_px=round(float(ee.mean()), 5) if ee.size else "", std_px=round(std, 5),
                    rms_px=round(rms, 5), p95_px=round(float(np.percentile(np.abs(ee), 95)), 5) if ee.size else "",
                    max_px=round(float(np.abs(ee).max()), 5) if ee.size else "", rms_um=round(rms * UM_PER_PX, 3),
                    ms_per_frame=round(1000 * float(np.median(times)), 2)))
        print(f"  {name}: {nf}장 끝", flush=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE.parents[1] / "docs" / "레이저선-추출_자료" / "방법비교.csv"))
    ap.add_argument("--frames", type=int, default=N_FRAMES)
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    rows = run(a.out, a.frames)
    r = [x for x in rows if x["scenario"] == "nominal_10bit" and x["guided"] == 1]
    best = min(r, key=lambda x: x["rms_px"])
    print(f"nominal_10bit 최소 RMS: {best['method']} {best['rms_px']} px "
          f"(cog {[x['rms_px'] for x in r if x['method'] == 'cog'][0]} px)")
    print(f"행 {len(rows)}개 → {a.out}")
    print(f"걸린 시간 {time.perf_counter() - t0:.1f} s (단순 합성 영상, 하드웨어 성능의 증거가 아님)")


if __name__ == "__main__":
    main()
