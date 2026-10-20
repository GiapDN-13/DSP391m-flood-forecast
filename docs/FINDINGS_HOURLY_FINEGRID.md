# PHÁT HIỆN: Mưa mịn hơn, theo giờ, Spark và Deep Learning (Report 3–4)

**Ngày:** 20/10/2026 · Nhánh `feat/hourly-finegrid`

Thầy góp ý ba điều. Một là dùng ô lưới mịn hơn 5 km. Hai là dùng bước thời gian theo giờ thay vì theo ngày. Ba là ở Report 4, xử lý dữ liệu phân tán và huấn luyện bằng Spark, nếu làm được Deep Learning thì càng tốt. File này tổng hợp những gì nhánh đã làm cho ba yêu cầu đó.

Mọi con số ở đây đều đã được **chạy lại hoặc đối chiếu với file kết quả trên đĩa** trong đợt kiểm chứng ngày 20/10/2026. Lệnh chạy ở §8, bảng đối chiếu ở §9. Số nào chỉ chép lại từ báo cáo của agent mà chưa kiểm được (thường vì phải dùng mạng hoặc chạy quá lâu) thì có dấu **‡**.

Chạy lại:

    python -m src.features.basins                        # DEM → lưu vực con → trọng số ô lưới
    python -m src.features.hourly_features --source era5 # 54 cột hr_* → daily_panel_hourly.parquet
    python -m src.models.ablation_hourly                 # A / B0 / B / C
    python -m src.models.dl_lstm --jobs 8 --threads 2    # LSTM, MLP so với LightGBM
    docker compose -f infra/spark/docker-compose.yml up -d   # cụm Spark, xem §5

---

## 1. Thầy yêu cầu gì, nhánh này làm được gì

Cần nói rõ ngay từ đầu: **biến mục tiêu vẫn là lưu lượng GloFAS v4, theo ngày, ô ~5 km**. Đổi mưa đầu vào sang lưới mịn hơn hay sang theo giờ không làm biến mục tiêu mịn hơn. Muốn có mục tiêu theo giờ tại đúng trạm thì phải có mực nước giờ Kim Long của ngành KTTV (email đã soạn ở `docs/data_requests/`, chưa gửi, xem §7).

| Yêu cầu | Đã làm | Trạng thái |
|---|---|---|
| Ô mịn hơn 5 km | PERSIANN-CCS 0,04° (~4 km) theo giờ. Lưu vực con cắt từ DEM 30 m, mưa được gộp theo đúng ranh giới lưu vực thay cho 3 dải vĩ độ | Mới tải 2 tháng (10–11/2020). Sản phẩm này **mất gần hết mưa gió mùa đông bắc** (§2) |
| Theo giờ | 54 đặc trưng mưa giờ (ERA5 2015–2026) cho 5 lưu vực con và toàn lưu vực. Đã thêm vào panel và chạy ablation | Có ích ở h=3, yếu ở h=2, ở h=1 thì không phải nhờ thông tin trong ngày (§4) |
| Spark (Report 4) | Cụm Spark standalone thật: 1 master và 2 worker trên Docker. ETL giờ → ngày, đặc trưng giờ, MLlib GBT/RF, LSTM phân tán (TorchDistributor) | Chạy được, kết quả **trùng** Polars. Ở cỡ dữ liệu này Spark **chậm hơn** Polars 10–20 lần (§5) |
| Deep Learning | LSTM nhiều đầu ra và MLP, 8 cấu hình × 3 seed. Chạy đơn tiến trình và DDP 2 rank | **Không thắng LightGBM** ở h=1. Ở h=2–3 nhỉnh hơn chút nhưng không bền (§6) |

---

## 2. Nguồn mưa mịn hơn và theo giờ

Cả bảng được tính lại theo cùng một cách. Lấy trung bình mọi ô nằm trong vùng phủ của 64 ô ERA5 (16,05–16,85° N, 107,05–107,85° E). Mưa được đưa về **giờ kết thúc** theo giờ VN, rồi so với trung bình 64 ô ERA5 (`data/raw/rain_hourly`). Tháng tính theo ngày giờ VN. Hệ số tương quan theo ngày chỉ tính trên những ngày đủ 24 giờ (29–30 ngày mỗi tháng).

| Nguồn | Ô | Bước | Đã có trên máy | 10/2020: tỷ lệ tổng / r giờ / r ngày | 11/2020: tỷ lệ tổng / r giờ / r ngày |
|---|---|---|---|---|---|
| ERA5 (Open-Meteo), mốc so sánh | 0,1° (nội suy, năm 2020 chỉ có 59/64 chuỗi khác nhau) | 1 h | 64 ô, 2015 → 08/2026 | 1 / 1 / 1 | 1 / 1 / 1 |
| **PERSIANN-CCS** | **0,04°** | 1 h | 625 ô, chỉ 10–11/2020 (0,45 MB) | 1,214 / 0,464 / 0,603 | **0,073** / 0,198 / 0,476 |
| IMERG V06B Final (ERDDAP NOAA) | 0,1° | 30 ph | 100 ô, 4/2020 và 10/2020 | 1,164 / 0,580 / 0,786 | — |
| IMERG V07 (Earth Engine) | 0,1° | 30 ph | 100 ô, **01/1998 → 19/10/2026**, 346 file, 47,7 MB | 1,193 / 0,606 / 0,803 | 0,388 / 0,702 / 0,856 |
| GSMaP v8, chỉ vệ tinh (Earth Engine) | 0,1° | 1 h | 100 ô, 01/1998 → 19/10/2026, 346 file, 50,8 MB (cùng file với dòng dưới) | 1,808 / 0,565 / 0,776 | 0,170 / 0,541 / 0,862 |
| **GSMaP v8, hiệu chỉnh theo trạm (GC)** | 0,1° | 1 h | như trên | 1,454 / 0,629 / **0,882** | **0,899** / **0,740** / 0,868 |

Nhận xét:

