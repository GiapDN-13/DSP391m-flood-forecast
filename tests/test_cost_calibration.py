"""Hiệu chỉnh isotonic (FR-M6): bộ hiệu chỉnh của năm Y không bao giờ thấy dữ liệu
năm ≥ Y; xác suất sau hiệu chỉnh đơn điệu, trong [0, 1]; reliability đếm đúng."""

from datetime import date

import numpy as np
import pytest

ct = pytest.importorskip("src.models.cost_threshold")
pytest.importorskip("sklearn")
pl = pytest.importorskip("polars")


def _oof(seed: int = 3, years=range(2005, 2016)) -> pl.DataFrame:
    """OOF giả: xác suất thô bị "phóng đại" (p_thật = p_thô / 4) để có gì mà hiệu chỉnh."""
    rng = np.random.default_rng(seed)
    parts = []
    for yr in years:
        d = np.arange(np.datetime64(f"{yr}-01-01"), np.datetime64(f"{yr + 1}-01-01"))
        p = rng.beta(0.6, 4.0, len(d))
        y = rng.random(len(d)) < p / 4
        parts.append(pl.DataFrame({"bo_dac_trung": "E", "level": 1, "horizon": 1, "year": yr,
                                   "date": d, "y": y, "p": p, "q0": p * 1000,
                                   "thr_q": 750.0, "w": 30.0}))
    return pl.concat(parts)


def _arrays(o: pl.DataFrame):
    return (o["year"].to_numpy(), o["date"].to_numpy(), o["y"].to_numpy(), o["p"].to_numpy())


def test_bo_hieu_chinh_nam_Y_khong_thay_nam_tu_Y_tro_di():
    oof = _oof()
    Y = 2012
    yr, dt, y, p = _arrays(oof)
    pm, iso, pc_pool, pc_te = ct.calibrate_fold(yr, dt, y, p, Y)
    assert iso is not None
    # bể = năm < Y và ≤ 28/12/(Y−1) — không hàng nào của năm ≥ Y, không hàng nào trong gap
    assert not pm[yr >= Y].any()
    assert not pm[(yr == Y - 1) & (dt > np.datetime64(date(Y - 1, 12, 28)))].any()
    assert pm[yr < Y - 1].all()
    # điểm nút của isotonic chỉ lấy từ xác suất trong bể
    assert np.isin(iso.X_thresholds_, p[pm]).all()

    # xáo trộn tuỳ ý nhãn + xác suất của MỌI năm ≥ Y ⇒ bộ hiệu chỉnh y hệt
    rng = np.random.default_rng(9)
    fut = yr >= Y
    y2, p2 = y.copy(), p.copy()
    y2[fut] = rng.random(fut.sum()) < 0.5
    p2[fut] = rng.random(fut.sum())
    pm2, iso2, pc_pool2, _ = ct.calibrate_fold(yr, dt, y2, p2, Y)
    assert np.array_equal(pm, pm2)
    assert np.array_equal(iso.X_thresholds_, iso2.X_thresholds_)
    assert np.array_equal(iso.y_thresholds_, iso2.y_thresholds_)
    assert np.array_equal(pc_pool, pc_pool2)
    # cùng xác suất năm Y đầu vào ⇒ cùng xác suất đã hiệu chỉnh
    grid = np.linspace(0, 1, 101)
    assert np.array_equal(iso.predict(grid), iso2.predict(grid))


def test_evaluate_cal_khong_nhin_nam_test():
    """Đổi nhãn/xác suất năm test (và năm sau) không đổi ngưỡng đã chọn hay bộ hiệu chỉnh."""
    oof = _oof()

    def picked(o):
        rows, _ = ct.evaluate_cal(o, years=(2012,))
        return {(x["phuong_phap"], x["ty_le"]): (x["nguong_p"], x["n_pool"], x["n_pool_pos"])
                for x in rows}

    base = picked(oof)
    noisy = oof.with_columns(
        pl.when(pl.col("year") >= 2012).then(1 - pl.col("p")).otherwise(pl.col("p")).alias("p"),
        pl.when(pl.col("year") >= 2012).then(~pl.col("y")).otherwise(pl.col("y")).alias("y"))
    assert picked(noisy) == base
    n_pool = oof.filter((pl.col("year") < 2012) & (pl.col("date") <= date(2011, 12, 28))).height
    assert {v[1] for v in base.values()} == {n_pool}


