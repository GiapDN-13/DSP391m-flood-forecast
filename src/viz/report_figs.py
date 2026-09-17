"""Hình cho báo cáo in — nền sáng, đọc được khi in đen trắng (NFR-7).

Khác với hình trên màn hình theo dõi (nền tối), hình trong báo cáo phải:
in đen trắng vẫn phân biệt được, chữ đủ lớn ở khổ một cột IEEE (~3,5 inch).

    python -m src.viz.report_figs
"""

from __future__ import annotations

import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import config as cfg  # noqa: E402

OUT = cfg.FIGURES / "report"
INK, MID, LIGHT = "#1a1a1a", "#666666", "#bbbbbb"


def fig_lag(d: pd.DataFrame) -> None:
    lags = list(range(0, 8))
    cors = [d["rain_basin"].shift(k).corr(d["discharge"]) for k in lags]
    best = max(range(len(cors)), key=lambda i: cors[i])

    fig, ax = plt.subplots(figsize=(3.4, 2.3), dpi=300)
    bars = ax.bar(lags, cors, color=LIGHT, edgecolor=INK, linewidth=0.7)
    bars[best].set_color(MID)
    bars[best].set_hatch("///")
    ax.annotate(f"r = {cors[best]:.3f}", (best, cors[best]),
                xytext=(0, 5), textcoords="offset points",
                ha="center", fontsize=7.5, color=INK, fontweight="bold")
    ax.set_xlabel("Rainfall lag (days)", fontsize=8, color=INK)
    ax.set_ylabel("Correlation with discharge", fontsize=8, color=INK)
    ax.set_ylim(0, 0.92)
    ax.tick_params(labelsize=7.5, colors=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.3, lw=0.5)
    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "fig_lag.png", facecolor="white")
    plt.close(fig)


def fig_baseline() -> None:
    f = cfg.ROOT / "reports" / "baseline_results.csv"
    if not f.exists():
        print("  ! chưa có baseline_results.csv, bỏ qua")
        return
    r = pd.read_csv(f)
    piv = r.pivot(index="horizon", columns="model", values="NSE")
    order = ["persistence", "climatology", "arima", "seasonal_naive"]
    piv = piv[[c for c in order if c in piv.columns]]

    fig, ax = plt.subplots(figsize=(3.4, 2.3), dpi=300)
    hatches = ["", "///", "...", "xxx"]
    greys = ["#555555", "#888888", "#aaaaaa", "#cccccc"]
    n = len(piv.columns)
    w = 0.8 / n
    for i, c in enumerate(piv.columns):
        ax.bar([x + i * w for x in range(len(piv))], piv[c].values, w,
               label=c.replace("_", " "), color=greys[i % 4],
               edgecolor=INK, linewidth=0.6, hatch=hatches[i % 4])
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks([x + 0.4 - w / 2 for x in range(len(piv))])
    ax.set_xticklabels([f"h={h}" for h in piv.index], fontsize=7.5)
    ax.set_ylabel("NSE", fontsize=8, color=INK)
    ax.set_xlabel("Forecast horizon (days)", fontsize=8, color=INK)
    ax.tick_params(labelsize=7.5, colors=INK)
    ax.legend(fontsize=6.2, frameon=False, ncol=2, loc="lower left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.3, lw=0.5)
    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "fig_baseline.png", facecolor="white")
    plt.close(fig)


def fig_seasonal(d: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(3.4, 2.1), dpi=300)
    by_m = [d.loc[d["date"].dt.month == m, "discharge"].dropna() for m in range(1, 13)]
    bp = ax.boxplot(by_m, showfliers=False, patch_artist=True, widths=0.65)
    for i, b in enumerate(bp["boxes"], start=1):
        b.set_facecolor("#888888" if i in cfg.FLOOD_SEASON_MONTHS else "#dddddd")
        b.set_edgecolor(INK)
        b.set_linewidth(0.6)
        if i in cfg.FLOOD_SEASON_MONTHS:
            b.set_hatch("///")
    for k in ("medians", "whiskers", "caps"):
        for e in bp[k]:
            e.set_color(INK)
            e.set_linewidth(0.7)
    ax.set_xticklabels(range(1, 13), fontsize=7)
    ax.set_xlabel("Month", fontsize=8, color=INK)
    ax.set_ylabel("Discharge (m³/s)", fontsize=8, color=INK)
    ax.tick_params(labelsize=7.5, colors=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.3, lw=0.5)
    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "fig_seasonal.png", facecolor="white")
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(cfg.DATA_PROCESSED / "daily_panel.parquet")
    d["date"] = pd.to_datetime(d["date"])
    fig_lag(d)
    fig_seasonal(d)
    fig_baseline()
    for f in sorted(OUT.glob("*.png")):
        print(f"→ {f.name}  ({f.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
