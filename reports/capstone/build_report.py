"""Report 4 — Capstone Project Document theo mẫu FPT (bìa, mục lục, 7 chương, một cột A4).

    PYTHONIOENCODING=utf-8 python reports/capstone/build_report.py            # bản nháp
    PYTHONIOENCODING=utf-8 python reports/capstone/build_report.py --submit   # bản nộp

Nội dung khoa học lấy nguyên từ ``reports/final/build_report.py`` (hàm ``story()``): chạy lại
hàm đó với helper bản một cột (tiêu đề, bảng, hình) rồi xếp các mục cũ vào 7 chương của mẫu.
Mọi số vẫn đi qua sổ ``reports/final/facts.py`` và lớp quét số / ký tự của Report 3, nên
bản này không thể lệch số với bản Final. Chương mới (thông tin dự án, quản lý dự án, thiết kế
hệ thống) viết ở đây; số thập phân trong đó đăng ký vào sổ kèm nguồn (``extra_facts``).

Thông tin bìa chưa có (MSSV, email, giảng viên, tên nhóm) để trong ``TEAM_INFO``; bản nháp in
chỗ trống có đánh dấu, ``--submit`` dừng build nếu còn chỗ trống.
"""

from __future__ import annotations

import importlib.util
import io
import re
import sys
from pathlib import Path

from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
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
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

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


fb = _load("final_build_capstone", ROOT / "reports" / "final" / "build_report.py")
r3, fx = fb.r3, fb.fx
V = fx.R
OUT = HERE / "DSP391m_Report4_Capstone_Project_Document.pdf"
FIGS = r3.FIGS
SLIDE_IMG = ROOT / "reports" / "final" / "slides" / "img"
WARN: list[str] = []
TT, TE, ND = "<font face='Courier'>", "</font>", "&#8211;"

# ------------------------------------------------------------------ thông tin bìa
# None = chưa có ⇒ in "[...]" màu đỏ; --submit dừng nếu còn None.
TEAM_INFO = {
    "group": None,                       # tên nhóm (dòng đậm dưới tên đề tài)
    "supervisor": None,                  # họ tên giảng viên hướng dẫn (không dấu)
    "supervisor_email": None,
    "members": [                         # (tên không dấu, vai trò, MSSV, email FPT)
        ("Dang Nguyen Giap", "Leader (Tech Lead)", None, None),
        ("Ho Anh Duc", "Member (Data Analyst)", None, None),
        ("Mai Thi Le Huyen", "Member (Research &amp; Docs)", None, None),
    ],
}
MISSING: list[str] = []


def info(v, what: str) -> str:
    if v:
        return v
    MISSING.append(what)
    return f"<font color='#C0392B'>[{what}]</font>"


# ================================================================== kiểu chữ
PW, PH = A4
LM = RM = 1.0 * inch
TM, BM = 1.0 * inch, 0.95 * inch
TW = PW - LM - RM


def S(name, **kw):
    base = dict(fontName="Times-Roman", fontSize=11, leading=14.6, alignment=TA_JUSTIFY,
                spaceAfter=6)
    base.update(kw)
    return ParagraphStyle(name, **base)


CS = {
    "body": S("body"), "body0": S("body0"),
    "bullet": S("bullet", leftIndent=0.28 * inch, bulletIndent=0.1 * inch, spaceAfter=3),
    "ref": S("ref", fontSize=10, leading=12.6, alignment=TA_LEFT, leftIndent=0.3 * inch,
             firstLineIndent=-0.3 * inch, spaceAfter=3),
    "pending": S("pending", fontName="Times-Italic", textColor=colors.HexColor("#8a4b00")),
    "ch": S("ch", fontName="Times-Bold", fontSize=18, leading=22, alignment=TA_LEFT,
            spaceBefore=6, spaceAfter=12),
    "s1": S("s1", fontName="Times-Bold", fontSize=14, leading=17, alignment=TA_LEFT,
            spaceBefore=10, spaceAfter=6),
    "s2": S("s2", fontName="Times-Bold", fontSize=12, leading=15, alignment=TA_LEFT,
            spaceBefore=8, spaceAfter=4),
    "front": S("front", fontName="Times-Bold", fontSize=18, leading=22, alignment=TA_LEFT,
               spaceAfter=14),
    "cap": S("cap", fontSize=10, leading=12.4, alignment=TA_CENTER, spaceBefore=4,
             spaceAfter=10),
    "th": S("th", fontName="Times-Bold", fontSize=9.4, leading=11.4, alignment=TA_CENTER,
            spaceAfter=0),
    "td": S("td", fontSize=9.4, leading=11.4, alignment=TA_LEFT, spaceAfter=0),
}
COV = {
    "small": S("cs", fontName="Times-Bold", fontSize=13, leading=17, alignment=TA_CENTER),
    "doc": S("cd", fontName="Times-Roman", fontSize=16, leading=20, alignment=TA_CENTER),
    "title": S("ct", fontName="Times-BoldItalic", fontSize=19, leading=25, alignment=TA_CENTER),
    "group": S("cg", fontName="Times-Bold", fontSize=15, leading=19, alignment=TA_CENTER),
    "lab": S("cl", fontName="Times-Bold", fontSize=13, leading=17, alignment=TA_CENTER,
             spaceBefore=10),
    "txt": S("cx", fontSize=13, leading=17, alignment=TA_CENTER, spaceAfter=2),
}


# ================================================================== tiêu đề + mục lục
class Head(Paragraph):
    """Tiêu đề có mục trong Contents (toc = mức) — afterFlowable đọc thuộc tính này."""

    def __init__(self, text, style, toc_level: int, toc_text: str):
        super().__init__(text, style)
        self.toc = ("TOCEntry", toc_level, toc_text)


