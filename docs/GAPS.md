# NHỮNG THỨ KẾ HOẠCH GỐC CÒN THIẾU — và cách bù

Xếp theo mức độ nguy hiểm. Mục 1–5 nếu không xử lý thì **sẽ bị hỏi và bị trừ điểm khi vấn đáp**.

---

## 🔴 1. Không có định nghĩa "ngưỡng báo động lũ" — mà đây là biến mục tiêu của bài toán phân loại

**Vấn đề:** Câu hỏi nghiên cứu #2 là *"mô hình phân loại ngày vượt ngưỡng báo động lũ"*, nhưng kế hoạch không nói ngưỡng đó là gì.
Ngưỡng báo động BĐ I/II/III của Việt Nam được định nghĩa theo **mực nước (m)** tại trạm Kim Long (sông Hương) và Phú Ốc (sông Bồ). Trong khi đó GloFAS chỉ cho **lưu lượng (m³/s)**. **Hai đơn vị khác nhau, không quy đổi trực tiếp được** nếu không có đường quan hệ mực nước – lưu lượng (rating curve).

**Cách xử lý (chọn 1, ghi rõ trong báo cáo):**

- **Phương án A (khuyên dùng, chắc chắn làm được):** định nghĩa ngưỡng theo **phân vị lịch sử của chính chuỗi GloFAS** — ví dụ Q95 / Q98 / Q99.5 của discharge mùa lũ, gọi tên là "mức nguy cơ 1/2/3". Nêu rõ **đây là ngưỡng thống kê thay thế (proxy), không phải ngưỡng pháp lý**.
- **Phương án B (điểm cao hơn, nếu xin được số liệu Đài KTTV):** dựng rating curve từ cặp (mực nước, lưu lượng) quan trắc, rồi ánh xạ BĐ I/II/III sang m³/s.
- **Phương án C (đối chiếu định tính):** lấy ngày lũ lịch sử từ báo chí / báo cáo phòng chống thiên tai (1999, 2020, 2023) để kiểm tra ngưỡng chọn có "bắt" đúng các đợt đó không.

👉 Làm A + C ngay từ W05, B là bonus. Ghi kết quả vào `docs/THRESHOLDS.md`.

---

## 🔴 2. Ranh giới xã đã thay đổi — bản đồ "theo xã" có thể sai hoàn toàn

**Vấn đề:** Sản phẩm cuối là *"bản đồ nguy cơ theo xã"*, nhưng địa giới hành chính Việt Nam đã thay đổi lớn: Thừa Thiên Huế trở thành **thành phố Huế trực thuộc trung ương**, và cả nước **bỏ cấp huyện, sắp xếp lại cấp xã từ 01/07/2025**. Mọi file GeoJSON xã tải trước 2025 đều **không còn đúng**.

**Cách xử lý:**
- Tải GeoJSON cấp xã **phiên bản sau 01/07/2025** (nguồn: cổng dữ liệu mở của Cục Đo đạc Bản đồ, hoặc OpenStreetMap trích xuất mới).
- Ghi rõ **ngày phiên bản ranh giới** trong data dictionary.
- Nếu không tìm được bản mới kịp → **đổi đơn vị không gian sang "tiểu lưu vực" hoặc "ô lưới 5 km"** thay vì xã, và giải thích lý do. Tiểu lưu vực thực ra **hợp lý hơn về mặt thuỷ văn**, vì nước chảy theo lưu vực chứ không theo địa giới.

👉 Giao Đức khảo sát ngay W04, đừng để tới W11 mới phát hiện.

---

## 🔴 3. Chưa trả lời được: "Tại sao không dùng thẳng dự báo của GloFAS?"

**Vấn đề:** Open-Meteo Flood API **đã có sẵn dự báo lưu lượng 7 ngày**. Nếu mô hình của team không tốt hơn cái đó, giảng viên sẽ hỏi ngay: *dự án này đóng góp gì?*

**Cách xử lý — bắt buộc có trong Report 3:**
- Đặt **dự báo GloFAS gốc làm baseline thứ 4** (cạnh persistence / seasonal naive / ARIMA), so trên cùng tập test.
- Định vị đóng góp rõ ràng, chọn 1–2 hướng:
  1. **Hiệu chỉnh sai số cục bộ (bias correction / post-processing)** cho lưu vực sông Hương – sông Bồ — đây là đóng góp hợp lệ và dễ chứng minh nhất.
  2. **Chuyển từ dự báo lưu lượng sang cảnh báo mức nguy cơ theo xã** — thứ GloFAS không cung cấp.
  3. **Giải thích được bằng SHAP** — GloFAS là hộp đen với người dùng địa phương.

👉 Viết 1 đoạn "Contribution" vào Report 1 ngay từ W02, đừng để tới W12.

---

## 🟠 4. Lệch phân phối giữa lúc train và lúc chạy thật

