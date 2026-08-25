---
product: googlecast-mcp
loai: harness vận hành (MCP server, systemd service)
ngay: 2026-08-25
transmission_level: L2 (chấm độc lập bởi người đọc sạch, 2026-08-25)
package: _dong-goi/package/
---

# Cách đã dựng googlecast-mcp

Một MCP server để trợ lý AI **nói tiếng Việt ra loa Google** trong nhà. Ghi lại
**cách nghĩ**, không phải nhật ký công việc.

Ba lớp tài sản, đừng lẫn:

| Lớp | Là gì | Ở đâu |
|---|---|---|
| Output | sản phẩm chạy được + bộ 4 tài liệu bàn giao | `_dong-goi/package/` |
| Reproduction | prompt dựng lại đúng sản phẩm này | `_dong-goi/reproduction-prompt.md` |
| **Method** | cách nghĩ, để xây **cái khác** | file này |

---

## Bài học 30 giây

Mục này là **mục lục**, không phải bản tóm tắt độc lập — mỗi dòng trỏ tới
bước nói kỹ. Cố ý để mỗi ý chỉ được giải thích ở đúng một chỗ.

1. **Dựng bản chạy được trước, rồi ĐỐI CHIẾU yêu cầu để lộ chỗ thiếu.** Danh
   sách yêu cầu chưa đạt chính là danh sách module cần viết. → Bước 1.
2. **Chọn công cụ theo loại công cụ, không theo một quy trình chung.** → Bước 2.
3. **Không biết thì HỎI, đừng đoán** — nhất là khi đoán sai gây hậu quả vật lý.
   → Bước 3.
4. **Khi người dùng nói "vẫn lỗi" lần thứ hai với đúng câu chữ cũ: DỪNG SỬA**,
   đi kiểm bản sửa đã được nạp chưa. → Bước 4.
5. **Hai mẫu trùng nhau không đủ để kết luận nguyên nhân hệ thống.** → bảng
   "Ngõ cụt", mục #7.
6. **Bài kiểm chưa từng ĐỎ là bài kiểm chưa chứng minh được gì.** → Bước 7,
   bốn luật.
7. **Kiểm một lần rồi kết luận là ngõ cụt.** Giữ **lịch sử đo** mới phân định
   được lỗi thiết bị với hồi quy mã nguồn. → Bước 4 và "Cách đã kiểm chứng".

---

## Bước 1 — Đối chiếu yêu cầu để tìm ra việc phải làm

**Nguyên tắc.** Không thiết kế từ đầu cho hoàn hảo. Dựng một bản chạy được, đưa
yêu cầu của người dùng ra đối chiếu từng câu, và **mỗi câu chưa đạt trở thành
một module**.

**Việc làm cụ thể.** Lúc bắt đầu đã có sẵn scaffold từ phiên trước: 11 tool điều
khiển Cast chung chung, **chưa có đọc chữ thành tiếng**. Người dùng không viết
đặc tả — họ gõ ba câu đánh số. Đối chiếu ra **đạt 1/3**:

| Yêu cầu | Trạng thái | Module sinh ra |
|---|---|---|
| 1. Dò loa trong LAN rồi lưu lại | một nửa (dò được, chưa lưu, chưa lọc loa) | `speaker_store.py` |
| 2. Text → tiếng Việt → phát ra loa | **chưa có gì** | `tts.py`, `media_server.py` |
| 3. Không chọn loa thì hỏi lại | **chưa có gì** | `say()` + `_select_targets()` |

`cast_manager.py` giữ nguyên — nó đã đúng việc.

**"Bản chạy được" tối thiểu là gì.** Không phải bản có tính năng. Là bản **kết
nối được và liệt kê được thiết bị** — đủ để chứng minh bạn nói chuyện được với
phần cứng, và đủ để đối chiếu yêu cầu lên nó. Với sản phẩm này, bản đó đã có sẵn
từ phiên trước (11 tool điều khiển Cast). Nếu bạn bắt đầu từ số 0, hãy dựng đúng
chừng đó trước rồi mới sang bước đối chiếu.

**Prompt mẫu** *(tái dựng — dùng cho sản phẩm bất kỳ, đây là câu bạn gõ)*:

```
Đây là N yêu cầu người dùng viết, đánh số:
<dán nguyên văn, giữ nguyên lỗi gõ>

Đọc mã nguồn hiện có rồi trả về một bảng, KHÔNG sửa gì cả:
  yêu cầu | trạng thái (đủ / một nửa / chưa có) | bằng chứng trong mã | module phải viết

Với mỗi yêu cầu "một nửa", nói rõ NỬA NÀO đang thiếu.
Cuối cùng: phần nào của mã hiện có đã đúng việc và KHÔNG nên đụng vào?
```

**Prompt gốc của người dùng** (nguyên văn, giữ nguyên lỗi gõ) — thứ đã sinh ra
toàn bộ sản phẩm:

```
hãy kiểm tra xem mcp này đúng yêu cầu không:
1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả
```

**Quyết định chốt.** Câu prompt này sinh ra toàn bộ sản phẩm, và nó có hai đặc
điểm đáng học: **yêu cầu được ĐÁNH SỐ**, và **diễn đạt bằng HÀNH VI quan sát
được** ("phát lên speaker", "sẽ hỏi user"). Đánh số cho phép đối chiếu từng
mục; diễn đạt bằng hành vi cho phép biến thẳng thành tiêu chí nghiệm thu. Một
câu như "làm cho nó hỗ trợ tiếng Việt tốt hơn" thì không làm được gì cả.

🔧 Ba yêu cầu này về sau thành bảng tiêu chí chấp nhận trong
`package/requirement.md` — gần như không phải viết lại.

---

## Bước 2 — Chọn công cụ: hai loại, hai cách chọn

**Nguyên tắc.** Cách chọn phụ thuộc vào **loại thành phần**, không phải một quy
trình so sánh chung áp lên tất cả.

| Loại thành phần | Cách chọn | Ai quyết |
|---|---|---|
| Người dùng **cảm nhận được** (giọng đọc, giao diện) | bày ra vài phương án, bắt họ **nghe/nhìn thật** | người dùng |
| **Xương sống** (thư viện giao thức, runtime) | chọn theo mức bảo trì + độ phủ giao thức | kỹ thuật |

**Việc làm cụ thể — thành phần cảm nhận được (giọng đọc).** Bày 4 phương án với
tiêu chí kỹ thuật tự chấm sẵn, để **một tiêu chí duy nhất cho người dùng**: nghe
có tự nhiên không.

| Phương án | Kỹ thuật | Kết luận |
|---|---|---|
| gTTS | miễn phí, không key | giọng máy móc |
| Google Cloud TTS | chất lượng cao | cần API key + trả phí |
| Piper | chạy offline | tiếng Việt yếu, setup nặng |
| **edge-tts** | miễn phí, không key | **tự nhiên nhất — người dùng chọn** |

**Việc làm cụ thể — thành phần xương sống (pychromecast).** **Không qua so sánh
nào.** Nó là thư viện Python duy nhất còn được bảo trì cho giao thức Cast. Bày
ra một bảng so sánh giả vờ ở đây là lãng phí thời gian của cả hai bên.

**Prompt mẫu** *(tái dựng — bản gốc không giữ nguyên văn)*:

```
Tôi cần đọc chữ tiếng Việt thành tiếng, phát ra loa Google.
Hãy so sánh các thư viện TTS tiếng Việt theo: chất lượng giọng, chi phí,
có cần API key không, chạy offline được không.
Với tiêu chí "nghe có tự nhiên không" thì đừng tự chấm — hãy sinh cho tôi
một file mp3 mẫu cho mỗi phương án để tôi nghe rồi tự chọn.
```

**Quyết định chốt.** `edge-tts` (`vi-VN-HoaiMyNeural` nữ / `NamMinhNeural` nam).
Và một quyết định về **quy trình**: chỉ **MỘT vòng** so sánh, không lặp. Người
dùng đã nghe và chọn xong thì đóng lại, không quay về bàn tiếp.

---

## Bước 3 — Chỗ thiếu thông tin: hỏi lại, đừng mặc định

**Nguyên tắc.** Khi thiếu thông tin mà **đoán sai gây hậu quả vật lý**, hành
động đúng là **trả về câu hỏi**, không phải chọn một mặc định "hợp lý".

**Việc làm cụ thể.** Gọi `say` mà không nói loa nào thì:

- **không** phát ra tất cả (cả nhà nghe — hậu quả vật lý);
- **không** phát ra loa đầu tiên (tuỳ tiện);
- **không** dùng MCP elicitation để server tự hỏi;
- **có**: trả về `status="needs_speaker_selection"` + danh sách loa + một câu
  bảo LLM hỏi lại người dùng.

