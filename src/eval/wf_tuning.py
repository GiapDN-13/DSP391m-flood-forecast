"""Tinh chỉnh cấu hình E: bỏ nhóm đặc trưng nghi ngờ, đổi hàm mất mát, Optuna —
đánh giá bằng walk-forward theo NĂM (Report 3).

Bối cảnh (``docs/FINDINGS_SHAP.md``): SHAP cho thấy độ ẩm đất ERA5-Land (SOIL)
tác động ngược chiều vật lý, ``rain_season_cum`` không ủng hộ giả thuyết "hồ đầy",
và mô hình cắt ngọn lũ (``min_child_samples=30`` + L1 trên log1p + ít mẫu cực trị).
Ở đây thử từng thay đổi MỘT, so với E (``ablation_ext.py``, tham số ``lgbm.py``):

    E                        mốc (= E0 của walk_forward_sat, train từ 1998-01-04)
    E-SOIL                   bỏ sm_0_7, sm_7_28, sm_28_100, et0
    E-rain_season_cum        bỏ rain_season_cum
    E-SOIL-rain_season_cum   bỏ cả hai
    E mcs10                  min_child_samples = 10
    E quantile0.9            objective quantile α = 0,9 trên log1p (cận trên)
    E L2                     objective regression (L2) trên log1p
    E optuna                 tham số tốt nhất của Optuna (chọn trên VALID)

Walk-forward: fold năm 2013 … 2025 (``walk_forward_sat.year_fold``), train mở rộng
từ 1998-01-04, gap 3 ngày, ngưỡng mức 1 mỗi fold chỉ từ train
(``walk_forward_sat.fold_threshold``); dự báo = trung bình các seed. Mọi cấu hình
dùng chung tập hàng (đủ cột E) ⇒ ΔNSE ghép cặp theo fold.

Optuna (TPE, seed 42): tối đa NSE trung bình h1–h3 trên VALID 2016-01-01 →
2022-06-30, train 1998-01-04 → 2015-12-28 (gap 3 ngày), 1 seed mỗi trial; trial 0
= đúng tham số E. Sau đó chấm lại ``top_k`` trial tốt nhất bằng 3 seed (vẫn trên
valid) và chọn trial có NSE valid 3 seed cao nhất. Không nhìn test để chọn.
⚠️ Fold 2016–2022 của "E optuna" nằm trong giai đoạn đã dùng để chọn tham số ⇒
lạc quan; số sạch là giai đoạn ``ngoai_valid_optuna`` (2013–2015, 2023–2025).

Test (≥ 2022-07-01, train 1998-01-04 → 2022-06-30, ngưỡng ``risk_levels.csv``)
CHỈ để báo cáo, không dùng chọn cấu hình.

Các bước ghi file trung gian vào ``.cache/wf_tuning`` (mỗi seed một tiến trình, lưu dự
báo từng seed; ``summary`` ghép ensemble các seed đủ cho MỌI cấu hình):

    python -m src.eval.wf_tuning --stage optuna --n-trials 30 --n-jobs 2
    python -m src.eval.wf_tuning --stage wf --seeds 42 --tag s42 --n-jobs 2 --configs E E-SOIL \\
        E-rain_season_cum E-SOIL-rain_season_cum "E mcs10" "E quantile0.9" "E L2" "E optuna"
    (lặp lại với --seeds 7 --tag s7 và --seeds 2026 --tag s2026)
    python -m src.eval.wf_tuning --stage valid --n-jobs 2    # NSE valid split Optuna, 3 seed
    python -m src.eval.wf_tuning --stage test --n-jobs 2     # test ≥ 2022-07-01, 3 seed, chỉ báo cáo
    python -m src.eval.wf_tuning --stage summary             # gộp → CSV + hình, không fit
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from src import config as cfg
from src.eval import metrics
from src.eval.walk_forward_sat import boot_mean_ci, fold_threshold, wilcoxon_p, year_fold
from src.features import risk_levels as rl
from src.models import ablation_ext as ax
from src.models import ablation_hourly as ab
from src.models import ablation_sat as sa
from src.models import lgbm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_FOLDS = cfg.ROOT / "reports" / "wf_tuning_folds.csv"
OUT_SUMMARY = cfg.ROOT / "reports" / "wf_tuning_summary.csv"
OUT_TRIALS = cfg.ROOT / "reports" / "optuna_trials.csv"
OUT_FIG = cfg.FIGURES / "report" / "wf_tuning_en.png"
WORK = cfg.CACHE / "wf_tuning"
RISK = cfg.ROOT / "reports" / "risk_levels.csv"

START = sa.EXT_START                         # 1998-01-04, như nhóm ext của walk_forward_sat
YEARS = tuple(range(2013, 2026))
SEEDS = (42, 7, 2026)
MIN_GAIN = ab.MIN_GAIN                       # 0,01 = dao động giữa seed
RSC = "rain_season_cum"
BASE = "E"
OPTUNA = "E optuna"
VARIANTS: dict[str, tuple[list[str], dict]] = {      # tên → (cột bỏ đi, tham số ghi đè)
    BASE: ([], {}),
    "E-SOIL": (list(ax.SOIL), {}),
    "E-rain_season_cum": ([RSC], {}),
    "E-SOIL-rain_season_cum": ([*ax.SOIL, RSC], {}),
    "E mcs10": ([], {"min_child_samples": 10}),
    "E quantile0.9": ([], {"objective": "quantile", "alpha": 0.9}),
    "E L2": ([], {"objective": "regression"}),
}
OPT_TRAIN = (START, date(2015, 12, 28))      # gap 3 ngày trước valid
OPT_VALID = (date(2016, 1, 1), date.fromisoformat(cfg.VALID_END))
TEST_SPLIT = {"train": (START, date.fromisoformat(cfg.VALID_END)),
              "test": (date.fromisoformat(cfg.GLOFAS_REGIME_BREAK), date(2100, 1, 1))}
TUNED = ("num_leaves", "learning_rate", "n_estimators", "min_child_samples",
         "colsample_bytree", "subsample", "reg_lambda")
PERIODS: dict[str, tuple[int, ...]] = {
    "chinh_2013_2025": YEARS,
    "reanalysis_2013_2021": tuple(range(2013, 2022)),
    "doi_che_do_2022": (2022,),
    "forecast_2023_2025": (2023, 2024, 2025),
    "ngoai_valid_optuna": (2013, 2014, 2015, 2023, 2024, 2025),
}
MAIN = "chinh_2013_2025"
TEST_PERIOD = "test_split_chinh"
VALID_PERIOD = "valid_2016_2022_06"


# ================================================================ dữ liệu, mô hình

def e_features() -> list[str]:
    """Đúng tập cột cấu hình E (= ``ablation_sat.configs('ext')`` mốc E0)."""
    base = ab.base_cols(pl.read_parquet(sa.PANEL))
    return base + ax.SOIL + ax.RESERVOIR_PROXY + ax.CONTEXT


def load() -> tuple[pl.DataFrame, list[str]]:
    return pl.read_parquet(sa.PANEL_EXT).sort("date"), e_features()


def config_features(feats: list[str], drop: list[str]) -> list[str]:
    missing = set(drop) - set(feats)
    if missing:
        raise ValueError(f"Cột cần bỏ không có trong E: {sorted(missing)}")
    return [c for c in feats if c not in set(drop)]


def model_params(overrides: dict, seed: int, n_jobs: int) -> dict:
    """Tham số LightGBM = ``lgbm.PARAMS`` + ghi đè; KHÔNG sửa ``lgbm.PARAMS``."""
    return {**lgbm.PARAMS, **overrides, "random_state": seed, "n_jobs": n_jobs}


def fit_predict(X_tr: np.ndarray, y_tr: np.ndarray, X_ev: np.ndarray, feats: list[str],
                params: dict) -> np.ndarray:
    """LightGBM trên log1p(Q) → expm1, cắt âm. Bọc pandas ngay trước LightGBM
    (LightGBM 4.5 + scikit-learn 1.9 lỗi ``force_all_finite`` với mảng numpy)."""
    import pandas as pd
    from lightgbm import LGBMRegressor

    model = LGBMRegressor(**params)
    model.fit(pd.DataFrame(X_tr, columns=feats), np.log1p(y_tr))
    return np.clip(np.expm1(model.predict(pd.DataFrame(X_ev, columns=feats))), 0, None)


def score(y: np.ndarray, yhat: np.ndarray, flood: np.ndarray, thr1: float) -> dict:
    """Chỉ số một fold; thêm tỷ lệ phủ (dự báo ≥ thực) cho cấu hình cận trên."""
    rep = metrics.regression_report(y, yhat)
    ev = metrics.event_report(y >= thr1, yhat >= thr1)
    pos = y >= thr1
    return {"NSE": rep["NSE"], "NSE_flood": metrics.nse(y[flood], yhat[flood]),
            "KGE": rep["KGE"], "RMSE": rep["RMSE"], "peak_bias": rep["peak_bias"],
            "n_pos1": ev["n_positive"], "hits1": ev["hits"], "misses1": ev["misses"],
            "false_alarms1": ev["false_alarms"], "POD1": ev["POD"], "FAR1": ev["FAR"],
            "CSI1": ev["CSI"], "cover_all": float(np.mean(yhat >= y)) if len(y) else np.nan,
            "n_cover_pos1": int((yhat[pos] >= y[pos]).sum())}


def pooled(hits: int, misses: int, fa: int) -> dict:
    nan = float("nan")
    return {"POD1": hits / (hits + misses) if hits + misses else nan,
            "FAR1": fa / (hits + fa) if hits + fa else nan,
            "CSI1": hits / (hits + misses + fa) if hits + misses + fa else nan}


def configs_for(names: list[str], feats: list[str]) -> dict[str, tuple[list[str], dict]]:
    """Tên cấu hình → (cột, tham số ghi đè). "E optuna" đọc từ ``optuna_trials.csv``."""
    out = {}
    for n in names:
        if n == OPTUNA:
            out[n] = (feats, best_params())
        elif n in VARIANTS:
            drop, ov = VARIANTS[n]
            out[n] = (config_features(feats, drop), ov)
        else:
            raise ValueError(f"Cấu hình lạ: {n}")
    return out


# ================================================================ walk-forward

def run_wf(panel: pl.DataFrame, feats: list[str], cfgs: dict, years: list[int],
           seeds: tuple[int, ...], n_jobs: int, out: Path | None = None,
           preds_out: Path | None = None) -> list[dict]:
    """Walk-forward theo năm. ``preds_out``: lưu dự báo TỪNG seed (parquet) để
    ghép ensemble nhiều seed về sau (chạy mỗi seed một tiến trình)."""
    d = panel["date"].cast(pl.Date)
    X = panel.select(feats).to_numpy().astype(float)
    col = {c: i for i, c in enumerate(feats)}
    q0 = panel["discharge"].to_numpy().astype(float)
    flood_all = d.dt.month().is_in(rl.FLOOD_MONTHS).to_numpy()
    rows: list[dict] = []
    preds: list[pl.DataFrame] = []
    for year in years:
        t0 = time.time()
        fold = year_fold(year, START)
        thr1 = fold_threshold(panel, *fold["train"])
        for h in cfg.HORIZONS:
            m = ab.masks(panel, feats, h, fold)        # chung mọi cấu hình (đều ⊆ E)
            tr, te = m["train"], m["test"]
            y = panel[f"target_h{h}"].to_numpy().astype(float)
            d_tr, d_te = d.filter(pl.Series(tr)), d.filter(pl.Series(te))
            fl = flood_all[te]
            meta = {"fold": year, "horizon": h, "train_start": d_tr.min(), "train_end": d_tr.max(),
                    "test_start": d_te.min(), "test_end": d_te.max(),
                    "gap_days": (d_te.min() - d_tr.max()).days - 1, "n_train": int(tr.sum()),
                    "n_test": int(te.sum()), "n_flood": int(fl.sum()), "thr1": thr1,
                    "seeds": "/".join(map(str, seeds))}
            if BASE in cfgs:
                rows.append({**meta, "config": "persistence", "n_feat": 1,
                             **score(y[te], q0[te], fl, thr1)})
            for name, (fs, ov) in cfgs.items():
                idx = [col[c] for c in fs]
                Xtr, Xte = X[tr][:, idx], X[te][:, idx]
                ps = [fit_predict(Xtr, y[tr], Xte, fs, model_params(ov, s, n_jobs)) for s in seeds]
                rows.append({**meta, "config": name, "n_feat": len(fs),
                             **score(y[te], np.mean(ps, axis=0), fl, thr1),
                             **{f"NSE_seed{s}": metrics.nse(y[te], p) for s, p in zip(seeds, ps)}})
                preds += [pl.DataFrame({"fold": year, "horizon": h, "config": name, "seed": s,
                                        "date": d_te, "y": y[te], "yhat": p, "flood": fl, "thr1": thr1})
                          for s, p in zip(seeds, ps)]
        if out is not None:
            pl.from_dicts(rows, infer_schema_length=None).write_csv(out, float_precision=6)
        if preds_out is not None:
            pl.concat(preds).write_parquet(preds_out)
        r2 = [r for r in rows if r["fold"] == year and r["horizon"] == 2 and r["config"] != "persistence"]
        print(f"  {year} (train→{fold['train'][1]} | ngưỡng {thr1:6.1f}) {time.time() - t0:5.1f}s  h2 NSE "
              + " · ".join(f"{r['config']} {r['NSE']:.3f}" for r in r2), flush=True)
    return rows


# ================================================================ Optuna

def search_space(trial) -> dict:
    """Không gian tìm; chứa đúng giá trị E (trial 0 được xếp hàng bằng E)."""
    return {"num_leaves": trial.suggest_int("num_leaves", 8, 128, log=True),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 150, 1500, step=50),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100, log=True),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 30.0, log=True)}


def e_defaults() -> dict:
    return {k: lgbm.PARAMS[k] for k in TUNED}


def valid_data(panel: pl.DataFrame, feats: list[str]) -> dict[int, tuple]:
    X = panel.select(feats).to_numpy().astype(float)
    out = {}
    for h in cfg.HORIZONS:
        m = ab.masks(panel, feats, h, {"train": OPT_TRAIN, "valid": OPT_VALID})
        y = panel[f"target_h{h}"].to_numpy().astype(float)
        out[h] = (X[m["train"]], y[m["train"]], X[m["valid"]], y[m["valid"]])
    return out


def valid_nse(data: dict, feats: list[str], ov: dict, seeds: tuple[int, ...], n_jobs: int) -> dict[int, float]:
    """NSE valid theo horizon của dự báo trung bình các seed."""
    res = {}
    for h, (Xtr, ytr, Xva, yva) in data.items():
        ps = [fit_predict(Xtr, ytr, Xva, feats, model_params(ov, s, n_jobs)) for s in seeds]
        res[h] = metrics.nse(yva, np.mean(ps, axis=0))
    return res


def run_valid(panel: pl.DataFrame, feats: list[str], cfgs: dict, seeds: tuple[int, ...],
              n_jobs: int) -> list[dict]:
    """NSE trên VALID của split Optuna (train ≤ 2015-12-28 → valid 2016–2022/06) cho
    mọi cấu hình — góc nhìn thứ hai (một lần chia) bên cạnh walk-forward."""
    data = valid_data(panel, feats)
    col = {c: i for i, c in enumerate(feats)}
    rows = []
    for name, (fs, ov) in cfgs.items():
        idx = [col[c] for c in fs]
        sub = {h: (a[:, idx], b, c[:, idx], e) for h, (a, b, c, e) in data.items()}
        r = valid_nse(sub, fs, ov, seeds, n_jobs)
        rows += [{"config": name, "horizon": h, "NSE_valid": v} for h, v in r.items()]
        print(f"  valid {name:<24} " + " ".join(f"h{h} {v:.4f}" for h, v in r.items()), flush=True)
    return rows


def run_optuna(panel: pl.DataFrame, feats: list[str], n_trials: int, top_k: int, n_jobs: int,
               out: Path = OUT_TRIALS) -> pl.DataFrame:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    data = valid_data(panel, feats)
    print(f"Optuna: train {OPT_TRAIN[0]}→{OPT_TRAIN[1]} ({len(data[1][1])} hàng h1) · valid "
          f"{OPT_VALID[0]}→{OPT_VALID[1]} ({len(data[1][3])} hàng) · {n_trials} trial · seed {cfg.SEED}",
          flush=True)

    def objective(trial) -> float:
        t0 = time.time()
        r = valid_nse(data, feats, search_space(trial), (cfg.SEED,), n_jobs)
        for h, v in r.items():
            trial.set_user_attr(f"NSE_h{h}", v)
        trial.set_user_attr("sec", time.time() - t0)
        val = float(np.mean(list(r.values())))
        print(f"  trial {trial.number:2d}  NSE valid TB {val:.4f}  ({time.time() - t0:4.1f}s)  {trial.params}",
              flush=True)
        return val

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=cfg.SEED))
    study.enqueue_trial(e_defaults())
    study.optimize(objective, n_trials=n_trials)

    rows = []
    for t in study.trials:
        rows.append({"trial": t.number, "la_E": t.number == 0, "NSE_valid_mean_seed42": t.value,
                     **{f"NSE_valid_h{h}_seed42": t.user_attrs[f"NSE_h{h}"] for h in cfg.HORIZONS},
                     "sec": t.user_attrs["sec"], **{f"p_{k}": t.params[k] for k in TUNED}})
    tri = pl.from_dicts(rows).sort("NSE_valid_mean_seed42", descending=True)
    cand = tri.filter(~pl.col("la_E")).head(top_k)["trial"].to_list()
    re: dict[int, dict[int, float]] = {}
    for tid in [0, *cand]:                         # chấm lại bằng 3 seed, VẪN trên valid
        ov = {k: study.trials[tid].params[k] for k in TUNED}
        re[tid] = valid_nse(data, feats, ov, SEEDS, n_jobs)
        print(f"  chấm lại trial {tid:2d} (3 seed): NSE valid TB {np.mean(list(re[tid].values())):.4f} "
              + " ".join(f"h{h} {v:.4f}" for h, v in re[tid].items()), flush=True)
    best = max(cand, key=lambda t: np.mean(list(re[t].values())))
    tri = tri.with_columns(
        pl.col("trial").map_elements(lambda t: float(np.mean(list(re[t].values()))) if t in re else None,
                                     return_dtype=pl.Float64).alias("NSE_valid_mean_3seed"),
        *[pl.col("trial").map_elements(lambda t, h=h: re[t][h] if t in re else None,
                                       return_dtype=pl.Float64).alias(f"NSE_valid_h{h}_3seed")
          for h in cfg.HORIZONS],
        (pl.col("trial") == best).alias("chon"))
    tri.write_csv(out, float_precision=6)
    print(f"→ {out}  · chọn trial {best}", flush=True)
    return tri


def best_params(path: Path = OUT_TRIALS) -> dict:
    if not path.exists():
        raise SystemExit(f"Chưa có {path.name} — chạy `--stage optuna` trước.")
    r = pl.read_csv(path).filter(pl.col("chon")).row(0, named=True)
    return {k: (int(r[f"p_{k}"]) if k in ("num_leaves", "n_estimators", "min_child_samples")
                else float(r[f"p_{k}"])) for k in TUNED}


# ================================================================ test (chỉ báo cáo)

def run_test(panel: pl.DataFrame, feats: list[str], cfgs: dict, seeds: tuple[int, ...],
             n_jobs: int) -> list[dict]:
    thr1 = float(pl.read_csv(RISK).filter(pl.col("muc") == "nguy_co_1")["nguong_m3s"].item())
    d = panel["date"].cast(pl.Date)
    X = panel.select(feats).to_numpy().astype(float)
    col = {c: i for i, c in enumerate(feats)}
    q0 = panel["discharge"].to_numpy().astype(float)
    flood_all = d.dt.month().is_in(rl.FLOOD_MONTHS).to_numpy()
    rows = []
    for h in cfg.HORIZONS:
        m = ab.masks(panel, feats, h, TEST_SPLIT)
        tr, te = m["train"], m["test"]
        y = panel[f"target_h{h}"].to_numpy().astype(float)
        fl = flood_all[te]
        meta = {"horizon": h, "n_train": int(tr.sum()), "n_test": int(te.sum()), "thr1": thr1,
                "train_start": d.filter(pl.Series(tr)).min(), "test_end": d.filter(pl.Series(te)).max()}
        rows.append({**meta, "config": "persistence", **score(y[te], q0[te], fl, thr1)})
        for name, (fs, ov) in cfgs.items():
            idx = [col[c] for c in fs]
            ps = [fit_predict(X[tr][:, idx], y[tr], X[te][:, idx], fs, model_params(ov, s, n_jobs))
                  for s in seeds]
            rows.append({**meta, "config": name, **score(y[te], np.mean(ps, axis=0), fl, thr1),
                         **{f"NSE_seed{s}": metrics.nse(y[te], p) for s, p in zip(seeds, ps)}})
        print(f"  test h{h}: " + " · ".join(f"{r['config']} {r['NSE']:.3f}" for r in rows
                                            if r["horizon"] == h), flush=True)
    return rows


# ================================================================ tổng hợp

def add_deltas(folds: pl.DataFrame) -> pl.DataFrame:
    """ΔNSE, ΔNSE mùa lũ, Δpeak_bias và ΔNSE từng seed so với E cùng fold × horizon."""
    seeds = [c.removeprefix("NSE_seed") for c in folds.columns if c.startswith("NSE_seed")]
    keys = [k for k in ("fold", "horizon") if k in folds.columns]
    b = folds.filter(pl.col("config") == BASE).select(
        *keys, pl.col("NSE").alias("_b"), pl.col("NSE_flood").alias("_bf"),
        pl.col("peak_bias").alias("_bp"), *[pl.col(f"NSE_seed{s}").alias(f"_b{s}") for s in seeds])
    x = folds.join(b, on=keys, how="left")
    dn = [(pl.col("NSE") - pl.col("_b")).alias("dNSE"),
          (pl.col("NSE_flood") - pl.col("_bf")).alias("dNSE_flood"),
          (pl.col("peak_bias") - pl.col("_bp")).alias("d_peak_bias"),
          *[(pl.col(f"NSE_seed{s}") - pl.col(f"_b{s}")).alias(f"dNSE_seed{s}") for s in seeds]]
    not_ref = ~pl.col("config").is_in([BASE, "persistence"])
    return (x.with_columns([pl.when(not_ref).then(e).otherwise(None).alias(e.meta.output_name())
                            for e in dn])
             .drop("_b", "_bf", "_bp", *[f"_b{s}" for s in seeds]))


def common_seeds(preds: pl.DataFrame, years=YEARS) -> list[int]:
    """Seed có ĐỦ mọi fold × horizon của MỌI cấu hình (để ensemble công bằng)."""
    need = len(years) * len(cfg.HORIZONS)
    full = (preds.filter(pl.col("fold").is_in(list(years)))
                 .group_by("config", "seed").agg(pl.struct("fold", "horizon").n_unique().alias("n"))
                 .filter(pl.col("n") == need))
    n_cfg = preds["config"].n_unique()
    ok = full.group_by("seed").agg(pl.len().alias("k")).filter(pl.col("k") == n_cfg)
    return sorted(ok["seed"].to_list())


def folds_from_preds(preds: pl.DataFrame, seeds: list[int]) -> pl.DataFrame:
    """Chỉ số từng fold của dự báo trung bình ``seeds`` (ghép từ các lần chạy từng seed)."""
    rows = []
    x = preds.filter(pl.col("seed").is_in(seeds)).sort("fold", "horizon", "config", "seed", "date")
    for (fold, h, c), g in x.group_by(["fold", "horizon", "config"], maintain_order=True):
        by = {s: g.filter(pl.col("seed") == s) for s in seeds}
        if any(v.is_empty() for v in by.values()):
            continue
        g0 = by[seeds[0]]
        y, fl, thr1 = g0["y"].to_numpy(), g0["flood"].to_numpy(), float(g0["thr1"][0])
        ps = [by[s]["yhat"].to_numpy() for s in seeds]
        rows.append({"fold": fold, "horizon": h, "config": c, "seeds": "/".join(map(str, seeds)),
                     **score(y, np.mean(ps, axis=0), fl, thr1),
                     **{f"NSE_seed{s}": metrics.nse(y, p) for s, p in zip(seeds, ps)}})
    return pl.from_dicts(rows, infer_schema_length=None)


def _f(v) -> float:
    return float(v) if v is not None else float("nan")


def summarize(folds: pl.DataFrame, test: pl.DataFrame | None = None,
              valid: pl.DataFrame | None = None) -> pl.DataFrame:
    rows = []
    seeds = [c.removeprefix("dNSE_seed") for c in folds.columns if c.startswith("dNSE_seed")]
    for c, h in folds.select("config", "horizon").unique(maintain_order=True).iter_rows():
        x = folds.filter((pl.col("config") == c) & (pl.col("horizon") == h)).sort("fold")
        for per, ys in PERIODS.items():
            s = x.filter(pl.col("fold").is_in(list(ys)))
            if s.is_empty():
                continue
            hits, miss, fa = (int(s[k].sum()) for k in ("hits1", "misses1", "false_alarms1"))
            ncov = int(s["n_cover_pos1"].sum())
            r = {"config": c, "horizon": h, "period": per, "n_folds": s.height,
                 "NSE_mean": s["NSE"].mean(), "NSE_median": s["NSE"].median(),
                 "NSE_flood_mean": s["NSE_flood"].mean(), "peak_bias_mean": s["peak_bias"].mean(),
                 "n_pos1": hits + miss, "hits1": hits, "misses1": miss, "false_alarms1": fa,
                 **pooled(hits, miss, fa), "cover_all_mean": s["cover_all"].mean(),
                 "cover_pos1": ncov / (hits + miss) if hits + miss else None}
            if s["dNSE"].null_count() < s.height:
                dn = s["dNSE"].cast(pl.Float64).to_numpy()
                df = s["dNSE_flood"].cast(pl.Float64).to_numpy()
                lo, hi = boot_mean_ci(dn)
                r.update({"dNSE_mean": float(np.mean(dn)), "dNSE_median": float(np.median(dn)),
                          "dNSE_ci_lo": lo, "dNSE_ci_hi": hi,
                          "n_win": int((dn > 0).sum()), "n_loss": int((dn < 0).sum()),
                          "n_win_001": int((dn >= MIN_GAIN).sum()), "n_loss_001": int((dn <= -MIN_GAIN).sum()),
                          "p_wilcoxon": wilcoxon_p(dn), "p_wilcoxon_gt": wilcoxon_p(dn, "greater"),
                          "dNSE_flood_mean": float(np.nanmean(df)) if np.isfinite(df).any() else None,
                          "d_peak_bias_mean": s["d_peak_bias"].mean(),
                          **{f"dNSE_mean_seed{sd}": s[f"dNSE_seed{sd}"].mean() for sd in seeds}})
            rows.append(r)
    if valid is not None and valid.height:
        e = dict(valid.filter(pl.col("config") == BASE).select("horizon", "NSE_valid").iter_rows())
        for r in valid.iter_rows(named=True):
            rows.append({"config": r["config"], "horizon": r["horizon"], "period": VALID_PERIOD,
                         "n_folds": 1, "NSE_mean": r["NSE_valid"], "NSE_median": r["NSE_valid"],
                         "dNSE_mean": None if r["config"] == BASE else r["NSE_valid"] - e[r["horizon"]]})
    if test is not None and test.height:
        for r in test.iter_rows(named=True):
            hits, miss, fa = r["hits1"], r["misses1"], r["false_alarms1"]
            rows.append({"config": r["config"], "horizon": r["horizon"], "period": TEST_PERIOD,
                         "n_folds": 1, "NSE_mean": r["NSE"], "NSE_median": r["NSE"],
                         "NSE_flood_mean": r["NSE_flood"], "peak_bias_mean": r["peak_bias"],
                         "n_pos1": hits + miss, "hits1": hits, "misses1": miss, "false_alarms1": fa,
                         **pooled(hits, miss, fa), "cover_all_mean": r["cover_all"],
                         "cover_pos1": r["n_cover_pos1"] / (hits + miss) if hits + miss else None,
                         "dNSE_mean": r.get("dNSE"), "dNSE_flood_mean": r.get("dNSE_flood"),
                         "d_peak_bias_mean": r.get("d_peak_bias")})
    return pl.from_dicts(rows, infer_schema_length=None)


def _fmt(v, f="+.3f") -> str:
    return "  —  " if v is None or not np.isfinite(v) else format(v, f)


def report(summ: pl.DataFrame) -> None:
    for per in (MAIN, "ngoai_valid_optuna", "forecast_2023_2025", VALID_PERIOD, TEST_PERIOD):
        x = summ.filter((pl.col("period") == per) & (pl.col("config") != "persistence"))
        if x.is_empty():
            continue
        print(f"\n--- {per}: NSE TB · ΔNSE TB [CI95 bootstrap fold] · thắng/thua (|Δ|≥0,01) · "
              f"p Wilcoxon · peak_bias TB · phủ ngày ≥ ngưỡng")
        for r in x.sort("horizon", maintain_order=True).iter_rows(named=True):
            line = (f"  h={r['horizon']} {r['config']:<24} NSE {r['NSE_mean']:.3f}  "
                    f"pb {_fmt(r['peak_bias_mean'])}  phủ+ {_fmt(r['cover_pos1'], '.2f')}")
            if r.get("dNSE_mean") is not None and np.isfinite(_f(r["dNSE_mean"])):
                line += f"  Δ {_fmt(r['dNSE_mean'])}"
                if r.get("n_win") is not None:
                    line += (f" [{_fmt(r['dNSE_ci_lo'])}, {_fmt(r['dNSE_ci_hi'])}] {r['n_win']}/{r['n_loss']}"
                             f" ({r['n_win_001']}/{r['n_loss_001']}) p {_fmt(r['p_wilcoxon'], '.3f')}")
            print(line)
        if per == VALID_PERIOD:
            continue
        ev = x.filter(pl.col("horizon") == 1)
        print(f"  mức 1, h=1, gộp sự kiện ({per}):")
        for r in ev.iter_rows(named=True):
            print(f"    {r['config']:<24} n+ {r['n_pos1']:3d} hits {r['hits1']:3d} miss {r['misses1']:3d} "
                  f"FA {r['false_alarms1']:3d}  POD {_fmt(r['POD1'], '.3f')} FAR {_fmt(r['FAR1'], '.3f')} "
                  f"CSI {_fmt(r['CSI1'], '.3f')}")


# ================================================================ hình

C_INK, C_INK2, C_GRID, C_SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
C_UP, C_DOWN, C_NEU = "#2a78d6", "#eb6834", "#8a8984"


def plot(folds: pl.DataFrame, summ: pl.DataFrame, out: Path = OUT_FIG) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = [c for c in [*VARIANTS, OPTUNA] if c != BASE and c in folds["config"].unique().to_list()]
    fig, axes = plt.subplots(1, 3, figsize=(15, 0.55 * len(names) + 2.2), sharey=True,
                             facecolor=C_SURF)
    rng = np.random.default_rng(0)
    yr = pl.col("fold").is_in(list(YEARS))
    # Trục x theo các biến thể "gần E"; quantile lệch rất xa ⇒ điểm ngoài trục bị kẹp ở mép
    # (mũi tên rỗng) và nhãn chữ vẫn ghi giá trị thật.
    near = folds.filter(yr & pl.col("config").is_in([c for c in names if c != "E quantile0.9"]))
    for j, h in enumerate(cfg.HORIZONS):
        dv = near.filter(pl.col("horizon") == h)["dNSE"].drop_nulls().to_numpy()
        dv = dv if len(dv) else np.array([0.0])
        lo, hi = min(-0.04, float(dv.min())) - 0.01, max(0.04, float(dv.max())) + 0.01
        ax = axes[j]
        ax.set_facecolor(C_SURF)
        ax.axvline(0, color=C_INK, lw=1.6, zorder=2)
        for i, c in enumerate(names):
            yy = len(names) - 1 - i
            f = folds.filter((pl.col("config") == c) & (pl.col("horizon") == h) & yr)["dNSE"].to_numpy()
            jit = yy + rng.uniform(-0.18, 0.18, len(f))
            ins = (f >= lo) & (f <= hi)
            ax.scatter(f[ins], jit[ins], s=14, color=C_NEU, alpha=0.55, lw=0, zorder=3)
            for side, m, mk in ((lo, f < lo, "<"), (hi, f > hi, ">")):
                if m.any():
                    ax.scatter(np.full(m.sum(), side), jit[m], s=22, marker=mk, facecolor="none",
                               edgecolor=C_NEU, lw=1, zorder=3, clip_on=False)
            s = summ.filter((pl.col("config") == c) & (pl.col("horizon") == h)
                            & (pl.col("period") == MAIN)).row(0, named=True)
            col = C_UP if s["dNSE_ci_lo"] > 0 else C_DOWN if s["dNSE_ci_hi"] < 0 else C_INK2
            mu, cl, ch = (float(np.clip(v, lo, hi)) for v in (s["dNSE_mean"], s["dNSE_ci_lo"], s["dNSE_ci_hi"]))
            ax.errorbar(mu, yy, xerr=[[mu - cl], [ch - mu]], fmt="D" if mu == s["dNSE_mean"] else "<" if mu == lo else ">",
                        ms=7, color=col, ecolor=col, elinewidth=2.2, capsize=0, zorder=4)
            p = s["p_wilcoxon"]
            ax.annotate(f"{s['dNSE_mean']:+.3f}  {s['n_win']}W/{s['n_loss']}L  "
                        + ("p<0.001" if p < 0.001 else f"p={p:.3f}"),
                        (1.0, yy), xycoords=("axes fraction", "data"), xytext=(-4, 9),
                        textcoords="offset points", ha="right", fontsize=7.6, color=C_INK2)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(list(reversed(names)), fontsize=9, color=C_INK)
        ax.set_title(f"h = {h} d", loc="left", fontsize=10.5, color=C_INK)
        ax.grid(axis="x", color=C_GRID, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(colors=C_INK2, labelsize=9)
        ax.set_xlabel("ΔNSE vs E (test year)", color=C_INK2)
        ax.set_ylim(-0.6, len(names) - 0.25)
        ax.set_xlim(lo, hi)
    fig.suptitle("Walk-forward 2013–2025 (13 test years, expanding train from 1998, 3-day gap): "
                 "variants of LightGBM config E", x=0.01, y=0.995, ha="left", fontsize=12, color=C_INK)
    fig.text(0.01, 0.945, "Grey dots: ΔNSE per test year. Diamond + bar: mean and 95% bootstrap CI over "
             "years (blue = CI > 0, orange = CI < 0); hollow arrows = off-scale, clipped at the edge (text "
             "gives true mean). 'E optuna' was tuned on 2016–2022/06 data, so its 2016–2022 folds are optimistic.", fontsize=8.3, color=C_INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.935))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=C_SURF)
    plt.close(fig)
    return out


# ================================================================ main

META = ["fold", "horizon", "train_start", "train_end", "test_start", "test_end", "gap_days",
        "n_train", "n_test", "n_flood", "thr1"]


def stage_summary(work: Path, seeds: list[int] | None = None) -> int:
    """Gộp các lần chạy. Có ``preds_*.parquet`` ⇒ dựng lại ensemble từ dự báo từng
    seed (mặc định: mọi seed đủ fold cho MỌI cấu hình); không có ⇒ dùng CSV."""
    parts = sorted(work.glob("folds_*.csv"))
    if not parts:
        raise SystemExit(f"Không có {work}/folds_*.csv — chạy `--stage wf` trước.")
    folds = pl.concat([pl.read_csv(p, infer_schema_length=None, try_parse_dates=True) for p in parts],
                      how="diagonal_relaxed")
    folds = folds.unique(subset=["fold", "horizon", "config"], keep="first", maintain_order=True)
    pp = sorted(work.glob("preds_*.parquet"))
    if pp:
        preds = pl.concat([pl.read_parquet(p) for p in pp], how="diagonal_relaxed")
        preds = preds.unique(subset=["fold", "horizon", "config", "seed", "date"], keep="first")
        seeds = seeds or common_seeds(preds)
        if not seeds:
            raise SystemExit("Không có seed nào đủ mọi fold cho mọi cấu hình.")
        print(f"Ensemble từ dự báo từng seed: seed {seeds}; cấu hình {sorted(preds['config'].unique())}")
        meta = folds.select(META).unique(subset=["fold", "horizon"], keep="first")
        nfeat = folds.select("config", "n_feat").unique(subset="config", keep="first")
        ens = (folds_from_preds(preds, seeds).join(meta, on=["fold", "horizon"], how="left")
                                             .join(nfeat, on="config", how="left"))
        pers = folds.filter(pl.col("config") == "persistence").drop(
            [c for c in folds.columns if c.startswith("NSE_seed")])
        folds = pl.concat([pers, ens], how="diagonal_relaxed")
    folds = add_deltas(folds).sort("fold", "horizon")
    folds.write_csv(OUT_FOLDS, float_precision=6)
    test = None
    if (work / "test.csv").exists():
        test = add_deltas(pl.read_csv(work / "test.csv", infer_schema_length=None, try_parse_dates=True))
    valid = pl.read_csv(work / "valid.csv") if (work / "valid.csv").exists() else None
    summ = summarize(folds, test, valid)
    summ.write_csv(OUT_SUMMARY, float_precision=6)
    report(summ)
    print(f"\n→ {OUT_FOLDS} ({folds.height} dòng)\n→ {OUT_SUMMARY} ({summ.height} dòng)")
    print(f"→ {plot(folds, summ)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", choices=("wf", "optuna", "valid", "test", "summary"), required=True)
    ap.add_argument("--configs", nargs="+", default=list(VARIANTS))
    ap.add_argument("--tag", default="variants", help="tên file trung gian folds_<tag>.csv")
    ap.add_argument("--years", nargs="+", type=int, default=list(YEARS))
    ap.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    ap.add_argument("--n-trials", type=int, default=30)
    ap.add_argument("--top-k", type=int, default=3, help="số trial chấm lại 3 seed trên valid")
    ap.add_argument("--n-jobs", type=int, default=4, help="số luồng LightGBM mỗi lần fit")
    ap.add_argument("--work-dir", default=str(WORK))
    a = ap.parse_args(argv)
    work = Path(a.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    if a.stage == "summary":
        return stage_summary(work, a.seeds if a.seeds != list(SEEDS) else None)
    panel, feats = load()
    if a.stage == "optuna":
        run_optuna(panel, feats, a.n_trials, a.top_k, a.n_jobs)
    elif a.stage == "wf":
        cfgs = configs_for(a.configs, feats)
        print(f"Walk-forward fold {a.years}; seed {a.seeds}; n_jobs {a.n_jobs}; "
              + ", ".join(f"{k} ({len(f)} cột, {ov})" for k, (f, ov) in cfgs.items()), flush=True)
        run_wf(panel, feats, cfgs, a.years, tuple(a.seeds), a.n_jobs, work / f"folds_{a.tag}.csv",
               work / f"preds_{a.tag}.parquet")
        print(f"→ {work / f'folds_{a.tag}.csv'}")
    elif a.stage == "valid":
        names = [*VARIANTS, *([OPTUNA] if OUT_TRIALS.exists() else [])]
        rows = run_valid(panel, feats, configs_for(names, feats), tuple(a.seeds), a.n_jobs)
        pl.from_dicts(rows).write_csv(work / "valid.csv", float_precision=6)
        print(f"→ {work / 'valid.csv'}")
    else:
        names = [*VARIANTS, *([OPTUNA] if OUT_TRIALS.exists() else [])]
        rows = run_test(panel, feats, configs_for(names, feats), tuple(a.seeds), a.n_jobs)
        pl.from_dicts(rows, infer_schema_length=None).write_csv(work / "test.csv", float_precision=6)
        print(f"→ {work / 'test.csv'}")
    print(f"Thời gian bước {a.stage}: {(time.time() - t0) / 60:.1f} phút", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
