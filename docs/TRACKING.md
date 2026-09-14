# CÔNG CỤ THEO DÕI TIẾN ĐỘ

Nguyên tắc: **một nguồn sự thật duy nhất**. Nếu dùng cả Trello lẫn Notion lẫn Excel thì sau 3 tuần sẽ không cái nào đúng.

## Bộ công cụ chốt

| Việc | Công cụ | Vì sao chọn |
|---|---|---|
| Quản lý task | **GitHub Projects (Board + Table)** | Miễn phí, gắn thẳng vào issue/PR/commit — không phải cập nhật 2 nơi |
| Trao đổi hằng ngày | **Discord / Messenger group** | Nhanh, có lịch sử |
| Biên bản họp | `docs/meetings/YYYY-MM-DD.md` trong repo | Có vết, tìm lại được khi vấn đáp |
| Tài liệu báo cáo | **Google Docs** khi đang viết chung → export `.docx` vào `reports/` khi chốt | Google Docs comment tốt hơn Git cho văn bản |
| Trích dẫn | **Zotero** (group library) | Bắt buộc cho literature review |
| Đóng góp cá nhân | `docs/CONTRIBUTION_LOG.md` | Bằng chứng khi giảng viên chấm cá nhân |
| CI | **GitHub Actions** | Chặn code hỏng vào `main` |

**Cố tình KHÔNG dùng:** Jira (nặng), Notion (tách rời khỏi code), Excel tracker thủ công (không ai cập nhật).

---

## 1. Thiết lập GitHub Projects

Tạo project **"DSP391m Flood Forecast"** (kiểu Table), thêm các trường tuỳ chỉnh:

| Trường | Kiểu | Giá trị |
|---|---|---|
| `Status` | Single select | `Backlog` · `Todo` · `In progress` · `In review` · `Blocked` · `Done` |
| `Owner` | Single select | `Giáp` · `Đức` · `Huyền` · `Cả team` |
| `Week` | Single select | `W1` … `W9` |
| `Milestone` | (có sẵn) | `Report 1` · `Report 2` · `Report 3` · `Final + Exam` |
| `Req` | Text | ID yêu cầu, ví dụ `FR-D1`, `NFR-4` — xem `docs/SPEC.md` |
| `Effort` | Number | Số giờ ước lượng |
| `Due` | Date | Deadline nội bộ |

### 3 view cần tạo

1. **Board theo Status** — view mặc định, nhìn phát biết ai đang kẹt.
2. **Table nhóm theo `Owner`** — kiểm tra tỉ trọng có đúng 50/32/18 không.
3. **Board nhóm theo `Week`** — dùng trong họp thứ 4 hằng tuần.

### Mỗi FR là một issue

Tiêu đề issue bắt đầu bằng ID yêu cầu: `[W3] FR-T2 — Xây ánh xạ mực nước sang lưu lượng`.
Phần **Tiêu chí nghiệm thu** trong `docs/SPEC.md` chép thẳng vào ô "Xong khi nào" của issue — không viết lại, không diễn giải.

Lợi ích: khi vấn đáp bị hỏi *"làm sao chứng minh đã làm đủ?"*, mở board lọc theo `Req` là ra ngay bằng chứng cho từng yêu cầu.

Yêu cầu ưu tiên **M** mà chưa `Done` sau tuần đã định ⇒ **lên đầu agenda họp thứ 4**, trước mọi việc khác.

### Cột "Blocked" là quan trọng nhất

Rủi ro lớn nhất của một team nhỏ là **có người kẹt mà không ai biết**. Với lịch 9 tuần, mất 3 ngày im lặng là mất 5 % tổng thời gian.
**Rule cứng, áp dụng cho cả ba người:** kẹt > 45 phút → kéo issue sang `Blocked` + comment mô tả. Kéo sang `Blocked` **không phải điểm trừ**; để đó cả tuần mới là.

---

## 2. Labels

