"""Hồ chứa thượng nguồn — dữ liệu xả và luật xử lý (Report 3).

Bốn hồ lớn quanh Huế, nhưng chỉ hai hồ nằm TRÊN dòng chảy tới ô lưới của ta
(16.45, 107.50 ≈ Kim Long, lưu vực sông Hương tới Kim Long ~1 540 km²):

* **Tả Trạch** — trên sông Tả Trạch (nhánh chính sông Hương)   → ảnh hưởng
* **Bình Điền** — trên sông Hữu Trạch (nhánh sông Hương)        → ảnh hưởng
* **Hương Điền** — trên sông Bồ                                 → KHÔNG
* **A Lưới** — nước qua tuabin sang thượng nguồn sông Bồ, còn xả
  tràn thì chảy theo sông A Sáp sang Lào (Sê Kông)              → KHÔNG

Sông Bồ nhập vào sông Hương ở ngã ba Sình, hạ lưu Kim Long; ô lưới GloFAS cũng
đã được chọn để KHÔNG gộp sông Bồ (`config.RIVER_POINTS`). Nên lượng xả của
Hương Điền và A Lưới không đổ vào chuỗi ta dự báo.

Quy trình vận hành liên hồ chứa lưu vực sông Hương: QĐ 1606/QĐ-TTg (13/11/2019,
thay QĐ 2482/QĐ-TTg). Mùa lũ vận hành: 01/09 – 15/12. Thông số từng hồ
(dung tích, diện tích lưu vực) lấy từ Phụ lục I của QĐ này:
`data/external/reservoir_info.csv`.

Không có nguồn số liệu xả theo giờ/ngày dạng máy đọc được cho các hồ này
(trang hồ chứa của EVN không có hồ nào thuộc lưu vực sông Hương). Số liệu xả lấy
từ thông báo vận hành đăng trên báo/cổng tỉnh, mỗi dòng có URL và trích nguyên
văn: `data/external/reservoir_releases.csv`.

Luật xử lý khi vận hành (`release_floor`): nước hồ đã xả phải chảy qua Kim Long
trong vài giờ, nên lưu lượng tại Kim Long **không thể nhỏ hơn** tổng lượng xả
của hai hồ thượng nguồn. Dự báo thấp hơn mức đó được nâng lên bằng mức đó.
"""

from __future__ import annotations

import polars as pl

from src import config as cfg

RELEASES = cfg.DATA_EXTERNAL / "reservoir_releases.csv"
# Lệnh xả đang có hiệu lực, nhập tay khi tỉnh phát thông báo (job hằng ngày đọc)
ORDERS = cfg.DATA_EXTERNAL / "reservoir_orders.csv"

UPSTREAM = ("Tả Trạch", "Bình Điền")        # đổ về ô lưới đang dự báo
OTHER_BASIN = ("Hương Điền", "A Lưới")      # sông Bồ — không đổ về ô lưới


def load_releases(path=RELEASES) -> pl.DataFrame:
    """Bảng theo NGÀY × HỒ: nhỏ nhất / lớn nhất của các lần báo trong ngày.

    Báo chí đưa tin ở những giờ khác nhau cho từng hồ, nên cộng hai hồ lại phải
    cẩn thận: cộng các giá trị NHỎ NHẤT là cận dưới bảo thủ, cộng các giá trị
    LỚN NHẤT có thể cộng hai đỉnh không cùng lúc.
    """
    d = pl.read_csv(path, infer_schema_length=0)
    d = d.with_columns(pl.col("date").str.to_date(),
                       pl.col("q_in_m3s").cast(pl.Float64, strict=False),
                       pl.col("q_out_m3s").cast(pl.Float64, strict=False))
    return (d.filter(pl.col("q_out_m3s").is_not_null() | pl.col("q_in_m3s").is_not_null())
             .group_by("date", "reservoir")
             .agg(pl.col("q_out_m3s").min().alias("q_out_min"),
                  pl.col("q_out_m3s").max().alias("q_out_max"),
                  pl.col("q_in_m3s").max().alias("q_in_max"),
                  pl.len().alias("n_reports"))
             .sort("date", "reservoir"))


def upstream_daily(rel: pl.DataFrame) -> pl.DataFrame:
    """Tổng của các hồ thượng nguồn theo ngày, kèm số hồ có số liệu.

    `n_upstream < 2` nghĩa là chỉ biết một hồ — tổng là CẬN DƯỚI của lượng thật.
    `q_inflow_upstream`: nước tự nhiên đổ vào hai hồ — phần lưu vực này cũng
    chảy tới Kim Long, nên đây là cận dưới của dòng chảy TỰ NHIÊN tại Kim Long.
    """
    up = rel.filter(pl.col("reservoir").is_in(UPSTREAM))
    out = (up.drop_nulls("q_out_max").group_by("date")
             .agg(pl.col("q_out_max").sum().alias("q_release_upstream"),
                  pl.col("q_out_min").sum().alias("q_release_upstream_min"),
                  pl.col("reservoir").n_unique().alias("n_upstream")))
    inflow = (up.drop_nulls("q_in_max").group_by("date")
                .agg(pl.col("q_in_max").sum().alias("q_inflow_upstream"),
                     pl.col("reservoir").n_unique().alias("n_inflow")))
    return out.join(inflow, on="date", how="full", coalesce=True).sort("date")


def release_floor(q_forecast: float, q_release: float | None) -> float:
    """Cận dưới vật lý: dự báo tại Kim Long ≥ tổng xả hồ thượng nguồn."""
    if q_release is None or q_release != q_release:      # None hoặc NaN
        return q_forecast
    return max(q_forecast, q_release)


def active_orders(day, path=ORDERS) -> float | None:
    """Tổng lưu lượng xả theo lệnh đang hiệu lực cho `day` (chỉ hồ thượng nguồn).

    File nhập tay: date_from,date_to,reservoir,q_out_m3s,source_url. Không có
    file hoặc không có lệnh ⇒ None (không hiệu chỉnh).
    """
    if not path.exists():
        return None
    o = pl.read_csv(path, try_parse_dates=True)
    if o.is_empty():                     # file mẫu chỉ có dòng tiêu đề
        return None
    o = o.filter(pl.col("reservoir").is_in(UPSTREAM)
                 & (pl.col("date_from") <= day) & (pl.col("date_to") >= day))
    if o.is_empty():
        return None
    # Một hồ có thể có nhiều lệnh chồng nhau: lấy lệnh lớn nhất của mỗi hồ
    return float(o.group_by("reservoir").agg(pl.col("q_out_m3s").max())
                   ["q_out_m3s"].sum())
