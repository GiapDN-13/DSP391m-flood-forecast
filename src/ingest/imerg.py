"""Mưa vệ tinh GPM IMERG (lưới 0,1°, bước 30 phút) cắt theo FINE_BBOX.

Hai nguồn, đều CẮT VÙNG phía server (chỉ tải 10 × 10 ô, không tải lưới toàn cầu):

* ``erddap`` (mặc định, KHÔNG cần tài khoản) — ERDDAP của NOAA/AOML (Hurricane
  Database) phát lại IMERG **Final** nửa giờ, mỗi năm một dataset:
  V06 ``precipitation_YYYY`` (2000-06 → 2024-06-02) và V07
  ``precipitation_YYYY_v07`` (1998–2000, 2024 → 2025-08). Một request = một tháng.
* ``gesdisc`` (CẦN tài khoản NASA Earthdata) — nguồn gốc NASA GES DISC, V07,
  đủ ba run: ``final`` (GPM_3IMERGHH.07, hiệu chỉnh trạm GPCC, trễ vài tháng),
  ``late`` (GPM_3IMERGHHL.07, trễ ~14 giờ) và ``early`` (GPM_3IMERGHHE.07, ~4 giờ).
  Danh sách file lấy từ CMR (công khai), số liệu qua OPeNDAP trên Earthdata
  Cloud (opendap.earthdata.nasa.gov); ``--onprem`` dùng máy chủ cũ gpm1 —
  NASA thông báo tắt OPeNDAP on-prem trong 20/08–30/09/2026.
  Đăng nhập: biến môi trường ``EARTHDATA_TOKEN`` (Bearer) hoặc ``~/_netrc`` /
  ``~/.netrc`` dòng ``machine urs.earthdata.nasa.gov login ... password ...``.

Đầu ra ``data/raw/imerg/``: ``imerg_YYYYMM.parquet`` (Final V07),
``imerg_v06_YYYYMM.parquet`` (Final V06), ``imerg_{late|early}_YYYYMM.parquet``.
Tách tên theo phiên bản để không trộn lẫn V06/V07 khi huấn luyện. Cột:

* ``time_utc`` — ĐẦU khoảng 30 phút, UTC.
* ``time``     — như trên theo giờ Việt Nam (UTC+7, không gắn múi giờ — cùng
  quy ước với ``data/raw/rain_hourly``).
* ``lat``, ``lon`` — tâm ô 0,1° (x,x5).
* ``precip_mm_hr`` — CƯỜNG ĐỘ mưa trung bình trong 30 phút, **mm/h** (đơn vị gốc
  của IMERG). Lượng mưa của khoảng = ``precip_mm_hr / 2`` (mm). Thiếu số liệu = null.
* ``product`` (final/late/early), ``version`` (vd V06B, V07B).

Chạy lại được giữa chừng: ERDDAP resume theo tháng; GES DISC resume theo ngày
(file tạm ``_parts/``, đủ tháng thì gộp và xoá).

    python -m src.ingest.imerg --start 2020-10 --end 2020-10                  # ERDDAP, tự chọn V07/V06
    python -m src.ingest.imerg --start 2001-01 --end 2024-05 --version v06    # chuỗi V06 liền mạch
    python -m src.ingest.imerg --source gesdisc --product late --start 2026-10-01 --end 2026-10-19
    python -m src.ingest.imerg --compare-era5 2020-10 --version v06
"""

from __future__ import annotations

import argparse
import calendar
import csv
import io
import json
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import h5py
import numpy as np
import polars as pl
import requests
from scipy.io import netcdf_file

from src import config as cfg

OUT = cfg.DATA_RAW / "imerg"

ERDDAP = "https://erddap.aoml.noaa.gov/hdb/erddap"
GESDISC = "https://gpm1.gesdisc.eosdis.nasa.gov"            # on-prem, đang bị NASA tắt dần
CLOUD_OPENDAP = "https://opendap.earthdata.nasa.gov"
CMR = "https://cmr.earthdata.nasa.gov/search"
COLLECTIONS = {   # run → (short name GES DISC, concept id CMR) — tra CMR ngày 20/10/2026
    "final": ("GPM_3IMERGHH.07", "C2723754847-GES_DISC"),
    "late": ("GPM_3IMERGHHL.07", "C2723754845-GES_DISC"),
    "early": ("GPM_3IMERGHHE.07", "C2723758340-GES_DISC"),
}

