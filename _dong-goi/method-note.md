---
product: googlecast-mcp
loai: harness vận hành (MCP server chạy như systemd service)
ngay: 2026-08-20
transmission_level: L2 (đánh giá độc lập bởi method-note-evaluator-solo, 2026-08-20)
package: ./package/
---

# Method note — xây một MCP server điều khiển loa trong nhà

Ghi lại **cách nghĩ**, không phải cách chạy. Muốn cài và dùng thì đọc
`package/README.md`. Muốn dựng lại **đúng sản phẩm này** thì đọc
`reproduction-prompt.md` — file đó chỉ dùng để tái tạo googlecast-mcp, **không
dùng cho bài tương tự**; muốn làm sản phẩm khác thì dùng chính note này.

---

## Bài học 30 giây

1. **Yêu cầu đánh số, nói bằng hành vi, thì đối chiếu được từng dòng.** Cả sản
   phẩm này sinh ra từ ba dòng đánh số của người dùng. Lần đối chiếu đầu tiên ra
   kết quả 1/3 — biết được là 1/3 chính vì nó đối chiếu được.
2. **Việc gì máy tự chấm được thì đừng hỏi người. Việc gì phải cảm nhận thì đừng
   chấm hộ.** Chọn thư viện giao thức: tự quyết. Chọn giọng đọc: bắt buộc người
   dùng nghe rồi chọn.
3. **Nghe người dùng lặp lại "vẫn lỗi" là tín hiệu đổi hướng, không phải tín
   hiệu sửa tiếp.** Lần thứ hai nghe câu đó, hãy ngừng sửa và đi kiểm tra xem
   bản sửa đã thực sự được NẠP chưa.
4. **Sản phẩm tác động ra thế giới vật lý thì trạng thái phần mềm không phải
   bằng chứng.** Ở đây bốn thiết bị đều báo "đang phát" trong khi đang chồng
   tiếng lên nhau. Chỉ tai người mới biết.
5. **Hai mẫu giống nhau chưa đủ để kết luận nguyên nhân hệ thống.** Hai thiết bị
   cùng hỏng một kiểu từng khiến tôi kết luận sai là "do firmware".
6. **Một bộ test chưa bao giờ đỏ thì chưa chứng minh được gì.** Đưa lỗi cũ trở
   lại, xem nó có đỏ đúng chỗ không, rồi mới tin.

---

## Bước 1 — Ép yêu cầu mơ hồ thành danh sách đối chiếu được

**Nguyên tắc.** Đặc tả tốt không cần dài. Nó cần ba tính chất: đánh số, nói bằng
hành vi quan sát được, và mỗi dòng trả lời được đạt/không đạt. Có ba tính chất
đó thì tiến độ đo được; thiếu thì mọi cuộc trao đổi về "xong chưa" đều là cảm
tính.

**Việc làm cụ thể.** Người dùng đưa ba dòng. Việc của tôi không phải diễn giải
cho hay hơn, mà là đối chiếu từng dòng với code hiện có rồi báo con số thật.

**Prompt thật của người dùng** (nguyên văn, giữ nguyên lỗi gõ):

> hãy kiểm tra xem mcp này đúng yêu cầu không:
> 1. dò danh sách các google speaker trong mạng nội bộ sau đó lưu lại
> 2. gửi tin nhắn là text  tham số truyền vào mcp sau đó chuyển thanh âm thanh hỗ trợ tiếng việt sau đó phát lên speaker theo yêu cầu
> 3. nếu user không chọn speaker sẽ hỏi user xem phát ở speaker nào, hoặc tất cả

**Quyết định chốt.** Đối chiếu ra **1/3 đạt**. Báo đúng con số đó thay vì tô
hồng. Ba dòng này trở thành xương sống của cả dự án — chúng được chép nguyên văn
vào `package/requirement.md` và mỗi dòng được nở ra thành tiêu chí kiểm.

*Bài học chuyển giao được:* khi nhận một yêu cầu mơ hồ, việc đầu tiên là biến nó
thành danh sách đánh số mà chính người đặt hàng gật đầu, rồi mới đụng tới code.

---

## Bước 1.5 — Dựng khung chạy được trước, nối thiết bị thật sau

**Nguyên tắc.** Đừng gỡ hai loại khó cùng lúc. "Client có nối được vào server
không" và "thư viện có điều khiển được thiết bị không" là hai vấn đề độc lập;
nhập chúng làm một thì khi hỏng bạn không biết đang hỏng ở đâu. Dựng khung rỗng
chạy được trước, rồi mới cắm thiết bị thật vào.

