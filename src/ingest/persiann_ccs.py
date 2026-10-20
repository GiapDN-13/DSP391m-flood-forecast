"""Mưa vệ tinh PERSIANN-CCS theo giờ, ô 0,04° (~4 km), cắt khung FINE_BBOX.

Nguồn: CHRS — UC Irvine (Hong và cs., 2004). Hai đường tải, cho CÙNG giá trị
(so 2020-10-01, 23 giờ × 625 ô: chênh tuyệt đối lớn nhất 0,000 mm):

* ``files`` (mặc định) — file toàn cầu theo giờ của CHRS, có từ 2000 tới nay:
  https://persiann.eng.uci.edu/CHRSdata/PERSIANN-CCS/hrly/YYYY/rgccs1hYYDDDHH.bin.gz
  Giải mã theo ``hrly/readme.hrly`` của CHRS (đã kiểm trên file thật):

  - nhị phân int16 big-endian, xếp theo hàng, 3000 hàng × 9000 cột, ô 0,04°;
  - đơn vị mm/h × 100; thiếu = -9999 (``daily/readme.daily`` ghi NODATA -9999;
    file giờ 2020-10-01 00Z: giá trị âm duy nhất là -9999);
  - phủ 60°N–60°S, kinh độ 0–360; ô đầu (tây bắc) có TÂM tại 59,98°N; 0,02°E;
  - ``HH`` trong tên file là ĐẦU giờ tích luỹ (HH:00–HH:59), giờ UTC.

  Mỗi file nén ~1,9 MB. Khung Huế ở hàng 1080–1104 (37 % đầu file) nên chỉ tải +
  giải nén phần đầu luồng gzip rồi cắt kết nối (~0,59 MB/giờ). Server chậm và
  dao động mạnh (đo 10/2026: 3–43 s cho một file).
* ``gdex`` — bản NetCDF của NSF NCAR GDEX (ds d652000, UCI CHRS + NCAR chuyển từ
  chính file nhị phân trên, phủ 2003-01-01 → 2024-12-31), cắt vùng PHÍA SERVER
  qua OPeNDAP: 1 request/ngày ≈ 80 KB thay vì 24 × 0,59 MB. Toạ độ tâm ô tường
  minh (lat ±59,98, lon ±179,98) ⇒ đồng thời là phép kiểm định vị độc lập.
  Nhãn thời gian GDEX = KẾT THÚC giờ tích luỹ (thuộc tính ``datetime_convention``)
  nên file ngày D chứa các giờ bắt đầu từ D-1 23Z tới D 22Z.

Không dùng CHRS Data Portal (chrsdata.eng.uci.edu): so ngày 2020-10-01, lưới cắt
của portal lệch so với cả file gốc lẫn GDEX (tương quan theo ô 0,32 tại cùng vị
trí, cao nhất 0,58 khi dịch 1 ô) và giá trị bị làm tròn về mm nguyên.

Đầu ra ``data/raw/persiann_ccs/pccs_YYYYMM.parquet`` (tháng theo giờ BẮT ĐẦU):

  time_utc   datetime UTC — thời điểm KẾT THÚC giờ tích luỹ (HH+1). Cùng quy ước
             với GDEX và với mưa ERA5 Open-Meteo trong data/raw/rain_hourly
             ("tổng giờ trước đó") ⇒ join theo ``time`` không lệch giờ.
  time       giờ Việt Nam (UTC+7, config.TIMEZONE), naive — giống rain_hourly
  lat, lon   TÂM ô (độ, làm tròn 2 chữ số)
  precip_mm  float32, mm trong giờ đó; null = vệ tinh không có dữ liệu

Resume theo giờ: giờ đã có trong parquet, hoặc nguồn đó đã báo không có (ghi ở
``_manifest.json``), thì không tải lại. Tháng đủ ⇒ bỏ qua hẳn.

    python -m src.ingest.persiann_ccs --start 2020-10-01 --end 2020-10-31
    python -m src.ingest.persiann_ccs --start 2003-01-01 --end 2024-12-30 --months 9,10,11,12 --source gdex
    python -m src.ingest.persiann_ccs --start 2020-10-01 --end 2020-11-30 --compare-era5

Hạn chế đã biết: PERSIANN-CCS suy mưa từ nhiệt độ sáng đỉnh mây hồng ngoại của vệ
tinh địa tĩnh (phân mảnh mây theo ngưỡng, Hong và cs., 2004, JAM 43:1834–1853).

* Mây ấm không được tính: "Warm raining clouds with brightness temperature higher
  than 253K are not covered from the current algorithm" (Karbalaee, Hsu & Sorooshian,
  AGU Fall Meeting 2015). Mưa địa hình mây thấp — đúng kiểu mưa gió mùa đông bắc
  dồn vào Trường Sơn ở Huế — vì vậy dễ bị ƯỚC LƯỢNG THẤP.
* Lệch theo độ cao: vùng núi Tây Bắc Mexico bị sót mưa nhỏ ở vùng cao, báo thừa ở
  vùng thấp, chu kỳ ngày lệch 1–2 giờ (Hong và cs., 2007, J. Hydrometeor. 8:469–482).
* Mây ti lạnh không mưa dễ bị báo mưa; nâng ngưỡng để bắt mây ấm thì báo động giả
  tăng (Karbalaee và cs., 2015). Tổng quan họ PERSIANN: Nguyen và cs., 2018, HESS 22:5801.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shutil
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import numpy as np
import polars as pl
import requests

from src import config as cfg

OUT_DIR = cfg.DATA_RAW / "persiann_ccs"
FILES_URL = "https://persiann.eng.uci.edu/CHRSdata/PERSIANN-CCS/hrly"
GDEX_URL = "https://tds.gdex.ucar.edu/thredds/dodsC/files/g/d652000/persiann-ccs"
GDEX_END = date(2024, 12, 31)   # temporalCoverage của d652000, kiểm 20/10/2026

# Lưới toàn cầu — readme.hrly
NROWS, NCOLS = 3000, 9000
RES = 0.04
LAT0 = 59.98     # tâm hàng đầu (bắc nhất)
LON0 = 0.02      # tâm cột đầu (kinh độ 0–360)
NODATA = -9999
SCALE = 100.0    # mm/h × 100
DATA_START = date(2003, 1, 1)   # mốc bộ CCS công bố; thư mục hrly có thêm 2000–2002

COLS = ["time_utc", "time", "lat", "lon", "precip_mm"]
SOURCES = ("files", "gdex")
MAX_WORKERS = 8      # lịch sự với server của trường đại học
MIN_FREE_GB = 3.0
TIMEOUT_S = 90
UA = {"User-Agent": "DSP391m-capstone/1.0 (student hydrology research; PERSIANN-CCS subset)"}

_local = threading.local()


class FormatError(RuntimeError):
    """Dữ liệu trả về sai cấu trúc — không thử lại."""


# ---------------------------------------------------------------- lưới, tên file

def bbox_index(bbox: dict) -> tuple[slice, slice]:
    """Hàng/cột (lưới file gốc) của các ô có TÂM nằm trong khung, tính cả biên."""
    eps = 1e-6
    lon_min, lon_max = bbox["lon_min"] % 360, bbox["lon_max"] % 360
    if lon_max < lon_min:
        raise ValueError("khung cắt qua kinh tuyến 0 — chưa hỗ trợ")
    r0 = max(math.ceil((LAT0 - bbox["lat_max"]) / RES - eps), 0)
    r1 = min(math.floor((LAT0 - bbox["lat_min"]) / RES + eps), NROWS - 1)
    c0 = max(math.ceil((lon_min - LON0) / RES - eps), 0)
    c1 = min(math.floor((lon_max - LON0) / RES + eps), NCOLS - 1)
    if r0 > r1 or c0 > c1:
        raise ValueError(f"khung {bbox} không chứa tâm ô nào")
    return slice(r0, r1 + 1), slice(c0, c1 + 1)


def cell_centers(rows: slice, cols: slice) -> tuple[np.ndarray, np.ndarray]:
    """Vĩ độ (bắc → nam) và kinh độ (-180..180) tâm ô."""
    lats = np.round(LAT0 - RES * np.arange(rows.start, rows.stop), 2)
    lons = np.round(LON0 + RES * np.arange(cols.start, cols.stop), 2)
    return lats, np.where(lons > 180, np.round(lons - 360, 2), lons)


def file_url(start_utc: datetime, base: str = FILES_URL) -> str:
    """URL file giờ có giờ BẮT ĐẦU ``start_utc`` (naive, UTC)."""
    doy = start_utc.timetuple().tm_yday
    return (f"{base}/{start_utc.year}/"
            f"rgccs1h{start_utc.year % 100:02d}{doy:03d}{start_utc.hour:02d}.bin.gz")


def gdex_url(label_day: date, base: str = GDEX_URL) -> str:
    """URL OPeNDAP file ngày GDEX (nhãn = kết thúc giờ tích luỹ)."""
    d = f"{label_day:%Y%m%d}"
    return (f"{base}/{label_day.year}/PERSIANN.CCS.A01H.VLD{d}.S{d}T000000.E{d}T235959"
            ".V01.SRCBIN.X9000Y3000.R0p04.FMT.nc")


def decode_prefix(raw: bytes, rows: slice, cols: slice) -> np.ndarray:
    """Phần đầu file đã giải nén (≥ rows.stop hàng) → lưới mm/h float32, NaN = thiếu."""
    a = np.frombuffer(raw, dtype=">i2", count=rows.stop * NCOLS).reshape(rows.stop, NCOLS)
    a = a[rows, cols]
    out = a.astype(np.float32) / np.float32(SCALE)
    out[a < 0] = np.nan          # chỉ gặp -9999; mưa âm là vô nghĩa
    return out


def parse_dap_ascii(txt: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Phản hồi OPeNDAP ``.ascii`` của ``precip[t][lat][lon]`` → (mảng, time giây, lat, lon)."""
    m = re.search(r"precip\.precip\[(\d+)\]\[(\d+)\]\[(\d+)\]", txt)
    if not m:
        raise FormatError(f"phản hồi OPeNDAP lạ: {txt[:200]!r}")
    nt, ny, nx = (int(x) for x in m.groups())
    body = txt[m.end():].split("precip.time[", 1)[0]
    arr = np.full((nt, ny, nx), np.nan)
    n = 0
    for k, i, vals in re.findall(r"^\[(\d+)\]\[(\d+)\], (.+)$", body, re.M):
        arr[int(k), int(i)] = [float(v) for v in vals.split(",")]
        n += 1
    if n != nt * ny:
        raise FormatError(f"thiếu dòng dữ liệu: {n}/{nt * ny}")

    def vec(name: str) -> np.ndarray:
        v = re.search(rf"precip\.{name}\[\d+\]\s*\n([^\n]+)", txt)
        if not v:
            raise FormatError(f"thiếu toạ độ {name}")
        return np.array([float(x) for x in v.group(1).split(",")])

    return arr, vec("time"), vec("lat"), vec("lon")