1. **Chỉ PERSIANN-CCS mịn hơn 5 km**, nhưng tháng 11 nó chỉ ghi được 7 % lượng mưa (49 mm so với 672 mm của ERA5). Thuật toán bỏ qua mây ấm, mà mưa gió mùa đông bắc ở Huế lại đến từ mây thấp (lý giải của agent theo tài liệu ‡). Vì vậy nguồn này **không dùng làm đầu vào một mình được**. Các nguồn khác đều là 0,1° (~11 km).
2. GSMaP bản hiệu chỉnh trạm (GC) gần ERA5 nhất ở tháng 11 và có tương quan theo ngày cao nhất. IMERG V07 chỉ ghi được 39 % mưa tháng 11. Nhưng **gần ERA5 không có nghĩa là đúng**: ERA5 cũng hụt mưa địa hình cực lớn (`FINDINGS_FACTORS.md`, lớp 4). Muốn biết nguồn nào đúng thì phải có mưa trạm (Vrain, KTTV, xem §7).
3. **Quy ước nhãn giờ khác nhau.** ERA5 và PERSIANN-CCS ghi `time` là **cuối** giờ tích luỹ. Earth Engine gắn ảnh IMERG/GSMaP với **đầu** khoảng đo. Bảng trên đã dời trước khi so. **Đã sửa tận gốc (20/10):** `gee_precip.py` nay ghi `time` là cuối khoảng đo, 692 file đã tải được dời theo (+30 phút IMERG, +60 phút GSMaP; dấu `data/raw/gee/_time_is_end.json`). Bản IMERG lấy từ ERDDAP (`imerg.py`) vẫn là đầu khoảng. Dùng tương quan trễ thì không kiểm được chuyện này: đường tương quan gần như phẳng trong khoảng ±1 giờ (GSMaP-GC tháng 10: r = 0,62–0,63).
4. Bản IMERG V07 trên Earth Engine đã phủ đủ 1998 → 10/2026, nên **không cần tài khoản Earthdata để có IMERG cho mô hình nữa**. Bản ERDDAP chỉ có V06 tới 06/2024. Đoạn gần thời gian thực trên Earth Engine là bản Late/Early hay Final thì chưa kiểm ‡. `src/ingest/gee_precip.py` và `data/raw/gee/` (96 MB) do người điều phối viết và tải ngày 20/10 (ngoài 7 agent); ID dự án Google Cloud đọc từ `.env` (không commit), không ghi cứng.
5. Các kiểm chứng sau là của agent PERSIANN và chưa chạy lại được vì cần mạng ‡. Tải bằng nguồn `files` (file gốc của CHRS) và nguồn `gdex` (NCAR) cho số liệu giống hệt nhau trên cả tháng 10/2020. Còn CHRS Data Portal thì lệch lưới.

---

## 3. Lưu vực con từ DEM 30 m

Dữ liệu là Copernicus GLO-30, xử lý bằng pysheds (D8). Lưu vực được chia làm 5 phần không chồng nhau: đập Tả Trạch, đập Bình Điền, đoạn Tả Trạch dưới đập, đoạn Hữu Trạch dưới đập, và đoạn từ ngã ba Tuần tới Kim Long (`src/features/basins.py`).

| Lưu vực | Code (cầu quy đổi) | Đo trên ellipsoid WGS84 | Tham chiếu | Lệch (code / WGS84) |
|---|---|---|---|---|
| Tới Kim Long | 1 543,4 km² | 1 538,1 km² | 1 490 (ĐH Thuỷ lợi ‡) | +3,6 % / +3,2 % |
| Đập Tả Trạch | 670,5 | 668,2 | 717 (QĐ 1606) | −6,5 % / −6,8 % |
| Đập Bình Điền | 506,8 | 505,0 | 515 (QĐ 1606) | −1,6 % / −1,9 % |
| Kiểm tra độc lập: trạm Thượng Nhật | 126,1 (ô sông gần nhất) · 197,9 (ô cách 978 m, dưới một hợp lưu) | | 208 | |

Năm lưu vực con theo code: 670,4 · 506,8 · 88,2 · 185,1 · 92,8 km². Khoảng cách snap cửa ra: Kim Long 498 m, Tả Trạch 196 m, Bình Điền 33 m.

* Con số **2 830 km²** cũ là diện tích **cả hệ thống sông Hương, gồm cả sông Bồ** (nguồn UNESCO-IHP ‡), không phải lưu vực tới Kim Long. Lúc 20:32–20:34 đã sửa trong `config.py` (`KIM_LONG_AREA_KM2 = 1540`), `river_id.py`, `reservoirs.py`, `reservoir_check.py`, đồng thời chạy lại `reservoir_dam_era.csv`.
* Cách tính diện tích ô trong code (cầu bán kính quy đổi) cho số **lớn hơn 0,34 %** so với ellipsoid WGS84 ở 16,3° N. Docstring cũ ghi "< 0,1 %" là sai, đã sửa docstring. Số trong geojson vẫn theo công thức cầu.
* Kiểm hai thuật toán độc lập với nhau. Tích luỹ dòng chảy của pysheds tại cửa ra Kim Long ra đúng 1 684 710 pixel, bằng số pixel của mặt nạ lưu vực cắt bằng BFS.
* 64 ô ERA5 chỉ phủ **92,5 %** lưu vực Kim Long (lưu vực đập Tả Trạch 87,6 %, Bình Điền 93,5 %), vì phần hở nằm phía nam 16,05° N. Lưới PERSIANN-CCS 0,04° phủ 100 %. Trọng số tính lại khớp file CSV (34 dòng ERA5, 140 dòng PCCS; chênh lớn nhất 5e-7, do CSV làm tròn tới 6 chữ số).

---

## 4. Đặc trưng mưa giờ và ablation

Mỗi ngày có 9 đặc trưng: tổng ngày, max 1h/3h/6h, số giờ ≥ 1 mm, giờ đỉnh (sin, cos), mưa 24h tính tới 07h và mưa 72h. Nhân với 5 lưu vực con và toàn lưu vực được 54 cột `hr_*`. Panel `daily_panel_hourly.parquet` có 6 087 × 125, trong đó 4 260 ngày có đặc trưng giờ. Chạy lại cho kết quả giống **từng bit**.

**Ranh giới ngày.** Lấy 64 ô × 366 ngày năm 2020: tổng các nhãn 00–23h trùng `precipitation_sum` của mưa ngày, lệch lớn nhất 1,7e-13 mm. Dời đi ±1 giờ thì lệch tới 27,5–47,5 mm. Vậy ranh giới ngày của đặc trưng giờ khớp với panel.

