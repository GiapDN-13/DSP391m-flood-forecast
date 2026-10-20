# NGUỒN SỐ LIỆU ĐO THẬT THEO GIỜ — mực nước Kim Long, Phú Ốc và mưa trạm lưu vực sông Hương

**Khảo sát ngày 20/10/2026.** Mục đích: tìm số liệu **thực đo theo giờ** để thay hoặc kiểm chứng biến mục tiêu hiện tại, là lưu lượng GloFAS v4 **mô phỏng, theo ngày, ô khoảng 5 km**. Đây là hướng thầy yêu cầu: ô mịn hơn và bước thời gian theo giờ.

Phạm vi của thư mục này gồm khảo sát nguồn, soạn email xin dữ liệu và thử đọc bản tin. **Chưa có code ingest, chưa gửi email, chưa đăng ký tài khoản nào.**

| File | Nội dung |
|---|---|
| `README.md` | Bảng nguồn, khuyến nghị, thủ tục pháp lý, đầu mối liên hệ, danh sách trạm Vrain |
| `email_kttv.md` | Email (a) gửi Đài KTTV: H giờ Kim Long, Phú Ốc và mưa trạm KTTV |
| `email_watec_vrain.md` | Email (b) gửi WATEC: lịch sử mưa các trạm Vrain |
| `kttv_bulletins_probe.md` | Thử 13 bản tin thủy văn, trích số Kim Long kèm giờ và URL, đánh giá khả năng liệt kê |

## 1. Bảng nguồn đo thật theo giờ

| ID | Nguồn | Đơn vị giữ số liệu | Loại số liệu | Bước thời gian | Giai đoạn có số liệu | Cách lấy | Chi phí | Trạng thái 20/10/2026 |
|---|---|---|---|---|---|---|---|---|
| **K1** | Trạm thủy văn **Kim Long** (sông Hương) và **Phú Ốc** (sông Bồ) | Mạng trạm quốc gia, do **Đài KTTV Trung Bộ** (Đà Nẵng) quản lý; **Đài KTTV TP Huế** trực thuộc. Cơ sở dữ liệu quốc gia: **Trung tâm Thông tin và Dữ liệu KTTV** (Cục KTTV, Bộ NN&MT) | Mực nước H (cm), mưa | **Giờ.** Biểu phí có mục "Biểu H, Q giờ mùa lũ". Cục KTTV trả lời công khai rằng có các bước 1h, 4h, 6h và ngày | Kim Long **1977–**, Phú Ốc **1976–** (bài P2, Bảng 2) | Phiếu hoặc văn bản yêu cầu (Mẫu 04, NĐ 38/2016), xem §3 | Có thu phí, 280–300 nghìn đ/trạm/năm tài liệu (§3) | Email (a) đã soạn, **chưa gửi** |
| **K2** | Trạm thủy văn **Thượng Nhật** (sông Tả Trạch) | Như K1 | H, mưa, **lưu lượng Q đo thật** | Chưa rõ | 1979– (bài P2) | Như K1 | Như K1 | Đã gộp vào email (a) |
| **K3** | Trạm khí tượng **Huế, A Lưới, Nam Đông** | Như K1 | Mưa (biểu phí có mục "Lượng mưa từng giờ") | Giờ | Bài P2 dùng chuỗi 1981–2020 | Như K1 | 200 nghìn đ/trạm/năm | Đã gộp vào email (a) |
| **K4** | **Bản tin thủy văn công khai** trên kttv.gov.vn, kèm bản lưu Internet Archive | Trung tâm Dự báo KTTV quốc gia | H Kim Long và Phú Ốc tại giờ bản tin, đỉnh và giờ đỉnh, **dự báo chính thức** 6–24h | Không liên tục, tối đa 6 giờ/lần trong mùa lũ | **2024–2026 tốt**, 2022 một phần, **2020 không có** | Tải PDF công khai | Miễn phí | **Đã thử 13 bản** (`kttv_bulletins_probe.md`) |
| **V1** | **Vrain** (mưa tự động) | **CTCP Tư vấn và Phát triển kỹ thuật Tài nguyên nước (WATEC)**, Đà Nẵng. Trạm đặt tại hồ chứa, Phòng NN&PTNT, đồn biên phòng của tỉnh (bài P2, Bảng 3) | Lượng mưa | Trang web công khai **chỉ hiện trạng thái hiện tại**. Lịch sử nằm sau API `/private/` (cần token đăng nhập của tổ chức) | Theo từng trạm. Có 22 trạm ở TT Huế vào năm 2022 (P2). Báo chí ghi đỉnh Bạch Mã "có số liệu quan trắc từ năm 2022", chưa rõ đó có phải trạm Vrain không | Xin qua email WATEC, có thể CC Chi cục Thủy lợi TP Huế | Chưa rõ | Email (b) đã soạn, **chưa gửi** |
| **H1** | **Hue-S** (ứng dụng đô thị thông minh Huế) | Trung tâm Giám sát, điều hành đô thị thông minh (IOC) Huế. Tên này lấy theo báo chí; **đơn vị chủ quản năm 2026 chưa xác minh** | H tại **cầu Dã Viên**, cách trạm Kim Long khoảng 1 km về hạ lưu; tại **cầu Tứ Phú**, cách Phú Ốc khoảng 1 km về hạ lưu; mưa trạm (tờ rơi lấy ví dụ trạm Quảng Phú, trạm này cũng có trên Vrain); tháp báo lũ | App vẽ biểu đồ theo giờ | Không rõ | **Chỉ xem trong app.** Không thấy web hoặc API công khai | — | Chưa liên hệ |
| **D1** | Cổng dữ liệu mở TP Huế `data.hue.gov.vn` | Sở KH&CN TP Huế | Chưa rõ | — | — | Trang tìm kiếm tải nội dung động, **chưa kiểm tra được** có bộ dữ liệu thủy văn không | — | Chưa kiểm |

