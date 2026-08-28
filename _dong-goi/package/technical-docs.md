---
product: googlecast-mcp
layer: output
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
method_note: "[[method-googlecast-mcp]]"
registry: "[[packages/googlecast-mcp]]"
---

# Kỹ thuật

Kiến trúc đầy đủ và đang sống: [`docs/architecture.md`](../../docs/architecture.md).
File này chỉ ghi những gì tài liệu đó KHÔNG ghi: vì sao chọn thế, đã vấp ở đâu,
và chỗ nào còn hở.

## Bản đồ module

| File | Việc | Điểm cần biết |
|---|---|---|
| `server.py` | 13 tool MCP, `_select_targets()`, `say()` | pychromecast là blocking → mọi tool đẩy qua `asyncio.to_thread` |
| `cast_manager.py` | bọc pychromecast, giữ kết nối | `_connect_saved()` nối thẳng địa chỉ đã lưu khi mDNS sót |
| `speaker_store.py` | lưu bền danh sách thiết bị | gộp theo uuid, ghi-rồi-đổi-tên |
| `tts.py` | edge-tts, cache mp3 | khoá **theo từng vòng lặp**, thử lại 3 lần, dọn file rỗng |
| `media_server.py` | HTTP server phát file cho loa | bind `0.0.0.0`, quảng bá `lan_ip()` — **hai thứ khác nhau** |
| `__main__.py` | CLI, allowlist an ninh, CORS | nới bảo vệ DNS-rebinding thay vì tắt nó |

## Quyết định và lý do

**edge-tts.** Người dùng chọn sau khi so bốn phương án: gTTS (giọng máy móc),
Google Cloud TTS (cần khoá + tính phí), Piper (chạy offline nhưng yếu, setup
nặng), edge-tts (tự nhiên nhất, miễn phí, không cần khoá). Tiêu chí kỹ thuật
thì tự chấm được; tiêu chí **"nghe có tự nhiên không"** bắt buộc để người dùng
nghe. Chỉ một vòng.

**pychromecast: không qua so sánh nào.** Đây là thư viện Python duy nhất còn
được bảo trì cho giao thức Cast. Nguyên tắc chung: thành phần **xương sống**
chọn theo mức bảo trì và độ phủ giao thức; chỉ thành phần **cảm nhận được** mới
đáng đem ra so.

**Ghim `mcp[cli]>=1.13,<2`.** Trên PyPI có gói tên `mcp` phiên bản 2.0.0 hoàn
toàn KHÔNG liên quan, kéo theo `httpx2` (typosquat) và `mcp-types`. Không ghim
là cài nhầm.

**Giữ bảo vệ DNS-rebinding của SDK, chỉ nới allowlist.** Tắt hẳn thì dễ hơn
nhưng mất luôn lớp phòng thủ; `_transport_security()` thêm đúng những địa chỉ
mà server thực sự tới được.

## Bốn mục đã vá trong `tts.py` — ghi là **ĐÃ VÁ**

Chuỗi này đáng đọc vì nó là ví dụ của "sửa mà chưa tới gốc".

1. **Thiếu thử lại** → thêm 3 lần thử có giãn cách. Đo lại: **4/6 đạt, 101s**,
   lỗi `Cannot connect to host`. Thử lại KHÔNG cứu được, vì các lần thử vẫn
   chồng lên nhau — phải chặn ở gốc.
2. **Chưa tuần tự hoá** → thêm khoá. Đo lại: **6/6, 12s**.
3. **Khoá mức module là bẫy.** `asyncio.Lock` mức module chỉ gắn vào vòng lặp
   **KHI CÓ TRANH CHẤP** (đường nhanh của `acquire()` trả về trước khi chạm
   `_get_loop()`), nên lỗi ẩn mãi tới lúc hai render chồng nhau; sau đó mọi
   vòng lặp khác nhận `RuntimeError: bound to a different event loop`. Vá bằng
   **một khoá cho mỗi vòng lặp** (`WeakKeyDictionary`, `tts.py:29-46`). Đo:
   cả hai vòng đều chạy; dồn 6 vẫn **6/6, 6.2s**.
   → Mô tả ban đầu ("chạy `asyncio.run()` hai lần là hỏng") **quá rộng**. Điều
   kiện thật hẹp hơn nhiều, và chỉ đo mới ra.
4. **Đọng file 0 byte** khi `save()` ném lỗi sau khi đã tạo file → bọc
   `try/except` và `unlink` trước mỗi lần thử. Đo: 0 file 0 byte.

