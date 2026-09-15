# THIẾT KẾ NGHIÊN CỨU — đóng góp, kịch bản đánh giá, xử lý mất cân bằng

Tài liệu này chốt 3 quyết định khoa học (GAPS #3, #4, #5). Dùng lại nguyên văn cho Report 1 mục *Contribution* (viết ở W2) và Report 3 mục *Methodology*.

---

# 1. Định vị đóng góp — trả lời "sao không dùng thẳng GloFAS?"

## 1.1 Thực trạng phải thừa nhận thẳng

Open-Meteo Flood API **đã có sẵn dự báo lưu lượng 7 ngày** từ GloFAS v4. Nếu nhóm giấu chuyện này đi thì sẽ bị bắt lỗi; nếu nêu ra mà không có đóng góp rõ ràng thì đề tài mất giá trị. Cách xử lý đúng: **nêu ra ngay từ Report 1, và định vị dự án là lớp bổ sung nằm TRÊN GloFAS chứ không phải đối thủ của GloFAS.**

> **Câu định vị dùng xuyên suốt 4 báo cáo và lúc thuyết trình:**
> *"Nghiên cứu này không nhằm thay thế GloFAS, mà **hiệu chỉnh và bản địa hoá** đầu ra của GloFAS thành cảnh báo theo **cấp báo động BĐ I/II/III của Việt Nam** ở quy mô tiểu lưu vực sông Hương – sông Bồ."*

## 1.2 Ba đóng góp cụ thể

### Đóng góp 1 — Hiệu chỉnh sai số cục bộ (bias correction / statistical post-processing) ⭐ chính

GloFAS là mô hình **toàn cầu**, lưới ~5 km, hiệu chuẩn cho lưu vực lớn. Sông Hương (~2 830 km²) và sông Bồ (~938 km²) là lưu vực **nhỏ, dốc, lũ lên nhanh, do bão và gió mùa đông bắc**, đúng loại mà mô hình toàn cầu thường sai nhiều nhất.

- **Đầu vào:** dự báo GloFAS thô tại horizon h **+** mưa dự báo **+** trạng thái lưu vực quá khứ.
- **Đầu ra:** lưu lượng đã hiệu chỉnh.
- **Chứng minh:** so RMSE / MAE / NSE / KGE giữa *GloFAS thô* và *GloFAS đã hiệu chỉnh* trên cùng tập test 07/2022–2026.
- Đây là hướng đã có nền tảng trong tài liệu (statistical post-processing of ensemble streamflow forecasts) → H tìm 2 bài về hướng này cho literature review ở W1.

> 🔴 **CẬP NHẬT 15/09/2026 — lập luận dưới đây KHÔNG thực hiện được.**
>
> ~~Dự báo GloFAS thô vừa là BASELINE, vừa là FEATURE đầu vào của mô hình.~~
>
> Open-Meteo **không có kho lưu trữ dự báo lưu lượng quá khứ** (`historical-forecast-api.../flood` → 404). Không có dự báo GloFAS quá khứ thì **không có cột feature đó trong tập huấn luyện**. Dùng chuỗi *phân tích* GloFAS tại t+h thay thế là **rò rỉ dữ liệu trắng trợn** — tuyệt đối không làm.
>
> **Thay bằng:** đối chứng với persistence / climatology / ARIMA trên lịch sử, và đối chứng với GloFAS thô trên phần `reports/forecast_log/` tích luỹ từ W1. Chi tiết: `FINDINGS_BASELINE.md` §2.

### Đóng góp 2 — Ánh xạ sang hệ cấp báo động của Việt Nam

GloFAS phát ngưỡng theo **chu kỳ lặp lại 2 / 5 / 20 năm** — một hệ quy chiếu **không trùng** với BĐ I/II/III mà chính quyền và người dân Việt Nam đang dùng. Việc quy đổi sang BĐ (quy trình ở `docs/THRESHOLDS.md`) là đóng góp thật, dùng được ngay, và chưa có sẵn trong sản phẩm gốc.

### Đóng góp 3 — Bản địa hoá không gian + khả năng giải thích

- Cảnh báo theo **tiểu lưu vực / xã**, không phải theo ô lưới 5 km vô danh.
- **SHAP** cho biết cảnh báo hôm nay đến từ đâu (mưa thượng nguồn 2 ngày trước? nền ẩm cao sẵn?). GloFAS với người dùng địa phương là hộp đen.

## 1.3 Điều KHÔNG được tuyên bố

Để tránh bị bắt lỗi khi vấn đáp, nhóm **không** tuyên bố:

- ❌ "Mô hình của chúng tôi chính xác hơn GloFAS" — nói đúng: *chính xác hơn GloFAS thô **trên lưu vực này, trên tập test này***.
- ❌ "Có thể dùng để cảnh báo thiên tai" — luôn kèm disclaimer sản phẩm học thuật.
- ❌ "Dự báo lũ" chung chung — nói đúng: *dự báo lưu lượng và cấp báo động 1–3 ngày*.

---

# 2. Hai kịch bản đánh giá — xử lý lệch phân phối train/vận hành

## 2.1 Vấn đề

Mô hình train bằng **mưa ERA5 (reanalysis, gần như quan trắc)** nhưng khi chạy thật phải dùng **mưa dự báo**. Mưa dự báo sai hơn nhiều, nhất là mưa lớn do bão — đúng tình huống mà nhóm quan tâm nhất. Báo cáo chỉ số đẹp từ ERA5 rồi triển khai bằng mưa dự báo là **tự lừa mình**, và là lỗi phổ biến nhất trong các đồ án dự báo thuỷ văn.

## 2.2 Giải pháp — báo cáo song song hai kịch bản

| | **Kịch bản A — Cận trên lý tưởng** | **Kịch bản B — Vận hành thực tế** |
|---|---|---|
| Mưa đầu vào | ERA5 reanalysis (quan trắc) | Mưa **dự báo** tại thời điểm phát báo |
| Trả lời câu hỏi | *Nếu biết chính xác mưa sẽ rơi, mô hình tốt đến đâu?* | *Hằng ngày, sản phẩm thật chạy tốt đến đâu?* |
| Dùng ở đâu | Đánh giá khả năng học của mô hình | **Con số chính thức đưa vào kết luận** |

**Δ = hiệu năng(A) − hiệu năng(B)** là một kết quả có giá trị riêng: nó đo **bao nhiêu phần sai số đến từ dự báo mưa chứ không phải từ mô hình của nhóm**. Đây là loại phân tích làm báo cáo trông chuyên nghiệp hơn hẳn.

## 2.3 Lấy mưa dự báo quá khứ ở đâu

Open-Meteo có **Historical Forecast API** (`historical-forecast-api.open-meteo.com`) lưu trữ **các bản dự báo đã phát từ 2021 đến nay** — tức là đúng thứ cần: *"ngày 05/10/2022 người ta đã dự báo mưa 3 ngày tới là bao nhiêu"*.

May mắn là kho này **phủ trọn tập test 07/2022–2026** của nhóm. Vì vậy:

- **Train + validation** (2010 → 06/2022): dùng ERA5.
- **Test** (07/2022 → 2026): chạy **cả A và B**, báo cáo cả hai.

Nếu kho lưu trữ không đủ dày cho một horizon nào đó → ghi rõ, và làm **kịch bản B′ giả lập**: nhiễu hoá mưa ERA5 theo phân phối sai số của dự báo mưa đã đo được, rồi đánh giá độ nhạy. Kém hơn B thật, nhưng vẫn hơn là im lặng.

## 2.4 Bảng kết quả bắt buộc trong Report 3

| Mô hình | Horizon | RMSE (A) | RMSE (B) | Δ | NSE (A) | NSE (B) |
|---|---|---|---|---|---|---|
| GloFAS thô (baseline) | 1/2/3 | | | | | |
| Persistence | 1/2/3 | | | | | |
| Seasonal naive | 1/2/3 | | | | | |
| ARIMA | 1/2/3 | | | | | |
| **LightGBM (nhóm)** | 1/2/3 | | | | | |
| LSTM *(chỉ nếu W8 còn thời gian)* | 1/2/3 | | | | | |

---

# 3. Xử lý mất cân bằng lớp

## 3.1 Quy mô vấn đề

| Ngưỡng | Tỉ lệ ngày dương ước tính | Số ngày dương dự kiến trong test (~1 520 ngày) |
|---|---|---|
| ≥ BĐ I | 1–3 % | ~15–45 |
| ≥ BĐ II | 0,3–1 % | ~5–15 |
| ≥ BĐ III | < 0,3 % | **có thể chỉ 2–5** |

Đoán "không bao giờ có lũ" đã đạt accuracy ~98 %. **Accuracy bị cấm dùng trong mọi báo cáo của nhóm.**

## 3.2 Bộ metric chốt

| Metric | Công thức | Vì sao dùng |
|---|---|---|
| **POD** (recall / hit rate) | TP / (TP+FN) | Bắt được bao nhiêu phần trăm số đợt lũ thật |
| **FAR** | FP / (TP+FP) | Báo động nhầm bao nhiêu — liên quan niềm tin của dân |
| **CSI** (threat score) | TP / (TP+FP+FN) | Chỉ số tổng hợp chuẩn của ngành khí tượng thuỷ văn |
| **F1** | — | Để so với tài liệu ML |
| **PR-AUC** | — | Không phụ thuộc ngưỡng quyết định; **luôn dùng thay ROC-AUC** khi lớp hiếm |
| **Brier score** + reliability diagram | — | Xác suất phát ra có đáng tin không |

## 3.3 Kỹ thuật xử lý

1. **`scale_pos_weight = n_âm / n_dương`** trong LightGBM. Đơn giản, hiệu quả, không sinh dữ liệu giả.
2. **Không dùng SMOTE.** Sinh mẫu tổng hợp trên chuỗi thời gian phá vỡ cấu trúc thời gian và dễ gây rò rỉ. Nếu có ai hỏi tại sao không dùng — đây là câu trả lời.
3. **Chọn ngưỡng quyết định theo chi phí**, không lấy mặc định 0,5:
   - Đặt tỉ lệ chi phí `C_bỏsót : C_báonhầm = 10 : 1` (bỏ sót một trận lũ nguy hiểm hơn nhiều so với báo động thừa).
   - Quét ngưỡng trên đường PR của tập validation, chọn điểm tối thiểu hoá chi phí kỳ vọng.
   - **Làm phân tích độ nhạy** với tỉ lệ 5:1 và 20:1 để chứng minh kết luận không phụ thuộc con số 10 tự chọn.
4. **Hiệu chỉnh xác suất** (isotonic regression trên validation) trước khi vẽ reliability diagram.

## 3.4 Ràng buộc trung thực — quy tắc 30 mẫu

> Nếu một ngưỡng có **dưới 30 ngày dương trong tập test**, mọi metric của nó **phải đi kèm số mẫu và khoảng tin cậy bootstrap**, và **không được dùng làm kết luận chính**.

Với BĐ III gần như chắc chắn rơi vào trường hợp này. Xử lý:

- Lấy **≥ BĐ II làm ngưỡng chính** cho phần kết luận và khuyến nghị.
- BĐ III báo cáo dạng **nghiên cứu trường hợp** (đúng/sai trên từng đợt cụ thể), không quy thành tỉ lệ phần trăm.
- Bổ sung đánh giá theo **đợt lũ (event-based)** thay vì theo ngày: một đợt lũ kéo dài 4 ngày tính là **1 sự kiện**, mô hình được coi là bắt được nếu cảnh báo đúng trong cửa sổ ±1 ngày. Cách đếm này gần với cách cơ quan phòng chống thiên tai đánh giá thực tế hơn, và tránh thổi phồng số mẫu.

## 3.5 Nói thẳng trong Limitations

Chuỗi test 4 năm chỉ chứa vài sự kiện cực đoan ⇒ **không đủ mẫu để kết luận mạnh về lũ lớn**. Đây là hạn chế cố hữu của bài toán, không phải lỗi của nhóm — nêu ra sẽ được đánh giá cao hơn là che đi.
