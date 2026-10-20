"""Địa hình 30 m + chia lưu vực sông Hương tới Kim Long thành lưu vực con.

Thầy yêu cầu ô mịn hơn 5 km và theo giờ. Muốn gộp mưa theo đúng phần lưu vực
đổ về Kim Long (thay cho khung chữ nhật thượng/trung/hạ) thì phải biết ranh
giới lưu vực. Module này:

1. Tải Copernicus DEM GLO-30 (bucket công khai AWS) → ghép, cắt theo
   ``config.FINE_BBOX`` → ``data/raw/dem/`` (gitignored).
2. Lấp trũng, xử lý vùng phẳng, hướng chảy D8, tích luỹ dòng chảy (pysheds).
3. Bắt điểm cửa ra (snap) vào ô gần nhất có tích luỹ ≥ ngưỡng (dòng chính), cắt
   lưu vực tới Kim Long, đập Tả Trạch, đập Bình Điền; phần còn lại tách tiếp
   tại ngã ba Tuần (nơi Tả Trạch gặp Hữu Trạch) → 5 lưu vực con không chồng lấn.

Kết quả (chạy 20/10/2026): Kim Long 1 543 km² (tham chiếu 1 490, +3,6 %; con số
2 830 km² trong config là của cả hệ thống Hương gồm sông Bồ), Tả Trạch 670 km²
(717, −6,5 %), Bình Điền 507 km² (515, −1,6 %). 64 ô ERA5 hiện có phủ 92,5 %
lưu vực Kim Long (hở 85 km² phía nam 16,05° N và 31 km² phía đông 107,85° E).
4. Ghi ``data/external/basins/{huong_kim_long,subbasins}.geojson`` và trọng số
   ô lưới cho ERA5 0,1°, PERSIANN-CCS 0,04° và IMERG/GSMaP 0,1° (``weights_gee_0p1``).

Hàm dùng chung (không cần DEM, chỉ cần geojson): :func:`cell_weights`,
:func:`basin_mean`, :func:`grid_coverage`.

    python -m src.features.basins            # chạy toàn bộ
    python -m src.features.basins --stage weights   # chỉ tính lại trọng số + hình
    python -m src.features.basins --stage plot      # chỉ vẽ lại hình

Cần: pysheds, rasterio, shapely, pyproj (pysheds 0.5 gọi np.in1d đã bỏ ở
numpy 2.4 — có shim trong :func:`flow_routing`).

Nguồn toạ độ: xem ``OUTLETS``. Diện tích tham chiếu: ``REF_AREA_KM2``.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import polars as pl

from src import config as cfg

DEM_DIR = cfg.DATA_RAW / "dem"
BASIN_DIR = cfg.DATA_EXTERNAL / "basins"
FIG = cfg.FIGURES / "report" / "basins_map.png"

DEM_URL = "https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"
DEM_TILES = ("N15_00_E107_00", "N16_00_E107_00")   # 1°×1°, đủ phủ FINE_BBOX
DEM_SOURCE = "Copernicus DEM GLO-30 (AWS s3://copernicus-dem-30m), D8 pysheds"

# Toạ độ GỐC trước khi snap. Mỗi điểm ghi nguồn; snap dời về ô GẦN NHẤT có
# tích luỹ ≥ min_km2 trong bán kính radius_m (ngưỡng loại suối nhánh nhỏ).
OUTLETS = {
    # Không tìm được toạ độ chính thức của trạm. Trạm "nằm 4 km thượng lưu trung
    # tâm Huế" (Hydrological Sciences J. 54(5), doi 10.1623/hysj.54.5.909) trên
    # sông Hương, đoạn chảy qua phường Kim Long (OSM relation 19324110, đường
    # Kim Long chạy dọc bờ bắc). Lấy (16,46 · 107,56) ở phường Kim Long. Điểm
    # docs/FINDINGS_GRID.md dùng (16,47 · 107,57) snap về cách đó ~1 km xuôi dòng,
    # diện tích chỉ hơn 4 km² (1 545 so với 1 541 km², đo 20/10/2026) — không nhạy.
    "kim_long": {
        "lat": 16.4600, "lon": 107.5600, "radius_m": 1500, "min_km2": 1000,
        "src": "Kim Long ward on Huong River (OSM relation 19324110; "
               "HSJ 54(5) doi:10.1623/hysj.54.5.909: '4 km upstream of the centre of Hue')",
    },
    # Đập Tả Trạch: OSM way 762253643 "Đập Tả Trạch" (tâm hình học).
    # Kiểm chéo: trạm Dương Hoà (hồ Tả Trạch) 16°18' N, 107°38' E, F = 717 km²
    # (JICA, openjicareport.jica.go.jp/pdf/11740701_06.pdf, bảng A2-2).
    "ta_trach": {
        "lat": 16.31258, "lon": 107.63158, "radius_m": 1000, "min_km2": 300,
        "src": "OSM way 762253643 'Dap Ta Trach'; cross-check JICA 11740701_06 "
               "table A2-2 Duong Hoa 16d18'N 107d38'E",
    },
    # Đập Bình Điền: OSM way 290884578 "Đập Bình Điền" (tâm hình học).
    # Kiểm chéo: trạm Bình Điền 16°20' N, 107°30' E, F = 570 km² (cùng bảng JICA).
    "binh_dien": {
        "lat": 16.31729, "lon": 107.50266, "radius_m": 1000, "min_km2": 300,
        "src": "OSM way 290884578 'Dap Binh Dien'; cross-check JICA 11740701_06 "
               "table A2-2 Binh Dien 16d20'N 107d30'E",
    },
}

# Điểm kiểm tra độc lập (không dùng để cắt): trạm thuỷ văn Thượng Nhật trên
# thượng nguồn Tả Trạch, 16°07'25" N, 107°41'14" E, F = 208 km² (UNESCO-IHP
# River Catalogue Vol.5 "Viet Nam-8 Huong River", mục 4.2 —
# hywr.kuciv.kyoto-u.ac.jp/ihp/riverCatalogue/Vol_05/11_Viet_Nam-8.pdf).
VALIDATION = {
    "thuong_nhat": {"lat": 16 + 7 / 60 + 25 / 3600, "lon": 107 + 41 / 60 + 14 / 3600,
                    "radius_m": 1000, "min_km2": 100, "ref_km2": 208.0},
}

# Diện tích tham chiếu (km²) để so sánh.
#  - Tả Trạch 717, Bình Điền 515: QĐ 1606/QĐ-TTg Phụ lục I (data/external/reservoir_info.csv)
#  - Kim Long: 2 830 km² trong config/FINDINGS_GRID là của CẢ HỆ THỐNG sông Hương
#    (gồm cả sông Bồ 938 km² — UNESCO-IHP River Catalogue Vol.5 "Viet Nam-8 Huong
#    River": "Area 2,830 km2 ... Main tributaries: ... Huu Trach River (729 km2),
#    Bo River (938 km2)"). Trạm Kim Long ở THƯỢNG LƯU ngã ba Sình nên không gồm
#    sông Bồ. Bảng đặc trưng dòng chảy ĐH Thuỷ lợi ghi "Hương – Kim Long 1 490".
REF_AREA_KM2 = {
    "kim_long_system_2830": 2830.0,
    "kim_long_tlu_1490": 1490.0,
    "ta_trach": 717.0,
    "binh_dien": 515.0,
}
REF_SRC = {
    "kim_long_system_2830": "src/config.py, docs/FINDINGS_GRID.md; UNESCO-IHP Catalogue Viet Nam-8 "
                            "(whole Huong system incl. Bo)",
    "kim_long_tlu_1490": "vjol.info.vn/DHTL/article/download/26636/22790 (Thuyloi Univ. journal)",
    "ta_trach": "QD 1606/QD-TTg Annex I (data/external/reservoir_info.csv)",
    "binh_dien": "QD 1606/QD-TTg Annex I (data/external/reservoir_info.csv)",
}

# Thứ tự lưu vực con (khoá trong geojson / bảng trọng số)
SUBBASINS = ("ta_trach_dam", "binh_dien_dam", "ta_trach_below_dam",
             "huu_trach_below_dam", "huong_tuan_kim_long")

# PERSIANN-CCS: lưới 3000×9000, 0,04°, ô đầu tiên (TB) có tâm 59,98° N, 0,02° E
# (persiann.eng.uci.edu/CHRSdata/PERSIANN-CCS/daily/readme.daily)
PCCS_LAT0, PCCS_LON0, PCCS_STEP = 59.98, 0.02, 0.04
# IMERG V07 / GSMaP v8 qua Earth Engine: ô 0,1°, biên ở bội số 0,1
GEE_STEP = 0.1

DIRMAP = (64, 128, 1, 2, 4, 8, 16, 32)   # N NE E SE S SW W NW (mặc định pysheds)
_DROWCOL = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1),
            4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}


# ================================================================ tiện ích

def _round(x, nd: int = 4):
    return round(float(x), nd)


def pixel_area_km2(lat_centers: np.ndarray, dlat: float, dlon: float) -> np.ndarray:
    """Diện tích (km²) một ô lưới địa lý theo vĩ độ tâm — công thức đới cầu trên
    bán kính quy đổi diện tích WGS84 (6371,0072 km). Ở 16,3° N cho LỚN hơn diện tích
    trên ellipsoid WGS84 (pyproj Geod) 0,34 % — vì vậy lưu vực Kim Long 1 543,4 km² ở
    đây ứng với 1 538,1 km² nếu đo bằng Geod (cũng là diện tích polygon geojson)."""
    r = 6371.0072
    lat1 = np.radians(lat_centers - dlat / 2)
    lat2 = np.radians(lat_centers + dlat / 2)
    return r * r * np.radians(dlon) * np.abs(np.sin(lat2) - np.sin(lat1))


def pccs_centers(bbox: dict = cfg.FINE_BBOX) -> tuple[np.ndarray, np.ndarray]:
    """Tâm ô PERSIANN-CCS trong khung bbox (theo quy ước readme của CHRS)."""
    i0 = math.ceil((PCCS_LAT0 - bbox["lat_max"]) / PCCS_STEP - 1e-9)
    i1 = math.floor((PCCS_LAT0 - bbox["lat_min"]) / PCCS_STEP + 1e-9)
    j0 = math.ceil((bbox["lon_min"] - PCCS_LON0) / PCCS_STEP - 1e-9)
    j1 = math.floor((bbox["lon_max"] - PCCS_LON0) / PCCS_STEP + 1e-9)
    lats = np.round(PCCS_LAT0 - PCCS_STEP * np.arange(i0, i1 + 1), 4)
    lons = np.round(PCCS_LON0 + PCCS_STEP * np.arange(j0, j1 + 1), 4)
    return lats, lons


def era5_centers() -> tuple[np.ndarray, np.ndarray]:
    """64 tâm ô ERA5 0,1° đã có trong data/raw/rain_hourly (lat 16,1–16,8; lon 107,1–107,8)."""
    return np.round(np.arange(16.1, 16.85, 0.1), 4), np.round(np.arange(107.1, 107.85, 0.1), 4)


def gee_centers(bbox: dict = cfg.FINE_BBOX) -> tuple[np.ndarray, np.ndarray]:
    """Tâm ô IMERG/GSMaP 0,1° (lưới gốc biên ở bội số 0,1 ⇒ tâm x,x5) trong bbox:
    10 × 10 ô, lat 15,85…16,75, lon 107,05…107,95 (``src/ingest/gee_precip.py``)."""
    def axis(lo, hi):
        n = int(round((hi - lo) / GEE_STEP))
        return np.round(lo + GEE_STEP * (np.arange(n) + 0.5), 4)
    return axis(bbox["lat_min"], bbox["lat_max"]), axis(bbox["lon_min"], bbox["lon_max"])


def mesh(lat_axis: Sequence[float], lon_axis: Sequence[float]) -> tuple[list, list]:
    """Hai trục → danh sách cặp tâm ô (lat, lon) dùng cho :func:`cell_weights`."""
    la, lo = np.meshgrid(np.asarray(lat_axis, float), np.asarray(lon_axis, float), indexing="ij")
    return la.ravel().tolist(), lo.ravel().tolist()


# ================================================================ lưu vực → ô lưới

def load_subbasins(path: Path | None = None) -> dict:
    """Đọc subbasins.geojson → {tên: shapely Polygon/MultiPolygon} (giữ thứ tự)."""
    from shapely.geometry import shape

    path = path or BASIN_DIR / "subbasins.geojson"
    fc = json.loads(Path(path).read_text(encoding="utf-8"))
    return {f["properties"]["name"]: shape(f["geometry"]) for f in fc["features"]}


def _geod_area_km2(geom) -> float:
    from pyproj import Geod

    if geom.is_empty:
        return 0.0
    a, _ = Geod(ellps="WGS84").geometry_area_perimeter(geom)
    return abs(a) / 1e6


def cell_weights(lats: Sequence[float], lons: Sequence[float], step_deg: float,
                 basins: dict | None = None) -> pl.DataFrame:
    """Trọng số diện tích của từng ô lưới trong từng lưu vực con.

    ``lats``, ``lons``: danh sách CẶP tâm ô cùng độ dài (ô thứ k = (lats[k], lons[k]));
    có hai trục riêng thì dùng :func:`mesh` trước. Ô là hình vuông cạnh ``step_deg``.
    ``basins``: {tên: polygon} (mặc định đọc subbasins.geojson).

    Trả về ``[subbasin, lat, lon, weight]``: weight = diện tích (ô ∩ lưu vực) /
    tổng diện tích phần lưu vực mà các ô này phủ ⇒ tổng weight mỗi lưu vực = 1.
    Ô không chạm lưu vực bị bỏ. Phần lưu vực nằm ngoài mọi ô KHÔNG được tính —
    xem :func:`grid_coverage` để biết phủ được bao nhiêu %.
    """
    from shapely import STRtree, box

    lats = np.asarray(lats, dtype=float).ravel()
    lons = np.asarray(lons, dtype=float).ravel()
    if lats.shape != lons.shape:
        raise ValueError("lats và lons phải là các cặp tâm ô cùng độ dài — dùng mesh() nếu là hai trục")
    if step_deg <= 0:
        raise ValueError("step_deg phải dương")
    basins = load_subbasins() if basins is None else basins
    h = step_deg / 2
    cells = [box(lo - h, la - h, lo + h, la + h) for la, lo in zip(lats, lons)]
    tree = STRtree(cells)

    rows = []
    for name, poly in basins.items():
        parts = []
        for k in tree.query(poly, predicate="intersects"):
            a = _geod_area_km2(cells[k].intersection(poly))
            if a > 1e-6:                     # bỏ giao "chạm biên" do sai số số thực (< 1 m²)
                parts.append((_round(lats[k]), _round(lons[k]), a))
        tot = sum(p[2] for p in parts)
        rows += [(name, la, lo, a / tot) for la, lo, a in parts] if tot > 0 else []
    return pl.DataFrame(rows, schema={"subbasin": pl.Utf8, "lat": pl.Float64,
                                      "lon": pl.Float64, "weight": pl.Float64},
                        orient="row").sort("subbasin", "lat", "lon")


def grid_coverage(lats: Sequence[float], lons: Sequence[float], step_deg: float,
                  basins: dict | None = None) -> pl.DataFrame:
    """% diện tích từng lưu vực (và toàn lưu vực) nằm trong hợp các ô lưới."""
    from shapely import box, union_all

    basins = load_subbasins() if basins is None else basins
    h = step_deg / 2
    cover = union_all([box(lo - h, la - h, lo + h, la + h)
                       for la, lo in zip(np.ravel(lats), np.ravel(lons))])
    items = dict(basins)
    items["huong_kim_long"] = union_all(list(basins.values()))
    out = []
    for name, poly in items.items():
        a = _geod_area_km2(poly)
        c = _geod_area_km2(poly.intersection(cover))
        out.append((name, a, c, 100 * c / a if a else float("nan")))
    return pl.DataFrame(out, schema=["subbasin", "area_km2", "covered_km2", "covered_pct"],
                        orient="row")


def basin_mean(df_long: pl.DataFrame, weights: pl.DataFrame, value_col: str,
               time_col: str | Sequence[str] = "time", wide: bool = False) -> pl.DataFrame:
    """Gộp chuỗi theo ô lưới (dạng dài: time, lat, lon, value) thành chuỗi theo lưu vực con.

    Trung bình có trọng số; nếu ô nào thiếu số liệu (null/NaN) ở một bước thời gian
    thì chia lại cho tổng trọng số các ô CÒN số liệu. Ghép lat/lon sau khi làm tròn
    4 chữ số để tránh lệch số thực. ``wide=True`` → mỗi lưu vực một cột
    ``{value_col}_{subbasin}``.
    """
    keys = [time_col] if isinstance(time_col, str) else list(time_col)
    v = (df_long.select(*keys, "lat", "lon", value_col)
         .with_columns(pl.col("lat").round(4), pl.col("lon").round(4),
                       pl.col(value_col).cast(pl.Float64).fill_nan(None)))
    w = weights.select("subbasin", pl.col("lat").round(4), pl.col("lon").round(4), "weight")
    j = v.join(w, on=["lat", "lon"], how="inner").filter(pl.col(value_col).is_not_null())
    out = (j.group_by(*keys, "subbasin")
            .agg(((pl.col(value_col) * pl.col("weight")).sum() / pl.col("weight").sum())
                 .alias(value_col))
            .sort(*keys, "subbasin"))
    if wide:
        out = (out.pivot(on="subbasin", index=keys, values=value_col)
                  .sort(keys))
        out = out.rename({c: f"{value_col}_{c}" for c in out.columns if c not in keys})
    return out


# ================================================================ DEM

def download_dem(tiles: Sequence[str] = DEM_TILES, dest: Path = DEM_DIR) -> list[Path]:
    """Tải ô DEM GLO-30 (COG ~30–50 MB/ô). Đã có file thì bỏ qua."""
    import requests

    dest.mkdir(parents=True, exist_ok=True)
    paths = []
    for t in tiles:
        n = f"Copernicus_DSM_COG_10_{t}_DEM"
        p = dest / f"{n}.tif"
        if not p.exists():
            r = requests.get(DEM_URL.format(n=n), timeout=600)
            r.raise_for_status()
            p.write_bytes(r.content)
            print(f"→ {p} ({len(r.content) / 1e6:.1f} MB)")
        paths.append(p)
    return paths


def build_dem(paths: Sequence[Path], bbox: dict = cfg.FINE_BBOX,
              out: Path = DEM_DIR / "dem_fine_bbox.tif") -> Path:
    """Ghép các ô và cắt theo bbox → GeoTIFF float32 nén."""
    import rasterio
    from rasterio.merge import merge

    srcs = [rasterio.open(p) for p in paths]
    arr, tr = merge(srcs, bounds=(bbox["lon_min"], bbox["lat_min"], bbox["lon_max"], bbox["lat_max"]))
    prof = srcs[0].profile.copy()
    for s in srcs:
        s.close()
    # GLO-30 không có nodata; biển/phá ≤ 0 m. Khai báo nodata = -9999 rõ ràng,
    # nếu không pysheds mặc định nodata = 0 và coi mọi ô 0 m là "không có số liệu".
    prof.update(driver="GTiff", height=arr.shape[1], width=arr.shape[2], transform=tr,
                nodata=-9999.0,
                dtype="float32", compress="deflate", predictor=3, tiled=True,
                blockxsize=512, blockysize=512, count=1)
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(arr.astype("float32"))
    return out


def fix_dead_ends(fd: np.ndarray, demc: np.ndarray, land: np.ndarray) -> int:
    """Ô trên đất liền (không ở biên) mà D8 không có hướng → trỏ về ô lân cận thấp
    nhất KHÔNG tạo vòng lặp. Sửa tại chỗ, trả về số ô đã sửa.

    Lý do: resolve_flats của pysheds có thể nâng một vùng phẳng cao hơn ô ra của
    nó vài mm, tạo hố mới; một hố như vậy ở thượng nguồn Tả Trạch (16,14 N;
    107,82 E) từng "nuốt" 49 km² lưu vực."""
    h, w = fd.shape
    fixed = 0
    for r, c in zip(*np.nonzero((fd <= 0) & land)):
        if r in (0, h - 1) or c in (0, w - 1):
            continue                                  # ô biên = cửa ra khung, giữ nguyên
        for _, d in sorted((float(demc[r + dr, c + dc]), d) for d, (dr, dc) in _DROWCOL.items()):
            dr, dc = _DROWCOL[d]
            if (int(r), int(c)) not in set(downstream_path(fd, r + dr, c + dc, 500_000)):
                fd[r, c] = d
                fixed += 1
                break
    return fixed


def flow_routing(dem_path: Path = DEM_DIR / "dem_fine_bbox.tif") -> dict:
    """Lấp hố → lấp trũng → xử lý phẳng → hướng chảy D8 → tích luỹ (số ô).

    Tính bằng float64 và eps = 1e-7: với float32 + eps mặc định 1e-5, pysheds để
    lại 631 ô cụt trên đất > 2 m; float64 + 1e-7 còn 12 ô (> 0 m), sửa nốt bằng
    :func:`fix_dead_ends`. Ô biển/phá (≤ 0 m) không có hướng thì để nguyên."""
    import rasterio
    from pysheds.grid import Grid
    from pysheds.sview import Raster

    if not hasattr(np, "in1d"):          # pysheds 0.5 còn gọi np.in1d (đã bỏ ở numpy 2.4)
        np.in1d = np.isin
    grid = Grid.from_raster(str(dem_path))
    raw = grid.read_raster(str(dem_path))
    dem = Raster(np.asarray(raw, dtype="float64"), viewfinder=raw.viewfinder)
    dem = grid.fill_pits(dem)
    dem = grid.fill_depressions(dem)
    dem = grid.resolve_flats(dem, eps=1e-7)
    fdir = grid.flowdir(dem, dirmap=DIRMAP)
    fd = np.asarray(fdir).astype("int16")
    n_fixed = fix_dead_ends(fd, np.asarray(dem), np.asarray(raw) > 0)
    fdir = Raster(fd, viewfinder=fdir.viewfinder)
    acc = grid.accumulation(fdir, dirmap=DIRMAP)
    with rasterio.open(dem_path) as r:
        prof, tr = r.profile.copy(), r.transform
    fd[fd < 0] = 0                                  # phẳng/hố (biển, phá) → 0
    prof.update(dtype="uint8", nodata=0, predictor=1)
    with rasterio.open(DEM_DIR / "fdir.tif", "w", **prof) as dst:
        dst.write(fd.astype("uint8"), 1)
    prof.update(dtype="float32", nodata=None, predictor=3)
    with rasterio.open(DEM_DIR / "acc.tif", "w", **prof) as dst:
        dst.write(np.asarray(acc, dtype="float32"), 1)
    print(f"  hướng chảy: sửa {n_fixed} ô cụt trên đất liền")
    return {"fdir": fd.astype("uint8"), "acc": np.asarray(acc, dtype="float32"), "transform": tr,
            "n_dead_end_fixed": n_fixed}


def load_routing() -> dict:
    import rasterio

    with rasterio.open(DEM_DIR / "fdir.tif") as r:
        fdir, tr = r.read(1), r.transform
    with rasterio.open(DEM_DIR / "acc.tif") as r:
        acc = r.read(1)
    return {"fdir": fdir, "acc": acc, "transform": tr}


def _rc(tr, lat: float, lon: float) -> tuple[int, int]:
    col, row = (lon - tr.c) / tr.a, (lat - tr.f) / tr.e      # lưới địa lý, không xoay
    return int(math.floor(row)), int(math.floor(col))


def _xy(tr, row: int, col: int) -> tuple[float, float]:
    lon, lat = tr.c + (col + 0.5) * tr.a, tr.f + (row + 0.5) * tr.e
    return lat, lon


def snap_outlet(acc: np.ndarray, tr, lat: float, lon: float, radius_m: float,
                min_acc: float | None = None) -> tuple[int, int]:
    """Bắt điểm cửa ra vào dòng chính.

    ``min_acc`` (cùng đơn vị với acc): chọn ô GẦN NHẤT có tích luỹ ≥ min_acc trong
    bán kính — tránh lỗi của cách "lấy ô tích luỹ lớn nhất", vốn luôn trượt xuôi
    dòng tới mép vòng tìm kiếm. Không có ô nào đạt ngưỡng (hoặc min_acc=None) thì
    lấy ô tích luỹ lớn nhất trong bán kính."""
    r0, c0 = _rc(tr, lat, lon)
    dy = abs(tr.e) * 110_574.0
    dx = abs(tr.a) * 111_320.0 * math.cos(math.radians(lat))
    nr, nc = int(radius_m / dy) + 1, int(radius_m / dx) + 1
    rs, cs = slice(max(r0 - nr, 0), r0 + nr + 1), slice(max(c0 - nc, 0), c0 + nc + 1)
    win = acc[rs, cs].astype("float64")
    yy, xx = np.mgrid[rs.start:rs.start + win.shape[0], cs.start:cs.start + win.shape[1]]
    d2 = ((yy - r0) * dy) ** 2 + ((xx - c0) * dx) ** 2
    inside = d2 <= radius_m ** 2
    ok = inside & (win >= min_acc) if min_acc is not None else np.zeros_like(inside)
    if ok.any():
        score = np.where(ok, d2 - 1e-9 * win, np.inf)          # gần nhất, hoà thì lấy acc lớn
        k = np.unravel_index(int(np.argmin(score)), win.shape)
    else:
        k = np.unravel_index(int(np.argmax(np.where(inside, win, -1))), win.shape)
    return rs.start + int(k[0]), cs.start + int(k[1])


def downstream_path(fdir: np.ndarray, row: int, col: int, max_steps: int = 10_000_000) -> list:
    """Danh sách ô (row, col) đi xuôi dòng từ (row, col) tới khi ra khỏi lưới / gặp ô không hướng."""
    path = [(row, col)]
    h, w = fdir.shape
    for _ in range(max_steps):
        d = int(fdir[row, col])
        if d not in _DROWCOL:
            break
        dr, dc = _DROWCOL[d]
        row, col = row + dr, col + dc
        if not (0 <= row < h and 0 <= col < w):
            break
        path.append((row, col))
    return path


def catchment_mask(fdir: np.ndarray, row: int, col: int) -> np.ndarray:
    """Mặt nạ các ô chảy về (row, col) — duyệt NGƯỢC hướng chảy (BFS), không đệ quy."""
    h, w = fdir.shape
    mask = np.zeros((h, w), dtype=bool)
    mask[row, col] = True
    frontier = np.array([[row, col]])
    # ô lân cận (dr, dc) chảy VÀO ô hiện tại nếu hướng của nó trỏ về (−dr, −dc)
    inflow = [(-dr, -dc, d) for d, (dr, dc) in _DROWCOL.items()]
    while frontier.size:
        nxt = []
        for dr, dc, d in inflow:
            r = frontier[:, 0] + dr
            c = frontier[:, 1] + dc
            ok = (r >= 0) & (r < h) & (c >= 0) & (c < w)
            r, c = r[ok], c[ok]
            hit = (fdir[r, c] == d) & ~mask[r, c]
            if hit.any():
                rr, cc = r[hit], c[hit]
                mask[rr, cc] = True
                nxt.append(np.stack([rr, cc], axis=1))
        frontier = np.concatenate(nxt) if nxt else np.empty((0, 2), dtype=int)
    return mask


def delineate(routing: dict) -> dict:
    """Bắt điểm cửa ra, cắt 5 lưu vực con không chồng lấn. Trả về dict kết quả."""
    fdir, acc, tr = routing["fdir"], routing["acc"], routing["transform"]
    rows = np.arange(fdir.shape[0])
    lat_c = tr.f + (rows + 0.5) * tr.e
    pix_km2 = pixel_area_km2(lat_c, abs(tr.e), abs(tr.a))[:, None]

    cell_km2 = float(pixel_area_km2(np.array([16.3]), abs(tr.e), abs(tr.a))[0])
    snapped = {k: snap_outlet(acc, tr, o["lat"], o["lon"], o["radius_m"], o["min_km2"] / cell_km2)
               for k, o in OUTLETS.items()}
    # Ngã ba Tuần: ô ĐẦU TIÊN chung của hai đường xuôi dòng từ hai đập
    p_ta = downstream_path(fdir, *snapped["ta_trach"])
    p_bd = downstream_path(fdir, *snapped["binh_dien"])
    set_bd = {p: i for i, p in enumerate(p_bd)}
    i_ta = next(i for i, p in enumerate(p_ta) if p in set_bd)
    conf = p_ta[i_ta]
    i_bd = set_bd[conf]
    br_ta, br_bd = p_ta[i_ta - 1], p_bd[i_bd - 1]      # ô cuối của mỗi nhánh trước hợp lưu
    on_path_kl = snapped["kim_long"] in set(downstream_path(fdir, *conf))

    m = {
        "kim_long": catchment_mask(fdir, *snapped["kim_long"]),
        "ta_trach": catchment_mask(fdir, *snapped["ta_trach"]),
        "binh_dien": catchment_mask(fdir, *snapped["binh_dien"]),
        "br_ta": catchment_mask(fdir, *br_ta),
        "br_bd": catchment_mask(fdir, *br_bd),
        "conf": catchment_mask(fdir, *conf),
    }
    label = np.zeros(fdir.shape, dtype="uint8")
    label[m["kim_long"]] = 5                              # huong_tuan_kim_long
    label[m["br_ta"]] = 3                                 # ta_trach_below_dam
    label[m["br_bd"]] = 4                                 # huu_trach_below_dam
    label[m["ta_trach"]] = 1
    label[m["binh_dien"]] = 2
    label[~m["kim_long"]] = 0
    label = clean_label(label)
    for k in ("ta_trach", "binh_dien"):
        if not m["kim_long"][snapped[k]]:
            raise RuntimeError(f"Đập {k} không nằm trong lưu vực Kim Long — kiểm tra điểm cửa ra")
    if not on_path_kl:
        raise RuntimeError("Ngã ba Tuần không chảy về Kim Long — kiểm tra điểm cửa ra")

    def area(mask):
        return float((mask * pix_km2).sum())

    pts = {k: _xy(tr, *v) for k, v in snapped.items()}
    pts["tuan_confluence"] = _xy(tr, *conf)
    pts["br_ta"], pts["br_bd"] = _xy(tr, *br_ta), _xy(tr, *br_bd)
    sub_area = {name: float(((label == i + 1) * pix_km2).sum()) for i, name in enumerate(SUBBASINS)}
    touches_edge = bool(m["kim_long"][0, :].any() or m["kim_long"][-1, :].any()
                        or m["kim_long"][:, 0].any() or m["kim_long"][:, -1].any())
    # Kiểm tra độc lập ở thượng nguồn: trạm Thượng Nhật (không dùng để cắt lưu vực)
    v = VALIDATION["thuong_nhat"]
    near = snap_outlet(acc, tr, v["lat"], v["lon"], v["radius_m"], v["min_km2"] / cell_km2)
    below = snap_outlet(acc, tr, v["lat"], v["lon"], v["radius_m"], None)
    checks = {"thuong_nhat": {"ref_km2": v["ref_km2"],
                              "nearest_km2": float(acc[near] * pix_km2[near[0], 0]),
                              "max_in_radius_km2": float(acc[below] * pix_km2[below[0], 0]),
                              "max_in_radius_dist_m": _dist_m(v["lat"], v["lon"], *_xy(tr, *below))}}
    return {
        "label": label, "transform": tr, "snapped_rc": snapped, "points": pts,
        "areas": {"kim_long": area(m["kim_long"]), "ta_trach": area(m["ta_trach"]),
                  "binh_dien": area(m["binh_dien"]), "conf": area(m["conf"]),
                  "br_ta": area(m["br_ta"]), "br_bd": area(m["br_bd"])},
        "sub_area": sub_area, "acc_km2_at": {k: float(acc[v] * pix_km2[v[0], 0])
                                             for k, v in snapped.items()},
        "confluence_on_kim_long_path": bool(on_path_kl), "touches_edge": touches_edge,
        "snap_dist_m": {k: _dist_m(OUTLETS[k]["lat"], OUTLETS[k]["lon"], *pts[k]) for k in OUTLETS},
        "checks": checks,
    }


def clean_label(label: np.ndarray, min_px: int = 50) -> np.ndarray:
    """Mảnh rời < min_px ô (D8 nối chéo → vector hoá 4-liên thông tách ra 1 ô lẻ)
    gán sang nhãn lưu vực con lân cận phổ biến nhất (khác 0)."""
    from scipy import ndimage

    out = label.copy()
    for v in [int(x) for x in np.unique(label) if x > 0]:
        comp, _ = ndimage.label(out == v)
        sizes = np.bincount(comp.ravel())
        boxes = ndimage.find_objects(comp)
        for k in np.nonzero(sizes < min_px)[0]:
            if k == 0:
                continue
            sl = tuple(slice(max(s.start - 1, 0), s.stop + 1) for s in boxes[k - 1])
            mk = comp[sl] == k
            ring = ndimage.binary_dilation(mk) & ~mk
            nb = out[sl][ring]
            nb = nb[(nb != v) & (nb > 0)]
            if nb.size:
                out[sl][mk] = np.bincount(nb).argmax()
    return out


def _dist_m(lat1, lon1, lat2, lon2) -> float:
    dy = (lat2 - lat1) * 110_574.0
    dx = (lon2 - lon1) * 111_320.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


# ================================================================ vector hoá + ghi

def polygons_from_label(label: np.ndarray, tr, simplify_deg: float = 0.0003) -> dict:
    """Raster nhãn → {tên lưu vực con: polygon}, đơn giản hoá theo kiểu 'coverage'
    (giữ biên chung giữa các lưu vực, không sinh khe hở/chồng lấn)."""
    import shapely
    from rasterio.features import shapes
    from shapely.geometry import shape

    geoms = {i: [] for i in range(1, len(SUBBASINS) + 1)}
    for g, v in shapes(label, mask=label > 0, transform=tr, connectivity=4):
        geoms[int(v)].append(shape(g))
    polys = [shapely.union_all(geoms[i]) for i in range(1, len(SUBBASINS) + 1)]
    # bỏ mảnh vụn (do D8 ở vùng phẳng) < 1 km² ~ 1 100 ô 30 m
    polys = [_drop_slivers(p, 1e-4) for p in polys]
    simp = shapely.coverage_simplify(polys, tolerance=simplify_deg, simplify_boundary=True)
    simp = shapely.set_precision(simp, 1e-5)          # ~1 m
    simp = [shapely.make_valid(p) for p in simp]
    return dict(zip(SUBBASINS, simp))


def _drop_slivers(geom, min_area_deg2: float):
    from shapely.geometry import MultiPolygon, Polygon

    if isinstance(geom, Polygon):
        return Polygon(geom.exterior)
    keep = [Polygon(p.exterior) for p in geom.geoms if p.area >= min_area_deg2]
    return keep[0] if len(keep) == 1 else MultiPolygon(keep)


def write_geojson(res: dict, polys: dict) -> None:
    import shapely
    from shapely.geometry import mapping

    BASIN_DIR.mkdir(parents=True, exist_ok=True)
    pts = res["points"]
    outlet = {"ta_trach_dam": pts["ta_trach"], "binh_dien_dam": pts["binh_dien"],
              "ta_trach_below_dam": pts["br_ta"], "huu_trach_below_dam": pts["br_bd"],
              "huong_tuan_kim_long": pts["kim_long"]}
    ref = {"ta_trach_dam": REF_AREA_KM2["ta_trach"], "binh_dien_dam": REF_AREA_KM2["binh_dien"]}
    feats = []
    for name in SUBBASINS:
        a = res["sub_area"][name]
        props = {"name": name, "area_km2": round(a, 1),
                 "outlet_lat": round(outlet[name][0], 5), "outlet_lon": round(outlet[name][1], 5),
                 "source": DEM_SOURCE}
        if name in ref:
            props["ref_area_km2"] = ref[name]
            props["diff_pct"] = round(100 * (a - ref[name]) / ref[name], 1)
        feats.append({"type": "Feature", "properties": props, "geometry": mapping(polys[name])})
    (BASIN_DIR / "subbasins.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")

    whole = shapely.union_all(list(polys.values()))
    akl = res["areas"]["kim_long"]
    props = {"name": "huong_kim_long", "area_km2": round(akl, 1),
             "outlet_lat": round(pts["kim_long"][0], 5), "outlet_lon": round(pts["kim_long"][1], 5),
             "source": DEM_SOURCE, "outlet_source": OUTLETS["kim_long"]["src"]}
    for k in ("kim_long_system_2830", "kim_long_tlu_1490"):
        props[f"ref_{k}"] = REF_AREA_KM2[k]
        props[f"diff_pct_{k}"] = round(100 * (akl - REF_AREA_KM2[k]) / REF_AREA_KM2[k], 1)
    (BASIN_DIR / "huong_kim_long.geojson").write_text(
        json.dumps({"type": "FeatureCollection",
                    "features": [{"type": "Feature", "properties": props, "geometry": mapping(whole)}]},
                   ensure_ascii=False), encoding="utf-8")


def write_label_raster(res: dict) -> None:
    import rasterio

    with rasterio.open(DEM_DIR / "dem_fine_bbox.tif") as r:
        prof = r.profile.copy()
    prof.update(dtype="uint8", nodata=0, predictor=1)
    with rasterio.open(DEM_DIR / "subbasins.tif", "w", **prof) as dst:
        dst.write(res["label"], 1)


# tag → (hàm trả hai trục tâm ô, cạnh ô °)
GRIDS = {"era5_0p1": (era5_centers, 0.1),
         "pccs_0p04": (pccs_centers, PCCS_STEP),
         "gee_0p1": (gee_centers, GEE_STEP)}


def write_grid_weights(tag: str, basins: dict | None = None) -> dict:
    """Tính + ghi ``weights_{tag}.csv`` cho một lưới trong :data:`GRIDS`;
    trả về {"weights", "coverage"} (coverage: % lưu vực nằm trong lưới)."""
    centers, step = GRIDS[tag]
    basins = load_subbasins() if basins is None else basins
    lats, lons = mesh(*centers())
    w = cell_weights(lats, lons, step, basins)
    w.write_csv(BASIN_DIR / f"weights_{tag}.csv", float_precision=6)
    return {"weights": w, "coverage": grid_coverage(lats, lons, step, basins)}


def write_weights() -> dict:
    """Trọng số cho lưới ERA5 0,1° (64 ô hiện có), PERSIANN-CCS 0,04° và
    IMERG/GSMaP 0,1° (FINE_BBOX)."""
    basins = load_subbasins()
    return {tag: write_grid_weights(tag, basins) for tag in GRIDS}


# ================================================================ hình

def plot_map(dest: Path = FIG) -> Path:
    """Bản đồ: DEM nền, ranh giới lưu vực con, sông (từ DEM), Kim Long + 2 đập, lưới."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio
    from matplotlib.colors import LightSource, ListedColormap
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from shapely.geometry import shape

    with rasterio.open(DEM_DIR / "dem_fine_bbox.tif") as r:
        dem_full = r.read(1)
        b = r.bounds
    with rasterio.open(DEM_DIR / "acc.tif") as r:
        acc = r.read(1)
        tr = r.transform
    basins = load_subbasins()
    kl = json.loads((BASIN_DIR / "huong_kim_long.geojson").read_text(encoding="utf-8"))
    props = kl["features"][0]["properties"]
    whole = shape(kl["features"][0]["geometry"])
    sub_props = {f["properties"]["name"]: f["properties"] for f in
                 json.loads((BASIN_DIR / "subbasins.geojson").read_text(encoding="utf-8"))["features"]}

    fig, ax = plt.subplots(figsize=(7.2, 6.6), dpi=200)
    ext = (b.left, b.right, b.bottom, b.top)
    dem = dem_full[::4, ::4]                                       # ~120 m cho nền
    land = ListedColormap(plt.get_cmap("terrain")(np.linspace(0.25, 1.0, 256)))
    shade = LightSource(azdeg=315, altdeg=45).hillshade(np.clip(dem, 0, None), vert_exag=0.03)
    ax.imshow(np.where(dem > 0, np.nan, 1.0), extent=ext, cmap=ListedColormap(["#d6e6f5"]),
              zorder=0)
    ax.imshow(np.where(dem > 0, shade, np.nan), extent=ext, cmap="gray", vmin=0, vmax=1,
              alpha=0.6, zorder=0)
    im = ax.imshow(np.where(dem > 0, dem, np.nan), extent=ext, cmap=land, vmin=0, vmax=1600,
                   alpha=0.45, zorder=1)

    # sông từ tích luỹ DEM (chỉ trên đất liền): ≥ 20 km² nét mảnh, ≥ 300 km² nét đậm
    lat_c = tr.f + (np.arange(acc.shape[0]) + 0.5) * tr.e
    akm = acc * pixel_area_km2(lat_c, abs(tr.e), abs(tr.a))[:, None]
    for thr, size, col in ((20, 0.06, "#3b78c4"), (300, 0.5, "#0b3d91")):
        rr, cc = np.nonzero((akm >= thr) & (dem_full > 0))   # mặt sông GLO-30 ~0,5 m
        ax.scatter(tr.c + (cc + 0.5) * tr.a, tr.f + (rr + 0.5) * tr.e, s=size, c=col, lw=0,
                   zorder=4, rasterized=True)

    colors = {"ta_trach_dam": "#d95f02", "binh_dien_dam": "#7570b3", "ta_trach_below_dam": "#e6ab02",
              "huu_trach_below_dam": "#1b9e77", "huong_tuan_kim_long": "#e7298a"}
    labels = {"ta_trach_dam": "Ta Trach reservoir", "binh_dien_dam": "Binh Dien reservoir",
              "ta_trach_below_dam": "Ta Trach below dam", "huu_trach_below_dam": "Huu Trach below dam",
              "huong_tuan_kim_long": "Huong: Tuan to Kim Long"}
    for name, g in basins.items():
        for p in getattr(g, "geoms", [g]):
            x, y = p.exterior.xy
            ax.fill(x, y, color=colors[name], alpha=0.30, lw=0, zorder=2)
            ax.plot(x, y, color=colors[name], lw=0.8, zorder=5)
    for p in getattr(whole, "geoms", [whole]):
        x, y = p.exterior.xy
        ax.plot(x, y, color="black", lw=1.5, zorder=6)

    # lưới GloFAS 0,05° (biên ô ở bội số 0,05) và ERA5 0,1° (64 ô hiện có, biên ở x,x5)
    for v in np.arange(107.0, 108.0 + 1e-9, 0.05):
        ax.axvline(v, color="#444444", lw=0.3, alpha=0.35, ls=(0, (2, 2)), zorder=7)
    for v in np.arange(15.8, 16.8 + 1e-9, 0.05):
        ax.axhline(v, color="#444444", lw=0.3, alpha=0.35, ls=(0, (2, 2)), zorder=7)
    la, lo = era5_centers()
    for v in np.append(lo - 0.05, lo[-1] + 0.05):
        ax.plot([v, v], [la[0] - 0.05, la[-1] + 0.05], color="#08306b", lw=0.7, alpha=0.55, zorder=7)
    for v in np.append(la - 0.05, la[-1] + 0.05):
        ax.plot([lo[0] - 0.05, lo[-1] + 0.05], [v, v], color="#08306b", lw=0.7, alpha=0.55, zorder=7)

    kl_pt = (props["outlet_lat"], props["outlet_lon"])
    ax.plot(kl_pt[1], kl_pt[0], marker="o", ms=7, mfc="red", mec="white", mew=1.2, zorder=9)
    ax.annotate(f"Kim Long (outlet)\n{props['area_km2']:,.0f} km²", kl_pt[::-1], xytext=(8, 4),
                textcoords="offset points", fontsize=7.5, fontweight="bold", zorder=10)
    for nm, lab, off, ha in (("ta_trach_dam", "Ta Trach dam", (8, -4), "left"),
                             ("binh_dien_dam", "Binh Dien dam", (-8, -4), "right")):
        sp = sub_props[nm]
        ax.plot(sp["outlet_lon"], sp["outlet_lat"], marker="^", ms=7, mfc="black", mec="white",
                mew=1.0, zorder=9)
        ax.annotate(f"{lab}\n{sp['area_km2']:,.0f} km² (ref. {sp['ref_area_km2']:,.0f})",
                    (sp["outlet_lon"], sp["outlet_lat"]), xytext=off, textcoords="offset points",
                    fontsize=6.5, ha=ha, va="top", zorder=10,
                    bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.7})
    cf = sub_props["ta_trach_below_dam"]
    ax.plot(cf["outlet_lon"], cf["outlet_lat"], marker="D", ms=3.5, mfc="white", mec="black",
            mew=0.8, zorder=9)
    ax.annotate("Tuan confluence", (cf["outlet_lon"], cf["outlet_lat"]), xytext=(6, 2),
                textcoords="offset points", fontsize=6.3, zorder=10)
    ax.plot(107.50, 16.45, marker="s", ms=5, mfc="none", mec="black", mew=1.0, zorder=9)
    ax.annotate("GloFAS target point\n(16.45, 107.50)", (107.50, 16.45), xytext=(-6, 6),
                textcoords="offset points", fontsize=6.3, ha="right", zorder=10)

    handles = [Patch(facecolor=colors[k], alpha=0.5, edgecolor=colors[k],
                     label=f"{labels[k]} ({sub_props[k]['area_km2']:,.0f} km²)") for k in SUBBASINS]
    handles += [Line2D([], [], color="black", lw=1.5, label="Basin to Kim Long"),
                Line2D([], [], color="#0b3d91", lw=1.5, label="Main rivers (DEM, ≥ 300 km²)"),
                Line2D([], [], color="#3b78c4", lw=0.6, label="Streams (DEM, ≥ 20 km²)"),
                Line2D([], [], color="#08306b", lw=0.8, alpha=0.6, label="ERA5 0.1° cells (64 in use)"),
                Line2D([], [], color="#444444", lw=0.6, ls=(0, (2, 2)), label="GloFAS 0.05° grid")]
    ax.legend(handles=handles, loc="upper right", fontsize=6.2, framealpha=0.92)
    cb = fig.colorbar(im, ax=ax, shrink=0.55, pad=0.02)
    cb.set_label("Elevation (m), Copernicus DEM GLO-30", fontsize=7)
    cb.ax.tick_params(labelsize=6.5)
    ax.set_xlim(107.05, 107.95)
    ax.set_ylim(15.9, 16.75)
    ax.set_aspect(1 / math.cos(math.radians(16.3)))
    ax.set_xlabel("Longitude (°E)", fontsize=8)
    ax.set_ylabel("Latitude (°N)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title("Huong River basin to Kim Long: sub-basins delineated from 30 m DEM",
                 fontsize=9.5, fontweight="bold")
    fig.tight_layout()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, facecolor="white")
    plt.close(fig)
    return dest


