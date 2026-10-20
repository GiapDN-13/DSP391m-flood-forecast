"""Test cho walk-forward DL (src/eval/walk_forward_dl.py) — không cần dữ liệu thật.

Khoá: mốc fold và gap, valid nằm trong phần học, chuẩn hoá + ngưỡng chỉ từ phần
được học, và chấm điểm / tổng hợp so với LightGBM tính đúng.
"""

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from src.eval import walk_forward_dl as wf
from src.models import dl_lstm as dl

SMALL = {"hidden": 8, "max_epochs": 2, "patience": 1, "batch_size": 256,
         "num_threads": 1, "seq_len": 7}


def _d(s: str) -> date:
    return date.fromisoformat(s)


@pytest.fixture(scope="module")
def toy_panel() -> pl.DataFrame:
    """Panel giả 2010 → 2021: Q phản ứng trễ với mưa, đủ cột cho LSTM base."""
    rng = np.random.default_rng(1)
    d = pl.date_range(date(2010, 1, 1), date(2021, 12, 31), "1d", eager=True)
    n = d.len()
    doy = np.array([x.timetuple().tm_yday for x in d.to_list()], dtype=float)
    wet = np.isin(np.array([x.month for x in d.to_list()]), [9, 10, 11, 12])
    rain = rng.gamma(0.4, 8.0, n) * np.where(wet, 3.0, 0.7)
    q = np.empty(n)
    q[0] = 50.0
    for t in range(1, n):
        q[t] = 0.85 * q[t - 1] + 4.0 * rain[t - 1] + 5.0
    df = pl.DataFrame({
        "date": d, "discharge": q,
        "rain_thuong": rain * 1.2, "rain_trung": rain, "rain_ha": rain * 0.8,
        "rain_basin": rain, "api": np.convolve(rain, 0.9 ** np.arange(30))[:n],
        "doy_sin": np.sin(2 * np.pi * doy / 365.25), "doy_cos": np.cos(2 * np.pi * doy / 365.25),
        "mua_lu": wet.astype(np.int64)})
    return df.with_columns(
        pl.col("discharge").shift(1).alias("discharge_lag1"),
        *[pl.col("discharge").shift(-h).alias(f"target_h{h}") for h in (1, 2, 3)],
        pl.lit(None, dtype=pl.Int8).alias("alert_level"))


# ---------------------------------------------------------------- mốc fold

def test_moc_fold_2020():
    b = wf.fold_bounds(2020)
    assert b == {"train_end": "2018-12-25", "valid_start": "2018-12-29",
                 "valid_end": "2019-12-28", "test_start": "2020-01-01",
                 "test_end": "2020-12-31"}


@pytest.mark.parametrize("year", [*wf.TEST_YEARS, wf.EXTRA_YEAR])
def test_gap_va_valid_nam_trong_phan_hoc(year):
    b = {k: _d(v) for k, v in wf.fold_bounds(year).items()}
    gap = wf.GAP_DAYS
    # Nhãn h = 3 của ngày học cuối không chạm năm test; giữa hai bên đúng 3 ngày trống.
    assert b["valid_end"] + timedelta(days=max(dl.cfg.HORIZONS)) < b["test_start"]
    assert (b["test_start"] - b["valid_end"]).days == gap + 1
    # Valid = 365 ngày cuối phần học; train trong cách valid một gap.
    assert (b["valid_end"] - b["valid_start"]).days + 1 == wf.VALID_DAYS
    assert (b["valid_start"] - b["train_end"]).days == gap + 1
    assert b["train_end"] + timedelta(days=gap) < b["valid_start"]
    assert b["test_end"] == date(year, 12, 31)


def test_fold_mo_rong_va_test_khong_chong_lan():
    bs = [wf.fold_bounds(y) for y in wf.TEST_YEARS]
    for a, b in zip(bs, bs[1:]):
        assert a["valid_end"] < b["valid_end"]                       # phần học lớn dần
        assert _d(a["test_end"]) + timedelta(days=1) == _d(b["test_start"])


