#!/usr/bin/env python3
"""Eval cho googlecast-mcp. Hai tầng.

TẦNG OFFLINE (mặc định) — chạy được ở bất kỳ máy nào, KHÔNG cần loa,
KHÔNG phát ra tiếng. Dùng một speaker store giả và thay thế (monkeypatch)
lớp cast + TTS, nên không có gói tin nào đi tới thiết bị thật.

TẦNG HARDWARE (chỉ khi truyền cờ --hardware) — CẢNH BÁO: tầng này CASTS
THẬT và SẼ PHÁT TIẾNG RA LOA TRONG NHÀ BẠN. Nó cần loa Google có thật
trên cùng LAN. Đừng chạy trong phòng có người đang ngủ hoặc đang họp.

Chạy:
    uv run --directory <repo> python _dong-goi/package/eval/eval_googlecast_mcp.py
    uv run --directory <repo> python _dong-goi/package/eval/eval_googlecast_mcp.py --hardware

Exit code 0 = tất cả mục PASS. 1 = có mục FAIL.
Mục SKIP (ví dụ không có internet cho TTS) không làm hỏng exit code,
nhưng được in rõ để người đọc biết chỗ nào CHƯA thực sự được kiểm.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

# ---------------------------------------------------------------------------
# Phải đặt TRƯỚC khi import package: SpeakerStore đọc biến môi trường ngay lúc
# khởi tạo, mà server.py khởi tạo CastManager ở cấp module. Nếu đặt sau,
# eval sẽ đụng vào file thật ~/.googlecast-mcp/speakers.json của người dùng.
# ---------------------------------------------------------------------------
_TMP = Path(tempfile.mkdtemp(prefix="googlecast-mcp-eval-"))
_FAKE_STORE = _TMP / "speakers.json"
_FAKE_DEVICES = [
    {"uuid": "u-1", "friendly_name": "Kitchen speaker", "cast_type": "audio",
     "model_name": "Google Home Mini", "host": "192.168.1.22", "port": 8009},
    {"uuid": "u-2", "friendly_name": "Bedroom speaker", "cast_type": "audio",
     "model_name": "Google Home Mini", "host": "192.168.1.23", "port": 8009},
    {"uuid": "u-3", "friendly_name": "Family speaker group", "cast_type": "group",
     "model_name": "Google Cast Group", "host": "192.168.1.22", "port": 42000},
    {"uuid": "u-4", "friendly_name": "Living room TV", "cast_type": "cast",
     "model_name": "Chromecast", "host": "192.168.1.30", "port": 8009},
]
_FAKE_STORE.write_text(json.dumps({"devices": _FAKE_DEVICES}), encoding="utf-8")
os.environ["GOOGLECAST_MCP_STORE"] = str(_FAKE_STORE)
os.environ["GOOGLECAST_MCP_CACHE"] = str(_TMP / "cache")

RESULTS: list[tuple[str, str, str]] = []  # (state, name, detail)


def record(state: str, name: str, detail: str = "") -> None:
    RESULTS.append((state, name, detail))
    mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}[state]
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def check(name: str, condition: bool, detail: str = "") -> None:
    record("PASS" if condition else "FAIL", name, detail)


def fn(tool):
    """Hàm thật đứng sau một tool đã đăng ký.

    Tuỳ phiên bản MCP SDK, @mcp.tool() có thể trả về chính hàm gốc hoặc một
    đối tượng Tool bọc nó ở thuộc tính .fn. Chấp nhận cả hai.
    """
    return getattr(tool, "fn", tool)


# ===========================================================================
# TẦNG OFFLINE
# ===========================================================================

def offline() -> None:
    # --- 1. Import được ---
    try:
        from googlecast_mcp import server as srv
        from googlecast_mcp import tts
        from googlecast_mcp.cast_manager import _guess_content_type
        from googlecast_mcp.speaker_store import is_speaker
        from googlecast_mcp.__main__ import _transport_security
    except Exception as exc:  # noqa: BLE001
        record("FAIL", "server import được", repr(exc))
        return
    record("PASS", "server import được")

    # --- 2. Đăng ký đúng 13 tool ---
    expected = {
        "say", "discover_devices", "list_speakers", "list_devices", "get_status",
        "play_media", "play", "pause", "stop", "seek", "set_volume", "set_muted",
        "quit_app",
    }
    tools = {t.name for t in asyncio.run(srv.mcp.list_tools())}
    check("đăng ký đúng 13 tool", tools == expected,
          f"{len(tools)} tool; thiếu={sorted(expected - tools)} thừa={sorted(tools - expected)}")

    # --- 3. is_speaker lọc đúng audio/group vs cast ---
    check("is_speaker: audio -> True", is_speaker({"cast_type": "audio"}) is True)
    check("is_speaker: group -> True", is_speaker({"cast_type": "group"}) is True)
    check("is_speaker: cast (thiết bị hình ảnh) -> False",
          is_speaker({"cast_type": "cast"}) is False)
    check("is_speaker: thiếu cast_type -> False", is_speaker({}) is False)

    # --- 4. _guess_content_type ---
    cases = {
        "http://h/a.mp3": "audio/mpeg",
        "http://h/a.MP3": "audio/mpeg",
        "http://h/a.mp3?x=1": "audio/mpeg",
        "http://h/a.mp4": "video/mp4",
        "http://h/a.flac": "audio/flac",
        "http://h/stream.m3u8": "application/x-mpegURL",
        "http://h/a.png": "image/png",
        "http://h/no-extension": "video/mp4",  # mặc định
    }
    bad = {u: (_guess_content_type(u), want) for u, want in cases.items()
           if _guess_content_type(u) != want}
    check("_guess_content_type đúng cho mọi trường hợp", not bad, str(bad))

    # --- 5. resolve_voice ---
    check("resolve_voice('female') -> HoaiMy", tts.resolve_voice("female") == "vi-VN-HoaiMyNeural")
    check("resolve_voice('male') -> NamMinh", tts.resolve_voice("male") == "vi-VN-NamMinhNeural")
    check("resolve_voice(None) -> giọng mặc định", tts.resolve_voice(None) == tts.DEFAULT_VOICE)
    check("resolve_voice(' MALE ') chuẩn hoá hoa/thường + khoảng trắng",
          tts.resolve_voice(" MALE ") == "vi-VN-NamMinhNeural")
    check("resolve_voice(id đầy đủ) giữ nguyên",
          tts.resolve_voice("vi-VN-HoaiMyNeural") == "vi-VN-HoaiMyNeural")

    # --- 6. _transport_security: allowlist phải có https và host không kèm port ---
    # Đây chính là hai ngõ cụt 421 / reverse-proxy đã tốn nhiều thời gian.
    sec = _transport_security("0.0.0.0", ["google-cast.adrec.cloud"], [])
    hosts = list(sec.allowed_hosts or [])
    origins = list(sec.allowed_origins or [])
    check("allowed_hosts chứa host KHÔNG kèm port (proxy 443 không gửi port)",
          "google-cast.adrec.cloud" in hosts, str(hosts))
    check("allowed_hosts cũng chứa dạng có port", "google-cast.adrec.cloud:*" in hosts)
    check("allowed_origins chứa scheme https (proxy đổi scheme)",
          "https://google-cast.adrec.cloud" in origins)
    check("allowed_origins chứa scheme http", "http://google-cast.adrec.cloud" in origins)
    check("bind 0.0.0.0 KHÔNG bị đưa vào allowlist (không phải địa chỉ client gọi)",
          "0.0.0.0" not in hosts, str(hosts))
    sec2 = _transport_security("0.0.0.0", [], ["http://192.168.1.99:8383"])
    check("origin trình duyệt truyền vào được thêm nguyên văn",
          "http://192.168.1.99:8383" in list(sec2.allowed_origins or []))

    # --- 7. say KHÔNG có target -> needs_speaker_selection và KHÔNG phát gì ---
    cast_calls: list[tuple] = []
    tts_calls: list[str] = []

    def fake_play_media(name, url, content_type=None, title=None):
        cast_calls.append((name, url, content_type, title))
        return {"speaker": name, "status": "playing"}

    async def fake_synthesize(text, voice=None, rate="+0%", **kw):
        tts_calls.append(text)
        return Path(_TMP / "fake.mp3")

    srv._manager.play_media = fake_play_media          # type: ignore[assignment]
    srv._manager.discover = lambda timeout=5.0: _FAKE_DEVICES  # type: ignore[assignment]
    _real_synthesize = srv.tts.synthesize
    srv.tts.synthesize = fake_synthesize               # type: ignore[assignment]
    srv._media_server.url_for = lambda p: "http://192.168.1.128:8766/fake.mp3"  # type: ignore[assignment]

    res = asyncio.run(fn(srv.say)(text="thử"))
    check("say thiếu target -> status=needs_speaker_selection",
          res.get("status") == "needs_speaker_selection", str(res.get("status")))
    check("say thiếu target -> KHÔNG cast gì cả", not cast_calls, str(cast_calls))
    check("say thiếu target -> KHÔNG gọi TTS", not tts_calls)
    check("say thiếu target -> trả kèm danh sách loa cho LLM hỏi lại",
          len(res.get("speakers") or []) == 3,
          f"{len(res.get('speakers') or [])} loa (phải là 3: 2 audio + 1 group)")

    # --- 8. say target='all' KHÔNG chứa phần tử cast_type=group ---
    # Nhóm phát QUA các thành viên; gộp cả hai = một loa vật lý nhận 2 luồng,
    # mà API vẫn báo 'playing' nên chỉ nghe mới phát hiện được.
    cast_calls.clear()
    res = asyncio.run(fn(srv.say)(text="thử", target="all"))
    names = [c[0] for c in cast_calls]
    check("say all -> KHÔNG gửi tới speaker group",
          "Family speaker group" not in names, str(names))
    check("say all -> gửi tới đúng các loa audio",
          sorted(names) == ["Bedroom speaker", "Kitchen speaker"], str(names))
    check("say all -> KHÔNG gửi tới thiết bị hình ảnh (cast)",
          "Living room TV" not in names)
    check("say all -> status ok", res.get("status") == "ok", str(res.get("status")))

    cast_calls.clear()
    res = asyncio.run(fn(srv.say)(text="thử", target="tất cả"))
    check("từ khoá tiếng Việt 'tất cả' tương đương 'all'",
          sorted(c[0] for c in cast_calls) == ["Bedroom speaker", "Kitchen speaker"])

    # --- 9. Nhóm vẫn gọi được bằng tên (sửa 'all' không làm mất nhóm) ---
    cast_calls.clear()
    asyncio.run(fn(srv.say)(text="thử", target="Family speaker group"))
    check("nhóm loa vẫn cast được khi gọi đích danh bằng tên",
          [c[0] for c in cast_calls] == ["Family speaker group"], str(cast_calls))

    # --- 10. Nhiều loa cách phẩy ---
    cast_calls.clear()
    asyncio.run(fn(srv.say)(text="thử", target="Kitchen speaker, Bedroom speaker"))
    check("target nhiều loa cách phẩy -> cast tới từng loa",
          sorted(c[0] for c in cast_calls) == ["Bedroom speaker", "Kitchen speaker"])

    # --- 11. Cô lập lỗi: một loa hỏng không kéo đổ cả lệnh ---
    def flaky(name, url, content_type=None, title=None):
        if name == "Ghost speaker":
            raise RuntimeError("wait timed out after 10 s")
        cast_calls.append((name, url, content_type, title))

    cast_calls.clear()
    srv._manager.play_media = flaky  # type: ignore[assignment]
    res = asyncio.run(fn(srv.say)(text="thử", target="Kitchen speaker, Ghost speaker"))
    states = {r["speaker"]: r["status"] for r in res["results"]}
    check("loa hỏng -> phần tử đó status=error", states.get("Ghost speaker") == "error", str(states))
    check("loa tốt vẫn playing khi loa khác hỏng", states.get("Kitchen speaker") == "playing")
    check("tổng thể vẫn ok khi có ít nhất một loa phát được",
          res.get("status") == "ok", str(res.get("status")))

    # --- 12. text rỗng -> ValueError (nhánh trước giờ chưa từng chạy thật) ---
    from googlecast_mcp import tts as real_tts
    real_tts.synthesize = _real_synthesize  # bỏ bản giả đã gắn ở trên
    try:
        asyncio.run(real_tts.synthesize("   "))
        record("FAIL", "TTS text rỗng -> ValueError", "không ném lỗi")
    except ValueError:
        record("PASS", "TTS text rỗng -> ValueError")
    except Exception as exc:  # noqa: BLE001
        record("FAIL", "TTS text rỗng -> ValueError", f"ném sai loại: {exc!r}")

    # --- 13. TTS sinh mp3 khác rỗng (CẦN INTERNET) ---
    try:
        path = asyncio.run(real_tts.synthesize("Cơm đã chín rồi", voice="female"))
        size = path.stat().st_size
        check("TTS sinh mp3 khác rỗng", size > 0, f"{size} byte")
        head = path.read_bytes()[:3]
        # Hoặc thẻ ID3, hoặc frame sync MPEG (11 bit 1 đầu tiên).
        header_ok = head[:3] == b"ID3" or (head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
        check("file TTS trông giống mp3 thật", header_ok)
    except Exception as exc:  # noqa: BLE001
        record("SKIP", "TTS sinh mp3 khác rỗng", f"cần internet tới edge-tts; {exc!r}")


# ===========================================================================
# TẦNG HARDWARE — PHÁT TIẾNG THẬT
# ===========================================================================

def hardware(speaker: str | None) -> None:
    print()
    print("!!! TẦNG HARDWARE: sắp CAST THẬT và PHÁT TIẾNG RA LOA TRONG NHÀ !!!")
    print()
    # Import lại sạch, KHÔNG dùng store giả của tầng offline.
    os.environ.pop("GOOGLECAST_MCP_STORE", None)
    os.environ.pop("GOOGLECAST_MCP_CACHE", None)
    for mod in [m for m in list(sys.modules) if m.startswith("googlecast_mcp")]:
        del sys.modules[mod]
    from googlecast_mcp import server as srv

    speakers = asyncio.run(fn(srv.list_speakers)())
    check("tìm thấy ít nhất một loa thật trên LAN", bool(speakers),
          f"{len(speakers)} loa")
    if not speakers:
        return
    name = speaker or speakers[0]["friendly_name"]
    res = asyncio.run(fn(srv.say)(text="Đây là bài kiểm tra tự động.", target=name))
    ok = res.get("status") == "ok"
    check(f"say phát được ra loa thật {name!r}", ok, str(res.get("results")))
    st = asyncio.run(fn(srv.get_status)(target=name))
    print(f"       trạng thái sau khi phát: {st}")
    print("       LƯU Ý: trạng thái 'playing' KHÔNG chứng minh âm thanh đúng.")
    print("       Chỉ tai người mới phát hiện được chồng luồng / phát cụt.")
    srv._media_server.stop()
    srv._manager.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hardware", action="store_true",
                   help="CHẠY TẦNG HARDWARE: cast thật, PHÁT TIẾNG ra loa thật.")
    p.add_argument("--speaker", default=None,
                   help="Tên loa dùng cho tầng hardware (mặc định: loa đầu tiên).")
    args = p.parse_args()

    print("=== TẦNG OFFLINE (không phát tiếng) ===")
    offline()
    if args.hardware:
        hardware(args.speaker)

    failed = [r for r in RESULTS if r[0] == "FAIL"]
    skipped = [r for r in RESULTS if r[0] == "SKIP"]
    print()
    print(f"Tổng: {len(RESULTS)} mục — "
          f"{len(RESULTS) - len(failed) - len(skipped)} PASS, "
          f"{len(failed)} FAIL, {len(skipped)} SKIP")
    for _, name, detail in skipped:
        print(f"  CHƯA KIỂM: {name} ({detail})")
    for _, name, detail in failed:
        print(f"  HỎNG: {name} ({detail})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
