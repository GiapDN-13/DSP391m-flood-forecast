"""Final defense deck (DSP391m · Final): 25 slides 1920×1080, Vietnamese, build steps + speaker notes.

Chạy:  python reports/final/slides/gen_deck.py      -> slides/*.html + deck.json
       python reports/final/slides/build_pdf.py     -> _slides.html + _script.html (in bằng Chrome headless)

Máy dựng slide lấy từ deck Report 3 (helpers P, BOX, SVG, slide, card_style, rbar...).
Mọi con số lấy từ reports/final/OUTLINE_VI.txt (sổ số kiểm lúc build) và các CSV/tài liệu ghi ở từng slide.
"""
import json
import pathlib

S = pathlib.Path(__file__).resolve().parent
OUT = S / "slides"
OUT.mkdir(exist_ok=True)

INK, MUTED, LIGHT, BG2, DARK, CARD = "#14213D", "#5A6577", "#F6F4EE", "#E9EEF2", "#14213D", "#FFFDF8"
BLUE, ORANGE, TEAL, PURPLE, GOLD, GRAY = "#1F6FB2", "#D2691E", "#2E9E8F", "#7B5EA7", "#A07A10", "#8A94A3"
SKY, PEACH, SOFT, RED = "#7FC7CE", "#F2B880", "#BFD0DA", "#B23A3A"
SERIF, SANS = "'Source Serif 4', Georgia, serif", "'IBM Plex Sans', Arial, sans-serif"
X0, Y0 = 128, 280          # gốc vùng nội dung (dưới tiêu đề)
CW = 1664                  # bề rộng vùng nội dung
FOOT = "DSP391m · Final"
WPM = 160                  # tốc độ nói tiếng Việt ước lượng (từ/phút)

GIAP, DUC, HUYEN = "Đặng Nguyên Giáp", "Hồ Anh Đức", "Mai Thị Lệ Huyền"


def b(order, anim="rise"):
    return f' data-build-in="{anim} {order}"' if order else ""


def P(x, y, w, text, size=28, color=INK, align="left", bold=False, order=0, anim="fade", serif=False, lh=1.25, bg=None):
    ff = f"font-family:{SERIF};" if serif else ""
    if bg:   # nền nhãn để đường lưới / vạch mục tiêu không gạch qua chữ
        text = f'<span style="background:{bg};padding:0 6px;border-radius:4px">{text}</span>'
    fw = "font-weight:600;" if bold else ""
    return (f'<p{b(order, anim)} style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;{ff}'
            f'font-size:{size}px;line-height:{lh};color:{color};text-align:{align};{fw}">{text}</p>')


def BOX(x, y, w, inner, style, order=0, anim="rise", h=None):
    hh = f"height:{h:.0f}px;" if h else ""
    return (f'<div{b(order, anim)} style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;{hh}{style}">'
            f'{inner}</div>')


