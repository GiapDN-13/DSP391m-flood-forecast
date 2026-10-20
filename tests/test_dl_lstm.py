"""Test cho mô hình DL (src/models/dl_lstm.py) — không cần mạng, dùng panel giả lập.

Ba điều phải khoá: cửa sổ không nhìn tương lai, chuẩn hoá chỉ dùng tập train,
và `train(config)` là hàm thuần chạy được (kể cả DDP 2 tiến trình như trong
Spark TorchDistributor).
"""

from datetime import date

import numpy as np
import polars as pl
import pytest
import torch

from src.models import dl_lstm as dl

SMALL = {"hidden": 8, "max_epochs": 3, "patience": 2, "batch_size": 128,
         "num_threads": 1, "seq_len": 7}


@pytest.fixture(scope="module")
def toy_panel() -> pl.DataFrame:
    """Panel giả 2013 → 2023-06 đủ cả 3 tập; Q phản ứng trễ với mưa, có vài đợt lũ."""
    rng = np.random.default_rng(0)
    d = pl.date_range(date(2013, 1, 1), date(2023, 6, 30), "1d", eager=True)
    n = d.len()
    doy = np.array([x.timetuple().tm_yday for x in d.to_list()], dtype=float)
    wet = np.isin(np.array([x.month for x in d.to_list()]), [9, 10, 11, 12])
    rain = rng.gamma(0.4, 8.0, n) * np.where(wet, 3.0, 0.7)
    q = np.empty(n)
    q[0] = 50.0
    for t in range(1, n):
        q[t] = 0.85 * q[t - 1] + 4.0 * rain[t - 1] + 5.0
    df = pl.DataFrame({
        "date": d,
        "discharge": q,
        "rain_thuong": rain * 1.2, "rain_trung": rain, "rain_ha": rain * 0.8,
        "rain_basin": rain,
        "api": np.convolve(rain, 0.9 ** np.arange(30))[:n],
        "doy_sin": np.sin(2 * np.pi * doy / 365.25),
        "doy_cos": np.cos(2 * np.pi * doy / 365.25),
        "mua_lu": wet.astype(np.int64),
    })
    df = df.with_columns(
        pl.col("discharge").shift(1).alias("discharge_lag1"),
        pl.col("rain_basin").shift(1).alias("rain_basin_lag1"),
        *[pl.col("discharge").shift(-h).alias(f"target_h{h}") for h in (1, 2, 3)],
        pl.lit(None, dtype=pl.Int8).alias("alert_level"),
    )
    return df


@pytest.fixture(scope="module")
def panel_path(toy_panel, tmp_path_factory) -> str:
    p = tmp_path_factory.mktemp("dl") / "panel.parquet"
    toy_panel.write_parquet(p)
    return str(p)


# ---------------------------------------------------------------- cửa sổ

def test_cua_so_ket_thuc_tai_t_va_khong_nhin_tuong_lai():
    X = np.arange(40, dtype=float).reshape(20, 2)
    end, W = dl.make_windows(X, 5)
    assert end[0] == 4 and len(end) == 16
    np.testing.assert_array_equal(W[3], X[3:8])       # cửa sổ kết thúc tại t = end[3] = 7
    X2 = X.copy()
    X2[8:] = -999.0                                    # sửa tương lai của t = 7
    _, W2 = dl.make_windows(X2, 5)
    np.testing.assert_array_equal(W2[3], W[3])


def test_cua_so_co_nan_bi_bo():
    X = np.ones((10, 1))
    X[4] = np.nan
    end, _ = dl.make_windows(X, 3)
    assert not set(end) & {4, 5, 6}                    # mọi cửa sổ chứa hàng 4
    assert set(end) == {2, 3, 7, 8, 9}


def test_split_theo_moc_config():
    dates = np.array(["2015-12-31", "2016-01-01", "2022-06-30", "2022-07-01"],
                     dtype="datetime64[D]")
    tr, va, te = dl.split_masks(dates, dl.DEFAULTS)
    assert tr.tolist() == [True, False, False, False]
    assert va.tolist() == [False, True, True, False]
    assert te.tolist() == [False, False, False, True]


# ---------------------------------------------------------------- chuẩn bị dữ liệu

def test_chuan_hoa_chi_dung_train(toy_panel):
    conf = {**dl.DEFAULTS, **SMALL}
    a = dl.prepare(toy_panel, conf)
    pha = toy_panel.with_columns(
        pl.when(pl.col("date") > date(2015, 12, 31)).then(pl.col("discharge") * 50)
        .otherwise(pl.col("discharge")).alias("discharge"))
    b = dl.prepare(pha, conf)
    np.testing.assert_allclose(a["mu"], b["mu"])
    np.testing.assert_allclose(a["sd"], b["sd"])


