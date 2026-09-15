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
from datetime import date

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


def main() -> int:
    run_date = date.today()
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
        df.insert(0, "run_date", run_date)
        df.insert(1, "point", name)
        df.insert(2, "lat", lat)
        df.insert(3, "lon", lon)
        df["horizon_days"] = (df["target_date"].dt.date - run_date).apply(lambda d: d.days)
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

    # Một file cho mỗi ngày phát báo: không bao giờ ghi đè, dễ đối chiếu về sau
    dest = LOG_DIR / f"{run_date:%Y-%m-%d}.csv"
    out.to_csv(dest, index=False)
    out.to_csv(SUMMARY, index=False)
    print(f"\n→ {dest}  ({len(out)} dòng)")

    n_days = len(list(LOG_DIR.glob("20*.csv")))
    print(f"Kho dự báo đã tích luỹ: {n_days} ngày phát báo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
