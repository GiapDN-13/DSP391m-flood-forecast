"""Deep Learning dự báo lưu lượng 1–3 ngày: LSTM nhiều đầu ra (Report 4).

So với LightGBM (`src/models/lgbm.py`), LSTM **không** nhận các cột lag dựng
sẵn mà đọc thẳng một cửa sổ L ngày các biến gốc rồi tự học độ trễ:

    discharge, rain_thuong, rain_trung, rain_ha, rain_basin, api,
    doy_sin, doy_cos, mua_lu                         (cửa sổ [t-L+1 .. t])
        → LSTM → Linear → (log Q_{t+1}, log Q_{t+2}, log Q_{t+3})

Giữ y nguyên các quyết định của LightGBM để bảng so sánh công bằng:

* **Split** theo chế độ GloFAS (`walk_forward.regime_split`): train ≤ 2015-12-31,
  valid tới 2022-06-30, test từ 2022-07-01. Early stopping chạy trên valid; sau
  đó **huấn luyện lại trên train+valid** đúng số epoch tốt nhất (`refit`) — vì
  LightGBM cũng học trên train+valid. Kết quả chỉ-train vẫn được ghi để đối chiếu.
* **Mục tiêu log1p(Q)** (lệch phải, skew 5,91); mưa và API cũng log1p. Chuẩn hoá
  z-score bằng thống kê **chỉ của tập train**.
* **Metric** từ `src/eval/metrics.py`; ngưỡng mức nguy cơ 1 = Q95 mùa lũ trên
  train+valid, y như `src/features/risk_levels.py` / `classifier.py`. POD/FAR/CSI
  ở đây tính bằng cách so **lưu lượng dự báo** với ngưỡng (mô hình hồi quy).

Thêm hai thứ của riêng DL:

* **Dự báo phần dư** (`residual`): đầu ra = log Q_t + Δ. Persistence đã đạt
  NSE 0,54 ở h=1 nên cho mạng học phần chênh dễ hơn học lại mức nền.
* **Loss nhấn đỉnh** (`loss="peak"`): MSE trên log, trọng số mỗi mẫu
  w = clip(Q_{t+h} / Q̄_train, 1, w_max) — ngày lũ nặng ký hơn ngày kiệt.

Baseline DL để đối chứng: **MLP** trên đúng bộ cột của LightGBM tại ngày t
(cửa sổ L = 1, `features="full"`).

Kết quả lần chạy 20/10/2026 (`reports/dl_results.csv`; test, học trên
train+valid, trung bình ± sd 3 seed; NSE h1 / h2 / h3):

    LightGBM (chạy lại, khớp lgbm_results.csv)   0,747 / 0,420 / 0,175
    LSTM L=30, MSE                               0,725±0,016 / 0,446±0,018 / 0,198±0,021
    LSTM chọn theo valid (L=14, đủ cột panel)    0,709±0,018 / 0,404±0,002 / 0,171±0,017
    MLP trên cột lag, loss nhấn đỉnh             0,713±0,029 / 0,490±0,003 / 0,220±0,067

→ h=1: LightGBM vẫn tốt nhất. h=2–3: đa số cấu hình DL nhỉnh hơn 0,02–0,07 NSE,
cỡ 1–2 sd giữa các seed, và mọi mô hình vẫn < 0,5 ở h=2–3. Loss nhấn đỉnh giảm
cắt ngọn (peak_bias h2 −0,59 so với −0,73) và tăng POD nhưng tăng cả FAR.

Chạy được trong Spark TorchDistributor
--------------------------------------
`train(config) -> dict` là hàm thuần: không đọc biến toàn cục nào ngoài hằng số
mặc định, dữ liệu đọc từ `config["panel_path"]`. Khi `WORLD_SIZE > 1` (torchrun
hoặc TorchDistributor đặt sẵn RANK/WORLD_SIZE/MASTER_ADDR/MASTER_PORT) hàm tự
`init_process_group("gloo")`, bọc mô hình bằng DDP và chia mẫu bằng
DistributedSampler; chỉ rank 0 trả kết quả đầy đủ::

    from pyspark.ml.torch.distributor import TorchDistributor
    from src.models.dl_lstm import DEFAULTS, train
    conf = {**DEFAULTS, "panel_path": "/dbfs/.../daily_panel.parquet"}
    res = TorchDistributor(num_processes=4, local_mode=False,
                           use_gpu=False).run(train, conf)

Trên một máy: ``python -m src.models.dl_lstm --ddp 2`` (tự spawn 2 tiến trình) hoặc
``torchrun --nproc_per_node=2 -m src.models.dl_lstm --ddp 1``.

TorchDistributor KHÔNG chạy trên Windows (torchrun cần libuv, bản torch Windows
không có) — trên Windows dùng ``python -m src.distributed.spark_dl --engine barrier``.

Kết quả phụ thuộc số luồng torch (thứ tự cộng số thực đổi → early stopping dừng ở
epoch khác, dao động ngang độ lệch giữa seed). Muốn tái lập đúng
``reports/dl_results.csv`` phải chạy ``--threads 2``.

Mở rộng sang đầu vào theo giờ (chưa cài đặt)
------------------------------------------
Mưa ERA5 theo giờ đã có (`data/raw/rain_hourly`, 64 ô 0,1°, 2015–2026). Hướng
mở rộng là **multi-timescale LSTM** (Gauch et al., 2021, HESS 25, 2045–2062):
một nhánh LSTM ngày đọc lịch sử dài (vd. 365 ngày), trạng thái (h, c) của nó ở
ngày t−7 được chiếu tuyến tính sang khởi tạo nhánh LSTM giờ, nhánh giờ đọc
7×24 = 168 giờ gần nhất (đầu vào = 64 ô hoặc gộp theo tiểu lưu vực thượng/
trung/hạ) và có đầu ra riêng; loss = tổng NSE*/MSE của hai thang thời gian.
Lưu ý khi làm: (1) mưa giờ chỉ từ 2015 → phải dời split (vd. train 2015–2019);
(2) mục tiêu GloFAS vẫn theo ngày nên đầu ra giờ cần nhãn theo giờ (trạm đo)
hoặc chỉ dùng nhánh giờ làm đầu vào; (3) batch × 168 bước × 64 ô vẫn vừa CPU.

    python -m src.models.dl_lstm                 # toàn bộ thí nghiệm + CSV + hình
    python -m src.models.dl_lstm --jobs 4 --threads 4
    python -m src.models.dl_lstm --quick         # chạy thử vài epoch
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

import numpy as np
import polars as pl
import torch
import torch.distributed as dist
from torch import nn
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler, TensorDataset

from src import config as cfg
from src.eval import metrics
from src.features.risk_levels import FLOOD_MONTHS, QUANTILES

PANEL = cfg.DATA_PROCESSED / "daily_panel.parquet"
OUT_CSV = cfg.ROOT / "reports" / "dl_results.csv"
OUT_FIG = cfg.FIGURES / "report" / "dl_vs_lgbm_en.png"
LGBM_CLS = cfg.ROOT / "reports" / "classifier_results.csv"

SEEDS = (42, 7, 2026)
BASE_VARS = ["discharge", "rain_thuong", "rain_trung", "rain_ha", "rain_basin",
             "api", "doy_sin", "doy_cos", "mua_lu"]
# Cột không âm, lệch phải → log1p trước khi chuẩn hoá. q_diff* có thể âm nên không.
LOG_PREFIXES = ("discharge", "rain_", "api")
DROP_COLS = {"date", "alert_level", "risk_level"}   # giống lgbm.feature_cols

DEFAULTS: dict = {
    "name": "lstm_L30_mse",
    "panel_path": str(PANEL),
    "model": "lstm",           # "lstm" | "mlp"
    "features": "base",        # "base" = biến gốc; "full" = mọi cột số của panel
    "seq_len": 30,
    "loss": "mse",             # "mse" | "peak"
    "peak_w_max": 20.0,
    "residual": True,
    "hidden": 64,
    "layers": 1,
    "dropout": 0.2,
    "lr": 1e-3,
    "weight_decay": 1e-4,
    "batch_size": 64,
    "max_epochs": 200,
    "patience": 20,
    "refit": True,
    "seed": 42,
    "num_threads": 4,
    "train_end": cfg.TRAIN_END,
    "valid_end": cfg.VALID_END,
    "test_start": cfg.GLOFAS_REGIME_BREAK,
}

# Lưới thí nghiệm. Mỗi cấu hình chạy với 3 seed.
EXPERIMENTS: list[dict] = [
    {"name": "lstm_L14_mse", "seq_len": 14},
    {"name": "lstm_L30_mse", "seq_len": 30},
    {"name": "lstm_L14_peak", "seq_len": 14, "loss": "peak"},
    {"name": "lstm_L30_peak", "seq_len": 30, "loss": "peak"},
    {"name": "lstm_L30_mse_noresid", "seq_len": 30, "residual": False},
    {"name": "lstm_L14_full_mse", "seq_len": 14, "features": "full"},
    {"name": "mlp_lag_mse", "model": "mlp", "seq_len": 1, "features": "full"},
    {"name": "mlp_lag_peak", "model": "mlp", "seq_len": 1, "features": "full",
     "loss": "peak"},
]


# ----------------------------------------------------------------- dữ liệu

def feature_list(schema: dict, mode: str) -> list[str]:
    """Cột đầu vào. "full" lấy mọi cột số trừ date/target/nhãn, như LightGBM."""
    if mode == "base":
        return list(BASE_VARS)
    if mode == "full":
        return [c for c, t in schema.items()
                if c not in DROP_COLS and not c.startswith("target_") and t.is_numeric()]
    raise ValueError(f"features không hợp lệ: {mode}")


def log_transform(X: np.ndarray, cols: list[str]) -> np.ndarray:
    """log1p cho các cột lưu lượng / mưa / API (giá trị âm do lỗi số bị kẹp về 0)."""
    X = X.astype(np.float64, copy=True)
    for j, c in enumerate(cols):
        if c.startswith(LOG_PREFIXES):
            X[:, j] = np.log1p(np.clip(X[:, j], 0, None))
    return X


def split_masks(dates: np.ndarray, conf: dict) -> tuple[np.ndarray, ...]:
    """train / valid / test theo mốc trong config (mặc định = regime_split)."""
    d = dates.astype("datetime64[D]")
    tr = d <= np.datetime64(conf["train_end"])
    va = (d > np.datetime64(conf["train_end"])) & (d <= np.datetime64(conf["valid_end"]))
    te = d >= np.datetime64(conf["test_start"])
    return tr, va, te


def fit_scaler(X_train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Trung bình / độ lệch chuẩn theo cột, CHỈ trên hàng của tập train."""
    mu = np.nanmean(X_train, axis=0)
    sd = np.nanstd(X_train, axis=0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-8), sd, 1.0)
    return mu, sd


