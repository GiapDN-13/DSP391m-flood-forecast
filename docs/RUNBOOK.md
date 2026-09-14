# RUNBOOK — chạy lại toàn bộ dự án từ số 0

> Mục đích: nếu **một người vắng mặt**, hai người còn lại vẫn chạy được mọi thứ. Đây là bảo hiểm quan trọng nhất của dự án (xem `docs/GAPS.md` mục 12).
>
> Viết dần từ **W3**, hoàn thiện ở **W8**. Mỗi khi thêm bước thủ công vào pipeline, **ghi vào đây ngay** — đừng đợi cuối kỳ.

## 0. Quy tắc

- Không có bước nào chỉ một người biết.
- Không có mật khẩu nào chỉ nằm trong đầu một người.
- Mọi lệnh ở đây phải **copy–paste chạy được**, không phải mô tả chung chung.

## 1. Tài khoản & quyền — ai giữ gì

| Thứ | Ai giữ | Người dự phòng | Chia sẻ qua |
|---|---|---|---|
| GitHub repo (owner) | G | D | Thêm D làm admin repo |
| Google Drive backup | G | H | Chia sẻ thư mục cho cả 3 |
| Hugging Face dataset | G | D | Token lưu trong |
| Streamlit Cloud | G | D | |
| Zotero group | H | G | |
| Tài khoản LMS nộp bài | | | |

⚠️ Không commit token vào repo. Dùng GitHub Secrets cho CI, file `.env` (đã gitignore) cho máy cá nhân.

## 2. Dựng môi trường

```powershell
git clone <url-repo>
cd DSP391m
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
nbstripout --install
pytest -q tests        # phải xanh trước khi làm gì tiếp
```

## 3. Chạy lại pipeline từ đầu

| Bước | Lệnh | Thời gian ước tính | Đầu ra |
|---|---|---|---|
| 1. Chọn ô lưới | `python -m src.ingest.openmeteo_flood --scan` | ~5 phút | `data/external/grid_candidates.csv` |
| 2. Crawl discharge | `python -m src.ingest.crawl_all --what discharge` | ⬜ điền | `data/raw/discharge/` |
| 3. Crawl mưa ERA5 | `python -m src.ingest.crawl_all --what rain` | ⬜ điền | `data/raw/rain/` |
| 4. Crawl mưa dự báo | `python -m src.ingest.crawl_all --what hist-forecast` | ⬜ điền | `data/raw/hist_forecast/` |
| 5. Làm sạch | `make clean-data` | | `data/interim/` |
| 6. Ngưỡng BĐ | `python -m src.features.thresholds` | | `docs/THRESHOLDS.md` §4 |
| 7. Bảng phân tích | `make features` | | `data/processed/daily_panel.parquet` |
| 8. Train | `make train` | | `models/` |
| 9. Đánh giá | `make eval` | | `reports/experiments.csv` |
| 10. Dashboard | `make dashboard` | | localhost:8501 |

**Đường tắt:** nếu chỉ cần chạy lại mô hình, tải sẵn `daily_panel.parquet` từ backup (mục 4) rồi nhảy thẳng vào bước 8. Không cần crawl lại.

## 4. Khôi phục dữ liệu từ backup

```powershell
# Google Drive: <dán link thư mục>
# Hugging Face: huggingface-cli download <org>/<dataset> --repo-type dataset --local-dir data/
```

Kiểm tra sau khi tải: số dòng `daily_panel.parquet` phải là ⬜____, khoảng ngày ⬜____ → ⬜____.

## 5. Bước thủ công — KHÔNG tự động hoá được

Ghi lại mọi thứ phải làm bằng tay, kèm **ai biết làm**:

| Bước thủ công | Vì sao không tự động | Ai làm được |
|---|---|---|
| Tra mực nước BĐ trong QĐ 05/2020/QĐ-TTg | Văn bản PDF | H, G |
| Thu thập sự kiện lũ vào `flood_events.csv` | Đọc bản tin, đánh giá độ tin cậy nguồn | H, G |
| Chọn ô lưới GloFAS cuối cùng | Cần mắt người đối chiếu bản đồ sông | G, D |
| ⬜ | | |

## 6. Sự cố hay gặp

| Triệu chứng | Nguyên nhân thường gặp | Xử lý |
|---|---|---|
| HTTP 429 khi crawl | Rate limit | Tăng `REQUEST_SLEEP_S` trong `src/config.py`, chạy lại — crawler có checkpoint nên không mất dữ liệu |
| Discharge phẳng lì hoặc quá nhỏ | Ô lưới không trúng dòng sông | Chạy lại `--scan`, xem `RISKS.md` R1 |
| NSE > 0.98 | **Nghi rò rỉ dữ liệu** | Chạy `pytest tests/test_no_leakage.py`, rà lại code tạo lag |
| Tổng mưa ngày ≠ tổng 24 giờ | Sai timezone hoặc sai đơn vị | `docs/API_NOTES.md` §4 |
| CI đỏ vì notebook | Còn output trong notebook | `nbstripout <file>.ipynb` rồi commit lại |
| Streamlit Cloud không lên | Thiếu dependency hoặc thiếu model | Kiểm `requirements.txt`; model tải từ GitHub Release |

## 7. Trước buổi thuyết trình — checklist

- [ ] Dashboard mở được từ máy khác, không chỉ máy G
- [ ] **Video demo backup** đã quay, để trong slide
- [ ] Repo đã tag `final`
- [ ] Cả 3 người đã đọc `docs/EXPLAINER.md` và `docs/EXAM_QUESTION_BANK.md`
- [ ] File báo cáo bản cuối có ở cả Drive lẫn máy từng người
