# PHÁT HIỆN — Ngưỡng cảnh báo theo chi phí cho bộ phân loại mức nguy cơ (FR-M5)

**Ngày:** 21/10/2026 · Nhánh `feat/sat-latency` · Chạy lại: `python -m src.models.cost_threshold` (~8–12 phút, 4 luồng, seed 42)
Số: `reports/cost_threshold.csv` · Hình: `reports/figures/report/cost_threshold_en.png` · Test: `tests/test_cost_threshold.py`

`classifier.py` báo động khi xác suất ≥ 0,5. `RESEARCH_DESIGN.md` §3.3 yêu cầu thay bằng ngưỡng tối thiểu
chi phí kỳ vọng với tỉ lệ bỏ sót : báo nhầm = **10 : 1** (`cfg.COST_RATIO_MISS_TO_FALSE_ALARM`), kèm độ
nhạy **5 : 1** và **20 : 1**. Hai câu hỏi: (1) ngưỡng theo chi phí có giảm chi phí **ngoài mẫu** không;
(2) cấu hình E (thêm đất, đại diện hồ, bão/khí áp/ENSO) có giúp bộ phân loại không.

---

## 0. Cách làm

* **Chi phí** C = R · misses + 1 · false_alarms, R ∈ {5, 10, 20}. "Không bao giờ báo" tốn R × số ngày
  dương — mốc 1,0 trên hình.
* **Mô hình:** `LGBMClassifier` đúng tham số `classifier.py` (`scale_pos_weight = n_âm/n_dương`), seed 42;
  nhãn "Q(t+h) ≥ mức k". Làm mức 1 và mức 2; mức 3 không làm (≤ 9 ngày dương/năm tốt nhất).
* **Hai bộ đặc trưng:** **R2** = `classifier.feature_cols` (66 cột, panel từ 2010). **E** = cấu hình E của
  `ablation_ext` (88 cột, panel từ 1997). Đối chứng **B** = đặc trưng R2 nhưng học từ 1997 (`--sets B`) để
  tách "thêm năm học" khỏi "thêm đặc trưng". Nhãn **chung** cho mọi bộ ⇒ so được từng fold.
* **Không bao giờ chọn ngưỡng trên test.** Lưới 108 ngưỡng (10⁻⁴ … 0,999); hoà chi phí thì lấy ngưỡng gần 0,5 nhất.
  * **Một lần chia** (test ≥ 2022-07-01): mô hình học train (≤ 2015) dự báo valid (2016 → 06/2022, 48 ngày
    ≥ mức 1) ⇒ chọn ngưỡng; mô hình học train + valid (đúng `classifier.py`) dự báo test (31 ngày ≥ mức 1)
    ⇒ áp ngưỡng đã chọn. **Kiểm tái lập:** ở 0,5, R2 khớp `classifier_results.csv` tuyệt đối cả 6 dòng
    (mức 1 h1: 20 / 11 / 5 → POD 0,645 · FAR 0,20 · CSI 0,556).
  * **Walk-forward theo năm** (`walk_forward_sat.year_fold`, gap 3 ngày): mỗi năm Y một mô hình học tới
    28/12/(Y−1), dự báo cả năm Y (OOF). Ngưỡng cho năm Y chọn trên **OOF gộp của các năm < Y**, chỉ lấy
    hàng ≤ 28/12/(Y−1). Bể có < 10 ngày dương ⇒ giữ 0,5.
  * Tổng hợp chính 2013–2025 (13 fold): hits/misses/FA **cộng qua fold**; so từng fold bằng Wilcoxon và
    CI 95 % bootstrap theo fold. Ngưỡng lưu lượng mỗi fold = Q95/Q98 mùa lũ từ 1997 tới hết cửa sổ train
    (mức 1: 737–773 m³/s) ⇒ **104 ngày ≥ mức 1**, 35 ngày ≥ mức 2.
* **Mốc so sánh:** ngưỡng 0,5 · persistence (báo khi Q hôm nay đã ≥ mức k) · ngưỡng lý thuyết w/(w+R)
  (≈ 0,84–0,87 ở R = 10, mức 1).

---

## 1. Bảng chính — mức nguy cơ 1

"0,5 → chọn": chi phí ở ngưỡng 0,5 → ở ngưỡng chọn theo chi phí. WF ΔC/fold = trung bình (chọn − 0,5)
mỗi fold, âm là rẻ hơn · CI 95 % bootstrap theo fold · p Wilcoxon · số fold rẻ hơn/đắt hơn.
Test ≥ 07/2022: 31 ngày dương. WF 2013–2025: 104 ngày dương.