def make_windows(X: np.ndarray, L: int) -> tuple[np.ndarray, np.ndarray]:
    """Cửa sổ trượt kết thúc tại t: W[k] = X[t-L+1 .. t], chỉ giữ cửa sổ đủ số.

    Trả về (chỉ số hàng t, mảng (n, L, F)). Cửa sổ chỉ chứa dữ liệu ≤ t nên không
    rò rỉ tương lai (`tests/test_dl_lstm.py` khoá điều này).
    """
    T, F = X.shape
    if T < L:
        return np.empty(0, dtype=np.int64), np.empty((0, L, F), dtype=X.dtype)
    W = np.lib.stride_tricks.sliding_window_view(X, L, axis=0)   # (T-L+1, F, L)
    W = np.moveaxis(W, -1, 1)                                    # (T-L+1, L, F)
    end = np.arange(L - 1, T)
    ok = np.isfinite(W).all(axis=(1, 2))
    return end[ok], np.ascontiguousarray(W[ok])


def risk_threshold(q: np.ndarray, dates: np.ndarray, fit_mask: np.ndarray) -> float:
    """Ngưỡng mức nguy cơ 1 = phân vị Q95 mùa lũ trên train+valid (như risk_levels)."""
    months = (dates.astype("datetime64[M]").astype(int) % 12) + 1
    s = q[fit_mask & np.isin(months, list(FLOOD_MONTHS)) & np.isfinite(q)]
    return float(np.quantile(s, QUANTILES["nguy_co_1"]))   # nội suy tuyến tính = pandas


