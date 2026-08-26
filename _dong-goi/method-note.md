---
product: googlecast-mcp
loai: harness vận hành (MCP server)
ngay: 2026-08-26
transmission_level: L2 (chấm 2026-08-26, người đọc sạch, đề đối chứng: MCP server điều khiển đèn Philips Hue)
---

# Cách xây googlecast-mcp — và cách nghĩ để xây cái khác

Product: một MCP server dò loa Google trong nhà rồi đọc text tiếng Việt ra loa.
Nhưng ghi chú này **không phải để hiểu product đó**. Nó để người sau xây được
*một thứ khác* theo cùng cách nghĩ. Muốn hiểu product thì đọc `package/`.

---

## Bài học 30 giây

1. **Yêu cầu đánh số, diễn đạt bằng hành vi, là thứ đáng giá nhất người dùng đưa
   cho bạn.** Đối chiếu được từng cái một. Và **danh sách yêu cầu chưa đạt chính
   là danh sách việc phải làm** — không cần nghĩ thêm bản kế hoạch nào nữa.
2. **Thành phần người ta *cảm nhận được* thì phải để người ta nghe/nhìn rồi chọn.
   Thành phần *xương sống* thì chọn theo mức bảo trì, không cần so sánh.** Hai
   loại quyết định khác nhau, đừng áp một quy trình cho cả hai.
3. **Hai lần trùng nhau không đủ để kết luận nguyên nhân hệ thống.** Hai thiết bị
   cùng hỏng một kiểu vẫn có thể chỉ là hai thiết bị đang treo.
4. **Khi người dùng nói "vẫn lỗi" lần thứ hai, dừng sửa lại.** Đi kiểm xem bản sửa
   của bạn **đã được nạp chưa**. Đây là tín hiệu, và nó dễ bị bỏ lỡ nhất.
5. **Thử lại không cứu được thứ hỏng vì chồng lấn.** Nếu các lần thử vẫn đè lên
   nhau thì thử lại chỉ là hỏng lại. Phải chặn ở gốc: xếp hàng.
6. **Bài kiểm chưa từng đỏ là bài kiểm chưa chứng minh được gì** — và bài kiểm đỏ
   khi không có gì sai cũng hỏng y như vậy. Phải thử **cả hai chiều**.
7. **Mặc định của mọi hành động không hoàn tác được là: không làm gì.** Im lặng
   an toàn hơn đoán mò.

## Thứ tự làm việc

Bảy mục dưới đây là bảy bài học theo chủ đề, không phải bảy bước. Thứ tự thao tác
thật là:

1. Đọc yêu cầu, **đánh số** lại nếu người dùng chưa đánh số → mục 1
2. Đối chiếu từng yêu cầu với mã đang có, ra bảng **đạt / chưa đạt** → mục 1
3. Tìm **ràng buộc vật lý** không thương lượng được, để kiến trúc lộ ra → mục 3
4. Chọn thư viện: tách **cảm nhận được** khỏi **xương sống** → mục 2
5. Viết đúng các module trong danh sách **chưa đạt** → mục 1
6. Viết bộ kiểm **cùng lúc**, kèm kiểm ngược hai chiều → mục 6
7. Chạy thật, gặp lỗi thì theo mục 4 và 5; chốt mặc định an toàn theo mục 7
8. Lập bảng **"Cách đã kiểm chứng"** — cái gì chưa thử thì ghi **CHƯA THỬ**

---

## 1. Đọc yêu cầu — chỗ này quyết định mọi thứ

**Nguyên tắc.** Không phải mọi câu người dùng gõ đều ngang giá. Có câu sinh ra cả
product; có câu chỉ là dán lỗi vào cho bạn tự chẩn. Nhận ra khác biệt đó tiết kiệm
được phần lớn công sức.

**Việc làm cụ thể.** Product này bắt đầu từ một scaffold có sẵn từ phiên trước
(11 tool Cast chung chung, **chưa có TTS**). "Chạy được" lúc đó chỉ nghĩa là *kết
nối được và liệt kê được thiết bị*. Rồi đúng **một** prompt sinh ra toàn bộ phần
còn lại.

**Prompt mẫu thật** (nguyên văn, giữ nguyên lỗi gõ):

```
hãy kiểm tra xem mcp này đúng yêu cầu không:
1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả
```