# ---------------------------------------------------------------- tải

def _session() -> requests.Session:
    s = getattr(_local, "s", None)
    if s is None:
        s = _local.s = requests.Session()
        s.headers.update(UA)
    return s


def fetch_prefix(url: str, nbytes: int) -> tuple[bytes | None, int]:
    """Tải luồng gzip tới khi giải nén đủ ``nbytes`` byte đầu rồi cắt. 404 → (None, 0).

    Trả về (byte đã giải nén, số byte thực tải qua mạng).
    """
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    buf = bytearray()
    got = 0
    with _session().get(url, stream=True, timeout=TIMEOUT_S) as r:
        if r.status_code == 404:
            return None, 0
        r.raise_for_status()
        for chunk in r.iter_content(64 * 1024):
            got += len(chunk)
            buf += d.decompress(chunk, nbytes - len(buf))
            if len(buf) >= nbytes:
                break
    if len(buf) < nbytes:
        raise OSError(f"luồng ngắn: giải nén được {len(buf)}/{nbytes} byte")
    return bytes(buf), got


def _retry(fn, *args, what: str = ""):
    """Gọi lại với backoff mũ + nhiễu; hết lượt thì ném lỗi. FormatError ném ngay."""
    for k in range(cfg.MAX_RETRIES):
        try:
            return fn(*args)
        except (requests.RequestException, OSError, zlib.error) as e:
            if k == cfg.MAX_RETRIES - 1:
                raise
            wait = min(60.0, 2.0 * 2 ** k) + random.uniform(0, 1)
            print(f"  ! {what}: {e.__class__.__name__}: {str(e)[:120]} — thử lại sau {wait:.0f}s",
                  flush=True)
            time.sleep(wait)
    raise RuntimeError("không tới được đây")


