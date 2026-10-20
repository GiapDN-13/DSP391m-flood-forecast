"""Đặc trưng mưa theo giờ → ngày: dữ liệu giả lập, không cần mạng/file thật."""

import json
import math
from datetime import date, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from src.features import hourly_features as hf


def _hours(days: int, start: datetime = datetime(2020, 10, 1)) -> pl.Series:
    return pl.datetime_range(start, start + timedelta(days=days) - timedelta(hours=1),
                             "1h", eager=True)


def _one(vals: dict[int, float], days: int = 3) -> pl.DataFrame:
    """Chuỗi giờ một đơn vị 'u': {chỉ số giờ kể từ 00h ngày đầu: mm}."""
    t = _hours(days)
    x = [0.0] * len(t)
    for k, v in vals.items():
        x[k] = v
    return pl.DataFrame({"time": t, "u": x})


def _day(f: pl.DataFrame, d: date) -> dict:
    return f.filter(pl.col("date") == d).row(0, named=True)


# ------------------------------------------------------------ cường độ, tổng

def test_tong_max1h_max3h_max6h_va_so_gio_mua():
    # ngày 2 (giờ 24…47): 10h=2, 11h=5, 12h=1 ; 20h=4, 21h=4
    f = hf.daily_features(_one({34: 2, 35: 5, 36: 1, 44: 4, 45: 4}), ["u"])
    r = _day(f, date(2020, 10, 2))
    assert r["hr_sum_u"] == pytest.approx(16)
    assert r["hr_max1h_u"] == pytest.approx(5)
    assert r["hr_max3h_u"] == pytest.approx(8)       # 2+5+1 (và 4+4+0)
    assert r["hr_max6h_u"] == pytest.approx(8)       # hai cụm cách nhau > 6 giờ
    assert r["hr_nh1mm_u"] == 5                       # 1 mm cũng tính là giờ mưa


def test_max3h_lay_cua_so_lien_tuc_khong_lay_tong_3_gio_lon_nhat():
    # 3 giờ lớn nhất (6, 6, 6) rải rác → max3h là cụm liền nhau 3+4+5 = 12
    f = hf.daily_features(_one({26: 6, 32: 6, 40: 6, 43: 3, 44: 4, 45: 5}), ["u"])
    r = _day(f, date(2020, 10, 2))
    assert r["hr_max3h_u"] == pytest.approx(12)
    assert r["hr_max1h_u"] == pytest.approx(6)


def test_cua_so_3h_bat_qua_nua_dem_tinh_cho_ngay_ket_thuc():
    # 23h ngày 1 = 4, 00h ngày 2 = 4 → cửa sổ kết thúc lúc 00h ngày 2 = 8
    f = hf.daily_features(_one({23: 4, 24: 4}), ["u"])
    assert _day(f, date(2020, 10, 2))["hr_max3h_u"] == pytest.approx(8)
    assert _day(f, date(2020, 10, 1))["hr_max3h_u"] is None    # ngày đầu thiếu giờ trước đó


# ------------------------------------------------------------ giờ đỉnh

def test_gio_dinh_sin_cos():
    f = hf.daily_features(_one({24 + 18: 9.0, 24 + 3: 2.0}), ["u"])
    r = _day(f, date(2020, 10, 2))
    a = 2 * math.pi * 18 / 24
    assert r["hr_peak_sin_u"] == pytest.approx(math.sin(a))
    assert r["hr_peak_cos_u"] == pytest.approx(math.cos(a))


def test_gio_dinh_trung_thi_lay_gio_som_nhat_va_khong_mua_thi_bang_0():
    f = hf.daily_features(_one({24 + 6: 3.0, 24 + 15: 3.0, 48 + 9: 0.05}), ["u"])
    r = _day(f, date(2020, 10, 2))
    assert r["hr_peak_sin_u"] == pytest.approx(math.sin(2 * math.pi * 6 / 24))
    for d in (date(2020, 10, 1), date(2020, 10, 3)):          # khô / chỉ mưa vết
        r = _day(f, d)
        assert (r["hr_peak_sin_u"], r["hr_peak_cos_u"]) == (0.0, 0.0)


