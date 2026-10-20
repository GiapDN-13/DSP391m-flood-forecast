# THỬ BẢN TIN THỦY VĂN KTTV — dựng được "mực nước Kim Long tại giờ bản tin" không?

Ngày thử: **20/10/2026**. Không viết code ingest. Chỉ tải tay **13 PDF** (~5,4 MB) vào thư mục tạm trên ổ C:, đọc chữ bằng PyMuPDF và render ảnh các trang có bảng dạng ảnh. Thư mục tạm đã xoá sau khi ghi file này.

> Dự kiến tải 3–5 bản, thực tế tải 13 bản. Lý do: cả 3 bản năm 2020 tìm được đều không có số Kim Long, và cần đủ mẫu cho 3 dạng bản tin khác nhau.

## 1. Kết luận nhanh

| Câu hỏi | Trả lời |
|---|---|
| Dựng được bộ "H Kim Long tại giờ bản tin" không? | **Được cho 2024–2026**, **một phần cho 10/2022** (lấy qua Internet Archive), **không được cho 2020** (xem §6) |
| Độ phân giải | Tối đa **6 giờ/lần** (01–07–13–19h), cộng thêm đỉnh và giờ đỉnh ghi trong lời văn. **Không phải chuỗi giờ liên tục** |
| Dùng vào việc gì | **Kiểm chứng** độ lớn và thời điểm đỉnh lũ của mô hình trên tập test (≥ 2022-07-01). Làm **baseline "dự báo chính thức"**, vì mỗi tin lũ có dự báo 4 mốc 6 giờ. Bổ sung `flood_events.csv` |
| Không dùng được vào việc gì | Không dùng làm nhãn huấn luyện theo giờ, vì ngoài mùa lũ không có số và các năm 2020, 2021, 2023 gần như trống |
| Liệt kê URL bằng mẫu được không? | **Không.** Thư mục, giờ phát và hậu tố trong URL thay đổi; mã sản phẩm và host cũng đổi qua các năm. Cần **trang danh mục** (chỉ giữ khoảng 1 năm) **hoặc Internet Archive CDX** |

## 2. Ba loại bản tin có số liệu Kim Long

| Mã file | Tên bản tin | Tần suất | Kim Long có gì | Bảng số liệu |
|---|---|---|---|---|
| `dbqg_tvhn` | Bản tin dự báo, cảnh báo thủy văn **thời hạn ngắn** | **Hằng ngày** khoảng 10h30. Số hiệu bằng thứ tự ngày trong năm: TVHN-283 (10/10/2022), TVHN-330 (25/11/2024), TVHN-303 (30/10/2025) | Bảng ghi **cao nhất và thấp nhất thực đo 24h qua**, dự báo cao nhất và thấp nhất 24h tới (cm), **không ghi giờ**. Lời văn mục "Sông Hương" khi có lũ ghi H kèm giờ | Dạng chữ, trích được |
| `dbqg_lutb` (≤ 2023) / `dbqg_lulu` (từ 2024) | **Tin lũ / Tin lũ khẩn cấp** | Chỉ phát khi có lũ, thấy 3–4 bản/ngày (03h30, 09h00 hoặc 10h00, 15h30, 21h00); khi lũ khẩn cấp có thêm bản 19h30, 02h30… | H thực đo tại 1 mốc giờ, đỉnh và giờ đỉnh, **dự báo 4 mốc** cách nhau 6 giờ (Phụ lục 1) | Năm 2022 dạng **chữ**. Năm 2025 Phụ lục 1 là **ảnh**, phải đọc ảnh hoặc OCR |
| `dbqg_hghn` | Bản tin dự báo thủy văn hằng ngày **phục vụ quy trình liên hồ chứa sông Hương** trong mùa lũ | Hằng ngày 15h00 trong mùa lũ. **Chỉ thấy năm 2026** (06/09, 08/09, 09/10) | **H thực đo Kim Long và Phú Ốc lúc 19h, 01h, 07h, 13h** (24h qua) và dự báo 4 mốc | Dạng chữ, trích được |

## 3. Các bản tin đã tải thử

