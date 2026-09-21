"""Độ phủ dữ liệu thật, không phải số dòng.

Vì sao có file này: `FR-D1` từng được nghiệm thu bằng "số ngày khớp khoảng yêu
cầu" — 15 584 dòng cho 1984–2026. Nhưng 1984–1996 rỗng 100 % ở cả 83 ô lưới,
tức 30,5 % chuỗi là null. Panel bắt đầu 2010 nên mọi kiểm tra trên panel báo
sạch. Đếm dòng không phải đếm dữ liệu. Xem docs/FINDINGS_EVENTS.md §3.
"""

import pandas as pd
import pytest

from src import config as cfg

RAW = cfg.ROOT / "data" / "raw" / "discharge"


def _series():
    lat, lon = cfg.RIVER_POINTS["huong_kim_long"]
    f = RAW / f"q_{lat:g}_{lon:g}.parquet"
    if not f.exists():
        pytest.skip("chưa có dữ liệu thô — chạy scripts/restore_data.py")
    d = pd.read_parquet(f)
    tcol = "time" if "time" in d.columns else "date"
    return pd.Series(d["river_discharge"].to_numpy(),
                     index=pd.to_datetime(d[tcol]).dt.tz_localize(None))


def test_config_ghi_dung_ngay_bat_dau_thuc_te():
    """Hằng số phải là 1997, không phải 1984 — tránh viết sai vào báo cáo."""
    assert cfg.DISCHARGE_DATA_START == "1997-01-01"
    assert cfg.DATE_START == "1984-01-01"      # khoảng yêu cầu, giữ nguyên


def test_du_lieu_luu_luong_bat_dau_1997_khong_phai_1984():
    s = _series().dropna()
    assert str(s.index.min().date()) == "1997-01-01"
    assert s.index.min().year != 1984


def test_so_ngay_co_du_lieu_du_dung():
    """FR-D1 nghiệm thu bằng số ngày KHÔNG RỖNG, không phải số dòng."""
    s = _series()
    assert len(s.dropna()) >= 10_000, f"chỉ {len(s.dropna())} ngày có dữ liệu"


def test_khong_co_lo_trong_sau_1997():
    """Sau 1997 phải liền mạch — lỗ trống mới xuất hiện là dấu hiệu crawl hỏng."""
    s = _series()
    sau = s.loc["1997-01-01":]
    assert sau.isna().sum() == 0, f"{sau.isna().sum()} ngày rỗng sau 1997"
