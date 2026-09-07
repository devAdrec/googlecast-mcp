---
product: googlecast-mcp
layer: output
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
eval_last: 2026-09-07
eval_offline: "57/57 ĐẠT"
eval_online: "60/60 ĐẠT (57 offline + 3 online)"
eval_hardware: "64/64 ĐẠT ở lượt 2026-08-28 (sau khi sửa 2 lỗi của chính bài kiểm) — KHÔNG chạy lại 2026-09-07 vì phát tiếng thật cần xin phép"
reverse_check: "60/60 lỗi gieo ĐẠT, phủ 57/57 mục offline, 3 đối chứng xanh, 57s"
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

**8. Xanh phải là xanh trong THỜI GIAN HỮU HẠN.** Mọi bước dọn dẹp chạm tài
nguyên của sản phẩm (server HTTP, kết nối Cast, tiến trình con) phải có **hạn
giờ**, và **quá hạn tính là ĐỎ, không phải ERROR**. Lý do rất cụ thể: khi bài
kiểm treo thì `X/Y` **không đếm được nữa** — không có dòng nào in ra để mà so.
Treo vì thế ẩn hơn cả sập giữa chừng, và sập giữa chừng đã là thứ luật 1 phải
đặt ra để bắt. `stop_quietly()` tắt server trong luồng nền có hạn 5s; bộ kiểm
ngược coi eval quá hạn là ĐỎ. Kịch bản DoD HTTP cũng theo luật này: chờ tắt tối
đa 10s rồi báo `quá hạn dọn dẹp -> ĐỎ`.

**9. `run_items` rỗng là lỗi CẤU HÌNH, không phải kết quả.** Mỗi ca kiểm ngược
— nhất là **đối chứng**, vốn không có `expect_red` để suy ra — phải khai tường
minh danh sách mục eval sẽ chạy. Ca không khai gì sẽ chạy eval với bộ lọc rỗng
và "đạt" mà chẳng kiểm gì. Chặn bằng ERROR ngay trước khi gieo.

