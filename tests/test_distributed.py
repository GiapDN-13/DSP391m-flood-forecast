"""Kiểm phép tính của ETL Spark trên dữ liệu giả 2 ô × 3 ngày (local[1], không cần mạng).

Bỏ qua cả file nếu máy không có pyspark hoặc Java. Trên Windows dữ liệu đi vào
Spark qua Arrow nên không cần Hadoop/winutils.
"""

from __future__ import annotations

import datetime as dt
import os
import shutil

import polars as pl
import pytest

from src.distributed import spark_session

pytest.importorskip("pyspark")
if not (shutil.which("java") or os.environ.get("JAVA_HOME")):
    pytest.skip("không có Java — bỏ qua test Spark", allow_module_level=True)

from src.distributed import spark_etl  # noqa: E402

A = (16.1, 107.1)
B = (16.2, 107.1)
D0 = dt.datetime(2020, 1, 1)


def _hours(cell, day: int, values: dict[int, float], skip: tuple[int, ...] = ()):
    rows = []
    for h in range(24):
        if h in skip:
            continue
        rows.append({"time": D0 + dt.timedelta(days=day, hours=h),
                     "precipitation": values.get(h, 0.0), "temperature_2m": 20.0,
                     "relative_humidity_2m": 90, "lat": cell[0], "lon": cell[1]})
    return rows


@pytest.fixture(scope="module")
def hourly() -> pl.DataFrame:
    rows = (
        # Ô A: mưa 22h–23h ngày 1 nối sang 0h ngày 2 → cửa sổ 3h vắt qua nửa đêm
        _hours(A, 0, {22: 2.0, 23: 3.0})
        + _hours(A, 1, {0: 4.0, 10: 1.0, 11: 0.5, 15: 5.0})
        + _hours(A, 2, {})                                    # ngày khô
        # Ô B: hoà đỉnh lúc 5h và 9h; ngày 2 thiếu giờ 7; ngày 3 có một dòng trùng
        + _hours(B, 0, {5: 2.0, 9: 2.0})
        + _hours(B, 1, {5: 1.5, 6: 1.0, 8: 1.0}, skip=(7,))
        + _hours(B, 2, {0: 0.2})
        + _hours(B, 2, {0: 0.2})[:1]
    )
    return pl.DataFrame(rows)


@pytest.fixture(scope="module")
def spark():
    s = spark_session.get_spark("local", app_name="test-distributed", cores=1,
                                shuffle_partitions=2)
    yield s
    s.stop()


@pytest.fixture(scope="module")
def daily_spark(spark, hourly) -> pl.DataFrame:
    sdf = spark_etl.normalize_hourly(spark.createDataFrame(hourly.to_arrow()))
    out = spark_etl.daily_stats(sdf, n_partitions=2).toArrow()
    return pl.from_arrow(out).sort("lat", "lon", "date")


def _row(df: pl.DataFrame, cell, day: int) -> dict:
    r = df.filter((pl.col("lat") == cell[0]) & (pl.col("lon") == cell[1])
                  & (pl.col("date") == (D0 + dt.timedelta(days=day)).date()))
    assert r.height == 1
    return r.row(0, named=True)


def test_resolve_master(monkeypatch):
    monkeypatch.delenv("SPARK_MASTER", raising=False)
    assert spark_session.resolve_master("local", cores=4) == "local[4]"
    assert spark_session.resolve_master() == "local[*]"
    monkeypatch.setenv("SPARK_MASTER", "spark://x:7077")
    assert spark_session.resolve_master() == "spark://x:7077"
    assert spark_session.resolve_master("cluster") == "spark://x:7077"
    with pytest.raises(ValueError):
        spark_session.resolve_master("yarn")


def test_shape(daily_spark):
    assert daily_spark.height == 6                       # 2 ô × 3 ngày
    assert set(spark_etl.DAILY_COLS) <= set(daily_spark.columns)


def test_daily_sum_and_max(daily_spark):
    a1, a2, a3 = (_row(daily_spark, A, d) for d in range(3))
    assert a1["rain_sum"] == pytest.approx(5.0)
    assert a2["rain_sum"] == pytest.approx(10.5)
    assert a3["rain_sum"] == pytest.approx(0.0)
    assert a2["rain_max1h"] == pytest.approx(5.0)
    assert a1["n_wet_hours"] == 2 and a2["n_wet_hours"] == 3 and a3["n_wet_hours"] == 0


