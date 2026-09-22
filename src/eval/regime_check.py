"""Kiểm chuỗi GloFAS có đổi chế độ qua mốc 2022-07-01 hay không (R21).

Vì sao phải kiểm: từ 2022-07-01 Open-Meteo đổi nguồn "lịch sử" của GloFAS từ
**tái phân tích** sang **dự báo lưu trữ**. Nếu hai đoạn không so được với nhau
về biên độ thì mô hình đang được huấn luyện trên một chế độ và vận hành trên
một chế độ khác — hỏng cả nhánh hồi quy lẫn nhánh phân loại, không riêng FR-T2.

Dấu hiệu làm nảy ra nghi ngờ: kiểm chứng ánh xạ H→Q trên 5 đợt lũ sau mốc gãy
chệch **−1,94 m một chiều**, nặng nhất là 15/11/2023 (đỉnh thật 4,34 m mà
GloFAS chỉ 584 m³/s).

**Cái bẫy của phép so trực tiếp.** So thống kê discharge trước/sau mốc gãy là
so hai khoảng thời gian *khác nhau*, nên chênh lệch có thể chỉ là biến động khí
hậu giữa các năm chứ không phải đổi chế độ dữ liệu. Muốn tách hai nguyên nhân
đó thì cần một **mốc tham chiếu không đổi qua mốc gãy**.

Mốc đó là **mưa ERA5**: ERA5 là tái phân tích trong suốt cả giai đoạn, không
đổi nguồn ở 2022-07. Nên phép thử quyết định là:

    với cùng một lượng mưa, lưu lượng GloFAS phản ứng có như nhau không?

Nếu quan hệ mưa → lưu lượng giữ nguyên thì chênh lệch thống kê chỉ là thời
tiết. Nếu quan hệ đó đổi thì chuỗi lưu lượng đã đổi chế độ.

    python -m src.eval.regime_check
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src import config as cfg

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
OUT = cfg.ROOT / "reports" / "regime_check.csv"
BREAK = pd.Timestamp(cfg.GLOFAS_REGIME_BREAK)
FLOOD_MONTHS = (9, 10, 11, 12)      # mùa lũ chính vụ ở Huế
N_BOOT = 2000


def load() -> pd.DataFrame:
    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d["date"])
    d["regime"] = np.where(d["date"] < BREAK, "truoc", "sau")
    return d


def describe(d: pd.DataFrame, label: str) -> list[dict]:
    """Thống kê mô tả hai chế độ. KHÔNG kết luận được gì một mình — xem docstring."""
    rows = []
    for reg in ("truoc", "sau"):
        s = d.loc[d["regime"] == reg, "discharge"].dropna()
        rows.append({
            "phep_do": label, "che_do": reg, "n": len(s),
            "trung_binh": round(float(s.mean()), 1),
            "trung_vi": round(float(s.median()), 1),
            "p90": round(float(s.quantile(0.90)), 1),
            "p99": round(float(s.quantile(0.99)), 1),
            "cuc_dai": round(float(s.max()), 1),
        })
    return rows


def boot_ratio(a: np.ndarray, b: np.ndarray, stat) -> tuple[float, float, float]:
    """Tỉ số thống kê sau/trước, kèm KTC 95 % bootstrap."""
    rng = np.random.default_rng(cfg.SEED)
    base = stat(b) / stat(a)
    out = []
    for _ in range(N_BOOT):
        ra = rng.choice(a, len(a), replace=True)
        rb = rng.choice(b, len(b), replace=True)
        va = stat(ra)
        if va > 0:
            out.append(stat(rb) / va)
    lo, hi = np.percentile(out, [2.5, 97.5])
    return float(base), float(lo), float(hi)


def response_curve(d: pd.DataFrame) -> pd.DataFrame:
    """Phép thử quyết định: cùng lượng mưa thì lưu lượng phản ứng thế nào.

    Dùng mưa tích luỹ 3 ngày (`rain_basin` + 2 lag) làm biến điều khiển, vì lũ
    ở lưu vực này sinh ra từ mưa dồn vài ngày chứ không phải mưa một ngày.
    Chia mưa thành các khoảng cố định **dùng chung cho cả hai chế độ**, rồi so
    lưu lượng trung vị trong từng khoảng.
    """
    d = d.copy()
    d["rain3"] = d["rain_basin"] + d["rain_basin_lag1"] + d["rain_basin_lag2"]
    d = d.dropna(subset=["rain3", "discharge"])

    edges = [0, 5, 20, 50, 100, 200, 1e9]
    names = ["0–5", "5–20", "20–50", "50–100", "100–200", "> 200"]
    d["bin"] = pd.cut(d["rain3"], bins=edges, labels=names, right=False)

    rows = []
    for b in names:
        sub = d[d["bin"] == b]
        a = sub.loc[sub["regime"] == "truoc", "discharge"].to_numpy(float)
        c = sub.loc[sub["regime"] == "sau", "discharge"].to_numpy(float)
        if len(a) < 20 or len(c) < 20:
            rows.append({"bin_mua_3ngay_mm": b, "n_truoc": len(a), "n_sau": len(c),
                         "q_trung_vi_truoc": np.nan, "q_trung_vi_sau": np.nan,
                         "ti_so": np.nan, "lo95": np.nan, "hi95": np.nan,
                         "khac_biet": "thiếu mẫu"})
            continue
        r, lo, hi = boot_ratio(a, c, np.median)
        rows.append({
            "bin_mua_3ngay_mm": b, "n_truoc": len(a), "n_sau": len(c),
            "q_trung_vi_truoc": round(float(np.median(a)), 1),
            "q_trung_vi_sau": round(float(np.median(c)), 1),
            "ti_so": round(r, 3), "lo95": round(lo, 3), "hi95": round(hi, 3),
            # KTC không chứa 1 ⇒ khác biệt có ý nghĩa thống kê
            "khac_biet": "CÓ" if (lo > 1 or hi < 1) else "không",
        })
    return pd.DataFrame(rows)


def peak_response(d: pd.DataFrame) -> pd.DataFrame:
    """So đỉnh lưu lượng năm với tổng mưa mùa lũ của chính năm đó.

    Nếu GloFAS sau mốc gãy bị làm trơn / hạ đỉnh, tỉ số đỉnh-trên-mưa sẽ tụt.
    """
    d = d[d["date"].dt.month.isin(FLOOD_MONTHS)].copy()
    d["nam"] = d["date"].dt.year
    g = d.groupby("nam").agg(q_dinh=("discharge", "max"),
                             mua_mua_lu=("rain_basin", "sum"),
                             n=("discharge", "size")).reset_index()
    g = g[g["n"] >= 80]                      # đủ mùa lũ, bỏ năm cụt
    g["che_do"] = np.where(g["nam"] < BREAK.year, "truoc", "sau")
    g["dinh_tren_mua"] = (g["q_dinh"] / g["mua_mua_lu"]).round(3)
    return g.round(1)


def main() -> int:
    d = load()
    print(f"Panel {len(d):,} ngày · mốc gãy {BREAK:%Y-%m-%d}".replace(",", " "))
    print(f"  trước: {(d['regime'] == 'truoc').sum():,} ngày · "
          f"sau: {(d['regime'] == 'sau').sum():,} ngày".replace(",", " "))

    # --- 1. Mô tả: gợi ý, KHÔNG phải bằng chứng --------------------------
    print("\n" + "=" * 70)
    print("1. THỐNG KÊ MÔ TẢ — chưa kết luận được gì")
    print("=" * 70)
    rows = describe(d, "tat_ca_ngay")
    flood = d[d["date"].dt.month.isin(FLOOD_MONTHS)]
    rows += describe(flood, "chi_mua_lu")
    desc = pd.DataFrame(rows)
    print(desc.to_string(index=False))
    print("\nHai đoạn là hai khoảng thời gian khác nhau, nên chênh lệch ở đây có")
    print("thể chỉ là thời tiết. Phần 2 mới tách được hai nguyên nhân.")

    # --- 2. Phép thử quyết định ------------------------------------------
    print("\n" + "=" * 70)
    print("2. CÙNG LƯỢNG MƯA THÌ LƯU LƯỢNG PHẢN ỨNG NHƯ NHAU KHÔNG?")
    print("   (mưa ERA5 là tái phân tích suốt cả giai đoạn ⇒ mốc tham chiếu)")
    print("=" * 70)
    rc = response_curve(d)
    print(rc.to_string(index=False))
    signif = rc[rc["khac_biet"] == "CÓ"]
    print(f"\n{len(signif)}/{len(rc.dropna(subset=['ti_so']))} khoảng mưa có khác biệt "
          f"vượt KTC 95 %.")

    # --- 3. Đỉnh năm trên tổng mưa mùa lũ --------------------------------
    print("\n" + "=" * 70)
    print("3. ĐỈNH LŨ NĂM SO VỚI TỔNG MƯA MÙA LŨ CỦA CHÍNH NĂM ĐÓ")
    print("=" * 70)
    pk = peak_response(d)
    print(pk[["nam", "che_do", "q_dinh", "mua_mua_lu", "dinh_tren_mua"]]
          .to_string(index=False))
    a = pk.loc[pk["che_do"] == "truoc", "dinh_tren_mua"].to_numpy(float)
    b = pk.loc[pk["che_do"] == "sau", "dinh_tren_mua"].to_numpy(float)
    if len(a) >= 3 and len(b) >= 2:
        print(f"\n  trung vị đỉnh/mưa — trước: {np.median(a):.3f} · "
              f"sau: {np.median(b):.3f} · tỉ số {np.median(b)/np.median(a):.2f}")
        print(f"  (n = {len(a)} năm trước, {len(b)} năm sau — mẫu nhỏ, chỉ là gợi ý)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    desc.to_csv(OUT, index=False)
    rc.to_csv(OUT.with_name("regime_response.csv"), index=False)
    pk.to_csv(OUT.with_name("regime_peaks.csv"), index=False)
    print(f"\n→ {OUT.relative_to(cfg.ROOT)}")
    print(f"→ {OUT.with_name('regime_response.csv').relative_to(cfg.ROOT)}")
    print(f"→ {OUT.with_name('regime_peaks.csv').relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