**Việc làm cụ thể.** Khung tối thiểu gồm đúng hai công cụ: một cái *liệt kê*, một
cái *hành động*. Cả hai trả dữ liệu giả. Nối client thật vào, thấy nó gọi được,
mới bắt đầu thay dữ liệu giả bằng thiết bị thật.

Phần thưởng kèm theo: bộ dữ liệu giả đó chính là fixture cho bộ eval ở Bước 8 —
viết một lần, dùng hai chỗ.

**Prompt mẫu** *(tái dựng)*:

> Dựng một MCP server tối thiểu bằng [ngôn ngữ], dùng SDK chính thức, transport
> [stdio để thử tại chỗ]. Phơi đúng hai tool: `list_<thiết bị>` trả danh sách
> giả gồm 3 phần tử, và `<hành động>` chỉ ghi log rồi trả về thành công. **Chưa
> nối thư viện thiết bị thật.** Mỗi tool phải có docstring rõ ràng — đó là toàn
> bộ ngữ cảnh mô hình gọi tool có được. Rồi chỉ tôi cách nối client vào để xác
> nhận nó thấy đủ tool.

**Quyết định chốt.** Chỉ khi client thật đã gọi được tool giả mới thay bằng thư
viện thiết bị. Từ đó về sau, mọi lỗi kết nối chắc chắn nằm ở tầng thiết bị, vì
tầng giao thức đã được chứng minh xong.

🔧 Bộ 13 tool cuối cùng, cách chia lớp, và mô hình luồng: `package/harness-spec.md`.

---

## Bước 2 — Chọn thành phần bằng hai tiêu chuẩn khác nhau

**Nguyên tắc.** Đừng dùng một quy trình chọn cho mọi thành phần. Hỏi: *người
dùng có CẢM NHẬN trực tiếp được thứ này không?*

- **Không cảm nhận được** (thư viện giao thức, framework): chọn theo mức độ được
  bảo trì và độ phủ chức năng. Tự quyết. So sánh dài dòng ở đây chỉ tốn thời
  gian của người dùng.
- **Cảm nhận được** (giọng đọc, màu sắc, cách hành văn): **bắt buộc người dùng
  trải nghiệm rồi chọn**. Không chấm hộ. Tôi không nghe được hộ ai.

**Việc làm cụ thể.** Thư viện nói chuyện với thiết bị: chọn thẳng, không so sánh
gì, vì chỉ còn đúng một lựa chọn còn được bảo trì. Giọng đọc: dựng bốn phương án,
tự chấm phần đo được (có cần khoá API không, có cần trả phí không, cài đặt nặng
nhẹ ra sao, chạy được offline không), rồi để trống đúng một cột — "nghe có tự
nhiên không" — và đưa người dùng nghe.

**Prompt mẫu** *(tái dựng — không phải nguyên văn)*:

> Có 4 cách làm tiếng nói tiếng Việt: A, B, C, D. Tôi đã so phần đo được:
> [bảng: khoá API / chi phí / offline được không / độ nặng khi cài].
> Còn một tiêu chí tôi không tự chấm được là giọng nghe có tự nhiên không.
> Tôi sẽ tạo mỗi phương án một file mẫu cùng một câu, anh nghe rồi chọn.

**Quyết định chốt.** Người dùng nghe và chọn edge-tts. **Chỉ diễn ra một vòng** —
không lặp lại, không quay lại bàn nữa. Đó là dấu hiệu vòng chọn được đặt đúng
chỗ: hỏi một lần, hỏi đúng thứ chỉ người đó trả lời được.

🔧 Chi tiết kỹ thuật của lựa chọn (voice id, cache, cách ghim phiên bản):
`package/harness-spec.md` lớp Tool và `package/technical-docs.md`.

---

## Bước 3 — Với hành động có tác dụng phụ vật lý, mặc định phải là KHÔNG LÀM GÌ

**Nguyên tắc.** Phần mềm đoán sai thì hiện sai màn hình. Phần mềm điều khiển
thiết bị đoán sai thì làm ồn cả nhà lúc nửa đêm. Nên khi thiếu thông tin, mặc
định đúng là **im lặng và hỏi lại**, không phải "làm tất cho chắc".

