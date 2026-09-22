"""EDA 8 mục theo `docs/EDA_CHECKLIST.md` — nội dung chính của Report 2.

Sinh cả **số** (in ra + ghi CSV) và **hình** (PNG nền sáng, in được đen trắng).
Mỗi mục trả về một dict kết luận, gom lại thành `reports/eda_summary.csv` để
dán thẳng vào báo cáo thay vì chép tay.

    python -m src.eval.eda
"""

from __future__ import annotations

import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import config as cfg  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
FIGS = cfg.ROOT / "reports" / "figures" / "report"
OUT = cfg.ROOT / "reports" / "eda_summary.csv"
BREAK = pd.Timestamp(cfg.GLOFAS_REGIME_BREAK)

# Nền sáng, đủ tương phản khi in đen trắng
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "savefig.bbox": "tight",
    "font.size": 9, "axes.grid": True, "grid.alpha": 0.25,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})
INK, ACC, WARN = "#1a1a1a", "#00666e", "#b35c00"


def save(fig, name: str) -> str:
    FIGS.mkdir(parents=True, exist_ok=True)
    p = FIGS / name
    fig.savefig(p)
    plt.close(fig)
    print(f"    → {p.relative_to(cfg.ROOT)}")
    return name


def m1_tong_quan(d: pd.DataFrame) -> list[dict]:
    print("\n[1] Tổng quan dữ liệu")
    q = d["discharge"]
    miss = d[["discharge", "rain_basin"]].isna().mean()
    out = [
        {"muc": 1, "chi_tieu": "số ngày", "gia_tri": len(d)},
        {"muc": 1, "chi_tieu": "khoảng", "gia_tri": f"{d.date.min():%Y-%m-%d} → {d.date.max():%Y-%m-%d}"},
        {"muc": 1, "chi_tieu": "discharge thiếu (%)", "gia_tri": round(float(miss.discharge) * 100, 2)},
        {"muc": 1, "chi_tieu": "mưa thiếu (%)", "gia_tri": round(float(miss.rain_basin) * 100, 2)},
        {"muc": 1, "chi_tieu": "Q trung vị (m³/s)", "gia_tri": round(float(q.median()), 1)},
        {"muc": 1, "chi_tieu": "Q p99 (m³/s)", "gia_tri": round(float(q.quantile(0.99)), 1)},
        {"muc": 1, "chi_tieu": "Q cực đại (m³/s)", "gia_tri": round(float(q.max()), 1)},
        {"muc": 1, "chi_tieu": "ngày đạt cực đại", "gia_tri": f"{d.loc[q.idxmax(), 'date']:%Y-%m-%d}"},
        {"muc": 1, "chi_tieu": "hệ số bất đối xứng", "gia_tri": round(float(q.skew()), 2)},
    ]
    for r in out:
        print(f"    {r['chi_tieu']:<24} {r['gia_tri']}")

    fig, ax = plt.subplots(1, 2, figsize=(9, 2.9))
    ax[0].plot(d.date, d.discharge, lw=0.35, color=ACC)
    ax[0].set(title="Lưu lượng ngày, 2010–2026", ylabel="m³/s")
    ax[1].hist(np.log10(q.dropna() + 1), bins=60, color=ACC, edgecolor="white", lw=0.3)
    ax[1].set(title="Phân bố log₁₀(Q+1)", xlabel="log₁₀(m³/s)", ylabel="số ngày")
    out.append({"muc": 1, "chi_tieu": "hình", "gia_tri": save(fig, "eda1_tong_quan.png")})
    return out


def m2_mua_vu(d: pd.DataFrame) -> list[dict]:
    print("\n[2] Tính mùa vụ")
    g = d.groupby(d.date.dt.month).agg(q=("discharge", "median"), r=("rain_basin", "mean"))
    top = g.q.idxmax()
    share = d.loc[d.date.dt.month.isin([9, 10, 11, 12]), "discharge"].sum() / d.discharge.sum()
    out = [
        {"muc": 2, "chi_tieu": "tháng Q trung vị lớn nhất", "gia_tri": int(top)},
        {"muc": 2, "chi_tieu": "Q trung vị tháng đó (m³/s)", "gia_tri": round(float(g.q.max()), 1)},
        {"muc": 2, "chi_tieu": "Q trung vị tháng thấp nhất", "gia_tri": round(float(g.q.min()), 1)},
        {"muc": 2, "chi_tieu": "tỉ lệ dòng chảy tháng 9–12 (%)", "gia_tri": round(float(share) * 100, 1)},
    ]
    for r in out:
        print(f"    {r['chi_tieu']:<32} {r['gia_tri']}")

    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    ax.bar(g.index - 0.2, g.q, width=0.4, color=ACC, label="Q trung vị (m³/s)")
    ax2 = ax.twinx()
    ax2.grid(False)
    ax2.bar(g.index + 0.2, g.r, width=0.4, color=WARN, label="mưa TB (mm/ngày)")
    ax.set(xlabel="tháng", ylabel="m³/s", xticks=range(1, 13), title="Chu kỳ mùa")
    ax2.set_ylabel("mm/ngày")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, framealpha=0.9)
    out.append({"muc": 2, "chi_tieu": "hình", "gia_tri": save(fig, "eda2_mua_vu.png")})
    return out