def SVG(x, y, w, h, inner, alt, order=0, anim="fade"):
    return (f'<svg{b(order, anim)} aria-label="{alt}" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;'
            f'width:{w}px;height:{h}px" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'xmlns="http://www.w3.org/2000/svg">{inner}</svg>')


def IMG(x, y, w, src, alt, order=0, h=None, style=""):
    hh = f"height:{h}px;object-fit:cover;object-position:top left;" if h else ""
    return (f'<img{b(order, "fade")} src="img/{src}" alt="{alt}" style="position:absolute;left:{x}px;top:{y}px;'
            f'width:{w}px;{hh}border-radius:12px;border:1px solid #D9DEE3;{style}">')


def card_style(border=None, bg=CARD, pad=32, gap=14):
    bt = f"border-top:6px solid {border};" if border else ""
    return (f"background:{bg};border:1px solid #D9DEE3;{bt}border-radius:16px;padding:{pad}px;"
            f"display:flex;flex-direction:column;gap:{gap}px")


def rbar(x, y, w, h, c):
    if h <= 0:
        return ""
    r = min(4, w / 2, h)
    return f'<path d="M{x:.1f},{y+h:.1f} V{y+r:.1f} Q{x:.1f},{y:.1f} {x+r:.1f},{y:.1f} H{x+w-r:.1f} Q{x+w:.1f},{y:.1f} {x+w:.1f},{y+r:.1f} V{y+h:.1f} Z" fill="{c}"/>'


def rbar_down(x, y0, w, h, c):
    if h <= 0:
        return ""
    r = min(4, w / 2, h)
    return f'<path d="M{x:.1f},{y0:.1f} H{x+w:.1f} V{y0+h-r:.1f} Q{x+w:.1f},{y0+h:.1f} {x+w-r:.1f},{y0+h:.1f} H{x+r:.1f} Q{x:.1f},{y0+h:.1f} {x:.1f},{y0+h-r:.1f} Z" fill="{c}"/>'


def hbar(x, y, w, h, c):
    if w <= 0:
        return ""
    r = min(4, h / 2, w)
    return f'<path d="M{x:.1f},{y:.1f} H{x+w-r:.1f} Q{x+w:.1f},{y:.1f} {x+w:.1f},{y+r:.1f} V{y+h-r:.1f} Q{x+w:.1f},{y+h:.1f} {x+w-r:.1f},{y+h:.1f} H{x:.1f} Z" fill="{c}"/>'


def num(v, d=3):
    """Số có dấu trừ chuẩn (−)."""
    return f"{v:.{d}f}".replace("-", "−")


def sgn(v, d=3):
    return ("+" if v > 0 else "") + num(v, d) if v != 0 else f"{0:.{d}f}"


def arrow(x, y, order=0, color=ORANGE, size=48):
    return P(x, y, 60, "&#8594;", size, color, "center", bold=True, order=order)


def ul(items, size=28, gap=10, color=INK):
    lis = "".join(f'<li style="margin:0 0 {gap}px 0">{t}</li>' for t in items)
    return f'<ul style="font-size:{size}px;line-height:1.4;color:{color};padding-left:1.1em;margin:0">{lis}</ul>'


DECK = []   # (sid, title, speaker, minutes, notes, n_builds)


def notes_html(speaker, paras):
    out = [f"<p>Người nói: {speaker}</p>"]
    for i, t in enumerate(paras):
        tag = "[Mở slide]" if i == 0 else f"[Bấm {i}]"
        out.append(f"<p>{tag} {t}</p>")
    return "".join(out)


def builds_in(parts):
    import re
    orders = [int(m) for m in re.findall(r'data-build-in="\w+ (\d+)"', "".join(parts))]
    return max(orders) if orders else 0


def slide(sid, ttl, parts, speaker, minutes, paras, dark=False, foot=True):
    n = builds_in(parts)
    assert len(paras) == n + 1, f"{sid}: {n} bước build nhưng {len(paras) - 1} đoạn [Bấm]"
    bg, fg = (DARK, LIGHT) if dark else (LIGHT, INK)
    h2 = (f'<h2 style="font-family:{SERIF};font-size:56px;font-weight:600;line-height:1.15;color:{fg};'
          f'position:absolute;left:128px;top:112px;width:1664px">{ttl}</h2>') if ttl else ""
    ft = ""
    if foot:
        fc = SOFT if dark else MUTED
        ft = (P(128, 984, 900, FOOT, 22, fc) + P(1000, 984, 792, speaker, 22, fc, "right"))
    html = (f'<section id="{sid}" data-transition="fade" style="background:{bg};color:{fg};font-family:{SANS};'
            f'position:relative">{h2}{"".join(parts)}{ft}'
            f'<aside>{notes_html(speaker, paras)}</aside></section>\n')
    (OUT / f"{sid}.html").write_text(html, encoding="utf-8")
    words = sum(len(t.split()) for t in paras)
    minutes = round(max(minutes, words / WPM), 1)   # ước lượng theo tốc độ nói ~WPM từ/phút
    DECK.append({"id": sid, "title": ttl, "speaker": speaker, "minutes": minutes, "words": words,
                 "notes": paras, "builds": n})


# =============================================================================================
# PHẦN 1 — GIÁP: bài toán, dữ liệu, pipeline, Spark, hệ thống vận hành
# =============================================================================================

# ------------------------------------------------------------------ 1 cover
parts = [
    P(128, 120, 1664, "DSP391m · Bảo vệ cuối kỳ · FPT University · Fall 2026", 28, SKY, bold=True),
    P(128, 260, 1600, "Dự báo lưu lượng và mức nguy cơ lũ sông Hương tại Kim Long, 1–3 ngày tới",
      80, LIGHT, bold=True, serif=True, lh=1.1, order=1, anim="rise"),
    P(128, 560, 1500, "Một lớp hiệu chỉnh cục bộ trên GloFAS — dữ liệu mở, ~107.5 triệu bản ghi giờ, chạy tự động mỗi sáng",
      34, SOFT, order=2),
]
team = [("Đặng Nguyên Giáp", "Tech Lead", "Bài toán · dữ liệu · Spark · hệ thống vận hành"),
        ("Hồ Anh Đức", "Data Analyst", "Mô hình · đánh giá · cảnh báo · SHAP"),
        ("Mai Thị Lệ Huyền", "Research &amp; Docs", "DL · thử giảm cắt ngọn · hạn chế · kết luận")]
for i, (n_, r_, s_) in enumerate(team):
    parts.append(BOX(128 + i * 560, 730, 520,
                     f'<p style="font-size:30px;font-weight:600;color:{LIGHT}">{n_}</p>'
                     f'<p style="font-size:24px;color:{SKY}">{r_}</p>'
                     f'<p style="font-size:24px;color:{SOFT};line-height:1.35">{s_}</p>',
                     f"border-top:4px solid {SKY};padding:20px 0 0 0;display:flex;flex-direction:column;gap:6px",
                     order=3))
slide("cover", "", parts, GIAP, 0.5, [
    "Em chào thầy cô. Em là Đặng Nguyên Giáp, Tech Lead của nhóm. Hôm nay nhóm em bảo vệ đồ án DSP391m.",
    "Đề tài của nhóm: dự báo lưu lượng và mức nguy cơ lũ sông Hương tại Kim Long, cho 1, 2 và 3 ngày tới.",
    "Nói ngắn gọn, sản phẩm là một lớp hiệu chỉnh cục bộ đặt trên GloFAS: chỉ dùng dữ liệu mở, xử lý khoảng 107,5 triệu bản ghi theo giờ, và đã chạy tự động mỗi sáng.",
    "Bài trình bày khoảng 30 phút, chia ba phần. Em trình bày bài toán, dữ liệu, Spark và hệ thống vận hành. Bạn Đức trình bày mô hình, đánh giá, cảnh báo và SHAP. Bạn Huyền trình bày deep learning, các thử nghiệm giảm cắt ngọn, hạn chế và kết luận.",
], dark=True, foot=False)

# ------------------------------------------------------------------ 2 problem
parts = []
st = [("5.05 m", "mực nước Kim Long ngày 27/10/2025 — cao hơn báo động III 1.55 m (theo tin báo)", PEACH),
      ("5–6 giờ", "để mưa trên núi về tới Huế: lưu vực ngắn và dốc", SKY),
      ("1–3 ngày", "báo trước là thời gian để dân kê đồ, neo thuyền, sơ tán", PEACH)]
for i, (big, small, c) in enumerate(st):
    parts.append(BOX(X0 + i * 568, Y0 + 10, 520,
                     f'<p style="font-family:{SERIF};font-size:88px;font-weight:600;line-height:1;color:{c}">{big}</p>'
                     f'<p style="font-size:28px;color:{SOFT};line-height:1.35">{small}</p>',
                     f"border-top:6px solid {c};padding:28px 0 0 0;display:flex;flex-direction:column;gap:16px",
                     order=i + 1))
parts.append(BOX(X0, 720, CW,
                 f'<p style="font-size:24px;color:{SKY};font-weight:600;letter-spacing:.04em">CÂU HỎI CỦA ĐỒ ÁN</p>'
                 f'<p style="font-family:{SERIF};font-size:40px;font-weight:600;color:{LIGHT};line-height:1.25">'
                 f'Lưu lượng tại Kim Long 1, 2, 3 ngày tới là bao nhiêu — và có vượt mức nguy cơ không?</p>',
                 "display:flex;flex-direction:column;gap:10px", order=4))
slide("problem", "Huế có vài giờ, không phải vài ngày", parts, GIAP, 1.0, [
    "Em bắt đầu từ lý do của bài toán.",
    "Ngày 27/10/2025, mực nước tại Kim Long lên 5,05 mét, cao hơn báo động ba 1,55 mét — con số này nhóm lấy từ tin báo, chỉ để minh hoạ mức độ.",
    "Lưu vực sông Hương ngắn và dốc: mưa trên núi chỉ khoảng 5 đến 6 giờ là về tới thành phố.",
    "Vì vậy mỗi ngày báo trước có giá trị thật: người dân có thời gian kê đồ, neo thuyền, sơ tán.",
    "Câu hỏi của đồ án: lưu lượng tại Kim Long 1, 2, 3 ngày tới là bao nhiêu, và có vượt mức nguy cơ hay không.",
], dark=True)

# ------------------------------------------------------------------ 3 positioning
parts = []
colw, gapw = 470, 127
cols = [
    ("GloFAS v4 (Copernicus)", GRAY, ["Mô phỏng thuỷ văn toàn cầu, ô ~5 km, theo ngày, miễn phí",
                                      "Không mô phỏng hồ Tả Trạch, Bình Điền",
                                      "Thiếu lũ lớn: nước vào hồ &gt; GloFAS ở 14/23 ngày kiểm"]),
    ("Lớp hiệu chỉnh cục bộ", BLUE, ["LightGBM cấu hình E, 88 đặc trưng",
                                     "Học lưu lượng GloFAS 1–3 ngày tới từ mưa giờ, hệ thống thời tiết, trạng thái lưu vực",
                                     "Thêm thông tin cục bộ mà GloFAS không dùng lúc phát báo"]),
    ("Đầu ra mỗi sáng", TEAL, ["Lưu lượng 1–3 ngày tới (m³/s)",
                               "Mức nguy cơ 806 / 1,275 / 1,905 m³/s",
                               "Xác suất vượt mức 1 đã hiệu chỉnh, báo khi ≥ 1/11"]),
]
for i, (h, c, items) in enumerate(cols):
    x = X0 + i * (colw + gapw)
    parts.append(BOX(x, Y0, colw, f'<h3 style="font-size:32px;font-weight:600;color:{c}">{h}</h3>' + ul(items, 25, 8),
                     card_style(c, pad=28), order=i + 1, h=400))
    if i < 2:
        parts.append(arrow(x + colw + 33, Y0 + 170, order=i + 2))
parts.append(BOX(X0, 740, CW,
                 '<p style="font-size:28px;line-height:1.4"><b>Không thay GloFAS.</b> Không có số đo KTTV ⇒ mục tiêu là '
                 '<b>lưu lượng GloFAS v4 theo ngày</b> tại ô (16.45 N, 107.50 E). Mức nguy cơ là phân vị mùa lũ, '
                 '<b>không phải BĐ I/II/III</b>.</p>',
                 f"background:{BG2};border-radius:12px;padding:24px 32px", order=4))
slide("position", "Định vị: lớp hiệu chỉnh cục bộ trên GloFAS", parts, GIAP, 1.0, [
    "Câu hỏi đầu tiên hội đồng hay đặt là: đã có GloFAS, nhóm làm thêm gì? Slide này trả lời.",
    "GloFAS là mô phỏng thuỷ văn toàn cầu, ô khoảng 5 km, miễn phí. Nhưng nó không có hồ Tả Trạch, Bình Điền, và mô phỏng thiếu lũ lớn: nhóm kiểm thấy lượng nước vào hồ lớn hơn GloFAS ở 14 trên 23 ngày có số liệu.",
    "Lớp của nhóm là LightGBM cấu hình E với 88 đặc trưng. Nó học lưu lượng GloFAS 1 đến 3 ngày tới từ mưa theo giờ, hệ thống thời tiết như bão, không khí lạnh, ENSO, và trạng thái lưu vực — những thông tin cục bộ GloFAS không dùng lúc phát báo.",
    "Đầu ra mỗi sáng gồm lưu lượng 1 đến 3 ngày tới, mức nguy cơ theo ba ngưỡng 806, 1.275 và 1.905 m³/s, và xác suất vượt mức 1 đã hiệu chỉnh.",
    "Nhóm nói rõ hai giới hạn ngay từ đầu: không thay GloFAS, và vì không có số đo trạm KTTV nên mục tiêu là lưu lượng GloFAS theo ngày; mức nguy cơ là phân vị mùa lũ, không phải cấp báo động chính thức.",
])

# ------------------------------------------------------------------ 4 basin
parts = [IMG(X0, Y0 - 30, 700, "basins_map.png", "Bản đồ lưu vực sông Hương tới Kim Long, 5 lưu vực con", h=642)]
facts = [("1,543 km²", "lưu vực tới Kim Long, cắt từ DEM 30 m — đính chính con số 2,830 km² cũ (gồm cả sông Bồ 938 km²)", BLUE),
         ("5 lưu vực con", "Tả Trạch 670 · Bình Điền 507 · dưới đập 88 + 185 · Tuần–Kim Long 93 km²", TEAL),
         ("646 + 424 triệu m³", "dung tích hồ Tả Trạch và Bình Điền — GloFAS không mô phỏng hai hồ này", ORANGE),
         ("6,087 ngày", "EDA: Q trung vị 49.7, cực đại 3,588 m³/s (08/11/2011); tháng 9–12 = 58.6 % dòng chảy năm", PURPLE)]
for i, (big, small, c) in enumerate(facts):
    parts.append(BOX(X0 + 760, Y0 - 30 + i * 162, 904,
                     f'<p style="font-family:{SERIF};font-size:40px;font-weight:600;color:{c};line-height:1.05">{big}</p>'
                     f'<p style="font-size:24px;color:{INK};line-height:1.35">{small}</p>',
                     f"border-left:6px solid {c};padding:4px 0 4px 24px;display:flex;flex-direction:column;gap:6px",
                     order=i + 1))
slide("basin", "Lưu vực sông Hương tới Kim Long", parts, GIAP, 1.0, [
    "Đây là khu vực nghiên cứu: lưu vực sông Hương tính tới cửa ra Kim Long, ô vuông nhỏ là điểm mục tiêu GloFAS.",
    "Nhóm tự cắt lưu vực từ mô hình số độ cao 30 mét: 1.543 km². Báo cáo trước ghi 2.830 km², nhưng con số đó là cả hệ thống sông Hương, đã gồm sông Bồ 938 km² — sông Bồ nhập ở hạ lưu Kim Long nên nhóm đã đính chính.",
    "Lưu vực chia thành 5 lưu vực con, mưa được gộp theo đúng ranh giới này thay vì theo dải vĩ độ.",
    "Hai hồ lớn Tả Trạch và Bình Điền có dung tích 646 và 424 triệu m³; GloFAS không mô phỏng hai hồ này, nên nhóm có thêm luật nâng sàn khi hồ xả.",
    "Phân tích khám phá trên 6.087 ngày: dòng chảy rất lệch, trung vị chỉ 49,7 nhưng cực đại 3.588 m³/s; bốn tháng 9 đến 12 chiếm 58,6 % dòng chảy năm — đó là mùa lũ mà mô hình phải làm tốt.",
])

# ------------------------------------------------------------------ 5 data & scale
parts = []
src = [("ERA5 · reanalysis · giờ · 64 ô", 6.544896), ("IMERG · NASA · 30 phút · 100 ô", 50.477),
       ("GSMaP-GC · JAXA · giờ · 100 ô", 25.2418), ("GSMaP_NRT · JAXA · giờ · 100 ô", 25.2456)]
bx, bw = 640, 820
for i, (n, v) in enumerate(src):
    y = Y0 + i * 118
    w = bw * v / 50.477
    parts.append(SVG(X0 + bx, y, int(w) + 2, 72, hbar(0, 4, w, 64, BLUE), f"{n}: {v:.1f} triệu dòng", order=i + 1, anim="left"))
    parts.append(P(X0, y + 18, 610, n, 28, INK, "right", order=i + 1))
    parts.append(P(X0 + bx + w + 18, y + 14, 260, f"{v:.1f} triệu", 32, INK, bold=True, order=i + 1))
parts.append(P(X0, Y0 + 480, CW, "Tổng ≈ 107.5 triệu bản ghi giờ · 1998–2026 · Parquet chia theo nguồn / năm / tháng", 32, BLUE, bold=True, order=5))
parts.append(P(X0, Y0 + 540, CW, "Thêm: ERA5-Land (độ ẩm đất) · IBTrACS 417 cơn bão · không khí lạnh · ENSO (ONI trễ 3 tháng) · tin xả hồ", 26, MUTED, order=5))
slide("data", "Dữ liệu: mưa theo giờ từ bốn nguồn mở", parts, GIAP, 1.0, [
    "Về dữ liệu: mục tiêu theo ngày, nhưng đầu vào mưa nhóm lấy theo giờ để biết mưa dồn vào lúc nào trong ngày.",
    "ERA5 reanalysis theo giờ, 64 ô phủ lưu vực: 6,5 triệu dòng.",
    "IMERG của NASA, nửa giờ một lần trên lưới 100 ô 0,1 độ: 50,5 triệu dòng.",
    "GSMaP bản hiệu chỉnh theo trạm của JAXA: 25,2 triệu dòng.",
    "Và GSMaP bản gần thời gian thực, nhóm tải thẳng từ máy chủ JAXA: thêm 25,2 triệu dòng.",
    "Tổng khoảng 107,5 triệu bản ghi giờ, 1998 đến 2026, lưu dạng Parquet chia theo nguồn, năm, tháng. Ngoài mưa còn có độ ẩm đất ERA5-Land, 417 cơn bão IBTrACS, không khí lạnh, ENSO và tin xả hồ.",
])

# ------------------------------------------------------------------ 6 pipeline
parts = []
steps = [("1", "Thu thập", "Tác vụ độc lập, bỏ qua file đã có, khoá chống chạy song song"),
         ("2", "Lưu trữ", "Parquet theo nguồn / năm / tháng, giờ Việt Nam"),
         ("3", "Xử lý", "Giờ → ngày → 5 lưu vực con; 54 đặc trưng mưa giờ (Polars; cùng logic trên Spark)"),
         ("4", "Học &amp; đánh giá", "LightGBM E, walk-forward 13 năm, bootstrap + Wilcoxon"),
         ("5", "Vận hành", "Job 05:00 mỗi sáng → nhật ký CSV → dashboard")]
bw5, gp = 296, 46
for i, (n_, h, s_) in enumerate(steps):
    x = X0 + i * (bw5 + gp)
    parts.append(BOX(x, Y0 + 10, bw5,
                     f'<p style="font-family:{SERIF};font-size:48px;font-weight:600;color:{BLUE};line-height:1">{n_}</p>'
                     f'<h3 style="font-size:30px;font-weight:600">{h}</h3>'
                     f'<p style="font-size:25px;color:{MUTED};line-height:1.35">{s_}</p>',
                     f"background:{BG2};border-radius:18px;padding:28px 22px;display:flex;flex-direction:column;gap:12px",
                     order=i + 1, h=360))
    if i < 4:
        parts.append(arrow(x + bw5 - 7, Y0 + 160, order=i + 2, size=40))
parts.append(BOX(X0, 720, CW,
                 '<p style="font-size:27px;line-height:1.45"><b>Mỗi bước tự kiểm được:</b> tổng nhãn 00–23 h trùng mưa ngày '
                 '(lệch ≤ 1.7e-13 mm, dời ±1 h lệch 27.5–47.5 mm) · cắt dữ liệu ở 3 mốc rồi tính lại: ngày trước mốc không đổi · '
                 'Spark = Polars từng bit.</p>',
                 f"background:{CARD};border:1px solid #D9DEE3;border-left:8px solid {TEAL};border-radius:12px;padding:22px 30px",
                 order=6))
slide("pipeline", "Một pipeline, từ tải dữ liệu tới bản tin mỗi sáng", parts, GIAP, 1.0, [
    "Toàn bộ hệ thống là một pipeline năm bước.",
    "Thu thập: mỗi ngày dữ liệu là một tác vụ độc lập, file đã có thì bỏ qua, có khoá chống hai tiến trình ghi cùng lúc — đứt mạng thì chạy lại là tiếp tục.",
    "Lưu trữ: Parquet chia thư mục theo nguồn, năm, tháng, thống nhất giờ Việt Nam.",
    "Xử lý: gộp giờ thành ngày, theo 5 lưu vực con, và tạo 54 đặc trưng mưa giờ như mưa lớn nhất 1, 3, 6 giờ. Bản chính dùng Polars, cùng logic có bản Spark.",
    "Học và đánh giá: LightGBM cấu hình E, kiểm bằng walk-forward 13 năm với bootstrap và Wilcoxon — bạn Đức sẽ trình bày.",
    "Vận hành: job chạy 5 giờ sáng, ghi nhật ký CSV, dashboard đọc nhật ký đó.",
    "Điều nhóm coi trọng là mỗi bước tự kiểm được: tổng 24 nhãn giờ trùng mưa ngày tới 1,7 nhân 10 mũ trừ 13 mm, dời một giờ là lệch hàng chục mm; cắt dữ liệu ở 3 mốc rồi tính lại thì ngày trước mốc không đổi — tức không rò rỉ tương lai; và Spark cho kết quả trùng Polars từng bit.",
])

# ------------------------------------------------------------------ 7 spark ETL full scale
parts = []
parts.append(BOX(X0, Y0, 560,
                 f'<p style="font-family:{SERIF};font-size:80px;font-weight:600;color:{BLUE};line-height:1">101.0 triệu</p>'
                 f'<p style="font-size:26px;color:{MUTED};line-height:1.35">dòng giờ vệ tinh (IMERG + GSMaP-GC + GSMaP_NRT, 125 MB) xử lý trên cụm Spark</p>',
                 "display:flex;flex-direction:column;gap:10px", order=1))
parts.append(BOX(X0, Y0 + 250, 560,
                 f'<p style="font-family:{SERIF};font-size:80px;font-weight:600;color:{TEAL};line-height:1">0 khác biệt</p>'
                 f'<p style="font-size:26px;color:{MUTED};line-height:1.35">6,246,870 giá trị (54 cột đặc trưng giờ): Spark = Polars từng bit</p>',
                 "display:flex;flex-direction:column;gap:10px", order=2))
# chart: seconds per source, Polars vs Spark best (local[8]) vs cluster 2×4
# trung vị seconds_total, cùng container (reports/spark/full_scale_bench.csv): Polars | Spark local[8] driver 4g | cụm 2w×4c
bench = [("IMERG", 16.3, 29.8, 42.6), ("GSMaP-GC", 5.1, 24.1, 31.6), ("GSMaP_NRT", 4.7, 23.3, 30.9)]
W, H = 1000, 470
L, Bm, T = 70, 60, 50
ph = H - T - Bm
mx = 50.0
Yv = lambda v: T + ph * (1 - v / mx)  # noqa: E731
grid = "".join(f'<line x1="{L}" x2="{W}" y1="{Yv(v):.1f}" y2="{Yv(v):.1f}" stroke="#D9DEE3" stroke-width="1"/>' for v in (0, 10, 20, 30, 40, 50))
cx0 = X0 + 660
parts.append(SVG(cx0, Y0 - 10, W, H, grid, "trục"))
parts += [P(cx0, Y0 - 10 + Yv(v) - 14, L - 12, str(v), 22, MUTED, "right") for v in (0, 10, 20, 30, 40, 50)]
parts.append(P(cx0 + L, Y0 - 10 + 4, 760, "giây (trung vị các lần chạy, cùng container)", 22, MUTED))
gw = (W - L) / 3
lay = {1: "", 2: ""}
for i, (nm, pol, spk, clu) in enumerate(bench):
    gx = L + i * gw + 40
    parts.append(P(cx0 + gx - 10, Y0 - 10 + H - Bm + 12, 260, nm, 24, INK, "center", bold=True))
    for j, (v, c, k) in enumerate(((pol, TEAL, 3), (spk, BLUE, 3), (clu, "#9DB9D8", 3))):
        x = gx + j * 82
        lay.setdefault(k, "")
        lay[k] += rbar(x, Yv(v), 70, Yv(0) - Yv(v), c)
        parts.append(P(cx0 + x - 15, Y0 - 10 + Yv(v) - 34, 100, f"{v:.1f}", 22, INK, "center", bold=(j == 0), order=3))
parts.append(SVG(cx0, Y0 - 10, W, H, lay[3], "Polars và Spark theo nguồn", order=3, anim="rise"))
leg = [("Polars", TEAL), ("Spark local[8]", BLUE), ("Cụm 2 worker × 4 lõi", "#9DB9D8")]
lx = cx0 + L
for nm, c in leg:
    parts.append(BOX(lx, Y0 + H + 4, 300, f'<span style="display:inline-block;width:22px;height:22px;border-radius:4px;background:{c};vertical-align:-3px"></span>'
                     f'<span style="font-size:24px;margin-left:10px">{nm}</span>', "", order=3, anim="fade"))
    lx += 300
parts.append(P(X0, 820, CW, "Polars nhanh hơn Spark 1.8 / 4.7 / 5.0 lần; 2 worker không nhanh hơn 1. Dữ liệu vừa RAM một máy, cụm chạy trên một máy vật lý — Spark chứng minh tính đúng.",
               27, INK, bold=True, order=4))
slide("spark_etl", "Spark ở quy mô đủ: toàn bộ lưu trữ vệ tinh", parts, GIAP, 1.2, [
    "Thầy yêu cầu xử lý phân tán, nên nhóm dựng cụm Spark thật: một master, hai worker mỗi worker 4 lõi, trên Docker, Spark 4.1.3.",
    "Sau Report 4, nhóm chạy ETL đặc trưng giờ cho toàn bộ lưu trữ vệ tinh: 101 triệu dòng giờ của IMERG, GSMaP-GC và GSMaP_NRT, 125 MB.",
    "Kết quả đúng là điều quan trọng nhất: nhóm so 6.246.870 giá trị của 54 cột đặc trưng giữa Spark và Polars — trùng từng bit.",
    "Về tốc độ thì nhóm nói thẳng: đo trong cùng container, lấy trung vị các lần chạy, Polars mất 16,3 giây cho IMERG, Spark local 8 lõi 29,8 giây, cụm hai worker 42,6 giây; với GSMaP chênh còn lớn hơn.",
    "Tức Polars nhanh hơn 1,8; 4,7 và 5 lần, và thêm worker thứ hai không nhanh hơn. Lý do: dữ liệu 125 MB vừa RAM một máy, và cả cụm chạy trên một máy vật lý nên chỉ phân tán về giao thức. Giá trị của Spark ở đây là chứng minh pipeline đúng khi tách executor, sẵn sàng khi dữ liệu vượt RAM — không phải để nhanh hơn.",
])

# ------------------------------------------------------------------ 8 spark walk-forward
parts = []
rows = [("Nối tiếp (tổng thời gian 141 tác vụ)", 2081.4, GRAY), ("Pool 8 tiến trình, một máy", 329.9, "#9DB9D8"),
        ("Spark cụm 2 worker × 4 lõi = 8 lõi", 270.7, BLUE)]
bx, bw = 560, 860
for i, (n, v, c) in enumerate(rows):
    y = Y0 + i * 120
    w = bw * v / 2081.4
    parts.append(SVG(X0 + bx, y, int(w) + 2, 72, hbar(0, 4, w, 64, c), f"{n}: {v} s", order=i + 1, anim="left"))
    parts.append(P(X0, y + 16, 530, n, 27, INK, "right", order=i + 1))
    parts.append(P(X0 + bx + w + 18, y + 14, 260, f"{v:,.0f} s", 32, INK, bold=True, order=i + 1))
parts.append(BOX(X0, Y0 + 390, 800,
                 f'<p style="font-family:{SERIF};font-size:72px;font-weight:600;color:{BLUE};line-height:1">7.7×</p>'
                 f'<p style="font-size:26px;color:{MUTED};line-height:1.35">nhanh hơn nối tiếp trên 8 lõi — mỗi lượt (cấu hình × năm × seed) độc lập, ~15 s CPU</p>',
                 "display:flex;flex-direction:column;gap:8px", order=3))
parts.append(BOX(X0 + 864, Y0 + 390, 800,
                 f'<p style="font-family:{SERIF};font-size:72px;font-weight:600;color:{TEAL};line-height:1">2.3e-13</p>'
                 f'<p style="font-size:26px;color:{MUTED};line-height:1.35">lệch lớn nhất giữa dự báo trên cụm và local — 141 lượt, 154,494 giá trị</p>',
                 "display:flex;flex-direction:column;gap:8px", order=4))
slide("spark_wf", "Spark có lợi thật: walk-forward song song theo tác vụ", parts, GIAP, 1.0, [
    "Vậy Spark có lợi ở đâu? Nhóm tìm ra: ở walk-forward, khi đơn vị công việc là một lượt huấn luyện độc lập.",
    "Walk-forward thử giảm cắt ngọn gồm 141 lượt LightGBM, mỗi lượt là một cấu hình, một năm test, một seed. Chạy nối tiếp tổng cộng khoảng 2.081 giây.",
    "Pool 8 tiến trình trên một máy: 330 giây.",
    "Cùng hàm đó gửi lên cụm Spark 8 lõi: 271 giây — nhanh hơn chạy nối tiếp 7,7 lần, khoảng 96 % mức lý tưởng trên 8 lõi, vì mỗi tác vụ khoảng 15 giây CPU, lớn hơn nhiều so với chi phí khởi động.",
    "Và vẫn đúng: 141 lượt, 154.494 dự báo, lệch lớn nhất giữa cụm và local chỉ 2,3 nhân 10 mũ trừ 13 — sai số làm tròn số thực. Bài học: Spark có lợi khi song song theo tác vụ, không phải ở ETL dữ liệu nhỏ.",
])

# ------------------------------------------------------------------ 9 operational job
parts = []
flow = [("05:00 VN", "GitHub Actions (cron 20:00 UTC)"),
        ("Tải dữ liệu", "GloFAS phát báo + thời tiết dự báo, ~130 ngày gần nhất"),
        ("88 cột", "dựng bằng cùng mã với panel lịch sử"),
        ("LightGBM E", "đóng băng · 3 seed × 3 horizon · nâng sàn khi hồ xả"),
        ("p_level1", "isotonic trên 9,862 ngày OOF · báo khi ≥ 0.091 = 1/11"),
        ("Nhật ký CSV", "reports/forecast_log/ · commit · dashboard đọc")]
bw6, gp6 = 250, 33
for i, (h, s_) in enumerate(flow):
    x = X0 + i * (bw6 + gp6)
    c = BLUE if i in (3, 4) else INK
    parts.append(BOX(x, Y0, bw6,
                     f'<h3 style="font-size:28px;font-weight:600;color:{c}">{h}</h3>'
                     f'<p style="font-size:24px;color:{MUTED};line-height:1.35">{s_}</p>',
                     f"background:{BG2};border-radius:16px;padding:22px 18px;display:flex;flex-direction:column;gap:10px",
                     order=1 if i < 3 else 2, h=250))
    if i < 5:
        parts.append(arrow(x + bw6 - 13, Y0 + 100, order=1 if i < 2 else 2, size=34))
parts.append(BOX(X0, Y0 + 300, 808,
                 f'<h3 style="font-size:28px;font-weight:600;color:{TEAL}">Trạng thái</h3>'
                 + ul(["Nhật ký từ 15/09/2026: 56 bản phát tới 10/11 (mất 20/09 do lỗi múi giờ, không điền bù); có LightGBM từ 02/11",
                       "<b>10/11/2026: cảnh báo mức 1 đầu tiên</b> cho 11/11 — GloFAS 970, LightGBM 817 m³/s (mức 1 = 806), P = 0.21 &gt; 1/11"], 24, 8),
                 card_style(TEAL, pad=26, gap=10), order=3, h=290))
parts.append(BOX(X0 + 856, Y0 + 300, 808,
                 f'<h3 style="font-size:28px;font-weight:600;color:{ORANGE}">Đầu vào chạy thật khác lúc học</h3>'
                 + ul(["Mưa ngày t là mưa <b>dự báo</b>, không phải reanalysis",
                       "Độ ẩm đất giữ giá trị cuối; tải bão lỗi = coi như không có bão",
                       "⇒ NSE báo cáo là <b>cận trên</b> của chất lượng chạy thật"], 24, 8),
                 card_style(ORANGE, pad=26, gap=10), order=4, h=290))
slide("ops", "Hệ thống vận hành: bản tin tự động mỗi sáng", parts, GIAP, 1.2, [
    "Phần cuối của em là hệ thống vận hành.",
    "Mỗi sáng khoảng 5 giờ, GitHub Actions chạy job: tải bản phát GloFAS và thời tiết dự báo khoảng 130 ngày gần nhất, rồi dựng đúng 88 cột đặc trưng bằng chính mã đã dùng cho dữ liệu lịch sử — để tránh lệch giữa lúc học và lúc chạy.",
    "Sau đó chạy LightGBM E đã đóng băng, 3 seed cho mỗi horizon, áp luật nâng sàn khi hồ xả, và tính xác suất vượt mức 1 đã hiệu chỉnh isotonic trên 9.862 ngày ngoài mẫu; báo động khi xác suất từ 1 phần 11 trở lên. Kết quả ghi thành CSV và commit vào repo.",
    "Trạng thái hiện tại: nhật ký có từ 15/09/2026, 56 bản phát tới hôm nay; ngày 20/09 mất do lỗi múi giờ và nhóm không điền bù. Mô hình phát hành ở release model-v1.0 và chạy trên GitHub Actions từ 02/11. Sáng nay, 10/11, hệ thống phát cảnh báo mức 1 đầu tiên cho ngày 11/11: GloFAS thô 970, LightGBM 817 mét khối mỗi giây, đều trên mức 1 là 806; xác suất đã hiệu chỉnh 0,21, cao hơn ngưỡng 1 phần 11. Đúng hay sai phải chờ GloFAS tái phân tích những ngày này, nên nhóm chưa kết luận tiêu chí AC-3.",
    "Và một điều nhóm phải nói rõ: đầu vào lúc chạy thật khác lúc học. Mưa ngày t là mưa dự báo, độ ẩm đất giữ giá trị cuối. Vì vậy các con số NSE bạn Đức sắp trình bày là cận trên của chất lượng chạy thật.",
])

# ------------------------------------------------------------------ 10 dashboard
parts = [IMG(X0, Y0 - 20, 808, "dash_slide_du_bao.png", "Dashboard tab Dự báo, bản phát 10/11/2026", order=1, h=490),
         IMG(X0 + 856, Y0 - 20, 808, "dash_slide_ban_do.png", "Dashboard tab Bản đồ lưu vực", order=2, h=490)]
tabs = [("Dự báo", "30 ngày qua + 1–3 ngày tới: GloFAS thô, LightGBM, sàn hồ; 3 mức nguy cơ"),
        ("Bản đồ lưu vực", "5 lưu vực con tô theo mức của ngày chọn — một mức chung toàn lưu vực"),
        ("Giải thích &amp; hạn chế", "SHAP theo nhóm, NSE test / walk-forward / persistence, các hạn chế")]
for i, (h, s_) in enumerate(tabs):
    parts.append(BOX(X0 + i * 568, Y0 + 510, 528,
                     f'<p style="font-size:26px;font-weight:600">{h}</p><p style="font-size:24px;color:{MUTED};line-height:1.35">{s_}</p>',
                     "display:flex;flex-direction:column;gap:6px", order=i + 1))
parts.append(P(X0, Y0 + 660, CW, f'<b style="color:{BLUE}">dsp391m-huong-flood.streamlit.app</b> · tự cập nhật khi job commit · sản phẩm học thuật, không phải bản tin cảnh báo chính thức',
               24, MUTED, order=4))
slide("dashboard", "Dashboard: bản phát 10/11 báo mức nguy cơ 1", parts, GIAP, 0.8, [
    "Người dùng xem kết quả qua dashboard Streamlit, đọc trực tiếp nhật ký dự báo.",
    "Tab Dự báo: 30 ngày đã qua và 1 đến 3 ngày tới, có đường GloFAS thô, GloFAS nâng sàn hồ và LightGBM, cùng ba đường mức nguy cơ. Ảnh là bản phát sáng nay: cả GloFAS thô và LightGBM cùng vượt mức nguy cơ 1 cho ngày mai.",
    "Tab Bản đồ: 5 lưu vực con tô màu theo mức nguy cơ của ngày chọn. Nhóm ghi rõ đây là một mức chung cho cả lưu vực tại Kim Long, không phải dự báo riêng từng lưu vực con.",
    "Tab Giải thích và hạn chế: tỉ trọng SHAP theo nhóm, các chỉ số NSE và danh sách hạn chế.",
    "Dashboard tự cập nhật khi job commit, và ghi rõ trên mọi trang: sản phẩm học thuật, không phải bản tin cảnh báo chính thức. Em xin chuyển lời cho bạn Đức trình bày mô hình và đánh giá.",
])

# =============================================================================================
# PHẦN 2 — ĐỨC: đặc trưng, mô hình, đánh giá, cảnh báo, SHAP
# =============================================================================================

# ------------------------------------------------------------------ 11 features & leakage
parts = []
cfg = [("A", "66", "Report 2: lưu lượng trễ, mưa ERA5, mùa"), ("B", "", "+ mưa từ 1997: train 4,550 → 9,298 ngày"),
       ("C", "70", "+ độ ẩm đất ERA5-Land"), ("D", "73", "+ đại diện mực nước hồ"),
       ("E", "88", "+ bão, không khí lạnh, ENSO")]
for i, (k, nf, s_) in enumerate(cfg):
    y = Y0 + i * 96
    c = BLUE if k == "E" else INK
    parts.append(BOX(X0, y, 800,
                     f'<p style="font-family:{SERIF};font-size:44px;font-weight:600;color:{c};width:56px">{k}</p>'
                     f'<p style="font-size:26px;line-height:1.3;color:{c}">{s_}{f" <span style=color:{MUTED}>({nf} cột)</span>" if nf else ""}</p>',
                     "display:flex;gap:20px;align-items:center;border-bottom:1px solid #D9DEE3;padding-bottom:12px",
                     order=1))
guard = ["<b>Chia theo thời gian</b>: train ≤ 2015 · valid → 06/2022 · test ≥ 07/2022 (1,522 ngày)",
         "<b>Walk-forward</b> 13 năm 2013–2025, train mở rộng, gap 3 ngày, ngưỡng mức 1 tính lại từ train từng fold",
         "<b>Test rò rỉ</b> (AC-5): bộ test tự động xanh và NSE &lt; 0.98 — NSE &gt; 0.98 là dấu hiệu nhìn thấy tương lai",
         "<b>So sánh có kiểm định</b>: CI 95 % bootstrap theo fold + Wilcoxon; chênh &lt; 0.01 NSE coi là nhiễu"]
parts.append(BOX(X0 + 856, Y0, 808, f'<h3 style="font-size:30px;font-weight:600;color:{TEAL}">Chống rò rỉ &amp; so sánh công bằng</h3>' + ul(guard, 25, 12),
                 card_style(TEAL, pad=30), order=2, h=480))
parts.append(P(X0, 800, CW, "Mọi lựa chọn (cấu hình, hàm mất mát, ngưỡng) chọn bằng valid / walk-forward — không nhìn test.", 28, INK, bold=True, order=3))
slide("features", "Đặc trưng A → E và hàng rào chống rò rỉ", parts, DUC, 1.2, [
    "Em là Hồ Anh Đức, em trình bày mô hình và đánh giá. Trước hết là đặc trưng.",
    "Nhóm xây đặc trưng theo năm nấc, mỗi nấc thêm một nhóm dữ liệu: A là bộ Report 2 với 66 cột; B kéo dài mưa về 1997 nên số ngày train tăng từ 4.550 lên 9.298; C thêm độ ẩm đất; D thêm đại diện mực nước hồ; E thêm bão, không khí lạnh và ENSO — tổng 88 cột.",
    "Với chuỗi thời gian, rủi ro lớn nhất là rò rỉ tương lai. Nhóm chia theo thời gian: train đến 2015, valid đến 06/2022, test từ 07/2022 với 1.522 ngày. Ngoài ra kiểm walk-forward 13 năm, cách 3 ngày giữa train và test. Có bộ test rò rỉ tự động, và NSE trên 0,98 bị coi là dấu hiệu rò rỉ chứ không phải thành tích. Và mọi so sánh đều có khoảng tin cậy bootstrap theo fold và kiểm định Wilcoxon; chênh dưới 0,01 NSE nhóm coi là nhiễu.",
    "Nguyên tắc chung: mọi lựa chọn đều làm trên valid hoặc walk-forward, không nhìn tập test.",
])

# ------------------------------------------------------------------ 12 model E
parts = []
parts.append(BOX(X0, Y0, 760,
                 f'<h3 style="font-family:{SERIF};font-size:44px;font-weight:600;color:{BLUE}">LightGBM cấu hình E</h3>'
                 + ul(["88 đặc trưng · một mô hình cho mỗi horizon h1, h2, h3",
                       "600 cây · learning rate 0.05 · 31 lá · min_child_samples 30",
                       "Trung bình 3 seed",
                       "Hàm mất mát: <b>L1 ở h1</b>, <b>L2 ở h2–h3</b>",
                       "Đóng băng ngày 02/11/2026"], 27, 12),
                 card_style(BLUE, pad=34), order=1, h=520))
# chart: ΔNSE L2 vs L1 per horizon (walk-forward)
dl = [("h1", 0.018, "p 0.22"), ("h2", 0.039, "p 0.003"), ("h3", 0.036, "p 0.002")]
W, H = 800, 400
L, T, Bm = 80, 30, 60
ph = H - T - Bm
Yd = lambda v: T + ph * (1 - v / 0.05)  # noqa: E731
grid = "".join(f'<line x1="{L}" x2="{W}" y1="{Yd(v):.1f}" y2="{Yd(v):.1f}" stroke="{"#9AA3AE" if v == 0 else "#D9DEE3"}" stroke-width="1"/>' for v in (0, 0.01, 0.02, 0.03, 0.04, 0.05))
cx0, cy0 = X0 + 864, Y0 + 60
parts.append(P(X0 + 864, Y0, 800, "Vì sao L2 ở h2–h3: ΔNSE (L2 − L1), walk-forward 13 năm", 26, INK, bold=True, order=2))
parts.append(SVG(cx0, cy0, W, H, grid, "trục", order=2))
parts += [P(cx0, cy0 + Yd(v) - 13, L - 12, f"+{v:.2f}" if v else "0", 20, MUTED, "right", order=2) for v in (0, 0.01, 0.02, 0.03, 0.04, 0.05)]
bars = ""
for i, (h, v, p) in enumerate(dl):
    x = L + 60 + i * 230
    bars += rbar(x, Yd(v), 120, Yd(0) - Yd(v), BLUE if i else "#9DB9D8")
    parts.append(P(cx0 + x - 40, cy0 + Yd(v) - 66, 200, f"+{v:.3f}", 26, INK, "center", bold=bool(i), order=2))
    parts.append(P(cx0 + x - 40, cy0 + Yd(v) - 36, 200, p, 22, MUTED, "center", order=2))
    parts.append(P(cx0 + x - 40, cy0 + H - Bm + 12, 200, h, 26, INK, "center", bold=True, order=2))
parts.append(SVG(cx0, cy0, W, H, bars, "ΔNSE L2 so với L1", order=2, anim="rise"))
parts.append(P(X0 + 864, Y0 + 480, 800, "Chỉ đổi sang L2 ở horizon có cải thiện ý nghĩa — h1 giữ L1.", 25, INK, order=3))
slide("model", "Mô hình chính: LightGBM cấu hình E", parts, DUC, 1.0, [
    "Mô hình chính là LightGBM, phù hợp với dữ liệu bảng khoảng chín nghìn ngày, huấn luyện nhanh và giải thích được bằng SHAP.",
    "Cấu hình E: 88 đặc trưng, một mô hình riêng cho mỗi horizon; 600 cây, learning rate 0,05, 31 lá, min_child_samples 30; lấy trung bình 3 seed. Hàm mất mát L1 ở h1 và L2 ở h2–h3. Mô hình đóng băng ngày 02/11/2026.",
    "Vì sao lại L1 và L2 khác nhau? Nhóm so trên walk-forward 13 năm: đổi sang L2 tăng NSE h2 thêm 0,039 với p 0,003 và h3 thêm 0,036 với p 0,002; còn ở h1 chỉ tăng 0,018, p 0,22 — không có ý nghĩa.",
    "Nên nhóm chỉ đổi sang L2 ở nơi cải thiện có ý nghĩa thống kê, h1 giữ L1. Lựa chọn này làm trên walk-forward, không theo tập test.",
])

# ------------------------------------------------------------------ 13 baselines & AC-1
res = [("1 ngày", 0.542, 0.747, 0.70, "Đạt", TEAL), ("2 ngày", 0.008, 0.499, 0.40, "Đạt", TEAL),
       ("3 ngày", -0.198, 0.236, 0.25, "Trượt 0.014", ORANGE)]
W, H = 1260, 560
L, T, Bm = 100, 30, 70
ph = H - T - Bm
lo, hi = -0.3, 0.9
Yr = lambda v: T + ph * (hi - v) / (hi - lo)  # noqa: E731
gw = (W - L) / 3
ox, oy = X0, Y0 - 10
grid = "".join(f'<line x1="{L}" x2="{W}" y1="{Yr(v):.1f}" y2="{Yr(v):.1f}" stroke="{"#9AA3AE" if v == 0 else "#D9DEE3"}" stroke-width="{2 if v == 0 else 1}"/>'
               for v in (-0.2, 0, 0.2, 0.4, 0.6, 0.8))
parts = [SVG(ox, oy, W, H, grid, "trục")]
parts += [P(ox, oy + Yr(v) - 14, L - 14, num(v, 1), 22, MUTED, "right") for v in (-0.2, 0, 0.2, 0.4, 0.6, 0.8)]
parts.append(P(ox + L + 8, oy + 2, 200, "NSE test", 22, MUTED))
layers = {1: "", 2: "", 3: ""}
labels = []
for i, (g, base, mod, t, verdict, vc) in enumerate(res):
    gx = L + i * gw + gw / 2
    parts.append(P(ox + gx - 100, oy + H - Bm + 14, 200, g, 28, INK, "center", bold=True))
    for j, (v, c, k) in enumerate(((base, GRAY, 1), (mod, BLUE, 2))):
        x = gx - 120 + j * 124
        layers[k] += rbar(x, Yr(v), 112, Yr(0) - Yr(v), c) if v >= 0 else rbar_down(x, Yr(0), 112, Yr(v) - Yr(0), c)
        ty = (Yr(v) - 38) if v >= 0 else (Yr(v) + 6)
        labels.append(P(ox + x - 20, oy + ty, 152, num(v), 26, INK, "center", bold=(k == 2), order=k, bg=LIGHT))
    layers[3] += f'<line x1="{gx-140:.1f}" x2="{gx+140:.1f}" y1="{Yr(t):.1f}" y2="{Yr(t):.1f}" stroke="{ORANGE}" stroke-width="4" stroke-dasharray="12 8"/>'
    parts.append(P(ox + gx - 140, oy + 24, 280, verdict, 26, vc, "center", bold=True, order=3))
parts.append(SVG(ox, oy, W, H, layers[1], "persistence", order=1, anim="rise"))
parts.append(SVG(ox, oy, W, H, layers[2], "LightGBM E", order=2, anim="rise"))
parts.append(SVG(ox, oy, W, H, layers[3], "ngưỡng AC-1", order=3))
parts += labels
lg = [("Persistence (Q hôm nay)", GRAY, 1), ("LightGBM E", BLUE, 2), ("Mục tiêu AC-1: 0.70 / 0.40 / 0.25", ORANGE, 3)]
for i, (nm, c, o) in enumerate(lg):
    parts.append(BOX(X0 + 1300, Y0 + 10 + i * 64, 364,
                     f'<span style="display:inline-block;width:26px;height:{6 if o == 3 else 26}px;background:{c};border-radius:3px;vertical-align:middle"></span>'
                     f'<span style="font-size:24px;margin-left:12px;vertical-align:middle">{nm}</span>', "", order=o, anim="fade"))
parts.append(BOX(X0 + 1300, Y0 + 230, 364,
                 f'<p style="font-size:25px;line-height:1.4;color:{MUTED}">h1: RMSE thấp hơn persistence <b style="color:{INK}">25.6 %</b> (AC-1 cần ≥ 20 %).<br>'
                 f'Khí hậu 0.097 · ARIMA −0.093 · seasonal naive −0.434.</p>', "", order=4))
slide("baselines", "So với baseline và tiêu chí AC-1 (test từ 07/2022)", parts, DUC, 1.4, [
    "Kết quả trên tập test từ 07/2022, mô hình chưa từng thấy. NSE bằng 1 là hoàn hảo, bằng 0 là không hơn trung bình.",
    "Cột xám là persistence — lấy lưu lượng hôm nay làm dự báo, baseline khó nhất ở h1: 0,542; ở h2 gần bằng 0, ở h3 âm.",
    "Cột xanh là LightGBM E: 0,747; 0,499 và 0,236. Hơn persistence ở cả ba horizon, khoảng cách lớn nhất ở h2–h3 — đúng chỗ persistence sụp.",
    "Vạch cam là tiêu chí AC-1 đặt từ đầu dự án: 0,70; 0,40; 0,25. h1 và h2 đạt. h3 đạt 0,236, thiếu 0,014 so với 0,25 — nhóm nói thẳng là h3 trượt AC-1. Lý do: 2–3 ngày trước đỉnh lũ, mưa gây lũ phần lớn chưa rơi lúc phát báo.",
    "Thêm hai điểm: ở h1, RMSE thấp hơn persistence 25,6 %, đạt điều kiện từ 20 % trở lên của AC-1. Các baseline khác như khí hậu, ARIMA, seasonal naive đều kém hơn persistence.",
])

# ------------------------------------------------------------------ 14 walk-forward
wfE1 = [0.792, 0.907, 0.810, 0.796, 0.795, 0.634, 0.481, 0.884, 0.797, 0.681, 0.759, 0.705, 0.853]
wfE2 = [0.368, 0.508, 0.352, 0.374, 0.458, 0.394, 0.376, 0.519, 0.371, 0.394, 0.505, 0.502, 0.559]
wfP1 = [0.490, 0.463, 0.568, 0.471, 0.574, 0.614, 0.552, 0.661, 0.531, 0.332, 0.624, 0.467, 0.619]
wfP2 = [-0.120, -0.180, -0.088, -0.294, 0.014, 0.075, -0.137, 0.196, -0.216, -0.449, 0.103, -0.111, 0.117]
yrs = list(range(2013, 2026))
W, H = 1300, 560
L, R, T, Bm = 90, 20, 20, 60
pw, ph = W - L - R, H - T - Bm
lo, hi = -0.5, 1.0
Xw = lambda i: L + pw * i / 12  # noqa: E731
Yw = lambda v: T + ph * (hi - v) / (hi - lo)  # noqa: E731
ox, oy = X0, Y0 - 10
grid = "".join(f'<line x1="{L}" x2="{L+pw}" y1="{Yw(v):.1f}" y2="{Yw(v):.1f}" stroke="{"#9AA3AE" if v == 0 else "#D9DEE3"}" stroke-width="1"/>' for v in (-0.5, -0.25, 0, 0.25, 0.5, 0.75, 1))
parts = [SVG(ox, oy, W, H, grid, "trục")]
parts += [P(ox, oy + Yw(v) - 13, L - 14, num(v, 2), 20, MUTED, "right") for v in (-0.5, 0, 0.5, 1)]
parts += [P(ox + Xw(i) - 40, oy + H - Bm + 12, 80, str(y), 20, MUTED, "center") for i, y in enumerate(yrs) if y % 2 == 1]


def series(d, c, wd, dash=""):
    pts = " L".join(f"{Xw(i):.1f},{Yw(v):.1f}" for i, v in enumerate(d))
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="M{pts}" fill="none" stroke="{c}" stroke-width="{wd}"{da}/>' + "".join(
        f'<circle cx="{Xw(i):.1f}" cy="{Yw(v):.1f}" r="5" fill="{c}" stroke="{LIGHT}" stroke-width="2"/>' for i, v in enumerate(d)))


