# PHÁT HIỆN — Thử giảm cắt ngọn lũ của mô hình chính (Report 4, 02/11/2026)

Chạy lại: `python -m src.eval.wf_peak --stage run` · `--stage lstm` · `--stage summary`
Số: `reports/wf_peak_summary.csv` (tổng hợp) · `reports/wf_peak_folds.csv` (từng fold)

---

## 1. Câu hỏi và tiêu chí đặt TRƯỚC khi chạy

Mô hình chính E dự báo thấp đỉnh: peak_bias −0,45 / −0,71 / −0,86 trên test, h3 NSE
0,236 < ngưỡng AC-1 0,25. Report 3 đã thử quantile, `min_child_samples`, L2, Optuna
(`FINDINGS_TUNING.md`). Ở đây thử ba hướng khác, chấm bằng walk-forward 13 fold
2013–2025 (train mở rộng từ 1998-01-04, gap 3 ngày, ngưỡng mức 1 mỗi fold chỉ từ train,
3 seed, giống hệt `wf_tuning`):

| Mã | Biến thể |
|---|---|
| B1 | trọng số mẫu nhấn đỉnh khi học `w = 1 + α·max(0, y/ngưỡng1 − 1)`; α = 1, 3 (thêm 5, 10 sau khi xem α = 1, 3) |
| B2 | hiệu chỉnh lệch sau dự báo: isotonic log1p(ŷ) → log1p(y) fit trên dự báo ngoài mẫu của **các fold năm < Y** (fold 2005–2012 chạy thêm chỉ để có dữ liệu hiệu chỉnh); `iso_hi` chỉ áp cho ŷ ≥ ngưỡng1/2 |
| B3 | trung bình 50/50 E và LSTM L30 MSE (`dl_lstm`, cùng fold, 3 seed); trọng số đặt trước, không tinh chỉnh |

**Tiêu chí nhận:** ΔNSE h2/h3 > 0 với Wilcoxon p < 0,05 **và** ΔNSE h1 ≥ −0,01; hoặc
peak_bias / số ngày lũ bắt được tăng rõ mà NSE không giảm quá 0,01.

Mốc E tái lập đúng số Report 3: **0,761 / 0,437 / 0,206** (LightGBM 1 luồng).

## 2. Kết quả (13 fold 2013–2025; ΔNSE so với E, CI 95 % bootstrap theo fold)

| Biến thể | h1 ΔNSE (thắng/thua, p) | h2 ΔNSE (p) | h3 ΔNSE (p) | POD h1 |
|---|---|---|---|---|
| E (mốc) | 0,761 | 0,437 | 0,206 | 0,55 |
| B1 α=1 | +0,007 (8/5, p 0,59) | −0,001 (0,89) | −0,003 (0,54) | 0,59 |
| B1 α=3 | +0,011 [0,000; 0,024] (9/4, p 0,13) | +0,012 (0,22) | +0,001 (0,89) | 0,62 |
| B1 α=5 | +0,008 (0,54) | +0,005 (0,74) | −0,007 (0,34) | 0,62 |
| B1 α=10 | −0,010 (0,46) | +0,001 (1,00) | −0,008 (0,34) | 0,53 |
| B2 iso | −0,040 (0,64) | −0,008 (0,50) | **−0,027 (12 thua, p 0,001)** | 0,57 |
| B2 iso_hi | −0,042 (0,59) | −0,005 (0,74) | −0,013 (0,067) | 0,57 |
| B3 E+LSTM | **+0,029 [0,006; 0,056] (10/3, p 0,048)** | −0,022 [−0,044; −0,001] (0,068) | **−0,023 [−0,039; −0,007] (p 0,021)** | 0,57 |

## 3. Kết luận

1. **Không biến thể nào đạt tiêu chí** ⇒ **giữ E làm mô hình chính, đóng băng 02/11/2026.**
   h3 vẫn 0,21 (walk-forward) / 0,236 (test) — dưới AC-1 0,25, báo cáo trung thực.
2. **Trọng số đỉnh (B1)**: α = 3 nhích h1/h2 (+0,011/+0,012) và POD h1 0,55 → 0,62,
   peak_bias h1 −0,27 → −0,21, nhưng không có ý nghĩa thống kê, không đơn điệu theo α
   (α = 5, 10 kém hơn) và α được chọn SAU khi xem ⇒ không nhận. Cắt ngọn ở h2–h3
   (peak_bias −0,65 / −0,82) gần như không đổi: vấn đề không nằm ở việc mô hình "coi
   nhẹ" mẫu đỉnh mà ở thông tin đầu vào — 2–3 ngày trước đỉnh, mưa gây lũ chưa rơi.
3. **Hiệu chỉnh isotonic (B2) làm hại**: quan hệ ŷ → y trên các năm trước không ổn
   định giữa các năm (đổi chế độ GloFAS 07/2022, năm lũ lớn hiếm) ⇒ hiệu chỉnh đẩy
   dự báo sai hướng ở năm bình thường.
4. **Ghép LSTM (B3) giúp h1, hại h2–h3**: h1 +0,029 (p 0,048, 10/3 fold) là cải thiện
   có ý nghĩa duy nhất của cả đợt thử — đúng với Report 4 (LSTM có POD/CSI h1 tốt hơn).
   Nhưng h2–h3 thua ở 11/13 fold. Không đổi mô hình chính vì (a) tiêu chí đặt cho
   h2–h3, (b) chỉ dùng cho h1 là chọn sau khi xem, (c) job hằng ngày phải chạy thêm
   torch. Ghi làm **hướng tiếp theo**: ghép theo horizon, kiểm trên dữ liệu mới.
5. Chặn đúng giới hạn: dự báo thấp đỉnh ở h2–h3 cần **mưa dự báo tốt** (kịch bản B,
   chưa có kho lưu trữ đúng nghĩa — `FINDINGS_MODEL.md` §4b) hoặc số liệu xả hồ đầy đủ,
   không chữa được bằng hàm mất mát / hậu xử lý.

## 4. Phân tán (Report 4)

141 + 78 lượt LightGBM (cấu hình × năm × seed) chạy song song theo tác vụ: pool 6–7
tiến trình 9,3 + 5,8 phút; 39 lượt LSTM 6,3 phút (4 tiến trình × 2 luồng). Cùng hàm
`wf_peak.run_job` chạy trên Spark (`src/distributed/spark_walkforward.py`) — số đo và
đối chiếu trong `reports/spark/wf_bench.csv`.
