---
product: googlecast-mcp
loai: MCP server (package, harness vận hành)
ngay: 2026-08-27
transmission_level: L2
chấm bởi: người đọc sạch (context riêng), 2026-08-27
package: _dong-goi/package/
---

# Cách làm ra googlecast-mcp

Ghi lại **cách nghĩ**, không phải cách chạy. Muốn cài và dùng thì sang
`package/README.md` và `package/user-manual.md`; muốn biết mã làm gì thì sang
`package/technical-docs.md`, và từ đó sang `docs/architecture.md` ở gốc repo.
Ở đây chỉ có những quyết định mà người làm việc tương tự cần bắt chước.

**Về đường dẫn trong file này:** `package/...` là tương đối với `_dong-goi/`;
mọi đường dẫn khác (`docs/`, `scripts/`, `src/`, `plans/`) là tương đối với
**gốc repo**. Gói bàn giao nằm *bên trong* repo và không tách rời khỏi nó —
`package/README.md` bước 0 nói cách lấy repo về.

---

## Bài học 30 giây

1. **Yêu cầu viết bằng hành vi thì đối chiếu được từng câu.** Danh sách yêu cầu
   *chưa đạt* chính là danh sách việc phải làm — không cần bước lập kế hoạch
   nào khác.
2. **Không phải thành phần nào cũng cần so sánh.** Thứ người ta *cảm nhận
   được* thì phải so, và phải để người thật cảm nhận. Thứ *xương sống* thì
   chọn theo mức bảo trì rồi đi tiếp.
3. **Suy luận hợp lý vẫn có thể sai; chỉ con số mới cho biết.** Bản vá đầu
   tiên của tôi đúng về lý và sai về thực tế — cho tới khi đo được "4 trên 6".
4. **Người dùng nói "vẫn lỗi" lần thứ hai là một tín hiệu khác hẳn lần thứ
   nhất.** Nó thường có nghĩa bản sửa chưa được nạp, chứ không phải sửa chưa
   đủ sâu. Dừng sửa, đi kiểm cái đang chạy.
5. **Mô tả lỗi quá rộng làm người sau tìm sai chỗ.** Ghi đúng điều kiện thật
   đã đo được, không ghi ấn tượng ban đầu.
6. **Bài kiểm chưa từng đỏ là bài kiểm chưa chứng minh được gì.** Phải cố tình
   làm hỏng sản phẩm và bắt bài kiểm bắt được — kèm một đối chứng vô hại để
   biết nó không đỏ bừa.
7. **Hai mẫu trùng nhau không đủ để suy ra nguyên nhân hệ thống.**

---

## Bước 1 — Biến ba câu của người đặt hàng thành danh sách việc

**Nguyên tắc.** Yêu cầu diễn đạt bằng *hành vi quan sát được* thì đối chiếu
được thẳng với mã đang có. Không cần diễn giải lại, không cần workshop. Đối
chiếu xong, cái chưa đạt chính là cái phải viết.

**Việc làm cụ thể.** Product không bắt đầu từ số 0: một phiên trước đã để lại
scaffold 11 tool Cast chung chung, **chưa có TTS**. "Chạy được" lúc đó chỉ có
nghĩa là *kết nối được và liệt kê được thiết bị*. Tôi đọc file bàn giao, rồi
lấy ba câu yêu cầu soi vào scaffold đó, từng câu một.

Kết quả đối chiếu: **đạt 1/3**. Câu 1 đạt một nửa (dò được, nhưng cache trong
RAM, restart là mất). Câu 2 và câu 3 chưa có gì.

Từ đó ra thẳng danh sách module:

| Yêu cầu chưa đạt | Module phải viết |
|---|---|
| lưu lại danh sách loa | `speaker_store.py` |
| text → tiếng nói tiếng Việt | `tts.py` |
| audio đến được loa | `media_server.py` |
| hỏi khi chưa chọn loa | `say()` + `_select_targets()` trong `server.py` |

`cast_manager.py` giữ nguyên — nó đã làm đúng việc của nó. **Việc đáng kể nhất
của bước này là quyết định KHÔNG viết lại thứ đang đúng.**

Điểm xuất phát cụ thể nằm ở `plans/reports/handoff-260807-1157-googlecast-mcp-scaffold.md`
(gốc repo) — đó là file bàn giao mà prompt số 2 bảo đọc.