**Quyết định chốt.** Không viết kế hoạch. Đối chiếu thẳng ba yêu cầu với mã đang
có, ra kết quả **đạt 1/3** — và cái 1/3 đó còn dở dang (chỉ cache trong RAM, mất
khi khởi động lại). Rồi:

> **Danh sách yêu cầu chưa đạt chính là danh sách module cần viết.**

YC1 thiếu phần "lưu lại" → `speaker_store.py`. YC2 thiếu toàn bộ → `tts.py` +
`media_server.py`. YC3 thiếu toàn bộ → `say()` + `_select_targets()`. Phần
`cast_manager.py` **giữ nguyên** vì nó vốn đã đúng việc.

Hai điểm đáng học ở prompt trên:
- nó **đánh số**, nên đối chiếu được từng cái;
- nó tả **hành vi quan sát được** ("phát lên speaker"), không tả giải pháp
  ("dùng thư viện X"). Nhờ vậy cách làm còn tự do, còn đích thì rõ.

🔧 Ngược lại, những prompt như `URL must start with 'https'` hay
`Failed to fetch (check CORS?)` chỉ là **lỗi dán vào**. Người dùng không chẩn gì
cả — toàn bộ việc chẩn đoán thuộc về AI. Đừng chờ thêm thông tin từ những câu đó.

## 2. Chọn thư viện — hai loại quyết định, đừng trộn

**Nguyên tắc.** Thành phần mà người dùng **cảm nhận được bằng giác quan** thì
tiêu chí kỹ thuật không quyết định nổi; phải để họ trải nghiệm rồi chọn. Thành
phần **xương sống** thì ngược lại: so sánh là lãng phí thời gian.

**Việc làm cụ thể.**

*Giọng nói* — người dùng nghe được, nên phải nghe. Dựng thử **4 phương án** và
đưa mẫu âm thanh cho họ so:

| Phương án | Kỹ thuật | Kết quả |
|---|---|---|
| gTTS | miễn phí, dễ | giọng máy móc |
| Google Cloud TTS | chất lượng cao | cần API key + trả phí |
| Piper | chạy offline | giọng yếu, cài đặt nặng |
| **edge-tts** | miễn phí, không key | **tự nhiên nhất → chọn** |

*pychromecast* — **không qua so sánh nào cả.** Nó là thư viện Python duy nhất còn
được bảo trì cho giao thức Cast. Ngồi so sánh chỉ để ra đúng một lựa chọn là phí
thời gian.

**Prompt mẫu** *(tái dựng — không phải nguyên văn)*:

```
Tôi cần TTS tiếng Việt cho MCP server này. Hãy dựng thử 4 phương án
(gTTS, Google Cloud TTS, Piper, edge-tts), mỗi cái render cùng một câu
tiếng Việt ra file mp3, rồi đưa tôi nghe. Tiêu chí kỹ thuật (chi phí,
cần key hay không, chạy offline được không) thì anh tự chấm và ghi bảng.
Riêng tiêu chí "nghe có tự nhiên không" thì tôi nghe rồi tôi quyết.
```

**Quyết định chốt.** **Chỉ một vòng**, không lặp. Người dùng nghe, chọn edge-tts,
xong. Cách chia việc là điểm mấu chốt: **AI tự chấm phần đo được, con người chấm
phần cảm nhận được.** Trộn hai thứ vào nhau thì hoặc AI quyết thay người ở chỗ nó
không đủ tư cách, hoặc người phải ngồi đọc bảng so sánh mà lẽ ra AI làm được.

## 3. Để kiến trúc lộ ra từ ràng buộc vật lý

**Nguyên tắc.** Trước khi thiết kế, đi tìm **một sự thật vật lý** mà bạn không
thể thương lượng. Kiến trúc thường chỉ là hệ quả của nó.

**Việc làm cụ thể.** Sự thật ở đây: **thiết bị Cast tự đi tải media qua HTTP.**
Nó không phải cái loa để ghi byte vào. Từ đó suy ra ngay:

- đường dẫn file trên máy là vô nghĩa với nó → phải có URL;
- URL phải với tới được từ phía thiết bị → phải là địa chỉ LAN;
- vậy **server "nói được" bắt buộc kiêm luôn HTTP file server**;
- và vì thế nó **bắt buộc nằm cùng LAN với loa** — không có cách lách nào.