class Caption(Paragraph):
    def __init__(self, text, kind: str, entry: str):
        super().__init__(text, CS["cap"])
        self.toc = (kind, 0, entry)


def chapter(num: str, title: str):
    return [CondPageBreak(2.2 * inch),
            Head(f"{num}&nbsp;&nbsp;{title}", CS["ch"], 0, f"{num}  {title}")]


def sec(num: str, title: str):
    if f"sec_{num}" not in V.val:          # số mục (4.2, 5.1.3) không phải số liệu: đăng ký cho lớp quét số
        V.doc(f"sec_{num}", num, "số mục của tài liệu")
    lvl = num.count(".")
    st = CS["s1"] if lvl == 1 else CS["s2"]
    return [CondPageBreak(1.0 * inch), Head(f"{num}&nbsp;&nbsp;{title}", st, lvl, f"{num}  {title}")]


def front(title: str, toc: bool = True):
    if toc:
        return Head(title, CS["front"], 0, title)
    return Paragraph(title, CS["front"])


class ListOf(TableOfContents):
    """Danh sách bảng / hình: nghe sự kiện riêng thay vì TOCEntry."""

    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind
        self.levelStyles = [S(f"lo_{kind}", fontSize=10.5, leading=13, alignment=TA_LEFT,
                              leftIndent=0, firstLineIndent=0, spaceAfter=2)]

    def notify(self, kind, stuff):
        if kind == self.kind:
            self.addEntry(*stuff)


def toc():
    t = TableOfContents()
    t.levelStyles = [
        S("toc0", fontName="Times-Bold", fontSize=11.5, leading=15, alignment=TA_LEFT,
          spaceBefore=5, spaceAfter=1),
        S("toc1", fontSize=11, leading=13.6, alignment=TA_LEFT, leftIndent=0.3 * inch,
          spaceAfter=0),
        S("toc2", fontSize=10.5, leading=13, alignment=TA_LEFT, leftIndent=0.65 * inch,
          spaceAfter=0),
    ]
    return t


# ================================================================== bảng, hình
T: dict[str, str] = {}
F: dict[str, str] = {}
CASE: dict[str, str] = {}        # cách viết hoa của từ trong thân bài, để đổi chú thích IN HOA


def plain(t: str) -> str:
    return r3.plain(t)


def sentence(cap: str) -> str:
    """Chú thích IEEE IN HOA → câu thường, giữ tên riêng / viết tắt theo cách viết trong bài."""
    letters = [c for c in plain(cap) if c.isalpha()]
    if sum(c.isupper() for c in letters) < 0.7 * len(letters):
        return cap

    def word(m):
        w = m.group(0)
        return w if len(w) == 1 else CASE.get(w.lower(), w.lower())     # h, A, E giữ nguyên

    parts = re.split(r"(<[^>]+>|&#?\w+;)", cap)
    first = True
    for i, x in enumerate(parts):
        if x.startswith(("<", "&")) or not x:
            continue
        x = re.sub(r"[A-Za-z][A-Za-z0-9-]*", word, x)
        if first and re.search(r"[A-Za-z]", x):
            j = re.search(r"[A-Za-z]", x).start()
            x, first = x[:j] + x[j].upper() + x[j + 1:], False
        parts[i] = x
    return "".join(parts)