`WB` là bản lưu Internet Archive, URL dạng `http://web.archive.org/web/<timestamp>id_/<URL gốc>`. Bản gốc trên `thoitietvietnam.gov.vn` đã trả 404.

| # | File | Nguồn tải | Có số Kim Long? |
|---|---|---|---|
| 1 | `dbqg_lutb_20200916_1600.pdf` | WB `20201027171639` · gốc `https://thoitietvietnam.gov.vn/upload/thuyvan2/2020/9/16/dbqg_lutb_20200916_1600.pdf` | Không. Chỉ là tin cảnh báo chung, dự báo sông Quảng Bình–TT Huế ở mức BĐ1–BĐ2 |
| 2 | `dbqg_lutb_20201031_2130.pdf` | WB `20201101050229` · gốc `https://thoitietvietnam.gov.vn//upload/thuyvan2/2020/10/31/dbqg_lutb_20201031_2130.pdf` | Không. Bản tin về sông Nghệ An, Hà Tĩnh |
| 3 | `dbqg_lutb_20201107_0930.pdf` | WB `20201111052705` · gốc `https://thoitietvietnam.gov.vn//upload/thuyvan2/2020/11/7/dbqg_lutb_20201107_0930.pdf` | Không. Bản tin về sông Quảng Nam |
| 4 | `dbqg_tvhn_20221010_1030.pdf` | **Gốc còn sống**: `https://kttv.gov.vn//upload/admin/2022/10/10/dbqg_tvhn_20221010_1030.pdf` | Có (bảng cao nhất/thấp nhất) |
| 5 | `dbqg_lutb_20221014_2100.pdf` | WB `20221014231032` · gốc `https://thoitietvietnam.gov.vn//upload/thuyvan2/2022/10/14/dbqg_lutb_20221014_2100.pdf` | Có |
| 6 | `dbqg_lutb_20221015_0330.pdf` | WB `20221014231029` · gốc `https://thoitietvietnam.gov.vn//upload/thuyvan2/2022/10/15/dbqg_lutb_20221015_0330.pdf` | Có |
| 7 | `dbqg_lutb_20221015_1000.pdf` | WB `20221015111020` · gốc `https://thoitietvietnam.gov.vn//upload/thuyvan2/2022/10/15/dbqg_lutb_20221015_1000.pdf` | Có |
| 8 | `dbqg_tvhn_20241125_1030.pdf` | `https://kttv.gov.vn//upload/thuyvan1/2024/11/25/dbqg_tvhn_20241125_1030.pdf` | Có |
| 9 | `dbqg_tvhn_20251030_1030.pdf` | `https://kttv.gov.vn//upload/thuyvan2/2025/10/30/dbqg_tvhn_20251030_1030.pdf` | Có |
| 10 | `dbqg_lulu_20251102_1930.pdf` | `https://kttv.gov.vn//upload/thuyvan2/2025/11/2/dbqg_lulu_20251102_1930.pdf` | Có (phụ lục dạng ảnh) |
| 11 | `dbqg_lulu_20251103_1530.pdf` | `https://kttv.gov.vn//upload/thuyvan2/2025/11/3/dbqg_lulu_20251103_1530.pdf` | Có (phụ lục dạng ảnh) |
| 12 | `dbqg_lulu_20251117_0230.pdf` | `https://kttv.gov.vn//upload/thuyvan2/2025/11/17/dbqg_lulu_20251117_0230.pdf` | Có (phụ lục dạng ảnh) |
| 13 | `dbqg_hghn_20261009_1500.pdf` | `https://kttv.gov.vn//upload/thuyvan1/2026/10/9/dbqg_hghn_20261009_1500.pdf` | Có |

## 4. Số liệu thực đo trích được

Giờ là giờ Việt Nam. Ngưỡng BĐ1/2/3: Kim Long 1,0/2,0/3,5 m, Phú Ốc 1,5/3,0/4,5 m. Cột "So BĐ" chép đúng như bản tin ghi. Số # ứng với bảng §3.

