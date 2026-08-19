# Prompt dựng lại googlecast-mcp

Dán khối dưới đây cho một AI coding agent trong một thư mục trống. Mục tiêu là dựng
lại **đúng product này**, kể cả các quyết định đã trả giá mới có — chứ không phải một
biến thể "tương đương về ý tưởng".

Muốn học **cách nghĩ** để xây một product KHÁC: đọc `method-note.md`.
Muốn **cài và chạy** bản đã có: đọc `package/README.md`.

---

```
Xây một MCP server bằng Python cho phép AI nói tiếng Việt ra loa Google trong nhà.

## Yêu cầu hành vi (gốc, đánh số — đối chiếu từng dòng khi xong)

1. Dò danh sách loa Google trong mạng nội bộ, sau đó LƯU LẠI.
2. Nhận một tham số text, chuyển thành âm thanh tiếng Việt, phát lên loa theo yêu cầu.
3. Nếu người dùng KHÔNG chọn loa thì phải hỏi lại xem phát ở loa nào, hoặc tất cả.

Thêm (sinh ra từ hoàn cảnh triển khai thật):
4. Chạy được như systemd service; MCP client ở MÁY KHÁC gọi tới được, kể cả client
   chỉ chấp nhận https và client chạy trong trình duyệt.

## Stack

Python 3.12 + uv. MCP SDK (FastMCP), pychromecast, edge-tts.

PIN `mcp[cli]>=1.13,<2` VÀ ĐỪNG NỚI TRẦN. Trên PyPI có gói tên `mcp` phiên bản 2.0.0
KHÔNG liên quan gì tới MCP SDK: layout khác hẳn, kéo theo `httpx2` (typosquat) và
`mcp-types`. Dấu hiệu nhận bản đúng: nó phụ thuộc `httpx`, không phải `httpx2`.

## Ràng buộc kiến trúc — đọc kỹ, đây là thứ quyết định thiết kế

Thiết bị Cast TỰ đi tải media qua HTTP; nó KHÔNG đọc được đường dẫn file local.
Hệ quả không né được: server này bắt buộc phải kiêm luôn một HTTP file server phục vụ
thư mục cache mp3.

Server audio đó bind `0.0.0.0` (mọi interface), NHƯNG URL quảng bá cho thiết bị thì
dựng từ IP LAN dò được. HAI THỨ NÀY KHÁC NHAU — địa chỉ lắng nghe không phải địa chỉ
quảng bá. Bind rộng vì interface định tuyến ra internet chưa chắc là interface loa
dùng để gọi về. Đừng viết gọn thành "bind trên IP LAN".

## Cấu trúc mô-đun

src/googlecast_mcp/
  cast_manager.py   — bọc pychromecast, thread-safe, cache kết nối
  speaker_store.py  — lưu bền ~/.googlecast-mcp/speakers.json
  tts.py            — edge-tts, cache mp3
  media_server.py   — HTTP phục vụ thư mục cache
  server.py         — FastMCP, 13 tool
  __main__.py       — CLI, chọn transport, cấu hình bảo mật
scripts/service.sh                  — systemd install/remove/start/stop/restart/status/logs
scripts/nginx-googlecast-mcp.conf   — mẫu vhost reverse proxy https

13 tool: say, discover_devices, list_speakers, list_devices, get_status, play_media,
play, pause, stop, seek, set_volume, set_muted, quit_app.

## Quyết định bắt buộc giữ nguyên (mỗi cái đều đã trả giá)

1. TTS = edge-tts, giọng vi-VN-HoaiMyNeural (nữ, mặc định) / vi-VN-NamMinhNeural (nam).
   Người dùng chọn sau khi NGHE thử 4 phương án. gTTS giọng máy móc; Google Cloud TTS
   cần key + phí; Piper offline nhưng yếu và setup nặng. Đánh đổi đã chấp nhận có ý
   thức: edge-tts cần internet.

2. Thiếu `target` → KHÔNG phát gì, KHÔNG cả gọi TTS. Trả về:
   {"status": "needs_speaker_selection", "speakers": [...], "message": "..."}
   với message viết CHO LLM ĐỌC: nói rõ phải hỏi người dùng gì và gọi lại tool với
   tham số nào.
   Không dùng MCP elicitation (nhiều client chưa hỗ trợ → hỏng câm ở đúng client cần
   nó). Không mặc định phát tất cả (tác dụng phụ vật lý, sai là ồn cả nhà, không có
   nút hoàn tác).

3. `target` nhận: một tên, nhiều tên cách phẩy, hoặc "all" / "tất cả".

4. "all" phải LOẠI BỎ thiết bị có cast_type == "group". Nhóm Cast phát QUA các loa
   thành viên; gộp cả hai làm một loa vật lý nhận hai luồng. Điểm đáng sợ: MỌI thiết
   bị vẫn trả `playing` — trạng thái API không phát hiện được lỗi này, chỉ nghe mới
   biết. Nhóm vẫn phải gọi được bằng tên.

5. Lưu bền danh sách thiết bị, HỢP NHẤT theo uuid (không ghi đè), ghi kiểu
   write-then-rename. mDNS lossy và chậm; một lần quét sót không được xoá mất thiết bị
   đã biết. Khi mDNS sót một thiết bị đang có trong store thì nối THẲNG bằng host/port
   đã lưu — nếu không, lỗi "không tìm thấy" sẽ tự mâu thuẫn: nó liệt kê chính thiết bị
   đó trong danh sách đã biết.

6. Lọc loa: cast_type "audio" và "group" là loa; "cast" là thiết bị hình ảnh, loại ra.

7. pychromecast là thư viện blocking → mọi lời gọi đi qua asyncio.to_thread.

8. Cast tới nhiều loa thì mỗi loa một task, bắt lỗi RIÊNG từng loa. Một loa chết trả
   error cho riêng nó; tổng thể vẫn "ok" nếu ít nhất một loa phát được. Trong nhà luôn
   có một thiết bị đang treo; nếu nó kéo đổ cả lệnh thì tính năng coi như không dùng
   được.

9. GIỮ NGUYÊN bảo vệ DNS-rebinding của SDK, CHỈ NỚI allowlist. Tắt nó là mở cho một
   trang web bất kỳ mà nạn nhân đang mở sai khiến server nội bộ của họ.

## Ngõ cụt — cài sẵn cách thoát, đừng để phải tự vấp lại

a) 421 Misdirected Request: SDK chỉ tin 127.0.0.1; bind 0.0.0.0 KHÔNG đủ (bind là
   chuyện nghe, allowlist là chuyện tin). Cần cờ --allow-host <domain> lặp lại được.
   Allowlist PHẢI chứa cả scheme `https` (reverse proxy đổi scheme) VÀ host KHÔNG kèm
   `:port` (trang ở cổng 443 gửi Host không có port). Thiếu một trong hai là hỏng.

b) nginx: BẮT BUỘC `proxy_buffering off;` và `proxy_read_timeout 3600s;`. Thiếu, client
   TREO IM LẶNG, không báo bất kỳ lỗi nào.

c) Tên miền KHÔNG được chứa dấu gạch dưới — CA/B Forum cấm `_`, sẽ KHÔNG BAO GIỜ xin
   được chứng chỉ. Gặp client chỉ nhận https thì đây là ngõ cụt tuyệt đối, không có
   cách vòng. Dùng gạch nối.

d) Claude Desktop custom connector chỉ nhận https. Đường vòng nhẹ hơn reverse proxy:
   npx -y mcp-remote http://<ip>:<port>/mcp --allow-http

e) Client trình duyệt báo "Failed to fetch (check CORS?)": SDK trả OPTIONS = 405 không
   header CORS, trình duyệt chặn và JS chỉ thấy lỗi TRỐNG. Cần cờ --cors-origin bọc
   streamable_http_app() bằng CORSMiddleware. BẮT BUỘC expose_headers=["Mcp-Session-Id"]
   — đây là lỗi thứ hai nấp sau lỗi thứ nhất: qua được preflight vẫn hỏng, vì trình
   duyệt không đọc được header không được expose nên không giữ được session. Origin
   phải khớp CHÍNH XÁC thanh địa chỉ; trang ở cổng 80/443 gửi origin không kèm port.

f) Client khắt khe: cần thêm --json-response (trả JSON thay vì khung SSE) và --stateless
   (không đòi client mang Mcp-Session-Id giữa các request).

g) `systemctl enable --now` KHÔNG restart service đang chạy → tiến trình cũ giữ nguyên
   mã và tham số CŨ trong khi mọi thứ trông như đã cài xong. Lệnh install PHẢI gọi
   restart tường minh, và lệnh status PHẢI in /proc/<MainPID>/cmdline để xác nhận tiến
   trình đang chạy đúng tham số. (Không có điều này, một tiến trình cũ đã sống 3 ngày.)

h) 406 khi mở /mcp bằng trình duyệt là ĐÚNG ĐẶC TẢ, không phải lỗi. Đừng đi sửa.

## Cờ CLI

--transport stdio|http|sse, --host, --port, --media-port, --allow-host (lặp lại được),
--json-response, --stateless, --cors-origin (lặp lại được).
Ghim cổng audio để chỉ phải viết một luật tường lửa.

## Eval — viết luôn, hai tầng

Tầng offline (mặc định, KHÔNG phát tiếng, chạy được ở mọi máy): dùng speaker store giả
trong thư mục tạm + thay thế lớp cast và TTS. Kiểm: server import được; đúng 13 tool;
lọc loa audio/group vs cast; đoán MIME theo đuôi file; map giọng; allowlist có https và
host không kèm port; say thiếu target trả needs_speaker_selection VÀ không cast VÀ
không gọi TTS; say "all" không chứa cast_type=group; nhóm vẫn gọi được bằng tên; cô lập
lỗi từng loa; text rỗng → ValueError; TTS sinh mp3 khác rỗng (cần internet, thiếu mạng
thì báo SKIP chứ không FAIL).

Tầng hardware (chỉ chạy khi có cờ --hardware, MẶC ĐỊNH TẮT): cast thật, PHÁT TIẾNG RA
LOA THẬT. Ghi cảnh báo rõ ràng trong script.

Script trả exit code 0/1 và in pass/fail từng mục.

LƯU Ý KỸ THUẬT khi viết eval: SpeakerStore đọc biến môi trường ngay lúc khởi tạo, mà
server.py khởi tạo CastManager ở CẤP MODULE. Nên biến GOOGLECAST_MCP_STORE phải được
đặt TRƯỚC lệnh import; đặt sau, eval sẽ đụng vào file thật của người dùng.

Và sau khi eval xanh, KIỂM NGƯỢC nó: cố tình đưa lỗi cũ trở lại (cho "all" gồm cả nhóm
lẫn thành viên) và xác nhận eval FAIL đúng mục. Một bộ eval chưa từng thấy màu đỏ là
một bộ eval chưa biết có hoạt động không.

## Tài liệu

README.md: cài, chạy, chạy như service, cấu hình client (remote/local/reverse proxy),
danh sách tool, troubleshooting.
docs/architecture.md: vấn đề cốt lõi, luồng request, mô-đun, threading, cache, phân
giải thiết bị, triển khai, cổng, những chỗ hay cắn, mô hình bảo mật.

## Nói thẳng những gì product này CHƯA làm — đừng che

- Không có xác thực ở tầng ứng dụng. Tên miền công khai = ai biết URL cũng phát được
  tiếng trong nhà.
- Cổng audio bind 0.0.0.0, không xác thực, phục vụ nguyên một thư mục file. Chặn IP ở
  nginx CHỈ che cổng MCP, KHÔNG chạm cổng audio.
- Cache TTS tăng vô hạn, chưa dọn.
- Chưa khôi phục âm lượng / media đang phát sau khi thông báo xong.
```

---

## Cách kiểm bản dựng lại có đúng không

Chạy eval offline — phải 0 FAIL. Rồi đối chiếu bằng tay bốn điểm mà eval offline
**không** bắt được:

1. `nc -z <ip-loa> 8009` thông, và loa **thật sự tải được** file audio về (xem log HTTP
   của media server có `200` không).
2. Client thật ở **máy khác** thấy đủ 13 tool.
3. `service.sh status` in ra dòng `cmdline` **đúng tham số** bạn vừa đặt.
4. **Nghe bằng tai** khi gọi `all`: phải là các loa riêng lẻ, không chồng tiếng. Đây là
   điểm duy nhất mà không một chỉ số nào thay thế được — trạng thái API báo `playing`
   ngay cả khi âm thanh sai.
