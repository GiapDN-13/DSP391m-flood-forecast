"""Sinh Báo cáo cuối kỳ (Final Report) theo định dạng IEEE hai cột.

    PYTHONIOENCODING=utf-8 python reports/final/build_report.py

Gộp Report 1 (đề xuất), Report 2 (dữ liệu/EDA), Report 3 (mô hình & đánh giá) và
Report 4 (Spark & deep learning), cập nhật phần việc sau Report 4 (thử giảm cắt ngọn lũ,
hiệu chỉnh isotonic, job hằng ngày có LightGBM, dashboard, Spark quy mô đủ).

Cùng khuôn với Report 3/4: kiểu chữ và helper (``p``, ``h1``, ``h2``, ``tbl``, ``col_fig``,
``pending``, ``no_orphans``, ``check_text``) được *import* từ
``reports/report3/build_report.py``, chỉ trỏ sổ số liệu / số bảng / số hình sang bản
cuối kỳ. Ba lớp bảo vệ giữ nguyên:

1. **Số đối chiếu với nguồn lúc build** (``facts.py`` của bản này, nạp lại toàn bộ sổ
   Report 3 + Report 4 và thêm khoá mới). Lệch là build hỏng.
2. **Quét số trong PDF**: mọi số thập phân / số có dấu phẩy nghìn phải có trong sổ.
3. **Ký tự ngoài WinAnsi** ⇒ build hỏng.

Kết quả có thể chưa có lúc build (Spark walk-forward trên cụm, bản phát đầu tiên có cột
LightGBM trong nhật ký dự báo, Spark quy mô đủ) ⇒ in khung ``pending`` có đánh dấu và
cảnh báo, không bịa số. Build ghi ``reports/final/OUTLINE_VI.txt``.
"""

from __future__ import annotations

import html
import importlib.util
import io
import sys
from pathlib import Path

from PIL import Image as PILImage
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
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


r3 = _load("report3_build_final", ROOT / "reports" / "report3" / "build_report.py")
fx = _load("final_facts", HERE / "facts.py")
p, bullets, h1, h2, ST, tbl, col_fig, pending = (r3.p, r3.bullets, r3.h1, r3.h2, r3.ST, r3.tbl,
                                                 r3.col_fig, r3.pending)
COLW, LM, RM, TM, BM, GUT, PW, PH = r3.COLW, r3.LM, r3.RM, r3.TM, r3.BM, r3.GUT, r3.PW, r3.PH
FIGS = r3.FIGS
DELTA, SIGMA, DEG, M3S, KM2, PM = r3.DELTA, r3.SIGMA, r3.DEG, r3.M3S, r3.KM2, r3.PM
OUT = HERE / "DSP391m_Final_Report_IEEE.pdf"
OUTLINE = HERE / "OUTLINE_VI.txt"

V = fx.R            # V("key") → số đã kiểm, dấu trừ in thành gạch en
WARN: list[str] = []
T: dict[str, str] = {}
F: dict[str, str] = {}
TT, TE = "<font face='Courier'>", "</font>"
ND = "&#8211;"


def rng(key: str) -> str:
    lo, hi = V(f"{key}_lo"), V(f"{key}_hi")
    return lo if lo == hi else f"{lo}{ND}{hi}"


def of(key: str) -> str:
    return V(key).replace("/", " of ")


def won(key: str) -> str:
    return f"{V(key).split('/')[0]} of {V('wf_nfold')}"


def raw(key: str) -> str:
    """Số cho chữ trong hình vẽ (không phải HTML)."""
    return html.unescape(V(key))


def px(key: str) -> str:
    return V(key).replace(" x ", " &#215; ")


def arch_drawing() -> Drawing:
    """Cụm Spark standalone trên Docker (như Report 4, Hình 1)."""
    W, H = COLW - 0.06 * inch, 178
    d = Drawing(W, H)
    grey, dark = colors.HexColor("#f2f2f2"), colors.HexColor("#333333")
    d.add(Rect(0, 0, W, H, fillColor=colors.white, strokeColor=dark, strokeWidth=0.8))
    d.add(String(5, H - 11, f"Windows 11 host: {raw('host_cores')} cores, {raw('host_ram')} GB RAM",
                 fontName="Times-Bold", fontSize=7.5))
    d.add(Rect(6, 6, W - 12, H - 22, fillColor=grey, strokeColor=colors.HexColor("#777777"),
               strokeWidth=0.6, strokeDashArray=[3, 2]))
    d.add(String(11, H - 27, f"Docker Desktop ({raw('docker_ram')} GB), image apache/spark "
                             f"{raw('spark_ver')}, Java {raw('java_ver')}, PyTorch {raw('torch_ver')} (CPU)",
                 fontName="Times-Italic", fontSize=6.6))

    def box(x, y, w, h, title, lines, fill):
        d.add(Rect(x, y, w, h, fillColor=fill, strokeColor=dark, strokeWidth=0.7))
        d.add(String(x + w / 2, y + h - 10, title, fontName="Times-Bold", fontSize=7.4, textAnchor="middle"))
        for i, t in enumerate(lines):
            d.add(String(x + w / 2, y + h - 19 - 8.2 * i, t, fontName="Times-Roman", fontSize=6.6,
                         textAnchor="middle"))

    mw, ww, bh = 128, 96, 38
    mx, my = (W - mw) / 2, 104
    box(mx, my, mw, bh, "spark-master", ["driver, spark-submit, port 7077",
                                         "TorchDistributor / barrier stage"], colors.HexColor("#fde0c5"))
    w1x, w2x, wy = 16, W - 16 - ww, 50
    for x, name in ((w1x, "spark-worker-1"), (w2x, "spark-worker-2")):
        box(x, wy, ww, bh, name, [f"{raw('w_cores')} cores, {raw('w_mem')} GB", "1 executor = 1 DDP rank"],
            colors.HexColor("#d6e6f5"))
        d.add(Line(W / 2, my, x + ww / 2, wy + bh, strokeColor=dark, strokeWidth=0.7))
        d.add(Line(x + ww / 2, wy, x + ww / 2, 32, strokeColor=dark, strokeWidth=0.6, strokeDashArray=[1, 1.5]))
    d.add(String(W / 2, 92, "tasks", fontName="Times-Italic", fontSize=6.4, textAnchor="middle"))
    d.add(Line(w1x + ww, wy + bh / 2, w2x, wy + bh / 2, strokeColor=colors.HexColor("#c0392b"),
               strokeWidth=0.8, strokeDashArray=[3, 2]))
    d.add(String(W / 2, wy + bh / 2 + 3, "gloo", fontName="Times-Italic", fontSize=6.4,
                 textAnchor="middle", fillColor=colors.HexColor("#c0392b")))
    d.add(Rect(12, 12, W - 24, 20, fillColor=colors.HexColor("#e3f1e0"), strokeColor=dark, strokeWidth=0.7))
    d.add(String(W / 2, 19.5, "/opt/repo: repository mounted in every container (replaces HDFS / S3)",
                 fontName="Times-Roman", fontSize=6.6, textAnchor="middle"))
    return d


ETL_LABEL = {
    "windows_polars": ("Polars, host", "#1b9e77"),
    "docker_polars": ("Polars, container", "#1b9e77"),
    "docker_local8": ("Spark local[8], container", "#7570b3"),
    "docker_local4": ("Spark local[4], container", "#7570b3"),
    "docker_local1": ("Spark local[1], container", "#7570b3"),
    "cluster_1w_4c": ("Cluster: 1 worker, 4 cores", "#d95f02"),
    "cluster_2w_8c": ("Cluster: 2 workers, 8 cores", "#d95f02"),
    "cluster_1w_1c": ("Cluster: 1 worker, 1 core", "#d95f02"),
    "windows_local8_arrow": ("Spark local[8], host via Arrow", "#999999"),
}


def etl_drawing() -> Drawing:
    """Thời gian ETL giờ → ngày (như Report 4, Hình 2): thanh = trung bình, nhãn = min–max."""
    eb = fx._csv("spark/etl_benchmark.csv")
    mean = eb.groupby("tag").seconds_etl.mean()
    order = list(ETL_LABEL)
    W, row = COLW - 0.06 * inch, 13.5
    H = row * len(order) + 22
    lab_w, val_w = 104, 40
    scale = (W - lab_w - val_w) / mean[order].max()
    d = Drawing(W, H)
    for i, t in enumerate(order):
        y = H - 6 - row * (i + 1)
        lab, col = ETL_LABEL[t]
        d.add(String(lab_w - 4, y + 3, lab, fontName="Times-Roman", fontSize=7, textAnchor="end"))
        d.add(Rect(lab_w, y + 1, mean[t] * scale, row - 4, fillColor=colors.HexColor(col), strokeColor=None))
        d.add(String(lab_w + mean[t] * scale + 3, y + 3, html.unescape(rng(f"etl_{t}")) + " s",
                     fontName="Times-Roman", fontSize=7))
    d.add(Line(lab_w, 10, lab_w, H - 4, strokeColor=colors.HexColor("#555555"), strokeWidth=0.5))
    d.add(String(lab_w, 1, "seconds for read + compute + write (JVM start-up excluded)",
                 fontName="Times-Italic", fontSize=6.6))
    return d


def fig_drawing(drawing: Drawing, key: str, caption: str):
    return KeepTogether([drawing, Paragraph(f"Fig. {F[key]}.&nbsp; {caption}", ST["caption"])])


def roman(i: int) -> str:
    out = ""
    for v, r in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while i >= v:
            out, i = out + r, i - v
    return out


def col_img(img: ImageReader, key: str, caption: str, scale: float = 1.0):
    w = (COLW - 0.05 * inch) * scale
    iw, ih = img.getSize()
    buf = io.BytesIO()
    img._image.save(buf, "PNG")
    buf.seek(0)
    return KeepTogether([Image(buf, width=w, height=w * ih / iw),
                         Paragraph(f"Fig. {F[key]}.&nbsp; {caption}", ST["caption"])])


def _stack(path: Path, boxes: list[tuple[int, int, int, int]], size: tuple[int, int]) -> ImageReader:
    im = PILImage.open(path).convert("RGB")
    if im.size != size:
        WARN.append(f"{path.name} đổi kích thước {im.size} — dùng nguyên hình, kiểm lại bố cục")
        return ImageReader(im)
    parts = [im.crop(b) for b in boxes]
    out = PILImage.new("RGB", (im.size[0], sum(x.size[1] for x in parts)), "white")
    y = 0
    for x in parts:
        out.paste(x, (0, y))
        y += x.size[1]
    return ImageReader(out)


def crop_events() -> ImageReader:
    """Panel (a) số đợt bắt được + (b) tỉ số đỉnh của event_eval_en.png, kèm chú giải."""
    return _stack(FIGS / "event_eval_en.png", [(0, 100, 1955, 745), (0, 1410, 1955, 1470)], (1955, 1530))


def crop_reliability() -> ImageReader:
    """Hàng cấu hình E (h = 1, 2, 3) của cost_reliability_en.png, kèm chú giải."""
    return _stack(FIGS / "cost_reliability_en.png", [(0, 0, 1756, 965), (0, 2005, 1756, 2050)], (1756, 2050))