Ràng buộc cuối cùng đó không phải giới hạn của bản triển khai này. Nó là giới hạn
của bài toán. Chép vào tài liệu ngay, vì người sau sẽ hỏi "sao không chạy trên VPS
được".

**Prompt mẫu** *(tái dựng — dùng được cho bất kỳ product nào nói chuyện với thiết
bị hoặc dịch vụ bên ngoài)*:

```
Trước khi thiết kế gì cả: liệt kê các SỰ THẬT VẬT LÝ về thiết bị / giao thức
này mà tôi KHÔNG thương lượng được — nó tự làm gì, nó cần gì từ phía tôi, nó
không thể làm gì. Với mỗi sự thật, suy ra ràng buộc triển khai BẮT BUỘC đi
kèm. Nếu có ràng buộc nào giới hạn cả bài toán chứ không chỉ bản làm này
(ví dụ: buộc phải chạy trong cùng mạng), hãy nói rõ để tôi ghi vào tài liệu.
```

**Quyết định chốt.** Nhận ra sớm cũng đồng nghĩa nhận ra: địa chỉ **bind** và địa
chỉ **quảng bá** là hai thứ khác nhau. Bind `0.0.0.0`, quảng bá `lan_ip()`. Lẫn
lộn hai cái này là một lớp lỗi riêng, và về sau nó trở thành một mục kiểm.

## 4. Chẩn lỗi — bốn cái bẫy đã sập vào

**Nguyên tắc.** Sai lầm chẩn đoán tốn kém nhất không phải là sửa sai chỗ. Là
**sửa đúng chỗ mà bản sửa không được nạp** — rồi kết luận rằng chẩn đoán sai.

### 4a. Tín hiệu "vẫn lỗi" lần thứ hai

Người dùng gõ `vẫn báo lổi khi kết nối với mcp llama-server`, rồi lần sau chỉ gõ
`vẫn báo lổi:`. **Đây là tín hiệu cần nhận ra ở phía người dùng, không phải câu
để bạn đi gõ lại cho AI.**

Lần lặp thứ hai nghĩa là: giả thuyết hiện tại **hoặc** sai, **hoặc** đúng nhưng
chưa tới được nơi đang chạy. Kiểm khả năng thứ hai trước — nó rẻ hơn nhiều.

Trong phiên gốc, tín hiệu này **đã bị bỏ lỡ một vòng**. Ghi lại ở đây đúng vì thế.

**Prompt mẫu** *(tái dựng — gõ cái này thay vì gõ thêm một mô tả lỗi nữa)*:

```
Khoan sửa tiếp. Trước hết hãy CHỨNG MINH cho tôi bản sửa vừa rồi đã thật sự
được nạp vào cái đang chạy: in dòng lệnh của tiến trình đang chạy (không phải
nội dung file cấu hình), in mtime của các file mã mà tiến trình đó đang dùng,
và chỉ ra chỗ nào trong đó chứa thay đổi vừa làm. Nếu không chứng minh được
thì vấn đề là ở khâu nạp, không phải ở chẩn đoán.
```

### 4b. `systemctl enable --now` không khởi động lại service đang chạy

Đây chính là cơ chế của 4a. Một tiến trình cũ sống tiếp **3 ngày**, người dùng
phải nói "vẫn lỗi" **ba lần**, trong khi mọi bản sửa đều đúng và đều không được
nạp.

Cách thoát, và cũng là thứ nên có sẵn trong mọi script service:

```bash
sudo systemctl restart "$SERVICE_NAME"      # tường minh, không dựa vào enable --now

# và status phải in ra dòng lệnh tiến trình ĐANG THẬT SỰ chạy:
pid="$(systemctl show "$SERVICE_NAME" -p MainPID --value)"
tr '\0' ' ' < "/proc/$pid/cmdline"
```

> **Bài học tổng quát:** mọi công cụ triển khai đều cần một cách **quan sát cái
> đang chạy**, tách hẳn khỏi cách xem **cái đáng lẽ phải chạy**. Thiếu nó thì
> mọi vòng chẩn đoán đều có thể là vòng vô ích.

### 4c. Hai mẫu trùng nhau không phải là quy luật

Cả **hai** cái Nest Hub trong nhà đều từ chối cổng TCP 8009. Kết luận rút ra lúc
đó: *"Nest Hub bỏ cổng 8009 do firmware"*. Nghe rất hợp lý.