parts.append(SVG(ox, oy, W, H, series(wfP1, GRAY, 3) + series(wfP2, GRAY, 2, "8 6"), "persistence h1 và h2", order=1, anim="fade"))
parts.append(SVG(ox, oy, W, H, series(wfE1, BLUE, 4), "LightGBM E h1", order=2, anim="fade"))
parts.append(SVG(ox, oy, W, H, series(wfE2, ORANGE, 4), "LightGBM E h2", order=3, anim="fade"))
leg = [("Persistence h1", GRAY, "", 1), ("Persistence h2", GRAY, "8 6", 1), ("LightGBM E h1", BLUE, "", 2), ("LightGBM E h2", ORANGE, "", 3)]
for i, (nm, c, da, o) in enumerate(leg):
    dd = f' stroke-dasharray="{da}"' if da else ""
    parts.append(BOX(X0 + 1340, Y0 + i * 52, 330,
                     f'<svg width="40" height="20" style="display:inline-block;vertical-align:middle"><line x1="0" x2="40" y1="10" y2="10" stroke="{c}" stroke-width="4"{dd}/></svg>'
                     f'<span style="font-size:25px;margin-left:10px;vertical-align:middle">{nm}</span>', "", order=o, anim="fade"))
parts.append(BOX(X0 + 1340, Y0 + 240, 324,
                 f'<p style="font-size:24px;color:{MUTED};line-height:1.35">Trung bình 13 năm</p>'
                 f'<p style="font-size:26px;line-height:1.4"><b style="color:{BLUE}">E: 0.761 / 0.437 / 0.206</b><br>Persistence: 0.536 / −0.084 / −0.361</p>'
                 f'<p style="font-size:24px;color:{MUTED};line-height:1.35">E h1 hơn persistence 12/13 năm (trừ 2019); h2, h3 hơn cả 13 năm</p>',
                 "display:flex;flex-direction:column;gap:8px", order=4))
