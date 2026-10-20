"""Lưu vực con: trọng số ô lưới, gộp chuỗi, D8 trên lưới giả lập — không cần mạng/DEM."""

import json
import math

import numpy as np
import polars as pl
import pytest

from src.features import basins as b

pytest.importorskip("pyproj")
box = pytest.importorskip("shapely.geometry").box     # shapely/pyproj chưa cài → bỏ qua cả file


# ------------------------------------------------------------ trọng số ô lưới

def test_trong_so_tong_bang_1_va_bo_o_ngoai():
    # Lưu vực = đúng 2×2 ô 0,1° (tâm 16.1/16.2 × 107.1/107.2) → 4 ô, mỗi ô ~0,25
    basins = {"a": box(107.05, 16.05, 107.25, 16.25)}
    lats, lons = b.mesh([16.1, 16.2, 16.3], [107.1, 107.2, 107.3])
    w = b.cell_weights(lats, lons, 0.1, basins)
    assert w.height == 4                                  # 5 ô không chạm bị bỏ
    assert w["weight"].sum() == pytest.approx(1.0)
    # ô phía nam rộng hơn ô phía bắc một chút (cos vĩ độ) nhưng gần 0,25
    assert w["weight"].to_list() == pytest.approx([0.25] * 4, abs=1e-3)
    s = w.filter(pl.col("lat") == 16.1)["weight"].sum()
    n = w.filter(pl.col("lat") == 16.2)["weight"].sum()
    assert s > n


def test_trong_so_ti_le_dien_tich_giao():
    # Lưu vực phủ trọn ô A (107.1) và nửa ô B (107.2) → B nặng bằng nửa A
    basins = {"a": box(107.05, 16.05, 107.20, 16.15)}
    w = b.cell_weights([16.1, 16.1], [107.1, 107.2], 0.1, basins)
    wa = w.filter(pl.col("lon") == 107.1)["weight"].item()
    wb = w.filter(pl.col("lon") == 107.2)["weight"].item()
    assert wa / wb == pytest.approx(2.0, rel=1e-3)
    assert wa + wb == pytest.approx(1.0)


def test_trong_so_nhieu_luu_vuc_va_sai_do_dai():
    basins = {"x": box(107.05, 16.05, 107.15, 16.15), "y": box(107.15, 16.05, 107.25, 16.15)}
    w = b.cell_weights([16.1, 16.1], [107.1, 107.2], 0.1, basins)
    assert sorted(w["subbasin"].unique().to_list()) == ["x", "y"]
    assert w.group_by("subbasin").agg(pl.col("weight").sum())["weight"].to_list() == \
        pytest.approx([1.0, 1.0])
    with pytest.raises(ValueError):
        b.cell_weights([16.1, 16.2], [107.1], 0.1, basins)


def test_do_phu_luoi():
    # Một nửa lưu vực nằm ngoài lưới (phía nam) → phủ ~50 %
    basins = {"a": box(107.05, 15.95, 107.15, 16.15)}
    cov = b.grid_coverage([16.1], [107.1], 0.1, basins)
    row = cov.filter(pl.col("subbasin") == "a").row(0, named=True)
    assert row["covered_pct"] == pytest.approx(50.0, abs=0.3)


# ------------------------------------------------------------ gộp chuỗi

def _weights():
    return pl.DataFrame({"subbasin": ["s", "s"], "lat": [16.1, 16.2], "lon": [107.1, 107.1],
                         "weight": [0.25, 0.75]})


def test_trung_binh_co_trong_so_va_lam_tron_toa_do():
    df = pl.DataFrame({"time": [1, 1, 2, 2],
                       "lat": [16.100000001, 16.2, 16.1, 16.199999999],   # lệch số thực
                       "lon": [107.1, 107.1, 107.1, 107.1],
                       "rain": [4.0, 8.0, 0.0, 2.0]})
    out = b.basin_mean(df, _weights(), "rain")
    assert out["rain"].to_list() == pytest.approx([0.25 * 4 + 0.75 * 8, 0.75 * 2])


def test_o_thieu_so_lieu_chia_lai_trong_so():
    df = pl.DataFrame({"time": [1, 1], "lat": [16.1, 16.2], "lon": [107.1, 107.1],
                       "rain": [4.0, None]})
    out = b.basin_mean(df, _weights(), "rain")
    assert out["rain"].item() == pytest.approx(4.0)       # chỉ còn ô 16.1 → trọng số 1


def test_dang_rong():
    w = pl.concat([_weights(), _weights().with_columns(pl.lit("t").alias("subbasin"))])
    df = pl.DataFrame({"time": [1, 1], "lat": [16.1, 16.2], "lon": [107.1, 107.1],
                       "rain": [4.0, 8.0]})
    out = b.basin_mean(df, w, "rain", wide=True)
    assert set(out.columns) == {"time", "rain_s", "rain_t"}


# ------------------------------------------------------------ lưới & diện tích

