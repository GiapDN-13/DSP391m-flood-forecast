"""Phần xử lý của src/ingest/gee_precip.py — không gọi Earth Engine."""

from datetime import date

from src.ingest import gee_precip as g

ROWS = [
    ["id", "longitude", "latitude", "time", "precipitation"],
    ["20201010000000", 107.05048967687217, 15.850072502367343, 1602288000000, 18.35],
    ["20201010003000", 107.05048967687217, 15.850072502367343, 1602289800000, None],
]


def test_rows_to_frame_doi_gio_va_toa_do():
    df = g.rows_to_frame(ROWS, {"precipitation": "precip_mm_hr"}, step_min=30)
    assert df.columns == ["time_utc", "time", "lat", "lon", "precip_mm_hr"]
    assert df["lat"][0] == 15.85 and df["lon"][0] == 107.05
    # ảnh 00:00–00:30 UTC → nhãn CUỐI khoảng, cùng quy ước ERA5/PERSIANN-CCS
    assert str(df["time_utc"][0]) == "2020-10-10 00:30:00"
    assert str(df["time"][0]) == "2020-10-10 07:30:00"  # giờ VN = UTC+7
    assert df["precip_mm_hr"][1] is None  # giữ ô thiếu, không thay bằng 0


def test_month_range_qua_nam():
    assert g.month_range("1998-11", "1999-02") == ["1998-11", "1998-12", "1999-01", "1999-02"]
    assert g.month_bounds("2020-12") == ("2020-12-01", "2021-01-01")


def test_needs_fetch(tmp_path):
    f = tmp_path / "x.parquet"
    assert g.needs_fetch(f, "2020-10", date(2026, 10, 20))
    f.write_bytes(b"x")
    assert not g.needs_fetch(f, "2020-10", date(2026, 10, 20))
    assert g.needs_fetch(f, "2026-09", date(2026, 10, 20))  # tháng gần đây: tải lại
