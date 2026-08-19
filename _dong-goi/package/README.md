# googlecast-mcp — cài từ số 0

Tài liệu này chỉ trả lời một câu: **làm sao đưa product này chạy được trên một máy mới.**
Cách dùng hằng ngày, danh sách tool, bảng troubleshooting nằm ở `README.md` gốc của repo —
đó là tài liệu ĐANG SỐNG, luôn đúng hơn bản chép lại.

| Bạn cần gì | Đọc ở đâu |
|---|---|
| Cài đặt từ đầu | file này |
| Dùng `say`, các dạng `target`, lỗi thường gặp | `_dong-goi/package/user-manual.md` → `README.md` |
| Kiến trúc, luồng request | `docs/architecture.md` |
| Ràng buộc triển khai (cổng, allowlist, CORS, DNS) | `_dong-goi/package/technical-docs.md` |
| Vì sao product tồn tại, tiêu chí chấp nhận | `_dong-goi/package/requirement.md` |
| Kiểm chứng bản cài | `_dong-goi/package/eval/` |

## 0. Máy này có đủ điều kiện không?

Bốn điều kiện, thiếu một là product KHÔNG chạy đúng — và ba trong bốn không hiện ra
thành lỗi rõ ràng, nó chỉ im lặng không phát tiếng:

1. **Linux + systemd**, Python **3.12**, có `uv` trong PATH.
2. **Cùng LAN, cùng broadcast domain với loa.** Discovery dùng mDNS: mDNS không đi
   qua router giữa hai subnet. Máy ở VLAN khác sẽ không thấy loa nào.
3. **Loa phải gọi ngược về được máy này qua HTTP.** Thiết bị Cast tự đi tải file
   audio; nếu firewall chặn chiều loa → máy, mọi thứ báo `playing` mà không ra tiếng.
4. **Ra được internet** — edge-tts tổng hợp giọng nói trên máy chủ Microsoft, không
   phải offline.

## 1. Lấy mã nguồn và dựng môi trường

```bash
git clone <repo> googlecast_mcp && cd googlecast_mcp
uv sync
```

`uv sync` khoá `mcp[cli]>=1.13,<2` theo `pyproject.toml`. **Đừng nới trần `<2`.**
Trên PyPI có gói tên `mcp` phiên bản 2.0.0 KHÔNG liên quan gì tới MCP SDK: layout
khác hẳn và nó kéo theo `httpx2` (typosquat) cùng `mcp-types`. Dấu hiệu nhận biết
bản đúng: nó phụ thuộc `httpx`, không phải `httpx2`.

## 2. Chạy thử ở chế độ đơn giản nhất

```bash
uv run --directory "$PWD" googlecast-mcp --transport http --host 0.0.0.0 --port 8765
```

Rồi từ chính máy đó:

```bash
uv run --directory "$PWD" python _dong-goi/package/eval/eval-googlecast-mcp.py
```

Eval tầng offline không cần loa và **không phát tiếng**. Thoát mã 0 = bản cài lành lặn.
Xem `eval/README.md` trước khi nghĩ tới cờ `--hardware` (cờ đó PHÁT TIẾNG THẬT).

## 3. Cài thành service systemd

```bash
./scripts/service.sh install
./scripts/service.sh status
./scripts/service.sh logs
```

Các lệnh khác: `remove`, `start`, `stop`, `restart`.

Biến môi trường điều chỉnh: `MCP_HOST` (mặc định `0.0.0.0`), `MCP_PORT` (`8765`),
`MEDIA_PORT` (`8766`), `MCP_USER`, `MCP_EXTRA_ARGS`.

Lệnh đang chạy thật trên `192.168.1.128`:

```bash
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud --json-response --stateless --cors-origin http://192.168.1.99:8383" \
  ./scripts/service.sh install
```

**Cạm bẫy đã cắn một lần, mất 3 ngày:** `systemctl enable --now` KHÔNG khởi động lại
một service đang chạy. Sửa unit xong mà tiến trình cũ vẫn sống thì nó vẫn chạy mã và
tham số CŨ, trong khi mọi thứ trông như đã cài xong. `service.sh install` nay gọi
`restart` tường minh, và `service.sh status` in `/proc/<MainPID>/cmdline`
(`scripts/service.sh:78-80,112-115`). **Luôn đọc dòng cmdline đó** để xác nhận tiến
trình đang chạy đúng tham số bạn vừa đặt, thay vì tin vào `active (running)`.

## 4. Reverse proxy https (chỉ khi client bắt buộc https)

Claude Desktop custom connector chỉ nhận `https://`. Dùng
`scripts/nginx-googlecast-mcp.conf` làm mẫu vhost, rồi cấp chứng chỉ Let's Encrypt.

Hai điều kiện sống còn, cả hai đều từng làm hỏng việc:

- **Tên miền KHÔNG được chứa dấu gạch dưới.** `google_cast.example.com` sẽ KHÔNG BAO
  GIỜ xin được chứng chỉ — CA/B Forum cấm `_` trong hostname. Đây là ngõ cụt tuyệt
  đối, không có cách vòng. Dùng gạch nối: `google-cast.example.com`.
- **`proxy_buffering off;`** và `proxy_read_timeout 3600s;`
  (`scripts/nginx-googlecast-mcp.conf:37,42`). Thiếu, client sẽ TREO im lặng, không
  báo bất kỳ lỗi nào — nginx giữ luôn dòng sự kiện.

Phải khai tên miền cho server bằng `--allow-host <domain>`, nếu không SDK trả
**421 Misdirected Request**.

Nếu client không đòi https, có đường vòng nhẹ hơn:
`npx -y mcp-remote http://<ip>:8765/mcp --allow-http`.

## 5. Kiểm tra cài đúng

Theo thứ tự, dừng ở bước đầu tiên sai:

```bash
# 1. tiến trình chạy đúng tham số
./scripts/service.sh status

# 2. cổng đang nghe
ss -ltnp | grep -E '8765|8766'

# 3. endpoint sống (406 ở đây là ĐÚNG ĐẶC TẢ, không phải lỗi)
curl -i http://127.0.0.1:8765/mcp

# 4. eval offline
uv run --directory "$PWD" python _dong-goi/package/eval/eval-googlecast-mcp.py

# 5. loa có thật sự bắt được TCP không (làm TRƯỚC khi nghi ngờ mã nguồn)
nc -z <ip-loa> 8009
```

Ý nghĩa mã trả về khi gọi thẳng bằng trình duyệt hoặc curl:

| Mã | Nghĩa | Xử lý |
|---|---|---|
| 406 | client không nhận `text/event-stream` | Bình thường. Trình duyệt mở tay luôn ra thế này. |
| 421 | Host không nằm trong allowlist | thêm `--allow-host <domain>` |
| 403 `Invalid Origin header` | origin trình duyệt không được phép | thêm `--cors-origin <origin>` |
| 405 cho `OPTIONS` | chưa bật CORS | thêm `--cors-origin`; nếu không trình duyệt chỉ báo "Failed to fetch" |

## 6. Trước khi coi là xong: hai lỗ hổng phải tự quyết

Product **không có xác thực ở tầng ứng dụng**. Nếu bạn trỏ một tên miền công khai vào
nó, bất kỳ ai biết URL đều phát được tiếng trong nhà bạn.

Và chặn IP ở nginx **chỉ che cổng 8765**. Cổng audio **8766 vẫn bind `0.0.0.0`, không
xác thực, phục vụ nguyên một thư mục file**. Muốn đóng thật thì phải chặn ở tường lửa
máy chủ, không phải ở nginx. Chi tiết trong `technical-docs.md`.
