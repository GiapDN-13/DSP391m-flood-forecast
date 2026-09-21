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
| R18 | GloFAS không mô phỏng vận hành hồ chứa (Tả Trạch, Bình Điền, Hương Điền) | ~~3~~ **ĐÃ XÁC NHẬN 21/09** | **5** ⬆ | Quan hệ H–Q mất tính đơn điệu khi trộn thời kỳ trước/sau 2009: 1998 Q=3 161→H=4,47 m nhưng 1999 Q=1 900→H=5,81 m | Phải fit ánh xạ riêng từ 2009; N tụt từ 11 xuống 7. Nêu rõ trong Limitations. `FINDINGS_EVENTS.md` §4 | D |
| R10 | Rò rỉ dữ liệu tương lai trong lag feature | 2 | 5 | Kết quả đẹp bất thường (NSE > 0.98) | Test #5 trong `tests/`; walk-forward nghiêm ngặt; review chéo code split | G |
| R11 | ~~Mất dữ liệu (ổ cứng / máy hỏng)~~ **ĐÃ XỬ LÝ 17/09** | 2 | 2 ⬇ | — | Release `data-2026-09-17` trên repo, 95 MB. `scripts/restore_data.py` đã kiểm khôi phục bit-for-bit. Tạo bản mới sau mỗi lần dữ liệu đổi đáng kể | G |
| R12 | Trùng lịch thi các môn khác | 4 | 4 | — | Lịch 9 tuần gần như không có buffer — bám chốt kiểm tra trong `PLAN.md`, trễ là cắt scope ngay | Cả 3 |
| R13 | Mất mạng / lỗi demo lúc thuyết trình | 2 | 4 | — | Quay sẵn video demo + screenshot dự phòng trong slide | D |
| R17 | Không bật được bảo vệ nhánh (repo private, tài khoản free) | — | 2 | Có commit vào `main` không qua PR | Quy ước thay thế trong `GIT_WORKFLOW.md` §2; G rà `git log --first-parent main` hằng tuần | G |
| R15 | ~~Không thu đủ 15 sự kiện~~ **ĐÃ THU ĐỦ 21/09** nhưng **chỉ 7 dùng được để hiệu chuẩn** | 3 | **5** | Tập chính N = 7 < 10 | ⬆ **Mức ảnh hưởng tăng vì R1 đã bị loại — R2 giờ là đường duy nhất.** Hạ xuống 10 sự kiện + nới cửa sổ ghép ±3 ngày; không đủ thì lùi R4 và đổi tên nhãn | H |
| R16 | ~~GloFAS không phân giải được Hương và Bồ~~ **ĐÃ XẢY RA, ĐÃ XỬ LÝ** | — | 3 | — | Xác nhận bằng diện tích lưu vực suy ra (mọi ô ứng viên lệch ≥ 84 % so với 938 km²). Đã thu hẹp còn trạm Kim Long, nêu ở Limitations | G |
| R19 | Job tự động báo thành công nhưng sản phẩm sai/thiếu | ~~3~~ **ĐÃ XẢY RA** | 3 | Số file trong `reports/forecast_log/` ít hơn số ngày | ✅ Mất bản 20/09 dù Actions xanh 6 lần (`date.today()` = ngày UTC, job nổ quanh nửa đêm UTC, ghi đè bản hôm trước). Đã dùng `ict_today()`, chặn ghi đè, lịch 22:00 → 20:00 UTC, `scripts/check_forecast_log.py` chạy trong job nên thiếu ngày là job ĐỎ | G |
| R20 | Chuỗi GloFAS thiếu 13 năm đầu mà nghiệm thu không phát hiện | ~~2~~ **ĐÃ XẢY RA** | 3 | 15 584 dòng nhưng chỉ 10 835 ngày có giá trị | ✅ 1984–1996 rỗng 100 % ở cả 83 ô. Nghiệm thu FR-D1 cũ đếm **số dòng**, panel lại bắt đầu 2010 nên mọi kiểm tra báo sạch. Đã sửa nghiệm thu sang **số ngày không rỗng**, thêm `tests/test_data_coverage.py`, sửa 16 chỗ ghi "1984" kể cả PDF Report 1 | G |
| R21 | Chuỗi sau mốc gãy 2022-07-01 có thể lệch biên độ so với tái phân tích | **4** | **5** | Trận 15/11/2023 đỉnh 4,34 m mà GloFAS chỉ 584 m³/s; kiểm chứng ngoài mẫu chệch −1,94 m một chiều | 🔴 **Việc số 1 của W2.** Nếu đúng thì hệ thống vận hành đang chạy trên chế độ dữ liệu khác chế độ huấn luyện — ảnh hưởng toàn dự án, không chỉ FR-T2 | G |
| R22 | Lưới mưa không đều làm lệch mưa lưu vực | **ĐÃ XẢY RA** | 2 | 68 ô mưa gồm 52 ô lưới 0,10° (thiếu 12) + 16 ô sót từ lưới 0,15° đã bỏ | `aggregate_rain()` lấy trung bình các ô nên vùng nhiều ô hơn bị cân nặng hơn. Sửa rẻ: crawl 12 ô 0,10° còn thiếu rồi bỏ 16 ô lẻ (~vài phút). Xem `CRAWL_EXPLAINED.md` §8b | G |
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