**Sai.** Khởi động lại thiết bị là hết. Chúng chỉ đang cùng treo.

Hai mẫu trùng nhau đủ để **đặt giả thuyết**, không đủ để **kết luận**. Nhất là khi
kết luận đó tiện lợi — "phần cứng nó thế" là câu kết thúc điều tra rất êm tai.

🔧 Thứ tự đúng khi thiết bị Cast không nhận lệnh: `nc -z <ip> 8009` **trước**, rồi
mới nghi ngờ code. mDNS trả lời và `ping` được **không** có nghĩa là cổng cast mở.

### 4d. Lỗi im lặng khó hơn lỗi ồn ào

Ba lỗi tốn thời gian nhất trong phiên đều **không nói gì**:

| Triệu chứng | Sự thật |
|---|---|
| Client nối được rồi treo, không có lỗi | nginx đang **đệm** stream → `proxy_buffering off` |
| Trình duyệt báo mỗi `Failed to fetch` | SDK trả `OPTIONS` = **405 không kèm header CORS** → trình duyệt chặn, JS chỉ thấy lỗi trống |
| Thiết bị "nhận" cast nhưng im lặng | nó **không với tới được** cổng audio |

Với lớp lỗi này, đọc log ứng dụng là vô ích — thông tin nằm ở **tầng dưới**: tab
Network của trình duyệt, `curl -v`, log nginx. Đổi tầng quan sát, đừng đọc kỹ hơn
ở tầng cũ.

🔧 Cái bẫy CORS còn một tầng nữa: bật `CORSMiddleware` thôi **chưa đủ**. Phải
`expose_headers=["Mcp-Session-Id"]`, vì trình duyệt **không đọc được** header
không được expose, nên không nối tiếp phiên được — mà lỗi hiện ra vẫn y hệt.

### 4e. Ngõ cụt tuyệt đối cũng cần được nhận ra

Người dùng tạo `google_cast.adrec.cloud`. Không CA nào cấp chứng chỉ cho tên có
dấu gạch dưới (CA/B Forum cấm). Mà Claude Desktop **bắt buộc** https.

Đây không phải lỗi cấu hình cần sửa. Đây là **ngõ cụt**: mọi nỗ lực theo hướng đó
đều thất bại. Cách thoát duy nhất là quay lại đổi tên miền. Nhận ra một ngõ cụt
sớm cũng có giá trị ngang việc tìm ra cách sửa.

## 5. Thử lại không phải thuốc chữa bách bệnh

**Nguyên tắc.** Trước khi thêm cơ chế thử lại, hỏi: *các lần thử có còn chồng lên
nhau không?* Nếu có, thử lại chỉ nhân bản thất bại.

**Việc làm cụ thể.** Gọi dồn 6 thông báo cùng lúc → **4/6 đạt, 101 giây**, lỗi
`Cannot connect to host`. Thêm thử lại. Đo lại: **vẫn 4/6**.

Vì nguyên nhân không phải "lỗi ngẫu nhiên" mà là "dịch vụ từ chối các kết nối đến
**cùng lúc**". Ba lần thử đồng thời chỉ là ba lần bị từ chối đồng thời.

Cách thoát: **tuần tự hoá** bằng một `asyncio.Lock`, cộng với thử lại có giãn
cách. Đo lại: **6/6 đạt, 12 giây**, và không còn file 0 byte.

**Quyết định chốt.** Số đo trước/sau là thứ phân định. Nếu chỉ nhìn code mà không
đo, bản vá đầu tiên trông đã "có thử lại rồi" và sẽ được coi là xong.

> Cùng lúc đó lộ ra một bẫy nhỏ nhưng đắt: khi `save()` ném lỗi, nó **đã kịp tạo
> file rỗng**. File 0 byte đó nằm lại trong cache, và lần sau cache "trúng" nó →
> loa phát im lặng **vĩnh viễn**. Bộ nhớ đệm mà không kiểm tính hợp lệ của thứ nó
> nhớ thì là bộ nhớ đệm lỗi.

## 6. Viết bài kiểm không tự lừa mình

**Nguyên tắc.** Bộ kiểm là mã, nên nó cũng có lỗi — và lỗi của nó **luôn nghiêng
về phía lạc quan**. Vậy phải kiểm chính bộ kiểm, **cả hai chiều**.

