# PHÁT HIỆN — LightGBM hồi quy lưu lượng (FR-M2)

**Ngày:** 22/09/2026 · Chạy lại: `python -m src.models.lgbm`

Chia tập y hệt `baselines.py`: train ≤ 2015-12-31, valid tới 2022-06-30, **test
từ 2022-07-01** (1 523 ngày). 66 feature, không có cột nào chứa thông tin tương
lai (`tests/test_no_leakage.py` khoá điều này).

---

## 1. Kết quả: thắng persistence ở cả ba horizon

| h | NSE LightGBM | KTC 95 % | NSE persistence | KTC 95 % | Chênh | `AC-1` |
|---|---|---|---|---|---|---|
| 1 | **0,742** | 0,673 – 0,789 | 0,542 | 0,388 – 0,650 | +0,200 | ≥ 0,70 ✅ |
| 2 | **0,422** | 0,366 – 0,469 | 0,008 | −0,298 – 0,223 | +0,414 | ≥ 0,40 ✅ |
| 3 | **0,167** | 0,111 – 0,211 | −0,198 | −0,561 – 0,013 | +0,364 | ≥ 0,25 ❌ |

KTC tính bằng **block bootstrap** (khối 30 ngày) chứ không phải bootstrap i.i.d.
— chuỗi ngày tự tương quan mạnh nên bootstrap thường sẽ cho khoảng quá hẹp.

**Khoảng tin cậy của hai mô hình không chồng lấn ở cả ba horizon** ⇒ biên thắng
là thật, không phải nhiễu. Ngược lại, KTC của h=3 **nằm trọn dưới ngưỡng 0,25**
⇒ `AC-1` trượt ở h=3 là dứt khoát, không phải sát nút.

> **Đã kiểm tính công bằng của phép so.** Mặt nạ tập test của LightGBM (đòi đủ
> 66 feature không rỗng) và của persistence **trùng nhau hoàn toàn** — 1 522 /
> 1 521 / 1 520 ngày ở h=1/2/3, chênh 0. Không có chuyện mô hình được chấm trên
> tập dễ hơn.

Đúng như dự đoán từ bảng baseline: **mức cải thiện lớn nhất nằm ở h=2 và h=3**,
nơi persistence sụp. Ở h=1 persistence vốn đã mạnh nên biên thắng hẹp hơn.

`AC-1` đạt ở h=1 và h=2, **trượt ở h=3** (0,167 so với ngưỡng 0,25). Không tìm
cách lách: dự báo 3 ngày ở lưu vực nhỏ, dốc, thời gian tập trung nước chỉ 5–6
giờ là bài toán khó — đó là kết quả trung thực, và mục 4 nói vì sao.

---

## 2. ⚠️ Vấn đề nghiêm trọng hơn con số NSE: mô hình **hạ thấp đỉnh lũ**

| h | `peak_bias` LightGBM | `peak_bias` persistence |
|---|---|---|
| 1 | **−0,460** | −0,361 |
| 2 | −0,750 | −0,648 |
| 3 | −0,885 | −0,683 |

`peak_bias` đo sai lệch ở phân vị 99. Âm nghĩa là **dự báo thấp hơn thực tế**.
Ở h=1, LightGBM có NSE tốt hơn persistence rõ rệt **nhưng tái tạo đỉnh lại kém
hơn**.

Với hệ thống cảnh báo lũ, đây đúng là kiểu sai tệ nhất: sai về trung bình thì
chấp nhận được, **bỏ sót đỉnh thì mất toàn bộ mục đích**.

### Đã kiểm: không phải lỗi hàm mất mát

| Biến thể | NSE h=1 | NSE h=2 | NSE h=3 | `peak_bias` h=1 |
|---|---|---|---|---|
| L1 + log1p *(đang dùng)* | 0,742 | 0,422 | 0,167 | −0,460 |
| L2 + log1p | 0,719 | 0,450 | 0,176 | −0,472 |
| L2 + thang gốc | 0,714 | 0,431 | 0,174 | −0,412 |
| Huber + log1p | 0,743 | 0,441 | 0,175 | −0,450 |

Cả bốn đều âm ở mức tương đương. Thiên lệch hạ đỉnh là **bản chất của bài toán
hồi quy trung tâm trên phân bố lệch**, không phải do chọn sai hàm mất mát.