# ================================================================== nội dung
def story() -> list:
    s: list = []
    SF, SW, LIVE = fx.SPARK_FULL, fx.SPARK_WF or {}, fx.LIVE_LGBM

    # ============================================================ I
    s += [h1("I", "Introduction"),
          p("Central Vietnam is the part of the country most exposed to river floods. Hue lies "
            "on the Huong River, whose catchment to the Kim Long station is short and steep: "
            "rain from tropical cyclones, cold surges and the north-east monsoon becomes a "
            f"flood peak within a day [5]. Official warnings are issued as water-level alert "
            f"stages ({V('bd1')}, {V('bd2')} and {V('bd3')} m at Kim Long [4]), while the "
            "only open, long, daily discharge record for the basin is a simulation: the "
            "Global Flood Awareness System (GloFAS) v4 [1], [2], driven by ERA5 [3].",
            "body0"),
          p("This project forecasts the daily GloFAS discharge at the Kim Long cell "
            f"({V('pt_lat')}{DEG} N, {V('pt_lon')}{DEG} E) one, two and three days ahead from "
            "open data only, and translates the forecast into flood-risk levels. It is "
            "positioned as a <i>local correction layer</i> on top of GloFAS, in the line of "
            "recent GloFAS post-processing studies [7], [8], not as a replacement: the global "
            "model is known to degrade in small, steep, monsoon-driven catchments, and a "
            "local model can add predictors that the global system does not use (storms, cold "
            "surges, soil moisture, local rainfall, reservoir orders)."),
          p("The work was delivered in four stages: a proposal (Report 1), data collection and "
            "exploratory analysis (Report 2), modelling and evaluation (Report 3), and "
            "distributed processing with deep learning (Report 4). This final report merges "
            "them and adds the work completed after Report 4. Its contributions are:"),
          *bullets([
              "a reproducible open-data pipeline (GloFAS, ERA5, ERA5-Land, IBTrACS, ONI, "
              f"IMERG, GSMaP and GSMaP_NRT; about {V('fs_all_mrows') if SF else V('sat_mrows')} "
              "million hourly cell records) with automated leakage tests;",
              f"a LightGBM model with {V('nfE')} predictors (configuration E) that beats "
              "persistence, climatology, seasonal naive and ARIMA at every horizon, evaluated "
              f"on a held-out period and in a {V('wf_nfold')}-fold yearly walk-forward;",
              "risk levels defined as flood-season percentiles of discharge, a cost-based "
              "alert threshold and isotonic calibration of the alert probability;",
              "negative results reported as such: reservoir effects absent from the target, "
              "satellite rain helpful only in hindsight, deep learning and peak-weighting not "
              "better than LightGBM, Spark slower than a single machine at this data size;",
              "an operational daily job on GitHub Actions and a Streamlit dashboard.",
          ]),
          p("Report 1 posed three research questions: (RQ1) can daily discharge be predicted "
            "one to three days ahead from gridded rainfall and antecedent discharge, and with "
            "what error; (RQ2) with what detection rate and false-alarm ratio can a classifier "
            "flag days above an official alert stage; and (RQ3) which sub-basins carry the "
            f"highest flood risk. Table {T['anl']} gives the analytics position, unchanged since "
            "the proposal. Section XI answers the three questions."),
          tbl([["Class", "Position", "Reason"],
               ["Descriptive", "Supporting", "Seasonality, lag structure and flood events "
                "establish that the signal exists (Report 2)."],
               ["Diagnostic", "Partial", "SHAP attribution and the reservoir tests explain "
                "forecasts; no causal design is claimed."],
               ["Predictive", "<b>Core</b>", "Discharge and risk level one to three days ahead."],
               ["Prescriptive", "Out of scope", "Evacuation advice needs authority and "
                "accountability that an academic project does not hold."]],
              [0.7 * inch, 0.66 * inch, 2.14 * inch], "anl",
              "POSITION ON THE FOUR CLASSES OF ANALYTICS", small=True)]

    # ============================================================ II
    s += [h1("II", "Related Work"),
          p("<b>Global flood forecasting.</b> GloFAS couples a land-surface and routing model "
            "to ECMWF forcing and provides daily discharge worldwide on a ~5 km grid [1], "
            "[2]. Skill is lower in small, steep catchments, which motivates local "
            "post-processing; ensemble machine-learning bias correction of GloFAS has "
            "recently been shown to improve station-level flow [7], [8].", "body0"),
          p("<b>Machine learning for streamflow.</b> Gradient-boosted trees such as LightGBM "
            "[10] are strong on tabular hydrological predictors and train in seconds at this "
            "data size. LSTM networks learn rainfall&#8211;runoff behaviour from sequences "
            "[11], [12] and are the state of the art for global ungauged flood prediction "
            "[6], but their advantage is clearest when many catchments are pooled; transfer "
            "to a single small basin is an open question [13]."),
          p("<b>Evaluation and explanation.</b> The Nash&#8211;Sutcliffe efficiency (NSE) "
            "[14] and the Kling&#8211;Gupta efficiency [15] are the reference skill scores; "
            "guidance places satisfactory streamflow simulation near NSE 0.5 [16]. Rare "
            "events are scored with contingency measures (POD, FAR, CSI) and the Brier score "
            "[17]; isotonic regression is a standard way to calibrate classifier "
            "probabilities [18]. SHAP values [19] attribute tree-ensemble forecasts to their "
            "inputs and are used for streamflow models [9]."),
          p("<b>Distributed processing.</b> Apache Spark [20] and MLlib [21] distribute data "
            "and model fitting; PyTorch DDP [22] distributes neural-network training. The "
            "COST argument [23] warns that a distributed system should be compared with a "
            "competent single-machine implementation before claiming a speed-up.")]

    # ============================================================ III
    s += [h1("III", "Study Area and Data"),
          h2("A", "Basin"),
          p(f"The Huong catchment to Kim Long covers about {V('area_cfg')} {KM2} "
            f"({V('area_dem')} {KM2} delineated from the Copernicus GLO-30 DEM [24]). Report 1 "
            f"used {V('area_sys')} {KM2}, which is the whole Huong system including the Bo "
            f"River ({V('area_bo')} {KM2}) that joins downstream of Kim Long; Report 3 "
            "corrected this. A D8 flow model splits the catchment into five sub-basins "
            f"(Fig. {F['basins']}): the Ta Trach and Binh Dien reservoir catchments "
            f"({V('a_tt')} and {V('a_bd')} {KM2}; capacities {V('cap_tt')} and {V('cap_bd')} "
            f"million m&#179; [25]), the reaches below the dams ({V('a_ttb')} and {V('a_htb')} "
            f"{KM2}) and the reach from the Tuan confluence to Kim Long ({V('a_tkl')} {KM2}).",
            "body0"),
          col_fig("basins_map.png", "basins",
                  f"Huong basin to Kim Long ({V('area_dem')} {KM2}), five sub-basins from the "
                  "30 m DEM, ERA5 cells and the GloFAS target point.", scale=0.82),

          h2("B", "Target: GloFAS v4 discharge"),
          p("The target is the GloFAS v4 daily mean discharge at the cell selected in Report 1 "
            "by three independent tests (distance to OpenStreetMap river lines, correlation "
            "between candidate cells, and the catchment implied by specific runoff). Through "
            "Open-Meteo [26] the series starts in 1997 for this basin. Three caveats bound "
            "every result:"),
          *bullets([
              "<b>It is a simulation.</b> All scores measure agreement with GloFAS, not with "
              "the river.",
              "<b>Regime change in July 2022.</b> Before 1 July 2022 the series is reanalysis; "
              "from that date it is built from archived forecasts. Report 2 found no "
              f"systematic shift in the heavy-rain response (Mann&#8211;Whitney p = "
              f"{V('mw_p')}), but only {V('fc_nfold')} full walk-forward years fall in the "
              "new regime, too few to test it alone.",
              "<b>No dams and under-simulated floods.</b> Four flow indices show no change "
              "after the Ta Trach and Binh Dien dams came into operation (all p above 0.05; "
              "Section V-H), and reported natural inflows to the two reservoirs exceed the "
              f"simulated discharge at Kim Long on {of('r2_inf')} bulletin days "
              f"(Fig. {F['r2']}).",
          ]),

          h2("C", "Predictors"),
          p(f"Table {T['data']} lists the inputs. ERA5 rainfall on {V('n_cells_era5')} cells "
            f"({V('era5_rows')} hourly rows since 2015, daily since 1997) is averaged per "
            "basin band and sub-basin. ERA5-Land adds soil moisture in three layers; IBTrACS "
            f"v04r01 [27] adds {V('storms')} tropical cyclones within {V('storm_km')} km of "
            "Hue; ERA5 pressure and wind give cold-surge indicators; the Oceanic Ni&#241;o "
            "Index [28] is lagged three months so that only published values are used; and "
            "15-day, 30-day and season-cumulative rainfall since 1 September act as proxies "
            "for reservoir storage. Satellite rainfall (IMERG V07 [29] and GSMaP v8 [30] from "
            f"Earth Engine, and GSMaP_NRT from JAXA) was retrieved hourly on {V('sat_cells')} "
            "cells since 1998."
            + (f" With ERA5, the hourly inputs total about {V('fs_all_mrows')} million cell "
               f"records ({V('fs_sat_mrows')} million from the three satellite products)."
               if SF else "")),
          tbl([["Source", "Variables", "Period, step", "Role"],
               ["GloFAS v4 [1], [26]", "Daily discharge, one cell", "1997&#8211;2026, 1 day",
                "Target, lags"],
               ["ERA5 [3]", f"Rain, met. ({V('n_cells_era5')} cells, {V('grid_sat')}{DEG})",
                "1997&#8211;2026, 1 h from 2015", "Main predictors"],
               ["ERA5-Land", "Soil moisture, 3 layers", "1997&#8211;2026, 1 day", "Config. C"],
               ["IBTrACS [27]", "Cyclone distance, wind, speed", "1996&#8211;2026", "Config. E"],
               ["ERA5 pressure, wind", "Cold-surge indices", "1997&#8211;2026", "Config. E"],
               ["ONI [28]", "ENSO, lagged 3 months", "Monthly", "Config. E"],
               ["IMERG, GSMaP [29], [30]", f"Hourly rain, {V('sat_cells')} cells",
                "1998&#8211;Oct. 2026", "Tested"],
               ["GSMaP_NRT (JAXA)", "Hourly rain, low latency", "1998&#8211;Oct. 2026", "Tested"],
               ["Bulletins, news", f"{V('rel_rows')} reservoir records",
                f"{V('rel_y0')}&#8211;2026", "Checks, floor rule"]],
              [0.9 * inch, 1.12 * inch, 0.88 * inch, 0.6 * inch], "data",
              "OPEN DATA USED BY THE PROJECT", small=True),

          h2("D", "Exploratory findings (Report 2)"),
          p(f"The 2010&#8211;2026 daily panel has {V('eda_ndays')} days with no missing "
            f"discharge or rainfall. Discharge is highly skewed (median {V('eda_qmed')} {M3S}, "
            f"maximum {V('eda_qmax')} {M3S} on 8 November 2011, skewness {V('eda_skew')}), so "
            "models are trained on log(1 + Q). September to December carry "
            f"{V('eda_sepdec')}% of the runoff. Rainfall correlates best with discharge one "
            f"day later (r = {V('eda_r1')}), which supports a short forecast horizon, and wet "
            f"antecedent conditions matter: after heavy rain the median discharge is "
            f"{V('eda_wet')} {M3S} on wet ground against {V('eda_dry')} {M3S} on dry ground."),

          h2("E", "Data engineering"),
          p("Acquisition is a set of independent tasks, each writing one Parquet file; a task "
            "whose output exists is skipped, so an interrupted crawl resumes without "
            "re-requesting data, request pacing adapts to rate-limit replies, and a lock file "
            "prevents concurrent crawlers (three parallel crawlers had once been mistaken for "
            "provider throttling). Raw files are converted to Vietnam local time (UTC+7), "
            "hourly rain is aggregated to days with a test that the hourly values sum to the "
            "daily value, and validation functions raise errors instead of silently repairing "
            "negative discharge, duplicated dates or gaps. Satellite rain was cut to a box of "
            "cells around the basin as it was downloaded (Earth Engine month by month, "
            "GSMaP_NRT from JAXA's server). Raw data are backed up as a checksummed GitHub "
            "release, and every experiment writes versioned CSV files from which the numbers "
            "of this report are recomputed and checked when the PDF is built."),
          p("The rainfall sources disagree. Over the 2015&#8211;2025 flood seasons IMERG, "
            f"GSMaP and gauge-calibrated GSMaP total {V('rr_imerg')}, {V('rr_gsmap')} and "
            f"{V('rr_gc')} times ERA5. ERA5 correlates best with next-day GloFAS discharge "
            f"(r = {V('rq_era5')} against {V('rq_imerg')} for IMERG), as expected because "
            "GloFAS is driven by ERA5; this does not show that ERA5 is closer to the true "
            f"rain. PERSIANN-CCS, the only product finer than GloFAS ({V('grid_pccs')}{DEG}), "
            f"recorded {V('pccs_nov')} of the ERA5 total in November 2020, probably missing "
            "rain from low, warm monsoon clouds, and was not used."),

          h2("F", "Why no gauge data"),
          p("Observed hourly water levels and discharge at Kim Long belong to the national "
            "hydro-meteorological service. The team decided not to request them, so the "
            "target stays the open GloFAS daily series and hourly or finer data enter only as "
            "inputs. The official alert stages are water levels, and the attempt to map "
            f"discharge to level from published flood peaks failed: across {V('hq_n')} floods "
            f"log discharge explains little of the peak level (R&#178; = {V('hq_r2')}), and the "
            f"best fit missed the five floods after July 2022 by {V('hq_bias')} m on average. "
            "Tide and backwater from the Tam Giang lagoon, the Thao Long barrage and reservoir "
            "operation decouple level from simulated discharge.")]

    # ============================================================ IV
    s += [h1("IV", "Methodology"),
          h2("A", "Task, features and leakage control"),
          p("Each forecast is issued at the end of day t for h = 1, 2 and 3 days. Every "
            "predictor is known at the end of day t: rolling windows look backward only, and "
            "automated tests fail if a feature uses later information or if NSE exceeds "
            f"{V('leak_eps')}, which would signal leakage. Five configurations add data "
            f"cumulatively: A is the Report 2 panel ({V('nfA')} features: discharge lags of "
            "1&#8211;14 days, band rainfall with lags and sums, an antecedent precipitation "
            f"index, season code) trained from 2010; B trains from 1997; C adds soil moisture "
            f"({V('nfC')}); D adds reservoir-storage proxies ({V('nfD')}); E adds storm, "
            f"cold-surge and ENSO predictors ({V('nfE')}).", "body0"),

          h2("B", "Splits and walk-forward protocol"),
          p("<b>Single regime split:</b> train to December 2015, validation to June 2022, test "
            f"from 1 July 2022 ({V('n_test1')} days at h = 1); final models are refit on train "
            "plus validation. <b>Yearly walk-forward:</b> each year 2013&#8211;2025 is a test "
            f"fold ({V('wf_nfold')} folds) with an expanding training window, a 3-day gap so "
            "that no h = 3 label enters the test year, and risk thresholds recomputed from "
            f"each fold's training data. Gains are reported as the mean {DELTA}NSE over folds "
            "with a 95% bootstrap interval over folds, folds won/lost and a two-sided Wilcoxon "
            "test. Perturbing the inputs at the 13th decimal moves NSE by about "
            f"{PM}{V('noise')}, so smaller differences are not resolvable."),

          h2("C", "Main model: LightGBM configuration E"),
          p(f"LightGBM [10] is trained on log(1 + Q) with {V('lgb_trees')} trees, learning rate "
            f"{V('lgb_lr')}, {V('lgb_leaves')} leaves and at least {V('lgb_mcs')} days per "
            "leaf, one model per horizon, averaged over seeds 42, 7 and 2026. The loss is L1 at "
            "h = 1 and L2 at h = 2&#8211;3. The switch was chosen on the walk-forward and the "
            f"validation period, never on the test set: L2 raised the mean NSE by {V('tun2_m')} "
            f"{V('tun2_ci')} at h = 2 and {V('tun3_m')} {V('tun3_ci')} at h = 3 (folds won/lost "
            f"{V('tun2_wl')}, p = {V('tun2_p')} and {V('tun3_p')}), while at h = 1 the gain "
            f"({V('tun1_m')}, p = {V('tun1_p')}) was not significant and validation fell "
            f"({V('tunv1')}). The model was frozen on {V('pk_freeze')} after the experiments "
            "of Section VII."),

          h2("D", "Baselines"),
          p("Persistence, climatology of the calendar day (training years only), seasonal "
            "naive and ARIMA(2,1,2) on log discharge. The raw GloFAS forecast cannot be "
            "rebuilt for past dates: Open-Meteo does not archive past flood forecasts (HTTP "
            "404), and the GloFAS analysis at t + h would leak the target. Issued GloFAS "
            "forecasts have therefore been logged every morning since 15 September 2026."),

          h2("E", "Risk levels instead of alert stages"),
          p(f"Because discharge does not determine the official water level (Section III-E), "
            f"labels are <i>risk levels</i> at the 95th, 98th and {V('q_lv3')}th "
            "percentiles of September&#8211;December discharge on train plus validation: "
            f"{V('thr1')}, {V('thr2')} and {V('thr3')} {M3S}. They are relative to the GloFAS "
            "climate and are <i>not</i> the official alert stages. The test period holds "
            f"{V('npos1')} level-1 days, {V('npos2')} level-2 and {V('npos3')} level-3 days; "
            "a level supports a main conclusion only with at least 30 positive days, so "
            "level 1 is the operational level."),

          h2("F", "Classifier, cost-based threshold and calibration"),
          p("A binary LightGBM classifier per level and horizon is weighted by the "
            "negative-to-positive ratio instead of resampling, which would break the temporal "
            f"structure. A fixed threshold of {V('clf_thr')} ignores that a missed flood costs "
            "more than a false alarm, so the threshold minimises C = 10 &#215; misses + false "
            "alarms (sensitivity 5:1 and 20:1). It is chosen on out-of-fold probabilities of "
            "earlier years only. Isotonic regression [18] is fitted on the same pool (years "
            "before the test year) and maps raw scores to calibrated probabilities; on a "
            "calibrated scale the Bayes threshold for a 10:1 cost ratio is 1/(1 + 10) = "
            f"{V('cal_bay_thr')}."),

          h2("G", "Reservoir floor rule"),
          p("When the province orders releases, the forecast at Kim Long becomes the larger "
            "of the model forecast and the sum of ordered releases at Ta Trach and Binh Dien, "
            "since released water reaches Kim Long within hours. The rule only raises a "
            "forecast. It is a safeguard, not a validated component: no historical series of "
            "orders exists to score it.")]

    # ============================================================ V
    s += [h1("V", "Results"),
          h2("A", "Baselines and LightGBM"),
          p(f"LightGBM beats every baseline at every horizon (Table {T['base']}). "
            "Configuration E reaches NSE "
            f"{V('abE1')}, {V('abE2')} and {V('abE3')} on the test period, against "
            f"{V('persistence_nse1')}, {V('persistence_nse2')} and {V('persistence_nse3')} for "
            "persistence, and the yearly walk-forward gives a consistent picture "
            f"({V('wfE0_1')}, {V('wfE0_2')}, {V('wfE0_3')}; persistence {V('pk_P1')}, "
            f"{V('pk_P2')}, {V('pk_P3')}). <b>Acceptance criterion AC-1</b> (NSE at least "
            f"{V('ac1_h1')}, {V('ac1_h2')} and {V('ac1_h3')}) is met at h = 1 and h = 2 and "
            f"<b>missed at h = 3</b>: {V('abE3')} on the test period and {V('wfE0_3')} in the "
            f"walk-forward, both below {V('ac1_h3')}. The RMSE criterion at h = 1 is met "
            f"({V('rmse_gain1')}% below persistence for configuration A, target "
            f"{V('ac1_rmse')}%). Skill decays quickly beyond one day because the rain that "
            "drives a flood two or three days ahead has usually not yet fallen at issue time."),
          tbl([["Model", "NSE h=1", "h=2", "h=3", f"RMSE h=1 ({M3S})", "h=2", "h=3"]]
              + [[name] + [V(f"{m}_nse{h}") for h in (1, 2, 3)]
                 + [V(f"{m}_rmse{h}") for h in (1, 2, 3)]
                 for m, name in (("persistence", "Persistence"), ("climatology", "Climatology"),
                                 ("seasonal_naive", "Seasonal naive"), ("arima", "ARIMA(2,1,2)"))]
              + [["LightGBM, config. A"] + [V(f"lgb_nse{h}") for h in (1, 2, 3)]
                 + [V(f"lgb_rmse{h}") for h in (1, 2, 3)],
                 ["LightGBM, config. E (main)"] + [V(f"abE{h}") for h in (1, 2, 3)] + ["n/r"] * 3],
              [0.86 * inch] + [0.42 * inch] * 3 + [0.52 * inch] + [0.4 * inch] * 2, "base",
              "TEST PERIOD JULY 2022 &#8211; AUGUST 2026. CONFIG. A: L1, SEED 42; CONFIG. E: MEAN OF "
              "THREE SEEDS, RMSE NOT RECORDED (N/R)", small=True, bold_rows=(6,)),

          h2("B", "Does more data help?"),
          p(f"A longer record (B) is the only change that helps at h = 1 ({V('abBA1')}; Table "
            f"{T['abl']}). Soil moisture (C) and storage proxies (D) give small changes of mixed "
            "sign: that information is already carried by discharge lags and the API. Storm, "
            f"cold-surge and ENSO predictors (E) give the largest gain at h = 2 and 3 "
            f"({V('abED2')} and {V('abED3')} over D): these drivers announce heavy rain one to "
            f"three days ahead. The seed standard deviation is at most {V('ab_sd')}."),
          tbl([["Config.", "Added", "NSE h=1", "h=2", "h=3"],
               ["A", f"Report 2 panel, from 2010 ({V('ntrA')} days)", V("abA1"), V("abA2"), V("abA3")],
               ["B", f"Record from 1997 ({V('ntrB')} days)", V("abB1"), V("abB2"), V("abB3")],
               ["C", "+ soil moisture", V("abC1"), V("abC2"), V("abC3")],
               ["D", "+ reservoir-storage proxies", V("abD1"), V("abD2"), V("abD3")],
               ["E", "+ storms, cold surges, ENSO", V("abE1"), V("abE2"), V("abE3")]],
              [0.42 * inch, 1.65 * inch] + [0.47 * inch] * 3, "abl",
              "CUMULATIVE ABLATION, TEST PERIOD, MEAN OF THREE SEEDS", small=True),
          p("Two further tests bound what better rainfall can give. Nine hourly ERA5 features "
            "per basin (own split, as hourly ERA5 starts in 2015) raise NSE at h = 3 from "
            f"{V('hrA3')} to {V('hrB3')}, consistently across seeds ({V('hrB3_s0')}, "
            f"{V('hrB3_s1')}, {V('hrB3_s2')}), while hourly features per sub-basin are no "
            f"better than the basin mean ({V('hrC3')}): ERA5 is too coarse to separate them. "
            f"Multiplicative log-normal noise with {SIGMA} = 1 on all rainfall inputs lowers NSE "
            f"at h = 1 from {V('sb0_h1')} to {V('sb1_h1')} and not at all at h = 3 "
            f"({V('sb0_h3')} to {V('sb1_h3')}). The model leans on discharge lags, so imperfect "
            "rainfall costs little; for the same reason it cannot anticipate rain that has not "
            "yet fallen."),

          h2("C", "Satellite rainfall and latency"),
          p("On the single split IMERG appeared to help at h = 2; across "
            f"{V('wf_nfold')} folds the only consistent gain on configuration E comes from "
            f"gauge-calibrated GSMaP at h = 3 ({V('gc3_m')} {V('gc3_ci')}, positive in "
            f"{won('gc3_wl')} folds, p = {V('gc3_p')}; Table {T['sat']}, Fig. {F['sat']}). The "
            f"Earth Engine archive, however, arrives about {V('lat_gsmap')} h late, so a "
            "forecast issued near 05:00 has satellite rain only up to day t &#8211; 1; with "
            f"features lagged one day the gain disappears ({V('lag1_3_m')}, p = "
            f"{V('lag1_3_p')}). JAXA's GSMaP_NRT arrives about {V('lat_nrt')} h after "
            "observation and was tested by retraining on its own history: it helps the weaker "
            f"Report 2 panel at every horizon ({V('nrtA1_m')}, {V('nrtA2_m')}, "
            f"{V('nrtA3_m')}) but adds nothing to configuration E ({V('nrtE1_m')}, "
            f"{V('nrtE2_m')}, {V('nrtE3_m')}; all p at least {V('nrtE1_p')}). Satellite rain "
            "partly substitutes for predictors that E already contains; it was not added to "
            "the operational model."),
          tbl([["Config. (vs. own baseline)", "h = 1", "h = 2", "h = 3"],
               ["E + GSMaP-GC, same day", f"{V('gc1_m')} ({V('gc1_wl')})",
                f"{V('gc2_m')} ({V('gc2_wl')}), p {V('gc2_p')}",
                f"{V('gc3_m')}<br/>{V('gc3_ci')}<br/>{V('gc3_wl')}, p {V('gc3_p')}"],
               ["E + GSMaP-GC, lagged one day", f"{V('lag1_1_m')} ({V('lag1_1_wl')})",
                f"{V('lag1_2_m')} ({V('lag1_2_wl')})",
                f"{V('lag1_3_m')}<br/>{V('lag1_3_ci')}<br/>{V('lag1_3_wl')}, p {V('lag1_3_p')}"],
               ["E + GSMaP_NRT", f"{V('nrtE1_m')} ({V('nrtE1_wl')})",
                f"{V('nrtE2_m')} ({V('nrtE2_wl')})",
                f"{V('nrtE3_m')}<br/>{V('nrtE3_ci')}<br/>{V('nrtE3_wl')}, p {V('nrtE3_p')}"],
               ["A + GSMaP_NRT", f"{V('nrtA1_m')} ({V('nrtA1_wl')}), p {V('nrtA1_p')}",
                f"{V('nrtA2_m')}<br/>{V('nrtA2_ci')}<br/>{V('nrtA2_wl')}, p {V('nrtA2_p')}",
                f"{V('nrtA3_m')}<br/>{V('nrtA3_ci')}<br/>{V('nrtA3_wl')}, p {V('nrtA3_p')}"]],
              [1.06 * inch, 0.76 * inch, 0.84 * inch, 0.84 * inch], "sat",
              f"{DELTA}NSE FROM SATELLITE RAINFALL, {V('wf_nfold')} YEARLY FOLDS: MEAN, 95% "
              "INTERVAL, FOLDS WON/LOST, WILCOXON p", small=True),
          col_img(r3.crop_sat(), "sat",
                  f"{DELTA}NSE per test year when IMERG or gauge-calibrated GSMaP is added to "
                  "configuration E (three seeds). Shaded: GloFAS regime change (07/2022); "
                  "hollow markers: partial year 2026, excluded."),

          h2("D", "Risk-level detection and flood events"),
          p(f"The level-1 classifier detects {V('c1h1_hits')} of the {V('npos1')} level-1 test "
            f"days one day ahead with {V('c1h1_fa')} false alarms (POD {V('c1h1_pod')}, FAR "
            f"{V('c1h1_far')}, CSI {V('c1h1_csi')}; Table {T['clf']}); CSI falls to "
            f"{V('c1h2_csi')} at h = 2 and {V('c1h3_csi')} at h = 3. Level 2 has only "
            f"{V('npos2')} positive test days, so criterion AC-2 (POD at least {V('ac2_pod')} for "
            "the second level) can be neither met nor evaluated reliably."),
          tbl([["Level", "h", "Positive test days", "POD", "FAR", "CSI", "PR-AUC"]]
              + [[f"{lv} ({V('thr' + lv)} {M3S})" if h == 1 else "", str(h),
                  V("npos" + lv)] + [V(f"c{lv}h{h}_{m}") for m in ("pod", "far", "csi", "pr_auc")]
                 for lv in ("1", "2") for h in (1, 2, 3)],
              [0.8 * inch, 0.22 * inch, 0.56 * inch] + [0.44 * inch] * 3 + [0.52 * inch], "clf",
              "RISK-LEVEL CLASSIFIERS ON THE TEST PERIOD (THRESHOLD 0.5)", small=True),
          NextPageTemplate(["wide_ev", "*", "rest"]),
          p("Scored per flood <i>event</i> (consecutive level-1 days), the main regression "
            f"model catches {V('ev_wf_E1')} of "
            f"{V('ev_nwf')} walk-forward events one day ahead, level with persistence "
            f"({V('ev_wf_P1')}; Fig. {F['ev']}), and has real lead time: {V('ev_lead_n')} "
            "caught events were flagged before their onset, which persistence can never do. "
            f"At h = 2 it catches {V('ev_wf_E2')} against {V('ev_wf_P2')} for persistence and "
            f"at h = 3 none against {V('ev_wf_P3')}, with almost no false events "
            f"({V('ev_fa_E2')} and {V('ev_fa_E3')} against {V('ev_fa_P2')} and "
            f"{V('ev_fa_P3')}). The reason is peak cutting: the forecast peak is a median "
            f"{V('ev_ratio1')}, {V('ev_ratio2')} and {V('ev_ratio3')} of the simulated peak. "
            f"On the {V('ev_nte')} test-period events the counts are {V('ev_te_E1')}, "
            f"{V('ev_te_E2')} and {V('ev_te_E3')} against {V('ev_te_P1')}, {V('ev_te_P2')} and "
            f"{V('ev_te_P3')} for persistence; the walk-forward refits every year, the single "
            "split does not."),

          h2("E", "Alert threshold and calibration"),
          NextPageTemplate(["wide_rel", "*", "rest"]),
          p(f"Across {V('cal_nfold')} folds ({V('cal_n')} days, {V('cal_npos')} level-1 days "
            f"at h = 1) the cost-based threshold cuts misses from {V('cal_p05_miss')} to "
            f"{V('cal_raw_miss')} at the price of {V('cal_raw_fay')} false alarms per year "
            f"instead of {V('cal_p05_fay')}, lowering the 10:1 cost from {V('cal_p05_cost')} to "
            f"{V('cal_raw_cost')} (p = {V('cal_p05_p')}; Table {T['cal']}). Raw probabilities "
            f"are badly scaled: the optimal raw threshold is only {V('cal_raw_thr')}. Isotonic "
            f"calibration does not change the alert cost ({V('cal_iso_cost')}; difference "
            f"{V('cal_dcost')} per fold, p = {V('cal_dcost_p')}), because a monotone map "
            "keeps the ranking of days. What it improves is the probability itself: the Brier "
            f"score falls from {V('cal_brier_raw')} to {V('cal_brier_iso')} (skill score "
            f"{V('cal_bss_raw')} to {V('cal_bss_iso')}, {DELTA}Brier {V('cal_dbrier')} "
            f"{V('cal_dbrier_ci')} per fold, p = {V('cal_dbrier_p')}, better in "
            f"{V('cal_dbrier_win')} folds) and the expected calibration error from "
            f"{V('cal_ece_raw')} to {V('cal_ece_iso')} (Fig. {F['rel']}). After calibration the "
            f"selected threshold ({V('cal_iso_thr')}, range {V('cal_iso_thrlo')}{ND}"
            f"{V('cal_iso_thrhi')}) is close to the Bayes value {V('cal_bay_thr')}, and using "
            f"{V('cal_bay_thr')} directly gives the same cost ({V('cal_bay_cost')}) without any "
            "selection. The operational job therefore displays calibrated probabilities and "
            f"alerts at 1/11. At 5:1 calibration helps slightly ({V('cal_cost5_raw')} to "
            f"{V('cal_cost5_iso')}), at 20:1 it costs more ({V('cal_cost20_raw')} to "
            f"{V('cal_cost20_iso')})."),
          tbl([["Rule", "Threshold", "Misses", "False alarms (per year)", "POD / FAR / CSI",
                "Cost 10:1"]]
              + [[lab, thr, V(f"cal_{t}_miss"), f"{V(f'cal_{t}_fa')} ({V(f'cal_{t}_fay')})",
                  f"{V(f'cal_{t}_pod')} / {V(f'cal_{t}_far')} / {V(f'cal_{t}_csi')}",
                  V(f"cal_{t}_cost")]
                 for t, lab, thr in (
                     ("p05", "Fixed 0.5, raw", V("cal_p05_thr")),
                     ("raw", "Cost-based, raw", f"{V('cal_raw_thr')} ({V('cal_raw_thrlo')}{ND}"
                                                f"{V('cal_raw_thrhi')})"),
                     ("iso", "Cost-based, isotonic", f"{V('cal_iso_thr')} ({V('cal_iso_thrlo')}{ND}"
                                                     f"{V('cal_iso_thrhi')})"),
                     ("bay", "Bayes 1/11, isotonic", V("cal_bay_thr")))],
              [0.86 * inch, 0.6 * inch, 0.4 * inch, 0.56 * inch, 0.68 * inch, 0.4 * inch], "cal",
              f"LEVEL-1 ALERTS AT h = 1, CONFIGURATION E, {V('cal_nfold')} WALK-FORWARD FOLDS "
              "(THRESHOLD: MEDIAN AND RANGE OVER FOLDS)", small=True),

          h2("F", "Peak underprediction"),
          p("Peaks are cut at every horizon: the mean peak bias of configuration E on the "
            f"test period is {V('pk_testpb1')}, {V('pk_testpb2')} and {V('pk_testpb3')}. For the "
            "forecast issued on 15 October 2022 the model gave "
            f"{V('wf_fc_2022')} {M3S} against a GloFAS peak of "
            f"{V('r2_2022-10-15_glofas_best')} {M3S}; on 30 October 2025 it gave "
            f"{V('wf_fc_2025')} against {V('q_max_test')} {M3S}. The limit is structural: only "
            f"{V('wf_n_above')} of the {V('ntrE')} training days exceed the 2022 peak, each "
            f"leaf holds at least {V('lgb_mcs')} days, the L1 loss targets a conditional median, "
            f"and every training day above {V('wf_q2000')} {M3S} receded the next day, so the "
            "model predicts recession while the river is still rising. Section VII tests "
            "three remedies."),
          col_fig("shap_waterfall_20221016_h1_en.png", "wfall",
                  "SHAP waterfall (log(1 + Q) units) for the forecast issued on 15 October 2022: "
                  "discharge and rainfall push the forecast up, but it stays far below the "
                  "simulated peak of the next day.", scale=0.88),

          h2("G", "Explainability"),
          p("Tree SHAP on configuration E (Fig. "
            f"{F['shap']}) shows a plausible core. Today's discharge dominates at h = 1 "
            f"({V('sf_discharge_1')}% of mean |SHAP|); with lead time the weight moves from "
            f"lagged discharge ({V('sg_flow_1')}% to {V('sg_flow_3')}% by group) to rainfall "
            f"(largest at h = 2, {V('sg_rain_2')}%) and to large-scale drivers: the pressure, "
            f"wind and humidity group grows from {V('sg_synoptic_1')}% to "
            f"{V('sg_synoptic_3')}%, and the north&#8211;south pressure gradient that marks cold "
            "surges ranks third at h = 3. Two signals are not plausible: soil moisture acts in "
            f"reverse (Spearman correlation with its SHAP value {V('rho_sm_7_28_2')} at h = 2), "
            "because it duplicates wetness already in today's discharge, and the "
            "full-reservoir proxy is not supported. At h = 3 the calendar carries "
            f"{V('sg_season_3')}%: when the dynamical signal is weak the model falls back on "
            "the season."),
          col_fig("shap_groups_en.png", "shap",
                  "Share of grouped mean |SHAP| by mechanism and horizon, configuration E, all "
                  "test days (left) and level-1 days (right); whiskers: range over three seeds.",
                  scale=1.0),

          h2("H", "Reservoirs"),
          p(f"If GloFAS represented the Ta Trach and Binh Dien reservoirs, the 30-day low flow, "
            "runoff ratio, flashiness and storm response after both dams operated "
            "(2014&#8211;2026) should differ from 1998&#8211;2008. None changes "
            f"significantly (low flow {V('r1_low_flow_30d_pre')} to "
            f"{V('r1_low_flow_30d_post')} {M3S}, p = {V('r1_low_flow_30d_p')}; flashiness "
            f"{V('r1_flashiness_rb_pre')} to {V('r1_flashiness_rb_post')}, p = "
            f"{V('r1_flashiness_rb_p')}). Bulletins show the opposite problem: on 15 October "
            f"2022 the dams released at least {V('r2_2022-10-15_q_release_upstream_min')} {M3S} "
            f"with an inflow of {V('r2_2022-10-15_q_inflow_upstream')} {M3S}, while GloFAS "
            f"gave {V('r2_2022-10-15_glofas_best')} {M3S}. The target is an unregulated river "
            "that under-simulates the largest floods; reservoir effects cannot be learned "
            "from it, which motivates relative risk levels and the floor rule."),
          col_fig("res2_release_vs_glofas_en.png", "r2",
                  "Reported dam releases and natural inflows (lower bounds) against GloFAS at "
                  "Kim Long. Points below the diagonal are impossible for the real river.",
                  scale=0.7),

          h2("I", "Acceptance criteria"),
          p(f"Table {T['ac']} sets the results against the criteria fixed in the specification "
            "before modelling. AC-5 is met; AC-3 and AC-6 are met in part (against "
            "persistence, and for level 1 only); AC-1 is met at two of three horizons; AC-2 "
            "could not be evaluated and AC-4 failed. The reasons are stated rather than the "
            "criteria being relaxed."),
          tbl([["Criterion", "Target", "Result", "Status"],
               ["AC-1 regression", f"NSE {V('ac1_h1')} / {V('ac1_h2')} / {V('ac1_h3')}; RMSE "
                f"{V('ac1_rmse')}% below persistence at h = 1",
                f"E: {V('abE1')} / {V('abE2')} / {V('abE3')} (walk-forward {V('wfE0_1')} / "
                f"{V('wfE0_2')} / {V('wfE0_3')}); RMSE {V('rmse_gain1')}% below (A)",
                "Met at h = 1, 2; <b>missed at h = 3</b>"],
               ["AC-2 detection", f"POD at least {V('ac2_pod')} for the second level, h = 1",
                f"POD {V('c2h1_pod')} on {V('npos2')} test days", "Not evaluable"],
               ["AC-3 baselines", "RMSE not above the best baseline at every horizon; raw "
                "GloFAS comparison", f"RMSE {V('lgb_rmse1')} / {V('lgb_rmse2')} / "
                f"{V('lgb_rmse3')} against {V('persistence_rmse1')} / {V('persistence_rmse2')} / "
                f"{V('persistence_rmse3')}", "Met; GloFAS part pending (log)"],
               ["AC-4 level mapping", "Historic floods within one alert stage",
                f"R&#178; = {V('hq_r2')}; bias {V('hq_bias')} m after 07/2022",
                "Failed; replaced by risk levels"],
               ["AC-5 no leakage", f"Leakage tests pass; NSE below {V('leak_eps')}",
                f"All tests pass; highest NSE {V('abE1')}", "Met"],
               ["AC-6 sample size", "At least 30 positive test days for a main conclusion",
                f"Level 1: {V('npos1')}; level 2: {V('npos2')}", "Met for level 1 only"]],
              [0.7 * inch, 0.92 * inch, 1.18 * inch, 0.7 * inch], "ac",
              "ACCEPTANCE CRITERIA OF THE SPECIFICATION AND FINAL STATUS (TEST PERIOD UNLESS "
              "STATED)", small=True)]

    # ============================================================ VI
    s += [h1("VI", "Distributed Processing and Deep Learning"),
          h2("A", "Spark cluster and pipeline parity"),
          p(f"A Spark standalone cluster (one master, {V('n_workers')} workers with "
            f"{V('w_cores')} cores and {V('w_mem')} GB each, Spark {V('spark_ver')}, Java "
            f"{V('java_ver')}, CPU PyTorch {V('torch_ver')}) runs in Docker on one machine; the "
            f"repository mounted at {TT}/opt/repo{TE} plays the role of HDFS or S3. The ETL "
            f"turns {V('era5_rows')} hourly ERA5 rows into {V('era5_out')} cell-days with the "
            "same result as the Polars pipeline, and the "
            f"{V('par_ncol')} hourly rainfall features agree with Polars bit for bit "
            f"({V('par_nh_era5')} hourly and {V('par_nd_era5')} daily cells). Exactness required "
            "summing in the Polars order and taking the sine of the peak hour from a Polars "
            "table, because one unit in the last place can flip a threshold test.", "body0"),
          fig_drawing(arch_drawing(), "arch",
                      "Spark standalone cluster used for the distributed experiments. Three "
                      "containers share one physical machine; the mounted repository replaces "
                      "a distributed file system."),
          p("On the Windows host itself Spark 4 cannot read local Parquet files without the "
            "Hadoop native binaries, which the team chose not to install from unofficial "
            "sources; there data travel through Arrow, a path used only for tests and one "
            f"benchmark row. Run times of the ETL are shown in Fig. {F['etl']}: one to four "
            f"cores speed the cluster up {V('spd_cl')} times, but eight cores on two workers "
            f"are no faster than four on one ({rng('etl_cluster_2w_8c')} s against "
            f"{rng('etl_cluster_1w_4c')} s)."),
          fig_drawing(etl_drawing(), "etl",
                      f"Run time of the hourly-to-daily ETL ({V('era5_rows')} rows). Bars: mean "
                      "of the runs; labels: minimum and maximum. Green: Polars; purple: Spark "
                      "local mode; orange: standalone cluster; grey: Spark on the host via Arrow.")]
    if SF:
        rows = []
        for src, lab in (("imerg", "IMERG"), ("gsmap_gc", "GSMaP-GC"), ("gsmap_nrt", "GSMaP_NRT")):
            rows.append([lab, V(f"fs_{src}_rows"), V(f"fs_{src}_mb"),
                         rng(f"fs_{src}_cluster_2w_8c"), rng(f"fs_{src}_cluster_1w_4c"),
                         rng(f"fs_{src}_docker_local8_drv4g"), rng(f"fs_{src}_docker_polars")])
        s += [h2("B", "Full-scale satellite features"),
              p(f"Report 4 also ran the hourly-feature job on the full satellite record "
                f"({V('fs_sat_mrows')} million hourly rows, {V('fs_mb_tot')} MB of Parquet; "
                f"Table {T['full']}). On the two-worker cluster all {V('fs_values')} compared "
                f"values ({V('fs_hrows')} hourly rows and {V('fs_ncol')} daily features per "
                "product) are bit-identical to Polars. Spark is still slower: in medians, the best Spark "
                f"set-up (local[8]) takes {V('fs_imerg_ratio')}, {V('fs_gsmap_gc_ratio')} and "
                f"{V('fs_gsmap_nrt_ratio')} times as long as Polars in the same container, and "
                "the second worker does not help, because both workers share one machine and "
                "its disk."),
              tbl([["Product", "Hourly rows", "MB", "Cluster 2 x 4", "Cluster 1 x 4",
                    "local[8]", "Polars"]] + rows,
                  [0.62 * inch, 0.66 * inch, 0.32 * inch, 0.5 * inch, 0.5 * inch, 0.46 * inch,
                   0.44 * inch], "full",
                  "FULL-RECORD HOURLY SATELLITE FEATURES IN THE CONTAINERS: SECONDS (MIN"
                  "&#8211;MAX OVER RUNS; FIRST CLUSTER RUN WITH COLD CACHE), START-UP "
                  "EXCLUDED; LOCAL[8] WITH A 4 GB DRIVER", small=True)]
    else:
        s += [h2("B", "Full-scale satellite features"),
              pending("<b>[Full-scale Spark run pending]</b> The run of the hourly-feature job "
                      "on the full IMERG, GSMaP-GC and GSMaP_NRT records "
                      f"({TT}reports/spark/full_scale_*.csv{TE}) is incomplete. This subsection "
                      "will give rows, run times on the cluster, local mode and Polars, and the "
                      "bitwise parity check.")]
    s += [h2("C", "MLlib models"),
          p("MLlib gradient-boosted trees (GBT) and random forests (RF) were first trained on the "
            "configuration-A panel with one split; Spark's CrossValidator splits rows at random, "
            "which lets a model see the future, so it was replaced by a loop over a fixed "
            f"validation period. One day ahead LightGBM was best (GBT {V('ml_gbt_NSE_1')}, RF "
            f"{V('ml_rf_NSE_1')}, LightGBM {V('lgb_nse1')}); RF was ahead at h = 2&#8211;3, but "
            "on one split. To settle this, both models were retrained on the cluster with "
            f"exactly the data of the main model E (from {V('mf_start')}, {V('mf_nfeat')} "
            f"predictors; {V('mf_ngrid')} validation fits) and run through the same "
            f"{V('mf_nfold')} walk-forward folds (Table {T['mllib']}). On the test period they "
            f"are level with E at h = 2 only; across the folds both are worse at every horizon, "
            "with the 95% interval below zero and Wilcoxon p &lt; 0.05 (one day ahead GBT "
            f"{V('mf_gbt_w1_m')}, RF {V('mf_rf_w1_m')}, RF losing {V('mf_rf_w1_wl')} folds). "
            "Peak bias is as large as for LightGBM and no level-1 day is caught three days "
            "ahead, so more years and a distributed learner do not remove the peak "
            f"underestimation. The run took {V('mf_wall')} minutes on {V('mf_cores')} cores."),
          tbl([["Model", "Test h=1", "h=2", "h=3", "WF h=1", "h=2", "h=3"],
               ["LightGBM E (main)"] + [V(f"abE{h}") for h in (1, 2, 3)]
               + [V(f"bl_E{h}") for h in (1, 2, 3)],
               ["Spark GBT"] + [V(f"mf_gbt_t{h}") for h in (1, 2, 3)]
               + [V(f"mf_gbt_w{h}") for h in (1, 2, 3)],
               ["Spark RF"] + [V(f"mf_rf_t{h}") for h in (1, 2, 3)]
               + [V(f"mf_rf_w{h}") for h in (1, 2, 3)]],
              [1.1 * inch] + [0.4 * inch] * 3 + [0.46 * inch] + [0.4 * inch] * 2, "mllib",
              "MLLIB ON THE FULL DATA OF THE MAIN MODEL: NSE ON THE TEST PERIOD AND MEAN NSE OVER "
              f"{V('mf_nfold')} WALK-FORWARD FOLDS", small=True),

          h2("D", "Deep learning"),
          p(f"An LSTM [11] reads 14 or 30 days of nine raw daily variables and predicts the "
            f"three horizons jointly; an MLP on the LightGBM lag columns is the deep baseline "
            f"({V('n_dlcfg')} configurations, three seeds). Training was distributed with "
            "PyTorch DDP [22] through Spark, both with TorchDistributor and with a barrier "
            "stage written for the project (TorchDistributor fails on Windows because the "
            "PyTorch build lacks libuv). The single-process run reproduces the experiment "
            f"exactly; all two-rank runs give the same result ({V('c_td_nse1')}, "
            f"{V('c_td_nse2')}, {V('c_td_nse3')}) on one machine and on two workers; DDP "
            f"changes NSE by {V('ddp_d1')}, {V('ddp_d2')} and {V('ddp_d3')}, about one seed "
            f"standard deviation; and it is slower ({rng('c_td_train')} s against "
            f"{rng('d_single_train')} s for one process), because a model of "
            f"{V('n_params')} parameters spends more on gradient synchronisation than the "
            "split saves."),
          tbl([["Run (where)", "Proc. &#215; threads", "Global batch", "Best epoch",
                "train() (s)", "Wall (s)"]]
              + [[lab, px(f"{k}_pt"), V(f"{k}_gb"), V(f"{k}_ep"), rng(f"{k}_train"), rng(f"{k}_wall")]
                 for k, lab in (("w_single", "Single process (host)"),
                                ("w_barrier", "Barrier, local[2] (host)"))]
              + [["TorchDistributor, local (host)", "2 &#215; 2", "&#8212;", "&#8212;",
                  "failed: no libuv", "&#8212;"]]
              + [[lab, px(f"{k}_pt"), V(f"{k}_gb"), V(f"{k}_ep"), rng(f"{k}_train"), rng(f"{k}_wall")]
                 for k, lab in (("d_single", "Single process (container)"),
                                ("d_tdlocal", "TorchDistributor, local (container)"),
                                ("c_td", "TorchDistributor, 2 workers (cluster)"),
                                ("c_barrier", "Barrier, 2 workers (cluster)"))],
              [1.14 * inch, 0.45 * inch, 0.4 * inch, 0.36 * inch, 0.58 * inch, 0.58 * inch], "ddp",
              "DISTRIBUTED LSTM TRAINING (L = 30, MSE, SEED 42); RANGES OVER REPEATED RUNS",
              small=True),
          p(f"On the single split some deep configurations beat LightGBM at h = 2 and 3 (best: "
            f"a peak-weighted MLP, {V('dlmlp2')} against {V('lgb_nse2')} at h = 2), but the "
            f"LSTM selected on validation lost at all horizons ({V('dlsel1')}, {V('dlsel2')}, "
            f"{V('dlsel3')} against {V('lgb_nse1')}, {V('lgb_nse2')}, {V('lgb_nse3')}); the "
            "better configurations were identified only after seeing the test set."),
          p(f"Under the walk-forward (Table {T['dl']}, Fig. {F['dl']}) no deep model beats "
            f"LightGBM consistently: the LSTM with MSE loss is level at h = 1 ({V('lstmM1_m')}, "
            "interval includes zero) and the peak-weighted LSTM loses clearly at h = 3 "
            f"({V('lstmP3_m')}, p = {V('lstmP3_p')}). Deep models detect more level-1 days "
            f"(pooled CSI {V('csi_lstmM')} against {V('csi_lgb')}) and cut peaks less, but "
            f"their seed-to-seed spread is {V('sd_dl_lo')}{ND}{V('sd_dl_hi')} NSE against at "
            f"most {V('sd_lgb')} for LightGBM."),
          tbl([["Model", "h = 1", "h = 2", "h = 3", "CSI lv. 1, h=1"],
               ["LightGBM (NSE)", V("dl_lgb1"), V("dl_lgb2"), V("dl_lgb3"), V("csi_lgb")]]
              + [[name] + [f"{V(t + str(h) + '_m')}<br/>{V(t + str(h) + '_ci')}<br/>"
                           f"{V(t + str(h) + '_wl')}" for h in (1, 2, 3)] + [V(c)]
                 for t, name, c in (("lstmM", "LSTM L=30, MSE", "csi_lstmM"),
                                    ("lstmP", "LSTM L=30, peak-weighted", "csi_lstmP"),
                                    ("mlpP", "MLP on lags, peak-weighted", "csi_mlpP"))],
              [0.98 * inch, 0.72 * inch, 0.72 * inch, 0.72 * inch, 0.38 * inch], "dl",
              f"DEEP LEARNING AGAINST LIGHTGBM (PANEL A), {V('wf_nfold')} YEARLY FOLDS: "
              f"{DELTA}NSE MEAN, 95% INTERVAL, FOLDS WON/LOST", small=True),
          col_img(r3.crop_dl(), "dl",
                  f"Deep learning against LightGBM under the walk-forward: {DELTA}NSE per test "
                  "year, positive when the deep model is better; grey band: largest change "
                  "caused by the torch thread count."),

          h2("E", "Task parallelism and honest assessment"),
          p(f"The deep-learning walk-forward needed {V('wf_nfit')} independent fits "
            f"({V('wf_sec')} s in sequence); a local pool of {V('wf_procs')} processes finished "
            f"them in about {V('wf_min')} minutes. This task parallelism, not data-parallel "
            "DDP, is what shortened the experiments."
            + (f" For the peak experiments of Section VII, {V('wfb_pool_jobs')} LightGBM "
               f"runs took {V('wfb_pool_s')} s on a pool of {V('wfb_pool_cores')} processes."
               if SW.get("pool") else "")
            + (f" The same runs as Spark tasks ({TT}spark_walkforward.py{TE}, two workers, "
               f"{V('wfb_sp_cores')} cores) took {V('wfb_sp_s')} s, {V('wfb_sp_speed')} times "
               "faster than the summed task time, and reproduced the local forecasts of "
               f"{V('wfb_sp_pjobs')} runs up to rounding (largest difference "
               + (f"{V('wfb_sp_diff_m')} &#215; 10<super>{V('wfb_sp_diff_e')}</super>"
                  if "wfb_sp_diff_m" in V.val else V('wfb_sp_diff'))
               + " m<super>3</super>/s; LightGBM is built differently for "
               "Linux and Windows). Part of the gap to the Windows pool may come from the "
               "operating system and the LightGBM build rather than from Spark; what is "
               "established is near-linear scaling of independent fits on the cluster."
               if SW.get("spark") else "")),
          *([] if SW.get("spark") else [pending(
              "<b>[Spark walk-forward pending]</b> The run of the same LightGBM jobs as Spark "
              f"tasks on the cluster ({TT}reports/spark/wf_bench.csv{TE}) has not been recorded "
              "yet. It will give wall time against the sequential and pool runs and the "
              "parity of the forecasts with the local runs.")]),
          p(f"At this data size Spark is slower than Polars: the two-worker ETL takes "
            f"{V('x_c2_wpol')} times as long as Polars on the host, and the hourly features "
            f"{V('x_par_c')} times on the cluster. Measured causes are reading through the "
            "Windows&#8211;Docker mount, partitions skewed by only "
            f"{V('era5_cells')} cell keys, fixed start-up costs and two workers sharing one "
            "machine. Spark becomes the right tool when data no longer fit one machine or "
            "already live in distributed storage, for example many river cells across "
            "Vietnam, or folds and seeds spread over several real machines [23]. The code is "
            "portable: the session reads the master address from an environment variable and "
            "the training function takes the panel path as a parameter, so a managed workspace "
            "such as Databricks [31] could host the same jobs with Delta tables. That step "
            "is a proposal; it was not run and no result here comes from it.")]

    # ============================================================ VII
    s += [h1("VII", "Experiments on Peak Underprediction"),
          p("Report 4 also tested three remedies for peak cutting on the "
            f"{V('pk_nfold')}-fold walk-forward with criteria fixed before running: accept a "
            f"variant only if {DELTA}NSE at h = 2 or 3 is positive with p below 0.05 and h = 1 "
            f"loses at most {V('pk_crit_h1')}, or if detection rises clearly at that cost. "
            "(B1) peak-weighted training, w = 1 + <font face=\"Symbol\">&#945;</font>&#183;max(0, y/level 1 &#8211; 1); "
            "(B2) isotonic correction of log forecasts fitted on earlier folds, on all "
            "forecasts or only on high ones; (B3) a fixed 50/50 average of E and the LSTM. "
            f"The baseline reproduces Report 3 ({V('pk_E1')}, {V('pk_E2')}, {V('pk_E3')}).",
            "body0"),
          tbl([["Variant", f"{DELTA}NSE h = 1", "h = 2", "h = 3", "POD h=1"],
               ["E (baseline NSE)", V("pk_E1"), V("pk_E2"), V("pk_E3"), V("pk_Epod1")]]
              + [[lab,
                  f"{V(f'pk_{v}1_m')} ({V(f'pk_{v}1_wl')}, p {V(f'pk_{v}1_p')})",
                  f"{V(f'pk_{v}2_m')} ({V(f'pk_{v}2_wl')}, p {V(f'pk_{v}2_p')})",
                  f"{V(f'pk_{v}3_m')} ({V(f'pk_{v}3_wl')}, p {V(f'pk_{v}3_p')})",
                  V(f"pk_{v}_pod1")]
                 for v, lab in (("w1", "B1, <font face=\"Symbol\">&#945;</font> = 1"), ("w3", "B1, <font face=\"Symbol\">&#945;</font> = 3"),
                                ("w5", "B1, <font face=\"Symbol\">&#945;</font> = 5"), ("w10", "B1, <font face=\"Symbol\">&#945;</font> = 10"),
                                ("iso", "B2, isotonic"), ("isohi", "B2, high only"),
                                ("lstm", "B3, E + LSTM"))],
              [0.74 * inch, 0.82 * inch, 0.76 * inch, 0.78 * inch, 0.4 * inch], "peak",
              f"PEAK EXPERIMENTS, {V('pk_nfold')} YEARLY FOLDS: {DELTA}NSE AGAINST E (FOLDS "
              "WON/LOST, WILCOXON p)", small=True, bold_rows=(8,)),
          p("<b>No variant meets the criteria, so E remains the main model.</b> Peak weighting "
            f"with <font face=\"Symbol\">&#945;</font> = 3 lifts h = 1 slightly ({V('pk_w31_m')} {V('pk_w31_ci')}, p = "
            f"{V('pk_w31_p')}), POD from {V('pk_Epod1')} to {V('pk_w3_pod1')} and the h = 1 "
            f"peak bias from {V('pk_Epb1')} to {V('pk_w3_pb1')}, but the gain is not "
            "significant, not monotone in <font face=\"Symbol\">&#945;</font> and <font face=\"Symbol\">&#945;</font> was widened after seeing the first "
            f"results; the h = 2&#8211;3 peak bias ({V('pk_Epb2')}, {V('pk_Epb3')}) does not "
            "move. Isotonic correction hurts (h = 3: "
            f"{V('pk_iso3_m')} {V('pk_iso3_ci')}, {V('pk_iso3_wl')} folds, p = "
            f"{V('pk_iso3_p')}) because the mapping from forecast to target is unstable across "
            "years. The E + LSTM average gives the only significant improvement of the whole "
            f"series, at h = 1 ({V('pk_lstm1_m')} {V('pk_lstm1_ci')}, {V('pk_lstm1_wl')} folds, "
            f"p = {V('pk_lstm1_p')}), but it is worse at h = 2 ({V('pk_lstm2_m')}) and h = 3 "
            f"({V('pk_lstm3_m')}, p = {V('pk_lstm3_p')}). Using it only at h = 1 would be a "
            "choice made after seeing the results and would add PyTorch to the daily job; it "
            "is recorded as future work, to be tested on new data. Two to three days before a "
            "peak the flood-producing rain has usually not fallen, so peak cutting at "
            "h = 2&#8211;3 needs good rainfall forecasts or release data, not a different loss.")]

    # ============================================================ VIII
    s += [h1("VIII", "Operational System"),
          p("A GitHub Actions job runs every morning (scheduled at 20:00 UTC, in practice near "
            "05:00 local time). It downloads the issued GloFAS forecast and weather forecast, "
            "applies the reservoir floor rule, writes one CSV per issue date to "
            f"{TT}reports/forecast_log/{TE} and commits it; a check fails the job if a day is "
            f"missing. The log starts on 15 September 2026 and holds {V('live_nlogs')} issue "
            f"dates up to {V('live_last')} (20 September was lost to a time-zone bug and is "
            "not imputed).", "body0"),
          p(f"The job now also runs the frozen main model: {V('live_nfeat')} predictors, three "
            "seeds per horizon, L1 at h = 1 and L2 at h = 2&#8211;3, refit on all labelled "
            f"days from 1998 to August 2026 ({V('live_rows')} rows at h = 1). It writes "
            f"{TT}lgbm_q{TE}, the floored {TT}lgbm_san_ho{TE} and a risk level, plus "
            f"{TT}p_level1{TE}: the probability that tomorrow's discharge reaches "
            f"{V('live_level')} {M3S}, calibrated by isotonic regression on "
            f"{V('live_oof_n')} out-of-fold days of 1999&#8211;2025 ({V('live_oof_pos')} "
            f"positive), with an alert at {V('live_thr')} = 1/11. Models are plain-text "
            "LightGBM files downloaded from a GitHub release; the calibration is applied with "
            "linear interpolation, so the job needs neither PyTorch nor scikit-learn."),
          p("<b>Live inputs differ from training inputs.</b> The training panel uses ERA5 "
            "reanalysis; the job uses ERA5 up to about six days before the issue date and "
            f"Open-Meteo forecast data after that, so rain on day t is a <i>forecast</i> for "
            f"the whole day. The noise experiment of Report 3 ({SIGMA} = 1 lowers NSE at h = 1 "
            f"from {V('sb0_h1')} to {V('sb1_h1')}) bounds the expected loss. Soil moisture is "
            "held at its last ERA5-Land value, a failed IBTrACS download is treated as no "
            "storm and flagged, and the GloFAS value for day t is the latest forecast, not "
            "the analysis.")]
    if not LIVE:
        s += [pending("<b>[First operational LightGBM forecasts pending]</b> No issue in "
                      f"{TT}reports/forecast_log/{TE} contains the LightGBM columns yet (the "
                      "model release must be published for the Actions job). Comparison of "
                      "LightGBM with the raw GloFAS forecast on the operational sample (AC-3) "
                      "will be possible once forecasts and verifying GloFAS values overlap.")]
    else:
        s += [p(f"The first operational run with the LightGBM columns was issued on "
                f"{V('live_lgbm_first')} ({V('live_nlgbm')} run(s) so far); AC-3 still needs "
                "weeks of forecasts overlapping verifying GloFAS values.")]
    s += [p("<b>Dashboard.</b> A Streamlit application reads the log and has three tabs: the "
            "forecast (30 past days and three forecast days for raw GloFAS, floored GloFAS and "
            "LightGBM, with the three risk-level lines and a table of levels), a map of the "
            "five sub-basins coloured by the basin-wide level at Kim Long, and an explanation "
            "tab with grouped SHAP shares, skill scores and limitations. It states on every "
            "page that the product is academic and that risk levels are not the official "
            "alert stages. It is deployed at https://dsp391m-huong-flood.streamlit.app.")]

    # ============================================================ IX
    s += [h1("IX", "Discussion"),
          p("<b>What the correction layer adds.</b> The model does not see a better river "
            "than GloFAS; it sees the same simulated river earlier. Its gain over persistence "
            "comes from information GloFAS does not use at the issue time: the antecedent "
            "state carried by recent discharge, rain already fallen on the basin, and "
            "synoptic drivers (storms, cold-surge pressure gradients) that announce rain one to "
            "three days ahead. That is why the large-scale predictors helped at two and three "
            "days while soil moisture and storage proxies did not, and why skill collapses "
            "when the flood-producing rain has not yet fallen.", "body0"),
          p("<b>Single split against walk-forward.</b> Several conclusions changed when the "
            "single test period was replaced by thirteen yearly folds. IMERG looked useful at "
            f"h = 2 on the single split ({V('ss_im2')}) but its fold gain ({V('im2_m')}) has an "
            "interval that includes zero; deep models that beat LightGBM on the test period "
            "did so only in the years that period happened to contain; and the loss switch "
            "for h = 2&#8211;3 was decided on folds and validation, never on the test set. "
            "Every acceptance decision in this project therefore rests on the walk-forward, "
            "and the criteria for the peak experiments were written down before running them."),
          p("<b>Negative results as results.</b> Five lines of work did not improve the "
            "operational forecast: reservoir records, satellite rainfall, deep learning, peak "
            "weighting and Spark. Each produced something usable nonetheless: the reservoir "
            "tests justify percentile risk levels and the floor rule; the latency test showed "
            "which satellite product could be used live; the deep models are the best "
            "detectors at one day; and the Spark jobs reproduce the pipeline exactly, ready "
            f"for larger inputs. Table {T['dev']} lists where the project departed from the "
            "proposal and why."),
          tbl([["Proposal (Report 1)", "Delivered", "Reason"],
               ["Official alert stages as labels", "Percentile risk levels",
                "Discharge does not determine the water level"],
               ["Raw GloFAS forecast as baseline", "Forward log since Sept. 2026",
                "Past flood forecasts are not archived"],
               ["Scenario B with archived rain forecasts", "Noise test on rainfall",
                "The archive returned ERA5 values"],
               ["Three latitude bands", "Five DEM sub-basins", "Hydrologically meaningful units"],
               ["Commune-level risk map", "Sub-basin map, one basin-wide level",
                "Target exists at one cell only"],
               ["Fixed 0.5 alert threshold", "Cost-based, calibrated, 1/11",
                "Misses cost more than false alarms"],
               ["LSTM only if time allowed", "LSTM, MLP, distributed DDP",
                "Requested in the review of Report 3"],
               ["Single machine", "Spark cluster, MLlib, task parallelism",
                "Requested in the review of Report 3"]],
              [1.2 * inch, 1.15 * inch, 1.15 * inch], "dev",
              "DEVIATIONS FROM THE PROPOSAL", small=True)]

    s += [h1("X", "Limitations and Future Work"),
          *bullets([
              "<b>Simulated target.</b> Scores measure agreement with GloFAS, which itself "
              "under-simulates the largest floods; true peaks are under-estimated twice. "
              "GloFAS v5 adds large reservoirs and may change the target; the dam-era test "
              "must then be repeated.",
              f"<b>h = 3 below target.</b> AC-1 is missed at three days ({V('abE3')} test, "
              f"{V('wfE0_3')} walk-forward against {V('ac1_h3')}). Archived rainfall forecasts "
              "would be the most promising input; the archive tested in Report 2 returned "
              "ERA5 values and could not be used.",
              "<b>Regime change.</b> The test period consists of archived GloFAS forecasts; "
              f"only {V('fc_nfold')} walk-forward years fall in that regime, for which the "
              f"smallest attainable Wilcoxon p is {V('fc_pmin')}, so it cannot be tested alone. "
              f"In 2023&#8211;2025 configuration E scored {V('pk_Efc1')}, {V('pk_Efc2')} and "
              f"{V('pk_Efc3')}, in line with earlier years.",
              "<b>One cell, daily target.</b> The 5 km grid does not resolve the Bo River, so "
              "only Kim Long is forecast; the sub-basin map shows one basin-wide level. Finer "
              "and hourly inputs cannot make the daily, gridded target finer.",
              f"<b>Resolution of comparisons.</b> NSE differences below about {V('noise')} are "
              "numerical noise; conclusions rest on fold-level intervals, not on means.",
              "<b>Rare events.</b> Only level 1 has enough events; level 2 and AC-2 cannot be "
              "evaluated, and risk levels are relative, not official stages.",
              "<b>No raw-GloFAS comparison yet.</b> AC-3 depends on the forecast log, which "
              "is short and has not yet overlapped with verifying values.",
              "<b>Operational inputs.</b> Live rainfall for day t is a forecast; satellite "
              "rainfall gave no operational gain on configuration E.",
              "<b>Future work:</b> a horizon-specific E + LSTM ensemble at h = 1 tested on new "
              "seasons; walk-forward folds as Spark tasks on several machines; requesting "
              "gauge data if the project continues beyond the course.",
          ])]

    # ============================================================ X
    s += [h1("XI", "Conclusion"),
          p("Open global data support a useful local forecast of GloFAS discharge at Kim Long. "
            f"LightGBM with {V('nfE')} predictors reaches NSE {V('abE1')}, {V('abE2')} and "
            f"{V('abE3')} on the test period and {V('wfE0_1')}, {V('wfE0_2')} and "
            f"{V('wfE0_3')} across {V('wf_nfold')} years, far above persistence beyond one day, "
            "catches level-1 flood events one day ahead as often as persistence but with lead "
            "time, and provides calibrated alert probabilities. It cuts flood peaks and misses "
            "the three-day target, for reasons that were measured rather than tuned away. "
            "Large-scale weather predictors helped; reservoir data, satellite rain, deep "
            "learning, peak weighting and Spark did not improve the operational forecast at "
            "this scale, and each negative result is documented with its evidence. The model "
            "now runs daily, and its forecasts are shown on a dashboard that states its "
            "limits. The research questions of Report 1 are answered as follows."),
          *bullets([
              f"<b>RQ1.</b> Yes at one and two days (NSE {V('abE1')} and {V('abE2')}, RMSE "
              f"{V('rmse_gain1')}% below persistence at one day); only partly at three days "
              f"({V('abE3')}), with peaks cut at all horizons.",
              "<b>RQ2.</b> Not against official stages, which are water levels that simulated "
              "discharge does not determine; against the first risk level the classifier "
              f"reaches POD {V('c1h1_pod')} and FAR {V('c1h1_far')} one day ahead, and the "
              f"calibrated cost-based rule POD {V('cal_iso_pod')} with FAR {V('cal_iso_far')} "
              "across folds.",
              "<b>RQ3.</b> Only indirectly: the target exists at Kim Long alone, but SHAP "
              f"gives upper-basin rainfall the largest rain share one day ahead "
              f"({V('sf_rain_thuong_1')}% against {V('sf_rain_basin_1')}% for the basin mean), "
              "consistent with the two reservoir catchments supplying most of the flow.",
          ]),
          tbl([["Member", "Role", "Main contributions"],
               ["Dang Nguyen Giap", "Tech Lead",
                "Data engineering, modelling and evaluation, Spark and deep learning, daily "
                "job, integration and review"],
               ["Ho Anh Duc", "Data Analyst",
                "Exploratory analysis, feature engineering, baselines, dashboard"],
               ["Mai Thi Le Huyen", "Research &amp; Docs",
                "Literature review, legal sources, data dictionary, report editing and slides"]],
              [0.95 * inch, 0.75 * inch, 1.8 * inch], "team", "TEAM ROLES", small=True)]

    # ============================================================ refs
    s += [p("REFERENCES", "h1")]
    refs = [
        "[1] L. Alfieri <i>et al.</i>, &#8220;GloFAS &#8211; global ensemble streamflow forecasting "
        "and flood early warning,&#8221; <i>Hydrol. Earth Syst. Sci.</i>, vol. 17, no. 3, "
        "pp. 1161&#8211;1175, 2013.",
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
        "[9] S. Gnjato, I. Lescesen, X. Zhou and D. Dukanovic, &#8220;Explainable machine "
        "learning for streamflow forecasting: application to the Bosna River basin,&#8221; "
        "<i>Water</i>, vol. 18, no. 10, 1226, 2026.",
        "[10] G. Ke <i>et al.</i>, &#8220;LightGBM: A highly efficient gradient boosting "
        "decision tree,&#8221; in <i>Adv. Neural Inf. Process. Syst.</i>, vol. 30, 2017, "
        "pp. 3146&#8211;3154.",
        "[11] F. Kratzert, D. Klotz, C. Brenner, K. Schulz and M. Herrnegger, "
        "&#8220;Rainfall&#8211;runoff modelling using Long Short-Term Memory (LSTM) "
        "networks,&#8221; <i>Hydrol. Earth Syst. Sci.</i>, vol. 22, no. 11, "
        "pp. 6005&#8211;6022, 2018.",
        "[12] F. Kratzert, D. Klotz, G. Shalev, G. Klambauer, S. Hochreiter and G. Nearing, "
        "&#8220;Towards learning universal, regional, and local hydrological behaviors via "
        "machine learning applied to large-sample datasets,&#8221; <i>Hydrol. Earth Syst. "
        "Sci.</i>, vol. 23, no. 12, pp. 5089&#8211;5110, 2019.",
        "[13] J. H. Ougahi and J. S. Rowan, &#8220;Investigating deep learning knowledge "
        "transfer in streamflow prediction from global to local catchment,&#8221; <i>Water "
        "Resour. Res.</i>, 2026, doi: 10.1029/2025WR041194.",
        "[14] J. E. Nash and J. V. Sutcliffe, &#8220;River flow forecasting through conceptual "
        "models part I &#8211; a discussion of principles,&#8221; <i>J. Hydrol.</i>, vol. 10, "
        "no. 3, pp. 282&#8211;290, 1970.",
        "[15] H. V. Gupta, H. Kling, K. K. Yilmaz and G. F. Martinez, &#8220;Decomposition of "
        "the mean squared error and NSE performance criteria: implications for improving "
        "hydrological modelling,&#8221; <i>J. Hydrol.</i>, vol. 377, no. 1&#8211;2, "
        "pp. 80&#8211;91, 2009.",
        "[16] D. N. Moriasi <i>et al.</i>, &#8220;Model evaluation guidelines for systematic "
        "quantification of accuracy in watershed simulations,&#8221; <i>Trans. ASABE</i>, "
        "vol. 50, no. 3, pp. 885&#8211;900, 2007.",
        "[17] G. W. Brier, &#8220;Verification of forecasts expressed in terms of "
        "probability,&#8221; <i>Mon. Weather Rev.</i>, vol. 78, no. 1, pp. 1&#8211;3, 1950.",
        "[18] B. Zadrozny and C. Elkan, &#8220;Transforming classifier scores into accurate "
        "multiclass probability estimates,&#8221; in <i>Proc. 8th ACM SIGKDD Int. Conf. "
        "Knowl. Discov. Data Min.</i>, 2002, pp. 694&#8211;699.",
        "[19] S. M. Lundberg and S.-I. Lee, &#8220;A unified approach to interpreting model "
        "predictions,&#8221; in <i>Adv. Neural Inf. Process. Syst.</i>, 2017, "
        "pp. 4765&#8211;4774.",
        "[20] M. Zaharia <i>et al.</i>, &#8220;Apache Spark: A unified engine for big data "
        "processing,&#8221; <i>Commun. ACM</i>, vol. 59, no. 11, pp. 56&#8211;65, 2016.",
        "[21] X. Meng <i>et al.</i>, &#8220;MLlib: Machine learning in Apache Spark,&#8221; "
        "<i>J. Mach. Learn. Res.</i>, vol. 17, no. 34, pp. 1&#8211;7, 2016.",
        "[22] S. Li <i>et al.</i>, &#8220;PyTorch distributed: Experiences on accelerating data "
        "parallel training,&#8221; <i>Proc. VLDB Endow.</i>, vol. 13, no. 12, "
        "pp. 3005&#8211;3018, 2020.",
        "[23] F. McSherry, M. Isard and D. G. Murray, &#8220;Scalability! But at what "
        "COST?,&#8221; in <i>Proc. 15th Workshop Hot Topics Oper. Syst. (HotOS XV)</i>, 2015.",
        "[24] ESA/Copernicus, &#8220;Copernicus DEM GLO-30.&#8221; [Online]. Available: "
        "https://copernicus-dem-30m.s3.amazonaws.com/",
        "[25] Prime Minister of Vietnam, &#8220;Decision 1606/QD-TTg on the inter-reservoir "
        "operating procedure for the Huong River basin,&#8221; Nov. 2019. [in Vietnamese]",
        "[26] Open-Meteo, &#8220;Flood API and Historical Weather API,&#8221; 2026. [Online]. "
        "Available: https://open-meteo.com/en/docs",
        "[27] NOAA NCEI, &#8220;International Best Track Archive for Climate Stewardship "
        "(IBTrACS) v04r01.&#8221; [Online]. Available: https://www.ncei.noaa.gov/products/"
        "international-best-track-archive",
        "[28] NOAA CPC, &#8220;Oceanic Ni&#241;o Index.&#8221; [Online]. Available: "
        "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "[29] NASA, &#8220;GPM IMERG V07, Earth Engine collection NASA/GPM_L3/IMERG_V07.&#8221;",
        "[30] JAXA, &#8220;GSMaP v8 operational, Earth Engine collection "
        "JAXA/GPM_L3/GSMaP/v8/operational; GSMaP_NRT, JAXA G-Portal.&#8221;",
        "[31] Databricks, &#8220;Databricks Free Edition,&#8221; documentation. [Online]. "
        "Available: https://docs.databricks.com/aws/en/getting-started/free-edition",
    ]
    s += [p(r, "ref") for r in refs]
    return s


