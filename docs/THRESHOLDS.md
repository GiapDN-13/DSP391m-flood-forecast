# NGƯỠNG BÁO ĐỘNG LŨ — quy đổi từ cấp BĐ của Việt Nam sang lưu lượng

> **Quyết định của nhóm (chốt 15/09/2026):** lấy **cấp báo động chính thức của Việt Nam làm gốc**, rồi quy đổi sang lưu lượng GloFAS. Không dùng ngưỡng phân vị tự chế làm định nghĩa chính.
>
> Đây là điểm ăn điểm lớn: sản phẩm nói cùng ngôn ngữ với cơ quan phòng chống thiên tai, thay vì đẻ ra một thang đo riêng không ai dùng.

## 1. Vấn đề đơn vị

| | Đại lượng | Nguồn |
|---|---|---|
| Ngưỡng pháp lý BĐ I / II / III | **mực nước H (m)** tại trạm thuỷ văn | Quyết định của Thủ tướng Chính phủ |
| Dữ liệu nhóm có | **lưu lượng Q (m³/s)**, mô phỏng, trung bình ngày | GloFAS v4 qua Open-Meteo |

Cần một ánh xạ **H → Q**. Cả file này là quy trình xây dựng ánh xạ đó.

## 2. Ngưỡng pháp lý — điền và ĐỐI CHIẾU trước khi dùng

**Nguồn pháp lý cần trích dẫn:** Quyết định **05/2020/QĐ-TTg** ngày 31/01/2020 của Thủ tướng Chính phủ *"Quy định mực nước tương ứng với các cấp báo động lũ trên các sông thuộc phạm vi cả nước"* — xem Phụ lục phần sông thuộc Thừa Thiên Huế (nay là TP. Huế).

| Trạm | Sông | BĐ I (m) | BĐ II (m) | BĐ III (m) | Đã đối chiếu văn bản gốc? |
|---|---|---|---|---|---|
| Kim Long | Hương | 1,00 | 2,00 | 3,50 | ☐ |
| Phú Ốc | Bồ | 1,50 | 3,00 | 4,50 | ☐ |

> ⚠️ **Các số trên là giá trị được trích dẫn phổ biến trong bản tin KTTV, CHƯA phải là số đã tra từ văn bản gốc.** H tra Phụ lục QĐ 05/2020/QĐ-TTg trên `vanban.chinhphu.vn` hoặc `thuvienphapluat.vn`, xác nhận hoặc sửa lại, rồi tick ô cuối và ghi số hiệu trang. **Sai một con số ở đây là sai toàn bộ nhãn của bài toán phân loại.**
>
> Cũng kiểm tra luôn: sau sáp nhập hành chính 2025 có văn bản nào thay thế/điều chỉnh QĐ 05/2020 không.

## 3. Ba đường quy đổi H → Q

> 🔴 **Cập nhật 15/09/2026: đường R1 đã bị loại** — nhóm không gửi được công văn xin số liệu trạm.
> ⇒ **R2 là đường duy nhất**, R3 là cách kiểm chứng chéo duy nhất. Điều này làm `FR-D7` (thu ≥15 sự kiện lũ có nguồn) trở thành **việc quan trọng nhất của H**, vì không còn đường lui nào ngoài R4.

Thứ tự: **R2 chính · R3 kiểm chứng · R4 dự phòng cuối.**

### R1 — Đường quan hệ mực nước–lưu lượng thực đo (chuẩn nhất, phụ thuộc may mắn)

Chỉ làm được nếu Đài KTTV Trung Trung Bộ cấp chuỗi **cặp (H, Q) quan trắc**. Fit dạng chuẩn thuỷ văn:

```
Q = a · (H − H₀)^b
```

`H₀` = cao độ đáy quy ước. Fit bằng bình phương tối thiểu trên thang log. Nghịch đảo tại H = BĐ I/II/III.

❌ **ĐÃ LOẠI KHỎI PHẠM VI (15/09/2026).** Không gửi được công văn. Giữ lại mô tả ở đây để nêu trong Limitations: *nghiên cứu không có số liệu mực nước quan trắc để hiệu chuẩn trực tiếp, nên ánh xạ H→Q được xây gián tiếp từ các đợt lũ đã công bố.*

