# Bộ kiểm chứng googlecast-mcp

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py             # 138 mục, ~0.5s
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online    # 157 mục, ~20-110s
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware  # SẼ PHÁT TIẾNG
uv run python _dong-goi/package/eval/reverse-check.py                   # kiểm ngược, ~1-2 phút
```

## Ba tầng, phân theo tác dụng phụ

| Tầng | Cờ | Làm gì | An toàn chạy lúc nào? |
|---|---|---|---|
| 1 | *(mặc định)* | 138 mục, toàn bộ logic chọn đích / lọc loa / allowlist / lưu bền | **Bất cứ lúc nào** |
| 2 | `--online` | thêm 19 mục gọi edge-tts thật | cần internet, tốn hạn ngạch Microsoft |
| 3 | `--hardware` | cast thật ra loa | **có tiếng động vật lý — phải xin phép** |

**Vì sao mặc định phải không tác dụng phụ:** sản phẩm này phát tiếng trong nhà
người khác. Nếu bộ kiểm mặc định làm loa kêu, sẽ không ai chạy nó, và một bộ
kiểm không ai dám chạy thì bằng không có.

Ngoại lệ duy nhất ở tầng 1: nhóm `1.16` mở một cổng HTTP tạm trên máy này (cổng
0 → hệ chọn cổng rỗi), phục vụ một thư mục tạm, và đóng ngay trong `finally`.
Không gói tin nào ra ngoài, không tốn tiền, không ai nghe thấy gì.

### Kết quả mới nhất

```
Tầng offline   : 138/138 đạt (0.5s)
Tầng --online  : 157/157 đạt
Tầng --hardware: ĐÃ CHẠY sau khi xin phép — **157/157, exit 0**.

Lần chạy đầu đỏ một mục (`loa thật thật sự phát dù bạn cùng lượt hỏng`), và đó
là lỗi của BÀI KIỂM chứ không phải của sản phẩm. Hai bẫy chồng lên nhau:

1. Mục kiểm hỏi trạng thái qua **một `CastManager` khác** cái mà `say()` đã
   dùng. Trạng thái media là *theo từng kết nối* — kết nối không phát thì báo
   `UNKNOWN` mãi, nên `wait_until` hết mốc chờ là tất yếu.
2. Kể cả hỏi đúng manager thì vẫn đỏ: phần tử hỏng kéo `say()` dài **5.4s**
   trong khi clip chỉ **2.26s**, nên lúc `say()` trả về loa đã phát XONG
   (`IDLE`, `duration=2.256`). Đòi thấy `PLAYING` là đòi một trạng thái **chắc
   chắn đã hết hạn**.

Sửa: kiểm **bằng chứng còn lại** thay vì trạng thái thoáng qua — `content_id`
của thiết bị khớp đúng URL vừa cast, và `duration > 0`. Cả hai đều tồn tại sau
khi phát xong.