| Bộ | h | R | Test: ngưỡng (chọn trên valid) | Test POD / FAR / CSI | Test C (0,5 → chọn) | WF: ngưỡng trung vị [min–max] | WF POD / FAR / CSI | WF C (0,5 → chọn) | WF ΔC/fold [CI 95 %] · p · rẻ/đắt |
|---|---|---|---|---|---|---|---|---|---|
| R2 | 1 | 5:1 | 0,03 | 0,87 / 0,54 / 0,43 | 60 → **52** | 0,02 [0,02–0,5] | 0,74 / 0,56 / 0,38 | 237 → **235** | −0,2 [−3,2; +2,8] · 0,840 · 6/5 |
| E | 1 | 5:1 | 0,04 | 0,87 / 0,50 / 0,47 | 62 → **47** | 0,05 [0,05–0,19] | 0,85 / 0,50 / 0,46 | 200 → **168** | −2,5 [−6,4; +1,2] · 0,518 · 5/7 |
| R2 | 1 | 10:1 | 0,0026 | 0,94 / 0,73 / 0,26 | 115 → **99** | 0,02 [0,0026–0,5] | 0,80 / 0,63 / 0,34 | 447 → **353** | −7,2 [−13,6; −1,3] · 0,077 · 8/4 |
| E | 1 | 10:1 | 0,04 | 0,87 / 0,50 / 0,47 | 117 → **67** | 0,03 [0,02–0,04] | 0,88 / 0,55 / 0,43 | 360 → **239** | −9,3 [−16,4; −2,6] · 0,042 · 8/4 |
| R2 | 1 | 20:1 | 0,0004 | 0,94 / 0,84 / 0,16 | 225 → **194** | 0,0014 [0,0002–0,5] | 0,84 / 0,72 / 0,26 | 867 → **567** | −23,1 [−44,2; −5,7] · 0,028 · 9/3 |
| E | 1 | 20:1 | 0,02 | 0,90 / 0,56 / 0,42 | 227 → **96** | 0,0026 [0,0014–0,0026] | 0,93 / 0,69 / 0,31 | 680 → **352** | −25,2 [−45,1; −7,2] · 0,046 · 9/4 |
| R2 | 2 | 5:1 | 0,19 | 0,58 / 0,61 / 0,31 | 110 → **93** | 0,08 [0,02–0,5] | 0,40 / 0,73 / 0,19 | 459 → **422** | −2,8 [−9,3; +2,8] · 0,988 · 4/7 |
| E | 2 | 5:1 | 0,03 | 0,81 / 0,81 / 0,19 | 117 → **134** | 0,36 [0,14–0,37] | 0,38 / 0,62 / 0,24 | 385 → **384** | −0,1 [−1,3; +0,9] · 0,922 · 2/5 |
| R2 | 2 | 10:1 | 0,0026 | 0,84 / 0,88 / 0,12 | 210 → **245** | 0,005 [0,005–0,5] | 0,61 / 0,84 / 0,15 | 889 → **734** | −11,9 [−29,2; +2,5] · 0,320 · 6/5 |
| E | 2 | 10:1 | 0,02 | 0,81 / 0,83 / 0,16 | 217 → **185** | 0,01 [0,01–0,03] | 0,75 / 0,82 / 0,17 | 730 → **609** | −9,3 [−18,1; −0,5] · 0,151 · 8/5 |
| R2 | 2 | 20:1 | 0,0004 | 0,94 / 0,92 / 0,08 | 410 → **360** | 0,005 [0,005–0,5] | 0,64 / 0,83 / 0,15 | 1749 → **1074** | −51,9 [−87,5; −21,5] · 0,012 · 9/3 |
| E | 2 | 20:1 | 0,0026 | 0,97 / 0,89 / 0,11 | 417 → **254** | 0,005 [0,005–0,01] | 0,85 / 0,84 / 0,16 | 1420 → **778** | −49,4 [−75,3; −22,3] · 0,010 · 10/3 |
| R2 | 3 | 5:1 | 0,48 | 0,13 / 0,79 / 0,09 | 150 → **150** | 0,85 [0,25–0,91] | 0,00 / 1,00 / 0,00 | 520 → **527** | +0,5 [−1,8; +3,1] · 0,861 · 6/4 |
| E | 3 | 5:1 | 0,33 | 0,19 / 0,79 / 0,11 | 149 → **147** | 0,7 [0,52–0,995] | 0,07 / 0,65 / 0,06 | 475 → **498** | +1,8 [−0,4; +4,1] · 0,258 · 4/5 |
| R2 | 3 | 10:1 | 0,005 | 0,84 / 0,87 / 0,12 | 285 → **230** | 0,25 [0,005–0,91] | 0,09 / 0,91 / 0,05 | 1010 → **1039** | +2,2 [−3,8; +8,5] · 0,575 · 5/6 |
| E | 3 | 10:1 | 0,07 | 0,45 / 0,80 / 0,16 | 284 → **225** | 0,19 [0,12–0,23] | 0,30 / 0,80 / 0,14 | 920 → **853** | −5,2 [−11,8; +0,8] · 0,175 · 7/4 |
| R2 | 3 | 20:1 | 0,005 | 0,84 / 0,87 / 0,12 | 555 → **280** | 0,0007 [0,0004–0,5] | 0,53 / 0,93 / 0,07 | 1990 → **1675** | −24,2 [−66,6; +15,4] · 0,424 · 6/6 |
| E | 3 | 20:1 | 0,02 | 0,61 / 0,86 / 0,13 | 554 → **358** | 0,01 [0,005–0,01] | 0,64 / 0,89 / 0,10 | 1810 → **1277** | −41,0 [−75,0; −9,0] · 0,060 · 10/3 |