**Prompt thật** (nguyên văn, kể cả lỗi gõ — đây là prompt sinh ra toàn bộ
product):

```
hãy kiểm tra xem mcp này đúng yêu cầu không:
1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả
```

**Quyết định chốt.** Không lập kế hoạch riêng. Bảng đối chiếu chính là kế
hoạch. Ba câu này về sau còn được dùng lại làm khung cho `requirement.md` và
làm gốc cho từng mục của bài kiểm.

> 🔧 Chi tiết ai làm gì: `package/technical-docs.md`, mục "Đối chiếu mã ↔ yêu cầu".

### Việc riêng của yêu cầu số 3: hỏi lại thế nào khi thiếu tham số

Yêu cầu "chưa chọn thì hỏi" nghe như một câu điều kiện, nhưng cài đặt nó là
một quyết định thiết kế riêng, và nó lặp lại ở mọi product điều khiển đồ vật.

**Nguyên tắc.** Tool không hỏi được người dùng. Chỉ có LLM gọi tool mới hỏi
được. Nên tool phải trả về **nguyên liệu để LLM đi hỏi**, chứ không phải một
lỗi — và tuyệt đối không được tự chọn hộ.

**Việc làm cụ thể.** Thiếu loa đích thì `say()` trả về một object có
`status: "needs_speaker_selection"`, danh sách loa, và một `message` viết
thẳng cho LLM: *hãy hỏi người dùng chọn loa nào, rồi gọi lại tool này với
`target=<tên>`*. Không render TTS, không phát gì cả. Trường hợp mạng không có
loa nào là một status **khác** (`no_speakers_found`) vì nó cần cách xử lý khác.

Ba lựa chọn đã cân nhắc, và vì sao chọn cái thứ ba:

| Cách | Vì sao không / có |
|---|---|
| Mặc định phát tất cả | **không.** Tác dụng phụ vật lý, không hoàn tác được |
| MCP elicitation (giao thức tự hỏi) | **CHƯA THỬ** — chưa đo trên client nào. Đây là phán đoán, không phải kết luận |
| Trả dữ liệu cho LLM hỏi lại | **có.** Chạy trên mọi client, không phụ thuộc tính năng giao thức |

**Quyết định chốt.** Trạng thái do **LLM** giữ giữa hai lượt gọi, không phải
server. Server không nhớ "đang hỏi ai cái gì" — nhờ vậy nó vẫn không trạng
thái, và hai người dùng hỏi cùng lúc không giẫm lên nhau.

> 🔧 `_select_targets()` trong `src/googlecast_mcp/server.py`; tiêu chí đầy đủ ở
> `package/requirement.md` mục YC3.

---

## Bước 2 — Chọn thành phần: hai loại, hai cách chọn

**Nguyên tắc.** Thành phần mà **người ta cảm nhận được** thì bắt buộc so sánh,
và tiêu chí cảm nhận phải để người thật cảm nhận — máy không tự chấm được
"giọng này nghe có tự nhiên không". Thành phần **xương sống** thì chọn theo mức
bảo trì và độ phủ giao thức; bày ra bảng so sánh cho đủ lệ bộ không đổi được
kết luận khi thực tế chỉ có một lựa chọn còn sống.

**Việc làm cụ thể.**

*Giọng nói* — cảm nhận được. So bốn phương án: gTTS (giọng máy móc), Google
Cloud TTS (cần key, có phí), Piper (chạy offline nhưng yếu, cài đặt nặng),
edge-tts (tự nhiên nhất, miễn phí, không cần key). Tiêu chí kỹ thuật tôi tự
chấm; tiêu chí "nghe có ổn không" thì để người dùng nghe. **Một vòng, chốt,
không lặp lại.**

*Giao thức Cast* — xương sống. `pychromecast` là thư viện Python duy nhất còn
được bảo trì phủ giao thức này. **Không so sánh gì cả**, và đó là quyết định
đúng chứ không phải bước bị bỏ sót.

**Prompt thật: KHÔNG CÓ.** Bước này không sinh ra prompt nào — bảng so sánh do
tôi tự dựng rồi trình bày, người dùng chọn bằng cách nghe thử. Ghi ra để không
ai đi tìm một prompt không tồn tại. (Bước 4, 5, 7, 8 cũng vậy: chúng là công
việc chẩn đoán, không phải công việc hỏi-đáp.)

