---
product: googlecast-mcp
layer: output
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
package_kind: mcp
package_status: CÓ
method_note: "[[method-googlecast-mcp]]"
reproduction: "[[reproduce-googlecast-mcp]]"
registry: "[[packages/googlecast-mcp]]"
dod_test: "người lạ, môi trường sạch, chỉ đọc file này — GỌI ĐƯỢC TOOL"
dod_verified: 2026-08-28
---

# googlecast-mcp — cách cài

MCP server cho loa Google Cast: dò loa trong LAN, đọc văn bản tiếng Việt thành
tiếng nói và phát ra loa được chọn.

Bốn phần bàn giao: file này (cách cài) · [requirement.md](requirement.md) ·
[technical-docs.md](technical-docs.md) · [user-manual.md](user-manual.md).
Bằng chứng chất lượng: [eval/](eval/README.md).

Tài liệu ĐANG SỐNG của sản phẩm nằm trong chính repo — [`README.md`](../../README.md)
và [`docs/architecture.md`](../../docs/architecture.md). Bộ bốn phần này cố tình
MỎNG và trỏ về đó, để không lệch pha khi sản phẩm đổi.

---

## Bước 0 — lấy mã

```bash
git clone https://github.com/devAdrec/googlecast-mcp.git
cd googlecast-mcp
```

Repo **private**. Chưa có quyền thì xin từ **`devAdrec`** — mở issue trên
GitHub hoặc nhắn trực tiếp. Cần **SSH key** đã đăng ký, hoặc **Personal Access
Token** phạm vi `repo`.

Không có đường nào khác: chưa có release artefact đóng dấu, và đường dẫn local
trên máy người đóng gói không tính là cách lấy mã.

## Bước 1 — điều kiện cần

