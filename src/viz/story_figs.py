"""Hình kể chuyện cho báo cáo và slide — mỗi hình trả lời đúng MỘT câu hỏi.

Khác với `src/eval/eda.py` (hình thống kê đầy đủ cho phân tích), các hình ở đây
được thiết kế để **thuyết phục người xem trong vài giây**: tiêu đề là câu kết
luận, chú thích nằm ngay trên dữ liệu, và chỉ giữ thứ cần cho kết luận đó.

Quy tắc theo skill dataviz: không bao giờ dùng hai trục y — hai đại lượng khác
đơn vị thì tách thành hai ô chung trục thời gian.

    python -m src.viz.story_figs            # nền sáng cho báo cáo
    python -m src.viz.story_figs --dark     # nền tối cho slide
"""

from __future__ import annotations

import argparse
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from src import config as cfg  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
FIGS = cfg.ROOT / "reports" / "figures" / "story"

THEMES = {
    "light": dict(bg="#FFFFFF", ink="#1B2A30", muted="#5F7680", grid="#E4EBED",
                  q="#00737C", q_fill="#00737C", rain="#3D6FA8",
                  r1="#B8860B", r2="#C2571A", r3="#B3261E"),
    "dark": dict(bg="#07141A", ink="#EAF4F5", muted="#8BA8B1", grid="#16313C",
                 q="#2FC2CC", q_fill="#2FC2CC", rain="#7FA7D9",
                 r1="#E8BE55", r2="#E0833C", r3="#E8665C"),
}


def style(t: dict) -> None:
    plt.rcParams.update({
        "figure.facecolor": t["bg"], "axes.facecolor": t["bg"],
        "savefig.facecolor": t["bg"], "savefig.dpi": 200, "savefig.bbox": "tight",
        "font.size": 10, "text.color": t["ink"], "axes.labelcolor": t["muted"],
        "xtick.color": t["muted"], "ytick.color": t["muted"],
        "axes.edgecolor": t["grid"], "axes.grid": True, "grid.color": t["grid"],
        "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.axisbelow": True,
    })


def risk_thresholds(d: pd.DataFrame) -> dict[str, float]:
    """Cùng định nghĩa với src/features/risk_levels.py: phân vị mùa lũ, chỉ train+valid."""
    from src.features.risk_levels import FLOOD_MONTHS, QUANTILES
    m = (d["date"] <= cfg.VALID_END) & d["date"].dt.month.isin(FLOOD_MONTHS)
    s = d.loc[m, "discharge"].dropna()
    return {k: float(s.quantile(q)) for k, q in QUANTILES.items()}


