# Ràng buộc triển khai

**Kiến trúc, luồng request, mô-đun, mô hình luồng (threading), phân giải thiết bị:
đọc `docs/architecture.md`.** File này KHÔNG chép lại nội dung đó — nó chỉ ghi những
ràng buộc chỉ lộ ra khi đem product ra khỏi máy phát triển: cổng, allowlist, CORS, DNS.

## Ràng buộc gốc, quyết định mọi thứ còn lại

**Thiết bị Cast tự đi tải media qua HTTP.** Bạn không đưa cho nó một đường dẫn file;
bạn đưa cho nó một URL và nó tự kết nối ngược lại. Hệ quả không né được: một server
"nói được" bắt buộc phải kiêm luôn HTTP file server. Đó là lý do có `media_server.py`,
là lý do có cổng thứ hai, và là lý do phần lớn lỗi trong product này là lỗi mạng chứ
không phải lỗi logic.

Chính xác về chỗ hay bị viết nhầm: `media_server.py:76` bind **`0.0.0.0`** (mọi
interface). URL quảng bá cho thiết bị thì dựng từ `lan_ip()`. **Hai thứ khác nhau** —
địa chỉ lắng nghe không phải địa chỉ quảng bá. Bind rộng vì interface định tuyến ra
ngoài chưa chắc là interface loa dùng để gọi về.

## Cổng

| Cổng | Ai nghe | Ai gọi tới | Có xác thực? |
|---|---|---|---|
| 8765 | endpoint MCP (`--port`) | MCP client (Claude Desktop, llama-server webui) | Không |
| 8766 | HTTP audio (`--media-port`) | **loa Google**, gọi ngược về máy chủ | Không |

Ghim cổng audio (mặc định là cổng ngẫu nhiên) để chỉ phải viết một luật tường lửa.

**Điều dễ hiểu lầm nhất về bảo mật ở đây:** chặn IP trong nginx **chỉ che 8765**.
Cổng 8766 không đi qua nginx. Nó bind `0.0.0.0`, không xác thực, và phục vụ nguyên
một thư mục file. Muốn đóng thật thì đóng ở tường lửa máy chủ.

Trong `scripts/nginx-googlecast-mcp.conf:55-56` có sẵn hai dòng
`allow 192.168.0.0/16; deny all;` — người dùng đã đồng ý bật nhưng **hiện vẫn đang
comment**. Chưa bật.

## Allowlist: vì sao có 421 Misdirected Request

MCP SDK có bảo vệ chống DNS-rebinding và **chỉ tin `127.0.0.1`**. Bind `0.0.0.0`
KHÔNG đủ — bind là chuyện nghe, allowlist là chuyện tin. Client ở máy khác sẽ ăn 421.

Lựa chọn ở đây là **nới allowlist, không tắt bảo vệ**. Tắt là mở cửa cho một trang web
bất kỳ mà nạn nhân đang mở sai khiến server nội bộ của họ.

`__main__.py:46-69` dựng allowlist gồm loopback, IP LAN, và mọi `--allow-host`. Hai
chi tiết nhỏ mà thiếu là hỏng:

- Phải có host **KHÔNG kèm `:port`**. Trang ở cổng 443 gửi header Host không có port.
- Phải có scheme **`https`**, vì reverse proxy đổi scheme.

Cả hai được eval khoá lại (mục `allowed_hosts` / `allowed_origins`), chính vì cả hai
đều từng bị thiếu.

## CORS: vì sao trình duyệt chỉ báo "Failed to fetch"

SDK không sinh phản hồi CORS. Với client chạy trong trình duyệt, preflight `OPTIONS`
nhận **405** không kèm header nào; trình duyệt chặn, và JavaScript **chỉ thấy một lỗi
trống rỗng** — không có mã, không có nội dung. Triệu chứng không hề trỏ về nguyên nhân.

`--cors-origin` bọc `streamable_http_app()` bằng `CORSMiddleware` (`__main__.py:37`).

