"""Lấy lưu lượng sông (GloFAS v4) từ Open-Meteo Flood API.

Việc W1 của G — hai chế độ:

    # 1. Quét lưới quanh trạm, chọn ô nằm đúng dòng sông (RISKS.md R1)
    python -m src.ingest.openmeteo_flood --scan

    # 2. Lấy chuỗi 1 điểm và vẽ, để nhìn thấy đợt lũ 10/2020
    python -m src.ingest.openmeteo_flood --point 16.46 107.59 --plot

Kết quả lưu Parquet trong data/raw/discharge/ và cache JSON trong .cache/
để chạy lại không tốn request (RISKS.md R3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import pandas as pd
import requests

from src import config as cfg


def _cache_path(params: dict) -> Path:
    key = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
    return cfg.CACHE / f"flood_{key}.json"


def fetch_discharge(
    lat: float,
    lon: float,
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Lấy river_discharge theo ngày cho một toạ độ.

    Trả về DataFrame cột ['date', 'discharge', 'lat', 'lon'].
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "river_discharge",
        "start_date": start or cfg.DATE_START,
        "end_date": end or cfg.DATE_END,
    }

    cache = _cache_path(params)
    if use_cache and cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
    else:
        payload = _get_with_retry(cfg.FLOOD_API, params)
        cache.write_text(json.dumps(payload), encoding="utf-8")
        time.sleep(cfg.REQUEST_SLEEP_S)

    daily = payload["daily"]
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "discharge": daily["river_discharge"],
        }
    )
    df["lat"] = lat
    df["lon"] = lon
    return df


def _get_with_retry(url: str, params: dict) -> dict:
    """GET có retry luỹ thừa. 429 = rate limit, chờ lâu hơn."""
    delay = 2.0
    for attempt in range(1, cfg.MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 429:
                raise requests.HTTPError("429 rate limit")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == cfg.MAX_RETRIES:
                raise
            print(f"  ! lỗi ({e}) — thử lại sau {delay:.0f}s "
                  f"[{attempt}/{cfg.MAX_RETRIES}]")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("không tới được đây")


def scan_grid(
    lat0: float,
    lon0: float,
    radius_deg: float = 0.3,
    step_deg: float = 0.05,
    start: str = "2015-01-01",
    end: str = "2023-12-31",
) -> pd.DataFrame:
    """Quét lưới quanh một trạm, xếp hạng các ô theo lưu lượng trung bình.

    Ô nằm đúng dòng chảy chính sẽ có discharge lớn hơn hẳn các ô xung quanh.
    Quét trên khoảng ngắn (2015–2023) cho nhanh; chốt xong mới lấy chuỗi đầy đủ.
    """
    rows = []
    n = int(radius_deg / step_deg)
    coords = [
        (round(lat0 + i * step_deg, 4), round(lon0 + j * step_deg, 4))
        for i in range(-n, n + 1)
        for j in range(-n, n + 1)
    ]
    print(f"Quét {len(coords)} ô quanh ({lat0}, {lon0})…")

    for k, (la, lo) in enumerate(coords, 1):
        try:
            d = fetch_discharge(la, lo, start, end)
        except Exception as e:  # một ô hỏng không được làm chết cả lượt quét
            print(f"  [{k}/{len(coords)}] ({la}, {lo}) lỗi: {e}")
            continue
        q = d["discharge"]
        rows.append(
            {
                "lat": la,
                "lon": lo,
                "q_mean": q.mean(),
                "q_max": q.max(),
                "q_std": q.std(),
                "n_missing": int(q.isna().sum()),
            }
        )
        print(f"  [{k}/{len(coords)}] ({la}, {lo})  "
              f"trung bình {q.mean():8.1f}  đỉnh {q.max():9.1f} m³/s")

    out = pd.DataFrame(rows).sort_values("q_mean", ascending=False)
    dest = cfg.DATA_EXTERNAL / "grid_candidates.csv"
    out.to_csv(dest, index=False)
    print(f"\n→ {dest}")
    print("\nTop 5 ô có lưu lượng lớn nhất (ứng viên dòng chảy chính):")
    print(out.head().to_string(index=False))
    print("\n⚠️ Đừng tin số liệu một mình: mở toạ độ top-1 trên bản đồ "
          "(OSM / Google Maps) kiểm tra nó có nằm trên sông thật không, "
          "rồi ghi kết luận vào docs/THRESHOLDS.md và src/config.py.")
    return out


def plot_series(df: pd.DataFrame, title: str, dest: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.plot(df["date"], df["discharge"], lw=0.7, color="#1d4ed8")
    ax.set_title(title)
    ax.set_ylabel("Lưu lượng (m³/s)")
    ax.set_xlabel("Ngày")
    ax.grid(alpha=0.3)

    # Đánh dấu các đợt lũ lịch sử để kiểm tra bằng mắt
    for year, month, label in [(1999, 11, "11/1999"), (2020, 10, "10/2020"),
                               (2023, 11, "11/2023")]:
        t = pd.Timestamp(year=year, month=month, day=1)
        if df["date"].min() <= t <= df["date"].max():
            ax.axvline(t, color="#dc2626", ls="--", lw=1, alpha=0.8)
            ax.annotate(label, (t, ax.get_ylim()[1] * 0.92),
                        color="#dc2626", fontsize=8, ha="left")

    fig.tight_layout()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, dpi=140)
    print(f"→ {dest}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scan", action="store_true",
                   help="quét lưới quanh các trạm trong config.RIVER_POINTS")
    p.add_argument("--point", nargs=2, type=float, metavar=("LAT", "LON"),
                   help="lấy chuỗi cho một toạ độ")
    p.add_argument("--start", default=cfg.DATE_START)
    p.add_argument("--end", default=cfg.DATE_END)
    p.add_argument("--plot", action="store_true", help="vẽ chuỗi ra PNG")
    args = p.parse_args()

    if args.scan:
        for name, (la, lo) in cfg.RIVER_POINTS.items():
            print(f"\n=== {name} ===")
            scan_grid(la, lo)
        return

    if args.point:
        la, lo = args.point
        df = fetch_discharge(la, lo, args.start, args.end)
        dest = cfg.DATA_RAW / "discharge" / f"q_{la}_{lo}.parquet"
        dest.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(dest, index=False)
        print(f"→ {dest}  ({len(df):,} dòng)")
        print(df["discharge"].describe().to_string())

        if args.plot:
            plot_series(
                df,
                f"Lưu lượng GloFAS tại ({la}, {lo})",
                cfg.FIGURES / f"w1_discharge_{la}_{lo}.png",
            )
        return

    p.print_help()


if __name__ == "__main__":
    main()
