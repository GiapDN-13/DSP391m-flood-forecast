# PHÁT HIỆN — Đánh giá theo đợt lũ (FR-V5) và đối chứng GloFAS thô (AC-3)

*21/10/2026 · nhánh `feat/sat-latency` · `src/eval/event_eval.py`*

## 0. Tóm tắt

- Tính theo **đợt** (không theo ngày), LightGBM cấu hình E bắt được đợt lũ mức 1 ở **h = 1 ngang persistence** (walk-forward 2013–2025: 65 % so với 63 % trên 43 đợt), nhưng ở **h = 2–3 thì kém hẳn** (14 % / 0 % so với 33 % / 16 %).
- Nguyên nhân: **cắt ngọn đỉnh** — đỉnh dự báo chỉ bằng 0,80 / 0,44 / 0,28 đỉnh thật (trung vị, h1/h2/h3), nên dự báo hiếm khi chạm ngưỡng ở h ≥ 2.
- Điểm E hơn persistence: **có thời gian báo trước thật** (trung vị +1 ngày ở h1; 15/28 đợt bắt được có báo trước ≥ 1 ngày), **gần như không báo nhầm** (0 đợt nhầm ở h2–h3 so với 16 và 29 của persistence), và **đúng thời điểm** (lệch đỉnh trung vị 0 ngày ở h1). Persistence có đỉnh đúng nhưng **luôn trễ đúng h ngày** và không bao giờ báo trước được.
- **Học lại mỗi năm giúp nhiều:** cùng 9 đợt 2023–2025, mô hình học một lần (≤ 2022-06) bắt 4/9 ở h1, mô hình học lại theo năm bắt 8/9.
- ⇒ Dùng thẳng "Q̂ ≥ ngưỡng" làm luật cảnh báo **không ổn ở h ≥ 2**. Cần ngưỡng cảnh báo hiệu chỉnh riêng theo horizon (hoặc bộ phân loại / mục tiêu phân vị cao) — xem §6 và `FINDINGS_COST_THRESHOLD.md`.
- **Đối chứng GloFAS thô (AC-3) chưa làm được:** nhật ký dự báo (16/09–20/10/2026) không có cặp nào trùng với lưu lượng quan trắc (panel dừng 31/08/2026) và không có dự báo LightGBM cho các ngày đó (§5).

## 1. Định nghĩa

| Khái niệm | Định nghĩa |
|---|---|
| Đợt lũ | Ngày có GloFAS `discharge` ≥ ngưỡng mức 1; các ngày vượt ngưỡng cùng một đợt nếu giữa chúng có ≤ 2 ngày dưới ngưỡng. Đỉnh = ngày Q lớn nhất trong đợt |
| Dự báo cho ngày v ở horizon h | Bản phát ngày t = v − h (LightGBM E: trung bình 3 seed; persistence: Q̂(v) = Q(v − h)) |
| Bắt được | ≥ 1 ngày trong [bắt đầu, kết thúc] có dự báo ≥ ngưỡng. `caught_win` nới thêm ±1 ngày (FR-V5), chỉ để tham khảo |
| Tỷ số đỉnh | max dự báo trong [bắt đầu − 1, kết thúc + h] / max thật |
| Lệch thời điểm đỉnh | ngày đạt max dự báo − ngày đỉnh thật (dương = muộn) |
| Thời gian báo trước | ngày bắt đầu đợt − ngày **phát** của dự báo đầu tiên vượt ngưỡng trong đợt ±1 ngày. ≤ 0 = không báo trước |
| Không lấn đợt kề | Chỉ xét dự báo phát sau khi đợt trước kết thúc và có ngày hiệu lực trước khi đợt sau bắt đầu |
| Đợt báo nhầm | Cụm ngày dự báo ≥ ngưỡng (gộp cùng quy tắc) không chạm cửa sổ ±1 ngày của đợt thật nào |

**Hai phạm vi:**
- **(a)** Split chính: E học trên ≤ 2022-06-30, test ≥ 2022-07-01, ngưỡng 806 m³/s (`risk_levels.csv`).
- **(b)** Walk-forward theo năm 2013–2025: dùng `year_fold` / `fold_threshold` của `walk_forward_sat.py`, nhóm `ext`, cấu hình E0 = E, cùng mặt nạ hàng. Ngưỡng mỗi fold = Q95 lưu lượng tháng 9–12 trong cửa sổ train của fold (733–769 m³/s). Cùng các dự báo đó được chấm lại ở ngưỡng cố định 806 để đối chiếu.

