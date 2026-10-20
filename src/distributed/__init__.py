"""Xử lý và huấn luyện phân tán bằng Apache Spark (Report 4).

* `spark_session` — tạo SparkSession cho chế độ local hoặc cụm standalone.
* `spark_etl`     — mưa ERA5 theo giờ → chỉ số mưa theo ngày cho từng ô / lưu vực con.
* `spark_train`   — GBT / RandomForest của Spark MLlib, đúng split thời gian của dự án.
* `spark_hourly`  — đặc trưng mưa giờ theo lưu vực con, trùng từng bit với `hourly_features`.
* `spark_dl`      — LSTM của `dl_lstm` huấn luyện DDP qua TorchDistributor / stage barrier.

Hạ tầng cụm nằm ở `infra/spark/` (docker-compose 1 master + 2 worker).
"""
