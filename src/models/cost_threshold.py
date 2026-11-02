"""Ngưỡng cảnh báo theo CHI PHÍ cho bộ phân loại mức nguy cơ (FR-M5).

``classifier.py`` báo động khi xác suất ≥ 0,5. Con số 0,5 không gắn với cái giá
thật của hai loại sai. ``docs/RESEARCH_DESIGN.md`` §3.3 chốt tỉ lệ chi phí bỏ sót
: báo động nhầm = 10 : 1 (``cfg.COST_RATIO_MISS_TO_FALSE_ALARM``), độ nhạy 5 : 1 và
20 : 1. Ở đây ngưỡng xác suất được chọn để tối thiểu hoá

    C = R · misses + 1 · false_alarms          (R = 5, 10, 20)

và **không bao giờ chọn trên tập test**:

* **Một lần chia** (test ≥ 2022-07-01, như ``classifier.py``): mô hình train
  (≤ 2015) dự báo valid (2016 → 06/2022) ⇒ chọn ngưỡng trên valid; mô hình
  train + valid (đúng mô hình của ``classifier.py``) dự báo test ⇒ áp ngưỡng đã
  chọn. Chênh hiệu chỉnh xác suất giữa hai mô hình là có — ghi ở phần kết luận.
* **Walk-forward theo năm** (fold ``walk_forward_sat.year_fold``, gap 3 ngày):
  mỗi năm Y có một mô hình train tới 28/12/(Y−1) dự báo cả năm Y (dự báo
  out-of-fold, OOF). Ngưỡng dùng cho năm Y chọn trên OOF GỘP của các năm < Y,
  chỉ những hàng ≤ 28/12/(Y−1) (nhãn t+3 không chạm năm Y). Bể OOF có < 10 ngày
  dương ⇒ giữ 0,5. Tổng hợp chính 2013–2025 (13 fold); hits/misses/FA cộng
  qua fold, so từng fold bằng Wilcoxon + bootstrap theo fold.

Hai bộ đặc trưng: ``R2`` = ``classifier.feature_cols`` trên panel từ 2010 (66
cột); ``E`` = cấu hình E của ``ablation_ext`` (R2 + đất + đại diện hồ + bão/khí
áp/ENSO, 88 cột, panel mở rộng từ 1997). Nhãn CHUNG cho hai bộ: một lần chia dùng
ngưỡng lưu lượng của ``classifier.py`` (806 / 1 275 m³/s, train + valid panel R2);
walk-forward dùng ngưỡng mỗi fold = phân vị mùa lũ của lưu lượng từ 1997 tới hết
cửa sổ train (``fold_threshold`` trên panel mở rộng — lưu lượng hai panel trùng
khớp tuyệt đối). Mức 3 (≤ 9 ngày dương/năm tốt nhất) không làm.

Thêm hai mốc không cần chọn gì: **persistence** (báo động khi Q hôm nay đã ≥
ngưỡng) và **ngưỡng lý thuyết** w / (w + R): mô hình học với
``scale_pos_weight = w`` nên odds xác suất của nó ≈ w × odds thật; quy tắc
Bayes "báo khi p_thật > 1/(1+R)" thành "p_mô_hình > w/(w+R)" — w ≈ 52–69 (mức 1),
110–166 (mức 2) nên ngưỡng này 0,72–0,97 (R = 10, mức 1: ≈ 0,84–0,87). Chạy thật cho thấy giả định "odds × w"
KHÔNG đúng ngoài mẫu: ngưỡng lý thuyết đắt hơn cả 0,5, ngưỡng tối ưu thực nghiệm
lại < 0,05 (xác suất của LightGBM xếp hạng được nhưng không hiệu chỉnh — FR-M6).

Đối chứng tuỳ chọn ``--sets B``: đặc trưng R2 nhưng học từ 1997 (= cấu hình B của
``ablation_ext``) — tách phần lợi của E do thêm năm học với phần do thêm đặc trưng.

**Hiệu chỉnh isotonic (FR-M6, ``--calibrate``):** với năm test Y, ``IsotonicRegression``
(clip, [0, 1]) học trên ĐÚNG bể OOF dùng chọn ngưỡng (năm < Y, ≤ 28/12/(Y−1),
``pool_mask``) rồi biến đổi xác suất năm Y; ngưỡng chi phí chọn lại trên xác suất
đã hiệu chỉnh của bể (cùng ``choose_threshold``). Bể < 10 ngày dương ⇒ không hiệu
chỉnh (giữ xác suất thô, ngưỡng 0,5) như nhánh thô. So cặp từng fold với nhánh thô
(``chi_phi``): chi phí, Brier, log-loss; thêm ``bayes_iso`` = ngưỡng Bayes 1/(1+R)
trên xác suất đã hiệu chỉnh (không chọn gì). Ghi ``reports/cost_calibration.csv``
(+ ``_bins.csv``) và reliability diagram — KHÔNG ghi đè ``cost_threshold.csv``.

    python -m src.models.cost_threshold                 # ~8–20 phút, 4 luồng (R2 + E, seed 42)
    python -m src.models.cost_threshold --seeds 42 7 2026 --out <csv> --fig <png>   # độ nhạy seed
    python -m src.models.cost_threshold --sets B --out <csv> --fig <png>            # đối chứng B
    python -m src.models.cost_threshold --sets R2 --years 2013 2014 --out <csv> --fig <png>  # thử
    python -m src.models.cost_threshold --calibrate --oof-out <parquet>     # FR-M6 (~12 phút)
    python -m src.models.cost_threshold --calibrate --oof-in <parquet>      # FR-M6 từ OOF đã lưu
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
from src.eval.walk_forward_sat import boot_mean_ci, fold_threshold, wilcoxon_p, year_fold
from src.features import risk_levels as rl
from src.models import ablation_ext as ax
from src.models import ablation_hourly as ab
from src.models import ablation_sat as sa
from src.models import classifier as clf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = cfg.DATA_PROCESSED / "daily_panel.parquet"
PANEL_EXT = cfg.DATA_PROCESSED / "daily_panel_ext.parquet"
OUT = cfg.ROOT / "reports" / "cost_threshold.csv"
OUT_FIG = cfg.FIGURES / "report" / "cost_threshold_en.png"

RATIOS = (5, cfg.COST_RATIO_MISS_TO_FALSE_ALARM, 20)
DEFAULT_P = 0.5
# Lưới ngưỡng: thưa-log ở đầu thấp (xác suất LightGBM có trọng số lớp dồn về 0
# và 1 trên dữ liệu mới), bước 0,01 ở giữa.
GRID = np.unique(np.round(np.r_[np.geomspace(1e-4, 5e-3, 7), np.arange(0.01, 0.995, 0.01),
                                0.995, 0.999], 5))
MIN_POOL_POS = 10        # bể chọn ngưỡng ít hơn số này ngày dương ⇒ giữ 0,5
MIN_TRAIN_POS = 10       # như classifier.py: < 10 ngày dương trong train ⇒ không fit
LEVELS = {1: "nguy_co_1", 2: "nguy_co_2"}
SEEDS = (cfg.SEED,)      # classifier.py dùng 1 seed
WF_YEARS = tuple(range(2013, 2026))   # tổng hợp chính (giống walk_forward_sat)
WF_FIRST = {"R2": 2011, "B": 1999, "E": 1999}    # năm OOF đầu tiên (bể chọn ngưỡng cho các fold sau)
THR_START = date(1997, 1, 1)          # lưu lượng dùng tính ngưỡng fold: từ đầu panel mở rộng
METHODS = ("p=0.5", "chi_phi", "ly_thuyet", "persistence")
# FR-M6 — hiệu chỉnh isotonic
OUT_CAL = cfg.ROOT / "reports" / "cost_calibration.csv"
OUT_FIG_CAL = cfg.FIGURES / "report" / "cost_reliability_en.png"
CAL_METHODS = ("p=0.5", "chi_phi", "chi_phi_iso", "bayes_iso")
N_BINS = 10              # reliability diagram: 10 khoảng đều trên [0, 1]
LOGLOSS_EPS = 1e-4       # kẹp xác suất khi tính log-loss (isotonic cho được đúng 0 / 1)


# ================================================================ chi phí, chọn ngưỡng

def contingency_at(y: np.ndarray, p: np.ndarray, t: float) -> tuple[int, int, int, int]:
    """(hits, misses, false_alarms, correct_negatives) khi báo động lúc p ≥ t."""
    y = np.asarray(y, bool)
    a = np.asarray(p, float) >= t
    return (int(np.sum(y & a)), int(np.sum(y & ~a)), int(np.sum(~y & a)), int(np.sum(~y & ~a)))


def expected_cost(y: np.ndarray, p: np.ndarray, t: float, ratio: float) -> float:
    _, miss, fa, _ = contingency_at(y, p, t)
    return ratio * miss + fa


def cost_curve(y: np.ndarray, p: np.ndarray, ratio: float, grid: np.ndarray = GRID) -> np.ndarray:
    """C(t) = R·misses(t) + FA(t) cho mọi t trong lưới (vector hoá)."""
    y = np.asarray(y, bool)
    a = np.asarray(p, float)[None, :] >= np.asarray(grid, float)[:, None]
    miss = np.sum(y[None, :] & ~a, axis=1)
    fa = np.sum(~y[None, :] & a, axis=1)
    return ratio * miss + fa


def choose_threshold(y: np.ndarray, p: np.ndarray, ratio: float, grid: np.ndarray = GRID,
                     default: float = DEFAULT_P, min_pos: int = MIN_POOL_POS) -> tuple[float, bool]:
    """Ngưỡng tối thiểu chi phí trên (y, p) — ``(ngưỡng, đã_chọn)``.

    Hoà chi phí ⇒ lấy ngưỡng gần ``default`` nhất (không đổi nếu không có lợi).
    Ít hơn ``min_pos`` ngày dương ⇒ trả ``default`` (``đã_chọn = False``).
    """
    y = np.asarray(y, bool)
    if int(y.sum()) < min_pos:
        return float(default), False
    c = cost_curve(y, p, ratio, grid)
    cand = np.asarray(grid, float)[c == c.min()]
    return float(cand[np.argmin(np.abs(cand - default))]), True


def theory_threshold(w: float, ratio: float) -> float:
    """Ngưỡng Bayes trên xác suất của mô hình học với ``scale_pos_weight = w``."""
    return float(w / (w + ratio))


def pool_mask(years: np.ndarray, dates: np.ndarray, test_year: int, cutoff: date) -> np.ndarray:
    """Hàng OOF được dùng chọn ngưỡng cho năm ``test_year``: năm trước đó và ngày
    ≤ ``cutoff`` (cuối cửa sổ train của fold) — không bao giờ chạm năm test."""
    return (np.asarray(years) < test_year) & (np.asarray(dates) <= np.datetime64(cutoff))


def event_row(y: np.ndarray, pred: np.ndarray, ratio: float) -> dict:
    y, pred = np.asarray(y, bool), np.asarray(pred, bool)
    h, m, f = int(np.sum(y & pred)), int(np.sum(y & ~pred)), int(np.sum(~y & pred))
    n_pos = h + m
    return {"n": int(len(y)), "n_pos": n_pos, "hits": h, "misses": m, "false_alarms": f,
            "n_alarm": h + f, **_pfc(h, m, f), "cost": ratio * m + f,
            "cost_never": ratio * n_pos}


def _pfc(h: int, m: int, f: int) -> dict:
    nan = float("nan")
    return {"POD": h / (h + m) if h + m else nan, "FAR": f / (h + f) if h + f else nan,
            "CSI": h / (h + m + f) if h + m + f else nan}


# ================================================================ dữ liệu, mô hình

def load_set(name: str) -> tuple[pl.DataFrame, list[str], date]:
    """(panel, đặc trưng, ngày đầu) của bộ ``R2``, ``E`` hoặc đối chứng ``B``."""
    p2 = pl.read_parquet(PANEL)
    base = ab.base_cols(p2)                  # = classifier.feature_cols (66 cột)
    if name == "R2":
        p = p2
    elif name == "B":        # đối chứng: đặc trưng R2 nhưng học từ 1997 (= cấu hình B)
        p = pl.read_parquet(PANEL_EXT)
    elif name == "E":
        p = pl.read_parquet(PANEL_EXT)
        base = base + ax.SOIL + ax.RESERVOIR_PROXY + ax.CONTEXT
    else:
        raise ValueError(name)
    p = p.with_columns(pl.col("date").cast(pl.Date)).sort("date")
    return p, base, p["date"].min()


def fit_proba(X: np.ndarray, feats: list[str], y: np.ndarray, tr: np.ndarray, ev: np.ndarray,
              seeds=SEEDS, n_jobs: int = 4) -> tuple[np.ndarray, float]:
    """LGBMClassifier tham số ``classifier.py`` (scale_pos_weight = n_âm/n_dương);
    trung bình xác suất qua ``seeds``. Bọc pandas NGAY trước LightGBM (LightGBM 4.5
    + sklearn 1.9 lỗi ``force_all_finite`` với mảng numpy)."""
    import pandas as pd
    from lightgbm import LGBMClassifier

    n_pos = int(y[tr].sum())
    w = float((int(tr.sum()) - n_pos) / max(n_pos, 1))
    xtr = pd.DataFrame(X[tr], columns=feats)
    xev = pd.DataFrame(X[ev], columns=feats)
    ytr = pd.Series(y[tr].astype("int8"))
    ps = []
    for s in seeds:
        m = LGBMClassifier(**{**clf.PARAMS, "random_state": s, "n_jobs": n_jobs},
                           scale_pos_weight=w)
        m.fit(xtr, ytr)
        ps.append(m.predict_proba(xev)[:, 1])
    return np.mean(ps, axis=0), w


def _target(panel: pl.DataFrame, h: int) -> np.ndarray:
    return panel[f"target_h{h}"].cast(pl.Float64).fill_null(np.nan).to_numpy()


def _methods(y, p, q0, thr_q, chosen: dict, w: float) -> list[tuple[str, int, float, np.ndarray]]:
    """(phương pháp, R, ngưỡng xác suất, dự báo nhị phân) cho mọi R."""
    out = []
    for r in RATIOS:
        out.append(("p=0.5", r, DEFAULT_P, p >= DEFAULT_P))
        out.append(("chi_phi", r, chosen[r], p >= chosen[r]))
        tt = theory_threshold(w, r)
        out.append(("ly_thuyet", r, tt, p >= tt))
        out.append(("persistence", r, float("nan"), q0 >= thr_q))
    return out


# ================================================================ một lần chia

def run_split(sets: dict, p2: pl.DataFrame, seeds, n_jobs: int,
              levels=LEVELS) -> tuple[list[dict], dict]:
    vend = date.fromisoformat(cfg.VALID_END)
    # = ngưỡng classifier.py: mùa lũ, train + valid của panel R2 (806 / 1 275 m³/s)
    thr = {k: fold_threshold(p2, date(1900, 1, 1), vend, rl.QUANTILES[v]) for k, v in levels.items()}
    rows, curves = [], {}
    for name, (panel, feats, _) in sets.items():
        X = panel.select(feats).to_numpy().astype(float)
        q0 = panel["discharge"].to_numpy().astype(float)
        split = sa.main_split()
        for h in cfg.HORIZONS:
            m = ab.masks(panel, feats, h, split)
            trv = m["train"] | m["valid"]
            tgt = _target(panel, h)
            for k, lv in levels.items():
                y = tgt >= thr[k]
                if y[m["train"]].sum() < MIN_TRAIN_POS:
                    print(f"  ! {name} {lv} h{h}: < {MIN_TRAIN_POS} ngày dương trong train — bỏ")
                    continue
                p_va, w_va = fit_proba(X, feats, y, m["train"], m["valid"], seeds, n_jobs)
                p_te, w = fit_proba(X, feats, y, trv, m["test"], seeds, n_jobs)
                y_va, y_te = y[m["valid"]], y[m["test"]]
                chosen = {r: choose_threshold(y_va, p_va, r)[0] for r in RATIOS}
                meta = {"bo_dac_trung": name, "muc": lv, "nguong_m3s": round(thr[k], 1),
                        "horizon": h, "fold": None}
                for meth, r, t, pred in _methods(y_va, p_va, q0[m["valid"]], thr[k], chosen, w_va):
                    rows.append({**meta, "pham_vi": "split_valid", "ty_le": r, "phuong_phap": meth,
                                 "nguong_p": t, "w_pos": round(w_va, 2),
                                 "n_pos_train": int(y[m["train"]].sum()), **event_row(y_va, pred, r)})
                for meth, r, t, pred in _methods(y_te, p_te, q0[m["test"]], thr[k], chosen, w):
                    rows.append({**meta, "pham_vi": "split_test", "ty_le": r, "phuong_phap": meth,
                                 "nguong_p": t, "w_pos": round(w, 2),
                                 "n_pos_train": int(y[trv].sum()), **event_row(y_te, pred, r)})
                curves[(name, k, h)] = {"valid": (y_va, p_va), "test": (y_te, p_te),
                                        "chosen": chosen}
                print(f"  split {name} {lv} h{h}: valid {int(y_va.sum())} dương, test "
                      f"{int(y_te.sum())} · ngưỡng R=10 → {chosen[10]:.3f}", flush=True)
    return rows, curves


# ================================================================ walk-forward

def run_oof(name: str, panel: pl.DataFrame, feats: list[str], start: date, thr_panel: pl.DataFrame,
            years, seeds, n_jobs: int, levels=LEVELS) -> pl.DataFrame:
    """Dự báo out-of-fold từng năm (mô hình train tới 28/12 năm trước)."""
    X = panel.select(feats).to_numpy().astype(float)
    d = panel["date"].to_numpy()
    q0 = panel["discharge"].to_numpy().astype(float)
    tgts = {h: _target(panel, h) for h in cfg.HORIZONS}
    parts = []
    for year in years:
        t0 = time.time()
        fold = year_fold(year, start)
        thr = {k: fold_threshold(thr_panel, THR_START, fold["train"][1], rl.QUANTILES[v])
               for k, v in levels.items()}
        for h in cfg.HORIZONS:
            m = ab.masks(panel, feats, h, fold)
            tr, te = m["train"], m["test"]
            if not te.any():
                continue
            for k in levels:
                y = tgts[h] >= thr[k]
                if y[tr].sum() < MIN_TRAIN_POS:
                    continue
                p, w = fit_proba(X, feats, y, tr, te, seeds, n_jobs)
                parts.append(pl.DataFrame({
                    "bo_dac_trung": name, "level": k, "horizon": h, "year": year,
                    "date": d[te], "y": y[te], "p": p, "q0": q0[te],
                    "thr_q": thr[k], "w": w}))
        print(f"  OOF {name} {year}: ngưỡng mức 1 {thr[1]:6.1f} · {time.time() - t0:4.1f}s",
              flush=True)
    return pl.concat(parts, how="vertical_relaxed")


def evaluate_wf(oof: pl.DataFrame, years=WF_YEARS) -> list[dict]:
    """Mỗi fold Y: chọn ngưỡng trên OOF của năm < Y (≤ 28/12/(Y−1)), áp vào năm Y."""
    rows = []
    for (name, k, h), g in oof.group_by(["bo_dac_trung", "level", "horizon"], maintain_order=True):
        yr, dt = g["year"].to_numpy(), g["date"].to_numpy()
        yy, pp = g["y"].to_numpy(), g["p"].to_numpy()
        q0, tq, ww = g["q0"].to_numpy(), g["thr_q"].to_numpy(), g["w"].to_numpy()
        for year in years:
            te = yr == year
            if not te.any():
                continue
            pm = pool_mask(yr, dt, year, year_fold(year, THR_START)["train"][1])
            chosen, picked = {}, {}
            for r in RATIOS:
                chosen[r], picked[r] = choose_threshold(yy[pm], pp[pm], r)
            meta = {"bo_dac_trung": name, "muc": LEVELS[k], "nguong_m3s": round(float(tq[te][0]), 1),
                    "horizon": h, "fold": year, "w_pos": round(float(ww[te][0]), 2),
                    "n_pool": int(pm.sum()), "n_pool_pos": int(yy[pm].sum())}
            for meth, r, t, pred in _methods(yy[te], pp[te], q0[te], tq[te][0], chosen,
                                             float(ww[te][0])):
                rows.append({**meta, "pham_vi": "wf_fold", "ty_le": r, "phuong_phap": meth,
                             "nguong_p": t, "nguong_da_chon": picked[r] if meth == "chi_phi" else None,
                             **event_row(yy[te], pred, r)})
    return rows


def pool_wf(folds: pl.DataFrame) -> list[dict]:
    """Cộng hits/misses/FA qua 13 fold + so từng fold (chi phí) với p=0.5 và E với R2."""
    rows = []
    keys = folds.select("bo_dac_trung", "muc", "horizon", "ty_le", "phuong_phap").unique(maintain_order=True)
    for name, lv, h, r, meth in keys.iter_rows():
        def sel(n=name, mm=meth):
            return folds.filter((pl.col("bo_dac_trung") == n) & (pl.col("muc") == lv)
                                & (pl.col("horizon") == h) & (pl.col("ty_le") == r)
                                & (pl.col("phuong_phap") == mm)).sort("fold")
        s = sel()
        hi, mi, fa = (int(s[c].sum()) for c in ("hits", "misses", "false_alarms"))
        t = s["nguong_p"].drop_nulls().drop_nans()
        row = {"bo_dac_trung": name, "muc": lv, "horizon": h, "pham_vi": "wf_2013_2025",
               "ty_le": r, "phuong_phap": meth, "n_fold": s.height,
               "nguong_p": float(t.median()) if t.len() else None,
               "nguong_p_min": float(t.min()) if t.len() else None,
               "nguong_p_max": float(t.max()) if t.len() else None,
               "n": int(s["n"].sum()), "n_pos": hi + mi, "hits": hi, "misses": mi,
               "false_alarms": fa, "n_alarm": hi + fa, **_pfc(hi, mi, fa),
               "cost": r * mi + fa, "cost_never": r * (hi + mi)}
        if meth != "p=0.5":
            b = sel(mm="p=0.5")
            dc = (s["cost"] - b["cost"]).cast(pl.Float64).to_numpy()
            lo, up = boot_mean_ci(dc)
            row.update({"d_cost_vs_p05_mean": float(dc.mean()), "d_cost_vs_p05_ci_lo": lo,
                        "d_cost_vs_p05_ci_hi": up, "p_wilcoxon_vs_p05": wilcoxon_p(dc),
                        "n_fold_re_hon_p05": int((dc < 0).sum()),
                        "n_fold_dat_hon_p05": int((dc > 0).sum())})
        if name == "E" and meth != "persistence":
            # so trên các fold CHUNG (R2 bỏ fold có < 10 ngày dương trong train) và
            # cùng nhãn (cùng số ngày dương từng fold)
            j = s.select("fold", "n_pos", "cost").join(
                sel(n="R2").select("fold", "n_pos", pl.col("cost").alias("cost_r2")),
                on=["fold", "n_pos"], how="inner")
            if j.height >= 2:
                dc = (j["cost"] - j["cost_r2"]).cast(pl.Float64).to_numpy()
                lo, up = boot_mean_ci(dc)
                row.update({"n_fold_chung_R2": j.height, "d_cost_E_vs_R2_mean": float(dc.mean()),
                            "d_cost_E_vs_R2_ci_lo": lo, "d_cost_E_vs_R2_ci_hi": up,
                            "p_wilcoxon_E_vs_R2": wilcoxon_p(dc),
                            "n_fold_E_re_hon": int((dc < 0).sum()),
                            "n_fold_E_dat_hon": int((dc > 0).sum())})
        rows.append(row)
    return rows


# ================================================================ hiệu chỉnh isotonic (FR-M6)

def brier(y: np.ndarray, p: np.ndarray) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.mean((p - y) ** 2)) if len(y) else float("nan")


def log_loss(y: np.ndarray, p: np.ndarray, eps: float = LOGLOSS_EPS) -> float:
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))) if len(y) else float("nan")


def fit_calibrator(p: np.ndarray, y: np.ndarray, min_pos: int = MIN_POOL_POS):
    """``IsotonicRegression`` (clip, [0, 1]) học ánh xạ p → P(y = 1) trên bể; bể có
    < ``min_pos`` ngày dương ⇒ ``None`` (không hiệu chỉnh)."""
    from sklearn.isotonic import IsotonicRegression

    y = np.asarray(y, bool)
    if int(y.sum()) < min_pos:
        return None
    return IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(
        np.asarray(p, float), y.astype(float))


def calibrate_fold(years: np.ndarray, dates: np.ndarray, y: np.ndarray, p: np.ndarray,
                   test_year: int) -> tuple[np.ndarray, object, np.ndarray, np.ndarray]:
    """``(pool, calibrator, p_bể_đã_hiệu_chỉnh, p_test_đã_hiệu_chỉnh)`` cho năm ``test_year``.

    Bể = ``pool_mask`` (năm < Y, ≤ 28/12/(Y−1)) — đúng bể chọn ngưỡng; bộ hiệu chỉnh
    không bao giờ thấy hàng của năm ≥ Y. Không hiệu chỉnh được ⇒ trả xác suất thô.
    """
    years, p = np.asarray(years), np.asarray(p, float)
    pm = pool_mask(years, dates, test_year, year_fold(test_year, THR_START)["train"][1])
    te = years == test_year
    iso = fit_calibrator(p[pm], np.asarray(y)[pm])
    if iso is None:
        return pm, None, p[pm], p[te]
    return pm, iso, iso.predict(p[pm]), iso.predict(p[te])


def reliability_bins(y: np.ndarray, p: np.ndarray, n_bins: int = N_BINS) -> list[dict]:
    """Reliability diagram: ``n_bins`` khoảng đều trên [0, 1] (khoảng cuối đóng)."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    idx = np.minimum((p * n_bins).astype(int), n_bins - 1)
    out = []
    for b in range(n_bins):
        s = idx == b
        n = int(s.sum())
        out.append({"bin": b, "p_lo": b / n_bins, "p_hi": (b + 1) / n_bins, "n": n,
                    "n_pos": int(y[s].sum()), "p_mean": float(p[s].mean()) if n else float("nan"),
                    "tan_suat": float(y[s].mean()) if n else float("nan")})
    return out


