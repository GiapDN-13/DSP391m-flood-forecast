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

Nguồn vệ tinh (``imerg``, ``gsmap``, ``gsmap_gc``, ``gsmap_nrt`` — khoá của
``hf.GEE``, 0,1°, 1998 → nay, toàn bộ lưu trữ): cùng danh sách file với
``hf.load_gee`` (:func:`gee_files`), chỉ giữ ô có trong bảng trọng số, rồi
:func:`to_hourly_spark` gộp bước 30 phút của IMERG về giờ đúng như ``hf.to_hourly``.
``--bench`` ghi một dòng đo vào ``reports/spark/full_scale_bench.csv``; ``--compare``
thêm tóm tắt so khớp vào ``reports/spark/full_scale_parity.csv``.

    python -m src.distributed.spark_hourly --source era5 --mode local --cores 8 --compare
    python -m src.distributed.spark_hourly --source pccs --mode local --cores 4 --compare
    python -m src.distributed.spark_hourly --source imerg --years 2020 --mode local --cores 8 --compare
    python -m src.distributed.spark_hourly --source imerg --polars-only --bench   # chỉ đo Polars
    spark-submit --master spark://spark-master:7077 src/distributed/spark_hourly.py \\
        --mode cluster --cores-max 8 --executor-cores 4 --source era5 --compare
    spark-submit --master spark://spark-master:7077 src/distributed/spark_hourly.py \\
        --mode cluster --cores-max 8 --executor-cores 4 --source imerg --compare --bench --tag cluster_2w
    spark-submit --master "local[8]" --driver-memory 4g src/distributed/spark_hourly.py \\
        --mode local --cores 8 --source imerg --bench --tag docker_local8_drv4g
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import os
import platform
import sys
import time
from pathlib import Path

import polars as pl

from src import config as cfg
from src.distributed.spark_etl import _n_executors
from src.distributed.spark_session import describe, get_spark, hadoop_io_ok
from src.features import hourly_features as hf

OUT_ROOT = cfg.DATA_INTERIM / "spark"
REPORT_DIR = cfg.ROOT / "reports" / "spark"
BENCH = REPORT_DIR / "full_scale_bench.csv"
PARITY = REPORT_DIR / "full_scale_parity.csv"
SRC_GLOB = {"era5": (hf.HOURLY_DIR, "rh_*.parquet", "precipitation"),
            "pccs": (hf.PCCS_DIR, "pccs_*.parquet", "precip_mm")}
SOURCES = ("era5", "pccs", *hf.GEE)
COORD_DECIMALS = 4                     # như basins.basin_mean


def out_path(source: str) -> Path:
    return OUT_ROOT / f"hourly_features_{source}.parquet"


def parity_path(source: str, host: str) -> Path:
    return OUT_ROOT / f"hourly_parity_{source}_{host}.csv"


def gee_files(source: str, months: list[str] | None = None,
              years: list[int] | None = None) -> list[Path]:
    """Đúng danh sách file mà ``hf.load_gee`` đọc: file tháng ``<tiền tố>_YYYYMM`` +
    (nguồn JAXA) ngày lẻ chưa gộp ``_parts/YYYYMMDD``, lọc theo tháng/năm của tên file."""
    folder, _, _ = hf.GEE[source]
    base = hf.SAT_ROOT.get(source, hf.GEE_DIR) / folder
    files = sorted(base.glob(f"{folder}_*.parquet")) + sorted((base / "_parts").glob("*.parquet"))

    def ym(f: Path) -> str:
        return f.stem[-6:] if f.stem.startswith(folder) else f.stem[:6]

    if months:
        keep = {m.replace("-", "") for m in months}
        files = [f for f in files if ym(f) in keep]
    if years:
        files = [f for f in files if int(ym(f)[:4]) in set(years)]
    if not files:
        raise FileNotFoundError(f"không có file {folder} trong {base}")
    return files


def source_files(source: str, months: list[str] | None = None,
                 years: list[int] | None = None) -> list[Path]:
    """File đầu vào của một nguồn (để đếm dòng/MB cho bảng đo)."""
    if source in hf.GEE:
        return gee_files(source, months, years)
    src, pattern, _ = SRC_GLOB[source]
    files = sorted(src.glob(pattern))
    if source == "era5" and years:
        files = [f for f in files if int(f.stem.rsplit("_", 1)[1]) in set(years)]
    if source == "pccs" and months:
        files = [f for f in files if f.stem.split("_")[1] in set(months)]
    return files


