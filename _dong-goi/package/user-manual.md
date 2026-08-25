# Dùng hằng ngày

Dành cho người đã cài xong (`package/README.md`) và đang chat với một trợ lý AI
có nối `googlecast-mcp`.

## 1. Việc chính: bảo loa nói

Cứ nói bằng tiếng thường. Trợ lý sẽ tự gọi tool `say`.

> "Nói 'Cơm đã chín rồi' ra loa bếp"
>
> "Thông báo tất cả các loa: 15 phút nữa xe tới"
>
> "Đọc câu này ở loa phòng ngủ giọng nam, chậm lại một chút: ..."

**Nếu bạn không nói loa nào, trợ lý sẽ hỏi lại.** Đó là hành vi cố ý: sản phẩm
sẽ **không phát gì cả** khi chưa biết phát ở đâu. Đoán sai là cả nhà nghe.

## 2. Các cách chỉ định loa

| Bạn viết | Nghĩa là |
|---|---|
| `Kitchen speaker` | đúng một loa (không phân biệt hoa/thường) |
| `Kitchen speaker, Bedroom speaker` | nhiều loa, cách nhau dấu phẩy |
| `all` / `tất cả` / `tat ca` / `everyone` / `*` | mọi loa đơn |
| `Family speaker group` | một nhóm loa, gọi đích danh |
| *(bỏ trống)* | trợ lý hỏi lại, không phát gì |
| `f88d1e3f-…` | uuid thiết bị, cũng nhận |

### "tất cả" cố tình BỎ QUA các nhóm loa

Nhóm Cast phát **thông qua** các loa thành viên. Nếu "tất cả" gửi tới cả nhóm
lẫn từng thành viên, một loa vật lý nhận **hai luồng cùng lúc** — nghe như tiếng
vọng chồng lên nhau.

Điều đáng sợ là **API vẫn báo `playing` cho cả bốn đích** — nhìn kết quả trả về
thì không phân biệt được với lần phát đúng. Chỉ nghe mới biết.

Nên: `all` chỉ gửi tới loa đơn. Muốn dùng nhóm thì **gọi tên nhóm**, và khi đó
đừng dùng `all` cùng lúc.

## 3. Giọng và tốc độ

| Tham số | Giá trị | Mặc định |
|---|---|---|
| `voice` | `female`, `male`, hoặc id edge-tts đầy đủ | `female` (`vi-VN-HoaiMyNeural`) |
| `rate` | `-50%` … `+100%` | `+0%` |

Giọng nam là `vi-VN-NamMinhNeural`. **Lưu ý:** giọng nam và tham số `rate` chưa
từng được ai nghe bằng tai để đánh giá — chỉ mới kiểm là "có ra file âm thanh".

Câu giống hệt nhau (cùng giọng, cùng tốc độ) được lấy từ cache, không đọc lại.

## 4. Các tool khác

| Tool | Dùng khi |
|---|---|
| `list_speakers` | xem có những loa nào (đọc danh sách đã lưu, nhanh) |
| `discover_devices` | quét lại mạng — dùng khi vừa thêm loa mới |
| `list_devices` | mọi thiết bị Cast, **kể cả TV và màn hình** |
| `get_status` | đang phát gì, âm lượng bao nhiêu |
| `play_media` | phát một URL bất kỳ (nhạc, video) |
| `play` / `pause` / `stop` / `seek` | điều khiển phát |
| `set_volume` / `set_muted` | âm lượng 0.0–1.0 (giá trị ngoài khoảng bị kẹp lại) |
| `quit_app` | đưa thiết bị về màn hình chờ |

## 5. Lỗi thường gặp

### "Trợ lý hỏi tôi phát ở loa nào mà tôi đã nói rồi"

Tên loa phải khớp tên **friendly name** thật. Hỏi "liệt kê các loa" để xem danh
sách chính xác rồi chép lại.

### Một loa im, các loa khác vẫn nói

Đúng thiết kế: một loa hỏng không kéo đổ cả lượt. Kết quả trả về sẽ ghi
`status: error` riêng cho loa đó. Xem lý do ở dòng `error`.

### `wait timed out` — loa không phản hồi

Gần như luôn là **thiết bị treo**, không phải lỗi phần mềm. Dấu hiệu điển hình:
mDNS thấy nó, ping được, mà cổng 8009 từ chối kết nối.

```bash
nc -z <ip-của-loa> 8009
```

Không thông → rút điện loa 10 giây rồi cắm lại. Đã gặp: một Nest Hub hỏng **3
lần liên tiếp trong 2 ngày**, khởi động lại là hết hẳn.

### Loa nháy sáng rồi tắt, không phát hết câu

Thiết bị nhận được media nhưng ngắt giữa chừng. Kiểm: máy chạy server có còn
cùng LAN với loa không, và cổng audio (8766) có bị firewall chặn không — loa
phải **tải ngược** file từ máy đó.

### Trợ lý báo mất kết nối MCP

```bash
./scripts/service.sh status     # đọc kỹ dòng "Running command line"
./scripts/service.sh restart
./scripts/service.sh logs
```

Dòng "Running command line" quan trọng: **file cấu hình có thể đã đổi mà tiến
trình đang chạy thì chưa.**

### Vừa sửa cấu hình mà "vẫn lỗi y hệt"

Trước khi sửa tiếp, hãy kiểm **bản sửa đã thật sự được nạp chưa**. Lỗi lặp lại
không đổi một chữ thường là dấu hiệu bạn đang sửa thứ chưa chạy — không phải
dấu hiệu bạn sửa sai chỗ.

## 6. Điều nên biết trước khi mở ra internet

Sản phẩm này **không có xác thực ở tầng ứng dụng**. Ai gọi được endpoint là phát
được tiếng vào nhà bạn. Cổng audio 8766 còn phục vụ nguyên thư mục cache TTS
cho bất kỳ ai trong LAN. Xem `technical-docs.md` mục 6 trước khi phơi ra ngoài.
