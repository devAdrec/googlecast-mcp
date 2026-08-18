---
product: googlecast-mcp
product_path: /storage/apps/mcp/googlecast_mcp
loai: cong-cu-thuan (MCP server chay that, da trien khai)
transmission_level: L2
eval_boi: method-note-evaluator-solo (doc sach), 2026-08-18
commit_tham_chieu: 4775e38  # moi tham chieu file:line duoi day doc theo commit nay
ngay: 2026-08-18
---

# Method note — googlecast-mcp

Product: một MCP server để LLM nói tiếng Việt ra loa Google trong nhà.
Note này KHÔNG mô tả lại code — code và tài liệu vận hành đã nằm trong chính repo:

- Cách cài, 13 tool, troubleshooting, lệnh triển khai thật → `README.md`
- Luồng request, bảng module, threading, "Things that bite" → `docs/architecture.md`
- Cài/gỡ/khởi động lại service → `scripts/service.sh`
- Vhost nginx đã dùng thật → `scripts/nginx-googlecast-mcp.conf`

Note này ghi **cách nghĩ** đã tạo ra nó, để làm lại được một product khác cùng kiểu.

---

## Bài học 30 giây

1. **Yêu cầu đánh số, viết bằng hành vi, là thứ quý nhất người dùng đưa cho bạn.** Có nó thì kiểm được từng mục đạt hay không; product này lúc "tưởng xong" chỉ đạt 1/3.
2. **Việc gì có tác dụng phụ ngoài đời thật thì không được đoán.** Thiếu thông tin thì hỏi lại, đừng chọn mặc định "làm tất cả" — sai là ồn cả nhà.
3. **Tiêu chí cảm nhận (hay/dở, tự nhiên/máy móc) phải để người dùng quyết.** AI chỉ thu hẹp danh sách và nêu đánh đổi.
4. **Người dùng nói "vẫn lỗi" lần thứ hai = bạn đang sửa sai hướng.** Dừng sửa, đi kiểm bản sửa đã thật sự được NẠP chưa (chi tiết ở Bước 7 — đây là ngõ cụt tốn nhiều ngày nhất của phiên).
5. **Hai lần trùng nhau không phải là một quy luật.** Trước khi đổ cho thiết kế của thiết bị, hãy làm một phép thử rẻ tiền để loại trừ trạng thái tạm (chi tiết ở Bước 8).
6. **Ghi lại lần đo được, kèm ngày giờ.** Cùng một thiết bị lúc chạy lúc không; chỉ lịch sử đo mới phân định được "lỗi thiết bị" với "code vừa hỏng".
7. **Khi đóng gói, viết trung thực cái CHƯA thử.** Danh sách "chưa thử" có giá trị bằng danh sách "đã chạy".

---

## Bước 0 — Khoá và bí mật của thiết bị

**Nguyên tắc.** Trước khi viết dòng code nào, trả lời: thiết bị này có cần khoá/mật khẩu không? Lấy ở đâu? Cất ở đâu? Có bị commit nhầm không?

**Với product này: KHÔNG có khoá nào.** Giao thức Google Cast trong LAN không yêu cầu xác thực — đó là lý do bước này trống, và cũng là lý do phần "Điểm còn hở" bên dưới nghiêm trọng: không có khoá nghĩa là **ai vào được mạng (hoặc vào được URL công khai) là điều khiển được**.

**Với product khác cùng kiểu** (đèn Tuya cần `local_key`, camera cần token…), đây là bước 0 thật sự và phải làm trước: xác định nguồn khoá, cất vào file ngoài repo hoặc biến môi trường, thêm vào `.gitignore` ngay lúc tạo.

**Prompt mẫu:**
> Thiết bị/nền tảng này có cần khoá, token hay mật khẩu để điều khiển trong LAN không? Nếu có: lấy bằng cách nào, và hãy thiết kế sẵn chỗ cất nằm ngoài repo trước khi viết code. Nếu không cần khoá, hãy nói rõ điều đó có nghĩa gì về mặt an toàn.

---

## Bước 1 — Lấy được một bản yêu cầu kiểm được

