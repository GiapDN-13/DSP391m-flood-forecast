# PHÁT HIỆN — Tinh chỉnh cấu hình E: bỏ đặc trưng nghi ngờ, đổi hàm mất mát, Optuna (walk-forward 13 fold)

> 21/10/2026 · nhánh `feat/sat-latency` · code `src/eval/wf_tuning.py` · test `tests/test_wf_tuning.py` (13 test)
> Số liệu: `reports/wf_tuning_folds.csv` (fold × horizon × cấu hình), `reports/wf_tuning_summary.csv`
> (tổng hợp theo giai đoạn + valid + test), `reports/optuna_trials.csv`; hình
> `reports/figures/report/wf_tuning_en.png`. Mọi số từ lần chạy thật 21/10, ensemble 3 seed.

**Tóm tắt.**
1. Bỏ SOIL hay `rain_season_cum` **không giúp gì**; bỏ cả hai còn thua nhẹ nhưng đều ở h2–h3 ⇒ giữ 88 cột E.
2. Đổi mục tiêu L1 → **L2 trên log1p** là thay đổi DUY NHẤT cải thiện vững: ΔNSE h2 **+0,039
   [+0,020; +0,057], 11/2 fold, p 0,003**; h3 **+0,036 [+0,020; +0,051], 11/2, p 0,002**. Đúng với
   từng seed và với valid một lần chia (+0,059 / +0,053). Nhưng mức tăng gần như toàn bộ nằm ở
   2013–2022; 3 fold 2023–2025 (chế độ GloFAS hiện tại) chưa xác nhận.
3. `min_child_samples = 10`: không có tác dụng. Quantile α = 0,9: NSE giảm mạnh, đổi lấy POD cao hơn.
4. Optuna 30 trial: +0,013 NSE trên valid; walk-forward chỉ +0,011…+0,015; ngoài giai đoạn đã
   tune gần như 0 ⇒ không đáng đổi.
5. **Không biến thể nào chữa được cắt ngọn lũ** (peak_bias h2–h3 vẫn ≤ −0,65 với mọi cấu hình
   hồi quy trung tâm).

## 0. Câu hỏi và cách làm

SHAP (`docs/FINDINGS_SHAP.md`) để lại ba nghi vấn với cấu hình chính E (LightGBM, 88 cột,
`lgbm.PARAMS`): (1) độ ẩm đất ERA5-Land (SOIL = `sm_0_7`, `sm_7_28`, `sm_28_100`, `et0`) tác động
ngược chiều vật lý; (2) `rain_season_cum` không ủng hộ giả thuyết "hồ đầy"; (3) cắt ngọn lũ, nghi do
`min_child_samples = 30` + mục tiêu L1 trên log1p + ít mẫu cực trị. SPEC/PLAN còn hạng mục "Optuna
30 trial". Mỗi biến thể chỉ đổi MỘT thứ so với E:

| Biến thể | Thay đổi so với E |
|---|---|
| E-SOIL | bỏ 4 cột SOIL (84 cột) |
| E-rain_season_cum | bỏ `rain_season_cum` (87 cột) |
| E-SOIL-rain_season_cum | bỏ cả hai (83 cột) |
| E mcs10 | `min_child_samples = 10` |
| E quantile0.9 | `objective = "quantile"`, `alpha = 0.9`, vẫn trên log1p (cận trên) |
| E L2 | `objective = "regression"` (L2), vẫn trên log1p |
| E optuna | 7 siêu tham số do Optuna chọn trên VALID (§2) |

