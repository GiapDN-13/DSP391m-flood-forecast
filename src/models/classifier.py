"""Phân loại ngày vượt mức nguy cơ (FR-M3).

Bài toán đặt dưới dạng **nhị phân theo từng mức**: "ngày t+h có vượt mức k
không", với k = 1, 2, 3 và h = 1, 2, 3. Đặt như vậy vì đó đúng là câu hỏi vận
hành ("hôm nay có cần cảnh báo không"), và vì phân loại đa lớp trên 3 lớp hiếm
với 7–31 ngày dương thì không học được gì.

Nhãn là **mức nguy cơ theo phân vị lưu lượng**, *không* phải cấp báo động
BĐ I/II/III — xem `src/features/risk_levels.py` và `THRESHOLDS.md` R4.

**Không dùng accuracy.** Ngày vượt mức 1 chỉ chiếm ~1 % số ngày, nên một mô
hình luôn đoán "không" đã đạt 99 %. Bộ chỉ số là POD / FAR / CSI / F1 / PR-AUC
/ Brier, và **luôn in kèm số ngày dương** để người đọc tự đánh giá độ tin.

    python -m src.models.classifier
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src import config as cfg
from src.eval import metrics, walk_forward
from src.features.risk_levels import FLOOD_MONTHS, QUANTILES

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
OUT = cfg.ROOT / "reports" / "classifier_results.csv"
MIN_POS = 30          # luật 30 mẫu (SPEC.md)

PARAMS = dict(
    objective="binary",
    n_estimators=400,
    learning_rate=0.05,
    num_leaves=15,           # nhỏ hơn bản hồi quy: lớp dương rất ít, dễ khớp quá mức
    min_child_samples=20,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    random_state=cfg.SEED,
    verbose=-1,
)


def feature_cols(panel: pd.DataFrame) -> list[str]:
    drop = ({"date", "alert_level", "risk_level"}
            | {c for c in panel.columns if c.startswith("target_")})
    return [c for c in panel.columns if c not in drop
            and pd.api.types.is_numeric_dtype(panel[c])]


def main() -> int:
    from lightgbm import LGBMClassifier
    from sklearn.metrics import average_precision_score, brier_score_loss

    panel = pd.read_parquet(PANEL)
    panel["date"] = pd.to_datetime(panel["date"])
    sp = walk_forward.regime_split(pd.DatetimeIndex(panel["date"]))
    tr = panel["date"].isin(sp["train"]) | panel["date"].isin(sp["valid"])
    te = panel["date"].isin(sp["test"])
    feats = feature_cols(panel)

    # Ngưỡng phải tính lại đúng như risk_levels.py: chỉ trên train+valid.
    s = panel.loc[tr & panel["date"].dt.month.isin(FLOOD_MONTHS), "discharge"].dropna()
    thr = {k: float(s.quantile(q)) for k, q in QUANTILES.items()}
    print("Ngưỡng (train+valid, mùa lũ): "
          + " · ".join(f"{k} = {v:.0f}" for k, v in thr.items()))
    print(f"Train+valid {int(tr.sum())} ngày · Test {int(te.sum())} ngày · "
          f"{len(feats)} feature\n")

    rows = []
    for k, (name, thr_v) in enumerate(thr.items(), start=1):
        for h in cfg.HORIZONS:
            y = (panel[f"target_h{h}"] >= thr_v).astype("int8")
            ok = panel[f"target_h{h}"].notna() & panel[feats].notna().all(axis=1)
            a, b = tr & ok, te & ok
            n_pos_tr, n_pos_te = int(y[a].sum()), int(y[b].sum())
            if n_pos_tr < 10:
                print(f"  ! {name} h={h}: chỉ {n_pos_tr} ngày dương trong train — bỏ qua")
                continue

            # Bù mất cân bằng lớp bằng trọng số, không lấy mẫu lại: lấy mẫu lại
            # trên chuỗi thời gian sẽ phá cấu trúc tự tương quan.
            w = float((len(y[a]) - n_pos_tr) / max(n_pos_tr, 1))
            m = LGBMClassifier(**PARAMS, scale_pos_weight=w)
            m.fit(panel.loc[a, feats], y[a])

            proba = m.predict_proba(panel.loc[b, feats])[:, 1]
            yt = y[b].to_numpy()
            pred = (proba >= 0.5).astype(int)

            ev = metrics.event_report(yt, pred)
            rows.append({
                "muc": name, "nguong_m3s": round(thr_v), "horizon": h,
                "n_duong_train": n_pos_tr, "n_duong_test": n_pos_te,
                **{kk: round(vv, 3) for kk, vv in ev.items()},
                "PR_AUC": round(float(average_precision_score(yt, proba)), 3)
                if n_pos_te else np.nan,
                "Brier": round(float(brier_score_loss(yt, proba)), 4),
                "du_mau": n_pos_te >= MIN_POS,
            })

    res = pd.DataFrame(rows)
    cols = ["muc", "horizon", "n_duong_test", "POD", "FAR", "CSI", "F1",
            "PR_AUC", "Brier", "du_mau"]
    print(res[cols].to_string(index=False))

    thieu = res[~res.du_mau]
    if len(thieu):
        print(f"\n⚠️ {len(thieu)}/{len(res)} dòng có DƯỚI {MIN_POS} ngày dương trong "
              f"test. Những dòng đó báo cáo được nhưng KHÔNG được dùng làm kết")
        print("   luận chính (SPEC.md, luật 30 mẫu).")
    good = res[res.du_mau]
    if len(good):
        print(f"\nDòng đủ mẫu: {', '.join(f'{r.muc} h={r.horizon}' for _, r in good.iterrows())}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT, index=False)
    print(f"\n→ {OUT.relative_to(cfg.ROOT)}")
    print("\n⚠️ Nhãn là MỨC NGUY CƠ theo phân vị lưu lượng, KHÔNG phải BĐ I/II/III.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
