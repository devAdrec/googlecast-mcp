# Prompt dựng lại googlecast-mcp

Dán khối dưới đây cho một AI coding agent trong một thư mục trống. Nó dựng lại
đúng sản phẩm này, **không** cần đọc mã nguồn cũ.

Khác với `method-note.md`: file kia dạy cách nghĩ để xây cái khác; file này
dựng lại đúng cái này.

---

```
Xây một MCP server bằng Python để nói tiếng Việt ra loa Google Cast trong nhà.

## Ba yêu cầu chức năng

1. Dò danh sách loa Google trong mạng nội bộ, sau đó LƯU LẠI (bền qua restart,
   không phải cache RAM).
2. Nhận text làm tham số, chuyển thành âm thanh tiếng Việt, phát lên loa theo
   yêu cầu.
3. Nếu người dùng không chọn loa thì hỏi lại xem phát ở loa nào, hoặc tất cả.

## Ba yêu cầu vận hành

4. Chạy được dạng systemd service; có install / remove / start / stop /
   restart / status / logs.
5. Cổng cố định, biết trước, để đặt được sau nginx reverse proxy có TLS.
6. Chạy được với client trong trình duyệt, và với client khắt khe hơn đặc tả.

## Thư viện — đã chốt, đừng so sánh lại

- `pychromecast` cho giao thức Cast. Thư viện Python duy nhất còn bảo trì.
- `edge-tts` cho giọng nói: `vi-VN-HoaiMyNeural` (nữ), `vi-VN-NamMinhNeural`
  (nam). Đã so với gTTS (giọng máy móc), Google Cloud TTS (cần key + phí),
  Piper (offline nhưng yếu). edge-tts tự nhiên nhất và không cần key.
- SDK MCP: ghim `mcp[cli]>=1.13,<2`. Trên PyPI có gói tên `mcp` phiên bản
  2.0.0 KHÔNG liên quan, kéo theo httpx2 và mcp-types. Đừng cài nhầm.
- Python >= 3.11, quản lý bằng uv.

## Ràng buộc gốc — đọc kỹ, mọi thứ khác mọc ra từ đây

Thiết bị Cast TỰ đi tải media qua HTTP. Nó KHÔNG đọc được đường dẫn file local.

Vì vậy server bắt buộc kiêm luôn một HTTP file server phục vụ thư mục cache mp3.
Bind `0.0.0.0`, nhưng URL quảng bá cho loa phải dựng từ địa chỉ LAN thật của máy
— HAI THỨ KHÁC NHAU, đừng lẫn.

Máy chạy server phải cùng LAN với loa: mDNS không đi qua router, và loa phải
với tới được server.

## Module

- `cast_manager.py`   — bọc pychromecast, thread-safe, cache kết nối sống
- `speaker_store.py`  — lưu bền ra ~/.googlecast-mcp/speakers.json
- `tts.py`            — edge-tts, cache mp3 theo hash của (voice|rate|volume|text)
- `media_server.py`   — HTTP server phục vụ thư mục cache
- `server.py`         — FastMCP, 13 tool
- `__main__.py`       — CLI, chọn transport, cấu hình bảo mật

13 tool: say, discover_devices, list_speakers, list_devices, get_status,
play_media, play, pause, stop, seek, set_volume, set_muted, quit_app.

pychromecast là blocking. Mọi lời gọi tới nó phải đi qua `asyncio.to_thread`
để không chặn event loop của MCP.

## Hành vi bắt buộc, không thương lượng

- Loa = `cast_type` thuộc {"audio", "group"}. `cast_type == "cast"` là thiết bị
  hình ảnh (Chromecast, Nest Hub) — không phải loa.
- `say` KHÔNG được đặt `target` vào `required` của schema. Thiếu `target` thì
  trả `{"status": "needs_speaker_selection", "speakers": [...], "message": ...}`
  và KHÔNG tổng hợp âm thanh, KHÔNG gửi lệnh cast nào. Message phải nói rõ có
  thể chọn "all".
- Mạng không có loa nào → `{"status": "no_speakers_found", ...}`.
- `target` nhận: một tên, nhiều tên cách phẩy, hoặc "all"/"tất cả"/"tat ca"/
  "everyone"/"*". Không phân biệt hoa thường. Cắt khoảng trắng thừa, bỏ phần tử rỗng.
- `target="all"` phải BỎ QUA `cast_type == "group"`. Nhóm Cast phát QUA các loa
  thành viên, nên gửi tới cả nhóm lẫn thành viên khiến một loa vật lý nhận hai
  luồng cùng lúc. Cả bốn lời gọi vẫn trả "playing" — API không phát hiện được,
  chỉ nghe mới biết. Nhóm vẫn phải phát được khi gọi đích danh tên nhóm.
- Một loa hỏng → phần tử đó trả "error" riêng, những loa còn lại vẫn phát,
  tổng thể vẫn "ok". Chỉ khi mọi loa hỏng mới trả "failed".
- Text rỗng hoặc chỉ khoảng trắng → ValueError, TRƯỚC khi gọi mạng.
- `speaker_store.save()` phải HỢP NHẤT theo uuid, không thay thế: mDNS lossy,
  một lần quét sót không được xoá thiết bị đã biết. Ghi bằng write-then-rename.
  File hỏng hoặc thiếu → đọc ra rỗng, không sập.
- Khi giải tên loa mà lần quét hiện tại sót, phải thử kết nối thẳng tới địa chỉ
  đã lưu (`get_chromecast_from_host`) trước khi quét lại. Nếu không sẽ ném
  DeviceNotFoundError cho một thiết bị mà chính store đang liệt kê — tự mâu thuẫn.

## Bảo mật transport — nơi tốn nhiều thời gian nhất

SDK MCP chỉ tin 127.0.0.1. Bind 0.0.0.0 KHÔNG đủ: client từ máy khác nhận
`421 Misdirected Request`.

GIỮ bảo vệ DNS-rebinding, chỉ NỚI allowlist. Tắt nó là mở cửa cho web bất kỳ
tấn công server nội bộ.

Allowlist phải gồm, và cả hai điểm này đều đã làm hỏng thật:
- Host TRẦN, không kèm ":port" — proxy ở cổng 443 gửi Host không có phần cổng.
- Cả scheme "https" — TLS kết thúc ở nginx nhưng origin trình duyệt vẫn là https.
Địa chỉ bind wildcard (0.0.0.0) không được tính là một allowed host.

Cờ CLI: `--transport {stdio,http,sse}`, `--host`, `--port`, `--media-port`,
`--allow-host` (lặp được), `--json-response`, `--stateless`, `--cors-origin`
(lặp được).

CORS: SDK không sinh phản hồi CORS — OPTIONS trả 405 không header, trình duyệt
chặn, JS chỉ thấy "Failed to fetch (check CORS?)". Bọc app Starlette bằng
CORSMiddleware, và BẮT BUỘC `expose_headers=["Mcp-Session-Id"]` — không expose
thì trình duyệt không giữ được phiên, mà triệu chứng trông giống hệt lỗi CORS.

`--json-response` cho client không đọc được khung SSE; `--stateless` cho client
bỏ qua header session.

## Service và reverse proxy

`scripts/service.sh`: sinh unit systemd, MCP mặc định 8765, media 8766, đọc
MCP_HOST / MCP_PORT / MEDIA_PORT / MCP_EXTRA_ARGS từ môi trường.

`install` phải gọi `systemctl restart` tường minh. `enable --now` KHÔNG khởi
động lại service đang chạy — tiến trình cũ từng sống ba ngày với dòng lệnh cũ
và trông y hệt như bản sửa không có tác dụng.

`status` phải in `/proc/<MainPID>/cmdline`, để phân biệt được "bản sửa sai" với
"bản sửa chưa được nạp".

nginx: `proxy_buffering off` và `proxy_read_timeout 3600s`. Thiếu cái đầu thì
client TREO IM, không có lỗi nào để tìm. Chỉ proxy 8765; 8766 ở lại LAN vì loa
lấy file trực tiếp.

Tên miền KHÔNG được có gạch dưới: CA/B Forum cấm "_", nên tên như
`google_cast.example.com` không bao giờ xin được chứng chỉ — mà Claude Desktop
chỉ nhận https. Ngõ cụt tuyệt đối, không có cách vòng.

Claude Desktop ở máy khác: ô custom connector chỉ nhận https, nên với server
LAN chạy http phải bắc cầu bằng
`npx -y mcp-remote http://<ip>:8765/mcp --allow-http`.

