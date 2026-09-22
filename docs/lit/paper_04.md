# Tóm tắt bài báo — paper_04 · ⭐ Hiệu chỉnh sai lệch GloFAS — bài số 2, có XAI

**Trích dẫn đầy đủ (APA):**
> Honcharenko, T., Dolhopolov, S., Neftissov, A., Kazambayev, I., Aubakirova, A., Kirichenko, L., & Kuchanskyi, O. (2026). Explainable Deep Ensemble Bias Correction of GloFAS-ERA5 Streamflow Across Snow-Influenced Transboundary Basins of Central Asia. *Water*, *18*(16), 2055. https://doi.org/10.3390/w18162055

**Link / DOI:** https://doi.org/10.3390/w18162055

**Người tóm tắt:** G  **Ngày:** 22/09/2026

---

## 1. Bài báo giải quyết vấn đề gì?

Hiệu chỉnh sai lệch GloFAS-ERA5 bằng **ensemble học sâu có giải thích được**, cho các lưu vực xuyên biên giới Trung Á chịu ảnh hưởng tuyết. Bổ sung cho paper_03 ở chỗ có thêm phần giải thích mô hình.

## 2. Dữ liệu họ dùng

| Nguồn | Khu vực | Khoảng thời gian | Độ phân giải |
|---|---|---|---|
| GloFAS-ERA5 + kho CA-discharge | **74 trạm** hệ thống Syr Darya & Amu Darya, Trung Á | ⚠️ khoảng thời gian cần kiểm | ngày |

## 3. Phương pháp

- Hiệu chỉnh **log-residual** của GloFAS-ERA5 (không hiệu chỉnh trực tiếp lưu lượng)
- Nền: LSTM *entity-aware* → **mixture of experts có cổng theo chế độ**
- Hàm mất mát: **CRPS** dạng đóng cho hỗn hợp; thêm ràng buộc vật lý về tuyết
- Lớp **conformal** (Mondrian) theo chế độ để cho khoảng tin cậy
- Đánh giá: temporal holdout · leave-one-basin-out · dự báo ở vùng không có trạm
- Giải thích: **grouped Shapley** (SHAP theo nhóm biến)

## 4. Kết quả chính

| Metric | Giá trị | So với baseline |
|---|---|---|
| KGE′ trung vị | **0,386 → 0,825** | GloFAS thô → sau hiệu chỉnh |
| Số trạm đạt kỹ năng dự báo | **74/74** | trước đó không phải trạm nào cũng đạt |

## 5. Hạn chế tác giả tự nêu

- Tác giả nêu thẳng: GloFAS-ERA5 **mất độ chính xác ở lưu vực đầu nguồn nhỏ**, nuôi bởi tuyết và băng — đúng kiểu giới hạn phân giải mà nhóm gặp
- Lưu vực chịu ảnh hưởng tuyết, khác hẳn mưa gió mùa

## 6. 👉 Liên hệ với dự án của nhóm

- **Dùng lại được:** cho thấy hiệu chỉnh GloFAS **kèm giải thích** là hướng đang được theo đuổi, đúng như `FR-V7` (SHAP) yêu cầu. Hai bài 03 + 04 cùng nhau đủ để định vị đóng góp của nhóm.
- **Khác họ:** lưu vực của họ chịu ảnh hưởng **tuyết**; lưu vực Hương là **mưa gió mùa, dốc, có triều và hồ chứa** — cơ chế sinh lũ khác hẳn, nên kết quả của họ không chuyển thẳng sang được.
- **Trích ở mục:** ⭐ Contribution · Interpretation (SHAP)

## 7. Câu trích dẫn nguyên văn

> "Global streamflow reanalyses such as GloFAS-ERA5 are available everywhere yet lose fidelity in small, snow- and glacier-fed headwaters" (Honcharenko et al., 2026, abstract)

> "Correction rendered all 74 gauges skillful, raising the median modified Kling–Gupta efficiency (KGE′) from 0.386 (raw) to 0.825" (như trên)

PDF: `docs/lit/pdf/paper_04_Honcharenko_2026_explainable_bias_correction.pdf` (mở, CC BY)
