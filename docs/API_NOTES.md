# GHI CHÚ API OPEN-METEO

Phụ trách: **D** · Hạn: **W1** · Mục đích: để cả team biết gọi gì, tham số nào, và crawl mất bao lâu.

## 1. Bốn endpoint dùng trong dự án

| Endpoint | Host | Dùng để | Ghi chú |
|---|---|---|---|
| **Marine API** | `marine-api.open-meteo.com/v1/marine` | `sea_level_height_msl` theo giờ — biến triều tại cửa Thuận An (16,57 · 107,63). ⚠️ **Kho chỉ có từ 2023-01-01** nên không làm feature huấn luyện được | CC BY 4.0 |
| Flood API | `flood-api.open-meteo.com/v1/flood` | `river_discharge` theo ngày; tài liệu ghi từ 1984 nhưng **thực tế chỉ có dữ liệu từ 1997** (xem `FINDINGS_EVENTS.md` §3) → +7 ngày | GloFAS v4, ~5 km |
| Historical (ERA5) | `archive-api.open-meteo.com/v1/archive` | Mưa/nhiệt/gió theo giờ | Trễ ~5 ngày |
| **Historical Forecast** | `historical-forecast-api.open-meteo.com/v1/forecast` | **Mưa dự báo đã phát trong quá khứ (từ 2021)** | ⭐ Cần cho kịch bản B |
| Forecast | `api.open-meteo.com/v1/forecast` | Dự báo mưa 1–7 ngày | Chạy hằng ngày |

## 2. Tham số cần ghi rõ (điền khi đọc doc)

| Tham số | Giá trị dùng | Ghi chú |
|---|---|---|
| `latitude` / `longitude` | | Gọi được nhiều điểm/1 request không? |
| `start_date` / `end_date` | | Khoảng tối đa cho 1 request? |
| `daily` / `hourly` | | Tên biến chính xác |
| `timezone` | `Asia/Bangkok` | Xem mục 4 |
| `models` | | Flood API có chọn được model không |
| `cell_selection` | | Có ảnh hưởng tới việc chọn ô sông không |

## 3. Giới hạn & tốc độ — ĐO THỰC TẾ, đừng đoán

| Đo gì | Kết quả |
|---|---|
| Giới hạn free (request/ngày, /giờ, /phút) | |
| Thời gian 1 request discharge 40 năm, 1 điểm | |
| Thời gian 1 request mưa giờ 1 năm, 1 điểm | |
| Số ngày tối đa gộp được vào 1 request | |
| **Ước tính tổng thời gian crawl 50 điểm × 2010–2026 (giờ)** | ⬅ con số quan trọng nhất |
| Dung lượng Parquet ước tính | |
| Hành vi khi bị 429 | |

> Nếu ước tính tổng > 48 giờ → báo G ngay trong W1, cắt scope tiếp (xem `RISKS.md` R2).

## 4. Bẫy đã biết

- **Timezone.** Đặt `timezone=Asia/Bangkok` hay lấy UTC rồi tự đổi? Hai cách cho kết quả gộp ngày **khác nhau** — chốt một cách và ghi vào đây, vì nó ảnh hưởng trực tiếp tới việc ghép mưa với discharge.
- **Đơn vị mưa.** `mm` mỗi giờ hay mỗi khoảng? Xác nhận bằng cách cộng 24 giá trị giờ so với giá trị ngày.
- **Mốc 07/2022** của GloFAS — xem `docs/DATA_SPLITS.md` §1.
- **Ô lưới không trùng sông thật** — xem `docs/RISKS.md` R1.

## 5. Trích dẫn bắt buộc (CC BY 4.0)

Ghi đúng dạng trích dẫn Open-Meteo và GloFAS/Copernicus vào đây để H dùng lại trong cả 4 báo cáo:

```
(điền)
```
