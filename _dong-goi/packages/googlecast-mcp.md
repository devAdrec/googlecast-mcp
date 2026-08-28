---
product: googlecast-mcp
layer: registry
product_repo: https://github.com/devAdrec/googlecast-mcp
package: https://github.com/devAdrec/googlecast-mcp
package_kind: mcp
package_status: CÓ
package_root: /storage/apps/mcp/googlecast_mcp/_dong-goi
dod_test: "người lạ, môi trường sạch, chỉ đọc package/README — GỌI ĐƯỢC TOOL"
dod_verified: 2026-08-28
eval_last: 2026-08-28
eval_offline: "57/57 ĐẠT"
eval_online: "3/3 ĐẠT"
eval_hardware: "64/64 ĐẠT (2026-08-28, sau khi sửa 2 lỗi của chính bài kiểm)"
reverse_check: "60/60 lỗi gieo ĐẠT, phủ 57/57 mục offline, 3 đối chứng xanh, 56s"
transmission_level: L2
method_note_triage: "7 lỗ hổng — 6 sửa ngay, 1 chấp nhận có lý do, 0 ngoài phạm vi"
method_note: "[[method-googlecast-mcp]]"
reproduction: "[[reproduce-googlecast-mcp]]"
feedback: "[[phan-hoi-quy-trinh]]"
tags: [mcp, google-cast, tts, tiếng-việt, systemd]
---

# googlecast-mcp

MCP server điều khiển loa Google Cast trong LAN: dò loa, đọc văn bản tiếng Việt
thành tiếng nói, phát ra loa được chọn. 13 tool. Đang chạy thật dạng systemd
service trên `192.168.1.128`, phục vụ Claude Desktop (máy `.28`) qua https và
webui llama-server (máy `.99:8383`).

## Vì sao thẻ này nằm ở đây

Chế độ solo **không có vault**, nên không có thư mục `packages/` ở tầng điều
phối để đặt thẻ vào. Đặt tại `_dong-goi/packages/googlecast-mcp.md` để:

1. cả cụm tài sản của một product nằm **cùng một chỗ**, đi theo repo — không có
   mảnh nào ở lại một máy;
2. thẻ được **git theo dõi** như mọi tài sản khác, nên nó tồn tại được lâu hơn
   phiên làm việc;
3. khi vault xuất hiện, chỉ cần **sao/liên kết đúng một file** này lên
   `packages/` mà không phải đi gom lại; `package_root` trong frontmatter chỉ
   sẵn nơi phần còn lại nằm.

## Tài sản

| Lớp | File |
|---|---|
| output — cách cài + **bằng chứng DoD** | [[package/README]] |
| output — yêu cầu | [[package/requirement]] |
| output — kỹ thuật, ngõ cụt, điểm hở | [[package/technical-docs]] |
| output — hướng dẫn dùng | [[package/user-manual]] |
| output — harness 5 lớp | [[package/harness-spec]] |
| output — bài kiểm + kiểm ngược | [[package/eval/README]] |
| method | [[method-googlecast-mcp]] |
| reproduction | [[reproduce-googlecast-mcp]] |
| feedback | [[phan-hoi-quy-trinh]] |

Tài liệu **đang sống** của sản phẩm nằm trong repo: `README.md`,
`docs/architecture.md`. Bộ bàn giao cố ý mỏng và trỏ về đó.

## Trạng thái

- **`package: CÓ`.** DoD dạng MCP (*gọi được tool*) đã chạy lại ngày 2026-08-28
  trên bản clone sạch, cả stdio lẫn HTTP, đều ra 13 tool; `list_speakers` trả
  loa thật.
- **Điểm hở đã biết, chưa đóng:** không xác thực ở tầng ứng dụng, trong khi tên
  miền phân giải công khai · cổng audio 8766 không xác thực, phục vụ nguyên thư
  mục cache · chặn IP nginx đã đồng ý bật nhưng hai dòng vẫn đang comment. Chi
  tiết ở [[package/technical-docs#điểm-còn-hở--không-tô-hồng]].
- **Method note: L2** (chấm bởi `method-note-evaluator-solo`, context sạch, đề
  đối chứng "MCP máy in nhãn LAN"). Mức được giữ **ở thẻ này**, cố ý KHÔNG ghi
  trong frontmatter của chính note — để note tự dán mức cho mình không mồi sẵn
  kỳ vọng cho người chấm sau. Bảng định đoạt 7 lỗ hổng nằm ở phụ lục cuối note.
- **Chưa thử:** giọng nam và tham số `rate` bằng tai · service sống sót qua
  reboot · loa đổi IP → nhánh quét lại · MCP elicitation trên client thật.

## Chạy lại bài kiểm

```bash
cd /storage/apps/mcp/googlecast_mcp
uv run python _dong-goi/package/eval/eval-googlecast-mcp.py     # ~5s
uv run python _dong-goi/package/eval/reverse-check.py           # ~60s
```
