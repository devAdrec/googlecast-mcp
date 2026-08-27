# Sổ tay dùng googlecast-mcp

Dành cho người đã cài xong (`README.md`) và giờ muốn dùng.

Cách dùng thường ngày là **nói với AI bằng tiếng Việt**, AI chọn tool. Bảng
tool dưới đây để tra khi cần biết chính xác nó làm gì.

---

## Việc hay làm nhất: cho loa nói một câu

> "Nói 'Cơm đã chín rồi' ở loa bếp"

AI gọi `say(text="Cơm đã chín rồi", target="Kitchen speaker")`.

**Không nói rõ loa nào thì sẽ bị hỏi lại, và không có tiếng nào phát ra.** Đó
là cố ý, không phải trục trặc: âm thanh đã ra khỏi loa thì không thu lại được,
nên mặc định là *không phát gì* chứ không phải *phát tất cả*.

> "Nói 'Tới giờ đi học rồi' ở tất cả loa"

Nhận cả `all` lẫn `tất cả`. `all` **cố tình bỏ qua nhóm loa** — nhóm phát qua
chính các thành viên của nó, gộp cả hai thì một loa vật lý nhận hai luồng
chồng nhau. Muốn phát vào một nhóm thì gọi thẳng tên nhóm.

Nhiều loa cụ thể: ngăn cách bằng dấu phẩy — `target="Kitchen speaker, Bedroom speaker"`.

## 13 tool

### Nói và tìm loa

| Tool | Làm gì | Tham số đáng chú ý |
|---|---|---|
| `say` | text → giọng nói → phát lên loa | `text`; `target` (tên loa / nhiều tên cách phẩy / `all` / `tất cả`); `voice` = `female` (mặc định) hoặc `male`; `rate` vd `-20%`, `+10%` |
| `discover_devices` | quét mạng tìm thiết bị Cast | `timeout` giây, mặc định 5 |
| `list_speakers` | liệt kê **loa** đã biết (bỏ thiết bị hình ảnh) | tự quét một lần nếu chưa biết gì |
| `list_devices` | liệt kê **mọi** thiết bị đã biết, kể cả TV/Nest Hub | — |

`list_speakers` đọc từ danh sách đã lưu nên trả lời ngay. `discover_devices`
mới thật sự quét mạng — dùng khi vừa thêm loa mới.

### Điều khiển phát

| Tool | Làm gì |
|---|---|
| `play_media` | cast một URL media bất kỳ (loa **tự đi tải** URL đó) |
| `play` / `pause` / `stop` | tiếp tục / tạm dừng / dừng hẳn |
| `seek` | nhảy tới giây thứ N |
| `get_status` | app đang chạy, trạng thái media, âm lượng |
| `set_volume` | đặt mức tuyệt đối 0.0–1.0 (ngoài khoảng thì bị kẹp lại) |
| `set_muted` | tắt / bật tiếng |
| `quit_app` | đóng app, trả thiết bị về màn hình chờ |

`play_media` cần URL mà **loa** với tới được, không phải máy bạn. URL
`localhost` là vô nghĩa với loa.

## Giọng nói

| Chọn | Giọng |
|---|---|
| `female` (mặc định) | `vi-VN-HoaiMyNeural` |
| `male` | `vi-VN-NamMinhNeural` |
| tên đầy đủ bất kỳ | truyền thẳng cho edge-tts, vd `en-US-AriaNeural` |

`rate` chỉnh tốc độ: `rate="-20%"` chậm lại, `rate="+10%"` nhanh lên.

Mỗi tổ hợp (nội dung, giọng, tốc độ) được cache trên đĩa, nên câu lặp lại phát
ngay không phải render lại.

*Giọng nam và tham số `rate` chưa được nghe kiểm bằng tai — chúng chạy, nhưng
chưa ai xác nhận nghe có ổn không.*

## Khi có chuyện

| Thấy gì | Làm gì |
|---|---|
| AI hỏi "phát ở loa nào?" | đúng như thiết kế — trả lời tên loa, hoặc `tất cả` |
| Báo `no_speakers_found` | chạy `discover_devices`. Vẫn không thấy: máy chủ có cùng LAN với loa không? |
| Một loa báo `error`, loa khác vẫn phát | phần tử hỏng được cô lập có chủ đích. Xem `error` của riêng loa đó |
| `wait timed out` với một thiết bị | thiết bị treo. Kiểm `nc -z <ip> 8009`. Khởi động lại thiết bị |
| Màn hình loa nháy sáng rồi tắt, **không có tiếng** | loa không tải được file: cổng audio (8766) chưa mở cho LAN |
| Đổi tên loa trong app Google Home rồi gọi không được | chạy lại `discover_devices` |
| Loa đổi IP | nhánh xử lý này **chưa từng được thử**. Chạy `discover_devices` là cách chắc nhất |

## Nên biết

- **Thông báo cắt ngang nhạc đang phát và không trả lại.** Chưa có chức năng
  khôi phục âm lượng/media cũ.
- **Hai `say` liên tiếp vào một loa**: cái sau cắt cái trước, không xếp hàng.
- **Cache audio không tự dọn.** Thư mục
  `${GOOGLECAST_MCP_CACHE:-/tmp/googlecast-mcp-tts}` chỉ tăng — xoá tay khi cần.
- **Không có xác thực.** Ai tới được cổng đều gọi được tool, kể cả `say`. Nếu
  server đang phơi ra internet, xem mục "Khiếm khuyết còn mở" trong
  `technical-docs.md` trước khi để nguyên như vậy.
- **`say` trả về trước khi loa phát xong** — với clip ngắn, có khi loa đã phát
  xong trước cả lúc lệnh trả về. Trạng thái `get_status` ngay sau đó có thể
  đã là "xong rồi", không phải "đang phát".