**Quyết định chốt.** edge-tts + pychromecast. Điều đáng mang đi không phải hai
cái tên đó, mà là **câu hỏi phân loại**: *thứ này người ta có cảm nhận trực
tiếp được không?* Trả lời xong mới biết có cần so sánh hay không.

---

## Bước 3 — Chạm thiết bị thật càng sớm càng tốt

**Nguyên tắc.** Với product điều khiển đồ vật, "chạy đúng" trong máy không có
nghĩa gì. Phải xác minh trên vật thật, sớm, và bằng giác quan.

**Việc làm cụ thể.** Ngay khi có đủ chuỗi TTS → HTTP → cast, chạy thật ra loa
thật và **nghe**. Không đợi làm xong mới thử.

Việc này lộ ra ngay ràng buộc kiến trúc quan trọng nhất của cả product: **thiết
bị Cast tự đi tải media qua HTTP**. Nó không phải cái loa để ghi byte vào. Suy
ra: server "nói được" bắt buộc kiêm luôn HTTP file server. Không có cách bỏ.

Hệ quả phải nhớ: **một lệnh cast "thành công" hoàn toàn có thể tương ứng với
sự im lặng.** Lệnh đã tới thiết bị, chỉ việc tải file mới hỏng. Bất kỳ ai đo
thành công bằng mã trả về của API đều sẽ bị lừa.

**Prompt thật:**

```
có workinig speaker xác minh luôn tts -> HTTP -> cast chạy thật
```

và câu chốt nghiệm thu:

```
đã nghe được rồi vậy xong chưa
```

**Quyết định chốt.** Tiêu chí chấp nhận của yêu cầu số 2 là **tai người**, ghi
thẳng vào `requirement.md` như vậy (mục 2.9), không giả vờ tự động hoá được.

---

## Bước 4 — Đo, rồi mới kết luận đã sửa xong

**Nguyên tắc.** Một bản vá hợp lý về mặt suy luận vẫn có thể không đủ. Chỉ con
số mới phân biệt được "đã đỡ" với "đã hết".

**Việc làm cụ thể.** Ba vòng, mỗi vòng một phép đo trên cùng một kịch bản: dồn
6 yêu cầu TTS song song.

| Vòng | Bản vá | Đo được |
|---|---|---|
| 1 | thêm 3 lần thử giãn cách | **4/6 đạt, 101 giây** |
| 2 | tuần tự hoá bằng khoá | **6/6, 12 giây** |
| 3 | một khoá cho mỗi vòng lặp | **6/6, 6.2 giây**, 0 file 0 byte |

Vòng 1 là chỗ đáng học. Thử lại là phản xạ đúng với lỗi mạng, và nó *có* cải
thiện — nhưng con số 4/6 cho thấy nó không giải quyết được nguyên nhân: **các
lần thử vẫn chồng lên nhau**, mà dịch vụ thì từ chối chính các kết nối đồng
thời. Phải chặn ở gốc, không phải chữa ở ngọn.

**Quyết định chốt.** Không chấp nhận "đã đỡ" làm điều kiện kết thúc. Kịch bản
đo được giữ nguyên qua cả ba vòng để các con số so được với nhau — đây là lý
do vòng 3 phát hiện được cả cải thiện về thời gian.

> 🔧 Chi tiết ba bản vá và mã: `package/technical-docs.md`, mục "Khiếm khuyết — ĐÃ VÁ".

---

## Bước 5 — Mô tả lỗi đúng độ rộng

**Nguyên tắc.** Mô tả rộng hơn sự thật thì người sau đi tìm sai chỗ, và bản vá
cũng sẽ rộng hơn cần thiết.

**Việc làm cụ thể.** Lỗi ở vòng 3 lúc đầu được mô tả là *"chạy `asyncio.run()`
hai lần là hỏng"*. Đo kỹ thì không phải: một khoá dùng chung cho cả tiến trình
chỉ **tự gắn vào vòng lặp khi thực sự có tranh chấp** — đường nhanh của phép
lấy khoá trả về trước khi nó chạm tới vòng lặp. Nghĩa là lỗi nằm im cho tới
lúc có hai việc chồng nhau, rồi mới hiện ra ở một chỗ khác hẳn.

Điều kiện thật, viết lại cho đúng: *vòng lặp thứ nhất có hai render chồng
nhau, thì mọi vòng lặp sau đó đều hỏng.*