**Walk-forward** (như `walk_forward_sat.py`, import `year_fold`, `fold_threshold`, `boot_mean_ci`,
`wilcoxon_p`): fold = năm test 2013 … 2025 (13 fold), train MỞ RỘNG từ 1998-01-04 tới 28/12 năm
trước (gap 3 ngày = horizon lớn nhất), ngưỡng mức 1 mỗi fold = Q95 mùa lũ 9–12 chỉ trong train của
fold. Mọi cấu hình dùng chung tập hàng (đủ 88 cột E) ⇒ ΔNSE ghép cặp theo fold. Dự báo = trung bình
3 seed (42, 7, 2026): mỗi seed chạy một tiến trình, lưu dự báo từng seed rồi ghép ensemble (test
`test_ghep_seed_bang_chay_chung`: ghép = chạy chung, sai khác 1e−12). Mốc E ở đây **trùng E0 của
`wf_sat_folds.csv`** (NSE TB 0,761 / 0,398 / 0,170; CSI mức 1 h1 0,450).

Thống kê qua 13 fold: ΔNSE TB [CI 95 % bootstrap theo fold, 10 000 lần], số fold thắng/thua,
Wilcoxon hai phía; peak_bias (sai lệch TB trên 1 % ngày lớn nhất của năm test) lấy TB qua fold;
POD/FAR/CSI mức 1 GỘP hits/misses/false alarms qua 13 fold (105 ngày ≥ ngưỡng). **Tỷ lệ phủ** = %
ngày thực ≥ ngưỡng mức 1 mà dự báo ≥ thực.

**Không nhìn test để chọn.** Biến thể được đánh giá bằng walk-forward; Optuna chọn trên VALID. Test
≥ 2022-07-01 chỉ báo cáo (§4).

## 1. Walk-forward 2013–2025 (13 fold, ensemble 3 seed)

**Bảng 1 — ΔNSE so với E: TB [CI 95 %] · thắng/thua · p Wilcoxon**

| Cấu hình | h1 | h2 | h3 |
|---|---|---|---|
| persistence | NSE 0,536 | NSE −0,084 | NSE −0,361 |
| **E (mốc)** | NSE 0,761 | NSE 0,398 | NSE 0,170 |
| E-SOIL | +0,000 [−0,005; +0,006] · 8/5 · p 1,000 | −0,007 [−0,016; +0,001] · 5/8 · p 0,244 | −0,006 [−0,012; +0,001] · 5/8 · p 0,127 |
| E-rain_season_cum | +0,003 [−0,003; +0,010] · 9/4 · p 0,497 | −0,006 [−0,012; −0,001] · 2/11 · p 0,048 | −0,003 [−0,009; +0,002] · 6/7 · p 0,635 |
| E-SOIL-rain_season_cum | +0,004 [−0,004; +0,012] · 7/6 · p 0,497 | −0,009 [−0,016; −0,002] · 2/11 · p 0,033 | −0,008 [−0,014; −0,003] · 2/11 · p 0,006 |
| E mcs10 | +0,008 [−0,005; +0,023] · 7/6 · p 0,542 | +0,003 [−0,007; +0,014] · 5/8 · p 1,000 | −0,001 [−0,006; +0,005] · 7/6 · p 0,839 |
| E quantile0.9 | −0,116 [−0,246; −0,024] · 4/9 · p 0,027 | −0,141 [−0,350; +0,034] · 7/6 · p 0,787 | −0,174 [−0,434; +0,041] · 7/6 · p 0,787 |
| **E L2** | +0,018 [−0,003; +0,042] · 8/5 · p 0,216 | **+0,039 [+0,020; +0,057] · 11/2 · p 0,003** | **+0,036 [+0,020; +0,051] · 11/2 · p 0,002** |
| E optuna ⚠️ | +0,015 [−0,001; +0,038] · 7/6 · p 0,244 | +0,012 [−0,002; +0,027] · 8/5 · p 0,168 | +0,011 [+0,003; +0,019] · 10/3 · p 0,033 |

⚠️ 7/13 fold của "E optuna" (2016–2022) nằm trong giai đoạn valid đã dùng để chọn tham số ⇒ lạc quan (§2).

**Bảng 2 — NSE, cắt ngọn, sự kiện mức 1 (h1, gộp 13 fold), tỷ lệ phủ ngày ≥ ngưỡng**

