# PHÁT HIỆN — Các yếu tố ảnh hưởng tới dự báo (hồ chứa và hơn thế)

**Ngày:** 14/10/2026 · Nhánh `feat/data-ext-reservoir`

Câu hỏi của thầy: lưu lượng còn phụ thuộc mức xả của hồ chứa. Hồ chứa chỉ là một
trong nhiều yếu tố. File này liệt kê **mọi yếu tố đã biết**, phân theo việc nó tác
động vào đâu, rồi ghi rõ cái nào đã đưa vào mô hình, cái nào được xử lý bằng luật,
cái nào nằm ngoài phạm vi và vì sao.

Chạy lại:

    python -m src.ingest.crawl_extend        # mưa 1997–2009, độ ẩm đất, khí áp/gió
    python -m src.ingest.external_indices    # bão IBTrACS, ENSO ONI
    python -m src.features.build_panel --ext
    python -m src.eval.reservoir_check       # R1, R2
    python -m src.models.ablation_ext        # A → E

---

## 1. Bản đồ yếu tố — bốn lớp

Điểm mấu chốt: **biến mục tiêu là lưu lượng GloFAS (mô phỏng)**, không phải sông thật.
Nên mỗi yếu tố phải hỏi hai câu: nó có làm đổi lưu lượng GloFAS không, và nó có làm
sông thật khác GloFAS không.

### Lớp 1 — Gây ra lũ, có trong cả sông thật lẫn GloFAS → đưa vào mô hình

| Yếu tố | Cơ chế | Dữ liệu mở | Trạng thái |
|---|---|---|---|
| Mưa lưu vực | Nguồn nước chính | ERA5 qua Open-Meteo | Có từ 2010 → **mở rộng về 1997** |
| Độ ẩm đất | Đất bão hoà ⇒ cùng trận mưa sinh lũ lớn hơn (EDA: ×6,9) | ERA5-Land 3 tầng + ET₀ | **Mới** — trước chỉ ước lượng bằng API |
| Bão / áp thấp nhiệt đới | Mưa cực lớn trong 1–3 ngày | IBTrACS v04r01 (NOAA): 417 cơn trong bán kính 1 500 km từ 1996 | **Mới**: khoảng cách, sức gió, tốc độ tiến lại |
| Không khí lạnh + nhiễu động gió đông | Kiểu mưa lũ đặc trưng tháng 10–11 ở Huế | ERA5: khí áp, gió tại Huế, Hà Nội, ngoài khơi | **Mới**: chênh áp Hà Nội − Huế, gió đông bắc |
| ENSO (El Niño / La Niña) | Điều biến lượng mưa cả mùa | ONI (NOAA CPC) | **Mới**, trễ 3 tháng để không dùng số chưa công bố |
| Mưa dự báo | Đầu vào khi vận hành thật | Kho dự báo Open-Meteo | Có (kịch bản B) |

Kiểm chứng nhanh: lũ trái mùa **14/06/2025** (2 055 m³/s) — trước đây bị nghi là lỗi —
trùng **bão Wutip** đi qua cách Huế ~200 km ngày 12–13/06, mưa lưu vực 181 và 98 mm.
Có dữ liệu bão thì ngày này hết là "ngoại lai khó hiểu".

### Lớp 2 — Làm sông thật khác GloFAS → xử lý bằng luật và kiểm chứng, không học được

| Yếu tố | Vì sao không đưa vào huấn luyện | Cách xử lý |
|---|---|---|
| **Xả hồ Tả Trạch, Bình Điền** | Không có chuỗi số liệu theo ngày; chỉ có tin báo lúc lũ (57 ngày) | Luật nâng sàn khi có lệnh xả (§3) + kiểm chứng R2 |
| GloFAS mô phỏng thiếu lũ cực đoan | Đây chính là biến mục tiêu | Ghi rõ là hạn chế; mức nguy cơ theo phân vị (tương đối) thay vì m³/s tuyệt đối |
| Lấy nước tưới, cấp nước | Nhỏ so với lũ, gần như không có trong mùa lũ | Ngoài phạm vi |

Hai hồ **không** liên quan: Hương Điền (sông Bồ) và A Lưới (nước qua tuabin sang sông
Bồ, xả tràn sang Lào theo sông A Sáp). Sông Bồ nhập sông Hương ở ngã ba Sình, hạ lưu
Kim Long; ô lưới GloFAS cũng đã chọn để không gộp sông Bồ.

### Lớp 3 — Chỉ đổi MỰC NƯỚC tại Kim Long, không đổi lưu lượng

Ngưỡng báo động chính thức tính bằng **mét** (1,0 / 2,0 / 3,5 m), còn ta dự báo
**m³/s**. Các yếu tố sau làm cùng một lưu lượng cho ra mực nước khác nhau — đây là lý
do quan hệ mực nước – lưu lượng chỉ đạt **R² = 0,18** (EDA E5):

