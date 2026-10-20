"""IMERG: lưới, đọc file giả lập (HDF5 GES DISC + NetCDF-3 ERDDAP), thử lại, resume, so ERA5.

Không cần mạng: file được dựng đúng cấu trúc thật — HDF5 gốc (nhóm /Grid, mảng
[time][lon][lat], _FillValue -9999,9) và NetCDF-3 ERDDAP ([time][latitude][longitude],
missing_value = 0) — còn server được giả lập bằng FakeSession.
"""

from __future__ import annotations

import io
import json
from datetime import date, datetime, timedelta

import h5py
import numpy as np
import polars as pl
import pytest
from scipy.io import netcdf_file

from src.ingest import imerg

IDX = (2870, 2879, 1058, 1067)
LAT, LON = imerg.cell_centers(IDX)


def _value(i: int, j: int) -> float:
    """Giá trị nhận diện ô (i = chỉ số lon, j = chỉ số lat): đọc ra là biết có lật trục không."""
    return (i - 2870) * 10 + (j - 1058) * 0.5


# ---------- Dựng file giả lập ----------

def _write_grid(f: h5py.File, grp: str, lat, lon, p):
    g = f.require_group(grp) if grp != "/" else f
    ds = g.create_dataset("precipitation", data=p[None], dtype="f4",
                          chunks=(1, min(len(lon), 145), min(len(lat), 1800)), compression="gzip")
    ds.attrs["DimensionNames"] = b"time,lon,lat"
    ds.attrs["Units"] = b"mm/hr"
    ds.attrs["_FillValue"] = np.float32(-9999.9)
    g.create_dataset("lat", data=np.asarray(lat, dtype="f4"))
    g.create_dataset("lon", data=np.asarray(lon, dtype="f4"))


def _subset_array() -> np.ndarray:
    return np.array([[_value(i, j) for j in range(IDX[2], IDX[3] + 1)]
                     for i in range(IDX[0], IDX[1] + 1)], dtype="f4")


def full_granule_bytes() -> bytes:
    """HDF5 gốc toàn cầu 3600 × 1800 như GES DISC phát hành (nén gzip cho nhẹ)."""
    p = np.zeros((imerg.NLON, imerg.NLAT), dtype="f4")
    p[IDX[0]:IDX[1] + 1, IDX[2]:IDX[3] + 1] = _subset_array()
    p[IDX[0], IDX[2]] = -9999.9                                   # một ô thiếu
    buf = io.BytesIO()
    with h5py.File(buf, "w") as f:
        _write_grid(f, "Grid", -89.95 + 0.1 * np.arange(imerg.NLAT),
                    -179.95 + 0.1 * np.arange(imerg.NLON), p)
    return buf.getvalue()


def subset_granule_bytes(group: str = "/") -> bytes:
    """NetCDF-4 OPeNDAP đã cắt: on-prem DAP2 để biến ở gốc, cloud DAP4 giữ nhóm /Grid."""
    buf = io.BytesIO()
    with h5py.File(buf, "w") as f:
        _write_grid(f, group, LAT, LON, _subset_array())
    return buf.getvalue()


def erddap_nc_bytes(tmp_path, t0: datetime, nt: int, var: str = "precipitationCal",
                    version: str = "V06B") -> bytes:
    """NetCDF-3 như ERDDAP griddap trả về: [time][latitude][longitude], 0 = không mưa."""
    f = tmp_path / f"erd_{t0:%Y%m}_{var}.nc"
    with netcdf_file(f, "w") as nc:
        nc.FileHeader = f"DOI=10.5067/GPM/IMERG/3B-HH/07;\nProductVersion={version};\n"
        for name, n in (("time", nt), ("latitude", 10), ("longitude", 10)):
            nc.createDimension(name, n)
        t = nc.createVariable("time", "f8", ("time",))
        t[:] = [(t0 - datetime(1970, 1, 1)).total_seconds() + 1800 * k for k in range(nt)]
        nc.createVariable("latitude", "f4", ("latitude",))[:] = LAT
        nc.createVariable("longitude", "f4", ("longitude",))[:] = LON
        v = nc.createVariable(var, "f4", ("time", "latitude", "longitude"))
        v._FillValue = np.float32(-9999.9)
        v.missing_value = np.float32(0.0)
        data = np.broadcast_to(_subset_array().T, (nt, 10, 10)).copy()   # → [time, lat, lon]
        data[0, 0, 0] = 0.0                                              # không mưa
        data[0, 0, 1] = -9999.9                                          # thiếu
        v[:] = data
    return f.read_bytes()