| Cấu hình | NSE TB h1/h2/h3 | peak_bias TB h1/h2/h3 | POD/FAR/CSI mức 1 h1 | hits/miss/FA | phủ ngày ≥ ngưỡng h1/h2/h3 |
|---|---|---|---|---|---|
| persistence | 0,536 / −0,084 / −0,361 | −0,330 / −0,672 / −0,737 | 0,533 / 0,467 / 0,364 | 56/49/49 | 0,24 / 0,13 / 0,10 |
| E | 0,761 / 0,398 / 0,170 | −0,273 / −0,705 / −0,846 | 0,552 / 0,293 / 0,450 | 58/47/24 | 0,18 / 0,00 / 0,00 |
| E-SOIL | 0,761 / 0,392 / 0,165 | −0,273 / −0,711 / −0,854 | 0,571 / 0,302 / 0,458 | 60/45/26 | 0,18 / 0,00 / 0,00 |
| E-rain_season_cum | 0,764 / 0,392 / 0,167 | −0,275 / −0,712 / −0,850 | 0,552 / 0,310 / 0,443 | 58/47/26 | 0,19 / 0,00 / 0,00 |
| E-SOIL-rain_season_cum | 0,765 / 0,390 / 0,162 | −0,276 / −0,713 / −0,852 | 0,571 / 0,277 / 0,469 | 60/45/23 | 0,18 / 0,00 / 0,00 |
| E mcs10 | 0,769 / 0,401 / 0,170 | −0,271 / −0,696 / −0,845 | 0,552 / 0,284 / 0,453 | 58/47/23 | 0,17 / 0,00 / 0,00 |
| E quantile0.9 | 0,645 / 0,257 / −0,004 | −0,012 / −0,461 / −0,656 | 0,800 / 0,421 / 0,506 | 84/21/61 | 0,47 / 0,11 / 0,02 |
| E L2 | 0,779 / 0,437 / 0,206 | −0,241 / −0,652 / −0,820 | 0,571 / 0,318 / 0,451 | 60/45/28 | 0,18 / 0,04 / 0,00 |
| E optuna | 0,776 / 0,410 / 0,181 | −0,279 / −0,690 / −0,839 | 0,581 / 0,256 / 0,484 | 61/44/21 | 0,15 / 0,00 / 0,00 |

Giai đoạn con (`period` trong `wf_tuning_summary.csv`): `reanalysis_2013_2021` (9 fold),
`doi_che_do_2022`, `forecast_2023_2025` (3 fold), `ngoai_valid_optuna` (2013–2015 + 2023–2025).

### 1.1 Bỏ SOIL / `rain_season_cum`: KHÔNG cải thiện — giữ nguyên

- Bỏ riêng từng nhóm: |ΔNSE TB| ≤ 0,007 mọi horizon; chỗ duy nhất có ý nghĩa là THUA
  (E-rain_season_cum h2 −0,006, 2/11, p 0,048).
- Bỏ cả hai: **thua nhẹ nhưng nhất quán ở h2–h3** (−0,009 và −0,008; 2/11 fold; p 0,033 / 0,006).
  Valid một lần chia cùng chiều (h3 −0,011).
- ⇒ Dấu SHAP "ngược chiều vật lý" KHÔNG có nghĩa là cột vô ích: mô hình dùng chúng như biến trạng
  thái/mùa (tương tác với mưa và lưu lượng trễ); dấu SHAP biên không đo đóng góp vào sai số dự báo.
  Mức chênh ≤ 0,01 NSE (cỡ dao động giữa seed, `ablation_ext.py`) ⇒ **giữ 88 cột E**.

### 1.2 `min_child_samples = 10`: không có tác dụng vững

Chỉ seed 42 cho h2 +0,011 (p 0,04); ensemble 3 seed còn +0,003 (5/8, p 1,0); từng seed +0,011 /
−0,000 / −0,007. peak_bias gần như không đổi (h2 −0,705 → −0,696). ⇒ Lá nhỏ hơn KHÔNG chữa cắt ngọn
lũ — và là ví dụ rõ vì sao không kết luận từ một seed.