| Yếu tố | Ghi chú |
|---|---|
| Thuỷ triều cửa Thuận An | Mực nước biển Open-Meteo chỉ có từ 2023 — quá ngắn để huấn luyện |
| Nước dâng do bão | Trùng đúng ngày lũ lớn |
| Đập ngăn mặn Thảo Long | Vận hành cửa đập đổi mực nước hạ lưu |
| Cửa biển, phá Tam Giang, lòng sông thay đổi | Bồi lấp, khai thác cát làm quan hệ H–Q trôi theo năm |
| Sông Bồ tràn sang sông Hương khi lũ lớn | Qua vùng đồng bằng, không có trong ô lưới |

⇒ Không đổi m³/s sang mét bằng một đường cong cố định. Giữ mức nguy cơ theo lưu lượng.

### Lớp 4 — Rủi ro dữ liệu và hệ thống

| Rủi ro | Ảnh hưởng | Cách đối phó |
|---|---|---|
| GloFAS đổi chế độ 07/2022 (reanalysis → kho dự báo) | Chuỗi mục tiêu đổi tính chất | Test chỉ trên 2022-07 về sau; đã kiểm (Mann–Whitney p = 0,58) |
| **GloFAS v5** thêm ~800 hồ chứa (tiêu chí: dung tích ≥ 100 triệu m³, lưu vực ≥ 500 km², mức điều tiết ≥ 0,8; dưới mức này mô phỏng như hồ tự nhiên) | Tả Trạch (646 triệu m³, 717 km²) và Bình Điền (424 triệu m³, 515 km²) đạt hai tiêu chí đầu; tiêu chí điều tiết chưa kiểm được ⇒ chuỗi mục tiêu **có thể** đổi | Khi Open-Meteo chuyển v5: chạy lại R1, huấn luyện lại |
| Mưa ERA5 hụt ở mưa địa hình cực lớn | 11/2024: ERA5 332 mm, núi 500–800 mm | Ghi rõ hạn chế; vệ tinh IMERG/CHIRPS là hướng tiếp |
| Mưa ERA5 vài ngày gần nhất là bản sơ bộ (ERA5T) | Có thể bị sửa | Vận hành thật dùng mưa dự báo, không dùng ERA5 |
| API giới hạn hạn mức theo giờ | Crawler bị chặn (gặp lại 14/10/2026) | Resume theo file, chờ hết giờ rồi chạy tiếp |
| Khí hậu không dừng | Phân phối mưa cực trị dịch dần | Walk-forward theo thời gian, không trộn ngẫu nhiên |

---

## 2. R2 — Số liệu hồ công bố so với GloFAS

Nguồn: `data/external/reservoir_releases.csv` — 132 dòng, 57 ngày, 2016–2026, mỗi dòng có
URL, ngày truy cập và trích nguyên văn. Thông số hồ: Phụ lục I, QĐ 1606/QĐ-TTg
(`reservoir_info.csv`).

Hai cận dưới, đều bảo thủ:

* **Lượng xả** của hai hồ thượng nguồn, lấy giá trị **nhỏ nhất** mỗi hồ được báo trong
  ngày (báo đưa tin ở những giờ khác nhau, cộng hai đỉnh không cùng lúc là thổi phồng).
* **Lượng nước đổ vào** hai hồ: hai hồ chiếm 1 232 / ~1 540 km² lưu vực tới Kim Long, nên dòng
  chảy tự nhiên tại Kim Long còn lớn hơn con số này.

So với GloFAS ngày t hoặc t+1, lấy giá trị lớn hơn:

| Phép thử | GloFAS thấp hơn cận dưới |
|---|---|
| Lượng xả hai hồ | **11 / 24 ngày** |
| Lượng nước đổ vào hai hồ | **14 / 23 ngày** |

Ngày điển hình:

| Ngày | Xả (cận dưới) | Nước vào hai hồ | GloFAS | Ghi chú |
|---|---|---|---|---|
| 15/10/2022 | 3 672 | 13 787 | 1 967 | Kim Long vượt BĐ III 0,5 m |
| 15/11/2023 | 3 650 | — | 584 | |
| 26/11/2024 | 1 994 | 2 186 | 505 | |
| 27/10/2025 | 3 669 | 13 433 | 2 022 | Lũ lịch sử |

**Lưu ý so sánh:** số của tỉnh là **tức thời** (theo giờ), GloFAS là **trung bình
ngày**. Đỉnh tức thời luôn lớn hơn trung bình ngày, nên một phần chênh lệch là do
khác cách đo. Nhưng chênh tới 2–7 lần ở những ngày lũ lớn thì không thể giải thích
hết bằng khác cách đo.

**Kết luận R2:**

