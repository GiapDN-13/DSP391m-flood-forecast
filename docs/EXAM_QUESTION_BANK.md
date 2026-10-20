# NGÂN HÀNG CÂU HỎI VẤN ĐÁP

Thi cuối kỳ **chấm cá nhân, 30 phút, 20 % điểm**. Mỗi người phải trả lời được **toàn bộ**, kể cả phần mình không làm.

Cách dùng: gặp khái niệm mới trong tuần → thêm 1 câu vào đây. Mock exam ở **W6** và **W9**, mỗi người bốc 3 câu.
Ghi kết quả mock vào bảng cuối file.

---

## A. Bài toán & dữ liệu

1. Vì sao chọn Huế mà không phải nơi khác? Dẫn chứng gì?
2. GloFAS là gì? Dữ liệu là **quan trắc** hay **mô phỏng**? Điều đó ảnh hưởng kết luận thế nào?
3. Vì sao phải tách train/test tại mốc **07/2022**? Nếu không tách thì sai ở đâu?
4. Độ phân giải ~5 km có ý nghĩa gì với một xã rộng vài km²?
5. ERA5 là gì, khác dữ liệu trạm đo ở điểm nào?
6. Dữ liệu trễ ~5 ngày thì chạy dự báo hằng ngày kiểu gì?
7. Giấy phép Open-Meteo là gì? Trích dẫn ra sao?
8. Xử lý giá trị thiếu thế nào? Vì sao chọn cách đó mà không nội suy?
9. Mưa giờ gộp thành ngày theo múi giờ nào? UTC hay ICT? Vì sao quan trọng?

## B. Đặc trưng & mô hình

10. Lag feature là gì? Vì sao chọn lag tối đa 7 ngày cho mưa, 14 ngày cho discharge?
11. API (antecedent precipitation index) là gì, dùng để làm gì?
12. Vì sao chọn LightGBM làm mô hình chính thay vì LSTM?
13. Persistence baseline là gì? Vì sao bắt buộc phải có baseline?
14. **Mô hình của nhóm tốt hơn dự báo GloFAS gốc ở điểm nào?** *(câu chắc chắn bị hỏi — trả lời theo `RESEARCH_DESIGN.md` §1)*
14b. GloFAS vừa là baseline vừa là feature đầu vào — như vậy có phải gian lận không? Vì sao không?
14c. Ngưỡng BĐ I/II/III định nghĩa theo mực nước, dữ liệu lại là lưu lượng — nhóm quy đổi bằng cách nào, và cách đó có hạn chế gì?
15. Walk-forward validation khác k-fold thường ở chỗ nào? Vì sao không được dùng k-fold ở đây?
16. Rò rỉ dữ liệu (data leakage) trong chuỗi thời gian xảy ra như thế nào? Nhóm phòng bằng cách nào?
17. Optuna tối ưu gì, theo metric nào, bao nhiêu trial?

## C. Đánh giá

18. NSE là gì, giá trị bao nhiêu thì coi là tốt? NSE = 0 nghĩa là gì?
19. Vì sao **không** báo cáo accuracy cho bài toán phân loại ngày lũ?
20. POD, FAR, CSI là gì? Đánh đổi giữa chúng ra sao?
21. Nếu phải chọn giữa recall cao và precision cao cho cảnh báo lũ, chọn cái nào? Vì sao?
22. Mô hình sai nhiều nhất ở tình huống nào? Có cắt ngọn đỉnh lũ không?
23. SHAP cho biết điều gì? Feature nào quan trọng nhất, có hợp lý về mặt thuỷ văn không?

## D. Sản phẩm & ứng dụng

24. Dashboard dành cho ai? Họ dùng như thế nào?
25. Nếu mô hình báo động sai, hậu quả là gì? Nhóm ghi disclaimer thế nào?
26. Pipeline chạy hằng ngày ra sao? Nếu API chết thì sao?
27. Khuyến nghị cụ thể cho địa phương là gì? *(phải nêu được xã, ngưỡng, thời gian cảnh báo)*

## E. Hạn chế & hướng phát triển

28. Ba hạn chế lớn nhất của dự án là gì?
29. Mô hình train bằng mưa quan trắc nhưng chạy bằng mưa dự báo — vấn đề gì phát sinh?
30. Có thêm 6 tháng nữa thì làm gì tiếp?

## F. Yêu cầu & nghiệm thu

34. Dự án có bao nhiêu yêu cầu bắt buộc? Cái nào chưa đạt và vì sao?
35. Ngưỡng nghiệm thu NSE ≥ 0,5 và POD ≥ 0,7 lấy căn cứ từ đâu?
36. Yêu cầu phi chức năng nào khó đạt nhất? Nhóm xử lý thế nào?
37. Làm sao chứng minh một con số trong Report 3 là có thật và tái lập được?

## G. Câu hỏi về quy trình làm việc

