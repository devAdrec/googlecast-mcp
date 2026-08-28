---
product: googlecast-mcp
layer: feedback
product_repo: https://github.com/devAdrec/googlecast-mcp
spec_version: "dong-goi-solo-agent v1.9 (sinh từ vault dong-goi-product v1.9)"
session: 2026-08-28
registry: "[[packages/googlecast-mcp]]"
---

# Phản hồi quy trình đóng gói — từ phiên v1.9

Gửi về người bảo trì bản chuẩn trong vault Adrec. Bản solo **không được tự
sửa**; những đề xuất dưới đây phải vá vào bản vault rồi tái sinh bản solo.

Ghi thành file (không chỉ nói trong chat) vì phản hồi chỉ nằm trong chat là bay
hơi theo phiên — chính luật này ở v1.9 đã cứu được danh sách dưới đây.

---

## Cái gì ở v1.9 đã chứng minh giá trị trong phiên này

Không phải điều nào cũng cần sửa. Ghi lại phần đã trả công, để không ai gỡ nhầm.

1. **Bốn trạng thái DoD** (thay vì ba) là cải tiến đúng. Phiên này có **bốn**
   bước rơi vào trạng thái 2 — *không chạy lại được nhưng đã kiểm bằng đường
   khác*: `service.sh install` (cài đè sẽ cắt dịch vụ hai máy đang dùng),
   `claude mcp add`, và ba nhánh proxy/Desktop/CORS. Với thang ba trạng thái cũ
   thì tất cả đều bị dồn vào "thiếu sót", làm báo cáo trông tệ hơn thực tế và
   che mất bốn bằng chứng thay thế hợp lệ.

2. **Thi hành chi phí kiểm ngược** là cải tiến đắt giá nhất. Lượt đầy đủ:
   **60 lỗi gieo, 56 giây** — so với 12 phút của cách "mỗi lỗi gieo × toàn bộ
   bài kiểm". Nhờ rẻ mà nó được chạy nhiều lần trong phiên thay vì chạy một lần
   lấy lệ.

3. **Ba nhánh định đoạt "lẽ-ra-đỏ-mà-xanh"** đã dùng thật: một ca **kỳ vọng
   sai** (sniff mp3 so 3 byte với mẫu 2 byte — sửa theo ISO/IEC 11172-3, có
   trích nguồn, không nới cho xanh) và một ca **test giả** (bài kiểm treo vì
   `shutdown()` chờ một vòng lặp chưa từng khởi động). Không có nhánh 2 thì ca
   đầu rất dễ bị "nới cho xanh".

4. **Gieo vào bản sao trong thư mục tạm** khiến `git status -- src …` sạch
   trơn suốt phiên. Hoàn nguyên là hệ quả của cấu trúc, đúng như thiết kế.

5. **Quét bắc cầu trước khi giao evaluator** tiết kiệm đúng một vòng như dự
   đoán: 51 tham chiếu, tất cả tồn tại trước khi giao, và người chấm tự kiểm
   được cả neo sâu (`package/README.md:155`, `package/eval/README.md:137`) lẫn
   một mục eval cụ thể — không mất vòng nào cho "link chết" tự tan.

6. **Triage từng lỗ hổng kể cả khi đạt L2** đã bắt được **Đ7 dưới đây**. Nếu
   luật chỉ yêu cầu "đạt L2 thì thôi" thì lỗ hổng lớn nhất của phiên đã rơi im
   lặng — nó không chặn L2, nó chỉ sai.

---

## Đề xuất

### Đ1 — Thêm dạng test giả thứ năm: **dọn dẹp treo**

**Quan sát.** Ca gieo lỗi `media_never_starts_thread` làm cả bộ kiểm ngược đứng
**180 giây**. Chỗ treo **không phải khẳng định** mà là dọn dẹp:
`ThreadingHTTPServer.shutdown()` chờ vòng `serve_forever` thoát, mà lỗi gieo
làm vòng đó không bao giờ khởi động.

**Vì sao đáng thành luật.** Luật hiện có phủ *sập giữa chừng* (mục đếm X/Y),
nhưng **treo** thì X/Y không cứu được — không có mục nào kết thúc để mà đếm.
Và nó ẩn hơn sập: không có ngoại lệ, không có log, chỉ là im lặng.

