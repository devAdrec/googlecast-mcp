---
product: googlecast-mcp
product_path: /storage/apps/mcp/googlecast_mcp
loai: cong-cu-thuan (MCP server)
ngay: 2026-08-13
transmission_level_self_assessed: L3
transmission_level_independent: "L3 (agent context sạch, 2026-08-13; đối chiếu 6/6 khẳng định kỹ thuật với source, không phát hiện sai sự thật)"
prompt_source: nguyên văn từ log phiên gốc
---

# Method note — googlecast-mcp

Product làm gì và dùng thế nào: đọc `README.md`. Kiến trúc và module: đọc `docs/architecture.md`.
File này KHÔNG lặp lại hai tài liệu đó. Nó chỉ ghi **cách nghĩ** đã dựng ra được nó — phần
tái dùng được cho **bất kỳ MCP server nào phục vụ nhiều loại client**.

## Bài học 30 giây

1. **Cái ràng buộc kiến trúc thường nằm ở phía thiết bị, không phải phía mình.** Loa Cast tự đi tải
   file qua HTTP — nên server "nói được" bắt buộc phải kiêm luôn web server. Tìm ra ràng buộc gốc này
   trước, mọi quyết định sau tự rơi vào chỗ.
2. **Đo, đừng đoán.** Gần như mọi ngõ cụt ở dự án này được gỡ bằng một phép đo 5 phút (poll trạng thái,
   bật log, `nc -z`, `curl` giả client), chứ không phải bằng sửa mò.
3. **Hai ca giống nhau không phải là một quy luật.** Thấy hai Nest Hub cùng đóng cổng 8009, tôi kết luận
   "firmware bỏ cổng" — sai. Restart là hết. Trước khi quy cho nguyên nhân hệ thống, hãy thử phép thử rẻ nhất.
4. **"Sửa rồi mà không thấy đổi" = bạn đang nhìn nhầm tiến trình.** So dòng lệnh THẬT của tiến trình đang
   chạy với file cấu hình, đừng tin file cấu hình.
5. **Client là môi trường, không phải là spec.** Cùng một MCP server đúng chuẩn vẫn hỏng theo 4 kiểu khác nhau
   ở 4 loại client. Liệt kê trước các loại client sẽ gọi vào, rồi tự tay giả lập từng loại.
6. **Nói thật chỗ còn hở.** Server này chưa có xác thực; ghi rõ trong tài liệu tốt hơn là để người dùng
   tự phát hiện.

## Phần phương pháp

### 1. Tìm ràng buộc gốc trước khi thiết kế

- **Nguyên tắc:** với tích hợp phần cứng/dịch vụ ngoài, hỏi "ai là bên chủ động đi lấy dữ liệu?" trước khi
  vẽ module. Câu trả lời quyết định luôn hình dạng hệ thống.
- **Việc làm:** đọc cách giao thức Cast nhận media → phát hiện thiết bị TỰ tải URL, không đọc được đường dẫn
  local → suy ra phải có HTTP server nội bộ, và **URL quảng bá cho thiết bị phải là địa chỉ LAN** chứ không phải
  `localhost`. Từ đó mới sinh ra `media_server.py` và hàm `lan_ip()`.
- **Prompt thật của người dùng** (nguyên văn): *"có workinig speaker xác minh luôn tts -> HTTP -> cast chạy thật"* —
  đáng chú ý: người dùng tự viết chuỗi `tts -> HTTP -> cast`. Khi người dùng vẽ được chuỗi mắt xích, hãy
  kiểm chứng **từng mắt** trên phần cứng thật, đừng kiểm chứng cả chuỗi bằng một lần thử.
- **Quyết định chốt:** server MCP kiêm HTTP file server phục vụ cache TTS, cổng riêng (8766). Lưu ý phân biệt
  hai thứ hay bị lẫn: nó **bind `0.0.0.0`** (mọi interface), còn **URL đưa cho thiết bị** thì dựng từ `lan_ip()`.
  Bind rộng là mặt phơi nhiễm — xem mục "Điểm còn hở".

### 2. Chọn thư viện bằng so sánh có tiêu chí, không theo mặc định

- **Nguyên tắc:** với thành phần "chất lượng cảm nhận được" (giọng nói, hình ảnh), người dùng phải nghe/nhìn
  rồi mới chốt — đừng chọn hộ.
