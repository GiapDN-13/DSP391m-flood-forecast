"""Sinh Report 3 (Modelling & Evaluation) theo định dạng IEEE hai cột.

    python reports/report3/build_report.py

Cùng khuôn với Report 1–2 (kiểu chữ, helper ``p``/``bullets``/``h1``/``ST`` nạp từ
``reports/report1/build_report.py``). Ba lớp bảo vệ — lỗi ở báo cáo nộp đi là lỗi
đắt nhất:

1. **Số đối chiếu với nguồn lúc build** (``facts.py``). Văn bản lấy số qua
   ``V(key)``; mỗi khoá được tính lại từ ``reports/*.csv`` và so với chuỗi định in.
   Chạy lại thí nghiệm mà số đổi thì build **hỏng**.
2. **Quét số trong PDF.** Mọi số thập phân / số có dấu phẩy nghìn trong thân bài,
   bảng và chú thích hình phải có trong sổ số liệu. Gõ tay một số lạ là build hỏng.
3. **Ký tự ngoài bảng mã WinAnsi** (≥, ≈, →, Δ, chữ Việt có dấu…) sẽ thành ô đen
   với font Times chuẩn của PDF ⇒ build hỏng, kèm vị trí. Δ và σ in bằng font
   Symbol (``DELTA``, ``SIGMA``).

Hai mục phụ thuộc kết quả có thể chưa có — thiếu file thì KHÔNG hỏng build, in khung
chỗ trống có đánh dấu và in cảnh báo:

* ``reports/wf_sat_nrt.csv``      → mục IV-G. Thiếu: "[GSMaP_NRT operational test
  pending]". Có: bảng ΔNSE tự tính lúc build (cùng bootstrap/Wilcoxon với
  ``walk_forward_sat``) + khung "[Interpretation pending team review]" — câu kết
  luận phải do nhóm viết sau khi xem số.
* ``reports/shap_importance.csv`` → mục V. Thiếu: "[SHAP section pending]". Có: mục V
  viết theo ``docs/FINDINGS_SHAP.md``, số kiểm bằng ``facts.load_shap`` (lệch là hỏng).

Build cũng ghi ``reports/report3/OUTLINE_VI.txt``: dàn ý tiếng Việt cho người nói
và danh sách mọi số đã dùng kèm nguồn.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as cfg  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


r1 = _load("report1_build", ROOT / "reports" / "report1" / "build_report.py")
fx = _load("report3_facts", HERE / "facts.py")
p, bullets, h1, ST = r1.p, r1.bullets, r1.h1, r1.ST
COLW, LM, RM, TM, BM, GUT, PW, PH = r1.COLW, r1.LM, r1.RM, r1.TM, r1.BM, r1.GUT, r1.PW, r1.PH
FIGS = r1.FIGS
REP = ROOT / "reports"
OUT = HERE / "DSP391m_Report3_Modelling_Evaluation_IEEE.pdf"
OUTLINE = HERE / "OUTLINE_VI.txt"

# Ô bảng hẹp mà căn đều thì chữ giãn xấu — căn trái (chỉ trên bản module nạp riêng).
ST["tabcell"].alignment = TA_LEFT
ST["tc7"] = ParagraphStyle("tc7", parent=ST["tabcell"], fontSize=7.4, leading=8.8)
ST["tc7w"] = ParagraphStyle("tc7w", parent=ST["tc7"], wordWrap="CJK")   # tên feature dài
ST["th7"] = ParagraphStyle("th7", parent=ST["tabhead"], fontSize=7.4, leading=8.8)
ST["capwide"] = ParagraphStyle("capwide", parent=ST["caption"], alignment=TA_JUSTIFY,
                               spaceBefore=0, spaceAfter=0)
ST["pending"] = ParagraphStyle("pending", parent=ST["body0"], fontName="Times-Italic",
                               backColor=colors.HexColor("#fff3cd"),
                               borderColor=colors.HexColor("#c9a227"), borderWidth=0.6,
                               borderPadding=4, spaceBefore=6, spaceAfter=8)

# Ký hiệu ngoài WinAnsi → font Symbol; ký hiệu trong WinAnsi → thực thể
ST["tabcap"].spaceBefore = 6
ST["ref"].alignment = TA_LEFT
DELTA = '<font face="Symbol">&#916;</font>'      # font Symbol vẽ được Δ, σ (Times thì không)
SIGMA = '<font face="Symbol">&#963;</font>'
ND, MD, DEG, PM = "&#8211;", "&#8212;", "&#176;", "&#177;"
M3S, KM2 = "m&#179;/s", "km&#178;"

V = fx.R            # V("key") → số đã kiểm, dấu trừ in thành gạch en
WARN: list[str] = []


def of(key: str) -> str:
    """'11/24' (số ngày / tổng) → '11 of 24'."""
    return V(key).replace("/", " of ")


def won(key: str) -> str:
    """'11/2' (fold thắng / thua) → '11 of 13'."""
    return f"{V(key).split('/')[0]} of {V('wf_nfold')}"


def _rel(path: Path) -> Path:
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def h2(letter: str, text: str):
    return p(f"{letter}.&nbsp;&nbsp;{text}", "h2")


def pending(text: str):
    return Paragraph(text, ST["pending"])


def roman(i: int) -> str:
    return ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"][i - 1]


# ================================================================ bảng, hình
def tbl(rows, widths, key: str, caption: str, small: bool = False, bold_rows=()):
    hs, cs = (ST["th7"], ST["tc7"]) if small else (ST["tabhead"], ST["tabcell"])
    data = [[Paragraph(c, hs) for c in rows[0]]]
    for i, r in enumerate(rows[1:], start=1):
        data.append([Paragraph(f"<b>{c}</b>" if i in bold_rows else c, cs) for c in r])
    t = Table(data, colWidths=widths, hAlign="CENTER", repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return KeepTogether([Paragraph(f"TABLE {T[key]}<br/>{caption}", ST["tabcap"]), t, Spacer(1, 8)])


def col_fig(fname: str, key: str, caption: str, scale: float = 1.0):
    f = FIGS / fname
    if not f.exists():
        raise SystemExit(f"Thiếu hình {f.relative_to(ROOT)}")
    w = (COLW - 0.05 * inch) * scale
    iw, ih = ImageReader(str(f)).getSize()
    return KeepTogether([Image(str(f), width=w, height=w * ih / iw),
                         Paragraph(f"Fig. {F[key]}.&nbsp; {caption}", ST["caption"])])


def crop_sat() -> ImageReader:
    """Hàng EXT (mốc E0) của wf_sat_en.png — Report 3 báo theo mốc E0."""
    im = PILImage.open(FIGS / "wf_sat_en.png").convert("RGB")
    if im.size != (2181, 1358):
        WARN.append(f"wf_sat_en.png đổi kích thước {im.size} — dùng nguyên hình, kiểm lại bố cục")
        return ImageReader(im)
    return ImageReader(im.crop((0, 720, im.size[0], im.size[1])))


def crop_dl() -> ImageReader:
    """Chú giải + hàng ΔNSE so với LightGBM của wf_dl_en.png."""
    im = PILImage.open(FIGS / "wf_dl_en.png").convert("RGB")
    if im.size != (2046, 1395):
        WARN.append(f"wf_dl_en.png đổi kích thước {im.size} — dùng nguyên hình, kiểm lại bố cục")
        return ImageReader(im)
    leg, bot = im.crop((0, 78, im.size[0], 142)), im.crop((0, 800, im.size[0], im.size[1]))
    out = PILImage.new("RGB", (im.size[0], leg.size[1] + bot.size[1]), "white")
    out.paste(leg, (0, 0))
    out.paste(bot, (0, leg.size[1]))
    return ImageReader(out)


# ===================================================== kết quả còn chờ (tuỳ chọn)
def prep_nrt():
    """reports/wf_sat_nrt.csv (walk_forward_sat --nrt-test) → bảng; thiếu thì None."""
    f = REP / "wf_sat_nrt.csv"
    if not f.exists():
        WARN.append("reports/wf_sat_nrt.csv chưa có → in khung [GSMaP_NRT operational test pending]")
        return None
    try:
        d = pd.read_csv(f)
        d = d[d.fold.between(2013, 2025)]
        rows = []
        for g in d.group.unique():
            x = d[d.group == g]
            for c in [c for c in x.config.unique() if c.endswith(("+gsmap_gc", "+gsmap_nrt"))]:
                cells = [c.replace("gsmap_gc", "GSMaP-GC (EE)").replace("gsmap_nrt", "GSMaP_NRT")]
                for h in (1, 2, 3):
                    dn = x[(x.config == c) & (x.horizon == h)].sort_values("fold").dNSE.to_numpy(float)
                    dn = dn[np.isfinite(dn)]
                    if len(dn) < 3:
                        cells.append("n/a")
                        continue
                    lo, hi = fx.boot_mean_ci(dn)
                    k = f"nrt_{g}_{c}_{h}"
                    vals = (fx.sg(dn.mean()), fx.ci(lo, hi), f"{(dn > 0).sum()}/{(dn < 0).sum()}",
                            fx.f(fx.wilcoxon_p(dn)))
                    for j, v in enumerate(vals):
                        V.csv(f"{k}_{j}", v, v, "reports/wf_sat_nrt.csv (tính lúc build)")
                    nf = "" if len(dn) == 13 else f" (n = {len(dn)})"
                    cells.append(f"{V(k + '_0')}<br/>{V(k + '_1')}<br/>{V(k + '_2')}, "
                                 f"p {V(k + '_3')}{nf}")
                rows.append(cells)
        if not rows:
            raise ValueError("không thấy cấu hình +gsmap_nrt / +gsmap_gc")
        return rows
    except Exception as e:  # noqa: BLE001 — tệp đang được người khác sinh, đừng làm hỏng build
        WARN.append(f"reports/wf_sat_nrt.csv đọc không được ({e}) → in khung chờ")
        return None


NRT = prep_nrt()
SHAP = fx.SHAP_CSV.exists()      # số SHAP nạp và kiểm trong build() (fx.load_shap)
if not SHAP:
    WARN.append("reports/shap_importance.csv chưa có → in khung [SHAP section pending]")
_tabs = ["feedback", "base", "clf", "abl", "sat"] + (["nrt"] if NRT else []) + ["dl", "r1"] + \
        (["shap"] if SHAP else [])
T = {k: roman(i) for i, k in enumerate(_tabs, start=1)}
_figs = ["basins", "sat", "dl", "r2"] + (["shap"] if SHAP else [])
F = {k: str(i) for i, k in enumerate(_figs, start=1)}


# ================================================================== nội dung
def story() -> list:
    s: list = []

    # ============================================================ I
    s += [h1("I", "Introduction"),
          p("Reports 1 and 2 defined the task and the data: forecast the daily discharge of "
            f"the Huong River at Kim Long (Hue, Vietnam) one, two and three days ahead, at the "
            f"GloFAS v4 cell that represents the station ({V('pt_lat')}{DEG} N, "
            f"{V('pt_lon')}{DEG} E), and translate the forecast into flood-risk levels using "
            "open data only. This report covers model development and evaluation. The "
            "project is positioned as a local post-processing layer on top of the global "
            "forecast, in the line of recent GloFAS bias-correction studies [7], [8], not as "
            "a replacement for it.", "body0"),
          tbl([["Feedback", "Work done", "Finding"],
               ["Reservoir releases, other factors",
                f"Dam-era test of GloFAS (R1); {V('rel_rows')} reported dam flows (R2); "
                "soil moisture, storage proxies, storms, cold surges, ENSO",
                "GloFAS v4 has no dams: releases enter a raise-only floor rule; weather "
                "drivers help at h = 2&#8211;3"],
               ["Finer grid",
                f"30 m DEM sub-basins; satellite rain at {V('grid_sat')}{DEG}; PERSIANN-CCS "
                f"at {V('grid_pccs')}{DEG}",
                f"{V('grid_pccs')}{DEG} product misses monsoon rain; sub-basins add little"],
               ["Hourly time step",
                f"{V('n_hr_feat')} hourly ERA5 features; hourly IMERG, GSMaP 1998&#8211;2026",
                "Gain at h = 3 only, and only with same-day satellite data"],
               ["Spark, deep learning (Report 4)",
                "Two-worker Spark cluster; LSTM, MLP under walk-forward",
                "Spark matches Polars but is slower; DL does not beat LightGBM"]],
              [0.82 * inch, 1.36 * inch, 1.32 * inch], "feedback",
              "FEEDBACK ON REPORT 2 AND THE RESPONSE IN THIS REPORT", small=True),
          p("The review of Report 2 raised three points: river flow at Kim Long also depends "
            "on reservoir releases and other factors; the 5 km grid is coarse; and a daily "
            "time step may hide the rapid response of a steep basin. Distributed processing "
            "with Spark and, if possible, deep learning were requested for Report 4. Table "
            f"{T['feedback']} maps each point to the work done and the answer obtained. One "
            "constraint frames every answer: the target remains GloFAS daily discharge on a "
            "~5 km grid, so finer or hourly <i>inputs</i> cannot make the <i>target</i> finer. "
            "Section II also corrects the catchment area used in Reports 1 and 2.")]

    # ============================================================ II
    s += [h1("II", "Data Updates"),
          h2("A", "Longer record and new predictors"),
          p("ERA5 rainfall was extended back to 1997, the first year in which GloFAS returns "
            f"discharge for this basin, which doubles the training set of the main split from "
            f"{V('ntrA')} to {V('ntrB')} days. Four predictor families were added: ERA5-Land "
            f"soil moisture in three layers; tropical cyclones from IBTrACS v04r01 [15] "
            f"({V('storms')} storms within {V('storm_km')} km of Hue since 1996), described by "
            "distance, wind speed and approach speed; cold-surge indicators from ERA5 pressure "
            "and wind (the Hanoi&#8211;Hue pressure difference and the north-easterly wind); "
            "and the Oceanic Ni&#241;o Index [16], lagged three months so that only values "
            "already published are used."),

          h2("B", "Correction to Report 2: catchment area"),
          p(f"Report 1 gave the Huong catchment as about {V('area_sys')} {KM2}, and the grid-cell "
            "selection described there (and repeated in the Report 2 presentation) used that figure when checking the catchment "
            f"area implied by specific runoff. The value is wrong for Kim Long. {V('area_sys')} "
            f"{KM2} is the whole Huong system <i>including</i> the Bo River ({V('area_bo')} "
            f"{KM2}) [12], and the Bo joins downstream of Kim Long; the earlier reference for "
            f"the combined system ({V('area_dbl')} {KM2}) counted the Bo twice. Delineation "
            f"from the Copernicus GLO-30 DEM [17] gives {V('area_dem')} {KM2} to Kim Long, and "
            f"the project now uses about {V('area_cfg')} {KM2}. The selected cell does not "
            f"change: its mean discharge of {V('q_cell')} {M3S} implies {V('imp_lo')}&#8211;"
            f"{V('imp_hi')} {KM2} for a specific runoff of {V('spec_lo')}&#8211;{V('spec_hi')} "
            f"{M3S} per {KM2}, consistent with the corrected area. All area-based quantities "
            "in this report use the corrected value."),

          h2("C", "Sub-basins from a 30 m DEM"),
          p("Rainfall was previously averaged over three latitude bands. The catchment is now "
            f"split into five non-overlapping sub-basins with a D8 flow model (Fig. {F['basins']}): "
            f"the Ta Trach and Binh Dien reservoir catchments ({V('a_tt')} and {V('a_bd')} "
            f"{KM2}, within {V('dtt_pct')}% and {V('dbd_pct')}% of the official {V('ref_tt')} "
            f"and {V('ref_bd')} {KM2} [11]), the Ta Trach and Huu Trach reaches below the dams "
            f"({V('a_ttb')} and {V('a_htb')} {KM2}) and the reach from the Tuan confluence to "
            f"Kim Long ({V('a_tkl')} {KM2}). The {V('n_cells_era5')} ERA5 cells cover only "
            f"{V('cov_era5')}% of the catchment because its southern rim lies outside the "
            "rainfall box; the satellite grids below cover all of it."),
          col_fig("basins_map.png", "basins",
                  f"Huong basin to Kim Long ({V('area_dem')} {KM2}), five sub-basins "
                  "delineated from the 30 m DEM, ERA5 cells and the GloFAS target point.",
                  scale=0.86),

          h2("D", "Satellite rainfall"),
          p(f"Hourly IMERG V07 [13] and GSMaP v8 [14] (satellite-only and gauge-calibrated, "
            "GC) were retrieved from Google Earth Engine for January 1998 to October 2026 on "
            f"{V('n_cells_sat')} cells of {V('grid_sat')}{DEG}. Only PERSIANN-CCS is finer than "
            f"the GloFAS grid ({V('grid_pccs')}{DEG}), but for November 2020 it recorded "
            f"{V('pccs_nov')} of the ERA5 total, probably because its cloud-top retrieval "
            "misses rain from the low, warm clouds of north-east monsoon events, so it was "
            "not used. For each basin and "
            "day nine hourly features were derived: daily total; maximum 1-, 3- and 6-h rain; "
            "hours with at least 1 mm; peak hour as sine and cosine; 24-h total to 07:00; and "
            f"72-h total. Over the 2015&#8211;2025 flood seasons IMERG, GSMaP and GSMaP-GC total "
            f"{V('rr_imerg')}, {V('rr_gsmap')} and {V('rr_gc')} times ERA5. ERA5 correlates best "
            f"with next-day GloFAS discharge (r = {V('rq_era5')} against {V('rq_imerg')} for "
            "IMERG and GSMaP-GC), as expected, because GloFAS v4 is itself driven by ERA5; "
            "this does not show that ERA5 is closer to the true rainfall."),

          h2("E", "Reservoir records"),
          p("Release and inflow figures for the Ta Trach and Binh Dien reservoirs were "
            f"collected from provincial bulletins and news: {V('rel_rows')} records on "
            f"{V('rel_days')} days from {V('rel_y0')} to 2026, each with source URL, access "
            "date and a verbatim quotation. No daily release series is published, so these "
            "records can test the target and drive an operating rule, but cannot be a "
            "training feature.")]

    # ============================================================ III
    s += [h1("III", "Methodology"),
          h2("A", "Forecasting task"),
          p("The target is the GloFAS v4 daily mean discharge at the Kim Long cell, h = 1, 2 "
            "and 3 days after the issue date t. Every predictor is known at the end of day t: "
            "rolling windows look backward only and an automated test fails if a feature "
            "uses later information. The main test period starts on 1 July 2022, when the "
            "Open-Meteo GloFAS series switches from reanalysis to archived forecasts "
            f"(n = {V('n_test1')} days at h = 1)."),

          h2("B", "Feature configurations"),
          p(f"Configuration A is the Report 2 panel ({V('nfA')} features): discharge lags of "
            "1&#8211;14 days, rainfall per band with lags and 3-, 5- and 7-day sums, an "
            f"antecedent precipitation index (k = {V('api_k')}) and a cyclic day-of-year code. "
            "B&#8211;E add data cumulatively: B trains from 1997 with the same features; C adds "
            f"soil moisture ({V('nfC')}); D adds reservoir-storage proxies, namely 15- and "
            "30-day rainfall and rainfall accumulated since 1 September, the start of the "
            f"flood-operation season set by the inter-reservoir procedure [11] ({V('nfD')}); "
            f"E adds storm, cold-surge and ENSO predictors ({V('nfE')}). Satellite features are "
            "tested on top of E (called E0 in the walk-forward runs) and of A (A0)."),

          h2("C", "Models"),
          p("The main model is LightGBM trained on log(1 + Q) with an L1 objective "
            f"({V('lgb_trees')} trees, learning rate {V('lgb_lr')}, {V('lgb_leaves')} leaves), "
            "one model per horizon; results are for seed 42 or, where stated, the mean of "
            "seeds 42, 7 and 2026. L1 was fixed before "
            "any test result because it is robust to extremes; L2 and Huber variants gave a "
            "similar negative peak bias, so under-predicting peaks is a property of central "
            "regression on a skewed target, not of the loss. Risk levels are predicted by "
            "separate binary LightGBM classifiers per level and horizon, with class weights "
            "equal to the negative-to-positive ratio instead of resampling, which would break "
            f"the temporal structure, and a decision threshold of {V('clf_thr')}; a threshold "
            "tuned on validation did not transfer to the test period and was not adopted."),
          p(f"Two neural families were compared ({V('n_dlcfg')} configurations, 3 seeds each): "
            "a multi-output LSTM reading a 14- or 30-day window of raw variables (discharge, "
            "band rainfall, API, season), optionally predicting the change from today's "
            "discharge and optionally with a peak-weighted loss; and an MLP on the LightGBM "
            "lag columns. Global LSTM models are the state of the art for ungauged flood "
            "prediction [6], and transfer to small local basins is an open question [10]."),

          h2("D", "Baselines"),
          p("Persistence, climatology (multi-year mean of the calendar day, fitted on "
            "training data only), seasonal naive and ARIMA(2,1,2) on log discharge. The raw "
            "GloFAS forecast, the natural reference for a post-processing model, cannot be "
            "rebuilt for past dates: Open-Meteo archives past rainfall forecasts but not past "
            "flood forecasts (the historical flood endpoint returns HTTP 404), and using the "
            "GloFAS analysis at t + h as an input would leak the target. The issued GloFAS "
            "forecast has therefore been logged every morning since 15 September 2026 (one "
            "day, 20 September, was lost to a time-zone bug and is not imputed); the "
            "comparison will be reported in Report 4 on that operational sample."),

          h2("E", "Validation protocol"),
          p("<b>Single regime split.</b> Train to December 2015, validation to June 2022, "
            "test from July 2022; final models are refit on train plus validation. "
            "<b>Yearly walk-forward.</b> Each year 2013&#8211;2025 is a test fold "
            f"({V('wf_nfold')} folds); the training window expands from the start of the "
            "record; a 3-day gap separates train and test so that no h = 3 label enters the "
            "test year; and the risk threshold is recomputed from each fold's training data "
            f"only. Gains are summarised by the mean {DELTA}NSE over folds with a 95% bootstrap "
            "interval that resamples folds, the folds won and lost, and a two-sided Wilcoxon "
            "signed-rank test. January&#8211;August 2026 is excluded as a partial year."),
          p("Two facts bound the interpretation. Perturbing the input panel at the 13th "
            f"decimal changes LightGBM NSE by about {PM}{V('noise')}, so smaller differences "
            "are not resolvable. And the archived-forecast regime contains only "
            f"{V('fc_nfold')} full folds (2023&#8211;2025), for which the smallest attainable "
            f"two-sided p is {V('fc_pmin')}: that regime cannot be tested on its own."),

          h2("F", "Risk levels instead of alert stages"),
          p(f"Official alert stages at the Hue (Kim Long) station are water levels of {V('bd1')}, "
            f"{V('bd2')} and {V('bd3')} m [4], whereas the model forecasts discharge. An "
            "event-calibrated mapping from discharge to level was built from published flood "
            f"peaks and failed: across {V('hq_n')} floods since 2010 log discharge explains "
            f"little of the peak level (R&#178; = {V('hq_r2')}), and the best fit on "
            f"{V('hq_nfit')} floods (R&#178; = {V('hq_r2fit')}) missed the five floods after "
            f"July 2022 with a mean bias of {V('hq_bias')} m. Tide and backwater from the Tam "
            "Giang lagoon, the Thao Long barrage, reservoir operation and the under-simulation "
            "of extreme floods all decouple level from simulated discharge. Labels are "
            "therefore <i>risk levels</i> at the 95th, 98th and "
            f"{V('q_lv3')}th percentiles of September&#8211;December discharge on train plus "
            f"validation: {V('thr1')}, {V('thr2')} and {V('thr3')} {M3S}. They are relative to "
            "the GloFAS climate and are not alert stages."),

          h2("G", "Rare-event verification"),
          p("Level-1 days are about 1% of the test period, so accuracy is never reported. "
            "Detection is scored with POD, FAR, CSI, F1, PR-AUC and the Brier score. A level "
            "supports a main conclusion only if the test set holds at least 30 positive days: "
            f"level 1 has {V('npos1')}, level 2 only {V('npos2')} and level 3 {V('npos3')}; "
            f"level 3 has just {V('ntv3')} positive days in train plus validation and is not "
            "modelled."),

          h2("H", "Reservoir floor rule"),
          p("When the province orders releases, the forecast at Kim Long becomes the larger "
            "of the model forecast and the sum of the ordered releases at Ta Trach and Binh "
            "Dien, since released water reaches Kim Long within hours. The rule only raises a "
            "forecast and never lowers it; without an order nothing changes. Huong Dien and A "
            "Luoi are ignored because they drain to the Bo River or out of the basin. The daily "
            "job keeps the raw GloFAS value beside the floored one. The rule is a safeguard, "
            "not a validated component: no historical series of orders exists to score it.")]

    # ============================================================ IV
    s += [h1("IV", "Results"),
          NextPageTemplate(["wide_sat", "*", "rest"]),
          h2("A", "Baselines and LightGBM"),
          p(f"LightGBM beats every baseline at every horizon (Table {T['base']}). With the "
            "Report 2 predictors (configuration A, the reference for the acceptance criteria), "
            f"its NSE at h = 1 of {V('lgb_nse1')} meets the threshold of {V('ac1_h1')} and its "
            f"RMSE is {V('rmse_gain1')}% below persistence (target {V('ac1_rmse')}%); at h = 2 "
            f"it meets {V('ac1_h2')} ({V('lgb_nse2')}); at h = 3 it misses {V('ac1_h3')} "
            f"({V('lgb_nse3')}). The margin is largest where persistence collapses "
            f"({V('persistence_nse2')} and {V('persistence_nse3')} at h = 2 and 3). Peaks, "
            "however, are under-predicted at all horizons: the peak bias at the 99th "
            f"percentile is {V('lgb_pb1')}, {V('lgb_pb2')} and {V('lgb_pb3')}, worse than "
            f"persistence at h = 1 ({V('per_pb1')}). The model wins on average error but cuts "
            "flood peaks, the most serious weakness for a warning product. Configuration E, "
            "the main model from this report on (Section IV-D), keeps h = 1 and raises "
            f"h = 2 and 3 to {V('abE2')} and {V('abE3')}, still short of {V('ac1_h3')} at "
            "h = 3."),
          tbl([["Model", "NSE h=1", "h=2", "h=3", f"RMSE h=1 ({M3S})", "h=2", "h=3"]]
              + [[name] + [V(f"{m}_nse{h}") for h in (1, 2, 3)]
                 + [V(f"{m}_rmse{h}") for h in (1, 2, 3)]
                 for m, name in (("persistence", "Persistence"), ("climatology", "Climatology"),
                                 ("seasonal_naive", "Seasonal naive"), ("arima", "ARIMA(2,1,2)"))]
              + [["Raw GloFAS forecast", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a"],
                 ["LightGBM, config. A"] + [V(f"lgb_nse{h}") for h in (1, 2, 3)]
                 + [V(f"lgb_rmse{h}") for h in (1, 2, 3)],
                 ["LightGBM, config. E"] + [V(f"abE{h}") for h in (1, 2, 3)] + ["n/r"] * 3],
              [0.86 * inch] + [0.42 * inch] * 3 + [0.52 * inch] + [0.4 * inch] * 2, "base",
              "BASELINES AND LIGHTGBM, TEST PERIOD JULY 2022 &#8211; AUGUST 2026. RAW GLOFAS "
              "FORECASTS ARE NOT ARCHIVED (III-D); CONFIG. A: SEED 42; CONFIG. E: MEAN OF THREE "
              "SEEDS, RMSE NOT RECORDED (N/R)", small=True, bold_rows=(6, 7)),

          h2("B", "Risk-level detection"),
          p(f"The level-1 classifier detects {V('c1h1_hits')} of the {V('npos1')} level-1 days "
            f"one day ahead with {V('c1h1_fa')} false alarms (POD {V('c1h1_pod')}, FAR "
            f"{V('c1h1_far')}, CSI {V('c1h1_csi')}; Table {T['clf']}), better than thresholding "
            f"the regression forecast (CSI {V('dl_lgbcsi')}). Skill decays quickly: CSI "
            f"{V('c1h2_csi')} at h = 2 and {V('c1h3_csi')} at h = 3. Level 2 has only "
            f"{V('npos2')} positive test days; its POD is {V('c2h1_pod')} at h = 1 and zero "
            "beyond. The acceptance criterion for alert stage II (POD of at least "
            f"{V('ac2_pod')} one day ahead) can therefore be neither met nor evaluated "
            "reliably with this test set."),
          tbl([["Level", "h", "Positive test days", "POD", "FAR", "CSI", "PR-AUC"]]
              + [[f"{lv} ({V('thr' + lv)} {M3S})" if h == 1 else "", str(h),
                  V("npos" + lv)] + [V(f"c{lv}h{h}_{m}") for m in ("pod", "far", "csi", "pr_auc")]
                 for lv in ("1", "2") for h in (1, 2, 3)],
              [0.8 * inch, 0.22 * inch, 0.56 * inch] + [0.44 * inch] * 3 + [0.52 * inch], "clf",
              "DEDICATED RISK-LEVEL CLASSIFIERS ON THE TEST PERIOD", small=True),

          h2("C", "Imperfect rainfall (scenario B')"),
          p("Scenario B planned to replace observed by archived forecast rainfall, but the "
            "archive returned values identical to ERA5 (Report 2). It was replaced by a "
            f"sensitivity test with multiplicative log-normal noise of growing {SIGMA} on all "
            f"rainfall inputs. At {SIGMA} = 1, NSE falls from {V('sb0_h1')} to {V('sb1_h1')} "
            f"at h = 1 ({V('sb_drop1')} lower), from {V('sb0_h2')} to {V('sb1_h2')} at h = 2, "
            f"and does not fall at h = 3 ({V('sb0_h3')} to {V('sb1_h3')}); the noise-free run "
            f"matches the main model within {PM}{V('noise')}. The model leans on discharge "
            "lags, so imperfect rainfall costs little; for the same reason it cannot anticipate "
            "rain that has not yet fallen, which caps skill at h = 2&#8211;3."),

          h2("D", "Does more data help? (configurations A&#8211;E)"),
          p(f"A longer record (B) is the only change that helps at h = 1 ({V('abBA1')}; "
            f"Table {T['abl']}). Soil moisture (C) and storage proxies (D) add nothing "
            "measurable: that information is already carried by discharge lags and the API. "
            f"Storm, cold-surge and ENSO predictors (E) give the largest gain at h = 2 "
            f"({V('abED2')} over D, from {V('abA2')} for A to {V('abE2')}) and {V('abED3')} at "
            "h = 3: these drivers announce heavy rain one to three days ahead, which observed "
            f"rainfall cannot. The seed standard deviation is at most {V('ab_sd')}. No "
            f"configuration removes the peak bias ({V('ab_pbmax')} to {V('ab_pbmin')}), which "
            "points to the target itself (Section IV-I)."),
          tbl([["Config.", "Added", "NSE h=1", "h=2", "h=3"],
               ["A", f"Report 2 panel, train from 2010 ({V('ntrA')} days)",
                V("abA1"), V("abA2"), V("abA3")],
               ["B", f"Rainfall from 1997 ({V('ntrB')} days)", V("abB1"), V("abB2"), V("abB3")],
               ["C", "+ soil moisture", V("abC1"), V("abC2"), V("abC3")],
               ["D", "+ reservoir-storage proxies", V("abD1"), V("abD2"), V("abD3")],
               ["E", "+ storms, cold surges, ENSO", V("abE1"), V("abE2"), V("abE3")]],
              [0.42 * inch, 1.65 * inch] + [0.47 * inch] * 3, "abl",
              "CUMULATIVE ABLATION, SINGLE SPLIT, MEAN OF THREE SEEDS", small=True),

          h2("E", "Hourly rainfall (ERA5)"),
          p("Hourly ERA5 exists only from 2015, so this test uses its own split (train "
            "2015&#8211;2020, validation to June 2022, test from July 2022); its baseline is "
            "therefore lower. Nine basin-wide hourly features raise NSE at h = 3 from "
            f"{V('hrA3')} to {V('hrB3')}, consistently across seeds ({V('hrB3_s0')}, "
            f"{V('hrB3_s1')}, {V('hrB3_s2')}). At h = 2 the mean gain ({V('hrA2')} to "
            f"{V('hrB2')}) comes almost entirely from one seed ({V('hrB2_s0')}, {V('hrB2_s1')}, "
            f"{V('hrB2_s2')}). At h = 1 the gain is not intra-day information: daily totals "
            f"over the DEM sub-basins alone reach {V('hrB01')}, against {V('hrB1')} with hourly "
            f"features. Hourly features per sub-basin are no better than the basin mean "
            f"({V('hrC1')}, {V('hrC2')}, {V('hrC3')}): ERA5 is too coarse to separate them."),

          h2("F", "Satellite rainfall under walk-forward"),
          p(f"On the single split, IMERG appeared to lift E0 at h = 2 and 3 ({V('ss_im2')}, "
            f"{V('ss_im3')}). Across {V('wf_nfold')} yearly folds the effect shrinks to "
            f"{V('im2_m')} and {V('im3_m')} with intervals touching zero (Table {T['sat']}, "
            f"Fig. {F['sat']}). Gauge-calibrated GSMaP is the only source with a consistent "
            f"gain on the strong baseline: {V('gc3_m')} at h = 3, positive in {won('gc3_wl')} "
            f"folds (p = {V('gc3_p')}), and fewer level-1 false alarms at h = 1 ({V('fa_e0')} to "
            f"{V('fa_gc')} over {V('pos_wf')} pooled event days; CSI {V('csi_e0')} to "
            f"{V('csi_gc')}). At h = 2 the mean gain ({V('gc2_m')}) is not significant "
            f"(p = {V('gc2_p')}), and at h = 1 there is none. On the weaker baseline A0 the "
            f"same source gains more ({V('agc2_m')} at h = 2, positive in {won('agc2_wl')} folds): "
            "satellite rain partly stands in for predictors that E0 already contains."),
          tbl([["Config. (vs. own baseline)", "h = 1", "h = 2", "h = 3"],
               ["E0 + GSMaP-GC", f"{V('gc1_m')} ({V('gc1_wl')})",
                f"{V('gc2_m')}<br/>{V('gc2_ci')}<br/>{V('gc2_wl')}, p {V('gc2_p')}",
                f"{V('gc3_m')}<br/>{V('gc3_ci')}<br/>{V('gc3_wl')}, p {V('gc3_p')}"],
               ["E0 + IMERG", f"{V('im1_m')} ({V('im1_wl')})",
                f"{V('im2_m')}<br/>{V('im2_ci')}<br/>{V('im2_wl')}, p {V('im2_p')}",
                f"{V('im3_m')}<br/>{V('im3_ci')}<br/>{V('im3_wl')}, p {V('im3_p')}"],
               ["A0 + GSMaP-GC", f"{V('agc1_m')} ({V('agc1_wl')})",
                f"{V('agc2_m')}<br/>{V('agc2_ci')}<br/>{V('agc2_wl')}",
                f"{V('agc3_m')}<br/>{V('agc3_ci')}<br/>{V('agc3_wl')}"],
               ["E0 + GSMaP-GC, same day (latency run)", f"{V('lag0_1_m')} ({V('lag0_1_wl')})",
                f"{V('lag0_2_m')} ({V('lag0_2_wl')})",
                f"{V('lag0_3_m')}<br/>{V('lag0_3_ci')}<br/>{V('lag0_3_wl')}, p {V('lag0_3_p')}"],
               ["E0 + GSMaP-GC, lagged one day", f"{V('lag1_1_m')} ({V('lag1_1_wl')})",
                f"{V('lag1_2_m')} ({V('lag1_2_wl')})",
                f"{V('lag1_3_m')}<br/>{V('lag1_3_ci')}<br/>{V('lag1_3_wl')}, p {V('lag1_3_p')}"]],
              [1.06 * inch, 0.7 * inch, 0.86 * inch, 0.86 * inch], "sat",
              f"{DELTA}NSE FROM SATELLITE RAINFALL, {V('wf_nfold')} YEARLY FOLDS: MEAN, 95% "
              "INTERVAL, FOLDS WON/LOST. BASELINE NSE: E0 "
              f"{V('wfE0_1')}/{V('wfE0_2')}/{V('wfE0_3')}, A0 {V('wfA0_1')}/{V('wfA0_2')}/"
              f"{V('wfA0_3')}", small=True),
          p(f"<b>Latency.</b> On 20 October 2026 the newest GSMaP image on Earth Engine was "
            f"about {V('lat_gsmap')} h old (IMERG about {V('lat_imerg')} h). A forecast issued "
            "near 05:00 local time therefore has satellite rain only up to day t &#8211; 1. "
            "Re-running the walk-forward with GSMaP-GC features lagged by one day removes the "
            f"gain: {V('lag1_3_m')} {V('lag1_3_ci')} at h = 3 ({V('lag1_3_wl')} folds, "
            f"p = {V('lag1_3_p')}), against {V('lag0_3_m')} (p = {V('lag0_3_p')}) with "
            "same-day features in the same run. The benefit comes entirely from rain on the "
            "issue day itself. <i>The satellite gain is a reanalysis result; it is not yet an "
            "operational one.</i>")]

    # ---- IV-G: GSMaP_NRT (chờ kết quả)
    s += [h2("G", "Low-latency satellite rainfall (GSMaP_NRT)")]
    nrt_intro = (f"JAXA distributes a gauge-adjusted near-real-time GSMaP product published "
                 f"about {V('lat_nrt')} h after observation and reprocessed back to 1998. It is "
                 "a different product from the standard GSMaP on Earth Engine (hourly "
                 f"correlation {V('nrt_r_lo')}&#8211;{V('nrt_r_hi')}), so it has to be tested "
                 "by retraining on its own history rather than by substitution. With the "
                 "forecast job moved after 07:00 local time, this product would supply day-t "
                 "rain operationally.")
    if NRT is None:
        s += [p(nrt_intro),
              KeepTogether([pending(
                  "<b>[GSMaP_NRT operational test pending]</b> The 13-fold walk-forward "
                  "comparing GSMaP_NRT with the standard GSMaP-GC on baselines E0 and A0 "
                  "(<font face='Courier'>reports/wf_sat_nrt.csv</font>) has not finished. "
                  f"This subsection will report the mean {DELTA}NSE, 95% interval, folds "
                  "won/lost and Wilcoxon p per horizon, and state whether the h = 3 gain "
                  "survives in an operational setting.")])]
    else:
        s += [p(nrt_intro + f" Table {T['nrt']} gives the walk-forward result."),
              tbl([["Config. (vs. own baseline)", "h = 1", "h = 2", "h = 3"]] + NRT,
                  [1.06 * inch, 0.8 * inch, 0.8 * inch, 0.82 * inch], "nrt",
                  f"{DELTA}NSE FROM GSMAP_NRT AND STANDARD GSMAP-GC, YEARLY WALK-FORWARD",
                  small=True),
              pending("<b>[Interpretation pending team review]</b> Numbers above are computed "
                      "from <font face='Courier'>reports/wf_sat_nrt.csv</font> at build time; "
                      "the conclusion sentence must be written after the team has checked "
                      "them.")]

    # ---- IV-H: DL
    s += [NextPageTemplate(["wide_dl", "*", "rest"]),
          h2("H", "Deep learning versus LightGBM"),
          p(f"On the single split some of the {V('n_dlcfg')} DL configurations beat LightGBM "
            f"at h = 2 and 3 (best: a peak-weighted MLP, {V('dlmlp2')} against {V('lgb_nse2')} "
            "at h = 2), but the LSTM configuration selected on validation lost at all three "
            f"horizons ({V('dlsel1')}, {V('dlsel2')}, {V('dlsel3')} against {V('lgb_nse1')}, "
            f"{V('lgb_nse2')}, {V('lgb_nse3')}); the better configurations were identified "
            "only after seeing the test set. Under the yearly walk-forward, with every model "
            "on the Report 2 panel, no DL model beats "
            f"LightGBM consistently (Table {T['dl']}, Fig. {F['dl']}). The LSTM with MSE loss "
            f"is level at h = 1 ({V('lstmM1_m')}, interval includes zero) and slightly worse "
            f"at h = 2&#8211;3; the peak-weighted LSTM loses clearly at h = 3 "
            f"({V('lstmP3_m')}, p = {V('lstmP3_p')}). The single-split advantage at "
            "h = 2&#8211;3 appears only in 2022&#8211;2025, the years that split happened to "
            "test; in 2013&#8211;2021 every DL model loses on average at h = 2 and 3."),
          tbl([["Model", "h = 1", "h = 2", "h = 3", "CSI level 1, h = 1"],
               ["LightGBM (NSE)", V("dl_lgb1"), V("dl_lgb2"), V("dl_lgb3"), V("csi_lgb")]]
              + [[name] + [f"{V(t + str(h) + '_m')}<br/>{V(t + str(h) + '_ci')}<br/>"
                           f"{V(t + str(h) + '_wl')}" for h in (1, 2, 3)] + [V(c)]
                 for t, name, c in (("lstmM", "LSTM L=30, MSE", "csi_lstmM"),
                                    ("lstmP", "LSTM L=30, peak-weighted", "csi_lstmP"),
                                    ("mlpP", "MLP on lags, peak-weighted", "csi_mlpP"))],
              [0.98 * inch, 0.72 * inch, 0.72 * inch, 0.72 * inch, 0.38 * inch], "dl",
              f"DEEP LEARNING VERSUS LIGHTGBM, {V('wf_nfold')} YEARLY FOLDS: {DELTA}NSE MEAN, "
              "95% INTERVAL, FOLDS WON/LOST; POOLED CSI", small=True),
          p("DL has two genuine strengths at h = 1: it detects more level-1 days (POD "
            f"{V('pod_lstmM')}&#8211;{V('pod_mlpP')} against {V('pod_lgb')}; pooled CSI "
            f"{V('csi_lstmM')} against {V('csi_lgb')}) and cuts peaks less (peak bias "
            f"{V('pb_mlpP')} to {V('pb_lstmP')} against {V('pb_lgb')}). It is also far less "
            f"stable: the seed-to-seed spread is {V('sd_dl_lo')}&#8211;{V('sd_dl_hi')} NSE "
            f"against at most {V('sd_lgb')} for LightGBM, and the torch thread count moves the "
            f"MLP by up to {V('thr_rng')} while leaving the LSTM unchanged. LightGBM remains "
            "the main model."),

          h2("I", "Reservoirs: is the dam signal in GloFAS?"),
          p(f"If GloFAS v4 represented the Ta Trach ({V('cap_tt')} million m&#179;) and Binh "
            f"Dien ({V('cap_bd')} million m&#179;) reservoirs, the simulated series after both "
            "dams were operating (2014&#8211;2026) should show higher dry-season flow, lower "
            "flashiness and a weaker storm response than before them (1998&#8211;2008). None "
            f"of the four indices changes significantly (Table {T['r1']}), and the three "
            "dam-sensitive ones move the wrong way or not at all. The target behaves as an "
            "unregulated river, so reservoir effects cannot be learned from it (R1)."),
          tbl([["Index", "Before", "After", "Change", "p"],
               [f"30-day low flow ({M3S})", V("r1_low_flow_30d_pre"), V("r1_low_flow_30d_post"),
                V("r1_low_flow_30d_chg") + "%", V("r1_low_flow_30d_p")],
               ["Runoff ratio", V("r1_runoff_ratio_pre"), V("r1_runoff_ratio_post"),
                V("r1_runoff_ratio_chg") + "%", V("r1_runoff_ratio_p")],
               ["Flashiness (Richards&#8211;Baker)", V("r1_flashiness_rb_pre"),
                V("r1_flashiness_rb_post"), V("r1_flashiness_rb_chg") + "%", V("r1_flashiness_rb_p")],
               ["Storm response", V("r1_response_pre"), V("r1_response_post"),
                V("r1_response_chg") + "%", V("r1_response_p")]],
              [1.3 * inch, 0.5 * inch, 0.5 * inch, 0.55 * inch, 0.4 * inch], "r1",
              f"GLOFAS BEFORE (1998&#8211;2008, {V('r1_npre')} YEARS) AND AFTER "
              f"(2014&#8211;2026, {V('r1_npost')} YEARS) THE DAMS: MEDIANS, MANN&#8211;WHITNEY p "
              f"(STORM RESPONSE: {V('r1_ev_pre')} AND {V('r1_ev_post')} EVENTS)", small=True),
          col_fig("res2_release_vs_glofas_en.png", "r2",
                  "Reported dam releases and natural inflows (lower bounds) against GloFAS at "
                  "the Kim Long cell. Points below the diagonal are physically impossible for "
                  "the real river.", scale=0.74),
          p("Bulletins give two conservative lower bounds for the flow reaching Kim Long: the "
            "smallest release reported for each reservoir on a day, and the reported natural "
            f"inflow to the two reservoirs, whose catchments ({V('dam_area')} {KM2}) make up "
            f"most of the basin. GloFAS (the larger of days t and t + 1) is below the release "
            f"bound on {of('r2_rel')} days and below the inflow bound on {of('r2_inf')} (Fig. "
            f"{F['r2']}, R2). On 15 October 2022 the dams released at least "
            f"{V('r2_2022-10-15_q_release_upstream_min')} {M3S} with an inflow of "
            f"{V('r2_2022-10-15_q_inflow_upstream')} {M3S}, while GloFAS gave "
            f"{V('r2_2022-10-15_glofas_best')} {M3S}; on 27 October 2025 the figures were "
            f"{V('r2_2025-10-27_q_release_upstream_min')}, {V('r2_2025-10-27_q_inflow_upstream')} "
            f"and {V('r2_2025-10-27_glofas_best')} {M3S}. Bulletins report instantaneous values "
            "and GloFAS daily means, which explains part of the gap but not several-fold "
            "differences. The dominant problem is not reservoir operation but that GloFAS "
            "under-simulates the largest floods, consistent with ERA5 under-estimating extreme "
            "orographic rain. This supports relative, percentile-based risk levels and "
            "motivates the floor rule of Section III-H.")]

    # ============================================================ V
    s += [h1("V", "Explainability"),
          p("Split-gain importance is a poor guide for this model: at h = 2 the two seasonal "
            "encodings rank first and second by gain, yet removing them in an earlier "
            "ablation did not lower NSE at any horizon, because the same information is "
            "carried by discharge and rainfall lags. SHAP values attribute each individual "
            "forecast to its inputs and are a standard explanation tool for tree ensembles "
            "in streamflow forecasting [9]; they are used here to check whether the main "
            "model relies on hydrologically plausible signals.")]
    if not SHAP:
        s += [pending("<b>[SHAP section pending]</b> Global importance (mean |SHAP| per "
                      "feature and mechanism group, per horizon), a check of the sign of each "
                      "effect and a case study of the largest test flood will be inserted here "
                      "from <font face='Courier'>reports/shap_importance.csv</font> once the "
                      "SHAP run is complete.")]
    else:
        G = list(fx.SHAP_GROUPS.items())
        s += [h2("A", "Set-up"),
              p("Tree SHAP values were computed for configuration E (88 features), trained on "
                "train plus validation with seed 42 and explained on the test period, in units "
                "of log(1 + Q) so that the base value plus the contributions equals the "
                "forecast. The run reproduces the ablation exactly (NSE "
                f"{V('shap_nse1')}, {V('shap_nse2')}, {V('shap_nse3')}). Correlated inputs "
                "(discharge and its lags; the three rainfall bands) share credit arbitrarily, so "
                f"results are read by mechanism group (Table {T['shap']}); recomputing the "
                f"shares with seeds 7 and 2026 changes them by at most {V('shap_spread')} "
                "percentage points."),
              tbl([["Group", "All test days h=1", "h=2", "h=3", "Level-1 days h=1", "h=2", "h=3"]]
                  + [[lab] + [V(f"sg_{g}_{h}") for h in (1, 2, 3)]
                     + [V(f"sgf_{g}_{h}") for h in (1, 2, 3)] for g, lab in G],
                  [1.06 * inch, 0.44 * inch, 0.36 * inch, 0.36 * inch, 0.48 * inch,
                   0.36 * inch, 0.36 * inch], "shap",
                  "SHARE OF GROUPED MEAN |SHAP| (%), CONFIGURATION E, SEED 42", small=True),
              h2("B", "What the model relies on"),
              p(f"Today's discharge dominates at h = 1 ({V('sf_discharge_1')}% of mean |SHAP|), "
                f"followed by upper-basin ({V('sf_rain_thuong_1')}%) and basin-mean rainfall "
                f"({V('sf_rain_basin_1')}%). With lead time the weight moves from lagged "
                f"discharge ({V('sg_flow_1')}% to {V('sg_flow_3')}% by group) to rainfall and "
                "to large-scale drivers: the pressure, wind and humidity group grows from "
                f"{V('sg_synoptic_1')}% to {V('sg_synoptic_3')}%, and the north&#8211;south "
                "pressure gradient that marks cold surges becomes the third feature at h = 3 "
                f"({V('sf_mslp_grad_north_3')}%), behind basin rainfall "
                f"({V('sf_rain_basin_3')}%) and discharge ({V('sf_discharge_3')}%). This is the "
                f"mechanism behind the {V('abED2')} gain of configuration E at h = 2. The "
                "direction is physically right for the core inputs: the Spearman correlation "
                f"between a feature and its own SHAP value is {V('rho_discharge_1')} for "
                f"discharge at h = 1 and {V('rho_mslp_grad_north_1')} to "
                f"{V('rho_mslp_grad_north_3')} for the pressure gradient."),
              h2("C", "Where the model is not plausible"),
              *bullets([
                  "<b>Soil moisture acts in reverse.</b> For the 7&#8211;28 cm ERA5-Land layer "
                  f"the correlation is {V('rho_sm_7_28_1')}, {V('rho_sm_7_28_2')} and "
                  f"{V('rho_sm_7_28_3')}: wetter soil lowers the forecast, and the soil and "
                  f"API group is negative on level-1 days at every horizon ({V('soil_signed1')}, "
                  f"{V('soil_signed2')}, {V('soil_signed3')} in log units). Soil moisture "
                  "largely duplicates the wetness already contained in today's discharge, so "
                  "the model uses it as a correction term. It must not be cited as a flood "
                  "mechanism.",
                  "<b>The full-reservoir proxy is not supported.</b> Rain accumulated since 1 "
                  f"September has correlations of {V('rho_rain_season_cum_1')}, "
                  f"{V('rho_rain_season_cum_2')} and {V('rho_rain_season_cum_3')}, consistent "
                  "with R1: the target contains no reservoir.",
                  f"<b>Climatology at h = 3.</b> The calendar group carries {V('sg_season_3')}% "
                  "at h = 3: when the dynamical signal is weak the model partly falls back on "
                  "the season.",
              ]),
              h2("D", "Why peaks are cut"),
              p(f"For the forecast issued on 15 October 2022 (Fig. {F['shap']}), discharge and "
                "rainfall push the forecast strongly upward, yet it reaches only "
                f"{V('wf_fc_2022')} {M3S} against a GloFAS peak of "
                f"{V('r2_2022-10-15_glofas_best')} {M3S}. The limit is structural rather than "
                f"a missing feature: only {V('wf_n_above')} of the {V('ntrE')} training days "
                f"exceed that peak, each leaf must hold at least {V('lgb_mcs')} training days, "
                "and the L1 loss on log discharge targets the conditional median. Moreover, "
                f"every training day with discharge above {V('wf_q2000')} {M3S} receded the "
                "next day, so the model predicts recession even while the river is still "
                f"rising: on 30 October 2025 it gave {V('wf_fc_2025')} {M3S} against "
                f"{V('q_max_test')} {M3S}, the largest flow of the test period. The remedy is "
                "quantile regression or a smaller minimum leaf size, chosen on validation, not "
                "more predictors."),
              col_fig("shap_waterfall_20221016_h1_en.png", "shap",
                      "SHAP waterfall (log(1 + Q) units) for the forecast issued on 15 October "
                      "2022 for the GloFAS peak of the next day: discharge and rainfall push "
                      "upward, but the forecast stays far below the peak.", scale=0.9)]

    # ============================================================ VI
    s += [h1("VI", "Discussion and Limitations"),
          *bullets([
              "<b>The target is simulated.</b> Every score measures agreement with GloFAS, "
              "not with the river. LightGBM cuts peaks relative to GloFAS, and GloFAS itself "
              "under-simulates the largest floods (Section IV-I), so true peaks are "
              "under-estimated further. The quantile regression announced in Report 2 has "
              "not yet been run.",
              "<b>Regime change in July 2022.</b> The test period consists of archived "
              "forecasts. Report 2 found no systematic shift in the rainfall response "
              f"(Mann&#8211;Whitney p = {V('mw_p')} in the heavy-rain tail), but that test "
              "assumes ERA5 is right, and the archived regime has too few folds to be tested "
              "alone. GloFAS v5 adds large reservoirs; Ta Trach and Binh Dien meet its "
              "storage and area criteria, so the target may change when Open-Meteo moves to "
              "v5, and R1 must then be repeated.",
              "<b>Satellite latency.</b> The h = 3 gain from GSMaP-GC exists only when "
              "same-day rain is available. Through Earth Engine it is not; the operational "
              "value depends on the GSMaP_NRT test (Section IV-G).",
              "<b>No hourly target.</b> Finer and hourly inputs were tested, but the target "
              "is still daily GloFAS discharge on a ~5 km grid. An hourly target would need "
              "observed hourly water levels at Kim Long from the national hydro-meteorological "
              "service; the team decided not to request these data, so hourly forecasting of "
              "the river itself is out of scope.",
              f"<b>Rare events and labels.</b> Only level 1 has enough test events "
              f"({V('npos1')} days). Risk levels are relative to GloFAS and are not official "
              f"alert stages, because discharge explains little of the water level "
              f"(R&#178; = {V('hq_r2')}).",
              f"<b>Resolution of comparisons.</b> NSE differences below about {V('noise')} "
              "are numerical noise; differences between configurations are reported with "
              "fold-level intervals, and statements rest on those intervals, not on means.",
          ])]

    # ============================================================ VII
    s += [h1("VII", "Conclusion and Plan for Report 4"),
          p("LightGBM on open data forecasts GloFAS discharge at Kim Long with clear skill "
            f"over all baselines (NSE {V('lgb_nse1')}, {V('lgb_nse2')}, {V('lgb_nse3')}) and "
            f"detects level-1 risk one day ahead with CSI {V('c1h1_csi')}, but cuts peaks and "
            "loses most skill beyond one day. Of the factors raised in the review, reservoir "
            "releases cannot be learned from a target that does not contain them and are "
            "handled by a floor rule; large-scale weather predictors help at h = 2; "
            "satellite and hourly rainfall help at h = 3 only in hindsight; and deep learning "
            "does not beat LightGBM once evaluated across years. Report 4 will:"),
          *bullets([
              "run the GSMaP_NRT walk-forward and, if the gain holds, move the daily job "
              "after 07:00 so that day-t satellite rain is available;",
              "compare the model with the raw GloFAS forecasts logged since 15 September "
              "2026, and report the event-based scores of the 2026 flood season;",
              ("test, on validation folds only, the removal of soil moisture and of the "
               "reservoir proxy that SHAP flags as implausible, and " if SHAP else
               "complete the SHAP analysis, and ")
              + "address peak cutting with quantile regression or a smaller minimum leaf "
              "size, and with a cost-based warning threshold;",
              f"present the Spark pipeline honestly: on a two-worker cluster it reproduces "
              f"the Polars ETL exactly ({V('etl_rows_in')} hourly rows to {V('etl_rows_out')} "
              f"cell-days) but takes {V('etl_c2_lo')}&#8211;{V('etl_c2_hi')} s against "
              f"{V('etl_pl_lo')}&#8211;{V('etl_pl_hi')} s for Polars on one machine; MLlib "
              f"models (GBT {V('sp_gbt1')}, random forest {V('sp_rf1')} at h = 1) do not "
              "beat LightGBM; and",
              "report the walk-forward as the main comparison for every model, with the "
              "single split as one case among thirteen.",
          ])]

    # ============================================================ refs
    s += [p("REFERENCES", "h1")]
    refs = [
        "[1] Open-Meteo, &#8220;Flood API and Historical Weather API,&#8221; 2026. [Online]. "
        "Available: https://open-meteo.com/en/docs",
        "[2] S. Harrigan <i>et al.</i>, &#8220;Daily ensemble river discharge reforecasts and "
        "real-time forecasts from the operational Global Flood Awareness System,&#8221; "
        "<i>Hydrol. Earth Syst. Sci.</i>, vol. 27, no. 1, pp. 1&#8211;19, 2023.",
        "[3] H. Hersbach <i>et al.</i>, &#8220;The ERA5 global reanalysis,&#8221; <i>Q. J. R. "
        "Meteorol. Soc.</i>, vol. 146, no. 730, pp. 1999&#8211;2049, 2020.",
        "[4] Prime Minister of Vietnam, &#8220;Decision 05/2020/QD-TTg on water levels "
        "corresponding to flood alert levels,&#8221; <i>Official Gazette</i>, no. 179+180, "
        "Feb. 2020, Annex I, row 135. [in Vietnamese]",
        "[5] H. S. Nguyen <i>et al.</i>, &#8220;Synoptic patterns causing heavy rain and "
        "floods in Thua Thien Hue province in 2020,&#8221; <i>Hue Univ. J. Sci.: Earth Sci. "
        "Environ.</i>, vol. 131, no. 4A, pp. 149&#8211;162, 2022. [in Vietnamese]",
        "[6] G. Nearing <i>et al.</i>, &#8220;Global prediction of extreme floods in ungauged "
        "watersheds,&#8221; <i>Nature</i>, vol. 627, pp. 559&#8211;563, 2024.",
        "[7] V. Nourani, S. Kheirieh, S. A. Kantoush and J. J. Huang, &#8220;Bias correction "
        "of Global Flood Awareness System (GloFAS) data for multi-station river flow "
        "prediction by ensemble modelling,&#8221; <i>Eng. Appl. Comput. Fluid Mech.</i>, "
        "vol. 20, no. 1, 2665857, 2026.",
        "[8] T. Honcharenko <i>et al.</i>, &#8220;Explainable deep ensemble bias correction of "
        "GloFAS-ERA5 streamflow across snow-influenced transboundary basins of Central "
        "Asia,&#8221; <i>Water</i>, vol. 18, no. 16, 2055, 2026.",
        "[9] S. Gnjato, I. Lescesen, X. Zhou and D. Dukanovic, "
        "&#8220;Explainable machine learning for streamflow forecasting: application to the "
        "Bosna River basin,&#8221; <i>Water</i>, vol. 18, no. 10, 1226, 2026.",
        "[10] J. H. Ougahi and J. S. Rowan, &#8220;Investigating deep learning knowledge "
        "transfer in streamflow prediction from global to local catchment,&#8221; <i>Water "
        "Resour. Res.</i>, 2026, doi: 10.1029/2025WR041194.",
        "[11] Prime Minister of Vietnam, &#8220;Decision 1606/QD-TTg on the inter-reservoir "
        "operating procedure for the Huong River basin,&#8221; Nov. 2019. [Online]. "
        "Available: https://datafiles.chinhphu.vn/cpp/files/vbpq/2019/11/1606.signed.pdf "
        "[in Vietnamese]",
        "[12] UNESCO-IHP, <i>Catalogue of Rivers for Southeast Asia and the Pacific</i>, "
        "vol. V, entry Viet Nam-8 (Huong River).",
        "[13] NASA, &#8220;GPM IMERG V07, Earth Engine collection NASA/GPM_L3/IMERG_V07.&#8221;",
        "[14] JAXA, &#8220;GSMaP v8 operational, Earth Engine collection "
        "JAXA/GPM_L3/GSMaP/v8/operational.&#8221;",
        "[15] NOAA NCEI, &#8220;International Best Track Archive for Climate Stewardship "
        "(IBTrACS) v04r01.&#8221; [Online]. Available: https://www.ncei.noaa.gov/data/"
        "international-best-track-archive-for-climate-stewardship-ibtracs/",
        "[16] NOAA CPC, &#8220;Oceanic Ni&#241;o Index.&#8221; [Online]. Available: "
        "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "[17] ESA/Copernicus, &#8220;Copernicus DEM GLO-30.&#8221; [Online]. Available: "
        "https://copernicus-dem-30m.s3.amazonaws.com/",
    ]
    s += [p(r, "ref") for r in refs]
    return s


def no_orphans(flowables: list) -> list:
    """Trước mỗi tiêu đề: nếu cột còn quá ít chỗ thì sang cột mới (tiêu đề không mồ côi).
    Dùng CondPageBreak thay keepWithNext — keepWithNext gói cả đoạn văn dài đi theo và
    để lại khoảng trắng lớn."""
    out = []
    for fl in flowables:
        name = getattr(getattr(fl, "style", None), "name", "")
        if name in ("h1", "h2"):
            out.append(CondPageBreak((1.1 if name == "h1" else 0.85) * inch))
        out.append(fl)
    return out


# ======================================================= kiểm ký tự + quét số
ALLOWED = set(range(32, 127)) | {
    0xA0, 0xB0, 0xB1, 0xB2, 0xB3, 0xB5, 0xB7, 0xD7, 0xF1,          # nbsp ° ± ² ³ µ · × ñ
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022,        # – — ‘ ’ “ ” •
}


def walk(fl):
    """Mọi Paragraph bên trong flowable (kể cả ô bảng và KeepTogether)."""
    if isinstance(fl, Paragraph):
        yield fl
    elif isinstance(fl, KeepTogether):
        for c in fl._content:
            yield from walk(c)
    elif isinstance(fl, Table):
        for row in fl._cellvalues:
            for c in row:
                yield from walk(c)
    elif isinstance(fl, (list, tuple)):
        for c in fl:
            yield from walk(c)


def plain(txt: str) -> str:
    t = re.sub(r'<font face="Symbol">[^<]*</font>', "~", txt)   # Δ, σ: font Symbol, hợp lệ
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), t)
    return t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


NUM = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+")


def check_text(flowables) -> int:
    probs, unknown, n_num = [], set(), 0
    known = V.numbers()
    for para in walk(flowables):
        is_ref = para.style.name == "ref"
        t = plain(para.text)
        for ch in set(t):
            if ord(ch) not in ALLOWED:
                i = t.index(ch)
                probs.append(f"  U+{ord(ch):04X} '{ch}' … {t[max(0, i - 30):i + 30]!r}")
        if is_ref:
            continue
        for m in NUM.finditer(t):
            n_num += 1
            if m.group(0) not in known:
                unknown.add(f"  {m.group(0)!r} … {t[max(0, m.start() - 40):m.end() + 20]!r}")
    if probs:
        raise SystemExit("Ký tự font Times không vẽ được (sẽ thành ô đen):\n"
                         + "\n".join(sorted(set(probs))[:25]))
    if unknown:
        raise SystemExit("Số trong văn bản KHÔNG có trong sổ số liệu (facts.py) — đăng ký "
                         "kèm nguồn hoặc bỏ đi:\n" + "\n".join(sorted(unknown)[:30]))
    return n_num


# ================================================================== bố cục
def build() -> int:
    fx.load(cfg)
    if SHAP and not fx.load_shap():
        raise SystemExit("shap_importance.csv biến mất giữa chừng")
    if V.bad:
        raise SystemExit("Số trong báo cáo lệch với dữ liệu — sửa văn bản trước khi build:\n"
                         + "\n".join(V.bad))

    W = PW - LM - RM
    avail_h = PH - TM - BM

    def fr(x, y, w, h, i):
        return Frame(x, y, w, h, id=i, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Times-Roman", 8.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(PW / 2, BM - 26, str(d.page))
        canvas.drawString(LM, BM - 26, "DSP391m - Data Science Project - Report 3")
        canvas.drawRightString(PW - RM, BM - 26, "FPT University, Fall 2026")
        canvas.restoreState()

    wide_caps: list[Paragraph] = []

    def wide(tid: str, img: ImageReader, key: str, caption: str) -> PageTemplate:
        """Hình rộng hai cột ở đầu trang (kiểu figure* của IEEE), vẽ thẳng lên canvas."""
        iw, ih = img.getSize()
        h_img = W * ih / iw
        cap = Paragraph(f"Fig. {F[key]}.&nbsp; {caption}", ST["capwide"])
        wide_caps.append(cap)
        _, h_cap = cap.wrap(W, PH)
        block = h_img + 4 + h_cap + 12

        def on_page(canvas, d):
            footer(canvas, d)
            top = PH - TM
            canvas.drawImage(img, LM, top - h_img, width=W, height=h_img)
            cap.drawOn(canvas, LM, top - h_img - 4 - h_cap)

        return PageTemplate(id=tid, onPage=on_page, frames=[
            fr(LM, BM, COLW, avail_h - block, tid + "l"),
            fr(LM + COLW + GUT, BM, COLW, avail_h - block, tid + "r")])

    head = [
        p("Modelling and Evaluation of One-to-Three-Day Discharge and Flood-Risk Forecasts "
          "for the Huong River at Kim Long", "title"),
        p(("&nbsp;" * 4).join(cfg.TEAM_ASCII), "author"),
        Spacer(1, 3),
        p("Department of Information Technology, FPT University<br/>"
          "DSP391m &#8212; Data Science Project &#8212; Fall 2026<br/>Hue, Vietnam", "affil"),
        Spacer(1, 9),
        Paragraph(
            "<b><i>Abstract</i></b>&#8212;<font size=9>This report presents the modelling and "
            "evaluation stage of a project that forecasts the daily discharge and flood-risk "
            "level of the Huong River at Kim Long, Vietnam, one to three days ahead from open "
            f"data. A LightGBM model on log discharge reaches NSE = {V('lgb_nse1')}, "
            f"{V('lgb_nse2')} and {V('lgb_nse3')} at one, two and three days on a test period "
            f"from July 2022, against {V('persistence_nse1')}, {V('persistence_nse2')} and "
            f"{V('persistence_nse3')} for persistence, and a dedicated classifier detects the "
            f"first risk level one day ahead with POD = {V('c1h1_pod')} and FAR = "
            f"{V('c1h1_far')}. Responding to the review of Report 2, we tested reservoir "
            "releases, a longer record, large-scale weather drivers, finer and hourly "
            "satellite rainfall, and deep learning. GloFAS v4 shows no trace of the two "
            "upstream dams, and reported natural inflows exceed the simulated discharge on "
            f"{of('r2_inf')} days, so reservoir orders enter as a raise-only floor rule. "
            f"Storm, cold-surge and ENSO predictors raise NSE at two days from {V('abA2')} to "
            f"{V('abE2')}. In a {V('wf_nfold')}-fold yearly walk-forward, gauge-calibrated "
            f"GSMaP rainfall adds {V('gc3_m')} NSE at three days (positive in {won('gc3_wl')} "
            "folds), but "
            f"the gain vanishes ({V('lag1_3_m')}) once the one-day delivery delay of the "
            "archive is imposed: it is a reanalysis result, not yet an operational one. LSTM "
            "and MLP models do not beat LightGBM consistently."
            + (" SHAP attributions are plausible at the core (today's discharge and upstream "
               "rain, with pressure gradients gaining weight with lead time) but reveal a "
               "reversed soil-moisture effect." if SHAP else "")
            + " We also correct the catchment "
            f"area used earlier from {V('area_sys')} to about {V('area_cfg')} {KM2}.</font>",
            ST["abstext"]),
        Paragraph(
            "<b><i>Keywords</i></b>&#8212;<font size=9>flood forecasting, LightGBM, "
            "walk-forward validation, satellite precipitation, reservoir operation, GloFAS, "
            "rare-event verification, Huong River</font>", ST["keywords"]),
    ]
    head_h = sum(fl.wrap(W, PH)[1] + fl.getSpaceBefore() + fl.getSpaceAfter() for fl in head) + 8

    sat_img, dl_img = crop_sat(), crop_dl()
    doc = BaseDocTemplate(str(OUT), pagesize=(PW, PH), leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM,
                          title="DSP391m Report 3 - Modelling and Evaluation",
                          author=", ".join(cfg.TEAM_ASCII))
    doc.addPageTemplates([
        PageTemplate(id="first", onPage=footer, frames=[
            fr(LM, PH - TM - head_h, W, head_h, "head"),
            fr(LM, BM, COLW, avail_h - head_h, "c1l"),
            fr(LM + COLW + GUT, BM, COLW, avail_h - head_h, "c1r")]),
        PageTemplate(id="rest", onPage=footer, frames=[
            fr(LM, BM, COLW, avail_h, "cl"),
            fr(LM + COLW + GUT, BM, COLW, avail_h, "cr")]),
        wide("wide_sat", sat_img, "sat",
             f"Satellite rainfall under yearly walk-forward (baseline E0, train from 1998). "
             f"{DELTA}NSE of each test year for IMERG and gauge-calibrated GSMaP added to E0, "
             "ensemble of three seeds; legends give the mean, folds won/lost and Wilcoxon p "
             "over 2013&#8211;2025. Shaded: GloFAS regime change (07/2022). Hollow markers: "
             "January&#8211;August 2026, excluded from the summary."),
        wide("wide_dl", dl_img, "dl",
             f"Deep learning against LightGBM under the same walk-forward (panel from 2010): "
             f"{DELTA}NSE per test year, positive when DL is better. The grey band is the "
             "largest change caused by the torch thread count (folds 2020 and 2024)."),
    ])

    body = no_orphans(story())
    n_num = check_text(head + body + wide_caps)
    doc.build(head + [NextPageTemplate("rest")] + body)
    n_pages = doc.page
    write_outline(n_pages)

    k = V.kind.values()
    print(f"Đối chiếu số: {sum(1 for x in k if x == 'csv')} giá trị khớp nguồn, "
          f"{sum(1 for x in k if x == 'claim')} câu định tính đúng, "
          f"{sum(1 for x in k if x == 'doc')} số chỉ có trong tài liệu (ghi nguồn)")
    n_used = sum(1 for k in V.used if V.kind[k] == "csv")
    print(f"Trong PDF: {n_used} số in ra đã kiểm với file nguồn; quét {n_num} số thập phân / "
          "số nghìn trong văn bản, tất cả có trong sổ")
    for w in WARN:
        print(f"CẢNH BÁO: {w}")
    print(f"→ {_rel(OUT)}  ({n_pages} trang, {OUT.stat().st_size // 1024} KB)")
    print(f"→ {_rel(OUTLINE)}")
    return 0


# ============================================================ dàn ý tiếng Việt
def write_outline(n_pages: int) -> None:
    o = V.val
    pend_nrt = "CHỜ — reports/wf_sat_nrt.csv chưa có" if NRT is None else \
        "ĐÃ CÓ bảng số (tự tính lúc build) — CẦN viết câu kết luận"
    pend_shap = "CHỜ — reports/shap_importance.csv chưa có" if not SHAP else \
        "ĐÃ VIẾT từ shap_importance.csv + docs/FINDINGS_SHAP.md (số đã kiểm)"
    shap_lines = "" if not SHAP else (
        f" - SHAP trên cấu hình E (88 feature, seed 42), tái lập đúng NSE ablation ({o['shap_nse1']} / "
        f"{o['shap_nse2']} / {o['shap_nse3']}).\n"
        f" - h1 → h3: nhóm lưu lượng trễ {o['sg_flow_1']} % → {o['sg_flow_3']} %; khí áp/gió/ẩm "
        f"{o['sg_synoptic_1']} % → {o['sg_synoptic_3']} %; chênh áp Bắc–Huế (KK lạnh) hạng {o['rank_mslp3']} ở h3.\n"
        f" - KHÔNG hợp lý: độ ẩm đất ngược chiều (rho {o['rho_sm_7_28_1']} / {o['rho_sm_7_28_2']} / "
        f"{o['rho_sm_7_28_3']}); 'hồ đầy' (mưa từ 01/09) không được ủng hộ; h3 dựa {o['sg_season_3']} % vào lịch.\n"
        f" - Cắt ngọn lũ là giới hạn cấu trúc: 16/10/2022 dự báo {o['wf_fc_2022']} so với {o['r2_2022-10-15_glofas_best']} m³/s; "
        f"chỉ {o['wf_n_above']}/{o['ntrE']} ngày train vượt đỉnh đó; lá tối thiểu {o['lgb_mcs']} ngày.\n")
    lines = f"""DÀN Ý REPORT 3 — MÔ HÌNH & ĐÁNH GIÁ (IEEE, {n_pages} trang)
