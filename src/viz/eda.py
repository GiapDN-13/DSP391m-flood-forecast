"""EDA theo `docs/EDA_CHECKLIST.md` — sinh hình cho Report 2 (FR-R2).

    python -m src.viz.eda

Mỗi hình đều phải kèm một câu kết luận bằng lời trong báo cáo. Script in sẵn
các con số cần thiết ra màn hình để khỏi phải đọc lại hình rồi đoán.
"""

from __future__ import annotations

import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import config as cfg  # noqa: E402

BG, PANEL, GRID, FG, MUTED = "#0f172a", "#1e293b", "#334155", "#e2e8f0", "#94a3b8"
BLUE, GREEN, AMBER, RED = "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"


def _dark(ax, title=""):
    ax.set_facecolor(PANEL)
    for sp in ax.spines.values():
        sp.set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.label.set_color(MUTED)
    ax.xaxis.label.set_color(MUTED)
    ax.grid(alpha=0.15, color=GRID)
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold", color=FG)


def load() -> pd.DataFrame:
    p = cfg.DATA_PROCESSED / "daily_panel.parquet"
    if not p.exists():
        raise SystemExit("Chưa có daily_panel.parquet")
    d = pd.read_parquet(p)
    d["date"] = pd.to_datetime(d["date"])
    return d


def figure(d: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(17, 13), facecolor=BG)
    gs = fig.add_gridspec(4, 3, hspace=0.48, wspace=0.26)

    # --- 1. Chuỗi lưu lượng toàn giai đoạn ---
    ax = fig.add_subplot(gs[0, :])
    ax.plot(d["date"], d["discharge"], lw=0.5, color=BLUE)
    ax.set_yscale("log")
    ax.set_ylabel("m³/s (log)")
    _dark(ax, "① Lưu lượng sông Hương tại ô (16.45, 107.50), 2010–2026")
    for yr, mo in [(2020, 10), (2023, 11), (2025, 10)]:
        t = pd.Timestamp(yr, mo, 1)
        if d["date"].min() <= t <= d["date"].max():
            ax.axvline(t, color=RED, ls="--", lw=0.9, alpha=0.7)

    # --- 2. Mùa vụ ---
    ax = fig.add_subplot(gs[1, 0])
    by_m = [d.loc[d["date"].dt.month == m, "discharge"].dropna() for m in range(1, 13)]
    bp = ax.boxplot(by_m, showfliers=False, patch_artist=True,
                    medianprops=dict(color=FG))
    for i, b in enumerate(bp["boxes"], start=1):
        b.set_facecolor(AMBER if i in cfg.FLOOD_SEASON_MONTHS else BLUE)
        b.set_alpha(0.75)
    ax.set_xticklabels(range(1, 13), fontsize=7)
    ax.set_xlabel("Tháng")
    ax.set_ylabel("m³/s")
    _dark(ax, "② Phân bố lưu lượng theo tháng")

    # --- 3. Tương quan theo độ trễ ---
    ax = fig.add_subplot(gs[1, 1])
    lags = range(0, 11)
    cors = [d["rain_basin"].shift(k).corr(d["discharge"]) for k in lags]
    ax.bar(list(lags), cors, color=[GREEN if c == max(cors) else BLUE for c in cors])
    best = int(np.argmax(cors))
    ax.annotate(f"đỉnh: lag {best} ngày\nr = {cors[best]:.3f}",
                (best, cors[best]), color=GREEN, fontsize=9, fontweight="bold",
                xytext=(12, -6), textcoords="offset points")
    ax.set_xlabel("Độ trễ (ngày)")
    ax.set_ylabel("Hệ số tương quan")
    _dark(ax, "③ Tương quan mưa – lưu lượng theo độ trễ")

    # --- 4. Mưa tích luỹ ---
    ax = fig.add_subplot(gs[1, 2])
    names, vals = [], []
    for c in ["rain_basin", "rain_basin_roll3", "rain_basin_roll5", "rain_basin_roll7"]:
        if c in d:
            names.append(c.replace("rain_basin", "mưa").replace("_roll", " tích luỹ ") + ("d" if "roll" in c else ""))
            vals.append(d[c].shift(1).corr(d["discharge"]))
    ax.barh(names, vals, color=BLUE)
    ax.set_xlabel("Tương quan với lưu lượng (lag 1)")
    _dark(ax, "④ Mưa tích luỹ có tốt hơn mưa một ngày?")

    # --- 5. Phân bố cực trị ---
    ax = fig.add_subplot(gs[2, 0])
    ax.hist(np.log10(d["discharge"].dropna()), bins=60, color=BLUE, alpha=0.85)
    for q, c in [(0.95, AMBER), (0.99, RED)]:
        v = d["discharge"].quantile(q)
        ax.axvline(np.log10(v), color=c, ls="--", lw=1.3,
                   label=f"Q{int(q*100)} = {v:,.0f}".replace(",", " "))
    ax.legend(fontsize=7.5, facecolor=PANEL, edgecolor=GRID, labelcolor=FG)
    ax.set_xlabel("log₁₀(lưu lượng)")
    _dark(ax, "⑤ Phân bố lưu lượng (thang log)")

    # --- 6. Đỉnh lũ từng năm ---
    ax = fig.add_subplot(gs[2, 1])
    yearly = d.set_index("date")["discharge"].resample("YE").max()
    ax.bar(yearly.index.year, yearly.values, color=BLUE)
    ax.axhline(yearly.median(), color=AMBER, ls="--", lw=1,
               label=f"trung vị {yearly.median():,.0f}".replace(",", " "))
    ax.legend(fontsize=7.5, facecolor=PANEL, edgecolor=GRID, labelcolor=FG)
    ax.set_ylabel("m³/s")
    _dark(ax, "⑥ Đỉnh lũ từng năm")

    # --- 7. Trước / sau mốc 07/2022 ---
    ax = fig.add_subplot(gs[2, 2])
    brk = pd.Timestamp(cfg.GLOFAS_REGIME_BREAK)
    a = d.loc[d["date"] < brk, "discharge"].dropna()
    b = d.loc[d["date"] >= brk, "discharge"].dropna()
    ax.boxplot([a, b], showfliers=False, patch_artist=True,
               medianprops=dict(color=FG),
               boxprops=dict(facecolor=BLUE, alpha=0.75))
    ax.set_xticklabels([f"trước 07/2022\n(n={len(a):,})".replace(",", " "),
                        f"sau 07/2022\n(n={len(b):,})".replace(",", " ")], fontsize=8)
    ax.set_ylabel("m³/s")
    _dark(ax, "⑦ Hai chế độ dữ liệu GloFAS")

    # --- 8. Mưa theo tiểu lưu vực ---
    ax = fig.add_subplot(gs[3, 0])
    subs = [c for c in ["rain_thuong", "rain_trung", "rain_ha"] if c in d]
    ax.bar([s.replace("rain_", "") for s in subs],
           [d[s].mean() * 365.25 for s in subs], color=GREEN)
    ax.set_ylabel("mm/năm")
    _dark(ax, "⑧ Mưa trung bình năm theo tiểu lưu vực")

    # --- 9. Baseline ---
    ax = fig.add_subplot(gs[3, 1:])
    f = cfg.ROOT / "reports" / "baseline_results.csv"
    if f.exists():
        r = pd.read_csv(f)
        piv = r.pivot(index="horizon", columns="model", values="NSE")
        x = np.arange(len(piv))
        w = 0.8 / len(piv.columns)
        for i, m in enumerate(piv.columns):
            ax.bar(x + i * w, piv[m].values, w, label=m)
        ax.axhline(0.5, color=GREEN, ls="--", lw=1.2, label="ngưỡng AC-1 = 0,5")
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xticks(x + 0.4 - w / 2)
        ax.set_xticklabels([f"h = {h} ngày" for h in piv.index])
        ax.set_ylabel("NSE (cao hơn = tốt hơn)")
        ax.legend(fontsize=7.5, ncol=3, facecolor=PANEL, edgecolor=GRID,
                  labelcolor=FG)
        _dark(ax, "⑨ Baseline — NSE trên tập test 07/2022–2026")
    else:
        _dark(ax, "⑨ Chưa có baseline_results.csv")

    fig.suptitle("DSP391m · EDA + BASELINE — sông Hương, ô (16.45, 107.50)",
                 fontsize=15, fontweight="bold", color=FG)
    dest = cfg.FIGURES / "w1_eda_baseline.png"
    fig.savefig(dest, dpi=110, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"→ {dest}")


