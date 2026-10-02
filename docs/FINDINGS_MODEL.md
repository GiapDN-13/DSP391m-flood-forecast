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

## 3b. Phân loại mức nguy cơ (FR-M3)

Đặt dưới dạng **nhị phân theo từng mức** ("ngày t+h có vượt mức k không") chứ
không phải đa lớp — đó đúng là câu hỏi vận hành, và 3 lớp hiếm với 7–31 ngày
dương thì đa lớp không học được gì. Bù mất cân bằng bằng **trọng số lớp**, không
lấy mẫu lại (lấy mẫu lại trên chuỗi thời gian phá cấu trúc tự tương quan).

| Mức | h | n ngày dương (test) | POD | FAR | CSI | F1 | PR-AUC | Đủ mẫu |
|---|---|---|---|---|---|---|---|---|
| nguy_cơ_1 | 1 | 31 | **0,677** | **0,192** | **0,583** | 0,737 | 0,668 | ✅ |
| nguy_cơ_1 | 2 | 31 | 0,419 | 0,435 | 0,317 | 0,481 | 0,350 | ✅ |
| nguy_cơ_1 | 3 | 31 | 0,065 | 0,900 | 0,041 | 0,078 | 0,175 | ✅ |
| nguy_cơ_2 | 1 | 12 | 0,417 | 0,444 | 0,312 | 0,476 | 0,403 | ❌ |
| nguy_cơ_2 | 2 | 12 | **0,000** | 1,000 | 0,000 | — | 0,071 | ❌ |
| nguy_cơ_2 | 3 | 12 | 0,083 | 0,857 | 0,056 | 0,105 | 0,057 | ❌ |
| nguy_cơ_3 | — | — | *chỉ 9 ngày dương trong train — bỏ hẳn, không huấn luyện* | | | | | |

**Đọc thẳng:** chỉ **mức 1 ở h=1** dùng được thật (bắt được 2/3 số ngày vượt
ngưỡng với 19 % báo động giả). Sang h=2 đã tệ, h=3 thì **hỏng hẳn** — POD 0,065
với FAR 0,90 nghĩa là gần như không bắt được gì mà báo động giả gần hết.

Không dùng accuracy ở bất kỳ dòng nào: ngày vượt mức 1 chỉ chiếm ~1 %, nên đoán
"không" cho mọi ngày đã đạt 99 %.

### Đã thử chỉnh ngưỡng quyết định — không ăn thua

Ngưỡng 0,5 là tuỳ tiện với dữ liệu lệch, nên thử chọn ngưỡng tối đa hoá CSI
**trên tập valid** (huấn luyện chỉ trên train, để không đụng test):

| h | CSI test @ 0,5 | Ngưỡng tối ưu trên valid | CSI test @ ngưỡng đó |
|---|---|---|---|
| 1 | 0,450 | 0,60 | **0,400** ↓ |
| 2 | 0,089 | 0,05 | 0,100 ↑ |
| 3 | 0,020 | 0,07 | 0,093 ↑ |

Ngưỡng tối ưu trên valid **không chuyển sang được test**, thậm chí làm xấu đi ở
h=1. Giữ 0,5. Đây cũng là một kết quả đáng báo cáo: giai đoạn valid (2016 →
2022-06) và test (từ 2022-07) khác nhau đủ để một siêu tham số chỉnh trên valid
không còn tối ưu trên test.

*(Các con số trong bảng này thấp hơn bảng trên vì huấn luyện chỉ trên train
2 191 ngày thay vì train+valid 4 564 ngày.)*

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

## 4b. 🔴 Kịch bản B không dựng được — và điều đó làm lộ ra một phát hiện lớn hơn

**Kịch bản B thật đã chết.** `FR-D3` crawl "mưa dự báo đã phát" từ Historical
Forecast API để làm kịch bản B. Kiểm 22/09/2026: endpoint đó trả về **đúng cùng
con số** với Archive API (ERA5) — tương quan **1,0000**, chênh lệch tối đa
**0,0 mm** trên 1 523 ngày, xác nhận lại bằng gọi API trực tiếp. Previous-Runs
API cũng không có biến `*_previous_dayN` cho vùng này.

⇒ Không có nguồn mở nào cho mưa dự báo phát trước 1–3 ngày ở lưu vực này.
`data/raw/fc_rain/` (64 ô, 2 MB) **trùng lặp với `rain_daily`**, không mang thêm
thông tin nào.

Thay bằng **kịch bản B′** (`RESEARCH_DESIGN.md` §2 đã dự phòng): quét độ nhạy —
làm nhiễu mưa bằng nhiễu nhân lognormal với `sigma` tăng dần.

| sigma | h=1 | h=2 | h=3 |
|---|---|---|---|
| 0,0 *(mưa hoàn hảo)* | 0,744 | 0,430 | 0,169 |
| 0,4 | 0,729 | 0,417 | 0,169 |
| 0,8 | 0,703 | 0,398 | 0,171 |
| 1,0 *(sai số rất lớn)* | 0,679 | 0,383 | 0,177 |