**Việc làm cụ thể.** Gieo từng lỗi đã biết vào **bản sao** của product, chạy lại,
đòi đúng những mục đã khai báo trước phải đỏ. Kèm vài **đối chứng vô hại** phải để
mọi thứ xanh.

**Prompt mẫu** *(tái dựng)*:

```
Viết reverse-check cho bộ eval này. Với mỗi lỗi gieo, khai báo TRƯỚC danh
sách id mục kiểm phải chuyển đỏ. Mục nào nằm trong danh sách mà vẫn xanh
thì in ra là TEST GIẢ. Thêm vài đối chứng vô hại (thêm chú thích, sửa lời
docstring) và đòi chúng để bộ kiểm XANH — đỏ ở đối chứng là đỏ bừa.
Gieo lỗi vào bản sao dưới thư mục tạm, PYTHONPATH trỏ vào bản sao, tuyệt
đối không ghi vào cây sản phẩm. Cuối cùng chạy lại trên cây nguyên vẹn và
đòi XANH. In ra mục nào không lỗi gieo nào làm đỏ được.
```

**Quyết định chốt.** Lần chạy đầu tiên trả **CHUA DAT** với 4 vấn đề thật — trong
đó 3 là bộ kiểm tự tố cáo mình. Chi tiết ở `package/eval/README.md`. Điểm cần nhớ
là **hình dạng** của chúng, vì chúng lặp lại ở mọi dự án:

| Hình dạng | Dấu hiệu |
|---|---|
| **Test giả** | mục xanh dù hành vi nó tự nhận canh gác đã bị phá |
| **Kỳ vọng sai** | mục có chạm mã sản phẩm, nhưng đòi sai điều — sửa **kỳ vọng theo requirement, có trích nguồn**; cấm nới cho xanh |
| **Đỏ bừa** | mục đỏ trong khi product hoàn toàn đúng — hỏng ngang test giả |
| **Sập giữa chừng** | một lỗi làm mọi mục sau im lặng biến mất; báo cáo vẫn "toàn xanh" |
| **So kích thước** | `len(a)==len(b)` xanh cả khi cả hai cùng co lại — phải so **tập tường minh** |
| **Không chạm sản phẩm** | mục viết lại logic ngay trong bài kiểm thay vì gọi vào mã thật |

🔧 Bốn quy tắc thao tác đi kèm, mỗi cái vá một lần đã bị lừa thật:

- **Đếm đủ trước khi đếm xanh.** In `đã chạy X/Y mục đăng ký`; `X<Y` là **FAIL
  toàn cục**. Bọc mỗi mục riêng, lỗi hạ tầng là `ERROR` chứ không được nuốt.
- **Hoàn nguyên = chạy lại thấy XANH sau khi xoá bytecode**, không phải nhìn
  `git status`. Lỗi gieo dài đúng bằng bản gốc có thể để lại `.pyc` cũ.
- **Ưu tiên cô lập hơn canh gác.** Thay thế ở tầng **thấp nhất** có thể
  (`edge_tts.Communicate` thay vì `tts.synthesize`) để mã sản phẩm còn chạy thật.
  Và có **residue guard** quy lỗi cho đúng mục làm rò.
- **Bằng chứng phải bền.** Chờ việc bất đồng bộ thì đừng bắt trạng thái thoáng
  qua. Ở đây, mục kiểm loa từng đỏ oan vì bắt `PLAYING` — mà clip chỉ dài 2.26s
  còn lệnh mất 5.4s, nên lúc quay lại nhìn thì loa **đã phát xong**. Đổi sang
  `content_id` khớp URL **và** `duration > 0`: dấu vết còn lại *sau khi* xong.

## 7. Mặc định an toàn cho hành động không hoàn tác được

**Nguyên tắc.** Khi hành động có tác dụng phụ **vật lý** không hoàn tác được,
mặc định phải là **không làm gì**.

**Việc làm cụ thể.** YC3 nói "nếu user không chọn speaker sẽ hỏi user". Có hai
cách hiểu, và cách hấp dẫn hơn là cách sai:

| Cách hiểu | Đánh giá |
|---|---|
| Phát ra tất cả rồi hỏi sau | tiện, và **sai** — đã phát tiếng vào nhà người ta rồi |
| **Không phát gì, trả danh sách để hỏi lại** | chậm hơn một nhịp, nhưng đúng |