def fetch_hour_files(start_utc: datetime, rows: slice, cols: slice,
                     base: str = FILES_URL) -> tuple[np.ndarray | None, int]:
    """Một giờ từ file toàn cầu → (lưới cắt, byte tải). None nếu server không có file."""
    url = file_url(start_utc, base)
    raw, n = _retry(fetch_prefix, url, rows.stop * NCOLS * 2, what=url.rsplit("/", 1)[-1])
    if raw is None:
        return None, 0
    return decode_prefix(raw, rows, cols), n


def _gdex_get(url: str) -> tuple[str | None, int]:
    r = _session().get(url, timeout=TIMEOUT_S)
    if r.status_code == 404:
        return None, 0
    r.raise_for_status()
    return r.text, len(r.content)


def fetch_day_gdex(label_day: date, k0: int, k1: int, lats: np.ndarray, lons: np.ndarray,
                   base: str = GDEX_URL) -> tuple[dict[datetime, np.ndarray], int]:
    """Nhãn giờ k0..k1 của file ngày ``label_day`` trên GDEX → {giờ BẮT ĐẦU UTC: lưới}.

    GDEX xếp lat tăng dần (nam → bắc), lon -180..180; lật về bắc → nam như file gốc
    và đối chiếu toạ độ trả về với tâm ô tính từ readme.
    """
    i = np.rint((lats + LAT0) / RES).astype(int)
    j = np.rint((lons + 180 - LON0) / RES).astype(int)
    q = f"precip[{k0}:1:{k1}][{i.min()}:1:{i.max()}][{j.min()}:1:{j.max()}]"
    url = f"{gdex_url(label_day, base)}.ascii?{quote(q, safe=':')}"
    txt, n = _retry(_gdex_get, url, what=f"gdex {label_day}")
    if txt is None:
        return {}, 0
    arr, tsec, la, lo = parse_dap_ascii(txt)
    if not (np.array_equal(np.round(la[::-1], 2), lats) and np.array_equal(np.round(lo, 2), lons)):
        raise FormatError(f"toạ độ GDEX lệch tâm ô readme ({label_day})")
    out = {}
    for k, ts in enumerate(tsec):
        label = datetime(1970, 1, 1) + timedelta(seconds=int(ts))
        if label.date() != label_day or not k0 <= label.hour <= k1:
            raise FormatError(f"nhãn giờ GDEX lạ: {label}")
        out[label - timedelta(hours=1)] = arr[k, ::-1, :].astype(np.float32)
    return out, n


