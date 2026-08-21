# Bộ kiểm googlecast-mcp

Một file: `eval-googlecast-mcp.py`. Không cần pytest — chạy được ngay sau
`uv sync` trên một bản clone trắng.

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py            # 62 mục, không tiếng
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online   # +10 mục, cần internet, vẫn không tiếng
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware --speaker "Kitchen speaker"
```

Thoát 0 khi mọi mục được chọn đều xanh.

## Phân tầng theo tác dụng phụ

Product này gây tác dụng phụ **vật lý**: nó phát tiếng thật trong nhà người ta.
Một bộ test mà không ai dám chạy thì bằng không có. Nên tầng mặc định được kéo
xuống mức **không tác dụng phụ nào**, và những gì có tác dụng phụ thì phải bật
tường minh.

| Tầng | Cờ | Cần gì | Gây ra gì |
|---|---|---|---|
| offline | (mặc định) | không gì cả | không mạng, không tiếng, không chạm thiết bị thật |
| online | `--online` | internet | tổng hợp mp3 thật, **vẫn không tiếng** |
| hardware | `--hardware` | loa thật, cùng LAN | **PHÁT TIẾNG THẬT** |

Tầng mặc định còn trỏ `GOOGLECAST_MCP_STORE` và `GOOGLECAST_MCP_CACHE` vào thư
mục tạm **trước khi import** server, nên một lần chạy eval không bao giờ đọc hay
ghi đè `~/.googlecast-mcp/speakers.json` thật.

## Bộ dữ liệu giả dựng lại đúng cái nhà thật

Bốn "loa" trong fixture cố ý tái hiện tình huống đã sinh ra lỗi: **`Family
speaker group` và `Kitchen speaker` cùng nằm ở `192.168.1.22`** — nhóm và một
thành viên của nó là **cùng một cái loa vật lý**. Không có chi tiết này thì
không test nào bắt được lỗi chồng luồng.

## Kiểm ngược: có tuyên bố kỳ vọng TRƯỚC

Một bộ test chưa từng đỏ là một bộ test chưa chứng minh được gì. Quy trình bắt
buộc ở đây là **liệt kê trước** những mục phải đỏ, rồi mới đưa lỗi vào.

**Lỗi dùng để kiểm ngược:** hoàn nguyên commit `fcf4035` — cho `all` gộp cả
nhóm loa trở lại. Đây đúng là lỗi đã có thật.

### Bước 1 — Kỳ vọng, viết ra trước khi chạy

Dự kiến 8 mục đỏ, tổng 54/62:

1. `'all' excludes speaker groups`
2. `'all' hits no physical device twice (compared by host, not name)`
3. `'all' still reaches every individual speaker`
4. `'tất cả' means every speaker, groups excluded`
5. `'tat ca' means every speaker, groups excluded`
6. `'everyone' means every speaker, groups excluded`
7. `'*' means every speaker, groups excluded`
8. `'ALL' means every speaker, groups excluded`

Mọi mục còn lại: xanh.

### Bước 2 — Đưa lỗi vào và chạy

```
54/62 checks passed

failed:
  - 'all' excludes speaker groups
      (cast to ['Family speaker group', 'Kitchen speaker', 'Bedroom speaker', 'Office speaker'])
  - 'all' hits no physical device twice (compared by host, not name)
      (hosts=['192.168.1.22', '192.168.1.22', '192.168.1.23', '192.168.1.24']
       from ['Family speaker group', 'Kitchen speaker', 'Bedroom speaker', 'Office speaker'])
  - 'all' still reaches every individual speaker
  - 'tất cả' means every speaker, groups excluded
  - 'tat ca' means every speaker, groups excluded
  - 'everyone' means every speaker, groups excluded
  - '*' means every speaker, groups excluded
  - 'ALL' means every speaker, groups excluded
