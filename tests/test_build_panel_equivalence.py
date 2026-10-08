"""Bảng phân tích dựng bằng DuckDB + Polars phải TRÙNG KHỚP bản pandas cũ.

Khi đổi tầng dữ liệu từ pandas sang DuckDB/Polars (10/2026), mọi kết quả mô
hình đã báo cáo đều dựa trên bảng do bản pandas dựng. Test này chốt "dấu vân
tay" của bảng cũ — tổng và số ô thiếu của từng cột — và đòi bản mới khớp.
So bằng dấu vân tay nên test không cần tới pandas.
"""

import json
from pathlib import Path

import polars as pl
import pytest

from src import config as cfg

FP = json.loads((Path(__file__).parent / "fixtures" / "panel_fingerprint.json")
                .read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def panel():
    if not (cfg.DATA_RAW / "rain_daily").exists():
        pytest.skip("chưa có dữ liệu thô — chạy scripts/restore_data.py --all")
    from src.features.build_panel import build
    return build()


def test_cung_kich_thuoc_va_thu_tu_cot(panel):
    assert list(panel.shape) == FP["shape"]
    assert panel.columns == FP["columns"]


def test_cung_khoang_ngay(panel):
    assert str(panel["date"].min())[:10] == FP["date_min"]
    assert str(panel["date"].max())[:10] == FP["date_max"]


def test_tung_cot_khop_tong_va_o_thieu(panel):
    lech = []
    for c, ref in FP["cols"].items():
        s = panel[c].cast(pl.Float64).fill_nan(None)
        if s.null_count() != ref["nulls"]:
            lech.append(f"{c}: thiếu {s.null_count()} vs {ref['nulls']}")
        elif abs(float(s.sum()) - ref["sum"]) > 1e-6 * max(1.0, abs(ref["sum"])):
            lech.append(f"{c}: tổng {s.sum()} vs {ref['sum']}")
    assert not lech, "\n".join(lech)
