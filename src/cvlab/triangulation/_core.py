"""레이저 선 추출 공통 계산 (내부용). 영상 규칙: f[v, u], 열 u마다 중심 행 v 하나."""
from __future__ import annotations

import math

import numpy as np

SIGMA_FLOOR_DN = 0.5   # [추정] 무잡음 영상에서 σ = 0을 막는 바닥 (양자화 잡음 1/√12 ≈ 0.29 DN보다 조금 큼)
MIN_ABOVE_PX = 2       # [추정] 창 안에 문턱 넘는 화소가 2개 이상이어야 선으로 봄 (외톨이 잡음 화소 거부)
BG_GAP_PX = 3          # [추정] 창 끝과 배경 띠 사이 틈 (선 꼬리를 배경에 덜 넣음)
BG_ROWS = 32           # [추정] 배경 띠 한쪽 행 수 (양쪽 64개 표본으로 중앙값 · MAD)
STRIP_R = 20           # FWHM을 재는 띠 반폭 (σ 3 px 선의 FWHM 7 px을 넉넉히 덮음)
HW_FIRST = 8           # 첫 배경 띠의 반폭. 창 반폭이 이 값 이하면 이 띠 (창 끝에서 4 px 넘게 떨어짐)를 그대로 씀
VALID_BITS = (8, 10, 12, 16)   # 명세 1절 frame.bit_depth 허용 값


def as_image(img) -> np.ndarray:
    a = np.asarray(img)
    if a.ndim != 2:
        raise ValueError(f"영상은 2차원 [H, W]여야 함 (받음 {a.shape})")
    if a.shape[0] < 3 or a.shape[1] < 1:
        raise ValueError(f"영상이 너무 작음 {a.shape} (행 ≥ 3)")
    if a.dtype.kind not in "uif":
        raise ValueError(f"영상 자료형 {a.dtype}은 쓸 수 없음")
    return a


def sat_level(a: np.ndarray, bit_depth) -> float:
    """포화값 = 2^bit_depth − 1 (그릇 최댓값이 아님, 명세 1절).

    bit_depth가 없으면: uint8 → 8, 실수 영상 → 포화 없음 (inf).
    uint16 (그 밖 정수 그릇 포함)은 그릇만으로 8 · 10 · 12 · 16비트를 가를 수 없어 ValueError (T-3).
    `load_frame`은 8비트 PNG도 uint16으로 돌려주므로 짐작하면 8비트 포화 (255)를 놓침 (팀장검증 5차 §4.5).
    """
    if bit_depth is not None:
        b = int(bit_depth)
        if b not in VALID_BITS:
            raise ValueError(f"bit_depth {bit_depth} ∉ {VALID_BITS}")
        if a.dtype == np.uint8 and b != 8:
            raise ValueError(f"uint8 영상인데 bit_depth = {b}")
        return float(2 ** b - 1)
    if a.dtype == np.uint8:
        return 255.0
    if a.dtype.kind in "ui":
        raise ValueError(f"{a.dtype} 영상은 bit_depth (frame.bit_depth)를 꼭 넘겨야 함 "
                         f"(그릇으로는 8 · 10 · 12 · 16비트를 가를 수 없음)")
    return math.inf