### 1.3 Quantile α = 0,9 (cận trên): đổi NSE lấy khả năng bắt lũ; lệch theo chế độ GloFAS

- NSE giảm mạnh: h1 −0,116 [−0,246; −0,024] (4/9, p 0,027); h2/h3 −0,14 / −0,17 với CI rất rộng.
- Đổi lại sự kiện mức 1: h1 POD 0,552 → **0,800**, FAR 0,293 → 0,421, CSI 0,450 → **0,506**
  (hits 58 → 84, FA 24 → 61); h2 CSI 0,103 → 0,298 (hits 11 → 53, FA 2 → 73).
- **Tỷ lệ phủ**: mọi ngày 82–83 % (dưới mức danh nghĩa 90 %); ngày thực ≥ ngưỡng mức 1 chỉ **47 %
  (h1), 11 % (h2), 2 % (h3)** ⇒ "cận trên" vẫn nằm DƯỚI hầu hết đỉnh lũ ở h2–h3 — phân vị có điều
  kiện ở vùng cực trị hiệu chỉnh rất kém (E: 18 % / 0 % / 0 %).
- **Phụ thuộc chế độ:** 2013–2021 thua nặng (−0,188 / −0,254 / −0,295; h1 0/9 fold), nhưng
  2023–2025 THẮNG cả 3 fold (+0,045 / +0,130 / +0,122) và trên test cao nhất. Tức là sau 07/2022 mô
  hình học từ GloFAS reanalysis bị **lệch thấp có hệ thống** trên GloFAS forecast archive, và dự báo
  thiên cao "vô tình" bù lại. Đây là tín hiệu cần hiệu chỉnh lệch theo chế độ, KHÔNG phải lý do chọn
  quantile (chọn theo test là sai quy trình).

### 1.4 L2 trên log1p: cải thiện VỮNG duy nhất, ở h2–h3

- h2 **+0,039 [+0,020; +0,057], 11/2, p 0,003**; h3 **+0,036 [+0,020; +0,051], 11/2, p 0,002**;
  h1 +0,018 [−0,003; +0,042], 8/5, p 0,22 (chưa có ý nghĩa).
- Vững theo TỪNG seed: h2 +0,049 / +0,030 / +0,029; h3 +0,032 / +0,032 / +0,035 (seed 42 / 7 / 2026).
  NSE mùa lũ (9–12): +0,015 / +0,048 / +0,046.
- Cắt ngọn giảm nhưng vẫn nặng: peak_bias −0,273 → −0,241 (h1), −0,705 → −0,652 (h2), −0,846 →
  −0,820 (h3). Sự kiện mức 1: h1 CSI 0,450 → 0,451 (hits 58 → 60, FA 24 → 28); h2 CSI 0,103 → 0,186
  (hits 11 → 21, FA 2 → 8); h3 vẫn 0 hit.
- Vì sao: L1 bám **trung vị** có điều kiện của log Q, L2 bám **trung bình**. Ở h2–h3 phân phối có
  điều kiện của log Q vẫn lệch phải (đa số ngày nước rút, ít ngày lên lũ) ⇒ trung bình > trung vị ⇒
  L2 bớt kéo dự báo xuống, đúng phần sai số bình phương (trên m³/s) mà NSE phạt.
- ⚠️ Mức tăng tập trung ở 2013–2021 (h1 +0,033, h2 +0,044, h3 +0,039; 7–8/9 fold, p 0,012–0,020)
  và 2022 (+0,090 / +0,081 ở h2/h3). **2023–2025 (3 fold) nhỏ và chưa kiểm định được**: h1 −0,018
  (1/2), h2 +0,004, h3 +0,010; CSI mức 1 h1 giai đoạn này 0,533 → 0,400 (hits 16 → 12).

