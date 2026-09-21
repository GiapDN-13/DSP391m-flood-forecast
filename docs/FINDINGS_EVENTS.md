# PHÁT HIỆN — Sự kiện lũ lịch sử & ánh xạ ngưỡng (FR-D7, FR-T1, FR-T2)

**Ngày:** 21/09/2026 (hết W1) · Chạy lại bằng `python -m src.features.thresholds`

Tài liệu này ghi kết quả thu thập sự kiện lũ và **bốn phát hiện làm thay đổi
thiết kế nghiên cứu**. Ba trong bốn phát hiện đó là tin xấu; ghi ra vì lờ đi
thì tới lúc vấn đáp mới bị hỏi.

---

## 1. Đã thu được gì (FR-D7)

`data/external/flood_events.csv` — **19 sự kiện tại trạm Kim Long**, mỗi dòng có
link nguồn, ngày truy cập và **trích nguyên văn câu chứa số liệu** trong cột
`notes`.

| Nhóm | Số sự kiện | Dùng để làm gì |
|---|---|---|
| Ghép được lưu lượng GloFAS, trước mốc gãy 2022-07-01 | **11** | fit ánh xạ H→Q |
| — trong đó từ 2009 (sau khi có hồ chứa lớn) | **7** | **tập chính** |
| Sau mốc gãy 2022-07-01 | 5 | kiểm chứng ngoài mẫu (FR-T4) |
| Không ghép được lưu lượng | 3 | không dùng được |

Vượt mức tối thiểu 10 của `RISKS.md` R15 ở tập trước mốc gãy, **nhưng chưa đạt
ở tập chính (7 < 10)** — xem mục 5.

### Nguồn chính

| Ký hiệu | Nguồn | Giá trị |
|---|---|---|
| **P2** | Nguyễn Hoàng Sơn và CS., *Các hình thế thời tiết gây mưa lũ ở tỉnh Thừa Thiên Huế năm 2020*, Tạp chí Khoa học Đại học Huế: Khoa học Trái đất và Môi trường, **Tập 131, Số 4A, 2022, tr. 149–162**, DOI `10.26459/hueunijese.v131i4A.6654` | Bảng 5 liệt kê 12 trận lũ lớn kèm ngày; phần §3.3 mổ 5 đợt mưa năm 2020 kèm **giờ đỉnh** |
| **P1** | Nguyễn Hoàng Sơn, *Đánh giá vai trò của các hình thế thời tiết gây mưa lũ…*, Tạp chí Khoa học ĐHSP TPHCM, **Số 61, 2014** | Chuỗi đỉnh lũ nhiều năm; lưu lượng lũ 1999 = 14 000 m³/s |
| Báo điện tử | VnExpress, Mekong ASEAN, VietnamPlus, Báo Chính phủ, Tuổi Trẻ/NLĐ | Các đợt 2023–2025 |

P2 là **bài bình duyệt của Đại học Huế** — đáng tin hơn hẳn bản tin báo chí, và
là nguồn tốt nhất tìm được cho giai đoạn 1983–2020.

---

## 2. FR-T1 đã xong: mức báo động được kiểm chứng độc lập **và** đã từng bị đổi

### 2a. Mức hiện hành được xác nhận bằng số học, từ 6 nguồn độc lập

Mọi bản tin đều ghi "H, trên/dưới báo động k là x m". Lấy H trừ x sẽ lộ ra mức
ngưỡng mà nguồn đang dùng — không cần nguồn nói thẳng:

| Nguồn | Câu | Suy ra |
|---|---|---|
| P2, bão Noul 17–18/9/2020 | "+0,9 m dưới báo động I là 0,1 m" | **BĐ I = 1,00 m** |
| P2, 19–29/11/2017 | "+2,71 m, trên báo động II là 0,71 m" | **BĐ II = 2,00 m** |
| P2, 3–9/11/2017 | "+4,03 m, trên báo động III là 0,53 m" | **BĐ III = 3,50 m** |
| P2, 17/10/2020 | "+3,31 m, dưới báo động III là 0,19 m" | **BĐ III = 3,50 m** |
| Mekong ASEAN 28/10/2025 | "5,05 m, cao hơn mức báo động 3 là 1,55 m" | **BĐ III = 3,50 m** |
| Báo Chính phủ 17/11/2025 | "BĐ3 sông Hương là 3,5m" | **BĐ III = 3,50 m** (nói thẳng) |

