"""Ánh xạ mực nước báo động sang lưu lượng GloFAS (FR-T2).

Vấn đề: ngưỡng báo động của Việt Nam định nghĩa bằng **mực nước (m)**, còn dữ
liệu ta có là **lưu lượng mô phỏng (m³/s)**. Không có chuỗi (H, Q) đồng thời,
nên dùng phương án R2 trong `docs/THRESHOLDS.md`: hiệu chuẩn theo **các đỉnh lũ
đã công bố** trong `data/external/flood_events.csv`.

    H = α · ln(Q) + β        →        Q_BĐk = exp((H_BĐk − β) / α)

⚠️ Đây **không phải** đường quan hệ H–Q vật lý của lòng sông. Nó hấp thụ cùng
lúc: lệch giữa lưu lượng trung bình ngày của GloFAS và đỉnh tức thời của mực
nước công bố, sai số mô phỏng, và sai số ngày đỉnh. Gọi đúng tên: **ánh xạ hiệu
chuẩn theo sự kiện**.

Ba điều phải biết trước khi đọc số:

1. **Chuỗi GloFAS thực tế bắt đầu 1997-01-01**, không phải 1984 như tài liệu cũ
   ghi. 1984-1996 API trả đủ dòng nhưng rỗng toàn bộ (30,5 % chuỗi). Nên sự
   kiện 1983/1984/1995/1996 không bao giờ ghép được lưu lượng.
2. **Quan hệ H-Q ở Kim Long không ổn định theo thời gian.** Trạm chịu ảnh hưởng
   triều mạnh, và từ 2009 đến 2014 lần lượt có Bình Điền, Hương Điền, Tả Trạch
   vào vận hành, đổi cách dòng chảy truyền về hạ lưu. Trộn cả thời kỳ làm quan
   hệ mất tính đơn điệu: 1998 có Q = 3 161 nhưng H = 4,47 m, còn 1999 chỉ
   Q = 1 900 mà H = 5,81 m. Vì vậy script fit **hai tập** và báo cáo cả hai.
3. Sau **2022-07-01** GloFAS đổi từ tái phân tích sang dự báo lưu trữ. Sự kiện
   sau mốc đó **không fit**, chỉ dùng kiểm chứng ngoài mẫu (FR-T4).

    python -m src.features.thresholds
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src import config as cfg

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EVENTS = cfg.ROOT / "data" / "external" / "flood_events.csv"
OUT = cfg.ROOT / "data" / "processed" / "threshold_mapping.csv"
WITH_Q = cfg.ROOT / "data" / "processed" / "flood_events_with_Q.csv"
N_BOOT = 2000
MIN_N = 10            # RISKS.md R15: dưới 10 cặp thì không được kết luận
RESERVOIR_ERA = "2009-01-01"   # Bình Điền vận hành; Hương Điền 2011, Tả Trạch 2014


def load_discharge(lat: float, lon: float) -> pd.Series:
    """Chuỗi lưu lượng ngày của một ô lưới, lấy từ dữ liệu thô.

    Không dùng `daily_panel.parquet` vì panel chỉ từ 2010, mà sự kiện hiệu
    chuẩn nằm rải từ 1997.
    """
    f = cfg.ROOT / "data" / "raw" / "discharge" / f"q_{lat:g}_{lon:g}.parquet"
    if not f.exists():
        raise SystemExit(f"Không có {f}. Chạy `python scripts/restore_data.py "
                         f"--what raw_discharge` trước.")
    d = pd.read_parquet(f)
    tcol = "time" if "time" in d.columns else "date"
    s = pd.Series(d["river_discharge"].to_numpy(),
                  index=pd.to_datetime(d[tcol]).dt.tz_localize(None).dt.normalize())
    return s.sort_index()


def peak_q(q: pd.Series, day: pd.Timestamp, half_window: int) -> float:
    """Lưu lượng đỉnh trong cửa sổ ±half_window ngày quanh ngày đỉnh mực nước.

    Cửa sổ hấp thụ lệch pha mô phỏng-thực đo, và việc nhiều nguồn chỉ cho
    khoảng ngày chứ không cho ngày đỉnh (cột `window_days`).
    """
    lo = day - pd.Timedelta(days=half_window)
    hi = day + pd.Timedelta(days=half_window)
    w = q.loc[lo:hi].dropna()
    return float(w.max()) if len(w) else float("nan")


def fit_log(qs: np.ndarray, hs: np.ndarray) -> tuple[float, float]:
    """Bình phương tối thiểu cho H = α·ln(Q) + β."""
    a, b = np.polyfit(np.log(qs), hs, 1)
    return float(a), float(b)


def invert(alpha: float, beta: float, h: float) -> float:
    return float(np.exp((h - beta) / alpha))


def quality(qs: np.ndarray, hs: np.ndarray) -> tuple[float, float, float, float]:
    """Trả về (alpha, beta, r2, rmse)."""
    a, b = fit_log(qs, hs)
    pred = a * np.log(qs) + b
    rmse = float(np.sqrt(np.mean((pred - hs) ** 2)))
    r2 = 1 - float(np.sum((hs - pred) ** 2)) / float(np.sum((hs - hs.mean()) ** 2))
    return a, b, r2, rmse


def build(station: str = "kim_long") -> pd.DataFrame:
    levels = cfg.ALERT_LEVELS_M[station]
    ev = pd.read_csv(EVENTS)
    ev = ev[ev["station"] == station].copy()
    ev["peak_date"] = pd.to_datetime(ev["peak_date"])

    lat, lon = cfg.RIVER_POINTS["huong_kim_long"]
    q = load_discharge(lat, lon)
    ok = q.dropna()
    print(f"Lưu lượng ô ({lat}, {lon}): {len(q)} dòng, có dữ liệu "
          f"{ok.index.min():%Y-%m-%d} -> {ok.index.max():%Y-%m-%d} "
          f"({len(ok)} ngày, rỗng {100 * q.isna().mean():.1f} %)")

    ev["peak_Q"] = [peak_q(q, d, int(w)) for d, w in
                    zip(ev["peak_date"], ev["window_days"])]
    WITH_Q.parent.mkdir(parents=True, exist_ok=True)
    ev.to_csv(WITH_Q, index=False)

    pre = ev[(ev["regime"] == "truoc_moc_gay") & ev["peak_Q"].notna()].copy()
    missing = ev[(ev["regime"] == "truoc_moc_gay") & ev["peak_Q"].isna()]
    for _, r in missing.iterrows():
        print(f"  ! {r['event_id']} không ghép được lưu lượng "
              f"- GloFAS rỗng trước 1997")

    subsets = {"truoc_moc_gay": pre,
               "tu_2009": pre[pre["peak_date"] >= RESERVOIR_ERA]}
    print(f"\nSự kiện tại {station}: {len(ev)} · ghép được lưu lượng: {len(pre)}")
    print("\nSo sánh hai tập hiệu chuẩn:")
    for name, sub in subsets.items():
        if len(sub) < 3:
            print(f"  {name:<14} N={len(sub)} - quá ít, bỏ qua")
            continue
        a, b, r2, rmse = quality(sub["peak_Q"].to_numpy(float),
                                 sub["peak_H_m"].to_numpy(float))
        print(f"  {name:<14} N={len(sub):<3} R2={r2:6.3f}  RMSE={rmse:.3f} m  "
              f"Q_BD3={invert(a, b, levels['BD3']):7.0f} m³/s")

    # Tập chính: từ 2009. Trộn cả thời kỳ trước hồ chứa làm quan hệ mất đơn điệu.
    primary = "tu_2009"
    fitset = subsets[primary]
    qs = fitset["peak_Q"].to_numpy(float)
    hs = fitset["peak_H_m"].to_numpy(float)
    alpha, beta, r2, rmse = quality(qs, hs)

    print(f"\nTập chính: {primary}")
    print(f"H = {alpha:.4f}·ln(Q) {beta:+.4f}")
    print(f"N = {len(qs)} · R2 = {r2:.3f} · RMSE = {rmse:.3f} m")
    if len(qs) < MIN_N:
        print(f"⚠️ N = {len(qs)} DƯỚI mức tối thiểu {MIN_N} của RISKS.md R15 => "
              f"ánh xạ này là TẠM THỜI, không được dùng làm kết luận chính.")

    # Bootstrap khoảng tin cậy. Với N nhỏ đây là phần quan trọng nhất của kết
    # quả - một con số điểm không nói được gì.
    rng = np.random.default_rng(cfg.SEED)
    boot: dict[str, list[float]] = {k: [] for k in levels}
    for _ in range(N_BOOT):
        i = rng.integers(0, len(qs), len(qs))
        if len(np.unique(qs[i])) < 3:
            continue
        try:
            a, b = fit_log(qs[i], hs[i])
        except Exception:
            continue
        if a <= 0:            # đường phải đơn điệu tăng mới có nghĩa
            continue
        for k, h in levels.items():
            boot[k].append(invert(a, b, h))

    rows = []
    for k, h in levels.items():
        qk = invert(alpha, beta, h)
        arr = np.array(boot[k], float)
        lo, hi = np.percentile(arr, [2.5, 97.5])
        width = float((hi - lo) / 2 / qk * 100)
        rows.append({"station": station, "alert": k, "H_m": h,
                     "Q_m3s": round(qk, 1),
                     "Q_lo95": round(float(lo), 1), "Q_hi95": round(float(hi), 1),
                     "ci_half_width_pct": round(width, 1),
                     "n_fit": len(qs), "n_min_required": MIN_N,
                     "fit_subset": primary,
                     "r2": round(r2, 3), "rmse_m": round(rmse, 3),
                     "alpha": round(alpha, 4), "beta": round(beta, 4),
                     "reliable": bool(width <= 30 and len(qs) >= MIN_N)})
    res = pd.DataFrame(rows)

    print("\nNgưỡng lưu lượng suy ra:")
    for r in rows:
        flag = "" if r["reliable"] else "   ⚠️ chưa đạt tiêu chí tin cậy"
        print(f"  {r['alert']} (H={r['H_m']:.2f} m) -> Q = {r['Q_m3s']:>7.1f} m³/s "
              f"[{r['Q_lo95']:.0f} … {r['Q_hi95']:.0f}] "
              f"±{r['ci_half_width_pct']:.0f} %{flag}")

    ver = ev[(ev["regime"] == "sau_moc_gay") & ev["peak_Q"].notna()]
    if len(ver):
        print("\nKiểm chứng ngoài mẫu (sau mốc gãy 2022-07-01, KHÔNG dùng để fit):")
        err = []
        for _, r in ver.iterrows():
            h_hat = alpha * np.log(r["peak_Q"]) + beta
            err.append(h_hat - r["peak_H_m"])
            print(f"  {r['event_id']:<10} H thật {r['peak_H_m']:.2f} m · "
                  f"H suy ra {h_hat:5.2f} m · lệch {h_hat - r['peak_H_m']:+.2f} m "
                  f"(Q = {r['peak_Q']:.0f})")
        print(f"  -> sai số tuyệt đối trung bình {np.mean(np.abs(err)):.2f} m, "
              f"độ chệch {np.mean(err):+.2f} m")

    res.to_csv(OUT, index=False)
    print(f"\n-> {OUT.relative_to(cfg.ROOT)}")
    print(f"-> {WITH_Q.relative_to(cfg.ROOT)}")
    return res


if __name__ == "__main__":
    build()
