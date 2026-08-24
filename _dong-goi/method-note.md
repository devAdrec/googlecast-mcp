---
product: googlecast-mcp
loại: MCP server (harness vận hành)
đóng gói: 2026-08-24
transmission_level: L2
---

# Cách xây googlecast-mcp — ghi chép phương pháp

Sản phẩm: một MCP server để nói tiếng Việt ra loa Google trong nhà. Ghi chép
này không dạy dùng nó (xem `package/user-manual.md`), cũng không dạy dựng lại
đúng nó (xem `reproduction-prompt.md`). Nó ghi **cách nghĩ** — để xây được một
cái khác.

---

## Bài học 30 giây

1. **Đưa yêu cầu thành danh sách đánh số, viết bằng hành vi.** Ba dòng đánh
   số của người dùng sinh ra toàn bộ sản phẩm. Mọi câu chữ khác trong phiên
   chỉ là dán lỗi vào.
2. **Dựng bản chạy được trước, rồi đối chiếu yêu cầu để lộ chỗ thiếu.** Mỗi
   chỗ thiếu thành một module. Đừng thiết kế trọn gói từ đầu.
3. **Chỉ so sánh phương án khi con người phải cảm nhận được sự khác nhau.**
   Thành phần xương sống thì chọn theo mức bảo trì, không cần so.
4. **Việc gì có tác dụng phụ ngoài đời thì đừng đoán hộ người dùng.** Thiếu
   thông tin thì hỏi lại, đừng chọn mặc định "làm tất".
5. **Người dùng lặp lại "vẫn lỗi" mà không có thông tin mới = đang sửa sai
   hướng.** Dừng sửa. Kiểm bản sửa đã được nạp chưa.
6. **Hai mẫu trùng nhau không đủ để kết luận nguyên nhân.** Và một kiểm chứng
   xanh chưa chứng minh gì cho tới khi bạn thấy nó đỏ đúng lúc phải đỏ.

---

## Bước 1 — Biến lời kể thành danh sách đối chiếu được

**Nguyên tắc.** Một sản phẩm chỉ bắt đầu tồn tại khi yêu cầu viết được thành
những câu kiểm được đúng/sai. Trước đó bạn đang đoán.

**Việc làm cụ thể.** Ở phiên gốc đã có sẵn một scaffold từ phiên trước — 11
tool điều khiển Cast chung chung, chưa có TTS. Người dùng không mô tả kiến
trúc, không nói cần module nào. Họ đưa ba dòng đánh số. Việc đầu tiên là lấy
ba dòng đó **đối chiếu ngược** với thứ đang có.

**Prompt mẫu thật** (nguyên văn, giữ nguyên lỗi gõ):

```
hãy kiểm tra xem mcp này đúng yêu cầu không:
1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả
```

**Quyết định chốt.** Kết quả đối chiếu: **đạt 1/3**, mà cái "đạt" cũng hỏng —
dò được thiết bị nhưng chỉ cache trong RAM, restart là mất, trong khi yêu cầu
ghi rõ "sau đó **lưu lại**".

🔧 Danh sách chưa đạt **chính là danh sách module cần viết**:

| Yêu cầu hụt | Module sinh ra |
|---|---|
| "lưu lại" | `speaker_store.py` |
| "chuyển thành âm thanh tiếng Việt" | `tts.py` |
| "phát lên speaker" | `media_server.py` |
| "không chọn thì hỏi" | `say()` + `_select_targets()` |

`cast_manager.py` giữ nguyên không sửa: nó đã làm đúng việc của nó. Phần
thiếu nằm ở tầng trên nó.

**Điều đáng học rộng ra:** đừng thiết kế trọn gói từ đầu. Dựng một bản chạy
được, rồi để danh sách yêu cầu chỉ ra chỗ hổng. Chỗ hổng tự nó phân module,
và phân đúng hơn là ngồi vẽ sơ đồ trước.

**Nếu bạn bắt đầu từ số 0** (phiên gốc đã có sẵn scaffold từ phiên trước, nên
không có prompt thật cho bước này — đây là prompt tái dựng):

