---
product: googlecast-mcp
loại: harness vận hành (MCP server chạy như systemd service)
ngày: 2026-08-21
transmission_level: L2
chấm_bởi: method-note-evaluator-solo (context sạch)
ngày_chấm: 2026-08-21
---

# Cách xây một MCP server điều khiển thiết bị thật trong nhà

## Bài học 30 giây

1. **Yêu cầu đánh số, viết bằng hành vi, đáng hơn mọi bản đặc tả dài.** Ba câu
   người dùng gõ ra đã làm luôn vai trò tiêu chí nghiệm thu, không cần dịch lại.
2. **Việc gì gây tác dụng ra thế giới vật lý thì thiếu thông tin phải hỏi, cấm
   đoán.** Không biết phát loa nào thì đừng phát cả nhà. Phát nhầm không rút lại được.
3. **Dựng bản chạy được trước, rồi đối chiếu với yêu cầu để lộ chỗ thiếu.**
   Danh sách yêu cầu chưa đạt chính là danh sách module cần viết — không cần
   một bước "thiết kế kiến trúc" riêng.
4. **API báo "thành công" không phải bằng chứng nó đúng.** Bốn cái loa cùng báo
   `playing` trong khi đang chồng tiếng lên nhau. Chỉ tai người mới biết.
5. **Bộ test chưa từng đỏ là bộ test chưa chứng minh được gì** — và tệ hơn cả
   một mục test thiếu, là một mục test **xanh giả**: nó tạo cảm giác đã được che.
6. **Người dùng lặp lại y hệt một câu than phiền = tín hiệu sai hướng.** Dừng
   sửa. Kiểm xem bản sửa đã được nạp chưa.
7. **Hai mẫu trùng nhau chưa đủ để kết luận nguyên nhân hệ thống.** Hai thiết bị
   cùng hỏng một kiểu vẫn có thể chỉ là hai thiết bị đang treo.

Muốn thực thi thì đọc `package/` — README là đường cài, `harness-spec.md` là
kiến trúc harness, `eval/` là bằng chứng. Note này chỉ nói **cách nghĩ**.

**Đọc note này thế nào:** Bước 1–5 và 9–11 là **tuần tự** — làm theo đúng thứ
tự. Bước 6–8 là **sổ tay tra cứu**, đọc khi gặp sự cố, không cần đọc trước.

Dấu 🔧 đánh dấu chi tiết kỹ thuật cụ thể của riêng product này. Bỏ qua được nếu
bạn chỉ muốn lấy phương pháp mang sang việc khác.

---

## Bước 1 — Đọc yêu cầu như đọc tiêu chí nghiệm thu

**Nguyên tắc.** Có những tin nhắn của người dùng đáng chép nguyên văn và treo
lên tường. Dấu hiệu nhận ra: nó **được đánh số** và mỗi số **mô tả một hành vi
quan sát được**, chứ không mô tả công nghệ.

**Việc làm cụ thể.** Toàn bộ product này sinh ra từ một tin nhắn duy nhất:

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Không diễn giải lại, không "chuẩn hoá" thành user story. Chép thẳng vào tài liệu
yêu cầu rồi treo bảng kiểm bên cạnh. Lúc đó bản đang có đạt **1/3**.

**Quyết định chốt.** Ba câu này thành mục lục của cả `requirement.md` lẫn cấu
trúc bộ eval. Việc diễn giải lại yêu cầu chỉ làm mất thông tin, không thêm.

**Prompt mẫu thật** *(nguyên văn của người dùng — dùng lại được cho việc khác)*:

```
hãy kiểm tra xem <thứ này> đúng yêu cầu không:
1. <hành vi 1>
2. <hành vi 2>
3. <hành vi 3>
```

Cách gõ này ép AI đối chiếu từng mục thay vì tán thành chung chung. Nếu bạn là
người ra yêu cầu, đây là dạng câu đáng tập.

---

## Bước 2 — Chọn thư viện: tách "cảm nhận được" khỏi "xương sống"

**Nguyên tắc.** Không phải lựa chọn nào cũng đáng so sánh. Chia làm hai loại:

