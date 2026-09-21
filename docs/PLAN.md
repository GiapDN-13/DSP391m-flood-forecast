# KẾ HOẠCH 9 TUẦN — DSP391m

**Khung thời gian:** 15/09/2026 → 16/11/2026 · 60 sessions nén vào **9 tuần ≈ 6–7 session/tuần**.

| Tuần | Session | Ngày |
|---|---|---|
| W1 | S1–7 | 15/09 – 21/09 |
| W2 | S8–13 | 22/09 – 28/09 |
| W3 | S14–20 | 29/09 – 05/10 |
| W4 | S21–27 | 06/10 – 12/10 |
| W5 | S28–33 | 13/10 – 19/10 |
| W6 | S34–40 | 20/10 – 26/10 |
| W7 | S41–47 | 27/10 – 02/11 |
| W8 | S48–53 | 03/11 – 09/11 |
| W9 | S54–60 | 10/11 – 16/11 |

> ⚠️ **Việc đầu tiên phải làm:** mở LMS, lấy **ngày nộp thật của 4 report**, thay vào bảng dưới. Bảng này suy ra từ session number, **chưa phải ngày chính thức**.

| Mốc | Session | Tuần | Ngày suy ra | **Deadline nội bộ** | % |
|---|---|---|---|---|---|
| Nháp Report 1 | S9 | W2 | ~24/09 | 23/09 | – |
| **Report 1** | S12 | W2 | ~28/09 | **26/09** | 10 % |
| **Report 2** | S26 | W4 | ~12/10 | **09/10** | 20 % |
| **Report 3** | S49 | W8 | ~04/11 | **02/11** | 40 % |
| **Report 4** | S57 | W9 | ~13/11 | **10/11** | 10 % |
| Thi vấn đáp | S58–60 | W9 | 13–16/11 | – | 20 % |

---

> 📋 **Dự án phải làm được gì** thì xem [`docs/SPEC.md`](SPEC.md) (FR / NFR / ngưỡng nghiệm thu). File này chỉ trả lời **khi nào và ai làm**.

## 🔪 Scope đã cắt sẵn — quyết định ngay từ đầu, không phải phương án dự phòng

9 tuần không đủ cho kế hoạch gốc. Những thứ sau **bỏ ngay từ W1**, không bàn lại:

| Cắt gì | Lý do | Ảnh hưởng điểm |
|---|---|---|
| **Mưa ERA5 chỉ crawl 2010–2026** (không phải 1940/1984) | Tiết kiệm ~2 tuần crawl. 16 năm × mùa lũ vẫn đủ mẫu huấn luyện | Không — chỉ cần nêu trong Limitations |
| **Lưới ~50 điểm** thay vì 200 | Giảm 4× thời gian crawl và dung lượng | Không |
| **Discharge yêu cầu 1984–2026, thực có 1997–2026** | Chuỗi ngày, 1 request/điểm — rẻ. Cần cho phân vị & sự kiện lũ cũ | Giữ được return period, nhưng trên 29 năm — `FINDINGS_EVENTS.md` §3 |
| **Bỏ NASA POWER** | Kế hoạch gốc đã ghi "tuỳ chọn" | Không |
| **Bỏ LSTM/TFT** khỏi phạm vi chính | LightGBM là mô hình chính; LSTM chỉ làm nếu W8 còn dư thời gian | Nhỏ — cần giải thích lựa chọn trong Methodology |
| **Bỏ PySpark** | DuckDB/Polars thừa sức với quy mô đã cắt | Không |
| **Optuna 30 trial** thay vì 100 | Lợi ích giảm dần rất nhanh | Không |
| **Dashboard 2 trang** (bản đồ + biểu đồ dự báo) | Đủ để demo và chấm | Không |
| **Mock exam 2 lần** thay vì 3 | Còn W6 và W9 | Không |

**Thứ KHÔNG được cắt:** baseline GloFAS thô · walk-forward đúng cách · ánh xạ ngưỡng BĐ · 2 kịch bản A/B · bộ metric sự kiện hiếm · SHAP. Đây là phần ăn điểm của Report 3 (40 %).

---