**Quyết định chốt.** Bài kiểm được viết theo điều kiện thật đó: phải **gây
tranh chấp ở vòng một** rồi mới thử vòng hai. Viết theo mô tả rộng ban đầu thì
bài kiểm sẽ xanh trong khi lỗi vẫn còn nguyên.

> 🔧 `tts.lock.is_per_event_loop_under_contention` trong `package/eval/`.

---

## Bước 6 — Đọc tín hiệu ở phía người dùng

**Nguyên tắc.** Nội dung câu người dùng nói không phải là tất cả thông tin.
**Việc họ nói lại lần thứ hai** cũng là thông tin — và nó thường trỏ về một
nguyên nhân khác hẳn.

**Việc làm cụ thể.** Đây là những tín hiệu đã gặp thật, và cách đọc chúng:

| Tín hiệu | Nghĩa thật |
|---|---|
| Yêu cầu **đánh số**, diễn đạt bằng hành vi | vàng ròng. Đối chiếu được từng câu, và về sau thành khung của cả tài liệu lẫn bài kiểm |
| Dán một thông báo lỗi trần trụi (`URL must start with 'https'`, `protocal error`, `Failed to fetch`) | chẩn đoán hoàn toàn thuộc về tôi. Người dùng đã cho hết thứ họ có |
| **"vẫn báo lổi"** lần thứ hai, cùng một triệu chứng | **dừng sửa mã.** Đi kiểm xem bản sửa đã được nạp chưa |
| Câu hỏi lạc đề nhưng gấp (`tại sau gatewaya khi chạy sudo tôi nhập đúng password những vẫn báo sai hoài`) | xử lý trước. Nó đang chặn mọi thứ khác |
| Hai báo cáo mâu thuẫn về **cùng một thiết bị**, cách nhau vài ngày | giữ lịch sử đo mới phân định được: thiết bị hỏng hay mã hồi quy |

Dòng thứ ba là dòng tôi **đã bỏ lỡ một vòng**, và cái giá là một vòng sửa vô
ích. Trong một trường hợp khác cùng loại, tiến trình cũ sống thêm **3 ngày**
vì `systemctl enable --now` không khởi động lại service đang chạy — người dùng
phải nói "vẫn lỗi" ba lần.

**Prompt thật** — hai câu liên tiếp, chính là chỗ tín hiệu xuất hiện:

```
vẫn báo lổi khi kết nối với mcp llama-server
```
```
vẫn báo lổi:
```

*(Đây là câu để NHẬN RA, không phải câu để người đọc gõ lại.)*

**Quyết định chốt.** Đưa việc kiểm tra ấy vào công cụ chứ không vào trí nhớ:
`service.sh status` in thẳng dòng lệnh thật mà tiến trình đang chạy, lấy từ
`/proc/<MainPID>/cmdline`. Không phải đoán, không phải nhớ.

---

## Bước 7 — Viết bài kiểm mà chính nó phải tự chứng minh

**Nguyên tắc.** Một bộ kiểm thử toàn màu xanh chưa nói lên điều gì: nó xanh vì
sản phẩm đúng, hay vì nó không thật sự kiểm gì? Cách duy nhất để biết là **cố
tình làm hỏng sản phẩm và bắt nó phải đỏ**.

**Việc làm cụ thể.** `package/eval/reverse-check.py` gieo từng khiếm khuyết đã
biết vào mã rồi đòi bài kiểm bắt đúng những mục đã ghi **trước** khi gieo.

Bốn điều làm nên khác biệt giữa việc này và "viết thêm test":

1. **Gieo vào BẢN SAO.** Mỗi trường hợp sao mã sang thư mục tạm riêng rồi sửa
   bản sao. Cây thật không bao giờ bị ghi vào — hoàn nguyên là hệ quả của cấu
   trúc, không phải của việc nhớ dọn dẹp.
2. **Kỳ vọng viết trước.** Ghi ra "lỗi này phải làm đỏ những mục nào" *trước*
   khi chạy. Ghi sau là tự chấm điểm cho mình.
3. **Đối chứng vô hại.** Ít nhất một thay đổi không đổi hành vi, kỳ vọng vẫn
   XANH. Nếu nó cũng đỏ thì bài kiểm đang đỏ bừa — cũng là hỏng.
