# Prompt dựng lại googlecast-mcp

Dán nguyên khối dưới đây cho một AI coding agent trong một thư mục trống. Nó
đủ để dựng lại **đúng product này**, không phải một product hao hao.

Muốn học *cách nghĩ* để làm product khác thì đọc `method-note.md`. File này
chỉ để tái dựng.

---

## Khối prompt

````
Xây một MCP server bằng Python tên `googlecast-mcp`. Nó tìm các loa Google Cast
trong mạng nội bộ và **đọc text tiếng Việt thành tiếng nói phát ra loa**.

## Ba yêu cầu gốc (nguyên văn của người đặt hàng, giữ nguyên lỗi gõ)

1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh
   hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

## Ràng buộc kiến trúc không thương lượng

Thiết bị Cast **tự đi tải media qua HTTP**; nó không phải cái loa để ghi byte
vào. Suy ra: server này BẮT BUỘC kiêm luôn một HTTP file server phục vụ thư
mục cache audio, ở một địa chỉ mà LOA với tới được. Đường dẫn file cục bộ là
vô nghĩa với loa.

Hệ quả phải xử lý đúng: bind nghe trên `0.0.0.0`, nhưng URL quảng bá dựng từ
địa chỉ LAN thật của máy. Hai thứ này KHÁC NHAU và cố ý khác nhau.

## Thư viện, đã chốt — đừng đi chọn lại

- `mcp[cli]>=1.13,<2` (FastMCP, SDK chính thức). **Ghim dưới 2.0**: trên PyPI
  có một gói tên `mcp` phiên bản 2.0.0 hoàn toàn không liên quan, kéo theo
  `httpx2` và `mcp-types`. Gói đúng cần `httpx`.
- `pychromecast>=14` — thư viện Python duy nhất còn bảo trì phủ giao thức Cast.
- `edge-tts>=7` — giọng tiếng Việt tự nhiên nhất trong các lựa chọn miễn phí,
  không cần API key. Giọng nữ `vi-VN-HoaiMyNeural`, nam `vi-VN-NamMinhNeural`.
- Quản lý môi trường bằng `uv`. Python ≥ 3.11.

## Cấu trúc

```
src/googlecast_mcp/
  cast_manager.py   # bọc pychromecast: dò, phân giải, điều khiển (blocking)
  speaker_store.py  # lưu bền danh sách thiết bị ra JSON, gộp theo uuid
  tts.py            # edge-tts → mp3, cache theo nội dung
  media_server.py   # phục vụ thư mục cache trên LAN
  server.py         # 13 tool FastMCP
  __main__.py       # chọn transport, allowlist, CORS
scripts/service.sh  # vòng đời systemd
```

13 tool, đúng những tên này: say, discover_devices, list_speakers, list_devices,
get_status, play_media, play, pause, stop, seek, set_volume, set_muted, quit_app.

`pychromecast` là thư viện chặn (blocking), nên MỌI tool phải đẩy nó sang
worker thread bằng `asyncio.to_thread`, đừng chặn vòng lặp sự kiện của MCP.

## Hành vi bắt buộc, kèm lý do

### Chọn loa (`say`)

- Thiếu loa đích → **KHÔNG phát gì cả, kể cả không render TTS**. Trả về
  `{"status": "needs_speaker_selection", "speakers": [...], "message": ...}`,
  trong đó `message` là câu chỉ dẫn cho LLM đi hỏi lại người dùng và có liệt
  kê sẵn tên loa. Lý do: âm thanh đã ra khỏi loa thì không thu lại được —
  mặc định an toàn là không phát, không phải phát tất cả.
- Mạng không có loa nào → `{"status": "no_speakers_found", ...}`. Phải khác
  với trường hợp trên; hai tình huống này cần hai cách xử lý khác nhau.
- Nhận: một tên loa · nhiều tên cách nhau bằng dấu phẩy · `all` · `tất cả`
  (kèm `tat ca`, `everyone`, `*`).