**Vấn đề:** Train bằng **mưa ERA5 (quan trắc/reanalysis)**, nhưng khi chạy dự báo hằng ngày lại phải dùng **mưa từ Forecast API (dự báo)**. Mưa dự báo sai hơn mưa quan trắc rất nhiều → mô hình chạy thật sẽ tệ hơn kết quả trong báo cáo, đôi khi tệ hơn nhiều.

**Cách xử lý:**
- Ở phần đánh giá, làm **2 kịch bản**: (a) dùng mưa quan trắc — *cận trên lý tưởng*; (b) dùng mưa dự báo — *hiệu năng thực tế*. Báo cáo cả hai.
- Nếu kịp: train thêm 1 bản dùng mưa dự báo quá khứ làm input.
- Tối thiểu: **nêu rõ hạn chế này trong Limitations** — chỉ cần nhận ra vấn đề đã ăn điểm.

---

## 🟠 5. Mất cân bằng lớp nghiêm trọng ở bài toán phân loại

**Vấn đề:** Ngày vượt ngưỡng báo động chỉ chiếm khoảng **1–3 %** số ngày. Accuracy 97 % là vô nghĩa (đoán "không lũ" mọi ngày cũng được 97 %).

**Cách xử lý:**
- **Không báo cáo accuracy.** Dùng: **POD (recall), FAR, CSI, F1, PR-AUC, Brier score**.
- Xử lý mất cân bằng: `scale_pos_weight` trong LightGBM, hoặc focal loss, hoặc điều chỉnh ngưỡng quyết định theo đường PR.
- Chọn ngưỡng quyết định theo **chi phí thực tế**: bỏ sót một trận lũ nguy hiểm hơn nhiều so với báo động nhầm → ưu tiên recall cao.
- Vẽ **reliability diagram** nếu xuất ra xác suất.

---

## 🟡 6. Chưa nói cách gộp mưa lưới thành đầu vào của mô hình

200 điểm lưới × nhiều biến ⇒ không thể nhét thẳng vào LightGBM. Cần chốt cách tổng hợp không gian:
- Mưa trung bình toàn lưu vực (đơn giản nhất), **hoặc**
- Trung bình theo trọng số Thiessen, **hoặc**
- Chia 3–5 tiểu lưu vực (thượng / trung / hạ) rồi lấy trung bình từng vùng ← *khuyên dùng, vừa gọn vừa giữ thông tin không gian*.

👉 Chốt ở W05, ghi vào `docs/DATA_SPLITS.md`.

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
- README có mục "Reproduce từ số 0" — viết ở W13.

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

Đây là rủi ro riêng của team này (xem `docs/TEAM.md` mục 4). Chia việc lệch là hợp lý về mặt vận hành, nhưng **điểm thi thì chấm từng người**. Cơ chế bù: knowledge handoff thứ 7 + `EXPLAINER.md` + 3 lần mock exam. Đã đưa vào kế hoạch từ W01.

---

## 🟢 11. Việc hành chính dễ quên

- [ ] **Báo giảng viên team 3 người** (kế hoạch gốc ghi 2 người) — làm ngay W01.
- [ ] **Hỏi giảng viên / phòng đào tạo về điều kiện thi phù hợp cho Huyền** — làm sớm, thủ tục thường mất thời gian.
- [ ] Kiểm tra template báo cáo chính thức của trường (font, lề, cách trích dẫn) **trước** khi viết, đừng format lại ở phút chót.
- [ ] Hỏi rõ trường yêu cầu trích dẫn APA hay IEEE.
- [ ] Kiểm tra dung lượng ổ đĩa: ~70 triệu bản ghi dạng Parquet ≈ **5–15 GB**. Kiểm tra ổ E: còn đủ chỗ trước khi crawl.
- [ ] Ghi **citation cho Open-Meteo và GloFAS** đúng chuẩn CC BY 4.0 — bắt buộc, dễ bị trừ điểm.
- [ ] Thêm **disclaimer trên dashboard**: *"Sản phẩm học thuật, không phải cảnh báo chính thức. Cảnh báo chính thức xem tại Đài KTTV."* Bắt buộc với sản phẩm dự báo thiên tai công khai.

---

## 🟢 12. Phương án nếu một người nghỉ đột xuất

Kế hoạch gốc chỉ ghi *"mọi việc đều có tài liệu trong repo"* — chưa đủ cụ thể với team 3 người lệch tải:

| Ai nghỉ | Ảnh hưởng | Xử lý |
|---|---|---|
| Huyền | Chậm khâu viết/format | G viết nội dung thô, D format; cắt bớt phần trau chuốt |
| Đức | Chậm EDA + dashboard | G gánh EDA, **cắt dashboard xuống 1 trang duy nhất** |
| Giáp | **Nguy hiểm nhất** — mất cả pipeline lẫn model | Bắt buộc: G viết `docs/RUNBOOK.md` (cách chạy lại mọi thứ), share credential, push code mỗi ngày, không giữ code trên máy cá nhân |

👉 `docs/RUNBOOK.md` là bảo hiểm quan trọng nhất của dự án này. Viết dần từ W04.