def erddap_info_csv(start: str, end: str, var: str) -> str:
    return ("Row Type,Variable Name,Attribute Name,Data Type,Value\n"
            f"attribute,NC_GLOBAL,time_coverage_end,String,{end}\n"
            f"attribute,NC_GLOBAL,time_coverage_start,String,{start}\n"
            "dimension,time,,double,\"nValues=17568, evenlySpaced=true\"\n"
            f"variable,{var},,float,\"time, latitude, longitude\"\n"
            f"attribute,{var},units,String,MM/Hr\n")


# ---------- Server giả ----------

class FakeResp:
    def __init__(self, status=200, content=b"", url="https://x.nasa.gov/y", ctype="application/x-netcdf"):
        self.status_code, self.url = status, url
        self.content = content.encode() if isinstance(content, str) else content
        self.headers = {"Content-Type": ctype}
        self.text = self.content.decode("utf-8", "ignore")
        self.ok = status < 400


def _granule_names(d: date, n: int, late: bool = False) -> list[str]:
    out = []
    for k in range(n):
        s = datetime(d.year, d.month, d.day) + timedelta(minutes=30 * k)
        e = s + timedelta(minutes=29, seconds=59)
        out.append(f"3B-HHR{'-L' if late else ''}.MS.MRG.3IMERG.{s:%Y%m%d}-S{s:%H%M%S}-"
                   f"E{e:%H%M%S}.{30 * k:04d}.V07B.HDF5")
    return out


class FakeSession:
    """CMR / thư mục gpm1 / OPeNDAP / ERDDAP giả, ghi lại mọi URL đã gọi."""

    def __init__(self, per_day: int = 2, script=None, erddap=None):
        self.per_day, self.script, self.calls = per_day, list(script or []), []
        self.blob = subset_granule_bytes("Grid")
        self.erddap = erddap or {}      # dataset id → (info csv, nc bytes)

    def get(self, url, timeout=None):
        self.calls.append(url)
        if self.script:
            return self.script.pop(0)
        if "cmr.earthdata.nasa.gov" in url:
            d = date.fromisoformat(url.split("temporal=")[1][:10])
            entries = [{"title": f"GPM_3IMERGHH.07:{n}", "links": [
                {"href": f"https://data.gesdisc.earthdata.nasa.gov/data/{n}"},
                {"href": f"{imerg.CLOUD_OPENDAP}/collections/C1/granules/GPM_3IMERGHH.07%3A{n}"}]}
                for n in _granule_names(d, self.per_day)]
            return FakeResp(content=json.dumps({"feed": {"entry": entries}}), ctype="application/json")
        if "/data/GPM_L3/" in url:
            y, doy = url.rstrip("/").split("/")[-2:]
            d = date(int(y), 1, 1) + timedelta(days=int(doy) - 1)
            html = "".join(f'<a href="{n}">{n}</a><a href="{n}.xml">x</a>'
                           for n in _granule_names(d, self.per_day))
            return FakeResp(content=html, ctype="text/html")
        if "/erddap/info/" in url:
            dsid = url.split("/info/")[1].split("/")[0]
            return FakeResp(content=self.erddap[dsid][0], ctype="text/csv") if dsid in self.erddap \
                else FakeResp(404)
        if "/erddap/griddap/" in url:
            dsid = url.split("/griddap/")[1].split(".nc")[0]
            return FakeResp(content=self.erddap[dsid][1])
        return FakeResp(content=self.blob)


# ---------- Lưới & URL ----------

