# SCRIPT THUYẾT TRÌNH — Report 1: Project Proposal

**Tiếng Anh đơn giản.** Câu ngắn, từ dễ, dễ nói trôi. Tiếng Việt ngay dưới để hiểu ý.

**Tổng: 9–10 phút** · Chia phần: **Giáp** slide 1–2 và 7–8 · **Đức** slide 3–4 · **Huyền** slide 5–6 và 9–10.

Cách dùng:
- Đọc **dòng EN**. Phần **VI** chỉ để hiểu khi tập.
- Chữ **in đậm** thì nhấn giọng.
- **Số thì đọc chậm.** Đó là phần giám khảo ghi lại.
- Mỗi câu ngắn xong thì **dừng một nhịp**. Đừng nói liền một hơi.

---

## Slide 1 — Title · ~40 giây · **Giáp**

> **EN.**
> Good morning. We are team three.
> Our project is about floods in Huế.
> We want to predict flood risk **one to three days** before it happens.
> We use only **free open data**.
> Central Vietnam has the worst floods in the country. But warnings at village level are still weak.
> So our question is simple. Can free data help?
> I will talk about four things. The topic. The problem. The data. And what we already did.

**VI.** *Chào buổi sáng. Chúng tôi là nhóm 3. Dự án của chúng tôi về lũ ở Huế. Chúng tôi muốn dự báo nguy cơ lũ trước 1–3 ngày. Chúng tôi chỉ dùng dữ liệu mở miễn phí. Miền Trung có lũ nặng nhất cả nước. Nhưng cảnh báo ở cấp xã vẫn yếu. Nên câu hỏi rất đơn giản: dữ liệu miễn phí có giúp được không? Tôi sẽ nói bốn phần: đề tài, bài toán, dữ liệu, và những gì đã làm được.*

---

## Slide 2 — Subject & context · ~70 giây · **Giáp**

> **EN.**
> The Hương river basin is small. About **two thousand eight hundred** square kilometres.
> It is also steep. So water moves fast.
> Rain today becomes a flood tomorrow. **Only one day.**
> This is why a three-day forecast is useful. It is also why it is hard.
> Now look at the right side.
> These are the **official alert levels** at Kim Long station.
> Level one is **one metre**. Level two is **two metres**. Level three is **three point five metres**.
> This part is important.
> We use these official numbers. We do not invent our own scale.
> Why? Because local officers already use these numbers every day.
> If we use different numbers, nobody will use our model.

**VI.** *Lưu vực sông Hương nhỏ, khoảng 2.800 km². Nó cũng dốc, nên nước chảy nhanh. Mưa hôm nay thành lũ ngày mai — chỉ một ngày. Đó là lý do dự báo ba ngày có ích, và cũng là lý do nó khó. Bên phải là các cấp báo động chính thức tại trạm Kim Long: BĐ1 là 1 mét, BĐ2 là 2 mét, BĐ3 là 3,5 mét. Phần này quan trọng: chúng tôi dùng số chính thức, không tự đặt thang riêng. Vì cán bộ địa phương đang dùng những con số này hằng ngày. Nếu chúng tôi dùng số khác thì không ai dùng mô hình của chúng tôi.*

---

## Slide 3 — Context of big data · ~60 giây · **Đức**

> **EN.**
> Many people think big data means **a lot of data**. We do not agree.
> Our data size is normal. About **one thousand five hundred** files.
> The hard part is something else. It is **variety** and **veracity**.
> Variety means many **different** types of data. We have six types.
> River flow. Rain. Old forecasts. River maps. A law document. And news reports.
> All of them must fit into **one table**, day by day. That is the hard work.
> Veracity means: **can we trust the data?**
> Our river flow data is **not measured**. It comes from a computer model.
> Also, dams upstream are **not** in the model.
> We say this clearly. We do not hide it.

