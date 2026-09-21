# CRAWL GIẢI THÍCH CẶN KẼ — làm gì, làm sao, ra cái gì

Đọc file này nếu bạn muốn hiểu `src/ingest/crawl_all.py` mà không phải đọc 430
dòng code. Viết cho cả người sẽ bị hỏi ở vấn đáp, không riêng người viết code.

---

## 1. Vì sao phải crawl — mô hình cần gì

Mục tiêu dự án: **hôm nay dự báo lưu lượng sông Hương 1, 2, 3 ngày tới**. Để
huấn luyện một mô hình như vậy, mỗi ngày trong quá khứ phải có đủ ba nhóm số:

| Nhóm | Câu hỏi nó trả lời | Lấy ở đâu |
|---|---|---|
| **Lưu lượng** ngày hôm đó và 14 ngày trước | "Sông đang ở mức nào, đang lên hay xuống?" | Open-Meteo Flood API (GloFAS v4) |
| **Mưa** trên lưu vực, nhiều ngày trước | "Bao nhiêu nước vừa rơi xuống thượng nguồn?" | Open-Meteo Archive API (ERA5) |
| **Mưa dự báo** cho 1–3 ngày tới | "Sắp mưa thêm bao nhiêu?" | Open-Meteo Historical Forecast API |

Nhóm thứ ba là chỗ hay bị hiểu sai. Khi **vận hành thật** (mai dự báo cho ngày
mốt) ta chỉ có **mưa dự báo**, không có mưa thực đo. Nên nếu huấn luyện bằng
mưa thực đo rồi vận hành bằng mưa dự báo thì mô hình được cho ăn hai loại số
khác nhau — kết quả đo trong phòng sẽ đẹp hơn thực tế. Vì vậy phải crawl thêm
**mưa dự báo đã phát trong quá khứ**, để có kịch bản B (`RESEARCH_DESIGN.md` §2).

> Đây là toàn bộ lý do có pha `fc_rain`. Không phải để nhiều dữ liệu cho oai.

---

## 2. Bốn API, ba việc khác nhau

```
flood-api.open-meteo.com/v1/flood                 → lưu lượng sông, theo NGÀY
archive-api.open-meteo.com/v1/archive             → ERA5 thực đo (mưa, nhiệt, gió)
historical-forecast-api.open-meteo.com/v1/forecast→ dự báo ĐÃ PHÁT trong quá khứ
api.open-meteo.com/v1/forecast                    → dự báo 7 ngày tới (job hằng ngày)
```

Ba cái đầu dùng khi crawl lịch sử. Cái thứ tư chỉ dùng trong
`src/models/predict_daily.py` chạy mỗi sáng trên GitHub Actions.

Tất cả **miễn phí, không cần API key** — đây là một trong những lý do chọn đề
tài này (`DSP391m_Ke_hoach_du_an_1.pdf` §1): không có nguy cơ bị chặn giữa kỳ.
Giấy phép **CC BY 4.0**, bắt buộc trích dẫn trong mọi báo cáo.

---

## 3. Vì sao là *lưới điểm*, không phải một điểm

API trả dữ liệu cho **một toạ độ mỗi lần gọi**. Nhưng:

- **Lưu lượng:** ta chưa biết ô lưới nào thật sự nằm trên sông Hương. GloFAS
  phân giải ~5 km nên dòng sông trong mô hình lệch so với sông thật vài km.
  Toạ độ trong kế hoạch gốc `(16.46, 107.59)` cho `q_mean` chỉ **5,7 m³/s**,
  trong khi ô cách đó không xa cho **308 m³/s**. Muốn biết ô nào đúng thì phải
  **quét cả vùng rồi so sánh**.
- **Mưa:** mưa gây lũ ở Huế rơi ở **thượng nguồn**, cách thành phố 30–50 km.
  Lấy mưa tại một điểm ở Huế là bỏ mất chính cái sinh ra lũ. Phải lấy mưa trên
  **toàn lưu vực** rồi gộp lại.

Hai hộp quét:

| | Phạm vi | Bước | Số ô lý thuyết |
|---|---|---|---|
| Lưu lượng | 16,05–16,95 N · 107,05–107,95 E | 0,05° (~5,5 km) | 19 × 19 = **361** |
| Mưa | 16,10–16,80 N · 107,10–107,80 E | 0,10° (~11 km) | 8 × 8 = **64** |

