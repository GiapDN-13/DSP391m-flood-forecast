"""Walk-forward theo năm: Deep Learning so với LightGBM trên nhiều fold (Report 4).

Bảng của `src/models/dl_lstm.py` chỉ dựa trên MỘT lần chia (test ≥ 2022-07-01) và
còn phụ thuộc số luồng torch. File này chấm lại trên 13 năm test 2013–2025
(+ 2026 tới tháng 8, báo riêng) để biết DL có thật sự hơn LightGBM ở h = 2–3 không.

Fold năm Y — cửa sổ mở rộng, panel từ 2010-01-01::

    học    : mọi ngày ≤ 28/12/(Y-1)        bỏ 3 ngày cuối = gap ≥ horizon dài nhất
    test   : ngày phát dự báo t ∈ 01/01/Y … 31/12/Y
    DL     : valid = 365 ngày cuối phần học; train trong = phần trước valid, cách
             valid 3 ngày gap. Early stopping trên valid → học lại trên TOÀN BỘ phần
             học đúng số epoch tốt nhất (giao thức `dl_lstm.train`). Chuẩn hoá và
             trọng số đỉnh lấy thống kê của train trong.
    ngưỡng : mức nguy cơ 1 = Q95 mùa lũ trên phần học của fold (`dl.risk_threshold`).

Mô hình: LightGBM (`lgbm.PARAMS`, cột như `lgbm.py`, n_jobs = 2 — cho đúng số
0,747/0,420/0,175 như mặc định), LSTM L30 MSE, LSTM L30 loss nhấn đỉnh, MLP trên cột
lag loss nhấn đỉnh; mỗi mô hình 3 seed (LightGBM đổi random_state). DL cố định
2 luồng torch. Persistence chỉ để tham chiếu. Thêm kiểm độ nhạy số luồng (1/2/4,
cộng một lần chạy lại 2 luồng) trên fold 2020 và 2024, seed 42.

Metric mỗi fold × mô hình × h: NSE, NSE mùa lũ (tháng 9–12 theo ngày phát t), KGE,
peak_bias, hits/misses/false alarms mức 1 (so Q dự báo với ngưỡng). Tổng hợp so với
LightGBM: ΔNSE từng fold (trung bình 3 seed mỗi bên), CI 95 % bootstrap theo fold,
thắng/thua, Wilcoxon; POD/FAR/CSI gộp sự kiện qua fold.

Kết quả lần chạy 20/10/2026 (`reports/wf_dl_summary.csv`; 13 fold 2013–2025; ΔNSE =
mô hình − LightGBM, TB qua fold [CI 95 %], thắng/thua, Wilcoxon p; h1 · h2 · h3)::

    LightGBM NSE TB     0,743 · 0,334 · 0,118
    LSTM L30 MSE        +0,021 [−0,014; 0,058] 8/5 p 0,38 · −0,025 [−0,117; 0,032] 7/6
                        p 0,74 · −0,026 [−0,101; 0,021] 7/6 p 1,00
    LSTM L30 nhấn đỉnh  −0,007 · −0,107 [−0,239; −0,008] 5/8 p 0,17 · −0,229 [−0,411;
                        −0,073] 5/8 p 0,033
    MLP lag nhấn đỉnh   +0,000 · −0,065 [−0,142; 0,002] 5/8 p 0,15 · −0,118 [−0,255;
                        −0,015] 6/7 p 0,094

→ Không cấu hình DL nào hơn LightGBM một cách vững ở horizon nào. 2023–2025 DL thắng
h2–h3 cả 3/3 fold (+0,01…+0,05, đúng giai đoạn của lần chia đơn) nhưng 2013–2021 thua
và 2026 (01–08) thua. Bỏ 3 fold đầu (2016–2025, DL có ≥ 5 năm train trong): LSTM MSE
+0,031 / +0,023 / +0,015, CI chạm 0, p ≥ 0,19. h=1 gộp 106 ngày sự kiện: DL tăng POD
(0,59–0,63 so với 0,51), FAR ngang hoặc cao hơn, CSI 0,49–0,50 so với 0,44.
Số luồng: LSTM 1/2/4 luồng cho NSE y hệt (fold 2020, 2024); MLP nhấn đỉnh lệch tối đa
0,028 (2024, 4 luồng); chạy lại 2 luồng khớp tuyệt đối — nhỏ hơn sd giữa seed (TB
0,03–0,20) và |ΔNSE| giữa mô hình (TB 0,04–0,26). 194 lượt, 12,8 phút (6 × 2 luồng).

    python -m src.eval.walk_forward_dl                  # 6 tiến trình × 2 luồng
    python -m src.eval.walk_forward_dl --resume          # dùng lại job đã xong (.cache/wf_dl)
    python -m src.eval.walk_forward_dl --quick           # chạy thử: 2 fold, 3 epoch
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context

import numpy as np
import polars as pl

from src import config as cfg
from src.eval import metrics
from src.eval.walk_forward import GAP_DAYS
from src.features.risk_levels import FLOOD_MONTHS
from src.models import dl_lstm as dl

OUT_FOLDS = cfg.ROOT / "reports" / "wf_dl_folds.csv"
OUT_SUMMARY = cfg.ROOT / "reports" / "wf_dl_summary.csv"
OUT_FIG = cfg.FIGURES / "report" / "wf_dl_en.png"
CACHE = cfg.CACHE / "wf_dl"

TEST_YEARS = tuple(range(2013, 2026))    # 13 fold đủ 12 tháng
EXTRA_YEAR = 2026                         # chỉ tới 08/2026 → báo riêng
VALID_DAYS = 365
THREADS = 2                               # cố định cho mọi lần chạy DL chính
SEEDS = dl.SEEDS
REF = "lightgbm"
MODELS = (REF, "lstm_L30_mse", "lstm_L30_peak", "mlp_lag_peak")
DL_CONF = {e["name"]: e for e in dl.EXPERIMENTS}
SENS_YEARS, SENS_MODELS, SENS_THREADS = (2020, 2024), ("lstm_L30_mse", "mlp_lag_peak"), (1, 2, 4)
# 2022 để riêng: GloFAS đổi từ reanalysis sang archived forecast 07/2022.
# 2016-2025 = kiểm độ nhạy: bỏ 3 fold đầu, nơi DL chỉ có 2–4 năm train trong.
PERIODS = {"2013-2025": range(2013, 2026), "2013-2021": range(2013, 2022),
           "2022": (2022,), "2023-2025": range(2023, 2026), "2016-2025": range(2016, 2026),
           "2026 (01-08)": (2026,)}
N_BOOT = 10_000


# ----------------------------------------------------------------- fold

def fold_bounds(year: int, gap: int = GAP_DAYS, valid_days: int = VALID_DAYS) -> dict[str, str]:
    """Mốc ngày (ISO) của fold năm `year` — cũng chính là khoá config của `dl.train`.

    valid_end = ngày học cuối cùng (28/12 năm trước với gap 3), train_end = cuối
    train trong (trước valid_start một gap).
    """
    one = dt.timedelta(days=1)
    test_start = dt.date(year, 1, 1)
    fit_end = test_start - (gap + 1) * one
    valid_start = fit_end - (valid_days - 1) * one
    train_end = valid_start - (gap + 1) * one
    return {"train_end": train_end.isoformat(), "valid_start": valid_start.isoformat(),
            "valid_end": fit_end.isoformat(), "test_start": test_start.isoformat(),
            "test_end": dt.date(year, 12, 31).isoformat()}


def fold_masks(dates: np.ndarray, b: dict) -> tuple[np.ndarray, np.ndarray]:
    """(phần học, năm test) cho mô hình không cần valid (LightGBM, persistence)."""
    d = dates.astype("datetime64[D]")
    fit = d <= np.datetime64(b["valid_end"])
    te = (d >= np.datetime64(b["test_start"])) & (d <= np.datetime64(b["test_end"]))
    return fit, te


# ----------------------------------------------------------------- chấm điểm

def score(dates: np.ndarray, y: np.ndarray, yhat: np.ndarray, thr: float) -> list[dict]:
    """Chỉ số mỗi horizon; y, yhat dạng (n, 3) m³/s, dates = ngày phát dự báo t."""
    months = (dates.astype("datetime64[M]").astype(int) % 12) + 1
    flood = np.isin(months, FLOOD_MONTHS)
    rows = []
    for j, h in enumerate(cfg.HORIZONS):
        ok = np.isfinite(y[:, j]) & np.isfinite(yhat[:, j])
        yt, yp = y[ok, j], yhat[ok, j]
        rep = metrics.regression_report(yt, yp)
        c = metrics.contingency(yt >= thr, yp >= thr)
        rows.append({"horizon": h, "NSE": rep["NSE"],
                     "NSE_flood": metrics.nse(y[ok & flood, j], yhat[ok & flood, j]),
                     "KGE": rep["KGE"], "RMSE": rep["RMSE"], "peak_bias": rep["peak_bias"],
                     "hits": c["hits"], "misses": c["misses"],
                     "false_alarms": c["false_alarms"], "n": rep["n"],
                     "n_flood": int((ok & flood).sum())})
    return rows


# ----------------------------------------------------------------- một lượt

def _panel(path: str) -> tuple[pl.DataFrame, np.ndarray, np.ndarray]:
    df = pl.read_parquet(path).sort("date")
    Y = df.select([f"target_h{h}" for h in cfg.HORIZONS]).cast(pl.Float64).to_numpy()
    return df, df["date"].cast(pl.Date).to_numpy(), Y


def _lightgbm(job: dict, b: dict) -> tuple:
    import pandas as pd  # chỉ bọc pandas ngay trước LightGBM (lỗi force_all_finite với numpy)
    from lightgbm import LGBMRegressor

    from src.models.lgbm import PARAMS

    df, dates, Y = _panel(job["panel_path"])
    feats = dl.feature_list(dict(df.schema), "full")
    X = df.select(feats).cast(pl.Float64).to_numpy()
    q = df["discharge"].cast(pl.Float64).to_numpy()
    fit, te = fold_masks(dates, b)
    x_ok = np.isfinite(X).all(axis=1)
    k = te & x_ok
    X_te = pd.DataFrame(X[k], columns=feats)
    yhat = np.full((int(k.sum()), len(cfg.HORIZONS)), np.nan)
    for j, h in enumerate(cfg.HORIZONS):
        a = fit & x_ok & np.isfinite(Y[:, j])
        m = LGBMRegressor(**{**PARAMS, "random_state": job["seed"], "n_jobs": job["threads"]})
        m.fit(pd.DataFrame(X[a], columns=feats), np.log1p(Y[a, j]))
        yhat[:, j] = np.clip(np.expm1(m.predict(X_te)), 0, None)
    return dates[k], Y[k], yhat, dl.risk_threshold(q, dates, fit), \
        {"n_fit": int((fit & x_ok).sum())}


def _persistence(job: dict, b: dict) -> tuple:
    df, dates, Y = _panel(job["panel_path"])
    q = df["discharge"].cast(pl.Float64).to_numpy()
    fit, te = fold_masks(dates, b)
    k = te & np.isfinite(q)
    return dates[k], Y[k], np.repeat(q[k, None], len(cfg.HORIZONS), axis=1), \
        dl.risk_threshold(q, dates, fit), {"n_fit": int(fit.sum())}


def _deep(job: dict, b: dict) -> tuple:
    conf = {**DL_CONF[job["model"]], **b, "seed": job["seed"], "num_threads": job["threads"],
            "panel_path": job["panel_path"], **job.get("override", {})}
    r = dl.train(conf)
    return r["test_dates"], r["y_test"], r["pred"]["train+valid"], r["threshold"], \
        {"n_fit": r["n_trval"], "n_train_inner": r["n_train"], "n_valid": r["n_valid"],
         "best_epoch": r["best_epoch"], "stopped_epoch": r["stopped_epoch"]}


def run_job(job: dict) -> dict:
    """Một lượt mô hình × fold × seed × số luồng. Hàm cấp module → chạy được ở tiến trình con."""
    t0 = time.perf_counter()
    b = fold_bounds(job["year"])
    fn = {REF: _lightgbm, "persistence": _persistence}.get(job["model"], _deep)
    dates, y, yhat, thr, info = fn(job, b)
    key = {k: job[k] for k in ("run", "model", "year", "seed", "threads")}
    rows = [{**key, **info, "threshold": thr, **r} for r in score(dates, y, yhat, thr)]
    t = time.perf_counter() - t0
    return {"job": job, "rows": [{**r, "time_s": t} for r in rows], "time_s": t}


# ----------------------------------------------------------------- lịch chạy

def build_jobs(years: list[int], seeds: tuple[int, ...], sens: bool, panel_path: str,
               override: dict | None = None) -> list[dict]:
    """Danh sách lượt chạy, lượt nặng (DL, fold muộn) trước để cân tải."""
    base = {"panel_path": panel_path, **({"override": override} if override else {})}
    jobs = [{**base, "run": "main", "model": m, "year": y, "seed": s, "threads": THREADS}
            for m in MODELS for y in years for s in seeds]
    jobs += [{**base, "run": "main", "model": "persistence", "year": y, "seed": 0,
              "threads": 1} for y in years]
    if sens:
        jobs += [{**base, "run": "threads", "model": m, "year": y, "seed": SEEDS[0],
                  "threads": t}
                 for m in SENS_MODELS for y in SENS_YEARS if y in years for t in SENS_THREADS]
    w = {"lstm_L30_mse": 5.0, "lstm_L30_peak": 5.0, "mlp_lag_peak": 1.0, REF: 0.5}
    return sorted(jobs, key=lambda j: -w.get(j["model"], 0.1) * (j["year"] - 2009))


def _job_id(job: dict, prefix: str) -> str:
    return f"{prefix}{job['run']}_{job['model']}_{job['year']}_s{job['seed']}_t{job['threads']}"


def _plain(v):
    return v.item() if isinstance(v, np.generic) else v


def run_all(jobs: list[dict], n_jobs: int, budget: int, resume: bool, prefix: str) -> list[dict]:
    """Chạy song song, tôn trọng ngân sách luồng (n_jobs × THREADS): lượt 4 luồng chạy riêng."""
    from src.eval.walk_forward_dl import run_job as run_fn  # picklable cho tiến trình con

    CACHE.mkdir(parents=True, exist_ok=True)
    rows, todo = [], []
    for j in jobs:
        f = CACHE / f"{_job_id(j, prefix)}.json"
        if resume and f.exists():
            rows += json.loads(f.read_text(encoding="utf-8"))
        else:
            todo.append(j)
    print(f"{len(jobs)} lượt · {len(jobs) - len(todo)} lấy từ cache · {len(todo)} cần chạy")
    t0 = time.perf_counter()
    groups = [[j for j in todo if j["threads"] <= THREADS], [j for j in todo if j["threads"] > THREADS]]
    for grp in groups:
        if not grp:
            continue
        workers = max(1, min(n_jobs, budget // max(j["threads"] for j in grp)))
        print(f"  nhóm {len(grp)} lượt · {workers} tiến trình × ≤{max(j['threads'] for j in grp)} luồng")
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as ex:
            futs = {ex.submit(run_fn, j): j for j in grp}
            for i, fu in enumerate(as_completed(futs), 1):
                r = fu.result()
                j = r["job"]
                out = [{k: _plain(v) for k, v in x.items()} for x in r["rows"]]
                (CACHE / f"{_job_id(j, prefix)}.json").write_text(
                    json.dumps(out), encoding="utf-8")
                rows += out
                ep = out[0].get("best_epoch")
                print(f"  [{i:>3}/{len(grp)}] {j['run']:<7} {j['model']:<14} {j['year']} "
                      f"s{j['seed']:<5} t{j['threads']}  "
                      + "  ".join(f"h{x['horizon']} {x['NSE']:+.3f}" for x in out)
                      + (f"  ep* {ep:>3}" if ep is not None else "")
                      + f"  ({r['time_s']:.0f}s, {(time.perf_counter() - t0) / 60:.1f} ph)",
                      flush=True)
    print(f"Thời gian chạy (wall): {(time.perf_counter() - t0) / 60:.1f} phút")
    return rows


# ----------------------------------------------------------------- tổng hợp

def boot_ci(d: np.ndarray, n_boot: int = N_BOOT, seed: int = cfg.SEED) -> tuple[float, float]:
    """CI 95 % percentile của trung bình, bootstrap lại theo fold."""
    d = np.asarray(d, dtype=float)
    if len(d) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (n_boot, len(d)))].mean(axis=1)
    return float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def wilcoxon_p(d: np.ndarray) -> float:
    from scipy.stats import wilcoxon

    d = np.asarray(d, dtype=float)
    if len(d) < 2 or np.all(d == 0):
        return np.nan
    return float(wilcoxon(d).pvalue)


def per_fold(folds: pl.DataFrame) -> pl.DataFrame:
    """Trung bình qua seed mỗi mô hình × năm × h (run = main)."""
    return (folds.filter(pl.col("run") == "main")
            .group_by(["model", "year", "horizon"])
            .agg(pl.len().alias("n_seeds"),
                 *[pl.col(c).fill_nan(None).mean().alias(c)
                   for c in ("NSE", "NSE_flood", "KGE", "peak_bias")],
                 pl.col("NSE").std(ddof=1).alias("NSE_seed_sd"))
            .sort(["model", "year", "horizon"]))


def _events(folds: pl.DataFrame, model: str, h: int, years) -> dict:
    """POD/FAR/CSI gộp sự kiện qua các fold: cộng bảng 2×2 mỗi seed rồi lấy TB qua seed."""
    d = (folds.filter((pl.col("run") == "main") & (pl.col("model") == model)
                      & (pl.col("horizon") == h) & pl.col("year").is_in(list(years)))
         .group_by("seed").agg(pl.col("hits", "misses", "false_alarms").sum()))
    if not d.height:
        return {}
    a, m, f = (d[c].to_numpy().astype(float) for c in ("hits", "misses", "false_alarms"))
    with np.errstate(invalid="ignore", divide="ignore"):    # cùng công thức metrics.event_report
        ev = {"POD": a / (a + m), "FAR": f / (a + f), "CSI": a / (a + m + f)}
    out = {k: float(np.nanmean(v)) if np.isfinite(v).any() else np.nan for k, v in ev.items()}
    return {"hits": a.mean(), "misses": m.mean(), "false_alarms": f.mean(), **out}


def summarize(folds: pl.DataFrame) -> pl.DataFrame:
    """Bảng tổng hợp: so với LightGBM theo giai đoạn + độ nhạy số luồng."""
    pf = per_fold(folds)
    ref = pf.filter(pl.col("model") == REF).select(
        "year", "horizon", pl.col("NSE").alias("NSE_ref"))
    pf = pf.join(ref, on=["year", "horizon"], how="left").with_columns(
        (pl.col("NSE") - pl.col("NSE_ref")).alias("dNSE"))
    rows = []
    models = [m for m in (*MODELS, "persistence") if pf.filter(pl.col("model") == m).height]
    for period, years in PERIODS.items():
        for m in models:
            for h in cfg.HORIZONS:
                d = pf.filter((pl.col("model") == m) & (pl.col("horizon") == h)
                              & pl.col("year").is_in(list(years)))
                if not d.height:
                    continue
                dn = d["dNSE"].drop_nulls().to_numpy()
                cmp = m != REF and len(dn) > 0
                lo, hi = boot_ci(dn) if cmp else (np.nan, np.nan)
                rows.append({
                    "table": "vs_lightgbm", "period": period, "model": m, "horizon": h,
                    "n_folds": d.height, "n_seeds": int(d["n_seeds"].max()),
                    "NSE_mean": d["NSE"].mean(), "NSE_median": d["NSE"].median(),
                    "NSE_min": d["NSE"].min(), "NSE_flood_mean": d["NSE_flood"].mean(),
                    "KGE_mean": d["KGE"].mean(), "peak_bias_mean": d["peak_bias"].mean(),
                    "NSE_seed_sd_mean": d["NSE_seed_sd"].mean(),
                    "dNSE_mean": float(dn.mean()) if cmp else np.nan,
                    "dNSE_ci_lo": lo, "dNSE_ci_hi": hi,
                    "abs_dNSE_mean": float(np.abs(dn).mean()) if cmp else np.nan,
                    "wins": int((dn > 0).sum()) if cmp else None,
                    "losses": int((dn < 0).sum()) if cmp else None,
                    "wilcoxon_p": wilcoxon_p(dn) if cmp else np.nan,
                    **_events(folds, m, h, years)})

    # Độ nhạy số luồng: NSE 1/2/4 luồng (+ chạy lại 2 luồng) so với chênh lệch giữa mô hình.
    th = folds.filter(pl.col("run") == "threads")
    for m in SENS_MODELS:
        for y in SENS_YEARS:
            for h in cfg.HORIZONS:
                d = th.filter((pl.col("model") == m) & (pl.col("year") == y)
                              & (pl.col("horizon") == h))
                if not d.height:
                    continue
                v = {t: d.filter(pl.col("threads") == t)["NSE"].to_list() for t in SENS_THREADS}
                main = folds.filter((pl.col("run") == "main") & (pl.col("model") == m)
                                    & (pl.col("year") == y) & (pl.col("horizon") == h))
                m42 = main.filter((pl.col("seed") == SEEDS[0])
                                  & (pl.col("threads") == THREADS))["NSE"].to_list()
                nse_t = [v[t][0] for t in SENS_THREADS if v[t]]
                f = pf.filter((pl.col("model") == m) & (pl.col("year") == y)
                              & (pl.col("horizon") == h))
                rows.append({
                    "table": "threads", "period": str(y), "model": m, "horizon": h,
                    **{f"NSE_t{t}": (v[t][0] if v[t] else np.nan) for t in SENS_THREADS},
                    "NSE_t2_main": m42[0] if m42 else np.nan,
                    "thread_range": float(np.ptp(nse_t)) if len(nse_t) > 1 else np.nan,
                    "NSE_seed_sd_mean": f["NSE_seed_sd"][0] if f.height else np.nan,
                    "dNSE_mean": f["dNSE"][0] if f.height else np.nan,
                    "abs_dNSE_mean": abs(f["dNSE"][0]) if f.height else np.nan})
    out = pl.DataFrame(rows, infer_schema_length=None)
    num = [c for c, t in out.schema.items() if t.is_float()]
    return out.with_columns([pl.col(c).round(4) for c in num])


# ----------------------------------------------------------------- hình

LABELS = {REF: "LightGBM", "persistence": "Persistence", **dl.LABELS}
STYLE = {REF: (dl.C_LGBM, "o"), "lstm_L30_mse": (dl.C_LSTM, "s"),
         "lstm_L30_peak": (dl.C_PEAK, "^"), "mlp_lag_peak": (dl.C_MLP, "D"),
         "persistence": (dl.C_PERS, None)}


def plot(folds: pl.DataFrame, summary: pl.DataFrame, out=OUT_FIG) -> None:
    """Hàng trên: NSE theo năm test; hàng dưới: ΔNSE so với LightGBM (dải xám = dao động số luồng)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pf = per_fold(folds)
    years = sorted(pf["year"].unique().to_list())
    full = [y for y in years if y != EXTRA_YEAR]
    th = summary.filter(pl.col("table") == "threads")

    def style(ax, title):
        ax.set_title(title, loc="left", fontsize=10.5, color=dl.C_INK)
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=dl.C_GRID, lw=0.8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(colors=dl.C_INK2, labelsize=9)

    fig, axes = plt.subplots(2, 3, figsize=(16, 9.5), facecolor=dl.C_SURF, sharex=True,
                             gridspec_kw={"height_ratios": [1.25, 1], "hspace": 0.25,
                                          "wspace": 0.18, "top": 0.85})
    for i, h in enumerate(cfg.HORIZONS):
        ax, axd = axes[0, i], axes[1, i]
        for ax_ in (ax, axd):
            ax_.axvspan(2021.5, 2022.5, color=dl.C_GRID, alpha=0.5, lw=0)
        lo_all = []
        ref = dict(pf.filter((pl.col("model") == REF) & (pl.col("horizon") == h))
                   .select("year", "NSE").iter_rows())
        for m in ("persistence", *MODELS):
            d = pf.filter((pl.col("model") == m) & (pl.col("horizon") == h)).sort("year")
            if not d.height:
                continue
            color, mk = STYLE[m]
            yv = dict(zip(d["year"].to_list(), d["NSE"].to_list()))
            xs = [y for y in full if y in yv]
            ls, lw = ("--", 1.4) if m == "persistence" else ("-", 2.0)
            ax.plot(xs, [yv[y] for y in xs], ls=ls, lw=lw, color=color, marker=mk, ms=6,
                    label=LABELS[m], zorder=3)
            if EXTRA_YEAR in yv:
                ax.plot([EXTRA_YEAR], [yv[EXTRA_YEAR]], ls="none", marker=mk or "o", ms=7,
                        mfc=dl.C_SURF, mec=color, mew=1.8, zorder=3)
            lo_all += list(yv.values())
            if m in (REF, "persistence"):
                continue
            dd = {y: yv[y] - ref[y] for y in yv if y in ref}
            xs2 = [y for y in full if y in dd]
            axd.plot(xs2, [dd[y] for y in xs2], lw=1.8, color=color, marker=mk, ms=5, zorder=3)
            if EXTRA_YEAR in dd:
                axd.plot([EXTRA_YEAR], [dd[EXTRA_YEAR]], ls="none", marker=mk, ms=6,
                         mfc=dl.C_SURF, mec=color, mew=1.6, zorder=3)
        # Dải dao động do số luồng: biên độ lớn nhất (1/2/4 luồng) ở horizon này.
        r = th.filter(pl.col("horizon") == h)["thread_range"].drop_nulls()
        if r.len():
            axd.axhspan(-r.max(), r.max(), color=dl.C_PERS, alpha=0.25, lw=0, zorder=1)
        axd.axhline(0, color=dl.C_LGBM, lw=1.6, zorder=2)
        lo, hi = (min(lo_all), max(lo_all)) if lo_all else (0.0, 1.0)
        ax.set_ylim(max(lo - 0.05, -1.0), min(hi + 0.05, 1.0))
        style(ax, f"NSE by test year, h = {h} d")
        style(axd, f"ΔNSE vs LightGBM, h = {h} d (> 0 = DL better)")
        axd.set_xticks(years, [str(y) if y != EXTRA_YEAR else "2026\n(Jan–Aug)" for y in years],
                       rotation=90)
        ax.annotate("GloFAS regime\nchange 07/2022", (2022, ax.get_ylim()[0]), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=7.5,
                    color=dl.C_INK2)
    from matplotlib.patches import Patch

    hs, ls_ = axes[0, 0].get_legend_handles_labels()
    hs.append(Patch(color=dl.C_PERS, alpha=0.25, lw=0))
    ls_.append("± max NSE range over 1 / 2 / 4 torch threads (folds 2020, 2024)")
    fig.legend(hs, ls_, frameon=False, fontsize=9, loc="upper left", ncol=3,
               bbox_to_anchor=(0.06, 0.955))
    fig.suptitle("Huong River at Kim Long — yearly walk-forward, deep learning vs LightGBM\n"
                 "Expanding window from 2010, 3-day gap before each test year; mean of seeds "
                 "42 / 7 / 2026; DL with 2 torch threads; 2026 (hollow) = Jan–Aug only",
                 x=0.06, y=0.995, ha="left", fontsize=12, color=dl.C_INK)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=dl.C_SURF)
    plt.close(fig)