- **`all` phải BỎ QUA nhóm loa** (`cast_type == "group"`). Nhóm Cast phát QUA
  các thành viên của nó, nên gộp cả nhóm lẫn thành viên sẽ đẩy hai luồng vào
  cùng một loa vật lý. Kết quả API không phân biệt được điều này — cả hai đều
  báo `playing`; chỉ nghe mới biết. Gọi thẳng tên nhóm thì vẫn phát vào nhóm.
- Một loa hỏng KHÔNG được đánh sập cả lệnh: bọc từng lời gọi, trả `error`
  riêng cho phần tử đó, tổng thể vẫn `ok` nếu còn loa nào phát được. Chỉ khi
  hỏng hết mới `failed`.

### Lưu bền thiết bị

- Ghi ra `~/.googlecast-mcp/speakers.json` (đổi được bằng `GOOGLECAST_MCP_STORE`).
- **Gộp theo uuid, không ghi đè.** mDNS lossy: một lần quét sót thiết bị không
  được xoá thiết bị đã biết. Cập nhật phải giữ lại các trường cũ.
- Ghi ra file tạm rồi đổi tên (atomic), để sập giữa chừng không để lại file cụt.
- File hỏng hoặc chưa có → trả danh sách rỗng, không được ném lỗi.
- Loa là `cast_type` ∈ {`audio`, `group`}; `cast` là thiết bị hình ảnh, phải lọc ra.
- Khi phân giải một tên: thử cache sống → **thử địa chỉ đã lưu** → mới quét
  lại. Bỏ bước giữa thì thiết bị đã lưu mà lần quét này sót sẽ thành lỗi
  "không tìm thấy" đầy mâu thuẫn.

### TTS

- Cache mp3 trên đĩa, khoá băm từ **(giọng, tốc độ, âm lượng, nội dung)** — đủ
  cả bốn, thiếu cái nào là cache trả nhầm.
- **Tuần tự hoá việc render.** Dịch vụ từ chối các kết nối đến cùng lúc. Thử
  lại KHÔNG đủ: đo được 4/6 đạt trong 101 giây khi chỉ có thử lại, vì các lần
  thử vẫn chồng lên nhau. Có khoá rồi: 6/6 trong 12 giây.
- **Một khoá cho MỖI VÒNG LẶP sự kiện**, không phải một khoá cho cả tiến trình
  (dùng `weakref.WeakKeyDictionary` khoá theo vòng lặp). Một `asyncio.Lock`
  mức module chỉ tự gắn vào vòng lặp KHI THỰC SỰ CÓ TRANH CHẤP — đường nhanh
  của `acquire()` trả về trước khi chạm tới vòng lặp — nên lỗi nằm im cho tới
  lúc hai render chồng nhau, rồi mọi vòng lặp khác đều hỏng. Sau khi vá: 6/6
  trong 6.2 giây, và hai vòng lặp liên tiếp đều chạy được.
- 3 lần thử, giãn cách tăng dần, **xoá file dở trước mỗi lần thử**: `save()`
  có thể tạo file rồi mới ném lỗi, để lại file 0 byte. File 0 byte KHÔNG được
  tính là cache hợp lệ.
- Kiểm cache hai lần: trước khi lấy khoá, và một lần nữa sau khi lấy được (có
  thể người khác đã render xong trong lúc chờ).

### Transport và an ninh

- `--transport stdio|http|sse`, `--host`, `--port`, `--media-port`.
- SDK chỉ tin loopback ⇒ client ở xa nhận `421 Misdirected Request`. **Nới
  allowlist, đừng tắt bảo vệ** (tắt là mở cho web bất kỳ tấn công server nội
  bộ). Allowlist gồm: loopback, địa chỉ LAN thật, và mọi `--allow-host` truyền
  vào. Với MỖI host phải chấp nhận cả dạng có `:port` lẫn dạng trần — proxy ở
  cổng mặc định gửi Host không kèm cổng. Origin phải cho cả `http` lẫn `https`
  (proxy có thể kết thúc TLS ở phía trước). Địa chỉ bind rỗng (`0.0.0.0`,
  `::`) KHÔNG phải là một địa chỉ client tới, đừng đưa vào allowlist.