def ece(y: np.ndarray, p: np.ndarray, n_bins: int = N_BINS) -> float:
    """Sai số hiệu chỉnh kỳ vọng = Σ n_b/N · |tần suất − p trung bình| (bin như trên)."""
    b = [x for x in reliability_bins(y, p, n_bins) if x["n"]]
    n = sum(x["n"] for x in b)
    return float(sum(x["n"] / n * abs(x["tan_suat"] - x["p_mean"]) for x in b)) if n else float("nan")


def evaluate_cal(oof: pl.DataFrame, years=WF_YEARS) -> tuple[list[dict], pl.DataFrame]:
    """Mỗi fold Y: hiệu chỉnh + chọn ngưỡng trên bể của Y, áp vào năm Y.

    Trả (hàng theo fold × tỉ lệ × phương pháp, khung OOF năm test có ``p_iso``,
    ``p_clim`` = tần suất dương của bể).
    """
    rows, cal = [], []
    for (name, k, h), g in oof.group_by(["bo_dac_trung", "level", "horizon"], maintain_order=True):
        yr, dt = g["year"].to_numpy(), g["date"].to_numpy()
        yy, pp = g["y"].to_numpy().astype(bool), g["p"].to_numpy().astype(float)
        tq, ww = g["thr_q"].to_numpy(), g["w"].to_numpy()
        for year in years:
            te = yr == year
            if not te.any():
                continue
            pm, iso, pc_pool, pc_te = calibrate_fold(yr, dt, yy, pp, year)
            y_te, p_te = yy[te], pp[te]
            clim = float(yy[pm].mean()) if pm.any() else float("nan")
            cal.append(pl.DataFrame({"bo_dac_trung": name, "level": k, "horizon": h, "year": year,
                                     "date": dt[te], "y": y_te, "p": p_te, "p_iso": pc_te,
                                     "p_clim": clim}))
            meta = {"bo_dac_trung": name, "muc": LEVELS[k], "nguong_m3s": round(float(tq[te][0]), 1),
                    "horizon": h, "fold": year, "pham_vi": "wf_fold", "w_pos": round(float(ww[te][0]), 2),
                    "n_pool": int(pm.sum()), "n_pool_pos": int(yy[pm].sum()),
                    "da_hieu_chinh": iso is not None}
            prob = {"raw": (brier(y_te, p_te), log_loss(y_te, p_te)),
                    "iso": (brier(y_te, pc_te), log_loss(y_te, pc_te))}
            for r in RATIOS:
                t_raw, ok_raw = choose_threshold(yy[pm], pp[pm], r)
                t_iso, ok_iso = choose_threshold(yy[pm], pc_pool, r)
                t_bay = 1.0 / (1.0 + r) if iso is not None else DEFAULT_P
                for meth, scale, t, ok in (("p=0.5", "raw", DEFAULT_P, None),
                                           ("chi_phi", "raw", t_raw, ok_raw),
                                           ("chi_phi_iso", "iso", t_iso, ok_iso),
                                           ("bayes_iso", "iso", t_bay, None)):
                    pv = p_te if scale == "raw" else pc_te
                    rows.append({**meta, "ty_le": r, "phuong_phap": meth, "thang_p": scale,
                                 "nguong_p": t, "nguong_da_chon": ok, "brier": prob[scale][0],
                                 "log_loss": prob[scale][1], **event_row(y_te, pv >= t, r)})
    return rows, pl.concat(cal, how="vertical_relaxed")