# ================================================================== bố cục
def build() -> int:
    global T, F
    fx.load(cfg)
    WARN.extend(fx.WARN)
    if V.bad:
        raise SystemExit("Số trong báo cáo lệch với dữ liệu — sửa văn bản trước khi build:\n"
                         + "\n".join(V.bad))

    tabs = ["anl", "data", "base", "abl", "sat", "clf", "cal", "ac"] \
        + (["full"] if fx.SPARK_FULL else []) + ["mllib", "ddp", "dl", "peak", "dev", "team"]
    T = {k: roman(i) for i, k in enumerate(tabs, start=1)}
    F = {k: str(i) for i, k in enumerate(["basins", "sat", "ev", "rel", "wfall", "shap", "r2",
                                          "arch", "etl", "dl"], start=1)}
    # số hình theo thứ tự in (III-B nhắc trước hình hồ chứa in ở V-H)
    r3.V, r3.T, r3.F = V, T, F

    W = PW - LM - RM
    avail_h = PH - TM - BM

    def fr(x, y, w, h, i):
        return Frame(x, y, w, h, id=i, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Times-Roman", 8.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(PW / 2, BM - 26, str(d.page))
        canvas.drawString(LM, BM - 26, "DSP391m - Data Science Project - Final Report")
        canvas.drawRightString(PW - RM, BM - 26, "FPT University, Fall 2026")
        canvas.restoreState()

    wide_caps: list[Paragraph] = []

    def wide(tid: str, figs) -> PageTemplate:
        parts = []
        for img, key, caption in figs:
            iw, ih = img.getSize()
            cap = Paragraph(f"Fig. {F[key]}.&nbsp; {caption}", ST["capwide"])
            wide_caps.append(cap)
            parts.append((img, W * ih / iw, cap, cap.wrap(W, PH)[1]))
        block = sum(h + 4 + hc + 10 for _, h, _, hc in parts) + 2

        def on_page(canvas, d):
            footer(canvas, d)
            top = PH - TM
            for img, h_img, cap, h_cap in parts:
                canvas.drawImage(img, LM, top - h_img, width=W, height=h_img)
                cap.drawOn(canvas, LM, top - h_img - 4 - h_cap)
                top -= h_img + 4 + h_cap + 10

        return PageTemplate(id=tid, onPage=on_page, frames=[
            fr(LM, BM, COLW, avail_h - block, tid + "l"),
            fr(LM + COLW + GUT, BM, COLW, avail_h - block, tid + "r")])

    sat_ab = (f"{V('fs_all_mrows')} million hourly records" if fx.SPARK_FULL
              else f"{V('sat_mrows')} million hourly satellite records")
    head = [
        p("Forecasting One-to-Three-Day Discharge and Flood Risk of the Huong River at Kim "
          "Long as a Local Correction Layer on GloFAS", "title"),
        p(("&nbsp;" * 4).join(cfg.TEAM_ASCII), "author"),
        Spacer(1, 3),
        p("Department of Information Technology, FPT University<br/>"
          "DSP391m &#8212; Data Science Project &#8212; Final Report, Fall 2026<br/>Hue, Vietnam",
          "affil"),
        Spacer(1, 9),
        Paragraph(
            "<b><i>Abstract</i></b>&#8212;<font size=9>We forecast the daily GloFAS v4 "
            "discharge of the Huong River at Kim Long, Vietnam, one to three days ahead from "
            f"open data only ({sat_ab} and daily records since 1997) and translate it into "
            "flood-risk levels defined as flood-season percentiles, since discharge does not "
            "determine the official water-level alert stages. A LightGBM model with "
            f"{V('nfE')} predictors, including storm, cold-surge and ENSO indicators, reaches "
            f"NSE {V('abE1')}, {V('abE2')} and {V('abE3')} on a test period from July 2022 "
            f"(persistence {V('persistence_nse1')}, {V('persistence_nse2')}, "
            f"{V('persistence_nse3')}) and {V('wfE0_1')}, {V('wfE0_2')} and {V('wfE0_3')} in a "
            f"{V('wf_nfold')}-fold yearly walk-forward; the three-day target of "
            f"{V('ac1_h3')} is missed. One day ahead it catches {V('ev_wf_E1')} of "
            f"{V('ev_nwf')} flood events, as many as persistence but with lead time, and "
            "isotonic calibration makes its alert probability reliable (Brier "
            f"{V('cal_brier_raw')} to {V('cal_brier_iso')}) so that the Bayes threshold 1/11 "
            "can be used directly. Peaks are cut; peak-weighted training, isotonic correction "
            "and an LSTM ensemble did not meet pre-set criteria. Reservoir effects are absent "
            "from the target, satellite rainfall helps only in hindsight, deep learning does "
            "not beat LightGBM across years, and a Spark cluster reproduces the pipeline bit "
            f"for bit but is {V('x_c2_wpol')} times slower than Polars at this scale. The "
            "model runs daily on GitHub Actions and feeds a Streamlit dashboard.</font>",
            ST["abstext"]),
        Paragraph(
            "<b><i>Keywords</i></b>&#8212;<font size=9>flood forecasting, GloFAS "
            "post-processing, LightGBM, walk-forward validation, probability calibration, "
            "Apache Spark, LSTM, Huong River</font>", ST["keywords"]),
    ]
    head_h = sum(fl.wrap(W, PH)[1] + fl.getSpaceBefore() + fl.getSpaceAfter() for fl in head) + 8

    doc = BaseDocTemplate(str(OUT), pagesize=(PW, PH), leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM,
                          title="DSP391m Final Report - Huong River discharge and flood-risk forecasting",
                          author=", ".join(cfg.TEAM_ASCII))
    doc.addPageTemplates([
        PageTemplate(id="first", onPage=footer, frames=[
            fr(LM, PH - TM - head_h, W, head_h, "head"),
            fr(LM, BM, COLW, avail_h - head_h, "c1l"),
            fr(LM + COLW + GUT, BM, COLW, avail_h - head_h, "c1r")]),
        PageTemplate(id="rest", onPage=footer, frames=[
            fr(LM, BM, COLW, avail_h, "cl"),
            fr(LM + COLW + GUT, BM, COLW, avail_h, "cr")]),
        wide("wide_ev", [
            (crop_events(), "ev",
             f"Flood events (runs of level-1 days) of configuration E and persistence. (a) "
             f"Share of events caught (at least one forecast day above the level-1 threshold) "
             f"on the test period ({V('ev_nte')} events) and in the walk-forward "
             f"({V('ev_nwf')} events); (b) forecast peak over simulated peak.")]),
        wide("wide_rel", [
            (crop_reliability(), "rel",
             "Reliability of the level-1 classifier, configuration E, pooled out-of-fold "
             "probabilities 2013&#8211;2025 (h = 1, 2, 3). Orange: raw LightGBM; blue: "
             "isotonic calibration fitted on earlier years only; bars: days per bin (log "
             "scale); hollow markers: fewer than ten days.")]),
    ])

    body = r3.no_orphans(story())
    n_num = r3.check_text(head + body + wide_caps)
    used_bad = sorted(k for k in V.used if k in V.inherited_bad)
    if used_bad:
        raise SystemExit("Khoá in trong PDF lệch nguồn ở sổ Report 3/4:\n"
                         + "\n".join(V.inherited_bad[k] for k in used_bad))
    for k, b in V.inherited_bad.items():
        WARN.append(f"sổ Report 3/4 lệch nguồn ở khoá không in: {b.strip()}")
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
    print(f"→ {OUT.relative_to(ROOT)}  ({n_pages} trang, {OUT.stat().st_size // 1024} KB)")
    print(f"→ {OUTLINE.relative_to(ROOT)}")
    return 0


# ============================================================ dàn ý tiếng Việt
def write_outline(n_pages: int) -> None:
    o = dict(V.val)
    SF, SW, LIVE = fx.SPARK_FULL, fx.SPARK_WF or {}, fx.LIVE_LGBM

    def g(k: str) -> str:
        return o.get(k, "?")

    pend = []
    if not SF:
        pend.append("VI-B Spark quy mô đủ: reports/spark/full_scale_*.csv chưa đủ → khung [Full-scale Spark run pending]")
    if not SW.get("spark"):
        pend.append("VI-E Spark walk-forward: reports/spark/wf_bench.csv chưa có dòng engine=spark → khung [Spark walk-forward pending]")
    if not LIVE:
        pend.append("VIII Job hằng ngày: chưa bản phát nào trong reports/forecast_log/ có cột lgbm_q → khung [First operational LightGBM forecasts pending]")
    spark_full = (f"   Spark quy mô đủ: {g('fs_sat_mrows')} triệu dòng giờ vệ tinh ({g('fs_mb_tot')} MB); {g('fs_values')} giá trị trùng Polars TỪNG BIT;\n"
                  f"   Spark tốt nhất chậm hơn Polars {g('fs_imerg_ratio')} / {g('fs_gsmap_gc_ratio')} / {g('fs_gsmap_nrt_ratio')} lần (IMERG / GSMaP-GC / NRT).\n"
                  if SF else "   Spark quy mô đủ: CHỜ.\n")
    lines = f"""DÀN Ý BÁO CÁO CUỐI KỲ — DỰ BÁO LƯU LƯỢNG & MỨC NGUY CƠ LŨ SÔNG HƯƠNG TẠI KIM LONG (IEEE, {n_pages} trang)
File: reports/final/DSP391m_Final_Report_IEEE.pdf
Build: PYTHONIOENCODING=utf-8 python reports/final/build_report.py   (mọi số kiểm với CSV/cấu hình lúc build)
Gộp Report 1 (đề xuất) + Report 2 (dữ liệu/EDA) + Report 3 (mô hình) + Report 4 (Spark/DL) + phần làm sau Report 4.

Câu định vị: mô hình là LỚP HIỆU CHỈNH CỤC BỘ trên GloFAS, không thay GloFAS. Mục tiêu = lưu lượng GloFAS v4
theo NGÀY tại ô ({g('pt_lat')} N, {g('pt_lon')} E). Mức nguy cơ = phân vị mùa lũ {g('thr1')} / {g('thr2')} / {g('thr3')} m³/s, KHÔNG phải BĐ I/II/III.

I. GIỚI THIỆU — bài toán, vì sao làm lớp hiệu chỉnh trên GloFAS, 5 đóng góp (pipeline mở, LightGBM E, mức nguy cơ +
   ngưỡng chi phí + hiệu chỉnh, kết quả âm báo trung thực, job hằng ngày + dashboard).
II. NGHIÊN CỨU LIÊN QUAN — GloFAS + hậu xử lý [1,2,7,8]; GBDT/LSTM [10–13,6]; NSE/KGE/Moriasi/Brier/isotonic/SHAP; Spark/MLlib/DDP/COST.
III. KHU VỰC & DỮ LIỆU
 A. Lưu vực ~{g('area_cfg')} km² (DEM {g('area_dem')}); đính chính {g('area_sys')} km² (gồm sông Bồ). 5 lưu vực con (Hình {F['basins']}). Hồ Tả Trạch {g('cap_tt')}, Bình Điền {g('cap_bd')} triệu m³.
 B. Mục tiêu GloFAS: mô phỏng; đổi chế độ 07/2022 (MW p {g('mw_p')}, chỉ {g('fc_nfold')} fold trong chế độ mới); không có hồ, mô phỏng thiếu lũ lớn
    (lượng nước vào hồ > GloFAS {g('r2_inf')} ngày) — Hình {F['r2']}.
 C. Biến dự báo (Bảng {T['data']}; Bảng {T['anl']} = vị trí 4 loại phân tích): ERA5 {g('era5_rows')} dòng giờ, ERA5-Land, IBTrACS {g('storms')} cơn, KK lạnh, ONI trễ 3 tháng, đại diện hồ,
    IMERG/GSMaP/GSMaP_NRT {g('sat_cells')} ô; tổng ~{g('fs_all_mrows')} triệu bản ghi giờ.
 D. EDA (Report 2): {g('eda_ndays')} ngày, Q trung vị {g('eda_qmed')}, cực đại {g('eda_qmax')} (08/11/2011), lệch {g('eda_skew')}; tháng 9–12 = {g('eda_sepdec')} % dòng chảy;
    r trễ 1 ngày {g('eda_r1')}; nền ẩm/khô {g('eda_wet')} / {g('eda_dry')} m³/s.
 E. Kỹ thuật dữ liệu: tác vụ độc lập + bỏ qua file đã có + khoá chống chạy song song; giờ VN; kiểm lỗi; so nguồn mưa
    (IMERG/GSMaP/GC = {g('rr_imerg')} / {g('rr_gsmap')} / {g('rr_gc')} lần ERA5; PERSIANN-CCS bị loại).
 F. Không có số liệu KTTV: nhóm quyết định không xin; R² H–Q = {g('hq_r2')} trên {g('hq_n')} đợt, chệch {g('hq_bias')} m ⇒ không dùng mét.
IV. PHƯƠNG PHÁP — A→E ({g('nfA')} → {g('nfE')} feature); test rò rỉ (NSE < {g('leak_eps')}); split ≤2015 / valid → 06/2022 / test ≥ 07/2022 ({g('n_test1')} ngày);
    walk-forward {g('wf_nfold')} fold, gap 3 ngày, bootstrap + Wilcoxon, nhiễu ±{g('noise')}; LightGBM {g('lgb_trees')} cây, lr {g('lgb_lr')}, L1 h1 / L2 h2–h3
    (chọn bằng WF: {g('tun2_m')} / {g('tun3_m')}, p {g('tun2_p')} / {g('tun3_p')}); đóng băng {g('pk_freeze')}; baseline; mức nguy cơ; bộ phân loại + ngưỡng chi phí 10:1
    + isotonic (Bayes 1/11 = {g('cal_bay_thr')}); luật nâng sàn hồ.
V. KẾT QUẢ
 A. Bảng {T['base']}: E test {g('abE1')} / {g('abE2')} / {g('abE3')}; WF {g('wfE0_1')} / {g('wfE0_2')} / {g('wfE0_3')}; persistence test {g('persistence_nse1')} / {g('persistence_nse2')} / {g('persistence_nse3')},
    WF {g('pk_P1')} / {g('pk_P2')} / {g('pk_P3')}. AC-1: ĐẠT h1, h2; TRƯỢT h3 ({g('abE3')} < {g('ac1_h3')}) — nói thẳng.
 B. Ablation (Bảng {T['abl']}): B giúp h1 ({g('abBA1')}); E giúp h2/h3 ({g('abED2')} / {g('abED3')}).
 C. Vệ tinh (Bảng {T['sat']}, Hình {F['sat']}): GSMaP-GC h3 {g('gc3_m')} p {g('gc3_p')} nhưng trễ {g('lat_gsmap')} h → trễ 1 ngày còn {g('lag1_3_m')}. GSMaP_NRT: giúp A
    ({g('nrtA1_m')} / {g('nrtA2_m')} / {g('nrtA3_m')}) nhưng KHÔNG giúp E ({g('nrtE1_m')} / {g('nrtE2_m')} / {g('nrtE3_m')}) ⇒ không đưa vào job.
 D. Phân loại mức 1 h1: POD {g('c1h1_pod')}, FAR {g('c1h1_far')}, CSI {g('c1h1_csi')} (Bảng {T['clf']}). Theo ĐỢT (Hình {F['ev']}): WF h1 bắt {g('ev_wf_E1')}/{g('ev_nwf')}
    = persistence {g('ev_wf_P1')}, có báo trước ({g('ev_lead_n')} đợt); h2 {g('ev_wf_E2')} vs {g('ev_wf_P2')}; h3 0 vs {g('ev_wf_P3')}; tỉ số đỉnh {g('ev_ratio1')} / {g('ev_ratio2')} / {g('ev_ratio3')}.
 E. Ngưỡng chi phí + isotonic (Bảng {T['cal']}, Hình {F['rel']}): chi phí 10:1 {g('cal_p05_cost')} → {g('cal_raw_cost')} → {g('cal_iso_cost')}; isotonic KHÔNG giảm chi phí
    (p {g('cal_dcost_p')}) nhưng Brier {g('cal_brier_raw')} → {g('cal_brier_iso')} (p {g('cal_dbrier_p')}, {g('cal_dbrier_win')}/13 fold), ECE {g('cal_ece_raw')} → {g('cal_ece_iso')};
    ngưỡng sau hiệu chỉnh {g('cal_iso_thr')} ≈ Bayes {g('cal_bay_thr')} ⇒ job dùng 1/11.
 F. Cắt ngọn: peak bias test {g('pk_testpb1')} / {g('pk_testpb2')} / {g('pk_testpb3')}; 15/10/2022 dự báo {g('wf_fc_2022')} vs {g('r2_2022-10-15_glofas_best')}.
 G. SHAP (Hình {F['shap']}; waterfall Hình {F['wfall']}): lưu lượng hôm nay {g('sf_discharge_1')} % h1; khí áp/gió {g('sg_synoptic_1')} → {g('sg_synoptic_3')} %; độ ẩm đất NGƯỢC chiều; h3 lịch {g('sg_season_3')} %.
 H. Hồ chứa: không chỉ số nào đổi; 15/10/2022 xả ≥ {g('r2_2022-10-15_q_release_upstream_min')} vs GloFAS {g('r2_2022-10-15_glofas_best')} (Hình {F['r2']}).
 I. Tiêu chí nghiệm thu (Bảng {T['ac']}): AC-1 đạt h1/h2, TRƯỢT h3; AC-2 không đánh giá được; AC-3 đạt so với persistence, phần GloFAS chờ;
    AC-4 thất bại → mức nguy cơ; AC-5 đạt; AC-6 chỉ mức 1.
VI. PHÂN TÁN & DL — cụm {g('n_workers')} worker × {g('w_cores')} lõi, Spark {g('spark_ver')}; ETL {g('era5_rows')} → {g('era5_out')}; {g('par_ncol')} đặc trưng giờ trùng TỪNG BIT.
{spark_full}   Kiến trúc Hình {F['arch']}, ETL Hình {F['etl']}. MLlib (Bảng {T['mllib']}): một lần chia GBT {g('ml_gbt_NSE_1')}, RF {g('ml_rf_NSE_1')} vs {g('lgb_nse1')} ở h1; dữ liệu đầy đủ E + walk-forward {g('mf_nfold')} fold: kém E cả 3 horizon (h1 GBT {g('mf_gbt_w1_m')}, RF {g('mf_rf_w1_m')}; h3 {g('mf_gbt_w3_m')} / {g('mf_rf_w3_m')}; p < 0,05). DDP: cùng NSE mọi cách phân tán, chậm hơn 1 tiến trình (Bảng {T['ddp']}).
   DL walk-forward (Bảng {T['dl']}, Hình {F['dl']}): không thắng vững (LSTM nhấn đỉnh h3 {g('lstmP3_m')}, p {g('lstmP3_p')}). Song song theo TÁC VỤ mới có lợi
   ({g('wf_nfit')} lần fit, ~{g('wf_min')} phút; wf_peak pool {g('wfb_pool_jobs')} lượt {g('wfb_pool_s')} s). ETL cụm chậm {g('x_c2_wpol')} lần Polars.
VII. THỬ GIẢM CẮT NGỌN (Bảng {T['peak']}, FINDINGS_PEAK): tiêu chí đặt trước; KHÔNG biến thể nào đạt ⇒ giữ E (đóng băng {g('pk_freeze')}).
    α = 3: h1 {g('pk_w31_m')} (p {g('pk_w31_p')}), POD {g('pk_Epod1')} → {g('pk_w3_pod1')}; isotonic hại h3 {g('pk_iso3_m')} (p {g('pk_iso3_p')});
    E + LSTM h1 {g('pk_lstm1_m')} {g('pk_lstm1_ci')} p {g('pk_lstm1_p')} — DUY NHẤT có ý nghĩa — nhưng h2 {g('pk_lstm2_m')}, h3 {g('pk_lstm3_m')} (p {g('pk_lstm3_p')}) ⇒ hướng tiếp theo.
VIII. HỆ THỐNG VẬN HÀNH — GitHub Actions 20:00 UTC (~05:00 VN); nhật ký từ 15/09/2026 ({g('live_nlogs')} ngày phát tới {g('live_last')}, mất 20/09).
    LightGBM E đóng băng ({g('live_rows')} hàng h1), cột lgbm_q / lgbm_san_ho / p_level1 (isotonic trên {g('live_oof_n')} ngày OOF, báo ở {g('live_thr')} = 1/11).
    ĐẦU VÀO CHẠY THẬT KHÁC LÚC HỌC: mưa ngày t là mưa DỰ BÁO; độ ẩm đất giữ giá trị cuối; bão tải lỗi = không bão.
    Dashboard Streamlit 3 tab (dự báo, bản đồ 5 lưu vực con, giải thích & hạn chế).
IX. THẢO LUẬN — lớp hiệu chỉnh thêm gì (thông tin GloFAS không dùng lúc phát báo); một lần chia vs walk-forward
    (IMERG {g('ss_im2')} → {g('im2_m')}); kết quả âm vẫn có ích; Bảng {T['dev']} sai khác so với đề xuất (BĐ → mức nguy cơ, GloFAS thô → nhật ký,
    kịch bản B → thử nhiễu, 3 dải → 5 lưu vực con, ngưỡng 0,5 → chi phí + 1/11, LSTM + Spark do thầy yêu cầu).
X. HẠN CHẾ & HƯỚNG TIẾP — mục tiêu mô phỏng; h3 dưới AC-1; đổi chế độ 07/2022 (2023–2025: {g('pk_Efc1')} / {g('pk_Efc2')} / {g('pk_Efc3')});
    một ô, mục tiêu ngày; nhiễu ±{g('noise')}; mức 2 quá ít; chưa so GloFAS thô (AC-3); đầu vào chạy thật.
XI. KẾT LUẬN + trả lời RQ1–RQ3 của Report 1 + bảng vai trò nhóm (chỉ tên + vai trò).

KHUNG CHỜ (pending) TRONG BẢN BUILD NÀY:
""" + ("\n".join(f" - {x}" for x in pend) or " (không có)") + """

CÂU HỎI DỄ BỊ HỎI — trả lời ngắn
 - "Sao không so với GloFAS?" → kho dự báo lưu lượng quá khứ không có (404); nhật ký từ 15/09/2026, chưa đủ cặp kiểm.
 - "Sao không dùng BĐ I/II/III?" → R² H–Q thấp; mức nguy cơ là tương đối, KHÔNG phải cấp báo động chính thức.
 - "h3 trượt AC-1?" → đúng, nói thẳng: mưa gây lũ 2–3 ngày sau chưa rơi lúc phát báo; cần mưa dự báo tốt.
 - "Isotonic để làm gì nếu chi phí không đổi?" → xác suất hiển thị đúng nghĩa + dùng thẳng ngưỡng Bayes 1/11, không phải chọn lại.
 - "E + LSTM tốt hơn ở h1 sao không dùng?" → tiêu chí đặt cho h2–h3; chỉ dùng h1 là chọn sau khi xem; thêm torch vào job.
 - "Spark để làm gì nếu chậm hơn?" → chứng minh pipeline ĐÚNG khi phân tán (trùng từng bit) + đo được vì sao chậm + khi nào đáng dùng.

CHỖ NHÓM CẦN KIỂM LẠI TRƯỚC KHI NỘP
 - Số chỉ có trong tài liệu (loại doc bên dưới).
 - Số Spark quy mô đủ / wf_bench / nhật ký dự báo được TÍNH lúc build từ file đang thay đổi (nguồn ghi "tính lúc build") — build lại sát ngày nộp.
 - Tài liệu tham khảo [17], [18] (Brier, Zadrozny & Elkan) mới thêm ở bản cuối kỳ: kiểm lại trang/năm.
"""
    rows = ["", "=" * 100, "DANH SÁCH SỐ DÙNG TRONG BÁO CÁO (sinh tự động lúc build; chỉ khoá in trong PDF)",
            "loại: csv = đã kiểm với file lúc build · claim = câu định tính đã kiểm · doc = chỉ có trong tài liệu",
            "=" * 100]
    for k in V.val:
        if k in V.used:
            rows.append(f"{V.kind[k]:<6} {k:<40} {V.val[k]:<26} {V.src[k]}")
    rows.append(f"\n({len(V.val) - len(V.used)} khoá khác của sổ Report 3/4 + bản cuối kỳ được nạp và kiểm nhưng không in.)")
    docs = [k for k in V.val if V.kind[k] == "doc" and k in V.used]
    rows += ["", f"SỐ CHỈ CÓ TRONG TÀI LIỆU, CÓ IN TRONG PDF ({len(docs)}) — nhóm kiểm lại:"]
    rows += [f" - {k} = {V.val[k]}  ({V.src[k]})" for k in docs]
    rows += ["", "CẢNH BÁO LẦN BUILD NÀY:"] + ([f" - {w}" for w in WARN] or [" (không có)"])
    OUTLINE.write_text(lines + "\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(build())
