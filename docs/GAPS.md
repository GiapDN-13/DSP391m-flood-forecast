# NHỮNG THỨ KẾ HOẠCH GỐC CÒN THIẾU — và cách bù

Xếp theo mức độ nguy hiểm. Mục 1–5 nếu không xử lý thì **sẽ bị hỏi và bị trừ điểm khi vấn đáp**.

## ✅ Quyết định đã chốt (15/09/2026)

| # | Vấn đề | Quyết định | Chi tiết ở |
|---|---|---|---|
| 1 | Ngưỡng báo động | **Lấy cấp BĐ I/II/III chính thức của VN làm gốc, quy đổi sang lưu lượng** bằng hiệu chuẩn theo sự kiện lịch sử | [`THRESHOLDS.md`](THRESHOLDS.md) |
| 2 | Ranh giới xã đổi sau 2025 | Ưu tiên GeoJSON xã bản sau 01/07/2025; không có thì **đổi sang tiểu lưu vực** | [`DATA_SPLITS.md`](DATA_SPLITS.md) §5 |
| 3 | Đóng góp so với GloFAS | **Hiệu chỉnh + bản địa hoá**, không phải thay thế. GloFAS vừa là baseline vừa là **feature đầu vào** | [`RESEARCH_DESIGN.md`](RESEARCH_DESIGN.md) §1 |
| 4 | Lệch phân phối train/vận hành | Báo cáo **song song 2 kịch bản** A (ERA5) và B (mưa dự báo, qua Historical Forecast API) | [`RESEARCH_DESIGN.md`](RESEARCH_DESIGN.md) §2 |
| 5 | Mất cân bằng lớp | Cấm accuracy; dùng POD/FAR/CSI/PR-AUC; **quy tắc 30 mẫu**; đánh giá theo đợt lũ | [`RESEARCH_DESIGN.md`](RESEARCH_DESIGN.md) §3 |
| 6 | Chưa có đặc tả yêu cầu | Đã bổ sung **FR / NFR / ngưỡng nghiệm thu AC** + ma trận truy vết | [`SPEC.md`](SPEC.md) |

---

## ✅🔴 1. Không có định nghĩa "ngưỡng báo động lũ" — mà đây là biến mục tiêu của bài toán phân loại

**Vấn đề:** Câu hỏi nghiên cứu #2 là *"mô hình phân loại ngày vượt ngưỡng báo động lũ"*, nhưng kế hoạch không nói ngưỡng đó là gì.
Ngưỡng báo động BĐ I/II/III của Việt Nam được định nghĩa theo **mực nước (m)** tại trạm Kim Long (sông Hương) và Phú Ốc (sông Bồ). Trong khi đó GloFAS chỉ cho **lưu lượng (m³/s)**. **Hai đơn vị khác nhau, không quy đổi trực tiếp được** nếu không có đường quan hệ mực nước – lưu lượng (rating curve).

**✅ ĐÃ CHỐT:** lấy **cấp BĐ chính thức làm gốc rồi quy đổi sang lưu lượng**, không dùng ngưỡng phân vị tự chế làm định nghĩa chính.

Quy trình đầy đủ ở [`docs/THRESHOLDS.md`](THRESHOLDS.md). Tóm tắt:

- Nguồn pháp lý: **Quyết định 05/2020/QĐ-TTg** — H tra Phụ lục, xác nhận số BĐ I/II/III cho Kim Long & Phú Ốc ở **W1**.
- Đường quy đổi chính (**R2**): thu ≥ 15 đợt lũ có công bố đỉnh mực nước, ghép với đỉnh discharge GloFAS ±2 ngày, fit `H = α·ln(Q) + β`, nghịch đảo tại từng cấp BĐ.
- **R1** (rating curve thực đo từ Đài KTTV) là bonus — gửi công văn xin **ngay W1** vì thủ tục mất 3–6 tuần.
- **R3** (ánh xạ tần suất) dùng kiểm chứng chéo; lệch > 25 % so với R2 thì phải điều tra trước khi đi tiếp.
- Gọi đúng tên sản phẩm là **"ánh xạ hiệu chuẩn theo sự kiện"**, không gọi là rating curve vật lý — vì nó hấp thụ cả lệch *trung bình ngày ↔ đỉnh tức thời* lẫn sai số GloFAS.