31. Bạn phụ trách phần nào? Phần **người khác** làm hoạt động ra sao?
32. Nhóm phối hợp qua công cụ gì? Xử lý bất đồng thế nào?
33. Rủi ro lớn nhất nhóm gặp phải và cách vượt qua?


## H. Bổ sung 21/10/2026: phát hiện mới cho Report 3–4

> Nguồn: `FINDINGS_HOURLY_FINEGRID.md` (**FHF**), `FINDINGS_FACTORS.md` (**FF**), `FINDINGS_GRID.md` (**FG**), `FINDINGS_SHAP.md` (**FS**), `reports/report3/OUTLINE_VI.txt` (**OUT**), `src/ingest/gsmap_nrt.py`, `infra/spark/README.md` (**SPK**), `docs/data_requests/README.md` (**DR**).
>
> Nhãn vai (theo `docs/TEAM.md`, chỉ dựa trên phân công công việc) để biết ai nên ôn câu nào trước — thi chấm cá nhân nên **ai cũng phải trả lời được tất cả**.
> **[TL]** Tech Lead (Đặng Nguyên Giáp) · **[DA]** Data Analyst (Hồ Anh Đức) · **[RD]** Research & Docs (Mai Thị Lệ Huyền) · **[BẪY]** câu dễ bị hỏi vặn.
>
> Lưu ý thuật ngữ: "R1" có 3 nghĩa — rủi ro ô lưới (`RISKS.md`), đường H–Q thực đo của KTTV đã loại 15/09 (`THRESHOLDS.md`), và phép thử "GloFAS có mô phỏng hồ không" (FF). Khi nói phải gọi rõ tên.
>
> Câu 35 ở trên đã lỗi thời: SPEC AC-1 (15/09) là h1 ≥ 0,70 kèm RMSE tốt hơn persistence ≥ 20 %, h2 ≥ 0,40, h3 ≥ 0,25.

### H1. Biến mục tiêu: theo giờ và ô mịn hơn

**38. Thầy yêu cầu theo giờ, sao biến mục tiêu vẫn là lưu lượng GloFAS theo ngày?** [TL] [RD]
- **Trả lời:** Mục tiêu theo giờ tại đúng trạm cần mực nước giờ Kim Long của ngành KTTV; hai trạm Kim Long, Phú Ốc "chưa được kết nối và chia sẻ trực tuyến", chỉ xin được qua Đài KTTV (DR §1). Nhóm quyết định không xin (câu 39), nên mục tiêu vẫn là GloFAS v4 theo ngày, ô ~5 km (16,45; 107,50). "Theo giờ" được đưa vào đầu vào: 54 đặc trưng mưa giờ (FHF §1, §4).
- **Hỏi vặn:** *"Mục tiêu theo ngày thì đặc trưng giờ dùng làm gì?"* → Tóm phân bố mưa trong ngày (max 1h/3h/6h, số giờ ≥ 1 mm, giờ đỉnh, mưa 24h tới 07h…) thành thông tin cho Q ngày; có ích ở h3 với cả 3 seed (FHF §4).

**39. Sao nhóm không xin số liệu đo của KTTV?** [RD] [TL]
- **Trả lời:** Luật KTTV 90/2015 Điều 32: khai thác dữ liệu phải trả phí, không miễn cho sinh viên. Biểu phí TT 197/2016: 280–300 nghìn đ/trạm/năm tài liệu cho "Biểu H, Q giờ mùa lũ" — ước ~6,2–6,6 triệu đ cho 2 trạm × 11 năm (DR §3; số ước ‡). Thủ tục Mẫu 04 (NĐ 38/2016) + giấy giới thiệu Trường, chờ 3–6 tuần — không hợp lịch. Email nháp ở `docs/data_requests/`, không gửi.
- **Hỏi vặn [BẪY]:** *"Bản tin KTTV miễn phí, sao không làm mục tiêu?"* → Không liên tục (dày nhất 6 giờ/lần mùa lũ; 2024–2026 đủ, 2022 một phần, 2020 không có) — chỉ dùng kiểm chứng đỉnh và giờ đỉnh (DR §1, §2).

**40. "Ô mịn hơn 5 km": vì sao chỉ áp được cho đầu vào?** [TL] [DA]
- **Trả lời:** Mục tiêu là lưu lượng tại một ô sông GloFAS v4; mục tiêu mịn hơn cần mô hình thuỷ văn lưới mịn hơn hoặc số đo trạm — ngoài dữ liệu mở (FHF §1). Nhóm làm hai việc: gộp mưa theo ranh giới lưu vực cắt từ DEM 30 m thay cho 3 dải vĩ độ, và thử PERSIANN-CCS 0,04° (~4 km) — nguồn duy nhất mịn hơn 5 km; IMERG, GSMaP là 0,1° (~11 km) (FHF §2, §3).
- **Hỏi vặn:** *"Mưa mịn hơn có giúp không?"* → B0 (tổng ngày theo lưu vực DEM) h1 0,726 so với A 0,715, ngang B và C có thông tin giờ (FHF §4).

