"""figures.py — 결과 그림 (판정량 막대, 점수 순위, 민감도 순위 범위)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from matplotlib import font_manager  # noqa: E402

_have = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = [f for f in ("Malgun Gothic", "AppleGothic", "NanumGothic") if f in _have] \
    + ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

INK, MUTED, GRID = "#1f2328", "#6e7781", "#d0d7de"
BAR = "#2f6db5"          # 한 계열이라 색 하나 (색 = 정체성이 아니라 막대)
BAR_FAIL = "#9aa4ae"
LINE4, LINE10 = "#b35900", "#2e7d32"


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, lw=0.6, alpha=0.6)
    ax.set_axisbelow(True)


def q_bars(st, path):
    types = ["단차", "선폭", "구멍지름", "위치"]
    ids = list(dict.fromkeys(st["id"]))
    fig, axes = plt.subplots(2, 2, figsize=(max(8, 0.45 * len(ids) + 5), 7), constrained_layout=True)
    for ax, t in zip(axes.flat, types):
        d = st[st["error_type"] == t].set_index("id").reindex(ids)
        q = d["Q_um"].to_numpy(float)
        l4, l10 = float(d["lim_4to1_um"].iloc[0]), float(d["lim_10to1_um"].iloc[0])
        finite = q[np.isfinite(q) & (q > 0)]
        lo = min(l10 / 10, finite.min() / 2) if finite.size else l10 / 10
        hi = max(l4 * 10, finite.max() * 2) if finite.size else l4 * 10
        x = np.arange(len(ids))
        qq = np.where(np.isfinite(q), np.maximum(q, lo * 1.01), np.nan)
        colors = [BAR if (np.isfinite(v) and v <= l4) else BAR_FAIL for v in q]
        ax.bar(x, qq, color=colors, width=0.6, bottom=lo)
        ax.set_yscale("log")
        ax.set_ylim(lo, hi)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.axhline(l4, color=LINE4, lw=1.5, ls="--")
        ax.axhline(l10, color=LINE10, lw=1.5, ls=":")
        ax.text(len(ids) - 0.5, l4, f" 4:1 ({l4:g} µm)", color=LINE4, va="bottom", ha="right", fontsize=8)
        ax.text(len(ids) - 0.5, l10, f" 10:1 ({l10:g} µm)", color=LINE10, va="top", ha="right", fontsize=8)
        for xi, v in zip(x, q):
            if not np.isfinite(v):
                ax.text(xi, lo * 1.15, "측정\n불가", ha="center", va="bottom", fontsize=7, color=MUTED)
        ax.set_xticks(x, ids, rotation=60 if len(ids) > 8 else 0, fontsize=8)
        ax.set_title(f"{t}: 판정량 |bias| + 2σ [µm]", fontsize=10, color=INK, loc="left")
        _style(ax)
    fig.suptitle("후보별 판정량 (로그축, 낮을수록 좋음 · 파랑 = 4:1 통과, 회색 = 불합격/측정 불가)",
                 fontsize=11, color=INK)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def score_rank(sdf, cdf, path):
    rows = [(r["id"], r["score"], bool(r["pass_all"])) for _, r in sdf.iterrows()]
    if len(cdf) and "valid" in cdf:
        rows += [(r["combo"], r["score"], True) for _, r in cdf[cdf["valid"]].head(10).iterrows()]
    rows.sort(key=lambda t: t[1])
    fig, ax = plt.subplots(figsize=(7.5, max(3, 0.32 * len(rows) + 1.2)), constrained_layout=True)
    y = np.arange(len(rows))
    ax.barh(y, [r[1] for r in rows], color=[BAR if r[2] else BAR_FAIL for r in rows], height=0.6)
    ax.set_yticks(y, [r[0] for r in rows], fontsize=8)
    for yi, r in zip(y, rows):
        ax.text(r[1] + 0.03, yi, f"{r[1]:.2f}", va="center", fontsize=8, color=INK)
    ax.set_xlim(0, 5.4)
    ax.set_xlabel("가중 점수 (1–5)", color=MUTED, fontsize=9)
    ax.set_title("점수 순위 (파랑 = 통과 조건 모두 만족 · 조합 포함, 회색 = 탈락 후보 참고)",
                 fontsize=10, color=INK, loc="left")
    _style(ax)
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color=GRID, lw=0.6, alpha=0.6)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def sens_range(sens, path):
    d = sens.sort_values("base_rank").head(20)
    fig, ax = plt.subplots(figsize=(7, max(3, 0.32 * len(d) + 1.2)), constrained_layout=True)
    y = np.arange(len(d))[::-1]
    ax.hlines(y, d["min_rank"], d["max_rank"], color=BAR_FAIL, lw=4)
    ax.plot(d["base_rank"], y, "o", color=BAR, ms=8)
    ax.set_yticks(y, d.index, fontsize=8)
    ax.invert_xaxis()
    ax.set_xlabel("순위 (점 = 기준 가중치, 막대 = 가중치 ±50 % 18경우의 범위)", color=MUTED, fontsize=9)
    ax.set_title(f"가중치 민감도 ({d['pool_basis'].iloc[0]})", fontsize=10, color=INK, loc="left")
    _style(ax)
    fig.savefig(path, dpi=150)
    plt.close(fig)
