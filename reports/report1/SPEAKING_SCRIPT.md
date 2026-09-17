# SCRIPT THUYẾT TRÌNH — Report 1: Project Proposal

**Tổng thời lượng mục tiêu: 9–10 phút** · Tiếng Anh là bản đọc; tiếng Việt ngay dưới để hiểu và tập.

Cách dùng: đọc **dòng EN**, phần **VI** chỉ để nắm ý khi tập. Chỗ in **đậm** là chỗ cần nhấn giọng.
Số liệu đọc chậm lại một nhịp — đó là phần giám khảo ghi lại.

Chia phần: **Giáp** slide 1–2 và 7–8 · **Đức** slide 3–4 · **Huyền** slide 5–6 và 9–10.
Đổi người thì nói một câu chuyển, đừng im lặng bước sang.

---

## Slide 1 — Title · ~40 giây

> **EN.** Good morning. We are forecasting flood risk one to three days ahead for the Huong River in Hue, using only openly available data.
> Central Vietnam is the most flood-affected region in the country, but commune-level warning coverage is thin. Our question is whether free global data can close part of that gap.
> I will cover four things: the subject and its big-data context, the problem and the analytics approach we chose, the data we need and how we collect it, and what we have already proven.

**VI.** *Chào buổi sáng. Nhóm chúng tôi dự báo nguy cơ lũ trước 1–3 ngày cho sông Hương ở Huế, chỉ dùng dữ liệu mở.*
*Miền Trung là vùng chịu lũ nặng nhất cả nước, nhưng cảnh báo ở cấp xã còn rất thưa. Câu hỏi của chúng tôi là liệu dữ liệu toàn cầu miễn phí có lấp được một phần khoảng trống đó.*
*Tôi sẽ trình bày bốn phần: đề tài và bối cảnh dữ liệu lớn, bài toán và cách tiếp cận phân tích, dữ liệu cần và cách thu thập, và những gì đã chứng minh được.*

---

## Slide 2 — Subject & context · ~70 giây

> **EN.** The Huong basin is about **two thousand eight hundred and thirty square kilometres** — small and steep. Rainfall becomes a flood peak within a day. That short response time is exactly what makes a one-to-three-day forecast useful, and also what makes it hard.
> On the right are the official alert stages at Kim Long station: **one metre, two metres, and three and a half metres**.
> This matters more than it looks. We anchor our target variable to these stages instead of inventing our own risk scale — because these are the numbers local authorities already act on. A model that speaks a different language is a model nobody uses.

**VI.** *Lưu vực sông Hương khoảng **2.830 km²** — nhỏ và dốc. Mưa biến thành đỉnh lũ chỉ trong một ngày. Thời gian phản ứng ngắn đó chính là lý do dự báo 1–3 ngày có ích, và cũng là lý do nó khó.*
*Bên phải là các cấp báo động chính thức tại trạm Kim Long: **1 mét, 2 mét và 3,5 mét**.*
*Điểm này quan trọng hơn vẻ ngoài của nó. Chúng tôi neo biến mục tiêu vào các cấp này thay vì tự đặt ra một thang nguy cơ riêng — vì đây là những con số chính quyền địa phương đang dùng để ra quyết định. Một mô hình nói ngôn ngữ khác là mô hình không ai dùng.*

---

## Slide 3 — Context of big data · ~65 giây

> **EN.** We deliberately avoid claiming this is big data just because it is large. Volume is moderate — about **fifteen hundred** Parquet files.
> What actually makes it a data-engineering problem is **variety** and **veracity**. Six different source types have to be reconciled onto one daily timeline: simulated discharge, reanalysis rainfall, archived forecasts, river geometry, a legal document, and news bulletins.
> And veracity is the binding constraint. The discharge series is **model output, not measurement**. Upstream reservoir operation is not represented in it. We treat that as a stated limitation, not a footnote.

