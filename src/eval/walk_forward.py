"""Chia tập kiểu walk-forward cho chuỗi thời gian (FR-V1).

Không dùng k-fold ngẫu nhiên: trộn ngẫu nhiên sẽ cho mô hình học từ tương lai
rồi kiểm tra trên quá khứ, kết quả đẹp giả và vô nghĩa.

Hai điểm bắt buộc:

* **Cửa sổ train mở rộng dần** (expanding), không trượt — luôn dùng hết dữ liệu
  quá khứ có được tại thời điểm đó, giống cách mô hình chạy thật.
* **Có khoảng trống (gap)** giữa cuối train và đầu test, rộng ít nhất bằng
  horizon dài nhất. Không có gap thì nhãn của mấy ngày cuối tập train đã chứa
  thông tin của mấy ngày đầu tập test.
"""

from __future__ import annotations

import pandas as pd

from src import config as cfg

GAP_DAYS = max(cfg.HORIZONS)


def make_folds(dates: pd.DatetimeIndex, n_folds: int = 5,
               gap_days: int = GAP_DAYS,
               min_train_frac: float = 0.4
               ) -> list[tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
    """Sinh các fold (train, test) nối tiếp theo thời gian.

    Trả về danh sách `(ngày_train, ngày_test)`. Tập test của các fold liền kề
    nhau và không chồng lấn; tập train lớn dần qua từng fold.
    """
    dates = pd.DatetimeIndex(pd.Series(dates).sort_values().unique())
    n = len(dates)
    if n < 10 or n_folds < 1:
        raise ValueError(f"Không đủ dữ liệu để chia fold: {n} ngày")

    start = int(n * min_train_frac)
    test_size = (n - start) // n_folds
    if test_size <= gap_days:
        raise ValueError(
            f"Mỗi fold chỉ có {test_size} ngày test, không lớn hơn gap "
            f"{gap_days} ngày. Giảm n_folds hoặc dùng chuỗi dài hơn."
        )

    folds = []
    for i in range(n_folds):
        train_end = start + i * test_size
        test_lo = train_end + gap_days
        test_hi = test_lo + test_size if i < n_folds - 1 else n
        if test_lo >= n:
            break
        folds.append((dates[:train_end], dates[test_lo:test_hi]))
    return folds


def describe_folds(folds) -> pd.DataFrame:
    """Bảng tóm tắt để dán vào báo cáo."""
    rows = []
    for i, (tr, te) in enumerate(folds, 1):
        rows.append({
            "fold": i,
            "train_tu": tr.min().date(), "train_den": tr.max().date(),
            "n_train": len(tr),
            "test_tu": te.min().date(), "test_den": te.max().date(),
            "n_test": len(te),
            "gap_ngay": (te.min() - tr.max()).days,
        })
    return pd.DataFrame(rows)


def regime_split(dates: pd.DatetimeIndex) -> dict[str, pd.DatetimeIndex]:
    """Chia theo mốc đổi chế độ dữ liệu của GloFAS (docs/DATA_SPLITS.md §1)."""
    dates = pd.DatetimeIndex(dates)
    return {
        "train": dates[dates <= cfg.TRAIN_END],
        "valid": dates[(dates > cfg.TRAIN_END) & (dates <= cfg.VALID_END)],
        "test": dates[dates >= cfg.GLOFAS_REGIME_BREAK],
    }


if __name__ == "__main__":
    panel = cfg.DATA_PROCESSED / "daily_panel.parquet"
    if not panel.exists():
        raise SystemExit("Chưa có daily_panel.parquet — chạy "
                         "`python -m src.features.build_panel` trước.")
    d = pd.DatetimeIndex(pd.read_parquet(panel, columns=["date"])["date"])

    print("Chia theo chế độ dữ liệu (dùng cho kết quả cuối):")
    for k, v in regime_split(d).items():
        if len(v):
            print(f"  {k:6} {len(v):6,} ngày  {v.min():%Y-%m-%d} → {v.max():%Y-%m-%d}"
                  .replace(",", " "))

    print(f"\nWalk-forward 5 fold (gap {GAP_DAYS} ngày):")
    print(describe_folds(make_folds(d, n_folds=5)).to_string(index=False))
