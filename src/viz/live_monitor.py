"""Màn hình theo dõi crawl, dark mode, tự làm mới — mở bằng Edge là xem được.

    python -m src.viz.live_monitor            # vòng lặp, vẽ lại mỗi 60 giây
    python -m src.viz.live_monitor --once     # vẽ một lần rồi thoát

Mở `reports/live/index.html`, trang tự reload 30 giây một lần.

Số liệu được nướng thẳng vào HTML (không dùng fetch), vì trang chạy qua `file://`
sẽ bị Edge chặn CORS nếu đọc JSON rời. Chỉ đọc file, không gọi API, nên chạy
song song với crawler vô hại.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src import config as cfg
from src.ingest import crawl_all as ca

LIVE = cfg.ROOT / "reports" / "live"
LIVE.mkdir(parents=True, exist_ok=True)

# Bảng màu tối, dùng chung cho cả biểu đồ lẫn trang HTML
BG = "#0f172a"
PANEL = "#1e293b"
GRID = "#334155"
FG = "#e2e8f0"
MUTED = "#94a3b8"

PHASE_LABEL = {
    "discharge_probe": "Quét mạng sông (dải ngắn, mọi ô)",
    "rain_daily": "Mưa ngày ERA5 2010–2026",
    "discharge_full": "Lưu lượng 1984–2026 (ô có sông)",
    "fc_rain": "Mưa dự báo lưu trữ 2022–nay",
    "rain_hourly": "Mưa giờ ERA5 2015–2026",
}
PHASE_COLOR = {"discharge_probe": "#38bdf8", "rain_daily": "#22c55e",
               "discharge_full": "#3b82f6", "fc_rain": "#f59e0b",
               "rain_hourly": "#a855f7"}


def read_progress() -> pd.DataFrame:
    if not ca.PROGRESS.exists():
        return pd.DataFrame()
    rows = []
    for line in ca.PROGRESS.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue          # dòng đang ghi dở — bỏ qua, lần sau có
    df = pd.DataFrame(rows)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    return df


def phase_counts() -> dict[str, tuple[int, int]]:
    out = {}
    for name in ca.DEFAULT_PHASES:
        tasks = ca.PHASES[name]()
        out[name] = (sum(t["dest"].exists() for t in tasks), len(tasks))
    return out


def load_discharge_grid() -> pd.DataFrame:
    """Gộp cả ô probe lẫn ô đã lấy chuỗi đầy đủ; bản đầy đủ được ưu tiên."""
    rows = {}
    for sub, pat, full in (("discharge_probe", "qp_*.parquet", False),
                           ("discharge", "q_*.parquet", True)):
        for f in sorted((cfg.DATA_RAW / sub).glob(pat)):
            try:
                d = pd.read_parquet(f, columns=["river_discharge", "lat", "lon"])
            except Exception:
                continue
            q = d["river_discharge"]
            key = (float(d["lat"].iloc[0]), float(d["lon"].iloc[0]))
            rows[key] = {"lat": key[0], "lon": key[1], "q_mean": q.mean(),
                         "q_max": q.max(), "full": full}
    return pd.DataFrame(list(rows.values()))


def load_rain_grid() -> pd.DataFrame:
    rows = []
    for f in sorted((cfg.DATA_RAW / "rain_daily").glob("rd_*.parquet")):
        try:
            d = pd.read_parquet(f, columns=["precipitation_sum", "lat", "lon"])
        except Exception:
            continue
        rows.append({"lat": d["lat"].iloc[0], "lon": d["lon"].iloc[0],
                     "rain_year": d["precipitation_sum"].mean() * 365.25})
    return pd.DataFrame(rows)


def dir_size_mb(p: Path) -> float:
    return sum(f.stat().st_size for f in p.rglob("*.parquet")) / 1e6 if p.exists() else 0.0


def _dark(ax, title: str = "") -> None:
    ax.set_facecolor(PANEL)
    for sp in ax.spines.values():
        sp.set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.label.set_color(MUTED)
    ax.xaxis.label.set_color(MUTED)
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold", color=FG)


def render(counts, prog, disc, rain) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    fig = plt.figure(figsize=(16, 7.2), facecolor=BG)
    gs = fig.add_gridspec(2, 3, hspace=0.42, wspace=0.26)

    # ---- Bản đồ lưu lượng (lớn dần theo tiến độ crawl) ----
    ax = fig.add_subplot(gs[:, 0])
    if len(disc) > 3:
        piv = disc.pivot_table(index="lat", columns="lon", values="q_mean")
        v = piv.values
        fin = v[np.isfinite(v) & (v > 0)]
        norm = LogNorm(vmin=max(fin.min(), 0.05), vmax=fin.max()) if fin.size else None
        im = ax.pcolormesh(piv.columns, piv.index, v, cmap="viridis",
                           norm=norm, shading="nearest")
        ax.set_facecolor("#1f2937")
        cb = fig.colorbar(im, ax=ax, label="m³/s", fraction=0.046, pad=0.04)
        cb.ax.yaxis.label.set_color(MUTED)
        cb.ax.tick_params(colors=MUTED, labelsize=8)
        cb.outline.set_edgecolor(GRID)
        top = disc.dropna(subset=["q_mean"]).nlargest(1, "q_mean")
        if len(top):
            r = top.iloc[0]
            ax.plot(r.lon, r.lat, "*", color="#f87171", ms=18, mec="white", mew=1)
        ax.set_aspect("equal")
    else:
        ax.text(.5, .5, "chờ dữ liệu…", ha="center", va="center", color=MUTED)
    _nfull = int(disc["full"].sum()) if len(disc) and "full" in disc else 0
    _dark(ax, f"Mạng sông GloFAS — {len(disc)} ô · {_nfull} ô có chuỗi 42 năm")
    ax.set_xlabel("Kinh độ"); ax.set_ylabel("Vĩ độ")

    # ---- Bản đồ mưa ----
    ax = fig.add_subplot(gs[0, 1])
    if len(rain) > 3:
        piv = rain.pivot_table(index="lat", columns="lon", values="rain_year")
        im = ax.pcolormesh(piv.columns, piv.index, piv.values,
                           cmap="YlGnBu", shading="nearest")
        cb = fig.colorbar(im, ax=ax, label="mm/năm", fraction=0.046, pad=0.04)
        cb.ax.yaxis.label.set_color(MUTED)
        cb.ax.tick_params(colors=MUTED, labelsize=8)
        cb.outline.set_edgecolor(GRID)
        ax.set_aspect("equal")
    else:
        ax.text(.5, .5, "chờ dữ liệu…", ha="center", va="center", color=MUTED)
    _dark(ax, f"Mưa trung bình năm — {len(rain)} điểm")

    # ---- Tốc độ crawl ----
    tasks = prog[prog["kind"].notna()] if "kind" in prog else pd.DataFrame()
    ax = fig.add_subplot(gs[0, 2])
    if len(tasks) > 5:
        per = tasks.set_index("ts").resample("2min").size() / 2
        ax.plot(per.index, per.values, color="#3b82f6", lw=1.8)
        ax.fill_between(per.index, per.values, alpha=0.3, color="#3b82f6")
        ax.grid(alpha=0.18, color=GRID)
        ax.tick_params(axis="x", labelrotation=25)
    else:
        ax.text(.5, .5, "chờ dữ liệu…", ha="center", va="center", color=MUTED)
    _dark(ax, "Tốc độ (task/phút)")

    # ---- Dung lượng tích luỹ ----
    ax = fig.add_subplot(gs[1, 1])
    if len(tasks) > 5 and "total_bytes" in tasks:
        ax.plot(tasks["ts"], tasks["total_bytes"] / 1e6, color="#22c55e", lw=1.8)
        ax.fill_between(tasks["ts"], tasks["total_bytes"] / 1e6, alpha=0.25, color="#22c55e")
        ax.grid(alpha=0.18, color=GRID)
        ax.tick_params(axis="x", labelrotation=25)
    else:
        ax.text(.5, .5, "chờ dữ liệu…", ha="center", va="center", color=MUTED)
    _dark(ax, "Dữ liệu tải về (MB)")

    # ---- Đỉnh lũ từng năm ở ô lớn nhất ----
    ax = fig.add_subplot(gs[1, 2])
    done = False
    if len(disc):
        top = disc.dropna(subset=["q_mean"]).nlargest(1, "q_mean")
        if len(top):
            r = top.iloc[0]
            f = cfg.DATA_RAW / "discharge" / f"q_{r.lat}_{r.lon}.parquet"
            if f.exists():
                d = pd.read_parquet(f)
                d["time"] = pd.to_datetime(d["time"])
                yr = d.set_index("time")["river_discharge"].resample("YE").max()
                ax.bar(yr.index.year, yr.values, color="#3b82f6", width=0.85)
                ax.grid(alpha=0.18, color=GRID, axis="y")
                _dark(ax, f"Đỉnh lũ năm — ô ({r.lat}, {r.lon})")
                done = True
    if not done:
        ax.text(.5, .5, "chờ dữ liệu…", ha="center", va="center", color=MUTED)
        _dark(ax, "Đỉnh lũ từng năm")

    fig.savefig(LIVE / "monitor.png", dpi=105, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    # ---- Số liệu trả về cho HTML ----
    st = {"phases": [], "rate": 0.0, "eta_h": 0.0, "done": 0, "remain": 0, "weight": 0,
          "mb": 0.0, "disk_mb": dir_size_mb(cfg.DATA_RAW), "free_gb": ca._free_gb(),
          "rl": 0, "fail": 0, "sleep": "-", "started": "-", "last": "-", "elapsed": 0}
    for n, (d, t) in counts.items():
        st["phases"].append({"key": n, "label": PHASE_LABEL[n], "color": PHASE_COLOR[n],
                             "done": d, "total": t,
                             "pct": round(d / t * 100, 1) if t else 0})
    st["done"] = sum(d for d, _ in counts.values())
    st["remain"] = sum(t - d for d, t in counts.values())
    if len(tasks):
        el = (tasks["ts"].max() - tasks["ts"].min()).total_seconds() / 60
        st["elapsed"] = round(el)
        st["rate"] = round(len(tasks) / el, 1) if el > 0 else 0
        st["eta_h"] = round(st["remain"] / st["rate"] / 60, 1) if st["rate"] else 0
        last = tasks.iloc[-1]
        st.update(weight=int(last.get("weight", 0) or 0),
                  mb=round(float(last.get("total_bytes", 0)) / 1e6),
                  rl=int(last.get("rl", 0)), fail=int(last.get("fail", 0)),
                  sleep=last.get("sleep", "-"),
                  started=f"{tasks['ts'].min():%H:%M:%S}",
                  last=f"{tasks['ts'].max():%H:%M:%S}")
    return st


def build_html(st: dict) -> str:
    bars = "".join(
        f'''<div class="ph">
      <div class="ph-top"><span>{p["label"]}</span>
        <span class="ph-n">{p["done"]}/{p["total"]} · {p["pct"]:.0f}%</span></div>
      <div class="track"><div class="fill" style="width:{p["pct"]}%;background:{p["color"]}"></div></div>
    </div>''' for p in st["phases"])

    tiles = [
        ("Task xong", f'{st["done"]}', "#22c55e"),
        ("Còn lại", f'{st["remain"]}', "#f59e0b"),
        ("Tốc độ", f'{st["rate"]}<small>/phút</small>', "#3b82f6"),
        ("Còn khoảng", f'{st["eta_h"]}<small>giờ</small>', "#a855f7"),
        ("Tải về", f'{st["mb"]}<small>MB</small>', "#06b6d4"),
        ("Trên đĩa", f'{st["disk_mb"]:.0f}<small>MB</small>', "#06b6d4"),
        ("Quota đã dùng", f'{st["weight"]:,}'.replace(",", " "), "#f59e0b"),
        ("Lỗi 429", f'{st["rl"]}', "#f87171" if st["rl"] else "#64748b"),
        ("Thất bại", f'{st["fail"]}', "#f87171" if st["fail"] else "#64748b"),
    ]
    tile_html = "".join(
        f'<div class="tile"><div class="k">{k}</div>'
        f'<div class="v" style="color:{c}">{v}</div></div>' for k, v, c in tiles)

    return f"""<!doctype html>
