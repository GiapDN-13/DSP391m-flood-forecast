"""PERSIANN-CCS: định vị lưới, giải mã nhị phân, nhãn giờ, resume — không cần mạng."""

import gzip
import json
from datetime import date, datetime, timedelta

import numpy as np
import polars as pl
import pytest
import requests

from src import config as cfg
from src.ingest import persiann_ccs as pc

ROWS, COLS = pc.bbox_index(cfg.FINE_BBOX)
LATS, LONS = pc.cell_centers(ROWS, COLS)


# ---------------------------------------------------------------- giả lập HTTP

class FakeResp:
    def __init__(self, data: bytes = b"", status: int = 200):
        self.data, self.status_code, self.sent = data, status, 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def iter_content(self, n):
        for i in range(0, len(self.data), n):
            self.sent += len(self.data[i:i + n])
            yield self.data[i:i + n]

    @property
    def content(self):
        return self.data

    @property
    def text(self):
        return self.data.decode()


class FakeSession:
    def __init__(self, route):
        self.route, self.calls = route, []

    def get(self, url, **kw):
        self.calls.append(url)
        return self.route(url, len(self.calls))


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(pc.time, "sleep", lambda s: None)


def _global_gz(seed: int = 0) -> tuple[bytes, np.ndarray]:
    """Lưới toàn cầu int16 big-endian giả, có vài giá trị đánh dấu trong khung Huế."""
    a = np.zeros((pc.NROWS, pc.NCOLS), dtype=">i2")
    a[1080, 2675] = 1234             # góc tây bắc khung → 12,34 mm
    a[1092, 2687] = 5                # giữa khung → 0,05 mm
    a[1104, 2699] = pc.NODATA        # góc đông nam → thiếu
    a[1079, 2675] = 999              # ngay NGOÀI khung (phía bắc) — không được lọt vào
    a[1080, 2674] = 999              # ngay ngoài khung (phía tây)
    rng = np.random.default_rng(seed)
    a[1200:1500] = rng.integers(0, 3000, size=(300, pc.NCOLS))   # nhiễu phía nam: khó nén
    return gzip.compress(a.tobytes(), compresslevel=1), a


# ---------------------------------------------------------------- lưới, tên file

def test_khung_fine_bbox_dung_hang_cot_va_tam_o():
    assert (ROWS.start, ROWS.stop, COLS.start, COLS.stop) == (1080, 1105, 2675, 2700)
    assert len(LATS) == 25 and len(LONS) == 25
    assert LATS[0] == 16.78 and LATS[-1] == 15.82          # bắc → nam, tâm ô
    assert LONS[0] == 107.02 and LONS[-1] == 107.98
    assert np.all(LATS > cfg.FINE_BBOX["lat_min"]) and np.all(LATS < cfg.FINE_BBOX["lat_max"])


def test_khung_qua_kinh_tuyen_0_bao_loi():
    with pytest.raises(ValueError):
        pc.bbox_index({"lat_min": 0, "lat_max": 1, "lon_min": 359.0, "lon_max": 1.0})


def test_ten_file_theo_ngay_trong_nam_va_gio_bat_dau():
    assert pc.file_url(datetime(2020, 10, 1, 0)).endswith("/2020/rgccs1h2027500.bin.gz")
    assert pc.file_url(datetime(2003, 12, 31, 23)).endswith("/2003/rgccs1h0336523.bin.gz")
    assert pc.file_url(datetime(2020, 12, 31, 5)).endswith("/2020/rgccs1h2036605.bin.gz")  # năm nhuận
    assert "VLD20201001.S20201001T000000.E20201001T235959" in pc.gdex_url(date(2020, 10, 1))


# ---------------------------------------------------------------- giải mã + tải

def test_giai_ma_dung_don_vi_thieu_va_cat_som(monkeypatch):
    gz, _ = _global_gz()
    resp = FakeResp(gz)
    monkeypatch.setattr(pc, "_session", lambda: FakeSession(lambda u, k: resp))
    g, n = pc.fetch_hour_files(datetime(2020, 10, 1), ROWS, COLS)
    assert g.shape == (25, 25) and g.dtype == np.float32
    assert g[0, 0] == pytest.approx(12.34)
    assert g[12, 12] == pytest.approx(0.05)
    assert np.isnan(g[-1, -1])
    assert np.nanmax(g) == pytest.approx(12.34)            # ô 999 ngoài khung không lọt vào
    assert np.isnan(g).sum() == 1
    assert n == resp.sent < len(gz) / 2                     # chỉ tải phần đầu luồng