4. **Phủ ngược đầy đủ.** Mục nào không lỗi gieo nào làm đỏ được thì bị nêu tên
   ngay: rất có thể nó không hề chạm vào mã sản phẩm.

**Ba dạng bài kiểm giả** đã gặp thật, ghi ra để nhận mặt:

- **So kích thước thay vì so tập.** "Có 13 tool" xanh cả khi một tool bị đổi
  tên. Phải so **tập tên tường minh**.
- **Sập giữa chừng mà vẫn báo đạt.** Nên báo cáo in `đã chạy X/Y mục đăng ký`,
  và X<Y là hỏng toàn cục — kể cả khi mọi mục đã chạy đều xanh. Luật này áp
  cho **mọi** công cụ trong thư mục kiểm, kể cả chính `reverse-check.py`:
  khớp 0 trường hợp không được báo ĐẠT.
- **Kiểm mà không chạm vào sản phẩm.** Bắt bằng luật phủ ngược ở trên.

**Khi một mục "lẽ ra đỏ mà lại xanh"**, có đúng ba khả năng, và phải chọn một:

| Nhánh | Nghĩa | Xử lý |
|---|---|---|
| **Test giả** | bài kiểm sai, không bắt được gì | sửa bài kiểm cho bắt thật |
| **Kỳ vọng sai** | có cắn, nhưng đòi sai điều | sửa kỳ vọng **theo yêu cầu gốc, có trích nguồn**. Cấm nới cho xanh |
| **Lỗi gieo không quan sát được** | lỗi bị một cơ chế khác che mất | **đổi lỗi gieo**, hoặc ghi CHƯA PHỦ kèm tên cơ chế che |

Nhánh thứ ba hay bị bỏ quên, và bỏ quên nó thì tệ: người ta sẽ đi làm bài kiểm
*tệ đi* cho vừa luật. Gặp thật ở product này: lỗi gieo vào tầng cache TTS bị
**lần kiểm thứ hai bên trong khoá** che mất, nên phải gieo vào cả hai chỗ mới
quan sát được.

**Ba cái bẫy đã tự dẫm phải** khi viết bộ kiểm này — đắt hơn cả việc viết:

- **Đỏ bừa vì đếm sau khi bối cảnh đã đóng.** Khẳng định đặt sau khi thư mục
  tạm đã dọn thì là đếm vào chỗ trống. **Bằng chứng phải bền cả theo thời gian
  lẫn theo phạm vi**: khẳng định phải sống trong vòng đời của thứ nó tham
  chiếu.
- **Tráo bối cảnh nửa vời.** Thay thành phần A mà quên thành phần B đi kèm,
  thế là B trỏ vào thế giới cũ và ném lỗi ở một chỗ chẳng liên quan gì.
  **Tráo nửa nguy hơn không tráo.**
- **Vá bằng cách gán đè lên chính thứ mình đang gọi.** Rút ngắn thời gian chờ
  bằng cách gán `sleep` trỏ về `sleep` — nó tự gọi chính nó, và lỗi hiện ra ở
  ba mục chẳng liên quan. Muốn thay thì bọc, đừng gán đè.

**Quyết định chốt.** Chia bài kiểm theo **tác dụng phụ**, không theo tốc độ:
tầng mặc định không chạm gì cả, tầng `--online` chạm mạng, tầng `--hardware`
phát ra tiếng thật và phải xin phép mỗi lần. **Bài kiểm không ai dám chạy thì
bằng như không có.**

> 🔧 Luật đầy đủ và cách chạy: `package/eval/README.md`.

---

## Bước 8 — Một bài học suy luận, suýt thành kết luận sai

**Nguyên tắc.** Hai mẫu trùng nhau không đủ để suy ra nguyên nhân hệ thống.

**Việc làm cụ thể.** Cả hai chiếc Nest Hub trong nhà cùng đóng cổng điều khiển
(mDNS thấy, ping được, nhưng TCP bị từ chối). Tôi đã kết luận: firmware mới bỏ
cổng đó. Nghe rất hợp lý — hai trên hai mà.

Sự thật: **thiết bị treo**. Khởi động lại là hết. Hai thiết bị cùng model,
cùng mạng, cùng lịch cập nhật thì trùng nhau là chuyện tất nhiên, không phải
bằng chứng về nguyên nhân.

