"""Mưa theo giờ có giúp mô hình ngày không? — ablation (Report 3).

Cùng LightGBM (tham số ``src/models/lgbm.py``), cùng hàng dữ liệu, chỉ khác bộ
cột:

    A    panel gốc               cột của daily_panel.parquet
    B0   + tổng ngày (đối chứng) A + hr_sum_basin, hr_r72h_basin — tổng ngày tính
                                 lại trên lưu vực DEM, KHÔNG có thông tin dưới ngày
    B    + giờ toàn lưu vực      A + 9 đặc trưng giờ của ``basin``
    C    + giờ lưu vực con       A + 9 × 5 đặc trưng giờ của 5 lưu vực con

B0 tách hai nguồn cải thiện có thể có của B: gộp không gian mới (lưu vực DEM thay
cho 3 dải vĩ độ) hay thông tin dưới ngày (cường độ, giờ đỉnh, 07h).

⚠️ SPLIT RIÊNG, KHÁC panel chính (train ≤ 2015-12-31): mưa ERA5 theo giờ chỉ có
từ 2015 nên dùng

    train 2015-01-01 → 2020-12-31 · valid 2021-01-01 → 2022-06-30 · test ≥ 2022-07-01

cho CẢ A/B0/B/C, và trên đúng một tập hàng (ngày có đủ mọi cột của mọi cấu hình).
Hai giai đoạn đánh giá: ``valid`` (fit trên train) và ``test`` (fit trên
train+valid, giống lgbm.py). Ngưỡng mức nguy cơ 1 lấy từ ``reports/risk_levels.csv``
(Q95 mùa lũ train+valid ≤ 2022-06-30 của panel chính) để so được với Report 2.
3 seed; chênh NSE < 0,01 (dao động giữa seed, xem ablation_ext.py) không tính là
cải thiện.

    python -m src.models.ablation_hourly
"""

from __future__ import annotations

import sys
from datetime import date

import numpy as np
import polars as pl

from src import config as cfg
from src.eval import metrics
from src.features import hourly_features as hf
from src.models import lgbm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = hf.OUT_PANEL
OUT = cfg.ROOT / "reports" / "ablation_hourly.csv"
RISK = cfg.ROOT / "reports" / "risk_levels.csv"
SEEDS = (42, 7, 2026)
MIN_GAIN = 0.01

SPLIT = {"train": (date(2015, 1, 1), date(2020, 12, 31)),
         "valid": (date(2021, 1, 1), date(2022, 6, 30)),
         "test": (date.fromisoformat(cfg.GLOFAS_REGIME_BREAK), date(2100, 1, 1))}
SPLIT_NOTE = ("ablation split 2015-01-01..2020-12-31 / 2021-01-01..2022-06-30 / >=2022-07-01 "
              "(khac panel chinh)")
N_BOOT, BLOCK = 1000, 30


def base_cols(panel: pl.DataFrame) -> list[str]:
    """Cột của panel gốc dùng làm feature (giống ``lgbm.feature_cols``, bỏ cột giờ)."""
    drop = {"date", "alert_level"}
    return [c for c, t in panel.schema.items()
            if c not in drop and not c.startswith("target_") and not c.startswith(hf.PREFIX)
            and t.is_numeric()]


def configs(panel: pl.DataFrame) -> dict[str, list[str]]:
    a = base_cols(panel)
    whole = hf.feature_names([hf.WHOLE])
    subs = [c for c in panel.columns if c.startswith(hf.PREFIX) and c not in whole]
    return {"A panel goc": a,
            "B0 +tong ngay (doi chung)": a + [f"{hf.PREFIX}sum_{hf.WHOLE}",
                                              f"{hf.PREFIX}r72h_{hf.WHOLE}"],
            "B +gio toan luu vuc": a + whole,
            "C +gio luu vuc con": a + subs}


def masks(panel: pl.DataFrame, feats: list[str], h: int,
          split: dict[str, tuple[date, date]] | None = None) -> dict[str, np.ndarray]:
    """Hàng dùng được cho horizon h — CHUNG cho mọi cấu hình. ``split`` mặc định
    :data:`SPLIT` (split riêng của ablation này)."""
    d = panel["date"].cast(pl.Date)
    ok = panel.select(pl.all_horizontal([pl.col(c).is_not_null() & pl.col(c).cast(pl.Float64).is_not_nan()
                                         for c in feats])
                      & pl.col(f"target_h{h}").is_not_null()).to_series().to_numpy()
    return {k: ok & (d >= lo).to_numpy() & (d <= hi).to_numpy()
            for k, (lo, hi) in (split or SPLIT).items()}


