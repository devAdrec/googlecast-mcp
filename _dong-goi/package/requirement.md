# Yêu cầu gốc và tiêu chí chấp nhận

## Ba yêu cầu gốc — nguyên văn của người đặt hàng

Giữ nguyên cách diễn đạt và lỗi gõ. Đây là bản gốc, không phải bản diễn giải:

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba câu này sinh ra toàn bộ product. Chúng có hai đặc điểm đáng chú ý: **được
đánh số** và **diễn đạt bằng HÀNH VI quan sát được** — nên đối chiếu được từng
câu một với mã đang có. Lần đối chiếu đầu tiên cho kết quả **đạt 1/3**, và
danh sách "chưa đạt" chính là danh sách module phải viết.

## Tiêu chí chấp nhận

### YC1 — Dò và lưu lại loa trong mạng nội bộ

| # | Tiêu chí | Mục eval chứng minh |
|---|---|---|
| 1.1 | Dò được thiết bị Google Cast trong LAN qua mDNS | `cast.discover.persists_to_store` |
| 1.2 | Phân biệt LOA (`cast_type` = `audio`/`group`) với thiết bị hình ảnh (`cast`) | `store.is_speaker.*`, `store.speakers.filters_video`, `cast.list_speakers.filters_video` |
| 1.3 | Danh sách được **lưu bền** ra đĩa, tiến trình mới vẫn biết | `cast.discover.persists_to_store`, `store.save.roundtrip` |
| 1.4 | Một lần quét sót thiết bị không được xoá thiết bị đã biết (mDNS lossy) | `store.save.merges_by_uuid`, `store.save.update_keeps_old_fields` |
| 1.5 | Thiết bị đã lưu mà lần quét này sót vẫn dùng được, qua địa chỉ đã lưu | `cast.resolve.saved_address_tried_before_rescan` |
| 1.6 | File lưu hỏng hoặc chưa có không được làm sập server | `store.load.corrupt_file_is_empty`, `store.load.missing_file_is_empty` |

*Không phải "lưu lại" nào cũng đủ.* Cache trong RAM từng thoả mãn câu chữ của
YC1 nhưng mất sạch khi restart — đó là lý do 1.3 nói rõ "ra đĩa".

### YC2 — Text (tham số truyền vào) → âm thanh tiếng Việt → phát lên loa

| # | Tiêu chí | Mục eval chứng minh |
|---|---|---|
| 2.1 | Nhận text làm tham số của tool `say` | `server.tools.exact_set` |
| 2.2 | Render được tiếng Việt thành audio thật | `online.tts.real_render_produces_audio` |
| 2.3 | Có cả giọng nữ và giọng nam tiếng Việt | `tts.resolve_voice.female/male`, `online.tts.real_male_voice` |
| 2.4 | Audio đến được loa: loa **tự tải** qua HTTP, nên URL phải tải được thật | `media.serves_file_over_http`, `server.say.audio_url_is_fetchable_by_the_speaker`, `online.end_to_end.tts_then_http_fetch` |
| 2.5 | Cast đúng kiểu nội dung `audio/mpeg` | `server.say.casts_as_audio_mpeg` |
| 2.6 | Text rỗng bị từ chối, không cast một file rỗng | `tts.synthesize.empty_text_rejected` |
| 2.7 | Render hỏng phải báo lỗi, không được im lặng cast file 0 byte | `tts.synthesize.empty_render_is_failure_not_success`, `...no_zero_byte_file_left_after_failure` |
| 2.8 | Nhiều thông báo cùng lúc thì cả loạt phải thành công | `tts.fanout.six_concurrent_all_succeed`, `online.tts.real_fanout_six_all_succeed` |
| 2.9 | **Nghe được bằng tai người** trên loa thật | `hardware.say.plays_on_a_real_speaker` + người dùng xác nhận |

2.9 không tự động hoá hết được. Một cast "thành công" hoàn toàn có thể tương
ứng với sự im lặng — cổng audio không tới được là đủ. Tiêu chí này chốt bằng
tai người, và đã chốt: *"đã nghe được rồi vậy xong chưa"*.