---

## 🔴 2. Ranh giới xã đã thay đổi — bản đồ "theo xã" có thể sai hoàn toàn

**Vấn đề:** Sản phẩm cuối là *"bản đồ nguy cơ theo xã"*, nhưng địa giới hành chính Việt Nam đã thay đổi lớn: Thừa Thiên Huế trở thành **thành phố Huế trực thuộc trung ương**, và cả nước **bỏ cấp huyện, sắp xếp lại cấp xã từ 01/07/2025**. Mọi file GeoJSON xã tải trước 2025 đều **không còn đúng**.

**Cách xử lý:**
- Tải GeoJSON cấp xã **phiên bản sau 01/07/2025** (nguồn: cổng dữ liệu mở của Cục Đo đạc Bản đồ, hoặc OpenStreetMap trích xuất mới).
- Ghi rõ **ngày phiên bản ranh giới** trong data dictionary.
- Nếu không tìm được bản mới kịp → **đổi đơn vị không gian sang "tiểu lưu vực" hoặc "ô lưới 5 km"** thay vì xã, và giải thích lý do. Tiểu lưu vực thực ra **hợp lý hơn về mặt thuỷ văn**, vì nước chảy theo lưu vực chứ không theo địa giới.

👉 Giao D khảo sát ngay **W3**, đừng để tới W7 mới phát hiện.

---

## ✅🔴 3. Chưa trả lời được: "Tại sao không dùng thẳng dự báo của GloFAS?"

**Vấn đề:** Open-Meteo Flood API **đã có sẵn dự báo lưu lượng 7 ngày**. Nếu mô hình của team không tốt hơn cái đó, giảng viên sẽ hỏi ngay: *dự án này đóng góp gì?*

**Cách xử lý — bắt buộc có trong Report 3:**
- Đặt **dự báo GloFAS gốc làm baseline thứ 4** (cạnh persistence / seasonal naive / ARIMA), so trên cùng tập test.
- Định vị đóng góp rõ ràng, chọn 1–2 hướng:
  1. **Hiệu chỉnh sai số cục bộ (bias correction / post-processing)** cho lưu vực sông Hương – sông Bồ — đây là đóng góp hợp lệ và dễ chứng minh nhất.
  2. **Chuyển từ dự báo lưu lượng sang cảnh báo mức nguy cơ theo xã** — thứ GloFAS không cung cấp.
  3. **Giải thích được bằng SHAP** — GloFAS là hộp đen với người dùng địa phương.

**✅ ĐÃ CHỐT** — chi tiết ở [`docs/RESEARCH_DESIGN.md`](RESEARCH_DESIGN.md) §1. Ba điểm cốt lõi:

1. Câu định vị dùng xuyên suốt: *"không thay thế GloFAS, mà **hiệu chỉnh và bản địa hoá** đầu ra của GloFAS thành cảnh báo theo cấp BĐ của Việt Nam ở quy mô tiểu lưu vực"*.
2. 🔑 **GloFAS thô vừa là baseline, vừa là feature đầu vào của mô hình.** Mô hình chỉ học phần sai số còn lại ⇒ về lý thuyết không thể thua GloFAS một cách hệ thống. Đây là cách vô hiệu hoá rủi ro R9.
3. Không tuyên bố quá lời: chỉ nói *chính xác hơn GloFAS thô **trên lưu vực này, trên tập test này***.

👉 Viết đoạn "Contribution" vào Report 1 ngay từ **W2**.

---

## ✅🟠 4. Lệch phân phối giữa lúc train và lúc chạy thật

**Vấn đề:** Train bằng **mưa ERA5 (quan trắc/reanalysis)**, nhưng khi chạy dự báo hằng ngày lại phải dùng **mưa từ Forecast API (dự báo)**. Mưa dự báo sai hơn mưa quan trắc rất nhiều → mô hình chạy thật sẽ tệ hơn kết quả trong báo cáo, đôi khi tệ hơn nhiều.

