"""ETL phân tán: mưa theo giờ → chỉ số mưa theo ngày cho từng ô lưới (Report 4).

Đầu vào  ``data/raw/rain_hourly/rh_{lat}_{lon}_{year}.parquet`` — ERA5 qua Open-Meteo,
         64 ô 0,1°, 2015–2026; cột ``time`` (giờ VN, không kèm múi), ``precipitation``
         (mm trong giờ), ``temperature_2m``, ``relative_humidity_2m``, ``lat``, ``lon``.
Đầu ra   ``data/interim/spark/rain_hourly_daily/year=YYYY/*.parquet`` — mỗi (ô, ngày):

    rain_sum      tổng mưa ngày (mm)
    rain_max1h    giờ mưa to nhất
    rain_max3h    tổng trượt 3 giờ lớn nhất
    rain_max6h    tổng trượt 6 giờ lớn nhất
    n_wet_hours   số giờ mưa ≥ 1 mm
    peak_hour     giờ (VN) của đỉnh 1h, giờ sớm nhất nếu hoà; rỗng nếu cả ngày khô
    n_hours       số giờ có số liệu (kiểm chất lượng, đủ ngày = 24)
    t2m_mean, rh_mean

Có bảng trọng số lưu vực con (``subbasin, lat, lon, weight``) thì thêm
``data/interim/spark/rain_subbasin_daily/``. Gộp ở mức GIỜ rồi mới tính chỉ số
ngày — max-3h của chuỗi trung bình lưu vực khác trung bình các max-3h từng ô.

Quy ước cửa sổ trượt: max 3h/6h của ngày d = max các tổng trượt *kết thúc*
trong ngày d; cửa sổ được kéo sang cuối ngày d-1 (trận mưa 23h–01h không bị cắt
đôi). Cửa sổ theo thời gian (``rangeBetween`` trên giây), không theo số dòng, nên
giờ bị thiếu không làm cửa sổ dãn ra.

Thay nguồn (vd. PERSIANN-CCS 0,04°): đổi ``--src/--pattern``, ánh xạ cột
``--time-col/--precip-col``, ``--weights data/external/basins/weights_pccs_0p04.csv``
và ``--out/--out-sub``; toạ độ làm tròn 3 chữ số nên lưới 0,04° vẫn khớp bảng trọng số.

    python -m src.distributed.spark_etl --mode local --cores 8
    spark-submit --master spark://spark-master:7077 src/distributed/spark_etl.py --mode cluster
    python -m src.distributed.spark_etl --engine polars        # cùng phép tính, 1 máy
"""

from __future__ import annotations

import argparse
import datetime as dt
import platform
import shutil
import sys
import time
from pathlib import Path

import polars as pl

from src import config as cfg
from src.distributed.spark_session import describe, get_spark, hadoop_io_ok

RAW_DIR = cfg.DATA_RAW / "rain_hourly"
PATTERN = "rh_*.parquet"
OUT_ROOT = cfg.DATA_INTERIM / "spark"
OUT_CELL = OUT_ROOT / "rain_hourly_daily"
OUT_POLARS = OUT_ROOT / "rain_hourly_daily_polars"
OUT_SUB = OUT_ROOT / "rain_subbasin_daily"
BENCH = OUT_ROOT / "etl_benchmark.csv"
WEIGHTS = cfg.DATA_EXTERNAL / "basins" / "weights_era5_0p1.csv"

CELL_KEYS = ("lat", "lon")
WET_MM = 1.0              # ngưỡng "giờ có mưa"
ROLL_HOURS = (3, 6)
COORD_DECIMALS = 3        # đủ phân biệt lưới 0,04° (PERSIANN-CCS) lẫn 0,1° (ERA5)
VALUE_DECIMALS = 3        # mưa gốc chỉ có 0,1 mm, làm tròn để bỏ nhiễu dấu phẩy động
DAILY_COLS = ["rain_sum", "rain_max1h", "rain_max3h", "rain_max6h", "n_wet_hours",
              "peak_hour", "n_hours", "t2m_mean", "rh_mean"]


# ------------------------------------------------------------------ đọc

def list_inputs(src: Path = RAW_DIR, pattern: str = PATTERN) -> list[Path]:
    paths = sorted(src.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"Không có file {pattern} trong {src}")
    return paths


