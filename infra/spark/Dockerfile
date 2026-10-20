# Image Spark chính thức + đúng bộ thư viện Python mà job của dự án cần.
# Phiên bản Spark PHẢI khớp pyspark cài trên máy (4.1.3) để chạy được cả hai chế độ.
FROM apache/spark:4.1.3-java21-python3

USER root
# numpy: bắt buộc cho pyspark.ml · pandas: src/eval/metrics.py import · polars/pyarrow: so sánh tốc độ
RUN pip3 install --no-cache-dir \
        numpy==2.1.3 pandas==2.2.3 pyarrow==18.1.0 polars==1.17.1
# torch CPU: cho src/distributed/spark_dl.py (LSTM phân tán qua TorchDistributor)
RUN pip3 install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
USER spark
ENV PYSPARK_PYTHON=python3 \
    PYTHONIOENCODING=utf-8 \
    PYTHONDONTWRITEBYTECODE=1
