# Dashboard dự báo lưu lượng sông Hương — Kim Long

Ứng dụng Streamlit đọc nhật ký dự báo hằng ngày (`reports/forecast_log/`) và hiển thị
lưu lượng 1–3 ngày tới tại Kim Long. **Sản phẩm học thuật, không phải bản tin cảnh báo
chính thức.**

| Tab | Nội dung |
|---|---|
| 📈 Dự báo | 30 ngày đã qua (GloFAS ngày phát, horizon 0 của các bản trước) + dự báo 1–3 ngày: GloFAS thô, GloFAS nâng sàn hồ, LightGBM (khi bản phát có cột `lgbm_q`, `lgbm_san_ho`, `p_level1`); 3 đường ngưỡng mức nguy cơ; bảng 3 ngày có nhãn mức (biểu tượng + chữ). Chọn ngày phát ở thanh bên. |
| 🗺️ Bản đồ lưu vực | 5 lưu vực con (geojson `data/external/basins/subbasins.geojson`) tô theo mức nguy cơ của ngày dự báo chọn. Mức là **mức toàn lưu vực tại Kim Long**, gán chung cho cả 5. |
| ℹ️ Giải thích & hạn chế | Tỉ trọng SHAP theo nhóm cơ chế h1/h2/h3 (`reports/shap_importance.csv`), NSE test / walk-forward / persistence, và các hạn chế. |

Ngưỡng mức nguy cơ đọc từ `reports/risk_levels.csv` (phân vị 95 / 98 / 99,5 % lưu lượng
mùa lũ = 806 / 1 275 / 1 905 m³/s) — **không phải cấp báo động BĐ I/II/III**.

## Chạy trên máy

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Mở <http://localhost:8501>. Chạy từ gốc repo. Nếu máy có `data/processed/daily_panel_ext.parquet`
(gitignored), biểu đồ vẽ thêm chuỗi GloFAS tái phân tích; không có thì chỉ dùng nhật ký
dự báo — bản triển khai luôn ở trường hợp này.

Hàm đọc dữ liệu nằm ở `dashboard/data.py` (chỉ pandas), kiểm bằng:

```bash
pytest -q tests/test_dashboard.py
```

Test cuối dùng `streamlit.testing.v1.AppTest` chạy cả app; tự bỏ qua nếu thiếu streamlit.

## Tự triển khai lên Streamlit Community Cloud

Việc này **bạn tự làm** (cần đăng nhập tài khoản của bạn); repo đang private nên phải cấp
quyền cho Streamlit đọc repo.

1. Đẩy nhánh có thư mục `dashboard/` lên GitHub.
2. Vào <https://share.streamlit.io>, đăng nhập bằng GitHub; lần đầu sẽ được hỏi cấp quyền
   truy cập repo **private** — chấp nhận cho repo này.
3. **Create app → Deploy a public app from GitHub** (hoặc "from repo"):
   * Repository: repo của dự án · Branch: `main` (hoặc nhánh bạn muốn)
   * Main file path: `dashboard/app.py`
   * Advanced settings → Python 3.12 hoặc 3.13.
4. Streamlit Cloud cài `dashboard/requirements.txt` (file cạnh `app.py` được ưu tiên hơn
   `requirements.txt` ở gốc — file gốc có torch/pyspark, rất nặng).
5. Ứng dụng từ repo private mặc định chỉ người được mời xem được; muốn chia sẻ thì
   **Share → mời email** hoặc đổi sang public trong cài đặt app.

Dữ liệu tự cập nhật: job GitHub Actions commit bản dự báo mới mỗi sáng; Streamlit Cloud
nhận commit mới và chạy lại app. Bộ nhớ đệm trong app hết hạn sau 10 phút.

## Khi mô hình bắt đầu ghi cột

`src/models/predict_daily.py` sẽ ghi thêm `lgbm_q`, `lgbm_san_ho`, `p_level1`, `alert_lgbm`.
Dashboard tự hiện đường LightGBM và cột xác suất khi các cột này có số; bản phát cũ không
có cột thì hiện GloFAS và ghi chú. Mức nguy cơ trong bảng xếp theo thứ tự ưu tiên:
LightGBM nâng sàn hồ → LightGBM → GloFAS nâng sàn hồ → GloFAS thô (cột "Xếp mức theo").