def test_max3h_crosses_midnight(daily_spark):
    a1, a2 = _row(daily_spark, A, 0), _row(daily_spark, A, 1)
    assert a1["rain_max3h"] == pytest.approx(5.0)
    assert a2["rain_max3h"] == pytest.approx(9.0)        # 22h + 23h hôm trước + 0h
    assert a2["rain_max6h"] == pytest.approx(9.0)


def test_max3h_uses_time_not_rows(daily_spark):
    b2 = _row(daily_spark, B, 1)
    # thiếu giờ 7: cửa sổ (6h–8h] chỉ có 6h, 8h = 2,0; nếu đếm theo dòng sẽ ra 3,5
    assert b2["rain_max3h"] == pytest.approx(2.5)
    assert b2["n_hours"] == 23


def test_peak_hour_and_dedup(daily_spark):
    assert _row(daily_spark, A, 1)["peak_hour"] == 15
    assert _row(daily_spark, B, 0)["peak_hour"] == 5     # hoà → giờ sớm nhất
    assert _row(daily_spark, A, 2)["peak_hour"] is None  # ngày khô
    assert _row(daily_spark, B, 2)["n_hours"] == 24      # dòng trùng đã bị bỏ


def test_polars_matches_spark(daily_spark, hourly):
    diff = spark_etl.compare_outputs(daily_spark, spark_etl.polars_daily_stats(hourly))
    assert diff["rows_a"] == diff["rows_b"] == diff["rows_join"] == 6
    for c in spark_etl.DAILY_COLS:
        assert diff[f"maxdiff_{c}"] < 1e-9, c
        assert diff[f"nullmismatch_{c}"] == 0, c


def test_subbasin_weighting(spark, hourly):
    w = pl.DataFrame({"subbasin": ["s1", "s1"], "lat": [A[0], B[0]],
                      "lon": [A[1], B[1]], "weight": [0.75, 0.25]})
    sdf = spark_etl.normalize_hourly(spark.createDataFrame(hourly.to_arrow()))
    sub = spark_etl.daily_stats(spark_etl.subbasin_hourly(spark, sdf, w), ("subbasin",),
                                n_partitions=1)
    got = pl.from_arrow(sub.toArrow()).sort("date")
    assert got.height == 3
    assert got["rain_sum"][0] == pytest.approx(0.75 * 5.0 + 0.25 * 4.0)
    # giờ 7 ngày 2 chỉ có ô A → chuẩn hoá lại trọng số, không kéo về 0
    assert got["n_hours"][1] == 24
    # dòng trùng của ô B ngày 3 không được tính hai lần
    assert got["rain_sum"][2] == pytest.approx(0.25 * 0.2)


def test_train_split_labels(spark):
    from src.distributed import spark_train

    df = spark.createDataFrame(pl.DataFrame({
        "date": [dt.date(2015, 12, 31), dt.date(2016, 1, 1), dt.date(2022, 6, 30),
                 dt.date(2022, 7, 1)]}).to_arrow())
    got = [r["split"] for r in spark_train.add_split(df).orderBy("date").collect()]
    assert got == ["train", "valid", "valid", "test"]


def test_train_feature_cols_and_quick_fit(spark):
    """Chạy trọn vòng chọn tham số → fit lại → chấm test trên panel giả rất nhỏ."""
    import numpy as np

    from src.distributed import spark_train

    rng = np.random.default_rng(0)
    dates = ([dt.date(2015, 1, 1) + dt.timedelta(days=i) for i in range(30)]
             + [dt.date(2018, 1, 1) + dt.timedelta(days=i) for i in range(15)]
             + [dt.date(2023, 1, 1) + dt.timedelta(days=i) for i in range(12)])
    x = rng.uniform(0, 3, len(dates))
    panel = pl.DataFrame({"date": dates, "x": x, "month": [d.month for d in dates],
                          "alert_level": pl.Series([0] * len(dates), dtype=pl.Int8),
                          "target_h1": np.expm1(x) * 10, "note": ["a"] * len(dates)})
    df = spark.createDataFrame(panel.to_arrow())
    feats = spark_train.feature_cols(df)
    assert feats == ["x", "month"]

    data = spark_train.prepare(df, feats, 1, n_partitions=1)
    rep, log = spark_train.tune_and_test("gbt", spark_train.QUICK["gbt"], data)
    assert rep["n"] == 12 and rep["n_train"] == 45 and len(log) == 1
    assert np.isfinite(rep["NSE"]) and rep["NSE"] > 0.5
    data.unpersist()
