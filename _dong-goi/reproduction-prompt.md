# Prompt dựng lại googlecast-mcp

Dán trọn phần trong khung dưới cho một AI có quyền chạy lệnh và ghi file, trên
một máy Linux **cùng mạng LAN với loa Google**. Mục tiêu là dựng lại đúng
product này từ con số không.

Prompt cố ý **không** nói trước các đáp án đã tìm ra ở lần đầu (chọn thư viện
nào, sửa lỗi mạng ra sao). Nó nêu yêu cầu và ràng buộc, để bản dựng lại vẫn
phải tự đi qua các quyết định. Muốn đối chiếu đáp án thì đọc `method-note.md`
sau khi làm xong, đừng đọc trước.

---

```
Xây cho tôi một MCP server bằng Python, chạy trên máy Linux cùng mạng LAN với
loa Google Cast trong nhà tôi. Ba yêu cầu:

1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
2. gửi tin nhắn là text tham số truyền vào mcp sau đó chuyển thanh âm thanh
   hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ràng buộc:
- Python 3.11+, quản lý phụ thuộc bằng uv.
- Dùng MCP SDK chính thức (modelcontextprotocol/python-sdk), FastMCP.
  Ghim phiên bản dưới 2.0 và kiểm tra kỹ: trên PyPI có một gói tên "mcp"
  phiên bản 2.0.0 KHÔNG liên quan, kéo theo httpx2 và mcp-types. Trước khi
  ghim, xác minh gói bạn chọn phụ thuộc httpx (không phải httpx2).
- TTS tiếng Việt phải không cần khoá API, không cần tài khoản.
- Phải chạy được cả stdio (client cùng máy) lẫn streamable HTTP (client máy khác).
- Phải chạy được như systemd service, có install/remove/start/stop/restart/
  status/logs.

Cách làm việc tôi muốn:

A. TRƯỚC KHI THIẾT KẾ, hãy trả lời: giao thức Google Cast bắt buộc phía server
   phải cung cấp những gì? Liệt kê ràng buộc không né được và hệ quả kiến trúc
   của từng cái. Đừng đề xuất giải pháp vội.

B. CHỌN THƯ VIỆN — tách hai loại:
   - Thành phần tôi CẢM NHẬN ĐƯỢC (giọng đọc): so sánh vài phương án, tự chấm
     phần kỹ thuật (cần khoá API không, chi phí, phụ thuộc, mức bảo trì), nhưng
     phần "nghe có tự nhiên không" thì ĐỪNG tự chấm — dựng mẫu thật của từng
     phương án cho tôi tự nghe. MỘT VÒNG THÔI.
   - Thành phần XƯƠNG SỐNG (thư viện giao thức Cast): chọn theo mức độ còn được
     bảo trì và độ phủ giao thức. Nếu chỉ có một lựa chọn còn sống thì nói thẳng,
     đừng dựng bảng so sánh cho có.

C. THIẾT KẾ TRƯỚC hành vi khi THIẾU thông tin, trước khi viết chức năng chính.
   Việc này phát ra tiếng thật trong nhà tôi — tác dụng phụ không rút lại được.
   Thiếu tên loa thì tuyệt đối không được đoán bừa, và cũng không được phát ra
   tất cả loa.

D. BỘ KIỂM phân tầng theo tác dụng phụ:
   - tầng mặc định: KHÔNG mạng, KHÔNG tiếng, KHÔNG chạm thiết bị thật, và không
     được ghi đè file dữ liệu thật của tôi. Đẩy được bao nhiêu kiểm tra xuống
     tầng này thì đẩy.
   - tầng --online: được dùng internet, vẫn không phát tiếng.
   - tầng --hardware: cast thật, phát tiếng thật. Phải hỏi tôi trước khi chạy.
   Bộ dữ liệu giả phải có tình huống: một NHÓM loa và một THÀNH VIÊN của nhóm
   đó là cùng một cái loa vật lý (cùng địa chỉ host).

E. KIỂM NGƯỢC bộ kiểm, theo đúng thứ tự sau:
   1. Viết ra TRƯỚC danh sách những mục sẽ phải đỏ khi cấy một lỗi cụ thể vào.
   2. Cấy lỗi. Chạy.
   3. So kỳ vọng với thực tế. Mục nào LẼ RA ĐỎ MÀ VẪN XANH là test giả — phải
      SỬA cho nó bắt được, hoặc ghi rõ CHƯA PHỦ. Chỉ chú thích lại là không đủ.
   4. Khôi phục, rồi xác minh mã nguồn đã sạch (git diff phải rỗng).
   Ghi trọn quy trình và số liệu vào README của thư mục kiểm.

F. VIẾT TÀI LIỆU CÀI ĐẶT theo phép thử này: một người lạ, máy sạch, CHỈ đọc
   file đó, có đưa được server tới chỗ GỌI ĐƯỢC TOOL không? Không dừng ở "cài
   xong". Không giả định người đọc đã có sẵn công cụ hay đang đứng trong repo.
   Viết xong thì tự chạy lại TỪNG lệnh trên một bản clone trắng và dán output
   thật vào làm bằng chứng. Dùng cổng rỗi, đừng đụng dịch vụ đang chạy.

Khi gặp lỗi tầng mạng: mỗi mã lỗi HTTP là một câu trả lời cụ thể, lập bảng tra
thay vì đoán. Nếu hệ thống IM LẶNG (treo, không lỗi, không log) thì nghi tầng
trung gian (proxy, trình duyệt) trước khi nghi mã nguồn của bạn.

Nếu tôi lặp lại y hệt một câu than phiền hai lần, ĐỪNG sửa tiếp — hãy kiểm tra
xem bản sửa của bạn đã thực sự được NẠP vào tiến trình đang chạy chưa.

Trước khi kết luận một nguyên nhân hệ thống từ vài thiết bị cùng hỏng: hai mẫu
trùng nhau không đủ. Cho tôi phép thử rẻ nhất tách được các giả thuyết.
```

