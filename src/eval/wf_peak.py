"""Walk-forward theo NĂM: thử giảm cắt ngọn lũ của mô hình chính E (Report 4).

Bối cảnh: E dự báo thấp đỉnh (peak_bias −0,45 / −0,71 / −0,86 trên test; trung vị
dự báo/thực trên ngày lũ 0,56 / 0,34 / 0,20). Quantile, ``min_child_samples`` và L2
đều không chữa được (``docs/FINDINGS_TUNING.md``). Ở đây thử hai hướng khác:

    E            mốc = mô hình chính (``lgbm.params_for(h)``: L1 ở h=1, L2 ở h=2–3)
    E w1, E w3   trọng số mẫu nhấn đỉnh khi học: w = 1 + α·max(0, y/ngưỡng1 − 1),
                 α = 1 hoặc 3; ngưỡng1 = Q95 mùa lũ của cửa sổ train (không rò rỉ)
    E iso        hiệu chỉnh lệch SAU khi dự báo: isotonic log1p(ŷ) → log1p(y) fit trên
                 dự báo NGOÀI MẪU của mọi fold năm < Y (fold 2005–2012 chỉ để có dữ
                 liệu hiệu chỉnh cho 2013) — năm test không bao giờ nằm trong tập fit
    E iso_hi     như ``E iso`` nhưng chỉ áp cho ŷ ≥ ngưỡng1/2 (giữ nguyên dòng chảy thấp)
    E+LSTM       trung bình 50/50 (đặt trước, không tinh chỉnh) dự báo E và LSTM L30 MSE
                 (``dl_lstm``, cùng fold ``walk_forward_dl.fold_bounds``, 3 seed) — LSTM ít
                 cắt ngọn hơn (peak_bias −0,26 so với −0,38, ``wf_dl_summary.csv``)

Fold, gap, ngưỡng y hệt ``wf_tuning`` (train mở rộng từ 1998-01-04, gap 3 ngày,
``walk_forward_sat.fold_threshold``). Dự báo = trung bình 3 seed. Một *lượt* =
cấu hình × năm × seed (cả 3 horizon) — đơn vị song song cho cả tiến trình local lẫn
Spark (``src/distributed/spark_walkforward.py`` gọi đúng ``run_job``).

Tiêu chí nhận (đặt TRƯỚC khi chạy, ``docs/FINDINGS_PEAK.md``): ΔNSE h2/h3 > 0 với
Wilcoxon p < 0,05 qua 13 fold 2013–2025 VÀ ΔNSE h1 ≥ −0,01; hoặc peak_bias / số ngày
lũ bắt được tăng rõ mà NSE không giảm quá 0,01. Test ≥ 07/2022 không dùng để chọn.

    python -m src.eval.wf_peak --stage run --n-procs 6        # ~400 lượt fit
    python -m src.eval.wf_peak --stage lstm --n-procs 6       # 39 lượt LSTM (2 luồng/lượt)
    python -m src.eval.wf_peak --stage summary                # gộp → CSV, không fit
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

import numpy as np
import polars as pl

from src import config as cfg
from src.eval import metrics
from src.eval.walk_forward_sat import boot_mean_ci, fold_threshold, wilcoxon_p, year_fold
from src.features import risk_levels as rl
from src.models import ablation_hourly as ab
from src.models import ablation_sat as sa
from src.models import lgbm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_FOLDS = cfg.ROOT / "reports" / "wf_peak_folds.csv"
OUT_SUMMARY = cfg.ROOT / "reports" / "wf_peak_summary.csv"
WORK = cfg.CACHE / "wf_peak"

START = sa.EXT_START
CAL_YEARS = tuple(range(2005, 2013))         # chỉ để có dự báo ngoài mẫu cho hiệu chỉnh
YEARS = tuple(range(2013, 2026))             # 13 fold chấm điểm, như wf_tuning
SEEDS = (42, 7, 2026)
BASE = "E"
FIT_CONFIGS = {BASE: 0.0, "E w1": 1.0, "E w3": 3.0, "E w5": 5.0, "E w10": 10.0}  # tên → α
POST_CONFIGS = ("E iso", "E iso_hi")
PERIODS = {"chinh_2013_2025": YEARS,
           "reanalysis_2013_2021": tuple(range(2013, 2022)),
           "forecast_2023_2025": (2023, 2024, 2025)}
MAIN = "chinh_2013_2025"


# ================================================================ một lượt

def e_features() -> list[str]:
    from src.eval.wf_tuning import e_features as ef
    return ef()


def peak_weights(y: np.ndarray, thr1: float, alpha: float) -> np.ndarray | None:
    """w = 1 + α·max(0, y/thr1 − 1); α = 0 ⇒ None (không trọng số)."""
    if alpha <= 0:
        return None
    return 1.0 + alpha * np.clip(y / thr1 - 1.0, 0.0, None)


def run_job(job: dict) -> dict:
    """Một lượt cấu hình × năm × seed, đủ 3 horizon. Trả về dict thuần (list) để
    chuyển qua tiến trình con / executor Spark mà không phụ thuộc phiên bản polars."""
    import pandas as pd
    from lightgbm import LGBMRegressor

    t0 = time.perf_counter()
    panel = pl.read_parquet(job.get("panel_path", sa.PANEL_EXT)).sort("date")
    feats = job.get("feats") or e_features()
    d = panel["date"].cast(pl.Date)
    X = panel.select(feats).to_numpy().astype(float)
    q0 = panel["discharge"].to_numpy().astype(float)
    flood_all = d.dt.month().is_in(rl.FLOOD_MONTHS).to_numpy()
    fold = year_fold(job["year"], START)
    thr1 = fold_threshold(panel, *fold["train"])
    alpha = FIT_CONFIGS[job["config"]]
    out = {k: [] for k in ("horizon", "date", "y", "yhat", "q0", "flood")}
    for h in cfg.HORIZONS:
        m = ab.masks(panel, feats, h, fold)
        tr, te = m["train"], m["test"]
        y = panel[f"target_h{h}"].to_numpy().astype(float)
        params = lgbm.params_for(h, random_state=job["seed"], n_jobs=job.get("threads", 1))
        model = LGBMRegressor(**params)
        model.fit(pd.DataFrame(X[tr], columns=feats), np.log1p(y[tr]),
                  sample_weight=peak_weights(y[tr], thr1, alpha))
        p = np.clip(np.expm1(model.predict(pd.DataFrame(X[te], columns=feats))), 0, None)
        n = int(te.sum())
        out["horizon"] += [h] * n
        out["date"] += d.filter(pl.Series(te)).to_list()
        out["y"] += y[te].tolist()
        out["yhat"] += p.tolist()
        out["q0"] += q0[te].tolist()
        out["flood"] += flood_all[te].tolist()
    return {**{k: job[k] for k in ("config", "year", "seed")}, "thr1": thr1,
            "cols": out, "time_s": time.perf_counter() - t0}


def to_frame(res: dict) -> pl.DataFrame:
    return pl.DataFrame(res["cols"]).with_columns(
        pl.lit(res["config"]).alias("config"), pl.lit(res["year"]).alias("fold"),
        pl.lit(res["seed"]).alias("seed"), pl.lit(res["thr1"]).alias("thr1"),
        pl.col("date").cast(pl.Date))


def build_jobs(configs=tuple(FIT_CONFIGS), seeds=SEEDS, years=None, threads: int = 1) -> list[dict]:
    """E chạy cả fold hiệu chỉnh 2005–2012; cấu hình trọng số chỉ cần 13 fold chấm."""
    jobs = []
    for c in configs:
        ys = years or ((*CAL_YEARS, *YEARS) if c == BASE else YEARS)
        jobs += [{"config": c, "year": y, "seed": s, "threads": threads} for y in ys for s in seeds]
    return sorted(jobs, key=lambda j: -j["year"])       # fold muộn (train dài) trước


def job_path(job: dict, work: Path = WORK) -> Path:
    return work / f"{job['config'].replace(' ', '_')}_{job['year']}_s{job['seed']}.parquet"


def run_local(jobs: list[dict], n_procs: int, work: Path = WORK, resume: bool = True) -> float:
    """Tiến trình local (đường chuẩn để đối chiếu với Spark). Trả về giây wall."""
    work.mkdir(parents=True, exist_ok=True)
    todo = [j for j in jobs if not (resume and job_path(j, work).exists())]
    print(f"{len(jobs)} lượt · {len(jobs) - len(todo)} có sẵn · {len(todo)} cần chạy · {n_procs} tiến trình")
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=n_procs, mp_context=get_context("spawn")) as ex:
        futs = [ex.submit(run_job, j) for j in todo]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            to_frame(r).write_parquet(job_path(r, work))
            print(f"  [{i:>3}/{len(todo)}] {r['config']:<6} {r['year']} s{r['seed']:<5}"
                  f" {r['time_s']:5.1f}s ({(time.perf_counter() - t0) / 60:.1f} ph)", flush=True)
    return time.perf_counter() - t0


# ================================================================ hiệu chỉnh sau dự báo

def isotonic_correct(cal_pred: np.ndarray, cal_y: np.ndarray, pred: np.ndarray,
                     floor: float | None = None) -> np.ndarray:
    """Isotonic tăng log1p(ŷ) → log1p(y) trên tập hiệu chỉnh; ``floor``: chỉ áp cho
    ŷ ≥ floor (dưới đó giữ nguyên ŷ). Ngoài miền hiệu chỉnh: kẹp (không ngoại suy)."""
    from sklearn.isotonic import IsotonicRegression

    iso = IsotonicRegression(out_of_bounds="clip", increasing=True)
    iso.fit(np.log1p(cal_pred), np.log1p(cal_y))
    corr = np.expm1(iso.predict(np.log1p(pred)))
    if floor is not None:
        corr = np.where(pred >= floor, corr, pred)
    return np.clip(corr, 0, None)


def ensemble(preds: pl.DataFrame) -> pl.DataFrame:
    """Trung bình seed cho mỗi cấu hình × fold × horizon × ngày (chỉ khi đủ mọi seed)."""
    n = preds["seed"].n_unique()
    return (preds.group_by("config", "fold", "horizon", "date")
                 .agg(pl.col("yhat").mean(), pl.col("seed").n_unique().alias("_k"),
                      pl.col("y", "q0", "flood", "thr1").first())
                 .filter(pl.col("_k") == n).drop("_k").sort("config", "fold", "horizon", "date"))


def add_post(ens: pl.DataFrame) -> pl.DataFrame:
    """Thêm ``E iso`` / ``E iso_hi``: fold Y hiệu chỉnh bằng dự báo E của fold < Y."""
    e = ens.filter(pl.col("config") == BASE)
    parts = []
    for (year, h), g in e.filter(pl.col("fold").is_in(list(YEARS))).group_by(
            ["fold", "horizon"], maintain_order=True):
        cal = e.filter((pl.col("fold") < year) & (pl.col("horizon") == h))
        assert cal["fold"].max() < year             # không bao giờ chạm năm test
        cp, cy = cal["yhat"].to_numpy(), cal["y"].to_numpy()
        p, thr1 = g["yhat"].to_numpy(), float(g["thr1"][0])
        parts += [g.with_columns(pl.Series("yhat", isotonic_correct(cp, cy, p)),
                                 pl.lit("E iso").alias("config")),
                  g.with_columns(pl.Series("yhat", isotonic_correct(cp, cy, p, floor=thr1 / 2)),
                                 pl.lit("E iso_hi").alias("config"))]
    return pl.concat([ens, *parts], how="vertical_relaxed")


# ================================================================ LSTM để ghép (B3)

LSTM_MODEL = "lstm_L30_mse"
LSTM_W = 0.5                                  # trọng số E trong E+LSTM, đặt trước
LSTM_REF = "E (ngày có LSTM)"


def run_lstm_job(job: dict) -> dict:
    """LSTM L30 MSE một fold × seed, giao thức ``walk_forward_dl`` (early stopping trên
    365 ngày cuối phần học, học lại trên toàn phần học)."""
    from src.eval import walk_forward_dl as wdl

    t0 = time.perf_counter()
    conf = {**wdl.DL_CONF[LSTM_MODEL], **wdl.fold_bounds(job["year"]), "seed": job["seed"],
            "num_threads": job.get("threads", 2)}
    from src.models import dl_lstm as dl
    r = dl.train(conf)
    dates = np.asarray(r["test_dates"]).astype("datetime64[D]")
    pred = np.asarray(r["pred"]["train+valid"])
    cols = {"horizon": [], "date": [], "yhat": []}
    for j, h in enumerate(cfg.HORIZONS):
        ok = np.isfinite(pred[:, j])
        cols["horizon"] += [h] * int(ok.sum())
        cols["date"] += dates[ok].tolist()
        cols["yhat"] += pred[ok, j].tolist()
    return {"config": "LSTM", "year": job["year"], "seed": job["seed"], "cols": cols,
            "time_s": time.perf_counter() - t0}


def lstm_path(job: dict, work: Path = WORK) -> Path:
    return work / "lstm" / f"lstm_{job['year']}_s{job['seed']}.parquet"


def run_lstm(n_procs: int, work: Path = WORK, years=YEARS, seeds=SEEDS) -> None:
    (work / "lstm").mkdir(parents=True, exist_ok=True)
    jobs = [{"year": y, "seed": s, "threads": 2} for y in years for s in seeds
            if not lstm_path({"year": y, "seed": s}, work).exists()]
    print(f"{len(jobs)} lượt LSTM · {n_procs} tiến trình × 2 luồng", flush=True)
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=n_procs, mp_context=get_context("spawn")) as ex:
        futs = [ex.submit(run_lstm_job, j) for j in sorted(jobs, key=lambda j: -j["year"])]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            (pl.DataFrame(r["cols"]).with_columns(pl.col("date").cast(pl.Date),
                                                  pl.lit(r["year"]).alias("fold"),
                                                  pl.lit(r["seed"]).alias("seed"))
               .write_parquet(lstm_path(r, work)))
            print(f"  [{i:>2}/{len(jobs)}] LSTM {r['year']} s{r['seed']} {r['time_s']:5.0f}s "
                  f"({(time.perf_counter() - t0) / 60:.1f} ph)", flush=True)


def add_lstm(ens: pl.DataFrame, work: Path = WORK) -> pl.DataFrame:
    """``E+LSTM`` = LSTM_W·E + (1−LSTM_W)·LSTM (trung bình seed mỗi bên), trên ngày chung."""
    files = sorted((work / "lstm").glob("lstm_*.parquet"))
    if not files:
        return ens
    lstm = pl.concat([pl.read_parquet(f) for f in files])
    n = lstm["seed"].n_unique()
    lstm = (lstm.group_by("fold", "horizon", "date")
                .agg(pl.col("yhat").mean().alias("_l"), pl.col("seed").n_unique().alias("_k"))
                .filter(pl.col("_k") == n).drop("_k"))
    e = ens.filter((pl.col("config") == BASE) & pl.col("fold").is_in(list(YEARS)))
    mix = (e.join(lstm, on=["fold", "horizon", "date"], how="inner")
            .with_columns((LSTM_W * pl.col("yhat") + (1 - LSTM_W) * pl.col("_l")).alias("yhat"),
                          pl.lit("E+LSTM").alias("config")).drop("_l"))
    # So cặp công bằng: E tính lại trên đúng các ngày có LSTM, đặt tên riêng
    base = e.join(mix.select("fold", "horizon", "date"), on=["fold", "horizon", "date"],
                  how="semi").with_columns(pl.lit(LSTM_REF).alias("config"))
    return pl.concat([ens, mix.select(ens.columns), base.select(ens.columns)],
                     how="vertical_relaxed")


# ================================================================ chấm điểm

def score(y: np.ndarray, yhat: np.ndarray, flood: np.ndarray, thr1: float) -> dict:
    rep = metrics.regression_report(y, yhat)
    ev = metrics.event_report(y >= thr1, yhat >= thr1)
    pos = y >= thr1
    return {"NSE": rep["NSE"], "NSE_flood": metrics.nse(y[flood], yhat[flood]),
            "KGE": rep["KGE"], "RMSE": rep["RMSE"], "peak_bias": rep["peak_bias"],
            "n_pos1": int(pos.sum()), "hits1": ev["hits"], "misses1": ev["misses"],
            "false_alarms1": ev["false_alarms"],
            "ratio_pos1_median": float(np.median(yhat[pos] / y[pos])) if pos.any() else np.nan}


def fold_scores(ens: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for (c, year, h), g in ens.filter(pl.col("fold").is_in(list(YEARS))).group_by(
            ["config", "fold", "horizon"], maintain_order=True):
        rows.append({"config": c, "fold": year, "horizon": h,
                     **score(g["y"].to_numpy(), g["yhat"].to_numpy(), g["flood"].to_numpy(),
                             float(g["thr1"][0]))})
    e = ens.filter((pl.col("config") == BASE) & pl.col("fold").is_in(list(YEARS)))
    for (year, h), g in e.group_by(["fold", "horizon"], maintain_order=True):
        rows.append({"config": "persistence", "fold": year, "horizon": h,
                     **score(g["y"].to_numpy(), g["q0"].to_numpy(), g["flood"].to_numpy(),
                             float(g["thr1"][0]))})
    f = pl.from_dicts(rows, infer_schema_length=None)
    # Mốc so cặp: E; riêng E+LSTM so với E trên đúng các ngày LSTM có dự báo
    ref = pl.when(pl.col("config") == "E+LSTM").then(pl.lit(LSTM_REF)).otherwise(pl.lit(BASE))
    b = f.select(pl.col("config").alias("_ref"), "fold", "horizon", pl.col("NSE").alias("_b"),
                 pl.col("peak_bias").alias("_bp"))
    return (f.with_columns(ref.alias("_ref")).join(b, on=["_ref", "fold", "horizon"], how="left")
             .with_columns((pl.col("NSE") - pl.col("_b")).alias("dNSE"),
                           (pl.col("peak_bias") - pl.col("_bp")).alias("d_peak_bias"))
             .drop("_ref", "_b", "_bp").sort("config", "horizon", "fold"))


def summarize(folds: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for period, years in PERIODS.items():
        f = folds.filter(pl.col("fold").is_in(list(years)))
        for (c, h), g in f.group_by(["config", "horizon"], maintain_order=True):
            dn = g["dNSE"].to_numpy()
            ref = c in (BASE, LSTM_REF)
            lo, hi = boot_mean_ci(dn) if not ref else (np.nan, np.nan)
            hits, miss = int(g["hits1"].sum()), int(g["misses1"].sum())
            fa = int(g["false_alarms1"].sum())
            rows.append({"period": period, "config": c, "horizon": h, "n_folds": g.height,
                         "NSE_mean": g["NSE"].mean(), "NSE_flood_mean": g["NSE_flood"].mean(),
                         "peak_bias_mean": g["peak_bias"].mean(),
                         "ratio_pos1_median": g["ratio_pos1_median"].median(),
                         "dNSE_mean": float(np.mean(dn)), "dNSE_ci_lo": lo, "dNSE_ci_hi": hi,
                         "wins": int((dn > 0).sum()), "losses": int((dn < 0).sum()),
                         "p_wilcoxon": wilcoxon_p(dn) if not ref else np.nan,
                         "hits1": hits, "misses1": miss, "false_alarms1": fa,
                         "POD1": hits / (hits + miss) if hits + miss else np.nan,
                         "FAR1": fa / (hits + fa) if hits + fa else np.nan})
    return pl.from_dicts(rows, infer_schema_length=None).sort("period", "horizon", "config")


def load_preds(work: Path = WORK) -> pl.DataFrame:
    files = sorted(work.glob("*.parquet"))
    if not files:
        raise SystemExit(f"Không có dự báo trong {work} — chạy --stage run trước.")
    return pl.concat([pl.read_parquet(f) for f in files], how="vertical_relaxed")


def stage_summary(work: Path = WORK) -> int:
    ens = add_lstm(add_post(ensemble(load_preds(work))), work)
    folds = fold_scores(ens)
    folds.write_csv(OUT_FOLDS, float_precision=6)
    summ = summarize(folds)
    summ.write_csv(OUT_SUMMARY, float_precision=6)
    show = summ.filter(pl.col("period") == MAIN).select(
        "config", "horizon", "NSE_mean", "dNSE_mean", "dNSE_ci_lo", "dNSE_ci_hi", "wins", "losses",
        "p_wilcoxon", "peak_bias_mean", "ratio_pos1_median", "POD1", "FAR1")
    with pl.Config(tbl_rows=40, tbl_cols=20, float_precision=3, tbl_width_chars=200):
        print(show)
    print(f"→ {OUT_FOLDS}\n→ {OUT_SUMMARY}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", choices=("run", "lstm", "summary"), required=True)
    ap.add_argument("--configs", nargs="+", default=list(FIT_CONFIGS))
    ap.add_argument("--years", nargs="+", type=int, default=None)
    ap.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    ap.add_argument("--n-procs", type=int, default=6)
    ap.add_argument("--threads", type=int, default=1, help="luồng LightGBM mỗi lượt")
    ap.add_argument("--work-dir", default=str(WORK))
    a = ap.parse_args(argv)
    work = Path(a.work_dir)
    if a.stage == "summary":
        return stage_summary(work)
    if a.stage == "lstm":
        run_lstm(a.n_procs, work)
        return 0
    jobs = build_jobs(a.configs, tuple(a.seeds), a.years, a.threads)
    todo = [j for j in jobs if not job_path(j, work).exists()]
    wall = run_local(jobs, a.n_procs, work)
    print(f"Thời gian (wall): {wall / 60:.1f} phút cho {len(todo)} lượt")
    if len(todo) == len(jobs):          # chỉ ghi số đo khi chạy đủ, không lấy từ cache
        from src.distributed.spark_walkforward import append_bench
        append_bench({"run_at": time.strftime("%Y-%m-%dT%H:%M"), "tag": f"pool_{a.n_procs}",
                      "engine": "process_pool", "cores_used": a.n_procs, "n_jobs": len(jobs),
                      "wall_s": wall})
    return 0


if __name__ == "__main__":
    sys.exit(main())