def tbl(rows, widths, key: str, caption: str, small: bool = False, bold_rows=(), fill=0.96):
    if key == "team":                 # bảng thành viên đã có ở Chương I
        return None
    k = TW * fill / sum(widths)
    data = [[Paragraph(c, CS["th"]) for c in rows[0]]]
    for i, r in enumerate(rows[1:], start=1):
        data.append([Paragraph(f"<b>{c}</b>" if i in bold_rows else c, CS["td"]) for c in r])
    t = Table(data, colWidths=[w * k for w in widths], hAlign="CENTER", repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa3ad")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6ebf0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    cap = sentence(caption).rstrip(".") + "."
    return KeepTogether([t, Caption(f"Table {T[key]}: {cap}", "LOT", f"{T[key]}&nbsp;&nbsp;{cap}")])


def _fig(img, key: str, caption: str, width: float):
    iw, ih = img.getSize() if hasattr(img, "getSize") else ImageReader(img).getSize()
    h = width * ih / iw
    if h > 6.3 * inch:                       # hình cao: giới hạn chiều cao
        width, h = width * 6.3 * inch / h, 6.3 * inch
    if isinstance(img, ImageReader):
        buf = io.BytesIO()
        img._image.save(buf, "PNG")
        buf.seek(0)
        img = buf
    cap = caption.rstrip(".") + "."
    return KeepTogether([Image(img, width=width, height=h),
                         Caption(f"Figure {F[key]}: {cap}", "LOF", f"{F[key]}&nbsp;&nbsp;{cap}")])


def col_fig(fname: str, key: str, caption: str, scale: float = 1.0):
    f = FIGS / fname
    if not f.exists():
        raise SystemExit(f"Thiếu hình {f.relative_to(ROOT)}")
    return _fig(str(f), key, caption, TW * 0.82 * min(scale * 1.1, 1.0))


def col_img(img: ImageReader, key: str, caption: str, scale: float = 1.0):
    return _fig(img, key, caption, TW * 0.9 * min(scale * 1.1, 1.0))


def img_fig(path: Path, key: str, caption: str, frac: float = 0.95):
    if not path.exists():
        raise SystemExit(f"Thiếu hình {path.relative_to(ROOT)}")
    return _fig(str(path), key, caption, TW * frac)


def fig_drawing(d: Drawing, key: str, caption: str):
    k = TW * 0.9 / d.width
    d.scale(k, k)
    d.width, d.height = d.width * k, d.height * k
    cap = caption.rstrip(".") + "."
    return KeepTogether([d, Caption(f"Figure {F[key]}: {cap}", "LOF", f"{F[key]}&nbsp;&nbsp;{cap}")])


def pending(text: str):
    return Paragraph(text, CS["pending"])


def para(text: str, st: str = "body"):
    return Paragraph(text, CS[st])


def blist(items):
    return [Paragraph(t, CS["bullet"], bulletText="•") for t in items]


# ================================================================== nội dung Final
class Mark:
    def __init__(self, level: int, label: str, title: str):
        self.level, self.label, self.title = level, label, title


SEC_REF = re.compile(r"(Sections?\s+)([IVX]+(?:-[A-I])?(?:(?:,\s*|\s+and\s+)[IVX]+(?:-[A-I])?)*)")
LABEL = re.compile(r"[IVX]+(?:-[A-I])?")


def run_final(refmap: dict[str, str]):
    """Chạy fb.story() với helper một cột → [(Mark, [flowables])]."""
    cur = [""]

    def fix(t: str) -> str:
        if not refmap:
            return t
        return SEC_REF.sub(lambda m: m.group(1) + LABEL.sub(
            lambda n: refmap.get(n.group(0), n.group(0)), m.group(2)), t)

    def h1(n, t):
        cur[0] = n
        return Mark(1, n, t)

    def h2(letter, t):
        return Mark(2, f"{cur[0]}-{letter}", t)

    def p(t, st="body"):
        if st == "h1":
            return Mark(1, "REF", t)
        return Paragraph(fix(t), CS.get(st, CS["body"]))

    fb.h1, fb.h2, fb.p, fb.pending = h1, h2, p, pending
    fb.bullets = lambda items: blist([fix(t) for t in items])
    fb.tbl, fb.col_fig, fb.col_img, fb.fig_drawing = tbl, col_fig, col_img, fig_drawing
    fb.T, fb.F = T, F
    out, cur_sec = [], None
    for fl in fb.story():
        if isinstance(fl, Mark):
            if fl.label in {m.label for m, _ in out}:      # VI-B in hai nhánh: nhánh nào chạy thì giữ
                cur_sec = next(c for m, c in out if m.label == fl.label)
                continue
            cur_sec = []
            out.append((fl, cur_sec))
        elif fl is None:
            continue
        elif isinstance(fl, NextPageTemplate):
            cur_sec.append(wide_fig(fl))
        else:
            cur_sec.append(fl)
    return out


def wide_fig(npt: NextPageTemplate):
    pt = npt.action[1]
    names = pt if isinstance(pt, (list, tuple)) else [pt]
    if "wide_ev" in names:
        return col_img(fb.crop_events(), "ev",
                       "Flood events (runs of level-1 days) of configuration E and persistence. "
                       "(a) Share of events caught (at least one forecast day above the level-1 "
                       f"threshold) on the test period ({V('ev_nte')} events) and in the "
                       f"walk-forward ({V('ev_nwf')} events); (b) forecast peak over simulated "
                       "peak", 1.0)
    if "wide_rel" in names:
        return col_img(fb.crop_reliability(), "rel",
                       "Reliability of the level-1 classifier, configuration E, pooled "
                       "out-of-fold probabilities 2013&#8211;2025 (h = 1, 2, 3). Orange: raw "
                       "LightGBM; blue: isotonic calibration fitted on earlier years only; bars: "
                       "days per bin (log scale); hollow markers: fewer than ten days", 1.0)
    raise SystemExit(f"NextPageTemplate lạ trong story(): {names}")


# Chương mới của mục Final cũ: nhãn h1 cũ → (số mục mới, tiêu đề mới hoặc None = giữ)
PLACE = {
    "I": ("1.1.1", "Project Background"),
    "II": ("3", None),
    "III": ("4.1", "Study Area and Data"),
    "IV": ("4.2", "Modelling Methodology"),
    "V": ("5.1", "Forecasting Results"),
    "VI": ("5.2", "Distributed Processing and Deep Learning"),
    "VII": ("5.3", "Experiments on Peak Underprediction"),
    "IX": ("5.4", "Discussion"),
    "VIII": ("6.4", "Daily Forecasting Service"),
    "XI": ("7.1", "Conclusion"),
    "X": ("7.2", "Limitations and Future Work"),
}


# Hình thêm cho bản một cột (đã có trong reports/figures/report), sau mục cũ tương ứng
EXTRA = {
    "III-D": [lambda: col_fig("eda10_box_kde_en.png", "eda1",
                              "Daily GloFAS discharge at Kim Long by month, flood season "
                              "September&#8211;December in teal (left), and the density of "
                              "log(1 + Q) (right)", 1.0),
              lambda: col_fig("eda11_corr_heatmap_en.png", "eda2",
                              "Pearson (left) and Spearman (right) correlations between "
                              "discharge, next-day discharge, rainfall aggregates and the "
                              "wetness index (Report 2)", 1.0)],
    "V-G": [lambda: col_fig("shap_beeswarm_h1_en.png", "bee",
                            "SHAP values of the fifteen most important features of "
                            "configuration E one day ahead on the test period; colour is the "
                            "feature value", 0.85)],
}


def refmap_from(secs) -> dict[str, str]:
    m, n = {}, {}
    for mk, _ in secs:
        if mk.level == 1 and mk.label in PLACE:
            num = PLACE[mk.label][0]
            m[mk.label] = num if "." in num else f"{num}"
        elif mk.level == 2:
            h = mk.label.split("-")[0]
            n[h] = n.get(h, 0) + 1
            m[mk.label] = f"{PLACE[h][0]}.{n[h]}"
    return m


def emit(secs, label: str, with_title: bool = True):
    """Mục cũ `label` (kèm mọi h2 con) với số mới."""
    num, title = PLACE[label]
    out, n = [], 0
    for mk, body in secs:
        if mk.label == label:
            if with_title:
                out += sec(num, title or mk.title) if "." in num else []
            out += body
        elif mk.level == 2 and mk.label.split("-")[0] == label:
            n += 1
            out += sec(f"{num}.{n}", mk.title) + body + [f() for f in EXTRA.get(mk.label, [])]
    return out


# ================================================================== số mới (có nguồn)
def extra_facts() -> None:
    R = V
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    wf = (ROOT / ".github" / "workflows" / "daily-forecast.yml").read_text(encoding="utf-8")
    dreq = (ROOT / "dashboard" / "requirements.txt").read_text(encoding="utf-8")

    def ver(key, pat, text, exp, src):
        m = re.search(pat, text)
        R.csv(key, m.group(1) if m else "?", exp, src)

    ver("cv_py", r'python-version:\s*"([\d.]+)"', wf, "3.11", ".github/workflows/daily-forecast.yml")
    ver("cv_lgbm", r"lightgbm==([\d.]+)", req, "4.5.0", "requirements.txt")
    ver("cv_sk", r"scikit-learn==([\d.]+)", req, "1.6.0", "requirements.txt")
    ver("cv_duck", r"duckdb==([\d.]+)", wf, "1.1.3", ".github/workflows/daily-forecast.yml")
    ver("cv_st", r"streamlit==([\d.]+)", dreq, "1.66.1", "dashboard/requirements.txt")
    ver("cv_plotly", r"plotly==([\d.]+)", dreq, "7.1.0", "dashboard/requirements.txt")
    # bản phát 10/11/2026: cảnh báo mức 1 đầu tiên của job hằng ngày
    import pandas as pd
    lg = ROOT / "reports" / "forecast_log"
    f = lg / "2026-11-10.csv"
    src = "reports/forecast_log/2026-11-10.csv"
    d = pd.read_csv(f).set_index("target_date").loc["2026-11-11"]
    R.csv("live_h1_glofas", f"{d.glofas_discharge:,.0f}", "970", src)
    R.csv("live_h1_lgbm", f"{d.lgbm_q:,.0f}", "817", src)
    R.csv("live_h1_p", f"{d.p_level1:.2f}", "0.21", src)
    R.claim("live_h1_alert", bool(d.canh_bao_level1) and d.p_level1 > 1 / 11,
            "level-1 alert issued (p above 1/11)", src)
    R.doc("lic_ccby", "4.0", "Open-Meteo: giấy phép CC BY 4.0")
    ver("cv_pandas", r"pandas==([\d.]+)", dreq, "3.0.3", "dashboard/requirements.txt")


# ================================================================== chương mới
def ch1(secs) -> list:
    m = TEAM_INFO["members"]
    s = chapter("I", "Project Information")
    s += [para("<b>Project name:</b> Forecasting One-to-Three-Day Discharge and Flood Risk of "
               "the Huong River at Kim Long as a Local Correction Layer on GloFAS.", "body0"),
          para("<b>Project goal:</b> build a reproducible open-data pipeline and a model that "
               "forecasts the daily GloFAS v4 discharge at Kim Long (Hue) one, two and three "
               "days ahead, translates it into flood-risk levels with a calibrated alert "
               "probability, runs every day without manual work and shows its forecasts on a "
               "public dashboard.", "body0"),
          para("<b>Duration:</b> September 2026 &#8211; November 2026 (nine weeks, W1&#8211;W9).",
               "body0"),
          para("<b>Iterations:</b> four report stages, each closed by a graded deliverable:",
               "body0"),
          *blist(["Stage 1 (W1&#8211;W2) &#8211; proposal, data inventory, legal sources, "
                  "choice of the GloFAS cell and start of the daily forecast log (Report 1).",
                  "Stage 2 (W3&#8211;W4) &#8211; data collection and cleaning, daily panel, "
                  "exploratory analysis, risk-level definition (Report 2).",
                  "Stage 3 (W5&#8211;W8) &#8211; baselines, LightGBM, ablations, walk-forward "
                  "validation, classifiers, SHAP, reservoirs (Report 3).",
                  "Stage 4 (W8&#8211;W9) &#8211; Spark cluster and deep learning, peak "
                  "experiments, calibration, live model, dashboard, final document (Report 4)."]),
          para("<b>Methodology:</b> iterative, evidence-first data-science process: every "
               "modelling decision is fixed on validation data or walk-forward folds before the "
               "test period is read; acceptance criteria are set before experiments; negative "
               "results are reported. Work is tracked in Git branches and pull requests with "
               "automated tests.", "body0"),
          para("<b>Team roles:</b> Tech Lead (data engineering, modelling, infrastructure, "
               "integration), Data Analyst (exploratory analysis, features, baselines, "
               "dashboard), Research &amp; Documentation (literature, legal sources, data "
               "dictionary, reports and slides).", "body0"),
          tbl([["Full name", "Role", "Student ID", "Email"],
               [info(TEAM_INFO["supervisor"], "Supervisor name"), "Supervisor", "&#8212;",
                info(TEAM_INFO["supervisor_email"], "Supervisor email")]]
              + [[n, r, info(sid, f"Student ID {n}"), info(em, f"Email {n}")]
                 for n, r, sid, em in m],
              [1.5, 1.4, 1.0, 2.1], "team0", "Project team members and supervisor")]
    s += sec("1.1", "Project Overview")
    s += emit(secs, "I")
    s += sec("1.1.2", "Problem Statement")
    s += [para("<b>Problem.</b> Given the information available at 05:00 local time on day "
               "<i>t</i> (GloFAS discharge up to <i>t</i>, observed and forecast rainfall, "
               "pressure, soil moisture, storm and climate indices), predict the GloFAS v4 "
               "discharge at Kim Long on days <i>t</i>+1, <i>t</i>+2 and <i>t</i>+3, and the "
               "probability that it exceeds the first flood-risk level.", "body0"),
          para("<b>Constraints.</b> Only open data may be used; no gauge discharge is "
               "published for Kim Long, so the target is the GloFAS simulation; the official "
               "alert stages are water levels that discharge does not determine; the daily job "
               "must run on free infrastructure.", "body0"),
          para("<b>Challenges.</b>", "body0"),
          *blist(["(C1) Floods are rare: few days per year exceed the risk levels, so "
                  "averages hide peak errors.",
                  "(C2) The catchment reacts within a day; two to three days ahead the rain that "
                  "causes a peak has often not fallen yet.",
                  "(C3) Two large reservoirs regulate the upper basin, while the GloFAS target "
                  "does not model them.",
                  "(C4) Satellite rainfall arrives with latency, which must be respected to "
                  "avoid look-ahead bias."]),
          para("<b>Research questions</b> (RQ1&#8211;RQ3) are stated in Section 1.1.1 and "
               "answered in Section 7.1.", "body0")]
    s += sec("1.1.3", "Project Scope &amp; Limitation")
    s += [para("<b>In scope.</b>", "body0"),
          *blist(["<b>Data:</b> GloFAS v4 discharge, ERA5 and ERA5-Land, Open-Meteo forecasts, "
                  "IBTrACS storm tracks, ONI, IMERG, GSMaP and GSMaP_NRT rainfall, reservoir "
                  "release orders; 1997&#8211;2026.",
                  "<b>Tasks:</b> daily discharge forecasts one to three days ahead; flood-risk "
                  "levels and a calibrated level-1 alert probability; explanation with SHAP.",
                  "<b>Engineering:</b> automated daily forecast job, versioned model release, "
                  "Streamlit dashboard, Spark cluster for distributed ETL and training.",
                  "<b>Evaluation:</b> NSE, KGE, RMSE, peak bias, POD, FAR, CSI, Brier score, "
                  "event-based scores, held-out test period and yearly walk-forward."]),
          para("<b>Out of scope.</b>", "body0"),
          *blist(["Official warnings or evacuation advice (prescriptive analytics).",
                  "Water-level forecasts and the official alert stages, which need gauge data "
                  "that is not open.",
                  "Commune-level inundation maps: the target exists at one cell only.",
                  "Production-grade hosting: the system is a demonstrative prototype on free "
                  "infrastructure."])]
    return s


def ch2(pm: dict) -> list:
    s = chapter("II", "Project Management Plan")
    s += pm["intro"]
    for num, title, body in pm["sections"]:
        s += sec(num, title) + body
    return s


def ch6(secs) -> list:
    s = chapter("VI", "System Design and Implementation")
    s += sec("6.1", "System Overview")
    s += sec("6.1.1", "System Objectives")
    s += blist(["Produce a forecast every morning without manual work and keep every forecast "
                "as an immutable record for later verification.",
                "Use exactly the same feature code for training and for live forecasts.",
                "Fail loudly: a green job that silently loses a day is treated as a failure.",
                "Keep the cost at zero: GitHub Actions, GitHub Releases and Streamlit "
                "Community Cloud."])
    s += sec("6.1.2", "High-Level Architecture")
    s += [para("The system has four layers. (1) <b>Ingestion</b> scripts download open data "
               "into partitioned Parquet files under " + TT + "data/raw" + TE + ". (2) The "
               "<b>feature layer</b> (Polars and DuckDB) builds the daily panel used for "
               "training and, with the same functions, the live feature row. (3) The "
               "<b>model layer</b> trains LightGBM configuration E and the calibrated level-1 "
               "classifier, and publishes them as a versioned release. (4) The <b>serving "
               "layer</b> is a scheduled GitHub Actions job that writes the daily forecast log, "
               "which the Streamlit dashboard reads. The Spark cluster (Section 6.6) runs the "
               "same ETL and walk-forward code for scale tests.")]
    s += [fig_drawing(ops_drawing(), "sys", "Data flow of the operational system: open-data "
                      "sources, feature layer, model release, daily job and dashboard")]
    s += sec("6.1.3", "Major Technologies Used")
    s += [tbl([["Layer", "Technology", "Use"],
               ["Language", f"Python {V('cv_py')}", "All code; one environment for training "
                "and the daily job"],
               ["Data", f"Polars {V('polars_ver')}, DuckDB {V('cv_duck')}, Parquet",
                "Partitioned raw data, daily panel, feature joins"],
               ["Models", f"LightGBM {V('cv_lgbm')}, scikit-learn {V('cv_sk')}",
                "Configuration E regressors, level-1 classifier, isotonic calibration"],
               ["Deep learning", f"PyTorch {V('torch_ver')}", "LSTM and MLP, DDP training"],
               ["Distributed", f"Apache Spark {V('spark_ver')} (PySpark {V('pyspark_ver')}), "
                "Docker", "Standalone cluster, ETL parity, MLlib, task-parallel walk-forward"],
               ["Serving", "GitHub Actions, GitHub Releases", "Daily forecast job, model "
                "registry"],
               ["Dashboard", f"Streamlit {V('cv_st')}, Plotly {V('cv_plotly')}, pandas "
                f"{V('cv_pandas')}", "Forecast chart, sub-basin map, explanations"],
               ["Quality", "pytest, ruff, GitHub Actions CI", "Tests, lint, leakage checks"]],
              [1.0, 1.9, 2.6], "stack", "Technology stack")]
    s += sec("6.2", "Data and Feature Pipeline")
    s += [para("Raw data are stored by source, year and month as compressed Parquet, so a "
               "re-download touches only the missing partitions. "
               + TT + "src/features/build_panel.py" + TE + " builds the daily panel in two "
               "steps that the live job reuses: " + TT + "add_features()" + TE + " (lags, "
               "rolling sums, antecedent precipitation index, seasonal terms) and "
               + TT + "join_context()" + TE + " (meteorology, storm and ENSO indicators). "
               "Leakage is guarded by tests that shift each source by its real latency and "
               "fail if any feature at day <i>t</i> uses data published after 05:00 on day "
               "<i>t</i>.")]
    s += sec("6.3", "Model Training and Registry")
    s += [para(TT + "src/models/predict_live.py --train" + TE + " fits the three horizon "
               "models of configuration E on all data up to the training cut-off, the level-1 "
               "classifier and its isotonic map fitted on out-of-fold probabilities from "
               "earlier years only. The artefacts are plain-text LightGBM models and JSON "
               "metadata (feature list, thresholds, data cut-off), published as the GitHub "
               "release " + TT + "model-v1.0" + TE + ". The daily job downloads exactly this "
               "release, so a forecast can always be traced to the model that produced it.")]
    s += emit(secs, "VIII")
    s += sec("6.5", "Dashboard")
    s += [para("The Streamlit dashboard (" + TT + "dashboard/app.py" + TE + ") reads the "
               "latest forecast log and has three tabs: <b>Forecast</b> (the last 30 days and "
               "the next three, with raw GloFAS, LightGBM and the reservoir floor against the "
               "three risk levels), <b>Map</b> (the five sub-basins coloured by risk level for "
               "+1, +2 or +3 days) and <b>Explanation</b> (SHAP groups, limits of the method, "
               "how far the forecasts can be trusted). It is deployed on Streamlit Community "
               "Cloud at <u>https://dsp391m-huong-flood.streamlit.app</u> and redeploys on every "
               "push to the main branch.")]
    for f, key, cap in (("dashboard_tab_du_bao.png", "dash1",
                         "Dashboard, Forecast tab: history, three-day forecast and risk levels"),
                        ("dashboard_tab_ban_do.png", "dash2",
                         "Dashboard, Map tab: sub-basins coloured by the forecast risk level")):
        s += [img_fig(SLIDE_IMG / f, key, cap, 0.92)]
    s += sec("6.6", "Distributed Infrastructure")
    s += [para("The Spark standalone cluster is defined in " + TT
               + "infra/spark/docker-compose.yml" + TE + ": one master and "
               f"{V('n_workers')} workers with {V('w_cores')} cores and {V('w_mem')} GB each, "
               f"Spark {V('spark_ver')} on Java {V('java_ver')}. The repository is mounted at "
               + TT + "/opt/repo" + TE + " in every container and replaces a distributed file "
               "system. The image adds PyTorch, LightGBM and scikit-learn so that the same "
               "functions run locally and as Spark tasks; results and measurements are in "
               "Section 5.2.")]
    s += sec("6.7", "Deployment and DevOps")
    s += blist(["<b>Branching:</b> feature branches and pull requests into " + TT + "main"
                + TE + "; no direct commits for code changes.",
                "<b>Continuous integration:</b> every push runs ruff and the pytest suite, "
                "including leakage and parity tests; Parquet files are blocked from commits.",
                "<b>Daily job:</b> " + TT + ".github/workflows/daily-forecast.yml" + TE
                + " runs at 20:00 UTC, installs a minimal environment, downloads the model "
                "release, forecasts, checks that the log has no missing day and commits the "
                "result; a copy is kept as a build artefact for 90 days.",
                "<b>Reports:</b> every report is generated from code; numbers are checked "
                "against their source files at build time."])
    s += sec("6.8", "Operational Summary")
    s += [para("The pipeline has produced a forecast every day since the start of the "
               "project; since 2 November 2026 the log carries the LightGBM forecast and the "
               f"calibrated level-1 probability next to raw GloFAS ({V('live_nlgbm')} issues "
               "so far). A run takes a few minutes on a free GitHub runner."),
          para("On 10 November 2026 the job issued its first level-1 alert: for 11 November "
               f"raw GloFAS forecast {V('live_h1_glofas')} {fb.M3S} and LightGBM "
               f"{V('live_h1_lgbm')} {fb.M3S}, both above the first risk level of "
               f"{V('thr1')} {fb.M3S}, with a calibrated probability of {V('live_h1_p')}, above "
               "the Bayes threshold 1/11 (Figure "
               f"{F['dash1']}). Whether the river actually rose that far can only be judged "
               "when GloFAS reanalysis for these days is available; with a few weeks of live "
               "forecasts, the operational comparison with GloFAS (AC-3) is reported as "
               "pending rather than concluded.")]
    return s


def ops_drawing() -> Drawing:
    """Luồng dữ liệu của hệ thống vận hành: nguồn → đặc trưng → mô hình → job → dashboard."""
    from reportlab.graphics.shapes import Line, Polygon, Rect, String
    W, H = 470, 150
    d = Drawing(W, H)
    dark = colors.HexColor("#2b3a4a")

    def box(x, y, w, h, title, lines, fill):
        d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=colors.HexColor(fill), strokeColor=dark,
                   strokeWidth=0.7))
        d.add(String(x + w / 2, y + h - 12, title, fontName="Times-Bold", fontSize=8.6,
                     textAnchor="middle"))
        for i, t in enumerate(lines):
            d.add(String(x + w / 2, y + h - 23 - 9.4 * i, t, fontName="Times-Roman",
                         fontSize=7.4, textAnchor="middle"))

    def arrow(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=dark, strokeWidth=0.9))
        d.add(Polygon([x2, y2, x2 - 5, y2 + 2.6, x2 - 5, y2 - 2.6], fillColor=dark,
                      strokeColor=dark, strokeWidth=0.1))

    box(0, 40, 92, 100, "Open data", ["GloFAS v4", "ERA5, ERA5-Land", "Open-Meteo",
                                      "IBTrACS, ONI", "IMERG, GSMaP", "reservoir orders"], "#e8eef5")
    box(118, 74, 100, 66, "Feature layer", ["Parquet by source/month", "Polars + DuckDB",
                                            "add_features()", "join_context()"], "#e3f1e0")
    box(118, 4, 100, 58, "Training", ["configuration E", "classifier + isotonic",
                                      "release model-v1.0"], "#fde0c5")
    box(244, 40, 104, 100, "Daily job", ["GitHub Actions", "20:00 UTC", "download model",
                                         "forecast h = 1, 2, 3", "check log, commit"], "#d6e6f5")
    box(374, 74, 96, 66, "Forecast log", ["reports/forecast_log", "one CSV per day",
                                          "GloFAS + LightGBM"], "#f5ecd6")
    box(374, 4, 96, 58, "Dashboard", ["Streamlit Cloud", "forecast, map,", "explanation"],
        "#efe3f3")
    arrow(92, 107, 118, 107)
    arrow(168, 74, 168, 62)
    arrow(218, 107, 244, 107)
    arrow(218, 33, 244, 60)
    arrow(348, 107, 374, 107)
    arrow(422, 74, 422, 62)
    return d


