"""Sinh deck HTML cho Report 1 — hệ thiết kế "Gauge".

    python reports/report1/slides/build_deck.py

Đường hydrograph trên slide tiêu đề **lấy từ dữ liệu thật** trong
data/processed/daily_panel.parquet (mùa lũ 2020), không phải số bịa — nên deck
luôn khớp với dữ liệu dự án. Chạy lại script là cập nhật theo dữ liệu mới nhất.

Khung cố định 1920×1080 theo yêu cầu của plugin frontend-slides: slide không
bao giờ tự dàn lại theo màn hình, chỉ scale nguyên khối.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src import config as cfg  # noqa: E402

OUT = ROOT / "reports" / "report1" / "slides" / "DSP391m_Report1_Proposal.html"
CW, CH = 1920.0, 560.0          # khung vẽ hydrograph


# ------------------------------------------------- hydrograph từ dữ liệu thật
def hydrograph(start="2020-09-15", end="2020-12-20"):
    d = pd.read_parquet(cfg.DATA_PROCESSED / "daily_panel.parquet",
                        columns=["date", "discharge"])
    d["date"] = pd.to_datetime(d["date"])
    w = d[(d["date"] >= start) & (d["date"] <= end)].reset_index(drop=True)
    q = w["discharge"].to_numpy()

    lq = np.log10(np.clip(q, 1, None))          # thang log, kẻo đỉnh bẹp phần còn lại
    lo, hi = lq.min(), lq.max()
    x = np.linspace(0, CW, len(q))
    y = CH - 40 - (lq - lo) / (hi - lo) * (CH - 110)

    line = "M" + " ".join(f"L{a:.0f},{b:.0f}" for a, b in zip(x, y))[1:]
    area = f"{line} L{CW:.0f},{CH:.0f} L0,{CH:.0f} Z"

    def y_of(qq):                               # vị trí ngưỡng trên trục y
        return CH - 40 - (np.log10(qq) - lo) / (hi - lo) * (CH - 110)

    peak_i = int(q.argmax())
    return {
        "line": line, "area": area,
        "len": int(np.hypot(np.diff(x), np.diff(y)).sum()) + 200,
        "bands": {k: float(y_of(v)) for k, v in
                  (("q95", 430.2), ("q98", 745.9), ("q99", 1168.8))},
        "peak_q": float(q.max()),
        "peak_date": w.loc[peak_i, "date"].strftime("%d/%m/%Y"),
        "n": len(q),
    }


# --------------------------------------------------------------------- slides
def slides(hg: dict) -> str:
    b = hg["bands"]
    S = []

    # ---------- 1. Title ----------
    S.append(f"""
<section class="slide" data-notes="Good morning. We are team three. Our project is about floods in Hue. We want to predict flood risk one to three days before it happens. We use only free open data. Central Vietnam has the worst floods in the country, but warnings at village level are still weak. So our question is simple: can free data help?">
  <div class="hero-chart">
    <svg viewBox="0 0 1920 560" preserveAspectRatio="none" aria-hidden="true">
      <defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#2FC2CC" stop-opacity=".32"/>
        <stop offset="100%" stop-color="#2FC2CC" stop-opacity="0"/>
      </linearGradient></defs>
      <path class="area" d="{hg['area']}" fill="url(#fade)"/>
      <path class="trace" d="{hg['line']}" fill="none" stroke="#2FC2CC"
            stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>
    </svg>
    <div class="bands">
      <div class="band bd3" style="top:{b['q99']:.0f}px"><span>Q99 · 1 169 m³/s</span></div>
      <div class="band bd2" style="top:{b['q98']:.0f}px"><span>Q98 · 746 m³/s</span></div>
      <div class="band bd1" style="top:{b['q95']:.0f}px"><span>Q95 · 430 m³/s</span></div>
    </div>
    <div class="chart-cap">Observed discharge, flood season 2020 &middot; peak
      {hg['peak_q']:,.0f} m³/s on {hg['peak_date']}</div>
  </div>

  <div class="byline">
    <b>{cfg.TEAM_VI[0]}</b>{cfg.TEAM_VI[1]}<br>{cfg.TEAM_VI[2]}
  </div>

  <div class="pad top">
    <div class="tag"><s></s>DSP391m &middot; REPORT 01 &middot; PROPOSAL</div>
    <h1 class="mega">Three days<br><span class="thin">of warning</span></h1>
    <p class="lede w900">Flood risk for the Hương River, Huế — forecast from open
      data and reported in Vietnam&rsquo;s own alert stages.</p>
    <div class="figrow">
      <div class="fig"><span class="n">42<u>yr</u></span><span class="k">DISCHARGE RECORD</span></div>
      <div class="fig"><span class="n">0.790</span><span class="k">RAIN LEADS FLOW · 1 DAY</span></div>
      <div class="fig"><span class="n">2,929<u>mm</u></span><span class="k">MEAN ANNUAL RAINFALL</span></div>
    </div>
  </div>
