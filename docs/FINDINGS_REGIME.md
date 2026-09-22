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

⇒ Hai dấu hiệu ngược chiều nhau và đều nhỏ.

**3d. Nới cửa sổ ghép đỉnh cũng không cứu được.** Với cả 5 đợt sau mốc gãy,
đỉnh GloFAS trong cửa sổ ±1 và ±7 ngày **y hệt nhau** — không phải do cửa sổ
quá hẹp.

**3e. Đã kiểm riêng phần đuôi phân bố** (phản biện độc lập chỉ ra rằng giả
thuyết "làm trơn đỉnh" nằm ở đuôi, mà bảng 3b lại bỏ khoảng > 200 mm vì thiếu
mẫu). Gộp toàn bộ ngày có mưa 3 ngày ≥ 200 mm:

| | n | Q trung vị | Mann–Whitney |
|---|---|---|---|
| trước | 45 | 1 275 | |
| sau | 14 | 1 519 (+19 %) | **p = 0,581** |

Không đủ bằng chứng khác biệt, và lại đi **ngược chiều** giả thuyết làm trơn.

⇒ **Không có thiên lệch hệ thống, kể cả ở đuôi.**

---

## 4. Vậy nguyên nhân thật là gì

Lấy 12 đợt lũ nằm trong khoảng panel (2010+), ghép mưa 5 ngày, lưu lượng GloFAS
và mực nước công bố:

| Quan hệ | R² | Spearman ρ | p | Ý nghĩa |
|---|---|---|---|---|
| ln(mưa) → ln(Q) | **0,691** | | | GloFAS phản ứng với mưa **rất nhất quán** |
| **mưa → H** | **0,362** | **+0,594** | **0,042** | quan hệ **duy nhất** có ý nghĩa thống kê |
| Q → H | 0,300 | | | |
| **ln(Q) → H** | **0,184** | +0,364 | 0,245 | **dạng dùng trong FR-T2 — không có ý nghĩa** |

Hai điều phải nói kèm, nếu không sẽ bị bắt lỗi:

1. **n = 12 nên kết quả nhạy với từng điểm.** Leave-one-out cho R² dao động
   **0,087 – 0,431**; bỏ riêng đợt 2023-11 thì R² lên 0,431. Kết luận "quan hệ
   yếu" đúng về hướng nhưng **không được trích con số 0,184 như một hằng số**.
2. **Không phải do mấy dòng dữ liệu kém tin cậy.** Lọc bỏ 3 đợt có
   `confidence = thap` (số dự báo, chưa phải thực đo), còn 8 đợt thì
   R² **tụt tiếp xuống 0,101** — quan hệ yếu đi chứ không mạnh lên.

Đáng chú ý nhất: **mưa dự báo mực nước tốt hơn lưu lượng GloFAS dự báo mực
nước** (0,362 so với 0,300, và chỉ mưa mới có ý nghĩa thống kê). Nếu bước qua
GloFAS làm *mất* thông tin so với dùng thẳng mưa, thì ngoài chuyện triều còn có
khả năng GloFAS bỏ sót chính các trận lớn — xem cảnh báo ở mục 5a.

Đọc theo chuỗi nhân quả:

```
mưa  ──R²=0,69──►  Q (GloFAS)  ──R²=0,18──►  H (mực nước công bố)
        chắc                        RẤT YẾU
```

**Khâu yếu nằm ở bước từ lưu lượng sang mực nước.** Nhưng phải cẩn thận khi
đọc câu này: nó **không** đồng nghĩa với "GloFAS đúng". Hai cách giải thích đều
còn sống, và dữ liệu hiện có **chưa tách được chúng**:

* **(a) Trạm đo:** mực nước Kim Long chịu triều và nước dềnh, nên không phải
  hàm của riêng lưu lượng thượng nguồn.
* **(b) Mô hình:** GloFAS (bị ép bởi trường mưa kiểu ERA5, vốn hạ thấp mưa cực
  trị) bỏ sót chính các trận lớn. Chi tiết ở mục 5a.

Việc **mưa dự báo H tốt hơn Q dự báo H** nghiêng về (b) nhiều hơn là (a): nếu
GloFAS chỉ đơn thuần "thiếu biến triều" thì nó vẫn phải giữ được thông tin của
mưa, chứ không làm mất bớt. Muốn phân định dứt khoát thì phải có **mưa trạm
thực đo** — hướng D ở mục 6.

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