def test_404_la_gio_thieu_khong_phai_loi(monkeypatch):
    monkeypatch.setattr(pc, "_session", lambda: FakeSession(lambda u, k: FakeResp(status=404)))
    assert pc.fetch_hour_files(datetime(2020, 10, 1), ROWS, COLS) == (None, 0)


def test_luong_cut_thi_thu_lai(monkeypatch, no_sleep):
    gz, _ = _global_gz()
    sess = FakeSession(lambda u, k: FakeResp(gz[:5000] if k == 1 else gz))
    monkeypatch.setattr(pc, "_session", lambda: sess)
    g, _ = pc.fetch_hour_files(datetime(2020, 10, 1), ROWS, COLS)
    assert len(sess.calls) == 2 and g[0, 0] == pytest.approx(12.34)


def test_loi_server_het_luot_thi_nem(monkeypatch, no_sleep):
    sess = FakeSession(lambda u, k: FakeResp(status=503))
    monkeypatch.setattr(pc, "_session", lambda: sess)
    with pytest.raises(requests.HTTPError):
        pc.fetch_hour_files(datetime(2020, 10, 1), ROWS, COLS)
    assert len(sess.calls) == cfg.MAX_RETRIES


# ---------------------------------------------------------------- GDEX (OPeNDAP ascii)

def _dap_ascii(label_day: date, hours: list[int], grids: list[np.ndarray],
               lats=LATS, lons=LONS) -> str:
    """Phản hồi .ascii đúng khuôn GDEX: lat tăng dần (nam → bắc), time = nhãn KẾT THÚC."""
    nt = len(hours)
    out = [f"Dataset {{ ... }} x.nc;\n{'-' * 45}\nprecip.precip[{nt}][25][25]"]
    for k, g in enumerate(grids):
        for i, row in enumerate(g[::-1]):
            out.append(f"[{k}][{i}], " + ", ".join("NaN" if np.isnan(v) else str(v) for v in row))
    epoch = datetime(1970, 1, 1)
    ts = [int((datetime(label_day.year, label_day.month, label_day.day, h) - epoch)
              .total_seconds()) for h in hours]
    out += ["", f"precip.time[{nt}]", ", ".join(map(str, ts)), "",
            "precip.lat[25]", ", ".join(str(x + 1e-12) for x in lats[::-1]), "",
            "precip.lon[25]", ", ".join(str(x) for x in lons), ""]
    return "\n".join(out)


def test_gdex_lat_lon_va_nhan_gio(monkeypatch):
    g0 = np.zeros((25, 25), dtype=np.float32)
    g0[0, 0] = 3.5                     # tây bắc
    g1 = np.full((25, 25), 0.25, dtype=np.float32)
    g1[-1, -1] = np.nan
    txt = _dap_ascii(date(2020, 10, 1), [0, 1], [g0, g1])
    sess = FakeSession(lambda u, k: FakeResp(txt.encode()))
    monkeypatch.setattr(pc, "_session", lambda: sess)
    out, n = pc.fetch_day_gdex(date(2020, 10, 1), 0, 1, LATS, LONS)
    # nhãn 00:00 = kết thúc giờ 23Z hôm trước
    assert sorted(out) == [datetime(2020, 9, 30, 23), datetime(2020, 10, 1, 0)]
    assert out[datetime(2020, 9, 30, 23)][0, 0] == pytest.approx(3.5)
    assert np.isnan(out[datetime(2020, 10, 1, 0)][-1, -1])
    q = sess.calls[0].split("?", 1)[1]
    assert q == "precip%5B0:1:1%5D%5B1895:1:1919%5D%5B7175:1:7199%5D"
    assert n == len(txt.encode())


def test_gdex_toa_do_lech_thi_bao_loi(monkeypatch):
    txt = _dap_ascii(date(2020, 10, 1), [0], [np.zeros((25, 25))], lons=LONS + 0.04)
    monkeypatch.setattr(pc, "_session", lambda: FakeSession(lambda u, k: FakeResp(txt.encode())))
    with pytest.raises(pc.FormatError):
        pc.fetch_day_gdex(date(2020, 10, 1), 0, 0, LATS, LONS)


# ---------------------------------------------------------------- bảng + resume

