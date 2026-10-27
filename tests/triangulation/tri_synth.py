"""T3 시뮬레이터가 아님. T7a 시험용 단순 합성 레이저 선 영상 (F1 §6.1과 같은 단순형).

단면: 화소 넓이로 적분한 가우시안 (오차함수 차). skewed는 가우시안 ⊗ 한쪽 지수 꼬리 (+v 쪽).
잡음: 산탄 σ = √(gain × DN) (8비트 gain 1, 10비트 gain 4 DN/e [추정]), 읽기 잡음, 반올림, 잘림.
참 중심 v_true(u) = 가운데 + 40 px 사인 (한 주기) + 25 px 단차 (u 500 – 699).
이 영상의 숫자는 하드웨어 성능의 증거가 아닙니다 (세부청사진 T7a §9).
"""
from __future__ import annotations

import numpy as np
from scipy.special import erf, erfc

SEED = 20261027
W, H = 1280, 256

SCENARIOS = {
    # 이름: bit, sigma_px, peak_dn, bg_dn, read_dn, 그 밖
    "f1_basic_8bit": dict(bit=8, sigma=1.5, peak=180, bg=8, read=2),
    "nominal_10bit": dict(bit=10, sigma=1.5, peak=720, bg=32, read=8),
    "low_10bit": dict(bit=10, sigma=1.5, peak=200, bg=32, read=8),
    "saturated_10bit": dict(bit=10, sigma=1.5, peak=1600, bg=32, read=8),
    "reflection_10bit": dict(bit=10, sigma=1.5, peak=720, bg=32, read=8, reflection=(900, 921, 12.0, 1.5)),
    "sigma08_10bit": dict(bit=10, sigma=0.8, peak=720, bg=32, read=8),
    "sigma30_10bit": dict(bit=10, sigma=3.0, peak=720, bg=32, read=8),
    "skewed_10bit": dict(bit=10, sigma=1.5, peak=720, bg=32, read=8, tail_tau=2.0),
    "noiseless_10bit": dict(bit=10, sigma=1.5, peak=720, bg=32, read=0, noiseless=True),
    "no_line_10bit": dict(bit=10, sigma=1.5, peak=720, bg=32, read=8, no_line=(300, 500)),
    "static100_10bit": dict(bit=10, sigma=1.5, peak=720, bg=32, read=8),
    "speed_roi_10bit": dict(bit=10, sigma=1.5, peak=720, bg=32, read=8),
    "speed_full_10bit": dict(bit=10, sigma=1.5, peak=720, bg=32, read=8, H=800),
}


def make_vtrue(w=W, h=H, step=(500, 700, 25.0), amp=40.0):
    u = np.arange(w)
    v = h / 2 + amp * np.sin(2 * np.pi * u / w)
    if step is not None:
        v = v + np.where((u >= step[0]) & (u < step[1]), step[2], 0.0)
    return v


def _gauss_pixels(h, center, sigma, peak):
    """화소 [r − 0.5, r + 0.5]로 적분한 가우시안. 점 표본이면 꼭대기 = peak."""
    edges = np.arange(h + 1)[:, None] - 0.5
    z = (edges - center[None, :]) / (np.sqrt(2) * sigma)
    cdf = 0.5 * (1 + erf(z))
    return peak * (cdf[1:] - cdf[:-1]) * np.sqrt(2 * np.pi) * sigma


def _emg_pixels(h, center, sigma, peak, tau, sub=10):
    """가우시안 ⊗ 지수 꼬리 (+v 쪽, 시간 상수 tau px). 전체 빛 양은 같은 가우시안과 같게 둠.

    밀도 f(x) = (1/(2τ)) exp(σ²/(2τ²) − (x−μ)/τ) erfc((σ/τ − (x−μ)/σ)/√2), 화소 안을 sub개로 나눠 평균.
    """
    total = peak * np.sqrt(2 * np.pi) * sigma
    xs = (np.arange(h)[:, None] - 0.5 + (np.arange(sub)[None, :] + 0.5) / sub).reshape(-1)  # (h*sub,)
    d = xs[:, None] - center[None, :]
    with np.errstate(over="ignore"):
        lg = sigma ** 2 / (2 * tau ** 2) - d / tau
        dens = 0.5 / tau * np.exp(np.minimum(lg, 700)) * erfc((sigma / tau - d / sigma) / np.sqrt(2))
    dens = np.nan_to_num(dens)
    return total * dens.reshape(h, sub, -1).mean(axis=1)


def synth(name_or_cfg, v_true=None, rng=None, h=None):
    """시나리오 이름 (또는 설정 dict) 으로 영상 한 장. 반환 (img, v_true, line_cols)."""
    cfg = dict(SCENARIOS[name_or_cfg]) if isinstance(name_or_cfg, str) else dict(name_or_cfg)
    h = h or cfg.get("H", H)
    rng = np.random.default_rng(SEED if rng is None else rng)
    if v_true is None:
        v_true = make_vtrue(W, h)
    w = v_true.size
    if "tail_tau" in cfg:
        sig = _emg_pixels(h, v_true, cfg["sigma"], cfg["peak"], cfg["tail_tau"])
    else:
        sig = _gauss_pixels(h, v_true, cfg["sigma"], cfg["peak"])
    if "reflection" in cfg:
        u0, u1, dv, k = cfg["reflection"]
        refl = np.zeros_like(sig)
        refl[:, u0:u1] = _gauss_pixels(h, v_true + dv, cfg["sigma"], cfg["peak"] * k)[:, u0:u1]
        sig = sig + refl
    line_cols = np.ones(w, bool)
    if "no_line" in cfg:
        a, b = cfg["no_line"]
        sig[:, a:b] = 0.0
        line_cols[a:b] = False
    img = cfg["bg"] + sig
    maxv = 2 ** cfg["bit"] - 1
    if cfg.get("noiseless"):
        return np.clip(img, 0, maxv), v_true, line_cols          # 실수 영상 (반올림 · 잡음 끔)
    gain = 1.0 if cfg["bit"] == 8 else 4.0
    img = img + rng.normal(0, 1, img.shape) * np.sqrt(gain * np.maximum(img, 0))
    img = img + rng.normal(0, cfg["read"], img.shape)
    img = np.clip(np.round(img), 0, maxv)
    return img.astype(np.uint8 if cfg["bit"] == 8 else np.uint16), v_true, line_cols
