"""Hồ chứa: luật nâng sàn, chọn đúng hồ thượng nguồn, feature mở rộng không rò rỉ."""

from datetime import date

import polars as pl
import pytest

from src.features import reservoirs
from src.features.build_panel import ext_features


def test_san_xa_ho_chi_nang_khong_ha():
    assert reservoirs.release_floor(500.0, 900.0) == 900.0
    assert reservoirs.release_floor(1200.0, 900.0) == 1200.0
    assert reservoirs.release_floor(500.0, None) == 500.0
    assert reservoirs.release_floor(500.0, float("nan")) == 500.0


def test_chi_cong_ho_thuong_nguon_song_huong(tmp_path):
    """Hương Điền và A Lưới đổ về sông Bồ — không được cộng vào xả thượng nguồn."""
    f = tmp_path / "rel.csv"
    f.write_text(
        "date,time,reservoir,q_in_m3s,q_out_m3s,water_level_m,source_url,publisher,accessed,quote\n"
        "2025-10-27,08:00,Tả Trạch,,500,,u,p,a,q\n"
        "2025-10-27,14:00,Tả Trạch,,700,,u,p,a,q\n"
        "2025-10-27,08:00,Bình Điền,,300,,u,p,a,q\n"
        "2025-10-27,08:00,Hương Điền,,1000,,u,p,a,q\n"
        "2025-10-28,08:00,Bình Điền,,200,,u,p,a,q\n",
        encoding="utf-8")
    up = reservoirs.upstream_daily(reservoirs.load_releases(f))
    d27 = up.filter(pl.col("date") == date(2025, 10, 27)).row(0, named=True)
    assert d27["q_release_upstream"] == 1000.0      # max Tả Trạch 700 + Bình Điền 300
    assert d27["q_release_upstream_min"] == 800.0   # min Tả Trạch 500 + Bình Điền 300
    assert d27["n_upstream"] == 2
    d28 = up.filter(pl.col("date") == date(2025, 10, 28)).row(0, named=True)
    assert d28["n_upstream"] == 1                    # chỉ là cận dưới


def test_lenh_xa_theo_khoang_ngay(tmp_path):
    f = tmp_path / "orders.csv"
    f.write_text("date_from,date_to,reservoir,q_out_m3s,source_url\n"
                 "2025-10-26,2025-10-28,Tả Trạch,600,u\n"
                 "2025-10-27,2025-10-27,Bình Điền,400,u\n"
                 "2025-10-27,2025-10-27,Hương Điền,900,u\n", encoding="utf-8")
    assert reservoirs.active_orders(date(2025, 10, 27), f) == 1000.0
    assert reservoirs.active_orders(date(2025, 10, 28), f) == 600.0
    assert reservoirs.active_orders(date(2025, 10, 30), f) is None


def test_feature_ho_chua_khong_nhin_tuong_lai():
    """Đổi mưa của ngày t+1 thì mọi feature mở rộng tại ngày t phải giữ nguyên."""
    n = 60
    d = pl.DataFrame({
        "date": pl.date_range(date(2020, 8, 1), date(2020, 9, 29), "1d", eager=True),
        "rain_basin": [float(i % 7) for i in range(n)],
    })
    a = d.with_columns(ext_features())
    b = d.with_columns(
        pl.when(pl.int_range(pl.len()) == 41).then(9999.0)
          .otherwise(pl.col("rain_basin")).alias("rain_basin")
    ).with_columns(ext_features())
    for c in ("rain_basin_roll15", "rain_basin_roll30", "rain_season_cum"):
        assert a[c][40] == b[c][40], c
        assert a[c][41] != b[c][41], c


def test_mua_tich_luy_reset_ngay_1_thang_9():
    d = pl.DataFrame({
        "date": pl.date_range(date(2020, 8, 30), date(2020, 9, 2), "1d", eager=True),
        "rain_basin": [10.0, 10.0, 5.0, 5.0],
    }).with_columns(ext_features())
    assert d["rain_season_cum"].to_list() == pytest.approx([10.0, 20.0, 5.0, 10.0])
