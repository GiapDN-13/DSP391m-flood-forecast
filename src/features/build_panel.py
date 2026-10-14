"""Dựng bảng phân tích chuẩn `daily_panel.parquet` (FR-E4 … FR-E6) — DuckDB + Polars.

Ba bước, mỗi bước một công cụ phù hợp nhất:

1. **Gộp không gian bằng SQL (DuckDB):** 64 ô mưa → 3 tiểu lưu vực trong một
   câu `GROUP BY date` với `avg(...) FILTER (WHERE lat ...)`.
2. **Ghép bảng (Polars):** lưu lượng ⋈ mưa theo ngày.
3. **Tạo feature (Polars):** lag, tổng trượt, chỉ số ẩm nền, mã hoá mùa —
   tất cả là *biểu thức* Polars, chạy song song theo cột.

Mọi feature ở đây **chỉ được nhìn về quá khứ**. Rò rỉ thông tin tương lai là
lỗi chí mạng của bài toán chuỗi thời gian: nó không báo lỗi, làm kết quả đẹp
giả, và chỉ lộ ra khi bị hỏi lúc vấn đáp. Xem `tests/test_no_leakage.py`.

Bảng đầu ra được kiểm **trùng khớp với bản pandas cũ** trước khi thay thế
(`tests/test_build_panel_equivalence.py`).

    python -m src.features.build_panel          # panel Report 2 (từ 2010)
    python -m src.features.build_panel --ext    # panel Report 3 (từ 1997 + đất + hồ)
"""

from __future__ import annotations

import math
import sys

import duckdb
import polars as pl

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

def make_lags(df: pl.DataFrame, col: str, lags: list[int]) -> pl.DataFrame:
    """Thêm cột trễ. `{col}_lag{k}` tại ngày t là giá trị tại ngày t−k."""
    return df.with_columns(pl.col(col).shift(k).alias(f"{col}_lag{k}") for k in lags)


def make_rolling(df: pl.DataFrame, col: str, windows: list[int],
                 how: str = "mean") -> pl.DataFrame:
    """Trung bình/tổng trượt **trailing** — cửa sổ kết thúc tại ngày hiện tại.

    Cửa sổ của Polars mặc định nằm phía SAU (trailing), không có tuỳ chọn căn
    giữa nhầm lẫn kiểu `center=True` — cửa sổ căn giữa sẽ lấy cả giá trị của
    những ngày phía sau, tức là rò rỉ tương lai.
    """
    if how not in {"mean", "sum"}:
        raise ValueError(f"cách gộp không hỗ trợ: {how}")
    return df.with_columns(
        (_window_sum(col, w) / (w if how == "mean" else 1)).alias(f"{col}_roll{w}")
        for w in windows)


def _window_sum(col: str, w: int) -> pl.Expr:
    """Tổng của w ngày gần nhất, cộng THẲNG từng giá trị — không trượt.

    Không dùng `rolling_sum` vì thuật toán trượt (cộng giá trị mới vào, trừ giá
    trị cũ ra) để lại phần dư cỡ 1e-14: một cửa sổ toàn ngày không mưa cho ra
    1e-14 thay vì đúng 0. Với mô hình cây, "đúng 0" và "gần 0" là hai giá trị
    khác nhau — đã đo được: 76 ngày bị lệch kiểu này làm NSE của LightGBM đổi
    tới 0,009. Cửa sổ chỉ 3–7 ngày nên cộng thẳng vẫn nhanh.

    Phép `+` lan truyền giá trị thiếu, nên thiếu một ngày trong cửa sổ là kết
    quả thiếu — đúng nghĩa "cần đủ w ngày" (min_periods = w).
    """
    total = pl.col(col)
    for i in range(1, w):
        total = total + pl.col(col).shift(i)
    return total


def make_target(df: pl.DataFrame, horizon: int, col: str = "discharge") -> pl.DataFrame:
    """Biến mục tiêu: giá trị tại ngày t+horizon."""
    return df.with_columns(pl.col(col).shift(-horizon).alias(f"target_h{horizon}"))


def antecedent_index(col: str = "rain_basin", k: float = 0.9, n: int = 14) -> pl.Expr:
    """Chỉ số ẩm trước (API): API_t = Σ kⁱ · P_{t−i}, i = 1…n.

    Đại diện cho mức bão hoà của đất. Cùng một trận mưa, nền ẩm cao sẽ sinh
    lũ lớn hơn nhiều — đây là feature thuỷ văn quan trọng nhất ngoài mưa.
    Bắt đầu từ i = 1 nên không dùng mưa của chính ngày hiện tại.
    """
    return pl.sum_horizontal(
        (k ** i) * pl.col(col).shift(i).fill_null(0.0) for i in range(1, n + 1))


