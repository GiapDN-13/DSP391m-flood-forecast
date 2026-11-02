"""deck.json + slides/*.html -> _slides.html (1920×1080 mỗi trang) và _script.html (A4, lời thuyết trình).

Chạy sau gen_deck.py:
    python reports/final/slides/build_pdf.py          # dựng HTML + in 2 PDF bằng Chrome/Edge headless
    python reports/final/slides/build_pdf.py --no-pdf # chỉ dựng HTML
Kết quả: DSP391m_Final_slides.pdf (25 trang 1920×1080) và DSP391m_Final_script.pdf (A4).
"""
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
deck = json.loads((root / "deck.json").read_text(encoding="utf-8"))
fonts = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400..700'
         '&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">')

secs = []
for sd in deck["slides"]:
    s = (root / "slides" / f"{sd['id']}.html").read_text(encoding="utf-8")
    s = re.sub(r"<aside>.*?</aside>", "", s, flags=re.S)
    secs.append(s.replace("<section ", '<section class="slide" ', 1))

css = """<style>@page{size:1920px 1080px;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0}
.slide{position:relative;width:1920px;height:1080px;overflow:hidden;break-after:page}
h1,h2,h3,p,ul,table{margin:0} ul{padding-left:1.1em}
table{border-collapse:collapse} th,td{padding:.45em .6em;border-bottom:1px solid rgba(127,140,155,.35)} svg{display:block}</style>"""
(root / "_slides.html").write_text(
    f"<!doctype html><html lang='vi'><head><meta charset='utf-8'><title>{html.escape(deck['title'])}</title>"
    f"{fonts}{css}</head><body>{''.join(secs)}</body></html>", encoding="utf-8")

# ---------------------------------------------------------------- script
FALLBACK = {"cover": "Mở đầu (bìa)", "qa": "Kết thúc – Cảm ơn và hỏi đáp"}
by_spk, rng = {}, {}
for i, sd in enumerate(deck["slides"], 1):
    by_spk[sd["speaker"]] = by_spk.get(sd["speaker"], 0) + sd["minutes"]
    rng.setdefault(sd["speaker"], [i, i])[1] = i
summary = "".join(
    f"<tr><td>{html.escape(k)}</td><td>Slide {a}–{b}</td><td>~{v:.1f} phút</td></tr>"
    for k, v in by_spk.items() for a, b in [rng[k]])
total = sum(by_spk.values())

items, prev = [], None
for i, sd in enumerate(deck["slides"], 1):
    if sd["speaker"] != prev:
        items.append(f"<h1 class='part'>Phần {html.escape(sd['speaker'])}</h1>")
        prev = sd["speaker"]
    ttl = sd["title"] or FALLBACK.get(sd["id"], sd["id"])
    ttl = html.unescape(re.sub("<[^>]+>", "", ttl))
    paras = "".join(
        f"<p><span class='tag'>{'[Mở slide]' if k == 0 else f'[Bấm {k}]'}</span> {html.escape(html.unescape(t))}</p>"
        for k, t in enumerate(sd["notes"]))
    items.append(f"<div class='it'><h2>Slide {i}. {html.escape(ttl)}</h2>"
                 f"<p class='meta'>Người nói: {html.escape(sd['speaker'])} · {sd['builds']} lần bấm · ~{sd['minutes']:.1f} phút</p>"
                 f"{paras}</div>")

css2 = """<style>@page{size:A4;margin:16mm 18mm}body{font-family:'IBM Plex Sans',Arial,sans-serif;color:#14213D;font-size:12pt;line-height:1.5}
h1{font-family:'Source Serif 4',Georgia,serif;font-size:21pt;margin:0 0 4pt}.sub{color:#5A6577;margin:0 0 10pt}
h1.part{font-size:15pt;color:#14213D;border-bottom:2px solid #1F6FB2;padding-bottom:3pt;margin:18pt 0 2pt;break-after:avoid}
h2{font-family:'Source Serif 4',Georgia,serif;font-size:13.5pt;color:#1F6FB2;margin:12pt 0 2pt;break-after:avoid}
.meta{color:#5A6577;font-size:10.5pt;margin:0 0 4pt}.it p{margin:0 0 5pt}.it{break-inside:avoid}
.tag{color:#D2691E;font-weight:600}table{border-collapse:collapse;margin:4pt 0 8pt}td,th{border-bottom:1px solid #D9DEE3;padding:3pt 10pt 3pt 0;text-align:left}</style>"""
(root / "_script.html").write_text(
    f"<!doctype html><html lang='vi'><head><meta charset='utf-8'><title>DSP391m Final – Lời thuyết trình</title>{fonts}{css2}</head><body>"
    f"<h1>DSP391m – Bảo vệ cuối kỳ: Lời thuyết trình</h1>"
    f"<p class='sub'>{len(deck['slides'])} slide · ~{total:.0f} phút · mỗi đoạn ứng với một lần bấm (đoạn đầu: lúc mở slide). "
    f"Số liệu: reports/final/OUTLINE_VI.txt.</p>"
    f"<table><tr><th>Người nói</th><th>Slide</th><th>Thời lượng ước</th></tr>{summary}</table>"
    f"{''.join(items)}</body></html>", encoding="utf-8")
print(len(secs), "slides;", {k: round(v, 1) for k, v in by_spk.items()})


# ---------------------------------------------------------------- PDF (Chrome / Edge headless)
def find_browser():
    for c in ("C:/Program Files/Google/Chrome/Application/chrome.exe",
              "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
              "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
              "C:/Program Files/Microsoft/Edge/Application/msedge.exe"):
        if pathlib.Path(c).exists():
            return c
    return shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("msedge")


if "--no-pdf" not in sys.argv:
    br = find_browser()
    if not br:
        sys.exit("Không tìm thấy Chrome/Edge — in _slides.html và _script.html thủ công.")
    for src, dst in (("_slides.html", "DSP391m_Final_slides.pdf"), ("_script.html", "DSP391m_Final_script.pdf")):
        subprocess.run([br, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--virtual-time-budget=10000", f"--print-to-pdf={root / dst}",
                        (root / src).as_uri()], check=True, capture_output=True)
        print("->", dst)