Ngay cả với `sigma = 1,0` — sai số nhân cỡ e^±1 — NSE chỉ tụt 0,065 ở h=1 và
**tăng nhẹ** ở h=3. Mô hình gần như **không nhạy với chất lượng mưa**.

### Vì sao lại thế — ablation cho câu trả lời, và nó bất ngờ

| Bộ feature | n | h=1 | h=2 | h=3 |
|---|---|---|---|---|
| Đầy đủ | 67 | **0,744** | 0,430 | 0,169 |
| Bỏ hết mưa (chỉ lưu lượng + mùa) | 22 | 0,664 | 0,267 | 0,123 |
| **Chỉ mưa + mùa vụ (bỏ hết lag lưu lượng)** | 49 | 0,698 | **0,474** | **0,172** |

> 🔴 **Diễn giải dưới đây đã bị bác bỏ ngày 02/10** khi kiểm trên tập valid —
> xem *Đính chính* ở cuối mục. Giữ lại để thấy lập luận đã sai ở đâu.

Đọc bảng này kỹ, vì nó đảo ngược một giả định:

1. **Mưa có đóng góp thật**, rõ nhất ở h=2 (+0,163 so với bỏ mưa).
2. Nhưng ở **h=2 và h=3, bỏ hẳn lag lưu lượng lại CHO KẾT QUẢ TỐT HƠN** mô hình
   đầy đủ (0,474 so với 0,430 · 0,172 so với 0,169).

Nghĩa là từ h≥2, **lag lưu lượng không còn là thông tin mà là thứ gây nhiễu**:
mô hình bám vào quán tính của dòng chảy, mà quán tính đó tắt nhanh — đúng với
thời gian tập trung nước chỉ 5–6 giờ (mục 4). Có lưu lượng trong tay, mô hình
"lười" đi và học mưa kém hơn.

Điều này cũng giải thích vì sao B′ không nhạy: khi còn lag lưu lượng, mô hình
dựa vào chúng nên mưa nhiễu hay không cũng ít đổi. Bỏ lưu lượng ra thì mưa mới
lộ giá trị.

~~**Hệ quả cho Report 3:** nên dùng bộ feature khác nhau theo horizon.~~
**Đã kiểm và bác bỏ** — xem đính chính ngay dưới.

> ⚠️ Bảng ablation đo trên tập test nên là **bằng chứng cơ chế**, không phải
> bước chọn mô hình. Muốn chốt bộ feature theo horizon thì phải chọn trên
> **valid** rồi mới đo lại trên test.

### 🔴 Đính chính 02/10/2026 — kết luận trên **không lặp lại** trên valid

Đã làm đúng quy trình (`src/models/horizon_features.py`): huấn luyện chỉ trên
train, chấm 4 bộ feature trên **valid** (2016 → 2022-06), chọn bộ tốt nhất theo
từng horizon, rồi mới đo test **một lần**.

| h | Valid: đầy đủ | Valid: chỉ mưa | Valid: mưa + Q ngắn | Bộ được chọn | Test: bộ chọn | Test: đầy đủ |
|---|---|---|---|---|---|---|
| 1 | 0,691 | 0,629 | **0,692** | mưa + Q ngắn | 0,735 | **0,744** |
| 2 | 0,278 | 0,271 | **0,289** | mưa + Q ngắn | 0,392 | **0,430** |
| 3 | **0,109** | 0,105 | 0,106 | đầy đủ | 0,169 | 0,169 |

Ba điều rút ra:

1. **Trên valid, mọi bộ feature cách nhau trong nhiễu** (chênh 0,001–0,07).
   Không có bộ nào thắng rõ.
2. Bộ "chỉ mưa" — bộ thắng trên test với 0,474 ở h=2 — **không** thắng trên
   valid (0,271 so với 0,289). Kết quả 0,474 là **đặc thù của giai đoạn test
   2022–2026**, không phải tính chất của lưu vực.
3. Bộ được chọn đúng quy trình lại **kém hơn** bộ đầy đủ trên test ở h=1, h=2.

⇒ **Câu chuyện cơ chế ở trên ("lag lưu lượng gây nhiễu, mô hình lười") KHÔNG
được dữ liệu ủng hộ.** Giữ **bộ 66 feature đầy đủ** làm mô hình chính cho cả
ba horizon.

Đây là ví dụ đúng kiểu cho câu hỏi vấn đáp *"vì sao không được chọn mô hình
trên tập test?"*: nếu chọn trên test, nhóm đã báo cáo NSE 0,474 ở h=2 — một
con số đẹp hơn thực tế 0,04 mà không ai biết.

Ghi chú phụ: NSE trên valid thấp hơn hẳn trên test (h=2: 0,28 so với 0,43) vì
giai đoạn valid chứa các mùa lũ lớn 2016, 2017 và 2020 — khó hơn giai đoạn
test.

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
