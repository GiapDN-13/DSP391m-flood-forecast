"""Test cho khâu làm sạch dữ liệu (Polars).

Lỗi ETL là loại lỗi âm thầm nhất: sai timezone 1 tiếng hoặc nhầm mm/h với mm/day
sẽ không báo lỗi gì cả, chỉ làm kết quả sai lặng lẽ. Xem docs/GAPS.md mục 9.
"""

from datetime import datetime

import polars as pl
import pytest

from src.etl.clean import (
    hourly_to_daily,
    to_local_time,
    validate_daily_index,
    validate_discharge,
)


def test_doi_timezone_utc_sang_ict():
    """00:00 UTC phải thành 07:00 giờ Việt Nam."""
    utc = pl.Series([datetime(2020, 10, 10, 0, 0)]).dt.replace_time_zone("UTC")
    assert to_local_time(utc).dt.hour()[0] == 7


def test_chuoi_khong_mui_gio_duoc_hieu_la_utc():
    naive = pl.Series([datetime(2020, 10, 10, 0, 0)])
    assert to_local_time(naive).dt.hour()[0] == 7


def test_gop_mua_gio_thanh_ngay():
    """Tổng 24 giá trị giờ phải bằng giá trị mưa ngày."""
    hourly = pl.DataFrame({
        "time": pl.datetime_range(datetime(2020, 10, 10), datetime(2020, 10, 11, 23),
                                  "1h", eager=True),
        "rain": [1.0] * 48,
    })
    daily = hourly_to_daily(hourly, col="rain", how="sum")
    assert daily.height == 2
    assert daily["rain"].to_list() == [24.0, 24.0]


def test_khong_co_discharge_am():
    bad = pl.DataFrame({"discharge": [10.0, -5.0, 20.0]})
    with pytest.raises(ValueError, match="âm"):
        validate_discharge(bad)


def test_khong_co_ngay_trung_lap():
    dup = pl.DataFrame({"date": [datetime(2020, 1, 1), datetime(2020, 1, 1),
                                 datetime(2020, 1, 2)]})
    with pytest.raises(ValueError, match="trùng"):
        validate_daily_index(dup)


def test_khong_thieu_ngay_giua_chuoi():
    """Chuỗi ngày phải liên tục, thiếu ngày phải được phát hiện chứ không im lặng."""
    missing = pl.DataFrame({"date": [datetime(2020, 1, 1), datetime(2020, 1, 3)]})
    with pytest.raises(ValueError, match="thiếu"):
        validate_daily_index(missing, require_continuous=True)
