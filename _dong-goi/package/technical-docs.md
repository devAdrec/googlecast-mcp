# Ràng buộc triển khai

Kiến trúc bên trong (luồng xử lý, mô hình luồng, cách phân giải thiết bị) nằm ở
**`docs/architecture.md`** ở gốc repo. Đó là tài liệu đang sống — đọc nó, đừng
đọc bản chép.

File này chỉ ghi những ràng buộc **khi đem đi triển khai**: cổng, allowlist,
CORS, DNS. Đây là phần đắt nhất của cả dự án: gần như mọi ngày chật vật đều nằm
ở tầng mạng, không phải ở logic.

---

## 1. Cổng

| Cổng | Ai nghe | Ai gọi tới | Bind |
|---|---|---|---|
| 8765 | MCP endpoint (`/mcp`) | client MCP (Claude Desktop, webui, nginx) | `0.0.0.0` |
| 8766 | HTTP phục vụ file mp3 | **chính cái loa** | `0.0.0.0` |

Điều dễ bỏ sót nhất trong cả product: **thiết bị Cast tự đi tải media qua HTTP**.
Nó không đọc được đường dẫn file trên máy bạn. Vì vậy một server "biết nói" bắt
buộc phải kiêm luôn một HTTP file server. Chặn 8766 là mất tiếng, dù MCP vẫn
xanh.

Ghim cổng media (`--media-port` hoặc `GOOGLECAST_MCP_MEDIA_PORT`) khi có tường
lửa, để chỉ phải viết một luật:

```bash
sudo ufw allow from 192.168.0.0/16 to any port 8765 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 8766 proto tcp
```

**Bind và địa chỉ quảng bá là hai thứ khác nhau.** `media_server.py:76` bind
`0.0.0.0`; còn URL đưa cho loa thì dựng từ `lan_ip()`. Nhầm hai thứ này là ra
một URL mà loa không tới được, trong khi `netstat` trông vẫn hoàn hảo.

## 2. Allowlist chống DNS-rebinding

SDK MCP mặc định **chỉ tin `127.0.0.1`**. Bind `0.0.0.0` **không** đủ: client ở
máy khác vẫn ăn `421 Misdirected Request`.

Cách xử lý (`__main__.py:46-69`) là **nới**, không phải tắt. Tắt là mở cho một
trang web bất kỳ trong trình duyệt của bạn tấn công server nội bộ.

Hai chi tiết mà thiếu là hỏng, và cả hai đều có test riêng:

- **Có cả scheme `https`.** Reverse proxy kết thúc TLS rồi chuyển tiếp bằng
  http, nhưng `Origin` client gửi vẫn là `https://…`.
- **Có cả host KHÔNG kèm `:port`.** Proxy chạy ở cổng 443 thì trình duyệt gửi
  header `Host` trần, không có `:443`.

Thêm tên miền bằng `--allow-host google-cast.adrec.cloud` (lặp lại được).

## 3. CORS cho client chạy trong trình duyệt

Triệu chứng: `Failed to fetch (check CORS?)` và **không có gì khác**. SDK trả
`OPTIONS` = **405** không kèm header CORS, trình duyệt chặn ở preflight, JS chỉ
thấy một lỗi rỗng — không có gì để lần theo.

Bật bằng `--cors-origin <origin>`, origin phải **khớp chính xác** thanh địa chỉ
(scheme + host + port).

Bắt buộc phải có `expose_headers=["Mcp-Session-Id"]` (`__main__.py:37`): trình
duyệt không đọc được header đó nếu không expose, nên không giữ nổi phiên, dù
`initialize` vẫn trả 200. Một dòng thiếu ở đây trông y hệt "server hỏng".

Client khắt khe còn cần thêm:

- `--json-response` — client không phân tích nổi khung SSE `event: message`.
- `--stateless` — client không mang `Mcp-Session-Id` giữa các request.

## 4. Reverse proxy và TLS

Vhost mẫu: `scripts/nginx-googlecast-mcp.conf`.

- **`proxy_buffering off`** — bắt buộc. Bật buffering thì client **treo im
  lặng**, không lỗi, không log gì. Đây là kiểu hỏng tệ nhất trong cả dự án.
- **`proxy_read_timeout 3600s`** — SSE là kết nối dài.
- **Tên miền tuyệt đối không được có dấu gạch dưới.** CA/B Forum cấm `_`, nên
  `google_cast.adrec.cloud` sẽ **không bao giờ** xin được chứng chỉ. Claude
  Desktop lại chỉ nhận `https`. Hai điều đó cộng lại thành ngõ cụt tuyệt đối,
  không có cách vòng. Đổi tên miền là con đường duy nhất.

## 5. Đăng ký phía client — bảng tra nhanh

| Client | Ở đâu | Cách nối |
|---|---|---|
| Claude Code | cùng máy | stdio: `claude mcp add --scope user googlecast -- uv run --directory <repo> googlecast-mcp` |
| Claude Desktop | máy khác, chưa có TLS | cầu nối `npx -y mcp-remote http://<ip>:8765/mcp --allow-http` |
| Claude Desktop | máy khác, đã có TLS | custom connector `https://<domain>/mcp` |
| llama-server webui | trong trình duyệt | HTTP + `--cors-origin` khớp chính xác |

## 6. Triển khai hiện tại

- systemd `googlecast-mcp.service` trên `192.168.1.128`
- nginx vhost `/etc/nginx/conf.d/adrec_cloud.conf`, chứng chỉ Let's Encrypt
- Phục vụ Claude Desktop ở `192.168.1.28` (https) và llama-server webui ở
  `192.168.1.99:8383` (LAN + CORS)

Dòng lệnh đang chạy:

```bash
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud --json-response --stateless --cors-origin http://192.168.1.99:8383" \
  ./scripts/service.sh install
```

## 7. Bảng đọc mã lỗi

| Thấy gì | Nghĩa là gì |
|---|---|
| `421 Misdirected Request` | host không nằm trong allowlist → thêm `--allow-host` |
| `403 Invalid Origin header` | origin không nằm trong allowlist |
| `406 Not Acceptable` | client thiếu `Accept: text/event-stream`. Mở `/mcp` bằng trình duyệt cũng ra 406 — **đúng đặc tả, không phải lỗi** |
| `405` cho `OPTIONS`, không header CORS | chưa bật `--cors-origin` |
| `Failed to fetch (check CORS?)` | như trên; trình duyệt không nói gì thêm |
| client treo, không lỗi, không log | nginx đang buffering |
| `wait timed out` khi cast | thiết bị treo. Kiểm `nc -z <ip> 8009` **trước khi** nghi mã nguồn |
| sửa xong mà "vẫn lỗi" y hệt | tiến trình cũ chưa được nạp lại. `./scripts/service.sh status` và đọc dòng `/proc/<pid>/cmdline` |

## 8. Chỗ còn hở, biết rõ và chưa vá

- **Không có xác thực ở tầng ứng dụng.** Ai tới được endpoint là điều khiển
  được loa. `google-cast.adrec.cloud` phân giải công khai ra internet.
- **8766 không xác thực**, phục vụ nguyên thư mục cache TTS. Chặn IP ở nginx
  chỉ che 8765 — 8766 vẫn hở.
- Hai dòng chặn IP trong vhost nginx **đã bàn nhưng vẫn đang comment**, chưa bật.
- Cache TTS chỉ tăng, chưa có dọn.
