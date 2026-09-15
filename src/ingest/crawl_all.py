"""Crawler chính — chạy nền nhiều giờ, dừng lúc nào cũng được (FR-D1..D4).

Thiết kế để chạy qua đêm không ai trông:

* Chia việc thành các **task độc lập**, mỗi task ghi ra một file Parquet riêng.
* Task đã xong thì bỏ qua khi chạy lại → **resume miễn phí**, không gọi lại API.
* Nhịp gọi **tự điều chỉnh**: gặp 429 thì giãn ra, chạy trơn thì siết lại.
* Ghi `_progress.jsonl` mỗi task để màn hình theo dõi vẽ realtime.
* Tự dừng khi ổ đĩa sắp đầy hoặc khi lỗi liên tiếp quá nhiều.

    python -m src.ingest.crawl_all                # chạy tất cả các pha
    python -m src.ingest.crawl_all --phase discharge
    python -m src.ingest.crawl_all --dry-run      # chỉ liệt kê task

Thứ tự pha cố ý: thứ rẻ và quan trọng nhất chạy trước, để nếu bị cắt giữa chừng
thì phần đã có vẫn dùng được ngay.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from src import config as cfg

# ---------------------------------------------------------------- cấu hình

RAW = cfg.DATA_RAW
MANIFEST = RAW / "_manifest.csv"
PROGRESS = RAW / "_progress.jsonl"
LOCKFILE = RAW / "_crawl.lock"

MIN_FREE_GB = 5.0          # dừng khi ổ đĩa còn ít hơn ngần này
MAX_CONSECUTIVE_FAIL = 25  # dừng khi API hỏng liên tục

# Vùng quét lưu lượng: rộng hơn lần quét đầu để thấy trọn mạng sông
DISCHARGE_BOX = {"lat_min": 16.05, "lat_max": 16.95, "lon_min": 107.05, "lon_max": 107.95}
DISCHARGE_STEP = 0.05

# Lưới mưa trên lưu vực — thưa hơn vì mưa biến đổi chậm theo không gian
RAIN_BOX = {"lat_min": 16.10, "lat_max": 16.80, "lon_min": 107.10, "lon_max": 107.80}
RAIN_STEP = 0.15   # thưa hơn 0.10 vì quota tính theo khối lượng

RAIN_DAILY_VARS = ("precipitation_sum,temperature_2m_mean,temperature_2m_max,"
                   "temperature_2m_min,wind_speed_10m_max")
RAIN_HOURLY_VARS = "precipitation,temperature_2m,relative_humidity_2m"

HOURLY_YEARS = range(2015, 2027)   # hourly chỉ lấy từ 2015 cho nhẹ
FC_START = "2022-07-01"            # mưa dự báo lưu trữ, phục vụ kịch bản B

# Open-Meteo tính quota theo KHỐI LƯỢNG dữ liệu, không phải số request.
# Xin trọn 42 năm cho cả 361 ô sẽ đốt sạch quota ngày mà phần lớn ô lại là
# ô khô (NaN) hoặc suối nhỏ vô dụng. Nên tách hai bước:
#   1. probe  — dải ngắn, mọi ô, đủ để dựng bản đồ mạng sông
#   2. full   — trọn 1984–2026, CHỈ những ô thực sự có dòng chảy
# Probe chỉ cần 1 năm: đủ để biết ô có dòng chảy hay không, rẻ hơn 6 lần.
PROBE_START, PROBE_END = "2023-01-01", "2023-12-31"
FULL_MIN_QMEAN = 1.0   # m³/s — dưới ngưỡng này coi như không phải sông
MAX_FULL_CELLS = 40    # trần số ô xin chuỗi 42 năm, tránh đốt sạch quota

# Quota Open-Meteo tính theo KHỐI LƯỢNG chứ không theo số request.
# Xấp xỉ: weight ≈ ceil(số ngày / 14) × ceil(số biến / 10).
# Hạn mức miễn phí ~10.000 đơn vị/ngày và ~5.000/giờ.
# ⇒ Một request 42 năm ≈ 1.113 đơn vị: chỉ 9 request là hết hạn mức giờ.
DAILY_QUOTA = 10_000
HOURLY_QUOTA = 5_000


class Budget:
    """Trạng thái chung của lượt crawl: nhịp gọi, đếm lỗi, đếm byte."""

    def __init__(self) -> None:
        self.sleep = 1.0
        self.ok = 0
        self.fail = 0
        self.rate_limited = 0
        self.consecutive_fail = 0
        self.since_429 = 0
        self.bytes = 0
        self.weight = 0          # tổng đơn vị quota đã tiêu
        self.t0 = time.time()

    def on_success(self, nbytes: int) -> None:
        self.ok += 1
        self.bytes += nbytes
        self.consecutive_fail = 0
        self.since_429 += 1
        # Phục hồi nhanh: chạy trơn 8 lần liên tiếp thì nới nhịp xuống 25 %.
        # Bản trước giảm quá chậm nên nhịp dính trần 8 s cả đêm.
        if self.since_429 >= 8:
            self.sleep = max(0.7, self.sleep * 0.75)
            self.since_429 = 0

    def on_rate_limit(self) -> None:
        self.rate_limited += 1
        self.since_429 = 0
        self.sleep = min(12.0, self.sleep * 1.5)

    def on_fail(self) -> None:
        self.fail += 1
        self.consecutive_fail += 1


# ---------------------------------------------------------------- tiện ích

def _grid(box: dict, step: float) -> list[tuple[float, float]]:
    lats = np.round(np.arange(box["lat_min"], box["lat_max"] + 1e-9, step), 4)
    lons = np.round(np.arange(box["lon_min"], box["lon_max"] + 1e-9, step), 4)
    return [(float(a), float(o)) for a in lats for o in lons]


def est_weight(params: dict, block: str) -> int:
    """Ước lượng số đơn vị quota mà một request tiêu tốn."""
    try:
        d0 = datetime.fromisoformat(params["start_date"]).date()
        d1 = datetime.fromisoformat(params["end_date"]).date()
        days = max((d1 - d0).days + 1, 1)
    except Exception:
        days = 1
    nvars = len(str(params.get(block, "")).split(","))
    w = -(-days // 14) * max(1, -(-nvars // 10))
    if block == "hourly":
        w *= 24
    return int(w)


class SingleInstance:
    """Khoá chống chạy trùng.

    Hai crawler chạy song song sẽ đốt gấp đôi quota và ép nhau vào 429 —
    đã dính đúng lỗi này một lần vì `pkill` của Git Bash không giết được
    tiến trình Python trên Windows.
    """

    def __enter__(self):
        if LOCKFILE.exists():
            try:
                old = int(LOCKFILE.read_text().split()[0])
            except Exception:
                old = None
            if old is not None and _pid_alive(old):
                raise SystemExit(
                    f"Đã có crawler đang chạy (PID {old}). "
                    f"Dừng nó trước, hoặc xoá {LOCKFILE} nếu chắc chắn nó đã chết."
                )
            print(f"Dọn khoá cũ của tiến trình đã chết (PID {old})")
        LOCKFILE.write_text(f"{os.getpid()} {datetime.now().isoformat()}")
        return self

    def __exit__(self, *exc):
        LOCKFILE.unlink(missing_ok=True)


def _pid_alive(pid: int) -> bool:
    try:
        import subprocess
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                             capture_output=True, text=True, timeout=10).stdout
        return str(pid) in out
    except Exception:
        return False


def _free_gb() -> float:
    return shutil.disk_usage(str(RAW))[2] / 1e9


def _log(rec: dict) -> None:
    rec["ts"] = datetime.now().isoformat(timespec="seconds")
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _get(url: str, params: dict, budget: Budget) -> tuple[dict | None, int]:
    """GET có backoff. Trả về (payload, số byte). None nếu bỏ cuộc."""
    delay = 2.0
    for attempt in range(cfg.MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=180)
            if r.status_code == 429:
                budget.on_rate_limit()
                time.sleep(delay)
                delay = min(90.0, delay * 2)
                continue
            r.raise_for_status()
            return r.json(), len(r.content)
        except (requests.RequestException, ValueError):
            time.sleep(delay)
            delay = min(90.0, delay * 2)
    return None, 0


# ---------------------------------------------------------------- các pha

def tasks_discharge_probe() -> list[dict]:
    """Dải ngắn, mọi ô — dựng bản đồ mạng sông với chi phí thấp."""
    out = []
    cells = _grid(DISCHARGE_BOX, DISCHARGE_STEP)
    # Lượt crawl trước đã phủ phía nam (lat ≤ 16.50). Ưu tiên phía bắc trước,
    # vì đó là vùng hợp lưu Hương–Bồ còn chưa biết gì.
    cells.sort(key=lambda c: -c[0])
    for la, lo in cells:
        if (RAW / "discharge" / f"q_{la}_{lo}.parquet").exists():
            continue                      # đã có bản đầy đủ thì khỏi probe
        out.append({
            "kind": "discharge_probe", "lat": la, "lon": lo,
            "dest": RAW / "discharge_probe" / f"qp_{la}_{lo}.parquet",
            "url": cfg.FLOOD_API,
            "params": {"latitude": la, "longitude": lo, "daily": "river_discharge",
                       "start_date": PROBE_START, "end_date": PROBE_END},
            "block": "daily",
        })
    return out


def river_cells() -> list[tuple[float, float, float]]:
    """Các ô có dòng chảy thật, suy từ kết quả probe. Sắp theo lưu lượng giảm dần."""
    rows = []
    for f in (RAW / "discharge_probe").glob("qp_*.parquet"):
        try:
            d = pd.read_parquet(f, columns=["river_discharge", "lat", "lon"])
        except Exception:
            continue
        qm = d["river_discharge"].mean()
        if pd.notna(qm) and qm >= FULL_MIN_QMEAN:
            rows.append((float(d["lat"].iloc[0]), float(d["lon"].iloc[0]), float(qm)))
    return sorted(rows, key=lambda r: -r[2])


def tasks_discharge_full() -> list[dict]:
    """Trọn 1984–2026, chỉ cho ô có dòng chảy. Ô lớn nhất chạy trước."""
    out = []
    for la, lo, _q in river_cells()[:MAX_FULL_CELLS]:
        out.append({
            "kind": "discharge_full", "lat": la, "lon": lo,
            "dest": RAW / "discharge" / f"q_{la}_{lo}.parquet",
            "url": cfg.FLOOD_API,
            "params": {"latitude": la, "longitude": lo, "daily": "river_discharge",
                       "start_date": cfg.DATE_START, "end_date": cfg.DATE_END},
            "block": "daily",
        })
    return out


def tasks_rain_daily() -> list[dict]:
    out = []
    for la, lo in _grid(RAIN_BOX, RAIN_STEP):
        out.append({
            "kind": "rain_daily", "lat": la, "lon": lo,
            "dest": RAW / "rain_daily" / f"rd_{la}_{lo}.parquet",
            "url": cfg.ARCHIVE_API,
            "params": {"latitude": la, "longitude": lo, "daily": RAIN_DAILY_VARS,
                       "start_date": cfg.RAIN_DATE_START, "end_date": cfg.DATE_END,
                       "timezone": cfg.TIMEZONE},
            "block": "daily",
        })
    return out


def tasks_rain_hourly() -> list[dict]:
    out = []
    for la, lo in _grid(RAIN_BOX, RAIN_STEP):
        for yr in HOURLY_YEARS:
            end = min(f"{yr}-12-31", cfg.DATE_END)
            if f"{yr}-01-01" > cfg.DATE_END:
                continue
            out.append({
                "kind": "rain_hourly", "lat": la, "lon": lo, "year": yr,
                "dest": RAW / "rain_hourly" / f"rh_{la}_{lo}_{yr}.parquet",
                "url": cfg.ARCHIVE_API,
                "params": {"latitude": la, "longitude": lo, "hourly": RAIN_HOURLY_VARS,
                           "start_date": f"{yr}-01-01", "end_date": end,
                           "timezone": cfg.TIMEZONE},
                "block": "hourly",
            })
    return out


def tasks_forecast_rain() -> list[dict]:
    """Mưa dự báo đã phát trong quá khứ — đầu vào kịch bản B (FR-D3)."""
    out = []
    today = date.today().isoformat()
    for la, lo in _grid(RAIN_BOX, RAIN_STEP):
        out.append({
            "kind": "fc_rain", "lat": la, "lon": lo,
            "dest": RAW / "fc_rain" / f"fc_{la}_{lo}.parquet",
            "url": cfg.HIST_FORECAST_API,
            "params": {"latitude": la, "longitude": lo,
                       "daily": "precipitation_sum,temperature_2m_mean",
                       "start_date": FC_START, "end_date": today,
                       "timezone": cfg.TIMEZONE},
            "block": "daily",
        })
    return out


# Thứ tự cố ý: rẻ và quan trọng trước. Danh sách task của mỗi pha được dựng
# NGAY TRƯỚC khi chạy pha đó, nên discharge_full thấy được kết quả của probe.
# Thứ tự theo GIÁ TRỊ TRÊN MỖI ĐƠN VỊ QUOTA, không theo thứ tự pipeline.
# 45 ô discharge chuỗi đầy đủ (gồm ô dòng chính) đã có sẵn từ lượt trước,
# nên phần thiếu nhất bây giờ là mưa.
PHASES = {
    "rain_daily": tasks_rain_daily,             # bắt buộc cho mô hình (FR-D2)
    "discharge_probe": tasks_discharge_probe,   # rẻ, hoàn tất bản đồ phía bắc
    "fc_rain": tasks_forecast_rain,             # kịch bản B (FR-D3)
    "discharge_full": tasks_discharge_full,     # đắt, chỉ ô có sông
    "rain_hourly": tasks_rain_hourly,           # ~189k đơn vị — xem ghi chú
}

# rain_hourly tốn ~189.000 đơn vị quota = ~19 ngày hạn mức miễn phí, trong khi
# mô hình chỉ cần dữ liệu NGÀY. Vì vậy nó KHÔNG nằm trong lượt chạy mặc định.
# Muốn chạy thì gọi tay:  python -m src.ingest.crawl_all --phase rain_hourly
DEFAULT_PHASES = ["rain_daily", "discharge_probe", "fc_rain", "discharge_full"]


# ---------------------------------------------------------------- vòng chạy

def run_task(t: dict, budget: Budget) -> str:
    dest: Path = t["dest"]
    if dest.exists():
        return "skip"

    budget.weight += est_weight(t["params"], t["block"])
    payload, nbytes = _get(t["url"], t["params"], budget)
    if payload is None:
        budget.on_fail()
        return "fail"

    block = payload.get(t["block"])
    if not block:
        budget.on_fail()
        return "fail"

    df = pd.DataFrame(block)
    tcol = "time"
    if tcol in df.columns:
        df[tcol] = pd.to_datetime(df[tcol])
    df["lat"], df["lon"] = t["lat"], t["lon"]

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(dest)           # ghi nguyên tử: không để lại file nửa vời

    budget.on_success(nbytes)

    value_col = [c for c in df.columns if c not in (tcol, "lat", "lon")]
    has_data = bool(value_col) and bool(df[value_col[0]].notna().any())
    _log({"kind": t["kind"], "lat": t["lat"], "lon": t["lon"],
          "year": t.get("year"), "rows": len(df), "bytes": nbytes,
          "has_data": has_data, "sleep": round(budget.sleep, 2),
          "ok": budget.ok, "fail": budget.fail, "rl": budget.rate_limited,
          "total_bytes": budget.bytes, "weight": budget.weight})
    return "ok"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--phase", nargs="*", default=DEFAULT_PHASES)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.dry_run:
        for name in args.phase:
            tasks = PHASES[name]()
            d = sum(t["dest"].exists() for t in tasks)
            print(f"  {name:16} {d:5}/{len(tasks):<5}")
        return

    budget = Budget()
    _log({"event": "start", "phases": list(args.phase), "pid": os.getpid()})
    stop = False

    for name in args.phase:
        if stop:
            break
        # Dựng danh sách ngay lúc này: discharge_full cần kết quả probe trước đó
        tasks = PHASES[name]()
        todo = [t for t in tasks if not t["dest"].exists()]
        print(f"\n=== {name}: {len(tasks)} task, cần chạy {len(todo)} ===", flush=True)
        _log({"event": "phase_start", "phase": name,
              "n_todo": len(todo), "n_total": len(tasks)})

        for i, t in enumerate(todo, 1):
            if _free_gb() < MIN_FREE_GB:
                print(f"DỪNG: ổ đĩa chỉ còn {_free_gb():.1f} GB")
                _log({"event": "stop", "reason": "disk_full"})
                stop = True
                break
            if budget.consecutive_fail >= MAX_CONSECUTIVE_FAIL:
                print(f"DỪNG: {budget.consecutive_fail} lỗi liên tiếp")
                _log({"event": "stop", "reason": "too_many_failures"})
                stop = True
                break

            try:
                status = run_task(t, budget)
            except Exception as e:
                budget.on_fail()
                status = "error"
                print(f"  ! {t['kind']} ({t['lat']}, {t['lon']}) lỗi: {e}", flush=True)
            if status == "ok":
                time.sleep(budget.sleep)

            if i % 25 == 0 or i == len(todo):
                el = time.time() - budget.t0
                rate = budget.ok / el * 60 if el else 0
                print(f"[{name} {i}/{len(todo)}] ok={budget.ok} fail={budget.fail} "
                      f"429={budget.rate_limited} nhip={budget.sleep:.1f}s "
                      f"{budget.bytes/1e6:.0f}MB quota~{budget.weight} "
                      f"{rate:.1f} task/phút", flush=True)

    _log({"event": "done", "ok": budget.ok, "fail": budget.fail,
          "rl": budget.rate_limited, "total_bytes": budget.bytes})
    print(f"\nXONG. ok={budget.ok} fail={budget.fail} 429={budget.rate_limited} "
          f"{budget.bytes/1e6:.0f} MB trong {(time.time()-budget.t0)/60:.0f} phút")


if __name__ == "__main__":
    with SingleInstance():
        main()