def read_hourly_spark(spark, src: Path = RAW_DIR, pattern: str = PATTERN,
                      use_hadoop: bool | None = None):
    """Đọc mưa giờ thành DataFrame Spark.

    Linux/cụm: Spark tự liệt kê và đọc file (mỗi executor đọc một phần).
    Windows không có Hadoop native: Polars đọc rồi chuyển sang Spark qua Arrow.
    """
    if use_hadoop is None:
        use_hadoop = hadoop_io_ok()
    if use_hadoop:
        list_inputs(src, pattern)                       # báo lỗi sớm nếu rỗng
        return spark.read.parquet((src / pattern).as_posix())
    tbl = pl.scan_parquet(list_inputs(src, pattern)).collect().to_arrow()
    return spark.createDataFrame(tbl)


def normalize_hourly(df, time_col: str = "time", precip_col: str = "precipitation"):
    """Chuẩn hoá schema về: time, precipitation, temperature_2m, relative_humidity_2m, lat, lon.

    * ``time`` → TIMESTAMP (phiên UTC nên giữ nguyên giờ VN trên mặt chữ).
    * mưa âm → 0; mưa rỗng giữ rỗng (không đoán là 0).
    * lat/lon làm tròn ``COORD_DECIMALS``; bỏ dòng thiếu toạ độ/thời gian.

    Bỏ trùng (lat, lon, time) để ở ``daily_stats``, sau khi đã chia theo ô — làm
    ở đây sẽ tốn thêm một lần xáo dữ liệu.
    """
    from pyspark.sql import functions as F

    cols = set(df.columns)
    p = F.col(precip_col).cast("double")

    def opt(name: str):
        return F.col(name).cast("double") if name in cols else F.lit(None).cast("double")

    out = df.select(
        F.col(time_col).cast("timestamp").alias("time"),
        F.when(p < 0, F.lit(0.0)).otherwise(p).alias("precipitation"),
        opt("temperature_2m").alias("temperature_2m"),
        opt("relative_humidity_2m").alias("relative_humidity_2m"),
        F.round(F.col("lat").cast("double"), COORD_DECIMALS).alias("lat"),
        F.round(F.col("lon").cast("double"), COORD_DECIMALS).alias("lon"),
    )
    return out.dropna(subset=["time", "lat", "lon"])


# ------------------------------------------------------------- tính toán

def daily_stats(hourly, keys: tuple[str, ...] = CELL_KEYS, n_partitions: int | None = None):
    """Chỉ số mưa theo ngày cho mỗi khoá (ô lưới hoặc lưu vực con).

    Chia lại dữ liệu theo ``keys`` MỘT lần: bỏ trùng (keys, time), cửa sổ trượt
    và groupBy(keys, date) đều dùng lại phân hoạch đó nên Spark không phải xáo dữ
    liệu lần hai. Bỏ trùng cần vì crawler chạy lại có thể ghi chồng giờ.
    """
    from pyspark.sql import Window
    from pyspark.sql import functions as F

    keys = tuple(keys)
    df = hourly.repartition(n_partitions, *keys) if n_partitions else hourly.repartition(*keys)
    df = df.dropDuplicates([*keys, "time"]).withColumn("ts", F.unix_seconds("time"))
    w = Window.partitionBy(*keys).orderBy("ts")
    for h in ROLL_HOURS:
        df = df.withColumn(f"roll{h}", F.sum("precipitation")
                           .over(w.rangeBetween(-(h - 1) * 3600, 0)))
    df = df.withColumn("date", F.to_date("time")).withColumn("hour", F.hour("time"))

    p = F.col("precipitation")
    agg = df.groupBy(*keys, "date").agg(
        F.sum(p).alias("rain_sum"),
        F.max(p).alias("rain_max1h"),
        *[F.max(f"roll{h}").alias(f"rain_max{h}h") for h in ROLL_HOURS],
        F.sum(F.when(p >= WET_MM, 1).otherwise(0)).cast("int").alias("n_wet_hours"),
        # Làm tròn trước khi so: mưa lưu vực con là trung bình có trọng số, lệch ~1e-17
        # tuỳ thứ tự cộng (Windows vs cụm) → hai giờ hoà bị coi là khác, giờ đỉnh nhảy.
        F.max(F.struct(F.round(p, VALUE_DECIMALS).alias("p"),
                       (-F.col("hour")).alias("neg_hour"))).alias("_peak"),
        F.count(p).cast("int").alias("n_hours"),
        F.avg("temperature_2m").alias("t2m_mean"),
        F.avg("relative_humidity_2m").alias("rh_mean"),
    )
    rnd = {c: F.round(c, VALUE_DECIMALS) for c in
           ["rain_sum", "rain_max1h", *[f"rain_max{h}h" for h in ROLL_HOURS],
            "t2m_mean", "rh_mean"]}
    return (agg.withColumns(rnd)
            .withColumn("peak_hour", F.when(F.col("rain_max1h") > 0,
                                            -F.col("_peak.neg_hour")).cast("int"))
            .drop("_peak")
            .withColumn("year", F.year("date"))
            .select(*keys, "date", *DAILY_COLS, "year"))


