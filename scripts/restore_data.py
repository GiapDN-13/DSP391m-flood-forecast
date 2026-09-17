"""Khôi phục dữ liệu từ bản sao lưu trên GitHub Release (FR-D6).

Bản sao lưu không có giá trị nếu chưa ai thử khôi phục. Script này là đường
khôi phục chính thức — chạy được trên máy trắng, chỉ cần `gh` đã đăng nhập.

    python scripts/restore_data.py                # chỉ bảng phân tích (~2 MB)
    python scripts/restore_data.py --all          # toàn bộ, kể cả mưa giờ 72 MB
    python scripts/restore_data.py --what interim raw_discharge
    python scripts/restore_data.py --list         # xem có gì mà không tải

Vì sao mặc định chỉ tải bảng phân tích: `daily_panel.parquet` là đủ để chạy
lại EDA, baseline và mô hình. Dữ liệu thô chỉ cần khi muốn dựng lại panel từ
đầu hoặc đổi cách gộp không gian.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REPO = "GiapDN-13/DSP391m-flood-forecast"
TAG = "data-2026-09-17"

# asset -> (giải nén vào đâu, mô tả)
ASSETS = {
    "daily_panel.parquet": (ROOT / "data" / "processed", "bảng phân tích chính"),
    "interim.tar.gz": (ROOT / "data", "dữ liệu đã làm sạch"),
    "raw_discharge.tar.gz": (ROOT / "data" / "raw", "lưu lượng GloFAS 1984–2026"),
    "raw_rain_daily.tar.gz": (ROOT / "data" / "raw", "mưa ngày ERA5"),
    "raw_fc_rain.tar.gz": (ROOT / "data" / "raw", "mưa dự báo đã phát"),
    "raw_discharge_probe.tar.gz": (ROOT / "data" / "raw", "probe dò mạng sông"),
    "raw_rain_hourly.tar.gz": (ROOT / "data" / "raw", "mưa giờ ERA5 (nặng, 72 MB)"),
}
DEFAULT = ["daily_panel.parquet"]


def gh(*args: str) -> str:
    """Gọi gh CLI, báo lỗi rõ ràng nếu chưa cài hoặc chưa đăng nhập."""
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True,
                           encoding="utf-8", timeout=900)
    except FileNotFoundError:
        raise SystemExit(
            "Chưa có GitHub CLI. Cài bằng:  winget install GitHub.cli\n"
            "rồi đăng nhập:  gh auth login")
    if r.returncode != 0:
        raise SystemExit(f"gh lỗi:\n{(r.stderr or '').strip()[:600]}")
    return r.stdout


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def show_list() -> int:
    raw = gh("release", "view", TAG, "--repo", REPO, "--json", "assets")
    print(f"Bản sao lưu {TAG} — {REPO}\n")
    for a in json.loads(raw)["assets"]:
        desc = ASSETS.get(a["name"], ("", "(siêu dữ liệu)"))[1]
        print(f"  {a['name']:<30} {a['size']/1e6:7.1f} MB  {desc}")
    return 0


def restore(names: list[str], tmp: Path) -> int:
    tmp.mkdir(parents=True, exist_ok=True)

    # MANIFEST + SHA256SUMS luôn tải, để kiểm tính toàn vẹn
    print("Tải siêu dữ liệu…")
    gh("release", "download", TAG, "--repo", REPO, "--pattern", "SHA256SUMS.txt",
       "--dir", str(tmp), "--clobber")
    sums = {}
    for line in (tmp / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            sums[name.strip().lstrip("*")] = digest

    ok = bad = 0
    for name in names:
        if name not in ASSETS:
            print(f"  ! bỏ qua '{name}' — không có trong bản sao lưu")
            continue
        dest_dir, desc = ASSETS[name]
        print(f"\n{name}  ({desc})")

        gh("release", "download", TAG, "--repo", REPO, "--pattern", name,
           "--dir", str(tmp), "--clobber")
        f = tmp / name

        # kiểm checksum TRƯỚC khi giải nén — tải lỗi thì đừng ghi vào data/
        if name in sums:
            got = sha256(f)
            if got != sums[name]:
                print(f"  ✗ checksum SAI\n    chờ {sums[name][:16]}…\n    được {got[:16]}…")
                bad += 1
                continue
            print("  ✓ checksum khớp")

        dest_dir.mkdir(parents=True, exist_ok=True)
        if name.endswith(".tar.gz"):
            with tarfile.open(f, "r:gz") as t:
                t.extractall(dest_dir, filter="data")
            print(f"  → giải nén vào {dest_dir.relative_to(ROOT)}")
        else:
            shutil.copy2(f, dest_dir / name)
            print(f"  → {(dest_dir / name).relative_to(ROOT)}")
        ok += 1

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nXong: {ok} asset khôi phục" + (f", {bad} LỖI checksum" if bad else ""))

    panel = ROOT / "data" / "processed" / "daily_panel.parquet"
    if panel.exists():
        try:
            import pandas as pd
            d = pd.read_parquet(panel)
            print(f"Kiểm tra: daily_panel.parquet {len(d):,} dòng × {d.shape[1]} cột, "
                  f"{str(d['date'].min())[:10]} → {str(d['date'].max())[:10]}"
                  .replace(",", " "))
            if len(d) != 6087:
                print("  ⚠️ số dòng khác kỳ vọng 6 087 — kiểm lại bản sao lưu")
        except ImportError:
            pass
    return 1 if bad else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--all", action="store_true", help="tải mọi asset")
    p.add_argument("--what", nargs="*", help="chọn asset cụ thể")
    p.add_argument("--list", action="store_true", help="chỉ liệt kê, không tải")
    a = p.parse_args()

    if a.list:
        return show_list()
    names = list(ASSETS) if a.all else (a.what or DEFAULT)
    print(f"Khôi phục {len(names)} asset từ {TAG}\n")
    return restore(names, ROOT / ".restore_tmp")


if __name__ == "__main__":
    sys.exit(main())
