# SỔ RỦI RO

Cập nhật mỗi thứ 4 trong buổi họp. `P` = xác suất, `I` = mức ảnh hưởng (1 thấp – 5 cao).

| # | Rủi ro | P | I | Dấu hiệu sớm | Phương án xử lý | Ai canh |
|---|---|---|---|---|---|---|
| R1 | Ô lưới GloFAS không trùng dòng sông thật | ~~3~~ **ĐÃ XẢY RA** | 5 | Discharge trung bình quá nhỏ hoặc phẳng lì | ✅ Đã quét 121 ô ngày 15/09: toạ độ kế hoạch gốc sai (5,7 vs 308 m³/s), mạng sông lệch ~7 km. **Việc còn lại: đối chiếu OSM bằng mắt** — xem `FINDINGS_GRID.md` | G |
| R2 | ~~Crawl không kịp trước W3~~ **ĐÃ GIẢI QUYẾT 15/09** | — | — | — | Toàn bộ dữ liệu thô crawl xong trong ~35 phút, 48 MB. Không còn là rủi ro | G |
| R3 | Rate limit API | 1 ⬇ | 2 | HTTP 429 | **Hoá ra không phải rủi ro thật.** Cơn 429 ngày 15/09 là do tự chạy trùng 3 crawler; chạy 1 tiến trình thì 0 lỗi. Toàn bộ crawl xong trong ~35 phút. Đã có khoá chống chạy trùng. Xem `FINDINGS_QUOTA.md` | G |
| R4 | ~~Không xin được số liệu trạm thực~~ **ĐÃ XẢY RA** | — | 2 | — | Không gửi công văn. R1 loại khỏi phạm vi; dùng R2 + R3. Nêu trong Limitations | H |
| R5 | LSTM ngốn thời gian | 4 | 1 | — | **Đã cắt khỏi phạm vi chính từ W1.** Chỉ làm ở W8 nếu dư thời gian | G |
| R6 | Có người kẹt mà không báo | 3 | 4 | Issue đứng yên > 2 ngày | Rule 45 phút + cột `Blocked` + pair-programming hằng tuần | G |
| R7 | Khối lượng biên tập dồn vào tuần nộp báo cáo | 3 | 3 | Trễ deadline nội bộ 2 lần liên tiếp | Deadline nội bộ sớm 2–3 ngày; G nhận lại phần viết nội dung; giảm scope slide | G |
| R8 | Ranh giới xã sau sáp nhập 2025 không tìm được GeoJSON | 3 | 3 | Hết W3 chưa có file | Đổi đơn vị không gian sang tiểu lưu vực / ô lưới (xem `GAPS.md` mục 2) | D |
| R9 | Mô hình không tốt hơn dự báo GloFAS gốc | 2 | 4 | Baseline GloFAS thắng ở W5 | **Đã phòng từ thiết kế:** GloFAS là feature đầu vào nên mô hình chỉ học phần dư (`RESEARCH_DESIGN.md` §1.2) | G |
| R10 | Rò rỉ dữ liệu tương lai trong lag feature | 2 | 5 | Kết quả đẹp bất thường (NSE > 0.98) | Test #5 trong `tests/`; walk-forward nghiêm ngặt; review chéo code split | G |
| R11 | Mất dữ liệu (ổ cứng / máy hỏng) | 2 | 5 | — | Backup Google Drive + HF Datasets **ngay sau khi crawl xong**, không đợi | G |
| R12 | Trùng lịch thi các môn khác | 4 | 4 | — | Lịch 9 tuần gần như không có buffer — bám chốt kiểm tra trong `PLAN.md`, trễ là cắt scope ngay | Cả 3 |
| R13 | Mất mạng / lỗi demo lúc thuyết trình | 2 | 4 | — | Quay sẵn video demo + screenshot dự phòng trong slide | D |
| R15 | Không thu đủ 15 sự kiện lũ có công bố đỉnh mực nước | 3 | **5** ⬆ | Hết W2 mà `flood_events.csv` < 10 dòng | ⬆ **Mức ảnh hưởng tăng vì R1 đã bị loại — R2 giờ là đường duy nhất.** Hạ xuống 10 sự kiện + nới cửa sổ ghép ±3 ngày; không đủ thì lùi R4 và đổi tên nhãn | H |
| R16 | GloFAS không phân giải được sông Hương và sông Bồ thành 2 dòng riêng | 3 | 4 | Chỉ tìm thấy 1 dòng > 100 m³/s trong vùng quét | Thu hẹp còn 1 trạm Kim Long, hoặc phát biểu lại bài toán ở mức hệ thống sông gộp — `FINDINGS_GRID.md` §4 | G |
| R14 | G vắng mặt đột xuất — **ảnh hưởng nặng nhất** | 2 | 5 | — | `docs/RUNBOOK.md` + push code mỗi ngày + chia sẻ credential | G |

## Chốt kiểm tra & cắt scope

Lịch 9 tuần nên **cắt scope là công cụ điều khiển chính**, không phải dấu hiệu thất bại. Phần lớn scope đã cắt sẵn từ W1 (xem `docs/PLAN.md` mục "Scope đã cắt sẵn"). Nếu vẫn trễ:

| Chốt | Điều kiện phải đạt | Không đạt thì cắt tiếp |
|---|---|---|
| **Hết W1** | Đã chốt ô lưới GloFAS, crawl discharge đang chạy | Cả team dừng việc khác, tập trung crawl |
| **Hết W3** | Có `daily_panel.parquet` + bảng ngưỡng BĐ | Mưa rút còn 2015–2026; lưới còn 25 điểm; ngưỡng lùi về R4 (phân vị) |
| **Hết W6** | Bảng metric đầy đủ 2 kịch bản A/B | Bỏ kịch bản B, chỉ báo cáo A, nêu rõ trong Limitations |
| **Hết W8** | Report 3 đã nộp | — |

Thứ tự hy sinh khi thiếu thời gian: **LSTM → trang dashboard phụ → kịch bản B → độ dài chuỗi dữ liệu → số điểm lưới**.

Thứ **không bao giờ** hy sinh: baseline GloFAS thô · walk-forward đúng cách · ánh xạ ngưỡng BĐ · bộ metric sự kiện hiếm · SHAP.
