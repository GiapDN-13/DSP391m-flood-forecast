"""Làm sạch và chuẩn hoá dữ liệu thô (FR-E1 … FR-E3).

Lỗi ETL là loại lỗi âm thầm nhất: sai múi giờ một tiếng hoặc nhầm mm/h với
mm/ngày sẽ **không báo lỗi gì cả**, chỉ làm mọi kết quả phía sau sai lặng lẽ.
Vì vậy mỗi hàm ở đây đều có test tương ứng trong `tests/test_clean.py`, và các
hàm `validate_*` **chủ động ném lỗi** thay vì lặng lẽ sửa dữ liệu.

    python -m src.etl.clean          # chạy toàn bộ, ghi ra data/interim/
"""

from __future__ import annotations

import sys

import pandas as pd

from src import config as cfg

TZ = cfg.TIMEZONE          # "Asia/Bangkok" = UTC+7, trùng giờ Việt Nam


# --------------------------------------------------------------- FR-E1

def to_local_time(s: pd.Series) -> pd.Series:
    """Đổi chuỗi thời gian sang giờ Việt Nam rồi bỏ thông tin múi giờ.

    Bỏ tzinfo sau khi đổi là cố ý: mọi thứ phía sau coi như đã ở giờ VN, không
    còn chỗ nào phải nhớ "cái này UTC hay ICT". Chuỗi chưa có tzinfo được hiểu
    là UTC — đúng với dữ liệu Open-Meteo khi không truyền tham số `timezone`.
    """
    s = pd.to_datetime(s)
    if s.dt.tz is None:
        s = s.dt.tz_localize("UTC")
    return s.dt.tz_convert(TZ).dt.tz_localize(None)


# --------------------------------------------------------------- FR-E2

def hourly_to_daily(df: pd.DataFrame, col: str, how: str = "sum",
                    time_col: str = "time") -> pd.DataFrame:
    """Gộp chuỗi theo giờ thành theo ngày.

    `how="sum"` cho mưa (cộng dồn), `how="mean"` cho nhiệt độ và độ ẩm.
    Ngày được cắt theo **giờ Việt Nam** — xem `docs/API_NOTES.md` §4.
    """
    if how not in {"sum", "mean", "max", "min"}:
        raise ValueError(f"cách gộp không hỗ trợ: {how}")

    out = df.copy()
    out[time_col] = pd.to_datetime(out[time_col])
    grouped = out.groupby(out[time_col].dt.date)[col]
    res = getattr(grouped, how)().reset_index()
    res.columns = [time_col, col]
    res[time_col] = pd.to_datetime(res[time_col])
    return res


# --------------------------------------------------------------- FR-E3

def validate_discharge(df: pd.DataFrame, col: str = "discharge") -> pd.DataFrame:
    """Lưu lượng không bao giờ được âm."""
    neg = df[df[col] < 0]
    if len(neg):
        raise ValueError(
            f"Có {len(neg)} giá trị lưu lượng âm ở cột '{col}' "
            f"(nhỏ nhất {neg[col].min()}). Dữ liệu hỏng, không được dùng tiếp."
        )
    return df


def validate_daily_index(df: pd.DataFrame, col: str = "date",
                         require_continuous: bool = False) -> pd.DataFrame:
    """Chuỗi ngày phải duy nhất, và tuỳ chọn là liên tục không đứt quãng."""
    d = pd.to_datetime(df[col])

    dup = d[d.duplicated()]
    if len(dup):
        raise ValueError(
            f"Có {len(dup)} ngày bị trùng trong cột '{col}', "
            f"ví dụ {dup.iloc[0].date()}."
        )

    if require_continuous and len(d) > 1:
        full = pd.date_range(d.min(), d.max(), freq="D")
        missing = full.difference(pd.DatetimeIndex(d))
        if len(missing):
            raise ValueError(
                f"Chuỗi ngày bị thiếu {len(missing)} ngày, "
                f"ví dụ {missing[0].date()}."
            )
    return df


