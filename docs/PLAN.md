# KẾ HOẠCH CHI TIẾT 60 SESSIONS — DSP391m

**Giả định quy đổi:** 60 sessions ≈ **15 tuần × 4 sessions/tuần**, bắt đầu tuần 14/09/2026.
👉 Nếu thời khoá biểu thực tế khác, chỉ cần sửa cột "Tuần / Ngày", phần việc giữ nguyên.

## Mốc nộp (từ syllabus)

| Mốc | Session | Tuần | Hạn thực tế | Deadline nội bộ (sớm hơn) | % điểm |
|---|---|---|---|---|---|
| Nháp Report 1 | S9 | W3 | 30/09/2026 | 28/09 | – |
| **Report 1** | S12 | W3 | **04/10/2026** | **01/10** | 10 % |
| **Report 2** | S26 | W7 | **01/11/2026** | **29/10** | 20 % |
| **Report 3** | S49 | W13 | **13/12/2026** | **10/12** | 40 % |
| **Report 4 / Final** | S57 | W15 | **21/12/2026** | **18/12** | 10 % |
| Thi vấn đáp | S58–60 | W15 | 22–27/12/2026 | – | 20 % |

---

## W01 · S1–4 · 14–20/09 — Khởi động

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Tạo repo GitHub private, push skeleton này, bật branch protection, mời D+H làm collaborator | D+H clone được |
| **G** | Tạo GitHub Project "DSP391m Flood", seed issue bằng `scripts/bootstrap_github.ps1` | Board có đủ issue |
| **G** | Script `src/ingest/openmeteo_flood.py` — gọi thử **1 điểm sông Hương (16.46, 107.59)**, discharge 2020–2023, vẽ để thấy đợt lũ 10/2020 | Có `reports/figures/w01_huong_2020.png` |
| **D** | Setup môi trường (`make setup`), chạy lại được script của G, tự thử 1 toạ độ khác trên sông Bồ | `notebooks/01_first_call.ipynb` chạy hết |
| **D** | Đọc doc Open-Meteo Flood API + Historical API, viết 1 trang tóm tắt tham số | `docs/API_NOTES.md` |
| **H** | Lập Zotero group, tìm **6 bài** về dự báo lưu lượng bằng ML / GloFAS / LSTM | 6 entry trong Zotero |
| **H** | Tóm tắt 2/6 bài theo template | `docs/lit/paper_01.md`, `paper_02.md` |
| **Cả 3** | Chốt tên đề tài chính thức, **gửi email giảng viên xin ý kiến trước S5** | Email đã gửi |
| **Cả 3** | Điền mục 6 của `docs/TEAM.md` (thoả thuận hỗ trợ với Huyền) | Đã điền |

> ⚠️ **Việc quan trọng nhất tuần này:** báo giảng viên team đổi từ 2 → 3 người và xin xác nhận phạm vi đề tài không đổi.

## W02 · S5–8 · 21–27/09 — Proposal (phần 1)

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Xác định **ô lưới GloFAS đúng dòng chảy**: quét lưới ±0.3° quanh Kim Long & Phú Ốc, chọn ô có discharge trung bình lớn nhất; lưu bảng toạ độ | `data/external/grid_candidates.csv` + hình so sánh |
| **G** | Viết Methodology + sơ đồ kiến trúc pipeline cho Report 1 | `reports/figures/pipeline.png` |
| **D** | Crawl thử ERA5 mưa theo giờ cho 5 điểm, 2019–2021; đo thời gian & dung lượng để **ước lượng chi phí crawl 40 năm** | Bảng ước lượng trong `docs/API_NOTES.md` |
| **D** | Viết phần Timeline + Risks cho Report 1 (dựa `docs/RISKS.md`) | Draft xong |
| **H** | Tóm tắt 4 bài còn lại | `paper_03..06.md` |
| **H** | Viết **Problem statement + Objectives + Research questions** | Draft trong `reports/report1/` |
| **H** | Ghép literature review thành một mục có mạch (không phải liệt kê rời rạc) | Draft xong |

## W03 · S9–12 · 28/09–04/10 — 🎯 Nộp Report 1

| Ai | Việc | Xong khi |
|---|---|---|
| **H** | **Gộp toàn bộ Report 1**, format theo template trường, mục lục, citation APA | `reports/report1/Report1_v1.docx` |
| **G + D** | Review chéo Report 1, sửa phần kỹ thuật | Comment đã resolve |
| **H** | Chạy `docs/templates/SUBMIT_CHECKLIST.md` | Tick đủ |
| **G** | Nộp nháp S9 → nhận feedback → sửa | Đã nộp |
| **G** | Song song: crawler có **retry + cache + checkpoint** (chạy cả tuần không mất dữ liệu) | `src/ingest/` có test |
| **Cả 3** | **Nộp Report 1 ngày 01/10** (sớm 3 ngày) | ✅ |