**Việc làm cụ thể.** Yêu cầu #3 của người dùng nói "sẽ hỏi user". Có ba cách
hiện thực, và cách chọn quan trọng hơn cách viết:

1. Dùng cơ chế hỏi-lại có sẵn của giao thức → **loại**, vì nhiều client chưa hỗ
   trợ; ai dùng client đó sẽ kẹt cứng.
2. Không chọn thì phát ra tất cả loa → **loại**, tác dụng phụ vật lý.
3. Trả về **dữ liệu có cấu trúc** để chính trợ lý AI đang gọi công cụ hỏi lại
   người dùng → **chọn**. Chạy trên mọi client, không phụ thuộc tính năng nào.

**Prompt mẫu** *(tái dựng)*:

> Khi thiếu tham số chọn thiết bị, đừng đoán và đừng làm với tất cả. Trả về
> trạng thái `needs_speaker_selection` kèm danh sách thiết bị và một câu hướng
> dẫn để mô hình gọi tool hỏi lại người dùng. Tuyệt đối không phát gì.

**Quyết định chốt.** Và điều quan trọng hơn cả việc viết ra: **phải kiểm chứng
được rằng nó KHÔNG làm gì**. Trong bộ eval, tôi cắm hai "điệp viên" vào hàm tổng
hợp giọng và hàm gửi tới thiết bị, gọi lệnh mà không truyền loa, rồi khẳng định
cả hai điệp viên **chưa được gọi lần nào**.

*Bài học chuyển giao được:* với sản phẩm có tác dụng phụ, kiểm "việc gì đã KHÔNG
xảy ra" quan trọng hơn kiểm "việc gì đã xảy ra".

---

## Bước 4 — Nghe tín hiệu "vẫn lỗi" như một tín hiệu ĐỔI HƯỚNG

**Nguyên tắc.** Người dùng lặp lại gần như y nguyên một câu báo lỗi nghĩa là
vòng lặp sửa-thử của bạn đang chạy trong hư không. Đó là dữ liệu về **quy
trình**, không phải dữ liệu về **bug**.

⚠️ Đây là tín hiệu **cần nhận ra ở phía người dùng**. Nó không phải câu để người
đọc note này gõ vào đâu cả.

**Việc làm cụ thể.** Trong dự án này người dùng nói "vẫn báo lổi" hai lần liên
tiếp. Tôi đã **bỏ lỡ tín hiệu đó một vòng** và tiếp tục sửa code. Nguyên nhân
thật hoàn toàn khác: bản sửa chưa bao giờ được nạp — tiến trình cũ vẫn đang chạy
code cũ, và nó sống như vậy **ba ngày**.

Việc đúng phải làm khi nghe câu đó lần thứ hai — theo thứ tự:

1. Bản sửa đã thực sự được nạp vào tiến trình đang chạy chưa?
2. Người dùng và tôi có đang nhìn cùng một thứ không (cùng máy, cùng URL, cùng
   phiên bản)?
3. *Chỉ khi hai câu trên đã trả lời xong* mới quay lại đọc code.

**Prompt mẫu** *(tái dựng — tự nói với chính mình, hoặc nói với AI đang làm
việc cùng)*:

> Đây là lần thứ hai triệu chứng y hệt. Dừng sửa code. Hãy chứng minh cho tôi
> thấy tiến trình đang chạy THẬT SỰ chứa bản sửa: in ra dòng lệnh thật của tiến
> trình đó và dấu thời gian của file. Nếu không chứng minh được thì đó chính là
> vấn đề.

**Quyết định chốt.** Biến bài học thành cơ chế, đừng để nó là kinh nghiệm cá
nhân: lệnh xem trạng thái của dịch vụ bây giờ **luôn in ra dòng lệnh thật của
tiến trình đang chạy**, chứ không chỉ đọc file cấu hình trên đĩa. Câu hỏi từng
tốn ba ngày giờ trả lời trong một giây.

🔧 Cụ thể: `scripts/service.sh` đọc `/proc/<MainPID>/cmdline`; và dùng `restart`
tường minh thay vì `enable --now` — xem `package/technical-docs.md` mục "Bẫy vận
hành".

🔧 Còn **cách dựng** cả tầng vận hành đó — unit systemd, reverse proxy, chứng chỉ
TLS, các cờ dành cho client khắt khe — nằm ở `package/README.md` mục 7–9 và
`package/technical-docs.md`. Note này không chép lại, vì đó là phần thực thi,
không phải phần phương pháp.