**41. Sao loại PERSIANN-CCS dù nó mịn nhất?** [TL] [DA]
- **Trả lời:** Tháng 11/2020 chỉ ghi được 0,073 lượng mưa ERA5 (49 so với 672 mm), dù tháng 10 là 1,214. Lý giải (‡): thuật toán bỏ mây ấm, mà mưa gió mùa đông bắc ở Huế đến từ mây thấp (FHF §2). Mất gần hết mưa đúng mùa lũ chính thì không dùng một mình được.
- **Hỏi vặn:** *"Lấy ERA5 làm mốc thì sao biết nguồn nào đúng?"* → Không biết được: ERA5 cũng hụt mưa địa hình (11/2024: 332 mm so với 500–800 mm trên núi); phân xử cần mưa trạm (FHF §2; FF §1).

**42. Đặc trưng mưa giờ giúp được gì (A/B0/B/C)?** [DA] [TL]
- **Trả lời:** NSE test: A 0,715/0,416/0,168; B 0,723/0,431/0,183; C 0,722/0,429/0,184 (FHF §4). Chỉ chắc ở h3 (3/3 seed); h2 gần như chỉ do một seed; h1 không đến từ thông tin trong ngày (B0 đã 0,726).
- **Hỏi vặn [BẪY]:** *"Sao A ở đây 0,715 mà Report 2 là 0,747?"* → Split riêng train 2015–2020 vì ERA5 giờ chỉ có từ 2015; không so trực tiếp (FHF §4).

**43. Lưu vực con từ DEM có đáng công không?** [TL]
- **Trả lời:** 5 lưu vực con (Tả Trạch 670, Bình Điền 507, hai đoạn dưới đập 88 và 185, Tuần–Kim Long 93 km²), pysheds D8 trên Copernicus GLO-30 (FHF §3). Với mô hình thì không: 45 cột lưu vực con ≈ 9 cột toàn lưu vực vì mưa giữa các lưu vực con tương quan cao (FHF §4, §12.1). Giá trị thật: diện tích đúng và trọng số ô theo ranh giới thật.
- **Hỏi vặn:** *"Kiểm thuật toán cắt lưu vực thế nào?"* → Hai thuật toán độc lập khớp đúng 1 684 710 pixel (tích luỹ pysheds tại cửa ra = mặt nạ BFS) (FHF §3).

**44. Làm sao chắc đặc trưng giờ không rò rỉ và đúng ranh giới ngày?** [DA] [TL]
- **Trả lời:** 64 ô × 366 ngày năm 2020: tổng nhãn 00–23h trùng mưa ngày, lệch lớn nhất 1,7e-13 mm; dời ±1 giờ thì lệch 27,5–47,5 mm. Cắt dữ liệu giờ tại 3 mốc rồi tính lại: mọi ngày trước mốc không đổi ô nào (FHF §4).
- **Hỏi vặn:** *"Nhãn giờ các nguồn có giống nhau không?"* → Không: ERA5/PERSIANN ghi cuối giờ, Earth Engine ghi đầu khoảng — đã dời 692 file (+30 phút IMERG, +60 phút GSMaP) để thống nhất cuối khoảng (FHF §2).

### H2. Diện tích lưu vực và ô lưới

**45. Vì sao đính chính diện tích 2 830 → ~1 540 km²?** [TL] [RD]
- **Trả lời:** 2 830 km² là cả hệ thống sông Hương, đã gồm sông Bồ 938 km² (UNESCO-IHP Catalogue Vol. V, Viet Nam-8). Kim Long ở thượng lưu ngã ba Sình nên không gồm sông Bồ (FG §3). Lưu vực tới Kim Long đo trên DEM GLO-30 là 1 543 km² (1 538 trên WGS84); ĐH Thuỷ lợi ghi 1 490 ‡. Bản cũ còn cộng 2 830 + 938 = 3 768 — đếm sông Bồ hai lần.
- **Hỏi vặn:** *"Sửa xong số nào đổi?"* → Ô lưới và chuỗi mục tiêu không đổi nên NSE không đổi; các chỗ dùng diện tích (hệ số dòng chảy trong phép thử hồ) đã chạy lại (FHF §3).

**46. [BẪY] Diện tích giảm gần một nửa mà vẫn giữ ô lưới, có mâu thuẫn không?** [TL]
- **Trả lời:** Không. Sau khi sửa, ô (16,45; 107,50) Q_tb 120,7 m³/s suy ra 1 508–2 011 km², khớp ~1 540 (lệch 10 %); ô hạ lưu (16,55; 107,50) Q_tb 194,5 suy ra 2 432–3 242 km², khớp cả hệ thống 2 830 (lệch 3 %) (FG §3). Tham chiếu cũ sai nhưng ô đã chọn đúng, hai ô nối tiếp còn khớp hơn trước.
- **Hỏi vặn:** *"Sao không lấy ô (16,55; 107,50)?"* → Ô đó gồm sông Bồ, còn ngưỡng đặt tại Kim Long; GloFAS không tách được sông Bồ (mọi ô cụm Hương lệch ≥ 81 % so với 938 km²) (FG §4).

