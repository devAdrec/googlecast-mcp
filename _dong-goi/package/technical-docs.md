# Ghi chú kỹ thuật của gói bàn giao

**Kiến trúc, luồng xử lý và lý do từng module tồn tại: đọc `docs/architecture.md`
trong repo.** Nó là tài liệu đang sống, cập nhật theo mã. Tờ này **không chép lại
nó** — chỉ bổ sung ba thứ nó không chứa:

1. ràng buộc triển khai mà người vận hành phải biết,
2. **bảng khiếm khuyết** — cái nào đã vá, cái nào còn mở,
3. các quyết định kỹ thuật kèm lý do, để người sau đừng "sửa" nhầm chúng.

---

## 1. Ràng buộc gốc, quyết định mọi thứ còn lại

Thiết bị Cast **không phải cái loa để ghi byte vào**. Nó là máy phát nối mạng và
**tự đi tải media qua HTTP**. Hệ quả không tránh được:

- đường dẫn file trên máy là vô nghĩa với nó;
- nên server "nói được" **bắt buộc kiêm luôn HTTP file server**;
- nên nó **bắt buộc nằm cùng LAN với loa**. Không có cách nào lách.

Hai địa chỉ ở đây là **hai thứ khác nhau**, lẫn lộn là hỏng:

| | Giá trị | Ý nghĩa |
|---|---|---|
| Địa chỉ **bind** | `0.0.0.0` (`media_server.py:76`) | nghe trên mọi giao diện mạng |
| Địa chỉ **quảng bá** | `lan_ip()` (`media_server.py:18-31`) | địa chỉ loa dùng để quay lại tải file |

`lan_ip()` mở một UDP socket hướng ra `8.8.8.8` để hỏi kernel *sẽ đi qua giao diện
nào* — không gửi gói tin nào cả. Bind theo địa chỉ quảng bá là sai: máy nhiều
giao diện sẽ mất kết nối từ phía còn lại. Mục eval
`media.binds_wildcard_advertises_lan` giữ đúng bất biến này.

## 2. Bảng khiếm khuyết

### 2.1 ĐÃ VÁ — commit `e6390a5`, có số đo trước/sau

| Khiếm khuyết | Triệu chứng đo được | Cách vá | Số đo sau |
|---|---|---|---|
| **Không thử lại khi dịch vụ TTS từ chối** | gọi dồn 6 yêu cầu → **4/6 đạt, 101 giây**, lỗi `Cannot connect to host` | 3 lần thử, giãn cách 0s/2s/4s **cộng với** `_synthesis_lock` tuần tự hoá (`tts.py:28,78`) | **6/6 đạt, 12 giây** |
| **Đọng file mp3 0 byte** | `save()` tạo file rồi ném lỗi, để lại file rỗng; lần sau cache "trúng" file rỗng → loa phát im lặng vĩnh viễn | bọc `try/except`, `unlink(missing_ok=True)` trước mỗi lần thử (`tts.py:88-97`) | **0 file 0 byte** |

**Bài học đắt nhất của cả product nằm ở ô thứ nhất:** bản vá đầu tiên *chỉ* thêm
thử lại — và vẫn hỏng, vẫn 4/6. Vì các lần thử lại **vẫn chồng lên nhau**: dịch
vụ từ chối kết nối *đến cùng lúc*, nên thử lại đồng thời chỉ là hỏng lại đồng
thời. Phải chặn ở gốc bằng **tuần tự hoá**. Thử lại là băng dán vết thương; nó
không chữa được nguyên nhân là sự chồng lấn.

Cùng chỗ đó có một chi tiết dễ mất khi ai đó "dọn code": sau khi giành được khoá,
`synthesize` **kiểm tra cache lần thứ hai** (`tts.py:80`). Trong lúc mình xếp hàng
chờ, người khác có thể đã render xong đúng câu đó rồi. Bỏ lần kiểm thứ hai là
render lại vô ích. (Xem thêm mục 4 — bộ kiểm hiện *không* thấy được nếu chỉ bỏ
lần kiểm **thứ nhất**.)

### 2.2 CÒN MỞ

| Khiếm khuyết | Mức | Vì sao còn để đó |
|---|---|---|
| **Không có xác thực tầng ứng dụng**, và `google-cast.adrec.cloud` **phân giải công khai ra internet** | cao | Đã có phương án (chặn IP trong nginx: `allow 192.168.0.0/16; deny all;`), đã đồng ý bật, nhưng **hai dòng đó vẫn đang comment**. Ai vào được `/mcp` là phát được tiếng trong nhà. |
| **Cổng audio 8766 bind `0.0.0.0`, không xác thực**, phục vụ nguyên thư mục cache | trung bình | Chặn IP ở nginx **chỉ che 8765**, không che 8766. Ai trong LAN cũng tải được mọi file TTS đã render. |
| **Cache TTS tăng vô hạn** | thấp | Chưa có dọn dẹp. Mỗi câu nói khác nhau là một file ở lại vĩnh viễn. |
| **Không khôi phục nhạc/âm lượng** đang phát sau thông báo | thấp | Chen thông báo vào là mất cái đang nghe. |
| ~~`_synthesis_lock` là `asyncio.Lock` mức module~~ — **ĐÃ VÁ** | — | Đo lại cho thấy mô tả ban đầu quá rộng: khoá **chỉ gắn vào vòng lặp khi thực sự có tranh chấp** (đường nhanh của `Lock.acquire()` trả về trước khi chạm `_get_loop()`). Không tranh chấp thì nhiều `asyncio.run()` vẫn chạy; đã tranh chấp một lần rồi thì vòng lặp sau nhận `RuntimeError: ... is bound to a different event loop`. **Tái hiện được** bằng: vòng 1 chạy 2 render song song → vòng 2 hỏng. Vá bằng **một khoá cho mỗi vòng lặp** (`WeakKeyDictionary`, `tts.py:29-46`). Đo lại: vòng 1 và vòng 2 đều 2 file; dồn 6 yêu cầu vẫn **6/6, 6.2 giây**. |

