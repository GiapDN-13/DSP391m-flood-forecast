# FLOW TOÀN MÔN — từ dữ liệu thô tới điểm thi

**Cập nhật:** 15/09/2026 (cuối W1) · Ký hiệu: ✅ xong · 🟡 đang dở · ⛔ bị chặn · ⬜ chưa bắt đầu

---

## 1. Sơ đồ tổng thể

```mermaid
flowchart TD
    subgraph A["① THU THẬP DỮ LIỆU — ✅ XONG"]
        A1["✅ FR-D5 Chọn ô lưới GloFAS<br/>(16.45, 107.50)"]
        A2["✅ FR-D1 Lưu lượng 1984–2026<br/>83 ô"]
        A3["✅ FR-D2 Mưa ERA5 ngày + giờ<br/>lưới 0,10° · 68 điểm"]
        A4["✅ FR-D3 Mưa dự báo lưu trữ<br/>2022–nay"]
        A5["⬜ FR-D6 Backup Drive / HF"]
    end

    subgraph B["② NGƯỠNG BÁO ĐỘNG — ⛔ ĐANG CHẶN"]
        B1["🟡 FR-T1 Mực nước BĐ I/II/III<br/>1,00 / 2,00 / 3,50 m"]
        B2["⛔ FR-D7 flood_events.csv<br/>≥ 15 đợt lũ có nguồn"]
        B3["⛔ FR-T2 Ánh xạ H → Q<br/>H = α·ln(Q) + β"]
        B4["⛔ FR-T3 Nhãn alert_level"]
    end

    subgraph C["③ XỬ LÝ — ✅ XONG"]
        C1["✅ FR-E1..E3 clean.py"]
        C2["✅ FR-E4 Gộp 3 tiểu lưu vực"]
        C3["✅ FR-E5/E6 daily_panel.parquet<br/>6 087 × 71, không rò rỉ"]
    end

    subgraph D["④ PHÂN TÍCH — ⬜"]
        D1["⬜ EDA 8 mục"]
        D2["⬜ FR-R2 Report 2"]
    end

    subgraph E["⑤ MÔ HÌNH — ⬜"]
        E1["⬜ FR-M1 4 baseline<br/>+ GloFAS thô"]
        E2["⬜ FR-M2 LightGBM hồi quy"]
        E3["⛔ FR-M3 3 classifier<br/>cấp báo động"]
        E4["⬜ FR-M4/M5 Optuna + ngưỡng chi phí"]
    end

    subgraph F["⑥ ĐÁNH GIÁ — 🟡"]
        F1["✅ FR-V1 Walk-forward + gap"]
        F2["⬜ FR-V2/V3 Metric hồi quy<br/>+ sự kiện hiếm"]
        F3["⬜ FR-V4 Kịch bản A / B"]
        F4["⬜ FR-V7 SHAP"]
    end

    subgraph G["⑦ SẢN PHẨM — 🟡"]
        G1["✅ FR-P4 Job dự báo hằng ngày<br/>GitHub Actions"]
        G2["⬜ FR-P1/P2 Dashboard 2 trang"]
        G3["⬜ FR-R3 Report 3 — 40 %"]
    end

    subgraph H["⑧ KẾT THÚC — ⬜"]
        H1["⬜ FR-R4 Report 4 + slide"]
        H2["⬜ Thi vấn đáp — chấm cá nhân"]
    end

    A2 --> C1
    A3 --> C1
    C1 --> C2 --> C3
    A1 --> A2
    B1 --> B3
    B2 --> B3 --> B4
    A2 --> B3
    C3 --> B4
    C3 --> D1 --> D2
    B4 --> E3
    C3 --> E1 --> E2 --> E4
    A4 --> F3
    E2 --> F2
    E3 --> F2
    F1 --> F2 --> F3 --> F4
    F4 --> G3
    E2 --> G2 --> G3
    G1 --> F3
    D2 --> G3 --> H1 --> H2

    classDef done fill:#166534,stroke:#22c55e,color:#fff
    classDef wip fill:#854d0e,stroke:#f59e0b,color:#fff
    classDef blocked fill:#7f1d1d,stroke:#ef4444,color:#fff
    classDef todo fill:#1e293b,stroke:#475569,color:#cbd5e1
    class A1,A2,A3,A4,C1,C2,C3,F1,G1 done
    class B1 wip
    class B2,B3,B4,E3 blocked
    class A5,D1,D2,E1,E2,E4,F2,F3,F4,G2,G3,H1,H2 todo
```

