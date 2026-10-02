"""Trang kể chuyện có chuyển động — "chúng ta đang làm gì" trong 5 cảnh.

    python -m src.viz.explainer

Sinh hai file trong `reports/explainer/`:

* `flood_story.html`        — bản để publish thành Artifact (không có thẻ html/head)
* `flood_story_local.html`  — bản đầy đủ, mở thẳng bằng trình duyệt khi thuyết trình

Mọi con số và mọi điểm trên hình đều lấy từ dữ liệu thật của dự án:
mưa từng ô lưới, lưu lượng, 361 ô dò, và dự báo LightGBM ngoài mẫu cho trận
lũ tháng 10/2025 (nằm trong tập test, mô hình chưa từng thấy).
"""

from __future__ import annotations

import glob
import json
import re
import sys

import numpy as np
import pandas as pd

from src import config as cfg
from src.eval import walk_forward
from src.features.build_panel import SUBBASINS
from src.features.risk_levels import FLOOD_MONTHS, QUANTILES
from src.models.lgbm import PARAMS, feature_cols

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAW = cfg.ROOT / "data" / "raw"
PANEL = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
OUTDIR = cfg.ROOT / "reports" / "explainer"
STATION = (16.47, 107.57)          # trạm Kim Long — FINDINGS_GRID.md §2
LARGEST = (16.60, 107.55)          # ô lưu lượng lớn nhất, gộp cả sông Bồ


def _cell(f: str, rx: str):
    m = re.search(rx, f.replace("\\", "/"))
    return (float(m.group(1)), float(m.group(2))) if m else None


def rain_scene(start="2020-10-03", end="2020-10-24") -> dict:
    frames = []
    for f in glob.glob(str(RAW / "rain_daily" / "rd_*.parquet")):
        d = pd.read_parquet(f, columns=["time", "precipitation_sum", "lat", "lon"])
        d["time"] = pd.to_datetime(d["time"])
        frames.append(d[(d["time"] >= start) & (d["time"] <= end)])
    r = pd.concat(frames)
    cells = sorted({(float(a), float(b)) for a, b in zip(r["lat"], r["lon"])})
    days = sorted(r["time"].unique())
    piv = r.pivot_table(index="time", columns=["lat", "lon"], values="precipitation_sum")
    grid = [[round(float(piv.loc[t, c]), 1) for c in cells] for t in days]

    def band(lat):
        for name, (lo, hi) in SUBBASINS.items():
            if lo <= lat < hi:
                return name
        return "other"

    p = pd.read_parquet(PANEL, columns=["date", "discharge", "rain_basin"])
    p["date"] = pd.to_datetime(p["date"])
    w = p[(p["date"] >= start) & (p["date"] <= end)].reset_index(drop=True)
    q = w["discharge"].round(0).tolist()
    rb = w["rain_basin"].round(1).tolist()

    # cặp (ngày đỉnh mưa cục bộ → ngày đỉnh sông cục bộ) để chú thích độ trễ
    pairs = []
    for i in range(1, len(q) - 1):
        if q[i] > q[i - 1] and q[i] >= q[i + 1] and q[i] > 800:
            js = [j for j in range(max(1, i - 3), i) if rb[j] >= rb[j - 1] and rb[j] >= rb[j + 1]]
            if js:
                pairs.append([js[-1], i])
    return {"cells": [[a, b, band(a)] for a, b in cells],
            "days": [pd.Timestamp(t).strftime("%d %b") for t in days],
            "rain": grid, "q": q, "rb": rb, "pairs": pairs,
            "rmax": float(np.nanmax(grid))}


def probe_scene() -> dict:
    qm = {}
    for f in glob.glob(str(RAW / "discharge" / "*.parquet")) + \
            glob.glob(str(RAW / "discharge_probe" / "*.parquet")):
        d = pd.read_parquet(f, columns=["time", "river_discharge", "lat", "lon"])
        k = (round(float(d["lat"].iloc[0]), 2), round(float(d["lon"].iloc[0]), 2))
        if k in qm:
            continue
        t = pd.to_datetime(d["time"])
        s = d.loc[(t >= "2023-01-01") & (t <= "2023-12-31"), "river_discharge"]
        qm[k] = round(float(s.mean()), 1) if s.notna().any() else None
    full = {_cell(f, r"q_([\d.]+)_([\d.]+)\.parquet")
            for f in glob.glob(str(RAW / "discharge" / "*.parquet"))}
    grid = [(round(16.05 + 0.05 * i, 2), round(107.05 + 0.05 * j, 2))
            for i in range(19) for j in range(19)]
    cells = []
    for c in grid:
        v = qm.get(c)
        cells.append([c[0], c[1], v if (v is not None and v > 0) else None,
                      1 if (c in full) else 0])
    return {"cells": cells, "chosen": list(cfg.RIVER_POINTS["huong_kim_long"]),
            "station": list(STATION), "largest": list(LARGEST)}