*Bài học chuyển giao được:* mỗi lần mất nhiều giờ vì một câu hỏi, hãy nhúng câu
trả lời cho câu hỏi đó vào công cụ. Bài học nằm trong đầu thì mất; nằm trong
lệnh `status` thì còn.

---

## Bước 5 — Không tin trạng thái do chính hệ thống tự báo về mình

**Nguyên tắc.** Khi phần mềm chạm vào thế giới vật lý, **hiện thực là trọng
tài, không phải API**. Trạng thái "thành công" chỉ nói rằng lệnh đã được nhận,
không nói rằng điều bạn muốn đã xảy ra.

**Việc làm cụ thể — ca bệnh cụ thể.** Lệnh "phát ra tất cả loa" trả về: bốn
thiết bị, cả bốn `playing`. Nhìn API thì hoàn hảo. Thực tế: nhóm loa phát thông
qua chính các thành viên của nó, nên "tất cả" đã đẩy hai luồng vào cùng một loa
vật lý. Bằng chứng phát hiện được là hai bản ghi khác tên nhưng **cùng một địa
chỉ mạng**.

**Điều đáng sợ nhất của ca này:** không có bất kỳ tín hiệu tự động nào. Không
log lỗi, không cờ cảnh báo, không trạng thái bất thường. Chỉ có tai người.

**Prompt mẫu** *(tái dựng)*:

> Lệnh vừa rồi báo thành công trên cả 4 thiết bị. Trước khi tôi tin, hãy liệt kê
> địa chỉ mạng của từng thiết bị trong danh sách và chỉ ra có hai bản ghi nào
> trỏ về cùng một thiết bị vật lý không.

**Quyết định chốt.** "Tất cả" từ nay **loại nhóm ra**, chỉ gửi tới từng loa lẻ;
nhóm vẫn dùng được khi gọi đích danh tên. Và lỗi này được biến thành mục kiểm
thường trực trong bộ eval.

*Bài học chuyển giao được:* nền tảng nào có khái niệm "nhóm thiết bị" thì danh
sách "tất cả" **phải khử trùng lặp giữa nhóm và thành viên**. Áp dụng được cho
loa, đèn, máy in, thiết bị nhà thông minh — bất cứ đâu có nhóm lồng vào thực
thể.

---

## Bước 6 — Chẩn đoán: đừng suy ra nguyên nhân hệ thống từ hai mẫu

**Nguyên tắc.** Hai thứ cùng hỏng theo một kiểu là một **quan sát**, không phải
một **nguyên nhân**. Muốn kết luận nguyên nhân hệ thống thì phải có cơ chế giải
thích được, hoặc phải loại trừ được các nguyên nhân đơn giản hơn.

**Việc làm cụ thể — tôi đã sai như thế nào.** Hai thiết bị cùng loại đều không
kết nối được. Tôi kết luận: dòng thiết bị đó đã bỏ giao thức này ở bản firmware
mới. Kết luận nghe rất thuyết phục, và **sai**. Nguyên nhân thật: thiết bị bị
treo. Rút điện cắm lại là hết.

Vì sao tôi sai: hai thiết bị cùng model, mua cùng lúc, cập nhật cùng lúc, chạy
cùng thời lượng — chúng **không phải hai mẫu độc lập**, chúng gần như là một mẫu
được đếm hai lần.

**Prompt mẫu** *(tái dựng)*:

> Trước khi kết luận nguyên nhân nằm ở thiết bị hay ở nhà sản xuất, hãy kiểm tra
> tầng thấp nhất trước: cổng đó có thực sự mở không, kiểm bằng một công cụ mạng
> thô không dùng thư viện của dự án. Và nói cho tôi biết hai thiết bị này có
> thực sự độc lập với nhau không.

**Quyết định chốt.** Thứ tự chẩn đoán được ghi thành quy trình: kiểm cổng bằng
công cụ mạng thô **trước khi** nghi ngờ code, và trước khi nghi ngờ nhà sản
xuất. Đưa vào `package/user-manual.md` như một tình huống thường gặp.

🔧 Lệnh cụ thể và các mã lỗi đi kèm: `package/technical-docs.md` mục "Bẫy vận
hành".

---

## Bước 7 — Lớp hạ tầng cũng phải chẩn đoán, và nó hay im lặng

