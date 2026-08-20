# Ghi chú kỹ thuật — ràng buộc triển khai

**Kiến trúc, luồng xử lý, mô hình luồng, mô hình bảo mật: đọc
`docs/architecture.md` ở gốc repo.** File này KHÔNG chép lại nội dung đó. Nó chỉ
ghi những ràng buộc khi đem product ra chạy thật — thứ mà tài liệu kiến trúc
không mô tả và người cài hay vấp.

## Ràng buộc kiến trúc gốc, không né được

Thiết bị Cast **tự đi tải media qua HTTP**; nó không đọc được đường dẫn file
trên máy bạn. Hệ quả: một server "biết nói" bắt buộc phải kiêm luôn một HTTP
file server. Đó là lý do có hai cổng, chứ không phải lựa chọn thiết kế tuỳ ý.

Nói chính xác về chỗ này, vì rất dễ viết nhầm:

- `media_server.py:76` bind `("0.0.0.0", port)` — **mọi interface**.
- URL quảng bá cho thiết bị được dựng từ `lan_ip()` (`media_server.py:19-32`),
  là địa chỉ LAN mà loa nhìn thấy.

Hai thứ này KHÁC NHAU. Bind mọi interface vì interface định tuyến không nhất
thiết là interface loa dùng để quay lại.

## Cổng

| Cổng | Ai gọi | Bind | Xác thực |
|---|---|---|---|
| 8765 | MCP client (Claude Desktop, webui, …) | `0.0.0.0` | không |
| 8766 | **Loa** quay lại tải file mp3 | `0.0.0.0` | không |

8766 mặc định là cổng ngẫu nhiên; service ghim nó qua
`GOOGLECAST_MCP_MEDIA_PORT` để chỉ phải viết một luật tường lửa. Cả hai cổng
phải mở cho LAN, nếu không loa không tải được file và bạn sẽ thấy loa nháy đèn
rồi tắt.

## Allowlist — vì sao lại phức tạp đến vậy

SDK có sẵn bảo vệ chống DNS-rebinding: mặc định chỉ tin `127.0.0.1`. Bind
`0.0.0.0` **không** làm nó tin thêm ai; client từ xa nhận **421 Misdirected
Request**. Quyết định: **giữ bảo vệ, chỉ nới allowlist** — tắt hẳn là mở cửa cho
trang web bất kỳ tấn công server trong mạng nội bộ của bạn.

`__main__.py:46-69` sinh allowlist. Hai chi tiết phải có, mỗi cái đều từ một sự
cố thật:

1. **Có cả host trần, không kèm `:port`.** Proxy chạy ở cổng mặc định (443) gửi
   header `Host` không có số cổng.
2. **Có cả scheme `https`.** Proxy kết thúc TLS, nên origin client gửi lên là
   `https://…` dù server nội bộ chỉ nói http.

Bỏ sót một trong hai là 421 hoặc 403 `Invalid Origin header`. Cả hai đều được
eval offline canh (`allowlist: *`).

Wildcard bind `0.0.0.0` cố ý KHÔNG được đưa vào danh sách host tin cậy — nó
không phải một địa chỉ client kết nối tới.

## CORS — chỉ cần khi client chạy trong trình duyệt

SDK không sinh phản hồi CORS: request `OPTIONS` bị trả **405**, không header
nào. Trình duyệt chặn, và JS chỉ thấy `Failed to fetch (check CORS?)` — một
thông báo trống rỗng, không chỉ ra được gì.

Cách xử lý (`__main__.py:22-40`): bọc `mcp.streamable_http_app()` bằng
`CORSMiddleware`. **Bắt buộc** có `expose_headers=["Mcp-Session-Id"]` — trình
duyệt không đọc được header không được expose, nên không duy trì được session,
dù preflight đã qua.

Origin phải khớp **chính xác** thanh địa chỉ. Trang ở cổng 80/443 gửi origin
không kèm số cổng.

## Reverse proxy / DNS

File mẫu: `scripts/nginx-googlecast-mcp.conf`.

- **`proxy_buffering off;` (dòng 37)** — thiếu thì client treo im lặng, không
  báo bất cứ lỗi gì. Đây là kiểu hỏng tệ nhất: không có tín hiệu để lần theo.
- **`proxy_read_timeout 3600s;` (dòng 42)** — kết nối MCP sống lâu.
- **Hostname không được có dấu gạch dưới.** CA/B Forum cấm `_` trong tên miền
  xin chứng chỉ, nên `google_cast.example.com` KHÔNG BAO GIỜ có https. Với client
  bắt buộc https (Claude Desktop custom connector), đó là ngõ cụt tuyệt đối, và
  không có thông báo lỗi nào nói cho bạn biết lý do. Dùng gạch nối.
- Hai dòng chặn theo IP (`allow 192.168.0.0/16; deny all;`, dòng 55-56) hiện
  **vẫn đang comment** — chưa bật.

## Cờ dành cho client khắt khe

| Cờ | Khi nào cần |
|---|---|
| `--json-response` | Client không parse được khung SSE `event: message` |
| `--stateless` | Client bỏ qua header `Mcp-Session-Id` |
| `--cors-origin <origin>` | Client chạy trong trình duyệt |
| `--allow-host <domain>` | Có reverse proxy đứng trước |

Cấu hình đang chạy thật trên máy triển khai:

```
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud --json-response --stateless --cors-origin http://192.168.1.99:8383" ./scripts/service.sh install
```

## Bẫy vận hành

- **`systemctl enable --now` KHÔNG restart service đang chạy.** Unit file đổi,
  tiến trình vẫn chạy code và tham số CŨ. Sự cố thật: tiến trình cũ sống 3 ngày,
  người dùng phải báo "vẫn lỗi" ba lần. `service.sh` dùng `restart` tường minh,
  và `status` in `/proc/<MainPID>/cmdline` để bạn thấy tiến trình THẬT đang chạy
  gì (`service.sh:78-80,112-115`).
- **Thiết bị Cast có thể treo**: mDNS thấy, ping được, nhưng TCP 8009 từ chối →
  `wait timed out after 10 s`. Restart thiết bị là hết. Chạy `nc -z <ip> 8009`
  TRƯỚC khi nghi ngờ code.
- **406 khi mở `/mcp` bằng trình duyệt là đúng đặc tả**, không phải lỗi.
- **Đừng dùng `pkill -f "<mẫu>"`** để dọn tiến trình: mẫu khớp luôn dòng lệnh
  bash đang chạy, và shell tự giết chính nó. Lấy PID từ `ss -ltnp`.

## Mặt phơi nhiễm — nói thẳng

- Không có xác thực ở tầng ứng dụng. Tên miền phân giải công khai ra internet
  nghĩa là ai biết URL cũng phát được tiếng trong nhà.
- Chặn IP ở nginx chỉ che 8765. **8766 không được che** — nó vẫn bind
  `0.0.0.0`, không xác thực, và phục vụ nguyên thư mục cache TTS. Phải xử lý
  riêng bằng tường lửa.