**47. Dòng chảy đơn vị 0,071 lấy từ đâu, sao dùng 0,060–0,080?** [TL] [RD]
- **Trả lời:** UNESCO ghi trực tiếp 0,071 m³/s/km² (Q_tb 198 m³/s, 2 830 km², lớp dòng chảy 2 210 mm), từ 0,040 ở đồng bằng ven biển tới hơn 0,080 ở vùng núi (FG §3). Lưu vực tới Kim Long gần như toàn núi nên lấy 0,060–0,080. Bản cũ 0,041–0,051 chỉ là giả định.
- **Hỏi vặn:** *"198/2 830 = 0,070 chứ?"* → Đúng, chênh làm tròn; UNESCO tự ghi 0,071 — không đổi kết luận. Khoảng 0,060–0,080 làm diện tích dao động ±14 %, nhưng ba ô vẫn xếp đúng thứ tự (FG §5).

**48. 64 ô ERA5 chỉ phủ 92,5 % lưu vực, có sao không?** [TL] [DA]
- **Trả lời:** Hở phía nam 16,05° N; Tả Trạch chỉ phủ 87,6 %. Lưới vệ tinh 10×10 ô 0,1° phủ 100 % (FHF §3, §11). Vẫn vậy, ERA5 tương quan với Q cao nhất (Pearson 0,781, Spearman 0,869).
- **Hỏi vặn [BẪY]:** *"Vậy ERA5 là nguồn mưa tốt nhất?"* → Không: GloFAS v4 chạy bằng chính ERA5 nên tương quan cao là tất yếu (FHF §11).

### H3. Mưa vệ tinh và độ trễ khi chạy thật

**49. Mưa vệ tinh có giúp mô hình không?** [DA] [TL]
- **Trả lời:** Có, nhỏ và ở hạn xa. Walk-forward 13 fold, E0 + GSMaP-GC: h3 +0,016 [+0,007; +0,024], 11/13 fold, p 0,005; h2 +0,017 nhưng CI chạm 0; h1 ≈ 0 (FHF §12.1). Báo động nhầm mức 1 giảm 24 → 19, CSI 0,450 → 0,484.
- **Hỏi vặn:** *"Trên mốc A0 sao tăng lớn hơn (h2 +0,032, 13/0)?"* → Vệ tinh bù phần A0 còn thiếu (độ ẩm đất, ngữ cảnh thời tiết, chuỗi train ngắn); Report 3 báo theo mốc mạnh E0.

**50. [BẪY] Vì sao mưa vệ tinh có lợi khi phân tích lại quá khứ mà mất khi chạy thật (qua Earth Engine)?** [TL]
- **Trả lời:** Trên Earth Engine GSMaP trễ ~27 giờ, IMERG ~38 giờ; job chạy ~05h VN chỉ có mưa vệ tinh tới ngày t−1 (FHF §12.3). Walk-forward với GSMaP-GC trễ 1 ngày: h3 +0,012 (p 0,033) → −0,002 [−0,009; +0,004]. Lợi ích nằm hết ở mưa của chính ngày t.
- **Hỏi vặn:** *"Sao 'đủ ngày t' ở đây (+0,012) khác §12.1 (+0,016)?"* → Thêm cột trễ làm đổi vài ngày bị loại do thiếu số.

**51. Bản chuẩn và bản NRT của GSMaP khác nhau ra sao? Dùng NRT có cứu được không?** [TL]
- **Trả lời:** GSMaP trên Earth Engine sau ~3 ngày là **bản chuẩn** (MVK) — trùng tuyệt đối với `standard/v8/hourly_G` của JAXA, trễ ~3 ngày. Bản **NRT** trên FTP JAXA trễ ~4,7 giờ nhưng là **sản phẩm khác** (tương quan theo giờ 0,6–0,8; mùa lũ 2010–2026 tổng chỉ bằng 0,70 bản chuẩn, r ngày 0,78) ⇒ phải huấn luyện lại bằng chính lịch sử NRT (JAXA có từ 1998). Walk-forward nhóm Report 2 (21/10): NRT vẫn giúp ở cả 3 horizon — h1 +0,009 (10/13 fold, p 0,008), h2 +0,019 (11/13, p 0,006), h3 +0,012 (12/13, p 0,005) — khoảng một nửa mức tăng của bản chuẩn ở h2–h3 (`reports/wf_sat_nrt_r2_partial.csv`). Kết quả trên cấu hình E: xem `reports/wf_sat_nrt.csv`.
- **Hỏi vặn:** *"Có NRT thì job chạy lúc nào?"* → Mưa tới 23h VN ngày t có trên FTP khoảng 04h sáng hôm sau; nên dời job sang sau 05–07h cho an toàn.

