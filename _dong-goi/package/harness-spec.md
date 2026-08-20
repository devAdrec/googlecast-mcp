# Harness spec — googlecast-mcp

Loại: **harness vận hành** (máy móc, kết quả xác định — cùng đầu vào cho cùng
đầu ra, không phải AI sinh nội dung). Trọng số vì thế dồn về lớp Execution và
Eval; lớp Context nhẹ.

## Lớp 1 — Context (nhẹ)

Server không có ngữ cảnh hội thoại. Trạng thái bền duy nhất:

| Thứ | Ở đâu | Vòng đời |
|---|---|---|
| Danh sách thiết bị | `~/.googlecast-mcp/speakers.json` | bền, merge theo `uuid`, không bao giờ tự xoá |
| Cache mp3 | `/tmp/googlecast-mcp-tts` (`GOOGLECAST_MCP_CACHE`) | bền tới khi `/tmp` bị dọn; **tăng vô hạn** |
| Kết nối tới thiết bị | trong RAM tiến trình | mất khi restart |

Quyết định đáng nhớ: **lưu bền danh sách thiết bị**, vì mDNS lossy và discovery
chậm. Ghi theo kiểu write-then-rename để một lần crash không để lại file cụt.
Merge chứ không thay thế, để một lần quét sót không xoá mất thiết bị đang ngủ.

Ngữ cảnh cho LLM gọi tool nằm trong docstring của từng tool — đó là toàn bộ
"prompt" mà product này có.

## Lớp 2 — Tool (13 tool)

Một tool sinh tác dụng phụ vật lý (`say`), một tool phát media bất kỳ
(`play_media`), còn lại là điều khiển và truy vấn.

Ràng buộc thiết kế quan trọng nhất: **`say` khi thiếu `target` thì KHÔNG làm
gì** — nó trả dữ liệu có cấu trúc để LLM hỏi lại người dùng. Không dùng MCP
elicitation (nhiều client chưa hỗ trợ), không mặc định phát tất cả (sai một lần
là ồn cả nhà).

Chọn thư viện — hai tiêu chuẩn khác nhau, cố ý:

- **pychromecast**: KHÔNG qua so sánh nào. Nó là thư viện Python duy nhất còn
  được bảo trì cho giao thức Cast. Thành phần *xương sống* chọn theo mức bảo trì
  và độ phủ giao thức.
- **edge-tts**: qua so sánh 4 phương án (gTTS, Google Cloud TTS, Piper,
  edge-tts). Tiêu chí kỹ thuật tự chấm được; tiêu chí "nghe có tự nhiên không"
  thì **bắt buộc người dùng nghe rồi chọn**. Thành phần người dùng *cảm nhận
  được* thì không chọn hộ.

## Lớp 3 — Execution

- pychromecast blocking → mọi tool đẩy sang worker thread bằng
  `asyncio.to_thread`, event loop MCP không bị chặn.
- Nhiều loa → `asyncio.gather` chạy song song.
- **Cô lập lỗi**: mỗi lần cast bọc try/except riêng; một loa chết trả `error`
  cho riêng nó, các loa khác vẫn phát, kết quả tổng thể vẫn `ok`.
- Timeout cứng 10 s cho `wait()` và `block_until_active()`.
- Nối lại thiết bị theo ba nấc: cache trong RAM → địa chỉ đã lưu
  (`_connect_saved`) → quét lại mDNS. Nấc giữa có vì mDNS sót thiết bị đã lưu
  từng tạo ra lỗi tự mâu thuẫn: `DeviceNotFoundError` mà lại liệt kê chính thiết
  bị đó là "known".

## Lớp 4 — Eval

Chi tiết đầy đủ: `eval/README.md`. Tóm tắt hai luật bắt buộc:

1. **Phân tầng theo tác dụng phụ**: mặc định offline (không mạng, không tiếng);
   `--online` thêm internet nhưng vẫn im lặng; `--hardware` mới phát tiếng thật
   và phải xin phép. Test không ai dám chạy = bằng không có test.
2. **Đã kiểm ngược**: đưa lỗi `all`-chồng-nhóm trở lại → 40/43, exit 1, đỏ đúng
   ba mục về `all`; khôi phục → 43/43, exit 0. Có ghi nhận ngày và số liệu.

Điểm eval KHÔNG với tới: chất lượng âm thanh, mDNS thật, nginx/TLS/systemd, sống
sót qua reboot, giọng `male`, tham số `rate`.

## Lớp 5 — Feedback

Đây là lớp yếu nhất và cần nói thẳng.

**Chỗ hệ thống không tự báo được, chỉ tai người mới biết:**

| Triệu chứng | API báo gì |
|---|---|
| Nhóm loa + thành viên cùng nhận luồng → chồng tiếng | **`playing` cho tất cả** — không có tín hiệu nào |
| Loa nháy đèn rồi tắt (không tải được file) | có thể vẫn báo trạng thái bình thường |

Hệ quả về phương pháp: với product tác động ra thế giới vật lý, **trạng thái API
không phải bằng chứng**. Phải có vòng phản hồi bằng giác quan con người. Trong
dự án này nó tồn tại dưới dạng người dùng nói "đã nghe được rồi" và "chỉ nháy
sáng rồi tắt".

**Chỗ có tín hiệu tự động:**

- `service.sh status` in `/proc/<MainPID>/cmdline` — trả lời được câu hỏi "bản
  sửa đã thực sự được nạp chưa", câu hỏi từng ngốn 3 ngày.
- `service.sh logs` → journalctl.
- Log HTTP của media server xác nhận thiết bị CÓ tải file (mã 200) — đây là cách
  phân biệt "loa không nhận được lệnh" với "loa nhận lệnh nhưng không tải được
  file".

**Còn thiếu**: không có health check; không có metric; không phát hiện được
cache phình; không cảnh báo khi địa chỉ đã lưu bị cũ.
