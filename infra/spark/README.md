# Spark phân tán — hạ tầng cho Report 4

Cụm **Spark standalone thật** chạy trên Docker Desktop: 1 master + 2 worker
(mỗi worker 4 lõi, 2 GB), image chính thức `apache/spark:4.1.3-java21-python3`
cộng numpy/pandas/pyarrow/polars (`Dockerfile`). Máy cài `pyspark==4.1.3` khớp
phiên bản cụm. Thư mục repo được mount vào `/opt/repo` ở cả 3 container — đóng
vai ổ dùng chung (HDFS/S3/NFS trong cụm thật) để executor ở worker nào cũng đọc
và ghi được cùng một đường dẫn.

| File | Việc |
|---|---|
| `docker-compose.yml` | cụm 1 master + 2 worker, UI master `http://localhost:8080` |
| `bench.sh` | đo ETL: 1 worker 1 lõi / 1 worker 4 lõi / 2 worker 8 lõi / local[1,4,8] / Polars |
| `src/distributed/spark_session.py` | `get_spark(mode='local'\|'cluster')`, đọc `SPARK_MASTER` |
| `src/distributed/spark_etl.py` | mưa ERA5 theo giờ → chỉ số mưa ngày theo ô (và theo lưu vực con nếu có bảng trọng số) |
| `src/distributed/spark_train.py` | GBT + RandomForest (MLlib), đúng split thời gian, so với LightGBM |
| `tests/test_distributed.py` | 10 test, Spark `local[1]` trên dữ liệu giả 2 ô × 3 ngày |

Dữ liệu sinh ra (không commit, `data/**` bị bỏ qua): `data/interim/spark/`
`rain_hourly_daily/` (bản Spark), `rain_hourly_daily_polars/` (bản Polars để đối chiếu),
`rain_subbasin_daily/`, `etl_benchmark.csv`, `train_grid.csv` — tổng vài MB.

## Vì sao chạy trong container chứ không chạy thẳng trên Windows

Spark 4.x dùng Hadoop 3.4 để đọc/ghi file. Trên Windows, thiếu `winutils.exe` +
`hadoop.dll` thì ngay cả **đọc** cũng hỏng — đo trên máy nhóm:
`spark.read.parquet(...)` → `UnsatisfiedLinkError: NativeIO$Windows.access0`.
Nhóm không tải binary winutils từ repo GitHub cá nhân không rõ nguồn. Vì vậy:

* **Chạy thật** (ETL, huấn luyện, đo tốc độ): trong container Linux — Spark tự đọc
  và ghi parquet như trên cụm thật.
* **Chạy trên Windows** (pytest, thử nhanh): `hadoop_io_ok()` trả False, dữ liệu
  đi đường vòng Polars → Arrow → Spark → `toArrow()` → Polars ghi. Phép tính vẫn do
  Spark làm, chỉ khâu đọc/ghi file đổi chỗ.

## Chạy (PowerShell, ở gốc repo)

```powershell
# 0. Docker Desktop phải đang chạy (docker info không báo lỗi)
docker compose -f infra/spark/docker-compose.yml up -d --build

# 1. ETL trên cụm 2 worker
docker exec dsp-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 `
    src/distributed/spark_etl.py --mode cluster --cores-max 8 --executor-cores 4 --tag cluster_2w_8c

# 2. Huấn luyện MLlib trên cụm → reports/spark_results.csv
docker exec dsp-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 `
    --driver-memory 2g src/distributed/spark_train.py --mode cluster --cores-max 8 --executor-cores 4 `
    --executor-memory 1800m --models rf,gbt

