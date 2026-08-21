# Harness spec — 5 lớp

`googlecast-mcp` là **harness vận hành**: đầu vào xác định, đầu ra xác định,
đúng/sai kiểm được bằng máy. Trọng số vì thế dồn vào lớp Tool và lớp Eval, chứ
không phải lớp Context như một harness sinh nội dung.

Có đúng **một** chỗ máy không kiểm được: âm thanh nghe ra sao. Chỗ đó phải có
tai người, và spec này ghi thẳng ra thay vì giả vờ là đã tự động hoá.

---

## 1. Context — mô hình cần biết gì để gọi đúng

Trọng số: **trung bình.** Mô hình chỉ cần biết có những loa nào và tên chúng là gì.

| Nguồn context | Ở đâu |
|---|---|
| Danh sách loa hiện có | `list_speakers` (đọc kho bền, tự dò nếu kho rỗng) |
| Kho bền | `~/.googlecast-mcp/speakers.json`, gộp theo `uuid` |
| Cách dùng từng tool | docstring của tool — đây là toàn bộ hướng dẫn mà mô hình nhận được |
| Hướng dẫn khi thiếu loa | chính chuỗi `message` trong `needs_speaker_selection` |

Quyết định đáng chú ý: khi thiếu tên loa, server **không** dùng MCP elicitation
để tự hỏi người dùng. Nó trả về dữ liệu kèm một câu hướng dẫn, để **mô hình**
hỏi. Elicitation nhiều client chưa hỗ trợ; trả dữ liệu thì chạy ở mọi client.
Nói cách khác: chỗ nào giao thức còn non, đẩy việc lên tầng ngôn ngữ.

## 2. Tool — bề mặt gọi

Trọng số: **cao.**

13 tool. Một tool "chủ" (`say`) và 12 tool điều khiển. Ba luật thiết kế:

1. **Tham số bắt buộc thiếu thì không được đoán bừa.** `say` thiếu loa thì trả
   về câu hỏi, không phát ra tất cả. Sai lầm ở đây không rút lại được.
2. **Mọi lệnh chặn đều đẩy sang worker thread** (`asyncio.to_thread`).
   pychromecast là thư viện chặn, giữ socket lâu dài; để nó trên event loop là
   treo cả server.
3. **Mỗi loa hỏng độc lập.** `say` gom kết quả từng loa; một loa lỗi trả `error`
   riêng, các loa còn lại vẫn phát, tổng thể vẫn `ok`.

Ràng buộc kiến trúc không né được: **thiết bị Cast tự đi tải media qua HTTP**.
Vì thế lớp Tool bắt buộc phải kèm một HTTP file server (`media_server.py`). Đây
không phải lựa chọn thiết kế, đây là hình dạng mà giao thức Cast áp đặt.

## 3. Execution — chạy ở đâu, đường đi thế nào

Trọng số: **cao** — đây là nơi tốn nhiều ngày nhất.

```
client MCP ──https/LAN──▶ :8765 /mcp ──▶ say()
                                          │
                                          ├─▶ edge-tts (internet) ─▶ mp3 trong cache
                                          │
                                          └─▶ pychromecast ─▶ bảo loa: "tải URL này"
                                                                     │
                          :8766 HTTP file server ◀────────────────────┘
```

Bốn ràng buộc cứng:

- Server **phải cùng LAN với loa**. mDNS không qua router, và loa phải quay lại
  tải file được.
- **Bind ≠ địa chỉ quảng bá.** Bind `0.0.0.0`, nhưng URL đưa cho loa dựng từ
  `lan_ip()`. Nhầm hai thứ này thì `netstat` vẫn đẹp mà loa vẫn câm.
- **Allowlist phải nới, không được tắt.** Chi tiết ở `technical-docs.md` mục 2.
- **Nạp lại phải tường minh.** `enable --now` không khởi động lại tiến trình
  đang chạy. `service.sh` dùng `restart` và in `/proc/<pid>/cmdline` trong
  `status` — để câu hỏi "bản sửa đã được nạp chưa?" luôn trả lời được bằng mắt.

## 4. Eval — làm sao biết nó đúng

Trọng số: **cao nhất.**

Ba tầng phân theo tác dụng phụ, xem `eval/README.md`. Ba luật:

1. **Mặc định phải là tầng không tác dụng phụ.** Test mà không ai dám chạy thì
   bằng không có. Cast là opt-in.
2. **Bộ eval phải từng đỏ, với kỳ vọng viết ra trước.** Liệt kê trước mục nào
   phải đỏ → cấy lỗi → so kỳ vọng với thực tế. Mục nào *lẽ ra đỏ mà xanh* là
   **TEST GIẢ**: phải sửa cho nó bắt được, hoặc ghi rõ **CHƯA PHỦ**. Chú thích
   suông không phải một lựa chọn — nó để lại một ô xanh giả trong bảng.
3. **Đo cái đúng, không đo cái dễ đo.** Bài học đắt nhất của product này: mục
   chống trùng lặp so theo *tên* thì xanh trong khi lỗi đang tồn tại, vì trùng
   lặp thật nằm ở mức *thiết bị vật lý*. So theo `host` mới bắt được.

Ranh giới thành thật: eval chứng minh được `all` gửi tới đúng tập loa. Nó
**không** chứng minh được âm thanh nghe ra sao. Với lỗi chồng luồng thì cả bốn
thiết bị đều báo `playing` — API mù hoàn toàn. Tác dụng phụ vật lý cần nghiệm
thu bằng giác quan, và spec này không giả vờ ngược lại.

## 5. Feedback — sai thì biết bằng cách nào

Trọng số: **trung bình.**

| Kênh | Trả lời được câu hỏi gì |
|---|---|
| kết quả từng loa trong `say` | loa nào phát được, loa nào không, vì sao |
| `audio_url` trả về | `curl` chính URL đó → phân biệt lỗi loa với lỗi mạng |
| mã HTTP (421/403/406/405) | mỗi mã trỏ đúng một nguyên nhân, xem bảng ở `technical-docs.md` |
| `service.sh status` | tiến trình đang chạy bằng **dòng lệnh nào** — chống ảo giác "đã sửa rồi" |
| `journalctl -u googlecast-mcp -f` | log thời gian thực |
| `nc -z <ip> 8009` | thiết bị treo hay mã nguồn sai |

Kênh cuối cùng, không tự động hoá được: **người dùng nghe rồi nói lại**. Đây là
kênh duy nhất bắt được lỗi chồng luồng.

Hai tín hiệu phản hồi đáng đọc kỹ hơn nội dung của chúng:

- **Người dùng lặp lại y hệt một câu than phiền** ("vẫn báo lỗi", "vẫn báo lỗi")
  → đừng sửa tiếp. Kiểm xem **bản sửa đã được nạp chưa**. Trong lịch sử product
  này, tín hiệu đó đã bị bỏ lỡ trọn một vòng.
- **Hai lần đo mâu thuẫn về cùng một thiết bị** → giữ lịch sử đo. Chỉ có lịch
  sử mới phân định được "thiết bị hỏng" với "mã nguồn hồi quy".