# ---------------------------------------------------------------- bảng, resume

def to_frame(grids: dict[datetime, np.ndarray], lats: np.ndarray, lons: np.ndarray) -> pl.DataFrame:
    """{giờ bắt đầu UTC: lưới} → bảng dài theo schema COLS."""
    starts = sorted(grids)
    if not starts:
        return pl.DataFrame(schema={"time_utc": pl.Datetime("us", "UTC"), "time": pl.Datetime("us"),
                                    "lat": pl.Float64, "lon": pl.Float64,
                                    "precip_mm": pl.Float32})
    n = len(lats) * len(lons)
    ends = np.array([t + timedelta(hours=1) for t in starts], dtype="datetime64[us]")
    vals = np.stack([grids[t] for t in starts]).astype(np.float32).ravel()
    df = pl.DataFrame({
        "time_utc": np.repeat(ends, n),
        "lat": np.tile(np.repeat(lats, len(lons)), len(starts)).astype(np.float64),
        "lon": np.tile(np.tile(lons, len(lats)), len(starts)).astype(np.float64),
        "precip_mm": vals,
    })
    return (df.with_columns(pl.col("time_utc").dt.replace_time_zone("UTC"),
                            pl.col("precip_mm").fill_nan(None))
              .with_columns(time=pl.col("time_utc").dt.convert_time_zone(cfg.TIMEZONE)
                                                   .dt.replace_time_zone(None))
              .select(COLS))


