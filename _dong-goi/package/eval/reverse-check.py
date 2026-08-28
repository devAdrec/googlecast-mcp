#!/usr/bin/env python3
"""Kiểm ngược bài kiểm: gieo lỗi rồi xem bài kiểm có ĐỎ đúng chỗ không.

Vì sao cần: một bài kiểm chưa từng đỏ thì chưa chứng minh được gì. Nó có thể
chỉ đang đo kích thước, đang so với chính nó, hoặc chẳng chạm vào mã sản phẩm.

Cách làm — bốn ràng buộc, đủ bộ:

1. KỲ VỌNG VIẾT TRƯỚC. Mỗi lỗi gieo mang sẵn danh sách mục eval PHẢI đỏ
   (``expect_red``), viết cùng lúc với lỗi, không phải chép lại kết quả chạy.

2. GIEO VÀO BẢN SAO. Với từng ca, ``src/`` được sao sang thư mục tạm, lỗi
   được gieo vào BẢN SAO, PYTHONPATH trỏ vào đó, PYTHONDONTWRITEBYTECODE=1.
   Hoàn nguyên là hệ quả của CẤU TRÚC (thư mục tạm tự xoá), không phải trí
   nhớ của người chạy. Cây sản phẩm không bao giờ bị ghi vào.

3. ĐỐI CHỨNG KỲ-VỌNG-XANH. Vài ca sửa mã ĐANG THỰC SỰ CHẠY mà không đổi hành
   vi (đổi tên biến cục bộ, tách biểu thức thành biến). Chú thích hay khoảng
   trắng KHÔNG tính là đối chứng — chúng vô hại tới mức không kiểm được gì.
   Đỏ trên đối chứng là ĐỎ BỪA và cũng phải sửa.

4. BÁO X/Y HAI CHIỀU. In cả "đã chạy S/T lỗi gieo" lẫn "đã phủ M/N mục eval".
   Lượt rút gọn (``--only``) không được hoá trang thành lượt đầy đủ.

Dùng:
    uv run python _dong-goi/package/eval/reverse-check.py               # đầy đủ
    uv run python _dong-goi/package/eval/reverse-check.py --only tts_   # rút gọn
    uv run python _dong-goi/package/eval/reverse-check.py --list
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # _dong-goi/package/eval -> _dong-goi/package -> _dong-goi -> repo
SRC = REPO / "src"
EVAL = HERE / "eval-googlecast-mcp.py"

STORE = "googlecast_mcp/speaker_store.py"
TTS = "googlecast_mcp/tts.py"
MEDIA = "googlecast_mcp/media_server.py"
CAST = "googlecast_mcp/cast_manager.py"
SERVER = "googlecast_mcp/server.py"
MAIN = "googlecast_mcp/__main__.py"


def seed(seed_id, path, old, new, expect_red, run_items=None, note=""):
    return {
        "id": seed_id,
        "path": path,
        "old": old,
        "new": new,
        "expect_red": list(expect_red),
        "run_items": list(run_items or expect_red),
        "note": note,
        "control": not expect_red,
    }


SEEDS = [
    # ---------------- speaker_store -------------------------------------
    seed(
        "store_no_speaker_types_at_all",
        STORE,
        'SPEAKER_CAST_TYPES = ("audio", "group")',
        "SPEAKER_CAST_TYPES = ()",
        ["store_is_speaker_audio", "store_is_speaker_group", "store_speakers_filters_video",
         "manager_discover_persists_devices"],
        note="không loa nào được nhận ra",
    ),
    seed(
        "store_drops_speaker_groups",
        STORE,
        'SPEAKER_CAST_TYPES = ("audio", "group")',
        'SPEAKER_CAST_TYPES = ("audio",)',
        ["store_is_speaker_group", "store_speakers_filters_video"],
        note="nhóm loa biến mất khỏi danh sách",
    ),
    seed(
        "store_treats_video_cast_as_speaker",
        STORE,
        'SPEAKER_CAST_TYPES = ("audio", "group")',
        'SPEAKER_CAST_TYPES = ("audio", "group", "cast")',
        ["store_rejects_video_cast", "store_speakers_filters_video",
         "manager_discover_persists_devices"],
        note="lẫn màn hình/TV vào danh sách loa",
    ),
    seed(
        "store_replaces_instead_of_merging",
        STORE,
        "for device in self.load() + devices:",
        "for device in devices:",
        ["store_save_merges_by_uuid"],
        note="một lần quét sót là mất thiết bị đã lưu",
    ),
    seed(
        "store_load_breaks_on_missing_file",
        STORE,
        "            except (OSError, json.JSONDecodeError):",
        "            except json.JSONDecodeError:",
        ["store_load_missing_is_empty"],
        note="chưa có file lưu thì ném lỗi",
    ),
    seed(
        "store_load_breaks_on_corrupt_json",
        STORE,
        "            except (OSError, json.JSONDecodeError):",
        "            except OSError:",
        ["store_load_corrupt_is_empty"],
        note="file hỏng thì ném lỗi thay vì trả rỗng",
    ),
    seed(
        "store_write_is_not_atomic",
        STORE,
        "            tmp.replace(self._path)",
        '            self._path.write_text(tmp.read_text(encoding="utf-8"), encoding="utf-8")',
        ["store_save_no_temp_left"],
        note="bỏ ghi-rồi-đổi-tên, để lại file .tmp",
    ),
    seed(
        "store_ignores_path_env",
        STORE,
        "    if override:\n        return Path(override).expanduser()",
        "    if False:\n        return Path(override).expanduser()",
        ["store_path_env_override"],
        note="bỏ qua GOOGLECAST_MCP_STORE",
    ),
    seed(
        "store_default_path_moved",
        STORE,
        'return Path.home() / ".googlecast-mcp" / "speakers.json"',
        'return Path.home() / ".gcmcp" / "speakers.json"',
        ["store_path_default_home"],
        note="đổi nơi lưu mặc định, bản cũ mất dấu",
    ),
    # ---------------- tts ------------------------------------------------
    seed(
        "tts_lock_is_module_level",
        TTS,
        "    loop = asyncio.get_running_loop()\n"
        "    lock = _synthesis_locks.get(loop)\n"
        "    if lock is None:\n"
        "        lock = _synthesis_locks[loop] = asyncio.Lock()\n"
        "    return lock",
        '    if not hasattr(_synthesis_lock, "_one"):\n'
        "        _synthesis_lock._one = asyncio.Lock()\n"
        "    return _synthesis_lock._one",
        ["tts_lock_per_loop"],
        note="quay lại đúng con bọ cũ: một khoá cho cả tiến trình",
    ),
    seed(
        "tts_no_lock_at_all",
        TTS,
        "    async with _synthesis_lock():",
        "    if True:",
        ["tts_serializes_concurrent_renders"],
        note="các lần render lại chồng lên nhau",
    ),
    seed(
        "tts_tries_only_once",
        TTS,
        "        for attempt in range(3):",
        "        for attempt in range(1):",
        ["tts_retries_three_times"],
        note="bỏ thử lại",
    ),
    seed(
        "tts_reuses_zero_byte_file",
        TTS,
        "    # Reuse an existing render; a zero-byte file means a previous run failed.\n"
        "    if path.exists() and path.stat().st_size > 0:",
        "    # Reuse an existing render; a zero-byte file means a previous run failed.\n"
        "    if path.exists():",
        ["tts_zero_byte_not_reused"],
        note="dùng lại file 0 byte của lần hỏng trước",
    ),
    seed(
        "tts_leaves_partial_file_behind",
        TTS,
        "                last_error = exc\n                path.unlink(missing_ok=True)\n                continue",
        "                last_error = exc\n                continue",
        ["tts_leaves_no_zero_byte_file"],
        note="save() hỏng giữa chừng để lại file rỗng",
    ),
    seed(
        "tts_cache_key_ignores_rate",
        TTS,
        'key = hashlib.sha256(f"{resolved}|{rate}|{volume}|{text}".encode()).hexdigest()[:32]',
        'key = hashlib.sha256(f"{resolved}|{volume}|{text}".encode()).hexdigest()[:32]',
        ["tts_cache_key_varies_with_rate"],
        note="đổi tốc độ đọc vẫn trả file cũ",
    ),
    seed(
        "tts_cache_never_hits",
        TTS,
        'key = hashlib.sha256(f"{resolved}|{rate}|{volume}|{text}".encode()).hexdigest()[:32]',
        'key = hashlib.sha256(f"{resolved}|{rate}|{volume}|{text}|{os.urandom(8)!r}".encode()).hexdigest()[:32]',
        ["tts_cache_hit_skips_render", "tts_zero_byte_not_reused"],
        note="cache thành vô dụng, mỗi lần lại gọi dịch vụ",
    ),
    seed(
        "tts_voices_swapped",
        TTS,
        '    "female": "vi-VN-HoaiMyNeural",',
        '    "female": "vi-VN-NamMinhNeural",',
        ["tts_resolve_female", "say_casts_to_chosen_speaker"],
        note="gọi giọng nữ ra giọng nam",
    ),
    seed(
        "tts_male_voice_wrong",
        TTS,
        '    "male": "vi-VN-NamMinhNeural",',
        '    "male": "vi-VN-HoaiMyNeural",',
        ["tts_resolve_male"],
        note="giọng nam không tồn tại nữa",
    ),
    seed(
        "tts_full_voice_id_dropped",
        TTS,
        "    return VOICES.get(voice.strip().lower(), voice)",
        "    return VOICES.get(voice.strip().lower(), DEFAULT_VOICE)",
        ["tts_resolve_passthrough_and_default"],
        note="id giọng đầy đủ bị nuốt, âm thầm về giọng mặc định",
    ),
    seed(
        "tts_accepts_empty_text",
        TTS,
        "    if not text or not text.strip():",
        "    if False:",
        ["tts_empty_text_raises"],
        note="văn bản rỗng vẫn gọi dịch vụ",
    ),
    seed(
        "tts_ignores_cache_env",
        TTS,
        '    override = os.environ.get("GOOGLECAST_MCP_CACHE")',
        "    override = None",
        ["tts_cache_dir_env_override"],
        note="bỏ qua GOOGLECAST_MCP_CACHE",
    ),
    # ---------------- media_server ---------------------------------------
    seed(
        "media_binds_loopback_only",
        MEDIA,
        'self._httpd = ThreadingHTTPServer(("0.0.0.0", self._requested_port), handler)',
        'self._httpd = ThreadingHTTPServer(("127.0.0.1", self._requested_port), handler)',
        ["media_binds_all_interfaces"],
        note="loa ở LAN không tải được file nữa",
    ),
    seed(
        "media_url_uses_bind_address",
        MEDIA,
        'return f"http://{self._host}:{self.port}/{quote(relative.as_posix())}"',
        'return f"http://{self._httpd.server_address[0]}:{self.port}/{quote(relative.as_posix())}"',
        ["media_url_uses_advertised_host"],
        note="quảng bá 0.0.0.0 cho loa — địa chỉ bind KHÁC địa chỉ quảng bá",
    ),
    seed(
        "media_url_not_quoted",
        MEDIA,
        "quote(relative.as_posix())",
        "relative.as_posix()",
        ["media_url_quotes_special_chars"],
        note="tên file tiếng Việt có dấu cách làm hỏng URL",
    ),
    seed(
        "media_never_starts_thread",
        MEDIA,
        "            self._thread.start()",
        "            pass",
        ["media_actually_serves_the_file"],
        note="server dựng lên nhưng không phục vụ ai",
    ),
    seed(
        "media_start_not_idempotent",
        MEDIA,
        "            if self._httpd is not None:\n                return\n            self._directory.mkdir(parents=True, exist_ok=True)",
        "            self._directory.mkdir(parents=True, exist_ok=True)",
        ["media_start_is_idempotent"],
        note="mỗi lần start lại dựng thêm một server ở cổng khác",
    ),
    seed(
        "media_port_change_allowed_while_running",
        MEDIA,
        'raise RuntimeError("cannot change port while the media server is running")',
        "pass",
        ["media_set_port_after_start_is_refused"],
        note="đổi cổng lúc đang chạy, URL đã phát đi thành sai",
    ),
    seed(
        "media_lan_ip_raises_offline",
        MEDIA,
        '    except OSError:\n        return "127.0.0.1"',
        "    except OSError:\n        raise",
        ["media_lan_ip_falls_back_to_loopback"],
        note="mất mạng là cả server chết",
    ),
    # ---------------- cast_manager ---------------------------------------
    seed(
        "guess_keeps_query_string",
        CAST,
        'lowered = url.lower().split("?", 1)[0]',
        "lowered = url.lower()",
        ["guess_content_type_ignores_query"],
        note="URL có ?token=... thì đoán sai kiểu nội dung",
    ),
    seed(
        "guess_mp3_wrong_mime",
        CAST,
        '        ".mp3": "audio/mpeg",',
        '        ".mp3": "audio/mp3",',
        ["guess_content_type_audio", "guess_content_type_ignores_query",
         "manager_status_reports_media_fields"],
        note="kiểu MIME sai, thiết bị có thể từ chối",
    ),
    seed(
        "guess_default_changed",
        CAST,
        '            return mime\n    return "video/mp4"',
        '            return mime\n    return "application/octet-stream"',
        ["guess_content_type_default"],
        note="đuôi lạ thì trả kiểu thiết bị không hiểu",
    ),
    seed(
        "manager_name_match_is_case_sensitive",
        CAST,
        "                if cast.cast_info.friendly_name.lower() == lowered:",
        "                if cast.cast_info.friendly_name == lowered:",
        ["manager_resolves_name_case_insensitively"],
        note="gõ sai hoa thường là không thấy loa",
    ),
    seed(
        "manager_skips_saved_address",
        CAST,
        "        found = self._connect_saved(",
        "        found = None or self._skip_saved(",
        ["manager_connects_saved_when_mdns_misses"],
        note="quay lại lỗi cũ: mDNS sót thiết bị đã lưu là chịu thua",
    ),
    seed(
        "manager_volume_not_clamped",
        CAST,
        "        clamped = max(0.0, min(1.0, level))",
        "        clamped = level",
        ["manager_volume_is_clamped"],
        note="gửi âm lượng 5.0 xuống loa",
    ),
    seed(
        "manager_discovery_not_persisted",
        CAST,
        "        self._store.save(found)\n        return found",
        "        return found",
        ["manager_discover_persists_devices"],
        note="khởi động lại là quên sạch thiết bị",
    ),
    seed(
        "manager_does_not_wait_for_connection",
        CAST,
        "        cast.wait(timeout=10)",
        "        pass",
        ["manager_status_reports_media_fields"],
        note="điều khiển trước khi kết nối sẵn sàng",
    ),
    seed(
        "manager_unknown_device_returns_none",
        CAST,
        "        raise DeviceNotFoundError(",
        "        return None or DeviceNotFoundError(",
        ["manager_unknown_device_raises"],
        note="thiết bị lạ trả None, lỗi nổ ở chỗ khác",
    ),
    # ---------------- server ---------------------------------------------
    seed(
        "select_all_includes_groups",
        SERVER,
        'return [s["friendly_name"] for s in speakers if s["cast_type"] != "group"], None',
        'return [s["friendly_name"] for s in speakers], None',
        ["select_all_excludes_groups"],
        note="quay lại lỗi chồng luồng: nhóm VÀ thành viên cùng nhận",
    ),
    seed(
        "select_missing_defaults_to_everything",
        SERVER,
        '    return [], {\n        "status": "needs_speaker_selection",',
        '    return names, None\n    return [], {\n        "status": "needs_speaker_selection",',
        ["select_without_choice_asks_back", "say_without_choice_plays_nothing"],
        note="không chọn loa thì phát ra TẤT CẢ — tác dụng phụ vật lý không hoàn tác được",
    ),
    seed(
        "select_no_speakers_status_wrong",
        SERVER,
        '            "status": "no_speakers_found",',
        '            "status": "needs_speaker_selection",',
        ["select_no_speakers_status"],
        note="bảo LLM đi hỏi người dùng chọn trong danh sách rỗng",
    ),
    seed(
        "select_does_not_split_commas",
        SERVER,
        '        return [part.strip() for part in cleaned.split(",") if part.strip()], None',
        "        return [cleaned], None",
        ["select_comma_separated_list"],
        note="nhiều loa cách phẩy thành một cái tên vô nghĩa",
    ),
    seed(
        "select_rejects_group_by_name",
        SERVER,
        '        return [part.strip() for part in cleaned.split(",") if part.strip()], None',
        '        _groups = {s["friendly_name"] for s in speakers if s["cast_type"] == "group"}\n'
        '        return [p.strip() for p in cleaned.split(",") if p.strip() and p.strip() not in _groups], None',
        ["select_group_by_name_still_allowed"],
        note="sửa quá tay ngõ cụt chồng luồng: cấm luôn cả gọi nhóm theo tên",
    ),
    seed(
        "say_one_bad_speaker_fails_everything",
        SERVER,
        '        except Exception as exc:  # one unreachable speaker must not fail the rest\n'
        '            return {"speaker": name, "status": "error", "error": str(exc)}',
        "        except Exception as exc:  # one unreachable speaker must not fail the rest\n"
        "            raise",
        ["say_isolates_one_broken_speaker", "say_all_broken_is_failed"],
        note="một loa rút điện là cả lượt phát đổ",
    ),
    seed(
        "say_reports_ok_even_when_nothing_played",
        SERVER,
        '        "status": "ok" if played else "failed",',
        '        "status": "ok",',
        ["say_all_broken_is_failed"],
        note="báo thành công trong khi không loa nào phát",
    ),
    seed(
        "server_loses_a_tool",
        SERVER,
        "@mcp.tool()\nasync def quit_app(",
        "async def quit_app(",
        ["server_exposes_thirteen_tools"],
        note="một công cụ biến mất khỏi danh mục MCP",
    ),
    seed(
        "server_tool_loses_description",
        SERVER,
        '    """Stop the running app and return the device to its idle screen.\n\n'
        "    Args:\n"
        "        target: Device friendly_name or uuid.\n"
        '    """\n',
        "",
        ["tool_descriptions_are_present"],
        note="LLM chọn công cụ bằng mô tả; mất mô tả là mất khả năng gọi đúng",
    ),
    # ---------------- __main__ (an ninh vận chuyển, CORS, CLI) ------------
    seed(
        "security_loopback_only",
        MAIN,
        '    hosts = ["127.0.0.1", "localhost", "[::1]", lan_ip()]',
        '    hosts = ["127.0.0.1", "localhost", "[::1]"]',
        ["security_allows_lan_address", "security_allows_https_origin_behind_proxy",
         "cli_http_binds_loopback_by_default"],
        note="quay lại 421 Misdirected Request cho mọi client ở máy khác",
    ),
    seed(
        "security_requires_port_suffix",
        MAIN,
        '        allowed_hosts=[p for h in unique for p in (h, f"{h}:*")],',
        '        allowed_hosts=[f"{h}:*" for h in unique],',
        ["security_allows_bare_host_without_port", "security_allows_lan_address",
         "cli_http_binds_loopback_by_default"],
        note="proxy ở cổng mặc định gửi Host không kèm :port, bị chặn",
    ),
    seed(
        "security_http_origins_only",
        MAIN,
        '        for scheme in ("http", "https")',
        '        for scheme in ("http",)',
        ["security_allows_https_origin_behind_proxy"],
        note="proxy kết thúc TLS thì origin https bị từ chối",
    ),
    seed(
        "security_wildcard_bind_allowed_as_host",
        MAIN,
        '    if bind_host not in ("0.0.0.0", "::"):',
        "    if True:",
        ["security_wildcard_bind_is_not_an_address"],
        note="đưa 0.0.0.0 vào allowlist — nới bảo vệ mà chẳng ích cho ai",
    ),
    seed(
        "security_drops_browser_origins",
        MAIN,
        "    allowed_origins.extend(origins or [])",
        "    pass",
        ["security_browser_origin_passes_through"],
        note="origin trình duyệt qua được CORS nhưng bị SDK chặn",
    ),
    seed(
        "cors_does_not_expose_session_header",
        MAIN,
        '        expose_headers=["Mcp-Session-Id", "mcp-session-id"],',
        "        expose_headers=[],",
        ["cors_exposes_session_header"],
        note="trình duyệt không đọc được session id, chỉ thấy 'Failed to fetch'",
    ),
    seed(
        "cors_blocks_preflight",
        MAIN,
        '        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],',
        '        allow_methods=["GET", "POST", "DELETE"],',
        ["cors_exposes_session_header"],
        note="preflight OPTIONS bị từ chối",
    ),
    seed(
        "cli_default_transport_is_http",
        MAIN,
        '        choices=["stdio", "http", "sse"],\n        default="stdio",',
        '        choices=["stdio", "http", "sse"],\n        default="http",',
        ["cli_defaults_are_safe"],
        note="cài xong là tự mở cổng mạng mà không ai yêu cầu",
    ),
    seed(
        "cli_default_host_is_wildcard",
        MAIN,
        '        default="127.0.0.1",\n        help="Bind host for http/sse transports (default: 127.0.0.1).",',
        '        default="0.0.0.0",\n        help="Bind host for http/sse transports (default: 127.0.0.1).",',
        ["cli_http_binds_loopback_by_default"],
        note="mặc định phơi ra toàn mạng",
    ),
    seed(
        "cli_media_port_ignored",
        MAIN,
        "        _media_server.set_port(args.media_port)",
        "        pass",
        ["cli_http_binds_loopback_by_default"],
        note="--media-port bị lờ đi, quy tắc tường lửa thành vô nghĩa",
    ),
    seed(
        "cli_no_cleanup_on_exit",
        MAIN,
        "        _media_server.stop()\n        _manager.close()",
        "        pass",
        ["cli_defaults_are_safe"],
        note="thoát mà không đóng cổng HTTP và các kết nối Cast",
    ),
    # ---------------- ĐỐI CHỨNG kỳ-vọng-XANH ------------------------------
    # Sửa mã ĐANG CHẠY, không đổi hành vi. Chú thích/khoảng trắng không tính.
    seed(
        "control_rename_local_variables",
        CAST,
        "    for ext, mime in mapping.items():\n"
        "        if lowered.endswith(ext):\n"
        "            return mime",
        "    for extension, mimetype in mapping.items():\n"
        "        if lowered.endswith(extension):\n"
        "            return mimetype",
        [],
        run_items=["guess_content_type_audio", "guess_content_type_ignores_query",
                   "guess_content_type_default", "manager_status_reports_media_fields"],
        note="đổi tên biến cục bộ trong vòng lặp thực thi",
    ),
    seed(
        "control_split_expression",
        STORE,
        '    return device.get("cast_type") in SPEAKER_CAST_TYPES',
        '    cast_type = device.get("cast_type")\n    return cast_type in SPEAKER_CAST_TYPES',
        [],
        run_items=["store_is_speaker_audio", "store_is_speaker_group",
                   "store_rejects_video_cast", "store_speakers_filters_video"],
        note="tách biểu thức thành biến trung gian",
    ),
    seed(
        "control_extract_url_variable",
        MEDIA,
        '        return f"http://{self._host}:{self.port}/{quote(relative.as_posix())}"',
        "        encoded = quote(relative.as_posix())\n"
        '        return f"http://{self._host}:{self.port}/{encoded}"',
        [],
        run_items=["media_url_uses_advertised_host", "media_url_quotes_special_chars",
                   "media_actually_serves_the_file"],
        note="tách phần mã hoá URL ra biến riêng",
    ),
]


