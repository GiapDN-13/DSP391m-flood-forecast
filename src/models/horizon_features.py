"""Chọn bộ feature riêng cho từng horizon — trên tập VALID, không phải test.

Vì sao: ablation trên tập test (`FINDINGS_MODEL.md` §4b) cho thấy từ h≥2, bỏ
hẳn lag lưu lượng lại cho NSE cao hơn mô hình đầy đủ. Nhưng chọn bộ feature
theo điểm test là rò rỉ tập test. Ở đây làm đúng quy trình:

1. Huấn luyện **chỉ trên train** (≤ 2015-12-31).
2. Chấm từng bộ feature ứng viên trên **valid** (2016-01-01 → 2022-06-30).
3. Chọn bộ tốt nhất theo NSE valid, **riêng từng horizon**.
4. Huấn luyện lại trên train + valid với bộ đã chọn, rồi đo **test đúng một lần**.

Danh sách ứng viên giữ ngắn có chủ ý: càng nhiều ứng viên thì càng dễ chọn
trúng một bộ "may mắn" trên valid.

    python -m src.models.horizon_features
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src import config as cfg
from src.eval import metrics, walk_forward
from src.models.lgbm import PARAMS, feature_cols

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
OUT = cfg.ROOT / "reports" / "horizon_features.csv"
SEASON = {"doy_sin", "doy_cos", "month", "mua_lu"}


def candidates(full: list[str]) -> dict[str, list[str]]:
    is_rain = lambda c: c.startswith("rain_") or c == "api"  # noqa: E731
    is_q = lambda c: c.startswith("discharge") or c.startswith("q_diff")  # noqa: E731
    short_q = {"discharge", "discharge_lag1", "discharge_lag2", "discharge_lag3",
               "q_diff1", "q_diff3"}
    return {
        "day_du": full,
        "chi_mua_mua_vu": [c for c in full if is_rain(c) or c in SEASON],
        "mua_va_Q_ngan": [c for c in full if is_rain(c) or c in SEASON or c in short_q],
        "khong_mua": [c for c in full if is_q(c) or c in SEASON],
    }


def fit_nse(panel, feats, h, tr, ev) -> tuple[float, int]:
    from lightgbm import LGBMRegressor
    y = panel[f"target_h{h}"]
    ok = panel[feats].notna().all(axis=1) & y.notna()
    a, b = tr & ok, ev & ok
    m = LGBMRegressor(**PARAMS)
    m.fit(panel.loc[a, feats], np.log1p(y[a]))
    pr = np.clip(np.expm1(m.predict(panel.loc[b, feats])), 0, None)
    return metrics.nse(y[b].to_numpy(float), pr), int(b.sum())


def main() -> int:
    panel = pd.read_parquet(PANEL)
    panel["date"] = pd.to_datetime(panel["date"])
    sp = walk_forward.regime_split(pd.DatetimeIndex(panel["date"]))
    train = panel["date"].isin(sp["train"])
    valid = panel["date"].isin(sp["valid"])
    test = panel["date"].isin(sp["test"])
    cands = candidates(feature_cols(panel))
    print(f"Train {int(train.sum())} ngày · Valid {int(valid.sum())} · Test {int(test.sum())}")
    print(f"{len(cands)} bộ ứng viên: " + ", ".join(f"{k} ({len(v)})" for k, v in cands.items()))

    rows = []
    for h in cfg.HORIZONS:
        print(f"\nh={h}  — chấm trên VALID (huấn luyện chỉ trên train):")
        scores = {}
        for name, fs in cands.items():
            nse_v, n = fit_nse(panel, fs, h, train, valid)
            scores[name] = nse_v
            print(f"    {name:<16} NSE valid = {nse_v:+.3f}  (n={n})")
        best = max(scores, key=scores.get)

        # Test chỉ đo MỘT lần, sau khi đã chọn xong.
        nse_best, n_te = fit_nse(panel, cands[best], h, train | valid, test)
        nse_full, _ = fit_nse(panel, cands["day_du"], h, train | valid, test)
        print(f"  → chọn: {best}  ·  NSE test {nse_best:+.3f}  "
              f"(bộ đầy đủ: {nse_full:+.3f}, chênh {nse_best - nse_full:+.3f})")
        rows.append({"horizon": h, "bo_chon": best, "n_feature": len(cands[best]),
                     "nse_valid_bo_chon": round(scores[best], 3),
                     "nse_valid_day_du": round(scores["day_du"], 3),
                     "nse_test_bo_chon": round(nse_best, 3),
                     "nse_test_day_du": round(nse_full, 3),
                     "chenh_test": round(nse_best - nse_full, 3), "n_test": n_te})

    res = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT, index=False)
    print("\n" + res.to_string(index=False))
    print(f"\n→ {OUT.relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
