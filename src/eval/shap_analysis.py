"""SHAP cho mô hình chính — đặc trưng quan trọng có hợp lý thuỷ văn không? (Report 3)

Mô hình: LightGBM cấu hình **E** của `ablation_ext` (feature Report 2 + độ ẩm
đất + đại diện hồ chứa + bão/khí áp/gió/ENSO), học trên train+valid (1997 →
2022-06-30), giải thích trên **tập test** (từ 2022-07-01). Cùng panel, cùng
tham số (`lgbm.params_for(h)`: L1 ở h=1, L2 ở h=2–3 — mô hình chính từ
21/10/2026; bản L1 cũ ở `reports/l1_ref/shap_importance.csv`), cùng mặt nạ dòng
như `ablation_ext` ⇒ NSE phải khớp `ablation_ext.csv` theo từng seed — đó là
phép kiểm đầu tiên trước khi đọc SHAP.

Ba câu hỏi:

1. Đặc trưng / nhóm nào gánh dự báo, ở mọi ngày và riêng ngày lũ (≥ mức 1)?
2. Chiều tác động có đúng vật lý không (mưa ↑ → dự báo ↑, bão gần → ↑ …)?
   Đo bằng Spearman giữa giá trị đặc trưng và SHAP của chính nó.
3. Từ h=1 → h=3, mô hình chuyển từ lưu lượng trễ sang nhóm nào?

SHAP tính trên log1p(Q) — đơn vị mô hình học — nên cộng được:
base + Σ SHAP = log1p(dự báo). +0,5 nghĩa là nhân (1 + Q) lên e^0,5 ≈ 1,65 lần.

    python -m src.eval.shap_analysis
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from src import config as cfg  # noqa: E402
from src.eval import metrics  # noqa: E402
from src.models import ablation_ext as abl  # noqa: E402
from src.models import lgbm  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANEL = abl.PANEL_EXT
PANEL_R2 = abl.PANEL                  # chỉ để lấy danh sách feature Report 2
ABL_CSV = cfg.ROOT / "reports" / "ablation_ext.csv"
RISK_CSV = cfg.ROOT / "reports" / "risk_levels.csv"
OUT = cfg.ROOT / "reports" / "shap_importance.csv"
FIGS = cfg.FIGURES / "report"

SEED = cfg.SEED                       # seed chính cho bảng đặc trưng và hình
SEEDS = abl.SEEDS                     # 3 seed — chỉ để kiểm độ ổn định của nhóm
TOP = 15
MIN_RHO = 0.1                         # |ρ| dưới mức này coi là không rõ chiều

VALID_END = date.fromisoformat(cfg.VALID_END)
TEST_START = date.fromisoformat(cfg.GLOFAS_REGIME_BREAK)

# Đỉnh GloFAS (ngày ĐÍCH của dự báo) của hai trận lũ có số xả hồ của tỉnh
# (FINDINGS_FACTORS §2): tỉnh báo lũ 15/10/2022 và 27/10/2025, GloFAS đạt đỉnh
# 16/10/2022 (1 967) và 30/10/2025 (2 903 — lớn nhất tập test).
PEAKS = (date(2022, 10, 16), date(2025, 10, 30))

DEP_FEATS = ("discharge", "rain_basin", "api", "sm_7_28",
             "storm_dist_km", "mslp_grad_north")

# Đại diện mỗi nhóm để kiểm chiều ở mức NHÓM: ρ(giá trị đại diện, Σ SHAP nhóm).
GROUP_PROXY = {"flow": "discharge", "rain": "rain_basin_roll3",
               "rain_long": "rain_basin_roll30", "soil_api": "api",
               "storm": "storm_dist_km", "synoptic": "mslp_grad_north", "enso": "oni_lag3"}
STORM_BINS = ((0, 300), (300, 800), (800, 1501), (1501, 1e9))  # 2 000 = không có bão
FLOOD_MONTHS = (9, 10, 11, 12)

# ---------------------------------------------------------------- nhóm feature

GROUP_ORDER = ("flow", "rain", "rain_long", "soil_api", "storm", "synoptic",
               "enso", "season")
GROUP_VI = {"flow": "Lưu lượng trễ", "rain": "Mưa ≤ 7 ngày",
            "rain_long": "Mưa dài / đại diện hồ", "soil_api": "Độ ẩm đất & API",
            "storm": "Bão / ATNĐ", "synoptic": "Khí áp, gió, ẩm (KK lạnh)",
            "enso": "ENSO", "season": "Mùa (lịch)"}
GROUP_EN = {"flow": "Lagged discharge", "rain": "Rain ≤ 7 d",
            "rain_long": "Long rain / reservoir proxy", "soil_api": "Soil moisture & API",
            "storm": "Tropical cyclone", "synoptic": "Pressure, wind, humidity",
            "enso": "ENSO", "season": "Calendar"}

_SEASON = {"doy_sin", "doy_cos", "month", "mua_lu"}


def feature_group(col: str) -> str:
    """Gán một feature vào đúng một nhóm cơ chế. Cột lạ ⇒ KeyError, không đoán."""
    if col == "discharge" or col.startswith(("discharge_lag", "q_diff")):
        return "flow"
    if col in abl.RESERVOIR_PROXY:
        return "rain_long"
    if col.startswith("rain_"):
        return "rain"
    if col == "api" or col in abl.SOIL:
        return "soil_api"
    if col.startswith("storm_"):
        return "storm"
    if col.startswith(("mslp_", "wind_", "rh_", "cloud_")):
        return "synoptic"
    if col.startswith("oni"):
        return "enso"
    if col in _SEASON:
        return "season"
    raise KeyError(f"feature chưa có nhóm: {col}")


def expected_sign(col: str) -> int:
    """Chiều vật lý kỳ vọng: feature ↑ ⇒ Q(t+h) ↑ (+1) hay ↓ (−1); 0 = không có
    kỳ vọng một chiều (lag Q khi đã có Q hôm nay, mã hoá lịch, tốc độ gió vô hướng)."""
    plus = {"discharge", "api", "sm_0_7", "sm_7_28", "sm_28_100",
            "storm_wind_kt", "mslp_grad_north", "wind_ne_hue", "wind_e_sea",
            "rh_hue", "cloud_hue", "mua_lu"}
    minus = {"et0", "storm_dist_km", "storm_approach_km", "mslp_hue", "mslp_sea",
             "mslp_hue_d1", "oni_lag3"}
    if col in plus or col.startswith("rain_"):
        return 1
    if col in minus:
        return -1
    return 0


def sign_check(rho: float, expected: int, min_rho: float = MIN_RHO) -> str:
    if expected == 0 or not np.isfinite(rho):
        return "khong_ky_vong"
    if abs(rho) < min_rho:
        return "yeu"
    return "dung" if np.sign(rho) == expected else "nguoc"


# ---------------------------------------------------------------- dữ liệu, mô hình

def features_e() -> list[str]:
    """Bộ feature cấu hình E, đúng thứ tự `ablation_ext` (thứ tự đổi ⇒ cây đổi)."""
    sch = pl.read_parquet_schema(PANEL_R2)
    base = [c for c, t in sch.items()
            if c not in {"date", "alert_level"} and not c.startswith("target_")
            and t.is_numeric()]
    return base + abl.SOIL + abl.RESERVOIR_PROXY + abl.CONTEXT


def load_panel() -> pl.DataFrame:
    return (pl.read_parquet(PANEL)
              .with_columns(pl.col("date").cast(pl.Date),
                            pl.col(pl.Float64).fill_nan(None)))


def split_rows(panel: pl.DataFrame, h: int, feats: list[str]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Như `lgbm.fit_predict`: bỏ dòng thiếu đích hoặc thiếu bất kỳ feature nào."""
    ok = pl.col(f"target_h{h}").is_not_null() & pl.all_horizontal(pl.col(feats).is_not_null())
    tr = panel.filter(ok & (pl.col("date") <= VALID_END))
    te = panel.filter(ok & (pl.col("date") >= TEST_START))
    return tr, te