**Quyết định chốt.** Trả về **dữ liệu có cấu trúc** (`status`, `speakers`,
`message`) chứ không phải lỗi, để LLM biết phải hỏi người dùng rồi gọi lại. Không
dùng MCP elicitation — **CHƯA THỬ trên client thật**, nên đó là phán đoán, và ghi
rõ là phán đoán.

🔧 Cùng nguyên tắc, ở chỗ khác: `target="all"` **bỏ nhóm loa**. Nhóm Cast phát
*qua* thành viên, nên gửi cả nhóm lẫn thành viên khiến một loa vật lý nhận **hai
luồng**. Điểm đáng sợ: **cả 4 lệnh đều trả `playing`** — API không phân biệt
được. Dấu vết duy nhất nằm ở siêu dữ liệu (nhóm và thành viên trùng `host`), và
cách phát hiện duy nhất là **nghe bằng tai**.

> Có những lớp lỗi mà mọi tín hiệu số đều báo thành công. Với chúng, một vòng
> kiểm tra bằng giác quan con người là không thể thay thế.

**Khi tác dụng phụ *hoàn tác được* thì cân lại.** Phát tiếng ra loa là không lấy
lại được, nên mặc định phải là im lặng. Nhưng bật một bóng đèn thì tắt lại được:
ở đó, "làm rồi báo, kèm cách hoàn tác" có thể tốt hơn "hỏi lại rồi mới làm". Câu
hỏi phân định không phải *"có tác dụng phụ không"* mà là **"hoàn tác có rẻ không,
và ai chịu chi phí nếu đoán sai"**.

---

## Cách đã kiểm chứng

Cột "số lần" là **số** hoặc **CHƯA ĐẾM**. Không ghi "nhiều".

| Kịch bản | Số lần | Biên / điều kiện | Kết quả |
|---|---|---|---|
| `say` → Kitchen speaker | CHƯA ĐẾM (≥6) | bình thường | `playing`; người dùng xác nhận **nghe được** |
| `say` → Working display (Nest Hub) | 5, rải 2 ngày | thiết bị treo, rồi restart | 3 lần đầu **thất bại** (`wait timed out`, 8009 refuse); sau restart: 1 OK + 3 clip đo |
| Đo thời lượng phát | 3 clip (2.09 / 4.27 / 7.10s) | độ dài khác nhau | cả 3 `PLAYING` đủ `duration` → `idle_reason=FINISHED`; log HTTP xác nhận có tải file (200) |
| Thương lượng `protocolVersion` | 3 phiên bản | client cũ và mới | cả 3 trả đúng version |
| MCP client thật qua https (nginx+TLS) | 1 | — | initialize + 13 tool + `list_speakers` → 4 loa |
| MCP client thật qua LAN `:8765` | 1 | — | như trên |
| Client trình duyệt (Origin `http://192.168.1.99:8383`) | 1 | có CORS | preflight 200 + allow-origin đúng; initialize 200 JSON; 13 tool |
| `--json-response --stateless` | 1 | client khắt khe | trả `application/json`; `tools/call` không cần session id |
| Dò thiết bị + lọc loa | CHƯA ĐẾM (≥5) | mạng thật 8 thiết bị | 4 loa / 4 thiết bị hình ảnh |
| `target="all"` | 2 (trước và sau khi sửa) | 4 loa song song | trước: 4 `playing` nhưng **chồng luồng**; sau: 3 loa riêng lẻ |
| Nhiều loa cách phẩy | 1 | 2 loa | cả 2 `playing` |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 2 | phần tử hỏng | loa thật nhận đúng audio; phần tử hỏng `error` riêng; tổng thể `ok`. Đo được `say()` mất **5.4s** trong khi clip chỉ **2.26s** |
| TTS gọi dồn 6 yêu cầu song song | 2 (trước và sau khi vá) | dịch vụ từ chối kết nối đồng thời | trước **4/6 (101s)** → sau **6/6 (12s)**, 0 file 0 byte |
| **Eval offline** | 5 phiên đóng gói | không tiếng | 35 → 43 → 67 → 138 → **47 mục, exit 0** ¹ |
| **Eval `--online`** | 2 | cần internet | 50/50; fan-out 6 thông báo trong 4.9s |
| **Eval `--hardware`** | 4 (xin phép mỗi lần) | cast thật | 37 → 48 → FAIL 62/63 rồi 67/67 → FAIL 155/156 rồi 157/157 |
| **Kiểm ngược** (`reverse-check.py`) | 2 | 45 lỗi gieo + 4 đối chứng | lần 1 **CHUA DAT** (3 test giả + 1 case cũ); lần 2 **DAT 49/49**, phủ ngược 47/47 mục |
| **Cài lại từ số 0** trên clone sạch | 1 | `/tmp`, không dùng thư mục làm việc | `git clone` → `uv sync` → stdio initialize → **13 tool** → `tools/call list_speakers` OK |
| HTTP transport trên cổng rỗi 8798 | 1 | song song service thật | initialize 200; 13 tool; `GET /mcp` → 406; `Host: evil.example.com` → 421 |

