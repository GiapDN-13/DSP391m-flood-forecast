"""Test chống rò rỉ dữ liệu tương lai — quan trọng nhất trong bộ test.

Rò rỉ dữ liệu là lỗi chí mạng của bài toán chuỗi thời gian: kết quả đẹp giả,
không báo lỗi, và chỉ lộ ra khi giảng viên hỏi. Xem docs/GAPS.md mục 9.
"""

from datetime import date

import polars as pl
import pytest

from src.features.build_panel import antecedent_index, make_lags, make_rolling, make_target


@pytest.fixture
def toy_series() -> pl.DataFrame:
    """Chuỗi giả: discharge tăng đều 0, 1, 2, ... để dễ kiểm bằng mắt."""
    n = 50
    return pl.DataFrame({
        "date": pl.date_range(date(2020, 1, 1), date(2020, 2, 19), "1d", eager=True),
        "discharge": [float(i) for i in range(n)],
        "rain": [float(i) * 2 for i in range(n)],
    })


def test_lag_khong_nhin_tuong_lai(toy_series):
    """q_lag1 tại ngày t phải bằng discharge tại ngày t-1, không phải t+1."""
    out = make_lags(toy_series, col="discharge", lags=[1, 3])
    assert out["discharge_lag1"][10] == toy_series["discharge"][9]
    assert out["discharge_lag3"][10] == toy_series["discharge"][7]
    assert out["discharge_lag1"][0] is None


def test_target_dung_horizon(toy_series):
    """target_h3 tại ngày t phải là discharge tại ngày t+3."""
    out = make_target(toy_series, horizon=3)
    assert out["target_h3"][10] == toy_series["discharge"][13]
    assert out["target_h3"][toy_series.height - 1] is None


def test_rolling_khong_can_giua(toy_series):
    """Rolling mean phải là trailing, không được centered."""
    out = make_rolling(toy_series, col="rain", windows=[3])
    # trailing mean tại t=10 dùng ngày 8, 9, 10
    expected = sum(toy_series["rain"][8:11]) / 3
    assert out["rain_roll3"][10] == pytest.approx(expected)


def test_api_khong_dung_mua_hom_nay(toy_series):
    """Chỉ số ẩm nền tại ngày t chỉ dùng mưa từ t−1 trở về trước."""
    a = toy_series.with_columns(antecedent_index("rain").alias("api"))
    # đổi mưa của CHÍNH ngày 10 thì API ngày 10 không được đổi
    b = toy_series.with_columns(
        pl.when(pl.int_range(pl.len()) == 10).then(9999.0).otherwise(pl.col("rain")).alias("rain")
    ).with_columns(antecedent_index("rain").alias("api"))
    assert a["api"][10] == b["api"][10]
    assert a["api"][11] != b["api"][11]


def test_split_khong_chong_lan():
    """Train/valid/test phải tách rời và đúng thứ tự thời gian."""
    from src.config import GLOFAS_REGIME_BREAK, TRAIN_END, VALID_END

    assert TRAIN_END < VALID_END < GLOFAS_REGIME_BREAK


def test_walk_forward_co_gap():
    """Phải có khoảng trống giữa cuối train và đầu test, ít nhất bằng horizon lớn nhất."""
    pytest.importorskip("src.eval.walk_forward")
    import pandas as pd  # phần đánh giá mô hình (không thuộc tầng dữ liệu)

    from src.config import HORIZONS
    from src.eval.walk_forward import make_folds

    folds = make_folds(
        pd.date_range("2010-01-01", "2020-12-31", freq="D"), n_folds=3
    )
    for train_idx, test_idx in folds:
        gap_days = (test_idx.min() - train_idx.max()).days
        assert gap_days > max(HORIZONS), f"gap {gap_days} ngày là quá ngắn"