def fit(tr: pl.DataFrame, h: int, feats: list[str], seed: int):
    from lightgbm import LGBMRegressor

    model = LGBMRegressor(**lgbm.params_for(h, random_state=seed))
    model.fit(tr.select(feats).to_pandas(), np.log1p(tr[f"target_h{h}"].to_numpy()))
    return model


def explain(model, X):
    """SHAP TreeExplainer (tree_path_dependent) → (values n×p, base value)."""
    import shap

    ex = shap.TreeExplainer(model)
    sv = np.asarray(ex.shap_values(X), dtype=float)
    return sv, float(np.ravel(ex.expected_value)[0])


# ---------------------------------------------------------------- bảng

def group_importance(sv: np.ndarray, feats: list[str]) -> dict[str, float]:
    """Mean |Σ SHAP trong nhóm|: cộng có dấu trước rồi mới lấy trị tuyệt đối, để
    các feature cùng nhóm triệt tiêu nhau (Q hôm nay +, Q hôm qua −) không bị
    thổi phồng thành quan trọng."""
    g = np.array([feature_group(f) for f in feats])
    return {k: float(np.abs(sv[:, g == k].sum(axis=1)).mean()) if (g == k).any() else 0.0
            for k in GROUP_ORDER}


def group_signed(sv: np.ndarray, feats: list[str]) -> dict[str, float]:
    g = np.array([feature_group(f) for f in feats])
    return {k: float(sv[:, g == k].sum(axis=1).mean()) if (g == k).any() else 0.0
            for k in GROUP_ORDER}


