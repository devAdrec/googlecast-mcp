---
product: googlecast-mcp
layer: output
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
harness_kind: vận-hành
registry: "[[packages/googlecast-mcp]]"
---

# Harness — năm lớp

googlecast-mcp là **harness vận hành**: cùng đầu vào cho ra cùng kết quả, nên
eval chấm **pass/fail** chứ không chấm chất lượng. Trọng số nghiêng về lớp Tool
và lớp Execution — chỗ mọi ngõ cụt thật đã xảy ra.

## 1. Context — thứ mô hình được thấy

| Nguồn | Nội dung |
|---|---|
| Danh mục 13 tool | tên + mô tả + lược đồ tham số |
| Mô tả tool | mang cả luật hành vi: *"Omit to be asked which speaker to use"* |
| `list_speakers` | danh sách loa thật, đã lọc thiết bị hình ảnh |
| `needs_speaker_selection` | trạng thái + danh sách loa + câu hướng dẫn hỏi lại |

**Điểm quan trọng nhất của lớp này:** khi thiếu `target`, sản phẩm KHÔNG cố tự
đoán. Nó trả về **ngữ cảnh để mô hình đi hỏi người**. Mô tả tool là chỗ luật đó
được truyền đi — mất mô tả là mất luật, nên eval có mục
`tool_descriptions_are_present`.

Trọng số: **trung bình**. Không có mô tả thì LLM chọn sai tool, nhưng sai lệch
không âm thầm.

## 2. Tool — mặt tiếp xúc

13 tool, chia ba nhóm:

- **Dò tìm**: `discover_devices`, `list_devices`, `list_speakers`
- **Nói**: `say` (thứ duy nhất chỉ product này mới có)
- **Điều khiển Cast chung**: `get_status`, `play_media`, `play`, `pause`,
  `stop`, `seek`, `set_volume`, `set_muted`, `quit_app`

Hợp đồng bắt buộc:

| Hợp đồng | Vì sao | Mục eval |
|---|---|---|
| đủ đúng 13 tool | client đếm tool để biết đã nối đúng server | `server_exposes_thirteen_tools` |
| `say` thiếu `target` → không phát gì | tác dụng phụ vật lý, không hoàn tác | `say_without_choice_plays_nothing` |
| `all` bỏ nhóm loa | tránh chồng luồng | `select_all_excludes_groups` |
| một loa hỏng không kéo đổ lượt phát | mạng gia đình luôn có thiết bị ngủ | `say_isolates_one_broken_speaker` |
| âm lượng bị kẹp 0.0–1.0 | tránh gửi giá trị vô lý xuống phần cứng | `manager_volume_is_clamped` |

Trọng số: **cao**.

## 3. Execution — thứ thật sự chạy

Bốn ràng buộc thời gian chạy, mỗi cái đến từ một lần vấp thật:

1. **Tuần tự hoá render TTS, khoá theo TỪNG vòng lặp.** Dịch vụ từ chối kết nối
   đồng thời; và một khoá mức module sẽ tự gắn vào vòng lặp đầu tiên có tranh
   chấp rồi từ chối mọi vòng lặp sau.
2. **Server phải bind `0.0.0.0` nhưng quảng bá `lan_ip()`.** Hai địa chỉ khác
   nhau; lẫn lộn là loa không tải được file.
3. **Bảo vệ DNS-rebinding phải nới cho cả host trần lẫn origin https.** Proxy ở
   cổng mặc định gửi Host không kèm `:port`.
4. **CORS phải expose `Mcp-Session-Id`.** Không expose thì trình duyệt không
   duy trì được phiên và chỉ báo `Failed to fetch`.

Ranh giới tác dụng phụ:

| Tầng | Chạm tới | Mặc định |
|---|---|---|
| offline | chỉ thư mục tạm | **bật** |
| `--online` | dịch vụ edge-tts thật | tắt |
| `--hardware` | **phát tiếng thật ra loa** | tắt, **phải xin phép** |

Trọng số: **cao nhất**.

## 4. Eval — cách chấm

Chi tiết và bằng chứng: [eval/README.md](eval/README.md).

- 57 mục offline · 3 mục `--online` · 4 mục `--hardware`.
- Chấm nhị phân. "đã chạy X/Y mục đăng ký"; X < Y là **KHÔNG ĐẠT toàn cục**.
- Đã kiểm ngược bằng **60 lỗi gieo**, phủ **57/57** mục offline, có **3 đối
  chứng kỳ-vọng-xanh**.

## 5. Feedback — cái gì quay lại đâu

| Tín hiệu | Ai nhận | Đi tới đâu |
|---|---|---|
| `needs_speaker_selection` | LLM | đặt câu hỏi cho người dùng |
| lỗi từng loa trong `results` | LLM | báo đúng loa nào hỏng |
| `DeviceNotFoundError` kèm danh sách thiết bị đã biết | LLM và người | gõ đúng tên |
| `service.sh status` in `/proc/<pid>/cmdline` | người vận hành | biết bản đang chạy có phải bản vừa sửa không |
| eval đỏ | người bảo trì | id mục chỉ thẳng vào hợp đồng bị vi phạm |

Vòng phản hồi đắt nhất đã gặp là vòng **thiếu**: sửa xong ba lần mà tiến trình
cũ vẫn sống ba ngày, vì không có gì nói cho ai biết bản đang chạy là bản nào.
Dòng `cmdline` trong `status` sinh ra từ đó.

Trọng số: **trung bình–cao** với người vận hành, **cao** với LLM.