1. Vấn đề lớn nhất không phải là hồ xả, mà là **GloFAS mô phỏng thiếu chính trận lũ**.
   Nước đổ vào hồ — dòng chảy tự nhiên, chưa qua điều tiết — đã gấp nhiều lần GloFAS.
   Khớp với hạn chế đã biết: mưa ERA5 hụt mạnh ở mưa địa hình cực lớn.
2. Vì vậy mô hình dự báo **mức nguy cơ theo phân vị của chính GloFAS** (tương đối) là
   đúng hướng; con số m³/s tuyệt đối của ngày lũ lớn không được đọc như lưu lượng thật.
3. `peak_bias −0,45` của LightGBM là so với GloFAS. So với sông thật, đỉnh lũ còn bị
   đánh giá thấp hơn nữa.

Hình: `reports/figures/report/res2_release_vs_glofas_en.png`.

## 3. Luật vận hành khi hồ xả

Nước hồ đã xả phải chảy qua Kim Long trong vài giờ (hai hồ cách Kim Long vài chục km).
Nên khi tỉnh phát lệnh xả:

    dự báo tại Kim Long = max(dự báo mô hình, tổng xả Tả Trạch + Bình Điền)

* File nhập tay `data/external/reservoir_orders.csv`
  (`date_from, date_to, reservoir, q_out_m3s, source_url`).
* Job hằng ngày (`predict_daily.py`) thêm cột `q_release_upstream` và `glofas_san_ho`;
  cột GloFAS thô giữ nguyên.
* Chỉ **nâng**, không bao giờ hạ dự báo. Không có lệnh ⇒ không đổi gì.
* Hương Điền, A Lưới bị bỏ qua có chủ đích (khác lưu vực).

Quy trình liên hồ (QĐ 1606/QĐ-TTg, 13/11/2019): mùa lũ vận hành **01/09 – 15/12**.
Feature "mưa tích luỹ từ 01/09" dùng đúng mốc này.

## 4. R1 — GloFAS có mô phỏng hồ không?

So chuỗi GloFAS **trước khi có hồ** (1998–2008) với **sau khi cả hai hồ vận hành**
(2014–2026), panel mở rộng 1997–2026. Nếu GloFAS có mô phỏng hồ thì dòng kiệt phải
tăng (hồ xả bù mùa khô), độ "giật" (flashiness) và phản ứng với mưa bão phải giảm.

| Chỉ số | Trước (trung vị) | Sau (trung vị) | Thay đổi | p (Mann–Whitney) | Nếu có mô phỏng hồ |
|---|---|---|---|---|---|
| Dòng kiệt 30 ngày (m³/s) | 29,7 | 26,5 | −10,7 % | 0,42 | phải **tăng** |
| Hệ số dòng chảy (lưu vực 1 540 km²) | 0,857 | 0,875 | +2,2 % | 0,91 | gần như không đổi |
| Flashiness (Richards–Baker) | 0,435 | 0,441 | +1,3 % | 0,64 | phải **giảm** |
| Phản ứng với mưa bão | 5,80 | 5,98 | +3,2 % | 0,64 | phải **giảm** |

(n = 11 năm trước / 13 năm sau; phản ứng bão: 25 / 37 sự kiện.)

**Kết luận R1:** không chỉ số nào đổi có ý nghĩa thống kê, và cả ba chỉ số nhạy với hồ
đều đổi **ngược** chiều hoặc không đổi. Không thấy dấu vết hồ Tả Trạch / Bình Điền
trong GloFAS v4 tại ô này ⇒ GloFAS mô phỏng sông như chưa có hồ. Đây là lý do cần
luật nâng sàn khi có lệnh xả (§3) thay vì trông vào biến mục tiêu.

Giới hạn: chỉ 11 và 13 năm; mưa hai giai đoạn khác nhau cũng làm đổi các chỉ số
(hệ số dòng chảy đã chia cho mưa nên đỡ hơn). Hình: `reports/figures/report/res1_dam_era_en.png`.

## 5. Thêm dữ liệu có giúp mô hình không? (A → E)

LightGBM, cùng tham số, test từ 2022-07-01, trung bình 3 seed (42, 7, 2026), mỗi cấu
hình cộng dồn lên cấu hình trước (`reports/ablation_ext.csv`):

| Cấu hình | Thêm gì | NSE h1 | NSE h2 | NSE h3 |
|---|---|---|---|---|
| A | Report 2 (train từ 2010) | 0,745 | 0,420 | 0,172 |
| B | Mưa 1997–2009 → train gấp đôi (9 298 ngày) | **0,766** | 0,428 | 0,176 |
| C | + độ ẩm đất ERA5-Land | 0,757 | 0,430 | 0,181 |
| D | + đại diện cho mức nước hồ: mưa 15 và 30 ngày, mưa tích luỹ từ 01/09 (QĐ 1606) | 0,756 | 0,428 | 0,186 |
| E | + bão, không khí lạnh, ENSO | 0,747 | **0,483** | **0,199** |