def test_bbox_index_khop_fine_bbox():
    assert imerg.bbox_index() == IDX
    assert LAT[0] == 15.85 and LAT[-1] == 16.75 and len(LAT) == 10
    assert LON[0] == 107.05 and LON[-1] == 107.95 and len(LON) == 10


def test_parse_listing_onprem_bo_trung_va_url_dap2():
    names = _granule_names(date(2020, 10, 1), 2)
    html = "".join(f'<a href="{n}"><a href="{n}.xml">' for n in reversed(names * 2))
    g = imerg.parse_listing(html, "final")
    assert [x.start_utc for x in g] == [datetime(2020, 10, 1, 0, 0), datetime(2020, 10, 1, 0, 30)]
    assert g[0].base.startswith(imerg.GESDISC + "/opendap/GPM_L3/GPM_3IMERGHH.07/2020/275/")
    u = imerg.opendap_url(g[0], IDX)
    assert u.endswith(".HDF5.nc4?precipitation%5B0:0%5D%5B2870:2879%5D%5B1058:1067%5D,"
                      "lat%5B1058:1067%5D,lon%5B2870:2879%5D")


def test_parse_cmr_lay_link_opendap_cloud_va_url_dap4():
    late = _granule_names(date(2026, 10, 19), 1, late=True)[0].replace("V07B", "V07C")
    payload = {"feed": {"entry": [
        {"title": f"GPM_3IMERGHHL.07:{late}", "links": [{"href": "https://other/x"}]}]}}
    g = imerg.parse_cmr(payload, "late")[0]
    assert g.version == "V07C" and g.start_utc == datetime(2026, 10, 19)
    assert g.base == f"{imerg.CLOUD_OPENDAP}/collections/C2723754845-GES_DISC/granules/GPM_3IMERGHHL.07:{late}"
    u = imerg.opendap_url(g, IDX)
    assert ".HDF5.dap.nc4?dap4.ce=/Grid/precipitation%5B0:0%5D%5B2870:2879%5D%5B1058:1067%5D;" in u
    assert u.endswith(";/Grid/lat%5B1058:1067%5D;/Grid/lon%5B2870:2879%5D")


def test_erddap_url_va_info():
    u = imerg.erddap_url("precipitation_2020", "precipitationCal", datetime(2020, 10, 1),
                         datetime(2020, 10, 31, 23, 30), IDX)
    assert u == (f"{imerg.ERDDAP}/griddap/precipitation_2020.nc?precipitationCal"
                 "%5B(2020-10-01T00:00:00Z):1:(2020-10-31T23:30:00Z)%5D"
                 "%5B(15.85):1:(16.75)%5D%5B(107.05):1:(107.95)%5D")
    info = imerg.parse_erddap_info(erddap_info_csv("2024-01-01T00:00:00Z", "2024-06-02T13:30:00Z",
                                                   "precipitationCal"))
    assert info == {"start": datetime(2024, 1, 1), "end": datetime(2024, 6, 2, 13, 30),
                    "var": "precipitationCal"}


# ---------- Đọc file ----------

@pytest.mark.parametrize("make", [full_granule_bytes, subset_granule_bytes,
                                  lambda: subset_granule_bytes("Grid")])
def test_read_granule_dung_huong_lon_lat(make):
    lat, lon, p = imerg.read_granule(make(), IDX)
    assert p.shape == (10, 10) and lat[0] == 15.85 and lon[-1] == 107.95
    assert p[3, 7] == pytest.approx(_value(2873, 1065))           # P[lon, lat]
    if make is full_granule_bytes:
        assert np.isnan(p[0, 0]) and np.isfinite(p[1:, :]).all()   # _FillValue → NaN


def test_read_granule_tu_duong_dan(tmp_path):
    f = tmp_path / "g.HDF5"
    f.write_bytes(full_granule_bytes())
    assert imerg.read_granule(f, IDX)[2][9, 9] == pytest.approx(_value(2879, 1067))


