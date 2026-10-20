"""Sinh Report 4 (Distributed processing & Deep Learning) theo định dạng IEEE hai cột.

    PYTHONIOENCODING=utf-8 python reports/report4/build_report.py

Cùng khuôn với Report 3: kiểu chữ, helper (``p``, ``h1``, ``h2``, ``tbl``, ``col_fig``,
``no_orphans``) và ba lớp bảo vệ được *import* từ ``reports/report3/build_report.py``,
chỉ trỏ sổ số liệu / số bảng / số hình sang của Report 4:

1. **Số đối chiếu với nguồn lúc build** (``facts.py``): văn bản lấy số qua ``V(key)``;
   mỗi khoá được tính lại từ ``reports/**/*.csv``, cấu hình ``infra/spark`` hoặc metadata
   parquet và so với chuỗi định in. Lệch là build hỏng.
2. **Quét số trong PDF**: mọi số thập phân / số có dấu phẩy nghìn trong thân bài, bảng,
   chú thích phải có trong sổ.
3. **Ký tự ngoài WinAnsi** (font Times chuẩn không vẽ được) ⇒ build hỏng.

Hai hình vẽ bằng reportlab (kiến trúc cụm, thời gian ETL) lấy chữ và số từ cùng sổ.
Build ghi ``reports/report4/OUTLINE_VI.txt``: dàn ý tiếng Việt + mọi số đã dùng kèm nguồn.
Chỉ đọc CSV/hình đã có — không chạy lại thí nghiệm.
"""

from __future__ import annotations

import html
import importlib.util
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


r3 = _load("report3_build_r4", ROOT / "reports" / "report3" / "build_report.py")
fx = _load("report4_facts", HERE / "facts.py")
p, bullets, h1, h2, ST, tbl, col_fig = r3.p, r3.bullets, r3.h1, r3.h2, r3.ST, r3.tbl, r3.col_fig
COLW, LM, RM, TM, BM, GUT, PW, PH = r3.COLW, r3.LM, r3.RM, r3.TM, r3.BM, r3.GUT, r3.PW, r3.PH
FIGS = r3.FIGS
DELTA, DEG, M3S = r3.DELTA, r3.DEG, r3.M3S
OUT = HERE / "DSP391m_Report4_Distributed_DL_IEEE.pdf"
OUTLINE = HERE / "OUTLINE_VI.txt"

V = fx.R            # V("key") → số đã kiểm, dấu trừ in thành gạch en
rng = fx.rng        # "a–b" từ khoá _lo/_hi
WARN: list[str] = []

T = {k: r3.roman(i) for i, k in enumerate(["data", "parity", "mllib", "ddp", "wf"], start=1)}
F = {k: str(i) for i, k in enumerate(["arch", "etl", "dlsplit", "wfdl"], start=1)}
# helper của Report 3 đọc sổ / số bảng / số hình qua biến toàn cục của module ⇒ trỏ sang Report 4
r3.V, r3.T, r3.F = V, T, F

TT = "<font face='Courier'>"        # tên file / hàm
TE = "</font>"


def raw(key: str) -> str:
    """Số cho chữ trong hình vẽ (không phải HTML)."""
    return html.unescape(V(key))


def px(key: str) -> str:
    """'2 x 4' → '2 × 4'."""
    return V(key).replace(" x ", " &#215; ")


# ================================================================ hình vẽ
def arch_drawing() -> Drawing:
    """Hình 1: cụm Spark standalone trên Docker, một máy vật lý."""
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
                 fontName="Times-Roman", fontSize=6.6,
                 textAnchor="middle"))
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
    """Hình 2: thời gian ETL giờ → ngày (thanh = trung bình các lần chạy, nhãn = min–max)."""
    eb = fx._csv("spark/etl_benchmark.csv")
    mean = eb.groupby("tag").seconds_etl.mean()
    order = list(ETL_LABEL)
    W, row = COLW - 0.06 * inch, 13.5
    H = row * len(order) + 22
    lab_w, val_w = 104, 40
    bar_w = W - lab_w - val_w
    scale = bar_w / mean[order].max()
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


def crop_dlsplit() -> ImageReader:
    """Hàng NSE (một lần chia, 8 cấu hình DL so với LightGBM) của dl_vs_lgbm_en.png."""
    im = PILImage.open(FIGS / "dl_vs_lgbm_en.png").convert("RGB")
    if im.size != (2212, 1666):
        WARN.append(f"dl_vs_lgbm_en.png đổi kích thước {im.size} — dùng nguyên hình, kiểm lại bố cục")
        return ImageReader(im)
    return ImageReader(im.crop((0, 100, im.size[0], 580)))


def full_wfdl() -> ImageReader:
    im = PILImage.open(FIGS / "wf_dl_en.png").convert("RGB")
    if im.size != (2046, 1395):
        WARN.append(f"wf_dl_en.png đổi kích thước {im.size} — kiểm lại bố cục")
    return ImageReader(im)


