# googlecast-mcp — cài từ số 0 tới lúc gọi được tool

Tài liệu này dành cho **người chưa từng thấy máy này**. Không giả định bạn đang
đứng trong thư mục mã nguồn, cũng không giả định máy bạn đã có sẵn công cụ gì.
Đi hết bảy bước dưới đây là bạn **gọi được tool thật**, không dừng ở "cài xong".

`googlecast-mcp` là một MCP server: nó cho mô hình (Claude Desktop, Claude Code,
llama-server webui…) đọc câu tiếng Việt thành tiếng nói và phát ra loa Google
trong nhà.

> Tài liệu đang sống của product nằm ở `README.md` và `docs/architecture.md` ở
> gốc repo. File này KHÔNG chép lại chúng — nó chỉ là đường đi ngắn nhất từ máy
> sạch tới lần gọi tool đầu tiên.

---

## Điều kiện bắt buộc trước khi bắt đầu

- Máy chạy server phải **cùng mạng LAN với loa**. Dò thiết bị dùng mDNS, và
  chính loa sẽ quay lại tải file âm thanh từ máy này. Đặt server ở VPS là hỏng.
- Python 3.11 trở lên.
- Có internet: giọng đọc do edge-tts tổng hợp trực tuyến (không cần khoá API).

---

## Bước 1 — Cài `uv`

Máy sạch chưa chắc có `uv`. Kiểm tra:

```bash
uv --version
```

Nếu báo `command not found`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# rồi mở lại terminal, hoặc:
export PATH="$HOME/.local/bin:$PATH"
```

Kết quả đúng trông như:

```
uv 0.11.21 (x86_64-unknown-linux-gnu)
```

## Bước 2 — Lấy mã nguồn

```bash
git clone <đường-dẫn-hoặc-URL-repo> googlecast-mcp
cd googlecast-mcp
ls
```

Thấy đủ `pyproject.toml`, `src/`, `scripts/`, `uv.lock` là đúng chỗ.

## Bước 3 — Cài phụ thuộc

```bash
uv sync
```

`uv` tự tạo `.venv` và cài đúng phiên bản trong `uv.lock`.

> Nếu terminal của bạn đang có sẵn biến `VIRTUAL_ENV` trỏ tới một venv khác,
> `uv` sẽ in cảnh báo `does not match the project environment path` rồi **bỏ
> qua** biến đó. Đây là cảnh báo vô hại, không phải lỗi.

## Bước 4 — Kiểm tra lệnh đã có

```bash
uv run googlecast-mcp --help
```

Phải in ra bảng tuỳ chọn có `--transport {stdio,http,sse}`. Nếu bước này chạy
được nghĩa là cài đặt đã xong; phần còn lại là đăng ký với client.

## Bước 5 — Chạy thử server

Có hai cách chạy, chọn theo chỗ đặt client:

**Client nằm CÙNG máy** (Claude Code trên chính máy này) → dùng stdio, không
cần chạy tay gì cả; client tự khởi động server. Bỏ qua, sang bước 6.

**Client nằm MÁY KHÁC** (Claude Desktop, llama-server webui) → chạy HTTP:

```bash
uv run googlecast-mcp --transport http --host 0.0.0.0 --port 8765
```

Muốn nó sống mãi như dịch vụ hệ thống thì dùng script có sẵn thay vì chạy tay:

```bash
./scripts/service.sh install     # tạo unit systemd, bật lúc khởi động, chạy luôn
./scripts/service.sh status      # xem nó đang chạy bằng dòng lệnh nào
./scripts/service.sh logs
```

Lệnh đang chạy thật trên máy `192.168.1.128`:

```bash
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud --json-response --stateless --cors-origin http://192.168.1.99:8383" \
  ./scripts/service.sh install