# ------------------------------------------------------------ 07h, 72h

def test_r24_7h_ranh_gioi_07h():
    # 07h ngày 2 thuộc ngày quan trắc 2; 08h ngày 2 thuộc ngày 3; 08h ngày 1 thuộc ngày 2
    f = hf.daily_features(_one({8: 1.0, 24 + 7: 10.0, 24 + 8: 100.0}), ["u"])
    assert _day(f, date(2020, 10, 2))["hr_r24_7h_u"] == pytest.approx(11.0)
    assert _day(f, date(2020, 10, 3))["hr_r24_7h_u"] == pytest.approx(100.0)
    assert _day(f, date(2020, 10, 1))["hr_r24_7h_u"] is None   # thiếu 08h…23h hôm trước


def test_r72h_bang_tong_3_ngay():
    f = hf.daily_features(_one({5: 1.0, 30: 2.0, 60: 4.0, 80: 8.0}, days=4), ["u"])
    assert f["hr_r72h_u"].to_list()[:2] == [None, None]
    assert _day(f, date(2020, 10, 3))["hr_r72h_u"] == pytest.approx(7.0)
    assert _day(f, date(2020, 10, 4))["hr_r72h_u"] == pytest.approx(14.0)


# ------------------------------------------------------------ rò rỉ, thiếu giờ

def test_khong_ro_ri_tuong_lai():
    rng = np.random.default_rng(0)
    t = _hours(6)
    x = rng.gamma(0.4, 3.0, len(t)) * (rng.random(len(t)) < 0.5)
    h = pl.DataFrame({"time": t, "u": x, "v": x[::-1].copy()})
    base = hf.daily_features(h)
    for cut_day in range(1, 5):                   # đổi mọi giờ từ 00h ngày cut_day+1 trở đi
        k = 24 * (cut_day + 1)
        y = x.copy()
        y[k:] = rng.gamma(2.0, 10.0, len(t) - k)
        alt = hf.daily_features(h.with_columns(pl.Series("u", y), pl.Series("v", y[::-1].copy())))
        d_cut = date(2020, 10, 1) + timedelta(days=cut_day)
        a = base.filter(pl.col("date") <= d_cut)
        b = alt.filter(pl.col("date") <= d_cut)
        assert a.select("date", *[c for c in a.columns if c.endswith("_u")]).equals(
            b.select("date", *[c for c in b.columns if c.endswith("_u")]))
        # đối chứng: ngày ngay sau thì PHẢI đổi
        nxt = d_cut + timedelta(days=1)
        assert _day(base, nxt)["hr_sum_u"] != pytest.approx(_day(alt, nxt)["hr_sum_u"])


def test_thieu_mot_gio_thi_ngay_do_null_ngay_khac_giu_nguyen():
    h = _one({30: 3.0, 60: 2.0})
    full = hf.daily_features(h, ["u"])
    miss = hf.daily_features(h.filter(pl.col("time") != datetime(2020, 10, 2, 5)), ["u"])
    r = _day(miss, date(2020, 10, 2))
    assert r["hr_sum_u"] is None and r["hr_max1h_u"] is None
    assert _day(miss, date(2020, 10, 3))["hr_sum_u"] == _day(full, date(2020, 10, 3))["hr_sum_u"]
    assert _day(miss, date(2020, 10, 3))["hr_r72h_u"] is None   # cửa sổ 72h chứa ngày thiếu


# ------------------------------------------------------------ lưới → lưu vực

def _grid_long() -> pl.DataFrame:
    t = _hours(2)
    n = len(t)
    return pl.DataFrame({
        "time": pl.concat([t, t, t]),
        "lat": [16.1] * n + [16.2] * n + [16.3] * n,
        "lon": [107.1] * (3 * n),
        "precip": [1.0] * n + [3.0] * n + [10.0] * n,
    })


