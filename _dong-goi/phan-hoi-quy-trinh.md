# Phản hồi quy trình đóng gói — từ phiên googlecast-mcp, 2026-08-26

Gửi người bảo trì bản chuẩn `dong-goi-product` trong vault Adrec. Đây là đề xuất
vá **bản vault**, rồi tái sinh bản solo — không sửa file quy trình tại chỗ.

Bản dùng trong phiên: **solo v1.7** (sinh từ vault v1.7).

---

## 1. Thêm một họ TEST GIẢ thứ bảy: **khẳng định ngoài vòng đời bằng chứng**

**Mức: nên vá.** Đây là lỗi đã xảy ra thật trong phiên này.

v1.7 liệt kê các dạng test giả: so kích thước, sập giữa chừng, không chạm sản
phẩm. Thiếu một dạng nữa, và nó gây **đỏ bừa** chứ không phải xanh giả:

```python
with tmpdir() as d:
    paths = await render_everything(cache_dir=d)
good = [p for p in paths if p.exists()]     # ← d ĐÃ BỊ XOÁ ở dòng trên
assert len(good) == 6                        # → 0/6, trong khi product hoàn toàn đúng
```

Mục `online.fanout_all_survive` báo **0/6** trong khi chạy tay đúng đoạn đó ra
**6/6 trong 15.6 giây**. Suýt nữa thì bị ghi thành "khiếm khuyết product".

**Đề xuất câu luật:** *"Bằng chứng nằm ở đâu thì phép khẳng định phải sống trong
cùng vòng đời với chỗ đó. Thư mục tạm, kết nối, tiến trình con — đóng trước khi
đếm là đếm vào chỗ trống."*

Nó ghép tự nhiên vào luật số (4) hiện có về **bằng chứng bền**: v1.7 mới lo
bằng chứng *biến mất theo thời gian*, chưa lo bằng chứng *biến mất theo phạm vi*.

## 2. Kiểm ngược: gieo lỗi vào **bản sao**, đừng sửa cây sản phẩm

**Mức: nên vá — nâng cấp thẳng, không chỉ là gợi ý.**

v1.7 nói "gieo lỗi rồi hoàn nguyên", và phải thòng thêm luật (7) *"hoàn nguyên =
chạy lại eval thấy XANH sau khi xoá bytecode"* để chống rò `.pyc`.

Cách mạnh hơn: **không bao giờ ghi vào cây sản phẩm.** Sao `src/` + file cấu hình
sang thư mục tạm mới cho **mỗi** case, gieo lỗi ở đó, chạy eval với
`PYTHONPATH` trỏ vào bản sao và `PYTHONDONTWRITEBYTECODE=1`.

Khi đó hoàn nguyên là **hệ quả của cấu trúc**, không phải của trí nhớ hay kỷ luật.
Rủi ro "quên hoàn nguyên rồi commit lỗi gieo vào product" biến mất hoàn toàn.
Luật (7) vẫn giữ, nhưng thành **bước xác nhận cuối** (chạy lại trên cây nguyên
vẹn, đòi XANH) chứ không còn là hàng phòng thủ duy nhất.

Đã làm thật ở `_dong-goi/package/eval/reverse-check.py`, chạy 49 case sạch.

## 3. "Mục xanh dù gieo lỗi" **không phải lúc nào cũng là test giả**

**Mức: nên vá — luật hiện tại kết tội oan.**

v1.7 viết: *lẽ-ra-đỏ-mà-xanh = TEST GIẢ*. Phiên này gặp **ba** trường hợp xanh, và
chỉ **một** là test giả thật:

| Trường hợp | Sự thật | Phải làm gì |
|---|---|---|
| bỏ `server_close()` mà eval vẫn xanh | `SO_REUSEADDR` + refcount **che mất** lỗi gieo — lỗi này *không quan sát được từ bên ngoài* | đổi **lỗi gieo**, không đổi bài kiểm |
| tắt lần kiểm cache thứ nhất mà vẫn xanh | lần kiểm **thứ hai** vẫn bắt được → đây là hồi quy **hiệu năng**, không phải correctness | gieo cả hai chỗ; ghi giới hạn vào eval/README |
| mục `no_speakers_found` xanh dù `say` mặc định phát tất cả | **KỲ VỌNG SAI**: nhánh mạng-rỗng trả về ở dòng trước đoạn bị gieo lỗi | sửa **kỳ vọng**, trích nguồn dòng mã |

Chỉ trường hợp thứ ba mới thuộc luật (3) hiện có. Hai trường hợp đầu là loại thứ
tư: **lỗi gieo không quan sát được**.

**Đề xuất:** tách thành ba nhánh định đoạt thay vì hai —
*test giả* (bài kiểm sai) / *kỳ vọng sai* (kỳ vọng sai) / **lỗi gieo không quan
sát được** (lỗi gieo sai — đổi lỗi gieo, hoặc ghi CHƯA PHỦ kèm cơ chế che).
Không có nhánh thứ ba thì người làm sẽ bị đẩy tới chỗ *sửa bài kiểm cho nó đỏ*,
tức là làm bài kiểm tệ đi để thoả một luật.

