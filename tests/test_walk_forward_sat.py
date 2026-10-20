"""Walk-forward theo năm cho mưa vệ tinh: mốc fold, gap 3 ngày, train không chạm
năm test, ngưỡng mức 1 chỉ từ train — dữ liệu giả lập (trừ một test đối chiếu
panel thật, bỏ qua nếu thiếu file)."""

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from src import config as cfg

wf = pytest.importorskip("src.eval.walk_forward_sat")
ab = wf.ab
START = date(2010, 1, 1)


def _panel(seed: int = 0, lo: date = START, hi: date = date(2016, 12, 31)) -> pl.DataFrame:
    d = pl.date_range(lo, hi, "1d", eager=True)
    rng = np.random.default_rng(seed)
    return _targets(pl.DataFrame({"date": d, "discharge": rng.gamma(2.0, 100.0, len(d)),
                                  "x": rng.normal(size=len(d))}))


def _targets(p: pl.DataFrame) -> pl.DataFrame:
    """target_h = lưu lượng t+h (null ở cuối chuỗi), như panel thật."""
    return p.with_columns([pl.col("discharge").shift(-h).alias(f"target_h{h}") for h in cfg.HORIZONS])


def _bump_from(p: pl.DataFrame, year: int, k: float = 100.0) -> pl.DataFrame:
    """Nhân lưu lượng từ 01/01/year trở đi lên k lần (giả lập 'tương lai' khác hẳn)."""
    q = pl.when(pl.col("date") >= date(year, 1, 1)).then(pl.col("discharge") * k).otherwise(pl.col("discharge"))
    return _targets(p.with_columns(q.alias("discharge")))


# ------------------------------------------------------------ mốc fold, gap

def test_fold_dung_moc():
    assert wf.year_fold(2015, START) == {"train": (START, date(2014, 12, 28)),
                                         "test": (date(2015, 1, 1), date(2015, 12, 31))}
    assert wf.YEARS == tuple(range(2013, 2026)) and len(wf.YEARS) == 13
    assert wf.PARTIAL == 2026 and wf.fold_type(2026) == "le" and wf.fold_type(2025) == "du_nam"
    assert wf.PERIODS[wf.MAIN] == (2013, 2025)


@pytest.mark.parametrize("year", [*wf.YEARS, wf.PARTIAL])
def test_gap_3_ngay_nhan_khong_cham_nam_test(year):
    f = wf.year_fold(year, START)
    tr_end, te_lo = f["train"][1], f["test"][0]
    assert te_lo == date(year, 1, 1)
    assert (te_lo - tr_end).days - 1 == wf.GAP == max(cfg.HORIZONS)
    for h in cfg.HORIZONS:                       # nhãn t+h của hàng train cuối vẫn trước năm test
        assert tr_end + timedelta(days=h) < te_lo


@pytest.mark.parametrize("year", [2012, 2014, 2016])
def test_mask_train_khong_cham_nam_test(year):
    p = _panel()
    d = p["date"]
    for h in cfg.HORIZONS:
        m = ab.masks(p, ["x"], h, wf.year_fold(year, START))
        tr, te = d.filter(pl.Series(m["train"])), d.filter(pl.Series(m["test"]))
        assert not (m["train"] & m["test"]).any()
        assert tr.max() == date(year - 1, 12, 28)
        assert (tr + timedelta(days=h)).max() < date(year, 1, 1)
        assert te.dt.year().unique().to_list() == [year]
        # đổi toàn bộ lưu lượng từ năm test trở đi → X, y của hàng train không đổi
        p2 = _bump_from(p, year)
        m2 = ab.masks(p2, ["x"], h, wf.year_fold(year, START))
        assert (m2["train"] == m["train"]).all()
        y1 = p[f"target_h{h}"].to_numpy()[m["train"]]
        y2 = p2[f"target_h{h}"].to_numpy()[m["train"]]
        np.testing.assert_array_equal(y1, y2)


# ------------------------------------------------------------ ngưỡng mức 1

