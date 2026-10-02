"""Nhãn **mức nguy cơ** theo phân vị lưu lượng (FR-T3, phương án R4).

Vì sao không dùng cấp báo động BĐ I/II/III: ánh xạ mực nước → lưu lượng tại
Kim Long đứng trên quan hệ **không có ý nghĩa thống kê** (ln(Q) → H có
R² = 0,184, Spearman p = 0,245 trên 12 đợt; xem `FINDINGS_REGIME.md` §4). Gán
nhãn BĐ bằng một ánh xạ như vậy là tạo ra nhãn sai mà không ai biết.

Nên theo đúng phương án R4 đã dự phòng sẵn trong `THRESHOLDS.md`:

* ngưỡng = **phân vị Q95 / Q98 / Q99,5 của mùa lũ**
* nhãn **bắt buộc** gọi là **"Mức nguy cơ 1/2/3"**, *không* gọi là BĐ I/II/III

Ngưỡng tính **chỉ trên train + valid** (tới 2022-06-30). Tính trên cả chuỗi là
rò rỉ thông tin của tập test vào định nghĩa nhãn.

    python -m src.features.risk_levels
"""

from __future__ import annotations

import sys

import pandas as pd

from src import config as cfg
from src.eval import metrics, walk_forward

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
OUT = cfg.ROOT / "reports" / "risk_levels.csv"
FLOOD_MONTHS = (9, 10, 11, 12)
QUANTILES = {"nguy_co_1": 0.95, "nguy_co_2": 0.98, "nguy_co_3": 0.995}
TEN_NHAN = {0: "binh_thuong", 1: "nguy_co_1", 2: "nguy_co_2", 3: "nguy_co_3"}


def fit_thresholds(panel: pd.DataFrame, train: pd.Series) -> dict[str, float]:
    """Ngưỡng phân vị, tính trên mùa lũ của train+valid."""
    s = panel.loc[train & panel["date"].dt.month.isin(FLOOD_MONTHS), "discharge"].dropna()
    return {k: float(s.quantile(q)) for k, q in QUANTILES.items()}


def apply_levels(q: pd.Series, thr: dict[str, float]) -> pd.Series:
    lv = pd.Series(0, index=q.index, dtype="int8")
    lv[q >= thr["nguy_co_1"]] = 1
    lv[q >= thr["nguy_co_2"]] = 2
    lv[q >= thr["nguy_co_3"]] = 3
    lv[q.isna()] = -1
    return lv


def main() -> int:
    panel = pd.read_parquet(PANEL)
    panel["date"] = pd.to_datetime(panel["date"])
    sp = walk_forward.regime_split(pd.DatetimeIndex(panel["date"]))
    train = panel["date"].isin(sp["train"]) | panel["date"].isin(sp["valid"])
    test = panel["date"].isin(sp["test"])

    thr = fit_thresholds(panel, train)
    print("Ngưỡng phân vị mùa lũ, tính CHỈ trên train+valid "
          f"({int(train.sum())} ngày, tới {cfg.VALID_END}):")
    for k, q in QUANTILES.items():
        print(f"  {k:<12} Q{q:.3%} = {thr[k]:8.1f} m³/s")

    # Ghi nhãn vào cột `alert_level` có sẵn của panel, KHÔNG thêm cột mới: một
    # cột thừa trong panel sẽ lọt vào feature của mọi mô hình đọc panel sau đó
    # (đã xảy ra: 66 → 67 feature). Panel giữ đúng 71 cột.
    risk = apply_levels(panel["discharge"], thr)
    panel = panel.drop(columns=["risk_level"], errors="ignore")
    panel["alert_level"] = risk

    rows = []
    print("\nPhân bố lớp:")
    print(f"  {'nhãn':<14}{'toàn chuỗi':>12}{'train+valid':>13}{'test':>8}{'% test':>9}")
    for lv in (0, 1, 2, 3):
        n_all = int((risk == lv).sum())
        n_tr = int(((risk == lv) & train).sum())
        n_te = int(((risk == lv) & test).sum())
        pct = n_te / int(test.sum()) * 100
        print(f"  {TEN_NHAN[lv]:<14}{n_all:>12}{n_tr:>13}{n_te:>8}{pct:>8.2f}%")
        rows.append({"muc": TEN_NHAN[lv], "nguong_m3s": round(thr.get(TEN_NHAN[lv], 0.0), 1),
                     "n_toan_chuoi": n_all, "n_train_valid": n_tr, "n_test": n_te,
                     "pct_test": round(pct, 2)})

    # Bài toán thật là "hôm nay có vượt mức k không", tức luỹ kế ≥ k, chứ không
    # phải rơi đúng vào dải k. Luật 30 mẫu (SPEC.md) áp trên số này.
    print()
    print("Số ngày ≥ mỗi mức trong TEST (đây mới là số mẫu của bài toán):")
    for r in rows[1:]:
        lv = [k for k, v in TEN_NHAN.items() if v == r["muc"]][0]
        n_cum = int(((risk >= lv) & test).sum())
        r["n_test_luy_ke"] = n_cum
        w = metrics.warn_small_sample(n_cum)
        r["du_mau_test"] = w is None
        flag = "đủ mẫu" if w is None else "⚠️ DƯỚI 30 — không được làm kết luận chính"
        print(f"  ≥ {r['muc']:<12} {n_cum:>4} ngày   {flag}")

    # Không nới ngưỡng để lấy số mẫu đẹp hơn: 95/98/99,5 đã chốt trong
    # THRESHOLDS.md R4 từ W1. Đổi ngưỡng cho vừa luật 30 mẫu chính là chỉnh
    # theo tập test. Hạn chế thật nằm ở chỗ cửa sổ test chỉ 4,2 năm.

    res = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT, index=False)
    panel.to_parquet(PANEL, index=False)
    print(f"\n→ {OUT.relative_to(cfg.ROOT)}")
    print(f"→ {PANEL.relative_to(cfg.ROOT)}  (cột alert_level đã điền, "
          f"{int((risk >= 0).sum())} ngày có nhãn · panel {panel.shape[1]} cột)")
    print("\n⚠️ Nhãn này là MỨC NGUY CƠ theo phân vị lưu lượng, KHÔNG phải cấp")
    print("   báo động BĐ I/II/III của nhà nước. Không được gọi nhầm tên trong")
    print("   báo cáo hay dashboard — xem docs/THRESHOLDS.md R4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