def prepare(df: pl.DataFrame, conf: dict) -> dict:
    """Panel → các mảng sẵn sàng cho mạng (đã log, chuẩn hoá, cắt cửa sổ, chia tập)."""
    df = df.sort("date")
    cols = feature_list(dict(df.schema), conf["features"])
    if "discharge" not in cols:
        raise ValueError("cần cột discharge trong đầu vào")
    q_idx = cols.index("discharge")
    dates = df["date"].cast(pl.Date).to_numpy()
    X = log_transform(df.select(cols).cast(pl.Float64).to_numpy(), cols)
    q = df["discharge"].cast(pl.Float64).to_numpy()
    hz = [f"target_h{h}" for h in cfg.HORIZONS]
    Y = df.select(hz).cast(pl.Float64).to_numpy()            # null → nan

    tr, va, te = split_masks(dates, conf)
    mu, sd = fit_scaler(X[tr])
    Xs = ((X - mu) / sd).astype(np.float32)
    y_mu, y_sd = float(mu[q_idx]), float(sd[q_idx])         # cùng thang với đầu vào Q
    Ys = ((np.log1p(np.clip(Y, 0, None)) - y_mu) / y_sd).astype(np.float32)

    q_ref = float(np.nanmean(q[tr]))
    Wt = np.clip(Y / q_ref, 1.0, conf["peak_w_max"]) if conf["loss"] == "peak" \
        else np.ones_like(Y)
    Wt = np.nan_to_num(Wt, nan=1.0).astype(np.float32)

    end, win = make_windows(Xs, conf["seq_len"])
    y_ok = np.isfinite(Ys[end]).all(axis=1)
    sets = {}
    for name, m, need_y in (("train", tr, True), ("valid", va, True),
                            ("trval", tr | va, True), ("test", te, False)):
        k = m[end] & (y_ok if need_y else True)
        sets[name] = {"X": win[k], "Y": Ys[end[k]], "W": Wt[end[k]],
                      "Yraw": Y[end[k]], "date": dates[end[k]]}
    return {"sets": sets, "cols": cols, "q_idx": q_idx, "y_mu": y_mu, "y_sd": y_sd,
            "thr": risk_threshold(q, dates, tr | va), "mu": mu, "sd": sd}


# ----------------------------------------------------------------- mô hình

class LSTMNet(nn.Module):
    """LSTM → trạng thái cuối → Linear ra 3 horizon (chuẩn hoá log)."""

    def __init__(self, n_in: int, n_out: int, hidden: int, layers: int,
                 dropout: float, residual: bool, q_idx: int):
        super().__init__()
        self.lstm = nn.LSTM(n_in, hidden, num_layers=layers, batch_first=True,
                            dropout=dropout if layers > 1 else 0.0)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, n_out)
        self.residual, self.q_idx = residual, q_idx

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        y = self.head(self.drop(out[:, -1]))
        if self.residual:                        # neo vào log Q_t (persistence)
            y = y + x[:, -1, self.q_idx:self.q_idx + 1]
        return y


class MLPNet(nn.Module):
    """Baseline DL: MLP 2 lớp ẩn trên cửa sổ đã làm phẳng (L = 1 → cột lag của panel)."""

    def __init__(self, n_in: int, n_out: int, hidden: int, dropout: float,
                 residual: bool, q_idx: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(), nn.Linear(n_in, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, n_out))
        self.residual, self.q_idx = residual, q_idx

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.net(x)
        if self.residual:
            y = y + x[:, -1, self.q_idx:self.q_idx + 1]
        return y


def build_model(conf: dict, n_feat: int, q_idx: int) -> nn.Module:
    n_out = len(cfg.HORIZONS)
    if conf["model"] == "lstm":
        return LSTMNet(n_feat, n_out, conf["hidden"], conf["layers"], conf["dropout"],
                       conf["residual"], q_idx)
    if conf["model"] == "mlp":
        return MLPNet(n_feat * conf["seq_len"], n_out, conf["hidden"], conf["dropout"],
                      conf["residual"], q_idx)
    raise ValueError(f"model không hợp lệ: {conf['model']}")