def report_missing(df: pd.DataFrame, col: str,
                   time_col: str = "time") -> pd.DataFrame:
    """Thống kê tỉ lệ thiếu theo năm — đưa thẳng vào Report 2."""
    d = df.copy()
    d[time_col] = pd.to_datetime(d[time_col])
    g = d.groupby(d[time_col].dt.year)[col]
    out = pd.DataFrame({"n": g.size(), "thieu": g.apply(lambda s: s.isna().sum())})
    out["pct_thieu"] = (out["thieu"] / out["n"] * 100).round(2)
    return out.reset_index(names="nam")


# ------------------------------------------------------------ nạp dữ liệu

def load_discharge(lat: float, lon: float) -> pd.DataFrame:
    """Nạp chuỗi lưu lượng của một ô lưới, đã làm sạch."""
    f = cfg.DATA_RAW / "discharge" / f"q_{lat}_{lon}.parquet"
    if not f.exists():
        raise FileNotFoundError(f"Chưa crawl ô ({lat}, {lon}): thiếu {f}")
    d = pd.read_parquet(f)
    d = d.rename(columns={"river_discharge": "discharge", "time": "date"})
    d["date"] = pd.to_datetime(d["date"])
    d = d[["date", "discharge"]].sort_values("date").reset_index(drop=True)
    validate_discharge(d)
    validate_daily_index(d, require_continuous=True)
    return d


def load_rain_daily() -> pd.DataFrame:
    """Nạp toàn bộ điểm mưa ngày, giữ nguyên lat/lon để gộp theo tiểu lưu vực."""
    files = sorted((cfg.DATA_RAW / "rain_daily").glob("rd_*.parquet"))
    if not files:
        raise FileNotFoundError("Chưa có dữ liệu mưa ngày trong data/raw/rain_daily/")
    df = pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)
    df = df.rename(columns={"time": "date", "precipitation_sum": "rain"})
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "lat", "lon"]).reset_index(drop=True)


def load_forecast_rain() -> pd.DataFrame:
    """Mưa dự báo đã phát trong quá khứ — đầu vào kịch bản B."""
    files = sorted((cfg.DATA_RAW / "fc_rain").glob("fc_*.parquet"))
    if not files:
        raise FileNotFoundError("Chưa có dữ liệu mưa dự báo trong data/raw/fc_rain/")
    df = pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)
    df = df.rename(columns={"time": "date", "precipitation_sum": "rain_fc"})
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "lat", "lon"]).reset_index(drop=True)


def main() -> int:
    lat, lon = cfg.RIVER_POINTS["huong_kim_long"]
    print(f"Ô lưới: ({lat}, {lon})")

    q = load_discharge(lat, lon)
    print(f"  lưu lượng : {len(q):,} ngày, {q['date'].min():%Y-%m-%d} → "
          f"{q['date'].max():%Y-%m-%d}".replace(",", " "))

    rain = load_rain_daily()
    print(f"  mưa ngày  : {len(rain):,} dòng, {rain[['lat', 'lon']].drop_duplicates().shape[0]} "
          f"điểm lưới".replace(",", " "))

    fc = load_forecast_rain()
    print(f"  mưa dự báo: {len(fc):,} dòng".replace(",", " "))

    cfg.DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    q.to_parquet(cfg.DATA_INTERIM / "discharge.parquet", index=False)
    rain.to_parquet(cfg.DATA_INTERIM / "rain_daily.parquet", index=False)
    fc.to_parquet(cfg.DATA_INTERIM / "rain_forecast.parquet", index=False)
    print(f"\n→ {cfg.DATA_INTERIM}")

    print("\nTỉ lệ thiếu của chuỗi lưu lượng theo năm (5 năm gần nhất):")
    print(report_missing(q.rename(columns={"date": "time"}), "discharge")
          .tail(5).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
