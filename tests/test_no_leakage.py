"""Test chống rò rỉ dữ liệu tương lai — quan trọng nhất trong bộ test.

Rò rỉ dữ liệu là lỗi chí mạng của bài toán chuỗi thời gian: kết quả đẹp giả,
không báo lỗi, và chỉ lộ ra khi giảng viên hỏi. Xem docs/GAPS.md mục 9.

Các test này sẽ FAIL cho tới khi src/features/build_panel.py được viết ở W3 —
đó là chủ ý, để nhắc rằng chưa có gì bảo vệ.
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def toy_series() -> pd.DataFrame:
    """Chuỗi giả: discharge tăng đều 0, 1, 2, ... để dễ kiểm bằng mắt."""
    n = 50
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=n, freq="D"),
            "discharge": np.arange(n, dtype=float),
            "rain": np.arange(n, dtype=float) * 2,
        }
    )


def test_lag_khong_nhin_tuong_lai(toy_series):
    """q_lag1 tại ngày t phải bằng discharge tại ngày t-1, không phải t+1."""
    pytest.importorskip("src.features.build_panel")
    from src.features.build_panel import make_lags

    out = make_lags(toy_series, col="discharge", lags=[1, 3])
    assert out.loc[10, "discharge_lag1"] == toy_series.loc[9, "discharge"]
    assert out.loc[10, "discharge_lag3"] == toy_series.loc[7, "discharge"]
    assert pd.isna(out.loc[0, "discharge_lag1"])


def test_target_dung_horizon(toy_series):
    """target_h3 tại ngày t phải là discharge tại ngày t+3."""
    pytest.importorskip("src.features.build_panel")
    from src.features.build_panel import make_target

    out = make_target(toy_series, horizon=3)
    assert out.loc[10, "target_h3"] == toy_series.loc[13, "discharge"]
    assert pd.isna(out.loc[len(toy_series) - 1, "target_h3"])


def test_rolling_khong_can_giua(toy_series):
    """Rolling mean phải là trailing, không được centered."""
    pytest.importorskip("src.features.build_panel")
    from src.features.build_panel import make_rolling

    out = make_rolling(toy_series, col="rain", windows=[3])
    # trailing mean tại t=10 dùng ngày 8, 9, 10
    expected = toy_series.loc[8:10, "rain"].mean()
    assert out.loc[10, "rain_roll3"] == pytest.approx(expected)


def test_split_khong_chong_lan():
    """Train/valid/test phải tách rời và đúng thứ tự thời gian."""
    from src.config import GLOFAS_REGIME_BREAK, TRAIN_END, VALID_END

    assert TRAIN_END < VALID_END < GLOFAS_REGIME_BREAK


def test_walk_forward_co_gap():
    """Phải có khoảng trống giữa cuối train và đầu test, ít nhất bằng horizon lớn nhất."""
    pytest.importorskip("src.eval.walk_forward")
    from src.eval.walk_forward import make_folds

    from src.config import HORIZONS

    folds = make_folds(
        pd.date_range("2010-01-01", "2020-12-31", freq="D"), n_folds=3
    )
    for train_idx, test_idx in folds:
        gap_days = (test_idx.min() - train_idx.max()).days
        assert gap_days > max(HORIZONS), f"gap {gap_days} ngày là quá ngắn"