---

## 2. Bảng trạng thái chi tiết

### ① Thu thập dữ liệu — ✅ **hoàn tất**

| # | Việc | Trạng thái | Bằng chứng |
|---|---|---|---|
| FR-D5 | Chọn ô lưới GloFAS | ✅ | `(16.45, 107.50)`, 3 bằng chứng độc lập — `FINDINGS_GRID.md` |
| FR-D1 | Lưu lượng 1984–2026 | ✅ | 83 ô × 15 584 ngày |
| FR-D2 | Mưa ERA5 ngày + giờ | ✅ | 68 điểm lưới 0,10°; 2010–2026 ngày, 2015–2026 giờ |
| FR-D3 | Mưa dự báo lưu trữ | ✅ | 70 file, 2022-07 → nay |
| FR-D4 | Crawler chịu lỗi | ✅ | retry + cache + checkpoint + khoá chống chạy trùng |
| FR-D6 | Backup ra Drive / HF | ⬜ | **chưa làm** — dữ liệu mới chỉ nằm trên 1 máy |
| FR-D7 | `flood_events.csv` | ⛔ | 0/15 dòng — **nút thắt lớn nhất** |

### ② Ngưỡng báo động — ⛔ **đang chặn cả nhánh phân loại**

| # | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| FR-T1 | Mực nước BĐ I/II/III | 🟡 | Giá trị đã kiểm chứng chéo bằng 5 bản tin KTTV. Còn: dẫn nguồn gốc QĐ 05/2020/QĐ-TTg |
| FR-T2 | Ánh xạ H → Q | ⛔ | Chờ `FR-D7`. Thuật toán đã chốt ở `THRESHOLDS.md` §3 R2 |
| FR-T3 | Nhãn `alert_level` | ⛔ | Cột đã có trong panel nhưng **để trống** |
| FR-T4 | Kiểm chứng 3 đợt lũ | ⛔ | Chờ FR-T2 |

### ③ Xử lý dữ liệu — ✅ **hoàn tất**

| # | Việc | Trạng thái | Bằng chứng |
|---|---|---|---|
| FR-E1 | Múi giờ UTC → ICT | ✅ | test xanh |
| FR-E2 | Gộp giờ → ngày | ✅ | test xanh |
| FR-E3 | Bắt dữ liệu bất thường | ✅ | 4 test xanh; thực tế 0 % thiếu |
| FR-E4 | Gộp 3 tiểu lưu vực | ✅ | thượng 30 / trung 9 / hạ 29 điểm |
| FR-E5 | `daily_panel.parquet` | ✅ | 6 087 × 71, 2010–2026, 0 ngày trùng |
| FR-E6 | Lag không rò rỉ | ✅ | `test_no_leakage.py` xanh toàn bộ |

### ④ → ⑧ Phần còn lại — ⬜ **chưa bắt đầu**

| Giai đoạn | Việc chính | Phụ thuộc |
|---|---|---|
| ④ Phân tích | EDA 8 mục (`EDA_CHECKLIST.md`) · Report 2 | panel ✅ — **làm được ngay** |
| ⑤ Mô hình | 4 baseline · LightGBM hồi quy | panel ✅ — **làm được ngay** |
| | 3 classifier cấp báo động | ⛔ chờ `alert_level` |
| ⑥ Đánh giá | Metric hồi quy + sự kiện hiếm · kịch bản A/B · SHAP | chờ ⑤ |
| ⑦ Sản phẩm | Dashboard 2 trang · Report 3 (40 %) | chờ ⑥ |
| ⑧ Kết thúc | Report 4 · slide · thi vấn đáp | chờ ⑦ |