**Ghi chú quan trọng:**
- Tờ rơi CRMC 2025 của Chi cục Thủy lợi TP Huế ghi nguyên văn: *"Hiện nay, hai trạm thủy văn Kim Long và Phú Ốc chưa được kết nối và chia sẻ trực tuyến theo thời gian thực."* Vì vậy **số liệu giờ ở đúng trạm có ngưỡng báo động chỉ xin được từ ngành KTTV (K1)**. Dã Viên và Tứ Phú (H1) là điểm đo khác, chỉ "có thể xem là tương đương".
- Đo trên bản đồ công khai Vrain lúc 17:43 ngày 20/10/2026 (tệp `data.vrain.vn/public/current/all.json`):
  - toàn quốc **2 584 trạm**;
  - **67 trạm** trong `FINE_BBOX` (15,8–16,8°N, 107,0–108,0°E);
  - **50 trạm** trong vùng 64 ô ERA5 của repo, phủ **33/64 ô** (làm tròn toạ độ về 0,1°).
  - Tệp chỉ có các trường tên, toạ độ, lượng mưa hiện tại và mức mưa, **không có lịch sử**.
- Theo trang `kttvttb.vn`, Đài KTTV khu vực Trung Trung Bộ có Phòng Thông tin và Dữ liệu KTTV, làm nhiệm vụ *"quản lý, lưu trữ, khai thác cơ sở dữ liệu khí tượng thủy văn"*. Tuy nhiên, ngày 20/10/2026 trang này có chèn liên kết quảng cáo cá cược ở chân trang, nên **không dùng địa chỉ email lấy từ đó**. Đơn vị này nay mang tên **Đài KTTV Trung Bộ** (QĐ 2437/QĐ-BNNMT).

## 2. Khuyến nghị ưu tiên

