"""Sinh deck HTML cho Report 2 — cùng hệ thiết kế "Gauge" với Report 1.

    python reports/report2/slides/build_deck.py

Dùng lại nguyên CSS, JS và hàm hydrograph của deck Report 1 để hai lần thuyết
trình cùng một bộ mặt. Biểu đồ tương quan theo độ trễ **tính từ panel thật**,
không gõ tay — chạy lại là khớp dữ liệu mới nhất.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "deck1", ROOT / "reports" / "report1" / "slides" / "build_deck.py")
deck1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deck1)

OUT = ROOT / "reports" / "report2" / "slides" / "DSP391m_Report2_Data_EDA.html"
PANEL = ROOT / "data" / "processed" / "daily_panel.parquet"

EXTRA_CSS = """
.funnel{ display:flex; flex-direction:column; gap:22px; margin-top:8px }
.fr{ display:grid; grid-template-columns:150px 1fr; align-items:center; gap:30px }
.fr .n{ font:800 64px/1 "Be Vietnam Pro",sans-serif; text-align:right; letter-spacing:-.03em }
.fr .bar{ height:64px; display:flex; align-items:center; padding-left:26px;
  font:500 26px/1.2 "Be Vietnam Pro",sans-serif; color:var(--water) }
.fr .bar.dark{ color:var(--ink) }
.fr.pick .n{ color:var(--flow) }
.note{ font:400 26px/1.45 "Be Vietnam Pro",sans-serif; color:var(--muted); margin-top:40px; max-width:1500px }
.note b{ color:var(--ink) }
.kpi{ display:flex; gap:60px; margin-top:46px }
.kpi div{ border-top:2px solid var(--flow); padding-top:20px; min-width:300px }
.kpi .v{ display:block; font:800 72px/1 "Be Vietnam Pro",sans-serif; letter-spacing:-.03em }
.kpi .l{ display:block; font:400 24px/1.35 "Be Vietnam Pro",sans-serif; color:var(--muted); margin-top:12px }
.kpi .hot .v{ color:var(--bd2) }
.chg{ width:100%; border-collapse:collapse; font:400 27px/1.35 "Be Vietnam Pro",sans-serif }
.chg th{ text-align:left; font:500 19px/1 "JetBrains Mono",monospace; letter-spacing:.12em;
  color:var(--muted); padding:0 24px 18px 0; border-bottom:1px solid var(--edge) }
.chg td{ padding:22px 24px 22px 0; border-bottom:1px solid var(--edge); vertical-align:top }
.chg td:first-child{ color:var(--muted); text-decoration:line-through; text-decoration-color:var(--bd3) }
.chg td:nth-child(2){ color:var(--ink); font-weight:600 }
"""


def lag_corr(max_lag: int = 5) -> list[float]:
    d = pd.read_parquet(PANEL)
    out = []
    for L in range(max_lag + 1):
        v = pd.concat([d["rain_basin"].shift(L), d["discharge"]], axis=1).dropna()
        out.append(float(np.corrcoef(v.iloc[:, 0], v.iloc[:, 1])[0, 1]))
    return out


def lag_bars(cc: list[float]) -> str:
    best = int(np.argmax(cc))
    return "\n".join(
        f'            <div class="lb{" top" if i == best else ""}">'
        f'<i style="height:{c * 100:.0f}%"></i><span>{i}d</span><b>{c:.3f}'.replace("0.", ".", 1)
        + "</b></div>"
        for i, c in enumerate(cc))


def slides(hg: dict, cc: list[float]) -> str:
    S = []
    S.append(_title(hg, cc[1]))

    # ---------- 2. Sources ----------
    S.append("""
