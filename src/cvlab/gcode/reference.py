"""G3 · 층별 정답 높이 지도 (RefStack).

층 n 발자국 = 층 n 압출 선분마다 캡슐 (칸 중심까지 거리 ≤ w/2 + 1e-9 mm) 안의 칸.
꼭대기 층 L_n(x, y) = max{k ≤ n : 발자국_k ∋ (x, y)},  Z_ref = z[L_n] (flat), 없으면 NaN.
층마다 발자국을 np.packbits로 저장하고 높이는 그때 계산한다.
스커트·브림·서포트도 넣는다 (판정에서 빼는 일은 G4 · T4b). PRIME (첫 층 표시 앞 퍼지선)은 층이 없어 빠진다.
"""
from __future__ import annotations

import json

import numpy as np

from .bead import effective_width
from .grid import make_grid
from .params import GCodeError, GCodeParams

_RANK = {"FILL": 0, "SKIN": 1, "WALL-INNER": 2, "WALL-OUTER": 3}  # 그 밖 (스커트·서포트 등) = 4, 뒤가 이김
_EPS = 1e-9


def capsule_window(grid: dict, x0, y0, x1, y1, r):
    """선분 캡슐이 덮는 칸: (iy 슬라이스, ix 슬라이스, bool 마스크)."""
    res, gx0, gy0 = grid["res_mm"], grid["x0_mm"], grid["y0_mm"]
    ixa = max(int(np.floor((min(x0, x1) - r - gx0) / res)) - 1, 0)
    ixb = min(int(np.ceil((max(x0, x1) + r - gx0) / res)) + 1, grid["nx"] - 1)
    iya = max(int(np.floor((min(y0, y1) - r - gy0) / res)) - 1, 0)
    iyb = min(int(np.ceil((max(y0, y1) + r - gy0) / res)) + 1, grid["ny"] - 1)
    if ixa > ixb or iya > iyb:
        return None
    xs = gx0 + np.arange(ixa, ixb + 1) * res
    ys = gy0 + np.arange(iya, iyb + 1) * res
    X, Y = np.meshgrid(xs, ys)
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    if L2 > 0:
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0.0, 1.0)
    else:
        t = 0.0
    d2 = (X - (x0 + t * dx)) ** 2 + (Y - (y0 + t * dy)) ** 2
    return slice(iya, iyb + 1), slice(ixa, ixb + 1), d2 <= (r + _EPS) ** 2


