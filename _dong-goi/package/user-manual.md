---
product: googlecast-mcp
layer: output
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
registry: "[[packages/googlecast-mcp]]"
---

# Hướng dẫn dùng

Cài xong rồi thì bạn không gọi tool bằng tay. Bạn **nói với trợ lý bằng tiếng
Việt**, nó tự chọn tool.

## Nói một câu ra loa

> *"Nói 'Cơm đã chín rồi' ở loa bếp"*

Trợ lý gọi `say(text="Cơm đã chín rồi", target="Kitchen speaker")`. Vài giây
sau loa nói câu đó bằng giọng nữ tiếng Việt.

**Không nói rõ loa nào thì sẽ KHÔNG có gì kêu.** Trợ lý sẽ hỏi lại, kèm danh
sách loa. Đây là cố ý: phát nhầm ra cả nhà là việc không hoàn tác được.

> *"Nói 'Sắp tới giờ họp' ở tất cả loa"* → phát ra mọi loa riêng lẻ.
> *"…ở loa bếp và loa ngủ"* → hai loa.

## Đổi giọng và tốc độ

| Muốn | Nói |
|---|---|
| giọng nam | *"…đọc bằng giọng nam"* (`voice="male"`) |
| chậm lại | *"…đọc chậm lại"* (`rate="-20%"`) |
| nhanh lên | *"…đọc nhanh hơn"* (`rate="+10%"`) |

## Các việc khác

| Muốn | Nói đại ý |
|---|---|
| xem có loa nào | *"liệt kê loa"* |
| quét lại mạng | *"dò lại thiết bị Cast"* |
| xem loa đang phát gì | *"loa bếp đang phát gì"* |
| phát một file/stream | *"phát <URL> ở loa bếp"* |
| tạm dừng / tiếp / dừng hẳn | *"tạm dừng loa bếp"* … |
| nhảy tới phút 1 | *"tua tới giây 60 ở loa bếp"* |
| chỉnh âm lượng | *"đặt âm lượng loa bếp 30%"* |
| tắt/bật tiếng | *"tắt tiếng loa bếp"* |
| trả loa về màn hình chờ | *"thoát ứng dụng trên loa bếp"* |

Tên loa lấy đúng tên bạn đặt trong app Google Home, không phân biệt hoa thường.

## Nhóm loa

Nhóm loa (vd *Family speaker group*) gọi được **theo tên**. Nhưng `"tất cả"`
thì **cố ý bỏ nhóm ra** — nhóm phát qua chính các loa thành viên, gộp cả hai
thì một loa nhận hai luồng chồng nhau. Muốn dùng nhóm thì gọi thẳng tên nhóm.

## Khi thấy lạ

| Thấy | Nghĩa là | Làm gì |
|---|---|---|
| trợ lý hỏi "phát ở loa nào" | bạn chưa chọn loa | trả lời tên loa, hoặc "tất cả" |
| "No Google speaker found" | chưa quét được loa nào | bảo trợ lý *"dò lại thiết bị"*; kiểm máy chạy server có cùng Wi-Fi/LAN với loa không |
| một loa báo lỗi, các loa khác vẫn nói | loa đó không trả lời | thường là thiết bị treo — rút điện cắm lại |
| `wait timed out` | thiết bị Cast treo | khởi động lại thiết bị đó |
| màn hình Nest Hub nháy sáng rồi tắt, không có tiếng | thiết bị treo, không phải lỗi phần mềm | khởi động lại thiết bị |
| lệnh chạy nhưng im lặng | loa đang bị tắt tiếng hoặc âm lượng 0 | *"đặt âm lượng loa bếp 40%"* rồi thử lại |

## Cần biết trước

- **Máy chạy server phải cùng LAN với loa.** Loa tự đi tải file âm thanh ngược
  về máy đó; qua VPN hay mạng khác là không nghe được gì.
- **Cần internet.** Việc chuyển chữ thành tiếng nói dùng dịch vụ trực tuyến.
- **Câu đã đọc được nhớ lại.** Nói lại y hệt một câu thì phát ngay, không phải
  chờ tổng hợp lần nữa.
- **Thông báo xong không tự trả lại nhạc đang nghe.** Đang nghe nhạc mà cho
  loa nói thì phải tự bật nhạc lại.