<section class="slide" data-notes="First, where the data comes from. Four free sources. River flow from the global flood system. Rain from the ERA5 reanalysis. Sea level from a marine service. And nineteen real floods from a university paper and the news. One lesson for this whole report: we measured every source. We did not trust the documents. The flood service says it starts in 1984. In fact the first thirteen years are empty. Real data starts in 1997.">
  <div class="pad">
    <div class="tag"><s></s>DATA COLLECTION</div>
    <h2>Four open sources &mdash; <span class="thin">every one measured, not trusted</span></h2>
    <div class="quad">
      <div class="q"><span class="qn">River discharge</span>
        <p>GloFAS v4, ~5 km grid, daily. Documented from 1984 &mdash;
           <b>values only from 1997</b>.</p></div>
      <div class="q"><span class="qn">Rainfall</span>
        <p>ERA5 reanalysis, <b>64 grid cells</b>, daily 2010&ndash;2026,
           hourly 2015&ndash;2026.</p></div>
      <div class="q"><span class="qn">Sea level</span>
        <p>Marine API at the river mouth &mdash; a tide proxy,
           <b>only from 2023</b>.</p></div>
      <div class="q"><span class="qn">Ground truth</span>
        <p><b>19 documented floods</b> + official alert stages from
           Decision 05/2020/QD-TTg.</p></div>
    </div>
    <p class="note">All free, no API key, licence <b>CC BY 4.0</b>.
       Raw store: <b>1,295 files &middot; 98 MB</b> &rarr; one table of
       <b>6,087 days &times; 71 columns</b>.</p>
  </div>
</section>""")

    # ---------- 3. Funnel ----------
    S.append("""
<section class="slide" data-notes="The flood service gives one point at a time. But which point is our river? We do not know before we look. So we checked three hundred sixty-one points with one cheap year of data. Two hundred thirty-four had water. Eighty-three got the full history. One was chosen. Two simple rules were wrong. The biggest river point mixes two rivers. The point nearest the station is almost dry, because the model's river is seven kilometres away. We chose by checking the basin size.">
  <div class="pad">
    <div class="tag"><s></s>COLLECTION STRATEGY</div>
    <h2>Probe cheaply, <span class="thin">then fetch only what matters</span></h2>
    <div class="funnel">
      <div class="fr"><span class="n">361</span>
        <div class="bar dark" style="width:100%;background:#16313C">cells probed with one year of data</div></div>
      <div class="fr"><span class="n">234</span>
        <div class="bar dark" style="width:65%;background:#1E5A63">returned any flow</div></div>
      <div class="fr"><span class="n">83</span>
        <div class="bar" style="width:30%;background:#2FC2CC">full 1997&ndash;2026 series</div></div>
      <div class="fr pick"><span class="n">1</span>
        <div class="bar" style="width:14%;background:#7FE9EF">target</div></div>
    </div>
    <p class="note">Rejected: the <b>largest-flow cell</b> (it merges the Huong and Bo
       rivers) and the <b>cell nearest the gauge</b> (the model&rsquo;s channel is
       ~7 km away). Chosen by <b>catchment area implied by runoff</b>.</p>
  </div>
</section>""")

    # ---------- 4. Defects ----------
    S.append("""
<section class="slide" data-notes="Cleaning. We found four problems. Each one passed the normal check. One: thirteen years of empty river data. We counted rows, not values. Two: the rain grid was uneven. The middle area, closest to our station, had only nine of sixteen points. We fixed it. Three: the forecast rain was exactly the same as the observed rain. Zero point zero difference. So we could not use it. Four: the original map point was on a small side stream. The lesson: count values, not rows.">
  <div class="pad">
    <div class="tag"><s></s>DATA CLEANING</div>
    <h2>Four defects <span class="thin">&mdash; each passed the obvious check</span></h2>
    <div class="quad">
      <div class="q hot"><span class="qn">13 empty years</span>
        <p>1984&ndash;1996 delivered as nulls in all 83 cells. Acceptance counted
           <b>rows, not values</b>.</p></div>
      <div class="q hot"><span class="qn">Uneven rain grid</span>
        <p>Middle sub-basin &mdash; nearest the forecast point &mdash; had
           <b>9 of 16 cells</b>. Rebuilt to 64 uniform.</p></div>
      <div class="q hot"><span class="qn">&ldquo;Forecast&rdquo; = observed</span>
        <p>Archived forecast rain identical to ERA5:
           <b>max difference 0.0 mm</b> over 1,523 days.</p></div>
      <div class="q hot"><span class="qn">Wrong coordinate</span>
        <p>Planned point gave <b>5.7 m&sup3;/s</b>; the river carries ~308.</p></div>
    </div>
  </div>
