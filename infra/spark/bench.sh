#!/usr/bin/env bash
# Đo ETL mưa giờ → ngày với số worker / số lõi khác nhau, cùng phép tính bằng Polars.
# Chạy từ GỐC repo (Git Bash / WSL / Linux), cụm phải đang chạy:
#   docker compose -f infra/spark/docker-compose.yml up -d --build
#   bash infra/spark/bench.sh 2          # lặp 2 vòng
# Mỗi lần chạy nối một dòng vào data/interim/spark/etl_benchmark.csv
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash: không đổi /opt/... thành C:/Program Files/Git/opt/...

REPEAT=${1:-1}
M=dsp-spark-master
ETL=src/distributed/spark_etl.py
P=16                         # cùng số phân hoạch cho mọi cấu hình Spark
SUBMIT=(docker exec "$M" /opt/spark/bin/spark-submit)
CLUSTER=(--master spark://spark-master:7077)

for i in $(seq 1 "$REPEAT"); do
  echo "=== vòng $i/$REPEAT ==="
  # Cụm standalone: 1 worker 1 lõi → 1 worker 4 lõi → 2 worker × 4 lõi
  "${SUBMIT[@]}" "${CLUSTER[@]}" $ETL --mode cluster --cores-max 1 --executor-cores 1 --partitions $P --tag cluster_1w_1c
  "${SUBMIT[@]}" "${CLUSTER[@]}" $ETL --mode cluster --cores-max 4 --executor-cores 4 --partitions $P --tag cluster_1w_4c
  "${SUBMIT[@]}" "${CLUSTER[@]}" $ETL --mode cluster --cores-max 8 --executor-cores 4 --partitions $P --tag cluster_2w_8c
  # Một JVM trong container master: local[1] / local[4] / local[8]
  for c in 1 4 8; do
    "${SUBMIT[@]}" --master "local[$c]" --driver-memory 2g $ETL --mode local --cores $c --partitions $P --tag "docker_local$c"
  done
  # Cùng phép tính bằng Polars, cùng ổ mount → so I/O công bằng với Spark trong container
  docker exec "$M" python3 -m src.distributed.spark_etl --engine polars --tag docker_polars
done
