# Ghi chú kỹ thuật của gói bàn giao

**Nguồn chuẩn về kiến trúc là `docs/architecture.md` trong repo.** Đó là tài
liệu đang sống, đi cùng mã. File này không chép lại nó — chỉ bổ sung hai thứ
mà tài liệu kiến trúc không mang: **ràng buộc triển khai** khi đưa vào chạy
thật, và **bảng khiếm khuyết** (đã vá / còn mở).

Đọc `docs/architecture.md` trước để hiểu luồng `say() → tts → media server →
loa tự tải về`. Rồi quay lại đây.

---

## Ràng buộc kiến trúc không thể thương lượng

**Thiết bị Cast tự đi tải media qua HTTP.** Nó không phải cái loa mà ta ghi
byte vào; nó là trình phát nối mạng, nhận một URL rồi tự mở kết nối đi lấy.
Từ một sự thật đó suy ra tất cả:

1. Đường dẫn file cục bộ vô nghĩa với loa.
2. Server "nói được" **bắt buộc kiêm HTTP file server**. Không có cách bỏ.
3. Cổng audio phải tới được **từ phía loa**, không chỉ từ phía client MCP.
4. Cast "thành công" mà loa im lặng là chuyện bình thường: lệnh đã tới, việc
   tải file mới hỏng. Muốn biết loa có thật sự phát không thì phải hỏi lại
   trạng thái media, hoặc nghe.

Hệ quả trong mã: `media_server.py:76` bind `0.0.0.0`, còn URL quảng bá dựng từ
`lan_ip()`. **Hai thứ này KHÁC NHAU** và cố tình khác nhau — bind rộng để đến
được từ mọi giao diện mạng, quảng bá hẹp để loa biết đường về. Lẫn hai thứ là
một lớp lỗi riêng.

## Ràng buộc triển khai

| Ràng buộc | Vì sao | Hỏng thì thấy gì |
|---|---|---|
| Máy chạy server phải **cùng LAN với loa** | mDNS không qua router; loa phải với ngược về được | không dò thấy gì, hoặc dò thấy mà không có tiếng |
| **Hai cổng** phải mở: MCP (8765) và audio (8766) | loa tải file từ cổng audio | "màn hình nháy sáng rồi tắt" |
| Ghim cổng audio (`--media-port` / `GOOGLECAST_MCP_MEDIA_PORT`) | cổng 0 chọn cổng ngẫu nhiên, không viết nổi luật tường lửa | luật tường lửa lúc đúng lúc sai |
| `--allow-host <domain>` khi đứng sau proxy | SDK chỉ tin loopback; đây là bảo vệ chống DNS-rebinding | `421 Misdirected Request` |
| `--cors-origin <origin>` cho client trình duyệt | SDK không sinh phản hồi CORS; `OPTIONS` trả 405 | `Failed to fetch (check CORS?)`, JS chỉ thấy lỗi trống |
| `expose_headers=["Mcp-Session-Id"]` (`__main__.py:37`) | trình duyệt không đọc được header không được lộ ra ⇒ không nối tiếp được phiên | phiên đầu tiên chạy, các lời gọi sau hỏng |
| `proxy_buffering off` + `proxy_read_timeout 3600s` | luồng SSE bị nginx gom lại | **client treo, không lỗi gì cả** — triệu chứng khó nhất |
| Tên miền HTTPS **không có gạch dưới** | CA/B Forum cấm ký chứng chỉ cho tên chứa `_` | không xin nổi chứng chỉ; ngõ cụt tuyệt đối, không có cách vòng |
| Claude Desktop custom connector chỉ nhận `https` | quy định của client | `URL must start with 'https'` → bắc cầu `mcp-remote --allow-http` |
| Ghim `mcp[cli]>=1.13,<2` | trên PyPI có gói `mcp` 2.0.0 KHÔNG liên quan, kéo `httpx2` + `mcp-types` | import lỗi kỳ quặc; kiểm bằng "phải cần `httpx`, không phải `httpx2`" |
| `service.sh install` dùng `restart` tường minh | `systemctl enable --now` **không** khởi động lại service đang chạy | tiến trình cũ sống tiếp — lần đầu gặp là **3 ngày** trước khi phát hiện |

`service.sh status` in `/proc/<MainPID>/cmdline` (`service.sh:78-80,112-115`)
chính là để trả lời câu hỏi "bản sửa đã được nạp chưa" mà không phải đoán.