slide("walkforward", "Walk-forward 13 năm 2013–2025: kết quả đứng vững", parts, DUC, 1.3, [
    "Một tập test chỉ có 4 mùa lũ, có thể may mắn. Nên nhóm kiểm walk-forward: lần lượt coi mỗi năm 2013 đến 2025 là năm chưa biết, huấn luyện trên mọi năm trước đó rồi dự báo.",
    "Hai đường xám là persistence: liền là h1, đứt là h2 — h2 dao động quanh 0, nhiều năm âm.",
    "Đường xanh là LightGBM E ở h1: cao hơn persistence ở 12 trên 13 năm; riêng 2019 thấp hơn, 0,481 so với 0,552.",
    "Đường cam là E ở h2: ổn định quanh 0,35 đến 0,56, hơn persistence cả 13 năm.",
    "Trung bình 13 năm: E đạt 0,761; 0,437; 0,206 so với persistence 0,536; âm 0,084; âm 0,361. Ở h3 walk-forward cũng dưới 0,25 — khớp với kết luận trên test.",
])

# ------------------------------------------------------------------ 15 ablation
abl = {"A": (0.745, 0.432, 0.166), "B": (0.766, 0.447, 0.192), "C": (0.757, 0.454, 0.208),
       "D": (0.756, 0.461, 0.199), "E": (0.747, 0.499, 0.236)}
