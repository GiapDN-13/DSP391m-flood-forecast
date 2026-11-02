"""Dashboard dự báo lưu lượng sông Hương tại Kim Long (Huế), 1–3 ngày tới.

    streamlit run dashboard/app.py

Đọc ``reports/forecast_log/`` (job hằng ngày ghi), ``reports/risk_levels.csv``,
``reports/shap_importance.csv`` và geojson lưu vực con. Toàn bộ hàm đọc dữ liệu
nằm ở ``dashboard/data.py`` (có test). Sản phẩm học thuật, KHÔNG phải bản tin
cảnh báo chính thức.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# `streamlit run dashboard/app.py` chỉ đưa thư mục dashboard/ vào sys.path;
# thêm gốc repo để import theo gói, tránh đụng tên với thư mục data/ ở gốc.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dashboard import data as dd  # noqa: E402

st.set_page_config(page_title="Dự báo lưu lượng sông Hương — Kim Long",
                   page_icon="🌊", layout="wide")

# Màu chuỗi (bảng phân loại đã kiểm CVD) — khác hẳn màu trạng thái của mức nguy cơ.
C_HIST = "#8a8985"
C_GLOFAS = "#2a78d6"
C_LGBM = "#1baf7a"
LINE_W = 1.6


# ---------------------------------------------------------------- nạp dữ liệu (có cache)
@st.cache_data(ttl=600)
def _runs():
    return dd.list_runs()


@st.cache_data(ttl=600)
def _run(run):
    return dd.load_run(run)


@st.cache_data(ttl=600)
def _history(run, days):
    return dd.history_from_logs(run, days), dd.history_from_panel(run, days)


@st.cache_data(ttl=3600)
def _levels():
    return dd.load_risk_levels()


@st.cache_data(ttl=3600)
def _shap(basis):
    return dd.load_shap_groups(basis=basis)


@st.cache_data(ttl=3600)
def _basins():
    return dd.load_subbasins()


def _fmt_q(v) -> str:
    return "—" if v is None or pd.isna(v) else f"{v:,.0f}".replace(",", ".")


# ---------------------------------------------------------------- khung chung
st.title("Dự báo lưu lượng sông Hương tại Kim Long")
st.caption("Lưu lượng 1–3 ngày tới (m³/s). Mục tiêu dự báo là **lưu lượng GloFAS v4 "
           "theo ngày**, không phải số đo tại trạm. Sản phẩm học thuật (DSP391m) — "
           "**không phải bản tin cảnh báo chính thức**.")

runs = _runs()
thr, thr_from_file = _levels()

if not runs:
    st.error("Không tìm thấy bản phát nào trong `reports/forecast_log/`. "
             "Job dự báo hằng ngày chưa chạy hoặc thư mục bị thiếu.")
    st.stop()

with st.sidebar:
    st.header("Bản phát")
    run = st.selectbox("Ngày phát báo", options=list(reversed(runs)),
                       format_func=lambda d: d.strftime("%d/%m/%Y"),
                       help="Mỗi ngày job GitHub Actions phát một bản lúc ~05:00 giờ VN.")
    days_back = st.slider("Số ngày lịch sử", 7, 60, 30, step=1)
    show_levels = st.checkbox("Hiện ngưỡng mức nguy cơ", value=True)
    st.divider()
    today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
    latest = dd.latest_run(runs)
    st.caption(f"Bản mới nhất: **{latest:%d/%m/%Y}** · {len(runs)} bản phát đã lưu.")
    if latest < today - timedelta(days=1):
        st.warning(f"Bản mới nhất cũ hơn hôm nay ({today:%d/%m/%Y}) quá 1 ngày — "
                   "job hằng ngày có thể đã lỗi.")
    if not thr_from_file:
        st.warning("Không đọc được `reports/risk_levels.csv` — đang dùng ngưỡng dự phòng.")

run_df = _run(run)
model_on = dd.has_model(run_df)
table = dd.forecast_table(run_df, thr)

tab_fc, tab_map, tab_xai = st.tabs(["📈 Dự báo", "🗺️ Bản đồ lưu vực", "ℹ️ Giải thích & hạn chế"])

# ================================================================ TAB 1 — DỰ BÁO
with tab_fc:
    if not table.empty:
        worst = int(table["level"].max())
        st.subheader(f"Mức cao nhất 3 ngày tới: {dd.level_label(worst)}")
    if not model_on:
        st.info("Bản phát này **chưa có cột mô hình LightGBM** — biểu đồ và bảng "
                "chỉ hiển thị GloFAS thô (và GloFAS đã nâng sàn theo lệnh xả hồ nếu có).")

    hist_log, hist_panel = _history(run, days_back)
    fc = run_df[run_df["horizon_days"].between(0, 3)]

    fig = go.Figure()
    if not hist_panel.empty:
        fig.add_trace(go.Scatter(
            x=hist_panel["date"], y=hist_panel["discharge"], mode="lines",
            name="GloFAS tái phân tích (panel)",
            line=dict(color=C_HIST, width=LINE_W, dash="dot")))
    if not hist_log.empty:
        fig.add_trace(go.Scatter(
            x=hist_log["date"], y=hist_log["discharge"], mode="lines",
            name="Đã qua: GloFAS ngày phát (h0)",
            line=dict(color=C_HIST, width=LINE_W)))
    fig.add_trace(go.Scatter(
        x=fc["target_date"], y=fc["glofas_discharge"], mode="lines+markers",
        name="Dự báo GloFAS thô", line=dict(color=C_GLOFAS, width=LINE_W),
        marker=dict(size=7)))
    # Chỉ vẽ đường sàn hồ khi nó thật sự khác GloFAS thô (có lệnh xả).
    if (fc["glofas_san_ho"].notna().any()
            and not fc["glofas_san_ho"].fillna(-1).equals(fc["glofas_discharge"].fillna(-1))):
        fig.add_trace(go.Scatter(
            x=fc["target_date"], y=fc["glofas_san_ho"], mode="lines",
            name="GloFAS nâng sàn hồ", line=dict(color=C_GLOFAS, width=LINE_W, dash="dot")))
    if model_on:
        fig.add_trace(go.Scatter(
            x=fc["target_date"], y=fc["lgbm_q"], mode="lines+markers",
            name="Dự báo LightGBM", line=dict(color=C_LGBM, width=LINE_W),
            marker=dict(size=7, symbol="diamond")))
        if fc["lgbm_san_ho"].notna().any():
            fig.add_trace(go.Scatter(
                x=fc["target_date"], y=fc["lgbm_san_ho"], mode="lines",
                name="LightGBM nâng sàn hồ",
                line=dict(color=C_LGBM, width=LINE_W, dash="dot")))
    if show_levels:
        for k in (1, 2, 3):
            fig.add_hline(y=thr[k], line=dict(color=dd.LEVEL_COLOR[k], width=1, dash="dash"),
                          annotation_text=f"{dd.LEVEL_ICON[k]} {dd.LEVEL_TEXT[k]} "
                                          f"({_fmt_q(thr[k])})",
                          annotation_position="top left")
    # Vạch ngày phát: dùng shape + annotation riêng (add_vline với trục ngày dễ lỗi).
    x_run = pd.Timestamp(run)
    fig.add_shape(type="line", x0=x_run, x1=x_run, y0=0, y1=1, yref="paper",
                  line=dict(color=C_HIST, width=1, dash="dot"))
    fig.add_annotation(x=x_run, y=1, yref="paper", text="Ngày phát", showarrow=False,
                       xanchor="left", yanchor="bottom")
    fig.update_layout(
        height=470, margin=dict(l=10, r=10, t=70, b=10), hovermode="x unified",
        yaxis_title="Lưu lượng (m³/s)", xaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.07, x=0))
    fig.update_yaxes(rangemode="tozero")
    st.plotly_chart(fig, theme="streamlit")
    st.caption("Lịch sử lấy từ dòng horizon 0 của các bản phát trước (GloFAS ngày phát), "
               "nối thêm GloFAS tái phân tích khi máy có `data/processed/`. "
               "Ngưỡng mức nguy cơ = phân vị 95 / 98 / 99,5 % lưu lượng mùa lũ "
               "(train + valid), **không phải cấp báo động BĐ I/II/III**.")

    st.markdown("#### Ba ngày tới")
    if table.empty:
        st.warning("Bản phát này không có dòng horizon 1–3.")
    else:
        show = pd.DataFrame({
            "Ngày": [d.strftime("%d/%m/%Y") for d in table["target_date"]],
            "Trước": [f"{h} ngày" for h in table["horizon"]],
            "GloFAS thô (m³/s)": table["glofas_discharge"].map(_fmt_q),
            "GloFAS sàn hồ (m³/s)": table["glofas_san_ho"].map(_fmt_q),
        })
        if model_on:
            show["LightGBM (m³/s)"] = table["lgbm_q"].map(_fmt_q)
            if table["lgbm_san_ho"].notna().any():
                show["LightGBM sàn hồ (m³/s)"] = table["lgbm_san_ho"].map(_fmt_q)
            if table["p_level1"].notna().any():
                show["P(≥ mức 1)"] = table["p_level1"].map(
                    lambda p: "—" if pd.isna(p) else f"{p:.0%}")
        show["Xếp mức theo"] = table["nguon_xep_muc"]
        show["Mức nguy cơ"] = table["muc"]
        st.dataframe(show, hide_index=True)

# ================================================================ TAB 2 — BẢN ĐỒ
with tab_map:
    gj = _basins()
    if gj is None:
        st.warning("Không tìm thấy `data/external/basins/subbasins.geojson`.")
    elif table.empty:
        st.warning("Bản phát này không có dòng horizon 1–3 để tô màu bản đồ.")
    else:
        h = st.radio("Ngày dự báo", options=list(table["horizon"]), horizontal=True,
                     format_func=lambda x: (f"+{x} ngày ("
                                            f"{table.loc[table['horizon'] == x, 'target_date'].iloc[0]:%d/%m})"))
        row = table[table["horizon"] == h].iloc[0]
        lv = int(row["level"])
        st.markdown(f"**{dd.level_label(lv)}** — {row['nguon_xep_muc']} "
                    f"{_fmt_q(row['q_xep_muc'])} m³/s tại Kim Long, ngày "
                    f"{row['target_date']:%d/%m/%Y}.")
        st.info("Mô hình dự báo **một** lưu lượng cho cả lưu vực tại Kim Long. Mức nguy cơ "
                "trên bản đồ là **mức toàn lưu vực, gán chung cho cả 5 lưu vực con** — "
                "không phải dự báo riêng cho từng lưu vực con.")
        frame = dd.subbasin_frame(gj, lv)
        cmap = {dd.level_label(k): dd.LEVEL_COLOR[k] for k in dd.LEVEL_COLOR}
        choropleth = getattr(px, "choropleth_map", None)
        kw = dict(geojson=gj, locations="id", color="muc", color_discrete_map=cmap,
                  hover_name="ten", hover_data={"dien_tich_km2": True, "id": False,
                                                "muc": True},
                  labels={"muc": "Mức nguy cơ", "dien_tich_km2": "Diện tích (km²)"},
                  center=dict(lat=16.36, lon=107.58), zoom=9, opacity=0.45)
        if choropleth is not None:
            mfig = choropleth(frame, map_style="open-street-map", **kw)
            marker_cls = go.Scattermap
        else:   # plotly cũ chỉ có bản mapbox
            mfig = px.choropleth_mapbox(frame, mapbox_style="open-street-map", **kw)
            marker_cls = go.Scattermapbox
        mfig.update_traces(marker_line_width=1, marker_line_color="#333333",
                           selector=dict(type=mfig.data[0].type))
        mfig.add_trace(marker_cls(
            lat=[dd.KIM_LONG[0]], lon=[dd.KIM_LONG[1]], mode="markers+text",
            marker=dict(size=13, color="#111111"), text=["Kim Long"],
            textposition="top right", name="Trạm Kim Long (cửa ra)",
            hovertemplate="Kim Long<extra></extra>"))
        mfig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0),
                           legend=dict(yanchor="top", y=0.98, x=0.01))
        st.plotly_chart(mfig, theme="streamlit")
        st.dataframe(frame.rename(columns={"ten": "Lưu vực con",
                                           "dien_tich_km2": "Diện tích (km²)",
                                           "muc": "Mức nguy cơ (toàn lưu vực)"})
                     .drop(columns="id"), hide_index=True)
        st.caption("Ranh giới lưu vực con chia từ DEM Copernicus 30 m (D8, pysheds) — "
                   "`src/features/basins.py`. Nền bản đồ © OpenStreetMap.")

# ================================================================ TAB 3 — GIẢI THÍCH
with tab_xai:
    st.subheader("Mô hình dựa vào gì? (SHAP theo nhóm cơ chế)")
    basis = st.radio("Tập tính", options=["all", "flood"], horizontal=True,
                     format_func=lambda b: "Toàn tập test" if b == "all" else "Chỉ ngày lũ")
    sg = _shap(basis)
    if sg.empty:
        st.warning("Không đọc được `reports/shap_importance.csv`.")
    else:
        order = (sg[sg["horizon"] == 1].sort_values("share")["nhom"].tolist())
        sfig = go.Figure()
        # Cột ngang nhóm: plotly xếp vết đầu tiên ở DƯỚI cùng, nên thêm h3 → h1
        # để h1 nằm trên trong mỗi nhóm, rồi đảo lại thứ tự chú giải.
        for hz, color in zip((3, 2, 1), ("#1baf7a", "#eb6834", "#2a78d6")):
            s = sg[sg["horizon"] == hz].set_index("nhom").reindex(order)
            sfig.add_trace(go.Bar(
                y=s.index, x=s["share"], orientation="h", name=f"h{hz} (+{hz} ngày)",
                marker=dict(color=color),
                error_x=dict(type="data", symmetric=False, array=s["hi"] - s["share"],
                             arrayminus=s["share"] - s["lo"], thickness=1, width=3,
                             color="#8a8985"),
                hovertemplate="%{y}: %{x:.1f}%<extra>h" + str(hz) + "</extra>"))
        sfig.update_layout(barmode="group", height=480, bargap=0.25, bargroupgap=0.05,
                           xaxis_title="Tỉ trọng |SHAP| của nhóm (%)", yaxis_title=None,
                           margin=dict(l=10, r=10, t=10, b=10),
                           legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                                       traceorder="reversed"))
        st.plotly_chart(sfig, theme="streamlit")
        st.caption("Cột = trung bình 3 seed (42, 7, 2026); vạch = min–max giữa các seed. "
                   "Đọc: ở h1 lưu lượng hôm nay gánh ~58 %; tới h3 mô hình dựa nhiều hơn "
                   "vào khí áp/gió và **lịch (mùa)** — tức lùi dần về khí hậu. "
                   "Chi tiết: `docs/FINDINGS_SHAP.md`.")

    st.subheader("Mô hình tốt tới đâu?")
    perf = pd.DataFrame({
        "Horizon": ["h1 (+1 ngày)", "h2 (+2 ngày)", "h3 (+3 ngày)"],
        "NSE test (LightGBM E)": [0.75, 0.50, 0.24],
        "NSE walk-forward": [0.76, 0.44, 0.21],
        "NSE persistence (Q hôm nay)": [0.54, 0.01, -0.20],
        "Trung vị dự báo / thực, ngày lũ": [0.56, 0.34, 0.20],
    })
    st.dataframe(perf, hide_index=True, column_config={
        c: st.column_config.NumberColumn(format="%.2f") for c in perf.columns[1:]})
    st.caption("NSE = 1 là hoàn hảo; NSE ≤ 0 nghĩa là không hơn lấy trung bình. "
               "Persistence = giả định ngày mai bằng hôm nay.")

    st.subheader("Hạn chế — đọc trước khi dùng")
    st.markdown(f"""
