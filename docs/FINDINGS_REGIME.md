# PHÁT HIỆN — Mốc gãy 2022-07-01 và nút thắt thật (R21)

**Ngày:** 22/09/2026 · Chạy lại: `python -m src.eval.regime_check`

Kết luận ngắn: **R21 không được ủng hộ.** Chuỗi GloFAS *không* đổi biên độ qua
mốc gãy. Nhưng khi đi tìm nguyên nhân khác thì lộ ra một vấn đề **nặng hơn R21**
và nằm ở chỗ khác hẳn.

---

## 1. Nghi ngờ ban đầu

Kiểm chứng ánh xạ H→Q trên 5 đợt lũ sau mốc gãy chệch **−1,94 m một chiều**,
nặng nhất là 15/11/2023: đỉnh thật **4,34 m** (lớn nhất 10 năm) mà GloFAS chỉ
**584 m³/s**. Giả thuyết: từ 2022-07-01 Open-Meteo đổi nguồn "lịch sử" của
GloFAS từ tái phân tích sang **dự báo lưu trữ**, và dự báo lưu trữ bị làm trơn
nên hạ thấp đỉnh.

Nếu đúng thì mô hình được huấn luyện trên một chế độ và vận hành trên một chế
độ khác — hỏng cả nhánh hồi quy lẫn nhánh phân loại.

## 2. Vì sao không thể so trực tiếp

So thống kê discharge trước/sau mốc gãy là so **hai khoảng thời gian khác
nhau**, nên chênh lệch có thể chỉ là biến động khí hậu giữa các năm. Cần một
mốc tham chiếu **không đổi qua mốc gãy**.

Mốc đó là **mưa ERA5** — tái phân tích trong suốt cả giai đoạn, không đổi nguồn
ở 2022-07. Phép thử quyết định:

> Với **cùng một lượng mưa**, lưu lượng GloFAS phản ứng có như nhau không?

## 3. Kết quả: không có bằng chứng đổi chế độ

**3a. Thống kê mô tả gần như trùng nhau** (gợi ý, chưa phải bằng chứng):

| | n | trung vị | p90 | p99 |
|---|---|---|---|---|
| trước 2022-07 | 4 564 | 49,9 | 254,3 | 1 126,8 |
| sau 2022-07 | 1 523 | 49,4 | 272,8 | 1 216,9 |

**3b. Phản ứng theo lượng mưa — phép thử quyết định.** Chia mưa tích luỹ 3 ngày
thành các khoảng dùng chung, so lưu lượng trung vị, KTC 95 % bootstrap:

| Mưa 3 ngày (mm) | n trước | n sau | Q trước | Q sau | Tỉ số | KTC 95 % | Khác biệt |
|---|---|---|---|---|---|---|---|
| 0–5 | 1 356 | 434 | 29,0 | 29,3 | 1,012 | 0,988 – 1,033 | không |
| 5–20 | 1 678 | 555 | 46,6 | 46,4 | 0,995 | 0,927 – 1,064 | không |
| 20–50 | 1 047 | 348 | 127,8 | 107,7 | 0,842 | 0,745 – 0,941 | **có** |
| 50–100 | 325 | 122 | 296,9 | 280,5 | 0,945 | 0,749 – 1,125 | không |
| 100–200 | 111 | 50 | 604,3 | 674,4 | 1,116 | 0,879 – 1,438 | không |

Chỉ **1/5** khoảng có khác biệt vượt KTC, và chỉ −16 %.

**3c. Đỉnh lũ năm trên tổng mưa mùa lũ** lại đi **ngược chiều**: trung vị 0,95
trước và 1,10 sau, tỉ số **+16 %**. Nếu chuỗi sau mốc gãy bị làm trơn thì tỉ số
này phải **giảm**, không phải tăng.

⇒ Hai dấu hiệu ngược chiều nhau và đều nhỏ. **Không có thiên lệch hệ thống.**

**3d. Nới cửa sổ ghép đỉnh cũng không cứu được.** Với cả 5 đợt sau mốc gãy,
đỉnh GloFAS trong cửa sổ ±1 và ±7 ngày **y hệt nhau** — không phải do cửa sổ
quá hẹp.

---

## 4. Vậy nguyên nhân thật là gì

Lấy 12 đợt lũ nằm trong khoảng panel (2010+), ghép mưa 5 ngày, lưu lượng GloFAS
và mực nước công bố:

| Quan hệ | R² | Ý nghĩa |
|---|---|---|
| ln(mưa) → ln(Q) | **0,691** | GloFAS phản ứng với mưa **rất nhất quán** |
| mưa → H | 0,362 | |
| Q → H | 0,300 | |
| **ln(Q) → H** | **0,184** | **dạng đang dùng trong FR-T2** |

Đọc theo chuỗi nhân quả:

```
mưa  ──R²=0,69──►  Q (GloFAS)  ──R²=0,18──►  H (mực nước công bố)
        chắc                        RẤT YẾU
```

