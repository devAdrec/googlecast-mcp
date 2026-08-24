# Hướng dẫn dùng

Dành cho người đã cài xong (`README.md`) và muốn nói một câu ra loa.

## Nói một câu

```
say(text="Cơm đã chín rồi", target="Kitchen speaker")
```

Trong Claude, không cần gõ tên tool — nói thẳng *"báo lên loa bếp là cơm chín
rồi"* là đủ.

| Tham số | Bắt buộc | Nghĩa |
|---|---|---|
| `text` | có | Câu cần nói. Tiếng Việt có dấu chạy tốt. Rỗng thì bị từ chối |
| `target` | **không** | Loa nào. Bỏ trống là cố ý — xem dưới |
| `voice` | không | `female` (mặc định), `male`, hoặc một voice id edge-tts đầy đủ |
| `rate` | không | Tốc độ nói, ví dụ `-20%` chậm lại, `+10%` nhanh lên |

## Các dạng `target`

| Gõ gì | Xảy ra gì |
|---|---|
| `"Kitchen speaker"` | Phát ở đúng loa đó |
| `"Kitchen speaker, Office speaker"` | Phát ở cả hai, song song |
| `"all"` hoặc `"tất cả"` | Phát ở mọi loa **thật**, mỗi loa đúng một lần |
| `"Family speaker group"` | Phát qua nhóm loa, như trong app Google Home |
| bỏ trống | **Không phát gì.** Trả về danh sách loa để hỏi lại bạn |
| một UUID | Cũng được, nếu hai loa trùng tên |

Tên loa không phân biệt hoa thường.

### Vì sao `all` bỏ qua nhóm loa

Một nhóm Cast phát *qua* các loa thành viên. Nếu `all` gửi tới cả nhóm lẫn
từng thành viên, một loa vật lý sẽ nhận hai luồng cùng lúc, nghe như vọng và
lệch. Nên `all` chỉ gửi tới từng loa riêng lẻ. Muốn dùng nhóm thì gọi đích
danh tên nhóm.

Đáng nói: khi lỗi này còn, cả bốn lời gọi đều trả `playing`. API không phát
hiện được — chỉ nghe mới biết.

### Vì sao bỏ `target` lại không phát gì

Phát tiếng ra loa là một tác dụng phụ vật lý trong nhà người khác. Mặc định
phát ra tất cả loa vì người dùng quên nói rõ là một mặc định tồi. Nên server
trả về:

```json
{"status": "needs_speaker_selection",
 "speakers": [...],
 "message": "No target given. Ask the user which speaker ... Available: ..."}
```

LLM đọc cái đó rồi hỏi lại bạn. Không có âm thanh nào được tổng hợp, không có
lệnh nào gửi đi.

## Các tool khác

| Tool | Dùng khi |
|---|---|
| `discover_devices` | Quét lại LAN. Chạy khi có loa mới, hoặc loa đổi IP |
| `list_speakers` | Xem các loa đã biết (không quét lại). Bỏ thiết bị hình ảnh |
| `list_devices` | Mọi thiết bị Cast, kể cả Chromecast/Nest Hub |
| `get_status` | Loa đang phát gì, âm lượng bao nhiêu |
| `play_media` | Cast một URL bất kỳ (nhạc, video) — loa tự đi tải URL đó |
| `play` / `pause` / `stop` / `seek` | Điều khiển nội dung đang phát |
| `set_volume` / `set_muted` | Âm lượng 0.0–1.0; tự kẹp vào khoảng hợp lệ |
| `quit_app` | Trả thiết bị về màn hình chờ |

## Cắm vào client

| Client | Cách |
|---|---|
| Claude Code, cùng máy | `claude mcp add --scope user googlecast -- uv run --directory <repo> googlecast-mcp` |
| Claude Desktop, máy khác | Ô connector chỉ nhận https. Bắc cầu bằng `npx -y mcp-remote http://<ip>:8765/mcp --allow-http` trong `claude_desktop_config.json` |
| Claude Desktop qua tên miền | Dựng nginx + TLS, rồi `--allow-host <domain>` |
| Client trình duyệt (llama-server webui) | Cần `--cors-origin <origin khớp chính xác thanh địa chỉ>` |

Chi tiết và lý do: `technical-docs.md`.

## Lỗi thường gặp

**"Nó bảo playing mà không nghe thấy gì"**
Kiểm âm lượng loa trước. Rồi kiểm thiết bị có treo không: `nc -z <ip> 8009`.
mDNS và ping vẫn trả lời trong khi cổng 8009 đã từ chối — restart thiết bị là
hết. Đã gặp thật trên Nest Hub, và mất ba lần thử mới nhận ra.

**"Đèn loa nháy rồi tắt, không phát hết câu"**
Thường là loa không tải được file âm thanh: cổng 8766 bị tường lửa chặn, hoặc
máy chạy server không cùng LAN với loa.

**`DeviceNotFoundError` với một loa chắc chắn đang có**
mDNS lossy, một lần quét có thể sót. Server đã tự thử kết nối thẳng tới địa
chỉ đã lưu trước khi quét lại. Nếu loa đổi IP thì chạy `discover_devices`.

**Mở `http://<ip>:8765/mcp` bằng trình duyệt thì ra `406`**
Đúng như thế. Endpoint MCP không phải trang web.

**"Đã sửa rồi mà vẫn lỗi y hệt"**
Dừng sửa. Kiểm bản sửa đã được nạp chưa: `./scripts/service.sh status` in
dòng lệnh của tiến trình đang chạy thật. `systemctl enable --now` **không**
khởi động lại service đang chạy — tiến trình cũ từng sống ba ngày như thế.

**Máy tính không cùng LAN với loa**
Không có cách vòng. mDNS không đi qua router, và loa phải với tới được máy này
để tải file.

## Riêng tư

Text được gửi tới dịch vụ giọng nói của Microsoft Edge để tổng hợp. File mp3
lưu trong thư mục cache trên máy chạy server và phục vụ **không xác thực** ở
cổng 8766 cho mọi máy trong LAN. Đừng cho nó đọc điều gì bí mật.
