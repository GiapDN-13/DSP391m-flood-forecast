# TỪ ĐIỂN DỮ LIỆU

Phụ trách: **H** (diễn giải) với số liệu do **G** cung cấp · Hạn: **W3** · Dùng cho Report 2 mục Data Collection.

## 1. Nguồn dữ liệu

| Nguồn | Nội dung | Độ phân giải | Khoảng dùng | Giấy phép | Ngày truy cập |
|---|---|---|---|---|---|
| Open-Meteo Flood API (GloFAS v4) | Lưu lượng sông | ~5 km, ngày | **1997–2026** (yêu cầu 1984, nhưng 1984–1996 rỗng 100 %) | CC BY 4.0 | |
| Open-Meteo Historical (ERA5) | Mưa, nhiệt, gió, ẩm | ~11 km, giờ | 2010–2026 | CC BY 4.0 | |
| Open-Meteo Historical Forecast | Mưa dự báo đã phát | giờ | 2022–2026 | CC BY 4.0 | |
| Ranh giới xã | GeoJSON | — | Bản sau 01/07/2025 | | |

⚠️ **Ghi rõ ngày phiên bản ranh giới hành chính** — địa giới cấp xã thay đổi từ 01/07/2025 (xem `GAPS.md` mục 2).

## 2. Bảng phân tích `data/processed/daily_panel.parquet`

| Cột | Kiểu | Đơn vị | Ý nghĩa | Nguồn | Khoảng giá trị | % thiếu |
|---|---|---|---|---|---|---|
| `date` | date | — | Ngày (giờ Việt Nam, UTC+7) | — | | |
| `station` | str | — | `kim_long` / `phu_oc` | — | | |
| `discharge` | float | m³/s | Lưu lượng GloFAS | Flood API | | |
| `glofas_fc_h1..h3` | float | m³/s | Dự báo GloFAS thô 1–3 ngày | Flood API | | |
| `rain_sum` | float | mm/ngày | Mưa ngày, trung bình tiểu lưu vực | ERA5 | | |
| `rain_cum_3d/5d/7d` | float | mm | Mưa tích luỹ | dẫn xuất | | |
| `api_k09` | float | mm | Antecedent Precipitation Index | dẫn xuất | | |
| `alert_level` | int | 0–3 | Cấp BĐ suy ra từ ngưỡng | `THRESHOLDS.md` | | |

## 3. Quy ước

- **Múi giờ:** mọi cột `date` là giờ Việt Nam (UTC+7). Cách gộp giờ→ngày ghi trong `docs/API_NOTES.md` §4.
- **Giá trị thiếu:** mã hoá bằng `null` (không dùng `-999`). Cách xử lý ghi ở đây: ____
- **Làm tròn:** ____

## 4. Cách trích dẫn trong báo cáo

```
(điền — lấy từ docs/API_NOTES.md §5)
```
