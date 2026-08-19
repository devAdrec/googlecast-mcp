# Dùng hằng ngày

Danh sách đầy đủ 13 tool và bảng troubleshooting nằm ở `README.md` gốc
(mục `## Tools`, `## Troubleshooting`). File này chỉ nói kỹ phần người dùng thật sự
chạm vào: nói ra loa, và những gì xảy ra khi nó không kêu.

## Nói một câu ra loa

Trong Claude Desktop hoặc bất kỳ client MCP nào, cứ nói bằng tiếng thường:

> Nói "Cơm đã chín rồi" ở loa bếp

Client tự gọi `say(text="Cơm đã chín rồi", target="Kitchen speaker")`.

Chưa biết có loa nào thì hỏi trước: *"có những loa nào?"* → `list_speakers`.
Lần đầu tiên nó sẽ tự quét mạng, mất vài giây.

## Các dạng `target`

| Viết gì | Nghĩa |
|---|---|
| `Kitchen speaker` | một loa, theo đúng tên hiển thị |
| `Kitchen speaker, Bedroom speaker` | nhiều loa, cách nhau bằng dấu phẩy |
| `all` hoặc `tất cả` | mọi loa lẻ |
| `Family speaker group` | một nhóm loa, gọi đích danh bằng tên |
| *(bỏ trống)* | **không phát gì**; công cụ trả danh sách để client hỏi lại bạn |

**Vì sao `all` không bao gồm nhóm loa.** Nhóm Cast phát thông qua các loa thành viên
của nó. Nếu `all` gửi cả nhóm lẫn từng thành viên thì một loa vật lý nhận hai luồng
cùng lúc — nghe như tiếng vọng hoặc âm chồng lệch pha. Nên `all` chỉ lấy loa lẻ. Muốn
phát qua nhóm thì gọi tên nhóm.

**Cẩn thận với chỗ này khi tự kiểm tra:** trong tình huống chồng luồng, API vẫn báo
`playing` cho mọi thiết bị. Trạng thái không phát hiện được lỗi. Chỉ nghe mới biết.
Đây là lý do không nên coi `status: playing` là bằng chứng đã phát đúng.

## Giọng và tốc độ

```
say(text="...", voice="female")   # mặc định, vi-VN-HoaiMyNeural
say(text="...", voice="male")     # vi-VN-NamMinhNeural
say(text="...", rate="-20%")      # chậm lại
```

Nói thẳng: giọng nam và tham số `rate` **chưa từng được chạy thử lần nào**. Chúng có
trong mã và về nguyên tắc phải chạy được, nhưng chưa ai nghe. Nếu bạn là người đầu
tiên thử, hãy coi đó là thử nghiệm chứ không phải tính năng đã kiểm chứng.

Cần internet: edge-tts tổng hợp giọng trên máy chủ Microsoft. Mất mạng thì `say` hỏng,
còn các tool điều khiển khác vẫn chạy.

## Khi nó không kêu

Theo thứ tự — hầu hết trường hợp dừng ở bước 1 hoặc 2:

1. **Loa có bắt kết nối không?** `nc -z <ip-loa> 8009`. Thiết bị Cast thỉnh thoảng
   treo: mDNS thấy, ping thông, mà cổng 8009 vẫn từ chối. Rút điện cắm lại là hết.
   Làm bước này **trước** khi nghi ngờ phần mềm.
2. **Loa có tải được file audio về không?** Nó phải gọi ngược về máy chủ qua cổng
   8766. Firewall chặn chiều đó thì mọi thứ báo `playing` mà im lặng.
3. **Server có đang chạy đúng tham số không?** `./scripts/service.sh status` và đọc
   dòng `cmdline`. Cài lại mà quên khởi động lại thì tiến trình cũ vẫn chạy cấu hình
   cũ, trông y hệt như đã cài xong.
4. **Đèn nháy rồi tắt ngay, không phát hết câu.** Đã gặp trên Nest Hub. Không phải lỗi
   cast: đó là thiết bị. Kiểm bằng cách phát cùng câu đó lên một loa khác — nếu loa kia
   kêu đủ thì vấn đề nằm ở thiết bị. Giữ lại kết quả các lần đo trước, vì đó là thứ duy
   nhất phân biệt được "thiết bị hỏng" với "code vừa hồi quy".

Còn lại: `## Troubleshooting` trong `README.md` gốc.

## Điều nên biết trước khi mở ra internet

Server **không có xác thực**. Nếu nó nằm sau một tên miền công khai, ai biết URL cũng
phát được tiếng trong nhà bạn. Đây là trạng thái hiện tại của bản triển khai thật,
không phải cảnh báo lý thuyết.
