"""v4_analytic.py — V4 독립 검증: 판정량 Q 의 해석식(시뮬레이터와 별개 구현)과 시뮬레이션 결과 대조.

시뮬레이터(simulate.py)는 import 하지 않는다. 사양 CSV 의 숫자 해석(범위 표기 등)과 접촉식 판정만
specs.py 를 빌려 쓴다 (입력 단계). mode·배율 등급·seam 규칙은 청사진 8.1절·simulate.py 주석의
'사양'을 보고 여기서 다시 구현했다.

실행 (cv-lab 폴더):
  python docs/0_방법탐색/검증/v4_analytic.py --spec-dir <사양 CSV 폴더> --sim <시뮬레이션.csv>
      [--specs-py <specs.py 가 있는 폴더>] [--out docs/0_방법탐색/검증/v4_대조표.csv]

해석식 (보수-500 시나리오, 단위 µm)
  공통: 백색 σ_w = z/√2, 상관 σ_c = z/√2 (가우시안 필터 σ_f = 500 µm → 상관함수 exp(−d²/4σ_f²)),
        배율 u_s (calibrated 20 / industrial 100 / diy 500 / printer_axis 500 ppm),
        seam 수 n_s = ceil(40/fov) − 1 (fov < 40 mm, 래스터 점 센서·점 측정은 0),
        seam Z σ = z/√10, XY σ = max(xy_step/2, 1).
  H. 국소높이 (0.2 mm 칸, 2 × 2 mm, 칸당 점 n = (200/step)²)
        Var = σ_w²/n + σ_c²·ρ_cell + Var_seam,  ρ_cell = 칸 평균의 상관 계수(≈0.987),
        Var_seam = ½[Var(W_k − W̄) + Var(W_{k+1} − W̄)]  (W = seam 랜덤워크, k = n_s // 2)
        Q_H = 2√Var + E|치우침|  (치우침 = 50회 평균의 MC 요동)
  W. 국소선폭 (0.5 mm 구간, 구간당 단면 n_r = 500/step 줄)
     W-a (순수 해석): 흐린 단면의 반높이 기울기 s 에서
        δw = (n_L + n_R − δbase − δtop)/s,  n = 경계 위치의 잡음 (백색 σ_w²/n_r·⅔ + 상관),
        Q_Wa = 2·√Var(δw) + 2D 는 양자화만: σ = step·√(f(1−f))·√3/2, f = frac(2a′/step)
     W-b (반해석): W-a 에 결정론적 항을 더함 — 위상 40개마다 잡음 없는 단면을 표본화해
        경사·edge_loss 결측 틈을 건너는 선형 보간의 치우침·위상 분산, 보간 현의 기울기로 잡음 전파.
  L. 길이40: Q_L = 2√(2σ_e² + (40 mm·u_s)² + n_s·σ_xy²),  σ_e = step/√12 (점 측정은 z),
        래스터 점 센서는 σ_e² 에 축 위치 잡음 5² 을 더함, 점 측정은 seam 0.
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))     # cv-lab

# ---------------------------------------------------------------- 사양 상수 (청사진 4.3·9절, simulate.py 주석의 '사양')
LINE_W, LINE_ERR, LINE_H = 400.0, 40.0, 200.0
POS_X = 200.0
SEG = 500.0
CELL, FLAT = 200.0, 2000.0
FLAT_RELIEF, LINE_RELIEF = 1000.0, 200.0
SIG_F = 500.0                 # 상관 잡음 가우시안 필터 σ
CORR_FRAC = 0.5
N_MC = 50
WALL_DEG = 60.0
RASTER_JIT = 5.0
PPM = {"calibrated": 20, "industrial": 100, "diy": 500, "printer_axis": 500}
ID_CAL = {"calibrated": ["M01", "M02", "M04", "M14", "M15", "M16", "M23", "M09"],
          "industrial": ["M06", "M10", "M21"],
          "diy": ["M05", "M11", "M13", "M17", "M19", "M20", "M22", "M12"],
          "printer_axis": ["M03", "M07", "M08", "M18"]}
ACCESS_PPM = {"lab": 20, "outsource": 20, "own": 500}
ID_POINT, ID_RASTER, ID_LINEPROF = {"M01", "M04"}, {"M03", "M07", "M08"}, {"M02"}
MODES = ("area", "line_profiler", "raster_point", "point_probe", "2d", "indirect")


def fnum(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return np.nan
    return v


def resolve(row, diy_ppm=500):
    rid = str(row["id"]).upper()
    mode = str(row.get("mode", "") or "").strip().lower()
    if mode not in MODES:
        mz = fnum(row.get("measures_z"))
        mode = ("point_probe" if rid in ID_POINT else "raster_point" if rid in ID_RASTER else
                "line_profiler" if rid in ID_LINEPROF else "2d" if (np.isfinite(mz) and mz < 0.5) else "area")
    cal = str(row.get("cal_class", "") or "").strip().lower()
    if cal not in PPM:
        cal = next((c for c, ids in ID_CAL.items() if rid in ids), "")
    ppm = (diy_ppm if cal == "diy" else PPM[cal]) if cal else ACCESS_PPM.get(str(row.get("access", "")).lower(), 500)
    return mode, cal, ppm


class P:
    """해석용 사양 묶음."""

    def __init__(self, row):
        self.id = row["id"]
        self.mode, self.cal, ppm = resolve(row)
        self.us = ppm * 1e-6
        st = fnum(row.get("xy_step_um"))
        self.ok = self.mode != "indirect" and np.isfinite(st) and st > 0
        self.step_raw = st
        self.st = max(st, 2.0) if np.isfinite(st) else np.nan
        mz = fnum(row.get("measures_z"))
        zs = fnum(row.get("z_sigma_um"))
        if self.mode == "2d":
            mz = 0.0
        if not np.isfinite(mz):
            mz = 1.0 if np.isfinite(zs) else 0.0
        self.mz = mz >= 0.5
        if self.mz and not np.isfinite(zs):
            self.ok = False
        self.z = zs if self.mz else 0.0
        self.contact = bool(row.get("contact", False))
        b = fnum(row.get("xy_blur_um"))
        self.blur = max(b if np.isfinite(b) else (st if np.isfinite(st) else 0.0), 0.0)
        el = fnum(row.get("edge_loss_um"))
        self.el = max(el, 0.0) if np.isfinite(el) else 0.0
        ms = fnum(row.get("max_slope_deg"))
        self.ms = ms if np.isfinite(ms) else (90.0 if self.contact else 60.0)
        d = fnum(row.get("depth_mm"))
        self.depth = d * 1000 if np.isfinite(d) and d > 0 else np.inf
        f = fnum(row.get("fov_mm"))
        self.fov_mm = f if np.isfinite(f) and f > 0 else np.inf
        self.raster = self.mode == "raster_point"
        self.point = self.mode == "point_probe"
        self.jit = RASTER_JIT if self.raster else 0.0
        if self.raster or self.point or not np.isfinite(self.fov_mm) or self.fov_mm >= 40:
            self.ns = 0
        else:
            self.ns = int(math.ceil(40.0 / self.fov_mm)) - 1
        # 시뮬레이터 규칙(점 측정에도 seam 적용) — 차이 원인 확인용
        self.ns_simrule = 0 if (self.raster or not np.isfinite(self.fov_mm) or self.fov_mm >= 40) \
            else int(math.ceil(40.0 / self.fov_mm)) - 1
        self.seam_xy = max(0.5 * (st if np.isfinite(st) else 0.0), 1.0)
        self.seam_z = self.z / math.sqrt(10)
        self.ws = self.z * math.sqrt(1 - CORR_FRAC)
        self.cs = self.z * math.sqrt(CORR_FRAC)


def e_abs(mu, tau):
    """E|X|, X ~ N(mu, tau²)."""
    if tau <= 0:
        return abs(mu)
    return tau * math.sqrt(2 / math.pi) * math.exp(-mu * mu / (2 * tau * tau)) + mu * math.erf(mu / (tau * math.sqrt(2)))


def rho_box(a, sf=SIG_F, n=400):
    """길이 a 구간 평균의 상관 계수 (1D): mean over u,v of exp(−(u−v)²/(4 sf²))."""
    u = (np.arange(n) + 0.5) / n * a
    d = u[:, None] - u[None, :]
    return float(np.exp(-d * d / (4 * sf * sf)).mean())


def corr(d):
    return np.exp(-np.asarray(d) ** 2 / (4 * SIG_F ** 2))


def seam_var(n, sz):
    """W_0 = 0, W_j = Σ e_i (j = 1..n), 평균 제거 후 W_k, W_{k+1} 분산의 평균 (k = n//2)."""
    if n <= 0 or sz <= 0:
        return 0.0, 0.0
    idx = np.arange(n + 1)
    C = np.minimum(idx[:, None], idx[None, :]) * sz * sz
    M = np.eye(n + 1) - 1.0 / (n + 1)
    Cc = M @ C @ M
    k = n // 2
    v = 0.5 * (Cc[k, k] + Cc[k + 1, k + 1])
    vmean = 0.25 * (Cc[k, k] + Cc[k + 1, k + 1] + 2 * Cc[k, k + 1])     # 패치 평균 (dL+dR)/2
    return float(v), float(vmean)


# ---------------------------------------------------------------- H. 국소높이
RHO_CELL = rho_box(CELL) ** 2
RHO_PATCH = rho_box(FLAT) ** 2


def q_local_height(p: P):
    if not p.ok or not p.mz:
        return np.nan, "2D·측정 불가"
    if p.point:
        return (2 * p.z if p.step_raw < CELL else np.nan), "점 측정(1점/칸)"
    if FLAT_RELIEF > p.depth:
        return np.nan, "depth < 1 mm"
    if (CELL / p.st) ** 2 < 0.5 and p.st > CELL:
        return np.nan, "칸 점유 < 50 %"
    n = max((CELL / p.st) ** 2, 1.0)
    vs, vsm = seam_var(p.ns, p.seam_z)
    var = p.ws ** 2 / n + p.cs ** 2 * RHO_CELL + vs
    var_mean = p.ws ** 2 / (n * 100) + p.cs ** 2 * RHO_PATCH + vsm       # 회차당 패치 평균
    q = 2 * math.sqrt(var) + e_abs(0.0, math.sqrt(var_mean / N_MC))
    return q, f"n={n:.0f}, seam {p.ns}"


# ---------------------------------------------------------------- W. 국소선폭
def _grid(p: P):
    s = p.blur / 2.355
    g = min(p.st, max(s, 1.0)) / 4
    if p.contact and p.mz:
        g = max(g, p.blur / 300)
    return float(np.clip(g, 0.5, 25.0))


def _profile(p: P):
    """잡음 없는 측정 단면 (흐림 후), 실제 단면, 격자, 결측 마스크, 측정 창 L."""
    a = (LINE_W + LINE_ERR) / math.sqrt(3)
    L = a + abs(POS_X) + 400 + 2 * p.blur + p.el          # 측정 창 (시뮬레이터와 같은 크기)
    g = _grid(p)
    pad = 4 * p.blur / 2.355 + 1.5 * p.blur + p.el + 10 * g
    x = np.arange(-L - pad, L + pad + g / 2, g)
    t = (x - POS_X) / a
    zt = LINE_H * np.sqrt(np.clip(1 - t * t, 0, None))
    if p.mz and p.contact:
        r = p.blur
        k = int(math.ceil(r / g))
        if k >= 1:
            u = np.arange(-k, k + 1) * g
            fp = u * u <= r * r
            b = np.where(fp, np.sqrt(np.clip(r * r - u * u, 0, None)) - r, -np.inf)
            zp = np.pad(zt, k, mode="edge")
            D = np.full(zt.shape, -np.inf)
            for j, bj in zip(range(-k, k + 1), b):
                if np.isfinite(bj):
                    D = np.maximum(D, zp[k + j: k + j + zt.size] + bj)
            Dp = np.pad(D, k, mode="edge")
            E = np.full(zt.shape, np.inf)
            for j, bj in zip(range(-k, k + 1), b):
                if np.isfinite(bj):
                    E = np.minimum(E, Dp[k + j: k + j + zt.size] - bj)
            zb = E
        else:
            zb = zt.copy()
    elif p.mz:
        s = p.blur / 2.355 / g
        if s >= 0.3:
            k = int(4 * s + 0.5)
            w = np.exp(-0.5 * (np.arange(-k, k + 1) / s) ** 2)
            w /= w.sum()
            zb = np.convolve(np.pad(zt, k, mode="edge"), w, mode="valid")
        else:
            zb = zt.copy()
    else:
        zb = zt.copy()
    nanm = np.zeros(x.size, bool)
    if p.mz:
        sl = np.degrees(np.arctan(np.abs(np.gradient(zb, g))))
        nanm |= sl > p.ms
        if p.el > 0:
            wall = np.degrees(np.arctan(np.abs(np.gradient(zt, g)))) > WALL_DEG
            if wall.any():
                wi = np.nonzero(wall)[0]
                # 각 점에서 가장 가까운 벽 점까지 거리
                pos = np.searchsorted(wi, np.arange(x.size))
                lo = wi[np.clip(pos - 1, 0, wi.size - 1)]
                hi = wi[np.clip(pos, 0, wi.size - 1)]
                dist = np.minimum(np.abs(np.arange(x.size) - lo), np.abs(hi - np.arange(x.size))) * g
                nanm |= dist <= p.el / 2
    return x, zb, nanm, L, g


def _cov_points(xa, xb, p: P, nr):
    """구간 평균 단면의 두 x 위치 사이 잡음 공분산 (상관 성분, 행 평균 포함)."""
    rho_y = rho_box(min(SEG, nr * p.st) if nr > 1 else 1.0)
    return p.cs ** 2 * rho_y * corr(np.subtract.outer(xa, xb))


def q_local_width(p: P):
    """→ (Q_Wa, Q_Wb, 메모)."""
    if not p.ok:
        return np.nan, np.nan, "측정 불가"
    if p.point:
        if 2 * p.blur > LINE_W:
            return np.nan, np.nan, "볼 지름 > 0.4 mm"
        q = 2 * math.hypot(p.z * math.sqrt(2), LINE_W * p.us)
        return q, q, "점 측정 해석식(시뮬레이터와 같은 식)"
    if p.mz and LINE_RELIEF > p.depth:
        return np.nan, np.nan, "depth < 0.2 mm"
    a = (LINE_W + LINE_ERR) / math.sqrt(3)
    if not p.mz:
        # 2D: 흐린 실루엣 0.5 문턱 → 반폭 a' (erf), 표본 수 양자화
        s = p.blur / 2.355
        if s > 0:
            from math import erf
            lo, hi = 0.0, a + 5 * s
            for _ in range(60):
                mid = (lo + hi) / 2
                v = 0.5 * (erf((a - mid) / (math.sqrt(2) * s)) + erf((a + mid) / (math.sqrt(2) * s)))
                lo, hi = (mid, hi) if v > 0.5 else (lo, mid)
            ap = (lo + hi) / 2
        else:
            ap = a
        W = 2 * ap / p.st
        f = W - math.floor(W)
        bias = (2 * ap * math.sqrt(3) / 2) - (LINE_W + LINE_ERR)
        sd = p.st * math.sqrt(f * (1 - f)) * math.sqrt(3) / 2
        sd = math.hypot(sd, (LINE_W + LINE_ERR) * p.us)
        q = abs(bias) + 2 * sd
        return q, q, f"2D 양자화 f={f:.2f}"
    x, zb, nanm, L, g = _profile(p)
    nr = max(SEG / p.st, 1.0)
    sp2 = p.ws ** 2 / nr                                  # 구간 평균 단면의 표본당 백색 분산
    # ---- W-a: 반높이 기울기 (결측·위상 무시)
    inwin = (x >= -L) & (x <= L)
    top_true = zb[inwin].max()
    base_true = 0.0
    half = (top_true + base_true) / 2
    ic = int(np.argmax(np.where(inwin, zb, -np.inf)))
    iL = np.nonzero(zb[:ic] < half)[0]
    iR = np.nonzero(zb[ic:] < half)[0]
    if iL.size == 0 or iR.size == 0:
        return np.nan, np.nan, "반높이 없음"
    iL, iR = iL[-1], ic + iR[0]
    dz = np.gradient(zb, g)
    sL, sR = dz[iL], -dz[iR]
    xL, xR, xT = x[iL], x[iR], x[ic]
    n15 = max(int(0.15 * 2 * L / p.st), 1)
    xbL, xbR = -L + 0.5 * n15 * p.st, L - 0.5 * n15 * p.st
    ntop = max(int(np.sum(zb[inwin] >= 0.95 * top_true) * g / p.st), 3)
    # 변수: [n_L, n_R, base_L, base_R, top] 상관 성분 공분산 + 백색
    pts = np.array([xL, xR, xbL, xbR, xT])
    C = _cov_points(pts, pts, p, nr)
    Wd = np.diag([sp2 * 2 / 3, sp2 * 2 / 3, (math.pi / 2) * sp2 / n15, (math.pi / 2) * sp2 / n15,
                  (9 / 4) * sp2 / ntop])
    if p.jit:
        Wd[0, 0] += (p.jit * sL) ** 2 / nr
        Wd[1, 1] += (p.jit * sR) ** 2 / nr
    # δw = n_L/sL + n_R/sR − (δbase + δtop)/2 · (1/sL + 1/sR),  δbase = (b_L + b_R)/2
    cL, cR = 1 / sL, 1 / sR
    h = 0.5 * (cL + cR)
    c = np.array([cL, cR, -h / 2, -h / 2, -h])
    var_a = float(c @ (C + Wd) @ c) + ((LINE_W + LINE_ERR) * p.us) ** 2
    qa = 2 * math.sqrt(var_a) + e_abs(0.0, math.sqrt(var_a / N_MC))
    # ---- W-b: 위상 40개, 결측 틈을 건너는 보간
    ws_list, vars_ = [], []
    for ph in (np.arange(40) + 0.5) / 40 * p.st:
        k0 = math.ceil((-L - ph) / p.st)
        k1 = math.floor((L - ph) / p.st)
        xs = ph + np.arange(k0, k1 + 1) * p.st
        if xs.size < 7:
            continue
        v = np.interp(xs, x, zb)
        nn = nanm[np.clip(np.rint((xs - x[0]) / g).astype(int), 0, x.size - 1)]
        n15b = max(int(0.15 * xs.size), 1)
        endv = np.concatenate([v[:n15b], v[-n15b:]])
        endn = np.concatenate([nn[:n15b], nn[-n15b:]])
        if (~endn).sum() == 0:
            continue
        base = float(np.median(endv[~endn]))
        okx, okv = xs[~nn], v[~nn]
        if okx.size < 7:
            continue
        ip = int(np.argmax(okv))
        sel = np.nonzero(okv >= base + 0.95 * (okv[ip] - base))[0]
        top = okv[ip]
        if sel.size >= 3:
            cc = np.polyfit(okx[sel] - okx[ip], okv[sel], 2)
            if cc[0] < 0 and abs(-cc[1] / (2 * cc[0])) <= okx[sel].max() - okx[sel].min():
                top = cc[2] - cc[1] ** 2 / (4 * cc[0])
        hf = base + (top - base) / 2
        j = ip
        while j > 0 and okv[j] >= hf:
            j -= 1
        kk = ip
        while kk < okv.size - 1 and okv[kk] >= hf:
            kk += 1
        if okv[j] >= hf or okv[kk] >= hf:
            continue
        x1L, x2L, v1L, v2L = okx[j], okx[j + 1], okv[j], okv[j + 1]
        x1R, x2R, v1R, v2R = okx[kk - 1], okx[kk], okv[kk - 1], okv[kk]
        xl = x1L + (hf - v1L) * (x2L - x1L) / (v2L - v1L)
        xr = x1R + (hf - v1R) * (x2R - x1R) / (v2R - v1R)
        ws_list.append(xr - xl)
        # 잡음 전파: x_e = x1 + (hf − v1)(x2 − x1)/(v2 − v1)
        slL = (v2L - v1L) / (x2L - x1L)
        slR = (v2R - v1R) / (x2R - x1R)
        tL = (hf - v1L) / (v2L - v1L)
        tR = (hf - v1R) / (v2R - v1R)
        nb = 2 * n15b
        ntp = max(sel.size, 3)
        P5 = np.array([x1L, x2L, x1R, x2R, -L + 0.5 * n15b * p.st, L - 0.5 * n15b * p.st, okx[ip]])
        Cb = _cov_points(P5, P5, p, nr)
        Wb = np.diag([sp2, sp2, sp2, sp2, (math.pi / 2) * sp2 / nb * 2, (math.pi / 2) * sp2 / nb * 2,
                      (9 / 4) * sp2 / ntp])
        if p.jit:
            for ii, xx in enumerate((x1L, x2L, x1R, x2R)):
                Wb[ii, ii] += (p.jit * np.interp(xx, x, dz)) ** 2 / nr
        # xr − xl 의 미분: d xl = (δhf − (1−tL)δv1L − tL δv2L)/slL, d xr 같음(slR 음수)
        dh = 1 / slR - 1 / slL                     # δhf 계수
        cvec = np.array([(1 - tL) / slL, tL / slL, -(1 - tR) / slR, -tR / slR,
                         dh / 4, dh / 4, dh / 2])
        vars_.append(float(cvec @ (Cb + Wb) @ cvec))
    if not ws_list:
        return qa, np.nan, "W-b 표본 부족"
    wv = np.array(ws_list)
    bias = float(wv.mean() - (LINE_W + LINE_ERR))
    var_b = float(np.mean(vars_)) + float(wv.var()) + ((LINE_W + LINE_ERR) * p.us) ** 2
    qb = e_abs(bias, math.sqrt(var_b / N_MC)) + 2 * math.sqrt(var_b)
    return qa, qb, f"s={sL:.2f}, 결측틈 위상평균 치우침 {bias:+.2f}"


# ---------------------------------------------------------------- L. 길이40
def q_length(p: P, sim_rule=False):
    if not p.ok:
        return np.nan
    e2 = p.z ** 2 if p.point else p.st ** 2 / 12
    if p.raster and not sim_rule:
        e2 += p.jit ** 2
    ns = p.ns_simrule if sim_rule else p.ns
    v = 2 * e2 + (40000 * p.us) ** 2 + ns * p.seam_xy ** 2
    return 2 * math.sqrt(v)


# ---------------------------------------------------------------- 대조
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", default=os.path.join(ROOT, "docs", "0_방법탐색"))
    ap.add_argument("--sim", default=os.path.join(ROOT, "docs", "0_방법탐색", "결과", "시뮬레이션.csv"))
    ap.add_argument("--specs-py", default=os.path.join(ROOT, "scripts", "method_screening"))
    ap.add_argument("--out", default=os.path.join(HERE, "v4_대조표.csv"))
    ap.add_argument("--tol", type=float, default=0.30)
    a = ap.parse_args(argv)
    sys.path.insert(0, a.specs_py)
    import warnings
    warnings.simplefilter("ignore")
    from specs import load_specs
    df = load_specs(sorted(glob.glob(os.path.join(a.spec_dir, "후보-사양_*.csv"))))
    st = pd.read_csv(a.sim)
    st = st[st["scenario"] == "보수-500"]
    qsim = st.pivot(index="id", columns="error_type", values="Q_um")
    recs = []
    for _, r in df.iterrows():
        p = P(r.to_dict())
        qh, nh = q_local_height(p)
        qa, qb, nw = q_local_width(p)
        ql = q_length(p)
        ql_s = q_length(p, sim_rule=True)
        for metric, qan, qalt, lim, note in (("국소높이", qh, qh, 5.0, nh), ("국소선폭", qa, qb, 10.0, nw),
                                            ("길이40", ql, ql_s, 25.0, f"seam {p.ns}(해석) / {p.ns_simrule}(시뮬 규칙)")):
            qs = float(qsim.loc[p.id, metric]) if p.id in qsim.index else np.nan
            ref = qalt if metric == "국소선폭" else qan
            dif = (qs - ref) / ref if (np.isfinite(qs) and np.isfinite(ref) and ref > 0) else np.nan
            dif_a = (qs - qan) / qan if (np.isfinite(qs) and np.isfinite(qan) and qan > 0) else np.nan
            both_nan = not np.isfinite(qs) and not np.isfinite(ref)
            fl = ("" if both_nan else "측정가능 불일치" if (np.isfinite(qs) != np.isfinite(ref)) else
                  ("초과" if abs(dif) > a.tol else ""))
            fl_a = ("" if (not np.isfinite(qs) and not np.isfinite(qan)) else "측정가능 불일치"
                    if (np.isfinite(qs) != np.isfinite(qan)) else ("초과" if abs(dif_a) > a.tol else ""))
            pass_s = np.isfinite(qs) and qs <= lim
            pass_a = np.isfinite(ref) and ref <= lim
            recs.append({"id": p.id, "mode": p.mode, "metric": metric, "Q_sim": qs, "Q_ana": qan,
                         "Q_ana_b": qalt, "diff_a": dif_a, "flag_a": fl_a, "diff_ref": dif, "flag_ref": fl,
                         "lim4": lim, "pass_sim": pass_s, "pass_ana_ref": pass_a,
                         "verdict_differs": bool(pass_s != pass_a), "note": note,
                         "z": p.z, "step": p.step_raw, "blur": p.blur, "el": p.el, "ms": p.ms, "contact": p.contact,
                         "ppm": p.us * 1e6, "seams": p.ns})
    out = pd.DataFrame(recs)
    out.to_csv(a.out, index=False, encoding="utf-8-sig")
    for col in ("flag_a", "flag_ref"):
        print(col, out.groupby("metric")[col].apply(lambda s: (s != "").sum()).to_dict())
    print("판정이 갈리는 경우:", out[out["verdict_differs"]][["id", "metric", "Q_sim", "Q_ana", "Q_ana_b"]].to_string())
    return out


if __name__ == "__main__":
    main()
