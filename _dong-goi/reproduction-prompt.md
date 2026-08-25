# Prompt dựng lại googlecast-mcp từ đầu

Dán phần trong khung cho một trợ lý lập trình, trong một thư mục trống. Prompt
này dựng lại **đúng sản phẩm này**, không phải một sản phẩm tương tự.

Nếu bạn muốn học **cách nghĩ** để xây một thứ khác, đọc `method-note.md`.

---

```
Xây một MCP server bằng Python để trợ lý AI nói tiếng Việt ra loa Google
(Google Cast) trong mạng nội bộ.

## Ba yêu cầu hành vi (đây là tiêu chí nghiệm thu)

1. Dò danh sách loa Google trong LAN rồi LƯU LẠI để lần chạy sau không phải
   dò lại.
2. Nhận một tham số text, chuyển thành giọng nói tiếng Việt, phát ra loa
   được chỉ định.
3. Nếu người dùng KHÔNG chọn loa thì hỏi lại xem phát ở loa nào, hoặc tất cả.

## Chọn công cụ

- MCP: SDK chính thức, ghim `mcp[cli]>=1.13,<2`. GHIM LÀ BẮT BUỘC: trên PyPI
  có một gói tên `mcp` phiên bản 2.0.0 hoàn toàn không liên quan, kéo theo
  `httpx2` (typosquat) và `mcp-types`. Bản thật phụ thuộc `httpx`.
- Cast: `pychromecast`. Không cần so sánh gì — đây là thư viện Python duy
  nhất còn bảo trì cho giao thức Cast.
- TTS: `edge-tts` (`vi-VN-HoaiMyNeural` nữ, `vi-VN-NamMinhNeural` nam).
  Miễn phí, không cần API key, giọng tiếng Việt tự nhiên nhất trong nhóm
  miễn phí.
- Quản lý phụ thuộc: `uv`. Python >= 3.11.

## Ràng buộc kiến trúc bắt buộc

1. Thiết bị Cast TỰ đi tải media qua HTTP; nó không đọc được đường dẫn file
   local. Vì vậy server BẮT BUỘC kiêm luôn một HTTP file server phục vụ thư
   mục cache TTS. Đây không phải tuỳ chọn.
2. Media server BIND `0.0.0.0` nhưng URL QUẢNG BÁ cho loa phải dựng từ địa
   chỉ LAN thật của máy. Hai thứ này KHÁC NHAU — quảng bá `0.0.0.0` thì loa
   không bao giờ tải được file mà server vẫn "chạy tốt".
3. Máy chạy server phải cùng LAN với loa (mDNS + loa tải ngược).
4. pychromecast là thư viện chặn; mọi tool MCP phải đẩy nó sang worker
   thread bằng `asyncio.to_thread`.

## 13 tool

say, discover_devices, list_speakers, list_devices, get_status, play_media,
play, pause, stop, seek, set_volume, set_muted, quit_app

## Quy tắc hành vi không được làm sai

- Lọc loa khỏi thiết bị hình ảnh: chỉ `cast_type` thuộc {"audio","group"} là
  loa. Chromecast/Nest Hub (`cast_type="cast"`) phải bị loại khỏi
  `list_speakers`.
- `say` thiếu tham số chọn loa: KHÔNG phát gì, và KHÔNG ĐƯỢC GỌI TTS. Trả về
  `{"status": "needs_speaker_selection", "speakers": [...], "message": "..."}`
  đủ để LLM hỏi lại người dùng. Không dùng MCP elicitation (nhiều client
  chưa hỗ trợ). Không mặc định phát tất cả (tác dụng phụ vật lý).
- Không có loa nào trên mạng: trả `no_speakers_found` — phân biệt rõ với
  "chưa chọn loa", vì hai tình huống này đòi hai hành động khác nhau.
- Chấp nhận: một tên loa, nhiều tên cách nhau dấu phẩy, hoặc từ khoá
  {"all","tất cả","tat ca","everyone","*"}.
- QUAN TRỌNG NHẤT: từ khoá "tất cả" phải LOẠI các nhóm loa
  (`cast_type == "group"`). Nhóm Cast phát THÔNG QUA các thành viên, nên gửi
  tới cả nhóm lẫn thành viên khiến một loa vật lý nhận hai luồng cùng lúc —
  nghe như tiếng vọng chồng lên nhau. API trả `playing` cho MỌI đích nên
  không thể phát hiện bằng máy. Nhóm vẫn phải cast được khi gọi đích danh.
- Một loa hỏng không được kéo đổ cả lượt: trả `error` riêng cho loa đó, các
  loa còn lại vẫn `playing`, tổng thể `ok` nếu có ít nhất một loa phát được.
- Text rỗng hoặc toàn khoảng trắng: ném `ValueError` TRƯỚC khi gọi mạng.
- Âm lượng ngoài [0.0, 1.0] bị kẹp lại, không lọt xuống thiết bị.
- Cache mp3 theo hash của (giọng, tốc độ, âm lượng, text). File 0 byte coi
  như hỏng, phải sinh lại.
- Lưu bền danh sách thiết bị ở `~/.googlecast-mcp/speakers.json`. Lần lưu sau
  GỘP theo uuid chứ không ghi đè (mDNS lossy, loa đang ngủ hay bị bỏ sót).
  Ghi bằng write-then-rename để một cú sập không để lại file cụt.
- mDNS bỏ sót thiết bị đã lưu: trước khi báo không tìm thấy, thử kết nối
  thẳng tới địa chỉ đã lưu, rồi mới quét lại.

## Transport và triển khai

- Mặc định stdio. Thêm `--transport http|sse`, `--host`, `--port`,
  `--media-port`.
- Nới DNS-rebinding allowlist của SDK, TUYỆT ĐỐI KHÔNG TẮT nó (tắt là mở
  đường cho bất kỳ trang web nào người dùng mở tấn công server nội bộ).
  Allowlist phải có đủ BỐN dạng, thiếu một dạng là 421 ở đúng một tình huống
  mà thông báo lỗi không hề nói cho bạn biết thiếu gì:
    * host trần, KHÔNG kèm ":port"  (reverse proxy ở cổng 443 không gửi port)
    * "host:*"
    * scheme http
    * scheme https  (khi có proxy kết thúc TLS phía trước)
  Thêm cờ `--allow-host <domain>` lặp lại được.
- `--json-response` và `--stateless` cho client không parse được SSE framing
  hoặc bỏ qua header session.
- `--cors-origin <origin>` cho client trình duyệt. SDK trả OPTIONS=405 không
  kèm header CORS nên trình duyệt chặn ở preflight và JS chỉ thấy
  "Failed to fetch". Gắn CORSMiddleware, và BẮT BUỘC
  `expose_headers=["Mcp-Session-Id"]` — thiếu dòng đó thì preflight qua
  nhưng không duy trì được phiên.
- Script `scripts/service.sh` quản lý systemd: install / remove / start /
  stop / restart / status / logs. Lệnh install phải gọi `systemctl restart`
  TƯỜNG MINH — `enable --now` KHÔNG khởi động lại một service đang chạy, nên
  cài lại sẽ im lặng không đổi gì. Lệnh `status` phải in
  `/proc/<MainPID>/cmdline` vì file unit có thể khác dòng lệnh đang chạy
  thật.
- Mẫu cấu hình nginx reverse proxy. Bắt buộc `proxy_buffering off` (thiếu nó
  client TREO mà không có thông báo lỗi nào) và `proxy_read_timeout 3600s`.
- Tên miền KHÔNG được chứa dấu gạch dưới: CA/Browser Forum cấm `_` trong tên
  miền chứng chỉ, nên `a_b.example.com` không bao giờ xin được cert. Dùng
  gạch nối.

## Bộ kiểm chứng

Viết một eval script phân tầng theo tác dụng phụ:
- tầng mặc định: không tác dụng phụ (mock, offline);
- `--online`: gọi edge-tts thật;
- `--hardware`: cast thật ra loa — CÓ TIẾNG ĐỘNG VẬT LÝ, chỉ chạy khi được
  cho phép.

Bốn luật bắt buộc:
1. So TẬP KỲ VỌNG tường minh. Cấm so kích thước/đếm thay cho so tập —
   `len(x) == len(set(x))` vẫn xanh khi tập thu về đúng một phần tử.
2. Mọi khẳng định chạm mạng hoặc thiết bị phải có MỐC CHỜ (timeout + điều
   kiện thoả). `play_media` chỉ chờ ứng dụng trên thiết bị KHỞI ĐỘNG, chưa
   chờ nó PHÁT — đọc trạng thái ngay khi nó trả về là đo tốc độ mạng.
3. Vệ sinh mock: ảnh chụp lấy TRƯỚC tầng đầu tiên, khôi phục trong `finally`,
   mỗi mục kiểm dựng object MỚI. KHÔNG dùng `importlib.reload` — nó nạp
   module mới dưới chân chính cái ảnh chụp đang giữ tay nắm.
4. Một cú sập giữa chừng phải bị ghi thành mục ĐỎ, không được nuốt: nếu
   không, mọi mục kiểm phía sau im lặng không chạy và bộ kiểm nói dối theo
   hướng lạc quan.

Rồi viết script kiểm ngược: với mỗi lỗi gieo vào mã nguồn, KHAI TRƯỚC danh
sách mục kiểm lẽ-ra-phải-đỏ; chạy; mục lẽ-ra-đỏ-mà-XANH là TEST GIẢ, phải
sửa bài kiểm hoặc ghi CHƯA PHỦ. Cuối cùng xác minh hoàn nguyên bằng cách
khôi phục, XOÁ `__pycache__`, rồi CHẠY LẠI bộ kiểm và đòi thấy XANH —
`git status` sạch KHÔNG phải bằng chứng hoàn nguyên.

## Tài liệu

README ở gốc repo: cài, chạy, các cờ, cách nối từng loại client (Claude Code
qua stdio; Claude Desktop máy khác — chỉ nhận https nên phải bắc cầu
`npx -y mcp-remote http://<ip>:<port>/mcp --allow-http`; client trình duyệt
cần `--cors-origin` khớp chính xác origin trên thanh địa chỉ).
`docs/architecture.md`: luồng dữ liệu, vai trò từng module, các bẫy đã gặp.
```

---

## Kiểm lại kết quả dựng

Sản phẩm dựng lại đúng khi:

1. `uv sync` rồi `uv run googlecast-mcp --help` chạy được.
2. `initialize` + `tools/list` (header `Accept: application/json,
   text/event-stream`) trả về **đúng 13 tool**.
3. `tools/call list_speakers` trả về loa thật trong LAN, **không có thiết bị
   hình ảnh nào lọt vào**.
4. `say` thiếu tham số chọn loa → `needs_speaker_selection`, **không loa nào
   phát**, **không gọi TTS**.
5. `say` với `target="all"` → **không** gửi tới nhóm loa.
6. Một loa thật + một tên không tồn tại → loa thật vẫn `playing`, tên sai trả
   `error` riêng, tổng thể `ok`.
7. `say` ra loa thật → nghe được tiếng Việt, và **người nghe xác nhận** nó tự
   nhiên. Bước 7 không có bài kiểm tự động nào thay thế được.
