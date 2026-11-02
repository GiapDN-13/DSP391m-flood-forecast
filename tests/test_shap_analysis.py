"""Test cho phân tích SHAP (src/eval/shap_analysis.py) — không cần dữ liệu thật.

Khoá: base + Σ SHAP = dự báo thô của mô hình (log1p), hàm gộp nhóm phủ hết mọi
cột của cấu hình E và không đoán bừa cột lạ, gộp nhóm cộng có dấu trước khi lấy
trị tuyệt đối, và phép kiểm chiều vật lý.
"""

import numpy as np
import pandas as pd
import polars as pl
import pytest

from src import config as cfg
from src.eval import shap_analysis as sa
from src.models import ablation_ext as abl


def _feats_e_tu_cong_thuc() -> list[str]:
    """Bộ feature E dựng lại theo `build_panel` — không đọc parquet."""
    rains = ["rain_thuong", "rain_trung", "rain_ha", "rain_basin"]
    base = ["discharge", *rains, *[f"discharge_lag{i}" for i in cfg.Q_LAGS]]
    for r in rains:
        base += [f"{r}_lag{i}" for i in cfg.RAIN_LAGS] + [f"{r}_roll{w}" for w in (3, 5, 7)]
    base += ["api", "q_diff1", "q_diff3", "doy_sin", "doy_cos", "month", "mua_lu"]
    return base + abl.SOIL + abl.RESERVOIR_PROXY + abl.CONTEXT


# ---------------------------------------------------------------- nhóm

def test_nhom_phu_het_cau_hinh_e():
    feats = _feats_e_tu_cong_thuc()
    assert len(feats) == 88                     # khớp n_feat của E trong ablation_ext.csv
    groups = {f: sa.feature_group(f) for f in feats}
    assert set(groups.values()) == set(sa.GROUP_ORDER)   # nhóm nào cũng có thành viên
    assert groups["discharge"] == groups["q_diff1"] == "flow"
    assert groups["rain_basin_roll3"] == "rain"
    assert groups["rain_basin_roll30"] == groups["rain_season_cum"] == "rain_long"
    assert groups["api"] == groups["sm_7_28"] == "soil_api"
    assert groups["storm_approach_km"] == "storm"
    assert groups["mslp_grad_north"] == groups["cloud_hue"] == "synoptic"
    assert groups["oni_lag3"] == "enso"
    assert groups["doy_sin"] == groups["mua_lu"] == "season"
    for p in sa.GROUP_PROXY.values():
        assert p in feats


@pytest.mark.skipif(not sa.PANEL_R2.exists(), reason="chưa có daily_panel.parquet")
def test_nhom_phu_het_cot_that():
    feats = sa.features_e()
    assert feats == _feats_e_tu_cong_thuc()
    for f in feats:
        assert sa.feature_group(f) in sa.GROUP_ORDER


def test_cot_la_bao_loi():
    with pytest.raises(KeyError):
        sa.feature_group("glofas_fc_h1")


def test_gop_nhom_cong_co_dau_truoc():
    feats = ["discharge", "discharge_lag1", "rain_basin"]
    sv = np.array([[+1.0, -1.0, 0.5],
                   [-0.5, +0.5, -0.5]])
    g = sa.group_importance(sv, feats)
    assert g["flow"] == pytest.approx(0.0)       # hai lag triệt tiêu ⇒ nhóm không quan trọng
    assert g["rain"] == pytest.approx(0.5)
    assert g["storm"] == 0.0
    s = sa.group_signed(sv, feats)
    assert s["rain"] == pytest.approx(0.0)


def test_bang_nhom_ti_trong_cong_100():
    rng = np.random.default_rng(0)
    feats = _feats_e_tu_cong_thuc()
    sv = rng.normal(size=(50, len(feats)))
    X = rng.normal(size=(50, len(feats)))
    flood = np.arange(50) < 10
    t = sa.group_table(sv, X, feats, flood)
    assert t.height == len(sa.GROUP_ORDER)
    assert t["share_all_pct"].sum() == pytest.approx(100.0)
    assert t["share_flood_pct"].sum() == pytest.approx(100.0)


# ---------------------------------------------------------------- chiều vật lý

def test_kiem_chieu():
    assert sa.sign_check(+0.8, +1) == "dung"
    assert sa.sign_check(-0.8, +1) == "nguoc"
    assert sa.sign_check(-0.6, -1) == "dung"
    assert sa.sign_check(+0.05, +1) == "yeu"
    assert sa.sign_check(+0.9, 0) == "khong_ky_vong"
    assert sa.sign_check(float("nan"), +1) == "khong_ky_vong"


def test_chieu_ky_vong():
    assert sa.expected_sign("rain_thuong_lag3") == 1
    assert sa.expected_sign("storm_dist_km") == -1       # bão càng gần càng nguy hiểm
    assert sa.expected_sign("oni_lag3") == -1            # La Niña ⇒ mưa nhiều ở miền Trung
    assert sa.expected_sign("mslp_grad_north") == 1      # không khí lạnh tràn về
    assert sa.expected_sign("discharge_lag5") == 0
    assert sa.expected_sign("doy_sin") == 0


# ---------------------------------------------------------------- SHAP cộng lại

@pytest.fixture(scope="module")
def toy():
    """Q(t+1) phụ thuộc Q hôm nay và mưa; học trên log1p như mô hình thật."""
    rng = np.random.default_rng(3)
    n = 800
    X = pd.DataFrame({"discharge": rng.gamma(2.0, 60.0, n),
                      "rain_basin": rng.gamma(0.5, 20.0, n),
                      "storm_dist_km": rng.choice([150.0, 600.0, 2000.0], n)})
    y = 0.7 * X["discharge"] + 6.0 * X["rain_basin"] + rng.normal(0, 5, n)
    return X, np.log1p(y.clip(lower=1).to_numpy())


def test_shap_cong_lai_bang_du_bao(toy):
    from lightgbm import LGBMRegressor

    X, ylog = toy
    params = {**sa.lgbm.PARAMS, "n_estimators": 60}
    model = LGBMRegressor(**params).fit(X, ylog)
    rows = X.iloc[:7]
    sv, base = sa.explain(model, rows)
    assert sv.shape == (7, 3)
    np.testing.assert_allclose(base + sv.sum(axis=1), model.predict(rows), atol=1e-8)
    # mưa nhiều ⇒ SHAP của mưa lớn hơn (mô hình đồ chơi phải học đúng chiều)
    sv_all, _ = sa.explain(model, X)
    assert sa._rho(X["rain_basin"].to_numpy(), sv_all[:, 1]) > 0.5


def test_bang_feature_xep_hang(toy):
    X, _ = toy
    sv = np.column_stack([np.full(len(X), 0.1), np.full(len(X), -0.3), np.zeros(len(X))])
    flood = np.zeros(len(X), bool)
    flood[:5] = True
    t = sa.feature_table(sv, X.to_numpy(), list(X.columns), flood)
    assert t["name"].to_list()[0] == "rain_basin"         # |−0,3| lớn nhất
    assert t.filter(pl.col("name") == "rain_basin")["rank_all"].item() == 1
    assert t["share_all_pct"].sum() == pytest.approx(100.0)
