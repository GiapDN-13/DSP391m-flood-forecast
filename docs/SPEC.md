# ĐẶC TẢ YÊU CẦU — DSP391m

**Phiên bản:** 1.0 · **Ngày:** 15/09/2026 · **Chủ tài liệu:** G
**Trạng thái:** Baseline. Mọi thay đổi phải qua PR và ghi vào §10.

## Cách dùng tài liệu này

- Mỗi yêu cầu có **ID cố định** (`FR-D1`, `NFR-3`…). ID **không bao giờ đổi hay tái sử dụng**, kể cả khi yêu cầu bị huỷ.
- **Mỗi FR = một issue trên GitHub Project**, tiêu đề bắt đầu bằng ID. Phần *Tiêu chí nghiệm thu* chính là Definition of Done của issue.
- Ưu tiên theo MoSCoW: **M** = bắt buộc (không có thì hỏng bài) · **S** = nên có · **C** = có thì tốt · **W** = đã loại khỏi phạm vi.
- Lịch 9 tuần: **chỉ M là cam kết**. S và C là phần hy sinh trước khi đụng tới M.

---

# 1. Bối cảnh & phạm vi

## 1.1 Bài toán

Xây dựng hệ thống dự báo **lưu lượng sông và cấp báo động lũ 1–3 ngày** cho lưu vực sông Hương – sông Bồ (TP. Huế), từ dữ liệu khí tượng – thuỷ văn mở, và trình bày kết quả dưới dạng cảnh báo theo **cấp BĐ I/II/III của Việt Nam** ở quy mô tiểu lưu vực.

## 1.2 Trong phạm vi

- Thu thập, làm sạch, lưu trữ dữ liệu GloFAS + ERA5 qua Open-Meteo.
- Quy đổi mực nước báo động → ngưỡng lưu lượng.
- Mô hình hồi quy lưu lượng và phân loại cấp báo động, horizon 1–3 ngày.
- Đánh giá theo chuẩn thuỷ văn và chuẩn sự kiện hiếm.
- Dashboard trực quan + pipeline chạy hằng ngày.
- 4 báo cáo và bài thuyết trình.

## 1.3 Ngoài phạm vi *(nêu rõ để không bị hỏi vặn)*

| Không làm | Vì sao |
|---|---|
| Mô hình thuỷ văn vật lý (HEC-HMS, MIKE…) | Ngoài phạm vi môn học, thiếu số liệu địa hình/mặt cắt |
| Dự báo ngập lụt theo độ sâu, bản đồ ngập | Cần DEM độ phân giải cao và mô hình thuỷ lực 2D |
| Cảnh báo thời gian thực dưới 24 giờ | Dữ liệu đầu vào cập nhật theo ngày |
| Cảnh báo chính thức cho người dân | Sản phẩm học thuật — xem `NFR-9` |
| Horizon > 3 ngày | Sai số dự báo mưa tăng nhanh, ngoài câu hỏi nghiên cứu |

## 1.4 Người dùng

| Ký hiệu | Đối tượng | Cần gì |
|---|---|---|
| U1 | Cán bộ phòng chống thiên tai cấp xã *(người dùng giả định)* | Biết xã mình 1–3 ngày tới ở cấp BĐ nào |
| U2 | Người dân vùng ven sông | Thông tin đơn giản, một màn hình |
| U3 | **Giảng viên chấm bài** | Kiểm được phương pháp, số liệu, khả năng tái lập |
| U4 | Chính nhóm | Chạy lại, gỡ lỗi, bàn giao |

> U3 là người dùng **thực sự** của kỳ này. Mọi yêu cầu về truy vết và tái lập (`NFR-1`, `NFR-11`) tồn tại vì U3.

## 1.5 Trường hợp sử dụng chính

| ID | Use case | Người dùng | FR liên quan |
|---|---|---|---|
| UC1 | Xem cấp nguy cơ 1–3 ngày tới của một tiểu lưu vực/xã | U1, U2 | FR-P1, FR-P2 |
| UC2 | Hiểu vì sao hôm nay có cảnh báo | U1, U3 | FR-V5, FR-P3 |
| UC3 | Hệ thống tự cập nhật dự báo mỗi sáng | — | FR-P4 |
| UC4 | Tái lập toàn bộ kết quả từ số 0 | U3, U4 | NFR-1, FR-V6 |
| UC5 | Đối chiếu mô hình với dự báo GloFAS gốc | U3 | FR-M1, FR-V4 |

