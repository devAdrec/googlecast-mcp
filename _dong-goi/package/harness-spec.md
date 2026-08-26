# Harness spec — googlecast-mcp

Loại harness: **vận hành** (máy móc, kết quả xác định). Không có bước nào do AI
sinh ra nội dung, nên mọi mục kiểm đều pass/fail dứt khoát, không có chấm điểm
chất lượng.

Trọng số 5 lớp cho loại này: **Execution và Eval nặng nhất**; Context nhẹ vì
không có prompt nào cần thiết kế; Feedback trung bình.

---

## Lớp 1 — Context (nhẹ)

Server không sinh nội dung. "Context" ở đây là thứ nó **kể cho LLM nghe** để LLM
quyết định đúng — và chỗ đó có một quyết định thiết kế thật sự.

| Thành phần | Nội dung |
|---|---|
| Mô tả tool | docstring của mỗi `@mcp.tool()`; là thứ duy nhất LLM đọc để chọn tool |
| Điểm quyết định | `say` **không** có `target` mặc định. Docstring nói thẳng: *"If `target` is omitted, no audio is played"* |
| Kênh hỏi lại | khi thiếu loa, kết quả trả về là **dữ liệu có cấu trúc** (`status`, `speakers`, `message`) chứ không phải lỗi — để LLM biết phải hỏi người dùng rồi gọi lại |
| Ràng buộc | `message` phải liệt kê tên loa sẵn có, nếu không LLM sẽ hỏi vu vơ |

Neo bằng: `server.no_target_asks`, `server.say_schema`, `server.tool_surface`.

## Lớp 2 — Tool (nhẹ)

13 tool, một mặt tiếp xúc. Điều đáng kiểm không phải từng tool làm gì, mà là
**mặt tiếp xúc không được lặng lẽ đổi**: một tool biến mất hoặc một tham số bắt
buộc mọc thêm sẽ làm hỏng mọi client đang chạy.

- `server.tool_surface` so **tập tên tường minh**, không so số lượng.
  `len(a) == len(b)` vẫn xanh khi cả hai cùng co lại.
- `server.say_schema` giữ `target` là **tuỳ chọn** và `text` là **bắt buộc**.

## Lớp 3 — Execution (nặng)

Chuỗi thật là: **text → TTS → file → HTTP → thiết bị Cast tự tải về → phát ra**.
Ba biên giới, mỗi biên giới một kiểu hỏng riêng.

| Biên | Hỏng kiểu gì | Neo bằng |
|---|---|---|
| Ứng dụng → dịch vụ TTS | từ chối kết nối đến cùng lúc; file 0 byte | `tts.renders_are_serialised`, `tts.no_zero_byte_residue`, `online.fanout_all_survive` |
| Ứng dụng → HTTP | phục vụ sai thư mục; URL không escape; bind sai địa chỉ | `media.serves_bytes`, `media.quotes_filenames`, `media.binds_wildcard_advertises_lan` |
| HTTP → thiết bị Cast | thiết bị treo; mDNS sót; sai MIME | `cast.*`, `hardware.say_leaves_durable_trace` |
| Client → MCP | Host không tin (421); thiếu CORS; khung SSE | `entry.*` |

**Ba tầng tác dụng phụ**, mặc định là tầng vô hại:

| Tầng | Cờ | Chạm vào gì | Ai chạy được |
|---|---|---|---|
| offline | *(mặc định)* | chỉ thư mục tạm | bất kỳ ai, bất kỳ lúc nào, CI |
| online | `--online` | internet (dịch vụ edge-tts) | ai có mạng |
| hardware | `--hardware` | **phát tiếng thật ra loa thật** | **phải xin phép trước** |

Bài kiểm mà không ai dám chạy thì bằng không có. Vì vậy tầng mặc định phải chạy
được ở bất cứ đâu, và hai tầng kia là **opt-in**.

## Lớp 4 — Eval (nặng)

Bộ luật bộ kiểm tự áp lên chính nó. Mỗi điều dưới đây là hệ quả của một lần
bộ kiểm **đã từng nói dối** trong các phiên trước.

1. **Kiểm ngược hai chiều, kỳ vọng viết TRƯỚC.** Mỗi lỗi gieo mang sẵn danh sách
   mục *phải* đỏ. Mục nằm trong danh sách mà vẫn xanh = **TEST GIẢ**. Kèm **4 đối
   chứng vô hại kỳ-vọng-XANH**; đối chứng làm đỏ = **đỏ bừa**, cũng phải sửa.
2. **Đếm đủ trước khi đếm xanh.** Mỗi mục bọc riêng; lỗi hạ tầng là `ERROR`,
   không bị nuốt. Báo cáo in `da chay X/Y muc dang ky`; `X < Y` là **FAIL toàn
   cục**. Có `atexit` in bảng kê cả khi tiến trình chết giữa chừng.
3. **Mỗi mục phải chạm mã sản phẩm** và phải nằm trong **≥1 danh sách kỳ-vọng-đỏ**.
   `reverse-check.py` in ra mục nào **CHƯA PHỦ**.
4. **So TẬP tường minh, không so kích thước.** `expect_set` báo rõ thiếu gì / thừa gì.
5. **Test giả ≠ kỳ vọng sai.** Kỳ vọng sai thì sửa kỳ vọng **theo requirement,
   kèm trích nguồn**; cấm nới cho xanh.
6. **Async: mốc chờ + bằng chứng bền.** Điều kiện chờ phải là dấu vết còn lại
   *sau khi* việc xong (`content_id`, file trên đĩa, số đếm), không phải trạng
   thái thoáng qua.
7. **Vệ sinh mock.** `swap()`/`swap_item()` luôn khôi phục; một **residue guard**
   so lại danh tính gốc sau **mỗi** mục và quy lỗi cho đúng mục làm rò. Không
   dùng `importlib.reload`.
8. **Hoàn nguyên = chạy lại thấy XANH**, không phải nhìn `git status`.
   `reverse-check.py` gieo lỗi vào **bản sao** dưới thư mục tạm, đặt
   `PYTHONDONTWRITEBYTECODE=1`, và **không bao giờ ghi vào cây sản phẩm**.

## Lớp 5 — Feedback (trung bình)

| Ai nhận | Nhận cái gì |
|---|---|
| LLM | `needs_speaker_selection` + danh sách loa + câu hướng dẫn gọi lại |
| Người dùng | kết quả **theo từng loa**: loa nào `playing`, loa nào `error` và vì sao |
| Người vận hành | `service.sh status` in dòng lệnh tiến trình **đang thật sự chạy** |
| Người bảo trì | `eval/README.md` — bộ kiểm đã đỏ ở đâu, và chỗ nào còn chưa phủ |

Nguyên tắc: **thất bại một phần phải nhìn thấy được**. `say()` gọi 3 loa, 1 loa
chết, thì kết quả không được là "ok" trơn cũng không được là "failed" trơn —
phải là `ok` kèm bảng chi tiết chỉ đúng con nào hỏng.