def test_mat_na_dl_khop_fold(toy_panel):
    """dl.split_masks với khoá fold: train trong / valid / năm test đúng mốc, không giao nhau."""
    conf = {**dl.DEFAULTS, **wf.fold_bounds(2018)}
    dates = toy_panel["date"].to_numpy()
    tr, va, te = dl.split_masks(dates, conf)
    d = dates.astype("datetime64[D]")
    assert d[tr].max() == np.datetime64("2016-12-25")
    assert d[va].min() == np.datetime64("2016-12-29") and d[va].max() == np.datetime64("2017-12-28")
    assert va.sum() == 365
    assert d[te].min() == np.datetime64("2018-01-01") and d[te].max() == np.datetime64("2018-12-31")
    assert not (tr & va).any() and not (va & te).any() and not (tr & te).any()
    fit, te2 = wf.fold_masks(dates, wf.fold_bounds(2018))
    np.testing.assert_array_equal(te, te2)
    assert (fit >= (tr | va)).all() and not (fit & te).any()


def test_hoc_lai_gom_ca_gap_va_khong_vuot_moc(toy_panel):
    conf = {**dl.DEFAULTS, **SMALL, **wf.fold_bounds(2018)}
    p = dl.prepare(toy_panel, conf)
    s = p["sets"]
    assert s["trval"]["date"].max() == np.datetime64("2017-12-28")
    assert np.isin(np.array(["2016-12-27"], dtype="datetime64[D]"), s["trval"]["date"]).all()
    assert s["train"]["date"].max() <= np.datetime64("2016-12-25")
    assert s["valid"]["date"].min() >= np.datetime64("2016-12-29")
    assert s["test"]["date"].min() >= np.datetime64("2018-01-01")
    assert s["test"]["date"].max() <= np.datetime64("2018-12-31")


# ---------------------------------------------------------------- không rò rỉ

def test_chuan_hoa_chi_tu_train_trong(toy_panel):
    """Sửa mọi thứ sau train_end (valid, gap, test, tương lai) → mu/sd không đổi."""
    conf = {**dl.DEFAULTS, **SMALL, **wf.fold_bounds(2018)}
    a = dl.prepare(toy_panel, conf)
    pha = toy_panel.with_columns(*[
        pl.when(pl.col("date") > date(2016, 12, 25)).then(pl.col(c) * 37 + 5)
        .otherwise(pl.col(c)).alias(c) for c in ("discharge", "rain_basin", "api")])
    b = dl.prepare(pha, conf)
    np.testing.assert_allclose(a["mu"], b["mu"])
    np.testing.assert_allclose(a["sd"], b["sd"])


def test_nguong_muc_1_chi_tu_phan_hoc(toy_panel):
    conf = {**dl.DEFAULTS, **SMALL, **wf.fold_bounds(2018)}
    a = dl.prepare(toy_panel, conf)["thr"]
    pha = toy_panel.with_columns(
        pl.when(pl.col("date") >= date(2017, 12, 29)).then(pl.col("discharge") * 9)
        .otherwise(pl.col("discharge")).alias("discharge"))
    assert dl.prepare(pha, conf)["thr"] == pytest.approx(a)
    m = toy_panel.filter((pl.col("date") <= date(2017, 12, 28))
                         & pl.col("date").dt.month().is_in([9, 10, 11, 12]))
    assert a == pytest.approx(float(np.quantile(m["discharge"].to_numpy(), 0.95)))


# ---------------------------------------------------------------- chấm điểm