**Đề xuất chữ.** Thêm vào B5 mục (2), sau *sập giữa chừng*:

> **treo ở dọn dẹp** → *"xanh phải là xanh trong thời gian hữu hạn"*: mọi lời
> gọi dọn dẹp chạm tới tài nguyên của sản phẩm (đóng server, join luồng, tắt
> tiến trình con) phải có **hạn thời gian**, và bộ kiểm ngược phải coi **quá
> hạn là ĐỎ**, không phải ERROR hạ tầng. Sản phẩm hỏng thường hỏng ở đúng
> đường dọn dẹp.

### Đ2 — Lỗi gieo không áp được phải là ERROR, nói rõ trong spec

**Quan sát.** Một lỗi gieo sai thụt lề khớp **0 lần**. Bộ kiểm ngược ở đây báo
ERROR, nhưng đó là do người viết nghĩ ra, **spec không yêu cầu**.

**Vì sao nguy hiểm.** Một lỗi gieo không áp được mà bị bỏ qua trông **y hệt**
một lỗi gieo đã đạt. Đúng dạng "khớp 0 case không được báo ĐẠT" mà spec đã cấm
ở tầng mục eval, nhưng chưa cấm ở tầng lỗi gieo.

**Đề xuất chữ.** Trong B5 mục (1), thêm: *đoạn mã gốc của mỗi lỗi gieo phải
xuất hiện **đúng một lần**; 0 lần hoặc nhiều hơn 1 lần đều là ERROR chặn lượt
chạy, kèm thông điệp "mã sản phẩm đã đổi — phải cập nhật lỗi gieo".*

### Đ3 — Nói rõ "đối chứng đi qua mã thực thi" nghĩa là mã **đang được eval
chạy tới**

**Quan sát.** v1.9 đã nói đối chứng phải đi qua mã thực thi và phải được ít
nhất một mục eval thực thi. Nhưng lúc viết vẫn dễ nhầm: đổi tên một biến trong
một hàm mà bài kiểm **không mục nào gọi tới** thì vẫn "là mã thực thi" theo
nghĩa thông thường, mà chẳng kiểm được gì.

**Đề xuất chữ.** Yêu cầu mỗi đối chứng khai báo **danh sách mục eval sẽ chạy**
(ở đây là trường `run_items`), và bộ kiểm ngược **chạy đúng danh sách đó** —
danh sách rỗng là lỗi cấu hình. Như vậy "được ít nhất một mục eval thực thi"
trở thành thứ **cưỡng chế được**, không còn là lời hứa.

### Đ4 — Chốt chặn "gọi được tool" cho dạng MCP nên nói rõ là **hai transport**

**Quan sát.** Dạng MCP trong spec định nghĩa DoD là *gọi được tool*. Sản phẩm
này phục vụ **cả stdio lẫn HTTP**, và hai đường đi qua mã khác nhau
(`mcp.run(transport=...)` rẽ nhánh, tầng an ninh vận chuyển chỉ áp cho HTTP).
Chứng minh một đường không suy ra được đường kia.

**Đề xuất chữ.** Trong định nghĩa dạng **MCP**: *nếu product khai báo nhiều
transport thì DoD phải chứng minh **từng transport được khai báo**, hoặc ghi rõ
transport nào chưa chứng minh.*

### Đ5 — "Quan sát trong phiên" nên khuyến khích cả quan sát về **môi trường**

**Quan sát.** Luật v1.9 nói ngõ cụt tái hiện và số đo lại trong phiên là dữ liệu
hợp lệ. Phiên này thu được thêm một loại thứ ba, không thuộc hai loại đó nhưng
đáng giá ngang: **cổng audio 8766 mở lười** — `ss` cho thấy service thật chỉ
đang nghe 8765, vì chưa `say` lần nào kể từ lần khởi động gần nhất. Đây là một
sự thật **về bề mặt tấn công** mà không lần đọc mã nào lộ ra, và nó sửa lại
cách mô tả điểm hở số 2 trong technical-docs.

**Đề xuất chữ.** Mở rộng thành: *ngõ cụt tái hiện · số đo lại · **quan sát về
trạng thái thật của môi trường triển khai** (cổng đang mở, tiến trình đang
chạy, cấu hình thực tế) — đều là dữ liệu hợp lệ, ghi kèm nguồn.*