def load_weights(path: Path = WEIGHTS) -> pl.DataFrame | None:
    """Bảng trọng số ô → lưu vực con. Chưa có file thì trả None (bỏ bước gộp)."""
    if not path or not Path(path).exists():
        return None
    w = pl.read_csv(path)
    need = {"subbasin", "lat", "lon", "weight"}
    if not need <= set(w.columns):
        raise ValueError(f"{path} thiếu cột {sorted(need - set(w.columns))}")
    return (w.select(pl.col("subbasin").cast(pl.Utf8),
                     pl.col("lat").cast(pl.Float64).round(COORD_DECIMALS),
                     pl.col("lon").cast(pl.Float64).round(COORD_DECIMALS),
                     pl.col("weight").cast(pl.Float64))
            .filter(pl.col("weight") > 0))


def subbasin_hourly(spark, hourly, weights: pl.DataFrame):
    """Chuỗi giờ trung bình có trọng số cho từng lưu vực con.

    Chia cho tổng trọng số của các ô CÓ số liệu ở giờ đó — thiếu một ô thì phần
    còn lại tự chuẩn hoá, không kéo trung bình về 0.
    """
    from pyspark.sql import functions as F

    ws = F.broadcast(spark.createDataFrame(weights.to_arrow()))
    # bỏ trùng TRƯỚC khi gộp, không thì giờ bị ghi chồng được tính trọng số hai lần
    j = hourly.dropDuplicates(["lat", "lon", "time"]).join(ws, on=["lat", "lon"], how="inner")
    w = F.col("weight")

    def wavg(c: str):
        return (F.sum(w * F.col(c)) / F.sum(F.when(F.col(c).isNotNull(), w))).alias(c)

    return j.groupBy("subbasin", "time").agg(
        wavg("precipitation"), wavg("temperature_2m"), wavg("relative_humidity_2m"))


def polars_daily_stats(hourly: pl.DataFrame | pl.LazyFrame,
                       keys: tuple[str, ...] = CELL_KEYS) -> pl.DataFrame:
    """Cùng phép tính bằng Polars (1 máy) — mốc so tốc độ và để đối chiếu kết quả Spark.

    Khác biệt duy nhất: giờ rỗng được coi là 0 trong tổng trượt (Polars chưa hỗ trợ
    rolling_*_by trên chuỗi có null); chỉ lệch khi cả cửa sổ đều rỗng.
    """
    keys = list(keys)
    p = pl.col("precipitation")
    lf = (hourly.lazy()
          .with_columns(pl.col("time").cast(pl.Datetime("us")),
                        *[pl.col(k).round(COORD_DECIMALS) for k in keys if k in CELL_KEYS])
          .unique(subset=[*keys, "time"], keep="first")
          .sort([*keys, "time"])
          .with_columns([p.fill_null(0).rolling_sum_by("time", window_size=f"{h}h")
                         .over(keys).alias(f"roll{h}") for h in ROLL_HOURS])
          .with_columns(date=pl.col("time").dt.date(), hour=pl.col("time").dt.hour())
          .group_by([*keys, "date"])
          .agg(rain_sum=p.sum(), rain_max1h=p.max(),
               **{f"rain_max{h}h": pl.col(f"roll{h}").max() for h in ROLL_HOURS},
               n_wet_hours=(p >= WET_MM).sum().cast(pl.Int32),
               peak_hour=pl.col("hour").filter(p.round(VALUE_DECIMALS)
                                               == p.round(VALUE_DECIMALS).max())
               .min().cast(pl.Int32),
               n_hours=p.count().cast(pl.Int32),
               t2m_mean=pl.col("temperature_2m").mean(),
               rh_mean=pl.col("relative_humidity_2m").cast(pl.Float64).mean())
          .with_columns(rain_sum=pl.when(pl.col("n_hours") > 0).then(pl.col("rain_sum")),
                        peak_hour=pl.when(pl.col("rain_max1h") > 0).then(pl.col("peak_hour")))
          .with_columns([pl.col(c).round(VALUE_DECIMALS) for c in
                         ["rain_sum", "rain_max1h", *[f"rain_max{h}h" for h in ROLL_HOURS],
                          "t2m_mean", "rh_mean"]])
          .with_columns(year=pl.col("date").dt.year())
          .select([*keys, "date", *DAILY_COLS, "year"])
          .sort([*keys, "date"]))
    return lf.collect()