def _rho(x: np.ndarray, s: np.ndarray) -> float:
    if np.ptp(x) == 0 or np.ptp(s) == 0:
        return float("nan")
    return float(spearmanr(x, s).statistic)


def feature_table(sv: np.ndarray, X: np.ndarray, feats: list[str],
                  flood: np.ndarray) -> pl.DataFrame:
    a_all = np.abs(sv).mean(axis=0)
    a_fl = np.abs(sv[flood]).mean(axis=0)
    rho = [_rho(X[:, j], sv[:, j]) for j in range(len(feats))]
    exp = [expected_sign(f) for f in feats]
    return (pl.DataFrame({
        "name": feats, "group": [feature_group(f) for f in feats],
        "mean_abs_all": a_all, "share_all_pct": 100 * a_all / a_all.sum(),
        "mean_abs_flood": a_fl, "share_flood_pct": 100 * a_fl / a_fl.sum(),
        "mean_signed_flood": sv[flood].mean(axis=0),
        "rho_value_shap": rho, "expected_sign": exp,
        "sign_check": [sign_check(r, e) for r, e in zip(rho, exp)]})
        .with_columns(pl.col("mean_abs_all").rank("ordinal", descending=True)
                        .cast(pl.Int32).alias("rank_all"),
                      pl.col("mean_abs_flood").rank("ordinal", descending=True)
                        .cast(pl.Int32).alias("rank_flood"))
        .sort("rank_all"))


def group_table(sv: np.ndarray, X: np.ndarray, feats: list[str],
                flood: np.ndarray) -> pl.DataFrame:
    a_all, a_fl = group_importance(sv, feats), group_importance(sv[flood], feats)
    s_fl = group_signed(sv[flood], feats)
    tot_all, tot_fl = sum(a_all.values()), sum(a_fl.values())
    g = np.array([feature_group(f) for f in feats])
    rho, exp = [], []
    for k in GROUP_ORDER:
        p = GROUP_PROXY.get(k)
        rho.append(_rho(X[:, feats.index(p)], sv[:, g == k].sum(axis=1)) if p else float("nan"))
        exp.append(expected_sign(p) if p else 0)
    return pl.DataFrame({
        "name": list(GROUP_ORDER), "group": list(GROUP_ORDER),
        "mean_abs_all": [a_all[k] for k in GROUP_ORDER],
        "share_all_pct": [100 * a_all[k] / tot_all for k in GROUP_ORDER],
        "mean_abs_flood": [a_fl[k] for k in GROUP_ORDER],
        "share_flood_pct": [100 * a_fl[k] / tot_fl for k in GROUP_ORDER],
        "mean_signed_flood": [s_fl[k] for k in GROUP_ORDER],
        "rho_value_shap": rho, "expected_sign": exp,
        "sign_check": [sign_check(r, e) for r, e in zip(rho, exp)]})


def storm_bins(sv: np.ndarray, X: np.ndarray, feats: list[str]) -> list[tuple[str, int, float]]:
    """SHAP trung bình của cả nhóm bão theo khoảng cách bão – Huế hôm nay."""
    d = X[:, feats.index("storm_dist_km")]
    s = sv[:, [feature_group(f) == "storm" for f in feats]].sum(axis=1)
    out = []
    for lo, hi in STORM_BINS:
        m = (d >= lo) & (d < hi)
        out.append((f"{lo}–{hi:.0f} km" if hi < 1e9 else "không bão", int(m.sum()),
                    float(s[m].mean()) if m.any() else float("nan")))
    return out