**Mốc so sánh, 10 : 1, chi phí walk-forward (h1 / h2 / h3):**

| Cách báo | R2 | E |
|---|---|---|
| Không bao giờ báo | 1 040 / 1 040 / 1 040 | 1 040 / 1 040 / 1 040 |
| Persistence | 539 / 847 / 924 | 539 / 847 / 924 |
| Ngưỡng lý thuyết w/(w+R) | 632 / 1 000 / 1 023 | 441 / 891 / 1 015 |
| Ngưỡng 0,5 | 447 / 889 / 1 010 | 360 / 730 / 920 |
| **Ngưỡng theo chi phí** | **353 / 734 / 1 039** | **239 / 609 / 853** |

---

## 2. Đọc kết quả

### 2.1 Ngưỡng tối ưu thấp hơn 0,5 rất nhiều — và ngược chiều lý thuyết

* **E h1 10:1** chọn 0,02–0,04 ở **cả 13 fold** (ổn định). **R2** chọn 0,02 ở 2014–2020 và 0,003–0,005 ở
  2021–2025; fold 2013 phải giữ 0,5 vì bể OOF chỉ có 1 ngày dương.
* **Ngưỡng lý thuyết đắt hơn cả 0,5 ở mọi h** (≈ 0,84–0,87; WF h1: E 441 so với 360, R2 632 so với 447):
  mô hình khớp rất sát train (400 cây), ngày dương mới thường chỉ nhận p ~0,01–0,1.
* ⇒ Xác suất của bộ phân loại **xếp hạng được nhưng không hiệu chỉnh**. Phải hiệu chỉnh (FR-M6, isotonic)
  trước khi gọi là "xác suất" trên dashboard; 0,02–0,04 chỉ là điểm cắt trên thang điểm của chính mô hình.

### 2.2 Mức 1, h = 1: giảm chi phí rõ ở 10:1 và 20:1

* **10:1, E:** WF 360 → **239 (−34 %)**, ΔC −9,3/fold [−16,4; −2,6], p = 0,042, rẻ hơn 8/13 fold.
  **R2:** 447 → 353 (−21 %), p = 0,077.
* **Đổi lại (E):** POD 0,69 → 0,88 nhưng FAR 0,36 → 0,55, CSI 0,50 → 0,43. Trong 13 năm: ngày báo
  112 → 200 (8,6 → 15,4/năm), báo nhầm 40 → 109 (3,1 → 8,4/năm), bỏ sót 32 → 13. CSI giảm là đúng bản
  chất: CSI cân hai loại sai như nhau, còn 10:1 thì không.
* **20:1:** có ý nghĩa ở h1 (E −25,2/fold p 0,046; R2 −23,1 p 0,028) và h2 (E −49,4 p 0,010; R2 −51,9 p 0,012).
* **5:1:** không có lợi — ở tỉ lệ này 0,5 đã gần tối ưu.

### 2.3 h = 2–3: chi phí giảm nhưng không đủ bằng chứng

* **h2 10:1:** E 730 → 609 (p 0,15), R2 889 → 734 (p 0,32); R2 ở 0,5 (889) còn **kém persistence** (847).
* **h3 10:1:** R2 ở ngưỡng chọn 1 039 ≈ không báo (1 040), kém persistence (924); E 920 → 853 (p 0,18);
  CSI ≤ 0,17 ở mọi cách.
* **Một lần chia, R2 h2 10:1 đắt hơn 0,5** (210 → 245): ngưỡng chọn trên mô hình học 2010–2015 không chuyển
  được sang mô hình học tới 06/2022 ⇒ **walk-forward là bằng chứng chính**.

### 2.4 Mức 2: không có lợi

* E 35 ngày dương / 13 fold; R2 31 / 12 fold. Ở 5:1 và 10:1 không có chênh nào có ý nghĩa (E 5:1 h1 còn
  đắt hơn 0,5 ở 6/6 fold có khác biệt, p 0,031). Ở 20:1 có giảm nhưng p ≥ 0,17. Một lần chia chỉ có 12 ngày
  dương (< 30) — không dùng làm kết luận.

