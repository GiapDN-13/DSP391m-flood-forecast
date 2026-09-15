# PHÁT HIỆN — hạn mức Open-Meteo tính theo KHỐI LƯỢNG, không theo số request

**Ngày:** 15/09/2026 · **Liên quan:** `RISKS.md` R3 · `SPEC.md` NFR-2, NFR-13 · `PLAN.md` scope dữ liệu

## 1. Chuyện gì xảy ra

Lượt crawl đầu tiên xin **trọn 42 năm cho mỗi ô** lưu lượng. Sau 44 request, API trả 429 liên tục, nhịp gọi bị đẩy lên kịch trần 8 giây và gần như đứng hình — **không phải vì gọi quá nhanh, mà vì xin quá nhiều dữ liệu mỗi lần**.

## 2. Cách tính hạn mức

Hạn mức miễn phí không đếm số request mà đếm **đơn vị khối lượng**, xấp xỉ:

```
weight ≈ ceil(số ngày / 14) × ceil(số biến / 10)        (nhân thêm 24 nếu lấy theo giờ)
```

Hạn mức tham khảo: **~10.000 đơn vị/ngày**, **~5.000/giờ**.

Hệ quả cụ thể:

| Loại request | Số ngày | Trọng số | Gọi được bao nhiêu lần/ngày |
|---|---|---|---|
| Discharge 42 năm (1984–2026) | 15 584 | **~1 113** | **9** |
| Discharge 1 năm (probe) | 365 | ~27 | 370 |
| Mưa ngày 2010–2026 | 6 087 | ~435 | 23 |
| Mưa **giờ** 1 năm | 365 | **~648** | 15 |

👉 Chỉ **9 request** chuỗi 42 năm là hết hạn mức cả ngày. Đó chính xác là điều đã xảy ra.

## 3. Chi phí thực tế của kế hoạch ban đầu

| Pha | Số task | Trọng số |
|---|---|---|
| Mưa ngày (25 điểm, lưới 0,15°) | 25 | ~10 900 |
| Quét mạng sông (probe 1 năm, 316 ô) | 316 | ~8 500 |
| Mưa dự báo lưu trữ (25 điểm) | 25 | ~2 800 |
| **Mưa giờ (300 task)** | 300 | **~189 000** |
| **Tổng** | | **~211 000** |

**~211.000 đơn vị ÷ 10.000/ngày ≈ 21 ngày.** Không có cách nào lấy hết trong 9 tuần mà không ảnh hưởng việc khác.

## 4. Đã xử lý thế nào

1. **Loại `rain_hourly` khỏi lượt chạy mặc định.** Một mình nó chiếm 90 % chi phí (~19 ngày hạn mức) trong khi mô hình chỉ cần **dữ liệu ngày** — horizon là 1–3 ngày, không có feature dưới ngày nào. Vẫn chạy tay được:
   `python -m src.ingest.crawl_all --phase rain_hourly`
   Chỉ nên chạy cho **vài điểm, vài mùa lũ**, đủ để D kiểm chứng `FR-E2` (gộp giờ → ngày).
2. **Tách quét mạng sông thành 2 bước:** probe 1 năm cho mọi ô (rẻ, ~27 đơn vị/ô) → chỉ xin chuỗi 42 năm cho ô **thật sự có dòng chảy** (`FULL_MIN_QMEAN = 1 m³/s`, trần `MAX_FULL_CELLS = 40`).
3. **Thưa lưới mưa** từ 0,10° (64 điểm) xuống **0,15° (25 điểm)**. Mưa biến đổi chậm theo không gian; ở quy mô lưu vực này 25 điểm là đủ, mà tiết kiệm 60 % chi phí.
4. **Sắp lại thứ tự pha theo giá trị trên mỗi đơn vị quota**, không theo thứ tự pipeline. Mưa ngày chạy trước vì nó là thứ **bắt buộc** mà chưa có; lưu lượng đã có sẵn 45 ô chuỗi đầy đủ từ lượt trước.
5. **Nhịp gọi tự phục hồi nhanh hơn**: cứ 8 lần thành công liên tiếp thì giảm nhịp 25 %. Bản trước giảm quá chậm nên dính trần 8 giây cả đêm.
6. **Ghi và hiển thị trọng số đã tiêu** trên màn hình theo dõi, để biết còn bao nhiêu hạn mức.

## 5. Cần đưa vào báo cáo

- **Report 2 – Data Collection:** nêu rõ cơ chế hạn mức và cách nhóm thiết kế crawl để sống chung với nó. Đây là chi tiết kỹ thuật thật, cho thấy nhóm hiểu nguồn dữ liệu chứ không chỉ gọi API.
- **Limitations:** lý do dữ liệu mưa là **theo ngày** chứ không theo giờ — là quyết định do hạn mức, và không ảnh hưởng bài toán vì horizon tính bằng ngày.
- **`NFR-13` (chi phí 0 đồng)** vẫn giữ được, nhưng phải trả giá bằng thời gian crawl. Nêu rõ đánh đổi này.

## 6. Việc cho G

- [ ] Cập nhật `docs/API_NOTES.md` §3 bằng số đo thật ở đây (mục đang để trống chờ D điền).
- [ ] Quyết định có cần `rain_hourly` không. Khuyến nghị: **chỉ lấy 3 điểm × mùa lũ 2020 và 2023**, đủ để chứng minh khâu gộp giờ→ngày đúng, tốn ~2.600 đơn vị.
- [ ] Nếu cần nhiều dữ liệu hơn nữa: Open-Meteo có gói học thuật miễn phí cho nghiên cứu — nhưng cân nhắc thời gian xin so với lịch 9 tuần.