Chạy `scripts/bootstrap_github.ps1` để tạo tự động:

| Label | Màu | Ý nghĩa |
|---|---|---|
| `p0-critical` | 🔴 | Trên đường găng, trễ là chết |
| `p1` / `p2` | 🟠 🟡 | Ưu tiên thường / thấp |
| `data` `model` `eda` `dashboard` `docs` `infra` | ⚪ | Loại việc |
| `good-first-task` | 🟢 | Việc có hướng dẫn từng bước kèm theo |
| `light-task` | 🩵 | Việc async, chia được thành phiên ngắn, không deadline gấp |
| `blocked` | ⛔ | Đang kẹt |
| `needs-review` | 🔵 | Chờ người khác xem |

---

## 3. Nhịp theo dõi hằng tuần

| Khi nào | Ai | Làm gì | Mất bao lâu |
|---|---|---|---|
| **Thứ 2 sáng** | G | Kéo issue tuần mới vào `Todo`, gán `Owner` + `Due` | 15 phút |
| **Hằng ngày** | Cả 3 | Tự kéo issue của mình sang đúng cột | 1 phút |
| **Thứ 4** | Cả 3 | Họp 30 phút, mở view "Board theo Week" | 30 phút |
| **Thứ 4 sau họp** | H | Viết biên bản vào `docs/meetings/` | 10 phút |
| **Thứ 7** | G | Knowledge handoff 20 phút | 20 phút |
| **Chủ nhật** | G | Chốt `CONTRIBUTION_LOG.md`, kiểm tra tỉ trọng | 10 phút |

## 4. Mẫu agenda họp thứ 4 (30 phút, đúng giờ)

```
00–05  Mở board. Mỗi người 90 giây: xong gì / đang làm gì / kẹt gì
05–15  Xử lý cột Blocked  ← phần quan trọng nhất, đừng bỏ
15–25  Chốt việc tuần tới, gán Owner + Due ngay trên board
25–30  Rủi ro tuần này (nhìn RISKS.md), có cần đổi kế hoạch không
```

Việc không gán được người cụ thể ⇒ coi như không tồn tại. Không có "để mai tính".

## 5. Chỉ số cảnh báo sớm — kiểm mỗi chủ nhật

| Chỉ số | Ngưỡng an toàn | Nếu vượt thì làm gì |
|---|---|---|
| Issue quá hạn (`Due` < hôm nay, chưa `Done`) | ≤ 2 | Cắt scope, đừng cố làm bù |
| Issue ở `Blocked` > 2 ngày | 0 | G vào gỡ trực tiếp, pair-programming |
| PR mở > 24 giờ không review | 0 | Review ngay hoặc merge |
| Tỉ lệ đóng góp lệch so với 50/32/18 | ±10 % | Tuần sau cân lại việc |
| **Yêu cầu ưu tiên M quá hạn** | **0** | Dừng mọi việc S/C, dồn vào M |
| `% hoàn thành` thấp hơn `% thời gian đã trôi` quá 10 điểm | — | Họp khẩn, cắt scope theo `RISKS.md` |

## 6. Ghi log đóng góp

Mỗi chủ nhật, Giáp cập nhật `docs/CONTRIBUTION_LOG.md`. Số issue `Done` lấy từ view Table nhóm theo `Owner`.
Mục đích không phải để so bì, mà để:

- khi giảng viên hỏi "ai làm gì" → có câu trả lời cụ thể;
- phát hiện sớm nếu một người bị quá tải hoặc bị bỏ rơi.

## 7. Nếu board vướng với luồng việc tài liệu

Việc biên tập báo cáo diễn ra chủ yếu trên Google Docs chứ không trên repo. Nếu theo dõi trên board thấy rườm rà, dùng **Google Sheet 1 tab** riêng cho nhánh tài liệu (`Việc | Hạn | Trạng thái | Link`), G đồng bộ sang GitHub. Mục tiêu là việc chạy, không phải dùng đúng tool.