1. **Làm ngay, không phụ thuộc ai (K4).** Dựng bảng *"H Kim Long tại giờ bản tin"* cho 2024–2026, cộng thêm 10/2022 lấy qua Internet Archive. Bảng dùng để **kiểm chứng đỉnh và giờ đỉnh** của mô hình theo giờ trên tập test (≥ 2022-07-01), và làm **baseline dự báo chính thức** theo hạn 6/12/18/24h. Bảng **không thay được** chuỗi giờ liên tục. Chi tiết ở `kttv_bulletins_probe.md` §7.
2. **Gửi email (a) cho Đài KTTV (K1–K3) sớm nhất có thể.** Đây là nguồn duy nhất có chuỗi giờ liên tục, dài hạn, tại đúng trạm Kim Long. Có phí, cần Mẫu 04 và giấy giới thiệu của Trường, chờ khoảng 3–6 tuần. Phần tối thiểu cần xin: **H giờ mùa lũ Kim Long 2015–2025**. Nếu được thì xin thêm Thượng Nhật (có Q đo thật), dùng cho đường R1 trong `docs/THRESHOLDS.md`.
3. **Gửi email (b) cho WATEC song song (V1).** Mạng trạm dày, đủ để kiểm chứng và hiệu chỉnh mưa ERA5 0,1° theo giờ. Chuỗi Vrain ngắn (trạm mới nhiều), nên chỉ hợp cho tập valid và test, hoặc cho phân tích sai số ERA5.
4. **Hue-S (H1) là phương án dự phòng.** Chỉ hỏi IOC Huế về chuỗi Dã Viên và Tứ Phú khi email (a) bị từ chối.
5. **Không tự thu lịch sử Vrain** qua API web. Endpoint lịch sử thuộc nhóm `/private/` và cần token đăng nhập, nên phải đi đường xin phép.
6. Gắn với Report 4: chuỗi đo thật có dung lượng nhỏ, đóng vai trò **nhãn và thước đo kiểm chứng**. Phần dữ liệu lớn, cần xử lý phân tán, vẫn là lưới mưa ERA5 theo giờ.

## 3. Thủ tục pháp lý xin số liệu KTTV (tóm tắt, có nguồn)

- **Luật KTTV 90/2015/QH13, Điều 32.** Khoản 4: khai thác thông tin, dữ liệu KTTV **phải trả phí**, trừ các trường hợp ở khoản 5. Khoản 5 chỉ miễn phí cho **cơ quan nhà nước** với các mục đích: thông báo trên phương tiện đại chúng không vì lợi nhuận; phòng chống thiên tai, quốc phòng, an ninh; trao đổi với nước ngoài theo điều ước; mục đích khác theo yêu cầu của cơ quan có thẩm quyền. Như vậy **không có miễn phí cho sinh viên hay mục đích học tập**.
- **NĐ 38/2016/NĐ-CP.** Văn bản này đã được sửa đổi bởi NĐ 48/2020, 22/2023, 136/2025 và 113/2026, có bản hợp nhất 50/VBHN-BNNMT năm 2026. Các điểm chính theo bản gốc:
  - Điều 22 khoản 4: dữ liệu khai thác không phải trả phí thì *"không được sử dụng vào mục đích lợi nhuận"*.
  - Điều 26: người yêu cầu *"nộp phiếu yêu cầu hoặc gửi văn bản yêu cầu"*; *"thời hạn cung cấp … do các bên thỏa thuận"*; nếu từ chối phải có văn bản nêu lý do.
  - Mẫu số 04 gồm thông tin người yêu cầu, danh mục dữ liệu, mục đích, hình thức nhận và cam kết. Cá nhân ký tên; tổ chức thì thủ trưởng ký và đóng dấu.
  - Các điều khoản trên đọc từ bản gốc trên caselaw.vn, **chưa đối chiếu với bản hợp nhất 2026**.