**Rò rỉ tương lai.** Cắt dữ liệu giờ tại 3 mốc (03/11/2019, 15/10/2020, 30/11/2020) rồi tính lại: mọi ngày trước mốc đều **không đổi ô nào**. Đọc code cũng thấy như vậy. Cửa sổ 3h/6h chỉ nhìn lùi (`_shift_sum` dùng `shift(i)` với i ≥ 1). `r24_7h` ngày t lấy các nhãn từ 08h ngày t−1 đến 07h ngày t. `r72h` là tổng ba ngày t, t−1 và t−2. Trong `dl_lstm.py` cũng không có rò rỉ: cửa sổ chỉ chứa X[t−L+1..t], bộ chuẩn hoá fit trên train, early stopping dùng valid, tập test không tham gia chọn mô hình.

**Ablation** dùng LightGBM, cùng tham số với `lgbm.py`, 3 seed. **Split riêng**: train 2015–2020, valid 2021 → 06/2022, test từ 07/2022. Vì vậy cấu hình A ở đây (0,715) **không so được** với `lgbm_results.csv` (0,747, train từ 2010).

| Cấu hình | NSE test h1 | h2 | h3 | NSE valid h1 | h2 | h3 |
|---|---|---|---|---|---|---|
| Persistence | 0,542 | 0,008 | −0,198 | 0,483 | −0,324 | −0,712 |
| A: panel gốc | 0,715 | 0,416 | 0,168 | 0,687 | 0,218 | 0,021 |
| B0: A + tổng ngày theo lưu vực DEM (không có thông tin trong ngày) | **0,726** | 0,421 | 0,167 | 0,686 | 0,210 | 0,032 |
| B: A + 9 cột giờ toàn lưu vực | 0,723 | **0,431** | 0,183 | 0,713 | **0,237** | **0,043** |
| C: A + 45 cột giờ lưu vực con | 0,722 | 0,429 | **0,184** | **0,723** | 0,235 | 0,042 |

Tách theo từng seed (42 / 7 / 2026) thì kết luận không mạnh như nhìn trung bình:

1. **h=3: mưa giờ giúp đều tay.** B hơn A +0,016 / +0,007 / +0,022. C hơn A +0,017 / +0,017 / +0,016.
2. **h=2: yếu.** B hơn A +0,003 / **+0,041** / +0,001, nên mức +0,015 trung bình gần như chỉ do seed 7. C hơn A +0,009 / +0,025 / +0,006.
3. **h=1: phần tăng không đến từ thông tin trong ngày.** B0, vốn chỉ có tổng ngày gộp theo lưu vực DEM, đã ngang với B và C. Với riêng seed 42, khoảng tin cậy 95 % (bootstrap khối 30 ngày) của ΔNSE ở h1 với B là [−0,018; +0,022].
4. **Chia lưu vực con (C) không hơn gộp toàn lưu vực (B).** Mưa giờ ERA5 giữa các lưu vực con tương quan 0,665–0,918, tức ERA5 quá thô để tách được các lưu vực con.
5. Đỉnh lũ vẫn bị đoán thấp (peak_bias −0,48 đến −0,88). POD mức 1 ở h2/h3 vẫn bằng 0. Ở h1 POD tăng từ 0,376 (A) lên 0,409 (B) và 0,419 (C), trên 31 ngày dương.

Chạy lại riêng seed 42 cho ra 24/24 dòng (4 cấu hình × 3 horizon × 2 giai đoạn) **trùng khớp** với `reports/ablation_hourly.csv`, mất 39 s.

---

## 5. Spark: kiến trúc, đo đạc, và quy mô thật

```
Windows 11 (16 nhân, 16 GB)
└─ Docker Desktop
   ├─ spark-master            (apache/spark 4.1.3, Java 21, Python 3)
   ├─ spark-worker-1  4 lõi · 2 GB  ┐ executor
   └─ spark-worker-2  4 lõi · 2 GB  ┘ executor
   repo mount vào /opt/repo ở cả 3 container, đóng vai ổ dùng chung (thay HDFS/S3)
```

Chạy thẳng trên Windows thì Spark không đọc parquet được vì thiếu winutils. Khi đó dữ liệu đi đường vòng Polars → Arrow → Spark. Đường này chỉ dùng cho pytest và chạy thử.

| Job | Làm gì | Kiểm lại |
|---|---|---|
| `spark_etl.py` | 768 file, 6 544 896 dòng giờ → 272 704 dòng ô × ngày, và 21 305 dòng theo 5 lưu vực con | Chạy lại trên cụm 2 worker và trên Windows `local[8]`. Hai kết quả trùng nhau và trùng bản cụm đã lưu. So với Polars trùng mọi cột mưa, `t2m_mean` lệch 0,001 do làm tròn |
| `spark_hourly.py` | 54 cột `hr_*`, giống `hourly_features.py` | File của cụm so với Polars chạy trên Windows: chỉ `hr_peak_sin_*` lệch 1 ulp (1,1e-16) ở 345–435 ô mỗi cột, do thư viện sin của Linux và Windows khác nhau |
| `spark_train.py` | GBT và RF trên MLlib. Chọn tham số bằng vòng lặp trên valid cố định, không dùng CV ngẫu nhiên | Chỉ đối chiếu với CSV. Chưa chạy lại vì mất 1 706 s ‡ |
| `spark_dl.py` | LSTM DDP 2 rank qua TorchDistributor hoặc barrier stage | Chạy lại chế độ barrier trên Windows: NSE trùng CSV |

**Thời gian ETL, ô × ngày** (`seconds_etl` = đọc + tính + ghi, không tính khởi động JVM):

| Cấu hình | Agent đo (2 lần) | Kiểm lại |
|---|---|---|
| Cụm 2 worker × 4 lõi | 40,5–41,2 s | 33,9 s |
| Cụm 1 worker × 4 lõi | 38,2 s | — |
| Cụm 1 worker × 1 lõi | 94,7–100,8 s | — |
| `local[8]` trong container | 32,6–32,9 s | — |
| Windows `local[8]`, qua Arrow | 60,0 s | 49,9 s và 55,5 s |
| Polars trong container | 8,7–10,1 s | — |
| Polars trên Windows | 3,4–3,7 s | 2,9 s và 3,0 s |

