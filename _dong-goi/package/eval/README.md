---
product: googlecast-mcp
layer: output
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
eval_last: 2026-08-28
eval_offline: "57/57 ĐẠT"
eval_online: "3/3 ĐẠT"
eval_hardware: "64/64 ĐẠT (sau khi sửa 2 lỗi của chính bài kiểm)"
reverse_check: "60/60 lỗi gieo ĐẠT, phủ 57/57 mục offline, 3 đối chứng xanh"
registry: "[[packages/googlecast-mcp]]"
---

# Bài kiểm

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py            # offline, ~5s
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online   # + edge-tts thật, ~80s
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --list
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --only tts_   # lượt rút gọn

# PHÁT TIẾNG THẬT — phải xin phép người dùng trước
GOOGLECAST_MCP_TEST_SPEAKER="Kitchen speaker" \
  uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware

# Kiểm ngược chính bài kiểm
uv run python _dong-goi/package/eval/reverse-check.py                  # ~60s
uv run python _dong-goi/package/eval/reverse-check.py --only media_    # lượt rút gọn
uv run python _dong-goi/package/eval/reverse-check.py --list
```

## Tầng tác dụng phụ

| Tầng | Số mục | Chạm tới | Mặc định |
|---|---|---|---|
| offline | 57 | chỉ thư mục tạm | **bật** |
| `--online` | 3 | dịch vụ edge-tts thật | tắt |
| `--hardware` | 4 | **phát tiếng thật ra loa** | tắt, xin phép |

Bài kiểm không ai dám chạy thì bằng không có. Vì thế tầng mặc định là tầng
**không tác dụng phụ** và chạy trong **5 giây** — đủ rẻ để chạy sau mỗi lần
sửa. Hai tầng còn lại phải bật tường minh.

## Luật của bài kiểm

**1. Đếm đủ trước khi đếm xanh.** Báo cáo luôn in `đã chạy X/Y mục đăng ký`.
`X < Y` là KHÔNG ĐẠT toàn cục, kể cả khi mọi mục đã chạy đều xanh. Khớp 0 mục
(vd `--only` gõ sai) cũng KHÔNG ĐẠT. Áp cho **cả hai công cụ** trong thư mục
này. Lý do: đã từng có lượt chạy sập giữa chừng vì một `KeyError`, làm mọi mục
sau im lặng biến mất mà báo cáo vẫn xanh.

**2. Mỗi mục phải gọi vào mã sản phẩm** và phải nằm trong ít nhất một danh sách
kỳ-vọng-đỏ. Mục không lỗi gieo nào làm đỏ được là nghi phạm cấu trúc — nó
không kiểm gì cả. `reverse-check.py` báo `CHƯA PHỦ` và trả về KHÔNG ĐẠT nếu còn
mục như vậy trong lượt đầy đủ.

**3. Lỗi hạ tầng là ERROR, không nuốt thành PASS.** Mỗi mục bọc riêng.

**4. Không ghi vào cây sản phẩm.** Mọi thứ nằm trong thư mục tạm; lỗi gieo đi
vào **bản sao** của `src/`.

**5. Bằng chứng phải bền theo THỜI GIAN và PHẠM VI.** Khẳng định phải sống
trong vòng đời của fixture nó tham chiếu. `tts_leaves_no_zero_byte_file` đếm
file **khi thư mục tạm còn sống** — đóng trước rồi mới đếm là đếm vào chỗ
trống. Ở tầng `--hardware`, `hardware_says_on_real_speaker` KHÔNG đọc
`player_state` (clip 2s thường đã phát xong lúc `say()` trả về, đo được: `say()`
5.4s so với clip 2.26s) mà kiểm **dấu vết bền**: `content_id` khớp URL và
`duration > 0` — `duration > 0` chỉ có được nếu thiết bị đã THỰC SỰ tải file.

**6. Tráo bối cảnh phải TRỌN BỘ.** `server_context()` tráo cả `_manager` LẪN
`_media_server`. Tráo nửa vời nguy hơn không tráo: phần chưa tráo vẫn trỏ vào
thế giới cũ và lỗi hiện ra ở chỗ chẳng liên quan — đã từng làm `url_for()`
nhận file nằm ngoài thư mục nó phục vụ.

**7. Cấm thay-thế-đệ-quy.** KHÔNG được gán `tts.asyncio.sleep = fake`:
`tts.asyncio` **chính là** module asyncio toàn cục, nên bản thay thế sẽ gọi lại
chính nó — đệ quy vô hạn, và lỗi hiện ra ở những mục chẳng liên quan. Dùng
`ModuleProxy`, giữ tham chiếu module gốc và bọc proxy ở ngoài. Ưu tiên **cô
lập** hơn **canh gác**.

**8. Không dùng `importlib.reload`.** Không dùng `assert` trần (dùng `want()`,
để `python -O` không xoá mất khẳng định).

## Kiểm ngược — vì sao và bằng chứng

Một bài kiểm chưa từng đỏ thì chưa chứng minh được gì.

`reverse-check.py` gieo **60 lỗi** vào một **bản sao** `src/` trong thư mục
tạm (`PYTHONPATH` trỏ vào bản sao, `PYTHONDONTWRITEBYTECODE=1`), rồi kiểm xem
đúng những mục eval đã ghi TRƯỚC có đỏ không. Hoàn nguyên là hệ quả của **cấu
trúc** — thư mục tạm tự xoá — chứ không phải trí nhớ của người chạy.

**Kỳ vọng viết trước, không phải chép lại.** Mỗi ca mang sẵn danh sách
`expect_red` nằm ngay cạnh lỗi gieo.

**Đối chứng kỳ-vọng-xanh — 3 ca.** Chúng sửa mã ĐANG THỰC SỰ CHẠY mà không đổi
hành vi. Chú thích và khoảng trắng KHÔNG tính: vô hại tới mức không kiểm được gì.

| Đối chứng | Sửa gì | Chạy mục nào |
|---|---|---|
| `control_rename_local_variables` | đổi tên `ext, mime` → `extension, mimetype` trong vòng lặp của `_guess_content_type` | 4 mục |
| `control_split_expression` | tách `device.get("cast_type")` ra biến trung gian trong `is_speaker` | 4 mục |
| `control_extract_url_variable` | tách phần `quote(...)` ra biến `encoded` trong `url_for` | 3 mục |

Đỏ trên đối chứng là **ĐỎ BỪA** và cũng phải sửa.

**Thi hành chi phí.** Lượt đầy đủ chạy **60 lỗi gieo trong 56s**, vì mỗi ca chỉ
chạy đúng tập mục eval liên quan (`--only`) chứ không chạy cả 57 mục. Cách làm
"mỗi lỗi gieo × toàn bộ bài kiểm" từng đo được **68 × 10s = 12 phút**, tự phá
luật ở mục Tầng ở trên. Lượt rút gọn in rõ `(lượt RÚT GỌN: n/60 …)` — không
được hoá trang thành lượt đầy đủ.

**Báo X/Y hai chiều.** In cả `đã chạy 60/60 lỗi gieo` lẫn `đã phủ 57/57 mục
eval tầng offline`. Thiếu chiều nào cũng che được một loại thiếu sót khác nhau.

### Kết quả lượt đầy đủ — 2026-08-28

```
đã chạy 60/60 lỗi gieo đăng ký
đã phủ 57/57 mục eval tầng offline bằng ít nhất một kỳ-vọng-đỏ
  đạt 60 · không đạt 0 · tổng thời gian 56s
