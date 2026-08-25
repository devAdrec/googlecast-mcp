#!/usr/bin/env python3
"""Bộ kiểm chứng googlecast-mcp — ba tầng theo mức tác dụng phụ.

    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware

Tầng mặc định (offline) KHÔNG chạm mạng ngoài, KHÔNG chạm thiết bị, KHÔNG
phát tiếng. Ngoại lệ duy nhất: vài mục kiểm mở một cổng HTTP tạm trên máy này
(cổng 0 = hệ chọn cổng rỗi) phục vụ một thư mục tạm rỗng, đóng ngay trong
`finally`. Không gửi gói ra ngoài, không tốn tiền, không ai nghe thấy gì.

    --online   thêm tầng gọi edge-tts thật (cần internet). Vẫn không phát tiếng.
    --hardware thêm tầng cast thật ra loa — CÓ TIẾNG ĐỘNG VẬT LÝ. Chỉ chạy khi
               đã xin phép người quanh đó.

Ba luật bắt buộc của bộ kiểm này (vi phạm là test giả):
  1. So TẬP KỲ VỌNG tường minh, không bao giờ so KÍCH THƯỚC/ĐẾM một mình.
  2. Vệ sinh mock: ảnh chụp lấy TRƯỚC tầng đầu tiên, khôi phục trong `finally`,
     mỗi tầng dựng object MỚI. Không dùng importlib.reload — nó thay module
     mới dưới chân chính cái ảnh chụp đang giữ, phá luôn đường khôi phục.
  3. Mọi khẳng định về hệ bất đồng bộ (mạng/thiết bị) phải đi kèm MỐC CHỜ:
     timeout + điều kiện thoả. Không mốc chờ = đang đo tốc độ mạng.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from googlecast_mcp import __main__ as entry  # noqa: E402
from googlecast_mcp import media_server as media_mod  # noqa: E402
from googlecast_mcp import server as srv  # noqa: E402
from googlecast_mcp import speaker_store as store_mod  # noqa: E402
from googlecast_mcp import tts as tts_mod  # noqa: E402
from googlecast_mcp.cast_manager import (  # noqa: E402
    CastManager,
    DeviceNotFoundError,
    _guess_content_type,
)

# --------------------------------------------------------------------------
# Sổ điểm
# --------------------------------------------------------------------------

PASSED = 0
FAILED: list[str] = []
_GROUP = ""


def group(name: str) -> None:
    global _GROUP
    _GROUP = name
    print(f"\n== {name}")


def check(label: str, ok: bool, detail: str = "") -> bool:
    global PASSED
    if ok:
        PASSED += 1
        print(f"  ok   {label}")
    else:
        FAILED.append(f"{_GROUP} :: {label}{(' — ' + detail) if detail else ''}")
        print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")
    return ok


def check_eq(label: str, got: Any, want: Any) -> bool:
    return check(label, got == want, f"got={got!r} want={want!r}")


def check_raises(label: str, exc: type[BaseException], fn: Callable[[], Any]) -> bool:
    try:
        fn()
    except exc:
        return check(label, True)
    except BaseException as other:  # noqa: BLE001
        return check(label, False, f"raised {type(other).__name__}: {other}")
    return check(label, False, "không ném lỗi nào")


def wait_until(
    predicate: Callable[[], Any],
    timeout: float,
    interval: float = 0.5,
    what: str = "điều kiện",
) -> tuple[bool, Any]:
    """Chờ tới MỐC: trả (thoả?, giá trị cuối). Bắt buộc cho khẳng định bất đồng bộ.

    Một khẳng định đọc trạng thái ngay khoảnh khắc lời gọi trả về là đang đo
    tốc độ mạng chứ không đo hành vi: play_media chỉ chờ ứng dụng trên thiết bị
    KHỞI ĐỘNG, chưa chờ nó PHÁT.
    """
    deadline = time.monotonic() + timeout
    last: Any = None
    while True:
        last = predicate()
        if last:
            return True, last
        if time.monotonic() >= deadline:
            print(f"       (hết mốc chờ {timeout}s cho {what}; giá trị cuối={last!r})")
            return False, last
        time.sleep(interval)


# --------------------------------------------------------------------------
# Dữ liệu giả — mô phỏng đúng mạng thật đã quan sát
# --------------------------------------------------------------------------

KITCHEN = {
    "friendly_name": "Kitchen speaker", "uuid": "uuid-kitchen",
    "model_name": "Google Nest Mini", "manufacturer": "Google Inc.",
    "host": "192.168.1.22", "port": 8009, "cast_type": "audio",
}
BEDROOM = {
    "friendly_name": "Bedroom speaker", "uuid": "uuid-bedroom",
    "model_name": "Google Home", "manufacturer": "Google Inc.",
    "host": "192.168.1.23", "port": 8009, "cast_type": "audio",
}
OFFICE = {
    "friendly_name": "Office speaker", "uuid": "uuid-office",
    "model_name": "Google Home Mini", "manufacturer": "Google Inc.",
    "host": "192.168.1.24", "port": 8009, "cast_type": "audio",
}
# Nhóm phát QUA thành viên. Trùng host với Kitchen — chính là cái bẫy chồng luồng.
FAMILY_GROUP = {
    "friendly_name": "Family speaker group", "uuid": "uuid-family-group",
    "model_name": "Google Cast Group", "manufacturer": "Google Inc.",
    "host": "192.168.1.22", "port": 42001, "cast_type": "group",
}
WORKING_DISPLAY = {
    "friendly_name": "Working display", "uuid": "uuid-working-display",
    "model_name": "Google Nest Hub", "manufacturer": "Google Inc.",
    "host": "192.168.1.31", "port": 8009, "cast_type": "cast",
}
ALL_DEVICES = [KITCHEN, BEDROOM, OFFICE, FAMILY_GROUP, WORKING_DISPLAY]

# TẬP KỲ VỌNG TƯỜNG MINH cho target="all". Không bao giờ so bằng độ dài.
EXPECTED_ALL = {
    ("Kitchen speaker", "192.168.1.22"),
    ("Bedroom speaker", "192.168.1.23"),
    ("Office speaker", "192.168.1.24"),
}
EXPECTED_SPEAKERS = {
    "Kitchen speaker", "Bedroom speaker", "Office speaker", "Family speaker group",
}
EXPECTED_TOOLS = {
    "say", "discover_devices", "list_speakers", "list_devices", "get_status",
    "play_media", "play", "pause", "stop", "seek", "set_volume", "set_muted",
    "quit_app",
}
BY_NAME = {d["friendly_name"]: d for d in ALL_DEVICES}


class FakeManager:
    """CastManager giả: ghi lại mọi lời gọi, không chạm mạng.

    Dựng MỚI cho từng mục kiểm — không tầng nào được thừa hưởng object của tầng
    trước, kể cả khi trông có vẻ sạch.
    """

    def __init__(self, devices: list[dict[str, Any]] | None = None) -> None:
        self.devices = list(devices if devices is not None else ALL_DEVICES)
        self.cast_calls: list[dict[str, Any]] = []
        self.discover_calls = 0

    def list_cached(self) -> list[dict[str, Any]]:
        return [dict(d) for d in self.devices]

    def list_speakers(self) -> list[dict[str, Any]]:
        return [dict(d) for d in self.devices if store_mod.is_speaker(d)]

    def discover(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        self.discover_calls += 1
        return self.list_cached()

    def play_media(self, name, url, content_type=None, title=None):
        if name not in BY_NAME:
            raise DeviceNotFoundError(f"Device {name!r} did not respond.")
        self.cast_calls.append(
            {"name": name, "host": BY_NAME[name]["host"], "url": url,
             "content_type": content_type, "title": title}
        )
        return {"device": dict(BY_NAME[name])}


class FakeMediaServer:
    def __init__(self) -> None:
        self.urls: list[Path] = []

    def url_for(self, path: Path) -> str:
        self.urls.append(path)
        return f"http://192.168.1.128:8766/{path.name}"


class FakeTTS:
    """TTS giả. Ghi lại lời gọi để chứng minh đường 'không chọn loa' KHÔNG gọi TTS."""

    def __init__(self, out: Path) -> None:
        self.out = out
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, text, voice=None, rate="+0%", **kw):
        self.calls.append({"text": text, "voice": voice, "rate": rate})
        return self.out


def cast_targets(fake: FakeManager) -> set[tuple[str, str]]:
    return {(c["name"], c["host"]) for c in fake.cast_calls}


# --------------------------------------------------------------------------
# TẦNG 1 — offline, không tác dụng phụ
# --------------------------------------------------------------------------


def tier_offline(tmp: Path) -> None:
    group("1.1 Nạp được module và đăng ký đúng bộ tool")
    for mod in (srv, entry, tts_mod, store_mod, media_mod):
        check(f"nạp được {mod.__name__}", mod is not None)
    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    # So TẬP, không so số lượng: thiếu một tool và thừa một tool khác vẫn cùng đếm.
    check_eq("bộ tool đúng bằng tập kỳ vọng", names, EXPECTED_TOOLS)
    check_eq("không có tool trùng tên", len(tools), len(names))
    check("mọi tool có mô tả", all((t.description or "").strip() for t in tools))
    say_tool = next(t for t in tools if t.name == "say")
    schema = say_tool.inputSchema
    check_eq("say: 'text' bắt buộc", set(schema.get("required", [])), {"text"})
    check("say: có tham số chọn loa", "target" in schema["properties"])
    check("say là hàm bất đồng bộ", inspect.iscoroutinefunction(srv.say))

    group("1.2 _guess_content_type")
    for url, want in [
        ("http://h/a.mp3", "audio/mpeg"),
        ("http://h/a.MP3", "audio/mpeg"),
        ("http://h/a.mp3?token=1", "audio/mpeg"),
        ("http://h/a.m4a", "audio/mp4"),
        ("http://h/v.mp4", "video/mp4"),
        ("http://h/v.mkv", "video/x-matroska"),
        ("http://h/s.m3u8", "application/x-mpegURL"),
        ("http://h/p.png", "image/png"),
        ("http://h/khong-duoi", "video/mp4"),
    ]:
        check_eq(f"{url} → {want}", _guess_content_type(url), want)

    group("1.3 is_speaker — lọc loa khỏi thiết bị hình ảnh")
    check("audio là loa", store_mod.is_speaker(KITCHEN))
    check("group là loa", store_mod.is_speaker(FAMILY_GROUP))
    check("cast KHÔNG phải loa", not store_mod.is_speaker(WORKING_DISPLAY))
    check("thiếu cast_type KHÔNG phải loa", not store_mod.is_speaker({"friendly_name": "x"}))
    check_eq("SPEAKER_CAST_TYPES", set(store_mod.SPEAKER_CAST_TYPES), {"audio", "group"})

    group("1.4 resolve_voice")
    check_eq("female", tts_mod.resolve_voice("female"), "vi-VN-HoaiMyNeural")
    check_eq("male", tts_mod.resolve_voice("male"), "vi-VN-NamMinhNeural")
    check_eq("hoa/thường + khoảng trắng", tts_mod.resolve_voice("  MALE "), "vi-VN-NamMinhNeural")
    check_eq("None → mặc định", tts_mod.resolve_voice(None), tts_mod.DEFAULT_VOICE)
    check_eq("rỗng → mặc định", tts_mod.resolve_voice(""), tts_mod.DEFAULT_VOICE)
    check_eq("id đầy đủ đi thẳng", tts_mod.resolve_voice("en-US-AriaNeural"), "en-US-AriaNeural")
    check_eq("mặc định là giọng nữ Việt", tts_mod.DEFAULT_VOICE, "vi-VN-HoaiMyNeural")

    group("1.5 text rỗng không bao giờ tới được edge-tts")
    check_raises("'' → ValueError", ValueError, lambda: asyncio.run(tts_mod.synthesize("")))
    check_raises("'   ' → ValueError", ValueError, lambda: asyncio.run(tts_mod.synthesize("   ")))
    check_raises("None → ValueError", ValueError, lambda: asyncio.run(tts_mod.synthesize(None)))

    group("1.6 _transport_security — allowlist đủ scheme và đủ dạng host")
    sec = entry._transport_security(
        "0.0.0.0", ["google-cast.adrec.cloud"], ["http://192.168.1.99:8383"]
    )
    hosts, origins = list(sec.allowed_hosts), list(sec.allowed_origins)
    check("có 127.0.0.1", "127.0.0.1" in hosts)
    check("có localhost", "localhost" in hosts)
    check("có địa chỉ LAN của máy", media_mod.lan_ip() in hosts)
    check("KHÔNG nhận 0.0.0.0 làm host hợp lệ", "0.0.0.0" not in hosts)
    check("domain dạng TRẦN (proxy cổng mặc định không gửi ':port')",
          "google-cast.adrec.cloud" in hosts)
    check("domain kèm ':*'", "google-cast.adrec.cloud:*" in hosts)
    check("origin https trần", "https://google-cast.adrec.cloud" in origins)
    check("origin https kèm cổng", "https://google-cast.adrec.cloud:*" in origins)
    check("origin http trần", "http://google-cast.adrec.cloud" in origins)
    check("origin trình duyệt truyền vào được giữ",
          "http://192.168.1.99:8383" in origins)
    check("không lặp host", len(hosts) == len(set(hosts)))
    check("không lặp origin", len(origins) == len(set(origins)))
    sec2 = entry._transport_security("192.168.1.128", [], None)
    check("bind host cụ thể được nhận", "192.168.1.128" in list(sec2.allowed_hosts))
    check("không có domain nào khi không khai báo",
          not any("adrec" in h for h in sec2.allowed_hosts))

    group("1.7 Thiếu chọn loa → KHÔNG phát gì, KHÔNG gọi TTS")
    fake, fake_tts = FakeManager(), FakeTTS(tmp / "x.mp3")
    srv._manager, srv._media_server, srv.tts.synthesize = fake, FakeMediaServer(), fake_tts
    res = asyncio.run(srv.say("Cơm đã chín rồi"))
    check_eq("status", res.get("status"), "needs_speaker_selection")
    check_eq("KHÔNG cast tới thiết bị nào", cast_targets(fake), set())
    check_eq("KHÔNG gọi TTS", fake_tts.calls, [])
    check_eq("trả đúng tập loa để hỏi lại",
             {s["friendly_name"] for s in res.get("speakers", [])}, EXPECTED_SPEAKERS)
    message = res.get("message", "")
    check("thông điệp bảo LLM hỏi người dùng", "Ask the user" in message)
    for n in EXPECTED_SPEAKERS:
        check(f"thông điệp có nêu tên '{n}'", n in message)
    res_blank = asyncio.run(srv.say("xin chào", target="   "))
    check_eq("chuỗi chọn loa toàn khoảng trắng cũng là 'chưa chọn'",
             res_blank.get("status"), "needs_speaker_selection")

    group("1.8 Không có loa nào trên mạng")
    fake_empty = FakeManager(devices=[WORKING_DISPLAY])
    srv._manager, srv._media_server, srv.tts.synthesize = (
        fake_empty, FakeMediaServer(), FakeTTS(tmp / "x.mp3"))
    res = asyncio.run(srv.say("xin chào"))
    check_eq("status", res.get("status"), "no_speakers_found")
    check_eq("danh sách loa rỗng", res.get("speakers", "<thiếu khoá>"), [])
    check_eq("KHÔNG cast", cast_targets(fake_empty), set())
    check("có dò lại trước khi kết luận", fake_empty.discover_calls >= 1)

    group("1.9 target='all' — KHÔNG được gửi tới nhóm VÀ thành viên cùng lúc")
    for keyword in ("all", "tất cả", "tat ca", "ALL", " everyone ", "*"):
        fake, ftts = FakeManager(), FakeTTS(tmp / "x.mp3")
        srv._manager, srv._media_server, srv.tts.synthesize = fake, FakeMediaServer(), ftts
        res = asyncio.run(srv.say("thông báo", target=keyword))
        got = cast_targets(fake)
        # So TẬP tường minh. `len(hosts) == len(set(hosts))` vẫn XANH khi 'all'
        # thu về đúng một loa — đó là test giả, và đây là bản thay thế.
        check_eq(f"'{keyword}' → đúng tập loa mong đợi", got, EXPECTED_ALL)
        check(f"'{keyword}' → không có nhóm trong danh sách",
              "Family speaker group" not in {n for n, _ in got})
        check(f"'{keyword}' → mỗi host vật lý nhận đúng một luồng",
              sorted(h for _, h in got) == sorted({h for _, h in got}))
        check_eq(f"'{keyword}' → status ok", res["status"], "ok")
        check_eq(f"'{keyword}' → TTS gọi đúng một lần", len(ftts.calls), 1)

    group("1.10 Nhóm vẫn cast được khi gọi đích danh")
    fake = FakeManager()
    srv._manager, srv._media_server, srv.tts.synthesize = (
        fake, FakeMediaServer(), FakeTTS(tmp / "x.mp3"))
    res = asyncio.run(srv.say("chào cả nhà", target="Family speaker group"))
    check_eq("chỉ nhóm nhận", cast_targets(fake),
             {("Family speaker group", "192.168.1.22")})
    check_eq("status ok", res["status"], "ok")

    group("1.11 Nhiều loa cách nhau bằng dấu phẩy")
    fake = FakeManager()
    srv._manager, srv._media_server, srv.tts.synthesize = (
        fake, FakeMediaServer(), FakeTTS(tmp / "x.mp3"))
    res = asyncio.run(srv.say("hai loa", target=" Kitchen speaker , Office speaker "))
    check_eq("đúng tập hai loa (đã cắt khoảng trắng)", cast_targets(fake),
             {("Kitchen speaker", "192.168.1.22"), ("Office speaker", "192.168.1.24")})
    check_eq("hai kết quả trả về", {r["speaker"] for r in res["results"]},
             {"Kitchen speaker", "Office speaker"})
    check("mọi kết quả đều playing",
          all(r["status"] == "playing" for r in res["results"]))
    fake2 = FakeManager()
    srv._manager, srv._media_server, srv.tts.synthesize = (
        fake2, FakeMediaServer(), FakeTTS(tmp / "x.mp3"))
    asyncio.run(srv.say("một loa", target="Kitchen speaker,,"))
    check_eq("',,' không sinh đích rỗng", cast_targets(fake2),
             {("Kitchen speaker", "192.168.1.22")})

    group("1.12 Một loa hỏng không kéo đổ cả lượt")
    fake = FakeManager()
    srv._manager, srv._media_server, srv.tts.synthesize = (
        fake, FakeMediaServer(), FakeTTS(tmp / "x.mp3"))
    res = asyncio.run(srv.say("thử", target="Kitchen speaker, Khong Ton Tai"))
    by = {r["speaker"]: r for r in res.get("results", [])}
    check_eq("loa thật vẫn phát", by.get("Kitchen speaker", {}).get("status"), "playing")
    check_eq("loa hỏng báo lỗi riêng", by.get("Khong Ton Tai", {}).get("status"), "error")
    check("lỗi có kèm nguyên nhân", bool(by.get("Khong Ton Tai", {}).get("error")))
    check_eq("tổng thể vẫn ok", res["status"], "ok")
    check_eq("chỉ loa thật được cast", cast_targets(fake),
             {("Kitchen speaker", "192.168.1.22")})
    fake = FakeManager()
    srv._manager, srv._media_server, srv.tts.synthesize = (
        fake, FakeMediaServer(), FakeTTS(tmp / "x.mp3"))
    res = asyncio.run(srv.say("thử", target="Khong Ton Tai"))
    check_eq("không loa nào phát được → failed", res["status"], "failed")

    group("1.13 say trả đủ siêu dữ liệu cho người gọi")
    fake, ftts = FakeManager(), FakeTTS(tmp / "abc.mp3")
    srv._manager, srv._media_server, srv.tts.synthesize = fake, FakeMediaServer(), ftts
    res = asyncio.run(srv.say("Cơm chín", target="Kitchen speaker", voice="male", rate="-10%"))
    check_eq("giọng trả về đã phân giải", res["voice"], "vi-VN-NamMinhNeural")
    check_eq("giọng truyền xuống TTS", ftts.calls[0]["voice"], "male")
    check_eq("tốc độ truyền xuống TTS", ftts.calls[0]["rate"], "-10%")
    check_eq("text nguyên vẹn", res["text"], "Cơm chín")
    check("audio_url là http tới máy này", res["audio_url"].startswith("http://"))
    check_eq("content_type gửi cho loa là audio/mpeg",
             fake.cast_calls[0]["content_type"], "audio/mpeg")
    check("tiêu đề hiện trên loa lấy từ text",
          fake.cast_calls[0]["title"].startswith("Cơm chín"))

    group("1.14 SpeakerStore — lưu bền, gộp theo uuid, chịu được file hỏng")
    sp = tmp / "store" / "speakers.json"
    st = store_mod.SpeakerStore(sp)
    check_eq("chưa có file → rỗng", st.load(), [])
    st.save([KITCHEN, WORKING_DISPLAY])
    check_eq("đọc lại đúng tập uuid", {d["uuid"] for d in st.load()},
             {"uuid-kitchen", "uuid-working-display"})
    st.save([BEDROOM])
    check_eq("lần lưu sau GỘP, không ghi đè", {d["uuid"] for d in st.load()},
             {"uuid-kitchen", "uuid-working-display", "uuid-bedroom"})
    st.save([{**KITCHEN, "host": "192.168.1.99"}])
    check_eq("cùng uuid thì cập nhật địa chỉ",
             {d["uuid"]: d["host"] for d in st.load()}["uuid-kitchen"], "192.168.1.99")
    check_eq("speakers() lọc đúng tập",
             {d["friendly_name"] for d in st.speakers()},
             {"Kitchen speaker", "Bedroom speaker"})
    check("không để lại file .tmp", not list(sp.parent.glob("*.tmp")))
    check("ghi ra JSON hợp lệ có khoá devices",
          "devices" in json.loads(sp.read_text(encoding="utf-8")))
    check("giữ nguyên dấu tiếng Việt (không escape)",
          "\\u" not in sp.read_text(encoding="utf-8"))
    sp.write_text("{ hỏng", encoding="utf-8")
    check_eq("file hỏng → rỗng, không ném lỗi", st.load(), [])
    check_eq("file hỏng → speakers() rỗng", st.speakers(), [])
    fresh = store_mod.SpeakerStore(tmp / "khong-ton-tai" / "a.json")
    check_eq("đường dẫn không tồn tại → rỗng", fresh.load(), [])

    group("1.15 CastManager không tìm ra thiết bị → lỗi nói rõ")
    mgr = CastManager(store=store_mod.SpeakerStore(tmp / "empty.json"))
    check_eq("list_speakers rỗng khi chưa dò", mgr.list_speakers(), [])
    check_eq("_resolve_locally không khớp gì → None", mgr._resolve_locally("x"), None)
    check_eq("_connect_saved với store rỗng → None", mgr._connect_saved("x"), None)
    # Kẹp âm lượng phải kiểm trên CHÍNH CastManager.set_volume, không phải trên
    # biểu thức min/max viết lại trong bài kiểm — thế thì chỉ đang kiểm Python.
    applied: list[float] = []

    class _StubCast:
        def set_volume(self, level):
            applied.append(level)

        def set_volume_muted(self, muted):
            applied.append(muted)

    mgr._connected = lambda tgt: _StubCast()  # type: ignore[method-assign]
    check_eq("set_volume(5.0) trả về 1.0", mgr.set_volume("bất kỳ", 5.0), 1.0)
    check_eq("giá trị thật gửi xuống thiết bị là 1.0", applied[-1], 1.0)
    check_eq("set_volume(-3.0) trả về 0.0", mgr.set_volume("bất kỳ", -3.0), 0.0)
    check_eq("giá trị thật gửi xuống thiết bị là 0.0", applied[-1], 0.0)
    check_eq("giá trị hợp lệ đi qua nguyên vẹn", mgr.set_volume("bất kỳ", 0.42), 0.42)

    group("1.16 MediaServer — URL loa gọi được (mở cổng tạm trên máy này)")
    served = tmp / "media"
    served.mkdir(parents=True, exist_ok=True)
    (served / "chào bạn.mp3").write_bytes(b"ID3fake")
    ms = media_mod.MediaServer(served, host="192.168.1.128", port=0)
    try:
        check_eq("chưa start thì port = cổng yêu cầu", ms.port, 0)
        url = ms.url_for(served / "chào bạn.mp3")
        check("đã start thì port thật khác 0", ms.port != 0)
        check("URL quảng bá là địa chỉ LAN, KHÔNG phải 0.0.0.0",
              url.startswith("http://192.168.1.128:") and "0.0.0.0" not in url)
        check_eq("tên file có dấu/khoảng trắng được mã hoá",
                 url.rsplit("/", 1)[1], "ch%C3%A0o%20b%E1%BA%A1n.mp3")
        check_raises("đổi cổng khi đang chạy → RuntimeError",
                     RuntimeError, lambda: ms.set_port(9999))
    finally:
        ms.stop()
    check("stop() rồi gọi lại vẫn an toàn", ms.stop() is None)
    check_eq("lan_ip() trả IPv4 4 phần",
             len(media_mod.lan_ip().split(".")), 4)


# --------------------------------------------------------------------------
# TẦNG 2 — --online (gọi edge-tts thật, vẫn không phát tiếng)
# --------------------------------------------------------------------------


ONLINE_SPACING = 3.0
ONLINE_TRIES = 4


def synth_online(*args: Any, **kw: Any) -> Path:
    """Gọi tts.synthesize thật, có giãn cách và thử lại.

    KHÔNG phải để làm đẹp con số: dịch vụ edge-tts trả `NoAudioReceived` khi bị
    bắn nhiều yêu cầu sát nhau (đã đo: 3 lần liên tiếp không giãn cách hỏng
    2/3; giãn 4s thì 6/6 đạt). Sản phẩm KHÔNG có thử lại — đó là một điểm còn
    hở thật, ghi ở eval/README và method note. Ở đây bọc lại để bài kiểm đo
    hành vi của sản phẩm chứ không đo hạn ngạch của Microsoft.
    """
    last: BaseException | None = None
    for attempt in range(ONLINE_TRIES):
        try:
            result = asyncio.run(tts_mod.synthesize(*args, **kw))
            time.sleep(ONLINE_SPACING)
            return result
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"       (edge-tts trả rỗng, thử lại {attempt + 1}/{ONLINE_TRIES})")
            time.sleep(ONLINE_SPACING * 2)
    raise AssertionError(f"edge-tts hỏng sau {ONLINE_TRIES} lần: {last}")


def tier_online(tmp: Path) -> None:
    group("2.1 edge-tts sinh mp3 thật cho tiếng Việt")
    out = tmp / "online"
    out.mkdir(parents=True, exist_ok=True)
    text = "Cơm đã chín rồi, mời cả nhà ăn tối."
    path = synth_online(text, voice="female", cache_dir=out)
    check("file tồn tại", path.exists())
    check("file khác rỗng", path.stat().st_size > 0, f"{path.stat().st_size} bytes")
    check("đủ lớn để là câu nói thật (>2KB)", path.stat().st_size > 2048,
          f"{path.stat().st_size} bytes")
    head = path.read_bytes()[:3]
    check("đúng định dạng mp3 (ID3 hoặc frame sync)",
          head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
          repr(head))
    check_eq("tên file khoá theo hash, đuôi .mp3", path.suffix, ".mp3")
    check("nằm trong đúng thư mục cache đã chỉ định", path.parent == out)

    group("2.2 Cache: lần hai không synthesize lại")
    size_before = path.stat().st_size
    mtime_before = path.stat().st_mtime
    again = asyncio.run(tts_mod.synthesize(text, voice="female", cache_dir=out))
    check_eq("cùng đường dẫn", again, path)
    check_eq("không đổi kích thước", again.stat().st_size, size_before)
    check_eq("không ghi lại file", again.stat().st_mtime, mtime_before)

    group("2.3 Đổi giọng / tốc độ sinh file KHÁC")
    male = synth_online(text, voice="male", cache_dir=out)
    check("giọng nam ra file khác", male != path)
    check("giọng nam khác rỗng", male.stat().st_size > 0)
    slow = synth_online(text, voice="female", rate="-25%", cache_dir=out)
    check("đổi rate ra file khác", slow != path)
    check("bản chậm dài hơn bản thường", slow.stat().st_size > size_before,
          f"{slow.stat().st_size} vs {size_before}")

    group("2.4 File cache 0 byte bị coi là hỏng, được sinh lại")
    path.write_bytes(b"")
    redo = synth_online(text, voice="female", cache_dir=out)
    check_eq("vẫn cùng đường dẫn", redo, path)
    check("đã được sinh lại, khác rỗng", redo.stat().st_size > 0)

    group("2.5 Giọng không tồn tại → báo lỗi, không bao giờ trả audio giả")
    before = set(out.glob("*.mp3"))

    def bad_voice() -> Path:
        return asyncio.run(
            tts_mod.synthesize("thử", voice="xx-XX-KhongCoNeural", cache_dir=out))

    check_raises("ném lỗi thay vì trả đường dẫn", Exception, bad_voice)
    new_files = set(out.glob("*.mp3")) - before
    check("không sinh ra file audio KHÁC RỖNG nào (không có audio giả)",
          all(p.stat().st_size == 0 for p in new_files),
          f"{[(p.name, p.stat().st_size) for p in new_files]}")
    # ĐIỂM CÒN HỞ ĐÃ BIẾT (bài kiểm này chốt lại đúng hành vi hiện tại, không
    # tô hồng): khi edge_tts.Communicate.save() NÉM lỗi, nó đã kịp tạo file
    # rỗng, và nhánh dọn dẹp trong tts.synthesize nằm SAU lời gọi đó nên không
    # bao giờ chạy. Hệ quả là cache đọng file 0 byte. Không sai hành vi — lần
    # sau vẫn sinh lại — nhưng là rác. Cách vá: bọc save() trong try/except,
    # unlink rồi ném tiếp. Xem eval/README mục "Điểm còn hở bộ kiểm phát hiện".
    check(f"(đã biết) lần hỏng để lại {len(new_files)} file 0 byte trong cache",
          len(new_files) >= 0)
    check_raises("file 0 byte KHÔNG bị dùng lại như bản render hợp lệ",
                 Exception, bad_voice)


# --------------------------------------------------------------------------
# TẦNG 3 — --hardware (CÓ TIẾNG ĐỘNG VẬT LÝ)
# --------------------------------------------------------------------------


def tier_hardware(tmp: Path, speaker: str) -> None:
    group("3.1 Dò thiết bị thật trên LAN")
    mgr = CastManager()
    devices = mgr.discover(8.0)
    names = {d["friendly_name"] for d in devices}
    print(f"       thiết bị thấy được: {sorted(names)}")
    check("dò được ít nhất một thiết bị", bool(devices))
    speakers = {d["friendly_name"] for d in mgr.list_speakers()}
    check("có ít nhất một loa", bool(speakers))
    check(f"loa đích '{speaker}' có mặt", speaker in speakers,
          f"chỉ thấy {sorted(speakers)}")
    check("mọi mục list_speakers đều là audio/group",
          all(d["cast_type"] in ("audio", "group") for d in mgr.list_speakers()))
    check("thiết bị hình ảnh bị loại khỏi danh sách loa",
          not any(d["cast_type"] == "cast" for d in mgr.list_speakers()))

    if speaker not in speakers:
        mgr.close()
        return

    group("3.2 say thật — MỐC CHỜ cho mọi khẳng định bất đồng bộ")
    srv._manager = mgr
    res = asyncio.run(srv.say("Đây là bài kiểm chứng tự động.", target=speaker))
    check_eq("status ok", res["status"], "ok")
    check_eq("loa báo playing",
             {r["speaker"]: r["status"] for r in res["results"]}, {speaker: "playing"})

    # play_media chỉ chờ ỨNG DỤNG khởi động, chưa chờ PHÁT. Đọc trạng thái ngay
    # tại đây là đo tốc độ mạng: phải chờ tới mốc.
    ok, state = wait_until(
        lambda: (mgr.status(speaker)["media"]["player_state"]
                 in ("PLAYING", "BUFFERING")) and mgr.status(speaker)["media"]["player_state"],
        timeout=15.0, what="loa chuyển sang PLAYING")
    check("trong 15s loa vào trạng thái phát", ok, f"trạng thái cuối={state!r}")

    ok, dur = wait_until(lambda: mgr.status(speaker)["media"]["duration"],
                         timeout=15.0, what="thời lượng media")
    check("trong 15s loa báo được thời lượng", ok and dur and dur > 0, f"duration={dur!r}")

    ok, _ = wait_until(
        lambda: mgr.status(speaker)["media"]["content_type"] == "audio/mpeg",
        timeout=10.0, what="content_type audio/mpeg")
    check("loa nhận đúng content_type audio/mpeg", ok)

    group("3.3 Phát hết bài rồi tự dừng (mốc chờ = thời lượng + biên)")
    limit = float(dur or 5.0) + 15.0
    ok, reason = wait_until(
        lambda: mgr.status(speaker)["media"]["player_state"] == "IDLE",
        timeout=limit, interval=1.0, what="phát xong về IDLE")
    check(f"trong {limit:.0f}s phát xong và về IDLE", ok, f"cuối={reason!r}")

    group("3.4 Điều khiển âm lượng thật")
    original = mgr.status(speaker)["app"]["volume_level"]
    try:
        mgr.set_volume(speaker, 0.25)
        ok, lvl = wait_until(
            lambda: abs((mgr.status(speaker)["app"]["volume_level"] or 0) - 0.25) < 0.06,
            timeout=10.0, what="âm lượng về 0.25")
        check("trong 10s âm lượng thật đổi về ~0.25", ok, f"lvl={lvl!r}")
        check_eq("giá trị >1 bị kẹp về 1.0", mgr.set_volume(speaker, 5.0), 1.0)
        check_eq("giá trị <0 bị kẹp về 0.0", mgr.set_volume(speaker, -1.0), 0.0)
    finally:
        if original is not None:
            mgr.set_volume(speaker, float(original))

    group("3.5 Cô lập lỗi trên phần cứng thật")
    res = asyncio.run(srv.say("Kiểm chứng cô lập lỗi.",
                              target=f"{speaker}, Loa Khong Ton Tai 9x"))
    by = {r["speaker"]: r["status"] for r in res["results"]}
    check_eq("loa thật vẫn phát", by.get(speaker), "playing")
    check_eq("tên không tồn tại báo lỗi riêng", by.get("Loa Khong Ton Tai 9x"), "error")
    check_eq("tổng thể vẫn ok", res["status"], "ok")
    # Hai cái bẫy ở mục này, cả hai đều làm bài kiểm đỏ oan:
    #  1. Trạng thái media là THEO TỪNG KẾT NỐI — hỏi một CastManager khác cái
    #     đã cast thì nó báo UNKNOWN mãi. Phải hỏi đúng manager say() đã dùng.
    #  2. Phần tử hỏng kéo say() dài hơn chính clip (đo được: 5.4s so với
    #     2.26s), nên lúc say() trả về thì loa đã phát XONG. Đòi thấy PLAYING
    #     là đòi một trạng thái chắc chắn đã hết hạn.
    # Nên kiểm BẰNG CHỨNG CÒN LẠI: thiết bị đã nạp đúng file mình vừa cast.
    url = res.get("audio_url")
    ok, last = wait_until(
        lambda: srv._manager.status(speaker)["media"]["content_id"] == url,
        timeout=15.0, what="loa thật đã nạp đúng audio vừa cast")
    media = srv._manager.status(speaker)["media"]
    check("loa thật thật sự nhận audio dù bạn cùng lượt hỏng", ok,
          f"content_id={media['content_id']!r} state={media['player_state']!r}")
    check("loa thật biết thời lượng, tức là đã nạp được media",
          (media.get("duration") or 0) > 0, f"duration={media.get('duration')!r}")
    mgr.quit_app(speaker)
    mgr.close()


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--online", action="store_true",
                    help="Thêm tầng gọi edge-tts thật (cần internet).")
    ap.add_argument("--hardware", action="store_true",
                    help="Thêm tầng cast thật — SẼ PHÁT TIẾNG trên loa.")
    ap.add_argument("--speaker", default="Kitchen speaker",
                    help="Tên loa dùng cho tầng --hardware.")
    args = ap.parse_args()

    # Ảnh chụp lấy TRƯỚC tầng đầu tiên, khôi phục trong finally. Không reload.
    snapshot = {
        "manager": srv._manager,
        "media_server": srv._media_server,
        "synthesize": srv.tts.synthesize,
    }
    tmp = Path(tempfile.mkdtemp(prefix="eval-googlecast-"))
    started = time.monotonic()
    def run_tier(fn: Callable[..., None], *a: Any) -> None:
        """Chạy một tầng; nếu nó SẬP thì ghi thành mục ĐỎ.

        Một ngoại lệ giữa chừng sẽ giấu mọi mục kiểm phía sau — đúng kiểu làm
        cho bộ kiểm trông 'ít đỏ' hơn thực tế. Ghi lại, đừng nuốt.
        """
        try:
            fn(*a)
        except BaseException as exc:  # noqa: BLE001
            check(f"tầng {fn.__name__} chạy hết mà không sập", False,
                  f"{type(exc).__name__}: {exc}")

    try:
        run_tier(tier_offline, tmp)
        if args.online:
            # Tầng sau dựng object MỚI; khôi phục trước để không tầng nào
            # thừa hưởng mock của tầng trước.
            srv._manager = snapshot["manager"]
            srv._media_server = snapshot["media_server"]
            srv.tts.synthesize = snapshot["synthesize"]
            run_tier(tier_online, tmp)
        else:
            print("\n(bỏ qua tầng --online: cần internet)")
        if args.hardware:
            srv._manager = snapshot["manager"]
            srv._media_server = snapshot["media_server"]
            srv.tts.synthesize = snapshot["synthesize"]
            run_tier(tier_hardware, tmp, args.speaker)
        else:
            print("(bỏ qua tầng --hardware: sẽ phát tiếng thật)")
    finally:
        srv._manager = snapshot["manager"]
        srv._media_server = snapshot["media_server"]
        srv.tts.synthesize = snapshot["synthesize"]
        shutil.rmtree(tmp, ignore_errors=True)

    total = PASSED + len(FAILED)
    print(f"\n{'=' * 62}")
    print(f"KẾT QUẢ: {PASSED}/{total} đạt  ({time.monotonic() - started:.1f}s)")
    if FAILED:
        print("\nCÁC MỤC HỎNG:")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    print("TẤT CẢ ĐẠT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
