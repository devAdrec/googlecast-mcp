# Phản hồi cho quy trình đóng gói (bản solo v1.8)

Chuyển về người bảo trì bản gốc trong vault Adrec để vá bản chuẩn rồi tái sinh
bản solo. **Không sửa file quy trình từ phía phiên này.**

Nguồn: phiên đóng gói `googlecast-mcp` ngày 2026-08-27, chạy bản
`dong-goi-solo-agent` sinh từ vault v1.8.

---

## 1. Chi phí chạy kiểm ngược tăng theo tích số, không theo tổng

**Quan sát.** `reverse-check.py` chạy trọn bộ eval cho **mỗi** lỗi gieo. Với 68
lỗi gieo × ~10 giây một lượt eval, một lần kiểm ngược mất khoảng **12 phút**.
Luật "phủ ngược đầy đủ" (mọi mục eval phải nằm trong ≥1 danh sách kỳ-vọng-đỏ)
đẩy số lỗi gieo lên xấp xỉ số mục eval, nên chi phí là **số mục × thời gian
một lượt eval** — tích số, không phải tổng.

**Vì sao đáng vá.** Bộ kiểm mà chạy mất 12 phút thì sẽ không được chạy thường
xuyên, và chính spec đã nói "bài kiểm không ai dám chạy thì bằng không có".
Luật đúng, nhưng cách thi hành ngây thơ tự phá luật khác của mình.

**Đề xuất.** Thêm vào B5 một câu về cách thi hành: cho phép kiểm ngược **chỉ
chạy tập mục liên quan** (`--only <danh sách id>`) trong lượt thường, và giữ
lượt chạy đầy đủ cho mốc đóng gói. Điều kiện: lượt rút gọn vẫn phải in "đã
chạy X/Y" của **cả hai** chiều — số mục eval đã chạy và số lỗi gieo đã chạy —
để rút gọn không hoá trang thành đầy đủ.

## 2. "Đối chứng vô hại" cần một định nghĩa chặt hơn

**Quan sát.** Spec đòi ≥1 đối chứng kỳ-vọng-XANH, nhưng không nói *vô hại tới
mức nào*. Thêm một dòng chú thích là vô hại tới mức không kiểm được gì: nó
không đi qua bất kỳ nhánh nào. Phải cố ý chọn một thay đổi **có sửa mã thật
đang chạy** mà không đổi hành vi (ví dụ đổi tên biến cục bộ trong một vòng lặp
đang được nhiều mục eval đi qua) thì đối chứng mới có sức nặng.

**Đề xuất.** Trong B5 mục (1), đổi "kèm ≥1 đối chứng vô hại kỳ-vọng-XANH"
thành: "kèm ≥1 đối chứng vô hại **đi qua mã đang được ít nhất một mục eval
thực thi** (đổi tên biến cục bộ, tách biểu thức) — chú thích và khoảng trắng
không tính".

## 3. Thiếu một dạng TEST GIẢ đã gặp thật: vá bằng cách gán đè lên chính thứ đang gọi

**Quan sát.** Spec liệt kê ba dạng test giả (so kích thước / sập giữa chừng /
không chạm sản phẩm). Phiên này dẫm phải một dạng thứ tư: để rút ngắn thời gian
chờ giữa các lần thử lại, bài kiểm gán `module.sleep = lambda: sleep(...)` —
nhưng `module.asyncio` và `asyncio` của bài kiểm là **cùng một đối tượng
module**, nên hàm tự gọi chính nó. Lỗi hiện ra ở ba mục chẳng liên quan, dưới
dạng vừa FAIL vừa ERROR, và mất một vòng chẩn đoán mới thấy.

Đây họ hàng gần với luật "vệ sinh mock" nhưng khác về cơ chế: không phải quên
khôi phục, mà là **thay thế đệ quy** — bản thay thế trỏ về chính chỗ nó vừa
thay.

**Đề xuất.** Thêm vào B5 mục (5): "cấm gán đè lên chính hàm mà bản thay thế sẽ
gọi lại — bọc bằng một lớp proxy, đừng gán đè; module là đối tượng dùng chung,
`a.f = lambda: a.f()` là vòng lặp vô hạn chứ không phải bản vá".

## 4. Ba trạng thái DoD nên có thêm một ô "kiểm chứng bằng đường khác"

**Quan sát.** v1.8 cho ba trạng thái: đã-chạy-lại / không-chạy-lại-được /
chưa-chạy. Phiên này gặp một bước rơi vào khoảng giữa: `service.sh install`
không chạy lại được (cài đè cắt dịch vụ đang phục vụ hai máy khác), **nhưng**
mục tiêu mà nó phục vụ — "gọi được tool" — vẫn kiểm chứng được **bằng một
đường khác** (dựng một tiến trình mới ở cổng rỗi, initialize + tools/list; và
gọi tool thật qua client đã đăng ký).

Trạng thái "không-chạy-lại-được" hiện gộp chung hai tình huống rất khác nhau:
*bước này không kiểm chứng được gì cả* và *bước này kiểm chứng được bằng đường
khác, đây là bằng chứng*. Gộp lại làm báo cáo DoD yếu hơn thực tế.

**Đề xuất.** Tách trạng thái giữa thành hai: **không-chạy-lại-được-nhưng-đã-
kiểm-bằng-đường-khác** (+ mô tả đường thay thế + output) và
**không-chạy-lại-được-và-chưa-có-đường-nào** (= vẫn là thiếu sót, chỉ khác là
có lý do chính đáng).

## 5. Nên nói rõ: tài liệu gói được phép ghi lại NGÕ CỤT gặp trong chính phiên đóng gói

**Quan sát.** Phiên này tái hiện sống ngõ cụt "`pkill -f <mẫu>` khớp luôn lệnh
bash đang chạy → tự giết shell (exit 144)" — đúng lúc dọn tiến trình thử
nghiệm. Nó nằm sẵn trong gói bàn giao như một bài học từ phiên gốc, và vừa
được xác nhận lại.

Spec không cấm, nhưng cũng không nhắc, nên dễ bị bỏ qua: bằng chứng thu được
**trong lúc đóng gói** cũng là dữ liệu thật của product, không phải nhiễu.

**Đề xuất.** Thêm một câu vào B6: "quan sát thu được trong chính phiên đóng gói
(ngõ cụt tái hiện, con số đo lại được) là dữ liệu hợp lệ — ghi vào bảng 'cách
đã kiểm chứng' với ghi chú nguồn, đừng bỏ".

## 6. Tiền điều kiện B4 nên quét cả đường dẫn *bên trong* file được trỏ tới

**Quan sát.** v1.8 đã thêm "quét đường dẫn note trỏ tới, đảm bảo mọi file đã
tồn tại trước khi giao evaluator" — tốt, và phiên này áp dụng được ngay. Nhưng
method note trỏ sang `package/README.md`, mà file đó lại trỏ tiếp sang
`eval/README.md` và `docs/architecture.md`. Evaluator đọc theo chuỗi trỏ và có
thể gặp mắt xích chết ở tầng hai.

**Đề xuất.** Đổi tiền điều kiện B4 thành quét **bắc cầu một tầng**: mọi đường
dẫn trong note, **và** mọi đường dẫn trong các file mà note trỏ tới.
