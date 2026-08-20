# Hướng dẫn sử dụng

Dành cho người đã cài xong (theo `README.md` cùng thư mục) và đã nối được MCP
client. Danh sách 13 tool đầy đủ và **bảng troubleshooting**: xem mục `Tools` và
`Troubleshooting` trong `README.md` ở gốc repo.

## Cách dùng thường ngày

Bạn không gõ lệnh. Bạn nói với trợ lý AI đang nối vào server này:

> "Nói 'Cơm đã chín rồi' ở loa bếp"

Trợ lý gọi tool `say`. Server tổng hợp giọng tiếng Việt, tự phục vụ file audio,
rồi bảo loa tới lấy.

Lần đầu tiên, nếu chưa có loa nào được lưu, hãy bảo trợ lý dò trước: "dò các
loa trong nhà" (`discover_devices`), rồi "liệt kê loa" (`list_speakers`).

## Chọn loa — bốn cách

| Bạn nói | Server hiểu |
|---|---|
| "ở loa bếp" | đúng một loa, khớp tên không phân biệt hoa thường |
| "ở loa bếp và loa phòng làm việc" | nhiều loa, phát song song |
| "ở tất cả các loa" / "all" | mọi loa lẻ |
| *không nói gì về loa* | **không phát gì cả** — server trả danh sách để trợ lý hỏi lại bạn |

Dòng cuối là cố ý. Đoán bừa rồi phát nhầm là làm ồn cả nhà, nên khi không rõ,
server im lặng và hỏi.

Ngoài tên, `target` còn nhận `uuid` của thiết bị.

## "Tất cả" và nhóm loa

Nếu bạn có **nhóm loa** (speaker group) tạo trong app Google Home:

- "tất cả" **cố ý bỏ qua nhóm**, chỉ gửi tới từng loa lẻ. Vì nhóm phát thông
  qua chính các thành viên của nó — gửi tới cả hai thì một loa vật lý nhận hai
  luồng, nghe như vọng/chồng tiếng.
- Nhóm vẫn dùng được bình thường: gọi đích danh tên nhóm ("phát ở nhóm loa gia
  đình").

Điều đáng nhớ: khi bị chồng luồng, API vẫn báo mọi thứ `playing`. **Chỉ nghe
bằng tai mới phát hiện được.** Đừng tin trạng thái API cho loại lỗi này.

## Giọng đọc và tốc độ

- `voice`: `female` (mặc định, `vi-VN-HoaiMyNeural`), `male`
  (`vi-VN-NamMinhNeural`), hoặc một voice id đầy đủ của edge-tts.
- `rate`: `-20%` chậm lại, `+10%` nhanh lên.

Trung thực: giọng `male` và tham số `rate` **chưa được nghe thử lần nào**. Chúng
có trong code và có đường dẫn hợp lệ, nhưng chưa ai xác nhận bằng tai.

## Điều khiển phát

`play`, `pause`, `stop`, `seek`, `set_volume` (0.0–1.0), `set_muted`,
`quit_app`, `get_status`. Ngoài giọng nói, `play_media` phát được URL media bất
kỳ mà thiết bị tự tải về được.

## Bốn tình huống hay gặp

**"Loa nháy đèn rồi tắt, không nghe gì."**
Loa không tải được file. Gần như luôn là tường lửa chặn cổng audio 8766, hoặc
máy chạy server không cùng LAN với loa. Mở cổng 8766 cho LAN.

**"Loa không phản hồi, `wait timed out after 10 s`."**
Thiết bị Cast bị treo — chuyện có thật, đã gặp: mDNS thấy nó, ping được, nhưng
cổng 8009 từ chối kết nối. Kiểm chứng: `nc -z <ip-loa> 8009`. Không thông thì
rút điện loa cắm lại. Đừng nghi code trước khi làm bước này.

**"Vừa sửa xong mà vẫn lỗi y hệt."**
Trước khi sửa tiếp, hãy kiểm tra bản sửa đã thực sự được NẠP chưa:

```bash
./scripts/service.sh status      # in cả dòng lệnh thật của tiến trình đang chạy
```

Cài lại service khi nó đang chạy có thể để nguyên tiến trình cũ với code cũ.

**"Client báo `Failed to fetch (check CORS?)` hoặc lỗi kết nối trống rỗng."**
Client chạy trong trình duyệt thì phải cài lại service với `--cors-origin`
khớp **chính xác** địa chỉ trang. Xem `technical-docs.md`.

## Nên biết

- Nói lại đúng một câu đã nói trước đó thì gần như tức thì — file mp3 được cache
  theo nội dung. Cache **tăng vô hạn**, chưa tự dọn: nằm ở
  `/tmp/googlecast-mcp-tts` (hoặc `GOOGLECAST_MCP_CACHE`), thỉnh thoảng tự xoá.
- Thông báo **không** khôi phục lại nhạc/âm lượng bạn đang nghe trước đó.
- Cần internet cho mỗi câu chưa từng nói (edge-tts là dịch vụ online).
- Danh sách loa lưu ở `~/.googlecast-mcp/speakers.json`, sống qua khởi động lại.
- **Ai truy cập được URL server đều phát được tiếng trong nhà bạn.** Không có
  xác thực. Cân nhắc kỹ trước khi mở ra internet.