def hours_requested(start: date, end: date, months: set[int] | None = None) -> dict[str, list[datetime]]:
    """Giờ BẮT ĐẦU (UTC, naive) từ start 00Z tới end 23Z, nhóm theo tháng YYYYMM."""
    out: dict[str, list[datetime]] = {}
    t = datetime(start.year, start.month, start.day)
    stop = datetime(end.year, end.month, end.day, 23)
    while t <= stop:
        if months is None or t.month in months:
            out.setdefault(f"{t:%Y%m}", []).append(t)
        t += timedelta(hours=1)
    return out


def month_path(ym: str, out_dir: Path | None = None) -> Path:
    return (out_dir or OUT_DIR) / f"pccs_{ym}.parquet"


def _load_manifest(d: Path) -> dict:
    f = d / "_manifest.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _save_manifest(d: Path, man: dict) -> None:
    f = d / "_manifest.json"
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, f)


def _known_missing(rec: dict, source: str) -> set[str]:
    legacy = rec.get("missing", []) if source == "files" else []   # bản ghi cũ chỉ có "files"
    return set(rec.get(f"missing_{source}", legacy))


def _hours_present(path: Path) -> set[datetime]:
    if not path.exists():
        return set()
    t = (pl.read_parquet(path, columns=["time_utc"]).get_column("time_utc").unique()
           .dt.replace_time_zone(None))
    return {x - timedelta(hours=1) for x in t.to_list()}


def _write_atomic(df: pl.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(".parquet.tmp")
    try:
        df.write_parquet(tmp, compression="zstd", statistics=True)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _log(ym: str, i: int, n: int, unit: str, nbytes: int, t0: float, every: int) -> None:
    if i % every == 0 or i == n:
        dt = time.time() - t0
        print(f"  [{ym}] {i}/{n} {unit} | {nbytes / 1e6:.2f} MB | {dt / i:.2f} s/{unit} | "
              f"còn ~{dt / i * (n - i) / 60:.0f} phút", flush=True)


def _fetch_files(ym: str, todo: list[datetime], rows: slice, cols: slice, workers: int,
                 base: str) -> tuple[dict[datetime, np.ndarray], list[datetime], int]:
    grids: dict[datetime, np.ndarray] = {}
    missing: list[datetime] = []
    nbytes = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_hour_files, t, rows, cols, base): t for t in todo}
        for i, f in enumerate(as_completed(futs), 1):
            g, n = f.result()
            nbytes += n
            if g is None:
                missing.append(futs[f])
            else:
                grids[futs[f]] = g
            _log(ym, i, len(todo), "giờ", nbytes, t0, 48)
    return grids, missing, nbytes