def test_mau_dung_ngay_va_dung_nhan(toy_panel):
    """Mẫu tại t: hàng cuối cửa sổ là Q_t, nhãn h là Q_{t+h}."""
    conf = {**dl.DEFAULTS, **SMALL}
    p = dl.prepare(toy_panel, conf)
    s = p["sets"]["valid"]
    q = toy_panel["discharge"].to_numpy()
    days = (s["date"] - np.datetime64("2013-01-01")).astype(int)
    lq_last = s["X"][:, -1, p["q_idx"]] * p["sd"][p["q_idx"]] + p["mu"][p["q_idx"]]
    np.testing.assert_allclose(np.expm1(lq_last), q[days], rtol=1e-4)
    for j, h in enumerate((1, 2, 3)):
        np.testing.assert_allclose(s["Yraw"][:, j], q[days + h])
    assert s["date"].min() > np.datetime64("2015-12-31")


def test_trong_so_dinh_lu(toy_panel):
    conf = {**dl.DEFAULTS, **SMALL, "loss": "peak"}
    s = dl.prepare(toy_panel, conf)["sets"]["train"]
    assert s["W"].min() >= 1.0 and s["W"].max() <= conf["peak_w_max"]
    k = np.argsort(s["Yraw"][:, 0])
    assert np.all(np.diff(s["W"][k, 0]) >= 0)          # lưu lượng lớn → trọng số không nhỏ hơn
    s0 = dl.prepare(toy_panel, {**conf, "loss": "mse"})["sets"]["train"]
    assert np.all(s0["W"] == 1.0)


def test_nguong_muc_1_tren_train_valid_mua_lu(toy_panel):
    p = dl.prepare(toy_panel, {**dl.DEFAULTS, **SMALL})
    m = toy_panel.filter((pl.col("date") <= date(2022, 6, 30))
                         & pl.col("date").dt.month().is_in([9, 10, 11, 12]))
    assert p["thr"] == pytest.approx(float(np.quantile(m["discharge"].to_numpy(), 0.95)))


# ---------------------------------------------------------------- mô hình

def test_residual_head_0_bang_persistence():
    net = dl.LSTMNet(n_in=3, n_out=3, hidden=4, layers=1, dropout=0.0,
                     residual=True, q_idx=1)
    torch.nn.init.zeros_(net.head.weight)
    torch.nn.init.zeros_(net.head.bias)
    x = torch.randn(5, 7, 3)
    out = net(x)
    assert out.shape == (5, 3)
    torch.testing.assert_close(out, x[:, -1, 1:2].expand(5, 3))


def test_weighted_mse_w1_bang_mse():
    p, y = torch.randn(10, 3), torch.randn(10, 3)
    torch.testing.assert_close(dl.weighted_mse(p, y, torch.ones(10, 3)),
                               torch.mean((p - y) ** 2))


# ---------------------------------------------------------------- train()

def test_train_chay_va_khong_doi_config(panel_path):
    conf = {**SMALL, "panel_path": panel_path, "name": "toy"}
    before = dict(conf)
    r = dl.train(conf)
    assert conf == before                               # hàm thuần: không sửa đầu vào
    keys = {(x["fit"], x["split"], x["horizon"]) for x in r["results"]}
    assert len(keys) == 9                               # valid + test + test(refit) × 3 h
    test_refit = [x for x in r["results"] if x["fit"] == "train+valid"]
    assert all(np.isfinite(x["NSE"]) for x in test_refit)
    assert r["pred"]["train+valid"].shape == (r["n_test"], 3)
    assert (r["pred"]["train+valid"] >= 0).all()
    assert 1 <= r["best_epoch"] <= SMALL["max_epochs"]


def test_mlp_full_features_chay(panel_path):
    r = dl.train({**SMALL, "panel_path": panel_path, "model": "mlp", "seq_len": 1,
                  "features": "full", "loss": "peak", "refit": False})
    assert r["config"]["features"] == "full"
    assert {x["fit"] for x in r["results"]} == {"train"}


def test_ddp_hai_tien_trinh(panel_path):
    """Như TorchDistributor(local_mode=True, num_processes=2): gloo trên CPU."""
    if not torch.distributed.is_available() or not torch.distributed.is_gloo_available():
        pytest.skip("torch build không có gloo")
    r = dl.run_local_ddp({**SMALL, "panel_path": panel_path, "max_epochs": 2,
                          "refit": False}, world_size=2)
    assert r["world_size"] == 2 and r["rank"] == 0
    assert all(np.isfinite(x["NSE"]) for x in r["results"])