## W04 · S13–16 · 05–11/10 — Crawl dữ liệu lớn

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Chạy crawl **discharge 1984–2026** cho toàn bộ điểm đã chốt; chạy nền, log đầy đủ | `data/raw/discharge/*.parquet` |
| **G** | Crawl ERA5 theo lô (chia theo năm), sleep + resume | ≥ 50 % lưới xong |
| **D** | Module `src/etl/clean.py`: xử lý missing, đổi timezone UTC→ICT, chuẩn hoá đơn vị | `pytest tests/test_clean.py` xanh |
| **D** | Kiểm tra toàn vẹn: số ngày thiếu, giá trị âm, outlier vô lý | `notebooks/02_data_quality.ipynb` |
| **H** | Dựng khung **Data dictionary** từ output G gửi (tên cột, đơn vị, nguồn, license) | `docs/DATA_DICTIONARY.md` |
| **H** | Viết mục **pháp lý & bản quyền** (Open-Meteo CC BY 4.0, NASA POWER) cho Report 2 | Draft xong |

## W05 · S17–20 · 12–18/10 — Làm sạch & chuẩn hoá

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Hoàn tất crawl ERA5 100 %; backup lên Google Drive + HF Datasets | Link backup trong README |
| **G** | Gộp về **một bảng phân tích chuẩn** (daily: mưa tổng hợp lưu vực + discharge) | `data/processed/daily_panel.parquet` |
| **G** | Chốt và ghi rõ **mốc cắt 07/2022** (GloFAS đổi từ reanalysis sang archived forecast) | `docs/DATA_SPLITS.md` |
| **D** | Resample mưa giờ → ngày; mưa tích luỹ 1/3/5/7 ngày; API (antecedent precipitation index) | Cột đã có trong panel |
| **D** | Đối chiếu 3 đợt lũ lịch sử **1999, 2020, 2023** có xuất hiện đúng trong dữ liệu không | 3 hình đợt lũ |
| **H** | Hoàn thiện Data dictionary; viết mục **Data Collection** cho Report 2 | Draft xong |

## W06 · S21–24 · 19–25/10 — EDA

| Ai | Việc | Xong khi |
|---|---|---|
| **D** | EDA mùa vụ: phân bố mưa/discharge theo tháng, boxplot mùa lũ (9–12) | `notebooks/03_eda_seasonal.ipynb` |
| **D** | **Tương quan mưa–lưu lượng theo lag 0–7 ngày**, cross-correlation, xác định lag tối ưu | Hình + kết luận bằng chữ |
| **G** | Bản đồ mưa trung bình lưu vực + vị trí điểm lưới, phân tích không gian | `reports/figures/map_rain.png` |
| **G** | Phân tích **extreme value**: return period, phân phối đuôi của discharge | Notebook |
| **H** | Biên tập insight EDA thành văn xuôi có ý nghĩa (không chỉ mô tả hình) | Draft Report 2 |
| **H** | Đặt caption + đánh số toàn bộ hình/bảng | Xong |

## W07 · S25–28 · 26/10–01/11 — 🎯 Nộp Report 2

| Ai | Việc | Xong khi |
|---|---|---|
| **H** | Gộp Report 2 (Data Collection + Cleaning + EDA), format, citation | `reports/report2/Report2_v1.docx` |
| **G + D** | Review chéo; đảm bảo **mỗi hình đều có 1 insight** đi kèm | Xong |
| **Cả 3** | **Nộp Report 2 ngày 29/10** | ✅ |
| **G** | Song song: dựng khung `src/models/` + hàm walk-forward split | Code chạy |

## W08 · S29–32 · 02–08/11 — Baseline & mô hình chính

| Ai | Việc | Xong khi |
|---|---|---|
| **D** | Baseline: **persistence**, **seasonal naive**, **ARIMA** cho horizon 1/2/3 ngày | Bảng RMSE/MAE/NSE |
| **D** | ⭐ Baseline quan trọng nhất: **dùng thẳng dự báo GloFAS của Open-Meteo** làm đối chứng | Có số để so |
| **G** | LightGBM với lag features (mưa lag 1–7, discharge lag 1–14, mùa, API) | Model v1 |
| **G** | Classifier "ngày vượt ngưỡng báo động" — ngưỡng chốt trong `docs/THRESHOLDS.md` | Model v1 |
| **H** | Viết Methodology cho Report 3 (mô tả từng mô hình bằng lời) | Draft |
| **H** | Cập nhật `docs/EXPLAINER.md` sau buổi handoff | 3 trang |

## W09 · S33–36 · 09–15/11 — LSTM & tinh chỉnh

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | LSTM (PyTorch) chuỗi 30 ngày → horizon 1–3; so với LightGBM | Bảng so sánh |
| **G** | Tuning LightGBM bằng **Optuna** 50–100 trial, log kết quả | `reports/experiments.csv` |
| **D** | Chạy **walk-forward validation** đúng mốc split; RMSE / MAE / NSE / KGE | Bảng kết quả |
| **D** | Metric sự kiện hiếm: **POD, FAR, CSI, F1** trên ngày vượt ngưỡng | Bảng |
| **H** | Format bảng kết quả cho báo cáo | Xong |