```
Dựng một MCP server Python tối thiểu nhưng CHẠY ĐƯỢC cho <thiết bị/dịch vụ X>:
dùng <thư viện>, bọc mỗi thao tác cơ bản thành một tool, chạy được transport
stdio. Chưa cần đúng đủ yêu cầu của tôi — tôi cần một bản chạy được để đối
chiếu ngược. Xong thì liệt kê các tool bạn đã tạo.
```

Rồi mới đưa danh sách yêu cầu đánh số vào và bảo nó đối chiếu. Thứ tự này quan
trọng: đối chiếu với một thứ có thật cho ra danh sách module cụ thể; đối chiếu
với một bản thiết kế tưởng tượng chỉ cho ra một bản thiết kế khác.

---

## Bước 2 — Chọn thư viện: chỉ so sánh khi con người cảm nhận được

**Nguyên tắc.** So sánh phương án tốn thời gian. Chỉ đáng bỏ ra khi khác biệt
là thứ con người sẽ nhận ra và phàn nàn. Còn lại thì chọn theo tiêu chí khô
khan và đi tiếp.

**Việc làm cụ thể — hai loại thành phần, hai cách chọn khác hẳn nhau:**

*Loại cảm nhận được* — giọng nói. Người dùng sẽ nghe nó mỗi ngày. Đã so bốn
phương án:

| Phương án | Kết luận |
|---|---|
| gTTS | giọng máy móc |
| Google Cloud TTS | cần key, có phí |
| Piper | chạy offline nhưng yếu, setup nặng |
| **edge-tts** | **tự nhiên nhất, miễn phí, không cần key** |

Tiêu chí kỹ thuật (phí, key, độ nặng) thì tự chấm được. Tiêu chí "nghe có tự
nhiên không" **bắt buộc để người dùng nghe** — không ai chấm hộ được. Và chỉ
**một vòng**, không lặp: so bốn phương án, người dùng nghe, chốt, đi tiếp.

*Loại xương sống* — giao thức Cast. `pychromecast` **không qua so sánh nào
cả**. Nó là thư viện Python duy nhất còn được bảo trì cho giao thức này. So
sánh ở đây là diễn kịch.

**Prompt mẫu thật** (tái dựng — khuôn dùng được cho bài khác):

```
Liệt kê các thư viện <việc cần làm> còn được bảo trì. Với mỗi cái ghi: lần
cập nhật gần nhất, có cần API key không, có phí không, độ nặng khi setup.
Rồi tách rõ hai nhóm tiêu chí: (a) tiêu chí bạn tự chấm được bằng dữ liệu,
(b) tiêu chí BẮT BUỘC tôi phải tự kiểm bằng giác quan.
Nếu chỉ còn đúng một thư viện còn bảo trì thì nói thẳng, đừng bày ra bảng so
sánh cho có.
```

Câu cuối là câu đáng giá nhất: nó cho phép AI trả lời "không có gì để so".

**Quyết định chốt.** edge-tts với `vi-VN-HoaiMyNeural` (nữ) và
`vi-VN-NamMinhNeural` (nam). pychromecast, không bàn.

🔧 Có một quyết định thứ ba đắt hơn cả hai: **ghim `mcp[cli]>=1.13,<2`**. Trên
PyPI có một gói tên `mcp` phiên bản 2.0.0 **hoàn toàn không liên quan**, kéo
theo `httpx2` (một cái tên typosquat) và `mcp-types`. Cài nhầm thì import fail
theo kiểu chẳng gợi ý gì. Bài học chung: khi một cái tên gói quá chung chung,
kiểm xem nó có kéo theo đúng những thứ bạn mong đợi không, rồi ghim lại.

---

## Bước 3 — Thiết kế xung quanh ràng buộc gốc, đừng thiết kế quanh mong muốn

**Nguyên tắc.** Trong mỗi bài toán có một sự thật vật lý không thương lượng
được. Tìm ra nó trước, rồi để mọi thứ khác xếp theo. Thiết kế đẹp mà chống lại
nó thì sẽ phải đập đi.

**Cách tìm ra nó** — đây mới là phần chuyển giao được, vì ràng buộc của bài
bạn sẽ khác. Hỏi một câu kiểm được:

```
Để <hành động đích> xảy ra, thiết bị/dịch vụ đích phải TỰ làm gì? Nó nhận đầu
vào ở dạng nào, và nó lấy đầu vào đó từ đâu — tôi đẩy sang, hay nó tự đi lấy?
Nếu nó tự đi lấy thì nó cần với tới cái gì, và điều đó buộc máy của tôi phải
có tính chất gì?
```

Câu chốt là **"tôi đẩy sang, hay nó tự đi lấy?"**. Trả lời "nó tự đi lấy" là
lập tức lòi ra một server, một địa chỉ, một cổng, và một mặt bảo mật.

Cùng câu hỏi đó cho vài bài khác: đèn Hue → mọi lệnh phải qua bridge, mà bridge
đòi bấm nút vật lý để cấp API key ⇒ có một bước đăng ký thiết bị mà **con người
phải có mặt**, không tự động hoá được. Máy in → phải qua hàng đợi của hệ điều
hành. Chuông cửa → nó gọi ngược về bạn bằng webhook, không phải bạn hỏi nó.

**Việc làm cụ thể.** Ràng buộc gốc ở đây: **thiết bị Cast tự đi tải media qua
HTTP; nó không đọc được đường dẫn file trên máy bạn.**

Nghe thì nhỏ. Hệ quả thì kéo dài cả dự án:

- Một server "nói được" **bắt buộc** kiêm luôn một HTTP file server.
- Máy chạy nó phải cùng LAN với loa — không phải cho tiện, mà vì loa phải với
  tới được nó, và mDNS không đi qua router.
- Sinh ra một cổng thứ hai (8766) phải cố định để viết được luật tường lửa.
- Sinh ra nguyên một mặt bảo mật: cổng đó phục vụ không xác thực.

🔧 Chỗ tinh tế nhất, và cũng là chỗ hay nhầm nhất: `media_server.py:76` bind
`0.0.0.0`, còn URL quảng bá cho loa dựng từ `lan_ip()`. **Hai thứ khác nhau.**
Bind rộng để loa nào cũng tới được; URL phải là một địa chỉ cụ thể vì loa cần
một địa chỉ để gọi. Lẫn hai thứ này là ra một bug rất khó nhìn.

**Quyết định chốt.** Chấp nhận cấu trúc hai cổng ngay từ đầu thay vì tìm cách
né. Không có cách né.

---

## Bước 4 — Tác dụng phụ vật lý thì hỏi, đừng đoán

**Nguyên tắc.** Khi một hành động gây ra hậu quả ngoài đời — phát ra tiếng,
tiêu tiền, gửi tin đi — thì thiếu thông tin phải hỏi. Mặc định "làm tất" là
một mặc định tồi, vì cái giá của đoán sai không đối xứng.

**Việc làm cụ thể.** Yêu cầu #3 nói: không chọn loa thì hỏi. Có ba cách:

| Cách | Vì sao loại / chọn |
|---|---|
| MCP elicitation | loại — nhiều client chưa hỗ trợ |
| mặc định phát tất cả | loại — tác dụng phụ vật lý, đoán sai thì cả nhà nghe |
| **trả dữ liệu cho LLM tự hỏi lại** | **chọn — chạy với mọi client** |

**Prompt mẫu thật** (nguyên văn) — chính là dòng thứ ba của yêu cầu gốc:

```
3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả
```

**Quyết định chốt.** Thiếu `target` → trả về `status:
"needs_speaker_selection"`, kèm **cả** danh sách loa (dữ liệu) **lẫn** một câu
chỉ dẫn hành động cho LLM. Không tổng hợp âm thanh, không gửi lệnh nào đi.

Nguyên tắc này áp cho **cả hai chiều**, không chỉ chiều xuất. Chiều nhập —
đăng ký thiết bị, cấp quyền, ghép đôi — cũng là tác dụng phụ vật lý: bridge
Hue đòi bấm nút trên vỏ máy, loa đòi ở cùng LAN. Ở những bước đó phải chừa chỗ
cho con người có mặt, đừng thiết kế như thể tự động hoá được.