**Nguyên tắc.** Đừng bắt đầu từ mô tả cảm tính. Bắt đầu từ một danh sách hành vi đánh số, để về sau đối chiếu từng dòng.

**Việc làm cụ thể.** Người dùng gõ nguyên văn (giữ nguyên lỗi gõ):

> `hãy kiểm tra xem mcp này đúng yêu cầu không:`
> `1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại`
> `2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu`
> `3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả`

Ba dòng này sinh ra toàn bộ product. Việc đầu tiên AI làm không phải là viết thêm code, mà là **chấm từng mục**: lúc đó chỉ đạt 1/3.

**Prompt mẫu:**
> Đây là danh sách yêu cầu đánh số của tôi. Đừng viết thêm code vội — hãy chấm từng mục: đạt / không đạt / đạt một phần, kèm bằng chứng ở file nào. Xong bảng chấm rồi mới sửa.

**Quyết định chốt.** Khi người dùng đưa yêu cầu dạng danh sách, hãy trả lời bằng đúng cấu trúc danh sách đó, ghi rõ đạt / không đạt / đạt một phần, rồi mới sửa.

---

## Bước 2 — Chọn công nghệ có tiêu chí cảm nhận

**Nguyên tắc.** Chia tiêu chí làm hai loại: loại đo được (miễn phí? cần khoá API? chạy offline?) thì AI tự chấm; loại **nghe/nhìn mới biết** thì bắt buộc để người dùng trải nghiệm rồi chọn. Không chọn hộ.

**Việc làm cụ thể.** So bốn cách sinh giọng tiếng Việt:

| Phương án | Đo được | Cảm nhận |
|---|---|---|
| gTTS | miễn phí, không khoá | giọng máy móc |
| Google Cloud TTS | cần khoá API + trả phí | tốt |
| Piper | offline, setup nặng | yếu |
| edge-tts | miễn phí, không khoá | tự nhiên nhất |

**Prompt mẫu** (tái dựng — dùng lại được cho bài khác):

> Có N cách làm X. Với mỗi cách, liệt kê: chi phí, phụ thuộc bên ngoài, độ khó cài đặt. Riêng chất lượng đầu ra thì đừng tự chấm — hãy tạo mẫu để tôi nghe/xem rồi tôi chọn.

**Quyết định chốt.** `edge-tts`, giọng `vi-VN-HoaiMyNeural` (nữ, mặc định) / `vi-VN-NamMinhNeural` (nam).

---

## Bước 3 — Xử lý thông tin thiếu ở một tool có tác dụng phụ vật lý

**Nguyên tắc.** Tool phát ra tiếng trong nhà thật thì "đoán bừa" là hỏng nặng hơn "không làm gì". Thiếu tham số → **trả dữ liệu để LLM hỏi lại**, không tự phát.

**Việc làm cụ thể.** Bỏ trống `target` khi gọi `say` → trả `needs_speaker_selection` + danh sách loa, và KHÔNG phát gì. Nhận: một tên, nhiều tên cách phẩy, hoặc `all` / `tất cả`.

**Prompt mẫu:**
> Tool này gây tác dụng phụ ngoài đời thật. Khi thiếu tham số chỉ định đối tượng, KHÔNG được đoán và KHÔNG được mặc định làm tất cả — hãy trả về danh sách lựa chọn kèm cờ báo cần chọn, để tầng gọi hỏi lại người dùng.

**Quyết định chốt.** Không dùng cơ chế hỏi-lại của giao thức MCP (elicitation) vì nhiều client chưa hỗ trợ — trả dữ liệu thường thì client nào cũng hiểu. Cũng không mặc định phát tất cả.

🔧 Xem `src/googlecast_mcp/server.py` (tool `say`).

---

## Bước 4 — Đọc ràng buộc gốc của hệ thống bên ngoài trước khi thiết kế

**Nguyên tắc.** Trước khi chọn kiến trúc, tìm cho ra ràng buộc **không thương lượng được** của nền tảng bạn nói chuyện cùng. Nó quyết định hình dạng chương trình, không phải sở thích của bạn.

