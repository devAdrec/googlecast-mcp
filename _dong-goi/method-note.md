---
product: googlecast-mcp
loai: harness vận hành (MCP server chạy như systemd service)
ngay_dong_goi: 2026-08-19
transmission_level: L2
cham_boi: method-note-evaluator-solo (context sạch, 2026-08-19)
package: _dong-goi/package/
---

# Cách xây một MCP server điều khiển thiết bị vật lý

Sản phẩm cụ thể: một MCP server để nói tiếng Việt ra loa Google trong nhà.
Nhưng phần đáng giữ lại không phải Google Cast — mà là **cách làm việc khi kết quả
cuối cùng chương trình không tự kiểm được**, ở đây là âm thanh.

**Cần thực thi:** `_dong-goi/package/` — trong đó `harness-spec.md` là thứ chuyển giao
mạnh nhất (mô hình 5 lớp Context / Tool / Execution / Eval / Feedback, kèm bảng "tín
hiệu nào máy đọc được, tín hiệu nào chỉ tai người đọc được").
**Cần cài đặt:** `package/README.md`. **Cần dựng lại đúng product này:**
`reproduction-prompt.md`.

---

## Bài học 30 giây

1. **Yêu cầu tốt là yêu cầu đánh số, mô tả hành vi, đối chiếu được từng dòng.** Ba câu
   đánh số của người dùng sinh ra toàn bộ product này, và cho phép chấm thẳng "hiện
   đạt 1/3". Một trang mô tả trôi chảy không làm được điều đó.
2. **Tiêu chí cảm nhận thì không được tự chấm.** "Giọng nghe có tự nhiên không" phải
   để người dùng nghe rồi chọn. Việc của AI là thu hẹp còn vài phương án và bày rõ
   đánh đổi.
3. **Tính năng có tác dụng phụ vật lý thì mặc định phải là KHÔNG LÀM GÌ.** Thiếu tham
   số thì hỏi lại, đừng đoán. Âm thanh đã phát ra không có nút hoàn tác.
4. **Trạng thái "thành công" mà hệ thống tự báo không phải bằng chứng.** Ở đây mọi loa
   báo `playing` trong khi âm thanh chồng lên nhau. Phải biết trước tín hiệu nào là mù.
5. **Người dùng lặp lại "vẫn lỗi" là tín hiệu SAI HƯỚNG, không phải lời mời sửa tiếp.**
   Dừng sửa. Đi kiểm tra bản sửa đã được nạp chưa.
6. **Hai mẫu trùng nhau không phải một quy luật.** Hai thiết bị cùng hỏng một kiểu
   không đủ để kết luận nguyên nhân hệ thống.
7. **Kiểm mạng trước khi đọc mã.** Trong sản phẩm nối tới thiết bị thật, phần lớn "bug"
   nằm ở đường truyền chứ không ở logic.

---

## 1. Đọc yêu cầu: giữ nguyên văn, đừng diễn giải

**Nguyên tắc.** Yêu cầu do người dùng viết ra là một tài sản. Diễn giải lại cho "gọn"
là làm mất thông tin, và mất luôn khả năng đối chiếu.

**Việc làm cụ thể.** Chép nguyên văn vào tài liệu yêu cầu, giữ cả lỗi gõ. Với mỗi dòng,
viết một tiêu chí chấp nhận **quan sát được**. Rồi chấm bản hiện có, nói thẳng con số.

**Prompt thật (nguyên văn của người dùng — chính tin nhắn này sinh ra cả product):**

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

Ba đặc điểm làm nên sức mạnh của nó: **đánh số** (đếm được), **mô tả hành vi** chứ
không mô tả kỹ thuật (không khoá trước giải pháp), **đối chiếu được** từng dòng. Lần
chấm đầu ra 1/3 — và con số đó chỉ tồn tại được nhờ yêu cầu viết theo kiểu này.

**Quyết định chốt.** Chép nguyên văn vào `package/requirement.md`, mỗi yêu cầu một mục
kèm tiêu chí chấp nhận và cách kiểm. Sau này mỗi khi eval thêm một mục, nó được gắn
ngược về yêu cầu tương ứng.

---

## 2. Chọn công nghệ: tách loại cảm nhận ra khỏi loại xương sống

**Nguyên tắc.** Chia tiêu chí làm hai loại. Loại **đối chiếu được** (cần API key không,
chạy offline được không, tốn tiền không, cài nặng không) thì AI tự chấm. Loại **cảm
nhận** (nghe có tự nhiên không) thì bắt buộc người dùng trải nghiệm rồi tự chọn. Chọn
hộ ở loại thứ hai là một dạng bịa: bạn đang khẳng định một điều bạn không kiểm chứng
được.

**Việc làm cụ thể.** Thu hẹp còn 3–4 phương án, làm bảng đánh đổi cho phần đối chiếu
được, rồi tạo mẫu thật cho người dùng nghe.

**Prompt mẫu (tái dựng — cấu trúc đã dùng, không phải nguyên văn):**

> Cần TTS tiếng Việt cho MCP server này. So sánh gTTS, Google Cloud TTS, Piper,
> edge-tts theo: chất lượng giọng, cần API key không, chi phí, offline được không,
> độ nặng khi cài. Làm bảng cho các tiêu chí đối chiếu được. Riêng chất lượng giọng
> thì đừng tự kết luận — dựng mẫu mỗi loại đọc cùng một câu tiếng Việt để tôi nghe.

**Quyết định chốt.** edge-tts (`vi-VN-HoaiMyNeural` nữ mặc định, `NamMinhNeural` nam) —
**người dùng chọn sau khi nghe**. Lý do các phương án kia bị loại: gTTS giọng máy móc,
Google Cloud TTS cần key và có phí, Piper chạy offline được nhưng giọng yếu và setup
nặng. Đánh đổi đã chấp nhận một cách có ý thức: edge-tts **cần internet**, nên tính
năng nói sẽ chết khi mất mạng.

**Dừng vòng lấy ý kiến khi nào?** Ở product này chỉ có **MỘT vòng**: người dùng xem
bảng so sánh, nghe, chọn edge-tts ngay, không lặp lại. Nói rõ vậy để không ai tưởng
đây là một quy trình lặp nhiều vòng — nó không phải. Vòng thứ hai chỉ cần khi người
dùng chọn xong rồi mà vẫn lăn tăn, hoặc khi không phương án nào đạt.

**Thành phần xương sống thì chọn bằng tiêu chí khác.** pychromecast **không qua so sánh
nào cả** — nó là thư viện Python duy nhất còn được bảo trì cho giao thức Cast. Ghi
đúng như vậy, vì đây là một loại quyết định khác với §2 ở trên:

| | Thành phần cảm nhận được (TTS) | Thành phần xương sống (client giao thức) |
|---|---|---|
| Chọn theo | người dùng trải nghiệm rồi chọn | mức độ được bảo trì + độ phủ giao thức |
| Ai quyết | người dùng | AI quyết được, nêu lý do |
| Đổi về sau | dễ — một hàm `synthesize` | rất đắt — thấm vào cả kiến trúc |

Nghịch lý đáng nhớ: thứ **dễ đổi** thì phải hỏi người dùng, thứ **khó đổi** thì thường
chỉ có một lựa chọn khả dĩ nên không có gì để hỏi. Việc cần làm với thành phần xương
sống không phải là so sánh, mà là **kiểm xem nó còn sống không** — commit gần nhất,
issue có người trả lời không, có theo kịp thay đổi giao thức không.

🔧 Cache mp3 theo `hash(text|voice|rate|volume)` — cùng một thông báo không tổng hợp
lại lần hai (`src/googlecast_mcp/tts.py`).

---

## 3. Thiết kế hành vi mặc định cho tool có tác dụng phụ vật lý

**Nguyên tắc.** Với tool mà hậu quả không hoàn tác được, **mặc định đúng là không làm
gì**. Thiếu thông tin thì hỏi lại. Sự tiện lợi của một giá trị mặc định không đáng đổi
lấy rủi ro làm ồn cả nhà vì một lệnh đoán sai.

**Việc làm cụ thể.** Thiếu `target` → dừng trước cả bước tổng hợp giọng, trả về một
đối tượng dữ liệu đủ để LLM tự hỏi lại người dùng:

```json
{"status": "needs_speaker_selection",
 "speakers": [...],
 "message": "No target given. Ask the user which speaker to play on, then call
             this tool again with target=<friendly_name>, ... Available: ..."}
```

Chi tiết dễ bỏ qua nhưng chính là điểm mấu chốt: **thông điệp lỗi được viết cho LLM
đọc, không phải cho người đọc.** Nó nói rõ phải hỏi gì, và phải gọi lại tool với tham
số nào. Trong một harness, thông điệp lỗi là một phần của giao diện.

**Prompt thật — người dùng viết, và đây là câu bạn muốn người dùng của mình viết:**

> nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

**Quyết định chốt.**
- Không dùng MCP elicitation — nhiều client chưa hỗ trợ; một tính năng hỏng câm ở đúng
  những client cần nó là tệ hơn không có.
- Không mặc định phát tất cả — tác dụng phụ vật lý, sai là ồn cả nhà.
- Trả dữ liệu cho LLM tự hỏi lại — chạy được trên mọi client.

---

## 4. Để ràng buộc của nền tảng dẫn dắt kiến trúc

**Nguyên tắc.** Trước khi thiết kế, tìm cho ra **ràng buộc cứng** của nền tảng. Một
ràng buộc cứng thường quyết định kiến trúc mạnh hơn mọi sở thích thiết kế cộng lại.

**Việc làm cụ thể.** Ràng buộc ở đây: **thiết bị Cast TỰ đi tải media qua HTTP, nó
không đọc được đường dẫn file trên máy bạn.** Hệ quả không né được: server "nói được"
**bắt buộc phải kiêm luôn một HTTP file server**. Đó là lý do có cổng thứ hai, và là
lý do phần lớn lỗi về sau là lỗi mạng chứ không phải lỗi logic.

**Prompt mẫu (tái dựng):**

> Trước khi viết code: pychromecast nhận media kiểu gì? Thiết bị tự tải hay mình đẩy
> byte sang? Nếu nó tự tải thì server phải phơi file ra ở đâu, và địa chỉ nào thiết bị
> gọi về được?

**Quyết định chốt.** `media_server.py` bind **`0.0.0.0`** (mọi interface); URL quảng
bá cho thiết bị dựng từ `lan_ip()`. **Hai thứ này khác nhau** — địa chỉ lắng nghe không
phải địa chỉ quảng bá. Bind rộng vì interface định tuyến ra internet chưa chắc là
interface loa dùng để gọi về.

Ràng buộc thứ hai, nhẹ hơn nhưng cùng loại: mDNS lossy và chậm → **lưu bền danh sách
thiết bị**, hợp nhất theo uuid chứ không ghi đè, để một lần quét sót không xoá mất
thiết bị đã biết.

---

## 5. Gỡ lỗi khi triệu chứng không trỏ về nguyên nhân

**Nguyên tắc.** Với hệ thống mạng nhiều tầng, **triệu chứng thường nằm cách nguyên
nhân vài tầng**, và tầng ở giữa hay nuốt mất thông tin. Đọc mã sớm quá là mất thời
gian. Đi từ ngoài vào: mạng → cấu hình → tiến trình đang chạy → mã nguồn.

**Việc làm cụ thể.** Người dùng thường chỉ dán lỗi vào, không phân tích. Đó là chuyện
bình thường — chẩn đoán là việc của AI. Các lỗi họ dán, nguyên văn:

> URL must start with 'https'

> https://google-cast.adrec.cloud/mcp kết quả là {"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept text/event-stream"}}

> mcp này tôi chạy khi kết nối với mcp llama-server thì báo lổi: protocal error

> vẫn báo lổi khi kết nối với mcp llama-server   *(kèm ảnh log: `Failed to fetch (check CORS?)`)*

**Prompt gõ lại được — dán nguyên khối này cho AI khi client không gọi được server:**

> Client không kết nối được tới MCP server. Đừng đọc mã nguồn vội. Đi theo đúng thứ tự
> này, dừng lại ở bước đầu tiên cho kết quả bất thường và báo tôi:
> 1. `curl -i` thẳng vào endpoint từ chính máy chủ, bỏ qua mọi proxy. Nó sống không?
>    (406 vì thiếu `Accept: text/event-stream` là ĐÚNG đặc tả, không phải lỗi.)
> 2. Nếu bước 1 sạch mà qua proxy vẫn hỏng: proxy đang đổi gì? So header `Host` và
>    `Origin` mà server NHẬN được với allowlist server đang cấu hình — chú ý scheme
>    (proxy đổi http→https) và port (cổng 443 gửi Host không kèm `:port`).
> 3. Nếu cấu hình trông đúng: tiến trình ĐANG CHẠY có đúng tham số đó không? Đọc
>    `/proc/<MainPID>/cmdline`, đừng tin `systemctl status` báo `active (running)`.
> 4. Chỉ khi cả ba bước trên đều sạch mới bắt đầu đọc mã.

Thứ tự này không phải cho đẹp: mỗi bước loại bỏ một tầng, và ba tầng đầu là nơi chứa
gần hết lỗi. Bước 3 tồn tại vì thiếu nó đã mất 3 ngày.

**Sáu ngõ cụt và cách thoát** — phần này giữ nguyên chi tiết vì đây là thứ không suy
ra được, chỉ trả giá mới có:

| Triệu chứng | Nguyên nhân thật | Thoát bằng |
|---|---|---|
| `421 Misdirected Request` | SDK chỉ tin `127.0.0.1`; bind `0.0.0.0` KHÔNG đủ — bind là chuyện nghe, allowlist là chuyện tin | nới allowlist, **phải có scheme `https`** (proxy đổi scheme) **và host không kèm `:port`** (cổng 443 không gửi port) |
| Client treo, **không báo lỗi gì** | nginx buffering giữ lại dòng sự kiện | `proxy_buffering off` + `proxy_read_timeout 3600s` |
| Không xin được chứng chỉ, mãi mãi | hostname có dấu gạch dưới; CA/B Forum cấm `_` | đổi tên miền sang gạch nối — **không có cách vòng** |
| Claude Desktop chỉ nhận https | giới hạn của custom connector | reverse proxy, hoặc `npx -y mcp-remote http://... --allow-http` |
| `Failed to fetch (check CORS?)`, JS chỉ thấy lỗi trống | SDK trả `OPTIONS` = 405, không header CORS → trình duyệt chặn trước khi JS thấy gì | `CORSMiddleware`, **bắt buộc** `expose_headers=["Mcp-Session-Id"]` |
| Sửa xong mà "vẫn lỗi" suốt 3 ngày | `systemctl enable --now` KHÔNG restart service đang chạy; tiến trình cũ giữ mã + tham số CŨ | `restart` tường minh; `status` in `/proc/<MainPID>/cmdline` |

Hai chi tiết trong bảng trên đáng nhấn vì chúng thuộc loại "lỗi nấp sau lỗi":

- **CORS ở đây có hai lớp.** Qua được preflight vẫn chưa xong: trình duyệt không đọc
  được header không được expose, nên không giữ được session, nên không tiếp tục được.
  `expose_headers` là lớp thứ hai, và nó không tự lộ ra.
- **406 khi mở `/mcp` bằng trình duyệt là ĐÚNG ĐẶC TẢ**, không phải lỗi. Nhận nhầm nó
  là lỗi sẽ dẫn cả buổi đi sai hướng.

**Quyết định chốt về bảo mật:** giữ nguyên bảo vệ DNS-rebinding của SDK, **chỉ nới
allowlist**. Tắt nó là mở cho một trang web bất kỳ mà nạn nhân đang mở sai khiến server
trong mạng nội bộ của họ.

🔧 `__main__.py:37` (CORS), `:46-69` (allowlist); `scripts/nginx-googlecast-mcp.conf:37,42`;
`scripts/service.sh:78-80,112-115`.

---

## 6. Đọc tín hiệu từ người dùng

**Nguyên tắc.** Cách người dùng lặp lại là dữ liệu chẩn đoán, ngang hàng với log.

**Ba tín hiệu đã gặp, và ý nghĩa của chúng:**

- **Lặp lại "vẫn lỗi" hai lần liên tiếp** (#17 → #18) = **sai hướng**. Không phải lời
  mời sửa tiếp. Dừng sửa, kiểm tra bản sửa đã được NẠP chưa. Tín hiệu này đã bị bỏ lỡ
  một vòng — và đúng lúc đó, bản sửa đúng đã nằm sẵn trên đĩa trong khi tiến trình cũ
  chạy tiếp 3 ngày.
- **Hai báo cáo mâu thuẫn về CÙNG một thiết bị** (#4 "phát tốt" → #15 "nháy đèn rồi
  tắt, không phát đầy đủ"). Chỉ có **lịch sử đo** mới phân định được lỗi thiết bị với
  hồi quy mã nguồn. Không giữ kết quả đo cũ thì hai thứ đó nhìn giống hệt nhau.
- **Câu hỏi lạc đề nhưng gấp** (#11: sudo nhập đúng mật khẩu vẫn báo sai). Lạc chủ đề
  hoàn toàn, nhưng hoá ra là việc gấp nhất phiên: phát hiện `pam_exec` + một binary
  thu mật khẩu chạy quyền root. Đừng gạt câu lạc đề sang bên chỉ vì nó không thuộc
  phạm vi đang làm.

**TÍN HIỆU cần NHẬN RA (nguyên văn, hai tin nhắn liền nhau của người dùng).** Đây
KHÔNG phải câu để bạn gõ — đây là câu bạn phải nhận ra khi nghe thấy nó:

> vẫn báo lổi khi kết nối với mcp llama-server

> vẫn báo lổi:

**Prompt gõ lại được — dán cho AI ngay khi bạn nhận ra tín hiệu đó:**

> Tôi vừa nói "vẫn lỗi" lần thứ hai. Dừng sửa. Kiểm tra bản sửa đã được nạp vào tiến
> trình đang chạy chưa: đọc `/proc/<MainPID>/cmdline` và đối chiếu với tham số lẽ ra
> phải có. Nếu tiến trình đang chạy cấu hình cũ thì mọi phân tích từ nãy tới giờ đều
> đang nói về một phiên bản không tồn tại.

**Quyết định chốt.** Đưa kỷ luật này vào công cụ chứ không để trong đầu:
`service.sh status` in thẳng `/proc/<MainPID>/cmdline`, để câu hỏi "bản sửa đã nạp
chưa" trả lời được trong một giây thay vì ba ngày.

---

## 7. Kiểm chứng thứ mà chương trình không tự kiểm được

**Nguyên tắc.** Xác định trước **tín hiệu nào là mù**, rồi thiết kế cách bù. Ở đây
`status: playing` là tín hiệu mù: nó chỉ chứng minh lệnh đã được nhận, không chứng
minh âm thanh đúng.

**Bằng chứng cụ thể cho việc đó — lỗi tệ nhất của cả product:** `target="all"` gửi tới
cả nhóm loa lẫn từng thành viên của nhóm. Nhóm Cast phát QUA các thành viên, nên một
loa vật lý nhận hai luồng. **Cả bốn thiết bị đều trả `playing`.** Không một chỉ số nào
báo động. Đo được: `Family speaker group` và `Kitchen speaker` cùng ở `192.168.1.22`.
Chỉ nghe mới biết.

**Bài học chung, áp được ra ngoài Google Cast:** nền tảng nào có khái niệm "nhóm thiết
bị" thì danh sách "tất cả" **phải khử trùng lặp giữa nhóm và thành viên**.

**Việc làm cụ thể.** Sửa: `all` bỏ `cast_type=group`; nhóm vẫn gọi được bằng tên
(commit `fcf4035`). Rồi **chạy lại thật và nghe**: 3 loa riêng lẻ, không chồng.

**Prompt thật — người dùng viết (câu này gõ lại được, cho chính bạn hoặc cho AI):**

> có workinig speaker xác minh luôn tts -> HTTP -> cast chạy thật

**Quyết định chốt.** Eval chia hai tầng (`package/eval/`): tầng offline không phát
tiếng, chạy được ở mọi nơi, exit 0/1; tầng `--hardware` phát tiếng thật, **mặc định
tắt**. Lý do chia: một bộ test phát tiếng trong phòng ngủ lúc 2 giờ sáng là bộ test
không ai dám chạy, mà test không ai dám chạy thì bằng không có.

Và eval được **kiểm ngược**: đưa lỗi `all` cũ trở lại thì mục tương ứng FAIL đúng như
mong đợi. Một bộ eval chưa từng thấy màu đỏ là một bộ eval chưa biết có hoạt động không.

---

## Cách đã kiểm chứng

Ghi trung thực. Chỗ chưa thử ghi rõ **CHƯA THỬ**.

### Đã chạy thật

| Kịch bản | Số lần | Biên / điều kiện | Kết quả |
|---|---|---|---|
| `say` → Kitchen speaker (Home Mini) | 1 | bình thường | `playing`; người dùng xác nhận **nghe được** |
| `say` → Working display (Nest Hub) | **5 lần rải qua 2 ngày** | thiết bị treo rồi restart | 3 lần đầu THẤT BẠI (`wait timed out`, cổng 8009 refuse); sau restart: 1 OK + 3 clip đo |
| Đo thời lượng phát | **3 clip** (2.09 / 4.27 / 7.10 s) | độ dài khác nhau | cả 3 `PLAYING` đủ `duration` → `idle_reason=FINISHED`; log HTTP xác nhận thiết bị CÓ tải file (200) |
| Thương lượng protocolVersion | **3 phiên bản** | client cũ/mới | cả 3 trả đúng version |
| MCP client thật qua `https://google-cast.adrec.cloud/mcp` | 1 | qua nginx + TLS | initialize + 13 tool + `list_speakers` → 4 loa |
| MCP client thật qua `http://<LAN>:8765/mcp` | 1 | trực tiếp LAN | như trên |
| Mô phỏng client trình duyệt (Origin `http://192.168.1.99:8383`) | 1 | có CORS | preflight 200 + allow-origin đúng; initialize 200 JSON; 13 tool |
| `--json-response --stateless` | 1 | client khắt khe | `application/json`; `tools/list` + `tools/call` chạy không cần session id |
| Dò thiết bị + lọc loa | 2 | mạng thật 8 thiết bị | 4 loa / 4 thiết bị hình ảnh |
| `target="all"` | **2 (trước và sau khi sửa)** | 4 loa song song | trước: 4 `playing` nhưng **chồng luồng**; sau: **3 loa riêng lẻ, không chồng** |
| `target` nhiều loa cách phẩy | 1 | 2 loa | cả 2 `playing` |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 1 | phần tử hỏng | loa thật vẫn `playing`, phần tử hỏng trả `error` riêng, tổng thể `ok` — cô lập **đúng** |
| Nhóm loa gọi theo tên sau khi sửa `all` | 1 | — | `playing` — nhóm vẫn dùng được |
| **Eval offline** (`package/eval/`) | **2 lần trong phiên đóng gói** | không loa, không phát tiếng | **35/35 PASS, exit 0** |
| **Eval tầng `--hardware`** | 1 | cast thật ra loa trong nhà | **37/37 PASS, exit 0**; script tự in cảnh báo `'playing' KHÔNG chứng minh âm thanh đúng` |
| **Kiểm ngược eval** (đưa lỗi `all` cũ trở lại) | 1 | hồi quy giả | eval **FAIL đúng mục mong đợi** → eval không rỗng |

### Biên / điều kiện xấu đã quan sát (thật, không dựng giả)

- mDNS + ping OK nhưng TCP 8009 refuse → timeout 10 s.
- mDNS sót thiết bị đã lưu → `DeviceNotFoundError` **tự mâu thuẫn** (liệt kê chính
  thiết bị đó là "known"). Thông báo lỗi tự mâu thuẫn = dấu hiệu hai nguồn sự thật
  đang lệch nhau.
- Origin ngoài allowlist → 403 `Invalid Origin header`.
- Host không tin → 421.
- Mở `/mcp` bằng trình duyệt → 406 (**đúng đặc tả, không phải lỗi**).
- Preflight khi chưa bật CORS → 405, không header.
- Bỏ `target` → `needs_speaker_selection`, không phát gì.
- Cài lại service khi đang chạy → tiến trình **không đổi**.
- `all` gồm cả nhóm lẫn thành viên → chồng luồng **mà API vẫn báo `playing`**.
- `pkill -f "<pattern>"` khớp luôn dòng lệnh bash đang chạy → tự giết shell (exit 144).
  Lấy PID từ `ss -ltnp`.

### CHƯA THỬ

- Giọng nam `vi-VN-NamMinhNeural` — **CHƯA THỬ** (mọi lần đều giọng nữ mặc định).
- Tham số `rate` — **CHƯA THỬ**.
- Service sống sót qua reboot máy (đã `enable`, **chưa reboot lần nào**).
- Địa chỉ đã lưu bị cũ vì thiết bị đổi IP → nhánh quét lại — **CHƯA THỬ**.
- Chặn IP nginx (`allow 192.168.0.0/16; deny all;`) — người dùng đã đồng ý bật nhưng
  **chưa bật**, hai dòng vẫn comment.
- ~~Tầng `--hardware` của eval script — chưa chạy lần nào.~~ **Đã chạy** sau khi xin phép
  người dùng: **37/37 PASS, exit 0**, cast thật ra Kitchen speaker. Bản thân script in
  cảnh báo `'playing' KHÔNG chứng minh âm thanh đúng` — đúng tinh thần: máy chỉ xác nhận
  được tới lớp giao thức, phần còn lại vẫn phải nghe.

### Điểm còn hở — không tô hồng

- **Không xác thực ở tầng ứng dụng.** `google-cast.adrec.cloud` phân giải **công khai**
  ra internet → ai biết URL cũng phát được tiếng trong nhà.
- **Mặt phơi nhiễm thứ hai:** cổng audio 8766 bind `0.0.0.0`, không xác thực, phục vụ
  nguyên một thư mục file. **Chặn IP ở nginx chỉ che 8765, không chạm 8766.**
- Cache TTS tăng vô hạn, chưa dọn.
- Chưa khôi phục âm lượng / media đang phát sau khi thông báo xong.
- Trước phiên đóng gói này product **không có test nào**; eval offline vá được phần
  logic, **không vá được phần âm thanh**.

---

## Áp sang bài khác

Bài toán tương tự — "AI điều khiển thiết bị vật lý trong nhà" (đèn, máy lạnh, rèm,
chuông cửa) — thì bảy điểm sau chuyển thẳng được:

1. Bắt người dùng viết yêu cầu **đánh số + mô tả hành vi**, rồi chấm bản hiện có bằng
   con số.
2. Tiêu chí cảm nhận → **đưa mẫu cho người dùng chọn**, không chọn hộ.
3. Tool có tác dụng phụ không hoàn tác → **mặc định không làm gì**, thiếu tham số thì
   trả dữ liệu để LLM hỏi lại. Viết thông điệp lỗi **cho LLM đọc**.
4. Tìm **ràng buộc cứng của nền tảng** trước khi thiết kế; nó quyết định kiến trúc.
5. Có khái niệm "nhóm thiết bị" → danh sách "tất cả" phải **khử trùng lặp nhóm ↔ thành
   viên**.
6. Liệt kê trước **tín hiệu nào là mù**; đừng lấy trạng thái tự báo làm bằng chứng.
7. Eval chia hai tầng: **offline không tác dụng phụ** (chạy mọi lúc) + **hardware sau
   một cờ tường minh**. Và kiểm ngược bộ eval bằng một hồi quy giả.
