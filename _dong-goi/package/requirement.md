---
product: googlecast-mcp
layer: output
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
method_note: "[[method-googlecast-mcp]]"
registry: "[[packages/googlecast-mcp]]"
---

# Yêu cầu

## Nguồn gốc — nguyên văn của người dùng

Toàn bộ sản phẩm sinh ra từ đúng một prompt:

> `hãy kiểm tra xem mcp này đúng yêu cầu không:`
> `1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại`
> `2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu`
> `3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả`

Lúc nhận prompt này đã có sẵn một scaffold 11 tool Cart chung chung từ phiên
trước, **chưa có TTS**. Đối chiếu ra **đạt 1/3**. Danh sách chưa đạt chính là
danh sách module phải viết.

## R1 — dò loa và lưu lại

- Quét thiết bị Google Cast trong LAN qua mDNS.
- **Lọc loa khỏi thiết bị hình ảnh**: `cast_type` là `audio` hoặc `group` là
  loa; `cast` (Chromecast/TV/Nest Hub có màn) không phải.
- **Lưu bền** ra `~/.googlecast-mcp/speakers.json` (đổi bằng
  `GOOGLECAST_MCP_STORE`). Lý do: mDNS lossy và quét thì chậm — một tiến trình
  mới phải biết ngay có những loa nào mà không phải quét trước.
- Lưu là **gộp theo uuid**, không phải ghi đè: một lần quét sót không được làm
  mất thiết bị đã biết.

## R2 — nói tiếng Việt ra loa

- `say(text, target?, voice, rate)`: văn bản → tiếng nói → phát ra loa.
- Tiếng Việt tự nhiên. Giọng nữ `vi-VN-HoaiMyNeural` (mặc định), nam
  `vi-VN-NamMinhNeural`, chỉnh tốc độ bằng `rate`.
- Ràng buộc kiến trúc kéo theo: thiết bị Cast **tự đi tải** media qua HTTP, nên
  một server "nói được" **bắt buộc kiêm HTTP file server** trên địa chỉ LAN.
  Đưa đường dẫn file cho loa là vô nghĩa.

## R3 — chưa chọn loa thì hỏi lại, KHÔNG phát

- Thiếu `target` → **không phát gì cả**, trả về `needs_speaker_selection` kèm
  danh sách loa và câu hướng dẫn để LLM hỏi lại người dùng.
- Không có loa nào → `no_speakers_found`.
- Nhận: một tên · nhiều tên cách dấu phẩy · `all` / `tất cả` / `everyone` / `*`.
- `all` **phải bỏ nhóm loa**: nhóm Cast phát QUA chính các thành viên, gửi cả
  nhóm lẫn thành viên thì một loa vật lý nhận hai luồng. Gọi nhóm theo tên thì
  vẫn được.

**Vì sao không dùng MCP elicitation:** đó là phán đoán, **CHƯA THỬ** trên
client thật. Trả dữ liệu cho LLM tự hỏi lại là đường chắc chắn chạy trên mọi
client. Vì sao không mặc định phát tất cả: đó là tác dụng phụ **vật lý, không
hoàn tác được** — âm thanh đã phát ra thì không thu lại được.

## Yêu cầu vận hành (đến sau, từ prompt #7 trở đi)

- Chạy dạng **service** trên một máy, phục vụ client ở máy khác trong LAN:
  `install / remove / start / stop / restart / status / logs`.
- Đứng được sau **reverse proxy** có tên miền và TLS.
- Phục vụ được **client trong trình duyệt** (cần CORS).
- Phục vụ được **client khắt khe** (cần `--json-response`, `--stateless`).

## Ngoài phạm vi (đã cân nhắc, cố ý không làm)

- Xác thực ở tầng ứng dụng — **đây là điểm hở đã biết**, xem
  [technical-docs.md](technical-docs.md).
- Dọn cache TTS.
- Khôi phục âm lượng / nội dung đang phát sau khi thông báo xong.
- Điều khiển thiết bị hình ảnh như một tính năng riêng (các tool Cast chung
  vẫn dùng được cho chúng).

## Chấp nhận được coi là đạt

Xem cột bằng chứng trong [README.md](README.md#nghiệm-thu--bằng-chứng-dod) và
[eval/README.md](eval/README.md). Tóm tắt: gọi được 13 tool từ client thật qua
cả stdio lẫn HTTP; `say` phát ra tiếng nghe được trên loa thật; thiếu `target`
thì không loa nào kêu.
