"""Trang kể chuyện có chuyển động — "nhóm đang làm gì" trong 6 cảnh, tiếng Việt.

    python -m src.viz.explainer

Sinh hai file trong `reports/explainer/`:

* `flood_story.html`        — bản để publish thành Artifact (không có thẻ html/head)
* `flood_story_local.html`  — bản đầy đủ, mở thẳng bằng trình duyệt khi thuyết trình

Mọi con số và mọi điểm trên hình đều lấy từ dữ liệu thật của dự án:
mưa từng ô lưới, lưu lượng, 361 ô dò, và dự báo LightGBM ngoài mẫu cho trận
lũ tháng 10/2025 (nằm trong tập test, mô hình chưa từng thấy).
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src import config as cfg
from src.eval import walk_forward
from src.features.build_panel import SUBBASINS
from src.features.risk_levels import FLOOD_MONTHS, QUANTILES
from src.models.lgbm import PARAMS, feature_cols

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAW = cfg.ROOT / "data" / "raw"
PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
OUTDIR = cfg.ROOT / "reports" / "explainer"
STATION = (16.47, 107.57)          # trạm Kim Long — FINDINGS_GRID.md §2
LARGEST = (16.60, 107.55)          # ô lưu lượng lớn nhất, gộp cả sông Bồ


def _cell(f: str, rx: str):
    m = re.search(rx, f.replace("\\", "/"))
    return (float(m.group(1)), float(m.group(2))) if m else None


def rain_scene(start="2020-10-03", end="2020-10-24") -> dict:
    frames = []
    for f in glob.glob(str(RAW / "rain_daily" / "rd_*.parquet")):
        d = pd.read_parquet(f, columns=["time", "precipitation_sum", "lat", "lon"])
        d["time"] = pd.to_datetime(d["time"])
        frames.append(d[(d["time"] >= start) & (d["time"] <= end)])
    r = pd.concat(frames)
    cells = sorted({(float(a), float(b)) for a, b in zip(r["lat"], r["lon"])})
    days = sorted(r["time"].unique())
    piv = r.pivot_table(index="time", columns=["lat", "lon"], values="precipitation_sum")
    grid = [[round(float(piv.loc[t, c]), 1) for c in cells] for t in days]

    def band(lat):
        for name, (lo, hi) in SUBBASINS.items():
            if lo <= lat < hi:
                return name
        return "other"

    p = pd.read_parquet(PANEL, columns=["date", "discharge", "rain_basin"])
    p["date"] = pd.to_datetime(p["date"])
    w = p[(p["date"] >= start) & (p["date"] <= end)].reset_index(drop=True)
    q = w["discharge"].round(0).tolist()
    rb = w["rain_basin"].round(1).tolist()

    # cặp (ngày đỉnh mưa cục bộ → ngày đỉnh sông cục bộ) để chú thích độ trễ
    pairs = []
    for i in range(1, len(q) - 1):
        if q[i] > q[i - 1] and q[i] >= q[i + 1] and q[i] > 800:
            js = [j for j in range(max(1, i - 3), i) if rb[j] >= rb[j - 1] and rb[j] >= rb[j + 1]]
            if js:
                pairs.append([js[-1], i])
    return {"cells": [[a, b, band(a)] for a, b in cells],
            "days": [pd.Timestamp(t).strftime("%d/%m") for t in days],
            "rain": grid, "q": q, "rb": rb, "pairs": pairs,
            "rmax": float(np.nanmax(grid))}


def probe_scene() -> dict:
    qm = {}
    for f in glob.glob(str(RAW / "discharge" / "*.parquet")) + \
            glob.glob(str(RAW / "discharge_probe" / "*.parquet")):
        d = pd.read_parquet(f, columns=["time", "river_discharge", "lat", "lon"])
        k = (round(float(d["lat"].iloc[0]), 2), round(float(d["lon"].iloc[0]), 2))
        if k in qm:
            continue
        t = pd.to_datetime(d["time"])
        s = d.loc[(t >= "2023-01-01") & (t <= "2023-12-31"), "river_discharge"]
        qm[k] = round(float(s.mean()), 1) if s.notna().any() else None
    full = {_cell(f, r"q_([\d.]+)_([\d.]+)\.parquet")
            for f in glob.glob(str(RAW / "discharge" / "*.parquet"))}
    grid = [(round(16.05 + 0.05 * i, 2), round(107.05 + 0.05 * j, 2))
            for i in range(19) for j in range(19)]
    cells = []
    for c in grid:
        v = qm.get(c)
        cells.append([c[0], c[1], v if (v is not None and v > 0) else None,
                      1 if (c in full) else 0])
    return {"cells": cells, "chosen": list(cfg.RIVER_POINTS["huong_kim_long"]),
            "station": list(STATION), "largest": list(LARGEST)}


def files_scene() -> dict:
    kinds = [("rain_hourly", "hourly rain"), ("discharge_probe", "flow probes"),
             ("discharge", "full flow"), ("rain_daily", "daily rain"),
             ("fc_rain", "forecast rain")]
    out = [{"k": lbl, "n": len(glob.glob(str(RAW / k / "*.parquet")))} for k, lbl in kinds]
    p = pd.read_parquet(PANEL)
    return {"kinds": out, "total": sum(o["n"] for o in out),
            "rows": int(len(p)), "cols": int(p.shape[1])}


def forecast_scene(start="2025-10-08", end="2025-11-25") -> dict:
    from lightgbm import LGBMRegressor
    p = pd.read_parquet(PANEL)
    p["date"] = pd.to_datetime(p["date"])
    sp = walk_forward.regime_split(pd.DatetimeIndex(p["date"]))
    tr = p["date"].isin(sp["train"]) | p["date"].isin(sp["valid"])
    feats = feature_cols(p)
    y = p["target_h1"]
    ok = p[feats].notna().all(axis=1) & y.notna()
    m = LGBMRegressor(**PARAMS)
    m.fit(p.loc[tr & ok, feats], np.log1p(y[tr & ok]))
    win = ok & (p["date"] >= start) & (p["date"] <= end)
    pred = np.clip(np.expm1(m.predict(p.loc[win, feats])), 0, None)
    # dự báo phát ngày t cho ngày t+1 → vẽ theo ngày t+1
    dates = (p.loc[win, "date"] + pd.Timedelta(days=1)).dt.strftime("%d/%m").tolist()
    s = p.loc[tr & p["date"].dt.month.isin(FLOOD_MONTHS), "discharge"].dropna()
    thr = [round(float(s.quantile(q))) for q in QUANTILES.values()]
    res = pd.read_csv(cfg.ROOT / "reports" / "lgbm_results.csv")
    nse1 = float(res.loc[res["horizon"] == 1, "NSE"].iloc[0])
    pers = pd.read_csv(cfg.ROOT / "reports" / "baseline_results.csv")
    nse_p = float(pers[(pers.model == "persistence") & (pers.horizon == 1)]["NSE"].iloc[0])
    return {"dates": dates, "obs": y[win].round(0).tolist(),
            "pred": np.round(pred, 0).tolist(), "thr": thr,
            "nse": round(nse1, 3), "nse_p": round(nse_p, 3)}


# HTML/CSS/JS nằm riêng ở explainer_template.html cho dễ sửa; file này chỉ lo dữ liệu.
TEMPLATE = (Path(__file__).with_name("explainer_template.html")
            .read_text(encoding="utf-8"))


def main() -> int:
    data = {"rain": rain_scene(), "probe": probe_scene(),
            "files": files_scene(), "fc": forecast_scene()}
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.replace("__DATA__", payload)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "flood_story.html").write_text(page, encoding="utf-8")
    local = ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
             "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
             "</head><body>\n" + page + "\n</body></html>\n")
    (OUTDIR / "flood_story_local.html").write_text(local, encoding="utf-8")
    print(f"→ reports/explainer/flood_story.html  ({len(page)//1024} KB)")
    print("→ reports/explainer/flood_story_local.html  (mở thẳng khi thuyết trình)")
    r = data["rain"]
    print(f"   mưa: {len(r['cells'])} ô × {len(r['days'])} ngày · cặp trễ {r['pairs']}")
    print(f"   dò: {sum(1 for c in data['probe']['cells'] if c[2])} ô có nước / "
          f"{len(data['probe']['cells'])} · tải đủ {sum(c[3] for c in data['probe']['cells'])}")
    print(f"   file: {data['files']['total']} → {data['files']['rows']} × {data['files']['cols']}")
    print(f"   dự báo: {len(data['fc']['obs'])} ngày · NSE h1 {data['fc']['nse']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
