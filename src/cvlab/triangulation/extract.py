"""레이저 선 서브픽셀 중심 추출 (F1, T7a 1차).

영상 규칙: img[v, u] (행 = v, 열 = u). 레이저 선은 대략 가로로 놓이므로 열마다 v 하나.
결과 v는 ROI 행 좌표 (float32, 못 찾으면 NaN). 전체 행 좌표는 `roi_to_full`.
방법과 식: docs/레이저선-추출.md §2. 이 모듈은 단순 합성 영상으로만 시험했습니다.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter

from . import _core
from .params import METHODS, TriParams
from .quality import FLAG

__all__ = ["METHODS", "extract_centers", "roi_to_full"]


def roi_to_full(v, roi_y0_px) -> np.ndarray:
    """ROI 행 좌표 → 전체 영상 행 좌표 (v + roi_y0, 명세 1절 `frame.roi_y0_px`)."""
    return (np.asarray(v, dtype=np.float64) + float(roi_y0_px)).astype(np.float32)


def _guided_peaks(f, p0, valid0, win, band):
    """연속성 안내: 1차 최대 행을 51열 중앙값 필터로 매끄럽게 한 안내선 ± band 안에서 다시 최대."""
    H, W = f.shape
    cols = np.arange(W)
    pv = p0.astype(np.float64)
    if not valid0.all():                       # 선이 없는 열은 이웃 유효 열로 메움 (안내선이 잡음에 끌리지 않게)
        pv = np.interp(cols, cols[valid0], pv[valid0])
    guide = np.rint(median_filter(pv, size=int(win), mode="nearest")).astype(np.int64)
    rows = guide[None, :] + np.arange(-int(band), int(band) + 1)[:, None]
    inb = (rows >= 0) & (rows < H)
    vals = np.where(inb, _core.gather(f, rows), -np.inf)
    return rows[vals.argmax(axis=0), cols]


def _wls_quadratic(x, y, w):
    """열마다 가중 최소제곱 y ≈ c0 + c1 x + c2 x² 의 꼭짓점 −c1/(2 c2). c2 ≥ 0이면 NaN."""
    s = [(w * x ** k).sum(axis=0) for k in range(5)]
    t = [(w * x ** k * y).sum(axis=0) for k in range(3)]
    A = np.stack([np.stack([s[0], s[1], s[2]], -1), np.stack([s[1], s[2], s[3]], -1),
                  np.stack([s[2], s[3], s[4]], -1)], -2)
    b = np.stack(t, -1)
    ok = (w > 0).sum(axis=0) >= 3
    A[~ok] = np.eye(3)
    b[~ok] = 0.0
    det = np.linalg.det(A)
    ok &= np.abs(det) > 1e-12
    A[~ok] = np.eye(3)
    c = np.linalg.solve(A, b[..., None])[..., 0]
    with np.errstate(invalid="ignore", divide="ignore"):
        x0 = -c[:, 1] / (2 * c[:, 2])
    x0[~ok | ~(c[:, 2] < 0)] = np.nan
    return x0


def _analyze(img, params, background, bit_depth):
    a = _core.as_image(img)
    sat = _core.sat_level(a, bit_depth)
    f = a                                     # 정수 영상은 그대로 씀 (전체 실수 변환을 피해 속도). 계산은 꺼낸 띠만 실수로
    if background is not None:
        b = _core.as_image(background)
        if b.shape != a.shape:
            raise ValueError(f"background 크기 {b.shape} ≠ 영상 {a.shape}")
        f = a.astype(np.float32) - b.astype(np.float32)
    H, W = f.shape
    cols = np.arange(W)
    k = float(params.threshold_k_sigma)
    p0 = _core.argmax_rows(f)
    if params.guide_band_px is not None:
        valid0 = f[p0, cols] > _core.global_threshold(f, k)
        p = _guided_peaks(f, p0, valid0, params.guide_win_cols, params.guide_band_px) if valid0.any() else p0
    else:
        p = p0
    st = _core.column_stats(f, p, params)
    hw = st["half_win"]
    offs = np.arange(-hw, hw + 1)
    rows = p[None, :] + offs[:, None]
    inb = (rows >= 0) & (rows < H)
    vals = _core.gather(f, rows).astype(np.float64)
    satpix = (_core.gather(a, rows) >= sat) & inb
    thr = st["thr"]
    above = (vals > thr[None, :]) & inb
    no_line = above.sum(axis=0) < _core.MIN_ABOVE_PX
    w = np.where(inb, np.maximum(vals - thr[None, :], 0.0), 0.0)
    return dict(a=a, f=f, sat=sat, p=p, hw=hw, offs=offs, rows=rows, inb=inb, vals=vals,
                satpix=satpix, w=w, no_line=no_line, **st)


def _m_max(d, params):
    return d["p"].astype(np.float64)


def _m_cog(d, params):
    w = d["w"]
    s = w.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (w * d["rows"]).sum(axis=0) / s
    v[~(s > 0)] = np.nan
    return v


def _three(d, fn=None):
    """p−1, p, p+1 세 값 (실수, fn을 주면 fn(값, 행 번호 0·1·2)), 영상 끝 마스크."""
    f = d["f"]
    H = f.shape[0]
    p = d["p"]
    edge = (p == 0) | (p == H - 1)
    pc = np.clip(p, 1, H - 2)
    g = _core.gather(f, pc[None, :] + np.array([-1, 0, 1])[:, None]).astype(np.float64)
    if fn is not None:
        g = fn(g)
    return g[0], g[1], g[2], pc, edge


def _m_parabola3(d, params):
    a, b, c, pc, edge = _three(d)
    den = a - 2 * b + c
    with np.errstate(invalid="ignore", divide="ignore"):
        dv = 0.5 * (a - c) / den
    v = pc + dv
    v[edge | ~(den < 0) | ~(np.abs(dv) <= 1)] = np.nan
    return v


def _m_gauss3(d, params):
    """로그 밝기 3점 포물선. 창 안에 포화 화소가 있는 열은 포화 화소를 뺀 로그 포물선 가중 맞춤."""
    bg = d["bg"][None, :]
    la, lb, lc, pc, edge = _three(d, lambda g: np.log(np.maximum(g - bg, 0.5)))
    den = la - 2 * lb + lc
    with np.errstate(invalid="ignore", divide="ignore"):
        dv = 0.5 * (la - lc) / den
    v = pc + dv
    v[edge | ~(den < 0) | ~(np.abs(dv) <= 1)] = np.nan
    has_sat = d["satpix"].any(axis=0)
    if has_sat.any():
        y = d["vals"] - d["bg"][None, :]
        m = d["inb"] & ~d["satpix"] & (d["vals"] > d["thr"][None, :])
        yl = np.log(np.maximum(y, 0.5))
        wt = np.where(m, np.maximum(y, 0.0) ** 2, 0.0)       # var(log y) ∝ 1/y² 이라 y² 가중
        x0 = _wls_quadratic(d["offs"][:, None].astype(np.float64), yl, wt)
        vs = d["p"] + x0
        vs[~(np.abs(x0) <= d["hw"])] = np.nan
        v = np.where(has_sat, vs, v)
    return v


def _m_gaussfit(d, params):
    """창 안 가우시안 + 상수 최소제곱 (레벤버그-마쿼트, 열마다 벡터로). 포화 화소는 뺌."""
    K = max(d["hw"], 4)
    f = d["f"]
    H = f.shape[0]
    p = d["p"]
    x = np.arange(-K, K + 1, dtype=np.float64)[:, None]
    rows = p[None, :] + np.arange(-K, K + 1)[:, None]
    inb = (rows >= 0) & (rows < H)
    y = _core.gather(f, rows).astype(np.float64)
    wt = (inb & (_core.gather(d["a"], rows) < d["sat"])).astype(np.float64)
    mu0 = _m_cog(d, params) - p
    mu = np.where(np.isfinite(mu0), mu0, 0.0)
    fw = d["fwhm"]
    s = np.where(np.isfinite(fw) & (fw > 0), fw / 2.3548, 1.0)
    c = d["bg"].copy()
    A = np.maximum(d["peak"] - c, 1.0)
    ok = wt.sum(axis=0) >= 5
    lam = 1e-3
    for _ in range(int(params.gaussfit_max_iter)):
        dx = x - mu[None, :]
        e = np.exp(-dx ** 2 / (2 * s[None, :] ** 2))
        r = y - (A[None, :] * e + c[None, :])
        J = np.stack([e, A * e * dx / s ** 2, A * e * dx ** 2 / s ** 3, np.ones_like(e)], -1)  # (K, W, 4)
        Jw = J * wt[..., None]
        JTJ = np.einsum("kwi,kwj->wij", Jw, J)
        JTr = np.einsum("kwi,kw->wi", Jw, r)
        JTJ = JTJ + lam * np.einsum("wii->wi", JTJ)[..., None] * np.eye(4)[None]
        bad = ~ok | ~np.isfinite(JTJ).all(axis=(1, 2)) | (np.abs(np.linalg.det(JTJ)) < 1e-30)
        JTJ[bad] = np.eye(4)
        JTr[bad] = 0.0
        step = np.linalg.solve(JTJ, JTr[..., None])[..., 0]
        A = A + step[:, 0]
        mu = mu + step[:, 1]
        s = np.clip(s + step[:, 2], 0.3, float(K))
        c = c + step[:, 3]
        ok &= ~bad
    v = p + mu
    v[~ok | ~np.isfinite(v) | ~(np.abs(mu) <= K) | ~(A > 0)] = np.nan
    return v


def _m_steger(d, params):
    """1차원 가우시안 미분 (σ_s) 의 0 교차: t = −r'/r'' (Steger 1998의 1차원 판)."""
    ss = float(params.steger_sigma_px)
    f = d["f"]
    H, W = f.shape
    cols = np.arange(W)
    p = d["p"]
    R = int(np.ceil(4 * ss)) + 3
    rows = p[None, :] + np.arange(-R, R + 1)[:, None]
    strip = _core.gather(f, rows).astype(np.float64)
    g0 = gaussian_filter1d(strip, ss, axis=0, order=0, mode="nearest")
    g1 = gaussian_filter1d(strip, ss, axis=0, order=1, mode="nearest")
    g2 = gaussian_filter1d(strip, ss, axis=0, order=2, mode="nearest")
    j = R - 2 + g0[R - 2:R + 3].argmax(axis=0)
    d1, d2 = g1[j, cols], g2[j, cols]
    with np.errstate(invalid="ignore", divide="ignore"):
        t = -d1 / d2
    v = p + (j - R) + t
    v[~(d2 < 0) | ~(np.abs(t) <= 1)] = np.nan
    return v