def fit_predict(X: np.ndarray, feats: list[str], y: np.ndarray, tr: np.ndarray,
                ev: np.ndarray, seed: int):
    """LightGBM trên log1p(Q), tham số của lgbm.py, chỉ đổi seed.

    Bắt buộc bọc pandas: LightGBM 4.5 gọi ``check_X_y(force_all_finite=...)`` với
    mảng numpy, tham số này đã bị bỏ ở scikit-learn 1.9 → TypeError. Đầu vào
    pandas đi đường khác (giống hệt lgbm.py).
    """
    import pandas as pd
    from lightgbm import LGBMRegressor

    model = LGBMRegressor(**{**lgbm.PARAMS, "random_state": seed})
    model.fit(pd.DataFrame(X[tr], columns=feats), np.log1p(y[tr]))
    yhat = model.predict(pd.DataFrame(X[ev], columns=feats))
    return np.clip(np.expm1(yhat), 0, None), model


def score(y: np.ndarray, yhat: np.ndarray, thr1: float) -> dict:
    rep = metrics.regression_report(y, yhat)
    ev = metrics.event_report(y >= thr1, yhat >= thr1)
    return {"NSE": rep["NSE"], "KGE": rep["KGE"], "RMSE": rep["RMSE"],
            "peak_bias": rep["peak_bias"], "POD1": ev["POD"], "FAR1": ev["FAR"],
            "CSI1": ev["CSI"], "n_pos1": ev["n_positive"]}


def block_boot_dnse(y, p_a, p_b, n: int = N_BOOT, block: int = BLOCK, seed: int = cfg.SEED):
    """Bootstrap khối (30 ngày) cho ΔNSE = NSE(b) − NSE(a) trên cùng các ngày."""
    rng = np.random.default_rng(seed)
    m = len(y)
    starts = np.arange(0, m - block + 1)
    k = int(np.ceil(m / block))
    out = np.empty(n)
    for i in range(n):
        idx = (rng.choice(starts, k)[:, None] + np.arange(block)).ravel()[:m]
        out[i] = metrics.nse(y[idx], p_b[idx]) - metrics.nse(y[idx], p_a[idx])
    return np.quantile(out, [0.025, 0.5, 0.975]), float(np.mean(out > 0))


