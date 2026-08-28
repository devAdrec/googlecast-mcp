---
product: googlecast-mcp
layer: method
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
package_files: "[[package/README|cách cài]] · [[package/requirement]] · [[package/technical-docs]] · [[package/user-manual]] · [[package/eval/README]]"
reproduction: "[[reproduce-googlecast-mcp]]"
registry: "[[packages/googlecast-mcp]]"
# Mức truyền đạt KHÔNG ghi ở đây — xem [[packages/googlecast-mcp]].
# Lý do: note tự dán mức cho chính mình sẽ mồi sẵn kỳ vọng cho người đọc sạch.
---

# Cách xây một MCP server điều khiển thiết bị vật lý

Ghi lại **cách nghĩ**, không phải cách dùng. Muốn cài và chạy sản phẩm thì đọc
[[package/README|package/README.md]]. Muốn dựng lại đúng sản phẩm này thì đọc
[[reproduce-googlecast-mcp]].

---

## Bài học 30 giây

Bảy câu, mỗi câu trỏ tới bước nói kỹ về nó. Đọc bảy câu này rồi nhảy thẳng vào
bước bạn đang cần — thân bài **không lặp lại** chúng, nó đi tiếp.

1. Yêu cầu **đánh số, nói bằng hành vi** thì đừng viết ngay — hãy đối chiếu.
   Danh sách chưa đạt chính là kế hoạch. → [Bước 1](#bước-1--đọc-yêu-cầu-và-đối-chiếu-đừng-viết-ngay)
2. Việc gì **AI tự chấm được thì AI chấm**; việc gì phải **cảm nhận** mới biết
   thì bắt buộc đưa cho người. → [Bước 2](#bước-2--chọn-thành-phần-hai-loại-hai-cách-chọn)
3. Tác dụng phụ **không hoàn tác được** thì thiếu thông tin phải dẫn tới
   **KHÔNG LÀM**, không dẫn tới đoán. → [Bước 3](#bước-3--thiết-kế-cho-tác-dụng-phụ-không-hoàn-tác-được)
4. Người dùng lặp lại **"vẫn lỗi"** là tín hiệu **đổi hướng**, không phải tín
   hiệu sửa tiếp. → [Bước 4](#bước-4--chẩn-đoán-đọc-tín-hiệu-từ-người-dùng)
5. **Đo trước khi mô tả nguyên nhân** — điều kiện thật luôn hẹp hơn mô tả đầu
   tiên. → [Bước 5](#bước-5--đo-trước-khi-mô-tả-nguyên-nhân)
6. **Hai mẫu trùng nhau không đủ** để kết luận nguyên nhân hệ thống; và nghi mã
   sau cùng, kiểm biên giới trước. → [Bước 6](#bước-6--trước-khi-nghi-mã-kiểm-biên-giới)
7. Bài kiểm **chưa từng đỏ** thì chưa chứng minh gì; bài kiểm **không ai dám
   chạy** thì bằng không có. → [Bước 7](#bước-7--viết-bài-kiểm-mà-bạn-tin-được)

---

## Bước 1 — Đọc yêu cầu và đối chiếu, đừng viết ngay

**Nguyên tắc.** Yêu cầu được đánh số và diễn đạt bằng *hành vi quan sát được*
là loại yêu cầu quý nhất. Việc đầu tiên không phải viết mã, mà là đối chiếu
từng số với cái đang có — vì kết quả đối chiếu chính là kế hoạch.

**Việc làm cụ thể.** Lúc nhận yêu cầu này đã có sẵn một scaffold 11 tool Cast
chung chung từ phiên trước, chưa có phần đọc chữ thành tiếng. "Chạy được" lúc
đó chỉ có nghĩa: nối được thiết bị và liệt kê được. Đối chiếu ba yêu cầu ra
**đạt 1/3**.

**Prompt mẫu thật** (nguyên văn của người dùng, giữ nguyên lỗi gõ):

```
hãy kiểm tra xem mcp này đúng yêu cầu không:
1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả
```

**Quyết định chốt.** Hai yêu cầu chưa đạt được dịch thẳng thành danh sách module
phải viết: `tts.py`, `media_server.py`, `speaker_store.py`, và trong
`server.py` là `say()` cùng `_select_targets()`. `cast_manager.py` giữ nguyên
vì nó đã làm đúng việc của nó. Chi tiết ở [[package/requirement]].

🔧 *Chỗ tinh tế:* yêu cầu số 2 kéo theo một ràng buộc kiến trúc mà bản thân nó
không nói ra. Thiết bị Cast **tự đi tải** media qua HTTP; đưa nó đường dẫn file
là vô nghĩa. Vậy một server "nói được" **bắt buộc kiêm HTTP file server** trên
địa chỉ LAN. Ràng buộc này không nằm trong chữ nào của yêu cầu — nó nằm trong
giao thức. **Hãy đọc giao thức trước khi thiết kế module.**

---

## Bước 2 — Chọn thành phần: hai loại, hai cách chọn

**Nguyên tắc.** Không phải thành phần nào cũng đáng đem ra so sánh. Chia làm
hai loại và đối xử khác nhau:

- **Thành phần cảm nhận được** — kết quả của nó con người *nghe/nhìn* thấy hay
  dở. Loại này bắt buộc phải so, và người phải là người chấm.
- **Thành phần xương sống** — nó chỉ cần *chạy đúng*. Chọn theo mức bảo trì và
  độ phủ giao thức. So sánh dài dòng ở đây là lãng phí.

**Việc làm cụ thể.** Giọng đọc thuộc loại một: so bốn phương án, dựng thử, cho
người dùng nghe. Thư viện giao thức Cast thuộc loại hai: `pychromecast` là thư
viện Python duy nhất còn được bảo trì — **không qua so sánh nào cả**.

**Prompt mẫu thật** (nguyên văn):

```
có workinig speaker xác minh luôn tts -> HTTP -> cast chạy thật
```

Đọc kỹ câu này: nó **không hỏi phương án nào tốt hơn**. Nó bảo *hãy chạy hết
chuỗi trên thiết bị thật*. Người dùng đang chọn cách nghiệm thu, không phải
chọn công nghệ.

**Quyết định chốt.** edge-tts (`vi-VN-HoaiMyNeural` nữ, `vi-VN-NamMinhNeural`
nam): tự nhiên nhất, miễn phí, không cần khoá API. Ba phương án bị loại vì —
gTTS giọng máy móc, Google Cloud TTS cần khoá và tính phí, Piper chạy offline
nhưng yếu và setup nặng. **Chỉ một vòng.** Lý do một vòng là đủ: tiêu chí kỹ
thuật đã tự chấm xong trước khi đưa cho người, nên người chỉ còn phải trả lời
đúng một câu — *nghe có tự nhiên không*.

---

## Bước 3 — Thiết kế cho tác dụng phụ không hoàn tác được

**Nguyên tắc.** Khi hành động của phần mềm để lại dấu vết ngoài đời — âm thanh
phát ra phòng khách, tiền chuyển đi, email gửi rồi — thì **thiếu thông tin phải
dẫn tới KHÔNG LÀM GÌ**, không được dẫn tới đoán.

**Việc làm cụ thể.** Yêu cầu số 3 nói "hỏi user". Có ba đường:

| Đường | Vì sao chọn / không |
|---|---|
| Mặc định phát tất cả | **loại.** Tác dụng phụ vật lý, không thu lại được |
| MCP elicitation | **loại.** Là phán đoán — **CHƯA THỬ** trên client thật |
| Trả dữ liệu cho LLM tự hỏi lại | **chọn.** Chạy trên mọi client, không phụ thuộc tính năng nào |

**Prompt.** Người dùng không viết prompt cho việc này; họ chỉ nêu hành vi mong
muốn ở gạch đầu dòng số 3. Prompt dưới đây là **để bạn gõ lại** — *tái dựng*,
không phải nguyên văn:

```
Tool <tên tool> có tác dụng phụ KHÔNG HOÀN TÁC ĐƯỢC: <âm thanh phát ra phòng /
giấy in ra / tiền chuyển đi>. Hãy liệt kê mọi đường xử lý khi người dùng KHÔNG
nêu <tham số bắt buộc>, kèm lý do loại từng đường. Ràng buộc: thiếu thông tin
phải dẫn tới KHÔNG LÀM GÌ — không được đoán, không được mặc định làm cho tất
cả. Nếu đường bạn chọn dựa vào một tính năng của client mà ta CHƯA THỬ trên
client thật, hãy nói rõ đó là phán đoán.
```

**Quyết định chốt.** Thiếu `target` thì trả về `needs_speaker_selection` kèm
danh sách loa và một câu hướng dẫn LLM hỏi lại. **Không tổng hợp giọng, không
phát gì cả.** Đây là hợp đồng quan trọng nhất của sản phẩm, nên nó có mục eval
riêng: `say_without_choice_plays_nothing`.

🔧 *Một cái bẫy trong chính lời giải:* `"tất cả"` gửi tới **cả nhóm loa lẫn
thành viên nhóm** thì một loa vật lý nhận hai luồng. Cái khó là **API không hề
báo sai** — cả bốn mục đều trả `playing`. Dấu vết duy nhất nằm ở siêu dữ liệu:
hai mục có cùng `host`. Còn lại chỉ nghe mới biết. Bài học rộng hơn: **khi kết
quả API không phân biệt được đúng và sai, hãy đi tìm một trường siêu dữ liệu
phân biệt được** — nếu không thì bạn đang không kiểm gì cả.

---

## Bước 4 — Chẩn đoán: đọc tín hiệu từ người dùng

**Nguyên tắc.** Phần lớn tin nhắn giữa chừng chỉ là *dán lỗi vào*. Việc chẩn
đoán hoàn toàn thuộc về phía AI. Nhưng có vài **dạng tin nhắn mang thông tin
chẩn đoán**, và nhận ra chúng thì rẻ hơn nhiều so với đọc log.

| Dạng tin nhắn | Ý nghĩa thật |
|---|---|
| Yêu cầu đánh số, nói bằng hành vi | đây là bản đặc tả — hãy đối chiếu, đừng viết ngay |
| Dán một mẩu lỗi, không nói gì thêm | chẩn đoán là việc của bạn, đừng hỏi lại |
| **Lặp lại "vẫn lỗi"** | **đổi hướng: kiểm bản sửa đã được nạp chưa** |
| Hai tin nhắn mâu thuẫn về cùng thiết bị | so lịch sử ĐO để phân định lỗi thiết bị hay hồi quy |
| Câu hỏi lạc đề nhưng gấp | xử trước, đừng cố kéo về chủ đề |

**Việc làm cụ thể — tín hiệu bị bỏ lỡ.** Hai tin nhắn liên tiếp:

```
vẫn báo lổi khi kết nối với mcp llama-server
```
```
vẫn báo lổi:
```

Chữ **"vẫn"** xuất hiện lần thứ hai là lúc phải dừng sửa. Ở đây đã **bỏ lỡ một
vòng** và tiếp tục sửa mã, trong khi vấn đề là bản sửa chưa hề được nạp:
`systemctl enable --now` **không restart** một service đang chạy, nên tiến trình
cũ sống ba ngày với dòng lệnh cũ.

**Quyết định chốt.** Vá gấp đôi: `service.sh install` gọi `restart` tường minh,
**và** `status` in `/proc/<MainPID>/cmdline` để lần sau nhìn một cái là biết bản
đang chạy có phải bản vừa sửa không (`service.sh:78-80,112-115`). Nguyên tắc
rút ra: **khi một lỗi tốn nhiều vòng vì không quan sát được, hãy vá cả cái làm
nó khó quan sát**, đừng chỉ vá cái sai.

*Lưu ý:* bảng trên là thứ để **nhận ra**. Hai câu "vẫn báo lổi" phía trên là
**mảnh người dùng dán vào**, không phải prompt — chúng minh hoạ tín hiệu chứ
không dùng lại được.

**Prompt để bạn gõ lại** (*tái dựng*) — dùng đúng lúc nghe "vẫn lỗi" lần thứ hai:

```
Đây là lần thứ hai người dùng nói "vẫn lỗi" cho cùng một triệu chứng. DỪNG sửa
mã. Trước tiên hãy chứng minh bản sửa ĐÃ ĐƯỢC NẠP: in dòng lệnh thật của tiến
trình đang chạy, mốc thời gian của file đang được nạp, và phiên bản mà tiến
trình đó tự báo cáo. Nếu không quan sát được điều đó, hãy THÊM một cách quan
sát trước khi sửa tiếp.
```

---

## Bước 5 — Đo trước khi mô tả nguyên nhân

**Nguyên tắc.** Một mô tả nguyên nhân quá rộng thì vô dụng khi đi sửa: nó khớp
với cả trường hợp đúng lẫn trường hợp sai, nên không chỉ được vào đâu. Điều
kiện thật bao giờ cũng hẹp hơn, và chỉ đo mới ra.

**Việc làm cụ thể — chuỗi ba lần sửa trên cùng một triệu chứng.** Triệu chứng:
phát nhiều câu cùng lúc thì phần lớn hỏng.

| Lần | Giả thuyết | Cách vá | **Số đo sau khi vá** |
|---|---|---|---|
| 1 | dịch vụ chập chờn | thử lại 3 lần | **4/6, 101s** — vẫn hỏng |
| 2 | các lần thử vẫn chồng nhau | thêm khoá | **6/6, 12s** |
| 3 | khoá mức module gắn nhầm vòng lặp | một khoá cho mỗi vòng lặp | **6/6, 6.2s** |

Lần 1 dạy điều quan trọng nhất: **thử lại không cứu được khi các lần thử vẫn
chồng lên nhau. Phải chặn ở gốc.** Nếu chỉ nhìn "có đỡ hơn không" thì đã dừng
ở lần 1 và tưởng là xong.

**Prompt để bạn gõ lại** (*tái dựng*):

```
Trước khi vá, hãy viết ra một KỊCH BẢN ĐO cố định cho triệu chứng này (số
lượng, mức song song, cách tính đạt/hỏng) và chạy để lấy số nền. Sau MỖI lần
vá, chạy lại ĐÚNG kịch bản đó, ghi cả tỉ lệ đạt LẪN thời gian. Nếu tỉ lệ đã
100% mà thời gian còn cải thiện được thì nguyên nhân gốc vẫn chưa hết. Phát
biểu nguyên nhân bằng ĐIỀU KIỆN HẸP NHẤT mà số đo chống đỡ được — đừng phát
biểu rộng hơn.
```

**Khi chính phép đo là hành động không hoàn tác được.** Bước 3 nói *thiếu thông
tin thì không làm*; bước này nói *đo lại bằng cùng một kịch bản*. Hai câu đó va
nhau khi phép đo tự nó để lại dấu vết ngoài đời: ở đây dồn 6 lần đọc × 3 lần vá
là 18 lần loa kêu; với máy in nhãn thì đó là **18 tờ giấy thật**. Cách gỡ, theo
thứ tự:

1. **Đo trên bản giả trước.** Thay đúng biên giới ra-ngoài-đời bằng bản giả có
   *cùng đặc tính gây lỗi* — ở đây là "từ chối kết nối đồng thời". Ba lần vá
   khoá TTS đều phân định được ở tầng này; thiết bị thật không cần tham gia.
2. **Chỉ lên thiết bị thật ở tầng phải xin phép**, và chỉ để **xác nhận lần
   cuối**, không phải để dò tìm. Đó là lý do `--hardware` mặc định tắt.
3. **Giảm N và nêu rõ.** Nếu buộc phải đo thật, hạ số lần xuống mức nhỏ nhất
   còn phân biệt được hai giả thuyết, rồi ghi N vào cột "số lần" — chứ không
   im lặng đo ít đi.

Dấu hiệu bạn đang vi phạm: cột "số lần" trong bảng kiểm chứng tăng lên mà không
ai kịp hỏi *lần này có cần chạy thật không*.

**Quyết định chốt.** Mỗi lần vá đều **đo lại bằng cùng một kịch bản** (dồn 6 yêu
cầu song song, chạy trên **bản giả**) và ghi cả **tỉ lệ đạt lẫn thời gian**. Chỉ số thứ hai mới lộ ra
lần 3 còn cải thiện được. Chi tiết ở [[package/technical-docs]].

🔧 *Vì sao lần 3 khó thấy:* một `asyncio.Lock` mức module chỉ gắn vào vòng lặp
**khi CÓ TRANH CHẤP** — đường nhanh của `acquire()` trả về trước khi chạm tới
`_get_loop()`. Nên lỗi ẩn hoàn toàn cho tới lần đầu hai render chồng nhau, và
sau đó mọi vòng lặp khác nhận `RuntimeError: bound to a different event loop`.
Mô tả đầu tiên — *"chạy `asyncio.run()` hai lần là hỏng"* — **sai vì quá rộng**:
chạy hai lần mà không có tranh chấp thì hoàn toàn bình thường. Vá bằng
`WeakKeyDictionary` khoá theo vòng lặp (`tts.py:29-46`).

---

## Bước 6 — Trước khi nghi mã, kiểm biên giới

**Nguyên tắc.** Với phần mềm nói chuyện với thiết bị vật lý, phần lớn "lỗi" nằm
ngoài mã. Trước khi đọc lại mã của mình, hãy kiểm **biên giới gần nhất** giữa
mã và thế giới.

**Việc làm cụ thể.** Triệu chứng: `wait timed out` khi phát ra một thiết bị. Đã
kiểm mDNS — thấy. Đã ping — thông. Đọc mã — không có gì sai. Biên giới thật là
**TCP cổng 8009**: `nc -z <ip> 8009` báo refuse. Thiết bị treo; rút điện cắm
lại là hết.

**Prompt để bạn gõ lại** (*tái dựng*):

```
Trước khi đọc lại mã của tôi: liệt kê các TẦNG "thấy được" giữa mã này và
thiết bị, từ xa tới gần (phát hiện dịch vụ → ICMP → TCP tới đúng cổng → bắt
tay giao thức). Cho tôi một lệnh kiểm cho TỪNG tầng. Tôi sẽ chạy và đưa kết
quả; chỉ nghi mã sau khi tầng gần nhất đã thông.
Nếu kết luận của bạn dựa vào việc nhiều thiết bị cùng hỏng một kiểu, hãy nói
rõ chúng có đang cùng chịu một điều kiện môi trường nào không.
```

**Quyết định chốt.** Thêm `nc -z <ip> 8009` vào bảng xử lý sự cố trong
[[package/README#không-dựng-lại-được-thì-hỏng-ở-đâu]]. Ba tầng "thấy được"
(mDNS · ICMP · TCP) không tương đương nhau, và chỉ tầng cuối mới nói lên điều
bạn cần biết.

**Sai lầm suy luận đã phạm ở đây, đáng ghi lại.** Cả **hai** Nest Hub cùng đóng
cổng 8009, nên đã kết luận *"Nest Hub bỏ cổng 8009 do firmware"*. Nghe rất
thuyết phục — hai mẫu, cùng model, cùng hành vi. **Nó sai.** Cả hai chỉ đang
treo cùng lúc. **Hai mẫu trùng nhau không đủ để suy ra nguyên nhân hệ thống**,
đặc biệt khi cả hai cùng chịu một điều kiện môi trường (cùng mạng, cùng thời
điểm, cùng lần mất điện).

🔧 *Một biên giới nữa, dạng khác:* tên máy chứa dấu gạch dưới thì **không bao
giờ** xin được chứng chỉ TLS — CA/B Forum cấm `_` trong tên máy. Mà Claude
Desktop lại **bắt buộc** https. Hai ràng buộc gặp nhau thành **ngõ cụt tuyệt
đối**: không có lượng mã nào thoát ra được, phải đổi tên miền. Nhận ra sớm một
ngõ cụt tuyệt đối tiết kiệm nhiều hơn bất kỳ mẹo gỡ lỗi nào. **Dấu hiệu nhận
biết: khi hai ràng buộc đều đến từ bên ngoài và mâu thuẫn nhau, hãy đổi đầu
vào, đừng đổi mã.**

---

## Bước 7 — Viết bài kiểm mà bạn tin được

**Nguyên tắc.** Hai câu ràng buộc lẫn nhau: *bài kiểm chưa từng đỏ thì chưa
chứng minh được gì*, và *bài kiểm không ai dám chạy thì bằng không có*. Bỏ vế
nào cũng hỏng — vế đầu đẩy bạn tới bài kiểm tốn kém, vế sau kéo bạn về bài kiểm
rẻ mà rỗng.

**Việc làm cụ thể.** Cách cân bằng ở đây:

1. **Chia tầng theo tác dụng phụ.** Tầng mặc định không chạm gì ngoài thư mục
   tạm và chạy trong 5 giây — đủ rẻ để chạy sau mỗi lần sửa. Tầng gọi mạng thật
   và tầng phát tiếng thật phải bật tường minh, và tầng cuối phải xin phép.
2. **Chứng minh bài kiểm có răng bằng cách gieo lỗi**, với kỳ vọng viết TRƯỚC,
   gieo vào **bản sao** trong thư mục tạm.
3. **Trả chi phí bằng cách gieo có mục tiêu**: mỗi lỗi gieo chỉ chạy đúng tập
   mục liên quan. Cách "mỗi lỗi gieo × toàn bộ bài kiểm" đã đo ở **phiên đóng
   gói TRƯỚC**: 68 lỗi gieo × ~10s = **12 phút**, và nó tự phá vế thứ hai. Cách
   có mục tiêu, đo ở **phiên NÀY**: 60 lỗi gieo trong **56 giây**. Hai con số
   không so trực tiếp được — số lỗi gieo đã đổi (68 → 60) vì cách chia mục eval
   đổi. Thứ so được là **chi phí mỗi lỗi gieo**: ~10s xuống ~0,9s.
4. **Thêm đối chứng kỳ-vọng-XANH** đi qua mã thực thi (đổi tên biến cục bộ,
   tách biểu thức). Thêm dòng chú thích thì vô hại tới mức không kiểm được gì.

Toàn bộ luật và bằng chứng: [[package/eval/README]].

**Prompt để bạn gõ lại** (*tái dựng*) — người dùng không yêu cầu phần này, nó
do phía xây tự đặt ra:

```
Hãy chứng minh bộ kiểm của dự án này CÓ RĂNG, theo đúng thứ tự:
1. Chia mục kiểm thành các TẦNG theo tác dụng phụ. Tầng mặc định không chạm gì
   ngoài thư mục tạm và phải chạy xong trong vài giây.
2. Với MỖI mục kiểm, viết TRƯỚC một lỗi gieo sẽ làm nó đỏ. Mục nào không nghĩ
   ra được lỗi gieo thì đánh dấu nghi phạm — nó có thể chẳng kiểm gì cả.
3. Gieo lỗi vào BẢN SAO mã nguồn trong thư mục tạm, không bao giờ vào cây sản
   phẩm. Mỗi ca chỉ chạy tập mục liên quan, để tổng chi phí còn chạy nổi.
4. Thêm vài ĐỐI CHỨNG kỳ-vọng-XANH sửa mã đang thực sự chạy mà không đổi hành
   vi (đổi tên biến cục bộ, tách biểu thức). Chú thích không tính là đối chứng.
5. Báo cáo in "đã chạy X/Y" theo CẢ HAI chiều, và coi X<Y là hỏng toàn cục.
Gieo lỗi rồi mà vẫn xanh thì phân loại theo đúng ba nhánh: test giả / kỳ vọng
sai / lỗi gieo không quan sát được. Đừng nới kỳ vọng cho xanh.
```

**Quyết định chốt — ba nhánh cho "lẽ ra đỏ mà lại xanh".** Gieo lỗi rồi mà bài
kiểm vẫn xanh thì có đúng ba khả năng, và trộn chúng lại là hỏng:

| Nhánh | Nghĩa là | Làm gì |
|---|---|---|
| **Test giả** | bài kiểm không chạm vào chỗ đó | sửa bài kiểm cho bắt được thật |
| **Kỳ vọng sai** | có chạm, nhưng đòi sai điều | sửa kỳ vọng **theo yêu cầu, có trích nguồn** — cấm nới cho xanh |
| **Lỗi gieo không quan sát được** | bị một cơ chế khác che | đổi lỗi gieo, hoặc ghi CHƯA PHỦ **kèm cơ chế che** |

Thiếu nhánh thứ ba là ép người ta làm bài kiểm tệ đi để thoả luật.

Trong chính phiên đóng gói này, lượt kiểm ngược đã lộ ra **cả nhánh 1 lẫn nhánh
2** — mỗi nhánh một ca thật, ghi chi tiết ở
[[package/eval/README#ba-lỗi-thật-do-chính-lượt-kiểm-ngược-này-lộ-ra]].

🔧 *Bốn cái bẫy cụ thể, đều đã cắn thật:*

- **Sập giữa chừng.** Một `KeyError` làm mọi mục sau im lặng biến mất mà báo cáo
  vẫn xanh. Vá: **đếm đủ trước khi đếm xanh** — luôn in `đã chạy X/Y mục đăng
  ký`, `X < Y` là hỏng toàn cục. Khớp 0 mục cũng không được coi là đạt.
- **Tráo bối cảnh nửa vời.** Tráo `_manager` mà quên `_media_server` → lỗi hiện
  ra ở chỗ chẳng liên quan. **Tráo nửa nguy hơn không tráo.**
- **Thay thế đệ quy.** `module.asyncio` **chính là** module `asyncio` toàn cục,
  nên `module.asyncio.sleep = lambda: ...gọi lại asyncio.sleep` là đệ quy vô
  hạn — và nó hiện ra ở ba mục chẳng liên quan. Giữ tham chiếu gốc, bọc proxy.
- **Bằng chứng hết hạn.** Đọc `player_state` ngay lúc lệnh trả về là đòi một
  trạng thái đã qua: đo được `say()` mất 5.4s trong khi clip chỉ 2.26s — lúc trả
  về loa đã phát **xong**. Phải kiểm **dấu vết bền**: `content_id` khớp URL và
  `duration > 0`. Cùng họ với nó: khẳng định phải sống trong vòng đời của thứ nó
  tham chiếu — đếm file sau khi thư mục tạm đã đóng là đếm vào chỗ trống.

---

## Cách đã kiểm chứng

Cột "số lần" là **số** hoặc **CHƯA ĐẾM** — không ghi "nhiều".

*Vì sao hai hàng nền tảng nhất lại là CHƯA ĐẾM.* `say` ra Kitchen speaker và
"dò thiết bị + lọc loa" là hai việc người dùng tự gọi trong sinh hoạt hàng
ngày, rải qua nhiều phiên, **trước khi có bất kỳ bộ đếm nào**. Con số thật nằm
trong lịch sử hội thoại chứ không nằm trong log, nên đếm lại bây giờ sẽ là
**dựng số**, tệ hơn là thú nhận chưa đếm. Cận dưới ≥9 và ≥7 lấy từ số lần xuất
hiện đếm được trong hội thoại. Định đoạt: **chấp nhận**. Từ nay hai kịch bản
này đã có mục eval tương ứng (`say_casts_to_chosen_speaker`,
`manager_discover_persists_devices`, và tầng `--hardware`), nên lần sau sẽ có
số đếm thật.

| Kịch bản | Số lần | Biên / điều kiện | Kết quả |
|---|---|---|---|
| `say` → Kitchen speaker | CHƯA ĐẾM (≥9) | bình thường | `playing`; người dùng xác nhận **nghe được** |
| `say` → Working display (Nest Hub) | 5, rải 2 ngày | **thiết bị treo rồi khởi động lại** | 3 lần đầu THẤT BẠI (`wait timed out`, 8009 refuse); sau khi khởi động lại: 1 OK + 3 clip đo |
| Đo thời lượng phát | 3 clip (2.09 / 4.27 / 7.10s) | độ dài khác nhau | cả 3 `PLAYING` đủ `duration` → `idle_reason=FINISHED`; log HTTP xác nhận có tải file (200) |
| Thương lượng `protocolVersion` | 3 phiên bản | client cũ và mới | cả 3 trả đúng version |
| MCP client thật qua https (nginx + TLS) | 1 | — | initialize + 13 tool + `list_speakers` → 4 loa |
| MCP client thật qua LAN `:8765` | 1 | — | như trên |
| Client trình duyệt (Origin `http://192.168.1.99:8383`) | 1 | **có CORS** | preflight 200 + allow-origin đúng; initialize 200 JSON; 13 tool |
| `--json-response --stateless` | 1 | **client khắt khe** | trả `application/json`; `tools/call` không cần session id |
| Dò thiết bị + lọc loa | CHƯA ĐẾM (≥7) | mạng thật 8 thiết bị | 4 loa / 4 thiết bị hình ảnh |
| `target="all"` | 2: trước và sau khi sửa | **4 loa song song** | trước: 4 `playing` nhưng **chồng luồng**; sau: 3 loa riêng lẻ |
| Nhiều loa cách phẩy | 1 | 2 loa | cả 2 `playing` |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 2 | **phần tử hỏng** | loa thật nhận đúng audio; phần tử hỏng `error` riêng; tổng thể `ok`; `say()` 5.4s so với clip 2.26s |
| **TTS dồn 6 yêu cầu song song** | **3**: trước vá / sau vá khoá / sau vá khoá-theo-vòng-lặp | **dịch vụ từ chối kết nối đồng thời** | 4/6 (101s) → 6/6 (12s) → **6/6 (6.2s)**, 0 file 0 byte |
| Khoá qua 2 vòng lặp có tranh chấp | 2: trước và sau vá | `asyncio.run()` hai lần | trước: vòng 2 `RuntimeError bound to a different event loop`; sau: **cả hai vòng đều chạy** |
| **Eval offline** | **7 phiên** | không tiếng | 35 → 43 → 67 → 138 → 49 → 77 → **57/57 ĐẠT** (số mục đổi vì cách chia mục đổi) |
| Eval `--online` | 4 | cần internet | 157 → 49 → 82 → **3/3 ĐẠT** |
| Eval `--hardware` (xin phép mỗi lần) | 6 | **cast thật, phát tiếng** | 37 → 48 → 67 → 157 → 49 → **78/78, ĐẠT NGAY LẦN ĐẦU** |
| **Kiểm ngược bài kiểm** | 1 lượt đầy đủ (2026-08-28) | 60 lỗi gieo + 3 đối chứng | **60/60 ĐẠT, phủ 57/57 mục, 56s**; lộ 1 test giả + 1 kỳ vọng sai + 1 lỗi gieo không áp được |
| **Nghiệm thu DoD trên clone sạch** | 1 (2026-08-28) | cổng rỗi 8797, không đụng service thật | clone → `uv sync` → chạy → initialize 200 → **13 tool** → `list_speakers` trả loa thật; stdio cũng 13 tool |

**Biên và điều kiện xấu đã quan sát được (thật, không phải giả định):** TCP 8009
refuse → timeout · mDNS sót thiết bị đã lưu → `DeviceNotFoundError` tự mâu
thuẫn · Origin ngoài allowlist → 403 · Host không tin → 421 · mở `/mcp` bằng
trình duyệt → 406 (**đúng đặc tả, không phải lỗi**) · preflight chưa bật CORS →
405 không header · bỏ `target` → `needs_speaker_selection`, không phát gì · cài
lại service khi đang chạy → tiến trình KHÔNG đổi · `all` gồm cả nhóm lẫn thành
viên → chồng luồng mà API vẫn báo `playing`.

**Quan sát mới trong chính phiên đóng gói này:** `pkill -f "<mẫu>"` khớp luôn
lệnh bash đang chạy và **tự giết shell** (exit 144) — ngõ cụt này đã **tái hiện
sống**; cách thoát là lấy PID từ `ss -ltnp` rồi `kill` theo PID. Và: cổng audio
8766 mở **lười** — `ss` cho thấy service thật chỉ đang nghe 8765, vì chưa `say`
lần nào kể từ lần khởi động gần nhất; nghĩa là **quét cổng lúc máy vừa khởi
động sẽ không thấy bề mặt tấn công đó**.

**CHƯA THỬ** (nói thẳng, đừng suy ra từ im lặng): giọng nam
`vi-VN-NamMinhNeural` bằng tai · tham số `rate` bằng tai · service sống sót qua
reboot máy (đã `enable`, chưa reboot) · địa chỉ đã lưu bị cũ vì loa đổi IP →
nhánh quét lại · chặn IP ở nginx (đã đồng ý bật, hai dòng vẫn đang comment) ·
MCP elicitation trên client thật.

---

## Đem sang bài khác

Phương pháp ở đây dùng lại được cho **bất kỳ MCP server nào điều khiển thứ có
thật**: đèn, máy in, robot, cổng thanh toán, máy gửi email.

1. Đọc **giao thức** của thiết bị trước khi chia module — nó áp đặt ràng buộc mà
   yêu cầu không nói ra (ở đây: server bắt buộc kiêm HTTP file server).
2. Chia thành phần thành **cảm nhận được** và **xương sống**; chỉ loại đầu mới
   đáng đem so, và người phải là người chấm.
3. Mọi hành động **không hoàn tác được**: thiếu thông tin thì **không làm**, trả
   ngữ cảnh cho mô hình đi hỏi.
4. Mỗi lần vá, **đo lại bằng cùng một kịch bản**, ghi cả tỉ lệ đạt lẫn thời gian.
5. Nghi mã sau cùng: kiểm **biên giới gần nhất** (TCP, chứ không phải ping).
6. Bài kiểm chia tầng theo tác dụng phụ; chứng minh nó có răng bằng **gieo lỗi
   có mục tiêu**, kỳ vọng viết trước, gieo vào bản sao.

**Prompt khởi động cho bài của bạn.** Điền ba chỗ `<…>` rồi dán cho AI. Đây là
prompt cho **bài tương tự**, khác với [[reproduce-googlecast-mcp]] — file đó
dựng lại đúng sản phẩm này, không dùng cho bài khác được.

```
Xây một MCP server điều khiển <THIẾT BỊ: máy in nhãn / đèn / cổng thanh toán>
qua <MẠNG/GIAO THỨC: LAN, mDNS + TCP …>.

Yêu cầu, diễn đạt bằng HÀNH VI quan sát được:
1. Dò <thiết bị> trong <phạm vi>, LỌC đúng loại cần dùng khỏi các loại khác,
   và LƯU BỀN danh sách ra đĩa. Lưu là GỘP theo id, không ghi đè — một lần dò
   sót không được làm mất thiết bị đã biết.
2. Một tool <hành động chính>(nội dung, đích?, <tuỳ chọn>) thực hiện việc
   chính lên thiết bị được chọn.
3. Nếu người dùng KHÔNG chọn đích thì KHÔNG LÀM GÌ CẢ — trả về trạng thái
   "cần chọn đích" kèm danh sách và câu hướng dẫn để LLM hỏi lại người dùng.
   <hành động chính> là KHÔNG HOÀN TÁC ĐƯỢC: <giấy in ra / tiếng phát ra>.

TRƯỚC KHI CHIA MODULE, hãy đọc giao thức của thiết bị và liệt kê ra cho tôi
những RÀNG BUỘC KIẾN TRÚC mà ba yêu cầu trên KHÔNG nói ra nhưng giao thức áp
đặt — ví dụ thiết bị có tự đi lấy dữ liệu không, nó cần địa chỉ nào để tới
được ta, thư viện có blocking không. Chỉ sau khi liệt kê xong mới đề xuất
danh sách module.

Sau đó, với mỗi thành phần phải chọn: phân loại nó là "cảm nhận được" (kết quả
con người phải nghe/nhìn mới chấm được) hay "xương sống" (chỉ cần chạy đúng).
Loại đầu thì dựng thử vài phương án cho tôi tự chấm; loại sau thì chọn theo
mức bảo trì và độ phủ giao thức, đừng bắt tôi so.
```

Muốn dựng lại **đúng sản phẩm này** thì dùng [[reproduce-googlecast-mcp]].

---

## Phụ lục — định đoạt lỗ hổng sau khi chấm L2

Người đọc sạch (`method-note-evaluator-solo`, context sạch, chấm bằng đề đối
chứng "MCP máy in nhãn LAN") kết luận **L2** và nêu 7 lỗ hổng. Ghi định đoạt
từng cái, kể cả cái đã sửa — để lần sau không ai phải đoán cái nào bị bỏ quên.

| # | Lỗ hổng | Định đoạt | Làm gì |
|---|---|---|---|
| 1 | 5/7 bước không có prompt gõ lại được | **sửa ngay** | thêm khối "Prompt để bạn gõ lại" vào Bước 3, 4, 5, 6, 7; đánh dấu rõ **tái dựng**, không phải nguyên văn |
| 2 | "Đem sang bài khác" chỉ có nguyên tắc, không có prompt | **sửa ngay** | thêm prompt khởi động điền-chỗ-trống ngay trên phụ lục này |
| 3 | Tóm tắt lặp lại thân bài | **sửa ngay** | "Bài học 30 giây" thành **con trỏ** có neo tới từng bước, không còn là bản sao |
| 4 | Không nêu xung đột: phép đo lặp lại mà bản thân nó không hoàn tác được | **sửa ngay** | thêm mục *"Khi chính phép đo là hành động không hoàn tác được"* ở Bước 5, ba đường gỡ theo thứ tự. **Đây là lỗ hổng phương pháp thật**, và nó cũng là thiếu sót của bộ luật đóng gói → đã đề xuất vá bản chuẩn ở [[phan-hoi-quy-trinh]] |
| 5a | Tự khen: *"bằng chứng tốt nhất rằng bước này không phải nghi thức"* | **sửa ngay** | xoá; bằng chứng đã tự nói |
| 5b | Tự bào chữa: *"đó là quyết định đúng chứ không phải sự lười"* | **sửa ngay** | xoá; luận cứ "thư viện duy nhất còn bảo trì" đã đủ |
| 5c | `transmission_level: L2` trong frontmatter của chính note | **sửa ngay, theo cách khác** | **bỏ khỏi note**, chỉ giữ ở thẻ đăng ký [[packages/googlecast-mcp]]. Lý do: note tự dán mức cho mình sẽ mồi sẵn kỳ vọng cho người đọc sạch tiếp theo, làm nhiễu chính phép chấm. Mức vẫn tra được, chỉ là không nằm trong thứ đem đi chấm |
| 6 | "68 × 10s" đặt cạnh "60 lỗi gieo / 56s" như so sánh trực tiếp | **sửa ngay** | nói rõ 68 là phiên trước, 60 là phiên này, và thứ so được là **chi phí mỗi lỗi gieo** (~10s → ~0,9s) |
| 7 | Hai hàng "CHƯA ĐẾM (≥9)" và "(≥7)" | **chấp nhận + ghi lý do** | đếm lại bây giờ là **dựng số**; lý do và cận dưới ghi ngay đầu mục "Cách đã kiểm chứng". Đã có mục eval phủ hai kịch bản này nên lần sau có số thật |

Không có lỗ hổng nào bị xếp *ngoài phạm vi*.