## Eval — viết cùng lúc với mã, không để sau

Ba tầng phân theo TÁC DỤNG PHỤ:
- mặc định: offline, không mạng, không tiếng. Chạy ở đâu cũng an toàn.
- `--online`: gọi edge-tts thật, vẫn im lặng.
- `--hardware`: cast thật, PHÁT TIẾNG. Cờ opt-in, phải xin phép mỗi lần.

Test mà không ai dám chạy thì bằng không có.

VỆ SINH MOCK — đã dính hai lần, đừng đi lại:
- Mọi phép thay thế đi qua context manager khôi phục trong `finally`.
- Một hàm kiểm "còn sạch không" chạy SAU MỖI TẦNG, đối chiếu với ảnh chụp lấy
  trước khi tầng đầu tiên chạy.
- Tầng online và hardware phải DỰNG OBJECT MỚI của riêng mình, không dùng
  singleton dùng chung. Một canh gác chỉ che một đường; cô lập mới giải quyết.
- ĐỪNG dùng importlib.reload để "lấy lại bản sạch": nó gán lại function object
  mới và phá mất tay nắm duy nhất vào hàm thật.

Kiểm hai điều-không-xảy-ra bằng tripwire (hàm ném lỗi nếu bị gọi), không bằng
giá trị trả về: thiếu `target` thì KHÔNG cast và KHÔNG gọi TTS.

Kiểm `all` theo `host`, KHÔNG theo tên. Và kiểm PHỦ CHÍNH XÁC (số lần cast
bằng đúng tập host loa riêng biệt), không phải "không trùng" — "không trùng"
vẫn xanh khi `all` sai thành đúng một phần tử. Đó là một test giả.

KIỂM NGƯỢC: viết một script gieo lỗi vào mã, với danh sách kỳ-vọng-đỏ ghi
TRƯỚC khi gieo. Mục nào lẽ ra đỏ mà vẫn xanh là TEST GIẢ. Sau khi khôi phục
phải XOÁ BYTECODE và xác minh eval xanh lại — một lỗi gieo vào dài y hệt bản
gốc sẽ để lại .pyc cũ khiến cây mã đã khôi phục vẫn chạy như bản hỏng.

## Tài liệu

README.md (cài đặt, cấu hình client, gỡ lỗi) và docs/architecture.md (luồng
xử lý, mô hình luồng, mô hình bảo mật, "những chỗ cắn người").

Nói thẳng những điểm còn hở: không có xác thực ở tầng ứng dụng; cổng audio
bind 0.0.0.0 không xác thực và không đi qua nginx nên chặn IP ở nginx không
che được nó; cache TTS tăng vô hạn.
```