def main() -> int:
    if not PANEL.exists():
        raise SystemExit("Chưa có daily_panel_hourly.parquet — chạy "
                         "`python -m src.features.hourly_features --source era5` trước.")
    panel = pl.read_parquet(PANEL).sort("date")
    thr1 = float(pl.read_csv(RISK).filter(pl.col("muc") == "nguy_co_1")["nguong_m3s"].item())
    cfgs = configs(panel)
    union = sorted({c for f in cfgs.values() for c in f})
    print(f"Split RIÊNG cho ablation: {SPLIT_NOTE}")
    print(f"Ngưỡng mức nguy cơ 1 = {thr1:.1f} m³/s (reports/risk_levels.csv)")
    for k, f in cfgs.items():
        print(f"  {k:<28} {len(f):3d} feature")

    rows, preds, imps = [], {}, []
    for h in cfg.HORIZONS:
        m = masks(panel, union, h)
        y = panel[f"target_h{h}"].to_numpy().astype(float)
        q0 = panel["discharge"].to_numpy().astype(float)
        print(f"\nh={h}: train {m['train'].sum()} · valid {m['valid'].sum()} · "
              f"test {m['test'].sum()} ngày", flush=True)
        phases = {"valid": (m["train"], m["valid"]),
                  "test": (m["train"] | m["valid"], m["test"])}
        for ph, (tr, ev) in phases.items():
            rows.append({"config": "persistence", "phase": ph, "horizon": h, "seed": None,
                         "n_train": 0, "n_eval": int(ev.sum()), "n_feat": 1,
                         **score(y[ev], q0[ev], thr1)})
            for name, feats in cfgs.items():
                X = panel.select(feats).to_numpy().astype(float)
                for seed in SEEDS:
                    yhat, model = fit_predict(X, feats, y, tr, ev, seed)
                    rows.append({"config": name, "phase": ph, "horizon": h, "seed": seed,
                                 "n_train": int(tr.sum()), "n_eval": int(ev.sum()),
                                 "n_feat": len(feats), **score(y[ev], yhat, thr1)})
                    preds.setdefault((name, ph, h), []).append(yhat)
                    if ph == "test" and name.startswith("C") and seed == cfg.SEED:
                        g = model.booster_.feature_importance("gain")
                        imps += [(h, f, float(v)) for f, v in zip(feats, g)]
            preds[("_y", ph, h)] = [y[ev]]

    res = pl.DataFrame(rows).with_columns(pl.lit(SPLIT_NOTE).alias("split"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.write_csv(OUT)

    agg = (res.group_by("config", "phase", "horizon", maintain_order=True)
              .agg(pl.col("NSE").mean().alias("NSE"), pl.col("NSE").std().alias("NSE_sd"),
                   pl.col("KGE").mean().alias("KGE"),
                   pl.col("peak_bias").mean().alias("peak_bias"),
                   pl.col("POD1").mean().alias("POD1"), pl.col("FAR1").mean().alias("FAR1"),
                   pl.col("CSI1").mean().alias("CSI1"), pl.col("n_pos1").first().alias("n_pos1"),
                   pl.col("n_eval").first().alias("n"))
              .sort("phase", "horizon", "config"))
    with pl.Config(tbl_rows=80, tbl_cols=20, float_precision=3, tbl_width_chars=200):
        print("\nTrung bình 3 seed:")
        print(agg)

    print(f"\nΔNSE so với A (trung bình 3 seed; |Δ| < {MIN_GAIN} = không đổi) "
          f"+ bootstrap khối {BLOCK} ngày ({N_BOOT} lần) trên dự báo trung bình 3 seed:")
    for ph in ("valid", "test"):
        for h in cfg.HORIZONS:
            y = preds[("_y", ph, h)][0]
            pa = np.mean(preds[("A panel goc", ph, h)], axis=0)
            na = metrics.nse(y, pa)
            for name in list(cfgs)[1:]:
                pb = np.mean(preds[(name, ph, h)], axis=0)
                d = (agg.filter((pl.col("config") == name) & (pl.col("phase") == ph)
                                & (pl.col("horizon") == h))["NSE"].item()
                     - agg.filter((pl.col("config") == "A panel goc") & (pl.col("phase") == ph)
                                  & (pl.col("horizon") == h))["NSE"].item())
                ci, p_pos = block_boot_dnse(y, pa, pb)
                verdict = ("tốt hơn" if d >= MIN_GAIN else "kém hơn" if d <= -MIN_GAIN
                           else "không đổi")
                print(f"  {ph:5} h={h} {name:<28} ΔNSE {d:+.3f} ({verdict}); "
                      f"NSE ens {metrics.nse(y, pb):.3f} vs A {na:.3f}; "
                      f"CI95 Δ [{ci[0]:+.3f}, {ci[2]:+.3f}], P(Δ>0) {p_pos:.2f}")

    if imps:
        imp = pl.DataFrame(imps, schema=["horizon", "feature", "gain"], orient="row")
        tot = imp.group_by("horizon").agg(pl.col("gain").sum().alias("tot"))
        imp = imp.join(tot, on="horizon").with_columns((pl.col("gain") / pl.col("tot")).alias("share"))
        print("\nC (test, seed 42): tỷ trọng gain của nhóm cột giờ và 5 cột giờ mạnh nhất:")
        for h in cfg.HORIZONS:
            s = imp.filter((pl.col("horizon") == h) & pl.col("feature").str.starts_with(hf.PREFIX))
            top = s.sort("share", descending=True).head(5)
            print(f"  h={h}: cột giờ chiếm {s['share'].sum():.1%} gain; "
                  + ", ".join(f"{r['feature']} {r['share']:.1%}" for r in top.iter_rows(named=True)))

    print(f"\n→ {OUT.relative_to(cfg.ROOT)} ({res.height} dòng)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