**Nói thật về quy mô.** Dữ liệu đầu vào chỉ 74 MB và vừa trong RAM một máy. Spark chậm hơn Polars 10–20 lần. Tăng từ 4 lõi trên 1 worker lên 8 lõi trên 2 worker không nhanh thêm. Agent đo được hai nguyên nhân: đọc qua ổ mount từ Windows sang Docker mất 14–63 s, và phân hoạch bị lệch ‡. Ba container cùng nằm trên **một máy vật lý**, nên chạy "phân tán" ở đây chứng minh được rằng pipeline chạy đúng khi tách executor, chứ chưa chứng minh được lợi ích về tốc độ. Report 4 nên trình bày đúng như vậy. Kể cả khi tải đủ PERSIANN-CCS 2003–2026 (625 ô × ~208 nghìn giờ ≈ 130 triệu dòng, tức gấp ~20 lần ERA5 hiện có), dữ liệu vẫn trong tầm một máy chạy Polars.

**Lỗi đã sửa trong đợt kiểm chứng.** Bản đầu cho `peak_hour` theo lưu vực con lệch giữa Windows và cụm ở 79/21 305 dòng. Nguyên nhân: mưa lưu vực con là trung bình có trọng số, lệch cỡ 1e-17 tuỳ thứ tự cộng, nên hai giờ thực ra bằng nhau lại bị coi là khác nhau. Đã sửa `spark_etl.py` để làm tròn mưa tới 0,001 mm trước khi tìm giờ đỉnh. Sau khi sửa, Windows và cụm trùng 21 305/21 305 dòng ở mọi cột. Thư mục `data/interim/spark/rain_subbasin_daily/` đã được ghi lại bằng lần chạy trên cụm.

**MLlib so với LightGBM** (NSE test, học trên train+valid, theo `reports/spark_results.csv`): GBT 0,699 / 0,429 / 0,182; RF 0,687 / 0,454 / 0,214; LightGBM 0,747 / 0,420 / 0,175. Ở h1 LightGBM vẫn tốt nhất. RF nhỉnh hơn ở h2/h3, nhưng mới chỉ trên một lần chia dữ liệu.

**DL phân tán.** TorchDistributor **không chạy được trên Windows**: torchrun cần libuv mà bản torch cho Windows không có. Trên Windows phải dùng chế độ barrier. DDP 2 rank cho NSE 0,7115 / 0,4133 / 0,1602 ở mọi cách chạy. Tôi chạy lại chế độ barrier trên Windows và ra đúng các số đó, `train()` mất 19,3 s, wall 28,6 s. Chạy 1 tiến trình mất 16,1–19,0 s (theo CSV). Trên cụm, `train()` mất 9,9–10,4 s so với 9,0–9,5 s khi chạy 1 tiến trình (theo CSV). Mô hình chỉ có 19 395 tham số và 2 162 mẫu train, nên DDP chỉ tốn thêm công đồng bộ mà không nhanh hơn.

---

## 6. Deep Learning so với LightGBM

> **Cập nhật 20/10:** bảng dưới là MỘT lần chia. Walk-forward 13 fold (§12.2) cho thấy DL **không** hơn LightGBM một cách vững ở horizon nào; mục 3 bên dưới ("phụ thuộc số luồng") cũng đã được đo lại và **bác bỏ**.

Panel ngày, split chính (train ≤ 2015, valid tới 06/2022, test từ 07/2022), học trên train+valid, tính trên tập test. Số là trung bình ± độ lệch chuẩn qua 3 seed (`reports/dl_results.csv`).

| Mô hình | NSE h1 | NSE h2 | NSE h3 | peak_bias h2 | KGE h2 | CSI mức 1, h1 |
|---|---|---|---|---|---|---|
| Persistence | 0,542 | 0,008 | −0,198 | −0,648 | 0,504 | 0,319 |
| **LightGBM** (chạy lại, khớp `lgbm_results.csv`) | **0,747** | 0,420 | 0,175 | −0,758 | 0,270 | 0,394 |
| LSTM chọn **theo valid** (L=14, đủ cột panel) | 0,709 ± 0,018 | 0,404 ± 0,002 | 0,171 ± 0,017 | −0,765 | 0,310 | 0,380 |
| LSTM L=30, MSE | 0,725 ± 0,016 | 0,446 ± 0,018 | 0,198 ± 0,021 | −0,734 | 0,342 | 0,413 |
| LSTM L=30, không dùng phần dư | 0,735 ± 0,043 | 0,479 ± 0,067 | 0,208 ± 0,047 | −0,718 | 0,342 | 0,375 |
| LSTM L=30, loss nhấn đỉnh | 0,692 ± 0,015 | 0,451 ± 0,044 | 0,178 ± 0,059 | **−0,586** | **0,570** | 0,417 |
| LSTM L=14, loss nhấn đỉnh | 0,706 ± 0,018 | 0,430 ± 0,020 | 0,163 ± 0,081 | −0,657 | 0,513 | **0,454** |
| MLP trên cột lag, MSE | 0,712 ± 0,025 | 0,421 ± 0,016 | 0,194 ± 0,013 | −0,755 | 0,307 | 0,353 |
| MLP trên cột lag, loss nhấn đỉnh | 0,713 ± 0,029 | **0,490 ± 0,003** | **0,220 ± 0,067** | −0,611 | 0,535 | 0,395 |
| Spark RF (tham khảo, 1 seed) | 0,687 | 0,454 | 0,214 | −0,751 | 0,326 | — |

Ngưỡng mức 1 là 806 m³/s (Q95 mùa lũ trên train+valid), tập test có 31 ngày vượt ngưỡng. Bộ phân loại LightGBM riêng đạt CSI 0,556 (`classifier_results.csv`, không chạy lại ‡), cao hơn mọi mô hình hồi quy trong bảng.

**Kết luận:**