def test_tam_o_persiann_ccs():
    lats, lons = b.pccs_centers({"lat_min": 15.8, "lat_max": 16.8, "lon_min": 107.0, "lon_max": 108.0})
    assert lats[0] == pytest.approx(16.78) and lats[-1] == pytest.approx(15.82)
    assert lons[0] == pytest.approx(107.02) and lons[-1] == pytest.approx(107.98)
    assert len(lats) == 25 and len(lons) == 25
    # đúng quy ước readme CHRS: tâm = 59.98 - 0.04 i, 0.02 + 0.04 j
    for la in lats:
        assert (59.98 - la) / 0.04 == pytest.approx(round((59.98 - la) / 0.04), abs=1e-6)


def test_tam_o_imerg_gsmap():
    lats, lons = b.gee_centers({"lat_min": 15.8, "lat_max": 16.8, "lon_min": 107.0, "lon_max": 108.0})
    assert lats.tolist() == pytest.approx([15.85 + 0.1 * i for i in range(10)])
    assert lons.tolist() == pytest.approx([107.05 + 0.1 * i for i in range(10)])


def test_dien_tich_o_xich_dao():
    # Ô 1°×1° ở xích đạo ≈ 12 364 km²
    assert b.pixel_area_km2(np.array([0.0]), 1.0, 1.0)[0] == pytest.approx(12364, rel=2e-3)


# ------------------------------------------------------------ D8 giả lập

def _fdir_funnel():
    """Lưới 5×5: mọi ô chảy về cột giữa, cột giữa chảy xuống hàng cuối (cửa ra (4, 2))."""
    E, W, S, SE, SW = 1, 16, 4, 2, 8
    return np.array([
        [SE, SE, S, SW, SW],
        [E, SE, S, SW, W],
        [E, E, S, W, W],
        [E, E, S, W, W],
        [0, E, S, W, 0],
    ], dtype=np.uint8)


def test_catchment_va_duong_xuoi_dong():
    fd = _fdir_funnel()
    m = b.catchment_mask(fd, 4, 2)
    assert m.sum() == 23                                  # trừ hai ô góc dưới (fdir 0)
    assert not m[4, 0] and not m[4, 4]
    path = b.downstream_path(fd, 0, 0)
    assert path[0] == (0, 0) and path[-1] == (4, 2)       # (4,2) chảy ra ngoài lưới


def test_snap_chon_o_gan_nhat_dat_nguong_khong_truot_xuoi_dong():
    from affine import Affine

    acc = np.zeros((7, 7), dtype="float32")
    acc[:, 3] = np.arange(1, 8) * 100.0                   # dòng chính, tăng dần xuôi dòng
    tr = Affine(0.001, 0, 107.0, 0, -0.001, 16.0)          # ô ~110 m
    lat, lon = b._xy(tr, 2, 1)                            # điểm gốc lệch 2 ô khỏi dòng
    r, c = b.snap_outlet(acc, tr, lat, lon, radius_m=600, min_acc=50)
    assert (r, c) == (2, 3)                               # gần nhất, không phải ô lớn nhất
    r, c = b.snap_outlet(acc, tr, lat, lon, radius_m=600, min_acc=None)
    assert c == 3 and r > 2                               # kiểu cũ: trượt xuôi dòng


def test_sua_o_cut_khong_tao_vong():
    fd = np.full((3, 3), 4, dtype=np.int16)               # mọi ô chảy xuống (S)
    fd[1, 1] = -2                                         # hố còn sót
    demc = np.array([[5, 5, 5], [5, 3, 1.0], [5, 4, 5]], dtype=float)
    land = np.ones((3, 3), bool)
    assert b.fix_dead_ends(fd, demc, land) == 1
    assert fd[1, 1] == 1                                  # về phía đông (thấp nhất = 1.0)
    assert len(b.downstream_path(fd, 1, 1)) < 10


def test_lam_sach_manh_le():
    lab = np.ones((6, 6), dtype=np.uint8)
    lab[:, 3:] = 2
    lab[2, 4] = 1                                         # một ô lẻ nhãn 1 giữa vùng nhãn 2
    out = b.clean_label(lab, min_px=3)
    assert out[2, 4] == 2 and (out[:, :3] == 1).all()


# ------------------------------------------------------------ sản phẩm thật (nếu đã chạy)

def test_san_pham_luu_vuc_neu_co():
    f = b.BASIN_DIR / "subbasins.geojson"
    if not f.exists():
        pytest.skip("chưa chạy python -m src.features.basins")
    fc = json.loads(f.read_text(encoding="utf-8"))
    names = [x["properties"]["name"] for x in fc["features"]]
    assert names == list(b.SUBBASINS)
    for x in fc["features"]:
        assert {"name", "area_km2", "outlet_lat", "outlet_lon", "source"} <= set(x["properties"])
    kl = json.loads((b.BASIN_DIR / "huong_kim_long.geojson").read_text(encoding="utf-8"))
    tot = sum(x["properties"]["area_km2"] for x in fc["features"])
    assert tot == pytest.approx(kl["features"][0]["properties"]["area_km2"], abs=1.0)
    for tag in ("era5_0p1", "pccs_0p04", "gee_0p1"):
        w = pl.read_csv(b.BASIN_DIR / f"weights_{tag}.csv")
        sums = w.group_by("subbasin").agg(pl.col("weight").sum())["weight"].to_list()
        assert all(math.isclose(s, 1.0, abs_tol=1e-4) for s in sums)