# ================================================================== trang đầu
def cover() -> list:
    m = TEAM_INFO["members"]
    s = [Spacer(1, 0.4 * inch),
         Paragraph("MINISTRY OF EDUCATION AND TRAINING", COV["small"]),
         Paragraph("FPT UNIVERSITY", COV["small"]), Spacer(1, 0.9 * inch),
         Paragraph("Capstone Project Document", COV["doc"]), Spacer(1, 0.25 * inch),
         Paragraph("Forecasting One-to-Three-Day Discharge<br/>and Flood Risk of the Huong "
                   "River at Kim Long<br/>as a Local Correction Layer on GloFAS", COV["title"]),
         Spacer(1, 0.3 * inch),
         Paragraph(info(TEAM_INFO["group"], "Group name"), COV["group"]),
         Spacer(1, 0.6 * inch), Paragraph("Group Members", COV["lab"])]
    s += [Paragraph(f"{n} - {i:02d} - {info(sid, f'Student ID {n}')}", COV["txt"])
          for i, (n, _, sid, _) in enumerate(m, start=1)]
    s += [Paragraph("Supervisor", COV["lab"]),
          Paragraph(info(TEAM_INFO["supervisor"], "Supervisor name"), COV["txt"]),
          Spacer(1, 0.7 * inch),
          Paragraph("DSP391m &#8212; Data Science Project", COV["txt"]),
          Paragraph("November 2026", COV["txt"]), PageBreak()]
    return s


