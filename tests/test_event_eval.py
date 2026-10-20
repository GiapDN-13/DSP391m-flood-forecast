"""Test cho đánh giá theo đợt lũ (src/eval/event_eval.py) — không cần dữ liệu thật.

Khoá: quy tắc gộp đợt (≤ 2 ngày dưới ngưỡng thì vẫn cùng đợt), đỉnh đợt, định
nghĩa "bắt được" (≥ 1 ngày TRONG đợt có dự báo ≥ ngưỡng; cửa sổ ±1 chỉ cho
``caught_win``), thời gian báo trước tính theo ngày PHÁT, và đếm đợt báo nhầm.
"""

from datetime import date, timedelta

import numpy as np
import pytest

from src.eval import event_eval as ee

D0 = date(2020, 10, 1)


def d(i: int) -> date:
    return D0 + timedelta(days=i)


def series(vals: list[float]) -> tuple[list[date], np.ndarray]:
    return [d(i) for i in range(len(vals))], np.array(vals, dtype=float)


# ---------------------------------------------------------------- gộp đợt

def test_gop_ngay_lien_nhau_va_cach_toi_da_hai_ngay():
    # 1,2 liền nhau; 2→5 có 2 ngày dưới ngưỡng (3,4) ⇒ cùng đợt; 5→9 có 3 ngày ⇒ tách
    assert ee.clusters([d(1), d(2), d(5), d(9)]) == [(d(1), d(5)), (d(9), d(9))]


@pytest.mark.parametrize("gap,expected", [(0, 3), (1, 2), (2, 1)])
def test_max_gap_dieu_khien_so_dot(gap, expected):
    days = [d(0), d(2), d(5)]                 # khoảng trống 1 ngày và 2 ngày
    assert len(ee.clusters(days, max_gap=gap)) == expected


def test_find_events_dinh_va_so_ngay():
    thr = 806.0
    dates, q = series([100, 900, 1200, 700, 700, 810, 300, 300, 300, 806, np.nan, 50])
    evs = ee.find_events(dates, q, thr)
    assert [(e["start"], e["end"]) for e in evs] == [(d(1), d(5)), (d(9), d(9))]
    assert evs[0]["peak_date"] == d(2) and evs[0]["peak_q"] == 1200
    assert evs[0]["n_days"] == 5 and evs[0]["n_above"] == 3
    assert evs[1]["peak_q"] == 806            # đúng bằng ngưỡng vẫn tính là vượt


def test_khong_co_ngay_vuot_thi_khong_co_dot():
    dates, q = series([10, 20, np.nan, 805.9])
    assert ee.find_events(dates, q, 806.0) == []


# ---------------------------------------------------------------- bắt được

EV = {"start": d(10), "end": d(12), "peak_date": d(11), "peak_q": 1000.0}


def test_bat_duoc_khi_mot_ngay_trong_dot_vuot_nguong():
    r = ee.score_event(EV, {d(12): 806.0}, 806.0, h=1)
    assert r["caught"] and r["caught_win"]


def test_vuot_nguong_ngoai_dot_khong_tinh_la_bat_duoc():
    r = ee.score_event(EV, {d(9): 900.0, d(10): 500.0}, 806.0, h=1)
    assert not r["caught"]                    # chỉ vượt ở ngày trước đợt
    assert r["caught_win"]                    # nhưng nằm trong cửa sổ ±1 (FR-V5)


def test_du_bao_thap_hoac_thieu_khong_bat_duoc():
    r = ee.score_event(EV, {d(10): 300.0, d(11): np.nan}, 806.0, h=2)
    assert not r["caught"] and not r["caught_win"]
    assert np.isnan(r["lead_onset"])
    assert r["peak_ratio"] == pytest.approx(0.3)


def test_ty_so_dinh_lech_thoi_diem_va_bao_truoc():
    fc = {d(9): 850.0, d(10): 700.0, d(12): 900.0}
    r = ee.score_event(EV, fc, 806.0, h=2)
    assert r["peak_ratio"] == pytest.approx(0.9)
    assert r["timing_err"] == 1               # đỉnh dự báo ngày 12, thật ngày 11
    # cảnh báo đầu tiên cho ngày 9 (trong cửa sổ ±1), phát ngày 9 − 2 = ngày 7
    assert r["warn_issue_date"] == d(7)
    assert r["lead_onset"] == 3 and r["lead_peak"] == 4


def test_persistence_khong_bao_giu_bao_truoc_duoc():
    """Persistence Q̂(v) = Q(v − h): đợt 1 ngày không bắt được, đợt dài bắt được
    nhưng thời gian báo trước tới lúc bắt đầu luôn ≤ 0."""
    dates, q = series([100] * 10 + [900, 950, 1000, 400] + [100] * 6)
    obs = dict(zip(dates, q))
    ev = ee.find_events(dates, q, 806.0)[0]
    for h in (1, 2, 3):
        fc = {v + timedelta(days=h): obs[v] for v in dates}
        r = ee.score_event(ev, fc, 806.0, h)
        assert r["caught"] == (h < 3)         # đợt 3 ngày: trễ 3 ngày thì ra ngoài đợt
        assert np.isnan(r["lead_onset"]) or r["lead_onset"] <= 0
        assert r["peak_ratio"] == pytest.approx(1.0) and r["timing_err"] == h
    one = {"start": d(5), "end": d(5), "peak_date": d(5), "peak_q": 900.0}
    assert not ee.score_event(one, {d(6): 900.0}, 806.0, h=1)["caught"]


def test_khong_muon_dinh_cua_dot_truoc():
    """Persistence h=3 cho ngày 13 = Q(ngày 10), ngày 10 thuộc đợt trước ⇒ không tính."""
    ev = {"start": d(14), "end": d(15), "peak_date": d(14), "peak_q": 900.0}
    fc = {d(13): 2000.0, d(14): 500.0, d(17): 900.0}
    r = ee.score_event(ev, fc, 806.0, h=3, prev_end=d(10))
    assert r["peak_ratio"] == pytest.approx(1.0) and r["timing_err"] == 3
    assert np.isnan(r["lead_onset"])          # cảnh báo duy nhất (ngày 17) ngoài cửa sổ ±1
    r0 = ee.score_event(ev, fc, 806.0, h=3)   # không khai báo đợt trước ⇒ bị lấn
    assert r0["peak_ratio"] == pytest.approx(2000 / 900)


def test_khong_tinh_ngay_cua_dot_sau():
    ev = {"start": d(10), "end": d(10), "peak_date": d(10), "peak_q": 1000.0}
    r = ee.score_event(ev, {d(10): 600.0, d(12): 3000.0}, 806.0, h=3, next_start=d(12))
    assert r["peak_ratio"] == pytest.approx(0.6) and r["timing_err"] == 0


# ---------------------------------------------------------------- báo nhầm

def test_dem_dot_bao_nham():
    evs = [{"start": d(10), "end": d(12)}]
    fc = {d(11): 900.0,                       # trùng đợt thật
          d(13): 900.0,                       # chạm cửa sổ +1 ⇒ không tính nhầm
          d(20): 900.0, d(22): 900.0,         # một cụm nhầm (cách 1 ngày ⇒ gộp)
          d(30): 900.0}                       # cụm nhầm thứ hai
    assert ee.false_alarm_events(fc, 806.0, evs, d(0), d(40)) == 2
    assert ee.false_alarm_events(fc, 806.0, evs, d(0), d(25)) == 1   # cắt theo [lo, hi]