def test_bang_dai_nhan_ket_thuc_gio_va_gio_vn():
    g = np.zeros((25, 25), dtype=np.float32)
    g[0, 0] = np.nan
    df = pc.to_frame({datetime(2020, 10, 1, 0): g, datetime(2020, 10, 1, 1): g + 1}, LATS, LONS)
    assert df.columns == pc.COLS and df.height == 2 * 625
    assert df.schema["time_utc"] == pl.Datetime("us", "UTC")
    assert df.schema["precip_mm"] == pl.Float32
    first = df.row(0, named=True)
    assert first["time_utc"].replace(tzinfo=None) == datetime(2020, 10, 1, 1)   # giờ 00Z kết thúc 01Z
    assert first["time"] == datetime(2020, 10, 1, 8)                             # UTC+7
    assert (first["lat"], first["lon"]) == (16.78, 107.02)
    assert first["precip_mm"] is None
    assert df["precip_mm"].null_count() == 2


def test_gio_yeu_cau_theo_thang_bat_dau_va_loc_thang():
    h = pc.hours_requested(date(2020, 9, 30), date(2020, 10, 31), months={10})
    assert list(h) == ["202010"] and len(h["202010"]) == 744
    assert h["202010"][-1] == datetime(2020, 10, 31, 23)
    assert len(pc.hours_requested(date(2020, 2, 1), date(2020, 2, 29))["202002"]) == 29 * 24


def test_resume_chi_tai_gio_con_thieu(tmp_path, monkeypatch):
    calls = []
    lost = datetime(2020, 10, 1, 3)

    def fake(t, rows, cols, base):
        calls.append(t)
        if t == lost:
            return None, 0
        return np.full((25, 25), t.hour, dtype=np.float32), 100

    monkeypatch.setattr(pc, "fetch_hour_files", fake)
    hours = [datetime(2020, 10, 1, h) for h in range(6)]
    s = pc.process_month("202010", hours, "files", 2, out_dir=tmp_path)
    assert s["hours"] == 5 and s["missing"] == 1 and s["bytes"] == 500
    df = pl.read_parquet(tmp_path / "pccs_202010.parquet")
    assert df.height == 5 * 625 and df["time_utc"].n_unique() == 5
    man = json.loads((tmp_path / "_manifest.json").read_text(encoding="utf-8"))
    assert man["202010"]["missing_files"] == [lost.isoformat()]

    calls.clear()
    assert pc.process_month("202010", hours, "files", 2, out_dir=tmp_path) is None
    assert calls == []                                   # đủ rồi: không gọi mạng

    more = hours + [datetime(2020, 10, 1, 6), datetime(2020, 10, 1, 7)]
    s = pc.process_month("202010", more, "files", 2, out_dir=tmp_path)
    assert sorted(calls) == more[-2:] and s["rows"] == 7 * 625
    assert not list(tmp_path.glob("*.tmp"))              # không để lại file tạm


def test_so_sanh_era5_tren_du_lieu_gia(tmp_path):
    rng = np.random.default_rng(1)
    starts = [datetime(2020, 10, 1) + timedelta(hours=k) for k in range(72)]
    vals = rng.gamma(0.5, 2.0, size=len(starts)).astype(np.float32)
    grids = {t: np.full((25, 25), v, dtype=np.float32) for t, v in zip(starts, vals)}
    pc.to_frame(grids, LATS, LONS).write_parquet(tmp_path / "pccs_202010.parquet")
    era_dir = tmp_path / "era5"
    era_dir.mkdir()
    vn = [t + timedelta(hours=8) for t in starts]           # cùng nhãn kết thúc giờ, giờ VN
    for la, lo in [(16.1, 107.1), (16.8, 107.8)]:
        pl.DataFrame({"time": vn, "precipitation": (vals / 2).astype(np.float64),
                      "lat": la, "lon": lo}).write_parquet(era_dir / f"rh_{la}_{lo}_2020.parquet")
    r = pc.compare_era5(["202010"], out_dir=tmp_path, era5_dir=era_dir)
    assert r["n_cells_box"] == 625 and r["n_cells_footprint"] == 19 * 20
    assert r["ratio_fp_over_era5"] == pytest.approx(2.0, abs=1e-3)
    assert r["corr_hourly_fp"] == pytest.approx(1.0, abs=1e-3)
    assert r["corr_hourly_by_lag"][0] == max(r["corr_hourly_by_lag"].values())
    assert r["n_days"] >= 2