# ================================================================== nội dung
def story() -> list:
    s: list = []

    # ============================================================ I
    s += [h1("I", "Introduction"),
          p("The project forecasts the daily discharge of the Huong River at Kim Long (Hue, "
            "Vietnam) one, two and three days ahead from open data, using the GloFAS v4 "
            "simulation as the target [1], [2]. Report 3 selected LightGBM [10] as the main "
            f"model (NSE {V('abE1')}, {V('abE2')} and {V('abE3')} on the test period from July "
            "2022) and introduced a yearly walk-forward evaluation. The lecturer's review "
            "asked that Report 4 treat the data as distributed, train the models with Apache "
            "Spark [3] and, better still, use deep learning. This report answers that request "
            "and reports what it costs.", "body0"),
          p("The raw inputs are hourly (Table " + T["data"] + "). ERA5 rainfall from Open-Meteo "
            f"has {V('era5_rows')} hourly rows for {V('era5_cells')} cells since 2015, and "
            f"satellite rainfall from IMERG V07 and GSMaP v8 on {V('sat_cells')} cells since "
            f"1998 adds {V('sat_mrows')} million rows. In bytes the data are small: "
            f"{V('era5_mb')} MB and {V('sat_mb')} MB of compressed Parquet, and the modelling "
            "table has one row per day. The useful questions are therefore whether the "
            "pipeline stays correct when it is split across executors, and how a distributed "
            "system compares with a good single-machine implementation [4]."),
          tbl([["Source", "Cells (grid)", "Step", "Period", "Rows", "Size"],
               ["ERA5, Open-Meteo", f"{V('era5_cells')} ({V('grid_sat')}{DEG})", "1 h",
                "2015&#8211;Aug. 2026", V("era5_rows"), f"{V('era5_mb')} MB"],
               ["IMERG V07, Earth Engine", f"{V('sat_cells')} ({V('grid_sat')}{DEG})", "30 min",
                "1998&#8211;Oct. 2026", V("rows_imerg"), f"{V('sat_mb')} MB (with GSMaP)"],
               ["GSMaP v8, raw and gauge-calibrated", f"{V('sat_cells')} ({V('grid_sat')}{DEG})", "1 h",
                "1998&#8211;Oct. 2026", V("rows_gsmap"), ""],
               ["PERSIANN-CCS (test months)", f"{V('pccs_cells')} ({V('grid_pccs')}{DEG})", "1 h",
                "Oct.&#8211;Nov. 2020", V("rows_pccs"), "&#8212;"],
               ["ERA5 after the Spark ETL", f"{V('era5_cells')} cells", "1 day",
                "2015&#8211;Aug. 2026", V("era5_out"), "&#8212;"]],
              [0.9 * inch, 0.6 * inch, 0.34 * inch, 0.6 * inch, 0.56 * inch, 0.52 * inch], "data",
              "HOURLY INPUT DATA (ROWS = CELL &#215; TIME STEP; SIZE = PARQUET ON DISK)", small=True),
          p("Contributions: (i) a Spark standalone cluster and three Spark jobs that reproduce "
            "the single-machine pipeline exactly, the hourly features bit for bit; (ii) MLlib "
            "gradient-boosted trees and random forests [5] trained on the cluster with a "
            "leakage-free hyperparameter search; (iii) LSTM training with PyTorch distributed "
            "data parallel (DDP) [6] through Spark, with TorchDistributor [7] and a barrier-mode "
            "fallback; (iv) a walk-forward comparison of deep learning with LightGBM; and (v) "
            "measured run times with an explanation of why Spark is slower here and when it "
            "would not be.")]

    # ============================================================ II
    s += [h1("II", "Distributed Architecture"),
          h2("A", "Cluster"),
          p(f"The cluster runs on Docker Desktop: one master and {V('n_workers')} workers with "
            f"{V('w_cores')} cores and {V('w_mem')} GB each (Fig. {F['arch']}), built from the "
            f"official Spark {V('spark_ver')} image with Java {V('java_ver')}, Polars "
            f"{V('polars_ver')} and CPU PyTorch {V('torch_ver')}; the host has pyspark "
            f"{V('pyspark_ver')}, matching the cluster. The repository is mounted at "
            f"{TT}/opt/repo{TE} in all three containers. This shared folder plays the role that "
            "HDFS, S3 or a Delta Lake table [8] plays in a production cluster: an executor on "
            "any worker reads and writes the same paths. All containers run on one physical "
            "machine, so the set-up is distributed in protocol (separate executors, barrier "
            "stages, gradient exchange over the Docker network) but adds no hardware."),
          fig_drawing(arch_drawing(), "arch",
                      "Spark standalone cluster used in this report. Three containers share one "
                      "physical machine; the mounted repository replaces a distributed file "
                      "system."),
          p("On the Windows host itself Spark 4 cannot read local Parquet files without the "
            "Hadoop native binaries (winutils), which the team chose not to install from "
            "unofficial sources. On the host, data therefore travel through Arrow (Polars "
            "reads, Spark computes, Polars writes); this path is used only for unit tests and "
            "for one benchmark row."),

          h2("B", "Hourly-to-daily ETL"),
          p(f"{TT}spark_etl.py{TE} reads {V('era5_files')} Parquet files ({V('era5_rows')} rows) "
            f"and writes {V('era5_out')} cell-days ({V('era5_cells')} cells &#215; "
            f"{V('era5_days')} days), partitioned by year: daily total, maximum 1-, 3- and 6-h "
            "rain, wet hours and peak hour. Sliding windows are defined on time "
            f"({TT}rangeBetween{TE} in seconds), not on row counts, so a missing hour cannot "
            "stretch a window, and windows reach back into the previous day so that a storm "
            "crossing midnight is not cut in two. Sub-basin rainfall is averaged at the hourly "
            f"level before the daily indices are computed ({V('sub_rows')} sub-basin-days). "
            "Against the Polars implementation every row matches, rain and count columns "
            f"agree exactly, and mean temperature differs by {V('t2m_diff')}{DEG}C because the "
            "two engines round halves differently. Verification found one real bug: the "
            f"sub-basin peak hour disagreed between host and cluster on {V('sub_bad')} of "
            f"{V('sub_rows')} rows, because weighted means differ in the last bits with the "
            "order of summation and turned ties into non-ties. Rainfall is now rounded to "
            f"{V('round_mm')} mm before the peak is located, and both platforms agree on all "
            f"rows. Run times are shown in Fig. {F['etl']} and discussed in Section V."),
          fig_drawing(etl_drawing(), "etl",
                      f"Run time of the hourly-to-daily ETL ({V('era5_rows')} rows). Bars: mean "
                      "of the runs; labels: minimum and maximum. Green: Polars; purple: Spark "
                      "local mode; orange: standalone cluster; grey: Spark on the host via "
                      "Arrow."),

          h2("C", "Hourly features: bit-identical results"),
          p(f"{TT}spark_hourly.py{TE} re-implements the {V('par_ncol')} hourly rainfall features "
            "of Report 3 (nine per sub-basin and for the whole basin). Compared cell by cell "
            f"with the Polars version using exact equality, no cell differs (Table {T['parity']}). "
            "Exactness needed three changes, because a difference of one unit in the last "
            "place can flip a threshold test: sums are accumulated sequentially in the Polars "
            f"order ({TT}aggregate{TE} over a sorted array instead of {TT}F.sum{TE}); the five "
            "sub-basins are added with the same bracketing as Polars; and the sine and cosine "
            "of the peak hour come from a table computed in Polars rather than from the JVM. "
            "Between Windows and Linux the C-library sine itself differs in the last place, in "
            "both engines; that difference is not caused by Spark."),
          tbl([["Source, where Spark ran", "Cells compared (hourly / daily)", "Differing cells",
                "Spark (s)", "Polars (s)"],
               ["ERA5, cluster (2 workers)", f"{V('par_nh_era5')} / {V('par_nd_era5')}", "0",
                V("par_sp_era5_c"), V("par_pl_era5_c")],
               ["ERA5, host local[8]", f"{V('par_nh_era5')} / {V('par_nd_era5')}", "0",
                V("par_sp_era5_w"), V("par_pl_era5_w")],
               ["PERSIANN-CCS, cluster", f"{V('par_nh_pccs')} / {V('par_nd_pccs')}", "0",
                V("par_sp_pccs_c"), V("par_pl_pccs_c")],
               ["PERSIANN-CCS, host local[8]", f"{V('par_nh_pccs')} / {V('par_nd_pccs')}", "0",
                V("par_sp_pccs_w"), V("par_pl_pccs_w")]],
              [1.08 * inch, 0.95 * inch, 0.5 * inch, 0.48 * inch, 0.48 * inch], "parity",
              f"SPARK AGAINST POLARS FOR THE {V('par_ncol')} HOURLY FEATURES: EXACT (BITWISE) "
              "COMPARISON, NO ROW ON ONE SIDE ONLY", small=True)]

    # ============================================================ III
    s += [h1("III", "Distributed Machine Learning with MLlib"),
          p(f"{TT}spark_train.py{TE} trains MLlib gradient-boosted trees (GBT) and random "
            f"forests (RF) on the {V('nfA')} predictors of the Report 2 panel (configuration A "
            "of Report 3), on log(1 + Q), one model per horizon, with the same temporal split "
            f"as LightGBM: training 2010&#8211;2015 ({V('ml_train_days')} days), validation to "
            f"June 2022 ({V('ml_valid_days')} days), refit on both ({V('ml_ntrain')} days) and a "
            f"single evaluation on the test period from July 2022 ({V('ml_ntest_lo')}&#8211;"
            f"{V('ml_ntest_hi')} days). Spark's {TT}CrossValidator{TE} and "
            f"{TT}TrainValidationSplit{TE} split rows at random, which lets a model see the "
            "future; they were replaced by a loop that fits each grid point on the training "
            f"years and scores it on the fixed validation period ({V('ml_gbt_grid')} GBT and "
            f"{V('ml_rf_grid')} RF settings, {V('ml_ngrid')} fits over three horizons)."),
          tbl([["Model", "NSE h=1", "h=2", "h=3", "Peak bias h=1", "h=2", "h=3"],
               ["LightGBM (Report 3, config. A)"] + [V(f"lgb_nse{h}") for h in (1, 2, 3)]
               + [V(f"lgb_pb{h}") for h in (1, 2, 3)],
               ["Spark GBT"] + [V(f"ml_gbt_NSE_{h}") for h in (1, 2, 3)]
               + [V(f"ml_gbt_peak_bias_{h}") for h in (1, 2, 3)],
               ["Spark RF"] + [V(f"ml_rf_NSE_{h}") for h in (1, 2, 3)]
               + [V(f"ml_rf_peak_bias_{h}") for h in (1, 2, 3)]],
              [1.1 * inch] + [0.4 * inch] * 3 + [0.46 * inch] + [0.4 * inch] * 2, "mllib",
              "MLLIB ON THE TWO-WORKER CLUSTER AGAINST LIGHTGBM, SAME PANEL AND SPLIT, TEST "
              "PERIOD FROM JULY 2022", small=True),
          p(f"LightGBM remains best one day ahead (Table {T['mllib']}): GBT is "
            f"{V('ml_gbt_delta_NSE_vs_lgbm_1')} and RF {V('ml_rf_delta_NSE_vs_lgbm_1')} NSE behind. "
            f"At h = 2 and 3 RF is ahead by {V('ml_rf_delta_NSE_vs_lgbm_2')} and "
            f"{V('ml_rf_delta_NSE_vs_lgbm_3')}, but on one split without a test of significance, "
            "and LightGBM used fixed hyperparameters while the MLlib models were tuned on "
            "validation; this is not evidence that the Spark models are better. All three "
            "cut flood peaks by a similar amount, so changing the engine does not remove the "
            "limitation of daily predictors. GBT chose the shallowest and slowest grid point "
            f"at every horizon (depth {V('gbt_depth')}, step {V('gbt_step')}, {V('gbt_iter')} "
            "iterations), which suggests extending the grid towards simpler models; RF chose "
            f"the deepest trees ({V('rf_depth')} levels, {V('rf_trees')} trees)."),
          p(f"<b>Engineering note.</b> In the first run both executors ({V('oom_mem')} MB) died "
            f"with exit code {V('oom_code')} while fitting RF, most likely because MLlib reserves "
            f"{V('oom_def')} MB of node statistics per task by default and four tasks per "
            f"executor exceeded its execution memory. Setting {TT}maxMemoryInMB{TE} to {V('rf_mem')} and the executor "
            f"memory to {V('ok_mem')} MB fixed it. The grid search and refits took "
            f"{V('ml_sec_tot')} s on {V('ml_cores')} cores in total ({rng('ml_gbt_sec')} s per "
            f"horizon for GBT, {rng('ml_rf_sec')} s for RF); a LightGBM fit of all three horizons "
            f"takes a median of {V('wf_med_lgb')} s on two threads (Section IV-D).")]

    # ============================================================ IV
    s += [h1("IV", "Deep Learning"),
          h2("A", "Models"),
          p("The LSTM [9] reads a window of L = 14 or 30 days of nine raw daily variables "
            "(discharge, rainfall per band and basin mean, antecedent precipitation index, "
            "season code, flood-season flag) instead of hand-made lag columns, and predicts "
            "log discharge at t + 1, t + 2 and t + 3 jointly, as in LSTM rainfall&#8211;runoff "
            "models [11]. Options are to predict the change from today's discharge and to use "
            "a peak-weighted loss (MSE weighted by discharge over its training mean, clipped). "
            "An MLP on the LightGBM lag columns is the deep-learning baseline. All models keep "
            "the LightGBM protocol: inputs standardised with training statistics only, early "
            "stopping on validation, then a refit on training plus validation for the selected "
            f"number of epochs. The reference LSTM (L = 30, MSE) has {V('n_params')} parameters "
            f"and {V('n_win')} training windows; {V('n_dlcfg')} configurations were run with "
            "three seeds each."),

          h2("B", "Distributed training through Spark"),
          p(f"The training function {TT}train(config){TE} is pure: it reads only its "
            "configuration and the panel path. When the world size exceeds one it starts a "
            "gloo process group, wraps the model in DDP and shards samples with a distributed "
            "sampler, so gradients are averaged across ranks after every batch [6]. It was run "
            "in four ways: a single process; TorchDistributor in local mode (torchrun on the "
            "driver); TorchDistributor on the cluster, which starts a barrier stage with one "
            "task per executor; and a barrier stage written for this project, in which each "
            "task obtains the address of task 0 from the barrier context, sets the rank and "
            f"world size and calls {TT}train(){TE} directly. The last path exists because "
            "TorchDistributor fails on Windows: torchrun builds its rendezvous store with "
            "libuv, which the Windows build of PyTorch lacks, and disabling it through the "
            f"documented environment variable does not help. Table {T['ddp']} lists the runs."),
          tbl([["Run (where)", "Proc. &#215; threads", "Global batch", "Best epoch",
                "train() (s)", "Wall (s)"]]
              + [[lab, px(f"{k}_pt"), V(f"{k}_gb"), V(f"{k}_ep"), rng(f"{k}_train"), rng(f"{k}_wall")]
                 for k, lab in (("w_single", "Single process (host)"),
                                ("w_barrier", "Barrier, local[2] (host)"),
                                ("w_barrier64", "Barrier, local[2] (host)"))]
              + [["TorchDistributor, local (host)", "2 &#215; 2", "&#8212;", "&#8212;",
                  "failed: no libuv", "&#8212;"]]
              + [[lab, px(f"{k}_pt"), V(f"{k}_gb"), V(f"{k}_ep"), rng(f"{k}_train"), rng(f"{k}_wall")]
                 for k, lab in (("d_single", "Single process (container)"),
                                ("d_tdlocal", "TorchDistributor, local mode (container)"),
                                ("c_td", "TorchDistributor, 2 workers (cluster)"),
                                ("c_td64", "TorchDistributor, 2 workers (cluster)"),
                                ("c_barrier", "Barrier, 2 workers (cluster)"))],
              [1.14 * inch, 0.45 * inch, 0.4 * inch, 0.36 * inch, 0.58 * inch, 0.58 * inch], "ddp",
              "DISTRIBUTED LSTM TRAINING (L = 30, MSE, SEED 42). TRAIN() = RANK 0 FROM DATA "
              "LOADING TO EVALUATION; WALL = CALL TO RESULT, SPARK SESSION START EXCLUDED; "
              "RANGES OVER REPEATED RUNS", small=True),
          p("Four results follow. (1) The single-process run reproduces seed 42 of the deep-"
            f"learning experiment exactly (NSE {V('d_single_nse1')}, {V('d_single_nse2')}, "
            f"{V('d_single_nse3')}) on the host and in the container. (2) With the same number "
            "of ranks and global batch, the result does not depend on how training is "
            f"distributed: all two-rank runs with batch 128 give {V('c_td_nse1')}, "
            f"{V('c_td_nse2')}, {V('c_td_nse3')} (with batch 64: {V('c_td64_nse1')}, "
            f"{V('c_td64_nse2')}, {V('c_td64_nse3')}); barrier mode and TorchDistributor are "
            "bit-identical on the cluster, and host and container agree to four decimals. "
            f"(3) DDP changes the learning curve, not the skill: {V('ddp_d1')}, {V('ddp_d2')} and "
            f"{V('ddp_d3')} NSE against the single process, within about one seed standard "
            f"deviation ({V('seed_sd1')}, {V('seed_sd2')}, {V('seed_sd3')}). (4) Distribution is "
            f"slower: on the cluster {TT}train(){TE} takes {rng('c_td_train')} s against "
            f"{rng('d_single_train')} s for one process, and TorchDistributor adds "
            f"{rng('ov_td')} s to start the barrier stage and torchrun ({rng('ov_bar')} s for the "
            "lighter barrier path). With a small model and a few dozen batches per epoch, "
            "synchronising gradients after every batch costs more than the split saves."),

          h2("C", "Deep learning against LightGBM"),
          NextPageTemplate(["wide_dl", "*", "rest"]),
          p(f"On the single split some of the {V('n_dlcfg')} configurations beat LightGBM at "
            f"h = 2 and 3 (Fig. {F['dlsplit']}; best: a peak-weighted MLP, {V('dlmlp2')} against "
            f"{V('lgb_nse2')} at h = 2), but the LSTM selected on validation lost at all three "
            f"horizons ({V('dlsel1')}, {V('dlsel2')}, {V('dlsel3')} against {V('lgb_nse1')}, "
            f"{V('lgb_nse2')}, {V('lgb_nse3')}); the better configurations were identified only "
            f"after seeing the test set. Under the {V('wf_nfold')}-fold yearly walk-forward of "
            f"Report 3 (Table {T['wf']}, Fig. {F['wfdl']}) no deep model beats LightGBM "
            f"consistently. The LSTM with MSE loss is level at h = 1 ({V('lstmM1_m')}, interval "
            "includes zero) and slightly worse at h = 2&#8211;3; the peak-weighted LSTM loses "
            f"clearly at h = 3 ({V('lstmP3_m')}, p = {V('lstmP3_p')}). The single-split "
            "advantage at h = 2&#8211;3 appears only in 2022&#8211;2025, the years that split "
            "happened to test; in 2013&#8211;2021 every deep model loses on average at h = 2 "
            "and 3."),
          tbl([["Model", "h = 1", "h = 2", "h = 3", "CSI level 1, h = 1"],
               ["LightGBM (NSE)", V("dl_lgb1"), V("dl_lgb2"), V("dl_lgb3"), V("csi_lgb")]]
              + [[name] + [f"{V(t + str(h) + '_m')}<br/>{V(t + str(h) + '_ci')}<br/>"
                           f"{V(t + str(h) + '_wl')}" for h in (1, 2, 3)] + [V(c)]
                 for t, name, c in (("lstmM", "LSTM L=30, MSE", "csi_lstmM"),
                                    ("lstmP", "LSTM L=30, peak-weighted", "csi_lstmP"),
                                    ("mlpP", "MLP on lags, peak-weighted", "csi_mlpP"))],
              [0.98 * inch, 0.72 * inch, 0.72 * inch, 0.72 * inch, 0.38 * inch], "wf",
              f"DEEP LEARNING AGAINST LIGHTGBM, {V('wf_nfold')} YEARLY FOLDS 2013&#8211;2025: "
              f"{DELTA}NSE MEAN, 95% BOOTSTRAP INTERVAL, FOLDS WON/LOST; POOLED CSI", small=True),
          p("Deep learning has two genuine strengths one day ahead: it detects more level-1 "
            f"flood days (POD {V('pod_lstmM')}&#8211;{V('pod_mlpP')} against {V('pod_lgb')}; "
            f"pooled CSI {V('csi_lstmM')} against {V('csi_lgb')}) and cuts peaks less (peak bias "
            f"{V('pb_mlpP')} to {V('pb_lstmP')} against {V('pb_lgb')}). It is also far less "
            f"stable: the seed-to-seed spread is {V('sd_dl_lo')}&#8211;{V('sd_dl_hi')} NSE "
            f"against at most {V('sd_lgb')} for LightGBM, and the torch thread count moves the "
            f"MLP by up to {V('thr_rng')} while leaving the LSTM unchanged. LightGBM remains the "
            "main model; the deep models are candidates for a detection-oriented ensemble."),

          h2("D", "Where parallelism pays: independent fits"),
          p(f"The walk-forward needed {V('wf_nfit')} independent fits (four models, fourteen "
            f"test years including the partial year 2026, three seeds), {V('wf_sec')} s if run "
            f"one after another. A median LSTM fit takes {V('wf_med_lstm_lo')}&#8211;"
            f"{V('wf_med_lstm_hi')} s, against {V('wf_med_lgb')} s for LightGBM and "
            f"{V('wf_med_mlp')} s for the MLP. Because the fits share nothing, they were spread "
            f"over a local pool of {V('wf_procs')} processes with two threads each and finished "
            f"in about {V('wf_min')} minutes. This task parallelism, not data-parallel DDP, is "
            "what shortened the experiments; it maps directly onto Spark (one task per fold, "
            "seed and configuration), which has not yet been implemented.")]

    # ============================================================ V
    s += [h1("V", "Scaling and Honest Assessment"),
          h2("A", "Measured cost"),
          p(f"At this data size Spark is slower than Polars (Fig. {F['etl']}). For the ETL, the "
            f"two-worker cluster takes {V('x_c2_wpol')} times as long as Polars on the host, "
            f"and Spark on the host through Arrow {V('x_arrow_wpol')} times; inside the same "
            f"container, with the same mounted disk, the best Spark run is {V('x_dl8_dpol')} "
            f"times slower than Polars. For the hourly features the ratio is {V('x_par_c')} on "
            f"the cluster and {V('x_par_w')} on the host (Table {T['parity']}). Parallelism does "
            f"work inside Spark: one to four cores speeds the ETL up {V('spd_cl')} times on the "
            f"cluster and {V('spd_loc')} times in local mode. Going from four cores on one "
            f"worker to eight on two does not ({rng('etl_cluster_1w_4c')} s against "
            f"{rng('etl_cluster_2w_8c')} s), and distributed LSTM training is slower than one "
            "process (Section IV-B)."),
          h2("B", "Why"),
          *bullets([
              f"<b>I/O through the mount.</b> Reading the {V('era5_files')} files from the "
              f"Windows disk into Docker alone takes {V('mnt_1c_lo')}&#8211;{V('mnt_1c_hi')} s "
              f"with one core and {V('mnt_8c_lo')}&#8211;{V('mnt_8c_hi')} s with eight, "
              f"{V('mnt_pct_lo')}&#8211;{V('mnt_pct_hi')}% of the ETL time; Polars on the host "
              f"reads the same files natively and is {V('x_dpol_wpol')} times faster than "
              "Polars in the container.",
              f"<b>Skewed partitions.</b> Only {V('era5_cells')} cell keys are hashed into "
              f"{V('n_part')} partitions; the largest holds {V('part_max')} rows, "
              f"{V('part_ratio')} times the mean of {V('part_mean')}, and the slowest task "
              "sets the time of the whole stage.",
              "<b>One physical machine.</b> Both workers share the host's cores, memory bus "
              "and disk, so adding a worker adds scheduling and shuffling, not capacity.",
              f"<b>Fixed costs.</b> Starting a Spark application takes {rng('start_dock')} s in "
              f"the containers and {V('start_win')} s on the host, before any data are read; "
              "task scheduling and shuffles add more. For two months of PERSIANN-CCS Polars "
              f"needs {V('par_pl_pccs_c')} s and Spark {V('par_sp_pccs_c')}&#8211;"
              f"{V('par_sp_pccs_w')} s.",
              f"<b>Small model.</b> With {V('n_params')} parameters and {V('n_win')} training "
              "windows, per-batch gradient synchronisation dominates DDP.",
          ]),
          p("This is the COST argument [4]: a distributed system should first be compared "
            "with a competent single-threaded implementation, and for data that fit in memory "
            "the single machine usually wins. Run times were measured while other jobs shared "
            "the machine and vary by a few percent; this does not change the ratios."),
          h2("C", "When Spark would pay off"),
          p("Spark becomes the right tool when the data no longer fit in one machine's memory "
            "or already live in distributed storage. Plausible extensions of this project "
            "reach that point: forecasting many river cells across Vietnam instead of one; "
            f"PERSIANN-CCS at {V('grid_pccs')}{DEG} for its full record, about "
            f"{V('pccs_full')} million rows for this basin alone (an estimate, which one machine "
            "with Polars would still handle); and an hourly-input LSTM reading "
            f"{V('h_steps')} hourly steps of {V('era5_cells')} cells per sample, in the spirit "
            "of multi-timescale LSTMs [12]. The most immediate gain is the task parallelism of "
            "Section IV-D: walk-forward folds, seeds and hyperparameter grids as independent "
            "Spark tasks on several real machines."),
          h2("D", "Path to the cloud (proposal, not executed)"),
          p("The code is already portable: the Spark session reads the master address from "
            "an environment variable, the training function takes the panel path as a "
            "parameter, and TorchDistributor runs unmodified on Linux. A managed workspace "
            "such as Databricks Free Edition [13] could host the same jobs with Parquet "
            "replaced by Delta tables [8]. This step has not been run, and no result in this "
            "report comes from it; the free tier's limits on compute size and on installing "
            "PyTorch must be checked first.")]

    # ============================================================ VI
    s += [h1("VI", "Conclusion"),
          p("The project's pipeline now runs on a Spark cluster and gives the same answers as "
            "the single-machine version: the ETL row for row and the hourly features bit for "
            f"bit. MLlib models trained on the cluster do not beat LightGBM one day ahead "
            f"(NSE {V('ml_gbt_NSE_1')} and {V('ml_rf_NSE_1')} against {V('lgb_nse1')}). LSTM "
            "training distributed through TorchDistributor or a barrier stage reproduces the "
            "same result on one machine and on two workers, and across "
            f"{V('wf_nfold')} yearly folds no deep model beats LightGBM consistently, although "
            "deep models detect more flood days. At the present size of the data Spark is "
            "slower than Polars and DDP is slower than one process, for reasons that were "
            "measured. The recommendation is therefore to keep Polars and LightGBM for the "
            "daily forecast, keep the tested Spark jobs as the path for larger inputs, and "
            "use Spark next where it helps immediately: running walk-forward folds and seeds "
            "as parallel tasks on more than one physical machine.")]

    # ============================================================ refs
    s += [p("REFERENCES", "h1")]
    refs = [
        "[1] S. Harrigan <i>et al.</i>, &#8220;Daily ensemble river discharge reforecasts and "
        "real-time forecasts from the operational Global Flood Awareness System,&#8221; "
        "<i>Hydrol. Earth Syst. Sci.</i>, vol. 27, no. 1, pp. 1&#8211;19, 2023.",
        "[2] H. Hersbach <i>et al.</i>, &#8220;The ERA5 global reanalysis,&#8221; <i>Q. J. R. "
        "Meteorol. Soc.</i>, vol. 146, no. 730, pp. 1999&#8211;2049, 2020.",
        "[3] M. Zaharia <i>et al.</i>, &#8220;Apache Spark: A unified engine for big data "
        "processing,&#8221; <i>Commun. ACM</i>, vol. 59, no. 11, pp. 56&#8211;65, 2016.",
        "[4] F. McSherry, M. Isard and D. G. Murray, &#8220;Scalability! But at what "
        "COST?,&#8221; in <i>Proc. 15th Workshop Hot Topics Oper. Syst. (HotOS XV)</i>, 2015.",
        "[5] X. Meng <i>et al.</i>, &#8220;MLlib: Machine learning in Apache Spark,&#8221; "
        "<i>J. Mach. Learn. Res.</i>, vol. 17, no. 34, pp. 1&#8211;7, 2016.",
        "[6] S. Li <i>et al.</i>, &#8220;PyTorch distributed: Experiences on accelerating data "
        "parallel training,&#8221; <i>Proc. VLDB Endow.</i>, vol. 13, no. 12, "
        "pp. 3005&#8211;3018, 2020.",
        "[7] Apache Software Foundation, &#8220;pyspark.ml.torch.distributor.TorchDistributor,"
        "&#8221; PySpark documentation. [Online]. Available: https://spark.apache.org/docs/"
        "latest/api/python/reference/api/pyspark.ml.torch.distributor.TorchDistributor.html",
        "[8] M. Armbrust <i>et al.</i>, &#8220;Delta Lake: High-performance ACID table storage "
        "over cloud object stores,&#8221; <i>Proc. VLDB Endow.</i>, vol. 13, no. 12, "
        "pp. 3411&#8211;3424, 2020.",
        "[9] S. Hochreiter and J. Schmidhuber, &#8220;Long short-term memory,&#8221; "
        "<i>Neural Comput.</i>, vol. 9, no. 8, pp. 1735&#8211;1780, 1997.",
        "[10] G. Ke <i>et al.</i>, &#8220;LightGBM: A highly efficient gradient boosting "
        "decision tree,&#8221; in <i>Adv. Neural Inf. Process. Syst.</i>, vol. 30, 2017, "
        "pp. 3146&#8211;3154.",
        "[11] F. Kratzert, D. Klotz, C. Brenner, K. Schulz and M. Herrnegger, "
        "&#8220;Rainfall&#8211;runoff modelling using Long Short-Term Memory (LSTM) "
        "networks,&#8221; <i>Hydrol. Earth Syst. Sci.</i>, vol. 22, no. 11, "
        "pp. 6005&#8211;6022, 2018.",
        "[12] M. Gauch, F. Kratzert, D. Klotz, G. Nearing, J. Lin and S. Hochreiter, "
        "&#8220;Rainfall&#8211;runoff prediction at multiple timescales with a single Long "
        "Short-Term Memory network,&#8221; <i>Hydrol. Earth Syst. Sci.</i>, vol. 25, no. 4, "
        "pp. 2045&#8211;2062, 2021.",
        "[13] Databricks, &#8220;Databricks Free Edition,&#8221; documentation. [Online]. "
        "Available: https://docs.databricks.com/aws/en/getting-started/free-edition",
    ]
    s += [p(r, "ref") for r in refs]
    return s