- **Thành phần người dùng CẢM NHẬN ĐƯỢC** (giọng đọc, giao diện, văn phong) →
  bắt buộc so sánh, và **bắt buộc để người dùng tự nghe / tự nhìn**. AI không
  chấm hộ được chuyện "nghe có tự nhiên không".
- **Thành phần XƯƠNG SỐNG** (thư viện giao thức, driver) → chọn theo **mức độ
  còn được bảo trì** và **độ phủ giao thức**. So sánh ở đây phần lớn là diễn.

**Việc làm cụ thể.** Giọng đọc: so 4 phương án, tự chấm phần kỹ thuật, còn phần
"nghe thế nào" thì dựng mẫu cho người dùng nghe.

| Phương án | Tự nhiên | Cần khoá | Chi phí | Kết |
|---|---|---|---|---|
| gTTS | máy móc | không | 0 | loại |
| Google Cloud TTS | rất tốt | **có** | có phí | loại |
| Piper (offline) | yếu | không | 0 | loại |
| **edge-tts** | **tốt nhất trong nhóm miễn phí** | không | 0 | **chọn** |

Thư viện Cast: **pychromecast, không qua so sánh nào.** Nó là thư viện Python
duy nhất còn được bảo trì phủ giao thức Cast. Dựng một bảng so sánh giả ở đây
chỉ là trình diễn quy trình.

**Quyết định chốt.** edge-tts với `vi-VN-HoaiMyNeural` (nữ) /
`vi-VN-NamMinhNeural` (nam). Và **chỉ một vòng nghe thử, không lặp**. Vòng thứ
hai tốn thời gian người dùng mà gần như không đổi kết quả.

**Prompt mẫu thật** *(tái dựng)*:

```
So sánh <N> phương án cho <thành phần>. Tự chấm các tiêu chí kỹ thuật
(cần khoá API không, chi phí, phụ thuộc, mức bảo trì) và kết luận thẳng.
Riêng tiêu chí <cảm nhận: nghe/nhìn/đọc>, đừng tự chấm — hãy dựng mẫu thật
của từng phương án để tôi tự <nghe/nhìn>. Một vòng thôi.
```

Câu **"một vòng thôi"** là phần đáng chép nhất. Không có nó, việc so sánh phình
ra vô hạn.

---

## Bước 3 — Thiết kế chỗ thiếu thông tin, trước khi viết chức năng chính

**Nguyên tắc.** Với việc có tác dụng phụ không rút lại được, **hành vi khi
thiếu thông tin quan trọng ngang hành vi khi đủ thông tin**. Thiết kế nó trước,
đừng để thành phần xử lý ngoại lệ.

**Việc làm cụ thể.** Ba lựa chọn khi người dùng không nói phát loa nào:

| Lựa chọn | Vì sao loại / chọn |
|---|---|
| Mặc định phát tất cả | **Loại.** Tác dụng phụ vật lý, không rút lại được |
| MCP elicitation (giao thức tự hỏi) | **Loại.** Nhiều client chưa hỗ trợ |
| Trả dữ liệu + câu hướng dẫn cho mô hình tự hỏi | **Chọn.** Chạy ở mọi client |

Lựa chọn thứ ba đáng nhớ như một khuôn mẫu chung: **chỗ nào giao thức còn non,
đẩy việc lên tầng ngôn ngữ.** Thay vì đòi client hỗ trợ một tính năng, trả về
một cấu trúc kèm một câu tiếng Anh dặn mô hình phải làm gì tiếp.

🔧 Cụ thể: trả `{"status": "needs_speaker_selection", "speakers": [...],
"message": "No target given. Ask the user which speaker…"}` — và **không tổng
hợp âm thanh**, **không cast gì cả**. Cả hai điều đó có mục eval riêng.

**Quyết định chốt.** Thiếu tên loa ⇒ không phát, không tổng hợp, trả câu hỏi.

---

## Bước 4 — Tìm ràng buộc mà kiến trúc áp đặt, trước khi tự nghĩ kiến trúc

**Nguyên tắc.** Trước khi thiết kế, hỏi: **giao thức phía kia bắt buộc mình
phải có gì?** Câu trả lời thường quyết định hình dạng hệ thống nhiều hơn mọi
lựa chọn kiến trúc của bạn.