def anatomy(d: pd.DataFrame, t: dict, start="2020-10-03", end="2020-10-24") -> plt.Figure:
    """Mưa trên, sông dưới: mưa đỉnh trước, sông đỉnh sau một ngày."""
    w = d[(d["date"] >= start) & (d["date"] <= end)].copy()
    thr = risk_thresholds(d)

    fig, (ar, aq) = plt.subplots(
        2, 1, figsize=(9, 5.6), sharex=True,
        gridspec_kw={"height_ratios": [1, 2.3], "hspace": 0.22})

    # --- mưa ---
    ar.bar(w["date"], w["rain_basin"], width=0.78, color=t["rain"], linewidth=0)
    ar.set_ylabel("rain (mm/day)")
    ar.set_ylim(0, w["rain_basin"].max() * 1.32)
    ir = w["rain_basin"].idxmax()
    ar.annotate(f"{w.loc[ir, 'rain_basin']:.0f} mm",
                (w.loc[ir, "date"], w.loc[ir, "rain_basin"]),
                xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=9.5, fontweight="bold", color=t["ink"])
    ar.text(0.0, 1.06, "Basin-average rainfall", transform=ar.transAxes,
            fontsize=10, color=t["muted"])

    # --- lưu lượng ---
    aq.fill_between(w["date"], w["discharge"], color=t["q_fill"], alpha=0.12, linewidth=0)
    aq.plot(w["date"], w["discharge"], color=t["q"], linewidth=2.2)
    aq.set_ylabel("discharge (m³/s)")
    top = max(w["discharge"].max(), thr["nguy_co_3"]) * 1.15
    aq.set_ylim(0, top)
    aq.text(0.0, 1.02, "River discharge at the target cell", transform=aq.transAxes,
            fontsize=10, color=t["muted"])

    for k, lbl, col in [("nguy_co_1", "Risk level 1", t["r1"]),
                        ("nguy_co_2", "Risk level 2", t["r2"]),
                        ("nguy_co_3", "Risk level 3", t["r3"])]:
        aq.axhline(thr[k], color=col, linewidth=1.1, linestyle=(0, (5, 3)))
        aq.text(w["date"].iloc[-1], thr[k], f"{lbl} · {thr[k]:,.0f} m³/s",
                va="bottom", ha="right", fontsize=8.5, color=t["ink"],
                bbox=dict(facecolor=t["bg"], edgecolor="none", pad=1.5))

    iq = w["discharge"].idxmax()
    qd, qv = w.loc[iq, "date"], w.loc[iq, "discharge"]
    aq.scatter([qd], [qv], s=46, color=t["q"], zorder=5,
               edgecolor=t["bg"], linewidth=2)
    aq.annotate(f"peak {qv:,.0f} m³/s\n{qd:%d %b}  ·  water level 4.17 m",
                (qd, qv), xytext=(12, 4), textcoords="offset points",
                fontsize=9.5, color=t["ink"], va="bottom",
                bbox=dict(facecolor=t["bg"], edgecolor="none", pad=1.5))

    # --- độ trễ theo TỪNG NHỊP ---
    # Đợt lũ nhiều ngày có nhiều nhịp mưa liên tiếp: nối mưa lớn nhất với đỉnh
    # lũ sẽ ra độ trễ sai (09/10 → 12/10 là 3 ngày, nhưng đỉnh 12/10 là do nhịp
    # mưa 11/10). Đúng là: mỗi đỉnh sông cục bộ ↔ đỉnh mưa cục bộ ngay trước nó.
    w = w.reset_index(drop=True)
    qs, rs = w["discharge"], w["rain_basin"]
    q_peaks = [i for i in range(1, len(w) - 1)
               if qs[i] > qs[i - 1] and qs[i] >= qs[i + 1] and qs[i] >= thr["nguy_co_1"]]
    lags = []
    for i in q_peaks:
        cand = [j for j in range(max(0, i - 3), i)
                if j > 0 and rs[j] >= rs[j - 1] and rs[j] >= rs[j + 1]]
        if not cand:
            continue
        j = cand[-1]
        lag = int(i - j)
        lags.append(lag)
        y_arrow = qs[i] * 1.07
        aq.annotate("", xy=(w["date"][i], y_arrow), xytext=(w["date"][j], y_arrow),
                    arrowprops=dict(arrowstyle="->", color=t["ink"], linewidth=1.3))
        aq.text(w["date"][j] + (w["date"][i] - w["date"][j]) / 2, y_arrow * 1.02,
                f"{lag} day" + ("s" if lag != 1 else ""), ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color=t["ink"],
                bbox=dict(facecolor=t["bg"], edgecolor="none", pad=1))
        ar.axvline(w["date"][j], color=t["muted"], linewidth=0.9, linestyle=":")
        aq.axvline(w["date"][j], color=t["muted"], linewidth=0.9, linestyle=":")

    lag = max(set(lags), key=lags.count) if lags else 1
    aq.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    aq.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.suptitle(f"Each burst of rain lifts the river {lag} day later",
                 x=0.125, ha="left", y=0.995, fontsize=14, fontweight="bold",
                 color=t["ink"])
    fig.text(0.125, 0.935, "Flood of October 2020, Huong River. Dashed lines: "
             "risk levels from flood-season discharge percentiles.",
             fontsize=9, color=t["muted"])
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dark", action="store_true")
    a = ap.parse_args()
    theme = "dark" if a.dark else "light"
    t = THEMES[theme]
    style(t)
    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d["date"])
    FIGS.mkdir(parents=True, exist_ok=True)

    fig = anatomy(d, t)
    out = FIGS / f"anatomy_2020_{theme}.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"→ {out.relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