ACRONYMS = [
    ("AC", "Acceptance criterion"), ("API", "Application Programming Interface"),
    ("CI/CD", "Continuous Integration / Continuous Deployment"),
    ("CSI", "Critical Success Index"), ("DDP", "PyTorch Distributed Data Parallel"),
    ("DL", "Deep Learning"), ("ENSO", "El Ni&#241;o&#8211;Southern Oscillation"),
    ("ERA5", "ECMWF Reanalysis v5"), ("ETL", "Extract, Transform, Load"),
    ("FAR", "False Alarm Ratio"), ("GloFAS", "Global Flood Awareness System"),
    ("GSMaP", "Global Satellite Mapping of Precipitation (NRT: near real time)"),
    ("IBTrACS", "International Best Track Archive for Climate Stewardship"),
    ("IMERG", "Integrated Multi-satellitE Retrievals for GPM"),
    ("KGE", "Kling&#8211;Gupta Efficiency"), ("LSTM", "Long Short-Term Memory network"),
    ("ML", "Machine Learning"), ("MLP", "Multilayer Perceptron"),
    ("NSE", "Nash&#8211;Sutcliffe Efficiency"), ("ONI", "Oceanic Ni&#241;o Index"),
    ("POD", "Probability of Detection"), ("PR", "Pull Request"),
    ("RMSE", "Root Mean Squared Error"), ("RQ", "Research Question"),
    ("SHAP", "SHapley Additive exPlanations"), ("UI", "User Interface"),
    ("WBS", "Work Breakdown Structure"), ("WF", "Walk-forward validation"),
]


