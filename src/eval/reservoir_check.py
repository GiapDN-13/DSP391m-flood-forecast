"""Hồ chứa có làm thay đổi chuỗi lưu lượng ta dự báo không? (Report 3)

Câu hỏi của thầy: lưu lượng còn phụ thuộc mức xả của hồ. Trả lời bằng hai phép
thử, mỗi phép trả lời một câu khác nhau:

**R1 — GloFAS có "thấy" hồ không?** Tả Trạch và Bình Điền bắt đầu tích nước
khoảng 2009–2013. Nếu mô hình GloFAS có mô phỏng hồ, chuỗi lưu lượng SAU khi có
hồ phải khác TRƯỚC khi có hồ theo đúng kiểu hồ điều tiết:
  * mùa kiệt cao hơn (hồ xả phát điện),
  * đỉnh lũ thấp hơn với cùng lượng mưa (hồ cắt lũ),
  * dòng chảy bớt "giật" (chỉ số Richards–Baker giảm).
So sánh năm thuỷ văn 1998–2008 với 2014–2026 (bỏ giai đoạn chuyển tiếp).
Cần panel mở rộng có mưa từ 1997 — trước đây không làm được phép thử này.

**R2 — Số xả thật so với GloFAS.** Với các ngày tỉnh công bố lượng xả (báo,
cổng tỉnh), lưu lượng tại Kim Long phải ≥ tổng xả của hai hồ thượng nguồn. Ngày
nào GloFAS thấp hơn mức đó là ngày GloFAS chắc chắn sai so với sông thật.

    python -m src.features.build_panel --ext     # cần trước
    python -m src.eval.reservoir_check
"""

from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
import seaborn as sns  # noqa: E402
from scipy.stats import mannwhitneyu  # noqa: E402

from src import config as cfg  # noqa: E402
from src.features import reservoirs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.DATA_PROCESSED / "daily_panel_ext.parquet"
FIGS = cfg.ROOT / "reports" / "figures" / "report"
OUT_ERA = cfg.ROOT / "reports" / "reservoir_dam_era.csv"
OUT_TEST = cfg.ROOT / "reports" / "reservoir_dam_era_test.csv"
OUT_REL = cfg.ROOT / "reports" / "reservoir_release_check.csv"

AREA_KM2 = cfg.KIM_LONG_AREA_KM2   # lưu vực sông Hương tới Kim Long (~1 540 km²)
# Năm thuỷ văn đánh số theo năm KẾT THÚC: 2008 = 09/2007 → 08/2008.
PRE = (1998, 2008)         # trước Bình Điền (2009) và Tả Trạch
POST = (2014, 2026)        # cả hai hồ đã vận hành
EVENT_RAIN3_MM = 150       # trận mưa lớn: tổng 3 ngày ≥ 150 mm
DECLUSTER_DAYS = 5         # hai trận cách nhau < 5 ngày coi là một

sns.set_theme(style="whitegrid", context="paper", font_scale=1.05)
ACC, WARN, INK = "#00666e", "#b35c00", "#1a1a1a"


def save(fig, name: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"    → reports/figures/report/{name}")


def _era(hy: pl.Expr) -> pl.Expr:
    return (pl.when(hy.is_between(*PRE)).then(pl.lit("pre"))
              .when(hy.is_between(*POST)).then(pl.lit("post")))


# ------------------------------------------------------------------ R1

def yearly_metrics(d: pl.DataFrame) -> pl.DataFrame:
    """Chỉ số theo năm thuỷ văn (09 → 08)."""
    hy = pl.col("date").dt.year() + (pl.col("date").dt.month() >= 9).cast(pl.Int32)
    d = d.with_columns(hy=hy,
                       q30=pl.col("discharge").rolling_mean(30),
                       dq=pl.col("discharge").diff().abs())
    dry = pl.col("date").dt.month().is_between(3, 8)
    # Thể tích dòng chảy / thể tích mưa: m³/s·ngày → m³, mm·km² → m³
    to_m3 = 86400.0
    return (d.group_by("hy").agg(
                pl.len().alias("n_days"),
                pl.col("q30").filter(dry).min().alias("low_flow_30d"),
                (pl.col("discharge").sum() * to_m3
                 / (pl.col("rain_basin").sum() / 1000 * AREA_KM2 * 1e6))
                .alias("runoff_ratio"),
                (pl.col("dq").sum() / pl.col("discharge").sum()).alias("flashiness_rb"),
                pl.col("discharge").max().alias("q_max"))
             .filter(pl.col("n_days") >= 360)
             .with_columns(era=_era(pl.col("hy")))
             .sort("hy"))


