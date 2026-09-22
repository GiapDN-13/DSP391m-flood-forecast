# Tóm tắt bài báo — paper_06 · Lũ lưu vực sông Hương — bối cảnh địa phương

**Trích dẫn đầy đủ (APA):**
> Nguyễn Hoàng Sơn, Phan Hữu Thịnh, Lê Phúc Chi Lăng, Nguyễn Thị Minh Hương, & Đoàn Xuân Tú (2022). Các hình thế thời tiết gây mưa lũ ở tỉnh Thừa Thiên Huế năm 2020. *Tạp chí Khoa học Đại học Huế: Khoa học Trái đất và Môi trường*, *131*(4A), 149–162. https://doi.org/10.26459/hueunijese.v131i4A.6654

**Link / DOI:** https://csdlkhoahoc.hueuni.edu.vn/data/2024/7/6519-Article_Text-31346-1-10-20240409.pdf

**Người tóm tắt:** G  **Ngày:** 22/09/2026

---

## 1. Bài báo giải quyết vấn đề gì?

Phân tích các hình thế thời tiết gây mưa lũ ở Thừa Thiên Huế, với **Bảng 5 liệt kê 12 trận lũ lớn 1983–2020 kèm ngày và đỉnh lũ tại Kim Long**, và phần §3.3 mổ chi tiết 5 đợt mưa năm 2020 kèm giờ đỉnh.

## 2. Dữ liệu họ dùng

| Nguồn | Khu vực | Khoảng thời gian | Độ phân giải |
|---|---|---|---|
| Trạm Kim Long (sông Hương) | Thừa Thiên Huế | **1977–2020** | ngày, mực nước (cm) + mưa (mm) |
| Trạm Phú Ốc (sông Bồ) | | 1976–2020 | |
| Trạm Thượng Nhật (Tả Trạch) | | 1979–2020 | có cả lưu lượng |

## 3. Phương pháp

- Phân tích thống kê hình thế thời tiết, không dùng mô hình học máy
- Nguồn số liệu: Đài KTTV khu vực + hệ thống đo mưa tự động Vrain

## 4. Kết quả chính

| Metric | Giá trị | So với baseline |
|---|---|---|
| Đỉnh lũ 12/10/2020 tại Kim Long | **+4,17 m** | trên BĐ III 0,67 m |
| Lưu lượng lũ 11/1999 | **14 000 m³/s** | so với max GloFAS ~2 635 |
| Thời gian truyền lũ Thượng Nhật → Kim Long | **5–6 giờ / 51 km** | |

## 5. Hạn chế tác giả tự nêu

- Chỉ mô tả, không dự báo
- Dừng ở 2020

## 6. 👉 Liên hệ với dự án của nhóm

- **Dùng lại được:** đây là **nguồn gốc của 19 sự kiện lũ** trong `flood_events.csv`, và là nguồn cho ba con số quan trọng nhất của dự án: (1) đỉnh 12/10/2020 trùng đúng ngày đỉnh GloFAS trong panel ⇒ chứng cứ độc lập cho ô lưới đã chọn; (2) lưu lượng 1999 = 14 000 m³/s so với max GloFAS ~2 635 ⇒ GloFAS hạ thấp đỉnh cực đoan rất nhiều; (3) thời gian truyền lũ 5–6 giờ ⇒ giải thích vì sao h=3 khó và vì sao lag mưa→Q giống nhau ở cả 3 tiểu lưu vực.
- **Khác họ:** họ mô tả quá khứ; nhóm **dự báo tương lai**. Họ có số liệu trạm thật; nhóm chỉ có mô phỏng.
- **Trích ở mục:** Introduction (bối cảnh) · Data Collection · EDA §5 · Limitations · Threshold definition

## 7. Câu trích dẫn nguyên văn

> "do bị ảnh hưởng mạnh của triều cường nên mỗi trận lũ có thể kéo dài 3–5 ngày" (tr. 156–157)

> "trung bình 5–6 giờ với khoảng cách 51 km từ thượng nguồn (Thượng Nhật) đến hạ lưu (Kim Long)" (tr. 157)