## 2. Optuna (30 trial, chọn trên VALID)

- TPE (seed 42), 30 trial, mục tiêu = NSE TB h1–h3 trên **valid 2016-01-01 → 2022-06-30**, train
  1998-01-04 → 2015-12-28 (gap 3 ngày), 1 seed/trial, objective giữ L1 như E. Trial 0 = đúng tham số
  E. Không gian: `num_leaves` 8–128 (log), `learning_rate` 0,01–0,2 (log), `n_estimators` 150–1500
  (bước 50), `min_child_samples` 5–100 (log), `colsample_bytree` (feature_fraction) 0,4–1,
  `subsample` (bagging, freq 1) 0,5–1, `reg_lambda` 1e−3–30 (log).
- E trên valid: 0,4400 (1 seed) / **0,4443 (3 seed: 0,774 / 0,381 / 0,177)**. 20/29 trial còn lại
  vượt E (1 seed); trung vị 30 trial 0,447.
- Chấm lại top-3 bằng 3 seed (vẫn trên valid): trial 15 **0,4573**, trial 25 0,4560, trial 26 0,4534
  ⇒ chọn **trial 15** (+0,013 so với E):

| Tham số | E | Optuna (trial 15) |
|---|---|---|
| num_leaves | 31 | 127 |
| learning_rate | 0,05 | 0,0716 |
| n_estimators | 600 | 1350 |
| min_child_samples | 30 | 15 |
| colsample_bytree | 0,8 | 0,729 |
| subsample | 0,8 | 0,707 |
| reg_lambda | 1,0 | 0,044 |

- Walk-forward 2013–2025: +0,015 / +0,012 / **+0,011 [+0,003; +0,019] (10/3, p 0,033)**; CSI h1
  0,450 → 0,484 (FA 24 → 21). Nhưng **ngoài giai đoạn đã tune** (2013–2015 + 2023–2025, 6 fold):
  +0,004 / +0,001 / +0,015 [+0,003; +0,028] (5/1, p 0,094) — gần như không đổi ở h1–h2.
- Test (chỉ báo cáo): 0,750 / 0,485 / 0,214 (Δ −0,002 / +0,015 / +0,007).
- Chi phí: 127 lá × 1350 cây ⇒ thời gian fit ~6 lần E.
- **So sánh quan trọng:** chỉ đổi L1 → L2, không tune, đạt NSE valid TB **0,4780** — cao hơn MỌI
  trial Optuna (tốt nhất 0,4573). Hàm mất mát quan trọng hơn siêu tham số; nếu tune tiếp thì nên tune
  trên L2.

## 3. Đối chiếu valid một lần chia (train ≤ 2015-12-28 → valid 2016–2022/06, 3 seed)

| Cấu hình | NSE h1/h2/h3 | ΔNSE so với E h1/h2/h3 |
|---|---|---|
| E | 0,774 / 0,381 / 0,177 | — / — / — |
| E-SOIL | 0,781 / 0,383 / 0,169 | +0,007 / +0,002 / −0,008 |
| E-rain_season_cum | 0,771 / 0,379 / 0,176 | −0,004 / −0,002 / −0,002 |
| E-SOIL-rain_season_cum | 0,783 / 0,373 / 0,166 | +0,008 / −0,008 / −0,011 |
| E mcs10 | 0,780 / 0,400 / 0,176 | +0,005 / +0,019 / −0,002 |
| E quantile0.9 | 0,595 / 0,309 / 0,202 | −0,179 / −0,072 / +0,024 |
| E L2 | 0,763 / 0,440 / 0,230 | −0,011 / +0,059 / +0,053 |
| E optuna | 0,789 / 0,397 / 0,184 | +0,014 / +0,016 / +0,006 |

Cùng chiều walk-forward: L2 thắng rõ ở h2–h3, hơi thua ở h1; bỏ đặc trưng không giúp. (Giá trị
"E optuna" ở đây 0,4565 TB, khác 0,4573 khi chấm trong Optuna vì `optuna_trials.csv` lưu tham số 6
chữ số thập phân; mọi đánh giá walk-forward/valid/test đều dùng ĐÚNG bộ đã lưu.)