### R2 — Hiệu chuẩn theo sự kiện lịch sử ⭐ ĐƯỜNG CHÍNH

Ý tưởng: không cần chuỗi (H, Q) đầy đủ, chỉ cần **các cặp đỉnh lũ đã được công bố**.

**Bước 1.** Thu thập ≥ 15 đợt lũ (tối thiểu chấp nhận được: 10 — xem `RISKS.md` R15) có công bố **đỉnh mực nước tại Kim Long / Phú Ốc**, giai đoạn 1984–2022. Ghi vào `data/external/flood_events.csv`:

| cột | ý nghĩa |
|---|---|
| `event_id` | ví dụ `1999-11` |
| `station` | `kim_long` / `phu_oc` |
| `peak_date` | ngày đỉnh (YYYY-MM-DD) |
| `peak_H_m` | đỉnh mực nước (m) |
| `alert_level` | BĐ đạt được, nếu nguồn có nói |
| `source_type` | `kttv_bulletin` / `pctt_report` / `news` / `paper` |
| `source_url` | link |
| `accessed_date` | ngày truy cập |
| `confidence` | `cao` / `trung binh` / `thap` |

Nguồn chấp nhận được, xếp theo độ tin cậy: bản tin lưu trữ **Đài KTTV khu vực Trung Trung Bộ / nchmf.gov.vn** > báo cáo Ban Chỉ đạo Phòng chống thiên tai > bài báo khoa học về lũ lưu vực sông Hương > báo điện tử chính thống. **Mọi dòng phải có link và ngày truy cập** — literature review sẽ dùng lại.

**Bước 2.** Với mỗi sự kiện, lấy `peak_Q` = max discharge GloFAS trong cửa sổ **±2 ngày** quanh `peak_date`, tại điểm lưới tương ứng trạm đó. Cửa sổ ±2 ngày để hấp thụ lệch pha giữa mô phỏng và thực đo.

**Bước 3.** Fit đường đơn điệu tăng trên N cặp `(peak_Q, peak_H)`, mỗi trạm một đường riêng:

```
H = α · ln(Q) + β          (dạng log, thường khớp tốt và ổn định với N nhỏ)
```

**Bước 4.** Nghịch đảo tại các cấp BĐ:

```
Q_BĐk = exp( (H_BĐk − β) / α )
```

**Bước 5.** Báo cáo chất lượng ánh xạ: **N, R², RMSE (m), khoảng tin cậy bootstrap 95 % của từng Q_BĐk**. Nếu khoảng tin cậy của Q_BĐIII rộng hơn ±30 % thì phải nói rõ là ngưỡng kém tin cậy.

> 🔴 **Bắt buộc ghi trong báo cáo, không được lờ đi:**
> GloFAS cho **lưu lượng trung bình ngày**, còn mực nước công bố là **đỉnh tức thời**. Hai đại lượng lệch nhau có hệ thống (trung bình ngày luôn thấp hơn đỉnh tức thời). Đường fit ở R2 **hấp thụ cả độ lệch này lẫn sai số mô phỏng của GloFAS**, nên nó **không phải đường quan hệ H–Q vật lý của lòng sông**. Gọi đúng tên: **"ánh xạ hiệu chuẩn theo sự kiện" (event-based calibration mapping)**. Gọi nhầm là "rating curve" sẽ bị bắt lỗi ngay khi vấn đáp.

### R3 — Ánh xạ tần suất (kiểm chứng chéo, không dùng riêng lẻ)

Nếu tra được **số ngày/số đợt vượt từng cấp BĐ mỗi năm** (niên giám KTTV, báo cáo PCTT hằng năm):

1. Tính tần suất vượt thực tế `p_I`, `p_II`, `p_III` (số ngày vượt / tổng số ngày).
2. Lấy phân vị `(1 − p_k)` của chuỗi GloFAS 1984–2022 → `Q_k`.

**Tiêu chí chấp nhận:** nếu `Q_k` từ R3 lệch **dưới 25 %** so với R2 → ánh xạ đáng tin, ghi cả hai vào báo cáo. Lệch trên 25 % → phải điều tra nguyên nhân (thường là chọn sai ô lưới, xem `docs/RISKS.md` R1) trước khi đi tiếp.

