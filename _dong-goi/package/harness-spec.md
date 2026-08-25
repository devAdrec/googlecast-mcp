# Harness spec — googlecast-mcp

Loại: **harness vận hành** (máy móc, kết quả xác định). Không có bước nào do AI
sinh ra output tự do, nên eval đo **đúng/sai**, không đo chất lượng.

Trọng số năm lớp cho loại này:

| Lớp | Trọng số | Vì sao |
|---|---|---|
| Context | thấp | tool có mô tả rõ; không có prompt phức tạp cần chỉnh |
| **Tool** | **cao** | 13 tool là toàn bộ bề mặt hợp đồng |
| **Execution** | **cao** | tác dụng phụ VẬT LÝ — phát tiếng trong nhà |
| **Eval** | **cao** | phần lớn hành vi phải kiểm được mà không phát tiếng |
| Feedback | trung bình | lỗi phải nói được nguyên nhân cho người vận hành |

---

## Lớp 1 — Context

Trợ lý chỉ có mô tả tool để hành động. Ba điều mô tả phải nói rõ:

1. **Chạy `discover_devices` trước** — nói thẳng trong docstring.
2. **Bỏ `target` thì KHÔNG phát gì** — nói thẳng, để LLM không tưởng là mặc
   định phát tất cả.
3. **Các dạng `target`** — một tên, nhiều tên cách phẩy, hoặc `all`.

Kiểm: mọi tool có `description` khác rỗng; `say` có đúng `text` là bắt buộc.

## Lớp 2 — Tool

Hợp đồng: **đúng 13 tool, đúng 13 cái tên đó.**

Bài kiểm so **TẬP** với `EXPECTED_TOOLS`, không so số lượng. Kiểm ngược đã gieo
đúng lỗi bẫy: đổi tên `quit_app` → `quit_application`. **Số lượng không đổi**,
nên một bài kiểm đếm sẽ vẫn xanh. Bài kiểm so tập thì đỏ.

Ranh giới đầu vào phải giữ:

| Tool | Ranh giới |
|---|---|
| `say` | `text` rỗng/toàn khoảng trắng → `ValueError`, **không gọi mạng** |
| `say` | `target` rỗng → `needs_speaker_selection` |
| `set_volume` | ngoài `[0,1]` bị kẹp, không lọt xuống thiết bị |
| `play_media` | thiếu `content_type` → đoán từ đuôi URL |

## Lớp 3 — Execution

**Đây là lớp quyết định cách phân tầng bộ kiểm.** Sản phẩm có tác dụng phụ vật
lý: nó phát ra tiếng trong nhà người khác.

| Tầng | Cờ | Tác dụng phụ | Chạy được mọi lúc? |
|---|---|---|---|
| 1 — offline | *(mặc định)* | mở một cổng HTTP tạm trên máy này, đóng ngay | **Có** |
| 2 — online | `--online` | gọi edge-tts (Microsoft), tốn hạn ngạch | Cần internet |
| 3 — hardware | `--hardware` | **PHÁT TIẾNG THẬT** | Chỉ khi đã xin phép |

Nguyên tắc: **tầng mặc định phải là tầng không ai ngại chạy.** Một bộ kiểm mà
không ai dám bấm chạy thì bằng không có.

Ba tầng phải **cô lập** với nhau:

- Ảnh chụp các thuộc tính bị thay thế được lấy **TRƯỚC tầng đầu tiên**, khôi
  phục trong `finally`.
- Mỗi tầng, mỗi mục kiểm dựng **object MỚI**. Không thừa hưởng object của tầng
  trước dù trông có vẻ sạch.
- **Không dùng `importlib.reload`.** Nó thay module mới dưới chân chính cái ảnh
  chụp đang giữ tay nắm, tức là phá luôn đường khôi phục. Đã thử, đã phải loại.

## Lớp 4 — Eval

Ba luật, mỗi luật rút từ một lỗi thật đã dính:

### Luật 1 — So TẬP KỲ VỌNG tường minh, không so kích thước

Dạng test giả phổ biến nhất là **so đếm/độ dài thay cho so tập**.

Ca thật đã dính: `len(hosts) == len(set(hosts))` để kiểm "`all` không phát chồng
lên một loa". Nó **vẫn xanh** khi `all` sai thành đúng một phần tử — một phần tử
thì không thể trùng. Bản thay thế so `{(tên, host)}` với `EXPECTED_ALL`.

Cách tự soát: mọi mục kiểm dạng `len(...)`, `count`, `>=` phải trả lời được câu
"có hình dạng SAI nào khiến con số này vẫn đúng không?".

### Luật 2 — Eval phải từng ĐỎ, với kỳ vọng khai TRƯỚC

`reverse-check.py` gieo 12 lỗi + 1 đối chứng vô hại. Mỗi lỗi khai trước danh
sách mục **lẽ ra phải đỏ**. Sau khi chạy:

- lẽ-ra-đỏ-mà-xanh → **TEST GIẢ**, phải sửa bài kiểm hoặc ghi **CHƯA PHỦ**;
- đối chứng vô hại mà làm đỏ → bài kiểm đang bám vào thứ không phải hành vi.

### Luật 3 — Hoàn nguyên = CHẠY LẠI EVAL THẤY XANH

**`git status` sạch KHÔNG phải bằng chứng hoàn nguyên.** Một lỗi gieo vào dài
đúng bằng bản gốc để lại `.pyc` cũ: git thấy sạch mà eval vẫn đỏ. Quy trình
đúng: khôi phục → **xoá `__pycache__`** → chạy lại eval → đòi thấy XANH.

### Luật 4 — Khẳng định bất đồng bộ phải có MỐC CHỜ

Mọi khẳng định chạm mạng/thiết bị phải đi kèm timeout + điều kiện thoả, qua
`wait_until()`.

Ca thật đã dính: đọc `player_state` ngay khoảnh khắc `play_media` trả về. Hàm đó
chỉ chờ **ứng dụng trên thiết bị khởi động**, chưa chờ nó **phát** → FAIL
`Kitchen speaker reports IDLE` dù loa hoàn toàn tốt. Không có mốc chờ nghĩa là
đang đo tốc độ mạng chứ không đo hành vi.

## Lớp 5 — Feedback

Lỗi phải nói được **nguyên nhân**, vì người đọc nó là người đang sửa mạng nhà
mình lúc 11 giờ đêm:

| Tình huống | Thông điệp phải chứa |
|---|---|
| Không tìm thấy thiết bị | tên đã gõ **và** danh sách tên đang biết |
| Một loa hỏng trong lượt nhiều loa | mục `error` **riêng cho loa đó**, các loa khác vẫn `playing` |
| Thiếu chọn loa | danh sách loa **và** lời hướng dẫn LLM hỏi lại |
| Không có loa nào | phân biệt rõ với "thiếu chọn loa" (`no_speakers_found`) |

Đây là lý do `_select_targets` trả về hai trạng thái khác nhau chứ không gộp
một: "chưa chọn" và "không có gì để chọn" cần hai hành động khác nhau.

---

## Điều harness này CỐ Ý không phủ

- **Chất lượng giọng đọc.** Không đo được bằng máy. Bắt buộc người nghe.
- **Tiếng chồng luồng.** API báo `playing` cho mọi đích; chỉ tai người nghe ra.
  Bài kiểm chốt được *quy tắc chọn đích* (qua dấu vết trùng `host`), nhưng
  không chốt được *âm thanh thật sự phát ra*.
- **nginx / TLS.** Eval kiểm allowlist mà tiến trình sinh ra, không dựng nginx.
- **Nhánh `_connect_saved` thành công.** Cần thiết bị Cast thật.
