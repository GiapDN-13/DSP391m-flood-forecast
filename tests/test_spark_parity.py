"""Bản Spark (``spark_hourly``) phải TRÙNG bản Polars (``hourly_features``), và huấn luyện
LSTM qua stage barrier của Spark (``spark_dl``) phải ra đúng kết quả DDP thường — dữ liệu
giả, không cần mạng. Bỏ qua cả file nếu máy không có pyspark hoặc Java."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest

pytest.importorskip("pyspark")
if not (shutil.which("java") or os.environ.get("JAVA_HOME")):
    pytest.skip("không có Java — bỏ qua test Spark", allow_module_level=True)

from src.distributed import spark_hourly as sh  # noqa: E402
from src.distributed import spark_session  # noqa: E402
from src.features import hourly_features as hf  # noqa: E402

AREAS = {"u1": 670.4, "u2": 506.8, "u3": 88.2, "u4": 185.1, "u5": 92.8}
CELLS = [(16.1, 107.1), (16.1, 107.2), (16.1, 107.3), (16.2, 107.1), (16.2, 107.2),
         (16.2, 107.3), (16.3, 107.2)]
WEIGHTS = pl.DataFrame(
    [("u1", 16.1, 107.1, 0.25), ("u1", 16.1, 107.2, 0.5), ("u1", 16.2, 107.1, 0.25),
     ("u2", 16.1, 107.3, 0.3), ("u2", 16.2, 107.3, 0.7),
     ("u3", 16.2, 107.2, 1.0),
     ("u4", 16.2, 107.2, 0.123), ("u4", 16.3, 107.2, 0.877),
     ("u5", 16.1, 107.2, 0.4), ("u5", 16.2, 107.2, 0.35), ("u5", 16.3, 107.2, 0.25)],
    schema={"subbasin": pl.Utf8, "lat": pl.Float64, "lon": pl.Float64, "weight": pl.Float64},
    orient="row")
T0 = datetime(2020, 10, 1)
N_DAYS = 8


def _grid() -> pl.DataFrame:
    """8 ngày × 7 ô, có đủ ca khó: ngày chỉ mưa phùn 0,1 mm ở mọi ô (đỉnh hoà nhau và
    chạm đúng ngưỡng 0,1 mm), mọi ô = 1 mm (ngưỡng giờ mưa), NaN, ô thiếu giờ, cả giờ
    thiếu, ngày đầu bắt đầu từ 03h."""
    rng = np.random.default_rng(2026)
    vals = np.array([0.0, 0.0, 0.0, 0.1, 0.2, 0.3, 1.0, 2.5, 7.3, 12.9])
    rows = []
    for k in range(3, N_DAYS * 24):                       # ngày 1 thiếu 00–02h
        t = T0 + timedelta(hours=k)
        if k == 4 * 24 + 13:                              # ngày 5 thiếu hẳn 13h
            continue
        for lat, lon in CELLS:
            p = float(rng.choice(vals))
            if 24 <= k < 48:
                p = 0.1 if k < 30 else 0.0                # ngày 2: mọi ô 0,1 mm lúc 00–05h
            elif 2 * 24 + 8 <= k < 2 * 24 + 11:
                p = 1.0                                   # ngày 3, 08–10h: mọi ô 1 mm
            elif 2 * 24 + 11 <= k < 3 * 24:
                p = 0.0
            if k == 3 * 24 + 5 and (lat, lon) == (16.1, 107.2):
                p = float("nan")                          # NaN → chia lại trọng số
            if k == 3 * 24 + 9 and (lat, lon) == (16.2, 107.2):
                continue                                  # ô u3 duy nhất thiếu → u3 rỗng
            rows.append((t, lat, lon, p))
    df = pl.DataFrame(rows, schema={"time": pl.Datetime("us"), "lat": pl.Float64,
                                    "lon": pl.Float64, "precip": pl.Float64}, orient="row")
    return df.sort("time", "lat", "lon")                  # như hf.load_era5 / load_pccs


@pytest.fixture(scope="module")
def spark():
    s = spark_session.get_spark("local", app_name="test-spark-parity", cores=2,
                                shuffle_partitions=3)
    yield s
    s.stop()


@pytest.fixture(scope="module")
def grid() -> pl.DataFrame:
    return _grid()


@pytest.fixture(scope="module")
def spark_out(spark, grid):
    sdf = sh.normalize(spark.createDataFrame(grid.to_arrow()))
    hw, feats = sh.hourly_features_spark(spark, sdf, WEIGHTS, AREAS)
    return sh.to_polars(hw), sh.to_polars(feats)


def _assert_identical(p: pl.DataFrame) -> None:
    s = sh.summarize(p)
    assert s["rows_only_one_side"] == 0
    assert s["null_mismatch"] == 0
    assert s["max_abs_diff"] == 0.0
    assert s["cells_not_bitwise_equal"] == 0


def test_cay_cong_giong_sum_horizontal():
    assert sh.tree_order(list(range(5))) == ((0, 1), (2, (3, 4)))
    assert sh.tree_order(list(range(3))) == (0, (1, 2))
    rng = np.random.default_rng(0)
    x = rng.random((5000, 5)) * rng.choice([0.0, 0.1, 1.0, 7.7], size=(5000, 5))
    f = [a / sum(AREAS.values()) for a in AREAS.values()]
    df = pl.DataFrame({f"c{i}": x[:, i] for i in range(5)})
    pol = df.select(pl.sum_horizontal([pl.col(f"c{i}") * f[i] for i in range(5)])).to_series()
    tree = sh._tree_sum(sh.tree_order([x[:, i] * f[i] for i in range(5)]))
    assert np.array_equal(pol.to_numpy(), tree)


def test_chuoi_gio_theo_luu_vuc_trung_polars(spark_out, grid):
    ref = hf.basin_hourly(grid, WEIGHTS, AREAS)
    hw, _ = spark_out
    assert hw.columns == ref.columns
    assert hw.height == N_DAYS * 24
    _assert_identical(sh.parity(ref, hw, "time"))


def test_dac_trung_ngay_trung_polars_tung_bit(spark_out, grid):
    ref = hf.hourly_features(grid, WEIGHTS, AREAS)
    _, feats = spark_out
    assert feats.columns == ref.columns
    assert feats.height == N_DAYS
    _assert_identical(sh.parity(ref, feats, "date"))


def test_ca_kho_co_that_trong_du_lieu(spark_out):
    _, f = spark_out
    d = {r["date"].day: r for r in f.iter_rows(named=True)}
    assert d[1]["hr_sum_basin"] is None                     # ngày 1 thiếu 00–02h
    assert d[5]["hr_sum_basin"] is None                     # ngày 5 thiếu 13h
    assert d[4]["hr_sum_u3"] is None and d[4]["hr_sum_basin"] is None
    assert d[4]["hr_sum_u1"] is not None                    # NaN của u1 được chia lại trọng số
    assert d[3]["hr_nh1mm_u3"] >= 3                         # 08–10h đúng 1,0 mm ở mọi ô
    assert d[2]["hr_max1h_u3"] == pytest.approx(0.1)        # ngày mưa phùn: đỉnh hoà 00–05h
    assert d[2]["hr_peak_cos_u3"] == 1.0                    # → lấy giờ sớm nhất (00h)
    assert d[6]["hr_r72h_basin"] is None                    # cửa sổ 72h chạm ngày 5 rỗng
    assert d[8]["hr_r72h_basin"] is not None


def test_khong_ro_ri_tuong_lai(spark, grid, spark_out):
    _, full = spark_out
    cut = grid.filter(pl.col("time") < T0 + timedelta(days=3))       # tới 23:00 ngày 3
    sdf = sh.normalize(spark.createDataFrame(cut.to_arrow()))
    _, f = sh.hourly_features_spark(spark, sdf, WEIGHTS, AREAS)
    part = sh.to_polars(f)
    assert part.height == 3
    _assert_identical(sh.parity(full.filter(pl.col("date") <= part["date"].max()), part, "date"))


# ================================================================ spark_dl (LSTM qua Spark)

def _toy_panel(path) -> str:
    """Panel giả 2014-06 → 2022-12 đủ train/valid/test; Q phản ứng trễ với mưa."""
    from datetime import date

    rng = np.random.default_rng(0)
    d = pl.date_range(date(2014, 6, 1), date(2022, 12, 31), "1d", eager=True)
    n = d.len()
    doy = np.array([x.timetuple().tm_yday for x in d.to_list()], dtype=float)
    wet = np.isin(np.array([x.month for x in d.to_list()]), [9, 10, 11, 12])
    rain = rng.gamma(0.4, 8.0, n) * np.where(wet, 3.0, 0.7)
    q = np.empty(n)
    q[0] = 50.0
    for t in range(1, n):
        q[t] = 0.85 * q[t - 1] + 4.0 * rain[t - 1] + 5.0
    df = pl.DataFrame({"date": d, "discharge": q, "rain_thuong": rain * 1.2, "rain_trung": rain,
                       "rain_ha": rain * 0.8, "rain_basin": rain,
                       "api": np.convolve(rain, 0.9 ** np.arange(30))[:n],
                       "doy_sin": np.sin(2 * np.pi * doy / 365.25),
                       "doy_cos": np.cos(2 * np.pi * doy / 365.25),
                       "mua_lu": wet.astype(np.int64)})
    df = df.with_columns(*[pl.col("discharge").shift(-h).alias(f"target_h{h}") for h in (1, 2, 3)])
    df.write_parquet(path)
    return str(path)


def test_bang_ket_qua_thay_dong_cung_tag_va_ghi_ca_lan_hong(tmp_path):
    from src.distributed import spark_dl as sd

    meta = {"tag": "a", "engine": "single", "status": "ok", "error": ""}
    fake = {"world_size": 1, "best_epoch": 2, "stopped_epoch": 3, "n_train": 10, "n_trval": 20,
            "n_test": 5, "n_params": 7, "time_s": 1.234, "threshold": 806.04,
            "results": [{"fit": "train", "split": "valid", "horizon": h, "n": 5, "NSE": 0.5}
                        for h in (1, 2, 3)]}
    out = tmp_path / "r.csv"
    sd.save_rows(sd.result_rows(meta, fake), out)
    sd.save_rows(sd.result_rows({**meta, "tag": "b", "status": "failed", "error": "x"}, None), out)
    sd.save_rows(sd.result_rows(meta, fake), out)          # chạy lại tag a → thay, không nhân đôi
    d = pl.read_csv(out)
    assert d.filter(pl.col("tag") == "a").height == 3
    assert d.filter(pl.col("tag") == "b")["status"].to_list() == ["failed"]


def test_barrier_spark_hai_rank_trung_ddp_mp_spawn(spark, tmp_path):
    """Stage barrier 2 task (mỗi task 1 rank DDP) = DDP 2 tiến trình mp.spawn của dl_lstm:
    cách phân tán không được làm đổi kết quả."""
    from src.distributed import spark_dl as sd
    from src.models import dl_lstm as dl

    conf = {**dl.DEFAULTS, "panel_path": _toy_panel(tmp_path / "p.parquet"), "hidden": 8,
            "max_epochs": 2, "patience": 2, "batch_size": 128, "num_threads": 1, "seq_len": 7}
    r = sd.run_barrier(spark, conf, 2)
    assert r["rank"] == 0 and r["world_size"] == 2
    assert len(r["results"]) == 9
    ref = dl.run_local_ddp(conf, 2)
    assert [x["NSE"] for x in r["results"]] == pytest.approx([x["NSE"] for x in ref["results"]],
                                                            abs=1e-9)
