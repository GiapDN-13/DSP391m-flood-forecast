"""Hàm đọc dữ liệu cho dashboard — thuần pandas, KHÔNG import streamlit.

Tách khỏi ``app.py`` để kiểm thử được (``tests/test_dashboard.py``) mà không
cần dựng giao diện. Mọi hàm nhận đường dẫn làm tham số, mặc định trỏ vào
file đã commit trong repo, nên bản triển khai trên Streamlit Community Cloud
(không có ``data/processed/`` vì bị gitignore) vẫn chạy được.

Nguyên tắc: thiếu file hoặc thiếu cột thì **xuống cấp nhẹ nhàng** — trả về
bảng rỗng / cột NaN và để giao diện ghi chú, không ném lỗi.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "reports" / "forecast_log"
# Cho phép trỏ sang thư mục khác (test chạy app với bản phát giả có cột mô hình).
ENV_LOG_DIR = "DASHBOARD_LOG_DIR"
RISK_CSV = ROOT / "reports" / "risk_levels.csv"
SHAP_CSV = ROOT / "reports" / "shap_importance.csv"
PANEL = ROOT / "data" / "processed" / "daily_panel_ext.parquet"
# Geojson lưu vực con đã được mở khỏi .gitignore (data/external/basins/**),
# nên có mặt cả trên bản triển khai.
SUBBASINS = ROOT / "data" / "external" / "basins" / "subbasins.geojson"

POINT = "huong_kim_long"
KIM_LONG = (16.456, 107.562)   # cửa ra lưu vực sau snap (src/features/basins.py)

# Cột mô hình sẽ được predict_daily.py ghi thêm khi có mô hình trong models/.
MODEL_COLS = ("lgbm_q", "lgbm_san_ho", "p_level1", "alert_lgbm")
# Cột có từ đầu hoặc thêm dần theo thời gian (log tháng 9 chưa có cột hồ).
BASE_COLS = ("glofas_discharge", "q_release_upstream", "glofas_san_ho")

# Chỉ nhận bản phát chính thức YYYY-MM-DD.csv; bỏ "_chu-ky-muon-" và "_latest"
# (README của forecast_log: bản chạy muộn không dùng cho đánh giá).
_RUN_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.csv$")

# Ngưỡng dự phòng khi thiếu reports/risk_levels.csv — CHỈ để app không sập;
# giao diện sẽ ghi rõ là đang dùng giá trị dự phòng.
FALLBACK_LEVELS = {1: 806.0, 2: 1275.4, 3: 1905.3}

LEVEL_TEXT = {
    -1: "Không có số liệu",
    0: "Bình thường",
    1: "Mức nguy cơ 1",
    2: "Mức nguy cơ 2",
    3: "Mức nguy cơ 3",
}
# Biểu tượng đi KÈM chữ — không để màu tự mang nghĩa.
LEVEL_ICON = {-1: "⚪", 0: "🟢", 1: "🟡", 2: "🟠", 3: "🔴"}
# Bảng màu trạng thái (dùng chung cho đường ngưỡng và bản đồ).
LEVEL_COLOR = {-1: "#9a9a96", 0: "#0ca30c", 1: "#fab219", 2: "#ec835a", 3: "#d03b3b"}

SUBBASIN_LABELS = {
    "ta_trach_dam": "Tả Trạch (thượng lưu đập)",
    "binh_dien_dam": "Bình Điền / Hữu Trạch (thượng lưu đập)",
    "ta_trach_below_dam": "Tả Trạch (hạ du đập)",
    "huu_trach_below_dam": "Hữu Trạch (hạ du đập)",
    "huong_tuan_kim_long": "Sông Hương Tuần → Kim Long",
}

SHAP_GROUP_LABELS = {
    "flow": "Lưu lượng trễ",
    "rain": "Mưa ≤ 7 ngày",
    "rain_long": "Mưa dài / đại diện hồ",
    "soil_api": "Độ ẩm đất & API",
    "storm": "Bão / ATNĐ",
    "synoptic": "Khí áp, gió, ẩm",
    "enso": "ENSO",
    "season": "Mùa (lịch)",
}


# ---------------------------------------------------------------- bản phát
def _log_dir(log_dir: Path | None) -> Path:
    if log_dir is not None:
        return Path(log_dir)
    return Path(os.environ.get(ENV_LOG_DIR) or LOG_DIR)


def list_runs(log_dir: Path | None = None) -> list[date]:
    """Các ngày phát báo chính thức có file, tăng dần."""
    log_dir = _log_dir(log_dir)
    if not Path(log_dir).is_dir():
        return []
    out = []
    for p in Path(log_dir).iterdir():
        m = _RUN_FILE.match(p.name)
        if m:
            out.append(date.fromisoformat(m.group(1)))
    return sorted(out)


def latest_run(runs: list[date]) -> date | None:
    return max(runs) if runs else None


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Bổ sung cột mô hình/cột hồ còn thiếu thành NaN để phần vẽ không phải rẽ nhánh."""
    df = df.copy()
    for c in (*BASE_COLS, *MODEL_COLS):
        if c not in df.columns:
            df[c] = pd.NA
    for c in (*BASE_COLS, "lgbm_q", "lgbm_san_ho", "p_level1"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    return df


def read_run(path: Path, point: str = POINT) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "point" in df.columns and (df["point"] == point).any():
        df = df[df["point"] == point]
    df = ensure_columns(df)
    df["run_date"] = pd.to_datetime(df["run_date"]).dt.normalize()
    df["target_date"] = pd.to_datetime(df["target_date"]).dt.normalize()
    df["horizon_days"] = pd.to_numeric(df["horizon_days"], errors="coerce")
    return df.sort_values("target_date").reset_index(drop=True)


def load_run(run: date, log_dir: Path | None = None, point: str = POINT) -> pd.DataFrame:
    return read_run(_log_dir(log_dir) / f"{run:%Y-%m-%d}.csv", point)


def has_model(df: pd.DataFrame) -> bool:
    """Bản phát có số dự báo của mô hình (không chỉ có cột rỗng)?"""
    return "lgbm_q" in df.columns and df["lgbm_q"].notna().any()


# ---------------------------------------------------------------- mức nguy cơ
def load_risk_levels(path: Path = RISK_CSV) -> tuple[dict[int, float], bool]:
    """Ngưỡng {1: Q95, 2: Q98, 3: Q99,5} mùa lũ và cờ "đọc từ file"."""
    try:
        df = pd.read_csv(path)
        thr = {}
        for k in (1, 2, 3):
            row = df.loc[df["muc"] == f"nguy_co_{k}", "nguong_m3s"]
            thr[k] = float(row.iloc[0])
        return thr, True
    except (OSError, KeyError, IndexError, ValueError):
        return dict(FALLBACK_LEVELS), False


def classify(q, thresholds: dict[int, float]) -> int:
    """Lưu lượng → mức 0..3; -1 khi thiếu số."""
    if q is None or pd.isna(q):
        return -1
    lv = 0
    for k in (1, 2, 3):
        if q >= thresholds[k]:
            lv = k
    return lv


def level_label(lv: int) -> str:
    return f"{LEVEL_ICON[lv]} {LEVEL_TEXT[lv]}"


def primary_value(row: pd.Series) -> tuple[float, str]:
    """Số dùng để xếp mức: ưu tiên mô hình (đã nâng sàn hồ) → GloFAS sàn hồ → GloFAS thô."""
    for col, name in (("lgbm_san_ho", "LightGBM (sàn hồ)"), ("lgbm_q", "LightGBM"),
                      ("glofas_san_ho", "GloFAS (sàn hồ)"),
                      ("glofas_discharge", "GloFAS thô")):
        v = row.get(col)
        if v is not None and not pd.isna(v):
            return float(v), name
    return float("nan"), "—"


def forecast_table(run_df: pd.DataFrame, thresholds: dict[int, float],
                   horizons: tuple[int, ...] = (1, 2, 3)) -> pd.DataFrame:
    """Bảng 3 ngày tới: số dự báo, nguồn dùng để xếp mức, nhãn mức."""
    rows = []
    for h in horizons:
        sub = run_df[run_df["horizon_days"] == h]
        if sub.empty:
            continue
        r = sub.iloc[0]
        q, src = primary_value(r)
        lv = classify(q, thresholds)
        rows.append({
            "horizon": h,
            "target_date": r["target_date"].date(),
            "glofas_discharge": r["glofas_discharge"],
            "glofas_san_ho": r["glofas_san_ho"],
            "lgbm_q": r["lgbm_q"],
            "lgbm_san_ho": r["lgbm_san_ho"],
            "p_level1": r["p_level1"],
            "q_xep_muc": q,
            "nguon_xep_muc": src,
            "level": lv,
            "muc": level_label(lv),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- lịch sử
def history_from_logs(end: date, days: int = 30, log_dir: Path | None = None,
                      point: str = POINT) -> pd.DataFrame:
    """Lưu lượng đã qua từ dòng horizon 0 của các bản phát ≤ ``end``.

    Đây là GloFAS ngày phát (không phải trạm đo), dùng vì ``data/`` không có
    trên bản triển khai. Trả về cột ``date``, ``discharge``.
    """
    start = pd.Timestamp(end) - pd.Timedelta(days=days)
    parts = []
    for run in list_runs(log_dir):
        if run > end or pd.Timestamp(run) < start:
            continue
        df = load_run(run, log_dir, point)
        h0 = df[df["horizon_days"] == 0]
        if not h0.empty:
            parts.append(h0[["target_date", "glofas_discharge"]])
    if not parts:
        return pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"),
                             "discharge": pd.Series(dtype="float64")})
    out = (pd.concat(parts).rename(columns={"target_date": "date",
                                             "glofas_discharge": "discharge"})
           .dropna().drop_duplicates("date", keep="last").sort_values("date"))
    return out.reset_index(drop=True)


def history_from_panel(end: date, days: int = 30, path: Path = PANEL) -> pd.DataFrame:
    """Chuỗi GloFAS tái phân tích/lưu trữ trong panel (chỉ có trên máy có data/)."""
    empty = pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"),
                          "discharge": pd.Series(dtype="float64")})
    if not Path(path).exists():
        return empty
    try:
        p = pd.read_parquet(path, columns=["date", "discharge"])
    except Exception:   # thiếu pyarrow hoặc file hỏng → coi như không có
        return empty
    p["date"] = pd.to_datetime(p["date"]).dt.normalize()
    start = pd.Timestamp(end) - pd.Timedelta(days=days)
    p = p[(p["date"] >= start) & (p["date"] <= pd.Timestamp(end))].dropna()
    return p.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------- SHAP