---

# 2. Yêu cầu chức năng — Dữ liệu (FR-D)

| ID | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Ai | Tuần |
|---|---|---|---|---|---|
| **FR-D1** | Lấy lưu lượng GloFAS theo ngày cho các điểm đã chốt, 1984-01-01 → 2026-08-31 | **M** | File Parquet tồn tại; số ngày khớp khoảng yêu cầu; 0 ngày trùng; `q_mean` của ô chính > 100 m³/s | G | W1–W2 |
| **FR-D2** | Lấy mưa ERA5 theo **giờ** (2015–2026) và theo **ngày** (2010–2026), lưới 0,10° (64 điểm) | **M** | ≥ 95 % điểm × năm có dữ liệu; phần thiếu liệt kê trong log | G | ✅ **xong 15/09** |
| **FR-D3** | Lấy **mưa dự báo đã phát trong quá khứ** (Historical Forecast API) phủ tập test 07/2022 → 2026, horizon 1–3 ngày | **S** | Có chuỗi mưa dự báo cho ≥ 90 % ngày trong tập test | G | W5 |
| **FR-D4** | Crawler chịu lỗi: retry luỹ thừa, cache theo request, checkpoint để resume | **M** | Ngắt mạng giữa chừng rồi chạy lại **không mất dữ liệu và không gọi lại request đã xong** | G | W1 |
| **FR-D5** | Xác định ô lưới GloFAS nằm đúng dòng chảy chính | **M** | Chốt bằng 3 bằng chứng độc lập (hình học OSM · tương quan · diện tích lưu vực suy ra), tái lập được bằng `python -m src.features.river_id`; ghi vào `config.RIVER_POINTS` | G | ✅ **xong 15/09** |
| **FR-D6** | Sao lưu dữ liệu ra ngoài máy cá nhân | **M** | `daily_panel.parquet` tải về được từ Google Drive **và** HF Datasets bởi cả 3 người | G | W3 |
| **FR-D7** | Bộ sự kiện lũ lịch sử ≥ 15 đợt, có nguồn trích dẫn được | **M** | `flood_events.csv` đủ cột; mọi dòng có `source_url` + `accessed_date`; ≥ 10 dòng `confidence=cao` | H | W2–W3 |
| **FR-D8** | Ranh giới hành chính cấp xã bản sau 01/07/2025 | **S** | GeoJSON tải được, ghi rõ ngày phiên bản. Không có → chuyển sang tiểu lưu vực (`FR-P1`) | D | W3 |

# 3. Yêu cầu chức năng — Xử lý (FR-E)

| ID | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Ai | Tuần |
|---|---|---|---|---|---|
| **FR-E1** | Chuẩn hoá múi giờ về giờ Việt Nam (UTC+7) nhất quán toàn hệ thống | **M** | `tests/test_clean.py::test_doi_timezone_utc_sang_ict` xanh | D | W2 |
| **FR-E2** | Gộp mưa giờ → ngày, đúng định nghĩa ngày hành chính VN | **M** | Tổng 24 giá trị giờ = giá trị ngày (test tự động) | D | W2 |
| **FR-E3** | Phát hiện và xử lý dữ liệu bất thường: thiếu ngày, ngày trùng, discharge âm, mưa âm | **M** | 4 test trong `tests/test_clean.py` xanh; báo cáo tỉ lệ thiếu theo năm | D | W2 |
| **FR-E4** | Tổng hợp mưa lưới → trung bình theo **tiểu lưu vực** (3 vùng) | **M** | `DATA_SPLITS.md` §5 điền xong; số cột mưa ≤ 30 | D | W3 |
| **FR-E5** | Sinh bảng phân tích chuẩn `daily_panel.parquet` | **M** | 1 dòng/ngày/trạm; đủ cột trong `DATA_DICTIONARY.md` §2; không có ngày trùng | G | W3 |
| **FR-E6** | Sinh lag feature và mưa tích luỹ **không rò rỉ tương lai** | **M** | `tests/test_no_leakage.py` xanh toàn bộ | G | W3 |

# 4. Yêu cầu chức năng — Ngưỡng báo động (FR-T)