# ------------------------------------------------------- gộp không gian

def aggregate_rain(rain: pl.DataFrame) -> pl.DataFrame:
    """Gộp lưới mưa thành trung bình theo từng tiểu lưu vực — một câu SQL."""
    cols = ",\n".join(
        f"avg(rain) FILTER (WHERE lat >= {lo} AND lat < {hi}) AS rain_{name}"
        for name, (lo, hi) in SUBBASINS.items())
    out = duckdb.sql(f"SELECT date,\n{cols}\nFROM rain GROUP BY date ORDER BY date").pl()

    for name, (lo, hi) in SUBBASINS.items():
        n = rain.filter((pl.col("lat") >= lo) & (pl.col("lat") < hi)) \
                .select("lat", "lon").unique().height
        print(f"  {name:8} {n:3} điểm lưới")
    rain_cols = [f"rain_{n}" for n in SUBBASINS]
    return out.with_columns(pl.mean_horizontal(rain_cols).alias("rain_basin"))


# ------------------------------------------------- feature mở rộng (Report 3)

# Mùa lũ vận hành hồ chứa sông Hương bắt đầu 01/09 (QĐ 1606/QĐ-TTg, Điều 2):
# "năm thuỷ văn" tính từ 01/09.
HYDRO_YEAR_START_MONTH = 9


def ext_features() -> list[pl.Expr]:
    """Feature chỉ có ở panel mở rộng.

    Hồ chứa thượng nguồn (Tả Trạch, Bình Điền) cắt lũ khi còn chỗ trống và
    buộc phải xả khi đã đầy. Không có số liệu mực nước hồ công khai theo ngày,
    nên dùng hai đại lượng **đại diện cho mức đầy của hồ**, đều chỉ nhìn quá khứ:

    * tổng mưa 15 / 30 ngày — mưa kéo dài làm đầy hồ;
    * mưa tích luỹ từ 01/09 — đầu mùa hồ còn trống, cuối mùa hồ đầy và mọi trận
      mưa đi thẳng xuống hạ du.
    """
    hy = (pl.col("date").dt.year()
          + (pl.col("date").dt.month() >= HYDRO_YEAR_START_MONTH).cast(pl.Int32))
    return [
        _window_sum("rain_basin", 15).alias("rain_basin_roll15"),
        _window_sum("rain_basin", 30).alias("rain_basin_roll30"),
        pl.col("rain_basin").cum_sum().over(hy).alias("rain_season_cum"),
    ]


STORM_FAR_KM = 2000.0      # ngày không có bão trong bán kính 1 500 km


def join_context(df: pl.DataFrame) -> pl.DataFrame:
    """Ghép các yếu tố khí tượng quy mô lớn — mỗi nhóm là một cơ chế gây lũ khác nhau.

    * **Bão / ATNĐ** (IBTrACS): khoảng cách tới Huế, sức gió, đang tiến lại hay ra xa.
    * **Không khí lạnh + gió đông**: chênh khí áp Hà Nội − Huế (tăng vọt khi khối
      lạnh tràn về), gió đông bắc tại Huế, gió đông ngoài khơi.
    * **ENSO** (ONI): trễ 3 tháng — mùa ONI giữa tháng M−3 kết thúc tháng M−2,
      đã được công bố trước tháng M. Dùng số chưa công bố là rò rỉ.
    """
    met = clean.load_met_daily()
    storm = clean.load_storm_daily()
    oni = clean.load_oni()
    deg = math.pi / 180
    df = (df.join(met, on="date", how="left")
            .join(storm, on="date", how="left")
            .with_columns(pl.col("storm_dist_km").fill_null(STORM_FAR_KM),
                          pl.col("storm_wind_kt").fill_null(0.0)))
    m_lag = pl.col("date").dt.year() * 12 + pl.col("date").dt.month() - 1 - 3
    df = (df.with_columns(_ym=m_lag)
            .join(oni.with_columns(_ym=pl.col("year") * 12 + pl.col("month") - 1)
                     .select("_ym", pl.col("oni").alias("oni_lag3")),
                  on="_ym", how="left")
            .drop("_ym"))
    return df.with_columns(
        (pl.col("mslp_north") - pl.col("mslp_hue")).alias("mslp_grad_north"),
        pl.col("mslp_hue").diff(1).alias("mslp_hue_d1"),
        # thành phần gió THỔI TỪ hướng đông bắc (45°) / đông (90°), dương = đúng hướng
        (pl.col("wind_speed_hue") * ((pl.col("wind_dir_hue") - 45) * deg).cos())
            .alias("wind_ne_hue"),
        (pl.col("wind_speed_sea") * ((pl.col("wind_dir_sea") - 90) * deg).cos())
            .alias("wind_e_sea"),
        pl.col("storm_dist_km").diff(1).alias("storm_approach_km"),
    ).drop("wind_dir_hue", "wind_dir_north", "wind_dir_sea")