- **Phí: TT 197/2016/TT-BTC** (sửa bởi TT 55/2018/TT-BTC, hợp nhất 16/VBHN-BTC năm 2019).
  - Tổ chức thu phí gồm Trung tâm Quan trắc KTTV, Trung tâm Thông tin và Dữ liệu KTTV, Liên đoàn Khảo sát KTTV và các Đài KTTV khu vực.
  - Mức thu tính *"cho 1 lần khai thác"*, đơn vị là *"1 năm"* tài liệu:
    - mục 5.1 l) *"Biểu H (mực nước), Q (lưu lượng nước) giờ mùa lũ"*: **280 nghìn đ**;
    - mục 6.1 i), vùng sông ảnh hưởng triều, *"Biểu H, Q giờ mùa lũ, cạn"*: **300 nghìn đ**;
    - mục 1.14 a) *"Lượng mưa từng giờ"*: **200 nghìn đ**.
  - TT 36/2020/TT-BTC giảm phí 30%, nhưng chỉ áp dụng từ 05/5 đến 31/12/2020.
  - Tra ngày 20/10/2026, **chưa tìm thấy văn bản thay thế** TT 197/2016. Cần hỏi lại khi gửi yêu cầu.
- **Trang hỏi đáp chính thức của Cục KTTV** (câu hỏi ngày 21/07/2026): số liệu trạm *"generally begin from 1977"*; tần suất *"hourly or at standard observation intervals (1h, 4h, 6h, etc.), daily"*; có thu phí; đầu mối là **Trung tâm Thông tin và Dữ liệu KTTV hoặc Đài KTTV khu vực**. Trang này có ghi tên và email người phụ trách, xem tại link ở §6.
- **Tổ chức ngành.** QĐ 2437/QĐ-BNNMT ngày 30/06/2025, hiệu lực từ 01/07/2025, quy định **Đài KTTV Trung Bộ** thuộc Cục KTTV, trụ sở tại Đà Nẵng, phụ trách 9 tỉnh/thành trong đó có Huế. Cơ cấu gồm Phòng Thông tin, dữ liệu KTTV và **Đài KTTV TP Huế**. QĐ này thay thế QĐ 743/QĐ-BNNMT.

## 4. Đầu mối liên hệ (đều lấy từ nguồn công khai, cần xác minh lại trước khi gửi)

| Đơn vị | Thông tin | Nguồn |
|---|---|---|
| Cục Khí tượng Thủy văn | 24 Huỳnh Thúc Kháng, Hà Nội · 19001260 · `kttv@mae.gov.vn` | Chân trang vnmha.mae.gov.vn |
| Trung tâm Dự báo KTTV quốc gia (đơn vị phát bản tin) | Tầng 12, số 24 Huỳnh Thúc Kháng, Hà Nội · `vtttkttv@mae.gov.vn` | Chân trang nchmf.gov.vn |
| Đài KTTV Trung Bộ | 660 Trưng Nữ Vương, Hải Châu, Đà Nẵng | kttvttb.vn. Trang có chèn spam nên chỉ lấy địa chỉ; hỏi email qua Cục |
| WATEC (Vrain) | 299 Huỳnh Ngọc Huệ, Hòa Khê, Thanh Khê, Đà Nẵng · 02363.711.364 · `tainguyennuoc@watec.vn` | watec.vn |
| Chi cục Thủy lợi và BĐKH TP Huế | 0234 382 2519 / 0234 384 9123 | Tờ rơi CRMC 2025 |
| Hue-S | Hotline 19001075 | Tờ rơi CRMC 2025 |

## 5. Phụ lục: trạm mưa Vrain lưu vực sông Hương

Bảng ghép **nhóm theo lưu vực hồ trong tờ rơi CRMC 2025** với **tên đầy đủ và toạ độ trên bản đồ công khai Vrain** (20/10/2026). Nhóm "Hạ du / TP Huế" chọn theo toạ độ, **chưa xác minh ranh giới lưu vực**.

