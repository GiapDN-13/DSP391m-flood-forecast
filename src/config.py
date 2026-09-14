"""Cấu hình dùng chung. Mọi hằng số nằm ở đây, không rải rác trong notebook."""

from pathlib import Path

# ---------- Đường dẫn ----------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_EXTERNAL = ROOT / "data" / "external"
FIGURES = ROOT / "reports" / "figures"
CACHE = ROOT / ".cache"

for _p in (DATA_RAW, DATA_INTERIM, DATA_PROCESSED, DATA_EXTERNAL, FIGURES, CACHE):
    _p.mkdir(parents=True, exist_ok=True)

# ---------- Tái lập kết quả ----------
SEED = 42

# ---------- Vùng nghiên cứu ----------
# Điểm khởi đầu từ kế hoạch gốc; toạ độ CHÍNH THỨC chốt ở W02 sau khi quét lưới,
# kết quả ghi vào data/external/grid_candidates.csv
RIVER_POINTS = {
    "huong_kim_long": (16.46, 107.59),
    "bo_phu_oc": (16.55, 107.50),  # kiểm tra lại ở W02
}

BBOX = {"lat_min": 16.0, "lat_max": 16.9, "lon_min": 107.0, "lon_max": 108.0}
GRID_STEP_DEG = 0.05  # ~5 km

# ---------- API ----------
FLOOD_API = "https://flood-api.open-meteo.com/v1/flood"
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_API = "https://api.open-meteo.com/v1/forecast"

TIMEZONE = "Asia/Bangkok"  # UTC+7, trùng giờ Việt Nam
REQUEST_SLEEP_S = 1.2      # tránh rate limit, xem RISKS.md R3
MAX_RETRIES = 5

# ---------- Thời gian ----------
DATE_START = "1984-01-01"
DATE_END = "2026-08-31"

# Mốc GloFAS đổi từ reanalysis sang archived forecast — xem docs/DATA_SPLITS.md
GLOFAS_REGIME_BREAK = "2022-07-01"

TRAIN_END = "2015-12-31"
VALID_END = "2022-06-30"

# ---------- Bài toán ----------
HORIZONS = [1, 2, 3]          # số ngày dự báo trước
RAIN_LAGS = list(range(1, 8))
Q_LAGS = list(range(1, 15))
FLOOD_SEASON_MONTHS = [9, 10, 11, 12]

# Ngưỡng nguy cơ theo phân vị — giá trị thực tế chốt ở W05, ghi vào docs/THRESHOLDS.md
RISK_QUANTILES = {"muc_1": 0.95, "muc_2": 0.98, "muc_3": 0.995}
