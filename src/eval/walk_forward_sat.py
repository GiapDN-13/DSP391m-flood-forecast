"""Walk-forward theo NĂM: mức tăng NSE nhờ mưa vệ tinh (IMERG / GSMaP-GC) có giữ
được qua nhiều năm test không? (Report 3)

``ablation_sat.py`` chỉ có MỘT lần chia (test ≥ 2022-07-01, ~4 năm, 31 ngày vượt
mức 1) ⇒ ΔNSE +0,02–0,03 ở h2–h3 có thể chỉ là may rủi của một cửa sổ. Ở đây mỗi
năm test là một fold, cửa sổ train MỞ RỘNG (ý tưởng ``walk_forward.py``):

    fold Y = 2013 … 2025   train [đầu nhóm, 28/12/(Y−1)] · test cả năm Y
    fold 2026 (01–08)      fold lẻ — báo riêng, KHÔNG vào tổng hợp chính

Bỏ 3 ngày cuối trước năm test (gap = horizon lớn nhất) ⇒ nhãn t+3 của hàng train
cuối (28/12) là 31/12, không chạm năm test.

Nhóm và cấu hình giữ nguyên ``ablation_sat.py`` (mỗi nhóm so với mốc của chính
nó, trên tập hàng chung của nhóm): ``r2`` = A0, +imerg, +gsmap_gc, +gsmap_gc lưu
vực con (panel từ 2010); ``ext`` = E0, +gsmap_gc, +imerg (train từ 1998-01-04).
LightGBM 3 seed; dự báo = trung bình 3 seed (NSE từng seed ghi thêm). Tham số
(``group_params``): nhóm ``r2`` giữ ``lgbm.PARAMS`` (L1 mọi horizon — mốc Report
2); nhóm ``ext`` là mô hình chính nên dùng ``lgbm.params_for(h)`` (L1 ở h=1, L2 ở
h=2–3, chọn bằng walk-forward/valid trong ``wf_tuning.py``) cho MỌI cấu hình
trong nhóm, kể cả ``--lag-test`` và ``--nrt-test``. Cột ``objective`` ghi hàm mất
mát đã dùng. Kết quả cũ (ext L1, trước 21/10/2026) ở ``reports/l1_ref/``.
Chạy một phần nhóm (``--groups ext``) ghi vào file mặc định thì dòng của nhóm
KHÔNG chạy lại được giữ nguyên từ file cũ (``merge_other_groups``). Ngưỡng mức 1 MỖI fold = Q95 lưu lượng mùa lũ 9–12 CHỈ trong cửa sổ
train của fold (định nghĩa ``risk_levels.fit_thresholds``) — không rò rỉ; ngưỡng
hai nhóm khác nhau vì cửa sổ train khác nhau. NSE mùa lũ: ngày phát dự báo t
thuộc tháng 9–12.

Tổng hợp theo giai đoạn: 2013–2025 (13 fold, chính), 2013–2021 (GloFAS
reanalysis), 2022 (năm đổi chế độ 07/2022, để riêng), 2023–2025 (GloFAS forecast
archive), 2026 lẻ. ΔNSE so với mốc nhóm: trung bình, trung vị, số fold thắng/thua
(và |Δ| ≥ 0,01), Wilcoxon signed-rank qua fold, CI 95 % của ΔNSE trung bình bằng
bootstrap theo fold; POD/FAR/CSI mức 1 GỘP hits/misses/false alarms mọi fold.

``--n-jobs`` chỉ đổi số luồng LightGBM (đã kiểm: NSE từng seed trùng
``ablation_hourly_sat.csv`` tới 5 chữ số).

    python -m src.eval.walk_forward_sat                  # ~15–26 phút, 882 lần fit
    python -m src.eval.walk_forward_sat --groups r2 --years 2013 2014 --out-dir <thư mục thử>
    python -m src.eval.walk_forward_sat --plot-only      # in lại + vẽ lại từ 2 file CSV, không fit
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from src import config as cfg
from src.eval import metrics, walk_forward
from src.features import hourly_features as hf
from src.features import risk_levels as rl
from src.models import ablation_hourly as ab
from src.models import ablation_sat as sa
from src.models import lgbm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_FOLDS = cfg.ROOT / "reports" / "wf_sat_folds.csv"
OUT_SUMMARY = cfg.ROOT / "reports" / "wf_sat_summary.csv"
OUT_FIG = cfg.FIGURES / "report" / "wf_sat_en.png"
OUT_LAG = cfg.ROOT / "reports" / "wf_sat_lag1.csv"   # phép thử độ trễ khi chạy thật
OUT_NRT = cfg.ROOT / "reports" / "wf_sat_nrt.csv"    # GSMaP_NRT (JAXA) so với bản chuẩn
SPLIT_CSV = sa.OUT                          # kết quả một-lần-chia để đối chiếu

GAP = walk_forward.GAP_DAYS                 # 3 = horizon lớn nhất
YEARS = tuple(range(2013, 2026))            # 13 fold đủ năm
PARTIAL = 2026                              # dữ liệu tới 08/2026 → fold lẻ
PERIODS = {"chinh_2013_2025": (2013, 2025),
           "reanalysis_2013_2021": (2013, 2021),
           "doi_che_do_2022": (2022, 2022),
           "forecast_2023_2025": (2023, 2025),
           "le_2026_01_08": (PARTIAL, PARTIAL)}
MAIN = "chinh_2013_2025"
SEEDS = sa.SEEDS
Q1 = rl.QUANTILES["nguy_co_1"]
N_BOOT = 10_000


# ================================================================ fold, ngưỡng

def year_fold(year: int, start: date, gap: int = GAP) -> dict[str, tuple[date, date]]:
    """Khoảng ngày (dạng ``ab.masks``) của fold năm test ``year``: train từ
    ``start`` tới 01/01/year − (gap + 1) ngày, test cả năm ``year``."""
    lo = date(year, 1, 1)
    return {"train": (start, lo - timedelta(days=gap + 1)), "test": (lo, date(year, 12, 31))}


def fold_type(year: int) -> str:
    return "le" if year == PARTIAL else "du_nam"


def fold_threshold(panel: pl.DataFrame, lo: date, hi: date, q: float = Q1) -> float:
    """Ngưỡng mức 1 của fold: phân vị ``q`` lưu lượng các ngày mùa lũ trong
    [lo, hi] (= ``risk_levels.fit_thresholds`` thu về cửa sổ train)."""
    d = pl.col("date").cast(pl.Date)
    s = (panel.filter(d.is_between(lo, hi) & d.dt.month().is_in(rl.FLOOD_MONTHS))["discharge"]
              .cast(pl.Float64).drop_nulls().drop_nans().to_numpy())
    return float(np.quantile(s, q))


def score(y: np.ndarray, yhat: np.ndarray, flood: np.ndarray, thr1: float) -> dict:
    rep = metrics.regression_report(y, yhat)
    ev = metrics.event_report(y >= thr1, yhat >= thr1)
    return {"NSE": rep["NSE"], "NSE_flood": metrics.nse(y[flood], yhat[flood]),
            "KGE": rep["KGE"], "RMSE": rep["RMSE"], "peak_bias": rep["peak_bias"],
            "n_pos1": ev["n_positive"], "hits1": ev["hits"], "misses1": ev["misses"],
            "false_alarms1": ev["false_alarms"], "POD1": ev["POD"], "FAR1": ev["FAR"],
            "CSI1": ev["CSI"]}


# ================================================================ chạy

def load_ext_lag1(group: str = "ext") -> tuple[pl.DataFrame, dict[str, list[str]], dict]:
    """Nhóm EXT + cấu hình GSMaP-GC TRỄ 1 NGÀY — đúng điều kiện chạy thật.

    Earth Engine đưa ảnh GSMaP lên chậm ~27 giờ (kiểm 20/10/2026: ảnh mới nhất
    13:00 UTC ngày 19/10 lúc 15:53 UTC ngày 20/10). Job dự báo chạy ~05h giờ VN
    nên ngày t (hôm qua) chưa đủ giờ; chỉ có đặc trưng vệ tinh của ngày t−1.
    """
    panel, cfgs, split = sa.load_group(group)
    base = next(iter(cfgs.values()))
    gc = [c for c in cfgs["E0+gsmap_gc"] if c not in base]
    panel = panel.sort("date").with_columns([pl.col(c).shift(1).alias(f"{c}_lag1") for c in gc])
    new = {next(iter(cfgs)): base, "E0+gsmap_gc": cfgs["E0+gsmap_gc"],
           "E0+gsmap_gc_lag1": base + [f"{c}_lag1" for c in gc]}
    return panel, new, split


def load_nrt(group: str) -> tuple[pl.DataFrame, dict[str, list[str]], dict]:
    """Mốc của nhóm + GSMaP-GC bản chuẩn (Earth Engine, chỉ phân tích lại quá khứ)
    + GSMaP_Gauge_NRT (JAXA, trễ ~4,7 h — dùng được khi chạy thật, không cần trễ)."""
    panel, cfgs, split = sa.load_group(group)
    panel = hf.join_panel(panel, sa.load_sat("gsmap_nrt"))
    name0, base = next(iter(cfgs.items()))
    std = next(k for k in cfgs if k.endswith("+gsmap_gc"))
    tag = name0.split()[0]
    new = {name0: base, std: cfgs[std],
           f"{tag}+gsmap_nrt": base + sa.sat_cols("gsmap_nrt", [hf.WHOLE])}
    return panel, new, split


def group_params(group: str, h: int) -> dict:
    """Tham số LightGBM của nhóm ở horizon ``h`` (đọc ``lgbm.PARAMS`` lúc gọi ⇒ giữ
    ``n_jobs`` đã đặt): ``ext`` = mô hình chính ``lgbm.params_for(h)``; ``r2`` =
    ``lgbm.PARAMS`` gốc (mốc Report 2)."""
    return lgbm.params_for(h) if group == "ext" else dict(lgbm.PARAMS)


def merge_other_groups(new: pl.DataFrame, path: Path) -> pl.DataFrame:
    """Giữ dòng của các nhóm KHÔNG có trong ``new`` từ file cũ ``path`` (chạy lại một
    phần nhóm mà không xoá kết quả nhóm kia). Dòng cũ thiếu cột ``objective`` là
    ``lgbm.PARAMS`` (L1)."""
    if not path.exists():
        return new
    old = pl.read_csv(path, infer_schema_length=None, try_parse_dates=True)
    keep = old.filter(~pl.col("group").is_in(new["group"].unique().to_list()))
    if keep.is_empty():
        return new
    if "objective" not in keep.columns:
        keep = keep.with_columns(objective=pl.lit(lgbm.PARAMS["objective"]))
    print(f"  giữ {keep.height} dòng nhóm {sorted(set(keep['group']))} từ {path.name} cũ")
    return pl.concat([keep, new], how="diagonal_relaxed")


def run_group(group: str, years: list[int], loader=None) -> list[dict]:
    panel, cfgs, split = (loader or sa.load_group)(group)
    start, names = split["train"][0], list(cfgs)
    base = names[0]
    union = sorted({c for f in cfgs.values() for c in f})
    X = {k: panel.select(f).to_numpy().astype(float) for k, f in cfgs.items()}
    d = panel["date"].cast(pl.Date)
    q0 = panel["discharge"].to_numpy().astype(float)
    flood_all = d.dt.month().is_in(rl.FLOOD_MONTHS).to_numpy()
    print(f"\n=== Nhóm {group}: mốc '{base}'; " + ", ".join(f"{k} {len(f)}" for k, f in cfgs.items()))

    rows = []
    for year in years:
        t0 = time.time()
        fold = year_fold(year, start)
        thr1 = fold_threshold(panel, *fold["train"])
        for h in cfg.HORIZONS:
            m = ab.masks(panel, union, h, fold)
            tr, te = m["train"], m["test"]
            y = panel[f"target_h{h}"].to_numpy().astype(float)
            params = group_params(group, h)
            d_tr, d_te = d.filter(pl.Series(tr)), d.filter(pl.Series(te))
            fl = flood_all[te]
            meta = {"group": group, "fold": year, "fold_type": fold_type(year), "horizon": h,
                    "train_start": d_tr.min(), "train_end": d_tr.max(),
                    "test_start": d_te.min(), "test_end": d_te.max(),
                    "gap_days": (d_te.min() - d_tr.max()).days - 1,
                    "n_train": int(tr.sum()), "n_test": int(te.sum()), "n_flood": int(fl.sum()),
                    "thr1": thr1, "objective": params["objective"]}
            rows.append({**meta, "config": "persistence", "n_feat": 1,
                         **score(y[te], q0[te], fl, thr1)})
            out = {}
            for name, feats in cfgs.items():
                ps = [ab.fit_predict(X[name], feats, y, tr, te, s, params)[0] for s in SEEDS]
                out[name] = {**meta, "config": name, "n_feat": len(feats),
                             **score(y[te], np.mean(ps, axis=0), fl, thr1),
                             **{f"NSE_seed{s}": metrics.nse(y[te], p) for s, p in zip(SEEDS, ps)}}
            b = out[base]
            for name, r in out.items():
                if name != base:
                    r.update({"dNSE": r["NSE"] - b["NSE"], "dNSE_flood": r["NSE_flood"] - b["NSE_flood"],
                              **{f"dNSE_seed{s}": r[f"NSE_seed{s}"] - b[f"NSE_seed{s}"] for s in SEEDS}})
                rows.append(r)
        r1 = [r for r in rows if r["fold"] == year and r["horizon"] == 2 and r["config"] != "persistence"]
        print(f"  {year} ({fold['train'][1]} | ngưỡng {thr1:6.1f}) {time.time() - t0:5.1f}s  h2 NSE "
              + " · ".join(f"{r['NSE']:.3f}" for r in r1), flush=True)
    return rows


# ================================================================ tổng hợp

def wilcoxon_p(d: np.ndarray, alternative: str = "two-sided") -> float:
    """Wilcoxon signed-rank qua fold (scipy; n ≤ 50 không trùng hạng ⇒ p chính xác)."""
    d = d[np.isfinite(d)]
    if len(d) < 2 or not np.any(d != 0):
        return float("nan")
    from scipy.stats import wilcoxon
    return float(wilcoxon(d, alternative=alternative).pvalue)


def boot_mean_ci(d: np.ndarray, n: int = N_BOOT, seed: int = cfg.SEED) -> tuple[float, float]:
    """CI 95 % (phân vị) của trung bình, bootstrap lấy lại FOLD có hoàn lại."""
    d = d[np.isfinite(d)]
    if len(d) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), (n, len(d)))].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(lo), float(hi)


def pooled(hits: int, misses: int, fa: int) -> dict:
    """POD/FAR/CSI từ hits/misses/false alarms đã cộng qua fold (công thức ``metrics.event_report``)."""
    nan = float("nan")
    return {"POD1": hits / (hits + misses) if hits + misses else nan,
            "FAR1": fa / (hits + fa) if hits + fa else nan,
            "CSI1": hits / (hits + misses + fa) if hits + misses + fa else nan}


def summarize(folds: pl.DataFrame) -> pl.DataFrame:
    rows = []
    keys = folds.select("group", "config", "horizon").unique(maintain_order=True)
    for g, c, h in keys.iter_rows():
        x = folds.filter((pl.col("group") == g) & (pl.col("config") == c)
                         & (pl.col("horizon") == h)).sort("fold")
        for per, (lo, hi) in PERIODS.items():
            s = x.filter(pl.col("fold").is_between(lo, hi))
            if s.is_empty():
                continue
            hits, miss, fa = (int(s[k].sum()) for k in ("hits1", "misses1", "false_alarms1"))
            r = {"group": g, "config": c, "horizon": h, "period": per, "n_folds": s.height,
                 **({"objective": s["objective"][0]} if "objective" in s.columns else {}),
                 "fold_tu": s["fold"].min(), "fold_den": s["fold"].max(),
                 "NSE_mean": s["NSE"].mean(), "NSE_median": s["NSE"].median(),
                 "NSE_flood_mean": s["NSE_flood"].mean(), "peak_bias_mean": s["peak_bias"].mean(),
                 "n_pos1": hits + miss, "hits1": hits, "misses1": miss, "false_alarms1": fa,
                 **pooled(hits, miss, fa)}
            if "dNSE" in s.columns and s["dNSE"].null_count() < s.height:
                dn = s["dNSE"].cast(pl.Float64).to_numpy()
                df = s["dNSE_flood"].cast(pl.Float64).to_numpy()
                ci = boot_mean_ci(dn)
                r.update({"dNSE_mean": float(np.mean(dn)), "dNSE_median": float(np.median(dn)),
                          "dNSE_ci_lo": ci[0], "dNSE_ci_hi": ci[1],
                          "n_win": int((dn > 0).sum()), "n_loss": int((dn < 0).sum()),
                          "n_win_001": int((dn >= ab.MIN_GAIN).sum()),
                          "n_loss_001": int((dn <= -ab.MIN_GAIN).sum()),
                          "p_wilcoxon": wilcoxon_p(dn), "p_wilcoxon_gt": wilcoxon_p(dn, "greater"),
                          "dNSE_flood_mean": float(np.nanmean(df)) if np.isfinite(df).any() else None,
                          "n_win_flood": int((df > 0).sum()), "n_loss_flood": int((df < 0).sum()),
                          **{f"dNSE_mean_seed{sd}": s[f"dNSE_seed{sd}"].mean() for sd in SEEDS}})
            rows.append(r)
    out = pl.from_dicts(rows, infer_schema_length=None)
    if SPLIT_CSV.exists():                  # đối chiếu một-lần-chia (test ≥ 2022-07-01)
        ref = (pl.read_csv(SPLIT_CSV, infer_schema_length=None)
                 .filter((pl.col("phase") == "test") & (pl.col("seed") == "mean3"))
                 .select("group", "config", "horizon", pl.col("NSE").alias("NSE_split_chinh"),
                         pl.col("dNSE").alias("dNSE_split_chinh")))
        out = out.join(ref, on=["group", "config", "horizon"], how="left")
    return out


# ================================================================ báo cáo

def _fmt(v, f="+.3f") -> str:
    return "  —  " if v is None or not np.isfinite(v) else format(v, f)


def report(summ: pl.DataFrame) -> None:
    has_ref = "dNSE_split_chinh" in summ.columns
    for g in summ["group"].unique(maintain_order=True):
        s = summ.filter((pl.col("group") == g) & (pl.col("config") != "persistence"))
        for per in PERIODS:
            x = s.filter(pl.col("period") == per)
            if x.is_empty():
                continue
            print(f"\n--- {g} · {per} ({x['n_folds'][0]} fold): NSE TB/trung vị · ΔNSE TB [CI95 "
                  f"bootstrap fold] trung vị · thắng/thua (|Δ|≥0,01) · p Wilcoxon 2 phía / Δ>0"
                  + (" · Δ một-lần-chia" if has_ref and per == MAIN else ""))
            for r in x.sort("horizon", maintain_order=True).iter_rows(named=True):
                line = f"  h={r['horizon']} {r['config']:<26} NSE {r['NSE_mean']:.3f}/{r['NSE_median']:.3f}"
                if r.get("dNSE_mean") is not None:
                    line += (f"  Δ {_fmt(r['dNSE_mean'])} [{_fmt(r['dNSE_ci_lo'])}, {_fmt(r['dNSE_ci_hi'])}]"
                             f" med {_fmt(r['dNSE_median'])}  {r['n_win']}/{r['n_loss']}"
                             f" ({r['n_win_001']}/{r['n_loss_001']})  p {_fmt(r['p_wilcoxon'], '.3f')}"
                             f"/{_fmt(r['p_wilcoxon_gt'], '.3f')}  Δmùa lũ {_fmt(r['dNSE_flood_mean'])}")
                    if has_ref and per == MAIN:
                        line += f"  | 1 lần chia {_fmt(r['dNSE_split_chinh'])}"
                print(line)
        ev = summ.filter((pl.col("group") == g) & (pl.col("horizon") == 1))
        print(f"--- {g}: mức 1, h=1, GỘP sự kiện qua fold (ngưỡng riêng từng fold)")
        for per in (MAIN, "reanalysis_2013_2021", "forecast_2023_2025"):
            for r in ev.filter(pl.col("period") == per).iter_rows(named=True):
                print(f"  {per:<22} {r['config']:<26} n+ {r['n_pos1']:3d}  hits {r['hits1']:3d} "
                      f"miss {r['misses1']:3d} FA {r['false_alarms1']:3d}  POD {_fmt(r['POD1'], '.3f')} "
                      f"FAR {_fmt(r['FAR1'], '.3f')} CSI {_fmt(r['CSI1'], '.3f')}")


# ================================================================ hình

LABELS = {"imerg": "+IMERG (whole basin)", "gsmap_gc": "+GSMaP-GC (whole basin)",
          "gsmap_gc luu vuc con": "+GSMaP-GC (5 sub-basins)"}
# Màu categorical cố định (dataviz palette, cùng dl_lstm.py), gán theo NGUỒN, không theo hạng.
COLORS = {"imerg": "#2a78d6", "gsmap_gc": "#eb6834", "gsmap_gc luu vuc con": "#1baf7a"}
MARKERS = {"imerg": "o", "gsmap_gc": "s", "gsmap_gc luu vuc con": "^"}
C_INK, C_INK2, C_GRID, C_SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
ROW_TITLE = {"r2": "R2 panel (train from 2010) — ΔNSE vs A0",
             "ext": "EXT panel (train from 1998) — ΔNSE vs E0"}


def _src(config: str) -> str:
    return config.split("+", 1)[1]


def _p(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def plot(folds: pl.DataFrame, summ: pl.DataFrame, out: Path = OUT_FIG) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = [g for g in ("r2", "ext") if g in folds["group"].unique().to_list()]
    fig, axes = plt.subplots(len(groups), 3, figsize=(15, 4.6 * len(groups)), sharey=True,
                             facecolor=C_SURF, squeeze=False)
    for i, g in enumerate(groups):
        x = folds.filter((pl.col("group") == g) & pl.col("dNSE").is_not_null())
        for j, h in enumerate(cfg.HORIZONS):
            ax = axes[i, j]
            ax.set_facecolor(C_SURF)
            ax.axvspan(2021.5, 2022.5, color=C_GRID, alpha=0.6, lw=0)
            ax.axhline(0, color=C_INK, lw=1.8, zorder=2)
            cs = sorted(x["config"].unique().to_list(), key=lambda c: list(LABELS).index(_src(c)))
            for c in cs:
                s = x.filter((pl.col("config") == c) & (pl.col("horizon") == h)).sort("fold")
                full, part = s.filter(pl.col("fold_type") == "du_nam"), s.filter(pl.col("fold_type") == "le")
                k = _src(c)
                st = summ.filter((pl.col("group") == g) & (pl.col("config") == c)
                                 & (pl.col("horizon") == h) & (pl.col("period") == MAIN))
                lab = LABELS[k]
                if st.height:
                    r = st.row(0, named=True)
                    lab += f": mean {r['dNSE_mean']:+.3f}, {r['n_win']}W/{r['n_loss']}L, {_p(r['p_wilcoxon'])}"
                ax.plot(full["fold"], full["dNSE"], color=COLORS[k], marker=MARKERS[k], ms=6,
                        lw=2, label=lab, zorder=3)
                if part.height:
                    ax.plot(part["fold"], part["dNSE"], ls="none", marker=MARKERS[k], ms=7,
                            mfc=C_SURF, mec=COLORS[k], mew=1.8, zorder=3)
            ax.set_title(f"{ROW_TITLE[g]}, h = {h} d", loc="left", fontsize=10.5, color=C_INK)
            ax.set_xticks(range(2013, 2027, 2))
            ax.grid(axis="y", color=C_GRID, lw=0.8)
            ax.set_axisbelow(True)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            ax.tick_params(colors=C_INK2, labelsize=9)
            ax.legend(fontsize=7.8, frameon=False, loc="lower left")
            if j == 0:
                ax.set_ylabel("ΔNSE (test year)", color=C_INK2)
            if i == len(groups) - 1:
                ax.set_xlabel("Test year", color=C_INK2)
    dv = folds["dNSE"].drop_nulls()
    axes[0, 0].set_ylim(dv.min() - 0.05, dv.max() + 0.012)      # chừa dải dưới cho chú thích
    axes[0, 0].annotate("GloFAS regime change\n(07/2022)", (2022, 1), xycoords=("data", "axes fraction"),
                        ha="center", va="top", fontsize=7.5, color=C_INK2)
    fig.suptitle("Walk-forward by test year (expanding train, 3-day gap): does satellite hourly rain "
                 "help LightGBM?", x=0.06, ha="left", fontsize=12, color=C_INK)
    fig.text(0.06, 0.935 if len(groups) > 1 else 0.89,
             "ΔNSE = NSE(config) − NSE(baseline), ensemble of 3 seeds. Lines: 13 full test years "
             "2013–2025 (legend: mean, wins/losses, Wilcoxon p). Hollow marker: 2026 Jan–Aug only, "
             "not in the summary.", fontsize=8.5, color=C_INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.93 if len(groups) > 1 else 0.87))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=C_SURF)
    plt.close(fig)
    return out


# ================================================================ main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--groups", nargs="+", choices=sa.GROUPS, default=list(sa.GROUPS))
    ap.add_argument("--years", nargs="+", type=int, default=[*YEARS, PARTIAL])
    ap.add_argument("--n-jobs", type=int, default=8, help="số luồng LightGBM mỗi lần fit")
    ap.add_argument("--out-dir", default=None, help="ghi 3 file đầu ra vào thư mục khác (chạy thử)")
    ap.add_argument("--plot-only", action="store_true")
    ap.add_argument("--lag-test", action="store_true",
                    help="chỉ chạy phép thử GSMaP-GC trễ 1 ngày → reports/wf_sat_lag1.csv")
    ap.add_argument("--nrt-test", action="store_true",
                    help="so GSMaP_NRT (JAXA) với bản chuẩn trên 2 nhóm → reports/wf_sat_nrt.csv")
    a = ap.parse_args(argv)

    if a.nrt_test:
        lgbm.PARAMS["n_jobs"] = a.n_jobs
        std = sa.load_sat("gsmap_gc").select("date", pl.col(f"gsmap_gc_{hf.PREFIX}sum_{hf.WHOLE}").alias("std"))
        nrt = sa.load_sat("gsmap_nrt").select("date", pl.col(f"gsmap_nrt_{hf.PREFIX}sum_{hf.WHOLE}").alias("nrt"))
        both = std.join(nrt, on="date").drop_nulls()
        fl = both.filter(pl.col("date").dt.month().is_in(rl.FLOOD_MONTHS))
        for lab, x in (("cả năm", both), ("mùa lũ", fl)):
            if x.height and x["std"].sum() > 0:
                print(f"Mưa ngày toàn lưu vực, NRT so với bản chuẩn ({lab}): {x.height} ngày, "
                      f"r = {x.select(pl.corr('std', 'nrt')).item():.3f}, "
                      f"tổng NRT/chuẩn = {x['nrt'].sum() / x['std'].sum():.3f}")
        rows = []
        for g in a.groups:
            rows += run_group(g, list(YEARS), loader=load_nrt)
        folds = pl.from_dicts(rows, infer_schema_length=None)
        if set(a.groups) != set(sa.GROUPS):
            folds = merge_other_groups(folds, OUT_NRT)
        folds.write_csv(OUT_NRT, float_precision=5)
        for name in folds["config"].unique(maintain_order=True):
            if name == "persistence" or folds.filter(pl.col("config") == name)["dNSE"].null_count() == \
                    folds.filter(pl.col("config") == name).height:
                continue
            for h in cfg.HORIZONS:
                d = folds.filter((pl.col("config") == name) & (pl.col("horizon") == h))["dNSE"].to_numpy()
                lo, hi = boot_mean_ci(d)
                print(f"{name:<18} h{h}: ΔNSE {d.mean():+.3f} [{lo:+.3f}; {hi:+.3f}] "
                      f"thắng/thua {(d > 0).sum()}/{(d < 0).sum()} p {wilcoxon_p(d):.3f}")
        print(f"→ {OUT_NRT}")
        return 0

    if a.lag_test:
        lgbm.PARAMS["n_jobs"] = a.n_jobs
        folds = pl.from_dicts(run_group("ext", list(YEARS), loader=load_ext_lag1),
                              infer_schema_length=None)
        folds.write_csv(OUT_LAG, float_precision=5)
        for name in ("E0+gsmap_gc", "E0+gsmap_gc_lag1"):
            for h in cfg.HORIZONS:
                d = folds.filter((pl.col("config") == name) & (pl.col("horizon") == h))["dNSE"].to_numpy()
                lo, hi = boot_mean_ci(d)
                print(f"{name:<18} h{h}: ΔNSE {d.mean():+.3f} [{lo:+.3f}; {hi:+.3f}] "
                      f"thắng/thua {(d > 0).sum()}/{(d < 0).sum()} p {wilcoxon_p(d):.3f}")
        print(f"→ {OUT_LAG}")
        return 0

    od = Path(a.out_dir) if a.out_dir else None
    f_folds = od / OUT_FOLDS.name if od else OUT_FOLDS
    f_summ = od / OUT_SUMMARY.name if od else OUT_SUMMARY
    f_fig = od / OUT_FIG.name if od else OUT_FIG
    if od:
        od.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    if a.plot_only:
        folds = pl.read_csv(f_folds, infer_schema_length=None, try_parse_dates=True)
    else:
        lgbm.PARAMS["n_jobs"] = a.n_jobs              # chỉ đổi số luồng, không đổi mô hình
        chk = fold_threshold(pl.read_parquet(sa.PANEL), date(1900, 1, 1), date.fromisoformat(cfg.VALID_END))
        print(f"Kiểm định nghĩa ngưỡng: split chính tính lại {chk:.1f} m³/s (risk_levels.csv 806.0)")
        print(f"Fold năm {a.years}; gap {GAP} ngày; seed {SEEDS}; n_jobs {a.n_jobs}")
        rows = []
        for g in a.groups:
            rows += run_group(g, a.years)
        folds = pl.from_dicts(rows, infer_schema_length=None)
        partial = set(a.groups) != set(sa.GROUPS)
        if partial:
            folds = merge_other_groups(folds, f_folds)
        folds.write_csv(f_folds, float_precision=5)
        print(f"→ {f_folds} ({folds.height} dòng)")

    if a.plot_only and f_summ.exists():      # giữ tóm tắt tính từ số chưa làm tròn
        summ = pl.read_csv(f_summ, infer_schema_length=None)
    else:
        summ = summarize(folds.filter(pl.col("group").is_in(a.groups)))
        if not a.plot_only and partial:     # tóm tắt nhóm không chạy lại: giữ bản cũ (số chưa làm tròn)
            summ = merge_other_groups(summ, f_summ)
        summ.write_csv(f_summ, float_precision=5)
    report(summ)
    print(f"\n→ {f_summ} ({summ.height} dòng)")
    print(f"→ {plot(folds, summ, f_fig)}")
    print(f"Thời gian chạy: {(time.time() - t0) / 60:.1f} phút")
    return 0


if __name__ == "__main__":
    sys.exit(main())
