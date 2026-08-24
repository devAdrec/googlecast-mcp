# Ràng buộc triển khai

Kiến trúc, luồng xử lý và vai trò từng module nằm ở **`docs/architecture.md`**
trong repo. Trang này không chép lại, chỉ ghi những ràng buộc mà người triển
khai buộc phải biết mới dựng lại được hệ thống — phần dễ sai nhất, và phần
`docs/architecture.md` không nói.

## Ràng buộc gốc, quyết định mọi thứ còn lại

Thiết bị Cast **tự đi tải media qua HTTP**. Nó không đọc được đường dẫn file
trên máy bạn. Vì vậy một server "nói được" bắt buộc phải kiêm luôn một HTTP
file server mà loa với tới được. Mọi rắc rối về cổng, bind, tường lửa và bảo
mật dưới đây đều mọc ra từ câu đó.

Hệ quả trực tiếp, và là chỗ hay nhầm: `media_server.py:76` bind `0.0.0.0`
(nghe mọi giao diện), còn URL quảng bá cho loa dựng từ `lan_ip()`. **Hai thứ
khác nhau.** Bind rộng để loa nào cũng tới được; URL phải là một địa chỉ cụ
thể vì loa cần một địa chỉ để gọi.

## Cổng

| Cổng | Là gì | Bind | Ra internet được không |
|---|---|---|---|
| 8765 | MCP streamable HTTP | `0.0.0.0` | có, qua nginx + TLS |
| 8766 | Server phát file mp3 cho loa | `0.0.0.0` | **không** — chỉ LAN |

Cổng 8766 phải cố định (`--media-port` hoặc `GOOGLECAST_MCP_MEDIA_PORT`) khi
chạy như service. Mặc định là cổng ngẫu nhiên, tiện khi chạy tay nhưng không
viết được luật tường lửa.

Đừng bao giờ proxy 8766. Loa phải lấy file trực tiếp từ LAN.

## Allowlist — bảo vệ DNS-rebinding

SDK MCP chỉ tin `127.0.0.1`. Bind `0.0.0.0` **không** đủ: client từ máy khác
sẽ nhận `421 Misdirected Request`. Cách xử lý là **nới allowlist, không tắt
bảo vệ** — tắt là mở cửa cho một trang web bất kỳ tấn công server nội bộ qua
trình duyệt của bạn.

`__main__.py:46-69` (`_transport_security`) sinh allowlist. Hai chi tiết phải
giữ, cả hai đều từng làm hỏng và cả hai đều có test riêng:

1. **Host trần, không kèm `:port`.** Một reverse proxy chạy ở cổng 443 gửi
   header `Host: google-cast.adrec.cloud`, không có phần cổng. Nếu allowlist
   chỉ có `<host>:*` thì mọi request qua proxy đều 421.
2. **Cả scheme `https`.** TLS kết thúc ở nginx, nhưng origin trình duyệt gửi
   lên vẫn là `https://...`.

Thêm tên miền bằng `--allow-host <domain>` (lặp lại được). Loopback và địa chỉ
LAN của máy luôn được cho phép.

## CORS — chỉ khi client chạy trong trình duyệt

SDK không sinh phản hồi CORS: `OPTIONS` trả **405 không kèm header nào**, nên
trình duyệt chặn, và JavaScript chỉ thấy `Failed to fetch (check CORS?)` — một
lỗi rỗng không nói gì. `--cors-origin <origin>` bọc app Starlette bằng
`CORSMiddleware`.

**Bắt buộc `expose_headers=["Mcp-Session-Id"]`** (`__main__.py:37`). Trình
duyệt không đọc được header đó nếu không expose, nên không giữ được phiên, và
triệu chứng lại trông giống hệt một lỗi CORS khác.

Origin phải **khớp chính xác thanh địa chỉ**, kể cả cổng:
`http://192.168.1.99:8383`, không phải `http://192.168.1.99`.

## Client khắt khe hơn đặc tả

