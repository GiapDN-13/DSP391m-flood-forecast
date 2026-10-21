"""Dữ liệu mở rộng có giúp mô hình không? — thử từng bước một (Report 3).

Năm cấu hình, mỗi bước chỉ thêm MỘT nhóm để biết nhóm nào có tác dụng:

    A  Report 2           panel từ 2010, feature cũ
    B  + mưa 1997–2009    cùng feature, thêm 12 năm huấn luyện
    C  + độ ẩm đất        B + ERA5-Land 3 tầng + ET₀
    D  + đại diện hồ chứa C + mưa 15/30 ngày + mưa tích luỹ từ 01/09
    E  + bão, KK lạnh, ENSO D + IBTrACS + khí áp/gió 3 điểm + ONI trễ 3 tháng

Hàm mất mát: CẢ NĂM cấu hình dùng cùng quy tắc của mô hình chính
``lgbm.params_for(h)`` — L1 ở h=1, L2 (``regression``) ở h=2 và h=3 (chọn bằng
walk-forward/valid, ``docs/FINDINGS_TUNING.md``). Chỉ bộ cột khác nhau giữa
các cấu hình nên phép so đặc trưng vẫn công bằng. Cột ``objective`` ghi hàm mất
mát đã dùng. Bản cũ (L1 mọi horizon, trước 21/10/2026) giữ ở
``reports/l1_ref/ablation_ext.csv``.

Tập test GIỐNG HỆT nhau (từ 2022-07-01), ngưỡng nguy cơ giữ nguyên của
Report 2 (`reports/risk_levels.csv`) để so sánh công bằng. Mỗi cấu hình chạy 3
seed vì LightGBM dao động ±0,01 NSE giữa các seed — chênh nhỏ hơn mức đó
không được coi là cải thiện.

    python -m src.models.ablation_ext
"""

from __future__ import annotations

import sys

import pandas as pd

from src import config as cfg
from src.eval import metrics, walk_forward
from src.models import lgbm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.DATA_PROCESSED / "daily_panel.parquet"
PANEL_EXT = cfg.DATA_PROCESSED / "daily_panel_ext.parquet"
OUT = cfg.ROOT / "reports" / "ablation_ext.csv"
SEEDS = (42, 7, 2026)

SOIL = ["sm_0_7", "sm_7_28", "sm_28_100", "et0"]
RESERVOIR_PROXY = ["rain_basin_roll15", "rain_basin_roll30", "rain_season_cum"]
CONTEXT = ["storm_dist_km", "storm_wind_kt", "storm_approach_km",
           "mslp_hue", "mslp_north", "mslp_sea", "mslp_grad_north", "mslp_hue_d1",
           "wind_ne_hue", "wind_e_sea", "wind_speed_hue", "wind_speed_sea",
           "rh_hue", "cloud_hue", "oni_lag3"]


def _load(path) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    p = pd.read_parquet(path)
    p["date"] = pd.to_datetime(p["date"])
    s = walk_forward.regime_split(pd.DatetimeIndex(p["date"]))
    tr = p["date"].isin(s["train"]) | p["date"].isin(s["valid"])
    te = p["date"].isin(s["test"])
    return p, tr, te


def run(name: str, panel, tr, te, feats, thr1: float) -> list[dict]:
    rows = []
    for h in cfg.HORIZONS:
        for seed in SEEDS:
            params = lgbm.params_for(h, random_state=seed)
            y, yhat, _, n_tr = lgbm.fit_predict(panel, h, feats, tr, te, params)
            rep = metrics.regression_report(y, yhat)
            ev = metrics.event_report(y >= thr1, yhat >= thr1)
            rows.append({"config": name, "horizon": h, "seed": seed,
                         "objective": params["objective"],
                         "n_train": n_tr, "n_test": len(y), "n_feat": len(feats),
                         "NSE": rep["NSE"], "KGE": rep["KGE"],
                         "peak_bias": rep["peak_bias"],
                         "POD1": ev["POD"], "FAR1": ev["FAR"], "CSI1": ev["CSI"]})
    return rows


def main() -> int:
    thr1 = float(pd.read_csv(cfg.ROOT / "reports" / "risk_levels.csv")
                 .set_index("muc").loc["nguy_co_1", "nguong_m3s"])
    p2, tr2, te2 = _load(PANEL)
    p3, tr3, te3 = _load(PANEL_EXT)
    base = lgbm.feature_cols(p2)

    configs = [
        ("A Report 2", p2, tr2, te2, base),
        ("B +rain 1997", p3, tr3, te3, base),
        ("C +soil", p3, tr3, te3, base + SOIL),
        ("D +reservoir proxy", p3, tr3, te3, base + SOIL + RESERVOIR_PROXY),
        ("E +storm/monsoon/ENSO", p3, tr3, te3, base + SOIL + RESERVOIR_PROXY + CONTEXT),
    ]
    rows = []
    for name, p, tr, te, feats in configs:
        print(f"… {name}: {len(feats)} feature, train {int(tr.sum())} ngày", flush=True)
        rows += run(name, p, tr, te, feats, thr1)

    res = pd.DataFrame(rows)
    res.to_csv(OUT, index=False)
    agg = (res.groupby(["config", "horizon"])
              .agg(NSE=("NSE", "mean"), NSE_sd=("NSE", "std"),
                   peak_bias=("peak_bias", "mean"), POD1=("POD1", "mean"),
                   FAR1=("FAR1", "mean"), n_train=("n_train", "first"),
                   n_test=("n_test", "first"))
              .reset_index())
    print("\nTrung bình 3 seed (test từ 2022-07-01):")
    print(agg.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    piv = agg.pivot(index="config", columns="horizon", values="NSE")
    print("\nNSE theo horizon:")
    print(piv.to_string(float_format=lambda v: f"{v:.3f}"))
    print(f"\n→ {OUT.relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
