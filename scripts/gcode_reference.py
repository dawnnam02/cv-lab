"""G코드 파일 하나 → 요약 한 줄 (SUMMARY {json}) + (선택) 층 표 CSV · 정답 지도 npz · 그림.

예) PYTHONPATH=src python scripts/gcode_reference.py file.gcode --summary --out $TEMP/t4a_out --csv --npz --png
출력 폴더가 후보 폴더 (읽기 전용) 안이면 거부한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cvlab.gcode import GCodeError, GCodeParams, build_reference, parse_file  # noqa: E402
from cvlab.gcode.grid import extent  # noqa: E402

FORBIDDEN_OUT = os.path.join(ROOT, "data", "gcode_candidates")  # 쓰기 거부 (읽기 전용 후보 폴더)


def out_is_forbidden(out_dir: str) -> bool:
    a = os.path.normcase(os.path.realpath(out_dir))
    b = os.path.normcase(os.path.realpath(FORBIDDEN_OUT))
    return a == b or a.startswith(b + os.sep)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("gcode")
    ap.add_argument("--summary", action="store_true", help="SUMMARY {json} 한 줄 출력")
    ap.add_argument("--out", default=None, help="출력 폴더")
    ap.add_argument("--csv", action="store_true", help="층 표 CSV")
    ap.add_argument("--npz", action="store_true", help="정답 지도 npz")
    ap.add_argument("--png", action="store_true", help="첫·가운데·마지막 층 정답 지도 그림")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "gcode.yaml"))
    ap.add_argument("--allow", action="append", default=[], metavar="NAME=이유",
                    help="허용 목록에 더함 (이유 필수)")
    ap.add_argument("--line-width", type=float, default=None, help="머리말에 선폭이 없을 때")
    ap.add_argument("--res", type=float, default=None, help="격자 칸 크기 mm (기본 config)")
    a = ap.parse_args(argv)

    if a.out and out_is_forbidden(a.out):
        print("오류: 출력 폴더가 읽기 전용 후보 폴더 안입니다. 다른 곳을 고르세요.", file=sys.stderr)
        return 2
    p = GCodeParams.from_yaml(a.config)
    allow = list(p.allow_commands)
    for item in a.allow:
        name, sep, reason = item.partition("=")
        if not sep or not reason.strip():
            print(f"오류: --allow {item} 에 이유가 없음 (NAME=이유)", file=sys.stderr)
            return 2
        allow.append({"name": name.strip(), "reason": reason.strip()})
    p.allow_commands = allow
    if a.line_width is not None:
        p.line_width_mm = a.line_width
    if a.res is not None:
        p.grid_res_mm = a.res
    p.validate()

    t0 = time.perf_counter()
    try:
        r = parse_file(a.gcode, p)
    except GCodeError as e:
        print(f"GCodeError: {e}")
        return 1
    parse_s = time.perf_counter() - t0
    s = r.summary()
    s["parse_s"] = round(parse_s, 3)
    s["file"] = os.path.basename(a.gcode)
    if a.summary:
        print("SUMMARY " + json.dumps(s, ensure_ascii=False))

    if a.out and (a.csv or a.npz or a.png):
        os.makedirs(a.out, exist_ok=True)
        stem = os.path.splitext(os.path.basename(a.gcode))[0]
        if a.csv:
            r.layers.to_csv(os.path.join(a.out, f"{stem}_layers.csv"), index=False, encoding="utf-8")
        if a.npz or a.png:
            try:
                ref = build_reference(r, params=p)
            except GCodeError as e:
                print(f"GCodeError: {e}")
                return 1
            if a.npz:
                ref.save(os.path.join(a.out, f"{stem}_ref.npz"))
            if a.png:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt

                n = ref.n_layers
                picks = sorted({0, n // 2, n - 1})
                fig, axes = plt.subplots(1, len(picks), figsize=(4.2 * len(picks), 4), squeeze=False)
                for ax, k in zip(axes[0], picks):
                    im = ax.imshow(ref.height_at_layer(k), origin="lower", extent=extent(ref.grid),
                                   interpolation="nearest")
                    ax.set_title(f"layer {k} (Z {ref.z_layers[k]:.3f} mm)")
                    ax.set_xlabel("X {G} mm")
                    ax.set_ylabel("Y {G} mm")
                    fig.colorbar(im, ax=ax, shrink=0.8, label="Z_ref mm")
                fig.tight_layout()
                fig.savefig(os.path.join(a.out, f"{stem}_ref.png"), dpi=110)
                plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