## W1 · S1–7 · 15/09 – 21/09 — Khởi động + crawl bắt đầu NGAY

Nguyên tắc tuần này: **không có tuần "chuẩn bị"**. Crawl phải chạy từ ngày 2.

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Push repo lên GitHub, branch protection, mời D + H | D + H clone được |
| **G** | Chạy `scripts/bootstrap_github.ps1`, dựng Project board, **tạo issue cho từng FR ưu tiên M** | Board có issue W1–W2 |
| **G** | ✅ *`src/ingest/openmeteo_flood.py` đã viết & chạy được (có cache + retry + quét lưới).* Còn lại: chạy chuỗi đầy đủ trên ô đã chốt | `reports/figures/w1_discharge_*.png` |
| **G** | ✅ *Đã quét lần 1 (15/09): toạ độ kế hoạch gốc (16.46, 107.59) **sai ô lưới** — q_mean 5,7 m³/s so với 308 m³/s tại (16.56, 107.59).* Còn lại: **quét tinh step 0.05° quanh ô mới + đối chiếu bản đồ OSM + quét trạm Phú Ốc** | `data/external/grid_candidates.csv` |
| **G** | Khởi động crawl discharge toàn bộ điểm (chạy nền) | Chạy được qua đêm |
| **D** | `make setup`, chạy lại script của G, thử 1 toạ độ sông Bồ | `notebooks/01_first_call.ipynb` |
| **D** | Đọc doc Open-Meteo Archive + **Historical Forecast API**, ước lượng thời gian crawl 50 điểm × 2010–2026 | `docs/API_NOTES.md` |
| **H** | **Tra Phụ lục QĐ 05/2020/QĐ-TTg**, xác nhận mực nước BĐ I/II/III cho Kim Long & Phú Ốc | `THRESHOLDS.md` §2 đã tick |
| **H** | ~~Công văn xin số liệu Đài KTTV~~ — **đã loại**. Thay bằng: **bắt đầu thu `flood_events.csv`** (giờ là đường duy nhất để quy đổi ngưỡng) | ≥ 5 sự kiện có nguồn |
| **H** | Zotero group + tìm 6 bài (2 bài về **post-processing dự báo dòng chảy**) | 6 entry |
| **Cả 3** | Chốt tên đề tài + **email giảng viên báo team 3 người** | Đã gửi |
| **Cả 3** | Lấy ngày nộp thật từ LMS, cập nhật bảng mốc ở trên | Bảng đã sửa |

## W2 · S8–13 · 22/09 – 28/09 — 🎯 Report 1 + crawl chạy nền

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Crawl mưa ERA5 2010–2026, ~50 điểm, theo lô + resume | ≥ 70 % xong |
| **G** | Viết Methodology + **mục Contribution** (`RESEARCH_DESIGN.md` §1) cho Report 1 | Draft |
| **G** | Sơ đồ pipeline | `reports/figures/pipeline.png` |
| **D** | `src/etl/clean.py` + 5 test trong `tests/test_clean.py` | `pytest` xanh |
| **D** | Viết Timeline + Risks cho Report 1 | Draft |
| **H** | Tóm tắt 6 bài, ghép thành literature review có mạch | `docs/lit/` đủ 6 file |
| **H** | Problem statement + Objectives + Research questions | Draft |
| **H** | **Gộp + format Report 1**, mục lục, citation | `reports/report1/Report1_v1.docx` |
| **Cả 3** | Review chéo → **nộp Report 1 ngày 26/09** | ✅ |

## W3 · S14–20 · 29/09 – 05/10 — Dữ liệu xong + ngưỡng BĐ

