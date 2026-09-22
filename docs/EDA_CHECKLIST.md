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

> **Kết luận:** 6 087 ngày 2010-01-01 → 2026-08-31, **0 % thiếu** ở cả lưu lượng lẫn mưa. Phân bố lệch rất mạnh (hệ số bất đối xứng **5,91**): trung vị chỉ 49,9 m³/s trong khi cực đại 3 588 m³/s ngày 08/11/2011. Hệ quả trực tiếp: mọi mô hình phải học trên thang log, và **không được dùng accuracy** làm thước đo. Hình `eda1_tong_quan.png`.

## 2. Tính mùa vụ

- [ ] Phân bố discharge trung bình theo **tháng** (boxplot 12 tháng)
- [ ] Phân bố mưa theo tháng
- [ ] Xác định **mùa lũ** bằng số liệu, không nói theo cảm tính
- [ ] So mùa lũ tìm được với mốc 9–12 trong `src/config.py:FLOOD_SEASON_MONTHS` — khớp không?

> **Kết luận:** Mùa lũ chính vụ là **tháng 10–12**, đỉnh ở **tháng 10** (Q trung vị 118,3 m³/s, gấp ~3,9 lần tháng thấp nhất 30,4). Bốn tháng 9–12 gánh **58,6 %** tổng dòng chảy cả năm. Vì vậy `doy_sin`/`doy_cos` là feature bắt buộc, và mọi phép chia tập phải giữ nguyên mùa lũ trong cả train lẫn test. Hình `eda2_mua_vu.png`.

## 3. Tương quan mưa – lưu lượng theo độ trễ ⭐ mục quan trọng nhất

- [ ] Cross-correlation giữa mưa ngày và discharge, **lag 0 → 7 ngày**
- [ ] Vẽ biểu đồ hệ số tương quan theo lag
- [ ] **Lag nào cho tương quan cao nhất?** → đây là căn cứ chọn feature, ghi lại con số
- [ ] Làm riêng cho **mùa lũ** và **mùa khô** — lag có khác nhau không
- [ ] Làm riêng cho từng tiểu lưu vực — thượng nguồn có lag dài hơn hạ nguồn không

> **Kết luận (dùng thẳng cho mục feature engineering):** Mưa dẫn trước lưu lượng đúng **1 ngày** (r = 0,789), và **lag này giống nhau ở cả ba tiểu lưu vực** (thượng 0,790 · trung 0,765 · hạ 0,729) lẫn cả hai mùa. Không phải vì thượng nguồn không xa hơn, mà vì thời gian truyền lũ từ Thượng Nhật về Kim Long chỉ **5–6 giờ trên 51 km** (bài báo ĐH Huế 131/4A/2022) — **ngắn hơn một ngày, nên độ phân giải ngày không tách được**. Đây chính là chỗ dữ liệu mưa **theo giờ** có thể ăn thêm điểm nếu còn thời gian. Hình `eda3_lag.png`.

## 4. Mưa tích luỹ và độ ẩm nền

- [ ] Tương quan giữa discharge và mưa tích luỹ **3 / 5 / 7 ngày**
- [ ] Mưa tích luỹ có tương quan mạnh hơn mưa một ngày không?
- [ ] Chỉ số API (antecedent precipitation index) so với mưa tích luỹ — cái nào tốt hơn

> **Kết luận:** Mưa **tích luỹ 3 ngày** là biến mưa mạnh nhất: r = **0,863**, so với mưa 1 ngày chỉ 0,642 và mưa 14 ngày 0,568. Quan trọng hơn: với **cùng một trận mưa lớn** (trên phân vị 95), nền đất ẩm cho lưu lượng **585 m³/s** còn nền khô chỉ **85 m³/s** — **gấp 6,9 lần**. Độ ẩm nền không phải biến phụ, nó quyết định phản ứng của lưu vực. Giữ cả `api` lẫn các cửa sổ mưa tích luỹ. Hình `eda4_api.png`.

## 5. Ba đợt lũ lịch sử

Với mỗi đợt **1999 · 2020 · 2023**:

- [ ] Vẽ chuỗi discharge + mưa trong cửa sổ ±30 ngày quanh đỉnh
- [ ] Đỉnh discharge là bao nhiêu, rơi vào ngày nào
- [ ] **Độ trễ thực tế từ đỉnh mưa đến đỉnh lũ** là mấy ngày
- [ ] Đối chiếu với `data/external/flood_events.csv` — GloFAS có "bắt" được đợt này không
- [ ] Nếu GloFAS **không** thấy đợt lũ đã biết → báo G ngay, nghi sai ô lưới (`RISKS.md` R1)

> **Kết luận:** Ba đợt cho thấy **mực nước và lưu lượng không đi cùng nhau**: 2020-10b có H = 4,17 m ứng Q = 2 060 m³/s, nhưng 2023-11 có H **cao hơn** (4,34 m) mà Q chỉ **584 m³/s** — thấp hơn 3,5 lần. Trên 12 đợt trong khoảng panel, ln(Q) → H chỉ đạt **R² = 0,184**, trong khi ln(mưa) → ln(Q) đạt **0,691**. Khâu yếu là bước lưu lượng → mực nước, không phải GloFAS. Xem `FINDINGS_REGIME.md` §4. Hình `eda5_su_kien.png`.

## 6. Phân bố cực trị

- [ ] Histogram discharge ở thang log
- [ ] Phân vị Q90 / Q95 / Q99 / Q99.5 cho cả năm và riêng mùa lũ
- [ ] Số ngày vượt từng ngưỡng BĐ (lấy từ `docs/THRESHOLDS.md` §4) **theo từng năm**
- [ ] ⚠️ Con số này quyết định bài toán phân loại có đủ mẫu hay không — xem quy tắc 30 mẫu ở `RESEARCH_DESIGN.md` §3.4

> **Kết luận (ghi rõ số ngày dương mỗi ngưỡng):** p90 = 258,4 m³/s → **610 ngày** · p95 = 430,2 → **305 ngày** · p99 = 1 168,8 → **61 ngày** · p99,5 = 1 556,0 → **31 ngày**. Ngưỡng p99 trở lên đã chạm **luật 30 mẫu** (`SPEC.md`): p99,5 chỉ có 31 ngày dương trên toàn chuỗi, nên nếu chia test thì số ngày dương trong test còn ít hơn nữa và **không được dùng làm kết luận chính**. Hình `eda6_cuc_tri.png`.

## 7. So sánh hai chế độ dữ liệu quanh mốc 07/2022

- [ ] Thống kê discharge **trước** và **sau** 07/2022 có khác nhau rõ rệt không
- [ ] Nếu khác nhiều → là bằng chứng cho việc bắt buộc tách split (`DATA_SPLITS.md` §1), đưa hình này vào báo cáo

> **Kết luận:** **Không có bằng chứng đổi biên độ.** Trung vị 49,9 (trước) so với 49,4 (sau); p99 1 126,8 so với 1 216,9. Phép thử chặt hơn — cùng lượng mưa thì lưu lượng phản ứng thế nào — cho thấy chỉ **1/5 khoảng mưa** có khác biệt vượt KTC 95 %, và tỉ số đỉnh-trên-mưa lại đi **ngược chiều** (+16 %). Vẫn **giữ nguyên việc tách test từ 2022-07-01** vì đó là kỷ luật đúng, nhưng R21 được hạ cấp. Chi tiết `FINDINGS_REGIME.md`. Hình `eda7_che_do.png`.

## 8. Không gian *(phối hợp với G)*

- [ ] Bản đồ mưa trung bình năm trên lưới
- [ ] Vị trí các điểm lưới + trạm Kim Long / Phú Ốc trên nền bản đồ sông
- [ ] Mưa thượng nguồn và hạ nguồn khác nhau bao nhiêu

> **Kết luận:** Ba tiểu lưu vực có lượng mưa trung bình khá gần nhau (thượng 8,36 · trung 8,41 · hạ 6,64 mm/ngày) sau khi đã sửa lưới về 64 ô đều (`CRAWL_EXPLAINED.md` §8b). Tương quan với lưu lượng giảm dần từ thượng xuống hạ, đúng với kỳ vọng thuỷ văn: nước sinh ra ở thượng nguồn. Hình `eda8_khong_gian.png`.

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