</section>""")

    # ---------- 2. Subject & context ----------
    S.append("""
<section class="slide" data-notes="The Huong basin is small, about two thousand eight hundred square kilometres. It is also steep, so water moves fast. Rain today becomes a flood tomorrow — only one day. On the right are the official alert levels at Kim Long: one metre, two metres, three point five metres. We use these official numbers. We do not invent our own scale. Local officers already use them every day. If we use different numbers, nobody will use our model.">
  <div class="pad col2">
    <div>
      <div class="tag"><s></s>SUBJECT &amp; CONTEXT</div>
      <h2>A basin that floods<br><span class="thin">in a single day</span></h2>
      <ul class="big">
        <li>Central Vietnam is the country&rsquo;s most flood-affected region.</li>
        <li>Short, steep catchment — rain becomes a flood peak within <b>one day</b>.</li>
        <li>Commune-level warning remains sparse relative to the damage.</li>
      </ul>
    </div>
    <div class="panel">
      <div class="panel-h">OFFICIAL ALERT STAGES</div>
      <div class="panel-s">Kim Long station &middot; water level above datum</div>
      <div class="gauge">
        <div class="grow"><span class="lv">BĐ I</span>
          <span class="bar"><i class="f1" style="width:28.6%"></i></span>
          <span class="m">1.00 m</span></div>
        <div class="grow"><span class="lv">BĐ II</span>
          <span class="bar"><i class="f2" style="width:57.1%"></i></span>
          <span class="m">2.00 m</span></div>
        <div class="grow"><span class="lv">BĐ III</span>
          <span class="bar"><i class="f3" style="width:100%"></i></span>
          <span class="m">3.50 m</span></div>
      </div>
      <div class="panel-f">Decision 05/2020/QĐ-TTg &mdash; cross-checked against five
        bulletins of the Huế Hydro-Meteorological Station.</div>
    </div>
  </div>
</section>""")

    # ---------- 3. Big data context ----------
    S.append("""
<section class="slide" data-notes="Many people think big data means a lot of data. We do not agree. Our data size is normal, about one thousand five hundred files. The hard part is variety and veracity. Six different types must fit into one table, day by day. And veracity means: can we trust it? Our river flow is not measured — it comes from a computer model. Dams upstream are not in the model. We say this clearly. We do not hide it.">
  <div class="pad">
    <div class="tag"><s></s>CONTEXT OF BIG DATA</div>
    <h2>Not the volume &mdash; <span class="thin">the variety and the veracity</span></h2>
    <div class="quad">
      <div class="q"><span class="qn">Volume</span>
        <p>42 years of daily discharge, 11 years of hourly rainfall, 68 grid points.
           About <b>1,500 Parquet files</b> — moderate, not extreme.</p></div>
      <div class="q"><span class="qn">Variety</span>
        <p>Six source types on one daily timeline: simulated flow, reanalysis rain,
           archived forecasts, river geometry, a legal document, news bulletins.</p></div>
      <div class="q"><span class="qn">Velocity</span>
        <p>Forecasts are re-issued several times a day. An automated job pulls a fresh
           7-day forecast <b>every morning</b>.</p></div>
      <div class="q hot"><span class="qn">Veracity</span>
        <p>Discharge is <b>model output, not measurement</b>. Reservoir releases are
           unmodelled. Stated, not hidden.</p></div>
    </div>
  </div>
</section>""")

    # ---------- 4. Problem ----------
    S.append("""
<section class="slide" data-notes="Two problems. First: how much water? River flow in cubic metres per second, for one, two and three days. Second: which alert level? Here is a trap - flood days are very rare, one to three percent. So we never use accuracy. If I say no flood every day I am correct ninety-eight percent, but my model is useless. We use POD, FAR and CSI. The hard part in the middle: official levels are in metres, our data is in cubic metres per second. We could not get real measurements, so we build the link from old flood records.">
  <div class="pad">
    <div class="tag"><s></s>PROBLEM STATEMENT</div>
    <h2>Two targets, <span class="thin">one awkward bridge</span></h2>
    <div class="steps">
      <div class="step"><span class="sn">01</span>
        <div><h3>How much water?</h3>
          <p>Daily discharge in m³/s at 1, 2 and 3 days. Continuous target &mdash;
             RMSE, MAE, NSE, KGE.</p></div></div>
      <div class="step"><span class="sn">02</span>
        <div><h3>Which alert stage?</h3>
          <p>Exceedance of BĐ I / II / III. Positive days are <b>1&ndash;3 %</b>, so
             accuracy is banned &mdash; POD, FAR, CSI instead.</p></div></div>
      <div class="step hot"><span class="sn">03</span>
        <div><h3>The bridge between them</h3>
          <p>Stages are <b>metres</b>; our data is <b>m³/s</b>. No measured rating curve
             was available, so the mapping is built from documented flood peaks.</p></div></div>
    </div>
  </div>
</section>""")

    # ---------- 5. Approach ----------
    S.append("""