¹ Con số mục thay đổi giữa các phiên vì bộ kiểm được viết lại, không phải vì độ
phủ giảm. Bản này gộp nhiều phép khẳng định vào một mục có id, để **đếm được**
`X/Y` và để **kiểm ngược quy trách nhiệm được** cho từng mục.

### Cách lặp lại các hàng đo được

Bốn hàng cuối bảng lặp lại được ngay, không cần phần cứng:

```bash
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py            # hàng "Eval offline"
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online   # hàng "Eval --online" + fan-out 6
uv run python _dong-goi/package/eval/reverse-check.py                  # hàng "Kiểm ngược"
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --list     # xem id mục kiểm của từng hàng
```

Hàng "TTS gọi dồn 6 yêu cầu" tương ứng mục `tts.renders_are_serialised` (offline,
đo sự chồng lấn) và `online.fanout_all_survive` (online, đo thật). Hàng "Eval
`--hardware`" cần loa thật và **phải xin phép** — xem `package/eval/README.md`.
Hàng "Cài lại từ số 0" có nguyên output trong `package/README.md`.

### Biên và điều kiện xấu đã quan sát thật

TCP 8009 refuse → timeout · mDNS sót thiết bị đã lưu → `DeviceNotFoundError` tự
mâu thuẫn · Origin ngoài allowlist → 403 · Host không tin → 421 · mở `/mcp` bằng
trình duyệt → 406 (**đúng đặc tả**, không phải lỗi) · preflight chưa bật CORS →
405 không header · bỏ `target` → `needs_speaker_selection`, không phát gì · cài
lại service khi đang chạy → tiến trình **không đổi** · `all` gồm cả nhóm lẫn thành
viên → chồng luồng mà API vẫn báo `playing` · **bốn lần bộ eval tự hỏng** (2 rò
mock + 1 sập giữa chừng vì `KeyError` + 1 đỏ bừa do khẳng định đặt ngoài vòng đời
thư mục tạm).

### CHƯA THỬ — nói thẳng

- giọng nam `vi-VN-NamMinhNeural` **bằng tai** (mới chỉ so byte)
- tham số `rate` **bằng tai**
- service sống sót qua **reboot máy** (đã `enable`, chưa reboot lần nào)
- địa chỉ đã lưu bị cũ vì loa **đổi IP** → nhánh quét lại
- **chặn IP trong nginx** (đã đồng ý bật, hai dòng vẫn đang comment)
- **MCP elicitation** trên client thật — đang là phán đoán, chưa đo
- `./scripts/service.sh install` **chạy lại trong phiên này** (sẽ cắt dịch vụ của
  hai máy đang dùng)

---

## Đi tiếp

| Muốn gì | Đọc gì |
|---|---|
| Cài và chạy product này | `package/README.md` |
| Biết nó phải làm đúng những gì | `package/requirement.md` |
| Vận hành, chẩn lỗi hằng ngày | `package/user-manual.md` |
| Ràng buộc triển khai + khiếm khuyết còn mở | `package/technical-docs.md` |
| Kiến trúc và luồng xử lý | `docs/architecture.md` (trong repo) |
| Thiết kế bộ kiểm cho một product khác | `package/harness-spec.md` |
| Bộ kiểm và cách nó tự chứng minh | `package/eval/README.md` |
| Dựng lại một server tương đương từ đầu | `reproduction-prompt.md` |