def front_matter() -> list:
    s = [front("Contents", toc=False), toc(), PageBreak()]
    s += [front("Acknowledgement"),
          para("We thank our supervisor, " + info(TEAM_INFO["supervisor"], "Supervisor name")
               + ", for the questions and reviews after each report, which shaped the "
               "distributed and deep-learning work and the honest treatment of negative "
               "results. We thank the providers of the open data this project depends on: "
               "the Copernicus Emergency Management Service (GloFAS), ECMWF (ERA5), "
               "Open-Meteo (CC BY 4.0), NOAA (IBTrACS and ONI), NASA (IMERG) and JAXA (GSMaP)."),
          Spacer(1, 10), front("Definition and Acronyms"),
          tbl([["Acronym", "Definition"]] + [[a, d] for a, d in ACRONYMS], [1.2, 4.3],
              "acr", "List of definitions and acronyms", fill=0.8),
          PageBreak(), front("List of Tables"), ListOf("LOT"), Spacer(1, 14),
          front("List of Figures"), ListOf("LOF"), PageBreak()]
    return s


# ================================================================== lắp ráp
TABLE_ORDER = ["acr", "team0", "anl"]
FIG_ORDER = ["basins", "eda1", "eda2", "sat", "ev", "rel", "wfall", "shap", "bee", "r2", "arch", "etl", "dl",
             "sys", "dash1", "dash2"]