Bài học, bổ sung cho luật "mốc chờ" của v1.6: **có mốc chờ vẫn chưa đủ.** Nếu
thứ mình chờ là một trạng thái thoáng qua và đường thất bại của bạn cùng lượt
dài hơn chính nó, thì chờ bao lâu cũng vô ích. Phải chọn *bằng chứng bền*.
reverse-check  : 12 lỗi gieo + 1 đối chứng — không có mục lẽ-ra-đỏ-mà-xanh; hoàn nguyên XANH
```

---

## Kiểm ngược: chứng minh bộ kiểm có thật

**Một bộ eval chưa từng ĐỎ là một bộ eval chưa chứng minh được gì.**
`reverse-check.py` làm đúng bốn bước, và **thứ tự là điểm mấu chốt**:

1. **Khai TRƯỚC kỳ vọng.** Mỗi lỗi gieo vào đi kèm danh sách mục kiểm *lẽ ra
   phải đỏ*, viết ra trước khi chạy. Nhìn kết quả rồi mới "kỳ vọng" là tự lừa
   mình.
2. Gieo lỗi, chạy lại eval.
3. So kỳ vọng với thực tế. Mục **lẽ-ra-đỏ-mà-XANH = TEST GIẢ** → phải **sửa bài
   kiểm** hoặc ghi **CHƯA PHỦ**. Viết một dòng chú thích rồi bỏ qua **không
   phải một lựa chọn**.
4. Khôi phục → **xoá `__pycache__`** → **chạy lại eval, đòi thấy XANH**.

### Vì sao bước 4 không phải là nhìn `git status`

Đã dính thật: một lỗi gieo vào **dài đúng bằng bản gốc**, khôi phục xong `git
status` sạch trơn — nhưng `.pyc` cũ vẫn nằm đó và eval vẫn đỏ. Suýt kết luận
"sản phẩm hỏng" trong khi thứ hỏng là bytecode đọng lại.

**Hoàn nguyên = chạy lại eval thấy xanh sau khi xoá bytecode. Không có đường
tắt.**

### 12 lỗi đã gieo và kết quả

| Lỗi gieo vào | Mục kiểm đỏ đúng kỳ vọng |
|---|---|
| Hoàn nguyên bản vá `all` (gửi cả nhóm lẫn thành viên) | tập loa, không-có-nhóm, mỗi-host-một-luồng |
| Coi thiết bị hình ảnh cũng là loa | `is_speaker`, tập loa hỏi lại, tập `all` |
| **Đổi tên một tool (số lượng KHÔNG đổi)** | tập tool ≠ tập kỳ vọng |
| Allowlist bỏ dạng host trần | `127.0.0.1`, domain trần |
| Allowlist bỏ scheme `https` | origin https trần / kèm cổng |
| Thiếu chọn loa thì cứ phát tất cả | không-cast, không-gọi-TTS, chuỗi toàn khoảng trắng |
| Media server quảng bá `0.0.0.0` | URL phải là địa chỉ LAN |
| Bỏ chốt chặn text rỗng | `''`, `'   '` → ValueError |
| `SpeakerStore` ghi đè thay vì gộp | gộp-không-ghi-đè, lọc loa |
| Bỏ kẹp âm lượng | `set_volume(5.0)`→1.0, giá trị gửi xuống thiết bị |
| Đoán sai MIME cho `.mp3` | ba biến thể URL mp3 |
| Một loa hỏng làm đổ cả lượt | lỗi riêng cho loa hỏng, `failed` khi không loa nào phát |
| *(đối chứng)* sửa một dòng chú thích | eval **vẫn XANH** — đúng như phải thế |

### Kiểm ngược đã bắt được gì trong chính bộ eval này

Không phải để trang trí — nó tìm ra ba thứ thật:

1. **Test giả loại "chú thích không được kiểm".** `"chuỗi chọn loa toàn khoảng
   trắng cũng là 'chưa chọn'"` không bao giờ đỏ. Nguyên nhân sâu hơn nhiều so
   với vẻ ngoài: khi hình dạng trả về đổi, mục kiểm phía trên **ném KeyError**,
   eval **sập giữa chừng**, và mọi mục kiểm phía sau **không bao giờ chạy** —
   trông như "ít đỏ hơn" thực tế. Đã vá hai chỗ: dùng `.get()` cho các truy cập
   phụ thuộc hình dạng, và bọc mỗi tầng để một cú sập bị ghi thành mục ĐỎ chứ
   không nuốt mất cả lượt.
2. **Một kỳ vọng SAI (không phải test giả).** Từng kỳ vọng lỗi MIME làm đỏ mục
   `"content_type gửi cho loa"`. Thực tế `say()` truyền thẳng hằng
   `"audio/mpeg"`, không đi qua bảng MIME. Bài kiểm vẫn thật; **kỳ vọng mới là
   thứ sai** → sửa kỳ vọng, **không nới bài kiểm**. Phân biệt hai ca này là
   quan trọng: nới bài kiểm cho khớp kỳ vọng sai là cách tạo ra test giả.
