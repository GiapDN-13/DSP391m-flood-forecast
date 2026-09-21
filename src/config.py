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

# ---------- Thành viên ----------
# NGUỒN SỰ THẬT DUY NHẤT cho tên. Mọi chỗ sinh báo cáo/slide phải import từ đây,
# đừng viết lại tên trong từng file — đã một lần sửa tên mà quên build lại PDF.
TEAM = [
    {"vi": "Đặng Nguyên Giáp", "ascii": "Dang Nguyen Giap", "role": "Tech Lead"},
    {"vi": "Hồ Anh Đức",       "ascii": "Ho Anh Duc",       "role": "Data Analyst"},
    {"vi": "Mai Thị Lệ Huyền", "ascii": "Mai Thi Le Huyen", "role": "Research & Docs"},
]
TEAM_VI = [m["vi"] for m in TEAM]
TEAM_ASCII = [m["ascii"] for m in TEAM]

# ---------- Tái lập kết quả ----------
SEED = 42

# ---------- Vùng nghiên cứu ----------
# ---------- Điểm lưới GloFAS ----------
# CHỐT 15/09/2026 bằng src/features/river_id.py (xem docs/FINDINGS_GRID.md).
# Căn cứ mạnh nhất là suy ngược diện tích lưu vực từ lưu lượng trung bình
# nhiều năm: Q_tb ≈ diện tích × dòng chảy đơn vị (~0,046 m³/s/km² ở vùng Huế).
#
#   (16.45, 107.50)  120,7 m³/s  → 2 366–2 943 km²  ≈ sông Hương 2 830 km²  (lệch 7 %)
#   (16.55, 107.50)  194,5 m³/s  → 3 814–4 745 km²  ≈ Hương + Bồ 3 768 km²  (lệch 12 %)
#   (16.60, 107.55)  313,3 m³/s  → 6 144–7 643 km²  vượt xa cả hai → đã gộp lưu vực khác
#
# Toạ độ kế hoạch gốc (16.46, 107.59) chỉ cho 5,7 m³/s — không nằm trên dòng chính.
RIVER_POINTS = {
    "huong_kim_long": (16.45, 107.50),   # đại diện lưu vực sông Hương
}

# Ô đã xét nhưng KHÔNG dùng, giữ lại để giải trình trong báo cáo:
REJECTED_POINTS = {
    "hop_luu_huong_bo": (16.55, 107.50),  # gộp cả Hương lẫn Bồ
    "ha_luu_pha_tam_giang": (16.60, 107.55),  # gộp thêm lưu vực ngoài
    "ke_hoach_goc_sai_o": (16.46, 107.59),    # nhánh nhỏ, 5,7 m³/s
}

# Sông Bồ: GloFAS ở độ phân giải ~5 km KHÔNG tách được thành dòng riêng trong
# vùng này — mọi ô ứng viên đều lệch ≥ 84 % so với diện tích lưu vực 938 km².
# ⇒ Phạm vi thu hẹp còn MỘT trạm (Kim Long / sông Hương). Nêu rõ ở Limitations.

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
DATE_START = "1984-01-01"          # khoảng YÊU CẦU khi gọi API
# Khoảng THỰC TẾ có dữ liệu. Open-Meteo công bố GloFAS v4 từ 1984, nhưng
# endpoint chỉ trả giá trị từ 1997 cho vùng này: 1984–1996 rỗng 100 % ở cả 83
# ô lưới (30,5 % chuỗi). Phát hiện 21/09/2026 khi ghép sự kiện lũ — xem
# docs/FINDINGS_EVENTS.md §3. Dùng hằng số này khi nói về độ dài chuỗi.
DISCHARGE_DATA_START = "1997-01-01"
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
# Muc nuoc BD I/II/III (m) theo QD 05/2020/QD-TTg.
# DA KIEM CHUNG CHEO 15/09/2026 bang so hoc tu 5 ban tin Dai KTTV
# (moi ban tin ghi ca muc nuoc do duoc lan chenh so voi cap bao dong):
#   1.37 m = tren BD I  0.37  -> BD I  = 1.00
#   2.70 m = tren BD II 0.70  -> BD II = 2.00   (them nguon: 2.81 = tren BD II 0.81)
#   3.63 m = tren BD III 0.13 -> BD III = 3.50  (them nguon: 3.75 = tren BD III 0.25)
# Bao cao PHAI trich dan nguon goc la QD 05/2020/QD-TTg, khong trich bao chi.
ALERT_LEVELS_M = {
    "kim_long": {"BD1": 1.00, "BD2": 2.00, "BD3": 3.50},
}
# Phu Oc da loai: GloFAS khong tach duoc song Bo (docs/FINDINGS_GRID.md Phan 2).
# Nguong luu luong (m3/s) tuong ung - dien o W3 sau khi chay anh xa H->Q (duong R2).
ALERT_LEVELS_Q = {}
# Du phong R4 neu khong thu du su kien: phan vi mua lu. Khi dung PHAI doi ten nhan.
FALLBACK_QUANTILES = {"muc_1": 0.95, "muc_2": 0.98, "muc_3": 0.995}
EVENT_MATCH_WINDOW_DAYS = 2   # cua so ghep dinh lu thuc do voi dinh GloFAS
COST_RATIO_MISS_TO_FALSE_ALARM = 10   # docs/RESEARCH_DESIGN.md §3.3