### Đ6 — Nhỏ: nêu ví dụ tự-giết-shell của `pkill -f`

`pkill -f "<mẫu>"` khớp luôn dòng lệnh bash đang chạy và giết chính shell đó
(exit 144). Ngõ cụt này **đã tái hiện sống** trong phiên. Nó thuộc họ "công cụ
tự nuốt mình" cùng với thay-thế-đệ-quy mà v1.9 đã cấm. Đề xuất ghi cạnh nhau
trong cùng một mục, kèm cách thoát: lấy PID từ `ss -ltnp` rồi `kill` theo PID.

---

### Đ7 — Thiếu luật cho **phép đo lặp lại mà bản thân nó không hoàn tác được**

**Đây là đề xuất quan trọng nhất trong danh sách.** Nó không đến từ phiên đóng
gói mà từ **người đọc sạch chấm method note** — nghĩa là bộ luật đã tự che mắt
mình, phải có người ngoài mới thấy.

**Quan sát.** v1.9 có hai luật đúng, đứng riêng thì không sao:

- *tác dụng phụ không hoàn tác được thì mặc định KHÔNG LÀM* (tinh thần của
  tầng tác-dụng-phụ, B5 mục 6);
- *mỗi lần vá phải đo lại bằng cùng một kịch bản* (B3, mục "Cách đã kiểm
  chứng" đòi cột *số lần*, và cấm ghi "nhiều").

Chúng **va nhau khi chính phép đo là hành động không hoàn tác được**. Ở product
này, kịch bản đo là "dồn 6 yêu cầu song song" × 3 lần vá = 18 lần loa kêu.
Chuyển sang một product khác — máy in nhãn — đúng bộ luật đó bắt in **18 tờ
giấy thật**. Cột *số lần* trong bảng kiểm chứng khi ấy **thưởng cho việc chạy
thật nhiều lần**, mà không có luật nào bắt dừng lại hỏi *lần này có cần chạy
thật không*.

**Vì sao luật hiện có không đủ.** Tầng tác-dụng-phụ (`--hardware` opt-in, xin
phép trước) quản **bài kiểm**. Nó **không** quản **vòng lặp chẩn đoán** — giai
đoạn đo đi đo lại lúc đang truy nguyên nhân, vốn nằm ở B3 chứ không ở B5. Đó
đúng là chỗ số lần chạy tăng nhanh nhất.

**Đề xuất chữ.** Thêm vào B3, ngay tại mục "Cách đã kiểm chứng":

> Nếu **bản thân phép đo** có tác dụng phụ không hoàn tác được, kịch bản đo
> phải nêu rõ nó chạy ở **tầng nào**, theo thứ tự ưu tiên:
> **(1) bản giả** mang *cùng đặc tính gây lỗi* (vd "từ chối kết nối đồng
> thời") — mặc định, và phải đủ để phân định các giả thuyết;
> **(2) thiết bị thật** chỉ để **xác nhận lần cuối**, không để dò tìm, và phải
> xin phép;
> **(3) giảm N** xuống mức nhỏ nhất còn phân biệt được hai giả thuyết, rồi
> **ghi N vào cột "số lần"** — giảm âm thầm cũng là một dạng dựng số.
> Cột "số lần" tăng mà không ai hỏi *lần này có cần chạy thật không* là dấu
> hiệu đang vi phạm.

Đã áp trước vào note của product này (mục *"Khi chính phép đo là hành động
không hoàn tác được"* ở Bước 5), nhưng đó là vá cục bộ — **bản chuẩn nên có
luật này**, vì product tiếp theo có thể không may mắn có một bản giả rẻ như
`edge_tts.Communicate`.

## Không đề xuất

- **Không** đề xuất nới luật "đếm đủ trước khi đếm xanh". Nó bắt được lỗi thật
  trong phiên này và chi phí bằng không.
- **Không** đề xuất bỏ tầng `--hardware` dù phiên này không chạy nó. Lịch sử
  cho thấy năm phiên đầu **lần nào nó cũng lộ một lỗi của chính bài kiểm** —
  giá trị của nó nằm ở chỗ đó, không phải ở chỗ xác nhận sản phẩm chạy.
