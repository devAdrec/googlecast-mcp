# Bài kiểm googlecast-mcp — và cách nó tự chứng minh

Hai file:

| File | Việc |
|---|---|
| `eval-googlecast-mcp.py` | bài kiểm. 77 mục offline, 5 mục `--online`, 1 mục `--hardware` |
| `reverse-check.py` | **kiểm chính bài kiểm**: gieo 67 khiếm khuyết đã biết vào một BẢN SAO của mã, đòi bài kiểm phải đỏ đúng chỗ |

```bash
uv run python eval-googlecast-mcp.py            # offline: không mạng, không thiết bị
uv run python eval-googlecast-mcp.py --online   # + edge-tts thật
uv run python eval-googlecast-mcp.py --json     # cho máy đọc
uv run python reverse-check.py                  # ~12 phút
```

---

## Ba tầng tác dụng phụ

| Tầng | Cờ | Chạm tới | Xin phép? |
|---|---|---|---|
| offline | (mặc định) | không gì cả — mạng, thiết bị, dịch vụ TTS đều bị thay thế | không |
| online | `--online` | edge-tts thật (cần internet). **Không phát ra loa nào** | không |
| hardware | `--hardware` | **loa thật, phát ra tiếng trong nhà** | **có, mỗi lần** |

Tầng `--hardware` cần `GOOGLECAST_MCP_TEST_SPEAKER=<tên loa>`.

**Kết quả phiên này: 78/78 mục đăng ký, ĐẠT ngay lần chạy đầu.** Đáng ghi lại,
vì đây là lần đầu tiên trong sáu phiên đóng gói mà tầng hardware không lộ lỗi
nào của chính bài kiểm. Năm lần trước lần lượt vấp: rò mock TTS, rò mock
`list_speakers`/`discover`, sập giữa chừng vì `KeyError`, đọc trạng thái ngay
lúc `play_media` trả về, và tráo `_manager` mà quên `_media_server`. Các luật
tích luỹ từ đúng những lần vấp đó — bằng-chứng-bền theo thời gian *và* phạm vi,
tráo-bối-cảnh-trọn-bộ, đếm-đủ-trước-khi-đếm-xanh — là thứ đã chặn chúng lần này.

Chia theo **tác dụng phụ**, không theo tốc độ. Tầng mặc định phải chạy được ở
bất cứ đâu, bất cứ lúc nào, không làm phiền ai — vì **bài kiểm không ai dám
chạy thì bằng như không có**.

## Bốn luật, thi hành trong mã

### 1. Đếm đủ trước khi đếm xanh

Mỗi mục được bọc riêng: `AssertionError` → FAIL, mọi lỗi khác → **ERROR**
(không nuốt thành PASS). Báo cáo in `đã chạy X/Y mục đăng ký`, và **X<Y là
hỏng toàn cục** kể cả khi mọi mục đã chạy đều xanh.

Luật này áp cho **mọi công cụ trong thư mục này**, kể cả `reverse-check.py`:
nó in `đã chạy X/Y trường hợp đăng ký`, và khớp 0 trường hợp **không** được
báo ĐẠT.

### 2. Mọi mục phải gọi vào mã sản phẩm

Và phải nằm trong ≥1 danh sách kỳ-vọng-đỏ. `reverse-check.py` tự kiểm điều
này và nêu tên mục không được phủ: *mục mà không lỗi gieo nào làm đỏ được rất
có thể không hề chạm vào sản phẩm.*

Hiện tại: **77/77 mục offline** đều nằm trong ít nhất một danh sách kỳ-vọng-đỏ.

### 3. So TẬP kỳ vọng, không so KÍCH THƯỚC

`server.tools.exact_set` so tập tên tool tường minh. Kiểm "có 13 tool" thì vẫn
xanh khi một tool bị đổi tên — đó là **test giả**.

### 4. Bằng chứng bền theo thời gian VÀ phạm vi

Khẳng định phải sống trong **vòng đời của thứ nó tham chiếu**. Đếm file sau
khi thư mục tạm đã dọn là đếm vào chỗ trống → **đỏ bừa**, không phải lỗi sản
phẩm. Với tầng hardware: không đòi `player_state == PLAYING` (đo được `say()`
mất 5.4s trong khi clip chỉ 2.26s — trạng thái đã hết hạn), mà đòi dấu vết
bền: `content_id` khớp URL vừa cast **và** `duration > 0`, trong một vòng chờ
có timeout. Media server phải còn sống cho tới khi loa tải xong.

## Kiểm ngược hoạt động thế nào

Với **mỗi** lỗi gieo:

1. Sao `src/` sang một thư mục tạm riêng (bỏ `__pycache__`).
2. Sửa **bản sao**, đặt `GOOGLECAST_MCP_SRC` và `PYTHONPATH` trỏ vào đó,
   `PYTHONDONTWRITEBYTECODE=1`.
3. Chạy eval, so tập mục đỏ với `expect_red` **đã ghi trước**.

Cây sản phẩm thật **không bao giờ bị ghi vào**. Hoàn nguyên là hệ quả của
**cấu trúc**, không phải của việc nhớ dọn dẹp.

Xác nhận cuối **không phải** nhìn `git status`, mà là **chạy lại eval trên cây
nguyên vẹn và thấy xanh** (sau khi xoá bytecode).

**Đối chứng vô hại** (`expect_red` rỗng) kỳ vọng vẫn XANH: nếu một thay đổi
không đổi hành vi mà bài kiểm vẫn đỏ thì bài kiểm **đỏ bừa** — cũng là hỏng.

