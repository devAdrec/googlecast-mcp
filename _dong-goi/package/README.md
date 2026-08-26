# googlecast-mcp — cài từ số 0 tới gọi được tool

Đây là **tờ hướng dẫn cài đặt của gói bàn giao**. Nó chỉ có một mục đích: đưa
người chưa từng thấy product này tới trạng thái **một MCP client gọi được tool
`say` và nghe được tiếng nói phát ra từ loa Google trong nhà**.

Tài liệu sống của product nằm ở `README.md` và `docs/architecture.md` trong repo.
Tờ này **không lặp lại chúng** — nó chỉ đi một đường thẳng từ số 0 đến khi tool
chạy, và trỏ ngược về chúng khi cần chi tiết.

- Yêu cầu gốc + tiêu chí chấp nhận → `requirement.md`
- Ràng buộc triển khai + bảng khiếm khuyết → `technical-docs.md`
- Dùng hằng ngày → `user-manual.md`
- Bộ kiểm chứng → `eval/README.md`

---

## Bước 0 — Lấy mã nguồn

```bash
git clone https://github.com/devAdrec/googlecast-mcp.git
cd googlecast-mcp
```

> **Repo đang ở chế độ private.** Người ngoài không clone được nếu chưa được cấp
> quyền. Cách xin: mở issue trên GitHub gửi tới tổ chức **`devAdrec`**, hoặc nhắn
> trực tiếp cho người bảo trì repo. Sau khi được thêm vào repo, cần **SSH key đã
> nạp lên GitHub**, hoặc **Personal Access Token có scope `repo`** để clone qua
> https. Không có quyền thì mọi bước dưới đây đều không chạy được — đừng bắt đầu.

Kiểm tra nhanh mình có quyền hay không, trước khi clone:

```bash
git ls-remote https://github.com/devAdrec/googlecast-mcp.git
```

Ra được dòng `HEAD` + `refs/heads/main` là có quyền.

## Bước 1 — Điều kiện môi trường

| Cần | Vì sao |
|---|---|
| Python ≥ 3.11 | product dùng cú pháp `str \| None` |
| [`uv`](https://docs.astral.sh/uv/) | quản lý môi trường + chạy; mọi lệnh dưới đây đều qua `uv` |
| Máy **cùng LAN với loa** | dò thiết bị bằng mDNS, và **loa tự quay lại tải file audio từ máy này** |
| Internet ra ngoài | edge-tts render giọng qua dịch vụ neural của Microsoft (không cần API key) |

Điều kiện thứ ba là điều kiện dễ bỏ sót nhất: máy ảo/VPS ngoài mạng nhà **không
chạy được**, dù mọi thứ khác đúng. Lý do ở `technical-docs.md` mục "Ràng buộc gốc".

## Bước 2 — Cài phụ thuộc

```bash
uv sync
```

## Bước 3 — Chạy thử tại chỗ (stdio)

```bash
uv run googlecast-mcp
```

Tiến trình sẽ đứng im chờ MCP client nói chuyện qua stdin — **đúng như vậy là
đang chạy được**, không phải treo. Bấm `Ctrl-C` để thoát.

## Bước 4 — Đăng ký với client

### Claude Code, cùng máy (đường ngắn nhất)

```bash
claude mcp add --scope user googlecast -- uv run --directory "$(pwd)" googlecast-mcp
claude mcp list
```

Dòng `googlecast ... ✔ Connected` là đã xong.

### Claude Desktop trên máy khác

Claude Desktop chỉ nhận URL `https` ở ô **Add custom connector**, nên server LAN
chạy http phải bắc cầu qua `mcp-remote` (cần Node.js trên máy client). Sửa
`claude_desktop_config.json` (**Settings → Developer → Edit Config**):

```json
{
  "mcpServers": {
    "googlecast": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://<ip-máy-chạy-server>:8765/mcp", "--allow-http"]
    }
  }
}
```

Khởi động lại Claude Desktop.

### Client chạy trong trình duyệt (ví dụ llama-server webui)

Server phải được khởi động kèm `--cors-origin` **khớp chính xác thanh địa chỉ**
của trang (scheme + host + port, không path). Xem `user-manual.md`.

## Bước 5 — Chạy như service (máy chủ luôn bật)

```bash
./scripts/service.sh install     # viết unit, enable, RESTART
./scripts/service.sh status      # in cả dòng lệnh tiến trình đang thật sự chạy
```

`install` cần `sudo`, mặc định MCP `8765` và audio `8766`. Dòng lệnh đang dùng
trong triển khai thật, kèm giải thích từng cờ, nằm ở `README.md` của repo, mục
*The deployed command*.

## Bước 6 — Xác nhận đã "gọi được tool"

Đây là mốc nghiệm thu. Chọn một trong hai:

**a) Qua client** — bảo Claude: *"liệt kê loa Google trong nhà"*. Nó phải gọi
`list_speakers` và trả về danh sách loa.

