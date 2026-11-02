"""Dự báo LightGBM trực tuyến cho job hằng ngày (Report 4, AC-3 / FR-P4).

Job ``predict_daily`` mới chỉ ghi GloFAS thô. File này thêm dự báo của mô hình chính
(cấu hình E, 88 cột, ``lgbm.params_for``) cho ngày phát báo t = hôm nay:

1. **Huấn luyện** (``--train``, chạy tay sau khi đóng băng mô hình): học trên MỌI hàng
   của ``daily_panel_ext.parquet`` có nhãn, 3 seed × 3 horizon, lưu LightGBM dạng văn
   bản vào ``models/`` (+ ``lgbm_live_meta.json``: cột, seed, khoảng dữ liệu).
   Phát hành lên GitHub release để job trên Actions tải về (``models/`` bị gitignore).
   Kèm bộ phân loại mức nguy cơ 1 (h=1, tham số ``classifier.PARAMS``) và hàm hiệu chỉnh
   isotonic fit trên xác suất ngoài mẫu ``reports/cost_oof_E_level1_h1.parquet``
   (walk-forward 1999–2025 của ``cost_threshold --calibrate``, FR-M6) ⇒ cột ``p_level1``.
   Ngưỡng báo = 1/(1+R) = 1/11 trên xác suất đã hiệu chỉnh (chi phí 10:1, cùng chi phí
   với ngưỡng chọn hằng năm, ``FINDINGS_COST_THRESHOLD.md`` §8).
2. **Dự báo** (``predict``): lấy ~130 ngày gần nhất từ API, dựng ĐÚNG các cột như panel
   lịch sử bằng ``build_panel.add_features`` / ``join_context`` (cùng mã, không viết lại).

Nguồn dữ liệu trực tuyến KHÁC panel huấn luyện — ghi rõ để không ai đọc nhầm:

* lưu lượng: Flood API (GloFAS), giá trị ngày t là bản dự báo gần nhất;
* mưa/khí tượng: ERA5 qua Archive API tới t−6 (ERA5 trễ ~5 ngày); t−5 … t lấy từ
  Forecast API (phân tích/dự báo NWP) — riêng mưa ngày t là **mưa dự báo** cả ngày,
  tức kịch bản B (nhiễu σ = 1 làm NSE h1 giảm ~0,06, ``FINDINGS_MODEL.md``);
* độ ẩm đất ERA5-Land: tới t−6 rồi giữ nguyên giá trị cuối (biến chậm);
* bão: IBTrACS ACTIVE; tải lỗi thì coi như không có bão (2 000 km) và ghi cờ;
* ONI: NOAA CPC, trễ 3 tháng như panel.

    python -m src.models.predict_live --train      # huấn luyện + lưu models/
    python -m src.models.predict_live              # in dự báo hôm nay (không ghi file)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

import numpy as np
import polars as pl

from src import config as cfg

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODELS = cfg.ROOT / "models"
META = MODELS / "lgbm_live_meta.json"
CLF = MODELS / "lgbm_live_clf_level1_h1.txt"
ISO = MODELS / "lgbm_live_iso_level1_h1.json"
OOF = cfg.ROOT / "reports" / "cost_oof_E_level1_h1.parquet"
SEEDS = (42, 7, 2026)
LOOKBACK_DAYS = 130          # đủ mưa từ 01/09 (rain_season_cum) tới cuối tháng 12, roll30, lag14
ARCHIVE_LAG_DAYS = 6         # ERA5 trên Archive API trễ ~5 ngày
STORM_ACTIVE_URL = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-"
                    "climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.ACTIVE.list.v04r01.csv")


def model_path(h: int, seed: int):
    return MODELS / f"lgbm_live_h{h}_s{seed}.txt"


# ================================================================ huấn luyện

def train() -> dict:
    """Học trên toàn bộ panel có nhãn; trả meta đã ghi."""
    import pandas as pd
    from lightgbm import LGBMRegressor

    from src.eval.wf_tuning import e_features
    from src.models import ablation_hourly as ab
    from src.models import ablation_sat as sa
    from src.models import lgbm

    panel = pl.read_parquet(sa.PANEL_EXT).sort("date")
    feats = e_features()
    d = panel["date"].cast(pl.Date)
    split = {"train": (sa.EXT_START, d.max())}
    MODELS.mkdir(parents=True, exist_ok=True)
    X = panel.select(feats).to_numpy().astype(float)
    n_rows = {}
    for h in cfg.HORIZONS:
        tr = ab.masks(panel, feats, h, split)["train"]
        y = panel[f"target_h{h}"].to_numpy().astype(float)
        n_rows[h] = int(tr.sum())
        for s in SEEDS:
            m = LGBMRegressor(**lgbm.params_for(h, random_state=s))
            m.fit(pd.DataFrame(X[tr], columns=feats), np.log1p(y[tr]))
            m.booster_.save_model(str(model_path(h, s)))
            print(f"  h{h} seed {s}: {n_rows[h]} hàng → {model_path(h, s).name}", flush=True)
    meta = {"features": feats, "seeds": list(SEEDS), "horizons": list(cfg.HORIZONS),
            "objective": {h: lgbm.MAIN_OBJECTIVE[h] for h in cfg.HORIZONS},
            "train_start": str(sa.EXT_START), "train_end": str(d.max()), "n_rows": n_rows,
            "config": "E", "classifier": train_classifier(feats)}
    META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def train_classifier(feats: list[str]) -> dict:
    """Bộ phân loại ``Q(t+1) ≥ mức 1`` trên toàn panel + isotonic từ OOF (lưu nút dạng
    JSON để job trên Actions áp bằng ``np.interp``, không cần scikit-learn)."""
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.isotonic import IsotonicRegression

    from src.models import ablation_hourly as ab
    from src.models import ablation_sat as sa
    from src.models import classifier as clf
    from src.models.predict_daily import risk_thresholds

    thr = risk_thresholds()["nguy_co_1"]
    panel = pl.read_parquet(sa.PANEL_EXT).sort("date")
    tr = ab.masks(panel, feats, 1, {"train": (sa.EXT_START, panel["date"].cast(pl.Date).max())})["train"]
    y = (panel["target_h1"].to_numpy().astype(float) >= thr)[tr].astype("int8")
    w = float((len(y) - y.sum()) / max(int(y.sum()), 1))
    m = LGBMClassifier(**{**clf.PARAMS, "random_state": cfg.SEED}, scale_pos_weight=w)
    m.fit(pd.DataFrame(panel.select(feats).to_numpy().astype(float)[tr], columns=feats), pd.Series(y))
    m.booster_.save_model(str(CLF))
    oof = pl.read_parquet(OOF)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1, increasing=True)
    iso.fit(oof["p"].to_numpy(), oof["y"].cast(pl.Int8).to_numpy())
    knots = {"x": iso.X_thresholds_.tolist(), "y": iso.y_thresholds_.tolist(),
             "threshold": 1 / (1 + cfg.COST_RATIO_MISS_TO_FALSE_ALARM), "level_m3s": thr,
             "oof_years": [int(oof["year"].min()), int(oof["year"].max())],
             "oof_n": oof.height, "oof_pos": int(oof["y"].sum()), "scale_pos_weight": w}
    ISO.write_text(json.dumps(knots, indent=2), encoding="utf-8")
    print(f"  phân loại mức 1 (≥ {thr:.0f} m³/s): {len(y)} hàng, {int(y.sum())} dương → {CLF.name}")
    return knots


def calibrate(p_raw: float) -> float:
    k = json.loads(ISO.read_text(encoding="utf-8"))
    return float(np.interp(p_raw, k["x"], k["y"]))      # = IsotonicRegression(clip).predict


def models_ready() -> bool:
    if not META.exists():
        return False
    meta = json.loads(META.read_text(encoding="utf-8"))
    return all(model_path(h, s).exists() for h in meta["horizons"] for s in meta["seeds"])


# ================================================================ lấy dữ liệu

def _get(url: str, params: dict):
    from src.models.predict_daily import _get as get  # retry luỹ thừa có sẵn
    return get(url, params)


def _multi(url: str, points: list[tuple[float, float]], daily: str, start: date, end: date
           ) -> pl.DataFrame:
    """Nhiều điểm trong MỘT lần gọi (Open-Meteo nhận danh sách toạ độ)."""
    js = _get(url, {"latitude": ",".join(str(a) for a, _ in points),
                    "longitude": ",".join(str(o) for _, o in points),
                    "daily": daily, "start_date": str(start), "end_date": str(end),
                    "timezone": cfg.TIMEZONE})
    js = js if isinstance(js, list) else [js]
    frames = []
    for (la, lo), j in zip(points, js):
        d = j["daily"]
        frames.append(pl.DataFrame(d).with_columns(
            pl.col("time").str.to_datetime("%Y-%m-%d").alias("date"),
            pl.lit(la).alias("lat"), pl.lit(lo).alias("lon")).drop("time"))
    return pl.concat(frames, how="vertical_relaxed")


def _archive_then_forecast(points, daily: str, t: date) -> pl.DataFrame:
    """ERA5 (Archive) tới t−6, phần còn lại tới t từ Forecast API; trùng ngày ưu tiên ERA5."""
    start = t - timedelta(days=LOOKBACK_DAYS)
    cut = t - timedelta(days=ARCHIVE_LAG_DAYS)
    arc = _multi(cfg.ARCHIVE_API, points, daily, start, cut)
    fc = _multi(cfg.FORECAST_API, points, daily, cut - timedelta(days=2), t)
    vals = [c for c in arc.columns if c not in ("date", "lat", "lon")]
    arc = arc.filter(pl.any_horizontal(pl.col(vals).is_not_null()))
    fc = fc.join(arc.select("date", "lat", "lon"), on=["date", "lat", "lon"], how="anti")
    return pl.concat([arc, fc.select(arc.columns)], how="vertical_relaxed").sort("lat", "lon", "date")


def fetch_discharge(t: date) -> pl.DataFrame:
    lat, lon = cfg.RIVER_POINTS["huong_kim_long"]
    d = _get(cfg.FLOOD_API, {"latitude": lat, "longitude": lon, "daily": "river_discharge",
                             "start_date": str(t - timedelta(days=LOOKBACK_DAYS)),
                             "end_date": str(t)})["daily"]
    return pl.DataFrame({"date": d["time"], "discharge": d["river_discharge"]}).with_columns(
        pl.col("date").str.to_datetime("%Y-%m-%d"), pl.col("discharge").cast(pl.Float64))


def fetch_rain(t: date) -> pl.DataFrame:
    from src.ingest import crawl_all as ca
    pts = ca._grid(ca.RAIN_BOX, ca.RAIN_STEP)
    r = _archive_then_forecast(pts, "precipitation_sum", t)
    return r.rename({"precipitation_sum": "rain"})


def fetch_soil(t: date) -> pl.DataFrame:
    from src.ingest import crawl_all as ca
    from src.ingest import crawl_extend as ce
    pts = ca._grid(ca.RAIN_BOX, ce.SOIL_STEP)
    s = _multi(cfg.ARCHIVE_API, pts, ce.SOIL_DAILY_VARS, t - timedelta(days=LOOKBACK_DAYS), t)
    s = (s.group_by("date").agg(pl.col("soil_moisture_0_to_7cm_mean").mean().alias("sm_0_7"),
                                pl.col("soil_moisture_7_to_28cm_mean").mean().alias("sm_7_28"),
                                pl.col("soil_moisture_28_to_100cm_mean").mean().alias("sm_28_100"),
                                pl.col("et0_fao_evapotranspiration").mean().alias("et0"))
          .sort("date"))
    # Archive chưa có mấy ngày cuối → giữ giá trị gần nhất (độ ẩm đất biến chậm)
    return s.with_columns(pl.col("sm_0_7", "sm_7_28", "sm_28_100", "et0").forward_fill())


def fetch_met(t: date) -> pl.DataFrame:
    from src.ingest import crawl_extend as ce
    names = list(ce.MET_POINTS)
    m = _archive_then_forecast([ce.MET_POINTS[n] for n in names], ce.MET_DAILY_VARS, t)
    m = m.join(pl.DataFrame({"lat": [ce.MET_POINTS[n][0] for n in names],
                             "lon": [ce.MET_POINTS[n][1] for n in names], "point": names}),
               on=["lat", "lon"], how="left")
    m = m.select("date", "point",
                 pl.col("pressure_msl_mean").alias("mslp"),
                 pl.col("wind_direction_10m_dominant").alias("wind_dir"),
                 pl.col("wind_speed_10m_mean").alias("wind_speed"),
                 pl.col("relative_humidity_2m_mean").alias("rh"),
                 pl.col("cloud_cover_mean").alias("cloud"))
    return m.pivot(on="point", index="date", values=["mslp", "wind_dir", "wind_speed", "rh", "cloud"],
                   separator="_").sort("date")


def fetch_storm(t: date) -> tuple[pl.DataFrame, bool]:
    """(bảng bão theo ngày như ``clean.load_storm_daily``, tải được hay không)."""
    import io

    import requests

    from src.ingest import external_indices as ei
    empty = pl.DataFrame(schema={"date": pl.Datetime, "storm_dist_km": pl.Float64,
                                 "storm_wind_kt": pl.Float64})
    try:
        r = requests.get(STORM_ACTIVE_URL, timeout=60)
        r.raise_for_status()
        d = pl.read_csv(io.BytesIO(r.content), skip_rows_after_header=1, infer_schema_length=0,
                        columns=["ISO_TIME", "LAT", "LON", "WMO_WIND", "USA_WIND"])
    except Exception as e:                            # noqa: BLE001 — bão là biến phụ
        print(f"  ! không tải được IBTrACS ACTIVE ({e}) — coi như không có bão", flush=True)
        return empty, False
    num = lambda c: pl.col(c).str.strip_chars().cast(pl.Float64, strict=False)  # noqa: E731
    d = (d.with_columns(lat=num("LAT"), lon=num("LON"),
                        wind_kt=pl.coalesce(num("WMO_WIND"), num("USA_WIND")),
                        time_utc=pl.col("ISO_TIME").str.to_datetime("%Y-%m-%d %H:%M:%S"))
          .with_columns(dist_km=ei.haversine_km(pl.col("lat"), pl.col("lon"), *ei.HUE))
          .filter(pl.col("dist_km") <= ei.STORM_RADIUS_KM)
          .with_columns(date=(pl.col("time_utc") + pl.duration(hours=7)).dt.date().cast(pl.Datetime)))
    if d.is_empty():
        return empty, True
    return (d.group_by("date").agg(pl.col("dist_km").min().alias("storm_dist_km"),
                                   pl.col("wind_kt").filter(pl.col("dist_km") <= 1000).max()
                                   .alias("storm_wind_kt"))
             .sort("date")), True


# ================================================================ dựng hàng & dự báo

def live_features(t: date) -> tuple[pl.DataFrame, dict]:
    """Hàng đặc trưng của ngày t (đúng 88 cột E) + thông tin nguồn."""
    from src.features import build_panel as bp
    from src.ingest import external_indices as ei

    q = fetch_discharge(t)
    rain_agg = bp.aggregate_rain(fetch_rain(t))
    storm, storm_ok = fetch_storm(t)
    df = (q.join(rain_agg, on="date", how="inner").sort("date")
           .join(fetch_soil(t), on="date", how="left"))
    df = bp.join_context(df, met=fetch_met(t), storm=storm, oni=ei.fetch_oni())
    df = bp.add_features(df, ext=True)
    row = df.filter(pl.col("date").dt.date() == t)
    info = {"storm_ok": storm_ok, "n_days": df.height}
    return row, info


def predict(t: date) -> dict:
    """{h: Q dự báo m³/s} cho ngày phát báo t, + 'info'. Thiếu mô hình → {}."""
    import lightgbm as lgb

    if not models_ready():
        return {}
    meta = json.loads(META.read_text(encoding="utf-8"))
    row, info = live_features(t)
    if row.is_empty():
        raise RuntimeError(f"Không dựng được hàng đặc trưng cho {t}")
    x = row.select(meta["features"]).to_numpy().astype(float)
    missing = [c for c, v in zip(meta["features"], x[0]) if not np.isfinite(v)]
    out = {"info": {**info, "missing": missing}}
    for h in meta["horizons"]:
        ps = [lgb.Booster(model_file=str(model_path(h, s))).predict(x)[0] for s in meta["seeds"]]
        out[int(h)] = float(np.clip(np.expm1(np.mean(ps)), 0, None))
    if CLF.exists() and ISO.exists():
        p_raw = float(lgb.Booster(model_file=str(CLF)).predict(x)[0])
        out["p_level1"] = calibrate(p_raw)
        out["p_level1_raw"] = p_raw
        out["p_threshold"] = json.loads(ISO.read_text(encoding="utf-8"))["threshold"]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--date", default=None, help="ngày phát báo (mặc định hôm nay giờ VN)")
    a = ap.parse_args(argv)
    if a.train:
        meta = train()
        print(f"→ {META} (train {meta['train_start']} → {meta['train_end']})")
        return 0
    from src.models.predict_daily import ict_today
    t = date.fromisoformat(a.date) if a.date else ict_today()
    print(json.dumps(predict(t), indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