</section>""")

    # ---------- 5. Signal ----------
    S.append(f"""
<section class="slide" data-notes="Now the main signal. Rain comes first. The river follows one day later. Correlation zero point seven nine. It is the same in all three parts of the basin, because water travels from the mountains to the city in only five to six hours. Two more results. Rain added over three days is even stronger, zero point eight six. And wet ground matters a lot. The same heavy rain gives almost seven times more water when the ground is already wet.">
  <div class="pad">
    <div class="tag"><s></s>EDA &mdash; THE SIGNAL</div>
    <h2>Rain today, <span class="thin">river tomorrow</span></h2>
    <div class="col2b">
      <div>
        <div class="lagchart">
          <div class="lc-h">Correlation of rainfall with discharge, by lag</div>
          <div class="lc-bars">
{lag_bars(cc)}
          </div>
        </div>
      </div>
      <div>
        <ul class="big">
          <li>Peak at <b>one day</b>, same in all three sub-basins &mdash; travel time
              is only <b>5&ndash;6 hours</b>.</li>
          <li><b>3-day accumulated rain</b> is the strongest rain feature:
              <b>r = 0.863</b>.</li>
          <li>Same heavy rain, wet vs dry ground: <b>585 vs 85 m&sup3;/s</b> &mdash;
              a factor of <b>6.9</b>.</li>
        </ul>
      </div>
    </div>
  </div>
</section>""")

    # ---------- 6. Floods & extremes ----------
    S.append("""
<section class="slide" data-notes="Real floods tell a surprising story. In October 2020 the water level was four point one seven metres, with two thousand cubic metres per second. In November 2023 the level was higher, four point three four metres, but the flow was only five hundred eighty-four. So level and flow do not move together at this station. Also, big floods are rare. The top one percent of days happens only sixty-one times in sixteen years. So for rare levels we report results, but we do not make strong claims with fewer than thirty days.">
  <div class="pad">
    <div class="tag"><s></s>EDA &mdash; FLOODS AND EXTREMES</div>
    <h2>Water level <span class="thin">does not follow flow</span></h2>
    <div class="kpi">
      <div><span class="v">4.17 m</span><span class="l">Oct 2020<br>2,060 m&sup3;/s</span></div>
      <div class="hot"><span class="v">4.34 m</span><span class="l">Nov 2023 &mdash; higher level<br>only <b>584 m&sup3;/s</b></span></div>
      <div><span class="v">61</span><span class="l">days above the 99th<br>percentile in 16 years</span></div>
    </div>
    <p class="note">At Kim Long, log-flow explains little of the published level
       (R&sup2; = 0.18). Tide and backwater from the lagoon are likely causes &mdash;
       so flood risk is defined by <b>discharge percentiles</b>, not official stages.</p>
  </div>
</section>""")

    # ---------- 7. Limitations ----------
    S.append("""
<section class="slide" data-notes="We say our limits now, not later. One: river flow is from a model, not measured. Two: the reanalysis misses the heaviest rain. In November 2024 it shows three hundred thirty-two millimetres, but the mountains really had five to eight hundred. Three: tide data starts only in 2023. Four: the test period is short, only four years. Only the first risk level has enough flood days to make a strong claim.">
  <div class="pad">
    <div class="tag"><s></s>LIMITATIONS &mdash; STATED NOW</div>
    <h2>What the data <span class="thin">cannot tell us</span></h2>
    <ul class="big">
      <li>Discharge is <b>simulated, not measured</b> &mdash; no gauge record.</li>
      <li>ERA5 <b>under-catches extreme rain</b>: Nov 2024, 332 mm vs 500&ndash;800 mm
          published in the mountains.</li>
      <li>Tide data <b>only from 2023</b> &mdash; cannot be a training feature.</li>
      <li>Short test window: only risk level 1 has <b>&ge; 30 positive days</b> (31).</li>
    </ul>
  </div>
</section>""")

    # ---------- 8. Changes + next ----------
    S.append("""
