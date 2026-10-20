"""Kịch bản B′ — độ nhạy với chất lượng dự báo mưa (FR-V4).

**Kịch bản B thật không dựng được.** Kế hoạch ban đầu là thay mưa thực đo bằng
**mưa dự báo đã phát** từ Historical Forecast API (`data/raw/fc_rain/`, FR-D3).
Kiểm ngày 22/09/2026 cho thấy endpoint đó trả về **đúng cùng con số** với
Archive API (ERA5): tương quan 1,0000 và chênh lệch tối đa **0,0 mm** trên
1 523 ngày, xác nhận lại bằng gọi API trực tiếp. Đã thử cả Previous-Runs API —
các biến `*_previous_dayN` bị bỏ qua cho vùng này.

⇒ Không có nguồn mở nào cho **mưa dự báo phát trước 1–3 ngày** ở lưu vực này.

**Thay bằng gì.** `RESEARCH_DESIGN.md` §2 đã dự phòng sẵn phương án **B′**. Ở
đây làm dạng chặt hơn một bậc: thay vì đoán một phân phối sai số rồi báo một
con số, ta **quét độ nhạy** — làm nhiễu mưa với nhiều mức sai số tăng dần rồi
xem kỹ năng dự báo tụt theo đường nào.

Câu hỏi trả lời được: *"chất lượng dự báo mưa phải tốt đến đâu thì mô hình mới
còn dùng được?"* — hữu ích hơn một con số đơn lẻ, và không giả vờ biết thứ
mình không đo được.

Nhiễu dùng dạng **nhân, lognormal** (sai số dự báo mưa lệch phải, không âm),
tham số `sigma` là độ lệch chuẩn log. `sigma = 0` chính là kịch bản A.

    python -m src.eval.scenario_b
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src import config as cfg
from src.etl import clean
from src.eval import metrics, walk_forward
from src.features.build_panel import (
    aggregate_rain,
    antecedent_index,
    make_lags,
    make_rolling,
)
from src.models.lgbm import PARAMS, feature_cols

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
OUT = cfg.ROOT / "reports" / "scenario_b_results.csv"


def forecast_rain_panel() -> pd.DataFrame:
    """Dựng các cột mưa từ **mưa dự báo**, đúng cách gộp như panel chính.

    Dùng lại nguyên các hàm của tầng dữ liệu (DuckDB + Polars), rồi mới chuyển
    sang bảng pandas ở cuối vì phần mô hình bên dưới vẫn làm việc với pandas.
    """
    fc = clean.load_forecast_rain().rename({"rain_fc": "rain"})
    out = aggregate_rain(fc)

    # Lag và cửa sổ trượt phải dựng lại TỪ chuỗi dự báo, không mượn của panel A.
    for c in [c for c in out.columns if c.startswith("rain_")]:
        out = make_lags(out, c, cfg.RAIN_LAGS)
        out = make_rolling(out, c, [3, 5, 7], how="sum")
    out = out.with_columns(antecedent_index("rain_basin").alias("api"))
    return out.to_pandas()


def main() -> int:
    from lightgbm import LGBMRegressor

    panel = pd.read_parquet(PANEL)
    panel["date"] = pd.to_datetime(panel["date"])
    sp = walk_forward.regime_split(pd.DatetimeIndex(panel["date"]))
    tr = panel["date"].isin(sp["train"]) | panel["date"].isin(sp["valid"])
    te = panel["date"].isin(sp["test"])
    feats = feature_cols(panel)

    # Chứng minh lại tại chỗ: fc_rain không khác ERA5. Để ai chạy lại cũng thấy.
    fcp = forecast_rain_panel()
    j = panel[["date", "rain_basin"]].merge(
        fcp[["date", "rain_basin"]].rename(columns={"rain_basin": "fc"}), on="date")
    print(f"Đối chiếu mưa 'dự báo' với ERA5 trên {len(j)} ngày: "
          f"chênh lệch lớn nhất {float((j.rain_basin - j.fc).abs().max()):.4f} mm "
          f"⇒ {'KHÁC NHAU' if float((j.rain_basin - j.fc).abs().max()) > 0.01 else 'GIỐNG HỆT — không dùng làm kịch bản B được'}")
    print()

    rain_cols = [c for c in feats if c.startswith("rain_") or c == "api"]
    rng = np.random.default_rng(cfg.SEED)
    sigmas = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    rows = []
    for h in cfg.HORIZONS:
        y = panel[f"target_h{h}"]
        ok_tr = tr & y.notna() & panel[feats].notna().all(axis=1)
        ok_te = te & y.notna() & panel[feats].notna().all(axis=1)
        m = LGBMRegressor(**PARAMS)
        m.fit(panel.loc[ok_tr, feats], np.log1p(y[ok_tr]))
        yt = y[ok_te].to_numpy(float)

        for sg in sigmas:
            X = panel.loc[ok_te, feats].copy()
            if sg > 0:
                # Nhiễu nhân, trung vị giữ nguyên 1 để không thêm độ chệch.
                noise = rng.lognormal(mean=0.0, sigma=sg, size=(len(X), len(rain_cols)))
                X[rain_cols] = X[rain_cols].to_numpy() * noise
            pred = np.clip(np.expm1(m.predict(X)), 0, None)
            r = metrics.regression_report(yt, pred)
            rows.append({"horizon": h, "sigma": sg, "n": len(yt),
                         "NSE": round(r["NSE"], 3), "RMSE": round(r["RMSE"], 1),
                         "peak_bias": round(r["peak_bias"], 3)})

    res = pd.DataFrame(rows)
    piv = res.pivot(index="sigma", columns="horizon", values="NSE")
    print("NSE theo mức sai số mưa (sigma = 0 là kịch bản A, mưa hoàn hảo):")
    print(piv.to_string())

    base = piv.loc[0.0]
    print()
    print("Mức tụt so với mưa hoàn hảo:")
    for sg in sigmas[1:]:
        d = (piv.loc[sg] - base)
        print(f"  sigma = {sg:.1f}: " + " · ".join(
            f"h{h} {d[h]:+.3f}" for h in cfg.HORIZONS))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT, index=False)
    print()
    print(f"→ {OUT.relative_to(cfg.ROOT)}")
    print()
    print("⚠️ Đây là kịch bản B′ (giả lập), KHÔNG phải kịch bản B thật. Mọi con số")
    print("   trong báo cáo phải gọi đúng tên và nêu rõ vì sao B thật không làm được.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