**Việc làm cụ thể.** Ràng buộc lớn nhất ở đây: **thiết bị Cast tự đi tải media
qua HTTP.** Nó không đọc được đường dẫn file trên máy bạn. Hệ quả không né được:
một MCP server "biết nói" **bắt buộc kiêm luôn một HTTP file server**.

Không tìm ra điều này sớm thì bạn sẽ viết xong phần TTS, gọi cast, thấy thiết bị
nháy sáng rồi tắt, và mất nhiều giờ nghi ngờ nhầm chỗ.

🔧 Chi tiết dễ nhầm: **bind và địa chỉ quảng bá là hai thứ khác nhau.**
`media_server.py:76` bind `0.0.0.0`, còn URL đưa cho loa dựng từ `lan_ip()`.
Nhầm hai thứ này thì `netstat` nhìn hoàn hảo mà loa vẫn câm.

**Prompt mẫu thật** *(tái dựng)*:

```
Trước khi thiết kế: giao thức <X> bắt buộc phía tôi phải cung cấp những gì?
Liệt kê các ràng buộc không né được, kèm hệ quả kiến trúc của từng cái.
Đừng đề xuất giải pháp vội.
```

**Quyết định chốt.** Media server là thành phần bắt buộc, không phải tuỳ chọn.
Ghim cổng của nó (8766) để chỉ phải viết một luật tường lửa.

---

## Bước 5 — Giao cho AI viết bản chạy được đầu tiên

**Nguyên tắc.** Đừng thiết kế trọn gói từ đầu. **Dựng một bản chạy được trước,
rồi đối chiếu với danh sách yêu cầu để lộ ra chỗ thiếu.** Danh sách yêu cầu
chưa đạt chính là danh sách module cần viết — bạn không cần một bước "thiết kế
kiến trúc" riêng, vì việc đối chiếu đã tự sinh ra ranh giới chia việc.

**Việc làm cụ thể.** Bản scaffold đầu tiên của product này **không sinh ra
trong phiên chính**; nó đến từ một phiên trước và được bàn giao lại bằng một
file. Phiên chính mở đầu đúng bằng một câu:

```
hãy đọc plans/reports/handoff-260807-1157-googlecast-mcp-scaffold.md để tiếp tục
```

Bản scaffold đó có 11 tool điều khiển Cast chung chung và **chưa hề có TTS**.

Chức năng chính của product ra đời từ đúng cái prompt ở Bước 1 — người dùng
không mô tả giải pháp, chỉ liệt kê 3 yêu cầu hành vi và bảo *"kiểm tra xem đúng
yêu cầu không"*. Kết quả đối chiếu: **đạt 1/3**. Chỉ có phần dò thiết bị, mà còn
chỉ cache trong RAM nên mất sạch khi khởi động lại. Yêu cầu 2 và 3 thiếu hoàn
toàn.

Ba mục chưa đạt đó biến thẳng thành ba module mới, mỗi module một trách nhiệm:

| Chỗ thiếu | Sinh ra |
|---|---|
| dò xong không lưu lại được | `speaker_store.py` |
| chưa có text thành tiếng nói | `tts.py` |
| loa không tải được file trên máy | `media_server.py` |
| chưa có lệnh "nói", chưa biết hỏi lại khi thiếu loa | tool `say()` + hàm chọn loa trong `server.py` |

**Quyết định chốt.** Viết theo từng module có trách nhiệm đơn lẻ, **không viết
trọn một lượt**. Nhờ vậy `cast_manager.py` được giữ nguyên vẹn: nó vốn đã làm
đúng việc của nó, chỗ thiếu nằm ở tầng trên. Sửa cái đang đúng là cách nhanh
nhất để hỏng thêm.

**Prompt mẫu thật** *(nguyên văn — chính là prompt ở Bước 1, dùng lại được cho
việc khác)*:

```
hãy kiểm tra xem <thứ này> đúng yêu cầu không:
1. <hành vi 1>
2. <hành vi 2>
3. <hành vi 3>
```

Điểm hay của cách gõ này: nó vừa là **yêu cầu**, vừa là **lệnh đối chiếu**. AI
buộc phải trả lời "đạt mấy trên ba", và mỗi mục trượt tự nó chỉ ra một phần
việc. Nếu bạn đang ở phía người ra đề, đây là câu đáng tập nhất trong cả note
này.

