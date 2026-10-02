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

## 📍 Trạng thái thực tế — 02/10/2026 (giữa W3)

Phần dữ liệu và mô hình **đi trước kế hoạch khoảng 3 tuần**. Kế hoạch W1–W3 bên
dưới giữ nguyên làm lịch sử; từ W4 trở đi đã **lập lại** theo những gì thực sự
còn phải làm.

| Hạng mục | Kế hoạch gốc | Thực tế |
|---|---|---|
| Crawl + panel | W3 | ✅ W1 |
| Report 1 | W2 | ✅ nộp đúng hạn |
| EDA 8 mục | W4 | ✅ 22/09 |
| Baseline + LightGBM + classifier | W5–W6 | ✅ 22/09 — thắng persistence cả 3 horizon |
| Report 2 (PDF) | W4 | ✅ bản nháp 02/10, PR #13 |
| Ngưỡng báo động | W3, ánh xạ H→Q | 🔄 **đổi hướng**: nhãn theo phân vị lưu lượng (`FINDINGS_REGIME.md`) |
| Kịch bản B | W6 | 🔄 **đổi hướng**: thay bằng B′ vì mưa dự báo lưu trữ trùng ERA5 (`FINDINGS_MODEL.md` §4b) |
| Literature review | W2 | ✅ 6/6 bài |

Những thay đổi lớn về thiết kế đều có file `FINDINGS_*.md` ghi lý do — **đọc
trước khi thi vấn đáp**.

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

## W4 · 06/10 – 12/10 — 🎯 Report 2 + thuyết trình

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Đọc lại văn xuôi Report 2, merge PR #13 | PDF chốt |
| **G** | Slide Report 2 + script EN/VI | Deck xong |
| **Cả 3** | Luyện thuyết trình Report 2, bấm giờ | ≥ 2 lần |
| **Cả 3** | **Nộp Report 2 ngày 09/10** | ✅ |
| **G** | Report 3 bước 1: **bộ feature theo horizon, chọn trên valid** | Bảng so sánh valid/test |
| **D, H** | Đọc `FINDINGS_GRID.md` + `CRAWL_EXPLAINED.md`, tự trả lời 5 câu đầu của `EXAM_QUESTION_BANK.md` | Trả lời được không cần tài liệu |

## W5 · 13/10 – 19/10 — Mô hình chính cho Report 3

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | **Hồi quy phân vị 0,9** — xử lý `peak_bias` −0,46 (R24) | Bảng NSE + peak_bias + độ phủ phân vị |
| **G** | Classifier mức nguy cơ dùng bộ feature theo horizon | POD/FAR/CSI cập nhật |
| **G** | **SHAP** cho mô hình h=1 và h=2 | 2 hình summary + dependence |
| **D, H** | Đọc `FINDINGS_EVENTS.md` + `FINDINGS_REGIME.md` | Giải thích được vì sao bỏ ánh xạ H→Q |

## W6 · 20/10 – 26/10 — Dashboard + hoàn thiện đánh giá

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Dashboard Streamlit 2 trang (FR-P1/P2): dự báo hôm nay + lịch sử | Chạy được local |
| **G** | Optuna — **chỉ sau khi bộ feature đã chốt** | Cải thiện ghi vào `experiments.csv` |
| **G** | Đánh giá theo sự kiện: các đợt lũ 2023–2025 trong tập test | Bảng hit/miss |
| **D, H** | Đọc `FINDINGS_MODEL.md` | Giải thích được ablation và peak_bias |

## W7 · 27/10 – 02/11 — 🎯 Viết Report 3

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | `reports/report3/build_report.py` theo mẫu IEEE | PDF |
| **Cả 3** | Review chéo | Xong |
| **Cả 3** | **Nộp Report 3 ngày 02/11** (40 %) | ✅ |

## W8 · 03/11 – 09/11 — Thuyết trình Report 3 + luyện thi

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Slide Report 3 + script | Deck xong |
| **G** | Hoàn thiện `EXPLAINER.md` + `EXAM_QUESTION_BANK.md` | Đủ 30 câu |
| **Cả 3** | 🔁 **Mock exam lần 1** — hỏi xoáy phần **không phải mình làm** | Xong |

## W9 · 10/11 – 16/11 — 🎯 Report 4 + thi

| Ai | Việc | Xong khi |
|---|---|---|
| **G** | Report 4 = R1 + R2 + R3 đã sửa theo feedback, **kèm đính chính abstract Report 1** | PDF |
| **G** | Đối chiếu số liệu giữa 3 report | Bảng đối chiếu |
| **Cả 3** | **Nộp Report 4 ngày 10/11** | ✅ |
| **Cả 3** | 🔁 Mock exam lần 2 + luyện nói 3 lần | Xong |
| **Cả 3** | Thi vấn đáp S58–60 | ✅ |

---

## Đường găng (từ 02/10)

```
Report 2 (09/10)
   └─> feature theo horizon (W4) ─> phân vị 0,9 + SHAP (W5) ─> dashboard (W6)
                                                                  └─> Report 3 (02/11, 40 %)
                                                                        └─> Report 4 + thi
Song song suốt W4–W9:  D, H đọc FINDINGS_*  →  mock exam  →  thi vấn đáp (20 %, chấm cá nhân)
```

Rủi ro lớn nhất còn lại **không phải kỹ thuật** mà là thi vấn đáp: mỗi người bị
chấm riêng, nên ai cũng phải giải thích được toàn bộ dự án — kể cả phần mình
không trực tiếp làm.

## Chốt kiểm tra

| Khi nào | Điều kiện | Không đạt thì |
|---|---|---|
| **09/10** | Report 2 nộp | — |
| **19/10** | Có hồi quy phân vị + SHAP | Bỏ Optuna, dùng tham số hiện tại |
| **26/10** | Dashboard chạy được | Cắt còn 1 trang |
| **02/11** | Report 3 nộp | — |

Thứ tự hy sinh khi thiếu thời gian: **Optuna → trang dashboard thứ 2 → đánh giá
theo sự kiện**. Không bao giờ hy sinh: walk-forward đúng cách · metric sự kiện
hiếm · SHAP · phần Limitations.
