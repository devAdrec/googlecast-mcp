# Kỹ thuật — ràng buộc triển khai

**Kiến trúc đầy đủ ở `docs/architecture.md` (gốc repo). Đó là tài liệu SỐNG —
đọc nó trước.** File này chỉ ghi những ràng buộc mà người triển khai buộc phải
biết trước khi đụng vào cấu hình, và những điểm hở chưa vá.

| Muốn biết | Đọc ở đâu |
|---|---|
| Luồng dữ liệu, vai trò từng module | `docs/architecture.md` |
| Cờ dòng lệnh, cách nối client | `README.md` (gốc repo) và `package/README.md` |
| Cài từ số 0 | `package/README.md` |
| Cách kiểm chứng | `package/eval/README.md` |

---

## 1. Ràng buộc kiến trúc không thương lượng được

### 1.1 Server "nói được" bắt buộc kiêm HTTP file server

Thiết bị Cast **tự đi tải media qua HTTP**; nó không đọc được đường dẫn file
trên máy bạn. Nên `media_server.py` không phải tiện ích thêm vào cho vui — nó
là điều kiện tồn tại của tính năng `say`.

Hệ quả trực tiếp:

- Máy chạy server **phải cùng LAN với loa**. Đặt lên đám mây thì không dùng
  được, dù MCP endpoint vẫn trả lời bình thường.
- Có **hai** cổng phải mở, không phải một: cổng MCP (8765) và cổng audio (8766).

### 1.2 Bind ≠ địa chỉ quảng bá — hai thứ KHÁC NHAU

`media_server.py:76` bind `0.0.0.0` (nghe trên mọi giao diện), nhưng URL đưa cho
loa dựng từ `lan_ip()`. Nhầm hai thứ này là hỏng: quảng bá `0.0.0.0` thì loa
không bao giờ tải được file, mà server vẫn "chạy tốt".

`lan_ip()` học địa chỉ bằng cách mở một socket UDP hướng ra 8.8.8.8 và đọc lại
giao diện kernel chọn. **Không có gói tin nào được gửi.**

### 1.3 Giữ bảo vệ DNS-rebinding của SDK, chỉ NỚI allowlist

SDK chỉ tin `127.0.0.1`, nên client từ máy khác nhận `421 Misdirected Request`.
Cách chữa **không phải** tắt kiểm tra — tắt là mở đường cho bất kỳ trang web nào
người dùng mở tấn công server nội bộ. `__main__.py:46-69` nới danh sách, và
danh sách đó phải có đủ **bốn dạng**:

| Dạng | Vì sao cần |
|---|---|
| `host` trần, không kèm `:port` | reverse proxy ở cổng mặc định (443) không gửi `:port` trong header `Host` |
| `host:*` | truy cập trực tiếp có cổng |
| scheme `http` | LAN |
| scheme `https` | khi có proxy kết thúc TLS phía trước |

Thiếu **một** trong bốn là 421 ở đúng một tình huống, và thông báo lỗi không hề
nói cho bạn biết thiếu dạng nào.

### 1.4 Tên miền có dấu gạch dưới KHÔNG BAO GIỜ xin được chứng chỉ

CA/Browser Forum cấm ký tự `_` trong tên miền chứng chỉ. `google_cast.example`
là ngõ cụt tuyệt đối — không phải "khó", mà là **không tồn tại đường đi**. Vì
Claude Desktop bắt buộc https, dùng gạch dưới là tự chặn mình. Dùng gạch nối:
`google-cast.adrec.cloud`.

### 1.5 Ghim `mcp[cli]>=1.13,<2`

Trên PyPI có một gói tên `mcp` phiên bản 2.0.0 **hoàn toàn không liên quan** tới
SDK chính thức; nó kéo theo `httpx2` (dạng typosquat) và `mcp-types`. Cách nhận
ra bản thật: nó phụ thuộc `httpx`, không phải `httpx2`. Đừng bỏ ghim.

## 2. Cấu hình reverse proxy — hai dòng bắt buộc

Xem `scripts/nginx-googlecast-mcp.conf`. Hai chỉ thị không được thiếu:

```nginx
proxy_buffering off;         # thiếu → client TREO, KHÔNG có thông báo lỗi nào
proxy_read_timeout 3600s;    # SSE là kết nối dài
```

Triệu chứng của việc thiếu `proxy_buffering off` là **im lặng**: không log,
không mã lỗi, client chỉ đứng im. Đó là loại lỗi tốn nhiều giờ nhất.

## 3. CORS cho client trình duyệt

SDK trả `OPTIONS` = **405** và không có header CORS, nên trình duyệt chặn ở bước
preflight và JavaScript chỉ nhận được `"Failed to fetch"` — không có gì để đọc.

`__main__.py:37` gắn `CORSMiddleware`, và **bắt buộc** phải có:

```python
expose_headers=["Mcp-Session-Id", "mcp-session-id"]
```

