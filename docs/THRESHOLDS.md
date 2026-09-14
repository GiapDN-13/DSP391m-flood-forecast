# NGƯỠNG BÁO ĐỘNG LŨ — định nghĩa biến mục tiêu phân loại

> Điền ở **W05**. Đây là mục dễ bị hỏi nhất khi vấn đáp — xem lý do ở `docs/GAPS.md` mục 1.

## 1. Vấn đề đơn vị

| | Đơn vị | Nguồn |
|---|---|---|
| Ngưỡng báo động chính thức của Việt Nam (BĐ I/II/III) | **mực nước (m)** tại trạm | Đài KTTV, quy định nhà nước |
| Dữ liệu nhóm có | **lưu lượng (m³/s)** mô phỏng | GloFAS qua Open-Meteo |

Hai đại lượng **không quy đổi trực tiếp** được nếu thiếu đường quan hệ mực nước – lưu lượng (rating curve) của từng trạm.

## 2. Phương án chọn — điền sau khi chốt

- [ ] **A. Ngưỡng phân vị thống kê** *(mặc định, luôn làm được)*
- [ ] **B. Rating curve từ số liệu trạm thực** *(bonus, chỉ khi xin được số liệu)*
- [ ] **C. Đối chiếu đợt lũ lịch sử** *(luôn làm, bổ trợ cho A hoặc B)*

## 3. Phương án A — ngưỡng phân vị

Tính trên chuỗi discharge GloFAS **giai đoạn 1984–2022** (phần reanalysis, trước mốc cắt) tại điểm lưới đã chốt.

| Mức nguy cơ | Định nghĩa | Giá trị (m³/s) | Số ngày/năm trung bình | % tổng số ngày |
|---|---|---|---|---|
| Mức 1 – Cảnh giác | Q95 mùa lũ | | | |
| Mức 2 – Nguy cơ | Q98 mùa lũ | | | |
| Mức 3 – Nguy cơ cao | Q99.5 mùa lũ | | | |

"Mùa lũ" = tháng 9–12.

> ⚠️ Trong báo cáo **bắt buộc ghi**: *"Các mức nguy cơ trong nghiên cứu này là ngưỡng thống kê thay thế được xây dựng từ phân vị lịch sử của chuỗi GloFAS, KHÔNG phải ngưỡng báo động BĐ I/II/III chính thức theo quy định của Việt Nam."*

## 4. Phương án C — kiểm chứng bằng đợt lũ lịch sử

Ngưỡng chọn phải "bắt" được các đợt lũ lớn đã biết. Nếu trận 10/2020 không vượt Mức 3 thì ngưỡng đặt sai.

| Đợt lũ | Thời gian | Discharge đỉnh (m³/s) | Vượt mức nào? | Nguồn đối chiếu |
|---|---|---|---|---|
| Lũ lịch sử 1999 | 11/1999 | | | |
| Lũ 10/2020 | 10/2020 | | | |
| Lũ 2023 | 11/2023 | | | |

Nguồn đối chiếu chấp nhận được: báo cáo Ban chỉ đạo phòng chống thiên tai, bản tin Đài KTTV lưu trữ, báo điện tử chính thống. **Ghi link + ngày truy cập** để trích dẫn được.

## 5. Ảnh hưởng tới mô hình phân loại

- Tỉ lệ lớp dương dự kiến: **1–3 %** → mất cân bằng nặng.
- Metric dùng: **POD, FAR, CSI, F1, PR-AUC**. Không dùng accuracy.
- `scale_pos_weight` ≈ (số ngày âm / số ngày dương). Ghi giá trị thực tế: ______
- Ngưỡng quyết định chọn theo đường PR, ưu tiên **recall** (bỏ sót lũ nguy hiểm hơn báo nhầm). Ngưỡng chốt: ______