# --------------------------------------------------------------------------


def run_eval(src_root, item_ids, timeout=60):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("GOOGLECAST_MCP_STORE", None)
    env.pop("GOOGLECAST_MCP_CACHE", None)
    proc = subprocess.run(
        [sys.executable, str(EVAL), "-q", "--json", "--only", ",".join(item_ids)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO),
        timeout=timeout,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("JSON "):
            return json.loads(line[5:])
    raise RuntimeError(
        "không đọc được kết quả eval:\n" + proc.stdout[-2000:] + "\n" + proc.stderr[-2000:]
    )


def apply_seed(case, work):
    target = work / case["path"]
    text = target.read_text(encoding="utf-8")
    hits = text.count(case["old"])
    if hits != 1:
        raise RuntimeError(
            f"lỗi gieo không áp được: đoạn mã gốc xuất hiện {hits} lần trong {case['path']} "
            "(mã sản phẩm đã đổi — phải cập nhật lỗi gieo, không được bỏ qua)"
        )
    target.write_text(text.replace(case["old"], case["new"]), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Kiểm ngược bài kiểm googlecast-mcp")
    ap.add_argument("--only", default="", help="chỉ chạy lỗi gieo có id chứa chuỗi này (cách phẩy)")
    ap.add_argument("--list", action="store_true", help="liệt kê lỗi gieo rồi thoát")
    args = ap.parse_args()

    if args.list:
        for case in SEEDS:
            kind = "ĐỐI CHỨNG" if case["control"] else "lỗi gieo "
            print(f"{kind} {case['id']:45} -> {', '.join(case['expect_red']) or '(phải XANH)'}")
        return 0

    only = [s.strip() for s in args.only.split(",") if s.strip()]
    cases = [c for c in SEEDS if not only or any(o in c["id"] for o in only)]
    total_seeds = len(cases)
    if total_seeds == 0:
        print("KHÔNG ĐẠT — không lỗi gieo nào khớp bộ lọc")
        return 2
    if only:
        print(f"(lượt RÚT GỌN: {total_seeds}/{len(SEEDS)} lỗi gieo — KHÔNG phải lượt đầy đủ)\n")

    # Danh mục mục eval tầng offline, để báo độ phủ theo chiều còn lại.
    listing = subprocess.run(
        [sys.executable, str(EVAL), "--list"], capture_output=True, text=True, cwd=str(REPO)
    )
    offline_items = {
        line.split()[1] for line in listing.stdout.splitlines() if line.startswith("offline")
    }
    covered = {i for c in SEEDS for i in c["expect_red"]}

    ran = 0
    good, bad = [], []
    started_all = time.monotonic()

    for case in cases:
        started = time.monotonic()
        verdict, detail = "ERROR", ""
        try:
            with tempfile.TemporaryDirectory(prefix="gcmcp-seed-") as tmp:
                work = Path(tmp) / "src"
                # Gieo vào BẢN SAO. Cây sản phẩm không bao giờ bị chạm tới.
                shutil.copytree(
                    SRC, work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
                )
                apply_seed(case, work)
                try:
                    result = run_eval(work, case["run_items"])
                except subprocess.TimeoutExpired:
                    # Bài kiểm treo là bài kiểm KHÔNG xanh. Với ca gieo lỗi đó
                    # là quan sát hợp lệ; với đối chứng thì là hỏng thật.
                    result = {
                        "ran": len(case["run_items"]), "total": len(case["run_items"]),
                        "pass": [], "fail": list(case["run_items"]), "error": [],
                    }
                    timed_out = True
                else:
                    timed_out = False

            red = set(result["fail"]) | set(result["error"])
            if result["ran"] != result["total"] or result["total"] == 0:
                verdict = "ERROR"
                detail = f"eval không chạy đủ mục: {result['ran']}/{result['total']}"
            elif timed_out and case["control"]:
                verdict, detail = "ĐỎ BỪA", "đối chứng vô hại mà eval treo quá hạn"
            elif case["control"]:
                verdict = "OK" if not red else "ĐỎ BỪA"
                if red:
                    detail = f"đối chứng vô hại mà vẫn đỏ: {sorted(red)}"
            else:
                missing = [i for i in case["expect_red"] if i not in red]
                verdict = "OK" if not missing else "LẼ-RA-ĐỎ-MÀ-XANH"
                if missing:
                    detail = f"gieo lỗi rồi mà các mục này vẫn xanh: {missing}"
                extra = sorted(red - set(case["expect_red"]))
                if not missing and extra:
                    detail = f"(đỏ thêm ngoài kỳ vọng, chấp nhận được: {extra})"
                if not missing and timed_out:
                    detail = "(đỏ bằng cách làm eval treo quá hạn — vẫn là quan sát được)"
        except Exception as exc:  # noqa: BLE001
            verdict, detail = "ERROR", f"{type(exc).__name__}: {exc}"
        finally:
            ran += 1  # đếm ĐÃ CHẠY trước khi biết kết quả

        took = time.monotonic() - started
        (good if verdict == "OK" else bad).append(case["id"])
        print(f"  [{verdict:17}] {case['id']} ({took:.1f}s)")
        if detail:
            print(f"        {detail}")

    print()
    print(f"đã chạy {ran}/{total_seeds} lỗi gieo đăng ký")
    print(
        f"đã phủ {len(covered & offline_items)}/{len(offline_items)} mục eval tầng offline "
        "bằng ít nhất một kỳ-vọng-đỏ"
    )
    uncovered = sorted(offline_items - covered)
    if uncovered:
        print(f"  CHƯA PHỦ: {', '.join(uncovered)}")
    print(f"  đạt {len(good)} · không đạt {len(bad)} · tổng thời gian {time.monotonic()-started_all:.0f}s")
    if bad:
        print(f"  không đạt: {', '.join(bad)}")

    if ran < total_seeds or bad:
        print("KHÔNG ĐẠT")
        return 1
    if not only and uncovered:
        print("KHÔNG ĐẠT — còn mục eval không lỗi gieo nào làm đỏ được (nghi phạm cấu trúc)")
        return 1
    print("ĐẠT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
