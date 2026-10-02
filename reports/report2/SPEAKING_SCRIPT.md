# SCRIPT THUYẾT TRÌNH — Report 2: Data Collection, Cleaning & EDA

**Tiếng Anh đơn giản.** Câu ngắn, từ dễ, dễ nói trôi. Tiếng Việt ngay dưới để hiểu ý.

**Tổng: ~8 phút** · Chia phần: **Giáp** slide 1–2 và 8 · **Đức** slide 3–4 · **Huyền** slide 5–7.

Cách dùng:
- Đọc **dòng EN**. Phần **VI** chỉ để hiểu khi tập.
- Chữ **in đậm** thì nhấn giọng.
- **Số thì đọc chậm.** Đó là phần giám khảo ghi lại.
- Mỗi câu ngắn xong thì **dừng một nhịp**.

Deck: `reports/report2/slides/DSP391m_Report2_Data_EDA.html` (bấm **S** để xem ghi chú) ·
PDF: `DSP391m_Report2_Data_EDA_slides.pdf`

---

## Slide 1 — Title · ~40 giây · **Giáp**

> **EN.**
> Good morning. We are team three.
> Last time, we proposed our flood project.
> Today is Report 2. How we **collected** the data. How we **cleaned** it. And what it **tells** us.
> The short version: we **measured everything**.
> And some things in Report 1 were **wrong**.
> We will show you what, and why.

> **VI.** Chào thầy/cô. Lần trước nhóm đề xuất dự án lũ. Hôm nay là Report 2: thu thập, làm sạch, và dữ liệu nói gì. Tóm lại: nhóm đo lại mọi thứ, và vài điểm trong Report 1 đã sai — nhóm sẽ chỉ ra sai gì và vì sao.

## Slide 2 — Four open sources · ~60 giây · **Giáp**

> **EN.**
> We use **four free sources**.
> River flow from the global flood system, GloFAS.
> Rain from ERA5, on **sixty-four** grid points.
> Sea level at the river mouth, as a tide signal.
> And **nineteen** real floods, from a university paper and the news.
> One lesson for this whole report. We **measured** every source. We did not trust the documents.
> The flood service says it starts in **nineteen eighty-four**.
> In fact, the first **thirteen years are empty**. Real data starts in **nineteen ninety-seven**.

> **VI.** Bốn nguồn miễn phí: lưu lượng GloFAS, mưa ERA5 64 điểm, mực nước biển ở cửa sông, và 19 trận lũ thật. Bài học chung: nhóm đo từng nguồn, không tin tài liệu. GloFAS ghi có từ 1984 nhưng 13 năm đầu rỗng — dữ liệu thật từ 1997.

## Slide 3 — Probe, then fetch · ~60 giây · **Đức**

> **EN.**
> The flood service gives **one point** at a time. But which point is our river?
> We do not know before we look.
> So we checked **three hundred sixty-one** points, with one cheap year of data.
> **Two hundred thirty-four** had water. **Eighty-three** got the full history. **One** was chosen.
> Two simple rules were **wrong**.
> The biggest river point mixes **two rivers**.
> The point nearest the station is **almost dry**, because the model's river is **seven kilometres** away.
> We chose by checking the **basin size**.

> **VI.** Mỗi lần gọi API chỉ được một điểm, chưa biết điểm nào là sông. Nhóm dò 361 điểm bằng 1 năm dữ liệu cho rẻ → 234 có nước → 83 lấy đủ chuỗi → chọn 1. Hai quy tắc trực giác đều sai: điểm lưu lượng lớn nhất gộp cả sông Bồ; điểm gần trạm nhất gần như khô vì sông trong mô hình lệch 7 km. Chọn bằng cách kiểm diện tích lưu vực.

## Slide 4 — Four defects · ~60 giây · **Đức**

> **EN.**
> Cleaning. We found **four problems**. Each one passed the normal check.
> One: **thirteen years** of empty river data. We counted **rows**, not **values**.
> Two: the rain grid was **uneven**. The middle area, closest to our station, had only **nine of sixteen** points. We fixed it.
> Three: the forecast rain was **exactly the same** as the observed rain. **Zero point zero** difference. So we could not use it.
> Four: the original map point was on a **small side stream**.
> The lesson: **count values, not rows**.

> **VI.** Bốn lỗi, lỗi nào cũng qua được bước kiểm tra thông thường: 13 năm rỗng (đếm dòng chứ không đếm giá trị); lưới mưa lệch, vùng giữa gần trạm nhất chỉ có 9/16 điểm — đã sửa; mưa "dự báo" giống hệt mưa thực đo, chênh 0,0 mm — không dùng được; toạ độ kế hoạch gốc nằm trên nhánh nhỏ.

## Slide 5 — Rain today, river tomorrow · ~60 giây · **Huyền**

