# Tóm tắt bài báo — paper_03 · ⭐ Hiệu chỉnh sai lệch GloFAS bằng học máy — bài số 1

**Trích dẫn đầy đủ (APA):**
> Nourani, V., Kheirieh, S., Kantoush, S. A., & Huang, J. J. (2026). Bias correction of Global Flood Awareness System (GloFAS) data for multi-station river flow prediction by ensemble modelling. *Engineering Applications of Computational Fluid Mechanics*, *20*(1), 2665857. https://doi.org/10.1080/19942060.2026.2665857

**Link / DOI:** https://www.tandfonline.com/doi/full/10.1080/19942060.2026.2665857

**Người tóm tắt:** G  **Ngày:** 22/09/2026

---

## 1. Bài báo giải quyết vấn đề gì?

Đúng bài toán của nhóm: **GloFAS-ERA5 lệch so với dòng chảy thật**, và bài đề xuất hiệu chỉnh sai lệch bằng mô hình học máy đa trạm. Làm ở lưu vực Ajichai, tây bắc Iran.

## 2. Dữ liệu họ dùng

| Nguồn | Khu vực | Khoảng thời gian | Độ phân giải |
|---|---|---|---|
| GloFAS-ERA5 | 3 trạm Sahzab, Mirkuh, Markid — lưu vực Ajichai, Iran | lưu lượng thực đo **1993–2024** | ngày |
| Mưa + nhiệt trạm địa phương & ERA5 | cùng lưu vực | 1993–2024 | ngày |

## 3. Phương pháp

- Mô hình: FFNN, ANFIS, SVR, LSTM, và **ensemble phi tuyến Neural Averaging (NA)**
- Chạy nhiều kịch bản dùng GloFAS **thô** và GloFAS **đã hiệu chỉnh sai lệch**
- Chiến lược **đa trạm**: đưa lưu lượng thượng nguồn (Sahzab, Mirkuh) vào để dự báo hạ nguồn (Markid)
- Chia: calibration / verification

## 4. Kết quả chính

| Metric | Giá trị | So với baseline |
|---|---|---|
| Ensemble **NA** | vượt mọi mô hình ML đơn lẻ | |
| RMSE tại Markid, đa trạm vs đơn trạm | **−2,2 %** (calibration) · **−9,4 %** (verification) | |
| Chỉ số dùng | RMSE và DC (hệ số xác định) | |

## 5. Hạn chế tác giả tự nêu

- Sai lệch của GloFAS gắn với **độ phân giải không gian** — tác giả nêu thẳng trong abstract
- Chỉ 3 trạm, một lưu vực

## 6. 👉 Liên hệ với dự án của nhóm

- **Dùng lại được:** đây là **bài gần đề tài nhóm nhất** trong cả 6 bài. Nó xác nhận (a) GloFAS-ERA5 có sai lệch cần hiệu chỉnh, và (b) học máy là cách hiệu chỉnh hợp lệ — chính là `RESEARCH_DESIGN.md` §1.2.
- **Khác họ:** họ có **3 trạm đo thật** để hiệu chỉnh về. Nhóm **không có trạm nào**, nên không hiệu chỉnh về dòng chảy thật được, chỉ dự báo chính chuỗi GloFAS. Đây là hạn chế lớn nhất của nhóm và bài này làm nổi bật nó.
- **Trích ở mục:** ⭐ Contribution · Methodology · Limitations

## 7. Câu trích dẫn nguyên văn

> "The Global Flood Awareness System (GloFAS) is a promising flood-modelling tool available for most river basins worldwide. However, it contains inherent biases, notably linked to its spatial resolution." (Nourani et al., 2026, abstract)

PDF: `docs/lit/pdf/paper_03_Nourani_2026_GloFAS_bias_correction.pdf`
