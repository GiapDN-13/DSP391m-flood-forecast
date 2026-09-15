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

---

# PHẦN 2 — Đã giải quyết bằng phân tích tự động (15/09/2026)

Công cụ: `python -m src.features.river_id` · Hình: `reports/figures/w1_river_id.png`

Không cần nhìn bản đồ bằng mắt. Ba nguồn bằng chứng độc lập, chạy lại được.

## 1. Hình học — sông có tên từ OpenStreetMap

Tải đường tim sông qua Overpass API (`data/external/osm_rivers.json`, có cache).
Vùng có **42 sông có tên**, trong đó có đủ Sông Hương, Sông Bồ, Tả Trạch, Hữu Trạch.

⚠️ Riêng cách này **không đủ**: OSM "Sông Ô Lâu" trải tới vùng phá Tam Giang nên
"sông gần nhất" của ô lớn nhất lại ra Ô Lâu. Gần nhất về khoảng cách **không**
đồng nghĩa đúng về thuỷ văn.

## 2. Tương quan chuỗi lưu lượng

58 ô có dòng chảy nhưng chỉ **35 pixel GloFAS phân biệt** — nhiều toạ độ rơi vào cùng ô.

Lộ ra **hai hệ thống sông tách biệt**:

| Cụm | Ô | Tương quan nội bộ | Tương quan chéo |
|---|---|---|---|
| A — vùng Hương | (16.60·107.55), (16.55·107.50), (16.45·107.50) | 0,95–0,99 | 0,83–0,92 |
| B — phía bắc | (16.90·107.15), (16.85·107.05), (16.75·107.15) | 0,986–0,995 | |

Cụm B là lưu vực khác (Ô Lâu / Thạch Hãn), **loại khỏi phạm vi**.

Trong cụm A, (16.45·107.50) và (16.55·107.50) tương quan **0,992** ⇒ **cùng một dòng**,
nối tiếp thượng–hạ lưu, không phải hai sông.

## 3. ⭐ Suy ngược diện tích lưu vực — bằng chứng quyết định

Lưu lượng trung bình nhiều năm ≈ diện tích lưu vực × dòng chảy đơn vị.
Vùng Huế: mưa ~2 800–3 200 mm/năm, hệ số dòng chảy ~0,45–0,50
⇒ dòng chảy đơn vị **~0,041–0,051 m³/s trên mỗi km²**.

| Ô | Q_tb (m³/s) | Diện tích suy ra (km²) | Đối chiếu |
|---|---|---|---|
| (16.45 · 107.50) | 120,7 | **2 366 – 2 943** | ✅ **sông Hương 2 830 km², lệch 7 %** |
| (16.55 · 107.50) | 194,5 | 3 814 – 4 745 | Hương + Bồ 3 768 km², lệch 12 % |
| (16.60 · 107.55) | 313,3 | 6 144 – 7 643 | ✗ vượt xa cả hai, lệch 81 % |

Ba dòng này nhất quán với nhau và với thứ tự dòng chảy: đi từ thượng xuống hạ lưu,
lưu vực tích luỹ lớn dần — Hương đơn lẻ → Hương cộng Bồ → cộng thêm lưu vực ngoài.

## 4. ✅ Kết luận đã chốt

**Ô dùng cho sông Hương / trạm Kim Long: `(16.45, 107.50)`**
Lưu lượng trung bình 120,7 m³/s · đỉnh 3 588 m³/s · cách đường tim sông Hương 2,93 km.

Đã ghi vào `src/config.py:RIVER_POINTS`, kèm `REJECTED_POINTS` để giải trình.

**Sông Bồ: GloFAS không tách được thành dòng riêng.** Mọi ô ứng viên đều lệch
≥ 84 % so với diện tích lưu vực 938 km². ⇒ **Thu hẹp còn một trạm (Kim Long)**,
đúng như phương án (a) đề xuất ở Phần 1 §4.

## 5. Phải nêu trong Limitations

- Ở độ phân giải ~5 km, GloFAS **không phân giải được sông Bồ (938 km²)** thành dòng riêng ⇒ nghiên cứu giới hạn ở lưu vực sông Hương.
- Ô lưới cách trạm Kim Long ~2,9 km theo đường tim sông; mạng sông mô phỏng lệch khỏi vị trí thật.
- Diện tích lưu vực là **suy ra từ dòng chảy đơn vị giả định**, không phải đo đạc. Sai số ±10 % của dòng chảy đơn vị kéo theo ±10 % diện tích. Dù vậy ba ô xếp đúng thứ tự và biên độ, nên kết luận **tương đối** (ô nào lớn hơn ô nào) vững hơn con số tuyệt đối.

## 6. Ba cách đều có thể sai ở đâu

| Cách | Điểm yếu |
|---|---|
| Hình học OSM | Tên sông gần cửa biển chồng lấn; gần nhất ≠ đúng |
| Tương quan | Hai sông kề nhau cùng chịu một trận mưa vẫn tương quan cao |
| Diện tích suy ra | Phụ thuộc dòng chảy đơn vị giả định |

Ba cách **hội tụ về cùng một kết luận** nên độ tin cậy cao hơn bất kỳ cách đơn lẻ nào.
Một phép kiểm tôi đã **bỏ** vì không đáng tin: cân bằng khối lượng (cộng lưu lượng
hai nhánh). Hai ô nối tiếp trên cùng một dòng cộng lại vẫn ra đúng số do đếm trùng
phần thượng nguồn — bản đầu đã suýt kết luận sai vì phép này.