**Kiểm tái lập:** NSE từng seed ở (a) trùng `ablation_ext.csv` (Δ = 0). Ở (b), 39 cặp fold×h lệch |ΔNSE| tối đa 5·10⁻⁶ so với `wf_sat_folds.csv`, n_test khớp 39/39.

## 2. Kết quả (a) — tập test ≥ 2022-07-01, 13 đợt

| h | E bắt | Persistence bắt | E: tỷ số đỉnh, trung vị [IQR] | E: lệch đỉnh, trung vị (\|·\|) | Persistence: lệch đỉnh | E: báo trước, trung vị (số đợt > 0) | Đợt nhầm E / P |
|---|---|---|---|---|---|---|---|
| 1 | 6/13 (46 %) | 9/13 (69 %) | 0,57 [0,53–0,64] | 0 (0) | +1 | +1 ngày (4/6) | 0 / 0 |
| 2 | 1/13 (8 %) | 3/13 (23 %) | 0,38 [0,29–0,44] | 0 (0) | +2 | −4 (0/1) | 0 / 4 |
| 3 | 0/13 | 3/13 (23 %) | 0,20 [0,15–0,32] | +1 (2) | +3 | — | 0 / 10 |

- Persistence không bắt được đợt chỉ 1 ngày ở h1 (4 đợt). E bắt được 1 trong số đó (16/10/2022, 1 967 m³/s, báo trước 1 ngày).
- E bỏ lỡ 7 đợt ở h1, phần lớn là đợt ngắn 1–2 ngày, có tỷ số đỉnh 0,37–0,85.
- Với 7 đợt có đỉnh ≥ 1 275 m³/s (mức 2): E bắt 6/7, 1/7, 0/7 (h1/h2/h3); persistence bắt 6/7, 3/7, 3/7.

## 3. Kết quả (b) — walk-forward 2013–2025 (ngưỡng theo fold), 43 đợt

| h | E bắt | Persistence bắt | E: tỷ số đỉnh [IQR] | E: lệch đỉnh (\|·\|) | E: báo trước (số đợt > 0) | Đợt nhầm E / P |
|---|---|---|---|---|---|---|
| 1 | 28/43 (65 %) | 27/43 (63 %) | 0,80 [0,66–0,96] | 0 (1) | +1 (15/28) | 8 / 0 |
| 2 | 6/43 (14 %) | 14/43 (33 %) | 0,44 [0,33–0,55] | +1 (1) | +0,5 (3/6) | 0 / 16 |
| 3 | 0/43 | 7/43 (16 %) | 0,28 [0,20–0,35] | +2 (2) | — | 0 / 29 |

**Theo giai đoạn (tỷ lệ bắt ở h1, E so với persistence):** 2013–2021: 17/28 so với 17/28 · 2022: 3/5 so với 2/5 · 2023–2025: 8/10 so với 8/10.

**Ở ngưỡng cố định 806 (40 đợt):** E bắt 28/40, 5/40, 0/40; persistence bắt 27/40, 14/40, 7/40.

**Với 22 đợt có đỉnh ≥ 1 275 m³/s:** E bắt 21/22, 5/22, 0/22, tỷ số đỉnh trung vị 0,71 / 0,36 / 0,21; persistence bắt 20/22, 13/22, 7/22.

**Học lại theo năm:** cùng 9 đợt 2023–2025 ở ngưỡng 806, mô hình (a) học một lần bắt 4/9 ở h1; walk-forward học lại mỗi năm (có dữ liệu sau mốc gãy 07/2022) bắt 8/9, tỷ số đỉnh trung vị 0,58 → 0,66.

## 4. Đối chiếu tin báo (`flood_events.csv`, 12 trận từ 2013)