```

> `./scripts/service.sh install` gọi `systemctl restart`, **không** dùng
> `enable --now`. Lý do: `enable --now` không khởi động lại một dịch vụ đang
> chạy, nên tiến trình cũ sẽ sống tiếp với dòng lệnh cũ và bạn sửa gì cũng
> "không ăn". `status` in thêm dòng lệnh thật lấy từ `/proc/<pid>/cmdline`
> chính là để bạn thấy ngay chuyện đó.

## Bước 6 — Đăng ký với client

### 6a. Claude Code, cùng máy (stdio)

```bash
claude mcp add --scope user googlecast -- uv run --directory /đường/dẫn/tới/googlecast-mcp googlecast-mcp
claude mcp list
```

Dòng `googlecast` phải hiện `✔ Connected`. Nếu không, xem `claude mcp get googlecast`.

### 6b. Claude Desktop ở máy khác

Custom connector của Claude Desktop **chỉ nhận `https`**. Server LAN chạy
`http` nên phải bắc cầu bằng `mcp-remote`. Sửa `claude_desktop_config.json`:

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

Nếu bạn đã có tên miền + TLS thật (xem `technical-docs.md`) thì khai báo thẳng
`https://google-cast.adrec.cloud/mcp` làm custom connector, không cần cầu nối.

> Tên miền **không được có dấu gạch dưới**. `google_cast.adrec.cloud` sẽ không
> bao giờ xin được chứng chỉ (quy định CA/B Forum cấm `_` trong tên miền), mà
> Claude Desktop lại bắt buộc https — thành ngõ cụt tuyệt đối. Dùng
> `google-cast.adrec.cloud`.

### 6c. Client chạy trong trình duyệt (llama-server webui)

Trình duyệt chặn nếu server không trả header CORS. Phải khởi động server với
đúng origin bạn thấy trên thanh địa chỉ, khớp từng ký tự:

```bash
uv run googlecast-mcp --transport http --host 0.0.0.0 --port 8765 \
  --cors-origin http://192.168.1.99:8383 --json-response --stateless
```

Rồi khai URL `http://192.168.1.128:8765/mcp` trong webui.

## Bước 7 — Xác nhận GỌI ĐƯỢC TOOL

Đây là bước quyết định. Cài xong mà chưa gọi được tool thì coi như chưa xong.

**Cách nhanh nhất, không cần client nào:**

```bash
curl -s -D /tmp/h -X POST http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"kiemtra","version":"1"}}}'

SID=$(grep -i '^mcp-session-id:' /tmp/h | tr -d '\r' | awk '{print $2}')

curl -s -X POST http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Phải trả về **13 tool**. Thiếu header `Accept` có cả `text/event-stream` thì
server trả lỗi `Not Acceptable` — đó là đúng đặc tả, không phải hỏng.

**Gọi thật một tool, mà không phát ra tiếng nào** — gọi `say` nhưng cố ý không
chọn loa:

```bash
curl -s -X POST http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"say","arguments":{"text":"kiem tra"}}}'
```

Kết quả đúng là `"status": "needs_speaker_selection"` kèm danh sách loa trong
nhà bạn. Thấy được danh sách đó nghĩa là **toàn bộ chuỗi đã thông**: client →
MCP → dò mạng → loa. Từ đây chỉ cần thêm tên loa vào là có tiếng.

**Bằng chứng chạy thật** của bảy bước này nằm trong `eval/README.md`, mục
"Diễn tập Definition of Done".

---

## Gỡ ra

```bash
./scripts/service.sh remove       # xoá unit systemd (giữ lại danh sách thiết bị)
claude mcp remove --scope user googlecast
rm -rf ~/.googlecast-mcp          # nếu muốn xoá cả danh sách loa đã lưu
```

## Chạy bộ kiểm tra

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py            # không tiếng, chạy mọi máy
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online   # thêm TTS thật, vẫn không tiếng
```

Còn `--hardware` thì **phát tiếng thật trong nhà** — chỉ chạy khi bạn chủ ý.

## Đi tiếp

| Muốn biết | Đọc |
|---|---|
| Ba yêu cầu gốc và tiêu chí nghiệm thu | `requirement.md` |
| Cổng, allowlist, CORS, DNS, TLS | `technical-docs.md` |
| Dùng `say` hằng ngày, lỗi thường gặp | `user-manual.md` |
| Kiến trúc bên trong | `../../docs/architecture.md` |
| Cách product này được xây | `../method-note.md` |