ĐẠT
```

Lượt đầy đủ có `--online`, cùng ngày:

```
đã chạy 60/60 mục đăng ký
  xanh 60 · đỏ 0 · lỗi hạ tầng 0
ĐẠT
```

*Số đo đáng ghi từ chính lượt này:* kịch bản "dồn 6 yêu cầu" đo được **63.7s**
ở lần chạy đầu và **5.4s** ở lần sau, cùng mã, cùng máy. Biên độ hơn mười lần
là của **dịch vụ bên ngoài**, không phải của sản phẩm — nên mục
`online_serializes_a_burst` cố ý chỉ khẳng định **6/6 đạt và không đọng file 0
byte**, không đặt ngưỡng thời gian. Đặt ngưỡng ở đây sẽ tạo ra một bài kiểm
chập chờn, và bài kiểm chập chờn thì người ta sẽ ngừng tin nó.

Xác nhận cuối, trên cây **nguyên vẹn** sau khi xoá bytecode
(`find src -name __pycache__ -exec rm -rf {} +`) — không phải nhìn `git status`:

```
đã chạy 57/57 mục đăng ký
  xanh 57 · đỏ 0 · lỗi hạ tầng 0
ĐẠT
```

`git status -- src scripts docs pyproject.toml README.md` không có dòng nào:
cây sản phẩm không bị chạm.

### Ba lỗi thật do chính lượt kiểm ngược này lộ ra

**(a) Kỳ vọng sai — `online_renders_real_vietnamese_audio` đỏ.** Nhận
`b'\xff\xf3d'` mà kỳ vọng lại so **3 byte** với các mẫu **2 byte**
(`b"\xff\xfb"`). Định đoạt: **nhánh 2 — kỳ vọng sai**. Sửa theo nguồn, không
nới cho xanh: frame sync của MPEG là **11 bit 1 đầu tiên** (ISO/IEC 11172-3
§2.4.1.2), tức byte đầu `0xFF` và ba bit cao của byte sau đều là 1. Kiểm giờ so
đúng điều đó, vẫn từ chối dữ liệu không phải mp3.

**(b) Test giả — `media_never_starts_thread` treo 180s.** Định đoạt: **nhánh 1
— bài kiểm sai**. Nguyên nhân không nằm ở khẳng định mà ở dọn dẹp:
`ThreadingHTTPServer.shutdown()` chờ vòng `serve_forever` thoát, mà lỗi gieo
làm vòng đó không bao giờ khởi động → treo vĩnh viễn. Sửa bài kiểm để bắt được
thật: `stop_quietly()` tắt server trong luồng nền có hạn 5s, và bộ kiểm ngược
coi **treo quá hạn là ĐỎ** (xanh phải là xanh trong thời gian hữu hạn). Ca này
giờ đỏ trong 15s.

**(c) Lỗi gieo không áp được — `media_lan_ip_raises_offline`.** Đoạn mã gốc
viết trong lỗi gieo sai thụt lề nên khớp 0 lần. Bộ kiểm ngược **báo ERROR chứ
không im lặng bỏ qua** — một lỗi gieo không áp được mà bị bỏ qua sẽ trông y hệt
một lỗi gieo đã đạt. Sửa đúng thụt lề.

### Chưa phủ — nói thẳng

### Hai lỗi bài kiểm mà lượt chạy `--hardware` phiên này lộ ra

Chạy thật lần đầu: **63 xanh / 1 đỏ**.

1. `hardware_says_on_real_speaker` — chọn ĐÚNG bằng chứng bền (`content_id` +
   `duration`) nhưng đọc **không có mốc chờ**. `content_id` xuất hiện ngay khi
   thiết bị nhận lệnh; `duration` chỉ có sau khi nó TẢI và đọc xong file. Đọc
   cả hai tại cùng một khoảnh khắc là đo `duration` quá sớm → `duration=None`.
   Đây là luật "mốc chờ + bằng chứng bền" bị thực hiện **hụt nửa sau**: chọn
   đúng thứ để đo, sai thời điểm đo. Đã thêm mốc chờ 20s.

2. `hardware_all_never_doubles_a_speaker` — dùng `len(hosts) == len(set(hosts))`,
   đúng dạng **so kích thước** mà v1.9 liệt kê là test giả. Nó vẫn xanh khi
   `chosen` co lại còn một phần tử hoặc rỗng — tức là xanh đúng vào lúc lựa
   chọn hỏng nặng nhất, ở chính mục canh cái lỗi chồng luồng. Đã đổi sang **so
   tập kỳ vọng tường minh** (bằng đúng tập loa không-phải-nhóm) kèm điều kiện
   `len(chosen) >= 2` để phép kiểm có nghĩa.

Đáng ghi: cả hai đều là luật bộ quy trình **đã có tên**, và bài kiểm vẫn phạm.
Biết luật không thay thế được việc chạy thật.

Kiểm ngược chỉ phủ **tầng offline**. Ba mục `--online` và bốn mục `--hardware`
**CHƯA có lỗi gieo nào**: gieo lỗi cho chúng cần một tiến trình gọi ra ngoài
mạng hoặc ra phần cứng thật cho từng ca, chi phí vượt xa giá trị. Cơ chế che
khả dĩ: một mục hardware hỏng có thể vẫn xanh nếu thiết bị tình cờ đang phát
sẵn nội dung khác trùng URL — nên chúng kiểm `content_id` khớp **đúng URL vừa
cast**, không kiểm "có đang phát gì đó không".

## Lịch sử — tầng hardware đã dạy được gì

Năm phiên đóng gói đầu, lần nào tầng `--hardware` cũng lộ ra một lỗi của **chính
bài kiểm**, không phải của sản phẩm:

1. rò mock `tts.synthesize` sang tầng `--online`;
2. rò mock `list_speakers`/`discover` sang tầng `--hardware`;
3. sập giữa chừng vì `KeyError`, mọi mục sau im lặng;
4. đọc `player_state` ngay lúc `play_media` trả về — đòi một trạng thái đã hết hạn;
5. tráo `_manager` mà quên `_media_server` → `url_for()` nhận file ngoài thư mục
   nó phục vụ.

Phiên thứ sáu **đạt ngay lần đầu, 78/78**. Các luật ở mục "Luật của bài kiểm"
phía trên chính là kết tinh của đúng năm lần vấp đó — đó là lý do chúng được
viết ra thành luật thay vì để trong đầu.

## Số đo lịch sử

| Lượt | Kết quả |
|---|---|
| Eval offline, 7 phiên | 35 → 43 → 67 → 138 → 49 → 77 → **57** (số mục đổi vì cách chia mục đổi; exit 0) |
| Eval `--online`, 4 lượt | 157 → 49 → 82 → **3/3** |
| Eval `--hardware`, 6 lượt | 37 → 48 → 67 → 157 → 49 → **78/78 đạt ngay lần đầu** |
| Kiểm ngược, lượt này | **60/60, 56s** |