| ID | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Ai | Tuần |
|---|---|---|---|---|---|
| **FR-T1** | Nạp mực nước BĐ I/II/III đã **đối chiếu văn bản gốc** QĐ 05/2020/QĐ-TTg | **M** | `THRESHOLDS.md` §2 đã tick cả 2 trạm, ghi số hiệu phụ lục | H | W1 |
| **FR-T2** | Xây ánh xạ mực nước → lưu lượng theo đường R2, kèm khoảng tin cậy bootstrap | **M** | `THRESHOLDS.md` §4 điền đủ; báo cáo N, R², KTC 95 % cho từng cấp | G | W3 |
| **FR-T3** | Sinh nhãn `alert_level` (0–3) cho toàn chuỗi | **M** | Cột có trong panel; phân bố lớp được báo cáo theo năm | G | W3 |
| **FR-T4** | Kiểm chứng ngưỡng bằng 3 đợt lũ lịch sử 1999/2020/2023 | **M** | `THRESHOLDS.md` §5 điền; **lệch tối đa 1 cấp** ở cả 3 đợt | G | W3 |
| **FR-T5** | Kiểm chứng chéo bằng ánh xạ tần suất (R3) | **C** | Lệch < 25 % so với R2, hoặc giải thích được nguyên nhân | G | W3 |
| ~~FR-T6~~ | ~~Đường R1 (rating curve thực đo) từ số liệu trạm~~ | **W** | **ĐÃ LOẠI 15/09/2026** — không gửi được công văn xin số liệu. Ánh xạ H→Q dựa hoàn toàn vào R2, kiểm chứng chéo bằng R3 | — | — |

# 5. Yêu cầu chức năng — Mô hình (FR-M)

| ID | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Ai | Tuần |
|---|---|---|---|---|---|
| **FR-M1** | 4 baseline: persistence · seasonal naive · ARIMA · **dự báo GloFAS thô** | **M** | Bảng metric đủ 4 baseline × 3 horizon | D | W5 |
| **FR-M2** | LightGBM hồi quy lưu lượng, horizon 1/2/3, **có GloFAS forecast làm feature** | **M** | Model lưu được, dự báo lại được; đạt `AC-1` §7 | G | W5 |
| **FR-M3** | 3 bộ phân loại nhị phân lồng nhau `≥BĐ I`, `≥BĐ II`, `≥BĐ III`, có xử lý mất cân bằng | **M** | `scale_pos_weight` đúng tỉ lệ; xuất xác suất; đạt `AC-2` §7 | G | W5 |
| **FR-M4** | Tinh chỉnh siêu tham số bằng Optuna trên tập validation | **M** | ≥ 30 trial; kết quả ghi `experiments.csv`; **không chạm tập test** | G | W6 |
| **FR-M5** | Chọn ngưỡng quyết định theo chi phí 10:1, kèm độ nhạy 5:1 và 20:1 | **M** | Bảng 3 kịch bản chi phí | G | W6 |
| **FR-M6** | Hiệu chỉnh xác suất (isotonic) + reliability diagram | **S** | Có hình reliability | G | W6 |
| **FR-M7** | LSTM để so sánh | **C** | Chỉ làm ở W8 nếu mọi M đã xong | G | W8 |

# 6. Yêu cầu chức năng — Đánh giá (FR-V)

| ID | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Ai | Tuần |
|---|---|---|---|---|---|
| **FR-V1** | Walk-forward validation, cửa sổ mở rộng dần, **gap ≥ 3 ngày** giữa train và test | **M** | `tests/test_no_leakage.py::test_walk_forward_co_gap` xanh | D | W6 |
| **FR-V2** | Metric hồi quy: RMSE · MAE · NSE · KGE, theo từng horizon | **M** | Bảng đầy đủ, có cả baseline để so | D | W6 |
| **FR-V3** | Metric sự kiện hiếm: POD · FAR · CSI · F1 · PR-AUC · Brier. **Cấm accuracy** | **M** | Không có chữ "accuracy" trong bảng kết quả | D | W6 |
| **FR-V4** | Đánh giá **2 kịch bản**: A (mưa ERA5) và B (mưa dự báo) | **S** | Bảng `RESEARCH_DESIGN.md` §2.4 điền đủ, có cột Δ | D | W6 |
| **FR-V5** | Đánh giá theo **đợt lũ** (1 đợt = 1 sự kiện, cửa sổ ±1 ngày) | **M** | Bảng riêng, kèm số sự kiện trong tập test | D | W6 |
| **FR-V6** | Nhật ký thí nghiệm: mọi lần chạy ghi ngày, commit hash, config, metric | **M** | `reports/experiments.csv` có ≥ 1 dòng cho mỗi số xuất hiện trong Report 3 | G | W5–W8 |
| **FR-V7** | Giải thích mô hình bằng SHAP | **M** | Hình SHAP + nhận xét feature quan trọng có hợp lý thuỷ văn không | G | W7 |
| **FR-V8** | Phân tích sai số: sai ở mùa nào, có cắt ngọn đỉnh lũ không, ablation nhóm feature | **S** | Notebook + bảng ablation | G/D | W6–W7 |