<section class="slide" data-notes="Four types of analytics. Descriptive: what happened - we use it to help. Diagnostic: why - a little, to explain warnings. Predictive: what will happen - this is our main work. Prescriptive: what should we do - we do not do this, because telling people to leave their homes needs legal power a student project does not have. The last line is our real contribution: a global system already predicts this river. We fix its errors for our small basin, and we translate it into Vietnamese alert levels.">
  <div class="pad">
    <div class="tag"><s></s>ANALYTICS APPROACH</div>
    <h2>Primarily <span class="thin">predictive</span></h2>
    <div class="four">
      <div class="c"><span class="ct">SUPPORTING</span><h3>Descriptive</h3>
        <p>Seasonality, rainfall&ndash;discharge lag, historical events.</p></div>
      <div class="c"><span class="ct">PARTIAL</span><h3>Diagnostic</h3>
        <p>SHAP attributes each warning to rain, wetness or season.</p></div>
      <div class="c core"><span class="ct">CORE</span><h3>Predictive</h3>
        <p>Discharge and alert stage 1&ndash;3 days ahead. Both research questions.</p></div>
      <div class="c out"><span class="ct">OUT OF SCOPE</span><h3>Prescriptive</h3>
        <p>Evacuation decisions need authority we do not hold.</p></div>
    </div>
    <p class="claim">We do not replace the global forecast. We <b>correct it locally</b>
      and <b>translate it</b> into Vietnam&rsquo;s alert stages at sub-basin scale.</p>
  </div>
</section>""")

    # ---------- 6. Data requirements ----------
    S.append("""
<section class="slide" data-notes="Six types of data, one daily table. Five are done. Only the last row is not finished: old flood records. This is our biggest problem right now. Without it we cannot change metres into cubic metres per second, and the alert level problem cannot exist. This work is manual - we must read weather reports and news by hand. A computer cannot do it. One good point: all data is free and open. Our project costs zero.">
  <div class="pad">
    <div class="tag"><s></s>DATA REQUIREMENTS</div>
    <h2>Six inputs, <span class="thin">one daily table</span></h2>
    <table class="dt">
      <thead><tr><th>Dataset</th><th>Role</th><th>Span</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td>River discharge &mdash; GloFAS v4</td><td>Target and lag features</td>
            <td>1997&ndash;2026, daily</td><td class="ok">Collected</td></tr>
        <tr><td>Rain &amp; meteorology &mdash; ERA5</td><td>Primary predictors</td>
            <td>2010&ndash;2026, daily + hourly</td><td class="ok">Collected</td></tr>
        <tr><td>Archived rainfall forecasts</td><td>Operational input scenario</td>
            <td>2022&ndash;2026, daily</td><td class="ok">Collected</td></tr>
        <tr><td>River centre-lines &mdash; OpenStreetMap</td><td>Grid cell to river</td>
            <td>Current extract</td><td class="ok">Collected</td></tr>
        <tr><td>Legal alert thresholds</td><td>Defines the target</td>
            <td>05/2020/QĐ-TTg</td><td class="ok">Verified</td></tr>
        <tr class="crit"><td>Documented flood peaks</td><td>Calibrates metres to m³/s</td>
            <td>&ge; 15 events</td><td class="wip">In progress</td></tr>
      </tbody>
    </table>
    <p class="claim warn">The last row is the <b>critical path</b>. Without it the
      alert-stage target cannot be defined at all.</p>
  </div>
</section>""")

    # ---------- 7. Collection ----------
    S.append("""
<section class="slide" data-notes="Four steps: select, crawl, clean, assemble. Step one has a story. Our first map point gave five point seven cubic metres per second - too small, impossible for this river. So we checked three hundred sixty-one points with three tests. The best test: from water flow we can guess the basin size. Our new point gives about two thousand six hundred square kilometres; the real basin is two thousand eight hundred and thirty. Only seven percent different. And one more story about our own mistake: we saw many too-many-requests errors and thought the website blocked us. The real reason was us - three programs running at the same time. With one program everything finished in thirty-five minutes, zero errors. Check your own computer first.">
  <div class="pad">
    <div class="tag"><s></s>COLLECTION METHOD</div>
    <h2>How the data <span class="thin">gets here</span></h2>
    <div class="flow">
      <div class="fstep"><span class="fn">1</span><h3>Select</h3>
        <p>Scan 361 cells; keep the one whose inferred catchment matches the real basin.</p></div>
      <div class="farrow">&rarr;</div>
      <div class="fstep"><span class="fn">2</span><h3>Crawl</h3>
        <p>Independent tasks, one file each. Retry, cache, checkpoint, lock.</p></div>
      <div class="farrow">&rarr;</div>
      <div class="fstep"><span class="fn">3</span><h3>Clean</h3>
        <p>Normalise to Vietnam time, hourly&rarr;daily, validate and fail loudly.</p></div>
      <div class="farrow">&rarr;</div>
      <div class="fstep"><span class="fn">4</span><h3>Assemble</h3>
        <p>Average rain over three sub-basins, build lags, block leakage.</p></div>
    </div>
    <div class="lesson">
      <span class="lt">WHAT WE GOT WRONG</span>
      <p>Persistent rate-limit errors were blamed on the provider &mdash; and a scope cut
         was proposed. The real cause was <b>three of our own crawlers running in
         parallel</b>. With one process the whole collection took <b>35 minutes,
         zero errors</b>. Lesson: count your own processes first.</p>
    </div>
  </div>