> **EN.**
> Now the main signal.
> Rain comes first. The river follows **one day** later. Correlation **zero point seven nine**.
> It is the same in all three parts of the basin. Because water travels from the mountains to the city in only **five to six hours**.
> Two more results.
> Rain added over **three days** is even stronger: **zero point eight six**.
> And **wet ground** matters a lot. The same heavy rain gives almost **seven times** more water when the ground is already wet.

> **VI.** Mưa đi trước, sông theo sau 1 ngày, tương quan 0,79, giống nhau ở cả 3 tiểu lưu vực vì nước từ núi về thành phố chỉ mất 5–6 giờ. Mưa cộng dồn 3 ngày còn mạnh hơn: 0,86. Và nền đất ẩm quan trọng: cùng một trận mưa lớn, đất ẩm cho lượng nước gấp gần 7 lần đất khô.

## Slide 6 — Water level does not follow flow · ~60 giây · **Huyền**

> **EN.**
> Real floods tell a **surprising** story.
> In October twenty twenty, the water level was **four point one seven** metres, with **two thousand** cubic metres per second.
> In November twenty twenty-three, the level was **higher**, **four point three four** metres. But the flow was only **five hundred eighty-four**.
> So level and flow **do not move together** at this station.
> Also, big floods are **rare**. The top one percent of days happens only **sixty-one** times in sixteen years.
> So for rare levels, we report results. But we do not make strong claims with **fewer than thirty** days.

> **VI.** Lũ 10/2020 mực nước 4,17 m với 2 000 m³/s; lũ 11/2023 mực nước còn cao hơn, 4,34 m, mà lưu lượng chỉ 584. Ở trạm này mực nước và lưu lượng không đi cùng nhau. Lũ lớn lại hiếm: 1 % số ngày cao nhất chỉ 61 lần trong 16 năm, nên mức nào dưới 30 ngày thì chỉ báo cáo, không kết luận mạnh.

## Slide 7 — Limitations · ~50 giây · **Huyền**

> **EN.**
> We say our limits **now**, not later.
> One: river flow is from a **model**, not measured.
> Two: the reanalysis **misses the heaviest rain**. In November twenty twenty-four it shows **three hundred thirty-two** millimetres. But the mountains really had **five to eight hundred**.
> Three: tide data starts only in **twenty twenty-three**.
> Four: the test period is short, only **four years**. Only the first risk level has enough flood days for a strong claim.

> **VI.** Nói rõ hạn chế ngay: lưu lượng là mô phỏng; ERA5 hụt mưa cực trị (11/2024: 332 mm so với 500–800 mm ở miền núi); dữ liệu triều chỉ từ 2023; tập test chỉ 4 năm nên chỉ mức nguy cơ 1 đủ ngày để kết luận mạnh.

## Slide 8 — Measured, then corrected · ~60 giây · **Giáp**

> **EN.**
> Last slide. **Four** things in Report 1 were wrong, and we correct them here.
> Forty-two years of data is really **twenty-nine**.
> Forecast rain is the same as observed rain. So we test **sensitivity** instead.
> The target is now **risk levels** from flow percentiles, not official stages.
> And three-day rain is **stronger** than one-day rain, not weaker.
> The official stages are still correct: **one, two, and three point five** metres. Now checked from the **law itself**.
> Next, Report 3. Our first model already **beats** the simple baseline.
> Thank you.

> **VI.** Bốn điểm sai trong Report 1 được sửa: 42 năm thực ra là 29; mưa dự báo trùng mưa thực đo nên chuyển sang kiểm độ nhạy; mục tiêu chuyển sang mức nguy cơ theo phân vị lưu lượng; mưa 3 ngày mạnh hơn chứ không yếu hơn mưa 1 ngày. Ngưỡng chính thức vẫn đúng — 1,0 / 2,0 / 3,5 m — nay đã kiểm từ chính văn bản pháp luật. Report 3: mô hình đầu tiên đã thắng baseline. Cảm ơn.

---

## Câu hỏi dễ bị hỏi — trả lời ngắn

| Câu hỏi | Trả lời |
|---|---|
| Why not use the official alert stages as the target? | At Kim Long, level is only weakly related to flow (R² = 0.18). Tide and backwater also raise the level. Labels built on that link would be wrong without anyone knowing. |
| How do you know the forecast rain was identical? | We compared 1,523 days: maximum difference 0.0 mm. We also called both APIs directly and got the same numbers. |
| Is this big data? | Not by volume. By **variety and veracity**: four sources, different time zones and resolutions, and a source that changes regime in 2022. |
| Why trust a simulated river? | We do not fully trust it. We say it is a limit, and we checked it against 19 real floods. The October 2020 peak falls on the same day in both. |