# ================================================================ chạy

def report(res: dict) -> None:
    a = res["areas"]
    print("Điểm cửa ra sau snap (lat, lon) | lệch so với điểm gốc:")
    for k, (la, lo) in res["points"].items():
        d = res["snap_dist_m"].get(k)
        print(f"  {k:18s} {la:.5f} {lo:.5f}" + (f"  | {d:,.0f} m" if d is not None else ""))
    print(f"Lưu vực chạm biên khung DEM: {res['touches_edge']}")
    for k, ref in (("kim_long", "kim_long_system_2830"), ("kim_long", "kim_long_tlu_1490"),
                   ("ta_trach", "ta_trach"), ("binh_dien", "binh_dien")):
        r = REF_AREA_KM2[ref]
        print(f"  {k:10s} {a[k]:8.1f} km²  vs {ref:22s} {r:7.1f}  → lệch {100 * (a[k] - r) / r:+.1f} %")
    print("Lưu vực con:")
    for k, v in res["sub_area"].items():
        print(f"  {k:22s} {v:8.1f} km²")
    print(f"  tổng                   {sum(res['sub_area'].values()):8.1f} km²")
    tn = res["checks"]["thuong_nhat"]
    print(f"Kiểm tra Thượng Nhật (ref {tn['ref_km2']:.0f} km²): ô sông gần nhất {tn['nearest_km2']:.1f} km²;"
          f" lớn nhất trong 1 km {tn['max_in_radius_km2']:.1f} km² (cách {tn['max_in_radius_dist_m']:,.0f} m)")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", choices=["all", "weights", "plot"], default="all")
    args = ap.parse_args(argv)
    if args.stage == "all":
        paths = download_dem()
        dem = build_dem(paths)
        print(f"→ {dem}")
        routing = flow_routing(dem)
        res = delineate(routing)
        report(res)
        polys = polygons_from_label(res["label"], res["transform"])
        write_geojson(res, polys)
        write_label_raster(res)
    if args.stage in ("all", "weights"):
        for tag, d in write_weights().items():
            w = d["weights"]
            print(f"weights_{tag}.csv: {w.height} dòng, {w['lat'].n_unique()}×{w['lon'].n_unique()} ô chạm lưu vực")
            print(d["coverage"])
    print(f"→ {plot_map()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