# ------------------------------------------------------------ dựng bảng

def build(ext: bool = False) -> pl.DataFrame:
    """`ext=True`: panel Report 3 — mưa từ 1997, thêm độ ẩm đất và feature hồ chứa."""
    lat, lon = cfg.RIVER_POINTS["huong_kim_long"]
    print(f"Ô lưới lưu lượng: ({lat}, {lon})")

    q = clean.load_discharge(lat, lon)
    folders = ("rain_daily_ext", "rain_daily") if ext else ("rain_daily",)
    rain = clean.load_rain_daily(folders)
    print("Gộp mưa theo tiểu lưu vực:")
    rain_agg = aggregate_rain(rain)

    df = q.join(rain_agg, on="date", how="inner").sort("date")
    if ext:
        df = df.join(clean.load_soil_daily(), on="date", how="left")
        df = join_context(df)
    print(f"\nGiao nhau: {df.height} ngày, {df['date'].min():%Y-%m-%d} → "
          f"{df['date'].max():%Y-%m-%d}")

    rain_cols = [c for c in df.columns if c.startswith("rain_")]

    # --- feature ---
    df = make_lags(df, "discharge", cfg.Q_LAGS)
    for c in rain_cols:
        df = make_lags(df, c, cfg.RAIN_LAGS)
        df = make_rolling(df, c, [3, 5, 7], how="sum")
    doy = pl.col("date").dt.ordinal_day()
    df = df.with_columns(
        antecedent_index("rain_basin").alias("api"),
        # biến thiên lưu lượng — bắt pha nước đang lên
        pl.col("discharge").diff(1).alias("q_diff1"),
        pl.col("discharge").diff(3).alias("q_diff3"),
        # mùa, mã hoá tuần hoàn để tháng 12 và tháng 1 nằm cạnh nhau
        (2 * math.pi * doy / 365.25).sin().alias("doy_sin"),
        (2 * math.pi * doy / 365.25).cos().alias("doy_cos"),
        pl.col("date").dt.month().cast(pl.Int32).alias("month"),
        pl.col("date").dt.month().is_in(cfg.FLOOD_SEASON_MONTHS).cast(pl.Int64).alias("mua_lu"),
    )

    if ext:
        df = df.with_columns(ext_features())

    # --- biến mục tiêu ---
    for h in cfg.HORIZONS:
        df = make_target(df, h)

    # --- nhãn: điền sau bởi src/features/risk_levels.py (mức nguy cơ theo phân vị) ---
    levels = getattr(cfg, "ALERT_LEVELS_Q", {}) or {}
    if levels:
        expr = pl.lit(0)
        for k, name in enumerate(("BD1", "BD2", "BD3"), start=1):
            if name in levels:
                expr = pl.when(pl.col("discharge") >= levels[name]).then(k).otherwise(expr)
        df = df.with_columns(expr.alias("alert_level"))
        print(f"Đã gán nhãn alert_level từ {levels}")
    else:
        df = df.with_columns(pl.lit(None, dtype=pl.Int8).alias("alert_level"))
        print("Cột alert_level để trống — chạy src/features/risk_levels.py để điền "
              "mức nguy cơ theo phân vị lưu lượng.")

    return df


def main() -> int:
    ext = "--ext" in sys.argv[1:]
    df = build(ext=ext)
    clean.validate_daily_index(df, require_continuous=True)

    dest = cfg.DATA_PROCESSED / ("daily_panel_ext.parquet" if ext else "daily_panel.parquet")
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest)

    print(f"\n→ {dest}")
    print(f"   {df.height} dòng × {df.width} cột")
    usable = df.drop_nulls(subset=[f"target_h{h}" for h in cfg.HORIZONS]
                           + [c for c in df.columns if "_lag" in c])
    print(f"   dùng được sau khi bỏ dòng thiếu đầu/cuối: {usable.height} dòng")
    print(f"   khoảng: {df['date'].min():%Y-%m-%d} → {df['date'].max():%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