## W10 · S37–40 · 16–22/11 — Đánh giá sâu

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Error analysis: sai ở đâu? mùa nào? đỉnh lũ có bị "cắt ngọn" không? | Notebook + hình |
| **G** | **SHAP** giải thích feature quan trọng | `reports/figures/shap_*.png` |
| **D** | Ablation: bỏ từng nhóm feature, xem RMSE tăng bao nhiêu | Bảng ablation |
| **D** | Bắt đầu dashboard Streamlit — khung trang + biểu đồ dự báo | `dashboard/app.py` chạy |
| **H** | Viết mục Evaluation cho Report 3 | Draft |
| **Cả 3** | 🔁 **Mock exam lần 1** — mỗi người 3 câu | Ghi vào log |

## W11 · S41–44 · 23–29/11 — Trực quan hoá & triển khai

| Ai | Việc | Xong khi |
|---|---|---|
| **D** | Dashboard: bản đồ nguy cơ **theo xã** (GeoJSON xã mới sau sáp nhập 2025) | Trang map chạy |
| **D** | Trang biểu đồ dự báo 1–3 ngày + khoảng tin cậy | Xong |
| **G** | Pipeline hàng ngày: forecast API → feature → predict → ghi kết quả | `make daily` chạy được |
| **G** | Deploy **GitHub Actions cron + Streamlit Community Cloud** (không phụ thuộc home server) | Link công khai |
| **H** | Viết nội dung chữ trên dashboard + hướng dẫn sử dụng | `docs/DASHBOARD_GUIDE.md` |
| **H** | Bắt đầu slide (khung 30 phút) | Outline slide |

## W12 · S45–48 · 30/11–06/12 — Hoàn thiện nội dung Report 3

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Chốt model cuối, freeze code, tag `v1.0` | Tag trên GitHub |
| **G** | Viết Model Development + Interpretation | Draft |
| **D** | Viết Conclusion & Recommendation cho địa phương (xã nào, ngưỡng nào, cảnh báo ra sao) | Draft |
| **D** | Mục **Limitations** (GloFAS là mô phỏng, không có trạm thực, độ phân giải ~5 km) | Draft |
| **H** | Gộp + format Report 3 — **40 % điểm, quan trọng nhất** | `Report3_v1.docx` |
| **Cả 3** | 🔁 **Mock exam lần 2** | Xong |

## W13 · S49–52 · 07–13/12 — 🎯 Nộp Report 3

| Ai | Việc | Xong khi |
|---|---|---|
| **Cả 3** | Review chéo toàn bộ Report 3, **2 vòng** | Xong |
| **H** | Checklist nộp, kiểm tra citation, kiểm tra trùng lặp | Tick đủ |
| **Cả 3** | **Nộp Report 3 ngày 10/12** | ✅ |
| **G** | Dọn repo: README đầy đủ, hướng dẫn reproduce từ số 0 | Người lạ chạy được |

## W14 · S53–56 · 14–20/12 — Gộp báo cáo cuối & luyện nói

| Ai | Việc | Xong khi |
|---|---|---|
| **H** | Gộp Report 1+2+3 → **Report 4**, sửa theo toàn bộ feedback giảng viên | `Final_v1.docx` |
| **H** | Hoàn thiện slide 30 phút + script nói cho từng người | Slide xong |
| **G** | Kiểm tra nhất quán số liệu giữa 3 report (số trong R1 phải khớp R3) | Bảng đối chiếu |
| **D** | Chuẩn bị demo dashboard live + **video backup** phòng mất mạng | Video xong |
| **Cả 3** | **Luyện thuyết trình lần 1 & 2**, bấm giờ | Ghi lại |

## W15 · S57–60 · 21–27/12 — 🎯 Nộp Final + Thi

| Ai | Việc | Xong khi |
|---|---|---|
| **Cả 3** | **Nộp Report 4 ngày 18/12** | ✅ |
| **Cả 3** | **Luyện thuyết trình lần 3**, full 30 phút | Xong |
| **Cả 3** | 🔁 **Mock exam lần 3** — hỏi xoáy phần KHÔNG phải mình làm | Xong |
| **Cả 3** | Thi vấn đáp S58–60 | ✅ |

---

## Đường găng (critical path)

```
W01  chốt ô lưới GloFAS
  └─> W04–W05  crawl xong toàn bộ dữ liệu      ← RỦI RO CAO NHẤT
        └─> W06  EDA
              └─> W08–W09  model
                    └─> W12  Report 3 (40 %)
```

**Quy tắc vàng:** nếu hết **W05** mà chưa có `data/processed/daily_panel.parquet` → kích hoạt phương án B trong `docs/RISKS.md`: giảm còn 15 năm dữ liệu (2010–2026) và 50 điểm lưới. Thà dữ liệu ít mà kịp model, còn hơn dữ liệu đẹp mà không kịp làm Report 3.

## Buffer đã cài sẵn

- Mọi deadline nội bộ sớm hơn deadline thật **3 ngày**.
- W14 gần như không có việc mới → là buffer cho phần trễ từ W12–13.
- Việc của Huyền luôn có G backup và **không nằm trên đường găng**.
