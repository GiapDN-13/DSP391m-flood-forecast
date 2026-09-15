"""Bộ chỉ số đánh giá (FR-V2, FR-V3).

Tách riêng khỏi code mô hình để mọi baseline và mọi mô hình đều được chấm bằng
đúng một thước đo — tránh chuyện mỗi chỗ tính RMSE một kiểu rồi so nhầm.

⚠️ **Accuracy bị cấm** trong dự án này: ngày vượt báo động chỉ chiếm 1–3 %, nên
đoán "không bao giờ lũ" đã đạt ~98 %. Xem `docs/RESEARCH_DESIGN.md` §3.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clean_pair(y: np.ndarray, yhat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype=float)
    yhat = np.asarray(yhat, dtype=float)
    ok = np.isfinite(y) & np.isfinite(yhat)
    return y[ok], yhat[ok]


# ------------------------------------------------------------ hồi quy

def rmse(y, yhat) -> float:
    y, yhat = _clean_pair(y, yhat)
    return float(np.sqrt(np.mean((y - yhat) ** 2))) if len(y) else np.nan


def mae(y, yhat) -> float:
    y, yhat = _clean_pair(y, yhat)
    return float(np.mean(np.abs(y - yhat))) if len(y) else np.nan


def nse(y, yhat) -> float:
    """Nash–Sutcliffe Efficiency.

    NSE = 1 là hoàn hảo; NSE = 0 nghĩa là mô hình chỉ ngang với việc đoán bằng
    giá trị trung bình; NSE < 0 là tệ hơn cả đoán trung bình.
    Ngưỡng "chấp nhận được" thường dùng trong thuỷ văn là 0,5 (xem `AC-1`).
    """
    y, yhat = _clean_pair(y, yhat)
    if len(y) < 2:
        return np.nan
    denom = np.sum((y - np.mean(y)) ** 2)
    return float(1 - np.sum((y - yhat) ** 2) / denom) if denom > 0 else np.nan


def kge(y, yhat) -> float:
    """Kling–Gupta Efficiency: tách riêng sai số tương quan, biên độ và trung bình.

    Bổ sung cho NSE vì NSE phạt rất nặng việc lệch đỉnh, dễ che mất chuyện mô
    hình thật ra nắm đúng dạng chuỗi.
    """
    y, yhat = _clean_pair(y, yhat)
    if len(y) < 2 or np.std(y) == 0 or np.std(yhat) == 0:
        return np.nan
    r = float(np.corrcoef(y, yhat)[0, 1])
    alpha = float(np.std(yhat) / np.std(y))
    beta = float(np.mean(yhat) / np.mean(y)) if np.mean(y) != 0 else np.nan
    return float(1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2))


def peak_bias(y, yhat, q: float = 0.99) -> float:
    """Sai lệch tương đối ở vùng đỉnh — mô hình có bị 'cắt ngọn' đỉnh lũ không.

    Giá trị âm = dự báo thấp hơn thực tế ở vùng đỉnh, đúng thứ nguy hiểm nhất
    với bài toán cảnh báo lũ.
    """
    y, yhat = _clean_pair(y, yhat)
    if len(y) < 10:
        return np.nan
    thr = np.quantile(y, q)
    m = y >= thr
    return float((np.mean(yhat[m]) - np.mean(y[m])) / np.mean(y[m])) if m.sum() else np.nan


def regression_report(y, yhat) -> dict[str, float]:
    return {"RMSE": rmse(y, yhat), "MAE": mae(y, yhat),
            "NSE": nse(y, yhat), "KGE": kge(y, yhat),
            "peak_bias": peak_bias(y, yhat), "n": int(len(_clean_pair(y, yhat)[0]))}


# ------------------------------------------------- sự kiện hiếm (FR-V3)

def contingency(y_true, y_pred) -> dict[str, int]:
    """Bảng 2×2 chuẩn của ngành khí tượng thuỷ văn."""
    y_true = np.asarray(y_true).astype(bool)
    y_pred = np.asarray(y_pred).astype(bool)
    return {"hits": int(np.sum(y_true & y_pred)),
            "misses": int(np.sum(y_true & ~y_pred)),
            "false_alarms": int(np.sum(~y_true & y_pred)),
            "correct_negatives": int(np.sum(~y_true & ~y_pred))}


def event_report(y_true, y_pred) -> dict[str, float]:
    """POD · FAR · CSI · F1 — KHÔNG có accuracy, theo đúng chủ ý."""
    c = contingency(y_true, y_pred)
    h, m, f = c["hits"], c["misses"], c["false_alarms"]
    pod = h / (h + m) if (h + m) else np.nan          # bắt được bao nhiêu % đợt lũ thật
    far = f / (h + f) if (h + f) else np.nan          # báo động nhầm bao nhiêu
    csi = h / (h + m + f) if (h + m + f) else np.nan  # chỉ số tổng hợp
    prec = 1 - far if np.isfinite(far) else np.nan
    f1 = 2 * prec * pod / (prec + pod) if np.isfinite(prec) and (prec + pod) else np.nan
    return {**c, "POD": pod, "FAR": far, "CSI": csi, "F1": f1,
            "n_positive": h + m}


def warn_small_sample(n_positive: int, nguong: int = 30) -> str | None:
    """Quy tắc 30 mẫu — `docs/RESEARCH_DESIGN.md` §3.4."""
    if n_positive < nguong:
        return (f"⚠️ Chỉ có {n_positive} ngày dương (< {nguong}). Mọi chỉ số ở đây "
                f"phải kèm số mẫu và KHÔNG được dùng làm kết luận chính.")
    return None


def summary_table(results: dict[str, dict]) -> pd.DataFrame:
    """Gộp nhiều mô hình thành một bảng, sắp theo RMSE tăng dần."""
    df = pd.DataFrame(results).T
    if "RMSE" in df:
        df = df.sort_values("RMSE")
    return df