🔧 Cách kiểm điều này quan trọng hơn bản thân nó: eval **không** kiểm bằng giá
trị trả về. Nó cắm tripwire vào cả `tts.synthesize` lẫn `play_media`; hàm nào
bị gọi là đỏ ngay. Vì câu cần chứng minh không phải "trả về đúng chữ" mà là
"**không có gì xảy ra cả**". Muốn kiểm một điều-không-xảy-ra thì phải bẫy
đường đi, không thể nhìn kết quả.

---

## Bước 5 — Đọc tín hiệu từ người dùng

**Nguyên tắc.** Không phải câu nào của người dùng cũng cùng loại. Nhận sai
loại là làm sai việc.

**Việc làm cụ thể.** Cả phiên gốc có 21 lượt. Chúng rơi vào ba nhóm rất khác
nhau:

*Nhóm sinh ra sản phẩm* — đánh số, diễn đạt bằng hành vi. Chỉ có một:
prompt #3. Nó sinh ra toàn bộ chức năng chính.

*Nhóm dán lỗi vào* — người dùng chỉ đưa triệu chứng, chẩn đoán **hoàn toàn
thuộc về AI**:

```
URL must start with 'https'
https://google-cast.adrec.cloud/mcp kết quả là {"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept text/event-stream"}}
mcp này tôi chạy khi kết nối với mcp llama-server thì báo lổi: protocal error
```

*Nhóm tín hiệu cảnh báo* — quan trọng nhất, và cũng dễ bỏ lỡ nhất.

**Quyết định chốt — cái tín hiệu cần nhận ra:** người dùng nói *"vẫn báo
lổi"*, rồi lượt sau lại *"vẫn báo lổi:"*. **Lặp lại mà không có thông tin mới
nghĩa là đang sửa sai hướng.** Đúng cách xử lý: dừng sửa, kiểm xem bản sửa đã
thật sự được nạp chưa. Ở phiên gốc, tín hiệu này **đã bị bỏ lỡ một vòng** —
mất thêm một lượt sửa vô ích mới nhận ra.

Đây là tín hiệu **cần nhận ra ở phía người dùng**, không phải một câu để bạn
đi gõ cho AI.

Hai chi tiết nữa của lớp này:

- Có lượt lạc đề mà gấp nhất phiên: người dùng hỏi vì sao `sudo` báo sai mật
  khẩu. Lần theo ra `pam_exec` gọi một binary chạy dưới quyền root đang thu
  mật khẩu. Không liên quan gì tới MCP, nhưng phải xử ngay. **Đừng gạt câu
  lạc đề chỉ vì nó lạc đề.**
- Hai lượt mâu thuẫn về cùng một thiết bị: một lượt nói đã nghe được, một lượt
  sau nói "đèn nháy rồi tắt, không phát đầy đủ". **Giữ lịch sử đo mới phân
  định được** đó là lỗi thiết bị hay hồi quy mã nguồn.

---

## Bước 6 — Chẩn đoán hạ tầng: đọc mã lỗi như một manh mối

**Nguyên tắc.** Trong hạ tầng mạng, mã lỗi không phải phiền toái — nó là chẩn
đoán. Sai lầm là bịt lỗi thay vì đọc nó.

**Việc làm cụ thể.** 🔧 Bảng thu được sau khi lần lượt vấp từng cái. Bốn hàng
đầu là **đặc thù MCP-over-HTTP**, chép sang bài khác không dùng được; hai hàng
cuối (`Failed to fetch` và "sửa rồi mà không đổi gì") là **chung cho mọi hệ**
có trình duyệt hoặc có tiến trình nền:

| Triệu chứng | Nguyên nhân thật | Cách thoát |
|---|---|---|
| `421 Misdirected Request` | SDK chỉ tin `127.0.0.1`; bind `0.0.0.0` **không** đủ | Nới allowlist, kể cả **host trần không kèm port** và scheme **https** |
| Client treo, **không báo gì** | nginx đang đệm phản hồi streaming | `proxy_buffering off` + `proxy_read_timeout 3600s` |
| Không xin được chứng chỉ | Tên miền có gạch dưới. CA/B Forum **cấm** `_` | Đổi sang `google-cast.adrec.cloud`. **Không có cách vòng** |
| Claude Desktop không nhận URL | Ô connector chỉ nhận https | Bắc cầu `mcp-remote ... --allow-http` |
| `Failed to fetch (check CORS?)` | `OPTIONS` trả 405, không header CORS; JS chỉ thấy lỗi rỗng | `CORSMiddleware`, **bắt buộc** expose `Mcp-Session-Id` |
| Sửa rồi mà không đổi gì | `enable --now` **không** restart service đang chạy | `restart` tường minh + in `/proc/<pid>/cmdline` |

