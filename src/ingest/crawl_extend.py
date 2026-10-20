"""Mở rộng dữ liệu cho Report 3 — dùng lại toàn bộ hạ tầng của `crawl_all`.

Ba pha mới, dùng chung hạ tầng của `crawl_all`:

* **rain_daily_ext** — mưa ERA5 1997–2009. Lưu lượng có từ 1997 nhưng mưa chỉ
  từ 2010, nên 13 năm lưu lượng đang bị bỏ phí. Ghép xong: 29 năm thay vì 16,7.
  Cùng biến, cùng tham số API với `rain_daily` ⇒ cùng schema, đọc chung một glob.
* **soil_daily** — độ ẩm đất ba tầng (0–7, 7–28, 28–100 cm) và bốc thoát hơi
  tiềm năng ET₀, 1997–2026. Open-Meteo lấy độ ẩm đất từ ERA5-Land (0,1°, khớp
  lưới mưa). Đây là đo trực tiếp thứ mà chỉ số ẩm nền API chỉ ước lượng.
  Lấy lưới 0,2° (16 điểm) thay vì 0,1°: độ ẩm đất biến đổi chậm theo không gian,
  còn chuỗi 30 năm × 4 biến đốt quota gấp đôi chuỗi mưa — lưới dày bị chặn 429.
* **met_daily** — khí áp mực biển và gió tại 3 điểm, 1997–2026. Mưa lớn ở Huế
  thường do **không khí lạnh tràn về gặp nhiễu động gió đông**: khí áp phía bắc
  (Hà Nội) tăng vọt so với Huế, gió chuyển hướng đông bắc. Ba điểm đủ để đo
  chênh áp — trường khí áp biến đổi chậm, không cần lưới dày.

Ghi vào thư mục riêng, không đụng file cũ ⇒ số liệu Report 2 giữ nguyên.

    python -m src.ingest.crawl_extend               # cả ba pha
    python -m src.ingest.crawl_extend --dry-run
"""

from __future__ import annotations

from src import config as cfg
from src.ingest import crawl_all as ca

EXT_END = "2009-12-31"   # nối liền với RAIN_DATE_START = 2010-01-01
MET_DAILY_VARS = ("pressure_msl_mean,wind_direction_10m_dominant,wind_speed_10m_mean,"
                  "relative_humidity_2m_mean,cloud_cover_mean")
MET_POINTS = {
    "hue": (16.4, 107.5),        # giữa lưu vực
    "north": (21.0, 105.8),      # Hà Nội — nơi khối không khí lạnh tới trước
    "sea": (16.5, 109.5),        # ngoài khơi — nhiễu động gió đông, bão tiến vào
}
SOIL_STEP = 0.2
SOIL_DAILY_VARS = ("soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean,"
                   "soil_moisture_28_to_100cm_mean,et0_fao_evapotranspiration")


def tasks_rain_daily_ext() -> list[dict]:
    out = []
    for la, lo in ca._grid(ca.RAIN_BOX, ca.RAIN_STEP):
        out.append({
            "kind": "rain_daily_ext", "lat": la, "lon": lo,
            "dest": ca.RAW / "rain_daily_ext" / f"rd_{la}_{lo}.parquet",
            "url": cfg.ARCHIVE_API,
            "params": {"latitude": la, "longitude": lo, "daily": ca.RAIN_DAILY_VARS,
                       "start_date": cfg.RAIN_EXT_START, "end_date": EXT_END,
                       "timezone": cfg.TIMEZONE},
            "block": "daily",
        })
    return out


def tasks_soil_daily() -> list[dict]:
    out = []
    for la, lo in ca._grid(ca.RAIN_BOX, SOIL_STEP):
        out.append({
            "kind": "soil_daily", "lat": la, "lon": lo,
            "dest": ca.RAW / "soil_daily" / f"sd_{la}_{lo}.parquet",
            "url": cfg.ARCHIVE_API,
            "params": {"latitude": la, "longitude": lo, "daily": SOIL_DAILY_VARS,
                       "start_date": cfg.RAIN_EXT_START, "end_date": cfg.DATE_END,
                       "timezone": cfg.TIMEZONE},
            "block": "daily",
        })
    return out


def tasks_met_daily() -> list[dict]:
    return [{
        "kind": "met_daily", "lat": la, "lon": lo,
        "dest": ca.RAW / "met_daily" / f"md_{name}.parquet",
        "url": cfg.ARCHIVE_API,
        "params": {"latitude": la, "longitude": lo, "daily": MET_DAILY_VARS,
                   "start_date": cfg.RAIN_EXT_START, "end_date": cfg.DATE_END,
                   "timezone": cfg.TIMEZONE},
        "block": "daily",
    } for name, (la, lo) in MET_POINTS.items()]


ca.PHASES.update({"rain_daily_ext": tasks_rain_daily_ext,
                  "soil_daily": tasks_soil_daily,
                  "met_daily": tasks_met_daily})
# met_daily trước: chỉ 3 task, và là dữ liệu duy nhất chưa có nguồn thay thế
ca.DEFAULT_PHASES[:] = ["met_daily", "rain_daily_ext", "soil_daily"]


if __name__ == "__main__":
    with ca.SingleInstance():
        ca.main()
