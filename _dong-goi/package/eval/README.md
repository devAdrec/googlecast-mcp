# Bộ kiểm googlecast-mcp

Hai file:

| File | Việc |
|---|---|
| `eval-googlecast-mcp.py` | chạy các mục kiểm trên product |
| `reverse-check.py` | chứng minh bộ kiểm **có thể đỏ** — và **không đỏ bừa** |

Cái thứ hai quan trọng ngang cái thứ nhất. **Bộ kiểm chưa từng đỏ là bộ kiểm chưa
chứng minh được gì.**

## Chạy

```bash
# từ thư mục gốc repo
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py             # 47 mục, không tác dụng phụ
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online    # + 3 mục, cần internet
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware  # + 2 mục, PHÁT TIẾNG THẬT
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --list      # xem danh sách mục

uv run python _dong-goi/package/eval/reverse-check.py                   # 49 case, ~6 phút
uv run python _dong-goi/package/eval/reverse-check.py --only tts        # lọc theo id
```

> **`--hardware` phát tiếng ra loa thật trong nhà.** Xin phép người dùng trước
> mỗi lần chạy. Đừng đưa nó vào CI, đừng chạy lúc nửa đêm.

## Ba tầng, mặc định là tầng vô hại

| Tầng | Số mục | Chạm vào |
|---|---|---|
| `offline` | 47 | chỉ thư mục tạm |
| `--online` | 3 | dịch vụ edge-tts trên internet |
| `--hardware` | 2 | thiết bị Cast thật, âm thanh thật |

Bài kiểm mà không ai dám chạy thì bằng như không có. Nên tầng mặc định phải chạy
được ở bất cứ đâu, kể cả CI không mạng.

## Kết quả lần chạy này (2026-08-26)

```
offline    : da chay 47/47 muc dang ky -- dat 47, hong 0, loi 0   -> XANH
--online   : da chay 50/50 muc dang ky -- dat 50, hong 0, loi 0   -> XANH
             (fan-out 6 thông báo hoàn tất trong 4.9s)
--hardware : ĐÃ CHẠY sau khi xin phép -- **49/49 mục đăng ký, XANH**

Lần chạy đầu LỖI (không phải hỏng): `url_for()` ném `ValueError` vì mục kiểm
tráo `server._manager` nhưng **không tráo `server._media_server`**. Mỗi mục
chạy trên thư mục cache riêng, trong khi media server mức module vẫn trỏ vào
thư mục có từ lúc import — nên nó nhận một file nằm ngoài thư mục nó phục vụ.

Sửa: tầng hardware **dựng MediaServer riêng** trỏ đúng cache đang dùng, và giữ
nó sống tới hết mục kiểm (loa còn phải tải file từ đó — dừng sớm là cắt giữa
chừng).

Bài học, nối tiếp luật "vệ sinh mock" của v1.7: **cô lập phải trọn bộ.** Tráo
một nửa bối cảnh còn nguy hiểm hơn không tráo, vì phần chưa tráo vẫn trỏ vào
thế giới cũ và lỗi hiện ra ở chỗ chẳng liên quan gì.

reverse-check: case dat 49/49 (45 lỗi gieo + 4 đối chứng)
               do phu nguoc (lop offline): 47/47 muc
               cay nguyen ven XANH (47/47)      -> DAT
```

## Kiểm ngược làm gì, và làm thế nào

Với **mỗi** case, `reverse-check.py`:

1. sao chép `src/`, `scripts/`, `pyproject.toml` sang một thư mục tạm **mới**;
2. gieo đúng một thay đổi vào bản sao đó — nếu chuỗi cần tìm không xuất hiện đúng
   số lần đã khai báo thì **báo lỗi**, vì case đã cũ so với product;
3. chạy lại lớp offline với `PYTHONPATH` trỏ vào bản sao và
   `PYTHONDONTWRITEBYTECODE=1`;
4. đối chiếu tập mục đỏ thật với **danh sách kỳ vọng viết trước**.

