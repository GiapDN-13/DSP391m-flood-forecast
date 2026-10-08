"""Làm sạch và chuẩn hoá dữ liệu thô (FR-E1 … FR-E3) — DuckDB + Polars, không pandas.

Hai công cụ, mỗi cái một việc:

* **DuckDB** đọc dữ liệu thô. Một câu SQL `read_parquet('thư_mục/*.parquet')` quét
  cả trăm file cùng lúc, đa luồng, không phải nạp từng file vào bộ nhớ rồi nối
  lại như cách làm với pandas. Đây là cách xử lý dữ liệu lớn mà kế hoạch dự án
  đã chọn từ đầu (`DSP391m_Ke_hoach_du_an_1.pdf` §6).
* **Polars** biến đổi bảng sau khi đọc: đổi múi giờ, gộp theo ngày, kiểm tra.
  Polars chạy theo cột, đa luồng, và không có chỉ mục ẩn kiểu pandas — nên ít
  lỗi lệch dòng âm thầm hơn.

Lỗi ETL là loại lỗi âm thầm nhất: sai múi giờ một tiếng hoặc nhầm mm/h với
mm/ngày sẽ **không báo lỗi gì cả**, chỉ làm mọi kết quả phía sau sai lặng lẽ.
Vì vậy mỗi hàm ở đây đều có test trong `tests/test_clean.py`, và các hàm
`validate_*` **chủ động ném lỗi** thay vì lặng lẽ sửa dữ liệu.

    python -m src.etl.clean          # chạy toàn bộ, ghi ra data/interim/
"""

from __future__ import annotations

import sys

import duckdb
import polars as pl

from src import config as cfg

TZ = cfg.TIMEZONE          # "Asia/Bangkok" = UTC+7, trùng giờ Việt Nam


def _sql(query: str) -> pl.DataFrame:
    """Chạy một câu SQL DuckDB và nhận kết quả thẳng dưới dạng bảng Polars."""
    return duckdb.sql(query).pl()


def _glob(folder: str, pattern: str) -> str:
    """Đường dẫn dạng glob cho DuckDB (dùng dấu / để chạy được cả trên Windows)."""
    files = list((cfg.DATA_RAW / folder).glob(pattern))
    if not files:
        raise FileNotFoundError(f"Chưa có dữ liệu trong data/raw/{folder}/")
    return str(cfg.DATA_RAW / folder / pattern).replace("\\", "/")


# --------------------------------------------------------------- FR-E1

def to_local_time(s: pl.Series) -> pl.Series:
    """Đổi chuỗi thời gian sang giờ Việt Nam rồi bỏ thông tin múi giờ.

    Bỏ tzinfo sau khi đổi là cố ý: mọi thứ phía sau coi như đã ở giờ VN, không
    còn chỗ nào phải nhớ "cái này UTC hay ICT". Chuỗi chưa có tzinfo được hiểu
    là UTC — đúng với dữ liệu Open-Meteo khi không truyền tham số `timezone`.
    """
    if s.dtype == pl.Utf8:
        s = s.str.to_datetime()
    if s.dtype.time_zone is None:                        # type: ignore[union-attr]
        s = s.dt.replace_time_zone("UTC")
    return s.dt.convert_time_zone(TZ).dt.replace_time_zone(None)


# --------------------------------------------------------------- FR-E2

def hourly_to_daily(df: pl.DataFrame, col: str, how: str = "sum",
                    time_col: str = "time") -> pl.DataFrame:
    """Gộp chuỗi theo giờ thành theo ngày.

    `how="sum"` cho mưa (cộng dồn), `how="mean"` cho nhiệt độ và độ ẩm.
    Ngày được cắt theo **giờ Việt Nam** — xem `docs/API_NOTES.md` §4.
    """
    aggs = {"sum": pl.col(col).sum(), "mean": pl.col(col).mean(),
            "max": pl.col(col).max(), "min": pl.col(col).min()}
    if how not in aggs:
        raise ValueError(f"cách gộp không hỗ trợ: {how}")
    return (df.group_by(pl.col(time_col).dt.date().alias(time_col))
              .agg(aggs[how])
              .sort(time_col)
              .with_columns(pl.col(time_col).cast(pl.Datetime("us"))))


# --------------------------------------------------------------- FR-E3

def validate_discharge(df: pl.DataFrame, col: str = "discharge") -> pl.DataFrame:
    """Lưu lượng không bao giờ được âm."""
    neg = df.filter(pl.col(col) < 0)
    if neg.height:
        raise ValueError(
            f"Có {neg.height} giá trị lưu lượng âm ở cột '{col}' "
            f"(nhỏ nhất {neg[col].min()}). Dữ liệu hỏng, không được dùng tiếp."
        )
    return df