**Khâu yếu không phải GloFAS, mà là bước từ lưu lượng sang mực nước.**

Nhìn từng đợt thì thấy ngay:

| Đợt | Mưa 5 ngày | Q | H |
|---|---|---|---|
| 2020-09 | 113,5 | 970 | **0,90** |
| 2023-11 | 168,0 | 584 | **4,34** |
| 2020-10b | 656,8 | 2 060 | 4,17 |
| 2025-10a | 554,7 | 2 022 | 5,05 |

Trận 2023-11 có mưa gần thấp nhất nhóm và lưu lượng thấp nhất nhóm, nhưng mực
nước cao thứ nhì. Trận 2020-09 thì ngược lại: lưu lượng 970 m³/s mà mực nước
chỉ 0,90 m.

Lời giải thích hợp lý nhất đã có sẵn trong nguồn: bài báo ĐH Huế (Tập 131, Số
4A, 2022) ghi rằng tại Kim Long **"do bị ảnh hưởng mạnh của triều cường nên mỗi
trận lũ có thể kéo dài 3–5 ngày"**, và trong đợt 10/2020 mực nước tại Thảo Long
duy trì **+1,8 đến +2,12 m** làm **thoát lũ chậm**, gây ngập trên diện rộng.

⇒ **Mực nước tại Kim Long không phải hàm của riêng lưu lượng thượng nguồn.** Nó
còn phụ thuộc triều, nước dềnh từ phá Tam Giang, và vận hành hồ chứa.

---

## 5. Hệ quả — phải sửa hai chỗ

**5a. R21 hạ cấp.** Từ P=4 / I=5 xuống **P=1 / I=2**. Vẫn phải tách train/test
theo mốc 2022-07-01 như `DATA_SPLITS.md` quy định — đó là kỷ luật đúng, và kế
hoạch gốc cũng đã dặn — nhưng **không còn là mối đe doạ với toàn dự án**.
Nhánh hồi quy lưu lượng **không bị ảnh hưởng gì**.

**5b. FR-T2 lạc quan hơn thực tế.** Con số R² = 0,629 báo cáo trước đó là trên
**N = 7** đợt chọn lọc. Trên đủ 12 đợt trong khoảng panel, cùng dạng ln(Q) → H,
R² chỉ còn **0,184**. Đây là dấu hiệu kinh điển của khớp quá mức trên mẫu nhỏ.

Điều này **không** làm hỏng nhánh hồi quy (câu hỏi nghiên cứu 1). Nhưng nó làm
lung lay nhánh phân loại cấp báo động (câu hỏi nghiên cứu 2), và lý do không
phải "thiếu dữ liệu" mà là **vật lý của trạm đo**.

---

## 6. Ba đường đi tiếp — cần quyết trước W4

| | Hướng | Được | Mất |
|---|---|---|---|
| **A** | Giữ ánh xạ H→Q, nêu rõ hạn chế trong Limitations | Giữ nguyên đề cương, vẫn nói được "cấp báo động BĐ I/II/III" | Đứng trên quan hệ R² = 0,18. Ở vấn đáp rất dễ bị hỏi gãy |
| **B** | Đổi nhãn sang **phân vị lưu lượng** (phương án R4 trong `THRESHOLDS.md`), **không** gọi là BĐ | Trung thực, nhãn dựng trên chính đại lượng mô hình dự báo, đủ mẫu để huấn luyện | Mất tính "chính danh" của ngưỡng nhà nước; phải viết lại phần đặt vấn đề |
| **C** | Giữ BĐ nhưng thêm biến triều / mực nước hạ lưu vào mô hình | Đúng vật lý nhất | Cần nguồn dữ liệu triều mới; không chắc lấy được trong 8 tuần còn lại |

Khuyến nghị của tôi: **B**, có nhắc tới A và C trong Limitations. Lý do: phương
án B là thứ duy nhất trong ba cái mà ta **chắc chắn làm xong được** trong thời
gian còn lại, và nó trung thực với dữ liệu đang có. `THRESHOLDS.md` đã dự phòng
sẵn đường này từ W1, kèm dặn **đổi tên nhãn thành "mức nguy cơ", không gọi là
BĐ** — đúng chỗ cần dùng bây giờ.

Dù chọn hướng nào, kết quả mục 4 **phải vào báo cáo**: quan hệ mưa → lưu lượng
mạnh còn lưu lượng → mực nước yếu là một phát hiện thật về lưu vực này, không
phải một thất bại kỹ thuật cần giấu.

---

## 7. Ghi chú phương pháp

Phép thử ở mục 3b là mẫu chung cho mọi nghi ngờ kiểu "dữ liệu có đổi không":
**đừng so hai đoạn với nhau, hãy so phản ứng của chúng với một biến thứ ba
không đổi qua mốc**. So trực tiếp thì không tách được "dữ liệu đổi" khỏi "thế
giới đổi".