File: reports/report3/DSP391m_Report3_Modelling_Evaluation_IEEE.pdf
Build: python reports/report3/build_report.py   (mọi số được kiểm với CSV lúc build)

Câu định vị (nói xuyên suốt): mô hình là LỚP HIỆU CHỈNH CỤC BỘ trên GloFAS, không thay GloFAS.
Biến mục tiêu vẫn là lưu lượng GloFAS v4 theo ngày, ô ~5 km tại ({o['pt_lat']} N, {o['pt_lon']} E).

I. GIỚI THIỆU
 - Nhắc lại bài toán: dự báo lưu lượng Kim Long 1–3 ngày + mức nguy cơ, chỉ dữ liệu mở.
 - Góp ý của thầy ở Report 2: (1) xả hồ và các yếu tố khác, (2) ô mịn hơn 5 km, (3) theo giờ;
   Report 4: Spark + DL. Bảng I: góp ý → đã làm gì → kết quả.
 - Ràng buộc: đầu vào mịn/giờ KHÔNG làm biến mục tiêu mịn hơn.

II. CẬP NHẬT DỮ LIỆU
 A. Mưa ERA5 mở rộng về 1997 → train tăng {o['ntrA']} → {o['ntrB']} ngày. Thêm độ ẩm đất ERA5-Land,
    bão IBTrACS ({o['storms']} cơn trong {o['storm_km']} km), không khí lạnh (chênh áp Hà Nội–Huế, gió ĐB),
    ENSO (ONI trễ 3 tháng).
 B. ĐÍNH CHÍNH Report 2: diện tích lưu vực tới Kim Long ~{o['area_cfg']} km² (DEM {o['area_dem']} km²),
    KHÔNG phải {o['area_sys']} km² ({o['area_sys']} là cả hệ thống Hương gồm sông Bồ {o['area_bo']} km²).
    Ô lưới đã chọn KHÔNG đổi: Q_tb {o['q_cell']} m³/s ⇒ {o['imp_lo']}–{o['imp_hi']} km².
 C. 5 lưu vực con từ DEM 30 m (Hình 1): Tả Trạch {o['a_tt']}, Bình Điền {o['a_bd']}, dưới đập {o['a_ttb']} + {o['a_htb']},
    Tuần–Kim Long {o['a_tkl']} km². ERA5 chỉ phủ {o['cov_era5']} %, lưới vệ tinh phủ 100 %.
 D. Mưa vệ tinh IMERG V07, GSMaP v8 (+ GC) 1998–10/2026 theo giờ qua Earth Engine. PERSIANN-CCS 0,04°
    bị loại (tháng 11/2020 chỉ ghi được {o['pccs_nov']} lượng mưa ERA5). ERA5 tương quan với GloFAS cao
    nhất vì GloFAS chạy bằng ERA5 — không có nghĩa ERA5 đúng hơn.
 E. Số liệu hồ: {o['rel_rows']} dòng, {o['rel_days']} ngày, có URL + trích nguyên văn — chỉ để kiểm chứng và luật,
    không làm feature.

