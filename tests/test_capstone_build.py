"""Bộ build tài liệu Capstone (reports/capstone/build_report.py): chú thích và số mục."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cap():
    pytest.importorskip("reportlab")      # CI không cài reportlab (chỉ dùng để build báo cáo)
    spec = importlib.util.spec_from_file_location("capstone_build_t",
                                                  ROOT / "reports" / "capstone" / "build_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_chu_thich_in_hoa_thanh_cau_thuong(cap):
    cap.CASE.clear()
    cap.CASE.update({"nse": "NSE", "lightgbm": "LightGBM"})
    got = cap.sentence('<font face="Symbol">&#916;</font>NSE OF LIGHTGBM AT h = 1, CONFIG. A')
    assert got == '<font face="Symbol">&#916;</font>NSE of LightGBM at h = 1, config. A'
    assert cap.sentence("Already sentence case") == "Already sentence case"


def test_tham_chieu_muc_cu_doi_so_moi(cap):
    secs = [(cap.Mark(1, "V", "Results"), []), (cap.Mark(2, "V-A", "x"), []),
            (cap.Mark(2, "V-B", "y"), []), (cap.Mark(1, "VII", "Peak"), [])]
    m = cap.refmap_from(secs)
    assert m == {"V": "5.1", "V-A": "5.1.1", "V-B": "5.1.2", "VII": "5.3"}
    t = "see Sections V-A and V-B; Section VII tests"
    assert cap.SEC_REF.sub(lambda g: g.group(1) + cap.LABEL.sub(
        lambda n: m.get(n.group(0), n.group(0)), g.group(2)), t) == \
        "see Sections 5.1.1 and 5.1.2; Section 5.3 tests"