**Quyết định chốt — viết thành luật, không chỉ thành mẩu chuyện.** *Trước khi
nghi ngờ mã của mình, hãy tìm một phép kiểm rẻ tiền ở TẦNG DƯỚI mã và chạy nó
trước.* Ở đây tầng dưới là TCP, phép kiểm là `nc -z <ip> 8009`. Với product
khác thì là một `ping`, một `curl`, một lệnh đọc trạng thái của gateway — cái
gì cũng được, miễn nó trả lời câu "thiết bị có còn nghe không" mà không cần
mã của mình đúng. Ghi vào bảng sự cố của `package/README.md` để lần sau không
phải nhớ.

---

## Cách đã kiểm chứng

Cột "số lần" là **số**, hoặc **CHƯA ĐẾM**. Không ghi "nhiều".

| Kịch bản | Số lần | Biên / điều kiện xấu | Kết quả |
|---|---|---|---|
| `say` → Kitchen speaker | CHƯA ĐẾM (≥8) | bình thường | `playing`; người dùng xác nhận **nghe được** |
| `say` → Working display (Nest Hub) | 5, rải 2 ngày | thiết bị treo rồi khởi động lại | 3 lần đầu **thất bại** (`wait timed out`, cổng 8009 refuse); sau restart: 1 OK + 3 clip đo |
| Đo thời lượng phát | 3 clip (2.09 / 4.27 / 7.10s) | độ dài khác nhau | cả 3 `PLAYING` đủ `duration` → `idle_reason=FINISHED`; log HTTP xác nhận có tải file (200) |
| Thương lượng protocolVersion | 3 phiên bản | client cũ / mới | cả 3 trả đúng version |
| MCP client thật qua https (nginx+TLS) | 1 | — | initialize + 13 tool + `list_speakers` → 4 loa |
| MCP client thật qua LAN `:8765` | 1 | — | như trên |
| Client trình duyệt (Origin `http://192.168.1.99:8383`) | 1 | có CORS | preflight 200 + allow-origin đúng; initialize 200 JSON; 13 tool |
| `--json-response --stateless` | 1 | client khắt khe | trả `application/json`; `tools/call` không cần session id |
| Dò thiết bị + lọc loa | CHƯA ĐẾM (≥6) | mạng thật 8 thiết bị | 4 loa / 4 thiết bị hình ảnh |
| `target="all"` | 2: trước và sau khi sửa | 4 loa song song | trước: 4 `playing` nhưng **chồng luồng**; sau: 3 loa riêng lẻ |
| Nhiều loa cách phẩy | 1 | 2 loa | cả 2 `playing` |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 2 | phần tử hỏng | loa thật nhận đúng audio, phần tử hỏng `error` riêng, tổng thể `ok`; `say()` 5.4s so với clip 2.26s |
| TTS dồn 6 yêu cầu song song | 3: trước vá / sau khoá / sau khoá-theo-vòng-lặp | dịch vụ từ chối kết nối đồng thời | 4/6 (101s) → 6/6 (12s) → **6/6 (6.2s)**, 0 file 0 byte |
| Khoá qua 2 vòng lặp **có tranh chấp** | 2: trước và sau vá | `asyncio.run()` hai lần | trước: vòng 2 lỗi "gắn nhầm vòng lặp"; sau: **cả hai vòng đều chạy** |
| **Eval offline** | 6 phiên đóng gói | không tiếng | 35 → 43 → 67 → 138 → 49 → **77 mục, phủ ngược đầy đủ**, exit 0 |
| **Eval `--online`** | 2 | cần internet | 157/157 rồi 49/49 |
| **Eval `--hardware`** (xin phép mỗi lần) | 5 | cast thật ra loa | 37 → 48 → 67 → 157 → 49/49; **lần nào cũng lộ ≥1 lỗi của bài kiểm** |

**Vì sao dãy số mục eval nhảy lên rồi tụt xuống** (35 → 43 → 67 → 138 → 49 →
77): không phải bỏ bớt phép kiểm, mà là **đổi đơn vị đếm** giữa các phiên. Có
phiên đếm từng phép khẳng định, có phiên đếm từng *mục* (một mục chứa nhiều
khẳng định). Con số 138 là lần đếm mịn nhất. Từ phiên này trở đi đơn vị được
chốt là **mục đăng ký**, nên chỉ các con số từ đây về sau mới so được với
nhau. Ghi ra vì chính note này dạy "giữ nguyên kịch bản để con số so được" —
và bảng này từng vi phạm điều đó.