Và quan trọng: **đường này KHÔNG được gọi TTS.** Nếu vẫn tổng hợp giọng rồi mới
phát hiện thiếu loa thì đã tốn hạn ngạch cho một việc không ai yêu cầu.

**Prompt mẫu** *(tái dựng)*:

```
Khi tool được gọi mà thiếu tham số bắt buộc và việc đoán sai có hậu quả
không hoàn tác được, đừng chọn giá trị mặc định. Trả về một cấu trúc đủ để
LLM hỏi lại người dùng: trạng thái, danh sách lựa chọn, câu hướng dẫn.
Đường trả-về-câu-hỏi này không được gây bất kỳ tác dụng phụ nào.
```

**Quyết định chốt.** Trả dữ liệu cho LLM hỏi lại, thay vì elicitation. Đánh đổi
rõ ràng: kém "gọn" hơn về mặt giao thức, nhưng chạy được ở mọi client — mà mục
đích là dùng được, không phải đúng chuẩn.

> **CHƯA THỬ — đây là phán đoán, không phải kết quả đo.** Căn cứ "nhiều client
> chưa hỗ trợ elicitation" **không được kiểm bằng thực nghiệm** trong phiên này:
> không có client nào được thử với elicitation rồi thất bại. Ai kế thừa mà muốn
> đảo quyết định này thì hãy đo trước — bắt đầu bằng chính ba client đã dùng
> thật (Claude Code, Claude Desktop, llama-server webui).

🔧 Về sau đây là mục kiểm khó nhất của bộ eval, vì phải chứng minh **hai điều
không xảy ra**: không cast, và không gọi TTS. Chứng minh "không xảy ra" luôn cần
một thiết bị ghi lại lời gọi.

---

## Bước 4 — Đọc tín hiệu từ người dùng

**Nguyên tắc.** Các câu người dùng gõ ra không bằng giá trị nhau. Phải phân loại
được, vì mỗi loại đòi một hành động khác hẳn.

**Việc làm cụ thể.** Bốn loại tín hiệu gặp trong phiên này:

| Loại | Ví dụ | Hành động đúng |
|---|---|---|
| **Sinh ra sản phẩm** | ba yêu cầu đánh số | đối chiếu, biến thành module |
| **Chỉ dán lỗi vào** | `URL must start with 'https'`, `Failed to fetch (check CORS?)`, `protocal error` | chẩn đoán hoàn toàn thuộc về AI — người dùng không có gì thêm để cho |
| **LẶP LẠI y hệt** | `vẫn báo lổi` → `vẫn báo lổi:` | **đây là tín hiệu SAI HƯỚNG** |
| **Lạc đề nhưng gấp** | "tại sao nhập đúng mật khẩu vẫn báo sai" | ngắt việc đang làm |

**Về tín hiệu lặp lại.** Người dùng nói "vẫn báo lổi" hai lần liên tiếp với đúng
câu chữ cũ. Hành động đúng: **dừng sửa, đi kiểm bản sửa đã được NẠP chưa.** Tôi
đã bỏ lỡ một vòng vì cứ tiếp tục sửa mã nguồn.

Đây là thứ cần **NHẬN RA ở phía người đọc note này**, không phải câu để gõ lại
cho AI.

**Về câu lạc đề.** `kiểm tra xem tại sau gatewaya khi chạy sudo tôi nhập đúng
password những vẫn báo sai hoài` — hoàn toàn không liên quan tới loa, và là việc
**gấp nhất cả phiên**: hoá ra có `pam_exec` gọi một binary chạy dưới quyền root
đang thu mật khẩu. Nguyên tắc: câu lạc đề vẫn phải **đánh giá mức nghiêm trọng**
trước khi gạt sang bên.

**Về hai lần đo mâu thuẫn.** Người dùng nói `có workinig speaker xác minh luôn
tts -> HTTP -> cast chạy thật` (tốt), rồi sau đó `khi phát loa working display
chi nháy sáng rồi tắt không phát đầy đủ âm thanh` (hỏng) — **cùng một thiết bị**.
Chỉ nhờ giữ **lịch sử đo** mới phân định được: không phải hồi quy mã nguồn, mà
là thiết bị treo.

---

## Bước 5 — Chẩn đoán khi thông báo lỗi nói dối