def _fetch_gdex(ym: str, todo: list[datetime], lats: np.ndarray, lons: np.ndarray, workers: int,
                base: str) -> tuple[dict[datetime, np.ndarray], list[datetime], int]:
    want = set(todo)
    by_day: dict[date, list[int]] = {}
    for t in todo:
        label = t + timedelta(hours=1)
        by_day.setdefault(label.date(), []).append(label.hour)
    grids: dict[datetime, np.ndarray] = {}
    nbytes = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=min(workers, 4)) as ex:
        futs = [ex.submit(fetch_day_gdex, d, min(h), max(h), lats, lons, base)
                for d, h in by_day.items()]
        for i, f in enumerate(as_completed(futs), 1):
            g, n = f.result()
            nbytes += n
            grids.update({k: v for k, v in g.items() if k in want})
            _log(ym, i, len(futs), "ngày", nbytes, t0, 8)
    return grids, sorted(want - set(grids)), nbytes


def process_month(ym: str, starts: list[datetime], source: str = "files", workers: int = 4,
                  bbox: dict | None = None, out_dir: Path | None = None,
                  base: str | None = None) -> dict | None:
    """Tải các giờ còn thiếu của một tháng, gộp với file cũ, ghi nguyên tử.

    Trả thống kê đo được, hoặc None nếu tháng đã đủ.
    """
    if source not in SOURCES:
        raise ValueError(f"source lạ: {source}")
    bbox = bbox or cfg.FINE_BBOX
    d = out_dir or OUT_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = month_path(ym, d)
    man = _load_manifest(d)
    rec = man.get(ym, {})
    known = _known_missing(rec, source)
    have = _hours_present(path)
    todo = [t for t in starts if t not in have and t.isoformat() not in known]
    if not todo:
        print(f"[{ym}] đủ {len(starts)} giờ — bỏ qua", flush=True)
        return None

    rows, cols = bbox_index(bbox)
    lats, lons = cell_centers(rows, cols)
    print(f"[{ym}] cần tải {len(todo)}/{len(starts)} giờ ({source})", flush=True)
    t0 = time.time()
    if source == "files":
        grids, missing, nbytes = _fetch_files(ym, todo, rows, cols, workers, base or FILES_URL)
    else:
        grids, missing, nbytes = _fetch_gdex(ym, todo, lats, lons, workers, base or GDEX_URL)
    secs = time.time() - t0

    new = to_frame(grids, lats, lons)
    df = pl.concat([pl.read_parquet(path), new]) if path.exists() else new
    df = df.unique(["time_utc", "lat", "lon"], keep="last").sort(["time_utc", "lat", "lon"],
                                                                 descending=[False, True, False])
    _write_atomic(df, path)

    man = _load_manifest(d)          # đọc lại: tiến trình khác có thể vừa ghi tháng khác
    rec = man.get(ym, {})
    legacy = rec.pop("missing", None)
    if legacy is not None:
        rec.setdefault("missing_files", legacy)
    rec[f"missing_{source}"] = sorted(_known_missing(rec, source) | known
                                      | {t.isoformat() for t in missing})
    rec.setdefault("runs", []).append({
        "source": source, "hours": len(grids), "missing": len(missing), "bytes": nbytes,
        "seconds": round(secs, 1), "workers": workers, "at": f"{datetime.now():%Y-%m-%d %H:%M}"})
    man[ym] = rec
    _save_manifest(d, man)

    stat = {"ym": ym, "source": source, "hours": len(grids), "missing": len(missing),
            "bytes": nbytes, "seconds": round(secs, 1), "parquet_bytes": path.stat().st_size,
            "rows": df.height}
    print(f"[{ym}] xong {len(grids)} giờ, thiếu {len(missing)} | tải {nbytes / 1e6:.2f} MB "
          f"trong {secs / 60:.1f} phút | parquet {stat['parquet_bytes'] / 1e6:.2f} MB", flush=True)
    return stat