**Quyết định chốt quan trọng nhất của bước này:** khi gặp 421, cám dỗ là tắt
bảo vệ DNS-rebinding của SDK. **Không tắt.** Chỉ nới allowlist. Tắt là mở cửa
cho một trang web bất kỳ tấn công server nội bộ qua trình duyệt của bạn. Sửa
một lỗi mà mở ra một lỗ là chưa sửa.

🔧 Cái giá của lỗi cuối bảng: tiến trình cũ sống **ba ngày**, người dùng phải
nói "vẫn lỗi" ba lần. Từ đó `service.sh status` in luôn dòng lệnh của tiến
trình đang chạy thật — để lần sau phân biệt được ngay "bản sửa sai" với "bản
sửa chưa được nạp".

---

## Bước 7 — Suy luận: đừng kết luận nguyên nhân từ hai mẫu

**Nguyên tắc.** Hai thứ cùng hỏng theo cùng một kiểu **không** đủ để kết luận
một nguyên nhân hệ thống. Đó vẫn chỉ là hai mẫu.

**Việc làm cụ thể.** Cả hai Nest Hub trong nhà đều đóng cổng 8009. Kết luận
rút ra lúc đó: *"Nest Hub đã bỏ cổng 8009 do firmware mới"* — nghe rất hợp lý,
khớp cả hai mẫu, và **sai**.

Sự thật: thiết bị bị treo. mDNS vẫn trả lời, ping vẫn thông, nhưng TCP 8009
refuse. Restart thiết bị là hết.

**Quyết định chốt.** Thêm một bước đo **trước** khi nghi mã nguồn:

```bash
nc -z <ip> 8009
```

Một dòng, phân định ngay "thiết bị treo" với "mã nguồn hồi quy". Quy tắc rộng
ra: trước khi kết luận nguyên nhân hệ thống, tìm một phép đo **rẻ** phân biệt
được hai giả thuyết — đừng chọn giả thuyết nghe hay hơn.

🔧 Một cái bẫy cùng họ, phải trả giá bằng một shell bị giết: `pkill -f
"<pattern>"` khớp luôn chính lệnh bash đang chạy chứa pattern đó, và tự giết
mình (exit 144).

---

## Bước 8 — Lỗi mà API không thấy được

**Nguyên tắc.** Với sản phẩm có tác dụng phụ vật lý, phải chừa sẵn một chỗ cho
con người nghiệm thu. Có những lỗi không mã nào phát hiện được.

**Việc làm cụ thể.** `target="all"` gửi tới **cả nhóm loa lẫn từng thành
viên**. Nhóm Cast phát *qua* các thành viên của nó, nên `Family speaker group`
và `Kitchen speaker` — cùng địa chỉ `192.168.1.22` — khiến một loa vật lý nhận
**hai luồng cùng lúc**.

**Cả bốn lời gọi đều trả `playing`.** Không có mã lỗi, không có cảnh báo, trạng
thái hoàn toàn khoẻ mạnh. Chỉ khi có người nghe thấy tiếng vọng lệch pha thì
lỗi mới lộ.

**Quyết định chốt.** `all` bỏ qua `cast_type=group`. Nhóm vẫn gọi được bằng
tên nếu ai đó muốn.

🔧 Và đây là chỗ dễ viết ra một test giả: kiểm *"`all` không chứa tên nhóm"*
là kiểm cái tên, không kiểm cái hại. Cái hại là **hai luồng vào một loa vật
lý**, và loa vật lý nhận diện bằng **`host`**, không bằng tên. Nên phép kiểm
phải đối chiếu theo `host`.