**VI.** *Nhiều người nghĩ dữ liệu lớn nghĩa là nhiều dữ liệu. Chúng tôi không đồng ý. Kích thước dữ liệu của chúng tôi bình thường, khoảng 1.500 file. Phần khó nằm ở chỗ khác: tính đa dạng và độ tin cậy. Đa dạng là nhiều loại dữ liệu khác nhau — chúng tôi có sáu loại: lưu lượng sông, mưa, dự báo cũ, bản đồ sông, một văn bản luật, và bản tin báo chí. Tất cả phải ghép vào một bảng theo từng ngày. Đó mới là phần khó. Độ tin cậy nghĩa là: dữ liệu có tin được không? Lưu lượng của chúng tôi không phải số đo, mà từ mô hình máy tính. Và hồ chứa thượng nguồn không có trong mô hình. Chúng tôi nói rõ điều này, không giấu.*

---

## Slide 4 — Problem statement · ~65 giây · **Đức**

> **EN.**
> We have **two** problems.
> The first one is easy to say. **How much water?**
> We predict river flow in cubic metres per second. For one, two and three days.
> The second one is different. **Which alert level?**
> Level one, two, or three.
> Here is a trap. Flood days are **very rare**. Only **one to three percent** of all days.
> So we **never use accuracy** in this project.
> Think about it. If I say "no flood" every day, I am correct **ninety-eight percent** of the time. But my model is useless.
> So we use other scores: POD, FAR and CSI.
> Now the hard part in the middle.
> The official levels are in **metres**. Our data is in **cubic metres per second**.
> They are different units. We cannot just convert them.
> We asked for real measurements. We could not get them.
> So we build the link from **old flood records** instead.

**VI.** *Chúng tôi có hai bài toán. Cái thứ nhất dễ nói: bao nhiêu nước? Dự báo lưu lượng m³/s cho 1, 2, 3 ngày. Cái thứ hai khác: cấp báo động nào — 1, 2 hay 3. Đây là cái bẫy: ngày lũ rất hiếm, chỉ 1–3 % tổng số ngày. Nên chúng tôi không bao giờ dùng accuracy. Nghĩ mà xem: nếu tôi nói "không lũ" mọi ngày thì tôi đúng 98 %, nhưng mô hình vô dụng. Nên chúng tôi dùng POD, FAR, CSI. Giờ là phần khó ở giữa: cấp báo động tính bằng mét, dữ liệu của chúng tôi tính bằng m³/s. Hai đơn vị khác nhau, không đổi thẳng được. Chúng tôi đã xin số liệu thực đo nhưng không được. Nên chúng tôi dựng cầu nối từ các trận lũ cũ.*

---

## Slide 5 — Analytics approach · ~65 giây · **Huyền**

> **EN.**
> There are four types of analytics. Let me go through them.
> **Descriptive** asks: what happened? We use it, but only to help.
> **Diagnostic** asks: why did it happen? We use it a little, to explain our warnings.
> **Predictive** asks: what will happen? **This is our main work.** Both our research questions are here.
> **Prescriptive** asks: what should we do? **We do not do this.**
> Why not? Because telling people to leave their homes needs **legal power**. A student project does not have that power.
> Now the last line. This is our real contribution.
> A global system **already** predicts this river. We are not fighting it.
> We do two things. We **fix its errors** for our small basin. And we **translate** it into Vietnamese alert levels.

**VI.** *Có bốn loại phân tích. Descriptive hỏi: chuyện gì đã xảy ra — chúng tôi dùng để hỗ trợ. Diagnostic hỏi: vì sao xảy ra — dùng một phần để giải thích cảnh báo. Predictive hỏi: chuyện gì sẽ xảy ra — đây là phần chính, cả hai câu hỏi nghiên cứu nằm ở đây. Prescriptive hỏi: nên làm gì — chúng tôi không làm. Vì bảo người dân rời nhà cần thẩm quyền pháp lý, mà đồ án sinh viên không có. Dòng cuối là đóng góp thật: một hệ thống toàn cầu đã dự báo con sông này rồi, chúng tôi không cạnh tranh. Chúng tôi làm hai việc: sửa sai số của nó cho lưu vực nhỏ này, và dịch nó sang cấp báo động của Việt Nam.*

---

## Slide 6 — Data requirements · ~55 giây · **Huyền**