def load_shap_groups(path: Path = SHAP_CSV, basis: str = "all") -> pd.DataFrame:
    """Tỉ trọng nhóm (%) theo horizon: trung bình 3 seed + min/max làm khoảng.

    ``basis`` = "all" (toàn tập test) hoặc "flood" (chỉ ngày lũ). Trả về bảng
    dài: group, nhom, horizon, share, lo, hi.
    """
    col = "share_all_pct" if basis == "all" else "share_flood_pct"
    try:
        d = pd.read_csv(path)
    except OSError:
        return pd.DataFrame(columns=["group", "nhom", "horizon", "share", "lo", "hi"])
    g = d[d["level"] == "group"]
    agg = (g.groupby(["group", "horizon"])[col]
           .agg(share="mean", lo="min", hi="max").reset_index())
    agg["nhom"] = agg["group"].map(SHAP_GROUP_LABELS).fillna(agg["group"])
    return agg[["group", "nhom", "horizon", "share", "lo", "hi"]]


# ---------------------------------------------------------------- lưu vực
def load_subbasins(path: Path = SUBBASINS) -> dict | None:
    """Geojson 5 lưu vực con, thêm ``id`` và tên tiếng Việt cho mỗi feature."""
    try:
        gj = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for f in gj.get("features", []):
        name = f["properties"].get("name", "")
        f["id"] = name
        f["properties"]["ten"] = SUBBASIN_LABELS.get(name, name)
    return gj


def subbasin_frame(gj: dict, level: int) -> pd.DataFrame:
    """Một dòng cho mỗi lưu vực con, cùng gán MỨC TOÀN LƯU VỰC (chưa có dự báo riêng)."""
    rows = [{"id": f["id"], "ten": f["properties"]["ten"],
             "dien_tich_km2": f["properties"].get("area_km2"),
             "muc": level_label(level)} for f in gj.get("features", [])]
    return pd.DataFrame(rows)