**b) Qua HTTP, không cần client** — với server chạy transport http:

```bash
curl -s -X POST http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'

curl -s -X POST http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Phải ra **13 tool**. Thiếu header `Accept` sẽ nhận `406 Not Acceptable` —
đó là đúng đặc tả, không phải lỗi.

Cuối cùng, phát thử một câu:

```
say(text="Cơm đã chín rồi", target="<tên loa>")
```

Nghe được tiếng là **xong**.

---

## Bằng chứng đã chạy thật (2026-08-26)

Toàn bộ các bước trên được chạy lại từ đầu trên bản clone sạch tại
`/tmp/dod-googlecast`, không dùng thư mục làm việc của người đóng gói:

```
$ git ls-remote https://github.com/devAdrec/googlecast-mcp.git
e6390a567dc49459928f733195769890a6ee3b81	HEAD
e6390a567dc49459928f733195769890a6ee3b81	refs/heads/main

$ git clone https://github.com/devAdrec/googlecast-mcp.git /tmp/dod-googlecast
$ cd /tmp/dod-googlecast && uv sync        # OK

# Bước 3+6 qua stdio (bắt tay MCP thật):
initialize -> {'name': 'googlecast-mcp', 'version': '1.29.0'} 2025-06-18
tools/list -> 13 tools: ['discover_devices', 'get_status', 'list_devices',
  'list_speakers', 'pause', 'play', 'play_media', 'quit_app', 'say', 'seek',
  'set_muted', 'set_volume', 'stop']
tools/call list_speakers -> isError=False in 0.0s
    { "friendly_name": "Kitchen speaker", "uuid": "f88d1e3f-...",
      "model_name": "Google Home Mini", "host": "192.168.1.22",
      "port": 8009, "cast_type": "audio" }

# Bước 6b qua HTTP (cổng rỗi 8798, không đụng service thật ở 8765):
initialize  -> 200, protocolVersion 2025-06-18
tools/list  -> 13 tools
GET /mcp bằng trình duyệt      -> 406   (đúng đặc tả)
POST với Host: evil.example.com -> 421   (chặn DNS-rebinding còn nguyên)
```

**Một điểm không tô hồng:** `list_speakers` trả kết quả trong 0.0s vì máy chạy
thử **đã có sẵn** `~/.googlecast-mcp/speakers.json`. Trên máy trắng, lần gọi đầu
tiên sẽ tự dò mạng và mất khoảng 5 giây. Đó là hành vi đúng, chỉ là chậm hơn con
số ở trên.

**Chưa chạy trong lần nghiệm thu này:** bước 5 (`service.sh install`) không chạy
lại, vì service thật đang phục vụ hai máy khác và cài đè sẽ cắt dịch vụ của họ.
Bước đó đã được kiểm chứng ở lần triển khai gốc — xem `technical-docs.md`.