def test_read_erddap_nc_giu_so_0_va_lat_truoc_lon(tmp_path):
    blob = erddap_nc_bytes(tmp_path, datetime(2020, 10, 1), 3)
    times, lat, lon, p, ver = imerg.read_erddap_nc(blob)
    assert ver == "V06B" and p.shape == (3, 10, 10)
    assert times[1] == np.datetime64("2020-10-01T00:30:00")
    assert p[0, 0, 0] == 0.0 and np.isnan(p[0, 0, 1])            # 0 vẫn là 0, chỉ -9999,9 là thiếu
    df = imerg.finalize(imerg.erddap_frame(times, lat, lon, p, ver))
    row = df.filter((pl.col("time_utc").dt.minute() == 30) & (pl.col("lat") == 16.45)
                    & (pl.col("lon") == 107.35))
    assert row["precip_mm_hr"][0] == pytest.approx(_value(2873, 1064))
    assert df.height == 300 and df["precip_mm_hr"].null_count() == 1


def test_finalize_gio_viet_nam_va_schema():
    lat, lon, p = imerg.read_granule(full_granule_bytes(), IDX)
    g = imerg.Granule("x", datetime(2020, 10, 1, 17, 30), "V07B")
    df = imerg.finalize(imerg.granule_frame(lat, lon, p, g, "final"))
    assert df.columns == ["time_utc", "time", "lat", "lon", "precip_mm_hr", "product", "version"]
    assert df.schema["precip_mm_hr"] == pl.Float32 and df["precip_mm_hr"].null_count() == 1
    assert str(df.schema["time_utc"].time_zone) == "UTC"
    assert df["time"][0] == datetime(2020, 10, 2, 0, 30)          # 17:30 UTC = 00:30 hôm sau giờ VN


# ---------- Mạng ----------

def test_http_get_thu_lai_khi_loi_server():
    s = FakeSession(script=[FakeResp(503), FakeResp(200, b"abc")])
    assert imerg.http_get(s, "https://x/y", sleep_s=0) == b"abc"
    assert len(s.calls) == 2


def test_http_get_404_la_khong_co_file():
    assert imerg.http_get(FakeSession(script=[FakeResp(404)]), "https://x", sleep_s=0) is None


@pytest.mark.parametrize("resp", [
    FakeResp(401),
    FakeResp(200, b"<html>login</html>", url="https://urs.earthdata.nasa.gov/oauth/authorize",
             ctype="text/html"),
])
def test_http_get_chua_dang_nhap_dung_ngay(resp):
    s = FakeSession(script=[resp, FakeResp(200, b"ok")])
    with pytest.raises(imerg.AuthError):
        imerg.http_get(s, "https://x", sleep_s=0)
    assert len(s.calls) == 1                                       # không thử lại vô ích


def test_phan_hoi_loi_dang_text_bao_ro():
    s = FakeSession(per_day=1)
    s.blob = b'Error { code = 400; message = "Constraint expression parse error"; }'
    with pytest.raises(ValueError, match="không đọc được phản hồi OPeNDAP"):
        imerg.fetch_day(s, "final", date(2020, 10, 1), IDX, workers=1)


