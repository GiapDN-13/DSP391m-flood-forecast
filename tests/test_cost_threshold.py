"""Ngưỡng cảnh báo theo chi phí: chọn đúng ngưỡng trên dữ liệu giả, không bao giờ
dùng dữ liệu test (hay năm test của walk-forward) để chọn."""

from datetime import date

import numpy as np
import pytest

ct = pytest.importorskip("src.models.cost_threshold")

# 3 ngày dương, 7 ngày âm — tính tay được chi phí ở mọi ngưỡng
Y = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0, 0], bool)
P = np.array([0.90, 0.60, 0.30, 0.80, 0.50, 0.20, 0.10, 0.05, 0.04, 0.03])
GRID = np.round(np.arange(0.01, 1.0, 0.01), 2)


def test_chi_phi_dung_cong_thuc():
    # t = 0,30: bắt cả 3, báo nhầm 0,80 và 0,50 ⇒ C = 10·0 + 2
    assert ct.expected_cost(Y, P, 0.30, 10) == 2
    # t = 0,55: hụt 0,30, báo nhầm 0,80 ⇒ C = 10·1 + 1
    assert ct.expected_cost(Y, P, 0.55, 10) == 11
    c = ct.cost_curve(Y, P, 10, GRID)
    assert np.array_equal(c, [ct.expected_cost(Y, P, t, 10) for t in GRID])


def test_chon_nguong_toi_thieu_chi_phi():
    # R = 10: bỏ sót đắt ⇒ hạ ngưỡng tới 0,30 (mọi t ∈ (0,20; 0,30] cùng C = 2,
    # hoà lấy gần 0,5 nhất)
    t, ok = ct.choose_threshold(Y, P, 10, GRID, min_pos=1)
    assert ok and t == pytest.approx(0.30)
    # R = 1: hai vùng cùng C = 2 — [0,81; 0,90] và [0,51; 0,60] ⇒ gần 0,5 nhất
    t, _ = ct.choose_threshold(Y, P, 1, GRID, min_pos=1)
    assert t == pytest.approx(0.51)
    # vét cạn: không ngưỡng nào trong lưới rẻ hơn ngưỡng đã chọn
    for r in (1, 5, 10, 20):
        t, _ = ct.choose_threshold(Y, P, r, GRID, min_pos=1)
        assert ct.expected_cost(Y, P, t, r) == min(ct.expected_cost(Y, P, g, r) for g in GRID)


def test_it_ngay_duong_giu_mac_dinh():
    t, ok = ct.choose_threshold(Y, P, 10, GRID, min_pos=5)
    assert (t, ok) == (0.5, False)


def test_nguong_ly_thuyet():
    # w = 1 (không bù lớp) ⇒ quy tắc Bayes 1/(1+R)
    assert ct.theory_threshold(1, 10) == pytest.approx(1 / 11)
    # w = R ⇒ đúng 0,5: trọng số lớp đã "mã hoá" sẵn tỉ lệ chi phí
    assert ct.theory_threshold(10, 10) == pytest.approx(0.5)


def test_mot_lan_chia_khong_dung_test():
    """Ngưỡng chọn trên valid không đổi dù nhãn/xác suất test bị xáo trộn tuỳ ý."""
    rng = np.random.default_rng(0)
    y_va = rng.random(500) < 0.05
    p_va = np.clip(y_va * 0.4 + rng.random(500) * 0.6, 0, 1)
    t0, _ = ct.choose_threshold(y_va, p_va, 10)
    for _ in range(3):
        y_te, p_te = rng.random(300) < 0.5, rng.random(300)
        ct.event_row(y_te, p_te >= t0, 10)      # áp lên test …
        assert ct.choose_threshold(y_va, p_va, 10)[0] == t0   # … không ảnh hưởng lựa chọn


def test_bang_walk_forward_chi_gom_nam_truoc():
    years = np.repeat([2010, 2011, 2012, 2013], 4)
    dates = np.array([np.datetime64(date(y, 12, d)) for y in (2010, 2011, 2012, 2013)
                      for d in (1, 27, 28, 30)])
    m = ct.pool_mask(years, dates, 2013, date(2012, 12, 28))
    assert not m[years == 2013].any()                    # năm test không bao giờ vào bể
    assert m[years < 2012].all()
    # 30/12/2012 nằm trong gap (nhãn t+3 = 02/01/2013) ⇒ loại
    assert list(m[years == 2012]) == [True, True, True, False]


def test_walk_forward_khong_nhin_nam_test():
    """evaluate_wf: đổi xác suất năm test không đổi ngưỡng chọn cho năm đó."""
    pl = pytest.importorskip("polars")
    rng = np.random.default_rng(1)
    parts = []
    for yr in range(2008, 2014):
        d = np.arange(np.datetime64(f"{yr}-01-01"), np.datetime64(f"{yr + 1}-01-01"))
        y = rng.random(len(d)) < 0.04
        p = np.clip(y * 0.5 + rng.random(len(d)) * 0.5, 0, 1)
        parts.append(pl.DataFrame({"bo_dac_trung": "R2", "level": 1, "horizon": 1, "year": yr,
                                   "date": d, "y": y, "p": p, "q0": p * 1000,
                                   "thr_q": 800.0, "w": 25.0}))
    oof = pl.concat(parts)

    def chosen(o):
        r = [x for x in ct.evaluate_wf(o, years=(2013,)) if x["phuong_phap"] == "chi_phi"]
        return {x["ty_le"]: x["nguong_p"] for x in r}

    base = chosen(oof)
    noisy = oof.with_columns(pl.when(pl.col("year") == 2013).then(1 - pl.col("p"))
                             .otherwise(pl.col("p")).alias("p"))
    assert chosen(noisy) == base
    # và bể chỉ gồm 2008–2012
    r = [x for x in ct.evaluate_wf(oof, years=(2013,)) if x["phuong_phap"] == "chi_phi"][0]
    n_pool = oof.filter((pl.col("year") < 2013) & (pl.col("date") <= date(2012, 12, 28))).height
    assert r["n_pool"] == n_pool