1. **h=1: LightGBM vẫn tốt nhất.** Không cấu hình DL nào vượt 0,747.
2. **Cấu hình LSTM chọn trước bằng valid thua LightGBM ở cả 3 horizon.** Các cấu hình "nhỉnh hơn ở h2/h3" là chọn sau khi đã nhìn tập test, trong số 8 cấu hình, nên lạc quan.
3. **Kết quả DL phụ thuộc số luồng torch.** Đây là phát hiện của đợt kiểm chứng. MLP nhấn đỉnh, seed 7, chạy với 2 luồng cho 0,746 / 0,494 / 0,143, trùng CSV. Với 1 luồng thì ra 0,766 / 0,546 / 0,191, với 4 luồng ra 0,752 / 0,520 / 0,152. Thứ tự cộng số thực đổi thì early stopping dừng ở epoch khác. Mức dao động này **ngang với độ lệch giữa các seed**, nên khoảng chênh 0,02–0,07 ở h2/h3 chưa phải là cải thiện bền. Muốn tái lập đúng CSV thì phải chạy `--threads 2`. LSTM L=30 seed 42 chạy lại với 4 luồng vẫn ra đúng 0,709 / 0,432 / 0,180.
4. **Loss nhấn đỉnh làm đúng việc của nó.** Đỉnh lũ bớt bị cắt (peak_bias h2 từ −0,73 xuống −0,59) và KGE tăng mạnh. Đổi lại FAR mức 1 tăng (h1: 0,26 so với 0,20).
5. Nếu chỉ học trên train (không học lại trên train+valid), MLP lag MSE đạt 0,762 ở h1, cao hơn LightGBM. Thứ hạng đổi theo cách học, thêm một dấu hiệu cho thấy chênh lệch giữa các mô hình nhỏ hơn độ bất định.
6. Mọi mô hình vẫn dưới 0,5 ở h2–h3. Giới hạn nằm ở biến mục tiêu GloFAS và ở chỗ chưa có mưa dự báo (`FINDINGS_FACTORS.md` §5), không nằm ở chọn kiến trúc mô hình.

---

## 7. Việc còn chờ người dùng và người điều phối

**Tài khoản, liên hệ**

- Earthdata (NASA): IMERG cho mô hình nay đã có qua Earth Engine (§2), nên chỉ cần tài khoản này nếu muốn tải thẳng từ GES DISC (`src/ingest/imerg.py --source gesdisc`).
- Email gửi KTTV và WATEC (`docs/data_requests/`) chưa gửi. Cần làm mấy việc sau.
  - Nhóm và GVHD quyết định có gửi không, vì ngày 15/09 nhóm đã loại hướng R1.
  - Điền MSSV, email, SĐT, tên GVHD.
  - Xin giấy giới thiệu của Trường và điền Mẫu 04.
  - Xác minh địa chỉ email của Đài qua tổng đài 19001260.
  - Chuẩn bị phí, ước tính khoảng 6,2–6,6 triệu đồng cho H giờ mùa lũ 2 trạm × 11 năm ‡.

**Tải toàn bộ.** PERSIANN-CCS mùa lũ 2003–2024 qua `--source gdex`, agent ước tính mất 1,4–1,7 giờ và chiếm ≤ 35 MB ‡. Nhưng vì §2 cho thấy nguồn này mất mưa tháng 11, nên ưu tiên **GSMaP-GC / IMERG V07 đã có**.

**Sửa file dùng chung** — ĐÃ LÀM ngày 20/10 trừ mục môi trường:

- `requirements.txt`: thêm `pyspark==4.1.3`, `shapely==2.2.0`, `pyproj==3.8.0`, `rasterio==1.5.2`, `pysheds==0.5`, `scipy==1.17.1`, `h5py==3.14.0`, `earthengine-api==1.7.49`. ✅
- **Môi trường đang lệch** so với file ghim phiên bản. Máy có scikit-learn 1.9.0 (ghim 1.6.0) và torch 2.13 (ghim 2.5.1). Với sklearn 1.9, LightGBM 4.5 báo `TypeError: check_X_y() got an unexpected keyword argument 'force_all_finite'` khi nhận mảng numpy (đã thử lại). Nên cài lại đúng sklearn 1.6.0 hoặc nâng LightGBM lên ≥ 4.6. ⏳ chưa làm — đổi môi trường cần cả nhóm thống nhất.
- `.gitignore`: thêm `!data/external/basins/` và `!data/external/basins/**` (~204 KB). ✅
- `infra/spark/Dockerfile`: thêm `RUN pip3 install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu`. ✅
- Bằng chứng đo đạc đang nằm trong `data/interim/spark/` (bị gitignore): `etl_benchmark.csv`, `hourly_parity_*.csv`, `train_grid.csv`. ✅ đã chép sang `reports/spark/`.
- Ngoài phần việc của 7 agent, các file sau đã bị sửa: `src/features/build_panel.py` (ép kiểu Int64 khi join ONI, 19:57), `config.py`, `river_id.py`, `reservoirs.py`, `reservoir_check.py`, `FINDINGS_GRID.md`, `FINDINGS_FACTORS.md`, `RISKS.md`, `RESEARCH_DESIGN.md` (20:32–20:34, sửa 2 830 → 1 540 km² sau khi đối chiếu UNESCO-IHP Viet Nam-8). Do người điều phối làm theo yêu cầu của người dùng; commit riêng.

---

## 8. Lệnh tái lập

```bash
export PYTHONIOENCODING=utf-8
python -m src.features.basins                          # ~1 phút
python -m src.features.hourly_features --source era5   # ~1 s
python -m src.models.ablation_hourly                   # ~1,5 phút
python -m src.models.dl_lstm --jobs 8 --threads 2      # ~2,4 phút; PHẢI giữ --threads 2
python -m src.distributed.spark_etl --mode local --cores 8 --partitions 16 --tag win_local8
python -m src.distributed.spark_etl --engine polars --tag win_polars
docker compose -f infra/spark/docker-compose.yml up -d   # Git Bash: MSYS_NO_PATHCONV=1 trước docker exec
docker exec dsp-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 src/distributed/spark_etl.py --mode cluster --cores-max 8 --executor-cores 4 --partitions 16
docker exec dsp-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --driver-memory 2g src/distributed/spark_train.py --mode cluster --cores-max 8 --executor-cores 4 --executor-memory 1800m --models rf,gbt
docker compose -f infra/spark/docker-compose.yml down
python -m src.distributed.spark_dl --engine barrier --procs 2 --threads 2 --tag win_barrier_2x2
python -m src.ingest.persiann_ccs --start 2020-10-01 --end 2020-11-30 --source gdex --workers 4
python -m src.ingest.imerg --start 2020-10 --end 2020-10
python -m src.ingest.gee_precip --dataset gsmap --start 2020-10 --end 2020-11   # cần ee.Authenticate() + EE_PROJECT trong .env
python -m pytest -q && python -m ruff check src tests
```