**52. IMERG trên Earth Engine là bản Final hay bản sớm?** [TL] [DA]
- **Trả lời:** Trộn: `permanent` (Final) tới 30/09/2025, sau đó `provisional` (bản sớm) (FHF §12.3). Train trên Final rồi chạy thật trên bản sớm là lệch sản phẩm — IMERG chỉ là phép thử phụ; lần chia đơn còn đánh giá nó quá cao.
- **Hỏi vặn:** *"Sao chọn GSMaP-GC mà không chọn GSMaP gốc?"* → GSMaP gốc không ổn định (mùa lũ 2018 chỉ bằng 14 % ERA5); bản GC tăng đều ở h3 (FHF §11, §12.1).

### H4. Walk-forward và một lần chia

**53. Walk-forward 13 fold làm thế nào, khác một lần chia ở đâu?** [DA] [TL]
- **Trả lời:** Fold theo năm, train mở rộng, test lần lượt 2013 … 2025, gap 3 ngày; ngưỡng mức 1 tính lại chỉ từ train từng fold; 3 seed; báo ΔNSE kèm CI bootstrap theo fold, số fold thắng/thua, Wilcoxon (FHF §12). Lần chia đơn chỉ test từ 07/2022 — 4 mùa lũ, 31 ngày ≥ mức 1 — một năm bất thường có thể quyết định kết luận.
- **Hỏi vặn:** *"2023–2025 có kiểm định riêng được không?"* → Chưa: 3 fold thì p hai phía nhỏ nhất là 0,25; năm 2022 (đổi chế độ GloFAS) và 2026 báo riêng.

**54. [BẪY] Vì sao một lần chia đánh giá IMERG và DL quá cao?** [DA] [TL]
- **Trả lời:** IMERG: lần chia đơn +0,018/+0,017 (h2/h3), qua 13 fold còn +0,010/+0,008, CI chạm 0 (FHF §12.1). DL: ưu thế h2–h3 chỉ có ở 2022–2025, đúng giai đoạn test cũ; 2013–2021 DL thua (§12.2). Nguyên nhân chung: test 4 mùa lũ là mẫu nhỏ, cộng việc chọn cấu hình sau khi đã nhìn test.
- **Hỏi vặn:** *"Chênh bao nhiêu thì coi là nhiễu?"* → Chỉ đổi ngày bắt đầu train đã làm E h2 0,483 → 0,469; báo cáo dùng ngưỡng nhiễu NSE ±0,01.

**55. [BẪY] NSE "thật" của mô hình chính là bao nhiêu?** [TL] [RD]
- **Trả lời:** Mô hình chính là LightGBM cấu hình E (88 feature). Lần chia đơn (test từ 07/2022): 0,747/0,483/0,199; walk-forward trung bình 13 năm của E0: 0,761/0,398/0,170 (OUT III; FHF §12.1). Đừng nhầm với 0,747/0,420/0,175 — đó là LightGBM panel Report 2 (`lgbm_results.csv`).
- **Hỏi vặn:** *"Có đạt AC-1 không?"* → AC-1: h1 ≥ 0,70 (RMSE tốt hơn persistence ≥ 20 %), h2 ≥ 0,40, h3 ≥ 0,25. Lần chia đơn đạt h1 (RMSE tốt hơn 25,6 %) và h2, trượt h3; walk-forward h2 0,398 sát dưới ngưỡng.

### H5. Deep Learning

**56. Vì sao DL không thắng LightGBM?** [TL]
- **Trả lời:** Walk-forward so với LightGBM (0,743/0,334/0,118): LSTM L30 MSE h1 +0,021 nhưng CI [−0,014; +0,058] chứa 0; h2/h3 −0,025/−0,026; LSTM loss nhấn đỉnh h3 −0,229 (p 0,033) (FHF §12.2). Độ lệch giữa seed của DL 0,03–0,20, LightGBM 0,01. Giới hạn h2–h3 nằm ở mục tiêu GloFAS và việc thiếu mưa dự báo, không ở kiến trúc.
- **Hỏi vặn:** *"DL hơn chỗ nào?"* → Ở h1 bắt sự kiện tốt hơn: POD 0,59–0,63 so với 0,51, CSI 0,49–0,50 so với 0,44; ít cắt ngọn hơn (peak_bias −0,21…−0,26 so với −0,38).

**57. [BẪY] Bảng lần chia đơn có MLP 0,490 và LSTM 0,479 ở h2, cao hơn LightGBM 0,420 — sao vẫn nói DL không thắng?** [TL] [DA]
- **Trả lời:** Các cấu hình đó được chọn sau khi đã nhìn test, trong 8 cấu hình × 3 seed. Cấu hình chọn trước bằng valid (LSTM L=14) chỉ 0,709/0,404/0,171, thua LightGBM cả 3 horizon (FHF §6). Walk-forward bác bỏ ưu thế này.
- **Hỏi vặn:** *"Kết quả DL phụ thuộc số luồng torch không?"* → Nhỏ: LSTM trùng hệt ở 1/2/4 luồng, MLP lệch ≤ 0,028 — nhỏ hơn độ lệch giữa seed; vẫn ghim `--threads 2` để tái lập đúng CSV.