def test_nguong_chi_tu_train_mua_lu():
    p = _panel(seed=1)
    lo, hi = wf.year_fold(2015, START)["train"]
    thr = wf.fold_threshold(p, lo, hi)
    s = p.filter(pl.col("date").is_between(lo, hi) & pl.col("date").dt.month().is_in([9, 10, 11, 12]))
    assert thr == pytest.approx(np.quantile(s["discharge"].to_numpy(), 0.95))
    # tương lai (≥ 2015, gồm 3 ngày gap cuối 2014 thì không) thay đổi → ngưỡng không đổi
    assert wf.fold_threshold(_bump_from(p, 2015), lo, hi) == thr
    gap = p.with_columns(pl.when(pl.col("date") > hi).then(1e6).otherwise(pl.col("discharge"))
                         .alias("discharge"))
    assert wf.fold_threshold(gap, lo, hi) == thr
    # ngoài mùa lũ không tham gia
    dry = p.with_columns(pl.when(pl.col("date").dt.month() < 9).then(1e6).otherwise(pl.col("discharge"))
                         .alias("discharge"))
    assert wf.fold_threshold(dry, lo, hi) == thr


def test_nguong_split_chinh_khop_risk_levels():
    panel = cfg.DATA_PROCESSED / "daily_panel.parquet"
    risk = cfg.ROOT / "reports" / "risk_levels.csv"
    if not (panel.exists() and risk.exists()):
        pytest.skip("thiếu daily_panel.parquet / risk_levels.csv")
    ref = pl.read_csv(risk).filter(pl.col("muc") == "nguy_co_1")["nguong_m3s"].item()
    thr = wf.fold_threshold(pl.read_parquet(panel), date(1900, 1, 1), date.fromisoformat(cfg.VALID_END))
    assert round(thr, 1) == pytest.approx(ref)


# ------------------------------------------------------------ tổng hợp

def test_tong_hop_wilcoxon_bootstrap_su_kien_gop(monkeypatch, tmp_path):
    pytest.importorskip("scipy")
    monkeypatch.setattr(wf, "SPLIT_CSV", tmp_path / "khong_co.csv")
    years = [*wf.YEARS, wf.PARTIAL]
    d = np.linspace(0.005, 0.03, len(wf.YEARS)).tolist() + [-0.5]     # 2026 âm rất mạnh
    rows = []
    for i, y in enumerate(years):
        common = {"group": "r2", "horizon": 2, "fold": y, "peak_bias": 0.0,
                  "hits1": 2, "misses1": 1, "false_alarms1": 1}
        rows.append({**common, "config": "A0", "NSE": 0.4, "NSE_flood": 0.3})
        rows.append({**common, "config": "A0+x", "NSE": 0.4 + d[i], "NSE_flood": 0.3 + d[i],
                     "dNSE": d[i], "dNSE_flood": d[i],
                     **{f"dNSE_seed{s}": d[i] for s in wf.SEEDS}})
    s = wf.summarize(pl.from_dicts(rows, infer_schema_length=None))
    r = s.filter((pl.col("config") == "A0+x") & (pl.col("period") == wf.MAIN)).row(0, named=True)
    assert r["n_folds"] == 13 and (r["fold_tu"], r["fold_den"]) == (2013, 2025)   # 2026 không vào
    assert r["dNSE_mean"] == pytest.approx(np.mean(d[:13]))
    assert (r["n_win"], r["n_loss"]) == (13, 0)
    assert r["p_wilcoxon"] == pytest.approx(2 / 2 ** 13)          # 13 dấu dương, p chính xác
    assert r["dNSE_ci_lo"] <= r["dNSE_mean"] <= r["dNSE_ci_hi"]
    assert min(d[:13]) <= r["dNSE_ci_lo"] and r["dNSE_ci_hi"] <= max(d[:13])
    assert (r["n_pos1"], r["hits1"], r["false_alarms1"]) == (39, 26, 13)
    assert r["POD1"] == pytest.approx(26 / 39) and r["CSI1"] == pytest.approx(26 / 52)
    le = s.filter((pl.col("config") == "A0+x") & (pl.col("period") == "le_2026_01_08")).row(0, named=True)
    assert le["n_folds"] == 1 and le["dNSE_mean"] == pytest.approx(-0.5)
    assert np.isnan(le["p_wilcoxon"])
    base = s.filter((pl.col("config") == "A0") & (pl.col("period") == wf.MAIN)).row(0, named=True)
    assert base["dNSE_mean"] is None and base["NSE_mean"] == pytest.approx(0.4)