🔴 **Tuần quyết định cả dự án.** Hết tuần này không có `daily_panel.parquet` thì mọi thứ phía sau đổ.

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Crawl xong 100 % + **backup Google Drive / HF Datasets ngay** | Link trong README |
| **G** | Gộp `data/processed/daily_panel.parquet` (daily, mưa theo tiểu lưu vực + discharge + GloFAS forecast) | File chạy được |
| **G** | Chốt `docs/DATA_SPLITS.md`: mốc 07/2022, walk-forward, cách gộp không gian | Đã điền |
| **G** | `src/features/thresholds.py` — fit `H = α·ln(Q)+β`, nghịch đảo, bootstrap | Có test |
| **H** | **Hoàn tất `data/external/flood_events.csv` ≥ 15 sự kiện có nguồn** | CSV đủ cột |
| **G** | Chạy ánh xạ H→Q, điền `THRESHOLDS.md` §4, kiểm chứng 1999/2020/2023 | Bảng đã điền |
| **D** | Resample mưa giờ→ngày, mưa tích luỹ 1/3/5/7 ngày, API index | Cột có trong panel |
| **D** | Kiểm tra chất lượng: ngày thiếu, giá trị âm, outlier | `notebooks/02_data_quality.ipynb` |
| **H** | Data dictionary + mục pháp lý/bản quyền (CC BY 4.0) | `docs/DATA_DICTIONARY.md` |

## W4 · S21–27 · 06/10 – 12/10 — 🎯 Report 2 (EDA)

| Ai | Việc | Xong khi |
|---|---|---|
| **D** | EDA đủ 8 mục theo `docs/EDA_CHECKLIST.md` — trọng tâm **tương quan mưa–lưu lượng theo lag 0–7 ngày** | `notebooks/03_eda.ipynb` |
| **D** | Đối chiếu 3 đợt lũ lịch sử 1999 / 2020 / 2023 | 3 hình |
| **G** | Bản đồ mưa lưu vực + phân tích extreme value / return period | `reports/figures/map_rain.png` |
| **H** | Biên tập insight EDA thành văn xuôi; caption + đánh số hình/bảng | Draft |
| **H** | **Gộp + format Report 2** (Data Collection + Cleaning + EDA) | `Report2_v1.docx` |
| **G + D** | Review chéo — **mỗi hình phải kèm 1 insight** | Xong |
| **Cả 3** | **Nộp Report 2 ngày 09/10** | ✅ |
| **G** | Song song: khung `src/models/` + hàm walk-forward split | Code chạy |

## W5 · S28–33 · 13/10 – 19/10 — Baseline + mô hình chính

| Ai | Việc | Xong khi |
|---|---|---|
| **D** | 4 baseline: persistence · seasonal naive · ARIMA · **GloFAS thô** | Bảng RMSE/MAE/NSE |
| **G** | LightGBM hồi quy, horizon 1/2/3, **có GloFAS forecast làm feature** | Model v1 |
| **G** | 3 classifier lồng nhau: `≥BĐ I`, `≥BĐ II`, `≥BĐ III`, `scale_pos_weight` | Model v1 |
| **G** | Crawl mưa dự báo quá khứ (Historical Forecast API) cho tập test → phục vụ kịch bản B | Dữ liệu sẵn sàng |
| **H** | Viết Methodology Report 3 (mô tả từng mô hình bằng lời) | Draft |
| **H** | Cập nhật `docs/EXPLAINER.md` sau handoff | 2–3 trang |

## W6 · S34–40 · 20/10 – 26/10 — Đánh giá 2 kịch bản + tuning

| Ai | Việc | Xong khi |
|---|---|---|
| **D** | Walk-forward validation, RMSE/MAE/NSE/KGE — **cả kịch bản A và B** | Bảng §2.4 `RESEARCH_DESIGN.md` |
| **D** | Metric sự kiện hiếm: POD / FAR / CSI / F1 / PR-AUC + đánh giá theo đợt lũ | Bảng |
| **G** | Optuna 30 trial; chọn ngưỡng quyết định theo chi phí 10:1 + độ nhạy 5:1, 20:1 | `reports/experiments.csv` |
| **G** | Error analysis: sai ở đâu, có cắt ngọn đỉnh lũ không | Notebook + hình |
| **H** | Viết mục Evaluation Report 3 | Draft |
| **Cả 3** | 🔁 **Mock exam lần 1** | Ghi điểm |