def capsule_cells(grid: dict, x0, y0, x1, y1, r):
    """capsule_window와 같은 칸을 (iy, ix) 첨자 배열로 돌려줌 (G-2 빠른 판).

    capsule_window의 창 안에서, 행마다 캡슐이 닿을 수 있는 x 범위 (여유 2칸 + 앞뒤 1칸)만 계산한다.
    칸 좌표·t·거리 식은 capsule_window와 글자 그대로 같아 결과가 비트 단위로 같다
    (시험 test_band_equals_window_*). 대각 25 mm 선분에서 보는 칸이 약 150만 → 약 7만.
    """
    res, gx0, gy0 = grid["res_mm"], grid["x0_mm"], grid["y0_mm"]
    ixa = max(int(np.floor((min(x0, x1) - r - gx0) / res)) - 1, 0)
    ixb = min(int(np.ceil((max(x0, x1) + r - gx0) / res)) + 1, grid["nx"] - 1)
    iya = max(int(np.floor((min(y0, y1) - r - gy0) / res)) - 1, 0)
    iyb = min(int(np.ceil((max(y0, y1) + r - gy0) / res)) + 1, grid["ny"] - 1)
    if ixa > ixb or iya > iyb:
        return None
    dx, dy = x1 - x0, y1 - y0
    rows = np.arange(iya, iyb + 1)
    yr = gy0 + rows * res
    R = r + 2.0 * res  # 범위 계산용 여유 (반올림 오차보다 훨씬 큼)
    if abs(dy) < 1e-12:
        ta = np.zeros(len(rows))
        tb = np.ones(len(rows))
        valid = np.ones(len(rows), bool)
    else:
        t1 = (yr - R - y0) / dy
        t2 = (yr + R - y0) / dy
        tlo, thi = np.minimum(t1, t2), np.maximum(t1, t2)
        valid = (tlo <= 1.0) & (thi >= 0.0)
        ta, tb = np.clip(tlo, 0.0, 1.0), np.clip(thi, 0.0, 1.0)
    xa, xb = x0 + ta * dx, x0 + tb * dx
    lo = np.minimum(xa, xb) - R
    hi = np.maximum(xa, xb) + R
    ia = np.maximum(np.floor((lo - gx0) / res).astype(np.int64) - 1, ixa)
    ib = np.minimum(np.ceil((hi - gx0) / res).astype(np.int64) + 1, ixb)
    cnt = np.where(valid, np.maximum(ib - ia + 1, 0), 0)
    total = int(cnt.sum())
    if total == 0:
        return np.zeros(0, np.int64), np.zeros(0, np.int64)
    start = np.cumsum(cnt) - cnt
    iy = np.repeat(rows, cnt)
    ix = np.arange(total) - np.repeat(start, cnt) + np.repeat(ia, cnt)
    # ---- 여기부터 capsule_window와 같은 식
    X = gx0 + ix * res
    Y = gy0 + iy * res
    L2 = dx * dx + dy * dy
    if L2 > 0:
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0.0, 1.0)
    else:
        t = 0.0
    d2 = (X - (x0 + t * dx)) ** 2 + (Y - (y0 + t * dy)) ** 2
    m = d2 <= (r + _EPS) ** 2
    return iy[m], ix[m]


def segment_widths(result, params: GCodeParams) -> np.ndarray:
    """압출 선분 (층 ≥ 0)마다 선폭. 머리말 명목값 → config → (extrusion 모델이면 w_eff 우선)."""
    seg = result.extrusions()
    hw = result.header.get("line_widths") or {}
    default = hw.get("DEFAULT", params.line_width_mm)
    out = np.empty(len(seg))
    for i, (t, li) in enumerate(zip(seg["type"], seg["layer_idx"])):
        w = None
        if li == 0 and "FIRST_LAYER" in hw:
            w = hw["FIRST_LAYER"]
        if w is None:
            w = hw.get(t)
        if w is None:
            w = default
        if w is None:
            raise GCodeError("선폭을 모름: 머리말에 없고 config line_width_mm도 비어 있음")
        out[i] = w
    if params.width_model == "extrusion":
        d = result.header.get("filament_d_mm") or params.filament_diameter_mm
        weff = effective_width(seg, d, params.w_eff_min_len_mm).to_numpy()
        out = np.where(np.isfinite(weff), weff, out)
    return out