⇒ `ALERT_LEVELS_M["kim_long"] = {BD1: 1.00, BD2: 2.00, BD3: 3.50}` **đúng**.

### 2b. ⚠️ Phát hiện: BĐ III trước đây là **3,00 m**, không phải 3,50 m

| Nguồn | Câu | Suy ra |
|---|---|---|
| P2, 19–22/11/1998 | "Đỉnh lũ tại Huế đạt mức 4,47 m (trên báo động III: 1,47 m)" | BĐ III = **3,00 m** |
| P2, 06–11/10/2000 | "3,63 m, trên báo động III là 0,63 m" | BĐ III = **3,00 m** |
| P1 (thống kê 1977–2005) | "34 trận lũ lớn vượt báo động cấp III **(H>3,0m)** tại trạm Thuỷ văn Kim Long" | BĐ III = **3,00 m** |

**Vì sao điều này quan trọng:** nhiều nguồn cũ chỉ cho mực nước **tương đối**
("trên báo động III là 0,61 m"). Quy đổi bằng ngưỡng 3,50 m của hôm nay sẽ ra
số sai **0,5 m** — lớn hơn cả RMSE của ánh xạ. Sự kiện `1984-10` trong file
được quy đổi bằng **3,00 m** đúng theo thời kỳ, và cột `notes` ghi rõ.

Việc còn lại của FR-T1: dẫn trực tiếp Phụ lục **QĐ 05/2020/QĐ-TTg**. Trang
thuvienphapluat trả HTTP 403 với công cụ tự động; cần tải tay từ
`vanban.chinhphu.vn`. Sáu nguồn ở mục 2a đã đủ để làm việc tiếp, nên đây là
việc hoàn thiện trích dẫn, không phải nút thắt.

---

## 3. ⚠️ Phát hiện nặng: chuỗi GloFAS **bắt đầu 1997**, không phải 1984

```
tổng dòng      : 15 584
có dữ liệu     : 10 835   (1997-01-01 → 2026-08-31)
rỗng           :  4 749   (30,5 %)  ← toàn bộ 1984–1996
```

Năm 1984 đến 1996 **rỗng 100 %**, giống nhau ở **cả 83 ô lưới**. API nhận
khoảng ngày yêu cầu và trả về đủ số dòng, nhưng giá trị là null.

**Vì sao không ai phát hiện sớm hơn:** `validate_discharge` và `report_missing`
chạy trên `daily_panel.parquet`, mà panel bắt đầu **2010** nên báo 0 % thiếu —
đúng, và vô dụng. Còn crawler thì đếm **số dòng**, không đếm số giá trị không
rỗng. *Đếm dòng không phải là đếm dữ liệu.*

**Hệ quả:**

- Mất 3 sự kiện hiệu chuẩn: `1983-10`, `1984-10`, `1995-10`.
- Mọi phát biểu "1984–2026" trong SPEC, FLOW, PLAN, DATA_DICTIONARY, RUNBOOK,
  **và trong PDF Report 1 + slide đã xuất** đều sai. Đã sửa và build lại.
- Phần "phân vị / return period trên chuỗi dài" trong `DATA_SPLITS.md` và R3 của
  `THRESHOLDS.md` giờ dựa trên **29 năm**, không phải 42 năm. Vẫn dùng được,
  nhưng phải nói đúng độ dài.
- `tests/test_data_coverage.py` khoá lại độ phủ này để không tái diễn.

**Không phải lỗi của crawler.** Open-Meteo công bố GloFAS v4 từ 1984; thực tế
endpoint chỉ trả dữ liệu từ 1997 cho vùng này. Đây là chuyện phải **đo** rồi
mới tin, không phải đọc tài liệu rồi tin.

---

## 4. ⚠️ Phát hiện: quan hệ H–Q ở Kim Long **không ổn định theo thời gian**

Ghép 11 cặp (Q, H) trước mốc gãy rồi fit một đường duy nhất cho kết quả rất
kém: **R² = 0,250 · RMSE = 1,085 m**. Nguyên nhân lộ ra khi xem từng cặp:

| Sự kiện | H (m) | Q GloFAS (m³/s) |
|---|---|---|
| 1998-11 | 4,47 | **3 161** |
| 1999-11 | **5,81** | 1 900 |
| 2020-10b | 4,17 | 2 060 |

Đỉnh lũ **lịch sử 1999** (5,81 m, lưu lượng thực tính 14 000 m³/s theo P1) lại
có lưu lượng GloFAS **thấp hơn** trận 2020 chỉ 4,17 m. Quan hệ **mất tính đơn
điệu** — mà tính đơn điệu là giả định nền của cả phương án R2.

Ba nguyên nhân hợp lý, xếp theo mức tin:

1. **Hồ chứa.** Bình Điền (2009), Hương Điền (2011), Tả Trạch (2014) lần lượt
   vào vận hành, đổi hẳn cách dòng chảy truyền về hạ lưu. GloFAS **không mô
   phỏng vận hành hồ** (`RISKS.md` R18) nên sai lệch của nó cũng đổi theo thời
   kỳ. Trước 2009 và sau 2009 là **hai hệ thống thuỷ văn khác nhau**.
2. **Ảnh hưởng triều.** P2: tại Kim Long "do bị ảnh hưởng mạnh của triều cường
   nên mỗi trận lũ có thể kéo dài 3–5 ngày"; trong đợt 10/2020 mực nước Thảo
   Long duy trì +1,8 đến +2,12 m làm **thoát lũ chậm**. Mực nước ở Kim Long do
   đó **không phải hàm của riêng lưu lượng thượng nguồn**.
3. **GloFAS hạ thấp đỉnh cực đoan.** Max toàn chuỗi ~2 635 m³/s so với 14 000
   m³/s tính cho 1999 — chênh hơn 5 lần.

**Xử lý:** fit **hai tập**, lấy tập từ 2009 làm chính.

| Tập | N | R² | RMSE | Q_BĐ3 |
|---|---|---|---|---|
| Toàn bộ trước mốc gãy | 11 | 0,250 | 1,085 m | 1 501 m³/s |
| **Từ 2009 (tập chính)** | **7** | **0,629** | **0,646 m** | **1 823 m³/s** |

Chênh lệch `Q_BĐ3` giữa hai tập là **1,2 lần** — không phải sai số làm tròn.
Chọn tập nào là một **quyết định nghiên cứu phải bảo vệ được**, không phải
tham số kỹ thuật.

---

## 5. Kết quả FR-T2 và phán quyết trung thực

```
H = 2,8596 · ln(Q) − 17,9711        (N = 7, R² = 0,629, RMSE = 0,646 m)
```

| Cấp | H (m) | Q (m³/s) | KTC 95 % bootstrap | Nửa bề rộng |
|---|---|---|---|---|
| BĐ I | 1,00 | 761 | 175 … 1 014 | ±55 % |
| BĐ II | 2,00 | 1 079 | 437 … 1 308 | ±40 % |
| **BĐ III** | 3,50 | **1 823** | 1 506 … 2 252 | **±20 %** |

**Phán quyết: ánh xạ là TẠM THỜI, chưa được dùng làm kết luận chính.**

- `Q_BĐ3` đạt tiêu chí bề rộng KTC (±20 % < ±30 %) — đây là tin tốt duy nhất.
- `Q_BĐ1` và `Q_BĐ2` **không đạt** (±55 %, ±40 %). Dễ hiểu: tập chính chỉ có
  **một** điểm neo dưới BĐ I (0,90 m ngày 17/9/2020). Đường log không có gì để
  tựa ở đầu thấp.
- **N = 7 < 10** nên vi phạm chính tiêu chí của `RISKS.md` R15.

Vì vậy **`cfg.ALERT_LEVELS_Q` vẫn để trống có chủ ý**. Job dự báo hằng ngày tiếp
tục ghi `chua_co_nguong` thay vì phát nhãn báo động dựa trên ánh xạ chưa đạt.
Số tạm thời nằm trong `data/processed/threshold_mapping.csv`, cột `reliable` =
`False`.

### Kiểm chứng ngoài mẫu (5 sự kiện sau mốc gãy) — thất bại rõ rệt

