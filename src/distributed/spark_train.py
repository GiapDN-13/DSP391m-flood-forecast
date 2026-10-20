"""Huấn luyện ML phân tán bằng Spark MLlib: GBT và RandomForest dự báo lưu lượng 1–3 ngày.

Cùng dữ liệu, cùng split, cùng thước đo với LightGBM (``src/models/lgbm.py``) để
bảng so sánh công bằng:

* panel ``data/processed/daily_panel.parquet``; feature = mọi cột số trừ ``date``,
  ``alert_level`` và ``target_*`` (y hệt ``lgbm.feature_cols``).
* train ≤ ``TRAIN_END``, valid tới ``VALID_END``, test từ ``GLOFAS_REGIME_BREAK`` —
  chia theo THỜI GIAN, không xáo trộn.
* học ``log1p(Q)``, dự báo ``expm1`` rồi cắt âm về 0.
* chấm bằng ``src.eval.metrics.regression_report`` (NSE, KGE, peak_bias…).

Chọn siêu tham số: ``CrossValidator`` của Spark chia fold ngẫu nhiên,
``TrainValidationSplit`` cũng tách ngẫu nhiên theo tỉ lệ → cả hai đều cho mô hình
nhìn thấy tương lai. Thay bằng vòng lặp tự viết: fit trên train, chấm NSE (m³/s)
trên valid cố định, chọn bộ tốt nhất, fit lại trên train+valid (đúng quy trình
LightGBM) rồi chấm test MỘT lần.

    python -m src.distributed.spark_train --mode local --cores 8
    spark-submit --master spark://spark-master:7077 src/distributed/spark_train.py --mode cluster
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np
import polars as pl

from src import config as cfg
from src.distributed.spark_session import describe, get_spark, hadoop_io_ok
from src.eval import metrics

PANEL = cfg.DATA_PROCESSED / "daily_panel.parquet"
OUT = cfg.ROOT / "reports" / "spark_results.csv"
GRID_LOG = cfg.DATA_INTERIM / "spark" / "train_grid.csv"
LGBM = cfg.ROOT / "reports" / "lgbm_results.csv"

# Lưới nhỏ có chủ đích: dữ liệu chỉ ~4,5 nghìn ngày train+valid, lưới to chỉ tốn thời gian.
GBT_GRID = [dict(maxDepth=d, stepSize=s, lossType=loss, maxIter=150, subsamplingRate=0.8)
            for d in (3, 5) for s in (0.05, 0.1) for loss in ("squared", "absolute")]
# maxMemoryInMB=64: mặc định 256 MB cho MỖI task, 4 task/executor = 1 GB — lần chạy đầu
# trên cụm (executor 1 500 MB) chết vì OOM (exit code 52) khi fit RF; hạ xuống 64 thì chạy hết.
RF_GRID = [dict(numTrees=200, maxDepth=d, featureSubsetStrategy=f, subsamplingRate=0.8,
                maxMemoryInMB=64)
           for d in (8, 12) for f in ("onethird", "0.5")]
QUICK = {"gbt": [dict(maxDepth=3, stepSize=0.1, lossType="squared", maxIter=20)],
         "rf": [dict(numTrees=20, maxDepth=6, featureSubsetStrategy="onethird")]}

NUMERIC = {"double", "float", "int", "bigint", "smallint", "tinyint"}


def load_panel(spark, path=PANEL, use_hadoop: bool | None = None):
    """Đọc panel ngày thành DataFrame Spark (Windows: qua Arrow)."""
    from pyspark.sql import functions as F

    if use_hadoop is None:
        use_hadoop = hadoop_io_ok()
    df = (spark.read.parquet(path.as_posix()) if use_hadoop
          else spark.createDataFrame(pl.read_parquet(path).to_arrow()))
    return df.withColumn("date", F.to_date("date"))


def feature_cols(df) -> list[str]:
    """Mọi cột số trừ date / alert_level / target_* — khớp ``lgbm.feature_cols``."""
    return [c for c, t in df.dtypes
            if t in NUMERIC and c not in {"date", "alert_level"}
            and not c.startswith("target_")]


def add_split(df):
    """Gắn nhãn train/valid/test theo mốc thời gian của dự án (không xáo)."""
    from pyspark.sql import functions as F

    d = F.col("date")
    return df.withColumn(
        "split",
        F.when(d <= F.lit(cfg.TRAIN_END).cast("date"), "train")
         .when(d <= F.lit(cfg.VALID_END).cast("date"), "valid")
         .when(d >= F.lit(cfg.GLOFAS_REGIME_BREAK).cast("date"), "test"))


def prepare(df, feats: list[str], h: int, n_partitions: int):
    """Bảng (date, split, features, label=log1p(Q), y=Q) cho một horizon, đã cache."""
    from pyspark.ml.feature import VectorAssembler
    from pyspark.sql import functions as F

    tgt = f"target_h{h}"
    # na.drop bỏ cả null lẫn NaN — giống điều kiện notna() của LightGBM
    base = add_split(df).na.drop(subset=[*feats, tgt]).filter(F.col("split").isNotNull())
    va = VectorAssembler(inputCols=feats, outputCol="features")
    out = (va.transform(base)
           .select("date", "split", "features",
                   F.log1p(tgt).alias("label"), F.col(tgt).alias("y"))
           .repartition(n_partitions).cache())
    out.count()
    return out


def make_estimator(kind: str, params: dict):
    from pyspark.ml.regression import GBTRegressor, RandomForestRegressor

    cls = {"gbt": GBTRegressor, "rf": RandomForestRegressor}[kind]
    return cls(featuresCol="features", labelCol="label", seed=cfg.SEED, **params)


def predict(model, df) -> tuple[np.ndarray, np.ndarray]:
    """Trả về (y thật, y dự báo) theo thứ tự ngày, đã đổi về m³/s và cắt âm."""
    tbl = model.transform(df).select("date", "y", "prediction").orderBy("date").toArrow()
    y = tbl.column("y").to_numpy()
    yhat = np.clip(np.expm1(tbl.column("prediction").to_numpy()), 0, None)
    return y, yhat


def tune_and_test(kind: str, grid: list[dict], data) -> tuple[dict, list[dict]]:
    """Chọn tham số trên valid, fit lại train+valid, chấm test. Trả (kết quả test, nhật ký lưới)."""
    from pyspark.sql import functions as F

    tr = data.filter(F.col("split") == "train")
    va = data.filter(F.col("split") == "valid")
    trva = data.filter(F.col("split").isin("train", "valid"))
    te = data.filter(F.col("split") == "test")

    log = []
    t0 = time.perf_counter()
    for params in grid:
        t1 = time.perf_counter()
        y, yhat = predict(make_estimator(kind, params).fit(tr), va)
        log.append({"params": json.dumps(params, sort_keys=True),
                    "valid_NSE": metrics.nse(y, yhat), "valid_RMSE": metrics.rmse(y, yhat),
                    "seconds": round(time.perf_counter() - t1, 2)})
    best = max(log, key=lambda r: -np.inf if np.isnan(r["valid_NSE"]) else r["valid_NSE"])

    t2 = time.perf_counter()
    model = make_estimator(kind, json.loads(best["params"])).fit(trva)
    y, yhat = predict(model, te)
    rep = metrics.regression_report(y, yhat)
    rep.update({"valid_NSE": best["valid_NSE"], "params": best["params"],
                "n_train": trva.count(), "seconds_refit": round(time.perf_counter() - t2, 2),
                "seconds_total": round(time.perf_counter() - t0, 2),
                "_importances": model.featureImportances.toArray()})
    return rep, log


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=["local", "cluster"], default=None)
    ap.add_argument("--cores", type=int, default=None)
    ap.add_argument("--cores-max", type=int, default=None)
    ap.add_argument("--executor-cores", type=int, default=None)
    ap.add_argument("--executor-memory", default="1500m")
    ap.add_argument("--partitions", type=int, default=8)
    ap.add_argument("--models", default="gbt,rf")
    ap.add_argument("--horizons", default=",".join(map(str, cfg.HORIZONS)))
    ap.add_argument("--quick", action="store_true", help="lưới 1 bộ, ít cây — chỉ để thử máy")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    spark = get_spark(args.mode, app_name="flow-mllib", cores=args.cores,
                      cores_max=args.cores_max, executor_cores=args.executor_cores,
                      executor_memory=args.executor_memory,
                      shuffle_partitions=args.partitions)
    panel = load_panel(spark)
    feats = feature_cols(panel)
    info = describe(spark)
    print(f"Spark {info['spark_version']} · master {info['master']} · "
          f"{info['cores_used']} lõi · {len(feats)} feature")

    lgbm = pl.read_csv(LGBM) if LGBM.exists() else None
    rows, grid_rows = [], []
    kinds = [k.strip() for k in args.models.split(",") if k.strip()]
    for h in [int(x) for x in args.horizons.split(",")]:
        data = prepare(panel, feats, h, args.partitions)
        n = {r["split"]: r["count"] for r in data.groupBy("split").count().collect()}
        print(f"\nh={h}: train {n.get('train', 0)} · valid {n.get('valid', 0)} · "
              f"test {n.get('test', 0)} ngày")
        for kind in kinds:
            grid = QUICK[kind] if args.quick else {"gbt": GBT_GRID, "rf": RF_GRID}[kind]
            rep, log = tune_and_test(kind, grid, data)
            imp = rep.pop("_importances")
            top = [feats[i] for i in np.argsort(imp)[::-1][:5]]
            ref = None
            if lgbm is not None:
                m = lgbm.filter(pl.col("horizon") == h)
                ref = float(m["NSE"][0]) if m.height else None
            rows.append({"model": f"spark_{kind}", "horizon": h,
                         **{k: rep[k] for k in ["RMSE", "MAE", "NSE", "KGE", "peak_bias", "n"]},
                         "valid_NSE": rep["valid_NSE"], "lgbm_NSE": ref,
                         "delta_NSE_vs_lgbm": rep["NSE"] - ref if ref is not None else None,
                         "n_train": rep["n_train"], "grid_size": len(grid),
                         "seconds_total": rep["seconds_total"],
                         "seconds_refit": rep["seconds_refit"],
                         "master": info["master"], "cores": info["cores_used"],
                         "params": rep["params"], "top5_features": ";".join(top)})
            grid_rows += [{"model": f"spark_{kind}", "horizon": h, **r} for r in log]
            ref_s = f"{ref:+.3f}" if ref is not None else "n/a"
            print(f"  spark_{kind:<4} NSE test {rep['NSE']:+.3f} (LightGBM {ref_s}) · "
                  f"valid {rep['valid_NSE']:+.3f} · {rep['seconds_total']:.0f} s · "
                  f"{rep['params']}")
        data.unpersist()

    spark.stop()
    res = pl.DataFrame(rows)
    res.write_csv(args.out)
    GRID_LOG.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(grid_rows).write_csv(GRID_LOG)
    print(f"\nTổng thời gian {time.perf_counter() - t0:.0f} s")
    print(res.select("model", "horizon", "NSE", "lgbm_NSE", "valid_NSE", "seconds_total"))
    print(f"→ {args.out}\n→ {GRID_LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
