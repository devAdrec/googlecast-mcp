# Yêu cầu gốc và tiêu chí chấp nhận

## Nguồn: nguyên văn của người dùng

Toàn bộ product sinh ra từ MỘT tin nhắn duy nhất. Chép nguyên văn, giữ nguyên lỗi gõ,
vì cách diễn đạt của nó mới là thứ đáng học:

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba đặc điểm khiến tin nhắn này làm được việc mà một bản mô tả dài không làm được:
nó **đánh số**, nó mô tả **hành vi quan sát được** chứ không mô tả kỹ thuật, và vì thế
mỗi dòng **đối chiếu được** với sản phẩm thật. Lần đối chiếu đầu tiên cho kết quả
1/3 — con số đó chỉ tồn tại được là nhờ yêu cầu viết theo kiểu này.

## YC-1 — Dò và lưu danh sách loa

**Chấp nhận khi:**
- `discover_devices` quét mDNS, trả về `friendly_name`, `uuid`, `model_name`, địa chỉ.
- Danh sách được ghi bền ra `~/.googlecast-mcp/speakers.json`; tiến trình mới đọc lại
  được mà không cần quét.
- `list_speakers` chỉ trả loa (`cast_type` là `audio` hoặc `group`), loại bỏ thiết bị
  hình ảnh (`cast_type` = `cast`).
- Ghi là **hợp nhất theo uuid**, không phải ghi đè: một lần quét sót không được xoá
  mất thiết bị đã biết.

**Vì sao khắt khe chỗ "lưu bền":** mDNS lossy và chậm. Nếu chỉ dựa vào quét, cùng một
câu lệnh sẽ lúc chạy lúc không, và người dùng sẽ đổ lỗi cho tính năng nói chứ không
phải cho discovery.

Kiểm tự động: eval mục `is_speaker: *`.
Kiểm thật: 2 lần trên mạng 8 thiết bị → 4 loa / 4 thiết bị hình ảnh.

## YC-2 — Text tiếng Việt → âm thanh → phát ra loa

**Chấp nhận khi:**
- `say(text=...)` nhận tiếng Việt có dấu và phát ra loa được chỉ định.
- Giọng nghe tự nhiên, không phải giọng máy đọc từng tiếng.
- Không cần API key, không cần tài khoản trả phí.
- Một loa hỏng không được làm hỏng cả lệnh khi gọi nhiều loa.

**Tiêu chí "tự nhiên" là tiêu chí cảm nhận, và nó KHÔNG được tự chấm.** Bốn phương án
đã so: gTTS (giọng máy móc), Google Cloud TTS (cần key, có phí), Piper (offline nhưng
yếu, setup nặng), edge-tts. Tiêu chí kỹ thuật — cần key không, offline không, chi phí
— tự đối chiếu được. Còn "nghe có tự nhiên không" thì bắt buộc để người dùng nghe rồi
tự chọn. Người dùng chọn edge-tts. Giọng: `vi-VN-HoaiMyNeural` (nữ, mặc định),
`vi-VN-NamMinhNeural` (nam).

Kiểm tự động: eval mục `resolve_voice`, `TTS sinh mp3 khác rỗng`, `loa hỏng -> phần tử
đó status=error`.
Kiểm thật: người dùng xác nhận NGHE ĐƯỢC; 3 clip đo 2.09 / 4.27 / 7.10 giây đều
`PLAYING` đủ thời lượng rồi `idle_reason=FINISHED`.

## YC-3 — Không chọn loa thì phải HỎI, không được tự phát

**Chấp nhận khi:**
- Thiếu `target` → **không phát bất cứ thứ gì**, kể cả không gọi TTS.
- Trả về `status="needs_speaker_selection"` kèm danh sách loa và một thông điệp đủ để
  LLM tự hỏi lại người dùng.
- `target` nhận: một tên, nhiều tên cách phẩy, hoặc `all` / `tất cả`.

**Đây là yêu cầu dễ làm sai nhất, và làm sai thì hậu quả là vật lý.** Mặc định phát
tất cả khi thiếu tham số nghe có vẻ tiện, nhưng lệnh sai sẽ làm ồn cả nhà — và không
có nút hoàn tác cho âm thanh đã phát ra. Cũng không dùng MCP elicitation: nhiều client
chưa hỗ trợ, tính năng sẽ hỏng câm ở đúng những client cần nó nhất. Cách chọn: trả dữ
liệu về cho LLM tự hỏi lại — chạy được trên mọi client.

Kiểm tự động: eval mục `say thiếu target -> ...` (4 mục, gồm cả "KHÔNG cast gì cả" và
"KHÔNG gọi TTS").

## YC-4 (phát sinh) — Chạy được như service, client ở máy khác gọi tới

Không có trong tin nhắn gốc; sinh ra từ hoàn cảnh thật: người dùng chạy Claude Desktop
ở máy `.28`, MCP ở máy `.128`, và loa thì chỉ máy `.128` với tới được.

**Chấp nhận khi:** cài/gỡ/khởi động lại bằng một script; client từ LAN gọi được; client
đòi https gọi được qua reverse proxy; client trình duyệt gọi được (CORS); client khắt
khe gọi được (`--json-response --stateless`).

Kiểm tự động: eval mục `allowed_hosts` / `allowed_origins`.
Kiểm thật: qua `https://google-cast.adrec.cloud/mcp`, qua `http://<LAN>:8765/mcp`, và
mô phỏng client trình duyệt với Origin `http://192.168.1.99:8383` — cả ba đều thấy đủ
13 tool.

## YC-5 (ngầm, phát hiện muộn) — "tất cả" không được phát chồng

Không ai viết ra yêu cầu này. Nó lộ ra khi nghe.

**Chấp nhận khi:** `target="all"` không gửi tới cả nhóm loa lẫn từng thành viên của
nhóm đó.

**Điểm đáng sợ:** nhóm Cast phát QUA các thành viên, nên gửi cả hai làm một loa vật lý
nhận hai luồng — mà **mọi thiết bị vẫn trả `playing`**. Trạng thái API không phát hiện
được lỗi này. Chỉ tai người mới biết. Đo được: `Family speaker group` và
`Kitchen speaker` cùng ở `192.168.1.22`.

Đã sửa (commit `fcf4035`): `all` bỏ `cast_type=group`; nhóm vẫn gọi được bằng tên.
Kiểm tự động: eval mục `say all -> KHÔNG gửi tới speaker group` (mục này đã được kiểm
ngược: đưa lỗi cũ trở lại thì eval FAIL đúng như mong đợi).
Kiểm thật: sau khi sửa, 3 loa riêng lẻ, không chồng.

## Chưa đạt / còn hở

- Không xác thực ở tầng ứng dụng; tên miền phân giải công khai.
- Cổng audio 8766 không xác thực, phục vụ cả thư mục cache.
- Cache TTS tăng vô hạn, chưa dọn.
- Chưa khôi phục âm lượng / media đang phát sau khi thông báo xong.
- Giọng nam và tham số `rate` — **CHƯA THỬ** lần nào.