III. PHƯƠNG PHÁP
 - Mục tiêu Q(t+h), h = 1..3; feature chỉ dùng thông tin tới hết ngày t; test tự động chống rò rỉ.
 - Cấu hình A→E ({o['nfA']} → {o['nfE']} feature). LightGBM log1p, L1, {o['lgb_trees']} cây, lr {o['lgb_lr']}, 3 seed.
   MÔ HÌNH CHÍNH từ Report 3 = cấu hình E (NSE {o['abE1']} / {o['abE2']} / {o['abE3']}); A chỉ là mốc cho tiêu chí AC.
 - Bộ phân loại nhị phân từng mức, trọng số lớp, ngưỡng {o['clf_thr']}. DL: LSTM (cửa sổ 14/30 ngày), MLP.
 - Baseline: persistence, climatology, seasonal naive, ARIMA. GloFAS thô KHÔNG dựng lại được quá khứ
   (404) → nhật ký dự báo từ 15/09/2026, so sánh ở Report 4.
 - Walk-forward 13 fold theo năm 2013–2025, train mở rộng, gap 3 ngày, ngưỡng tính lại trong mỗi fold,
   CI bootstrap theo fold + Wilcoxon. Ngưỡng nhiễu NSE ±{o['noise']}.
 - Vì sao không đổi sang mét: R² H–Q = {o['hq_r2']} trên {o['hq_n']} đợt lũ; ánh xạ chệch {o['hq_bias']} m ngoài mẫu.
   ⇒ mức nguy cơ = phân vị 95/98/99,5 mùa lũ = {o['thr1']} / {o['thr2']} / {o['thr3']} m³/s.
 - Metric sự kiện: POD/FAR/CSI/F1/PR-AUC/Brier; cấm accuracy; quy tắc ≥ 30 ngày dương.
 - Luật nâng sàn khi hồ xả: dự báo = max(mô hình, tổng lệnh xả Tả Trạch + Bình Điền), chỉ nâng.