def weighted_mse(pred: torch.Tensor, y: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
    """MSE trên log chuẩn hoá, trọng số theo mẫu × horizon (w = 1 → MSE thường)."""
    return ((pred - y) ** 2 * w).sum() / w.sum()


# ----------------------------------------------------------------- huấn luyện

def _dist_env() -> tuple[int, int, bool]:
    """(world_size, rank, đã tự init?) — đọc biến môi trường torchrun/TorchDistributor."""
    ws = int(os.environ.get("WORLD_SIZE", "1"))
    if ws <= 1:
        return 1, 0, False
    created = False
    if not dist.is_initialized():
        dist.init_process_group("gloo")          # CPU; MASTER_ADDR/PORT từ môi trường
        created = True
    return dist.get_world_size(), dist.get_rank(), created


def _tensors(s: dict) -> tuple[torch.Tensor, ...]:
    return (torch.from_numpy(s["X"]), torch.from_numpy(s["Y"]), torch.from_numpy(s["W"]))


@torch.no_grad()
def _predict(model: nn.Module, X: np.ndarray, bs: int = 1024) -> np.ndarray:
    model.eval()
    out = [model(torch.from_numpy(X[i:i + bs])) for i in range(0, len(X), bs)]
    return torch.cat(out).numpy() if out else np.empty((0, len(cfg.HORIZONS)))


def _fit(conf: dict, data: dict, fit_set: str, epochs: int, early_stop: bool,
         ws: int, rank: int) -> tuple[nn.Module, dict]:
    """Một lượt huấn luyện. early_stop=True → dừng theo loss trên valid."""
    torch.manual_seed(conf["seed"])
    np.random.seed(conf["seed"])
    sets = data["sets"]
    model = build_model(conf, len(data["cols"]), data["q_idx"])
    ds = TensorDataset(*_tensors(sets[fit_set]))
    if ws > 1:
        sampler = DistributedSampler(ds, num_replicas=ws, rank=rank, shuffle=True,
                                     seed=conf["seed"], drop_last=False)
        loader = DataLoader(ds, batch_size=conf["batch_size"], sampler=sampler)
        net: nn.Module = DDP(model)
    else:
        sampler = None
        g = torch.Generator().manual_seed(conf["seed"])
        loader = DataLoader(ds, batch_size=conf["batch_size"], shuffle=True, generator=g)
        net = model
    opt = torch.optim.Adam(net.parameters(), lr=conf["lr"],
                           weight_decay=conf["weight_decay"])
    Xv, Yv, Wv = _tensors(sets["valid"])
    best, best_ep, bad, best_state, ep = np.inf, epochs, 0, None, 0

    for ep in range(1, epochs + 1):
        if sampler is not None:
            sampler.set_epoch(ep)
        net.train()
        for xb, yb, wb in loader:
            opt.zero_grad()
            loss = weighted_mse(net(xb), yb, wb)
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
        if early_stop:
            # Mọi rank tính trên toàn bộ valid với tham số đã đồng bộ → cùng quyết định.
            with torch.no_grad():
                model.eval()
                vl = float(weighted_mse(model(Xv), Yv, Wv))
            if vl < best - 1e-6:
                best, best_ep, bad = vl, ep, 0
                best_state = copy.deepcopy(model.state_dict())
            else:
                bad += 1
                if bad >= conf["patience"]:
                    break
    if early_stop and best_state is not None:
        model.load_state_dict(best_state)
    return model, {"best_epoch": best_ep, "stopped_epoch": ep,
                   "valid_loss": best if early_stop else np.nan}


def _to_q(pred_std: np.ndarray, data: dict) -> np.ndarray:
    """Đầu ra chuẩn hoá → m³/s (âm vô nghĩa nên kẹp về 0)."""
    return np.clip(np.expm1(pred_std * data["y_sd"] + data["y_mu"]), 0, None)


def evaluate(y: np.ndarray, yhat: np.ndarray, thr: float) -> list[dict]:
    """Chỉ số hồi quy + sự kiện (Q ≥ ngưỡng mức 1) cho từng horizon."""
    rows = []
    for j, h in enumerate(cfg.HORIZONS):
        ok = np.isfinite(y[:, j])
        yt, yp = y[ok, j], yhat[ok, j]
        rep = metrics.regression_report(yt, yp)
        ev = metrics.event_report(yt >= thr, yp >= thr)
        rows.append({"horizon": h, **rep,
                     **{k: ev[k] for k in ("POD", "FAR", "CSI", "hits", "misses",
                                           "false_alarms", "n_positive")}})
    return rows


def train(config: dict) -> dict:
    """Huấn luyện + đánh giá một cấu hình. Hàm thuần, chạy được trong TorchDistributor.

    Trả về dict (rank 0): chỉ số valid/test, epoch tốt nhất, dự báo test (m³/s).
    """
    conf = {**DEFAULTS, **config}
    t0 = time.perf_counter()
    torch.set_num_threads(int(conf["num_threads"]))
    ws, rank, created = _dist_env()
    try:
        data = prepare(pl.read_parquet(conf["panel_path"]), conf)
        sets, thr = data["sets"], data["thr"]

        model, info = _fit(conf, data, "train", conf["max_epochs"], True, ws, rank)
        results = [{"fit": "train", "split": "valid", **r}
                   for r in evaluate(sets["valid"]["Yraw"],
                                     _to_q(_predict(model, sets["valid"]["X"]), data), thr)]
        pred = {"train": _to_q(_predict(model, sets["test"]["X"]), data)}
        results += [{"fit": "train", "split": "test", **r}
                    for r in evaluate(sets["test"]["Yraw"], pred["train"], thr)]

        if conf["refit"]:
            # Học lại trên train+valid đúng số epoch tốt nhất — cùng dữ liệu với LightGBM.
            model, _ = _fit(conf, data, "trval", info["best_epoch"], False, ws, rank)
            pred["train+valid"] = _to_q(_predict(model, sets["test"]["X"]), data)
            results += [{"fit": "train+valid", "split": "test", **r}
                        for r in evaluate(sets["test"]["Yraw"], pred["train+valid"], thr)]
    finally:
        if created:
            dist.destroy_process_group()

    if rank != 0:
        return {"rank": rank}
    return {
        "name": conf["name"], "seed": conf["seed"], "rank": rank, "world_size": ws,
        "config": {k: v for k, v in conf.items() if k != "panel_path"},
        **info, "threshold": thr, "results": results,
        "n_train": len(sets["train"]["X"]), "n_valid": len(sets["valid"]["X"]),
        "n_trval": len(sets["trval"]["X"]), "n_test": len(sets["test"]["X"]),
        "n_params": int(sum(p.numel() for p in model.parameters())),
        "test_dates": sets["test"]["date"], "y_test": sets["test"]["Yraw"], "pred": pred,
        "time_s": time.perf_counter() - t0,
    }


def _ddp_worker(rank: int, world_size: int, config: dict, port: int, out: str) -> None:
    """Một tiến trình DDP: đặt biến môi trường như torchrun/TorchDistributor rồi gọi train()."""
    import pickle

    os.environ.update({"MASTER_ADDR": "127.0.0.1", "MASTER_PORT": str(port),
                       "RANK": str(rank), "LOCAL_RANK": str(rank),
                       "WORLD_SIZE": str(world_size)})
    if sys.platform == "win32":
        os.environ.setdefault("USE_LIBUV", "0")   # TCPStore trên Windows
    res = train(config)
    if rank == 0:
        with open(out, "wb") as f:
            pickle.dump(res, f)


def run_local_ddp(config: dict, world_size: int = 2) -> dict:
    """Giả lập TorchDistributor(local_mode=True) trên một máy: N tiến trình DDP gloo."""
    import pickle
    import socket
    import tempfile

    import torch.multiprocessing as mp

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "rank0.pkl")
        mp.spawn(_ddp_worker, args=(world_size, config, port, out), nprocs=world_size,
                 join=True)
        with open(out, "rb") as f:
            return pickle.load(f)