```

### Bước 3 — So kỳ vọng với thực tế

| | |
|---|---|
| Kỳ vọng đỏ | 8 mục |
| Thực tế đỏ | 8 mục, **đúng y danh sách trên** |
| **Lẽ ra đỏ mà xanh (TEST GIẢ)** | **không có** |
| Lẽ ra xanh mà đỏ | không có |

### Bước 4 — Khôi phục và xác minh sạch

```
$ git checkout -- src/googlecast_mcp/server.py
$ git diff --stat -- src/ scripts/
(rỗng)
$ uv run python _dong-goi/package/eval/eval-googlecast-mcp.py
62/62 checks passed   (exit 0)
```

## TEST GIẢ đã bắt được và đã sửa

Phiên đóng gói trước có một mục tên `all: no duplicate physical device`. Khi
đưa đúng lỗi này vào, **nó vẫn xanh** — trong khi lỗi đang tồn tại rành rành.

Lý do: nó so trùng lặp theo **tên**. Mà nhóm loa và thành viên của nó có tên
khác nhau. Nên nó mù hoàn toàn trước dạng trùng lặp duy nhất có ý nghĩa ở đây:
trùng ở mức **thiết bị vật lý**.

Phiên đó chỉ **ghi chú lại** rằng mục này không bắt được lỗi. Ghi chú không sửa
được gì: mục test vẫn xanh, người đọc bảng kết quả vẫn tưởng đã được bảo vệ.
Lần này nó được **sửa thật**: so theo `host`, không theo tên.

```python
hosts_hit = [HOST_BY_NAME[n] for n in names if n in HOST_BY_NAME]
check("'all' hits no physical device twice (compared by host, not name)",
      len(hosts_hit) == len(set(hosts_hit)), ...)
```

Bằng chứng nó thật sự bắt được: ở bước 2 phía trên nó nằm trong danh sách đỏ,
kèm đúng hai lần `192.168.1.22`.

**Bài học chung:** một mục test xanh trong khi lỗi đang tồn tại thì nguy hiểm
hơn hẳn một mục test không tồn tại — nó tạo ra cảm giác đã được che chắn. Chỉ
kiểm ngược mới lôi được nó ra, và chỉ khi kỳ vọng được viết ra **trước**.

## Một lỗi thật của chính bộ eval, tìm ra trong phiên này

Tầng offline thay `tts.synthesize` **trên chính module object**, mà module thì
mọi nơi import đều dùng chung. Hậu quả: khi tầng `--online` chạy sau, nó đo
đúng cái hàm giả của mình, chứ không phải TTS thật. Triệu chứng là "mp3 0 byte"
— và nếu chỉ nhìn thoáng qua thì rất dễ kết luận nhầm rằng edge-tts hỏng.

Đã sửa: giữ lại tham chiếu tới hàm thật, khôi phục trước khi tầng online đo, và
thêm hẳn một mục canh gác:

```
PASS  the online tier is testing the real synthesize, not the fake
```

Một bộ eval cũng là mã nguồn, cũng hỏng được, và nó hỏng theo hướng **xanh
giả**.

### Rò lần thứ hai — cùng một họ, phát hiện khi chạy tầng hardware

Mục canh gác trên chỉ che đường TTS. Tầng hardware sau đó vẫn **FAIL** với
`no speaker answered mDNS`, trong khi loa vẫn sống (cổng 8009 mở) và một lần
`say` thủ công vẫn phát được bình thường.

Nguyên nhân: phép thử "mạng rỗng" thay `list_speakers` và `discover` lên chính
`server._manager` rồi **không khôi phục**. Tầng hardware dùng lại đúng object
đó, nên nó "dò" thấy cái mạng rỗng mà phép thử trước dựng ra. Đổi biến môi
trường store và reload module không cứu được, vì cái hỏng nằm ở object đã bị
sửa, không phải ở cấu hình.

Đã sửa: tầng hardware **dựng `CastManager` mới** thay vì tin object dùng chung,
kèm một mục canh gác nữa:

```
PASS  hardware tier holds a real manager, not an offline stub
```

Bài học: một mục canh gác chỉ bảo vệ **đúng một** đường bị mock. Mỗi thứ tầng
trước thay thế đều cần canh gác riêng — và cách rẻ nhất để tìm ra là **chạy
tầng sau và hỏi tại sao nó đỏ**, thay vì cho rằng mạng đang trục trặc.

## Bảng phủ

| Nhóm | Số mục | Phủ điều gì |
|---|---|---|
| import + bề mặt tool | 4 | import được; đúng 13 tool; đúng tên; tool nào cũng có mô tả |
| đoán content type | 6 | mp3/mp4/hls, có query string, chữ hoa, đuôi lạ |
| phân loại loa | 4 | `audio`/`group` là loa, `cast` thì không, thiếu trường thì không |
| giọng đọc | 5 | mặc định, `female`/`male`, khoảng trắng và chữ hoa, id đầy đủ |
| allowlist transport | 9 | **có scheme https**, **có host trần không port**, loopback, `0.0.0.0` không tự vào allowlist, origin trình duyệt |
| kho thiết bị | 5 | kho rỗng, lưu-đọc, gộp theo uuid, giữ địa chỉ mới, lọc loa |
| `say` thiếu loa | 5 | `needs_speaker_selection`, **không cast**, **không gọi TTS**, có danh sách loa |
| `say` với `all` | 7 | bỏ nhóm, **không trùng thiết bị vật lý theo host**, tổng hợp đúng một lần, chung một URL |
| từ khoá "tất cả" | 5 | `tất cả`, `tat ca`, `everyone`, `*`, `ALL` |
| chỉ định tường minh | 3 | nhóm gọi đích danh vẫn phát, danh sách cách phẩy, khoảng trắng thừa |
| cô lập lỗi | 5 | loa hỏng không kéo loa tốt chết theo; không loa nào phát thì báo `failed` |
| text rỗng | 2 | `ValueError`, không cast |
| mạng không có loa | 2 | `no_speakers_found`, không cast |
| **online** | 10 | canh gác hàm thật, mp3 khác rỗng, đúng magic byte, dùng lại cache, đổi giọng/tốc độ ra file khác |
| **hardware** | 4 | dò được loa thật, cast thật, thiết bị báo trạng thái media |

## Diễn tập Definition of Done

Chạy lại đúng từng lệnh trong `../README.md` trên một bản clone trắng, cổng
8799 (không đụng dịch vụ thật ở 8765/8766).

```
### STEP 1 — uv 0.11.21 (x86_64-unknown-linux-gnu)
### STEP 2 — cloned; thấy pyproject.toml, src/, scripts/, uv.lock
### STEP 3 — uv sync: cài xong (uvicorn, zeroconf, yarl, …)
### STEP 4 — uv run googlecast-mcp --help → in bảng tuỳ chọn có --transport {stdio,http,sse}
### STEP 5 — stdio qua pipe:
initialize ok: {'name': 'googlecast-mcp', 'version': '1.29.0'} 2024-11-05
tools/list count: 13
tools: discover_devices, get_status, list_devices, list_speakers, pause, play,
       play_media, quit_app, say, seek, set_muted, set_volume, stop