<section class="slide closing" data-notes="Last slide. Four things in Report 1 were wrong, and we correct them here. Forty-two years of data is really twenty-nine. Forecast rain is the same as observed rain, so we test sensitivity instead. The target is now risk levels from flow percentiles, not official stages. And three-day rain is stronger than one-day rain, not weaker. The official stages are still correct, one, two and three point five metres, now checked from the law itself. Next, Report 3: our first model already beats the simple baseline. Thank you.">
  <div class="pad">
    <div class="tag"><s></s>CORRECTIONS TO REPORT 1</div>
    <h2>Measured, <span class="thin">then corrected</span></h2>
    <table class="chg">
      <tr><th>REPORT 1 SAID</th><th>CORRECTED TO</th></tr>
      <tr><td>42-year discharge record</td><td>29 years, 1997&ndash;2026</td></tr>
      <tr><td>Archived forecast rain as input</td><td>Sensitivity test on perturbed rain</td></tr>
      <tr><td>Target: official alert stage</td><td>Risk levels from discharge percentiles</td></tr>
      <tr><td>Single-day rain beats accumulations</td><td>3-day accumulated rain is strongest (r = 0.863)</td></tr>
    </table>
    <p class="thanks">Official stages confirmed from Decision 05/2020: 1.0 / 2.0 / 3.5 m.
       &nbsp;Thank you &mdash; questions welcome.</p>
  </div>
</section>""")
    return "\n".join(S)


def _title(hg: dict, lag1: float) -> str:
    """Slide tiêu đề Report 1 với chữ thay cho Report 2, giữ nguyên hydrograph."""
    t = deck1.slides(hg).split("</section>")[0] + "</section>"
    start = t.index('data-notes="') + len('data-notes="')
    end = t.index('"', start)
    t = t[:start] + ("Good morning. We are team three. Last time we proposed our flood project. "
                     "Today is Report 2: how we collected the data, how we cleaned it, "
                     "and what it tells us. The short version: we measured everything, "
                     "and some things in Report 1 were wrong. We will show you what, and why.") + t[end:]
    swaps = [
        ("REPORT 01 &middot; PROPOSAL", "REPORT 02 &middot; DATA, CLEANING &amp; EDA"),
        ('Three days<br><span class="thin">of warning</span>',
         'Measured,<br><span class="thin">not trusted</span>'),
        ("Flood risk for the Hương River, Huế — forecast from open\n"
         "      data and reported in Vietnam&rsquo;s own alert stages.",
         "How the open data were collected, cleaned and explored &mdash;\n"
         "      and what we corrected since Report 1."),
        # Report 1 ghi 42 năm — sai; số thật là 29 năm (1997–2026)
        ('<span class="n">42<u>yr</u></span><span class="k">DISCHARGE RECORD</span>',
         '<span class="n">29<u>yr</u></span><span class="k">DISCHARGE RECORD</span>'),
        ('<span class="n">0.790</span>', f'<span class="n">{lag1:.3f}</span>'),
        ('<span class="n">2,929<u>mm</u></span><span class="k">MEAN ANNUAL RAINFALL</span>',
         '<span class="n">6,087</span><span class="k">DAYS IN THE ANALYSIS TABLE</span>'),
    ]
    for a, b in swaps:
        if a not in t:
            raise SystemExit(f"Slide tiêu đề Report 1 đã đổi, không tìm thấy: {a[:50]}")
        t = t.replace(a, b)
    return t


def main() -> int:
    hg = deck1.hydrograph()
    cc = lag_corr()
    css = deck1.CSS.replace("__TRACELEN__", str(hg["len"])) + EXTRA_CSS
    body = slides(hg, cc)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSP391m · Report 2 — Data, Cleaning and EDA</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>{css}</style>
</head>
<body>
<div class="prog" id="prog"></div>
<div class="deck-viewport">
  <div class="deck-stage" id="stage">
{body}
  </div>
</div>
<div class="hud hint">← → navigate &nbsp;·&nbsp; S speaker notes &nbsp;·&nbsp; E edit text</div>
<div class="hud count" id="count">01 / 08</div>
<div class="notes" id="notes"></div>
<script>{deck1.JS}</script>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)}  ({len(html) // 1024} KB)")
    print(f"   số slide: {html.count('<section class=')} · lag: "
          + " ".join(f"{c:.3f}" for c in cc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
