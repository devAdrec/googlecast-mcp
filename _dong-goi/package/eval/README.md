# Eval

```bash
# tầng offline — không cần loa, KHÔNG phát tiếng
uv run --directory /storage/apps/mcp/googlecast_mcp \
  python _dong-goi/package/eval/eval-googlecast-mcp.py

# tầng hardware — CAST THẬT, PHÁT TIẾNG RA LOA TRONG NHÀ
uv run --directory /storage/apps/mcp/googlecast_mcp \
  python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware
```

Exit code 0 = mọi mục PASS. 1 = có FAIL. Mục SKIP không làm hỏng exit code nhưng được
in riêng ở cuối, để chỗ CHƯA thực sự được kiểm không lẫn vào chỗ đã kiểm.

## Vì sao chia hai tầng

Product này có **tác dụng phụ vật lý**. Một bộ test chạy được ở mọi nơi mà lại phát
tiếng trong phòng ngủ lúc 2 giờ sáng là một bộ test không ai dám chạy — và test không
ai dám chạy thì bằng không có.

Nên tầng mặc định thay thế (monkeypatch) lớp cast và TTS, dùng một speaker store giả
trong thư mục tạm: không một gói tin nào tới thiết bị thật. Tầng hardware phải bật
tường minh bằng cờ `--hardware`.

**Chi tiết dễ bỏ sót:** `SpeakerStore` đọc biến môi trường ngay lúc khởi tạo, mà
`server.py` khởi tạo `CastManager` ở cấp module. Nên `GOOGLECAST_MCP_STORE` phải được
đặt **trước lệnh import**. Đặt sau, eval sẽ đụng vào file thật
`~/.googlecast-mcp/speakers.json` của người dùng.

## Tầng offline kiểm gì (35 mục)

| Nhóm | Kiểm điều gì | Vá được ngõ cụt nào |
|---|---|---|
| import + đăng ký tool | server import được; đúng 13 tool, không thiếu không thừa | đổi tên/xoá tool mà không ai biết |
| `is_speaker` | `audio`/`group` là loa, `cast` thì không | lọc sai → cast tiếng lên TV |
| `_guess_content_type` | 8 trường hợp gồm chữ hoa, query string, không có đuôi | đoán sai MIME → thiết bị từ chối |
| `resolve_voice` | female/male/None/hoa-thường/id đầy đủ | |
| `_transport_security` | allowlist có scheme `https` **và** host không kèm port | 421 Misdirected Request, reverse proxy |
| `say` thiếu `target` | trả `needs_speaker_selection`, **không cast, không gọi TTS** | YC-3 — tác dụng phụ vật lý |
| `say` với `all` | không gửi tới `cast_type=group`; nhóm vẫn gọi được bằng tên | chồng luồng lên một loa vật lý |
| nhiều loa cách phẩy | cast tới từng loa | |
| cô lập lỗi | một loa hỏng → phần tử đó `error`, loa còn lại vẫn `playing` | một loa chết kéo đổ cả lệnh |
| TTS | text rỗng → `ValueError`; sinh ra mp3 khác rỗng, đúng header | |

Mục TTS thật cần internet. Không có mạng thì nó ra **SKIP**, không phải FAIL — nhưng
được in ở cuối để không ai nhầm là đã kiểm.

## Eval này có thật sự bắt được lỗi không?

Đã kiểm ngược. Đưa hành vi cũ trở lại (`all` gồm cả nhóm lẫn thành viên) rồi chạy lại:
mục `say all -> KHÔNG gửi tới speaker group` FAIL đúng như mong đợi. Một bộ eval chưa
từng thấy màu đỏ là một bộ eval chưa được kiểm chứng.

## Cái tầng offline KHÔNG kiểm được

Nói rõ để không ai coi exit code 0 là bảo chứng:

- **Âm thanh có đúng không.** Chồng luồng, phát cụt, sai giọng — API vẫn báo `playing`
  trong cả ba trường hợp. Chỉ tai người mới phát hiện được.
- **mDNS discovery thật** — cần mạng thật và thiết bị thật.
- **Thiết bị có thật sự tải được file audio về không** — cần loa gọi ngược lại.
- **nginx, TLS, CORS trên đường truyền thật** — cần bản triển khai đang chạy.

Cột này chính là phần việc của tầng `--hardware`, cộng với tai người.