def numbers(d: pd.DataFrame) -> None:
    print("\n=== SỐ LIỆU CHO REPORT 2 ===")
    print(f"Khoảng: {d['date'].min():%Y-%m-%d} → {d['date'].max():%Y-%m-%d} "
          f"({len(d):,} ngày)".replace(",", " "))
    print(f"Lưu lượng: tb {d['discharge'].mean():.1f} · trung vị "
          f"{d['discharge'].median():.1f} · đỉnh {d['discharge'].max():,.0f} m³/s"
          .replace(",", " "))
    print(f"Mưa năm trung bình: {d['rain_basin'].mean()*365.25:,.0f} mm".replace(",", " "))

    cors = {k: d["rain_basin"].shift(k).corr(d["discharge"]) for k in range(0, 8)}
    best = max(cors, key=cors.get)
    print(f"\nTương quan mưa–lưu lượng đỉnh ở lag {best} ngày (r = {cors[best]:.3f})")
    print("  " + " · ".join(f"lag{k}={v:.3f}" for k, v in cors.items()))

    print("\nPhân vị lưu lượng:")
    for q in (0.5, 0.9, 0.95, 0.98, 0.99, 0.995):
        print(f"  Q{q*100:5.1f} = {d['discharge'].quantile(q):8.1f} m³/s")

    fl = d[d["date"].dt.month.isin(cfg.FLOOD_SEASON_MONTHS)]
    print(f"\nMùa lũ (tháng 9–12): {len(fl)/len(d)*100:.0f} % số ngày, "
          f"nhưng chiếm {fl['discharge'].sum()/d['discharge'].sum()*100:.0f} % tổng lượng nước")

    brk = pd.Timestamp(cfg.GLOFAS_REGIME_BREAK)
    a, b = d[d["date"] < brk]["discharge"], d[d["date"] >= brk]["discharge"]
    print(f"\nTrước/sau mốc 07/2022: trung bình {a.mean():.1f} → {b.mean():.1f} m³/s "
          f"({(b.mean()/a.mean()-1)*100:+.0f} %)")

    print("\nBất thường cần kiểm:")
    odd = d[(~d["date"].dt.month.isin(cfg.FLOOD_SEASON_MONTHS))
            & (d["discharge"] > d["discharge"].quantile(0.99))]
    print(f"  {len(odd)} ngày vượt Q99 NGOÀI mùa lũ")
    if len(odd):
        print(odd.nlargest(3, "discharge")[["date", "discharge", "rain_basin"]]
              .to_string(index=False))


def main() -> int:
    d = load()
    numbers(d)
    figure(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
