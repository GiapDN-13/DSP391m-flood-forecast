"""So sánh nguồn mưa theo ngày trên toàn lưu vực Kim Long (Report 3).

ERA5 (Open-Meteo, 64 ô 0,1° phủ 92,5 % lưu vực) / IMERG V07 / GSMaP v8 / GSMaP-GC
(Earth Engine, 100 ô 0,1° phủ 100 %), cùng trọng số lưu vực con DEM, cùng ranh
giới ngày (nhãn giờ 00…23 của ngày t). Lấy cột ``hr_sum_basin`` (mưa ngày) và
``hr_r72h_basin`` (mưa 3 ngày t, t−1, t−2) của ``src/features/hourly_features.py``.

Mỗi nguồn, trên các ngày CHUNG của cả 4 nguồn (2015-01 → 2026-08), cả năm và
riêng mùa lũ tháng 9–12 (theo tháng của ngày t):

* tổng mưa, tỷ lệ tổng so với ERA5;
* tương quan Pearson mưa ngày giữa từng cặp nguồn;
* tương quan (Pearson, Spearman) của mưa 3 ngày (t, t−1, t−2) với lưu lượng
  GloFAS ngày t+1 (cột ``discharge`` của ``daily_panel.parquet``).

    python -m src.eval.rain_source_compare
"""

from __future__ import annotations

import sys
from datetime import date

import polars as pl

from src import config as cfg
from src.features import hourly_features as hf

SOURCES = ("era5", "imerg", "gsmap", "gsmap_gc")
START, END = date(2015, 1, 1), date(2026, 8, 31)
FLOOD_MONTHS = (9, 10, 11, 12)
OUT = cfg.ROOT / "reports" / "rain_source_compare.csv"


def _source_cols(df: pl.DataFrame, src: str) -> pl.DataFrame:
    return df.select(pl.col("date").cast(pl.Date),
                     pl.col(f"{hf.PREFIX}sum_{hf.WHOLE}").alias(f"sum_{src}"),
                     pl.col(f"{hf.PREFIX}r72h_{hf.WHOLE}").alias(f"r3d_{src}"))


def load_daily(start: date = START, end: date = END) -> pl.DataFrame:
    """date, sum_<nguồn>, r3d_<nguồn> cho 4 nguồn + q_next = discharge ngày t+1."""
    if not hf.OUT_PANEL.exists():
        raise SystemExit("Thiếu daily_panel_hourly.parquet — chạy hourly_features --source era5")
    df = _source_cols(pl.read_parquet(hf.OUT_PANEL), "era5")
    for s in SOURCES[1:]:
        p = hf.feats_path(s)
        if not p.exists():
            raise SystemExit(f"Thiếu {p.name} — chạy `python -m src.features.hourly_features --source {s}`")
        df = df.join(_source_cols(pl.read_parquet(p), s), on="date", how="left")
    q = (pl.read_parquet(hf.PANEL)
           .select((pl.col("date").cast(pl.Date) - pl.duration(days=1)).alias("date"),
                   pl.col("discharge").alias("q_next")))
    return (df.join(q, on="date", how="left")
              .filter(pl.col("date").is_between(start, end))
              .sort("date"))


def compare(df: pl.DataFrame, period: str) -> list[dict]:
    """Một dòng cho mỗi nguồn trên các ngày có đủ mưa ngày của cả 4 nguồn."""
    d = df.drop_nulls([f"sum_{s}" for s in SOURCES])
    dq = df.drop_nulls([*[f"r3d_{s}" for s in SOURCES], "q_next"])
    tot_e = d["sum_era5"].sum()
    rows = []
    for s in SOURCES:
        tot = d[f"sum_{s}"].sum()
        row = {"period": period, "source": s, "n_days": d.height,
               "date_from": d["date"].min(), "date_to": d["date"].max(),
               "total_mm": tot, "mean_mm_day": tot / d.height,
               "ratio_vs_era5": tot / tot_e}
        for o in SOURCES:
            row[f"r_day_vs_{o}"] = d.select(pl.corr(f"sum_{s}", f"sum_{o}")).item()
        row["n_days_q"] = dq.height
        row["r_r3d_q_next"] = dq.select(pl.corr(f"r3d_{s}", "q_next")).item()
        row["rho_r3d_q_next"] = dq.select(pl.corr(f"r3d_{s}", "q_next", method="spearman")).item()
        rows.append(row)
    return rows


def main() -> int:
    df = load_daily()
    flood = df.filter(pl.col("date").dt.month().is_in(FLOOD_MONTHS))
    res = pl.DataFrame(compare(df, "ca_nam") + compare(flood, "mua_lu_9_12"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.write_csv(OUT, float_precision=4)

    with pl.Config(tbl_rows=20, tbl_cols=20, float_precision=3, tbl_width_chars=220):
        print(f"Toàn lưu vực Kim Long, ngày chung của 4 nguồn ({START} → {END}):")
        print(res.drop("date_from", "date_to"))
        yr = (flood.drop_nulls([f"sum_{s}" for s in SOURCES])
                   .group_by(pl.col("date").dt.year().alias("nam"))
                   .agg(*[pl.col(f"sum_{s}").sum().alias(s) for s in SOURCES])
                   .with_columns(*[(pl.col(s) / pl.col("era5")).alias(f"{s}/era5")
                                   for s in SOURCES[1:]])
                   .sort("nam"))
        print("\nTổng mưa mùa lũ (tháng 9–12) theo năm, mm:")
        print(yr)
    print(f"\n→ {OUT.relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