**Việc làm cụ thể.** Thiết bị Cast **tự đi tải media qua HTTP**; nó không đọc được đường dẫn file trên máy bạn. Hệ quả: một server "nói được" **buộc phải kiêm luôn HTTP file server**. Đó là lý do có `media_server.py`, không phải vì thích tách module.

**Prompt mẫu:**
> Trước khi thiết kế, hãy tra và liệt kê những ràng buộc KHÔNG thương lượng được của nền tảng/giao thức thiết bị này (nó chủ động kết nối hay bị kết nối? đọc dữ liệu kiểu gì? một kết nối tại một thời điểm?). Với mỗi ràng buộc, nói nó ép kiến trúc của tôi phải có thành phần nào.

Ghi cho đúng, đây là chỗ dễ viết nhầm: server **bind `0.0.0.0`** (mọi interface), còn **URL quảng bá** cho thiết bị thì dựng từ IP LAN — hai thứ khác nhau.

🔧 `src/googlecast_mcp/media_server.py:76`.

---

## Bước 5 — Chống lại sự "lúc được lúc không" của mạng nội bộ

**Nguyên tắc.** Với mạng gia đình, thứ dò được một lần không đảm bảo lần sau dò lại thấy. Hãy **lưu bền** kết quả và **kết nối thẳng bằng địa chỉ đã lưu** trước khi kết luận "không tìm thấy".

**Việc làm cụ thể.** Dấu hiệu phát hiện lỗi rất đặc trưng: thông báo lỗi **tự mâu thuẫn** — báo "không tìm thấy thiết bị X" trong khi chính X có trong danh sách "đã biết". Một thông báo tự mâu thuẫn luôn là bug logic, không phải sự cố môi trường.

**Prompt mẫu:**
> Cơ chế dò thiết bị này có thể sót. Hãy lưu bền địa chỉ mỗi thiết bị và khi thao tác thì thử kết nối thẳng bằng địa chỉ đã lưu TRƯỚC, dò lại chỉ là phương án dự phòng. Không bao giờ báo "không tìm thấy" một thiết bị đang có trong danh sách đã biết.

**Quyết định chốt.** `_connect_saved()`: nối thẳng bằng host/port đã lưu, thất bại mới quét lại. 🔧 `src/googlecast_mcp/cast_manager.py:110,124,134`; kho lưu `~/.googlecast-mcp/speakers.json`.

---

## Bước 6 — Nhóm lỗi "phơi server ra ngoài máy" (phần tốn thời gian nhất)

**Nguyên tắc.** Khi một service chạy được ở localhost mà chết ở máy khác, nguyên nhân gần như luôn nằm ở **các lớp giữa** — kiểm tra bảo mật của thư viện, reverse proxy, trình duyệt — chứ không phải logic nghiệp vụ. Học cách đọc mã lỗi để nhảy thẳng tới lớp đúng:

| Triệu chứng | Lớp thật sự có lỗi | Cách thoát |
|---|---|---|
| `421 Misdirected Request` | SDK chỉ tin `127.0.0.1`; bind `0.0.0.0` KHÔNG đủ | nới allowlist host/origin: thêm IP LAN + domain, kèm cả `https` (proxy đổi scheme) và cả **host không kèm `:port`** (proxy cổng 443 không gửi port) — 🔧 `__main__.py:46-69` |
| `403 Invalid Origin header` | origin gọi tới không nằm trong allowlist | thêm đúng origin |
| Client treo im, không báo lỗi | nginx **đệm** response; giao thức này giữ kết nối mở đẩy sự kiện dần | `proxy_buffering off` + `proxy_read_timeout 3600s` — 🔧 `nginx-googlecast-mcp.conf:37,42` |
| `Failed to fetch (check CORS?)` từ webui | SDK trả `OPTIONS` = 405, không header CORS → trình duyệt chặn, JS chỉ thấy lỗi rỗng | bọc app bằng CORSMiddleware; **BẮT BUỘC** `expose_headers=["Mcp-Session-Id"]` — thiếu là kết nối được nhưng không đọc nổi session id — 🔧 `__main__.py:37` |
| `406 Not Acceptable: must accept text/event-stream` khi mở bằng trình duyệt | **không phải lỗi** — đúng đặc tả | đừng đi sửa |