Bước lưới chọn theo phân giải của nguồn: lấy dày hơn 5 km cho GloFAS là vô
nghĩa vì các ô kề nhau sẽ ra cùng một giá trị.

---

## 4. Năm pha, và cái mẹo tiết kiệm quan trọng nhất

`PHASES` trong code xếp theo **giá trị trên mỗi đơn vị quota**, không theo thứ
tự pipeline:

| # | Pha | Làm gì | Vì sao đứng ở vị trí này |
|---|---|---|---|
| 1 | `rain_daily` | Mưa ngày 2010–2026, mọi ô lưới mưa | Bắt buộc cho mô hình (FR-D2). Rẻ, nên làm trước |
| 2 | `discharge_probe` | Lưu lượng **chỉ năm 2023**, mọi ô trong 361 ô | Rẻ. Mục đích duy nhất: **dò xem ô nào có sông** |
| 3 | `fc_rain` | Mưa dự báo đã phát, 2022-07 → nay | Kịch bản B (FR-D3). Không lấy bây giờ thì mất vĩnh viễn |
| 4 | `discharge_full` | Lưu lượng **chuỗi đầy đủ**, chỉ ô có sông | Đắt nhất trên mỗi ô, nên phải biết ô nào đáng lấy trước |
| 5 | `rain_hourly` | Mưa theo giờ 2015–2026 | Nặng nhất (~189 000 đơn vị quota). Có thì tốt, không có vẫn làm được |

### Mẹo probe → full

Đây là phần thiết kế đáng nói nhất, và là câu trả lời tốt nếu bị hỏi
*"em tối ưu chi phí thu thập như thế nào?"*

```
361 ô  ──probe 1 năm──►  đọc q_mean từng ô  ──lọc q_mean ≥ 1,0 m³/s──►
                                                  sắp theo q_mean giảm dần
                                                  lấy 40 ô đầu
                                          ──full 42 năm──►  chỉ 40 ô
```

Nếu xin chuỗi đầy đủ cho cả 361 ô thì chi phí gấp **9 lần** mà phần lớn là ô
trên núi hoặc trên biển, `river_discharge` gần bằng 0 — vô dụng. Probe một năm
rẻ hơn chuỗi 42 năm khoảng 42 lần, đủ để biết ô nào là sông.

Hai hằng số điều khiển việc này:

```python
FULL_MIN_QMEAN = 1.0    # dưới 1 m³/s thì coi như không phải sông
MAX_FULL_CELLS = 40     # trần số ô xin chuỗi đầy đủ
```

Danh sách task của mỗi pha được dựng **ngay trước khi chạy pha đó**, nên
`discharge_full` đọc được kết quả `discharge_probe` vừa xong trong cùng lượt
chạy. Đây là lý do thứ tự pha không thể đảo.

---

## 5. Output: 1 295 file, ~98 MB

```
data/raw/
├── discharge/          83 file    13 MB   q_<lat>_<lon>.parquet
├── discharge_probe/   316 file     3 MB   qp_<lat>_<lon>.parquet
├── rain_daily/         64 file     7 MB   rd_<lat>_<lon>.parquet
├── rain_hourly/       768 file    74 MB   rh_<lat>_<lon>_<năm>.parquet
├── fc_rain/            64 file     2 MB   fc_<lat>_<lon>.parquet
├── _stale/rain_grid_0.15/  224 file       lưới 0,15° đã loại, giữ để truy nguyên (§8b)
├── _progress.jsonl                        nhật ký từng task
└── _crawl.log / _crawl.err                stdout / stderr
```

**Một file = một ô lưới** (mưa giờ: một ô × một năm, để file không quá to).
Toạ độ nằm ngay trong tên file, nên biết file nào là ô nào mà không cần mở.

### Bên trong file trông như thế nào

`rain_daily/rd_16.1_107.1.parquet` — **6 087 dòng × 8 cột**, một dòng một ngày:

```
        time  precipitation_sum  temperature_2m_mean  ...   lat    lon
0 2010-01-01                0.0                 17.3  ...  16.1  107.1
1 2010-01-02                0.1                 17.7  ...  16.1  107.1
```

`discharge/q_16.05_107.05.parquet` — **15 584 dòng × 4 cột**:

```
        time  river_discharge    lat     lon
0 1984-01-01              NaN  16.05  107.05
1 1984-01-02              NaN  16.05  107.05
```

⚠️ Chú ý cái `NaN` đó. Xem mục 8.

`rain_hourly/rh_16.1_107.1_2015.parquet` — **8 760 dòng** (= 365 × 24) × 6 cột.

Cột `lat`/`lon` được nhét vào **từng dòng** dù lặp lại — có vẻ thừa, nhưng nhờ
vậy gộp 64 file thành một bảng chỉ cần `pd.concat`, không phải tự nhớ file nào
là ô nào. Parquet nén cột lặp lại gần như miễn phí.

---

## 6. Từ 1 295 file thô thành 1 bảng duy nhất

Crawl **không** tạo ra thứ mô hình ăn được. Còn một bước ETL nữa:

```
1 295 file thô
   │
   ├─ src/etl/clean.py        đổi UTC → giờ VN, gộp giờ → ngày,
   │                          kiểm giá trị bất thường (báo lỗi, KHÔNG tự sửa)
   │
   ├─ src/features/build_panel.py
   │     • gộp 64 ô mưa thành 3 tiểu lưu vực: thượng / trung / hạ
   │     • tạo lag 1–14 ngày cho lưu lượng và mưa
   │     • cửa sổ trượt CHỈ LÙI VỀ SAU (không bao giờ center=True)
   │     • chỉ số mưa tích lũy API (k = 0,9, n = 14 ngày)
   │
   ▼
data/processed/daily_panel.parquet     6 087 dòng × 71 cột
```

```
        date  discharge  rain_thuong  rain_trung  rain_ha  rain_basin
0 2010-01-01      32.11     0.000000    0.000000  0.00000  0.000000
1 2010-01-02      31.14     0.333333    0.533333  0.22069  0.362452
```

**6 087 dòng = số ngày từ 2010-01-01 tới 2026-08-31.** Panel bắt đầu 2010 vì
mưa chỉ crawl từ 2010 (scope đã cắt có chủ ý — xem `PLAN.md`), dù lưu lượng có
xa hơn.

Vì sao gộp mưa thành **3 tiểu lưu vực** chứ không để 64 cột riêng: 64 cột mưa ×
14 lag = 896 biến trên 6 087 dòng thì mô hình sẽ học nhiễu. Ba tiểu lưu vực
giữ được thông tin "mưa ở thượng nguồn hay hạ nguồn" — vốn là thông tin có ý
nghĩa thuỷ văn — mà chỉ tốn 3 cột.

---

## 7. Bốn cơ chế để crawl không chết giữa đêm

| Cơ chế | Cách làm | Vì sao cần |
|---|---|---|
| **Resume** | Trước mỗi task, kiểm `dest.exists()`; có rồi thì bỏ qua | Mất mạng lúc 3 giờ sáng thì chạy lại chỉ làm phần còn thiếu. Không có trạng thái nào cần nhớ ngoài chính các file đã ghi |
| **Khoá chống chạy trùng** | `SingleInstance` ghi PID vào lockfile, kiểm bằng `tasklist` | Đã dính đúng lỗi này: `pkill` của Git Bash **không giết được tiến trình Python trên Windows**, nên có lúc 3 crawler chạy song song tự ép nhau vào 429 |
| **Nhịp gọi tự điều chỉnh** | Gặp 429 → nhịp × 1,5 (trần 12 s). Chạy trơn 8 lần → nhịp × 0,75 (sàn 0,7 s) | Nhịp cố định thì hoặc quá chậm hoặc bị chặn. Bản đầu phục hồi quá chậm nên nhịp dính trần 8 s cả đêm |
| **Nhật ký không bao giờ làm chết crawl** | `_log()` dùng `json.dumps(default=str)` trong `try/except` | Đã có lần `numpy.bool_` không serialize được và **giết cả lượt crawl** chỉ vì một dòng log |