- **GloFAS bỏ lỡ lũ thật:** 2023-11 (4,34 m, mức BĐ3) GloFAS chỉ 584 m³/s; 2024-11 (3,10 m, đỉnh là số dự báo) GloFAS 600 m³/s — cả hai không thành đợt. Mô hình học theo GloFAS nên **không thể** cảnh báo hai trận này — giới hạn của nhãn, không phải của mô hình.
- **Ngược lại:** 2020-09 (0,9 m, dưới BĐ1) lại là một đợt GloFAS (970 m³/s).
- **Trận gộp:** 2020-10a/b/c (3 trận theo tin báo) gộp thành 1 đợt GloFAS 08–20/10 với ngưỡng fold; ở ngưỡng 806 thì 10c tách riêng.
- **Trên các trận khớp tin báo (walk-forward, 7 đợt GloFAS):** E bắt 5/7, 4/7, 0/7 (h1/h2/h3); persistence 5/7, 5/7, 4/7. Lũ lịch sử 2025-10 (5,05 m): E bắt ở h1–h2, báo trước 1 ngày, đỉnh dự báo chỉ 0,58–0,66 đỉnh thật ở h1. 2025-11 (đợt 1 ngày, 846 m³/s): cả hai đều bỏ lỡ.
- Trong 13 đợt GloFAS của tập test, 11 đợt không có trong danh mục tin báo — danh mục chưa đầy đủ, không có nghĩa là các đợt đó không có thật.

## 5. Đối chứng GloFAS thô (AC-3) — chưa đủ dữ liệu

**Hiện trạng:** `reports/forecast_log/` có 35 bản phát (15/09–20/10, thiếu 20/09); bản 15/09 ở ô lưới cũ nên loại, còn 34 bản. Mỗi bản có GloFAS t+0 … t+6 nhưng **không có cột LightGBM** (chưa có `models/`, `predict_daily.py` chỉ ghi GloFAS). Lưu lượng quan trắc dừng ở 2026-08-31 ⇒ **0 cặp** (dự báo, thật).

**Phép đo thay thế, KHÔNG độc lập** ("thật" = t+0 của bản phát đúng ngày đích — cùng hệ thống GloFAS, có lợi cho GloFAS; chủ yếu nước thấp, max 834,6 m³/s ngày 09/10/2026):

| h | n | GloFAS thô: NSE / MAE (m³/s) / peak_bias | Persistence: NSE / MAE |
|---|---|---|---|
| 1 | 32 | 0,916 / 25,4 / −0,26 | 0,263 / 84,9 |
| 2 | 31 | 0,819 / 38,2 / −0,39 | −0,428 / 114,1 |
| 3 | 30 | 0,845 / 40,7 / −0,14 | −0,695 / 147,9 |

n rất nhỏ, khác giai đoạn và khác định nghĩa "thật" ⇒ **không được** đặt cạnh NSE của LightGBM.

**Cần để làm đúng:** (1) tải lưu lượng lưu trữ Open-Meteo cho ô (16.45, 107.5), 16/09–23/10/2026, kiểm giá trị lưu trữ có bằng t+0 không; (2) kéo dài mưa, đất, khí tượng, bão, ONI tới ≥ 20/10 rồi dựng lại `daily_panel_ext`; (3) chạy E cho các ngày phát 16/09–20/10, ghép theo (ngày đích, h); (4) cho `predict_daily` lưu cột LightGBM mỗi sáng, chờ hết mùa lũ (12/2026) để có vài đợt.

## 6. Hạn chế và việc tiếp

- **Ít đợt:** 13 đợt test, 43 đợt walk-forward — 1 đợt ≈ 8 điểm % trên tập test.
- **Nhãn là GloFAS, không phải mực nước thật:** xem §4 (2023-11, 2024-11).
- **Có thể nhạy với quy tắc gộp đợt:** `--max-gap` để thử 0/1 (chưa chạy).
- **Việc tiếp:** hiệu chỉnh ngưỡng cảnh báo theo horizon trên train/valid, hoặc objective phân vị / bộ phân loại cho h2–h3, rồi chấm lại bằng `event_eval.py`. Ưu tiên học lại mô hình định kỳ khi chạy thật.

## 7. Tái lập

    python -m src.eval.event_eval              # ~10 phút, 126 lần fit, n_jobs = 4
    python -m src.eval.event_eval --from-cache # chấm lại từ .cache/event_eval_preds.parquet
    python -m src.eval.event_eval --plot-only
    python -m pytest tests/test_event_eval.py -q   # 14 passed

Đầu ra: `reports/event_eval_events.csv`, `event_eval_summary.csv`, `event_eval_news.csv`, `event_eval_glofas_raw.csv`, `reports/figures/report/event_eval_en.png`.