def story(pm) -> list:
    secs = run_final({})                   # lượt 1: lấy cấu trúc mục cũ
    refmap = refmap_from(secs)
    lower_seen: set[str] = set()
    for t in (plain(x.text) for _, b in secs for fl in b for x in r3.walk(fl)
              if not isinstance(x, Caption)):
        for w in re.findall(r"[A-Za-z][A-Za-z0-9-]*", t):
            if w.islower():
                lower_seen.add(w)
            elif sum(c.isupper() for c in w) > sum(c.isupper() for c in CASE.get(w.lower(), "")):
                CASE[w.lower()] = w             # dạng nhiều chữ hoa nhất: NSE, LightGBM, GloFAS
    for w in lower_seen & set(CASE):            # có dạng chữ thường trong bài ⇒ từ thường
        del CASE[w]
    secs = run_final(refmap)               # lượt 2: tham chiếu mục đã đổi số
    s = cover() + front_matter() + ch1(secs) + ch2(pm)
    s += chapter("III", "Literature Review / Existing Systems") + emit(secs, "II", False)
    s += chapter("IV", "Methodology") + emit(secs, "III") + emit(secs, "IV")
    s += chapter("V", "Results and Discussion") + emit(secs, "V") + emit(secs, "VI") \
        + emit(secs, "VII") + emit(secs, "IX")
    s += ch6(secs)
    s += chapter("VII", "Conclusion and Future Work") + emit(secs, "XI") + emit(secs, "X")
    s += [CondPageBreak(2 * inch), Head("References", CS["ch"], 0, "References")]
    s += next(b for m, b in secs if m.label == "REF")
    return s


