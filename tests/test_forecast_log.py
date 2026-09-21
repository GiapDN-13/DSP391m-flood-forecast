"""Nhật ký dự báo hằng ngày phải đúng ngày và không tự xoá lịch sử.

Vì sao có file test này: ngày 19–21/09/2026 job chạy xanh 6 lần liên tiếp
nhưng mất một bản dự báo. Nguyên nhân là `date.today()` trên runner UTC cộng
với việc job nổ quanh nửa đêm UTC. Xanh không có nghĩa là đúng — nên phải
có test khoá lại hành vi.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from src import config as cfg
from src.models import predict_daily as pd_job


def test_timezone_la_gio_viet_nam():
    """Lệch UTC phải là +7 giờ, bất kể tên vùng đặt là gì."""
    off = datetime(2026, 9, 20, 12, tzinfo=ZoneInfo(cfg.TIMEZONE)).utcoffset()
    assert off.total_seconds() == 7 * 3600


def test_ict_today_khac_ngay_utc_luc_nua_dem():
    """Mốc gãy thật: 23:58 UTC ngày 19/09 là 06:58 ICT ngày 20/09."""
    moment_utc = datetime(2026, 9, 19, 23, 58, tzinfo=ZoneInfo("UTC"))
    ict = moment_utc.astimezone(ZoneInfo(cfg.TIMEZONE)).date()
    assert ict.isoformat() == "2026-09-20"
    assert moment_utc.date().isoformat() == "2026-09-19"  # cái bẫy cũ


def test_ict_today_tra_ve_ngay_ict_hien_tai():
    assert pd_job.ict_today() == datetime.now(ZoneInfo(cfg.TIMEZONE)).date()


def test_khong_ghi_de_ban_du_bao_da_co(tmp_path, monkeypatch):
    """Chạy lại trong cùng ngày phải sinh file mới, giữ nguyên bản gốc."""
    monkeypatch.setattr(pd_job, "LOG_DIR", tmp_path)
    monkeypatch.setattr(pd_job, "SUMMARY", tmp_path / "_latest.csv")
    monkeypatch.setattr(pd_job.cfg, "RIVER_POINTS", {"p": (16.45, 107.50)})

    import pandas as pd
    fake = pd.DataFrame({"target_date": pd.to_datetime(["2026-09-20"]),
                         "glofas_discharge": [100.0]})
    monkeypatch.setattr(pd_job, "fetch_discharge_forecast", lambda la, lo: fake.copy())
    monkeypatch.setattr(pd_job, "fetch_rain_forecast", lambda la, lo: pd.DataFrame(
        {"target_date": pd.to_datetime(["2026-09-20"]),
         "rain_forecast": [1.0], "temp_forecast": [25.0]}))

    day = pd_job.ict_today().isoformat()
    (tmp_path / f"{day}.csv").write_text("BAN GOC", encoding="utf-8")
    assert pd_job.main() == 0
    assert (tmp_path / f"{day}.csv").read_text(encoding="utf-8") == "BAN GOC"
    assert any(p.name.startswith(f"{day}_chu-ky-muon-") for p in tmp_path.iterdir())