**Bài học rộng:** khi API báo khoẻ mà người dùng nói không ổn, tin người dùng.
Và đưa lỗi đó vào eval theo **đúng cái đại lượng gây hại**, không theo cái đại
lượng dễ viết.

---

## Bước 9 — Eval chưa từng đỏ là eval chưa chứng minh gì

**Nguyên tắc.** Một bộ test toàn màu xanh không nói lên điều gì cho tới khi
bạn thấy nó **đỏ đúng lúc phải đỏ**. Và bạn phải viết ra *kỳ vọng đỏ* **trước
khi** gieo lỗi — nếu không, bạn sẽ hợp lý hoá bất cứ kết quả nào nhận được.

**Việc làm cụ thể.** Quy trình bốn nhịp, làm đúng theo thứ tự này:

1. Liệt kê trước: gieo lỗi X thì **những kiểm nào phải đỏ**.
2. Gieo lỗi, chạy eval.
3. Đối chiếu. Mục **lẽ ra đỏ mà vẫn xanh = TEST GIẢ**.
4. Khôi phục, **và xác minh mã đã hoàn nguyên sạch**.

**Prompt mẫu thật** (tái dựng — nội dung của bước này ở phiên đóng gói):

```
Viết một script kiểm ngược cho bộ eval. Với mỗi lỗi gieo vào, ghi TRƯỚC danh
sách những kiểm phải chuyển sang đỏ. Rồi gieo lỗi, chạy eval, đối chiếu.
Mục nào lẽ ra đỏ mà vẫn xanh thì báo là TEST GIẢ. Cuối cùng khôi phục mã và
xác minh cây mã sạch lại rồi eval xanh trở lại.
```

**Quyết định chốt.** 🔧 Vòng kiểm ngược đầu tiên bắt được **hai** thứ, cả hai
đều sẽ âm thầm phá hoại nếu bỏ qua bước này:

*Một test giả thật.* Kiểm ban đầu viết là "`all` không đụng một host quá một
lần" (`len(hosts) == len(set(hosts))`). Gieo lỗi vào, nó **vẫn xanh**: khi
`all` sai thành đúng một phần tử, tập một phần tử đương nhiên không trùng.
Câu khẳng định đúng nhưng rỗng. Sửa thành **phủ chính xác**: số lần cast phải
bằng đúng tập host loa riêng biệt — không thừa, không thiếu.

