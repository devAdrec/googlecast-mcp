# Reproduction prompt — googlecast-mcp

Dán nguyên khối dưới đây cho một AI coding agent trong một thư mục trống để dựng lại product tương đương.
Đọc `method-note.md` cạnh file này để hiểu vì sao từng ràng buộc tồn tại.

**Nếu bạn làm một product KHÁC MIỀN** (đèn thông minh, camera, máy in… trong LAN), thay các phần đánh dấu 🔁 và giữ nguyên các phần đánh dấu 🔒:
- 🔁 **thay được:** loại thiết bị, giao thức, cổng, thư viện, cách sinh nội dung (TTS), phần "ràng buộc bắt buộc" đặc thù Cast.
- 🔒 **bất biến, đừng bỏ:** bảng yêu cầu đánh số làm bảng chấm; quy tắc thiếu tham số thì hỏi lại chứ không đoán; lưu bền + kết nối thẳng địa chỉ đã lưu; toàn bộ mục "phơi ra ngoài máy"; service phải restart tường minh; kiểm chứng bằng thiết bị thật kèm ghi lại lần đo. Thêm một bước 0 về khoá/bí mật nếu thiết bị của bạn cần.

---

Xây một MCP server bằng Python (MCP SDK / FastMCP) để một LLM có thể nói tiếng Việt ra loa Google Cast trong mạng nội bộ.

**🔒 Yêu cầu hành vi (đây là bảng chấm, đối chiếu từng mục khi xong):**
1. Dò danh sách loa Google trong LAN qua mDNS rồi lưu lại bền vững.
2. Nhận một tham số `text` tiếng Việt → chuyển thành âm thanh → phát lên loa được chỉ định.
3. Nếu người dùng không chọn loa: KHÔNG phát gì cả, trả về danh sách loa kèm thông điệp để LLM hỏi lại. Chấp nhận một tên, nhiều tên cách phẩy, hoặc "all" / "tất cả".

**🔁 Ràng buộc riêng của miền Google Cast (đã trả giá để biết — thay khi đổi miền):**
- TTS dùng `edge-tts`, giọng mặc định `vi-VN-HoaiMyNeural`. (Nếu bạn muốn đề xuất khác, hãy tạo mẫu âm thanh cho tôi nghe rồi tôi chọn — đừng tự quyết chất lượng giọng.)
- Thiết bị Cast tự đi tải media qua HTTP và không đọc được đường dẫn local ⇒ server phải kèm một HTTP file server. Bind `0.0.0.0`, nhưng URL quảng bá cho thiết bị dựng từ IP LAN — hai thứ khác nhau.
- Lọc loa khỏi thiết bị có màn hình bằng `cast_type` (`audio`/`group` là loa; `cast` là TV/màn hình).
- Lưu bền host/port/uuid từng thiết bị; khi cast, thử **kết nối thẳng bằng địa chỉ đã lưu trước**, mDNS sót là chuyện thường. Đừng báo "not found" cho một thiết bị đang có trong danh sách đã biết.
- Pin `mcp[cli]>=1.13,<2`. Gói `mcp` 2.0.0 trên PyPI KHÔNG liên quan, layout khác, kéo theo `httpx2` (typosquat) và `mcp-types`.

**🔒 Phơi ra ngoài máy (transport Streamable HTTP) — làm đúng ngay từ đầu:**
- SDK chỉ tin `127.0.0.1`; bind `0.0.0.0` không đủ, client máy khác sẽ nhận `421 Misdirected Request`. Nới allowlist host/origin: thêm IP LAN, thêm cờ `--allow-host <domain>`, sinh cả scheme `http` lẫn `https`, và cả biến thể **không kèm `:port`**. GIỮ cơ chế chống DNS-rebinding, chỉ nới — không tắt.
- Thêm CORSMiddleware cho client chạy trong trình duyệt, **bắt buộc** `expose_headers=["Mcp-Session-Id"]`.
- Thêm cờ `--json-response` và `--stateless` cho client khắt khe.
- Nếu đặt sau nginx: `proxy_buffering off` + `proxy_read_timeout 3600s`, nếu không client sẽ treo im không báo lỗi.
- Tên miền cho cert TLS **không được có gạch dưới** (`google_cast.…` sẽ không bao giờ xin được cert).

**🔒 Chạy như service:** viết script install / remove / start / stop / restart / status / logs cho systemd. Lệnh cài **phải restart tường minh** — `enable --now` không khởi động lại tiến trình đang chạy, và bạn sẽ mất nhiều ngày gỡ nhầm bài toán. Lệnh `status` in luôn `/proc/<MainPID>/cmdline` để thấy tiến trình thật đang chạy tham số nào.

**🔒 Kiểm chứng:** phát thật ra loa thật và hỏi tôi có nghe được không. Khi một thiết bị không phản hồi, kiểm `nc -z <ip> 8009` trước khi nghi code. Ghi lại mọi lần đo kèm thời điểm.

**Tài liệu khi xong:** README (cách cài, bảng tool, troubleshooting, lệnh triển khai thật kèm giải thích từng cờ) và một tài liệu kiến trúc (luồng request, bảng module, mô hình luồng, các bẫy đã gặp).
