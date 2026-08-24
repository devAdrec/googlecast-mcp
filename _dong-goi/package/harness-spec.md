# Harness spec — 5 lớp

Sản phẩm này là **harness vận hành**: đầu ra xác định, đúng/sai kiểm được bằng
máy. Không có bước nào do AI sinh ra nội dung tự do. Trọng số vì thế dồn về
lớp Tool và lớp Execution; lớp Eval chấm pass/fail chứ không chấm chất lượng.

## 1. Context — LLM biết gì để quyết định

Trọng số: **cao**. Đây là chỗ dễ hỏng nhất của một MCP server, và nó không
nằm trong mã xử lý mà nằm trong mô tả tool.

- 13 tool, mỗi tool có docstring viết cho LLM đọc, không phải cho lập trình
  viên. Đã kiểm: mọi tool đều có description.
- `say` **không** đặt `target` vào `required`. Đây là quyết định thiết kế, có
  test riêng: nếu bắt buộc, LLM sẽ tự bịa một tên loa thay vì hỏi lại.
- Khi thiếu `target`, server trả về cả `speakers` (dữ liệu) lẫn `message` (lời
  chỉ dẫn hành động). LLM cần cả hai mới hỏi lại đúng được.
- `list_speakers` tự quét một lần nếu chưa biết gì, để LLM không phải học một
  thứ tự gọi bắt buộc.
- Trạng thái bền: `~/.googlecast-mcp/speakers.json`. Tiến trình khởi động lại
  vẫn biết trong nhà có loa nào.

## 2. Tool — bề mặt gọi được

Trọng số: **cao**.

| Nhóm | Tool |
|---|---|
| Khám phá | `discover_devices`, `list_devices`, `list_speakers` |
| Nói | `say` |
| Media | `play_media`, `play`, `pause`, `stop`, `seek` |
| Thiết bị | `get_status`, `set_volume`, `set_muted`, `quit_app` |

Hợp đồng phải giữ:
- `say` không có `target` → **không tác dụng phụ nào cả**. Kiểm bằng tripwire
  trên cả TTS lẫn cast, không kiểm bằng giá trị trả về.
- `all` → đúng một lời gọi cho mỗi loa vật lý. Đối chiếu theo `host`.
- Một loa hỏng → phần tử đó `error`, những loa còn lại vẫn phát, tổng thể `ok`.
- Mọi lời gọi pychromecast (blocking) đi qua `asyncio.to_thread`.

## 3. Execution — chạy ở đâu, ràng buộc gì

Trọng số: **cao**. Phần lớn thời gian của dự án tiêu ở lớp này.

- Ràng buộc gốc: thiết bị Cast tự đi tải media qua HTTP ⇒ server bắt buộc
  kiêm HTTP file server. Bind `0.0.0.0`, quảng bá `lan_ip()`. Hai thứ khác nhau.
- Cùng LAN với loa. mDNS không đi qua router.
- Cổng cố định 8765 / 8766 khi chạy như service.
- Allowlist DNS-rebinding được **nới**, không tắt. Phải có host trần và scheme
  https.
- CORS chỉ khi client là trình duyệt, và bắt buộc expose `Mcp-Session-Id`.
- Cài lại phải `restart`, không phải `enable --now`.

Chi tiết đầy đủ: `technical-docs.md`.

## 4. Eval — pass/fail

Trọng số: **cao**, nhưng là kiểm đúng-sai, không phải chấm điểm.

Ba tầng phân theo tác dụng phụ (offline / `--online` / `--hardware`), cộng một
vòng kiểm ngược có kỳ vọng viết trước. Toàn bộ ở `eval/README.md`.

Nguyên tắc: eval chưa từng đỏ là eval chưa chứng minh được gì. Vòng kiểm ngược
đầu tiên đã bắt được một test giả và một cái bẫy bytecode cũ.

Chỗ eval **không** với tới được: chất lượng giọng nói, và hiện tượng chồng
luồng khi nghe. Ghi rõ ở mục CHƯA PHỦ chứ không lấp liếm.

## 5. Feedback — biết mình sai bằng cách nào

Trọng số: **trung bình**, nhưng là lớp quyết định tốc độ sửa lỗi.

- Mã lỗi HTTP là chẩn đoán, không phải phiền toái: 421 = allowlist, 403 =
  origin, 406 = thiếu Accept (và là **đúng**), 405 không header = chưa CORS.
- `service.sh status` in `/proc/<pid>/cmdline`: phân biệt "bản sửa sai" với
  "bản sửa chưa được nạp".
- `nc -z <ip> 8009` trước khi nghi mã nguồn: phân biệt thiết bị treo với hồi quy.
- Tín hiệu ở phía con người: người dùng lặp lại *"vẫn báo lổi"* mà không thêm
  thông tin mới nghĩa là **đang sửa sai hướng** — dừng lại, kiểm bản sửa đã
  được nạp chưa. Ở phiên gốc tín hiệu này đã bị bỏ lỡ một vòng.
- Có những lỗi không lớp nào bắt được: `all` chồng luồng, cả bốn lời gọi đều
  trả `playing`. Chỉ tai người phát hiện ra. Với sản phẩm có tác dụng phụ vật
  lý, phải chừa sẵn một chỗ cho con người nghiệm thu.