**Prompt mẫu:**
> Server chạy tốt ở localhost nhưng client ở máy khác không kết nối được, mã lỗi là <dán mã lỗi>. Đừng sửa logic nghiệp vụ. Hãy xác định lỗi thuộc lớp nào: kiểm tra bảo mật của SDK, reverse proxy, hay chính sách CORS của trình duyệt — rồi sửa đúng lớp đó.

**Bài học riêng, không có đường vòng:** hostname có **gạch dưới** thì **không bao giờ** xin được chứng chỉ TLS (quy định CA cấm ký tự `_` trong tên miền của cert). Người dùng đã tạo `google_cast.adrec.cloud`, mà client đích chỉ nhận `https` ⇒ ngõ cụt tuyệt đối. Cách thoát duy nhất: **đổi tên miền** thành `google-cast.adrec.cloud`.

*(Các tên miền, IP, cổng nêu trong bảng và đoạn trên là chi tiết riêng của lần triển khai này — khi làm lại hãy thay hết, chỉ giữ lại quy tắc.)*

**Nguyên tắc rút ra:** khi gặp một ràng buộc do **tiêu chuẩn/chính sách** đặt ra (chứ không phải do phần mềm), đừng tốn thời gian tìm mẹo — đổi đầu vào.

**Quyết định chốt về bảo mật.** Giữ nguyên cơ chế chống DNS-rebinding của SDK, **chỉ nới allowlist**. Tắt hẳn là mở cửa cho web bất kỳ tấn công server nội bộ.

---

## Bước 7 — Bẫy "đã sửa rồi mà vẫn lỗi"

**Nguyên tắc.** Trước khi chẩn đoán tiếp, hãy chứng minh rằng **bản sửa đã được nạp**. Không chứng minh được thì mọi suy luận sau đó đều vô nghĩa.

**Việc làm cụ thể.** Lệnh cài service kiểu `enable --now` **KHÔNG khởi động lại tiến trình đang chạy**: file cấu hình đã đổi, tiến trình vẫn chạy code và tham số cũ. Ở đây tiến trình cũ sống **3 ngày**. Cách phát hiện: đọc dòng lệnh thật của tiến trình đang chạy qua `/proc/<PID>/cmdline` — nếu nó không có cờ mới vừa thêm, bạn đang gỡ nhầm bài toán.

**Prompt mẫu:**
> Tôi đã sửa và cài lại nhưng lỗi y hệt. Trước khi chẩn đoán tiếp, hãy chứng minh tiến trình đang chạy CHÍNH LÀ bản mới: in dòng lệnh thật của tiến trình đang chạy và đối chiếu với tham số tôi vừa thêm.

**Quyết định chốt.** `service.sh` khởi động lại **tường minh**, và lệnh `status` in luôn dòng lệnh thật của tiến trình. 🔧 `scripts/service.sh:78-80,112-115`.

**Tín hiệu từ người dùng:** câu "vẫn lỗi" lặp lần thứ hai chính là chỗ phải chuyển từ "sửa tiếp" sang "kiểm tra bản sửa đã nạp chưa". Tôi đã bỏ lỡ tín hiệu này mất một vòng.

---

## Bước 8 — Phân biệt lỗi thiết bị với lỗi code

**Nguyên tắc.** Trước khi nghi code, làm một phép thử rẻ ở tầng thấp hơn.

**Việc làm cụ thể.** Thiết bị Cast có thể **trả lời mDNS và ping bình thường nhưng từ chối kết nối TCP cổng 8009** → chương trình chỉ thấy `Execution of wait timed out after 10 s`. Kiểm tra cổng trực tiếp (`nc -z <ip> 8009`) TRƯỚC. Restart thiết bị là hết.

**Prompt mẫu:**
> Thiết bị không phản hồi. Trước khi nghi code, hãy kiểm tầng thấp hơn: cổng điều khiển của nó có mở không (`nc -z <ip> <port>`). Nếu hai thiết bị cùng dòng cùng hỏng, đừng vội kết luận đó là đặc tính của dòng máy — hãy thử một phép loại trừ rẻ tiền (restart) trước.

