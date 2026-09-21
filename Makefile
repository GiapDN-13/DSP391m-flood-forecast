# Makefile — mọi việc chạy đúng 1 lệnh, để ai cũng tái lập được (docs/GAPS.md mục 8)
# Windows: cài make bằng `winget install GnuWin32.Make`, hoặc đọc lệnh bên dưới rồi gõ tay.

.PHONY: help setup lint test crawl clean-data features train eval daily dashboard report all

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