_FUNCS = {"max": _m_max, "cog": _m_cog, "parabola3": _m_parabola3, "gauss3": _m_gauss3,
          "gaussfit": _m_gaussfit, "steger": _m_steger}
assert tuple(_FUNCS) == METHODS


def _flags(d, params):
    H = d["f"].shape[0]
    p, hw, nl = d["p"], d["hw"], d["no_line"]
    line = ~nl
    fl = np.zeros(p.shape, np.uint8)
    fl[nl] |= FLAG["no_line"]
    fl[line & (d["peak"] < params.low_peak_factor * d["thr"])] |= FLAG["low_peak"]
    if np.isfinite(d["fwhm_med"]):
        fl[line & (d["fwhm"] > params.wide_factor * d["fwhm_med"])] |= FLAG["wide"]
    fl[d["satpix"].any(axis=0)] |= FLAG["saturated"]
    npk = _core.count_peaks(d["f"], d["thr"])
    sec = _core.second_peak(d["f"], p, hw, cols=line & (npk >= 2))
    multi = line & (npk >= 2) & ((sec - d["bg"]) > params.multi_peak_ratio * (d["peak"] - d["bg"]))
    fl[multi] |= FLAG["multi_peak"]
    fl[line & ((p - hw < 0) | (p + hw > H - 1))] |= FLAG["edge_window"]
    return fl


def extract_centers(img, method="cog", params=None, background=None, *, bit_depth=None):
    """열마다 레이저 선 중심 행 v (서브픽셀).

    img        : [H, W] uint8 · uint16 (10 · 12비트는 아래 비트 정렬) · float. 행 = v, 열 = u.
    method     : METHODS 중 하나 ("max", "cog", "parabola3", "gauss3", "gaussfit", "steger").
    params     : TriParams (None이면 기본값 = config/triangulation.yaml). 연속성 안내는 guide_band_px.
    background : 레이저 끈 프레임 (선택). 있으면 빼고 계산.
    bit_depth  : `frame.bit_depth` (포화값 2^bit − 1). None이면 그릇으로 추정 (_core.sat_level).
    반환       : v float32[W] (ROI 행 좌표, 못 찾으면 NaN), flags uint8[W] (FLAG 비트 합).
    """
    params = params or TriParams()
    if method not in _FUNCS:
        raise ValueError(f"method={method!r}: {METHODS} 중 하나여야 함")
    d = _analyze(img, params, background, bit_depth)
    v = _FUNCS[method](d, params)
    v = np.where(d["no_line"], np.nan, v)
    return v.astype(np.float32), _flags(d, params)