## Ngõ cụt đã đi qua

| # | Triệu chứng | Nguyên nhân thật | Vá ở đâu |
|---|---|---|---|
| 1 | `421 Misdirected Request` | SDK chỉ tin `127.0.0.1`; bind `0.0.0.0` không đủ | `__main__.py:46-69` |
| 2 | client treo, không lỗi | nginx buffer body | `proxy_buffering off`, `proxy_read_timeout 3600s` |
| 3 | không xin được chứng chỉ | CA/B Forum cấm `_` trong tên máy → `google_cast.` là ngõ cụt tuyệt đối | đổi thành `google-cast.adrec.cloud` |
| 4 | Claude Desktop không nối được | custom connector chỉ nhận https | bắc cầu `mcp-remote --allow-http` |
| 5 | `Failed to fetch (check CORS?)` | SDK trả `OPTIONS` = **405**, không header CORS; JS chỉ thấy lỗi trống | `CORSMiddleware`, **bắt buộc** `expose_headers=["Mcp-Session-Id"]` (`__main__.py:37`) |
| 6 | sửa xong mà "vẫn lỗi" 3 ngày | `systemctl enable --now` KHÔNG restart service đang chạy | `restart` tường minh + `status` in `/proc/<pid>/cmdline` (`service.sh:78-80,112-115`) |
| 7 | `wait timed out` | thiết bị Cast treo: mDNS + ping OK nhưng TCP 8009 refuse | không phải lỗi code; `nc -z <ip> 8009` rồi khởi động lại thiết bị |
| 8 | `DeviceNotFoundError` tự mâu thuẫn | mDNS sót thiết bị ĐÃ LƯU | `_connect_saved()` (`cast_manager.py:110,124,134`) |
| 9 | một loa nhận hai luồng | `all` gửi tới cả nhóm lẫn thành viên | `all` bỏ `cast_type=group` (`fcf4035`) |
| 10 | `player_state` mãi `UNKNOWN` | trạng thái media là **theo từng kết nối** — hỏi bằng `CastManager` khác cái đã cast thì không thấy | dùng lại đúng kết nối đã cast |
| 11 | `say()` chậm hơn clip | đo `say()` 5.4s trong khi clip chỉ 2.26s → lúc trả về loa đã phát XONG | muốn nghiệm thu phải kiểm `content_id` khớp URL và `duration > 0`, đừng đọc `player_state` |

**Về #7 — bài học suy luận:** đã từng kết luận sai *"Nest Hub bỏ cổng 8009 do
firmware"* chỉ vì CẢ HAI Nest Hub cùng đóng cổng. Hai mẫu trùng nhau không đủ
để suy ra nguyên nhân hệ thống. Khởi động lại thiết bị là hết.

**Về #9 — vì sao nó khó thấy:** kết quả API KHÔNG phân biệt được, cả bốn mục
đều trả `playing`. Dấu vết duy nhất nằm ở siêu dữ liệu — `Family speaker group`
và `Kitchen speaker` cùng `host` 192.168.1.22. Còn lại chỉ nghe mới biết.

## Điểm còn hở — không tô hồng

1. **Không xác thực ở tầng ứng dụng.** `google-cast.adrec.cloud` phân giải
   CÔNG KHAI ra internet. Ai biết URL là gọi được tool, tức là phát được tiếng
   vào nhà.
2. **Cổng audio 8766 bind `0.0.0.0`, không xác thực, phục vụ nguyên thư mục
   cache.** Chặn IP ở nginx CHỈ che được 8765.
   *Phát hiện trong phiên này:* cổng audio mở **lười** — `ss` cho thấy service
   thật đang chỉ nghe 8765, cổng 8766 chưa mở vì chưa `say` lần nào kể từ lần
   khởi động gần nhất. Bề mặt tấn công chỉ xuất hiện sau lần phát đầu tiên;
   quét cổng lúc máy vừa khởi động sẽ KHÔNG thấy nó.
3. **Chặn IP ở nginx: đã đồng ý bật, hai dòng vẫn đang comment.** Còn mở.
4. **Cache TTS tăng vô hạn**, chưa có cơ chế dọn.
5. **Chưa khôi phục âm lượng / nội dung đang phát** sau khi thông báo xong.

## Chưa thử

Giọng nam bằng tai · tham số `rate` bằng tai · service sống sót qua reboot máy
(đã `enable`, chưa reboot) · địa chỉ đã lưu bị cũ vì loa đổi IP → nhánh quét
lại · MCP elicitation trên client thật.
