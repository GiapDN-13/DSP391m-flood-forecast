# PHÁT HIỆN — EDA bổ sung theo giáo trình chương 3–4

**Ngày:** 13/10/2026 · Chạy lại: `python -m src.eval.eda_curriculum`
Hình: `reports/figures/report/eda9…eda12_*_en.png` · Số: `reports/eda_descriptive.csv`,
`eda_correlation.csv`, `eda_outliers.csv`

Giáo trình (slide chương 3–4) gọi tên đích danh vài kỹ thuật mà 8 mục EDA cũ
chưa có. File này lấp đúng các mục đó. Code dùng **Polars + seaborn**, không pandas.

---

## 0. Sắp lại EDA theo univariate → bivariate → multivariate

| Mức | Mục |
|---|---|
| **Univariate** | E1 tổng quan · E9 thống kê mô tả · E10 box plot + KDE · E2 mùa vụ · E6 cực trị |
| **Bivariate** | E3 độ trễ mưa → lưu lượng · E4 ẩm nền · E5 mực nước so với lưu lượng · E12 ngoại lai |
| **Multivariate** | E7 hai chế độ (lưu lượng × thời kỳ × mưa) · E8 không gian · E11 ma trận Pearson/Spearman |

## 1. Thống kê mô tả (E9)

| | mean | median | mode | std | skew |
|---|---|---|---|---|---|
| Lưu lượng Q | 120,3 | 49,7 | 28,9 | 214,6 | 5,91 |
| Mưa lưu vực | 7,8 | 2,9 | **0,0** | 15,9 | 5,75 |
| Mưa 3 ngày | 23,4 | 11,6 | 0,1 | 37,5 | 4,26 |
| Chỉ số ẩm API | 54,1 | 36,9 | 16,4 | 58,7 | 3,09 |

Mean > 2 × median và std > mean ở gần mọi biến ⇒ lệch phải, đuôi nặng. Mode của
mưa = 0: ngày phổ biến nhất là ngày khô. Mode tính sau khi làm tròn 1 chữ số
(biến liên tục).

**Chuẩn hoá / scaling:** không áp dụng. LightGBM chia nút theo **thứ tự** giá trị
nên bất biến với mọi biến đổi đơn điệu; scaling không đổi kết quả. `log1p` chỉ
dùng để xử lý độ lệch của biến mục tiêu.

## 2. Box plot theo tháng + KDE (E10)

Box tháng 9–12 vừa **cao hơn** vừa **rộng hơn** — mùa lũ không chỉ nhiều nước
hơn mà còn biến động hơn. Điểm ngoài râu ở mùa khô là lũ trái mùa thật
(01–02/04/2022: 1 840 và 2 635 m³/s, mưa 179 và 147 mm).

## 3. Pearson và Spearman (E11)

Tương quan với `Q(t+1)`:

| Biến | Pearson | Spearman | Chênh |
|---|---|---|---|
| Q hôm nay | 0,778 | **0,907** | +0,13 |
| Mưa hôm nay | 0,789 | 0,750 | −0,04 |
| Mưa 3 ngày | 0,753 | 0,836 | +0,08 |
| Mưa 7 ngày | 0,600 | 0,772 | +0,17 |
| **Chỉ số ẩm API** | 0,479 | **0,679** | **+0,20** |
| Biến thiên Q 1 ngày | 0,444 | 0,181 | **−0,26** |

* Dữ liệu lệch mạnh nên **Spearman là mặc định đúng**: Pearson bị vài ngày lũ
  cực lớn chi phối.
* API: quan hệ **đơn điệu nhưng phi tuyến** — Pearson đánh giá thấp nó tới 0,20.
* Biến thiên Q thì ngược lại: Pearson cao do vài ngày nước lên rất mạnh kéo; trên
  thứ hạng thì yếu. Đừng đọc 0,44 như một quan hệ ổn định.
* Ba tiểu lưu vực tương quan với nhau 0,83–0,99 (đa cộng tuyến). Không hại mô
  hình cây, nhưng làm feature importance bị chia nhỏ giữa chúng — nhớ điều này
  khi đọc SHAP ở Report 3.

## 4. Ngoại lai (E12) — "hiếm" không có nghĩa là "sai"

Hai phép thử trả lời hai câu hỏi khác nhau:

1. **Thống kê — IQR trên log1p(Q):** rào trên Q3 + 1,5·IQR = **860 m³/s** → 98
   ngày, **91 ngày nằm trong mùa lũ**. IQR gắn cờ chính các ngày lũ mà mô hình cần
   học ⇒ không được xoá theo IQR.
2. **Vật lý:** Q ≥ Q99 (1 166 m³/s) mà mưa lưu vực 3 ngày trước < 10 mm ⇒ không có
   nguồn nước nào sinh ra nó. Kết quả: **0 ngày**.

**Quyết định: giữ toàn bộ.**

**Sửa một nghi ngờ cũ** (`FINDINGS_BASELINE.md` §4): ngày **14/06/2025** (2 055 m³/s)
từng bị nghi là xả hồ hoặc lỗi mô phỏng vì mưa *cùng ngày* chỉ 0,9 mm. Nhìn đúng
độ trễ thì hai hôm trước mưa **181 mm và 98 mm** — giải thích trọn vẹn. Bài học:
kiểm ngoại lai phải theo đúng cơ chế (trễ 1 ngày), không theo cùng ngày.

Ngày lũ được mưa giải thích yếu nhất: **01/04/2017** (1 336 m³/s, 31 mm trong 4
ngày) — vẫn trên ngưỡng 10 mm, giữ lại, ghi nhận.

## 5. Quyền riêng tư, đạo đức, pháp lý (giáo trình ch.3 slide 4)

| Mục | Cách làm |
|---|---|
| Giấy phép | Open-Meteo CC BY 4.0; ERA5 và GloFAS theo giấy phép Copernicus; OpenStreetMap ODbL. Ghi nguồn đầy đủ |
| Dữ liệu cá nhân | Không có — toàn bộ là dữ liệu lưới khí tượng thuỷ văn |
| Dữ liệu thu từ web | 19 trận lũ: mỗi dòng có URL, ngày truy cập, trích nguyên văn |
| Ngưỡng chính thức | Trích từ văn bản gốc QĐ 05/2020/QĐ-TTg, Phụ lục I |
| Dùng API công bằng | Giới hạn nhịp, một crawler, không tải lại |
| Sử dụng có trách nhiệm | Sản phẩm học thuật, không phải cảnh báo chính thức — có disclaimer |
