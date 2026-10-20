"""Huấn luyện LSTM của ``src/models/dl_lstm.py`` PHÂN TÁN qua Spark (Report 4).

Cùng một hàm ``dl_lstm.train(config)`` (khi ``WORLD_SIZE > 1`` nó tự chạy DDP gloo
trên CPU: mỗi tiến trình một phần mẫu qua DistributedSampler, gradient được
all-reduce sau mỗi batch), chạy theo bốn cách để so kết quả và thời gian:

* ``single``      — 1 tiến trình, không Spark: mốc so sánh.
* ``distributor`` — ``pyspark.ml.torch.distributor.TorchDistributor``:
    - ``--local-mode``: torchrun N tiến trình ngay trên máy driver;
    - mặc định (cụm): 1 stage Spark *barrier* N task, mỗi task trên một executor
      chạy torchrun 1 tiến trình → N máy (container worker) cùng huấn luyện.
* ``barrier``     — tự cài đúng cơ chế TorchDistributor dùng bên trong nhưng bỏ
  torchrun: stage barrier N task, mỗi task lấy địa chỉ task 0 qua
  ``BarrierTaskContext``, đặt MASTER_ADDR/PORT, RANK, WORLD_SIZE rồi gọi ``train()``.

Vì sao cần ``barrier``: trên Windows TorchDistributor KHÔNG chạy được (thử thật
20/10/2026, torch 2.13 CPU, pyspark 4.1.3, Python 3.13). TorchDistributor
``local_mode`` gọi ``torchrun --standalone``, torchrun dựng TCPStore cho rendezvous
c10d với ``use_libuv`` mặc định, mà bản torch Windows không có libuv →
``DistStoreError: use_libuv was requested but PyTorch was built without libuv
support``. Đặt ``USE_LIBUV=0`` vẫn lỗi y vậy (đã thử): biến này chỉ tới được
``init_process_group``. (Rendezvous static cũng tạo TCPStore cùng kiểu — mới đọc mã
nguồn, chưa chạy.) Đường ``barrier`` không qua torchrun nên chạy được, có đặt
``USE_LIBUV=0``. Trong container Linux thì TorchDistributor chạy nguyên bản.

Chú ý khi đọc kết quả: N tiến trình × batch b ⇒ batch toàn cục N·b, số bước mỗi
epoch giảm N lần ⇒ đường học khác bản 1 tiến trình. ``--batch-per-proc 32`` với
N = 2 giữ batch toàn cục 64 như bản 1 tiến trình.

Kết quả 20/10/2026 (seed 42, ``lstm_L30_mse``, NSE test học trên train+valid;
``reports/spark_dl_results.csv``, bảng đầy đủ ở ``infra/spark/README.md``):

    1 tiến trình (Windows / container)            0,709 / 0,432 / 0,180   9–18 s
    DDP 2 rank, batch toàn cục 128 (mọi cách)     0,712 / 0,413 / 0,160
    DDP 2 rank, batch toàn cục 64                 0,704 / 0,413 / 0,165
    TorchDistributor 2 worker trên cụm: train() 9,9–10,1 s, wall 22,6–23,2 s
    (1 tiến trình trong container 9,0–9,5 s) ⇒ dữ liệu quá nhỏ, phân tán chậm hơn.

    python -m src.distributed.spark_dl --engine single --threads 4 --tag single_t4
    python -m src.distributed.spark_dl --engine barrier --procs 2 --threads 2 --tag barrier_2x2
    spark-submit --master spark://spark-master:7077 src/distributed/spark_dl.py \\
        --engine distributor --mode cluster --procs 2 --threads 4 --tag td_cluster_2x4
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import platform
import socket
import sys
import time
import traceback
from pathlib import Path

import polars as pl

from src import config as cfg

OUT_CSV = cfg.ROOT / "reports" / "spark_dl_results.csv"
METRICS = ["NSE", "KGE", "RMSE", "MAE", "peak_bias", "POD", "FAR", "CSI"]


# ================================================================ hàm chạy trong tiến trình con

def train_for_distributor(config: dict) -> dict | None:
    """``train()`` cho TorchDistributor.

    Ở ``local_mode`` mọi rank torchrun cùng chạy một script của FunctionPickler và
    cùng ghi MỘT file kết quả → rank ≠ 0 ghi đè ngẫu nhiên kết quả rank 0. Vì vậy
    khi nhiều rank chung một máy (LOCAL_WORLD_SIZE > 1), rank ≠ 0 thoát sạch
    (mã 0) ngay sau khi huấn luyện xong, không ghi gì. Trên cụm mỗi task có file
    riêng và Spark chỉ lấy kết quả của task 0.
    """
    from src.models.dl_lstm import train

    res = train(config)
    if (int(os.environ.get("RANK", "0")) != 0
            and int(os.environ.get("LOCAL_WORLD_SIZE", "1")) > 1):
        sys.stdout.flush()
        os._exit(0)
    return res


def _free_port(host: str) -> int:
    with socket.socket() as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def barrier_task(config: dict, n_procs: int, local_master: bool):
    """Hàm cho ``rdd.barrier().mapPartitions``: mỗi task = 1 rank DDP."""

    def run(_it):
        from pyspark import BarrierTaskContext, cloudpickle

        from src.models.dl_lstm import train

        ctx = BarrierTaskContext.get()
        rank = ctx.partitionId()
        hosts = [t.address.split(":")[0] for t in ctx.getTaskInfos()]
        master = "127.0.0.1" if local_master else hosts[0]
        port = ctx.allGather(str(_free_port(master)) if rank == 0 else "")[0]
        os.environ.update({"MASTER_ADDR": master, "MASTER_PORT": port, "RANK": str(rank),
                           "LOCAL_RANK": "0", "WORLD_SIZE": str(n_procs)})
        if os.name == "nt":
            os.environ["USE_LIBUV"] = "0"       # torch Windows không có libuv
        res = train(config)
        ctx.barrier()
        yield cloudpickle.dumps(res) if rank == 0 else b""

    return run


# ================================================================ các cách chạy

def run_single(conf: dict) -> dict:
    from src.models.dl_lstm import train

    for k in ("WORLD_SIZE", "RANK"):
        os.environ.pop(k, None)
    return train(conf)


def run_barrier(spark, conf: dict, n_procs: int) -> dict:
    from pyspark import cloudpickle

    sc = spark.sparkContext
    fn = barrier_task(conf, n_procs, sc.master.startswith("local"))
    out = sc.parallelize(range(n_procs), n_procs).barrier().mapPartitions(fn).collect()
    blobs = [b for b in out if b]
    if len(blobs) != 1:
        raise RuntimeError(f"cần đúng 1 kết quả từ rank 0, nhận {len(blobs)}")
    return cloudpickle.loads(blobs[0])


class _Tee:
    """Giữ lại log torchrun (TorchDistributor in thẳng ra stdout) để ghi nguyên nhân gốc
    khi hỏng — exception của nó chỉ nói chung chung 'failed during training'."""

    def __init__(self, stream):
        self.stream, self.lines = stream, []

    def write(self, s: str) -> int:
        self.lines.extend(s.splitlines())
        del self.lines[:-200]
        return self.stream.write(s)

    def flush(self) -> None:
        self.stream.flush()

    def root_cause(self) -> str:
        errs = [ln.strip() for ln in self.lines if "Error:" in ln and "Traceback" not in ln]
        return errs[0] if errs else ""


def run_distributor(conf: dict, n_procs: int, local_mode: bool) -> dict:
    from pyspark.ml.torch.distributor import TorchDistributor

    if os.name == "nt":
        os.environ["USE_LIBUV"] = "0"           # thử hết cách; torchrun vẫn không đọc biến này
    td = TorchDistributor(num_processes=n_procs, local_mode=local_mode, use_gpu=False)
    tee, old = _Tee(sys.stdout), sys.stdout
    sys.stdout = tee
    try:
        res = td.run(train_for_distributor, conf)
    except Exception as e:
        raise RuntimeError(f"{tee.root_cause() or e}") from e
    finally:
        sys.stdout = old
    if not isinstance(res, dict) or res.get("rank", 0) != 0:
        raise RuntimeError(f"TorchDistributor trả về kết quả không phải của rank 0: {res!r:.200}")
    return res


# ================================================================ ghi kết quả

def _host() -> str:
    tag = "docker" if Path("/.dockerenv").exists() else "host"
    return f"{platform.system().lower()}-{tag}"


def result_rows(meta: dict, res: dict | None) -> list[dict]:
    """Một dòng mỗi (fit, split, horizon); chạy hỏng → 1 dòng ghi lỗi, chỉ số rỗng."""
    if res is None:
        return [{**meta, "fit": None, "split": None, "horizon": None}]
    base = {**meta, "world_size": res["world_size"], "best_epoch": res["best_epoch"],
            "stopped_epoch": res["stopped_epoch"], "n_train": res["n_train"],
            "n_trval": res["n_trval"], "n_test": res["n_test"], "n_params": res["n_params"],
            "train_s": round(res["time_s"], 2), "risk1_threshold": round(res["threshold"], 1)}
    return [{**base, "fit": r["fit"], "split": r["split"], "horizon": r["horizon"], "n": r["n"],
             **{m: r.get(m) for m in METRICS}} for r in res["results"]]


def save_rows(rows: list[dict], path: Path = OUT_CSV) -> pl.DataFrame:
    """Ghép vào CSV, thay các dòng cũ cùng ``tag`` (chạy lại không nhân đôi)."""
    new = pl.DataFrame(rows, infer_schema_length=None)
    if path.exists():
        old = pl.read_csv(path, infer_schema_length=0)
        old = old.filter(~pl.col("tag").is_in(new["tag"].unique().to_list()))
        new = pl.concat([old, new.cast(pl.Utf8)], how="diagonal")
    path.parent.mkdir(parents=True, exist_ok=True)
    new.write_csv(path)
    return new


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", choices=["single", "barrier", "distributor"], required=True)
    ap.add_argument("--procs", type=int, default=2, help="số tiến trình DDP")
    ap.add_argument("--threads", type=int, default=2, help="torch threads mỗi tiến trình")
    ap.add_argument("--batch-per-proc", type=int, default=None,
                    help="batch mỗi tiến trình (mặc định = batch của dl_lstm)")
    ap.add_argument("--seed", type=int, default=cfg.SEED)
    ap.add_argument("--local-mode", action="store_true", help="TorchDistributor(local_mode=True)")
    ap.add_argument("--mode", choices=["local", "cluster"], default=None)
    ap.add_argument("--cores-max", type=int, default=None)
    ap.add_argument("--executor-cores", type=int, default=None)
    ap.add_argument("--quick", action="store_true", help="chạy thử 3 epoch")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=OUT_CSV)
    a = ap.parse_args(argv)

    from src.models.dl_lstm import DEFAULTS

    conf = {**DEFAULTS, "seed": a.seed, "num_threads": a.threads,
            **({"batch_size": a.batch_per_proc} if a.batch_per_proc else {}),
            **({"max_epochs": 3, "patience": 2} if a.quick else {})}
    procs = 1 if a.engine == "single" else a.procs
    # tiến trình con (python worker, torchrun) phải import được src.*
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(cfg.ROOT), *[p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]])
    meta = {"run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "tag": a.tag, "engine": a.engine, "host": _host(), "master": "",
            "local_mode": a.local_mode if a.engine == "distributor" else None,
            "num_processes": procs, "threads_per_process": a.threads,
            "total_threads": procs * a.threads, "batch_per_process": conf["batch_size"],
            "global_batch": conf["batch_size"] * procs, "model": conf["name"], "seed": a.seed,
            "max_epochs": conf["max_epochs"], "status": "ok", "error": ""}

    spark = None
    t0 = time.perf_counter()
    res = None
    try:
        if a.engine != "single":
            from src.distributed.spark_session import get_spark

            extra = {}
            if a.mode == "cluster" or (a.mode is None and os.environ.get("SPARK_MASTER")):
                # 1 task chiếm trọn 1 executor ⇒ N task barrier nằm trên N worker khác nhau
                extra["spark.task.cpus"] = str(a.executor_cores or a.threads)
            spark = get_spark(a.mode, app_name=f"dl-{a.tag}", cores=procs,
                              cores_max=a.cores_max, executor_cores=a.executor_cores,
                              extra_conf=extra)
            meta["master"] = spark.sparkContext.master
        t1 = time.perf_counter()
        if a.engine == "single":
            res = run_single(conf)
        elif a.engine == "barrier":
            res = run_barrier(spark, conf, procs)
        else:
            res = run_distributor(conf, procs, a.local_mode)
        meta["wall_s"] = round(time.perf_counter() - t1, 2)
        if spark is not None:
            from src.distributed.spark_etl import _n_executors

            meta["n_executors"] = _n_executors(spark)      # local[*] → 0
            meta["task_cpus"] = spark.conf.get("spark.task.cpus", "1")
    except Exception as e:  # noqa: BLE001 — ghi lại lỗi thật vào bảng kết quả
        traceback.print_exc()
        msg = " ".join(str(e).split())
        key = [ln for ln in traceback.format_exc().splitlines() if "Error" in ln]
        meta.update(status="failed", wall_s=round(time.perf_counter() - t0, 2),
                    error=(key[-1].strip() if key else msg)[:300])
    finally:
        meta["wall_with_startup_s"] = round(time.perf_counter() - t0, 2)
        if spark is not None:
            spark.stop()

    rows = result_rows(meta, res)
    save_rows(rows, a.out)
    print(f"[{a.tag}] {a.engine} · {procs} tiến trình × {a.threads} luồng · batch toàn cục "
          f"{meta['global_batch']} · {meta['status']} · {meta['wall_s']} s "
          f"(gồm khởi động {meta['wall_with_startup_s']} s)")
    if res is not None:
        print(f"  world_size {res['world_size']}, best_epoch {res['best_epoch']}, "
              f"train() {res['time_s']:.1f} s")
        for r in res["results"]:
            print(f"  {r['fit']:<12} {r['split']:<6} h{r['horizon']}  NSE {r['NSE']:+.4f}  "
                  f"KGE {r['KGE']:+.4f}")
    else:
        print(f"  lỗi: {meta['error']}")
    print(f"→ {a.out}")
    return 0 if res is not None else 1


if __name__ == "__main__":
    sys.exit(main())
