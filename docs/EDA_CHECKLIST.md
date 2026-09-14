# CHECKLIST EDA — Report 2

Phụ trách: **D** · Tuần: **W4** · Đầu ra: `notebooks/03_eda.ipynb` + hình trong `reports/figures/`

Nguyên tắc chấm điểm của Report 2: **mỗi hình phải kèm một câu kết luận bằng lời**. Hình không có insight = hình bị trừ điểm. Sau mỗi mục dưới đây có ô "Kết luận" — viết 1–2 câu, H sẽ biên tập lại thành văn xuôi.

---

## 1. Tổng quan dữ liệu

- [ ] Khoảng thời gian thực tế, số dòng, số điểm lưới
- [ ] Bảng `describe()` cho discharge và mưa
- [ ] **% giá trị thiếu theo năm** — có năm nào thiếu bất thường không
- [ ] Kiểm tra giá trị vô lý: discharge âm, mưa âm, mưa > 1 000 mm/ngày
- [ ] Số ngày bị trùng / bị nhảy cóc

> **Kết luận:** ______

## 2. Tính mùa vụ

- [ ] Phân bố discharge trung bình theo **tháng** (boxplot 12 tháng)
- [ ] Phân bố mưa theo tháng
- [ ] Xác định **mùa lũ** bằng số liệu, không nói theo cảm tính
- [ ] So mùa lũ tìm được với mốc 9–12 trong `src/config.py:FLOOD_SEASON_MONTHS` — khớp không?

> **Kết luận:** ______

## 3. Tương quan mưa – lưu lượng theo độ trễ ⭐ mục quan trọng nhất

- [ ] Cross-correlation giữa mưa ngày và discharge, **lag 0 → 7 ngày**
- [ ] Vẽ biểu đồ hệ số tương quan theo lag
- [ ] **Lag nào cho tương quan cao nhất?** → đây là căn cứ chọn feature, ghi lại con số
- [ ] Làm riêng cho **mùa lũ** và **mùa khô** — lag có khác nhau không
- [ ] Làm riêng cho từng tiểu lưu vực — thượng nguồn có lag dài hơn hạ nguồn không

> **Kết luận (dùng thẳng cho mục feature engineering):** ______

## 4. Mưa tích luỹ và độ ẩm nền

- [ ] Tương quan giữa discharge và mưa tích luỹ **3 / 5 / 7 ngày**
- [ ] Mưa tích luỹ có tương quan mạnh hơn mưa một ngày không?
- [ ] Chỉ số API (antecedent precipitation index) so với mưa tích luỹ — cái nào tốt hơn

> **Kết luận:** ______

## 5. Ba đợt lũ lịch sử

Với mỗi đợt **1999 · 2020 · 2023**:

- [ ] Vẽ chuỗi discharge + mưa trong cửa sổ ±30 ngày quanh đỉnh
- [ ] Đỉnh discharge là bao nhiêu, rơi vào ngày nào
- [ ] **Độ trễ thực tế từ đỉnh mưa đến đỉnh lũ** là mấy ngày
- [ ] Đối chiếu với `data/external/flood_events.csv` — GloFAS có "bắt" được đợt này không
- [ ] Nếu GloFAS **không** thấy đợt lũ đã biết → báo G ngay, nghi sai ô lưới (`RISKS.md` R1)

> **Kết luận:** ______

## 6. Phân bố cực trị

- [ ] Histogram discharge ở thang log
- [ ] Phân vị Q90 / Q95 / Q99 / Q99.5 cho cả năm và riêng mùa lũ
- [ ] Số ngày vượt từng ngưỡng BĐ (lấy từ `docs/THRESHOLDS.md` §4) **theo từng năm**
- [ ] ⚠️ Con số này quyết định bài toán phân loại có đủ mẫu hay không — xem quy tắc 30 mẫu ở `RESEARCH_DESIGN.md` §3.4

> **Kết luận (ghi rõ số ngày dương mỗi ngưỡng):** ______

## 7. So sánh hai chế độ dữ liệu quanh mốc 07/2022

- [ ] Thống kê discharge **trước** và **sau** 07/2022 có khác nhau rõ rệt không
- [ ] Nếu khác nhiều → là bằng chứng cho việc bắt buộc tách split (`DATA_SPLITS.md` §1), đưa hình này vào báo cáo

> **Kết luận:** ______

## 8. Không gian *(phối hợp với G)*

- [ ] Bản đồ mưa trung bình năm trên lưới
- [ ] Vị trí các điểm lưới + trạm Kim Long / Phú Ốc trên nền bản đồ sông
- [ ] Mưa thượng nguồn và hạ nguồn khác nhau bao nhiêu

> **Kết luận:** ______

---

## Quy ước hình cho báo cáo

- Kích thước xuất: `dpi=140`, rộng 10–14 inch cho chuỗi thời gian
- Lưu vào `reports/figures/`, tên dạng `eda_<mục>_<nội dung>.png`
- **Mọi trục phải có nhãn kèm đơn vị** (`Lưu lượng (m³/s)`, `Mưa (mm/ngày)`)
- Đọc được khi in đen trắng — đừng chỉ phân biệt bằng màu
- Tiêu đề hình bằng tiếng Việt, khớp với caption trong báo cáo

## Xong khi

- [ ] Đủ 8 mục, mỗi mục có ít nhất 1 hình và 1 kết luận đã viết
- [ ] Notebook chạy lại từ đầu không lỗi (`Restart & Run All`)
- [ ] Đã xoá output trước khi commit (`nbstripout`)
- [ ] G đã review và không còn comment mở
