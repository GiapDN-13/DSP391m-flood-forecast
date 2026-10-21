# PHÁT HIỆN — SHAP cho mô hình chính: đặc trưng quan trọng có hợp lý thuỷ văn không?

**Ngày:** 21/10/2026 · Nhánh `feat/sat-latency` · Chạy lại: `python -m src.eval.shap_analysis` (~1 phút)
Số: `reports/shap_importance.csv` · Hình: `reports/figures/report/shap_*_en.png`

Mục bắt buộc của Report 3 (`PLAN.md` W7: "SHAP; kiểm tra feature quan trọng có hợp lý
thuỷ văn không"). Trả lời ba câu: mô hình dựa vào gì, chiều tác động có đúng vật lý
không, và vì sao vẫn dự báo thấp đỉnh lũ.

> **Cập nhật 21/10/2026: cấu hình chính đổi sang L2 cho h2–h3** (`lgbm.params_for(h)`: L1 ở h1,
> L2 trên log1p ở h2–h3, chọn bằng walk-forward/valid — `FINDINGS_TUNING.md`). `shap_importance.csv`
> và hình `shap_*_en.png` đã chạy lại với mô hình mới; số mới ở **§7**. §0–§6 dưới đây giữ nguyên
> số của bản L1 (file cũ `reports/l1_ref/shap_importance.csv`) để đối chiếu. h1 không đổi (cùng
> tham số) ⇒ §4 (hai ca đỉnh lũ h1) vẫn đúng nguyên văn.

---

## 0. Cách làm

* **Mô hình:** LightGBM cấu hình **E** của `ablation_ext` (88 feature = Report 2 + độ ẩm
  đất + đại diện hồ + bão/khí áp/gió/ENSO), `PARAMS` của `lgbm.py`, học trên
  train+valid 1997 → 2022-06-30 (9 283 ngày), seed 42.
* **Giải thích trên tập test** từ 2022-07-01: 1 522 / 1 521 / 1 520 ngày ở h = 1/2/3, trong đó
  **31 ngày** có Q(t+h) ≥ mức nguy cơ 1 (806 m³/s).
* **Kiểm tái lập trước khi đọc SHAP:** NSE khớp `ablation_ext.csv` **tuyệt đối** ở cả 9 lần
  chạy (3 horizon × 3 seed). Seed 42: **0,748 / 0,485 / 0,193**; trung bình 3 seed
  0,747 / 0,483 / 0,199.
* **SHAP:** `shap.TreeExplainer` (tree_path_dependent), đơn vị **log1p(Q)** — đơn vị mô
  hình học — nên cộng được: base + Σ SHAP = log1p(dự báo), sai số tối đa 3·10⁻¹⁴. SHAP
  +0,5 nghĩa là nhân (1 + Q) lên e^0,5 ≈ 1,65 lần. Base ≈ 4,19 (≈ 65 m³/s) ở h=1.
* **Gộp nhóm** (8 nhóm cơ chế): tầm quan trọng nhóm = trung bình |Σ SHAP trong nhóm| —
  cộng **có dấu** trước rồi mới lấy trị tuyệt đối, để các biến cùng nhóm triệt tiêu
  nhau (Q hôm nay +, Q hôm qua −) không bị thổi phồng. Nhóm "Mưa dài / đại diện hồ" (mưa
  15, 30 ngày, mưa tích luỹ từ 01/09) tách khỏi "Mưa ≤ 7 ngày" cho khớp cấu hình D.
* **Kiểm chiều vật lý:** Spearman ρ giữa giá trị feature và SHAP của chính nó trên tập
  test; |ρ| < 0,1 coi là không rõ chiều. Kiểm thêm ở mức nhóm và riêng mùa lũ / ngày mưa
  3 ngày ≥ 50 mm.
* **Độ ổn định:** tỉ trọng nhóm tính lại với seed 7 và 2026 — chênh tối đa **2,3 điểm %**,
  không đổi thứ tự kết luận. Bảng feature dùng seed 42.
* Phiên bản: `shap 0.48.0` trên máy (requirements ghim 0.46.0 — Python 3.13 không có
  wheel 0.46.0; CI Python 3.11 dùng đúng bản ghim).

## 1. Đặc trưng quan trọng nhất theo horizon

Tỉ trọng = mean |SHAP| của feature / tổng 88 feature, toàn tập test, seed 42
(hình `shap_beeswarm_h{1,2,3}_en.png`, `shap_bar_top15_en.png`):

| Hạng | h = 1 | h = 2 | h = 3 |
|---|---|---|---|
| 1 | `discharge` 37,4 % | `rain_basin` 20,0 % | `rain_basin` 16,0 % |
| 2 | `rain_thuong` 11,2 % | `discharge` 13,5 % | `discharge` 8,1 % |
| 3 | `rain_basin` 9,5 % | `rain_thuong` 12,3 % | `mslp_grad_north` 5,8 % |
| 4 | `q_diff1` 6,1 % | `mslp_grad_north` 4,0 % | `rain_thuong` 5,1 % |
| 5 | `rain_basin_roll3` 5,7 % | `rain_basin_roll30` 3,1 % | `mslp_sea` 4,8 % |
| 6 | `discharge_lag2` 2,0 % | `mslp_sea` 2,9 % | `rain_basin_roll30` 3,7 % |
| 7 | `rain_trung` 1,8 % | `rain_trung` 2,7 % | `month` 3,5 % |
| 8 | `rain_thuong_lag2` 1,7 % | `discharge_lag2` 1,7 % | `oni_lag3` 3,0 % |
| 9 | `rain_ha_roll3` 1,4 % | `q_diff1` 1,6 % | `wind_e_sea` 2,8 % |
| 10 | `mslp_grad_north` 1,3 % | `month` 1,6 % | `cloud_hue` 2,2 % |

* `discharge` là **Q hôm nay** (ngày phát dự báo). `discharge_lag1` chỉ hạng 29 ở h=1
  (0,4 %): thông tin của nó đã nằm trong `discharge` và `q_diff1`.
* Riêng **31 ngày lũ**, top 5 ở h=1 giữ nguyên. Ở h=2, `rain_thuong` lên hạng 2 (18,6 %);
  ở h=3, `month` và `doy_sin` vào top 8. Ở h=1, `sm_0_7`, `sm_7_28` vào top 10 ngày lũ
  — nhưng với **dấu âm** (§3).
* `rain_thuong` xếp trên `rain_ha` ở mọi horizon: nước sinh ra ở thượng nguồn, khớp
  `FINDINGS_MODEL.md` §3. Ba tiểu lưu vực tương quan 0,83–0,99 nên tầm quan trọng bị
  chia nhỏ giữa chúng — đọc theo nhóm ở §2.

## 2. Gộp theo cơ chế: h1 → h3 dựa vào đâu

% của tổng mean |Σ SHAP nhóm|, seed 42 (hình `shap_groups_en.png`, whisker = khoảng 3 seed):

| Nhóm | Toàn test h1 | h2 | h3 | Ngày lũ h1 | h2 | h3 |
|---|---|---|---|---|---|---|
| Lưu lượng trễ (Q, lag, q_diff) | **58,4** | 28,4 | 22,6 | **57,4** | 21,9 | 20,2 |
| Mưa ≤ 7 ngày | 33,3 | **46,4** | **33,3** | 35,0 | **52,0** | **34,5** |
| Mưa dài / đại diện hồ | 2,2 | 5,3 | 7,6 | 1,5 | 4,2 | 6,8 |
| Độ ẩm đất & API | 1,8 | 3,0 | 4,0 | 2,6 | 3,9 | 5,2 |
| Bão / ATNĐ | 0,9 | 2,4 | 4,1 | 0,7 | 2,8 | 5,5 |
| Khí áp, gió, ẩm (KK lạnh, gió đông) | 2,3 | 8,8 | **14,2** | 1,8 | 10,6 | **15,1** |
| ENSO | 0,5 | 1,6 | 5,0 | 0,3 | 0,9 | 3,6 |
| Mùa (lịch) | 0,7 | 4,1 | **9,2** | 0,7 | 3,7 | **9,1** |

1. **Đúng kỳ vọng:** lưu lượng trễ giảm mạnh từ 58 % xuống 23 % — quán tính dòng chảy
   tắt nhanh ở lưu vực có thời gian tập trung 5–6 giờ. Mưa quan trắc gánh chính ở h2
   (46 %, 52 % ngày lũ).
2. **Yếu tố quy mô lớn tăng theo horizon** — khí áp/gió 2 → 14 %, bão 1 → 4 %, ENSO
   0,5 → 5 %. Đây là cơ chế đằng sau +0,055 NSE ở h2 của cấu hình E so với D
   (`FINDINGS_FACTORS.md` §5): `mslp_grad_north` lên hạng 4 ở h2, hạng 3 ở h3.
3. **Bão vẫn nhỏ** (≤ 5,5 % kể cả ngày lũ): chỉ 35 ngày test có bão trong 300 km.
4. **Cảnh báo ở h3:** nhóm lịch 9 %, `month` hạng 7 — mô hình lùi một phần về khí hậu
   khi tín hiệu động lực yếu. Không áp đảo (< 10 %), nhưng phải ghi nhận.
5. SHAP có dấu trung bình trên ngày lũ: h1 lưu lượng +1,47, mưa +0,88; h3 lưu lượng
   +0,29, mưa +0,49, khí áp +0,23, **lịch +0,12 > bão +0,05**. Nhóm "Độ ẩm đất & API"
   **âm ở cả ba horizon** (−0,06 / −0,09 / −0,07).

## 3. Kiểm tính hợp lý thuỷ văn

ρ = Spearman(giá trị, SHAP) trên toàn test, h1 / h2 / h3:

| Feature | Kỳ vọng | ρ | Kết luận |
|---|---|---|---|
| `discharge` (Q hôm nay) | + | +1,00 / +0,98 / +0,96 | ✅ Đúng; bão hoà ở Q cao (§4) |
| `rain_basin`, `rain_thuong` (mưa hôm nay) | + | +0,89 / +0,96 / +0,96 · +0,80 / +0,89 / +0,95 | ✅ Đúng |
| `rain_basin_roll30` | + | +0,76 / +0,77 / +0,74 | ✅ Đúng |
| Mưa trễ 1–2 ngày (`*_lag1`, `*_lag2`) | + | `rain_basin_lag1` −0,63 / −0,79 / −0,84 | ⚠️ Ngược từng biến, **đúng ở mức nhóm** (+0,67 / +0,68 / +0,69) |
| `mslp_grad_north` (Hà Nội − Huế, KK lạnh) | + | +0,89 / +0,93 / +0,93 | ✅ Đúng; mạnh nhất trong nhóm mới |
| `mslp_sea`, `mslp_hue` (áp thấp) | − | −0,93 / −0,94 / −0,95 · −0,67 / −0,83 / −0,88 | ✅ Đúng |
| `wind_e_sea`, `cloud_hue`, `rh_hue` | + | +0,61 / +0,74 / +0,81 · +0,67 / +0,91 / +0,93 · +0,77 / +0,89 / +0,90 | ✅ Đúng |
| `storm_dist_km` (bão càng gần) | − | −0,18 / −0,19 / −0,41 | ✅ Đúng chiều nhưng **không đơn điệu** (dưới đây) |
| `storm_wind_kt` | + | +0,45 / +0,49 / +0,50 | ✅ Đúng, nhỏ (hạng 25–53) |
| `oni_lag3` (La Niña ⇒ nhiều nước) | − | −0,83 / −0,83 / −0,85 | ✅ Đúng chiều, nhưng chỉ 45 giá trị tháng trong test |
| `api` | + | +0,44 / −0,33 / +0,51 | ⚠️ Gần như không dùng (hạng 34–58, ≤ 0,6 %) |
| `sm_0_7`, `sm_7_28`, `sm_28_100` | + | `sm_7_28` −0,12 / −0,40 / −0,52 | ❌ **Ngược**; mùa lũ −0,79 / −0,83 / −0,83 |
| `rain_season_cum` (hồ đầy cuối mùa) | + | −0,16 / −0,00 / −0,23 | ❌ Không ủng hộ; ngày mưa ≥ 50 mm −0,73 / −0,70 / −0,74 |
| `et0` (nắng, bốc hơi) | − | +0,19 / +0,13 / −0,07 | ⚠️ Ngược nhẹ, nhỏ (hạng 21–39) |
| `month`, `doy_*` | — | `month` +0,81 / +0,92 / +0,91 | Học mùa, tăng theo horizon (§2) |

Ở mức nhóm, 6/7 nhóm có đại diện đúng chiều ở cả ba horizon. Nhóm duy nhất sai là
**Độ ẩm đất & API** (ρ với `api`: −0,10 / −0,42 / −0,27).

**(a) Mưa trễ âm — hợp lý, là hiệu ứng có điều kiện.** Thời gian tập trung nước 5–6 giờ
nên mưa hôm qua đã nằm sẵn trong Q hôm nay. Khi đã biết Q hôm nay, mưa hôm qua lớn
nghĩa là đỉnh đang đi qua và ngày mai sẽ rút. Cả nhóm mưa vẫn đẩy dự báo lên đúng chiều.

**(b) Độ ẩm đất ngược chiều — chỗ không hợp lý rõ nhất.** Hình `shap_dependence_h1_en.png`:
SHAP của `sm_7_28` gần 0 tới ~0,45 m³/m³ rồi **tụt xuống âm** khi đất gần bão hoà — đúng
vùng các ngày lũ. Độ ẩm đất ERA5-Land gần như là bản sao của trạng thái ẩm đã có trong
Q hôm nay (Spearman với Q(t) trên train: `sm_7_28` +0,74, `api` +0,77), nên mô hình dùng
nó như một biến **hiệu chỉnh** chứ không như cơ chế sinh dòng chảy. Khớp ablation: thêm độ
ẩm đất (C) không cải thiện (h1 0,766 → 0,757). EDA cho thấy nền ẩm quan trọng **biên**
(×6,9; Spearman API 0,68), nhưng khi đã có Q hôm nay thì phần thông tin thêm gần bằng 0.
⇒ **Không dùng SHAP độ ẩm đất để giải thích cơ chế** trong báo cáo.

**(c) Đại diện hồ không có cơ sở trong biến mục tiêu.** `rain_season_cum` âm vào ngày
mưa lớn — nhất quán với R1: GloFAS v4 không mô phỏng hồ (`FINDINGS_FACTORS.md` §4).
`rain_basin_roll30` thì đúng chiều — nó mang nghĩa "lưu vực ướt", không phải "hồ đầy".

**(d) Bão: tín hiệu báo trước, đúng vật lý nhưng không đơn điệu.** SHAP trung bình cả
nhóm bão theo khoảng cách bão – Huế hôm nay:

| Khoảng cách | n ngày | h1 | h2 | h3 |
|---|---|---|---|---|
| 0–300 km | 35 | +0,012 | −0,001 | +0,008 |
| 300–800 km | 102 | +0,046 | +0,136 | **+0,180** |
| 800–1 500 km | 100 | −0,000 | +0,011 | +0,048 |
| không có bão | ~1 285 | −0,004 | −0,010 | −0,019 |

Bão đang cách 300–800 km là tín hiệu "sắp tới", và tác động tăng theo horizon — đúng thứ
mưa quan trắc chưa biết. Bão đã sát Huế thì mưa của nó đã nằm trong mưa quan trắc, nên
nhóm bão không cộng thêm gì; riêng `storm_dist_km` < 150 km còn âm (−0,06 ở h1). Hệ quả
xấu: ngày bão đổ bộ mô hình không nâng dự báo (§4).

**(e) `mslp_grad_north`** tăng đơn điệu tới khoảng 5 hPa rồi giảm khi > 6 hPa (đợt lạnh
rất mạnh) — có thể là khối khí lạnh khô sau front, nhưng ít mẫu nên chưa kết luận.

**(f) ENSO.** Chiều đúng nhưng test chỉ có 4 mùa lũ, nên `oni_lag3` có thể đóng vai "mã
năm". Mùa 2023 (ONI +1,0) có 4 ngày ≥ mức 1, mùa 2025 (ONI −0,1) có 14 ngày — không đủ
để tách tác động ENSO khỏi khác biệt giữa các năm.

## 4. Vì sao vẫn dự báo thấp đỉnh — hai ngày đỉnh lũ (h = 1)

Dự báo phát ngày t cho ngày t+1 là đỉnh GloFAS. Hình `shap_waterfall_20221016_h1_en.png`,
`shap_waterfall_20251030_h1_en.png`.

| | Phát 15/10 → 16/10/2022 | Phát 29/10 → 30/10/2025 |
|---|---|---|
| Q hôm nay (GloFAS) | 751 m³/s | 2 316 m³/s |
| Mưa hôm nay / hôm qua (`rain_basin`) | 112 / 200 mm | 109 / 129 mm |
| Bão cách Huế | 107 km | không có |
| **GloFAS thật ngày đích** | **1 967** | **2 903** |
| **Dự báo** | **862** (0,44 lần) | **1 727** (0,59 lần) |
| base + Σ SHAP (log1p) | 4,19 + 2,57 = 6,76 | 4,19 + 3,26 = 7,45 |
| Cần (log1p thật) | 7,58 — thiếu 0,82 (×2,3) | 7,97 — thiếu 0,52 (×1,7) |
| Nhóm: lưu lượng / mưa / bão / ẩm đất | +1,49 / +1,11 / −0,06 / −0,08 | +1,80 / +1,33 / −0,00 / −0,01 |
| Ngày train có Q(t+1) ≥ giá trị thật | 12 / 9 283 | 5 / 9 283 |

Không phải thiếu đặc trưng — mưa và lưu lượng đều đẩy đúng chiều và mạnh. Thiếu là do
**cấu trúc dữ liệu + mô hình**:

1. **Trần dự báo.** Dự báo lớn nhất của mô hình trên toàn tập train chỉ **2 067 m³/s**
   (trên test: 1 727). `min_child_samples = 30` buộc mỗi lá chứa ≥ 30 ngày train, trong
   khi chỉ có 12 ngày Q(t+1) ≥ 1 967 m³/s ⇒ không lá nào "thuần" ngày cực trị. Cộng
   thêm L1 trên log1p (nhắm trung vị có điều kiện) ⇒ lá bị kéo về các ngày lũ vừa.
2. **Q hôm nay bị "bão hoà".** SHAP của `discharge` là +1,19 ở 751 m³/s và chỉ +1,35 ở
   2 316 m³/s. Mô hình học đúng dữ liệu: trong train, **12/12 ngày Q(t) ≥ 2 000 m³/s đều
   rút vào hôm sau** (trung vị Q(t+1)/Q(t) = 0,63); với Q ≥ 1 500 chỉ 13 % còn lên. Đợt
   10/2025 lên liên tục 3 ngày trên 2 000 m³/s là chưa từng có trong train, nên mô hình dự
   báo **rút** (1 727 < 2 316) đúng lúc nước còn lên.
3. **Quy tắc "mưa hôm qua đã qua" phản tác dụng khi mưa lớn kéo dài.** Ngày 15/10/2022,
   `rain_thuong_lag1` = 239 mm cho −0,04, và `rain_basin_roll3` = 315 mm chỉ cho +0,10.
4. **Bão sát Huế không được cộng thêm** (−0,06, xem §3d).

So với **sông thật** khoảng thiếu còn lớn hơn: chính GloFAS đã thấp hơn nước đổ vào hai hồ
nhiều lần (13 787 so với 1 967 m³/s ngày 15/10/2022 — `FINDINGS_FACTORS.md` §2).

Trên 31 ngày lũ của tập test, tỉ số trung vị dự báo / thật là **0,56 / 0,33 / 0,15** ở
h = 1/2/3: SHAP ở h3 đang giải thích một dự báo gần như không bắt được lũ.

## 5. Kết luận

1. **Hợp lý ở cốt lõi.** Mô hình dựa vào Q hôm nay và mưa quan trắc (thượng nguồn trước),
   đúng chiều, và chuyển trọng tâm đúng như vật lý: lưu lượng trễ 58 % → 23 %; khí áp/gió
   2 → 14 %, bão 1 → 4 % từ h1 → h3. Chênh áp Bắc–Huế (không khí lạnh) là biến mới có giá
   trị nhất, giải thích phần cải thiện h2 của cấu hình E.
2. **Không hợp lý, cần ghi rõ:**
   * Độ ẩm đất ERA5-Land tác động **ngược chiều** (đất càng ướt dự báo càng thấp), nhất là
     mùa lũ; nhóm độ ẩm đất & API âm trên ngày lũ.
   * Giả thuyết "hồ đầy cuối mùa" (`rain_season_cum`) không được dữ liệu ủng hộ.
   * h3 dựa 9 % vào lịch và 5 % vào ENSO — một phần là học khí hậu / học năm.
3. **Mưa trễ âm không phải lỗi** — hiệu ứng có điều kiện của lưu vực tập trung nước nhanh;
   cả nhóm mưa đúng chiều.
4. **Cắt ngọn đỉnh lũ là giới hạn cấu trúc** (ít mẫu cực trị, `min_child_samples`, L1 trên
   log, Q cao trong train luôn rút), không phải thiếu đặc trưng.

**Việc tiếp (chọn trên valid / walk-forward, không theo test):** thử bỏ `SOIL` và
`rain_season_cum`; hồi quy phân vị α = 0,9 hoặc giảm `min_child_samples` cho đường cận trên
mùa lũ.

## 6. Giới hạn

* SHAP giải thích **mô hình**, không giải thích sông: biến mục tiêu là GloFAS mô phỏng.
* Feature tương quan mạnh (Q và các lag; ba tiểu lưu vực r 0,83–0,99) chia nhau tầm quan
  trọng một cách tuỳ cây ⇒ đọc theo nhóm, đừng đọc thứ hạng lẻ của biến tương quan.
* ρ Spearman là chiều **biên** trên toàn test (gồm mùa khô); đã kiểm riêng mùa lũ / ngày mưa
  cho các biến đáng ngờ.
* Chỉ 31 ngày lũ trong 4 mùa lũ test; bảng feature dùng một seed (bảng nhóm dùng 3 seed,
  chênh ≤ 2,3 điểm %).

## 7. Cập nhật 21/10/2026 — mô hình chính L2 ở h2–h3

Chạy lại `python -m src.eval.shap_analysis` với `lgbm.params_for(h)`. Kiểm tái lập: NSE khớp
`ablation_ext.csv` mới tuyệt đối ở cả 9 lần chạy; seed 42 **0,748 / 0,503 / 0,231** (cũ 0,748 /
0,485 / 0,193); TB 3 seed 0,747 / 0,499 / 0,236. |base + ΣSHAP − f(x)| ≤ 7,5·10⁻¹⁴. Tỉ trọng
nhóm giữa 3 seed chênh tối đa **3,6** điểm % (cũ 2,3).

**Top 10 theo mean |SHAP| (seed 42), mới — h1 không đổi:**

| Hạng | h = 2 mới | h = 2 cũ | h = 3 mới | h = 3 cũ |
|---|---|---|---|---|
| 1 | `rain_basin` 15,0 % | `rain_basin` 20,0 % | **`discharge` 6,5 %** | `rain_basin` 16,0 % |
| 2 | `discharge` 9,7 % | `discharge` 13,5 % | `rain_basin` 6,1 % | `discharge` 8,1 % |
| 3 | `rain_thuong` 7,3 % | `rain_thuong` 12,3 % | `mslp_grad_north` 5,2 % | `mslp_grad_north` 5,8 % |
| 4 | `mslp_grad_north` 5,2 % | `mslp_grad_north` 4,0 % | `mslp_sea` 4,7 % | `rain_thuong` 5,1 % |
| 5 | `mslp_sea` 4,1 % | `rain_basin_roll30` 3,1 % | `rain_ha` 4,7 % | `mslp_sea` 4,8 % |
| 6 | `rain_basin_roll30` 2,7 % | `mslp_sea` 2,9 % | `month` 4,3 % | `rain_basin_roll30` 3,7 % |
| 7 | `discharge_lag2` 2,1 % | `rain_trung` 2,7 % | `rain_basin_roll30` 3,2 % | `month` 3,5 % |
| 8 | `month` 2,1 % | `discharge_lag2` 1,7 % | `oni_lag3` 2,9 % | `oni_lag3` 3,0 % |
| 9 | `q_diff1` 1,9 % | `q_diff1` 1,6 % | `rain_thuong` 2,9 % | `wind_e_sea` 2,8 % |
| 10 | `oni_lag3` 1,7 % | `month` 1,6 % | `wind_e_sea` 2,5 % | `cloud_hue` 2,2 % |

**Tỉ trọng nhóm (% mean |Σ SHAP nhóm|, seed 42), h2 / h3 mới (cũ):**

| Nhóm | Toàn test h2 | h3 | Ngày lũ h2 | h3 |
|---|---|---|---|---|
| Lưu lượng trễ | 26,3 (28,4) | 22,8 (22,6) | 20,7 (21,9) | 21,7 (20,2) |
| Mưa ≤ 7 ngày | 36,5 (46,4) | **22,5 (33,3)** | 44,5 (52,0) | 23,3 (34,5) |
| Mưa dài / đại diện hồ | 5,1 (5,3) | 7,8 (7,6) | 3,5 (4,2) | 6,2 (6,8) |
| Độ ẩm đất & API | 5,6 (3,0) | 4,7 (4,0) | 5,9 (3,9) | 3,8 (5,2) |
| Bão / ATNĐ | 3,5 (2,4) | 4,4 (4,1) | 3,5 (2,8) | 6,0 (5,5) |
| Khí áp, gió, ẩm | **12,7 (8,8)** | **16,3 (14,2)** | 14,1 (10,6) | 16,8 (15,1) |
| ENSO | 3,0 (1,6) | 5,9 (5,0) | 1,9 (0,9) | 5,2 (3,6) |
| Mùa (lịch) | 7,2 (4,1) | **15,6 (9,2)** | 6,0 (3,7) | **16,9 (9,1)** |

h1 không đổi (58,4 / 33,3 / 2,2 / 1,8 / 0,9 / 2,3 / 0,5 / 0,7).

**Kiểm chiều (ρ Spearman giá trị–SHAP, h1 / h2 / h3):** `discharge` +1,00 / +0,97 / +0,97;
`rain_basin` +0,89 / +0,96 / +0,94; `mslp_grad_north` +0,89 / +0,95 / +0,95; `mslp_sea` −0,93 /
−0,96 / −0,95; `oni_lag3` −0,83 / −0,78 / −0,78; `sm_7_28` −0,12 / **−0,25 / −0,27** (cũ −0,40 /
−0,52 — vẫn ngược nhưng yếu hơn; mùa lũ −0,79 / −0,83 / −0,70); `rain_season_cum` −0,16 / +0,02 /
+0,02 (cũ −0,00 / −0,23 — vẫn không ủng hộ "hồ đầy"; ngày mưa ≥ 50 mm −0,73 / −0,45 / −0,45);
`et0` +0,19 / +0,51 / +0,56 (ngược, hạng 15 ở h2). Mức nhóm: vẫn 6/7 nhóm đúng chiều, chỉ "Độ ẩm
đất & API" ngược (ρ với `api` −0,10 / −0,55 / −0,38). SHAP có dấu nhóm độ ẩm đất & API trên ngày
lũ: −0,06 / −0,13 / −0,04 (vẫn âm cả ba horizon).

**Bão theo khoảng cách (SHAP TB nhóm bão, h2 / h3):** 0–300 km +0,049 / −0,008 · 300–800 km
**+0,186 / +0,160** (cũ +0,136 / +0,180) · 800–1 500 km +0,020 / +0,050 · không bão −0,018 / −0,022.

**Ngày lũ (31 ngày):** trung vị dự báo / thật **0,56 / 0,34 / 0,20** (cũ 0,56 / 0,33 / 0,15).

**Đọc lại kết luận §5:**

1. Cốt lõi vẫn hợp lý và chuyển trọng tâm đúng vật lý; với L2, mô hình ở h2–h3 dựa **ít hơn vào
   mưa ≤ 7 ngày** và **nhiều hơn vào khí áp/gió (12,7 % / 16,3 %), ENSO và lịch**. Ở h3
   `discharge` và `rain_basin` gần ngang nhau (6,5 % / 6,1 %) — thay cho câu cũ "`rain_basin` hạng 1
   ở h2 và h3": nay **chỉ hạng 1 ở h2**.
2. **Cảnh báo học khí hậu mạnh hơn ở h3:** nhóm lịch 9,2 % → **15,6 %** (16,9 % ngày lũ), xấp xỉ
   nhóm khí áp/gió. L2 cải thiện NSE nhưng một phần là nhờ bám mùa — nhóm cần xem lại câu chữ.
3. Độ ẩm đất vẫn ngược chiều (yếu hơn) và `rain_season_cum` vẫn không có cơ sở ⇒ hai kết luận
   "không hợp lý" giữ nguyên.
4. Cắt ngọn ở h1 không đổi (§4); h2–h3 dự báo/thật nhích lên nhưng vẫn rất thấp (0,34 / 0,20).

## Tái lập

    set PYTHONIOENCODING=utf-8
    python -m src.eval.shap_analysis                 # bảng + 10 hình, ~1 phút
    python -m pytest tests/test_shap_analysis.py -q  # 9 passed
    python -m ruff check src/eval/shap_analysis.py tests/test_shap_analysis.py