3. **Một mục kiểm chỉ đang kiểm Python.** `min(1.0, max(0.0, 5.0)) == 1.0` viết
   lại biểu thức kẹp âm lượng ngay trong bài kiểm, tức là không hề chạm vào
   `CastManager.set_volume`. Đã thay bằng lời gọi thật vào sản phẩm với một
   thiết bị giả ghi lại giá trị nhận được.

## CHƯA PHỦ — nói thẳng

| Vùng | Vì sao chưa phủ |
|---|---|
| Tầng `--hardware` trong `reverse-check` | không gieo lỗi tự động được; cần loa thật và sẽ phát tiếng. Luật mốc chờ ở đó **đã được kiểm ngược MỘT LẦN BẰNG TAY**: bản trước đọc `player_state` ngay khi `play_media` trả về và **đỏ thật** (`Kitchen speaker reports IDLE`) dù loa hoàn toàn tốt; thay bằng `wait_until` thì xanh 91/91 |
| Nhánh `_connect_saved` **thành công** | cần một thiết bị Cast thật ở địa chỉ đã lưu |
| nginx / TLS / CORS ở tầng proxy | eval chỉ kiểm allowlist mà tiến trình sinh ra, không dựng nginx |
| Chất lượng giọng đọc | không đo được bằng máy — bắt buộc người nghe |
| Tiếng chồng luồng khi phát ra nhóm + thành viên | eval chốt được *quy tắc chọn đích* qua dấu vết trùng `host`, nhưng **âm thanh thật sự phát ra** thì API báo `playing` cho mọi đích — chỉ tai người nghe ra |

## Một mục kiểm dạng so-kích-thước còn lại, có chủ ý

`2.3 "bản chậm dài hơn bản thường"` so kích thước hai file mp3. Đây **không**
phải so-kích-thước-thay-cho-so-tập: nó là một khẳng định **có hướng** (đọc chậm
hơn thì âm thanh dài hơn) và không có tập kỳ vọng nào thay thế được. Mọi mục
kiểm dạng đếm khác trong bộ này đã được đổi sang so tập tường minh.

## Vệ sinh mock

- Ảnh chụp lấy **trước tầng đầu tiên**, khôi phục trong `finally`.
- Mỗi mục kiểm dựng `FakeManager` / `FakeTTS` **MỚI**.
- Giữa các tầng, khôi phục về ảnh chụp trước khi vào tầng sau.
- **Không dùng `importlib.reload`.** Nó nạp module mới dưới chân chính cái ảnh
  chụp đang giữ tay nắm — tức là phá luôn đường khôi phục. Đã thử ở một phiên
  trước và phải loại bỏ.

## Điểm còn hở bộ kiểm phát hiện trong SẢN PHẨM

Bộ kiểm này tìm ra hai khiếm khuyết thật trong `tts.py`, đã ghi vào
`technical-docs.md` mục 6 (#6, #7) và **chưa vá**:

1. **`tts.synthesize` không thử lại.** edge-tts trả `NoAudioReceived` khi bị bắn
   nhiều yêu cầu sát nhau. Đo được: liên tiếp không giãn cách hỏng ~2/3; giãn 4s
   thì 6/6 đạt. Một loạt `say` dồn dập trong đời thật sẽ hỏng.
   Tầng `--online` bọc lời gọi bằng `synth_online()` có giãn cách và thử lại —
   để bài kiểm đo **hành vi của sản phẩm** chứ không đo hạn ngạch của Microsoft.
   Cái bọc đó **không** làm khiếm khuyết biến mất, nó chỉ được ghi ra.
2. **File 0 byte đọng trong cache khi synthesize hỏng.** `Communicate.save()`
   kịp tạo file rồi mới ném lỗi, mà nhánh dọn dẹp nằm SAU lời gọi đó nên không
   bao giờ chạy. Không sai hành vi (lần sau vẫn sinh lại), nhưng là rác.
   Vá: bọc `save()` trong `try/except`, `unlink` rồi ném tiếp.
   Mục `2.5` chốt lại đúng hành vi hiện tại và **gọi tên nó là điểm còn hở**,
   không tô hồng thành "đạt".