def m3_lag(d: pd.DataFrame) -> list[dict]:
    """Mục quan trọng nhất: mưa dẫn trước lưu lượng bao nhiêu ngày."""
    print("\n[3] Tương quan mưa – lưu lượng theo độ trễ  ⭐")
    lags = range(0, 8)
    sets = {
        "cả năm": d,
        "mùa lũ (9–12)": d[d.date.dt.month.isin([9, 10, 11, 12])],
        "mùa khô (1–8)": d[~d.date.dt.month.isin([9, 10, 11, 12])],
    }
    basins = ["rain_basin", "rain_thuong", "rain_trung", "rain_ha"]
    out, curves = [], {}

    for name, sub in sets.items():
        cc = []
        for L in lags:
            x = sub["rain_basin"].shift(L)
            v = pd.concat([x, sub["discharge"]], axis=1).dropna()
            cc.append(float(np.corrcoef(v.iloc[:, 0], v.iloc[:, 1])[0, 1]))
        curves[name] = cc
        best = int(np.argmax(cc))
        out += [{"muc": 3, "chi_tieu": f"lag tốt nhất · {name}", "gia_tri": best},
                {"muc": 3, "chi_tieu": f"r tại lag đó · {name}", "gia_tri": round(cc[best], 3)}]
        print(f"    {name:<16} lag tốt nhất = {best} ngày, r = {cc[best]:.3f}")

    print("    theo tiểu lưu vực (cả năm):")
    for b in basins:
        cc = []
        for L in lags:
            v = pd.concat([d[b].shift(L), d["discharge"]], axis=1).dropna()
            cc.append(float(np.corrcoef(v.iloc[:, 0], v.iloc[:, 1])[0, 1]))
        curves[b] = cc
        best = int(np.argmax(cc))
        out += [{"muc": 3, "chi_tieu": f"lag tốt nhất · {b}", "gia_tri": best},
                {"muc": 3, "chi_tieu": f"r tại lag đó · {b}", "gia_tri": round(cc[best], 3)}]
        print(f"      {b:<14} lag = {best}, r = {cc[best]:.3f}")

    fig, ax = plt.subplots(1, 2, figsize=(9, 3))
    for name, st in zip(sets, ["-o", "-s", "-^"]):
        ax[0].plot(lags, curves[name], st, ms=3.5, lw=1.3, label=name)
    ax[0].set(title="Theo mùa", xlabel="độ trễ mưa (ngày)", ylabel="hệ số tương quan")
    ax[0].legend(fontsize=8)
    for b, st in zip(basins, ["-o", "-s", "-^", "-d"]):
        ax[1].plot(lags, curves[b], st, ms=3.5, lw=1.3, label=b.replace("rain_", ""))
    ax[1].set(title="Theo tiểu lưu vực", xlabel="độ trễ mưa (ngày)")
    ax[1].legend(fontsize=8)
    out.append({"muc": 3, "chi_tieu": "hình", "gia_tri": save(fig, "eda3_lag.png")})
    return out


