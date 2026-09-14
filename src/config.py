"""Cấu hình dùng chung. Mọi hằng số nằm ở đây, không rải rác trong notebook."""

import sys
from pathlib import Path

# Console Windows mac dinh la cp1252, in tieng Viet co dau se nem UnicodeEncodeError
# va lam chet script du cong viec da xong. Ep UTF-8 ngay khi import config.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

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
# ---------- Điểm lưới GloFAS ----------
# ⚠️ PHÁT HIỆN 15/09/2026 (quét lưới lần 1, step 0.1°, xem data/external/grid_candidates.csv):
#   Toạ độ (16.46, 107.59) trong kế hoạch gốc KHÔNG nằm trên dòng chảy chính.
#   Quét quanh đó cho kết quả chênh nhau ~54 lần:
#       (16.46, 107.59)  q_mean ≈   5.7 m³/s   đỉnh ≈    29 m³/s   <- kế hoạch gốc, SAI ô
#       (16.56, 107.59)  q_mean ≈ 308.3 m³/s   đỉnh ≈  5584 m³/s   <- ứng viên dòng chính
#   Đỉnh ~5.600 m³/s hợp lý với lũ lớn trên sông Hương; ~29 m³/s thì không.
#   Nhiều ô lân cận trả về NaN = nằm ngoài mặt nạ sông của GloFAS (không có sông).
#
# VIỆC TIẾP THEO (G, W1): quét lại quanh (16.56, 107.59) với step 0.05°, đối chiếu
# toạ độ top-1 trên bản đồ sông (OSM) rồi chốt. Làm tương tự cho trạm Phú Ốc / sông Bồ.
RIVER_POINTS = {
    "huong_kim_long": (16.56, 107.59),  # tạm chốt sau quét lần 1 — cần xác nhận bản đồ
    "bo_phu_oc": (16.55, 107.50),       # CHƯA quét, làm ở W1
}

BBOX = {"lat_min": 16.0, "lat_max": 16.9, "lon_min": 107.0, "lon_max": 108.0}
GRID_STEP_DEG = 0.05  # ~5 km

# ---------- API ----------
FLOOD_API = "https://flood-api.open-meteo.com/v1/flood"
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_API = "https://api.open-meteo.com/v1/forecast"
# Kho du bao da phat trong qua khu (tu 2021) - dung cho kich ban B, RESEARCH_DESIGN.md §2.3
HIST_FORECAST_API = "https://historical-forecast-api.open-meteo.com/v1/forecast"

TIMEZONE = "Asia/Bangkok"  # UTC+7, trùng giờ Việt Nam
REQUEST_SLEEP_S = 1.2      # tránh rate limit, xem RISKS.md R3
MAX_RETRIES = 5

# ---------- Thời gian ----------
# Discharge lay du chuoi dai (re, 1 request/diem). Mua ERA5 chi tu 2010 - scope da cat.
DATE_START = "1984-01-01"
RAIN_DATE_START = "2010-01-01"
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

# --- Nguong bao dong ---
# Muc nuoc BD I/II/III (m) theo QD 05/2020/QD-TTg. H xac nhan o W1 (docs/THRESHOLDS.md §2).
ALERT_LEVELS_M = {
    "kim_long": {"BD1": 1.00, "BD2": 2.00, "BD3": 3.50},
    "phu_oc": {"BD1": 1.50, "BD2": 3.00, "BD3": 4.50},
}
# Nguong luu luong (m3/s) tuong ung - dien o W3 sau khi chay anh xa H->Q (duong R2).
ALERT_LEVELS_Q = {}
# Du phong R4 neu khong thu du su kien: phan vi mua lu. Khi dung PHAI doi ten nhan.
FALLBACK_QUANTILES = {"muc_1": 0.95, "muc_2": 0.98, "muc_3": 0.995}
EVENT_MATCH_WINDOW_DAYS = 2   # cua so ghep dinh lu thuc do voi dinh GloFAS
COST_RATIO_MISS_TO_FALSE_ALARM = 10   # docs/RESEARCH_DESIGN.md §3.3