def run(start: date, end: date, months: set[int] | None = None, source: str = "files",
        workers: int = 4, out_dir: Path | None = None) -> list[dict]:
    if start < DATA_START:
        print(f"Cảnh báo: CCS công bố từ {DATA_START}; giờ không có file sẽ ghi là thiếu.")
    if source == "gdex" and end >= GDEX_END:
        print(f"Cảnh báo: GDEX chỉ tới {GDEX_END}; phần sau đó dùng --source files.")
    workers = max(1, min(workers, MAX_WORKERS))
    d = out_dir or OUT_DIR
    d.mkdir(parents=True, exist_ok=True)
    stats = []
    for ym, starts in hours_requested(start, end, months).items():
        free = shutil.disk_usage(d).free / 1e9
        if free < MIN_FREE_GB:
            print(f"DỪNG: ổ đĩa chỉ còn {free:.1f} GB")
            break
        s = process_month(ym, starts, source, workers, out_dir=out_dir)
        if s:
            stats.append(s)
    if stats:
        h = sum(s["hours"] for s in stats)
        b = sum(s["bytes"] for s in stats)
        sec = sum(s["seconds"] for s in stats)
        pq = sum(s["parquet_bytes"] for s in stats)
        print(f"\nTỔNG: {h} giờ | tải {b / 1e6:.1f} MB ({b / max(h, 1) / 1e3:.1f} KB/giờ) | "
              f"{sec / max(h, 1):.3f} s/giờ ({source}, workers={workers}) | parquet {pq / 1e6:.2f} MB")
    return stats


# ---------------------------------------------------------------- so với ERA5

# Ô ERA5 trong data/raw/rain_hourly: tâm 16,1–16,8 × 107,1–107,8 bước 0,1 ⇒ phủ ±0,05
ERA5_FOOTPRINT = {"lat_min": 16.05, "lat_max": 16.85, "lon_min": 107.05, "lon_max": 107.85}


def _corr(a: pl.Series, b: pl.Series) -> float:
    return float(np.corrcoef(a.to_numpy(), b.to_numpy())[0, 1])


