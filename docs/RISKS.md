# SỔ RỦI RO

Cập nhật mỗi thứ 4 trong buổi họp. `P` = xác suất, `I` = mức ảnh hưởng (1 thấp – 5 cao).

| # | Rủi ro | P | I | Dấu hiệu sớm | Phương án xử lý | Ai canh |
|---|---|---|---|---|---|---|
| R1 | Ô lưới GloFAS không trùng dòng sông thật | 3 | 5 | Discharge trung bình quá nhỏ (< 20 m³/s) hoặc phẳng lì | Quét lưới ±0.3°, chọn ô discharge lớn nhất; đối chiếu với bản đồ sông trên OSM | G |
| R2 | **Crawl 40 năm không kịp trước W05** | 3 | 5 | Hết W04 mà < 50 % lưới xong | **Phương án B:** rút còn 2010–2026 và 50 điểm lưới. Ghi rõ lý do trong báo cáo | G |
| R3 | Rate limit API | 3 | 3 | HTTP 429 | Gộp nhiều ngày vào 1 request, sleep 1–2 s, cache theo file, chạy đêm | G |
| R4 | Không xin được số liệu trạm thực | 4 | 2 | Không hồi âm sau 2 tuần | Dùng ngưỡng phân vị (`THRESHOLDS.md` phương án A) + đối chiếu báo chí | H |
| R5 | LSTM ngốn thời gian, không kịp | 3 | 3 | Hết W09 chưa có kết quả LSTM | **LightGBM là mô hình chính**, LSTM chỉ là phần so sánh — bỏ được mà không hỏng báo cáo | G |
| R6 | Đức kẹt mà không nói | 3 | 4 | Issue đứng yên > 3 ngày | Rule 45 phút + cột `Blocked` + pair-programming hằng tuần | G |
| R7 | Huyền quá tải do sức khoẻ / trùng lịch | 3 | 3 | Trễ deadline nội bộ 2 lần liên tiếp | Deadline nội bộ đã sớm 3 ngày; G nhận lại phần viết; giảm scope slide | G |
| R8 | Ranh giới xã sau sáp nhập 2025 không tìm được GeoJSON | 3 | 3 | Hết W05 chưa có file | Đổi đơn vị không gian sang tiểu lưu vực / ô lưới (xem `GAPS.md` mục 2) | D |
| R9 | Mô hình không tốt hơn dự báo GloFAS gốc | 3 | 4 | Baseline GloFAS thắng ở W08 | Đổi định vị sang "hiệu chỉnh sai số cục bộ" + cảnh báo theo xã (`GAPS.md` mục 3) | G |
| R10 | Rò rỉ dữ liệu tương lai trong lag feature | 2 | 5 | Kết quả đẹp bất thường (NSE > 0.98) | Test #5 trong `tests/`; walk-forward nghiêm ngặt; review chéo code split | G |
| R11 | Mất dữ liệu (ổ cứng / máy hỏng) | 2 | 5 | — | Backup Google Drive + HF Datasets **ngay sau khi crawl xong**, không đợi | G |
| R12 | Trùng lịch thi các môn khác cuối kỳ | 4 | 3 | — | Deadline nội bộ sớm 3 ngày; W14 để trống làm buffer | Cả 3 |
| R13 | Mất mạng / lỗi demo lúc thuyết trình | 2 | 4 | — | Quay sẵn video demo + screenshot dự phòng trong slide | D |
| R14 | Giáp ốm/bận đột xuất | 2 | 5 | — | `docs/RUNBOOK.md` + push code mỗi ngày + chia sẻ credential | G |

## Ngưỡng kích hoạt phương án B

Kiểm vào **cuối W05 (18/10)**. Nếu chưa có `data/processed/daily_panel.parquet` chạy được:

1. Rút phạm vi dữ liệu: 1984–2026 → **2010–2026**.
2. Rút số điểm lưới: 200 → **50** (chỉ giữ lưu vực sông Hương + sông Bồ).
3. Bỏ NASA POWER (vốn đã là "tuỳ chọn").
4. Bỏ LSTM, chỉ làm LightGBM.

Cả 4 việc này **không làm hỏng bất kỳ tiêu chí chấm nào** — chỉ cần giải thích lý do trong Limitations. Mất Report 3 mới là hỏng thật.
