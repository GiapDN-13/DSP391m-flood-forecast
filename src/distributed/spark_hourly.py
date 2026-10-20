"""Đặc trưng mưa THEO GIỜ theo lưu vực con — bản Spark của ``src/features/hourly_features.py``.

Cùng định nghĩa, cùng hằng số (đọc thẳng từ ``hourly_features``): lưới giờ
(time, lat, lon, precip) → chuỗi giờ 5 lưu vực con + toàn lưu vực ``basin`` →
9 đặc trưng/ngày/đơn vị, cột ``hr_{đặc trưng}_{đơn vị}``. Kết quả phải TRÙNG bản
Polars; ``--compare`` chạy cả hai rồi ghi sai khác lớn nhất từng cột
(``tests/test_spark_parity.py`` khoá điều này trên dữ liệu nhỏ).

Để trùng tới từng bit chứ không chỉ "gần bằng" (lệch 1e-16 cũng đủ lật ngưỡng
giờ mưa ≥ 1 mm hay đỉnh ≥ 0,1 mm khi mọi ô cùng 0,1 mm):

* Tổng trong nhóm cộng TUẦN TỰ đúng thứ tự Polars cộng (ô theo lat, lon; giờ theo
  thời gian) bằng ``aggregate`` trên mảng đã sắp. ``F.sum`` cộng theo thứ tự dòng
  tới executor, không cố định.
* Toàn lưu vực = tổng có trọng số 5 lưu vực con theo đúng cây cộng của
  ``pl.sum_horizontal`` (rayon chia đôi: ((0+1)+(2+(3+4)))) — xem ``_tree_sum``.
* sin/cos giờ đỉnh lấy từ bảng 24 giá trị tính bằng chính biểu thức Polars thay
  vì ``F.sin`` của JVM.

Đọc dữ liệu: Linux/cụm → Spark tự đọc parquet (mỗi executor đọc một phần);
Windows (không có winutils) → Polars đọc rồi đưa vào Spark qua Arrow
(như ``spark_etl``). Kết quả cuối nhỏ (~4 300 ngày × 54 cột) nên gom về driver và
ghi bằng Polars ở cả hai chế độ.

    python -m src.distributed.spark_hourly --source era5 --mode local --cores 8 --compare
    python -m src.distributed.spark_hourly --source pccs --mode local --cores 4 --compare
    spark-submit --master spark://spark-master:7077 src/distributed/spark_hourly.py \\
        --mode cluster --cores-max 8 --executor-cores 4 --source era5 --compare
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import platform
import sys
import time
from pathlib import Path

import polars as pl

from src import config as cfg
from src.distributed.spark_session import describe, get_spark, hadoop_io_ok
from src.features import hourly_features as hf

OUT_ROOT = cfg.DATA_INTERIM / "spark"
SRC_GLOB = {"era5": (hf.HOURLY_DIR, "rh_*.parquet", "precipitation"),
            "pccs": (hf.PCCS_DIR, "pccs_*.parquet", "precip_mm")}
COORD_DECIMALS = 4                     # như basins.basin_mean


def out_path(source: str) -> Path:
    return OUT_ROOT / f"hourly_features_{source}.parquet"


def parity_path(source: str, host: str) -> Path:
    return OUT_ROOT / f"hourly_parity_{source}_{host}.csv"


# ================================================================ tiện ích cộng

def tree_order(items: list):
    """Cây cộng của ``pl.sum_horizontal``: rayon chia đôi tại len//2 tới khi còn 1 phần
    tử. 5 cột → ((0, 1), (2, (3, 4))). Đúng khi Polars có ≥ 2 luồng."""
    if len(items) == 1:
        return items[0]
    mid = len(items) // 2
    return (tree_order(items[:mid]), tree_order(items[mid:]))


def _tree_sum(tree):
    if isinstance(tree, tuple):
        return _tree_sum(tree[0]) + _tree_sum(tree[1])
    return tree


def _fold(arr: str, field: str):
    """Tổng tuần tự từ 0,0 theo thứ tự mảng (giống sum nhóm của Polars)."""
    from pyspark.sql import functions as F

    return F.aggregate(F.col(arr), F.lit(0.0), lambda acc, x: acc + x[field])


def _peak_table() -> tuple[dict[int, float], dict[int, float]]:
    """sin/cos(2π·giờ/24) tính bằng đúng biểu thức của ``hourly_features``."""
    h = pl.DataFrame({"h": list(range(24))}).with_columns(pl.col("h").cast(pl.Float64))
    ang = 2 * math.pi * pl.col("h") / 24
    t = h.select(pl.col("h").cast(pl.Int32), ang.sin().alias("s"), ang.cos().alias("c"))
    return dict(zip(t["h"], t["s"])), dict(zip(t["h"], t["c"]))


def _lookup(table: dict[int, float], col: str):
    from pyspark.sql import functions as F

    m = F.create_map(*[x for k, v in table.items() for x in (F.lit(k), F.lit(v))])
    return F.element_at(m, F.col(col))


# ================================================================ đọc

def read_source(spark, source: str, weights: pl.DataFrame | None,
                use_hadoop: bool | None = None, months: list[str] | None = None):
    """Nguồn mưa giờ → DataFrame Spark (time, lat, lon, precip) đã chuẩn hoá.

    ERA5 chỉ giữ các ô có trong bảng trọng số (như ``hf.load_era5(cells=...)``).
    """
    from pyspark.sql import functions as F

    if use_hadoop is None:
        use_hadoop = hadoop_io_ok()
    src, pattern, pcol = SRC_GLOB[source]
    if use_hadoop:
        files = sorted(src.glob(pattern))
        if source == "pccs" and months:
            files = [f for f in files if f.stem.split("_")[1] in set(months)]
        if not files:
            raise FileNotFoundError(f"không có {pattern} trong {src}")
        sdf = (spark.read.parquet(*[f.as_posix() for f in files])
               .select("time", "lat", "lon", F.col(pcol).alias("precip")))
    else:
        raw = (hf.load_era5(cells=weights) if source == "era5" else hf.load_pccs(months))
        sdf = spark.createDataFrame(raw.to_arrow())
    sdf = normalize(sdf)
    if source == "era5" and weights is not None and use_hadoop:
        cells = spark.createDataFrame(weights.select("lat", "lon").unique().to_arrow())
        cells = cells.select(*[F.round(F.col(c).cast("double"), COORD_DECIMALS).alias(c)
                               for c in ("lat", "lon")])
        sdf = sdf.join(F.broadcast(cells), on=["lat", "lon"], how="left_semi")
    return sdf


def normalize(sdf):
    """time → TIMESTAMP (phiên UTC nên giữ nguyên giờ VN), lat/lon làm tròn 4 chữ số,
    mưa → double, NaN → rỗng. KHÔNG kẹp âm, KHÔNG bỏ trùng: y như bản Polars."""
    from pyspark.sql import functions as F

    p = F.col("precip").cast("double")
    return sdf.select(
        F.col("time").cast("timestamp").alias("time"),
        F.round(F.col("lat").cast("double"), COORD_DECIMALS).alias("lat"),
        F.round(F.col("lon").cast("double"), COORD_DECIMALS).alias("lon"),
        F.when(F.isnan(p), F.lit(None).cast("double")).otherwise(p).alias("precip"))


def cells_of(sdf) -> pl.DataFrame:
    """Các ô (lat, lon) có trong dữ liệu — cần cho trọng số dự phòng 3 dải vĩ độ."""
    return pl.from_arrow(sdf.select("lat", "lon").distinct().toArrow())


# ================================================================ lưới → lưu vực

def basin_hourly_spark(spark, sdf, weights: pl.DataFrame, areas: dict[str, float]):
    """(time, lat, lon, precip) → bảng giờ rộng ``time`` + 1 cột mỗi đơn vị + ``basin``,
    trên lưới giờ liên tục 00:00 ngày đầu → 23:00 ngày cuối (giống ``hf.basin_hourly``).

    Trong lưu vực con: Σ(v·w)/Σw trên các ô CÒN số liệu ở giờ đó, cộng tuần tự theo
    (lat, lon). Toàn lưu vực: trung bình theo diện tích, rỗng nếu thiếu 1 lưu vực con.
    """
    from pyspark.sql import functions as F

    units = list(areas)
    w = spark.createDataFrame(
        weights.select(pl.col("subbasin").cast(pl.Utf8), pl.col("lat").cast(pl.Float64),
                       pl.col("lon").cast(pl.Float64), pl.col("weight").cast(pl.Float64))
        .to_arrow())
    w = w.select("subbasin", *[F.round("lat", COORD_DECIMALS).alias("lat"),
                               F.round("lon", COORD_DECIMALS).alias("lon")], "weight")
    j = sdf.join(F.broadcast(w), on=["lat", "lon"], how="inner").where(F.col("precip").isNotNull())
    cell = F.struct("lat", "lon", (F.col("precip") * F.col("weight")).alias("vw"), "weight")
    sub = (j.groupBy("time", "subbasin").agg(F.array_sort(F.collect_list(cell)).alias("_c"))
           .select("time", "subbasin", (_fold("_c", "vw") / _fold("_c", "weight")).alias("v")))
    wide = sub.groupBy("time").pivot("subbasin", units).agg(F.first("v"))

    tot = sum(areas.values())                    # cùng phép cộng Python với hf.basin_hourly
    whole = _tree_sum(tree_order([F.col(u) * F.lit(areas[u] / tot) for u in units]))
    any_null = F.lit(False)
    for u in units:
        any_null = any_null | F.col(u).isNull()
    wide = wide.withColumn(hf.WHOLE, F.when(any_null, F.lit(None).cast("double"))
                           .otherwise(whole))
    return full_hours(wide).select("time", *units, hf.WHOLE)


def full_hours(df):
    """Lưới giờ liên tục từ 00:00 ngày đầu tới 23:00 ngày cuối, giờ thiếu = rỗng."""
    from pyspark.sql import functions as F

    b = df.agg(F.date_trunc("day", F.min("time")).alias("t0"),
               F.date_trunc("day", F.max("time")).alias("t1"))
    grid = b.select(F.explode(F.sequence("t0", F.col("t1") + F.expr("INTERVAL 23 HOURS"),
                                         F.expr("INTERVAL 1 HOUR"))).alias("time"))
    return grid.join(df, on="time", how="left")


# ================================================================ giờ → ngày

def daily_features_spark(hourly_wide, units: list[str]):
    """Bảng giờ rộng → đặc trưng ngày ``date`` + ``hr_{f}_{u}`` (cùng định nghĩa
    ``hf.daily_features``; mọi đặc trưng ngày t chỉ dùng nhãn ≤ 23:00 ngày t)."""
    from pyspark.sql import Window
    from pyspark.sql import functions as F

    h = full_hours(hourly_wide.select("time", *units))
    long = h.unpivot("time", units, "unit", "v")
    v = F.col("v")
    wt = Window.partitionBy("unit").orderBy("time")

    def shift_sum(k: int):
        e = v
        for i in range(1, k):
            e = e + F.lag(v, i).over(wt)
        return e

    h = long.select(
        "unit", "time", "v", shift_sum(3).alias("_r3"), shift_sum(6).alias("_r6"),
        F.to_date("time").alias("date"), F.hour("time").alias("_hour"),
        # ngày quan trắc 07h: nhãn (t−1 08h … t 07h] → t
        F.to_date(F.col("time") + F.expr(f"INTERVAL {23 - hf.OBS_HOUR} HOURS")).alias("_obs"))

    def n_null(c: str):
        return F.sum(F.col(c).isNull().cast("int"))

    day = h.groupBy("unit", "date").agg(
        n_null("v").alias("_nv"), n_null("_r3").alias("_n3"), n_null("_r6").alias("_n6"),
        F.array_sort(F.collect_list(F.struct("_hour", "v"))).alias("_hv"),
        F.max("v").alias("_mx"), F.max("_r3").alias("_m3"), F.max("_r6").alias("_m6"),
        F.count(F.when(v >= hf.WET_MM, 1)).cast("double").alias("_nh"),
        # max theo v, hoà thì giờ SỚM nhất (−giờ lớn nhất) = arg_max của Polars
        F.max(F.struct(v.alias("p"), (-F.col("_hour")).alias("nh"))).alias("_pk"))

    sin_t, cos_t = _peak_table()
    ok = F.col("_nv") == 0

    def strict(cond, e):
        return F.when(cond, e).otherwise(F.lit(None).cast("double"))

    day = day.withColumn("_ph", -F.col("_pk.nh"))
    has_peak = F.col("_mx") >= hf.PEAK_MIN_MM
    day = day.select(
        "unit", "date",
        strict(ok, _fold("_hv", "v")).alias("sum"),
        strict(ok, F.col("_mx")).alias("max1h"),
        strict(F.col("_n3") == 0, F.col("_m3")).alias("max3h"),
        strict(F.col("_n6") == 0, F.col("_m6")).alias("max6h"),
        strict(ok, F.col("_nh")).alias("nh1mm"),
        strict(ok, F.when(has_peak, _lookup(sin_t, "_ph")).otherwise(0.0)).alias("peak_sin"),
        strict(ok, F.when(has_peak, _lookup(cos_t, "_ph")).otherwise(0.0)).alias("peak_cos"))

    obs = (h.groupBy("unit", "_obs")
            .agg(F.count(F.lit(1)).alias("_n"), n_null("v").alias("_nv"),
                 F.array_sort(F.collect_list(F.struct("time", "v"))).alias("_tv"))
            .select("unit", F.col("_obs").alias("date"),
                    strict((F.col("_n") == 24) & (F.col("_nv") == 0), _fold("_tv", "v"))
                    .alias("r24_7h")))
    day = day.join(obs, on=["unit", "date"], how="left")
    # ngày liên tục (lưới giờ đầy đủ) ⇒ lag(1) đúng là hôm trước
    wd = Window.partitionBy("unit").orderBy("date")
    s = F.col("sum")
    day = day.withColumn("r72h", s + F.lag(s, 1).over(wd) + F.lag(s, 2).over(wd))

    wide = day.groupBy("date").pivot("unit", units).agg(*[F.first(f).alias(f) for f in hf.FEATS])
    return wide.select("date", *[F.col(f"{u}_{f}").alias(f"{hf.PREFIX}{f}_{u}")
                                 for u in units for f in hf.FEATS]).orderBy("date")


def hourly_features_spark(spark, sdf, weights: pl.DataFrame, areas: dict[str, float]):
    """(bảng giờ rộng theo đơn vị, đặc trưng ngày) — cả hai là DataFrame Spark."""
    hw = basin_hourly_spark(spark, sdf, weights, areas)
    return hw, daily_features_spark(hw, [*areas, hf.WHOLE])


# ================================================================ về Polars + so khớp

def to_polars(sdf) -> pl.DataFrame:
    """Spark → Polars qua Arrow; ``time`` (UTC trên mặt chữ) → datetime không múi giờ."""
    df = pl.from_arrow(sdf.toArrow())
    if "time" in df.columns and isinstance(df.schema["time"], pl.Datetime):
        df = df.with_columns(pl.col("time").dt.replace_time_zone(None).dt.cast_time_unit("us"))
    return df


def parity(ref: pl.DataFrame, other: pl.DataFrame, key: str) -> pl.DataFrame:
    """So từng cột (``ref`` = Polars, ``other`` = Spark): sai khác tuyệt đối lớn nhất,
    số ô rỗng lệch nhau, số ô bằng nhau tuyệt đối (==)."""
    a = ref.with_columns(pl.col(key).cast(other.schema[key]))
    j = a.join(other, on=key, how="full", suffix="_spark", coalesce=True)
    only_ref = j.height - other.height
    only_other = j.height - a.height
    rows = []
    for c in [c for c in ref.columns if c != key]:
        x = j[c].cast(pl.Float64)
        y = j[f"{c}_spark"].cast(pl.Float64)
        both = x.is_not_null() & y.is_not_null()
        d = (x - y).abs().filter(both)
        rows.append({"column": c, "rows": j.height, "rows_only_polars": only_ref,
                     "rows_only_spark": only_other, "n_both": int(both.sum()),
                     "n_null_mismatch": int((x.is_null() != y.is_null()).sum()),
                     "n_exact_equal": int((x == y).filter(both).sum()),
                     "max_abs_diff": float(d.max()) if d.len() else 0.0})
    return pl.DataFrame(rows)


def summarize(p: pl.DataFrame) -> dict:
    return {"columns": p.height, "max_abs_diff": p["max_abs_diff"].max(),
            "null_mismatch": int(p["n_null_mismatch"].sum()),
            "cells_compared": int(p["n_both"].sum()),
            "cells_not_bitwise_equal": int((p["n_both"] - p["n_exact_equal"]).sum()),
            "rows_only_one_side": int(p["rows_only_polars"].max() + p["rows_only_spark"].max())}


# ================================================================ CLI

def _host() -> str:
    tag = "docker" if Path("/.dockerenv").exists() else "host"
    return f"{platform.system().lower()}-{tag}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", choices=("era5", "pccs"), default="era5")
    ap.add_argument("--mode", choices=["local", "cluster"], default=None)
    ap.add_argument("--cores", type=int, default=None, help="local[N]")
    ap.add_argument("--cores-max", type=int, default=None, help="spark.cores.max (cluster)")
    ap.add_argument("--executor-cores", type=int, default=None)
    ap.add_argument("--partitions", type=int, default=None, help="spark.sql.shuffle.partitions")
    ap.add_argument("--compare", action="store_true",
                    help="chạy cả bản Polars (hourly_features) rồi so từng cột")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    out = a.out or out_path(a.source)

    w_path = hf.WEIGHTS[a.source]
    w_try = pl.read_csv(w_path) if w_path.exists() else None
    t0 = time.perf_counter()
    spark = get_spark(a.mode, app_name=f"hourly-features-{a.source}", cores=a.cores,
                      cores_max=a.cores_max, executor_cores=a.executor_cores,
                      shuffle_partitions=a.partitions)
    t_start = time.perf_counter() - t0
    info = describe(spark)
    use_hadoop = hadoop_io_ok()

    t1 = time.perf_counter()
    sdf = read_source(spark, a.source, w_try, use_hadoop).cache()
    have_basins = w_path.exists() and hf.SUBBASIN_GEOJSON.exists()
    weights, areas, how = hf.load_weights(a.source, None if have_basins else cells_of(sdf))
    hw, feats = hourly_features_spark(spark, sdf, weights, areas)
    hw = hw.cache()
    f_spark = to_polars(feats)
    t_spark = time.perf_counter() - t1
    rows_in = sdf.count()
    units = [*areas, hf.WHOLE]
    print(f"Spark ({info['master']}, {'đọc bằng Spark' if use_hadoop else 'Polars→Arrow→Spark'}):"
          f" {rows_in:,} dòng giờ×ô → {f_spark.height} ngày × {f_spark.width - 1} cột, "
          f"gộp theo {how} — {t_spark:.1f} s (khởi động {t_start:.1f} s)")
    out.parent.mkdir(parents=True, exist_ok=True)
    f_spark.write_parquet(out)
    print(f"→ {out}")

    if a.compare:
        h_spark = to_polars(hw)
        t2 = time.perf_counter()
        raw = hf.load_era5(cells=w_try) if a.source == "era5" else hf.load_pccs()
        hb_pl = hf.basin_hourly(raw, weights, areas)
        f_pl = hf.daily_features(hb_pl, units)
        t_pl = time.perf_counter() - t2
        p_day = parity(f_pl, f_spark, "date").with_columns(pl.lit("daily").alias("level"))
        p_hr = parity(hb_pl, h_spark, "time").with_columns(pl.lit("hourly").alias("level"))
        rep = pl.concat([p_hr, p_day]).with_columns(
            pl.lit(a.source).alias("source"), pl.lit(_host()).alias("host"),
            pl.lit(info["master"]).alias("master"),
            pl.lit(round(t_spark, 2)).alias("seconds_spark"),
            pl.lit(round(t_pl, 2)).alias("seconds_polars"),
            pl.lit(dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")).alias("run_at"))
        rep.write_csv(parity_path(a.source, _host()))
        with pl.Config(tbl_rows=80, tbl_width_chars=160):
            print(rep.select("level", "column", "n_both", "n_null_mismatch", "n_exact_equal",
                             "max_abs_diff"))
        print(f"Giờ : {summarize(p_hr)}")
        print(f"Ngày: {summarize(p_day)}")
        print(f"Polars cùng phép tính: {t_pl:.1f} s · Spark: {t_spark:.1f} s")
        print(f"→ {parity_path(a.source, _host())}")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
