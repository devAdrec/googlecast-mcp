# Dùng googlecast-mcp hằng ngày

Cài đặt: `README.md` trong gói này. Tờ này là lúc mọi thứ đã chạy.

## Việc thường làm nhất

Nói với Claude bằng tiếng Việt bình thường:

> *"Nói ở loa bếp: cơm đã chín rồi"*
> *"Báo tất cả các loa: 5 phút nữa đi học"*
> *"Có những loa nào trong nhà?"*

Claude tự chọn tool. Không cần nhớ tên tool.

## Nếu không nói rõ loa

Server **sẽ không phát gì cả**. Nó trả về danh sách loa và nhờ client hỏi lại
bạn. Đây là cố ý: phát tiếng ra loa là việc **không hoàn tác được** trong nhà
người khác, nên im lặng là mặc định an toàn.

Trả lời bằng: một tên loa, nhiều tên cách nhau bằng phẩy, hoặc `tất cả`.

## Bảng tool

| Tool | Làm gì |
|---|---|
| `say(text, target?, voice, rate)` | **Nói thành tiếng.** Bỏ `target` → hỏi lại, không phát. |
| `discover_devices(timeout=5.0)` | Quét mạng và lưu lại thiết bị. |
| `list_speakers()` | Chỉ loa và nhóm loa (không TV). Tự quét nếu chưa có gì. |
| `list_devices()` | Mọi thiết bị đã biết. |
| `get_status(target)` | Đang phát gì, âm lượng bao nhiêu. |
| `play_media(target, url, content_type?, title?)` | Phát một URL media. |
| `play` / `pause` / `stop` (target) | Điều khiển phát. |
| `seek(target, position_seconds)` | Nhảy tới vị trí. |
| `set_volume(target, level)` | Âm lượng 0.0–1.0 (tự kẹp về khoảng này). |
| `set_muted(target, muted)` | Tắt / bật tiếng. |
| `quit_app(target)` | Thoát app, trả thiết bị về màn hình chờ. |

`target` là **tên thân thiện** của thiết bị (ví dụ `"Kitchen speaker"`) hoặc
`uuid` của nó.

## Chi tiết đáng biết về `say`

- **Giọng**: `voice="female"` (`vi-VN-HoaiMyNeural`, mặc định) hoặc `"male"`
  (`vi-VN-NamMinhNeural`), hoặc bất kỳ id giọng edge-tts nào.
- **Tốc độ**: `rate="-20%"` chậm lại, `"+10%"` nhanh lên.
- **`tất cả`** chỉ phát ra **từng loa riêng lẻ**, cố ý bỏ qua nhóm loa. Nhóm loa
  phát *qua* thành viên của nó, nên gửi cả hai sẽ khiến một loa nhận hai luồng.
  Muốn dùng nhóm thì **gọi thẳng tên nhóm**.
- **Câu lặp lại là tức thì**: đã render một lần thì lần sau lấy từ cache.
- **Cần internet** để render giọng (dịch vụ neural của Microsoft, không cần key).
- Một loa chết **không kéo đổ** cả lệnh: các loa còn lại vẫn phát, loa hỏng được
  báo riêng trong `results`.

## Vận hành service

```bash
./scripts/service.sh status      # đang chạy không, và chạy bằng dòng lệnh nào
./scripts/service.sh logs        # theo dõi journal
./scripts/service.sh restart     # nạp lại sau khi sửa
./scripts/service.sh remove      # gỡ hẳn
```

**Luôn dùng `status` sau khi đổi bất cứ thứ gì**, và đọc dòng
*"Running command line"*. Unit file có thể đã đúng trong khi tiến trình đang chạy
vẫn là bản cũ — chuyện này từng kéo dài **ba ngày**.

## Chẩn lỗi

| Triệu chứng | Nguyên nhân và cách xử |
|---|---|
| `say` trả `needs_speaker_selection` | Đúng như thiết kế: bạn chưa chọn loa, nên chưa phát gì. |
| Không tìm thấy loa nào | Server không cùng LAN với loa, hoặc mDNS bị chặn giữa các VLAN. |
| `Execution of wait timed out after 10 s` cho **một** thiết bị | Thiết bị đó không nhận kết nối cast. Kiểm `nc -z <ip> 8009` **trước khi** nghi ngờ code. Nest Hub ở trạng thái này thường **khởi động lại là hết**. |
| Loa nhận lệnh nhưng im lặng | Nó không với tới được cổng audio. Kiểm firewall, và kiểm URL quảng bá có phải địa chỉ LAN không. |
| Màn hình loé rồi tắt, âm thanh cụt | Gọi `get_status` liên tục trong lúc phát. Nếu `player_state=PLAYING` đủ `duration` rồi kết thúc bằng `idle_reason=FINISHED` thì **phía cast không có lỗi** — nghi thiết bị (âm lượng, hoặc trạng thái không ổn định sau khi restart). |
| Mở `/mcp` bằng trình duyệt ra `Not Acceptable: Client must accept text/event-stream` | **Bình thường.** Endpoint không phải để duyệt web; câu trả lời này chứng tỏ server đang khoẻ. |
| `421 Misdirected Request` | `Host` chưa được tin. Thêm bằng `--allow-host <tên>`. |
| Client nối được nhưng gọi thì treo | Có proxy đang đệm. Đặt `proxy_buffering off`. |
| Client báo "protocol error" chung chung | Nó không đọc được khung SSE hoặc không mang session header. Chạy server với `--json-response --stateless`. |
| Client trình duyệt báo `Failed to fetch (check CORS?)` | Thiếu `--cors-origin`. Giá trị phải **khớp chính xác thanh địa chỉ** — scheme, host, port, không path. Trang chạy ở cổng 80/443 gửi origin **không kèm cổng**. |

## Điều nên biết về an toàn

Endpoint **không có xác thực**. Ai với tới `/mcp` là phát được tiếng trong nhà
bạn. Nếu tên miền phân giải công khai ra internet, hãy chặn trong nginx:

```nginx
allow 192.168.0.0/16;
deny all;
```

Và nhớ: dòng đó **chỉ che cổng MCP 8765**. Cổng audio **8766** vẫn mở cho cả LAN.