---

## Bước 6 — Đọc tín hiệu từ người dùng, không chỉ đọc nội dung

**Nguyên tắc.** Vài dạng tin nhắn mang thông tin nằm ở **hình dạng** của chúng,
không nằm ở chữ. Nhận ra hình dạng thì tiết kiệm được nhiều ngày.

Đây là những tín hiệu **cần NHẬN RA khi thấy chúng xuất hiện** — không phải câu
để bạn gõ cho AI.

| Hình dạng tín hiệu | Nghĩa thật | Phải làm gì |
|---|---|---|
| Yêu cầu **đánh số**, tả bằng hành vi | đây là tiêu chí nghiệm thu | chép nguyên văn, dựng bảng kiểm |
| **Lặp lại y hệt** một câu than phiền | bạn đang sai hướng | **dừng sửa**, kiểm bản sửa đã được nạp chưa |
| Dán vào một dòng lỗi, không nói gì thêm | chẩn đoán hoàn toàn thuộc về AI | đừng hỏi lại, đi tìm |
| Hai lần đo **mâu thuẫn** về cùng thiết bị | có thể là lỗi thiết bị, có thể là hồi quy | giữ lịch sử đo mới phân định được |
| Câu hỏi **lạc đề nhưng gấp** | ưu tiên thật của người dùng đang ở đó | xử lý ngay, đừng bảo "để sau" |

Dòng thứ hai của bảng có giá cụ thể: hai lần liền người dùng gõ đúng chữ
*"vẫn báo lổi"*, và tín hiệu đó **đã bị bỏ lỡ trọn một vòng**. Đó là lý do
`service.sh status` in dòng lệnh thật lấy từ `/proc/<pid>/cmdline` — để câu hỏi
"bản sửa đã vào chưa?" trả lời được bằng mắt, trong ba giây.

Còn tín hiệu "lạc đề nhưng gấp": giữa lúc đang gỡ MCP, người dùng hỏi vì sao
`sudo` báo sai mật khẩu. Lạc đề hoàn toàn — và hoá ra là một `pam_exec` cùng một
binary đang thu mật khẩu, chạy dưới quyền root. Việc gấp nhất cả phiên nằm trong
câu hỏi lạc đề nhất.

---

## Bước 7 — Gỡ lỗi tầng mạng: mỗi mã lỗi là một câu trả lời

**Nguyên tắc.** Ở tầng mạng, mã lỗi hiếm khi mơ hồ. Lập bảng tra một lần, dùng
mãi. Chỉ có **hai** kiểu hỏng thật sự khó, và cả hai đều khó vì cùng một lý do:
**chúng không nói gì cả.**

- **nginx buffering** → client treo, không lỗi, không log. Chữa:
  `proxy_buffering off`.
- **thiếu header CORS** → trình duyệt chặn ở preflight, JS chỉ thấy `Failed to
  fetch` rỗng.

Ghi nhớ chung: **khi một hệ thống im lặng, hãy nghi tầng trung gian trước khi
nghi mã nguồn của mình.**

🔧 Bảng tra đầy đủ (421 / 403 / 406 / 405, ý nghĩa và cách chữa) ở
`package/technical-docs.md` mục 7. Ba chi tiết mà thiếu là hỏng, mỗi cái có một
mục eval riêng: allowlist phải có **scheme `https`**, phải có **host trần không
kèm `:port`**, và CORS phải **expose `Mcp-Session-Id`**.

Một ngõ cụt **tuyệt đối**, đáng nhớ vì không có đường vòng: tên miền có **dấu
gạch dưới** thì không bao giờ xin được chứng chỉ (CA/B Forum cấm `_`), mà Claude
Desktop lại chỉ nhận `https`. Hai điều đó cộng lại là bế tắc. Đổi tên miền là
lối ra duy nhất. Bài học rộng hơn: **có loại ràng buộc do quy định ngành, không
phải do phần mềm — đừng phí giờ tìm cách lách.**

---

## Bước 8 — Suy luận từ triệu chứng: đếm mẫu trước khi kết luận

