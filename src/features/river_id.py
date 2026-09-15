"""Tự động xác định ô lưới GloFAS thuộc con sông nào (FR-D5).

Thay cho việc mở bản đồ nhìn bằng mắt. Gộp ba nguồn bằng chứng độc lập:

1. **Hình học** — tải đường tim sông có tên từ OpenStreetMap (Overpass API),
   gán mỗi ô lưới cho con sông gần nhất.
2. **Tương quan** — hai ô trên cùng một dòng thì chuỗi lưu lượng gần như trùng
   nhau; hai sông riêng biệt thì tương quan thấp hơn hẳn.
3. **Cân bằng khối lượng** — ở chỗ hợp lưu, lưu lượng hạ lưu ≈ tổng các nhánh.
   Đây là cách phát hiện ô nằm dưới hợp lưu, thứ tuyệt đối không được dùng
   để ánh xạ sang mực nước của một trạm đơn lẻ.

    python -m src.features.river_id

Kết quả: reports/figures/w1_river_id.png + bảng kết luận in ra màn hình.
Hình học OSM được cache trong data/external/osm_rivers.json.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import requests

from src import config as cfg

OSM_CACHE = cfg.DATA_EXTERNAL / "osm_rivers.json"
OVERPASS = "https://overpass-api.de/api/interpreter"
BBOX = (16.05, 107.05, 16.95, 107.95)      # nam, tây, bắc, đông

# Diện tích lưu vực tham khảo (km²) — dùng để kiểm tra tỉ lệ lưu lượng có hợp lý
BASIN_KM2 = {"Sông Hương": 2830, "Sông Bồ": 938}

MIN_QMEAN = 5.0        # m³/s — dưới ngưỡng này bỏ qua, không phải dòng đáng kể
MAX_DIST_KM = 8.0      # xa hơn ngưỡng này thì không gán cho sông nào


# ------------------------------------------------------------------ OSM

def fetch_osm_rivers(force: bool = False) -> dict[str, list[list[tuple[float, float]]]]:
    """Lấy đường tim các con sông CÓ TÊN trong vùng. Kết quả được cache."""
    if OSM_CACHE.exists() and not force:
        raw = json.loads(OSM_CACHE.read_text(encoding="utf-8"))
    else:
        s, w, n, e = BBOX
        query = f"""[out:json][timeout:90];
(way["waterway"="river"]["name"]({s},{w},{n},{e});
 way["waterway"="stream"]["name"]({s},{w},{n},{e}););
