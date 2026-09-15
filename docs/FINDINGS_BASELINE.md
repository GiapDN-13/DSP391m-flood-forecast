# PHÁT HIỆN — EDA và baseline (15/09/2026)

Chạy lại: `python -m src.models.baselines` · `python -m src.viz.eda`
Hình: `reports/figures/w1_eda_baseline.png` · Số: `reports/baseline_results.csv`

---

## 1. 🔴 Ngưỡng nghiệm thu AC-1 đặt quá dễ — phải sửa

`AC-1` trong `SPEC.md` yêu cầu **NSE ≥ 0,5** ở horizon 1 ngày.

Kết quả thực tế của baseline tầm thường nhất:

| Mô hình | h=1 | h=2 | h=3 |
|---|---|---|---|
| **persistence** (lấy y hôm nay làm dự báo) | **0,542** | 0,008 | −0,198 |
| climatology | 0,097 | 0,097 | 0,096 |
| ARIMA(2,1,2) trên log | −0,093 | −0,093 | −0,093 |
| seasonal naive | −0,434 | −0,434 | −0,435 |

**Persistence đã vượt ngưỡng AC-1 mà không cần mô hình gì cả.** Nếu giữ nguyên tiêu chí, nhóm có thể "đạt" mà không chứng minh được điều gì — và giám khảo sẽ hỏi đúng chỗ đó.

### Đề xuất sửa AC-1

| | Cũ | Mới |
|---|---|---|
| h = 1 | NSE ≥ 0,5 | **NSE ≥ 0,70** *và* cải thiện ≥ 20 % RMSE so với persistence |
| h = 2 | — | **NSE ≥ 0,40** (persistence chỉ 0,008) |
| h = 3 | — | **NSE ≥ 0,25** (persistence âm) |

Lý do đặt theo horizon: persistence mạnh ở h=1 nhưng **sụp rất nhanh** — h=2 đã về 0, h=3 âm. Đó chính là khoảng trống mà mô hình phải lấp, và là chỗ dự án có giá trị thật.

> Bài học phương pháp: **đặt ngưỡng nghiệm thu trước khi chạy baseline là sai thứ tự.** Ngưỡng phải được hiệu chỉnh theo baseline, nếu không nó chỉ là con số cho đẹp.

---

## 2. 🔴 Baseline "GloFAS thô" KHÔNG dựng lại được từ quá khứ

Kiểm ngày 15/09/2026:

```
historical-forecast-api.open-meteo.com/v1/flood  →  404 Not Found
```

Open-Meteo có kho lưu trữ **dự báo mưa** đã phát (`historical-forecast-api`), nhưng **không có** kho tương đương cho **dự báo lưu lượng**. Chuỗi lịch sử của Flood API là *giá trị phân tích của mô hình*, không phải bản dự báo đã phát trước đó mấy ngày.

### Ảnh hưởng tới hai chỗ quan trọng

**(a) `AC-3`** — "RMSE của LightGBM ≤ RMSE GloFAS thô" **không đánh giá được trên quá khứ**.

**(b) Quyết định thiết kế ở `RESEARCH_DESIGN.md` §1.2** — "GloFAS thô vừa là baseline vừa là feature đầu vào" — **không thực hiện được khi huấn luyện**. Không có dự báo GloFAS quá khứ thì không có cột feature đó trong tập train. Đây là chỗ hổng nghiêm trọng vì nó chính là lập luận vô hiệu hoá rủi ro R9.

### Ba cách xử lý

| Cách | Nội dung | Đánh giá |
|---|---|---|
| **A. Tích luỹ tiến về phía trước** ⭐ | Job hằng ngày đã chạy từ W1, ghi `reports/forecast_log/`. Tới W8 có ~8 tuần cặp dự báo–thực tế | Là **dữ liệu thật**, nhưng mẫu nhỏ và có thể không chứa đợt lũ lớn nào |
| **B. Đổi khung đối chứng** | So với **persistence / climatology / ARIMA** trên quá khứ (đã có), và chỉ so với GloFAS thô trên phần tích luỹ được | Trung thực, làm được ngay |
| **C. Dùng chuỗi phân tích GloFAS làm feature** | ❌ **Không được** — giá trị phân tích tại ngày t+h là thông tin tương lai. Đây là rò rỉ dữ liệu trắng trợn | Loại |