**Nguyên tắc.** Hai quan sát trùng nhau **không đủ** để kết luận một nguyên nhân
hệ thống. Nhất là khi hai mẫu ấy cùng loại — chúng có thể cùng hỏng vì cùng một
lý do nhất thời.

**Việc làm cụ thể.** Hai cái Nest Hub cùng đóng cổng 8009. Kết luận rút ra lúc
đó: *"firmware Nest Hub đã bỏ cổng 8009"*. Sai. Chúng chỉ đang treo — khởi động
lại là hết.

Cái bẫy nằm ở chỗ giả thuyết "firmware" nghe **rất hợp lý**, giải thích được
trọn vẹn dữ liệu, và cùng mẫu thiết bị làm nó nghe càng thuyết phục. Nhưng cùng
mẫu thiết bị cũng có nghĩa là **cùng chịu một kiểu lỗi nhất thời**.

**Quyết định chốt.** Trước khi nghi mã nguồn hoặc nghi firmware, chạy phép thử
rẻ nhất tách được hai giả thuyết:

```bash
nc -z <ip-thiết-bị> 8009    # cổng có mở không?
```

Rồi khởi động lại thiết bị và đo lại. Ba lần thất bại rải hai ngày mới ra được
kết luận đúng.

**Prompt mẫu thật** *(tái dựng)*:

```
Tôi thấy <triệu chứng> trên <N> thiết bị. Đừng kết luận nguyên nhân vội.
Liệt kê các giả thuyết còn sống, và với mỗi cái cho tôi PHÉP THỬ RẺ NHẤT
tách được nó khỏi các giả thuyết còn lại.
```

---

## Bước 9 — Kiểm ngược bộ eval, có tuyên bố kỳ vọng trước

**Nguyên tắc.** Bộ test chưa từng đỏ chưa chứng minh được gì. Nhưng chỉ "cấy lỗi
xem có đỏ không" thì vẫn hụt: bạn sẽ nhìn bảng đỏ, gật đầu, và bỏ sót mục **lẽ
ra phải đỏ mà lại xanh**. Vì thế phải **viết danh sách kỳ vọng ra trước**.

**Việc làm cụ thể.** Bốn bước, đúng thứ tự:

1. Liệt kê ra giấy: cấy lỗi này vào thì **những mục nào** phải đỏ.
2. Cấy lỗi. Chạy.
3. So kỳ vọng với thực tế. Ô đáng sợ nhất trong bảng so sánh là ô ***lẽ ra đỏ
   mà xanh*** — đó là **TEST GIẢ**.
4. Khôi phục, rồi **xác minh mã nguồn đã sạch** (`git diff --stat` phải rỗng).
   Bước này nghe thừa cho tới lần đầu bạn commit nhầm một lỗi cấy vào.

**Đây là chỗ đắt nhất của cả note.** Phiên đóng gói trước có một mục tên
`all: no duplicate physical device`. Cấy đúng lỗi vào — **nó vẫn xanh.** Lý do:
nó so trùng lặp theo **tên**, mà nhóm loa và thành viên của nó tên khác nhau.
Trùng lặp thật nằm ở mức **thiết bị vật lý** — cùng địa chỉ `host`.

Phiên đó xử lý bằng cách **ghi chú lại** rằng mục này không bắt được lỗi. Đó là
xử lý sai. Ghi chú không sửa được gì: ô vẫn xanh, người đọc bảng vẫn tưởng mình
đã được che chắn. Chỉ có hai lối thoát thành thật: **sửa cho nó bắt được**,
hoặc **ghi thẳng là CHƯA PHỦ** để không ai nhầm.

Lần này nó được sửa: so theo `host`. Và nó đã đỏ đúng lúc cần đỏ.

🔧 Số liệu, danh sách kỳ vọng viết trước, và bảng so sánh: `package/eval/README.md`.

**Prompt mẫu thật** *(tái dựng)*:

```
Kiểm ngược bộ test, theo đúng thứ tự sau, đừng đảo:
1. TRƯỚC KHI sửa gì, viết ra danh sách những mục sẽ phải ĐỎ khi tôi cấy
   lỗi <mô tả lỗi> vào. Nêu cả tổng số mục dự kiến đỏ.
2. Cấy lỗi. Chạy. Dán kết quả thật.
3. So kỳ vọng với thực tế thành bảng, và trả lời thẳng câu này: có mục nào
   LẼ RA ĐỎ MÀ VẪN XANH không? Mục đó là test giả — SỬA cho nó bắt được,
   hoặc ghi rõ CHƯA PHỦ. Chú thích lại không phải một lựa chọn.
4. Khôi phục, rồi chứng minh mã nguồn đã sạch (git diff phải rỗng).
```

Câu **"có mục nào lẽ ra đỏ mà vẫn xanh không?"** là câu quan trọng nhất trong
prompt này. Không hỏi thẳng thì gần như chắc chắn không ai đi tìm.

**Bài học rộng hơn, đáng mang đi nơi khác:** **một ô xanh giả nguy hiểm hơn một
ô trống.** Ô trống thì bạn biết mình chưa che. Ô xanh giả làm bạn tin là đã che.

Thêm một chuyện của chính phiên này: **bộ eval cũng là mã nguồn, cũng hỏng
được, và nó hỏng theo hướng xanh giả.** Tầng offline thay `tts.synthesize` ngay
trên module object; tầng `--online` chạy sau đo đúng cái hàm giả ấy và báo "mp3
0 byte". Nếu nhìn lướt thì rất dễ kết luận nhầm là edge-tts hỏng. Chữa xong,
thêm hẳn một mục canh gác: *"the online tier is testing the real synthesize, not
the fake"*.

---

## Bước 10 — Phân tầng test theo tác dụng phụ

**Nguyên tắc.** **Một bộ test mà không ai dám chạy thì bằng không có.** Nếu
product gây tác dụng phụ ra thế giới thật — phát tiếng, gửi tin, tiêu tiền, điều
khiển phần cứng — thì tầng **mặc định phải hoàn toàn không có tác dụng phụ**, và
tầng thật phải là một cờ bật tường minh.

**Việc làm cụ thể.** Ba tầng: mặc định (không mạng, không tiếng) · `--online`
(cần internet, vẫn không tiếng) · `--hardware` (phát tiếng thật, opt-in).

Đẩy được **bao nhiêu** kiểm tra xuống tầng mặc định thì đẩy. Ở đây là 62 mục
không tiếng, gồm cả những mục quan trọng nhất về hành vi: `all` gửi tới đúng tập
loa nào, thiếu loa thì không phát gì, một loa hỏng không kéo cả lệnh chết theo.

🔧 Một chi tiết dễ quên: tầng mặc định trỏ `GOOGLECAST_MCP_STORE` và
`GOOGLECAST_MCP_CACHE` vào thư mục tạm **trước khi import** server — nếu không,
chạy eval sẽ ghi đè danh sách thiết bị thật của người dùng. "Không tác dụng phụ"
phải tính cả tác dụng phụ lên tệp tin, không chỉ lên phần cứng.

**Prompt mẫu thật** *(tái dựng)*:

```
Product này gây tác dụng phụ thật ra thế giới: <phát tiếng / gửi tin / tiêu
tiền / điều khiển phần cứng>. Hãy dựng bộ test phân tầng theo tác dụng phụ:
- tầng MẶC ĐỊNH: không mạng, không tác dụng phụ nào, không ghi đè dữ liệu
  thật của tôi. Đẩy được bao nhiêu kiểm tra xuống tầng này thì đẩy hết.
- các tầng có tác dụng phụ: phải là cờ bật tường minh, và phải hỏi tôi
  trước khi chạy.
Liệt kê trước: mục nào xuống được tầng mặc định, mục nào bắt buộc phải ở
tầng thật, và vì sao.
```

**Quyết định chốt.** Agent đóng gói được phép chạy tầng mặc định và `--online`
tuỳ ý; `--hardware` phải xin phép người dùng.

---

## Bước 11 — Biết chỗ nào máy không kiểm được, và nói thẳng ra

**Nguyên tắc.** Mọi harness đều có một đường biên: chỗ mà máy không phán được
đúng sai. **Vẽ đường biên đó ra giấy** thay vì giả vờ là đã tự động hoá tới đó.