---

## 9. Phụ lục: số agent báo và số kiểm lại

| Mục | Agent báo | Kiểm lại | Cách kiểm |
|---|---|---|---|
| pytest toàn repo | — | **131 passed** (90 s); ruff sạch | trước và sau khi sửa |
| Diện tích Kim Long | 1 543,4 km² (polygon 1 538,1) | 1 543,4 (cầu) · **1 538,1 (raster lẫn polygon, WGS84)** | `delineate()` trong bộ nhớ; đếm pixel × diện tích Geod |
| Tả Trạch / Bình Điền | 670,5 / 506,8 | 670,5 / 506,8 (cầu) · 668,2 / 505,0 (WGS84) | như trên |
| Thượng Nhật; snap cửa ra | 126,1 / 197,9; 498 / 196 / 33 m | như báo | `delineate()` |
| Phủ ERA5 / PCCS; số dòng trọng số | 92,5 % / 100 %; 34 / 140 | như báo; chênh lớn nhất 5e-7 | `grid_coverage`, `cell_weights` |
| Panel giờ | 6 087 × 125, 54 cột, 4 260 ngày | trùng từng bit | chạy lại vào thư mục tạm |
| Ranh giới ngày | lệch 1,1e-13 mm (1 ô) | 1,7e-13 mm (64 ô, 2020); ±1 h → 27,5–47,5 mm | tổng nhãn 00–23 so với `rain_daily` |
| Không rò rỉ | 289/289 ngày (1 mốc) | 0 ô khác ở 3 mốc | cắt dữ liệu rồi tính lại |
| Ablation NSE test | A 0,715/0,416/0,168 · B 0,723/0,431/0,183 · C 0,722/0,429/0,184 · B0 0,726/0,421/0,167 | trùng CSV; seed 42 chạy lại 24/24 dòng trùng | `ablation_hourly` với SEEDS=(42,) |
| PCCS so với ERA5 theo lưu vực | 0,852 / 0,321 / 0,432 | như báo | `hourly_features --source pccs` |
| PCCS 10/2020; 11/2020 | 1,211 / 0,466 / 0,603; 0,072 | 1,214 / 0,464 / 0,603; 0,073 (theo tháng giờ VN) | script riêng |
| IMERG V06 10/2020 | 1,164 / 0,580 / 0,784; 148 800 dòng | 1,164 / 0,580 / 0,786; 148 800 dòng | script riêng |
| Spark ETL dòng vào → ra | 6 544 896 → 272 704 | như báo | chạy lại trên cụm và trên Windows |
| Spark = Polars (ô) | 0 lệch, `t2m_mean` 0,001 | như báo; Windows = cụm | `compare_outputs` |
| Spark lưu vực con | 21 305 dòng | 21 305; **peak_hour lệch 79 dòng giữa hai nền tảng → đã sửa, nay 0** | so lần chạy Windows với lần chạy cụm |
| ETL cụm 2×4 / Windows / Polars | 40,5–41,2 / 60,0 / 3,4–3,7 s | 33,9 / 49,9–55,5 / 2,9–3,0 s | chạy lại |
| spark_hourly so với Polars | peak_sin lệch 1 ulp ở 351–435 ô/cột | 1,11e-16 ở **345**–435 ô/cột | file cụm so với Polars Windows |
| MLlib GBT / RF | 0,699/0,429/0,182 · 0,687/0,454/0,214 | trùng CSV | đọc CSV (không chạy lại) |
| LSTM L30 MSE | 0,725±0,016 / 0,446±0,018 / 0,198±0,021 | trùng CSV; seed 42 chạy lại 0,709/0,432/0,180 | `train()` |
| MLP nhấn đỉnh, seed 7 | 0,746 / 0,494 / 0,143 | **chỉ trùng khi chạy 2 luồng** | `train()` với 1, 2, 4 luồng |
| DDP 2 rank | 0,7115 / 0,4133 / 0,1602 | như báo | `spark_dl --engine barrier` |
| Dữ liệu mới trên E: | — | ~241 MB (DEM 120, GEE 96, interim/spark 7,8 MB…); ổ E: còn 7,4 GB | `du`, `find -newer` |
| Bản tin KTTV, Vrain, biểu phí, độ trùng files/GDEX của PCCS, CHRS Portal | xem báo cáo agent | **không kiểm lại** ‡ | cần mạng |

---

## 10. Vấn đề còn tồn tại

| Mức | Vấn đề | Đề xuất |
|---|---|---|
| Trung bình | Kết quả DL phụ thuộc số luồng torch, dao động ngang độ lệch giữa các seed | Báo cáo kèm dao động theo số luồng; luôn chạy `--threads 2` |
| Trung bình | Ablation B ở h2: phần tăng gần như chỉ do một seed | Ở Report 3 chỉ kết luận chắc cho h3 |
| Trung bình | Môi trường lệch so với `requirements.txt` (sklearn 1.9 / torch 2.13) | Đã thêm 8 gói còn thiếu; còn phải thống nhất phiên bản sklearn/LightGBM (§7) |
| Đã xử lý | File dùng chung bị sửa ngoài phần việc của 7 agent | Do người điều phối; commit riêng |
| Đã sửa | Nhãn giờ IMERG/GSMaP (đầu khoảng) khác ERA5/PCCS (cuối giờ) | `gee_precip.py` ghi cuối khoảng; dữ liệu đã dời |
| Đã sửa | `gee_precip.py` có giá trị mặc định là project ID cá nhân | Bỏ mặc định; bắt buộc `EE_PROJECT` trong `.env` |
| Đã sửa | Bằng chứng đo đạc nằm trong `data/interim` (gitignored) | Đã chép sang `reports/spark/` |
| Thấp | Split không có khoảng đệm (≤ 3 ngày), giống `lgbm.py` | Ghi ở phần hạn chế |
| Đã sửa | `peak_hour` lưu vực con không ổn định giữa các nền tảng | Làm tròn trước khi tìm giờ đỉnh |
| Đã sửa | Docstring `pixel_area_km2` ghi sai "< 0,1 %" | Thực đo +0,34 % |