> **Ghi rõ về phương pháp:** bảng trên đo trên **tập test**, nên nó là **phép
> kiểm độ nhạy**, không phải căn cứ chọn mô hình. L1 được chọn **từ trước** vì
> bền với cực trị, và giữ nguyên. Chọn biến thể theo điểm test là rò rỉ tập
> test — sẽ bị bắt lỗi ngay ở vấn đáp.

### Hướng xử lý cho Report 3

1. **Hồi quy phân vị** (`objective="quantile", alpha=0.9`) để phát thêm một
   đường dự báo cận trên — đúng tinh thần cảnh báo hơn là một con số điểm.
2. **Ngưỡng theo chi phí** (`FR-M5`): khi chuyển sang bài toán cảnh báo, chọn
   ngưỡng tối ưu theo tỉ lệ thiệt hại bỏ sót / báo động giả, chứ không lấy 0,5.
3. Báo cáo `peak_bias` **cạnh** NSE trong mọi bảng. Chỉ đưa NSE là che mất
   điểm yếu quan trọng nhất.

---

## 3. Feature nào đang gánh mô hình (h=2)

| Hạng | Feature | Gain |
|---|---|---|
| 1 | `doy_sin` | 514 |
| 2 | `doy_cos` | 501 |
| 3 | `discharge` | 446 |
| 4 | `rain_thuong` | 443 |
| 5–10 | `discharge_lag9…14`, `q_diff1` | 356–386 |

Hai feature mùa vụ đứng đầu thoạt nhìn đáng lo: liệu mô hình có đang dựa vào
"đang là tháng mấy" thay vì tín hiệu mưa?

**Đã kiểm bằng ablation — câu trả lời là không:**

| Bộ feature | NSE h=1 | NSE h=2 | NSE h=3 |
|---|---|---|---|
| đủ 66 feature | 0,742 | 0,422 | 0,167 |
| **bỏ hẳn `doy_sin`, `doy_cos`** | **0,748** | **0,423** | **0,174** |

Bỏ hai cột mùa vụ thì NSE **không giảm, thậm chí nhích lên**. Nghĩa là thông
tin mùa vụ đã nằm sẵn trong các lag lưu lượng và mưa; xếp hạng `gain` cao chỉ
phản ánh việc biến liên tục tuần hoàn được dùng ở **nhiều nút chia nhỏ**, không
phải nó gánh mô hình.

> Giữ nguyên bộ 66 feature làm cấu hình chính. Không đổi sang bộ bỏ `doy_*` dù
> điểm nhích lên — chênh lệch nằm trong nhiễu và việc chọn theo điểm **test**
> là rò rỉ tập test. Bảng trên là **bằng chứng phản bác một nghi ngờ**, không
> phải bước chọn mô hình.

`rain_thuong` đứng thứ 4 khớp với EDA §8: nước sinh ra ở thượng nguồn.

---

## 4. Vì sao h=3 khó

Thời gian truyền lũ từ Thượng Nhật về Kim Long chỉ **5–6 giờ trên 51 km** (bài
báo ĐH Huế 131/4A/2022). Nghĩa là **toàn bộ thông tin thuỷ văn có ích đã nằm
gọn trong vòng chưa tới một ngày**. Dự báo xa hơn 1 ngày thì không còn dựa được
vào nước đang chảy trong sông nữa, mà phải dựa vào **mưa sẽ rơi** — tức là phụ
thuộc vào chất lượng dự báo mưa, chứ không phải vào mô hình thuỷ văn.

Đây chính là lý do kịch bản B (`RESEARCH_DESIGN.md` §2, dùng `fc_rain`) không
phải phần phụ mà là **phần quyết định ở h=2 và h=3**. Đó là việc tiếp theo.

---

## 5. Việc tiếp

| # | Việc | Vì sao |
|---|---|---|
| 1 | Chạy kịch bản B — thay mưa thực đo bằng mưa dự báo đã phát | Là con đường thật để cải thiện h=2, h=3 |
| 2 | Bỏ `doy_sin`/`doy_cos`, đo lại | Kiểm xem mô hình học lũ hay học mùa vụ |
| 3 | Hồi quy phân vị 0,9 | Xử lý thiên lệch hạ đỉnh |
| 4 | Optuna (`FR-M4`) | Sau khi đã chốt bộ feature, không phải trước |
| 5 | SHAP (`FR-V7`) | Yêu cầu của CLO, và để giải thích mục 3 |

Thứ tự này có chủ ý: **không tinh chỉnh siêu tham số trước khi chốt feature**.
Optuna trên bộ feature sai chỉ tốn thời gian.
