"""Đánh giá theo ĐỢT LŨ (FR-V5) — Report 3.

Chỉ số theo ngày (NSE, POD theo ngày) không trả lời câu người vận hành hỏi:
*đợt lũ này có được báo trước không, đỉnh dự báo lệch bao nhiêu, sớm hay muộn
mấy ngày?* Ở đây mỗi đợt lũ là MỘT sự kiện; mô hình chính LightGBM cấu hình E
(``ablation_ext.py``) được so với persistence (Q(t+h) = Q(t)).

Định nghĩa (đặt một lần ở đây; ``tests/test_event_eval.py`` khoá lại):

* **Đợt lũ**: ngày có lưu lượng GloFAS (cột ``discharge``) ≥ ngưỡng mức 1. Các
  ngày vượt ngưỡng gộp chung một đợt nếu giữa chúng có ≤ ``MAX_GAP`` = 2 ngày
  dưới ngưỡng. Đỉnh = ngày Q lớn nhất trong đợt.
* **Dự báo cho ngày v ở horizon h** = dự báo phát ngày t = v − h.
* **Bắt được** (``caught``): ít nhất một ngày v trong [bắt đầu, kết thúc] của
  đợt có dự báo ≥ ngưỡng. ``caught_win`` nới cửa sổ ±1 ngày (FR-V5), tham khảo.
* **Tỷ số đỉnh** (``peak_ratio``) = max dự báo / max thật, max dự báo tìm trong
  cửa sổ đỉnh [bắt đầu − 1, kết thúc + h] (cho phép muộn tới h ngày — cửa sổ ±1
  sẽ cắt cụt dự báo trễ 2–3 ngày như persistence ở h2–h3).
* **Lệch thời điểm đỉnh** (``timing_err``) = ngày đạt max dự báo (trong cửa sổ
  đỉnh) − ngày đỉnh thật; dương = muộn.
* **Thời gian báo trước** (``lead_onset``) = ngày bắt đầu đợt − ngày PHÁT của
  dự báo đầu tiên vượt ngưỡng trong cửa sổ ±1; ≤ 0 nghĩa là chỉ báo được khi lũ
  đã vượt ngưỡng. ``lead_peak`` tương tự nhưng tính tới ngày đỉnh.
* **Không lấn đợt kề**: với tỷ số đỉnh, thời điểm và báo trước chỉ xét dự báo
  PHÁT sau ngày kết thúc đợt trước và có ngày hiệu lực trước ngày bắt đầu đợt
  sau (nếu không, persistence sẽ "mượn" đỉnh của đợt trước).
* **Đợt báo nhầm**: cụm ngày dự báo ≥ ngưỡng (gộp cùng quy tắc) không chạm cửa
  sổ ±1 ngày của đợt thật nào.

Hai phạm vi:

(a) ``test_2022_07`` — split chính: E học trên ≤ 2022-06-30 (train + valid,
    đúng ``ablation_ext.py``), test ≥ 2022-07-01; ngưỡng 806 m³/s
    (``reports/risk_levels.csv`` — Q95 mùa lũ ≤ 2022-06-30, không rò rỉ).
(b) ``walk_forward`` — fold theo năm 2013–2025 của ``walk_forward_sat.py``
    (nhóm ``ext``, cấu hình E0 = E, cùng mặt nạ hàng, chỉ import). Ngưỡng mỗi
    fold = ``fold_threshold`` (Q95 mùa lũ trong cửa sổ train của fold) — chế độ
    ``fold_q95`` (chính); chế độ ``fixed_806`` chấm lại CÙNG dự báo để đối chiếu.

LightGBM: tham số mô hình chính ``lgbm.params_for(h)`` (L1 ở h=1, L2 ở h=2–3,
từ 21/10/2026; bản L1 cũ ở ``reports/l1_ref/``), dự báo = trung bình 3 seed (42, 7, 2026),
``n_jobs`` = 4. Đối chiếu ``data/external/flood_events.csv``: mỗi đợt GloFAS ghi
các trận lũ báo chí có đỉnh trong [bắt đầu − 2, kết thúc + 2] ngày.

Phần 2 (``glofas_raw_check``): ``reports/forecast_log/`` có đủ để so GloFAS thô
với LightGBM chưa — chỉ đọc file, không gọi mạng.

    python -m src.eval.event_eval                  # ~6–10 phút, 126 lần fit
    python -m src.eval.event_eval --from-cache     # chấm lại từ dự báo đã lưu
    python -m src.eval.event_eval --plot-only      # vẽ lại từ CSV
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from src import config as cfg
from src.eval import metrics

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_EVENTS = cfg.ROOT / "reports" / "event_eval_events.csv"
OUT_SUMMARY = cfg.ROOT / "reports" / "event_eval_summary.csv"
OUT_NEWS = cfg.ROOT / "reports" / "event_eval_news.csv"
OUT_GLOFAS = cfg.ROOT / "reports" / "event_eval_glofas_raw.csv"
OUT_FIG = cfg.FIGURES / "report" / "event_eval_en.png"
PREDS = cfg.CACHE / "event_eval_preds.parquet"
RISK = cfg.ROOT / "reports" / "risk_levels.csv"
NEWS = cfg.DATA_EXTERNAL / "flood_events.csv"
LOG_DIR = cfg.ROOT / "reports" / "forecast_log"
WF_FOLDS_CSV = cfg.ROOT / "reports" / "wf_sat_folds.csv"
ABL_CSV = cfg.ROOT / "reports" / "ablation_ext.csv"

SEEDS = (42, 7, 2026)
N_JOBS = 4
MAX_GAP = 2            # số ngày dưới ngưỡng tối đa giữa hai ngày vượt ngưỡng cùng đợt
WINDOW = 1             # cửa sổ ±1 ngày (FR-V5): caught_win, gắn cảnh báo với đợt
NEWS_PAD = 2           # đối chiếu tin báo: đỉnh trong [bắt đầu − 2, kết thúc + 2]
MODELS = ("lgbm_E", "persistence")
TEST_START = date.fromisoformat(cfg.GLOFAS_REGIME_BREAK)
TRAIN_END = date.fromisoformat(cfg.VALID_END)
WF_YEARS = tuple(range(2013, 2026))
WF_PERIODS = {"wf_2013_2025": (2013, 2025), "wf_2013_2021": (2013, 2021),
              "wf_2022": (2022, 2022), "wf_2023_2025": (2023, 2025)}
E0 = "E0 (=E ablation_ext)"
LOG_POINT = ("huong_kim_long", 16.45, 107.5)   # ô đã chốt (A3); 15/09 còn dùng ô cũ


def thr_fixed() -> float:
    r = pl.read_csv(RISK)
    return float(r.filter(pl.col("muc") == "nguy_co_1")["nguong_m3s"][0])


# ================================================================ định nghĩa đợt (thuần)

def _days(a: date, b: date) -> list[date]:
    return [a + timedelta(days=i) for i in range((b - a).days + 1)]


def clusters(days, max_gap: int = MAX_GAP) -> list[tuple[date, date]]:
    """Gộp các ngày thành cụm [đầu, cuối]: hai ngày liên tiếp (đã sắp) cùng cụm
    nếu giữa chúng có ≤ ``max_gap`` ngày không thuộc tập."""
    out: list[tuple[date, date]] = []
    for d in sorted(set(days)):
        if out and (d - out[-1][1]).days - 1 <= max_gap:
            out[-1] = (out[-1][0], d)
        else:
            out.append((d, d))
    return out


def find_events(dates, q, thr: float, max_gap: int = MAX_GAP) -> list[dict]:
    """Đợt lũ trên chuỗi quan trắc: cụm ngày ``q ≥ thr`` (bỏ NaN)."""
    q = np.asarray(q, dtype=float)
    obs = {d: v for d, v in zip(dates, q) if np.isfinite(v)}
    exc = [d for d, v in obs.items() if v >= thr]
    evs = []
    for s, e in clusters(exc, max_gap):
        span = [(d, obs[d]) for d in _days(s, e) if d in obs]
        pk_d, pk_q = max(span, key=lambda x: x[1])
        evs.append({"start": s, "end": e, "peak_date": pk_d, "peak_q": float(pk_q),
                    "n_days": (e - s).days + 1, "n_above": sum(s <= d <= e for d in exc)})
    return evs


def _vals(fc: dict, days: list[date]) -> np.ndarray:
    v = np.array([fc.get(d, np.nan) for d in days], dtype=float)
    return np.where(np.isfinite(v), v, np.nan)


def _ge(v: np.ndarray, thr: float) -> np.ndarray:
    return np.where(np.isfinite(v), v, -np.inf) >= thr


def score_event(ev: dict, fc: dict, thr: float, h: int, window: int = WINDOW,
                prev_end: date | None = None, next_start: date | None = None) -> dict:
    """Chấm một đợt cho một chuỗi dự báo ``fc`` = {ngày hiệu lực v: Q̂(v)} ở horizon h.

    ``prev_end``/``next_start``: ngày kết thúc đợt trước / bắt đầu đợt sau — dự báo
    phát trong đợt trước hoặc hiệu lực trong đợt sau không được tính cho đợt này.
    """
    def own(days: list[date]) -> list[date]:
        return [d for d in days if (prev_end is None or d - timedelta(days=h) > prev_end)
                and (next_start is None or d < next_start)]

    span = _days(ev["start"], ev["end"])
    win = own(_days(ev["start"] - timedelta(days=window), ev["end"] + timedelta(days=window)))
    pkw = own(_days(ev["start"] - timedelta(days=window), ev["end"] + timedelta(days=h)))
    v_span, v_win, v_pk = _vals(fc, span), _vals(fc, win), _vals(fc, pkw)
    out = {"caught": bool(_ge(v_span, thr).any()), "caught_win": bool(_ge(v_win, thr).any()),
           "n_fc_days": int(np.isfinite(v_pk).sum()), "fc_peak": np.nan, "fc_peak_date": None,
           "peak_ratio": np.nan, "timing_err": np.nan, "warn_issue_date": None,
           "lead_onset": np.nan, "lead_peak": np.nan}
    if out["n_fc_days"]:
        i = int(np.nanargmax(v_pk))
        out.update(fc_peak=float(v_pk[i]), fc_peak_date=pkw[i],
                   peak_ratio=float(v_pk[i]) / ev["peak_q"],
                   timing_err=float((pkw[i] - ev["peak_date"]).days))
    warn = [d for d, ok in zip(win, _ge(v_win, thr)) if ok]
    if warn:
        issue = warn[0] - timedelta(days=h)
        out.update(warn_issue_date=issue, lead_onset=float((ev["start"] - issue).days),
                   lead_peak=float((ev["peak_date"] - issue).days))
    return out


def false_alarm_events(fc: dict, thr: float, events: list[dict], lo: date, hi: date,
                       max_gap: int = MAX_GAP, window: int = WINDOW) -> int:
    """Số cụm ngày dự báo ≥ ngưỡng trong [lo, hi] không chạm cửa sổ ±window của đợt nào."""
    exc = [d for d, v in fc.items() if lo <= d <= hi and np.isfinite(v) and v >= thr]
    wins = [(e["start"] - timedelta(days=window), e["end"] + timedelta(days=window)) for e in events]
    return sum(not any(s <= b and a <= e for a, b in wins) for s, e in clusters(exc, max_gap))


def news_match(ev: dict, news: pl.DataFrame, pad: int = NEWS_PAD) -> str:
    a, b = ev["start"] - timedelta(days=pad), ev["end"] + timedelta(days=pad)
    ids = news.filter(pl.col("peak_date").is_between(a, b))["event_id"].to_list()
    return ";".join(ids)


# ================================================================ dự báo

def _fit_block(panel: pl.DataFrame, feats: list[str], mask_feats: list[str],
               split: dict[str, tuple[date, date]], tag: dict) -> pl.DataFrame:
    """Fit E (3 seed) + persistence cho h = 1..3 trên ``split``; trả dạng dài."""
    from src.models import ablation_hourly as ab
    from src.models import lgbm

    lgbm.PARAMS["n_jobs"] = N_JOBS
    d = panel["date"].cast(pl.Date)
    X = panel.select(feats).to_numpy().astype(float)
    q0 = panel["discharge"].to_numpy().astype(float)
    out = []
    for h in cfg.HORIZONS:
        m = ab.masks(panel, mask_feats, h, split)
        tr, te = m["train"], m["test"]
        y = panel[f"target_h{h}"].to_numpy().astype(float)
        ps = [ab.fit_predict(X, feats, y, tr, te, s, lgbm.params_for(h))[0] for s in SEEDS]
        issue = d.filter(pl.Series(te))
        p = np.mean(ps, axis=0)
        print(f"    h{h}: train {int(tr.sum())} · test {int(te.sum())} · NSE seed "
              + " ".join(f"{metrics.nse(y[te], x):.4f}" for x in ps)
              + f" · NSE TB-3-seed {metrics.nse(y[te], p):.4f} · persistence "
              f"{metrics.nse(y[te], q0[te]):.4f}", flush=True)
        out.append(pl.DataFrame({"issue_date": issue, "y": y[te], "lgbm_E": p,
                                 "persistence": q0[te]})
                   .with_columns(horizon=pl.lit(h), n_train=pl.lit(int(tr.sum())), **{
                       k: pl.lit(v) for k, v in tag.items()},
                       **{f"nse_seed{s}": pl.lit(metrics.nse(y[te], x)) for s, x in zip(SEEDS, ps)}))
    return pl.concat(out)


def predict_main() -> pl.DataFrame:
    """(a) Split chính — giống hệt cấu hình E của ``ablation_ext.py``."""
    from src.models import ablation_ext as ax
    from src.models import ablation_hourly as ab

    feats = (ab.base_cols(pl.read_parquet(ax.PANEL))
             + ax.SOIL + ax.RESERVOIR_PROXY + ax.CONTEXT)
    panel = pl.read_parquet(ax.PANEL_EXT).sort("date")
    split = {"train": (date(1900, 1, 1), TRAIN_END), "test": (TEST_START, date(2100, 1, 1))}
    print(f"\n=== (a) split chính: E {len(feats)} feature, train ≤ {TRAIN_END}, test ≥ {TEST_START}")
    return _fit_block(panel, feats, feats, split,
                      {"scope": "test_2022_07", "fold": 0, "thr_fold": thr_fixed()})


def predict_wf(years) -> pl.DataFrame:
    """(b) Walk-forward theo năm — fold và ngưỡng của ``walk_forward_sat.py``."""
    from src.eval import walk_forward_sat as wfs
    from src.models import ablation_sat as sa

    panel, cfgs, split = sa.load_group("ext")
    feats = cfgs[E0]
    union = sorted({c for f in cfgs.values() for c in f})
    start = split["train"][0]
    print(f"\n=== (b) walk-forward {years[0]}–{years[-1]}: {E0}, {len(feats)} feature, "
          f"mặt nạ hàng theo {len(union)} cột (như walk_forward_sat)")
    out = []
    for y in years:
        t0 = time.time()
        fold = wfs.year_fold(y, start)
        thr = wfs.fold_threshold(panel, *fold["train"])
        print(f"  fold {y}: train {fold['train'][0]}..{fold['train'][1]} · ngưỡng {thr:.1f}", flush=True)
        out.append(_fit_block(panel, feats, union, fold,
                              {"scope": "walk_forward", "fold": y, "thr_fold": thr}))
        print(f"    ({time.time() - t0:.1f}s)", flush=True)
    return pl.concat(out)


def observed() -> pl.DataFrame:
    """Chuỗi GloFAS quan trắc theo ngày (panel ext)."""
    return (pl.read_parquet(cfg.DATA_PROCESSED / "daily_panel_ext.parquet", columns=["date", "discharge"])
              .with_columns(pl.col("date").cast(pl.Date)).sort("date"))


def check_reproduction(preds: pl.DataFrame) -> None:
    """In chênh NSE so với kết quả đã công bố (ablation_ext.csv, wf_sat_folds.csv)."""
    a = preds.filter(pl.col("scope") == "test_2022_07")
    if ABL_CSV.exists() and a.height:
        ref = pl.read_csv(ABL_CSV).filter(pl.col("config").str.starts_with("E "))
        for h in cfg.HORIZONS:
            r = a.filter(pl.col("horizon") == h).row(0, named=True)
            for s in SEEDS:
                v = ref.filter((pl.col("horizon") == h) & (pl.col("seed") == s))["NSE"]
                if v.len():
                    print(f"  kiểm (a) h{h} seed {s}: NSE {r[f'nse_seed{s}']:.5f} vs ablation_ext "
                          f"{v[0]:.5f} (Δ {r[f'nse_seed{s}'] - v[0]:+.1e})")
    w = preds.filter(pl.col("scope") == "walk_forward")
    if WF_FOLDS_CSV.exists() and w.height:
        ref = pl.read_csv(WF_FOLDS_CSV).filter((pl.col("group") == "ext") & (pl.col("config") == E0))
        diffs, n_ok, n_all = [], 0, 0
        for (y, h), g in w.group_by("fold", "horizon"):
            r = ref.filter((pl.col("fold") == y) & (pl.col("horizon") == h))
            if r.height:
                diffs.append(abs(metrics.nse(g["y"].to_numpy(), g["lgbm_E"].to_numpy()) - r["NSE"][0]))
                n_ok += int(g.height == r["n_test"][0])
                n_all += 1
        if n_all:
            print(f"  kiểm (b): {n_all} cặp fold×h, |ΔNSE| tối đa so với wf_sat_folds = "
                  f"{max(diffs):.1e}; n_test khớp {n_ok}/{n_all}")


# ================================================================ chấm theo đợt

def _fc_dict(p: pl.DataFrame, model: str) -> dict:
    v = p.with_columns(valid=pl.col("issue_date") + pl.duration(days=pl.col("horizon")))
    return dict(zip(v["valid"].to_list(), v[model].to_numpy().astype(float)))


def score_block(p: pl.DataFrame, obs: pl.DataFrame, lo: date, hi: date, thr: float,
                tag: dict, news: pl.DataFrame, max_gap: int = MAX_GAP) -> tuple[list[dict], list[dict]]:
    o = obs.filter(pl.col("date").is_between(lo, hi))
    evs = find_events(o["date"].to_list(), o["discharge"].to_numpy(), thr, max_gap)
    rows, fa = [], []
    for h in cfg.HORIZONS:
        ph = p.filter(pl.col("horizon") == h)
        for model in MODELS:
            fc = _fc_dict(ph, model)
            fa.append({**tag, "model": model, "horizon": h,
                       "n_fa_events": false_alarm_events(fc, thr, evs, lo, hi, max_gap)})
            for i, ev in enumerate(evs):
                nb = {"prev_end": evs[i - 1]["end"] if i else None,
                      "next_start": evs[i + 1]["start"] if i + 1 < len(evs) else None}
                rows.append({**tag, "event_id": ev["start"].strftime("%Y-%m-%d"),
                             **{k: ev[k] for k in ("start", "end", "n_days", "n_above",
                                                    "peak_date", "peak_q")},
                             "news_events": news_match(ev, news), "model": model, "horizon": h,
                             **score_event(ev, fc, thr, h, **nb)})
    return rows, fa


def score_all(preds: pl.DataFrame, obs: pl.DataFrame, max_gap: int = MAX_GAP):
    news = (pl.read_csv(NEWS).filter(pl.col("station") == "kim_long")
              .with_columns(pl.col("peak_date").str.to_date()))
    t806 = thr_fixed()
    rows, fa = [], []
    a = preds.filter(pl.col("scope") == "test_2022_07")
    if a.height:
        r, f = score_block(a, obs, TEST_START, obs["date"].max(), t806,
                           {"scope": "test_2022_07", "fold": 0, "thr_mode": "fixed_806", "thr": t806},
                           news, max_gap)
        rows += r
        fa += f
    w = preds.filter(pl.col("scope") == "walk_forward")
    for y in sorted(w["fold"].unique().to_list()):
        p = w.filter(pl.col("fold") == y)
        for mode, thr in (("fold_q95", float(p["thr_fold"][0])), ("fixed_806", t806)):
            r, f = score_block(p, obs, date(y, 1, 1), date(y, 12, 31), thr,
                               {"scope": "walk_forward", "fold": y, "thr_mode": mode, "thr": thr},
                               news, max_gap)
            rows += r
            fa += f
    return pl.DataFrame(rows, infer_schema_length=None), pl.DataFrame(fa)


def _med(s: pl.Series) -> float:
    s = s.drop_nulls().drop_nans()
    return float(s.median()) if s.len() else float("nan")


def summarize(ev: pl.DataFrame, fa: pl.DataFrame) -> pl.DataFrame:
    def periods():
        yield "test_2022_07", "fixed_806", pl.col("scope") == "test_2022_07"
        for name, (a, b) in WF_PERIODS.items():
            for mode in ("fold_q95", "fixed_806"):
                yield name, mode, ((pl.col("scope") == "walk_forward")
                                   & pl.col("fold").is_between(a, b))

    rows = []
    for name, mode, cond in periods():
        e = ev.filter(cond & (pl.col("thr_mode") == mode))
        f = fa.filter(cond & (pl.col("thr_mode") == mode))
        for model in MODELS:
            for h in cfg.HORIZONS:
                x = e.filter((pl.col("model") == model) & (pl.col("horizon") == h))
                c = x.filter(pl.col("caught"))
                n = x.height
                rows.append({
                    "scope": name, "thr_mode": mode, "model": model, "horizon": h,
                    "n_events": n, "n_caught": c.height,
                    "catch_rate": c.height / n if n else float("nan"),
                    "catch_rate_win": x["caught_win"].sum() / n if n else float("nan"),
                    "peak_ratio_median": _med(x["peak_ratio"]),
                    "peak_ratio_q25": float(x["peak_ratio"].drop_nans().quantile(0.25)) if n else float("nan"),
                    "peak_ratio_q75": float(x["peak_ratio"].drop_nans().quantile(0.75)) if n else float("nan"),
                    "timing_err_median": _med(x["timing_err"].cast(pl.Float64)),
                    "abs_timing_err_median": _med(x["timing_err"].cast(pl.Float64).abs()),
                    "lead_onset_median_caught": _med(c["lead_onset"].cast(pl.Float64)),
                    "n_lead_onset_pos": int((c["lead_onset"].cast(pl.Float64) > 0).sum()),
                    "lead_peak_median_caught": _med(c["lead_peak"].cast(pl.Float64)),
                    "n_fa_events": int(f.filter((pl.col("model") == model)
                                                & (pl.col("horizon") == h))["n_fa_events"].sum()),
                    "thr_min": float(e["thr"].min()) if e.height else float("nan"),
                    "thr_max": float(e["thr"].max()) if e.height else float("nan"),
                })
    return pl.DataFrame(rows)


def news_table(obs: pl.DataFrame, ev: pl.DataFrame) -> pl.DataFrame:
    """Trận lũ báo chí 2013–2026: GloFAS max quanh ngày đỉnh và có thành đợt (806) không."""
    news = (pl.read_csv(NEWS).filter(pl.col("station") == "kim_long")
              .with_columns(pl.col("peak_date").str.to_date())
              .filter(pl.col("peak_date") >= date(2013, 1, 1)))
    evs = (ev.filter((pl.col("thr_mode") == "fixed_806") & (pl.col("model") == "lgbm_E")
                     & (pl.col("horizon") == 1))
             .unique(["event_id"]).select("event_id", "start", "end", "peak_q"))
    out = []
    for r in news.iter_rows(named=True):
        w = int(r["window_days"])
        a, b = r["peak_date"] - timedelta(days=w), r["peak_date"] + timedelta(days=w)
        o = obs.filter(pl.col("date").is_between(a, b))
        m = evs.filter((pl.col("start") - pl.duration(days=NEWS_PAD) <= r["peak_date"])
                       & (pl.col("end") + pl.duration(days=NEWS_PAD) >= r["peak_date"]))
        out.append({"news_event": r["event_id"], "peak_date": r["peak_date"], "peak_H_m": r["peak_H_m"],
                    "alert_level": r["alert_level"], "confidence": r["confidence"],
                    "glofas_max_window": float(o["discharge"].max()) if o.height else float("nan"),
                    "glofas_event_806": ";".join(m["event_id"].to_list())})
    return pl.DataFrame(out)


# ================================================================ phần 2: GloFAS thô

def glofas_raw_check() -> pl.DataFrame:
    """Dự báo GloFAS thô trong ``forecast_log`` so với 'thực' — có cặp nào dùng được?

    Thực dạng 1: ``discharge`` của panel (GloFAS archive Open-Meteo) — panel dừng
    ở ngày cuối đã tải. Thực dạng 2 (thay thế, KHÔNG độc lập): giá trị horizon 0
    của bản phát vào chính ngày đó (GloFAS ước lượng ngày hiện tại).
    """
    files = sorted(f for f in LOG_DIR.glob("????-??-??.csv"))
    log = pl.concat([pl.read_csv(f, columns=["run_date", "point", "lat", "lon", "target_date",
                                             "glofas_discharge", "horizon_days"],
                                 schema_overrides={"glofas_discharge": pl.Float64})
                     for f in files], how="vertical_relaxed")
    log = log.with_columns(pl.col("run_date").str.to_date(), pl.col("target_date").str.to_date())
    name, lat, lon = LOG_POINT
    pt = log.filter((pl.col("point") == name) & ((pl.col("lat") - lat).abs() < 1e-6)
                    & ((pl.col("lon") - lon).abs() < 1e-6))
    obs = observed()
    h0 = (pt.filter(pl.col("horizon_days") == 0)
            .select(pl.col("target_date"), pl.col("glofas_discharge").alias("q_h0")))
    runs = pt["run_date"].unique().sort()
    print(f"\n=== Phần 2: forecast_log — {len(files)} bản phát chính thức, {runs.len()} bản ở ô "
          f"({lat}, {lon}) từ {runs.min()} tới {runs.max()}; panel quan trắc tới {obs['date'].max()}")
    rows = []
    for h in cfg.HORIZONS:
        f = (pt.filter(pl.col("horizon_days") == h)
               .select("run_date", "target_date", pl.col("glofas_discharge").alias("fc"))
               .join(h0.rename({"target_date": "run_date", "q_h0": "q_issue"}), on="run_date", how="left")
               .join(h0, on="target_date", how="left")
               .join(obs.rename({"date": "target_date", "discharge": "q_panel"}), on="target_date",
                     how="left"))
        n_panel = int(f["q_panel"].is_not_null().sum())
        g = f.drop_nulls(["fc", "q_h0"])
        p = g.drop_nulls(["q_issue"])
        for model, yhat, gg in (("glofas_raw", "fc", g), ("persistence_h0", "q_issue", p)):
            y, yh = gg["q_h0"].to_numpy(), gg[yhat].to_numpy()
            rows.append({"horizon": h, "model": model, "reference": "h0_cung_ngay (proxy)",
                         "n": gg.height, "NSE": metrics.nse(y, yh), "MAE": metrics.mae(y, yh),
                         "peak_bias": metrics.peak_bias(y, yh),
                         "obs_max": float(y.max()) if len(y) else float("nan"),
                         "n_issue_with_fc": f.height, "n_pairs_with_panel_obs": n_panel,
                         "n_pairs_with_lgbm": 0})
    res = pl.DataFrame(rows)
    with pl.Config(tbl_cols=20, tbl_width_chars=220, float_precision=3):
        print(res.drop("reference"))
    return res


# ================================================================ hình

COL = {"lgbm_E": "#2a78d6", "persistence": "#eb6834"}
LAB = {"lgbm_E": "LightGBM (config E)", "persistence": "Persistence"}


def plot(ev: pl.DataFrame, summ: pl.DataFrame, out: Path = OUT_FIG) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hs = list(cfg.HORIZONS)
    test = ("test_2022_07", "fixed_806")
    wf = ("wf_2013_2025", "fold_q95")

    def s(scope, model, col):
        x = summ.filter((pl.col("scope") == scope[0]) & (pl.col("thr_mode") == scope[1])
                        & (pl.col("model") == model)).sort("horizon")
        return x[col].to_list(), x

    def evs(scope, model, h, col):
        cond = (pl.col("model") == model) & (pl.col("horizon") == h)
        if scope == test:
            cond &= pl.col("scope") == "test_2022_07"
        else:
            cond &= (pl.col("scope") == "walk_forward") & (pl.col("thr_mode") == "fold_q95")
        return ev.filter(cond)[col].cast(pl.Float64).drop_nulls().drop_nans().to_numpy()

    n_test = s(test, "lgbm_E", "n_events")[0][0]
    n_wf = s(wf, "lgbm_E", "n_events")[0][0]
    fig, ax = plt.subplots(2, 2, figsize=(11.5, 9.0))
    plt.rcParams.update({"font.size": 9})
    w = 0.19
    # (A) tỷ lệ bắt
    a = ax[0, 0]
    for j, (scope, model, hatch, lab) in enumerate([
            (test, "lgbm_E", None, f"LightGBM E — test ≥ 2022-07 ({n_test} events)"),
            (test, "persistence", None, f"Persistence — test ≥ 2022-07 ({n_test} events)"),
            (wf, "lgbm_E", "///", f"LightGBM E — walk-forward 2013–2025 ({n_wf} events)"),
            (wf, "persistence", "///", f"Persistence — walk-forward 2013–2025 ({n_wf} events)")]):
        v, x = s(scope, model, "catch_rate")
        xs = np.arange(3) + (j - 1.5) * (w + 0.02)
        a.bar(xs, v, w, color=COL[model], hatch=hatch, edgecolor="white", linewidth=0.8, label=lab)
        for xi, vi, k, n in zip(xs, v, x["n_caught"].to_list(), x["n_events"].to_list()):
            a.text(xi, vi + 0.015, f"{k}/{n}", ha="center", va="bottom", fontsize=7, color="#333")
    a.set_xticks(range(3), [f"h = {h} d" for h in hs])
    a.set_ylim(0, 1.12)
    a.set_ylabel("Share of flood events caught")
    a.set_title("(a) Event caught: ≥ 1 day in event forecast ≥ level-1 threshold", fontsize=9.5)
    a.legend(fontsize=7, loc="upper right", frameon=False)
    # (B) tỷ số đỉnh, (C) lệch thời điểm — hộp = walk-forward, chấm = test
    for a, col, ttl, ylab, ref in ((ax[0, 1], "peak_ratio", "(b) Peak ratio = forecast max / observed max",
                                    "Forecast peak / observed peak", 1.0),
                                   (ax[1, 0], "timing_err", "(c) Peak timing error (+ = late)",
                                    "Forecast peak date − observed peak date (days)", 0.0)):
        for i, h in enumerate(hs):
            for k, model in enumerate(MODELS):
                x0 = i + (k - 0.5) * 0.36
                d = evs(wf, model, h, col)
                bp = a.boxplot(d, positions=[x0], widths=0.26, patch_artist=True, showfliers=False)
                for p in bp["boxes"]:
                    p.set(facecolor=COL[model], alpha=0.35, edgecolor=COL[model])
                for key in ("medians", "whiskers", "caps"):
                    for ln in bp[key]:
                        ln.set(color=COL[model], linewidth=1.4 if key == "medians" else 1)
                t = evs(test, model, h, col)
                jit = np.linspace(-0.07, 0.07, len(t)) if len(t) > 1 else np.zeros(len(t))
                a.scatter(x0 + jit, t, s=26, color=COL[model], edgecolor="white", linewidth=0.8, zorder=3)
        a.axhline(ref, color="#888", linestyle="--", linewidth=0.9)
        a.set_xticks(range(3), [f"h = {h} d" for h in hs])
        a.set_title(ttl, fontsize=9.5)
        a.set_ylabel(ylab)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    hnd = [Patch(facecolor=COL[m], alpha=0.35, edgecolor=COL[m], label=f"{LAB[m]} — walk-forward (box)")
           for m in MODELS] + [Line2D([], [], marker="o", linestyle="", color=COL[m],
                                      label=f"{LAB[m]} — test ≥ 2022-07 (dots)") for m in MODELS]
    fig.legend(handles=hnd, fontsize=7.5, frameon=False, loc="lower center", ncol=4,
               bbox_to_anchor=(0.5, 0.035), title="Panels (b)–(c)", title_fontsize=7.5)
    # (D) thời gian báo trước tới lúc bắt đầu đợt (đợt bắt được)
    a = ax[1, 1]
    for j, (scope, model, hatch) in enumerate([(test, "lgbm_E", None), (test, "persistence", None),
                                               (wf, "lgbm_E", "///"), (wf, "persistence", "///")]):
        v, x = s(scope, model, "lead_onset_median_caught")
        xs = np.arange(3) + (j - 1.5) * (w + 0.02)
        v = np.array(v, dtype=float)
        a.bar(xs, np.nan_to_num(v), w, color=COL[model], hatch=hatch, edgecolor="white", linewidth=0.8)
        for xi, vi, n in zip(xs, v, x["n_caught"].to_list()):
            ok = bool(np.isfinite(vi))
            up = not ok or vi >= 0
            a.text(xi, (vi if ok else 0.0) + (0.05 if up else -0.05),
                   f"{vi:+.1f}\n(n={n})" if ok else "n/a", ha="center",
                   va="bottom" if up else "top", fontsize=6.5, color="#333")
    a.axhline(0, color="#888", linewidth=0.9)
    a.set_xticks(range(3), [f"h = {h} d" for h in hs])
    lo = min(-1.5, a.get_ylim()[0] - 0.6)
    a.set_ylim(lo, max(4.2, a.get_ylim()[1] + 0.6))
    a.set_ylabel("Median lead time to event onset (days)")
    a.set_title("(d) Warning lead time, caught events only (≤ 0 = no early warning)", fontsize=9.5)
    for a in ax.ravel():
        a.grid(axis="y", color="#e5e5e5", linewidth=0.6)
        a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.suptitle("Event-based evaluation (FR-V5) — Huong River at Kim Long, GloFAS v4 discharge, "
                 "events = days ≥ level-1 threshold merged across ≤ 2 dry days", fontsize=10)
    fig.text(0.5, 0.004, "Test ≥ 2022-07: model trained ≤ 2022-06-30, threshold 806 m³/s. Walk-forward: "
             "yearly folds 2013–2025, expanding train window, per-fold threshold (Q95 of Sep–Dec flow\n"
             "in the fold's train window). LightGBM = mean of 3 seeds. Peak ratio/timing: forecast max "
             "searched in [onset − 1, end + h]; caught: event days; lead time: event ± 1 day.",
             ha="center", fontsize=7.5, color="#555")
    fig.tight_layout(rect=(0, 0.09, 1, 0.96))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


# ================================================================ in

def report(summ: pl.DataFrame) -> None:
    cols = ["scope", "thr_mode", "model", "horizon", "n_events", "n_caught", "catch_rate",
            "peak_ratio_median", "timing_err_median", "abs_timing_err_median",
            "lead_onset_median_caught", "n_lead_onset_pos", "n_fa_events"]
    with pl.Config(tbl_rows=200, tbl_cols=20, tbl_width_chars=220, float_precision=3):
        print(summ.select(cols))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from-cache", action="store_true", help=f"đọc dự báo đã lưu ở {PREDS}")
    ap.add_argument("--plot-only", action="store_true")
    ap.add_argument("--years", type=int, nargs="*", default=list(WF_YEARS))
    ap.add_argument("--max-gap", type=int, default=MAX_GAP)
    ap.add_argument("--out-dir", type=Path, default=None, help="ghi CSV/hình vào thư mục khác (thử)")
    a = ap.parse_args(argv)
    od = a.out_dir
    o_ev, o_sum, o_news, o_gl, o_fig = ((od / p.name if od else p)
                                        for p in (OUT_EVENTS, OUT_SUMMARY, OUT_NEWS, OUT_GLOFAS, OUT_FIG))
    if od:
        od.mkdir(parents=True, exist_ok=True)
    if a.plot_only:
        ev, summ = pl.read_csv(o_ev, try_parse_dates=True), pl.read_csv(o_sum)
        print(f"→ {plot(ev, summ, o_fig)}")
        return 0
    t0 = time.time()
    if a.from_cache:
        preds = pl.read_parquet(PREDS)
    else:
        preds = pl.concat([predict_main(), predict_wf(a.years)], how="diagonal_relaxed")
        PREDS.parent.mkdir(parents=True, exist_ok=True)
        preds.write_parquet(PREDS)
    check_reproduction(preds)
    obs = observed()
    ev, fa = score_all(preds, obs, a.max_gap)
    summ = summarize(ev, fa)
    ev.write_csv(o_ev)
    summ.write_csv(o_sum)
    nt = news_table(obs, ev)
    nt.write_csv(o_news)
    with pl.Config(tbl_rows=50, tbl_width_chars=200):
        print("\nĐối chiếu tin báo (flood_events.csv, 2013–):")
        print(nt)
    report(summ)
    glofas_raw_check().write_csv(o_gl)
    print(f"\n→ {o_ev}\n→ {o_sum}\n→ {o_news}\n→ {o_gl}\n→ {plot(ev, summ, o_fig)}"
          f"\n({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