# 7. Ngưỡng nghiệm thu sản phẩm khoa học (AC)

Đây là **điều kiện để tuyên bố dự án thành công**. Không đạt thì phải giải thích trong Limitations, không được giấu.

| ID | Tiêu chí | Ngưỡng | Ghi chú |
|---|---|---|---|
| **AC-1** | Chất lượng hồi quy tại horizon 1 ngày, kịch bản A | **NSE ≥ 0,5** trên tập test | NSE > 0,5 là mức "chấp nhận được" thường dùng trong tài liệu thuỷ văn — H tra và trích dẫn nguồn chuẩn (thường dẫn Moriasi et al.) |
| **AC-2** | Khả năng bắt sự kiện tại ngưỡng **≥ BĐ II**, horizon 1 ngày | **POD ≥ 0,7** kèm FAR được báo cáo | Ưu tiên POD vì bỏ sót nguy hiểm hơn báo nhầm |
| **AC-3** | **So với GloFAS thô** | RMSE của LightGBM **≤** RMSE GloFAS thô tại h=1 trên cùng tập test | Đây là tiêu chí sống còn của phần Contribution. Vì GloFAS là feature đầu vào nên khó trượt — nếu vẫn trượt thì có lỗi trong pipeline, phải điều tra |
| **AC-4** | Ánh xạ ngưỡng đáng tin | 3/3 đợt lũ lịch sử lệch **≤ 1 cấp** BĐ | Xem `FR-T4` |
| **AC-5** | Không rò rỉ dữ liệu | Toàn bộ `tests/test_no_leakage.py` xanh **và** NSE < 0,98 | NSE > 0,98 là dấu hiệu rò rỉ, không phải thành tích |
| **AC-6** | Đủ mẫu để kết luận | Ngưỡng dùng làm kết luận chính có **≥ 30 ngày dương** trong test | Không đủ → lùi xuống ngưỡng thấp hơn, xem `RESEARCH_DESIGN.md` §3.4 |

> ⚠️ **AC-1 và AC-2 là kỳ vọng, không phải lời hứa.** Ngưỡng đặt trước để tránh tự huyễn hoặc khi có kết quả. Nếu không đạt: báo cáo trung thực số thật + phân tích nguyên nhân. Một dự án đạt NSE 0,42 mà giải thích được vì sao **ăn điểm cao hơn** một dự án khoe 0,99 do rò rỉ dữ liệu.

# 8. Yêu cầu chức năng — Sản phẩm (FR-P) & Báo cáo (FR-R)

| ID | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Ai | Tuần |
|---|---|---|---|---|---|
| **FR-P1** | Bản đồ nguy cơ theo tiểu lưu vực (hoặc xã nếu có `FR-D8`), tô màu theo cấp BĐ | **M** | Mở được, chọn được ngày, hiển thị đúng cấp | D | W7 |
| **FR-P2** | Biểu đồ dự báo lưu lượng 1–3 ngày, có vẽ **đường ngưỡng BĐ I/II/III** | **M** | Hiển thị lịch sử 30 ngày + dự báo 3 ngày | D | W7 |
| **FR-P3** | Trang giải thích: cảnh báo dựa trên gì, hạn chế là gì, SHAP | **S** | Người ngoài đọc hiểu không cần giải thích thêm | H/D | W7 |
| **FR-P4** | Pipeline dự báo chạy tự động hằng ngày | **S** | GitHub Actions cron chạy xanh **3 ngày liên tiếp** | G | ✅ **bật sớm 15/09** — chạy từ W1 để tích luỹ dự báo thật, xem `predict_daily.py` |
| **FR-P5** | Tuyên bố miễn trừ trách nhiệm hiển thị **trên mọi màn hình** | **M** | Có ở footer mọi trang — xem `NFR-9` | D | W7 |
| **FR-R1** | Report 1 — Proposal | **M** | Theo `SUBMIT_CHECKLIST.md` | H | W2 |
| **FR-R2** | Report 2 — Data & EDA | **M** | Mỗi hình kèm 1 insight | H | W4 |
| **FR-R3** | Report 3 — Model & Evaluation | **M** | Mọi số truy được về `experiments.csv` | H | W8 |
| **FR-R4** | Report 4 + slide 30 phút | **M** | Đã sửa theo toàn bộ feedback | H | W9 |

