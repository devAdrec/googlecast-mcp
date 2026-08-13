# Reproduction prompt — googlecast-mcp

Dán khối dưới cho một AI coding agent để dựng lại product tương đương từ số không.
Đọc kèm `method-note.md` để hiểu vì sao từng ràng buộc tồn tại.

## Đề bài gốc (nguyên văn của người dùng, prompt sinh ra cả product)

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba dòng đó là đề bài. Toàn bộ phần dưới là **ràng buộc rút ra sau khi làm thật** — nếu bạn muốn trải nghiệm
lại quá trình khám phá, hãy bắt đầu chỉ với 3 dòng trên; nếu bạn muốn đi thẳng tới kết quả, dùng cả khối dưới.

---

Xây một MCP server bằng Python 3.12 + uv, dùng official MCP SDK (FastMCP) + pychromecast, làm 3 việc:

1. Dò thiết bị Google Cast trong LAN qua mDNS; lọc riêng loa (`cast_type` là `audio` hoặc `group`)
   khỏi TV/màn hình (`cast`); lưu bền ra `~/.googlecast-mcp/speakers.json`, merge theo `uuid`.
2. Tool `say(text, target?, voice, rate)`: text tiếng Việt → TTS bằng **edge-tts**
   (`vi-VN-HoaiMyNeural` nữ / `NamMinhNeural` nam) → phát ra loa.
3. Nếu `target` trống → KHÔNG phát gì; trả về danh sách loa + thông điệp để LLM hỏi lại người dùng.
   Chấp nhận một tên, nhiều tên cách dấu phẩy, hoặc `all` / `tất cả` (fan-out bằng `asyncio.gather`).

Tổng 13 tool: say, discover_devices, list_speakers, list_devices, get_status, play_media, play, pause,
stop, seek, set_volume, set_muted, quit_app.

Ràng buộc bắt buộc:

- **Thiết bị Cast tự đi tải media qua HTTP**, không đọc được đường dẫn local ⇒ server phải kèm một
  `ThreadingHTTPServer` phục vụ thư mục cache TTS trên **IP LAN** (cổng riêng, ví dụ 8766).
- Cache file TTS theo `sha256(voice|rate|volume|text)`.
- Wrapper pychromecast phải thread-safe, có cache kết nối, và có `_connect_saved()`: nối thẳng bằng
  host/port đã lưu qua `pychromecast.get_chromecast_from_host()` **trước khi** quét mDNS lại
  (mDNS lossy, hay sót thiết bị đã biết).
- `pyproject.toml` pin `mcp[cli]>=1.13,<2` — gói `mcp` 2.0.0 trên PyPI là gói khác, kéo theo `httpx2`.
- CLI hỗ trợ transport stdio / streamable-http / sse, kèm cờ `--allow-host`, `--cors-origin`,
  `--json-response`, `--stateless`.
- Bảo mật transport: **giữ nguyên** bảo vệ DNS-rebinding của SDK, chỉ nới `allowed_hosts`/`allowed_origins`.
  Phải thêm cả biến thể có scheme `https` và biến thể host **không kèm `:port`** (proxy ở 443 không gửi port).
- CORS: bọc `mcp.streamable_http_app()` bằng Starlette `CORSMiddleware`, **bắt buộc**
  `expose_headers=["Mcp-Session-Id"]`.
- Kèm `scripts/service.sh` (systemd install/remove/start/stop/**restart**/status/logs). `status` phải in
  `/proc/<MainPID>/cmdline`; `install` phải `restart` chứ không chỉ `enable --now`.
- Kèm vhost nginx mẫu với `proxy_buffering off` và `proxy_read_timeout 3600s`.
- Domain phải dùng **gạch ngang**, không gạch dưới (CA không cấp cert cho hostname có `_`).

Layout module (`src/googlecast_mcp/`), mỗi file một trách nhiệm:

- `cast_manager.py` — wrapper pychromecast thread-safe: discovery, cache kết nối, controls, `_connect_saved()`.
- `speaker_store.py` — lưu/nạp JSON, merge theo `uuid`, hàm `is_speaker()`.
- `tts.py` — edge-tts → mp3, cache theo hash.
- `media_server.py` — HTTP server phục vụ thư mục cache, hàm `lan_ip()`.
- `server.py` — 13 `@mcp.tool()`, `_select_targets()`, fan-out.
- `__main__.py` — CLI: transport, cấu hình bảo mật transport, CORS, cleanup.

Tài liệu: `README.md` (cài đặt, cấu hình client cho cả stdio/HTTP/reverse-proxy, bảng troubleshooting,
lệnh triển khai thật kèm giải thích từng cờ) và `docs/architecture.md` (luồng request, module, threading,
cache, ports, "things that bite", security model).

Ghi rõ trong tài liệu: server **không có xác thực tầng ứng dụng**, và cổng audio bind mọi interface, không
xác thực, phục vụ nguyên một thư mục; nếu domain public thì phải chặn ở nginx (`allow 192.168.0.0/16; deny all;`).

## Definition of done

Coi là xong khi **cả 5 mục sau đã chạy thật trên phần cứng thật**, không phải chạy qua test giả:

1. Phát được câu tiếng Việt nghe rõ trên loa thật, **trọn thời lượng**, kết thúc với `idle_reason=FINISHED`.
2. Dò được thiết bị trong LAN và **lọc đúng** loa khỏi thiết bị có màn hình; danh sách sống sót qua restart.
3. Một MCP client thật kết nối qua HTTP và gọi được **đủ 13 tool**.
4. Một client chạy trong trình duyệt: preflight `OPTIONS` trả **200**, `tools/list` trả về đủ tool
   (nếu preflight 405 hoặc thiếu `expose_headers` thì chưa xong).
5. Gọi `say` **không có `target`** → KHÔNG phát gì, trả về danh sách loa để LLM hỏi lại.
