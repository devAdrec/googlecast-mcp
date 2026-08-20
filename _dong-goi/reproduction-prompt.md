# Reproduction prompt — dựng lại googlecast-mcp từ đầu

Dán phần trong khung dưới đây cho một trợ lý AI có quyền đọc/ghi file và chạy
lệnh, trên một máy Linux **cùng LAN với loa Google Cast**.

Đây là prompt để dựng lại **đúng sản phẩm này**. Muốn học cách nghĩ để xây một
sản phẩm khác thì đọc `method-note.md`. Muốn cài bản đã có sẵn thì đọc
`package/README.md`.

---

## Prompt

> Hãy xây một MCP server bằng Python đáp ứng đúng ba yêu cầu sau. Ba yêu cầu này
> là đặc tả duy nhất; hãy đối chiếu từng dòng khi báo cáo tiến độ.
>
> 1. Dò danh sách các Google speaker trong mạng nội bộ, sau đó lưu lại.
> 2. Nhận tin nhắn dạng text làm tham số của tool, chuyển thành âm thanh (hỗ trợ
>    tiếng Việt), rồi phát lên speaker theo yêu cầu.
> 3. Nếu người dùng không chọn speaker thì phải hỏi lại xem phát ở speaker nào,
>    hoặc tất cả.
>
> ### Ràng buộc kiến trúc — đã kiểm chứng, đừng thiết kế lại
>
> - Dùng MCP Python SDK chính thức (FastMCP) và **ghim `mcp[cli]>=1.13,<2`**.
>   Trên PyPI có một gói tên `mcp` phiên bản 2.0.0 hoàn toàn không liên quan,
>   layout khác, kéo theo `httpx2` và `mcp-types`. Ghim là bắt buộc.
> - Dùng `pychromecast` để nói chuyện với thiết bị. Không cần so sánh phương án:
>   đây là thư viện Python duy nhất còn được bảo trì cho giao thức Cast.
> - Dùng `edge-tts` cho tiếng Việt (`vi-VN-HoaiMyNeural` nữ,
>   `vi-VN-NamMinhNeural` nam). Không cần khoá API.
> - **Thiết bị Cast tự đi tải media qua HTTP**; nó không đọc được đường dẫn file
>   trên máy bạn. Vì vậy server bắt buộc kiêm luôn một HTTP file server phục vụ
>   thư mục cache mp3. Bind nó trên **mọi interface (`0.0.0.0`)**, nhưng URL
>   quảng bá cho thiết bị thì dựng từ **địa chỉ LAN** của máy — hai thứ này khác
>   nhau, đừng gộp làm một.
> - `pychromecast` là thư viện blocking. Mọi tool phải đẩy lời gọi sang worker
>   thread (`asyncio.to_thread`) để không chặn event loop của MCP.
> - Lưu bền danh sách thiết bị ra `~/.googlecast-mcp/speakers.json`, ghi theo
>   kiểu write-then-rename, **merge theo `uuid` chứ không thay thế** (mDNS lossy;
>   một lần quét sót không được xoá mất thiết bị đang ngủ).
>
> ### Hành vi bắt buộc
>
> - Lọc loa (`cast_type` là `audio` hoặc `group`) khỏi thiết bị hình ảnh
>   (`cast`).
> - **Thiếu tham số chọn loa thì KHÔNG phát gì cả**: không tổng hợp giọng, không
>   gửi tới thiết bị. Trả về dữ liệu có cấu trúc (`status`,
>   `needs_speaker_selection`, danh sách loa, một câu hướng dẫn) để chính mô hình
>   gọi tool hỏi lại người dùng. **Không dùng MCP elicitation** (nhiều client
>   chưa hỗ trợ) và **không mặc định phát ra tất cả** (tác dụng phụ vật lý).
> - Không có loa nào trong mạng thì trả một trạng thái khác hẳn
>   (`no_speakers_found`) với thông điệp hành động được.
> - Chấp nhận: một tên, nhiều tên cách phẩy, `all` / `tất cả` / `tat ca`.
> - **`all` phải LOẠI nhóm loa ra**, chỉ gửi tới từng loa lẻ. Nhóm Cast phát
>   thông qua chính các thành viên của nó, nên gửi tới cả hai sẽ đẩy hai luồng
>   vào cùng một loa vật lý — và cả bốn thiết bị vẫn báo `playing`, API không
>   phát hiện được, chỉ nghe mới biết. Nhóm vẫn phải gọi được bằng tên đích danh.
> - Một loa hỏng không được kéo theo các loa khác: bọc riêng từng lần cast, trả
>   lỗi cho riêng loa đó, kết quả tổng thể vẫn `ok` nếu còn loa nào phát được.
> - Text rỗng hoặc chỉ có khoảng trắng → `ValueError`, trước mọi tác dụng phụ.
> - Nối lại thiết bị theo ba nấc: cache trong RAM → nối thẳng bằng địa chỉ đã
>   lưu → quét lại mDNS. Nấc giữa là bắt buộc: thiếu nó, một lần mDNS sót thiết
>   bị sẽ sinh ra lỗi "không tìm thấy" tự mâu thuẫn (liệt kê chính thiết bị đó
>   là đã biết).
>
> ### Bộ tool
>
> 13 tool: `say`, `discover_devices`, `list_speakers`, `list_devices`,
> `get_status`, `play_media`, `play`, `pause`, `stop`, `seek`, `set_volume`,
> `set_muted`, `quit_app`. Mỗi tool phải có docstring — đó là toàn bộ ngữ cảnh
> mà mô hình gọi tool có được.
>
> ### Triển khai
>
> Viết một script quản lý systemd (`install`/`remove`/`start`/`stop`/`restart`/
> `status`/`logs`) và một file cấu hình nginx reverse proxy mẫu. Bốn chi tiết
> dưới đây đều xuất phát từ sự cố thật, đừng bỏ:
>
> 1. SDK có bảo vệ chống DNS-rebinding, mặc định chỉ tin loopback; client từ xa
>    nhận **421**. **Nới allowlist, đừng tắt bảo vệ.** Allowlist phải chứa cả
>    **host trần không kèm `:port`** (proxy ở cổng 443 gửi Host không có port) và
>    cả **scheme `https`** (proxy kết thúc TLS). Thêm cờ `--allow-host` lặp được.
> 2. Client chạy trong trình duyệt cần CORS: SDK trả `OPTIONS` = 405 không
>    header, trình duyệt chặn và JS chỉ thấy `Failed to fetch`. Bọc
>    `streamable_http_app()` bằng `CORSMiddleware`, **bắt buộc**
>    `expose_headers=["Mcp-Session-Id"]` — không expose thì trình duyệt không duy
>    trì được session dù preflight đã qua. Thêm cờ `--cors-origin` lặp được.
> 3. Thêm `--json-response` và `--stateless` cho client khắt khe.
> 4. Trong nginx: **`proxy_buffering off;`** (thiếu thì client treo im lặng,
>    không báo lỗi gì) và `proxy_read_timeout 3600s;`.
>
> Script `install` phải dùng `systemctl restart` tường minh, **không dùng
> `enable --now`** — lệnh đó không restart service đang chạy, nên tiến trình cũ
> sẽ tiếp tục chạy code và tham số cũ mà không ai biết. Lệnh `status` phải in ra
> **dòng lệnh thật của tiến trình đang chạy** (`/proc/<MainPID>/cmdline`), không
> chỉ đọc unit file trên đĩa.
>
> Ghim cổng phục vụ audio qua biến môi trường (mặc định service: MCP 8765, audio
> 8766) để chỉ phải viết một luật tường lửa. Nhắc người cài mở **cả hai** cổng
> cho LAN.
>
> ### Bộ eval — làm cùng lúc với code, không để sau
>
> Viết một script eval in pass/fail từng mục, exit 0/1, **chia ba tầng theo tác
> dụng phụ**:
>
> - **mặc định**: offline hoàn toàn. Không mạng, không tiếng, không cần loa.
>   Phải chạy được ở mọi máy vào bất cứ lúc nào.
> - `--online`: thêm kiểm tổng hợp giọng nói (cần internet, vẫn im lặng).
> - `--hardware`: mới cast thật ra loa. **Phải là opt-in, không bao giờ mặc
>   định** — nó phát tiếng trong nhà người ta.
>
> Tầng offline phải phủ: import được; đúng 13 tool; thiếu tham số chọn loa →
> `needs_speaker_selection` **và chứng minh được là KHÔNG tổng hợp giọng, KHÔNG
> cast** (dùng spy rồi khẳng định spy rỗng); `all` không chứa nhóm nhưng nhóm vẫn
> gọi được bằng tên; nhiều loa cách phẩy; cô lập lỗi khi một loa hỏng; lọc loa vs
> thiết bị hình ảnh; đoán MIME type; chọn giọng; allowlist có cả `https` lẫn host
> trần; text rỗng raise `ValueError`.
>
> Trong fixture, hãy để một nhóm loa và một loa thành viên **cùng địa chỉ host** —
> đó chính là cấu hình đã làm lỗi chồng luồng nghe thấy được.
>
> **Cuối cùng, hãy kiểm ngược bộ eval**: đưa lỗi `all`-gồm-cả-nhóm trở lại, chạy
> eval, xác nhận nó **đỏ đúng các mục về `all`** (không đỏ lan sang mục khác),
> rồi khôi phục và xác nhận xanh lại. Ghi quy trình và kết quả vào README của
> eval. Một bộ eval chưa từng đỏ thì chưa chứng minh được gì.
>
> ### Tài liệu
>
> README ở gốc: cài, chạy, cấu hình client, danh sách tool, bảng troubleshooting.
> `docs/architecture.md`: luồng xử lý, module, mô hình luồng, mô hình bảo mật.
>
> Nói thẳng trong tài liệu về phần còn hở: **không có xác thực ở tầng ứng
> dụng**, và cổng phục vụ audio là mặt phơi nhiễm thứ hai (bind mọi interface,
> không xác thực, phục vụ nguyên thư mục cache) mà biện pháp chặn IP ở nginx
> không che được.

---

## Hai điều prompt này KHÔNG thay thế được

1. **Chọn giọng đọc.** Prompt ghi thẳng kết quả (edge-tts) để dựng lại nhanh.
   Nhưng nếu bạn làm sản phẩm cho người khác, tiêu chí "nghe có tự nhiên không"
   **phải để chính họ nghe rồi chọn** — xem `method-note.md` bước 2.
2. **Xác nhận bằng tai.** Không có mục eval nào chứng minh được âm thanh phát ra
   đúng và đủ. Phải có người nghe. Xem `method-note.md` bước 5.

## Điều kiện tiên quyết

Máy dựng phải **cùng LAN với loa** (mDNS + loa quay lại tải file), phải **có
internet** (edge-tts là dịch vụ online), Python ≥ 3.11, và cần ít nhất một loa
Google Cast đang bật để kiểm tầng `--hardware`.