### R4 — Dự phòng: ngưỡng phân vị thuần tuý

Chỉ dùng nếu **cả R1, R2, R3 đều thất bại** (không thu đủ 10 sự kiện — xem `RISKS.md` R15). Lấy Q95 / Q98 / Q99.5 mùa lũ, và **bắt buộc đổi tên nhãn** thành "Mức nguy cơ 1/2/3", **không được gọi là BĐ I/II/III**. Đây là bước lùi về chất lượng — ghi rõ trong Limitations.

## 4. Bảng kết quả — điền ở W3

| Trạm | Cấp | H (m) | **Q (m³/s)** | Đường dùng | KTC 95 % | Số ngày vượt/năm | % tổng ngày |
|---|---|---|---|---|---|---|---|
| Kim Long | BĐ I | | | | | | |
| Kim Long | BĐ II | | | | | | |
| Kim Long | BĐ III | | | | | | |
| Phú Ốc | BĐ I | | | | | | |
| Phú Ốc | BĐ II | | | | | | |
| Phú Ốc | BĐ III | | | | | | |

Chất lượng ánh xạ R2: Kim Long N = ___, R² = ___ · Phú Ốc N = ___, R² = ___

## 5. Kiểm chứng bắt buộc bằng đợt lũ lịch sử

Ngưỡng quy đổi ra phải "bắt" đúng các đợt đã biết. Nếu lũ 10/2020 không vượt BĐ III trên chuỗi GloFAS thì ngưỡng sai, hoặc ô lưới sai — **dừng lại sửa, đừng đi tiếp**.

| Đợt lũ | Đỉnh H thực đo (m) | Cấp BĐ thực tế | Q GloFAS đỉnh (m³/s) | Cấp BĐ mô hình suy ra | Khớp? |
|---|---|---|---|---|---|
| 11/1999 (lũ lịch sử) | | | | | |
| 10/2020 | | | | | |
| 11/2023 | | | | | |

Ba đợt này phải khớp cấp, hoặc lệch tối đa 1 cấp. Lệch 2 cấp trở lên = ánh xạ hỏng.

## 6. Hệ quả sang bài toán phân loại

- Bài toán trở thành **phân loại thứ bậc 4 lớp**: `không báo động` < `BĐ I` < `BĐ II` < `BĐ III`.
- Cách làm đơn giản và đủ tốt: **3 bộ phân loại nhị phân lồng nhau** (`≥ BĐ I`, `≥ BĐ II`, `≥ BĐ III`), dễ giải thích và dễ đo hơn multiclass.
- Tỉ lệ lớp dương dự kiến: `≥ BĐ I` khoảng 1–3 % · `≥ BĐ III` có thể **dưới 0,3 %**.
- ⚠️ **Ràng buộc thống kê:** tập test (07/2022–2026, ~1 520 ngày) có thể chỉ chứa **vài ngày** vượt BĐ III. Nếu số ngày dương trong test **< 30**, **không được báo cáo metric riêng cho BĐ III như thể nó đáng tin** — báo kèm số mẫu và khoảng tin cậy, hoặc gộp `≥ BĐ II` làm ngưỡng chính. Xem `docs/RESEARCH_DESIGN.md` mục 3.

## 7. Việc phải làm, gắn người và tuần

| # | Việc | Ai | Tuần | Đầu ra |
|---|---|---|---|---|
| 1 | Tra Phụ lục QĐ 05/2020/QĐ-TTg, xác nhận số BĐ | **H** | **W1** | Mục 2 đã tick |
| 2 | Soạn & gửi công văn xin số liệu Đài KTTV | **H** | **W1** | Đã gửi, có ngày |
| 3 | Thu thập ≥ 15 sự kiện vào `flood_events.csv` | **H** | **W2–W3** | File CSV có nguồn đầy đủ |
| 4 | Viết `src/features/thresholds.py` (fit + nghịch đảo + bootstrap) | **G** | **W3** | Có test |
| 5 | Chạy R2, kiểm chứng chéo R3, điền mục 4 và 5 | **G** | **W3** | Bảng đã điền |
| 6 | Viết mục "Định nghĩa ngưỡng" cho Report 2 | **H** | **W4** | Draft |