---

## 3. E có giúp bộ phân loại không?

ΔC = E − R2 mỗi fold, mức 1, 10 : 1, 13 fold chung, cùng nhãn:

| h | Ngưỡng theo chi phí | Ngưỡng 0,5 |
|---|---|---|
| 1 | −8,8 [−14,6; −3,0] · p 0,015 · 10/2 | −6,7 [−14,1; +0,2] · p 0,196 |
| 2 | −9,6 [−19,8; −0,5] · p 0,130 · 9/4 | −12,2 [−21,8; −3,0] · p 0,040 |
| 3 | −14,3 [−22,8; −5,8] · p 0,021 · 8/3 | −6,9 [−13,9; −0,2] · p 0,027 |

Bỏ fold 2013 (R2 phải giữ 0,5): h1 −7,2 (p 0,030) và h3 −13,5 (p 0,041) vẫn giữ.

**Tách bằng đối chứng B** (đặc trưng R2, học từ 1997), chi phí WF 10 : 1:

| h | R2 → B → E (ngưỡng theo chi phí) | R2 → B → E (ngưỡng 0,5) | Lợi đến từ |
|---|---|---|---|
| 1 | 353 → 268 → 239 (E−B −2,2/fold p 0,041) | 447 → 375 → 360 (E−B p 0,52) | **thêm năm học** |
| 2 | 734 → 694 → 609 (E−B p 0,24) | 889 → 879 → 730 (E−B −11,5 p 0,014) | **đặc trưng mới** |
| 3 | 1 039 → 1 029 → 853 (E−B −13,5 p 0,040) | 1 010 → 1 012 → 920 (E−B −7,1 p 0,021) | **đặc trưng mới** |

Mức 2: E − R2 không có ý nghĩa ở mọi ô (p ≥ 0,078).

---

## 4. Độ nhạy seed

Trung bình xác suất 3 seed (42 / 7 / 2026): **10:1, E** h1 367 → 233 (p 0,071), h2 728 → 583 (p 0,012),
h3 959 → 843 (p 0,091); **E − R2** ở ngưỡng theo chi phí h1 −9,7 (p 0,016), h3 −13,5 (p 0,009). Chiều kết
luận không đổi; p từng ô dao động 0,01–0,1 giữa seed. Chưa hiệu chỉnh đa so sánh (36 ô cho mức 1) — các ô có
p quanh 0,05 chỉ là gợi ý.

---

## 5. Kết luận

1. **Thay 0,5 bằng ngưỡng theo chi phí chỉ đáng làm cho mức nguy cơ 1, h = 1, khi tỉ lệ ≥ 10 : 1.** Dùng cấu
   hình E, chọn lại ngưỡng mỗi năm trên OOF quá khứ (≈ 0,02–0,04). Kỳ vọng POD ≈ 0,88, FAR ≈ 0,55, ~15 ngày
   báo/năm.
2. **h2–h3 và mức 2:** ngưỡng theo chi phí không cứu được bộ phân loại — không quảng bá.
3. **E giúp bộ phân loại.** Ở h1 chủ yếu nhờ học dài hơn; ở h2–h3 nhờ đặc trưng đất/hồ/bão/ENSO.
4. **Xác suất chưa hiệu chỉnh:** ngưỡng lý thuyết sai chiều — cần FR-M6 trước khi hiển thị xác suất.

## 6. Hạn chế

* Ít ngày dương (104 ngày mức 1 trong 13 năm, nhiều fold 0–2 ngày) ⇒ Wilcoxon ít lực; không hiệu chỉnh đa so sánh.
* Đếm theo ngày, không theo đợt (xem `FINDINGS_EVENTS_EVAL.md` cho đánh giá theo đợt).
* Ở 20 : 1 ngưỡng chọn rơi vào 10⁻⁴–10⁻² — phụ thuộc đuôi xác suất rất thấp, nhạy với seed.
* Nhãn là mức nguy cơ theo phân vị GloFAS, không phải BĐ I/II/III; ngưỡng fold (737–773) khác ngưỡng một lần chia (806).
* Tỉ lệ 10 : 1 do nhóm đặt, chưa hỏi người dùng thật.

## 7. Tái lập

```
python -m src.models.cost_threshold                                        # R2 + E, seed 42 → CSV + hình
python -m src.models.cost_threshold --seeds 42 7 2026 --out <csv> --fig <png>   # độ nhạy seed (§4)
python -m src.models.cost_threshold --sets B --out <csv> --fig <png>            # đối chứng B (§3)
python -m pytest tests/test_cost_threshold.py -q
```