# Lưới IMERG: tâm ô lon = -179,95 + 0,1·i (i = 0..3599), lat = -89,95 + 0,1·j (j = 0..1799).
# File gốc xếp [time][lon][lat] (lon TRƯỚC lat); ERDDAP xếp [time][lat][lon].
RES = 0.1
NLON, NLAT = 3600, 1800
FILL_THRESHOLD = -9000.0   # _FillValue = -9999,9. Lưu ý: ERDDAP gắn missing_value=0 nhưng 0 là "không mưa" thật
VN_OFFSET = timedelta(hours=7)
SLOTS_PER_DAY = 48
PRECIP_VARS = ("precipitation", "Grid/precipitation",
               "precipitationCal", "Grid/precipitationCal")   # V07 rồi tới V06
TIMEOUT_S = 60
ERDDAP_TIMEOUT_S = 900     # 1 tháng × 100 ô mất ~100 s phía server (đo 20/10/2026)
WORKERS = 8

GRANULE_RE = re.compile(
    r"3B-HHR(?:-[EL])?\.MS\.MRG\.3IMERG\.(\d{8})-S(\d{6})-E\d{6}\.\d{4}\.(V\d{2}[A-Z]?)\.(?:HDF5|RT-H5)")


class AuthError(RuntimeError):
    """Server trả về trang đăng nhập Earthdata hoặc 401/403 — thử lại vô ích."""


@dataclass(frozen=True)
class Granule:
    name: str
    start_utc: datetime   # đầu khoảng 30 phút, naive UTC
    version: str
    base: str = ""        # URL OPeNDAP của file, chưa có hậu tố


# ---------- Lưới ----------

def bbox_index(bbox: dict | None = None) -> tuple[int, int, int, int]:
    """(i0, i1, j0, j1) — chỉ số lon/lat (gồm cả hai đầu) của các ô NẰM TRỌN trong bbox."""
    b = bbox or cfg.FINE_BBOX
    i0 = round((b["lon_min"] + 180) / RES)
    i1 = round((b["lon_max"] + 180) / RES) - 1
    j0 = round((b["lat_min"] + 90) / RES)
    j1 = round((b["lat_max"] + 90) / RES) - 1
    if i1 < i0 or j1 < j0:
        raise ValueError(f"bbox quá nhỏ so với ô 0,1°: {b}")
    return i0, i1, j0, j1


