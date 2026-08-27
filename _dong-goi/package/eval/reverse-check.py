#!/usr/bin/env python3
"""Kiểm ngược HAI CHIỀU cho eval-googlecast-mcp.py.

Một bộ eval chưa từng ĐỎ là một bộ eval chưa chứng minh được điều gì. Kịch bản
này gieo từng khiếm khuyết đã biết vào mã sản phẩm rồi đòi bài kiểm phải bắt
đúng những mục đã ghi TRƯỚC trong ``expect_red``.

Bốn ràng buộc của kịch bản này:

1. GIEO VÀO BẢN SAO. Mỗi trường hợp sao ``src/`` sang một thư mục tạm riêng,
   sửa bản sao, chạy eval với GOOGLECAST_MCP_SRC trỏ vào đó. Cây sản phẩm
   thật KHÔNG BAO GIỜ bị ghi vào — hoàn nguyên là hệ quả của CẤU TRÚC, không
   phải của việc nhớ dọn dẹp. PYTHONDONTWRITEBYTECODE=1 để không có .pyc nào
   của bản sao còn sót lại.

2. KỲ VỌNG VIẾT TRƯỚC. ``expect_red`` là mục kỳ vọng ĐỎ, ghi trong bảng dưới
   đây trước khi chạy. Kèm ít nhất một ĐỐI CHỨNG VÔ HẠI kỳ vọng XANH: nếu một
   thay đổi không đổi hành vi mà bài kiểm vẫn đỏ, thì bài kiểm đỏ bừa — cũng
   là hỏng, và cũng phải sửa.

3. ĐẾM ĐỦ TRƯỚC KHI ĐẾM XANH. In "đã chạy X/Y trường hợp đăng ký"; X < Y là
   KHÔNG ĐẠT. Khớp 0 trường hợp KHÔNG được báo ĐẠT.

4. PHỦ NGƯỢC ĐẦY ĐỦ. Mọi mục offline của bộ eval phải nằm trong ít nhất một
   ``expect_red``. Mục mà không lỗi gieo nào làm đỏ được là nghi phạm cấu
   trúc — có thể nó không hề chạm vào mã sản phẩm.

Khi một mục "lẽ ra đỏ mà lại xanh", định đoạt theo BA nhánh (xem eval/README):
test giả / kỳ vọng sai / lỗi gieo không quan sát được.

Chạy:
    python reverse-check.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC = REPO / "src"
EVAL = HERE / "eval-googlecast-mcp.py"

STORE = "googlecast_mcp/speaker_store.py"
TTS = "googlecast_mcp/tts.py"
MEDIA = "googlecast_mcp/media_server.py"
CAST = "googlecast_mcp/cast_manager.py"
SERVER = "googlecast_mcp/server.py"
ENTRY = "googlecast_mcp/__main__.py"


# --------------------------------------------------------------------------
# Bảng lỗi gieo. expect_red viết TRƯỚC khi chạy.
# --------------------------------------------------------------------------

FAULTS: list[dict] = [
    # ---- speaker_store.py ------------------------------------------------
    {
        "id": "store/chi-nhan-nhom-lam-loa",
        "file": STORE,
        "edits": [('SPEAKER_CAST_TYPES = ("audio", "group")', 'SPEAKER_CAST_TYPES = ("group",)')],
        "expect_red": [
            "store.is_speaker.audio",
            "store.speakers.filters_video",
            "cast.list_speakers.filters_video",
            "server.say.without_a_speaker_choice_plays_nothing",
            "server.list_speakers.scans_once_when_store_is_empty",
        ],
    },
    {
        "id": "store/bo-quen-nhom-loa",
        "file": STORE,
        "edits": [('SPEAKER_CAST_TYPES = ("audio", "group")', 'SPEAKER_CAST_TYPES = ("audio",)')],
        "expect_red": ["store.is_speaker.group"],
    },
    {
        "id": "store/nhan-ca-thiet-bi-hinh-anh",
        "file": STORE,
        "edits": [
            (
                'return device.get("cast_type") in SPEAKER_CAST_TYPES',
                "return True",
            )
        ],
        "expect_red": [
            "store.is_speaker.video_excluded",
            "store.speakers.filters_video",
            "cast.list_speakers.filters_video",
            # KỲ VỌNG SAI đã sửa: server.say.all_excludes_speaker_groups lọc
            # nhóm bằng `s["cast_type"] != "group"` trong server.py, không hề
            # đi qua is_speaker() — lỗi gieo này không quan sát được ở đó.
        ],
    },
    {
        "id": "store/bo-qua-bien-moi-truong",
        "file": STORE,
        "edits": [('override = os.environ.get("GOOGLECAST_MCP_STORE")', "override = None")],
        "expect_red": ["store.default_path.env_override"],
    },
    {
        "id": "store/khong-chiu-noi-file-thieu",
        "file": STORE,
        "edits": [
            ("except (OSError, json.JSONDecodeError):", "except json.JSONDecodeError:")
        ],
        "expect_red": ["store.load.missing_file_is_empty"],
    },
    {
        "id": "store/khong-chiu-noi-file-hong",
        "file": STORE,
        "edits": [("except (OSError, json.JSONDecodeError):", "except OSError:")],
        "expect_red": ["store.load.corrupt_file_is_empty"],
    },
    {
        "id": "store/ghi-de-thay-vi-gop",
        "file": STORE,
        "edits": [
            ("for device in self.load() + devices:", "for device in devices:"),
        ],
        "expect_red": [
            "store.save.merges_by_uuid",
            "store.save.update_keeps_old_fields",
        ],
    },
    {
        "id": "store/danh-roi-truong-du-lieu",
        "file": STORE,
        "edits": [
            (
                "merged[uuid] = {**merged.get(uuid, {}), **device}",
                'merged[uuid] = {"uuid": uuid}',
            )
        ],
        "expect_red": [
            "store.save.roundtrip",
            "store.save.update_keeps_old_fields",
            "store.speakers.filters_video",
            "cast.discover.persists_to_store",
            # KỲ VỌNG SAI đã sửa: ba mục còn lại lấy dữ liệu từ CACHE SỐNG của
            # CastManager (list_cached() gộp `live` đè lên store.load(),
            # cast_manager.py), nên không đi qua vòng lưu-rồi-đọc mà lỗi gieo
            # này làm hỏng.
        ],
    },
    {
        "id": "store/khong-ghi-nguyen-tu",
        "file": STORE,
        "edits": [
            (
                "tmp.replace(self._path)",
                'self._path.write_text(tmp.read_text(encoding="utf-8"), encoding="utf-8")',
            )
        ],
        "expect_red": ["store.save.no_tmp_left_behind"],
    },
    {
        "id": "store/khong-tao-thu-muc-cha",
        "file": STORE,
        "edits": [
            ("self._path.parent.mkdir(parents=True, exist_ok=True)", "pass")
        ],
        "expect_red": ["store.save.creates_parent_dir"],
    },
    # ---- tts.py ----------------------------------------------------------
    {
        "id": "tts/giong-nu-tro-thanh-giong-nam",
        "file": TTS,
        "edits": [('"female": "vi-VN-HoaiMyNeural"', '"female": "vi-VN-NamMinhNeural"')],
        "expect_red": [
            "tts.resolve_voice.female",
            "tts.resolve_voice.default_when_blank",
        ],
    },
    {
        "id": "tts/giong-nam-tro-thanh-giong-nu",
        "file": TTS,
        "edits": [('"male": "vi-VN-NamMinhNeural"', '"male": "vi-VN-HoaiMyNeural"')],
        "expect_red": [
            "tts.resolve_voice.male",
            "server.say.reports_resolved_voice",
        ],
    },
    {
        "id": "tts/nuot-ten-giong-day-du",
        "file": TTS,
        "edits": [
            (
                "return VOICES.get(voice.strip().lower(), voice)",
                "return VOICES.get(voice.strip().lower(), DEFAULT_VOICE)",
            )
        ],
        "expect_red": ["tts.resolve_voice.passthrough_full_id"],
    },
    {
        "id": "tts/nhan-ca-chuoi-rong",
        "file": TTS,
        "edits": [("if not text or not text.strip():", "if False:")],
        "expect_red": ["tts.synthesize.empty_text_rejected"],
    },
    {
        "id": "tts/khong-dung-cache",
        "file": TTS,
        "edits": [
            (
                "    # Reuse an existing render; a zero-byte file means a previous run failed.\n"
                "    if path.exists() and path.stat().st_size > 0:\n"
                "        return path",
                "    # (gieo lỗi: bỏ hẳn cache)\n    if False:\n        return path",
            ),
            (
                "        # Another caller may have rendered it while we waited for the lock.\n"
                "        if path.exists() and path.stat().st_size > 0:\n"
                "            return path",
                "        # (gieo lỗi: bỏ hẳn cache)\n        if False:\n            return path",
            ),
        ],
        "expect_red": ["tts.synthesize.cache_hit_skips_render"],
    },
    {
        "id": "tts/file-0-byte-bi-coi-la-cache-hop-le",
        # Sửa CẢ HAI lần kiểm: sửa mỗi lần thứ nhất thì lần double-check trong
        # khoá che mất khiếm khuyết — đúng nhánh "lỗi gieo không quan sát
        # được", nên lỗi gieo đã được ĐỔI cho quan sát được.
        "file": TTS,
        "edits": [
            (
                "    if path.exists() and path.stat().st_size > 0:\n        return path",
                "    if path.exists():\n        return path",
            ),
            (
                "        if path.exists() and path.stat().st_size > 0:\n            return path",
                "        if path.exists():\n            return path",
            ),
        ],
        "expect_red": ["tts.synthesize.zero_byte_is_not_a_cache_hit"],
    },
    {
        "id": "tts/khoa-mot-cai-cho-ca-tien-trinh",
        # Cái bẫy thật: Lock mức module chỉ tự gắn vào vòng lặp KHI CÓ TRANH
        # CHẤP, nên nó im lặng cho tới lúc hai render chồng nhau.
        "file": TTS,
        "edits": [
            (
                "    loop = asyncio.get_running_loop()\n"
                "    lock = _synthesis_locks.get(loop)\n"
                "    if lock is None:\n"
                "        lock = _synthesis_locks[loop] = asyncio.Lock()\n"
                "    return lock",
                '    if not hasattr(asyncio, "_seeded_module_lock"):\n'
                "        asyncio._seeded_module_lock = asyncio.Lock()\n"
                "    return asyncio._seeded_module_lock",
            )
        ],
        "expect_red": ["tts.lock.is_per_event_loop_under_contention"],
    },
    {
        "id": "tts/khong-thu-lai",
        "file": TTS,
        "edits": [("for attempt in range(3):", "for attempt in range(1):")],
        "expect_red": [
            "tts.synthesize.retries_then_succeeds",
            "tts.synthesize.gives_up_after_three_attempts",
        ],
    },
    {
        "id": "tts/de-dong-file-0-byte",
        "file": TTS,
        "edits": [("path.unlink(missing_ok=True)", "pass  # gieo lỗi", "all")],
        "expect_red": ["tts.synthesize.no_zero_byte_file_left_after_failure"],
    },
    {
        "id": "tts/render-rong-van-tinh-la-thanh-cong",
        "file": TTS,
        "edits": [
            (
                "            if path.exists() and path.stat().st_size > 0:\n"
                "                return path",
                "            if path.exists():\n                return path",
            )
        ],
        "expect_red": [
            "tts.synthesize.empty_render_is_failure_not_success",
            # KỲ VỌNG SAI đã sửa: ...no_zero_byte_file_left_after_failure chạy
            # kịch bản save() NÉM LỖI, nên dừng ở nhánh except và không bao giờ
            # chạm tới dòng kiểm kích thước bị gieo lỗi.
        ],
    },
    {
        "id": "tts/khoa-cache-bo-qua-toc-do",
        "file": TTS,
        "edits": [
            ('f"{resolved}|{rate}|{volume}|{text}"', 'f"{resolved}|{volume}|{text}"')
        ],
        "expect_red": ["tts.synthesize.cache_key_varies_by_rate"],
    },
    {
        "id": "tts/khoa-cache-bo-qua-giong",
        "file": TTS,
        "edits": [('f"{resolved}|{rate}|{volume}|{text}"', 'f"{rate}|{volume}|{text}"')],
        "expect_red": ["tts.synthesize.cache_key_varies_by_voice"],
    },
    {
        "id": "tts/khoa-cache-bo-qua-noi-dung",
        "file": TTS,
        "edits": [('f"{resolved}|{rate}|{volume}|{text}"', 'f"{resolved}|{rate}|{volume}"')],
        "expect_red": [
            "tts.synthesize.cache_key_varies_by_text",
            "tts.fanout.six_concurrent_all_succeed",
        ],
    },
    {
        "id": "tts/sai-duoi-file",
        "file": TTS,
        "edits": [('f"{key}.mp3"', 'f"{key}.wav"')],
        "expect_red": ["tts.synthesize.writes_file"],
    },
    {
        "id": "tts/bo-qua-bien-moi-truong-cache",
        # Lộ luôn cái bẫy tráo-nửa-vời: cache đi một đằng, media server phục vụ
        # một nẻo, url_for() ném ValueError ở chỗ chẳng liên quan.
        "file": TTS,
        "edits": [('override = os.environ.get("GOOGLECAST_MCP_CACHE")', "override = None")],
        "expect_red": [
            "tts.cache_dir.env_override",
            "server.say.single_named_speaker",
            "server.say.comma_separated_list",
            "server.say.all_excludes_speaker_groups",
            "server.say.vietnamese_all_keyword",
            "server.say.broken_element_does_not_sink_the_rest",
            "server.say.all_broken_reports_failed",
            "server.say.audio_url_is_fetchable_by_the_speaker",
            "server.say.casts_as_audio_mpeg",
            "server.say.reports_resolved_voice",
        ],
    },
    # ---- media_server.py -------------------------------------------------
    {
        "id": "media/lan-ip-tra-ve-ten-may",
        "file": MEDIA,
        "edits": [("return sock.getsockname()[0]", "return socket.gethostname()")],
        "expect_red": ["media.lan_ip.returns_ipv4"],
    },
    {
        "id": "media/quang-bao-dia-chi-bind",
        "file": MEDIA,
        "edits": [
            (
                'return f"http://{self._host}:{self.port}/{quote(relative.as_posix())}"',
                'return f"http://0.0.0.0:{self.port}/{quote(relative.as_posix())}"',
            )
        ],
        "expect_red": ["media.url_for.shape"],
    },
    {
        "id": "media/khong-ma-hoa-duong-dan",
        "file": MEDIA,
        "edits": [("quote(relative.as_posix())", "relative.as_posix()")],
        "expect_red": ["media.url_for.percent_encodes"],
    },
    {
        "id": "media/chi-bind-loopback",
        "file": MEDIA,
        "edits": [
            (
                'ThreadingHTTPServer(("0.0.0.0", self._requested_port), handler)',
                'ThreadingHTTPServer(("127.0.0.1", self._requested_port), handler)',
            )
        ],
        "expect_red": ["media.binds_all_interfaces"],
    },
    {
        "id": "media/khong-tu-khoi-dong",
        "file": MEDIA,
        "edits": [
            (
                '        """Public URL for a file inside the served directory."""\n        self.start()',
                '        """Public URL for a file inside the served directory."""',
            )
        ],
        "expect_red": [
            "media.url_for.starts_server_lazily",
            "media.url_for.shape",
            "media.serves_file_over_http",
            "server.say.audio_url_is_fetchable_by_the_speaker",
        ],
    },
    {
        "id": "media/phuc-vu-nham-thu-muc",
        "file": MEDIA,
        "edits": [
            (
                "handler = partial(_QuietHandler, directory=str(self._directory))",
                'handler = partial(_QuietHandler, directory="/")',
            )
        ],
        "expect_red": [
            "media.serves_file_over_http",
            "server.say.audio_url_is_fetchable_by_the_speaker",
        ],
    },
    {
        "id": "media/ghim-cong-bi-lo-di",
        "file": MEDIA,
        "edits": [
            (
                "            self._requested_port = port\n\n    def start",
                "            pass\n\n    def start",
            )
        ],
        "expect_red": ["media.set_port.pins_port"],
    },
    {
        "id": "media/cho-doi-cong-luc-dang-chay",
        "file": MEDIA,
        "edits": [
            (
                'raise RuntimeError("cannot change port while the media server is running")',
                "pass",
            )
        ],
        "expect_red": ["media.set_port.rejected_while_running"],
    },
    {
        "id": "media/khoi-dong-hai-lan-thanh-hai-server",
        "file": MEDIA,
        "edits": [
            (
                "        with self._lock:\n            if self._httpd is not None:\n                return\n            self._directory.mkdir",
                "        with self._lock:\n            if False:\n                return\n            self._directory.mkdir",
            )
        ],
        "expect_red": ["media.start_is_idempotent"],
    },
    {
        "id": "media/dung-server-chua-chay-thi-no",
        "file": MEDIA,
        "edits": [
            (
                "        with self._lock:\n            if self._httpd is None:\n                return\n            self._httpd.shutdown()",
                "        with self._lock:\n            if False:\n                return\n            self._httpd.shutdown()",
            )
        ],
        "expect_red": ["media.stop_is_safe_when_not_running"],
    },
    {
        "id": "media/khong-tao-thu-muc-phuc-vu",
        "file": MEDIA,
        "edits": [("self._directory.mkdir(parents=True, exist_ok=True)", "pass")],
        "expect_red": ["media.creates_directory"],
    },
    # ---- cast_manager.py -------------------------------------------------
    {
        "id": "cast/sai-kieu-noi-dung-am-thanh",
        "file": CAST,
        "edits": [('".mp3": "audio/mpeg",', '".mp3": "application/octet-stream",')],
        "expect_red": [
            "cast.guess_content_type.audio",
            "cast.guess_content_type.ignores_query_string",
            "cast.guess_content_type.case_insensitive",
            "cast.play_media.guesses_type_and_returns_status",
        ],
    },
    {
        "id": "cast/sai-kieu-noi-dung-hinh-anh",
        "file": CAST,
        "edits": [('".mp4": "video/mp4",', '".mp4": "application/octet-stream",')],
        "expect_red": ["cast.guess_content_type.video"],
    },
    {
        "id": "cast/phan-biet-hoa-thuong-trong-duoi-file",
        "file": CAST,
        "edits": [
            ('lowered = url.lower().split("?", 1)[0]', 'lowered = url.split("?", 1)[0]')
        ],
        "expect_red": ["cast.guess_content_type.case_insensitive"],
    },
    {
        "id": "cast/khong-cat-chuoi-truy-van",
        "file": CAST,
        "edits": [('lowered = url.lower().split("?", 1)[0]', "lowered = url.lower()")],
        "expect_red": ["cast.guess_content_type.ignores_query_string"],
    },
    {
        "id": "cast/phan-biet-hoa-thuong-trong-ten-loa",
        "file": CAST,
        "edits": [
            (
                "if cast.cast_info.friendly_name.lower() == lowered:",
                "if cast.cast_info.friendly_name == target:",
            )
        ],
        "expect_red": ["cast.resolve.by_friendly_name_case_insensitive"],
    },
    {
        "id": "cast/khong-tra-cuu-duoc-theo-uuid",
        "file": CAST,
        "edits": [
            ("if target in self._devices:\n                return self._devices[target]", "if False:\n                return None"),
            ('if str(cast.cast_info.uuid).lower() == lowered:\n                    return cast', "if False:\n                    return cast"),
        ],
        "expect_red": ["cast.resolve.by_uuid"],
    },
    {
        "id": "cast/khop-bua-moi-ten",
        "file": CAST,
        "edits": [
            ("if cast.cast_info.friendly_name.lower() == lowered:", "if True:")
        ],
        "expect_red": [
            "cast.resolve.unknown_is_none",
            "cast.resolve.raises_with_known_devices_listed",
            # KỲ VỌNG SAI đã sửa: mục ...saved_address_tried_before_rescan dọn
            # sạch cache sống trước khi gọi, nên thân vòng lặp bị gieo lỗi
            # không hề chạy.
            "server.say.broken_element_does_not_sink_the_rest",
            "server.say.all_broken_reports_failed",
        ],
    },
    {
        "id": "cast/bo-qua-dia-chi-da-luu",
        "file": CAST,
        "edits": [
            (
                "        found = self._connect_saved(target)\n        if found is not None:\n            return found",
                "        pass  # gieo lỗi: nhảy thẳng sang quét lại",
            )
        ],
        "expect_red": ["cast.resolve.saved_address_tried_before_rescan"],
    },
    {
        "id": "cast/bao-loi-khong-noi-biet-nhung-gi",
        "file": CAST,
        "edits": [
            (
                'f"Device {target!r} did not respond. Known devices: {known}."',
                '"Device not found."',
            )
        ],
        "expect_red": ["cast.resolve.raises_with_known_devices_listed"],
    },
    {
        "id": "cast/am-luong-khong-bi-chan-bien",
        "file": CAST,
        "edits": [("clamped = max(0.0, min(1.0, level))", "clamped = level")],
        "expect_red": ["cast.set_volume.clamps_range"],
    },
    {
        "id": "cast/trang-thai-thieu-truong",
        "file": CAST,
        "edits": [('"duration": getattr(media, "duration", None),\n', "")],
        "expect_red": ["cast.status.shape"],
    },
    {
        "id": "cast/thong-tin-thiet-bi-thieu-dia-chi",
        "file": CAST,
        "edits": [('"host": info.host,\n', "")],
        "expect_red": [
            "cast.info.fields",
            "cast.resolve.saved_address_tried_before_rescan",
        ],
    },
    {
        "id": "cast/dieu-khien-truoc-khi-ket-noi-xong",
        "file": CAST,
        "edits": [("cast.wait(timeout=10)", "pass  # gieo lỗi")],
        "expect_red": ["cast.connect_waits_before_control"],
    },
    {
        "id": "cast/quet-xong-khong-luu-lai",
        "file": CAST,
        "edits": [("self._store.save(found)", "pass  # gieo lỗi")],
        "expect_red": ["cast.discover.persists_to_store"],
    },
    # ---- server.py -------------------------------------------------------
    {
        "id": "server/mat-mot-cong-cu",
        "file": SERVER,
        "edits": [("@mcp.tool()\nasync def quit_app", "async def quit_app")],
        "expect_red": ["server.tools.exact_set"],
    },
    {
        "id": "server/khong-chon-loa-thi-phat-het",
        # Đúng điều yêu cầu gốc #3 cấm: tác dụng phụ vật lý, không hoàn tác được.
        "file": SERVER,
        "edits": [
            (
                "    if target and target.strip():\n        cleaned = target.strip()",
                '    if True:\n        cleaned = (target or "all").strip()',
            )
        ],
        "expect_red": [
            "server.say.without_a_speaker_choice_plays_nothing",
            "server.say.no_speakers_on_network",
        ],
    },
    {
        "id": "server/all-gom-ca-nhom-lan-thanh-vien",
        "file": SERVER,
        "edits": [
            (
                'return [s["friendly_name"] for s in speakers if s["cast_type"] != "group"], None',
                'return [s["friendly_name"] for s in speakers], None',
            )
        ],
        "expect_red": ["server.say.all_excludes_speaker_groups"],
    },
    {
        "id": "server/bo-tu-khoa-tieng-viet",
        "file": SERVER,
        "edits": [
            (
                '_ALL_KEYWORDS = {"all", "tất cả", "tat ca", "everyone", "*"}',
                '_ALL_KEYWORDS = {"all", "everyone", "*"}',
            )
        ],
        "expect_red": ["server.say.vietnamese_all_keyword"],
    },
    {
        "id": "server/khong-tach-danh-sach-phay",
        "file": SERVER,
        "edits": [
            (
                'return [part.strip() for part in cleaned.split(",") if part.strip()], None',
                "return [cleaned], None",
            )
        ],
        "expect_red": [
            "server.say.comma_separated_list",
            "server.say.broken_element_does_not_sink_the_rest",
        ],
    },
    {
        "id": "server/lo-di-loa-duoc-chi-dinh",
        "file": SERVER,
        "edits": [
            (
                'return [part.strip() for part in cleaned.split(",") if part.strip()], None',
                "return names, None",
            )
        ],
        "expect_red": [
            "server.say.single_named_speaker",
            "server.say.broken_element_does_not_sink_the_rest",
            "server.say.all_broken_reports_failed",
        ],
    },
    {
        "id": "server/mot-loa-hong-danh-sap-ca-lenh",
        "file": SERVER,
        "edits": [
            (
                '"status": "ok" if played else "failed",',
                '"status": "ok" if len(played) == len(results) else "failed",',
            )
        ],
        "expect_red": ["server.say.broken_element_does_not_sink_the_rest"],
    },
    {
        "id": "server/cast-sai-kieu-noi-dung",
        "file": SERVER,
        "edits": [
            (
                '_manager.play_media, name, url, "audio/mpeg", text[:60]',
                '_manager.play_media, name, url, "video/mp4", text[:60]',
            )
        ],
        "expect_red": ["server.say.casts_as_audio_mpeg"],
    },
    {
        "id": "server/tra-ve-duong-dan-cuc-bo",
        # Đường dẫn file trên máy chủ là vô nghĩa với loa: loa TỰ đi tải qua HTTP.
        "file": SERVER,
        "edits": [('"audio_url": url,', '"audio_url": str(audio_path),')],
        "expect_red": ["server.say.audio_url_is_fetchable_by_the_speaker"],
    },
    {
        "id": "server/khong-tu-quet-khi-chua-biet-loa-nao",
        "file": SERVER,
        "edits": [
            (
                "    if not speakers:\n        await asyncio.to_thread(_manager.discover, 5.0)",
                "    if False:\n        await asyncio.to_thread(_manager.discover, 5.0)",
            )
        ],
        "expect_red": ["server.list_speakers.scans_once_when_store_is_empty"],
    },
    # ---- __main__.py -----------------------------------------------------
    {
        "id": "entry/chi-tin-loopback",
        "file": ENTRY,
        "edits": [
            (
                'hosts = ["127.0.0.1", "localhost", "[::1]", lan_ip()]',
                'hosts = ["127.0.0.1", "localhost", "[::1]"]',
            )
        ],
        "expect_red": ["entry.security.allows_lan_address"],
    },
    {
        "id": "entry/host-buoc-phai-kem-cong",
        # Chính là cái đẻ ra 421 Misdirected Request sau reverse proxy.
        "file": ENTRY,
        "edits": [
            (
                'allowed_hosts=[p for h in unique for p in (h, f"{h}:*")],',
                'allowed_hosts=[f"{h}:*" for h in unique],',
            )
        ],
        "expect_red": [
            "entry.security.allows_lan_address",
            "entry.security.bare_host_and_port_suffix",
            "entry.security.loopback_always_allowed",
            "entry.security.explicit_bind_host_allowed",
        ],
    },
    {
        "id": "entry/khong-chap-nhan-https",
        "file": ENTRY,
        "edits": [('for scheme in ("http", "https")', 'for scheme in ("http",)')],
        "expect_red": ["entry.security.https_origin_for_tls_proxy"],
    },
    {
        "id": "entry/danh-roi-origin-trinh-duyet",
        "file": ENTRY,
        "edits": [("allowed_origins.extend(origins or [])", "pass  # gieo lỗi")],
        "expect_red": ["entry.security.browser_origin_passes_through"],
    },
    {
        "id": "entry/coi-dia-chi-bind-rong-la-mot-dia-chi",
        "file": ENTRY,
        "edits": [('if bind_host not in ("0.0.0.0", "::"):', "if True:")],
        "expect_red": ["entry.security.wildcard_bind_not_treated_as_address"],
    },
    # ---- ĐỐI CHỨNG VÔ HẠI: kỳ vọng XANH ---------------------------------
    {
        "id": "doi-chung/them-mot-dong-chu-thich",
        "file": TTS,
        "edits": [
            (
                'DEFAULT_VOICE = VOICES["female"]',
                '# đối chứng vô hại: chỉ là một dòng chú thích\nDEFAULT_VOICE = VOICES["female"]',
            )
        ],
        "expect_red": [],
    },
    {
        "id": "doi-chung/doi-ten-bien-cuc-bo",
        "file": CAST,
        "edits": [
            (
                "    for ext, mime in mapping.items():\n"
                "        if lowered.endswith(ext):\n"
                "            return mime",
                "    for suffix, mime_type in mapping.items():\n"
                "        if lowered.endswith(suffix):\n"
                "            return mime_type",
            )
        ],
        "expect_red": [],
    },
]


# --------------------------------------------------------------------------


def run_eval(src_dir: Path) -> dict:
    env = {
        **os.environ,
        "GOOGLECAST_MCP_SRC": str(src_dir),
        "PYTHONPATH": str(src_dir),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    proc = subprocess.run(
        [sys.executable, str(EVAL), "--json"],
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {
            "broken": True,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-2000:],
        }


def apply_edits(src_dir: Path, fault: dict) -> None:
    path = src_dir / fault["file"]
    text = path.read_text(encoding="utf-8")
    for edit in fault["edits"]:
        old, new = edit[0], edit[1]
        how = edit[2] if len(edit) > 2 else "one"
        count = text.count(old)
        if how == "one":
            if count != 1:
                raise RuntimeError(
                    f"{fault['id']}: mẩu mã cần gieo xuất hiện {count} lần "
                    f"trong {fault['file']} (cần đúng 1). Lỗi gieo đã lạc hậu "
                    "so với mã sản phẩm."
                )
        elif count == 0:
            raise RuntimeError(f"{fault['id']}: không tìm thấy mẩu mã trong {fault['file']}")
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    if not SRC.is_dir():
        print(f"KHÔNG ĐẠT: không thấy cây mã sản phẩm ở {SRC}")
        return 1
    if not FAULTS:
        print("KHÔNG ĐẠT: bảng lỗi gieo rỗng — khớp 0 trường hợp không phải là ĐẠT")
        return 1

    total = len(FAULTS)
    ran = 0
    problems: list[str] = []

    # --- phủ ngược: mọi mục offline phải nằm trong ít nhất một expect_red ---
    baseline = run_eval(SRC)
    if baseline.get("broken"):
        print("KHÔNG ĐẠT: bộ eval không chạy nổi trên cây nguyên vẹn")
        print(baseline.get("stderr", "")[-1500:])
        return 1
    all_ids = {r["id"] for r in baseline["results"]}
    covered = {cid for f in FAULTS for cid in f["expect_red"]}
    unknown = covered - all_ids
    uncovered = all_ids - covered
    if unknown:
        problems.append(f"expect_red trỏ tới mục không tồn tại: {sorted(unknown)}")
    if uncovered:
        problems.append(
            "mục không lỗi gieo nào làm đỏ được (nghi phạm cấu trúc): "
            f"{sorted(uncovered)}"
        )
    if not baseline["ok"]:
        problems.append("cây nguyên vẹn đã KHÔNG ĐẠT trước cả khi gieo lỗi")

    print(f"nền: {baseline['passed']}/{baseline['registered']} xanh trên cây nguyên vẹn")
    print(f"phủ ngược: {len(covered)}/{len(all_ids)} mục nằm trong ít nhất một expect_red")
    print()

    # --- từng trường hợp gieo lỗi vào một BẢN SAO riêng ---------------------
    for fault in FAULTS:
        ran += 1
        label = fault["id"]
        with tempfile.TemporaryDirectory(prefix="gieo-loi-") as tmp:
            copy = Path(tmp) / "src"
            shutil.copytree(SRC, copy, ignore=shutil.ignore_patterns("__pycache__"))
            try:
                apply_edits(copy, fault)
            except RuntimeError as exc:
                problems.append(str(exc))
                print(f"  LỖI GIEO  {label}: {exc}")
                continue

            out = run_eval(copy)
            if out.get("broken"):
                problems.append(f"{label}: eval không trả nổi kết quả JSON")
                print(f"  HỎNG      {label}: eval sập, không có báo cáo")
                print(out.get("stderr", "")[-800:])
                continue
            if out["ran"] != out["registered"]:
                problems.append(
                    f"{label}: eval chỉ chạy {out['ran']}/{out['registered']} mục"
                )

            red = {r["id"] for r in out["results"] if r["status"] != "PASS"}
            expected = set(fault["expect_red"])
            missed = expected - red
            if expected:
                extra = red - expected
                if missed:
                    problems.append(
                        f"{label}: lẽ-ra-đỏ-mà-xanh → {sorted(missed)} "
                        "(định đoạt theo BA nhánh: test giả / kỳ vọng sai / "
                        "lỗi gieo không quan sát được)"
                    )
                    print(f"  THIẾU ĐỎ  {label}: {sorted(missed)}")
                else:
                    note = f" (+{len(extra)} mục đỏ lây)" if extra else ""
                    print(f"  bắt được  {label}{note}")
            else:
                if red:
                    problems.append(
                        f"{label}: ĐỐI CHỨNG VÔ HẠI mà bài kiểm vẫn đỏ → đỏ bừa: "
                        f"{sorted(red)}"
                    )
                    print(f"  ĐỎ BỪA    {label}: {sorted(red)}")
                else:
                    print(f"  xanh đúng {label} (đối chứng vô hại)")

    # --- xác nhận cuối: chạy lại trên cây NGUYÊN VẸN ------------------------
    for pyc in SRC.rglob("__pycache__"):
        shutil.rmtree(pyc, ignore_errors=True)
    final = run_eval(SRC)
    if final.get("broken") or not final["ok"]:
        problems.append("cây nguyên vẹn KHÔNG còn xanh sau khi chạy kiểm ngược")

    print()
    print(f"đã chạy {ran}/{total} trường hợp đăng ký")
    complete = ran == total
    if not complete:
        print("FAIL TOÀN CỤC: chạy thiếu trường hợp")
    print(
        "xác nhận cuối trên cây nguyên vẹn: "
        + ("xanh" if not final.get("broken") and final.get("ok") else "KHÔNG XANH")
    )
    if problems:
        print()
        print("Vấn đề:")
        for p in problems:
            print(f"  - {p}")
    print()
    print("KẾT QUẢ KIỂM NGƯỢC: ĐẠT" if complete and not problems else "KẾT QUẢ KIỂM NGƯỢC: KHÔNG ĐẠT")
    return 0 if complete and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