panels = [("h1", 0, 0.60, 0.80, "B: +0.021 (mưa từ 1997)", "B"), ("h2", 1, 0.40, 0.52, "E: +0.038 so với D", "E"),
          ("h3", 2, 0.14, 0.26, "E: +0.037 so với D", "E")]
parts = []
pw_, gap_ = 520, 52
for pi, (hn, idx, lo, hi, msg, best) in enumerate(panels):
    px = X0 + pi * (pw_ + gap_)
    W, H = pw_, 430
    T, Bm = 40, 50
    ph = H - T - Bm
    Ya = lambda v, lo=lo, hi=hi: T + ph * (hi - v) / (hi - lo)  # noqa: E731
    inner = f'<line x1="0" x2="{W}" y1="{T+ph}" y2="{T+ph}" stroke="#9AA3AE" stroke-width="1"/>'
    for j, k in enumerate("ABCDE"):
        v = abl[k][idx]
        x = 20 + j * 100
        c = BLUE if k == best else "#9DB9D8"
        inner += rbar(x, Ya(v), 76, T + ph - Ya(v), c)
        parts.append(P(px + x - 12, Y0 + 40 + Ya(v) - 34, 100, f"{v:.3f}", 21, INK, "center", bold=(k == best), order=pi + 1))
        parts.append(P(px + x - 12, Y0 + 40 + T + ph + 8, 100, k, 24, INK, "center", bold=True, order=pi + 1))
    parts.append(P(px, Y0, pw_, f"{hn} · trục từ {lo:.2f}", 26, INK, bold=True, order=pi + 1))
    parts.append(SVG(px, Y0 + 40, W, H, inner, f"ablation {hn}", order=pi + 1, anim="rise"))
    parts.append(P(px, Y0 + 490, pw_, msg, 25, BLUE, bold=True, order=pi + 1))
parts.append(P(X0, 830, CW, "Hệ thống thời tiết báo trước mưa trước khi mưa rơi ⇒ giúp đúng h2–h3. Độ ẩm đất (C), đại diện hồ (D): không thêm gì rõ. Trung bình 3 seed, sd 0.012.",
               26, INK, bold=True, order=4))
slide("ablation", "Ablation: nhóm dữ liệu nào giúp horizon nào", parts, DUC, 1.2, [
    "Ablation cho biết mỗi nhóm dữ liệu đóng góp gì. Mỗi cột là một cấu hình A đến E trên tập test, trung bình 3 seed. Lưu ý trục mỗi panel không bắt đầu từ 0 để thấy rõ chênh lệch.",
    "Ở h1, bước giúp nhiều nhất là B — kéo dài mưa về 1997, gấp đôi số ngày train: tăng 0,021. E ở h1 thấp hơn B một chút, 0,747 so với 0,766 — đây là đánh đổi có chủ đích, vì h1 của E vẫn trên 0,70.",
    "Ở h2, E thêm bão, không khí lạnh, ENSO: tăng từ 0,461 lên 0,499, tức 0,038 so với D.",
    "Ở h3, E tăng 0,037, lên 0,236.",
    "Diễn giải: hệ thống thời tiết báo trước mưa trước khi mưa rơi, nên giúp đúng ở h2–h3. Còn độ ẩm đất và đại diện hồ không thêm gì rõ. Độ lệch chuẩn giữa seed khoảng 0,012.",
])

# ------------------------------------------------------------------ 16 alerts & calibration
parts = []
parts.append(BOX(X0, Y0 - 10, CW,
                 '<p style="font-size:26px;line-height:1.4"><b>Mức nguy cơ</b> = phân vị 95 / 98 / 99.5 % lưu lượng mùa lũ = '
                 '<b>806 / 1,275 / 1,905 m³/s</b> — <b>không</b> phải BĐ I/II/III (quan hệ H–Q chỉ R² 0.18 trên 12 đợt, chệch −1.94 m).</p>',
                 f"background:{BG2};border-radius:12px;padding:18px 28px", order=1))
hdr = ["Quy tắc báo mức 1 (h1, 13 fold)", "Ngưỡng", "Bỏ sót", "Báo nhầm/năm", "Chi phí 10:1"]
rows_ = [("p ≥ 0.5 (mặc định)", "0.5", "32", "3.1", "360", 2, ""),
         ("Ngưỡng chi phí, xác suất thô", "0.03", "13", "8.4", "239", 3, ""),
         ("Isotonic + ngưỡng Bayes 1/11", "0.091", "12", "8.5", "230", 4, f"color:{BLUE};font-weight:600")]
