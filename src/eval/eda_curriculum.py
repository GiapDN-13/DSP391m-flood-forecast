"""EDA bổ sung theo đúng giáo trình chương 3–4 (Report 2) — Polars + seaborn.

Giáo trình yêu cầu đích danh vài kỹ thuật mà 8 mục EDA cũ (`src/eval/eda.py`)
chưa gọi tên. File này bổ sung đúng các mục đó, mỗi mục một hình:

    E9   Thống kê mô tả đầy đủ — mean, median, mode, std, IQR, skew, kurtosis
    E10  Phân bố theo tháng — box plot + mật độ KDE (thang log)
    E11  Tương quan Pearson **và** Spearman — heatmap đặt cạnh nhau
    E12  Ngoại lai (outlier) — IQR trên thang log + kiểm tra hợp lý vật lý

Vì sao cần Spearman: lưu lượng lệch rất mạnh (skew 5,91). Pearson đo quan hệ
TUYẾN TÍNH và bị vài ngày lũ cực lớn chi phối; Spearman đo quan hệ ĐƠN ĐIỆU trên
thứ hạng nên bền với phân bố lệch. Báo cả hai, chênh lệch giữa chúng chính là
một phát hiện.

Không dùng pandas: tính toán bằng Polars; seaborn chỉ nhận mảng numpy để vẽ.

    python -m src.eval.eda_curriculum
"""

from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
import seaborn as sns  # noqa: E402

from src import config as cfg  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.DATA_PROCESSED / "daily_panel.parquet"
FIGS = cfg.ROOT / "reports" / "figures" / "report"
OUT_STATS = cfg.ROOT / "reports" / "eda_descriptive.csv"
OUT_CORR = cfg.ROOT / "reports" / "eda_correlation.csv"
OUT_OUTL = cfg.ROOT / "reports" / "eda_outliers.csv"

sns.set_theme(style="whitegrid", context="paper", font_scale=1.05)
ACC, WARN, INK = "#00666e", "#b35c00", "#1a1a1a"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Biến đưa vào thống kê mô tả và ma trận tương quan — tên hiển thị tiếng Anh
VARS = {
    "discharge": "Q (today)",
    "target_h1": "Q (t+1)",
    "rain_basin": "Rain (today)",
    "rain_basin_lag1": "Rain (t-1)",
    "rain_basin_roll3": "Rain 3-day",
    "rain_basin_roll7": "Rain 7-day",
    "api": "Wetness API",
    "rain_thuong": "Rain upper",
    "rain_trung": "Rain middle",
    "rain_ha": "Rain lower",
    "q_diff1": "Q change 1d",
}


def save(fig, name: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"    → reports/figures/report/{name}")


# ------------------------------------------------------------------ E9

def e9_descriptive(d: pl.DataFrame) -> pl.DataFrame:
    """Thống kê mô tả: xu hướng trung tâm, độ phân tán, hình dạng phân bố."""
    print("\n[E9] Thống kê mô tả")
    rows = []
    # Q(t+1) và Rain(t-1) chỉ là bản dịch thời gian của Q và Rain — cùng phân bố
    for col, name in ((c, n) for c, n in VARS.items()
                      if c not in ("target_h1", "rain_basin_lag1")):
        s = d[col].drop_nulls()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        # Mode của biến liên tục vô nghĩa nếu lấy giá trị lặp nhiều nhất trên số
        # thực; làm tròn 1 chữ số rồi lấy mode — với mưa nó sẽ ra 0 (ngày khô).
        mode = s.round(1).mode().sort()[0]
        rows.append({
            "variable": name, "n": s.len(),
            "mean": s.mean(), "median": s.median(), "mode": mode,
            "std": s.std(), "min": s.min(), "q1": q1, "q3": q3, "iqr": q3 - q1,
            "max": s.max(), "skew": s.skew(), "kurtosis": s.kurtosis(),
        })
    t = pl.DataFrame(rows).with_columns(pl.selectors.float().round(2))
    t.write_csv(OUT_STATS)
    print(t.select("variable", "mean", "median", "mode", "std", "skew"))

    # Bảng dạng hình để chèn slide
    show = t.select("variable", "mean", "median", "mode", "std", "iqr", "max", "skew")
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    ax.axis("off")
    tb = ax.table(cellText=[[f"{v:,.2f}" if isinstance(v, float) else str(v) for v in r]
                            for r in show.iter_rows()],
                  colLabels=[c.upper() if c != "variable" else "Variable" for c in show.columns],
                  loc="center", cellLoc="right", colLoc="right")
    tb.auto_set_font_size(False)
    tb.set_fontsize(9)
    tb.scale(1, 1.35)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if r == 0:
            cell.set_facecolor("#e6f0f0")
            cell.set_text_props(weight="bold")
        if c == 0:
            cell.set_text_props(ha="left")
    save(fig, "eda9_descriptive_en.png")
    return t


