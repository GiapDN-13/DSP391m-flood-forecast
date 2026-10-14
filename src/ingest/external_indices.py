"""Hai nguồn ngoài Open-Meteo: bão (IBTrACS) và ENSO (ONI) — Report 3.

* **IBTrACS v04r01, lưu vực Tây Thái Bình Dương** (NOAA NCEI) — vị trí, sức gió
  của mọi cơn bão, 3–6 giờ một lần. File gốc ~115 MB; chỉ giữ các điểm từ 1996
  trong bán kính 1 500 km quanh Huế (vài trăm KB). Bão và áp thấp nhiệt đới là
  nguyên nhân của phần lớn trận lũ lớn trên sông Hương.
* **ONI** (NOAA CPC) — chỉ số El Niño / La Niña, trung bình trượt 3 tháng. Năm
  La Niña mùa lũ Trung Bộ thường nhiều mưa hơn (2020, 2022 đều là La Niña).

Cả hai là dữ liệu công khai, miễn phí, không cần tài khoản.

    python -m src.ingest.external_indices
"""

from __future__ import annotations

import math
import sys

import polars as pl
import requests

from src import config as cfg

IBTRACS_URL = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-"
               "climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.WP.list.v04r01.csv")
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

STORMS = cfg.DATA_RAW / "storms" / "ibtracs_wp_near_hue.parquet"
ONI = cfg.DATA_RAW / "indices" / "oni.parquet"

HUE = (16.46, 107.59)
STORM_RADIUS_KM = 1500
STORM_FIRST_SEASON = 1996

# Mùa ONI (3 tháng) → tháng ở GIỮA. DJF 1998 = 12/1997–02/1998, giữa là 01/1998.
SEASON_CENTER = {s: i + 1 for i, s in enumerate(
    ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"])}


def haversine_km(lat: pl.Expr, lon: pl.Expr, lat0: float, lon0: float) -> pl.Expr:
    r = math.pi / 180
    a = ((lat - lat0) * r / 2).sin() ** 2 + (
        math.cos(lat0 * r) * (lat * r).cos() * ((lon - lon0) * r / 2).sin() ** 2)
    return 2 * 6371.0 * a.sqrt().arcsin()


def fetch_storms() -> pl.DataFrame:
    raw = cfg.CACHE / "ibtracs.WP.list.v04r01.csv"
    if not raw.exists():
        print("  tải IBTrACS (~115 MB)…", flush=True)
        with requests.get(IBTRACS_URL, stream=True, timeout=120) as r:
            r.raise_for_status()
            tmp = raw.with_suffix(".tmp")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
            tmp.replace(raw)
    # Dòng thứ hai của file là đơn vị đo, không phải dữ liệu
    d = pl.read_csv(raw, skip_rows_after_header=1, infer_schema_length=0,
                    columns=["SID", "SEASON", "NAME", "ISO_TIME", "LAT", "LON",
                             "WMO_WIND", "USA_WIND"])
    num = lambda c: pl.col(c).str.strip_chars().cast(pl.Float64, strict=False)  # noqa: E731
    d = (d.with_columns(season=pl.col("SEASON").cast(pl.Int32), lat=num("LAT"),
                        lon=num("LON"), wind_kt=pl.coalesce(num("WMO_WIND"), num("USA_WIND")),
                        time_utc=pl.col("ISO_TIME").str.to_datetime("%Y-%m-%d %H:%M:%S"))
          .filter(pl.col("season") >= STORM_FIRST_SEASON)
          .with_columns(dist_km=haversine_km(pl.col("lat"), pl.col("lon"), *HUE))
          .filter(pl.col("dist_km") <= STORM_RADIUS_KM)
          # Quy ước giờ Việt Nam cho toàn dự án (FR-E1)
          .with_columns(date=(pl.col("time_utc") + pl.duration(hours=7)).dt.date())
          .select(pl.col("SID").alias("sid"), pl.col("NAME").alias("name"),
                  "time_utc", "date", "lat", "lon", "wind_kt", "dist_km")
          .sort("time_utc"))
    return d


def fetch_oni() -> pl.DataFrame:
    r = requests.get(ONI_URL, timeout=60)
    r.raise_for_status()
    rows = []
    for line in r.text.splitlines()[1:]:
        parts = line.split()
        if len(parts) == 4 and parts[0] in SEASON_CENTER:
            rows.append({"year": int(parts[1]), "month": SEASON_CENTER[parts[0]],
                         "oni": float(parts[3])})
    return pl.DataFrame(rows).sort("year", "month")


def main() -> int:
    for dest, fn in [(STORMS, fetch_storms), (ONI, fetch_oni)]:
        d = fn()
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        d.write_parquet(tmp)
        tmp.replace(dest)
        print(f"→ {dest.relative_to(cfg.ROOT)}  {d.height} dòng")
    s = pl.read_parquet(STORMS)
    print(f"  {s['sid'].n_unique()} cơn bão/ATNĐ đi vào bán kính {STORM_RADIUS_KM} km "
          f"từ {STORM_FIRST_SEASON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