Thêm `est_weight()` ước lượng quota mỗi request: `⌈số ngày/14⌉ × ⌈số biến/10⌉`,
nhân 24 nếu là dữ liệu giờ. Dùng để biết pha nào đắt **trước khi** chạy.

---

## 8. Hai chỗ output không như nhãn — phải biết

### 8a. Lưu lượng: 15 584 dòng nhưng chỉ 10 835 ngày có số

```
1984–1996  rỗng 100 %   ← giống nhau ở CẢ 83 ô
1997–2026  có dữ liệu
```

Open-Meteo công bố GloFAS v4 từ 1984; thực tế endpoint **chỉ trả giá trị từ
1997** cho vùng này. API vẫn trả về đủ dòng cho khoảng ngày đã xin, nhưng giá
trị là null — nên nếu chỉ đếm số dòng thì mọi thứ trông hoàn hảo.

Đã sửa nghiệm thu FR-D1 sang **đếm số ngày không rỗng**, và khoá bằng
`tests/test_data_coverage.py`. Chi tiết ở `FINDINGS_EVENTS.md` §3.

> Bài học: **đếm dòng không phải đếm dữ liệu.**

### 8b. Lưới mưa không đều — ✅ đã sửa 21/09/2026

Phát hiện khi viết tài liệu này: 68 ô mưa **không phải một lưới đều**, và cả ba
pha mưa đều bị:

| Pha | Đúng lưới | Ô lạc 0,15° | Thiếu |
|---|---|---|---|
| `rain_daily` | 52 | 16 | 12 |
| `fc_rain` | 54 | 16 | 10 |
| `rain_hourly` | 64 | 16 | 0 |

`aggregate_rain()` lấy **trung bình các ô** trong mỗi dải vĩ độ, nên dải nào có
nhiều ô hơn thì được cân nặng hơn. Tính theo tiểu lưu vực thì lệch rõ:

| Tiểu lưu vực | Đang dùng | Lưới đủ | Lệch |
|---|---|---|---|
| thượng 16,10–16,35 | 30 | 24 | +25 % |
| **trung 16,35–16,55** | **9** | **16** | **−44 %** |
| hạ 16,55–16,85 | 29 | 24 | +21 % |

Dải **trung** — chính là dải chứa trạm Kim Long (16,47) và ô lưới đã chọn
(16,45) — thiếu gần một nửa số ô. Đoạn sông gần điểm dự báo nhất lại là đoạn
có mưa được lấy mẫu kém nhất.

**Đã xử lý:** chuyển 224 file của lưới 0,15° sang `data/raw/_stale/rain_grid_0.15/`
(**không xoá**, để truy nguyên được), crawl 23 ô còn thiếu, dựng lại panel.
Cả ba pha giờ đúng **64 ô lưới đều**.

Mức thay đổi trong panel, đo trực tiếp:

| Cột | TB trước | TB sau | Đổi | Tương quan |
|---|---|---|---|---|
| `rain_thuong` | 8,297 | 8,355 | +0,7 % | 0,9999 |
| **`rain_trung`** | 8,970 | 8,409 | **−6,3 %** | 0,9907 |
| `rain_ha` | 6,788 | 6,641 | −2,2 % | 0,9990 |
| `rain_basin` | 8,018 | 7,802 | −2,7 % | 0,9986 |

Cột `discharge` **không đổi** — đúng như phải vậy, vì chỉ các cột mưa được dựng
lại. **Bốn baseline cũng không đổi một chữ số nào**, vì persistence / seasonal
naive / climatology / ARIMA đều chỉ dùng `discharge`. Thiên lệch này chỉ bắt đầu
có ảnh hưởng thật khi **mưa vào làm feature** — tức từ LightGBM trở đi.

Nói cách khác: sửa sớm thì rẻ, và nếu để tới sau khi train thì phải train lại.

---

## 9. Chi phí thật, đo được

Lượt chạy ngày 15/09/2026, một tiến trình duy nhất:

```
cả 5 pha           ~35 phút
số lần bị 429      0
dung lượng tải     48 MB
pha rain_hourly    14 phút  (ước lượng ban đầu là "189k đơn vị / 19 ngày")
```

