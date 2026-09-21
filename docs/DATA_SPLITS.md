# CHIA TẬP DỮ LIỆU & TỔNG HỢP KHÔNG GIAN

> Điền ở **W3**. Chốt xong thì **không đổi nữa** — đổi split giữa chừng là tự lừa mình.

## 1. Mốc cắt 07/2022 — vì sao quan trọng

Từ tháng 07/2022, dữ liệu "lịch sử" của GloFAS trên Open-Meteo **không còn là reanalysis** mà là **dự báo được lưu trữ (archived forecast)**. Hai chế độ này có đặc tính sai số khác nhau → nếu trộn lẫn khi train/test, kết quả sẽ không phản ánh đúng hiệu năng thực tế.

## 2. Bảng chia tập (đề xuất)

| Tập | Khoảng thời gian | Chế độ dữ liệu | Số ngày | Dùng để |
|---|---|---|---|---|
| Train | **2010-01-01** → 2015-12-31 | Reanalysis | ~2 190 | Huấn luyện |
| Validation | 2016-01-01 → 2022-06-30 | Reanalysis | ~2 370 | Chọn siêu tham số (Optuna) |
| **Test (chính)** | 2022-07-01 → 2026-08-31 | **Archived forecast** | ~1 520 | Báo cáo kết quả cuối |
| *(kiểm chéo)* | fold cuối của walk-forward | Reanalysis | — | So hiệu năng trên **cùng chế độ dữ liệu**, để tách ảnh hưởng của mốc 07/2022 |

⚠️ Mưa ERA5 **chỉ crawl từ 2010** (scope đã cắt, xem `PLAN.md`). Discharge yêu cầu từ 1984 nhưng **thực tế chỉ có dữ liệu từ 1997** (1984–1996 rỗng 100 %, xem `FINDINGS_EVENTS.md` §3). Phân vị, return period và ghép sự kiện lũ cũ vẫn làm được nhưng trên **29 năm**, không phải 42 năm — phải nói đúng độ dài trong báo cáo.

## 3. Walk-forward validation

Không dùng k-fold ngẫu nhiên. Sơ đồ:

```
fold 1: train[2010–2016]  → test[2017]
fold 2: train[2010–2017]  → test[2018]
fold 3: train[2010–2018]  → test[2019]
...
```

Cửa sổ train **mở rộng dần (expanding)**, không trượt. Có **gap 3 ngày** giữa cuối train và đầu test để chặn rò rỉ qua lag feature horizon 3 ngày.

## 4. Chống rò rỉ dữ liệu — checklist

- [ ] Mọi lag feature chỉ dùng thông tin tại thời điểm `t` trở về trước.
- [ ] Target là `discharge[t + h]` với `h ∈ {1, 2, 3}`.
- [ ] Scaler / encoder **fit trên train, transform trên val+test** — không fit trên toàn bộ.
- [ ] Không dùng rolling mean có căn giữa (centered).
- [ ] Đã có test tự động: `tests/test_no_leakage.py`.
- [ ] Kết quả NSE > 0.98 ⇒ **nghi ngờ rò rỉ**, kiểm lại trước khi mừng.

## 5. Tổng hợp không gian — 200 điểm lưới thành đầu vào mô hình

Phương án chốt: ☐ trung bình toàn lưu vực ☐ **trung bình theo tiểu lưu vực** *(khuyên dùng)* ☐ trọng số Thiessen

Nếu chia tiểu lưu vực:

| Tiểu lưu vực | Mô tả | Số điểm lưới | Ghi chú |
|---|---|---|---|
| Thượng sông Hương | Vùng núi, mưa lớn | | |
| Trung/hạ sông Hương | Qua TP Huế | | |
| Sông Bồ | Lưu vực riêng, trạm Phú Ốc | | |

Lý do chia theo tiểu lưu vực: giữ được thông tin không gian (mưa thượng nguồn quan trọng hơn mưa hạ nguồn với lưu lượng hạ lưu) mà vẫn giữ số cột ở mức LightGBM xử lý tốt.

## 6. Danh sách feature (điền dần)

| Nhóm | Feature | Công thức | Ghi chú |
|---|---|---|---|
| Mưa | `rain_sum_lag1..7` | mưa ngày, trễ 1–7 | theo từng tiểu lưu vực |
| Mưa tích luỹ | `rain_cum_3/5/7d` | tổng trượt | |
| Chỉ số ẩm trước | `api_k0.9` | API = Σ kⁱ·Pₜ₋ᵢ | |
| Lưu lượng | `q_lag1..14` | discharge trễ 1–14 | |
| Biến thiên | `q_diff1`, `q_diff3` | q[t] − q[t−n] | bắt pha nước lên |
| Mùa | `doy_sin`, `doy_cos`, `month` | mã hoá tuần hoàn | |
| Khác | nhiệt độ, độ ẩm, gió | trung bình ngày | ưu tiên thấp |