</section>""")

    # ---------- 8. Feasibility ----------
    S.append("""
<section class="slide" data-notes="This is not just a plan - we already did the work. Six thousand rows, seventy-one columns. Average rain per year is two thousand nine hundred millimetres, which matches the official climate data for Hue, so our data is correct. Look at the chart: rain comes first, river flow comes one day later, correlation zero point seven nine. We also tested three, five and seven day rain - all lower. The river reacts fast. That matches a small steep basin and supports our short forecast time. We also measured simple models, so we know the target we must beat.">
  <div class="pad">
    <div class="tag"><s></s>FEASIBILITY &mdash; ALREADY DEMONSTRATED</div>
    <h2>The signal <span class="thin">is measurable</span></h2>
    <div class="col2b">
      <div>
        <div class="lagchart">
          <div class="lc-h">Correlation of rainfall with discharge, by lag</div>
          <div class="lc-bars">
            <div class="lb"><i style="height:64%"></i><span>0d</span><b>.641</b></div>
            <div class="lb top"><i style="height:79%"></i><span>1d</span><b>.790</b></div>
            <div class="lb"><i style="height:61%"></i><span>2d</span><b>.608</b></div>
            <div class="lb"><i style="height:38%"></i><span>3d</span><b>.382</b></div>
            <div class="lb"><i style="height:28%"></i><span>4d</span><b>.284</b></div>
            <div class="lb"><i style="height:23%"></i><span>5d</span><b>.233</b></div>
          </div>
        </div>
      </div>
      <div>
        <ul class="big">
          <li><b>6,087 × 71</b> daily table, 0 % missing discharge.</li>
          <li>Rainfall <b>2,929 mm/yr</b> matches Huế&rsquo;s published climatology &mdash;
              an independent check on our own data.</li>
          <li>Single-day rain beats 3-, 5- and 7-day accumulations: the basin
              <b>responds fast</b>.</li>
          <li>Baselines measured, so the bar is real: persistence reaches
              <b>NSE 0.542</b> at one day, then collapses.</li>
        </ul>
      </div>
    </div>
  </div>
</section>""")

    # ---------- 9. Closing ----------
    S.append("""
<section class="slide closing" data-notes="One sentence to finish. We do not replace the global forecast - we fix it and translate it into Vietnamese alert levels. Three next steps: finish the flood records, train the model, check the dam problem. And three limits, said now not later. One: our river data is from a model, not measured. Two: the map is five kilometres wide, too big to see the small Bo river, so we study one station only. Three: this is a student project, not an official warning service. Thank you.">
  <div class="pad mid">
    <div class="tag"><s></s>IN ONE SENTENCE</div>
    <h1 class="big-claim">We correct and localise an open global flood forecast
      into <span class="thin">Vietnam&rsquo;s own alert stages</span>.</h1>
    <div class="col2c">
      <div>
        <span class="ch">NEXT THREE STEPS</span>
        <ol class="nx">
          <li>Complete the flood-event record that unlocks the alert-stage target.</li>
          <li>Train the model and beat the measured baselines.</li>
          <li>Test whether reservoir operation explains the anomalies we found.</li>
        </ol>
      </div>
      <div class="lim">
        <span class="ch warnc">STATED PLAINLY IN THE REPORT</span>
        <ul class="nx">
          <li>Discharge data is <b>simulated, not measured</b>.</li>
          <li>The 5 km grid cannot resolve the neighbouring Bồ River &mdash; so the study
              covers <b>one station</b>.</li>
          <li>Academic work, <b>not an official warning service</b>.</li>
        </ul>
      </div>
    </div>
    <p class="thanks">Thank you &mdash; questions welcome.</p>
  </div>
</section>""")

    return "\n".join(S)


# ------------------------------------------------------------------------ CSS
CSS = """
/* ===========================================
   FIXED 16:9 STAGE: MANDATORY BASE STYLES
   =========================================== */
