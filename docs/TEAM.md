# TEAM & PHÂN CÔNG — DSP391m

> Đề tài: **Dự báo nguy cơ lũ 1–3 ngày cho các xã ven đô TP. Huế từ dữ liệu khí tượng – thủy văn mở**
> Kế hoạch gốc viết cho team 2 người → bản này tái phân bổ cho **3 người trong 9 tuần**.

## 1. Thành viên & vai trò

| Ký hiệu | Tên | Vai trò | Tỉ trọng | Giờ/tuần |
|---|---|---|---|---|
| **G** | Giáp | **Tech Lead** — Data Engineering, Modeling, tích hợp, review | **50 %** | 14–16 h |
| **D** | Đức | **Data Analyst** — EDA, feature engineering, baseline, dashboard | **32 %** | 9–11 h |
| **H** | Huyền | **Research & Documentation Lead** — literature review, nguồn pháp lý, data dictionary, biên tập & format 4 báo cáo, slide | **18 %** | 5–6 h |

Ghi vào `docs/CONTRIBUTION_LOG.md` mỗi tuần để có bằng chứng khi giảng viên chấm đóng góp cá nhân.

> ⚠️ Lịch 9 tuần nên **giờ/tuần cao hơn bình thường**. Nếu thực tế không kham nổi thì **cắt scope** theo `docs/RISKS.md`, đừng kéo dài deadline — deadline là cứng.

## 2. Nguyên tắc phân công

### G — Tech Lead
Nhận mọi việc **có thể fail giữa chừng** hoặc **cần debug lâu**:
- Crawl API, xử lý rate-limit, retry, checkpoint.
- Chọn đúng ô lưới GloFAS trên sông Hương / sông Bồ.
- Pipeline ETL → Parquet, Polars/DuckDB.
- Ánh xạ mực nước → lưu lượng (`THRESHOLDS.md` R2).
- Mô hình chính LightGBM, walk-forward, Optuna, SHAP.
- Chủ repo: review 100 % PR, giữ `main` sạch.
- Pair-programming với D 30 phút/tuần.

### D — Data Analyst
Nguyên tắc: **G luôn giao issue đã mô tả rõ input – output – tiêu chí xong**, không giao việc mơ hồ. Template issue có ô "Gợi ý cách làm" bắt buộc điền.
- EDA theo `docs/EDA_CHECKLIST.md` (8 mục, mỗi mục có ô điền kết luận).
- Feature engineering từ danh sách feature G đã liệt kê.
- Baseline models (persistence, seasonal naive, ARIMA, GloFAS thô).
- Dashboard Streamlit theo wireframe G vẽ trước.
- Chạy thí nghiệm theo script G viết, ghi kết quả vào bảng.

> Kẹt > 45 phút → bắt buộc comment vào issue hoặc kéo sang `Blocked`. Đây là rule cứng, áp dụng cho **cả ba người**.

### H — Research & Documentation Lead

Đây là vai trò chuyên môn hoá, không phải việc phụ: **40 % tổng điểm nằm ở chất lượng trình bày 4 báo cáo** (R1 10 % + R2 20 % + R4 10 %), cộng slide thuyết trình.

Tính chất công việc của vai trò này, và cách tổ chức tương ứng:

1. **Không nằm trên đường găng kỹ thuật** — không trực pipeline, không on-call, không debug gấp. Việc viết chạy song song với việc code.
2. **Chia được thành phiên ngắn 30–45 phút**, làm async hoàn toàn.
3. **Deadline nội bộ sớm hơn deadline thật 2–3 ngày** để có đệm biên tập.
4. **Luôn có G backup** — không để bất kỳ đầu việc nào chỉ một người nắm.