def compare_era5(yms: list[str], out_dir: Path | None = None,
                 era5_dir: Path | None = None) -> dict:
    """So mưa trung bình khung PERSIANN-CCS với trung bình 64 ô ERA5 cùng giờ VN.

    ``pccs_fp``: chỉ các ô CCS nằm trong vùng phủ của 64 ô ERA5 (so công bằng);
    ``pccs_box``: cả khung FINE_BBOX. Ngày tính theo ngày lịch giờ VN của ``time``.
    """
    files = [f for f in (month_path(ym, out_dir) for ym in yms) if f.exists()]
    if not files:
        raise FileNotFoundError("chưa có tháng nào để so")
    p = pl.concat([pl.read_parquet(f) for f in files])
    fp = ERA5_FOOTPRINT
    in_fp = (pl.col("lat").is_between(fp["lat_min"], fp["lat_max"])
             & pl.col("lon").is_between(fp["lon_min"], fp["lon_max"]))
    pc = (p.group_by("time")
           .agg(pccs_box=pl.col("precip_mm").mean(),
                pccs_fp=pl.col("precip_mm").filter(in_fp).mean()))
    years = sorted({int(ym[:4]) for ym in yms})
    edir = era5_dir or cfg.DATA_RAW / "rain_hourly"
    era_files = [str(f) for y in years for f in edir.glob(f"rh_*_{y}.parquet")]
    era = (pl.scan_parquet(era_files).group_by("time")
             .agg(era5=pl.col("precipitation").mean(), n_era=pl.len()).collect())
    j = pc.join(era, on="time", how="inner").drop_nulls(["pccs_fp", "era5"]).sort("time")
    day = (j.group_by(pl.col("time").dt.date().alias("date"))
            .agg(pl.col("pccs_box", "pccs_fp", "era5").sum(), n=pl.len())
            .filter(pl.col("n") == 24).sort("date"))
    lags = {}
    for k in range(-3, 4):      # k > 0: PERSIANN trễ hơn ERA5 k giờ
        s = j.select(pl.col("pccs_fp").shift(-k), "era5").drop_nulls()
        lags[k] = round(_corr(s["pccs_fp"], s["era5"]), 3)
    res = {
        "months": yms,
        "n_cells_box": p.select(pl.struct("lat", "lon").n_unique()).item(),
        "n_cells_footprint": p.filter(in_fp).select(pl.struct("lat", "lon").n_unique()).item(),
        "n_hours_joined": j.height, "n_era5_cells_min": int(j["n_era"].min()),
        "null_cell_hours": int(p["precip_mm"].null_count()),
        "total_mm_pccs_box": round(float(j["pccs_box"].sum()), 1),
        "total_mm_pccs_fp": round(float(j["pccs_fp"].sum()), 1),
        "total_mm_era5": round(float(j["era5"].sum()), 1),
        "ratio_fp_over_era5": round(float(j["pccs_fp"].sum() / j["era5"].sum()), 3),
        "corr_hourly_fp": round(_corr(j["pccs_fp"], j["era5"]), 3),
        "corr_hourly_box": round(_corr(j["pccs_box"], j["era5"]), 3),
        "n_days": day.height,
        "corr_daily_fp": round(_corr(day["pccs_fp"], day["era5"]), 3),
        "corr_daily_box": round(_corr(day["pccs_box"], day["era5"]), 3),
        "corr_hourly_by_lag": lags,
        "max_hourly_mm_pccs_fp": round(float(j["pccs_fp"].max()), 2),
        "max_hourly_mm_era5": round(float(j["era5"].max()), 2),
        "wet_hour_frac_pccs_fp": round(float((j["pccs_fp"] > 0.1).mean()), 3),
        "wet_hour_frac_era5": round(float((j["era5"] > 0.1).mean()), 3),
        "max_daily_mm_pccs_fp": round(float(day["pccs_fp"].max()), 1),
        "max_daily_mm_era5": round(float(day["era5"].max()), 1),
        # tổng tháng của trung bình khung (tháng theo giờ bắt đầu = theo file)
        "monthly_total_mm_box": {
            f.stem[-6:]: round(float(pl.read_parquet(f).group_by("time")
                                     .agg(pl.col("precip_mm").mean())["precip_mm"].sum()), 1)
            for f in files},
    }
    for k, v in res.items():
        print(f"  {k:24} {v}")
    out = (out_dir or OUT_DIR) / "_compare_era5.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--start", required=True, type=date.fromisoformat, help="ngày UTC đầu")
    ap.add_argument("--end", required=True, type=date.fromisoformat, help="ngày UTC cuối (tính cả)")
    ap.add_argument("--months", type=lambda s: {int(x) for x in s.split(",")}, default=None,
                    help="chỉ lấy các tháng này, vd 9,10,11,12")
    ap.add_argument("--workers", type=int, default=4, help=f"số luồng tải (tối đa {MAX_WORKERS})")
    ap.add_argument("--source", choices=SOURCES, default="files",
                    help="files: CHRS gốc (mọi năm); gdex: cắt phía server, 2003–2024, nhẹ ~25 lần")
    ap.add_argument("--out-dir", type=Path, default=None, help=f"mặc định {OUT_DIR}")
    ap.add_argument("--dry-run", action="store_true", help="chỉ liệt kê tháng và số giờ")
    ap.add_argument("--compare-era5", action="store_true",
                    help="sau khi tải, so với ERA5 theo giờ trong data/raw/rain_hourly")
    a = ap.parse_args(argv)
    if a.end < a.start:
        ap.error("--end phải ≥ --start")
    plan = hours_requested(a.start, a.end, a.months)
    if a.dry_run:
        for ym, hs in plan.items():
            have = _hours_present(month_path(ym, a.out_dir))
            print(f"  {ym}: {len(hs)} giờ, đã có {len(have & set(hs))}")
        return
    run(a.start, a.end, a.months, a.source, a.workers, a.out_dir)
    if a.compare_era5:
        compare_era5(list(plan), a.out_dir)


if __name__ == "__main__":
    main()