IV. KẾT QUẢ
 A. LightGBM NSE {o['lgb_nse1']} / {o['lgb_nse2']} / {o['lgb_nse3']} vs persistence {o['persistence_nse1']} / {o['persistence_nse2']} / {o['persistence_nse3']}.
    AC-1 đạt h1 (RMSE tốt hơn {o['rmse_gain1']} %) và h2, TRƯỢT h3. Cắt ngọn lũ: peak bias {o['lgb_pb1']} / {o['lgb_pb2']} / {o['lgb_pb3']}.
 B. Mức 1, h1: POD {o['c1h1_pod']}, FAR {o['c1h1_far']}, CSI {o['c1h1_csi']} ({o['c1h1_hits']}/{o['npos1']} ngày). Mức 2 chỉ {o['npos2']} ngày → không kết luận.
 C. Kịch bản B': mưa nhiễu sigma = 1 → NSE h1 {o['sb0_h1']} → {o['sb1_h1']}; mô hình dựa vào lag lưu lượng.
 D. A→E: chuỗi dài giúp h1 ({o['abBA1']}); bão/không khí lạnh/ENSO giúp h2 ({o['abA2']} → {o['abE2']}); độ ẩm đất, đại diện hồ: không.
 E. Mưa giờ ERA5: giúp h3 đều 3 seed; h2 chủ yếu 1 seed; h1 không phải nhờ thông tin trong ngày.
 F. Mưa vệ tinh walk-forward: GSMaP-GC + E0, h3 {o['gc3_m']} {o['gc3_ci']}, {o['gc3_wl']} fold, p {o['gc3_p']}; FA {o['fa_e0']} → {o['fa_gc']}.
    IMERG bị lần chia đơn đánh giá quá cao ({o['ss_im2']} → {o['im2_m']}).
    ĐỘ TRỄ: Earth Engine trễ ~{o['lat_gsmap']} h → trễ 1 ngày thì h3 còn {o['lag1_3_m']} (p {o['lag1_3_p']}) ⇒ CHỈ có lợi khi
    phân tích lại quá khứ, CHƯA có lợi khi chạy thật.
 G. GSMaP_NRT (JAXA, trễ ~{o['lat_nrt']} h): {pend_nrt}.
 H. DL vs LightGBM walk-forward: KHÔNG thắng vững. LSTM MSE h1 {o['lstmM1_m']} (CI chứa 0); LSTM nhấn đỉnh h3 {o['lstmP3_m']}
    (p {o['lstmP3_p']}). Lợi thế lần chia đơn chỉ ở 2022–2025. Mặt được: POD/CSI h1 cao hơn, ít cắt ngọn hơn.
 I. Hồ chứa: R1 — không chỉ số nào đổi có ý nghĩa (GloFAS như sông chưa có hồ). R2 — GloFAS thấp hơn
    cận dưới lượng nước vào hồ {o['r2_inf']} ngày; 15/10/2022: xả ≥ {o['r2_2022-10-15_q_release_upstream_min']}, vào {o['r2_2022-10-15_q_inflow_upstream']}, GloFAS {o['r2_2022-10-15_glofas_best']} m³/s.
    ⇒ vấn đề lớn là GloFAS mô phỏng thiếu lũ lớn, không phải hồ.

