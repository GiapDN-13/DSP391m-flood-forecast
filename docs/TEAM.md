# TEAM & PHÂN CÔNG — DSP391m (3 người)

> Đề tài: **Dự báo nguy cơ lũ 1–3 ngày cho các xã ven đô TP. Huế từ dữ liệu khí tượng – thủy văn mở**
> Kế hoạch gốc viết cho team 2 người → bản này tái phân bổ cho **3 người**.

## 1. Thành viên & vai trò

| Ký hiệu | Tên | Vai trò chính | Tỉ trọng mục tiêu | Giờ/tuần dự kiến |
|---|---|---|---|---|
| **G** | Giáp (bạn) | **Tech Lead** – Data Engineering + Modeling + tích hợp + review | **50 %** | 10–12 h |
| **D** | Đức | **Data Analyst** – EDA, feature engineering, baseline model, dashboard | **32 %** | 6–8 h |
| **H** | Huyền | **Research & Documentation Lead** – literature review, data dictionary, viết & format báo cáo, slide, biên bản họp | **18 %** | 3–4 h |

Tổng 100 %. Con số này được **ghi vào `docs/CONTRIBUTION_LOG.md` mỗi tuần** để có bằng chứng khi giảng viên chấm đóng góp cá nhân.

## 2. Nguyên tắc phân công

### Giáp (G) — người gánh phần nặng & rủi ro cao
Nhận mọi việc **có thể fail giữa chừng** hoặc **cần debug lâu**:
- Crawl API 40 năm, xử lý rate-limit, retry, cache.
- Chọn đúng ô lưới GloFAS trên sông Hương / sông Bồ.
- Pipeline ETL → Parquet, DuckDB/Polars.
- Mô hình chính (LightGBM), walk-forward validation, Optuna.
- Chủ repo: review 100 % PR, giữ `main` sạch.
- Mentor Đức 30 phút/tuần (pair-programming).

### Đức (D) — việc có scope rõ, có template sẵn
Nguyên tắc: **G luôn đưa Đức một issue đã mô tả rõ input – output – tiêu chí xong**, không giao việc mơ hồ.
- EDA theo checklist có sẵn (mùa vụ, tương quan mưa–lưu lượng theo lag).
- Feature engineering từ danh sách feature G đã liệt kê sẵn.
- Baseline models (persistence, seasonal naive, ARIMA) — dễ, có công thức rõ.
- Trang Streamlit theo wireframe G vẽ trước.
- Chạy thí nghiệm theo script G viết, ghi kết quả vào bảng.

> Nếu Đức stuck > 45 phút → bắt buộc comment vào issue, **không được im lặng**. Đây là rule cứng.

### Huyền (H) — việc nhẹ, không deadline gấp, làm async 100 %
Nguyên tắc chọn việc cho Huyền:
1. **Không phụ thuộc thời gian thực** — không trực pipeline, không on-call, không debug gấp.
2. **Chủ yếu là đọc – viết – tổ chức thông tin**, làm được từ nhà, chia nhỏ 30–45 phút/lần.
3. **Deadline nội bộ luôn sớm hơn deadline thật 3–4 ngày** để có đệm.
4. **Không bao giờ là single point of failure** — mọi việc của H đều có G backup.
5. Việc của H vẫn là **việc thật, ăn điểm thật** (Report 1 = 10 %, Report 4 = 10 %, slide) chứ không phải việc phụ cho có.

Danh sách việc của H:
- Literature review 6 bài (có template tóm tắt sẵn `docs/templates/PAPER_SUMMARY.md`).
- Viết Problem statement / Objectives / Methodology (Report 1).
- Data dictionary: mô tả cột, đơn vị, nguồn, khoảng giá trị — G cung cấp `df.describe()`, H diễn giải thành bảng.
- Biên bản họp (2 buổi/tuần, mỗi buổi 10 phút ghi).
- Format & gộp báo cáo, kiểm tra citation (Zotero), mục lục, caption hình/bảng.
- Slide thuyết trình (30 phút) + script nói.
- Checklist QA trước mỗi lần nộp.

**Trao đổi trước, đừng giả định:** hỏi thẳng Huyền dạng tài liệu nào dễ làm nhất (Word / Google Docs / Markdown), có cần phụ đề khi họp online không, có cần tăng thời gian không. Ghi lại thoả thuận vào mục 6 bên dưới.

## 3. Bảng RACI theo hạng mục

| Hạng mục | G | D | H |
|---|---|---|---|
| Crawl API + ETL | **R/A** | C | I |
| Chọn ô lưới GloFAS | **R/A** | C | I |
| EDA | C | **R** | I |
| Feature engineering | **A** | **R** | I |
| Baseline models | C | **R** | I |
| LightGBM / LSTM | **R/A** | C | I |
| Walk-forward + tuning | **R/A** | C | I |
| Dashboard Streamlit | **A** | **R** | C (nội dung chữ) |
| Literature review | C | C | **R/A** |
| Report 1 | C | C | **R/A** |
| Report 2 | **R** (Data Collection) | **R** (EDA) | **A** (gộp + format) |
| Report 3 | **R/A** | C | **R** (format + chỉnh văn) |
| Report 4 (final) | C | C | **R/A** |
| Slide + luyện nói | C | C | **R/A** |
| Biên bản họp | I | I | **R/A** |

R = làm · A = chịu trách nhiệm cuối · C = được hỏi ý kiến · I = được thông báo

## 4. Thi cuối kỳ chấm CÁ NHÂN (20 %) — rủi ro lớn nhất

Syllabus ghi rõ: **30 phút, chấm cá nhân, mỗi người phải nắm toàn bộ dự án**.
Chia việc lệch ⇒ nếu không có cơ chế chia sẻ kiến thức thì Đức và Huyền sẽ **mất điểm dù dự án tốt**.

Cơ chế bắt buộc:
- **Knowledge handoff 20 phút mỗi thứ Bảy**: G trình bày 1 phần kỹ thuật, H viết lại thành 1 trang trong `docs/EXPLAINER.md`. Viết lại = học. Một mũi tên trúng 2 đích.
- Từ tuần 10: **mock exam luân phiên**, mỗi người bốc 3 câu hỏi từ `docs/EXAM_QUESTION_BANK.md` và trả lời trong 5 phút.
- Ngân hàng câu hỏi tích luỹ dần từ tuần 1 — cứ gặp khái niệm mới thì thêm 1 câu.

## 5. Quy tắc họp

| Buổi | Thời gian | Nội dung | Ghi biên bản |
|---|---|---|---|
| Họp chính | Thứ 4, 30 phút | Tiến độ, blocker, việc tuần tới | H |
| Standup ngắn | Chủ nhật, 15 phút (chat cũng được) | Chốt việc tuần | H |
| Knowledge handoff | Thứ 7, 20 phút | G giảng, D+H hỏi | H |
| Pair-programming G–D | Linh hoạt, 30 phút | Gỡ rối code cho Đức | — |

Huyền chỉ **bắt buộc** dự họp chính; 2 buổi còn lại tham gia nếu tiện, có ghi âm/ghi chú bù.

## 6. Thoả thuận hỗ trợ (điền sau khi hỏi Huyền)

- Định dạng tài liệu thuận tiện nhất: _______
- Kênh liên lạc ưu tiên (chat / voice / email): _______
- Thời lượng làm việc liên tục tối đa mỗi phiên: _______
- Cần hỗ trợ gì khi thuyết trình (ngồi nói, dùng slide-notes, thời gian thêm): _______
- Đã báo giảng viên để xin điều kiện thi phù hợp chưa? ☐ Chưa ☐ Rồi, ngày: ______