**VI.** *Chúng tôi cố ý không nói đây là dữ liệu lớn chỉ vì nó nhiều. Về khối lượng thì vừa phải — khoảng **1.500** file Parquet.*
*Thứ thực sự khiến nó thành bài toán kỹ thuật dữ liệu là **tính đa dạng** và **độ tin cậy**. Sáu loại nguồn khác nhau phải khớp về cùng một trục thời gian ngày: lưu lượng mô phỏng, mưa tái phân tích, dự báo lưu trữ, hình học sông, một văn bản pháp lý, và bản tin báo chí.*
*Và độ tin cậy là ràng buộc then chốt. Chuỗi lưu lượng là **đầu ra mô hình, không phải số đo**. Vận hành hồ chứa thượng nguồn không được mô phỏng trong đó. Chúng tôi coi đây là hạn chế nêu rõ, không phải chú thích cuối trang.*

---

## Slide 4 — Problem statement · ~70 giây

> **EN.** There are two targets. The **regression** problem asks *how much water* — daily discharge in cubic metres per second, at one, two and three days.
> The **classification** problem asks *which alert stage*. Positive days are rare, roughly one to three percent, so **accuracy is banned in this project**. Predicting "no flood" every single day would score ninety-eight percent and be completely useless. We use probability of detection, false-alarm ratio and critical success index instead.
> The two are linked by a unit conversion that is not trivial: the legal thresholds are **water levels in metres**, our data is **discharge in cubic metres per second**, and we could not obtain a measured rating curve. So we build that mapping from documented flood peaks instead.

**VI.** *Có hai biến mục tiêu. Bài toán **hồi quy** hỏi *bao nhiêu nước* — lưu lượng ngày, đơn vị m³/s, ở hạn 1, 2 và 3 ngày.*
*Bài toán **phân loại** hỏi *cấp báo động nào*. Số ngày dương rất ít, khoảng 1–3 %, nên **accuracy bị cấm trong dự án này**. Đoán "không lũ" mọi ngày sẽ đạt 98 % mà hoàn toàn vô dụng. Chúng tôi dùng POD, FAR và CSI thay thế.*
*Hai bài toán nối với nhau bằng một phép quy đổi đơn vị không hề đơn giản: ngưỡng pháp lý là **mực nước tính bằng mét**, dữ liệu của chúng tôi là **lưu lượng m³/s**, và chúng tôi không xin được đường quan hệ mực nước–lưu lượng thực đo. Nên chúng tôi dựng ánh xạ đó từ các đỉnh lũ đã được công bố.*

---

## Slide 5 — Analytics approach · ~70 giây

> **EN.** Of the four classes of analytics, our work is **primarily predictive**. Descriptive analysis supports it — seasonality and lag structure. Diagnostic comes through model explanation, showing which driver produced a given warning.
> We **exclude prescriptive analytics deliberately**. Recommending an evacuation requires legal authority and accountability that a student project does not have. Claiming otherwise would be irresponsible, regardless of how good the model is.
> And the line at the bottom is our actual contribution. A global forecast system **already** publishes discharge for this river cell. We are not competing with it. We correct it locally and translate it into Vietnam's own alert stages at sub-basin scale.

**VI.** *Trong bốn lớp phân tích, công việc của chúng tôi **chủ yếu là dự báo (predictive)**. Phân tích mô tả đóng vai trò hỗ trợ — tính mùa vụ và cấu trúc độ trễ. Phần chẩn đoán đến từ việc giải thích mô hình, cho biết yếu tố nào sinh ra một cảnh báo cụ thể.*
***Chúng tôi loại phân tích đề xuất (prescriptive) một cách có chủ ý**. Khuyến cáo sơ tán cần thẩm quyền pháp lý và trách nhiệm mà một đồ án sinh viên không có. Nói ngược lại sẽ là vô trách nhiệm, bất kể mô hình tốt đến đâu.*
*Và dòng dưới cùng là đóng góp thật của chúng tôi. Một hệ thống dự báo toàn cầu **đã** công bố lưu lượng cho ô sông này. Chúng tôi không cạnh tranh với nó. Chúng tôi hiệu chỉnh nó ở quy mô địa phương và dịch nó sang hệ cấp báo động của Việt Nam ở quy mô tiểu lưu vực.*

---

## Slide 6 — Data requirements · ~60 giây

