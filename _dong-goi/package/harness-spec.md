# Harness spec — googlecast-mcp

Loại harness: **vận hành** (máy móc, kết quả xác định). Không có thành phần
sinh nội dung bằng AI, nên trọng số dồn vào Tool và Execution; Eval nặng vừa
phải và chủ yếu đo *hành vi quan sát được*, không đo chất lượng chủ quan.

| Lớp | Trọng số | Vì sao |
|---|---|---|
| Context | thấp | không có prompt engineering; mô tả tool chính là context |
| Tool | **cao** | 13 tool là toàn bộ bề mặt product |
| Execution | **cao** | mạng, mDNS, thiết bị vật lý — chỗ mọi thứ hỏng |
| Eval | cao | phần lớn hành vi quan trọng không thấy được qua kết quả API |
| Feedback | trung bình | vòng phản hồi qua tai người, không tự động hoá hết được |

---

## 1. Context

**Thứ duy nhất LLM đọc được là docstring của tool.** Không có system prompt,
không có ví dụ few-shot.

Hai điều docstring phải tải nổi:

1. `say` **không phát gì** khi thiếu loa đích, và cái nó trả về là *nguyên
   liệu để hỏi lại người dùng*, không phải lỗi. Nếu LLM hiểu nhầm là lỗi, nó
   sẽ thử lại hoặc bịa ra một tên loa.
2. `target` nhận **bốn dạng**: một tên, nhiều tên cách phẩy, `all`, `tất cả`.

Chính vì thế thông điệp trả về của `_select_targets` (`server.py`) viết dài và
liệt kê sẵn tên loa: nó là *câu lệnh gửi cho LLM*, không phải thông báo lỗi
cho người.

Kiểm: `server.tools.exact_set` (đủ 13 tool, so TẬP tên tường minh),
`server.say.without_a_speaker_choice_plays_nothing` (nội dung thông điệp).

## 2. Tool

13 tool, chia ba nhóm: nói (`say`), khám phá (`discover_devices`,
`list_speakers`, `list_devices`), điều khiển (9 tool còn lại).

Ràng buộc thiết kế:

| Ràng buộc | Kiểm bởi |
|---|---|
| Mặc định an toàn: thiếu loa đích thì không có tác dụng phụ nào, **kể cả không render TTS** | `server.say.without_a_speaker_choice_plays_nothing` |
| Phân biệt "chưa chọn loa" với "mạng không có loa nào" | `server.say.no_speakers_on_network` |
| Một phần tử hỏng được cô lập, không đánh sập cả lệnh | `server.say.broken_element_does_not_sink_the_rest` |
| Hỏng hết thì phải báo `failed`, không được báo `ok` rỗng | `server.say.all_broken_reports_failed` |
| `all` bỏ nhóm loa | `server.say.all_excludes_speaker_groups` |
| Tham số ngoài khoảng bị kẹp, không ném lỗi | `cast.set_volume.clamps_range` |

## 3. Execution

Ba mặt phẳng thực thi tách rời, hỏng độc lập nhau:

```
MCP (8765) ── client gọi vào
mDNS/8009  ── server nói chuyện với thiết bị Cast
HTTP (8766) ── thiết bị Cast gọi NGƯỢC về server để tải audio
```

Mặt phẳng thứ ba là mặt phẳng người ta quên. Nó hỏng thì cast vẫn "thành
công" và loa vẫn im lặng.

| Điểm hỏng | Xử lý trong mã | Kiểm bởi |
|---|---|---|
| mDNS sót thiết bị đã lưu | `_connect_saved()` trước khi quét lại | `cast.resolve.saved_address_tried_before_rescan` |
| Thiết bị treo (TCP 8009 refuse) | timeout + lỗi riêng cho phần tử đó | `server.say.broken_element_does_not_sink_the_rest` |
| Dịch vụ TTS từ chối kết nối đồng thời | tuần tự hoá + 3 lần thử giãn cách | `tts.synthesize.retries_then_succeeds`, `tts.fanout.*` |
| Nhiều vòng lặp asyncio trong một tiến trình | một khoá cho mỗi vòng lặp | `tts.lock.is_per_event_loop_under_contention` |
| Render hỏng để lại file 0 byte | `unlink` trước mỗi lần thử + kiểm kích thước | `tts.synthesize.no_zero_byte_file_left_after_failure` |
| Client ở xa bị chặn bởi bảo vệ DNS-rebinding | nới allowlist, không tắt bảo vệ | `entry.security.*` |
| Client trình duyệt bị chặn bởi CORS | `CORSMiddleware` + `expose_headers` | `entry.security.browser_origin_passes_through` |

## 4. Eval

Chi tiết đầy đủ ở `eval/README.md`. Ở đây chỉ ghi hình dạng.

**Ba tầng tác dụng phụ**, tăng dần, tầng nặng phải opt-in:

| Tầng | Cờ | Chạm tới | Xin phép? |
|---|---|---|---|
| offline | (mặc định) | không gì cả | không |
| online | `--online` | edge-tts thật (internet) | không |
| hardware | `--hardware` | **loa thật, phát ra tiếng** | **có, mỗi lần** |

Bài kiểm mà không ai dám chạy thì bằng không có — nên tầng mặc định phải chạy
được ở bất cứ đâu, bất cứ lúc nào, không cần mạng, không làm phiền ai.

**Bốn luật viết bài kiểm** (thi hành trong mã, không chỉ là lời khuyên):

1. **Đếm đủ trước khi đếm xanh.** Báo cáo in `đã chạy X/Y mục đăng ký`; X<Y là
   FAIL toàn cục. Áp cho **cả** `reverse-check.py`: khớp 0 trường hợp không
   được báo ĐẠT.
2. **Mọi mục phải gọi vào mã sản phẩm** và nằm trong ≥1 danh sách kỳ-vọng-đỏ.
   `reverse-check.py` tự kiểm điều này và báo mục không được phủ.
3. **So TẬP kỳ vọng tường minh**, không so kích thước. `server.tools.exact_set`
   so tập tên, không so "13".
4. **Bằng chứng bền theo thời gian VÀ phạm vi.** Khẳng định phải sống trong
   vòng đời của fixture nó tham chiếu.

## 5. Feedback

Vòng phản hồi ngắn nhất trong product này **không tự động hoá được**: phải có
người nghe.

| Tín hiệu | Máy đọc được? |
|---|---|
| Tool trả `ok` | có — nhưng **không đủ**: cast "thành công" mà im lặng là chuyện thường |
| `content_id` khớp URL vừa cast + `duration > 0` | có — đây là bằng chứng bền nhất mà máy lấy được |
| `player_state == PLAYING` | **không tin được**: đo được `say()` mất 5.4s trong khi clip chỉ 2.26s, tức lúc trả về loa đã phát xong |
| Nghe có tự nhiên không | **không** — phải người nghe |
| Có chồng luồng lên một loa vật lý không | **không** — kết quả API không phân biệt; dấu vết duy nhất là nhóm và thành viên trùng `host` |

Hai dòng cuối là lý do tầng `--hardware` tồn tại và lý do nó không thay được
tai người.

**Tín hiệu từ phía người dùng cũng là dữ liệu.** Câu "vẫn báo lổi" lặp lại lần
thứ hai không có nghĩa là sửa chưa đủ sâu — nó thường có nghĩa là **bản sửa
chưa được nạp**. Đó là lý do `service.sh status` in `/proc/<MainPID>/cmdline`.