def test_basin_hourly_trong_so_va_toan_luu_vuc_theo_dien_tich():
    w = pl.DataFrame({"subbasin": ["a", "a", "b"], "lat": [16.1, 16.2, 16.3],
                      "lon": [107.1, 107.1, 107.1], "weight": [0.75, 0.25, 1.0]})
    hb = hf.basin_hourly(_grid_long(), w, {"a": 300.0, "b": 100.0})
    assert hb.columns == ["time", "a", "b", "basin"]
    assert hb.height == 48
    assert hb["a"].to_list() == pytest.approx([1.5] * 48)           # 0,75·1 + 0,25·3
    assert hb["basin"].to_list() == pytest.approx([(300 * 1.5 + 100 * 10) / 400] * 48)


def test_basin_hourly_o_thieu_thi_chia_lai_trong_so():
    g = _grid_long().with_columns(
        pl.when((pl.col("lat") == 16.1) & (pl.col("time") == datetime(2020, 10, 1, 5)))
        .then(None).otherwise(pl.col("precip")).alias("precip"))
    w = pl.DataFrame({"subbasin": ["a", "a", "b"], "lat": [16.1, 16.2, 16.3],
                      "lon": [107.1, 107.1, 107.1], "weight": [0.75, 0.25, 1.0]})
    hb = hf.basin_hourly(g, w, {"a": 1.0, "b": 1.0})
    assert hb.filter(pl.col("time") == datetime(2020, 10, 1, 5))["a"].item() == pytest.approx(3.0)


def test_hourly_features_ten_cot_va_so_cot():
    w = pl.DataFrame({"subbasin": ["a", "b"], "lat": [16.1, 16.3], "lon": [107.1, 107.1],
                      "weight": [1.0, 1.0]})
    f = hf.hourly_features(_grid_long(), w, {"a": 1.0, "b": 1.0})
    assert f.columns == ["date", *hf.feature_names(["a", "b", "basin"])]
    assert f.height == 2 and len(hf.FEATS) == 9


def test_trong_so_du_phong_3_dai_vi_do(monkeypatch, tmp_path):
    monkeypatch.setitem(hf.WEIGHTS, "era5", tmp_path / "khong_co.csv")
    lats = [16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.8]
    cells = pl.DataFrame({"lat": lats, "lon": [107.2] * len(lats)})
    w, areas, how = hf.load_weights("era5", cells)
    assert "dải vĩ độ" in how and list(areas) == ["thuong", "trung", "ha"]
    s = w.group_by("subbasin").agg(pl.col("weight").sum(), pl.len()).sort("subbasin")
    assert s["weight"].to_list() == pytest.approx([1.0, 1.0, 1.0])
    assert dict(zip(s["subbasin"], s["len"])) == {"ha": 2, "thuong": 3, "trung": 2}


# ------------------------------------------------------------ ghép panel

def test_join_panel_giu_so_dong_va_kieu_ngay():
    panel = pl.DataFrame({"date": pl.datetime_range(datetime(2020, 9, 29), datetime(2020, 10, 3),
                                                     "1d", eager=True),
                          "discharge": [1.0, 2, 3, 4, 5]})
    f = hf.daily_features(_one({30: 3.0}), ["u"])
    out = hf.join_panel(panel, f)
    assert out.height == panel.height
    assert out.schema["date"] == panel.schema["date"]
    assert out["hr_sum_u"].to_list()[:2] == [None, None]          # trước khi có mưa giờ
    assert out.filter(pl.col("date") == datetime(2020, 10, 2))["hr_sum_u"].item() == 3.0


# ------------------------------------------------------------ ablation