# ----------------------------------------------------------------- đối chứng

def reference_models(panel_path: str, thr: float) -> tuple[list[dict], dict]:
    """Chạy lại LightGBM (đúng PARAMS, cột, split của lgbm.py) và persistence.

    Mục đích: (1) kiểm tra pipeline numpy/Polars ở đây cho đúng số của
    `reports/lgbm_results.csv`; (2) tính POD/FAR/CSI của LightGBM **hồi quy** bằng
    cùng cách với DL (Q dự báo ≥ ngưỡng) — số 0,645/0,20/0,556 trong
    `classifier_results.csv` là của bộ phân loại riêng, không cùng loại mô hình.
    """
    import pandas as pd  # bắt buộc: LGBMRegressor bản đã cài lỗi với mảng numpy + sklearn mới
    from lightgbm import LGBMRegressor

    from src.models.lgbm import PARAMS

    df = pl.read_parquet(panel_path).sort("date")
    feats = feature_list(dict(df.schema), "full")
    dates = df["date"].cast(pl.Date).to_numpy()
    X = df.select(feats).cast(pl.Float64).to_numpy()
    q = df["discharge"].to_numpy().astype(float)
    tr, va, te = split_masks(dates, DEFAULTS)
    fit = tr | va
    x_ok = np.isfinite(X).all(axis=1)

    rows, preds = [], {"lightgbm": {}, "persistence": {}}
    for h in cfg.HORIZONS:
        y = df[f"target_h{h}"].cast(pl.Float64).to_numpy()
        a = fit & x_ok & np.isfinite(y)
        b = te & x_ok & np.isfinite(y)
        m = LGBMRegressor(**PARAMS)
        m.fit(pd.DataFrame(X[a], columns=feats), np.log1p(y[a]))
        yhat = np.clip(np.expm1(m.predict(pd.DataFrame(X[b], columns=feats))), 0, None)
        for name, yp in (("lightgbm", yhat), ("persistence", q[b])):
            rep = metrics.regression_report(y[b], yp)
            ev = metrics.event_report(y[b] >= thr, yp >= thr)
            rows.append({"name": name, "fit": "train+valid", "split": "test",
                         "horizon": h, "seed": cfg.SEED, **rep,
                         **{k: ev[k] for k in ("POD", "FAR", "CSI", "hits", "misses",
                                               "false_alarms", "n_positive")}})
            preds[name][h] = (dates[b], yp)
    return rows, preds


# ----------------------------------------------------------------- tổng hợp

AGG_COLS = ["NSE", "KGE", "RMSE", "MAE", "peak_bias", "POD", "FAR", "CSI"]