> **EN.**
> We need six types of data. All of them go into **one daily table**.
> Look at the last column. **Five are done.** We already have them.
> Only one is not finished. The last row: **old flood records**.
> This one is our **biggest problem** right now.
> Without it, we cannot change metres into cubic metres per second.
> And then the alert level problem **cannot exist**.
> This work is manual. We must read weather reports and news by hand.
> A computer cannot do it. So we put it in our plan as real work.
> One good point. All data is **free and open**. Our project costs **zero**.

**VI.** *Chúng tôi cần sáu loại dữ liệu, tất cả vào một bảng theo ngày. Nhìn cột cuối: năm loại đã xong. Chỉ còn một chưa: dòng cuối — hồ sơ các trận lũ cũ. Đây là vấn đề lớn nhất lúc này. Không có nó thì không đổi được mét sang m³/s, và bài toán cấp báo động không tồn tại. Việc này làm tay: phải đọc bản tin thời tiết và báo chí. Máy không làm được. Nên chúng tôi xếp nó thành việc thật trong kế hoạch. Một điểm tốt: mọi dữ liệu đều miễn phí và mở. Dự án tốn 0 đồng.*

---

## Slide 7 — Collection method · ~70 giây · **Giáp**

> **EN.**
> We collect data in four steps. Select. Crawl. Clean. Assemble.
> Step one has a story.
> Our first map point gave us **five point seven** cubic metres per second. That is **too small**. It is impossible for this river.
> So we checked **three hundred sixty-one** points. We used three different tests.
> The best test was this one. From the water flow, we can **guess the basin size**.
> Our new point gives about **two thousand six hundred** square kilometres. The real basin is **two thousand eight hundred and thirty**.
> That is only **seven percent** different. So we know the point is correct.
> Now one more story. This one is about our own mistake.
> We saw many "too many requests" errors. We thought the data website blocked us.
> We almost cut our project smaller because of this.
> But the real reason was **us**. We ran **three** programs at the same time. They fought each other.
> With only **one** program, everything finished in **thirty-five minutes**. **Zero** errors.
> So the lesson is simple. Check your own computer first.

**VI.** *Chúng tôi thu thập dữ liệu qua bốn bước: chọn, crawl, làm sạch, lắp bảng. Bước một có một câu chuyện: điểm đầu tiên cho 5,7 m³/s — quá nhỏ, bất khả thi với con sông này. Nên chúng tôi kiểm 361 điểm bằng ba phép thử khác nhau. Phép tốt nhất là: từ lưu lượng có thể suy ra diện tích lưu vực. Điểm mới cho khoảng 2.600 km², lưu vực thật là 2.830 km² — chỉ lệch 7 %, nên biết là chọn đúng. Còn một chuyện nữa, về lỗi của chính chúng tôi: thấy nhiều lỗi "quá nhiều request", tưởng bị trang web chặn, suýt cắt nhỏ dự án. Nhưng nguyên nhân thật là chúng tôi chạy ba chương trình cùng lúc, chúng giành nhau. Chạy một chương trình thôi thì xong trong 35 phút, không lỗi nào. Bài học đơn giản: kiểm máy mình trước đã.*

---

## Slide 8 — Feasibility · ~70 giây · **Giáp**

> **EN.**
> Now I want to show you: this is **not just a plan**. We already did the work.
> Our table is ready. **Six thousand** rows. **Seventy-one** columns.
> Average rain per year is **two thousand nine hundred** millimetres. This matches the official climate data for Huế. So our data is correct.
> Now look at the chart. This is the signal we want to model.
> Rain comes first. River flow comes **one day later**. The correlation is **zero point seven nine**.
> Look at the bars. Day one is the highest.
> We also tested three-day rain, five-day rain, seven-day rain. **All of them are lower.**
> This tells us the river reacts **fast**. It matches a small, steep basin.
> And it supports our short forecast time.
> Last point. We already measured simple models. So we know the target we must beat. It is a **real** number, not a guess.

