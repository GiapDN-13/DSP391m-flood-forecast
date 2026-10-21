"""Tinh chỉnh cấu hình E bằng walk-forward + Optuna: tập cột của từng biến thể,
tham số ghi đè không làm bẩn ``lgbm.PARAMS``, không gian Optuna chứa E, chia
valid không chạm test, ΔNSE/tổng hợp đúng — dữ liệu giả lập, LightGBM rất nhỏ."""

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from src import config as cfg
from src.models import ablation_ext as ax
from src.models import lgbm

wt = pytest.importorskip("src.eval.wf_tuning")

FEATS = ["discharge_lag1", "rain_basin", *ax.SOIL, *ax.RESERVOIR_PROXY, "oni_lag3"]


# ------------------------------------------------------------ biến thể

def test_bien_the_bo_dung_cot():
    c = wt.configs_for(list(wt.VARIANTS), FEATS)
    assert c["E"][0] == FEATS
    assert c["E-SOIL"][0] == [f for f in FEATS if f not in ax.SOIL]
    assert set(FEATS) - set(c["E-SOIL"][0]) == {"sm_0_7", "sm_7_28", "sm_28_100", "et0"}
    assert set(FEATS) - set(c["E-rain_season_cum"][0]) == {"rain_season_cum"}
    assert set(FEATS) - set(c["E-SOIL-rain_season_cum"][0]) == {*ax.SOIL, "rain_season_cum"}
    for n in ("E mcs10", "E quantile0.9", "E L2"):
        assert c[n][0] == FEATS                    # chỉ đổi tham số, giữ nguyên cột
    assert c["E mcs10"][1] == {"min_child_samples": 10}
    assert c["E quantile0.9"][1] == {"objective": "quantile", "alpha": 0.9}
    assert c["E L2"][1] == {"objective": "regression"}


def test_bo_cot_khong_co_thi_bao_loi():
    with pytest.raises(ValueError):
        wt.config_features(["a", "b"], ["sm_0_7"])
    with pytest.raises(ValueError):
        wt.configs_for(["E la"], FEATS)


def test_tham_so_ghi_de_khong_sua_params_goc():
    goc = dict(lgbm.PARAMS)
    p = wt.model_params({"objective": "quantile", "alpha": 0.9}, seed=7, n_jobs=2)
    assert p["objective"] == "quantile" and p["alpha"] == 0.9
    assert p["random_state"] == 7 and p["n_jobs"] == 2
    assert p["min_child_samples"] == goc["min_child_samples"] == 30
    assert lgbm.PARAMS == goc                       # không đổi PARAMS gốc
    assert wt.model_params({}, 42, 4)["objective"] == "regression_l1"


@pytest.mark.skipif(not wt.sa.PANEL.exists(), reason="thiếu daily_panel.parquet")
def test_tap_cot_E_that():
    f = wt.e_features()
    assert len(f) == len(set(f)) == 88
    assert set(ax.SOIL) <= set(f) and "rain_season_cum" in f
    assert not any(c.startswith("target_") for c in f)


# ------------------------------------------------------------ Optuna

class _Ghi:
    """Trial giả: ghi lại miền của mọi tham số, trả về cận dưới."""
    def __init__(self):
        self.mien = {}

    def suggest_int(self, k, lo, hi, step=1, log=False):
        self.mien[k] = (lo, hi, step)
        return lo

    def suggest_float(self, k, lo, hi, log=False):
        self.mien[k] = (lo, hi, None)
        return lo


def test_khong_gian_optuna_chua_tham_so_E():
    t = _Ghi()
    wt.search_space(t)
    assert set(t.mien) == set(wt.TUNED)
    for k, v in wt.e_defaults().items():
        lo, hi, step = t.mien[k]
        assert lo <= v <= hi, k
        if step and step > 1:
            assert (v - lo) % step == 0, k


def test_fixed_trial_tra_ve_E():
    optuna = pytest.importorskip("optuna")
    assert wt.search_space(optuna.trial.FixedTrial(wt.e_defaults())) == wt.e_defaults()


def test_valid_optuna_khong_cham_test():
    assert wt.OPT_TRAIN[0] == date(1998, 1, 4)
    assert (wt.OPT_VALID[0] - wt.OPT_TRAIN[1]).days - 1 == max(cfg.HORIZONS)
    assert wt.OPT_VALID[1] == date.fromisoformat(cfg.VALID_END)
    assert wt.OPT_VALID[1] < date.fromisoformat(cfg.GLOFAS_REGIME_BREAK) == wt.TEST_SPLIT["test"][0]


def test_best_params_doc_dong_duoc_chon(tmp_path):
    p = tmp_path / "t.csv"
    rows = [{"trial": i, "chon": i == 2, **{f"p_{k}": v + i for k, v in wt.e_defaults().items()}}
            for i in range(3)]
    pl.from_dicts(rows).write_csv(p)
    b = wt.best_params(p)
    assert b["num_leaves"] == 33 and isinstance(b["num_leaves"], int)
    assert b["learning_rate"] == pytest.approx(2.05) and isinstance(b["learning_rate"], float)


# ------------------------------------------------------------ chỉ số, tổng hợp

def test_ty_le_phu():
    y = np.array([100.0, 900.0, 1000.0, 50.0])
    s = wt.score(y, y * 1.1, np.ones(4, bool), 800.0)
    assert s["cover_all"] == 1.0 and s["n_cover_pos1"] == 2 == s["n_pos1"]
    s = wt.score(y, y * 0.9, np.ones(4, bool), 800.0)
    assert s["cover_all"] == 0.0 and s["n_cover_pos1"] == 0