**✅ ĐÃ CHỐT** — chi tiết ở [`docs/RESEARCH_DESIGN.md`](RESEARCH_DESIGN.md) §2:

- Báo cáo **song song 2 kịch bản**: **A** (mưa ERA5 — cận trên lý tưởng) và **B** (mưa dự báo — hiệu năng vận hành). **Số của B là con số chính thức đưa vào kết luận.**
- Nguồn mưa dự báo quá khứ: **Open-Meteo Historical Forecast API** (`historical-forecast-api.open-meteo.com`) lưu các bản dự báo đã phát từ 2021 — **phủ trọn tập test 07/2022–2026** của nhóm.
- **Δ = A − B** là một kết quả có giá trị riêng: nó đo phần sai số đến từ dự báo mưa chứ không phải từ mô hình.

---

## ✅🟠 5. Mất cân bằng lớp nghiêm trọng ở bài toán phân loại

**Vấn đề:** Ngày vượt ngưỡng báo động chỉ chiếm khoảng **1–3 %** số ngày. Accuracy 97 % là vô nghĩa (đoán "không lũ" mọi ngày cũng được 97 %).

**✅ ĐÃ CHỐT** — chi tiết ở [`docs/RESEARCH_DESIGN.md`](RESEARCH_DESIGN.md) §3:

- **Accuracy bị cấm** trong mọi báo cáo. Dùng POD / FAR / CSI / F1 / **PR-AUC** / Brier + reliability diagram.
- `scale_pos_weight` trong LightGBM. **Không dùng SMOTE** — sinh mẫu tổng hợp trên chuỗi thời gian phá vỡ cấu trúc thời gian và dễ gây rò rỉ.
- Ngưỡng quyết định chọn theo tỉ lệ chi phí `C_bỏsót : C_báonhầm = 10 : 1`, kèm **phân tích độ nhạy** 5:1 và 20:1.
- ⚠️ **Quy tắc 30 mẫu:** ngưỡng nào có < 30 ngày dương trong test thì metric phải kèm số mẫu + KTC bootstrap và **không được làm kết luận chính**. BĐ III gần như chắc rơi vào trường hợp này ⇒ lấy **≥ BĐ II làm ngưỡng chính**, BĐ III báo cáo dạng nghiên cứu trường hợp.
- Bổ sung **đánh giá theo đợt lũ** (1 đợt = 1 sự kiện, cửa sổ ±1 ngày) bên cạnh đánh giá theo ngày.

---

## 🟡 6. Chưa nói cách gộp mưa lưới thành đầu vào của mô hình

200 điểm lưới × nhiều biến ⇒ không thể nhét thẳng vào LightGBM. Cần chốt cách tổng hợp không gian:
- Mưa trung bình toàn lưu vực (đơn giản nhất), **hoặc**
- Trung bình theo trọng số Thiessen, **hoặc**
- Chia 3–5 tiểu lưu vực (thượng / trung / hạ) rồi lấy trung bình từng vùng ← *khuyên dùng, vừa gọn vừa giữ thông tin không gian*.

👉 Chốt ở **W3**, ghi vào `docs/DATA_SPLITS.md`.

---

## 🟡 7. Home server là điểm chết đơn lẻ

Kế hoạch ghi *"pipeline chạy hàng ngày trên home server"*. Mất điện / mất mạng đúng tuần thi là hỏng demo.

**Thay bằng:** **GitHub Actions cron** (chạy pipeline hằng ngày, miễn phí) + **Streamlit Community Cloud** (host dashboard, miễn phí). Home server chỉ là backup. Thêm **video demo quay sẵn** phòng mất mạng lúc thuyết trình.

---

## 🟡 8. Chưa có kế hoạch tái lập kết quả (reproducibility)

Giảng viên hỏi *"chạy lại có ra đúng số này không?"* là câu rất hay gặp.

