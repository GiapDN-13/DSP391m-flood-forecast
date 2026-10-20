"""Mưa THEO GIỜ theo lưu vực con → đặc trưng NGÀY cho mô hình ngày (Report 3).

Thầy yêu cầu dùng mưa theo giờ thay vì theo ngày. Mô hình vẫn dự báo lưu lượng
ngày (GloFAS là chuỗi ngày), nên mưa giờ được nén lại thành vài con số mỗi ngày
mà tổng ngày không thể hiện được: cường độ (max 1h/3h/6h trượt), độ kéo dài (số
giờ ≥ 1 mm), thời điểm (giờ đỉnh — mưa dồn cuối ngày chưa kịp tập trung về Kim
Long), mưa 24h tới 07h sáng (khớp giờ quan trắc mưa ngày của ngành KTTV) và mưa
tích luỹ 72h.

Ba bước, mỗi bước là hàm thuần (không đọc/ghi file):

1. :func:`basin_hourly` — lưới (time, lat, lon, precip) → chuỗi giờ theo 5 lưu
   vực con (trọng số diện tích của ``src/features/basins.py``) + toàn lưu vực
   ``basin`` = trung bình theo diện tích của 5 lưu vực con. Thiếu file lưu vực
   thì dùng 3 dải vĩ độ thuong/trung/ha giống ``build_panel.py`` (in cảnh báo).
2. :func:`daily_features` — chuỗi giờ → 9 đặc trưng/ngày/đơn vị, cột
   ``hr_{đặc trưng}_{đơn vị}``.
3. :func:`join_panel` — ghép vào ``daily_panel.parquet`` theo ngày.

Quy ước thời gian (đã kiểm 20/10/2026): ``time`` là giờ VN, nhãn = KẾT THÚC giờ
tích luỹ (ERA5 Open-Meteo, PERSIANN-CCS ``time``). Tổng các nhãn 00:00…23:00 của
ngày t trùng ``precipitation_sum`` ngày t trong ``data/raw/rain_daily`` tới
1e-13 mm (ô 16,3/107,6, 2019–2020) ⇒ cùng ranh giới ngày với panel.

KHÔNG rò rỉ tương lai: đặc trưng ngày t chỉ dùng các nhãn ≤ 23:00 ngày t
(``tests/test_hourly_features.py`` khoá điều này). Ngày thiếu dù một giờ thì
đặc trưng của ngày đó để trống (không nội suy).

Nguồn vệ tinh qua Earth Engine (``src/ingest/gee_precip.py``, 0,1°, 1998→):
``imerg`` (30 phút), ``gsmap`` và ``gsmap_gc`` (1 giờ, bản hiệu chỉnh trạm đo).
Nhãn ``time`` đã là CUỐI khoảng đo, giá trị là cường độ mm/giờ ⇒ :func:`to_hourly`
gộp IMERG về giờ: giờ kết thúc HH:00 = nửa giờ kết thúc HH−1:30 + nửa giờ kết
thúc HH:00, mỗi nửa = cường độ × 0,5 (thiếu một nửa → giờ đó trống). Sau đó
dùng nguyên pipeline trên ⇒ cùng định nghĩa đặc trưng và ranh giới ngày với
ERA5. Trọng số ô → lưu vực con: ``weights_gee_0p1.csv`` (lưới 10 × 10 ô phủ
100 % lưu vực Kim Long; 64 ô ERA5 chỉ phủ 92,5 %).

    python -m src.features.hourly_features --source era5   # → daily_panel_hourly.parquet
    python -m src.features.hourly_features --source pccs   # chạy thử + so với ERA5
    python -m src.features.hourly_features --source imerg  # → hourly_feats_imerg.parquet
    python -m src.features.hourly_features --source gsmap_gc
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time as _time
from pathlib import Path

import polars as pl

from src import config as cfg
from src.features import basins as bs

HOURLY_DIR = cfg.DATA_RAW / "rain_hourly"
PCCS_DIR = cfg.DATA_RAW / "persiann_ccs"
GEE_DIR = cfg.DATA_RAW / "gee"
PANEL = cfg.DATA_PROCESSED / "daily_panel.parquet"
OUT_PANEL = cfg.DATA_PROCESSED / "daily_panel_hourly.parquet"

# nguồn vệ tinh → (thư mục = tiền tố file, cột cường độ mm/giờ, số phút mỗi bước)
GEE = {"imerg": ("imerg", "precip_mm_hr", 30),
       "gsmap": ("gsmap", "precip_mm_hr", 60),
       "gsmap_gc": ("gsmap", "precip_gc_mm_hr", 60),
       # GSMaP_Gauge_NRT tải thẳng từ JAXA (src/ingest/gsmap_nrt.py) — cùng lưới 0,1°
       # tâm x,x5 với bản Earth Engine, nhưng là sản phẩm gần thời gian thực (trễ ~4,7 h)
       "gsmap_nrt": ("gsmap_nrt", "precip_gc_mm_hr", 60)}
# thư mục gốc riêng của nguồn không lấy từ Earth Engine
SAT_ROOT = {"gsmap_nrt": cfg.DATA_RAW}
SOURCES = ("era5", "pccs", *GEE)
GEE_GRID = "gee_0p1"

WEIGHTS = {"era5": bs.BASIN_DIR / "weights_era5_0p1.csv",
           "pccs": bs.BASIN_DIR / "weights_pccs_0p04.csv",
           **dict.fromkeys(GEE, bs.BASIN_DIR / f"weights_{GEE_GRID}.csv")}


def feats_path(source: str) -> Path:
    """Đặc trưng ngày của một nguồn vệ tinh (date + 54 cột hr_*)."""
    return cfg.DATA_PROCESSED / f"hourly_feats_{source}.parquet"
SUBBASIN_GEOJSON = bs.BASIN_DIR / "subbasins.geojson"

PREFIX = "hr_"
WHOLE = "basin"                  # đơn vị toàn lưu vực (giống hậu tố rain_basin)
FEATS = ("sum", "max1h", "max3h", "max6h", "nh1mm",
         "peak_sin", "peak_cos", "r24_7h", "r72h")
WET_MM = 1.0                     # ngưỡng "giờ có mưa"
PEAK_MIN_MM = 0.1                # max giờ dưới mức này → coi như không có đỉnh, sin = cos = 0
OBS_HOUR = 7                     # mưa ngày quan trắc: 07h hôm trước → 07h hôm nay

# Dự phòng khi chưa chia được lưu vực con — đúng 3 dải vĩ độ của build_panel.py
BANDS = {"thuong": (16.10, 16.35), "trung": (16.35, 16.55), "ha": (16.55, 16.85)}


def feature_names(units) -> list[str]:
    """Tên cột theo thứ tự ``hr_{đặc trưng}_{đơn vị}``."""
    return [f"{PREFIX}{f}_{u}" for u in units for f in FEATS]


# ================================================================ trọng số

def band_weights(lats, lons) -> pl.DataFrame:
    """Trọng số dự phòng: mỗi ô trong dải vĩ độ có trọng số bằng nhau."""
    rows = []
    for name, (lo, hi) in BANDS.items():
        cells = sorted({(round(float(a), 4), round(float(b), 4))
                        for a, b in zip(lats, lons) if lo <= a < hi})
        rows += [(name, a, b, 1.0 / len(cells)) for a, b in cells]
    return pl.DataFrame(rows, schema={"subbasin": pl.Utf8, "lat": pl.Float64,
                                      "lon": pl.Float64, "weight": pl.Float64}, orient="row")


def load_weights(source: str, cells: pl.DataFrame | None = None
                 ) -> tuple[pl.DataFrame, dict[str, float], str]:
    """(trọng số ô → đơn vị, diện tích từng đơn vị, mô tả cách gộp).

    Ưu tiên lưu vực con của ``basins.py``; thiếu file thì về 3 dải vĩ độ (cần
    ``cells`` = các ô lat/lon có trong dữ liệu) với diện tích bằng nhau ⇒ toàn
    lưu vực = trung bình 3 dải, đúng như ``rain_basin`` của panel.
    """
    wpath = WEIGHTS[source]
    if wpath.exists() and SUBBASIN_GEOJSON.exists():
        fc = json.loads(SUBBASIN_GEOJSON.read_text(encoding="utf-8"))
        areas = {f["properties"]["name"]: float(f["properties"]["area_km2"])
                 for f in fc["features"]}
        return pl.read_csv(wpath), areas, f"lưu vực con DEM ({wpath.name})"
    if cells is None:
        raise FileNotFoundError(f"thiếu {wpath} và không có danh sách ô để dùng dải vĩ độ")
    print(f"⚠️ Không có {wpath.name}/subbasins.geojson → dùng 3 dải vĩ độ thuong/trung/ha "
          "(giống build_panel.py), KHÔNG phải lưu vực con thật.")
    return (band_weights(cells["lat"].to_list(), cells["lon"].to_list()),
            dict.fromkeys(BANDS, 1.0), "3 dải vĩ độ (dự phòng)")


# ================================================================ lưới → lưu vực

def _full_hours(df: pl.DataFrame) -> pl.DataFrame:
    """Lưới giờ liên tục từ 00:00 ngày đầu tới 23:00 ngày cuối (giờ thiếu = null)
    — cần để ``shift(k)`` đúng là k giờ trước."""
    t0 = df["time"].min().replace(hour=0, minute=0, second=0, microsecond=0)
    t1 = df["time"].max().replace(hour=23, minute=0, second=0, microsecond=0)
    grid = pl.DataFrame({"time": pl.datetime_range(t0, t1, "1h", eager=True,
                                                   time_unit=df.schema["time"].time_unit)})
    return grid.join(df, on="time", how="left").sort("time")


def basin_hourly(df_long: pl.DataFrame, weights: pl.DataFrame,
                 areas: dict[str, float], value_col: str = "precip") -> pl.DataFrame:
    """(time, lat, lon, value) → bảng rộng ``time`` + một cột mỗi đơn vị + ``basin``.

    Trong một lưu vực con: trung bình có trọng số diện tích, ô thiếu thì chia lại
    trọng số (``basins.basin_mean``). Toàn lưu vực: trung bình 5 lưu vực con theo
    diện tích; giờ nào thiếu một lưu vực con thì để trống.
    """
    units = list(areas)
    w = bs.basin_mean(df_long, weights, value_col, "time", wide=True)
    w = w.rename({f"{value_col}_{u}": u for u in units if f"{value_col}_{u}" in w.columns})
    for u in units:                                   # lưu vực không có ô nào
        if u not in w.columns:
            w = w.with_columns(pl.lit(None, dtype=pl.Float64).alias(u))
    tot = sum(areas.values())
    w = w.with_columns(pl.sum_horizontal([pl.col(u) * (areas[u] / tot) for u in units])
                       .alias(WHOLE))
    w = w.with_columns(pl.when(pl.any_horizontal([pl.col(u).is_null() for u in units]))
                       .then(None).otherwise(pl.col(WHOLE)).alias(WHOLE))
    return _full_hours(w.select("time", *units, WHOLE))


# ================================================================ giờ → ngày

def _shift_sum(col: str, w: int) -> pl.Expr:
    """Tổng w giờ kết thúc tại giờ hiện tại, cộng thẳng (không trượt cộng-trừ để
    tránh dư 1e-14, cùng lý do với ``build_panel._window_sum``)."""
    e = pl.col(col)
    for i in range(1, w):
        e = e + pl.col(col).shift(i)
    return e


def _strict(e: pl.Expr, col: str) -> pl.Expr:
    """Giá trị gộp chỉ hợp lệ khi KHÔNG thiếu giờ nào trong nhóm."""
    return pl.when(pl.col(col).null_count() == 0).then(e).otherwise(None)


def daily_features(hourly: pl.DataFrame, units: list[str] | None = None) -> pl.DataFrame:
    """Bảng giờ rộng (``time`` + một cột mưa mỗi đơn vị) → đặc trưng ngày.

    Với mỗi đơn vị ``u`` (cột ``hr_{f}_{u}``):

    * ``sum`` tổng nhãn 00…23h; ``max1h``; ``max3h``/``max6h`` = max tổng trượt
      3/6 giờ KẾT THÚC trong ngày (cửa sổ có thể bắt đầu từ cuối ngày trước);
    * ``nh1mm`` số giờ ≥ 1 mm; ``peak_sin/cos`` giờ của max 1h (trùng thì lấy giờ
      sớm nhất), = 0 nếu max < 0,1 mm;
    * ``r24_7h`` tổng các nhãn 08h ngày t−1 … 07h ngày t;
    * ``r72h`` tổng 72 giờ tới 23h ngày t (= tổng ngày t, t−1, t−2).

    Mọi đặc trưng chỉ dùng nhãn ≤ 23:00 ngày t. Thiếu giờ → null.
    """
    units = units or [c for c in hourly.columns if c != "time"]
    h = _full_hours(hourly.select("time", *units))
    h = h.with_columns(pl.col("time").dt.date().alias("date"),
                       pl.col("time").dt.hour().cast(pl.Int32).alias("_hour"),
                       # ngày quan trắc 07h: nhãn (t−1 08h … t 07h] → t
                       (pl.col("time") + pl.duration(hours=23 - OBS_HOUR)).dt.date().alias("_obs"),
                       *[_shift_sum(u, 3).alias(f"_r3_{u}") for u in units],
                       *[_shift_sum(u, 6).alias(f"_r6_{u}") for u in units])

    aggs = []
    for u in units:
        mx = pl.col(u).max()
        ang = 2 * math.pi * pl.col("_hour").get(pl.col(u).arg_max()).cast(pl.Float64) / 24
        aggs += [
            _strict(pl.col(u).sum(), u).alias(f"{PREFIX}sum_{u}"),
            _strict(mx, u).alias(f"{PREFIX}max1h_{u}"),
            _strict(pl.col(f"_r3_{u}").max(), f"_r3_{u}").alias(f"{PREFIX}max3h_{u}"),
            _strict(pl.col(f"_r6_{u}").max(), f"_r6_{u}").alias(f"{PREFIX}max6h_{u}"),
            _strict((pl.col(u) >= WET_MM).sum().cast(pl.Float64), u).alias(f"{PREFIX}nh1mm_{u}"),
            _strict(pl.when(mx >= PEAK_MIN_MM).then(ang.sin()).otherwise(0.0), u)
            .alias(f"{PREFIX}peak_sin_{u}"),
            _strict(pl.when(mx >= PEAK_MIN_MM).then(ang.cos()).otherwise(0.0), u)
            .alias(f"{PREFIX}peak_cos_{u}"),
        ]
    day = h.group_by("date").agg(*aggs).sort("date")

    obs = (h.group_by("_obs")
            .agg(*[pl.when((pl.len() == 24) & (pl.col(u).null_count() == 0))
                   .then(pl.col(u).sum()).otherwise(None).alias(f"{PREFIX}r24_7h_{u}")
                   for u in units])
            .rename({"_obs": "date"}))
    day = day.join(obs, on="date", how="left")
    # ngày liên tục (lưới giờ đầy đủ) ⇒ shift(1) đúng là hôm trước
    day = day.with_columns(*[(pl.col(f"{PREFIX}sum_{u}")
                              + pl.col(f"{PREFIX}sum_{u}").shift(1)
                              + pl.col(f"{PREFIX}sum_{u}").shift(2)).alias(f"{PREFIX}r72h_{u}")
                             for u in units])
    return day.select("date", *feature_names(units))


def hourly_features(df_long: pl.DataFrame, weights: pl.DataFrame,
                    areas: dict[str, float], value_col: str = "precip") -> pl.DataFrame:
    """Lưới giờ dạng dài → đặc trưng ngày cho từng lưu vực con và toàn lưu vực."""
    hb = basin_hourly(df_long, weights, areas, value_col)
    return daily_features(hb, [*areas, WHOLE])


def join_panel(panel: pl.DataFrame, feats: pl.DataFrame) -> pl.DataFrame:
    """Ghép đặc trưng giờ vào panel ngày (left join theo ngày, giữ kiểu cột date
    của panel). Ngày trước khi có mưa giờ → null."""
    f = feats.with_columns(pl.col("date").cast(pl.Date).alias("_d")).drop("date")
    out = (panel.with_columns(pl.col("date").cast(pl.Date).alias("_d"))
                .join(f, on="_d", how="left").drop("_d"))
    if out.height != panel.height:
        raise AssertionError("ghép làm đổi số dòng panel — trùng ngày trong đặc trưng giờ?")
    return out


# ================================================================ nạp dữ liệu

def load_era5(years: list[int] | None = None, cells: pl.DataFrame | None = None) -> pl.DataFrame:
    """ERA5 theo giờ (data/raw/rain_hourly) → (time, lat, lon, precip)."""
    files = sorted(HOURLY_DIR.glob("rh_*.parquet"))
    if years:
        files = [f for f in files if int(f.stem.rsplit("_", 1)[1]) in set(years)]
    if not files:
        raise FileNotFoundError(f"không có file mưa giờ trong {HOURLY_DIR}")
    lf = (pl.scan_parquet(files)
            .select("time", pl.col("lat").round(4), pl.col("lon").round(4),
                    pl.col("precipitation").cast(pl.Float64).alias("precip")))
    if cells is not None:
        lf = lf.join(cells.lazy().select(pl.col("lat").round(4), pl.col("lon").round(4)).unique(),
                     on=["lat", "lon"], how="semi")
    return lf.collect().sort("time", "lat", "lon")


def load_pccs(months: list[str] | None = None) -> pl.DataFrame:
    """PERSIANN-CCS (data/raw/persiann_ccs/pccs_YYYYMM.parquet) → (time, lat, lon, precip)."""
    files = sorted(PCCS_DIR.glob("pccs_*.parquet"))
    if months:
        files = [f for f in files if f.stem.split("_")[1] in set(months)]
    if not files:
        raise FileNotFoundError(f"không có file PERSIANN-CCS trong {PCCS_DIR}")
    return (pl.scan_parquet(files)
              .select("time", pl.col("lat").round(4), pl.col("lon").round(4),
                      pl.col("precip_mm").cast(pl.Float64).alias("precip"))
              .collect().sort("time", "lat", "lon"))


def to_hourly(df: pl.DataFrame, step_min: int, value_col: str = "precip") -> pl.DataFrame:
    """Cường độ mm/giờ theo bước ``step_min`` phút (nhãn CUỐI bước) → lượng mưa
    giờ (mm), nhãn CUỐI giờ.

    Bước kết thúc lúc L thuộc giờ kết thúc ⌈L⌉ (làm tròn LÊN tới giờ tròn): với
    IMERG, giờ HH:00 = nửa giờ kết thúc HH−1:30 + nửa giờ kết thúc HH:00 (nửa
    giờ kết thúc 23:30 ngày t thuộc giờ 00:00 ngày t+1). Lượng mưa mỗi bước =
    cường độ × step_min/60. Giờ thiếu dù một bước (hoặc bước null) → null.
    """
    if step_min <= 0 or 60 % step_min:
        raise ValueError("step_min phải là ước của 60")
    bad = df.filter((pl.col("time").dt.minute() % step_min != 0) | (pl.col("time").dt.second() != 0))
    if bad.height:
        raise ValueError(f"nhãn thời gian lệch bước {step_min} phút: {bad['time'][0]}")
    amount = pl.col(value_col).cast(pl.Float64) * (step_min / 60)
    if step_min == 60:
        return df.select("time", "lat", "lon", amount.alias(value_col)).sort("time", "lat", "lon")
    n = 60 // step_min
    hour = (pl.col("time") - pl.duration(minutes=step_min)).dt.truncate("1h") + pl.duration(hours=1)
    return (df.with_columns(hour.alias("_h"))
              .group_by("_h", "lat", "lon")
              .agg(pl.when((pl.len() == n) & (pl.col(value_col).null_count() == 0))
                   .then(amount.sum()).otherwise(None).alias(value_col))
              .rename({"_h": "time"})
              .select("time", "lat", "lon", value_col)
              .sort("time", "lat", "lon"))


def load_gee(source: str, months: list[str] | None = None, years: list[int] | None = None,
             cells: pl.DataFrame | None = None, hourly: bool = True) -> pl.DataFrame:
    """IMERG/GSMaP (``data/raw/gee/<thư mục>/<tiền tố>_YYYYMM.parquet``) → (time, lat, lon, precip).

    ``time`` = giờ VN, nhãn CUỐI khoảng. ``hourly=True``: lượng mưa giờ (mm) qua
    :func:`to_hourly`; ``False``: giữ bước gốc, ``precip`` vẫn là cường độ mm/giờ.
    ``cells``: chỉ giữ các ô này (ô chạm lưu vực trong bảng trọng số).
    File theo tháng UTC: giờ 00–07 VN ngày 1 nằm ở file tháng trước, mỗi giờ VN
    (= giờ UTC + 7) luôn đủ hai nửa trong cùng một file.
    """
    folder, col, step = GEE[source]
    base = SAT_ROOT.get(source, GEE_DIR) / folder
    # file tháng <tiền tố>_YYYYMM + (nguồn JAXA) ngày lẻ chưa gộp _parts/YYYYMMDD
    files = sorted(base.glob(f"{folder}_*.parquet")) + sorted((base / "_parts").glob("*.parquet"))

    def ym(f: Path) -> str:
        return f.stem[-6:] if f.stem.startswith(folder) else f.stem[:6]

    if months:
        keep = {m.replace("-", "") for m in months}
        files = [f for f in files if ym(f) in keep]
    if years:
        files = [f for f in files if int(ym(f)[:4]) in set(years)]
    if not files:
        raise FileNotFoundError(f"không có file {folder} trong {base} — chạy "
                                f"`python -m src.ingest.gee_precip --dataset {folder}` "
                                f"hoặc `python -m src.ingest.gsmap_nrt`")
    lf = (pl.scan_parquet(files)
            .select("time", pl.col("lat").round(4), pl.col("lon").round(4),
                    # NaN (ô thiếu của JAXA) → null để basin_mean chia lại trọng số
                    pl.col(col).cast(pl.Float64).fill_nan(None).alias("precip")))
    if cells is not None:
        lf = lf.join(cells.lazy().select(pl.col("lat").round(4), pl.col("lon").round(4)).unique(),
                     on=["lat", "lon"], how="semi")
    raw = lf.collect()
    if raw.select(pl.struct("time", "lat", "lon").is_duplicated().any()).item():
        raise ValueError(f"{source}: trùng (time, lat, lon) — file tháng chồng lấn?")
    return to_hourly(raw, step) if hourly else raw.sort("time", "lat", "lon")


def _cells(df: pl.DataFrame) -> pl.DataFrame:
    return df.select("lat", "lon").unique()


def build_source(source: str, years: list[int] | None = None,
                 months: list[str] | None = None) -> tuple[pl.DataFrame, pl.DataFrame, str]:
    """Nạp nguồn + trọng số → (chuỗi giờ theo đơn vị, đặc trưng ngày, mô tả)."""
    if source == "era5":
        w_try = pl.read_csv(WEIGHTS["era5"]) if WEIGHTS["era5"].exists() else None
        raw = load_era5(years, cells=w_try)
    elif source in GEE:
        if not WEIGHTS[source].exists():
            bs.write_grid_weights(GEE_GRID)
        raw = load_gee(source, months, years, cells=pl.read_csv(WEIGHTS[source]))
    else:
        raw = load_pccs(months)
    weights, areas, how = load_weights(source, _cells(raw))
    hb = basin_hourly(raw, weights, areas)
    return hb, daily_features(hb, [*areas, WHOLE]), how


def check_daily_sum(source: str, feats: pl.DataFrame, months: list[str] | None = None,
                    years: list[int] | None = None) -> pl.DataFrame:
    """Kiểm ranh giới ngày của nguồn vệ tinh bằng đường tính KHÁC: tổng ngày lấy
    thẳng từ bước gốc (không qua bảng giờ, không qua :func:`to_hourly`) — bước k
    phút kết thúc lúc L thuộc ngày ``date(L + 60 − k phút)`` — từng ô → lưu vực
    (cùng trọng số) rồi so với ``hr_sum_*``. Chỉ ngày có đủ 24·60/k bước."""
    _, _, step = GEE[source]
    w, areas, _ = load_weights(source)
    raw = load_gee(source, months, years, cells=w, hourly=False)
    per_cell = (raw.with_columns((pl.col("time") + pl.duration(minutes=60 - step)).dt.date()
                                 .alias("date"))
                   .group_by("date", "lat", "lon")
                   .agg((pl.col("precip") * (step / 60)).sum().alias("precip"),
                        pl.len().alias("_n"))
                   .filter(pl.col("_n") == 24 * 60 // step))
    d = bs.basin_mean(per_cell, w, "precip", "date", wide=True)
    d = d.rename({f"precip_{u}": u for u in areas})
    tot = sum(areas.values())
    d = d.with_columns(pl.sum_horizontal([pl.col(u) * (areas[u] / tot) for u in areas]).alias(WHOLE))
    j = feats.join(d, on="date", how="inner")
    rows = []
    for u in [*areas, WHOLE]:
        x = j.select(pl.col(f"{PREFIX}sum_{u}").alias("a"), pl.col(u).alias("b")).drop_nulls()
        rows.append({"unit": u, "n_days": x.height,
                     "max_abs_diff_mm": x.select((pl.col("a") - pl.col("b")).abs().max()).item(),
                     "total_hr_sum_mm": x["a"].sum(), "total_direct_mm": x["b"].sum()})
    return pl.DataFrame(rows)


# ================================================================ so sánh nguồn

def compare(hb_a: pl.DataFrame, hb_b: pl.DataFrame, fa: pl.DataFrame, fb: pl.DataFrame,
            units: list[str]) -> pl.DataFrame:
    """So nguồn b với nguồn a trên giờ/ngày CHUNG, theo từng đơn vị: tổng, tỷ lệ
    tổng b/a, tương quan giờ và ngày."""
    rows = []
    hj = hb_a.join(hb_b, on="time", suffix="_b").drop_nulls()
    dj = fa.join(fb, on="date", suffix="_b")
    for u in units:
        s = f"{PREFIX}sum_{u}"
        d = dj.select(s, f"{s}_b").drop_nulls()
        rows.append({
            "unit": u, "n_hours": hj.height, "n_days": d.height,
            "total_a_mm": d[s].sum(), "total_b_mm": d[f"{s}_b"].sum(),
            "ratio_b_a": d[f"{s}_b"].sum() / d[s].sum() if d[s].sum() else float("nan"),
            "r_hour": hj.select(pl.corr(u, f"{u}_b")).item(),
            "r_day": d.select(pl.corr(s, f"{s}_b")).item(),
            "max1h_a": dj[f"{PREFIX}max1h_{u}"].max(), "max1h_b": dj[f"{PREFIX}max1h_{u}_b"].max(),
        })
    return pl.DataFrame(rows)


def subbasin_corr(hb: pl.DataFrame, units: list[str]) -> pl.DataFrame:
    """Tương quan giờ giữa các lưu vực con — cho biết nguồn mưa có thật sự phân
    biệt được lưu vực con hay không (ERA5 gốc ~0,25°)."""
    d = hb.select(units).drop_nulls()
    return pl.DataFrame([{"a": a, "b": b, "r": d.select(pl.corr(a, b)).item()}
                         for i, a in enumerate(units) for b in units[i + 1:]])


# ================================================================ CLI

def _elapsed(t0: float) -> str:
    return f"{_time.time() - t0:.1f} s"


def _month(df: pl.DataFrame, col: str, ym: tuple[int, int]) -> pl.DataFrame:
    """Lọc một tháng theo NGÀY (giờ 00…23 thuộc ngày của nó, cùng ranh giới với tổng ngày)."""
    d = pl.col(col).dt.date() if isinstance(df.schema[col], pl.Datetime) else pl.col(col)
    return df.filter((d.dt.year() == ym[0]) & (d.dt.month() == ym[1]))


def _print_table(df: pl.DataFrame) -> None:
    with pl.Config(tbl_rows=60, tbl_cols=20, float_precision=3, tbl_width_chars=160):
        print(df)


def _main_gee(a, hb: pl.DataFrame, feats: pl.DataFrame, units: list[str]) -> int:
    """Nguồn vệ tinh: độ phủ lưới, kiểm tổng ngày bằng đường tính khác, ghi đặc trưng."""
    cov = bs.grid_coverage(*bs.mesh(*bs.gee_centers()), bs.GEE_STEP)
    kl = cov.filter(pl.col("subbasin") == "huong_kim_long").row(0, named=True)
    print(f"Lưới 0,1° (10 × 10 ô) phủ {kl['covered_pct']:.1f} % lưu vực Kim Long "
          f"({kl['covered_km2']:.1f}/{kl['area_km2']:.1f} km²)")
    n_null = feats.filter(pl.col(f"{PREFIX}sum_{WHOLE}").is_null()).height
    print(f"Ngày thiếu giờ (đặc trưng trống): {n_null}")

    t0 = _time.time()
    chk = check_daily_sum(a.source, feats, years=a.years)
    print(f"\nKiểm ranh giới ngày — hr_sum (qua bảng giờ) so với tổng ngày tính thẳng từ "
          f"bước gốc ({_elapsed(t0)}):")
    _print_table(chk)
    print(f"Chênh lớn nhất: {chk['max_abs_diff_mm'].max():.2e} mm")
    if chk["max_abs_diff_mm"].max() > 1e-6:
        raise AssertionError("tổng ngày lệch > 1e-6 mm — kiểm lại quy ước nhãn cuối khoảng")

    dest = a.out or feats_path(a.source)
    dest.parent.mkdir(parents=True, exist_ok=True)
    feats.write_parquet(dest)
    print(f"\n→ {dest} — {feats.height} ngày × {feats.width - 1} cột "
          f"({feats['date'].min()} → {feats['date'].max()})")
    print(f"\nTương quan giờ giữa các lưu vực con ({a.source}):")
    _print_table(subbasin_corr(hb, [u for u in units if u != WHOLE]).sort("r"))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", choices=SOURCES, default="era5")
    ap.add_argument("--years", type=int, nargs="*", help="chỉ các năm này (era5, imerg, gsmap*)")
    ap.add_argument("--out", type=Path, default=None,
                    help="era5: panel đầu ra (mặc định daily_panel_hourly.parquet); "
                         "pccs: nếu có thì ghi đặc trưng ngày PERSIANN-CCS ra đây; "
                         "imerg/gsmap/gsmap_gc: mặc định hourly_feats_<nguồn>.parquet")
    a = ap.parse_args(argv)

    t0 = _time.time()
    hb, feats, how = build_source(a.source, years=a.years)
    units = [c for c in hb.columns if c != "time"]
    print(f"Nguồn {a.source}: {hb.height} giờ ({hb['time'].min()} → {hb['time'].max()}), "
          f"gộp theo {how}; {len(units)} đơn vị: {', '.join(units)}")
    print(f"Đặc trưng ngày: {feats.height} ngày × {feats.width - 1} cột "
          f"({_elapsed(t0)})")

    if a.source in GEE:
        return _main_gee(a, hb, feats, units)

    if a.source == "era5":
        panel = pl.read_parquet(PANEL)
        out = join_panel(panel, feats)
        dest = a.out or OUT_PANEL
        dest.parent.mkdir(parents=True, exist_ok=True)
        out.write_parquet(dest)
        newc = feature_names(units)
        n_ok = out.filter(pl.col(f"{PREFIX}max3h_{WHOLE}").is_not_null()).height
        print(f"\n→ {dest} — {out.height} dòng × {out.width} cột "
              f"(+{len(newc)} cột giờ; {n_ok} ngày có đặc trưng giờ, "
              f"{dest.stat().st_size / 1e6:.2f} MB)")
        chk = out.select(pl.corr(f"{PREFIX}sum_{WHOLE}", "rain_basin").alias("r_ngay"),
                         (pl.col(f"{PREFIX}sum_{WHOLE}").sum()
                          / pl.col("rain_basin").filter(pl.col(f"{PREFIX}sum_{WHOLE}")
                                                        .is_not_null()).sum()).alias("ty_le"))
        print(f"Kiểm tra: hr_sum_basin (lưu vực DEM) so với rain_basin (3 dải vĩ độ) — "
              f"r = {chk['r_ngay'].item():.3f}, tỷ lệ tổng = {chk['ty_le'].item():.3f}")
        print("\nTương quan giờ giữa các lưu vực con (ERA5):")
        _print_table(subbasin_corr(hb, [u for u in units if u != WHOLE]).sort("r"))
        return 0

    # --- pccs: chạy thử pipeline + so với ERA5 cùng thời gian ---
    years = sorted({t.year for t in (hb["time"].min(), hb["time"].max())})
    hb_e, fe, how_e = build_source("era5", years=list(range(years[0], years[-1] + 1)))
    hb_e = hb_e.filter(pl.col("time").is_between(hb["time"].min(), hb["time"].max()))
    print(f"So với ERA5 ({how_e}) trên giờ/ngày chung — b = PERSIANN-CCS, a = ERA5:")
    _print_table(compare(hb_e, hb, fe, feats, units))
    for ym in sorted({(d.year, d.month) for d in feats["date"]}):
        c = compare(_month(hb_e, "time", ym), _month(hb, "time", ym),
                    _month(fe, "date", ym), _month(feats, "date", ym), units)
        if c["n_days"].max() > 0:
            print(f"\nTháng {ym[0]}-{ym[1]:02d}:")
            _print_table(c.select("unit", "n_days", "total_a_mm", "total_b_mm", "ratio_b_a",
                                  "r_hour", "r_day"))
    print("\nTương quan giờ giữa các lưu vực con (PERSIANN-CCS):")
    _print_table(subbasin_corr(hb, [u for u in units if u != WHOLE]).sort("r"))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        feats.write_parquet(a.out)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