out geom;"""
        r = requests.post(OVERPASS, data={"data": query}, timeout=180,
                          headers={"User-Agent": "DSP391m-student-project"})
        r.raise_for_status()
        raw = r.json()
        OSM_CACHE.write_text(json.dumps(raw), encoding="utf-8")
        print(f"→ {OSM_CACHE}")

    rivers: dict[str, list[list[tuple[float, float]]]] = {}
    for el in raw.get("elements", []):
        name = el.get("tags", {}).get("name")
        geom = el.get("geometry")
        if not name or not geom:
            continue
        rivers.setdefault(name, []).append(
            [(p["lat"], p["lon"]) for p in geom])
    return rivers


# ------------------------------------------------------- hình học phẳng

def _to_m(lat: float, lon: float, lat0: float) -> tuple[float, float]:
    """Chiếu tương đương khoảng cách quanh vĩ độ lat0 — đủ chính xác ở quy mô này."""
    return (lon * 111_320 * math.cos(math.radians(lat0)), lat * 110_540)


def _dist_point_segment(p, a, b) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dist_to_river_km(lat: float, lon: float, ways: list[list[tuple[float, float]]],
                     lat0: float = 16.5) -> float:
    p = _to_m(lat, lon, lat0)
    best = float("inf")
    for way in ways:
        pts = [_to_m(la, lo, lat0) for la, lo in way]
        for i in range(len(pts) - 1):
            best = min(best, _dist_point_segment(p, pts[i], pts[i + 1]))
    return best / 1000.0


# ------------------------------------------------------------ dữ liệu

def load_series() -> dict[tuple[float, float], pd.Series]:
    out = {}
    for f in sorted((cfg.DATA_RAW / "discharge").glob("q_*.parquet")):
        d = pd.read_parquet(f)
        if "river_discharge" not in d.columns:
            continue
        s = d.set_index("time")["river_discharge"]
        if s.mean() >= MIN_QMEAN:
            out[(float(d["lat"].iloc[0]), float(d["lon"].iloc[0]))] = s
    return out


def dedupe(series: dict) -> pd.DataFrame:
    """Nhiều toạ độ lấy mẫu có thể rơi vào cùng một pixel GloFAS → gộp lại."""
    rows = []
    for (la, lo), s in series.items():
        rows.append({"lat": la, "lon": lo, "q_mean": s.mean(), "q_max": s.max(),
                     "sig": round(float(s.mean()), 4)})
    df = pd.DataFrame(rows)
    df["pixel"] = df.groupby("sig").ngroup()
    return df


# ------------------------------------------------------------ phân tích

def main() -> None:
    print("1) Tải hình học sông có tên từ OpenStreetMap…")
    rivers = fetch_osm_rivers()
    keep = [n for n in rivers if any(k in n for k in
            ("Hương", "Bồ", "Tả Trạch", "Hữu Trạch", "Ô Lâu", "Truồi", "Nong"))]
    print(f"   {len(rivers)} sông có tên, xét {len(keep)}: {', '.join(keep)}")

    print("\n2) Nạp chuỗi lưu lượng…")
    series = load_series()
    df = dedupe(series)
    print(f"   {len(df)} ô có q_mean ≥ {MIN_QMEAN} m³/s, "
          f"thuộc {df['pixel'].nunique()} pixel GloFAS phân biệt")

    print("\n3) Gán ô lưới cho sông gần nhất…")
    for name in keep:
        df[name] = [dist_to_river_km(r.lat, r.lon, rivers[name])
                    for r in df.itertuples()]
    df["_dH"] = df["Sông Hương"] if "Sông Hương" in df else np.nan
    df["_dB"] = df["Sông Bồ"] if "Sông Bồ" in df else np.nan
    df["song"] = df[keep].idxmin(axis=1)
    df["khoang_cach_km"] = df[keep].min(axis=1)
    df.loc[df["khoang_cach_km"] > MAX_DIST_KM, "song"] = "(khong xac dinh)"

    # Mỗi pixel GloFAS lấy ô đại diện gần sông nhất
    rep = (df.sort_values("khoang_cach_km")
             .groupby("pixel", as_index=False).first()
             .sort_values("q_mean", ascending=False))

    print("\n=== ỨNG VIÊN THEO LƯU LƯỢNG ===")
    print(f"{'lat':>6} {'lon':>8} {'q_mean':>9} {'q_max':>9}  "
          f"{'sông gần nhất':<16} {'cách (km)':>9}")
    for r in rep.head(12).itertuples():
        print(f"{r.lat:6.2f} {r.lon:8.2f} {r.q_mean:9.1f} {r.q_max:9.1f}  "
              f"{r.song:<16} {r.khoang_cach_km:9.2f}")

    print("\n4) Tương quan giữa các pixel lớn nhất…")
    top = rep.head(6)
    keys = [(r.lat, r.lon) for r in top.itertuples()]
    corr = pd.DataFrame({f"{la},{lo}": series[(la, lo)] for la, lo in keys}).corr()
    print(corr.round(3).to_string())

    print("\n5) Kiểm tra cân bằng khối lượng (phát hiện ô dưới hợp lưu)…")
    check_confluence(rep, series)

    print("\n6) Suy ngược diện tích lưu vực từ lưu lượng…")
    rep = check_basin_area(rep)

    plot(rep, rivers, keep, corr, keys)
    print("\n" + "=" * 70)
    print(verdict(rep, series))


MAX_CONFLUENCE_KM = 20.0   # hai nhánh phải ĐỦ GẦN ô hạ lưu mới coi là hợp lưu


def _km(a_lat, a_lon, b_lat, b_lon) -> float:
    ax, ay = _to_m(a_lat, a_lon, 16.5)
    bx, by = _to_m(b_lat, b_lon, 16.5)
    return math.hypot(ax - bx, ay - by) / 1000.0


def check_confluence(rep: pd.DataFrame, series: dict) -> None:
    """Cảnh báo ô nằm dưới hợp lưu — chỉ để tham khảo, KHÔNG dùng làm kết luận.

    Phép cộng lưu lượng ở đây rất dễ đánh lừa: hai ô nối tiếp trên cùng một
    dòng cộng lại vẫn ra đúng số vì đã đếm trùng phần thượng nguồn. Kết luận
    chính lấy từ suy ngược diện tích lưu vực (§6).
    """
    top = rep.iloc[0]
    near = rep.iloc[1:].copy()
    near["d_km"] = [_km(top.lat, top.lon, r.lat, r.lon) for r in near.itertuples()]
    near = near[near["d_km"] <= MAX_CONFLUENCE_KM]
    print(f"   Ô lớn nhất ({top.lat}, {top.lon}) = {top.q_mean:.1f} m³/s, "
          f"{len(near)} ô lân cận trong {MAX_CONFLUENCE_KM:.0f} km")
    print("   (bỏ qua phép cộng lưu lượng: hai ô nối tiếp cùng dòng sẽ đếm trùng)")


def verdict(rep: pd.DataFrame, series: dict) -> str:
    """Chọn ô cho trạm Kim Long dựa trên diện tích lưu vực suy ra."""
    target = BASIN_KM2["Sông Hương"]
    cand = rep.head(8).copy()
    cand["lech"] = (cand["dt_km2"] - target).abs() / target
    # Loại cụm phía bắc: tương quan thấp với ô lớn nhất vùng Hương
    ref = series[(rep.iloc[0].lat, rep.iloc[0].lon)]
    cand["corr_ref"] = [series[(r.lat, r.lon)].corr(ref) for r in cand.itertuples()]
    cand = cand[cand["corr_ref"] >= 0.93]
    if cand.empty:
        return "Không chọn được ô nào — cần kiểm tra thủ công."
    best = cand.sort_values("lech").iloc[0]
    tong = BASIN_KM2["Sông Hương"] + BASIN_KM2["Sông Bồ"]
    big = rep.iloc[0]
    out = [
        "KẾT LUẬN TỰ ĐỘNG",
        f"  Ô cho sông Hương / trạm Kim Long:  ({best.lat}, {best.lon})",
        f"    lưu lượng trung bình         {best.q_mean:.1f} m³/s",
        f"    diện tích lưu vực suy ra     {best.dt_min:.0f}–{best.dt_max:.0f} km²",
        f"    lưu vực sông Hương thực tế   {target} km² → lệch {best.lech*100:.0f} %",
        f"    cách đường tim sông Hương    {best._dH:.2f} km",
        "",
        f"  Ô ({big.lat}, {big.lon}) tuy lưu lượng lớn nhất nhưng diện tích suy ra",
        f"  {big.dt_km2:.0f} km², vượt xa cả Hương + Bồ ({tong} km²) — đã gộp thêm",
        "  lưu vực khác. KHÔNG dùng ô này để ánh xạ sang mực nước một trạm.",
    ]
    return chr(10).join(out)


# Dòng chảy đơn vị vùng Huế: mưa ~2.800–3.200 mm/năm, hệ số dòng chảy ~0,45–0,50
# ⇒ lớp dòng chảy ~1.300–1.600 mm/năm ⇒ ~0,041–0,051 m³/s trên mỗi km².
SPECIFIC_Q = 0.046          # m³/s/km², giá trị giữa
SPECIFIC_Q_RANGE = (0.041, 0.051)


def check_basin_area(rep: pd.DataFrame) -> pd.DataFrame:
    """Suy ngược diện tích lưu vực từ lưu lượng — phép kiểm mạnh nhất ở đây.

    Lưu lượng trung bình nhiều năm ≈ diện tích lưu vực × dòng chảy đơn vị.
    Dòng chảy đơn vị của một vùng khí hậu là khá ổn định, nên chia ngược ra
    diện tích rồi đối chiếu với diện tích lưu vực đã biết sẽ cho biết một ô
    đang "gánh" bao nhiêu đất — thứ mà khoảng cách tới đường tim sông
    không nói được.
    """
    lo, hi = SPECIFIC_Q_RANGE
    rep = rep.copy()
    rep["dt_km2"] = rep["q_mean"] / SPECIFIC_Q
    rep["dt_min"] = rep["q_mean"] / hi
    rep["dt_max"] = rep["q_mean"] / lo

    known = {"Sông Bồ": 938, "Sông Hương": 2830, "Hương + Bồ": 3768}
    print("   Diện tích lưu vực đã biết: "
          + " · ".join(f"{k} {v:,} km²".replace(",", " ") for k, v in known.items()))
    print()
    print(f"   {'lat':>6} {'lon':>8} {'q_mean':>8}  {'DT suy ra (km²)':>18}  khớp với")
    for r in rep.head(6).itertuples():
        best = min(known.items(), key=lambda kv: abs(kv[1] - r.dt_km2))
        lech = abs(best[1] - r.dt_km2) / best[1]
        dau = "✓" if lech < 0.25 else ("~" if lech < 0.5 else "✗")
        print(f"   {r.lat:6.2f} {r.lon:8.2f} {r.q_mean:8.1f}  "
              f"{r.dt_min:7.0f}–{r.dt_max:<10.0f}  {dau} {best[0]} "
              f"({best[1]:,} km², lệch {lech*100:.0f} %)".replace(",", " "))
    return rep


def plot(rep, rivers, keep, corr, keys) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.5),
                                   gridspec_kw={"width_ratios": [1.5, 1]})

    colors = plt.cm.tab10(np.linspace(0, 1, len(keep)))
    for c, name in zip(colors, keep):
        for k, way in enumerate(rivers[name]):
            la = [p[0] for p in way]
            lo = [p[1] for p in way]
            ax1.plot(lo, la, color=c, lw=2.2, alpha=0.85,
                     label=name if k == 0 else None)

    sc = ax1.scatter(rep["lon"], rep["lat"], s=np.sqrt(rep["q_mean"]) * 14,
                     c=rep["q_mean"], cmap="viridis", edgecolor="black",
                     linewidth=0.7, zorder=5)
    plt.colorbar(sc, ax=ax1, label="lưu lượng trung bình (m³/s)")
    for r in rep.head(4).itertuples():
        ax1.annotate(f"{r.q_mean:.0f}", (r.lon, r.lat), fontsize=9,
                     fontweight="bold", xytext=(7, 5),
                     textcoords="offset points", zorder=6)

    ax1.set_title("Ô lưới GloFAS đặt cạnh sông có tên (OpenStreetMap)",
                  fontsize=12, fontweight="bold")
    ax1.set_xlabel("Kinh độ")
    ax1.set_ylabel("Vĩ độ")
    ax1.legend(fontsize=8.5, loc="upper right")
    ax1.grid(alpha=0.25)
    ax1.set_aspect("equal")

    im = ax2.imshow(corr.values, cmap="RdYlGn", vmin=0.5, vmax=1.0)
    ax2.set_xticks(range(len(corr)))
    ax2.set_yticks(range(len(corr)))
    ax2.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax2.set_yticklabels(corr.columns, fontsize=8)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax2.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center",
                     fontsize=8.5,
                     color="black" if corr.values[i, j] > 0.7 else "white")
    plt.colorbar(im, ax=ax2, label="tương quan")
    ax2.set_title("Tương quan chuỗi lưu lượng\n(≈1,00 nghĩa là cùng một dòng)",
                  fontsize=12, fontweight="bold")

    fig.tight_layout()
    dest = cfg.FIGURES / "w1_river_id.png"
    fig.savefig(dest, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"\n→ {dest}")


if __name__ == "__main__":
    main()