| Nhóm (tờ rơi) | Tên trong tờ rơi | Tên trên Vrain | Lat, Lon |
|---|---|---|---|
| Hồ Hương Điền | Tà Lương | Tà Lương (A Lưới) | 16.3011, 107.3358 |
| Hồ Hương Điền | A Lưới | Thị trấn A Lưới (A Lưới)\* | 16.2722, 107.2325 |
| Hồ Hương Điền | Rào Trăng 3 | Đập Thủy điện Rào Trăng 3 (Phong Điền) | 16.4094, 107.2494 |
| Hồ Hương Điền | Rào Trăng 4 | Đập Thủy điện Rào Trăng 4 (Phong Điền) | 16.3972, 107.2981 |
| Hồ Hương Điền | Hương Bình | — không thấy trên Vrain | — |
| Hồ Hương Điền, Hồ Bình Điền | Bình Tiến | Bình Tiến (Hương Trà) | 16.3519, 107.4472 |
| Hồ Hương Điền | A Đớt | A Đớt (A Lưới) | 16.0769, 107.3703 |
| Hồ Bình Điền | Bình Điền | Thủy điện Bình Điền (Hương Trà) | 16.3164, 107.5014 |
| Hồ Bình Điền | Hương Nguyên | Hương Nguyên (A Lưới) | 16.0811, 107.4853 |
| Hồ A Lưới, A Lin | Nhâm | Nhâm (A Lưới) | 16.2211, 107.1794 |
| Hồ A Lưới, A Lin | hồ A Lá | Hồ A Lá (A Lưới) | 16.2603, 107.2450 |
| Hồ A Lưới, A Lin | Hồng Vân | Hồng Vân (A Lưới) | 16.3619, 107.1247 |
| Hồ Tả Trạch | Bạch Mã | Bạch Mã · Đỉnh Bạch Mã (Phú Lộc) · Vườn Quốc gia Bạch Mã (Phú Lộc) | 16.2510, 107.8733 · 16.1997, 107.8575 · 16.2273, 107.8558 |
| Hồ Tả Trạch | Khe Tre | TT Khe Tre (Phú Lộc) | 16.1683, 107.7189 |
| Hồ Tả Trạch | Hương Sơn | Hương Sơn (Phú Lộc) | 16.1696, 107.6813 |
| Hồ Tả Trạch | Xuân Lộc | Xuân Lộc (Phú Lộc) | 16.2619, 107.7033 |
| Hồ Tả Trạch | Thượng Quảng | Thượng Quảng (Phú Lộc) | 16.1229, 107.6307 |
| Hồ Tả Trạch | Thượng Nhật | Lưu vực Thủy điện Thượng Nhật (Phú Lộc) · Đập, Thủy điện Thượng Nhật (Phú Lộc) | 16.1011, 107.6956 · 16.1228, 107.6944 |
| Hạ du / TP Huế | (ví dụ trong tờ rơi: Quảng Phú) | Quảng Phú (Quảng Điền) | 16.5308, 107.4919 |
| Hạ du / TP Huế | — | Hồ chứa nước Khe Ngang | 16.4308, 107.5057 |
| Hạ du / TP Huế | — | Hồ Thọ Sơn (Hương Trà) | 16.4767, 107.4783 |
| Hạ du / TP Huế | — | Hương Chữ (Hương Trà) | 16.4914, 107.5208 |
| Hạ du / TP Huế | — | VP QLKTCTTL TP Huế (TP Huế) | 16.4897, 107.5551 |
| Hạ du / TP Huế | — | Quan Tượng Đài (Phú Xuân) | 16.4622, 107.5708 |
| Hạ du / TP Huế | — | An Tây (Thuận Hóa) | 16.4336, 107.5975 |
| Hạ du / TP Huế | — | Phú Sơn (Hương Thủy) | 16.3390, 107.6710 |
| (gần nhóm A Lưới, theo toạ độ) | — | Hồng Thái (A Lưới) | 16.2398, 107.2416 |

\* "Trạm A Lưới" trong tờ rơi có thể là trạm khí tượng A Lưới của ngành KTTV (K3) chứ không phải trạm Vrain. Ở đây tạm ghép với trạm Vrain "Thị trấn A Lưới".

