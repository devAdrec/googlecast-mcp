# Prompt dựng lại googlecast-mcp từ đầu

Dán khối dưới đây cho một AI coding agent trong một thư mục trống. Nó đủ để dựng
lại một server **tương đương**, kể cả các ngõ cụt — vì mấy ngõ cụt đó tốn nhiều
thời gian nhất và không tự tránh được.

Muốn hiểu **cách nghĩ** thay vì chỉ lấy kết quả: đọc `method-note.md`.

---

```
Xây một MCP server bằng Python để đọc text tiếng Việt thành tiếng nói phát ra
loa Google (Google Cast) trong mạng nội bộ.

## Ba yêu cầu chức năng

1. Dò danh sách loa Google trong mạng nội bộ, sau đó LƯU LẠI (sống qua khởi
   động lại tiến trình).
2. Nhận text làm tham số của tool, chuyển thành âm thanh hỗ trợ tiếng Việt, rồi
   phát lên loa được chỉ định.
3. Nếu người dùng KHÔNG chọn loa thì phải hỏi lại xem phát ở loa nào, hoặc tất
   cả. Tuyệt đối KHÔNG tự phát ra tất cả — phát tiếng vào nhà người ta là tác
   dụng phụ vật lý không hoàn tác được, nên mặc định phải là KHÔNG LÀM GÌ.

## Ràng buộc kiến trúc — đọc kỹ trước khi thiết kế

Thiết bị Cast KHÔNG phải cái loa để ghi byte vào. Nó là máy phát nối mạng và TỰ
ĐI TẢI media qua HTTP. Hệ quả không thương lượng được:

- đường dẫn file trên máy là vô nghĩa với nó — phải là URL;
- URL phải với tới được từ phía thiết bị — phải là địa chỉ LAN;
- vậy server "nói được" BẮT BUỘC kiêm luôn một HTTP file server;
- và vì thế nó BẮT BUỘC nằm cùng LAN với loa. Không có cách lách. Ghi điều này
  vào tài liệu ngay, người sau sẽ hỏi "sao không chạy trên VPS được".

Địa chỉ BIND và địa chỉ QUẢNG BÁ là hai thứ khác nhau: bind `0.0.0.0` (nghe trên
mọi giao diện), nhưng quảng bá địa chỉ LAN thật (loa dùng nó để quay lại tải
file). Tìm địa chỉ LAN bằng cách mở một UDP socket hướng ra 8.8.8.8 rồi đọc
`getsockname()` — không gửi gói tin nào cả.

## Lựa chọn thư viện

- Giao thức Cast: `pychromecast`. Không cần so sánh gì — đây là thư viện Python
  duy nhất còn được bảo trì cho giao thức này. Thành phần xương sống thì chọn
  theo mức bảo trì và độ phủ giao thức, không cần bảng so sánh.
- TTS tiếng Việt: `edge-tts` (`vi-VN-HoaiMyNeural` nữ, `vi-VN-NamMinhNeural`
  nam). Miễn phí, không cần API key, giọng tự nhiên nhất trong các phương án
  miễn phí. Nếu bạn muốn đổi: đây là thành phần NGƯỜI DÙNG CẢM NHẬN ĐƯỢC, nên
  hãy dựng thử vài phương án, render cùng một câu, rồi ĐƯA HỌ NGHE mà chọn.
  Tiêu chí kỹ thuật (chi phí, cần key không, offline được không) thì bạn tự chấm.
- MCP SDK: `mcp[cli]>=1.13,<2`. PIN NÀY QUAN TRỌNG: trên PyPI có một gói `mcp`
  2.0.0 HOÀN TOÀN KHÔNG LIÊN QUAN, kéo theo `httpx2` (typosquat) và `mcp-types`.
  Bản đúng cần `httpx`, không phải `httpx2` — dùng đó để kiểm chứng.

## Cấu trúc module

- `cast_manager.py` — bọc `pychromecast`, an toàn với luồng; sở hữu việc dò
  thiết bị, cache kết nối, và các phương thức điều khiển đồng bộ.
- `speaker_store.py` — lưu thiết bị đã dò ra JSON (`~/.googlecast-mcp/`).
  GỘP theo uuid, đừng ghi đè: mDNS mất gói, một lần quét sót mà ghi đè sẽ XOÁ
  mất loa vừa dùng được năm phút trước. File hỏng phải đọc thành danh sách rỗng,
  không được làm chết server.
- `tts.py` — text → mp3, cache trên đĩa theo hash của (giọng, tốc độ, nội dung).
- `media_server.py` — HTTP server chạy nền phục vụ thư mục cache.
- `server.py` — định nghĩa tool FastMCP. `pychromecast` là thư viện chặn, nên
  mọi tool phải đẩy sang luồng phụ bằng `asyncio.to_thread`.
- `__main__.py` — CLI, chọn transport, nới danh sách host tin cậy.

## Những chỗ hỏng mà bạn PHẢI xử lý ngay từ đầu

Tất cả đều đã xảy ra thật. Không xử lý trước thì sẽ mất nhiều giờ để tìm lại.

1. TTS gọi dồn: dịch vụ TỪ CHỐI các kết nối đến CÙNG LÚC. Thử lại đơn thuần
   KHÔNG cứu được (đo thật: vẫn 4/6 đạt, 101 giây) vì các lần thử vẫn chồng lên
   nhau. Phải TUẦN TỰ HOÁ bằng một `asyncio.Lock`, cộng thêm 3 lần thử có giãn
   cách. Sau khi vá: 6/6 đạt, 12 giây.
   Sau khi giành được khoá thì KIỂM CACHE LẦN NỮA — trong lúc xếp hàng, người
   khác có thể đã render xong đúng câu đó rồi.

2. `save()` của edge-tts có thể TẠO FILE RỒI MỚI NÉM LỖI, để lại file 0 byte.
   File rỗng đó nằm lại trong cache và lần sau cache "trúng" nó → loa phát im
   lặng VĨNH VIỄN. Phải `unlink` trước mỗi lần thử, và coi file 0 byte là thất
   bại chứ không phải thành công.

3. `421 Misdirected Request`: SDK chỉ tin `127.0.0.1`. Bind `0.0.0.0` KHÔNG đủ.
   Nới allowlist (đừng TẮT bảo vệ DNS-rebinding — tắt là mở cho mọi trang web
   tấn công server nội bộ): thêm IP LAN, thêm cờ `--allow-host <domain>`, và
   thêm cả scheme `https` lẫn host KHÔNG kèm `:port` (proxy ở cổng 443 gửi Host
   trần).

4. CORS cho client trình duyệt: SDK trả `OPTIONS` = 405 không kèm header CORS,
   nên trình duyệt chặn và JS chỉ thấy "Failed to fetch" trống rỗng. Thêm
   `CORSMiddleware`, và BẮT BUỘC `expose_headers=["Mcp-Session-Id"]` — trình
   duyệt không đọc được header không được expose nên không nối tiếp phiên được,
   mà lỗi hiện ra vẫn y hệt. Origin phải khớp CHÍNH XÁC thanh địa chỉ.

5. Client khắt khe (llama-server chẳng hạn) báo "protocol error" chung chung vì
   không đọc được khung SSE và không mang session header. Thêm hai cờ
   `--json-response` và `--stateless`.

6. Sau nginx reverse proxy: `proxy_buffering off` và `proxy_read_timeout 3600s`.
   Thiếu thì client TREO và KHÔNG BÁO LỖI GÌ CẢ — lớp lỗi câm lặng, cực khó chẩn.

7. Script systemd: dùng `systemctl restart` TƯỜNG MINH. `systemctl enable --now`
   KHÔNG khởi động lại service đang chạy — tiến trình cũ từng sống 3 ngày trong
   khi mọi bản sửa đều đúng và đều không được nạp. Và lệnh `status` phải in
   `/proc/<MainPID>/cmdline`, tức DÒNG LỆNH TIẾN TRÌNH ĐANG THẬT SỰ CHẠY, tách
   hẳn khỏi nội dung unit file.

8. mDNS có thể sót thiết bị đã lưu, sinh ra `DeviceNotFoundError` tự mâu thuẫn
   ("không tìm thấy" một thiết bị đang nằm trong danh sách đã lưu). Trước khi
   quét lại, hãy thử kết nối THẲNG tới địa chỉ đã lưu.

9. `target="all"` phải BỎ nhóm loa. Nhóm Cast phát QUA thành viên của nó, nên
   gửi tới cả nhóm lẫn từng thành viên khiến một loa vật lý nhận HAI luồng.
   Điểm đáng sợ: cả bốn lệnh đều trả `playing` — API không phân biệt được. Dấu
   vết duy nhất là nhóm và thành viên trùng `host`. Nhóm vẫn phải gọi được khi
   người dùng nêu đích danh tên nó.

10. Thiết bị Cast có thể TREO: mDNS trả lời được, ping được, nhưng TCP 8009 từ
    chối → `wait timed out`. Khởi động lại thiết bị là hết. Kiểm
    `nc -z <ip> 8009` TRƯỚC khi nghi ngờ code.
    Và đừng vội kết luận: có lần CẢ HAI Nest Hub cùng đóng cổng, dẫn tới kết
    luận sai "firmware bỏ cổng 8009". Hai mẫu trùng nhau đủ để đặt giả thuyết,
    KHÔNG đủ để kết luận nguyên nhân hệ thống.

11. Tên miền cho https KHÔNG ĐƯỢC chứa dấu gạch dưới. CA/B Forum cấm, nên không
    CA nào cấp chứng chỉ — mà Claude Desktop lại bắt buộc https. Đó là ngõ cụt
    tuyệt đối, không phải chuyện cấu hình sai.

12. Claude Desktop ở ô "Add custom connector" chỉ nhận URL https. Server LAN
    chạy http phải bắc cầu bằng `npx -y mcp-remote http://<ip>:<port>/mcp
    --allow-http` trong `claude_desktop_config.json`.

## Bộ kiểm — viết cùng lúc, không viết sau

Ba tầng, mặc định là tầng VÔ HẠI: offline (chỉ thư mục tạm) / `--online` (chạm
dịch vụ TTS thật) / `--hardware` (PHÁT TIẾNG THẬT — phải xin phép trước mỗi lần
chạy). Bài kiểm mà không ai dám chạy thì bằng như không có.

Luật bắt buộc:

- ĐẾM ĐỦ TRƯỚC KHI ĐẾM XANH: mỗi mục bọc riêng, lỗi hạ tầng là ERROR chứ không
  được nuốt; báo cáo in "đã chạy X/Y mục đăng ký"; X<Y là FAIL TOÀN CỤC.
- So TẬP tường minh, không so kích thước. `len(a)==len(b)` vẫn xanh khi cả hai
  cùng co lại còn một phần tử.
- Mỗi mục phải GỌI VÀO mã sản phẩm, không được viết lại logic ngay trong bài
  kiểm.
- Vệ sinh mock: luôn khôi phục sau mỗi phép thử; thay thế ở tầng THẤP NHẤT có
  thể để mã sản phẩm còn chạy thật; thêm "residue guard" so lại danh tính gốc
  sau mỗi mục để quy lỗi đúng chỗ rò. CẤM `importlib.reload`.
- Việc bất đồng bộ: chờ bằng BẰNG CHỨNG BỀN, không bắt trạng thái thoáng qua.
  Ví dụ thật: kiểm loa từng đỏ oan vì bắt `PLAYING`, trong khi clip dài 2.26s
  còn lệnh mất 5.4s nên lúc quay lại nhìn thì loa ĐÃ PHÁT XONG. Đúng là chờ
  `content_id` khớp URL vừa cast VÀ `duration > 0`. Và phải hỏi qua ĐÚNG kết nối
  đã cast — trạng thái media là theo từng kết nối, kết nối khác báo UNKNOWN mãi.

Rồi viết thêm một script KIỂM NGƯỢC HAI CHIỀU:

- gieo từng lỗi đã biết vào một BẢN SAO của product dưới thư mục tạm (đặt
  `PYTHONPATH` trỏ vào bản sao, `PYTHONDONTWRITEBYTECODE=1`, TUYỆT ĐỐI không ghi
  vào cây sản phẩm — hoàn nguyên khi đó là hệ quả của cấu trúc, không phải của
  trí nhớ);
- mỗi lỗi gieo mang danh sách id mục PHẢI ĐỎ, viết TRƯỚC khi chạy. Mục trong
  danh sách mà vẫn xanh = TEST GIẢ;
- kèm vài ĐỐI CHỨNG VÔ HẠI (thêm chú thích, sửa lời docstring) và đòi chúng để
  bộ kiểm XANH. Đỏ ở đối chứng là ĐỎ BỪA, hỏng ngang test giả;
- cuối cùng chạy lại trên cây NGUYÊN VẸN và đòi XANH — đó, chứ không phải
  `git status`, mới là bằng chứng không rò rỉ gì;
- in ra mục nào KHÔNG lỗi gieo nào làm đỏ được: đó là nghi phạm cấu trúc.

Khi kiểm ngược báo một mục xanh dù lẽ ra phải đỏ, hãy phân biệt cho đúng:
TEST GIẢ (mục chưa từng chạm hành vi đó → sửa bài kiểm) khác với KỲ VỌNG SAI
(mục có chạm nhưng đòi sai điều → sửa KỲ VỌNG theo requirement, có TRÍCH NGUỒN).
Cấm nới bài kiểm cho xanh.

## Bàn giao

Viết README đi từ số 0 tới lúc GỌI ĐƯỢC TOOL, rồi TỰ CHẠY LẠI từng lệnh trong đó
trên một bản clone sạch ở thư mục khác, và dán output thật vào làm bằng chứng.
"Đọc thấy ổn" không phải là bằng chứng.
```
