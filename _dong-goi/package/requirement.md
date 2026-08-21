# Yêu cầu gốc và tiêu chí nghiệm thu

## Ba yêu cầu, nguyên văn của người dùng

Toàn bộ product sinh ra từ một tin nhắn duy nhất. Chép lại đúng như đã gõ, giữ
nguyên lỗi chính tả:

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba câu này đáng chép nguyên văn vì chúng có hai tính chất hiếm: **được đánh số**
và **diễn đạt bằng hành vi quan sát được**, không phải bằng công nghệ. Nhờ vậy
chúng dùng thẳng làm tiêu chí nghiệm thu mà không cần diễn giải lại. Lúc yêu cầu
này được nêu, bản đang có chỉ đạt 1/3.

Các yêu cầu bổ sung xuất hiện sau, cũng nguyên văn:

> có workinig speaker xác minh luôn tts -> HTTP -> cast chạy thật

> Mcp này sẽ chạy dạng service trên máy ip .128 máy tôi setup claude desktop ip .28 giờ tôi làm dao bên cạnh đó hãy viết thêm install service remove service start stop cho mcp

---

## Tiêu chí chấp nhận

### YC1 — Dò và lưu danh sách loa

| # | Tiêu chí | Kiểm ở đâu |
|---|---|---|
| 1.1 | Dò được thiết bị Google Cast trong LAN qua mDNS | `discover_devices` trên mạng thật: 8 thiết bị |
| 1.2 | Phân biệt loa với thiết bị hình ảnh — `cast_type` là `audio`/`group` là loa, `cast` thì không | eval: `speaker classification` |
| 1.3 | Danh sách được lưu bền, tiến trình mới không cần dò lại | `~/.googlecast-mcp/speakers.json`; eval: `device store` |
| 1.4 | Lưu là **gộp** theo `uuid`, không ghi đè — một lần mDNS sót không được làm mất thiết bị | eval: `a re-save merges by uuid` |
| 1.5 | Thiết bị đã lưu mà mDNS sót vẫn kết nối được thẳng theo địa chỉ | `_connect_saved()` — `cast_manager.py:110` |

### YC2 — Text tiếng Việt thành tiếng nói phát ra loa

| # | Tiêu chí | Kiểm ở đâu |
|---|---|---|
| 2.1 | Nhận text tiếng Việt có dấu, đọc tự nhiên | Người dùng nghe và xác nhận |
| 2.2 | Không cần khoá API, không cần tài khoản | edge-tts |
| 2.3 | Chuỗi TTS → HTTP → cast chạy thật trên loa thật, hết cả câu | 3 clip đo 2.09/4.27/7.10s, đều `PLAYING` đủ `duration` rồi `idle_reason=FINISHED` |
| 2.4 | Lặp lại cùng một câu thì dùng lại file cũ, không tổng hợp lại | eval `--online`: `a repeat reuses the cached file` |
| 2.5 | Text rỗng bị từ chối trước khi gọi mạng | eval: `blank text raises ValueError` |
| 2.6 | Một loa hỏng không được kéo cả lệnh chết theo | eval: `one broken speaker must not sink the rest` |

### YC3 — Không chọn loa thì phải hỏi lại

| # | Tiêu chí | Kiểm ở đâu |
|---|---|---|
| 3.1 | Thiếu tên loa → **không phát gì cả** | eval: `omitting the speaker casts to NOTHING` |
| 3.2 | Thiếu tên loa → cũng **không tổng hợp** âm thanh | eval: `does NOT synthesize audio` |
| 3.3 | Trả về `needs_speaker_selection` kèm danh sách loa để mô hình hỏi lại người dùng | eval + bằng chứng DoD ở `eval/README.md` |
| 3.4 | Nhận được: một tên, nhiều tên cách dấu phẩy, hoặc `all` / `tất cả` | eval: `explicit targets`, `alias keywords` |
| 3.5 | `all` **không** gửi tới nhóm loa và thành viên của nó cùng lúc | eval: `hits no physical device twice (by host)` |
| 3.6 | Nhóm loa gọi đích danh thì vẫn phát được | eval: `a group named explicitly IS still cast to` |
| 3.7 | Mạng không có loa nào → `no_speakers_found`, không phát gì | eval: `an empty network casts nothing` |

### YC4 — Chạy như dịch vụ, phục vụ client ở máy khác

| # | Tiêu chí | Kiểm ở đâu |
|---|---|---|
| 4.1 | Có `install / remove / start / stop / restart / status / logs` | `scripts/service.sh` |
| 4.2 | Cài lại khi đang chạy phải thật sự đổi tiến trình | `service.sh` dùng `restart`, không `enable --now` |
| 4.3 | `status` cho thấy dòng lệnh **thật** của tiến trình đang chạy | `service.sh:112-115` đọc `/proc/<pid>/cmdline` |
| 4.4 | Client ở máy khác kết nối được qua LAN và qua https | Đã thông cả hai đường, 13 tool |
| 4.5 | Client trong trình duyệt kết nối được | Preflight 200 + `Mcp-Session-Id` được expose |

---

## Cố ý KHÔNG làm

- **Không dùng MCP elicitation** để hỏi người dùng chọn loa. Nhiều client chưa
  hỗ trợ; trả dữ liệu về cho mô hình tự hỏi thì chạy ở mọi client.
- **Không mặc định phát ra tất cả loa** khi thiếu tên. Phát nhầm ra tiếng trong
  nhà là tác dụng phụ vật lý, không rút lại được.
- **Không tắt bảo vệ DNS-rebinding của SDK**, chỉ nới allowlist. Tắt là mở cửa
  cho một trang web bất kỳ tấn công server trong nhà.

## Chưa đạt, biết rõ và ghi lại

- Không có xác thực ở tầng ứng dụng; `google-cast.adrec.cloud` phân giải công
  khai ra internet.
- Cổng audio 8766 bind `0.0.0.0`, không xác thực, phục vụ nguyên thư mục cache.
  Chặn IP ở nginx chỉ che được 8765.
- Cache TTS tăng vô hạn, chưa có dọn dẹp.
- Chưa khôi phục âm lượng / nội dung đang phát sau khi chen thông báo vào.
