# PHÁT HIỆN — chi phí crawl và hạn mức Open-Meteo

**Ngày:** 15/09/2026 · **Liên quan:** `RISKS.md` R3 · `SPEC.md` NFR-2, NFR-13
**Trạng thái:** đã đo lại, bản v1 của tài liệu này kết luận sai — xem §3.

## 1. Kết quả đo thật

Toàn bộ dữ liệu thô của dự án crawl xong trong **~35 phút**:

| Pha | Số task | Thời gian | Lỗi 429 |
|---|---|---|---|
| Mưa ngày ERA5 2010–2026 | 26 | ~3 phút | 0 |
| Quét mạng sông (probe 1 năm, mọi ô) | 316 | ~10 phút | 0 |
| Mưa dự báo lưu trữ 2022–nay | 26 | ~2 phút | 0 |
| Lưu lượng 1984–2026 yêu cầu (thực có 1997–2026) | 40 | ~6 phút | 15 |
| **Mưa giờ ERA5 2015–2026** | **300** | **14 phút** | **0** |

**Tổng ~48 MB Parquet.** Không phải 5–15 GB như ước tính trong kế hoạch gốc.

Tài nguyên máy: **RAM ~105 MB, CPU ~2 %**. Crawler gần như chỉ ngồi chờ mạng.

## 2. Nguyên nhân thật của cơn 429 ban đầu

**Không phải do hạn mức.** Do `pkill` của Git Bash không giết được tiến trình Python trên Windows, nên sau vài lần khởi động lại đã có **3 crawler và 4 monitor chạy song song**. Chúng tự ép nhau vào 429, nhịp gọi bị đẩy lên kịch trần 12 giây.

Chạy đúng **một** tiến trình: 429 về 0, nhịp về mức sàn 0,7 giây, tốc độ ~22 task/phút ổn định.

👉 Đã thêm khoá chống chạy trùng (`SingleInstance` trong `crawl_all.py`) để không tái diễn.

## 3. ⚠️ Bản v1 của tài liệu này đã kết luận sai

Bản đầu tiên quy cơn 429 thành "hạn mức tính theo khối lượng, ~10.000 đơn vị/ngày", rồi suy ra rằng `rain_hourly` tốn "~189.000 đơn vị ≈ 19 ngày hạn mức" và **đề xuất loại nó khỏi phạm vi**.

Thực tế: `rain_hourly` chạy **14 phút, 0 lỗi 429**. Tổng cả dự án tiêu ~190.000 đơn vị theo công thức ước lượng mà không hề bị chặn.

Rút ra:
- Công thức `ceil(ngày/14) × ceil(biến/10)` có thể đúng về cách Open-Meteo *đếm*, nhưng **con số hạn mức 10.000/ngày là tôi đoán, không phải đo**.
- Sai lầm về phương pháp: **quy một triệu chứng cho nguyên nhân chưa kiểm chứng**, rồi cắt phạm vi dự án dựa trên đó. Đúng ra phải loại trừ nguyên nhân tự gây ra trước.
- Bài học cho cả nhóm: gặp 429 thì việc đầu tiên là **đếm xem đang chạy bao nhiêu tiến trình**, không phải vội đổ cho nhà cung cấp.

## 4. Phạm vi đã khôi phục

| Hạng mục | Bản v1 (sai) | Hiện tại |
|---|---|---|
| `rain_hourly` | loại khỏi phạm vi | **giữ lại**, nằm trong lượt mặc định |
| Lưới mưa | thưa xuống 0,15° (25 điểm) | **0,10° (64 điểm)** như kế hoạch gốc |
| `FR-D2` trong SPEC | đổi sang "mưa ngày" | **khôi phục "mưa giờ"** |

Phần **giữ nguyên** vì tự thân nó đúng, không liên quan tới hạn mức:
- **Tách probe / full** khi quét mạng sông: xin 1 năm cho mọi ô rồi mới xin 42 năm cho ô có dòng chảy. Tiết kiệm thật, và cho bản đồ mạng sông đầy đủ 316 ô.
- **Nhịp gọi tự điều chỉnh** và **khoá chống chạy trùng**.

## 5. Kết luận cho dự án

- Dữ liệu thô **không phải là nút thắt**. Toàn bộ crawl lại từ đầu mất chưa tới 1 giờ.
- Chốt kiểm tra "hết W3 phải có dữ liệu" trong `PLAN.md` giờ rất thoải mái.
- **Nút thắt thật vẫn là `docs/FINDINGS_GRID.md`**: chọn đúng ô lưới, và câu hỏi GloFAS có tách được sông Hương với sông Bồ hay không. Đó là việc cần mắt người, không phải việc cần thêm dữ liệu.
- `NFR-13` (chi phí 0 đồng) giữ nguyên, không phải đánh đổi gì.

## 6. Đưa vào báo cáo

- **Report 2 – Data Collection:** nêu quy mô thật (số điểm lưới, khoảng thời gian, dung lượng, thời gian crawl) và thiết kế crawler chịu lỗi (retry, cache, checkpoint, khoá chống chạy trùng). Đây là chi tiết kỹ thuật thật, ăn điểm.
- **Không cần** đưa phần hạn mức vào Limitations nữa — hoá ra không phải hạn chế.