### STEP 6 — HTTP 127.0.0.1:8799
initialize → 200, serverInfo googlecast-mcp
session id: 6346b31b12674dee8d7904189202bbe1
tools/list count: 13
tools/call say (cố ý không chọn loa):
  status: needs_speaker_selection
  speakers offered: ['Kitchen speaker', 'Family speaker group',
                     'Bedroom speaker', 'Spa speaker']
### STEP 7 — 8799 đã đóng; 8765/8766 của dịch vụ thật vẫn nguyên
```

Mục cuối là bằng chứng mạnh nhất: đó là một **lần gọi tool thật**, đi hết chuỗi
client → MCP → dò mạng → và trả về **tên loa thật trong nhà**. Nó cũng không
phát ra tiếng nào, nên diễn tập DoD an toàn để chạy lại bất cứ lúc nào.

## Số liệu các lần chạy

| Lần | Tầng | Kết quả |
|---|---|---|
| bản đóng gói này | offline | **62/62**, exit 0 |
| bản đóng gói này | offline + online | **72/72**, exit 0 |
| bản đóng gói này | offline, có lỗi cấy vào | 54/62, đúng 8 mục kỳ vọng |
| bản đóng gói này | `--hardware` | **CHƯA CHẠY** — cần người dùng cho phép |
| hai phiên trước | offline | 35/35, rồi 43/43 |
| hai phiên trước | `--hardware` | 37/37, rồi 48/48 |

## Chưa phủ, nói thẳng

- **Giọng nam và tham số `rate` chưa được nghe.** Eval chỉ chứng minh chúng ra
  file mp3 khác rỗng, khác nhau. Chất lượng nghe được thì chưa ai kiểm.
- **Dịch vụ sống sót qua reboot máy:** đã `systemctl enable`, **chưa reboot bao
  giờ**.
- **Địa chỉ đã lưu bị cũ** (loa đổi IP) → nhánh quét lại trong `_connect_saved`
  chưa từng chạy trong test.
- **Chặn IP ở nginx** đã bàn và đã đồng ý bật, nhưng hai dòng vẫn đang comment.
- **Tầng hardware** chỉ kiểm được API báo `playing`. Chuyện âm thanh có thật sự
  đúng hay không thì API mù — chính lỗi chồng luồng đã chứng minh điều đó. Chỗ
  này không có cách tự động hoá; phải có tai người.
