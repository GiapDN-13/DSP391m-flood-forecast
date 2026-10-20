"""Mưa vệ tinh theo giờ / 30 phút qua Google Earth Engine — Report 3–4.

Thầy yêu cầu ô mịn hơn và bước thời gian theo giờ. Hai nguồn, đều 0,1° (~10 km),
đều từ 01/1998 tới gần hiện tại:

* **IMERG V07** (NASA, ``NASA/GPM_L3/IMERG_V07``) — 30 phút, band ``precipitation``
  (mm/giờ, đã hiệu chỉnh theo trạm đo ở bản Final).
* **GSMaP v8** (JAXA, ``JAXA/GPM_L3/GSMaP/v8/operational``) — 1 giờ, band
  ``hourlyPrecipRate`` (vệ tinh) và ``hourlyPrecipRateGC`` (hiệu chỉnh theo trạm đo).

Vì sao qua Earth Engine: máy chủ NASA chỉ cho tải nguyên file toàn cầu (7,8 MB mỗi
30 phút → ~4 TB cho 1998–2026) khi dịch vụ cắt vùng của họ lỗi. Earth Engine cắt
vùng phía máy chủ, mỗi tháng chỉ trả về ~150 nghìn dòng của khung ``FINE_BBOX``.

Cần đăng nhập một lần: ``python -c "import ee; ee.Authenticate()"``. Dự án Google
Cloud đã đăng ký Earth Engine lấy từ biến môi trường ``EE_PROJECT``.

    python -m src.ingest.gee_precip --dataset imerg
    python -m src.ingest.gee_precip --dataset gsmap --start 2020-10 --end 2020-11
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import polars as pl

from src import config as cfg

# Dự án Google Cloud đã đăng ký Earth Engine — đặt trong biến môi trường hoặc file
# .env (không commit), không ghi cứng vào repo.
EE_PROJECT_ENV = "EE_PROJECT"

# Lưới gốc của cả hai bộ: EPSG:4326, ô 0,1°. Lấy mẫu đúng tâm ô gốc, không nội suy.
NATIVE_CRS = "EPSG:4326"
NATIVE_TRANSFORM = [0.1, 0, -180, 0, -0.1, 90]

DATASETS = {
    "imerg": {
        "collection": "NASA/GPM_L3/IMERG_V07",
        "bands": {"precipitation": "precip_mm_hr"},
        "step_min": 30,
    },
    "gsmap": {
        "collection": "JAXA/GPM_L3/GSMaP/v8/operational",
        "bands": {"hourlyPrecipRate": "precip_mm_hr", "hourlyPrecipRateGC": "precip_gc_mm_hr"},
        "step_min": 60,
    },
}

FIRST_MONTH = "1998-01"
# Tháng kết thúc gần hơn ngần này ngày thì luôn tải lại (dữ liệu gần thời gian
# thực còn được bổ sung, IMERG Late → Final).
REFRESH_DAYS = 120
MAX_RETRIES = 5


def out_dir(dataset: str):
    return cfg.DATA_RAW / "gee" / dataset


def month_range(start: str, end: str) -> list[str]:
    """'1998-01' → '1998-03' ⇒ ['1998-01', '1998-02', '1998-03']."""
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    out = []
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def month_bounds(month: str) -> tuple[str, str]:
    """Khoảng [đầu tháng, đầu tháng sau) theo giờ UTC — Earth Engine lọc theo UTC."""
    y, m = map(int, month.split("-"))
    nxt = f"{y + 1:04d}-01-01" if m == 12 else f"{y:04d}-{m + 1:02d}-01"
    return f"{y:04d}-{m:02d}-01", nxt


def rows_to_frame(rows: list[list], bands: dict[str, str], step_min: int) -> pl.DataFrame:
    """Kết quả ``getRegion`` (hàng đầu là tên cột) → bảng dài.

    Earth Engine gắn mỗi ảnh với ĐẦU khoảng đo; ERA5 (Open-Meteo) và PERSIANN-CCS
    gắn với CUỐI giờ tích luỹ. Đổi về cuối khoảng (+ ``step_min``) để mọi nguồn
    ghép thẳng được với nhau.

    Cột: time_utc, time (giờ VN = UTC+7) — cả hai là CUỐI khoảng đo; lat, lon (tâm
    ô, làm tròn 2 chữ số); mỗi band một cột float32 (mm/giờ, cường độ trung bình
    trong khoảng — lượng mưa của khoảng = cường độ × step_min/60).
    """
    header, data = rows[0], rows[1:]
    df = pl.DataFrame(data, schema=header, orient="row")
    df = df.select(
        (pl.from_epoch(pl.col("time").cast(pl.Int64), time_unit="ms")
         + pl.duration(minutes=step_min)).alias("time_utc"),
        pl.col("latitude").cast(pl.Float64).round(2).alias("lat"),
        pl.col("longitude").cast(pl.Float64).round(2).alias("lon"),
        *[pl.col(b).cast(pl.Float32).alias(name) for b, name in bands.items()],
    )
    return (df.with_columns((pl.col("time_utc") + pl.duration(hours=7)).alias("time"))
              .select("time_utc", "time", "lat", "lon", *bands.values())
              .sort("time_utc", "lat", "lon"))


def fetch_month(ee, dataset: str, month: str) -> pl.DataFrame:
    spec = DATASETS[dataset]
    b = cfg.FINE_BBOX
    region = ee.Geometry.Rectangle([b["lon_min"], b["lat_min"], b["lon_max"], b["lat_max"]])
    start, end = month_bounds(month)
    ic = ee.ImageCollection(spec["collection"]).filterDate(start, end).select(list(spec["bands"]))
    rows = ic.getRegion(region, crs=NATIVE_CRS, crsTransform=NATIVE_TRANSFORM).getInfo()
    if len(rows) <= 1:
        return pl.DataFrame()
    return rows_to_frame(rows, spec["bands"], spec["step_min"])


def needs_fetch(path, month: str, today: date) -> bool:
    if not path.exists():
        return True
    _, nxt = month_bounds(month)
    return date.fromisoformat(nxt) > today - timedelta(days=REFRESH_DAYS)


def run(dataset: str, start: str, end: str, workers: int) -> None:
    import ee  # chỉ cần khi tải thật — test không phụ thuộc Earth Engine
    from dotenv import load_dotenv

    load_dotenv(cfg.ROOT / ".env")
    project = os.environ.get(EE_PROJECT_ENV)
    if not project:
        raise SystemExit(f"Thiếu {EE_PROJECT_ENV}: thêm dòng '{EE_PROJECT_ENV}=<id dự án>' "
                         f"vào {cfg.ROOT / '.env'} hoặc đặt biến môi trường.")
    ee.Initialize(project=project)
    dest = out_dir(dataset)
    dest.mkdir(parents=True, exist_ok=True)
    today = date.today()
    months = [m for m in month_range(start, end)
              if needs_fetch(dest / f"{dataset}_{m.replace('-', '')}.parquet", m, today)]
    print(f"[{dataset}] {len(months)} tháng cần tải ({start} → {end})", flush=True)

    def task(month: str) -> tuple[str, int]:
        path = dest / f"{dataset}_{month.replace('-', '')}.parquet"
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                df = fetch_month(ee, dataset, month)
                if df.height:
                    df.write_parquet(path, compression="zstd")
                return month, df.height
            except Exception as e:  # noqa: BLE001 — Earth Engine ném nhiều loại lỗi tạm thời
                if attempt == MAX_RETRIES:
                    raise
                wait = 5 * 2 ** attempt
                print(f"  {month} lỗi lần {attempt}: {str(e)[:120]} — chờ {wait}s", flush=True)
                time.sleep(wait)
        return month, 0

    t0, done, total_rows = time.time(), 0, 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(task, m) for m in months]
        for fut in as_completed(futures):
            try:
                month, n = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"  BỎ QUA sau {MAX_RETRIES} lần: {str(e)[:200]}", flush=True)
                continue
            done += 1
            total_rows += n
            if done % 12 == 0 or done == len(months):
                print(f"[{dataset} {done}/{len(months)}] {total_rows:,} dòng, "
                      f"{time.time() - t0:.0f}s", flush=True)
    size = sum(p.stat().st_size for p in dest.glob("*.parquet")) / 1e6
    print(f"XONG {dataset}: {total_rows:,} dòng mới, thư mục {size:.1f} MB", flush=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    p.add_argument("--start", default=FIRST_MONTH, help="YYYY-MM")
    p.add_argument("--end", default=date.today().strftime("%Y-%m"), help="YYYY-MM")
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args(argv)
    run(a.dataset, a.start, a.end, a.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