### YC3 — Không chọn loa thì HỎI, không tự phát

| # | Tiêu chí | Mục eval chứng minh |
|---|---|---|
| 3.1 | Thiếu loa đích → **không phát gì cả**, kể cả không render TTS | `server.say.without_a_speaker_choice_plays_nothing` |
| 3.2 | Trả về danh sách loa + thông điệp đủ để LLM hỏi lại người dùng | `server.say.without_a_speaker_choice_plays_nothing` |
| 3.3 | Mạng không có loa nào → nói rõ điều đó, khác với "chưa chọn" | `server.say.no_speakers_on_network` |
| 3.4 | Nhận một tên loa | `server.say.single_named_speaker` |
| 3.5 | Nhận nhiều tên cách nhau bằng dấu phẩy | `server.say.comma_separated_list` |
| 3.6 | Nhận `all` **và** `tất cả` | `server.say.all_excludes_speaker_groups`, `server.say.vietnamese_all_keyword` |
| 3.7 | `all` không được gửi hai luồng vào cùng một loa vật lý | `server.say.all_excludes_speaker_groups` |
| 3.8 | Một loa hỏng không được đánh sập cả lệnh | `server.say.broken_element_does_not_sink_the_rest` |

3.1 là tiêu chí nghiêm khắc nhất của product. Phát nhầm ra loa là **tác dụng
phụ vật lý không hoàn tác được** — âm thanh đã ra khỏi loa thì không thu lại
được. Vì thế mặc-định-an-toàn là *không phát gì*, chứ không phải *phát tất cả*.

3.7 tinh vi: nhóm loa Cast phát QUA các thành viên của nó, nên `all` gồm cả
nhóm lẫn thành viên sẽ đẩy hai luồng vào một loa vật lý. **Kết quả API không
phân biệt được** — cả bốn mục đều `playing`. Dấu vết duy nhất là siêu dữ liệu
thiết bị (nhóm và thành viên trùng `host`), còn lại chỉ nghe mới biết.

## Yêu cầu phát sinh trong quá trình dùng

Không nằm trong ba câu gốc, nhưng là điều kiện để product thật sự dùng được:

| # | Yêu cầu | Nguồn (nguyên văn) | Tiêu chí |
|---|---|---|---|
| 4.1 | Chạy dạng service, có install/remove/start/stop | *"hãy viết thêm install service remove service start stop cho mcp"* | `scripts/service.sh` đủ 7 lệnh; cài lại phải thật sự đổi tiến trình đang chạy |
| 4.2 | Claude Desktop ở máy khác gọi được | *"Tôi muốn khi chat với claude sẽ tự gọi và tương tác với mcp phải làm sao"* | qua `mcp-remote` hoặc reverse proxy TLS; đã xác minh thật |
| 4.3 | Đứng sau nginx reverse proxy | *"không đc port đang chạy là bao nhiêu để tôi dùng nginx reveser proxy về máy 128"* | `entry.security.*`; `proxy_buffering off` |
| 4.4 | Client trình duyệt gọi được | *"mcp này tôi chạy khi kết nối với mcp llama-server thì báo lổi: protocal error"* | `entry.security.browser_origin_passes_through`; preflight 200 + `Mcp-Session-Id` lộ ra |

## Điều KHÔNG nằm trong phạm vi

Ghi ra để không ai tưởng là thiếu sót:

- **Xác thực người gọi.** Không có. Bất kỳ ai tới được cổng đều gọi được tool.
- **Khôi phục nhạc/âm lượng đang phát** sau khi thông báo xong.
- **Dọn cache audio.** Thư mục cache tăng vô hạn.
- **Hàng đợi thông báo.** Hai `say` liên tiếp vào một loa thì cái sau cắt cái trước.
- **Điều khiển ngoài LAN.** Discovery bằng mDNS, không qua router.

Chi tiết và mức rủi ro: `technical-docs.md`.