> ⚠️ **Giới hạn của kết luận này, phải nêu trong báo cáo.** Phép thử dựa trên
> giả định **mưa ERA5 là mốc tham chiếu đúng**. Nhưng GloFAS v4 được *ép bởi*
> chính trường mưa kiểu ERA5, nên "mưa và lưu lượng nhất quán với nhau" có thể
> nghĩa là **cả hai cùng sai theo cùng một hướng**, không phải cả hai cùng
> đúng. Kết luận an toàn duy nhất rút ra được là: **chuỗi không đổi chế độ qua
> mốc 2022-07-01**. Nó **không** chứng minh GloFAS mô phỏng đúng lũ thật.
> Muốn kiểm điều đó phải đối chiếu với **mưa trạm thực đo** — xem mục 6.

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
| **D** | Đối chiếu **mưa ERA5 với mưa trạm** đã công bố cho 19 sự kiện | Kiểm được chính giả định nền của mục 5a. Kết quả nào cũng có giá trị: ERA5 hụt ⇒ phát hiện mạnh; không hụt ⇒ luận điểm triều được củng cố | Tốn công đọc–tra thủ công, giống FR-D7 |

Khuyến nghị của tôi: **B**, có nhắc tới A và C trong Limitations. Lý do: phương
án B là thứ duy nhất trong ba cái mà ta **chắc chắn làm xong được** trong thời
gian còn lại, và nó trung thực với dữ liệu đang có. `THRESHOLDS.md` đã dự phòng
sẵn đường này từ W1, kèm dặn **đổi tên nhãn thành "mức nguy cơ", không gọi là
BĐ** — đúng chỗ cần dùng bây giờ.

Dù chọn hướng nào, kết quả mục 4 **phải vào báo cáo**: quan hệ mưa → lưu lượng
mạnh còn lưu lượng → mực nước yếu là một phát hiện thật về lưu vực này, không
phải một thất bại kỹ thuật cần giấu.

---

## 6b. Kết quả hướng D — ERA5 **có** hụt mưa cực trị

Đối chiếu tổng mưa ERA5 (lấy **ô lưới lớn nhất**, không phải trung bình lưu
vực, để so được với trạm điểm) với số trạm đã công bố:

| Đợt | ERA5 ô lớn nhất | ERA5 TB lưu vực | Trạm đã công bố |
|---|---|---|---|
| 2017-11 (bão số 12) | 827 mm | 530 mm | 600–1 200 mm phổ biến; Bạch Mã 2 751 |
| 2020-10 (đợt dài) | 1 713 mm | 1 184 mm | Nhâm 2 390 · Phú Đa 2 081 · Quan Tượng Đài 2 096 |
| **2024-11** | **332 mm** | 171 mm | **miền núi 500–800 phổ biến**; Khe Tre 823 |
| 2023-11 | 323 mm | 180 mm | chưa tra được |

**Đợt 2024-11 là bằng chứng mạnh nhất:** ERA5 ở ô lớn nhất chỉ 332 mm trong khi
mức *phổ biến* ở miền núi đã là 500–800 mm — hụt hơn một phần ba, và đây là so
với mức phổ biến chứ không phải một trạm cực trị đơn lẻ.

**Phải nói kèm hai điều kẻo bị bắt lỗi:**

1. Ô lưới ERA5 ~0,25° là **trung bình trên diện tích**, còn trạm là **điểm**.
   Ở địa hình núi, trung bình ô thấp hơn đỉnh điểm là chuyện bình thường, nên
   một phần khoảng cách trên là do so lệch đơn vị chứ không hẳn do sai số.
2. Bạch Mã (~16,20 N · 107,85 E) **nằm ngoài hộp lưới mưa** (107,10–107,80),
   nên không được dùng con số 2 751 / 2 997 mm làm mốc so trực tiếp.

**Kết luận:** có bằng chứng ERA5 hụt mưa cực trị ở lưu vực này, độ lớn chưa xác
định chắc. Điều này **củng cố giả thuyết (b)** ở mục 4: GloFAS bị ép bởi trường
mưa hụt nên bỏ sót chính các trận lớn — và giải thích được vì sao đợt 2023-11
có mực nước 4,34 m mà GloFAS chỉ cho 584 m³/s.

⇒ Vào Limitations của Report 2 và Report 3. Đây là **hạn chế của nguồn dữ liệu
mở**, không phải lỗi của nhóm — và nêu ra được nó là điểm cộng.

---

## 7. Ghi chú phương pháp

Phép thử ở mục 3b là mẫu chung cho mọi nghi ngờ kiểu "dữ liệu có đổi không":
**đừng so hai đoạn với nhau, hãy so phản ứng của chúng với một biến thứ ba
không đổi qua mốc**. So trực tiếp thì không tách được "dữ liệu đổi" khỏi "thế
giới đổi".