def m4_api(d: pd.DataFrame) -> list[dict]:
    print("\n[4] Mưa tích luỹ và độ ẩm nền")
    d = d.copy()
    for k in (3, 7, 14):
        d[f"r{k}"] = d["rain_basin"].rolling(k, min_periods=k).sum()
    out = []
    for c, lbl in [("rain_basin", "mưa 1 ngày"), ("r3", "mưa 3 ngày"),
                   ("r7", "mưa 7 ngày"), ("r14", "mưa 14 ngày"), ("api", "chỉ số API")]:
        v = d[[c, "discharge"]].dropna()
        r = float(np.corrcoef(v[c], v.discharge)[0, 1])
        out.append({"muc": 4, "chi_tieu": f"r({lbl}, Q)", "gia_tri": round(r, 3)})
        print(f"    r({lbl:<12}, Q) = {r:.3f}")

    hi = d[d.api > d.api.quantile(0.75)]
    lo = d[d.api < d.api.quantile(0.25)]
    big = d.rain_basin.quantile(0.95)
    a = float(hi.loc[hi.rain_basin > big, "discharge"].median())
    b = float(lo.loc[lo.rain_basin > big, "discharge"].median())
    out += [{"muc": 4, "chi_tieu": "Q trung vị khi mưa lớn + nền ẩm", "gia_tri": round(a, 1)},
            {"muc": 4, "chi_tieu": "Q trung vị khi mưa lớn + nền khô", "gia_tri": round(b, 1)},
            {"muc": 4, "chi_tieu": "tỉ số ẩm/khô", "gia_tri": round(a / b, 2)}]
    print(f"    cùng mưa lớn: nền ẩm {a:.0f} vs nền khô {b:.0f} m³/s → gấp {a/b:.2f} lần")

    fig, ax = plt.subplots(figsize=(6.2, 3))
    s = d.dropna(subset=["api", "discharge"])
    ax.scatter(s.api, s.discharge, s=2.5, alpha=0.25, color=ACC, edgecolors="none")
    ax.set(yscale="log", xlabel="chỉ số mưa tích luỹ API (mm)", ylabel="Q (m³/s, log)",
           title="Độ ẩm nền quyết định phản ứng của sông")
    out.append({"muc": 4, "chi_tieu": "hình", "gia_tri": save(fig, "eda4_api.png")})
    return out


def m5_su_kien(d: pd.DataFrame) -> list[dict]:
    print("\n[5] Ba đợt lũ lịch sử")
    ev = pd.read_csv(cfg.ROOT / "data" / "processed" / "flood_events_with_Q.csv")
    ev["peak_date"] = pd.to_datetime(ev["peak_date"])
    pick = ["2020-10b", "2023-11", "2025-10a"]
    sel = ev[ev.event_id.isin(pick)]
    out = []
    fig, axes = plt.subplots(1, 3, figsize=(10, 2.9), sharey=True)
    for ax, (_, r) in zip(axes, sel.iterrows()):
        w = d[(d.date >= r.peak_date - pd.Timedelta(days=12)) &
              (d.date <= r.peak_date + pd.Timedelta(days=8))]
        ax.plot(w.date, w.discharge, color=ACC, lw=1.5)
        ax.axvline(r.peak_date, color=WARN, ls="--", lw=1.2)
        ax.set_title(f"{r.event_id} · H = {r.peak_H_m:.2f} m\nQ đỉnh = {r.peak_Q:.0f} m³/s",
                     fontsize=8.5)
        ax.tick_params(axis="x", rotation=45, labelsize=7)
        out.append({"muc": 5, "chi_tieu": f"{r.event_id} · H (m)", "gia_tri": r.peak_H_m})
        out.append({"muc": 5, "chi_tieu": f"{r.event_id} · Q (m³/s)", "gia_tri": round(r.peak_Q)})
        print(f"    {r.event_id}: H = {r.peak_H_m:.2f} m · Q = {r.peak_Q:.0f} m³/s")
    axes[0].set_ylabel("m³/s")
    out.append({"muc": 5, "chi_tieu": "hình", "gia_tri": save(fig, "eda5_su_kien.png")})
    return out


def m6_cuc_tri(d: pd.DataFrame) -> list[dict]:
    print("\n[6] Phân bố cực trị")
    q = d["discharge"].dropna()
    out = []
    for p in (0.90, 0.95, 0.99, 0.995):
        v = float(q.quantile(p))
        n = int((q >= v).sum())
        out.append({"muc": 6, "chi_tieu": f"phân vị {p:.1%} (m³/s)", "gia_tri": round(v, 1)})
        out.append({"muc": 6, "chi_tieu": f"số ngày ≥ phân vị {p:.1%}", "gia_tri": n})
        print(f"    p{p:.1%} = {v:8.1f} m³/s → {n:4d} ngày ({n/len(q)*100:.1f} %)")

    am = d.assign(nam=d.date.dt.year).groupby("nam").discharge.max().dropna()
    out.append({"muc": 6, "chi_tieu": "đỉnh năm trung vị (m³/s)", "gia_tri": round(float(am.median()), 1)})
    fig, ax = plt.subplots(1, 2, figsize=(9, 2.9))
    ax[0].bar(am.index, am.values, color=ACC)
    ax[0].set(title="Đỉnh lưu lượng từng năm", ylabel="m³/s")
    ax[0].tick_params(axis="x", rotation=45, labelsize=7)
    srt = np.sort(q)[::-1]
    ax[1].plot(np.arange(1, len(srt) + 1) / len(srt) * 100, srt, color=ACC, lw=1.2)
    ax[1].set(xscale="log", yscale="log", xlabel="% số ngày vượt", ylabel="m³/s",
              title="Đường duy trì dòng chảy")
    out.append({"muc": 6, "chi_tieu": "hình", "gia_tri": save(fig, "eda6_cuc_tri.png")})
    return out