def test_ablation_cau_hinh_va_mat_na_chung():
    ab = pytest.importorskip("src.models.ablation_hourly")
    n = 10
    d = pl.datetime_range(datetime(2020, 12, 27), datetime(2021, 1, 5), "1d", eager=True)
    panel = pl.DataFrame({"date": d, "discharge": np.arange(n, dtype=float),
                          "rain_basin": np.ones(n), "alert_level": [None] * n,
                          "target_h1": [*np.arange(1.0, n), None],
                          **{c: [None, *np.ones(n - 1)] for c in hf.feature_names(["basin", "s1"])}})
    c = ab.configs(panel)
    assert c["A panel goc"] == ["discharge", "rain_basin"]
    assert all(not x.startswith("hr_") for x in c["A panel goc"])
    assert set(c["B +gio toan luu vuc"]) - set(c["A panel goc"]) == set(hf.feature_names(["basin"]))
    assert set(c["C +gio luu vuc con"]) - set(c["A panel goc"]) == set(hf.feature_names(["s1"]))
    union = sorted({x for f in c.values() for x in f})
    m = ab.masks(panel, union, 1)
    # ngày 1 thiếu cột giờ, ngày cuối thiếu target → loại ở MỌI cấu hình
    assert m["train"].sum() == 4 and m["valid"].sum() == 4 and m["test"].sum() == 0


def test_bootstrap_dnse_bang_0_khi_hai_du_bao_trung_nhau():
    ab = pytest.importorskip("src.models.ablation_hourly")
    rng = np.random.default_rng(1)
    y = rng.gamma(2, 50, 200)
    p = y + rng.normal(0, 10, 200)
    ci, p_pos = ab.block_boot_dnse(y, p, p, n=50, block=10)
    assert ci == pytest.approx([0, 0, 0]) and p_pos == 0.0


# ------------------------------------------------------------ vệ tinh (IMERG / GSMaP)

def _half(start: datetime, n: int, cells=((16.25, 107.55),), seed: int = 0,
          step: int = 30) -> pl.DataFrame:
    """IMERG giả: n bước ``step`` phút (nhãn CUỐI) từ ``start``, cường độ mm/giờ, mỗi ô một chuỗi."""
    rng = np.random.default_rng(seed)
    t = pl.datetime_range(start, start + timedelta(minutes=step * (n - 1)), f"{step}m", eager=True)
    return pl.concat([pl.DataFrame({"time": t, "lat": [la] * n, "lon": [lo] * n,
                                    "precip": rng.gamma(0.5, 4.0, n) * (rng.random(n) < 0.6)})
                      for la, lo in cells])


def test_imerg_gop_nua_gio_ve_gio_nhan_cuoi_gio():
    t = [datetime(2020, 10, 1, 22, 30), datetime(2020, 10, 1, 23), datetime(2020, 10, 1, 23, 30),
         datetime(2020, 10, 2, 0), datetime(2020, 10, 2, 0, 30), datetime(2020, 10, 2, 1)]
    df = pl.DataFrame({"time": t, "lat": [16.25] * 6, "lon": [107.55] * 6,
                       "precip": [2.0, 4.0, 5.0, 3.0, 2.0, 6.0]})       # mm/giờ
    h = hf.to_hourly(df, 30)
    # giờ kết thúc HH:00 = nửa giờ kết thúc HH−1:30 + HH:00, mỗi nửa × 0,5
    assert h["time"].to_list() == [datetime(2020, 10, 1, 23), datetime(2020, 10, 2, 0),
                                   datetime(2020, 10, 2, 1)]
    assert h["precip"].to_list() == pytest.approx([3.0, 4.0, 4.0])
    # nửa giờ kết thúc 23:30 ngày 1 rơi vào giờ 00:00 ngày 2 ⇒ thuộc NGÀY 2
    full = (pl.DataFrame({"time": _hours(2)}).join(h, on="time", how="left")
              .select("time", pl.col("precip").fill_null(0.0).alias("u")))
    f = hf.daily_features(full, ["u"])
    assert _day(f, date(2020, 10, 1))["hr_sum_u"] == pytest.approx(3.0)
    assert _day(f, date(2020, 10, 2))["hr_sum_u"] == pytest.approx(8.0)