def test_score_mua_lu_va_su_kien():
    dates = np.array(["2020-08-31", "2020-09-01", "2020-10-01", "2020-12-31"],
                     dtype="datetime64[D]")
    y = np.array([[10.0] * 3, [100.0] * 3, [300.0] * 3, [50.0] * 3])
    yhat = y.copy()
    yhat[0] = 1000.0                                    # sai lớn NGOÀI mùa lũ, báo động nhầm
    yhat[2] = 150.0                                     # bỏ sót một ngày ≥ ngưỡng
    y[3, 2] = np.nan                                    # nhãn thiếu bị bỏ
    r = wf.score(dates, y, yhat, thr=200.0)
    assert [x["n"] for x in r] == [4, 4, 3]
    assert r[0]["n_flood"] == 3
    np.testing.assert_allclose(r[0]["NSE_flood"],
                               1 - 150 ** 2 / np.sum((y[1:, 0] - y[1:, 0].mean()) ** 2))
    assert r[0]["NSE"] < r[0]["NSE_flood"]
    assert (r[0]["hits"], r[0]["misses"], r[0]["false_alarms"]) == (0, 1, 1)


def test_tong_hop_so_voi_lightgbm():
    """ΔNSE từng fold = TB seed mô hình − TB seed LightGBM; thắng/thua; CI bao trung bình."""
    rows = []
    for y, (ref, dln) in zip(range(2013, 2019), [(0.5, 0.6), (0.4, 0.45), (0.3, 0.2),
                                                 (0.6, 0.7), (0.5, 0.55), (0.2, 0.3)]):
        for s, eps in ((42, -0.01), (7, 0.01)):
            for m, v in ((wf.REF, ref), ("lstm_L30_mse", dln)):
                rows.append({"run": "main", "model": m, "year": y, "seed": s, "threads": 2,
                             "horizon": 1, "NSE": v + eps, "NSE_flood": v, "KGE": v,
                             "peak_bias": -0.5, "hits": 1, "misses": 1, "false_alarms": 0})
    s = wf.summarize(pl.DataFrame(rows))
    r = s.filter((pl.col("period") == "2013-2021") & (pl.col("model") == "lstm_L30_mse")).row(
        0, named=True)
    assert r["n_folds"] == 6 and r["wins"] == 5 and r["losses"] == 1
    assert r["dNSE_mean"] == pytest.approx(np.mean([0.1, 0.05, -0.1, 0.1, 0.05, 0.1]), abs=1e-4)
    assert r["dNSE_ci_lo"] <= r["dNSE_mean"] <= r["dNSE_ci_hi"]
    assert 0 < r["wilcoxon_p"] <= 1
    assert r["POD"] == pytest.approx(0.5) and r["FAR"] == pytest.approx(0.0)
    ref = s.filter((pl.col("period") == "2013-2021") & (pl.col("model") == wf.REF)).row(
        0, named=True)
    assert ref["wins"] is None and np.isnan(ref["dNSE_mean"])


def test_boot_ci_hang_so():
    lo, hi = wf.boot_ci(np.full(5, 0.07))
    assert lo == pytest.approx(0.07) and hi == pytest.approx(0.07)
    assert np.isnan(wf.boot_ci(np.array([0.1]))[0])


# ---------------------------------------------------------------- chạy một lượt

def test_run_job_dl_va_lightgbm_tren_panel_gia(toy_panel, tmp_path):
    path = tmp_path / "panel.parquet"
    toy_panel.write_parquet(path)
    base = {"run": "main", "year": 2019, "seed": 42, "threads": 1, "panel_path": str(path)}
    r = wf.run_job({**base, "model": "lstm_L30_mse", "override": SMALL})
    assert [x["horizon"] for x in r["rows"]] == [1, 2, 3]
    assert all(x["n"] == 365 and np.isfinite(x["NSE"]) for x in r["rows"])
    assert 1 <= r["rows"][0]["best_epoch"] <= SMALL["max_epochs"]
    g = wf.run_job({**base, "model": wf.REF})
    assert all(x["n"] == 365 and np.isfinite(x["NSE"]) for x in g["rows"])
    assert g["rows"][0]["threshold"] == pytest.approx(r["rows"][0]["threshold"])