| Cờ | Khi nào cần |
|---|---|
| `--json-response` | Client không phân tích được khung SSE `event: message` |
| `--stateless` | Client bỏ qua header `Mcp-Session-Id` giữa các request |

Client nào đúng đặc tả thì không cần cả hai.

## Reverse proxy và DNS

`scripts/nginx-googlecast-mcp.conf` là bản dùng được. Bốn điểm chết người:

1. **`proxy_buffering off`.** Streamable HTTP giữ một phản hồi mở lâu và đẩy
   sự kiện dần. Nginx đệm lại thì client **treo im, không báo lỗi gì** — rất
   khó chẩn đoán vì không có thông báo nào để tìm.
2. **`proxy_read_timeout 3600s`.** Phiên MCP rỗi không được cắt giữa chừng.
3. **Hostname không được có gạch dưới.** CA/B Forum cấm `_` trong tên miền,
   nên `google_cast.adrec.cloud` **không bao giờ** xin được chứng chỉ. Mà
   Claude Desktop chỉ nhận https ⇒ ngõ cụt tuyệt đối, không có cách vòng.
   Phải đổi sang `google-cast.adrec.cloud`.
4. **Chỉ proxy 8765.** 8766 ở lại LAN.

Đổi tên miền thì phải đồng thời thêm `--allow-host <tên mới>`, nếu không mọi
request qua proxy trả 421.

## Bắc cầu cho Claude Desktop

Ô "custom connector" của Claude Desktop chỉ nhận `https`. Một server LAN chạy
http không điền vào đó được. Bắc cầu trong `claude_desktop_config.json`:

```json
{"mcpServers":{"googlecast":{"command":"npx",
 "args":["-y","mcp-remote","http://192.168.1.128:8765/mcp","--allow-http"]}}}
```

## Bảo mật — nói thẳng

- **Không có xác thực ở tầng ứng dụng.** Ai gọi được `/mcp` là phát được tiếng
  trong nhà.
- `google-cast.adrec.cloud` **phân giải công khai ra internet**. Hai dòng
  `allow 192.168.0.0/16; deny all;` trong file nginx đã đồng ý bật nhưng vẫn
  đang comment.
- Cổng 8766 phục vụ nguyên thư mục cache TTS, không xác thực, và chặn IP ở
  nginx **không che nó** — nó không đi qua nginx.
- Bảo vệ DNS-rebinding của SDK vẫn bật. Đừng tắt.

## Triển khai đang chạy thật

- systemd `googlecast-mcp.service` trên `192.168.1.128`, MCP 8765, audio 8766.
- nginx vhost `/etc/nginx/conf.d/adrec_cloud.conf`, chứng chỉ Let's Encrypt.
- Phục vụ Claude Desktop (máy `.28`) qua https, và llama-server webui
  (`192.168.1.99:8383`) qua CORS.

```bash
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud --json-response --stateless --cors-origin http://192.168.1.99:8383" \
    ./scripts/service.sh install
```

## Chẩn đoán theo mã lỗi

| Thấy gì | Nghĩa là gì |
|---|---|
| `421 Misdirected Request` | Host client dùng chưa có trong allowlist → `--allow-host` |
| `403` | Origin chưa được phép → `--cors-origin` |
| `406 Not Acceptable` | Thiếu `Accept: text/event-stream`. Mở bằng trình duyệt ra lỗi này là **đúng**, không phải hỏng |
| `405` ở preflight, không header | Chưa bật CORS |
| Client treo, không lỗi | Nginx đang đệm → `proxy_buffering off` |
| `Failed to fetch (check CORS?)` | Có thể là CORS, cũng có thể do thiếu `expose_headers` |
| `wait timed out` khi cast | Thiết bị treo. Kiểm `nc -z <ip> 8009` **trước** khi nghi mã nguồn |
| Sửa rồi mà vẫn y nguyên | Tiến trình cũ còn sống. `service.sh status` xem `/proc/<pid>/cmdline` |