**Nguyên tắc.** Với hệ thống nhiều tầng (client → proxy → server → thiết bị),
thông báo lỗi thường xuất phát từ tầng **không phải** tầng có lỗi. Trước khi
sửa, hãy hỏi *tầng nào thật sự đang từ chối?*

**Việc làm cụ thể — bốn ca đáng học nhất:**

**a) `421 Misdirected Request`.** Có vẻ như lỗi định tuyến. Thật ra SDK chỉ tin
`127.0.0.1`. Bẫy: bind `0.0.0.0` **không** giải quyết được — bind là "nghe ở
đâu", allowlist là "tin ai gọi tới". Hai chuyện khác nhau. Cách chữa là **nới**
allowlist, **không tắt** kiểm tra — tắt là mở đường cho bất kỳ trang web nào
người dùng mở tấn công server nội bộ.

**b) Client treo, KHÔNG có thông báo lỗi nào.** Loại tệ nhất, vì không có gì để
tra. Nguyên nhân: nginx buffer nguyên dòng SSE. Vá: `proxy_buffering off`.
Bài học: **triệu chứng "im lặng" trỏ về tầng trung gian**, không trỏ về hai đầu.

**c) `Failed to fetch (check CORS?)`.** Trình duyệt cố tình không cho JavaScript
biết vì sao — nên chuỗi lỗi rỗng đó **là thông tin**: nó nói "trình duyệt chặn",
chứ không nói "server hỏng". SDK trả `OPTIONS`=405 không kèm header CORS. Vá
bằng `CORSMiddleware`, và **bắt buộc** `expose_headers=["Mcp-Session-Id"]` —
thiếu dòng này thì preflight qua nhưng không duy trì được phiên.

**d) Ngõ cụt tuyệt đối.** Người dùng tạo tên miền `google_cast.adrec.cloud`. Dấu
gạch dưới **không bao giờ** xin được chứng chỉ (CA/B Forum cấm), mà Claude
Desktop lại bắt buộc https. Không có đường vòng nào cả.

Bài học: **phân biệt "khó" với "không tồn tại đường đi".** Với ngõ cụt tuyệt
đối, việc đúng là báo ngay để người dùng đổi ràng buộc (tạo tên miền dùng gạch
nối), không phải thử tiếp.

**Prompt mẫu** *(tái dựng)*:

```
Lỗi này xuất hiện ở tầng nào? Liệt kê từng tầng mà request đi qua
(trình duyệt → nginx → uvicorn → SDK → thiết bị), và với mỗi tầng nói:
tầng này CÓ THỂ sinh ra đúng thông báo này không, và nếu có thì cách
xác nhận rẻ nhất là gì. Đừng sửa gì trước khi trả lời xong.
```

**Quyết định chốt.** Giữ nguyên bảo vệ DNS-rebinding của SDK, chỉ nới allowlist
— và allowlist phải đủ **bốn dạng**: host trần, `host:*`, scheme `http`, scheme
`https`. Thiếu một dạng là hỏng ở đúng một tình huống, mà thông báo lỗi không
hề nói cho bạn biết thiếu dạng nào.

---

## Bước 6 — Cái bẫy mà API không phát hiện được

**Nguyên tắc.** Với sản phẩm có tác dụng phụ vật lý, **"API trả về thành công"
không phải bằng chứng đúng.** Phải hỏi: có trạng thái sai nào mà mọi chỉ báo
đều xanh không?

**Việc làm cụ thể.** `target="all"` gửi tới cả **nhóm loa** lẫn **từng thành
viên**. Nhóm Cast phát *thông qua* thành viên, nên một loa vật lý nhận **hai
luồng cùng lúc** — nghe như tiếng vọng chồng lên nhau.

`Family speaker group` và `Kitchen speaker` cùng địa chỉ `192.168.1.22` — dấu
vết duy nhất nhìn thấy được. **Cả bốn đích đều trả `playing` — trạng thái API trả về KHÔNG phân biệt
được ca này với ca đúng.** Thứ duy nhất nghe ra là tai người.

Nói cho chính xác: có **một** dấu vết máy đọc được, và nó chính là chỗ bấu víu
để vá — hai đích **cùng địa chỉ `host`**. Nhưng nó nằm ở *siêu dữ liệu thiết
bị*, không nằm ở *kết quả thao tác*. Bài học đúng là: **khi kết quả trả về không
phân biệt được đúng với sai, hãy đi tìm dấu vết ở tầng dữ liệu khác** — đừng
dừng ở "không kiểm được".