def files_scene() -> dict:
    kinds = [("rain_hourly", "hourly rain"), ("discharge_probe", "flow probes"),
             ("discharge", "full flow"), ("rain_daily", "daily rain"),
             ("fc_rain", "forecast rain")]
    out = [{"k": lbl, "n": len(glob.glob(str(RAW / k / "*.parquet")))} for k, lbl in kinds]
    p = pd.read_parquet(PANEL)
    return {"kinds": out, "total": sum(o["n"] for o in out),
            "rows": int(len(p)), "cols": int(p.shape[1])}


def forecast_scene(start="2025-10-08", end="2025-11-25") -> dict:
    from lightgbm import LGBMRegressor
    p = pd.read_parquet(PANEL)
    p["date"] = pd.to_datetime(p["date"])
    sp = walk_forward.regime_split(pd.DatetimeIndex(p["date"]))
    tr = p["date"].isin(sp["train"]) | p["date"].isin(sp["valid"])
    feats = feature_cols(p)
    y = p["target_h1"]
    ok = p[feats].notna().all(axis=1) & y.notna()
    m = LGBMRegressor(**PARAMS)
    m.fit(p.loc[tr & ok, feats], np.log1p(y[tr & ok]))
    win = ok & (p["date"] >= start) & (p["date"] <= end)
    pred = np.clip(np.expm1(m.predict(p.loc[win, feats])), 0, None)
    # dự báo phát ngày t cho ngày t+1 → vẽ theo ngày t+1
    dates = (p.loc[win, "date"] + pd.Timedelta(days=1)).dt.strftime("%d %b").tolist()
    s = p.loc[tr & p["date"].dt.month.isin(FLOOD_MONTHS), "discharge"].dropna()
    thr = [round(float(s.quantile(q))) for q in QUANTILES.values()]
    res = pd.read_csv(cfg.ROOT / "reports" / "lgbm_results.csv")
    nse1 = float(res.loc[res["horizon"] == 1, "NSE"].iloc[0])
    pers = pd.read_csv(cfg.ROOT / "reports" / "baseline_results.csv")
    nse_p = float(pers[(pers.model == "persistence") & (pers.horizon == 1)]["NSE"].iloc[0])
    return {"dates": dates, "obs": y[win].round(0).tolist(),
            "pred": np.round(pred, 0).tolist(), "thr": thr,
            "nse": round(nse1, 3), "nse_p": round(nse_p, 3)}