**Nguyên tắc.** Lỗi tệ nhất không phải lỗi to tiếng. Là lỗi **không phát ra tín
hiệu nào**: client treo mãi mà không báo gì, hoặc trình duyệt trả về một thông
báo trống rỗng. Với loại này, chi phí không nằm ở việc sửa mà ở việc **biết
đang sai ở đâu**.

**Việc làm cụ thể.** Người dùng dán vào bốn thông báo lỗi hạ tầng, không kèm
phân tích nào — toàn bộ việc chẩn đoán thuộc về AI. Mỗi cái hoá ra là một tầng
khác nhau: lớp bảo vệ của thư viện, lớp đệm của proxy, luật đặt tên miền, và cơ
chế bảo vệ của trình duyệt.

Điểm chung của cả bốn, và đó mới là bài học: **thông báo lỗi mô tả triệu chứng
ở tầng ngoài cùng, hiếm khi chỉ đúng tầng gây ra**. Nên cách làm là dựng lại
đường đi của một request và hỏi từng chặng "chặng này có thể từ chối vì lý do
gì".

Có một cái đặc biệt đáng nhớ vì nó là **ngõ cụt tuyệt đối**, không phải bug:
người dùng đã tạo một tên miền chứa dấu gạch dưới. Không tổ chức cấp chứng chỉ
nào cấp chứng chỉ cho tên đó, mà client thì bắt buộc dùng kết nối bảo mật. Không
có cách sửa nào ở phía code hết — phải đổi tên miền.

**Prompt mẫu** *(tái dựng)*:

> Đây là thông báo lỗi ở phía client. Đừng sửa gì vội. Hãy vẽ lại đường đi của
> một request từ client tới tiến trình cuối cùng, liệt kê mọi chặng có quyền từ
> chối nó, rồi với mỗi chặng nói xem thông báo này có thể do chặng đó sinh ra
> không.

**Quyết định chốt.** Nới lớp bảo vệ vừa đủ cho các địa chỉ hợp lệ, **không tắt
nó** — tắt là mở cửa cho trang web bất kỳ tấn công máy chủ trong mạng nội bộ.
Nguyên tắc chung: gặp cơ chế bảo mật cản đường, hãy nới đúng chỗ cần nới, đừng
gỡ cả cơ chế.

🔧 Bốn ca cụ thể, mã lỗi, và cấu hình đã sửa: `package/technical-docs.md` các
mục "Allowlist", "CORS", "Reverse proxy / DNS", và mục Troubleshooting ở
`README.md` gốc.

---

## Bước 8 — Đóng gói: bốn phần mỏng, và một bộ eval đã từng đỏ

**Nguyên tắc.** Product chưa cài được bởi người lạ thì chưa phải product.
Phép thử: *người lạ, máy sạch, chỉ đọc một file — cài và chạy được không?*

Và: tài liệu đóng gói **không được chép lại tài liệu đang sống**. Chép là sáu
tháng nữa có hai bản mâu thuẫn, người đọc không biết tin bản nào. Bốn phần bàn
giao phải mỏng, mỗi phần một mục đích, và **trỏ sang nguồn** cho chi tiết:

| File | Trả lời câu hỏi |
|---|---|
| `package/README.md` | Người lạ trên máy sạch cài thế nào? (file phải qua phép thử trên) |
| `package/requirement.md` | Yêu cầu gốc là gì, và căn cứ nào nói là đã đạt? |
| `package/technical-docs.md` | Đem ra chạy thật thì vấp ở đâu? |
| `package/user-manual.md` | Dùng hằng ngày thế nào, hỏng thì làm gì? |

(Riêng nhánh harness có thêm `package/harness-spec.md` mô tả 5 lớp, và
`package/eval/`.)

**Việc làm cụ thể.** Viết hướng dẫn cài từ số 0 — kể cả bước cài công cụ quản lý
môi trường, vì máy sạch chưa chắc có. Rồi **chạy lại từng lệnh đã viết** để chắc
nó chạy được đúng như đã viết. Nêu rõ điều kiện tiên quyết không thể bỏ, và nói
thẳng phần còn hở về bảo mật.

Về bộ eval, hai luật đáng mang đi nơi khác:

1. **Chia tầng theo tác dụng phụ.** Tầng mặc định phải không gây ra bất cứ hậu
   quả nào — không mạng, không tiếng, chạy được ở mọi máy vào lúc hai giờ sáng.
   Tầng chạm vào thực tế nằm sau một cờ phải bật tay. *Một bộ test mà không ai
   dám chạy thì bằng không có test.*
