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
| `Week` | Single select | `W01` … `W15` |
| `Milestone` | (có sẵn) | `Report 1` · `Report 2` · `Report 3` · `Final + Exam` |
| `Effort` | Number | Số giờ ước lượng |
| `Due` | Date | Deadline nội bộ |

### 3 view cần tạo

1. **Board theo Status** — view mặc định, nhìn phát biết ai đang kẹt.
2. **Table nhóm theo `Owner`** — kiểm tra tỉ trọng có đúng 50/32/18 không.
3. **Board nhóm theo `Week`** — dùng trong họp thứ 4 hằng tuần.

### Cột "Blocked" là quan trọng nhất

Đây là cơ chế chống rủi ro lớn nhất của team: Đức kẹt mà im lặng.
**Rule cứng:** kẹt > 45 phút → kéo issue sang `Blocked` + comment mô tả. Kéo sang `Blocked` **không phải là điểm trừ**, để đó cả tuần mới là điểm trừ.

---

## 2. Labels

Chạy `scripts/bootstrap_github.ps1` để tạo tự động:

| Label | Màu | Ý nghĩa |
|---|---|---|
| `p0-critical` | 🔴 | Trên đường găng, trễ là chết |
| `p1` / `p2` | 🟠 🟡 | Ưu tiên thường / thấp |
| `data` `model` `eda` `dashboard` `docs` `infra` | ⚪ | Loại việc |
| `good-first-task` | 🟢 | Việc dễ, có hướng dẫn — ưu tiên giao Đức |
| `light-task` | 🩵 | Việc nhẹ, async, không deadline gấp — dành cho Huyền |
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

## 5. Chỉ số sức khoẻ dự án — kiểm mỗi chủ nhật

| Chỉ số | Ngưỡng an toàn | Nếu vượt thì làm gì |
|---|---|---|
| Issue quá hạn (`Due` < hôm nay, chưa `Done`) | ≤ 2 | Cắt scope, đừng cố làm bù |
| Issue ở `Blocked` > 3 ngày | 0 | G vào gỡ trực tiếp, pair-programming |
| PR mở > 3 ngày không review | 0 | Review ngay hoặc merge |
| Tỉ lệ đóng góp lệch so với 50/32/18 | ±10 % | Tuần sau cân lại việc |
| Tuần đã trôi mà `% hoàn thành` < `% tuần đã qua` − 10 | — | Họp khẩn, kích hoạt phương án B |

## 6. Ghi log đóng góp

Mỗi chủ nhật, Giáp cập nhật `docs/CONTRIBUTION_LOG.md`. Số issue `Done` lấy từ view Table nhóm theo `Owner`.
Mục đích không phải để so bì, mà để:

- khi giảng viên hỏi "ai làm gì" → có câu trả lời cụ thể;
- phát hiện sớm nếu một người bị quá tải hoặc bị bỏ rơi.

## 7. Phương án dự phòng nếu GitHub Projects quá nặng với ai đó

Nếu Huyền thấy GitHub khó dùng (giao diện nhiều, nhiều thao tác), dùng **Google Sheet 1 tab** cho riêng phần việc tài liệu, cột: `Việc | Hạn | Trạng thái | Link`. Giáp đồng bộ sang GitHub hộ. **Đừng ép công cụ**, mục tiêu là việc chạy chứ không phải dùng đúng tool.
