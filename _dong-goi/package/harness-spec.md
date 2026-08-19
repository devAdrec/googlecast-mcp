# Harness spec — 5 lớp

Loại harness: **vận hành** (máy móc, kết quả xác định). Không có bước nào để AI sinh
nội dung tự do, nên trọng số dồn vào Tool và Execution; Eval nhẹ hơn so với harness
sinh, nhưng **không nhẹ được như một CLI thường** vì lớp Feedback ở đây bị mù một
phần: kết quả cuối cùng là âm thanh, mà chương trình không nghe được.

## 1. Context — thứ agent phải biết trước khi gọi

| Cái gì | Nguồn | Vì sao cần |
|---|---|---|
| Có những loa nào | `list_speakers` (đọc store, tự quét nếu rỗng) | không có thì không thể hỏi người dùng câu đúng |
| Loa vs thiết bị hình ảnh | `cast_type` trong store | tránh phát tiếng lên TV |
| Loa lẻ vs nhóm | `cast_type == "group"` | quyết định `all` gồm những gì |
| Thiếu `target` thì làm gì | thông điệp trong `needs_speaker_selection` | agent phải hỏi lại, không được đoán |

**Nguyên tắc thiết kế của lớp này:** khi thiếu thông tin, harness **trả dữ liệu để hỏi
lại**, không tự suy diễn. Cụ thể là trả nguyên danh sách loa kèm một câu chỉ dẫn đủ rõ
để LLM tự sinh câu hỏi. Không dùng MCP elicitation — nhiều client chưa hỗ trợ, và một
tính năng hỏng câm ở đúng client cần nó thì tệ hơn là không có.

## 2. Tool — bề mặt phơi ra cho agent

13 tool. Ranh giới quan trọng nhất không phải là tool nào có mà là **tool nào có tác
dụng phụ không hoàn tác được**:

| Nhóm | Tool | Tác dụng phụ |
|---|---|---|
| Đọc | `discover_devices`, `list_devices`, `list_speakers`, `get_status` | không |
| **Phát tiếng** | `say`, `play_media` | **vật lý, không hoàn tác được** |
| Điều khiển | `play`, `pause`, `stop`, `seek`, `set_volume`, `set_muted`, `quit_app` | có, nhưng đảo ngược được |

Quy tắc rút ra: **tool có tác dụng phụ vật lý phải đòi tham số tường minh.** `say`
không có giá trị mặc định cho `target`, và thiếu nó thì nó không làm gì cả — kể cả
không gọi TTS. Mặc định "phát tất cả" nghe tiện hơn, nhưng một lệnh sai sẽ làm ồn cả
nhà, và không có nút hoàn tác cho âm thanh đã phát.

Mô tả tool (docstring) là một phần của harness, không phải chú thích: agent chọn tool
và điền tham số dựa trên đó. Docstring của `say` nói thẳng "If `target` is omitted, no
audio is played" — chính câu đó ngăn agent tự đoán.

## 3. Execution — chuyện gì xảy ra khi gọi

```
say(text, target)
  └─ _select_targets  → thiếu target? dừng tại đây, trả prompt (KHÔNG TTS, KHÔNG cast)
  └─ tts.synthesize   → mp3, cache theo hash(text|voice|rate|volume)
  └─ media_server     → URL http://<lan_ip>:8766/<file>   (bind 0.0.0.0)
  └─ cast song song   → mỗi loa một task, lỗi được bắt riêng từng loa
```

Bốn tính chất thực thi được chọn có chủ ý:

- **Chặn sớm.** Nhánh thiếu `target` cắt trước cả TTS. Rẻ hơn, và quan trọng hơn là
  không để lại tác dụng phụ nào.
- **Cô lập lỗi.** Mỗi loa một task, `except` riêng. Một loa chết trả `error` cho riêng
  nó; tổng thể vẫn `ok` nếu có ít nhất một loa phát được. Trong một hệ nhiều thiết bị,
  luôn có một thiết bị đang treo — nếu nó kéo đổ cả lệnh thì tính năng coi như không
  dùng được.
- **Không chặn event loop.** pychromecast là thư viện blocking; mọi lời gọi đi qua
  `asyncio.to_thread`.
- **Bền qua tiến trình.** Store ghi hợp nhất theo uuid (write-then-rename), nên một
  lần quét sót không xoá mất thiết bị đã biết.

## 4. Eval — xem `eval/README.md`

Tóm tắt: 35 mục offline (không phát tiếng, exit 0/1) + một tầng `--hardware` phát tiếng
thật, mặc định tắt.

Điều đáng ghi vào spec chứ không chỉ vào README eval: **eval này đã được kiểm ngược.**
Đưa lỗi cũ trở lại thì mục tương ứng FAIL. Một bộ eval chưa từng đỏ là một bộ eval chưa
biết có hoạt động không.

Và ranh giới của nó: exit code 0 chứng minh **logic** đúng, không chứng minh **âm
thanh** đúng.

## 5. Feedback — vòng lặp học được gì sau mỗi lần chạy

Đây là lớp yếu nhất của harness này, và cần nói thẳng vì sao.

**Tín hiệu máy đọc được:** trạng thái Cast (`PLAYING` → `idle_reason=FINISHED`), log
HTTP của media server (thiết bị có GET file không, mã 200 không), `error` từng loa.

**Tín hiệu máy KHÔNG đọc được — và đây là vấn đề:**

- Chồng luồng: mọi thiết bị báo `playing`, âm thanh sai.
- Phát cụt giữa chừng: thiết bị nháy đèn rồi tắt, trạng thái vẫn không tố cáo.
- Giọng sai, tốc độ sai: không có tín hiệu nào cả.

Ba trường hợp trên **chỉ tai người phát hiện được**. Hệ quả cho bất kỳ ai làm việc tiếp
trên product này: **đừng coi `status: playing` là bằng chứng thành công.** Nó chỉ chứng
minh lệnh đã được nhận.

**Kỷ luật bù lại chỗ mù đó — cái này đã trả giá mới có:**

1. **Giữ lịch sử đo.** Cùng một thiết bị đã từng "phát tốt" (lần đo #4) rồi "nháy đèn
   rồi tắt" (lần #15). Chỉ nhờ có kết quả đo cũ mới phân định được lỗi thiết bị với hồi
   quy mã nguồn. Không có lịch sử thì hai thứ đó nhìn giống hệt nhau.
2. **Người dùng lặp lại "vẫn lỗi" = tín hiệu sai hướng.** Đó không phải lời mời sửa
   tiếp. Dừng sửa, đi kiểm tra bản sửa đã thực sự được NẠP chưa. Tín hiệu này từng bị
   bỏ lỡ một vòng, và bản sửa đúng đã nằm sẵn trên đĩa suốt thời gian đó trong khi tiến
   trình cũ chạy tiếp 3 ngày.
3. **Kiểm mạng trước khi đọc mã.** `nc -z <ip> 8009`.
4. **Hai mẫu trùng nhau không phải một quy luật.** Cả hai Nest Hub cùng đóng cổng 8009
   → đã kết luận sai là "firmware bỏ cổng này". Không phải. Thiết bị treo.