V. GIẢI THÍCH MÔ HÌNH (SHAP): {pend_shap}.
 - Gain không đáng tin: doy_sin/doy_cos đứng đầu theo gain ở h2 nhưng bỏ đi NSE không giảm.
{shap_lines}
VI. HẠN CHẾ: mục tiêu là mô phỏng; đổi chế độ 07/2022 + GloFAS v5 sẽ thêm hồ; độ trễ vệ tinh;
    KHÔNG có mục tiêu theo giờ (nhóm quyết định không xin số liệu đo KTTV); sự kiện hiếm; nhiễu ±{o['noise']}.

VII. KẾT LUẬN + REPORT 4: GSMaP_NRT; so với GloFAS thô từ nhật ký; SHAP; hồi quy phân vị; Spark trình bày
    trung thực (ETL cụm {o['etl_c2_lo']}–{o['etl_c2_hi']} s so với Polars {o['etl_pl_lo']}–{o['etl_pl_hi']} s); walk-forward là so sánh chính.

CÂU HỎI DỄ BỊ HỎI — trả lời ngắn
 - "Sao không so với GloFAS?" → kho dự báo lưu lượng quá khứ không tồn tại (404); đang tích luỹ từ 15/09.
 - "Sao không dùng mức BĐ I/II/III?" → R² H–Q = {o['hq_r2']}; mức nguy cơ là tương đối, không phải BĐ.
 - "Mưa vệ tinh có giúp không?" → có ở h3 khi nhìn lại quá khứ; chạy thật qua Earth Engine thì không.
 - "DL có tốt hơn không?" → không vững qua 13 năm; chỉ hơn ở 2022–2025.
 - "Spark để làm gì?" → chứng minh pipeline đúng khi tách executor; ở 74 MB thì chậm hơn Polars.
"""
    rows = ["", "=" * 100, "DANH SÁCH SỐ DÙNG TRONG BÁO CÁO (sinh tự động lúc build)",
            "loại: csv = đã kiểm với file lúc build · claim = câu định tính đã kiểm · doc = chỉ có trong tài liệu",
            "=" * 100]
    for k in V.val:
        mark = "" if k in V.used or V.kind[k] == "claim" else "  [không in trong PDF]"
        rows.append(f"{V.kind[k]:<6} {k:<44} {V.val[k]:<26} {V.src[k]}{mark}")
    rows += ["", "CẢNH BÁO LẦN BUILD NÀY:"] + ([f" - {w}" for w in WARN] or [" (không có)"])
    OUTLINE.write_text(lines + "\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(build())