## Khi một mục "lẽ ra đỏ mà lại xanh": BA nhánh, chọn một

| Nhánh | Nghĩa | Xử lý |
|---|---|---|
| **Test giả** | bài kiểm không bắt được gì thật | sửa bài kiểm cho bắt thật |
| **Kỳ vọng sai** | có cắn, nhưng đòi sai điều | sửa `expect_red` **theo requirement, có trích nguồn**. Cấm nới cho xanh |
| **Lỗi gieo không quan sát được** | bị một cơ chế khác che | **đổi lỗi gieo**, hoặc ghi CHƯA PHỦ kèm tên cơ chế che |

Thiếu nhánh thứ ba là ép người ta làm bài kiểm *tệ đi* cho vừa luật.

### Sáu lần định đoạt thật, đã ghi

Lượt kiểm ngược đầu tiên nêu **6 vấn đề**. Không cái nào được xử lý bằng cách
hạ tiêu chuẩn:

| # | Trường hợp | Nhánh | Xử lý |
|---|---|---|---|
| 1 | `media/khong-tu-khoi-dong` không làm đỏ `media.url_for.shape` | **TEST GIẢ** | Bài kiểm so URL với `server.port` của chính nó. Server chưa chạy thì cả hai cùng bằng 0, phép so vẫn xanh. **Siết** bài kiểm: thêm `server.port != 0` |
| 2 | `store/nhan-ca-thiet-bi-hinh-anh` không làm đỏ `server.say.all_excludes_speaker_groups` | kỳ vọng sai | `all` lọc nhóm bằng `s["cast_type"] != "group"` trong `server.py`, **không đi qua** `is_speaker()`. Bỏ khỏi `expect_red`, ghi lý do tại chỗ |
| 3 | `store/danh-roi-truong-du-lieu` không làm đỏ 3 mục | kỳ vọng sai | 3 mục đó đọc từ **cache sống** của `CastManager` (`list_cached()` gộp `live` đè lên `store.load()`), không qua vòng lưu-rồi-đọc |
| 4 | `tts/render-rong-van-tinh-la-thanh-cong` không làm đỏ `...no_zero_byte_file_left_after_failure` | kỳ vọng sai | mục đó chạy kịch bản `save()` **ném lỗi**, dừng ở nhánh `except`, không chạm dòng bị gieo |
| 5 | `cast/khop-bua-moi-ten` không làm đỏ `cast.resolve.saved_address_tried_before_rescan` | kỳ vọng sai | mục đó **dọn sạch cache sống** trước khi gọi, nên thân vòng lặp bị gieo lỗi không hề chạy |
| 6 | Đối chứng `doi-chung/doi-ten-bien-cuc-bo` không gieo được | (lỗi gieo lạc hậu) | thụt lề trong bảng lỗi gieo không khớp mã thật. Kịch bản **bắt được và báo lỗi** thay vì âm thầm bỏ qua — đúng như thiết kế |

Trường hợp #1 là trường hợp đáng giá nhất: đó là một bài kiểm **giả** đã sống
sót qua nhiều lượt xanh, và chỉ lộ ra khi bị đòi phải đỏ.

Còn **một lần định đoạt theo nhánh thứ ba** nằm sẵn trong bảng lỗi gieo: lỗi
"file 0 byte bị coi là cache hợp lệ" nếu chỉ gieo vào lần kiểm thứ nhất thì bị
**lần double-check bên trong khoá che mất** → đã **đổi lỗi gieo** thành gieo
vào cả hai chỗ. Xem chú thích tại `tts/file-0-byte-bi-coi-la-cache-hop-le`.

## Các dạng test giả phải canh

- **So kích thước thay vì so tập kỳ vọng tường minh.**
- **Sập giữa chừng mà vẫn báo đạt** → luật đếm đủ ở trên.
- **Kiểm mà không chạm vào sản phẩm** → luật phủ ngược ở trên.
- **So một giá trị với chính nó** → trường hợp #1.
- **Gán đè lên chính hàm mà bản thay thế sẽ gọi lại.** Rút ngắn thời gian chờ
  bằng `module.sleep = lambda: sleep(...)` là vòng lặp vô hạn: `module.asyncio`
  và `asyncio` của bài kiểm là **cùng một đối tượng**. Bọc bằng proxy
  (`_FastSleepAsyncio`), đừng gán đè.
- **So mấy byte đầu với một danh sách tiền tố có độ dài khác nhau.** `data[:3]`
  không bao giờ bằng một tiền tố 2 byte — bài kiểm đỏ trong khi sản phẩm không
  sao. Dùng `is_mp3()` kiểm từ đồng bộ MPEG cho đúng.

## Vệ sinh bối cảnh

`swapped_server()` tráo **trọn bộ**: `_manager`, `_media_server`, **và** biến
môi trường thư mục cache. Tráo nửa vời nguy hơn không tráo — thay `_manager`
mà quên `_media_server` thì `url_for()` nhận file nằm ngoài thư mục nó phục vụ
và ném `ValueError` ở một chỗ chẳng liên quan gì tới điều đang kiểm.

Lỗi gieo `tts/bo-qua-bien-moi-truong-cache` cố tình tái hiện đúng cái bẫy đó.

Mọi thứ thay thế đều khôi phục trong `finally`. Không dùng `importlib.reload`.
Ưu tiên cô lập hơn canh gác.
