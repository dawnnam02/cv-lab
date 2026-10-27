"""층 정하기 (MF-GCD-05) 와 층 표 (GC5).

① 주석 기준: 층 표시 (`;LAYER_CHANGE`, `;LAYER:n`, `; CHANGE_LAYER`) 사이 압출의 Z
② 압출 Z 기준: 압출 선분 Z를 오름차순으로 묶음
layer_source=both 이면 둘의 층 수와 층 Z가 같아야 한다. 다르면 GCodeError.
첫 층 표시 앞의 압출 (시작 퍼지선)은 PRIME 종류, 층 -1로 두고 두 방법 모두에서 뺀다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .params import GCodeError, GCodeParams

LAYER_COLUMNS = ["layer_idx", "layer_z_mm", "layer_h_mm", "gcode_line_start", "gcode_line_end",
                 "n_extrude", "extrude_len_mm", "sum_de_mm", "types"]


def _cluster(zs: np.ndarray, tol: float) -> list[float]:
    out: list[float] = []
    for z in np.sort(zs):
        if not out or z - out[-1] > tol:
            out.append(float(z))
    return out


def assign_layers(df: pd.DataFrame, markers: list, p: GCodeParams, warnings: list):
    tol = p.layer_z_tol_mm
    df = df.copy()
    is_ext = (df["kind"] == "extrude").to_numpy()
    has_markers = len(markers) > 0
    if has_markers:
        prime = is_ext & (df["_marker"].to_numpy() < 0)
        if prime.any():
            df.loc[prime, "type"] = "PRIME"
            warnings.append(f"첫 층 표시 앞 압출 {int(prime.sum())}개 (시작 퍼지선 등) → 종류 PRIME, 층에서 뺌")
    else:
        prime = np.zeros(len(df), bool)
    layer_ext = is_ext & ~prime
    ext = df[layer_ext]
    check = {"layers_comment": None, "layers_z": None, "z_max_diff_mm": None, "source": None}
    if ext.empty:
        warnings.append("층에 든 압출이 없음")
        return df, pd.DataFrame(columns=LAYER_COLUMNS), check

    z1 = ext["z1_mm"].to_numpy(float)
    drop = np.flatnonzero(np.diff(z1) < -tol)
    if drop.size:
        ln = int(ext["line_no"].iloc[drop[0] + 1])
        raise GCodeError(f"줄 {ln}: 압출 Z가 내려감 ({z1[drop[0]]:.4f} → {z1[drop[0] + 1]:.4f}, 순차 출력·비평면)")

    # ② 압출 Z 기준
    z_layers = _cluster(z1, tol)
    check["layers_z"] = len(z_layers)

    # ① 주석 기준
    c_layers = None
    if has_markers:
        mk = ext["_marker"].to_numpy()
        used = sorted(set(mk.tolist()))
        empty = len(markers) - len(used)
        if empty:
            warnings.append(f"압출 없는 층 표시 {empty}개 (층으로 세지 않음)")
        c_layers = []
        for m in used:
            zz = z1[mk == m]
            if zz.max() - zz.min() > tol:
                ln = int(ext["line_no"][mk == m].iloc[0])
                raise GCodeError(f"층 표시 줄 {markers[m][0]}: 한 층 안 압출 Z가 둘 이상 "
                                 f"({zz.min():.4f}–{zz.max():.4f}, 첫 압출 줄 {ln}, 나선·비평면)")
            c_layers.append((m, float(zz.min()), markers[m][1]))
        check["layers_comment"] = len(c_layers)
        diffs = [abs(cz - z) for _, z, cz in c_layers if cz is not None]
        check["z_max_diff_mm"] = float(max(diffs)) if diffs else None

    src = p.layer_source
    if src == "both":
        if c_layers is None:
            warnings.append("층 표시 없음 → 압출 Z 기준만 씀")
            use = "z"
        else:
            cz = [z for _, z, _ in c_layers]
            if len(cz) != len(z_layers):
                raise GCodeError(f"층 수 불일치: 주석 {len(cz)} · 압출 Z {len(z_layers)}")
            bad = [i for i, (a, b) in enumerate(zip(cz, z_layers)) if abs(a - b) > tol]
            if bad:
                i = bad[0]
                raise GCodeError(f"층 {i} Z 불일치: 주석 층 {cz[i]:.4f} · 압출 Z {z_layers[i]:.4f}")
            if check["z_max_diff_mm"] is not None and check["z_max_diff_mm"] > tol:
                raise GCodeError(f"주석 Z와 압출 Z 차 {check['z_max_diff_mm']:.5f} mm > {tol}")
            use = "comment"
    elif src == "comment":
        if c_layers is None:
            raise GCodeError("layer_source=comment 인데 층 표시가 없음")
        warnings.append("layer_source=comment: 압출 Z 대조를 하지 않음")
        use = "comment"
    else:
        warnings.append("layer_source=z: 주석 대조를 하지 않음")
        use = "z"
    check["source"] = use

    layer_idx = np.full(len(df), -1, dtype=np.int64)
    pos_ext = np.flatnonzero(layer_ext)
    if use == "comment":
        order = {m: i for i, (m, _, _) in enumerate(c_layers)}
        li = np.array([order[m] for m in ext["_marker"].to_numpy()], dtype=np.int64)
        zl = [z for _, z, _ in c_layers]
        # 주석 층 Z가 오름차순인지 (같은 Z로 표시가 나뉘면 층 수가 압출 Z와 달라 위에서 걸림)
        if any(b - a <= tol for a, b in zip(zl, zl[1:])):
            raise GCodeError("주석 층 Z가 오름차순이 아님")
    else:
        zl = z_layers
        edges = np.array(zl)
        li = np.searchsorted(edges + tol, z1, side="left").astype(np.int64)
    spread = np.abs(z1 - np.asarray(zl)[li])
    if np.any(spread > tol):
        j = int(np.argmax(spread))
        raise GCodeError(f"줄 {int(ext['line_no'].iloc[j])}: 한 층 안 압출 Z가 둘 이상 (차 {spread[j]:.5f} mm)")
    layer_idx[pos_ext] = li
    n = len(zl)

    lines_all = df["line_no"].to_numpy()
    ext_lines = ext["line_no"].to_numpy()
    first_ext = np.array([ext_lines[li == k].min() for k in range(n)])
    last_ext = np.array([ext_lines[li == k].max() for k in range(n)])
    starts = np.zeros(n, dtype=np.int64)
    if use == "comment":
        mlines = np.array([m[0] for m in markers])
        for k, (m, _, _) in enumerate(c_layers):
            lo = last_ext[k - 1] if k > 0 else -1
            cand = mlines[(mlines > lo) & (mlines <= markers[m][0])]
            starts[k] = int(cand.min())
    else:
        zmov = df[(df["z1_mm"] != df["z0_mm"]) & np.isfinite(df["z1_mm"]) & (df["line_no"] < first_ext[0])]
        starts[0] = int(zmov["line_no"].max()) if len(zmov) else 1
        for k in range(1, n):
            starts[k] = last_ext[k - 1] + 1
    ends = np.append(starts[1:] - 1, last_ext[-1])
    if np.any(starts > first_ext) or np.any(ends < last_ext):
        raise GCodeError("층 줄 범위 계산 오류 (압출이 범위 밖)")

    # 압출이 아닌 선분도 줄 범위로 층 번호를 붙임 (PRIME은 -1 유지)
    other = ~layer_ext & ~prime
    k_of = np.searchsorted(starts, lines_all[other], side="right") - 1
    inside = (k_of >= 0) & (lines_all[other] <= ends[np.clip(k_of, 0, n - 1)])
    layer_idx[np.flatnonzero(other)] = np.where(inside, k_of, -1)
    df["layer_idx"] = layer_idx

    rows = []
    e_all = df[layer_ext]
    for k in range(n):
        ek = e_all[layer_idx[layer_ext] == k]
        rows.append({
            "layer_idx": k,
            "layer_z_mm": zl[k],
            "layer_h_mm": round(zl[k] - (zl[k - 1] if k > 0 else 0.0), 10),  # 부동소수 잡음 제거
            "gcode_line_start": int(starts[k]),
            "gcode_line_end": int(ends[k]),
            "n_extrude": int(ek["line_no"].nunique()),
            "extrude_len_mm": float(ek["length_mm"].sum()),
            "sum_de_mm": float(ek["de_mm"].sum()),
            "types": ";".join(sorted(set(ek["type"]))),
        })
    return df, pd.DataFrame(rows, columns=LAYER_COLUMNS), check
