"""Phần giải mã của src/ingest/gsmap_nrt.py — không cần mạng."""

import gzip
from datetime import date

import numpy as np

from src.ingest import gsmap_nrt as g


def test_khung_10x10_dung_tam_o():
    assert len(g.LI) == 10 and len(g.LJ) == 10
    assert round(g.LAT[g.LI[0]], 2) == 16.75 and round(g.LAT[g.LI[-1]], 2) == 15.85
    assert round(g.LON[g.LJ[0]], 2) == 107.05 and round(g.LON[g.LJ[-1]], 2) == 107.95


def test_decode_cat_dung_o_va_doi_gia_tri_thieu():
    a = np.zeros((g.NLAT, g.NLON), dtype="<f4")
    a[g.LI[0], g.LJ[0]] = 12.5          # góc tây-bắc khung
    a[g.LI[-1], g.LJ[-1]] = -999.9      # thiếu
    a[g.LI[0] - 1, g.LJ[0]] = 99.0      # ngay ngoài khung — không được lọt vào
    sub = g.decode(gzip.compress(a.tobytes()))
    assert sub.shape == (10, 10)
    assert sub[0, 0] == 12.5 and np.isnan(sub[-1, -1]) and np.nanmax(sub) == 12.5


def test_hour_frame_nhan_cuoi_gio():
    sub = np.zeros((10, 10), dtype=np.float32)
    df = g.hour_frame(date(2026, 10, 10), 0, sub)
    assert df.height == 100
    assert str(df["time_utc"][0]) == "2026-10-10 01:00:00"   # file 00 = giờ 00–01 UTC
    assert str(df["time"][0]) == "2026-10-10 08:00:00"       # giờ VN
    assert df["lat"][0] == 16.75 and df["lon"][0] == 107.05
