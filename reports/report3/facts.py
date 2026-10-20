"""Số liệu của Report 3, mỗi số đối chiếu với nguồn trong repo lúc build.

Ba loại mục trong sổ ``R``:

* ``csv``   — số tính lại từ ``reports/*.csv`` (hoặc file dữ liệu đã commit) rồi so
  với chuỗi văn bản định in. Lệch một ký tự là build hỏng: chạy lại thí nghiệm mà
  số đổi thì phải sửa văn bản, không được âm thầm in số cũ.
* ``claim`` — câu định tính ("mọi cấu hình DL đều thua ở h2–h3 giai đoạn
  2013–2021") được kiểm bằng một biểu thức trên CSV. Sai là build hỏng.
* ``doc``   — số chỉ có trong tài liệu (``docs/*.md``, docstring, văn bản pháp lý),
  không có CSV để kiểm. Ghi rõ nguồn để người đọc tra lại; danh sách in ra
  ``OUTLINE_VI.txt``.

Văn bản báo cáo lấy số qua ``R(key)`` nên không thể in một số chưa đăng ký.
Lớp kiểm thứ ba (trong ``build_report.py``) quét mọi số thập phân trong PDF: số nào
không có trong sổ là build hỏng.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"


# ======================================================================= sổ
class Registry:
    def __init__(self) -> None:
        self.val: dict[str, str] = {}
        self.src: dict[str, str] = {}
        self.kind: dict[str, str] = {}
        self.bad: list[str] = []
        self.used: set[str] = set()     # khoá thực sự được in vào PDF

    def _put(self, key: str, text: str, src: str, kind: str) -> None:
        if key in self.val:
            raise KeyError(f"khoá trùng: {key}")
        self.val[key], self.src[key], self.kind[key] = text, src, kind

    def csv(self, key: str, got: str, expect: str, src: str) -> None:
        if got != expect:
            self.bad.append(f"  {key}: văn bản {expect!r}, nguồn cho {got!r}  ({src})")
        self._put(key, expect, src, "csv")

    def claim(self, key: str, ok: bool, text: str, src: str) -> None:
        if not ok:
            self.bad.append(f"  {key}: câu định tính SAI với dữ liệu — {text}  ({src})")
        self._put(key, text, src, "claim")

    def doc(self, key: str, text: str, src: str) -> None:
        self._put(key, text, src, "doc")

    def __call__(self, key: str) -> str:
        """Số để in: dấu trừ thành gạch ngang en (font Times không có U+2212)."""
        self.used.add(key)
        return self.val[key].replace("-", "&#8211;")

    def numbers(self) -> set[str]:
        """Mọi số đã đăng ký, bỏ dấu, để lớp quét số trong PDF so khớp."""
        out: set[str] = set()
        for k, v in self.val.items():
            if self.kind[k] == "claim":
                continue
            for tok in v.replace(";", " ").split():
                out.add(tok.strip("+-[]()%"))
        return out

    def count(self, kind: str) -> int:
        return sum(1 for k in self.kind.values() if k == kind)


R = Registry()


# ================================================================ định dạng
def f(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}"


def sg(x: float, nd: int = 3) -> str:
    return f"{x:+.{nd}f}"


def n(x: float) -> str:
    return f"{int(round(x)):,}"


def ci(lo: float, hi: float, nd: int = 3) -> str:
    return f"[{lo:+.{nd}f}; {hi:+.{nd}f}]"


def _csv(name: str) -> pd.DataFrame:
    p = REP / name
    if not p.exists():
        raise SystemExit(f"Thiếu {p.relative_to(ROOT)} — chạy lại thí nghiệm tương ứng trước khi build.")
    return pd.read_csv(p)


# ---- thống kê qua fold: chép đúng walk_forward_sat.boot_mean_ci / wilcoxon_p
N_BOOT, SEED = 10_000, 42


def boot_mean_ci(d: np.ndarray) -> tuple[float, float]:
    d = d[np.isfinite(d)]
    rng = np.random.default_rng(SEED)
    means = d[rng.integers(0, len(d), (N_BOOT, len(d)))].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(lo), float(hi)


def wilcoxon_p(d: np.ndarray) -> float:
    from scipy.stats import wilcoxon
    d = d[np.isfinite(d)]
    return float(wilcoxon(d).pvalue)


# ================================================================== nạp số
def load(cfg) -> Registry:
    """Nạp và kiểm mọi số. Gọi một lần; lỗi gom vào ``R.bad`` để báo một lượt."""
    # ------------------------------------------------ cấu hình dự án (src/config.py)
    lat, lon = cfg.RIVER_POINTS["huong_kim_long"]
    R.csv("pt_lat", f(lat, 2), "16.45", "src/config.py RIVER_POINTS")
    R.csv("pt_lon", f(lon, 2), "107.50", "src/config.py RIVER_POINTS")
    R.csv("area_cfg", n(cfg.KIM_LONG_AREA_KM2), "1,540", "src/config.py KIM_LONG_AREA_KM2")
    al = cfg.ALERT_LEVELS_M["kim_long"]
    R.csv("bd1", f(al["BD1"], 1), "1.0", "src/config.py ALERT_LEVELS_M")
    R.csv("bd2", f(al["BD2"], 1), "2.0", "src/config.py ALERT_LEVELS_M")
    R.csv("bd3", f(al["BD3"], 1), "3.5", "src/config.py ALERT_LEVELS_M")
    q = cfg.FALLBACK_QUANTILES
    R.csv("q_lv3", f(100 * q["muc_3"], 1), "99.5", "src/config.py FALLBACK_QUANTILES")
    R.claim("q_lv12", (q["muc_1"], q["muc_2"]) == (0.95, 0.98), "95th and 98th percentiles",
            "src/config.py FALLBACK_QUANTILES")

    # tham số LightGBM đọc thẳng từ mã nguồn (không import để khỏi kéo lightgbm)
    tree = ast.parse((ROOT / "src" / "models" / "lgbm.py").read_text(encoding="utf-8"))
    params = next({kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords
                   if isinstance(kw.value, ast.Constant)}
                  for node in tree.body
                  if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PARAMS")
    R.csv("lgb_obj", params["objective"], "regression_l1", "src/models/lgbm.py PARAMS")
    R.csv("lgb_trees", str(params["n_estimators"]), "600", "src/models/lgbm.py PARAMS")
    R.csv("lgb_lr", f(params["learning_rate"], 2), "0.05", "src/models/lgbm.py PARAMS")
    R.csv("lgb_leaves", str(params["num_leaves"]), "31", "src/models/lgbm.py PARAMS")
    R.csv("lgb_mcs", str(params["min_child_samples"]), "30", "src/models/lgbm.py PARAMS")
    clf = (ROOT / "src" / "models" / "classifier.py").read_text(encoding="utf-8")
    R.csv("clf_thr", "0.5" if "(proba >= 0.5)" in clf else "?", "0.5", "src/models/classifier.py")

    # ------------------------------------------------ lưu vực (geojson + reservoir_info)
    bas = ROOT / "data" / "external" / "basins"
    kl = json.loads((bas / "huong_kim_long.geojson").read_text(encoding="utf-8"))
    R.csv("area_dem", n(kl["features"][0]["properties"]["area_km2"]), "1,543",
          "data/external/basins/huong_kim_long.geojson")
    sub = {ft["properties"]["name"]: ft["properties"]["area_km2"] for ft in
           json.loads((bas / "subbasins.geojson").read_text(encoding="utf-8"))["features"]}
    for k, name, exp in (("a_tt", "ta_trach_dam", "670"), ("a_bd", "binh_dien_dam", "507"),
                         ("a_ttb", "ta_trach_below_dam", "88"), ("a_htb", "huu_trach_below_dam", "185"),
                         ("a_tkl", "huong_tuan_kim_long", "93")):
        R.csv(k, n(sub[name]), exp, "data/external/basins/subbasins.geojson")
    ri = pd.read_csv(ROOT / "data" / "external" / "reservoir_info.csv").set_index("reservoir")
    tt, bd = ri.loc["Tả Trạch"], ri.loc["Bình Điền"]
    R.csv("ref_tt", n(tt["catchment_km2"]), "717", "data/external/reservoir_info.csv (QD 1606)")
    R.csv("ref_bd", n(bd["catchment_km2"]), "515", "data/external/reservoir_info.csv (QD 1606)")
    R.csv("cap_tt", n(tt["capacity_mcm"]), "646", "data/external/reservoir_info.csv")
    R.csv("cap_bd", n(bd["capacity_mcm"]), "424", "data/external/reservoir_info.csv")
    R.csv("dam_area", n(tt["catchment_km2"] + bd["catchment_km2"]), "1,232",
          "reservoir_info.csv: 717 + 515")
    R.csv("dtt_pct", f(100 * (sub["ta_trach_dam"] / tt["catchment_km2"] - 1), 1), "-6.5",
          "subbasins.geojson / reservoir_info.csv")
    R.csv("dbd_pct", f(100 * (sub["binh_dien_dam"] / bd["catchment_km2"] - 1), 1), "-1.6",
          "subbasins.geojson / reservoir_info.csv")

    # ------------------------------------------------ baseline + LightGBM (split chính)
    lg = _csv("lgbm_results.csv").set_index("horizon")
    bl = _csv("baseline_results.csv")
    exp_lg = {"nse": ("0.747", "0.420", "0.175"), "rmse": ("116.3", "176.1", "210.0"),
              "pb": ("-0.45", "-0.76", "-0.89")}
    for h in (1, 2, 3):
        R.csv(f"lgb_nse{h}", f(lg.loc[h, "NSE"]), exp_lg["nse"][h - 1], "reports/lgbm_results.csv")
        R.csv(f"lgb_rmse{h}", f(lg.loc[h, "RMSE"], 1), exp_lg["rmse"][h - 1], "reports/lgbm_results.csv")
        R.csv(f"lgb_pb{h}", f(lg.loc[h, "peak_bias"], 2), exp_lg["pb"][h - 1], "reports/lgbm_results.csv")
    R.csv("n_test1", n(lg.loc[1, "n"]), "1,522", "reports/lgbm_results.csv")
    exp_bl = {"persistence": (("0.542", "0.008", "-0.198"), ("156.4", "230.2", "253.1")),
              "climatology": (("0.097", "0.097", "0.096"), ("219.6", "219.7", "219.8")),
              "seasonal_naive": (("-0.434", "-0.434", "-0.435"), ("276.8", "276.8", "276.9")),
              "arima": (("-0.093", "-0.093", "-0.093"), ("241.6", "241.7", "241.8"))}
    for m, (en, er) in exp_bl.items():
        s = bl[bl.model == m].set_index("horizon")
        for h in (1, 2, 3):
            R.csv(f"{m}_nse{h}", f(s.loc[h, "NSE"]), en[h - 1], "reports/baseline_results.csv")
            R.csv(f"{m}_rmse{h}", f(s.loc[h, "RMSE"], 1), er[h - 1], "reports/baseline_results.csv")
    per = bl[bl.model == "persistence"].set_index("horizon")
    R.csv("per_pb1", f(per.loc[1, "peak_bias"], 2), "-0.36", "reports/baseline_results.csv")
    for h, e in zip((1, 2, 3), ("25.6", "23.5", "17.0")):
        R.csv(f"rmse_gain{h}", f(100 * (1 - lg.loc[h, "RMSE"] / per.loc[h, "RMSE"]), 1), e,
              "lgbm_results.csv / baseline_results.csv")

    # ------------------------------------------------ mức nguy cơ + bộ phân loại
    rk = _csv("risk_levels.csv").set_index("muc")
    for k, lv, e in (("thr1", "nguy_co_1", "806"), ("thr2", "nguy_co_2", "1,275"),
                     ("thr3", "nguy_co_3", "1,905")):
        R.csv(k, n(rk.loc[lv, "nguong_m3s"]), e, "reports/risk_levels.csv")
    for k, lv, e in (("npos1", "nguy_co_1", "31"), ("npos2", "nguy_co_2", "12"),
                     ("npos3", "nguy_co_3", "7")):
        R.csv(k, n(rk.loc[lv, "n_test_luy_ke"]), e, "reports/risk_levels.csv")
    R.csv("ntv3", n(rk.loc["nguy_co_3", "n_train_valid"]), "9", "reports/risk_levels.csv")
    cl = _csv("classifier_results.csv").set_index(["muc", "horizon"])
    exp_cl = {("nguy_co_1", 1): ("0.645", "0.200", "0.556", "0.671"),
              ("nguy_co_1", 2): ("0.355", "0.476", "0.268", "0.354"),
              ("nguy_co_1", 3): ("0.129", "0.789", "0.087", "0.153"),
              ("nguy_co_2", 1): ("0.333", "0.500", "0.250", "0.419"),
              ("nguy_co_2", 2): ("0.000", "1.000", "0.000", "0.082"),
              ("nguy_co_2", 3): ("0.000", "1.000", "0.000", "0.035")}
    for (lv, h), e in exp_cl.items():
        r = cl.loc[(lv, h)]
        tag = f"c{lv[-1]}h{h}"
        for col, ev in zip(("POD", "FAR", "CSI", "PR_AUC"), e):
            R.csv(f"{tag}_{col.lower()}", f(r[col]), ev, "reports/classifier_results.csv")
    r = cl.loc[("nguy_co_1", 1)]
    R.csv("c1h1_f1", f(r["F1"]), "0.714", "reports/classifier_results.csv")
    R.csv("c1h1_brier", f(r["Brier"], 4), "0.0095", "reports/classifier_results.csv")
    R.csv("c1h1_hits", n(r["hits"]), "20", "reports/classifier_results.csv")
    R.csv("c1h1_miss", n(r["misses"]), "11", "reports/classifier_results.csv")
    R.csv("c1h1_fa", n(r["false_alarms"]), "5", "reports/classifier_results.csv")
    R.csv("c1_ntrain", n(r["n_duong_train"]), "79", "reports/classifier_results.csv")

    # ------------------------------------------------ kịch bản B' (nhiễu mưa)
    sb = _csv("scenario_b_results.csv").set_index(["horizon", "sigma"])
    for h, e0, e1 in ((1, "0.742", "0.683"), (2, "0.422", "0.384"), (3, "0.167", "0.172")):
        R.csv(f"sb0_h{h}", f(sb.loc[(h, 0.0), "NSE"]), e0, "reports/scenario_b_results.csv")
        R.csv(f"sb1_h{h}", f(sb.loc[(h, 1.0), "NSE"]), e1, "reports/scenario_b_results.csv")
    R.csv("sb_drop1", f(sb.loc[(1, 0.0), "NSE"] - sb.loc[(1, 1.0), "NSE"]), "0.059",
          "reports/scenario_b_results.csv")

    # ------------------------------------------------ ablation A–E (split chính, 3 seed)
    ab = _csv("ablation_ext.csv")
    mean = ab.groupby(["config", "horizon"], sort=False).NSE.mean().unstack()
    cfgs = list(mean.index)
    exp_ab = {"A": ("0.745", "0.420", "0.172"), "B": ("0.766", "0.428", "0.176"),
              "C": ("0.757", "0.430", "0.181"), "D": ("0.756", "0.428", "0.186"),
              "E": ("0.747", "0.483", "0.199")}
    for c in cfgs:
        L = c.split()[0]
        for h in (1, 2, 3):
            R.csv(f"ab{L}{h}", f(mean.loc[c, h]), exp_ab[L][h - 1], "reports/ablation_ext.csv (mean 3 seeds)")
    A, B, D, E = (next(c for c in cfgs if c.startswith(x)) for x in "ABDE")
    R.csv("abBA1", sg(mean.loc[B, 1] - mean.loc[A, 1]), "+0.021", "reports/ablation_ext.csv")
    R.csv("abED2", sg(mean.loc[E, 2] - mean.loc[D, 2]), "+0.055", "reports/ablation_ext.csv")
    R.csv("abED3", sg(mean.loc[E, 3] - mean.loc[D, 3]), "+0.014", "reports/ablation_ext.csv")
    R.csv("abEA2", sg(mean.loc[E, 2] - mean.loc[A, 2]), "+0.063", "reports/ablation_ext.csv")
    R.csv("ab_sd", f(ab.groupby(["config", "horizon"]).NSE.std().max()), "0.009", "reports/ablation_ext.csv")
    ntr = ab.groupby("config", sort=False).n_train.first()
    R.csv("ntrA", n(ntr[A]), "4,550", "reports/ablation_ext.csv")
    R.csv("ntrB", n(ntr[B]), "9,298", "reports/ablation_ext.csv")
    R.csv("ntrE", n(ntr[E]), "9,283", "reports/ablation_ext.csv")
    rg = _csv("regime_check.csv").set_index(["phep_do", "che_do"])
    R.csv("q_max_test", n(rg.loc[("tat_ca_ngay", "sau"), "cuc_dai"]), "2,903", "reports/regime_check.csv")
    nf = ab.groupby("config", sort=False).n_feat.first()
    for L, e in zip("ACDE", ("66", "70", "73", "88")):
        R.csv(f"nf{L}", n(nf[next(c for c in cfgs if c.startswith(L))]), e, "reports/ablation_ext.csv")
    pbm = ab.groupby(["config", "horizon"]).peak_bias.mean()
    R.csv("ab_pbmax", f(pbm.max(), 2), "-0.42", "reports/ablation_ext.csv")
    R.csv("ab_pbmin", f(pbm.min(), 2), "-0.88", "reports/ablation_ext.csv")

    # ------------------------------------------------ đặc trưng mưa giờ ERA5 (split riêng)
    ah = _csv("ablation_hourly.csv")
    t = ah[ah.phase == "test"]
    hm = t.groupby(["config", "horizon"], sort=False).NSE.mean().unstack()
    names = {"A": "A panel goc", "B0": "B0 +tong ngay (doi chung)", "B": "B +gio toan luu vuc",
             "C": "C +gio luu vuc con"}
    exp_h = {"A": ("0.715", "0.416", "0.168"), "B0": ("0.726", "0.421", "0.167"),
             "B": ("0.723", "0.431", "0.183"), "C": ("0.722", "0.429", "0.184")}
    for L, c in names.items():
        for h in (1, 2, 3):
            R.csv(f"hr{L}{h}", f(hm.loc[c, h]), exp_h[L][h - 1], "reports/ablation_hourly.csv")

    def seed_gain(c: str, h: int) -> list[str]:
        x = t[(t.config == c) & (t.horizon == h)].set_index("seed").NSE
        a = t[(t.config == names["A"]) & (t.horizon == h)].set_index("seed").NSE
        return [sg(x[s] - a[s]) for s in (42.0, 7.0, 2026.0)]
    for i, e in enumerate(("+0.016", "+0.008", "+0.022")):
        R.csv(f"hrB3_s{i}", seed_gain(names["B"], 3)[i], e, "reports/ablation_hourly.csv (per seed)")
    for i, e in enumerate(("+0.004", "+0.041", "+0.001")):
        R.csv(f"hrB2_s{i}", seed_gain(names["B"], 2)[i], e, "reports/ablation_hourly.csv (per seed)")

    # ------------------------------------------------ so sánh nguồn mưa (mùa lũ 2015–2025)
    rs = _csv("rain_source_compare.csv")
    rs = rs[rs.period == "mua_lu_9_12"].set_index("source")
    for k, s, e in (("rr_imerg", "imerg", "0.90"), ("rr_gsmap", "gsmap", "0.74"),
                    ("rr_gc", "gsmap_gc", "1.14")):
        R.csv(k, f(rs.loc[s, "ratio_vs_era5"], 2), e, "reports/rain_source_compare.csv")
    R.csv("rq_era5", f(rs.loc["era5", "r_r3d_q_next"], 2), "0.78", "reports/rain_source_compare.csv")
    R.csv("rq_imerg", f(rs.loc["imerg", "r_r3d_q_next"], 2), "0.69", "reports/rain_source_compare.csv")
    R.csv("rq_gc", f(rs.loc["gsmap_gc", "r_r3d_q_next"], 2), "0.69", "reports/rain_source_compare.csv")

    # ------------------------------------------------ mưa vệ tinh: một lần chia
    hs = _csv("ablation_hourly_sat.csv")
    hs = hs[(hs.phase == "test") & (hs.seed == "mean3")].set_index(["config", "horizon"])
    R.csv("ss_im2", sg(hs.loc[("E0+imerg", 2), "dNSE"]), "+0.018", "reports/ablation_hourly_sat.csv")
    R.csv("ss_im3", sg(hs.loc[("E0+imerg", 3), "dNSE"]), "+0.017", "reports/ablation_hourly_sat.csv")

    # ------------------------------------------------ mưa vệ tinh: walk-forward 13 fold
    ws = _csv("wf_sat_summary.csv")
    ws = ws[ws.period == "chinh_2013_2025"].set_index(["group", "config", "horizon"])
    E0 = "E0 (=E ablation_ext)"
    for h, e in zip((1, 2, 3), ("0.761", "0.398", "0.170")):
        R.csv(f"wfE0_{h}", f(ws.loc[("ext", E0, h), "NSE_mean"]), e, "reports/wf_sat_summary.csv")
    for h, e in zip((1, 2, 3), ("0.744", "0.336", "0.121")):
        R.csv(f"wfA0_{h}", f(ws.loc[("r2", "A0 panel goc", h), "NSE_mean"]), e, "reports/wf_sat_summary.csv")
    R.csv("wf_nfold", n(ws.loc[("ext", E0, 1), "n_folds"]), "13", "reports/wf_sat_summary.csv")

    def wrow(key: str, g: str, c: str, h: int, e_mean: str, e_ci: str | None, e_wl: str,
             e_p: str | None, pnd: int = 2) -> None:
        r = ws.loc[(g, c, h)]
        R.csv(f"{key}_m", sg(r["dNSE_mean"]), e_mean, "reports/wf_sat_summary.csv")
        if e_ci:
            R.csv(f"{key}_ci", ci(r["dNSE_ci_lo"], r["dNSE_ci_hi"]), e_ci, "reports/wf_sat_summary.csv")
        R.csv(f"{key}_wl", f"{int(r['n_win'])}/{int(r['n_loss'])}", e_wl, "reports/wf_sat_summary.csv")
        if e_p:
            R.csv(f"{key}_p", f(r["p_wilcoxon"], pnd), e_p, "reports/wf_sat_summary.csv")

    wrow("gc1", "ext", "E0+gsmap_gc", 1, "-0.001", "[-0.011; +0.010]", "8/5", "1.00")
    wrow("gc2", "ext", "E0+gsmap_gc", 2, "+0.017", "[-0.002; +0.036]", "8/5", "0.22")
    wrow("gc3", "ext", "E0+gsmap_gc", 3, "+0.016", "[+0.007; +0.024]", "11/2", "0.005", 3)
    wrow("im1", "ext", "E0+imerg", 1, "+0.001", "[-0.005; +0.008]", "8/5", "0.68")
    wrow("im2", "ext", "E0+imerg", 2, "+0.010", "[-0.002; +0.021]", "9/4", "0.09")
    wrow("im3", "ext", "E0+imerg", 3, "+0.008", "[+0.001; +0.016]", "8/5", "0.08")
    wrow("agc1", "r2", "A0+gsmap_gc", 1, "+0.006", "[+0.000; +0.011]", "9/4", "0.07")
    wrow("agc2", "r2", "A0+gsmap_gc", 2, "+0.032", "[+0.023; +0.041]", "13/0", "0.0002", 4)
    wrow("agc3", "r2", "A0+gsmap_gc", 3, "+0.025", "[+0.013; +0.038]", "12/1", "0.005", 3)
    e0, gc = ws.loc[("ext", E0, 1)], ws.loc[("ext", "E0+gsmap_gc", 1)]
    R.csv("csi_e0", f(e0["CSI1"]), "0.450", "reports/wf_sat_summary.csv")
    R.csv("csi_gc", f(gc["CSI1"]), "0.484", "reports/wf_sat_summary.csv")
    R.csv("fa_e0", n(e0["false_alarms1"]), "24", "reports/wf_sat_summary.csv")
    R.csv("fa_gc", n(gc["false_alarms1"]), "19", "reports/wf_sat_summary.csv")
    R.csv("pos_wf", n(e0["n_pos1"]), "105", "reports/wf_sat_summary.csv")
    wsf = _csv("wf_sat_summary.csv")
    fc = wsf[(wsf.period == "forecast_2023_2025") & wsf.p_wilcoxon.notna()]
    R.csv("fc_nfold", n(fc.n_folds.max()), "3", "reports/wf_sat_summary.csv")
    R.csv("fc_pmin", f(fc.p_wilcoxon.min(), 2), "0.25", "reports/wf_sat_summary.csv")

    # ------------------------------------------------ phép thử độ trễ (tính lại từ fold)
    lag = _csv("wf_sat_lag1.csv")
    exp_lag = {("E0+gsmap_gc", 1): ("+0.004", "[-0.002; +0.010]", "10/3", "0.127"),
               ("E0+gsmap_gc", 2): ("+0.016", "[-0.001; +0.034]", "8/5", "0.146"),
               ("E0+gsmap_gc", 3): ("+0.012", "[+0.002; +0.023]", "10/3", "0.033"),
               ("E0+gsmap_gc_lag1", 1): ("+0.001", "[-0.007; +0.008]", "8/5", "0.542"),
               ("E0+gsmap_gc_lag1", 2): ("-0.003", "[-0.007; +0.002]", "4/9", "0.244"),
               ("E0+gsmap_gc_lag1", 3): ("-0.002", "[-0.009; +0.004]", "6/7", "0.685")}
    for (c, h), (em, eci, ewl, ep) in exp_lag.items():
        d = lag[(lag.config == c) & (lag.horizon == h)].sort_values("fold").dNSE.to_numpy(float)
        tag = f"lag{'1' if c.endswith('lag1') else '0'}_{h}"
        lo, hi = boot_mean_ci(d)
        R.csv(f"{tag}_m", sg(d.mean()), em, "reports/wf_sat_lag1.csv (13 folds)")
        R.csv(f"{tag}_ci", ci(lo, hi), eci, "reports/wf_sat_lag1.csv (bootstrap over folds)")
        R.csv(f"{tag}_wl", f"{(d > 0).sum()}/{(d < 0).sum()}", ewl, "reports/wf_sat_lag1.csv")
        R.csv(f"{tag}_p", f(wilcoxon_p(d)), ep, "reports/wf_sat_lag1.csv (Wilcoxon)")
    R.csv("lag_nfold", n(lag.fold.nunique()), "13", "reports/wf_sat_lag1.csv")

    # ------------------------------------------------ DL: walk-forward so với LightGBM
    wd = _csv("wf_dl_summary.csv")
    wv = wd[wd.table == "vs_lightgbm"].set_index(["period", "model", "horizon"])
    P = "2013-2025"
    for h, e in zip((1, 2, 3), ("0.743", "0.334", "0.118")):
        R.csv(f"dl_lgb{h}", f(wv.loc[(P, "lightgbm", h), "NSE_mean"]), e, "reports/wf_dl_summary.csv")
    exp_dl = {("lstm_L30_mse", 1): ("+0.021", "[-0.014; +0.058]", "8/5", "0.38"),
              ("lstm_L30_mse", 2): ("-0.025", "[-0.117; +0.032]", "7/6", "0.74"),
              ("lstm_L30_mse", 3): ("-0.026", "[-0.101; +0.021]", "7/6", "1.00"),
              ("lstm_L30_peak", 1): ("-0.007", "[-0.065; +0.037]", "8/5", "0.68"),
              ("lstm_L30_peak", 2): ("-0.107", "[-0.239; -0.008]", "5/8", "0.17"),
              ("lstm_L30_peak", 3): ("-0.229", "[-0.411; -0.073]", "5/8", "0.033"),
              ("mlp_lag_peak", 1): ("+0.000", "[-0.031; +0.037]", "5/8", "0.79"),
              ("mlp_lag_peak", 2): ("-0.065", "[-0.142; +0.002]", "5/8", "0.15"),
              ("mlp_lag_peak", 3): ("-0.118", "[-0.255; -0.015]", "6/7", "0.094")}
    for (m, h), (em, eci, ewl, ep) in exp_dl.items():
        r = wv.loc[(P, m, h)]
        tag = f"{m.split('_')[0]}{'P' if m.endswith('peak') else 'M'}{h}"
        R.csv(f"{tag}_m", sg(r["dNSE_mean"]), em, "reports/wf_dl_summary.csv")
        R.csv(f"{tag}_ci", ci(r["dNSE_ci_lo"], r["dNSE_ci_hi"]), eci, "reports/wf_dl_summary.csv")
        R.csv(f"{tag}_wl", f"{int(r['wins'])}/{int(r['losses'])}", ewl, "reports/wf_dl_summary.csv")
        nd = 3 if ep.startswith("0.0") else 2
        R.csv(f"{tag}_p", f(r["wilcoxon_p"], nd), ep, "reports/wf_dl_summary.csv")
    for k, m, e in (("csi_lgb", "lightgbm", "0.44"), ("csi_lstmM", "lstm_L30_mse", "0.49"),
                    ("csi_lstmP", "lstm_L30_peak", "0.49"), ("csi_mlpP", "mlp_lag_peak", "0.49")):
        R.csv(k, f(wv.loc[(P, m, 1), "CSI"], 2), e, "reports/wf_dl_summary.csv (pooled, h=1)")
    for k, m, e in (("pod_lgb", "lightgbm", "0.51"), ("pod_lstmM", "lstm_L30_mse", "0.59"),
                    ("pod_mlpP", "mlp_lag_peak", "0.63")):
        R.csv(k, f(wv.loc[(P, m, 1), "POD"], 2), e, "reports/wf_dl_summary.csv (pooled, h=1)")
    for k, m, e in (("pb_lgb", "lightgbm", "-0.38"), ("pb_mlpP", "mlp_lag_peak", "-0.21"),
                    ("pb_lstmP", "lstm_L30_peak", "-0.26")):
        R.csv(k, f(wv.loc[(P, m, 1), "peak_bias_mean"], 2), e, "reports/wf_dl_summary.csv")
    dls = wv.loc[P].reset_index()
    dls = dls[dls.model.isin(["lstm_L30_mse", "lstm_L30_peak", "mlp_lag_peak"])]
    lgs = wv.loc[P].reset_index()
    lgs = lgs[lgs.model == "lightgbm"]
    R.csv("sd_lgb", f(lgs.NSE_seed_sd_mean.max(), 2), "0.01", "reports/wf_dl_summary.csv")
    R.csv("sd_dl_lo", f(dls.NSE_seed_sd_mean.min(), 2), "0.03", "reports/wf_dl_summary.csv")
    R.csv("sd_dl_hi", f(dls.NSE_seed_sd_mean.max(), 2), "0.20", "reports/wf_dl_summary.csv")
    th = wd[wd.table == "threads"]
    R.csv("thr_rng", f(th.thread_range.max()), "0.028", "reports/wf_dl_summary.csv (threads)")
    R.claim("lstm_thr0", bool((th[th.model == "lstm_L30_mse"].thread_range == 0).all()),
            "LSTM identical for 1, 2 and 4 threads", "reports/wf_dl_summary.csv (threads)")
    early = wv.loc["2013-2021"].reset_index()
    early = early[early.model.isin(["lstm_L30_mse", "lstm_L30_peak", "mlp_lag_peak"])
                  & early.horizon.isin([2, 3])]
    R.claim("dl_early_neg", bool((early.dNSE_mean < 0).all()),
            "every DL model loses on average at h = 2 and h = 3 in 2013-2021",
            "reports/wf_dl_summary.csv (period 2013-2021)")
    late = wv.loc["2023-2025"].reset_index()
    late = late[(late.model == "mlp_lag_peak") & late.horizon.isin([2, 3])]
    R.claim("dl_late_pos", bool((late.dNSE_mean > 0).all()),
            "peak-weighted MLP ahead at h = 2 and h = 3 in 2023-2025",
            "reports/wf_dl_summary.csv (period 2023-2025)")

    # DL một lần chia (học trên train+valid, test >= 2022-07)
    dr = _csv("dl_results.csv")
    dr = dr[(dr.fit == "train+valid") & (dr.split == "test")].set_index(["model", "horizon"])
    sel = "lstm_L14_full_mse"
    R.claim("dl_sel_valid", bool(dr.loc[(sel, 1), "best_lstm_on_valid"]),
            "LSTM L=14 on all panel columns is the configuration selected on validation",
            "reports/dl_results.csv")
    for h, e in zip((1, 2, 3), ("0.709", "0.404", "0.171")):
        R.csv(f"dlsel{h}", f(dr.loc[(sel, h), "NSE_mean"]), e, "reports/dl_results.csv")
    R.claim("dl_sel_loses", all(dr.loc[(sel, h), "NSE_mean"] < dr.loc[("lightgbm", h), "NSE_mean"]
                                for h in (1, 2, 3)),
            "selected LSTM below LightGBM at all horizons (single split)", "reports/dl_results.csv")
    R.csv("dlmlp2", f(dr.loc[("mlp_lag_peak", 2), "NSE_mean"]), "0.490", "reports/dl_results.csv")
    R.csv("dl_lgbcsi", f(dr.loc[("lightgbm", 1), "CSI_mean"]), "0.394", "reports/dl_results.csv")
    models = set(dr.index.get_level_values("model"))
    R.csv("n_dlcfg", n(sum(m.startswith(("lstm", "mlp")) for m in models)), "8",
          "reports/dl_results.csv (configurations)")

    # ------------------------------------------------ Spark (chỉ nhắc ngắn)
    sp = _csv("spark_results.csv").set_index(["model", "horizon"])
    R.csv("sp_gbt1", f(sp.loc[("spark_gbt", 1), "NSE"]), "0.699", "reports/spark_results.csv")
    R.csv("sp_rf1", f(sp.loc[("spark_rf", 1), "NSE"]), "0.687", "reports/spark_results.csv")
    eb = _csv("spark/etl_benchmark.csv")
    c2 = eb[eb.tag == "cluster_2w_8c"].seconds_etl
    pw = eb[eb.tag == "windows_polars"].seconds_etl
    R.csv("etl_c2_lo", f(c2.min(), 1), "40.5", "reports/spark/etl_benchmark.csv")
    R.csv("etl_c2_hi", f(c2.max(), 1), "41.2", "reports/spark/etl_benchmark.csv")
    R.csv("etl_pl_lo", f(pw.min(), 1), "3.4", "reports/spark/etl_benchmark.csv")
    R.csv("etl_pl_hi", f(pw.max(), 1), "3.7", "reports/spark/etl_benchmark.csv")
    R.csv("etl_rows_in", n(eb.rows_in.iloc[0]), "6,544,896", "reports/spark/etl_benchmark.csv")
    R.csv("etl_rows_out", n(eb.rows_out.iloc[0]), "272,704", "reports/spark/etl_benchmark.csv")

    # ------------------------------------------------ R1: GloFAS trước / sau khi có hồ
    r1 = _csv("reservoir_dam_era_test.csv").set_index("metric")
    exp_r1 = {"low_flow_30d": ("29.7", "26.5", "-10.7", "0.42", 1),
              "runoff_ratio": ("0.857", "0.875", "+2.2", "0.91", 3),
              "flashiness_rb": ("0.435", "0.441", "+1.3", "0.64", 3),
              "response": ("5.80", "5.98", "+3.2", "0.64", 2)}
    for m, (e0, e1, ec, ep, nd) in exp_r1.items():
        r = r1.loc[m]
        R.csv(f"r1_{m}_pre", f(r["median_pre"], nd), e0, "reports/reservoir_dam_era_test.csv")
        R.csv(f"r1_{m}_post", f(r["median_post"], nd), e1, "reports/reservoir_dam_era_test.csv")
        R.csv(f"r1_{m}_chg", sg(r["change_pct"], 1), ec, "reports/reservoir_dam_era_test.csv")
        R.csv(f"r1_{m}_p", f(r["p_mannwhitney"], 2), ep, "reports/reservoir_dam_era_test.csv")
    R.csv("r1_npre", n(r1.loc["low_flow_30d", "n_pre"]), "11", "reports/reservoir_dam_era_test.csv")
    R.csv("r1_npost", n(r1.loc["low_flow_30d", "n_post"]), "13", "reports/reservoir_dam_era_test.csv")
    R.csv("r1_ev_pre", n(r1.loc["response", "n_pre"]), "25", "reports/reservoir_dam_era_test.csv")
    R.csv("r1_ev_post", n(r1.loc["response", "n_post"]), "37", "reports/reservoir_dam_era_test.csv")
    R.claim("r1_none_sig", bool((r1.p_mannwhitney > 0.05).all()),
            "no index changes significantly (all p > 0.05)", "reports/reservoir_dam_era_test.csv")

    # ------------------------------------------------ R2: số hồ công bố so với GloFAS
    rel = pd.read_csv(ROOT / "data" / "external" / "reservoir_releases.csv")
    R.csv("rel_rows", n(len(rel)), "132", "data/external/reservoir_releases.csv")
    R.csv("rel_days", n(rel["date"].nunique()), "57", "data/external/reservoir_releases.csv")
    R.csv("rel_y0", rel["date"].min()[:4], "2016", "data/external/reservoir_releases.csv")
    rc = _csv("reservoir_release_check.csv")

    def frac(col: str) -> str:
        s = rc[col].dropna().astype(str).str.lower()
        return f"{(s == 'true').sum()}/{len(s)}"
    R.csv("r2_rel", frac("below_release"), "11/24", "reports/reservoir_release_check.csv")
    R.csv("r2_inf", frac("below_inflow"), "14/23", "reports/reservoir_release_check.csv")
    rc = rc.set_index("date")
    for d, k, e in (("2022-10-15", "q_release_upstream_min", "3,672"),
                    ("2022-10-15", "q_inflow_upstream", "13,787"),
                    ("2022-10-15", "glofas_best", "1,967"),
                    ("2025-10-27", "q_release_upstream_min", "3,669"),
                    ("2025-10-27", "q_inflow_upstream", "13,433"),
                    ("2025-10-27", "glofas_best", "2,022"),
                    ("2023-11-15", "q_release_upstream_min", "3,650"),
                    ("2023-11-15", "glofas_best", "584")):
        R.csv(f"r2_{d}_{k}", n(rc.loc[d, k]), e, "reports/reservoir_release_check.csv")

    # ------------------------------------------------ độ quan trọng theo gain (h = 2)
    gi = _csv("lgbm_importance.csv")
    top2 = set(gi[gi.horizon == 2].nlargest(2, "gain").feature)
    R.claim("gain_doy", top2 == {"doy_sin", "doy_cos"},
            "the two seasonal encodings rank first and second by split gain at h = 2",
            "reports/lgbm_importance.csv")

    # ------------------------------------------------ ánh xạ H-Q (nếu có file dữ liệu)
    tm = ROOT / "data" / "processed" / "threshold_mapping.csv"
    if tm.exists():
        m = pd.read_csv(tm)
        R.csv("hq_r2fit", f(m.r2.iloc[0]), "0.629", "data/processed/threshold_mapping.csv")
        R.csv("hq_nfit", n(m.n_fit.iloc[0]), "7", "data/processed/threshold_mapping.csv")
    else:
        R.doc("hq_r2fit", "0.629", "docs/FINDINGS_EVENTS.md §5 (file dữ liệu không có trên máy)")
        R.doc("hq_nfit", "7", "docs/FINDINGS_EVENTS.md §5")

    # ================================================== số chỉ có trong tài liệu
    D = R.doc
    D("area_sys", "2,830", "docs/FINDINGS_GRID.md §3 (UNESCO-IHP Catalogue of Rivers Vol. V, Viet Nam-8)")
    D("area_bo", "938", "docs/FINDINGS_GRID.md §3 (UNESCO-IHP)")
    D("area_dbl", "3,768", "docs/FINDINGS_GRID.md §3 (2,830 + 938, đếm trùng sông Bồ)")
    D("q_cell", "120.7", "docs/FINDINGS_GRID.md Phần 2 §3")
    D("spec_lo", "0.060", "docs/FINDINGS_GRID.md Phần 2 §3")
    D("spec_hi", "0.080", "docs/FINDINGS_GRID.md Phần 2 §3")
    D("imp_lo", "1,508", "docs/FINDINGS_GRID.md Phần 2 §3")
    D("imp_hi", "2,011", "docs/FINDINGS_GRID.md Phần 2 §3")
    D("cov_era5", "92.5", "docs/FINDINGS_HOURLY_FINEGRID.md §3")
    D("pccs_nov", "0.073", "docs/FINDINGS_HOURLY_FINEGRID.md §2 (PERSIANN-CCS 11/2020)")
    D("storms", "417", "docs/FINDINGS_FACTORS.md §1 (IBTrACS)")
    D("storm_km", "1,500", "docs/FINDINGS_FACTORS.md §1")
    D("hq_r2", "0.18", "docs/FINDINGS_REGIME.md §4 (R² = 0,184, 12 đợt lũ)")
    D("hq_n", "12", "docs/FINDINGS_REGIME.md §4")
    D("hq_bias", "-1.94", "docs/FINDINGS_EVENTS.md §5 (5 đợt lũ sau 07/2022)")
    D("noise", "0.01", "docs/FINDINGS_MODEL.md §6 (nhiễu 1e-13 đổi NSE ±0,01)")
    D("lat_gsmap", "27", "docs/FINDINGS_HOURLY_FINEGRID.md §12.3 (kiểm 20/10/2026)")
    D("lat_imerg", "38", "docs/FINDINGS_HOURLY_FINEGRID.md §12.3")
    D("lat_nrt", "4.7", "src/ingest/gsmap_nrt.py docstring")
    D("nrt_r_lo", "0.6", "src/ingest/gsmap_nrt.py docstring (tương quan giờ NRT/chuẩn)")
    D("nrt_r_hi", "0.8", "src/ingest/gsmap_nrt.py docstring")
    D("travel_h", "5-6", "docs/lit/paper_06.md; Report 2 §IV-C")
    D("travel_km", "51", "docs/lit/paper_06.md")
    D("grid_glofas", "0.05", "Report 2 §II-B (lưới quét GloFAS)")
    D("grid_sat", "0.1", "docs/FINDINGS_HOURLY_FINEGRID.md §2")
    D("grid_pccs", "0.04", "docs/FINDINGS_HOURLY_FINEGRID.md §2")
    D("n_hr_feat", "54", "docs/FINDINGS_HOURLY_FINEGRID.md §4")
    D("n_cells_era5", "64", "Report 2 §II-B")
    D("n_cells_sat", "100", "docs/FINDINGS_HOURLY_FINEGRID.md §11")
    D("api_k", "0.9", "Report 2 §III-C")
    D("leak_eps", "0.98", "docs/SPEC.md AC-5")
    D("ac1_h1", "0.70", "docs/SPEC.md AC-1")
    D("ac1_h2", "0.40", "docs/SPEC.md AC-1")
    D("ac1_h3", "0.25", "docs/SPEC.md AC-1")
    D("ac2_pod", "0.7", "docs/SPEC.md AC-2")
    D("ac1_rmse", "20", "docs/SPEC.md AC-1")
    D("mw_p", "0.581", "docs/FINDINGS_REGIME.md §3e; Report 2 §IV-G")
    return R


# ===================================================================== SHAP
SHAP_CSV = REP / "shap_importance.csv"
SHAP_GROUPS = {"flow": "Lagged discharge", "rain": "Rain, up to 7 days",
               "rain_long": "Long rain / reservoir proxy", "soil_api": "Soil moisture and API",
               "storm": "Tropical cyclone", "synoptic": "Pressure, wind, humidity",
               "enso": "ENSO", "season": "Calendar"}


def load_shap() -> bool:
    """Số của mục V từ ``reports/shap_importance.csv`` (``src/eval/shap_analysis.py``,
    diễn giải ở ``docs/FINDINGS_SHAP.md``). Không có file ⇒ False (mục V in khung chờ).
    Có file mà số lệch ⇒ ghi vào ``R.bad`` như mọi số khác."""
    if not SHAP_CSV.exists():
        return False
    d = pd.read_csv(SHAP_CSV)
    src = "reports/shap_importance.csv"
    # tái lập: NSE của mô hình được giải thích = NSE cấu hình E trong ablation_ext
    ab = _csv("ablation_ext.csv")
    ab = ab[ab.config.str.startswith("E")].set_index(["horizon", "seed"]).NSE
    m = d.drop_duplicates(["horizon", "seed"]).set_index(["horizon", "seed"]).nse_test
    R.claim("shap_repro", bool(np.allclose(m.values, ab.reindex(m.index).values, atol=1e-6)),
            "SHAP model reproduces the ablation NSE exactly", src + " vs ablation_ext.csv")
    for h, e in zip((1, 2, 3), ("0.748", "0.485", "0.193")):
        R.csv(f"shap_nse{h}", f(m.loc[(h, 42)]), e, src)
    g = d[d.level == "group"]
    g42 = g[g.seed == 42].set_index(["name", "horizon"])
    exp_all = {"flow": ("58.4", "28.4", "22.6"), "rain": ("33.3", "46.4", "33.3"),
               "rain_long": ("2.2", "5.3", "7.6"), "soil_api": ("1.8", "3.0", "4.0"),
               "storm": ("0.9", "2.4", "4.1"), "synoptic": ("2.3", "8.8", "14.2"),
               "enso": ("0.5", "1.6", "5.0"), "season": ("0.7", "4.1", "9.2")}
    exp_fl = {"flow": ("57.4", "21.9", "20.2"), "rain": ("35.0", "52.0", "34.5"),
              "rain_long": ("1.5", "4.2", "6.8"), "soil_api": ("2.6", "3.9", "5.2"),
              "storm": ("0.7", "2.8", "5.5"), "synoptic": ("1.8", "10.6", "15.1"),
              "enso": ("0.3", "0.9", "3.6"), "season": ("0.7", "3.7", "9.1")}
    for grp in SHAP_GROUPS:
        for h in (1, 2, 3):
            R.csv(f"sg_{grp}_{h}", f(g42.loc[(grp, h), "share_all_pct"], 1), exp_all[grp][h - 1], src)
            R.csv(f"sgf_{grp}_{h}", f(g42.loc[(grp, h), "share_flood_pct"], 1), exp_fl[grp][h - 1], src)
    for h, e in zip((1, 2, 3), ("-0.06", "-0.09", "-0.07")):
        R.csv(f"soil_signed{h}", f(g42.loc[("soil_api", h), "mean_signed_flood"], 2), e, src)
    spread = max(g.groupby(["name", "horizon"])[c].agg(lambda x: x.max() - x.min()).max()
                 for c in ("share_all_pct", "share_flood_pct"))
    R.csv("shap_spread", f(spread, 1), "2.3", src + " (seeds 42/7/2026)")
    ft = d[(d.level == "feature") & (d.seed == 42)].set_index(["name", "horizon"])
    for nm, h, e in (("discharge", 1, "37.4"), ("rain_thuong", 1, "11.2"), ("rain_basin", 1, "9.5"),
                     ("rain_basin", 2, "20.0"), ("discharge", 2, "13.5"), ("rain_thuong", 2, "12.3"),
                     ("rain_basin", 3, "16.0"), ("discharge", 3, "8.1"),
                     ("mslp_grad_north", 3, "5.8")):
        R.csv(f"sf_{nm}_{h}", f(ft.loc[(nm, h), "share_all_pct"], 1), e, src)
    R.csv("rank_mslp3", n(ft.loc[("mslp_grad_north", 3), "rank_all"]), "3", src)
    R.claim("top1_h1", ft.xs(1, level="horizon").rank_all.idxmin() == "discharge",
            "discharge ranks first at h = 1", src)
    R.claim("top1_h3", ft.xs(3, level="horizon").rank_all.idxmin() == "rain_basin",
            "basin rainfall ranks first at h = 2 and h = 3", src)
    for nm, e in (("discharge", ("+1.00", "+0.98", "+0.96")),
                  ("mslp_grad_north", ("+0.89", "+0.93", "+0.93")),
                  ("sm_7_28", ("-0.12", "-0.40", "-0.52")),
                  ("rain_season_cum", ("-0.16", "-0.00", "-0.23"))):
        for h in (1, 2, 3):
            R.csv(f"rho_{nm}_{h}", sg(ft.loc[(nm, h), "rho_value_shap"], 2), e[h - 1], src)
    # chỉ có trong tài liệu (FINDINGS_SHAP.md §4) — ca đỉnh lũ 16/10/2022 và 30/10/2025
    R.doc("wf_fc_2022", "862", "docs/FINDINGS_SHAP.md §4; reports/figures/report/shap_waterfall_20221016_h1_en.png")
    R.doc("wf_fc_2025", "1,727", "docs/FINDINGS_SHAP.md §4")
    R.doc("wf_n_above", "12", "docs/FINDINGS_SHAP.md §4 (12/9 283 ngày train có Q(t+1) >= 1 967)")
    R.doc("wf_q2000", "2,000", "docs/FINDINGS_SHAP.md §4 (12/12 ngày train Q(t) >= 2 000 đều rút)")
    R.doc("wf_ratio", "0.56", "docs/FINDINGS_SHAP.md §4 (trung vị dự báo/thật, 31 ngày lũ, h1)")
    return True