def m7_che_do(d: pd.DataFrame) -> list[dict]:
    """Mục này là R21 — kết luận đầy đủ ở docs/FINDINGS_REGIME.md."""
    print("\n[7] Hai chế độ dữ liệu quanh mốc 2022-07")
    a = d.loc[d.date < BREAK, "discharge"].dropna()
    b = d.loc[d.date >= BREAK, "discharge"].dropna()
    out = [
        {"muc": 7, "chi_tieu": "trung vị trước / sau", "gia_tri": f"{a.median():.1f} / {b.median():.1f}"},
        {"muc": 7, "chi_tieu": "p99 trước / sau", "gia_tri": f"{a.quantile(.99):.1f} / {b.quantile(.99):.1f}"},
        {"muc": 7, "chi_tieu": "kết luận", "gia_tri": "không có bằng chứng đổi biên độ — FINDINGS_REGIME.md"},
    ]
    for r in out:
        print(f"    {r['chi_tieu']:<24} {r['gia_tri']}")

    fig, ax = plt.subplots(figsize=(6.2, 3))
    bins = np.linspace(0, 3, 50)
    ax.hist(np.log10(a + 1), bins=bins, alpha=0.55, density=True, color=ACC, label="trước 2022-07")
    ax.hist(np.log10(b + 1), bins=bins, alpha=0.55, density=True, color=WARN, label="sau 2022-07")
    ax.set(xlabel="log₁₀(Q+1)", ylabel="mật độ", title="Hai chế độ gần như trùng nhau")
    ax.legend(fontsize=8)
    out.append({"muc": 7, "chi_tieu": "hình", "gia_tri": save(fig, "eda7_che_do.png")})
    return out


def m8_khong_gian(d: pd.DataFrame) -> list[dict]:
    print("\n[8] Không gian — mưa theo tiểu lưu vực")
    out = []
    cols = ["rain_thuong", "rain_trung", "rain_ha"]
    for c in cols:
        out.append({"muc": 8, "chi_tieu": f"{c} TB (mm/ngày)", "gia_tri": round(float(d[c].mean()), 2)})
        print(f"    {c:<14} TB {d[c].mean():.2f} mm/ngày")
    cm = d[cols + ["discharge"]].corr().round(3)
    for c in cols:
        out.append({"muc": 8, "chi_tieu": f"r({c}, Q)", "gia_tri": float(cm.loc[c, "discharge"])})

    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    im = ax.imshow(cm.values, cmap="BuPu", vmin=0, vmax=1)
    lbl = [c.replace("rain_", "") for c in cols] + ["Q"]
    ax.set(xticks=range(4), yticks=range(4), xticklabels=lbl, yticklabels=lbl,
           title="Tương quan mưa – lưu lượng")
    for i in range(4):
        for j in range(4):
            v = cm.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if v > 0.6 else INK)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.grid(False)
    out.append({"muc": 8, "chi_tieu": "hình", "gia_tri": save(fig, "eda8_khong_gian.png")})
    return out


def main() -> int:
    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d["date"])
    print(f"EDA trên {len(d):,} ngày · {d.date.min():%Y-%m-%d} → {d.date.max():%Y-%m-%d}"
          .replace(",", " "))

    rows: list[dict] = []
    for fn in (m1_tong_quan, m2_mua_vu, m3_lag, m4_api,
               m5_su_kien, m6_cuc_tri, m7_che_do, m8_khong_gian):
        rows += fn(d)

    res = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT, index=False)
    print(f"\n→ {OUT.relative_to(cfg.ROOT)}  ({len(res)} dòng)")
    print(f"→ {FIGS.relative_to(cfg.ROOT)}  (8 hình)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
