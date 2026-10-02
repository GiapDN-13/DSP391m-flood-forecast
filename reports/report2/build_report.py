"""Sinh Report 2 (Data Collection · Cleaning · EDA) theo định dạng IEEE hai cột.

    EDA_LANG=en python -m src.eval.eda      # sinh hình nhãn tiếng Anh trước
    python reports/report2/build_report.py

Dùng lại kiểu chữ và helper của Report 1 để hai báo cáo cùng một bộ mặt.

Hai lớp bảo vệ, vì lỗi ở báo cáo nộp đi là lỗi đắt nhất:

1. **Số liệu đối chiếu với CSV lúc build.** Mọi con số chính trong văn bản được
   kiểm lại với `reports/*.csv`. Chạy lại EDA mà số đổi thì build **hỏng**, thay
   vì âm thầm in số cũ.
2. **Ký tự ngoài bảng mã của font Times.** Font chuẩn của PDF chỉ vẽ được bảng
   mã WinAnsi; ký tự như ≥, ≈, →, chữ tiếng Việt có dấu sẽ thành ô đen. Build
   **hỏng** nếu gặp, kèm vị trí.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as cfg  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "report1", ROOT / "reports" / "report1" / "build_report.py")
r1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r1)
p, bullets, h1, table, ST = r1.p, r1.bullets, r1.h1, r1.table, r1.ST
COLW, LM, RM, TM, BM, GUT, PW, PH = r1.COLW, r1.LM, r1.RM, r1.TM, r1.BM, r1.GUT, r1.PW, r1.PH

OUT = ROOT / "reports" / "report2" / "DSP391m_Report2_Data_EDA_IEEE.pdf"

# Ô bảng hẹp mà căn đều thì chữ giãn rất xấu — căn trái cho Report 2.
# Chỉ đổi trên bản module nạp riêng, không đụng Report 1.
from reportlab.lib.enums import TA_LEFT  # noqa: E402

ST["tabcell"].alignment = TA_LEFT
REP = ROOT / "reports"


def h2(letter: str, text: str):
    return p(f"{letter}.&nbsp;&nbsp;{text}", "h2")


def fig(name: str, no: int, caption: str):
    # Hình nhãn tiếng Anh; thiếu thì dừng hẳn chứ không chèn bản tiếng Việt.
    f = f"{name}_en.png"
    if not (r1.FIGS / f).exists():
        raise SystemExit(f"Thiếu {f}. Chạy trước:  EDA_LANG=en python -m src.eval.eda")
    return r1.figure(f, no, caption)


# ------------------------------------------------------------- đối chiếu số
def check_numbers() -> None:
    """Số trong văn bản phải khớp CSV. Lệch là dừng."""
    eda = pd.read_csv(REP / "eda_summary.csv")
    v = dict(zip(eda["chi_tieu"], eda["gia_tri"].astype(str)))
    expect = {
        "số ngày": "6087",
        "hệ số bất đối xứng": "5.91",
        "Q cực đại (m³/s)": "3588.2",
        "tỉ lệ dòng chảy tháng 9–12 (%)": "58.6",
        "r tại lag đó · cả năm": "0.789",
        "r(mưa 1 ngày, Q)": "0.642",
        "r(mưa 3 ngày, Q)": "0.863",
        "tỉ số ẩm/khô": "6.89",
        "số ngày ≥ phân vị 99.0%": "61",
    }
    bad = [f"  {k}: văn bản {e}, CSV {v.get(k)}" for k, e in expect.items()
           if v.get(k) != e]
    rk = pd.read_csv(REP / "risk_levels.csv").set_index("muc")
    if int(rk.loc["nguy_co_1", "n_test_luy_ke"]) != 31:
        bad.append("  risk level 1 test positives != 31")
    if bad:
        raise SystemExit("Số trong báo cáo lệch với dữ liệu — sửa văn bản trước khi build:\n"
                         + "\n".join(bad))
    print(f"Đối chiếu số: {len(expect) + 1} giá trị khớp CSV")


# --------------------------------------------------------- kiểm ký tự font
ALLOWED = set(range(32, 127)) | {
    0xA0, 0xB0, 0xB1, 0xB2, 0xB3, 0xB5, 0xB7, 0xD7,          # nbsp ° ± ² ³ µ · ×
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022,  # – — ‘ ’ “ ” •
}


def check_glyphs(flowables) -> None:
    probs = []
    for fl in flowables:
        txt = getattr(fl, "text", None)
        if not txt:
            continue
        plain = re.sub(r"<[^>]+>", "", txt)
        plain = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), plain)
        plain = plain.replace("&nbsp;", " ").replace("&amp;", "&") \
                     .replace("&lt;", "<").replace("&gt;", ">")
        for ch in set(plain):
            if ord(ch) not in ALLOWED:
                i = plain.index(ch)
                probs.append(f"  U+{ord(ch):04X} '{ch}' … {plain[max(0, i-30):i+30]!r}")
    if probs:
        raise SystemExit("Ký tự font Times không vẽ được (sẽ thành ô đen):\n"
                         + "\n".join(sorted(set(probs))[:20]))


# ------------------------------------------------------------------ nội dung
def story() -> list:
    s: list = []

    # ============================================================ I
    s += [h1("I", "Introduction"),
          p("Report 1 proposed forecasting river discharge in the Huong River basin "
            "one to three days ahead using only open data. This report covers the three "
            "data stages required before any model is trusted: how the data were "
            "collected, how they were cleaned, and what exploratory analysis reveals "
            "about the basin. The emphasis throughout is on <i>verification</i>: several "
            "properties of the open data that were assumed in Report 1 turned out to be "
            "false when measured, and those findings change the design of the later "
            "modelling work. They are reported here rather than hidden, and Section VI "
            "lists every correction to Report 1 explicitly.")]

    # ============================================================ II
    s += [h1("II", "Data Collection"),
          h2("A", "Sources"),
          p("All data come from public endpoints that require no API key, which removes "
            "the risk of losing access mid-semester. Table I lists the sources. Every "
            "endpoint was queried directly and its actual coverage measured, because "
            "documented coverage and delivered coverage differ for two of them."),
          table([
              ["Source / endpoint", "Variable", "Resolution", "Usable period"],
              ["GloFAS v4 via Open-Meteo Flood API [1], [2]", "river discharge",
               "~5 km, daily", "1997&#8211;2026 (1984&#8211;1996 empty)"],
              ["ERA5 via Open-Meteo Archive API [3]", "precipitation, temperature",
               "0.1&#176; grid, daily + hourly", "2010&#8211;2026 daily; 2015&#8211;2026 hourly"],
              ["Open-Meteo Historical Forecast API", "archived forecast rain",
               "as above", "identical to ERA5 &#8212; not usable"],
              ["Open-Meteo Marine API", "sea level (tide proxy)", "hourly, one point",
               "2023&#8211;2026 only"],
              ["Peer-reviewed paper and news archive [5]", "19 published flood peaks",
               "event", "1983&#8211;2025"],
              ["Decision 05/2020/QD-TTg [4]", "official alert stages", "station", "in force since 2020"],
          ], [1.15 * inch, 0.82 * inch, 0.72 * inch, 0.85 * inch], "I",
              "DATA SOURCES AND MEASURED COVERAGE"),

          h2("B", "Spatial design"),
          p("The flood API returns one coordinate per request, and the correct grid cell "
            "is not known in advance: GloFAS represents rivers on a ~5 km grid, so the "
            "simulated channel is offset from the real one. The coordinate in the "
            "original plan returned a mean discharge of only 5.7 m&#179;/s, compared "
            "with 308 m&#179;/s at a nearby cell. Two grids were therefore scanned: "
            "361 cells at 0.05&#176; for discharge and 64 cells at 0.10&#176; for "
            "rainfall, covering the whole catchment because flood-producing rain falls "
            "30&#8211;50 km upstream of the city."),
          p("Collection used a two-stage design to avoid paying for useless series. "
            "Every cell was first probed with a single year of data; only cells with a "
            "mean flow above 1 m&#179;/s were then requested for the full record. Of "
            "361 probed cells, 234 returned values, 83 received full series, and one "
            "was selected as the forecast target, (16.45&#176; N, 107.50&#176; E). Two "
            "intuitive selection rules were tested and rejected: the largest-discharge "
            "cell combines the Huong and Bo rivers, and the cell nearest the Kim Long "
            "gauge carries almost no simulated flow. The decisive evidence was the "
            "catchment area implied by specific runoff."),

          h2("C", "Scale"),
          p("The raw store holds 1,295 Parquet files (about 98 MB): 83 full discharge "
            "series, 316 probes, 64 daily rainfall series, 768 hourly rainfall files "
            "(about 6.7 million records) and 64 forecast-rain series. These are reduced "
            "to a single analysis table of 6,087 days by 71 columns."),

          h2("D", "Licensing and provenance"),
          p("Open-Meteo data are distributed under CC BY 4.0; GloFAS and ERA5 are "
            "Copernicus products and are cited as their providers require [1]&#8211;[3]. "
            "Official alert stages are taken from the primary legal source, Annex I of "
            "Decision 05/2020/QD-TTg, row 135: station <i>Hue (Kim Long)</i>, stages "
            "I/II/III at 1.0, 2.0 and 3.5 m [4]. Every flood event carries its source "
            "URL, access date and a verbatim quotation of the sentence containing the "
            "number."),

          h2("E", "Reliability of collection"),
          *bullets([
              "<b>Resumable.</b> A task is skipped if its output file exists, so an "
              "interrupted crawl restarts without state.",
              "<b>Single instance.</b> A process lock prevents parallel crawlers; an "
              "early burst of HTTP 429 errors was traced to three crawlers competing, "
              "not to the API quota.",
              "<b>Adaptive pacing.</b> The delay widens by 1.5&#215; on rate limiting and "
              "narrows after eight clean calls.",
              "<b>Backed up and restorable.</b> 124 MB archived as a GitHub Release; "
              "restore verified bit-for-bit.",
              "<b>Operational feed.</b> A scheduled job records the live seven-day "
              "forecast every morning and fails loudly if a day is missing &#8212; a "
              "check added after a time-zone bug silently lost one day while every run "
              "reported success.",
          ])]

    # ============================================================ III
    s += [h1("III", "Data Cleaning"),
          h2("A", "Alignment"),
          p("All series were converted from UTC to Vietnam time (UTC+7) and hourly "
            "rainfall summed to daily totals. Validators raise an error instead of "
            "repairing data silently, so any defect stops the pipeline. The final table "
            "has no missing values in discharge or rainfall."),

          h2("B", "Defects found and corrected"),
          p("Measuring the data rather than trusting documentation exposed four "
            "defects, summarised in Table II. Each was invisible to the obvious check."),
          table([
              ["Defect", "Why it was missed", "Action"],
              ["Discharge empty for 1984&#8211;1996 (30.5% of rows) in all 83 cells",
               "Acceptance counted rows, not values; the panel starts in 2010, after the gap",
               "Record stated as 1997&#8211;2026; test on non-empty days"],
              ["Rain grid irregular: middle sub-basin 9 of 16 cells, upper 30 of 24",
               "Files from an abandoned 0.15&#176; grid were kept by the resume logic",
               "Rebuilt as 64 uniform cells; 224 files quarantined"],
              ["Archived forecast rain identical to ERA5 (max difference 0.0 mm, 1,523 days)",
               "Assumed different because the endpoint is named &#8220;forecast&#8221;",
               "Scenario B replaced by a sensitivity analysis"],
              ["Planned target coordinate on a minor branch",
               "Coordinate taken from the plan without checking",
               "Target chosen from three independent lines of evidence"],
          ], [1.2 * inch, 1.25 * inch, 1.09 * inch], "II", "DATA DEFECTS FOUND BY MEASUREMENT"),
          p("The rain-grid correction mattered most for the sub-basin closest to the "
            "forecast point: the middle sub-basin contains both the Kim Long gauge and "
            "the target cell, yet had been sampled at 56% of the intended density. After "
            "rebuilding, its mean rainfall changed by -6.3%; discharge columns were "
            "unchanged, as expected."),

          h2("C", "Features and leakage control"),
          p("Features comprise discharge lags of 1&#8211;14 days, rainfall per sub-basin "
            "with lags and 3-, 5- and 7-day trailing sums, an antecedent precipitation "
            "index (k = 0.9, 14 days), discharge differences and a cyclic day-of-year "
            "encoding. Every rolling window looks backward only; an automated test fails "
            "if any feature uses information from after the forecast date. The test "
            "period starts at 1 July 2022, the date GloFAS switches from reanalysis to "
            "archived forecasts.")]

    # ============================================================ IV
    s += [h1("IV", "Exploratory Data Analysis"),
          p("Each figure below is followed by the conclusion it supports. Numbers are "
            "taken from the analysis table of 6,087 days (2010&#8211;2026)."),

          h2("A", "Overview"),
          fig("eda1_tong_quan", 1, "Daily discharge (left) and its log distribution (right)."),
          p("Discharge is strongly right-skewed (skewness 5.91): the median is "
            "49.7 m&#179;/s while the maximum reaches 3,588 m&#179;/s on 8 November 2011. "
            "Models are therefore trained on a log scale, and accuracy is not used as a "
            "metric anywhere in the project."),

          h2("B", "Seasonality"),
          fig("eda2_mua_vu", 2, "Monthly median discharge and mean rainfall."),
          p("The flood season runs from September to December and peaks in October "
            "(median 118.3 m&#179;/s, about four times the driest month). These four "
            "months carry 58.6% of annual flow, so every train/test split must contain "
            "full flood seasons."),

          h2("C", "Rainfall&#8211;discharge lag"),
          fig("eda3_lag", 3, "Correlation between rainfall and discharge by lag, "
              "by season (left) and by sub-basin (right)."),
          p("Rainfall leads discharge by one day (r = 0.789), and the lag is identical in "
            "all three sub-basins. This is not because the upper basin is close: the "
            "travel time from Thuong Nhat to Kim Long is only five to six hours over "
            "51 km [5], shorter than the daily resolution can separate. Hourly rainfall "
            "is the natural way to recover this detail."),

          h2("D", "Accumulated rainfall and antecedent wetness"),
          fig("eda4_api", 4, "Discharge against the antecedent precipitation index."),
          p("Three-day accumulated rainfall is the strongest single rainfall variable "
            "(r = 0.863, against 0.642 for one-day rainfall). More striking, the same "
            "heavy rain produces a median discharge of 585 m&#179;/s on wet ground but "
            "only 85 m&#179;/s on dry ground &#8212; a factor of 6.9. Antecedent wetness "
            "is a primary control on the basin response, not a secondary feature."),

          h2("E", "Historical floods"),
          fig("eda5_su_kien", 5, "Simulated discharge around three documented floods."),
          p("Published water levels and simulated discharge do not move together. The "
            "flood of 12 October 2020 reached 4.17 m with 2,060 m&#179;/s, but the flood "
            "of 15 November 2023 reached a <i>higher</i> 4.34 m with only 584 m&#179;/s. "
            "Section V returns to the consequences."),

          h2("F", "Extremes"),
          fig("eda6_cuc_tri", 6, "Annual peaks (left) and the flow duration curve (right)."),
          p("The 99th percentile (1,169 m&#179;/s) is exceeded on 61 days in the whole "
            "record. Rare thresholds quickly run out of examples, so any result with "
            "fewer than 30 positive test days is reported but not used as a main "
            "conclusion."),

          h2("G", "Two data regimes"),
          fig("eda7_che_do", 7, "Discharge distribution before and after July 2022."),
          p("Report 1 flagged a risk that the archived-forecast period after July 2022 "
            "differs in amplitude. Comparing the two periods directly is not conclusive, "
            "because they are different years with different weather. Instead, rainfall "
            "was used as a reference that does not change regime: for the same "
            "three-day rainfall, median discharge differed significantly in only one of "
            "five rainfall bands, and the heaviest-rain tail showed no difference "
            "(Mann&#8211;Whitney p = 0.581). The risk is therefore downgraded, while the "
            "split at July 2022 is kept as good practice."),

          h2("H", "Spatial structure"),
          fig("eda8_khong_gian", 8, "Correlation between sub-basin rainfall and discharge."),
          p("Mean rainfall is similar across sub-basins after the grid correction, and "
            "correlation with discharge decreases from upper to lower basin, consistent "
            "with runoff generated upstream.")]

    # ============================================================ V
    s += [h1("V", "Data Limitations"),
          p("Four limitations follow directly from the analysis and bound what the "
            "later models can claim."),
          *bullets([
              "<b>Simulated, not observed, discharge.</b> No gauge record is available, "
              "so models forecast the GloFAS series, not the true river.",
              "<b>Reanalysis rainfall under-represents extremes.</b> For November 2024 "
              "the wettest ERA5 cell totals 332 mm, while published totals in the "
              "mountains were commonly 500&#8211;800 mm. A grid cell is an area average "
              "and a gauge is a point, so part of this gap is expected, but the "
              "direction is consistent with GloFAS missing the largest floods.",
              "<b>Water level is not a function of upstream discharge alone.</b> Across "
              "12 floods, log-discharge explains little of the published water level "
              "(R&#178; = 0.18, Spearman p = 0.245), while rainfall relates more "
              "strongly (p = 0.042). Tide and backwater from the Tam Giang lagoon are "
              "plausible causes: two floods with almost equal discharge (584 and "
              "600 m&#179;/s) differed by 1.24 m in level, and the higher one coincided "
              "with the higher tide. Tide data exist only from 2023, so this remains a "
              "lead, not a proof.",
              "<b>Short test window.</b> Labels are risk levels defined by flood-season "
              "discharge percentiles (95th, 98th, 99.5th) fitted on training data only. "
              "In the 4.2-year test period only the first level has at least 30 "
              "positive days (31; the others have 12 and 7).",
          ])]

    # ============================================================ VI
    s += [h1("VI", "Changes Since Report 1"),
          table([
              ["Report 1 stated", "Corrected to", "Reason"],
              ["A 42-year discharge record", "29 years, 1997&#8211;2026",
               "1984&#8211;1996 delivered as empty values"],
              ["Archived precipitation forecasts as an input",
               "Sensitivity analysis on perturbed rainfall",
               "Archived forecasts identical to ERA5"],
              ["Target: official flood-alert stage", "Risk levels from discharge percentiles",
               "Stage&#8211;discharge relation not reliable at Kim Long"],
              ["Official stages from news bulletins", "Decision 05/2020/QD-TTg, Annex I",
               "Primary legal source obtained"],
          ], [1.2 * inch, 1.2 * inch, 1.14 * inch], "III", "CORRECTIONS TO REPORT 1"),
          p("The official stages themselves (1.0, 2.0 and 3.5 m) were confirmed, both "
            "from the decree and independently from six published bulletins. Older "
            "sources show that stage III at Kim Long was previously 3.0 m, so relative "
            "values in pre-2010 reports must be converted with the threshold in force at "
            "the time.")]

    # ============================================================ VII
    s += [h1("VII", "Next Steps"),
          p("A first gradient-boosting model already beats persistence at all three "
            "horizons, and an ablation shows that beyond one day, discharge lags add "
            "noise rather than information. Report 3 will therefore select "
            "horizon-specific feature sets on the validation period, add quantile "
            "regression to address the systematic under-prediction of peaks, and explain "
            "the models with SHAP values.")]

    # ============================================================ refs
    s += [p("REFERENCES", "h1")]
    refs = [
        "[1] Open-Meteo, &#8220;Flood API, Archive API and Marine API,&#8221; 2026. "
        "[Online]. Available: https://open-meteo.com/en/docs",
        "[2] S. Harrigan <i>et al.</i>, &#8220;Daily ensemble river discharge reforecasts "
        "and real-time forecasts from the operational Global Flood Awareness System,&#8221; "
        "<i>Hydrol. Earth Syst. Sci.</i>, vol. 27, no. 1, pp. 1&#8211;19, 2023.",
        "[3] H. Hersbach <i>et al.</i>, &#8220;The ERA5 global reanalysis,&#8221; <i>Q. J. "
        "R. Meteorol. Soc.</i>, vol. 146, no. 730, pp. 1999&#8211;2049, 2020.",
        "[4] Prime Minister of Vietnam, &#8220;Decision 05/2020/QD-TTg on water levels "
        "corresponding to flood alert levels on rivers nationwide,&#8221; <i>Official "
        "Gazette</i>, no. 179+180, Feb. 2020, Annex I. [in Vietnamese]",
        "[5] H. S. Nguyen <i>et al.</i>, &#8220;Synoptic patterns causing heavy rain and "
        "floods in Thua Thien Hue province in 2020,&#8221; <i>Hue Univ. J. Sci.: Earth "
        "Sci. Environ.</i>, vol. 131, no. 4A, pp. 149&#8211;162, 2022. [in Vietnamese]",
        "[6] G. Nearing <i>et al.</i>, &#8220;Global prediction of extreme floods in "
        "ungauged watersheds,&#8221; <i>Nature</i>, vol. 627, pp. 559&#8211;563, 2024.",
        "[7] V. Nourani, S. Kheirieh, S. A. Kantoush and J. J. Huang, &#8220;Bias "
        "correction of Global Flood Awareness System (GloFAS) data for multi-station "
        "river flow prediction by ensemble modelling,&#8221; <i>Eng. Appl. Comput. Fluid "
        "Mech.</i>, vol. 20, no. 1, 2665857, 2026.",
        "[8] T. Honcharenko <i>et al.</i>, &#8220;Explainable deep ensemble bias correction "
        "of GloFAS-ERA5 streamflow across snow-influenced transboundary basins of Central "
        "Asia,&#8221; <i>Water</i>, vol. 18, no. 16, 2055, 2026.",
    ]
    s += [p(r, "ref") for r in refs]
    return s


# ------------------------------------------------------------------ bố cục
def build() -> int:
    check_numbers()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUT), pagesize=LETTER, leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM,
                          title="DSP391m Report 2 - Data Collection, Cleaning and EDA",
                          author=", ".join(cfg.TEAM_ASCII))
    avail_h = PH - TM - BM
    head_h = 3.0 * inch

    def fr(x, y, w, h, i):
        return Frame(x, y, w, h, id=i, leftPadding=0, rightPadding=0,
                     topPadding=0, bottomPadding=0)

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Times-Roman", 8.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(PW / 2, BM - 26, str(d.page))
        canvas.drawString(LM, BM - 26, "DSP391m - Data Science Project - Report 2")
        canvas.drawRightString(PW - RM, BM - 26, "FPT University, Fall 2026")
        canvas.restoreState()

    doc.addPageTemplates([
        PageTemplate(id="first", onPage=footer, frames=[
            fr(LM, PH - TM - head_h, PW - LM - RM, head_h, "head"),
            fr(LM, BM, COLW, avail_h - head_h, "c1l"),
            fr(LM + COLW + GUT, BM, COLW, avail_h - head_h, "c1r")]),
        PageTemplate(id="rest", onPage=footer, frames=[
            fr(LM, BM, COLW, avail_h, "cl"),
            fr(LM + COLW + GUT, BM, COLW, avail_h, "cr")]),
    ])

    head = [
        p("Data Collection, Cleaning and Exploratory Analysis for One-to-Three-Day "
          "Flood Forecasting in the Huong River Basin", "title"),
        p(("&nbsp;" * 4).join(cfg.TEAM_ASCII), "author"),
        Spacer(1, 3),
        p("Department of Information Technology, FPT University<br/>"
          "DSP391m &#8212; Data Science Project &#8212; Fall 2026<br/>Hue, Vietnam", "affil"),
        Spacer(1, 9),
        Paragraph(
            "<b><i>Abstract</i></b>&#8212;<font size=9>This report documents how open "
            "hydro-meteorological data for the Huong River basin were collected, cleaned "
            "and explored. A two-stage grid scan located the correct GloFAS cell among "
            "361 candidates and assembled a 6,087-day analysis table. Measuring the data "
            "instead of trusting documentation exposed four defects: thirteen years of "
            "empty discharge values, an irregular rainfall grid that under-sampled the "
            "sub-basin nearest the forecast point, archived forecast rainfall identical "
            "to reanalysis, and a misplaced target coordinate. Exploratory analysis shows "
            "a one-day rainfall&#8211;discharge lag (r = 0.789), a dominant role for "
            "three-day accumulated rainfall (r = 0.863), and a 6.9-fold amplification of "
            "the river response on wet ground. It also shows that published water levels "
            "at Kim Long are only weakly related to simulated discharge, which motivates "
            "defining flood risk by discharge percentiles rather than official stages. "
            "All corrections to Report 1 are listed explicitly.</font>",
            ST["abstext"]),
        Paragraph(
            "<b><i>Keywords</i></b>&#8212;<font size=9>data quality, exploratory data "
            "analysis, GloFAS, ERA5, open data, flood forecasting, Huong River</font>",
            ST["keywords"]),
    ]
    body = story()
    check_glyphs(head + body)
    doc.build(head + [NextPageTemplate("rest")] + body)
    print(f"→ {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(build())
