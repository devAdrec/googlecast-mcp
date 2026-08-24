# Yêu cầu

## Yêu cầu gốc — nguyên văn lời người dùng

Ba dòng dưới đây là toàn bộ đặc tả chức năng của sản phẩm, giữ nguyên cách gõ:

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba yêu cầu vận hành thêm vào sau, cũng nguyên văn:

> Mcp này sẽ chạy dạng service trên máy ip .128 máy tôi setup claude desktop ip .28 giờ tôi làm dao bên cạnh đó hãy viết thêm install service remove service start stop cho mcp

> không đc port đang chạy là bao nhiêu để tôi dùng nginx reveser proxy về máy 128

> mcp này tôi chạy khi kết nối với mcp llama-server thì báo lổi: protocal error

## Tiêu chí chấp nhận

### R1 — Dò và lưu loa

| # | Tiêu chí | Kiểm bằng |
|---|---|---|
| R1.1 | Dò được thiết bị Google Cast trong LAN qua mDNS | `discover_devices`; tầng `--hardware` |
| R1.2 | Loa (`cast_type` = `audio` hoặc `group`) tách khỏi thiết bị hình ảnh (`cast`) | eval offline: `is_speaker` |
| R1.3 | Danh sách **còn sau khi tiến trình chết**, ghi ra `~/.googlecast-mcp/speakers.json` | eval offline: vòng lưu/đọc `SpeakerStore` |
| R1.4 | Một lần quét sót thiết bị **không được** xoá thiết bị đã biết | eval offline: `save` là hợp nhất, không thay thế |
| R1.5 | File hỏng hoặc thiếu đọc ra rỗng, không sập | eval offline: file JSON hỏng |

R1.3 là điểm hỏng lúc đối chiếu lần đầu: bản có sẵn chỉ cache trong RAM.

### R2 — Text tiếng Việt thành tiếng nói ra loa

| # | Tiêu chí | Kiểm bằng |
|---|---|---|
| R2.1 | `say(text=...)` nhận tiếng Việt có dấu | eval `--online`; người dùng đã nghe |
| R2.2 | Giọng nghe tự nhiên, không phải giọng máy đọc từng chữ | **tai người** — không tự động hoá được |
| R2.3 | Không cần API key, không cần tài khoản | edge-tts |
| R2.4 | Âm thanh thật sự phát ra loa | tầng `--hardware`; log HTTP cho thấy loa có tải file |
| R2.5 | Text rỗng bị từ chối trước khi gọi mạng | eval offline: `ValueError` + tripwire |
| R2.6 | Nói lại đúng câu đó không tổng hợp lại | eval `--online`: dùng lại cache |

### R3 — Không chọn loa thì hỏi

| # | Tiêu chí | Kiểm bằng |
|---|---|---|
| R3.1 | Thiếu `target` → **không phát gì cả** | eval offline: tripwire trên cả TTS lẫn cast |
| R3.2 | Trả về danh sách loa + lời nhắn đủ để LLM hỏi lại | eval offline: `needs_speaker_selection` |
| R3.3 | Nhận một tên, nhiều tên cách phẩy, hoặc `all` / `tất cả` | eval offline: chọn đích |
| R3.4 | `all` **không** gửi hai luồng vào cùng một loa vật lý | eval offline: đối chiếu theo `host` |
| R3.5 | Nhóm loa vẫn phát được khi gọi đích danh | eval offline |
| R3.6 | Một loa hỏng không làm hỏng những loa còn lại | eval offline: cô lập lỗi |
| R3.7 | Mạng không có loa nào có trạng thái riêng | eval offline: `no_speakers_found` |

R3.4 là lỗi thật đã bắt được: nhóm Cast phát *qua* thành viên của nó, nên
`all` gửi tới cả nhóm lẫn từng thành viên khiến `Kitchen speaker` nhận hai
luồng. Cả bốn lời gọi đều trả `playing` — **API không phát hiện được**, chỉ
nghe mới biết. Vì thế tiêu chí viết theo `host`, không theo tên.

### R4 — Vận hành

| # | Tiêu chí | Kiểm bằng |
|---|---|---|
| R4.1 | Chạy nền được như systemd service, tự bật lại sau khi hỏng | `scripts/service.sh` |
| R4.2 | Có đủ install / remove / start / stop / restart / status / logs | `scripts/service.sh` |
| R4.3 | Cổng cố định, biết trước, để viết được luật tường lửa và reverse proxy | MCP 8765, audio 8766 |
| R4.4 | Cài lại khi đang chạy phải thật sự thay tiến trình | `install` gọi `restart`; `status` in `/proc/<pid>/cmdline` |
| R4.5 | Client MCP ở máy khác trong LAN gọi được | đã chạy thật |
| R4.6 | Client sau reverse proxy https gọi được | đã chạy thật qua `google-cast.adrec.cloud` |
| R4.7 | Client chạy trong trình duyệt gọi được | đã chạy thật với llama-server webui |
| R4.8 | Bảo vệ DNS-rebinding của SDK **được giữ**, chỉ nới allowlist | eval offline: allowlist |

## Ngoài phạm vi (biết mà cố ý không làm)

- **Không xác thực ở tầng ứng dụng.** Ai với được `/mcp` là phát được tiếng
  trong nhà. `google-cast.adrec.cloud` phân giải công khai ra internet. Hai
  dòng chặn IP trong `scripts/nginx-googlecast-mcp.conf` đã đồng ý bật nhưng
  vẫn đang comment.
- **Cổng audio 8766 bind `0.0.0.0`, không xác thực**, phục vụ nguyên thư mục
  cache. Chặn IP ở nginx chỉ che 8765, không che cổng này.
- Cache TTS tăng vô hạn, chưa có cơ chế dọn.
- Chưa khôi phục âm lượng / nội dung đang phát sau khi chen thông báo vào.
- Không dùng MCP elicitation cho R3: nhiều client chưa hỗ trợ, nên chọn cách
  trả dữ liệu để LLM tự hỏi lại.