Vá (`fcf4035`): `all` loại các đích có `cast_type == "group"`; nhóm vẫn cast
được khi gọi đích danh.

**Quyết định chốt.** Quy tắc chung rút ra: **khi hai đích trỏ tới cùng một tài
nguyên vật lý, "gửi tới tất cả" phải chọn MỘT tầng, không phải cả hai.** Áp
được sang: nhóm thiết bị IoT, danh sách gửi mail có nhóm lồng nhau, phát tin
theo topic có topic cha.

🔧 Về sau đây thành lỗi gieo vào số 1 của `reverse-check.py` — vì nó là lỗi đắt
nhất đã từng lọt.

---

## Bước 7 — Viết bộ kiểm mà người ta dám chạy

**Nguyên tắc.** Với sản phẩm có tác dụng phụ vật lý: **tầng mặc định phải không
gây tác dụng phụ**, tầng thật là cờ opt-in. Bộ kiểm không ai dám bấm chạy thì
bằng không có.

**Việc làm cụ thể.** Ba tầng: mặc định (offline, 138 mục) → `--online` (gọi TTS
thật, 157 mục) → `--hardware` (phát tiếng thật, phải xin phép).

Bốn luật, mỗi luật rút từ một lỗi đã dính thật:

**Luật 1 — So TẬP KỲ VỌNG tường minh, không so kích thước.** Dạng test giả phổ
biến nhất là so đếm thay cho so tập. Ca thật: `len(hosts) == len(set(hosts))` để
kiểm "`all` không phát chồng". Nó **vẫn xanh** khi `all` sai thành đúng một phần
tử — một phần tử thì không thể trùng. Tự soát: mọi `len()`, `count`, `>=` phải
trả lời được *"có hình dạng SAI nào khiến con số này vẫn đúng không?"*.

**Luật 2 — Bài kiểm phải từng ĐỎ, với kỳ vọng khai TRƯỚC.** Gieo lỗi vào mã
nguồn, nhưng **viết ra danh sách mục lẽ-ra-phải-đỏ TRƯỚC khi chạy**. Thứ tự là
tất cả: nhìn kết quả rồi mới "kỳ vọng" là tự lừa mình. Mục lẽ-ra-đỏ-mà-xanh =
**test giả**, phải sửa hoặc ghi **CHƯA PHỦ** — chú thích suông không phải một
lựa chọn.

**Luật 3 — Hoàn nguyên = chạy lại thấy XANH, không phải `git status` sạch.** Đã
dính: một lỗi gieo vào **dài đúng bằng bản gốc**, khôi phục xong git sạch trơn,
nhưng `.pyc` cũ còn đó và eval vẫn đỏ. Suýt kết luận "sản phẩm hỏng". Quy trình
đúng: khôi phục → **xoá `__pycache__`** → chạy lại → đòi thấy xanh.

**Luật 4 — Khẳng định bất đồng bộ phải có MỐC CHỜ.** Đã dính: đọc `player_state`
ngay khoảnh khắc `play_media` trả về. Hàm đó chỉ chờ **ứng dụng khởi động**,
chưa chờ **phát** → FAIL `Kitchen speaker reports IDLE` dù loa hoàn toàn tốt.
Không có mốc chờ nghĩa là đang đo tốc độ mạng, không đo hành vi.

**Vệ sinh mock.** Ảnh chụp lấy **trước tầng đầu**, khôi phục trong `finally`,
tầng sau dựng object **MỚI**. **`importlib.reload` KHÔNG phải bản sạch** — nó
nạp module mới dưới chân chính cái ảnh chụp đang giữ tay nắm, phá luôn đường
khôi phục. Đã thử và phải loại.

**Prompt mẫu** *(tái dựng, dùng được cho sản phẩm khác)*:

```
Viết bộ kiểm cho sản phẩm này, phân tầng theo tác dụng phụ: tầng mặc định
không được gây tác dụng phụ nào; tầng chạm thật là cờ opt-in.

Ràng buộc bắt buộc:
- Mọi khẳng định so TẬP KỲ VỌNG tường minh. Cấm so kích thước/đếm thay cho
  so tập.
- Mọi khẳng định chạm mạng hoặc thiết bị phải có mốc chờ (timeout + điều
  kiện thoả), không được đọc trạng thái ngay khi lời gọi trả về.
- Mock: chụp ảnh trước tầng đầu tiên, khôi phục trong finally, mỗi mục kiểm
  dựng object mới. Không dùng importlib.reload.

Rồi viết một script kiểm ngược: KHAI TRƯỚC danh sách mục lẽ-ra-phải-đỏ cho
mỗi lỗi gieo vào, chạy, so kỳ vọng với thực tế, và cuối cùng xác minh hoàn
nguyên bằng cách xoá bytecode rồi CHẠY LẠI bộ kiểm để thấy xanh.
```

**Quyết định chốt.** Kiểm ngược không phải nghi thức — nó tìm ra **ba thứ thật**
trong chính bộ kiểm vừa viết:

1. Một test giả không bao giờ đỏ được, mà nguyên nhân sâu hơn vẻ ngoài: khi hình
   dạng trả về đổi, một mục kiểm phía trên **ném lỗi**, bộ kiểm **sập giữa
   chừng**, và mọi mục phía sau **không bao giờ chạy** — trông như "ít đỏ hơn"
   thực tế. Bài học riêng: **một cú sập giữa chừng làm bộ kiểm nói dối theo
   hướng lạc quan.**
2. Một **kỳ vọng sai** (không phải test giả) — bài kiểm vẫn thật, kỳ vọng mới là
   thứ sai → sửa kỳ vọng, **không nới bài kiểm**. Phân biệt hai ca này là quan
   trọng: nới bài kiểm cho khớp kỳ vọng sai chính là cách sinh ra test giả.
3. Một mục kiểm chỉ đang **kiểm Python**: nó viết lại biểu thức kẹp âm lượng
   ngay trong bài kiểm thay vì gọi vào sản phẩm.

Và nó tìm ra **hai khiếm khuyết thật trong sản phẩm** (`tts.py` không thử lại
khi dịch vụ trả rỗng; file 0 byte đọng lại khi hỏng) — đã ghi vào
`package/technical-docs.md` mục 6, **chưa vá**.

---

## Bước 8 — Đóng gói: cửa vào phải là đường người lạ đi được

**Nguyên tắc.** Định nghĩa "đã đóng gói xong" là: **người lạ, máy sạch, chỉ đọc
README, đưa được sản phẩm vào trạng thái dùng được.** Không qua phép thử đó thì
chưa có package, dù bộ kiểm xanh rờn.

**Việc làm cụ thể.** Bước 0 của README phải là **đường lấy mã mà người lạ đi
được**: repo có remote, hoặc một artefact phát hành có đóng dấu. Đường dẫn local
trên máy người đóng gói **không tính** — nó chỉ tồn tại với đúng một người.

Repo này riêng tư, nên README phải ghi thêm **xin quyền từ AI, qua KÊNH NÀO**
(chủ repo `devAdrec`, qua GitHub issue hoặc nhắn trực tiếp). Không có mục đó thì
người đọc gặp `Repository not found` và tưởng mình gõ sai.

Và bằng chứng phải là **hành động, không phải đọc thấy ổn**: clone thật vào thư
mục sạch, chạy lại **từng lệnh trong README**, dán output ra.

**Prompt mẫu** *(tái dựng — giao thẳng cho AI để nó tự chứng minh)*:

```
Hãy CHỨNG MINH tài liệu cài đặt này dùng được, bằng hành động chứ không
bằng đọc:
1. Clone repo từ remote vào một thư mục tạm HOÀN TOÀN mới. Không được dùng
   đường dẫn tới bản làm việc trên máy này.
2. Chạy lại TỪNG lệnh trong tài liệu, theo đúng thứ tự, không thêm bước nào
   mà tài liệu không ghi.
3. Dán output thật của từng lệnh.
4. Lệnh nào hỏng, hoặc bước nào bạn phải tự suy ra mới đi tiếp được, thì đó
   là một lỗ hổng của tài liệu — liệt kê ra.
Đọc thấy hợp lý KHÔNG được tính là bằng chứng.
```

**Quyết định chốt.** Bốn tài liệu bàn giao viết **mỏng và TRỎ về nguồn**, không
chép lại. `README.md` và `docs/architecture.md` ở gốc repo là tài liệu **đang
sống** — chép nội dung của chúng sang `package/` là tự tạo ra hai bản sự thật sẽ
lệch pha trong vài tuần. Mỗi tài liệu giữ đúng một mục đích riêng:

| Tài liệu | Mục đích riêng |
|---|---|
| `README.md` | từ số 0 tới **gọi được tool** — file duy nhất phải qua phép thử người-lạ |
| `requirement.md` | yêu cầu gốc **nguyên văn** + tiêu chí chấp nhận |
| `technical-docs.md` | trỏ sang `docs/architecture.md`, bổ sung **ràng buộc triển khai + điểm còn hở** |
| `user-manual.md` | dùng hằng ngày, các dạng chỉ định loa, lỗi thường gặp |

---

## Cách đã kiểm chứng

Chỗ chưa thử ghi rõ **CHƯA THỬ** — đừng để trống.

| Kịch bản | Số lần | Biên / điều kiện xấu | Kết quả |
|---|---|---|---|
| `say` → Kitchen speaker | CHƯA ĐẾM chính xác (≥6 lần, rải nhiều ngày) | bình thường | `playing`; **người dùng xác nhận NGHE ĐƯỢC** |
| `say` → Working display (Nest Hub) | **5 lần rải 2 ngày** | thiết bị treo rồi khởi động lại | 3 lần đầu THẤT BẠI (`wait timed out`, 8009 refuse); sau restart: 1 OK + 3 clip đo |
| Đo thời lượng phát | **3 clip** (2.09 / 4.27 / 7.10s) | độ dài khác nhau, ngắn nhất ~2s | cả 3 `PLAYING` đủ `duration` → `idle_reason=FINISHED` |
| Thương lượng `protocolVersion` | **3 phiên bản** | client cũ và mới | cả 3 trả đúng version |
| MCP client thật qua https (nginx + TLS) | 1 | CHƯA THỬ ở điều kiện xấu (cert hết hạn, proxy chết) | initialize + 13 tool + `list_speakers` → 4 loa |
| Client trình duyệt (Origin `http://192.168.1.99:8383`) | 1 | có CORS | preflight 200, allow-origin đúng, 13 tool |
| `--json-response --stateless` | 1 | client khắt khe về framing | `tools/call` không cần session id |
| Dò thiết bị + lọc loa | CHƯA ĐẾM (≥10 lần, mỗi lần khởi động service) | mạng thật 8 thiết bị | 4 loa / 4 thiết bị hình ảnh |
| `target="all"` | **2 lần: TRƯỚC và SAU khi sửa** | 4 loa song song | trước: 4 `playing` nhưng **chồng luồng**; sau: 3 loa đơn |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 1 | phần tử hỏng | loa thật `playing`, phần tử hỏng `error` riêng, tổng thể `ok` |
| **DoD clone từ remote** | 2 (phiên trước + phiên này) | thư mục tạm sạch | clone → `uv sync` → 13 tool qua **cả stdio và HTTP** → `tools/call list_speakers` trả tên loa thật |
| **Eval offline** | 5 phiên đóng gói, ≥20 lượt chạy | không tiếng | 35 → 43 → 62 → 67 → **138/138** |
| **Eval `--online`** | 3 lượt phiên này + các phiên trước | cần internet; đã gặp dịch vụ trả rỗng | 72 → 79 → **157/157** |
| **Eval `--hardware`** | 4 (xin phép mỗi lần) | cast thật | 37/37 → 48/48 → FAIL 62/63 rồi 67/67 (rò mock) → FAIL 90/91 rồi **91/91** (thiếu mốc chờ) |
| **Kiểm ngược bộ eval** | 3 vòng phiên này | 12 lỗi gieo + 1 đối chứng | vòng 1: 2 test giả; vòng 2: sửa xong, 0 test giả; hoàn nguyên XANH |
| edge-tts dưới yêu cầu dồn dập | 3 liên tiếp, rồi 6 lần giãn 4s | không giãn cách | **hỏng ~2/3 khi dồn; 6/6 khi giãn** → phát hiện sản phẩm thiếu thử lại |

**Biên / điều kiện xấu đã quan sát thật:** TCP 8009 refuse → timeout; mDNS sót
thiết bị đã lưu → `DeviceNotFoundError` tự mâu thuẫn; Origin ngoài allowlist →
403; Host không tin → 421; mở `/mcp` bằng trình duyệt → 406 (đúng đặc tả);
preflight chưa bật CORS → 405; bỏ `target` → `needs_speaker_selection`, không
phát gì; cài lại service khi đang chạy → tiến trình **KHÔNG đổi**; `all` gồm cả
nhóm lẫn thành viên → chồng luồng mà API vẫn báo `playing`; **bốn loại lỗi trong
chính bộ eval: rò mock ×2, test giả so-kích-thước, khẳng định thiếu mốc chờ, và
sập-giữa-chừng khiến bộ kiểm nói dối theo hướng lạc quan**.