# ================================================================== bố cục
def build() -> int:
    fx.load(cfg)
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
        canvas.drawString(LM, BM - 26, "DSP391m - Data Science Project - Report 4")
        canvas.drawRightString(PW - RM, BM - 26, "FPT University, Fall 2026")
        canvas.restoreState()

    wide_caps: list[Paragraph] = []

    def wide(tid: str, figs: list[tuple[ImageReader, str, str]]) -> PageTemplate:
        """Một hay nhiều hình rộng hai cột xếp chồng ở đầu trang (figure* của IEEE)."""
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

    head = [
        p("Distributed Processing and Deep Learning for One-to-Three-Day Discharge "
          "Forecasting of the Huong River at Kim Long", "title"),
        p(("&nbsp;" * 4).join(cfg.TEAM_ASCII), "author"),
        Spacer(1, 3),
        p("Department of Information Technology, FPT University<br/>"
          "DSP391m &#8212; Data Science Project &#8212; Fall 2026<br/>Hue, Vietnam", "affil"),
        Spacer(1, 9),
        Paragraph(
            "<b><i>Abstract</i></b>&#8212;<font size=9>The lecturer's review of this project "
            "asked for distributed data processing, model training with Apache Spark and, "
            "preferably, deep learning. This report moves the pipeline of a daily discharge "
            "forecast for the Huong River at Kim Long, Vietnam, onto a Spark standalone "
            f"cluster (one master, {V('n_workers')} workers, Spark {V('spark_ver')} on Docker) "
            "and evaluates neural forecasters under the protocol used for the gradient-boosting "
            f"model. The cluster turns {V('era5_rows')} hourly ERA5 rows into daily rainfall "
            "indices with the same result as a single-machine Polars pipeline, and the "
            f"{V('par_ncol')} hourly rainfall features agree bit for bit. MLlib gradient-boosted "
            f"trees and random forests reach NSE {V('ml_gbt_NSE_1')} and {V('ml_rf_NSE_1')} one "
            f"day ahead, against {V('lgb_nse1')} for LightGBM. An LSTM trained with PyTorch DDP "
            "through TorchDistributor or a Spark barrier stage gives the same result on one "
            f"machine and on two workers. Across {V('wf_nfold')} yearly walk-forward folds no "
            "LSTM or MLP beats LightGBM consistently, although they detect more flood days. "
            f"At this data size the two-worker ETL takes {V('x_c2_wpol')} times as long as Polars on "
            "one machine, and "
            "distributed training is slower than one process; we measure why and identify "
            "where Spark would pay off.</font>",
            ST["abstext"]),
        Paragraph(
            "<b><i>Keywords</i></b>&#8212;<font size=9>Apache Spark, MLlib, distributed deep "
            "learning, LSTM, TorchDistributor, scalability, flood forecasting, Huong "
            "River</font>", ST["keywords"]),
    ]
    head_h = sum(fl.wrap(W, PH)[1] + fl.getSpaceBefore() + fl.getSpaceAfter() for fl in head) + 8

    doc = BaseDocTemplate(str(OUT), pagesize=(PW, PH), leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM,
                          title="DSP391m Report 4 - Distributed Processing and Deep Learning",
                          author=", ".join(cfg.TEAM_ASCII))
    doc.addPageTemplates([
        PageTemplate(id="first", onPage=footer, frames=[
            fr(LM, PH - TM - head_h, W, head_h, "head"),
            fr(LM, BM, COLW, avail_h - head_h, "c1l"),
            fr(LM + COLW + GUT, BM, COLW, avail_h - head_h, "c1r")]),
        PageTemplate(id="rest", onPage=footer, frames=[
            fr(LM, BM, COLW, avail_h, "cl"),
            fr(LM + COLW + GUT, BM, COLW, avail_h, "cr")]),
        wide("wide_dl", [(crop_dlsplit(), "dlsplit",
             f"Single split (test from July 2022, refit on train plus validation): NSE of the "
             f"{V('n_dlcfg')} deep-learning configurations, mean and standard deviation over "
             "three seeds; the vertical line is LightGBM. Only the LSTM on all panel columns "
             "was selected on validation; the others are shown for completeness."),
            (full_wfdl(), "wfdl",
             f"Deep learning against LightGBM under the yearly walk-forward (panel from 2010, "
             f"3-day gap). Top: NSE per test year; bottom: {DELTA}NSE, positive when the deep "
             "model is better. Shaded: GloFAS regime change (07/2022); hollow markers: "
             "January&#8211;August 2026, excluded from the summary. The grey band is the "
             "largest change caused by the torch thread count.")]),
    ])

    body = r3.no_orphans(story())
    n_num = r3.check_text(head + body + wide_caps)
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
    o = {k: v for k, v in V.val.items()}

    def r(key: str) -> str:
        lo, hi = o[f"{key}_lo"], o[f"{key}_hi"]
        return lo if lo == hi else f"{lo}–{hi}"

    lines = f"""DÀN Ý REPORT 4 — XỬ LÝ PHÂN TÁN (SPARK) & DEEP LEARNING (IEEE, {n_pages} trang)
File: reports/report4/DSP391m_Report4_Distributed_DL_IEEE.pdf
Build: PYTHONIOENCODING=utf-8 python reports/report4/build_report.py   (mọi số kiểm với CSV/cấu hình lúc build)

Câu định vị: thầy yêu cầu "dữ liệu phân tán, dùng Spark train ML, tốt hơn nữa là DL". Nhóm đã làm
THẬT trên cụm Spark và đo THẬT; kết luận trung thực: ở quy mô này Spark chậm hơn Polars, DL không
thắng LightGBM — nhưng pipeline phân tán cho kết quả TRÙNG bản một máy.

I. GIỚI THIỆU
 - Nhắc bài toán (GloFAS v4, Kim Long, 1–3 ngày). Mô hình chính Report 3: LightGBM cấu hình E
   NSE {o['abE1']} / {o['abE2']} / {o['abE3']}.
 - Quy mô thật (Bảng I): ERA5 giờ {o['era5_rows']} dòng ({o['era5_cells']} ô, 2015–08/2026, {o['era5_mb']} MB);
   IMERG {o['rows_imerg']} + GSMaP {o['rows_gsmap']} = {o['sat_mrows']} triệu dòng ({o['sat_cells']} ô, 1998–10/2026, {o['sat_mb']} MB);
   PERSIANN-CCS {o['rows_pccs']} dòng (2 tháng thử). Dữ liệu NHỎ tính theo byte → câu hỏi đúng là
   "pipeline có đúng khi tách executor không" và "so với một máy tốt thì sao" (lập luận COST [4]).

II. KIẾN TRÚC PHÂN TÁN
 A. Cụm Spark standalone trên Docker: 1 master + {o['n_workers']} worker × {o['w_cores']} lõi × {o['w_mem']} GB, Spark {o['spark_ver']},
    Java {o['java_ver']}, torch {o['torch_ver']} CPU. Repo mount /opt/repo ở cả 3 container = thay HDFS/S3/Delta.
    Một máy vật lý ({o['host_cores']} lõi, {o['host_ram']} GB; Docker {o['docker_ram']} GB) → phân tán về GIAO THỨC, không thêm phần cứng.
    Windows thiếu winutils → trên máy host đi đường vòng Arrow (chỉ cho test).
 B. ETL giờ → ngày: {o['era5_files']} file, {o['era5_rows']} → {o['era5_out']} ô×ngày ({o['era5_days']} ngày); lưu vực con {o['sub_rows']} dòng.
    Trùng Polars (t2m lệch {o['t2m_diff']} °C do làm tròn). Lỗi thật đã sửa: peak_hour lưu vực con lệch {o['sub_bad']}/{o['sub_rows']} dòng
    giữa Windows và cụm → làm tròn mưa trước khi tìm giờ đỉnh.
 C. {o['par_ncol']} đặc trưng giờ: Spark = Polars TỪNG BIT (Bảng II; ERA5 {o['par_nh_era5']} ô giờ / {o['par_nd_era5']} ô ngày).
    Ba mẹo: cộng tuần tự đúng thứ tự Polars; cộng 5 lưu vực con cùng cách đóng ngoặc; sin/cos giờ đỉnh lấy từ bảng Polars.

III. ML PHÂN TÁN (MLlib) — Bảng III
 - GBT/RF trên {o['nfA']} cột panel Report 2, split thời gian như LightGBM; KHÔNG dùng CrossValidator
   (chia ngẫu nhiên → rò rỉ tương lai) → vòng lặp chọn tham số trên valid cố định ({o['ml_ngrid']} lần fit).
 - NSE h1: GBT {o['ml_gbt_NSE_1']}, RF {o['ml_rf_NSE_1']} vs LightGBM {o['lgb_nse1']}. h2/h3 RF nhỉnh ({o['ml_rf_delta_NSE_vs_lgbm_2']} / {o['ml_rf_delta_NSE_vs_lgbm_3']})
   nhưng 1 lần chia, chưa kiểm định, LightGBM không tinh chỉnh → KHÔNG nói Spark tốt hơn.
 - Bài học kỹ thuật: executor {o['oom_mem']} MB chết (exit {o['oom_code']}) → maxMemoryInMB {o['rf_mem']} + executor {o['ok_mem']} MB.
   Tổng {o['ml_sec_tot']} s trên {o['ml_cores']} lõi.

IV. DEEP LEARNING
 A. LSTM (cửa sổ 14/30 ngày, 9 biến gốc, 3 đầu ra), tuỳ chọn dự báo phần dư, loss nhấn đỉnh; MLP trên cột lag.
    LSTM L30: {o['n_params']} tham số, {o['n_win']} cửa sổ train; {o['n_dlcfg']} cấu hình × 3 seed.
 B. DDP (gloo) qua TorchDistributor (local + cụm) và barrier tự viết (Bảng IV). TorchDistributor HỎNG trên
    Windows (torch Windows không có libuv) → barrier. Kết quả:
    (1) 1 tiến trình tái lập đúng seed 42 ({o['d_single_nse1']} / {o['d_single_nse2']} / {o['d_single_nse3']});
    (2) cùng số rank + batch → cùng NSE bất kể cách phân tán ({o['c_td_nse1']} / {o['c_td_nse2']} / {o['c_td_nse3']}); barrier = TD từng bit trên cụm;
    (3) DDP lệch {o['ddp_d1']} / {o['ddp_d2']} / {o['ddp_d3']} so với 1 tiến trình ≈ 1 sd giữa seed ({o['seed_sd1']} / {o['seed_sd2']} / {o['seed_sd3']});
    (4) CHẬM hơn: train() {r('c_td_train')} s vs {r('d_single_train')} s; TorchDistributor tốn thêm {r('ov_td')} s khởi động.
 C. DL vs LightGBM: một lần chia có cấu hình hơn ở h2–h3 (MLP nhấn đỉnh {o['dlmlp2']}) nhưng LSTM chọn theo valid THUA cả 3 horizon.
    Walk-forward {o['wf_nfold']} fold (Bảng V, Hình 4): không DL nào hơn vững; LSTM nhấn đỉnh thua rõ h3 ({o['lstmP3_m']}, p {o['lstmP3_p']}).
    Mặt được: POD/CSI h1 cao hơn (CSI {o['csi_lstmM']} vs {o['csi_lgb']}), ít cắt ngọn hơn. Giữ LightGBM.
 D. Song song có lợi THẬT là song song theo TÁC VỤ: {o['wf_nfit']} lần fit độc lập, {o['wf_sec']} s nếu chạy nối tiếp;
    pool {o['wf_procs']} tiến trình → ~{o['wf_min']} phút. Chưa chuyển sang Spark (đề xuất).

V. QUY MÔ & ĐÁNH GIÁ TRUNG THỰC
 A. ETL: cụm 2 worker chậm {o['x_c2_wpol']} lần Polars trên host; Spark host qua Arrow {o['x_arrow_wpol']} lần; cùng container {o['x_dl8_dpol']} lần.
    Đặc trưng giờ: {o['x_par_c']} lần (cụm), {o['x_par_w']} lần (host). 1→4 lõi nhanh {o['spd_cl']} lần; 4→8 lõi / 1→2 worker KHÔNG nhanh thêm.
 B. Vì sao: đọc qua ổ mount ({o['mnt_1c_lo']}–{o['mnt_1c_hi']} s / {o['mnt_8c_lo']}–{o['mnt_8c_hi']} s); phân hoạch lệch ({o['era5_cells']} khoá → {o['n_part']} phân hoạch,
    lớn nhất gấp {o['part_ratio']} lần TB); một máy vật lý; chi phí cố định (khởi động {r('start_dock')} s); mô hình DL nhỏ.
 C. Khi nào Spark có lợi: dữ liệu vượt RAM một máy / nằm sẵn trên kho phân tán (nhiều ô sông toàn quốc;
    PERSIANN-CCS đủ chuỗi ~{o['pccs_full']} triệu dòng — vẫn vừa một máy; LSTM giờ {o['h_steps']} bước × {o['era5_cells']} ô); song song fold/seed.
 D. Lên cloud: Databricks Free Edition CHỈ LÀ ĐỀ XUẤT, CHƯA CHẠY, không có số nào từ đó.

VI. KẾT LUẬN: pipeline phân tán ĐÚNG; MLlib không hơn LightGBM; DL không thắng vững; Spark chậm hơn ở quy mô
    này vì lý do đã đo. Khuyến nghị: Polars + LightGBM cho job hằng ngày; giữ job Spark đã kiểm cho dữ liệu lớn;
    bước tiếp: chạy walk-forward song song theo tác vụ trên nhiều máy thật.

CÂU HỎI DỄ BỊ HỎI — trả lời ngắn
 - "Sao dùng Spark mà chậm hơn?" → dữ liệu {o['era5_mb']}+{o['sat_mb']} MB vừa RAM; đo được nguyên nhân (ổ mount, lệch
   phân hoạch, 1 máy, chi phí cố định). Mục tiêu là chứng minh ĐÚNG khi phân tán + biết KHI NÀO đáng dùng.
 - "Phân tán thật không?" → thật về giao thức (2 executor trên 2 container, barrier, gloo qua mạng),
   không thêm phần cứng vì cùng một máy.
 - "Sao không dùng CrossValidator?" → chia ngẫu nhiên, mô hình nhìn thấy tương lai.
 - "DL có tốt hơn không?" → không vững qua {o['wf_nfold']} năm; bắt sự kiện tốt hơn nhưng kém ổn định.
 - "Databricks?" → đề xuất, chưa chạy.

CHỖ NHÓM CẦN KIỂM LẠI TRƯỚC KHI NỘP
 - Số chỉ có trong tài liệu (loại doc bên dưới), nhất là nguyên nhân chậm (ổ mount, phân hoạch lệch) và
   lỗi OOM của MLlib: chỉ có trong infra/spark/README.md, không có CSV.
 - Tổng thời gian MLlib: PDF in {o['ml_sec_tot']} s = tổng cột seconds_total của reports/spark_results.csv;
   infra/spark/README.md ghi 1 706 s (có thể gồm khởi động) — thống nhất cách ghi.
 - README ghi thời gian Spark đặc trưng giờ trên cụm "33,2; 28,7" s; CSV chỉ còn lần cuối ({o['par_sp_era5_c']} s) → PDF dùng CSV.
 - Kích thước dữ liệu tính theo 10^6 byte ({o['era5_mb']} MB ERA5); tài liệu cũ ghi "74 MB" (du, MiB) — cùng một dữ liệu.
 - Tài liệu tham khảo [7] (TorchDistributor) và [13] (Databricks Free Edition): kiểm lại URL.
 - Phần "khi nào Spark có lợi" và "lên cloud" là ĐỀ XUẤT, không có thí nghiệm.
"""
    rows = ["", "=" * 100, "DANH SÁCH SỐ DÙNG TRONG BÁO CÁO (sinh tự động lúc build)",
            "loại: csv = đã kiểm với file lúc build · claim = câu định tính đã kiểm · doc = chỉ có trong tài liệu",
            "=" * 100]
    for k in V.val:
        mark = "" if k in V.used or V.kind[k] == "claim" else "  [không in trong PDF]"
        rows.append(f"{V.kind[k]:<6} {k:<34} {V.val[k]:<26} {V.src[k]}{mark}")
    docs = [k for k in V.val if V.kind[k] == "doc" and k in V.used]
    rows += ["", f"SỐ CHỈ CÓ TRONG TÀI LIỆU, CÓ IN TRONG PDF ({len(docs)}) — nhóm kiểm lại:"]
    rows += [f" - {k} = {V.val[k]}  ({V.src[k]})" for k in docs]
    rows += ["", "CẢNH BÁO LẦN BUILD NÀY:"] + ([f" - {w}" for w in WARN] or [" (không có)"])
    OUTLINE.write_text(lines + "\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(build())