def pool_cal(folds: pl.DataFrame, cal: pl.DataFrame) -> list[dict]:
    """Cộng qua fold + so cặp từng fold với nhánh thô ``chi_phi`` và với p=0.5."""
    rows = []
    keys = folds.select("bo_dac_trung", "muc", "horizon", "ty_le", "phuong_phap").unique(maintain_order=True)
    for name, lv, h, r, meth in keys.iter_rows():
        def sel(mm=meth):
            return folds.filter((pl.col("bo_dac_trung") == name) & (pl.col("muc") == lv)
                                & (pl.col("horizon") == h) & (pl.col("ty_le") == r)
                                & (pl.col("phuong_phap") == mm)).sort("fold")
        s = sel()
        k = next(kk for kk, v in LEVELS.items() if v == lv)
        c = cal.filter((pl.col("bo_dac_trung") == name) & (pl.col("level") == k)
                       & (pl.col("horizon") == h))
        yc = c["y"].to_numpy().astype(bool)
        pc = c["p" if s["thang_p"][0] == "raw" else "p_iso"].to_numpy().astype(float)
        hi, mi, fa = (int(s[col].sum()) for col in ("hits", "misses", "false_alarms"))
        t = s["nguong_p"].drop_nulls().drop_nans()
        bs, bs_clim = brier(yc, pc), brier(yc, c["p_clim"].to_numpy())
        row = {"bo_dac_trung": name, "muc": lv, "horizon": h, "pham_vi": "wf_2013_2025",
               "ty_le": r, "phuong_phap": meth, "thang_p": s["thang_p"][0], "n_fold": s.height,
               "n_fold_hieu_chinh": int(s["da_hieu_chinh"].sum()),
               "nguong_p": float(t.median()) if t.len() else None,
               "nguong_p_min": float(t.min()) if t.len() else None,
               "nguong_p_max": float(t.max()) if t.len() else None,
               "n": int(s["n"].sum()), "n_pos": hi + mi, "hits": hi, "misses": mi,
               "false_alarms": fa, "n_alarm": hi + fa, "fa_moi_nam": fa / s.height,
               **_pfc(hi, mi, fa), "cost": r * mi + fa, "cost_never": r * (hi + mi),
               "brier": bs, "brier_clim": bs_clim,
               "BSS": 1 - bs / bs_clim if bs_clim > 0 else float("nan"),
               "log_loss": log_loss(yc, pc), "ece": ece(yc, pc)}
        for ref, tag in (("chi_phi", "raw"), ("p=0.5", "p05")):
            if meth == ref or (ref == "chi_phi" and meth == "p=0.5"):
                continue
            b = sel(ref)
            dc = (s["cost"] - b["cost"]).cast(pl.Float64).to_numpy()
            lo, up = boot_mean_ci(dc)
            row.update({f"d_cost_vs_{tag}_mean": float(dc.mean()), f"d_cost_vs_{tag}_ci_lo": lo,
                        f"d_cost_vs_{tag}_ci_hi": up, f"p_wilcoxon_vs_{tag}": wilcoxon_p(dc),
                        f"n_fold_re_hon_{tag}": int((dc < 0).sum()),
                        f"n_fold_dat_hon_{tag}": int((dc > 0).sum())})
            if tag == "raw" and s["thang_p"][0] == "iso":
                db = (s["brier"] - b["brier"]).to_numpy().astype(float)
                lo, up = boot_mean_ci(db)
                row.update({"d_brier_vs_raw_mean": float(np.nanmean(db)), "d_brier_vs_raw_ci_lo": lo,
                            "d_brier_vs_raw_ci_hi": up, "p_wilcoxon_brier_vs_raw": wilcoxon_p(db),
                            "n_fold_brier_tot_hon": int((db < 0).sum())})
        rows.append(row)
    return rows