## 4. Test ≥ 2022-07-01 — CHỈ báo cáo, không dùng để chọn

Train 1998-01-04 → 2022-06-30, ngưỡng mức 1 = 806,0 m³/s (`risk_levels.csv`), ensemble 3 seed.

| Cấu hình | NSE h1/h2/h3 | ΔNSE so với E h1/h2/h3 | peak_bias h1/h2/h3 | POD/FAR/CSI mức 1 h1 |
|---|---|---|---|---|
| persistence | 0,542 / 0,008 / −0,198 | — / — / — | −0,361 / −0,648 / −0,683 | 0,484 / 0,516 / 0,319 |
| E | 0,753 / 0,471 / 0,207 | — / — / — | −0,453 / −0,739 / −0,876 | 0,387 / 0,143 / 0,364 |
| E-SOIL | 0,761 / 0,482 / 0,218 | +0,008 / +0,011 / +0,011 | −0,454 / −0,730 / −0,871 | 0,419 / 0,133 / 0,394 |
| E-rain_season_cum | 0,754 / 0,468 / 0,199 | +0,001 / −0,003 / −0,007 | −0,453 / −0,740 / −0,885 | 0,452 / 0,125 / 0,424 |
| E-SOIL-rain_season_cum | 0,756 / 0,480 / 0,204 | +0,004 / +0,010 / −0,003 | −0,459 / −0,732 / −0,878 | 0,419 / 0,133 / 0,394 |
| E mcs10 | 0,750 / 0,474 / 0,200 | −0,003 / +0,003 / −0,007 | −0,457 / −0,738 / −0,882 | 0,387 / 0,143 / 0,364 |
| E quantile0.9 | 0,809 / 0,574 / 0,271 | +0,056 / +0,104 / +0,065 | −0,216 / −0,526 / −0,725 | 0,742 / 0,281 / 0,575 |
| E L2 | 0,736 / 0,504 / 0,243 | −0,017 / +0,033 / +0,036 | −0,450 / −0,702 / −0,858 | 0,419 / 0,188 / 0,382 |
| E optuna | 0,750 / 0,485 / 0,214 | −0,002 / +0,015 / +0,007 | −0,451 / −0,729 / −0,874 | 0,355 / 0,154 / 0,333 |

- E ở đây (train từ 1998-01-04, ensemble 3 seed) hơi khác `ablation_ext.csv` (train từ 1997, TB NSE
  từng seed: 0,747 / 0,483 / 0,199) — không phải lỗi, do khác ngày bắt đầu và cách gộp seed.
- Quantile cao nhất trên test — cùng hiện tượng lệch thấp sau 07/2022 ở §1.3; walk-forward cho thấy
  nó thua nặng 2013–2021 ⇒ minh hoạ vì sao không được chọn theo test.
- L2 trên test: h2 +0,033, h3 +0,036, h1 −0,017 — cùng chiều walk-forward.
- E-SOIL trên test +0,008…+0,011 nhưng walk-forward −0,007 / −0,006 ⇒ một cửa sổ test không đủ.

## 5. Kết luận và đề xuất cho Report 3 (chỉ đề xuất — chưa đổi `lgbm.py` / `ablation_ext.py`)

1. **Đặc trưng: không đổi.** Giữ SOIL và `rain_season_cum`. Ghi vào Report 3: dấu SHAP ngược chiều
   không phải lý do loại cột — loại đi không cải thiện, loại cả hai còn thua nhẹ ở h2–h3.