# ------------------------------------------------------------------ ghi

def write_daily(df, out: Path, keys: tuple[str, ...] = CELL_KEYS,
                use_hadoop: bool | None = None) -> None:
    """Ghi parquet phân vùng theo năm (``year=YYYY/``), mỗi năm một file."""
    if use_hadoop is None:
        use_hadoop = hadoop_io_ok()
    # "year" phải đứng đầu: bộ ghi phân vùng tự sắp theo year, nếu thứ tự hiện có
    # không bắt đầu bằng year thì nó sắp lại và làm mất thứ tự (ô, ngày)
    df = df.repartition("year").sortWithinPartitions("year", *keys, "date")
    if use_hadoop:
        df.write.mode("overwrite").partitionBy("year").parquet(out.as_posix())
        return
    tbl = df.toArrow()                       # Windows: Spark → Arrow → Polars ghi
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pl.from_arrow(tbl).sort([*keys, "date"]).write_parquet(out, partition_by="year")


def read_daily(out: Path) -> pl.DataFrame:
    """Đọc lại kết quả (cả hai kiểu ghi) bằng Polars."""
    return pl.read_parquet(out / "**" / "*.parquet", hive_partitioning=True)


def compare_outputs(a: pl.DataFrame, b: pl.DataFrame,
                    keys: tuple[str, ...] = CELL_KEYS) -> dict[str, float]:
    """Sai khác lớn nhất từng cột giữa hai kết quả (vd. Spark và Polars)."""
    on = [*keys, "date"]
    j = a.join(b, on=on, how="full", suffix="_b", coalesce=True)
    res: dict[str, float] = {"rows_a": a.height, "rows_b": b.height, "rows_join": j.height}
    for c in DAILY_COLS:
        d = (j[c].cast(pl.Float64) - j[f"{c}_b"].cast(pl.Float64)).abs()
        res[f"maxdiff_{c}"] = float(d.max() or 0.0)
        res[f"nullmismatch_{c}"] = int((j[c].is_null() != j[f"{c}_b"].is_null()).sum())
    return res


# --------------------------------------------------------------- chạy & đo

def _host() -> str:
    tag = "docker" if Path("/.dockerenv").exists() else "host"
    return f"{platform.system().lower()}-{tag}"


def _n_executors(spark) -> int:
    """Số executor thật (bỏ driver). local[*] → 0."""
    try:
        return max(int(spark.sparkContext._jsc.sc().getExecutorMemoryStatus().size()) - 1, 0)
    except Exception:  # noqa: BLE001 — chỉ để ghi log, không được làm hỏng job
        return -1


def append_bench(row: dict) -> None:
    BENCH.parent.mkdir(parents=True, exist_ok=True)
    new = pl.DataFrame([row])
    if BENCH.exists():
        old = pl.read_csv(BENCH, infer_schema_length=0)
        new = pl.concat([old, new.cast(pl.Utf8)], how="diagonal")
    new.write_csv(BENCH)


