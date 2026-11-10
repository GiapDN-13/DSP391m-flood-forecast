"""Chương II — Project Management Plan của tài liệu Capstone.

Nguồn: docs/PLAN.md, TEAM.md, TRACKING.md, RISKS.md, SPEC.md, GIT_WORKFLOW.md, lịch sử git và
GitHub (PR, issue, release, lượt chạy Actions) lấy ngày 10/11/2026. Số thập phân đăng ký vào sổ
bằng ``V.doc`` kèm lệnh đã dùng; số nguyên (đếm commit, PR, lượt chạy) ghi nguồn ở chú thích.
Chỉ viết điều repo chứng minh được: không khẳng định buổi họp hay biên bản không có trong repo.
"""

from __future__ import annotations

TABLES = ["comm", "wbs", "plan", "sprint", "risk", "qual", "change"]

ND = "&#8211;"
AR = '<font face="Symbol">&#8594;</font>'   # mũi tên: Times (WinAnsi) không có, font Symbol có


def chapter_content(para, blist, tbl, V) -> dict:
    V.doc("pm_ci_rate", "79.2", "gh run list -L 1000 (ci: 42/53 success, 10/11/2026)")
    V.doc("pm_daily_rate", "98.3", "gh run list -L 1000 (daily-forecast: 58/59 success, 10/11/2026)")

    intro = [
        para("<b>Working components:</b> open data " + AR + " daily panel and features " + AR + " "
             "baselines and LightGBM " + AR + " walk-forward evaluation " + AR + " daily job and "
             "dashboard " + AR + " reports. Each component has one owner, a definition of done in "
             "the specification (" + _tt("docs/SPEC.md") + ") and automated tests."),
        para("The team has three roles. The <b>Tech Lead</b> owns data engineering, modelling, "
             "infrastructure and integration and has the final technical say, with the reason "
             "written down. The <b>Data Analyst</b> owns exploratory analysis, features, "
             "baselines and the dashboard. <b>Research &amp; Documentation</b> owns the "
             "literature, legal sources, data dictionary, reports and slides. Because the oral "
             "exam is individual, every member must be able to explain every part of the "
             "project, which shaped the communication plan below."),
    ]

    comm = [
        para("Table " + _T("comm") + " lists the planned communication channels "
             "(" + _tt("docs/TEAM.md") + ", " + _tt("docs/TRACKING.md") + "). Two rules apply to "
             "everyone: a member stuck for more than 45 minutes raises it immediately, and "
             "messages are answered within 12 hours on working days."),
        tbl([["Channel / event", "Frequency", "Participants", "Purpose and output"],
             ["Main meeting", "Weekly, Wednesday, 30 min", "All members",
              "Status, blocked work, owners for next week, risk review"],
             ["Stand-up", "Weekly, Sunday, 15 min (chat allowed)", "All members",
              "Progress and blockers"],
             ["Knowledge hand-off", "Weekly, Saturday, 20 min", "Tech Lead to team",
              "Each member can explain each part; notes in " + _tt("docs/EXPLAINER.md")],
             ["Pair session", "Weekly, 30 min", "Tech Lead, Data Analyst",
              "Features, baselines, dashboard"],
             ["Supervisor review", "After each report", "Team, supervisor",
              "Questions and requests turned into tracked changes (Section 2.2.7)"],
             ["GitHub", "Continuous", "All members",
              "Pull requests, issues, CI results, releases, findings files"]],
            [1.3, 1.4, 1.1, 2.6], "comm", "Communication plan and protocols"),
    ]

    process = [
        para("The project used a time-boxed, iterative process of nine weeks with four graded "
             "report milestones (weights 10, 20, 40 and 10 %) and an oral exam (20 %). "
             "Internal deadlines were set two to three days before the real ones. The key "
             "elements were:"),
        *blist([
            "<b>Gates with a pre-agreed cut.</b> End of W1: GloFAS cell fixed and crawl "
            "running; end of W3: daily panel and risk thresholds (the critical-path point); end "
            "of W6: metrics for all horizons; end of W8: Report 3. Missing a gate triggers a "
            "cut that was decided in W1.",
            "<b>Pre-cut scope and a sacrifice order</b> (LSTM, then a secondary dashboard page, "
            "then scenario B, then series length, then grid size). Never sacrificed: the raw "
            "GloFAS baseline, a proper walk-forward, documented thresholds, rare-event metrics "
            "and SHAP.",
            "<b>Requirements with stable IDs</b> (functional requirements FR, non-functional "
            "NFR, acceptance criteria AC), MoSCoW priorities and a change log in "
            + _tt("docs/SPEC.md") + ".",
            "<b>Criteria before results.</b> Acceptance thresholds and the criteria of each "
            "experiment were written before it was run, and failed criteria are reported.",
            "<b>Trunk-based Git flow:</b> one long-lived " + _tt("main") + " branch, a branch "
            "and pull request per change, Conventional Commit messages, CI on every pull "
            "request and push.",
        ]),
    ]

    wbs = [
        para("The work breakdown follows the requirement groups of the specification "
             "(Table " + _T("wbs") + ")."),
        tbl([["WBS", "Work package", "Weeks", "Owner", "Main deliverables"],
             ["1", "Project management: plan, risks, tracking, Git workflow", "W1" + ND + "W9",
              "Tech Lead", "PLAN, TEAM, RISKS, TRACKING, GIT_WORKFLOW documents"],
             ["2", "Data acquisition: GloFAS, ERA5, forecasts, flood events, backups",
              "W1" + ND + "W3", "Tech Lead (events: Research)",
              "Raw Parquet, flood-event list, data release"],
             ["3", "Processing: time zone, hourly to daily, checks, daily panel",
              "W2" + ND + "W3", "Tech Lead, Data Analyst", "Daily panel, leakage tests"],
             ["4", "Risk levels: legal alert stages, thresholds, labels", "W1" + ND + "W3",
              "Research, Tech Lead", "Legal sources, risk-level table"],
             ["5", "Modelling: baselines, LightGBM, classifiers, calibration, LSTM",
              "W5" + ND + "W8", "Data Analyst, Tech Lead", "Models, result tables"],
             ["6", "Evaluation: walk-forward, rare-event and event scores, SHAP, ablation",
              "W6" + ND + "W7", "Data Analyst, Tech Lead", "Findings documents, figures"],
             ["7", "Product: daily job, dashboard, disclaimers", "W1, W7" + ND + "W8",
              "Data Analyst, Tech Lead", "GitHub Actions job, Streamlit app"],
             ["8", "Reports and defence", "W2, W4, W8, W9", "Research, Tech Lead",
              "Reports 1" + ND + "4, slides, script, question bank"],
             ["9", "Quality and operations: CI, tests, runbook", "Continuous", "Tech Lead",
              "CI workflow, test suite, RUNBOOK"]],
            [0.6, 2.4, 0.8, 1.2, 1.9], "wbs", "Work breakdown structure"),
    ]

    plan = [
        para("Table " + _T("plan") + " compares planned and actual dates of the main "
             "milestones, taken from commit, pull-request and release dates. Data and the first "
             "models arrived two to three weeks early, which created the slack that later "
             "absorbed the supervisor's requests for Spark and deep learning."),
        tbl([["Milestone", "Planned", "Actual", "Deviation"],
             ["GloFAS cell fixed, crawl running", "End of W1", "15/09", "Gate passed on day 1"],
             ["Off-machine data backup", "W3", "17/09 (release, restore verified)",
              "Two weeks early"],
             ["Daily panel (critical path)", "End of W3 (05/10)", "15/09, rebuilt 22/09",
              "About 18 days early"],
             ["Daily forecast job", "W8", "15/09", "Moved forward: live forecasts cannot be "
              "recovered later"],
             ["Risk thresholds from water levels", "W3", "21" + ND + "22/09",
              "Replaced by discharge percentiles (design change)"],
             ["Baselines, LightGBM, classifiers", "W5", "15" + ND + "22/09",
              "About three weeks early"],
             ["Walk-forward, Optuna, cost threshold", "W6", "20" + ND + "21/10", "On time"],
             ["SHAP", "W7", "21/10", "About one week early"],
             ["LSTM (optional)", "W8", "20/10", "Done although pre-cut"],
             ["Model freeze and release", "W8", "02/11 (release model-v1.0)", "On time"],
             ["Dashboard", "W7", "02/11, three tabs", "On time, one tab more"],
             ["Report 4 and final documents", "10/11", "02" + ND + "10/11", "On time"]],
            [2.2, 1.2, 1.7, 2.1], "plan", "Planned versus actual milestones"),
        para("<b>Lessons learned.</b>", "body0"),
        *blist([
            "A green job does not prove a correct product: the forecast of 20 September was "
            "lost while the job reported success. The job now checks its own output and fails "
            "on a missing day.",
            "Count what matters: an acceptance test that counted rows missed that GloFAS is "
            "empty before 1997; it now counts non-empty days.",
            "Test assumptions early: archived forecast rain turned out identical to reanalysis, "
            "and the water-level to discharge relation was too weak (R" + "&#178;" + " "
            + V("hq_r2") + ") to map the official stages; both changed the design within a "
            "week.",
            "Re-derive known constants: the catchment area quoted from the literature was the "
            "whole Huong system; the DEM-based value is about half of it.",
            "Fix documentation drift: the specification change log and the weekly plan were "
            "not updated after the replan of 2 October; changes were recorded in findings "
            "files and pull requests instead.",
        ]),
    ]

    sprint = [
        para("No issue tracker sprints were used after the first week; the unit of iteration "
             "is the plan week, closed by merged pull requests and releases (Table "
             + _T("sprint") + "). At the snapshot date (10/11/2026) the main branch has 138 "
             "commits: 80 by the team and 58 by the daily forecast job. There are 15 pull "
             "requests (9 merged, 2 folded into another, 4 open), 6 issues (all closed with a "
             "reason), 2 releases (a data snapshot and the frozen model) and 112 workflow runs. "
             "The first 24 commits went directly to " + _tt("main") + " before the pull-request "
             "flow started on 21 September; every later change came through a pull request."),
        tbl([["Week", "Merged pull requests / releases", "Main increments"],
             ["W1 (15" + ND + "21/09)", "#7, #8; data release",
              "Grid cell, crawl, ETL, panel, baselines, CI and daily job, Report 1, flood "
              "events, fix of the lost forecast"],
             ["W2 (22" + ND + "28/09)", "#11",
              "EDA, LightGBM beats persistence at three horizons, percentile risk levels, "
              "classifier, literature summaries"],
             ["W3 (29/09" + ND + "05/10)", "#12",
              "Scenario B ruled out, ablation, Report 2, replan, issues closed"],
             ["W4" + ND + "W5 (06" + ND + "19/10)", "#16 opened",
              "DuckDB and Polars data layer, extended data from 1997, reservoirs"],
             ["W6 (20" + ND + "26/10)", "#16, #17",
              "Hourly and satellite rain, Spark cluster, deep learning, catchment correction, "
              "SHAP, event scores, cost threshold"],
             ["W7 (27/10" + ND + "02/11)", "#18, #19, #20; model release",
              "Calibration, dashboard, live LightGBM job, Report 4 drafts, slides"],
             ["W8" + ND + "W9 (03" + ND + "10/11)", "#21 and this document",
              "MLlib on the full data, capstone document, first live level-1 alert"]],
            [1.1, 1.7, 3.6], "sprint", "Iterations: what each plan week delivered"),
    ]

    risk = [
        para("Risks are kept in " + _tt("docs/RISKS.md") + " with probability, impact (1"
             + ND + "5), an early signal, a response and an owner, and reviewed weekly. The "
             "register has 25 entries; Table " + _T("risk") + " shows those that occurred or "
             "shaped the design."),
        tbl([["ID", "Risk", "Response", "Outcome"],
             ["R1", "GloFAS cell does not match the river", "Scan of 121 cells",
              "Occurred on 15/09; cell (16.45, 107.50) chosen and re-confirmed"],
             ["R9", "Model cannot beat persistence", "Value expected at two to three days",
              "Beaten at all horizons; three-day target missed by a small margin"],
             ["R16", "GloFAS cannot separate Huong and Bo rivers", "Narrow to Kim Long",
              "Occurred; one station only"],
             ["R18", "GloFAS ignores reservoir operation", "State in limitations, test",
              "Confirmed; reservoir floor rule added"],
             ["R19", "Job green but product missing", "Check the product, not the status",
              "Occurred on 20/09; self-check added to the job"],
             ["R20", "GloFAS empty before 1997", "Count non-empty days", "Occurred; 16 places "
              "corrected, coverage test"],
             ["R23", "Water level not a function of discharge", "Three options analysed",
              "Confirmed; percentile risk levels"],
             ["R24", "Model underestimates flood peaks", "Report peak bias, test remedies",
              "Occurred; three remedies tested, none met the criteria"],
             ["R25", "ERA5 misses extreme rain", "State in limitations", "Not fixable with "
              "open data"],
             ["R5", "LSTM consumes time", "Cut from core scope", "Done later as comparison, "
              "no gain over LightGBM"]],
            [0.45, 2.0, 1.8, 2.4], "risk", "Main risks, responses and outcomes"),
    ]

    quality = [
        para("Quality is enforced by machines where possible:"),
        *blist([
            "<b>CI on every pull request and push:</b> pinned dependencies, ruff, the pytest "
            "suite, and guards against large files, committed data files and secrets.",
            "<b>Leakage and parity tests:</b> features may not use data published after the "
            "issue time; Spark results must equal the single-machine results; the daily panel "
            "built with DuckDB and Polars must equal the earlier pandas version.",
            "<b>Checked numbers in documents:</b> every report, including this one, is built "
            "from code, and every number is compared with its source file at build time.",
            "<b>Honest acceptance:</b> criteria AC-1 to AC-6 were fixed before results and are "
            "reported as met, missed or not evaluable (Table " + _T("ac") + ").",
        ]),
        tbl([["Measure", "Value (10/11/2026)"],
             ["Automated tests", "284 tests in 28 files, all passing"],
             ["Lint", "ruff clean on source, tests and scripts"],
             ["CI runs", f"53 runs, {V('pm_ci_rate')} % successful; 8 of the 11 failures in the "
              "first three days, before the pull-request flow"],
             ["Daily forecast job", f"59 runs, {V('pm_daily_rate')} % successful; 56 daily "
              "forecasts, one day lost (20/09) and documented"],
             ["Report numbers", "Built from code; a mismatch with the source stops the build"]],
            [1.6, 4.4], "qual", "Measured quality"),
        para("Code and documents were developed with the help of an AI coding assistant. "
             "Design decisions, acceptance criteria and the interpretation of results remain "
             "the team's; the tests, CI and the build-time number checks above are the "
             "controls that every change had to pass."),
    ]

    change = [
        para("Changes to the scope or design go through a pull request and are recorded with "
             "their reason: in the change log of the specification (versions 1.0" + ND + "1.6, "
             "15" + ND + "17/09), and afterwards in dated findings documents and pull-request "
             "descriptions. Cancelled requirements keep their ID and are struck through. "
             "Table " + _T("change") + " lists the main changes."),
        tbl([["Date", "Change", "Reason"],
             ["15/09", "Narrow to one station (Kim Long)", "GloFAS cannot resolve the Bo River"],
             ["15/09", "Tighten AC-1 per horizon", "Persistence already scored high one day "
              "ahead"],
             ["15/09", "Daily forecast job from W1 instead of W8", "Live forecasts cannot be "
              "recovered later"],
             ["21" + ND + "22/09", "Rain grid rebuilt to 64 uniform cells",
              "Uneven grid biased basin rainfall"],
             ["22/09", "Risk levels from discharge percentiles", "Water level not determined "
              "by discharge"],
             ["22/09", "Scenario B replaced by a noise test", "Archived forecasts equal "
              "reanalysis"],
             ["08/10", "Data layer moved to DuckDB and Polars", "Speed; identical results "
              "verified"],
             ["14/10", "Reservoir releases and data from 1997 added", "Supervisor question on "
              "reservoir operation"],
             ["20/10", "Hourly and satellite rain, Spark, deep learning added",
              "Supervisor request (October 2026)"],
             ["20/10", "Catchment area corrected", "Literature value covered the whole system"],
             ["02/11", "Model E frozen; peak remedies rejected", "Pre-set criteria not met"]],
            [0.8, 2.8, 2.6], "change", "Main changes to scope and design"),
    ]

    return {"intro": intro, "sections": [
        ("2.1", "Communication Plan", comm),
        ("2.2", "Project Management Approach", []),
        ("2.2.1", "Project Process", process),
        ("2.2.2", "Work Breakdown Structure (WBS)", wbs),
        ("2.2.3", "Plan vs. Actual Progress and Lessons Learned", plan),
        ("2.2.4", "Evidence of Iterations, Issues and Pull Requests", sprint),
        ("2.2.5", "Risk Management", risk),
        ("2.2.6", "Quality Management", quality),
        ("2.2.7", "Change Management Process", change),
    ]}


T: dict[str, str] = {}


def _T(key: str) -> str:
    return T[key]


def _tt(s: str) -> str:
    return f"<font face='Courier'>{s}</font>"