**Cây sản phẩm không bao giờ bị ghi vào.** Hoàn nguyên không phải là chuyện nhớ
hay quên — nó là hệ quả của cấu trúc. Và bước cuối cùng vẫn **chạy lại bộ kiểm
trên cây nguyên vẹn và đòi XANH**: đó, chứ không phải `git status`, mới là bằng
chứng không rò rỉ gì. (Lỗi gieo dài đúng bằng bản gốc có thể để lại `.pyc` cũ —
git sạch mà eval vẫn đỏ.)

### Hai chiều, vì một chiều là không đủ

- **45 lỗi gieo** — mỗi cái mang danh sách mục *phải* đỏ, viết **trước** khi chạy.
  Mục nằm trong danh sách mà vẫn xanh = **TEST GIẢ**: nó chưa từng chạm vào hành
  vi mà nó tự nhận là canh gác.
- **4 đối chứng vô hại** — thêm một dòng chú thích, đổi lời một docstring, thêm
  dòng trống, thêm một dấu cách trong script. Cả bốn **phải để bộ kiểm XANH**.
  Đối chứng làm đỏ nghĩa là bộ kiểm bắn vào tiếng ồn — hỏng ngang việc không bao
  giờ bắn.

### Kiểm ngược đã bắt được gì trong chính phiên này

Không phải lý thuyết. Lần chạy đầu tiên trả về `CHUA DAT` với 4 vấn đề thật:

| Vấn đề | Sự thật | Xử lý |
|---|---|---|
| `media.stop_is_idempotent` xanh dù bỏ `server_close()` | `HTTPServer` đặt `SO_REUSEADDR`, và bỏ tham chiếu thì refcount tự đóng socket — lỗi gieo **không quan sát được** | đổi lỗi gieo sang bỏ nhánh `if self._httpd is None: return` — đúng cái mục này thật sự canh |
| `tts.cache_hit_skips_service` xanh dù tắt lần kiểm cache đầu | lần kiểm **thứ hai** sau khoá vẫn bắt được → tắt riêng lần đầu chỉ là hồi quy hiệu năng | lỗi gieo giờ tắt **cả hai** lần kiểm; giới hạn ghi vào mục "chưa phủ" bên dưới |
| `server.no_speakers_found` xanh dù `say` mặc định phát tất cả | **KỲ VỌNG SAI**, không phải test giả: nhánh mạng-rỗng trả `no_speakers_found` ở `server.py:84-89`, **trước** đoạn bị gieo lỗi | sửa **kỳ vọng** theo nguồn, ghi rõ dòng mã; không nới bài kiểm cho xanh |
| `tts.keeps-zero-byte-file` báo case cũ | `path.unlink(missing_ok=True)` có **2** chỗ, khai báo 3 | sửa số; và bỏ `tts.retries_then_succeeds` khỏi kỳ vọng vì lần thử thứ ba ghi đè file rỗng nên mục đó **không thể** thấy |

Ba trong bốn là bộ kiểm tự tố cáo mình. Đó chính là công dụng.

### Một lần đỏ bừa nữa, ở lớp `--online`

Mục `online.fanout_all_survive` báo **0/6 render thành công** — trong khi chạy tay
đúng đoạn đó thì 6/6, mất 15.6 giây. Nguyên nhân nằm ở **bài kiểm**, không ở
product: các phép khẳng định bị đặt **sau** khi khối `with tmpdir()` kết thúc, nên
thư mục đã bị xoá trước lúc đếm file. Chuyển vào trong khối là xanh.

Bài học: bằng chứng là **file trên đĩa**, nên phép khẳng định phải sống trong
cùng vòng đời với cái đĩa đó.

## Chưa phủ — nói thẳng, không giấu

