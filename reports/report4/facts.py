"""Số liệu của Report 4 (Spark + Deep Learning), mỗi số đối chiếu với nguồn lúc build.

Cùng cơ chế với ``reports/report3/facts.py`` (lớp ``Registry`` và các hàm định dạng
được *import* từ đó, không chép lại):

* ``csv``   — số tính lại từ ``reports/**/*.csv``, file cấu hình trong repo
  (``infra/spark/*``, ``requirements.txt``) hoặc metadata parquet trong ``data/``,
  rồi so với chuỗi văn bản định in. Lệch một ký tự là build hỏng.
* ``claim`` — câu định tính kiểm bằng một biểu thức trên dữ liệu. Sai là build hỏng.
* ``doc``   — số chỉ có trong tài liệu (``infra/spark/README.md``,
  ``docs/FINDINGS_HOURLY_FINEGRID.md``, docstring); ghi rõ nguồn, in ra ``OUTLINE_VI.txt``.

Phần walk-forward DL và DL một lần chia đã được Report 3 kiểm: các khoá đó lấy thẳng từ
sổ của ``report3/facts.load`` (cùng nguồn CSV, cùng phép kiểm), không viết lại.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REP = ROOT / "reports"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


r3f = _load("report3_facts_r4", ROOT / "reports" / "report3" / "facts.py")
f, sg, n, _csv = r3f.f, r3f.sg, r3f.n, r3f._csv

# cùng biểu thức với lớp quét số của build (report3/build_report.py NUM)
NUM = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+")


class Registry(r3f.Registry):
    """Như sổ Report 3, thêm: số phiên bản "4.1.3" cũng hợp lệ ở dạng lớp quét thấy ("4.1")."""

    def numbers(self) -> set[str]:
        out = super().numbers()
        for k, v in self.val.items():
            if self.kind[k] != "claim":
                out.update(NUM.findall(v))
        return out


R = Registry()

# Khoá lấy từ sổ Report 3 (đã kiểm với reports/wf_dl_summary.csv, dl_results.csv,
# lgbm_results.csv, ablation_ext.csv). Không đăng ký lại ⇒ không thể lệch Report 3.
FROM_R3 = (
    ["wf_nfold", "n_dlcfg", "nfA", "dlmlp2", "dl_sel_valid", "dl_sel_loses", "noise",
     "csi_lgb", "csi_lstmM", "csi_lstmP", "csi_mlpP", "pod_lgb", "pod_lstmM", "pod_mlpP",
     "pb_lgb", "pb_mlpP", "pb_lstmP", "sd_lgb", "sd_dl_lo", "sd_dl_hi", "thr_rng",
     "lstm_thr0", "dl_early_neg", "dl_late_pos"]
    + [f"{k}{h}" for k in ("dl_lgb", "dlsel", "lgb_nse", "lgb_pb", "abE") for h in (1, 2, 3)]
    + [f"{t}{h}_{s}" for t in ("lstmM", "lstmP", "mlpP") for h in (1, 2, 3)
       for s in ("m", "ci", "wl", "p")]
)

# Nhóm lần chạy LSTM phân tán trong reports/spark_dl_results.csv (tag → hàng của bảng)
DDP_RUNS = {
    "w_single": ["win_single_1x4", "win_single_1x4_r2"],
    "w_barrier": ["win_barrier_2x2", "win_barrier_2x2_r2"],
    "w_barrier64": ["win_barrier_2x2_bs32"],
    "w_td": ["win_distributor_local_2x2"],
    "d_single": ["docker_single_1x4", "docker_single_1x4_r2"],
    "d_tdlocal": ["docker_td_local_2x2", "docker_td_local_2x2_r2"],
    "c_td": ["docker_td_cluster_2x4", "docker_td_cluster_2x4_r2"],
    "c_td64": ["docker_td_cluster_2x4_bs32"],
    "c_barrier": ["docker_barrier_cluster_2x4", "docker_barrier_cluster_2x4_r2"],
}

# Cấu hình đo ETL trong reports/spark/etl_benchmark.csv (tag → hàng của bảng)
ETL_TAGS = ["cluster_1w_1c", "cluster_1w_4c", "cluster_2w_8c", "docker_local1",
            "docker_local4", "docker_local8", "docker_polars", "windows_local8_arrow",
            "windows_polars"]


def _lohi(key: str, s: pd.Series, exp: tuple[str, str], src: str, nd: int = 1) -> None:
    s = s.dropna()
    R.csv(f"{key}_lo", f(s.min(), nd), exp[0], src)
    R.csv(f"{key}_hi", f(s.max(), nd), exp[1], src)


def rng(key: str) -> str:
    """'a–b' từ hai khoá _lo/_hi, hoặc một số nếu hai đầu bằng nhau (dùng trong build)."""
    lo, hi = R(f"{key}_lo"), R(f"{key}_hi")
    return lo if lo == hi else f"{lo}&#8211;{hi}"


# ================================================================== nạp số
def load(cfg) -> Registry:
    # ------------------------------------------------ khoá từ Report 3
    r3 = r3f.load(cfg)
    for k in FROM_R3:
        R._put(k, r3.val[k], r3.src[k] + " [qua report3/facts.py]", r3.kind[k])
    R.bad += [b for b in r3.bad if b.strip().split(":")[0] in FROM_R3]

    # ------------------------------------------------ cụm Spark (cấu hình trong repo)
    dc = (ROOT / "infra" / "spark" / "docker-compose.yml").read_text(encoding="utf-8")
    wk = re.findall(r"deploy\.worker\.Worker\s+--cores (\d+) --memory (\d+)g", dc)
    src = "infra/spark/docker-compose.yml"
    R.csv("n_workers", str(len(wk)), "2", src)
    R.claim("one_master", dc.count("deploy.master.Master") == 1, "one master", src)
    R.csv("w_cores", wk[0][0] if len(set(wk)) == 1 else "?", "4", src)
    R.csv("w_mem", wk[0][1] if len(set(wk)) == 1 else "?", "2", src)
    R.csv("w_cores_tot", str(sum(int(c) for c, _ in wk)), "8", src)
    R.claim("mount", "../..:/opt/repo" in dc, "repository mounted at /opt/repo in every container", src)
    dfile = (ROOT / "infra" / "spark" / "Dockerfile").read_text(encoding="utf-8")
    m = re.search(r"apache/spark:([\d.]+)-java(\d+)-python3", dfile)
    R.csv("spark_ver", m.group(1), "4.1.3", "infra/spark/Dockerfile")
    R.csv("java_ver", m.group(2), "21", "infra/spark/Dockerfile")
    R.csv("torch_ver", re.search(r"torch==([\d.]+)", dfile).group(1), "2.14.1", "infra/spark/Dockerfile")
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    R.csv("pyspark_ver", re.search(r"pyspark==([\d.]+)", req).group(1), "4.1.3", "requirements.txt")
    R.csv("polars_ver", re.search(r"polars==([\d.]+)", req).group(1), "1.17.1", "requirements.txt")
    D = R.doc
    D("grid_sat", "0.1", "docs/FINDINGS_HOURLY_FINEGRID.md §2 (IMERG, GSMaP, ERA5: 0,1°)")
    D("grid_pccs", "0.04", "docs/FINDINGS_HOURLY_FINEGRID.md §2 (PERSIANN-CCS 0,04°)")
    D("pccs_cells", "625", "docs/FINDINGS_HOURLY_FINEGRID.md §2 (625 ô, chỉ 10–11/2020)")
    D("host_cores", "16", "infra/spark/README.md (máy đo: Windows 11, 16 lõi, 16 GB)")
    D("host_ram", "16", "infra/spark/README.md")
    D("docker_ram", "7.4", "infra/spark/README.md (Docker Desktop cấp 7,4 GB)")

    # ------------------------------------------------ quy mô dữ liệu
    eb = _csv("spark/etl_benchmark.csv")
    src = "reports/spark/etl_benchmark.csv"
    R.claim("eb_same", eb.rows_in.nunique() == 1 and eb.rows_out.nunique() == 1,
            "every benchmark run reads and writes the same rows", src)
    R.csv("era5_rows", n(eb.rows_in.iloc[0]), "6,544,896", src)
    R.csv("era5_mrows", f(eb.rows_in.iloc[0] / 1e6, 1), "6.5", src)
    R.csv("era5_out", n(eb.rows_out.iloc[0]), "272,704", src)
    R.csv("era5_files", n(eb.files.iloc[0]), "768", src)
    R.csv("era5_cells", n(eb.cells.iloc[0]), "64", src)
    R.csv("era5_days", n(eb.rows_out.iloc[0] / eb.cells.iloc[0]), "4,261", src)
    _data_scale()

    # ------------------------------------------------ ETL: thời gian theo cấu hình
    exp = {"cluster_1w_1c": (("94.7", "100.8"), ("54.0", "54.0")),
           "cluster_1w_4c": (("38.2", "38.2"), ("17.6", "17.7")),
           "cluster_2w_8c": (("40.5", "41.2"), ("15.2", "16.9")),
           "docker_local1": (("87.9", "99.4"), ("52.5", "52.8")),
           "docker_local4": (("33.4", "34.7"), ("14.7", "15.2")),
           "docker_local8": (("32.6", "32.9"), ("13.0", "13.1")),
           "docker_polars": (("8.7", "10.1"), None),
           "windows_local8_arrow": (("60.0", "60.0"), ("22.7", "22.7")),
           "windows_polars": (("3.4", "3.7"), None)}
    for t in ETL_TAGS:
        g = eb[eb.tag == t]
        _lohi(f"etl_{t}", g.seconds_etl, exp[t][0], src)
        if exp[t][1]:
            _lohi(f"sub_{t}", g.seconds_subbasin, exp[t][1], src)
        R.csv(f"nrun_{t}", n(len(g)), "1" if t == "windows_local8_arrow" else "2", src)
        R.csv(f"exe_{t}", n(g.n_executors.iloc[0]), {"cluster_1w_1c": "1", "cluster_1w_4c": "1",
                                                     "cluster_2w_8c": "2"}.get(t, "0"), src)
        R.csv(f"cores_{t}", n(g.cores.iloc[0]),
              {"cluster_1w_1c": "1", "docker_local1": "1", "cluster_1w_4c": "4",
               "docker_local4": "4"}.get(t, "16" if "polars" in t else "8"), src)
    mean = eb.groupby("tag").seconds_etl.mean()
    R.csv("spd_cl", f(mean["cluster_1w_1c"] / mean["cluster_1w_4c"], 1), "2.6", src + " (trung bình 2 lần)")
    R.csv("spd_loc", f(mean["docker_local1"] / mean["docker_local4"], 1), "2.8", src)
    R.claim("no_gain_2w", bool(mean["cluster_2w_8c"] >= mean["cluster_1w_4c"]),
            "two workers (8 cores) are no faster than one worker (4 cores)", src)
    R.csv("x_c2_wpol", f(mean["cluster_2w_8c"] / mean["windows_polars"], 1), "11.6", src)
    R.csv("x_arrow_wpol", f(mean["windows_local8_arrow"] / mean["windows_polars"], 1), "17.0", src)
    R.csv("x_dl8_dpol", f(eb[eb.tag == "docker_local8"].seconds_etl.min() / mean["docker_polars"], 1),
          "3.5", src + " (Spark tốt nhất / Polars TB, cùng container)")
    R.csv("x_dpol_wpol", f(mean["docker_polars"] / mean["windows_polars"], 1), "2.7", src)
    st = eb[eb.engine == "spark"]
    _lohi("start_dock", st[st.host == "linux-docker"].seconds_startup, ("4.1", "6.5"), src)
    R.csv("start_win", f(eb[eb.tag == "windows_local8_arrow"].seconds_startup.max(), 1), "18.4", src)

    # chỉ có trong tài liệu: nguyên nhân chậm + đối chiếu ETL với Polars
    D("mnt_1c_lo", "56", "infra/spark/README.md (đọc 768 file qua ổ mount, 1 lõi: 56–63 s)")
    D("mnt_1c_hi", "63", "infra/spark/README.md")
    D("mnt_8c_lo", "14", "infra/spark/README.md (8 lõi: 14–21 s)")
    D("mnt_8c_hi", "21", "infra/spark/README.md")
    D("mnt_pct_lo", "35", "infra/spark/README.md (35–65 % thời gian ETL)")
    D("mnt_pct_hi", "65", "infra/spark/README.md")
    D("n_part", "16", "infra/spark/README.md (64 khoá băm vào 16 phân hoạch)")
    D("part_max", "920,376", "infra/spark/README.md")
    D("part_mean", "436,326", "infra/spark/README.md")
    D("part_ratio", "2.1", "infra/spark/README.md (920 376 / 436 326)")
    D("t2m_diff", "0.001", "infra/spark/README.md (t2m_mean lệch 0,001 °C do làm tròn)")
    D("round_mm", "0.001", "infra/spark/README.md (làm tròn mưa tới 0,001 mm trước khi tìm giờ đỉnh)")
    D("sub_bad", "79", "infra/spark/README.md (peak_hour lệch 79/21 305 dòng trước khi sửa)")
    D("pccs_full", "130", "docs/FINDINGS_HOURLY_FINEGRID.md §5 (PCCS 2003–2026 ≈ 130 triệu dòng, ước tính)")

    # ------------------------------------------------ đặc trưng giờ: Spark = Polars từng bit
    tot = {}
    for s_, h_ in (("era5", "linux-docker"), ("era5", "windows-host"),
                   ("pccs", "linux-docker"), ("pccs", "windows-host")):
        p = _csv(f"spark/hourly_parity_{s_}_{h_}.csv")
        src = f"reports/spark/hourly_parity_{s_}_{h_}.csv"
        R.claim(f"bit_{s_}_{h_}", bool((p.n_exact_equal == p.n_both).all() and (p.max_abs_diff == 0).all()
                                        and (p.n_null_mismatch == 0).all()
                                        and (p.rows_only_polars + p.rows_only_spark == 0).all()),
                "every cell bit-identical, no row on one side only", src)
        tot[(s_, h_)] = p
        tag = f"{s_}_{'c' if h_ == 'linux-docker' else 'w'}"
        R.csv(f"par_sp_{tag}", f(p.seconds_spark.iloc[0], 1),
              {"era5_c": "28.6", "era5_w": "42.3", "pccs_c": "14.0", "pccs_w": "35.7"}[tag], src)
        R.csv(f"par_pl_{tag}", f(p.seconds_polars.iloc[0], 1),
              {"era5_c": "3.9", "era5_w": "1.3", "pccs_c": "0.2", "pccs_w": "0.2"}[tag], src)
    for s_, eh, ed in (("era5", "613,584", "230,064"), ("pccs", "8,784", "3,234")):
        a, b = tot[(s_, "linux-docker")], tot[(s_, "windows-host")]
        R.claim(f"par_same_{s_}", bool(a.n_both.tolist() == b.n_both.tolist()),
                "same cells compared on both hosts", f"reports/spark/hourly_parity_{s_}_*.csv")
        R.csv(f"par_nh_{s_}", n(a[a.level == "hourly"].n_both.sum()), eh, f"reports/spark/hourly_parity_{s_}_linux-docker.csv")
        R.csv(f"par_nd_{s_}", n(a[a.level == "daily"].n_both.sum()), ed, f"reports/spark/hourly_parity_{s_}_linux-docker.csv")
    a = tot[("era5", "linux-docker")]
    R.csv("par_ncol", n((a.level == "daily").sum()), "54", "reports/spark/hourly_parity_era5_linux-docker.csv")
    R.csv("par_nh_units", n((a.level == "hourly").sum()), "6", "reports/spark/hourly_parity_era5_linux-docker.csv")
    R.csv("par_hrows", n(a[a.level == "hourly"].rows.iloc[0]), "102,264",
          "reports/spark/hourly_parity_era5_linux-docker.csv")
    R.csv("x_par_c", f(a.seconds_spark.iloc[0] / a.seconds_polars.iloc[0], 1), "7.3",
          "reports/spark/hourly_parity_era5_linux-docker.csv")
    w = tot[("era5", "windows-host")]
    R.csv("x_par_w", f(w.seconds_spark.iloc[0] / w.seconds_polars.iloc[0], 1), "32.8",
          "reports/spark/hourly_parity_era5_windows-host.csv")

    # ------------------------------------------------ MLlib GBT / RF
    sr = _csv("spark_results.csv").set_index(["model", "horizon"])
    src = "reports/spark_results.csv"
    exp = {"spark_gbt": {"NSE": ("0.699", "0.429", "0.182"), "peak_bias": ("-0.50", "-0.74", "-0.87"),
                         "delta_NSE_vs_lgbm": ("-0.047", "+0.010", "+0.008")},
           "spark_rf": {"NSE": ("0.687", "0.454", "0.214"), "peak_bias": ("-0.52", "-0.75", "-0.87"),
                        "delta_NSE_vs_lgbm": ("-0.060", "+0.034", "+0.039")}}
    for mdl, cols in exp.items():
        tg = "gbt" if mdl.endswith("gbt") else "rf"
        for col, ev in cols.items():
            for h in (1, 2, 3):
                v = sr.loc[(mdl, h), col]
                txt = sg(v) if col.startswith("delta") else f(v, 2 if col == "peak_bias" else 3)
                R.csv(f"ml_{tg}_{col}_{h}", txt, ev[h - 1], src)
        _lohi(f"ml_{tg}_sec", sr.loc[mdl].seconds_total, {"gbt": ("354.4", "364.9"),
                                                           "rf": ("188.8", "225.1")}[tg], src)
        R.csv(f"ml_{tg}_grid", n(sr.loc[(mdl, 1), "grid_size"]), {"gbt": "8", "rf": "4"}[tg], src)
    lg = _csv("lgbm_results.csv").set_index("horizon")
    R.claim("ml_lgb_same", all(abs(sr.loc[("spark_gbt", h), "lgbm_NSE"] - lg.loc[h, "NSE"]) < 1e-6
                               for h in (1, 2, 3)),
            "LightGBM column in spark_results equals lgbm_results.csv", src + " vs lgbm_results.csv")
    R.csv("ml_ntrain", n(sr.n_train.iloc[0]), "4,550", src)
    R.csv("ml_ntest_lo", n(sr.n.min()), "1,520", src)
    R.csv("ml_ntest_hi", n(sr.n.max()), "1,522", src)
    R.csv("ml_sec_tot", n(sr.seconds_total.sum()), "1,686", src + " (tổng seconds_total)")
    R.csv("ml_cores", n(sr.cores.iloc[0]), "8", src)
    gp = [json.loads(x) for x in sr.loc["spark_gbt"].params]
    rp = [json.loads(x) for x in sr.loc["spark_rf"].params]
    tgd = _csv("spark/train_grid.csv")
    gg = [json.loads(x) for x in tgd[tgd.model == "spark_gbt"].params]
    rg = [json.loads(x) for x in tgd[tgd.model == "spark_rf"].params]
    R.claim("gbt_smallest", all(q["maxDepth"] == min(x["maxDepth"] for x in gg)
                                and q["stepSize"] == min(x["stepSize"] for x in gg) for q in gp),
            "GBT selects the shallowest, slowest-learning grid point at every horizon",
            src + " + reports/spark/train_grid.csv")
    R.csv("gbt_depth", n(gp[0]["maxDepth"]), "3", src)
    R.csv("gbt_step", f(gp[0]["stepSize"], 2), "0.05", src)
    R.csv("gbt_iter", n(gp[0]["maxIter"]), "150", src)
    R.claim("rf_deep", all(q["maxDepth"] == max(x["maxDepth"] for x in rg) for q in rp),
            "RF selects the deepest trees at every horizon", src)
    R.csv("rf_depth", n(rp[0]["maxDepth"]), "12", src)
    R.csv("rf_trees", n(rp[0]["numTrees"]), "200", src)
    R.csv("rf_mem", n(rg[0]["maxMemoryInMB"]) if len({x["maxMemoryInMB"] for x in rg}) == 1 else "?",
          "64", "reports/spark/train_grid.csv")
    R.csv("ml_ngrid", n(len(tgd)), "36", "reports/spark/train_grid.csv")
    D("ml_train_days", "2,177", "infra/spark/README.md (train 2010–2015)")
    D("ml_valid_days", "2,373", "infra/spark/README.md (valid 2016 → 06/2022)")
    D("oom_mem", "1,500", "infra/spark/README.md (executor 1 500 MB chết, exit code 52)")
    D("oom_code", "52", "infra/spark/README.md")
    D("oom_def", "256", "infra/spark/README.md (maxMemoryInMB mặc định 256 MB)")
    D("ok_mem", "1,800", "infra/spark/README.md (executor 1 800 MB chạy hết)")

    # ------------------------------------------------ LSTM phân tán (DDP)
    _ddp()

    # ------------------------------------------------ chi phí tính của walk-forward DL
    wf = _csv("wf_dl_folds.csv")
    src = "reports/wf_dl_folds.csv"
    mm = wf[(wf.run == "main") & (wf.model != "persistence")].drop_duplicates(["model", "year", "seed"])
    R.csv("wf_nfit", n(len(mm)), "168", src + " (4 mô hình × 14 năm × 3 seed)")
    R.csv("wf_sec", n(mm.time_s.sum()), "4,049", src + " (tổng time_s)")
    med = mm.groupby("model").time_s.median()
    R.csv("wf_med_lgb", f(med["lightgbm"], 1), "10.2", src)
    R.csv("wf_med_mlp", f(med["mlp_lag_peak"], 1), "9.4", src)
    R.csv("wf_med_lstm_lo", f(min(med["lstm_L30_mse"], med["lstm_L30_peak"]), 1), "32.8", src)
    R.csv("wf_med_lstm_hi", f(max(med["lstm_L30_mse"], med["lstm_L30_peak"]), 1), "34.5", src)
    wfs = (ROOT / "src" / "eval" / "walk_forward_dl.py").read_text(encoding="utf-8")
    R.claim("wf_pool", "ProcessPoolExecutor" in wfs, "folds run in a local process pool",
            "src/eval/walk_forward_dl.py")
    D("wf_procs", "6", "docs/FINDINGS_HOURLY_FINEGRID.md §12.2 (6 tiến trình × 2 luồng)")
    D("wf_min", "13", "docs/FINDINGS_HOURLY_FINEGRID.md §12.2 (~13 phút)")
    D("h_steps", "168", "src/models/dl_lstm.py docstring (LSTM giờ 7 × 24 bước, chưa cài đặt)")
    return R


def _data_scale() -> None:
    """Số dòng mưa giờ đọc từ metadata parquet (nhẹ, không đọc dữ liệu)."""
    raw = ROOT / "data" / "raw"
    sets = {"imerg": (raw / "gee" / "imerg", "50,477,000"),
            "gsmap": (raw / "gee" / "gsmap", "25,241,800"),
            "pccs": (raw / "persiann_ccs", "915,000")}
    try:
        import pyarrow.parquet as pq
        got = {}
        for k, (d, e) in sets.items():
            fs = sorted(d.glob("*.parquet"))
            if not fs:
                raise FileNotFoundError(d)
            got[k] = (fs, sum(pq.ParquetFile(x).metadata.num_rows for x in fs))
            R.csv(f"rows_{k}", n(got[k][1]), e, f"{d.relative_to(ROOT).as_posix()}/*.parquet (metadata)")
        im, gs = got["imerg"], got["gsmap"]
        src = "data/raw/gee/*/*.parquet (metadata)"
        R.csv("n_satfiles", n(len(im[0])), "346", src + " (số file mỗi sản phẩm)")
        R.claim("sat_same_files", len(im[0]) == len(gs[0]), "same number of monthly files", src)
        R.csv("sat_mrows", f((im[1] + gs[1]) / 1e6, 1), "75.7", src)
        cells = pq.read_table(gs[0][-1], columns=["lat", "lon"]).to_pandas().drop_duplicates()
        R.csv("sat_cells", n(len(cells)), "100", src)
        mb = sum(x.stat().st_size for x in (raw / "gee").rglob("*.parquet")) / 1e6
        R.csv("sat_mb", f(mb, 0), "99", "data/raw/gee (byte / 10^6)")
        mb = sum(x.stat().st_size for x in (raw / "rain_hourly").glob("*.parquet")) / 1e6
        R.csv("era5_mb", f(mb, 0), "75", "data/raw/rain_hourly (byte / 10^6)")
        sub = sorted((ROOT / "data" / "interim" / "spark" / "rain_subbasin_daily").rglob("*.parquet"))
        R.csv("sub_rows", n(sum(pq.ParquetFile(x).metadata.num_rows for x in sub)), "21,305",
              "data/interim/spark/rain_subbasin_daily (metadata)")
    except (ImportError, FileNotFoundError, StopIteration) as e:   # máy không có data/
        for k, (d, e_) in sets.items():
            if k not in R.val:
                R.doc(f"rows_{k}", e_, f"đếm metadata parquet 21/10/2026 ({d.name}; thiếu: {e})")
        for k, v in (("n_satfiles", "346"), ("sat_mrows", "75.7"), ("sat_cells", "100"),
                     ("sat_mb", "99"), ("era5_mb", "75"), ("sub_rows", "21,305")):
            if k not in R.val:
                R.doc(k, v, "docs/FINDINGS_HOURLY_FINEGRID.md §2, §5 / đếm ngày 21/10/2026")
        R.claim("sat_same_files", True, "same number of monthly files", "doc")


def _ddp() -> None:
    d = _csv("spark_dl_results.csv")
    src = "reports/spark_dl_results.csv"
    t = d[(d.fit == "train+valid") & (d.split == "test")]
    exp = {  # procs×threads, batch, epoch, train lo/hi, wall lo/hi, NSE h1/h2/h3
        "w_single": ("1 x 4", "64", "10", ("16.1", "18.2"), ("16.1", "18.2")),
        "w_barrier": ("2 x 2", "128", "13", ("17.6", "17.7"), ("26.3", "26.8")),
        "w_barrier64": ("2 x 2", "64", "8", ("17.8", "17.8"), ("26.6", "26.6")),
        "d_single": ("1 x 4", "64", "10", ("9.0", "9.5"), ("9.0", "9.5")),
        "d_tdlocal": ("2 x 2", "128", "13", ("9.9", "10.1"), ("16.3", "16.4")),
        "c_td": ("2 x 4", "128", "13", ("9.9", "10.1"), ("22.6", "23.2")),
        "c_td64": ("2 x 4", "64", "8", ("10.3", "10.3"), ("23.5", "23.5")),
        "c_barrier": ("2 x 4", "128", "13", ("9.9", "10.4"), ("15.0", "15.5")),
    }
    nse_exp = {"single": ("0.709", "0.432", "0.180"), "b128": ("0.712", "0.413", "0.160"),
               "b64": ("0.704", "0.413", "0.165")}
    for key, tags in DDP_RUNS.items():
        g = d[d.tag.isin(tags)]
        if key == "w_td":
            R.claim("td_win_fail", bool((g.status == "failed").all()
                                        and g.error.str.contains("libuv").all()),
                    "TorchDistributor fails on Windows: torch built without libuv", src)
            continue
        r = g.iloc[0]
        pt, gb, ep, trn, wal = exp[key]
        R.csv(f"{key}_pt", f"{int(r.num_processes)} x {int(r.threads_per_process)}", pt, src)
        R.csv(f"{key}_gb", n(r.global_batch), gb, src)
        R.csv(f"{key}_ep", n(r.best_epoch), ep, src)
        R.claim(f"{key}_ok", bool((g.status == "ok").all() and g.tag.nunique() == len(tags)),
                "all runs of the group finished", src)
        first = g.drop_duplicates("tag")
        _lohi(f"{key}_train", first.train_s, trn, src)
        _lohi(f"{key}_wall", first.wall_s, wal, src)
        tt = t[t.tag.isin(tags)].pivot_table(index="tag", columns="horizon", values="NSE")
        R.claim(f"{key}_rep", bool((tt.max() - tt.min()).max() < 5e-5),
                "repeated runs give the same NSE", src)
        grp = "single" if key.endswith("single") else ("b64" if key.endswith("64") else "b128")
        for h in (1, 2, 3):
            R.csv(f"{key}_nse{h}", f(tt[float(h)].iloc[0]), nse_exp[grp][h - 1], src)
    # cùng số rank và batch ⇒ cùng NSE bất kể cách phân tán (4 chữ số)
    b128 = t[t.tag.isin(DDP_RUNS["w_barrier"] + DDP_RUNS["d_tdlocal"] + DDP_RUNS["c_td"]
                        + DDP_RUNS["c_barrier"])]
    R.claim("ddp_same4", bool(b128.groupby("horizon").NSE.apply(lambda s: s.round(4).nunique() == 1).all()),
            "barrier, TorchDistributor local and TorchDistributor on two workers agree to four decimals", src)
    cols = ["NSE", "KGE", "RMSE", "MAE", "peak_bias", "POD", "FAR", "CSI"]
    key_ = ["fit", "split", "horizon"]
    a = d[d.tag == "docker_barrier_cluster_2x4"].set_index(key_)[cols].sort_index()
    b = d[d.tag == "docker_td_cluster_2x4"].set_index(key_)[cols].sort_index()
    R.claim("ddp_bit", bool(a.equals(b)), "barrier and TorchDistributor bit-identical on the cluster", src)
    wn = d[d.tag == "win_barrier_2x2"].set_index(key_)[cols].sort_index()
    R.claim("ddp_os", bool(((wn - b).abs() / b.abs().clip(lower=1)).max().max() < 1e-4),
            "Windows and container agree to better than 1e-4", src)
    # bản 1 tiến trình tái lập seed 42 của dl_results.csv
    dr = _csv("dl_results.csv")
    dr = dr[(dr.model == "lstm_L30_mse") & (dr.fit == "train+valid") & (dr.split == "test")].set_index("horizon")
    s1 = t[t.tag == "docker_single_1x4"].set_index("horizon").NSE
    R.claim("single_repro", all(abs(float(dr.loc[h, "NSE_seeds"].split(";")[0]) - s1[float(h)]) < 5e-4
                                for h in (1, 2, 3)),
            "single-process run reproduces seed 42 of dl_results.csv", src + " vs reports/dl_results.csv")
    c = t[t.tag == "docker_td_cluster_2x4"].set_index("horizon").NSE
    for h, e, es in ((1, "+0.003", "0.016"), (2, "-0.019", "0.018"), (3, "-0.020", "0.021")):
        R.csv(f"ddp_d{h}", sg(c[float(h)] - s1[float(h)]), e, src)
        R.csv(f"seed_sd{h}", f(dr.loc[h, "NSE_std"]), es, "reports/dl_results.csv (lstm_L30_mse, 3 seed)")
    r = d[d.tag == "docker_single_1x4"].iloc[0]
    R.csv("n_params", n(r.n_params), "19,395", src)
    R.csv("n_win", n(r.n_train), "2,162", src)
    R.csv("n_trval", n(r.n_trval), "4,535", src)
    R.csv("max_ep", n(r.max_epochs), "200", src)
    ov = d[d.tag.isin(DDP_RUNS["c_td"])].drop_duplicates("tag")
    _lohi("ov_td", ov.wall_s - ov.train_s, ("12.7", "13.1"), src + " (wall - train)")
    ov = d[d.tag.isin(DDP_RUNS["c_barrier"])].drop_duplicates("tag")
    _lohi("ov_bar", ov.wall_s - ov.train_s, ("5.1", "5.1"), src + " (wall - train)")