> **EN.** Six inputs feed one daily analysis table. **Five of them are already on disk.**
> The one still in progress is the last row: documented flood peaks. And it is our **critical path** — without it we cannot convert the legal water-level thresholds into discharge, which means the classification target does not exist.
> That is a manual reading task: bulletins from the hydro-meteorological station, and disaster reports. It cannot be automated away, so we scheduled it as real work rather than assuming it would happen.
> All sources are open and free. The total project cost is **zero**.

**VI.** *Sáu nguồn đầu vào đổ vào một bảng phân tích ngày. **Năm trong số đó đã nằm trên đĩa.***
*Nguồn còn đang làm là dòng cuối: các đỉnh lũ đã công bố. Và nó là **đường găng** của chúng tôi — không có nó thì không quy đổi được ngưỡng mực nước pháp lý sang lưu lượng, nghĩa là biến mục tiêu phân loại không tồn tại.*
*Đó là việc đọc thủ công: bản tin của Đài Khí tượng Thuỷ văn và báo cáo phòng chống thiên tai. Không tự động hoá được, nên chúng tôi xếp nó thành việc thật trong kế hoạch chứ không giả định là nó tự xong.*
*Mọi nguồn đều mở và miễn phí. Tổng chi phí dự án là **không đồng**.*

---

## Slide 7 — Collection method · ~75 giây

> **EN.** Collection is a four-stage pipeline: select the grid cell, crawl, clean, assemble.
> Stage one deserves a note. The coordinate we started with returned a mean discharge of **five point seven** cubic metres per second — physically impossible for this basin. We scanned three hundred and sixty-one cells and used three independent tests to find the right one. The decisive test was inverting mean discharge into an implied catchment area: our chosen cell implies **two thousand three hundred to two thousand nine hundred square kilometres**, against a documented **two thousand eight hundred and thirty**. Seven percent error.
> One engineering detail worth your time. We spent hours diagnosing rate-limit errors and blaming the data provider. The real cause was **three of our own crawler processes running in parallel**, competing with each other. With a single process, the entire collection finished in about **thirty-five minutes with zero errors**. The lesson we wrote into our documentation: when you see rate limiting, count your own processes first.

**VI.** *Thu thập là một pipeline bốn bước: chọn ô lưới, crawl, làm sạch, lắp bảng.*
*Bước một đáng nói. Toạ độ ban đầu chúng tôi dùng cho lưu lượng trung bình **5,7** m³/s — bất khả thi về mặt vật lý với lưu vực này. Chúng tôi quét 361 ô và dùng ba phép kiểm độc lập để tìm ô đúng. Phép quyết định là suy ngược lưu lượng trung bình ra diện tích lưu vực: ô chúng tôi chọn suy ra **2.366–2.943 km²**, so với con số công bố **2.830 km²**. Sai 7 %.*
*Một chi tiết kỹ thuật đáng dành thời gian. Chúng tôi mất nhiều giờ chẩn đoán lỗi giới hạn tần suất và quy cho nhà cung cấp dữ liệu. Nguyên nhân thật là **ba tiến trình crawler của chính chúng tôi chạy song song**, giành nhau. Chạy đúng một tiến trình thì toàn bộ khâu thu thập xong trong khoảng **35 phút, không một lỗi nào**. Bài học chúng tôi ghi vào tài liệu: thấy bị giới hạn tần suất thì đếm tiến trình của mình trước đã.*

---

## Slide 8 — Feasibility · ~80 giây

> **EN.** We want to show this proposal is not speculative.
> The table is assembled: **six thousand and eighty-seven** daily records, seventy-one columns. Mean annual rainfall comes out at **two thousand nine hundred and twenty-nine millimetres**, which matches the published climatology of Hue — an independent check on our data.
> The chart shows the signal we intend to model. Rainfall leads discharge by exactly **one day**, correlation **zero point seven nine zero**. Notice that single-day rainfall beats every multi-day accumulation — three, five and seven days are all lower. The basin responds fast. That is physically consistent with its small steep geometry, and it supports our short forecast horizon.
> We have also measured our baselines, so the model has a real bar to clear. And a scheduled job has issued a fresh forecast every morning for three consecutive days, which is how we will compare against the global product later.