# ------------------------------------------------------------------ E10

def e10_distribution(d: pl.DataFrame) -> None:
    """Box plot theo tháng + KDE: vị trí, độ trải và độ lệch của phân bố."""
    print("\n[E10] Box plot theo tháng + KDE")
    m = d.select(pl.col("date").dt.month().alias("m"),
                 pl.col("discharge").log1p().alias("lq")).drop_nulls()
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw={"width_ratios": [2.2, 1]})

    groups = [m.filter(pl.col("m") == k)["lq"].to_numpy() for k in range(1, 13)]
    bp = ax[0].boxplot(groups, tick_labels=MONTHS, patch_artist=True, widths=0.6,
                       flierprops={"marker": ".", "markersize": 3, "alpha": 0.4})
    for k, box in enumerate(bp["boxes"], start=1):
        box.set_facecolor(ACC if k in cfg.FLOOD_SEASON_MONTHS else "#b8c7c9")
        box.set_alpha(0.75)
    ax[0].set(title="Discharge by month (flood season Sep–Dec in teal)",
              ylabel="log(1 + Q)  [m³/s]")

    q = d["discharge"].drop_nulls()
    lq = q.log1p().to_numpy()
    sns.histplot(lq, bins=50, stat="density", color="#b8c7c9", ax=ax[1], edgecolor="white")
    sns.kdeplot(lq, color=ACC, lw=2, ax=ax[1])
    top = ax[1].get_ylim()[1]
    for val, lab, ls, ha, y in [(q.mean(), "mean", "--", "left", 0.92),
                                (q.median(), "median", "-", "right", 0.80)]:
        ax[1].axvline(np.log1p(val), color=WARN, ls=ls, lw=1.4)
        ax[1].text(np.log1p(val), top * y, f" {lab} {val:.0f} ", ha=ha,
                   color=WARN, fontsize=8)
    ax[1].set(title="Density (KDE) of log(1 + Q)", xlabel="log(1 + Q)", ylabel="density")
    save(fig, "eda10_box_kde_en.png")
    print(f"    mean {q.mean():.1f} > median {q.median():.1f}: lệch phải, "
          f"mean bị kéo bởi ngày lũ")


# ------------------------------------------------------------------ E11

def e11_correlation(d: pl.DataFrame) -> pl.DataFrame:
    """Ma trận Pearson và Spearman cạnh nhau, cùng thang màu."""
    print("\n[E11] Pearson vs Spearman")
    cols = list(VARS)
    x = d.select(cols).drop_nulls()
    pear = np.corrcoef(x.to_numpy(), rowvar=False)
    # Spearman = Pearson trên thứ hạng (rank trung bình cho các giá trị bằng nhau)
    ranks = x.select(pl.all().rank("average")).to_numpy()
    spear = np.corrcoef(ranks, rowvar=False)

    labels = [VARS[c] for c in cols]
    fig, ax = plt.subplots(1, 3, figsize=(13.5, 5.6),
                           gridspec_kw={"width_ratios": [1, 1, 0.04]})
    for a, mat, title in [(ax[0], pear, "Pearson (linear)"),
                          (ax[1], spear, "Spearman (rank, robust to skew)")]:
        sns.heatmap(mat, ax=a, vmin=-1, vmax=1, cmap="RdBu_r", annot=True, fmt=".2f",
                    annot_kws={"size": 7}, xticklabels=labels,
                    yticklabels=labels if a is ax[0] else False,
                    cbar=a is ax[1], cbar_ax=ax[2] if a is ax[1] else None,
                    square=True, linewidths=0.4, linecolor="white")
        a.set_title(title, fontsize=11)
        a.tick_params(axis="x", rotation=45, labelsize=8)
        a.tick_params(axis="y", labelsize=8)
        plt.setp(a.get_xticklabels(), ha="right", rotation_mode="anchor")
    save(fig, "eda11_corr_heatmap_en.png")

    tgt = cols.index("target_h1")
    rows = [{"variable": VARS[c], "pearson_vs_Q_t1": round(float(pear[tgt, i]), 3),
             "spearman_vs_Q_t1": round(float(spear[tgt, i]), 3)}
            for i, c in enumerate(cols) if c != "target_h1"]
    t = pl.DataFrame(rows).with_columns(
        (pl.col("spearman_vs_Q_t1") - pl.col("pearson_vs_Q_t1")).round(3).alias("diff"))
    t.write_csv(OUT_CORR)
    print(t)
    return t


# ------------------------------------------------------------------ E12