### Biên và điều kiện xấu đã quan sát được (thật, không giả định)

TCP 8009 refuse → timeout · mDNS sót thiết bị đã lưu → lỗi tự mâu thuẫn ·
Origin ngoài allowlist → 403 · Host không tin → 421 · mở endpoint bằng trình
duyệt → 406 (**đúng đặc tả, không phải lỗi**) · preflight chưa bật CORS → 405
không kèm header · bỏ loa đích → `needs_speaker_selection`, **không phát gì** ·
cài lại service khi đang chạy → tiến trình **không đổi** · `all` gồm cả nhóm
lẫn thành viên → chồng luồng mà API vẫn báo `playing` · **sáu lần bộ eval tự
hỏng** (2 rò mock, 1 sập giữa chừng, 1 đỏ bừa do bối cảnh đóng sớm, 1 tráo
bối cảnh nửa vời, 1 gán đè lên chính hàm đang gọi).

### CHƯA THỬ

Giọng nam bằng tai · tham số tốc độ bằng tai · service sống sót qua **reboot
máy** (đã bật tự khởi động, chưa reboot bao giờ) · nhánh quét lại khi **loa
đổi IP** làm địa chỉ đã lưu bị cũ · chặn IP ở nginx (đã đồng ý bật, hai dòng
vẫn đang comment) · **MCP elicitation** trên client thật — quyết định không
dùng nó là **phán đoán**, chưa đo client nào.

### CÒN MỞ

Khác với CHƯA THỬ: đây là chỗ **đã biết là thiếu**, không phải chỗ chưa có dữ
liệu. Không có xác thực ở tầng ứng dụng, và endpoint đang phân giải công khai
ra internet · cổng audio bind mọi giao diện, không xác thực, phục vụ nguyên
thư mục cache · chặn IP nginx đã đồng ý bật nhưng hai dòng vẫn đang comment ·
cache TTS tăng vô hạn · chưa khôi phục âm lượng/media đang phát sau thông báo.

Mức rủi ro và chi tiết từng khoản: `package/technical-docs.md` mục "Khiếm
khuyết — CÒN MỞ".

---

## Danh sách prompt thật của người dùng

Giữ nguyên thứ tự và lỗi gõ. Đọc dọc danh sách này thấy được hình dạng thật
của một phiên làm việc: **một prompt sinh ra sản phẩm, hai mươi prompt còn lại
là vận hành và sự cố.**

```
1.  hãy khởi tạo git vào ignore folder .claude
2.  hãy đọc plans/reports/handoff-260807-1157-googlecast-mcp-scaffold.md để tiếp tục
3.  hãy kiểm tra xem mcp này đúng yêu cầu không: [ba yêu cầu — xem Bước 1]
4.  có workinig speaker xác minh luôn tts -> HTTP -> cast chạy thật
5.  đã nghe được rồi vậy xong chưa
6.  Tôi muốn khi chat với claude sẽ tự gọi và tương tác với mcp phải làm sao
7.  Mcp này sẽ chạy dạng service trên máy ip .128 máy tôi setup claude desktop ip .28 giờ tôi làm dao bên cạnh đó hãy viết thêm install service remove service start stop cho mcp
8.  URL must start with 'https'
9.  không đc port đang chạy là bao nhiêu để tôi dùng nginx reveser proxy về máy 128
10. domain tôi vừa tạo: google_cast.adrec.cloud hãy cập nhật
11. kiểm tra xem tại sau gatewaya khi chạy sudo tôi nhập đúng password những vẫn báo sai hoài
12. https://google-cast.adrec.cloud/mcp kết quả là {"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept text/event-stream"}}
13. đã chạy tốt ghi cập nhật readme và thông tin kỹ thuật đầy đủ
14. apex_hp đã xử lý xong
15. khi phát loa working display chi nháy sáng rồi tắt không phát đầy đủ âm thanh
16. mcp này tôi chạy khi kết nối với mcp llama-server thì báo lổi: protocal error
17. vẫn báo lổi khi kết nối với mcp llama-server        [+ ảnh log "Failed to fetch (check CORS?)"]
18. vẫn báo lổi:                                        [+ Connection Log]
19. server tôi đang setup mcp là 192.168.1.99 có cần cập nhật command không
20. đây là url llama-server tôi đang chạy http://192.168.1.99:8383/#/mcp-servers
21. note command đó vào readme
```