## Quyết định thiết kế và lý do

| Quyết định | Lý do | Đã so sánh? |
|---|---|---|
| **edge-tts** cho TTS | tự nhiên nhất trong các lựa chọn miễn phí, không cần API key | **Có**, một vòng, 4 phương án: gTTS (giọng máy móc), Google Cloud TTS (cần key + phí), Piper (offline nhưng yếu, setup nặng), edge-tts (thắng) |
| **pychromecast** cho giao thức Cast | thư viện Python duy nhất còn được bảo trì phủ giao thức Cast | **Không** — và cố ý không |
| Thiếu loa đích → trả dữ liệu cho LLM hỏi lại | tác dụng phụ vật lý không hoàn tác được | không dùng MCP elicitation: **CHƯA THỬ trên client nào**, đây là phán đoán |
| Lưu bền danh sách thiết bị ra đĩa | mDNS lossy, discovery chậm | — |
| Giữ bảo vệ DNS-rebinding của SDK, chỉ **nới allowlist** | tắt hẳn là mở cho web bất kỳ tấn công server nội bộ | — |
| `all` bỏ nhóm loa (`fcf4035`) | nhóm phát QUA thành viên ⇒ gộp cả hai là chồng luồng | — |

**Nguyên tắc rút ra từ hai dòng đầu:** thành phần *cảm nhận được* (giọng nói)
phải so sánh, và tiêu chí cảm nhận bắt buộc để người dùng nghe — máy không tự
chấm được "nghe có tự nhiên không". Thành phần *xương sống* (giao thức) chọn
theo mức bảo trì và độ phủ giao thức; so sánh cho vui không đổi được kết luận
khi chỉ có một lựa chọn sống.

## Khiếm khuyết — ĐÃ VÁ

Ghi lại vì cách vá quan trọng hơn bản vá.

| # | Khiếm khuyết | Cách vá | Đo được |
|---|---|---|---|
| 1 | TTS hỏng khi nhiều yêu cầu cùng lúc | thêm 3 lần thử giãn cách | **4/6 đạt, 101s** — *không đủ* |
| 2 | Thử lại vẫn chồng nhau nên vẫn bị từ chối kết nối | **tuần tự hoá** bằng khoá | **6/6, 12s** |
| 3 | Khoá mức module gắn nhầm vòng lặp | **một khoá cho mỗi vòng lặp** (`WeakKeyDictionary`, `tts.py:29-46`) | dồn 6: **6/6, 6.2s**; cả hai vòng lặp đều chạy |
| 4 | Đọng file 0 byte khi `save()` ném lỗi | bọc `try/except`, `unlink` trước mỗi lần thử | **0 file 0 byte** |
| 5 | `421 Misdirected Request` với client ở xa | nới allowlist (`__main__.py:46-69`) | client thật qua LAN và qua HTTPS đều gọi được |
| 6 | Client trình duyệt "Failed to fetch" | `CORSMiddleware` + `expose_headers` | preflight 200, 13 tool |
| 7 | Cài lại service không đổi tiến trình | `restart` tường minh + `status` in cmdline | — |
| 8 | mDNS sót thiết bị đã lưu → `DeviceNotFoundError` tự mâu thuẫn | `_connect_saved()` (`cast_manager.py:110,124,134`) | — |
| 9 | `target="all"` chồng luồng lên nhóm loa | `fcf4035`: `all` bỏ `cast_type=group` | trước: 4 `playing` nhưng chồng luồng; sau: 3 loa riêng lẻ |

### Bài học từ #1→#2→#3

**Thử lại không cứu được khi các lần thử vẫn chồng lên nhau; phải chặn ở gốc.**
Bản vá #1 hợp lý về mặt suy luận và *sai* về mặt đo đạc — chỉ có con số 4/6
mới cho biết điều đó.

**#3 còn dạy một điều khác về cách mô tả lỗi.** Mô tả ban đầu là "chạy
`asyncio.run()` hai lần là hỏng". Mô tả đó **quá rộng**: `asyncio.Lock` mức
module chỉ tự gắn vào vòng lặp **khi thực sự có tranh chấp** — đường nhanh của
`Lock.acquire()` trả về trước khi chạm `_get_loop()`. Điều kiện thật là *vòng
lặp thứ nhất có hai render chồng nhau*. Ghi mô tả rộng vào tài liệu thì người
sau sẽ đi tìm sai chỗ.