**58. Loss nhấn đỉnh được gì, mất gì?** [TL] [DA]
- **Trả lời:** Được: LSTM L30 peak_bias h2 −0,73 → −0,59, KGE h2 0,342 → 0,570. Mất: FAR mức 1 h1 0,20 → 0,26, và qua walk-forward tụt ở h3 (−0,229, p 0,033). Đánh đổi giữa bắt đỉnh và độ chính xác trung bình.
- **Hỏi vặn:** *"Có cách chữa cắt ngọn không cần DL?"* → Hồi quy phân vị α = 0,9 hoặc giảm `min_child_samples` cho đường cận trên mùa lũ — chọn trên valid/walk-forward (FS §5).

### H6. Spark và "big data"

**59. Spark chậm hơn Polars, sao vẫn làm?** [TL] [RD]
- **Trả lời:** Nói theo cặp số cụ thể kèm điều kiện đo: ETL 6 544 896 dòng giờ → 272 704 dòng ô × ngày — cụm 2 worker 33,9–41,2 s; Polars trên Windows 2,9–3,7 s; cùng trong container Polars 8,7–10,1 s so với Spark tốt nhất 32,6 s (FHF §5; SPK). Spark là yêu cầu Report 4; mục đích là chứng minh pipeline chạy đúng khi tách executor (kết quả trùng Polars) để sẵn sàng khi dữ liệu vượt RAM một máy — không phải để nhanh hơn ở cỡ 74 MB.
- **Hỏi vặn:** *"Sao tăng 4 → 8 lõi không nhanh thêm?"* → Đọc 768 file qua ổ mount Windows → Docker mất 14–63 s; và chỉ 64 khoá băm vào 16 phân hoạch nên phân hoạch lớn nhất gấp 2,1 lần trung bình (SPK).

**60. [BẪY] Đây có phải big data không?** [TL] [DA] [RD]
- **Trả lời:** Nói thẳng là chưa. Đầu vào ERA5 74 MB vừa RAM một máy; mưa vệ tinh 1998–2026 khoảng 75 triệu dòng (~100 MB) cũng vẫn trong tầm Polars (FHF §5). Phần phân tán chứng minh tính đúng và khả năng mở rộng, không chứng minh lợi ích tốc độ — nhóm trình bày đúng như vậy.
- **Hỏi vặn:** *"Khi nào Spark mới đáng dùng?"* → Khi dữ liệu vượt RAM một máy hoặc đã nằm sẵn trên kho phân tán; với DL là khi mô hình/dữ liệu lớn hơn nhiều (vd. LSTM giờ 168 bước × 64 ô) (SPK).

**61. Cụm Spark có thật sự phân tán không?** [TL]
- **Trả lời:** Về giao thức có: 1 master + 2 worker (mỗi worker 4 lõi, 2 GB) trên Docker; 2 executor trên 2 container; DDP 2 rank đồng bộ bằng gloo qua mạng Docker (SPK). Về phần cứng không: cả 3 container trên một máy vật lý 16 lõi; repo mount `/opt/repo` đóng vai ổ dùng chung thay HDFS/S3.
- **Hỏi vặn:** *"DDP 2 rank có nhanh hơn không?"* → Không: mô hình 19 395 tham số, 2 162 mẫu train — công đồng bộ ăn hết lợi; `train()` trên cụm 9,9–10,4 s so với 9,0–9,5 s một tiến trình (FHF §5).

**62. Làm sao biết Spark cho kết quả đúng?** [TL] [DA]
- **Trả lời:** So từng ô với Polars: ETL trùng mọi cột mưa (`t2m_mean` lệch 0,001 do làm tròn); 54 cột `hr_*` trùng từng bit trên cùng máy (FHF §5). Đợt kiểm chứng bắt được lỗi `peak_hour` lưu vực con lệch 79/21 305 dòng giữa Windows và cụm (cộng số thực khác thứ tự ~1e-17) — sửa bằng làm tròn trước khi tìm giờ đỉnh, nay trùng 21 305/21 305.
- **Hỏi vặn:** *"MLlib có tốt hơn LightGBM không?"* → h1 LightGBM tốt nhất (0,747 so với GBT 0,699, RF 0,687); RF nhỉnh h2/h3 (0,454/0,214) nhưng chỉ trên một lần chia.

### H7. SHAP