### CHƯA THỬ

- Giọng nam `vi-VN-NamMinhNeural` **bằng tai**.
- Tham số `rate` **bằng tai** (mới chỉ so kích thước file).
- Service sống sót qua **reboot máy** (đã `enable`, chưa reboot lần nào).
- Địa chỉ đã lưu bị cũ vì loa **đổi IP** → nhánh quét lại.
- Chặn IP ở nginx (đã đồng ý bật, hai dòng **vẫn đang comment**).
- Tầng `--hardware` **trong phiên đóng gói này** — chưa xin phép người quanh đó.

---

## Ngõ cụt đã đi qua (đừng đi lại)

| # | Ngõ cụt | Cách thoát |
|---|---|---|
| 1 | `421 Misdirected Request`; bind `0.0.0.0` **không** đủ | nới allowlist đủ **4 dạng** (`__main__.py:46-69`) |
| 2 | nginx buffering làm client treo, **không báo lỗi gì** | `proxy_buffering off` + `proxy_read_timeout 3600s` |
| 3 | Tên miền có `_` **không bao giờ** xin được chứng chỉ | đổi sang gạch nối — ngõ cụt tuyệt đối, báo ngay |
| 4 | Claude Desktop connector chỉ nhận https | bắc cầu `mcp-remote … --allow-http` |
| 5 | `Failed to fetch (check CORS?)`, JS chỉ thấy lỗi rỗng | `CORSMiddleware` + **bắt buộc** `expose_headers=["Mcp-Session-Id"]` |
| 6 | `systemctl enable --now` **KHÔNG** restart service đang chạy → bản sửa sống 3 ngày vô tác dụng | `restart` tường minh + `status` in `/proc/<MainPID>/cmdline` |
| 7 | Thiết bị Cast treo: mDNS + ping OK nhưng TCP 8009 refuse | `nc -z <ip> 8009` **TRƯỚC** khi nghi mã nguồn; restart thiết bị |
| 8 | mDNS sót thiết bị đã lưu → `DeviceNotFoundError` tự mâu thuẫn | `_connect_saved()` kết nối thẳng theo địa chỉ đã lưu |
| 9 | `pkill -f "<mẫu>"` khớp luôn shell đang chạy → tự giết mình (exit 144) | lọc theo cổng hoặc PID |
| 10 | `target="all"` chồng luồng lên nhóm loa — **API không phát hiện được** | `all` bỏ `cast_type=group` (`fcf4035`) |
| 11 | `importlib.reload` để "làm sạch mock" | không sạch — phá tay nắm của chính canh gác; dùng ảnh chụp + `finally` |
| 12 | Gieo lỗi dài bằng bản gốc → `.pyc` cũ, git sạch mà eval đỏ | Bước 7, luật 3 |
| 13 | Bộ kiểm sập giữa chừng vì `KeyError` → giấu hết mục phía sau | Bước 7, phần "quyết định chốt" |

**Bài học suy luận** (từ #7): đã từng kết luận sai *"Nest Hub bỏ cổng 8009 do
firmware"* chỉ vì **cả hai** Nest Hub cùng đóng cổng — trong khi thật ra chỉ là
hai thiết bị cùng treo. **Hai mẫu trùng nhau không đủ để suy ra nguyên nhân hệ
thống.** Đây là chỗ duy nhất bài học này được giải thích.

---

## Thực thi ở đâu

| Muốn | Đọc |
|---|---|
| Cài và chạy | `package/README.md` |
| Yêu cầu gốc + tiêu chí chấp nhận | `package/requirement.md` |
| Ràng buộc triển khai + **điểm còn hở** | `package/technical-docs.md` |
| Dùng hằng ngày | `package/user-manual.md` |
| Thiết kế bộ kiểm | `package/harness-spec.md` |
| Chạy kiểm chứng + kiểm ngược | `package/eval/README.md` |
| Dựng lại đúng sản phẩm này từ đầu | `reproduction-prompt.md` |
| Kiến trúc (tài liệu **sống**) | `docs/architecture.md` ở gốc repo |