*Một cái bẫy bytecode.* Lỗi gieo vào đổi `!= "group"` thành `== "group"` —
**dài y hệt**. `git checkout` khôi phục nội dung, `git status` sạch, nhưng eval
vẫn đỏ: Python đang chạy lại `.pyc` cũ. Nghĩa là nếu bỏ bước 4 ("xác minh mã
hoàn nguyên sạch"), cả vòng kiểm ngược sẽ đọc ra kết luận sai hoàn toàn — và
tệ hơn, ở chiều ngược lại nó có thể báo xanh cho một bản mã đã hỏng.

---

## Bước 10 — Vệ sinh mock: một canh gác chỉ che một đường

**Nguyên tắc.** Mock rò rỉ giữa các tầng test là loại lỗi tệ nhất, vì nó khiến
test **nói dối theo cả hai chiều**: báo thành công giả, hoặc báo hỏng giả.
Vá từng đường rò là thua. Phải cô lập.

**Việc làm cụ thể.** Ở phiên trước, đúng lỗi này dính **hai lần**:

*Lần một.* Tầng offline thay `tts.synthesize` ngay trên module object. Tầng
`--online` sau đó đo nhầm hàm giả và báo "mp3 0 byte". Sửa, và thêm một canh
gác.

*Lần hai.* Canh gác đó **chỉ che đường TTS**. Một phép thử "mạng rỗng" thay
`list_speakers`/`discover` lên `server._manager` rồi **không khôi phục** →
tầng `--hardware` FAIL `no speaker answered mDNS`, trong khi loa vẫn sống hoàn
toàn bình thường: cổng 8009 mở, gọi `say` thủ công phát được.

Mất công chẩn đoán một "lỗi phần cứng" không hề tồn tại.

**Quyết định chốt.** Lần này thiết kế **cô lập ngay từ đầu**, ba lớp:

1. Mọi phép thay thế đi qua một context manager khôi phục trong `finally`.
2. Một hàm `assert_pristine()` chạy **sau mỗi tầng**, đối chiếu với ảnh chụp
   lấy trước khi tầng đầu tiên chạy. Mock nào sống sót là đỏ ngay tại chỗ.
3. Tầng online và tầng hardware **không dùng singleton dùng chung**. Chúng tự
   dựng `CastManager` / `MediaServer` mới của riêng mình.

Lớp 3 là lớp thật sự giải quyết vấn đề. Lớp 1 và 2 chỉ giúp phát hiện sớm.

🔧 Một cám dỗ đã thử và loại: `importlib.reload(tts)` ở đầu tầng online, để
"lấy lại bản sạch". Reload gán lại một function object hoàn toàn mới, **phá
mất cái tay nắm duy nhất vào hàm thật**, khiến canh gác không còn phân biệt
được thật với giả — và nó đã đỏ ngay ở lần chạy đầu. Đối chiếu với ảnh chụp
thì được; reload thì không.

**Bài học rộng:** khi một lớp bảo vệ chỉ che được một đường, đừng thêm lớp thứ
hai cho đường thứ hai. Hỏi xem có cách nào để không có đường nào cả.

---

## Bước 11 — Phân tầng test theo tác dụng phụ

**Nguyên tắc.** Một bộ test mà không ai dám chạy thì bằng như không có.

**Việc làm cụ thể.** Sản phẩm này phát ra tiếng trong một căn nhà thật. Nếu
eval mặc định làm điều đó, sẽ không ai chạy nó, và nó sẽ mục.

| Tầng | Cờ | Gây ra gì |
|---|---|---|
| offline | (mặc định) | **không gì cả** — không mạng, không tiếng |
| online | `--online` | gọi internet, vẫn im lặng |
| hardware | `--hardware` | **phát tiếng thật** |

**Quyết định chốt.** Tầng mặc định phải hoàn toàn không có tác dụng phụ. Tầng
gây ra hậu quả ngoài đời là cờ opt-in, và phải xin phép chủ nhà **mỗi lần**.

Cùng một nguyên tắc với Bước 4, áp cho test thay vì cho tool: cái gì chạm vào
thế giới thật thì phải do con người bấm nút.

---

## Cách đã kiểm chứng

Bảng này là dữ liệu thật, không phải kế hoạch. "CHƯA THỬ" là chưa thử.

| Kịch bản | Số lần | Biên / điều kiện xấu | Kết quả |
|---|---|---|---|
| `say` → Kitchen speaker | nhiều | bình thường | `playing`; người dùng xác nhận **nghe được** |
| `say` → Working display (Nest Hub) | **5 lần rải 2 ngày** | thiết bị treo rồi restart | 3 lần đầu **thất bại** (`wait timed out`, 8009 refuse); sau restart: 1 OK + 3 clip đo |
| Đo thời lượng phát | **3 clip** (2.09 / 4.27 / 7.10s) | độ dài khác nhau | cả 3 `PLAYING` đủ `duration` → `idle_reason=FINISHED`; log HTTP xác nhận loa **có** tải file (200) |
| Thương lượng `protocolVersion` | **3 phiên bản** | client cũ và mới | cả 3 trả đúng version |
| MCP client thật qua https (nginx + TLS) | 1 | — | initialize + 13 tool + `list_speakers` → 4 loa |
| MCP client thật qua LAN `:8765` | 1 | — | như trên |
| Client trình duyệt (origin `http://192.168.1.99:8383`) | 1 | có CORS | preflight 200 + allow-origin đúng; initialize 200 JSON; 13 tool |
| `--json-response --stateless` | 1 | client khắt khe hơn đặc tả | trả `application/json`; `tools/call` không cần session id |
| Dò thiết bị + lọc loa | nhiều | mạng thật, 8 thiết bị | 4 loa / 4 thiết bị hình ảnh |
| `target="all"` | **2 lần: trước và sau khi sửa** | 4 loa song song | trước: 4 `playing` nhưng **chồng luồng**; sau: 3 loa riêng lẻ |
| Nhiều loa cách phẩy | 1 | 2 loa | cả 2 `playing` |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 1 | phần tử hỏng | loa thật `playing`, phần tử hỏng `error` riêng, tổng thể `ok` |
| **Eval offline** | **4 phiên đóng gói** | không tiếng | 35/35 → 43/43 → 62/62 → **67/67**, exit 0 |
| **Eval `--online`** | 2 | cần internet | 72/72 → **79/79**, exit 0 |
| **Eval `--hardware`** (xin phép mỗi lần) | 4, kể cả phiên này | cast thật | 37/37 → 48/48 → FAIL 62/63 rồi 67/67 (rò mock thứ hai) → **FAIL 90/91 rồi 91/91** (khẳng định đo sai thời điểm) |
| **Kiểm ngược có kỳ vọng viết trước** | 1 (phiên này) | 3 lỗi gieo vào | bắt được **1 test giả** + **1 bẫy bytecode**; sau khi sửa: mọi kỳ vọng đỏ đều đỏ, mã hoàn nguyên sạch, eval xanh lại |
| **DoD: cài lại theo README, gọi tool** | 2 (phiên này) | cổng rỗi 8799 / 8798 | tại chỗ: initialize OK, `tools/list` → **13 tool**, `tools/call list_speakers` → loa thật. **Từ bản clone mới của remote** + `uv sync`: initialize OK, **13 tool** |

**Biên đã quan sát được (thật, không suy đoán):** TCP 8009 refuse → timeout ·
mDNS sót thiết bị đã lưu → `DeviceNotFoundError` tự mâu thuẫn · origin ngoài
allowlist → 403 · host không tin → 421 · mở `/mcp` bằng trình duyệt → 406
(**đúng đặc tả**, không phải lỗi) · preflight chưa bật CORS → 405 không header
· bỏ `target` → `needs_speaker_selection`, không phát gì · cài lại service khi
đang chạy → tiến trình **không** đổi · `all` gồm cả nhóm lẫn thành viên →
chồng luồng mà API vẫn báo `playing` · **hai lần rò mock trong chính bộ eval**
· bytecode cũ khiến mã đã khôi phục vẫn chạy như bản hỏng.

**CHƯA THỬ:**

- Giọng nam `vi-VN-NamMinhNeural` **bằng tai** (eval chỉ kiểm được file khác rỗng).
- Tham số `rate` **bằng tai**.
- Service sống sót qua **reboot máy** (đã `enable`, chưa reboot bao giờ).
- Địa chỉ đã lưu bị cũ vì loa đổi IP → nhánh quét lại.
- Chặn IP ở nginx (đã đồng ý bật, hai dòng vẫn đang comment).

---

## Điểm còn hở (không tô hồng)

- **Không có xác thực ở tầng ứng dụng.** `google-cast.adrec.cloud` phân giải
  **công khai ra internet**. Ai với được `/mcp` là phát được tiếng trong nhà.
- **Cổng audio 8766 bind `0.0.0.0`**, không xác thực, phục vụ nguyên thư mục
  cache. Chặn IP ở nginx **chỉ che 8765**, không che cổng này.
- Cache TTS tăng vô hạn, chưa dọn.
- Chưa khôi phục âm lượng / nội dung đang phát sau khi chen thông báo vào.
- Kho mã đã có remote (`github.com/devAdrec/googlecast-mcp`) nhưng là repo
  **riêng tư**: người lạ vẫn cần được cấp quyền mới clone được. Đó là điều
  kiện thật, ghi rõ ở bước 0 của `package/README.md` chứ không giấu.

---

## Đi tiếp

| Muốn gì | Đọc file nào |
|---|---|
| Cài và chạy | `package/README.md` |
| Yêu cầu gốc + tiêu chí chấp nhận | `package/requirement.md` |
| Ràng buộc triển khai | `package/technical-docs.md` |
| Dùng `say` | `package/user-manual.md` |
| Ba tầng eval + kiểm ngược | `package/eval/README.md` |
| Năm lớp harness | `package/harness-spec.md` |
| Dựng lại **đúng** sản phẩm này | `reproduction-prompt.md` — chỉ dùng cho chính nó, **không phải khuôn cho bài khác** |
