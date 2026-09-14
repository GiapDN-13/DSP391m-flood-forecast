# SỔ RỦI RO

Cập nhật mỗi thứ 4 trong buổi họp. `P` = xác suất, `I` = mức ảnh hưởng (1 thấp – 5 cao).

| # | Rủi ro | P | I | Dấu hiệu sớm | Phương án xử lý | Ai canh |
|---|---|---|---|---|---|---|
| R1 | Ô lưới GloFAS không trùng dòng sông thật | ~~3~~ **ĐÃ XẢY RA** | 5 | Discharge trung bình quá nhỏ (< 20 m³/s) hoặc phẳng lì | ✅ Quét lần 1 ngày 15/09 đã phát hiện toạ độ kế hoạch gốc sai ô (5,7 vs 308 m³/s). Còn phải quét tinh step 0.05° + đối chiếu bản đồ OSM, và quét trạm Phú Ốc | G |
| R2 | **Crawl không kịp trước W3** | 4 | 5 | Hết W2 mà < 70 % lưới xong | Cắt tiếp: mưa còn 2015–2026, lưới còn 25 điểm | G |
| R3 | Rate limit API | 3 | 3 | HTTP 429 | Gộp nhiều ngày vào 1 request, sleep 1–2 s, cache theo file, chạy đêm | G |
| R4 | Không xin được số liệu trạm thực (đường R1) | 4 | 2 | Không hồi âm sau 2 tuần | Đã có kế hoạch: đường **R2** (hiệu chuẩn theo sự kiện lịch sử) không cần số liệu trạm — xem `THRESHOLDS.md` §3 | H |
| R5 | LSTM ngốn thời gian | 4 | 1 | — | **Đã cắt khỏi phạm vi chính từ W1.** Chỉ làm ở W8 nếu dư thời gian | G |
| R6 | Có người kẹt mà không báo | 3 | 4 | Issue đứng yên > 2 ngày | Rule 45 phút + cột `Blocked` + pair-programming hằng tuần | G |
| R7 | Khối lượng biên tập dồn vào tuần nộp báo cáo | 3 | 3 | Trễ deadline nội bộ 2 lần liên tiếp | Deadline nội bộ sớm 2–3 ngày; G nhận lại phần viết nội dung; giảm scope slide | G |
| R8 | Ranh giới xã sau sáp nhập 2025 không tìm được GeoJSON | 3 | 3 | Hết W3 chưa có file | Đổi đơn vị không gian sang tiểu lưu vực / ô lưới (xem `GAPS.md` mục 2) | D |
| R9 | Mô hình không tốt hơn dự báo GloFAS gốc | 2 | 4 | Baseline GloFAS thắng ở W5 | **Đã phòng từ thiết kế:** GloFAS là feature đầu vào nên mô hình chỉ học phần dư (`RESEARCH_DESIGN.md` §1.2) | G |
| R10 | Rò rỉ dữ liệu tương lai trong lag feature | 2 | 5 | Kết quả đẹp bất thường (NSE > 0.98) | Test #5 trong `tests/`; walk-forward nghiêm ngặt; review chéo code split | G |
| R11 | Mất dữ liệu (ổ cứng / máy hỏng) | 2 | 5 | — | Backup Google Drive + HF Datasets **ngay sau khi crawl xong**, không đợi | G |
| R12 | Trùng lịch thi các môn khác | 4 | 4 | — | Lịch 9 tuần gần như không có buffer — bám chốt kiểm tra trong `PLAN.md`, trễ là cắt scope ngay | Cả 3 |
| R13 | Mất mạng / lỗi demo lúc thuyết trình | 2 | 4 | — | Quay sẵn video demo + screenshot dự phòng trong slide | D |
| R15 | Không thu đủ 15 sự kiện lũ có công bố đỉnh mực nước | 3 | 4 | Hết W2 mà `flood_events.csv` < 10 dòng | Hạ xuống 10 sự kiện + nới cửa sổ ghép lên ±3 ngày; không đủ nữa thì lùi về R4 (phân vị) và đổi tên nhãn | H |
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