**63. Mô hình chính dựa vào gì? Có hợp lý thuỷ văn không?** [TL] [DA]
- **Trả lời:** SHAP trên LightGBM cấu hình E, seed 42 (tái lập NSE 0,748/0,485/0,193). h1 dựa chủ yếu Q hôm nay (`discharge` 37,4 %); h2–h3 dựa mưa lưu vực hôm nay (20,0 %, 16,0 %) (FS §1). Theo nhóm: từ h1 → h3 lưu lượng trễ 58,4 → 22,6 %, khí áp/gió 2,3 → 14,2 %, bão 0,9 → 4,1 % — đúng với lưu vực tập trung nước 5–6 giờ (FS §2).
- **Hỏi vặn:** *"Sao không dùng feature importance (gain)?"* → Gain không đáng tin: `doy_*` đứng đầu theo gain ở h2 nhưng bỏ đi NSE không giảm (OUT V).

**64. [BẪY] Độ ẩm đất ngược chiều — đất càng ướt dự báo càng thấp: mô hình sai à?** [TL] [DA]
- **Trả lời:** Đây là chỗ không hợp lý rõ nhất, nhóm ghi thẳng. ρ của `sm_7_28` là −0,12/−0,40/−0,52, mùa lũ khoảng −0,8 (FS §3b). Lý do: độ ẩm ERA5-Land gần như bản sao trạng thái ẩm đã có trong Q hôm nay (Spearman với Q(t) +0,74) nên mô hình dùng nó như biến hiệu chỉnh. Khớp ablation: thêm độ ẩm đất (C) h1 0,766 → 0,757. Báo cáo không dùng SHAP độ ẩm đất để giải thích cơ chế.
- **Hỏi vặn:** *"EDA nói nền ẩm làm lũ lớn gấp 6,9 lần?"* → Đó là quan hệ biên; khi đã biết Q hôm nay thì thông tin thêm gần bằng 0.

**65. Mưa hôm qua có SHAP âm — có phải lỗi?** [DA] [TL]
- **Trả lời:** Không. Riêng `rain_basin_lag1` ρ −0,63/−0,79/−0,84, nhưng cả nhóm mưa đúng chiều (+0,67/+0,68/+0,69) (FS §3a). Mưa hôm qua đã nằm trong Q hôm nay; khi đã biết Q, mưa hôm qua lớn nghĩa là đỉnh đang qua và mai rút — hiệu ứng có điều kiện.
- **Hỏi vặn:** *"Quy tắc đó có lúc phản tác dụng?"* → Khi mưa lớn kéo dài: 15/10/2022 `rain_thuong_lag1` = 239 mm lại cho −0,04 (FS §4).

**66. Vì sao vẫn cắt ngọn lũ (vd. đỉnh 16/10/2022)?** [TL]
- **Trả lời:** GloFAS 1 967 m³/s, dự báo 862 (0,44 lần) dù mưa và lưu lượng đẩy đúng chiều (FS §4). Nguyên nhân cấu trúc: chỉ 12/9 283 ngày train có Q(t+1) ≥ 1 967 trong khi `min_child_samples` = 30; L1 trên log1p kéo về lũ vừa; trong train 12/12 ngày Q ≥ 2 000 đều rút hôm sau. Thêm đặc trưng (A → E) không gỡ được.
- **Hỏi vặn:** *"Trên 31 ngày lũ test, dự báo đạt bao nhiêu phần thật?"* → Trung vị 0,56/0,33/0,15 ở h1/h2/h3 (FS §4).

**67. Vì sao không đổi m³/s sang mét để dùng đúng BĐ I/II/III?** [RD] [TL]
- **Trả lời:** Quan hệ H–Q chỉ R² = 0,18 trên 12 đợt lũ, ánh xạ chệch −1,94 m khi kiểm ngoài mẫu (OUT III; `FINDINGS_EVENTS.md`). Nhiều yếu tố đổi mực nước mà không đổi lưu lượng: triều cửa Thuận An, nước dâng do bão, đập Thảo Long, bồi lấp, sông Bồ tràn sang (FF §1 lớp 3). Nên dùng mức nguy cơ theo phân vị 95/98/99,5 mùa lũ (806/1 275/1 905 m³/s), không gọi là BĐ.
- **Hỏi vặn:** *"Mức tương đối đọc thế nào?"* → "Thuộc nhóm x % cao nhất của chính GloFAS", không đọc như m³/s thật vì GloFAS thiếu lũ lớn.

**68. h3 dựa 9 % vào lịch: mô hình học thuộc mùa/năm?** [DA] [RD]
- **Trả lời:** Một phần: h3 nhóm lịch 9,2 %, `month` hạng 7, ENSO 5 % — lùi về khí hậu khi tín hiệu động lực yếu (FS §2), chưa áp đảo (< 10 %). ENSO đúng chiều nhưng test chỉ 4 mùa lũ nên `oni_lag3` có thể đóng vai "mã năm".
- **Hỏi vặn [BẪY]:** *"SHAP giải thích con sông hay giải thích mô hình?"* → Giải thích mô hình; mục tiêu là GloFAS mô phỏng; feature tương quan mạnh thì đọc theo nhóm (FS §6).

### H8. Hồ chứa và các yếu tố khác

