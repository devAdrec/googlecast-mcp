# googlecast-mcp — cài từ số 0 tới gọi được tool

Tài liệu này chỉ có một việc: đưa người chưa từng thấy product này, trên một
máy sạch, tới chỗ **gọi được tool MCP**. Mọi thứ khác nằm ở nơi khác:

| Cần gì | Đọc file nào |
|---|---|
| Dùng hằng ngày, từng tool làm gì | `user-manual.md` |
| Yêu cầu gốc + tiêu chí chấp nhận | `requirement.md` |
| Kiến trúc, ràng buộc triển khai, khiếm khuyết | `technical-docs.md` → `docs/architecture.md` trong repo |
| Bài kiểm và cách nó tự chứng minh | `eval/README.md` |

`README.md` và `docs/architecture.md` **trong repo** là tài liệu đang sống của
product. File này không chép lại chúng, chỉ trỏ sang.

---

## Bước 0 — Lấy mã nguồn

```bash
git clone https://github.com/devAdrec/googlecast-mcp.git
cd googlecast-mcp
```

Repo đang **private**. Người ngoài phải xin quyền đọc trước:

- **Xin ai:** chủ repo, tài khoản GitHub `devAdrec`.
- **Kênh nào:** mở issue trên GitHub, hoặc nhắn trực tiếp cho `devAdrec`.
- **Cần gì để clone:** một SSH key đã đăng ký trong tài khoản GitHub của bạn,
  hoặc một Personal Access Token có scope `repo`. Với SSH đổi URL thành
  `git@github.com:devAdrec/googlecast-mcp.git`.

Không có đường nào khác: product này không có bản phát hành đóng gói sẵn.

## Bước 1 — Điều kiện của máy