# ---------------------------------------------------------------- hình

C_H = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}     # 3 slot đầu, đã kiểm CVD mọi cặp
C_FLOOD, C_GREY, C_DARK, INK = "#e34948", "#9a9893", "#3b3a37", "#1a1a1a"


def _save(fig, name: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"    → reports/figures/report/{name}")


def plot_beeswarm(sv: np.ndarray, base: float, X, h: int, n_flood: int) -> None:
    import shap

    exp = shap.Explanation(values=sv, base_values=np.full(len(sv), base),
                           data=X.to_numpy(), feature_names=list(X.columns))
    fig, ax = plt.subplots(figsize=(8.2, 7.2))
    shap.plots.beeswarm(exp, max_display=TOP, ax=ax, show=False, plot_size=None,
                        color_bar_label="Feature value (low → high)")
    ax.set_xlabel("SHAP value (log1p discharge units; +0.5 ≈ ×1.65)")
    ax.set_title(f"LightGBM config E, h = {h} d — SHAP on test 2022-07 → 2026-08\n"
                 f"n = {len(sv)} days ({n_flood} days ≥ risk level 1), top {TOP} features",
                 fontsize=10, loc="left")
    _save(fig, f"shap_beeswarm_h{h}_en.png")


def plot_bar_top(ft: pl.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.2))
    for ax, h in zip(axes, cfg.HORIZONS):
        d = ft.filter(pl.col("horizon") == h).sort("rank_all").head(TOP).reverse()
        y = np.arange(d.height)
        ax.barh(y + 0.2, d["mean_abs_all"], height=0.38, color=C_H[h], label="all test days")
        ax.barh(y - 0.2, d["mean_abs_flood"], height=0.38, color=C_DARK,
                label="days with Q(t+h) ≥ risk level 1")
        ax.set_yticks(y, d["name"].to_list(), fontsize=8.5)
        ax.set_title(f"h = {h} d", fontsize=11, loc="left")
        ax.set_xlabel("mean |SHAP| (log1p units)")
        ax.grid(axis="y", visible=False)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    fig.suptitle("Top 15 features by mean |SHAP| — LightGBM config E, test 2022-07 → 2026-08 "
                 "(ranked on all days)", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    _save(fig, "shap_bar_top15_en.png")


def plot_groups(gt: pl.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0), sharey=True)
    y = np.arange(len(GROUP_ORDER))[::-1]
    for ax, (col, title) in zip(axes, [("share_all_pct", "All test days"),
                                      ("share_flood_pct", "Days with Q(t+h) ≥ risk level 1")]):
        for i, h in enumerate(cfg.HORIZONS):
            d = gt.filter(pl.col("horizon") == h)
            main = d.filter(pl.col("seed") == SEED)
            v = np.array([main.filter(pl.col("group") == g)[col].item() for g in GROUP_ORDER])
            lo = np.array([d.filter(pl.col("group") == g)[col].min() for g in GROUP_ORDER])
            hi = np.array([d.filter(pl.col("group") == g)[col].max() for g in GROUP_ORDER])
            off = (1 - i) * 0.27
            ax.barh(y + off, v, height=0.25, color=C_H[h], label=f"h = {h} d")
            ax.errorbar(v, y + off, xerr=[v - lo, hi - v], fmt="none", ecolor=INK,
                        elinewidth=0.8, capsize=2)
        ax.set_title(title, fontsize=11, loc="left")
        ax.set_xlabel("share of grouped mean |SHAP| (%)")
        ax.grid(axis="y", visible=False)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_yticks(y, [GROUP_EN[g] for g in GROUP_ORDER])
    axes[1].legend(loc="lower right", frameon=False)
    fig.suptitle("Which mechanism carries the forecast? Grouped SHAP (signed sum within group, "
                 "then |·|); bars = seed 42, whiskers = range over seeds 42/7/2026",
                 x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout()
    _save(fig, "shap_groups_en.png")


def plot_dependence(sv: np.ndarray, X, feats: list[str], flood: np.ndarray, h: int) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, f in zip(axes.ravel(), DEP_FEATS):
        j = feats.index(f)
        x = X[f].to_numpy()
        ax.scatter(x[~flood], sv[~flood, j], s=9, color=C_GREY, alpha=0.5, lw=0,
                   label="other test days")
        ax.scatter(x[flood], sv[flood, j], s=22, color=C_FLOOD, edgecolor="white", lw=0.6,
                   label="Q(t+h) ≥ risk level 1")
        ax.axhline(0, color=INK, lw=0.6)
        if f in ("discharge", "api", "rain_basin"):
            ax.set_xscale("symlog", linthresh=10)
            ax.set_xlim(left=0)
        rho = _rho(x, sv[:, j])
        ax.set_title(f"{f}   (Spearman ρ value–SHAP = {rho:+.2f})", fontsize=9.5, loc="left")
        ax.set_xlabel(f)
        ax.set_ylabel("SHAP (log1p units)")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0, 0].legend(loc="upper left", frameon=False, fontsize=8)
    fig.suptitle(f"SHAP dependence — LightGBM config E, h = {h} d, test 2022-07 → 2026-08",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    _save(fig, f"shap_dependence_h{h}_en.png")


def plot_waterfall(sv_row: np.ndarray, base: float, x_row: np.ndarray, feats: list[str],
                   title: str, name: str) -> None:
    import shap

    exp = shap.Explanation(values=sv_row, base_values=base, data=x_row, feature_names=feats)
    shap.plots.waterfall(exp, max_display=14, show=False)
    fig = plt.gcf()
    fig.set_size_inches(9, 7.2)
    fig.axes[0].set_title(title, fontsize=9.5, loc="left")
    _save(fig, name)


# ---------------------------------------------------------------- chạy

def _thr1() -> float:
    r = pl.read_csv(RISK_CSV).filter(pl.col("muc") == "nguy_co_1")
    return float(r["nguong_m3s"].item())


def _abl_nse(h: int, seed: int) -> float:
    r = pl.read_csv(ABL_CSV).filter(pl.col("config").str.starts_with("E")
                                    & (pl.col("horizon") == h) & (pl.col("seed") == seed))
    return float(r["NSE"].item()) if r.height else float("nan")


def main() -> int:
    thr1 = _thr1()
    panel = load_panel()
    feats = features_e()
    print(f"Cấu hình E: {len(feats)} feature · ngưỡng mức 1 = {thr1:.0f} m³/s")

    feat_rows, group_rows, keep = [], [], {}
    for h in cfg.HORIZONS:
        tr, te = split_rows(panel, h, feats)
        X = te.select(feats).to_pandas()
        y = te[f"target_h{h}"].to_numpy()
        flood = y >= thr1
        for seed in SEEDS:
            model = fit(tr, h, feats, seed)
            raw = model.predict(X)
            yhat = np.clip(np.expm1(raw), 0, None)
            rep = metrics.regression_report(y, yhat)
            sv, base = explain(model, X)
            add_err = float(np.abs(base + sv.sum(axis=1) - raw).max())
            ref = _abl_nse(h, seed)
            print(f"h={h} seed={seed:<4} train {tr.height} · test {te.height} "
                  f"({int(flood.sum())} ngày ≥ mức 1) · NSE {rep['NSE']:.4f} "
                  f"(ablation_ext {ref:.4f}, lệch {rep['NSE'] - ref:+.1e}) · "
                  f"base {base:.3f} · |base+ΣSHAP−f(x)| max {add_err:.1e}")
            assert add_err < 1e-6, "SHAP không cộng lại bằng dự báo"
            meta = {"horizon": h, "seed": seed, "nse_test": rep["NSE"],
                    "nse_ablation_ext": ref, "peak_bias": rep["peak_bias"]}
            group_rows.append(group_table(sv, X.to_numpy(), feats, flood)
                              .with_columns(level=pl.lit("group"), **{k: pl.lit(v)
                                            for k, v in meta.items()}))
            if seed == SEED:
                feat_rows.append(feature_table(sv, X.to_numpy(), feats, flood)
                                 .with_columns(level=pl.lit("feature"), **{k: pl.lit(v)
                                               for k, v in meta.items()}))
                keep[h] = dict(sv=sv, base=base, X=X, y=y, yhat=yhat, raw=raw,
                               flood=flood, dates=te["date"].to_list(),
                               month=te["date"].dt.month().to_numpy(),
                               tr_q=tr["discharge"].to_numpy(),
                               tr_y=tr[f"target_h{h}"].to_numpy(),
                               train_max_pred=float(np.expm1(model.predict(
                                   tr.select(feats).to_pandas())).max()))

    ft = pl.concat(feat_rows)
    gt = pl.concat(group_rows)
    cols = ["level", "horizon", "seed", "name", "group", "mean_abs_all", "share_all_pct",
            "mean_abs_flood", "share_flood_pct", "mean_signed_flood", "rank_all",
            "rank_flood", "rho_value_shap", "expected_sign", "sign_check",
            "nse_test", "nse_ablation_ext", "peak_bias"]
    out = pl.concat([ft, gt], how="diagonal").select(cols)
    out.write_csv(OUT, float_precision=6)

    # ---- in bảng
    for h in cfg.HORIZONS:
        d = ft.filter(pl.col("horizon") == h)
        print(f"\n— h={h}: top {TOP} theo mean |SHAP| (seed {SEED}) —")
        print(d.head(TOP).select("rank_all", "name", "group", "mean_abs_all", "share_all_pct",
                                 "rank_flood", "mean_abs_flood", "rho_value_shap",
                                 "expected_sign", "sign_check"))
        print("  top 10 riêng ngày ≥ mức 1:",
              ", ".join(d.sort("rank_flood").head(10)["name"].to_list()))

    print("\nTỉ trọng NHÓM (% mean |Σ SHAP nhóm|), seed 42 [min–max 3 seed]:")
    for col in ("share_all_pct", "share_flood_pct"):
        print(f"  {col}")
        for g in GROUP_ORDER:
            parts = []
            for h in cfg.HORIZONS:
                d = gt.filter((pl.col("horizon") == h) & (pl.col("group") == g))
                v = d.filter(pl.col("seed") == SEED)[col].item()
                parts.append(f"h{h} {v:5.1f} [{d[col].min():4.1f}–{d[col].max():4.1f}]")
            print(f"    {GROUP_VI[g]:<28} " + "   ".join(parts))

    print("\nSHAP có dấu trung bình theo nhóm, ngày ≥ mức 1 (seed 42):")
    for h in cfg.HORIZONS:
        d = gt.filter((pl.col("horizon") == h) & (pl.col("seed") == SEED))
        k = keep[h]
        gap = np.log1p(k["y"][k["flood"]]) - k["raw"][k["flood"]]
        print(f"  h={h}: " + "  ".join(f"{g} {v:+.2f}" for g, v in
                                       zip(d["group"], d["mean_signed_flood"]))
              + f"  | base {k['base']:.2f} · thiếu so với thật (log) TB {gap.mean():+.2f}"
              f" · trung vị dự báo/thật {np.median(k['yhat'][k['flood']] / k['y'][k['flood']]):.2f}")

    print("\nKiểm chiều vật lý (top 20 mỗi horizon, ρ Spearman giá trị–SHAP):")
    for h in cfg.HORIZONS:
        d = ft.filter((pl.col("horizon") == h) & (pl.col("rank_all") <= 20))
        cnt = d.group_by("sign_check").len().sort("sign_check")
        print(f"  h={h}: " + ", ".join(f"{a} {b}" for a, b in cnt.iter_rows()))
        bad = d.filter(pl.col("sign_check") == "nguoc")
        for r in bad.iter_rows(named=True):
            print(f"      NGƯỢC: {r['name']} ρ={r['rho_value_shap']:+.2f} "
                  f"(kỳ vọng {r['expected_sign']:+d}, hạng {r['rank_all']})")

    print("\nKiểm chiều ở mức NHÓM: ρ(giá trị đại diện, Σ SHAP nhóm), seed 42:")
    for g, p in GROUP_PROXY.items():
        d = gt.filter((pl.col("group") == g) & (pl.col("seed") == SEED)).sort("horizon")
        print(f"  {GROUP_VI[g]:<28} vs {p:<18} " + "  ".join(
            f"h{r['horizon']} {r['rho_value_shap']:+.2f} {r['sign_check']}"
            for r in d.iter_rows(named=True)))

    print("\nSHAP nhóm bão theo khoảng cách bão – Huế hôm nay (seed 42):")
    for h in cfg.HORIZONS:
        k = keep[h]
        print(f"  h={h}: " + " · ".join(f"{lab} n={n} {m:+.3f}" for lab, n, m in
                                        storm_bins(k["sv"], k["X"].to_numpy(), feats)))

    print("\nρ giá trị–SHAP riêng mùa lũ (tháng 9–12) / ngày mưa 3 ngày ≥ 50 mm:")
    for h in cfg.HORIZONS:
        k = keep[h]
        wet = np.isin(k["month"], FLOOD_MONTHS)
        rainy = k["X"]["rain_basin_roll3"].to_numpy() >= 50
        parts = []
        for f in ("api", "sm_0_7", "sm_7_28", "sm_28_100", "rain_season_cum", "rain_basin_lag1"):
            x, s = k["X"][f].to_numpy(), k["sv"][:, feats.index(f)]
            parts.append(f"{f} {_rho(x[wet], s[wet]):+.2f}/{_rho(x[rainy], s[rainy]):+.2f}")
        print(f"  h={h} (n mùa lũ {int(wet.sum())}, n mưa {int(rainy.sum())}): "
              + "  ".join(parts))

    # ---- hình
    print("\nHình:")
    for h in cfg.HORIZONS:
        k = keep[h]
        plot_beeswarm(k["sv"], k["base"], k["X"], h, int(k["flood"].sum()))
        plot_dependence(k["sv"], k["X"], feats, k["flood"], h)
    plot_bar_top(ft)
    plot_groups(gt)

    k = keep[1]
    print(f"\nTrần dự báo h=1: max trên train {k['train_max_pred']:.0f} m³/s, "
          f"max trên test {k['yhat'].max():.0f} m³/s · min_child_samples "
          f"{lgbm.PARAMS['min_child_samples']} (mỗi lá ≥ ngần ấy ngày train)")
    for lo in (1000, 1500, 2000):
        m = k["tr_q"] >= lo
        print(f"  train Q(t) ≥ {lo}: {int(m.sum())} ngày, Q(t+1) > Q(t) ở "
              f"{(k['tr_y'][m] > k['tr_q'][m]).mean():.0%}, trung vị Q(t+1)/Q(t) "
              f"{np.median(k['tr_y'][m] / k['tr_q'][m]):.2f}")
    for peak in PEAKS:
        issue = peak - timedelta(days=1)
        if issue not in k["dates"]:
            print(f"  {issue} không có trong test h=1 — bỏ qua")
            continue
        i = k["dates"].index(issue)
        row = k["X"].iloc[i]
        sv_i = k["sv"][i]
        order = np.argsort(-np.abs(sv_i))[:8]
        print(f"\n  Phát {issue:%d/%m/%Y} → đích {peak:%d/%m/%Y}: thật {k['y'][i]:.0f}, "
              f"dự báo {k['yhat'][i]:.0f} m³/s, Q hôm nay {row['discharge']:.0f}; "
              f"base {k['base']:.2f} (= {np.expm1(k['base']):.0f} m³/s) + ΣSHAP "
              f"{sv_i.sum():+.2f} = {k['raw'][i]:.2f}; cần {np.log1p(k['y'][i]):.2f}")
        for j in order:
            print(f"      {feats[j]:<20} = {row.iloc[j]:>9.2f}   SHAP {sv_i[j]:+.3f}")
        grp = group_importance(sv_i[None, :], feats)
        sg = group_signed(sv_i[None, :], feats)
        print("      nhóm: " + "  ".join(f"{g} {sg[g]:+.2f}" for g in GROUP_ORDER if grp[g] > 0))
        print(f"      train có {int((k['tr_y'] >= k['y'][i]).sum())} / {len(k['tr_y'])} ngày "
              f"Q(t+1) ≥ {k['y'][i]:.0f} m³/s")
        title = (f"h = 1 d forecast issued {issue:%d %b %Y} for {peak:%d %b %Y} (GloFAS peak)\n"
                 f"GloFAS actual {k['y'][i]:.0f} m³/s · model {k['yhat'][i]:.0f} m³/s · "
                 f"discharge today {row['discharge']:.0f} m³/s — axis in log1p(Q) units")
        plot_waterfall(sv_i, k["base"], row.to_numpy(), feats, title,
                       f"shap_waterfall_{peak:%Y%m%d}_h1_en.png")

    print(f"\n→ {OUT.relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