---

## 11. Mưa vệ tinh IMERG / GSMaP 1998–2026 trên split chính (bổ sung 20/10)

> **Cập nhật:** kết luận cuối dựa trên walk-forward ở §12.1 — một lần chia dưới đây **đánh giá IMERG quá cao**.

Nguồn: Earth Engine (`src/ingest/gee_precip.py`), 10×10 ô 0,1° phủ **100 %** lưu vực
Kim Long (ERA5 chỉ 92,5 %). Đặc trưng giống hệt §4 (`hourly_features --source
imerg|gsmap|gsmap_gc`); IMERG nửa giờ được gộp về giờ kết thúc. Ranh giới ngày và
rò rỉ đã kiểm lại trên nguồn mới (chênh tổng ngày ≤ 3,4e-13 mm; đổi dữ liệu sau
23h ngày t không đổi đặc trưng ≤ t).

**So sánh nguồn mưa** — mùa lũ 9–12, 2015–2026, toàn lưu vực (`reports/rain_source_compare.csv`):

| Nguồn | Tổng / ERA5 | r ngày với ERA5 | r (mưa 3 ngày, Q t+1) Pearson / Spearman |
|---|---|---|---|
| ERA5 | 1,00 | — | **0,781 / 0,869** |
| IMERG V07 | 0,90 | 0,72 | 0,686 / 0,585 |
| GSMaP (vệ tinh) | 0,74 | 0,69 | 0,655 / 0,549 |
| GSMaP-GC (hiệu chỉnh trạm) | 1,14 | 0,78 | 0,686 / 0,790 |

ERA5 tương quan với lưu lượng cao nhất **vì GloFAS v4 chạy bằng chính ERA5** — không
có nghĩa ERA5 đúng hơn với sông thật. Các nguồn vệ tinh lệch nhau nhiều (r 0,67–0,88);
GSMaP gốc không ổn định (mùa lũ 2018 chỉ bằng 14 % ERA5).

**Ablation, split chính** (train ≤ 2015, valid → 06/2022, test ≥ 07/2022), LightGBM,
3 seed, ΔNSE test so với mốc của nhóm, CI 95 % bootstrap khối 30 ngày
(`src/models/ablation_sat.py`, `reports/ablation_hourly_sat.csv`):

| Nhóm / cấu hình | NSE h1 | h2 | h3 | Δ h2 [CI] | Δ h3 [CI] |
|---|---|---|---|---|---|
| A0 — panel Report 2 | 0,745 | 0,420 | 0,172 | | |
| A0 + IMERG giờ | 0,742 | **0,452** | 0,176 | **+0,032 [+0,013; +0,049]**, 3/3 seed dương | +0,004 |
| A0 + GSMaP-GC giờ | 0,734 | 0,427 | 0,195 | +0,007 (1 seed) | **+0,023 [+0,003; +0,050]**, 3/3 |
| A0 + GSMaP-GC lưu vực con | 0,724 | 0,440 | **0,200** | +0,020 | **+0,028 [+0,011; +0,051]**, 3/3 |
| E0 — cấu hình E, train từ 1998 | 0,752 | 0,469 | 0,205 | | |
| E0 + IMERG giờ | 0,751 | **0,488** | **0,222** | +0,018 [−0,001; +0,043], 3/3 | **+0,017 [+0,004; +0,034]** |
| E0 + GSMaP-GC giờ | 0,745 | 0,470 | 0,221 | +0,000 | +0,016 [−0,008; +0,056] |

**Kết luận** (thận trọng):

1. **h=1: mưa vệ tinh không giúp** — mọi Δ ≤ 0.
2. **h=2–3: tăng 0,02–0,03 NSE**, bằng chứng mạnh nhất là IMERG ở h2 (nhóm Report 2) và
   GSMaP-GC ở h3 — CI loại 0 và cả 3 seed cùng dương.
3. **Chưa chọn được nguồn tốt nhất**: thứ hạng IMERG / GSMaP-GC đảo giữa valid và test,
   và mức tăng cỡ bằng dao động khi chỉ đổi ngày bắt đầu train (E h2: 0,483 → 0,469).
   Cần walk-forward nhiều fold trước khi kết luận.
4. Cắt ngọn lũ không đổi (peak_bias h1 ≈ −0,45, h3 ≈ −0,88) — giới hạn vẫn là GloFAS.
5. **Khi dự báo thật**: chưa kiểm đoạn gần đây của IMERG V07 trên Earth Engine là bản
   Final (trễ ~3,5 tháng) hay Late. Nếu là Final thì vận hành phải dùng IMERG Early/Late
   hoặc GSMaP NRT, và nên chạy lại ablation với đúng sản phẩm đó.

Tái lập: `make hourly` (hoặc 5 lệnh cuối của target `hourly` trong Makefile).

---

## 12. Walk-forward 13 fold — kết luận cuối (20/10)

Fold theo năm, cửa sổ train mở rộng, test từng năm 2013 … 2025, gap 3 ngày giữa
train và test; ngưỡng mức 1 của mỗi fold tính chỉ từ train của fold đó; 3 seed.
Thống kê qua fold: ΔNSE trung bình [CI 95 % bootstrap theo fold], số fold thắng/thua,
Wilcoxon hai phía. Năm 2022 (GloFAS đổi chế độ) và 2026 (01–08) báo riêng.

### 12.1 Mưa vệ tinh (`src/eval/walk_forward_sat.py`, `reports/wf_sat_*.csv`)

| Cấu hình | ΔNSE h1 | ΔNSE h2 | ΔNSE h3 | CSI mức 1 h1 (gộp ~105 ngày) |
|---|---|---|---|---|
| E0 (cấu hình E, NSE TB 0,761 / 0,398 / 0,170) | — | — | — | 0,450 |
| **E0 + GSMaP-GC** (9 cột) | −0,001 · 8/5 | +0,017 [−0,002; +0,036] · 8/5 · p 0,22 | **+0,016 [+0,007; +0,024] · 11/2 · p 0,005** | **0,484** |
| E0 + IMERG | +0,001 · 8/5 | +0,010 [−0,002; +0,021] · p 0,09 | +0,008 [+0,001; +0,016] · p 0,08 | 0,446 |
| A0 (Report 2, NSE TB 0,744 / 0,336 / 0,121) | — | — | — | 0,423 |
| A0 + GSMaP-GC | +0,006 · 9/4 | **+0,032 [+0,023; +0,041] · 13/0** | **+0,025 [+0,013; +0,038] · 12/1** | 0,480 |
| A0 + IMERG | +0,012 · 11/2 | +0,019 · 12/1 | +0,012 · 9/4 | 0,452 |