## Khiếm khuyết — CÒN MỞ

Không tô hồng. Ai nhận bàn giao cần biết chính xác mình đang nhận gì.

| # | Còn mở | Mức | Chi tiết |
|---|---|---|---|
| A | **Không xác thực ở tầng ứng dụng** | cao | `google-cast.adrec.cloud` phân giải CÔNG KHAI ra internet. Ai tới được cổng đều gọi được tool — kể cả `say` |
| B | **Cổng audio 8766 bind `0.0.0.0`, không xác thực** | cao | phục vụ nguyên thư mục cache. Chặn IP ở nginx **chỉ che 8765**, không che 8766 |
| C | Chặn IP nginx đã đồng ý bật nhưng **hai dòng vẫn đang comment** | trung bình | việc treo, chưa làm |
| D | Cache TTS tăng vô hạn | thấp | chưa có cơ chế dọn |
| E | Chưa khôi phục âm lượng/media đang phát sau thông báo | thấp | thông báo cắt ngang nhạc đang nghe và không trả lại |

A và B cộng lại: một endpoint công khai, không xác thực, phát được âm thanh
vào nhà. Đây là điều đầu tiên phải xử lý nếu product đi xa hơn phạm vi hiện tại.

## Điều CHƯA THỬ

Khác với "còn mở" — đây là chỗ chưa có dữ liệu, không phải chỗ đã biết là thiếu.

- Giọng nam `vi-VN-NamMinhNeural` **bằng tai**.
- Tham số `rate` **bằng tai**.
- Service sống sót qua **reboot máy** (đã `enable`, chưa reboot bao giờ).
- Nhánh quét lại khi **loa đổi IP** làm địa chỉ đã lưu bị cũ.
- **MCP elicitation** trên client thật — quyết định không dùng nó là phán đoán,
  chưa đo client nào.

## Bẫy vận hành

| Bẫy | Thoát bằng |
|---|---|
| Thiết bị Cast treo: mDNS + ping OK nhưng TCP 8009 **refuse** | `nc -z <ip> 8009` **trước** khi nghi mã. Khởi động lại thiết bị là hết |
| `pkill -f "<mẫu>"` khớp luôn lệnh bash đang chạy → tự giết shell (exit 144) | thu hẹp mẫu, hoặc dùng PID |
| Trạng thái media là **theo từng kết nối** | hỏi một `CastManager` khác cái đã cast thì nó báo `UNKNOWN` mãi |
| `say()` trả về **sau khi** clip đã phát xong | đo được: `say()` 5.4s, clip 2.26s. Đòi thấy `PLAYING` là đòi trạng thái đã hết hạn. Kiểm `content_id` khớp URL + `duration > 0` |

### Một bài học suy luận, ghi lại vì suýt thành kết luận sai

Từng kết luận "Nest Hub bỏ cổng 8009 do firmware" chỉ vì **cả hai** Nest Hub
trong nhà cùng đóng cổng đó. Khởi động lại thiết bị là hết — không có chuyện
firmware nào cả. **Hai mẫu trùng nhau không đủ để suy ra nguyên nhân hệ
thống.** Hai thiết bị cùng model, cùng mạng, cùng lịch cập nhật thì trùng nhau
là chuyện tất nhiên, không phải bằng chứng.

## Đối chiếu mã ↔ yêu cầu

| Module | Việc | Yêu cầu phục vụ |
|---|---|---|
| `cast_manager.py` | dò, phân giải, điều khiển thiết bị (bọc pychromecast) | YC1 |
| `speaker_store.py` | lưu bền, gộp theo uuid, lọc loa khỏi thiết bị hình ảnh | YC1 |
| `tts.py` | edge-tts → mp3, cache theo nội dung, tuần tự hoá, thử lại | YC2 |
| `media_server.py` | phục vụ thư mục cache trên LAN, dựng URL loa với tới được | YC2 |
| `server.py` | 13 tool MCP; `say()` và `_select_targets()` | YC2, YC3 |
| `__main__.py` | chọn transport, nới allowlist, CORS | 4.2–4.4 |
| `scripts/service.sh` | vòng đời systemd | 4.1 |

`cast_manager.py` là module duy nhất được **giữ nguyên** từ scaffold ban đầu:
nó đã làm đúng việc của nó. Bốn module còn lại sinh ra từ chỗ đối chiếu ba
yêu cầu gốc và thấy đạt 1/3.