def _folds() -> pl.DataFrame:
    rows = []
    for fold in wt.YEARS:
        for h in cfg.HORIZONS:
            for c, nse in (("persistence", 0.3), ("E", 0.6), ("E L2", 0.6 + 0.01 * (fold % 2)),
                           ("E-SOIL", 0.55)):
                rows.append({"fold": fold, "horizon": h, "config": c, "NSE": nse, "NSE_seed42": nse,
                             "NSE_flood": nse - 0.1, "peak_bias": -0.3, "KGE": nse,
                             "hits1": 2, "misses1": 1, "false_alarms1": 1, "n_cover_pos1": 1,
                             "cover_all": 0.5})
    return pl.from_dicts(rows)


def test_delta_va_tong_hop():
    f = wt.add_deltas(_folds())
    assert f.filter(pl.col("config").is_in(["E", "persistence"]))["dNSE"].null_count() == 2 * 13 * 3
    assert f.filter(pl.col("config") == "E-SOIL")["dNSE"].to_numpy() == pytest.approx(-0.05)
    s = wt.summarize(f)
    m = s.filter((pl.col("period") == wt.MAIN) & (pl.col("horizon") == 1))
    soil = m.filter(pl.col("config") == "E-SOIL").row(0, named=True)
    assert soil["n_folds"] == 13 and soil["n_loss"] == 13 and soil["n_win"] == 0
    assert soil["dNSE_ci_lo"] == pytest.approx(-0.05) and soil["p_wilcoxon"] < 0.001
    l2 = m.filter(pl.col("config") == "E L2").row(0, named=True)
    assert l2["n_win"] == 7 and l2["n_loss"] == 0          # 7 năm lẻ trong 2013–2025
    assert l2["POD1"] == pytest.approx(2 / 3) and l2["FAR1"] == pytest.approx(1 / 3)
    assert l2["cover_pos1"] == pytest.approx(1 / 3)
    nv = s.filter((pl.col("period") == "ngoai_valid_optuna") & (pl.col("config") == "E"))
    assert set(nv["n_folds"].to_list()) == {6}


def test_tong_hop_co_valid():
    va = pl.DataFrame({"config": ["E", "E", "E L2", "E L2"], "horizon": [1, 2, 1, 2],
                       "NSE_valid": [0.70, 0.40, 0.72, 0.38]})
    s = wt.summarize(wt.add_deltas(_folds()), valid=va).filter(pl.col("period") == wt.VALID_PERIOD)
    d = {(r["config"], r["horizon"]): r["dNSE_mean"] for r in s.iter_rows(named=True)}
    assert d[("E", 1)] is None
    assert d[("E L2", 1)] == pytest.approx(0.02) and d[("E L2", 2)] == pytest.approx(-0.02)


# ------------------------------------------------------------ chạy thật (rất nhỏ)

def _panel() -> pl.DataFrame:
    d = pl.date_range(date(2009, 1, 1), date(2013, 12, 31), "1d", eager=True)
    rng = np.random.default_rng(0)
    q = rng.gamma(2.0, 100.0, len(d))
    p = pl.DataFrame({"date": d, "discharge": q, "x": q + rng.normal(0, 5, len(d)),
                      "z": rng.normal(size=len(d))})
    return p.with_columns([pl.col("discharge").shift(-h).alias(f"target_h{h}") for h in cfg.HORIZONS])


def test_run_wf_gap_va_moc():
    p = _panel()
    cfgs = {"E": (["x", "z"], {"n_estimators": 20}), "E L2": (["x"], {"n_estimators": 20,
                                                                    "objective": "regression"})}
    rows = wt.run_wf(p, ["x", "z"], cfgs, [2013], (42,), 1)
    f = pl.from_dicts(rows)
    assert set(f["config"]) == {"persistence", "E", "E L2"} and f.height == 9
    for r in f.iter_rows(named=True):
        assert r["train_end"] == date(2012, 12, 28) and r["gap_days"] == 3
        assert r["test_start"] == date(2013, 1, 1) and r["train_start"] == date(2009, 1, 1)
        assert r["train_end"] + timedelta(days=r["horizon"]) < r["test_start"]
    assert f.filter(pl.col("config") == "E L2")["n_feat"].to_list() == [1, 1, 1]


def test_ghep_seed_bang_chay_chung(tmp_path):
    """Chạy từng seed riêng rồi ghép = chạy 2 seed một lần (ensemble trung bình)."""
    p = _panel()
    cfgs = {"E": (["x", "z"], {"n_estimators": 15})}
    both = pl.from_dicts(wt.run_wf(p, ["x", "z"], cfgs, [2013], (42, 7), 1))
    for s in (42, 7):
        wt.run_wf(p, ["x", "z"], cfgs, [2013], (s,), 1, preds_out=tmp_path / f"preds_{s}.parquet")
    preds = pl.concat([pl.read_parquet(tmp_path / f"preds_{s}.parquet") for s in (42, 7)])
    assert set(preds.columns) >= {"fold", "horizon", "config", "seed", "date", "y", "yhat", "flood", "thr1"}
    assert wt.common_seeds(preds, years=(2013,)) == [7, 42]
    assert wt.common_seeds(preds.filter(~((pl.col("seed") == 7) & (pl.col("horizon") == 3))),
                           years=(2013,)) == [42]
    ens = wt.folds_from_preds(preds, [42, 7]).sort("horizon")
    ref = both.filter(pl.col("config") == "E").sort("horizon")
    assert ens["NSE"].to_numpy() == pytest.approx(ref["NSE"].to_numpy(), abs=1e-12)
    assert ens["NSE_seed7"].to_numpy() == pytest.approx(ref["NSE_seed7"].to_numpy(), abs=1e-12)