class RefStack:
    def __init__(self, grid: dict, z_layers, packed: list, type_codes: list, type_names: list):
        self.grid = dict(grid)
        self.z_layers = np.asarray(z_layers, float)
        self._packed = packed
        self._type_codes = type_codes
        self.type_names = list(type_names)
        self._shape = (grid["ny"], grid["nx"])

    @property
    def n_layers(self) -> int:
        return len(self.z_layers)

    def _check(self, n: int) -> None:
        if not (0 <= n < self.n_layers):
            raise IndexError(f"층 번호 {n} 범위 밖 (0–{self.n_layers - 1})")

    def footprint(self, n: int) -> np.ndarray:
        self._check(n)
        size = self._shape[0] * self._shape[1]
        return np.unpackbits(self._packed[n], count=size).astype(bool).reshape(self._shape)

    def top_layer_at(self, n: int) -> np.ndarray:
        self._check(n)
        top = np.full(self._shape, -1, dtype=np.int32)
        for k in range(n + 1):
            top[self.footprint(k)] = k
        return top

    def height_at_layer(self, n: int) -> np.ndarray:
        top = self.top_layer_at(n)
        h = np.full(self._shape, np.nan)
        m = top >= 0
        h[m] = self.z_layers[top[m]]
        return h

    def type_at(self, n: int) -> np.ndarray:
        """꼭대기 층의 경로 종류 코드 (self.type_names 번호), 없으면 −1."""
        self._check(n)
        out = np.full(self._shape[0] * self._shape[1], -1, dtype=np.int16)
        for k in range(n + 1):
            idx = np.flatnonzero(self.footprint(k).ravel())
            out[idx] = self._type_codes[k]
        return out.reshape(self._shape)

    def save(self, path) -> None:
        sizes = np.array([len(c) for c in self._type_codes], dtype=np.int64)
        np.savez_compressed(
            path,
            grid=np.array(json.dumps(self.grid)),
            z_layers=self.z_layers,
            packed=np.stack(self._packed) if self._packed else np.zeros((0, 0), np.uint8),
            type_codes=np.concatenate(self._type_codes) if self._type_codes else np.zeros(0, np.int16),
            type_sizes=sizes,
            type_names=np.array(json.dumps(self.type_names)),
        )

    @classmethod
    def load(cls, path) -> "RefStack":
        with np.load(path, allow_pickle=False) as d:
            grid = json.loads(str(d["grid"]))
            sizes = d["type_sizes"]
            codes = np.split(d["type_codes"], np.cumsum(sizes)[:-1]) if len(sizes) else []
            packed = [row.copy() for row in d["packed"]]
            return cls(grid, d["z_layers"], packed, [c.copy() for c in codes], json.loads(str(d["type_names"])))


def build_reference(result, grid: dict | None = None, params: GCodeParams | None = None,
                    method: str = "band") -> RefStack:
    """정답 지도. method="band" (기본, 빠른 판 capsule_cells) · "window" (1차 판 capsule_window, 대조용)."""
    if method not in ("band", "window"):
        raise ValueError(f"method는 band 또는 window: {method}")
    p = params or result.params or GCodeParams()
    seg = result.extrusions()
    if seg.empty:
        raise GCodeError("층에 든 압출이 없어 정답 지도를 만들 수 없음")
    widths = segment_widths(result, p)
    if grid is None:
        xs = np.concatenate([seg.x0_mm, seg.x1_mm])
        ys = np.concatenate([seg.y0_mm, seg.y1_mm])
        grid = make_grid(xs.min(), xs.max(), ys.min(), ys.max(), p.grid_res_mm, p.grid_margin_mm)
    shape = (grid["ny"], grid["nx"])
    z_layers = result.layers["layer_z_mm"].to_numpy(float)
    type_names = sorted(set(seg["type"]), key=lambda t: (_RANK.get(t, 4), t))
    code_of = {t: i for i, t in enumerate(type_names)}
    packed, codes = [], []
    li_all = seg["layer_idx"].to_numpy()
    for k in range(len(z_layers)):
        sel = np.flatnonzero(li_all == k)
        sk = seg.iloc[sel]
        wk = widths[sel]
        order = np.argsort([_RANK.get(t, 4) for t in sk["type"]], kind="stable")
        fp = np.zeros(shape, bool)
        tc = np.full(shape, -1, dtype=np.int16)
        cols = sk[["x0_mm", "y0_mm", "x1_mm", "y1_mm", "type"]].to_numpy()
        for j in order:
            x0, y0, x1, y1, t = cols[j]
            if method == "band":
                cells = capsule_cells(grid, float(x0), float(y0), float(x1), float(y1), wk[j] / 2.0)
                if cells is None:
                    continue
                iy, ix = cells
                fp[iy, ix] = True
                tc[iy, ix] = code_of[t]
                continue
            win = capsule_window(grid, float(x0), float(y0), float(x1), float(y1), wk[j] / 2.0)
            if win is None:
                continue
            sy, sx, m = win
            fp[sy, sx] |= m
            sub = tc[sy, sx]
            sub[m] = code_of[t]
        packed.append(np.packbits(fp.ravel()))
        codes.append(tc.ravel()[np.flatnonzero(fp.ravel())].copy())
    return RefStack(grid, z_layers, packed, codes, type_names)