def run_spark(args) -> dict:
    t0 = time.perf_counter()
    spark = get_spark(args.mode, app_name=f"rain-etl-{args.tag}", cores=args.cores,
                      cores_max=args.cores_max, executor_cores=args.executor_cores,
                      shuffle_partitions=args.partitions)
    t_start = time.perf_counter() - t0
    use_hadoop = hadoop_io_ok()
    files = list_inputs(Path(args.src), args.pattern)

    t1 = time.perf_counter()
    raw = read_hourly_spark(spark, Path(args.src), args.pattern, use_hadoop)
    hourly = normalize_hourly(raw, args.time_col, args.precip_col)
    daily = daily_stats(hourly, CELL_KEYS, args.partitions)
    write_daily(daily, Path(args.out), CELL_KEYS, use_hadoop)
    t_etl = time.perf_counter() - t1

    weights = load_weights(Path(args.weights)) if args.weights else None
    t_sub = None
    if weights is not None:
        t2 = time.perf_counter()
        sub = daily_stats(subbasin_hourly(spark, hourly, weights), ("subbasin",),
                          args.partitions)
        write_daily(sub, Path(args.out_sub), ("subbasin",), use_hadoop)
        t_sub = time.perf_counter() - t2
        print(f"Lưu vực con: {weights['subbasin'].n_unique()} vùng → {args.out_sub}")

    rows_in = raw.count()                    # đếm SAU khi đo để không ưu ái lần chạy
    info = describe(spark)
    info["n_executors"] = _n_executors(spark)
    spark.stop()
    out = read_daily(Path(args.out))
    return {
        "engine": "spark" if use_hadoop else "spark+arrow",
        "master": info["master"], "n_executors": info["n_executors"],
        "cores": info["cores_used"], "default_parallelism": info["default_parallelism"],
        "files": len(files),
        "rows_in": rows_in, "rows_out": out.height,
        "cells": out.select(CELL_KEYS).unique().height,
        "seconds_startup": round(t_start, 2), "seconds_etl": round(t_etl, 2),
        "seconds_subbasin": round(t_sub, 2) if t_sub is not None else None,
    }


def run_polars(args) -> dict:
    files = list_inputs(Path(args.src), args.pattern)
    t1 = time.perf_counter()
    rename = {k: v for k, v in [(args.time_col, "time"), (args.precip_col, "precipitation")]
              if k != v}
    lf = pl.scan_parquet(files).rename(rename)
    daily = polars_daily_stats(lf)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    daily.write_parquet(out, partition_by="year")
    t_etl = time.perf_counter() - t1
    rows_in = pl.scan_parquet(files).select(pl.len()).collect().item()
    return {
        "engine": "polars", "master": "1 process", "n_executors": 0,
        "cores": pl.thread_pool_size(), "default_parallelism": pl.thread_pool_size(),
        "files": len(files),
        "rows_in": rows_in, "rows_out": daily.height,
        "cells": daily.select(CELL_KEYS).unique().height,
        "seconds_startup": 0.0, "seconds_etl": round(t_etl, 2), "seconds_subbasin": None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", choices=["spark", "polars"], default="spark")
    ap.add_argument("--mode", choices=["local", "cluster"], default=None)
    ap.add_argument("--cores", type=int, default=None, help="local[N]")
    ap.add_argument("--cores-max", type=int, default=None, help="spark.cores.max (cluster)")
    ap.add_argument("--executor-cores", type=int, default=None)
    ap.add_argument("--partitions", type=int, default=None, help="số phân hoạch khi chia theo ô")
    ap.add_argument("--src", default=str(RAW_DIR))
    ap.add_argument("--pattern", default=PATTERN)
    ap.add_argument("--time-col", default="time")
    ap.add_argument("--precip-col", default="precipitation")
    ap.add_argument("--out", default=None)
    ap.add_argument("--out-sub", default=str(OUT_SUB), help="nơi ghi bảng theo lưu vực con")
    ap.add_argument("--weights", default=str(WEIGHTS) if WEIGHTS.exists() else None,
                    help="CSV subbasin,lat,lon,weight (mặc định dùng nếu file đã có)")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--no-bench", action="store_true", help="không ghi etl_benchmark.csv")
    args = ap.parse_args(argv)
    if args.out is None:
        args.out = str(OUT_POLARS if args.engine == "polars" else OUT_CELL)

    res = run_polars(args) if args.engine == "polars" else run_spark(args)
    row = {"run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "tag": args.tag,
           "host": _host(), **res}
    for k, v in row.items():
        print(f"  {k:<18} {v}")
    print(f"→ {Path(args.out)}")
    if not args.no_bench:
        append_bench(row)
        print(f"→ {BENCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