**VI.** *Chúng tôi muốn chứng minh đề xuất này không phải nói suông.*
*Bảng phân tích đã lắp xong: **6.087** bản ghi ngày, 71 cột. Lượng mưa trung bình năm ra **2.929 mm**, khớp với khí hậu Huế đã công bố — một phép kiểm độc lập cho dữ liệu của chúng tôi.*
*Biểu đồ cho thấy tín hiệu chúng tôi định mô hình hoá. Mưa dẫn trước lưu lượng đúng **một ngày**, tương quan **0,790**. Chú ý là mưa một ngày thắng mọi mức tích luỹ nhiều ngày — 3, 5 và 7 ngày đều thấp hơn. Lưu vực phản ứng nhanh. Điều đó nhất quán với hình thái nhỏ và dốc của nó, và củng cố cho hạn dự báo ngắn mà chúng tôi chọn.*
*Chúng tôi cũng đã đo các mô hình tham chiếu, nên mô hình có một mốc thật để vượt. Và một job tự động đã phát dự báo mới mỗi sáng trong ba ngày liên tiếp — đó là cách chúng tôi sẽ so với sản phẩm toàn cầu về sau.*

---

## Slide 9 — Nine-week schedule · ~50 giây

> **EN.** Nine weeks, four graded submissions. **Report 3 carries forty percent** — it is the heaviest single item, and it covers modelling and evaluation.
> Two things worth pointing out. First, data collection was scheduled across weeks one to three; it finished in **week one**. So we are ahead on the data, and the critical path has moved to the flood-event record.
> Second, the final examination is **assessed individually**. That shaped how our team works: every member has to be able to explain the whole project, not only the part they built. We hold a twenty-minute knowledge handoff every Saturday for exactly that reason.

**VI.** *Chín tuần, bốn lần nộp có điểm. **Report 3 chiếm 40 %** — là mục nặng nhất, bao phủ phần xây mô hình và đánh giá.*
*Hai điều đáng nói. Thứ nhất, khâu thu thập dữ liệu dự kiến trải tuần 1 đến tuần 3; nó xong trong **tuần 1**. Nên chúng tôi đang đi trước về dữ liệu, và đường găng đã chuyển sang bộ sự kiện lũ.*
*Thứ hai, kỳ thi cuối **chấm theo từng cá nhân**. Điều đó định hình cách nhóm làm việc: mỗi người phải giải thích được toàn bộ dự án, không chỉ phần mình làm. Chúng tôi có buổi chia sẻ kiến thức 20 phút mỗi thứ Bảy đúng vì lý do đó.*

> 💡 Slide này **không liệt kê "IEEE report + oral presentation"** nữa. Đó là yêu cầu của môn, không phải nội dung đáng trình bày cho người nghe — họ đang ngồi xem chính hai thứ đó.

---

## Slide 10 — Closing · ~50 giây

> **EN.** To close: our contribution in one sentence is **correction and localisation, not replacement**.
> Three next steps, and three limitations we state openly rather than let a reviewer find. The most important is the second one — the five kilometre grid **cannot separate the neighbouring Bo River**, so we narrowed the study to one station rather than pretend to cover two.
> Thank you. We are happy to take questions.

**VI.** *Để kết lại: đóng góp của chúng tôi trong một câu là **hiệu chỉnh và bản địa hoá, không phải thay thế**.*
*Ba việc tiếp theo, và ba hạn chế chúng tôi nêu thẳng thay vì để người phản biện tự tìm ra. Quan trọng nhất là hạn chế thứ hai — lưới 5 km **không tách được sông Bồ bên cạnh**, nên chúng tôi thu hẹp phạm vi về một trạm chứ không giả vờ bao phủ hai trạm.*
*Xin cảm ơn. Chúng tôi sẵn sàng trả lời câu hỏi.*

---

# Câu hỏi có thể bị hỏi — chuẩn bị sẵn

### Q1. "Why not just use the GloFAS forecast directly?"
> **EN.** Because it is a global model calibrated for large basins, and ours is small and steep — exactly where global models perform worst. Our role is local correction. We also translate the output into Vietnam's alert stages, which GloFAS does not provide; it publishes return-period thresholds instead.