def storm_events(d: pl.DataFrame) -> pl.DataFrame:
    """Trận mưa lớn đã tách cụm: mỗi trận lấy ngày có tổng mưa 3 ngày lớn nhất.

    Phản ứng = đỉnh Q trong 3 ngày sau / tổng mưa 3 ngày (m³/s mỗi mm). Cùng
    lượng mưa mà phản ứng nhỏ đi sau khi có hồ ⇒ hồ đang cắt lũ trong GloFAS.
    """
    peak_next = pl.max_horizontal(pl.col("discharge").shift(-k) for k in range(0, 4))
    c = (d.with_columns(q_peak=peak_next)
          .filter(pl.col("rain_basin_roll3") >= EVENT_RAIN3_MM)
          .sort("rain_basin_roll3", descending=True))
    kept: list = []
    for row in c.iter_rows(named=True):
        if all(abs((row["date"] - k).days) >= DECLUSTER_DAYS for k in kept):
            kept.append(row["date"])
    hy = pl.col("date").dt.year() + (pl.col("date").dt.month() >= 9).cast(pl.Int32)
    return (c.filter(pl.col("date").is_in(kept))
             .with_columns(response=pl.col("q_peak") / pl.col("rain_basin_roll3"),
                           era=_era(hy))
             .select("date", "era", "rain_basin_roll3", "api", "q_peak", "response")
             .sort("date"))


def era_tests(yr: pl.DataFrame, ev: pl.DataFrame) -> pl.DataFrame:
    rows = []
    expect = {"low_flow_30d": "higher", "runoff_ratio": "similar",
              "flashiness_rb": "lower", "response": "lower"}
    for metric, src in [("low_flow_30d", yr), ("runoff_ratio", yr),
                        ("flashiness_rb", yr), ("response", ev)]:
        a = src.filter(pl.col("era") == "pre")[metric].drop_nulls().to_numpy()
        b = src.filter(pl.col("era") == "post")[metric].drop_nulls().to_numpy()
        p = mannwhitneyu(a, b).pvalue
        rows.append({"metric": metric, "n_pre": len(a), "n_post": len(b),
                     "median_pre": float(np.median(a)), "median_post": float(np.median(b)),
                     "change_pct": float((np.median(b) / np.median(a) - 1) * 100),
                     "p_mannwhitney": float(p), "if_dams_modelled": expect[metric]})
    return pl.DataFrame(rows)