html, body { width:100%; height:100%; margin:0; overflow:hidden; background:var(--stage-bg,#000); }
.deck-viewport { position:fixed; inset:0; overflow:hidden; background:var(--stage-bg,#000); }
.deck-stage { position:absolute; left:0; top:0; width:1920px; height:1080px; overflow:hidden; transform-origin:0 0; background:var(--slide-bg,#fff); }
.slide { position:absolute; inset:0; width:1920px; height:1080px; overflow:hidden; display:block; visibility:hidden; opacity:0; pointer-events:none; background:var(--slide-bg,#fff); }
.slide.active, .slide.visible { visibility:visible; opacity:1; pointer-events:auto; z-index:1; }
img, video, canvas, svg { max-width:100%; max-height:100%; }
.deck-controls { position:fixed; left:50%; bottom:22px; transform:translateX(-50%); z-index:1000; }
@media print {
  @page { size:1920px 1080px; margin:0 }
  html, body { width:1920px; height:auto; overflow:visible; background:#fff; }
  .deck-viewport { position:static; overflow:visible; background:#fff; }
  .deck-stage { position:static; width:auto; height:auto; transform:none !important; background:none; }
  .slide { position:relative; display:block !important; visibility:visible !important; opacity:1 !important; pointer-events:auto !important; width:1920px; height:1080px; break-after:page; page-break-after:always; }
  .slide:last-child { break-after:auto; page-break-after:auto; }
  .deck-controls, .hud, .prog, .notes { display:none !important; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration:0.01ms !important; transition-duration:0.2s !important; } }

/* ===========================================
   GAUGE — the deck reads as a river gauge chart
   =========================================== */
:root{
  --water:#07141A; --water-2:#0C222B; --edge:#16313C;
  --ink:#EAF4F5; --muted:#6D8F99; --dim:#3F5F6A;
  --flow:#2FC2CC;
  --bd1:#E8BE55; --bd2:#E0833C; --bd3:#D2453B;
  --stage-bg:#03080B; --slide-bg:var(--water);
}
*{ box-sizing:border-box }
.slide{
  background:radial-gradient(1500px 900px at 80% 12%, #113240 0%, transparent 60%), var(--water);
  color:var(--ink);
  font-family:"Be Vietnam Pro", system-ui, sans-serif;
}
/* faint contour texture — water, not graph paper */
.slide::before{
  content:""; position:absolute; inset:0; pointer-events:none; opacity:.5;
  background:repeating-linear-gradient(to bottom, rgba(47,194,204,.045) 0 1px, transparent 1px 7px);
}
.pad{ position:absolute; inset:92px 120px; z-index:2;
  display:flex; flex-direction:column; justify-content:center }
.pad.top{ inset:92px 120px auto; display:block }
.pad.mid{ display:flex; flex-direction:column; justify-content:center }

.tag{ display:inline-flex; align-items:center; gap:16px; font:500 19px/1 "JetBrains Mono",monospace;
  letter-spacing:.22em; color:var(--flow); margin-bottom:34px }
.tag s{ width:52px; height:2px; background:var(--flow); display:block }

h1.mega{ font-weight:900; font-size:152px; line-height:.92; letter-spacing:-.045em; margin:0; max-width:1250px }
h2{ font-weight:800; font-size:78px; line-height:1.03; letter-spacing:-.035em; margin:0 0 46px; max-width:1500px }
h3{ font-weight:700; font-size:31px; line-height:1.2; letter-spacing:-.02em; margin:0 0 10px }
.thin{ font-weight:300; color:var(--flow); letter-spacing:-.03em }
.lede{ font:400 33px/1.42 "Be Vietnam Pro",sans-serif; color:var(--muted); margin:36px 0 0 }
.w900{ max-width:900px }
b{ font-weight:700; color:var(--ink) }

/* ---- hero hydrograph ---- */
.hero-chart{ position:absolute; left:0; right:0; bottom:0; height:560px; z-index:1 }
.hero-chart svg{ width:1920px; height:560px; display:block }
.bands{ position:absolute; left:0; right:120px; top:0; height:560px }
.band{ position:absolute; left:0; right:0; height:1px }
.band span{ position:absolute; right:0; top:-28px; font:700 17px/1 "JetBrains Mono",monospace; letter-spacing:.12em }
.bd1{ background:rgba(232,190,85,.32) } .bd1 span{ color:var(--bd1) }
.bd2{ background:rgba(224,131,60,.36) } .bd2 span{ color:var(--bd2) }
.bd3{ background:rgba(210,69,59,.42) }  .bd3 span{ color:var(--bd3) }
.chart-cap{ position:absolute; left:120px; bottom:78px; font:400 17px/1 "JetBrains Mono",monospace;
  letter-spacing:.1em; color:rgba(109,143,153,.8) }

.byline{ position:absolute; right:120px; top:92px; text-align:right; z-index:3;
  font:400 22px/1.7 "Be Vietnam Pro",sans-serif; color:var(--muted) }
.byline b{ display:block; margin-bottom:4px; color:var(--ink); font-weight:600 }

.figrow{ display:flex; gap:76px; margin-top:54px }
.fig .n{ display:block; font:700 50px/1 "JetBrains Mono",monospace; letter-spacing:-.03em }
.fig .n u{ text-decoration:none; font-size:23px; color:var(--muted); margin-left:5px }
.fig .k{ display:block; margin-top:11px; max-width:230px;
  font:500 15px/1.4 "JetBrains Mono",monospace; letter-spacing:.14em; color:var(--muted);
  white-space:nowrap }

/* ---- two-column ---- */
.col2{ display:grid; grid-template-columns:1fr 620px; gap:92px; align-items:center }
.col2b{ display:grid; grid-template-columns:840px 1fr; gap:88px; align-items:center }
.col2c{ display:grid; grid-template-columns:1fr 1fr; gap:90px; margin-top:58px }

ul.big{ list-style:none; margin:0; padding:0 }
ul.big li{ position:relative; padding-left:44px; margin-bottom:28px;
  font:400 30px/1.42 "Be Vietnam Pro",sans-serif; color:var(--muted); max-width:820px }
ul.big li::before{ content:""; position:absolute; left:0; top:18px; width:22px; height:2px; background:var(--flow) }

/* ---- side panel ---- */
.panel{ background:rgba(12,34,43,.72); border:1px solid var(--edge); padding:44px 42px; align-self:center }
.panel-h{ font:700 18px/1 "JetBrains Mono",monospace; letter-spacing:.2em; color:var(--flow) }
.panel-s{ font:400 19px/1.4 "Be Vietnam Pro",sans-serif; color:var(--dim); margin-top:12px }
.panel-f{ font:400 18px/1.5 "Be Vietnam Pro",sans-serif; color:var(--dim); margin-top:34px }

.gauge{ margin-top:36px; display:flex; flex-direction:column; gap:22px }
.grow{ display:grid; grid-template-columns:96px 1fr 104px; align-items:center; gap:18px }
.grow .lv{ font:700 22px/1 "JetBrains Mono",monospace }
.grow .bar{ height:12px; background:rgba(47,194,204,.14); display:block }
.grow .bar i{ display:block; height:100%; transform-origin:left; animation:gw .9s cubic-bezier(.2,.7,.2,1) both }
.f1{ background:var(--bd1); animation-delay:.3s } .f2{ background:var(--bd2); animation-delay:.42s }
.f3{ background:var(--bd3); animation-delay:.54s }
@keyframes gw{ from{ transform:scaleX(0) } to{ transform:scaleX(1) } }
.grow .m{ text-align:right; font:500 22px/1 "JetBrains Mono",monospace; color:var(--flow) }

/* ---- quadrants ---- */
.quad{ display:grid; grid-template-columns:1fr 1fr; gap:34px }
.q{ background:rgba(12,34,43,.6); border:1px solid var(--edge); padding:36px 38px }
.q.hot{ border-color:rgba(210,69,59,.55); background:rgba(45,20,18,.5) }
.qn{ display:block; font:700 30px/1 "Be Vietnam Pro",sans-serif; color:var(--flow); margin-bottom:16px }
.q.hot .qn{ color:var(--bd3) }
.q p{ margin:0; font:400 24px/1.46 "Be Vietnam Pro",sans-serif; color:var(--muted) }

/* ---- numbered steps ---- */
.steps{ display:flex; flex-direction:column; gap:34px }
.step{ display:grid; grid-template-columns:104px 1fr; gap:34px; align-items:start;
  border-top:1px solid var(--edge); padding-top:30px }
.step .sn{ font:700 54px/1 "JetBrains Mono",monospace; color:var(--dim); letter-spacing:-.04em }
.step.hot .sn{ color:var(--bd2) }
.step p{ margin:0; font:400 26px/1.45 "Be Vietnam Pro",sans-serif; color:var(--muted); max-width:1250px }

/* ---- four cards ---- */
.four{ display:grid; grid-template-columns:repeat(4,1fr); gap:26px }
.c{ background:rgba(12,34,43,.6); border:1px solid var(--edge); padding:34px 30px }
.c.core{ border-color:var(--flow); background:rgba(17,62,72,.6) }
.c.out{ opacity:.58 }
.ct{ display:block; font:700 14px/1 "JetBrains Mono",monospace; letter-spacing:.18em; color:var(--muted); margin-bottom:18px }
.c.core .ct{ color:var(--flow) }
.c h3{ font-size:34px; margin-bottom:14px }
.c.core h3{ color:var(--flow) }
.c p{ margin:0; font:400 21px/1.42 "Be Vietnam Pro",sans-serif; color:var(--muted) }
.claim{ margin:46px 0 0; font:400 27px/1.45 "Be Vietnam Pro",sans-serif; color:var(--muted); max-width:1450px }
.claim.warn{ color:var(--bd2) }

/* ---- table ---- */
table.dt{ width:100%; border-collapse:collapse }
table.dt th{ text-align:left; font:700 17px/1 "JetBrains Mono",monospace; letter-spacing:.14em;
  color:var(--flow); padding:0 0 18px; border-bottom:1.5px solid var(--flow) }
table.dt td{ font:400 24px/1.35 "Be Vietnam Pro",sans-serif; color:var(--muted);
  padding:19px 22px 19px 0; border-bottom:1px solid var(--edge) }
table.dt td:first-child{ color:var(--ink) }
tr.crit td{ color:var(--bd2) } tr.crit td:first-child{ color:var(--bd2) }
td.ok{ font:500 19px/1 "JetBrains Mono",monospace; color:var(--flow) }
td.wip{ font:500 19px/1 "JetBrains Mono",monospace; color:var(--bd2) }

/* ---- pipeline ---- */
.flow{ display:grid; grid-template-columns:1fr 46px 1fr 46px 1fr 46px 1fr; align-items:stretch; gap:0 }
.fstep{ background:rgba(12,34,43,.6); border:1px solid var(--edge); padding:32px 28px }
.fn{ display:block; font:700 24px/1 "JetBrains Mono",monospace; color:var(--bd1); margin-bottom:16px }
.fstep h3{ font-size:30px }
.fstep p{ margin:0; font:400 20px/1.4 "Be Vietnam Pro",sans-serif; color:var(--muted) }
.farrow{ display:flex; align-items:center; justify-content:center; font-size:26px; color:var(--dim) }
.lesson{ margin-top:46px; border-left:3px solid var(--bd2); padding:6px 0 6px 34px }
.lt{ display:block; font:700 16px/1 "JetBrains Mono",monospace; letter-spacing:.2em; color:var(--bd2); margin-bottom:16px }
.lesson p{ margin:0; font:400 26px/1.46 "Be Vietnam Pro",sans-serif; color:var(--muted); max-width:1500px }

/* ---- lag chart ---- */
.lagchart{ background:rgba(12,34,43,.6); border:1px solid var(--edge); padding:38px 40px 30px }
.lc-h{ font:700 18px/1 "JetBrains Mono",monospace; letter-spacing:.16em; color:var(--flow); margin-bottom:34px }
.lc-bars{ display:flex; align-items:flex-end; gap:30px; height:330px }
.lb{ flex:1; display:flex; flex-direction:column; align-items:center; height:100% ; justify-content:flex-end }
.lb i{ display:block; width:100%; background:rgba(47,194,204,.28); transform-origin:bottom;
  animation:bgrow .8s cubic-bezier(.2,.7,.2,1) both }
.lb:nth-child(1) i{animation-delay:.25s} .lb:nth-child(2) i{animation-delay:.35s}
.lb:nth-child(3) i{animation-delay:.45s} .lb:nth-child(4) i{animation-delay:.55s}
.lb:nth-child(5) i{animation-delay:.65s} .lb:nth-child(6) i{animation-delay:.75s}
@keyframes bgrow{ from{ transform:scaleY(0) } to{ transform:scaleY(1) } }
.lb.top i{ background:var(--flow) }
.lb span{ font:500 19px/1 "JetBrains Mono",monospace; color:var(--muted); margin-top:16px }
.lb b{ font:700 20px/1 "JetBrains Mono",monospace; color:var(--muted); margin-top:8px }
.lb.top b{ color:var(--flow) }

/* ---- closing ---- */
.closing{ background:radial-gradient(1400px 900px at 22% 78%, #0F2E3A 0%, transparent 62%), #050F14 }
h1.big-claim{ font-weight:800; font-size:86px; line-height:1.1; letter-spacing:-.035em;
  margin:0; max-width:1560px }
.ch{ display:block; font:700 17px/1 "JetBrains Mono",monospace; letter-spacing:.2em;
  color:var(--flow); margin-bottom:26px }
.ch.warnc{ color:var(--bd2) }
ol.nx, ul.nx{ margin:0; padding-left:30px }
ol.nx li, ul.nx li{ font:400 25px/1.45 "Be Vietnam Pro",sans-serif; color:var(--muted); margin-bottom:20px }
.lim{ border-left:1px solid var(--edge); padding-left:56px }
.thanks{ margin:64px 0 0; font:300 34px/1 "Be Vietnam Pro",sans-serif; color:var(--flow) }

/* ---- deck chrome (outside the slide design system) ---- */
.hud{ position:fixed; z-index:1000; font:500 15px/1 "JetBrains Mono",monospace;
  letter-spacing:.14em; color:rgba(109,143,153,.75) }
.hud.count{ right:26px; bottom:22px }
.hud.hint{ left:26px; bottom:20px; opacity:.45 }
.hud.hint:hover{ opacity:1 }
.prog{ position:fixed; left:0; top:0; height:3px; background:var(--flow); z-index:1001;
  transition:width .35s cubic-bezier(.2,.7,.2,1) }
.notes{ position:fixed; left:0; right:0; bottom:0; max-height:36vh; overflow:auto;
  background:rgba(3,10,14,.96); border-top:1px solid var(--edge); padding:26px 34px;
  font:400 17px/1.6 "Be Vietnam Pro",sans-serif; color:#B9D3D9; z-index:1002; display:none }
.notes.on{ display:block }
.notes b{ color:var(--flow); font:700 14px/1 "JetBrains Mono",monospace; letter-spacing:.2em;
  display:block; margin-bottom:12px }

/* slide entry choreography */
.slide.active .pad > *{ animation:rise .8s cubic-bezier(.2,.7,.2,1) both }
.slide.active .pad > *:nth-child(1){ animation-delay:.06s }
.slide.active .pad > *:nth-child(2){ animation-delay:.16s }
.slide.active .pad > *:nth-child(3){ animation-delay:.26s }
.slide.active .pad > *:nth-child(4){ animation-delay:.36s }
.slide.active .pad > *:nth-child(5){ animation-delay:.46s }
@keyframes rise{ from{ transform:translateY(26px) } to{ transform:none } }
/* Noi dung luon hien du animation khong chay — xem ghi chu trong build_deck.py */
@media print{ .slide .pad > *, .slide .trace, .slide .area, .slide .band,
  .slide .grow .bar i, .slide .lb i{ animation:none !important; opacity:1 !important;
  transform:none !important; stroke-dashoffset:0 !important } }
.slide.active .trace{ stroke-dasharray:__TRACELEN__; stroke-dashoffset:__TRACELEN__;
  animation:draw 2.8s .5s cubic-bezier(.35,.6,.25,1) forwards }
@keyframes draw{ to{ stroke-dashoffset:0 } }
.slide.active .area{ animation:fade 1.6s 1.6s ease backwards }
@keyframes fade{ from{ opacity:0 } to{ opacity:1 } }
.slide.active .band{ transform-origin:left center; animation:gw 1s both }
.slide.active .bd1{ animation-delay:1.0s } .slide.active .bd2{ animation-delay:1.14s }
.slide.active .bd3{ animation-delay:1.28s }

[contenteditable]:focus{ outline:2px solid var(--flow); outline-offset:6px }
"""

JS = """
(function(){
  var stage=document.getElementById('stage');
  var slides=[].slice.call(document.querySelectorAll('.slide'));
  var i=0, notes=document.getElementById('notes'), prog=document.getElementById('prog'),
      count=document.getElementById('count');

  function fit(){
    var s=Math.min(innerWidth/1920, innerHeight/1080);
    stage.style.transform='translate('+((innerWidth-1920*s)/2)+'px,'+
      ((innerHeight-1080*s)/2)+'px) scale('+s+')';
  }
  function show(n){
    i=Math.max(0, Math.min(slides.length-1, n));
    slides.forEach(function(s,k){ s.classList.toggle('active', k===i); });
    count.textContent=String(i+1).padStart(2,'0')+' / '+String(slides.length).padStart(2,'0');
    prog.style.width=((i+1)/slides.length*100)+'%';
    notes.innerHTML='<b>SPEAKER NOTES</b>'+(slides[i].dataset.notes||'');
    location.hash='s'+(i+1);
  }
  addEventListener('resize',fit);
  addEventListener('keydown',function(e){
    if(e.target.isContentEditable) return;
    if(['ArrowRight','ArrowDown','PageDown',' '].indexOf(e.key)>-1){ e.preventDefault(); show(i+1); }
    else if(['ArrowLeft','ArrowUp','PageUp'].indexOf(e.key)>-1){ e.preventDefault(); show(i-1); }
    else if(e.key==='Home'){ show(0); } else if(e.key==='End'){ show(slides.length-1); }
    else if(e.key==='s'||e.key==='S'){ notes.classList.toggle('on'); }
    else if(e.key==='e'||e.key==='E'){
      var on=document.body.dataset.edit==='1';
      document.body.dataset.edit=on?'0':'1';
      document.querySelectorAll('.slide h1,.slide h2,.slide h3,.slide p,.slide li,.slide td')
        .forEach(function(el){ el.contentEditable=on?'false':'true'; });
    }
  });
  addEventListener('click',function(e){
    if(e.target.isContentEditable||document.body.dataset.edit==='1') return;
    show(e.clientX < innerWidth*0.28 ? i-1 : i+1);
  });
  var m=(location.hash.match(/^#s(\\d+)$/));
  fit(); show(m?parseInt(m[1],10)-1:0);
})();
"""


def main() -> int:
    hg = hydrograph()
    css = CSS.replace("__TRACELEN__", str(hg["len"]))
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSP391m · Report 1 — Forecasting Flood Risk, Hương River</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>{css}</style>
</head>
<body>
<div class="prog" id="prog"></div>
<div class="deck-viewport">
  <div class="deck-stage" id="stage">
{slides(hg)}
  </div>
</div>
<div class="hud hint">← → navigate &nbsp;·&nbsp; S speaker notes &nbsp;·&nbsp; E edit text</div>
<div class="hud count" id="count">01 / 09</div>
<div class="notes" id="notes"></div>
<script>{JS}</script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"→ {OUT}  ({len(html) // 1024} KB)")
    print(f"   hydrograph: {hg['n']} ngày thật, đỉnh {hg['peak_q']:,.0f} m³/s "
          f"ngày {hg['peak_date']}")
    print(f"   số slide: {html.count('<section class=')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