**Ngõ cụt suy luận đã mắc:** thấy **cả hai** máy cùng dòng đều đóng cổng → kết luận "dòng máy này bỏ cổng 8009 do firmware". Sai. Hai mẫu trùng nhau không đủ suy ra nguyên nhân hệ thống; restart chứng minh ngược lại.

---

## Cách đã kiểm chứng

Toàn bộ kiểm chứng là **thủ công, không có unit test nào**.

**Bao nhiêu lần thì gọi là đã kiểm chứng?** Một lần chạy được KHÔNG phải kiểm chứng — nó chỉ chứng minh "có lúc chạy". Ngưỡng dùng ở đây: đường đi chính phải **lặp lại ở nhiều thời điểm khác nhau** (bảng dưới: 5 lần rải qua 2 ngày) và **nhiều đầu vào khác nhau** (3 clip dài ngắn khác nhau, 3 phiên bản giao thức). Đủ để phân biệt "chạy ổn định" với "may".

### Đã chạy thật

| Kịch bản | Số lần | Biên / điều kiện | Kết quả |
|---|---|---|---|
| `say` tiếng Việt → Kitchen speaker (Home Mini) | 1 | bình thường | `status=playing`; người dùng xác nhận NGHE ĐƯỢC |
| `say` → Working display (Nest Hub) | **5 lần rải qua 2 ngày** | thiết bị treo rồi được restart | 3 lần đầu THẤT BẠI (`wait timed out after 10 s`, cổng 8009 refuse); sau restart: 1 lần OK + 3 clip đo |
| Đo thời lượng phát trên Working display | **3 clip** (2.09s / 4.27s / 7.10s) | độ dài khác nhau | cả 3: `PLAYING` đủ `duration` → `IDLE` + `idle_reason=FINISHED`; log HTTP xác nhận thiết bị có tải file (200) |
| Thương lượng phiên bản giao thức | **3 phiên bản** (2024-11-05 / 2025-03-26 / 2025-06-18) | client cũ và mới | cả 3 trả đúng version tương ứng |
| MCP client thật qua `https://google-cast.adrec.cloud/mcp` | 1 | qua nginx + TLS | initialize + list_tools (13) + call_tool(list_speakers) → 4 loa |
| MCP client thật qua `http://<LAN>:8765/mcp` | 1 | trực tiếp trong LAN | như trên |
| Mô phỏng client trình duyệt, Origin `http://192.168.1.99:8383` | 1 | có CORS | preflight OPTIONS 200 + `allow-origin` đúng; initialize 200 JSON; tools/list 13 tool |
| Chế độ `--json-response --stateless` | 1 | client khắt khe | `application/json`; `tools/list` + `tools/call` chạy không cần session id, không cần handshake |
| Dò thiết bị + lọc loa | 2 | mạng thật 8 thiết bị | 4 loa (audio/group) / 4 thiết bị hình ảnh (cast) |
| TTS sinh mp3 + phục vụ qua HTTP | nhiều lần | — | mp3 hợp lệ, kích thước khớp byte tải về |
| `target="all"` — phát mọi loa cùng lúc | 1 | 4 loa thật song song | cả 4 `playing`; **nhưng lộ lỗi chồng luồng, xem dưới** |
| `target` nhiều loa cách dấu phẩy | 1 | 2 loa | cả 2 `playing` |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 1 | một phần tử hỏng | loa thật vẫn `playing`, phần tử hỏng trả `error` riêng, tổng thể `status=ok` — cô lập ĐÚNG |

### Biên / điều kiện xấu đã quan sát được (quan sát thật, không dựng giả)