def test_imerg_thieu_nua_gio_thi_gio_trong_va_gsmap_giu_nguyen():
    df = _half(datetime(2020, 10, 1, 0, 30), 48 * 2)
    miss = df.filter(pl.col("time") != datetime(2020, 10, 1, 9, 30))      # thuộc giờ 10:00
    h = hf.to_hourly(miss, 30)
    assert h.filter(pl.col("time") == datetime(2020, 10, 1, 10))["precip"].item() is None
    f = hf.daily_features(h.select("time", pl.col("precip").alias("u")), ["u"])
    assert _day(f, date(2020, 10, 1))["hr_sum_u"] is None
    assert _day(f, date(2020, 10, 2))["hr_sum_u"] is not None
    # GSMaP: bước 60 phút, giá trị mm/giờ = mm của giờ đó, nhãn giữ nguyên
    g = df.filter(pl.col("time").dt.minute() == 0)
    assert hf.to_hourly(g, 60).equals(g.with_columns(pl.col("precip").cast(pl.Float64)))
    with pytest.raises(ValueError):
        hf.to_hourly(df, 60)                                              # có nhãn :30


def test_imerg_khong_ro_ri_tuong_lai_qua_ca_pipeline():
    cells = ((16.25, 107.55), (16.35, 107.55))
    w = pl.DataFrame({"subbasin": ["a", "b"], "lat": [16.25, 16.35], "lon": [107.55, 107.55],
                      "weight": [1.0, 1.0]})
    areas = {"a": 2.0, "b": 1.0}
    raw = _half(datetime(2020, 9, 30, 23, 30), 48 * 6, cells)       # đủ 6 ngày 1…6/10
    base = hf.hourly_features(hf.to_hourly(raw, 30), w, areas)
    rng = np.random.default_rng(5)
    for cut in range(1, 5):
        d_cut = date(2020, 10, cut)
        late = pl.col("time") > datetime(d_cut.year, d_cut.month, d_cut.day, 23)
        alt_raw = raw.with_columns(pl.when(late).then(pl.lit(rng.gamma(2.0, 10.0)))
                                   .otherwise(pl.col("precip")).alias("precip"))
        alt = hf.hourly_features(hf.to_hourly(alt_raw, 30), w, areas)
        assert base.filter(pl.col("date") <= d_cut).equals(alt.filter(pl.col("date") <= d_cut))
        nxt = d_cut + timedelta(days=1)                               # đối chứng: phải đổi
        assert _day(base, nxt)["hr_sum_basin"] != pytest.approx(_day(alt, nxt)["hr_sum_basin"])
    # nửa giờ kết thúc ĐÚNG 23:00 thuộc ngày đó
    alt_raw = raw.with_columns(pl.when(pl.col("time") == datetime(2020, 10, 2, 23))
                               .then(pl.col("precip") + 10).otherwise(pl.col("precip")).alias("precip"))
    alt = hf.hourly_features(hf.to_hourly(alt_raw, 30), w, areas)
    assert _day(alt, date(2020, 10, 2))["hr_sum_a"] == pytest.approx(
        _day(base, date(2020, 10, 2))["hr_sum_a"] + 5.0)


def _fake_gee(tmp_path, monkeypatch, source: str) -> None:
    """File tháng giả đúng định dạng gee_precip + bảng trọng số/geojson giả."""
    folder, col, step = hf.GEE[source]
    n = 31 * 24 * 60 // step
    start = datetime(2020, 10, 1, 0, 30) if step == 30 else datetime(2020, 10, 1, 1)
    d = (pl.concat([_half(start, n, (c,), seed=k, step=step)
                    for k, c in enumerate(((16.25, 107.55), (16.35, 107.65)))])
           .with_columns((pl.col("time") - pl.duration(hours=7)).alias("time_utc"),
                         pl.col("precip").cast(pl.Float32).alias(col))
           .select("time_utc", "time", "lat", "lon", col))
    (tmp_path / folder).mkdir()
    d.write_parquet(tmp_path / folder / f"{folder}_202010.parquet")
    w = pl.DataFrame({"subbasin": ["a", "b"], "lat": [16.25, 16.35], "lon": [107.55, 107.65],
                      "weight": [1.0, 1.0]})
    w.write_csv(tmp_path / "w.csv")
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "a", "area_km2": 3.0}, "geometry": None},
        {"type": "Feature", "properties": {"name": "b", "area_km2": 1.0}, "geometry": None}]}
    (tmp_path / "sub.geojson").write_text(json.dumps(gj), encoding="utf-8")
    monkeypatch.setattr(hf, "GEE_DIR", tmp_path)
    monkeypatch.setitem(hf.WEIGHTS, source, tmp_path / "w.csv")
    monkeypatch.setattr(hf, "SUBBASIN_GEOJSON", tmp_path / "sub.geojson")