Đầu việc:
- Literature review 6 bài (template `docs/templates/PAPER_SUMMARY.md`).
- **Tra cứu nguồn pháp lý**: Phụ lục QĐ 05/2020/QĐ-TTg để xác nhận mực nước BĐ I/II/III — đầu vào trực tiếp cho biến mục tiêu của mô hình.
- **Thu thập bộ sự kiện lũ lịch sử** có công bố đỉnh mực nước → `data/external/flood_events.csv`. Đây là dữ liệu đầu vào cho ánh xạ H→Q, **việc kỹ thuật thật sự**, không phải việc hành chính.
- Data dictionary: G cung cấp `df.describe()`, H diễn giải thành bảng.
- Biên tập & format 4 báo cáo, citation (Zotero), mục lục, caption.
- Slide 30 phút + script nói.
- Checklist QA trước mỗi lần nộp.
- Biên bản họp.

## 3. Bảng RACI

| Hạng mục | G | D | H |
|---|---|---|---|
| Crawl API + ETL | **R/A** | C | I |
| Chọn ô lưới GloFAS | **R/A** | C | I |
| Nguồn pháp lý ngưỡng BĐ | C | I | **R/A** |
| Bộ sự kiện lũ lịch sử | C | I | **R/A** |
| Ánh xạ H→Q | **R/A** | I | C |
| EDA | C | **R** | I |
| Feature engineering | **A** | **R** | I |
| Baseline models | C | **R** | I |
| LightGBM + tuning | **R/A** | C | I |
| Walk-forward + metric | **A** | **R** | I |
| Dashboard | **A** | **R** | C |
| Literature review | C | C | **R/A** |
| Report 1 | C | C | **R/A** |
| Report 2 | **R** (Data) | **R** (EDA) | **A** (gộp + format) |
| Report 3 | **R/A** | C | **R** (biên tập) |
| Report 4 | C | C | **R/A** |
| Slide + luyện nói | C | C | **R/A** |
| Biên bản họp | I | I | **R/A** |

R = làm · A = chịu trách nhiệm cuối · C = được hỏi · I = được thông báo

## 4. Thi cuối kỳ chấm CÁ NHÂN (20 %)

Syllabus ghi rõ: **30 phút, chấm cá nhân, mỗi người phải nắm toàn bộ dự án**. Phân công chuyên môn hoá là hợp lý về vận hành, nhưng điểm thi chấm từng người — nên cần cơ chế chia sẻ kiến thức bắt buộc:

- **Knowledge handoff 20 phút mỗi thứ Bảy**: G trình bày 1 phần kỹ thuật, H viết lại thành 1 trang trong `docs/EXPLAINER.md`. Viết lại chính là học.
- **2 lần mock exam** (W6 và W9): mỗi người bốc 3 câu từ `docs/EXAM_QUESTION_BANK.md`, ưu tiên hỏi phần **không phải mình làm**.
- Ngân hàng câu hỏi tích luỹ dần từ W1.

## 5. Nhịp họp

| Buổi | Thời gian | Nội dung | Ghi biên bản |
|---|---|---|---|
| Họp chính | Thứ 4, 30 phút | Tiến độ, blocker, việc tuần tới | H |
| Standup | Chủ nhật, 15 phút (chat được) | Chốt việc tuần | H |
| Knowledge handoff | Thứ 7, 20 phút | G giảng, D + H hỏi | H |
| Pair G–D | Linh hoạt, 30 phút | Gỡ rối code | — |

Chỉ **họp chính** là bắt buộc cả ba. Hai buổi còn lại tham gia nếu tiện, có ghi chú bù trong `docs/meetings/`.

## 6. Quy ước làm việc

- **Kênh liên lạc chính:** _______ (Discord / Messenger — chốt W1)
- **Định dạng tài liệu khi soạn thảo:** Google Docs → export `.docx` vào `reports/` khi chốt
- **Thời gian phản hồi mong đợi trong ngày làm việc:** dưới 12 giờ
- **SLA review PR:** 24 giờ
- **Người quyết định cuối khi bất đồng kỹ thuật:** G — nhưng phải ghi lý do vào biên bản họp
