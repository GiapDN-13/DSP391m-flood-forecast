# QUY TRÌNH GIT — DSP391m

Mục tiêu: **`main` luôn chạy được**, mọi thay đổi đều qua PR, ai làm gì đều có vết.
Quy trình cố tình giữ đơn giản (chỉ 1 nhánh dài `main`) vì team 3 người, không cần GitFlow.

## 1. Tạo repo (G làm 1 lần)

```powershell
cd E:\FPT_University\2026\FALL_26\DSP391m
git init -b main
git add .
git commit -m "chore: khởi tạo cấu trúc dự án và tài liệu kế hoạch"

# Tạo repo private trên GitHub và push
gh repo create DSP391m-flood-forecast --private --source=. --remote=origin --push

# Mời 2 bạn còn lại
gh api -X PUT repos/:owner/DSP391m-flood-forecast/collaborators/<github-cua-duc>  -f permission=push
gh api -X PUT repos/:owner/DSP391m-flood-forecast/collaborators/<github-cua-huyen> -f permission=push
```

## 2. Bảo vệ nhánh `main`

> ⚠️ **Không bật được trên repo này.** GitHub chỉ cho bảo vệ nhánh ở repo **public**, hoặc repo private có tài khoản **Pro**. Repo của nhóm là private trên tài khoản free nên API trả `403`.

Ba lựa chọn:

| Cách | Đánh đổi |
|---|---|
| **Giữ private, không có bảo vệ tự động** ← đang dùng | CI vẫn chạy trên mọi PR và vẫn báo đỏ, chỉ là không *chặn* được merge. Phải tự giữ kỷ luật |
| Chuyển repo sang **public** | Được bảo vệ nhánh miễn phí, nhưng bài đang làm sẽ công khai trước khi nộp — rủi ro về liêm chính học thuật |
| Nâng **GitHub Pro** | Mất tiền, và `NFR-13` yêu cầu chi phí 0 đồng |

**Quy ước thay thế, cả ba phải tuân thủ:**

- Vẫn **mở PR cho mọi thay đổi**, không ai push thẳng vào `main`.
- **Không merge khi CI đang đỏ** — kiểm tra bằng mắt ở tab Checks trước khi bấm merge.
- G rà lịch sử `main` mỗi tuần: `git log --oneline --first-parent main` — commit nào không đi qua PR thì hỏi lại.

Sau khi nộp Report 4 xong, chuyển repo sang public là có bảo vệ nhánh miễn phí, và tiện làm portfolio.

Nếu sau này đủ điều kiện bật, file cấu hình đã có sẵn:

```powershell
gh api -X PUT repos/:owner/DSP391m-flood-forecast/branches/main/protection `
  --input .github/branch-protection.json
```

## 3. Đặt tên nhánh

`<loại>/<người>/<mô-tả-ngắn>`

| Loại | Dùng khi | Ví dụ |
|---|---|---|
| `feat` | Thêm chức năng code | `feat/giap/lightgbm-baseline` |
| `data` | Crawl / ETL / làm sạch | `data/giap/crawl-era5-2010-2015` |
| `eda` | Notebook phân tích | `eda/duc/lag-correlation` |
| `exp` | Thí nghiệm mô hình (có thể bỏ) | `exp/giap/lstm-30d` |
| `docs` | Báo cáo, tài liệu, slide | `docs/huyen/report1-problem-statement` |
| `fix` | Sửa lỗi | `fix/duc/timezone-off-by-one` |

## 4. Commit message — Conventional Commits

```
<loại>(<phạm vi>): <mô tả ngắn, tiếng Việt không dấu hoặc tiếng Anh>

[thân bài tuỳ chọn]
Refs: #<số issue>
```

Ví dụ tốt:

```
feat(ingest): them retry va checkpoint cho crawler ERA5

Crawl theo lo 1 nam, luu state vao .cache/ de resume khi dut mang.
Refs: #14
```

Commit **xấu** (đừng làm): `update`, `fix bug`, `asdasd`, `commit lan 2`.

## 5. Vòng đời một task

```
1. Nhận issue trên GitHub Project  →  kéo sang "In progress"
2. git switch main && git pull
3. git switch -c feat/giap/ten-viec
4. ... code ... commit nhỏ, thường xuyên ...
5. git push -u origin feat/giap/ten-viec
6. gh pr create --fill --base main
7. Người khác review  →  sửa theo comment
8. Squash and merge  →  issue tự đóng (nếu PR có "Closes #14")
9. git switch main && git pull && git branch -d feat/giap/ten-viec
```

## 6. Ai review của ai

| PR của | Người review |
|---|---|
| G | D (code) · H (nếu là tài liệu) |
| D | **G bắt buộc** |
| H | G hoặc D |

Mức độ review theo loại PR, không theo người: PR **code** review kỹ (logic, rò rỉ dữ liệu, test); PR **tài liệu/báo cáo** review nội dung và số liệu, không bắt bẻ chính tả vặt — góp ý câu chữ để lại comment trên Google Docs.

Nguyên tắc: **comment phải nói rõ "sửa thế nào"**, không chỉ nói "cái này sai". Mục tiêu của review là làm việc chạy và truyền kiến thức, không phải chặn.

SLA: review trong **24 giờ** — lịch 9 tuần không chịu được PR nằm chờ. Quá hạn mà không ai review → G merge để không chặn tiến độ.

## 7. Dữ liệu — TUYỆT ĐỐI không commit

`data/` đã nằm trong `.gitignore`. Dữ liệu đi đường khác:

| Loại | Nơi lưu | Ai quản |
|---|---|---|
| Raw Parquet (nặng) | Google Drive team + Hugging Face Datasets | G |
| `daily_panel.parquet` (bảng phân tích cuối) | HF Datasets (private) | G |
| Model đã train (`.pkl`, `.pt`) | GitHub Release asset | G |
| Hình cho báo cáo (PNG nhỏ) | **Có commit** trong `reports/figures/` | ai tạo |

Nếu lỡ commit file nặng: báo G ngay, **đừng tự `push --force`**.

## 8. Notebook — chống conflict

Notebook rất dễ conflict vì output nằm trong file JSON. Quy tắc:

- **Mỗi người một notebook riêng**, không sửa chung 1 file.
- Trước khi commit: `Kernel → Restart & Clear All Outputs` (hoặc để `nbstripout` trong pre-commit tự làm).
- Code dùng lại nhiều lần → chuyển vào `src/`, notebook chỉ gọi hàm.

## 9. Tag & release

| Tag | Khi nào |
|---|---|
| `report1` | Ngay sau khi nộp Report 1 |
| `report2` | Sau Report 2 |
| `v1.0` | Freeze model cuối (W8) |
| `final` | Sau khi nộp Report 4 |

```powershell
git tag -a report1 -m "Trang thai repo luc nop Report 1"
git push origin report1
```

Tag giúp trả lời được câu hỏi khi vấn đáp: *"lúc nộp Report 2 thì mô hình đang ở đâu?"*

## 10. Lệnh cứu hộ hay dùng

```powershell
git status                      # đang ở đâu, sửa gì
git switch main; git pull       # đồng bộ trước khi làm việc mới
git stash                       # cất tạm việc đang dở
git stash pop                   # lấy lại
git restore <file>              # bỏ sửa 1 file chưa commit
git log --oneline --graph -20   # xem lịch sử
git reset --soft HEAD~1         # gỡ commit cuối, GIỮ nguyên code
```

> Gặp chữ `CONFLICT` hoặc bất cứ thứ gì không chắc → **dừng lại, chụp màn hình, hỏi G**. Đừng đoán, đừng `--force`.
