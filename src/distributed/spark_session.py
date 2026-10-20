"""Tạo SparkSession dùng chung cho mọi job phân tán.

Hai chế độ:

* ``local``   — một JVM, ``local[N]``. Dùng cho test và máy cá nhân.
* ``cluster`` — nối vào master standalone. Địa chỉ lấy từ biến môi trường
  ``SPARK_MASTER`` (mặc định ``spark://spark-master:7077``, đúng tên dịch vụ
  trong ``infra/spark/docker-compose.yml``).

Không truyền ``mode`` thì tự chọn: có ``SPARK_MASTER`` → cluster, không có → local.

⚠️ Windows: Spark 4.x (Hadoop 3.4) KHÔNG đọc/ghi được file cục bộ nếu thiếu
``winutils.exe`` + ``hadoop.dll`` — đo thật trên máy nhóm: ``spark.read.parquet``
ném ``UnsatisfiedLinkError: NativeIO$Windows.access0``. Dự án không tải binary
winutils từ repo cá nhân không rõ nguồn; thay vào đó ``hadoop_io_ok()`` trả
False trên Windows và job đi đường vòng qua Arrow: Polars đọc → ``createDataFrame``
→ Spark tính → ``toArrow`` → Polars ghi. Chạy trong container Linux thì đọc/ghi
thẳng bằng Spark như cụm thật.
"""

from __future__ import annotations

import os
import re
import sys

DEFAULT_CLUSTER_MASTER = "spark://spark-master:7077"


def hadoop_io_ok() -> bool:
    """Spark có tự đọc/ghi file qua Hadoop FS được không.

    Linux/macOS: có. Windows: không, trừ khi người dùng tự cài Hadoop native
    đúng chuẩn và đặt ``DSP_SPARK_HADOOP_IO=1``.
    """
    if os.environ.get("DSP_SPARK_HADOOP_IO") == "1":
        return True
    return os.name != "nt"


def resolve_master(mode: str | None = None, master: str | None = None,
                   cores: int | None = None) -> str:
    """Chọn địa chỉ master: tham số > biến môi trường > mặc định theo chế độ."""
    if master:
        return master
    env = os.environ.get("SPARK_MASTER")
    if mode is None:
        mode = "cluster" if env else "local"
    if mode == "local":
        return f"local[{cores}]" if cores else "local[*]"
    if mode == "cluster":
        return env or DEFAULT_CLUSTER_MASTER
    raise ValueError(f"mode phải là 'local' hoặc 'cluster', nhận {mode!r}")


def get_spark(mode: str | None = None, app_name: str = "dsp391m",
              master: str | None = None, cores: int | None = None,
              cores_max: int | None = None, executor_cores: int | None = None,
              executor_memory: str = "1500m", driver_memory: str = "2g",
              shuffle_partitions: int | None = None,
              extra_conf: dict[str, str] | None = None):
    """Tạo (hoặc lấy lại) SparkSession.

    * ``cores``          — số lõi cho ``local[N]`` (bỏ qua ở chế độ cluster).
    * ``cores_max``      — tổng lõi cả ứng dụng được xin từ cụm (``spark.cores.max``).
    * ``executor_cores`` — lõi mỗi executor; cùng ``cores_max`` quyết định số worker dùng.

    Múi giờ phiên đặt cố định UTC: cột ``time`` của dữ liệu là giờ VN *không kèm
    múi* (naive), để UTC thì Spark không tự dịch giờ khi đổi kiểu.
    """
    from pyspark.sql import SparkSession

    # Python của executor phải trùng Python của driver (Windows hay lệch conda/venv).
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

    url = resolve_master(mode, master, cores)
    is_local = url.startswith("local")
    if shuffle_partitions is None:
        shuffle_partitions = 8 if is_local else 16

    b = (SparkSession.builder.master(url).appName(app_name)
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.driver.memory", driver_memory)
         .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
         .config("spark.sql.execution.arrow.pyspark.enabled", "true")
         .config("spark.ui.showConsoleProgress", "false"))
    if not is_local:
        b = b.config("spark.executor.memory", executor_memory)
        if cores_max:
            b = b.config("spark.cores.max", str(cores_max))
        if executor_cores:
            b = b.config("spark.executor.cores", str(executor_cores))
    for k, v in (extra_conf or {}).items():
        b = b.config(k, v)

    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def describe(spark) -> dict[str, object]:
    """Thông tin cụm để ghi kèm kết quả đo.

    ``cores_used`` là số lõi được cấp (N của local[N], hoặc spark.cores.max).
    KHÔNG dùng defaultParallelism làm số lõi: ở standalone nó tối thiểu là 2
    kể cả khi chỉ xin 1 lõi.
    """
    sc = spark.sparkContext
    conf = sc.getConf()
    m = re.fullmatch(r"local\[(\d+|\*)\]", sc.master)
    if m:
        cores_used = os.cpu_count() if m.group(1) == "*" else int(m.group(1))
    elif sc.master == "local":
        cores_used = 1
    else:
        cores_used = int(conf.get("spark.cores.max", "0")) or None
    return {
        "master": sc.master,
        "cores_used": cores_used,
        "default_parallelism": sc.defaultParallelism,
        "cores_max": conf.get("spark.cores.max", ""),
        "executor_cores": conf.get("spark.executor.cores", ""),
        "spark_version": spark.version,
    }
