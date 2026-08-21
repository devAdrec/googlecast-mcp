# Dùng hằng ngày

Dành cho người đã cài xong (theo `README.md` trong thư mục này) và giờ chỉ muốn
sai loa nói.

## Nói một câu

Bạn không gõ lệnh. Bạn nói với Claude bằng tiếng thường:

> Nói "Cơm đã chín rồi" ở loa bếp

Claude sẽ gọi tool `say`. Nếu bạn **không** nói loa nào:

> Nói "Cơm đã chín rồi"

thì **không có tiếng nào phát ra**. Tool trả về danh sách loa và Claude quay lại
hỏi bạn "phát ở loa nào?". Đây là hành vi cố ý: phát nhầm ra tiếng trong nhà là
việc không rút lại được.

## Các cách chỉ định loa

| Bạn nói | Kết quả |
|---|---|
| `loa bếp` (một tên) | chỉ loa đó |
| `loa bếp, loa phòng ngủ` | cả hai, phát song song, cùng một file âm thanh |
| `tất cả` / `all` / `everyone` / `*` | mọi loa lẻ |
| tên một **nhóm loa** | phát qua nhóm đó |

**Điều đáng biết về "tất cả":** nó cố ý **bỏ qua các nhóm loa**. Một nhóm phát
thông qua chính các thành viên của nó, nên nếu gửi cả nhóm lẫn thành viên thì
một cái loa vật lý nhận hai luồng âm thanh cùng lúc — nghe méo, chồng tiếng.
Nhóm vẫn phát được bình thường nếu bạn **gọi đích danh tên nhóm**.

Đây là lỗi từng có thật, và đáng nhớ vì lý do khác: **cả bốn thiết bị đều báo
`playing`, API hoàn toàn không phát hiện được gì bất thường.** Chỉ có tai người
mới biết. Việc gì có tác dụng ra thế giới vật lý thì trạng thái API xanh không
phải là bằng chứng nó đúng.

## Giọng và tốc độ

| Muốn | Nói thêm |
|---|---|
| giọng nữ (mặc định) | không cần nói gì |
| giọng nam | "giọng nam" — `vi-VN-NamMinhNeural` |
| đọc chậm lại | "chậm hơn" — tương ứng `rate="-20%"` |
| đọc nhanh lên | "nhanh hơn" — `rate="+10%"` |

> Giọng nam và tham số tốc độ **chưa được nghe kiểm chứng bằng tai**. Chúng có
> tổng hợp ra file mp3 khác rỗng (bộ eval `--online` xác nhận), nhưng chưa ai
> ngồi nghe xem có tự nhiên không.

## Các tool khác

Ngoài `say` còn 12 tool nữa: `discover_devices`, `list_speakers`,
`list_devices`, `get_status`, `play_media`, `play`, `pause`, `stop`, `seek`,
`set_volume`, `set_muted`, `quit_app`. Mô tả đầy đủ ở mục **Tools** trong
`README.md` gốc repo.

Vài câu hay dùng:

> Có những loa nào trong nhà? → `list_speakers`
> Dò lại thiết bị đi → `discover_devices`
> Loa bếp đang phát gì? → `get_status`
> Tắt loa phòng ngủ đi → `stop`
> Vặn loa bếp xuống 30% → `set_volume`

## Khi trục trặc

| Triệu chứng | Nghĩ tới điều này trước |
|---|---|
| "Không thấy loa nào" | Server có **cùng LAN với loa** không? Dò dùng mDNS, không qua được router. Bảo Claude `discover_devices` một lần. |
| Một loa cụ thể không phát, các loa khác vẫn ổn | Thiết bị treo. Kiểm `nc -z <ip-loa> 8009`. Refuse thì **khởi động lại cái loa** — không phải lỗi phần mềm. Từng mất 3 lần thử rải 2 ngày mới ra. |
| Loa nháy sáng rồi tắt, không phát hết câu | Loa không tải được file âm thanh. Kiểm cổng media (8766) có bị tường lửa chặn không. |
| Claude nói đã phát mà nhà im lặng | Xem `audio_url` trong kết quả rồi thử `curl` chính URL đó từ một máy khác. Tải được thì lỗi ở loa, không tải được thì lỗi ở mạng/cổng. |
| Client không kết nối được | Xem bảng mã lỗi trong `technical-docs.md` mục 7. |
| Đã sửa mà lỗi y hệt như cũ | **Dừng sửa.** Nhiều khả năng tiến trình cũ chưa được nạp lại: `./scripts/service.sh status`, đọc dòng lệnh thật in ra từ `/proc`. |

Phần troubleshooting đầy đủ hơn: mục **Troubleshooting** trong `README.md` gốc
repo.

## Nên biết trước khi dùng thật

- **Ai tới được endpoint là điều khiển được loa nhà bạn.** Không có xác thực ở
  tầng ứng dụng. Nếu đã mở ra tên miền công khai thì hãy chặn IP ở nginx.
- Thư mục cache âm thanh chỉ tăng dần, chưa tự dọn. Thỉnh thoảng xoá tay.
- Thông báo chen ngang sẽ **không** khôi phục lại nhạc đang nghe dở.
