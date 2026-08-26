# Yêu cầu gốc và tiêu chí chấp nhận

## Yêu cầu, nguyên văn lời người dùng

Toàn bộ product sinh ra từ một prompt duy nhất. Chép lại nguyên văn, giữ nguyên
lỗi gõ, vì cách diễn đạt của nó chính là bài học (xem `../method-note.md`):

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba yêu cầu này **đánh số** và **diễn đạt bằng hành vi quan sát được**. Đó là lý
do đối chiếu được từng cái một, và lý do biết chắc lúc bắt đầu chỉ mới đạt 1/3.

## Diễn giải thành tiêu chí chấp nhận

### YC1 — Dò và lưu loa

| # | Tiêu chí | Đạt bằng | Mục eval |
|---|---|---|---|
| 1.1 | Dò được thiết bị Google Cast trong LAN | `discover_devices` qua mDNS | `hardware.discovers_speakers` |
| 1.2 | Phân biệt **loa** với thiết bị hình ảnh | `cast_type` ∈ {`audio`, `group`} | `store.is_speaker`, `store.speakers_filter` |
| 1.3 | **Lưu lại** — sống qua khởi động lại tiến trình | `~/.googlecast-mcp/speakers.json` | `store.merge_keeps_missed` |
| 1.4 | Một lần quét sót không được xoá thiết bị đã biết | `SpeakerStore.save` gộp theo uuid | `store.merge_keeps_missed`, `store.merge_updates_fields` |
| 1.5 | File hỏng không được làm chết server | `load()` trả `[]` | `store.corrupt_json` |

Điểm 1.4 không có trong lời người dùng. Nó đến từ thực tế: mDNS mất gói, và một
lần quét thiếu mà ghi đè sẽ **xoá mất** loa vừa dùng được năm phút trước.

### YC2 — Text tiếng Việt → âm thanh → phát lên loa

| # | Tiêu chí | Đạt bằng | Mục eval |
|---|---|---|---|
| 2.1 | Nhận text làm tham số của tool | `say(text=...)` | `server.say_schema` |
| 2.2 | Đọc được **tiếng Việt** tự nhiên | edge-tts `vi-VN-HoaiMyNeural` / `NamMinhNeural` | `online.real_render`, `online.voices_differ` |
| 2.3 | Âm thanh **thật sự phát ra loa** | TTS → HTTP → Cast | `hardware.say_leaves_durable_trace` |
| 2.4 | Loa phải **lấy được** file audio | HTTP server trên địa chỉ LAN | `media.serves_bytes`, `media.binds_wildcard_advertises_lan` |
| 2.5 | Cast đúng dạng audio | `play_media(..., "audio/mpeg", ...)` | `say.casts_audio_mpeg` |
| 2.6 | Text lặp lại không render lại | cache theo hash nội dung | `tts.cache_hit_skips_service` |
| 2.7 | Một thông báo hỏng lẻ tẻ không được rơi mất | thử lại có giãn cách | `tts.retries_then_succeeds` |
| 2.8 | Gọi dồn nhiều thông báo cùng lúc: **tất cả** phải ra | tuần tự hoá bằng `asyncio.Lock` | `tts.renders_are_serialised`, `online.fanout_all_survive` |
| 2.9 | Lần render hỏng không để lại file 0 byte | `unlink` trước mỗi lần thử | `tts.no_zero_byte_residue` |

2.7–2.9 là **bổ sung sau khi đo**, không phải suy đoán: gọi dồn 6 yêu cầu thì chỉ
4 về đích, mất 101 giây, và cache đọng file rỗng. Chi tiết ở `technical-docs.md`.

### YC3 — Không chọn loa thì phải hỏi

| # | Tiêu chí | Đạt bằng | Mục eval |
|---|---|---|---|
| 3.1 | Thiếu loa → **không phát gì cả** | trả `needs_speaker_selection` | `say.without_target_plays_nothing` |
| 3.2 | Trả về danh sách để client hỏi lại người dùng | `speakers` + `message` trong kết quả | `server.no_target_asks` |
| 3.3 | Nhận **một** tên loa | `target="Kitchen speaker"` | `say.casts_audio_mpeg` |
| 3.4 | Nhận **nhiều** tên cách nhau bằng phẩy | tách theo `,` | `server.comma_list` |
| 3.5 | Nhận **"tất cả"** | `all` / `tất cả` / `everyone` / `*` | `server.all_excludes_groups` |
| 3.6 | Mạng không có loa nào → nói rõ, đừng hỏi vu vơ | `no_speakers_found` | `server.no_speakers_found` |
| 3.7 | "Tất cả" **không được** phát chồng lên một loa vật lý | bỏ nhóm loa khỏi `all` | `say.all_casts_once_per_speaker` |

3.1 là tiêu chí nghiêm nhất trong ba yêu cầu, và là chỗ dễ làm sai nhất. "Hỏi
user" cám dỗ người ta hiểu thành "cứ phát đại rồi hỏi sau". Nhưng phát tiếng ra
loa là **tác dụng phụ vật lý trong nhà người ta** — không hoàn tác được. Nên
mặc định là **im lặng**, không phải phát tất cả.

3.7 cũng không có trong lời người dùng. Nó lộ ra khi nghe bằng tai: nhóm loa Cast
phát *qua* thành viên của nó, nên `all` gửi tới cả nhóm lẫn từng loa sẽ khiến một
loa vật lý nhận **hai luồng**. Cả 4 lệnh đều trả `playing` — **API không phân biệt
được**; dấu vết duy nhất nằm ở chỗ nhóm và thành viên **trùng `host`**.

## Ngoài phạm vi (nói rõ để khỏi hiểu nhầm là thiếu sót)

- **Không có xác thực ở tầng ứng dụng.** Ai vào được `/mcp` là phát được tiếng
  trong nhà. Đây là quyết định đã biết, không phải bỏ quên — xem `technical-docs.md`.
- Không khôi phục nhạc/âm lượng đang phát sau khi chen thông báo vào.
- Không dọn cache TTS.
- Không dùng MCP elicitation (client hỏi người dùng theo chuẩn) — **chưa đo trên
  client thật**, nên đang trả dữ liệu để LLM tự hỏi lại.