def calibration_bins(cal: pl.DataFrame) -> pl.DataFrame:
    """Bảng reliability (thô và đã hiệu chỉnh) — OOF gộp các năm test, mọi nhóm."""
    rows = []
    for (name, k, h), g in cal.group_by(["bo_dac_trung", "level", "horizon"], maintain_order=True):
        y = g["y"].to_numpy()
        for scale, col in (("raw", "p"), ("iso", "p_iso")):
            for b in reliability_bins(y, g[col].to_numpy()):
                rows.append({"bo_dac_trung": name, "muc": LEVELS[k], "horizon": h,
                             "nam": f"{g['year'].min()}-{g['year'].max()}", "thang_p": scale, **b})
    return pl.from_dicts(rows)


def plot_reliability(bins: pl.DataFrame, out: Path = OUT_FIG_CAL, level: str = "nguy_co_1") -> Path:
    """Reliability diagram mức 1 (thô vs isotonic), mỗi bộ đặc trưng một hàng, mỗi h một cột;
    dưới mỗi ô là số ngày trong từng khoảng (trục log)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    titles = {"E": "Config E (88)", "R2": "R2 features (66)", "B": "R2 features, from 1997 (66)"}
    sets = [s for s in titles if bins.filter(pl.col("bo_dac_trung") == s).height]
    if not sets:
        return out
    style = {"raw": ("#eb6834", "o", "Raw LightGBM probability"),
             "iso": ("#2a78d6", "s", "Isotonic-calibrated (fit on past years only)")}
    hs = list(cfg.HORIZONS)
    fig = plt.figure(figsize=(4.6 * len(hs), 6.4 * len(sets) + 0.6))
    subs = np.atleast_1d(fig.subfigures(len(sets), 1, hspace=0.04))
    width = 1 / (2.6 * N_BINS)
    for i, (name, sf) in enumerate(zip(sets, subs)):
        gs = sf.add_gridspec(2, len(hs), height_ratios=[3, 1.4], hspace=0.06, wspace=0.22)
        for j, h in enumerate(hs):
            a = sf.add_subplot(gs[0, j])
            ac = sf.add_subplot(gs[1, j], sharex=a)
            g = bins.filter((pl.col("bo_dac_trung") == name) & (pl.col("muc") == level)
                            & (pl.col("horizon") == h))
            a.plot([0, 1], [0, 1], color="0.6", lw=1, ls="--",
                   label="Perfect calibration" if (i, j) == (0, 0) else None)
            for o, (scale, (col, mk, lab)) in enumerate(style.items()):
                s = g.filter((pl.col("thang_p") == scale) & (pl.col("n") > 0)).sort("bin")
                if not s.height:
                    continue
                a.plot(s["p_mean"], s["tan_suat"], color=col, lw=1.4, alpha=0.9,
                       label=lab if (i, j) == (0, 0) else None)
                big = (s["n"] >= 10).to_numpy()
                pm_, fq = s["p_mean"].to_numpy(), s["tan_suat"].to_numpy()
                a.plot(pm_[big], fq[big], color=col, marker=mk, ms=6, ls="none")
                a.plot(pm_[~big], fq[~big], marker=mk, ms=6, ls="none", mfc="white", mec=col)
                x = s["p_lo"].to_numpy() + 0.5 / N_BINS + (o - 0.5) * width
                ac.bar(x, s["n"].to_numpy(), width=width, color=col, alpha=0.85)
                for xx, n, npos in zip(x, s["n"], s["n_pos"]):
                    ac.text(xx, n * 1.3, f"{n} ({npos})", ha="center", va="bottom",
                            fontsize=6, color=col, rotation=90)
            raw = g.filter(pl.col("thang_p") == "raw")
            yrs = g["nam"][0] if g.height else ""
            a.set_title(f"{titles[name]} — h = {h} d · {yrs} pooled OOF\n"
                        f"{int(raw['n'].sum())} days, {int(raw['n_pos'].sum())} positive",
                        fontsize=9.5)
            a.set_xlim(0, 1)
            a.set_ylim(-0.02, 1.02)
            a.grid(alpha=0.25)
            a.tick_params(labelbottom=False)
            if j == 0:
                a.set_ylabel("Observed frequency of Q ≥ level 1")
                ac.set_ylabel("Days per bin\n(positives)", fontsize=8)
            ac.set_yscale("log")
            ac.set_ylim(0.8, max(10, int(g["n"].max() or 1)) * 3000)
            ac.set_xticks(np.linspace(0, 1, N_BINS + 1))
            ac.tick_params(axis="x", labelsize=7.5)
            ac.grid(alpha=0.25, axis="y")
            ac.set_xlabel("Forecast probability (10 equal-width bins)", fontsize=8.5)
    h_, l_ = subs[0].axes[0].get_legend_handles_labels()
    h_.append(plt.Line2D([], [], color="0.4", marker="o", mfc="white", ls="none"))
    l_.append("Hollow marker: < 10 days in bin (noisy)")
    fig.legend(h_, l_, loc="lower center", ncol=4, fontsize=9, frameon=False,
               bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Reliability diagram — risk level 1 classifier, walk-forward out-of-fold "
                 "(isotonic fit for year Y uses only years < Y)", fontsize=11, y=1.0)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def report_cal(res: pl.DataFrame) -> None:
    show = ["bo_dac_trung", "horizon", "ty_le", "phuong_phap", "nguong_p", "nguong_p_min",
            "nguong_p_max", "hits", "misses", "false_alarms", "POD", "FAR", "CSI", "cost",
            "brier", "BSS", "log_loss", "ece"]
    cmp_ = ["bo_dac_trung", "horizon", "ty_le", "phuong_phap", "d_cost_vs_raw_mean",
            "d_cost_vs_raw_ci_lo", "d_cost_vs_raw_ci_hi", "p_wilcoxon_vs_raw", "n_fold_re_hon_raw",
            "n_fold_dat_hon_raw", "d_cost_vs_p05_mean", "p_wilcoxon_vs_p05",
            "d_brier_vs_raw_mean", "p_wilcoxon_brier_vs_raw", "n_fold_brier_tot_hon"]
    with pl.Config(tbl_rows=400, tbl_cols=24, tbl_width_chars=240, float_precision=4):
        s = res.filter((pl.col("pham_vi") == "wf_2013_2025") & (pl.col("muc") == "nguy_co_1"))
        print("\n=== hiệu chỉnh isotonic — walk-forward 2013–2025, mức 1 ===")
        print(s.select([c for c in show if c in s.columns]))
        s = s.filter(pl.col("phuong_phap").is_in(["chi_phi_iso", "bayes_iso"]))
        print("\n=== so cặp từng fold (iso − thô `chi_phi`; − p=0.5) ===")
        print(s.select([c for c in cmp_ if c in s.columns]))


def run_calibration(oof: pl.DataFrame, years, out: Path = OUT_CAL, fig: Path = OUT_FIG_CAL) -> tuple:
    folds, cal = evaluate_cal(oof, years)
    fdf = pl.from_dicts(folds, infer_schema_length=None)
    res = pl.from_dicts(folds + pool_cal(fdf, cal), infer_schema_length=None)
    bins = calibration_bins(cal)
    out.parent.mkdir(parents=True, exist_ok=True)
    res.write_csv(out)
    out_bins = out.with_name(out.stem + "_bins.csv")
    bins.write_csv(out_bins)
    report_cal(res)
    return out, out_bins, plot_reliability(bins, fig)


# ================================================================ hình

def plot(curves: dict, oof: pl.DataFrame, out: Path = OUT_FIG) -> Path:
    """Chi phí tương đối (C / chi phí không bao giờ báo) theo ngưỡng — mức 1."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {5: "#2a78d6", 10: "#eb6834", 20: "#1baf7a"}
    titles = {"R2": "R2 features (66)", "B": "R2 features, trained from 1997 (66)",
              "E": "Config E (88)"}
    sets = [s for s in titles if any(k[0] == s for k in curves)]
    if not sets:
        return out
    fig, axes = plt.subplots(len(sets), 3, figsize=(13, 3.9 * len(sets)), sharey=True,
                             squeeze=False)
    for i, name in enumerate(sets):
        for j, h in enumerate(cfg.HORIZONS):
            axx = axes[i, j]
            c = curves.get((name, 1, h))
            g = oof.filter((pl.col("bo_dac_trung") == name) & (pl.col("level") == 1)
                           & (pl.col("horizon") == h)
                           & pl.col("year").is_between(WF_YEARS[0], WF_YEARS[-1]))
            for r in RATIOS:
                if g.height:
                    yw, pw = g["y"].to_numpy(), g["p"].to_numpy()
                    axx.plot(GRID, cost_curve(yw, pw, r) / (r * yw.sum()), color=colors[r], lw=1.8,
                             label=f"{r}:1 walk-forward 2013–25, pooled OOF (descriptive)"
                             if (i, j) == (0, 0) else None)
                if c is not None:
                    yv, pv = c["valid"]
                    axx.plot(GRID, cost_curve(yv, pv, r) / (r * yv.sum()), color=colors[r], lw=1.1,
                             ls="--", label=f"{r}:1 valid 2016–06/2022 (selection set)"
                             if (i, j) == (0, 0) else None)
                    t = c["chosen"][r]
                    axx.plot([t], [cost_curve(yv, pv, r, np.array([t]))[0] / (r * yv.sum())],
                             marker="v", color=colors[r], ms=8, ls="none")
            axx.axvline(DEFAULT_P, color="0.45", lw=1, ls=":")
            axx.text(DEFAULT_P * 1.15, 1.42, "p = 0.5", fontsize=8, color="0.35")
            axx.axhline(1.0, color="0.75", lw=0.8)
            axx.set_ylim(0, 1.5)
            axx.set_xscale("logit")
            axx.set_xlim(GRID[0], GRID[-1])
            axx.set_xticks([0.001, 0.01, 0.1, 0.5, 0.9, 0.99])
            axx.set_xticklabels(["0.001", "0.01", "0.1", "0.5", "0.9", "0.99"])
            axx.minorticks_off()
            n_wf = int(g["y"].sum()) if g.height else 0
            n_va = int(c["valid"][0].sum()) if c else 0
            axx.set_title(f"{titles[name]} — h = {h} d\n"
                          f"positives: walk-forward {n_wf}, valid {n_va}", fontsize=10)
            if j == 0:
                axx.set_ylabel("Relative cost  C / C(never warn)")
            if i == len(sets) - 1:
                axx.set_xlabel("Probability threshold (logit scale)")
            axx.grid(alpha=0.25)
    fig.legend(loc="lower center", ncol=3, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Risk level 1 (Q ≥ flood-season Q95): expected cost C = R·misses + false alarms "
                 "vs probability threshold\n▼ = threshold chosen on valid (never on test); "
                 "1.0 = cost of never warning", fontsize=11)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