| Điều kiện | Quan sát |
|---|---|
| Thiết bị mở mDNS + ping OK nhưng TCP 8009 refuse | `Execution of wait timed out after 10 s` — restart thiết bị là hết |
| mDNS sót thiết bị đã lưu | `DeviceNotFoundError` tự mâu thuẫn → sinh ra `_connect_saved()`; sau khi sửa, cast thành công qua địa chỉ đã lưu |
| Origin ngoài allowlist | 403 `Invalid Origin header` |
| Host header không được tin | 421 `Misdirected Request` |
| Mở `/mcp` bằng trình duyệt (Accept: text/html) | 406 `Not Acceptable` — đúng đặc tả, KHÔNG phải lỗi |
| Preflight OPTIONS khi chưa bật CORS | 405, không header CORS |
| Bỏ `target` khi gọi `say` | trả `needs_speaker_selection` + danh sách loa, KHÔNG phát gì |
| Cài lại service khi service đang chạy | tiến trình KHÔNG đổi — xem Bước 7 |
| `target="all"` khi có cả nhóm loa lẫn thành viên của nhóm | **LỖI CHƯA SỬA.** `list_speakers()` trả cả `audio` lẫn `group`, nên `all` cast tới nhóm VÀ tới từng thành viên → một loa vật lý nhận hai luồng. Đo được: `Family speaker group` và `Kitchen speaker` cùng ở `192.168.1.22` (nhóm lấy một thành viên làm điều phối). Tool báo `playing` cho cả hai, nên **trạng thái trả về không phát hiện được lỗi này** — chỉ nghe mới biết |

### CHƯA THỬ — đừng suy đoán là chạy được

- Giọng nam `vi-VN-NamMinhNeural` — **CHƯA THỬ** (mọi lần đều dùng giọng nữ mặc định)
- Tham số `rate` (nhanh/chậm) — **CHƯA THỬ**
- Service sống sót qua reboot máy (đã `enable` nhưng chưa reboot lần nào) — **CHƯA THỬ**
- Địa chỉ đã lưu bị cũ (thiết bị đổi IP) → nhánh quét lại — **CHƯA THỬ**
- `text` rỗng → `ValueError` — chỉ có trong code, **CHƯA chạy thật**
- Chặn IP ở nginx (`allow 192.168.0.0/16; deny all;`) — người dùng đã đồng ý bật nhưng **CHƯA bật**, hai dòng vẫn đang comment

---

## Điểm còn hở (không tô hồng)

- **Không có xác thực ở tầng ứng dụng.** `google-cast.adrec.cloud` phân giải công khai ra internet → ai biết URL cũng phát được tiếng trong nhà.
- **Mặt phơi nhiễm thứ hai:** cổng audio 8766 bind `0.0.0.0`, không xác thực, phục vụ nguyên một thư mục file. Chặn IP ở nginx **chỉ che cổng 8765**, không chạm tới 8766.
- **`target="all"` chồng luồng lên nhóm loa** (chi tiết ở bảng biên). Chưa sửa. Đây là bài học chung: khi nền tảng có khái niệm "nhóm thiết bị", danh sách "tất cả" phải khử trùng lặp giữa nhóm và thành viên, nếu không một thiết bị vật lý nhận hai lệnh.
- Cache TTS tăng vô hạn, chưa có cơ chế dọn.
- Chưa khôi phục âm lượng / media đang phát sau khi thông báo.

---

## Bài học đọc tín hiệu người dùng

- **Yêu cầu đánh số bằng hành vi đáng giá hơn mười đoạn mô tả** — dùng nó làm bảng chấm.
- **Người dùng thường chỉ dán thông báo lỗi, không phân tích.** Toàn bộ việc chẩn đoán thuộc về AI; đừng chờ thêm manh mối.
- **"Vẫn báo lỗi" lặp lại lần hai:** đổi chiến lược, không sửa tiếp cùng hướng.
- **Câu hỏi lạc đề có thể là việc gấp nhất phiên.** Giữa phiên này người dùng hỏi vì sao nhập đúng mật khẩu `sudo` vẫn báo sai — lần theo ra một binary chạy quyền root đang thu mật khẩu. Đừng gạt sang bên vì "ngoài phạm vi".
- **Hai lời kể mâu thuẫn về cùng thiết bị** ("nghe được" rồi vài hôm sau "chỉ nháy sáng rồi tắt"): giữ lịch sử ĐO mới phân định được lỗi thiết bị với hồi quy code.

---

## Dùng lại note này thế nào

Muốn dựng một product cùng kiểu (MCP server điều khiển thiết bị vật lý trong LAN, phơi ra qua reverse proxy) → đọc `reproduction-prompt.md` cạnh file này, rồi lấy bảng ở Bước 6 làm danh sách kiểm khi client ở máy khác không kết nối được.
