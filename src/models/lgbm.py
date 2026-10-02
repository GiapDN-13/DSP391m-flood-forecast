"""LightGBM hồi quy lưu lượng 1–3 ngày (FR-M2).

Mốc phải vượt là **persistence**, không phải số 0. Persistence đã đạt
NSE 0,542 ở h=1 nên gần như không thể thắng ở đó; cơ hội thật nằm ở **h=2 và
h=3**, nơi persistence sụp xuống 0,008 và −0,198 (`reports/baseline_results.csv`).

Ba quyết định thiết kế, đều rút ra từ EDA (`reports/eda_summary.csv`):

1. **Học trên `log1p(Q)`.** Phân bố lưu lượng lệch rất mạnh (hệ số bất đối xứng
   5,91); học thẳng trên m³/s thì hàm mất mát bị vài ngày lũ chi phối.
2. **Ưu tiên mưa tích luỹ hơn mưa một ngày.** EDA §4: r(mưa 3 ngày, Q) = 0,863
   so với r(mưa 1 ngày, Q) = 0,642.
3. **Giữ chỉ số ẩm nền API.** EDA §4: cùng một trận mưa lớn, nền ẩm cho lưu
   lượng gấp **6,9 lần** nền khô.

Chia tập y hệt `baselines.py` (`regime_split`) để bảng so sánh công bằng: train
≤ 2015-12-31, valid tới 2022-06-30, test từ 2022-07-01.

    python -m src.models.lgbm
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src import config as cfg
from src.eval import metrics, walk_forward

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
OUT = cfg.ROOT / "reports" / "lgbm_results.csv"
IMP = cfg.ROOT / "reports" / "lgbm_importance.csv"
BASE = cfg.ROOT / "reports" / "baseline_results.csv"

PARAMS = dict(
    objective="regression_l1",   # L1 bền với ngày lũ cực trị hơn L2
    n_estimators=600,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=30,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    random_state=cfg.SEED,
    verbose=-1,
)


def feature_cols(panel: pd.DataFrame) -> list[str]:
    """Mọi cột dùng được làm feature.

    Loại `date`, các cột `target_*` và `alert_level`. Không có cột nào chứa
    thông tin tương lai: panel chỉ chứa lag và cửa sổ trượt lùi về sau
    (`tests/test_no_leakage.py` khoá điều này).
    """
    # alert_level / risk_level là NHÃN, không bao giờ là feature.
    drop = {"date", "alert_level", "risk_level"} | {c for c in panel.columns if c.startswith("target_")}
    return [c for c in panel.columns if c not in drop
            and pd.api.types.is_numeric_dtype(panel[c])]


def fit_predict(panel: pd.DataFrame, h: int, feats: list[str],
                tr: pd.Series, te: pd.Series):
    """Huấn luyện một mô hình cho một horizon, trả về (y thật, y dự báo, model)."""
    from lightgbm import LGBMRegressor

    y = panel[f"target_h{h}"]
    ok_tr = tr & y.notna() & panel[feats].notna().all(axis=1)
    ok_te = te & y.notna() & panel[feats].notna().all(axis=1)

    model = LGBMRegressor(**PARAMS)
    model.fit(panel.loc[ok_tr, feats], np.log1p(y[ok_tr]))

    yhat = np.expm1(model.predict(panel.loc[ok_te, feats]))
    yhat = np.clip(yhat, 0, None)          # lưu lượng âm là vô nghĩa
    return y[ok_te].to_numpy(float), yhat, model, int(ok_tr.sum())


def main() -> int:
    panel = pd.read_parquet(PANEL)
    panel["date"] = pd.to_datetime(panel["date"])
    split = walk_forward.regime_split(pd.DatetimeIndex(panel["date"]))

    tr = panel["date"].isin(split["train"]) | panel["date"].isin(split["valid"])
    te = panel["date"].isin(split["test"])
    feats = feature_cols(panel)

    print(f"Train+valid: {int(tr.sum()):,} ngày · Test: {int(te.sum()):,} ngày"
          .replace(",", " "))
    print(f"Test từ {panel.loc[te, 'date'].min():%Y-%m-%d} "
          f"đến {panel.loc[te, 'date'].max():%Y-%m-%d}")
    print(f"Số feature: {len(feats)}\n")

    base = pd.read_csv(BASE)
    rows, imps = [], []

    for h in cfg.HORIZONS:
        y, yhat, model, n_tr = fit_predict(panel, h, feats, tr, te)
        rep = metrics.regression_report(y, yhat)
        rep.update({"model": "lightgbm", "horizon": h, "n": len(y)})
        rows.append(rep)

        b = base[(base.model == "persistence") & (base.horizon == h)].iloc[0]
        dn = rep["NSE"] - b["NSE"]
        print(f"h={h}:  NSE {rep['NSE']:+.3f}  (persistence {b['NSE']:+.3f}, "
              f"chênh {dn:+.3f})  RMSE {rep['RMSE']:.1f} vs {b['RMSE']:.1f}  "
              f"{'✅ THẮNG' if dn > 0 else '❌ THUA'}")

        gain = pd.DataFrame({"feature": feats, "gain": model.feature_importances_})
        gain["horizon"] = h
        imps.append(gain.sort_values("gain", ascending=False))

    res = pd.DataFrame(rows)[["model", "horizon", "RMSE", "MAE", "NSE", "KGE",
                              "peak_bias", "n"]]
    res.to_csv(OUT, index=False)
    imp = pd.concat(imps, ignore_index=True)
    imp.to_csv(IMP, index=False)

    print("\nKết quả LightGBM:")
    print(res.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    print("\n10 feature quan trọng nhất (h=2):")
    top = imp[imp.horizon == 2].nlargest(10, "gain")
    for _, r in top.iterrows():
        print(f"    {r.feature:<24} {r.gain:>8.0f}")

    print(f"\n→ {OUT.relative_to(cfg.ROOT)}")
    print(f"→ {IMP.relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