| Sự kiện | H thật | H suy ra | Lệch | Q GloFAS |
|---|---|---|---|---|
| 2023-11 | 4,34 | 0,24 | **−4,10** | 584 |
| 2024-11 | 3,10 | 0,32 | −2,78 | 600 |
| 2025-10a | 5,05 | 3,80 | −1,25 | 2 022 |
| 2025-10b | 4,90 | 4,83 | −0,07 | 2 903 |
| 2025-11 | 2,81 | 1,31 | −1,50 | 846 |

Sai số tuyệt đối trung bình **1,94 m**, độ chệch **−1,94 m** — chệch một chiều,
tức là **thiên lệch hệ thống**, không phải nhiễu.

Đáng ngờ nhất: trận 15/11/2023 đỉnh **4,34 m** (lớn nhất 10 năm, vượt đỉnh 2020)
mà GloFAS chỉ cho **584 m³/s**, thấp hơn cả một ngày mưa bình thường của 2020.
Hai khả năng, **phải điều tra trước Report 2**:

1. Chuỗi sau 2022-07-01 là **dự báo lưu trữ**, có thể lệch biên độ so với tái
   phân tích ⇒ nếu đúng thì **cả hệ thống vận hành đang chạy trên chế độ dữ
   liệu khác với chế độ dùng để huấn luyện**. Đây sẽ là vấn đề lớn nhất của dự
   án, lớn hơn cả FR-T2.
2. Hoặc cửa sổ ±1 ngày bỏ sót đỉnh; nới cửa sổ rồi đo lại.

---

## 6. Việc phải làm tiếp, theo thứ tự

| # | Việc | Vì sao | Ai |
|---|---|---|---|
| 1 | Điều tra biên độ chuỗi trước/sau mốc gãy 2022-07-01 | Nếu lệch hệ thống thì ảnh hưởng toàn dự án, không chỉ FR-T2 | G |
| 2 | Thu thêm **≥3 sự kiện 2010–2022** để N ≥ 10 ở tập chính | Điều kiện duy nhất còn thiếu để ánh xạ hết "tạm thời" | H |
| 3 | Thu thêm sự kiện **mực nước thấp** (dưới BĐ I) 2010–2022 | Siết `Q_BĐ1`, `Q_BĐ2` đang ±55 % / ±40 % | H |
| 4 | Dẫn trực tiếp Phụ lục QĐ 05/2020/QĐ-TTg | Hoàn thiện FR-T1 | H |
| 5 | Tìm đỉnh **thực đo** cho `2024-11`, `2025-10b`, `2025-11` | Ba dòng đang là số dự báo/đang lên, `confidence = thap` | H |
| 6 | Kiểm ảnh hưởng triều ở Kim Long khi EDA | Có thể phải thêm biến triều, hoặc đổi trạm mục tiêu | D |

Năm sự kiện 2010–2022 còn thiếu **rất có thể tồn tại** — các năm 2010, 2011,
2013, 2016, 2021, 2022 đều có lũ trên BĐ II theo Hình 1 của P2, chỉ là chưa tìm
được bản tin ghi số. P2 ghi rõ **2014, 2015 và 2019 không có trận lũ nào trên
BĐ II**, nên đừng mất thời gian tìm ba năm đó.

---

## 7. Bài học phương pháp

1. **Đếm dòng không phải đếm dữ liệu.** 15 584 dòng nghe như 42 năm; thực tế là
   29 năm dữ liệu và 13 năm null.
2. **Kiểm tra chạy trên tập đã lọc thì không thấy lỗi của tập gốc.** Panel sạch
   100 % vì panel bắt đầu sau chỗ hỏng.
3. **Ngưỡng hành chính thay đổi theo thời gian.** Quy đổi số liệu tương đối cũ
   bằng ngưỡng hiện hành là một lỗi âm thầm đáng 0,5 m.
4. **Số học trên nguồn thứ cấp là công cụ kiểm chứng mạnh.** Mọi lần lấy H trừ
   "trên báo động x" đều cho đúng mức ngưỡng, và chính nó phát hiện việc ngưỡng
   bị đổi.
5. **Bản tóm tắt của máy tìm kiếm gán sai năm.** Cùng con số 5,05 m ngày 27/10
   bị gán cho 2021, 2024 rồi 2025 tuỳ theo năm có trong câu truy vấn. Mọi số
   trong file đều lấy từ bài có **ngày xuất bản xác định** và **trích nguyên
   văn**.
