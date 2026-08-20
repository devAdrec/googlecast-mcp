# Bộ eval của googlecast-mcp

Trước khi đóng gói, product này **không có một test nào**. Đây là lỗ hổng lớn
nhất của nó. Bộ eval này vá được một phần — nó không phải test suite đầy đủ, mà
là lớp canh những hành vi mà nếu hỏng thì hoặc là im lặng, hoặc là gây ồn trong
nhà người khác.

## Ba tầng, chia theo TÁC DỤNG PHỤ

Nguyên tắc: **tầng mặc định không được có tác dụng phụ nào.** Một bộ test mà
không ai dám chạy thì bằng không có test.

| Tầng | Lệnh | Tác dụng phụ | Chạy được khi |
|---|---|---|---|
| offline (mặc định) | `python eval-googlecast-mcp.py` | **không có** | mọi máy, mọi lúc, kể cả CI, kể cả 2 giờ sáng |
| online | `... --online` | gọi ra internet (edge-tts). Không phát tiếng. | có mạng ra ngoài |
| hardware | `... --hardware --speaker "Kitchen speaker"` | **PHÁT TIẾNG THẬT trong nhà người ta** | phải xin phép trước |

Chạy đầy đủ:

```bash
uv run --directory /storage/apps/mcp/googlecast_mcp python \
    /storage/apps/mcp/googlecast_mcp/_dong-goi/package/eval/eval-googlecast-mcp.py
```

In pass/fail từng mục, exit 0 nếu tất cả xanh, 1 nếu có mục đỏ.

Kết quả gần nhất (2026-08-20): offline **43/43 pass, exit 0**; với `--online`
**45/45 pass, exit 0**. Tầng `--hardware` **chưa chạy trong phiên đóng gói này**
(chưa xin phép người dùng).

## Bộ eval canh những gì

- **Bề mặt tool**: import được; đúng 13 tool, đúng tên; tool nào cũng có mô tả.
- **Yêu cầu 3 — không chọn loa thì phải hỏi**: trả `needs_speaker_selection`,
  và quan trọng hơn: **không tổng hợp giọng, không cast**. Kiểm bằng spy ghi lại
  lời gọi, rồi khẳng định spy RỖNG. Đây là kiểu kiểm "chứng minh việc gì đó đã
  KHÔNG xảy ra" — với product có tác dụng phụ vật lý thì nó quan trọng hơn kiểm
  việc gì đó đã xảy ra.
- **`all` không được chồng nhóm với thành viên** (xem phần kiểm ngược bên dưới).
- **Cô lập lỗi**: một loa chết không được kéo theo các loa khác.
- **Lọc loa / thiết bị hình ảnh**, đoán MIME type, chọn giọng.
- **Allowlist transport**: có host trần không kèm port, có scheme `https`, và
  wildcard bind `0.0.0.0` không lọt vào danh sách tin cậy. Cả ba đều từ sự cố
  421/403 thật.
- **Text rỗng bị chặn** trước khi có bất cứ tác dụng phụ nào.

## KIỂM NGƯỢC — bộ eval này đã từng ĐỎ

Một bộ eval chưa bao giờ đỏ thì chưa chứng minh được điều gì: nó có thể đang
kiểm sai chỗ, hoặc kiểm một điều luôn đúng. Nên trước khi tin nó, phải đưa một
lỗi ĐÃ BIẾT trở lại và xem nó có bắt được không.

**Lỗi dùng để kiểm ngược**: `all` gửi tới cả nhóm loa lẫn thành viên của nhóm
(lỗi thật, đã sửa ở commit `fcf4035`).

### Quy trình — lặp lại được

1. Bảo đảm cây làm việc sạch: `git diff --quiet src/googlecast_mcp/server.py`
2. Đưa lỗi trở lại — trong `_select_targets` (`server.py`), thay dòng
   `return [s["friendly_name"] for s in speakers if s["cast_type"] != "group"], None`
   bằng `return names, None` (đúng dạng nguyên bản trước khi sửa).
3. Chạy eval offline.
4. Khôi phục: `git checkout -- src/googlecast_mcp/server.py`
5. Chạy lại eval offline.

### Kết quả đã ghi nhận (2026-08-20)

| Bước | Kết quả |
|---|---|
| Có lỗi | **40/43, exit 1** |
| Mục đỏ | `all: no speaker group included`<br>`all: every individual speaker included`<br>`all: Vietnamese 'tất cả' means the same thing` |
| Sau khi khôi phục | **43/43, exit 0** |

Đỏ đúng ba mục nói về `all`, không đỏ lan sang mục khác. Đó là điều cần thấy:
eval không chỉ biết đỏ, mà đỏ **đúng chỗ**.

### Một điều bộ eval tự phơi ra về chính nó

Khi có lỗi, mục `all: no duplicate physical device` **vẫn xanh**. Nó so trùng
theo TÊN, mà nhóm và thành viên có tên khác nhau — nên nó mù trước đúng loại
trùng lặp đang xảy ra (trùng ở mức thiết bị vật lý, không phải mức tên). Mục
thật sự bắt được lỗi là mục lọc theo `cast_type`.

Giữ lại ghi chú này thay vì lặng lẽ xoá mục kia, vì nó là bài học: **một mục
kiểm luôn xanh có thể đang tạo cảm giác an toàn giả**. Chỉ có kiểm ngược mới lộ
ra được.

## Fixture

Dữ liệu giả trong eval để `Family speaker group` và `Kitchen speaker` **cùng
host `192.168.1.22`** — đúng cấu hình thật đã làm lỗi chồng luồng nghe thấy
được. Fixture không nên là dữ liệu tròn trịa; nó nên mang hình dạng của sự cố đã
xảy ra.

## Bộ eval này KHÔNG canh được gì

Nói thẳng, để người sau không tưởng nhầm là đã an toàn:

- Không canh chất lượng âm thanh, không canh việc loa phát **đủ độ dài** (mới
  chỉ đo tay 3 clip).
- Không canh mDNS / hành vi mạng thật.
- Không canh cấu hình nginx, TLS, hay unit systemd.
- Không canh việc service sống sót qua reboot.
- Không canh giọng `male`, không canh tham số `rate`.
- **Không canh được lỗi chồng luồng ở đời thật** — nhớ rằng khi lỗi đó xảy ra,
  API báo `playing` cho mọi thiết bị. Tầng offline chỉ canh được phần logic
  chọn loa, tức là canh NGUYÊN NHÂN chứ không canh được HẬU QUẢ.