Ước lượng ban đầu sai gần 2 000 lần, và cái sai đó **đã từng làm cắt scope
oan** — hạ lưới mưa 0,10° → 0,15° và bỏ hẳn mưa giờ. Nguyên nhân thật không
phải hạn mức API mà là tự chạy trùng nhiều crawler. Đã khôi phục scope.
Đây cũng chính là nguồn gốc của 16 ô lẻ ở mục 8b. Xem `FINDINGS_QUOTA.md` §3.

> Bài học: **đo trước khi cắt.** Một kết luận sai về hạ tầng làm mất scope
> nghiên cứu, và kết luận đó rẻ hơn nhiều so với việc đi cắt.

---

## 10. Chạy lại thế nào

```powershell
python -m src.ingest.crawl_all              # chạy cả 5 pha, tự bỏ qua file đã có
python -m src.ingest.crawl_all --phase rain_daily fc_rain
```

Không cần dọn gì trước. Muốn crawl lại một ô thì **xoá file của ô đó** rồi chạy
lại — resume dựa trên sự tồn tại của file, không có state ẩn ở đâu khác.

Theo dõi khi đang chạy:

```powershell
Get-Content data/raw/_crawl.log -Wait      # log cuộn theo thời gian thực
start reports/live/index.html               # màn hình theo dõi, dark mode
```

Máy trắng, chưa có dữ liệu thì **đừng crawl lại** — tải bản sao lưu nhanh hơn
nhiều:

```powershell
python scripts/restore_data.py --all        # 95 MB từ GitHub Release
```

---

## 11. Nếu bị hỏi ở vấn đáp

Bốn câu dễ bị hỏi nhất về phần này, và câu trả lời ngắn:

**"Vì sao crawl 361 ô mà chỉ dùng 1 ô?"**
361 ô là để **tìm** ô đúng, không phải để dùng hết. Toạ độ trong kế hoạch ban
đầu sai (5,7 so với 308 m³/s). Ba bằng chứng độc lập mới chốt được
`(16,45; 107,50)`: hình học sông từ OpenStreetMap, phân cụm tương quan lưu
lượng, và suy diện tích lưu vực từ dòng chảy đơn vị. 83 ô có chuỗi đầy đủ vẫn
dùng cho phân cụm tương quan.

**"Vì sao mưa chỉ từ 2010 mà lưu lượng từ 1984?"**
Mưa đắt hơn lưu lượng nhiều lần trên mỗi năm dữ liệu. 16 năm × mùa lũ là đủ
mẫu huấn luyện, còn chuỗi lưu lượng dài thì cần cho phân vị và ghép sự kiện lũ
cũ. Là scope cắt có chủ ý, ghi trong `PLAN.md`. *(Và lưu lượng thực chỉ có từ
1997 — xem mục 8a.)*

**"Vì sao cần cả mưa thực đo và mưa dự báo?"**
Vì khi vận hành chỉ có mưa dự báo. Huấn luyện bằng mưa thực đo rồi vận hành
bằng mưa dự báo là tự cho mình điểm cao hơn thực tế. Kịch bản A dùng mưa thực
đo, kịch bản B dùng mưa dự báo — báo cáo cả hai.

**"Dữ liệu này có phải big data không?"**
Riêng mưa giờ là 768 file, 74 MB, ~6,7 triệu bản ghi; nếu lấy đủ 40 năm × 200
điểm như kế hoạch gốc ước tính thì khoảng 70 triệu bản ghi. Nhưng điểm đáng nói
không phải khối lượng — mà là **dữ liệu đến từ 4 API khác nhau, khác múi giờ,
khác tần suất, khác phân giải không gian, và một nguồn đổi chế độ giữa chuỗi**
(mốc 2022-07-01). Đó mới là phần khó.

---

## Liên quan

- `docs/FINDINGS_GRID.md` — chọn ô lưới, ba bằng chứng độc lập
- `docs/FINDINGS_QUOTA.md` — chi phí crawl và kết luận sai đã sửa
- `docs/FINDINGS_EVENTS.md` §3 — chuỗi lưu lượng bắt đầu 1997
- `docs/DATA_DICTIONARY.md` — ý nghĩa từng cột
- `docs/RUNBOOK.md` §4 — khôi phục dữ liệu từ bản sao lưu