## 4. B4 phải chạy **sau khi** mọi file trong `_dong-goi/` đã tồn tại

**Mức: nên vá — lỗi thứ tự, rẻ mà hay tái phạm.**

Phiên này giao B4 cho evaluator **song song** với lúc còn đang viết
`reproduction-prompt.md`. Evaluator đọc note, thấy bảng "Đi tiếp" trỏ sang file đó,
kiểm tra, thấy **không tồn tại**, và ghi nó thành **lỗ hổng nặng nhất**. File được
viết xong vài phút sau đó — lỗ hổng tự tan, nhưng đã tốn một vòng chấm.

**Đề xuất:** B4 ghi rõ *"chỉ giao evaluator khi mọi file được method note trỏ tới
đã tồn tại trên đĩa"*. Kèm một bước kiểm rẻ: quét mọi đường dẫn trong note và
xác nhận nó tồn tại, **trước** khi gọi evaluator.

## 5. DoD cần ô "bước nào KHÔNG chạy lại được, và vì sao"

**Mức: nên vá.**

v1.7 nói *"chạy lại từng lệnh README, dán output vào B6"*. Nhưng có bước **cố ý
không được chạy lại**: `./scripts/service.sh install` sẽ cài đè lên service thật
đang phục vụ hai máy khác — chạy lại là **cắt dịch vụ của người đang dùng**.

Luật hiện tại đẩy người làm vào thế nhị nguyên xấu: hoặc chạy và gây hại, hoặc
lặng lẽ bỏ qua rồi báo `package: CÓ`.

**Đề xuất:** DoD có ba trạng thái cho mỗi bước, không phải hai —
**đã chạy lại** (kèm output) / **không chạy lại được** (kèm *lý do* + *đã kiểm
chứng ở đâu trước đó*) / **chưa chạy** (= thiếu sót thật). Trạng thái giữa là hợp
lệ; trạng thái thứ ba thì không.

## 6. B6 thiếu ô "khiếm khuyết product phát hiện trong phiên, CHƯA vá"

**Mức: nên vá.**

Viết bộ eval làm lộ ra một khiếm khuyết thật của product: `tts._synthesis_lock` là
`asyncio.Lock` tạo ở **mức module**, nên nó gắn vào **vòng lặp sự kiện đầu tiên
tranh chấp nó**; ai chạy `asyncio.run()` hai lần trong một tiến trình sẽ hỏng
synthesize vĩnh viễn từ lần thứ hai.

Phiên này **bị cấm sửa mã sản phẩm**, nên nó không thể được vá ở đây — đúng luật.
Nhưng B6 v1.7 không có chỗ nào để báo cáo nó. Nó phải chui vào `technical-docs.md`
mục "còn mở" mới không rơi mất.

**Đề xuất:** thêm trường B6: `khiếm khuyết mới phát hiện: <có/không>` — nếu có thì
liệt kê + nơi đã ghi + định đoạt (*vá ngay / ngoài phạm vi, đã ghi vào đâu*).
Đóng gói thường là lần đầu product bị soi nghiêm túc; phát hiện khiếm khuyết ở
bước này là **chuyện bình thường**, và quy trình nên có sẵn ô cho nó.

## 7. Nhỏ: `--only` khớp chuỗi con, khớp 0 case mà vẫn báo ĐẠT

**Mức: đã tự vá trong phiên, ghi lại làm ví dụ.**

Cờ lọc của `reverse-check.py` ban đầu khớp 0 case vẫn in `KET QUA: DAT`. Đúng
tinh thần luật "đếm đủ trước khi đếm xanh", nhưng luật đó v1.7 chỉ áp cho **bộ
eval**, không áp cho **công cụ kiểm ngược**.

**Đề xuất:** mở rộng luật (2) sang mọi công cụ trong `eval/`: *"không có gì để
chứng minh thì không được báo ĐẠT"*.

---

## Tóm tắt định đoạt đề xuất

| # | Nội dung | Mức |
|---|---|---|
| 1 | Họ test giả thứ bảy: khẳng định ngoài vòng đời bằng chứng | nên vá |
| 2 | Kiểm ngược gieo lỗi vào bản sao, không sửa cây sản phẩm | nên vá |
| 3 | Tách nhánh thứ ba: **lỗi gieo không quan sát được** | nên vá |
| 4 | B4 chỉ chạy sau khi mọi file được trỏ tới đã tồn tại | nên vá |
| 5 | DoD ba trạng thái, có ô "không chạy lại được + lý do" | nên vá |
| 6 | B6 thêm ô "khiếm khuyết mới phát hiện, chưa vá" | nên vá |
| 7 | Luật "đếm đủ" áp cho mọi công cụ trong `eval/`, không chỉ bộ eval | nhỏ |