th = "".join(f'<th style="text-align:{"left" if i == 0 else "right"};font-size:24px;color:{MUTED};font-weight:600">{h}</th>' for i, h in enumerate(hdr))
parts.append(BOX(X0, Y0 + 110, 1000, f'<table style="width:100%;font-size:26px"><tr>{th}</tr></table>', "", order=2, anim="fade"))
for k, (a, b_, c_, d_, e_, o, sty) in enumerate(rows_):
    tds = "".join(f'<td style="text-align:{"left" if i == 0 else "right"};{sty};width:{w}px">{v}</td>'
                  for i, (v, w) in enumerate(zip((a, b_, c_, d_, e_), (420, 120, 120, 170, 170))))
    parts.append(BOX(X0, Y0 + 170 + k * 66, 1000, f'<table style="width:100%;font-size:26px"><tr>{tds}</tr></table>', "", order=o, anim="fade"))
parts.append(P(X0, Y0 + 380, 1000, "Chi phí: một lần bỏ sót = 10 lần báo nhầm. p = 0.5 → ngưỡng chi phí: −34 %, p 0.042.", 24, MUTED, order=3))
parts.append(BOX(X0 + 1060, Y0 + 110, 604,
                 f'<h3 style="font-size:28px;font-weight:600;color:{BLUE}">Hiệu chỉnh isotonic</h3>'
                 f'<p style="font-family:{SERIF};font-size:60px;font-weight:600;line-height:1">0.0119 → 0.0100</p>'
                 f'<p style="font-size:25px;color:{MUTED};line-height:1.35">Brier (p 0.027, tốt hơn 9/13 fold) · ECE 0.010 → 0.002</p>'
                 f'<p style="font-size:25px;line-height:1.4">Chi phí không đổi (239 → 230, p 0.75) vì isotonic giữ thứ hạng. '
                 f'Cái được: <b>xác suất có nghĩa</b>, ngưỡng tối ưu 0.12 ≈ 1/11 = 0.091 ⇒ job dùng thẳng 1/11.</p>',
                 card_style(BLUE, pad=28, gap=12), order=4, h=470))
slide("alerts", "Cảnh báo: ngưỡng theo chi phí + xác suất đã hiệu chỉnh", parts, DUC, 1.6, [
    "Từ dự báo lưu lượng, nhóm đưa ra cảnh báo theo mức nguy cơ.",
    "Mức nguy cơ là phân vị 95, 98 và 99,5 % lưu lượng mùa lũ: 806; 1.275 và 1.905 m³/s. Nhóm không gọi là báo động I, II, III, vì báo động tính theo mét mực nước, mà quan hệ mực nước – lưu lượng nhóm dựng được chỉ có R² 0,18 trên 12 đợt lũ, chệch gần 2 mét.",
    "Bộ phân loại mức 1 ở h1, kiểm trên 13 fold walk-forward. Với ngưỡng mặc định 0,5: bỏ sót 32 ngày lũ, báo nhầm khoảng 3 ngày mỗi năm.",
    "Với cảnh báo lũ, bỏ sót tệ hơn báo nhầm nhiều. Nhóm đặt một lần bỏ sót bằng 10 lần báo nhầm và chọn ngưỡng cho tổng chi phí nhỏ nhất: bỏ sót giảm còn 13, báo nhầm tăng lên 8,4 ngày mỗi năm, tổng chi phí từ 360 xuống 239 — giảm 34 %, p 0,042. Nhưng ngưỡng tối ưu chỉ 0,03 — xác suất thô không có nghĩa thật.",
    "Nên nhóm hiệu chỉnh isotonic, học trên xác suất ngoài mẫu của các năm trước. Brier giảm từ 0,0119 xuống 0,0100, p 0,027, tốt hơn 9 trên 13 fold. Chi phí gần như không đổi, 239 so với 230, p 0,75 — vì isotonic giữ thứ hạng các ngày. Cái được là xác suất có nghĩa: ngưỡng tối ưu về 0,12, sát ngưỡng lý thuyết Bayes 1 phần 11 bằng 0,091 — nên job dùng thẳng 1/11, không phải chọn lại ngưỡng mỗi năm.",
])

# ------------------------------------------------------------------ 17 flood events
ev = [("1 ngày", 28, 27), ("2 ngày", 10, 14), ("3 ngày", 0, 7)]
W, H = 1000, 520
L, T, Bm = 80, 30, 70
ph = H - T - Bm
Ye = lambda v: T + ph * (1 - v / 43)  # noqa: E731
grid = "".join(f'<line x1="{L}" x2="{W}" y1="{Ye(v):.1f}" y2="{Ye(v):.1f}" stroke="#D9DEE3" stroke-width="1"/>' for v in (0, 10, 20, 30, 40))
parts = [SVG(X0, Y0 - 10, W, H, grid, "trục")]
parts += [P(X0, Y0 - 10 + Ye(v) - 13, L - 12, str(v), 20, MUTED, "right") for v in (0, 10, 20, 30, 40)]
parts.append(P(X0 + L + 8, Y0 - 10, 500, "số đợt lũ bắt được / 43 đợt (walk-forward)", 22, MUTED))
lay = {1: "", 2: ""}
gw = (W - L) / 3
for i, (g, e_, p_) in enumerate(ev):
    gx = L + i * gw + gw / 2
    parts.append(P(X0 + gx - 100, Y0 - 10 + H - Bm + 14, 200, g, 26, INK, "center", bold=True))
    for j, (v, c, k) in enumerate(((p_, GRAY, 1), (e_, BLUE, 2))):
        x = gx - 110 + j * 116
        lay[k] += rbar(x, Ye(v), 104, Ye(0) - Ye(v), c)
        parts.append(P(X0 + x - 20, Y0 - 10 + Ye(v) - 36, 144, f"{v}/43", 24, INK, "center", bold=(k == 2), order=k))
parts.append(SVG(X0, Y0 - 10, W, H, lay[1], "persistence", order=1, anim="rise"))
parts.append(SVG(X0, Y0 - 10, W, H, lay[2], "LightGBM E", order=2, anim="rise"))
for i, (nm, c, o) in enumerate((("Persistence", GRAY, 1), ("LightGBM E", BLUE, 2))):
    parts.append(BOX(X0 + 560 + i * 230, Y0 - 6, 230,
                     f'<span style="display:inline-block;width:22px;height:22px;background:{c};border-radius:3px;vertical-align:-3px"></span>'
                     f'<span style="font-size:24px;margin-left:10px">{nm}</span>', "", order=o, anim="fade"))
side = [("15 đợt", "được báo trước ngày lũ bắt đầu — persistence không bao giờ làm được", BLUE, 3),
        ("0.80 / 0.54 / 0.31", "tỉ số đỉnh dự báo / đỉnh thật (trung vị) — cắt ngọn tăng theo horizon", ORANGE, 4),
        ("1 và 0", "đợt báo nhầm ở h2, h3 (persistence: 16 và 29)", TEAL, 4)]
for i, (big, small, c, o) in enumerate(side):
    parts.append(BOX(X0 + 1070, Y0 + i * 175, 594,
                     f'<p style="font-family:{SERIF};font-size:52px;font-weight:600;color:{c};line-height:1">{big}</p>'
                     f'<p style="font-size:25px;color:{MUTED};line-height:1.35">{small}</p>',
                     "display:flex;flex-direction:column;gap:8px", order=o))
slide("events", "Theo đợt lũ: h1 bắt ngang persistence nhưng có báo trước", parts, DUC, 1.2, [
    "NSE là chỉ số trung bình; người dân quan tâm từng đợt lũ. Nhóm gộp các ngày vượt mức 1 liên tiếp thành đợt: walk-forward có 43 đợt.",
    "Cột xám: persistence bắt 27 đợt ở h1, 14 ở h2, 7 ở h3.",
    "Cột xanh: LightGBM E bắt 28 đợt ở h1 — ngang persistence; nhưng chỉ 10 ở h2 và 0 ở h3.",
    "Khác biệt ở h1 là thời gian báo trước: 15 đợt mô hình báo trước khi lũ bắt đầu — persistence chỉ lặp lại hôm nay nên không bao giờ báo trước được.",
    "Vì sao h2–h3 kém? Cắt ngọn: đỉnh dự báo chỉ bằng 0,80; 0,54 và 0,31 lần đỉnh thật, nên ít khi vượt ngưỡng. Mặt khác mô hình gần như không báo nhầm đợt nào ở h2, h3, trong khi persistence báo nhầm 16 và 29 đợt. Cắt ngọn là điểm yếu chính — bạn Huyền sẽ trình bày các thử nghiệm để chữa.",
])

# ------------------------------------------------------------------ 18 SHAP
grp = [("Lưu lượng (trí nhớ sông)", BLUE), ("Mưa", TEAL), ("Hệ thống thời tiết", ORANGE), ("Mùa / lịch", PURPLE), ("Độ ẩm đất", GOLD)]
# seed 42, reports/shap_importance.csv (level=group): flow | rain+rain_long | synoptic+storm+enso | season | soil_api
vals = [("h1", [58.4, 35.5, 3.7, 0.7, 1.8]), ("h2", [26.3, 41.6, 19.2, 7.2, 5.6]), ("h3", [22.8, 30.3, 26.6, 15.6, 4.7])]
parts = []
lx = X0 + 120
leg = ""
for nme, c in grp:
    parts.append(BOX(lx, Y0 - 20, 330, f'<span style="display:inline-block;width:24px;height:24px;background:{c};border-radius:4px;vertical-align:-4px"></span>'
                     f'<span style="font-size:25px;margin-left:10px">{nme}</span>', ""))
    lx += 312
bw = 1500
for i, (k, vs) in enumerate(vals):
    y = Y0 + 50 + i * 122
    inner, xx = "", 0
    tot = sum(vs)
    parts.append(P(X0, y + 22, 100, k, 30, INK, "right", bold=True, order=i + 1))
    labs = []
    for j, v in enumerate(vs):
        w = bw * v / tot
        inner += f'<rect x="{xx:.1f}" y="0" width="{max(w - 2, 0):.1f}" height="84" fill="{grp[j][1]}"/>'
        if w > 80:
            labs.append(P(X0 + 120 + xx, y + 26, w - 2, f"{v:.1f} %", 25, LIGHT, "center", bold=True, order=i + 1))
        xx += w
    parts.append(SVG(X0 + 120, y, bw, 84, inner, f"SHAP {k}", order=i + 1, anim="left"))
    parts += labs
parts.append(BOX(X0, 700, CW,
                 '<p style="font-size:25px;line-height:1.45">Hợp thuỷ văn: càng xa, trí nhớ sông giảm, thời tiết tăng (khí áp/gió 2.3 → 16.3 %). '
                 '<b>Chưa hợp lý, ghi thẳng:</b> độ ẩm đất tác động <b>ngược chiều</b> (trùng thông tin với Q hôm nay); h3 dựa 15.6 % vào lịch. '
                 'Đỉnh 10/2022: GloFAS 1,967, dự báo 862 — chỉ 12/9,283 ngày train cao như vậy.</p>',
                 f"background:{CARD};border:1px solid #D9DEE3;border-left:8px solid {ORANGE};border-radius:12px;padding:20px 28px", order=4))
slide("shap", "SHAP: mô hình dựa vào đâu", parts, DUC, 1.3, [
    "SHAP cho biết mô hình dựa vào nhóm thông tin nào. Đây là tỉ trọng trung bình trị tuyệt đối SHAP theo nhóm, seed 42.",
    "Ở h1, mô hình dựa chủ yếu vào trí nhớ của sông — lưu lượng gần đây chiếm 58,4 %; riêng lưu lượng hôm nay 37,4 %.",
    "Ở h2, mưa chiếm nhiều nhất, 41,6 %, và hệ thống thời tiết tăng lên 19,2 %.",
    "Ở h3, hệ thống thời tiết lên 26,6 %, lưu lượng chỉ còn 22,8 %.",
    "Điều này hợp thuỷ văn: càng dự báo xa, càng phải dựa vào thời tiết — khí áp và gió tăng từ 2,3 lên 16,3 %. Nhưng nhóm ghi thẳng hai điểm chưa hợp lý: độ ẩm đất tác động ngược chiều, vì nó gần như trùng thông tin với lưu lượng hôm nay; và h3 dựa 15,6 % vào lịch. SHAP cũng giải thích cắt ngọn: đỉnh 10/2022 GloFAS 1.967, mô hình chỉ 862, vì trong 9.283 ngày train chỉ 12 ngày có lưu lượng cao như vậy. Em xin chuyển lời cho bạn Huyền.",
])

# =============================================================================================
# PHẦN 3 — HUYỀN: DL, vệ tinh, thử giảm cắt ngọn, hạn chế, hướng tiếp, kết luận
# =============================================================================================

# ------------------------------------------------------------------ 19 DL forest plot
dlrows = [("LSTM L30 (MSE)", [(0.021, -0.014, 0.058), (-0.025, -0.117, 0.032), (-0.026, -0.101, 0.021)], TEAL, 1),
          ("LSTM nhấn đỉnh", [(-0.007, -0.065, 0.037), (-0.107, -0.239, -0.008), (-0.229, -0.411, -0.073)], ORANGE, 2),
          ("MLP nhấn đỉnh", [(0.000, -0.031, 0.037), (-0.065, -0.142, 0.002), (-0.118, -0.255, -0.015)], PURPLE, 2)]