def aggregate(long: pl.DataFrame) -> pl.DataFrame:
    """Trung bình ± độ lệch chuẩn mẫu (ddof=1) qua các seed."""
    exprs = [pl.len().alias("n_seeds"), pl.col("n").first().alias("n"),
             pl.col("n_positive").first().alias("n_positive")]
    for c in AGG_COLS:
        exprs += [pl.col(c).fill_nan(None).mean().alias(f"{c}_mean"),
                  pl.col(c).fill_nan(None).std(ddof=1).alias(f"{c}_std")]
    exprs += [pl.col("best_epoch").mean().alias("best_epoch_mean"),
              pl.col("time_s").mean().alias("time_s_mean"),
              pl.col("NSE").round(3).cast(pl.Utf8).str.join(";").alias("NSE_seeds")]
    return (long.group_by(["name", "fit", "split", "horizon"], maintain_order=True)
            .agg(exprs).sort(["split", "fit", "name", "horizon"]))


LABELS = {
    "lstm_L14_mse": "LSTM L=14, MSE", "lstm_L30_mse": "LSTM L=30, MSE",
    "lstm_L14_peak": "LSTM L=14, peak-weighted", "lstm_L30_peak": "LSTM L=30, peak-weighted",
    "lstm_L30_mse_noresid": "LSTM L=30, MSE, no residual",
    "lstm_L14_full_mse": "LSTM L=14, all panel columns",
    "mlp_lag_mse": "MLP on lag columns, MSE", "mlp_lag_peak": "MLP on lag columns, peak-weighted",
}
# Màu theo bảng categorical cố định (dataviz palette), gán theo thực thể, không theo hạng.
C_LSTM, C_LGBM, C_MLP, C_PEAK, C_CLS = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
C_INK, C_INK2, C_GRID, C_SURF, C_PERS = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#8a8984"