**Đọc gì từ danh sách này:**

- **#3 sinh ra toàn bộ product.** Nó đánh số và diễn đạt bằng hành vi.
- **#8, #12, #16, #17, #18** chỉ là lỗi dán vào — chẩn đoán hoàn toàn thuộc về AI.
- **#17 → #18** lặp "vẫn báo lổi": tín hiệu đổi hướng, xem Bước 6.
- **#11** lạc đề nhưng gấp nhất cả phiên.
- **#4 và #15** mâu thuẫn nhau về cùng một thiết bị, cách nhau vài ngày. Giữ
  lịch sử đo mới phân định được lỗi thiết bị với hồi quy mã.
- **#10 → tên miền có gạch dưới** dẫn tới một ngõ cụt tuyệt đối: cơ quan cấp
  chứng chỉ không ký cho tên chứa gạch dưới, mà client thì bắt buộc `https`.
  Không có cách vòng, chỉ có đổi tên miền.

---

## Nếu làm lại product tương tự

Thứ tự này rút ra từ chính phiên trên, không phải lý thuyết:

1. Lấy yêu cầu **đánh số, viết bằng hành vi**. Nếu người đặt hàng chưa viết
   vậy thì giúp họ viết lại trước khi động vào mã.
2. Đối chiếu với cái đang có → danh sách việc. Giữ nguyên thứ đã đúng.
3. Phân loại thành phần: cảm nhận được thì so sánh (một vòng, người thật
   nghe/nhìn); xương sống thì chọn theo mức bảo trì.
4. Chạm vật thật sớm nhất có thể. Cái đường đi vòng mà mình chưa nghĩ ra sẽ lộ
   ra ở đây.
5. Mỗi lần vá: đo cùng một kịch bản, giữ con số để so được giữa các vòng.
6. Viết bài kiểm, rồi **kiểm chính bài kiểm bằng cách gieo lỗi vào bản sao**.
7. Chia bài kiểm theo tác dụng phụ; thứ gây tác dụng phụ vật lý phải xin phép.
8. Ghi lại cả **CHƯA THỬ** và **CÒN MỞ**. Bàn giao mà tô hồng thì người nhận
   sẽ phát hiện ra vào đúng lúc tệ nhất.

---

## Phụ lục — Định đoạt lỗ hổng sau khi chấm (B4)

Người đọc sạch chấm **L2** và nêu 9 lỗ hổng. Định đoạt từng cái, kể cả khi đã
đạt mức mục tiêu:

| # | Lỗ hổng | Định đoạt |
|---|---|---|
| 1 | frontmatter trỏ "xem B4" — không có mục nào tên vậy | **sửa ngay**: ghi thẳng `transmission_level: L2` |
| 2 | không bước nào dạy cách "hỏi lại khi thiếu tham số" | **sửa ngay**: thêm mục riêng cuối Bước 1 |
| 3 | Bước 2 (và 4, 5, 7, 8) không có prompt thật | **sửa ngay**: ghi thẳng "KHÔNG CÓ" + lý do, thay vì để người đọc đi tìm |
| 4 | con trỏ `docs/`, `plans/` ra ngoài package | **sửa ngay**: thêm quy ước đường dẫn ở đầu note + nêu đích danh file bàn giao scaffold |
| 5 | không có lệnh chạy eval trong note | **chấp nhận + ghi lý do**: đúng ranh giới đã tuyên bố (note = cách nghĩ). Note trỏ sang `package/eval/README.md`, nơi có đủ lệnh |
| 6 | dãy số mục eval nhảy lên rồi tụt | **sửa ngay**: thêm chú giải "đổi đơn vị đếm", chốt đơn vị từ nay |
| 7 | bài học "hai mẫu trùng nhau" thiếu luật khái quát | **sửa ngay**: viết thành luật ở Bước 8 |
| 8 | 5/7 ý được nói ba lần (tóm tắt → thân → checklist) | **chấp nhận + ghi lý do**: "Bài học 30 giây" là mục lục cho người đọc lướt, "Nếu làm lại" là danh sách thao tác. Cắt đi thì mất hai đường vào khác nhau |
| 9 | có CHƯA THỬ nhưng thiếu CÒN MỞ | **sửa ngay**: thêm mục CÒN MỞ, trỏ chi tiết sang `package/technical-docs.md` |
