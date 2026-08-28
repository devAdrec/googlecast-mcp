---
product: googlecast-mcp
layer: reproduction
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
method_note: "[[method-googlecast-mcp]]"
registry: "[[packages/googlecast-mcp]]"
---

# Prompt dựng lại googlecast-mcp

Dán phần trong khung cho một tác nhân lập trình có quyền chạy lệnh, trong một
thư mục trống. Prompt cố ý **nêu ràng buộc và ngõ cụt trước**, vì đó là thứ
đã tốn nhiều thời gian nhất.

Muốn hiểu **vì sao** lại chọn thế thì đọc [[method-googlecast-mcp]]; muốn cài
bản đã có thì đọc [[package/README]].

---

```
Xây một MCP server bằng Python để điều khiển loa Google Cast trong LAN.

## Ba yêu cầu chức năng
1. Dò thiết bị Google Cast trong LAN qua mDNS, LỌC loa (cast_type là "audio"
   hoặc "group") khỏi thiết bị hình ảnh ("cast"), và LƯU BỀN danh sách ra
   ~/.googlecast-mcp/speakers.json. Lưu là GỘP theo uuid, không ghi đè: mDNS
   lossy, một lần quét sót không được làm mất thiết bị đã biết.
2. Một tool say(text, target?, voice, rate): đọc văn bản TIẾNG VIỆT thành tiếng
   nói rồi phát ra loa được chọn.
3. Nếu không chọn loa thì KHÔNG PHÁT GÌ CẢ — trả về trạng thái
   "needs_speaker_selection" kèm danh sách loa và câu hướng dẫn để LLM hỏi lại
   người dùng. Nhận: một tên, nhiều tên cách dấu phẩy, hoặc "all"/"tất cả".

## Ràng buộc kiến trúc (đọc trước khi chia module)
- Thiết bị Cast TỰ ĐI TẢI media qua HTTP. Đưa đường dẫn file cho nó là vô
  nghĩa. Vì vậy server này BẮT BUỘC kiêm một HTTP file server phục vụ thư mục
  cache audio trên địa chỉ LAN.
- HTTP server đó phải bind 0.0.0.0 nhưng QUẢNG BÁ địa chỉ LAN thật. Hai thứ
  này KHÁC NHAU; lẫn lộn là loa không tải được file.
- pychromecast là blocking: mọi tool MCP phải đẩy nó qua asyncio.to_thread.

## Chọn thành phần
- TTS: edge-tts (vi-VN-HoaiMyNeural nữ, vi-VN-NamMinhNeural nam). Miễn phí,
  không cần khoá API, giọng Việt tự nhiên nhất trong các phương án miễn phí.
- Giao thức Cast: pychromecast — thư viện Python duy nhất còn được bảo trì.
- MCP SDK: GHIM "mcp[cli]>=1.13,<2". Trên PyPI có một gói tên `mcp` phiên bản
  2.0.0 HOÀN TOÀN KHÔNG LIÊN QUAN, kéo theo httpx2 (typosquat) và mcp-types.

## Bốn cái bẫy phải tránh ngay từ đầu, không phải vá sau
1. Dịch vụ TTS TỪ CHỐI các kết nối đến cùng lúc. Thử lại KHÔNG đủ (đo được
   4/6 đạt, 101s) vì các lần thử vẫn chồng lên nhau. Phải TUẦN TỰ HOÁ.
2. Khoá tuần tự hoá KHÔNG được là asyncio.Lock mức module. Nó chỉ gắn vào vòng
   lặp KHI CÓ TRANH CHẤP, nên lỗi ẩn tới lúc hai render chồng nhau, sau đó mọi
   vòng lặp khác nhận "RuntimeError: bound to a different event loop". Dùng
   MỘT KHOÁ CHO MỖI VÒNG LẶP (weakref.WeakKeyDictionary khoá theo event loop).
3. edge-tts save() có thể TẠO FILE RỒI MỚI NÉM LỖI, để lại file 0 byte và lần
   sau dùng lại nó. Phải unlink trước mỗi lần thử, và coi file 0 byte là
   KHÔNG có cache.
4. "all" phải BỎ nhóm loa (cast_type="group"). Nhóm Cast phát QUA chính các
   thành viên, nên gửi cả nhóm lẫn thành viên thì một loa vật lý nhận hai
   luồng. API KHÔNG báo sai — cả bốn đều trả "playing"; dấu vết duy nhất là
   hai mục cùng "host". Gọi nhóm theo tên thì vẫn phải được.

## Vận hành: chạy dạng service, phục vụ máy khác trong LAN
Viết scripts/service.sh: install / remove / start / stop / restart / status /
logs cho systemd. Mặc định MCP :8765, cổng audio :8766.
- install PHẢI gọi `systemctl restart` tường minh. `systemctl enable --now`
  KHÔNG restart một service đang chạy — tiến trình cũ sẽ sống với dòng lệnh cũ
  và người dùng sẽ nói "vẫn lỗi" nhiều lần mà không ai hiểu vì sao.
- status PHẢI in /proc/<MainPID>/cmdline, để nhìn một cái là biết bản đang
  chạy có phải bản vừa sửa không.

## Bốn ngõ cụt mạng, vá luôn trong CLI
1. SDK chỉ tin 127.0.0.1 → client ở máy khác nhận 421 Misdirected Request.
   Bind 0.0.0.0 KHÔNG đủ. GIỮ bảo vệ DNS-rebinding, chỉ NỚI allowlist: thêm
   IP LAN và cờ --allow-host <domain> lặp lại được. Phải cho cả scheme https
   (proxy kết thúc TLS) LẪN dạng host TRẦN không kèm ":port" (proxy ở cổng mặc
   định gửi Host không có port).
2. Client trình duyệt: SDK trả OPTIONS = 405 và không có header CORS, nên
   trình duyệt chặn và JS chỉ thấy "Failed to fetch". Thêm cờ --cors-origin
   lặp lại được, bọc app bằng CORSMiddleware, và BẮT BUỘC
   expose_headers=["Mcp-Session-Id"] — không expose thì trình duyệt không duy
   trì được phiên.
3. Thêm --json-response và --stateless cho client khắt khe.
4. Nếu đứng sau nginx: proxy_buffering off và proxy_read_timeout 3600s, thiếu
   thì client treo mà không báo lỗi gì. Và TÊN MIỀN KHÔNG ĐƯỢC CHỨA DẤU GẠCH
   DƯỚI — CA/B Forum cấm, nên nó sẽ không bao giờ xin được chứng chỉ.

## Chống lỗi lúc chạy
- mDNS có thể SÓT một thiết bị đã lưu, gây DeviceNotFoundError tự mâu thuẫn.
  Khi phân giải tên không thấy, hãy NỐI THẲNG địa chỉ đã lưu trước, rồi mới
  quét lại.
- Một loa không trả lời KHÔNG được kéo đổ cả lượt phát: bắt lỗi từng loa, trả
  kết quả riêng cho mỗi loa, tổng thể "ok" nếu còn ít nhất một loa phát được.
- Kẹp âm lượng về khoảng 0.0–1.0.

## Bàn giao
- README.md: cách cài, cách đăng ký với client (Claude Code stdio; Claude
  Desktop máy khác phải bắc cầu `npx -y mcp-remote http://<ip>:8765/mcp
  --allow-http` vì custom connector chỉ nhận https; client trình duyệt cần
  --cors-origin khớp CHÍNH XÁC thanh địa chỉ), và bảng xử lý sự cố.
- docs/architecture.md: sơ đồ luồng TTS → HTTP → Cast và các ràng buộc.
- Bài kiểm chia ba tầng theo TÁC DỤNG PHỤ: offline (mặc định, chỉ thư mục
  tạm, phải chạy trong vài giây), --online (gọi TTS thật), --hardware (PHÁT
  TIẾNG THẬT, mặc định tắt, phải xin phép). Báo cáo phải in "đã chạy X/Y mục
  đăng ký" và coi X<Y là KHÔNG ĐẠT toàn cục.

## Nghiệm thu
Trên máy CÙNG LAN với loa thật:
- Từ một bản clone sạch: uv sync, chạy transport http ở một cổng rỗi, POST
  initialize rồi tools/list (Accept phải có cả application/json và
  text/event-stream) → đúng 13 tool.
- Gọi list_speakers → ra loa thật, không lẫn thiết bị hình ảnh.
- Gọi say(...) với một tên loa → NGHE ĐƯỢC tiếng Việt. Đừng nghiệm thu bằng
  player_state (clip ngắn có thể đã phát xong lúc lệnh trả về — đo được say()
  mất 5.4s trong khi clip chỉ 2.26s). Hãy kiểm content_id khớp URL vừa cast và
  duration > 0.
- Gọi say(...) KHÔNG có target → không loa nào kêu, trả needs_speaker_selection.

Nếu phát ra "wait timed out": kiểm `nc -z <ip> 8009` TRƯỚC khi nghi mã. mDNS
và ping có thể thông trong khi TCP 8009 refuse — đó là thiết bị treo, khởi động
lại thiết bị là hết. Và đừng kết luận nguyên nhân hệ thống chỉ vì hai thiết bị
cùng model cùng hỏng: hai mẫu trùng nhau không đủ.
```

---

## Sai khác dự kiến

Prompt này dựng lại **cùng kiến trúc và cùng hành vi**, không phải cùng từng
dòng mã. Những chỗ nhiều khả năng khác bản gốc:

- Cách chia hàm bên trong `cast_manager.py`.
- Tên biến và bố cục `service.sh`.
- Có thể thiếu vài tool Cast chung (`seek`, `quit_app`…) nếu prompt không liệt
  kê đủ — bản gốc có **13 tool**: `say`, `discover_devices`, `list_speakers`,
  `list_devices`, `get_status`, `play_media`, `play`, `pause`, `stop`, `seek`,
  `set_volume`, `set_muted`, `quit_app`.
- Bộ eval sẽ khác về cách chia mục; điều cần giữ là **ba tầng theo tác dụng
  phụ** và luật *đếm đủ trước khi đếm xanh*.

## Không dựng lại được bằng prompt

- **Sự chấp thuận của người nghe** về giọng đọc. Đây là tiêu chí cảm nhận, bắt
  buộc phải có người nghe thật.
- **Danh sách loa thật** trong nhà người dùng.
- **Tên miền và chứng chỉ TLS.**