def input_size(files: list[Path]) -> tuple[int, float]:
    """(số dòng theo metadata parquet, MB trên đĩa) — không đọc dữ liệu."""
    import pyarrow.parquet as pq

    rows = sum(pq.read_metadata(f).num_rows for f in files)
    return rows, sum(f.stat().st_size for f in files) / 1e6


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
                use_hadoop: bool | None = None, months: list[str] | None = None,
                years: list[int] | None = None):
    """Nguồn mưa → DataFrame Spark (time, lat, lon, precip) đã chuẩn hoá, lượng mưa GIỜ.

    ERA5 và nguồn vệ tinh chỉ giữ các ô có trong bảng trọng số (như
    ``hf.load_era5``/``hf.load_gee`` với ``cells=...``). Nguồn vệ tinh: cường độ
    mm/giờ theo bước gốc → lượng mưa giờ qua :func:`to_hourly_spark`.
    """
    from pyspark.sql import functions as F

    if use_hadoop is None:
        use_hadoop = hadoop_io_ok()
    gee = source in hf.GEE
    if use_hadoop:
        files = source_files(source, months, years)
        if not files:
            raise FileNotFoundError(f"không có file đầu vào cho {source}")
        pcol = hf.GEE[source][1] if gee else SRC_GLOB[source][2]
        sdf = (spark.read.parquet(*[f.as_posix() for f in files])
               .select("time", "lat", "lon", F.col(pcol).alias("precip")))
    else:
        if gee:     # bước gốc, chưa gộp giờ — phần gộp giờ do Spark làm
            raw = hf.load_gee(source, months, years, cells=weights, hourly=False)
        elif source == "era5":
            raw = hf.load_era5(years, cells=weights)
        else:
            raw = hf.load_pccs(months)
        sdf = spark.createDataFrame(raw.to_arrow())
    sdf = normalize(sdf)
    if source != "pccs" and weights is not None and use_hadoop:
        cells = spark.createDataFrame(weights.select("lat", "lon").unique().to_arrow())
        cells = cells.select(*[F.round(F.col(c).cast("double"), COORD_DECIMALS).alias(c)
                               for c in ("lat", "lon")])
        sdf = sdf.join(F.broadcast(cells), on=["lat", "lon"], how="left_semi")
    if gee:
        sdf = to_hourly_spark(sdf, hf.GEE[source][2])
    return sdf