## 3. Quyết định kỹ thuật — đừng "sửa" nhầm

| Quyết định | Lý do | Sửa đi thì sao |
|---|---|---|
| Pin `mcp[cli]>=1.13,<2` | PyPI có gói **`mcp` 2.0.0 hoàn toàn không liên quan**, kéo theo `httpx2` (typosquat) và `mcp-types` | bỏ pin là mở cửa cho gói giả |
| Giữ bảo vệ DNS-rebinding của SDK, **chỉ nới allowlist** | tắt hẳn là để mọi trang web tấn công được server nội bộ | `entry.trusts_lan_and_proxy_domain` |
| Cho vào allowlist cả `https://` và host **không kèm `:port`** | proxy đứng ở cổng 443 gửi `Host` trần, không có `:port` | thiếu → `421 Misdirected Request` |
| `expose_headers=["Mcp-Session-Id"]` trong CORS | trình duyệt **không đọc được** header không được expose, nên không nối tiếp phiên được | thiếu → client web báo `Failed to fetch`, không nói gì thêm |
| `proxy_buffering off` trong nginx | streamable HTTP giữ response mở và đẩy sự kiện; nginx đệm lại thì **client treo, không có lỗi nào** | triệu chứng câm lặng, cực khó chẩn |
| `service.sh install` dùng `systemctl restart` chứ không `enable --now` | `enable --now` **không khởi động lại** service đang chạy | tiến trình cũ sống tiếp — thực tế đã sống **3 ngày** |
| `service.sh status` in `/proc/<MainPID>/cmdline` | unit file có thể khác hẳn dòng lệnh tiến trình đang chạy | mất cách duy nhất biết bản sửa đã được nạp chưa |
| `say()` truyền thẳng hằng `"audio/mpeg"` (`server.py:134`) | không đi qua bảng MIME của `cast_manager`, vì đầu ra TTS **luôn** là mp3 | đây là **cặp đôi ngầm**: bảng MIME và hằng này không ràng buộc nhau. Mục `say.casts_audio_mpeg` neo kỳ vọng theo **yêu cầu 2**, không theo bảng |
| Thiếu `target` → trả dữ liệu cho LLM hỏi lại, **không** dùng MCP elicitation | elicitation **chưa đo trên client thật** — đây là phán đoán, không phải kết luận | nếu đo được thì nên đổi |
| `all` bỏ nhóm loa (`fcf4035`) | nhóm phát *qua* thành viên → chồng luồng lên một loa vật lý | API vẫn báo `playing` cả 4; chỉ nghe mới biết |

## 4. Giới hạn đã biết của bộ kiểm

Nói rõ ra để đừng ai tin quá mức vào màu xanh:

- **Bỏ riêng lần kiểm cache thứ nhất** (`tts.py:71`) là hồi quy **hiệu năng** mà
  bộ kiểm không thấy — lần kiểm thứ hai sau khoá vẫn trả đúng kết quả. Chỉ khi
  bỏ **cả hai** thì `tts.cache_hit_skips_service` mới đỏ. Đã ghi trong
  `eval/reverse-check.py`.
- **Bỏ `server_close()`** trong `MediaServer.stop()` cũng không thấy được:
  `HTTPServer` đặt `SO_REUSEADDR`, và bỏ tham chiếu thì refcount tự đóng socket.
- Lớp `--online` và `--hardware` **không nằm trong kiểm ngược** — chúng cần dịch
  vụ thật và loa thật. Xem `eval/README.md`.

## 5. Triển khai đang chạy thật

| | |
|---|---|
| Máy | `192.168.1.128`, systemd unit `googlecast-mcp.service` |
| Cổng | MCP `8765`, audio `8766` |
| Reverse proxy | nginx vhost `/etc/nginx/conf.d/adrec_cloud.conf`, Let's Encrypt |
| Tên miền | `google-cast.adrec.cloud` |
| Đang phục vụ | Claude Desktop (máy `.28`) qua https; llama-server webui (máy `.99:8383`) qua LAN |

**Hostname không được chứa dấu gạch dưới.** CA/B Forum cấm `_` trong tên miền
xin chứng chỉ, nên `google_cast.adrec.cloud` **không bao giờ** có https — mà
Claude Desktop lại bắt buộc https. Đó là ngõ cụt tuyệt đối, không phải chuyện
cấu hình sai. Phải đổi tên miền thành `google-cast.adrec.cloud`.