def plot(agg: pl.DataFrame, best: str, runs: list[dict], ref_pred: dict,
         thr: float, out=OUT_FIG) -> None:
    """Hình tổng hợp: NSE mọi cấu hình theo horizon; peak_bias; POD/FAR/CSI h=1; thủy đồ."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    test = agg.filter((pl.col("split") == "test") & (pl.col("fit") == "train+valid"))

    def val(name, h, col="NSE"):
        d = test.filter((pl.col("name") == name) & (pl.col("horizon") == h))
        return (d[f"{col}_mean"][0], d[f"{col}_std"].fill_null(0)[0]) if d.height else (None, 0)

    def style(ax, title):
        ax.set_title(title, loc="left", fontsize=10.5, color=C_INK)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(colors=C_INK2, labelsize=9)

    fig = plt.figure(figsize=(15, 12.5), facecolor=C_SURF)
    gs = fig.add_gridspec(3, 6, height_ratios=[1.1, 1, 1], hspace=0.5, wspace=0.9, top=0.9)

    # Hàng 1 — NSE từng cấu hình DL, mỗi horizon một ô; vạch dọc = LightGBM.
    names = [n for n in LABELS if test.filter(pl.col("name") == n).height]
    ylab = [LABELS[n] + (" (best on valid)" if n == best else "") for n in names]
    for i, h in enumerate(cfg.HORIZONS):
        ax = fig.add_subplot(gs[0, 2 * i:2 * i + 2])
        for k, n in enumerate(names):
            m, sd = val(n, h)
            ax.errorbar(m, k, xerr=sd, fmt="o", ms=7, capsize=3, lw=1.5,
                        color=C_MLP if n.startswith("mlp") else C_LSTM)
        lg, _ = val("lightgbm", h)
        ax.axvline(lg, color=C_LGBM, lw=2)
        ax.annotate(f"LightGBM {lg:.3f}", (lg, -0.6), xytext=(4, 0),
                    textcoords="offset points", color=C_INK2, fontsize=8.5, va="center")
        ax.set_yticks(range(len(names)), ylab if i == 0 else [""] * len(names))
        ax.set_ylim(len(names) - 0.4, -0.9)
        ax.grid(axis="x", color=C_GRID, lw=0.8)
        pers, _ = val("persistence", h)
        style(ax, f"NSE on test, h = {h} d  (persistence {pers:.2f})")

    # Hàng 2 trái — peak_bias theo horizon.
    ax_p = fig.add_subplot(gs[1, 0:3])
    lines = [("persistence", "Persistence", C_PERS, "--"),
             ("lightgbm", "LightGBM regressor", C_LGBM, "-"),
             ("mlp_lag_mse", LABELS["mlp_lag_mse"], C_MLP, "-"),
             ("lstm_L30_mse", LABELS["lstm_L30_mse"], C_LSTM, "-"),
             ("lstm_L30_peak", LABELS["lstm_L30_peak"], C_PEAK, "-")]
    for j, (n, lab, color, ls) in enumerate(lines):
        pts = [val(n, h, "peak_bias") for h in cfg.HORIZONS]
        if pts[0][0] is None:
            continue
        ax_p.errorbar(np.array(cfg.HORIZONS) + (j - 2) * 0.05, [p[0] for p in pts],
                      yerr=[p[1] for p in pts], color=color, ls=ls, lw=2, marker="o",
                      ms=7, capsize=3, label=lab)
    ax_p.axhline(0, color=C_INK2, lw=0.8)
    ax_p.set_xticks(cfg.HORIZONS, [f"h = {h} d" for h in cfg.HORIZONS])
    ax_p.grid(axis="y", color=C_GRID, lw=0.8)
    ax_p.legend(frameon=False, fontsize=8.5, loc="upper right")
    style(ax_p, "Peak bias on test, top 1 % flows (0 = unbiased, < 0 = peaks cut)")

    # Hàng 2 phải — POD / FAR / CSI mức nguy cơ 1, h = 1.
    ax_e = fig.add_subplot(gs[1, 3:6])
    bars = [("Persistence", C_PERS, "persistence"), ("LightGBM regressor", C_LGBM, "lightgbm"),
            ("LightGBM classifier (classifier.py)", C_CLS, None),
            (LABELS["lstm_L30_mse"], C_LSTM, "lstm_L30_mse"),
            (LABELS["lstm_L30_peak"], C_PEAK, "lstm_L30_peak")]
    cls = {}
    if LGBM_CLS.exists():
        c = pl.read_csv(LGBM_CLS).filter((pl.col("muc") == "nguy_co_1") & (pl.col("horizon") == 1))
        cls = {m: (c[m][0], 0) for m in ("POD", "FAR", "CSI")} if c.height else {}
    w = 0.8 / len(bars)
    for i, (lab, color, n) in enumerate(bars):
        v = cls if n is None else {m: val(n, 1, m) for m in ("POD", "FAR", "CSI")}
        if not v or v["POD"][0] is None:
            continue
        x = np.arange(3) + (i - (len(bars) - 1) / 2) * w
        ax_e.bar(x, [np.nan if v[m][0] is None else v[m][0] for m in ("POD", "FAR", "CSI")],
                 w, yerr=[v[m][1] for m in ("POD", "FAR", "CSI")] if n and n.startswith(("lstm", "mlp")) else None, color=color,
                 edgecolor=C_SURF, linewidth=1.5, capsize=2,
                 error_kw={"lw": 1, "ecolor": C_INK2}, label=lab)
    ax_e.set_xticks(range(3), ["POD (higher better)", "FAR (lower better)",
                               "CSI (higher better)"])
    ax_e.set_ylim(0, 1)
    ax_e.grid(axis="y", color=C_GRID, lw=0.8)
    ax_e.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    n_pos = test.filter((pl.col("name") == "lightgbm") & (pl.col("horizon") == 1))["n_positive"]
    style(ax_e, f"Risk level 1 (Q >= {thr:.0f} m³/s), h = 1 d, test: "
                f"{int(n_pos[0]) if n_pos.len() else '?'} event days")

    # Hàng 3 — thủy đồ h = 1 quanh đỉnh lớn nhất của test (x = ngày được dự báo).
    ax_h = fig.add_subplot(gs[2, :])
    by = {n: [r for r in runs if r["name"] == n] for n in ("lstm_L30_mse", "lstm_L30_peak")}
    ref = by["lstm_L30_mse"] or [r for r in runs if r["name"] == best]
    dts, y = ref[0]["test_dates"], ref[0]["y_test"][:, 0]
    k = int(np.nanargmax(y))
    lo, hi = dts[k] - np.timedelta64(40, "D"), dts[k] + np.timedelta64(40, "D")
    win, one = (dts >= lo) & (dts <= hi), np.timedelta64(1, "D")
    ax_h.plot(dts[win] + one, y[win], color=C_INK, lw=2.4, label="GloFAS (target)")
    d_l, p_l = ref_pred["lightgbm"][1]
    w2 = (d_l >= lo) & (d_l <= hi)
    ax_h.plot(d_l[w2] + one, p_l[w2], color=C_LGBM, lw=2, label="LightGBM regressor")
    for n, color in (("lstm_L30_mse", C_LSTM), ("lstm_L30_peak", C_PEAK)):
        if by[n]:
            p = np.mean([r["pred"]["train+valid"][:, 0] for r in by[n]], axis=0)
            ax_h.plot(dts[win] + one, p[win], color=color, lw=2,
                      label=f"{LABELS[n]} (mean of {len(by[n])} seeds)")
    ax_h.axhline(thr, color=C_INK2, lw=1, ls=":")
    ax_h.annotate(f"risk level 1 = {thr:.0f} m³/s", (dts[win][-1] + one, thr),
                  xytext=(0, 4), textcoords="offset points", ha="right", va="bottom",
                  fontsize=8.5, color=C_INK2)
    ax_h.set_ylabel("Discharge (m³/s)", color=C_INK2)
    ax_h.grid(axis="y", color=C_GRID, lw=0.8)
    ax_h.legend(frameon=False, fontsize=9, loc="upper left")
    style(ax_h, "1-day-ahead forecast around the largest test flood (x = forecast valid date)")

    fig.suptitle("Huong River at Kim Long — deep learning vs LightGBM on the test period "
                 "2022-07 → 2026-08\nAll models fitted on train+valid (≤ 2022-06); "
                 "DL = mean ± sd over seeds 42 / 7 / 2026",
                 x=0.06, y=0.965, ha="left", fontsize=12, color=C_INK)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=C_SURF)
    plt.close(fig)


def _flatten(runs: list[dict]) -> pl.DataFrame:
    rows = []
    for r in runs:
        for x in r["results"]:
            rows.append({"name": r["name"], "seed": r["seed"],
                         "best_epoch": float(r["best_epoch"]), "time_s": r["time_s"], **x})
    return pl.DataFrame(rows)


def _run_all(a: argparse.Namespace) -> list[dict]:
    """Chạy lưới thí nghiệm song song (mỗi tiến trình một lượt train())."""
    from src.models.dl_lstm import train as train_fn  # picklable cho tiến trình con

    exps = [e for e in EXPERIMENTS if not a.only or e["name"] in a.only]
    seeds = SEEDS[:1] if a.quick else SEEDS
    jobs = [{**e, "seed": s, "num_threads": a.threads,
             **({"max_epochs": 3, "patience": 2} if a.quick else {})}
            for e in exps for s in seeds]
    print(f"{len(jobs)} lượt huấn luyện · {a.jobs} tiến trình × {a.threads} luồng")
    t0 = time.perf_counter()
    runs: list[dict] = []
    with ProcessPoolExecutor(max_workers=a.jobs, mp_context=get_context("spawn")) as ex:
        for r in ex.map(train_fn, jobs):
            runs.append(r)
            t = [x for x in r["results"] if x["split"] == "test" and x["fit"] == "train+valid"]
            print(f"  {r['name']:<22} seed {r['seed']:<5} epoch* {r['best_epoch']:>3}  "
                  + "  ".join(f"h{x['horizon']} {x['NSE']:+.3f}" for x in t)
                  + f"   ({r['time_s']:.0f}s)", flush=True)
    print(f"Tổng thời gian huấn luyện DL (wall): {(time.perf_counter() - t0) / 60:.1f} phút")
    return runs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", type=int, default=4, help="số tiến trình chạy song song")
    ap.add_argument("--threads", type=int, default=4, help="torch threads mỗi tiến trình")
    ap.add_argument("--quick", action="store_true", help="chạy thử: 3 epoch, 1 seed")
    ap.add_argument("--only", nargs="*", help="chỉ chạy các cấu hình này")
    ap.add_argument("--ddp", type=int, default=0,
                    help="chạy cấu hình mặc định bằng N tiến trình DDP gloo (dưới torchrun: --ddp 1)")
    ap.add_argument("--save-runs", help="pickle kết quả huấn luyện ra file (để vẽ lại)")
    ap.add_argument("--load-runs", help="bỏ qua huấn luyện, đọc kết quả đã pickle")
    a = ap.parse_args(argv)

    if a.ddp:
        from src.models.dl_lstm import run_local_ddp
        from src.models.dl_lstm import train as train_fn

        conf = {"num_threads": a.threads,
                **({"max_epochs": 3, "patience": 2} if a.quick else {})}
        under_launcher = int(os.environ.get("WORLD_SIZE", "1")) > 1
        res = train_fn(conf) if under_launcher or a.ddp == 1 else run_local_ddp(conf, a.ddp)
        if res.get("rank", 0) == 0:
            print(f"world_size = {res['world_size']}, best_epoch = {res['best_epoch']}")
            for x in res["results"]:
                print(f"  {x['fit']:<12} {x['split']:<6} h{x['horizon']}  NSE {x['NSE']:+.3f}")
        return 0

    import pickle

    if a.load_runs:
        with open(a.load_runs, "rb") as f:
            runs: list[dict] = pickle.load(f)
        print(f"Đọc {len(runs)} lượt huấn luyện từ {a.load_runs}")
    else:
        runs = _run_all(a)
        if a.save_runs:
            with open(a.save_runs, "wb") as f:
                pickle.dump(runs, f)

    thr = runs[0]["threshold"]
    ref_rows, ref_pred = reference_models(DEFAULTS["panel_path"], thr)
    long = pl.concat([_flatten(runs),
                      pl.DataFrame(ref_rows).with_columns(
                          pl.lit(np.nan).alias("best_epoch"), pl.lit(np.nan).alias("time_s"))],
                     how="diagonal_relaxed")
    agg = aggregate(long).with_columns(
        pl.when(pl.col("name").is_in(["lightgbm", "persistence"]))
        .then(pl.lit("reference")).otherwise(pl.lit("dl")).alias("family"),
        pl.lit(round(thr, 1)).alias("risk1_threshold_m3s"))
    num = [c for c, t in agg.schema.items() if t.is_float()]
    agg = agg.with_columns([pl.col(c).round(4) for c in num])

    # Chọn LSTM "tốt nhất" theo NSE trung bình 3 horizon trên VALID (không nhìn test).
    val = (agg.filter((pl.col("split") == "valid") & pl.col("name").str.starts_with("lstm"))
           .group_by("name").agg(pl.col("NSE_mean").mean()).sort("NSE_mean", descending=True))
    best = val["name"][0]
    print("NSE valid trung bình 3 horizon (chọn mô hình):")
    for n, v in val.iter_rows():
        print(f"  {n:<22} {v:.4f}")
    agg = agg.with_columns((pl.col("name") == best).alias("best_lstm_on_valid"))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    agg.rename({"name": "model"}).write_csv(OUT_CSV)
    plot(agg, best, runs, ref_pred, thr)

    show = ["name", "horizon", "n_seeds", "NSE_mean", "NSE_std", "KGE_mean",
            "peak_bias_mean", "POD_mean", "FAR_mean", "CSI_mean"]
    with pl.Config(tbl_rows=100, tbl_cols=20, tbl_width_chars=200):
        print("\nTEST (fit = train+valid):")
        print(agg.filter((pl.col("split") == "test") & (pl.col("fit") == "train+valid"))
              .select(show))
        print("\nVALID (fit = train, early stopping):")
        print(agg.filter(pl.col("split") == "valid").select(show[:6]))
    print(f"\nLSTM chọn theo valid: {best}")
    print(f"→ {OUT_CSV.relative_to(cfg.ROOT)}\n→ {OUT_FIG.relative_to(cfg.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
