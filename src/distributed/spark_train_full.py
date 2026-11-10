"""MLlib GBT / RandomForest trên DỮ LIỆU ĐẦY ĐỦ của mô hình chính, chạy trên cụm (Report 4).

``spark_train.py`` (Report 2–4) học trên panel Report 2: từ 2010, 66 cột, một lần chia.
File này học đúng dữ liệu của mô hình chính E để so công bằng với LightGBM:

* panel ``daily_panel_ext.parquet`` từ 1998-01-04, đúng 88 cột E (``wf_tuning.e_features``);
  hàng dùng được = mọi cột E và nhãn khác null/NaN (= ``ablation_hourly.masks``);
* học ``log1p(Q)``, dự báo ``expm1`` cắt âm — như LightGBM.

Hai bước, đều chạy trên Spark (mỗi lần fit là một job MLlib phân tán trên executor):

1. **Chọn tham số trên VALID** (train 1998-01-04 → 2015-12-28, valid 2016-01-01 →
   2022-06-30, như Optuna của ``wf_tuning``), lưới giống ``spark_train``; rồi học lại
   1998 → 2022-06-30 và chấm test ≥ 2022-07-01 MỘT lần (so với E: ``ablation_ext.csv``).
2. **Walk-forward 13 fold 2013–2025** với tham số đã chọn (fold, gap 3 ngày, ngưỡng mức 1
   như ``wf_tuning``); ΔNSE so với E cùng fold (``reports/wf_peak_folds.csv``, E 3 seed),
   CI bootstrap theo fold, thắng/thua, Wilcoxon.

    spark-submit --master spark://spark-master:7077 --driver-memory 2g \\
        src/distributed/spark_train_full.py --mode cluster --cores-max 8 --executor-cores 4
    python -m src.distributed.spark_train_full --mode local --cores 8 --quick   # thử máy
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date

import numpy as np
import polars as pl

from src import config as cfg
from src.distributed.spark_session import describe, get_spark
from src.distributed.spark_train import GBT_GRID, QUICK, RF_GRID, load_panel, make_estimator
from src.eval import metrics

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_SPLIT = cfg.ROOT / "reports" / "spark_full_results.csv"
OUT_FOLDS = cfg.ROOT / "reports" / "spark_full_wf_folds.csv"
OUT_SUMMARY = cfg.ROOT / "reports" / "spark_full_wf_summary.csv"
E_FOLDS = cfg.ROOT / "reports" / "wf_peak_folds.csv"
E_SPLIT = cfg.ROOT / "reports" / "ablation_ext.csv"

START = date(1998, 1, 4)                       # = ablation_sat.EXT_START
OPT_TRAIN = (START, date(2015, 12, 28))
OPT_VALID = (date(2016, 1, 1), date.fromisoformat(cfg.VALID_END))
TEST_TRAIN = (START, date.fromisoformat(cfg.VALID_END))
TEST_START = date.fromisoformat(cfg.GLOFAS_REGIME_BREAK)
YEARS = tuple(range(2013, 2026))


def prepare(df, feats: list[str], h: int, n_partitions: int):
    """(date, features, label, y) của horizon h trên hàng đủ cột E — đã cache."""
    from pyspark.ml.feature import VectorAssembler
    from pyspark.sql import functions as F

    tgt = f"target_h{h}"
    base = df.filter(F.col("date") >= F.lit(START)).na.drop(subset=[*feats, tgt])
    out = (VectorAssembler(inputCols=feats, outputCol="features").transform(base)
           .select("date", "features", F.log1p(tgt).alias("label"), F.col(tgt).alias("y"))
           .repartition(n_partitions).cache())
    out.count()
    return out


def between(df, lo: date, hi: date | None = None):
    from pyspark.sql import functions as F
    c = F.col("date") >= F.lit(lo)
    return df.filter(c & (F.col("date") <= F.lit(hi)) if hi else c)


def fit_predict(kind: str, params: dict, train, test) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(ngày, y thật, y dự báo m³/s) theo thứ tự ngày."""
    model = make_estimator(kind, params).fit(train)
    t = model.transform(test).select("date", "y", "prediction").orderBy("date").toArrow()
    return (t.column("date").to_numpy(zero_copy_only=False), t.column("y").to_numpy(),
            np.clip(np.expm1(t.column("prediction").to_numpy()), 0, None))


