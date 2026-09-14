# DSP391m — Dự báo nguy cơ lũ 1–3 ngày cho các xã ven đô TP. Huế

Dự án Capstone môn DSP391m, học kỳ Fall 2026.
Dữ liệu mở: **Open-Meteo Flood API (GloFAS v4)**, **Open-Meteo Historical/Forecast API (ERA5)**, **NASA POWER**.

**Team:** Giáp (Tech Lead) · Đức (Data Analyst) · Huyền (Research & Documentation Lead)

---

## 📌 Bắt đầu từ đâu

| Bạn cần gì | Đọc file nào |
|---|---|
| **Tuần này tôi làm gì?** | [`docs/PLAN.md`](docs/PLAN.md) — kế hoạch 15 tuần theo từng người |
| Ai làm gì, vì sao chia vậy | [`docs/TEAM.md`](docs/TEAM.md) |
| Dùng git thế nào | [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md) |
| Theo dõi tiến độ ở đâu | [`docs/TRACKING.md`](docs/TRACKING.md) |
| **Kế hoạch còn thiếu gì** | [`docs/GAPS.md`](docs/GAPS.md) ← *đọc kỹ, nhiều thứ ăn điểm ở đây* |
| Rủi ro và phương án B | [`docs/RISKS.md`](docs/RISKS.md) |
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
scripts/         bootstrap_github.ps1
```

## 📅 Mốc quan trọng

| Mốc | Hạn thật | **Deadline nội bộ** | % |
|---|---|---|---|
| Report 1 | 04/10/2026 | **01/10** | 10 % |
| Report 2 | 01/11/2026 | **29/10** | 20 % |
| Report 3 | 13/12/2026 | **10/12** | 40 % |
| Report 4 | 21/12/2026 | **18/12** | 10 % |
| Thi vấn đáp | 22–27/12/2026 | — | 20 % |

Luôn làm việc theo **deadline nội bộ**, không phải hạn thật.

## ⚠️ Ba luật cứng của team

1. **Không commit vào `data/`.** Dữ liệu đi qua Google Drive / Hugging Face Datasets.
2. **Kẹt quá 45 phút thì phải báo** — kéo issue sang `Blocked`. Báo ra không phải điểm trừ; im lặng cả tuần mới là.
3. **Mọi thay đổi vào `main` đều qua Pull Request.** Không ai push thẳng, kể cả Giáp.

## 📄 Nguồn dữ liệu & giấy phép

- **Open-Meteo** — CC BY 4.0. Bắt buộc trích dẫn trong mọi báo cáo.
- **GloFAS v4 (Copernicus Emergency Management Service)** — trích dẫn theo hướng dẫn của Copernicus.
- **NASA POWER** — miễn phí, trích dẫn theo hướng dẫn NASA.

> ⚠️ **Tuyên bố miễn trừ:** Đây là sản phẩm học thuật phục vụ môn học, **không phải cảnh báo thiên tai chính thức**. Thông tin cảnh báo chính thức xem tại Đài Khí tượng Thuỷ văn khu vực Trung Trung Bộ.
