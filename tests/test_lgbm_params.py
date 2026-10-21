"""Tham số mô hình chính theo horizon (``lgbm.params_for``): L1 ở h=1, L2 ở h=2–3,
không làm bẩn ``lgbm.PARAMS`` gốc (Report 2, mốc r2, bộ phân loại dùng nó)."""

from __future__ import annotations

import pytest

from src.models import lgbm


def test_objective_theo_horizon():
    assert lgbm.MAIN_OBJECTIVE == {1: "regression_l1", 2: "regression", 3: "regression"}
    for h, obj in lgbm.MAIN_OBJECTIVE.items():
        assert lgbm.params_for(h)["objective"] == obj


def test_params_goc_khong_doi():
    goc = dict(lgbm.PARAMS)
    p = lgbm.params_for(2, random_state=7, n_jobs=2)
    p["num_leaves"] = 999
    assert lgbm.PARAMS == goc
    assert lgbm.PARAMS["objective"] == "regression_l1"


def test_ghi_de_va_giu_tham_so_khac():
    p = lgbm.params_for(3, random_state=7, objective="huber")
    assert p["random_state"] == 7 and p["objective"] == "huber"
    for k in ("n_estimators", "learning_rate", "num_leaves", "min_child_samples"):
        assert p[k] == lgbm.PARAMS[k]


def test_doc_params_luc_goi(monkeypatch):
    monkeypatch.setitem(lgbm.PARAMS, "n_jobs", 3)       # như walk_forward_sat --n-jobs
    assert lgbm.params_for(1)["n_jobs"] == 3


def test_horizon_la_bao_loi():
    with pytest.raises(ValueError):
        lgbm.params_for(4)