Độ lệch chuẩn giữa 3 seed ≤ 0,009, nên các chênh lệch ≥ 0,02 là thật với lần chia này.

**Kết luận:**

1. **Chuỗi dài hơn giúp h1** (+0,021): mưa từ 1997 cho mô hình thấy thêm nhiều trận lũ.
2. **Yếu tố thời tiết quy mô lớn giúp h2–h3** (+0,055 / +0,014 so với D): bão và không
   khí lạnh báo trước mưa lớn 1–3 ngày — đúng thứ mà mưa đã quan trắc không biết.
3. Độ ẩm đất và đặc trưng hồ không thêm được gì rõ — thông tin đó đã nằm sẵn trong
   lưu lượng trễ và API.
4. Không cấu hình nào gỡ được cắt ngọn lũ (peak_bias vẫn −0,42 → −0,88): giới hạn nằm
   ở chính GloFAS (§2), không phải ở thiếu đặc trưng.

Cột POD1/FAR1 trong file csv là lấy ngưỡng trên lưu lượng **hồi quy**, không so trực
tiếp với bộ phân loại riêng (POD 0,645).

### 5.1 Cập nhật 21/10/2026: cấu hình chính đổi sang L2 cho h2–h3

Trưởng nhóm chốt: mô hình chính = LightGBM cấu hình E với hàm mất mát **L1 ở h1, L2
(`regression`, vẫn trên log1p) ở h2–h3** (`lgbm.MAIN_OBJECTIVE`, `lgbm.params_for(h)`).
Lựa chọn dựa trên walk-forward 13 fold + valid 2016–06/2022 (`docs/FINDINGS_TUNING.md`, cấu hình
"E L2": ΔNSE h2 +0,039, h3 +0,036, thắng 11/2 fold, p 0,003 / 0,002; valid +0,059 / +0,053),
**không** theo test. h1 giữ L1 vì walk-forward không có ý nghĩa (+0,018, p 0,22) và valid âm (−0,011).

`ablation_ext.py` chạy lại với **cùng quy tắc cho cả A–E** (chỉ bộ cột khác nhau ⇒ phép so đặc
trưng vẫn công bằng); cột `objective` trong `reports/ablation_ext.csv`. Bảng cũ (L1 mọi horizon) ở
trên giữ nguyên để đối chiếu; file cũ: `reports/l1_ref/ablation_ext.csv`. h1 trùng tuyệt đối
(cùng tham số).

| Cấu hình | NSE h1 | NSE h2 mới (cũ) | NSE h3 mới (cũ) |
|---|---|---|---|
| A | 0,745 | 0,432 (0,420) | 0,166 (0,172) |
| B | **0,766** | 0,447 (0,428) | 0,192 (0,176) |
| C | 0,757 | 0,454 (0,430) | 0,208 (0,181) |
| D | 0,756 | 0,461 (0,428) | 0,199 (0,186) |
| E | 0,747 | **0,499** (0,483) | **0,236** (0,199) |

Độ lệch chuẩn giữa 3 seed ≤ 0,012 (cũ 0,009). peak_bias −0,42 → −0,89 (cũ −0,42 → −0,88);
E h2 −0,73 → −0,71, h3 −0,88 → −0,86 — L2 giảm cắt ngọn rất ít.

Đọc lại kết luận:

1. L2 giúp ở h2 với mọi cấu hình (+0,012 … +0,033) và ở h3 với B–E (+0,013 … +0,037); riêng
   A h3 giảm nhẹ (−0,006, cỡ 1 sd).
2. **E vẫn là cấu hình tốt nhất ở h2–h3**, chênh so với D nay +0,038 / +0,037 (cũ +0,055 / +0,014).
3. Chuỗi dài (B) giờ giúp cả h2–h3 (+0,016 / +0,026 so với A), không chỉ h1.
4. Độ ẩm đất (C) và đại diện hồ (D): thay đổi nhỏ, trái dấu (C − B: +0,007 / +0,016; D − C:
   +0,007 / −0,009), trong khoảng ~2 sd seed ⇒ kết luận "không thêm gì rõ" giữ nguyên.
5. **AC-1 (một lần chia, cấu hình E):** h1 0,747 ≥ 0,70 ✅ · h2 0,499 ≥ 0,40 ✅ · h3 0,236 < 0,25 ❌
   (thiếu 0,014). Walk-forward 13 fold (`reports/wf_sat_summary.csv`, E0): xem
   `FINDINGS_HOURLY_FINEGRID.md` §12.5.
6. Mức 1 theo hồi quy ở h2: POD 0,054 → 0,118, FAR 0,000 → 0,067 (E, test, TB 3 seed); h3 vẫn 0.
