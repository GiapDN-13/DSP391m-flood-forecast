"""Kiểm nhật ký dự báo có đủ ngày và đúng nhãn ngày (RUNBOOK §8.7).

Vì sao cần script này: từ 15/09 tới 21/09/2026, GitHub Actions báo thành công
6 lần liên tiếp mà nhật ký vẫn mất bản 20/09 — một lần chạy quanh nửa đêm UTC
đã tự nhận sai ngày rồi ghi đè bản hôm trước. **Job xanh không chứng minh dữ
liệu đúng**, nên phải kiểm bằng sản phẩm.

    python scripts/check_forecast_log.py
    python scripts/check_forecast_log.py --bo-qua 2026-09-20

Thoát mã 1 nếu có ngày thiếu hoặc nhãn ngày sai — dùng được trong CI.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as cfg  # noqa: E402

LOG_DIR = cfg.ROOT / "reports" / "forecast_log"
NGAY = re.compile(r"^(\d{4}-\d{2}-\d{2})\.csv$")
MUON = re.compile(r"^(\d{4}-\d{2}-\d{2})_chu-ky-muon-.*\.csv$")

# Ngày đã biết là thiếu và KHÔNG cứu được — ghi rõ lý do, đừng giả vờ là đủ.
DA_BIET_THIEU = {
    "2026-09-20": "job chạy 23:58 UTC 19/09 tự nhận là 19/09 và ghi đè "
                  "(xem reports/forecast_log/README.md)",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bo-qua", nargs="*", default=[],
                    help="ngày cho phép thiếu, dạng YYYY-MM-DD")
    a = ap.parse_args()

    chinh: dict[str, Path] = {}
    muon: list[Path] = []
    for f in sorted(LOG_DIR.glob("*.csv")):
        if m := NGAY.match(f.name):
            chinh[m.group(1)] = f
        elif MUON.match(f.name):
            muon.append(f)

    if not chinh:
        print("Không có file dự báo nào trong reports/forecast_log/ — job chưa chạy?")
        return 1

    hom_nay = datetime.now(ZoneInfo(cfg.TIMEZONE)).date()
    dau = date.fromisoformat(min(chinh))
    print(f"Nhật ký dự báo: {min(chinh)} → {max(chinh)}  "
          f"({len(chinh)} bản, hôm nay {hom_nay})\n")

    bo_qua = set(a.bo_qua) | set(DA_BIET_THIEU)
    thieu, thieu_that = [], []
    d = dau
    while d <= hom_nay:
        k = d.isoformat()
        if k not in chinh:
            (thieu if k in bo_qua else thieu_that).append(k)
        d += timedelta(days=1)

    for k in thieu:
        ly_do = DA_BIET_THIEU.get(k, "được bỏ qua bằng --bo-qua")
        print(f"  ○ {k} thiếu — đã biết: {ly_do}")
    for k in thieu_that:
        print(f"  ✗ {k} THIẾU và chưa có lời giải thích")

    # Nhãn ngày trong file phải khớp tên file, nếu không là lặp lại lỗi múi giờ
    lech = []
    for k, f in chinh.items():
        dong = f.read_text(encoding="utf-8").splitlines()
        if len(dong) < 2:
            lech.append((k, "file rỗng"))
            continue
        cot = dong[0].split(",")
        if "run_date" in cot:
            got = dong[1].split(",")[cot.index("run_date")].strip()[:10]
            if got != k:
                lech.append((k, f"run_date trong file là {got}"))
    for k, v in lech:
        print(f"  ✗ {k}: {v}")

    if muon:
        print(f"\n  ⚠ {len(muon)} file chạy trùng ngày (giữ lại để truy nguyên, "
              f"KHÔNG dùng khi đánh giá):")
        for f in muon:
            print(f"      {f.name}")

    so_ngay = (hom_nay - dau).days + 1
    print(f"\nĐộ phủ: {len(chinh)}/{so_ngay} ngày "
          f"({100 * len(chinh) / so_ngay:.0f} %)")
    if thieu_that or lech:
        print("KHÔNG ĐẠT — xem RUNBOOK §8.7")
        return 1
    print("ĐẠT" + (f" (bỏ qua {len(thieu)} ngày đã ghi nhận)" if thieu else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