<html lang="vi"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<meta name="color-scheme" content="dark">
<title>DSP391m — theo dõi crawl</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:{BG};color:{FG};
 font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
header{{padding:14px 20px;background:{PANEL};border-bottom:1px solid {GRID};
 display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}}
h1{{font-size:15px;margin:0;letter-spacing:.2px}}
.live{{display:inline-block;width:8px;height:8px;border-radius:50%;
 background:#22c55e;margin-right:7px;animation:p 1.6s infinite}}
@keyframes p{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
.meta{{font-size:12px;color:{MUTED}}}
.wrap{{padding:16px;max-width:1500px;margin:0 auto}}
.tiles{{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));
 margin-bottom:16px}}
.tile{{background:{PANEL};border:1px solid {GRID};border-radius:10px;padding:11px 13px}}
.k{{font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:.6px}}
.v{{font-size:23px;font-weight:700;margin-top:3px}}
.v small{{font-size:12px;font-weight:500;color:{MUTED};margin-left:3px}}
.card{{background:{PANEL};border:1px solid {GRID};border-radius:12px;
 padding:15px 17px;margin-bottom:16px}}
.ph{{margin-bottom:13px}} .ph:last-child{{margin-bottom:0}}
.ph-top{{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:5px}}
.ph-n{{color:{MUTED};font-variant-numeric:tabular-nums}}
.track{{height:8px;background:#0b1220;border-radius:5px;overflow:hidden}}
.fill{{height:100%;border-radius:5px;transition:width .6s ease}}
img{{width:100%;border-radius:12px;border:1px solid {GRID};display:block}}
.note{{margin-top:14px;font-size:12.5px;color:{MUTED};
 border-left:3px solid #3b82f6;padding-left:12px}}
code{{background:#0b1220;padding:2px 6px;border-radius:4px;font-size:12px;color:#93c5fd}}
@media(max-width:600px){{.v{{font-size:19px}}}}
</style></head><body>
<header>
  <h1><span class="live"></span>DSP391m — theo dõi crawl dữ liệu</h1>
  <span class="meta">bắt đầu {st["started"]} · mới nhất {st["last"]} ·
   chạy {st["elapsed"]} phút · nhịp gọi {st["sleep"]}s · đĩa còn {st["free_gb"]:.1f} GB
   · tự làm mới 30s</span>
</header>
<div class="wrap">
  <div class="tiles">{tile_html}</div>
  <div class="card">{bars}</div>
  <img src="monitor.png?t={int(time.time())}" alt="Biểu đồ theo dõi crawl">
  <p class="note">
    Trang chỉ đọc file, không gọi API. Crawler dừng lúc nào cũng được — mỗi task
    ghi một Parquet riêng, chạy lại <code>python -m src.ingest.crawl_all</code>
    sẽ bỏ qua phần đã có. Dữ liệu thô ở <code>data/raw/</code>, nhật ký ở
    <code>data/raw/_progress.jsonl</code>.
  </p>
</div></body></html>
"""


def cycle() -> None:
    st = render(phase_counts(), read_progress(), load_discharge_grid(), load_rain_grid())
    (LIVE / "index.html").write_text(build_html(st), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    p.add_argument("--every", type=int, default=60)
    args = p.parse_args()

    while True:
        try:
            cycle()
            print(f"[{datetime.now():%H:%M:%S}] đã vẽ lại", flush=True)
        except Exception as e:                     # không bao giờ được chết
            print(f"[{datetime.now():%H:%M:%S}] lỗi vẽ: {e}", flush=True)
        if args.once:
            break
        time.sleep(args.every)


if __name__ == "__main__":
    main()
