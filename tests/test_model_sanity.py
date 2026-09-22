"""Chốt lại hai kết luận dễ bị phá khi sửa code sau này.

1. LightGBM phải thắng persistence ở cả ba horizon — nếu một thay đổi nào đó
   làm nó thua thì phải biết ngay, vì đó là toàn bộ lý do tồn tại của FR-M2.
2. Feature không được chứa cột target — lỗi rò rỉ kinh điển.
"""

import pandas as pd
import pytest

from src import config as cfg

REP = cfg.ROOT / "reports"


def _load(name):
    f = REP / name
    if not f.exists():
        pytest.skip(f"chưa chạy sinh {name}")
    return pd.read_csv(f)


def test_lightgbm_thang_persistence_moi_horizon():
    lg = _load("lgbm_results.csv")
    bs = _load("baseline_results.csv")
    per = bs[bs.model == "persistence"]
    for h in cfg.HORIZONS:
        a = float(lg[lg.horizon == h].NSE.iloc[0])
        b = float(per[per.horizon == h].NSE.iloc[0])
        assert a > b, f"h={h}: LightGBM {a:.3f} không thắng persistence {b:.3f}"


def test_feature_khong_chua_target():
    from src.models.lgbm import feature_cols
    panel = cfg.ROOT / "data" / "processed" / "daily_panel.parquet"
    if not panel.exists():
        pytest.skip("chưa có panel")
    d = pd.read_parquet(panel)
    feats = feature_cols(d)
    assert not [c for c in feats if c.startswith("target_")]
    assert "alert_level" not in feats
    assert "date" not in feats


def test_peak_bias_van_am_thi_phai_duoc_bao_cao():
    """Không phải test đúng/sai — là chốt rằng cột peak_bias luôn có mặt.

    Chỉ đưa NSE mà giấu peak_bias là che đúng điểm yếu quan trọng nhất
    (docs/FINDINGS_MODEL.md §2).
    """
    for name in ("lgbm_results.csv", "baseline_results.csv"):
        assert "peak_bias" in _load(name).columns, name