def cell_centers(idx: tuple[int, int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    i0, i1, j0, j1 = idx
    lon = np.round(-179.95 + RES * np.arange(i0, i1 + 1), 2)
    lat = np.round(-89.95 + RES * np.arange(j0, j1 + 1), 2)
    return lat, lon


def _enc(ce: str) -> str:
    """Mã hoá [ ] trong ràng buộc OPeNDAP/ERDDAP (Tomcat từ chối ngoặc vuông thô)."""
    return ce.replace("[", "%5B").replace("]", "%5D")


# ---------- Mạng: thử lại + đăng nhập ----------

def plain_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "DSP391m-imerg/1.0"
    return s


def has_credentials() -> bool:
    """Có token hoặc netrc chứa urs.earthdata.nasa.gov (chỉ kiểm tra, không đọc ra mật khẩu)."""
    if os.environ.get("EARTHDATA_TOKEN"):
        return True
    home = Path.home()
    for f in (os.environ.get("NETRC"), home / "_netrc", home / ".netrc"):
        if f and Path(f).is_file():
            try:
                if "urs.earthdata.nasa.gov" in Path(f).read_text(encoding="utf-8", errors="ignore"):
                    return True
            except OSError:
                pass
    return False


def earthdata_session() -> requests.Session:
    """Token → header Bearer (chỉ dùng cho máy chủ NASA). Không có token thì requests
    tự lấy netrc khi bị chuyển hướng sang urs.earthdata.nasa.gov (trust_env=True)."""
    s = plain_session()
    tok = os.environ.get("EARTHDATA_TOKEN")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


def _is_login_page(r) -> bool:
    host = r.url.split("/")[2] if "://" in r.url else ""
    return "urs.earthdata.nasa.gov" in host or r.headers.get("Content-Type", "").startswith("text/html")


def http_get(session, url: str, *, binary: bool = True, retries: int | None = None,
             sleep_s: float = 2.0, timeout: float = TIMEOUT_S) -> bytes | str | None:
    """GET có thử lại theo cấp số nhân. 404 → None (không có số liệu).

    401/403 hoặc bị đẩy về trang đăng nhập khi cần dữ liệu nhị phân → AuthError.
    4xx khác (vd 400 sai ràng buộc) → ValueError ngay, không thử lại.
    """
    retries = cfg.MAX_RETRIES if retries is None else retries
    last: Exception | None = None
    for k in range(retries):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 404:
                return None
            if r.status_code in (401, 403) or (binary and r.ok and _is_login_page(r)):
                raise AuthError(f"HTTP {r.status_code} — Earthdata chưa đăng nhập / chưa "
                                f"approve ứng dụng GES DISC ({url.split('?')[0]})")
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            if r.status_code >= 400:
                raise ValueError(f"HTTP {r.status_code}: {url.split('?')[0]} — {r.text[:300]}")
            return r.content if binary else r.text
        except (AuthError, ValueError):
            raise
        except (requests.RequestException, OSError) as e:
            last = e
            if k < retries - 1:
                time.sleep(sleep_s * 2 ** k)
    raise RuntimeError(f"Hết {retries} lần thử: {url.split('?')[0]} — {last}")


# ---------- Đặt tên file ----------

def month_path(product: str, y: int, m: int, out: Path = OUT, version: str = "v07") -> Path:
    tag = "" if product == "final" else f"{product}_"
    if product == "final" and version.lower().startswith("v06"):
        tag = "v06_"
    return out / f"imerg_{tag}{y:04d}{m:02d}.parquet"


def parts_dir(product: str, y: int, m: int, out: Path = OUT) -> Path:
    return out / "_parts" / f"{product}_{y:04d}{m:02d}"


def month_done(product: str, y: int, m: int, out: Path = OUT, version: str = "v07") -> bool:
    return (month_path(product, y, m, out, version).exists()
            and not parts_dir(product, y, m, out).exists())


def finalize(df: pl.DataFrame) -> pl.DataFrame:
    """Chuẩn hoá schema + giờ VN, sắp xếp. Vào: time_utc naive UTC."""
    return (df.with_columns(
                pl.col("time_utc").dt.replace_time_zone("UTC"),
                (pl.col("time_utc") + VN_OFFSET).alias("time"),     # tính trên cột naive
                pl.col("precip_mm_hr").cast(pl.Float32).fill_nan(None))
              .select("time_utc", "time", "lat", "lon", "precip_mm_hr", "product", "version")
              .sort("time_utc", "lat", "lon"))


def _write(df: pl.DataFrame, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    df.write_parquet(tmp, compression="zstd", statistics=True)
    tmp.replace(dest)
    return dest


# ====================== Nguồn 1: ERDDAP (không cần đăng nhập) ======================

_INFO_CACHE: dict[str, dict | None] = {}


def erddap_dataset_id(year: int, version: str) -> str:
    return f"precipitation_{year}_v07" if version == "v07" else f"precipitation_{year}"


def parse_erddap_info(text: str) -> dict:
    """CSV /info/<id>/index.csv → {start, end (naive UTC), var}."""
    rows = list(csv.reader(io.StringIO(text)))
    glob = {r[2]: r[4] for r in rows if len(r) >= 5 and r[1] == "NC_GLOBAL"}
    var = next(r[1] for r in rows if len(r) >= 2 and r[0] == "variable"
               and r[1].startswith("precipitation"))

    def ts(s: str) -> datetime:
        return datetime.strptime(s.rstrip("Z"), "%Y-%m-%dT%H:%M:%S")

    return {"start": ts(glob["time_coverage_start"]), "end": ts(glob["time_coverage_end"]),
            "var": var}


def erddap_info(session, dsid: str) -> dict | None:
    if dsid not in _INFO_CACHE:
        txt = http_get(session, f"{ERDDAP}/info/{dsid}/index.csv", binary=False)
        _INFO_CACHE[dsid] = parse_erddap_info(txt) if txt else None
    return _INFO_CACHE[dsid]


def erddap_pick(session, y: int, m: int, version: str) -> tuple[str, dict, str] | None:
    """Chọn dataset phủ tháng (y, m). version auto = ưu tiên V07, thiếu thì V06."""
    m0 = datetime(y, m, 1)
    m1 = datetime(y, m, calendar.monthrange(y, m)[1], 23, 30)
    for v in (("v07", "v06") if version == "auto" else (version,)):
        dsid = erddap_dataset_id(y, v)
        info = erddap_info(session, dsid)
        if info and info["start"] <= m1 and info["end"] >= m0:
            return dsid, info, v
    return None


def erddap_url(dsid: str, var: str, t0: datetime, t1: datetime, idx) -> str:
    lat, lon = cell_centers(idx)
    ce = (f"{var}[({t0:%Y-%m-%dT%H:%M:%SZ}):1:({t1:%Y-%m-%dT%H:%M:%SZ})]"
          f"[({lat[0]}):1:({lat[-1]})][({lon[0]}):1:({lon[-1]})]")
    return f"{ERDDAP}/griddap/{dsid}.nc?{_enc(ce)}"


def read_erddap_nc(blob: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str | None]:
    """NetCDF-3 của ERDDAP → (time naive UTC, lat, lon, P[time, lat, lon] mm/h, ProductVersion)."""
    with netcdf_file(io.BytesIO(blob), "r", mmap=False) as f:
        var = next(k for k in f.variables if k.startswith("precipitation"))
        p = np.array(f.variables[var].data, dtype=np.float32)
        t = np.array(f.variables["time"].data, dtype=np.float64)
        lat = np.round(np.array(f.variables["latitude"].data, dtype=np.float64), 2)
        lon = np.round(np.array(f.variables["longitude"].data, dtype=np.float64), 2)
        hdr = getattr(f, "FileHeader", b"")
    hdr = hdr.decode("utf-8", "ignore") if isinstance(hdr, bytes) else str(hdr)
    m = re.search(r"ProductVersion=(V\w+)", hdr)
    p[p < FILL_THRESHOLD] = np.nan          # chỉ -9999,9 là thiếu; 0 là không mưa
    times = (np.datetime64("1970-01-01T00:00:00") + np.round(t).astype("timedelta64[s]"))
    return times.astype("datetime64[us]"), lat, lon, p, (m.group(1) if m else None)


def erddap_frame(times, lat, lon, p, version: str) -> pl.DataFrame:
    nt, nla, nlo = p.shape
    return pl.DataFrame({
        "time_utc": np.repeat(times, nla * nlo),
        "lat": np.tile(np.repeat(lat, nlo), nt),
        "lon": np.tile(lon, nt * nla),
        "precip_mm_hr": p.ravel(),
    }).with_columns(pl.lit("final").alias("product"), pl.lit(version).alias("version"))


def erddap_month(session, y: int, m: int, version: str, idx, out: Path = OUT, log=print
                 ) -> Path | None:
    pick = erddap_pick(session, y, m, version)
    if pick is None:
        log(f"[không có] {y}-{m:02d}: ERDDAP không có dataset {version} phủ tháng này")
        return None
    dsid, info, v = pick
    if month_done("final", y, m, out, v):
        log(f"[bỏ qua] {month_path('final', y, m, out, v).name} đã có")
        return None
    t0 = max(datetime(y, m, 1), info["start"])
    t1 = min(datetime(y, m, calendar.monthrange(y, m)[1], 23, 30), info["end"])
    t_start = time.time()
    blob = http_get(session, erddap_url(dsid, info["var"], t0, t1, idx), timeout=ERDDAP_TIMEOUT_S)
    if blob is None:
        log(f"[trống] {dsid} {y}-{m:02d}")
        return None
    times, lat, lon, p, pv = read_erddap_nc(blob)
    exp_lat, exp_lon = cell_centers(idx)
    if not (np.allclose(lat, exp_lat, atol=1e-3) and np.allclose(lon, exp_lon, atol=1e-3)):
        raise ValueError(f"{dsid}: toạ độ trả về lệch lưới mong đợi")
    df = finalize(erddap_frame(times, lat, lon, p, pv or v.upper()))
    dest = _write(df, month_path("final", y, m, out, v))
    n_exp = int((t1 - t0).total_seconds() // 1800) + 1
    log(f"[ok] {dest.name} ({dsid}, {pv or v}): {len(times)}/{n_exp} mốc, "
        f"{len(blob) / 1e3:.0f} kB, {time.time() - t_start:.0f}s")
    return dest


def run_erddap(start: date, end: date, version: str = "auto", *, out: Path = OUT, session=None,
               workers: int = 2, log=print) -> list[Path]:
    """Tải nguyên tháng cho mọi tháng chạm [start, end]. Song song ≤ ``workers`` tháng."""
    session = session or plain_session()
    idx = bbox_index()
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        res = list(ex.map(lambda ym: erddap_month(session, *ym, version, idx, out, log), months))
    return [r for r in res if r]


# ====================== Nguồn 2: NASA GES DISC (cần Earthdata) ======================

def parse_listing(html: str, product: str = "final") -> list[Granule]:
    """Trang thư mục on-prem gpm1 → Granule (bỏ trùng, sắp theo giờ)."""
    coll = COLLECTIONS[product][0]
    seen: dict[str, Granule] = {}
    for m in GRANULE_RE.finditer(html):
        name = m.group(0)
        if name not in seen:
            start = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
            base = (f"{GESDISC}/opendap/GPM_L3/{coll}/{start.year}/"
                    f"{start.timetuple().tm_yday:03d}/{name}")
            seen[name] = Granule(name, start, m.group(3), base)
    return sorted(seen.values(), key=lambda g: g.start_utc)


def parse_cmr(payload: dict, product: str = "final") -> list[Granule]:
    """Kết quả CMR granules.json → Granule, URL OPeNDAP lấy từ link của CMR."""
    cid = COLLECTIONS[product][1]
    seen: dict[str, Granule] = {}
    for e in payload.get("feed", {}).get("entry", []):
        title = e.get("title", "")
        m = GRANULE_RE.search(title) or GRANULE_RE.search(e.get("producer_granule_id", ""))
        if not m or m.group(0) in seen:
            continue
        dap = next((lk["href"] for lk in e.get("links", [])
                    if lk.get("href", "").startswith(CLOUD_OPENDAP)), None)
        start = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        seen[m.group(0)] = Granule(m.group(0), start, m.group(3),
                                   dap or f"{CLOUD_OPENDAP}/collections/{cid}/granules/{title}")
    return sorted(seen.values(), key=lambda g: g.start_utc)


def list_granules(session, product: str, d: date, onprem: bool = False) -> list[Granule]:
    if onprem:
        url = (f"{GESDISC}/data/GPM_L3/{COLLECTIONS[product][0]}/{d.year}/"
               f"{d.timetuple().tm_yday:03d}/")
        html = http_get(session, url, binary=False)
        grans = parse_listing(html, product) if html else []
    else:
        q = urlencode({"collection_concept_id": COLLECTIONS[product][1],
                       "temporal": f"{d}T00:00:00Z,{d}T23:59:59Z",
                       "page_size": 100, "sort_key": "start_date"})
        txt = http_get(session, f"{CMR}/granules.json?{q}", binary=False)
        grans = parse_cmr(json.loads(txt), product) if txt else []
    return [g for g in grans if g.start_utc.date() == d]


def opendap_url(g: Granule, idx: tuple[int, int, int, int]) -> str:
    """URL trả NetCDF-4 chỉ chứa ô trong bbox. Cloud = DAP4 (giữ nhóm /Grid), on-prem = DAP2."""
    i0, i1, j0, j1 = idx
    if g.base.startswith(CLOUD_OPENDAP):
        ce = (f"/Grid/precipitation[0:0][{i0}:{i1}][{j0}:{j1}];"
              f"/Grid/lat[{j0}:{j1}];/Grid/lon[{i0}:{i1}]")
        return f"{g.base}.dap.nc4?dap4.ce={_enc(ce)}"
    ce = f"precipitation[0:0][{i0}:{i1}][{j0}:{j1}],lat[{j0}:{j1}],lon[{i0}:{i1}]"
    return f"{g.base}.nc4?{_enc(ce)}"


def _first(f: h5py.File, names: tuple[str, ...]):
    for n in names:
        if n in f:
            return f[n]
    raise KeyError(f"không thấy biến nào trong {names}; có: {list(f.keys())}")


def read_granule(src, idx: tuple[int, int, int, int] | None = None
                 ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """File IMERG (HDF5 gốc toàn cầu, hoặc NetCDF-4 OPeNDAP đã cắt) → (lat, lon, P[lon, lat]).

    ``src`` là đường dẫn hoặc bytes. Ô thiếu = NaN.
    """
    fh = h5py.File(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src, "r")
    with fh as f:
        ds = _first(f, PRECIP_VARS)
        grp = ds.name.rsplit("/", 1)[0]
        lat = np.asarray(f[f"{grp}/lat" if grp else "lat"][:], dtype=np.float64)
        lon = np.asarray(f[f"{grp}/lon" if grp else "lon"][:], dtype=np.float64)
        dims = ds.attrs.get("DimensionNames", b"time,lon,lat")
        dims = dims.decode() if isinstance(dims, bytes) else str(dims)
        lat_first = dims.replace(" ", "").endswith("lat,lon")
        if len(lon) == NLON and len(lat) == NLAT:          # file toàn cầu → cắt tại chỗ
            if idx is None:
                raise ValueError("file toàn cầu cần idx để cắt vùng")
            i0, i1, j0, j1 = idx
            si, sj = slice(i0, i1 + 1), slice(j0, j1 + 1)
            arr = np.asarray(ds[(0, sj, si) if lat_first else (0, si, sj)], dtype=np.float32)
            lat, lon = lat[sj], lon[si]
        else:
            arr = np.asarray(ds[0], dtype=np.float32)
        fill = ds.attrs.get("_FillValue")
    if lat_first:
        arr = arr.T
    arr = arr.copy()
    bad = arr < FILL_THRESHOLD
    if fill is not None:
        bad |= np.isclose(arr, np.float32(np.ravel(fill)[0]))
    arr[bad] = np.nan
    if arr.shape != (len(lon), len(lat)):
        raise ValueError(f"kích thước lệch: P{arr.shape} vs lon{len(lon)} lat{len(lat)}")
    return np.round(lat, 2), np.round(lon, 2), arr


def granule_frame(lat: np.ndarray, lon: np.ndarray, p: np.ndarray, g: Granule,
                  product: str) -> pl.DataFrame:
    """Một file 30 phút → bảng dài (mỗi ô một dòng)."""
    lon_g, lat_g = np.meshgrid(lon, lat, indexing="ij")   # cùng thứ tự với P[lon, lat]
    return pl.DataFrame({
        "time_utc": np.full(p.size, np.datetime64(g.start_utc, "us")),
        "lat": lat_g.ravel(),
        "lon": lon_g.ravel(),
        "precip_mm_hr": p.ravel(),
    }).with_columns(pl.lit(product).alias("product"), pl.lit(g.version).alias("version"))


def fetch_day(session, product: str, d: date, idx, workers: int = WORKERS,
              onprem: bool = False) -> tuple[pl.DataFrame | None, int]:
    """Tải các file 30 phút của một ngày. Trả (bảng, số file có trên server)."""
    grans = list_granules(session, product, d, onprem)
    if not grans:
        return None, 0
    exp_lat, exp_lon = cell_centers(idx)

    def one(g: Granule) -> pl.DataFrame | None:
        blob = http_get(session, opendap_url(g, idx))
        if blob is None:
            return None
        try:
            lat, lon, p = read_granule(blob, idx)
        except (OSError, KeyError) as e:   # server trả lỗi dạng text thay vì NetCDF-4
            raise ValueError(f"{g.name}: không đọc được phản hồi OPeNDAP ({e}): "
                             f"{blob[:200]!r}") from e
        if not (np.allclose(lat, exp_lat, atol=1e-3) and np.allclose(lon, exp_lon, atol=1e-3)):
            raise ValueError(f"{g.name}: toạ độ trả về lệch lưới mong đợi")
        return granule_frame(lat, lon, p, g, product)

    first = one(grans[0])   # tuần tự 1 file: chưa đăng nhập thì dừng ngay, không bắn nhiều luồng
    with ThreadPoolExecutor(max_workers=workers) as ex:
        rest = list(ex.map(one, grans[1:]))
    frames = [f for f in [first, *rest] if f is not None]
    return (pl.concat(frames) if frames else None), len(grans)


def merge_month(product: str, y: int, m: int, out: Path = OUT) -> Path | None:
    """Gộp file ngày → file tháng. Đủ ngày thì xoá _parts (đánh dấu tháng xong)."""
    pdir = parts_dir(product, y, m, out)
    files = sorted(pdir.glob("*.parquet")) if pdir.exists() else []
    if not files:
        return None
    dest = _write(finalize(pl.concat([pl.read_parquet(f) for f in files])),
                  month_path(product, y, m, out))
    if len(files) == calendar.monthrange(y, m)[1]:
        shutil.rmtree(pdir)
    return dest


def run_gesdisc(start: date, end: date, product: str = "final", *, out: Path = OUT,
                session=None, workers: int = WORKERS, onprem: bool = False,
                today: date | None = None, log=print) -> list[Path]:
    """Tải [start, end] (UTC) theo ngày, gộp theo tháng."""
    session = session or earthdata_session()
    idx = bbox_index()
    today = today or datetime.now(timezone.utc).date()
    written: list[Path] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        if month_done(product, y, m, out):
            log(f"[bỏ qua] {month_path(product, y, m, out).name} đã đủ")
        else:
            pdir = parts_dir(product, y, m, out)
            last = calendar.monthrange(y, m)[1]
            for d in (date(y, m, k) for k in range(1, last + 1)):
                part = pdir / f"{d:%Y%m%d}.parquet"
                if not (start <= d <= end) or part.exists():
                    continue
                t0 = time.time()
                df, n = fetch_day(session, product, d, idx, workers, onprem)
                if df is None:
                    log(f"[trống] {d} — server chưa có file")
                    continue
                got = df["time_utc"].n_unique()
                # Ngày sát hiện tại có thể chưa đủ 48 file (Late/Early đang ra) → không lưu, lần sau tải lại
                if got < SLOTS_PER_DAY and (today - d).days <= 2:
                    log(f"[chưa đủ] {d}: {got}/{SLOTS_PER_DAY} — chưa lưu")
                    continue
                pdir.mkdir(parents=True, exist_ok=True)
                df.write_parquet(part)
                log(f"[ok] {d} {product}: {got}/{n} file, {time.time() - t0:.1f}s")
            dest = merge_month(product, y, m, out)
            if dest:
                written.append(dest)
                log(f"[ghi] {dest.name}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return written


# ====================== So với ERA5 theo giờ ======================

def to_hourly(df: pl.DataFrame) -> pl.DataFrame:
    """30 phút → lượng mưa giờ (mm), nhãn giờ VN ở CUỐI giờ.

    Khớp quy ước Open-Meteo/ERA5: ``precipitation`` lúc t là tổng của giờ trước t.
    Hai khoảng [HH:00, HH:30) và [HH:30, HH+1) → nhãn HH+1:00. Giờ thiếu nửa nào thì bỏ.
    """
    return (df.with_columns(
                (pl.col("time").dt.truncate("1h") + timedelta(hours=1)).alias("time_h"),
                (pl.col("precip_mm_hr") * 0.5).alias("mm"))
              .group_by("time_h", "lat", "lon")
              .agg(pl.col("mm").sum(), pl.col("mm").count().alias("n"))
              .filter(pl.col("n") == 2)
              .select(pl.col("time_h").alias("time"), "lat", "lon",
                      pl.col("mm").cast(pl.Float64).alias("precip_mm"))
              .sort("time", "lat", "lon"))


def compare_era5(imerg: pl.DataFrame, era5: pl.DataFrame) -> dict:
    """Tương quan giờ / ngày và tỷ lệ tổng IMERG/ERA5.

    ``era5``: cột time (giờ VN, nhãn cuối giờ), lat, lon, precipitation (mm).
    * Trung bình vùng: ô IMERG có tâm trong khung điểm ERA5 nới ±0,05°.
    * Từng điểm ERA5: trung bình các ô IMERG có tâm cách điểm ±0,05° (4 ô bao quanh).
    Ngày = ngày giờ VN, chỉ lấy ngày đủ 24 giờ ở cả hai nguồn.
    """
    h = to_hourly(imerg)
    la0, la1 = era5["lat"].min() - 0.051, era5["lat"].max() + 0.051
    lo0, lo1 = era5["lon"].min() - 0.051, era5["lon"].max() + 0.051
    hz = h.filter(pl.col("lat").is_between(la0, la1) & pl.col("lon").is_between(lo0, lo1))
    a = hz.group_by("time").agg(pl.col("precip_mm").mean().alias("imerg"))
    b = era5.group_by("time").agg(pl.col("precipitation").mean().alias("era5"))
    hh = a.join(b, on="time", how="inner").drop_nulls().sort("time")
    dd = (hh.with_columns((pl.col("time") - timedelta(hours=1)).dt.date().alias("day"))
            .group_by("day").agg(pl.col("imerg").sum(), pl.col("era5").sum(), pl.len().alias("n"))
            .filter(pl.col("n") == 24))

    # Từng điểm: ghép bằng khoá lưới 0,05° (số nguyên) để khỏi so sánh float
    key = [((pl.col(c) * 20).round(0).cast(pl.Int32)).alias(f"k{c}") for c in ("lat", "lon")]
    pts = era5.select("lat", "lon").unique().with_columns(key)
    nb = pl.concat([pts.with_columns((pl.col("klat") + a_).alias("cklat"),
                                     (pl.col("klon") + o_).alias("cklon"))
                    for a_ in (-1, 1) for o_ in (-1, 1)])
    hk = h.with_columns(key).rename({"klat": "cklat", "klon": "cklon",
                                     "lat": "clat", "lon": "clon"})
    pi = (nb.join(hk, on=["cklat", "cklon"], how="inner")
            .group_by("lat", "lon", "time").agg(pl.col("precip_mm").mean().alias("imerg")))
    pj = pi.join(era5.select("time", "lat", "lon", pl.col("precipitation").alias("era5")),
                 on=["time", "lat", "lon"], how="inner").drop_nulls()
    per_pt = (pj.group_by("lat", "lon").agg(pl.corr("imerg", "era5").alias("r"))
                .drop_nans().drop_nulls())

    def corr(df: pl.DataFrame) -> float | None:
        return df.select(pl.corr("imerg", "era5")).item() if df.height > 2 else None

    return {
        "n_hours": hh.height,
        "n_days": dd.height,
        "r_hourly_area": corr(hh),
        "r_daily_area": corr(dd),
        "ratio_total": (hh["imerg"].sum() / hh["era5"].sum()) if hh["era5"].sum() else None,
        "imerg_total_mm": hh["imerg"].sum(),
        "era5_total_mm": hh["era5"].sum(),
        "r_hourly_point_median": per_pt["r"].median() if per_pt.height else None,
        "n_points": per_pt.height,
    }


def load_era5_month(y: int, m: int) -> pl.DataFrame:
    files = sorted((cfg.DATA_RAW / "rain_hourly").glob(f"rh_*_{y}.parquet"))
    if not files:
        raise FileNotFoundError(f"không có data/raw/rain_hourly/rh_*_{y}.parquet")
    return (pl.concat([pl.read_parquet(f, columns=["time", "precipitation", "lat", "lon"])
                       for f in files])
              .filter((pl.col("time").dt.year() == y) & (pl.col("time").dt.month() == m)))


# ---------- CLI ----------

def _parse_day(s: str, end: bool = False) -> date:
    if re.fullmatch(r"\d{4}-\d{2}", s):
        y, m = map(int, s.split("-"))
        return date(y, m, calendar.monthrange(y, m)[1] if end else 1)
    return date.fromisoformat(s)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Tải IMERG 30 phút cắt FINE_BBOX, ghi parquet theo tháng.")
    ap.add_argument("--start", help="YYYY-MM hoặc YYYY-MM-DD (UTC)")
    ap.add_argument("--end", help="YYYY-MM hoặc YYYY-MM-DD (UTC), gồm cả ngày cuối")
    ap.add_argument("--source", choices=["erddap", "gesdisc"], default="erddap")
    ap.add_argument("--product", choices=list(COLLECTIONS), default="final")
    ap.add_argument("--version", choices=["auto", "v06", "v07"], default="auto",
                    help="chỉ cho ERDDAP: auto = V07 nếu có, không thì V06")
    ap.add_argument("--workers", type=int, default=None,
                    help="số luồng (mặc định: ERDDAP 2 tháng song song, GES DISC 8 file)")
    ap.add_argument("--onprem", action="store_true", help="GES DISC: dùng máy chủ cũ gpm1")
    ap.add_argument("--dry-run", action="store_true",
                    help="chỉ liệt kê nguồn/URL, không tải số liệu")
    ap.add_argument("--compare-era5", metavar="YYYY-MM",
                    help="so file tháng đã tải với ERA5 theo giờ trong data/raw/rain_hourly")
    a = ap.parse_args(argv)

    if a.compare_era5:
        y, m = map(int, a.compare_era5.split("-"))
        cands = [month_path(a.product, y, m, version=v) for v in
                 (("v07", "v06") if a.version == "auto" else (a.version,))]
        f = next((p for p in cands if p.exists()), None)
        if f is None:
            raise SystemExit(f"chưa có file: {', '.join(p.name for p in cands)}")
        print(f"So {f.name} với ERA5 (data/raw/rain_hourly)")
        im = pl.read_parquet(f)
        res = compare_era5(im, load_era5_month(y, m))
        for k, v in res.items():
            print(f"{k:24s} {v:.3f}" if isinstance(v, float) else f"{k:24s} {v}")
        return

    if not (a.start and a.end):
        ap.error("cần --start và --end")
    if a.product != "final" and a.source == "erddap":
        ap.error("ERDDAP chỉ có Final — Late/Early dùng --source gesdisc")
    start, end = _parse_day(a.start), _parse_day(a.end, end=True)
    idx = bbox_index()
    lat, lon = cell_centers(idx)
    print(f"IMERG {a.source}/{a.product} {start} → {end}; ô lon {lon[0]}..{lon[-1]} × "
          f"lat {lat[0]}..{lat[-1]} = {len(lon) * len(lat)} ô")

    if a.source == "erddap":
        if a.dry_run:
            s = plain_session()
            for y in range(start.year, end.year + 1):
                for v in ("v07", "v06"):
                    info = erddap_info(s, erddap_dataset_id(y, v))
                    print(f"{erddap_dataset_id(y, v):24s} "
                          + (f"{info['start']} → {info['end']} ({info['var']})" if info else "không có"))
            return
        run_erddap(start, end, a.version, workers=a.workers or 2)
        return

    if a.dry_run:
        s = earthdata_session()
        d = start
        while d <= end:
            g = list_granules(s, a.product, d, a.onprem)
            print(f"{d}: {len(g)} file" + (f", vd {opendap_url(g[0], idx)}" if g else ""))
            d += timedelta(days=1)
        return
    if not has_credentials():
        raise SystemExit("Chưa có thông tin đăng nhập NASA Earthdata (EARTHDATA_TOKEN hoặc "
                         "~/_netrc). Xem docstring đầu file src/ingest/imerg.py.")
    run_gesdisc(start, end, a.product, workers=a.workers or WORKERS, onprem=a.onprem)


if __name__ == "__main__":
    main()