2. **Kiểm ngược.** Đưa một lỗi đã biết trở lại, xác nhận eval **đỏ đúng chỗ**,
   rồi khôi phục và xác nhận xanh lại. Eval chưa từng đỏ là eval chưa chứng minh
   được gì.

**Prompt mẫu** *(tái dựng)*:

> Hãy đưa lỗi [mô tả lỗi cũ đã sửa] trở lại đúng như trước khi sửa, chạy eval,
> và cho tôi xem những mục nào chuyển sang đỏ. Sau đó khôi phục và chạy lại.
> Ghi cả quy trình lẫn kết quả vào README của eval để người sau lặp lại được.

**Quyết định chốt.** Làm đúng như vậy, và kiểm ngược đã trả về một thứ không ai
ngờ: **một mục kiểm vẫn xanh trong khi lỗi đang tồn tại** — nó so trùng theo tên
nên mù trước loại trùng lặp đang xảy ra. Thay vì lặng lẽ xoá, tôi ghi lại nó
trong `package/eval/README.md`. Đó chính là giá trị của kiểm ngược: nó lộ ra
những mục kiểm đang tạo **cảm giác an toàn giả**.

---

## Bước 9 — Đọc tín hiệu từ người dùng

**Nguyên tắc.** Cách người dùng viết cho bạn chứa nhiều thông tin ngang với nội
dung họ viết.

Bốn tín hiệu đã gặp trong dự án này:

| Tín hiệu | Nghĩa là gì | Việc phải làm |
|---|---|---|
| Yêu cầu được đánh số, nói bằng hành vi | Đây là đặc tả thật | Đối chiếu từng dòng, báo con số thật |
| Dán lỗi vào, không phân tích gì | Việc chẩn đoán hoàn toàn thuộc về bạn | Đừng hỏi lại "anh nghĩ do đâu" — tự dựng lại đường đi |
| Lặp lại y nguyên câu báo lỗi | Vòng lặp sửa-thử đang chạy trong hư không | Dừng sửa. Kiểm bản sửa đã được nạp chưa (Bước 4) |
| Hai lần mô tả trái ngược về **cùng một thiết bị** | Có thể là lỗi thiết bị, có thể là hồi quy code | Phải có **lịch sử đo** mới phân định được |

Dòng cuối đáng nói thêm. Ở dự án này, cùng một thiết bị được xác nhận "chạy tốt"
rồi sau đó bị báo "chỉ nháy sáng rồi tắt". Nếu không lưu lại các phép đo có mốc
thời gian, hai lời chứng đó chỉ mâu thuẫn nhau và không kết luận được gì.
**Lịch sử đo là thứ biến hai lời kể mâu thuẫn thành một chẩn đoán.** Đó cũng là
lý do bảng "Cách đã kiểm chứng" bên dưới ghi cả số lần lẫn điều kiện.

Tín hiệu thứ năm, ngắn: giữa dự án người dùng hỏi một câu lạc đề hoàn toàn, và
nó hoá ra là việc **gấp nhất phiên** (lộ ra một cơ chế đang âm thầm thu thập mật
khẩu với quyền cao nhất). Đánh giá mức khẩn theo nội dung, đừng theo phạm vi dự
án.

---

## Cách đã kiểm chứng

Ghi trung thực. Chỗ chưa thử ghi rõ **CHƯA THỬ**, không suy đoán.

