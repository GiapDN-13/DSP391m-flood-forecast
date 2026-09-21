# DSP391m — Dự báo nguy cơ lũ 1–3 ngày cho các xã ven đô TP. Huế

Dự án Capstone môn DSP391m, học kỳ Fall 2026. **Khung thời gian: 9 tuần, 15/09 → 16/11/2026.**
Dữ liệu mở: **Open-Meteo Flood API (GloFAS v4)**, **Open-Meteo Historical + Historical Forecast API (ERA5)**.

**Team:** Giáp (Tech Lead) · Đức (Data Analyst) · Mai Thị Lệ Huyền (Research & Documentation Lead)

---

## 📌 Bắt đầu từ đâu

| Bạn cần gì | Đọc file nào |
|---|---|
| **Đang ở đâu trong cả môn?** | [`docs/FLOW.md`](docs/FLOW.md) — sơ đồ toàn bộ + trạng thái từng phần |
| **Dự án phải làm được gì?** | [`docs/SPEC.md`](docs/SPEC.md) — FR / NFR / ngưỡng nghiệm thu |
| **Tuần này tôi làm gì?** | [`docs/PLAN.md`](docs/PLAN.md) — kế hoạch 9 tuần theo từng người |
| Ai làm gì, vì sao chia vậy | [`docs/TEAM.md`](docs/TEAM.md) |
| Dùng git thế nào | [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md) |
| Theo dõi tiến độ ở đâu | [`docs/TRACKING.md`](docs/TRACKING.md) |
| **Kế hoạch còn thiếu gì** | [`docs/GAPS.md`](docs/GAPS.md) ← *đọc kỹ, nhiều thứ ăn điểm ở đây* |
| Đóng góp / kịch bản đánh giá / lớp hiếm | [`docs/RESEARCH_DESIGN.md`](docs/RESEARCH_DESIGN.md) |
| Ngưỡng báo động BĐ I/II/III | [`docs/THRESHOLDS.md`](docs/THRESHOLDS.md) |
| **Sự kiện lũ lịch sử & ánh xạ ngưỡng** | [`docs/FINDINGS_EVENTS.md`](docs/FINDINGS_EVENTS.md) ← *đọc §3 và §5 trước khi dùng số* · `python -m src.features.thresholds` |
| Chạy lại mọi thứ từ số 0 | [`docs/RUNBOOK.md`](docs/RUNBOOK.md) |
| **Tải dữ liệu về máy mới** | `python scripts/restore_data.py` — xem `RUNBOOK.md` §4 |
| Rủi ro & chốt cắt scope | [`docs/RISKS.md`](docs/RISKS.md) |
| **Chọn ô lưới GloFAS (đã chốt)** | [`docs/FINDINGS_GRID.md`](docs/FINDINGS_GRID.md) — `python -m src.features.river_id` |
| **Hạn mức API & chi phí crawl** | [`docs/FINDINGS_QUOTA.md`](docs/FINDINGS_QUOTA.md) |
| Theo dõi crawl (dark mode) | mở `reports/live/index.html` bằng trình duyệt |
| Dự báo phát hằng ngày | `reports/forecast_log/` — GitHub Actions ghi tự động mỗi 05:00; đọc `README.md` trong đó trước khi dùng để đánh giá |
| **Kiểm nhật ký dự báo có đủ ngày** | `python scripts/check_forecast_log.py` — xem `RUNBOOK.md` §8.7 |
| **Theo dõi job hằng ngày** | [`docs/RUNBOOK.md`](docs/RUNBOOK.md) §8 |
| Checklist EDA (Report 2) | [`docs/EDA_CHECKLIST.md`](docs/EDA_CHECKLIST.md) |
| Ôn thi vấn đáp | [`docs/EXAM_QUESTION_BANK.md`](docs/EXAM_QUESTION_BANK.md) |

## 🚀 Cài đặt

```powershell
git clone <url-repo>
cd DSP391m
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
nbstripout --install          # tự xoá output notebook khi commit
```

## 🔧 Chạy pipeline

```powershell
make crawl        # crawl dữ liệu thô (lâu, có resume)
make clean-data   # ETL làm sạch
make features     # tạo data/processed/daily_panel.parquet
make train        # train mô hình
make eval         # walk-forward validation
make dashboard    # mở Streamlit
```

Không có `make` trên Windows? Mở `Makefile` đọc lệnh rồi gõ tay — mỗi target chỉ là 1 dòng `python -m ...`.

## 📁 Cấu trúc

```
data/            raw / interim / processed / external   ← KHÔNG commit
src/
  config.py      mọi hằng số dùng chung (SEED, toạ độ, mốc split)
  ingest/        gọi API, crawl, cache, retry
  etl/           làm sạch, chuẩn hoá đơn vị, timezone
  features/      lag, rolling, API index, tổng hợp theo tiểu lưu vực
  models/        baseline, LightGBM, LSTM, dự báo hằng ngày
  eval/          walk-forward, metric, error analysis
  viz/           hàm vẽ dùng chung
notebooks/       phân tích — mỗi người file riêng, xoá output trước khi commit
dashboard/       Streamlit app
reports/         report1..4 + figures
tests/           pytest, quan trọng nhất là test_no_leakage.py
docs/            kế hoạch, quy trình, tài liệu
scripts/         bootstrap_github.ps1 · restore_data.py · check_forecast_log.py
```

## 📅 Mốc quan trọng

| Mốc | Hạn thật | **Deadline nội bộ** | % |
|---|---|---|---|
| Report 1 | ~28/09/2026 | **26/09** | 10 % |
| Report 2 | ~12/10/2026 | **09/10** | 20 % |
| Report 3 | ~04/11/2026 | **02/11** | 40 % |
| Report 4 | ~13/11/2026 | **10/11** | 10 % |
| Thi vấn đáp | 13–16/11/2026 | — | 20 % |

⚠️ Ngày trên **suy ra từ session number**, chưa phải ngày chính thức — việc đầu tiên ở W1 là lấy ngày thật từ LMS.

Luôn làm việc theo **deadline nội bộ**, không phải hạn thật.

## ⚠️ Ba luật cứng của team

1. **Không commit vào `data/`.** Dữ liệu đi qua Google Drive / Hugging Face Datasets.
2. **Kẹt quá 45 phút thì phải báo** — kéo issue sang `Blocked`. Báo ra không phải điểm trừ; im lặng cả tuần mới là.
3. **Mọi thay đổi vào `main` đều qua Pull Request.** Không ai push thẳng, kể cả G.

## 📄 Nguồn dữ liệu & giấy phép

- **Open-Meteo** — CC BY 4.0. Bắt buộc trích dẫn trong mọi báo cáo.
- **GloFAS v4 (Copernicus Emergency Management Service)** — trích dẫn theo hướng dẫn của Copernicus.
- **NASA POWER** — miễn phí, trích dẫn theo hướng dẫn NASA.

> ⚠️ **Tuyên bố miễn trừ:** Đây là sản phẩm học thuật phục vụ môn học, **không phải cảnh báo thiên tai chính thức**. Thông tin cảnh báo chính thức xem tại Đài Khí tượng Thuỷ văn khu vực Trung Trung Bộ.