**Chọn B + A.** Và phải sửa lại lời tuyên bố đóng góp: không nói "tốt hơn GloFAS" nữa, mà nói *"tốt hơn các baseline thống kê tiêu chuẩn, và bước đầu đối chứng với dự báo GloFAS trên giai đoạn vận hành thực tế"*.

> Điều này cũng cho thấy việc **bật job dự báo hằng ngày ngay từ W1** hoá ra quan trọng hơn dự tính ban đầu: nó là nguồn duy nhất cho phần đối chứng với GloFAS.

---

## 3. Kết quả EDA dùng được ngay cho Report 2

| Phát hiện | Số liệu | Ý nghĩa |
|---|---|---|
| **Độ trễ tối ưu** | lag **1 ngày**, r = **0,790** (lag0 0,641 · lag2 0,608 · lag3 0,382) | Căn cứ định lượng cho việc chọn feature; hợp lý với lưu vực ~2 800 km² |
| **Mưa một ngày thắng mưa tích luỹ** | mưa 1 ngày 0,79 > tích luỹ 3d 0,75 > 5d 0,66 > 7d 0,60 | Lũ ở đây **lên nhanh**, phản ứng tức thời chứ không tích luỹ chậm |
| **Mùa lũ tập trung** | tháng 9–12 chiếm **32 % số ngày** nhưng **59 % tổng lượng nước** | Khẳng định định nghĩa mùa lũ bằng số liệu |
| **Mưa năm** | 2 929 mm | Khớp khí hậu Huế; xác nhận độc lập cho giả định dòng chảy đơn vị khi chọn ô lưới |
| **Lệch phải rất mạnh** | trung vị 49,7 nhưng đỉnh 3 588 m³/s (gấp 72 lần) | Phải mô hình hoá trên thang log |
| **Hai chế độ GloFAS** | trung bình 118,4 → 126,1 m³/s (+6 %) sau 07/2022 | Chênh nhỏ — mốc cắt vẫn nên giữ, nhưng không phải đứt gãy lớn |

### Phân vị — đầu vào cho phương án dự phòng R4

| | Q50 | Q90 | Q95 | Q98 | Q99 | Q99.5 |
|---|---|---|---|---|---|---|
| m³/s | 49,7 | 258,4 | 430,2 | 745,9 | 1 168,8 | 1 556,0 |

---

## 4. ⚠️ Hai bất thường cần kiểm khi làm EDA chi tiết

5 ngày vượt Q99 nằm **ngoài** mùa lũ:

| Ngày | Lưu lượng | Mưa cùng ngày | Nhận định |
|---|---|---|---|
| 2022-04-01 | 1 839,8 | 178,7 mm | Có mưa lớn đi kèm → **nhiều khả năng là lũ trái mùa thật** |
| 2022-04-02 | 2 635,3 | 146,5 mm | Nối tiếp ngày trên, nhất quán |
| **2025-06-14** | **2 054,9** | **0,9 mm** | 🔴 **Đáng ngờ** — lưu lượng rất lớn mà gần như không có mưa |

Trường hợp 06/2025 phải làm rõ: có thể do **xả hồ chứa** (lưu vực sông Hương có hồ Tả Trạch và Bình Điền), hoặc là lỗi mô phỏng của GloFAS. Nếu là xả hồ thì đó là một hạn chế phải nêu — **GloFAS không mô phỏng vận hành hồ chứa**, mà hồ chứa lại chi phối mạnh lưu lượng hạ lưu sông Hương.

👉 Đây có thể là hạn chế lớn nhất chưa được ghi nhận của cả đề tài. Giao D kiểm khi làm EDA.

---

## 5. Việc tiếp theo

- [ ] Sửa `AC-1` và `AC-3` trong `SPEC.md` theo mục 1 và 2
- [ ] Sửa `RESEARCH_DESIGN.md` §1.2 — bỏ lập luận "GloFAS là feature đầu vào"
- [ ] Kiểm bất thường 2025-06-14: xả hồ hay lỗi dữ liệu
- [ ] Rà xem lưu vực có hồ chứa lớn nào, và GloFAS có mô phỏng không