**69. GloFAS có mô phỏng hồ Tả Trạch, Bình Điền không (phép thử hồ R1)?** [TL] [RD]
- **Trả lời:** Không thấy dấu vết. Trước khi có hồ (1998–2008) so với sau (2014–2026): dòng kiệt 30 ngày giảm 10,7 % (lẽ ra phải tăng), flashiness +1,3 % và phản ứng mưa bão +3,2 % (lẽ ra phải giảm); không chỉ số nào có ý nghĩa (p 0,42–0,91) (FF §4).
- **Hỏi vặn:** *"Phép thử yếu ở đâu?"* → Chỉ 11 và 13 năm; mưa hai giai đoạn khác nhau cũng đổi chỉ số (hệ số dòng chảy đã chia cho mưa nên đỡ hơn).

**70. Luật nâng sàn khi hồ xả là gì? Sao lấy max mà không cộng?** [TL] [DA]
- **Trả lời:** Khi tỉnh phát lệnh xả: dự báo Kim Long = max(dự báo mô hình, tổng xả Tả Trạch + Bình Điền); chỉ nâng, không hạ; không có lệnh thì không đổi (FF §3). Nước xả chắc chắn qua Kim Long trong vài giờ nên là cận dưới; cộng thêm sẽ đếm trùng vì GloFAS (như chưa có hồ) đã tính dòng chảy tự nhiên từ chính lưu vực hai hồ (suy luận từ R1).
- **Hỏi vặn:** *"Sao bỏ Hương Điền, A Lưới?"* → Khác lưu vực: Hương Điền trên sông Bồ; A Lưới chuyển nước sang sông Bồ, xả tràn sang Lào; sông Bồ nhập ở hạ lưu Kim Long.

**71. [BẪY] Sao không đưa lượng xả hồ làm feature?** [TL] [RD]
- **Trả lời:** Không có chuỗi theo ngày — chỉ tin báo lúc lũ (132 dòng, 57 ngày, 2016–2026) (FF §2). Quan trọng hơn, mục tiêu GloFAS không chứa tác động hồ (R1) nên không có gì để học. Biến đại diện mức nước hồ (cấu hình D) không cải thiện; SHAP của `rain_season_cum` còn âm vào ngày mưa lớn (FS §3c).
- **Hỏi vặn:** *"Số liệu hồ dùng vào đâu?"* → Kiểm chứng (R2) và luật nâng sàn.

**72. Vấn đề lớn nhất là hồ xả hay GloFAS (phép thử R2)?** [RD] [TL]
- **Trả lời:** GloFAS mô phỏng thiếu lũ lớn: thấp hơn cận dưới lượng xả 11/24 ngày, thấp hơn cận dưới nước đổ vào hai hồ 14/23 ngày (FF §2). Ví dụ 15/10/2022: xả ≥ 3 672, nước vào 13 787, GloFAS 1 967 m³/s. Số tỉnh là tức thời, GloFAS là trung bình ngày — nhưng chênh 2–7 lần thì không giải thích hết bằng khác cách đo.
- **Hỏi vặn:** *"Sao lấy lượng xả nhỏ nhất trong ngày?"* → Báo đưa tin giờ khác nhau; cộng hai đỉnh không cùng lúc là thổi phồng — lấy nhỏ nhất cho cận dưới bảo thủ.

**73. GloFAS lên v5 có thêm hồ thì sao?** [RD] [TL]
- **Trả lời:** v5 thêm ~800 hồ (dung tích ≥ 100 triệu m³, lưu vực ≥ 500 km², điều tiết ≥ 0,8). Tả Trạch, Bình Điền đạt hai tiêu chí đầu; tiêu chí điều tiết chưa kiểm (FF §1 lớp 4). Khi Open-Meteo chuyển v5: chạy lại phép thử hồ R1 và huấn luyện lại.
- **Hỏi vặn:** *"Còn việc GloFAS đổi chế độ 07/2022?"* → Chuyển từ reanalysis sang kho dự báo; test chỉ từ 2022-07, Mann–Whitney p = 0,58.

**74. Thêm dữ liệu (A → E): cái gì giúp, cái gì không?** [DA] [TL]
- **Trả lời:** Mưa từ 1997 (train 4 550 → 9 298 ngày) giúp h1 0,745 → 0,766. Bão, không khí lạnh, ENSO giúp h2–h3: E 0,483/0,199 so với D 0,428/0,186 (FF §5). Độ ẩm đất (C) và đại diện hồ (D) không thêm gì rõ.
- **Hỏi vặn [BẪY]:** *"E h1 (0,747) thấp hơn B (0,766), sao vẫn chọn E?"* → Đánh đổi có chủ đích: E thắng rõ ở h2–h3, đúng chỗ persistence sụp (0,008/−0,198); h1 của E vẫn ≥ 0,70.

---

## Kết quả mock exam

| Lần | Ngày | Giáp | Đức | Huyền | Câu yếu nhất cần ôn |
|---|---|---|---|---|---|
| 1 (W6) | | /10 | /10 | /10 | |
| 2 (W9) | | /10 | /10 | /10 | |