def to_hourly_spark(sdf, step_min: int):
    """Bản Spark của ``hf.to_hourly``: cường độ mm/giờ theo bước ``step_min`` phút
    (nhãn CUỐI bước) → lượng mưa giờ (mm), nhãn CUỐI giờ.

    Bước kết thúc lúc L thuộc giờ kết thúc ⌈L⌉ (IMERG: giờ HH:00 = nửa giờ kết thúc
    HH−1:30 + nửa giờ kết thúc HH:00). Mỗi bước = cường độ × step_min/60. Giờ thiếu
    dù một bước (hoặc bước rỗng) → rỗng. Với 2 bước/giờ thì tổng không phụ thuộc thứ
    tự cộng (a + b = b + a) nên ``F.sum`` trùng bit với Polars. Không kiểm nhãn lệch
    bước / trùng (time, lat, lon) như bản Polars — dữ liệu đã qua kiểm đó.
    """
    from pyspark.sql import functions as F

    if step_min <= 0 or 60 % step_min:
        raise ValueError("step_min phải là ước của 60")
    amount = F.col("precip") * F.lit(step_min / 60)
    if step_min == 60:
        return sdf.select("time", "lat", "lon", amount.alias("precip"))
    n = 60 // step_min
    hour = (F.date_trunc("hour", F.col("time") - F.expr(f"INTERVAL {step_min} MINUTES"))
            + F.expr("INTERVAL 1 HOUR"))
    g = (sdf.withColumn("_h", hour).groupBy("_h", "lat", "lon")
         .agg(F.count(F.lit(1)).alias("_n"), F.sum(F.col("precip").isNull().cast("int")).alias("_nn"),
              F.sum(amount).alias("_s")))
    ok = (F.col("_n") == n) & (F.col("_nn") == 0)
    return g.select(F.col("_h").alias("time"), "lat", "lon",
                    F.when(ok, F.col("_s")).otherwise(F.lit(None).cast("double")).alias("precip"))


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


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _append_csv(path: Path, rows: list[dict]) -> None:
    """Thêm dòng vào CSV báo cáo (giữ dòng cũ; cột mới thì nối chéo như ``spark_etl``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new = pl.DataFrame(rows).cast(pl.Utf8)
    if path.exists():
        new = pl.concat([pl.read_csv(path, infer_schema_length=0), new], how="diagonal")
    new.write_csv(path)


def _period(a) -> str:
    if a.months:
        return f"months={','.join(a.months)}"
    if a.years:
        return f"years={','.join(map(str, a.years))}"
    return "full"


def polars_reference(source: str, years: list[int] | None, months: list[str] | None,
                     weights: pl.DataFrame | None, areas: dict[str, float] | None
                     ) -> tuple[pl.DataFrame, pl.DataFrame, float]:
    """Bản Polars cùng phép tính (chuỗi giờ theo đơn vị, đặc trưng ngày, số giây).
    Nguồn vệ tinh: đúng ``hf.build_source`` (đọc + gộp giờ + lưu vực + ngày)."""
    t = time.perf_counter()
    if source in hf.GEE:
        hb, f, _ = hf.build_source(source, years=years, months=months)
    else:
        raw = hf.load_era5(years, cells=weights) if source == "era5" else hf.load_pccs(months)
        hb = hf.basin_hourly(raw, weights, areas)
        f = hf.daily_features(hb, [*areas, hf.WHOLE])
    return hb, f, time.perf_counter() - t


def _bench_row(a, engine: str, master: str, files: list[Path], **kw) -> dict:
    rows_files, mb = input_size(files)
    return {"run_at": _now(), "tag": a.tag or "", "source": a.source, "period": _period(a),
            "host": _host(), "engine": engine, "master": master, "files": len(files),
            "mb_on_disk": round(mb, 1), "rows_in_files": rows_files, **kw}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", choices=SOURCES, default="era5")
    ap.add_argument("--years", type=int, nargs="*", default=None,
                    help="chỉ các năm này (era5, nguồn vệ tinh — theo tháng của tên file)")
    ap.add_argument("--months", nargs="*", default=None,
                    help="chỉ các tháng YYYYMM này (pccs, nguồn vệ tinh)")
    ap.add_argument("--mode", choices=["local", "cluster"], default=None)
    ap.add_argument("--cores", type=int, default=None, help="local[N]")
    ap.add_argument("--cores-max", type=int, default=None, help="spark.cores.max (cluster)")
    ap.add_argument("--executor-cores", type=int, default=None)
    ap.add_argument("--executor-memory", default="1500m")
    ap.add_argument("--driver-memory", default="2g",
                    help="chỉ có tác dụng khi chạy bằng `python -m`; qua spark-submit thì JVM "
                         "driver đã chạy rồi ⇒ phải truyền `spark-submit --driver-memory 4g` "
                         "(local[8] trong container với heap mặc định 1g đã hết bộ nhớ với IMERG)")
    ap.add_argument("--partitions", type=int, default=None, help="spark.sql.shuffle.partitions")
    ap.add_argument("--compare", action="store_true",
                    help="chạy cả bản Polars (hourly_features) rồi so từng cột")
    ap.add_argument("--bench", action="store_true",
                    help="ghi một dòng đo vào reports/spark/full_scale_bench.csv")
    ap.add_argument("--polars-only", action="store_true",
                    help="chỉ đo bản Polars (hf.build_source), không khởi động Spark")
    ap.add_argument("--tag", default=None, help="nhãn cấu hình trong bảng đo")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    out = a.out or out_path(a.source)
    files = source_files(a.source, a.months, a.years)

    w_path = hf.WEIGHTS[a.source]
    w_try = pl.read_csv(w_path) if w_path.exists() else None
    have_basins = w_path.exists() and hf.SUBBASIN_GEOJSON.exists()

    if a.polars_only:
        weights, areas, _ = hf.load_weights(a.source) if have_basins else (None, None, None)
        hb_pl, f_pl, t_pl = polars_reference(a.source, a.years, a.months, weights, areas)
        print(f"Polars ({a.source}, {_period(a)}): {hb_pl.height} giờ → {f_pl.height} ngày "
              f"— {t_pl:.1f} s")
        if a.bench:
            _append_csv(BENCH, [_bench_row(a, "polars", "polars", files, n_executors=0,
                                           cores=os.cpu_count(), hours_out=hb_pl.height,
                                           days_out=f_pl.height, cols_out=f_pl.width - 1,
                                           seconds_startup=0.0, seconds_total=round(t_pl, 2),
                                           status="ok")])
            print(f"→ {BENCH}")
        return 0

    t0 = time.perf_counter()
    spark = get_spark(a.mode, app_name=f"hourly-features-{a.source}", cores=a.cores,
                      cores_max=a.cores_max, executor_cores=a.executor_cores,
                      executor_memory=a.executor_memory, driver_memory=a.driver_memory,
                      shuffle_partitions=a.partitions)
    t_start = time.perf_counter() - t0
    info = describe(spark)
    use_hadoop = hadoop_io_ok()

    t1 = time.perf_counter()
    sdf = read_source(spark, a.source, w_try, use_hadoop, a.months, a.years).cache()
    weights, areas, how = hf.load_weights(a.source, None if have_basins else cells_of(sdf))
    hw, feats = hourly_features_spark(spark, sdf, weights, areas)
    hw = hw.cache()
    f_spark = to_polars(feats)
    t_spark = time.perf_counter() - t1
    rows_in = sdf.count()                    # đếm SAU khi đo để không ưu ái lần chạy
    n_exec = _n_executors(spark)
    print(f"Spark ({info['master']}, {n_exec} executor, "
          f"{'đọc bằng Spark' if use_hadoop else 'Polars→Arrow→Spark'}): {len(files)} file, "
          f"{rows_in:,} dòng giờ×ô → {f_spark.height} ngày × {f_spark.width - 1} cột, "
          f"gộp theo {how} — {t_spark:.1f} s (khởi động {t_start:.1f} s)")
    out.parent.mkdir(parents=True, exist_ok=True)
    f_spark.write_parquet(out)
    print(f"→ {out}")
    h_spark = to_polars(hw) if a.compare else None
    spark.stop()                             # trả RAM của executor trước khi chạy Polars

    if a.bench:
        engine = "spark" if use_hadoop else "spark_arrow"
        _append_csv(BENCH, [_bench_row(a, engine, info["master"], files, n_executors=n_exec,
                                       cores=info["cores_used"], rows_hourly_cells=rows_in,
                                       days_out=f_spark.height, cols_out=f_spark.width - 1,
                                       seconds_startup=round(t_start, 2),
                                       seconds_total=round(t_spark, 2), status="ok")])
        print(f"→ {BENCH}")

    if a.compare:
        hb_pl, f_pl, t_pl = polars_reference(a.source, a.years, a.months, weights, areas)
        p_day = parity(f_pl, f_spark, "date").with_columns(pl.lit("daily").alias("level"))
        p_hr = parity(hb_pl, h_spark, "time").with_columns(pl.lit("hourly").alias("level"))
        rep = pl.concat([p_hr, p_day]).with_columns(
            pl.lit(a.source).alias("source"), pl.lit(_host()).alias("host"),
            pl.lit(info["master"]).alias("master"),
            pl.lit(round(t_spark, 2)).alias("seconds_spark"),
            pl.lit(round(t_pl, 2)).alias("seconds_polars"),
            pl.lit(_now()).alias("run_at"))
        rep.write_csv(parity_path(a.source, _host()))
        with pl.Config(tbl_rows=80, tbl_width_chars=160):
            print(rep.select("level", "column", "n_both", "n_null_mismatch", "n_exact_equal",
                             "max_abs_diff"))
        s_hr, s_day = summarize(p_hr), summarize(p_day)
        print(f"Giờ : {s_hr}")
        print(f"Ngày: {s_day}")
        print(f"Polars cùng phép tính: {t_pl:.1f} s · Spark: {t_spark:.1f} s")
        print(f"→ {parity_path(a.source, _host())}")
        if a.bench or a.source in hf.GEE:
            _append_csv(PARITY, [{
                "run_at": _now(), "tag": a.tag or "", "source": a.source, "period": _period(a),
                "host": _host(), "master": info["master"], "level": lvl, "rows": n,
                "columns": s["columns"], "values_compared": s["cells_compared"],
                "values_not_bitwise_equal": s["cells_not_bitwise_equal"],
                "null_mismatch": s["null_mismatch"], "rows_only_one_side": s["rows_only_one_side"],
                "max_abs_diff": s["max_abs_diff"], "seconds_spark": round(t_spark, 2),
                "seconds_polars": round(t_pl, 2)}
                for lvl, s, n in (("hourly", s_hr, hb_pl.height), ("daily", s_day, f_pl.height))])
            print(f"→ {PARITY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
