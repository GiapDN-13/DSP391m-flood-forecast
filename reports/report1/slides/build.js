/**
 * Report 1 — Project Proposal slides (DSP391m, week 2 slot).
 * Build:  node build.js
 */
const pptxgen = require("pptxgenjs");

// ---- palette: deep river blue + Vietnamese flood-warning ochre ----
const C = {
  deep:   "06263A",   // darkest ground (title / closing)
  river:  "0B3C5D",   // dominant blue
  teal:   "1D7A8C",   // secondary
  ochre:  "D4761A",   // accent — flood alert signage
  light:  "F4F7F8",   // light ground
  paper:  "FFFFFF",
  muted:  "6E8A98",
  line:   "D6E0E4",
  ink:    "10222C",
};
const HEAD = "Cambria";
const BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.3 x 7.5 in
pres.author = "Nhom DSP391m";
pres.title = "Flood Risk Forecasting for the Huong River";

const W = 13.3, H = 7.5, M = 0.62;

/* ---------- helpers ---------- */
const title = (s, text, opt = {}) =>
  s.addText(text, {
    x: M, y: 0.46, w: W - 2 * M, h: 0.85, isTextBox: true,
    fontFace: HEAD, fontSize: 38, bold: true, color: C.river,
    align: "left", valign: "middle", margin: 0, ...opt,
  });

const kicker = (s, text, color = C.ochre) =>
  s.addText(text, {
    x: M, y: 0.16, w: W - 2 * M, h: 0.3, isTextBox: true,
    fontFace: BODY, fontSize: 11.5, bold: true, color,
    charSpacing: 2.2, margin: 0, valign: "middle",
  });

const foot = (s, n) =>
  s.addText(`DSP391m · Report 1 — Project Proposal   |   ${n}`, {
    x: M, y: H - 0.52, w: W - 2 * M, h: 0.3, isTextBox: true,
    fontFace: BODY, fontSize: 9.5, color: C.muted, margin: 0,
  });

/** stat badge: big number in a soft tinted block */
function stat(s, x, y, w, value, unit, label, tint = C.light, val = C.river) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 1.36, rectRadius: 0.07, fill: { color: tint },
    line: { color: C.line, width: 0.75 },
  });
  s.addText(
    [{ text: value, options: { fontSize: 31, bold: true, color: val } },
     { text: unit ? " " + unit : "", options: { fontSize: 13, color: C.muted } }],
    { x: x + 0.16, y: y + 0.14, w: w - 0.32, h: 0.6, isTextBox: true,
      fontFace: HEAD, margin: 0, valign: "middle" });
  s.addText(label, {
    x: x + 0.16, y: y + 0.74, w: w - 0.32, h: 0.5, isTextBox: true,
    fontFace: BODY, fontSize: 10.5, color: C.ink, margin: 0, valign: "top" });
}

/** numbered circle + heading + body, one row */
function row(s, x, y, w, num, head, body, circle = C.river) {
  s.addShape(pres.ShapeType.ellipse, {
    x, y: y + 0.03, w: 0.44, h: 0.44, fill: { color: circle },
  });
  s.addText(String(num), {
    x, y: y + 0.03, w: 0.44, h: 0.44, isTextBox: true, fontFace: HEAD,
    fontSize: 15, bold: true, color: C.paper, align: "center",
    valign: "middle", margin: 0 });
  s.addText(head, {
    x: x + 0.62, y, w: w - 0.62, h: 0.32, isTextBox: true, fontFace: BODY,
    fontSize: 15, bold: true, color: C.ink, margin: 0, valign: "middle" });
  s.addText(body, {
    x: x + 0.62, y: y + 0.33, w: w - 0.62, h: 0.62, isTextBox: true,
    fontFace: BODY, fontSize: 12.5, color: C.muted, margin: 0, valign: "top" });
}