1. **Mức tăng là thật nhưng nhỏ**, và nhỏ hơn hẳn trên mốc mạnh E0 so với A0 (vệ tinh
   bù phần R2 còn thiếu: độ ẩm đất, ngữ cảnh thời tiết, chuỗi train ngắn). Report 3
   báo theo mốc **E0**.
2. **Chọn GSMaP-GC toàn lưu vực (9 cột)** cho cấu hình chính: tăng đều ở h3 (11/13
   fold, CI loại 0), giảm báo động nhầm mức 1 (FA 24 → 19, CSI 0,450 → 0,484). Ở h2
   dương nhưng dao động lớn giữa năm — ghi là **chưa có ý nghĩa thống kê**.
3. **IMERG bị lần chia đơn đánh giá quá cao** (+0,018 / +0,017 → +0,010 / +0,008 qua
   fold, CI chạm 0) — chỉ nêu là phép thử phụ.
4. **Lưu vực con không đáng**: 45 cột ≈ 9 cột toàn lưu vực.
5. Giai đoạn GloFAS forecast archive (2023–2025) mới 3 fold — chưa kiểm định được
   (p hai phía nhỏ nhất có thể là 0,25).

### 12.3 Độ trễ khi chạy thật — mức tăng MẤT khi dùng qua Earth Engine (21/10)

Kiểm trực tiếp trên Earth Engine lúc 15:53 UTC ngày 20/10/2026:

| Bộ | Ảnh mới nhất (UTC) | Trễ | `status` |
|---|---|---|---|
| GSMaP v8 operational | 19/10 13:00 | **~27 giờ** | `provisional` 3 ngày gần nhất, trước đó `permanent`; cùng thuật toán 3GSMAPH5 / bản 05C |
| IMERG V07 | 19/10 01:30 | ~38 giờ | `permanent` (Final) tới 30/09/2025, sau đó `provisional` ⇒ chuỗi IMERG trộn Final + bản sớm |

Job dự báo chạy ~05h giờ VN ⇒ ngày t (hôm qua) chưa đủ giờ, chỉ có mưa vệ tinh tới
ngày t−1. Walk-forward lại nhóm EXT với đặc trưng GSMaP-GC **trễ 1 ngày**
(`python -m src.eval.walk_forward_sat --lag-test`, `reports/wf_sat_lag1.csv`):

| Cấu hình | ΔNSE h1 | ΔNSE h2 | ΔNSE h3 |
|---|---|---|---|
| E0 + GSMaP-GC (đủ ngày t) | +0,004 · 10/3 | +0,016 · 8/5 | +0,012 [+0,002; +0,023] · 10/3 · p 0,033 |
| E0 + GSMaP-GC **trễ 1 ngày** | +0,001 · 8/5 | −0,003 · 4/9 | −0,002 [−0,009; +0,004] · 6/7 · p 0,69 |

(Dòng đầu lệch nhẹ so với §12.1 vì thêm cột trễ làm đổi vài ngày bị loại do thiếu số.)

⇒ **Toàn bộ lợi ích nằm ở mưa của chính ngày t.** Qua Earth Engine thì chạy thật
không còn lợi gì. Report 3 phải ghi: mức tăng ở §12.1 là **phân tích lại quá khứ**;
muốn dùng khi vận hành cần nguồn trễ ít — GSMaP_NRT tải thẳng từ JAXA (công bố trễ
khoảng 4 giờ, cần đăng ký miễn phí; chưa kiểm có đúng cùng sản phẩm với bản trên Earth
Engine không) và dời job sang sau 07h.

### 12.2 Deep Learning (`src/eval/walk_forward_dl.py`, `reports/wf_dl_*.csv`)

Panel Report 2, so với LightGBM (NSE TB qua fold 0,743 / 0,334 / 0,118); DL: early
stopping trên 365 ngày cuối của train rồi học lại trên toàn bộ train; `--threads 2`.

| Mô hình | ΔNSE h1 | ΔNSE h2 | ΔNSE h3 | CSI mức 1 h1 (gộp 106 ngày) |
|---|---|---|---|---|
| LightGBM | — | — | — | 0,44 |
| LSTM L30, MSE | +0,021 [−0,014; +0,058] · 8/5 | −0,025 · 7/6 | −0,026 · 7/6 | **0,50** |
| LSTM L30, loss nhấn đỉnh | −0,007 | −0,107 · 5/8 | **−0,229 · p 0,033** | 0,50 |
| MLP lag, loss nhấn đỉnh | 0,000 | −0,065 | −0,118 | 0,49 |

1. **Không cấu hình DL nào hơn LightGBM một cách vững.** Ưu thế h2–h3 ở lần chia đơn
   chỉ có ở 2022–2025 — đúng giai đoạn test cũ; 2013–2021 DL thua.
2. Mặt được: ở h1 DL bắt sự kiện tốt hơn (POD 0,59–0,63 so với 0,51; CSI 0,49–0,50 so
   với 0,44) và ít cắt ngọn hơn (peak_bias h1 −0,21…−0,26 so với −0,38).
3. Số luồng torch ảnh hưởng **nhỏ** (LSTM trùng hệt ở 1/2/4 luồng, MLP lệch ≤ 0,028)
   — nhỏ hơn độ lệch giữa seed (sd 0,03–0,20 với DL, 0,01 với LightGBM).
4. ⇒ **Giữ LightGBM làm mô hình chính**; Report 4 trình bày walk-forward là so sánh
   chính, lần chia đơn chỉ là một trường hợp.

Tái lập:

    python -m src.eval.walk_forward_sat     # ~15–26 phút (882 lần fit)
    python -m src.eval.walk_forward_dl      # ~13 phút (6 tiến trình × 2 luồng)
    # --plot-only / --resume: dựng lại bảng + hình từ kết quả đã lưu