---

# 9. Yêu cầu phi chức năng (NFR)

| ID | Loại | Yêu cầu | Cách kiểm chứng |
|---|---|---|---|
| **NFR-1** | **Tái lập** | Chạy lại từ số 0 trên máy khác cho **cùng con số** trong báo cáo. Seed cố định ở `config.SEED`; `requirements.txt` ghim `==`; mọi bước có lệnh trong `RUNBOOK.md` | Một người **không viết code đó** chạy lại theo RUNBOOK và ra cùng kết quả — thử ở W8 |
| **NFR-2** | Hiệu năng | Crawl toàn bộ ≤ **48 giờ** máy chạy nền. Pipeline dự báo hằng ngày ≤ **15 phút**. Dashboard tải trang đầu ≤ **5 giây** | Đo và ghi vào `API_NOTES.md` §3 |
| **NFR-3** | Chịu lỗi | Đứt mạng / lỗi API / tắt máy giữa chừng **không làm mất dữ liệu đã crawl** | Chủ động ngắt mạng giữa lúc crawl rồi chạy lại (test thủ công, ghi vào RUNBOOK) |
| **NFR-4** | **Toàn vẹn dữ liệu** | Không có rò rỉ thông tin tương lai ở bất kỳ khâu nào: feature, scaler, chọn siêu tham số, chia tập | `tests/test_no_leakage.py` chạy trong CI mọi PR |
| **NFR-5** | Bảo trì | Code dùng lại nằm trong `src/`, notebook chỉ gọi hàm. `ruff` sạch. Mọi module trong `src/etl`, `src/features` có ít nhất 1 test | CI chặn merge nếu lint hoặc test đỏ |
| **NFR-6** | Khả dụng | Người không chuyên nhìn dashboard **hiểu mức nguy cơ trong 30 giây**. Toàn bộ giao diện tiếng Việt. Dùng được trên màn hình điện thoại | Cho 2 người ngoài nhóm thử, ghi lại phản hồi ở W8 |
| **NFR-7** | **Tiếp cận được** | Cấp nguy cơ **không được phân biệt chỉ bằng màu** — phải kèm nhãn chữ và ký hiệu. Tương phản chữ/nền tối thiểu 4.5:1. Hình trong báo cáo đọc được khi in đen trắng | Kiểm bằng cách chuyển ảnh chụp màn hình sang thang xám — vẫn phân biệt được cấp |
| **NFR-8** | Pháp lý | Trích dẫn Open-Meteo (CC BY 4.0) và GloFAS/Copernicus đúng quy định trong **cả 4 báo cáo và trên dashboard** | Mục trong `SUBMIT_CHECKLIST.md` |
| **NFR-9** | **An toàn thông tin cảnh báo** | Mọi màn hình và mọi báo cáo phải ghi rõ: *sản phẩm học thuật, không phải cảnh báo chính thức; nguồn chính thức là Đài KTTV*. Không dùng từ ngữ mang tính chỉ đạo sơ tán | Rà trước mỗi lần nộp và trước khi deploy |
| **NFR-10** | Bảo mật | Không có token/mật khẩu trong repo. Dữ liệu và repo để chế độ private | CI quét file nặng và file dữ liệu; `.env` trong `.gitignore` |
| **NFR-11** | **Truy vết** | Mọi con số trong Report 3 truy được về một dòng trong `experiments.csv` kèm commit hash | Rà chéo ở W8 |
| **NFR-12** | Tính di động | Chạy được trên Windows (máy nhóm) và Linux (CI, Streamlit Cloud) | CI chạy Ubuntu; nhóm chạy Windows |
| **NFR-13** | Chi phí | **0 đồng.** Chỉ dùng hạn mức miễn phí: Open-Meteo, GitHub Actions, Streamlit Community Cloud, HF Datasets | Không đăng ký dịch vụ trả phí nào |
| **NFR-14** | Liên tục | Không có đầu việc nào chỉ một người làm được; không có credential chỉ một người giữ | `RUNBOOK.md` §1 và §5 điền đủ ở W8 |

---

# 10. Ràng buộc & giả định