## 6. Nguồn (truy cập 20/10/2026)

- Tờ rơi *Tiếp cận thông tin cảnh báo mưa, lũ tại thành phố Huế* (2025), Chi cục Thủy lợi và BĐKH TP Huế, CRMC/ZCRA: https://i-s-e-t.org/wp-content/uploads/CRMC-Leaflet-Access-to-rain-and-flood-warning-information-in-Hue-City-VN.pdf ; bản poster: https://i-s-e-t.org/wp-content/uploads/CRMC-Poster-Access-to-rain-and-flood-warning-information-in-Hue-City-VN.pdf
- Bài P2: Nguyễn Hoàng Sơn và cộng sự (2022), Tạp chí Khoa học ĐH Huế 131(4A), Bảng 2 (trạm thủy văn) và Bảng 3 (22 trạm Vrain): https://jos.hueuni.edu.vn/index.php/hujos-ese/article/download/6519/1880/31346
- Vrain: https://vrain.vn ; tệp công khai `https://data.vrain.vn/public/current/all.json` và `.../summary.json` ; WATEC: https://watec.vn
- QĐ 2437/QĐ-BNNMT (Đài KTTV Trung Bộ): https://luatvietnam.vn/tai-nguyen/quyet-dinh-2437-qd-bnnmt-405397-d1.html
- Luật KTTV 90/2015/QH13, Điều 32: https://hethongphapluat.com/law-no-90-2015-qh13-dated-november-23-2015-hydrometeorology/dieu-32
- NĐ 38/2016/NĐ-CP: https://caselaw.vn/van-ban-phap-luat/116618-nghi-dinh-38-2016-nd-cp-huong-dan-luat-khi-tuong-thuy-van ; NĐ 113/2026/NĐ-CP: https://luatvietnam.vn/tai-nguyen/nghi-dinh-113-2026-nd-cp-sua-doi-nghi-dinh-38-2016-nd-cp-ve-luat-khi-tuong-thuy-van-430789-d1.html ; bản hợp nhất 50/VBHN-BNNMT: https://luatvietnam.vn/tai-nguyen/van-ban-hop-nhat-50-vbhn-bnnmt-2026-quy-dinh-chi-tiet-luat-khi-tuong-thuy-van-433121-d5.html
- Biểu phí, bản hợp nhất 16/VBHN-BTC (TT 197/2016 + TT 55/2018): https://caselaw.vn/van-ban-phap-luat/339893-van-ban-hop-nhat-so-16-vbhn-btc-ngay-22-01-2019-cua-bo-tai-chinh-hop-nhat-thong-tu-quy-dinh-ve-muc-thu-che-do-thu-nop-quan-ly-va-su-dung-phi-khai-thac-su-dung-thong-tin-du-lieu-khi-tuong-thuy-van
- Hỏi đáp Cục KTTV về cung cấp số liệu trạm: https://vnmha.mae.gov.vn/chi-tiet-hoi-dap-12.htm
- Đài KTTV khu vực Trung Trung Bộ, trang Phòng Thông tin và Dữ liệu: https://kttvttb.vn/phong-thong-tin-du-lieu-kttv/ (lưu ý chèn spam, xem §1)
- Bản tin thủy văn: https://kttv.gov.vn/kttv/vi-VN/1/lu-ngap-lut-16-18.html ; https://kttv.gov.vn/kttv/vi-VN/1/du-bao-han-ngan-13-18.html ; danh sách URL cụ thể trong `kttv_bulletins_probe.md`
- Hue-S và IOC Huế (báo chí): https://vietnamnet.vn/hue-s-ung-dung-hieu-qua-ve-canh-bao-ngap-lut-thien-tai-2226677.html ; https://nhandan.vn/ocop/thich-ung-qua-mua-lu-nho-ung-dung-hue-s-post783503.html
- Cổng dữ liệu mở TP Huế: https://data.hue.gov.vn