- **Cách dựng bài so sánh** (đây mới là phần bắt chước được): tổng hợp **cùng một câu mẫu** qua từng engine,
  cho người dùng nghe lần lượt rồi chốt. Tiêu chí kỹ thuật (API key, chi phí, setup) mình tự chấm được;
  tiêu chí "chất lượng cảm nhận được" thì bắt buộc để người dùng nghe — chọn hộ là sai vai.
- **Việc làm:** so 4 lựa chọn TTS tiếng Việt theo 3 tiêu chí: chất lượng giọng / cần API key không / chi phí.
  gTTS máy móc, Google Cloud TTS cần key + tính phí, Piper offline nhưng yếu và setup nặng, edge-tts tự nhiên
  nhất và miễn phí.
- **Quyết định chốt:** edge-tts, giọng `vi-VN-HoaiMyNeural` / `NamMinhNeural`. Xem `src/googlecast_mcp/tts.py`.

### 3. Thiết kế tool cho AI, không cho người

- **Nguyên tắc:** khi thiếu tham số quan trọng, tool KHÔNG nên đoán và cũng không nên chỉ báo lỗi — hãy trả về
  **dữ liệu để LLM hỏi lại người dùng**. Cách này chạy trên mọi client, không phụ thuộc tính năng elicitation.
- **Prompt thật của người dùng** (nguyên văn, yêu cầu số 3 trong prompt sinh ra cả product):
  *"3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả"* — người dùng nêu HÀNH VI
  mong muốn, không nêu cơ chế. Chính vì thế mình được tự do bỏ elicitation mà vẫn đúng yêu cầu.
- **Việc làm:** `say()` không có `target` → trả danh sách loa + thông điệp gợi ý hỏi lại; không phát gì cả.
  Chấp nhận một tên, nhiều tên cách dấu phẩy, hoặc `all`/`tất cả`. Xem `_select_targets()` trong `server.py`.
- **Quyết định chốt:** bỏ MCP elicitation (nhiều client chưa hỗ trợ), bỏ luôn phương án "mặc định phát tất cả"
  (tác dụng phụ vật lý trong nhà — sai là ồn cả nhà).

### 4. Đo trước, sửa sau — bốn phép đo đáng học thuộc

- **Nguyên tắc:** mỗi triệu chứng mơ hồ đều có một phép đo rẻ tách được "lỗi của tôi" khỏi "lỗi phía kia".
- 🔧 **Loa nháy sáng rồi tắt, không đủ tiếng** → poll `media_controller.status` mỗi giây, in `player_state`,
  `current_time`, `duration`, `idle_reason`. Thấy PLAYING đủ `duration` rồi `FINISHED` ⇒ phía cast không lỗi,
  vấn đề nằm ở thiết bị.
- 🔧 **Không rõ thiết bị có tải được audio không** → monkeypatch `log_message` của HTTP server để in request.
  Tách bạch "cast thất bại" với "không tải nổi file".
- 🔧 **Nghi thiết bị treo** → `nc -z <ip> 8009` TRƯỚC khi đọc code. mDNS trả lời + ping OK vẫn có thể refuse TCP.
- 🔧 **Nghi client kén** → `curl` giả đúng client: kèm `Origin`, `Accept: application/json, text/event-stream`,
  thử cả 3 `protocolVersion`.
- **Prompt thật của người dùng** (nguyên văn, sinh ra phép đo đầu tiên):
  *"khi phát loa working display chi nháy sáng rồi tắt không phát đầy đủ âm thanh"* — chỉ có triệu chứng,
  không có phân tích. Đây là dạng input phổ biến nhất; toàn bộ chẩn đoán là việc của mình.
  Ba prompt còn lại cùng dạng: *"URL must start with 'https'"*, *"mcp này tôi chạy khi kết nối với mcp
  llama-server thì báo lổi: protocal error"*, *"vẫn báo lổi khi kết nối với mcp llama-server"*.

### 5. Danh sách kiểm cho MCP server phục vụ nhiều client (phần tái dùng nhất)

Mỗi mục dưới đây là một ngõ cụt thật đã tốn thời gian. Chi tiết triển khai xem `README.md` mục
"Client configuration" và `docs/architecture.md` mục "Things that bite".

