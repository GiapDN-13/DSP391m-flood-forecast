"""Walk-forward thử giảm cắt ngọn (src/eval/wf_peak.py) và job dự báo trực tuyến."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import polars as pl
import pytest

from src.eval import wf_peak


def test_trong_so_dinh():
    y = np.array([100.0, 800.0, 1600.0])
    assert wf_peak.peak_weights(y, 800.0, 0.0) is None
    np.testing.assert_allclose(wf_peak.peak_weights(y, 800.0, 3.0), [1.0, 1.0, 4.0])


def test_isotonic_khong_ngoai_suy_va_giu_dong_thap():
    cal_p = np.array([10.0, 100.0, 500.0, 1000.0])
    cal_y = np.array([12.0, 120.0, 800.0, 2000.0])
    p = np.array([5.0, 50.0, 3000.0])
    full = wf_peak.isotonic_correct(cal_p, cal_y, p)
    assert full[-1] == pytest.approx(2000.0)          # kẹp ở biên, không ngoại suy
    hi = wf_peak.isotonic_correct(cal_p, cal_y, p, floor=400.0)
    assert hi[0] == 5.0 and hi[1] == 50.0               # dưới ngưỡng giữ nguyên


def _ens(years):
    rows = []
    for y in years:
        for h in (1, 2, 3):
            for k in range(5):
                rows.append({"config": "E", "fold": y, "horizon": h, "date": date(y, 10, k + 1),
                             "yhat": 100.0 + k, "y": 120.0 + 2 * k, "q0": 100.0, "flood": True,
                             "thr1": 150.0})
    return pl.DataFrame(rows)


def test_hieu_chinh_chi_dung_fold_truoc(monkeypatch):
    """Fold Y chỉ được hiệu chỉnh bằng dự báo của fold < Y."""
    seen = []

    def spy(cal_p, cal_y, p, floor=None):
        seen.append(len(cal_p))
        return p
    monkeypatch.setattr(wf_peak, "isotonic_correct", spy)
    monkeypatch.setattr(wf_peak, "YEARS", (2013, 2014))
    ens = _ens([2011, 2012, 2013, 2014])
    wf_peak.add_post(ens)
    # 2013: 2 fold trước × 5 ngày; 2014: 3 fold × 5 — mỗi horizon, 2 biến thể
    assert sorted(set(seen)) == [10, 15]


def test_build_jobs_E_co_fold_hieu_chinh():
    jobs = wf_peak.build_jobs(("E", "E w3"), (42,))
    e_years = {j["year"] for j in jobs if j["config"] == "E"}
    w_years = {j["year"] for j in jobs if j["config"] == "E w3"}
    assert min(e_years) == min(wf_peak.CAL_YEARS) and w_years == set(wf_peak.YEARS)


def test_cot_mo_hinh_trong_nhat_ky(monkeypatch):
    from src.models import predict_daily as pdl
    from src.models import predict_live as pli

    monkeypatch.setattr(pli, "models_ready", lambda: True)
    monkeypatch.setattr(pli, "predict", lambda t: {1: 900.0, 2: 500.0, 3: 2000.0,
                                                   "info": {"storm_ok": True, "missing": []}})
    out = pd.DataFrame({"point": ["huong_kim_long"] * 4 + ["khac"],
                        "horizon_days": [0, 1, 2, 3, 1],
                        "q_release_upstream": [None, 1000.0, None, None, None]})
    res = pdl.add_model_columns(out, date(2026, 11, 2))
    assert np.isnan(res.loc[0, "lgbm_q"]) and np.isnan(res.loc[4, "lgbm_q"])
    assert res.loc[1, "lgbm_q"] == 900.0
    assert res.loc[1, "lgbm_san_ho"] >= 1000.0          # sàn lệnh xả hồ chỉ nâng lên
    assert res.loc[1, "alert_lgbm"] == "nguy_co_1"
    assert res.loc[3, "alert_lgbm"] == "nguy_co_3"
    assert res.loc[2, "alert_lgbm"] == "binh_thuong"


def test_mo_hinh_loi_van_ghi_glofas(monkeypatch):
    from src.models import predict_daily as pdl
    from src.models import predict_live as pli

    def boom(t):
        raise RuntimeError("API sập")
    monkeypatch.setattr(pli, "models_ready", lambda: True)
    monkeypatch.setattr(pli, "predict", boom)
    out = pd.DataFrame({"point": ["huong_kim_long"], "horizon_days": [1]})
    assert list(pdl.add_model_columns(out, date(2026, 11, 2)).columns) == ["point", "horizon_days"]
