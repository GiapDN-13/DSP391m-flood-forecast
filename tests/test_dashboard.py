"""Kiểm hàm đọc dữ liệu của dashboard (dashboard/data.py) + chạy thử app.

Phần hàm thuần chỉ cần pandas. Phần chạy app (AppTest) tự bỏ qua nếu máy
không có streamlit/plotly.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from dashboard import data as dd

ROOT = Path(__file__).resolve().parents[1]

HEADER_OLD = ("run_date,point,lat,lon,target_date,glofas_discharge,rain_forecast,"
              "temp_forecast,sea_level_max,horizon_days,alert_glofas\n")


def _write_run(folder: Path, run: str, qs: list[float], extra: dict | None = None,
               name: str | None = None) -> Path:
    """Ghi một bản phát giả: horizon 0..len(qs)-1."""
    rd = pd.Timestamp(run)
    df = pd.DataFrame({
        "run_date": run, "point": "huong_kim_long", "lat": 16.45, "lon": 107.5,
        "target_date": [(rd + pd.Timedelta(days=h)).strftime("%Y-%m-%d")
                        for h in range(len(qs))],
        "glofas_discharge": qs, "horizon_days": list(range(len(qs))),
        "alert_glofas": "chua_co_nguong",
    })
    for k, v in (extra or {}).items():
        df[k] = v
    p = folder / (name or f"{run}.csv")
    df.to_csv(p, index=False)
    return p


# ---------------------------------------------------------------- chọn bản phát
def test_list_runs_bo_ban_muon_va_latest(tmp_path):
    _write_run(tmp_path, "2026-09-19", [10, 20])
    _write_run(tmp_path, "2026-09-19", [11, 21], name="2026-09-19_chu-ky-muon-2358Z.csv")
    _write_run(tmp_path, "2026-09-21", [10, 20])
    _write_run(tmp_path, "2026-09-21", [10, 20], name="_latest.csv")
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    runs = dd.list_runs(tmp_path)
    assert runs == [date(2026, 9, 19), date(2026, 9, 21)]
    assert dd.latest_run(runs) == date(2026, 9, 21)


def test_list_runs_thu_muc_rong_hoac_thieu(tmp_path):
    assert dd.list_runs(tmp_path) == []
    assert dd.list_runs(tmp_path / "khong_co") == []
    assert dd.latest_run([]) is None


# ---------------------------------------------------------------- cột thiếu
def test_ban_phat_cu_khong_co_cot_ho_va_mo_hinh(tmp_path):
    p = tmp_path / "2026-10-15.csv"
    p.write_text(HEADER_OLD
                 + "2026-10-15,huong_kim_long,16.45,107.5,2026-10-15,119.5,0,25.8,1.0,0,x\n"
                 + "2026-10-15,huong_kim_long,16.45,107.5,2026-10-16,79.2,0,25.6,1.0,1,x\n",
                 encoding="utf-8")
    df = dd.load_run(date(2026, 10, 15), tmp_path)
    for c in (*dd.MODEL_COLS, "glofas_san_ho", "q_release_upstream"):
        assert c in df.columns
    assert df["lgbm_q"].isna().all()
    assert not dd.has_model(df)
    assert df["target_date"].dtype.kind == "M"


def test_has_model_khi_co_so_lgbm(tmp_path):
    _write_run(tmp_path, "2026-11-10", [50, 60, 70, 80],
               extra={"lgbm_q": [55, 65, 75, 85], "p_level1": [0.01, 0.02, 0.1, 0.2]})
    df = dd.load_run(date(2026, 11, 10), tmp_path)
    assert dd.has_model(df)
    # Cột có tên nhưng toàn rỗng thì coi như chưa có mô hình.
    df2 = df.assign(lgbm_q=float("nan"))
    assert not dd.has_model(df2)


def test_loc_dung_diem_kim_long(tmp_path):
    p = _write_run(tmp_path, "2026-09-15", [10, 20])
    extra = pd.read_csv(p).assign(point="bo_phu_oc", glofas_discharge=999)
    pd.concat([pd.read_csv(p), extra]).to_csv(p, index=False)
    df = dd.load_run(date(2026, 9, 15), tmp_path)
    assert set(df["point"]) == {"huong_kim_long"}
    assert df["glofas_discharge"].max() == 20


# ---------------------------------------------------------------- mức nguy cơ
THR = {1: 806.0, 2: 1275.4, 3: 1905.3}


@pytest.mark.parametrize("q, lv", [
    (0.0, 0), (805.9, 0), (806.0, 1), (1275.3, 1), (1275.4, 2),
    (1905.3, 3), (5000, 3), (float("nan"), -1), (None, -1),
])
def test_classify(q, lv):
    assert dd.classify(q, THR) == lv


def test_nhan_muc_co_chu_khong_chi_mau():
    for lv in (-1, 0, 1, 2, 3):
        lab = dd.level_label(lv)
        assert dd.LEVEL_TEXT[lv] in lab
    assert "BĐ" not in "".join(dd.LEVEL_TEXT.values())


def test_doc_nguong_tu_file_that():
    thr, from_file = dd.load_risk_levels()
    assert from_file
    assert thr[1] < thr[2] < thr[3]
    assert thr[1] == pytest.approx(806.0)


def test_nguong_du_phong_khi_thieu_file(tmp_path):
    thr, from_file = dd.load_risk_levels(tmp_path / "khong_co.csv")
    assert not from_file
    assert thr == dd.FALLBACK_LEVELS


# ---------------------------------------------------------------- bảng 3 ngày
def test_forecast_table_chi_glofas(tmp_path):
    _write_run(tmp_path, "2026-10-28", [30, 900, 1300, 2000, 50])
    df = dd.load_run(date(2026, 10, 28), tmp_path)
    t = dd.forecast_table(df, THR)
    assert list(t["horizon"]) == [1, 2, 3]
    assert list(t["level"]) == [1, 2, 3]
    assert set(t["nguon_xep_muc"]) == {"GloFAS thô"}


def test_forecast_table_uu_tien_mo_hinh_va_san_ho(tmp_path):
    _write_run(tmp_path, "2026-11-10", [50, 60, 70, 80],
               extra={"glofas_san_ho": [50, 60, 70, 80],
                      "lgbm_q": [55, 900, 75, 85],
                      "lgbm_san_ho": [55, 900, float("nan"), 85]})
    t = dd.forecast_table(dd.load_run(date(2026, 11, 10), tmp_path), THR)
    h1 = t[t.horizon == 1].iloc[0]
    assert h1["nguon_xep_muc"] == "LightGBM (sàn hồ)"
    assert h1["q_xep_muc"] == 900 and h1["level"] == 1
    # sàn hồ của mô hình rỗng ở h2 → lùi về số LightGBM, không về GloFAS
    h2 = t[t.horizon == 2].iloc[0]
    assert h2["nguon_xep_muc"] == "LightGBM"
    assert h2["q_xep_muc"] == 75 and h2["level"] == 0


def test_forecast_table_lui_ve_lgbm_khi_san_ho_rong(tmp_path):
    _write_run(tmp_path, "2026-11-10", [50, 60, 70, 80],
               extra={"lgbm_q": [55, 65, 75, 85],
                      "lgbm_san_ho": [float("nan")] * 4})
    t = dd.forecast_table(dd.load_run(date(2026, 11, 10), tmp_path), THR)
    assert set(t["nguon_xep_muc"]) == {"LightGBM"}


def test_forecast_table_thieu_horizon(tmp_path):
    _write_run(tmp_path, "2026-11-10", [50])   # chỉ có h0
    t = dd.forecast_table(dd.load_run(date(2026, 11, 10), tmp_path), THR)
    assert t.empty


# ---------------------------------------------------------------- lịch sử
def test_history_tu_horizon0_cac_ban_phat(tmp_path):
    for i, d in enumerate(["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-05"]):
        _write_run(tmp_path, d, [100 + i, 999])
    h = dd.history_from_logs(date(2026, 10, 3), days=30, log_dir=tmp_path)
    assert list(h["date"].dt.strftime("%Y-%m-%d")) == ["2026-10-01", "2026-10-02", "2026-10-03"]
    assert list(h["discharge"]) == [100, 101, 102]     # không lẫn horizon 1 (999)
    h2 = dd.history_from_logs(date(2026, 10, 5), days=2, log_dir=tmp_path)
    assert list(h2["date"].dt.day) == [3, 5]


def test_history_rong_khi_khong_co_file(tmp_path):
    assert dd.history_from_logs(date(2026, 10, 3), log_dir=tmp_path).empty
    assert dd.history_from_panel(date(2026, 10, 3), path=tmp_path / "x.parquet").empty


# ---------------------------------------------------------------- SHAP, lưu vực
def test_shap_groups_tu_file_that():
    sg = dd.load_shap_groups()
    assert set(sg["horizon"]) == {1, 2, 3}
    assert len(sg) == 8 * 3
    for hz, s in sg.groupby("horizon")["share"]:
        assert s.sum() == pytest.approx(100, abs=1.0)
    assert ((sg["lo"] <= sg["share"]) & (sg["share"] <= sg["hi"])).all()
    flow_h1 = sg[(sg.group == "flow") & (sg.horizon == 1)]["share"].item()
    assert flow_h1 > 50
    assert sg["nhom"].isin(dd.SHAP_GROUP_LABELS.values()).all()
    assert not dd.load_shap_groups(basis="flood").empty


def test_subbasins_du_5_va_co_id():
    gj = dd.load_subbasins()
    assert gj is not None
    ids = [f["id"] for f in gj["features"]]
    assert sorted(ids) == sorted(dd.SUBBASIN_LABELS)
    fr = dd.subbasin_frame(gj, 2)
    assert len(fr) == 5 and set(fr["muc"]) == {dd.level_label(2)}
    assert fr["dien_tich_km2"].sum() == pytest.approx(1543, abs=5)


def test_subbasins_thieu_file(tmp_path):
    assert dd.load_subbasins(tmp_path / "x.geojson") is None
    bad = tmp_path / "bad.geojson"
    bad.write_text("{khong phai json", encoding="utf-8")
    assert dd.load_subbasins(bad) is None
    ok = tmp_path / "ok.geojson"
    ok.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    assert dd.load_subbasins(ok)["features"] == []


# ---------------------------------------------------------------- chạy thử app
def test_app_chay_khong_loi():
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.tabs) == 3
    # Đổi sang bản phát cũ nhất (chưa có cột hồ) và tập "ngày lũ" — vẫn không lỗi.
    at.selectbox[0].set_value(dd.list_runs()[0]).run()
    at.radio[-1].set_value("flood").run()
    assert not at.exception, [e.value for e in at.exception]


def _app(monkeypatch, log_dir: Path):
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv(dd.ENV_LOG_DIR, str(log_dir))
    st.cache_data.clear()      # cache dùng chung trong tiến trình giữa các AppTest
    at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=60).run()
    return at


def test_app_hien_cot_mo_hinh_khi_co(monkeypatch, tmp_path):
    for i, d in enumerate(["2030-01-01", "2030-01-02"]):
        _write_run(tmp_path, d, [100 + i, 700, 1300, 2100],
                   extra={"glofas_san_ho": [100 + i, 700, 1300, 2100],
                          "lgbm_q": [110, 900, 1400, 1500],
                          "lgbm_san_ho": [110, 900, 1400, 1500],
                          "p_level1": [0.0, 0.6, 0.9, 0.95],
                          "alert_lgbm": ["binh_thuong", "nguy_co_1", "nguy_co_2",
                                         "nguy_co_1"]})
    at = _app(monkeypatch, tmp_path)
    assert not at.exception, [e.value for e in at.exception]
    assert not at.info or all("chưa có cột mô hình" not in i.value for i in at.info)
    bang = at.dataframe[0].value
    assert "LightGBM (m³/s)" in bang.columns and "P(≥ mức 1)" in bang.columns
    # Xếp mức theo LightGBM sàn hồ (900 / 1400 / 1500), không theo GloFAS (… / 2100).
    assert list(bang["Mức nguy cơ"]) == [dd.level_label(1), dd.level_label(2),
                                         dd.level_label(2)]
    assert set(bang["Xếp mức theo"]) == {"LightGBM (sàn hồ)"}


def test_app_bao_loi_ro_khi_khong_co_ban_phat(monkeypatch, tmp_path):
    at = _app(monkeypatch, tmp_path)
    assert not at.exception
    assert any("Không tìm thấy bản phát" in e.value for e in at.error)