| Điều kiện | Vì sao |
|---|---|
| Python ≥ 3.11 | cú pháp và `asyncio` mà mã dùng |
| [`uv`](https://docs.astral.sh/uv/) | trình quản lý môi trường/khoá phụ thuộc của product |
| **Cùng mạng LAN với loa** | dò thiết bị bằng mDNS, và loa phải với ngược lại được về máy này để tải audio |
| Ra được internet | edge-tts render giọng nói trên dịch vụ của Microsoft |

Máy ảo NAT, container mạng bridge, hay Wi-Fi khách có cách ly client đều **không
chạy được** — mDNS không qua được, và loa không mở được kết nối ngược về.

```bash
python3 --version      # ≥ 3.11
uv --version
```

## Bước 2 — Cài phụ thuộc

```bash
uv sync
```

Khoá phụ thuộc đã ghim `mcp[cli]>=1.13,<2`. **Đừng nới cái pin này**: trên PyPI
có một gói tên `mcp` phiên bản 2.0.0 hoàn toàn không liên quan, kéo theo
`httpx2` và `mcp-types`. Kiểm nhanh: gói đúng cần `httpx`, không phải `httpx2`.

Kiểm máy đã sẵn sàng:

```bash
uv run googlecast-mcp --help
```

## Bước 3 — Chọn một trong hai cách chạy

### 3A. stdio, cùng máy với client (đơn giản nhất)

Dành cho Claude Code / Claude Desktop chạy ngay trên máy này. Client tự khởi
động tiến trình server, không cần cổng nào.

```bash
claude mcp add --scope user googlecast -- uv run --directory /đường/dẫn/tới/googlecast-mcp googlecast-mcp
claude mcp list
```

Đạt khi dòng `googlecast` hiện `✔ Connected`.

### 3B. HTTP, phục vụ máy khác trong LAN

```bash
./scripts/service.sh install     # viết unit systemd, bật lúc khởi động, chạy
./scripts/service.sh status
./scripts/service.sh logs
```

`install` cần `sudo`, mặc định MCP ở cổng `8765` và audio ở cổng `8766`. Đổi
bằng biến môi trường: `MCP_PORT=9000 MEDIA_PORT=9001 ./scripts/service.sh install`.

**Phải mở CẢ HAI cổng** nếu có tường lửa. Cổng audio không phải tuỳ chọn: loa
tự mở kết nối về đó để tải file. Thiếu nó thì lệnh cast vẫn "thành công" mà
loa im lặng — đúng triệu chứng "màn hình nháy sáng rồi tắt".

```bash
sudo ufw allow from 192.168.0.0/16 to any port 8765 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 8766 proto tcp
```

Chạy tay, không qua systemd:

```bash
uv run googlecast-mcp --transport http --host 0.0.0.0 --port 8765 --media-port 8766
```

## Bước 4 — Xác nhận GỌI ĐƯỢC TOOL

Đây là mốc "dùng được". Chưa qua bước này thì chưa cài xong.

### Với stdio (3A)

Trong Claude Code, gọi `list_speakers`. Trả về danh sách loa là đạt.

### Với HTTP (3B)

Hai lời gọi, đúng thứ tự — `tools/list` không đứng một mình được, phải
`initialize` trước:

```bash
BASE=http://127.0.0.1:8765/mcp

curl -sS -D /tmp/mcp-headers.txt "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2024-11-05",
        "capabilities":{},
        "clientInfo":{"name":"smoke","version":"0"}}}'

SESSION=$(grep -i '^mcp-session-id:' /tmp/mcp-headers.txt | tr -d '\r' | cut -d' ' -f2)

curl -sS "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

curl -sS "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

Đạt khi lần gọi cuối liệt kê **13 tool**: `say`, `discover_devices`,
`list_speakers`, `list_devices`, `get_status`, `play_media`, `play`, `pause`,
`stop`, `seek`, `set_volume`, `set_muted`, `quit_app`.

Header `Accept: application/json, text/event-stream` là **bắt buộc**. Thiếu nó
server trả `Not Acceptable: Client must accept text/event-stream` — đúng đặc
tả, không phải lỗi. Mở `/mcp` bằng trình duyệt cũng ra `406` vì lý do đó.

## Bước 5 — Từng loại client ở xa

| Client | Cần gì |
|---|---|
| **Claude Code / Desktop cùng máy** | stdio ở 3A, không cần gì thêm |
| **Claude Desktop máy khác** | custom connector **chỉ nhận `https`**. Phải bắc cầu: `npx -y mcp-remote http://<ip>:8765/mcp --allow-http`, hoặc đặt reverse proxy TLS trước server |
| **Client trình duyệt** (vd llama-server webui) | chạy server với `--cors-origin <origin khớp CHÍNH XÁC thanh địa chỉ>`, ví dụ `--cors-origin http://192.168.1.99:8383` |
| **Client khắt khe về khung SSE** | thêm `--json-response --stateless` |
| **Sau reverse proxy tên miền** | thêm `--allow-host <domain>` |

Tên miền dùng cho HTTPS **không được có gạch dưới** (`google_cast.example.com`).
CA/B Forum cấm ký chứng chỉ cho tên có `_`; đó là ngõ cụt tuyệt đối, không có
cách vòng. Dùng gạch ngang: `google-cast.example.com`.

Mẫu cấu hình nginx: `scripts/nginx-googlecast-mcp.conf`. Hai dòng bắt buộc:

```nginx
proxy_buffering off;
proxy_read_timeout 3600s;
```

Thiếu `proxy_buffering off`, client **treo mà không báo lỗi gì** — triệu chứng
khó chẩn đoán nhất trong cả product này.

## Bước 6 — Chạy bài kiểm (không bắt buộc, nhưng nên)

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py            # offline
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online   # gọi edge-tts thật
uv run python _dong-goi/package/eval/reverse-check.py                  # bài kiểm tự chứng minh
```

`--hardware` **phát ra tiếng thật** trên loa thật; chỉ chạy khi trong nhà đã
đồng ý, và phải đặt `GOOGLECAST_MCP_TEST_SPEAKER=<tên loa>`.

## Gỡ ra

```bash
./scripts/service.sh remove     # dừng, tắt tự khởi động, xoá unit
```

Danh sách thiết bị ở `~/.googlecast-mcp/speakers.json` được giữ lại. Cache
audio nằm trong `${GOOGLECAST_MCP_CACHE:-/tmp/googlecast-mcp-tts}` — xoá tay
nếu muốn; product hiện **không tự dọn** (xem `technical-docs.md`).

## Hỏng thì xem đâu

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| `421 Misdirected Request` | client tới bằng tên/IP chưa được cho phép → thêm `--allow-host` |
| `406 Not Acceptable` | thiếu header `Accept: text/event-stream` |
| `Failed to fetch (check CORS?)` | thiếu `--cors-origin`; origin phải khớp chính xác |
| `URL must start with 'https'` | Claude Desktop custom connector → bắc cầu `mcp-remote` |
| Client treo, không lỗi | nginx thiếu `proxy_buffering off` |
| Loa nháy sáng rồi tắt, không có tiếng | cổng audio (8766) không tới được từ loa |
| `wait timed out` với một thiết bị | thiết bị treo. Kiểm `nc -z <ip> 8009` **trước khi** nghi mã. Khởi động lại thiết bị |
| Sửa xong mà "vẫn lỗi" | bản sửa chưa được nạp: `./scripts/service.sh restart` rồi xem `status` in ra dòng lệnh thật đang chạy. `systemctl enable --now` **không** khởi động lại tiến trình cũ |