Cần có:
- `requirements.txt` **ghim phiên bản chính xác** (`==`, không phải `>=`) — đã tạo sẵn.
- `SEED = 42` đặt ở một chỗ duy nhất trong `src/config.py`, dùng chung.
- `Makefile` với `make data`, `make train`, `make report` — đã tạo sẵn.
- `reports/experiments.csv` ghi lại **mọi lần chạy**: ngày, config, metric, commit hash.
- README có mục "Reproduce từ số 0" — viết ở **W8**.

---

## 🟡 9. Không có test — mà lỗi ETL là loại lỗi âm thầm nhất

Sai timezone 1 tiếng hoặc sai đơn vị mm/h ↔ mm/day sẽ **không báo lỗi**, chỉ làm kết quả sai lặng lẽ.

Tối thiểu 5 test trong `tests/`:
1. Đổi timezone UTC→ICT đúng (kiểm 1 mốc đã biết).
2. Resample mưa giờ→ngày: tổng 24 giá trị giờ = giá trị ngày.
3. Không có discharge âm.
4. Không có ngày trùng lặp trong panel.
5. Tạo lag feature **không rò rỉ tương lai** (kiểm bằng dữ liệu giả).

Test #5 quan trọng nhất — **rò rỉ dữ liệu (data leakage) là lỗi chí mạng** trong bài toán chuỗi thời gian.

---

## 🟡 10. Thi vấn đáp chấm cá nhân, nhưng phân công lại rất lệch

Xem `docs/TEAM.md` mục 4. Chuyên môn hoá vai trò là hợp lý về vận hành, nhưng **điểm thi chấm từng người**. Cơ chế bù: knowledge handoff thứ 7 + `EXPLAINER.md` + **2 lần mock exam (W6, W9)**. Đã đưa vào kế hoạch từ W1.

---

## 🟢 11. Việc hành chính dễ quên

- [ ] **Lấy ngày nộp thật của 4 report từ LMS** — mọi mốc trong `PLAN.md` hiện đang suy ra từ session number.
- [ ] **Báo giảng viên team 3 người** (kế hoạch gốc ghi 2 người) — làm ngay W1.
- [ ] Kiểm tra template báo cáo chính thức của trường (font, lề, cách trích dẫn) **trước** khi viết, đừng format lại ở phút chót.
- [ ] Hỏi rõ trường yêu cầu trích dẫn APA hay IEEE.
- [ ] Kiểm tra dung lượng ổ đĩa. Sau khi cắt scope (≈50 điểm × 2010–2026) ước còn **1–3 GB** Parquet, nhẹ hơn nhiều so với ước tính gốc.
- [ ] Ghi **citation cho Open-Meteo và GloFAS** đúng chuẩn CC BY 4.0 — bắt buộc, dễ bị trừ điểm.
- [ ] Thêm **disclaimer trên dashboard**: *"Sản phẩm học thuật, không phải cảnh báo chính thức. Cảnh báo chính thức xem tại Đài KTTV."* Bắt buộc với sản phẩm dự báo thiên tai công khai.

---

## 🟢 12. Phương án nếu một người nghỉ đột xuất

Kế hoạch gốc chỉ ghi *"mọi việc đều có tài liệu trong repo"* — chưa đủ cụ thể. Với lịch 9 tuần, mất một người một tuần là mất 11 % tổng quỹ thời gian:

| Vắng | Ảnh hưởng | Xử lý |
|---|---|---|
| **H** | Chậm khâu biên tập & format báo cáo | G viết nội dung thô, D format; cắt phần trau chuốt slide |
| **D** | Chậm EDA + dashboard | G gánh EDA, **cắt dashboard xuống 1 trang duy nhất** |
| **G** | **Nặng nhất** — mất cả pipeline lẫn model | Bắt buộc: `docs/RUNBOOK.md`, share credential, push code mỗi ngày, không giữ code chỉ trên máy cá nhân |

👉 `docs/RUNBOOK.md` là bảo hiểm quan trọng nhất của dự án này. Viết dần từ **W3**, hoàn thiện ở W8.