- **Mục tiêu là GloFAS, không phải trạm đo.** Mô hình hiệu chỉnh cục bộ lưu lượng
  GloFAS v4 theo ngày; số đo thực tại trạm Kim Long không dùng để huấn luyện.
- **Mức nguy cơ không phải cấp báo động BĐ I/II/III.** Đó là phân vị 95 / 98 / 99,5 %
  lưu lượng mùa lũ (= {_fmt_q(thr[1])} / {_fmt_q(thr[2])} / {_fmt_q(thr[3])} m³/s).
  Không quy được sang mực nước vì quan hệ H–Q tại Kim Long rất yếu (R² ≈ 0,18).
- **Đỉnh lũ bị dự báo thấp.** Trên các ngày lũ, trung vị tỉ số dự báo/thực chỉ
  0,56 / 0,34 / 0,20 ở h1 / h2 / h3 — số dự báo "bình thường" vẫn có thể là lũ.
- **h3 chưa đạt mục tiêu AC-1** (NSE ≥ 0,25): NSE test 0,24, walk-forward 0,21.
- Lưu vực chỉ có **một** dự báo tại Kim Long; màu trên bản đồ là mức chung.
- **Sản phẩm học thuật**, không thay thế bản tin của cơ quan khí tượng thuỷ văn.
  Khi có lũ, theo dõi thông báo chính thức của tỉnh và Đài KTTV.
""")
