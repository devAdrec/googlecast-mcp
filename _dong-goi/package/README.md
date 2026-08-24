# googlecast-mcp — cài từ số 0 tới khi gọi được tool

Trang này chỉ có một việc: đưa một người lạ, trên một máy sạch, từ chỗ không có
gì tới chỗ **một MCP client gọi được tool và nghe được tiếng nói ra loa**.

Tài liệu sản phẩm đang sống nằm ở `README.md` và `docs/architecture.md` trong
repo — trang này không chép lại chúng, chỉ trỏ tới.

Định nghĩa "xong" của trang này: chạy hết Bước 5 và thấy `13 tools`.

---

## Bước 0 — Lấy mã nguồn

```bash
git clone https://github.com/devAdrec/googlecast-mcp.git
cd googlecast-mcp
```

**Repo này là repo riêng tư.** Lệnh trên chỉ chạy được nếu tài khoản của bạn
đã được cấp quyền đọc, hoặc bạn dùng SSH key / personal access token có quyền
đó. Chưa có quyền thì xin chủ repo trước — không có cách vòng.

Đường dẫn thư mục trên máy người đóng gói (`/storage/apps/mcp/googlecast_mcp`)
**không tính** là cách lấy mã: người khác không với tới được nó.

## Bước 1 — Điều kiện máy

- Linux hoặc macOS, Python **3.11+**.
- [`uv`](https://docs.astral.sh/uv/) đã cài (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- Máy này phải **cùng LAN với loa**. Không phải để cho tiện, mà vì hai lý do
  cứng: dò loa dùng mDNS (không đi qua router), và loa tự quay lại tải file âm
  thanh từ chính máy này qua HTTP.
- Ra được internet (edge-tts tổng hợp giọng nói trên mạng).

## Bước 2 — Cài phụ thuộc

```bash
uv sync
```

`uv.lock` được commit sẵn, nên bản dựng lặp lại được. Nếu tự cài bằng pip, giữ
nguyên ràng buộc `mcp[cli]>=1.13,<2` trong `pyproject.toml`: trên PyPI có một
gói tên `mcp` phiên bản 2.0.0 **không liên quan gì**, kéo theo `httpx2` và
`mcp-types`. Cài nhầm nó thì import fail theo kiểu rất khó đoán.

## Bước 3 — Kiểm tra trước khi cắm vào client

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py
```

Mong đợi `67/67 checks passed`, exit 0. Tầng này không cần internet, không phát
tiếng, chạy ở đâu cũng an toàn. Chi tiết ba tầng: `eval/README.md`.

## Bước 4 — Chọn kiểu chạy

### 4a. Cùng máy với client (stdio) — đơn giản nhất

```bash
claude mcp add --scope user googlecast -- uv run --directory "$PWD" googlecast-mcp
claude mcp list          # phải thấy: googlecast ... ✔ Connected
```

### 4b. Chạy nền như một service, phục vụ máy khác trong LAN

```bash
./scripts/service.sh install     # tạo unit systemd, enable, restart
./scripts/service.sh status
```

Mặc định: MCP ở cổng `8765`, cổng phát âm thanh cho loa là `8766`. Đổi bằng
biến môi trường (`MCP_PORT`, `MEDIA_PORT`), thêm cờ bằng `MCP_EXTRA_ARGS`.
Dòng lệnh đang chạy thật trên `192.168.1.128`:

```bash
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud --json-response --stateless --cors-origin http://192.168.1.99:8383" \
    ./scripts/service.sh install
```

Dùng `install` để cài lại chứ đừng dùng `systemctl enable --now`: lệnh đó
**không khởi động lại** service đang chạy, nên tiến trình cũ vẫn sống với dòng
lệnh cũ và trông như bản sửa không có tác dụng. `service.sh status` in luôn
`/proc/<pid>/cmdline` để nhìn thấy tiến trình thật đang chạy bằng lệnh gì.

Cờ nào cần cho client nào, và cách bắc cầu https cho Claude Desktop, xem
`user-manual.md` (mục "Cắm vào client") và `technical-docs.md`.

## Bước 5 — Bằng chứng "gọi được tool"

Đây là bước quyết định. Chạy trên một cổng rỗi để không đụng service thật:

```bash
uv run googlecast-mcp --transport http --host 127.0.0.1 --port 8799 \
    --json-response --stateless &

curl -s -X POST http://127.0.0.1:8799/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'

curl -s -X POST http://127.0.0.1:8799/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Cả hai header `Accept` đều bắt buộc. Thiếu `text/event-stream` thì server trả
`Not Acceptable`, và mở `/mcp` bằng trình duyệt sẽ ra lỗi `406` — đó là đúng
đặc tả, không phải hỏng.

Kết quả thật, chạy lại **từ một bản clone mới** (`git clone` vào thư mục tạm,
`uv sync`, rồi hai lệnh trên) lúc đóng gói:

```
=== initialize ===
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",...,
 "serverInfo":{"name":"googlecast-mcp","version":"1.29.0"}}}
=== tools/list ===
13 tools: discover_devices, get_status, list_devices, list_speakers, pause,
play, play_media, quit_app, say, seek, set_muted, set_volume, stop
=== tools/call list_speakers ===
{"result":{"content":[{"type":"text","text":"{ \"friendly_name\": \"Kitchen speaker\", ...
 \"host\": \"192.168.1.22\", \"cast_type\": \"audio\" }"}, ...]}}
```

Nhìn thấy `13 tools` là cài xong. Nhớ `kill` tiến trình thử ở cổng 8799.

## Bước 6 — Nói thử một câu

```
say(text="Cơm đã chín rồi", target="Kitchen speaker")
```

Bỏ `target` là **cố ý**: server sẽ không phát gì cả, mà trả về danh sách loa
kèm lời nhắn để LLM hỏi lại người dùng. Cách dùng đầy đủ: `user-manual.md`.

---

## Gỡ cài đặt

```bash
./scripts/service.sh remove
```

Danh sách thiết bị ở `~/.googlecast-mcp/speakers.json` được giữ lại; xoá tay
nếu muốn sạch hẳn.

## Trỏ tiếp

| Cần gì | Đọc file nào |
|---|---|
| Yêu cầu gốc và tiêu chí chấp nhận | `requirement.md` |
| Ràng buộc triển khai: cổng, allowlist, CORS, DNS, TLS | `technical-docs.md` |
| Dùng `say`, các dạng `target`, lỗi thường gặp | `user-manual.md` |
| Ba tầng eval, cách kiểm ngược | `eval/README.md` |
| Kiến trúc và luồng xử lý | `docs/architecture.md` (trong repo) |
| Cách xây ra nó | `../method-note.md` |