**`expose_headers=["Mcp-Session-Id"]` là BẮT BUỘC.** Trình duyệt không đọc được header
không được expose, nên không giữ được session, nên không tiếp tục được — dù preflight
đã qua. Đây là một lỗi thứ hai nằm ngay sau lỗi thứ nhất.

Origin phải khớp **chính xác** thanh địa chỉ. Trang ở cổng 80/443 gửi origin không kèm
port.

## DNS và chứng chỉ

**Hostname chứa dấu gạch dưới không bao giờ xin được chứng chỉ.** CA/B Forum cấm `_`.
Gặp một client chỉ nhận https (Claude Desktop custom connector) thì đây là ngõ cụt
tuyệt đối — không có cách vòng, chỉ có đổi tên miền. `google_cast.…` → `google-cast.…`.

## nginx

`proxy_buffering off` + `proxy_read_timeout 3600s`
(`scripts/nginx-googlecast-mcp.conf:37,42`). Thiếu, nginx giữ lại dòng sự kiện và
client **treo im lặng, không báo lỗi gì cả**. Không có thông báo nào để tra cứu.

## Client khắt khe

`--json-response` trả JSON thay vì khung SSE `event: message`; `--stateless` bỏ yêu
cầu client mang `Mcp-Session-Id` giữa các request. Dùng cho client không parse được
SSE hoặc bỏ qua header session (ví dụ llama-server webui).

## Mã trả về, đọc đúng thì đỡ mất thời gian

| Mã | Nguyên nhân | Ghi chú |
|---|---|---|
| 406 | client không nhận `text/event-stream` | **Đúng đặc tả, không phải lỗi.** Mở `/mcp` bằng trình duyệt luôn ra thế này. |
| 421 | Host ngoài allowlist | `--allow-host` |
| 403 `Invalid Origin header` | origin ngoài allowlist | `--cors-origin` |
| 405 cho `OPTIONS` | chưa bật CORS | `--cors-origin` |

## Thiết bị treo: kiểm mạng trước khi nghi mã nguồn

Có trường hợp mDNS thấy thiết bị, ping thông, nhưng **TCP 8009 bị từ chối** →
`wait timed out after 10 s`. Khởi động lại thiết bị là hết. Luôn chạy
`nc -z <ip> 8009` TRƯỚC khi đọc mã nguồn.

**Một bài học suy luận đắt hơn bản thân lỗi:** đã có lúc kết luận "Nest Hub bỏ cổng
8009 do firmware", chỉ vì cả HAI Nest Hub trong nhà cùng đóng cổng. Hai mẫu trùng nhau
không đủ để suy ra nguyên nhân hệ thống. Kết luận đó sai, và nó suýt làm ngừng việc
tìm nguyên nhân thật.

## mDNS sót thiết bị đã lưu

Khi quét sót một thiết bị đang có trong store, lỗi `DeviceNotFoundError` **tự mâu
thuẫn**: nó liệt kê chính thiết bị đó trong danh sách "known". Thông báo lỗi tự mâu
thuẫn là dấu hiệu hai nguồn sự thật đang lệch nhau, không phải dấu hiệu code sai chỗ
ném lỗi. `_connect_saved()` (`cast_manager.py:110,124,134`) nối thẳng bằng host/port
đã lưu.

## Vận hành

- `systemctl enable --now` **không** khởi động lại service đang chạy. Tiến trình cũ
  giữ nguyên mã và tham số cũ. Ở đây một tiến trình cũ đã sống 3 ngày.
  `service.sh status` in `/proc/<MainPID>/cmdline` — đọc dòng đó, đừng tin
  `active (running)`.
- `pkill -f "<pattern>"` khớp luôn chính dòng lệnh bash đang chạy nó → tự giết shell
  (exit 144). Lấy PID từ `ss -ltnp`.

## Chưa kiểm chứng

- Service sống sót qua reboot (đã `enable`, **chưa reboot lần nào**).
- Địa chỉ đã lưu bị cũ vì thiết bị đổi IP → nhánh quét lại: **chưa thử**.
