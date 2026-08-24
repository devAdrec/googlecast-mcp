# Eval

Sản phẩm này **không có test nào** trước khi đóng gói. Bộ eval ở đây là lớp
kiểm chứng đầu tiên của nó.

## Chạy

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py            # 67 kiểm
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online   # 79 kiểm
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware # PHÁT TIẾNG THẬT
uv run python _dong-goi/package/eval/reverse-check.py                  # kiểm ngược
```

Exit 0 = mọi kiểm đều xanh.

## Ba tầng, phân theo tác dụng phụ

| Tầng | Cờ | Cần gì | Gây ra gì | Kết quả gần nhất |
|---|---|---|---|---|
| offline | (mặc định) | không gì cả | không gì cả | **67/67**, exit 0 |
| online | `--online` | internet | không tiếng | **79/79**, exit 0 |
| hardware | `--hardware` | loa thật | **phát tiếng trong nhà** | **91/91, exit 0** |

Tầng mặc định phải không có tác dụng phụ. Một bộ test mà không ai dám chạy thì
bằng như không có. Tầng phát tiếng là cờ opt-in, và phải xin phép chủ nhà mỗi
lần — nó gây ồn ở một căn nhà thật.

## Vệ sinh mock — vì sao file này viết như thế

Bài học phải trả giá hai lần ở phiên trước:

1. Tầng offline thay `tts.synthesize` ngay trên module object. Tầng `--online`
   sau đó đo nhầm hàm giả và báo "mp3 0 byte". Thêm một canh gác để chặn.
2. Canh gác ấy **chỉ che đường TTS**. Một phép thử "mạng rỗng" thay
   `list_speakers` / `discover` lên `server._manager` rồi không khôi phục →
   tầng `--hardware` FAIL `no speaker answered mDNS` trong khi loa vẫn sống:
   cổng 8009 mở, gọi `say` thủ công phát được bình thường.

Bài học: **một canh gác chỉ che đúng một đường.** Đừng đi vá từng đường —
hãy cô lập.

### Loại thứ ba: đo đúng thứ, sai thời điểm

Vệ sinh mock lần này làm chặt nên hai lỗi trên không tái diễn. Nhưng lần chạy
`--hardware` đầu tiên vẫn đỏ một mục: `Kitchen speaker reports IDLE`.

Không phải rò mock, cũng không phải loa hỏng — mục kiểm đọc `player_state`
**ngay khoảnh khắc `play_media` trả về**, mà hàm đó chỉ chờ *ứng dụng nhận*
khởi động xong, chưa chờ *phát*. Thiết bị còn `IDLE` thêm một nhịp. Với clip
ngắn thì còn có thể phát xong trước khi mục kiểm kịp nhìn.

Đã sửa: **chờ tới trạng thái cần thấy** (poll tối đa 10 giây) thay vì giả định
nó đã tới. Sau khi sửa: `91/91`.

Bài học: một khẳng định về hệ thống bất đồng bộ phải nói rõ **chờ tới bao giờ**.
Không có mốc chờ thì nó không kiểm hành vi, nó kiểm tốc độ mạng.

Ba luật trong `eval-googlecast-mcp.py`:

- Mọi phép thay thế đi qua `patched()`, khôi phục trong `finally`, kể cả khi
  thân hàm ném lỗi.
- `assert_pristine()` chạy **sau mỗi tầng**, đối chiếu với ảnh chụp lấy trước
  khi tầng đầu tiên chạy. Mock nào sống sót qua tầng của nó là đỏ ngay tại chỗ.
- Tầng `--online` và `--hardware` **không dùng singleton dùng chung**. Chúng
  tự dựng `CastManager` / `MediaServer` mới. Rò rỉ ở phía trên không thể làm
  chúng đo nhầm — theo cả hai chiều: thành công giả, hoặc "không thấy loa" giả.

Có một cám dỗ đã thử và loại bỏ: `importlib.reload(tts)` ở đầu tầng online.
Reload gán lại một function object hoàn toàn mới, phá mất cái tay nắm duy nhất
vào hàm thật, khiến canh gác không còn phân biệt được thật với giả. Đối chiếu
với ảnh chụp thì được; reload thì không.

## Kiểm ngược — có kỳ vọng viết TRƯỚC

`reverse-check.py` giữ sẵn danh sách *kỳ-vọng-đỏ* cho từng lỗi gieo vào, viết
**trước** khi gieo. Nó gieo lỗi, chạy eval, đối chiếu, rồi `git checkout --`
khôi phục và tự xác minh cây mã sạch lại.

Mục nào lẽ ra đỏ mà vẫn xanh là **TEST GIẢ**: nó đang khẳng định một điều mà
mã nguồn không thật sự phụ thuộc vào.

| Lỗi gieo | Nếu có thật thì hỏng gì |
|---|---|
| `M1` `'all'` lấy nhóm thay vì loa lẻ | Chồng luồng lên một loa vật lý |
| `M2` bỏ host trần khỏi allowlist | Proxy ở cổng 443 → mọi request 421 |
| `M3` không từ chối text rỗng | Text rỗng tới backend TTS, sinh mp3 0 byte |

### Kết quả lần chạy này

```
baseline: exit 0, 0 red
M1  exit 1, 5 red — cả 5 mục đỏ đúng dự đoán
M2  exit 1, 3 red — cả 3 mục đỏ đúng dự đoán
M3  exit 1, 2 red — cả 2 mục đỏ đúng dự đoán
source restored cleanly: True
post-restore eval: exit 0, 0 red
reverse check passed
```

### Hai thứ vòng kiểm ngược đầu tiên bắt được

**Một TEST GIẢ thật.** Kiểm ban đầu viết là *"`all` không đụng một host quá
một lần"* — `len(hosts) == len(set(hosts))`. Gieo M1 vào, nó **vẫn xanh**: khi
`all` sai thành đúng một phần tử (nhóm), tập một phần tử đương nhiên không
trùng. Câu khẳng định đúng nhưng rỗng. Đã sửa thành **phủ chính xác**: số lần
cast phải bằng đúng tập host loa riêng biệt — không thừa, không thiếu. Bản mới
đỏ cả với lỗi M1 lẫn lỗi gốc (không lọc gì cả).

**Bytecode cũ.** M1 đổi `!= "group"` thành `== "group"` — **dài y hệt**.
`git checkout` khôi phục nội dung, `git status` sạch, nhưng eval vẫn đỏ ba
mục: Python đang chạy lại `.pyc` cũ. Nghĩa là nếu bỏ bước "xác minh mã hoàn
nguyên sạch", vòng kiểm ngược sẽ đọc ra một kết luận sai hoàn toàn.
`reverse-check.py` giờ xoá bytecode trước **mỗi** lần chạy. Đừng bỏ dòng đó.

## Kiểm những gì

**Offline (67):** import và đúng 13 tool đăng ký · `say` không require
`target` trong schema · phân loại loa/nhóm/thiết bị hình ảnh · đoán MIME theo
đuôi file · phân giải tên giọng · text rỗng → `ValueError` **và** không chạm
tới backend TTS · `SpeakerStore` lưu-đọc, hợp nhất chứ không thay thế, file
hỏng không sập · thiếu `target` → `needs_speaker_selection`, **không cast,
không TTS** (chứng minh bằng tripwire, không phải bằng giá trị trả về) · mạng
rỗng → `no_speakers_found` · `all` / `tất cả` / nhiều tên cách phẩy / nhóm gọi
đích danh / khoảng trắng thừa · `all` phủ đúng mỗi host vật lý một lần · cô
lập lỗi khi một loa hỏng · mọi loa hỏng → `failed` · allowlist có host trần và
scheme `https`, không có `0.0.0.0` · URL media quảng bá host LAN, mã hoá tên
file tiếng Việt, cổng thật sự nhận kết nối, `stop()` nhả cổng · bốn kiểm vệ
sinh mock sau mỗi tầng.

**Online (+12):** hàm dưới phép thử đúng là hàm thật · mp3 khác rỗng, header
đúng định dạng · dùng lại cache đúng khoá · `rate` khác thì cache riêng ·
giọng nam tổng hợp được (**không** chấm bằng tai — xem CHƯA THỬ).

**Hardware:** mDNS thấy thiết bị · có loa trên LAN · cổng 8009 mở (phân biệt
thiết bị treo với lỗi mã nguồn) · cast thật và về trạng thái hợp lý.

## CHƯA PHỦ (nói thẳng, không giấu)

- **Chất lượng giọng nói.** R2.2 "nghe tự nhiên" chỉ tai người chấm được. Eval
  chỉ kiểm được file khác rỗng và đúng định dạng mp3.
- **Tham số `rate` nghe ra sao.** Chỉ kiểm được rằng nó tạo ra một bản render
  khác.
- **Chồng luồng khi `all` sai.** Eval kiểm được *tập đích* đúng; nó không nghe
  được. Chính vì API trả `playing` cả bốn lần mà lỗi này mới sống sót tới lúc
  có người nghe.
- **nginx, TLS, CORS ngoài đời.** Chỉ kiểm được hàm sinh allowlist. Chưa dựng
  proxy trong eval.
- **Service sống sót qua reboot.** Đã `enable`, chưa reboot bao giờ.
- **Địa chỉ đã lưu bị cũ vì loa đổi IP** → nhánh quét lại: chưa thử.
- **Chặn IP ở nginx.** Đã đồng ý bật, hai dòng vẫn đang comment.