def score(y: np.ndarray, yhat: np.ndarray, thr1: float) -> dict:
    rep = metrics.regression_report(y, yhat)
    ev = metrics.event_report(y >= thr1, yhat >= thr1)
    return {k: rep[k] for k in ("NSE", "KGE", "RMSE", "peak_bias")} | {
        "hits1": ev["hits"], "misses1": ev["misses"], "false_alarms1": ev["false_alarms"]}


def e_reference() -> tuple[dict[int, float], pl.DataFrame]:
    """NSE test của E (TB 3 seed) và NSE từng fold của E (walk-forward 3 seed)."""
    ab = pl.read_csv(E_SPLIT)
    col = "config" if "config" in ab.columns else ab.columns[0]
    e = ab.filter(pl.col(col).str.starts_with("E "))   # "E +storm/monsoon/ENSO"
    split = {int(r["horizon"]): float(r["NSE"]) for r in
             e.group_by("horizon").agg(pl.col("NSE").mean()).iter_rows(named=True)}
    folds = (pl.read_csv(E_FOLDS).filter(pl.col("config") == "E")
               .select("fold", "horizon", pl.col("NSE").alias("NSE_E")))
    return split, folds


def summarize(folds: pl.DataFrame) -> pl.DataFrame:
    from src.eval.walk_forward_sat import boot_mean_ci, wilcoxon_p

    rows = []
    for (m, h), g in folds.group_by(["model", "horizon"], maintain_order=True):
        d = g["dNSE_vs_E"].to_numpy()
        lo, hi = boot_mean_ci(d)
        hits, miss, fa = (int(g[c].sum()) for c in ("hits1", "misses1", "false_alarms1"))
        rows.append({"model": m, "horizon": h, "n_folds": g.height, "NSE_mean": g["NSE"].mean(),
                     "NSE_E_mean": g["NSE_E"].mean(), "dNSE_mean": float(d.mean()),
                     "dNSE_ci_lo": lo, "dNSE_ci_hi": hi, "wins": int((d > 0).sum()),
                     "losses": int((d < 0).sum()), "p_wilcoxon": wilcoxon_p(d),
                     "peak_bias_mean": g["peak_bias"].mean(),
                     "POD1": hits / (hits + miss) if hits + miss else np.nan,
                     "FAR1": fa / (hits + fa) if hits + fa else np.nan,
                     "seconds_fit_total": g["seconds"].sum()})
    return pl.from_dicts(rows).sort("horizon", "model")