| Cần | Vì sao |
|---|---|
| Python **≥ 3.11** | mã dùng cú pháp kiểu mới |
| [`uv`](https://docs.astral.sh/uv/) | quản lý môi trường và chạy |
| Cùng **LAN** với loa | dò thiết bị bằng mDNS, và loa phải tải được file audio NGƯỢC về máy này |
| Ra được internet | edge-tts là dịch vụ trực tuyến (không cần khoá API) |

Chạy trong máy ảo/container có mạng NAT thì mDNS và đường tải ngược đều hỏng —
đây là ràng buộc kiến trúc, không phải lỗi cấu hình.

## Bước 2 — cài phụ thuộc

```bash
uv sync
```

## Bước 3 — chạy

**a. Ngay trên máy đang dùng Claude Code (stdio):**

```bash
claude mcp add --scope user googlecast -- uv run --directory "$PWD" googlecast-mcp
claude mcp list        # phải thấy googlecast ... ✔ Connected
```

**b. Dạng dịch vụ, phục vụ máy khác trong LAN:**

```bash
./scripts/service.sh install         # tạo unit systemd, bật lúc khởi động, chạy ngay
./scripts/service.sh status          # in cả dòng lệnh của tiến trình ĐANG chạy
./scripts/service.sh logs
./scripts/service.sh remove
```

Mặc định: MCP ở `:8765`, cổng phát audio ở `:8766`. Đổi bằng biến môi trường
`MCP_PORT`, `MEDIA_PORT`, `MCP_EXTRA_ARGS` (xem đầu `scripts/service.sh`).

Endpoint cho client ở máy khác: `http://<ip-máy-này>:8765/mcp`.

**c. Sau reverse proxy có tên miền + TLS:**

```bash
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud" ./scripts/service.sh install
```

Mẫu cấu hình nginx: `scripts/nginx-googlecast-mcp.conf`. Hai dòng bắt buộc là
`proxy_buffering off` và `proxy_read_timeout 3600s` — thiếu thì client treo mà
không báo lỗi gì.

**Tên miền không được chứa dấu gạch dưới.** CA/B Forum cấm `_` trong tên máy,
nên `google_cast.example.com` KHÔNG BAO GIỜ xin được chứng chỉ, mà Claude
Desktop lại bắt buộc https. Đó là ngõ cụt tuyệt đối, phải đổi tên miền.

**d. Claude Desktop ở máy khác** — custom connector chỉ nhận `https`, nên server
LAN chạy http phải bắc cầu:

```
npx -y mcp-remote http://<ip>:8765/mcp --allow-http
```

**e. Client chạy trong trình duyệt** (vd webui của llama-server):

```bash
MCP_EXTRA_ARGS="--cors-origin http://192.168.1.99:8383" ./scripts/service.sh install
```

Origin phải **khớp chính xác** thanh địa chỉ. Thiếu thì trình duyệt chặn và
JavaScript chỉ nhìn thấy `Failed to fetch (check CORS?)`, không có gì khác.

## Bước 4 — kiểm tra gọi được tool

```bash
curl -s -D- -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"check","version":"1"}}}' \
  http://127.0.0.1:8765/mcp
```

Lấy `mcp-session-id` từ header trả về, rồi gọi `tools/list` với header đó —
phải ra **13 tool**. Header `Accept` phải có ĐỦ cả hai kiểu; thiếu
`text/event-stream` thì server trả `Not Acceptable`. Mở `/mcp` bằng trình duyệt
ra `406` là **đúng đặc tả**, không phải lỗi.

---

## Nghiệm thu — bằng chứng DoD

Phép thử: *người lạ, môi trường sạch, chỉ đọc file này — có gọi được tool không?*
Đã chạy lại ngày **2026-08-28** trên bản clone sạch tại `/tmp/dod-clone`, dùng
cổng rỗi 8797/8798 để **không đụng** service thật đang chạy ở 8765/8766.

| Bước | Trạng thái | Bằng chứng |
|---|---|---|
| B0 lấy mã | **đã-chạy-lại** | `git clone https://github.com/devAdrec/googlecast-mcp.git dod-clone` → `Cloning into 'dod-clone'...`, thư mục có đủ `src/ scripts/ docs/ pyproject.toml`. `git ls-remote origin HEAD` → `3af7361648d2…` |
| B1 điều kiện cần | **đã-chạy-lại** | `python 3.12.3`; `uv` có sẵn; máy cùng LAN với loa (chứng minh gián tiếp ở B4b) |
| B2 `uv sync` | **đã-chạy-lại** | cài xong tới `zeroconf==0.150.0`, không lỗi |
| B3a stdio | **đã-chạy-lại** | nói MCP thật qua stdin/stdout: `initialize -> {'name': 'googlecast-mcp', 'version': '1.29.0'}`, `tools/list -> 13 tool` |
| B3a `claude mcp add` | **không-chạy-lại-được, ĐÃ KIỂM BẰNG ĐƯỜNG KHÁC** | không đăng ký đè lên cấu hình client của người dùng đang dùng. Đường thay thế: chạy thẳng chính lệnh mà `claude mcp add` sẽ chạy (`uv run googlecast-mcp`) rồi bắt tay MCP qua stdio — kết quả ở dòng trên. Phần còn lại của lệnh chỉ là ghi một dòng vào cấu hình client. |
| B3b `service.sh install` | **không-chạy-lại-được, ĐÃ KIỂM BẰNG ĐƯỜNG KHÁC** | cài đè sẽ **cắt dịch vụ** của máy .28 và .99 đang dùng thật. Đường thay thế: dựng một tiến trình MỚI từ bản clone sạch ở cổng rỗi — `ss -ltnp` cho `LISTEN 0 2048 0.0.0.0:8797 users:(("googlecast-mcp",pid=1933782))`. Cùng mục tiêu (tiến trình HTTP phục vụ MCP ra LAN), khác ở chỗ systemd trông coi. Bản thân `service.sh` đọc được và `status` in `/proc/<pid>/cmdline`. |
| B3c/d/e proxy · Claude Desktop · CORS | **không-chạy-lại-được, ĐÃ KIỂM BẰNG ĐƯỜNG KHÁC** | không dựng lại nginx/TLS/Claude Desktop trong phiên này. Đường thay thế: eval tầng offline kiểm thẳng chính đoạn mã quyết định — `security_allows_bare_host_without_port`, `security_allows_https_origin_behind_proxy`, `security_browser_origin_passes_through`, `cors_exposes_session_header` đều XANH, và mỗi mục đó đều ĐỎ khi gieo lỗi tương ứng (xem `eval/README.md`). Lần chạy thật qua https + qua trình duyệt đã làm ở phiên gốc. |
| B4 gọi được tool (HTTP) | **đã-chạy-lại** | `initialize` → `HTTP/1.1 200 OK` + `mcp-session-id: 96117da798f14033af5e0162e8bb78d0`; `tools/list` → **13 tool**: `discover_devices, get_status, list_devices, list_speakers, pause, play, play_media, quit_app, say, seek, set_muted, set_volume, stop` |
| B4b gọi tool có tác dụng thật | **đã-chạy-lại** | `tools/call list_speakers` (không phát tiếng) → dò mDNS thật, trả về loa thật: `Spa speaker` 192.168.1.58, `Bedroom speaker` 192.168.1.24, `Kitchen speaker`… |
| Dọn dẹp | **đã-chạy-lại** | tắt đúng PID đã dựng; `ss` xác nhận 8797 đã trống, `0.0.0.0:8765` của service thật vẫn còn |
| `say` phát tiếng thật | **chưa-chạy** (thiếu sót có chủ đích) | phát tiếng ra loa nhà người dùng cần xin phép trước. Chạy bằng `--hardware` với `GOOGLECAST_MCP_TEST_SPEAKER=<tên loa>`. Đã đạt **78/78 ngay lần đầu** ở phiên gần nhất. |

**Kết luận: `package: CÓ`.** Người lạ có mã và có quyền truy cập repo đi hết
file này thì gọi được tool — đã chứng minh bằng lệnh chạy lại, không phải bằng
đọc thấy hợp lý.

### Không dựng lại được thì hỏng ở đâu

| Triệu chứng | Nguyên nhân thật | Cách xử |
|---|---|---|
| `421 Misdirected Request` | SDK chỉ tin loopback; bind `0.0.0.0` KHÔNG đủ | thêm `--allow-host <tên-miền>` |
| `Not Acceptable` / `406` | client thiếu `Accept: text/event-stream` | thêm header, hoặc `--json-response` |
| `Failed to fetch (check CORS?)` | preflight `OPTIONS` bị trả 405, không có header CORS | `--cors-origin <origin>` |
| client treo, không lỗi | nginx đang buffer | `proxy_buffering off` |
| `wait timed out` khi phát | thiết bị Cast treo: TCP 8009 refuse | `nc -z <ip> 8009`; refuse thì khởi động lại thiết bị |
| sửa xong mà "vẫn lỗi" | tiến trình cũ chưa được nạp lại | `./scripts/service.sh status` xem dòng lệnh thật của tiến trình |
