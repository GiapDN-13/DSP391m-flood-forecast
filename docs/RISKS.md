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
| R9 | Mô hình không thắng nổi persistence | **3** ⬆ | 5 | Persistence đã đạt NSE 0,542 ở h=1 | ⚠️ **Lập luận phòng vệ cũ đã mất** — không có dự báo GloFAS quá khứ để làm feature. Mốc đối chứng giờ là persistence, và nó mạnh ở h=1. Cơ hội thật nằm ở h=2 và h=3 nơi persistence sụp | G |
| R18 | GloFAS không mô phỏng vận hành hồ chứa (Tả Trạch, Bình Điền) | 3 | 4 | Đỉnh lưu lượng lớn mà không có mưa, ví dụ 2025-06-14: 2 055 m³/s với 0,9 mm mưa | Kiểm khi EDA; nếu đúng thì đây là hạn chế lớn phải nêu rõ trong Limitations | D |
| R10 | Rò rỉ dữ liệu tương lai trong lag feature | 2 | 5 | Kết quả đẹp bất thường (NSE > 0.98) | Test #5 trong `tests/`; walk-forward nghiêm ngặt; review chéo code split | G |
| R11 | ~~Mất dữ liệu (ổ cứng / máy hỏng)~~ **ĐÃ XỬ LÝ 17/09** | 2 | 2 ⬇ | — | Release `data-2026-09-17` trên repo, 95 MB. `scripts/restore_data.py` đã kiểm khôi phục bit-for-bit. Tạo bản mới sau mỗi lần dữ liệu đổi đáng kể | G |
| R12 | Trùng lịch thi các môn khác | 4 | 4 | — | Lịch 9 tuần gần như không có buffer — bám chốt kiểm tra trong `PLAN.md`, trễ là cắt scope ngay | Cả 3 |
| R13 | Mất mạng / lỗi demo lúc thuyết trình | 2 | 4 | — | Quay sẵn video demo + screenshot dự phòng trong slide | D |
| R17 | Không bật được bảo vệ nhánh (repo private, tài khoản free) | — | 2 | Có commit vào `main` không qua PR | Quy ước thay thế trong `GIT_WORKFLOW.md` §2; G rà `git log --first-parent main` hằng tuần | G |
| R15 | Không thu đủ 15 sự kiện lũ có công bố đỉnh mực nước | 3 | **5** ⬆ | Hết W2 mà `flood_events.csv` < 10 dòng | ⬆ **Mức ảnh hưởng tăng vì R1 đã bị loại — R2 giờ là đường duy nhất.** Hạ xuống 10 sự kiện + nới cửa sổ ghép ±3 ngày; không đủ thì lùi R4 và đổi tên nhãn | H |
| R16 | ~~GloFAS không phân giải được Hương và Bồ~~ **ĐÃ XẢY RA, ĐÃ XỬ LÝ** | — | 3 | — | Xác nhận bằng diện tích lưu vực suy ra (mọi ô ứng viên lệch ≥ 84 % so với 938 km²). Đã thu hẹp còn trạm Kim Long, nêu ở Limitations | G |
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