---

## 3. Đường găng hiện tại

```
⛔ FR-D7 flood_events.csv  ──►  FR-T2 ánh xạ H→Q  ──►  FR-T3 nhãn  ──►  FR-M3 classifier
                                                                            │
✅ daily_panel.parquet  ──►  EDA + baseline + LightGBM hồi quy  ────────────┤
                                                                            ▼
                                                                    Report 3 (40 %)
```

**Chỉ còn một nút thắt thật:** `flood_events.csv`. Nó chặn **toàn bộ nhánh phân loại cấp báo động** — tức câu hỏi nghiên cứu số 2, và là phần đặc thù nhất của đề tài.

Nhánh **hồi quy lưu lượng thì không bị chặn** — panel đã sẵn sàng, chạy baseline và LightGBM được ngay hôm nay.

---

## 4. Đối chiếu tiến độ với lịch 9 tuần

| Tuần | Kế hoạch | Thực tế |
|---|---|---|
| **W1** | Khởi động, bắt đầu crawl | ✅ **Vượt xa:** crawl xong toàn bộ, chọn xong ô lưới, ETL + panel xong, job hằng ngày đã chạy |
| **W2** | Report 1, crawl chạy nền | Còn: Report 1, literature review, `flood_events.csv` |
| **W3** | Dữ liệu xong + ngưỡng BĐ | Dữ liệu ✅ đã xong từ W1. Còn ngưỡng |
| W4 | EDA + Report 2 | làm được sớm hơn |
| W5–W6 | Mô hình + đánh giá | làm được sớm hơn |
| W7–W8 | SHAP, dashboard, Report 3 | |
| W9 | Report 4 + thi | |

Phần dữ liệu **đi trước kế hoạch khoảng 2 tuần**. Nhưng đừng coi đó là dư dả: phần ăn điểm nặng nhất (Report 3 — 40 %) vẫn ở phía trước, và `flood_events.csv` là việc **đọc–tra thủ công, không rút ngắn bằng máy được**.

---

## 5. Việc làm được ngay, không chờ ai

Vì panel đã xong, ba việc sau khởi động được lập tức:

1. **EDA 8 mục** theo `docs/EDA_CHECKLIST.md` → nội dung Report 2.
2. **4 baseline** (persistence · seasonal naive · ARIMA · **GloFAS thô**) → bảng so sánh đầu tiên.
3. **LightGBM hồi quy** h = 1/2/3, có GloFAS forecast làm feature → trả lời `AC-1` và `AC-3`.

Việc **chưa làm được**: mọi thứ liên quan cấp báo động (`FR-M3`, một phần `FR-V3`) — chờ `flood_events.csv`.

---

## 6. Rủi ro còn treo

| Rủi ro | Mức | Xử lý |
|---|---|---|
| `flood_events.csv` không đủ 10 đợt | 🔴 cao | Lùi về R4 (ngưỡng phân vị) và **đổi tên nhãn** thành "mức nguy cơ", không gọi là BĐ |
| Dữ liệu chỉ nằm trên 1 máy (FR-D6) | 🟠 | Backup Drive/HF — 10 phút, nên làm sớm |
| Đỉnh lũ bất thường 04/2022 (2 635 m³/s ngoài mùa lũ) | 🟡 | Kiểm khi EDA; nếu là lỗi dữ liệu thì ảnh hưởng phân vị và ngưỡng |
| Thi vấn đáp chấm cá nhân | 🟠 | `EXPLAINER.md` còn trống — bắt đầu viết từ W2 |
