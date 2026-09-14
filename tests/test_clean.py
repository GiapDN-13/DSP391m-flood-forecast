"""Test cho khâu làm sạch dữ liệu — D viết ở W2.

Lỗi ETL là loại lỗi âm thầm nhất: sai timezone 1 tiếng hoặc nhầm mm/h với mm/day
sẽ không báo lỗi gì cả, chỉ làm kết quả sai lặng lẽ. Xem docs/GAPS.md mục 9.
"""

import numpy as np
import pandas as pd
import pytest


def test_doi_timezone_utc_sang_ict():
    """00:00 UTC phải thành 07:00 giờ Việt Nam."""
    pytest.importorskip("src.etl.clean")
    from src.etl.clean import to_local_time

    utc = pd.Series(pd.to_datetime(["2020-10-10 00:00:00"], utc=True))
    local = to_local_time(utc)
    assert local.dt.hour.iloc[0] == 7


def test_gop_mua_gio_thanh_ngay():
    """Tổng 24 giá trị giờ phải bằng giá trị mưa ngày."""
    pytest.importorskip("src.etl.clean")
    from src.etl.clean import hourly_to_daily

    hourly = pd.DataFrame(
        {
            "time": pd.date_range("2020-10-10 00:00", periods=48, freq="h"),
            "rain": np.ones(48),
        }
    )
    daily = hourly_to_daily(hourly, col="rain", how="sum")
    assert len(daily) == 2
    assert daily["rain"].tolist() == [24.0, 24.0]


def test_khong_co_discharge_am():
    pytest.importorskip("src.etl.clean")
    from src.etl.clean import validate_discharge

    bad = pd.DataFrame({"discharge": [10.0, -5.0, 20.0]})
    with pytest.raises(ValueError, match="âm"):
        validate_discharge(bad)


def test_khong_co_ngay_trung_lap():
    pytest.importorskip("src.etl.clean")
    from src.etl.clean import validate_daily_index

    dup = pd.DataFrame(
        {"date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02"])}
    )
    with pytest.raises(ValueError, match="trùng"):
        validate_daily_index(dup)


def test_khong_thieu_ngay_giua_chuoi():
    """Chuỗi ngày phải liên tục, thiếu ngày phải được phát hiện chứ không im lặng."""
    pytest.importorskip("src.etl.clean")
    from src.etl.clean import validate_daily_index

    missing = pd.DataFrame(
        {"date": pd.to_datetime(["2020-01-01", "2020-01-03"])}
    )
    with pytest.raises(ValueError, match="thiếu"):
        validate_daily_index(missing, require_continuous=True)
