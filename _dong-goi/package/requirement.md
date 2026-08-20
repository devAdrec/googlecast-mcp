# Yêu cầu gốc và tiêu chí chấp nhận

## Ba yêu cầu, nguyên văn của người đặt hàng

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba dòng này là toàn bộ đặc tả sản phẩm. Chúng được giữ nguyên văn ở đây, kể cả
lỗi gõ, vì đây là bản gốc để đối chiếu — mọi diễn giải đẹp đẽ hơn đều là suy
đoán của người viết tài liệu, không phải yêu cầu.

Điều làm ba dòng này dùng được: chúng **đánh số**, **nói bằng hành vi quan sát
được**, và **đối chiếu được từng dòng**. Lần đối chiếu đầu tiên cho kết quả
1/3 đạt — chính vì đối chiếu được nên mới biết là 1/3.

## Tiêu chí chấp nhận

### YC1 — Dò và lưu loa

| # | Tiêu chí | Kiểm ở đâu |
|---|---|---|
| 1.1 | Dò được thiết bị Google Cast trong LAN qua mDNS | tầng `--hardware` của eval; đo thật: 8 thiết bị |
| 1.2 | Phân biệt **loa** (`cast_type` = `audio`, `group`) với thiết bị hình ảnh (`cast`) | eval offline: `is_speaker: *` |
| 1.3 | Danh sách được lưu bền, tiến trình mới không cần quét lại | `~/.googlecast-mcp/speakers.json`; ghi kiểu write-then-rename |
| 1.4 | Một lần mDNS sót thiết bị không được làm hỏng lệnh | `_connect_saved()` nối thẳng bằng địa chỉ đã lưu |

### YC2 — Text tiếng Việt → tiếng nói → phát ra loa

| # | Tiêu chí | Kiểm ở đâu |
|---|---|---|
| 2.1 | Nhận text tiếng Việt làm tham số, đọc bằng giọng tiếng Việt tự nhiên | `vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural` |
| 2.2 | Tổng hợp ra file audio khác rỗng | eval `--online`: `tts online: produced a non-empty mp3` |
| 2.3 | Loa phát ĐỦ độ dài, không chỉ nháy đèn rồi tắt | đo thật 3 clip 2.09 / 4.27 / 7.10 s, đều tới `idle_reason=FINISHED` |
| 2.4 | Text rỗng bị từ chối trước khi có bất kỳ tác dụng phụ nào | eval offline: `tts: empty text raises ValueError` |
| 2.5 | Một loa hỏng không làm hỏng các loa còn lại | eval offline: `failure isolation: *` |

### YC3 — Không chọn loa thì phải HỎI, không được tự phát

Đây là yêu cầu có hệ quả vật lý: đoán sai là ồn cả nhà. Nên nó được diễn giải
chặt nhất.

| # | Tiêu chí | Kiểm ở đâu |
|---|---|---|
| 3.1 | Thiếu tham số chọn loa → trả `needs_speaker_selection` kèm danh sách loa | eval offline |
| 3.2 | Thiếu tham số chọn loa → **KHÔNG tổng hợp giọng, KHÔNG cast** | eval offline: `does NOT synthesize`, `does NOT cast` |
| 3.3 | Không có loa nào trong mạng → trả `no_speakers_found`, thông điệp khác hẳn | eval offline |
| 3.4 | Chấp nhận: một tên, nhiều tên cách phẩy, `all` / `tất cả` | eval offline |
| 3.5 | `all` **không** gửi tới cả nhóm loa lẫn thành viên của nhóm | eval offline: `all: no speaker group included` |
| 3.6 | Nhóm loa vẫn gọi được khi nêu đích danh tên | eval offline: `group by name: still reachable` |

3.5 không có trong yêu cầu gốc. Nó sinh ra từ một lỗi đo được: nhóm loa phát
QUA các thành viên, nên `all` gồm cả hai sẽ đẩy hai luồng vào cùng một loa vật
lý — mà API vẫn báo `playing` cho tất cả. Chỉ tai người mới phát hiện được.

## Cách thực hiện yêu cầu 3 — và hai phương án đã bị loại

- **MCP elicitation** (giao thức có sẵn cơ chế hỏi lại người dùng): loại, vì
  nhiều client chưa hỗ trợ. Người dùng nào dùng client đó sẽ bị kẹt.
- **Mặc định phát ra tất cả loa**: loại, vì tác dụng phụ vật lý — sai một lần là
  ồn cả nhà.
- **Đã chọn**: trả về dữ liệu có cấu trúc (`status`, `speakers`, `message`) để
  chính LLM đang gọi tool hỏi lại người dùng. Hoạt động trên mọi client.

## Ngoài phạm vi (biết mà chưa làm)

- Không có xác thực ở tầng ứng dụng.
- Cache TTS tăng vô hạn, chưa có cơ chế dọn.
- Chưa khôi phục âm lượng / nội dung đang phát sau khi chen thông báo vào.
