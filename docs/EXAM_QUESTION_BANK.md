# NGÂN HÀNG CÂU HỎI VẤN ĐÁP

Thi cuối kỳ **chấm cá nhân, 30 phút, 20 % điểm**. Mỗi người phải trả lời được **toàn bộ**, kể cả phần mình không làm.

Cách dùng: gặp khái niệm mới trong tuần → thêm 1 câu vào đây. Từ W10 bốc thăm 3 câu/người mỗi buổi mock exam.
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
14. **Mô hình của nhóm tốt hơn dự báo GloFAS gốc ở điểm nào?** *(câu chắc chắn bị hỏi)*
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

## F. Câu hỏi về quy trình làm việc

31. Bạn phụ trách phần nào? Phần **người khác** làm hoạt động ra sao?
32. Nhóm phối hợp qua công cụ gì? Xử lý bất đồng thế nào?
33. Rủi ro lớn nhất nhóm gặp phải và cách vượt qua?

---

## Kết quả mock exam

| Lần | Ngày | Giáp | Đức | Huyền | Câu yếu nhất cần ôn |
|---|---|---|---|---|---|
| 1 (W10) | | /10 | /10 | /10 | |
| 2 (W12) | | /10 | /10 | /10 | |
| 3 (W15) | | /10 | /10 | /10 | |