def main(argv: list[str] | None = None) -> int:
    from src.eval.walk_forward_sat import fold_threshold, year_fold
    from src.eval.wf_tuning import e_features

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=["local", "cluster"], default=None)
    ap.add_argument("--cores", type=int, default=None)
    ap.add_argument("--cores-max", type=int, default=None)
    ap.add_argument("--executor-cores", type=int, default=None)
    ap.add_argument("--executor-memory", default="1800m")
    ap.add_argument("--partitions", type=int, default=8)
    ap.add_argument("--models", default="gbt,rf")
    ap.add_argument("--horizons", default=",".join(map(str, cfg.HORIZONS)))
    ap.add_argument("--years", nargs="+", type=int, default=list(YEARS))
    ap.add_argument("--quick", action="store_true", help="lưới 1 bộ, ít cây, 2 fold — thử máy")
    a = ap.parse_args(argv)
    years = a.years[:2] if a.quick else a.years

    t0 = time.perf_counter()
    spark = get_spark(a.mode, app_name="mllib-full", cores=a.cores, cores_max=a.cores_max,
                      executor_cores=a.executor_cores, executor_memory=a.executor_memory,
                      shuffle_partitions=a.partitions)
    info = describe(spark)
    from src.models.ablation_sat import PANEL_EXT
    panel_pl = pl.read_parquet(PANEL_EXT).sort("date")
    panel = load_panel(spark, PANEL_EXT)
    feats = e_features()
    e_split, e_folds = e_reference()
    thr_test = float(pl.read_csv(cfg.ROOT / "reports" / "risk_levels.csv")
                       .filter(pl.col("muc") == "nguy_co_1")["nguong_m3s"].item())
    print(f"Spark {info['spark_version']} · {info['master']} · {info['cores_used']} lõi · "
          f"{len(feats)} cột E · panel {panel_pl.height} ngày", flush=True)

    kinds = [k.strip() for k in a.models.split(",") if k.strip()]
    split_rows, fold_rows, grid_rows = [], [], []
    for h in [int(x) for x in a.horizons.split(",")]:
        data = prepare(panel, feats, h, a.partitions)
        for kind in kinds:
            grid = QUICK[kind] if a.quick else {"gbt": GBT_GRID, "rf": RF_GRID}[kind]
            # 1. chọn trên valid
            tr, va = between(data, *OPT_TRAIN), between(data, *OPT_VALID)
            best, best_nse = None, -np.inf
            for params in grid:
                t1 = time.perf_counter()
                _, y, yh = fit_predict(kind, params, tr, va)
                nse = metrics.nse(y, yh)
                grid_rows.append({"model": f"spark_{kind}", "horizon": h,
                                  "params": json.dumps(params, sort_keys=True),
                                  "valid_NSE": nse, "seconds": time.perf_counter() - t1})
                if np.isfinite(nse) and nse > best_nse:
                    best, best_nse = params, nse
            # test một lần
            t1 = time.perf_counter()
            _, y, yh = fit_predict(kind, best, between(data, *TEST_TRAIN), between(data, TEST_START))
            split_rows.append({"model": f"spark_{kind}", "horizon": h, **score(y, yh, thr_test),
                               "n_test": len(y), "valid_NSE": best_nse,
                               "NSE_E": e_split.get(h), "dNSE_vs_E": metrics.nse(y, yh) - e_split.get(h, np.nan),
                               "params": json.dumps(best, sort_keys=True),
                               "seconds_refit": time.perf_counter() - t1})
            print(f"h{h} spark_{kind:<3} valid {best_nse:.3f} · test NSE {split_rows[-1]['NSE']:.3f} "
                  f"(E {e_split.get(h, float('nan')):.3f}) · {best}", flush=True)
            # 2. walk-forward với tham số đã chọn
            for year in years:
                fold = year_fold(year, START)
                thr1 = fold_threshold(panel_pl, *fold["train"])
                t1 = time.perf_counter()
                _, y, yh = fit_predict(kind, best, between(data, *fold["train"]),
                                       between(data, *fold["test"]))
                fold_rows.append({"model": f"spark_{kind}", "horizon": h, "fold": year,
                                  **score(y, yh, thr1), "n_test": len(y), "thr1": thr1,
                                  "seconds": time.perf_counter() - t1})
            print(f"   walk-forward {len(years)} fold xong ({(time.perf_counter() - t0) / 60:.1f} ph)",
                  flush=True)
        data.unpersist()
    spark.stop()

    pl.DataFrame(split_rows).with_columns(pl.lit(info["master"]).alias("master"),
                                          pl.lit(info["cores_used"]).alias("cores")
                                          ).write_csv(OUT_SPLIT, float_precision=6)
    folds = (pl.DataFrame(fold_rows).join(e_folds, on=["fold", "horizon"], how="left")
               .with_columns((pl.col("NSE") - pl.col("NSE_E")).alias("dNSE_vs_E")))
    folds.write_csv(OUT_FOLDS, float_precision=6)
    summ = summarize(folds).with_columns(pl.lit(round(time.perf_counter() - t0, 1)).alias("wall_s_all"),
                                         pl.lit(info["master"]).alias("master"))
    summ.write_csv(OUT_SUMMARY, float_precision=6)
    pl.DataFrame(grid_rows).write_csv(cfg.ROOT / "reports" / "spark" / "train_full_grid.csv")
    with pl.Config(tbl_cols=20, float_precision=3, tbl_width_chars=200):
        print(summ.select("model", "horizon", "NSE_mean", "NSE_E_mean", "dNSE_mean", "dNSE_ci_lo",
                          "dNSE_ci_hi", "wins", "losses", "p_wilcoxon", "POD1"))
    print(f"Tổng {(time.perf_counter() - t0) / 60:.1f} phút\n→ {OUT_SPLIT}\n→ {OUT_FOLDS}\n→ {OUT_SUMMARY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