def test_has_credentials_doc_netrc(tmp_path, monkeypatch):
    for k in ("EARTHDATA_TOKEN", "NETRC"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert not imerg.has_credentials()
    (tmp_path / "_netrc").write_text("machine urs.earthdata.nasa.gov login u password p\n")
    assert imerg.has_credentials()


def test_token_khong_gui_sang_erddap(monkeypatch):
    monkeypatch.setenv("EARTHDATA_TOKEN", "abc")
    assert imerg.earthdata_session().headers["Authorization"] == "Bearer abc"
    assert "Authorization" not in imerg.plain_session().headers


def test_cli_gesdisc_dung_som_khi_chua_co_tai_khoan(monkeypatch):
    monkeypatch.setattr(imerg, "has_credentials", lambda: False)
    monkeypatch.setattr(imerg, "run_gesdisc", lambda *a, **k: pytest.fail("không được tải"))
    with pytest.raises(SystemExit, match="Earthdata"):
        imerg.main(["--source", "gesdisc", "--start", "2020-10", "--end", "2020-10"])
    with pytest.raises(SystemExit):
        imerg.main(["--product", "late", "--start", "2020-10", "--end", "2020-10"])  # ERDDAP chỉ có Final
    assert imerg._parse_day("2020-02", end=True) == date(2020, 2, 29)


# ---------- ERDDAP: tải theo tháng ----------

@pytest.fixture
def erddap_server(tmp_path):
    imerg._INFO_CACHE.clear()
    yield FakeSession(erddap={
        "precipitation_2020": (erddap_info_csv("2020-01-01T00:00:00Z", "2020-12-31T23:30:00Z",
                                               "precipitationCal"),
                               erddap_nc_bytes(tmp_path, datetime(2020, 10, 1), 31 * 48)),
        "precipitation_2024": (erddap_info_csv("2024-01-01T00:00:00Z", "2024-06-02T13:30:00Z",
                                               "precipitationCal"), b""),
        "precipitation_2024_v07": (erddap_info_csv("2024-01-01T00:00:00Z", "2024-12-31T23:30:00Z",
                                                   "precipitation"),
                                   erddap_nc_bytes(tmp_path, datetime(2024, 3, 1), 31 * 48,
                                                   var="precipitation", version="V07B")),
    })
    imerg._INFO_CACHE.clear()


def test_erddap_auto_chon_v07_neu_co_khong_thi_v06(erddap_server, tmp_path):
    out = tmp_path / "imerg"
    imerg.run_erddap(date(2020, 10, 1), date(2020, 10, 1), "auto", out=out,
                     session=erddap_server, log=lambda *_: None)
    imerg.run_erddap(date(2024, 3, 5), date(2024, 3, 5), "auto", out=out,
                     session=erddap_server, log=lambda *_: None)
    assert sorted(p.name for p in out.glob("*.parquet")) == ["imerg_202403.parquet",
                                                            "imerg_v06_202010.parquet"]
    v06 = pl.read_parquet(out / "imerg_v06_202010.parquet")
    assert v06.height == 31 * 48 * 100 and set(v06["version"]) == {"V06B"}
    assert set(pl.read_parquet(out / "imerg_202403.parquet")["version"]) == {"V07B"}
    # tải nguyên tháng dù chỉ xin 1 ngày; request chứa đúng khung thời gian của tháng
    grid = [u for u in erddap_server.calls if "/griddap/" in u]
    assert "(2020-10-01T00:00:00Z):1:(2020-10-31T23:30:00Z)" in grid[0]


def test_erddap_resume_va_ngoai_pham_vi(erddap_server, tmp_path):
    out = tmp_path / "imerg"
    logs: list[str] = []
    imerg.run_erddap(date(2020, 10, 1), date(2020, 10, 31), "v06", out=out,
                     session=erddap_server, log=logs.append)
    n = len(erddap_server.calls)
    imerg.run_erddap(date(2020, 10, 1), date(2020, 10, 31), "v06", out=out,
                     session=erddap_server, log=logs.append)
    assert not [u for u in erddap_server.calls[n:] if "/griddap/" in u]   # đã có → không tải lại
    assert imerg.run_erddap(date(2024, 7, 1), date(2024, 7, 31), "v06", out=out,
                            session=erddap_server, log=logs.append) == []  # V06 dừng 02/06/2024
    assert any("[không có]" in s for s in logs)


# ---------- GES DISC: tải theo ngày + resume ----------

@pytest.mark.parametrize("onprem", [False, True])
def test_gesdisc_ghi_thang_va_resume(tmp_path, onprem):
    s = FakeSession(per_day=2)
    if onprem:
        s.blob = subset_granule_bytes("/")
    out = tmp_path / "imerg"
    quiet = {"out": out, "session": s, "workers": 2, "onprem": onprem, "log": lambda *_: None}
    imerg.run_gesdisc(date(2020, 10, 1), date(2020, 10, 3), "final", **quiet)
    assert imerg.month_path("final", 2020, 10, out).exists()
    assert not imerg.month_done("final", 2020, 10, out)           # mới 3 ngày → giữ _parts
    n_first = len(s.calls)
    assert n_first == 3 * (1 + 2)                                  # 3 ngày × (1 listing + 2 file)
    data = [u for u in s.calls if "cmr.earthdata" not in u and "/data/GPM_L3/" not in u]
    assert len(data) == 6
    if onprem:
        assert all(u.startswith(imerg.GESDISC + "/opendap/") and ".nc4?precipitation" in u for u in data)
    else:
        assert all(u.startswith(imerg.CLOUD_OPENDAP) and ".dap.nc4?dap4.ce=" in u for u in data)

    imerg.run_gesdisc(date(2020, 10, 1), date(2020, 10, 31), "final", **quiet)
    assert len(s.calls) - n_first == 28 * 3                        # chỉ tải 28 ngày còn lại
    assert imerg.month_done("final", 2020, 10, out)
    df = pl.read_parquet(imerg.month_path("final", 2020, 10, out))
    assert df.height == 31 * 2 * 100 and df["time_utc"].is_sorted()

    n = len(s.calls)
    imerg.run_gesdisc(date(2020, 10, 1), date(2020, 10, 31), "final", **quiet)
    assert len(s.calls) == n                                       # tháng xong → không gọi server


def test_gesdisc_khong_luu_ngay_gan_hien_tai_chua_du(tmp_path):
    out = tmp_path / "imerg"
    imerg.run_gesdisc(date(2026, 10, 19), date(2026, 10, 19), "late", out=out,
                      session=FakeSession(per_day=5), today=date(2026, 10, 20), log=lambda *_: None)
    assert not imerg.parts_dir("late", 2026, 10, out).exists()
    assert imerg.month_path("late", 2026, 10, out).name == "imerg_late_202610.parquet"
    assert not imerg.month_path("late", 2026, 10, out).exists()


# ---------- So ERA5 ----------

def _synthetic_imerg(days: int = 4) -> pl.DataFrame:
    rng = np.random.default_rng(0)
    t0 = datetime(2020, 10, 1, 17, 0)                              # = 00:00 ngày 02/10 giờ VN
    rows = [(t0 + timedelta(minutes=30 * k), la, lo,
             float(rng.gamma(0.5, 4.0)) if rng.random() < 0.4 else 0.0)
            for k in range(days * 48) for la in (16.35, 16.45) for lo in (107.45, 107.55)]
    df = pl.DataFrame(rows, schema={"time_utc": pl.Datetime("us"), "lat": pl.Float64,
                                    "lon": pl.Float64, "precip_mm_hr": pl.Float32}, orient="row")
    return imerg.finalize(df.with_columns(pl.lit("final").alias("product"),
                                          pl.lit("V07B").alias("version")))


def test_to_hourly_nhan_cuoi_gio_va_doi_don_vi():
    df = _synthetic_imerg(1)
    h = imerg.to_hourly(df)
    assert h["time"].min() == datetime(2020, 10, 2, 1, 0)          # [00:00, 01:00) VN → nhãn 01:00
    cell = df.filter((pl.col("lat") == 16.35) & (pl.col("lon") == 107.45)).head(2)
    first = h.filter((pl.col("lat") == 16.35) & (pl.col("lon") == 107.45))["precip_mm"][0]
    assert first == pytest.approx(float(cell["precip_mm_hr"].sum()) * 0.5, rel=1e-5)


def test_compare_era5_trung_khop_hoan_hao():
    im = _synthetic_imerg(4)
    h = imerg.to_hourly(im)
    era5 = (h.group_by("time").agg(pl.col("precip_mm").mean().alias("precipitation"))
              .with_columns(pl.lit(16.4).alias("lat"), pl.lit(107.5).alias("lon")))
    res = imerg.compare_era5(im, era5)
    assert res["n_points"] == 1 and res["n_days"] >= 3
    assert res["r_hourly_area"] == pytest.approx(1.0, abs=1e-6)
    assert res["r_daily_area"] == pytest.approx(1.0, abs=1e-6)
    assert res["r_hourly_point_median"] == pytest.approx(1.0, abs=1e-6)
    assert res["ratio_total"] == pytest.approx(1.0, rel=1e-6)
    res2 = imerg.compare_era5(im, era5.with_columns(pl.col("precipitation") * 2))
    assert res2["ratio_total"] == pytest.approx(0.5, rel=1e-6)