**10. Không dùng `importlib.reload`.** Không dùng `assert` trần (dùng `want()`,
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

### Kết quả lượt đầy đủ — 2026-09-07 (mốc đóng gói)

Lượt **ĐẦY ĐỦ**, không `--only`, trên cây nguyên vẹn sau khi xoá bytecode:

```
uv run python _dong-goi/package/eval/reverse-check.py
đã chạy 60/60 lỗi gieo đăng ký
đã phủ 57/57 mục eval tầng offline bằng ít nhất một kỳ-vọng-đỏ
  đạt 60 · không đạt 0 · tổng thời gian 57s
ĐẠT
```

```
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py
đã chạy 57/57 mục đăng ký · xanh 57 · đỏ 0 · lỗi hạ tầng 0 · ĐẠT

uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online
đã chạy 60/60 mục đăng ký · xanh 60 · đỏ 0 · lỗi hạ tầng 0 · ĐẠT
  [online] 6 yêu cầu dồn: 6/6 đạt trong 5.1s
```

`--hardware` **KHÔNG chạy lượt này** (phát tiếng thật ra loa nhà người dùng,
phải xin phép trước). Bằng chứng gần nhất: 64/64 ngày 2026-08-28.

#### Hai chốt chặn được kiểm bằng cách LÀM CHÚNG NỔ

Luật chỉ đáng tin khi đã thấy nó chặn thật. Nạp `reverse-check.py` như module,
thay `SEEDS` bằng hai ca hỏng cố ý rồi chạy:

```
[ERROR] probe_empty_run_items
    RuntimeError: run_items rỗng — ca này không khai mục eval nào sẽ chạy
[ERROR] probe_seed_matches_zero_times
    RuntimeError: lỗi gieo không áp được: đoạn mã gốc xuất hiện 0 lần trong
    googlecast_mcp/speaker_store.py (mã sản phẩm đã đổi — phải cập nhật lỗi
    gieo, không được bỏ qua)
KHÔNG ĐẠT   (exit 1)
```

Cả hai đều **chặn lượt**, không im lặng bỏ qua. Đây chính là hai chỗ mà một bộ
kiểm ngược "trông có vẻ chạy" hay hỏng: lỗi gieo khớp 0 lần (mã sản phẩm đã
đổi) trông y hệt lỗi gieo đã đạt, và đối chứng không khai mục nào thì xanh vì
chẳng chạy gì.

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

### Hai lỗi bài kiểm mà lượt chạy `--hardware` 2026-08-28 lộ ra

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

### CHƯA PHỦ — nói thẳng, và đã rà soát thiết kế

Kiểm ngược chỉ phủ **tầng offline**. Bảy mục sau **CHƯA có lỗi gieo nào**:

| Mục | Tầng |
|---|---|
| `online_renders_real_vietnamese_audio` · `online_serializes_a_burst` · `online_two_event_loops` | `--online` |
| `hardware_discovers_real_speakers` · `hardware_says_on_real_speaker` · `hardware_all_never_doubles_a_speaker` · `hardware_volume_round_trip` | `--hardware` |

Vì sao chưa phủ: gieo lỗi cho chúng cần dựng một tiến trình gọi ra ngoài mạng
hoặc ra **phần cứng thật** cho **từng ca**. Với hardware thì mỗi ca là một lần
phát tiếng trong nhà người dùng — phép đo **không hoàn tác được**, nên không
được dùng để dò.

Vùng ngoài phủ thì không có bộ máy nào bắt lỗi thay, nên đổi lại phải **rà soát
thiết kế bằng tay**, đối chiếu từng dạng test giả đã liệt kê:

| Dạng test giả | Bảy mục này có mắc không |
|---|---|
| **so kích thước** thay vì so tập kỳ vọng | **ĐÃ TỪNG MẮC** ở `hardware_all_never_doubles_a_speaker` (`len==len(set)`) — đã đổi sang so tập tường minh + `len(chosen) >= 2`. Sáu mục còn lại rà lại: không mục nào khẳng định bằng độ dài |
| **sập giữa chừng** | không: mỗi mục bọc riêng, báo cáo in `đã chạy X/Y`, `X<Y` là KHÔNG ĐẠT toàn cục — luật này áp cho cả tầng hardware |
| **treo ở dọn dẹp** | rủi ro thật: dọn dẹp hardware đóng kết nối Cast tới thiết bị có thể đang treo. Đã có hạn giờ; quá hạn = ĐỎ |
| **không chạm mã sản phẩm** | không: cả bảy đều gọi `say()` / `synthesize()` thật, không mock |
| **bằng chứng thoáng qua** | **ĐÃ TỪNG MẮC** hai lần (đọc `player_state` quá muộn; đọc `duration` quá sớm) — nay là `content_id` + `duration` kèm **mốc chờ 20s** |
| **tráo bối cảnh nửa vời** | không áp dụng: tầng hardware cố ý KHÔNG tráo gì cả, chạy thẳng vào thế giới thật |

Cơ chế che còn lại, ghi rõ: một mục hardware hỏng vẫn có thể xanh nếu thiết bị
tình cờ đang phát sẵn nội dung khác **trùng URL**. Vì thế chúng kiểm
`content_id` khớp **đúng URL vừa cast**, không kiểm "có đang phát gì đó không".

Và điều thẳng thắn nhất: bảng rà soát trên đã bỏ sót đúng hai lỗi mà lượt chạy
thật lộ ra. **Rà soát thiết kế là thứ thay thế TỆ HƠN cho việc chạy thật** — nó
được dùng ở đây vì chi phí, không phải vì nó đủ.

### Thang phép đo không hoàn tác được

`--hardware` phát tiếng trong nhà người dùng: đo xong không thu lại được. Hai
luật của bộ quy trình đụng nhau ở đây — "không hoàn tác thì không làm" và "đo
lại bằng cùng kịch bản". Cách gỡ, theo thứ tự:

1. **Bản giả cùng đặc tính gây lỗi** (mặc định). Tầng offline dựng thiết bị Cast
   giả mang đúng đặc tính đã gây lỗi thật: nhóm loa và thành viên **trùng
   `host`** (`select_all_excludes_groups`), phần tử hỏng lẫn phần tử tốt
   (`say_isolates_one_broken_speaker`). Đủ để phân định giả thuyết.
2. **Thiết bị thật CHỈ để xác nhận cuối**, xin phép trước, không dùng để dò.
3. **Giảm N thì phải GHI N.** Tầng hardware là **4 mục**, nhưng chỉ **1 mục
   thực sự phát tiếng** (`hardware_says_on_real_speaker`, đúng **1 lần**, câu
   "Đây là bài kiểm tra tự động", khoảng **2 giây**). Ba mục kia cố ý chọn
   đường ít can thiệp nhất còn phân biệt được điều cần phân biệt:
   `hardware_discovers_real_speakers` chỉ dò; `hardware_all_never_doubles_a_speaker`
   kiểm **tập được chọn** chứ không cast tới nó — vì dấu vết phân biệt lỗi
   chồng luồng nằm ở **siêu dữ liệu (trùng `host`)**, không nằm ở âm thanh, nên
   phát thật ở đây không thêm sức phân định nào; `hardware_volume_round_trip`
   đổi âm lượng rồi **trả về giá trị cũ trong `finally`**.
   Đó là N đã giảm. Ghi ra đây vì giảm âm thầm rồi vẫn nói "đã kiểm tầng phần
   cứng" là dựng số.

## Lịch sử — tầng hardware đã dạy được gì

Trong **7 lượt** chạy `--hardware`, **6 lượt** lộ ra một lỗi của **chính bài
kiểm**, không phải của sản phẩm. Chỉ **1 lượt** đạt ngay lần đầu:

1. rò mock `tts.synthesize` sang tầng `--online`;
2. rò mock `list_speakers`/`discover` sang tầng `--hardware`;
3. sập giữa chừng vì `KeyError`, mọi mục sau im lặng;
4. đọc `player_state` ngay lúc `play_media` trả về — đòi một trạng thái đã hết hạn;
5. tráo `_manager` mà quên `_media_server` → `url_for()` nhận file ngoài thư mục
   nó phục vụ.

6. đọc `duration` không có mốc chờ, và `len(x) == len(set(x))` — hai lỗi của
   lượt 2026-08-28, cả hai đều là luật mục "Luật của bài kiểm" **đã có tên**.

Phiên thứ sáu **đạt ngay lần đầu, 78/78** — rồi phiên thứ bảy lại vấp. Các luật
ở mục "Luật của bài kiểm" phía trên chính là kết tinh của đúng những lần vấp
đó; đó là lý do chúng được viết ra thành luật thay vì để trong đầu.

Và bài học đắt nhất nằm ở chỗ khác: hai lỗi của lượt thứ bảy **vi phạm những
luật đã viết ra rồi**. **Biết luật không thay thế được việc chạy thật.** Một
danh sách luật làm cho lỗi dễ nhận ra SAU khi đã thấy nó; nó không làm cho lỗi
không xảy ra.

## Số đo lịch sử

| Lượt | Kết quả |
|---|---|
| Eval offline, 8 phiên | 35 → 43 → 67 → 138 → 49 → 77 → 57 → **57** (số mục đổi vì cách chia mục đổi; exit 0) |
| Eval `--online`, 4 lượt | 157 → 49 → 82 → **3/3** (lượt 2026-09-07: 60/60 gộp cả offline) |
| Eval `--hardware`, 7 lượt | 37 → 48 → 67 → 157 → 49 → 78/78 → **63/64 rồi 64/64 sau khi sửa 2 lỗi của chính bài kiểm** |
| Kiểm ngược, lượt 2026-09-07 | **60/60, 57s**, phủ 57/57 |
| TTS dồn 6 yêu cầu, 4 lượt | 4/6 (101s) → 6/6 (12s) → 6/6 (6.2s) → **6/6 (5.1s)** |

Cột "số lần" ở đây là **số**, không phải chữ "nhiều". Chỗ nào chưa đếm thì ghi
**CHƯA ĐẾM** kèm cận dưới, không để trống.
