"""Job dự báo hằng ngày (FR-P4) — chạy trên GitHub Actions mỗi sáng.

Chạy được **ngay từ hôm nay**, kể cả khi chưa có mô hình:

* Luôn làm: lấy dự báo GloFAS 7 ngày + mưa dự báo cho các điểm đã chốt,
  ghi một dòng cho mỗi (ngày phát báo × điểm × horizon) vào `reports/forecast_log/`.
* Khi đã có mô hình trong `models/`: chạy thêm phần hiệu chỉnh và ghi cột dự báo
  của nhóm cạnh cột GloFAS thô.

Vì sao chạy sớm dù chưa có mô hình: mỗi ngày trôi qua là một bản dự báo thật
**không lấy lại được**. Bắt đầu ghi từ W1 thì tới W8 đã có ~8 tuần dữ liệu
dự báo–thực tế để đánh giá kịch bản B (`RESEARCH_DESIGN.md` §2), thay vì
phải dựa hoàn toàn vào kho lưu trữ.

    python -m src.models.predict_daily
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from src import config as cfg

MAX_TRIES = 6

LOG_DIR = cfg.ROOT / "reports" / "forecast_log"
SUMMARY = cfg.ROOT / "reports" / "forecast_log" / "_latest.csv"
MODELS = cfg.ROOT / "models"


def _get(url: str, params: dict) -> dict:
    """GET có retry luỹ thừa.

    Job chạy tự động mỗi sáng, một cú 429 thoáng qua không được phép làm
    hỏng cả lần chạy — chờ rồi thử lại.
    """
    delay = 5.0
    for attempt in range(1, MAX_TRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=90)
            if r.status_code == 429:
                raise requests.HTTPError("429 rate limit")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == MAX_TRIES:
                raise
            print(f"    thử lại sau {delay:.0f}s ({e}) [{attempt}/{MAX_TRIES}]",
                  flush=True)
            time.sleep(delay)
            delay = min(120.0, delay * 2)
    raise RuntimeError("không tới được đây")


def fetch_discharge_forecast(lat: float, lon: float) -> pd.DataFrame:
    d = _get(cfg.FLOOD_API, {
        "latitude": lat, "longitude": lon,
        "daily": "river_discharge", "forecast_days": 7,
    })["daily"]
    return pd.DataFrame({"target_date": pd.to_datetime(d["time"]),
                         "glofas_discharge": d["river_discharge"]})


def fetch_rain_forecast(lat: float, lon: float) -> pd.DataFrame:
    d = _get(cfg.FORECAST_API, {
        "latitude": lat, "longitude": lon,
        "daily": "precipitation_sum,temperature_2m_mean",
        "forecast_days": 7, "timezone": cfg.TIMEZONE,
    })["daily"]
    return pd.DataFrame({"target_date": pd.to_datetime(d["time"]),
                         "rain_forecast": d["precipitation_sum"],
                         "temp_forecast": d["temperature_2m_mean"]})


def fetch_sea_level(lat: float = 16.57, lon: float = 107.63) -> pd.DataFrame:
    """Mực nước biển tại cửa Thuận An — biến triều cho nhánh phân loại.

    Vì sao ghi từ bây giờ: kho lưu trữ của Marine API **chỉ có từ 2023-01-01**,
    nên không dùng làm feature huấn luyện được (train kết thúc 2022-06). Nhưng
    mực nước tại Kim Long phụ thuộc triều (`FINDINGS_REGIME.md` §6c), nên mỗi
    ngày ghi lại là một ngày tích luỹ cho phân tích về sau. Không lấy thì mất.
    """
    # API chỉ có biến này ở mức GIỜ, không có sẵn bản theo ngày — gộp lấy đỉnh
    # trong ngày, vì cái gây dềnh nước là đỉnh triều chứ không phải trung bình.
    d = _get("https://marine-api.open-meteo.com/v1/marine", {
        "latitude": lat, "longitude": lon, "hourly": "sea_level_height_msl",
        "forecast_days": 7, "timezone": cfg.TIMEZONE,
    })["hourly"]
    s = pd.Series(d["sea_level_height_msl"], index=pd.to_datetime(d["time"]))
    g = s.groupby(s.index.normalize()).max()
    return pd.DataFrame({"target_date": g.index, "sea_level_max": g.to_numpy()})


def alert_level(q: float) -> str:
    """Quy lưu lượng ra cấp báo động, nếu ngưỡng đã được chốt ở W3."""
    levels = getattr(cfg, "ALERT_LEVELS_Q", {}) or {}
    if not levels or pd.isna(q):
        return "chua_co_nguong"
    for name in ("BD3", "BD2", "BD1"):
        thr = levels.get(name)
        if thr is not None and q >= thr:
            return name
    return "duoi_BD1"


def ict_today():
    """Ngày theo giờ Việt Nam.

    Runner của GitHub Actions chạy theo UTC. Dùng `date.today()` ở đó là lấy
    ngày UTC, và vì job thực tế nổ quanh nửa đêm UTC (lịch 22:00 UTC nhưng
    GitHub trễ ~2 giờ), nhãn ngày trở thành xổ số: lần chạy 06:58 ICT ngày
    20/09/2026 tự nhận là 19/09 rồi ghi đè bản dự báo sáng 19/09, còn ngày
    20/09 thì trắng file. Cả 6 lần chạy vẫn báo xanh.

    Toàn bộ dự án quy ước giờ Việt Nam (FR-E1), nhật ký dự báo phải theo.
    """
    return datetime.now(ZoneInfo(cfg.TIMEZONE)).date()


def main() -> int:
    run_date = ict_today()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for name, (lat, lon) in cfg.RIVER_POINTS.items():
        try:
            q = fetch_discharge_forecast(lat, lon)
            rain = fetch_rain_forecast(lat, lon)
        except Exception as e:
            print(f"  ! {name}: không lấy được dự báo — {e}", flush=True)
            continue

        df = q.merge(rain, on="target_date", how="outer").sort_values("target_date")
        # Triều là biến phụ: hỏng thì vẫn ghi phần chính, không để mất cả ngày.
        try:
            df = df.merge(fetch_sea_level(), on="target_date", how="left")
        except Exception as e:
            print(f"  ! {name}: không lấy được mực nước biển — {e}", flush=True)
            df["sea_level_max"] = pd.NA
        df.insert(0, "run_date", run_date)
        df.insert(1, "point", name)
        df.insert(2, "lat", lat)
        df.insert(3, "lon", lon)
        df["horizon_days"] = (df["target_date"].dt.date - run_date).apply(lambda d: d.days)
        # API lưu lượng chạy theo ngày GMT còn mưa theo giờ Việt Nam, nên phép
        # gộp ngoài đôi khi sinh ra một dòng cho NGÀY HÔM QUA với horizon âm và
        # cột mưa rỗng. Dòng đó vô nghĩa với một bản dự báo — bỏ đi.
        # (Gặp thật trong bản phát 2026-09-22 của job theo lịch.)
        df = df[df["horizon_days"] >= 0].copy()
        df["alert_glofas"] = df["glofas_discharge"].apply(alert_level)
        rows.append(df)
        print(f"  {name}: {len(df)} ngày, đỉnh dự báo "
              f"{df['glofas_discharge'].max():.1f} m³/s", flush=True)

    if not rows:
        print("Không lấy được dữ liệu cho điểm nào — thoát với mã lỗi.")
        return 1

    out = pd.concat(rows, ignore_index=True)

    if not any(MODELS.glob("*.pkl")):
        print("Chưa có mô hình trong models/ — chỉ ghi dự báo GloFAS thô. "
              "Đây là trạng thái bình thường cho tới W5.")

    # Một file cho mỗi ngày phát báo. Giữ bản ĐẦU TIÊN của ngày — đó là bản
    # phát lúc 05:00 ICT. Lần chạy sau trong cùng ngày (chạy tay, hoặc job trễ)
    # ghi ra file riêng, không được xoá bản gốc.
    dest = LOG_DIR / f"{run_date:%Y-%m-%d}.csv"
    if dest.exists():
        stamp = datetime.now(ZoneInfo("UTC")).strftime("%H%MZ")
        dest = LOG_DIR / f"{run_date:%Y-%m-%d}_chu-ky-muon-{stamp}.csv"
        print(f"  ! Đã có bản dự báo cho {run_date} — ghi ra {dest.name} "
              f"thay vì ghi đè.", flush=True)
    out.to_csv(dest, index=False)
    out.to_csv(SUMMARY, index=False)
    print(f"\n→ {dest}  ({len(out)} dòng)")

    n_days = len(list(LOG_DIR.glob("20*.csv")))
    print(f"Kho dự báo đã tích luỹ: {n_days} ngày phát báo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