**Việc làm cụ thể.** Lỗi đắt nhất của product này: `all` gửi tới **cả nhóm loa
lẫn từng thành viên**. Nhóm Cast phát *thông qua* các thành viên, nên một cái
loa vật lý nhận hai luồng cùng lúc.

Điều đáng nhớ không phải bản thân lỗi, mà là: **cả bốn thiết bị đều trả về
`playing`.** Không có một chỉ báo API nào bất thường. Chỉ có tai người mới biết.

Từ đó rút ra một luật kiểm thử: **với thứ có tác dụng ra thế giới vật lý, trạng
thái API xanh không phải bằng chứng nó đúng.** Nghiệm thu cuối cùng phải bằng
giác quan, và cần một câu hỏi thẳng cho người dùng: *"nghe có đúng không?"* chứ
không phải *"có báo lỗi không?"*.

Cho nên `package/eval/README.md` có hẳn mục **"Chưa phủ, nói thẳng"**: giọng nam
chưa ai nghe, tham số tốc độ chưa ai nghe, dịch vụ chưa từng qua reboot, chặn IP
nginx vẫn đang comment. Liệt kê chỗ chưa phủ là một phần của bộ eval, không phải
lời thú tội.

---

## Hai câu note này KHÔNG trả lời được

Ghi ra để không ai tưởng là đã có đáp án.

**"Khi nào thì quyết định chạy như một service?"** — Ở đây không có tiêu chí
nào cả. Nó đến thẳng từ người dùng, khi họ mô tả hiện trạng máy móc của mình:

```
Mcp này sẽ chạy dạng service trên máy ip .128 máy tôi setup claude desktop
ip .28 giờ tôi làm dao bên cạnh đó hãy viết thêm install service remove
service start stop cho mcp
```

Hình thái triển khai là **dữ kiện của người dùng**, không phải kết luận của một
phép cân nhắc kỹ thuật. Một tiêu chí tổng quát cho câu hỏi này thì note này
không có, và bịa ra một cái sẽ tệ hơn là để trống.

**"Bao nhiêu mục eval là đủ?"** — Không biết. Con số 62 ở đây là kết quả của
việc phủ hết các hành vi trong danh sách yêu cầu cộng với các biên đã gặp thật,
chứ không phải kết quả của một ngưỡng nào. Phép thử duy nhất đã dùng được là
phép thử ở Bước 9: **cấy lỗi thật vào xem bộ test có đỏ đúng chỗ không.** Số
lượng mục không nói lên điều gì; việc từng đỏ đúng chỗ thì có.

---

## Cách đã kiểm chứng

Chỉ ghi những gì đã đo thật. Chỗ chưa thử ghi rõ **CHƯA THỬ** — không bỏ trống.

| Kịch bản | Số lần | Biên / điều kiện xấu | Kết quả |
|---|---|---|---|
| `say` → Kitchen speaker | 1 | bình thường | `playing`; người dùng xác nhận **nghe được** |
| `say` → Working display (Nest Hub) | **5 lần rải 2 ngày** | thiết bị treo rồi khởi động lại | 3 lần đầu **thất bại** (`wait timed out`, 8009 refuse); sau restart: 1 OK + 3 clip đo |
| Đo thời lượng phát | **3 clip** 2.09 / 4.27 / 7.10s | độ dài khác nhau | cả 3 `PLAYING` đủ `duration` → `idle_reason=FINISHED`; log HTTP xác nhận có tải file (200) |
| Thương lượng `protocolVersion` | **3 phiên bản** | client cũ và mới | cả 3 trả đúng version |
| MCP client thật qua https (nginx+TLS) | 1 | — | initialize + 13 tool + `list_speakers` → 4 loa |
| MCP client thật qua LAN `:8765` | 1 | — | như trên |
| Client trong trình duyệt (Origin `http://192.168.1.99:8383`) | 1 | có CORS | preflight 200, allow-origin đúng, initialize 200, 13 tool |
| `--json-response --stateless` | 1 | client khắt khe | trả `application/json`; `tools/call` không cần session id |
| Dò thiết bị + lọc loa | 2 | mạng thật 8 thiết bị | 4 loa / 4 thiết bị hình ảnh |
| `target="all"` | **2 lần: trước và sau khi sửa** | 4 loa song song | trước: 4 báo `playing` nhưng **chồng luồng**; sau: 3 loa lẻ |
| Nhiều loa cách phẩy | 1 | 2 loa | cả 2 `playing` |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 1 | phần tử hỏng | loa thật `playing`, phần tử hỏng `error` riêng, tổng thể `ok` |
| Nhóm gọi đích danh, sau khi sửa `all` | 1 | — | `playing` |
| **Eval offline** | nhiều lần, 3 phiên đóng gói | không tiếng | 35/35 → 43/43 → **62/62**, exit 0 |
| **Eval `--online`** | 1 (phiên này) | cần internet | **72/72**, exit 0 |
| **Eval có lỗi cấy vào** | 1 (phiên này) | kỳ vọng viết trước | 54/62, **đúng 8 mục đã tuyên bố**, không có test giả |
| **Eval `--hardware`** | 3 (đã xin phép mỗi lần) | cast thật, có tiếng | 37/37 → 48/48 → **bản này FAIL 62/63 rồi 67/67 sau khi sửa rò mock thứ hai**, exit 0 |
| **Diễn tập DoD** (clone trắng → gọi được tool) | 1 (phiên này) | máy sạch, cổng rỗi 8799 | 13 tool qua cả stdio lẫn HTTP; `tools/call say` trả về **tên loa thật** |

