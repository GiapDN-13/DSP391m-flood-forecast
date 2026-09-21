# Nhật ký dự báo phát hằng ngày

Mỗi file `YYYY-MM-DD.csv` là **bản dự báo thật đã phát vào sáng ngày đó** (giờ
Việt Nam), lấy từ GloFAS + mưa dự báo. Đây là nguyên liệu cho **kịch bản B**
(`docs/RESEARCH_DESIGN.md` §2): đánh giá trên dự báo phát trong thời gian thực,
không phải trên kho lưu trữ. Đã phát rồi thì **không lấy lại được**.

| File | Nghĩa |
|---|---|
| `YYYY-MM-DD.csv` | bản phát ~05:00 ICT ngày đó — bản chính thức |
| `YYYY-MM-DD_chu-ky-muon-HHMMZ.csv` | lần chạy thêm trong cùng ngày, giữ lại để truy nguyên, **không dùng cho đánh giá** |
| `_latest.csv` | bản mới nhất, cho dashboard đọc |

## Lỗ hổng đã biết: **không có bản dự báo ngày 20/09/2026**

Từ 15/09 tới 21/09/2026, GitHub Actions báo **thành công 6 lần liên tiếp**, song
nhật ký vẫn mất một ngày. Nguyên nhân gồm hai lớp:

1. Lịch đặt 22:00 UTC, nhưng GitHub thực tế chạy trễ ~2 giờ, nên job nổ **quanh
   nửa đêm UTC**.
2. `run_date` lấy bằng `date.today()` — trên runner đó là **ngày UTC**, trong khi
   cả dự án quy ước giờ Việt Nam.

Hệ quả: lần chạy 23:58 UTC ngày 19/09 (= 06:58 ICT ngày **20/09**) tự nhận là
ngày 19/09 và **ghi đè** bản sáng 19/09. Ngày 20/09 không có file nào.

**Đã xử lý:**

* `src/models/predict_daily.py` dùng `ict_today()` — ngày theo `Asia/Bangkok`.
* Có file rồi thì **không ghi đè**, lần chạy sau ra file `_chu-ky-muon-`.
* Lịch chuyển sang 20:00 UTC để không ép sát nửa đêm UTC.
* `tests/test_forecast_log.py` khoá lại cả hai hành vi.
* Bản sáng 19/09 bị ghi đè đã **phục hồi từ git** (commit `068b87b`); bản ghi đè
  giữ lại thành `2026-09-19_chu-ky-muon-2358Z.csv`.

**Ngày 20/09 thì không cứu được.** Bản ghi đè *không phải* bản 20/09: phần lưu
lượng của nó vẫn là chu kỳ GloFAS của ngày 19/09 (API lưu lượng chạy theo ngày
GMT), chỉ phần mưa là của 20/09. Gán nó thành "bản 20/09" là bịa số liệu. Nên
20/09 để trống và ghi rõ ở đây; khi đánh giá kịch bản B thì n = số ngày thật có
bản phát, không tính 20/09.

## Bài học ghi lại

Job xanh **không chứng minh** dữ liệu đúng. Lần này mỗi lần chạy đều `exit 0`,
đều commit, đều gửi mail thành công — mà vẫn mất dữ liệu. Kiểm tra phải nhắm vào
**sản phẩm** (đủ file, đúng ngày), không phải vào trạng thái lần chạy. Xem
`docs/RUNBOOK.md` §8.7.