# ================================================================ in

def report(res: pl.DataFrame) -> None:
    show = ["bo_dac_trung", "muc", "horizon", "ty_le", "phuong_phap", "nguong_p", "n_pos",
            "POD", "FAR", "CSI", "cost"]
    with pl.Config(tbl_rows=400, tbl_cols=20, tbl_width_chars=200, float_precision=3):
        for scope in ("split_test", "wf_2013_2025"):
            s = res.filter((pl.col("pham_vi") == scope) & (pl.col("muc") == "nguy_co_1"))
            print(f"\n=== {scope} — mức 1 ===")
            print(s.select([c for c in show if c in s.columns]))
        s = res.filter((pl.col("pham_vi") == "wf_2013_2025") & (pl.col("phuong_phap") == "chi_phi"))
        cols = ["bo_dac_trung", "muc", "horizon", "ty_le", "d_cost_vs_p05_mean", "d_cost_vs_p05_ci_lo",
                "d_cost_vs_p05_ci_hi", "p_wilcoxon_vs_p05", "d_cost_E_vs_R2_mean",
                "p_wilcoxon_E_vs_R2"]
        print("\n=== walk-forward: Δ chi phí từng fold ===")
        print(s.select([c for c in cols if c in s.columns]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sets", nargs="+", default=["R2", "E"])
    ap.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    ap.add_argument("--years", nargs="+", type=int, default=None,
                    help="năm fold tổng hợp (mặc định 2013–2025)")
    ap.add_argument("--n-jobs", type=int, default=4)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--fig", type=Path, default=OUT_FIG)
    ap.add_argument("--no-split", action="store_true")
    ap.add_argument("--oof-out", type=Path, default=None, help="lưu dự báo OOF (parquet) để soát")
    ap.add_argument("--calibrate", action="store_true",
                    help="FR-M6: hiệu chỉnh isotonic + reliability diagram (ghi --cal-out, "
                         "không ghi --out)")
    ap.add_argument("--oof-in", type=Path, default=None,
                    help="với --calibrate: đọc OOF đã lưu (--oof-out) thay vì học lại")
    ap.add_argument("--cal-out", type=Path, default=OUT_CAL)
    ap.add_argument("--cal-fig", type=Path, default=OUT_FIG_CAL)
    a = ap.parse_args(argv)

    t0 = time.time()
    years = tuple(a.years) if a.years else WF_YEARS
    if a.calibrate and a.oof_in:
        oof = pl.read_parquet(a.oof_in).filter(pl.col("bo_dac_trung").is_in(a.sets))
        outs = run_calibration(oof, years, a.cal_out, a.cal_fig)
        print("\n" + "\n".join(f"→ {o}" for o in outs) + f"\n({time.time() - t0:.0f}s)")
        return 0
    sets = {s: load_set(s) for s in a.sets}
    p2 = sets["R2"][0] if "R2" in sets else load_set("R2")[0]
    thr_panel = sets["E"][0] if "E" in sets else load_set("E")[0]
    seeds = tuple(a.seeds)
    print("Bộ đặc trưng: " + ", ".join(f"{k} {len(v[1])} cột từ {v[2]}" for k, v in sets.items())
          + f" · seed {seeds} · tỉ lệ {RATIOS}")

    rows, curves = ([], {}) if (a.no_split or a.calibrate) else run_split(sets, p2, seeds, a.n_jobs)

    oofs = []
    for name, (panel, feats, start) in sets.items():
        yrs = range(WF_FIRST[name], max(years) + 1)
        oofs.append(run_oof(name, panel, feats, start, thr_panel, yrs, seeds, a.n_jobs))
    oof = pl.concat(oofs, how="vertical_relaxed")
    if a.oof_out:
        a.oof_out.parent.mkdir(parents=True, exist_ok=True)
        oof.write_parquet(a.oof_out)
    if a.calibrate:
        outs = run_calibration(oof, years, a.cal_out, a.cal_fig)
        print("\n" + "\n".join(f"→ {o}" for o in outs) + f"\n({time.time() - t0:.0f}s)")
        return 0
    folds = evaluate_wf(oof, years)
    pooled = pool_wf(pl.from_dicts(folds, infer_schema_length=None))

    res = pl.from_dicts(rows + folds + pooled, infer_schema_length=None)
    res = res.with_columns(pl.lit(",".join(map(str, seeds))).alias("seeds"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    res.write_csv(a.out)
    report(res)
    fig = plot(curves, oof, a.fig)
    print(f"\n→ {a.out}\n→ {fig}\n({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
