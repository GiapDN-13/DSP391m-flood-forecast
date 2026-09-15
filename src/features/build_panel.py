"""Dựng bảng phân tích chuẩn `daily_panel.parquet` (FR-E4 … FR-E6).

Mọi feature ở đây **chỉ được nhìn về quá khứ**. Rò rỉ thông tin tương lai là
lỗi chí mạng của bài toán chuỗi thời gian: nó không báo lỗi, làm kết quả đẹp
giả, và chỉ lộ ra khi bị hỏi lúc vấn đáp. Xem `tests/test_no_leakage.py`.

    python -m src.features.build_panel
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src import config as cfg
from src.etl import clean

# Chia lưới mưa thành 3 tiểu lưu vực theo vĩ độ (docs/DATA_SPLITS.md §5).
# Mưa thượng nguồn quan trọng hơn mưa hạ nguồn với lưu lượng ở hạ lưu, nên
# giữ tách ba vùng thay vì trung bình toàn lưu vực.
SUBBASINS = {
    "thuong": (16.10, 16.35),   # vùng núi, nguồn Tả Trạch / Hữu Trạch
    "trung": (16.35, 16.55),    # qua TP Huế
    "ha": (16.55, 16.85),       # hạ lưu, gần phá Tam Giang
}


# ------------------------------------------------- feature không rò rỉ

def make_lags(df: pd.DataFrame, col: str, lags: list[int]) -> pd.DataFrame:
    """Thêm cột trễ. `{col}_lag{k}` tại ngày t là giá trị tại ngày t−k."""
    out = df.copy()
    for k in lags:
        out[f"{col}_lag{k}"] = out[col].shift(k)
    return out


def make_rolling(df: pd.DataFrame, col: str, windows: list[int],
                 how: str = "mean") -> pd.DataFrame:
    """Trung bình/tổng trượt **trailing** — cửa sổ kết thúc tại ngày hiện tại.

    Tuyệt đối không dùng `center=True`: cửa sổ căn giữa sẽ lấy cả giá trị của
    những ngày phía sau, tức là rò rỉ tương lai.
    """
    out = df.copy()
    for w in windows:
        r = out[col].rolling(window=w, min_periods=w)
        out[f"{col}_roll{w}"] = getattr(r, how)()
    return out


def make_target(df: pd.DataFrame, horizon: int,
                col: str = "discharge") -> pd.DataFrame:
    """Biến mục tiêu: giá trị tại ngày t+horizon."""
    out = df.copy()
    out[f"target_h{horizon}"] = out[col].shift(-horizon)
    return out


def antecedent_index(rain: pd.Series, k: float = 0.9, n: int = 14) -> pd.Series:
    """Chỉ số ẩm trước (API): API_t = Σ kⁱ · P_{t−i}, i = 1…n.

    Đại diện cho mức bão hoà của đất. Cùng một trận mưa, nền ẩm cao sẽ sinh
    lũ lớn hơn nhiều — đây là feature thuỷ văn quan trọng nhất ngoài mưa.
    Bắt đầu từ i = 1 nên không dùng mưa của chính ngày hiện tại.
    """
    out = pd.Series(0.0, index=rain.index)
    for i in range(1, n + 1):
        out += (k ** i) * rain.shift(i).fillna(0.0)
    return out


# ------------------------------------------------------- gộp không gian

def aggregate_rain(rain: pd.DataFrame) -> pd.DataFrame:
    """Gộp lưới mưa thành trung bình theo từng tiểu lưu vực."""
    frames = []
    for name, (lo, hi) in SUBBASINS.items():
        sub = rain[(rain["lat"] >= lo) & (rain["lat"] < hi)]
        if sub.empty:
            print(f"  ! tiểu lưu vực '{name}' không có điểm lưới nào")
            continue
        g = (sub.groupby("date")["rain"].mean()
             .rename(f"rain_{name}").reset_index())
        frames.append(g.set_index("date"))
        print(f"  {name:8} {sub[['lat', 'lon']].drop_duplicates().shape[0]:3} điểm lưới")

    out = pd.concat(frames, axis=1).reset_index()
    out["rain_basin"] = out[[c for c in out.columns if c.startswith("rain_")]].mean(axis=1)
    return out


# ------------------------------------------------------------ dựng bảng

def build() -> pd.DataFrame:
    lat, lon = cfg.RIVER_POINTS["huong_kim_long"]
    print(f"Ô lưới lưu lượng: ({lat}, {lon})")

    q = clean.load_discharge(lat, lon)
    rain = clean.load_rain_daily()
    print("Gộp mưa theo tiểu lưu vực:")
    rain_agg = aggregate_rain(rain)

    df = q.merge(rain_agg, on="date", how="inner").sort_values("date")
    df = df.reset_index(drop=True)
    print(f"\nGiao nhau: {len(df):,} ngày, {df['date'].min():%Y-%m-%d} → "
          f"{df['date'].max():%Y-%m-%d}".replace(",", " "))

    rain_cols = [c for c in df.columns if c.startswith("rain_")]

    # --- feature ---
    df = make_lags(df, "discharge", cfg.Q_LAGS)
    for c in rain_cols:
        df = make_lags(df, c, cfg.RAIN_LAGS)
        df = make_rolling(df, c, [3, 5, 7], how="sum")
    df["api"] = antecedent_index(df["rain_basin"])

    # biến thiên lưu lượng — bắt pha nước đang lên
    df["q_diff1"] = df["discharge"].diff(1)
    df["q_diff3"] = df["discharge"].diff(3)

    # mùa, mã hoá tuần hoàn để tháng 12 và tháng 1 nằm cạnh nhau
    doy = df["date"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["month"] = df["date"].dt.month
    df["mua_lu"] = df["month"].isin(cfg.FLOOD_SEASON_MONTHS).astype(int)

    # --- biến mục tiêu ---
    for h in cfg.HORIZONS:
        df = make_target(df, h)

    # --- nhãn cấp báo động, nếu đã chốt ngưỡng ở W3 ---
    levels = getattr(cfg, "ALERT_LEVELS_Q", {}) or {}
    if levels:
        df["alert_level"] = 0
        for k, name in enumerate(("BD1", "BD2", "BD3"), start=1):
            if name in levels:
                df.loc[df["discharge"] >= levels[name], "alert_level"] = k
        print(f"Đã gán nhãn alert_level từ {levels}")
    else:
        df["alert_level"] = pd.NA
        print("⚠️  Chưa có ALERT_LEVELS_Q — cột alert_level để trống.\n"
              "    Cần chạy src/features/thresholds.py sau khi có flood_events.csv "
              "(issue #1, #5).")

    return df


def main() -> int:
    df = build()
    clean.validate_daily_index(df, require_continuous=True)

    dest = cfg.DATA_PROCESSED / "daily_panel.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest, index=False)

    print(f"\n→ {dest}")
    print(f"   {len(df):,} dòng × {df.shape[1]} cột".replace(",", " "))
    usable = df.dropna(subset=[f"target_h{h}" for h in cfg.HORIZONS]
                       + [c for c in df.columns if "_lag" in c])
    print(f"   dùng được sau khi bỏ NaN đầu/cuối: {len(usable):,} dòng".replace(",", " "))
    print(f"   khoảng: {df['date'].min():%Y-%m-%d} → {df['date'].max():%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