| Kịch bản | Số lần | Biên / điều kiện | Kết quả |
|---|---|---|---|
| Nói ra loa Home Mini | 1 | bình thường | báo `playing`; người dùng xác nhận **nghe được bằng tai** |
| Nói ra Nest Hub | **5 lần, rải qua 2 ngày** | thiết bị treo, rồi restart | 3 lần đầu **thất bại** (timeout, cổng 8009 từ chối); sau restart: 1 lần tốt + 3 clip đo |
| Đo thời lượng phát | **3 clip** (2.09 / 4.27 / 7.10 s) | độ dài khác nhau | cả 3 phát đủ độ dài tới trạng thái kết thúc; log HTTP xác nhận thiết bị **có tải file** (mã 200) |
| Thương lượng phiên bản giao thức | **3 phiên bản** | client cũ và mới | cả 3 trả đúng phiên bản |
| Client thật qua tên miền https | 1 | qua proxy + TLS | kết nối được, đủ 13 tool, liệt kê ra 4 loa |
| Client thật qua địa chỉ LAN trực tiếp | 1 | không qua proxy | như trên |
| Mô phỏng client chạy trong trình duyệt | 1 | có kiểm tra CORS | preflight qua, header đúng, khởi tạo thành công, đủ 13 tool |
| Chế độ dành cho client khắt khe | 1 | không dùng session id | hoạt động đúng |
| Dò thiết bị và lọc loa | 2 | mạng thật, 8 thiết bị | tách đúng 4 loa / 4 thiết bị hình ảnh |
| **"Tất cả" — trước và sau khi sửa** | **2 lần** | 4 loa song song | trước: cả 4 báo `playing` nhưng **chồng luồng**; sau: 3 loa lẻ, không chồng |
| Nhiều loa liệt kê cách phẩy | 1 | 2 loa | cả 2 phát |
| Cô lập lỗi: 1 loa thật + 1 tên không tồn tại | 1 | có phần tử hỏng | loa thật vẫn phát, phần tử hỏng báo lỗi riêng, tổng thể vẫn `ok` |
| Nhóm loa gọi đích danh, sau khi sửa | 1 | — | phát bình thường — nhóm vẫn dùng được |
| **Eval tầng offline** | nhiều lần, phiên này | không loa, không tiếng, không mạng | **43/43 pass, exit 0** |
| **Eval tầng online** | 1, phiên này | có internet, vẫn im lặng | **45/45 pass, exit 0** |
| **Kiểm ngược eval** (đưa lỗi cũ trở lại) | 1, phiên này | lỗi "tất cả" chồng nhóm | **40/43, exit 1**, đỏ đúng 3 mục về "tất cả"; khôi phục → **43/43, exit 0** |
| **Eval tầng hardware** | 2 lần, 2 phiên khác nhau | cast thật ra loa | phiên trước **37/37**; phiên này **48/48, exit 0** sau khi xin phép người dùng |

### Biên và điều kiện xấu đã quan sát được (thật, không dựng giả)

- Thiết bị thấy được qua mDNS, ping được, nhưng cổng điều khiển từ chối → treo
  rồi timeout.
- mDNS sót một thiết bị đã lưu → lỗi "không tìm thấy" tự mâu thuẫn, vì nó liệt
  kê chính thiết bị đó trong danh sách đã biết.
- Nguồn gọi ngoài danh sách cho phép → bị từ chối; tên máy chủ không tin cậy →
  bị từ chối. Hai loại từ chối khác nhau, mã khác nhau.
- Mở địa chỉ dịch vụ bằng trình duyệt → báo không chấp nhận được. **Đúng đặc
  tả, không phải lỗi.**
- Trình duyệt gửi preflight khi chưa bật CORS → bị chặn, và JS chỉ thấy một
  thông báo trống rỗng.
- Không truyền tham số chọn loa → trả về yêu-cầu-chọn-loa, **không phát gì**.
- Cài lại dịch vụ khi nó đang chạy → tiến trình **không đổi**.
- "Tất cả" gồm cả nhóm lẫn thành viên → chồng luồng, mà API vẫn báo `playing`.

### CHƯA THỬ

- Giọng nam.
- Tham số chỉnh tốc độ đọc.
- Dịch vụ sống sót qua khởi động lại máy (đã bật tự khởi động, nhưng **chưa
  reboot lần nào**).
- Nhánh xử lý khi địa chỉ đã lưu bị cũ (thiết bị đổi IP).
- Chặn truy cập theo IP ở proxy (đã đồng ý bật nhưng **chưa bật**).

---

## Còn hở — không tô hồng

- **Không có xác thực ở tầng ứng dụng.** Tên miền phân giải công khai ra
  internet, nghĩa là ai biết địa chỉ cũng phát được tiếng trong nhà.
- **Mặt phơi nhiễm thứ hai**: cổng phục vụ file audio mở trên mọi interface,
  không xác thực, phục vụ nguyên thư mục cache. Biện pháp chặn IP ở proxy chỉ
  che cổng chính, **không chạm tới cổng này**.
- Cache tiếng nói tăng vô hạn, chưa dọn.
- Chưa khôi phục âm lượng / nội dung đang phát sau khi chen thông báo vào.
- Không có health check, không có metric.
