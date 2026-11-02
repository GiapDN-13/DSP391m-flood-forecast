"""Bản Spark cho nguồn vệ tinh (``spark_hourly`` với ``imerg``/``gsmap_*``) phải TRÙNG bản
Polars (``hourly_features``) tới từng bit: gộp nửa giờ IMERG về giờ, cùng danh sách file
tháng + ``_parts`` của JAXA, rồi cả pipeline giờ → ngày. Dữ liệu giả trong thư mục tạm;
thêm một test trên 1 tháng IMERG thật nếu máy có file. Bỏ qua cả file nếu máy không có
pyspark hoặc Java (như ``tests/test_spark_parity.py``)."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest

pytest.importorskip("pyspark")
if not (shutil.which("java") or os.environ.get("JAVA_HOME")):
    pytest.skip("không có Java — bỏ qua test Spark", allow_module_level=True)

from src.distributed import spark_hourly as sh  # noqa: E402
from src.distributed import spark_session  # noqa: E402
from src.features import hourly_features as hf  # noqa: E402

AREAS = {"u1": 670.4, "u2": 506.8, "u3": 88.2, "u4": 185.1, "u5": 92.8}
# lưới 0,1° tâm x,x5 như Earth Engine; ô (16.45, 107.75) KHÔNG có trong bảng trọng số
CELLS = [(16.15, 107.45), (16.15, 107.55), (16.25, 107.45), (16.25, 107.55), (16.35, 107.65),
         (16.45, 107.75)]
WEIGHTS = pl.DataFrame(
    [("u1", 16.15, 107.45, 0.25), ("u1", 16.15, 107.55, 0.75),
     ("u2", 16.25, 107.45, 0.4), ("u2", 16.25, 107.55, 0.6),
     ("u3", 16.35, 107.65, 1.0),
     ("u4", 16.25, 107.55, 0.2), ("u4", 16.35, 107.65, 0.8),
     ("u5", 16.15, 107.55, 0.3), ("u5", 16.25, 107.45, 0.7)],
    schema={"subbasin": pl.Utf8, "lat": pl.Float64, "lon": pl.Float64, "weight": pl.Float64},
    orient="row")
T0 = datetime(2020, 10, 1, 0, 30)          # nhãn CUỐI nửa giờ đầu tiên (giờ VN)
N_DAYS = 4


def _imerg_grid() -> pl.DataFrame:
    """4 ngày × 6 ô bước 30 phút, cường độ mm/giờ Float32 như file Earth Engine; có NaN,
    nửa giờ thiếu (giờ đó phải rỗng), ngày 2 mọi ô 0,5 mm/h lúc 00–06h rồi khô (đỉnh hoà
    nhau) và ngày 3 mọi ô 1 mm/h lúc 09–11h (→ đúng 1 mm/giờ, ngưỡng giờ mưa)."""
    rng = np.random.default_rng(391)
    vals = np.array([0.0, 0.0, 0.0, 0.2, 0.4, 1.3, 2.0, 5.7, 14.9], dtype=np.float32)
    rows = []
    for k in range(N_DAYS * 48):
        t = T0 + timedelta(minutes=30 * k)
        for lat, lon in CELLS:
            p = float(rng.choice(vals))
            if 46 <= k < 94:                                # giờ 00…23 ngày 2
                p = 0.5 if k < 60 else 0.0                  # 00–06h: mọi ô 0,5 mm/h
            elif 96 + 16 <= k < 96 + 22:
                p = 1.0                                     # ngày 3, giờ 09–11h: 1 mm/h
            if k == 30 and (lat, lon) == (16.15, 107.55):
                p = float("nan")                            # NaN → giờ đó ô này rỗng
            if k == 3 * 48 + 30 and (lat, lon) == (16.35, 107.65):
                continue                                    # thiếu 1 nửa giờ → u3 rỗng
            rows.append((t - timedelta(hours=7), t, lat, lon, p))
    return pl.DataFrame(rows, schema={"time_utc": pl.Datetime("ms"), "time": pl.Datetime("ms"),
                                      "lat": pl.Float64, "lon": pl.Float64,
                                      "precip_mm_hr": pl.Float32}, orient="row")


@pytest.fixture(scope="module")
def spark():
    s = spark_session.get_spark("local", app_name="test-spark-satellite", cores=2,
                                shuffle_partitions=3)
    yield s
    s.stop()


@pytest.fixture()
def gee_dir(tmp_path, monkeypatch):
    """Thư mục Earth Engine giả: imerg chia 2 file tháng UTC như dữ liệu thật."""
    g = _imerg_grid()
    d = tmp_path / "gee" / "imerg"
    d.mkdir(parents=True)
    ym = pl.col("time_utc").dt.strftime("%Y%m")
    for (m,), part in g.with_columns(ym.alias("_m")).group_by(["_m"]):
        part.drop("_m").write_parquet(d / f"imerg_{m}.parquet")
    monkeypatch.setattr(hf, "GEE_DIR", tmp_path / "gee")
    return g


def _assert_identical(p: pl.DataFrame) -> None:
    s = sh.summarize(p)
    assert s["rows_only_one_side"] == 0
    assert s["null_mismatch"] == 0
    assert s["max_abs_diff"] == 0.0
    assert s["cells_not_bitwise_equal"] == 0


def _hadoop_modes() -> list[bool]:
    return [False, True] if spark_session.hadoop_io_ok() else [False]


@pytest.mark.parametrize("use_hadoop", _hadoop_modes())
def test_gop_nua_gio_imerg_trung_to_hourly(spark, gee_dir, use_hadoop):
    """read_source (lọc ô + to_hourly_spark) = hf.load_gee(hourly=True), từng ô từng giờ."""
    sdf = sh.read_source(spark, "imerg", WEIGHTS, use_hadoop=use_hadoop)
    got = sh.to_polars(sdf).sort("time", "lat", "lon")
    ref = hf.load_gee("imerg", cells=WEIGHTS)
    assert got.height == ref.height
    assert set(zip(got["lat"], got["lon"])) == {(a, b) for _, a, b, _ in WEIGHTS.iter_rows()}
    # khoá chuỗi: đưa về cùng đơn vị µs trước (file Earth Engine là ms, Spark trả µs)
    key = pl.concat_str([pl.col("time").dt.cast_time_unit("us").cast(pl.Utf8), "lat", "lon"],
                        separator="|")
    _assert_identical(sh.parity(ref.select(key.alias("k"), "precip"),
                                got.select(key.alias("k"), "precip"), "k"))
    # giờ kết thúc 12:00 = nửa giờ kết thúc 11:30 + nửa giờ kết thúc 12:00 (nhãn cuối khoảng)
    raw = gee_dir.filter((pl.col("lat") == 16.25) & (pl.col("lon") == 107.45))
    h = got.filter((pl.col("lat") == 16.25) & (pl.col("lon") == 107.45)
                   & (pl.col("time") == datetime(2020, 10, 1, 12)))["precip"].item()
    halves = raw.filter((pl.col("time") == datetime(2020, 10, 1, 11, 30))
                        | (pl.col("time") == datetime(2020, 10, 1, 12)))["precip_mm_hr"]
    assert halves.len() == 2
    assert h == float(halves.cast(pl.Float64).sum()) * 0.5
    # NaN ở nửa giờ kết thúc 15:30 → giờ kết thúc 16:00 của ô đó rỗng
    assert got.filter(pl.col("time") == datetime(2020, 10, 1, 16))["precip"].null_count() == 1


def test_pipeline_ve_tinh_trung_polars_tung_bit(spark, gee_dir):
    raw = hf.load_gee("imerg", cells=WEIGHTS)
    ref_h = hf.basin_hourly(raw, WEIGHTS, AREAS)
    ref_d = hf.daily_features(ref_h, [*AREAS, hf.WHOLE])
    sdf = sh.read_source(spark, "imerg", WEIGHTS, use_hadoop=False)
    hw, feats = sh.hourly_features_spark(spark, sdf, WEIGHTS, AREAS)
    got_h, got_d = sh.to_polars(hw), sh.to_polars(feats)
    assert got_d.columns == ref_d.columns
    assert got_d.height == N_DAYS + 1                     # nửa giờ 23:30 ngày cuối → 00h hôm sau
    _assert_identical(sh.parity(ref_h, got_h, "time"))
    _assert_identical(sh.parity(ref_d, got_d, "date"))
    d = {r["date"].day: r for r in got_d.iter_rows(named=True)}
    assert d[2]["hr_max1h_u3"] == 0.5                     # 0,5 mm/h × 0,5 h × 2 nửa
    assert d[2]["hr_peak_cos_u3"] == 1.0                  # đỉnh hoà 00–06h → giờ sớm nhất
    assert d[3]["hr_nh1mm_u1"] >= 3                       # 1 mm/h → đúng 1 mm/giờ
    assert d[4]["hr_sum_u3"] is None                      # thiếu 1 nửa giờ của ô u3 duy nhất
    assert d[4]["hr_sum_u4"] is not None                  # u4 chia lại trọng số cho ô còn lại


def test_danh_sach_file_giong_load_gee(tmp_path, monkeypatch):
    """gsmap_nrt: file tháng + ngày lẻ ``_parts/YYYYMMDD``, lọc tháng/năm theo tên file."""
    base = tmp_path / "gsmap_nrt"
    (base / "_parts").mkdir(parents=True)
    for n in ("gsmap_nrt_202008.parquet", "gsmap_nrt_202009.parquet",
              "gsmap_nrt_202109.parquet", "_parts/20210101.parquet", "_parts/20210102.parquet"):
        (base / n).write_bytes(b"")
    monkeypatch.setitem(hf.SAT_ROOT, "gsmap_nrt", tmp_path)
    names = [f.name for f in sh.gee_files("gsmap_nrt")]
    assert names == ["gsmap_nrt_202008.parquet", "gsmap_nrt_202009.parquet",
                     "gsmap_nrt_202109.parquet", "20210101.parquet", "20210102.parquet"]
    assert [f.name for f in sh.gee_files("gsmap_nrt", years=[2021])] == [
        "gsmap_nrt_202109.parquet", "20210101.parquet", "20210102.parquet"]
    assert [f.name for f in sh.gee_files("gsmap_nrt", months=["2020-09"])] == [
        "gsmap_nrt_202009.parquet"]
    with pytest.raises(FileNotFoundError):
        sh.gee_files("gsmap_nrt", years=[1999])


def test_to_hourly_spark_tu_choi_buoc_le(spark):
    with pytest.raises(ValueError):
        sh.to_hourly_spark(None, 45)


REAL_MONTH = "202010"


@pytest.mark.skipif(not (hf.GEE_DIR / "imerg" / f"imerg_{REAL_MONTH}.parquet").exists()
                    or not hf.WEIGHTS["imerg"].exists() or not hf.SUBBASIN_GEOJSON.exists(),
                    reason="không có file IMERG thật / bảng trọng số (data/** không commit)")
def test_mot_thang_imerg_that_trung_build_source(spark):
    """1 tháng IMERG thật (10/2020, lũ lớn) qua đường CLI: Spark = hf.build_source."""
    weights, areas, _ = hf.load_weights("imerg")
    sdf = sh.read_source(spark, "imerg", pl.read_csv(hf.WEIGHTS["imerg"]), use_hadoop=False,
                         months=[REAL_MONTH])
    hw, feats = sh.hourly_features_spark(spark, sdf, weights, areas)
    ref_h, ref_d, _ = hf.build_source("imerg", months=[REAL_MONTH])
    _assert_identical(sh.parity(ref_h, sh.to_polars(hw), "time"))
    _assert_identical(sh.parity(ref_d, sh.to_polars(feats), "date"))
