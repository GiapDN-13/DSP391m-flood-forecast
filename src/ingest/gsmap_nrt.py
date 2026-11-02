"""Mưa GSMaP_Gauge_NRT v8 theo giờ từ FTP của JAXA — nguồn dùng được khi chạy thật.

Vì sao cần: bản GSMaP trên Earth Engine (``gee_precip.py``) sau ~3 ngày được thay
bằng **bản chuẩn** (MVK) — kiểm 21/10/2026: trùng tuyệt đối với
``standard/v8/hourly_G`` của JAXA. Bản chuẩn trễ ~3 ngày, Earth Engine trễ ~27 giờ
⇒ job 05h sáng không có mưa của hôm qua, và walk-forward cho thấy khi trễ 1 ngày
thì mức tăng mất hết. Bản **NRT** công bố trễ ~4,7 giờ nhưng là sản phẩm KHÁC
(tương quan từng giờ với bản chuẩn 0,6–0,8) ⇒ phải huấn luyện lại bằng chính
lịch sử NRT. JAXA lưu NRT v8 xử lý lại từ 1998.

File gốc: ``realtime_ver/v8/hourly_G/YYYY/MM/DD/gsmap_gauge.YYYYMMDD.HH00.dat.gz``
— float32 little-endian 1200 × 3600, ô 0,1°, tâm ô lat 59,95 → −59,95,
lon 0,05 → 359,95, mm/giờ, giá trị âm = thiếu. ``HH`` là ĐẦU giờ UTC.

Mỗi file (1,2 MB) được tải vào bộ nhớ, cắt ``FINE_BBOX`` (10 × 10 ô) rồi bỏ —
không ghi file tạm. Kết quả: ``data/raw/gsmap_nrt/gsmap_nrt_YYYYMM.parquet``,
cột time_utc, time (CUỐI giờ, giờ VN = UTC+7 — cùng quy ước ERA5/GEE), lat, lon,
precip_gc_mm_hr. Ghi từng ngày vào ``_parts/`` để chạy lại là tiếp tục; đủ ngày
của tháng thì gộp thành file tháng.

Tài khoản trong ``.env`` (không commit): ``JAXA_HOST``, ``JAXA_USER``, ``JAXA_PASS``.

    python -m src.ingest.gsmap_nrt --start 1998-01-01 --end 2026-10-19 --workers 6
"""

from __future__ import annotations

import argparse
import calendar
import ftplib
import gzip
import io
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta

import numpy as np
import polars as pl

from src import config as cfg

OUT = cfg.DATA_RAW / "gsmap_nrt"
PARTS = OUT / "_parts"
MANIFEST = OUT / "_missing.jsonl"
REMOTE = "realtime_ver/v8/hourly_G/{d:%Y/%m/%d}/gsmap_gauge.{d:%Y%m%d}.{h:02d}00.dat.gz"

NLAT, NLON, STEP = 1200, 3600, 0.1
LAT = 59.95 - STEP * np.arange(NLAT)
LON = 0.05 + STEP * np.arange(NLON)
MAX_RETRIES = 6


def bbox_index(b: dict = cfg.FINE_BBOX) -> tuple[np.ndarray, np.ndarray]:
    """Chỉ số hàng/cột của các tâm ô nằm trong khung."""
    li = np.where((LAT >= b["lat_min"]) & (LAT <= b["lat_max"]))[0]
    lj = np.where((LON >= b["lon_min"]) & (LON <= b["lon_max"]))[0]
    return li, lj


LI, LJ = bbox_index()


def decode(raw_gz: bytes, li: np.ndarray = LI, lj: np.ndarray = LJ) -> np.ndarray:
    """File .dat.gz toàn cầu → mảng (len(li), len(lj)) mm/giờ, thiếu = NaN."""
    a = np.frombuffer(gzip.decompress(raw_gz), dtype="<f4")
    if a.size != NLAT * NLON:
        raise ValueError(f"kích thước lạ: {a.size}")
    sub = a.reshape(NLAT, NLON)[np.ix_(li, lj)].astype(np.float32)
    sub[sub < 0] = np.nan
    return sub


def hour_frame(day: date, hour: int, sub: np.ndarray,
               li: np.ndarray = LI, lj: np.ndarray = LJ) -> pl.DataFrame:
    """Một giờ (HH = đầu giờ UTC) → bảng dài, nhãn thời gian = CUỐI giờ."""
    end = datetime(day.year, day.month, day.day, hour) + timedelta(hours=1)
    n = len(li) * len(lj)
    return pl.DataFrame({
        "time_utc": [end] * n,
        "time": [end + timedelta(hours=7)] * n,
        "lat": np.repeat(np.round(LAT[li], 2), len(lj)),
        "lon": np.tile(np.round(LON[lj], 2), len(li)),
        "precip_gc_mm_hr": sub.ravel(),
    })