**VI.** *Tôi muốn cho thấy đây không chỉ là kế hoạch — chúng tôi đã làm rồi. Bảng đã xong: 6.000 dòng, 71 cột. Mưa trung bình năm 2.900 mm, khớp số liệu khí hậu chính thức của Huế, nên dữ liệu đúng. Nhìn biểu đồ: đây là tín hiệu chúng tôi muốn mô hình hoá. Mưa đến trước, lưu lượng đến sau một ngày, tương quan 0,79. Nhìn các cột: ngày 1 cao nhất. Chúng tôi cũng thử mưa 3, 5, 7 ngày — đều thấp hơn. Điều đó cho thấy sông phản ứng nhanh, khớp với lưu vực nhỏ và dốc, và ủng hộ hạn dự báo ngắn. Ý cuối: chúng tôi đã đo các mô hình đơn giản, nên biết mốc phải vượt là bao nhiêu — một con số thật, không phải đoán.*

---

## Slide 9 — Schedule · ~50 giây · **Huyền**

> **EN.**
> Nine weeks. Four reports.
> Look at report three. It is **forty percent**. It is the biggest one. It covers the model and the results.
> Two things I want to say.
> First, we planned three weeks for data collection. We finished in **one week**.
> So we are **ahead of plan** on data. Now our main problem is the flood records.
> Second, the final exam is **individual**.
> This changed how we work. Every member must explain the **whole** project. Not only his or her own part.
> So we meet every Saturday. One person teaches. The others ask questions.

**VI.** *Chín tuần, bốn báo cáo. Nhìn Report 3: 40 %, là mục lớn nhất, bao gồm mô hình và kết quả. Hai điều muốn nói. Thứ nhất, dự kiến ba tuần cho thu thập dữ liệu, nhưng xong trong một tuần — nên đang đi trước kế hoạch về dữ liệu, giờ vấn đề chính là hồ sơ lũ. Thứ hai, thi cuối kỳ chấm cá nhân. Điều đó đổi cách nhóm làm việc: mỗi người phải giải thích được toàn bộ dự án, không chỉ phần mình. Nên chúng tôi gặp nhau mỗi thứ Bảy, một người giảng, những người kia hỏi.*

---

## Slide 10 — Closing · ~45 giây · **Huyền**

> **EN.**
> One sentence to finish.
> We **do not replace** the global forecast. We **fix it** and **translate it** into Vietnamese alert levels.
> Three next steps. Finish the flood records. Train the model. And check the dam problem.
> And three limits. We say them now, not later.
> One. Our river data is from a model, **not measured**.
> Two. The map is five kilometres wide. It is **too big** to see the small Bồ river. So we study **one station only**.
> Three. This is a **student project**. It is **not** an official warning service.
> Thank you. We are happy to answer questions.

**VI.** *Một câu để kết. Chúng tôi không thay thế dự báo toàn cầu; chúng tôi sửa nó và dịch nó sang cấp báo động Việt Nam. Ba bước tiếp theo: hoàn thành hồ sơ lũ, huấn luyện mô hình, và kiểm vấn đề hồ chứa. Và ba hạn chế — nói ngay chứ không để sau. Một: dữ liệu sông từ mô hình, không phải số đo. Hai: lưới bản đồ rộng 5 km, quá to để thấy sông Bồ nhỏ, nên chỉ nghiên cứu một trạm. Ba: đây là đồ án sinh viên, không phải dịch vụ cảnh báo chính thức. Xin cảm ơn, chúng tôi sẵn sàng trả lời câu hỏi.*

---

# CÂU HỎI CÓ THỂ BỊ HỎI

### Q1. "Why not just use GloFAS directly?"
> **EN.** Two reasons.
> First, GloFAS is a **world** model. It works well for **big** rivers. Our river is small and steep. This is where world models are **weakest**.
> Second, GloFAS does not give Vietnamese alert levels. It gives different numbers. We translate them.

**VI.** *Hai lý do. Thứ nhất, GloFAS là mô hình toàn cầu, tốt cho sông lớn; sông của chúng tôi nhỏ và dốc — đúng chỗ mô hình toàn cầu yếu nhất. Thứ hai, GloFAS không cho cấp báo động Việt Nam mà cho số khác; chúng tôi dịch chúng.*

### Q2. "How do you know your model is good?"
> **EN.** We compare it with simple models.
> The best simple model is "**tomorrow is the same as today**". It gets **zero point five four** at one day.
> But at two days it drops to almost **zero**. At three days it is **negative**.
> So day two and day three are where we can win.