**VI.** *Vì đó là mô hình toàn cầu hiệu chuẩn cho lưu vực lớn, còn lưu vực của chúng tôi nhỏ và dốc — đúng chỗ mô hình toàn cầu sai nhiều nhất. Vai trò của chúng tôi là hiệu chỉnh địa phương. Chúng tôi cũng dịch đầu ra sang cấp báo động của Việt Nam, thứ GloFAS không cung cấp; nó phát ngưỡng theo chu kỳ lặp lại.*

### Q2. "How will you prove your model is better?"
> **EN.** Against measured baselines, not assumed ones. Persistence reaches NSE zero point five four two at one day, so that is the bar. It collapses to near zero at two days and goes negative at three — that gap is where we must win. A direct comparison with the global forecast is only possible going forward, because no archive of past discharge forecasts is published.

**VI.** *So với các baseline đã đo, không phải baseline giả định. Persistence đạt NSE 0,542 ở hạn 1 ngày, đó là mốc. Nó sụp về gần 0 ở hạn 2 ngày và âm ở hạn 3 — khoảng trống đó là chỗ chúng tôi phải thắng. So trực tiếp với dự báo toàn cầu chỉ làm được về phía trước, vì không có kho lưu trữ dự báo lưu lượng quá khứ.*

### Q3. "Your discharge data is simulated. Is the project still valid?"
> **EN.** Yes, but with a stated boundary. We are forecasting the behaviour of a well-documented operational model, and we validate our thresholds against real published flood peaks. We do not claim to reproduce measured water levels. That limitation is in the abstract, not buried in an appendix.

**VI.** *Có, nhưng với một giới hạn được nêu rõ. Chúng tôi dự báo hành vi của một mô hình vận hành đã được tài liệu hoá đầy đủ, và chúng tôi kiểm chứng ngưỡng của mình với các đỉnh lũ thật đã công bố. Chúng tôi không tuyên bố tái tạo được mực nước thực đo. Hạn chế đó nằm ngay trong phần tóm tắt, không vùi trong phụ lục.*

### Q4. "What if you cannot collect enough flood events?"
> **EN.** We have a documented fallback: a percentile-based risk scale derived from the discharge distribution. But if we use it, we rename the output — it becomes "risk level one to three", not BĐ one to three — because it would no longer be the official alert system.

**VI.** *Chúng tôi có phương án dự phòng đã ghi trong tài liệu: thang nguy cơ theo phân vị suy từ phân phối lưu lượng. Nhưng nếu dùng nó, chúng tôi đổi tên đầu ra — thành "mức nguy cơ 1–3", không phải BĐ I–III — vì khi đó nó không còn là hệ báo động chính thức.*

### Q5. "What is the anomaly on 14 June 2025?"
> **EN.** Two thousand and fifty-five cubic metres per second with almost no rainfall. Our hypothesis is reservoir release — the basin has Ta Trach and Binh Dien reservoirs, and GloFAS does not model reservoir operation. We have logged it as an open risk and it is on our investigation list.

**VI.** *2.055 m³/s mà gần như không có mưa. Giả thuyết của chúng tôi là xả hồ chứa — lưu vực có hồ Tả Trạch và Bình Điền, và GloFAS không mô phỏng vận hành hồ chứa. Chúng tôi đã ghi nó thành một rủi ro mở và nó nằm trong danh sách cần điều tra.*

---

# Mẹo khi tập

1. **Bấm giờ từng slide.** Vượt quá con số ghi ở tiêu đề là phải cắt câu, không phải nói nhanh hơn.
2. **Số liệu đọc chậm và tách chữ**: "two thousand eight hundred and thirty" chứ không phải "twenty-eight thirty".
3. **Đừng đọc slide.** Slide là chỗ dựa cho khán giả, không phải cho người nói. Nếu bí thì nhìn ghi chú trong PowerPoint (View → Presenter View).
4. **Ba câu phải nói trôi không cần nhìn**: định vị đóng góp (slide 5), bài học về tiến trình song song (slide 7), và hạn chế sông Bồ (slide 10). Đó là ba chỗ ghi điểm.
5. **Chuyển người** thì nói một câu bắc cầu, ví dụ *"Duc will now explain the big-data context."*
6. Luyện **3 lần**: lần 1 đọc script, lần 2 nhìn gạch đầu dòng, lần 3 không nhìn gì.
