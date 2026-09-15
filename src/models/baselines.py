"""Các mô hình tham chiếu (FR-M1).

Baseline không phải thủ tục cho có: nếu LightGBM không thắng nổi persistence
thì dự án không có giá trị gì, và tốt nhất là biết điều đó từ W5 chứ không
phải lúc vấn đáp.

    python -m src.models.baselines

## ⚠️ Về baseline "GloFAS thô"

Kế hoạch dự kiến so trực tiếp với **dự báo GloFAS ở cùng hạn dự báo**. Ngày
15/09/2026 đã kiểm: Open-Meteo **không có endpoint lưu trữ dự báo GloFAS quá
khứ** (`historical-forecast-api.open-meteo.com/v1/flood` → 404). Chuỗi lịch sử
của Flood API là giá trị phân tích của mô hình, **không phải bản dự báo đã phát
trước đó mấy ngày**.

Hệ quả: baseline này **không dựng lại được từ quá khứ**, chỉ tích luỹ tiến về
phía trước qua `reports/forecast_log/` (job chạy hằng ngày từ W1). Xem
`docs/FINDINGS_FORECAST.md`.

Thay thế trong lúc chờ: `persistence_glofas` — lấy chính giá trị GloFAS hôm nay
làm dự báo cho ngày t+h. Đây **không phải** dự báo GloFAS thật, mà là cận dưới
của nó; ghi rõ như vậy trong báo cáo.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src import config as cfg
from src.eval import metrics, walk_forward


def persistence(df: pd.DataFrame, horizon: int, col: str = "discharge") -> pd.Series:
    """Dự báo = giá trị hôm nay. Baseline khó thắng nhất với chuỗi trơn."""
    return df[col].copy()


def seasonal_naive(df: pd.DataFrame, horizon: int, col: str = "discharge",
                   period: int = 365) -> pd.Series:
    """Dự báo = giá trị cùng ngày năm ngoái."""
    return df[col].shift(period - horizon)


def climatology(df: pd.DataFrame, horizon: int, col: str = "discharge",
                train_mask: pd.Series | None = None) -> pd.Series:
    """Dự báo = trung bình nhiều năm của ngày đó trong năm.

    Trung bình CHỈ được tính trên phần train, nếu không là rò rỉ.
    """
    d = df.copy()
    d["doy"] = d["date"].dt.dayofyear
    src = d[train_mask] if train_mask is not None else d
    clim = src.groupby("doy")[col].mean()
    target_doy = (d["doy"] + horizon - 1) % 365 + 1
    return target_doy.map(clim)


def arima_forecast(df: pd.DataFrame, horizon: int, train_mask: pd.Series,
                   col: str = "discharge") -> pd.Series:
    """ARIMA trên log(lưu lượng), fit một lần trên train rồi dự báo cuốn chiếu.

    Dùng log vì lưu lượng lệch phải rất mạnh (đỉnh gấp ~30 lần trung bình).
    """
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        print("  ! chưa cài statsmodels, bỏ qua ARIMA")
        return pd.Series(np.nan, index=df.index)

    y = np.log1p(df[col].clip(lower=0))
    try:
        model = ARIMA(y[train_mask], order=(2, 1, 2)).fit()
    except Exception as e:
        print(f"  ! ARIMA không hội tụ: {e}")
        return pd.Series(np.nan, index=df.index)

    # Dự báo trong mẫu + ngoài mẫu, dịch đi horizon ngày
    pred = model.predict(start=0, end=len(y) - 1)
    pred = pred.reindex(df.index)
    return np.expm1(pred.shift(horizon)).clip(lower=0)


BASELINES = {
    "persistence": persistence,
    "seasonal_naive": seasonal_naive,
}


def evaluate(panel: pd.DataFrame | None = None) -> pd.DataFrame:
    if panel is None:
        p = cfg.DATA_PROCESSED / "daily_panel.parquet"
        if not p.exists():
            raise SystemExit("Chưa có daily_panel.parquet — chạy "
                             "`python -m src.features.build_panel` trước.")
        panel = pd.read_parquet(p)

    dates = pd.DatetimeIndex(panel["date"])
    split = walk_forward.regime_split(dates)
    train_mask = panel["date"].isin(split["train"]) | panel["date"].isin(split["valid"])
    test_mask = panel["date"].isin(split["test"])
    print(f"Train+valid: {int(train_mask.sum()):,} ngày · "
          f"Test: {int(test_mask.sum()):,} ngày".replace(",", " "))
    print(f"Test từ {panel.loc[test_mask, 'date'].min():%Y-%m-%d} "
          f"đến {panel.loc[test_mask, 'date'].max():%Y-%m-%d}\n")

    rows = []
    for h in cfg.HORIZONS:
        target = panel[f"target_h{h}"]
        preds = {name: fn(panel, h) for name, fn in BASELINES.items()}
        preds["climatology"] = climatology(panel, h, train_mask=train_mask)
        preds["arima"] = arima_forecast(panel, h, train_mask)

        for name, yhat in preds.items():
            m = metrics.regression_report(target[test_mask], yhat[test_mask])
            rows.append({"model": name, "horizon": h, **m})

    out = pd.DataFrame(rows)
    dest = cfg.ROOT / "reports" / "baseline_results.csv"
    out.to_csv(dest, index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    print(f"\n→ {dest}")
    return out


if __name__ == "__main__":
    sys.exit(0 if evaluate() is not None else 1)