# 3. Đo tốc độ (Git Bash): bash infra/spark/bench.sh 2
# 4. Test nhỏ trên Windows (local[1], dữ liệu giả, không cần Docker)
$env:PYTHONIOENCODING="utf-8"; python -m pytest tests/test_distributed.py -q
# 5. Tắt cụm (giải phóng ~4 GB RAM của Docker)
docker compose -f infra/spark/docker-compose.yml down
```

Git Bash: đặt `MSYS_NO_PATHCONV=1` trước `docker exec`, không thì `/opt/spark/...`
bị đổi thành `C:/Program Files/Git/opt/spark/...`.

## Kết quả đo — ETL mưa giờ → ngày (20/10/2026)

Đầu vào: 768 file, **6 544 896 dòng** (64 ô × 2015-01-01…2026-08-31 theo giờ).
Đầu ra: **272 704 dòng** (64 ô × 4 261 ngày), 12 thư mục `year=`; mọi ngày đủ 24 giờ.
Kết quả Spark và Polars **trùng khớp**: 272 704/272 704 dòng ghép được, sai khác
lớn nhất 0 ở mọi cột mưa/đếm; riêng `t2m_mean` lệch 0,001 °C do hai bên làm tròn
nửa khác nhau. Gộp 5 lưu vực con theo `data/external/basins/weights_era5_0p1.csv`
(34 ô) → 21 305 dòng.

Sửa 20/10/2026 (kiểm chứng): bản đầu cho `peak_hour` lưu vực con lệch giữa Windows và
cụm ở 79/21 305 dòng — mưa lưu vực con là trung bình có trọng số, lệch ~1e-17 tuỳ thứ
tự cộng nên hai giờ "hoà" bị coi là khác nhau. Nay làm tròn mưa tới 0,001 mm trước khi
tìm giờ đỉnh (hoà → giờ sớm nhất): Windows `local[8]` và cụm 2 worker trùng 21 305/21 305
dòng ở mọi cột; `rain_subbasin_daily/` đã ghi lại bằng bản sửa (chạy trên cụm).

`seconds_etl` = đọc + tính + ghi (không gồm khởi động JVM). Mỗi cấu hình 2 lần,
số liệu gốc ở `data/interim/spark/etl_benchmark.csv`, lệnh ở `bench.sh`.

| Cấu hình | Lõi | Executor | ETL ô (s), min–max | Gộp lưu vực (s) |
|---|---|---|---|---|
| Cụm: 1 worker × 1 lõi | 1 | 1 | 94,7 – 100,8 | 54,0 |
| Cụm: 1 worker × 4 lõi | 4 | 1 | 38,2 – 38,3 | 17,6 |
| Cụm: **2 worker** × 4 lõi | 8 | 2 | 40,5 – 41,2 | 16,1 |
| Container, `local[1]` | 1 | — | 87,9 – 99,4 | 52,6 |
| Container, `local[4]` | 4 | — | 33,4 – 34,7 | 14,9 |
| Container, `local[8]` | 8 | — | 32,6 – 32,9 | 13,0 |
| Container, **Polars** | 16 luồng | — | 8,7 – 10,1 | — |
| Windows, Spark `local[8]` + Arrow | 8 | — | 60,0 (1 lần) | 22,7 |
| Windows, **Polars** | 16 luồng | — | 3,4 – 3,7 | — |

Đọc bảng cho trung thực:

1. **Song song có tác dụng**: 1 → 4 lõi nhanh 2,6–2,8 lần (cụm 97,7 → 38,2 s;
   `local` 93,7 → 34,0 s, trung bình 2 lần chạy). Ở cấu hình 2 worker, master cấp
   thật 2 executor trên 2 container worker khác nhau (`n_executors = 2`).
2. **4 → 8 lõi / 1 → 2 worker gần như không nhanh thêm.** Hai nguyên nhân, đều đo được
   (script chẩn đoán chạy trên cụm): (a) chỉ riêng việc đọc 768 file qua ổ mount
   Windows→Docker đã mất 56–63 s với 1 lõi và 14–21 s với 8 lõi, tức khoảng
   35–65 % thời gian ETL tương ứng;
   (b) chỉ có 64 khoá (ô) băm vào 16 phân hoạch → phân hoạch lớn nhất 920 376 dòng,
   gấp 2,1 lần trung bình 436 326, task chậm nhất quyết định thời gian cả stage.
3. **Ở cỡ dữ liệu này Polars một máy nhanh hơn Spark.** Cùng container, cùng ổ
   mount: Polars 8,7–10,1 s so với Spark tốt nhất 32,6 s (~3,5 lần). Polars chạy
   thẳng trên ổ Windows: 3,4–3,7 s (~10 lần). 74 MB vừa thừa RAM một máy; Spark trả
   thêm chi phí lập lịch task và xáo dữ liệu giữa các executor. Spark chỉ đáng dùng
   khi dữ liệu vượt RAM một máy hoặc nằm sẵn trên kho phân tán — đúng hướng mở rộng của dự án (PERSIANN-CCS 0,04° phủ `FINE_BBOX`
   1°×1° là 25×25 = 625 ô, gấp ~10 lần 64 ô hiện tại — phép tính số học, chưa đo).
4. Trên Windows, đường vòng Arrow chậm gần gấp đôi chạy trong container (60 s so với
   33 s). Lý giải (chưa đo tách riêng): toàn bộ 6,5 triệu dòng phải đi qua driver
   (Polars đọc → `createDataFrame`) thay vì để executor tự đọc file.

Máy đo: Windows 11, 16 lõi, 16 GB RAM; Docker Desktop cấp 7,4 GB. Các agent khác
chạy song song trên cùng máy nên số giây có nhiễu vài phần trăm.

## Kết quả huấn luyện MLlib trên cụm (20/10/2026)

`spark_train.py` trên cụm 2 worker × 4 lõi (executor 1 800 MB), 66 feature của
`daily_panel.parquet`, học `log1p(Q)`. Chọn tham số bằng vòng lặp tự viết: fit trên
train (2010–2015, 2 177 ngày), chấm NSE trên valid cố định (2016 → 06/2022, 2 373 ngày),
fit lại trên train+valid (4 550 ngày), chấm test (từ 07/2022, 1 520–1 522 ngày) một lần.
Không dùng `CrossValidator`/`TrainValidationSplit` vì cả hai tách ngẫu nhiên.
Lưới: GBT 8 bộ, RF 4 bộ; tổng 1 706 s cho 3 horizon × 2 mô hình.

| Horizon | Spark GBT | Spark RF | LightGBM (`lgbm_results.csv`) |
|---|---|---|---|
| h=1 | 0,699 | 0,687 | **0,747** |
| h=2 | 0,429 | **0,454** | 0,420 |
| h=3 | 0,182 | **0,214** | 0,175 |

NSE trên tập test; chi tiết (RMSE, KGE, peak_bias, tham số chọn, thời gian) ở
`reports/spark_results.csv`, cả lưới ở `data/interim/spark/train_grid.csv`.

Đọc cho đúng:

* h=1 LightGBM vẫn tốt nhất. h=2/h=3 RF nhỉnh hơn 0,03–0,04 NSE, GBT nhỉnh ≤ 0,01 —
  một lần chia test duy nhất, chưa kiểm định, **không đủ để nói Spark tốt hơn**.
  Lưu ý thêm: LightGBM dùng tham số cố định, còn mô hình Spark được chọn trên valid.
* Cả ba mô hình đều cắt ngọn đỉnh lũ gần như nhau (peak_bias: Spark −0,50 → −0,87,
  LightGBM −0,45 → −0,89 từ h=1 đến h=3): đổi công cụ không chữa được giới hạn của
  feature ngày.
* GBT chọn đúng bộ nhỏ nhất lưới ở cả 3 horizon (sâu 3, bước 0,05) → nếu tinh chỉnh
  tiếp thì mở rộng lưới về phía mô hình đơn giản hơn.
* Lần chạy đầu (executor 1 500 MB) cả hai executor chết vì hết bộ nhớ (exit code 52)
  khi đang fit RF. Nhiều khả năng do MLlib mặc định cho mỗi task 256 MB thống kê nút
  (`maxMemoryInMB`), 4 task/executor = 1 GB, vượt vùng nhớ thực thi của executor
  (block manager báo 720 MiB). Đặt `maxMemoryInMB=64` + executor 1 800 MB thì chạy
  hết, kết quả trên là của lần chạy này.

## Cách chạy — đặc trưng mưa giờ + LSTM phân tán (Report 4)

Hai file mới: `src/distributed/spark_hourly.py` (bản Spark của
`src/features/hourly_features.py`, cùng 54 cột `hr_*`) và `src/distributed/spark_dl.py`
(LSTM của `src/models/dl_lstm.py` huấn luyện DDP qua Spark). Image cụm **chưa có torch**
nên bước 1 cài torch CPU vào cả 3 container (mất khi `down`; muốn cố định thì thêm vào
`Dockerfile`).

**Có Docker** (PowerShell, gốc repo; Git Bash thì đặt `MSYS_NO_PATHCONV=1` trước `docker exec`):

```powershell
# 1. Cụm 1 master + 2 worker, cài torch CPU vào cả 3 container
docker compose -f infra/spark/docker-compose.yml up -d
foreach ($c in "dsp-spark-master","dsp-spark-worker-1","dsp-spark-worker-2") { docker exec -u root $c pip3 install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu }
# 2. Đặc trưng giờ theo lưu vực con trên 2 worker + so từng cột với bản Polars
docker exec dsp-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 src/distributed/spark_hourly.py --mode cluster --cores-max 8 --executor-cores 4 --source era5 --compare
# 3. LSTM: mốc 1 tiến trình, rồi TorchDistributor 2 rank trên 2 worker → reports/spark_dl_results.csv
docker exec dsp-spark-master python3 -m src.distributed.spark_dl --engine single --threads 4 --tag docker_single_1x4
docker exec dsp-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 src/distributed/spark_dl.py --engine distributor --mode cluster --procs 2 --threads 4 --cores-max 8 --executor-cores 4 --tag docker_td_cluster_2x4
# 4. Tắt cụm
docker compose -f infra/spark/docker-compose.yml down
```

**Không có Docker** (Windows, Spark `local`):

```powershell
$env:PYTHONIOENCODING="utf-8"
python -m src.distributed.spark_hourly --source era5 --mode local --cores 8 --compare   # --source pccs cho PERSIANN-CCS
python -m src.distributed.spark_dl --engine single --threads 4 --tag win_single_1x4
python -m src.distributed.spark_dl --engine barrier --procs 2 --threads 2 --tag win_barrier_2x2
python -m pytest tests/test_spark_parity.py tests/test_distributed.py -q
```

Đầu ra: `data/interim/spark/hourly_features_{era5,pccs}.parquet`,
`data/interim/spark/hourly_parity_{nguồn}_{máy}.csv` (so từng cột, kèm số giây),
`reports/spark_dl_results.csv` (mỗi lần chạy 9 dòng = fit × split × horizon; chạy lại
cùng `--tag` thì thay dòng cũ; lần chạy hỏng cũng được ghi, cột `status`/`error`).

### Spark và Polars cho ra cùng đặc trưng giờ (20/10/2026)

So từng ô với `hourly_features.py` trên CÙNG máy: **0 ô lệch, kể cả so tới từng bit**
(`==`), 0 ô rỗng lệch nhau, không dòng nào chỉ có ở một bên.

| Nguồn | Chạy ở đâu | Dòng giờ × ô | Ô so (giờ / ngày) | Lệch lớn nhất | Spark (s) | Polars (s) |
|---|---|---|---|---|---|---|
| ERA5 2015-01 → 2026-08 | Windows `local[8]` (Arrow) | 2 147 544 | 613 584 / 230 064 | 0 | 42,3 | 1,3 |
| ERA5 | cụm 2 worker × 4 lõi | 2 147 544 | 613 584 / 230 064 | 0 | 33,2; 28,7 | 4,1; 3,9 |
| PERSIANN-CCS 10–11/2020 | Windows `local[8]` | 915 000 | 8 784 / 3 234 | 0 | 35,7 | 0,2 |
| PERSIANN-CCS | cụm 2 worker × 4 lõi | 915 000 | 8 784 / 3 234 | 0 | 14,0 | 0,2 |

Cần ba việc để trùng từng bit, vì lệch 1e-16 đã đủ lật ngưỡng (vd. trong dữ liệu giả của
`tests/test_spark_parity.py`, ngày mưa phùn mọi ô 0,1 mm cho trung bình toàn lưu vực
0,10000000000000002, sát ngưỡng đỉnh 0,1 mm):
cộng tuần tự theo đúng thứ tự Polars (`aggregate` trên mảng đã sắp, thay `F.sum`);
cộng 5 lưu vực con theo đúng cây của `pl.sum_horizontal` ((0+1)+(2+(3+4)));
sin/cos giờ đỉnh lấy từ bảng tính bằng Polars thay vì `F.sin` của JVM. Giữa Windows và
Linux, `hr_peak_sin_*` lệch ≤ 1,1e-16 (1 ulp) do `sin` của thư viện C khác nhau. Lệch
này có ở cả Polars lẫn Spark, không phải do Spark.

Ở cỡ dữ liệu này Spark chậm hơn Polars: ERA5 7–33 lần (cụm 28,7–33,2 s so với 3,9–4,1 s;
Windows 42,3 s so với 1,3 s). PERSIANN-CCS chỉ có 2 tháng nên Polars xong trong 0,2 s,
còn Spark vẫn mất 14–36 s chi phí cố định (lập lịch, xáo dữ liệu). Kết luận giống phần
ETL ở trên.

### Toàn bộ lưu trữ vệ tinh trên cụm (Report 4, 02/11/2026)

Trước đây Spark chỉ chạy lát ERA5 (2015 → 08/2026). Nay `spark_hourly.py --source`
nhận thêm `imerg`, `gsmap`, `gsmap_gc`, `gsmap_nrt` (khoá của `hourly_features.GEE`) và
chạy trên **toàn bộ** lưu trữ 0,1° từ 01/1998: cùng danh sách file tháng (+ `_parts/` ngày
lẻ của JAXA) với `hf.load_gee`, chỉ giữ 24 ô có trong `weights_gee_0p1.csv`, rồi
`to_hourly_spark` gộp nửa giờ IMERG về giờ đúng như `hf.to_hourly` (giờ HH:00 = nửa giờ
kết thúc HH−1:30 + HH:00, mỗi nửa = cường độ × 0,5; thiếu một nửa → giờ rỗng). Hai nửa
cộng nhau không phụ thuộc thứ tự (a + b = b + a), nên ở bước này `F.sum` vẫn trùng từng bit.

```powershell
# Git Bash: export MSYS_NO_PATHCONV=1 trước
docker exec dsp-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 src/distributed/spark_hourly.py --mode cluster --cores-max 8 --executor-cores 4 --source imerg --compare --bench --tag cluster_2w_8c
#   1 worker: --cores-max 4 · local trong container: --master "local[8]" --driver-memory 4g ... --mode local --cores 8
docker exec dsp-spark-master python3 -m src.distributed.spark_hourly --source imerg --polars-only --bench --tag docker_polars
python -m src.distributed.spark_hourly --source imerg --mode local --cores 8 --driver-memory 6g --compare --bench --tag win_local8_arrow
```

Số liệu gốc: `reports/spark/full_scale_bench.csv` (mỗi lần chạy 1 dòng) và
`reports/spark/full_scale_parity.csv` (tóm tắt so khớp giờ/ngày); chi tiết từng cột ở
`data/interim/spark/hourly_parity_<nguồn>_<máy>.csv`.

| Nguồn | File | MB | Dòng trong file | Ô×giờ (24 ô) | Đầu ra |
|---|---|---|---|---|---|
| IMERG (30 phút) | 346 | 47,7 | 50 477 000 | 6 057 744 | 252 456 giờ, 10 519 ngày × 54 cột |
| GSMaP-GC (Earth Engine) | 346 | 50,8 | 25 241 800 | 6 058 032 | 252 456 giờ, 10 519 ngày × 54 cột |
| GSMaP NRT (JAXA, + 19 file `_parts`) | 364 | 26,3 | 25 245 600 | 6 058 944 | 252 480 giờ, 10 520 ngày × 54 cột |

**Spark = Polars tới từng bit ở cả 3 nguồn, toàn bộ thời kỳ:** 0 giá trị lệch, 0 ô rỗng
lệch nhau, không ngày/giờ nào chỉ có ở một bên. Mỗi nguồn so khoảng 1,51 triệu giá trị giờ
(6 đơn vị × ~252 000 giờ) và 0,57 triệu giá trị ngày (54 cột × 10 519 ngày). Kết quả này
đúng cả trên cụm 2 worker (Linux) lẫn Windows `local[8]`. Trước đó đã thử từng năm
(IMERG/GSMaP-GC 2020, NRT 2026) trên Windows và cũng ra 0 lệch. Không phải sửa thêm gì
ngoài ba cách đã dùng cho ERA5.

Thời gian = đọc + tính + gom kết quả về driver, không gồm khởi động JVM (3–15 s). Đơn vị là
giây, min–trung vị–max của 2–3 lần chạy:

| Cấu hình | IMERG | GSMaP-GC | GSMaP NRT |
|---|---|---|---|
| Cụm **2 worker** × 4 lõi | 37,8 – 42,6 – 67,9 | 30,5 – 31,6 – 62,3 | 29,4 – 30,9 – 71,0 |
| Cụm 1 worker × 4 lõi | 39,1 – 40,3 – 65,5 | 29,8 – 31,3 – 51,1 | 29,2 – 29,4 – 31,4 |
| Container `local[8]`, driver 4 GB | 29,7; 29,9 | 23,5; 24,7 | 23,2; 23,3 |
| Container, **Polars** (`hf.build_source`) | 12,4; 20,3 | 4,8; 5,4 | 4,7; 4,7 |
| Windows `local[8]` + Arrow (kèm `--compare`) | 114,5 | 64,3 | 65,0 |
| Windows, **Polars** | 8,3; 12,5 | 2,2; 2,5 | 2,3; 2,3 |

Số max của cụm là lần chạy đầu: chạy kèm `--compare`, và file đọc qua ổ mount
Windows→Docker lần đầu chưa có trong cache. Các lần sau ổn định ở mức trung vị.

Kết luận:

1. **Đã chạy được toàn bộ dữ liệu vệ tinh trên cụm.** Tổng 101 triệu dòng đầu vào
   (125 MB parquet), 28,8 năm × 3 nguồn. Executor giữ mặc định 1 500 MB, worker 2 GB,
   không hết bộ nhớ, **không phải tăng bộ nhớ worker** trong `docker-compose.yml`.
2. **Có một lần hết bộ nhớ, ở chế độ local chứ không phải trên cụm:** IMERG chạy
   `local[8]` trong container bị `OutOfMemoryError: Java heap space` (dòng `status=failed`
   trong CSV). Nguyên nhân: chạy qua `spark-submit` thì JVM driver đã khởi động trước khi
   `get_spark` đặt `spark.driver.memory=2g`, nên heap vẫn là 1 GB mặc định. Ở `local[*]`,
   cả 8 task chạy chung heap này. Truyền `spark-submit --driver-memory 4g` thì chạy ổn
   (6/6 lần). Chạy bằng `python -m` thì `--driver-memory` của script có tác dụng.
3. **2 worker vẫn không nhanh hơn 1 worker, và Polars vẫn nhanh hơn Spark 2–6 lần**
   (container: IMERG 12–20 s so với 30–42 s; GSMaP 5 s so với 23–31 s). 101 triệu dòng
   nghe thì lớn, nhưng parquet nén chỉ 125 MB. Sau khi lọc 24 ô và gộp giờ, mỗi nguồn còn
   ~6 triệu dòng, rồi chỉ ~252 000 giờ × 6 đơn vị, vẫn vừa RAM một máy. Ngoài ra, phần
   cửa sổ (lag 3/6 giờ, r72h) phân hoạch theo đơn vị nên chỉ có 6 nhóm song song. IMERG
   là nguồn duy nhất mà Spark thu hẹp khoảng cách (gấp ~2 lần thay vì ~5 lần), vì bước gộp
   nửa giờ → giờ (50 triệu → 6 triệu dòng) chia đều được cho các task.
4. Trên Windows, đường vòng Arrow chậm gấp 2–4 lần chạy trong container: toàn bộ ~12 triệu
   dòng nửa giờ IMERG phải đi qua driver, cần `--driver-memory 6g`.

Image cụm giờ có thêm `scikit-learn==1.6.0 lightgbm==4.5.0 scipy==1.14.1` (cho
`spark_walkforward.py`). Đã kiểm `import lightgbm, sklearn` chạy được ở cả 3 container.
Test: `tests/test_spark_satellite.py` dùng IMERG giả bước 30 phút + 1 tháng IMERG thật
(10/2020, nếu máy có file). Kết quả: 5 passed trên Windows, 6 passed trong container (ở container
có thêm biến thể Spark tự đọc parquet).

### LSTM phân tán (seed 42, `lstm_L30_mse`, 20/10/2026)

| Cách chạy | Ở đâu | Tiến trình × luồng | Batch toàn cục | Epoch* | `train()` (s) | Wall (s) | NSE test h1/h2/h3 |
|---|---|---|---|---|---|---|---|
| 1 tiến trình | Windows | 1 × 4 | 64 | 10 | 16,1; 18,2 | 16,1; 18,2 | 0,709 / 0,432 / 0,180 |
| Spark barrier `local[2]` | Windows | 2 × 2 | 128 | 13 | 17,6; 17,7 | 26,3; 26,8 | 0,712 / 0,413 / 0,160 |
| Spark barrier `local[2]` | Windows | 2 × 2 | 64 | 8 | 17,8 | 26,6 | 0,704 / 0,413 / 0,165 |
| TorchDistributor `local_mode` | Windows | 2 × 2 | — | — | — | — | **không chạy được** |
| 1 tiến trình | container | 1 × 4 | 64 | 10 | 9,49; 9,04 | 9,49; 9,04 | 0,709 / 0,432 / 0,180 |
| TorchDistributor `local_mode` | container | 2 × 2 | 128 | 13 | 9,94; 10,07 | 16,3; 16,4 | 0,712 / 0,413 / 0,160 |
| **TorchDistributor, 2 worker** | cụm | 2 × 4 | 128 | 13 | 10,05; 9,92 | 23,2; 22,6 | 0,712 / 0,413 / 0,160 |
| TorchDistributor, 2 worker | cụm | 2 × 4 | 64 | 8 | 10,35 | 23,5 | 0,704 / 0,413 / 0,165 |
| Spark barrier, 2 worker | cụm | 2 × 4 | 128 | 13 | 10,40; 9,92 | 15,5; 15,0 | 0,712 / 0,413 / 0,160 |

NSE test học trên train+valid. `train()` = thời gian của rank 0 (đọc panel + 2 lượt học
+ đánh giá); Wall = từ lúc gọi tới lúc nhận kết quả, chưa gồm khởi động SparkSession.
Hai số cách nhau dấu `;` là 2 lần chạy.

* **Bản 1 tiến trình tái lập đúng** số của `reports/dl_results.csv` (seed 42: 0,709 /
  0,432 / 0,180), trên cả Windows lẫn container.
* **Phân tán không làm mô hình tốt hơn hay tệ hơn rõ rệt.** So với 1 tiến trình, NSE
  test lệch +0,003 / −0,019 / −0,020 (batch toàn cục 128) và −0,005 / −0,019 / −0,015
  (batch 64). So với độ lệch chuẩn giữa 3 seed của `dl_results.csv` (0,016 / 0,018 /
  0,021): ở h1 và h3 nhỏ hơn 1 sd, ở h2 xấp xỉ 1 sd (0,019 so với 0,018). Đây chỉ là 1
  seed nên chưa kết luận được gì thêm. DDP chia mẫu cho 2 rank nên đường học khác bản
  1 tiến trình.
* **Kết quả không phụ thuộc cách phân tán.** Cùng số rank và batch thì barrier tự viết,
  TorchDistributor `local_mode` và TorchDistributor 2 worker cho cùng NSE tới 4 chữ số.
  Trên cụm, barrier và TorchDistributor trùng từng bit; Windows (torch 2.13) và
  container (torch 2.14.1) lệch ≤ 3e-5 ở mọi chỉ số.
* **Phân tán CHẬM hơn.** Dữ liệu chỉ ~2 200 cửa sổ × 30 ngày × 9 biến, mỗi epoch vài
  chục batch nên đồng bộ gradient mỗi batch (gloo) ăn hết phần lợi chia việc. Riêng
  `train()` đã ngang hoặc chậm hơn 1 tiến trình (cụm: 9,9–10,4 s so với 9,0–9,5 s);
  TorchDistributor tốn thêm ~13 s dựng stage barrier + torchrun. Phân tán chỉ có ích
  khi mô hình hoặc dữ liệu lớn hơn nhiều (vd. LSTM giờ 168 bước × 64 ô).

**TorchDistributor trên Windows hỏng — đã thử, không vá được từ phía dự án:** torchrun
dựng TCPStore cho rendezvous (`--standalone` → c10d) với libuv mặc định, bản torch
Windows không có libuv: `torch.distributed.DistStoreError: use_libuv was requested but
PyTorch was built without libuv support`. Đặt `USE_LIBUV=0` cũng vẫn lỗi y như vậy (đã thử;
biến này chỉ tới được `init_process_group`). Vì vậy trên Windows dùng `--engine barrier`:
cùng cơ chế stage barrier như TorchDistributor nhưng mỗi task gọi `train()` trực tiếp,
không qua torchrun.

### Phần nào thật sự phân tán

| Việc | Phân tán thật (nhiều worker/tiến trình) | Chỉ local |
|---|---|---|
| `spark_hourly` trên cụm | ✔ 2 executor trên 2 container worker (8 lõi); executor tự đọc parquet | |
| `spark_hourly` trên Windows | | `local[8]`: 1 JVM nhiều luồng; dữ liệu đi qua driver (Arrow) |
| `spark_dl` TorchDistributor / barrier trên cụm | ✔ 2 rank DDP trên 2 worker (`spark.task.cpus=4` ⇒ 1 task/executor, gloo qua mạng Docker) | |
| `spark_dl` TorchDistributor `local_mode` (container), barrier `local[2]` (Windows) | 2 tiến trình DDP trên **một** máy | không đa máy |
| `spark_dl --engine single`, test pytest | | 1 tiến trình / `local[2]` |

Cả 3 container chạy chung một máy vật lý (16 lõi, Docker Desktop 7,4 GB), nên "2 worker"
là phân tán thật về giao thức (executor, barrier, gloo qua mạng) nhưng KHÔNG thêm phần cứng.