@pytest.mark.parametrize("source", ["imerg", "gsmap_gc"])
def test_tong_ngay_qua_bang_gio_bang_tong_tinh_thang(tmp_path, monkeypatch, source):
    _fake_gee(tmp_path, monkeypatch, source)
    hb, feats, how = hf.build_source(source)
    assert "w.csv" in how and hb.columns == ["time", "a", "b", "basin"]
    chk = hf.check_daily_sum(source, feats)
    assert chk["n_days"].min() >= 30
    assert chk["max_abs_diff_mm"].max() < 1e-9


def test_imerg_that_khong_ro_ri_neu_co_du_lieu():
    """Chạy lại kiểm rò rỉ trên IMERG THẬT (10/2020, có lũ lớn) nếu đã tải."""
    if not (hf.GEE_DIR / "imerg" / "imerg_202010.parquet").exists() or not hf.WEIGHTS["imerg"].exists():
        pytest.skip("chưa tải IMERG qua src.ingest.gee_precip")
    w, areas, _ = hf.load_weights("imerg")
    raw = hf.load_gee("imerg", months=["202010"], cells=w, hourly=False)
    base = hf.hourly_features(hf.to_hourly(raw, 30), w, areas)
    for cut in (date(2020, 10, 9), date(2020, 10, 17), date(2020, 10, 27)):
        late = pl.col("time") > datetime(cut.year, cut.month, cut.day, 23)
        alt = hf.hourly_features(hf.to_hourly(raw.with_columns(
            pl.when(late).then(pl.col("precip") * 3 + 7).otherwise(pl.col("precip"))
            .alias("precip")), 30), w, areas)
        assert base.filter(pl.col("date") <= cut).equals(alt.filter(pl.col("date") <= cut))
        assert not base.filter(pl.col("date") == cut + timedelta(days=1)).equals(
            alt.filter(pl.col("date") == cut + timedelta(days=1)))


def test_ablation_sat_cau_hinh_va_split_chinh():
    sa = pytest.importorskip("src.models.ablation_sat")
    base = ["discharge", "rain_basin"]
    c = sa.configs("r2", base)
    assert list(c)[0] == "A0 panel goc" and c["A0 panel goc"] == base
    assert c["A0+imerg"][2:] == [f"imerg_{x}" for x in hf.feature_names(["basin"])]
    assert len(c["A0+gsmap_gc luu vuc con"]) == 2 + 45
    assert not set(c["A0+gsmap_gc luu vuc con"]) & set(sa.sat_cols("gsmap_gc", ["basin"]))
    e = sa.configs("ext", base)
    assert list(e) == ["E0 (=E ablation_ext)", "E0+gsmap_gc", "E0+imerg"]
    sp = sa.main_split(sa.EXT_START)
    assert sp["train"] == (date(1998, 1, 4), date(2015, 12, 31))
    assert sp["valid"] == (date(2016, 1, 1), date(2022, 6, 30))
    assert sp["test"][0] == date(2022, 7, 1)
    ab = pytest.importorskip("src.models.ablation_hourly")
    d = pl.datetime_range(datetime(1998, 1, 1), datetime(1998, 1, 6), "1d", eager=True)
    panel = pl.DataFrame({"date": d, "x": np.ones(6), "target_h1": np.ones(6)})
    assert ab.masks(panel, ["x"], 1, sp)["train"].tolist() == [False] * 3 + [True] * 3