2. **Hàm mất mát: L2 là ứng viên mạnh nhất cho h2–h3.** Bằng chứng: 13 fold (11/2, p ≤ 0,003, CI
   loại 0), từng seed, và valid một lần chia đều cùng chiều. Đề xuất cho trưởng nhóm, theo thứ tự:
   (a) **giữ E làm cấu hình chính của Report 3** (mọi số Report 3 — ablation, vệ tinh, SHAP — đều
   tính trên E) và báo "E-L2" như kết quả tinh chỉnh vững ở h2–h3, kèm cảnh báo 2023–2025;
   (b) nếu còn thời gian chạy lại `ablation_ext` / `walk_forward_sat` / SHAP: chuyển h2–h3 sang
   `objective="regression"`, giữ L1 cho h1 (h1 không có bằng chứng: +0,018 CI chạm 0, valid −0,011,
   2023–2025 −0,018). Không đổi vì số test.
3. **Optuna: không đổi.** +0,013 trên valid nhưng walk-forward ngoài giai đoạn tune gần 0 ở h1–h2,
   mô hình nặng ~6×; L2 không tune đã hơn mọi trial. Bước tiếp (nếu cần): Optuna trên L2.
4. **`min_child_samples = 10`: bỏ.** Không vững qua seed.
5. **Quantile 0,9: không làm mô hình chính.** Có thể là kênh cảnh báo phụ (POD h1 0,80, CSI 0,506)
   nhưng FAR 0,42 và phủ cực trị kém (47 % / 11 % / 2 %) ⇒ cần hiệu chỉnh (vd. conformal theo mùa lũ)
   trước khi dùng.
6. **Cắt ngọn lũ chưa được giải quyết** bằng tham số hay hàm mất mát (peak_bias h2 tốt nhất −0,65).
   Tín hiệu mới: lệch thấp có hệ thống sau 07/2022 (quantile thắng 3/3 fold 2023–2025) ⇒ hướng tiếp
   là hiệu chỉnh lệch theo chế độ GloFAS và/hoặc hiệu chỉnh chuyển ngược log (smearing), không phải
   thêm tune.

## 6. Giới hạn

- 13 fold; giai đoạn GloFAS forecast archive (2023–2025) chỉ 3 fold (p hai phía nhỏ nhất 0,25) ⇒ mọi
  kết luận về chế độ hiện tại đều sơ bộ.
- Optuna: 30 trial, 1 seed/trial (chấm lại top-3 bằng 3 seed); valid 2016–2022/06 trùng 7 fold
  walk-forward ⇒ các fold đó lạc quan cho "E optuna"; tham số lưu 6 chữ số thập phân.
- peak_bias tính trên 1 % ngày lớn nhất mỗi năm (~4 ngày) ⇒ nhiễu, chỉ dùng TB qua fold.
- Quantile chỉ thử α = 0,9; tỷ lệ phủ ngày lũ dựa trên 105 ngày ≥ ngưỡng gộp 13 fold.
- LightGBM chạy `n_jobs = 2` (2 tiến trình song song, tổng 4 luồng) — chỉ đổi số luồng.

## Tái lập

```bash
export PYTHONIOENCODING=utf-8
python -m src.eval.wf_tuning --stage optuna --n-trials 30 --top-k 3 --n-jobs 2     # ~36 phút
for s in 42 7 2026; do
  python -m src.eval.wf_tuning --stage wf --seeds $s --tag s$s --n-jobs 2 --configs E E-SOIL \
    E-rain_season_cum E-SOIL-rain_season_cum "E mcs10" "E quantile0.9" "E L2" "E optuna"
done                                                    # ~17–22 phút/seed cho 7 cấu hình + ~15–20 phút "E optuna"
python -m src.eval.wf_tuning --stage valid --n-jobs 2   # ~7 phút
python -m src.eval.wf_tuning --stage test --n-jobs 2    # ~8 phút
python -m src.eval.wf_tuning --stage summary            # gộp → 2 CSV + hình, không fit
pytest tests/test_wf_tuning.py && ruff check src/eval/wf_tuning.py tests/test_wf_tuning.py
```
File trung gian (dự báo từng seed) ở `.cache/wf_tuning/` (không commit).