## 10.1 Ràng buộc

| ID | Ràng buộc | Hệ quả |
|---|---|---|
| C1 | **Chỉ còn 9 tuần** (15/09 → 16/11/2026) | Scope đã cắt sẵn — `PLAN.md` |
| C2 | Team 3 người, tỉ trọng 50/32/18 | Phân công theo `TEAM.md` |
| C3 | Không có ngân sách | `NFR-13` |
| C4 | GloFAS đổi chế độ dữ liệu từ 07/2022 | Bắt buộc tách split — `DATA_SPLITS.md` §1 |
| C5 | Ngưỡng BĐ theo mực nước, dữ liệu theo lưu lượng | Phải xây ánh xạ — `THRESHOLDS.md` |
| C6 | Địa giới cấp xã thay đổi từ 01/07/2025 | `FR-D8`, phương án tiểu lưu vực |
| C7 | Thi vấn đáp chấm **cá nhân** | `EXPLAINER.md` + mock exam |

## 10.2 Giả định *(nếu sai thì kế hoạch phải đổi)*

| ID | Giả định | Nếu sai thì |
|---|---|---|
| A1 | Open-Meteo giữ miễn phí, không đổi API trong 9 tuần | Dùng dữ liệu đã cache và backup; nêu trong Limitations |
| A2 | Thu được ≥ 10 sự kiện lũ có công bố đỉnh mực nước | Lùi về ngưỡng phân vị R4, **đổi tên nhãn**, hạ tuyên bố |
| A3 | Ô lưới GloFAS đại diện được dòng chảy thật tại trạm | ✅ **ĐÃ GIẢI QUYẾT 15/09** — chốt ô (16.45, 107.50) cho sông Hương bằng `src/features/river_id.py`; diện tích lưu vực suy ra lệch 7 % so với thực tế. **Sông Bồ không tách được** ⇒ thu hẹp còn 1 trạm | 
| A4 | Số ngày vượt BĐ II trong test đủ ≥ 30 | Áp `AC-6`, chuyển sang báo cáo theo đợt lũ |
| A5 | Ngày nộp suy ra từ session number gần đúng | Lấy ngày thật từ LMS ở W1 |

---

# 11. Ma trận truy vết

| Yêu cầu | Bằng chứng | Xuất hiện ở báo cáo |
|---|---|---|
| FR-D1…D8 | `data/raw/`, `grid_candidates.csv`, `flood_events.csv` | R2 — Data Collection |
| FR-E1…E6 | `tests/test_clean.py`, `test_no_leakage.py`, `DATA_DICTIONARY.md` | R2 — Data Cleaning |
| FR-T1…T6 | `THRESHOLDS.md` §4, §5 | R2 — Định nghĩa ngưỡng · R3 — Methodology |
| FR-M1…M7 | `experiments.csv`, `models/` | R3 — Model Development |
| FR-V1…V8 | `experiments.csv`, `reports/figures/shap_*` | R3 — Evaluation & Interpretation |
| AC-1…AC-6 | Bảng kết quả cuối | R3 — Results · Limitations |
| FR-P1…P5 | Link dashboard, video demo | R3 — Visualization |
| NFR-1, NFR-11 | `RUNBOOK.md`, `experiments.csv` | R3 — Reproducibility |
| NFR-7, NFR-9 | Ảnh chụp dashboard | R3 — Discussion |

# 12. Nhật ký thay đổi

| Ngày | Phiên bản | Thay đổi | Ai |
|---|---|---|---|
| 15/09/2026 | 1.0 | Bản đầu tiên | G |
| 15/09/2026 | 1.1 | Loại FR-T6 (không xin được số liệu trạm). Cập nhật giả định A3 theo kết quả quét lưới | G |
| 15/09/2026 | 1.2 | ~~FR-D2 đổi sang mưa ngày, lưới 25 điểm~~ — **đã huỷ ở 1.3** | G |
| 15/09/2026 | 1.3 | **Khôi phục FR-D2** (mưa giờ, lưới 0,10°). Lần cắt ở 1.2 dựa trên chẩn đoán sai về hạn mức (`FINDINGS_QUOTA.md` §3) | G |
| 15/09/2026 | 1.4 | **Thu hẹp phạm vi còn MỘT trạm (Kim Long / sông Hương)** — GloFAS ~5 km không phân giải được sông Bồ. FR-D5 hoàn thành (`FINDINGS_GRID.md` Phần 2) | G |