W, H = 1000, 520
L, R, T, Bm = 40, 30, 40, 60
pw = W - L - R
lo, hi = -0.45, 0.10
Xf = lambda v: L + pw * (v - lo) / (hi - lo)  # noqa: E731
cx0, cy0 = X0, Y0 + 10
inner = "".join(f'<line x1="{Xf(v):.1f}" x2="{Xf(v):.1f}" y1="{T}" y2="{H-Bm}" stroke="{"#5A6577" if v == 0 else "#D9DEE3"}" stroke-width="{2 if v == 0 else 1}"/>'
                for v in (-0.4, -0.3, -0.2, -0.1, 0, 0.1))
parts = [SVG(cx0, cy0, W, H, inner, "trục ΔNSE")]
parts += [P(cx0 + Xf(v) - 50, cy0 + H - Bm + 10, 100, sgn(v, 1) if v else "0", 20, MUTED, "center") for v in (-0.4, -0.3, -0.2, -0.1, 0, 0.1)]
parts.append(P(cx0, cy0 - 40, W, "ΔNSE so với LightGBM, walk-forward 13 năm (CI 95 % bootstrap theo fold)", 23, MUTED))
rowh = (H - T - Bm) / 3
lay = {1: "", 2: ""}
for hi_, hn in enumerate(("h1", "h2", "h3")):
    yb = T + hi_ * rowh
    parts.append(P(cx0 + W + 10, cy0 + yb + rowh / 2 - 16, 80, hn, 26, INK, bold=True))
    for mi, (nm, cis, c, o) in enumerate(dlrows):
        m, a, z = cis[hi_]
        y = yb + 26 + mi * 34
        lay[o] += (f'<line x1="{Xf(a):.1f}" x2="{Xf(z):.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{c}" stroke-width="3"/>'
                   f'<circle cx="{Xf(m):.1f}" cy="{y:.1f}" r="8" fill="{c}"/>')
parts.append(SVG(cx0, cy0, W, H, lay[1], "LSTM MSE", order=1))
parts.append(SVG(cx0, cy0, W, H, lay[2], "mô hình nhấn đỉnh", order=2))
for i, (nm, _, c, o) in enumerate(dlrows):
    parts.append(BOX(cx0 + 60 + i * 300, cy0 + H + 10, 300, f'<span style="display:inline-block;width:18px;height:18px;border-radius:50%;background:{c};vertical-align:-2px"></span>'
                     f'<span style="font-size:21px;margin-left:8px">{nm}</span>', "", order=o, anim="fade"))
facts = [("Thua rõ ở h3", "LSTM nhấn đỉnh −0.229, p 0.033", ORANGE, 2),
         ("Kém ổn định", "độ lệch giữa seed: DL 0.03–0.20 · LightGBM 0.01", INK, 3),
         ("Hơn ở h1 theo sự kiện", "CSI mức 1: DL 0.49 · LightGBM 0.44", TEAL, 3),
         ("Phân tán không giúp", "DDP 2 rank cùng NSE, chậm hơn 1 tiến trình · MLlib trên dữ liệu đầy đủ, 13 fold: kém E cả 3 horizon (h1 −0.044 / −0.049, p < 0.05)", INK, 4)]
for i, (h, s_, c, o) in enumerate(facts):
    parts.append(BOX(X0 + 1120, Y0 - 20 + i * 150, 544,
                     f'<p style="font-size:27px;font-weight:600;color:{c}">{h}</p><p style="font-size:24px;color:{MUTED};line-height:1.35">{s_}</p>',
                     "display:flex;flex-direction:column;gap:4px;border-bottom:1px solid #D9DEE3;padding-bottom:12px", order=o))
slide("dl", "Deep learning: không thắng LightGBM một cách vững", parts, HUYEN, 1.5, [
    "Em là Mai Thị Lệ Huyền. Phần của em là những gì nhóm đã thử nghiêm túc nhưng không đưa vào mô hình chính, các hạn chế và hướng tiếp theo. Đầu tiên là deep learning. Biểu đồ cho chênh lệch NSE so với LightGBM qua 13 năm walk-forward, kèm khoảng tin cậy 95 %; vạch đứng là không chênh.",
    "LSTM cửa sổ 30 ngày với hàm MSE: h1 hơn 0,021 nhưng khoảng tin cậy chứa 0; h2, h3 kém khoảng 0,025. Tức là không hơn một cách vững.",
    "Các biến thể nhấn đỉnh lũ còn kém hơn khi xa: LSTM nhấn đỉnh thua rõ ở h3, âm 0,229, p 0,033; MLP nhấn đỉnh cũng thua ở h3.",
    "DL cũng kém ổn định: độ lệch giữa các seed 0,03 đến 0,20, trong khi LightGBM chỉ 0,01. Mặt tích cực: ở h1, DL bắt sự kiện tốt hơn, CSI 0,49 so với 0,44 — đây là manh mối cho thử nghiệm ghép ở slide sau.",
    "Về phân tán: huấn luyện DDP hai rank trên cụm cho cùng NSE nhưng chậm hơn một tiến trình, vì mô hình chỉ khoảng 19 nghìn tham số. MLlib GBT và RF học trên đúng dữ liệu đầy đủ của mô hình E, chạy walk-forward 13 năm trên cụm, đều kém LightGBM ở cả ba horizon, có ý nghĩa thống kê: h1 kém 0,044 và 0,049. Nên nhóm giữ LightGBM.",
])

# ------------------------------------------------------------------ 20 satellite
parts = []
sat = [("GSMaP-GC, có mưa của chính ngày t (nhìn lại)", 0.018, "[+0.008; +0.028] · p 0.008", BLUE, 1),
       ("GSMaP-GC trễ 1 ngày (thực tế: trễ ~27 h)", -0.001, "[−0.007; +0.005] · p 0.84", GRAY, 2)]
x0c = X0 + 760
sc = 30000
for i, (n, v, ci, c, o) in enumerate(sat):
    y = Y0 + 40 + i * 140
    parts.append(P(X0, y + 4, 730, n, 26, INK, "right", order=o))
    parts.append(P(X0, y + 42, 730, ci, 22, MUTED, "right", order=o))
    w = abs(v) * sc
    if v >= 0:
        parts.append(SVG(x0c, y, int(w) + 4, 72, hbar(0, 4, w, 64, c), n, order=o, anim="left"))
        parts.append(P(x0c + w + 16, y + 14, 200, sgn(v), 30, INK, bold=True, order=o))
    else:
        parts.append(SVG(x0c - int(w) - 2, y, int(w) + 4, 72, f'<rect x="0" y="4" width="{w:.1f}" height="64" fill="{c}"/>', n, order=o, anim="fade"))
        parts.append(P(x0c + 16, y + 14, 200, sgn(v), 30, INK, bold=True, order=o))
parts.append(SVG(x0c - 2, Y0 + 20, 4, 300, '<rect x="0" y="0" width="2" height="300" fill="#5A6577"/>', "trục 0"))
parts.append(P(x0c - 100, Y0 - 16, 400, "ΔNSE h3 so với E, 13 fold", 22, MUTED))
parts.append(BOX(X0, Y0 + 360, CW,
                 '<p style="font-size:26px;line-height:1.45"><b>GSMaP_NRT</b> (trễ ~4.7 h, sản phẩm khác, học lại bằng lịch sử NRT): giúp mô hình yếu A '
                 '(+0.009 / +0.019 / +0.012, p ≤ 0.008) nhưng <b>không giúp E</b> (−0.002 / +0.003 / −0.001).</p>',
                 f"background:{BG2};border-radius:12px;padding:20px 28px", order=3))
parts.append(P(X0, Y0 + 520, CW, "⇒ Không đưa mưa vệ tinh vào job hằng ngày. Bài học: một lần chia đánh giá IMERG cao hơn walk-forward (+0.017 → +0.013).",
               27, INK, bold=True, order=4))
slide("satellite", "Mưa vệ tinh: có ích khi nhìn lại, mất khi chạy thật", parts, HUYEN, 1.2, [
    "Thử nghiệm thứ hai là mưa vệ tinh — 100 triệu dòng mà bạn Giáp đã trình bày. Câu hỏi: nó có giúp dự báo không?",
    "Nhìn lại quá khứ thì có: thêm GSMaP-GC có mưa của chính ngày phát báo, h3 tăng 0,018, p 0,008, có ý nghĩa.",
    "Nhưng khi chạy thật, GSMaP trên Earth Engine trễ khoảng 27 giờ, nên lúc 5 giờ sáng chỉ có mưa tới hôm qua. Mô phỏng đúng độ trễ đó, lợi ích về 0: âm 0,001, p 0,84. Toàn bộ lợi ích nằm ở mưa của chính ngày t.",
    "Nhóm thử tiếp bản gần thời gian thực GSMaP_NRT, chỉ trễ khoảng 4,7 giờ, học lại bằng lịch sử NRT. Nó giúp mô hình yếu A ở cả ba horizon với p dưới 0,01, nhưng trên mô hình E thì chênh lệch chỉ quanh 0, không còn lợi ích.",
    "Kết luận: không đưa mưa vệ tinh vào job hằng ngày. Và một bài học phương pháp: một lần chia đánh giá IMERG cao hơn walk-forward — walk-forward là thứ giữ nhóm khỏi kết luận sai.",
])

# ------------------------------------------------------------------ 21 peak experiments
hdr = ["Biến thể (so với E, 13 fold)", "h1 ΔNSE", "h2 ΔNSE", "h3 ΔNSE", "Kết luận"]
pk = [("B1 · trọng số mẫu nhấn đỉnh α = 3", "+0.011 (p 0.13)", "+0.012 (p 0.22)", "+0.001", "Không ý nghĩa; α chọn sau khi xem", 2, INK),
      ("B2 · hiệu chỉnh isotonic sau dự báo", "−0.040", "−0.008", "<b>−0.027 (p 0.001)</b>", "Làm hại: thua 12/13 fold ở h3", 3, RED),
      ("B3 · ghép 50/50 E + LSTM", "<b>+0.029 (p 0.048)</b>", "−0.022", "<b>−0.023 (p 0.021)</b>", "Giúp h1, hại h2–h3", 4, INK)]
parts = [BOX(X0, Y0 - 10, CW,
             '<p style="font-size:25px;line-height:1.4"><b>Tiêu chí đặt TRƯỚC khi chạy:</b> ΔNSE h2/h3 &gt; 0 với Wilcoxon p &lt; 0.05 <b>và</b> h1 không giảm quá 0.01 '
             '(hoặc bắt đỉnh rõ hơn mà NSE không giảm quá 0.01). Mốc E tái lập: 0.761 / 0.437 / 0.206.</p>',
             f"background:{BG2};border-radius:12px;padding:18px 28px", order=1)]
cw_ = (560, 250, 220, 250, 384)
th = "".join(f'<th style="text-align:left;font-size:24px;color:{MUTED};font-weight:600;width:{w}px">{h}</th>' for h, w in zip(hdr, cw_))
parts.append(BOX(X0, Y0 + 120, CW, f'<table style="width:100%;table-layout:fixed"><tr>{th}</tr></table>', "", order=1, anim="fade"))
for k, (a, b1, b2, b3, cc, o, col) in enumerate(pk):
    tds = "".join(f'<td style="text-align:left;font-size:{24 if i else 25}px;width:{w}px;{"font-weight:600;" if i == 0 else ""}color:{col if i == 4 else INK}">{v}</td>'
                  for i, (v, w) in enumerate(zip((a, b1, b2, b3, cc), cw_)))
    parts.append(BOX(X0, Y0 + 180 + k * 90, CW, f'<table style="width:100%;table-layout:fixed"><tr>{tds}</tr></table>', "", order=o, anim="fade"))
parts.append(BOX(X0, 780, CW,
                 f'<p style="font-size:28px;line-height:1.4"><b style="color:{BLUE}">Không biến thể nào đạt ⇒ giữ E, đóng băng 02/11/2026.</b> '
                 f'Cắt ngọn ở h2–h3 là do thiếu thông tin (mưa gây lũ chưa rơi), không chữa được bằng hàm mất mát hay hậu xử lý.</p>',
                 f"background:{CARD};border:1px solid #D9DEE3;border-left:8px solid {BLUE};border-radius:12px;padding:20px 28px", order=5))