---

## Kỳ vọng đầu ra

Dựng lại thành công thì phải có:

- `src/…/{cast_manager, speaker_store, tts, media_server, server, __main__}.py`
  hoặc tương đương — trong đó **có một HTTP file server**, vì giao thức Cast bắt
  buộc thế.
- 13 tool: `say` cộng 12 tool điều khiển.
- `say` thiếu tên loa → **không phát gì, không tổng hợp gì**, trả về danh sách
  loa kèm câu dặn mô hình hỏi lại.
- `all` → **bỏ qua nhóm loa** (nhóm vẫn phát được khi gọi đích danh).
- Script quản lý systemd dùng `restart`, **không** `enable --now`.
- Bộ kiểm ba tầng, đã kiểm ngược, có ghi lại danh sách kỳ vọng viết trước.
- Tài liệu cài đặt đã qua phép thử "người lạ, máy sạch, gọi được tool".

## Những chỗ bản dựng lại nhiều khả năng sẽ vấp

Đây là danh sách để **đối chiếu sau khi làm xong**, không phải để đọc trước:

- `421 Misdirected Request` với client ở máy khác — bind `0.0.0.0` không đủ.
- Allowlist thiếu scheme `https`, hoặc thiếu host trần không kèm `:port`.
- CORS quên expose header `Mcp-Session-Id`.
- nginx buffering làm client treo im lặng.
- Tên miền có dấu gạch dưới → không bao giờ xin được chứng chỉ.
- `enable --now` không khởi động lại tiến trình đang chạy.
- `all` gửi tới cả nhóm lẫn thành viên → chồng luồng, mà **API vẫn báo
  `playing`**.
- Mục test chống trùng lặp so theo **tên** thay vì theo **host** → xanh giả.
- `pkill -f "<mẫu>"` khớp luôn chính lệnh bash đang chạy → tự giết shell.

Giải thích đầy đủ từng cái: `method-note.md` và `package/technical-docs.md`.