TEMPLATE = r"""<title>Huong River Flood Story</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;500;700;900&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
/* Layout: one 16:9 stage scaled to the window, five scenes stepped like slides. */
:root{
  color-scheme:dark;
  --water:#07141A; --deep:#0C222B; --edge:#16313C;
  --ink:#EAF4F5; --muted:#8BA8B1; --dim:#46646E;
  --flow:#2FC2CC; --rain:#7FA7D9;
  --r1:#E8BE55; --r2:#E0833C; --r3:#E8665C;
  --display:"Be Vietnam Pro",system-ui,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Consolas,monospace;
}
html,body{height:100%;margin:0;background:var(--water);color:var(--ink);overflow:hidden}
body{font-family:var(--display)}
.viewport{position:fixed;inset:0;display:grid;place-items:center}
.stage{width:1600px;height:900px;position:relative;transform-origin:center center;flex:none}
.scene{position:absolute;inset:0;padding:64px 80px;box-sizing:border-box;
  visibility:hidden;pointer-events:none}
.scene.on{visibility:visible;pointer-events:auto}
.kick{font:600 15px/1 var(--mono);letter-spacing:.18em;color:var(--flow);text-transform:uppercase}
h1{font:900 64px/1.02 var(--display);letter-spacing:-.03em;margin:14px 0 10px;text-wrap:balance}
h1 .t{font-weight:300;color:var(--flow)}
.sub{font:300 23px/1.45 var(--display);color:var(--muted);max-width:820px;margin:0}
.sub b{color:var(--ink);font-weight:500}
svg text{font-family:var(--mono)}
.nav{position:fixed;left:50%;bottom:calc(18px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);
  display:flex;gap:10px;align-items:center;z-index:5}
.nav button{background:var(--deep);color:var(--ink);border:1px solid var(--edge);
  font:500 14px/1 var(--mono);padding:10px 14px;cursor:pointer}
.nav button:hover{border-color:var(--flow)}
.nav button:focus-visible{outline:2px solid var(--flow);outline-offset:2px}
.dots{display:flex;gap:8px;margin:0 6px}
.dots i{width:9px;height:9px;border-radius:50%;background:var(--dim);display:block}
.dots i.on{background:var(--flow)}
.big{font:900 120px/1 var(--display);letter-spacing:-.04em;font-variant-numeric:tabular-nums}
.lab{font:500 15px/1.3 var(--mono);color:var(--muted);letter-spacing:.06em;text-transform:uppercase}
.row{display:flex;gap:56px;align-items:flex-start}
.date{font:900 88px/1 var(--display);letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.callout{font:600 22px/1.3 var(--display);color:var(--ink)}
.legend{display:flex;gap:22px;font:500 14px/1 var(--mono);color:var(--muted);margin-top:14px}
.legend span{display:flex;gap:8px;align-items:center}
.sw{width:14px;height:14px;display:inline-block}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<div class="viewport"><div class="stage" id="stage">

<section class="scene on" id="s0">
  <div class="kick">Huong River basin · Hue, Vietnam</div>
  <h1>Where the rain falls <span class="t">before the city floods</span></h1>
  <p class="sub">The basin is covered by a grid of <b>64 rainfall cells</b>, grouped
    into three sub-basins. Rain falls in the mountains, then runs down to
    <b>Kim Long</b> station in Hue.</p>
  <svg id="map0" viewBox="0 0 1440 620" style="position:absolute;left:80px;top:250px;width:1440px;height:620px"></svg>
</section>

<section class="scene" id="s1">
  <div class="kick">October 2020 · real daily data</div>
  <h1>Rain falls, <span class="t">the river answers a day later</span></h1>
  <div class="row" style="margin-top:22px">
    <svg id="map1" viewBox="0 0 560 560" style="width:560px;height:560px;flex:none"></svg>
    <div style="flex:1;min-width:0">
      <div class="date" id="d1">03 Oct</div>
      <div class="lab" id="r1lab">basin rain 0 mm</div>
      <svg id="ch1" viewBox="0 0 820 400" style="width:820px;height:400px;margin-top:18px"></svg>
      <div class="callout" id="call1">&nbsp;</div>
    </div>
  </div>
</section>

<section class="scene" id="s2">
  <div class="kick">Data collection</div>
  <h1>361 places to look, <span class="t">one real river</span></h1>
  <div class="row" style="margin-top:10px">
    <svg id="map2" viewBox="0 0 640 640" style="width:640px;height:640px;flex:none"></svg>
    <div style="flex:1;min-width:0;padding-top:40px">
      <div class="big" id="cnt2">361</div>
      <div class="lab" id="lab2">grid cells checked with one year of data</div>
      <p class="sub" id="txt2" style="margin-top:34px">The flood model draws rivers on a 5 km grid,
        so we do not know in advance which cell is our river.</p>
    </div>
  </div>
</section>

<section class="scene" id="s3">
  <div class="kick">Data cleaning</div>
  <h1>Many files, <span class="t">one table</span></h1>
  <svg id="ch3" viewBox="0 0 1440 600" style="position:absolute;left:80px;top:250px;width:1440px;height:600px"></svg>
</section>

<section class="scene" id="s4">
  <div class="kick">Forecast · a flood the model never saw</div>
  <h1>Tomorrow's river, <span class="t">predicted today</span></h1>
  <p class="sub" id="txt4">October 2025 is in the test period. The model was trained on
    earlier years only, then asked to forecast each next day.</p>
  <svg id="ch4" viewBox="0 0 1440 520" style="position:absolute;left:80px;top:300px;width:1440px;height:520px"></svg>
</section>

</div></div>

<nav class="nav" aria-label="Scenes">
  <button id="prev" type="button" aria-label="Previous scene">&larr;</button>
  <div class="dots" id="dots"></div>
  <button id="next" type="button" aria-label="Next scene">&rarr;</button>
  <button id="replay" type="button">Replay</button>
</nav>

<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
var D = JSON.parse(document.getElementById('data').textContent);
var NS = 'http://www.w3.org/2000/svg';
var REDUCED = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
function el(tag, a, parent){ var e=document.createElementNS(NS,tag);
  for (var k in a) e.setAttribute(k,a[k]); if(parent) parent.appendChild(e); return e; }
function txt(parent,x,y,s,a){ var t=el('text',Object.assign({x:x,y:y,fill:'#8BA8B1','font-size':13},a||{}),parent); t.textContent=s; return t; }
function clear(s){ while(s.firstChild) s.removeChild(s.firstChild); }
var timers=[];
function later(fn,ms){ timers.push(setTimeout(fn, REDUCED?0:ms)); }
function stopAll(){ timers.forEach(clearTimeout); timers=[]; if(play.id){cancelAnimationFrame(play.id);play.id=null;} }
var play={id:null};

/* ---------- scale stage ---------- */
var stage=document.getElementById('stage');
function fit(){ var s=Math.min(innerWidth/1600,(innerHeight-60)/900); stage.style.transform='scale('+s+')'; }
addEventListener('resize',fit); fit();

/* ---------- colour ramps (single hue, light -> dark on dark ground) ---------- */
function mix(a,b,t){ var p=function(h){return [1,3,5].map(function(i){return parseInt(h.substr(i,2),16);});};
  var x=p(a),y=p(b); return 'rgb('+x.map(function(v,i){return Math.round(v+(y[i]-v)*t);}).join(',')+')'; }
function rainCol(v){ var t=Math.min(1,Math.sqrt(Math.max(0,v)/D.rain.rmax)); return mix('#0C222B','#9CC3EE',t); }
function flowCol(v){ var t=Math.log10(1+v)/Math.log10(1+340); return mix('#123540','#7FE9EF',Math.min(1,t)); }

/* ---------- shared map projection for the rain grid ---------- */
var RB={latMin:16.05,latMax:16.85,lonMin:107.05,lonMax:107.85};
function proj(lat,lon,x0,y0,size){ return [x0+(lon-RB.lonMin)/(RB.lonMax-RB.lonMin)*size,
  y0+(RB.latMax-lat)/(RB.latMax-RB.latMin)*size]; }
function drawRainGrid(svg,x0,y0,size){
  var cs=size/8*0.82, nodes=[];
  D.rain.cells.forEach(function(c){ var p=proj(c[0],c[1],x0,y0,size);
    nodes.push(el('rect',{x:p[0]-cs/2,y:p[1]-cs/2,width:cs,height:cs,rx:3,fill:'#0C222B',
      stroke:'#16313C','stroke-width':1},svg)); });
  return nodes;
}

/* ================= scene 0: the basin ================= */
function scene0(){
  var s=document.getElementById('map0'); clear(s);
  var size=560, x0=440, y0=20;
  var bands={thuong:'Upper basin',trung:'Middle basin',ha:'Lower basin'};
  var bandCol={thuong:'#1E4F5C',trung:'#2B6C7A',ha:'#1A3F4A'};
  D.rain.cells.forEach(function(c,i){ var p=proj(c[0],c[1],x0,y0,size), cs=size/8*0.82;
    var r=el('rect',{x:p[0]-cs/2,y:p[1]-cs/2,width:cs,height:cs,rx:3,fill:bandCol[c[2]]||'#16313C',
      style:'transform-origin:'+p[0]+'px '+p[1]+'px;transform:scale(.55);opacity:.35;transition:transform .5s ease, opacity .5s ease'},s);
    later(function(){ r.style.transform='scale(1)'; r.style.opacity='1'; }, 40+ (7-Math.round((c[0]-16.1)*10))*90 + Math.round((c[1]-107.1)*10)*25);
  });
  [['thuong',16.22],['trung',16.45],['ha',16.70]].forEach(function(b,i){
    var p=proj(b[1],107.85,x0,y0,size);
    var t=txt(s,p[0]+26,p[1]+5,bands[b[0]],{fill:'#EAF4F5','font-size':18,style:'opacity:.4;transition:opacity .6s'});
    later(function(){ t.style.opacity='1'; }, 900+i*180);
  });
  var st=proj(D.probe.station[0],D.probe.station[1],x0,y0,size);
  var ch=proj(D.probe.chosen[0],D.probe.chosen[1],x0,y0,size);
  var g=el('g',{style:'opacity:.3;transition:opacity .6s'},s);
  el('circle',{cx:ch[0],cy:ch[1],r:14,fill:'none',stroke:'#7FE9EF','stroke-width':3},g);
  el('circle',{cx:st[0],cy:st[1],r:7,fill:'#E8BE55'},g);
  txt(g,x0-24,ch[1]+5,'forecast cell',{fill:'#7FE9EF','font-size':16,'text-anchor':'end'});
  txt(g,x0-24,st[1]-22,'Kim Long station',{fill:'#E8BE55','font-size':16,'text-anchor':'end'});
  el('line',{x1:x0-18,y1:ch[1],x2:ch[0]-16,y2:ch[1],stroke:'#7FE9EF','stroke-width':1},g);
  el('line',{x1:x0-18,y1:st[1]-26,x2:st[0]-8,y2:st[1]-3,stroke:'#E8BE55','stroke-width':1},g);
  later(function(){ g.style.opacity='1'; }, 1500);
  txt(s,x0,y0+size+32,'0.1° grid  ·  about 11 km per cell',{'font-size':14});
}

/* ================= scene 1: rain -> river playback ================= */
function scene1(){
  var m=document.getElementById('map1'); clear(m);
  var cells=drawRainGrid(m,10,10,540);
  var c=document.getElementById('ch1'); clear(c);
  var W=820,H=400, pl=56, pr=150, pt=10, ph=110, gap=36, qt=pt+ph+gap, qh=H-qt-34;
  var n=D.rain.q.length, bw=(W-pl-pr)/n;
  var qmax=Math.max.apply(null,D.rain.q.concat([D.fc.thr[2]]))*1.08;
  var rmaxb=Math.max.apply(null,D.rain.rb)*1.1;
  function X(i){ return pl+bw*(i+0.5); }
  function YQ(v){ return qt+qh-(v/qmax)*qh; }
  txt(c,pl,pt+6,'rain, mm/day',{'font-size':12});
  txt(c,pl,qt-6,'river discharge, m³/s',{'font-size':12});
  el('line',{x1:pl,y1:pt+ph,x2:W-pr,y2:pt+ph,stroke:'#16313C'},c);
  el('line',{x1:pl,y1:qt+qh,x2:W-pr,y2:qt+qh,stroke:'#16313C'},c);
  var cols=['#E8BE55','#E0833C','#E8665C'], names=['risk 1','risk 2','risk 3'];
  D.fc.thr.forEach(function(v,i){ var y=YQ(v);
    el('line',{x1:pl,y1:y,x2:W-pr,y2:y,stroke:cols[i],'stroke-width':1,'stroke-dasharray':'5 4'},c);
    txt(c,W-pr+8,y+4,names[i]+' · '+v,{fill:'#EAF4F5','font-size':12}); });
  var bars=D.rain.rb.map(function(v,i){ var h=v/rmaxb*ph;
    return el('rect',{x:X(i)-bw*0.38,y:pt+ph-h,width:bw*0.76,height:h,rx:2,fill:'#7FA7D9',opacity:0.18},c); });
  var line=el('path',{d:'',fill:'none',stroke:'#2FC2CC','stroke-width':3,'stroke-linejoin':'round'},c);
  var dot=el('circle',{cx:X(0),cy:YQ(D.rain.q[0]),r:6,fill:'#2FC2CC',stroke:'#07141A','stroke-width':2},c);
  [0,Math.floor(n/2),n-1].forEach(function(i){ txt(c,X(i),qt+qh+22,D.rain.days[i],{'text-anchor':'middle','font-size':12}); });
  var lagMarks=el('g',{},c);
  var dEl=document.getElementById('d1'), rl=document.getElementById('r1lab'), call=document.getElementById('call1');
  call.innerHTML='&nbsp;';
  function frame(i){
    D.rain.rain[i].forEach(function(v,k){ cells[k].setAttribute('fill',rainCol(v)); });
    bars.forEach(function(b,k){ b.setAttribute('opacity',k<=i?1:0.18); });
    var d=''; for(var k=0;k<=i;k++) d+=(k?'L':'M')+X(k).toFixed(1)+','+YQ(D.rain.q[k]).toFixed(1);
    line.setAttribute('d',d); dot.setAttribute('cx',X(i)); dot.setAttribute('cy',YQ(D.rain.q[i]));
    dEl.textContent=D.rain.days[i];
    rl.textContent='basin rain '+Math.round(D.rain.rb[i])+' mm  ·  river '+Math.round(D.rain.q[i]).toLocaleString('en')+' m³/s';
    D.rain.pairs.forEach(function(p){ if(p[1]===i){
      var y=YQ(D.rain.q[i])-22;
      el('line',{x1:X(p[0]),y1:y,x2:X(i)-6,y2:y,stroke:'#EAF4F5','stroke-width':2},lagMarks);
      el('path',{d:'M'+(X(i)-6)+','+(y-5)+' L'+X(i)+','+y+' L'+(X(i)-6)+','+(y+5)+'Z',fill:'#EAF4F5'},lagMarks);
      var t=txt(lagMarks,(X(p[0])+X(i))/2,y-8,'1 day',{fill:'#EAF4F5','font-size':13,'text-anchor':'middle'});
      call.textContent='Rain peaked on '+D.rain.days[p[0]]+'. The river peaked the next day.';
    }});
  }
  if(REDUCED){ frame(n-1); return; }
  var i=0; frame(0);
  var t0=null, step=520;
  function tick(ts){ if(t0===null) t0=ts; var k=Math.min(n-1,Math.floor((ts-t0)/step));
    while(i<k){ i++; frame(i); } if(i<n-1) play.id=requestAnimationFrame(tick); else play.id=null; }
  later(function(){ play.id=requestAnimationFrame(tick); }, 600);
}

/* ================= scene 2: 361 -> 1 ================= */
function scene2(){
  var s=document.getElementById('map2'); clear(s);
  var B={latMin:16.05,latMax:16.95,lonMin:107.05,lonMax:107.95}, size=600, x0=20,y0=20, cs=size/19*0.78;
  function P(lat,lon){ return [x0+(lon-B.lonMin)/(B.lonMax-B.lonMin)*(size-cs)+cs/2,
                               y0+(B.latMax-lat)/(B.latMax-B.latMin)*(size-cs)+cs/2]; }
  var nodes=D.probe.cells.map(function(c){ var p=P(c[0],c[1]);
    return {c:c,r:el('rect',{x:p[0]-cs/2,y:p[1]-cs/2,width:cs,height:cs,rx:2,fill:'#2A4650',
      style:'transition:fill .7s ease, opacity .7s ease'},s)}; });
  var cnt=document.getElementById('cnt2'), lab=document.getElementById('lab2'), tx=document.getElementById('txt2');
  cnt.textContent='361'; lab.textContent='grid cells checked with one year of data';
  tx.textContent='The flood model draws rivers on a 5 km grid, so we do not know in advance which cell is our river.';
  function count(a,b,ms){ var t0=performance.now(); (function f(t){ var k=Math.min(1,(t-t0)/ms);
    cnt.textContent=Math.round(a+(b-a)*k); if(k<1) requestAnimationFrame(f); })(t0); }
  later(function(){ nodes.forEach(function(n){ if(n.c[2]==null){ n.r.style.opacity='.12'; }
      else n.r.setAttribute('fill',flowCol(n.c[2])); });
    count(361,234,700); lab.textContent='cells that carry any water';
    tx.textContent='Most cells are mountain slope or sea. Brighter means more water flows there.'; }, 1700);
  later(function(){ nodes.forEach(function(n){ if(n.c[2]!=null && !n.c[3]) n.r.style.opacity='.3'; });
    count(234,83,700); lab.textContent='cells downloaded in full, 1997–2026';
    tx.textContent='Only cells with real flow get the full 30-year history. This saves most of the cost.'; }, 3900);
  var big=P(D.probe.largest[0],D.probe.largest[1]), st=P(D.probe.station[0],D.probe.station[1]), ch=P(D.probe.chosen[0],D.probe.chosen[1]);
  later(function(){
    el('circle',{cx:big[0],cy:big[1],r:16,fill:'none',stroke:'#E8665C','stroke-width':2.5},s);
    txt(s,big[0]+22,big[1]-12,'largest: mixes two rivers',{fill:'#E8665C','font-size':13});
    el('circle',{cx:st[0],cy:st[1],r:6,fill:'#E8BE55'},s);
    txt(s,st[0]+12,st[1]+22,'station: dry cell',{fill:'#E8BE55','font-size':13});
    tx.textContent='Two easy rules fail. The biggest cell mixes the Huong and Bo rivers. The cell at the station has almost no flow.'; }, 6100);
  later(function(){ nodes.forEach(function(n){ var same=(Math.abs(n.c[0]-D.probe.chosen[0])<1e-6 && Math.abs(n.c[1]-D.probe.chosen[1])<1e-6);
      if(!same) n.r.style.opacity=Math.min(parseFloat(n.r.style.opacity||1),.18); });
    var ring=el('circle',{cx:ch[0],cy:ch[1],r:30,fill:'none',stroke:'#7FE9EF','stroke-width':3},s);
    if(!REDUCED){ el('animate',{attributeName:'r',values:'18;34;18',dur:'1.8s',repeatCount:'indefinite'},ring); }
    count(83,1,600); lab.textContent='cell chosen as the forecast target';
    tx.textContent='We chose the cell whose flow matches the size of the real basin.'; }, 8600);
}

/* ================= scene 3: files -> table ================= */
function scene3(){
  var s=document.getElementById('ch3'); clear(s);
  var kinds=D.files.kinds, per=8, cols=['#7FA7D9','#3E7E8A','#2FC2CC','#9CC3EE','#55707A'];
  var y=40, items=[];
  kinds.forEach(function(k,ki){
    txt(s,0,y+12,k.k+'  ·  '+k.n.toLocaleString('en')+' files',{fill:'#EAF4F5','font-size':15});
    var m=Math.max(1,Math.round(k.n/per));
    for(var i=0;i<m;i++){ var x=260+(i%40)*11, yy=y+Math.floor(i/40)*11;
      items.push({r:el('rect',{x:x,y:yy,width:8,height:8,rx:1,fill:cols[ki],
        style:'transition:transform 1.1s cubic-bezier(.6,.05,.3,1)'},s),x:x,y:yy}); }
    y+=Math.max(30,Math.ceil(m/40)*11+22);
  });
  txt(s,260,y+8,'each square ≈ '+per+' files',{'font-size':13});
  var TX=1080, TY=60, TW=300, TH=360;
  var tbl=el('g',{style:'opacity:.25;transition:opacity .8s'},s);
  el('rect',{x:TX,y:TY,width:TW,height:TH,fill:'#0C222B',stroke:'#2FC2CC','stroke-width':2},tbl);
  for(var r=1;r<9;r++) el('line',{x1:TX,y1:TY+r*TH/9,x2:TX+TW,y2:TY+r*TH/9,stroke:'#16313C'},tbl);
  for(var q=1;q<6;q++) el('line',{x1:TX+q*TW/6,y1:TY,x2:TX+q*TW/6,y2:TY+TH,stroke:'#16313C'},tbl);
  var big=txt(s,TX+TW/2,TY+TH+70,'',{fill:'#EAF4F5','font-size':40,'text-anchor':'middle','font-weight':600});
  var cap=txt(s,TX+TW/2,TY+TH+104,'days  ×  columns, one row per day',{'text-anchor':'middle','font-size':15});
  txt(s,TX+TW/2,TY-18,'daily_panel.parquet',{fill:'#2FC2CC','font-size':15,'text-anchor':'middle'});
  later(function(){ items.forEach(function(it,i){ var dx=TX+20+Math.random()*(TW-40)-it.x, dy=TY+20+Math.random()*(TH-40)-it.y;
      setTimeout(function(){ it.r.style.transform='translate('+dx+'px,'+dy+'px)'; }, REDUCED?0:i*5); });
    tbl.style.opacity='1'; }, 700);
  later(function(){ var t0=performance.now(), ms=900; (function f(t){ var k=Math.min(1,(t-t0)/ms);
    big.textContent=Math.round(D.files.rows*k).toLocaleString('en')+' × '+D.files.cols; if(k<1) requestAnimationFrame(f); })(t0); }, 2400);
  if(REDUCED) big.textContent=D.files.rows.toLocaleString('en')+' × '+D.files.cols;
}

/* ================= scene 4: out-of-sample forecast ================= */
function scene4(){
  var s=document.getElementById('ch4'); clear(s);
  var W=1440,H=520,pl=70,pr=190,pt=20,pb=50, n=D.fc.obs.length;
  var vmax=Math.max.apply(null,D.fc.obs.concat(D.fc.pred,[D.fc.thr[2]]))*1.1;
  function X(i){ return pl+(W-pl-pr)*i/(n-1); } function Y(v){ return pt+(H-pt-pb)*(1-v/vmax); }
  [0,1000,2000,3000].forEach(function(v){ if(v<vmax){ el('line',{x1:pl,y1:Y(v),x2:W-pr,y2:Y(v),stroke:'#16313C'},s);
    txt(s,pl-10,Y(v)+4,v.toLocaleString('en'),{'text-anchor':'end','font-size':12}); }});
  var cols=['#E8BE55','#E0833C','#E8665C'];
  D.fc.thr.forEach(function(v,i){ el('line',{x1:pl,y1:Y(v),x2:W-pr,y2:Y(v),stroke:cols[i],'stroke-dasharray':'5 4'},s);
    txt(s,W-pr+10,Y(v)+4,'risk level '+(i+1),{fill:'#EAF4F5','font-size':13}); });
  [0,Math.floor(n/3),Math.floor(2*n/3),n-1].forEach(function(i){ txt(s,X(i),H-pb+24,D.fc.dates[i],{'text-anchor':'middle','font-size':12}); });
  function path(a){ return a.map(function(v,i){return (i?'L':'M')+X(i).toFixed(1)+','+Y(v).toFixed(1);}).join(''); }
  var obs=el('path',{d:path(D.fc.obs),fill:'none',stroke:'#EAF4F5','stroke-width':2.5,opacity:.9},s);
  var pr_=el('path',{d:path(D.fc.pred),fill:'none',stroke:'#2FC2CC','stroke-width':3,'stroke-dasharray':'0'},s);
  var L=pr_.getTotalLength(), L2=obs.getTotalLength();
  [[obs,L2],[pr_,L]].forEach(function(o){ o[0].style.strokeDasharray=o[1]; o[0].style.strokeDashoffset=REDUCED?0:o[1];
    o[0].style.transition='stroke-dashoffset 3.2s ease-in-out'; });
  var lg=el('g',{},s);
  el('line',{x1:pl+8,y1:pt+8,x2:pl+40,y2:pt+8,stroke:'#EAF4F5','stroke-width':2.5},lg); txt(lg,pl+48,pt+12,'what happened',{fill:'#EAF4F5','font-size':14});
  el('line',{x1:pl+8,y1:pt+32,x2:pl+40,y2:pt+32,stroke:'#2FC2CC','stroke-width':3},lg); txt(lg,pl+48,pt+36,'forecast issued the day before',{fill:'#EAF4F5','font-size':14});
  later(function(){ obs.style.strokeDashoffset=0; }, 300);
  later(function(){ pr_.style.strokeDashoffset=0; }, 900);
  var im=D.fc.obs.indexOf(Math.max.apply(null,D.fc.obs));
  later(function(){ el('circle',{cx:X(im),cy:Y(D.fc.obs[im]),r:7,fill:'#EAF4F5',stroke:'#07141A','stroke-width':2},s);
    txt(s,X(im)+14,Y(D.fc.obs[im])-6,'peak '+D.fc.obs[im].toLocaleString('en')+' m³/s · '+D.fc.dates[im],{fill:'#EAF4F5','font-size':14});
    document.getElementById('txt4').innerHTML='Across the whole test period the one-day forecast scores <b>NSE '+D.fc.nse.toFixed(2)+
      '</b>, against <b>'+D.fc.nse_p.toFixed(2)+'</b> for simply repeating today&rsquo;s value. It still tends to <b>under-shoot the highest peaks</b>.'; }, 4300);
}

/* ---------- navigation ---------- */
var scenes=[scene0,scene1,scene2,scene3,scene4], cur=0;
var secs=document.querySelectorAll('.scene'), dots=document.getElementById('dots');
secs.forEach(function(_s,i){ var d=document.createElement('i'); dots.appendChild(d); });
function show(i){ stopAll(); cur=Math.max(0,Math.min(scenes.length-1,i));
  secs.forEach(function(s,k){ s.classList.toggle('on',k===cur); });
  dots.querySelectorAll('i').forEach(function(d,k){ d.classList.toggle('on',k===cur); });
  try{ history.replaceState(null,'','#s'+(cur+1)); }catch(e){}
  scenes[cur](); }
document.getElementById('next').onclick=function(){ show(cur+1); };
document.getElementById('prev').onclick=function(){ show(cur-1); };
document.getElementById('replay').onclick=function(){ show(cur); };
addEventListener('keydown',function(e){ if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){ e.preventDefault(); show(cur+1); }
  else if(e.key==='ArrowLeft'||e.key==='PageUp'){ show(cur-1); } else if(e.key==='r'){ show(cur); } });
var m=(location.hash||'').match(/^#s(\d)$/);
show(m?parseInt(m[1],10)-1:0);
})();
</script>
"""


def main() -> int:
    data = {"rain": rain_scene(), "probe": probe_scene(),
            "files": files_scene(), "fc": forecast_scene()}
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.replace("__DATA__", payload)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "flood_story.html").write_text(page, encoding="utf-8")
    local = ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
             "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
             "</head><body>\n" + page + "\n</body></html>\n")
    (OUTDIR / "flood_story_local.html").write_text(local, encoding="utf-8")
    print(f"→ reports/explainer/flood_story.html  ({len(page)//1024} KB)")
    print("→ reports/explainer/flood_story_local.html  (mở thẳng khi thuyết trình)")
    r = data["rain"]
    print(f"   mưa: {len(r['cells'])} ô × {len(r['days'])} ngày · cặp trễ {r['pairs']}")
    print(f"   dò: {sum(1 for c in data['probe']['cells'] if c[2])} ô có nước / "
          f"{len(data['probe']['cells'])} · tải đủ {sum(c[3] for c in data['probe']['cells'])}")
    print(f"   file: {data['files']['total']} → {data['files']['rows']} × {data['files']['cols']}")
    print(f"   dự báo: {len(data['fc']['obs'])} ngày · NSE h1 {data['fc']['nse']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