slide("peak", "Thử giảm cắt ngọn lũ: ba hướng, tiêu chí đặt trước", parts, HUYEN, 1.6, [
    "Điểm yếu lớn nhất là cắt ngọn lũ. Nhóm thử ba hướng chữa, chấm bằng walk-forward 13 năm, giống hệt cách chấm mô hình chính.",
    "Điều quan trọng là tiêu chí nhận được đặt trước khi chạy: phải tăng NSE ở h2 hoặc h3 với p dưới 0,05, và h1 không giảm quá 0,01. Mốc E tái lập đúng 0,761; 0,437; 0,206.",
    "Hướng một: đánh trọng số cao hơn cho các ngày lũ khi học. Với alpha bằng 3, NSE nhích 0,011 và 0,012 nhưng không có ý nghĩa thống kê, và alpha được chọn sau khi xem kết quả — nên không nhận.",
    "Hướng hai: hiệu chỉnh isotonic sau dự báo, học từ các năm trước. Kết quả làm hại: h3 giảm 0,027, thua 12 trên 13 fold, p 0,001 — vì quan hệ giữa dự báo và thực tế không ổn định giữa các năm.",
    "Hướng ba: ghép 50/50 LightGBM E với LSTM. Ở h1 tăng 0,029, p 0,048 — cải thiện có ý nghĩa duy nhất của cả đợt. Nhưng h2 giảm 0,022 và h3 giảm 0,023 với p 0,021. Không nhận vì tiêu chí đặt cho h2–h3, chỉ dùng cho h1 là chọn sau khi xem, và job hằng ngày sẽ phải chạy thêm PyTorch. Nhóm ghi nó làm hướng tiếp theo.",
    "Kết luận: không biến thể nào đạt, nhóm giữ E và đóng băng ngày 02/11/2026. Gốc vấn đề là 2–3 ngày trước đỉnh, mưa gây lũ chưa rơi — cần mưa dự báo tốt hoặc số liệu xả hồ, không phải đổi hàm mất mát.",
])

# ------------------------------------------------------------------ 22 limitations
lim = [("Mục tiêu là mô phỏng", "Học lưu lượng GloFAS, không phải số đo trạm; GloFAS không có hồ và thiếu lũ lớn"),
       ("h3 dưới AC-1", "Test 0.236, walk-forward 0.206 — dưới 0.25; đỉnh lũ bị cắt ở mọi horizon"),
       ("GloFAS đổi chế độ 07/2022", "Chỉ 3 năm sau đổi (2023–2025: 0.772 / 0.522 / 0.223) — chưa kiểm định riêng được"),
       ("Một ô, mục tiêu ngày", "Ô 5 km không tách sông Bồ; bản đồ chỉ có một mức chung toàn lưu vực"),
       ("Sự kiện hiếm", "Chỉ mức 1 đủ dữ liệu; mức 2, mức 3 và AC-2 chưa đánh giá được"),
       ("Chưa so với GloFAS thô (AC-3)", "Kho dự báo quá khứ không truy cập được; nhật ký mới từ 15/09/2026; đầu vào chạy thật là mưa dự báo")]
parts = []
for i, (h, s_) in enumerate(lim):
    col, row = i % 2, i // 2
    parts.append(BOX(X0 + col * 856, Y0 - 10 + row * 205, 808,
                     f'<h3 style="font-size:29px;font-weight:600;color:#9A4A10">{h}</h3>'
                     f'<p style="font-size:24px;color:{INK};line-height:1.4">{s_}</p>',
                     f"background:{CARD};border:1px solid #D9DEE3;border-left:8px solid {ORANGE};border-radius:12px;padding:22px 28px;display:flex;flex-direction:column;gap:8px",
                     order=row + 1, h=180))
slide("limits", "Hạn chế — nói thẳng", parts, HUYEN, 1.3, [
    "Nhóm liệt kê thẳng các hạn chế.",
    "Thứ nhất, mục tiêu là lưu lượng mô phỏng GloFAS, không phải số đo trạm — và GloFAS không có hồ, thiếu lũ lớn. Thứ hai, h3 dưới tiêu chí AC-1 cả trên test lẫn walk-forward, và đỉnh lũ bị cắt ở mọi horizon.",
    "Thứ ba, GloFAS đổi chế độ từ 07/2022; sau thời điểm đó mới có 3 năm, kết quả 0,772; 0,522; 0,223 tương đương các năm trước, nhưng 3 fold thì chưa kiểm định riêng được. Thứ tư, chỉ có một ô và mục tiêu theo ngày — ô 5 km không tách được sông Bồ.",
    "Thứ năm, sự kiện hiếm: chỉ mức 1 đủ dữ liệu để đánh giá; mức 2, 3 và tiêu chí AC-2 thì chưa. Thứ sáu, chưa so được với GloFAS thô vì kho dự báo quá khứ không truy cập được, nhật ký của nhóm mới bắt đầu từ 15/09/2026 — và lúc chạy thật mưa ngày t là mưa dự báo.",
])

# ------------------------------------------------------------------ 23 future work
fw = [("Ghép E + LSTM theo horizon ở h1", "Kiểm trên mùa lũ mới, đúng tiêu chí đặt trước", BLUE),
      ("Mưa dự báo tốt hơn + số liệu xả hồ", "Chỗ duy nhất có thể gỡ cắt ngọn ở h2–h3", TEAL),
      ("Tích luỹ nhật ký → kiểm AC-3", "So LightGBM với GloFAS thô trên các ngày đã có giá trị kiểm", ORANGE),
      ("GloFAS v5 có hồ chứa", "Chạy lại phép thử hồ, huấn luyện lại khi nguồn chuyển sang v5", PURPLE),
      ("Walk-forward trên nhiều máy thật", "Spark song song theo tác vụ khi dữ liệu / số mô hình vượt một máy", GOLD),
      ("Xin số liệu trạm KTTV", "Nếu đồ án tiếp tục sau môn học: mực nước giờ Kim Long", GRAY)]
parts = []
for i, (h, s_, c) in enumerate(fw):
    col, row = i % 3, i // 3
    parts.append(BOX(X0 + col * 568, Y0 + row * 300, 528,
                     f'<h3 style="font-size:29px;font-weight:600;line-height:1.25">{h}</h3>'
                     f'<p style="font-size:24px;color:{MUTED};line-height:1.4">{s_}</p>',
                     card_style(c, pad=28), order=row + 1, h=260))
slide("future", "Hướng tiếp theo", parts, HUYEN, 1.0, [
    "Từ các hạn chế đó, nhóm đề xuất sáu hướng tiếp theo.",
    "Một: ghép E với LSTM riêng cho h1, kiểm trên mùa lũ mới với tiêu chí đặt trước. Hai: mưa dự báo tốt hơn và số liệu xả hồ — đây là chỗ duy nhất có thể gỡ cắt ngọn ở h2–h3. Ba: tích luỹ nhật ký để kiểm AC-3, tức so trực tiếp với GloFAS thô.",
    "Bốn: khi GloFAS lên v5 có mô phỏng hồ chứa, chạy lại phép thử hồ và huấn luyện lại. Năm: đưa walk-forward song song theo tác vụ lên nhiều máy thật. Sáu: nếu đồ án tiếp tục sau môn học, xin số liệu mực nước giờ của trạm KTTV.",
])

# ------------------------------------------------------------------ 24 conclusion
tk = [("1", "Hữu ích 1–2 ngày", "Test 0.747 / 0.499, walk-forward 0.761 / 0.437 — vượt persistence; h3 0.236 trượt AC-1 0.014", BLUE),
      ("2", "Cảnh báo có cơ sở", "Ngưỡng chi phí −34 % chi phí; xác suất hiệu chỉnh Brier 0.0119 → 0.0100; báo ở 1/11", TEAL),
      ("3", "Chạy thật, trung thực", "Job mỗi sáng + dashboard; Spark trùng từng bit; kết quả âm (DL, vệ tinh, cắt ngọn) ghi kèm bằng chứng", ORANGE)]
parts = []
for i, (n_, h, s_, c) in enumerate(tk):
    parts.append(BOX(X0 + i * 568, Y0, 528,
                     f'<p style="font-family:{SERIF};font-size:64px;font-weight:600;color:{c};line-height:1">{n_}</p>'
                     f'<h3 style="font-size:34px;font-weight:600;line-height:1.2">{h}</h3>'
                     f'<p style="font-size:25px;color:{MUTED};line-height:1.4">{s_}</p>', card_style(c), order=i + 1, h=400))
parts.append(BOX(X0, Y0 + 450, CW,
                 '<p style="font-size:25px;line-height:1.45"><b>RQ1</b> dự báo được lưu lượng: có ở 1–2 ngày, một phần ở 3 ngày. '
                 '<b>RQ2</b> không theo cấp BĐ chính thức; theo mức 1: POD 0.88, FAR 0.54 (quy tắc chi phí, 13 fold). '
                 '<b>RQ3</b> gián tiếp: SHAP h1 mưa thượng nguồn 11.2 % so với mưa toàn lưu vực 9.5 %.</p>',
                 f"background:{BG2};border-radius:12px;padding:20px 28px", order=4))
slide("conclusion", "Kết luận: ba điều cần nhớ", parts, HUYEN, 1.2, [
    "Để kết lại, nhóm mong thầy cô nhớ ba điều.",
    "Một: dự báo hữu ích cho 1–2 ngày tới — test 0,747 và 0,499, walk-forward 0,761 và 0,437, vượt xa persistence. h3 đạt 0,236, trượt AC-1 0,014, nhóm nói thẳng.",
    "Hai: cảnh báo có cơ sở — ngưỡng theo chi phí giảm 34 % tổng chi phí cảnh báo; xác suất đã hiệu chỉnh, Brier từ 0,0119 xuống 0,0100, báo động ở ngưỡng 1/11.",
    "Ba: hệ thống chạy thật và trung thực — job mỗi sáng, dashboard, Spark cho kết quả trùng từng bit; các kết quả âm như DL, mưa vệ tinh, thử giảm cắt ngọn đều được ghi lại kèm bằng chứng.",
    "Trả lời ba câu hỏi nghiên cứu của Report 1: RQ1 — có, ở 1 và 2 ngày, một phần ở 3 ngày. RQ2 — không theo cấp báo động chính thức; theo mức nguy cơ 1, quy tắc chi phí đạt POD 0,88 với FAR 0,54. RQ3 — gián tiếp qua SHAP: ở h1 mưa thượng nguồn có tỉ trọng 11,2 %, lớn hơn mưa trung bình lưu vực 9,5 %.",
])

# ------------------------------------------------------------------ 25 Q&A
faq = [("Sao không so với GloFAS thô?", "Kho dự báo quá khứ không truy cập được; nhật ký mới từ 15/09/2026"),
       ("Sao không dùng BĐ I/II/III?", "H–Q R² 0.18 ⇒ dùng mức nguy cơ tương đối"),
       ("Spark chậm hơn thì để làm gì?", "Chứng minh đúng khi phân tán; có lợi khi song song tác vụ (7.7×)"),
       ("E + LSTM tốt ở h1 sao không dùng?", "Tiêu chí đặt cho h2–h3; chọn sau khi xem; thêm PyTorch vào job")]
parts = [P(128, 200, 1664, "Cảm ơn thầy cô đã lắng nghe", 80, LIGHT, bold=True, serif=True, order=1, anim="rise"),
         P(128, 330, 1664, "h1 0.747 · h2 0.499 · h3 0.236 (trượt 0.014) · 13 năm walk-forward · chạy mỗi sáng", 32, SOFT, order=1),
         P(128, 430, 1664, "Nhóm xin nhận câu hỏi — các câu hay gặp:", 30, SKY, bold=True, order=2)]
for i, (q, a) in enumerate(faq):
    col, row = i % 2, i // 2
    parts.append(BOX(128 + col * 840, 500 + row * 180, 800,
                     f'<p style="font-size:28px;font-weight:600;color:{LIGHT}">{q}</p>'
                     f'<p style="font-size:24px;color:{SOFT};line-height:1.35">{a}</p>',
                     f"border-top:4px solid {SKY};padding:16px 0 0 0;display:flex;flex-direction:column;gap:6px", order=2))
slide("qa", "", parts, HUYEN, 0.5, [
    "(Slide kết thúc.)",
    "Em xin thay mặt nhóm cảm ơn thầy cô đã lắng nghe. Tóm lại: NSE 0,747 và 0,499 ở 1 và 2 ngày, 0,236 ở 3 ngày — trượt mục tiêu 0,014; kiểm qua 13 năm walk-forward; hệ thống đã chạy mỗi sáng.",
    "Nhóm em xin nhận câu hỏi. (Phân công trả lời: dữ liệu, Spark, hệ thống — Giáp; mô hình, đánh giá, cảnh báo, SHAP — Đức; DL, thử nghiệm, hạn chế — Huyền. Trả lời nhanh: GloFAS thô — kho quá khứ không truy cập được, nhật ký từ 15/09/2026 chưa đủ cặp kiểm; BĐ — R² H–Q 0,18 nên dùng mức nguy cơ tương đối; Spark — chứng minh đúng khi phân tán, có lợi khi song song tác vụ 7,7 lần; E cộng LSTM — tiêu chí đặt cho h2–h3, chỉ dùng h1 là chọn sau khi xem, và thêm PyTorch vào job.)",
], dark=True, foot=False)

# ------------------------------------------------------------------ deck.json
deck = {"title": "DSP391m Final – Dự báo lưu lượng và mức nguy cơ lũ sông Hương tại Kim Long",
        "footer": FOOT, "order": [d["id"] for d in DECK], "slides": DECK}
(S / "deck.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8")
tot = {}
for d in DECK:
    tot[d["speaker"]] = tot.get(d["speaker"], 0) + d["minutes"]
print("ok", len(DECK), "slides;", {k: round(v, 1) for k, v in tot.items()}, "total", round(sum(tot.values()), 1))
