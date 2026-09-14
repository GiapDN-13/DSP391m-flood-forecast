# PHÁT HIỆN — chọn ô lưới GloFAS (FR-D5)

**Ngày:** 15/09/2026 · **Người chạy:** G · **Dữ liệu:** `data/external/grid_scan_region.csv`
**Hình:** `reports/figures/w1_grid_map.png` · **Lệnh:** `python -m src.viz.grid_map`

Quét 121 ô, bước 0,05° (~5 km), vùng 16,25–16,75 N × 107,25–107,75 E, lưu lượng trung bình 2018–2023.

## 1. Toạ độ trong kế hoạch gốc sai ô — đã xác nhận

| Toạ độ | q_mean | q_max | |
|---|---|---|---|
| (16,46 · 107,59) — kế hoạch gốc | **5,7** | 28,8 | ❌ không phải dòng chảy chính |
| (16,60 · 107,55) — ô lớn nhất | **308,3** | 5 583,7 | ✅ độ lớn hợp lý với lũ sông Hương |

Chênh ~54 lần. Nếu crawl 40 năm bằng toạ độ cũ thì toàn bộ dữ liệu vô dụng.

## 2. Mạng sông GloFAS lệch khỏi vị trí trạm thật ~7 km

Trạm Kim Long ở khoảng (16,47 · 107,57) rơi vào **ô tối**. Dòng chảy mô phỏng của GloFAS nằm ở **kinh độ 107,50**, lệch về phía tây ~7 km.

👉 Hệ quả: **không được chọn ô theo khoảng cách gần trạm nhất.** Phải chọn ô nằm trên dòng chảy mô phỏng có bậc sông tương ứng. Đây là chuyện bình thường với mô hình toàn cầu, nhưng phải nêu trong Limitations.

## 3. Cấu trúc dòng chảy quét được

Chỉ có **một dòng chảy chính** trong vùng, chạy theo hướng bắc dọc kinh độ 107,50, lưu lượng tăng dần về hạ lưu:

| lat | lon | q_mean | q_max |
|---|---|---|---|
| 16,40 | 107,50 | 109,3 | 2 510,9 |
| 16,45 | 107,50 | 117,1 | 2 635,3 |
| 16,50 | 107,50 | 189,2 | 3 970,9 |
| 16,55 | 107,50 | 189,2 | 3 970,9 |
| **16,60** | **107,55** | **308,3** | **5 583,7** |

Bước nhảy 189 → 308 cho thấy có nhánh nhập lưu ở giữa ⇒ **ô 308 nhiều khả năng nằm dưới chỗ hợp lưu**.

## 4. ⚠️ Vấn đề lớn nhất — có thể không tách được sông Hương và sông Bồ

89 ô có dữ liệu nhưng chỉ **43 giá trị q_mean phân biệt** — nhiều điểm lấy mẫu rơi vào cùng một ô GloFAS gốc. Và trong cả vùng chỉ tìm được **một** dòng chảy > 100 m³/s.

Cả hai trạm đều nằm sát dòng chảy duy nhất đó:
- Kim Long (16,47 · 107,57) → ô gần nhất trên dòng: (16,45–16,50 · 107,50)
- Phú Ốc (16,55 · 107,47) → ô gần nhất trên dòng: (16,55 · 107,50) — **cùng giá trị với (16,50 · 107,50)**

Nghĩa là ở độ phân giải ~5 km, **GloFAS có thể không phân giải sông Hương và sông Bồ thành hai dòng riêng**.

### Việc phải làm trước khi crawl (G, W1)

1. **Mở OpenStreetMap, đối chiếu bằng mắt**: dòng chảy ở kinh độ 107,50 là sông Hương, sông Bồ, hay đã là dòng hợp lưu? Máy không trả lời được câu này.
2. Nếu **tách được hai dòng** → chọn hai ô riêng, làm hai ánh xạ H→Q riêng như thiết kế.
3. Nếu **không tách được** → chọn một trong hai hướng, ghi rõ lý do:
   - **(a)** Thu hẹp còn **một trạm duy nhất (Kim Long / sông Hương)**, bỏ Phú Ốc. Đơn giản, trung thực, đủ cho 9 tuần. ⬅ khuyên dùng
   - **(b)** Coi ô hợp lưu là **hệ thống sông Hương – sông Bồ gộp**, và đổi cách phát biểu bài toán cho khớp. Không ánh xạ sang BĐ của từng trạm được nữa.
4. Quét thêm về **phía thượng nguồn (nam, lat < 16,40)** nếu muốn tìm điểm tách hai nhánh.

Chọn xong thì cập nhật `src/config.py:RIVER_POINTS`, `docs/THRESHOLDS.md` §2, và `docs/SPEC.md` §10.2 A3.

## 5. Nghiệm thu kèm theo

- **FR-D4 đạt**: trong lượt quét gặp HTTP 429 hai lần, retry luỹ thừa tự phục hồi, không mất ô nào.
- Cache hoạt động: chạy lại lượt quét thứ hai không tốn thêm request nào.
