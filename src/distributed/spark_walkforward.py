"""Walk-forward LightGBM phân tán theo TÁC VỤ trên Spark (Report 4).

Đơn vị song song là một *lượt* cấu hình × năm test × seed của
``src/eval/wf_peak.py`` (``run_job``: học 3 horizon, trả dự báo ngoài mẫu). Các lượt
độc lập nhau ⇒ ``sc.parallelize(jobs, len(jobs)).map(run_job)``: mỗi lượt là một
task Spark, executor nào rảnh thì nhận — đây là kiểu song song có lợi thật ở quy mô
dự án (ETL 75–100 MB thì Polars một máy nhanh hơn, xem ``infra/spark/README.md``).

Kiểm đúng: dự báo từ Spark so với dự báo của tiến trình local (``wf_peak --stage
run``, cùng seed, LightGBM 1 luồng) — phải trùng (|Δ| tối đa ghi vào CSV). Đo: thời
gian wall của Spark so với tổng thời gian các lượt khi chạy nối tiếp và với pool local.

    # trong container (xem infra/spark/README.md), cụm 2 worker × 4 lõi:
    spark-submit --master spark://spark-master:7077 src/distributed/spark_walkforward.py \\
        --mode cluster --cores-max 8 --executor-cores 4 --tag cluster_2w_8c
    # trên máy (local[N]):
    python -m src.distributed.spark_walkforward --mode local --cores 6 --tag local_6
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl

from src import config as cfg
from src.distributed.spark_session import describe, get_spark
from src.eval import wf_peak

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_BENCH = cfg.ROOT / "reports" / "spark" / "wf_bench.csv"
WORK = cfg.CACHE / "wf_peak_spark"


def run_spark(spark, jobs: list[dict]) -> tuple[list[dict], float]:
    """Mỗi lượt một phân hoạch ⇒ một task; gom kết quả về driver (vài MB)."""
    sc = spark.sparkContext
    t0 = time.perf_counter()
    res = sc.parallelize(jobs, len(jobs)).map(wf_peak.run_job).collect()
    return res, time.perf_counter() - t0


def parity(res: list[dict], ref_dir: Path) -> dict:
    """So dự báo Spark với dự báo local cùng lượt (nếu đã có)."""
    n_jobs = n_vals = 0
    worst = 0.0
    for r in res:
        f = wf_peak.job_path(r, ref_dir)
        if not f.exists():
            continue
        a = wf_peak.to_frame(r).sort("horizon", "date")
        b = pl.read_parquet(f).sort("horizon", "date")
        if a.height != b.height or not a["date"].equals(b["date"]):
            raise AssertionError(f"Lệch tập ngày ở lượt {f.name}")
        worst = max(worst, float(np.max(np.abs(a["yhat"].to_numpy() - b["yhat"].to_numpy()))))
        n_jobs += 1
        n_vals += a.height
    return {"parity_jobs": n_jobs, "parity_values": n_vals, "parity_max_abs_diff": worst}


def append_bench(row: dict, path: Path = OUT_BENCH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = pl.DataFrame([row])
    if path.exists():
        new = pl.concat([pl.read_csv(path), new], how="diagonal_relaxed")
    new.write_csv(path, float_precision=4)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=["local", "cluster"], default=None)
    ap.add_argument("--cores", type=int, default=None, help="local[N]")
    ap.add_argument("--cores-max", type=int, default=None)
    ap.add_argument("--executor-cores", type=int, default=None)
    ap.add_argument("--executor-memory", default="1800m")
    ap.add_argument("--configs", nargs="+", default=list(wf_peak.FIT_CONFIGS))
    ap.add_argument("--years", nargs="+", type=int, default=None)
    ap.add_argument("--seeds", nargs="+", type=int, default=list(wf_peak.SEEDS))
    ap.add_argument("--ref-dir", default=str(wf_peak.WORK), help="dự báo local để đối chiếu")
    ap.add_argument("--work-dir", default=str(WORK))
    ap.add_argument("--tag", required=True)
    a = ap.parse_args(argv)

    jobs = wf_peak.build_jobs(a.configs, tuple(a.seeds), a.years, threads=1)
    spark = get_spark(a.mode, app_name=f"wf_peak_{a.tag}", cores=a.cores, cores_max=a.cores_max,
                      executor_cores=a.executor_cores, executor_memory=a.executor_memory)
    info = describe(spark)
    print(f"{len(jobs)} lượt trên {info['master']} ({info['cores_used']} lõi)", flush=True)
    res, wall = run_spark(spark, jobs)
    spark.stop()

    work = Path(a.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    for r in res:
        wf_peak.to_frame(r).write_parquet(wf_peak.job_path(r, work))
    par = parity(res, Path(a.ref_dir))
    task_s = float(sum(r["time_s"] for r in res))
    # độ lệch cỡ 1e-13: ghi dạng chuỗi khoa học, không để float_precision làm tròn về 0
    par["parity_max_abs_diff"] = f"{par['parity_max_abs_diff']:.3e}"
    row = {"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "tag": a.tag,
           "engine": "spark", **info, "n_jobs": len(jobs), "wall_s": wall,
           "sum_task_s": task_s, "speedup_vs_serial": task_s / wall, **par}
    append_bench(row)
    print(f"wall {wall:.1f} s · tổng thời gian các lượt {task_s:.1f} s · "
          f"nhanh {task_s / wall:.2f}× so với nối tiếp")
    print(f"đối chiếu local: {par['parity_jobs']} lượt, {par['parity_values']} giá trị, "
          f"|Δ| tối đa {par['parity_max_abs_diff']}")
    print(f"→ {OUT_BENCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