## W7 · S41–47 · 27/10 – 02/11 — SHAP + dashboard + viết Report 3

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | SHAP; kiểm tra feature quan trọng có hợp lý thuỷ văn không | `reports/figures/shap_*.png` |
| **G** | Viết Model Development + Interpretation | Draft |
| **D** | Dashboard 2 trang: bản đồ nguy cơ (tiểu lưu vực/xã) + biểu đồ dự báo 1–3 ngày | `dashboard/app.py` chạy |
| **D** | Ablation bỏ từng nhóm feature | Bảng |
| **D** | Conclusion & Recommendation + Limitations | Draft |
| **H** | **Gộp + format Report 3** — 40 % điểm, quan trọng nhất | `Report3_v1.docx` |

## W8 · S48–53 · 03/11 – 09/11 — 🎯 Report 3 + deploy

| Ai | Việc | Xong khi |
|---|---|---|
| **Cả 3** | Review chéo Report 3 **2 vòng** | Xong |
| **H** | Checklist nộp, citation, kiểm tra trùng lặp | Tick đủ |
| **Cả 3** | **Nộp Report 3 ngày 02/11** | ✅ |
| **G** | Freeze model, tag `v1.0`; bật GitHub Actions cron + deploy Streamlit Cloud | Link công khai |
| **G** | `docs/RUNBOOK.md` + README reproduce từ số 0 | Người lạ chạy được |
| **D** | Quay **video demo backup** phòng mất mạng | Video xong |
| **H** | Bắt đầu slide 30 phút + script nói từng người | Outline |
| *(nếu dư)* | **G** | LSTM so sánh — chỉ làm nếu mọi việc trên đã xong | Bảng so sánh |

## W9 · S54–60 · 10/11 – 16/11 — 🎯 Report 4 + thi

| Ai | Việc | Xong khi |
|---|---|---|
| **H** | Gộp R1+R2+R3 → **Report 4**, sửa theo toàn bộ feedback | `Final_v1.docx` |
| **G** | Kiểm tra nhất quán số liệu giữa 3 report | Bảng đối chiếu |
| **Cả 3** | **Nộp Report 4 ngày 10/11** | ✅ |
| **H** | Hoàn thiện slide + script | Xong |
| **Cả 3** | Luyện thuyết trình **3 lần**, bấm giờ | Xong |
| **Cả 3** | 🔁 **Mock exam lần 2** — hỏi xoáy phần KHÔNG phải mình làm | Xong |
| **Cả 3** | Thi vấn đáp S58–60 | ✅ |

---

## Đường găng

```
W1  chốt ô lưới GloFAS + khởi động crawl
 └─> W3  daily_panel.parquet + ngưỡng BĐ      ← ĐIỂM CHẾT, không được trễ
       └─> W4  EDA (Report 2)
             └─> W5–W6  model + đánh giá
                   └─> W8  Report 3 (40 %)
```

Hai việc chạy song song trên đường găng phải xong **cùng lúc ở W3**:
- **G**: crawl → panel
- **H**: `flood_events.csv` → nếu thiếu, G không chạy được ánh xạ ngưỡng

## Chốt kiểm tra bắt buộc

| Khi nào | Điều kiện phải đạt | Không đạt thì làm gì |
|---|---|---|
| **Hết W1** | Đã chốt ô lưới + crawl discharge chạy | Dừng mọi việc khác, cả team tập trung vào crawl |
| **Hết W3** | Có `daily_panel.parquet` + bảng ngưỡng BĐ | Cắt tiếp: mưa còn 2015–2026, lưới còn 25 điểm; ngưỡng lùi về phương án R4 (phân vị) |
| **Hết W6** | Có bảng metric đầy đủ 2 kịch bản | Bỏ kịch bản B, chỉ báo cáo A + nêu rõ trong Limitations |
| **Hết W8** | Report 3 đã nộp | — |

## Buffer

Lịch 9 tuần **gần như không có buffer**. Đệm duy nhất:
- Deadline nội bộ sớm 2–3 ngày.
- LSTM và trang dashboard thứ 3 là phần "có thì tốt" — hy sinh trước tiên.
- W9 không có việc kỹ thuật mới, chỉ viết và luyện nói.

👉 Vì vậy **các chốt kiểm tra ở trên là bắt buộc**. Trễ mà không cắt scope là cách chắc chắn nhất để mất điểm Report 3.