def gather(f: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """f[rows[k, u], u]. 범위 밖 행은 끝 행으로 자름 (쓰는 쪽에서 inb로 가림)."""
    H = f.shape[0]
    if rows.min() < 0 or rows.max() > H - 1:
        rows = np.clip(rows, 0, H - 1)
    return f[rows, np.arange(f.shape[1])[None, :]]


def argmax_rows(f, block=16):
    """열마다 최대 행 (np.argmax(f, axis=0)와 같은 값, 같은 값이면 첫 행).

    행 축 argmax는 메모리를 건너뛰어 느려서, 16행 묶음의 최댓값으로 묶음을 고른 뒤 그 안에서 찾음.
    """
    H, W = f.shape
    nb = H // block
    if nb < 2:
        return f.argmax(axis=0)
    cols = np.arange(W)
    bm = f[:nb * block].reshape(nb, block, W).max(axis=1)
    if nb * block < H:
        bm = np.concatenate([bm, f[nb * block:].max(axis=0, keepdims=True)], axis=0)
    ib = bm.argmax(axis=0)
    rows = ib[None, :] * block + np.arange(block)[:, None]
    inb = rows < H
    sub = f[np.minimum(rows, H - 1), cols[None, :]]
    m = bm[ib, cols]
    hit = (sub == m[None, :]) & inb
    return ib * block + hit.argmax(axis=0)


def global_bg(f):
    """영상 전체의 거친 배경 (성긴 표본의 중앙값, σ = 1.4826 MAD). 안내선 계산용으로만 씀."""
    s = np.sort(f[::8, ::8].astype(np.float32).ravel())
    med = float(s[s.size // 2])
    d = np.sort(np.abs(s - med))
    mad = float(d[d.size // 2])
    return med, max(1.4826 * mad, SIGMA_FLOOR_DN)


def global_threshold(f, k):
    """영상 전체의 거친 문턱 (성긴 표본의 중앙값 + k × 1.4826 MAD). 안내선 메움용으로만 씀."""
    med, sig = global_bg(f)
    return med + k * sig


def bg_stats(f: np.ndarray, p: np.ndarray, hw: int):
    """열마다 창 (p ± hw) 밖 배경 띠의 중앙값과 σ (= 1.4826 × MAD)."""
    H = f.shape[0]
    k = np.arange(BG_ROWS) + hw + BG_GAP_PX + 1
    offs = np.concatenate([-k[::-1], k])
    rows = p[None, :] + offs[:, None]
    if p.min() - offs[-1] < 0 or p.max() + offs[-1] > H - 1:
        bad = (rows < 0) | (rows >= H)
        rows = np.where(bad, 2 * p[None, :] - rows, rows)   # 영상 밖이면 반대쪽으로 접음
    vals = np.ascontiguousarray(gather(f, rows).T, dtype=np.float32)   # (W, 64): 열마다 연속 메모리 (속도)
    med = _median_last(vals)
    mad = _median_last(np.abs(vals - med[:, None].astype(vals.dtype)))
    sig = np.maximum(1.4826 * mad, SIGMA_FLOOR_DN)
    return med, sig


def _median_last(x):
    """마지막 축 중앙값 (np.median과 같은 값). 짧은 행이 많을 때 sort가 partition보다 빠름."""
    n = x.shape[-1]
    h = n // 2
    s = np.sort(x, axis=-1)
    if n % 2:
        return s[..., h].astype(np.float64)
    return 0.5 * (s[..., h - 1].astype(np.float64) + s[..., h].astype(np.float64))


def fwhm(f: np.ndarray, p: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """p 행을 피크로 보고 반높이 (bg + (피크 − bg)/2)를 선형 보간으로 찾아 잰 폭 [px]."""
    W = f.shape[1]
    cols = np.arange(W)
    c = STRIP_R
    strip = gather(f, p[None, :] + np.arange(-c, c + 1)[:, None]).astype(np.float64)
    peak = strip[c]
    level = bg + 0.5 * (peak - bg)
    below = strip < level[None, :]
    br = below[c + 1:]
    has_r = br.any(axis=0)
    ir = br.argmax(axis=0) + c + 1
    bl = below[c - 1::-1]
    has_l = bl.any(axis=0)
    il = c - 1 - bl.argmax(axis=0)
    yi, yo = strip[ir - 1, cols], strip[ir, cols]
    with np.errstate(invalid="ignore", divide="ignore"):
        xr = (ir - 1) + (yi - level) / (yi - yo)
        yi2, yo2 = strip[il + 1, cols], strip[il, cols]
        xl = (il + 1) - (yi2 - level) / (yi2 - yo2)
    out = xr - xl
    out[~(has_r & has_l) | ~(peak > bg)] = np.nan
    return out


def column_stats(f, p, params, valid_hint=None) -> dict:
    """배경 · 문턱 · 창 반폭 · FWHM을 p 기준으로 계산 (ROI에서 잘라도 같은 값이 나오게 지역 띠만 씀)."""
    H, W = f.shape
    cols = np.arange(W)
    k = float(params.threshold_k_sigma)
    pk = f[p, cols].astype(np.float64)
    bg0, sig0 = bg_stats(f, p, HW_FIRST)
    valid = pk > bg0 + k * sig0
    if valid_hint is not None:
        valid &= valid_hint
    fw0 = fwhm(f, p, bg0)
    if params.half_win_px is not None:
        hw = int(params.half_win_px)
    else:
        sel = valid & np.isfinite(fw0)
        hw = int(math.ceil(1.5 * float(np.median(fw0[sel])))) if sel.any() else 5
    hw = int(min(max(hw, 2), STRIP_R, (H - 1) // 2 if H >= 5 else 1))
    if hw <= HW_FIRST:                       # 첫 배경 띠가 이미 창 밖이면 그대로 씀 (속도)
        bg, sig, fw = bg0, sig0, fw0
    else:                                    # 창이 넓으면 띠를 바깥으로 옮겨 다시 잼
        bg, sig = bg_stats(f, p, hw)
        fw = fwhm(f, p, bg)
    thr = bg + k * sig
    sel = (pk > thr) & np.isfinite(fw)
    if valid_hint is not None:
        sel &= valid_hint
    fw_med = float(np.median(fw[sel])) if sel.any() else float("nan")
    return {"bg": bg, "sigma": sig, "thr": thr, "half_win": hw, "fwhm": fw, "fwhm_med": fw_med, "peak": pk}


def count_peaks(f, thr) -> np.ndarray:
    """열마다 문턱 넘는 덩어리 수. 틈 2 px 이하는 한 덩어리로 봄 (선 옆구리 잡음으로 쪼개지는 것 막음)."""
    if f.dtype.kind in "ui":                  # 정수 화소: f > thr ⇔ f > ⌊thr⌋ (실수 변환 없이 비교)
        t = np.clip(np.floor(thr), -1, np.iinfo(f.dtype).max)
        above = f > t.astype(np.int64)[None, :] if t.min() < 0 else f > t.astype(f.dtype)[None, :]
    else:
        above = f > thr[None, :].astype(f.dtype)
    c = above.copy()
    c[1:] |= above[:-1]
    c[:-1] |= above[1:]
    return c[0].astype(np.int64) + (c[1:] & ~c[:-1]).sum(axis=0)


def second_peak(f, p, hw, cols=None) -> np.ndarray:
    """창 (p ± hw) 밖에서 가장 밝은 값. cols를 주면 그 열만 계산하고 나머지는 −inf."""
    H, W = f.shape
    out = np.full(W, -np.inf)
    sel = np.arange(W) if cols is None else np.flatnonzero(cols)
    if sel.size:
        sub = f[:, sel]
        far = np.abs(np.arange(H)[:, None] - p[None, sel]) > hw
        out[sel] = np.where(far, sub, -np.inf).max(axis=0)
    return out