| Triệu chứng | Nguyên nhân thật | Cách xử lý |
|---|---|---|
| `421 Misdirected Request` từ máy khác | SDK MCP chỉ tin `127.0.0.1` (chống DNS-rebinding); bind `0.0.0.0` không đủ | `--allow-host` (README §Troubleshooting). Điều README không nói: phải thêm **cả biến thể scheme `https`** và **cả host không kèm `:port`** |
| Client treo, không báo lỗi gì | nginx buffering nuốt luồng Streamable HTTP | `proxy_buffering off` + `proxy_read_timeout 3600s` |
| Không xin được chứng chỉ TLS | hostname có gạch dưới — CA/B Forum cấm `_` trong dNSName | Đổi sang gạch ngang. Đây là ngõ cụt tuyệt đối, không có đường vòng |
| Claude Desktop không nhận server LAN | custom connector bắt buộc https | Proxy stdio: `npx -y mcp-remote http://... --allow-http` |
| "Failed to fetch (check CORS?)" từ webui | SDK trả `OPTIONS` = 405, không có header CORS; JS chỉ thấy lỗi trống | Bọc `streamable_http_app()` bằng Starlette `CORSMiddleware`; **bắt buộc** `expose_headers=["Mcp-Session-Id"]`. Origin phải khớp CHÍNH XÁC thanh địa chỉ; trang ở cổng 80/443 gửi origin không kèm port |
| mDNS sót thiết bị đã lưu, thông điệp tự mâu thuẫn | discovery lossy | `_connect_saved()`: nối thẳng bằng host/port đã lưu qua `get_chromecast_from_host()` rồi mới quét lại |

**Nguyên tắc bao trùm:** giữ nguyên bảo vệ DNS-rebinding của SDK, chỉ **nới allowlist** — tắt nó là mở cho
web bất kỳ tấn công server nội bộ.

### 6. Vận hành: đừng tin file cấu hình

- **Nguyên tắc:** file unit ≠ tiến trình đang chạy.
- 🔧 `systemctl enable --now` **KHÔNG** restart service đang chạy. Cài lại với cờ mới → unit đổi, tiến trình vẫn
  chạy code+tham số cũ. Ở đây tiến trình cũ sống 3 ngày và làm chẩn đoán lệch hướng nhiều vòng.
- **Việc làm:** dùng `systemctl restart` tường minh; và cho lệnh `status` in `/proc/<MainPID>/cmdline` để thấy
  tham số THẬT. Xem `scripts/service.sh`.
- 🔧 `pkill -f "<pattern>"` khớp luôn chính lệnh bash đang chạy → tự giết shell (exit 144). Lấy PID từ
  `ss -ltnp` rồi kill.

### 7. Kiểm chứng trước khi nhờ người dùng chạy `sudo`

- **Nguyên tắc:** mỗi vòng thử-sai trên máy người dùng đắt hơn nhiều vòng thử trên máy mình.
- **Việc làm:** dựng instance local cùng tham số → `curl` thử → chỉ khi qua mới đưa lệnh triển khai thật.
- **Quyết định chốt:** README ghi **lệnh triển khai đã chạy thật**, kèm giải thích từng cờ ngăn được lỗi nào.

### 8. Đọc prompt của người dùng như tín hiệu chẩn đoán

Toàn phiên chỉ có 21 prompt. Chúng ngắn, tiếng Việt, nhiều lỗi gõ (`lổi`, `reveser`, `workinig`, `làm dao`) —
và không lỗi nào ảnh hưởng kết quả. **Đừng bắt người dùng viết chuẩn; hãy học cách đọc.**

- **Yêu cầu đánh số bằng hành vi là dạng đề bài mạnh nhất.** Prompt #3 sinh ra toàn bộ product và chỉ gồm
  3 gạch đầu dòng mô tả *hành vi mong muốn*, không mô tả giải pháp. Nhờ đánh số mà đối chiếu được từng mục —
  kiểm tra ra MCP lúc đó **mới đạt 1/3**. Nếu người dùng mô tả kỹ thuật thay vì hành vi, sẽ không có thước đo này.
  → Khi nhận đề bài mơ hồ, việc đầu tiên là **quy nó về danh sách hành vi đánh số** rồi tự chấm từng mục.
