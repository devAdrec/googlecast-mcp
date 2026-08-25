# Yêu cầu gốc và tiêu chí chấp nhận

## 1. Ba yêu cầu, nguyên văn lời người dùng

Trích đúng như đã gõ, giữ nguyên lỗi chính tả — vì cách diễn đạt mới là thứ
sinh ra sản phẩm, không phải bản diễn giải gọn gàng sau này:

> hãy kiểm tra xem mcp này đúng yêu cầu không:
>
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba câu này là **hành vi quan sát được**, không phải mô tả kỹ thuật. Đó là lý do
chúng dùng được làm tiêu chí nghiệm thu. Tại thời điểm nhận yêu cầu, sản phẩm
mới đạt **1/3** (chỉ có phần dò thiết bị) — và danh sách chưa đạt chính là danh
sách module phải viết.

## 2. Tiêu chí chấp nhận

### YC1 — Dò loa trong LAN rồi lưu lại

| # | Tiêu chí | Đạt khi |
|---|---|---|
| 1.1 | Dò được thiết bị Google Cast qua mDNS | `discover_devices` trả về danh sách khác rỗng trên mạng thật |
| 1.2 | **Phân biệt loa với thiết bị hình ảnh** | `list_speakers` chỉ trả `cast_type` ∈ {`audio`, `group`}; Chromecast/Nest Hub bị loại |
| 1.3 | Lưu bền qua các lần chạy | tiến trình mới đọc được `~/.googlecast-mcp/speakers.json` mà không cần dò lại |
| 1.4 | Lần dò sau **gộp**, không xoá | loa đang ngủ, bị một lượt mDNS bỏ sót, vẫn còn trong danh sách |

> 1.2 không nằm trong lời người dùng nhưng bắt buộc phải có: người dùng nói
> "google speaker", mà mDNS trả về mọi thiết bị Cast. Phát thông báo ra TV là
> sai ý định.

### YC2 — Text → tiếng Việt → phát ra loa

| # | Tiêu chí | Đạt khi |
|---|---|---|
| 2.1 | Nhận text làm tham số của tool | `say(text=...)` |
| 2.2 | **Đọc được tiếng Việt nghe tự nhiên** | người dùng NGHE và xác nhận — không có bài kiểm tự động nào thay được |
| 2.3 | Âm thanh tới được loa | loa báo `PLAYING`, chạy hết `duration`, rồi `idle_reason=FINISHED` |
| 2.4 | Chọn được giọng và tốc độ | `voice` = `female`/`male`/id đầy đủ; `rate` = `-20%`… |

> 2.2 là tiêu chí **cảm nhận**: bắt buộc con người nghe. Máy chỉ kiểm được
> "có ra file mp3 khác rỗng", không kiểm được "nghe có như người thật không".

### YC3 — Không chọn loa thì phải HỎI, không được tự phát

| # | Tiêu chí | Đạt khi |
|---|---|---|
| 3.1 | Thiếu `target` ⇒ **không phát gì cả** | không thiết bị nào nhận media, và **TTS cũng không được gọi** |
| 3.2 | Trả về đủ dữ liệu để LLM hỏi lại | `status="needs_speaker_selection"` + danh sách loa + thông điệp hướng dẫn |
| 3.3 | Nhận một tên | `target="Kitchen speaker"` |
| 3.4 | Nhận nhiều tên | `target="Kitchen speaker, Bedroom speaker"` |
| 3.5 | Nhận "tất cả" | `target` ∈ {`all`, `tất cả`, `tat ca`, `everyone`, `*`} |
| 3.6 | **"tất cả" không được phát chồng** | nhóm loa bị loại khỏi lượt "tất cả": nhóm phát QUA thành viên, gửi cả hai là hai luồng vào cùng một loa vật lý |
| 3.7 | Không có loa nào | `status="no_speakers_found"`, không phát gì |

> 3.6 là tiêu chí đắt nhất trong tài liệu này. **API báo `playing` cho cả bốn
> đích — kết quả thao tác không phân biệt được ca này với ca đúng.** Chỉ tai
> người nghe ra tiếng vọng chồng lên nhau. Dấu vết máy đọc được duy nhất nằm ở
> siêu dữ liệu thiết bị: nhóm và thành viên **cùng `host`** — và đó chính là
> chỗ bấu víu để vá.

### Yêu cầu phát sinh trong quá trình dùng thật

Không có trong ba câu ban đầu, nhưng nếu thiếu thì sản phẩm không dùng được:

| # | Tiêu chí | Đạt khi |
|---|---|---|
| 4.1 | Chạy được như service, máy khác gọi tới | systemd unit + transport HTTP |
| 4.2 | Client ngoài loopback không bị chặn | không còn `421`; nới allowlist chứ **không tắt** bảo vệ DNS-rebinding |
| 4.3 | Client trình duyệt gọi được | CORS có `expose_headers=["Mcp-Session-Id"]` |
| 4.4 | Client khắt khe về framing gọi được | `--json-response`, `--stateless` |
| 4.5 | Một loa hỏng không kéo đổ cả lượt | loa hỏng trả `error` riêng, loa còn lại vẫn `playing`, tổng thể `ok` |

## 3. Điều đã CỐ Ý không làm

| Không làm | Lý do |
|---|---|
| MCP elicitation (server tự hỏi người dùng) | phán đoán "nhiều client chưa hỗ trợ" — **CHƯA THỬ bằng thực nghiệm**; cách đang dùng (trả dữ liệu cho LLM hỏi lại) đã chạy thật ở cả 3 client |
| Mặc định "không chọn thì phát tất cả" | tác dụng phụ vật lý; đoán sai là cả nhà nghe |
| Xác thực ở tầng ứng dụng | chưa làm — xem "Điểm còn hở" trong `technical-docs.md`. Không phải đã cân nhắc rồi bỏ, mà là **nợ** |
| Khôi phục âm lượng / media đang phát sau thông báo | chưa làm |