**VI.** *Chúng tôi so với các mô hình đơn giản. Mô hình đơn giản tốt nhất là "ngày mai giống hôm nay", đạt 0,54 ở hạn 1 ngày. Nhưng hạn 2 ngày rơi về gần 0, hạn 3 ngày thành âm. Nên ngày 2 và ngày 3 là chỗ chúng tôi có thể thắng.*

### Q3. "Your data is not real measurement. Is that OK?"
> **EN.** It is a limit, and we say it clearly.
> We predict the behaviour of a well-known model. And we check our levels against **real flood records** from the news.
> We do not say we can reproduce real water levels. This limit is in our abstract, on page one.

**VI.** *Đó là hạn chế, và chúng tôi nói rõ. Chúng tôi dự báo hành vi của một mô hình đã được biết rõ, và kiểm ngưỡng bằng hồ sơ lũ thật từ báo chí. Chúng tôi không nói mình tái tạo được mực nước thật. Hạn chế này nằm ngay trong phần tóm tắt, trang một.*

### Q4. "What if you cannot find enough flood records?"
> **EN.** We have a backup plan.
> We can use **statistics** instead. We look at the highest five percent of days.
> But then we must **change the name**. We call it "risk level", not "BĐ level". Because it is no longer the official system.

**VI.** *Chúng tôi có phương án dự phòng: dùng thống kê thay thế, lấy 5 % số ngày cao nhất. Nhưng khi đó phải đổi tên — gọi là "mức nguy cơ", không gọi là "cấp BĐ", vì nó không còn là hệ chính thức.*

### Q5. "What is the strange day in June 2025?"
> **EN.** Good question. On that day the river was very high. But there was **almost no rain**.
> We think a **dam** opened upstream. There are two dams in this basin.
> GloFAS does not model dams. We wrote this down as an open problem. We will check it.

**VI.** *Câu hỏi hay. Hôm đó lưu lượng rất cao nhưng gần như không mưa. Chúng tôi nghĩ là hồ chứa xả — lưu vực có hai hồ. GloFAS không mô phỏng hồ chứa. Chúng tôi đã ghi lại thành vấn đề mở và sẽ kiểm tra.*

---

# TỪ KHÓ — TẬP ĐỌC TRƯỚC

| Từ | Đọc gần đúng | Nghĩa |
|---|---|---|
| discharge | **DIS**-charj | lưu lượng |
| basin | **BAY**-sin | lưu vực |
| catchment | **KATCH**-mənt | lưu vực hứng nước |
| correlation | ko-rə-**LAY**-shən | tương quan |
| rainfall | **RAYN**-fawl | lượng mưa |
| threshold | **THRESH**-hold | ngưỡng |
| reservoir | **REZ**-ər-vwar | hồ chứa |
| accuracy | **AK**-yə-rə-see | độ chính xác |
| veracity | və-**RASS**-i-tee | độ tin cậy |
| prescriptive | pri-**SKRIP**-tiv | mang tính chỉ định |
| cubic metres per second | KYOO-bik MEE-terz per SEK-ənd | m³/s |

**Đọc số cho dễ nghe:**
- 2.830 → "two thousand eight hundred and thirty"
- 0,790 → "zero point seven nine"
- 6.087 → "six thousand" (làm tròn khi nói cũng được)
- 1–3 % → "one to three percent"

---

# MẸO KHI TẬP

1. **Bấm giờ từng slide.** Quá giờ thì **bỏ bớt câu**, đừng nói nhanh hơn.
2. **Câu ngắn thì dừng.** Mỗi dấu chấm là một nhịp thở. Nói chậm nghe tự tin hơn nói nhanh.
3. **Đừng đọc slide.** Slide cho người nghe, script cho người nói. Bí thì bấm **S** trong deck để xem ghi chú.
4. **Ba câu phải thuộc, không cần nhìn:**
   - Slide 5: *"We fix its errors and translate it."*
   - Slide 7: *"The real reason was us."*
   - Slide 10: *"This is a student project, not an official warning service."*
5. **Đổi người thì nói một câu bắc cầu**, ví dụ: *"Now Duc will talk about the data."* Đừng im lặng bước sang.
6. **Tập 3 lần:** lần 1 đọc script · lần 2 nhìn gạch đầu dòng · lần 3 không nhìn gì.
