"""Mưa vệ tinh theo giờ (IMERG / GSMaP-GC) có giúp mô hình ngày không? — ablation
trên split CHÍNH (Report 3).

Khác ``ablation_hourly.py`` (mưa ERA5 giờ chỉ có từ 2015 ⇒ split riêng): mưa vệ
tinh có từ 01/1998 nên dùng được đúng split chính của dự án

    train ≤ 2015-12-31 · valid 2016-01-01 → 2022-06-30 · test ≥ 2022-07-01

Hai nhóm, mỗi nhóm so với mốc của CHÍNH nó, trên đúng một tập hàng chung (ngày
có đủ mọi cột của mọi cấu hình trong nhóm):

    r2   daily_panel.parquet (2010→)
         A0                       cột panel gốc (= lgbm.feature_cols)
         A0+imerg                 + 9 đặc trưng giờ IMERG toàn lưu vực
         A0+gsmap_gc              + 9 đặc trưng giờ GSMaP-GC toàn lưu vực
         A0+gsmap_gc luu vuc con  + 45 đặc trưng giờ GSMaP-GC của 5 lưu vực con
    ext  daily_panel_ext.parquet, train từ 1998-01-04 cho MỌI cấu hình
         E0                       đúng tập cột cấu hình E của ablation_ext.py
         E0+gsmap_gc              + 9 cột toàn lưu vực
         E0+imerg                 + 9 cột toàn lưu vực

LightGBM tham số ``lgbm.py``, 3 seed. ``valid`` = fit train → đánh giá valid;
``test`` = fit train+valid → đánh giá test (giống lgbm.py). ΔNSE so với mốc nhóm:
theo từng seed, trung bình 3 seed, và bootstrap khối 30 ngày × 1000 lần trên dự
báo trung bình 3 seed (cùng chỉ số khối cho hai cấu hình ⇒ so ghép cặp; code của
``ablation_hourly.block_boot_dnse``). Ngưỡng mức 1 lấy từ ``reports/risk_levels.csv``.

Cột vệ tinh đổi tên ``<nguồn>_hr_<đặc trưng>_<đơn vị>`` để không trùng cột ERA5.
Cần chạy trước ``python -m src.features.hourly_features --source imerg`` và
``--source gsmap_gc``.

    python -m src.models.ablation_sat                # cả hai nhóm
    python -m src.models.ablation_sat --groups r2
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import numpy as np
import polars as pl

from src import config as cfg
from src.eval import metrics
from src.features import basins as bs
from src.features import hourly_features as hf
from src.models import ablation_ext as ax
from src.models import ablation_hourly as ab

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = cfg.ROOT / "reports" / "ablation_hourly_sat.csv"
PANEL = hf.PANEL
PANEL_EXT = cfg.DATA_PROCESSED / "daily_panel_ext.parquet"
SEEDS = ab.SEEDS
EXT_START = date(1998, 1, 4)     # vệ tinh từ 01/01/1998 07h VN ⇒ r72h đủ từ ngày 4
GROUPS = ("r2", "ext")
SPLIT_NOTE = "split chinh: train <=2015-12-31 / valid ->2022-06-30 / test >=2022-07-01"


def main_split(start: date | None = None) -> dict[str, tuple[date, date]]:
    """Split chính (``walk_forward.regime_split``) dạng khoảng ngày cho ``ab.masks``."""
    tr_end = date.fromisoformat(cfg.TRAIN_END)
    return {"train": (start or date(1900, 1, 1), tr_end),
            "valid": (tr_end + timedelta(days=1), date.fromisoformat(cfg.VALID_END)),
            "test": (date.fromisoformat(cfg.GLOFAS_REGIME_BREAK), date(2100, 1, 1))}


def sat_cols(source: str, units) -> list[str]:
    return [f"{source}_{c}" for c in hf.feature_names(units)]


def load_sat(source: str) -> pl.DataFrame:
    """Đặc trưng ngày của nguồn vệ tinh, cột đổi tên ``<nguồn>_hr_*``."""
    p = hf.feats_path(source)
    if not p.exists():
        raise SystemExit(f"Thiếu {p.name} — chạy `python -m src.features.hourly_features "
                         f"--source {source}` trước.")
    f = pl.read_parquet(p)
    return f.rename({c: f"{source}_{c}" for c in f.columns if c.startswith(hf.PREFIX)})


def configs(group: str, base: list[str]) -> dict[str, list[str]]:
    """Cấu hình của nhóm; khoá đầu tiên là mốc."""
    whole, subs = [hf.WHOLE], list(bs.SUBBASINS)
    if group == "r2":
        return {"A0 panel goc": base,
                "A0+imerg": base + sat_cols("imerg", whole),
                "A0+gsmap_gc": base + sat_cols("gsmap_gc", whole),
                "A0+gsmap_gc luu vuc con": base + sat_cols("gsmap_gc", subs)}
    if group == "ext":
        return {"E0 (=E ablation_ext)": base,
                "E0+gsmap_gc": base + sat_cols("gsmap_gc", whole),
                "E0+imerg": base + sat_cols("imerg", whole)}
    raise ValueError(group)


def load_group(group: str) -> tuple[pl.DataFrame, dict[str, list[str]], dict]:
    """(panel đã ghép cột vệ tinh, cấu hình, split) của một nhóm."""
    p2 = pl.read_parquet(PANEL)
    base = ab.base_cols(p2)                                   # = lgbm.feature_cols
    if group == "r2":
        panel, start = p2, None
    else:
        panel, start = pl.read_parquet(PANEL_EXT), EXT_START
        base = base + ax.SOIL + ax.RESERVOIR_PROXY + ax.CONTEXT
    for s in ("imerg", "gsmap_gc"):
        panel = hf.join_panel(panel, load_sat(s))
    return panel.sort("date"), configs(group, base), main_split(start)


def run_group(group: str, thr1: float) -> list[dict]:
    panel, cfgs, split = load_group(group)
    union = sorted({c for f in cfgs.values() for c in f})
    names = list(cfgs)
    start = split["train"][0] if split["train"][0].year > 1900 else "đầu panel"
    print(f"\n=== Nhóm {group}: mốc '{names[0]}'; train từ {start}")
    for k, f in cfgs.items():
        print(f"  {k:<26} {len(f):3d} feature")

    rows, preds, ys, imps = [], {}, {}, []
    for h in cfg.HORIZONS:
        m = ab.masks(panel, union, h, split)
        y = panel[f"target_h{h}"].to_numpy().astype(float)
        q0 = panel["discharge"].to_numpy().astype(float)
        d = panel["date"].cast(pl.Date)
        print(f"h={h}: train {m['train'].sum()} ({d.filter(pl.Series(m['train'])).min()}→) · "
              f"valid {m['valid'].sum()} · test {m['test'].sum()} ngày", flush=True)
        for ph, (tr, ev) in {"valid": (m["train"], m["valid"]),
                             "test": (m["train"] | m["valid"], m["test"])}.items():
            ys[(ph, h)] = y[ev]
            rows.append({"group": group, "config": "persistence", "phase": ph, "horizon": h,
                         "seed": "-", "n_train": 0, "n_eval": int(ev.sum()), "n_feat": 1,
                         **ab.score(y[ev], q0[ev], thr1)})
            for name, feats in cfgs.items():
                X = panel.select(feats).to_numpy().astype(float)
                for seed in SEEDS:
                    yhat, model = ab.fit_predict(X, feats, y, tr, ev, seed)
                    preds[(name, ph, h, seed)] = yhat
                    rows.append({"group": group, "config": name, "phase": ph, "horizon": h,
                                 "seed": str(seed), "n_train": int(tr.sum()),
                                 "n_eval": int(ev.sum()), "n_feat": len(feats),
                                 **ab.score(y[ev], yhat, thr1)})
                    if ph == "test" and seed == cfg.SEED and name != names[0]:
                        g = model.booster_.feature_importance("gain")
                        sat = sum(v for f, v in zip(feats, g) if f not in cfgs[names[0]])
                        imps.append((name, h, float(sat / g.sum())))
    rows += summarize(group, rows, preds, ys, names, thr1)
    for name, h, share in imps:
        print(f"  gain cột vệ tinh (test, seed {cfg.SEED}) {name:<26} h={h}: {share:.1%}")
    return rows


def summarize(group: str, rows: list[dict], preds: dict, ys: dict, names: list[str],
              thr1: float) -> list[dict]:
    """Dòng ``seed = mean3``: trung bình 3 seed + ΔNSE so với mốc (từng seed, trung
    bình) + bootstrap khối trên dự báo trung bình 3 seed."""
    base = names[0]
    nse = {(r["config"], r["phase"], r["horizon"], r["seed"]): r["NSE"]
           for r in rows if r["group"] == group}
    out = []
    for (ph, h), y in ys.items():
        p_base = np.mean([preds[(base, ph, h, s)] for s in SEEDS], axis=0)
        for name in names:
            per = [r for r in rows if r["group"] == group and r["config"] == name
                   and r["phase"] == ph and r["horizon"] == h]
            row = {"group": group, "config": name, "phase": ph, "horizon": h, "seed": "mean3",
                   "n_train": per[0]["n_train"], "n_eval": per[0]["n_eval"],
                   "n_feat": per[0]["n_feat"]}
            for k in ("NSE", "KGE", "RMSE", "peak_bias", "POD1", "FAR1", "CSI1"):
                row[k] = float(np.mean([r[k] for r in per]))
            row["n_pos1"] = per[0]["n_pos1"]
            row["NSE_sd"] = float(np.std([r["NSE"] for r in per], ddof=1))
            p_ens = np.mean([preds[(name, ph, h, s)] for s in SEEDS], axis=0)
            row["NSE_ens"] = metrics.nse(y, p_ens)
            if name != base:
                d_seed = [nse[(name, ph, h, str(s))] - nse[(base, ph, h, str(s))] for s in SEEDS]
                ci, p_pos = ab.block_boot_dnse(y, p_base, p_ens)
                row.update({"dNSE": float(np.mean(d_seed)),
                            **{f"dNSE_seed{s}": v for s, v in zip(SEEDS, d_seed)},
                            "dNSE_ens": row["NSE_ens"] - metrics.nse(y, p_base),
                            "dNSE_ci_lo": ci[0], "dNSE_boot_med": ci[1], "dNSE_ci_hi": ci[2],
                            "p_dNSE_pos": p_pos})
            out.append(row)
    # ΔNSE từng seed cho cả dòng từng seed
    for r in rows:
        if r["group"] == group and r["seed"] not in ("-", "mean3") and r["config"] != base:
            r["dNSE"] = r["NSE"] - nse[(base, r["phase"], r["horizon"], r["seed"])]
    return out


def report(res: pl.DataFrame) -> None:
    s = res.filter(pl.col("seed") == "mean3")
    with pl.Config(tbl_rows=80, tbl_cols=20, float_precision=3, tbl_width_chars=220):
        for g in res["group"].unique(maintain_order=True):
            x = s.filter(pl.col("group") == g)
            print(f"\n--- {g}: NSE trung bình 3 seed (valid / test)")
            print(x.pivot(on=["phase", "horizon"], index="config", values="NSE"))
            print(f"--- {g}: test, ΔNSE so với mốc + CI95 bootstrap khối {ab.BLOCK} ngày × "
                  f"{ab.N_BOOT} (dự báo TB 3 seed), Δ từng seed 42/7/2026")
            t = x.filter((pl.col("phase") == "test") & pl.col("dNSE").is_not_null())
            for r in t.iter_rows(named=True):
                print(f"  h={r['horizon']} {r['config']:<26} NSE {r['NSE']:.3f}  Δ {r['dNSE']:+.3f} "
                      f"[{r['dNSE_ci_lo']:+.3f}, {r['dNSE_ci_hi']:+.3f}] P(Δ>0) {r['p_dNSE_pos']:.2f}"
                      f"  seed {r['dNSE_seed42']:+.3f}/{r['dNSE_seed7']:+.3f}/{r['dNSE_seed2026']:+.3f}"
                      f"  peak_bias {r['peak_bias']:+.3f}")
            h1 = x.filter((pl.col("phase") == "test") & (pl.col("horizon") == 1))
            print(f"--- {g}: test h=1, mức nguy cơ 1")
            print(h1.select("config", "NSE", "peak_bias", "POD1", "FAR1", "CSI1", "n_pos1"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--groups", nargs="+", choices=GROUPS, default=list(GROUPS))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)

    thr1 = float(pl.read_csv(ab.RISK).filter(pl.col("muc") == "nguy_co_1")["nguong_m3s"].item())
    print(f"{SPLIT_NOTE}; ngưỡng mức 1 = {thr1:.1f} m³/s; seed {SEEDS}")
    rows = []
    for g in a.groups:
        rows += run_group(g, thr1)
    res = pl.from_dicts(rows, infer_schema_length=None).with_columns(pl.lit(SPLIT_NOTE).alias("split"))
    res.write_csv(a.out, float_precision=5)
    report(res)
    print(f"\n→ {a.out} ({res.height} dòng)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