def validate_daily_index(df: pl.DataFrame, col: str = "date",
                         require_continuous: bool = False) -> pl.DataFrame:
    """Chuỗi ngày phải duy nhất, và tuỳ chọn là liên tục không đứt quãng."""
    d = df[col].cast(pl.Date)

    dup = d.filter(d.is_duplicated())
    if dup.len():
        raise ValueError(
            f"Có {dup.n_unique()} ngày bị trùng trong cột '{col}', ví dụ {dup[0]}."
        )

    if require_continuous and d.len() > 1:
        full = pl.date_range(d.min(), d.max(), "1d", eager=True)
        missing = full.filter(~full.is_in(d))
        if missing.len():
            raise ValueError(
                f"Chuỗi ngày bị thiếu {missing.len()} ngày, ví dụ {missing[0]}."
            )
    return df


def report_missing(df: pl.DataFrame, col: str, time_col: str = "time") -> pl.DataFrame:
    """Thống kê tỉ lệ thiếu theo năm — đưa thẳng vào Report 2."""
    return (df.group_by(pl.col(time_col).dt.year().alias("nam"))
              .agg(pl.len().alias("n"), pl.col(col).is_null().sum().alias("thieu"))
              .with_columns((pl.col("thieu") / pl.col("n") * 100).round(2).alias("pct_thieu"))
              .sort("nam"))


# ------------------------------------------------------------ nạp dữ liệu

def load_discharge(lat: float, lon: float) -> pl.DataFrame:
    """Nạp chuỗi lưu lượng của một ô lưới, đã làm sạch."""
    f = cfg.DATA_RAW / "discharge" / f"q_{lat}_{lon}.parquet"
    if not f.exists():
        raise FileNotFoundError(f"Chưa crawl ô ({lat}, {lon}): thiếu {f}")
    d = _sql(f"""
        SELECT CAST(time AS TIMESTAMP) AS date,
               river_discharge          AS discharge
        FROM read_parquet('{str(f).replace(chr(92), '/')}')
        ORDER BY date
    """)
    validate_discharge(d)
    validate_daily_index(d, require_continuous=True)
    return d


def load_rain_daily() -> pl.DataFrame:
    """Nạp toàn bộ điểm mưa ngày bằng MỘT câu SQL quét cả thư mục.

    Giữ nguyên lat/lon để gộp theo tiểu lưu vực ở bước sau.
    """
    return _sql(f"""
        SELECT CAST(time AS TIMESTAMP) AS date,
               lat, lon,
               precipitation_sum       AS rain,
               * EXCLUDE (time, lat, lon, precipitation_sum)
        FROM read_parquet('{_glob("rain_daily", "rd_*.parquet")}')
        ORDER BY date, lat, lon
    """)


def load_forecast_rain() -> pl.DataFrame:
    """Mưa dự báo đã phát trong quá khứ — đầu vào kịch bản B."""
    return _sql(f"""
        SELECT CAST(time AS TIMESTAMP) AS date,
               lat, lon,
               precipitation_sum       AS rain_fc,
               * EXCLUDE (time, lat, lon, precipitation_sum)
        FROM read_parquet('{_glob("fc_rain", "fc_*.parquet")}')
        ORDER BY date, lat, lon
    """)


def main() -> int:
    lat, lon = cfg.RIVER_POINTS["huong_kim_long"]
    print(f"Ô lưới: ({lat}, {lon})")

    q = load_discharge(lat, lon)
    print(f"  lưu lượng : {q.height} ngày, {q['date'].min():%Y-%m-%d} → "
          f"{q['date'].max():%Y-%m-%d}")

    rain = load_rain_daily()
    print(f"  mưa ngày  : {rain.height} dòng, "
          f"{rain.select('lat', 'lon').unique().height} điểm lưới")

    fc = load_forecast_rain()
    print(f"  mưa dự báo: {fc.height} dòng")

    cfg.DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    q.write_parquet(cfg.DATA_INTERIM / "discharge.parquet")
    rain.write_parquet(cfg.DATA_INTERIM / "rain_daily.parquet")
    fc.write_parquet(cfg.DATA_INTERIM / "rain_forecast.parquet")
    print(f"\n→ {cfg.DATA_INTERIM}")

    print("\nTỉ lệ thiếu của chuỗi lưu lượng theo năm (5 năm gần nhất):")
    print(report_missing(q, "discharge", time_col="date").tail(5))
    return 0


if __name__ == "__main__":
    sys.exit(main())