**Biên và điều kiện xấu đã quan sát được (thật, không suy diễn):** TCP 8009
refuse → timeout · mDNS sót thiết bị đã lưu → `DeviceNotFoundError` tự mâu thuẫn
· Origin ngoài allowlist → 403 · Host không tin → 421 · mở `/mcp` bằng trình
duyệt → 406 (**đúng đặc tả**, không phải lỗi) · preflight chưa bật CORS → 405
không header · bỏ tên loa → `needs_speaker_selection`, không phát gì · cài lại
dịch vụ khi đang chạy → tiến trình **không đổi** · `all` gồm cả nhóm lẫn thành
viên → chồng luồng mà API vẫn báo `playing` · mục eval chống trùng lặp **vẫn
xanh trong khi lỗi đang tồn tại** → test giả, đã sửa · `pkill -f "<mẫu>"` khớp
luôn chính lệnh bash đang chạy → **tự giết shell của mình** (exit 144, gặp lại
đúng trong phiên này).

**CHƯA THỬ:** giọng nam `vi-VN-NamMinhNeural` bằng tai · tham số `rate` bằng tai
· dịch vụ sống sót qua reboot máy (đã `enable`, chưa reboot lần nào) · địa chỉ
đã lưu bị cũ vì loa đổi IP → nhánh quét lại · chặn IP ở nginx (đã đồng ý bật,
hai dòng vẫn đang comment).

---

## Chỗ còn hở, không tô hồng

- **Không có xác thực ở tầng ứng dụng.** Ai tới được endpoint là điều khiển được
  loa. `google-cast.adrec.cloud` phân giải **công khai ra internet**.
- **Cổng audio 8766 bind `0.0.0.0`**, không xác thực, phục vụ nguyên thư mục
  cache. Chặn IP ở nginx chỉ che 8765.
- Cache TTS chỉ tăng, chưa có dọn.
- Chưa khôi phục âm lượng / nội dung đang phát sau khi chen thông báo vào.

**Biên áp dụng của chính phương pháp này** (chỗ hở của note, không phải của
product):

- Phương pháp này rút ra từ **một** product, do **một** người dùng đặt hàng,
  trong **một** miền (thiết bị trong nhà). Nó chưa được thử lại ở miền khác.
- Nó hợp với việc **có tác dụng phụ ra thế giới thật và có yêu cầu rõ ràng**.
  Với việc mà đầu ra do AI sinh và đúng/sai là chuyện thẩm mỹ (viết lách, thiết
  kế), Bước 9–11 gần như không dùng được: không có gì để cấy lỗi vào, và "xanh"
  không định nghĩa được.
- Nó **không** nói gì về làm việc nhiều người, review chéo, hay bảo trì dài hạn.
  Cả product này chỉ có một người dùng và một agent.