def e12_outliers(d: pl.DataFrame) -> pl.DataFrame:
    """Ngoại lai: thống kê (IQR trên log) và vật lý (lũ mà không có mưa).

    Hai câu hỏi khác nhau:
    * IQR trả lời "giá trị này có hiếm không" — ngày lũ thật cũng hiếm, nên IQR
      gắn cờ chính các ngày mô hình cần học nhất. Không được xoá theo IQR.
    * Kiểm tra vật lý trả lời "giá trị này có hợp lý không": lưu lượng vượt Q99
      mà mưa lưu vực 3 ngày gần đó gần như bằng 0 thì không có nguồn nước nào
      sinh ra nó trong mô hình thuỷ văn ⇒ nghi lỗi mô phỏng hoặc xả hồ chứa.
    """
    print("\n[E12] Ngoại lai")
    lq = pl.col("discharge").log1p()
    q1, q3 = d.select(lq.quantile(0.25)).item(), d.select(lq.quantile(0.75)).item()
    hi = q3 + 1.5 * (q3 - q1)
    q99 = d["discharge"].quantile(0.99)

    # mưa 3 ngày KẾT THÚC hôm trước — đúng độ trễ 1 ngày tìm thấy ở EDA mục 3
    x = d.with_columns(
        (pl.col("rain_basin").shift(1) + pl.col("rain_basin").shift(2)
         + pl.col("rain_basin").shift(3)).alias("rain_prev3"),
        (lq > hi).alias("iqr_flag"),
    ).with_columns(
        ((pl.col("discharge") >= q99) & (pl.col("rain_prev3") < 10)).alias("phys_flag"))

    n_iqr = int(x["iqr_flag"].sum())
    n_flood = int(x.filter(pl.col("iqr_flag") & pl.col("date").dt.month().is_in(
        cfg.FLOOD_SEASON_MONTHS)).height)
    sus = x.filter(pl.col("phys_flag")).select(
        pl.col("date").dt.strftime("%Y-%m-%d"), pl.col("discharge").round(1),
        pl.col("rain_basin").round(1).alias("rain_today"),
        pl.col("rain_prev3").round(1))
    print(f"    ngưỡng IQR trên log: Q > {np.expm1(hi):.0f} m³/s → {n_iqr} ngày "
          f"({n_flood} ngày trong mùa lũ)")
    print(f"    nghi bất hợp lý vật lý (Q ≥ Q99 = {q99:.0f}, mưa 3 ngày trước < 10 mm):")
    print(sus)
    sus.write_csv(OUT_OUTL)

    p = x.drop_nulls(["rain_prev3"])
    fig, ax = plt.subplots(figsize=(8.5, 4))
    ax.scatter(p["rain_prev3"], p["discharge"], s=5, alpha=0.25, color="#8a9a9c",
               label="normal day")
    f = p.filter(pl.col("iqr_flag") & ~pl.col("phys_flag"))
    ax.scatter(f["rain_prev3"], f["discharge"], s=10, color=ACC,
               label=f"IQR outlier, explained by rain ({f.height}) → keep")
    g = p.filter(pl.col("phys_flag"))
    ax.scatter(g["rain_prev3"], g["discharge"], s=60, color=WARN, edgecolor=INK,
               zorder=5, label=f"no rain behind it ({g.height}) → flag")
    for r in g.iter_rows(named=True):
        ax.annotate(f"{r['date']:%Y-%m-%d}", (r["rain_prev3"], r["discharge"]),
                    xytext=(8, 4), textcoords="offset points", fontsize=8, color=WARN)
    # Hai ngày đáng nói: 14/06/2025 từng bị nghi (mưa CÙNG ngày chỉ 0,9 mm) nhưng
    # hai hôm trước mưa 181 + 98 mm; và ngày lũ có ít mưa giải thích nhất.
    big = p.filter(pl.col("discharge") >= q99).sort("rain_prev3")
    notes = [(big.row(0, named=True), "weakest-explained flood day", (-170, 18)),
             (p.filter(pl.col("date") == pl.datetime(2025, 6, 14)).row(0, named=True),
              "once suspected: only 0.9 mm that day, "
              "but 181 + 98 mm the 2 days before", (-420, 22))]
    for r, txt, off in notes:
        ax.annotate(f"{r['date']:%Y-%m-%d}: {txt}", (r["rain_prev3"], r["discharge"]),
                    xytext=off, textcoords="offset points", fontsize=7.5,
                    color=INK, arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.7})
    ax.axhline(np.expm1(hi), color=ACC, ls="--", lw=1)
    ax.text(1, np.expm1(hi) * 1.1, f"IQR fence on log scale: {np.expm1(hi):.0f} m³/s",
            color=ACC, fontsize=8)
    ax.set_xlim(left=0)
    ax.set(xscale="symlog", yscale="log", xlabel="rain over the 3 previous days (mm)",
           ylabel="discharge Q (m³/s)", title="Outliers: rare is not the same as wrong")
    ax.legend(loc="lower right", fontsize=8, frameon=True)
    save(fig, "eda12_outliers_en.png")
    return sus


def main() -> int:
    d = pl.read_parquet(PANEL)
    print(f"EDA bổ sung trên {d.height} ngày")
    e9_descriptive(d)
    e10_distribution(d)
    e11_correlation(d)
    e12_outliers(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