/* =========================================================
   1 — Title
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.deep };

  s.addText("DSP391m  ·  REPORT 1  ·  PROJECT PROPOSAL", {
    x: M, y: 1.5, w: W - 2 * M, h: 0.34, isTextBox: true, fontFace: BODY,
    fontSize: 12.5, bold: true, color: C.ochre, charSpacing: 3, margin: 0 });

  // Tiêu đề chiếm hai dòng ở cỡ này — chừa đủ 1.7 in, đừng để tràn vào phụ đề
  s.addText([
    { text: "Forecasting Flood Risk", options: { breakLine: true } },
    { text: "1–3 Days Ahead", options: {} },
  ], {
    x: M, y: 1.92, w: 10.6, h: 1.7, isTextBox: true, fontFace: HEAD,
    fontSize: 44, bold: true, color: C.paper, lineSpacingMultiple: 1.0,
    margin: 0, valign: "top" });

  s.addText("Huong River, Hue — from open hydro-meteorological data", {
    x: M, y: 3.66, w: 10.6, h: 0.44, isTextBox: true, fontFace: HEAD,
    fontSize: 20, italic: true, color: "9FC4D2", margin: 0, valign: "middle" });

  s.addShape(pres.ShapeType.line, {
    x: M, y: 4.34, w: 3.2, h: 0, line: { color: C.teal, width: 2 } });

  s.addText(
    [{ text: "Team", options: { fontSize: 11, color: C.muted, breakLine: true } },
     { text: "Dang Nguyen Giap  ·  Hoang Anh Duc  ·  Le Thi Huyen",
       options: { fontSize: 14.5, color: C.paper } }],
    { x: M, y: 4.62, w: 6.4, h: 0.9, isTextBox: true, fontFace: BODY, margin: 0 });

  s.addText(
    [{ text: "Gauging station", options: { fontSize: 11, color: C.muted, breakLine: true } },
     { text: "Kim Long  ·  GloFAS cell 16.45 N, 107.50 E",
       options: { fontSize: 14.5, color: C.paper } }],
    { x: 7.3, y: 4.62, w: 5.4, h: 0.9, isTextBox: true, fontFace: BODY, margin: 0 });

  s.addText("Week 2 · 17 September 2026", {
    x: M, y: 6.5, w: 6, h: 0.3, isTextBox: true, fontFace: BODY,
    fontSize: 11, color: C.muted, margin: 0 });

  s.addNotes(
    "Good morning. Our project forecasts flood risk one to three days ahead for the Huong River in Hue, " +
    "using only open data. Central Vietnam is the most flood-affected region in the country, but local " +
    "gauging coverage is thin. We ask whether freely available global data can close part of that gap. " +
    "I will cover the subject and its big-data context, the problem and the analytics approach we chose, " +
    "and how we collect the data."
  );
}

/* =========================================================
   2 — Subject & context
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "SUBJECT & CONTEXT");
  title(s, "Why the Huong River basin");

  const bullets = [
    { text: "Central Vietnam is the country's most flood-affected region; Hue sits on a short, steep basin where floods rise within a day.", options: { bullet: true, breakLine: true } },
    { text: "Riverside communes suffer repeated damage, yet local gauging and commune-level warning remain sparse.", options: { bullet: true, breakLine: true } },
    { text: "Official alerts are issued as water-level stages BĐ I / II / III — the language local authorities already act on.", options: { bullet: true, breakLine: true } },
    { text: "Open global datasets now cover this basin at daily resolution, free and without an API key.", options: { bullet: true } },
  ];
  s.addText(bullets, {
    x: M, y: 1.6, w: 7.15, h: 2.6, isTextBox: true, fontFace: BODY,
    fontSize: 14.5, color: C.ink, paraSpaceAfter: 9, margin: 0, valign: "top" });

  s.addText("Research questions", {
    x: M, y: 4.35, w: 7.15, h: 0.32, isTextBox: true, fontFace: BODY,
    fontSize: 13, bold: true, color: C.teal, charSpacing: 1, margin: 0 });
  s.addText([
    { text: "Can river discharge be predicted 1, 2 and 3 days ahead from gridded rainfall and past discharge — and at what error?", options: { bullet: true, breakLine: true } },
    { text: "How well can a classifier flag days that exceed an official flood-alert stage?", options: { bullet: true, breakLine: true } },
    { text: "Which sub-basins carry the highest seasonal risk?", options: { bullet: true } },
  ], { x: M, y: 4.7, w: 7.15, h: 1.6, isTextBox: true, fontFace: BODY,
       fontSize: 13, color: C.ink, paraSpaceAfter: 7, margin: 0, valign: "top" });

  // right rail — alert stages, the subject's own instrument
  s.addShape(pres.ShapeType.roundRect, {
    x: 8.2, y: 1.6, w: 4.5, h: 4.7, rectRadius: 0.08,
    fill: { color: C.light }, line: { color: C.line, width: 0.75 } });
  s.addText("Official alert stages", {
    x: 8.46, y: 1.82, w: 4.0, h: 0.32, isTextBox: true, fontFace: BODY,
    fontSize: 12.5, bold: true, color: C.river, margin: 0 });
  s.addText("Kim Long station · water level above datum", {
    x: 8.46, y: 2.12, w: 4.0, h: 0.3, isTextBox: true, fontFace: BODY,
    fontSize: 10, color: C.muted, margin: 0 });

  const stages = [["BĐ I", "1.00 m", 0.30], ["BĐ II", "2.00 m", 0.57], ["BĐ III", "3.50 m", 1.0]];
  stages.forEach(([name, val, frac], i) => {
    const y = 2.62 + i * 0.72;
    s.addText(name, { x: 8.46, y, w: 0.85, h: 0.3, isTextBox: true,
      fontFace: HEAD, fontSize: 13, bold: true, color: C.ink, margin: 0 });
    s.addShape(pres.ShapeType.roundRect, { x: 9.34, y: y + 0.07, w: 2.1, h: 0.17,
      rectRadius: 0.04, fill: { color: "DCE7EA" }, line: { width: 0 } });
    s.addShape(pres.ShapeType.roundRect, { x: 9.34, y: y + 0.07, w: 2.1 * frac, h: 0.17,
      rectRadius: 0.04, fill: { color: i === 2 ? C.ochre : C.teal }, line: { width: 0 } });
    s.addText(val, { x: 11.5, y, w: 0.95, h: 0.3, isTextBox: true, fontFace: HEAD,
      fontSize: 12.5, color: C.river, align: "right", margin: 0 });
  });

  s.addText("Decision 05/2020/QD-TTg. Cross-checked against five bulletins of the Hue Hydro-Meteorological Station.", {
    x: 8.46, y: 5.0, w: 4.0, h: 1.1, isTextBox: true, fontFace: BODY,
    fontSize: 10.5, color: C.muted, margin: 0, valign: "top" });

  foot(s, "2");
  s.addNotes(
    "The Huong basin is about 2,830 square kilometres — small and steep, so floods rise and fall inside a " +
    "day or two. That short response time is exactly what makes a one-to-three-day forecast useful, and also " +
    "what makes it hard. On the right are the official alert stages at Kim Long: one, two and three and a half " +
    "metres. We anchor our target variable to these stages rather than inventing our own scale, because these " +
    "are the numbers local authorities already act on."
  );
}

/* =========================================================
   3 — Big data context
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "CONTEXT OF BIG DATA");
  title(s, "What makes this a data problem");

  s.addText("Volume alone does not define big data. This project meets four of the classic dimensions — each with a concrete figure from the data we have already collected.", {
    x: M, y: 1.52, w: 11.0, h: 0.5, isTextBox: true, fontFace: BODY,
    fontSize: 13.5, color: C.muted, margin: 0 });

  const dims = [
    ["Volume", "42 years of daily discharge and 11 years of hourly rainfall across 68 grid points — about 1,500 Parquet files.", C.river],
    ["Variety", "Simulated discharge, reanalysis rainfall, archived rainfall forecasts, river geometry, legal thresholds and news bulletins.", C.teal],
    ["Velocity", "Forecasts are re-issued every few hours; an automated job pulls a new 7-day forecast every morning.", C.river],
    ["Veracity", "Discharge is model output, not measurement. Reservoir releases are unmodelled. Both must be stated, not hidden.", C.ochre],
  ];
  dims.forEach(([h, b, col], i) => {
    const x = M + (i % 2) * 6.1, y = 2.25 + Math.floor(i / 2) * 1.62;
    s.addShape(pres.ShapeType.ellipse, { x, y: y + 0.04, w: 0.36, h: 0.36, fill: { color: col } });
    s.addText(h, { x: x + 0.52, y, w: 5.3, h: 0.34, isTextBox: true, fontFace: HEAD,
      fontSize: 17, bold: true, color: col, margin: 0, valign: "middle" });
    s.addText(b, { x: x + 0.52, y: y + 0.38, w: 5.3, h: 1.0, isTextBox: true,
      fontFace: BODY, fontSize: 12.5, color: C.ink, margin: 0, valign: "top" });
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 5.62, w: 11.0, h: 0.86, rectRadius: 0.07,
    fill: { color: C.light }, line: { color: C.line, width: 0.75 } });
  s.addText([
    { text: "Value.  ", options: { bold: true, color: C.river } },
    { text: "The output is not a number but a decision: which alert stage a commune should expect tomorrow, and how much confidence to place in it.", options: { color: C.ink } },
  ], { x: M + 0.24, y: 5.74, w: 10.5, h: 0.62, isTextBox: true, fontFace: BODY,
       fontSize: 13, margin: 0, valign: "middle" });

  foot(s, "3");
  s.addNotes(
    "We deliberately avoid claiming this is big data just because it is large. Volume is moderate — about fifteen " +
    "hundred files. What actually makes it a data-engineering problem is variety and veracity. Six different source " +
    "types have to be reconciled onto one daily timeline, and the discharge series is simulated rather than measured. " +
    "We treat that as a stated limitation, not a footnote."
  );
}

/* =========================================================
   4 — Problem statement
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "PROBLEM STATEMENT");
  title(s, "Two linked problems, one pipeline");

  row(s, M, 1.68, 11.0, 1, "Regression — how much water?",
      "Predict daily mean discharge in m³/s at horizons of 1, 2 and 3 days. Continuous target; evaluated with RMSE, MAE, NSE and KGE.", C.river);
  row(s, M, 3.0, 11.0, 2, "Classification — which alert stage?",
      "Predict whether each day exceeds BĐ I, II or III. Positive days are rare — roughly 1–3 % — so accuracy is banned; we use POD, FAR, CSI and PR-AUC.", C.teal);
  row(s, M, 4.32, 11.0, 3, "The bridge between them",
      "Official stages are water levels in metres; the data is discharge in m³/s. A calibration mapping from documented flood peaks converts one to the other.", C.ochre);

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 5.72, w: 11.0, h: 0.78, rectRadius: 0.07,
    fill: { color: "FDF1E3" }, line: { color: "F0D3AF", width: 0.75 } });
  s.addText([
    { text: "Constraint that shapes everything:  ", options: { bold: true, color: "8A4A0C" } },
    { text: "no measured water-level series is available to us, so the level-to-discharge mapping must be built indirectly from published flood peaks.", options: { color: C.ink } },
  ], { x: M + 0.24, y: 5.84, w: 10.5, h: 0.54, isTextBox: true, fontFace: BODY,
       fontSize: 12.5, margin: 0, valign: "middle" });

  foot(s, "4");
  s.addNotes(
    "There are two targets. The regression problem asks how much water; the classification problem asks which " +
    "alert stage. They are linked by a unit conversion that is not trivial: the legal thresholds are water levels " +
    "in metres, our data is discharge in cubic metres per second, and we could not obtain a measured rating curve. " +
    "So we build that mapping from documented flood peaks instead — and we name it a calibration mapping, not a " +
    "rating curve, because it absorbs model error as well as channel geometry."
  );
}

/* =========================================================
   5 — Analytics approach
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "ANALYTICS APPROACH");
  title(s, "Primarily predictive");

  const quads = [
    ["Descriptive", "What happened?", "Supporting. Seasonality, rainfall–discharge lag, historical flood events.", "SUPPORTING", C.teal],
    ["Diagnostic",  "Why did it happen?", "Partial. SHAP attributes each warning to rainfall, antecedent wetness or season.", "PARTIAL", C.teal],
    ["Predictive",  "What will happen?", "Core. Discharge and alert stage 1–3 days ahead. Both research questions live here.", "CORE", C.ochre],
    ["Prescriptive","What should we do?", "Out of scope. Evacuation decisions need authority and liability we do not have.", "OUT OF SCOPE", C.muted],
  ];
  quads.forEach(([name, q, body, tag, col], i) => {
    const x = M + (i % 2) * 5.72, y = 1.66 + Math.floor(i / 2) * 2.28;
    const isCore = tag === "CORE";
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w: 5.4, h: 2.06, rectRadius: 0.09,
      fill: { color: isCore ? "FDF1E3" : C.light },
      line: { color: isCore ? C.ochre : C.line, width: isCore ? 1.75 : 0.75 } });
    s.addText(tag, { x: x + 0.26, y: y + 0.2, w: 4.9, h: 0.26, isTextBox: true,
      fontFace: BODY, fontSize: 9.5, bold: true, color: col, charSpacing: 1.6, margin: 0 });
    s.addText(name, { x: x + 0.26, y: y + 0.48, w: 3.4, h: 0.42, isTextBox: true,
      fontFace: HEAD, fontSize: 21, bold: true, color: isCore ? "8A4A0C" : C.river, margin: 0 });
    s.addText(q, { x: x + 0.26, y: y + 0.92, w: 4.9, h: 0.28, isTextBox: true,
      fontFace: BODY, fontSize: 11.5, italic: true, color: C.muted, margin: 0 });
    s.addText(body, { x: x + 0.26, y: y + 1.24, w: 4.9, h: 0.68, isTextBox: true,
      fontFace: BODY, fontSize: 12, color: C.ink, margin: 0, valign: "top" });
  });

  s.addText("A global forecast system already publishes discharge for this cell. Our contribution is to correct it locally and translate it into Vietnam's own alert stages at sub-basin scale — not to replace it.", {
    x: M, y: 6.3, w: 11.1, h: 0.56, isTextBox: true, fontFace: BODY,
    fontSize: 12.5, italic: true, color: C.river, margin: 0, valign: "middle" });

  foot(s, "5");
  s.addNotes(
    "Of the four analytics types, our work is primarily predictive. Descriptive analysis supports it and diagnostic " +
    "comes through model explanation. We deliberately exclude prescriptive: recommending an evacuation is a decision " +
    "that needs legal authority we do not have, and claiming otherwise would be irresponsible for a student project. " +
    "The last line is important — a global system already forecasts this cell, so our contribution is local correction " +
    "and translation into Vietnamese alert stages, not replacement."
  );
}

/* =========================================================
   6 — Data requirements
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "DATA REQUIREMENTS");
  title(s, "Six inputs, one daily table");

  const rows = [
    ["Dataset", "Role in the model", "Span / resolution", "Status"],
    ["River discharge (GloFAS v4)", "Target variable and lag features", "1984–2026 · daily · ~5 km", "Collected"],
    ["Rainfall, temperature, wind (ERA5)", "Main predictors, aggregated by sub-basin", "2010–2026 · daily & hourly", "Collected"],
    ["Archived rainfall forecasts", "Operational scenario — what was knowable in advance", "2022–2026 · daily", "Collected"],
    ["River centre-lines (OpenStreetMap)", "Assign grid cells to the correct river", "Current snapshot", "Collected"],
    ["Legal alert thresholds", "Defines the classification target", "Decision 05/2020/QD-TTg", "Verified"],
    ["Documented flood peaks", "Calibrates water level to discharge", "≥ 15 events, 1999–2026", "In progress"],
  ];
  s.addTable(rows, {
    x: M, y: 1.66, w: 11.1, colW: [3.25, 3.5, 2.75, 1.6],
    border: { type: "solid", color: C.line, pt: 0.75 },
    fontFace: BODY, fontSize: 11.5, color: C.ink, valign: "middle",
    rowH: 0.52,
    fill: { color: C.paper },
  });

  s.addText([
    { text: "All sources are open and free. ", options: { bold: true, color: C.river } },
    { text: "Open-Meteo data is published under CC BY 4.0 and is cited accordingly; the total project cost is zero.", options: { color: C.ink } },
  ], { x: M, y: 5.65, w: 11.1, h: 0.4, isTextBox: true, fontFace: BODY,
       fontSize: 12.5, margin: 0 });

  s.addText("The last row is the critical path: without documented flood peaks the alert-stage target cannot be defined, so the classification problem cannot be evaluated.", {
    x: M, y: 6.1, w: 11.1, h: 0.56, isTextBox: true, fontFace: BODY,
    fontSize: 12, italic: true, color: "8A4A0C", margin: 0, valign: "top" });

  foot(s, "6");
  s.addNotes(
    "Six inputs feed one daily analysis table. Five of them are already on disk. The one still in progress is the " +
    "set of documented flood peaks, and it is the critical path: without it we cannot convert the legal water-level " +
    "thresholds into discharge, which means the classification target does not exist. That is a manual reading task " +
    "— bulletins and disaster reports — and it cannot be automated away."
  );
}

/* =========================================================
   7 — How we collect it
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "COLLECTION METHOD");
  title(s, "How the data is collected");

  // pipeline
  const steps = [
    ["Select", "Scan a 361-cell grid; pick the cell whose inferred catchment matches the real basin"],
    ["Crawl", "Independent tasks, one Parquet file each; retry, cache and checkpoint"],
    ["Clean", "Normalise to Vietnam time, aggregate hourly to daily, validate and fail loudly"],
    ["Assemble", "Average rainfall over three sub-basins, build lag features, prevent leakage"],
  ];
  steps.forEach(([h, b], i) => {
    const x = M + i * 2.83;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.66, w: 2.6, h: 1.92,
      rectRadius: 0.08, fill: { color: C.light }, line: { color: C.line, width: 0.75 } });
    s.addText(String(i + 1), { x: x + 0.22, y: 1.82, w: 0.5, h: 0.36, isTextBox: true,
      fontFace: HEAD, fontSize: 15, bold: true, color: C.ochre, margin: 0 });
    s.addText(h, { x: x + 0.22, y: 2.2, w: 2.2, h: 0.34, isTextBox: true,
      fontFace: HEAD, fontSize: 17, bold: true, color: C.river, margin: 0 });
    s.addText(b, { x: x + 0.22, y: 2.56, w: 2.2, h: 0.92, isTextBox: true,
      fontFace: BODY, fontSize: 10.5, color: C.ink, margin: 0, valign: "top" });
    if (i < 3) s.addText("→", { x: x + 2.6, y: 2.42, w: 0.23, h: 0.4, isTextBox: true,
      fontFace: BODY, fontSize: 17, color: C.muted, align: "center", margin: 0 });
  });

  s.addText("Design decisions that made it work", {
    x: M, y: 3.82, w: 11.1, h: 0.32, isTextBox: true, fontFace: BODY,
    fontSize: 13, bold: true, color: C.teal, charSpacing: 1, margin: 0 });
  s.addText([
    { text: "Every task writes its own file, so an interrupted run resumes for free and never re-requests what it already has.", options: { bullet: true, breakLine: true } },
    { text: "Request pacing adapts to the server: it widens on rate-limit responses and tightens again when the run is clean.", options: { bullet: true, breakLine: true } },
    { text: "A lock file prevents two crawlers running at once — our own duplicate processes, not the provider, caused every rate-limit error we saw.", options: { bullet: true, breakLine: true } },
    { text: "Manual collection is planned as manual: reading bulletins for flood peaks is scheduled work, not an afterthought.", options: { bullet: true } },
  ], { x: M, y: 4.18, w: 11.1, h: 2.0, isTextBox: true, fontFace: BODY,
       fontSize: 13, color: C.ink, paraSpaceAfter: 8, margin: 0, valign: "top" });

  foot(s, "7");
  s.addNotes(
    "Collection is a four-stage pipeline. The engineering detail worth a minute is the third bullet. We spent time " +
    "diagnosing rate-limit errors and blaming the data provider, when in fact our own shell had left three crawler " +
    "processes running in parallel, competing with each other. With a single process the entire collection finished " +
    "in about thirty-five minutes with no errors at all. The lesson we wrote into our documentation: when you see " +
    "rate limiting, count your own processes first."
  );
}

/* =========================================================
   8 — Feasibility evidence
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "FEASIBILITY — ALREADY DEMONSTRATED");
  title(s, "The proposal is not hypothetical");

  stat(s, M, 1.66, 2.55, "6,087", "× 71", "rows × columns in the assembled daily table");
  stat(s, M + 2.72, 1.66, 2.55, "2,929", "mm", "mean annual rainfall — matches Hue's climate");
  stat(s, M + 5.44, 1.66, 2.55, "0.790", "", "peak rainfall–discharge correlation, at 1-day lag", C.light, C.teal);
  stat(s, M + 8.16, 1.66, 2.55, "7", "%", "catchment area error for the selected grid cell", "FDF1E3", "8A4A0C");

  s.addChart(pres.ChartType.bar, [{
    name: "Correlation with discharge",
    labels: ["0 d", "1 d", "2 d", "3 d", "4 d", "5 d", "6 d", "7 d"],
    values: [0.641, 0.790, 0.608, 0.382, 0.284, 0.233, 0.184, 0.149],
  }], {
    x: M, y: 3.3, w: 6.3, h: 3.05,
    barDir: "col", chartColors: [C.teal],
    showTitle: true, title: "Rainfall leads discharge by one day",
    titleFontFace: HEAD, titleFontSize: 13, titleColor: C.river,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9,
    dataLabelColor: C.muted, dataLabelFormatCode: "0.00",
    showLegend: false,
    catAxisLabelColor: C.muted, catAxisLabelFontSize: 10,
    valAxisLabelColor: C.muted, valAxisLabelFontSize: 10,
    valAxisMaxVal: 1, valAxisMinVal: 0,
    valGridLine: { color: C.line, size: 0.75 },
    catGridLine: { style: "none" },
  });

  s.addText("What this establishes", {
    x: 7.28, y: 3.42, w: 5.4, h: 0.32, isTextBox: true, fontFace: BODY,
    fontSize: 13, bold: true, color: C.teal, charSpacing: 1, margin: 0 });
  s.addText([
    { text: "The data is obtainable, and the physical signal we intend to model is present and strong.", options: { bullet: true, breakLine: true } },
    { text: "Single-day rainfall outperforms 3-, 5- and 7-day accumulations — the basin responds fast, which supports a short forecast horizon.", options: { bullet: true, breakLine: true } },
    { text: "Baselines are already measured, so the model has a real bar to clear rather than an assumed one.", options: { bullet: true, breakLine: true } },
    { text: "A scheduled job has issued a fresh forecast every morning for three consecutive days.", options: { bullet: true } },
  ], { x: 7.28, y: 3.78, w: 5.4, h: 2.55, isTextBox: true, fontFace: BODY,
       fontSize: 12, color: C.ink, paraSpaceAfter: 7, margin: 0, valign: "top" });

  foot(s, "8");
  s.addNotes(
    "We want to show this proposal is not speculative. The data is collected, the table is assembled, and the signal " +
    "is there: rainfall leads discharge by exactly one day with a correlation of point seven nine. Notice that " +
    "single-day rainfall beats every multi-day accumulation — the basin responds fast, which is physically consistent " +
    "with its small steep geometry and supports our short forecast horizon. We have also measured our baselines, so " +
    "when we report model performance later there will be a real reference point."
  );
}

/* =========================================================
   9 — Deliverables & schedule
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "DELIVERABLES & SCHEDULE");
  title(s, "What we submit, and when");

  // deliverables
  const dels = [
    ["IEEE-format report", "PDF, two-column IEEE template. Introduction, problem statement, objectives, literature review, methodology, timeline and risks."],
    ["Oral presentation", "Delivered in English with this slide deck. Every team member must be able to explain the whole project, not only their own part."],
  ];
  dels.forEach(([h, b], i) => {
    const y = 1.66 + i * 1.34;
    s.addShape(pres.ShapeType.roundRect, { x: M, y, w: 6.35, h: 1.16,
      rectRadius: 0.08, fill: { color: C.light }, line: { color: C.line, width: 0.75 } });
    s.addText(h, { x: M + 0.24, y: y + 0.13, w: 5.9, h: 0.32, isTextBox: true,
      fontFace: HEAD, fontSize: 16, bold: true, color: C.river, margin: 0 });
    s.addText(b, { x: M + 0.24, y: y + 0.45, w: 5.9, h: 0.62, isTextBox: true,
      fontFace: BODY, fontSize: 11.5, color: C.ink, margin: 0, valign: "top" });
  });

  s.addText("Both deliverables are due in week 2. Report 1 carries 10 % of the course grade.", {
    x: M, y: 4.42, w: 6.35, h: 0.5, isTextBox: true, fontFace: BODY,
    fontSize: 12, italic: true, color: C.muted, margin: 0, valign: "top" });

  // milestones
  s.addText("Milestones across the nine-week term", {
    x: 7.4, y: 1.66, w: 5.3, h: 0.32, isTextBox: true, fontFace: BODY,
    fontSize: 13, bold: true, color: C.teal, charSpacing: 1, margin: 0 });

  const ms = [
    ["Report 1", "Proposal", "26 Sep", "10 %", true],
    ["Report 2", "Data & exploratory analysis", "09 Oct", "20 %", false],
    ["Report 3", "Modelling & evaluation", "02 Nov", "40 %", false],
    ["Report 4", "Final consolidated report", "10 Nov", "10 %", false],
    ["Viva", "Individually assessed", "13–16 Nov", "20 %", false],
  ];
  ms.forEach(([name, what, when, pct, now], i) => {
    const y = 2.1 + i * 0.85;
    s.addShape(pres.ShapeType.ellipse, { x: 7.4, y: y + 0.14, w: 0.2, h: 0.2,
      fill: { color: now ? C.ochre : C.line } });
    if (i < 4) s.addShape(pres.ShapeType.line, { x: 7.5, y: y + 0.34, w: 0, h: 0.51,
      line: { color: C.line, width: 1.25 } });
    s.addText(name, { x: 7.78, y, w: 1.6, h: 0.3, isTextBox: true, fontFace: HEAD,
      fontSize: 13.5, bold: true, color: now ? "8A4A0C" : C.river, margin: 0 });
    s.addText(what, { x: 7.78, y: y + 0.29, w: 3.3, h: 0.3, isTextBox: true,
      fontFace: BODY, fontSize: 11, color: C.muted, margin: 0 });
    s.addText(when, { x: 11.1, y, w: 1.0, h: 0.3, isTextBox: true, fontFace: BODY,
      fontSize: 11.5, bold: true, color: C.ink, align: "right", margin: 0 });
    s.addText(pct, { x: 11.1, y: y + 0.29, w: 1.0, h: 0.3, isTextBox: true,
      fontFace: BODY, fontSize: 10.5, color: C.muted, align: "right", margin: 0 });
  });

  foot(s, "9");
  s.addNotes(
    "Two deliverables for this slot: the IEEE-format report as a PDF, and this presentation in English. " +
    "On the right is the full nine-week schedule. Report 3 carries forty percent and the viva is assessed " +
    "individually, which is why our team agreed that every member has to be able to explain the whole project, " +
    "not just the part they built."
  );
}

/* =========================================================
   10 — Closing
   ========================================================= */
{
  const s = pres.addSlide();
  s.background = { color: C.deep };

  s.addText("IN ONE SENTENCE", {
    x: M, y: 1.3, w: 11.1, h: 0.32, isTextBox: true, fontFace: BODY,
    fontSize: 11.5, bold: true, color: C.ochre, charSpacing: 3, margin: 0 });

  s.addText("We correct and localise an open global flood forecast into Vietnam's own alert stages for the Huong River, one to three days ahead.", {
    x: M, y: 1.78, w: 11.1, h: 1.5, isTextBox: true, fontFace: HEAD,
    fontSize: 30, bold: true, color: C.paper, margin: 0, valign: "top" });

  s.addShape(pres.ShapeType.line, { x: M, y: 3.5, w: 3.2, h: 0,
    line: { color: C.teal, width: 2 } });

  s.addText("Next three steps", {
    x: M, y: 3.76, w: 5.6, h: 0.32, isTextBox: true, fontFace: BODY,
    fontSize: 12.5, bold: true, color: "9FC4D2", charSpacing: 1.4, margin: 0 });
  s.addText([
    { text: "Complete the flood-event record that unlocks the alert-stage target.", options: { bullet: true, breakLine: true } },
    { text: "Train the forecasting model and beat the measured baselines.", options: { bullet: true, breakLine: true } },
    { text: "Test whether reservoir operation explains the anomalies we found.", options: { bullet: true } },
  ], { x: M, y: 4.12, w: 5.6, h: 1.8, isTextBox: true, fontFace: BODY,
       fontSize: 13.5, color: C.paper, paraSpaceAfter: 8, margin: 0, valign: "top" });

  s.addShape(pres.ShapeType.roundRect, { x: 7.1, y: 3.7, w: 5.6, h: 2.25,
    rectRadius: 0.08, fill: { color: "0E3550" }, line: { color: "1C5375", width: 0.75 } });
  s.addText("Stated plainly in the report", {
    x: 7.36, y: 3.9, w: 5.1, h: 0.3, isTextBox: true, fontFace: BODY,
    fontSize: 11.5, bold: true, color: C.ochre, charSpacing: 1.2, margin: 0 });
  s.addText([
    { text: "Discharge data is simulated, not measured.", options: { bullet: true, breakLine: true } },
    { text: "The 5 km grid cannot resolve the neighbouring Bo River, so the study covers one station.", options: { bullet: true, breakLine: true } },
    { text: "This is academic work, not an official warning service.", options: { bullet: true } },
  ], { x: 7.36, y: 4.24, w: 5.1, h: 1.6, isTextBox: true, fontFace: BODY,
       fontSize: 11.5, color: "C9DCE4", paraSpaceAfter: 6, margin: 0, valign: "top" });

  s.addText("Thank you — questions welcome", {
    x: M, y: 6.45, w: 11.1, h: 0.4, isTextBox: true, fontFace: HEAD,
    fontSize: 15, italic: true, color: "9FC4D2", margin: 0 });

  s.addNotes(
    "To close: our contribution in one sentence is correction and localisation, not replacement. Three next steps, " +
    "and three limitations we state openly rather than let a reviewer find. The most important is the second one — " +
    "the five kilometre grid cannot separate the neighbouring Bo River, so we narrowed the study to one station " +
    "rather than pretend to cover two. Thank you; we are happy to take questions."
  );
}

pres.writeFile({ fileName: "DSP391m_Report1_Proposal.pptx" })
  .then(f => console.log("Wrote " + f));