- `--cors-origin` cho client trình duyệt: SDK không sinh phản hồi CORS, trả
  `OPTIONS` = 405 nên trình duyệt chặn và JS chỉ thấy "Failed to fetch". Bọc
  Starlette app bằng `CORSMiddleware`, và **BẮT BUỘC** `expose_headers` có
  `Mcp-Session-Id` — trình duyệt không đọc được header không được lộ ra, nên
  không nối tiếp được phiên.
- `--json-response` và `--stateless` cho client khắt khe.

### Service script

`install / remove / start / stop / restart / status / logs`, mặc định MCP 8765,
audio 8766.

- `install` phải dùng `systemctl restart` TƯỜNG MINH. `enable --now` KHÔNG
  khởi động lại service đang chạy: tiến trình cũ sống tiếp với dòng lệnh cũ,
  và cài lại trông như không có tác dụng gì. Lần đầu gặp lỗi này nó sống 3
  ngày.
- `status` phải in dòng lệnh THẬT của tiến trình đang chạy, đọc từ
  `/proc/<MainPID>/cmdline`. File unit có thể đã khác với thứ đang chạy.
- In ra lệnh mở tường lửa cho **cả hai** cổng. Thiếu cổng audio thì cast vẫn
  "thành công" và loa im lặng — màn hình nháy sáng rồi tắt.

## Bài kiểm

Viết bộ eval chia **ba tầng theo tác dụng phụ**: mặc định không chạm gì (thay
thế hết mạng và thiết bị), `--online` gọi TTS thật, `--hardware` cast ra loa
thật và phải xin phép mỗi lần.

Kèm một kịch bản **kiểm ngược**: gieo từng lỗi đã biết vào một BẢN SAO của mã
trong thư mục tạm, rồi đòi bài kiểm phải đỏ đúng những mục đã ghi TRƯỚC khi
gieo; kèm ít nhất một đối chứng vô hại kỳ vọng vẫn xanh. Báo cáo phải in "đã
chạy X/Y mục đăng ký" và coi X<Y là hỏng toàn cục.

## Tài liệu

`README.md` (cài + chạy + sự cố) và `docs/architecture.md` (vì sao mỗi mảnh
tồn tại, và cái gì cắn trong vận hành).
````

---

## Những chỗ prompt trên KHÔNG thay được người

| Việc | Vì sao máy không tự làm được |
|---|---|
| Nghe giọng có tự nhiên không | tiêu chí cảm nhận. Phải người nghe |
| Xác nhận loa thật sự phát ra tiếng | cast "thành công" mà im lặng là chuyện bình thường |
| Phát hiện chồng luồng lên một loa vật lý | kết quả API không phân biệt được; chỉ nghe mới biết |
| Cấp quyền `sudo`, mở tường lửa, tạo tên miền, cấp chứng chỉ | ngoài tầm với của agent |
| Quyết định phơi ra internet hay không | quyết định về rủi ro, thuộc về chủ nhà |

## Nếu môi trường khác đi

- **Không có thiết bị Cast thật**: dựng được và chạy được tầng eval mặc định
  cùng `--online`, nhưng **không nghiệm thu được**. Ghi rõ là chưa nghiệm thu,
  đừng ghi là xong.
- **Máy chạy trong container mạng bridge hoặc VM NAT**: mDNS không qua được và
  loa không mở được kết nối ngược về. Phải dùng mạng host.
- **Không dùng tiếng Việt**: đổi tên giọng edge-tts; phần còn lại giữ nguyên.
- **Chỉ chạy stdio cùng máy**: bỏ được toàn bộ phần allowlist, CORS, service,
  nginx. Nhưng HTTP file server thì **không bỏ được** — nó là ràng buộc từ
  phía thiết bị, không phải từ phía client.
