"""MLlib trên dữ liệu đầy đủ (src/distributed/spark_train_full.py): phần không cần Spark."""

from __future__ import annotations

import polars as pl

from src.distributed import spark_train_full as stf


def test_moc_E_doc_dung_cau_hinh():
    split, folds = stf.e_reference()
    assert set(split) == {1, 2, 3}
    assert round(split[1], 3) == 0.747 and round(split[3], 3) == 0.236
    assert folds["fold"].n_unique() == 13


def test_tong_hop_theo_fold():
    folds = pl.DataFrame({"model": ["spark_rf"] * 4, "horizon": [1] * 4, "fold": [2013, 2014, 2015, 2016],
                          "NSE": [0.7, 0.8, 0.6, 0.9], "NSE_E": [0.75, 0.75, 0.75, 0.75],
                          "peak_bias": [-0.3] * 4, "hits1": [1, 2, 0, 1], "misses1": [1, 0, 1, 0],
                          "false_alarms1": [0, 1, 0, 0], "seconds": [10.0] * 4}
                         ).with_columns((pl.col("NSE") - pl.col("NSE_E")).alias("dNSE_vs_E"))
    s = stf.summarize(folds).row(0, named=True)
    assert s["wins"] == 2 and s["losses"] == 2
    assert abs(s["dNSE_mean"] - 0.0) < 1e-12
    assert s["POD1"] == 4 / 6 and s["FAR1"] == 1 / 5