Không expose thì trình duyệt không đọc được session id, và **không duy trì được
phiên** — mặc dù preflight đã qua. Origin phải khớp **chính xác** chuỗi trên
thanh địa chỉ, kể cả cổng.

## 4. Vận hành

### 4.1 `systemctl enable --now` KHÔNG khởi động lại service đang chạy

Đây là lý do một bản sửa từng sống trong repo **3 ngày** mà không có tác dụng,
và người dùng phải nói "vẫn lỗi" ba lần. `scripts/service.sh:78-80` gọi
`restart` tường minh.

`service.sh status` (dòng 112-115) in `/proc/<MainPID>/cmdline`: **file unit có
thể khác hẳn dòng lệnh mà tiến trình đang chạy thật.** Luôn đọc dòng đó.

### 4.2 Phân biệt thiết bị treo với lỗi mã nguồn

Thiết bị Cast có thể trả lời mDNS, trả lời ping, mà **từ chối TCP 8009** →
`wait timed out`. Khởi động lại thiết bị là hết.

```bash
nc -z 192.168.1.31 8009    # chạy cái này TRƯỚC khi nghi ngờ mã nguồn
```

> Bài học suy luận: đã từng kết luận sai rằng "Nest Hub bỏ cổng 8009 do
> firmware" chỉ vì **cả hai** Nest Hub trong nhà cùng đóng cổng. Hai mẫu trùng
> nhau không đủ để suy ra nguyên nhân hệ thống.

### 4.3 `pkill -f "<mẫu>"` khớp luôn chính shell đang chạy nó

Chuỗi mẫu nằm trong dòng lệnh của shell, nên `pkill -f` tự giết mình (exit 144).
Lọc theo cổng hoặc PID thay vì theo chuỗi lệnh.

## 5. Triển khai đang chạy thật

| Hạng mục | Giá trị |
|---|---|
| Máy | `192.168.1.128`, systemd unit `googlecast-mcp.service` |
| Cổng MCP / audio | `8765` / `8766` |
| nginx | `/etc/nginx/conf.d/adrec_cloud.conf`, TLS Let's Encrypt |
| Tên miền | `google-cast.adrec.cloud` |
| Client | Claude Desktop (`192.168.1.28`) qua https; llama-server webui (`192.168.1.99:8383`) qua CORS |

```bash
MCP_EXTRA_ARGS="--allow-host google-cast.adrec.cloud --json-response --stateless \
  --cors-origin http://192.168.1.99:8383" ./scripts/service.sh install
```

## 6. ĐIỂM CÒN HỞ — chưa vá, không tô hồng

| # | Vấn đề | Mức | Trạng thái |
|---|---|---|---|
| 1 | **Không có xác thực ở tầng ứng dụng.** `google-cast.adrec.cloud` phân giải CÔNG KHAI ra internet. Ai gọi được endpoint là phát được tiếng vào nhà. | Cao | CHƯA VÁ |
| 2 | **Cổng audio 8766 bind `0.0.0.0`, không xác thực**, phục vụ nguyên thư mục cache TTS. Chặn IP ở nginx chỉ che 8765, **không che 8766**. | Cao | CHƯA VÁ |
| 3 | Hai dòng chặn IP trong cấu hình nginx đã đồng ý bật nhưng **vẫn đang bị comment**. | Trung bình | CHƯA BẬT |
| 4 | Cache TTS tăng vô hạn, không có cơ chế dọn. | Thấp | CHƯA VÁ |
| 5 | Không khôi phục âm lượng / media đang phát sau khi thông báo xong. | Thấp | CHƯA LÀM |
| 6 | ~~`tts.synthesize` không thử lại~~ — **ĐÃ VÁ.** Nguyên nhân sâu hơn báo cáo ban đầu: chỉ thêm thử lại vẫn hỏng (đo: 4/6 đạt, mất 101s) vì các lần thử vẫn chồng lên nhau và dịch vụ từ chối kết nối. Vá bằng **khoá tuần tự hoá** (`_synthesis_lock`) + thử lại 3 lần có giãn cách. Đo lại: **6/6 đạt, 12s**. | — | Đã vá |
| 7 | ~~Cache đọng file 0 byte khi `save()` ném lỗi~~ — **ĐÃ VÁ.** Bọc `save()` trong `try/except`, `unlink` trước mỗi lần thử lại. Đo lại sau đợt dồn dập: **0 file 0 byte còn đọng**. | — | Đã vá |

## 7. Chưa từng thử

Ghi ra để người sau không tưởng là đã có bảo chứng:

- Giọng nam `vi-VN-NamMinhNeural` — chưa ai nghe bằng tai.
- Tham số `rate` — chưa nghe bằng tai (mới chỉ kiểm bằng kích thước file).
- Service sống sót qua **reboot máy** — đã `enable`, chưa reboot lần nào.
- Nhánh quét lại khi loa **đổi IP** làm địa chỉ đã lưu bị cũ.
- Chặn IP ở nginx (xem điểm hở #3).
