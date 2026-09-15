"""Vẽ bản đồ lưu lượng GloFAS trên lưới — công cụ chọn ô sông (FR-D5).

Quét một vùng, lấy lưu lượng trung bình mỗi ô, rồi vẽ heatmap. Mạng lưới sông
của GloFAS sẽ hiện ra: ô trên dòng chảy chính sáng hẳn, ô ngoài sông là NaN.

    python -m src.viz.grid_map

Kết quả: reports/figures/w1_grid_map.png + data/external/grid_scan_region.csv
Dùng cache của openmeteo_flood nên chạy lại rất nhanh.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import config as cfg
from src.ingest.openmeteo_flood import fetch_discharge

# Vùng quét: bao trọn hạ lưu sông Hương và sông Bồ
BOX = {"lat_min": 16.25, "lat_max": 16.75, "lon_min": 107.25, "lon_max": 107.75}
STEP = 0.05
SCAN_START, SCAN_END = "2018-01-01", "2023-12-31"

# Vị trí xấp xỉ 2 trạm thuỷ văn (để đối chiếu, KHÔNG phải toạ độ ô lưới)
STATIONS = {
    "Kim Long (sông Hương)": (16.47, 107.57),
    "Phú Ốc (sông Bồ)": (16.55, 107.47),
}
PLAN_POINT = (16.46, 107.59)  # toạ độ trong kế hoạch gốc — đã biết là sai ô


def scan_region() -> pd.DataFrame:
    lats = np.round(np.arange(BOX["lat_min"], BOX["lat_max"] + 1e-9, STEP), 4)
    lons = np.round(np.arange(BOX["lon_min"], BOX["lon_max"] + 1e-9, STEP), 4)
    total = len(lats) * len(lons)
    print(f"Quét {len(lats)} × {len(lons)} = {total} ô, bước {STEP}° (~5 km)")

    rows, k = [], 0
    for la in lats:
        for lo in lons:
            k += 1
            try:
                d = fetch_discharge(float(la), float(lo), SCAN_START, SCAN_END)
                q = d["discharge"]
                rows.append({"lat": float(la), "lon": float(lo),
                             "q_mean": q.mean(), "q_max": q.max()})
            except Exception as e:
                rows.append({"lat": float(la), "lon": float(lo),
                             "q_mean": np.nan, "q_max": np.nan})
                print(f"  [{k}/{total}] ({la}, {lo}) lỗi: {e}")
            if k % 20 == 0:
                print(f"  …{k}/{total}")

    df = pd.DataFrame(rows)
    dest = cfg.DATA_EXTERNAL / "grid_scan_region.csv"
    df.to_csv(dest, index=False)
    print(f"→ {dest}")
    return df


def plot(df: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    piv_mean = df.pivot(index="lat", columns="lon", values="q_mean")
    piv_max = df.pivot(index="lat", columns="lon", values="q_max")

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1], hspace=0.28, wspace=0.18)

    for ax, piv, title in [
        (fig.add_subplot(gs[0, 0]), piv_mean, "Lưu lượng TRUNG BÌNH 2018–2023"),
        (fig.add_subplot(gs[0, 1]), piv_max, "Lưu lượng ĐỈNH 2018–2023"),
    ]:
        vals = piv.values
        finite = vals[np.isfinite(vals) & (vals > 0)]
        norm = LogNorm(vmin=max(finite.min(), 0.1), vmax=finite.max()) if finite.size else None
        im = ax.pcolormesh(piv.columns, piv.index, vals, cmap="viridis",
                           norm=norm, shading="nearest")
        ax.set_facecolor("#d9d9d9")  # ô NaN = ngoài mạng sông GloFAS
        fig.colorbar(im, ax=ax, label="m³/s (thang log)")

        for name, (sla, slo) in STATIONS.items():
            ax.plot(slo, sla, "o", mfc="none", mec="white", mew=2, ms=13)
            ax.annotate(name.split(" (")[0], (slo, sla), color="white",
                        fontsize=9, fontweight="bold",
                        xytext=(6, 6), textcoords="offset points")
        ax.plot(PLAN_POINT[1], PLAN_POINT[0], "x", color="#ff4d4d", mew=3, ms=14)
        ax.annotate("toạ độ KH gốc", (PLAN_POINT[1], PLAN_POINT[0]),
                    color="#ff4d4d", fontsize=9, fontweight="bold",
                    xytext=(6, -14), textcoords="offset points")

        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("Kinh độ")
        ax.set_ylabel("Vĩ độ")
        ax.set_aspect("equal")

    # --- Bảng xếp hạng ---
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.axis("off")
    top = df.dropna(subset=["q_mean"]).nlargest(12, "q_mean")
    lines = [f"{'lat':>7} {'lon':>8} {'q_mean':>9} {'q_max':>10}", "-" * 38]
    for _, r in top.iterrows():
        lines.append(f"{r.lat:7.2f} {r.lon:8.2f} {r.q_mean:9.1f} {r.q_max:10.1f}")
    n_river = int(df["q_mean"].notna().sum())
    n_uniq = df["q_mean"].round(1).nunique()
    lines += ["", f"O co du lieu song : {n_river}/{len(df)}",
              f"O ngoai mang song  : {len(df) - n_river}",
              f"Gia tri q_mean khac nhau: {n_uniq}",
              "(trung lap = nhieu diem lay mau roi vao",
              " cung mot o GloFAS goc)"]
    # Không dùng monospace cho tiêu đề: font monospace mặc định thiếu glyph tiếng Việt
    ax3.text(0, 1, "TOP 12 Ô LƯU LƯỢNG LỚN NHẤT", fontsize=11,
             fontweight="bold", va="top")
    ax3.text(0, 0.90, "\n".join(lines), fontsize=9.5, va="top", family="monospace")

    # --- Chuỗi thời gian so sánh ---
    ax4 = fig.add_subplot(gs[1, 1])
    best = df.dropna(subset=["q_mean"]).nlargest(1, "q_mean").iloc[0]
    compare = [(PLAN_POINT, "#ff4d4d", "KH gốc (16.46, 107.59)"),
               ((float(best.lat), float(best.lon)), "#1d4ed8",
                f"Ô lớn nhất ({best.lat:.2f}, {best.lon:.2f})")]
    for (la, lo), color, label in compare:
        d = fetch_discharge(la, lo, "2020-09-01", "2020-12-15")
        ax4.plot(d["date"], d["discharge"], color=color, lw=1.6, label=label)
    ax4.set_yscale("log")
    ax4.set_title("Đợt lũ 10/2020 — thang log", fontsize=11, fontweight="bold")
    ax4.set_ylabel("m³/s")
    ax4.legend(fontsize=8.5)
    ax4.grid(alpha=0.3)
    ax4.tick_params(axis="x", labelrotation=30, labelsize=8)

    fig.suptitle("GloFAS — chọn ô lưới cho sông Hương / sông Bồ  (FR-D5)",
                 fontsize=14, fontweight="bold")
    dest = cfg.FIGURES / "w1_grid_map.png"
    fig.savefig(dest, dpi=130, bbox_inches="tight")
    print(f"→ {dest}")


if __name__ == "__main__":
    cfg.REQUEST_SLEEP_S = 0.35  # quét nhiều ô, nới nhịp cho nhanh
    plot(scan_region())
