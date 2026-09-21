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

Dữ liệu nằm trong **GitHub Release asset** của chính repo này — không cần tài khoản nào khác, `gh auth login` là đủ. Chỉ collaborator đọc được, vì repo private.

Bản mới nhất: **`data-2026-09-17`** · 9 asset · 95 MB nén (124 MB giải nén)

```powershell
python scripts/restore_data.py            # chỉ bảng phân tích (~2 MB) — đủ để chạy mô hình
python scripts/restore_data.py --all      # toàn bộ, kể cả mưa giờ 72 MB
python scripts/restore_data.py --list     # xem có gì mà không tải
python scripts/restore_data.py --what interim raw_discharge
```

Script **kiểm checksum SHA-256 trước khi giải nén**, nên tải lỗi sẽ không ghi rác vào `data/`.

| Asset | Nén | Nội dung |
|---|---|---|
| `daily_panel.parquet` | 2,1 MB | **Bảng phân tích chính** — có cái này là chạy lại được EDA, baseline, mô hình |
| `interim.tar.gz` | 2,5 MB | Dữ liệu đã làm sạch |
| `raw_discharge.tar.gz` | 9,7 MB | Lưu lượng GloFAS 1984–2026, 83 ô lưới |
| `raw_rain_daily.tar.gz` | 5,1 MB | Mưa ngày ERA5 2010–2026, 68 điểm |
| `raw_rain_hourly.tar.gz` | 74,5 MB | Mưa giờ ERA5 2015–2026, 960 file |
| `raw_fc_rain.tar.gz` | 0,3 MB | Mưa dự báo đã phát 2022–nay |
| `raw_discharge_probe.tar.gz` | 0,2 MB | Probe 1 năm dò mạng sông |

**Đã kiểm thật, không phải giả định:** xoá `daily_panel.parquet` rồi khôi phục — file về đúng **6 087 dòng × 71 cột**, 2010-01-01 → 2026-08-31, và **giống bản gốc bit-for-bit** (SHA-256 khớp).

### Khi nào tạo bản sao lưu mới

Sau mỗi lần dữ liệu thô đổi đáng kể (thêm điểm lưới, đổi ô lưới, crawl thêm năm). Cách làm: nén theo từng loại, tạo `SHA256SUMS.txt` + `MANIFEST.json`, rồi `gh release create data-<ngày> ... <các asset>`. Sửa `TAG` trong `scripts/restore_data.py` sang bản mới.

> ⚠️ Đừng xoá release cũ. Nó là mốc để trả lời *"lúc nộp Report 2 thì dữ liệu ở trạng thái nào?"*

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

---

# 8. Theo dõi job dự báo hằng ngày

Job `daily-forecast` chạy **05:00 giờ Việt Nam** mỗi ngày trên GitHub Actions.

## 8.1 Xem nhanh từ terminal

```powershell
gh run list --workflow=daily-forecast.yml --limit 10   # 10 lần chạy gần nhất
gh run watch                                           # bám theo lần đang chạy, cập nhật realtime
gh run view --log                                      # xem log đầy đủ
gh run view --log-failed                               # chỉ xem bước hỏng
gh workflow run daily-forecast.yml                     # chạy tay ngay, không đợi tới 05:00
```

Một dòng gọn để hỏi "hôm nay chạy chưa, kết quả gì":

```powershell
gh run list --workflow=daily-forecast.yml --limit 5 --json createdAt,conclusion -q '.[] | "\(.createdAt[:16])  \(.conclusion)"'
```

## 8.2 Xem trên web

`https://github.com/GiapDN-13/DSP391m-flood-forecast/actions` → tab **daily-forecast**.
Bấm vào một lần chạy để xem log từng bước. Mỗi lần chạy còn đính kèm **artifact** giữ 90 ngày.

> Repo đang private nên **không gắn được badge trạng thái** vào README — ảnh badge của repo private cần token, người xem sẽ thấy "unknown". Sau khi nộp Report 4, chuyển repo sang public là gắn được.

## 8.3 Bằng chứng job đã chạy — không cần mở Actions

Job **commit thẳng kết quả vào repo**. Nên chỉ cần:

```powershell
git pull
ls reports/forecast_log/          # mỗi ngày phát báo một file YYYY-MM-DD.csv
git log --oneline --author=github-actions -5
```

> ⚠️ **Đừng suy luận ngược như vậy.** Thiếu file **không** đồng nghĩa job hỏng:
> ngày 20/09/2026 mất bản dự báo trong khi cả 6 lần chạy đều báo xanh. Xem
> `reports/forecast_log/README.md`. Kiểm tra bằng §8.7 thay vì đếm dấu tick.

## 8.4 Nhận thông báo khi hỏng

GitHub **tự gửi email cho chủ repo khi workflow theo lịch thất bại** — không phải cấu hình gì. Kiểm tra bật/tắt tại Settings → Notifications → Actions.

Cài **GitHub Mobile** thì có thông báo đẩy, tiện hơn email.

## 8.5 ⚠️ Bốn cái bẫy của workflow theo lịch

| Bẫy | Hệ quả | Cách tránh |
|---|---|---|
| **GitHub tự tắt lịch sau 60 ngày repo không có hoạt động** | Job im lặng ngừng chạy, không báo gì | Dự án kéo 9 tuần ≈ 63 ngày — sát ngưỡng. Vì job tự commit mỗi ngày nên repo luôn "có hoạt động", coi như đã tránh được. Nhưng **nếu có lúc job hỏng liên tiếp nhiều ngày thì đồng hồ 60 ngày bắt đầu chạy** |
| **Cron chạy trễ giờ cao điểm** | **Đo thực tế 15–21/09/2026: trễ ~2 giờ**, không phải 10–30 phút | Đừng đặt logic phụ thuộc đúng phút, và **đừng đặt lịch sát nửa đêm UTC** — trễ 2 giờ là sang ngày khác. Lịch đã chuyển 22:00 → 20:00 UTC |
| **Giờ UTC, không phải giờ Việt Nam** | Đặt nhầm giờ | `0 20 * * *` = 20:00 UTC; cộng độ trễ ~2h ≈ **05:00 VN** |
| **Code cũng đọc ngày theo UTC** — bẫy đã thực sự cắn | `date.today()` trên runner trả ngày UTC. Job nổ quanh nửa đêm UTC ⇒ nhãn ngày sai, **ghi đè bản hôm trước**, mất bản 20/09/2026 dù 6 lần chạy đều xanh | Dùng `ict_today()` trong `predict_daily.py`. Không bao giờ `date.today()` trong code chạy trên CI. Đã khoá bằng `tests/test_forecast_log.py` |

## 8.6 Kiểm mỗi tuần (G, trong buổi họp thứ 4)

- [ ] `python scripts/check_forecast_log.py` — xanh chưa? (§8.7)
- [ ] Lần chạy nào `failure` không? Lý do?
- [ ] Sau khi có mô hình (W5+): file có cột dự báo của nhóm chưa, hay vẫn chỉ GloFAS thô?

## 8.7 Kiểm tra nhật ký có đủ ngày — việc phải làm hằng tuần

Job xanh không chứng minh dữ liệu đúng. Kiểm bằng sản phẩm:

```powershell
python scripts/check_forecast_log.py
```

Script liệt kê mọi ngày thiếu giữa ngày đầu và hôm nay, cảnh báo file `_chu-ky-muon-`
(dấu hiệu job chạy trùng ngày) và kiểm `run_date` trong file có khớp tên file.
Thoát mã 1 nếu có ngày thiếu — chạy được cả trong CI.