# ----------------------------------------------------------------- main

def _print_summary(summary: pl.DataFrame) -> None:
    show = ["period", "model", "horizon", "n_folds", "NSE_mean", "NSE_median", "dNSE_mean",
            "dNSE_ci_lo", "dNSE_ci_hi", "wins", "losses", "wilcoxon_p", "NSE_seed_sd_mean"]
    with pl.Config(tbl_rows=200, tbl_cols=30, tbl_width_chars=250, float_precision=3):
        v = summary.filter(pl.col("table") == "vs_lightgbm")
        print(v.select(show))
        print(v.filter(pl.col("horizon") == 1).select(
            "period", "model", "hits", "misses", "false_alarms", "POD", "FAR", "CSI"))
        t = summary.filter(pl.col("table") == "threads")
        if t.height:
            print(t.select("period", "model", "horizon", "NSE_t1", "NSE_t2", "NSE_t4",
                           "NSE_t2_main", "thread_range", "NSE_seed_sd_mean", "dNSE_mean"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", type=int, default=6, help="số tiến trình song song")
    ap.add_argument("--budget", type=int, default=12, help="tổng số luồng được dùng")
    ap.add_argument("--years", type=int, nargs="*", help="chỉ chạy các năm test này")
    ap.add_argument("--no-sens", action="store_true", help="bỏ kiểm độ nhạy số luồng")
    ap.add_argument("--resume", action="store_true", help="dùng lại lượt đã có trong cache")
    ap.add_argument("--quick", action="store_true", help="chạy thử: 2 fold, 1 seed, 3 epoch")
    a = ap.parse_args(argv)

    years = a.years or [*TEST_YEARS, EXTRA_YEAR]
    seeds, override, prefix = SEEDS, None, ""
    if a.quick:
        years, seeds = a.years or list(SENS_YEARS), SEEDS[:1]
        override, prefix = {"max_epochs": 3, "patience": 2}, "quick_"
    jobs = build_jobs(years, seeds, not a.no_sens, str(dl.PANEL), override)
    rows = run_all(jobs, a.jobs, a.budget, a.resume, prefix)

    folds = pl.DataFrame(rows, infer_schema_length=None).sort(
        ["run", "model", "year", "seed", "threads", "horizon"])
    summary = summarize(folds)
    if a.quick:
        _print_summary(summary)
        print("(--quick: không ghi CSV/hình)")
        return 0
    folds.write_csv(OUT_FOLDS)
    summary.write_csv(OUT_SUMMARY)
    plot(folds, summary)
    _print_summary(summary)
    print(f"→ {OUT_FOLDS.relative_to(cfg.ROOT)}\n→ {OUT_SUMMARY.relative_to(cfg.ROOT)}"
          f"\n→ {OUT_FIG.relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