| Chỗ | Vì sao |
|---|---|
| Lớp `--online` (3 mục) | cần dịch vụ thật; kiểm ngược chỉ chạy lớp offline |
| Lớp `--hardware` (2 mục) | cần loa thật và sự cho phép của người dùng |
| Tắt **riêng** lần kiểm cache thứ nhất (`tts.py:71`) | lần kiểm thứ hai sau khoá vẫn trả đúng → là hồi quy **hiệu năng**, bộ kiểm không thấy |
| Bỏ `server_close()` trong `MediaServer.stop()` | `SO_REUSEADDR` + refcount che mất |
| `service.sh install` chạy thật | cần `sudo` và sẽ cắt dịch vụ của hai máy khác |
| Sống sót qua reboot máy | đã `enable`, chưa reboot lần nào |

Ba dòng cuối là **CHƯA THỬ**, không phải "đã thử và ổn".

## Bằng chứng bền cho việc bất đồng bộ

Lớp `--hardware` là chỗ dễ đỏ oan nhất. Trong các phiên trước nó đỏ oan **hai lần**:

1. Hỏi trạng thái qua **một `CastManager` khác** cái đã cast. Trạng thái media là
   **theo từng kết nối** — kết nối không phát sẽ báo `UNKNOWN` mãi mãi.
2. Kể cả hỏi đúng manager vẫn đỏ: phần tử hỏng kéo `say()` dài **5.4 giây** trong
   khi clip chỉ **2.26 giây**. Lúc `say()` trả về thì loa **đã phát xong** —
   `IDLE`, `duration=2.256`. Bắt `PLAYING` là bắt một trạng thái đã bay mất.

Cách đúng, đang dùng: hỏi qua **đúng manager đã cast**, và chờ tới khi
`content_id` khớp URL vừa cast **và** `duration > 0`. Đó là dấu vết **còn lại sau
khi phát xong**, chứ không phải trạng thái thoáng qua. Quy tắc chung: chỉ dùng
trạng thái thoáng qua khi **tuổi thọ bằng chứng > trễ quan sát tối đa** — ở đây
thì ngược lại, nên phải đổi bằng chứng.

## Vệ sinh mock

Mọi phép thay thế đi qua `swap()` / `swap_item()` và luôn khôi phục. Ngoài ra có
**residue guard**: sau **mỗi** mục, bộ chạy so lại danh tính của một danh sách
đối tượng canh gác; mục nào làm rò thì **chính nó** bị tính `ERROR` — không phải
một mục vô tội ba lớp sau.

Có lý do cụ thể cho việc này. Hai lần rò thật đã gặp:

- tầng offline thay `tts.synthesize` ngay trên module → tầng `--online` đo nhầm
  hàm giả và báo "mp3 0 byte";
- một phép thử "mạng rỗng" thay `list_speakers`/`discover` lên `server._manager`
  rồi không khôi phục → tầng `--hardware` FAIL với `no speaker answered mDNS`
  trong khi loa vẫn sống nhăn.

Nguyên tắc rút ra: **ưu tiên cô lập hơn canh gác**. Bộ kiểm hiện tại thay ở tầng
thấp nhất có thể (`edge_tts.Communicate` thay vì `tts.synthesize`) để mã sản phẩm
vẫn chạy thật hết mức.

## Một chi tiết về vòng lặp sự kiện

Bộ chạy dùng **một** vòng lặp asyncio cho cả lượt, đúng như server thật. Không
phải chuyện thẩm mỹ: `tts._synthesis_lock` là `asyncio.Lock` mức module, nó **gắn
vào vòng lặp đầu tiên tranh chấp nó**. Dùng `asyncio.run()` cho từng mục thì từ
mục thứ hai trở đi sẽ nhận `RuntimeError: ... bound to a different event loop`.

Đây là **điểm yếu thật của product**, phát hiện nhờ viết bộ kiểm. Nó đã được ghi
vào bảng khiếm khuyết CÒN MỞ trong `../technical-docs.md`. Bộ kiểm né nó bằng cách
mô phỏng đúng điều kiện production — **không** vá lén mã sản phẩm.
