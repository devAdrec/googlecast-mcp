# Cài đặt googlecast-mcp từ số 0

Đây là **hướng dẫn cài**, viết cho người chưa từng thấy dự án này, trên một máy
sạch. Mỗi lệnh dưới đây đã được chạy thật trên máy triển khai trước khi viết ra.

Chi tiết vận hành, danh sách tool đầy đủ, bảng troubleshooting: xem `README.md`
ở gốc repo. Kiến trúc: `docs/architecture.md`. Bốn file trong thư mục
`_dong-goi/package/` này cố tình MỎNG và chỉ trỏ sang hai nguồn đó, để sáu tháng
nữa không có hai bản tài liệu mâu thuẫn nhau.

## 0. Điều kiện tiên quyết — không có thì dừng lại ở đây

| Điều kiện | Vì sao bắt buộc |
|---|---|
| Máy cài phải **cùng LAN (cùng lớp mạng broadcast) với loa** | Dò thiết bị dùng mDNS, và loa tự quay lại tải file audio từ máy này. Qua VPN / khác VLAN là hỏng. |
| **Có internet** | Giọng đọc dùng edge-tts (dịch vụ online của Microsoft). Không có mạng ra ngoài thì không tổng hợp được tiếng nói. |
| **Linux/macOS + Python ≥ 3.11** | Đã kiểm trên Ubuntu, Python 3.12.3. |
| Ít nhất một loa Google Cast đã bật | Home Mini, Nest Hub, hoặc nhóm loa. |

Không cần API key, không cần tài khoản Google, không cần tài khoản Microsoft.

## 1. Cài `uv` (máy sạch chưa chắc có)

`uv` là trình quản lý môi trường Python mà dự án dùng. Kiểm tra trước:

```bash
uv --version        # đã có thì bỏ qua bước này
```

Chưa có thì cài:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"     # mở terminal mới cũng được
uv --version
```

## 2. Lấy mã nguồn

Repo này **chưa được đẩy lên remote nào** (đã kiểm: `git remote -v` không trả về
gì). Nên "lấy mã nguồn" nghĩa là một trong hai:

```bash
# a) copy nguyên thư mục dự án từ máy đang có nó
rsync -a nguoi_dung@may-cu:/storage/apps/mcp/googlecast_mcp/ ~/googlecast_mcp/

# b) hoặc clone, nếu bạn đã tự đẩy nó lên một remote của mình
git clone <url-remote-cua-ban> ~/googlecast_mcp
```

Từ đây, `~/googlecast_mcp` là **thư mục dự án**. Mọi lệnh dưới đây dùng đường dẫn
tuyệt đối nên bạn đứng ở đâu cũng chạy được — thay `~/googlecast_mcp` bằng đường
dẫn thật của bạn.

## 3. Cài phụ thuộc

```bash
uv sync --directory ~/googlecast_mcp
```

Lệnh này tạo `.venv` và cài đúng phiên bản đã khoá trong `uv.lock`.

> Ghi chú quan trọng về phụ thuộc: `pyproject.toml` ghim `mcp[cli]>=1.13,<2` là
> CỐ Ý. Trên PyPI có một gói tên `mcp` phiên bản 2.0.0 **không liên quan** tới
> MCP SDK chính thức; nó có layout khác và kéo theo `httpx2`, `mcp-types`. Đừng
> gỡ cái ghim đó.

## 4. Chạy thử ngay — chưa cần service, chưa phát ra tiếng

Kiểm tra chương trình khởi động được:

```bash
uv run --directory ~/googlecast_mcp googlecast-mcp --help
```

Chạy bộ eval offline (không cần loa, không phát tiếng, chạy được mọi lúc):

```bash
uv run --directory ~/googlecast_mcp python \
    ~/googlecast_mcp/_dong-goi/package/eval/eval-googlecast-mcp.py
```

Mong đợi: `43/43 passed`, exit code 0. Thêm `--online` để kiểm luôn phần tổng hợp
giọng nói qua internet (vẫn không phát ra tiếng): `45/45 passed`.

Kiểm tra transport HTTP trả lời đúng — chạy trên cổng rỗi 8799 để không đụng
service thật:

```bash
uv run --directory ~/googlecast_mcp googlecast-mcp \
    --transport http --host 127.0.0.1 --port 8799 --json-response --stateless &
sleep 4
curl -s -X POST http://127.0.0.1:8799/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}'
kill %1
```

Mong đợi: JSON có `"serverInfo":{"name":"googlecast-mcp",...}`.

> Nếu bạn mở `http://127.0.0.1:8799/mcp` bằng trình duyệt và thấy **406 Not
> Acceptable** — đó KHÔNG phải lỗi. Đặc tả yêu cầu client phải gửi header
> `Accept` chấp nhận `text/event-stream`; trình duyệt không gửi.

## 5. Dò loa và nói thử (bước này CÓ phát ra tiếng thật)

Cách nhanh nhất là nối một MCP client vào (bước 6) rồi gọi `discover_devices`,
`list_speakers`, rồi `say`. Nếu muốn thử bằng dòng lệnh, dùng tầng `--hardware`
của bộ eval — **nó sẽ phát tiếng trong nhà**, nên hãy chắc là đúng lúc:

```bash
uv run --directory ~/googlecast_mcp python \
    ~/googlecast_mcp/_dong-goi/package/eval/eval-googlecast-mcp.py \
    --hardware --speaker "Tên loa của bạn"
```

Danh sách thiết bị được lưu bền ở `~/.googlecast-mcp/speakers.json`.

## 6. Dùng tại chỗ qua stdio (client chạy cùng máy)

Với Claude Desktop / Claude Code trên chính máy này:

```json
{
  "mcpServers": {
    "googlecast": {
      "command": "uv",
      "args": ["run", "--directory", "/home/ban/googlecast_mcp", "googlecast-mcp"]
    }
  }
}
```

Đường dẫn phải TUYỆT ĐỐI. Nếu `uv` không nằm trong PATH mà client thấy, ghi
đường dẫn đầy đủ tới `uv` (`command -v uv` để lấy).

## 7. Chạy như service (client ở máy khác)

Chỉ làm bước này khi bước 4 đã xanh. Máy chạy service phải cùng LAN với loa.

```bash
~/googlecast_mcp/scripts/service.sh install
```

Mặc định: MCP ở cổng **8765**, cổng phục vụ audio cho loa là **8766**. Đổi bằng
biến môi trường (`MCP_PORT`, `MEDIA_PORT`, `MCP_USER`, `MCP_EXTRA_ARGS`).

Các lệnh quản lý: `install`, `remove`, `start`, `stop`, `restart`, `status`,
`logs`.

> Đây là script cần `sudo` (ghi unit file vào `/etc/systemd/system`).
> `service.sh status` cố ý in cả dòng lệnh THẬT của tiến trình đang chạy
> (`/proc/<pid>/cmdline`), vì unit file trên đĩa có thể đã khác với tiến trình
> đang sống.

Nếu bật tường lửa, mở cả hai cổng cho LAN:

```bash
sudo ufw allow from 192.168.0.0/16 to any port 8765 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 8766 proto tcp
```

Client ở máy khác trỏ vào `http://<ip-máy-này>:8765/mcp`.

## 8. Đưa ra https qua nginx (tuỳ chọn)

Chỉ cần khi client bắt buộc https (Claude Desktop custom connector là một ví dụ).

```bash
sudo cp ~/googlecast_mcp/scripts/nginx-googlecast-mcp.conf \
        /etc/nginx/conf.d/googlecast-mcp.conf
# sửa server_name và proxy_pass cho đúng domain / IP của bạn
sudo nginx -t && sudo systemctl reload nginx
```

Rồi cài lại service với tên miền được cho phép:

```bash
MCP_EXTRA_ARGS="--allow-host ten-mien-cua-ban.example.com" \
    ~/googlecast_mcp/scripts/service.sh install
```

Ba cái bẫy đã cắn thật, đã xử lý sẵn trong file conf — đừng bỏ:

1. **Tên miền không được chứa dấu gạch dưới `_`.** CA không cấp chứng chỉ cho
   nó, nên `google_cast.example.com` là ngõ cụt tuyệt đối với client bắt https.
   Dùng gạch nối: `google-cast.example.com`.
2. **`proxy_buffering off;`** — thiếu dòng này client treo im, không báo lỗi gì.
3. Bỏ `--allow-host` thì server trả **421 Misdirected Request**: SDK chỉ tin
   loopback cho tới khi được nới.

## 9. Client chạy trong trình duyệt (llama-server webui…)

Trình duyệt cần CORS, và cần đọc được header session:

```bash
MCP_EXTRA_ARGS="--allow-host ten-mien-cua-ban.example.com --json-response --stateless --cors-origin http://192.168.1.99:8383" \
    ~/googlecast_mcp/scripts/service.sh install
```

`--cors-origin` phải khớp **chính xác** thanh địa chỉ của trang gọi. Trang chạy
ở cổng 80/443 gửi origin KHÔNG kèm số cổng. Sai origin thì trình duyệt chặn và
JS chỉ thấy `Failed to fetch (check CORS?)` — không có thông tin gì thêm.

## 10. Gỡ

```bash
~/googlecast_mcp/scripts/service.sh remove
```

Danh sách thiết bị ở `~/.googlecast-mcp/` không bị xoá.

## Cảnh báo bảo mật — đọc trước khi mở ra internet

- **Không có xác thực ở tầng ứng dụng.** Ai biết URL cũng phát được tiếng trong
  nhà bạn. Nếu tên miền phân giải công khai, hãy chặn theo IP ở nginx (hai dòng
  `allow`/`deny` trong file conf mẫu, hiện đang comment) hoặc đặt thêm lớp xác
  thực trước nó.
- **Cổng audio 8766 là mặt phơi nhiễm thứ hai**: nó bind `0.0.0.0`, không xác
  thực, và phục vụ nguyên thư mục cache TTS. Chặn IP ở nginx CHỈ che 8765,
  KHÔNG chạm tới 8766. Phải xử lý riêng bằng tường lửa.
