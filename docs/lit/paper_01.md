# Tóm tắt bài báo — paper_01 · ML dự báo lưu lượng (cây tăng cường) + XAI

**Trích dẫn đầy đủ (APA):**
> Gnjato, S., Leščešen, I., Zhou, X., & Đukanović, D. (2026). Explainable Machine Learning for Streamflow Forecasting: Application to the Bosna River Basin. *Water*, *18*(10), 1226. https://doi.org/10.3390/w18101226

**Link / DOI:** https://www.mdpi.com/2073-4441/18/10/1226

**Người tóm tắt:** G  **Ngày:** 22/09/2026

---

## 1. Bài báo giải quyết vấn đề gì?

Dự báo lưu lượng lưu vực sông Bosna (Bosnia & Herzegovina) — nơi trước đó chưa có nghiên cứu ML nào về dòng chảy. Bài so ba mô hình và dùng công cụ XAI để giải thích, thay vì chỉ báo cáo điểm số.

## 2. Dữ liệu họ dùng

| Nguồn | Khu vực | Khoảng thời gian | Độ phân giải |
|---|---|---|---|
| Trạm khí tượng + thuỷ văn | Lưu vực sông Bosna | 1961–2020 | ngày |

## 3. Phương pháp

- Mô hình: **Random Forest**, LSTM, XGBoost
- Feature chính: biến khí tượng từ 5 trạm khí tượng + 1 trạm thuỷ văn
- Chia train/test: ⚠️ CẦN KIỂM khi đọc toàn văn

## 4. Kết quả chính

| Metric | Giá trị | So với baseline |
|---|---|---|
| Mô hình tốt nhất | **Random Forest** | vượt LSTM và XGBoost |
| Số liệu định lượng | ⚠️ CẦN KIỂM | |

## 5. Hạn chế tác giả tự nêu

- Chuỗi dài nhưng chỉ **một** trạm thuỷ văn
- ⚠️ phần còn lại CẦN KIỂM khi đọc toàn văn

## 6. 👉 Liên hệ với dự án của nhóm

- **Dùng lại được:** chỗ dựa cho việc nhóm chọn cây tăng cường (LightGBM) thay vì LSTM — RF/XGBoost thắng LSTM ở lưu vực vừa, dữ liệu vừa. Khớp với lập luận cắt LSTM khỏi phạm vi chính từ W1.
- **Khác họ:** họ có trạm thuỷ văn thật; nhóm chỉ có **lưu lượng mô phỏng** GloFAS. Khác biệt này phải nêu ở Limitations.
- **Trích ở mục:** Methodology (vì sao chọn LightGBM) · Interpretation (tiền lệ dùng XAI)

## 7. Câu trích dẫn nguyên văn

> "first application of machine learning methods for streamflow forecasting in Bosnia and Herzegovina" ⚠️ cần số trang