class Doc(BaseDocTemplate):
    def afterFlowable(self, fl):
        e = getattr(fl, "toc", None)
        if e:
            kind, lvl, text = e
            key = f"k{id(fl)}"
            self.canv.bookmarkPage(key)
            if kind == "TOCEntry":
                self.canv.addOutlineEntry(re.sub(r"<[^>]+>", "", text), key, level=lvl)
            self.notify(kind, (lvl, text, self.page - 1, key))


def build(submit: bool) -> int:
    global T, F
    fx.load(cfg)
    extra_facts()
    if V.bad:
        raise SystemExit("Số trong báo cáo lệch với dữ liệu:\n" + "\n".join(V.bad))
    from pm_chapter import TABLES as PM_TABLES
    from pm_chapter import chapter_content

    final_tabs = ["data", "base", "abl", "sat", "clf", "cal", "ac"] \
        + (["full"] if fx.SPARK_FULL else []) + ["mllib", "ddp", "dl", "peak", "dev"]
    order = TABLE_ORDER + PM_TABLES + final_tabs + ["stack"]
    T.update({k: str(i) for i, k in enumerate(order, start=1)})
    F.update({k: str(i) for i, k in enumerate(FIG_ORDER, start=1)})
    r3.V, r3.T, r3.F = V, T, F

    import pm_chapter
    pm_chapter.T = T
    pm = chapter_content(para, blist, tbl, V)
    body = story(pm)
    n_num = r3.check_text([fl for fl in body if not isinstance(fl, TableOfContents)])
    if submit and MISSING:
        raise SystemExit("Bản nộp còn thiếu: " + ", ".join(sorted(set(MISSING))))

    def page(canvas, d):
        if d.page == 1:
            return
        canvas.saveState()
        canvas.setFont("Times-Roman", 9)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(LM, PH - 0.6 * inch, "FPT UNIVERSITY")
        canvas.drawRightString(PW - RM, PH - 0.6 * inch, "DSP391m Capstone Project Document")
        canvas.setStrokeColor(colors.HexColor("#bbbbbb"))
        canvas.line(LM, PH - 0.66 * inch, PW - RM, PH - 0.66 * inch)
        canvas.drawCentredString(PW / 2, 0.55 * inch, str(d.page - 1))
        canvas.restoreState()

    doc = Doc(str(OUT), pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=TM,
              bottomMargin=BM, title="DSP391m Capstone Project Document - Huong River flood "
              "forecasting", author=", ".join(cfg.TEAM_ASCII))
    doc.addPageTemplates([PageTemplate(id="p", onPage=page, frames=[
        Frame(LM, BM, TW, PH - TM - BM, leftPadding=0, rightPadding=0, topPadding=0,
              bottomPadding=0)])])
    doc.multiBuild(body)
    print(f"Trong PDF: quét {n_num} số thập phân / số nghìn, tất cả có trong sổ")
    for w in WARN + fb.WARN:
        print(f"CẢNH BÁO: {w}")
    if MISSING:
        print("CẢNH BÁO: còn trống " + ", ".join(sorted(set(MISSING))) + " (--submit sẽ dừng)")
    print(f"→ {OUT.relative_to(ROOT)}  ({doc.page} trang, {OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    raise SystemExit(build("--submit" in sys.argv))