- **"Vẫn lỗi" lần thứ hai = DỪNG sửa, đi kiểm tra bản sửa đã được nạp chưa.** Prompt #17 và #18 lặp lại
  *"vẫn báo lổi"*; đến vòng #18 mới lộ ra tiến trình cũ đã chạy 3 ngày. Hai vòng trước đó sửa đúng code
  nhưng không ai chạy code đó. Đây là tín hiệu rẻ nhất trong phiên, và tôi đã bỏ lỡ nó một vòng.
- **Câu hỏi tưởng lạc đề có thể là việc gấp nhất.** Prompt #11 (*"tại sau gatewaya khi chạy sudo tôi nhập đúng
  password những vẫn báo sai hoài"*) không liên quan gì MCP — nhưng lần theo thì ra `pam_exec` gọi một binary
  thu thập mật khẩu chạy quyền root. Đừng gạt câu hỏi lạc đề sang bên để "làm cho xong task chính".
- **Ảnh chụp màn hình và log dán vào là dữ liệu hạng nhất.** Prompt #17 kèm ảnh Connection Log; đúng một dòng
  trong ảnh (`Failed to fetch (check CORS?)`) chỉ ra cả hướng sửa. Prompt #18 kèm log dạng text lộ header
  `accept: application/json, text/event-stream` — đủ để dựng lại lệnh `curl` giả client.
- **Hai phát biểu mâu thuẫn về cùng một thiết bị không có nghĩa là hồi quy.** #4 xác nhận "Working display"
  chạy được, #15 báo nó hỏng. Nhờ giữ lịch sử đo (`idle_reason=FINISHED`) mà phân định được: lỗi thiết bị,
  không phải code. → **Lưu lại kết quả đo, không chỉ lưu kết luận.**
- **Người dùng thay đổi môi trường giữa chừng mà không nói rõ.** #19 và #20 mới hé ra client thật chạy ở
  `http://192.168.1.99:8383`. Trước đó mọi giả định về origin đều sai. → Khi lỗi liên quan mạng, hỏi thẳng
  *"client đang chạy ở URL nào, dán nguyên thanh địa chỉ"* — origin phải khớp chính xác, không suy đoán được.

## Kết quả đã xác minh (không phải suy đoán)

Phát tiếng Việt thật, nghe được, trọn thời lượng (`idle_reason=FINISHED`) trên Google Home Mini và Nest Hub;
dò 8 thiết bị, lọc đúng 4 loa; MCP client thật qua `https://google-cast.adrec.cloud/mcp` gọi đủ 13 tool;
client trình duyệt (origin `http://192.168.1.99:8383`) preflight 200 + tools/list 13 tool.
Đang chạy production: systemd trên `192.168.1.128`, cổng 8765 (MCP) / 8766 (audio), nginx + Let's Encrypt.

## Điểm còn hở (ghi trung thực)

- **Không có xác thực ở tầng ứng dụng.** Domain phân giải công khai → ai biết URL cũng phát được tiếng trong nhà.
  Đã đề xuất `allow 192.168.0.0/16; deny all;` trong nginx nhưng **chưa bật**. Đây là việc cần làm tiếp, ưu tiên cao nhất.
- **Mặt phơi nhiễm thứ hai: cổng audio (8766).** `media_server.py` bind `0.0.0.0`, không xác thực, và phục vụ
  **nguyên một thư mục file**. Trong LAN thì chấp nhận được; nếu máy có interface public hoặc ai đó forward cổng
  thì đây là chỗ hở độc lập với endpoint MCP, cần chặn riêng.
- Chưa có unit test; toàn bộ kiểm chứng là thủ công trên phần cứng thật.
- Cache TTS tăng vô hạn, chưa có cơ chế dọn.
- Chưa khôi phục âm lượng/media đang phát sau khi thông báo.

## Bẫy phụ thuộc

Trên PyPI có gói `mcp` 2.0.0 **không liên quan**, layout khác, kéo theo `httpx2` (typosquat) + `mcp-types`.
Giữ pin `mcp[cli]>=1.13,<2` trong `pyproject.toml`. Kiểm nhanh: bản đúng phụ thuộc `httpx`, không phải `httpx2`.