class Ftp:
    """Mỗi luồng giữ một kết nối FTP riêng, tự nối lại khi rớt."""

    def __init__(self):
        self.local = threading.local()

    def conn(self) -> ftplib.FTP:
        c = getattr(self.local, "c", None)
        if c is None:
            c = ftplib.FTP(os.environ["JAXA_HOST"], timeout=60)
            c.login(os.environ["JAXA_USER"], os.environ["JAXA_PASS"])
            c.voidcmd("TYPE I")
            self.local.c = c
        return c

    def drop(self) -> None:
        c = getattr(self.local, "c", None)
        if c is not None:
            try:
                c.close()
            finally:
                self.local.c = None

    def get(self, path: str) -> bytes | None:
        """Nội dung file; None nếu file không tồn tại trên máy chủ."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                buf = io.BytesIO()
                self.conn().retrbinary(f"RETR {path}", buf.write)
                return buf.getvalue()
            except ftplib.error_perm as e:          # 550 = không có file
                if str(e).startswith("550"):
                    return None
                err = e
            except (OSError, EOFError, ftplib.Error) as e:
                err = e
            self.drop()
            time.sleep(min(60, 2 ** attempt))
        raise RuntimeError(f"{path}: {err}")


def part_path(day: date):
    return PARTS / f"{day:%Y%m%d}.parquet"


def month_path(y: int, m: int):
    return OUT / f"gsmap_nrt_{y:04d}{m:02d}.parquet"


def fetch_day(ftp: Ftp, day: date) -> tuple[date, int]:
    frames, missing = [], []
    for h in range(24):
        raw = ftp.get(REMOTE.format(d=day, h=h))
        if raw is None:
            missing.append(h)
            continue
        frames.append(hour_frame(day, h, decode(raw)))
    if frames:
        tmp = part_path(day).with_suffix(".tmp")
        pl.concat(frames).write_parquet(tmp, compression="zstd")
        tmp.replace(part_path(day))
    if missing:
        with open(MANIFEST, "a", encoding="utf-8") as f:
            f.write(json.dumps({"day": day.isoformat(), "missing_hours": missing}) + "\n")
    return day, 24 - len(missing)


def merge_months(today_end: date) -> int:
    """Gộp các tháng đã đủ ngày (ngày cuối tháng ≤ ``today_end``) thành file tháng."""
    done = 0
    months = sorted({(int(p.stem[:4]), int(p.stem[4:6])) for p in PARTS.glob("*.parquet")})
    for y, m in months:
        last = date(y, m, calendar.monthrange(y, m)[1])
        parts = [part_path(date(y, m, d)) for d in range(1, last.day + 1)]
        if last > today_end or not all(p.exists() for p in parts):
            continue
        pl.concat([pl.read_parquet(p) for p in parts]).write_parquet(
            month_path(y, m), compression="zstd")
        for p in parts:
            p.unlink()
        done += 1
    return done


def run(start: date, end: date, workers: int) -> None:
    from dotenv import load_dotenv

    load_dotenv(cfg.ROOT / ".env")
    for k in ("JAXA_HOST", "JAXA_USER", "JAXA_PASS"):
        if not os.environ.get(k):
            raise SystemExit(f"Thiếu {k} trong {cfg.ROOT / '.env'}")
    PARTS.mkdir(parents=True, exist_ok=True)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    todo = [d for d in days
            if not part_path(d).exists() and not month_path(d.year, d.month).exists()]
    print(f"[gsmap_nrt] {len(todo)}/{len(days)} ngày cần tải ({start} → {end}), "
          f"{workers} luồng", flush=True)

    ftp, t0, n_done, n_hours = Ftp(), time.time(), 0, 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(fetch_day, ftp, d) for d in todo]
        for fut in as_completed(futs):
            try:
                _, nh = fut.result()
            except Exception as e:  # noqa: BLE001 — ghi lại rồi đi tiếp, chạy lại sẽ thử lại
                print(f"  BỎ QUA: {str(e)[:160]}", flush=True)
                continue
            n_done += 1
            n_hours += nh
            if n_done % 50 == 0 or n_done == len(todo):
                el = time.time() - t0
                eta = el / n_done * (len(todo) - n_done)
                print(f"[{n_done}/{len(todo)} ngày] {n_hours:,} giờ · {el / 60:.0f} phút · "
                      f"còn ~{eta / 3600:.1f} giờ", flush=True)
                merge_months(end)
    print(f"Gộp thêm {merge_months(end)} tháng. XONG sau {(time.time() - t0) / 3600:.2f} giờ.",
          flush=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--start", default="1998-01-01")
    p.add_argument("--end", default=(date.today() - timedelta(days=1)).isoformat())
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args(argv)
    run(date.fromisoformat(a.start), date.fromisoformat(a.end), a.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
