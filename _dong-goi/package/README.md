# googlecast-mcp — cài từ số 0 tới gọi được tool

MCP server để một trợ lý AI **nói tiếng Việt ra loa Google** trong nhà bạn, và
điều khiển các thiết bị Google Cast trong mạng nội bộ.

Tài liệu này chỉ có một việc: đưa người chưa từng thấy sản phẩm này, trên một
máy sạch, tới lúc **gọi được tool**. Kiến trúc và vận hành nằm ở
`technical-docs.md`; cách dùng hằng ngày nằm ở `user-manual.md`.

---

## 0. Lấy mã nguồn

```bash
git clone https://github.com/devAdrec/googlecast-mcp.git
cd googlecast-mcp
```

> **Repo này là repo RIÊNG TƯ.** Lệnh trên chỉ chạy được nếu tài khoản GitHub
> của bạn đã được cấp quyền đọc. Bạn cần:
>
> - **Xin quyền từ ai:** chủ repo — tài khoản GitHub **`devAdrec`**.
> - **Xin qua kênh nào:** mở issue tại
>   `https://github.com/devAdrec/googlecast-mcp/issues` (nếu đã thấy repo), hoặc
>   nhắn trực tiếp cho `devAdrec` trên GitHub. Không có bản công khai và không
>   có bản release tải rời — clone là đường duy nhất.
> - **Xác thực:** sau khi được cấp quyền, dùng SSH key
>   (`git clone git@github.com:devAdrec/googlecast-mcp.git`) hoặc personal
>   access token có scope `repo`.
>
> Nếu clone báo `Repository not found`, gần như chắc chắn là **chưa được cấp
> quyền**, chứ không phải gõ sai đường dẫn.

## 1. Điều kiện môi trường

| Cần gì | Vì sao |
|---|---|
| Linux hoặc macOS, Python **≥ 3.11** | mã nguồn dùng cú pháp 3.10+ |
| [`uv`](https://docs.astral.sh/uv/) | quản lý phụ thuộc và chạy; mọi lệnh dưới đây đều qua `uv` |
| Máy **cùng lớp mạng LAN với loa** | dò thiết bị bằng mDNS, và loa sẽ **tải ngược** file âm thanh từ máy này |
| Internet ra ngoài | edge-tts là dịch vụ đọc chữ trực tuyến của Microsoft |

Cài `uv` nếu chưa có:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Máy phải nằm cùng LAN với loa.** Đây không phải khuyến nghị: thiết bị Cast tự
đi tải media qua HTTP từ địa chỉ LAN của máy này. Đặt server ở đám mây thì loa
không bao giờ tải được file.

## 2. Cài phụ thuộc

```bash
uv sync
```

## 3. Chạy thử — dò loa

```bash
uv run googlecast-mcp --help
```

Danh sách thiết bị được lưu bền ở `~/.googlecast-mcp/speakers.json`, nên lần
chạy sau không cần dò lại.

## 4. Nối vào một MCP client

### 4a. Claude Code, cùng máy (đơn giản nhất, dùng stdio)

```bash
claude mcp add --scope user googlecast -- uv run --directory "$PWD" googlecast-mcp
claude mcp list
```

Kết quả mong đợi: dòng `googlecast` kèm `✔ Connected`.

### 4b. Chạy như service HTTP cho máy khác dùng

```bash
./scripts/service.sh install
./scripts/service.sh status
```

Mặc định: MCP ở cổng `8765`, cổng phát audio cho loa `8766`. Đổi bằng biến môi
trường (`MCP_PORT`, `MEDIA_PORT`, `MCP_EXTRA_ARGS`). Ví dụ đang chạy thật:

```bash
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud --json-response --stateless \
  --cors-origin http://192.168.1.99:8383" ./scripts/service.sh install
```

Gỡ: `./scripts/service.sh remove`.

### 4c. Claude Desktop trên máy khác

Claude Desktop **chỉ nhận connector https**. Server LAN chạy http, nên phải bắc
cầu ở phía client:

```json
{
  "mcpServers": {
    "googlecast": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://192.168.1.128:8765/mcp", "--allow-http"]
    }
  }
}
```

Hoặc dựng reverse proxy có TLS — xem `scripts/nginx-googlecast-mcp.conf` và
`technical-docs.md`.

### 4d. Client chạy trong trình duyệt

Phải khai báo **đúng origin trong thanh địa chỉ**, không thừa không thiếu:

```bash
MCP_EXTRA_ARGS="--cors-origin http://192.168.1.99:8383" ./scripts/service.sh install
```

## 5. Xác nhận GỌI ĐƯỢC TOOL (bước nghiệm thu)

Đây là mốc "cài xong". Với transport HTTP:

```bash
curl -s http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
       "protocolVersion":"2025-06-18","capabilities":{},
       "clientInfo":{"name":"cli","version":"1"}}}'
```

rồi:

```bash
curl -s http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

**Đạt khi thấy đủ 13 tool:** `say`, `discover_devices`, `list_speakers`,
`list_devices`, `get_status`, `play_media`, `play`, `pause`, `stop`, `seek`,
`set_volume`, `set_muted`, `quit_app`.

Rồi gọi thật một tool không gây tiếng động:

```bash
curl -s http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call",
       "params":{"name":"list_speakers","arguments":{}}}'
```

Trả về tên loa thật trong nhà bạn ⇒ **đã dùng được**.

Cuối cùng, thử phát tiếng:

> "Nói 'Cơm đã chín rồi' ra loa bếp"

## 6. Tự kiểm sản phẩm

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py            # không tiếng
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online   # cần internet
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware # SẼ PHÁT TIẾNG
```

## 7. Hỏng thì xem đâu trước

| Triệu chứng | Nguyên nhân gần như chắc chắn |
|---|---|
| `421 Misdirected Request` | tên miền/IP client dùng chưa có trong allowlist → thêm `--allow-host` |
| `406 Not Acceptable` | thiếu header `Accept: application/json, text/event-stream` |
| `Failed to fetch (check CORS?)` | client trình duyệt, thiếu `--cors-origin` khớp **chính xác** origin |
| Client treo, không báo lỗi | nginx đang buffer → `proxy_buffering off` |
| `URL must start with 'https'` | Claude Desktop custom connector; bắc cầu bằng `mcp-remote` |
| `wait timed out` khi phát | thiết bị Cast treo. Kiểm `nc -z <ip> 8009` **trước** khi nghi mã nguồn; khởi động lại loa |
| Cài lại service mà không đổi gì | dùng `./scripts/service.sh restart`, và đọc dòng "Running command line" của `status` |

Chi tiết đầy đủ: `technical-docs.md` và `README.md` ở gốc repo.