def plot_era(yr: pl.DataFrame, ev: pl.DataFrame, t: pl.DataFrame) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.8))
    panels = [("low_flow_30d", yr, "Dry-season low flow\n(min 30-day mean, m³/s)"),
              ("flashiness_rb", yr, "Flashiness\n(Richards–Baker index)"),
              ("runoff_ratio", yr, "Runoff ratio\n(river volume / rain volume)"),
              ("response", ev, f"Storm response\n(peak Q per mm, rain3 ≥ {EVENT_RAIN3_MM} mm)")]
    order = ["pre", "post"]
    labels = [f"{PRE[0]}–{PRE[1]}\nbefore dams", f"{POST[0]}–{POST[1]}\nwith dams"]
    for ax, (m, src, title) in zip(axes, panels):
        pdf = src.filter(pl.col("era").is_not_null()).select("era", m).to_pandas()
        sns.boxplot(data=pdf, x="era", y=m, order=order, ax=ax, width=0.5,
                    palette=[ACC, WARN], hue="era", legend=False, showfliers=False)
        sns.stripplot(data=pdf, x="era", y=m, order=order, ax=ax, color=INK,
                      size=3, alpha=0.6)
        p = t.filter(pl.col("metric") == m)["p_mannwhitney"][0]
        ax.set_title(f"{title}\nMann–Whitney p = {p:.2f}", fontsize=9)
        ax.set_xticks([0, 1], labels, fontsize=8)
        ax.set_xlabel("")
        ax.set_ylabel("")
    fig.suptitle("R1 · Does the GloFAS series change after the upstream dams were built?",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    save(fig, "res1_dam_era_en.png")


# ------------------------------------------------------------------ R2

def release_check(d: pl.DataFrame) -> pl.DataFrame | None:
    """So GloFAS (ngày t hoặc t+1, lấy giá trị lớn hơn) với hai cận dưới từ báo:

    * `below_release` — GloFAS < tổng xả NHỎ NHẤT trong ngày của hai hồ.
    * `below_inflow`  — GloFAS < tổng nước đổ VÀO hai hồ. Hai hồ chỉ chiếm
      1 232 / ~1 540 km² lưu vực, nên dòng chảy tự nhiên tại Kim Long còn lớn hơn.
      Sai ở đây là GloFAS mô phỏng thiếu chính trận lũ, không phải do hồ.
    """
    if not reservoirs.RELEASES.exists():
        print("  (chưa có data/external/reservoir_releases.csv — bỏ qua R2)")
        return None
    up = reservoirs.upstream_daily(reservoirs.load_releases())
    q = d.select(pl.col("date").cast(pl.Date), "discharge",
                 pl.col("discharge").shift(-1).alias("discharge_next"))
    best = pl.max_horizontal("discharge", "discharge_next")
    return (up.join(q, on="date", how="left")
              .with_columns(glofas_best=best)
              .with_columns(
                  below_release=pl.col("glofas_best") < pl.col("q_release_upstream_min"),
                  below_inflow=pl.col("glofas_best") < pl.col("q_inflow_upstream"),
                  ratio_inflow=pl.col("q_inflow_upstream") / pl.col("glofas_best")))


def plot_release(r: pl.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    hi = float(max(r["q_inflow_upstream"].max() or 0, r["q_release_upstream_min"].max() or 0,
                   r["glofas_best"].max())) * 1.08
    ax.plot([0, hi], [0, hi], color=INK, lw=1, ls="--")
    ax.fill_between([0, hi], [0, 0], [0, hi], color=WARN, alpha=0.08)
    ax.text(hi * 0.97, hi * 0.04, "GloFAS too low\n(impossible in the real river)",
            ha="right", va="bottom", fontsize=8, color=WARN)
    rel = r.drop_nulls("q_release_upstream_min")
    inf = r.drop_nulls("q_inflow_upstream")
    ax.scatter(rel["q_release_upstream_min"], rel["glofas_best"], color=ACC, s=32,
               label=f"dam RELEASE, Tả Trạch + Bình Điền (n={rel.height})")
    ax.scatter(inf["q_inflow_upstream"], inf["glofas_best"], marker="^", color=WARN,
               s=36, label=f"natural INFLOW to the two dams (n={inf.height})")
    for row in inf.filter(pl.col("q_inflow_upstream") > 4000).iter_rows(named=True):
        ax.annotate(f"{row['date']:%d/%m/%Y}", (row["q_inflow_upstream"], row["glofas_best"]),
                    xytext=(-6, 6), textcoords="offset points", ha="right", fontsize=7)
    ax.set_xlim(0, hi)
    ax.set_ylim(0, hi)
    ax.set_xlabel("Reported by the province (m³/s, lower bound)")
    ax.set_ylabel("GloFAS at Kim Long cell, max of day t and t+1 (m³/s)")
    ax.set_title("R2 · Reported dam flows vs GloFAS", loc="left", fontsize=11)
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    save(fig, "res2_release_vs_glofas_en.png")


def main() -> int:
    d = pl.read_parquet(PANEL)
    print(f"Panel mở rộng: {d.height} ngày, {d['date'].min():%Y-%m-%d} → "
          f"{d['date'].max():%Y-%m-%d}")

    print("\nR1 — GloFAS trước và sau khi có hồ")
    yr = yearly_metrics(d)
    ev = storm_events(d)
    t = era_tests(yr, ev)
    yr.write_csv(OUT_ERA)
    t.write_csv(OUT_TEST)
    with pl.Config(tbl_rows=10, tbl_cols=10, float_precision=3, tbl_width_chars=140):
        print(t)
    plot_era(yr, ev, t)

    print("\nR2 — Số xả công bố so với GloFAS")
    r = release_check(d)
    if r is not None:
        r.write_csv(OUT_REL)
        r = r.drop_nulls("glofas_best")
        nr = r.drop_nulls("q_release_upstream_min").height
        ni = r.drop_nulls("q_inflow_upstream").height
        print(f"  GloFAS < tổng xả (cận dưới) : {int(r['below_release'].sum())}/{nr} ngày")
        print(f"  GloFAS < nước đổ vào 2 hồ  : {int(r['below_inflow'].sum())}/{ni} ngày")
        with pl.Config(tbl_rows=40, float_precision=0, tbl_width_chars=160):
            print(r.select("date", "q_release_upstream_min", "q_inflow_upstream",
                           "n_upstream", "n_inflow", "glofas_best"))
        plot_release(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
