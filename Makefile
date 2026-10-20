# Makefile — mọi việc chạy đúng 1 lệnh, để ai cũng tái lập được (docs/GAPS.md mục 8)
# Windows: cài make bằng `winget install GnuWin32.Make`, hoặc đọc lệnh bên dưới rồi gõ tay.

.PHONY: help setup lint test crawl clean-data features train eval daily dashboard report all \n        sat basins hourly dl spark-up spark-etl spark-train spark-dl spark-down

help:
	@echo "setup      - tao venv va cai dependency"
	@echo "lint       - ruff check"
	@echo "test       - pytest"
	@echo "crawl      - crawl du lieu tho tu Open-Meteo (chay lau, co resume)"
	@echo "clean-data - ETL: lam sach + chuan hoa -> data/interim"
	@echo "features   - tao bang phan tich -> data/processed/daily_panel.parquet"
	@echo "train      - train mo hinh chinh"
	@echo "eval       - walk-forward validation + xuat bang metric"
	@echo "daily      - chay pipeline du bao 1 ngay"
	@echo "dashboard  - mo Streamlit"
	@echo "all        - crawl -> clean-data -> features -> train -> eval"
	@echo "sat        - mua ve tinh IMERG/GSMaP 1998-nay qua Earth Engine (can EE_PROJECT trong .env)"
	@echo "basins     - DEM 30 m -> luu vuc con -> trong so o luoi"
	@echo "hourly     - dac trung mua theo gio + ablation"
	@echo "dl         - LSTM/MLP so voi LightGBM (giu --threads 2 de tai lap)"
	@echo "spark-*    - cum Spark Docker: spark-up, spark-etl, spark-train, spark-dl, spark-down"

setup:
	python -m venv .venv
	.venv/Scripts/python -m pip install -U pip
	.venv/Scripts/pip install -r requirements.txt
	.venv/Scripts/nbstripout --install

lint:
	ruff check --no-cache src tests scripts

test:
	pytest -q tests

crawl:
	python -m src.ingest.crawl_all

clean-data:
	python -m src.etl.clean

features:
	python -m src.features.build_panel

train:
	python -m src.models.train

eval:
	python -m src.eval.walk_forward

daily:
	python -m src.models.predict_daily

dashboard:
	streamlit run dashboard/app.py

all: crawl clean-data features train eval

# ---------- Report 3-4: mua min hon, theo gio, Spark, Deep Learning ----------
SPARK = docker exec dsp-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077

sat:
	python -m src.ingest.gee_precip --dataset imerg
	python -m src.ingest.gee_precip --dataset gsmap

basins:
	python -m src.features.basins

hourly:
	python -m src.features.hourly_features --source era5
	python -m src.models.ablation_hourly
	python -m src.features.hourly_features --source imerg
	python -m src.features.hourly_features --source gsmap
	python -m src.features.hourly_features --source gsmap_gc
	python -m src.eval.rain_source_compare
	python -m src.models.ablation_sat

dl:
	python -m src.models.dl_lstm --jobs 8 --threads 2

spark-up:
	docker compose -f infra/spark/docker-compose.yml up -d --build

spark-etl:
	$(SPARK) src/distributed/spark_etl.py --mode cluster --cores-max 8 --executor-cores 4 --partitions 16

spark-train:
	$(SPARK) --driver-memory 2g src/distributed/spark_train.py --mode cluster --cores-max 8 --executor-cores 4 --executor-memory 1800m --models rf,gbt

spark-dl:
	$(SPARK) src/distributed/spark_dl.py --engine distributor --mode cluster --procs 2 --threads 4 --cores-max 8 --executor-cores 4 --tag docker_td_cluster_2x4

spark-down:
	docker compose -f infra/spark/docker-compose.yml down