| Thời điểm | Trạm | H (m) | So BĐ (bản tin ghi) | Loại | Bản tin (#) |
|---|---|---|---|---|---|
| 24h trước bản tin 10h30 10/10/2022 | Kim Long | cao nhất 1,14 · thấp nhất 0,41 | — | cực trị 24h, không có giờ | TVHN-283 (#4) |
| 2022-10-14 19:00 | Kim Long | **2,48** | trên BĐ2 0,48 | thực đo | DBLU_33 21h00 (#5) |
| 2022-10-14 19:00 | Phú Ốc | 3,63 | trên BĐ2 0,63 | thực đo | #5 |
| 2022-10-15 01:00 | Kim Long | **3,75** | trên BĐ3 0,25 | thực đo | DBLU_35 03h30 (#6) |
| 2022-10-15 01:00 | Phú Ốc | 3,92 | dưới BĐ3 0,58 | thực đo | #6 |
| 2022-10-15 07:00 | Kim Long | **3,95** | trên BĐ3 0,45 | thực đo | DBLU 37 10h00 (#7) |
| 2022-10-15 07:00 | Phú Ốc | 4,62 | trên BĐ3 0,12 | thực đo | #7 |
| 2024-11-25 07:00 | Kim Long | **3,01** | dưới BĐ3 0,49 | thực đo, lũ đang lên. Bảng 24h qua: cao nhất 3,01, thấp nhất 1,10 | TVHN-330 (#8) |
| 2025-10-29 20:00 | Kim Long | **4,93** | bản tin ghi "trên BĐ3 0,43m" ⚠️ | **đỉnh**. Bảng 24h qua: cao nhất 4,93, thấp nhất 3,61 | TVHN-303 (#9) |
| 2025-10-29 18:00 | Phú Ốc | 5,27 | trên BĐ3 0,77 | **đỉnh** | #9 |
| 2025-11-02 19:00 | Kim Long | **3,49** | xấp xỉ BĐ3 (bảng ghi "< BĐ3 1" cm) | thực đo | DBLU_123 19h30 (#10) |
| 2025-11-03 13:00 | Kim Long | **4,47** | trên BĐ3 0,97 | **đỉnh** | DBLU_129 15h30 (#11) |
| 2025-11-03 13:00 | Phú Ốc | 5,31 | trên BĐ3 0,81, trên lũ lịch sử (5,27 m năm 2025) 0,04 | **đỉnh** | #11 |
| 2025-11-03 14:00 | Kim Long | 4,42 | trên BĐ3 0,92 | thực đo | #11 |
| 2025-11-03 14:00 | Phú Ốc | 5,29 | trên BĐ3 0,79 | thực đo | #11 |
| 2025-11-17 02:00 | Kim Long | **2,12** | trên BĐ2 0,12 | thực đo | DBLU_140 02h30 (#12) |
| 2025-11-17 02:00 | Phú Ốc | 4,43 | dưới BĐ3 0,07 | thực đo | #12 |
| 2026-10-08 19:00 | Kim Long / Phú Ốc | 0,97 / 1,44 | — | thực đo | 0910/DBQG_HGHN (#13) |
| 2026-10-09 01:00 | Kim Long / Phú Ốc | 1,12 / 1,47 | — | thực đo | #13 |
| 2026-10-09 07:00 | Kim Long / Phú Ốc | 0,81 / 1,41 | — | thực đo | #13 |
| 2026-10-09 13:00 | Kim Long / Phú Ốc | 0,93 / 1,41 | — | thực đo | #13 |

⚠️ **Lỗi đánh máy trong bản tin #9.** Đỉnh 4,93 m trừ BĐ3 3,50 m bằng **1,43 m**, nhưng bản tin ghi 0,43 m. Giá trị H 4,93 xuất hiện thống nhất ở cả lời văn lẫn bảng. Mọi dòng khác đều khớp phép trừ H − ngưỡng. Vì vậy **khi trích hàng loạt phải kiểm tra chéo H với độ chênh so với BĐ**.

**Đối chiếu với `data/external/flood_events.csv`:**
- Dòng `2025-10b` đang ghi 4,90 m, nguồn báo chí, độ tin cậy "thap". Bản tin #9 cho **4,93 m lúc 20h ngày 29/10/2025**, nên nâng được nguồn và độ tin cậy.
- Dòng `2024-11` ghi 3,10 m. Bản tin #8 cho 3,01 m lúc 07h, lũ đang lên, dự báo đạt đỉnh "dưới BĐ3 khoảng 0,4 m" (khoảng 3,1 m). Hai nguồn khớp nhau.
- **Hai sự kiện chưa có trong CSV:** lũ 10/2022 (≥ 3,95 m lúc 07h 15/10/2022, chưa có đỉnh) và lũ **03/11/2025** (đỉnh **4,47 m lúc 13h**). CSV không thuộc phần việc của file này, nên chỉ ghi đề xuất ở đây.
- Năm 2020: các mốc giờ đã có trong CSV lấy từ bài P2 (22h 9/10 3,09 m; 14h 17/10 3,31 m; 9h 15/11 2,03 m). Bản tin không bổ sung được gì cho năm này.

## 5. So dự báo chính thức với thực đo (chỉ từ các bản tin đã thử)

| Bản tin phát | Mốc dự báo | H dự báo (m) | H thực đo (m), lấy từ bản tin sau | Sai số (m) | Hạn tính từ giờ thực đo |
|---|---|---|---|---|---|
| 21h00 14/10/2022 (#5) | 01h 15/10 | 2,80 | 3,75 (#6) | −0,95 | 6 h |
| 21h00 14/10/2022 (#5) | 07h 15/10 | 3,10 | 3,95 (#7) | −0,85 | 12 h |
| 03h30 15/10/2022 (#6) | 07h 15/10 | 4,00 | 3,95 (#7) | +0,05 | 6 h |
| 19h30 02/11/2025 (#10) | 13h 03/11 | 4,40 | 4,47 (đỉnh, #11) | −0,07 | 18 h |

Bảng chỉ có 4 cặp, đủ để minh hoạ cách làm nhưng **chưa đủ để kết luận gì**. Nếu thu có hệ thống các bản tin 2024–2026 thì dựng được baseline "MAE dự báo chính thức theo hạn 6/12/18/24 h" để đặt mô hình của nhóm bên cạnh.

## 6. Liệt kê URL được không?

**Dạng URL quan sát được:**
```
https://kttv.gov.vn//upload/{thư_mục}/{YYYY}/{M}/{D}/dbqg_{mã}_{YYYYMMDD}_{HHMM}[hậu_tố].pdf
```
- `thư_mục` gặp: `thuyvan1`, `thuyvan2`, `admin`. Trước khoảng 2024, host là `thoitietvietnam.gov.vn`.
- `HHMM` gặp: 0230, 0330, 0900, 0930, 1000, 1030, 1215, 1500, 1530, 1600, 1930, 2100, 2130, 2330.
- `hậu_tố` gặp: `-1` (`dbqg_lulu_20251117_2100-1.pdf`), `-` (`dbqg_lutb_20221016_1530-.pdf`). Có cả file `.doc` (`dbqg_lutb_20221013_21000.doc`).
- Mã tin lũ đổi từ `lutb` (2020–2023) sang `lulu` (2024–2026). Cơ quan phát hành đổi từ "Tổng cục KTTV" sang "Cục KTTV" (bản tin 2025).

**Đoán URL theo mẫu không trúng lần nào:**
- 32 yêu cầu HEAD đoán `dbqg_lulu` cho 11–12/10/2020 và 14–15/10/2022 (2 thư mục × 4 giờ phát): 0 trúng. Trong khi đó file thật năm 2022 tồn tại với mã `lutb` trên host khác.
- 17 yêu cầu đoán `dbqg_hghn_*_1500` cho các ngày năm 2020, 2022, 2024, 2025: 0 trúng.

**Bản gốc còn hay mất không đều.** `dbqg_tvhn_20221010_1030` vẫn trả 200. `dbqg_lutb_20221015_0330` trả 404 trên cả `kttv.gov.vn` lẫn `thoitietvietnam.gov.vn`. `dbqg_lulu_20241001_2100` trả 404.

**Trang danh mục trên kttv.gov.vn** có phân trang `?pageindex=N`, mỗi bài `…-postNNNNN.html` chứa một link PDF. Danh mục chỉ giữ khoảng 1 năm:

| Chuyên mục | Tổng số mục (20/10/2026) | Mục cũ nhất |
|---|---|---|
| Thủy văn nguy hiểm › Lũ; Ngập lụt (`lu-ngap-lut-16-18.html`) | 191 | post51656, tức tin lũ 09h00 03/11/2025 |
| Thủy văn › Dự báo hạn ngắn (`du-bao-han-ngan-13-18.html`) | 295 | post52254 |
| Thủy văn chuyên đề (`thuy-van-chuyen-de-2067-18.html`, có bản tin `hghn`) | 957 | post52287 (bản tin đổ ải Đông Xuân) |

**Internet Archive CDX** (truy vấn 20/10/2026, gộp 2 host, đếm tên file duy nhất có bản lưu HTTP 200):

| Mã | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| `lutb` / `lulu` | 3 | 3 | 26 | 1 | 35 | 67 | 0 |
| `tvhn` | 0 | 0 | 1 | 0 | 90 | 122 | 15 |
| `hghn` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Trong lúc thử, Internet Archive có một lần trả "Temporarily Offline".

**Ước lượng số bản tin có số Kim Long mỗi năm** (suy từ số hiệu, chưa đếm đủ):
- TVHN khoảng 365 bản/năm. Cả 3/3 bản thử đều có dòng Kim Long, nhưng đều rơi vào mùa lũ, chưa kiểm mùa cạn.
- Tin lũ chỉ phát khi có lũ. Số hiệu DBLU đánh chung toàn quốc, đạt 33–37 vào 14–15/10/2022 và 123–140 vào 02–17/11/2025. Phần nói về Huế chỉ là một phần trong số đó.
- `hghn` khoảng 1 bản/ngày trong mùa lũ, mới thấy ở năm 2026.

## 7. Đánh giá và đề xuất

1. **Làm được ngay, miễn phí:** bảng `kim_long_bulletin_obs` gồm (thời điểm, trạm, H_m, loại thực đo/đỉnh/cực trị 24h, số hiệu bản tin, URL). Phạm vi 2024–2026 lấy từ danh mục kttv.gov.vn và CDX, cộng 10/2022 lấy từ CDX. Dùng để chấm **sai số đỉnh và lệch giờ đỉnh** của mô hình theo giờ trên tập test.
2. **Bảng dự báo chính thức** (từ Phụ lục 1 của tin lũ) dùng làm baseline. Phụ lục năm 2025 là ảnh, nên ưu tiên dạng chữ (`hghn`, `tvhn`, tin lũ ≤ 2023) trước.
3. **Không thay được chuỗi giờ liên tục.** Các năm 2020, 2021, 2023 gần như không có bản tin. Ngoài mùa lũ chỉ có cực trị 24h. Chuỗi giờ thật vẫn phải xin Đài KTTV (`email_kttv.md`).
4. Nếu sau này viết crawler (thuộc phần việc khác): tải danh mục rồi mới tải PDF, giãn cách giữa các yêu cầu, ghi URL nguồn vào từng dòng, kiểm chéo H − ngưỡng như cảnh báo ở §4. Đây là sản phẩm học thuật, không phải cảnh báo chính thức.

## 8. Tái lập

```bash
# tải 1 bản (gốc hoặc bản lưu Internet Archive)
curl -sL -A "Mozilla/5.0" -o x.pdf "https://kttv.gov.vn//upload/thuyvan2/2025/11/3/dbqg_lulu_20251103_1530.pdf"
curl -sL -o y.pdf "http://web.archive.org/web/20221014231029id_/https://thoitietvietnam.gov.vn//upload/thuyvan2/2022/10/15/dbqg_lutb_20221015_0330.pdf"
# liệt kê bản lưu theo mã
curl -s "http://web.archive.org/cdx/search/cdx?url=thoitietvietnam.gov.vn/upload/&matchType=prefix&filter=original:.*dbqg_.*&filter=statuscode:200&fl=timestamp,original&collapse=urlkey"
```
Đọc chữ bằng `fitz.open(pdf)[i].get_text()`. Phụ lục dạng ảnh thì render bằng `page.get_pixmap(dpi=130)` rồi đọc bằng mắt.
