"""Số liệu của Báo cáo cuối kỳ (Final Report), mỗi số đối chiếu với nguồn lúc build.

Cùng cơ chế với ``reports/report3/facts.py`` và ``reports/report4/facts.py``:

* Sổ của Report 3 và Report 4 được nạp nguyên (``report4/facts.load`` gọi
  ``report3/facts.load``) rồi chép vào sổ này — cùng nguồn CSV, cùng phép kiểm, không
  viết lại. Khoá nào lệch nguồn ở sổ cũ được giữ trong ``R.inherited_bad``; build sẽ
  hỏng nếu bản cuối kỳ IN khoá đó (khoá không in thì chỉ cảnh báo).
* Khoá MỚI (Report 4 bổ sung sau ngày 02/11/2026) đăng ký ở đây:

  - ``pk_*``   thử giảm cắt ngọn lũ (``reports/wf_peak_summary.csv``, ``docs/FINDINGS_PEAK.md``);
  - ``cal_*``  hiệu chỉnh isotonic FR-M6 (``reports/cost_calibration.csv``, §8 của
    ``docs/FINDINGS_COST_THRESHOLD.md``);
  - ``ev_*``   đánh giá theo đợt lũ (``reports/event_eval_summary.csv``);
  - ``nrt*``   GSMaP_NRT walk-forward (``reports/wf_sat_nrt.csv``, tính lại từ fold);
  - ``eda_*``  số Report 2 (``reports/eda_summary.csv``);
  - ``live_*`` job hằng ngày (``models/lgbm_live_*.json``, ``reports/forecast_log/``);
  - ``fs_*``, ``wfb_*`` Spark quy mô đủ (``reports/spark/full_scale_*.csv``,
    ``reports/spark/wf_bench.csv``) — các file này đang được agent khác ghi, nên số
    được TÍNH lúc build (``kind = csv``, nguồn = chính file) thay vì so với chuỗi định
    sẵn; thiếu file / thiếu dòng ⇒ ``None`` và build in khung ``pending``.

Ba loại mục giữ nguyên ý nghĩa: ``csv`` (kiểm với file), ``claim`` (câu định tính đã
kiểm), ``doc`` (chỉ có trong tài liệu, ghi nguồn).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REP = ROOT / "reports"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


r4f = _load("report4_facts_final", ROOT / "reports" / "report4" / "facts.py")
r3f = r4f.r3f
f, sg, n, ci, _csv = r3f.f, r3f.sg, r3f.n, r3f.ci, r3f._csv
boot_mean_ci, wilcoxon_p = r3f.boot_mean_ci, r3f.wilcoxon_p


class Registry(r4f.Registry):
    """Sổ Report 4 (chấp nhận số phiên bản) + danh sách lỗi thừa kế."""

    def __init__(self) -> None:
        super().__init__()
        self.inherited_bad: dict[str, str] = {}

    def auto(self, key: str, got: str, src: str) -> None:
        """Số tính lúc build từ file đang thay đổi (không có chuỗi định sẵn để so)."""
        self._put(key, got, src + " (tính lúc build)", "csv")


R = Registry()

# kết quả tuỳ chọn (None = chưa có, build in khung chờ)
SPARK_FULL: dict | None = None
SPARK_WF: dict | None = None
LIVE_LGBM: bool = False
WARN: list[str] = []


def _pfmt(p: float) -> str:
    return f(p, 3) if p < 0.1 else f(p, 2)


# ================================================================== nạp số
def load(cfg) -> Registry:
    global SPARK_FULL, SPARK_WF, LIVE_LGBM
    # ------------------------------------------------ sổ Report 3 + Report 4
    r4 = r4f.load(cfg)
    r3 = r3f.R
    import re as _re
    for reg in (r3, r4):
        for k in reg.val:
            if k in R.val:
                if R.val[k] != reg.val[k]:
                    R.bad.append(f"  {k}: Report 3 và Report 4 in khác nhau ({R.val[k]!r} / {reg.val[k]!r})")
                continue
            R._put(k, reg.val[k], reg.src[k], reg.kind[k])
        for b in reg.bad:
            m = _re.match(r"\s*(\S+):", b)
            if m:
                R.inherited_bad[m.group(1)] = b
    # SHAP của Report 3 nạp trong load_shap (cùng sổ r3)
    if r3f.SHAP_CSV.exists() and "sg_flow_1" not in r3.val:
        r3f.load_shap()
        for k in r3.val:
            if k not in R.val:
                R._put(k, r3.val[k], r3.src[k], r3.kind[k])

    _eda()
    _peak()
    _calibration()
    _events()
    _nrt()
    _live(cfg)
    SPARK_FULL = _spark_full()
    SPARK_WF = _spark_wf()
    return R


# ------------------------------------------------------------ Report 2 (EDA)
def _eda() -> None:
    e = _csv("eda_summary.csv")
    e = dict(zip(e.chi_tieu.astype(str), e.gia_tri.astype(str)))
    src = "reports/eda_summary.csv"
    for k, name, fmt, exp in (
            ("eda_ndays", "số ngày", lambda x: n(float(x)), "6,087"),
            ("eda_qmed", "Q trung vị (m³/s)", lambda x: f(float(x), 1), "49.7"),
            ("eda_qmax", "Q cực đại (m³/s)", lambda x: n(float(x)), "3,588"),
            ("eda_skew", "hệ số bất đối xứng", lambda x: f(float(x), 2), "5.91"),
            ("eda_sepdec", "tỉ lệ dòng chảy tháng 9–12 (%)", lambda x: f(float(x), 1), "58.6"),
            ("eda_r1", "r tại lag đó · cả năm", lambda x: f(float(x), 3), "0.789"),
            ("eda_wet", "Q trung vị khi mưa lớn + nền ẩm", lambda x: f(float(x), 1), "585.1"),
            ("eda_dry", "Q trung vị khi mưa lớn + nền khô", lambda x: f(float(x), 1), "84.9")):
        R.csv(k, fmt(e[name]), exp, src)
    R.claim("eda_lag1", e["lag tốt nhất · cả năm"] == "1", "rainfall-discharge correlation peaks at a lag of one day", src)
    R.claim("eda_qmax_day", e["ngày đạt cực đại"] == "2011-11-08", "maximum on 8 November 2011", src)


# ------------------------------------------------------------ thử giảm cắt ngọn
PK = {"w1": "E w1", "w3": "E w3", "w5": "E w5", "w10": "E w10", "iso": "E iso",
      "isohi": "E iso_hi", "lstm": "E+LSTM"}


def _peak() -> None:
    s = _csv("wf_peak_summary.csv")
    s = s[s.period == "chinh_2013_2025"].set_index(["config", "horizon"])
    src = "reports/wf_peak_summary.csv"
    for h, e in zip((1, 2, 3), ("0.761", "0.437", "0.206")):
        R.csv(f"pk_E{h}", f(s.loc[("E", h), "NSE_mean"]), e, src)
    for h, e in zip((1, 2, 3), ("-0.27", "-0.65", "-0.82")):
        R.csv(f"pk_Epb{h}", f(s.loc[("E", h), "peak_bias_mean"], 2), e, src)
    for h, e in zip((1, 2, 3), ("0.536", "-0.084", "-0.361")):
        R.csv(f"pk_P{h}", f(s.loc[("persistence", h), "NSE_mean"]), e, src)
    fc = _csv("wf_peak_summary.csv")
    fc = fc[(fc.period == "forecast_2023_2025") & (fc.config == "E")].set_index("horizon")
    for h, e in zip((1, 2, 3), ("0.772", "0.522", "0.223")):
        R.csv(f"pk_Efc{h}", f(fc.loc[h, "NSE_mean"]), e, src + " (2023-2025)")
    R.csv("pk_Epod1", f(s.loc[("E", 1), "POD1"], 2), "0.55", src)
    R.csv("pk_nfold", n(s.loc[("E", 1), "n_folds"]), "13", src)
    exp = {  # (dNSE, ci, wins/losses, p) per horizon; POD h1
        "w1": ((("+0.007", None, "8/5", "0.59"), ("-0.001", None, "5/8", "0.89"),
                ("-0.003", None, "6/7", "0.54")), "0.59"),
        "w3": ((("+0.011", "[+0.000; +0.024]", "9/4", "0.13"), ("+0.012", None, "9/4", "0.22"),
                ("+0.001", None, "6/7", "0.89")), "0.62"),
        "w5": ((("+0.008", None, "6/7", "0.54"), ("+0.005", None, "7/6", "0.74"),
                ("-0.007", None, "5/8", "0.34")), "0.62"),
        "w10": ((("-0.010", None, "4/9", "0.45"), ("+0.001", None, "7/6", "1.00"),
                 ("-0.008", None, "4/9", "0.34")), "0.53"),
        "iso": ((("-0.040", None, "6/7", "0.64"), ("-0.008", None, "5/8", "0.50"),
                 ("-0.027", "[-0.040; -0.016]", "1/12", "0.001")), "0.57"),
        "isohi": ((("-0.042", None, "6/7", "0.59"), ("-0.005", None, "7/6", "0.74"),
                   ("-0.013", None, "4/7", "0.067")), "0.57"),
        "lstm": ((("+0.029", "[+0.006; +0.056]", "10/3", "0.048"),
                  ("-0.022", "[-0.044; -0.001]", "2/11", "0.068"),
                  ("-0.023", "[-0.039; -0.007]", "2/11", "0.021")), "0.57"),
    }
    for v, (rows, pod) in exp.items():
        c = PK[v]
        for h, (em, eci, ewl, ep) in zip((1, 2, 3), rows):
            r = s.loc[(c, h)]
            R.csv(f"pk_{v}{h}_m", sg(r["dNSE_mean"]), em, src)
            if eci:
                R.csv(f"pk_{v}{h}_ci", ci(r["dNSE_ci_lo"], r["dNSE_ci_hi"]), eci, src)
            R.csv(f"pk_{v}{h}_wl", f"{int(r['wins'])}/{int(r['losses'])}", ewl, src)
            R.csv(f"pk_{v}{h}_p", _pfmt(r["p_wilcoxon"]), ep, src + " Wilcoxon")
        R.csv(f"pk_{v}_pod1", f(s.loc[(c, 1), "POD1"], 2), pod, src)
    R.csv("pk_w3_pb1", f(s.loc[("E w3", 1), "peak_bias_mean"], 2), "-0.21", src)
    ok = all(not ((s.loc[(c, 2), "dNSE_mean"] > 0 and s.loc[(c, 2), "p_wilcoxon"] < 0.05)
                  or (s.loc[(c, 3), "dNSE_mean"] > 0 and s.loc[(c, 3), "p_wilcoxon"] < 0.05))
             for c in PK.values())
    R.claim("pk_none", ok, "no variant improves h = 2 or h = 3 with p < 0.05", src)
    # NSE test (một lần chia) của E, peak bias test: ablation_ext
    ab = _csv("ablation_ext.csv")
    pb = ab[ab.config.str.startswith("E")].groupby("horizon").peak_bias.mean()
    for h, e in zip((1, 2, 3), ("-0.46", "-0.71", "-0.86")):
        R.csv(f"pk_testpb{h}", f(pb[h], 2), e, "reports/ablation_ext.csv (E, mean 3 seeds)")
    D = R.doc
    D("pk_freeze", "02/11/2026", "docs/FINDINGS_PEAK.md §3 (đóng băng E)")
    D("pk_crit_h1", "0.01", "docs/FINDINGS_PEAK.md §1 (tiêu chí: ΔNSE h1 ≥ −0,01)")


# ------------------------------------------------------------ hiệu chỉnh FR-M6
def _calibration() -> None:
    d = _csv("cost_calibration.csv")
    src = "reports/cost_calibration.csv (E, level 1, wf 2013-2025)"
    w = d[(d.bo_dac_trung == "E") & (d.muc == "nguy_co_1") & (d.pham_vi == "wf_2013_2025")]
    t = w[(w.horizon == 1) & (w.ty_le == 10)].set_index("phuong_phap")
    R.csv("cal_n", n(t.loc["p=0.5", "n"]), "4,748", src)
    R.csv("cal_npos", n(t.loc["p=0.5", "n_pos"]), "104", src)
    R.csv("cal_nfold", n(t.loc["chi_phi_iso", "n_fold"]), "13", src)
    exp = {"p=0.5": ("p05", "0.50", None, "32", "40", "3.1", "0.69", "0.36", "0.50", "360"),
           "chi_phi": ("raw", "0.03", ("0.02", "0.04"), "13", "109", "8.4", "0.88", "0.55", "0.43", "239"),
           "chi_phi_iso": ("iso", "0.12", ("0.10", "0.15"), "12", "110", "8.5", "0.88", "0.54", "0.43", "230"),
           "bayes_iso": ("bay", "0.091", None, "12", "110", "8.5", "0.88", "0.54", "0.43", "230")}
    for m, (tag, thr, rg, mis, fa, fay, pod, far, csi, cost) in exp.items():
        r = t.loc[m]
        R.csv(f"cal_{tag}_thr", f(r["nguong_p"], 3 if tag == "bay" else 2), thr, src)
        if rg:
            R.csv(f"cal_{tag}_thrlo", f(r["nguong_p_min"], 2), rg[0], src)
            R.csv(f"cal_{tag}_thrhi", f(r["nguong_p_max"], 2), rg[1], src)
        R.csv(f"cal_{tag}_miss", n(r["misses"]), mis, src)
        R.csv(f"cal_{tag}_fa", n(r["false_alarms"]), fa, src)
        R.csv(f"cal_{tag}_fay", f(r["fa_moi_nam"], 1), fay, src)
        R.csv(f"cal_{tag}_pod", f(r["POD"], 2), pod, src)
        R.csv(f"cal_{tag}_far", f(r["FAR"], 2), far, src)
        R.csv(f"cal_{tag}_csi", f(r["CSI"], 2), csi, src)
        R.csv(f"cal_{tag}_cost", n(r["cost"]), cost, src)
    raw, iso = t.loc["chi_phi"], t.loc["chi_phi_iso"]
    R.csv("cal_brier_raw", f(raw["brier"], 4), "0.0119", src)
    R.csv("cal_brier_iso", f(iso["brier"], 4), "0.0100", src)
    R.csv("cal_bss_raw", f(raw["BSS"], 2), "0.44", src)
    R.csv("cal_bss_iso", f(iso["BSS"], 2), "0.54", src)
    R.csv("cal_ece_raw", f(raw["ece"], 3), "0.010", src)
    R.csv("cal_ece_iso", f(iso["ece"], 3), "0.002", src)
    R.csv("cal_ll_raw", f(raw["log_loss"], 3), "0.050", src)
    R.csv("cal_ll_iso", f(iso["log_loss"], 3), "0.036", src)
    R.csv("cal_dbrier", f(iso["d_brier_vs_raw_mean"], 4), "-0.0020", src)
    R.csv("cal_dbrier_ci", f"[{iso['d_brier_vs_raw_ci_lo']:.4f}; {iso['d_brier_vs_raw_ci_hi']:.4f}]",
          "[-0.0036; -0.0006]", src)
    R.csv("cal_dbrier_p", f(iso["p_wilcoxon_brier_vs_raw"], 3), "0.027", src)
    R.csv("cal_dbrier_win", n(iso["n_fold_brier_tot_hon"]), "9", src)
    R.csv("cal_dcost", f(iso["d_cost_vs_raw_mean"], 1), "-0.7", src)
    R.csv("cal_dcost_p", f(iso["p_wilcoxon_vs_raw"], 2), "0.75", src)
    R.csv("cal_p05_p", f(iso["p_wilcoxon_vs_p05"], 3), "0.042", src)
    for ratio, er, ei in ((5, "168", "157"), (20, "352", "386")):
        u = w[(w.horizon == 1) & (w.ty_le == ratio)].set_index("phuong_phap")
        R.csv(f"cal_cost{ratio}_raw", n(u.loc["chi_phi", "cost"]), er, src)
        R.csv(f"cal_cost{ratio}_iso", n(u.loc["chi_phi_iso", "cost"]), ei, src)
    for h, er, ei in ((2, "0.0189", "0.0171"), (3, "0.0218", "0.0198")):
        u = w[(w.horizon == h) & (w.ty_le == 10)].set_index("phuong_phap")
        R.csv(f"cal_brier{h}_raw", f(u.loc["chi_phi", "brier"], 4), er, src)
        R.csv(f"cal_brier{h}_iso", f(u.loc["chi_phi_iso", "brier"], 4), ei, src)


# ------------------------------------------------------------ đánh giá theo đợt
def _events() -> None:
    e = _csv("event_eval_summary.csv")
    src = "reports/event_eval_summary.csv"
    wf = e[(e.scope == "wf_2013_2025") & (e.thr_mode == "fold_q95")].set_index(["model", "horizon"])
    te = e[(e.scope == "test_2022_07") & (e.thr_mode == "fixed_806")].set_index(["model", "horizon"])
    R.csv("ev_nwf", n(wf.loc[("lgbm_E", 1), "n_events"]), "43", src)
    R.csv("ev_nte", n(te.loc[("lgbm_E", 1), "n_events"]), "13", src)
    for tag, tab, exp in (("wf", wf, {("lgbm_E", 1): "28", ("lgbm_E", 2): "10", ("lgbm_E", 3): "0",
                                      ("persistence", 1): "27", ("persistence", 2): "14",
                                      ("persistence", 3): "7"}),
                          ("te", te, {("lgbm_E", 1): "6", ("lgbm_E", 2): "3", ("lgbm_E", 3): "0",
                                      ("persistence", 1): "9", ("persistence", 2): "3",
                                      ("persistence", 3): "3"})):
        for (m, h), ev in exp.items():
            R.csv(f"ev_{tag}_{'E' if m == 'lgbm_E' else 'P'}{h}", n(tab.loc[(m, h), "n_caught"]), ev, src)
    for h, ev in zip((1, 2, 3), ("0.80", "0.54", "0.31")):
        R.csv(f"ev_ratio{h}", f(wf.loc[("lgbm_E", h), "peak_ratio_median"], 2), ev, src)
    for (m, h), ev in {("lgbm_E", 2): "1", ("lgbm_E", 3): "0", ("persistence", 2): "16",
                       ("persistence", 3): "29"}.items():
        R.csv(f"ev_fa_{'E' if m == 'lgbm_E' else 'P'}{h}", n(wf.loc[(m, h), "n_fa_events"]), ev, src)
    R.csv("ev_lead_n", n(wf.loc[("lgbm_E", 1), "n_lead_onset_pos"]), "15", src)


# ------------------------------------------------------------ GSMaP_NRT
def _nrt() -> None:
    d = _csv("wf_sat_nrt.csv")
    d = d[d.fold.between(2013, 2025)]
    src = "reports/wf_sat_nrt.csv (13 folds, bootstrap/Wilcoxon as walk_forward_sat)"
    exp = {("E0+gsmap_nrt", 1): ("-0.002", "[-0.007; +0.003]", "4/9", "0.27"),
           ("E0+gsmap_nrt", 2): ("+0.003", "[-0.009; +0.017]", "6/7", "0.74"),
           ("E0+gsmap_nrt", 3): ("-0.001", "[-0.009; +0.008]", "5/8", "0.54"),
           ("A0+gsmap_nrt", 1): ("+0.009", "[+0.003; +0.014]", "10/3", "0.008"),
           ("A0+gsmap_nrt", 2): ("+0.019", "[+0.008; +0.031]", "11/2", "0.006"),
           ("A0+gsmap_nrt", 3): ("+0.012", "[+0.005; +0.019]", "12/1", "0.005")}
    for (c, h), (em, eci, ewl, ep) in exp.items():
        x = d[(d.config == c) & (d.horizon == h)].sort_values("fold").dNSE.to_numpy(float)
        tag = f"nrt{c[0]}{h}"
        lo, hi = boot_mean_ci(x)
        R.csv(f"{tag}_m", sg(x.mean()), em, src)
        R.csv(f"{tag}_ci", ci(lo, hi), eci, src)
        R.csv(f"{tag}_wl", f"{(x > 0).sum()}/{(x < 0).sum()}", ewl, src)
        R.csv(f"{tag}_p", _pfmt(wilcoxon_p(x)), ep, src)


# ------------------------------------------------------------ job hằng ngày
def _live(cfg) -> None:
    global LIVE_LGBM
    D = R.doc
    meta = ROOT / "models" / "lgbm_live_meta.json"
    iso = ROOT / "models" / "lgbm_live_iso_level1_h1.json"
    if meta.exists() and iso.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        k = json.loads(iso.read_text(encoding="utf-8"))
        src = "models/lgbm_live_meta.json"
        R.csv("live_nfeat", n(len(m["features"])), "88", src)
        R.csv("live_rows", n(m["n_rows"]["1"]), "10,466", src)
        R.claim("live_window", (m["train_start"], m["train_end"]) == ("1998-01-04", "2026-08-31"),
                "trained on 4 January 1998 to 31 August 2026", src)
        R.claim("live_obj", m["objective"] == {"1": "regression_l1", "2": "regression", "3": "regression"},
                "live models use L1 at h = 1, L2 at h = 2 and 3", src)
        src = "models/lgbm_live_iso_level1_h1.json"
        R.csv("live_thr", f(k["threshold"], 3), "0.091", src)
        R.csv("live_oof_n", n(k["oof_n"]), "9,862", src)
        R.csv("live_oof_pos", n(k["oof_pos"]), "185", src)
        R.csv("live_level", n(k["level_m3s"]), "806", src)
        R.claim("live_years", k["oof_years"] == [1999, 2025], "out-of-fold years 1999-2025", src)
    else:
        WARN.append("models/lgbm_live_*.json không có trên máy → số job hằng ngày lấy từ docstring")
        D("live_nfeat", "88", "src/models/predict_live.py docstring")
        D("live_rows", "10,466", "models/lgbm_live_meta.json (không có trên máy)")
        D("live_thr", "0.091", "src/models/predict_live.py docstring (1/11)")
        D("live_oof_n", "9,862", "models/lgbm_live_iso_level1_h1.json (không có trên máy)")
        D("live_oof_pos", "185", "models/lgbm_live_iso_level1_h1.json (không có trên máy)")
        D("live_level", "806", "reports/risk_levels.csv")
    D("live_lookback", "130", "src/models/predict_live.py LOOKBACK_DAYS")
    D("live_arch_lag", "6", "src/models/predict_live.py ARCHIVE_LAG_DAYS")
    D("sb_nse_drop", "0.06", "src/models/predict_live.py docstring (σ = 1 ⇒ NSE h1 −0,06)")
    D("dash_cache", "10", "dashboard/README.md (bộ nhớ đệm hết hạn sau 10 phút)")
    logs = sorted((REP / "forecast_log").glob("20??-??-??.csv"))
    src = "reports/forecast_log/*.csv"
    R.auto("live_nlogs", n(len(logs)), src)
    R.claim("live_first", logs[0].stem == "2026-09-15", "log starts on 15 September 2026", src)
    R.auto("live_last", logs[-1].stem, src)
    lg = 0
    for x in logs:
        h = pd.read_csv(x, nrows=5)
        if "lgbm_q" in h.columns and h["lgbm_q"].notna().any():
            lg += 1
    LIVE_LGBM = lg > 0
    R.auto("live_nlgbm", n(lg), src + " (bản phát có cột lgbm_q)")
    if not LIVE_LGBM:
        WARN.append("reports/forecast_log/: chưa bản phát nào có cột lgbm_q → in khung "
                    "[first operational LightGBM forecasts pending]")


# ------------------------------------------------------------ Spark quy mô đủ
def _spark_full() -> dict | None:
    fb, fp = REP / "spark" / "full_scale_bench.csv", REP / "spark" / "full_scale_parity.csv"
    if not (fb.exists() and fp.exists()):
        WARN.append("reports/spark/full_scale_*.csv chưa có → in khung [full-scale Spark pending]")
        return None
    try:
        b = pd.read_csv(fb)
        p = pd.read_csv(fp)
        b = b[(b.status == "ok") & (b.period == "full")]
        srcb, srcp = "reports/spark/full_scale_bench.csv", "reports/spark/full_scale_parity.csv"
        srcs = ["imerg", "gsmap_gc", "gsmap_nrt"]
        tags = ["cluster_2w_8c", "cluster_1w_4c", "docker_local8_drv4g", "docker_polars"]
        out = {"rows": {}}
        for s in srcs:
            x = b[b.source == s]
            if x.empty or not set(tags) <= set(x.tag):
                raise ValueError(f"thiếu cấu hình cho {s}")
            R.auto(f"fs_{s}_files", n(x.files.iloc[0]), srcb)
            R.auto(f"fs_{s}_mb", f(x.mb_on_disk.iloc[0], 1), srcb)
            R.auto(f"fs_{s}_rows", n(x.rows_in_files.iloc[0]), srcb)
            R.auto(f"fs_{s}_days", n(x.days_out.iloc[0]), srcb)
            for t in tags:
                y = x[x.tag == t].seconds_total
                R.auto(f"fs_{s}_{t}_lo", f(y.min(), 1), srcb)
                R.auto(f"fs_{s}_{t}_hi", f(y.max(), 1), srcb)
            sp = x[x.tag == "docker_local8_drv4g"].seconds_total.median()
            R.auto(f"fs_{s}_ratio", f(sp / x[x.tag == "docker_polars"].seconds_total.median(), 1),
                   srcb + " (trung vị Spark local[8] driver 4g / trung vị Polars, cùng container;"
                   " cùng cách tính với report4 fl_x_lo)")
            out["rows"][s] = int(x.rows_in_files.iloc[0])
        tot = sum(out["rows"].values())
        R.auto("fs_sat_mrows", f(tot / 1e6, 1), srcb + " (IMERG + GSMaP + GSMaP_NRT)")
        era5 = int(_csv("spark/etl_benchmark.csv").rows_in.iloc[0])
        R.auto("fs_all_mrows", f((tot + era5) / 1e6, 1), srcb + " + reports/spark/etl_benchmark.csv (ERA5)")
        mb = b.drop_duplicates("source").mb_on_disk.sum()
        R.auto("fs_mb_tot", f(mb, 0), srcb)
        c = p[(p.period == "full") & (p.master.str.startswith("spark://"))]
        if set(c.source) != set(srcs):
            raise ValueError("đối chiếu cụm chưa đủ ba nguồn")
        R.claim("fs_bit", bool((c.values_not_bitwise_equal == 0).all() and (c.null_mismatch == 0).all()
                               and (c.rows_only_one_side == 0).all() and (c.max_abs_diff == 0).all()),
                "every value bit-identical to Polars on the cluster, full record", srcp)
        R.auto("fs_values", n(c.values_compared.sum()), srcp)
        R.auto("fs_hrows", n(c[c.level == "hourly"].rows.max()), srcp)
        R.auto("fs_ncol", n(c[c.level == "daily"]["columns"].max()), srcp)
        w = p[p.host == "windows-host"]
        R.claim("fs_bit_win", bool(len(w) > 0 and (w.values_not_bitwise_equal == 0).all()),
                "host local[8] parity on one year per source also bit-identical", srcp)
        return out
    except Exception as e:  # noqa: BLE001 — file đang được agent khác ghi
        WARN.append(f"reports/spark/full_scale_*.csv chưa đủ ({e}) → in khung chờ")
        return None


def _spark_wf() -> dict | None:
    fw = REP / "spark" / "wf_bench.csv"
    out: dict = {}
    if not fw.exists():
        WARN.append("reports/spark/wf_bench.csv chưa có → in khung [Spark walk-forward pending]")
        return None
    w = pd.read_csv(fw)
    src = "reports/spark/wf_bench.csv"
    pool = w[w.engine == "process_pool"]
    if len(pool):
        r = pool.iloc[-1]
        R.auto("wfb_pool_jobs", n(r.n_jobs), src)
        R.auto("wfb_pool_cores", n(r.cores_used), src)
        R.auto("wfb_pool_s", f(r.wall_s, 1), src)
        out["pool"] = True
    sp = w[w.engine == "spark"]
    if len(sp) and {"sum_task_s", "parity_max_abs_diff"} <= set(sp.columns):
        r = sp.iloc[-1]
        R.auto("wfb_sp_tag", str(r.tag), src)
        R.auto("wfb_sp_jobs", n(r.n_jobs), src)
        R.auto("wfb_sp_cores", n(r.cores_used), src)
        R.auto("wfb_sp_s", f(r.wall_s, 1), src)
        R.auto("wfb_sp_serial", f(r.sum_task_s, 1), src)
        R.auto("wfb_sp_speed", f(r.speedup_vs_serial, 1), src)
        R.auto("wfb_sp_pjobs", n(r.parity_jobs), src)
        R.auto("wfb_sp_diff", f"{r.parity_max_abs_diff:.1e}" if r.parity_max_abs_diff else "0",
               src)
        if r.parity_max_abs_diff:
            m_, e_ = f"{r.parity_max_abs_diff:.1e}".split("e")
            R.auto("wfb_sp_diff_m", m_, src)
            R.auto("wfb_sp_diff_e", str(int(e_)), src)
        out["spark"] = True
    else:
        WARN.append("reports/spark/wf_bench.csv chưa có dòng Spark → in khung [Spark walk-forward pending]")
    return out or None