def test_hieu_chinh_don_dieu_trong_0_1_va_giam_brier():
    oof = _oof()
    yr, dt, y, p = _arrays(oof)
    _, iso, _, pc_te = ct.calibrate_fold(yr, dt, y, p, 2013)
    te = yr == 2013
    order = np.argsort(p[te])
    assert np.all(np.diff(pc_te[order]) >= -1e-12)          # đơn điệu không giảm
    assert pc_te.min() >= 0 and pc_te.max() <= 1
    # ngoài phạm vi bể ⇒ kẹp
    assert iso.predict(np.array([-1.0, 2.0])).tolist() == [iso.y_thresholds_[0], iso.y_thresholds_[-1]]
    # dữ liệu giả phóng đại ×4 ⇒ Brier sau hiệu chỉnh tốt hơn hẳn trên năm mới
    assert ct.brier(y[te], pc_te) < ct.brier(y[te], p[te])


def test_it_ngay_duong_khong_hieu_chinh():
    yr = np.repeat([2010, 2011], 50)
    dt = np.array([np.datetime64(date(y, 6, 1)) + i for y in (2010, 2011) for i in range(50)])
    y = np.zeros(100, bool)
    y[:3] = True                                             # 3 < MIN_POOL_POS
    p = np.linspace(0, 1, 100)
    pm, iso, pc_pool, pc_te = ct.calibrate_fold(yr, dt, y, p, 2011)
    assert iso is None
    assert np.array_equal(pc_te, p[yr == 2011])              # giữ xác suất thô


def test_reliability_bins_va_ece():
    y = np.array([0, 0, 1, 1, 0, 1], bool)
    p = np.array([0.05, 0.08, 0.15, 0.95, 1.0, 0.99])
    b = ct.reliability_bins(y, p, 10)
    assert [x["n"] for x in b] == [2, 1, 0, 0, 0, 0, 0, 0, 0, 3]     # p = 1,0 vào khoảng cuối
    assert b[9]["n_pos"] == 2 and b[9]["tan_suat"] == pytest.approx(2 / 3)
    assert sum(x["n"] for x in b) == len(y)
    # một khoảng [0,5; 0,6): p trung bình 0,51, tần suất 0,5 ⇒ ECE = 0,01
    assert ct.ece(np.array([0, 1, 0, 1], bool), np.array([0.5, 0.5, 0.52, 0.52])) == pytest.approx(0.01)
    assert ct.log_loss(np.array([1.0]), np.array([0.0])) == pytest.approx(-np.log(ct.LOGLOSS_EPS))


def test_pool_cal_so_cap_voi_nhanh_tho(tmp_path):
    oof = _oof()
    out, out_bins, fig = ct.run_calibration(oof, years=(2011, 2012, 2013, 2014, 2015),
                                            out=tmp_path / "c.csv", fig=tmp_path / "r.png")
    res = pl.read_csv(out)
    pooled = res.filter(pl.col("pham_vi") == "wf_2013_2025")
    assert set(pooled["phuong_phap"]) == set(ct.CAL_METHODS)
    # nhánh thô chi_phi trùng evaluate_wf cũ (cùng ngưỡng, cùng chi phí từng fold)
    old = [x for x in ct.evaluate_wf(oof, years=(2011, 2012, 2013, 2014, 2015))
           if x["phuong_phap"] == "chi_phi"]
    new = res.filter((pl.col("pham_vi") == "wf_fold") & (pl.col("phuong_phap") == "chi_phi"))
    assert sorted((x["fold"], x["ty_le"], x["cost"]) for x in old) == sorted(
        new.select("fold", "ty_le", "cost").iter_rows())
    iso = pooled.filter((pl.col("phuong_phap") == "chi_phi_iso") & (pl.col("ty_le") == 10))
    assert iso["n_fold"][0] == 5 and iso["p_wilcoxon_vs_raw"].len() == 1
    assert pl.read_csv(out_bins).height == 2 * ct.N_BINS
    assert fig.exists()
