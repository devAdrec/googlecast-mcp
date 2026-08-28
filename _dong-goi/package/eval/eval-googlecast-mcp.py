#!/usr/bin/env python3
"""Bài kiểm cho googlecast-mcp.

Ba tầng:
  (mặc định)   offline  — không mạng, không phần cứng, không tác dụng phụ
  --online              — gọi dịch vụ edge-tts thật (cần internet)
  --hardware            — cast ra loa THẬT, phát tiếng thật (phải xin phép)

Luật của bài kiểm này (xem eval/README.md để biết vì sao):
  * ĐẾM ĐỦ TRƯỚC KHI ĐẾM XANH: báo cáo in "đã chạy X/Y mục đăng ký".
    X < Y là KHÔNG ĐẠT toàn cục, kể cả khi mọi mục đã chạy đều xanh.
    Khớp 0 mục (vd --only sai tên) cũng KHÔNG ĐẠT.
  * Mỗi mục phải GỌI vào mã sản phẩm. Lỗi hạ tầng của chính bài kiểm được
    báo là ERROR chứ không nuốt thành PASS.
  * Không mục nào ghi vào cây sản phẩm; mọi thứ nằm trong thư mục tạm.

Dùng:
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --only tts_lock_per_loop,tts_serializes
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware   # phát tiếng thật
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import socket
import sys
import tempfile
import time
import traceback
import types
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------
# Sổ đăng ký
# --------------------------------------------------------------------------

REGISTRY: "list[tuple[str, str, object]]" = []  # (id, tier, fn)


def check(item_id: str, tier: str = "offline"):
    def wrap(fn):
        REGISTRY.append((item_id, tier, fn))
        return fn

    return wrap


# --------------------------------------------------------------------------
# Dụng cụ: tráo bối cảnh có khôi phục, KHÔNG bao giờ tự-gọi-đệ-quy
# --------------------------------------------------------------------------


class ModuleProxy(types.SimpleNamespace):
    """Bọc một module: các thuộc tính ghi đè nằm ở lớp ngoài, phần còn lại
    ủy quyền cho module GỐC đã giữ tham chiếu.

    Đây là cách tránh bẫy thay-thế-đệ-quy: KHÔNG được gán
    ``mod.asyncio.sleep = fake`` vì ``mod.asyncio`` chính là module asyncio
    toàn cục — bản thay thế sẽ gọi lại chính nó. Ở đây bản gốc được giữ riêng
    nên lời gọi ủy quyền luôn đi tới hàm thật.
    """

    def __init__(self, real, **overrides):
        super().__init__(**overrides)
        object.__setattr__(self, "_real", real)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_real"), name)


@contextlib.contextmanager
def swap(obj, name, value):
    """Đổi một thuộc tính rồi TRẢ LẠI nguyên trạng, kể cả khi có ngoại lệ."""
    missing = object()
    old = getattr(obj, name, missing)
    setattr(obj, name, value)
    try:
        yield
    finally:
        if old is missing:
            delattr(obj, name)
        else:
            setattr(obj, name, old)


@contextlib.contextmanager
def swap_env(name, value):
    missing = object()
    old = os.environ.get(name, missing)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if old is missing:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


@contextlib.contextmanager
def tmpdir():
    with tempfile.TemporaryDirectory(prefix="gcmcp-eval-") as d:
        yield Path(d)


def stop_quietly(server, seconds=5.0):
    """Tắt media server nhưng KHÔNG để nó treo cả bài kiểm.

    ThreadingHTTPServer.shutdown() chờ vòng serve_forever thoát; nếu sản phẩm
    (đã bị gieo lỗi) chưa từng khởi động vòng đó thì lời gọi này treo vĩnh
    viễn. Một bài kiểm treo không phải là bài kiểm xanh — nó phải kết thúc
    được rồi mới nói chuyện đỏ/xanh.
    """
    import threading

    t = threading.Thread(target=server.stop, daemon=True)
    t.start()
    t.join(seconds)


def want(condition, message):
    """Khẳng định. Dùng hàm thay vì `assert` để `python -O` không xoá mất."""
    if not condition:
        raise AssertionError(message)


# --------------------------------------------------------------------------
# Bản giả cho thiết bị Cast
# --------------------------------------------------------------------------


class FakeCastInfo:
    def __init__(self, name, uuid, cast_type="audio", host="192.168.1.22", port=8009):
        self.friendly_name = name
        self.uuid = uuid
        self.model_name = "Fake Speaker"
        self.manufacturer = "Fake"
        self.host = host
        self.port = port
        self.cast_type = cast_type


class FakeMediaController:
    def __init__(self):
        self.played = []
        self.status = types.SimpleNamespace(
            player_state="PLAYING",
            title="t",
            content_id=None,
            content_type="audio/mpeg",
            duration=2.0,
            current_time=0.0,
        )

    def play_media(self, url, content_type, title=None):
        self.played.append((url, content_type, title))
        self.status.content_id = url

    def block_until_active(self, timeout=10):
        pass

    def play(self):
        self.status.player_state = "PLAYING"

    def pause(self):
        self.status.player_state = "PAUSED"

    def stop(self):
        self.status.player_state = "IDLE"

    def seek(self, position):
        self.status.current_time = position


class FakeCast:
    def __init__(self, name, uuid, cast_type="audio", host="192.168.1.22"):
        self.cast_info = FakeCastInfo(name, uuid, cast_type, host)
        self.media_controller = FakeMediaController()
        self.status = types.SimpleNamespace(
            display_name="Default Media Receiver",
            app_id="CC1AD845",
            is_active_input=None,
            volume_level=0.5,
            volume_muted=False,
        )
        self.volume_calls = []
        self.mute_calls = []
        self.quit_calls = 0
        self.waited = 0

    def wait(self, timeout=10):
        self.waited += 1

    def set_volume(self, level):
        self.volume_calls.append(level)

    def set_volume_muted(self, muted):
        self.mute_calls.append(muted)

    def quit_app(self):
        self.quit_calls += 1

    def disconnect(self, blocking=False):
        pass


def fake_pychromecast(casts=(), from_host=None):
    """Bản giả TRỌN BỘ của mặt tiếp xúc pychromecast mà cast_manager dùng."""
    browser = types.SimpleNamespace(stop_discovery=lambda: None)

    def get_chromecasts(timeout=5.0):
        return list(casts), browser

    def get_chromecast_from_host(info, tries=1, timeout=5):
        if from_host is None:
            raise OSError("no route to host")
        return from_host(info)

    return types.SimpleNamespace(
        get_chromecasts=get_chromecasts,
        get_chromecast_from_host=get_chromecast_from_host,
    )


# ==========================================================================
# speaker_store
# ==========================================================================


@check("store_is_speaker_audio")
def _():
    from googlecast_mcp import speaker_store

    want(speaker_store.is_speaker({"cast_type": "audio"}), "loa audio phải là speaker")


@check("store_is_speaker_group")
def _():
    from googlecast_mcp import speaker_store

    want(speaker_store.is_speaker({"cast_type": "group"}), "nhóm loa phải là speaker")


@check("store_rejects_video_cast")
def _():
    from googlecast_mcp import speaker_store

    want(
        not speaker_store.is_speaker({"cast_type": "cast"}),
        "thiết bị hình ảnh KHÔNG được tính là loa",
    )
    want(not speaker_store.is_speaker({}), "thiếu cast_type thì không phải loa")


@check("store_path_env_override")
def _():
    from googlecast_mcp import speaker_store

    with tmpdir() as d:
        with swap_env("GOOGLECAST_MCP_STORE", str(d / "s.json")):
            want(
                speaker_store.default_store_path() == d / "s.json",
                "GOOGLECAST_MCP_STORE phải quyết định nơi lưu",
            )


@check("store_path_default_home")
def _():
    from googlecast_mcp import speaker_store

    with swap_env("GOOGLECAST_MCP_STORE", None):
        p = speaker_store.default_store_path()
    want(
        p == Path.home() / ".googlecast-mcp" / "speakers.json",
        f"đường dẫn mặc định sai: {p}",
    )


@check("store_load_missing_is_empty")
def _():
    from googlecast_mcp.speaker_store import SpeakerStore

    with tmpdir() as d:
        want(SpeakerStore(d / "none.json").load() == [], "file chưa có phải trả []")


@check("store_load_corrupt_is_empty")
def _():
    from googlecast_mcp.speaker_store import SpeakerStore

    with tmpdir() as d:
        p = d / "s.json"
        p.write_text("{ khong phai json", encoding="utf-8")
        want(SpeakerStore(p).load() == [], "JSON hỏng phải trả [] chứ không ném lỗi")


@check("store_save_merges_by_uuid")
def _():
    from googlecast_mcp.speaker_store import SpeakerStore

    with tmpdir() as d:
        s = SpeakerStore(d / "s.json")
        s.save([{"uuid": "u1", "friendly_name": "A", "cast_type": "audio"}])
        s.save([{"uuid": "u1", "host": "192.168.1.9"}])
        s.save([{"uuid": "u2", "friendly_name": "B", "cast_type": "cast"}])
        devices = {d_["uuid"]: d_ for d_ in s.load()}
        want(len(devices) == 2, f"phải còn đúng 2 thiết bị, có {len(devices)}")
        want(
            devices["u1"]["friendly_name"] == "A" and devices["u1"]["host"] == "192.168.1.9",
            "gộp theo uuid phải GIỮ trường cũ và thêm trường mới",
        )


@check("store_save_no_temp_left")
def _():
    from googlecast_mcp.speaker_store import SpeakerStore

    with tmpdir() as d:
        s = SpeakerStore(d / "s.json")
        s.save([{"uuid": "u1", "friendly_name": "A", "cast_type": "audio"}])
        leftovers = sorted(p.name for p in d.iterdir())
        want(leftovers == ["s.json"], f"ghi-rồi-đổi-tên không được để rác: {leftovers}")
        payload = json.loads((d / "s.json").read_text(encoding="utf-8"))
        want("updated_at" in payload and "devices" in payload, "thiếu khoá trong file lưu")


@check("store_speakers_filters_video")
def _():
    from googlecast_mcp.speaker_store import SpeakerStore

    with tmpdir() as d:
        s = SpeakerStore(d / "s.json")
        s.save(
            [
                {"uuid": "u1", "friendly_name": "Kitchen speaker", "cast_type": "audio"},
                {"uuid": "u2", "friendly_name": "Working display", "cast_type": "cast"},
                {"uuid": "u3", "friendly_name": "Family speaker group", "cast_type": "group"},
            ]
        )
        names = sorted(x["friendly_name"] for x in s.speakers())
        want(
            names == ["Family speaker group", "Kitchen speaker"],
            f"speakers() phải lọc thiết bị hình ảnh, được {names}",
        )


# ==========================================================================
# tts
# ==========================================================================


def _fake_edge_tts(behaviour):
    """Bản giả TRỌN BỘ mặt tiếp xúc edge_tts mà tts.py dùng (chỉ Communicate)."""
    state = {"calls": 0, "live": 0, "max_live": 0}

    class Communicate:
        def __init__(self, text, voice, rate="+0%", volume="+0%"):
            self.text, self.voice, self.rate = text, voice, rate

        async def save(self, path):
            state["calls"] += 1
            state["live"] += 1
            state["max_live"] = max(state["max_live"], state["live"])
            try:
                await behaviour(self, path)
            finally:
                state["live"] -= 1

    return types.SimpleNamespace(Communicate=Communicate), state


async def _write_ok(comm, path):
    await asyncio.sleep(0.03)
    Path(path).write_bytes(b"ID3fake-audio-bytes")


@check("tts_resolve_female")
def _():
    from googlecast_mcp import tts

    want(tts.resolve_voice("female") == "vi-VN-HoaiMyNeural", "giọng nữ sai")


@check("tts_resolve_male")
def _():
    from googlecast_mcp import tts

    want(tts.resolve_voice("male") == "vi-VN-NamMinhNeural", "giọng nam sai")


@check("tts_resolve_passthrough_and_default")
def _():
    from googlecast_mcp import tts

    want(tts.resolve_voice("en-US-AriaNeural") == "en-US-AriaNeural", "id đầy đủ phải đi thẳng")
    want(tts.resolve_voice(None) == tts.DEFAULT_VOICE, "None phải ra giọng mặc định")
    want(tts.resolve_voice("") == tts.DEFAULT_VOICE, "rỗng phải ra giọng mặc định")
    want(tts.DEFAULT_VOICE.startswith("vi-VN"), "mặc định phải là giọng tiếng Việt")


@check("tts_empty_text_raises")
def _():
    from googlecast_mcp import tts

    with tmpdir() as d:
        try:
            asyncio.run(tts.synthesize("   ", cache_dir=d))
        except ValueError:
            return
        raise AssertionError("text rỗng phải ném ValueError")


@check("tts_cache_hit_skips_render")
def _():
    from googlecast_mcp import tts

    fake, state = _fake_edge_tts(_write_ok)
    with tmpdir() as d, swap(tts, "edge_tts", fake):
        p1 = asyncio.run(tts.synthesize("Cơm đã chín rồi", cache_dir=d))
        want(state["calls"] == 1, "lần đầu phải render")
        p2 = asyncio.run(tts.synthesize("Cơm đã chín rồi", cache_dir=d))
        want(p1 == p2, "cùng nội dung phải ra cùng file")
        want(state["calls"] == 1, f"lần hai phải dùng cache, đã render {state['calls']} lần")


@check("tts_cache_key_varies_with_rate")
def _():
    from googlecast_mcp import tts

    fake, state = _fake_edge_tts(_write_ok)
    with tmpdir() as d, swap(tts, "edge_tts", fake):
        a = asyncio.run(tts.synthesize("xin chào", rate="+0%", cache_dir=d))
        b = asyncio.run(tts.synthesize("xin chào", rate="+10%", cache_dir=d))
        want(a != b, "đổi rate phải ra file khác")
        c = asyncio.run(tts.synthesize("xin chào", voice="male", cache_dir=d))
        want(c != a, "đổi giọng phải ra file khác")


@check("tts_zero_byte_not_reused")
def _():
    from googlecast_mcp import tts

    fake, state = _fake_edge_tts(_write_ok)
    with tmpdir() as d, swap(tts, "edge_tts", fake):
        p = asyncio.run(tts.synthesize("một hai ba", cache_dir=d))
        p.write_bytes(b"")  # giả lập lần chạy trước hỏng giữa chừng
        again = asyncio.run(tts.synthesize("một hai ba", cache_dir=d))
        want(again == p, "phải render lại đúng đường dẫn cũ")
        want(again.stat().st_size > 0, "file 0 byte KHÔNG được dùng lại")
        want(state["calls"] == 2, f"phải render lại, số lần render = {state['calls']}")


@check("tts_retries_three_times")
def _():
    from googlecast_mcp import tts

    async def always_fail(comm, path):
        raise OSError("Cannot connect to host")

    fake, state = _fake_edge_tts(always_fail)
    # Bọc asyncio bằng proxy: KHÔNG gán đè lên asyncio.sleep toàn cục.
    fast = ModuleProxy(asyncio, sleep=lambda *_a, **_k: asyncio.sleep(0))
    with tmpdir() as d, swap(tts, "edge_tts", fake), swap(tts, "asyncio", fast):
        try:
            asyncio.run(tts.synthesize("thử lại", cache_dir=d))
        except RuntimeError as exc:
            want("3 attempts" in str(exc), f"thông điệp lỗi phải nói rõ số lần thử: {exc}")
        else:
            raise AssertionError("render hỏng liên tục phải ném RuntimeError")
        want(state["calls"] == 3, f"phải thử đúng 3 lần, đã thử {state['calls']}")


@check("tts_leaves_no_zero_byte_file")
def _():
    from googlecast_mcp import tts

    async def create_then_fail(comm, path):
        Path(path).write_bytes(b"")  # save() tạo file rồi mới hỏng
        raise OSError("Cannot connect to host")

    fake, _state = _fake_edge_tts(create_then_fail)
    fast = ModuleProxy(asyncio, sleep=lambda *_a, **_k: asyncio.sleep(0))
    with tmpdir() as d, swap(tts, "edge_tts", fake), swap(tts, "asyncio", fast):
        with contextlib.suppress(RuntimeError):
            asyncio.run(tts.synthesize("hỏng", cache_dir=d))
        # Đếm KHI thư mục tạm còn sống — đóng trước rồi mới đếm là đếm chỗ trống.
        leftovers = [p.name for p in d.iterdir()]
        want(leftovers == [], f"không được để lại file 0 byte: {leftovers}")


@check("tts_serializes_concurrent_renders")
def _():
    from googlecast_mcp import tts

    fake, state = _fake_edge_tts(_write_ok)

    async def scenario(cache):
        await asyncio.gather(
            *(tts.synthesize(f"câu số {i}", cache_dir=cache) for i in range(6))
        )

    with tmpdir() as d, swap(tts, "edge_tts", fake):
        started = time.monotonic()
        asyncio.run(scenario(d))
        elapsed = time.monotonic() - started
        files = sorted(p for p in d.iterdir() if p.stat().st_size > 0)
    want(state["calls"] == 6, f"phải render đủ 6 câu, được {state['calls']}")
    want(len(files) == 6, f"phải ra 6 file có nội dung, được {len(files)}")
    want(
        state["max_live"] == 1,
        f"các lần render KHÔNG được chồng lên nhau; cao nhất cùng lúc = {state['max_live']}",
    )
    want(elapsed < 5, f"tuần tự hoá không được biến thành treo: {elapsed:.1f}s")


@check("tts_lock_per_loop")
def _():
    """Khoá phải theo TỪNG vòng lặp: một tiến trình gọi asyncio.run() hai lần,
    lần nào cũng có tranh chấp, cả hai đều phải chạy được."""
    from googlecast_mcp import tts

    fake, state = _fake_edge_tts(_write_ok)

    async def contended(cache, salt):
        # Hai lời gọi cùng lúc => chắc chắn có tranh chấp khoá.
        await asyncio.gather(
            tts.synthesize(f"vòng {salt} a", cache_dir=cache),
            tts.synthesize(f"vòng {salt} b", cache_dir=cache),
        )

    with tmpdir() as d, swap(tts, "edge_tts", fake):
        asyncio.run(contended(d, 1))
        asyncio.run(contended(d, 2))  # vòng lặp MỚI, khoá mức module sẽ chết ở đây
        made = len([p for p in d.iterdir() if p.stat().st_size > 0])
    want(made == 4, f"cả hai vòng lặp đều phải render được, chỉ có {made}/4 file")
    want(state["calls"] == 4, f"số lần render = {state['calls']}, phải là 4")


@check("tts_cache_dir_env_override")
def _():
    from googlecast_mcp import tts

    with tmpdir() as d:
        with swap_env("GOOGLECAST_MCP_CACHE", str(d / "cache")):
            got = tts.default_cache_dir()
        want(got == d / "cache", f"GOOGLECAST_MCP_CACHE phải quyết định thư mục cache: {got}")
        want(got.is_dir(), "thư mục cache phải được tạo sẵn")


# ==========================================================================
# media_server
# ==========================================================================


@check("media_binds_all_interfaces")
def _():
    from googlecast_mcp.media_server import MediaServer

    with tmpdir() as d:
        srv = MediaServer(d, host="10.9.9.9", port=0)
        try:
            srv.start()
            bind = srv._httpd.server_address[0]
            want(
                bind == "0.0.0.0",
                f"phải bind mọi giao diện để loa ở mạng khác tới được, đang bind {bind}",
            )
        finally:
            stop_quietly(srv)


@check("media_url_uses_advertised_host")
def _():
    from googlecast_mcp.media_server import MediaServer

    with tmpdir() as d:
        (d / "a.mp3").write_bytes(b"x")
        srv = MediaServer(d, host="10.9.9.9", port=0)
        try:
            url = srv.url_for(d / "a.mp3")
            want(
                url.startswith("http://10.9.9.9:"),
                f"URL quảng bá phải dùng địa chỉ LAN chứ không phải địa chỉ bind: {url}",
            )
            want(url.endswith("/a.mp3"), f"URL sai đuôi: {url}")
            want(srv.port != 0, "sau khi start phải biết cổng thật")
        finally:
            stop_quietly(srv)


@check("media_url_quotes_special_chars")
def _():
    from googlecast_mcp.media_server import MediaServer

    with tmpdir() as d:
        name = "cơm chín.mp3"
        (d / name).write_bytes(b"x")
        srv = MediaServer(d, host="127.0.0.1", port=0)
        try:
            url = srv.url_for(d / name)
            want(" " not in url, f"URL không được chứa khoảng trắng thô: {url}")
            want("%20" in url, f"khoảng trắng phải được mã hoá: {url}")
        finally:
            stop_quietly(srv)


@check("media_actually_serves_the_file")
def _():
    from googlecast_mcp.media_server import MediaServer

    payload = b"ID3" + b"\x00" * 64 + b"end"
    with tmpdir() as d:
        (d / "clip.mp3").write_bytes(payload)
        srv = MediaServer(d, host="127.0.0.1", port=0)
        try:
            url = srv.url_for(d / "clip.mp3")
            # Đọc XONG nội dung khi server và thư mục tạm còn sống.
            with urllib.request.urlopen(url, timeout=10) as resp:
                code, body = resp.status, resp.read()
            want(code == 200, f"phải phục vụ được file, mã {code}")
            want(body == payload, "nội dung tải về phải khớp file gốc")
        finally:
            stop_quietly(srv)


@check("media_set_port_after_start_is_refused")
def _():
    from googlecast_mcp.media_server import MediaServer

    with tmpdir() as d:
        srv = MediaServer(d, host="127.0.0.1", port=0)
        try:
            srv.start()
            try:
                srv.set_port(8797)
            except RuntimeError:
                pass
            else:
                raise AssertionError("đổi cổng khi đang chạy phải bị từ chối")
        finally:
            stop_quietly(srv)


@check("media_start_is_idempotent")
def _():
    from googlecast_mcp.media_server import MediaServer

    with tmpdir() as d:
        srv = MediaServer(d, host="127.0.0.1", port=0)
        try:
            srv.start()
            first = srv.port
            srv.start()
            want(srv.port == first, "gọi start() hai lần không được dựng server thứ hai")
        finally:
            stop_quietly(srv)
        srv.stop()  # gọi lại khi đã tắt phải an toàn


@check("media_lan_ip_falls_back_to_loopback")
def _():
    from googlecast_mcp import media_server

    class DeadSocket:
        def __init__(self, *a, **k):
            pass

        def connect(self, addr):
            raise OSError("network unreachable")

        def getsockname(self):
            raise AssertionError("không được hỏi tên socket sau khi connect hỏng")

        def close(self):
            pass

    fake_socket = ModuleProxy(socket, socket=DeadSocket)
    with swap(media_server, "socket", fake_socket):
        want(
            media_server.lan_ip() == "127.0.0.1",
            "mất mạng thì lan_ip() phải lui về 127.0.0.1 chứ không ném lỗi",
        )


# ==========================================================================
# cast_manager
# ==========================================================================


@check("guess_content_type_audio")
def _():
    from googlecast_mcp.cast_manager import _guess_content_type

    want(_guess_content_type("http://h/a.mp3") == "audio/mpeg", "mp3 phải ra audio/mpeg")
    want(_guess_content_type("http://h/A.MP3") == "audio/mpeg", "phải bỏ qua hoa/thường")


@check("guess_content_type_ignores_query")
def _():
    from googlecast_mcp.cast_manager import _guess_content_type

    got = _guess_content_type("http://h/a.mp3?token=1")
    want(got == "audio/mpeg", f"phải bỏ chuỗi truy vấn trước khi đoán, được {got}")


@check("guess_content_type_default")
def _():
    from googlecast_mcp.cast_manager import _guess_content_type

    want(_guess_content_type("http://h/stream") == "video/mp4", "không rõ đuôi thì mặc định mp4")


@check("manager_resolves_name_case_insensitively")
def _():
    from googlecast_mcp.cast_manager import CastManager
    from googlecast_mcp.speaker_store import SpeakerStore

    with tmpdir() as d:
        m = CastManager(SpeakerStore(d / "s.json"))
        cast = FakeCast("Kitchen speaker", "u1")
        m._devices["u1"] = cast
        want(m._resolve("kitchen SPEAKER") is cast, "tên phải khớp không phân biệt hoa thường")
        want(m._resolve("u1") is cast, "uuid phải khớp")
        want(m._resolve("  Kitchen speaker  ") is cast, "phải cắt khoảng trắng thừa")


@check("manager_connects_saved_when_mdns_misses")
def _():
    """mDNS sót thiết bị ĐÃ LƯU thì phải nối thẳng địa chỉ đã lưu, không được
    báo 'không tìm thấy' một cách tự mâu thuẫn."""
    from googlecast_mcp import cast_manager
    from googlecast_mcp.cast_manager import CastManager
    from googlecast_mcp.speaker_store import SpeakerStore

    saved = FakeCast("Kitchen speaker", "11111111-1111-1111-1111-111111111111")
    hits = []

    def from_host(info):
        hits.append(info)
        return saved

    # Quét mDNS trả về RỖNG (đúng cảnh sót thiết bị), nhưng địa chỉ lưu vẫn nối được.
    fake = fake_pychromecast(casts=(), from_host=from_host)
    with tmpdir() as d:
        store = SpeakerStore(d / "s.json")
        store.save(
            [
                {
                    "uuid": "11111111-1111-1111-1111-111111111111",
                    "friendly_name": "Kitchen speaker",
                    "cast_type": "audio",
                    "host": "192.168.1.22",
                    "port": 8009,
                    "model_name": "Google Home",
                }
            ]
        )
        m = CastManager(store)
        with swap(cast_manager, "pychromecast", fake):
            got = m._resolve("Kitchen speaker")
        want(got is saved, "phải nối được qua địa chỉ đã lưu")
        want(len(hits) == 1, f"phải thử đúng một lần nối thẳng, có {len(hits)}")


@check("manager_unknown_device_raises")
def _():
    from googlecast_mcp import cast_manager
    from googlecast_mcp.cast_manager import CastManager, DeviceNotFoundError
    from googlecast_mcp.speaker_store import SpeakerStore

    fake = fake_pychromecast(casts=(), from_host=None)
    with tmpdir() as d:
        m = CastManager(SpeakerStore(d / "s.json"))
        with swap(cast_manager, "pychromecast", fake):
            try:
                m._resolve("Không có loa này")
            except DeviceNotFoundError as exc:
                want("Known devices" in str(exc), f"lỗi phải liệt kê thiết bị đã biết: {exc}")
                return
        raise AssertionError("thiết bị lạ phải ném DeviceNotFoundError")


@check("manager_volume_is_clamped")
def _():
    from googlecast_mcp.cast_manager import CastManager
    from googlecast_mcp.speaker_store import SpeakerStore

    with tmpdir() as d:
        m = CastManager(SpeakerStore(d / "s.json"))
        cast = FakeCast("Kitchen speaker", "u1")
        m._devices["u1"] = cast
        want(m.set_volume("u1", 5.0) == 1.0, "trên 1.0 phải kẹp về 1.0")
        want(m.set_volume("u1", -3.0) == 0.0, "dưới 0.0 phải kẹp về 0.0")
        want(m.set_volume("u1", 0.4) == 0.4, "giá trị hợp lệ phải giữ nguyên")
        want(cast.volume_calls == [1.0, 0.0, 0.4], f"đã gửi xuống thiết bị: {cast.volume_calls}")


@check("manager_discover_persists_devices")
def _():
    from googlecast_mcp import cast_manager
    from googlecast_mcp.cast_manager import CastManager
    from googlecast_mcp.speaker_store import SpeakerStore

    casts = [
        FakeCast("Kitchen speaker", "u1", "audio"),
        FakeCast("Working display", "u2", "cast"),
    ]
    fake = fake_pychromecast(casts=casts, from_host=None)
    with tmpdir() as d:
        store = SpeakerStore(d / "s.json")
        m = CastManager(store)
        with swap(cast_manager, "pychromecast", fake):
            found = m.discover(0.1)
        want(len(found) == 2, f"phải tìm ra 2 thiết bị, được {len(found)}")
        want(len(store.load()) == 2, "kết quả quét phải được LƯU xuống đĩa")
        want(
            [s["friendly_name"] for s in m.list_speakers()] == ["Kitchen speaker"],
            "list_speakers phải bỏ thiết bị hình ảnh",
        )


@check("manager_status_reports_media_fields")
def _():
    from googlecast_mcp.cast_manager import CastManager
    from googlecast_mcp.speaker_store import SpeakerStore

    with tmpdir() as d:
        m = CastManager(SpeakerStore(d / "s.json"))
        cast = FakeCast("Kitchen speaker", "u1")
        m._devices["u1"] = cast
        out = m.play_media("u1", "http://h/x.mp3", None, "chào")
        want(out["media"]["content_id"] == "http://h/x.mp3", "content_id phải khớp URL đã cast")
        want(out["media"]["player_state"] == "PLAYING", "trạng thái phát sai")
        want(out["device"]["friendly_name"] == "Kitchen speaker", "thiếu thông tin thiết bị")
        want(
            cast.media_controller.played[0][1] == "audio/mpeg",
            "thiếu content_type thì phải tự đoán từ đuôi URL",
        )
        want(cast.waited >= 1, "phải chờ kết nối sẵn sàng trước khi điều khiển")


# ==========================================================================
# server (chọn loa, say)
# ==========================================================================


class FakeManager:
    """Bản giả của CastManager ở mức server dùng tới."""

    def __init__(self, speakers, fail_for=()):
        self._speakers = list(speakers)
        self._fail_for = set(fail_for)
        self.cast_calls = []
        self.discover_calls = 0

    def list_speakers(self):
        return list(self._speakers)

    def list_cached(self):
        return list(self._speakers)

    def discover(self, timeout=5.0):
        self.discover_calls += 1
        return list(self._speakers)

    def play_media(self, name, url, content_type=None, title=None):
        self.cast_calls.append((name, url, content_type, title))
        if name in self._fail_for:
            raise RuntimeError(f"Device {name!r} did not respond.")
        return {"device": {"friendly_name": name}, "media": {"content_id": url}}


class FakeMediaServer:
    def __init__(self, base="http://192.168.1.128:8766"):
        self.base = base

    def url_for(self, path):
        return f"{self.base}/{Path(path).name}"


SPEAKERS = [
    {"friendly_name": "Kitchen speaker", "uuid": "u1", "cast_type": "audio", "host": "192.168.1.22"},
    {"friendly_name": "Bedroom speaker", "uuid": "u2", "cast_type": "audio", "host": "192.168.1.23"},
    {"friendly_name": "Living speaker", "uuid": "u3", "cast_type": "audio", "host": "192.168.1.24"},
    {
        "friendly_name": "Family speaker group",
        "uuid": "u4",
        "cast_type": "group",
        "host": "192.168.1.22",
    },
]


@contextlib.contextmanager
def server_context(speakers=SPEAKERS, fail_for=()):
    """Tráo TRỌN BỘ bối cảnh của server: cả trình quản lý loa LẪN media server.

    Tráo nửa vời (chỉ _manager) từng làm url_for trỏ ra ngoài thư mục nó phục
    vụ và lỗi hiện ra ở chỗ chẳng liên quan.
    """
    from googlecast_mcp import server as srv

    manager = FakeManager(speakers, fail_for)
    media = FakeMediaServer()
    with swap(srv, "_manager", manager), swap(srv, "_media_server", media):
        yield srv, manager, media


def _fake_tts_module(srv):
    """Bản giả tts dùng trong tầng offline: không gọi mạng, có ghi lại lời gọi."""
    from googlecast_mcp import tts as real_tts

    calls = []

    async def synthesize(text, voice=None, rate="+0%", **kw):
        calls.append((text, voice, rate))
        return Path(tempfile.gettempdir()) / "gcmcp-eval-fake.mp3"

    proxy = ModuleProxy(real_tts, synthesize=synthesize)
    return proxy, calls


@check("select_without_choice_asks_back")
def _():
    with server_context() as (srv, manager, _media):
        out = asyncio.run(srv._select_targets(None))
        names, prompt = out
        want(names == [], "chưa chọn loa thì KHÔNG được có loa nào được chọn")
        want(prompt is not None, "phải trả về dữ liệu để LLM hỏi lại")
        want(
            prompt["status"] == "needs_speaker_selection",
            f"trạng thái sai: {prompt['status']}",
        )
        want(len(prompt["speakers"]) == 4, "phải kèm đủ danh sách loa cho người dùng chọn")
        want("Kitchen speaker" in prompt["message"], "thông điệp phải kể tên loa")


@check("select_no_speakers_status")
def _():
    with server_context(speakers=[]) as (srv, manager, _media):
        names, prompt = asyncio.run(srv._select_targets(None))
        want(names == [], "không có loa thì không chọn được gì")
        want(prompt["status"] == "no_speakers_found", f"trạng thái sai: {prompt['status']}")
        want(manager.discover_calls >= 1, "danh sách rỗng thì phải thử quét một lần")


@check("select_all_excludes_groups")
def _():
    """'all' phải BỎ nhóm loa: nhóm phát qua chính các thành viên, gửi cả hai
    thì một loa vật lý nhận hai luồng mà API vẫn báo 'playing'."""
    with server_context() as (srv, _manager, _media):
        for keyword in ("all", "tất cả", "ALL", "*"):
            names, prompt = asyncio.run(srv._select_targets(keyword))
            want(prompt is None, f"{keyword!r} là lựa chọn hợp lệ, không được hỏi lại")
            want(
                "Family speaker group" not in names,
                f"{keyword!r} không được gồm nhóm loa: {names}",
            )
            want(len(names) == 3, f"{keyword!r} phải ra 3 loa riêng lẻ, được {names}")


@check("select_comma_separated_list")
def _():
    with server_context() as (srv, _manager, _media):
        names, prompt = asyncio.run(
            srv._select_targets(" Kitchen speaker , Bedroom speaker ")
        )
        want(prompt is None, "danh sách tên là lựa chọn hợp lệ")
        want(
            names == ["Kitchen speaker", "Bedroom speaker"],
            f"phải tách theo dấu phẩy và cắt khoảng trắng, được {names}",
        )


@check("select_group_by_name_still_allowed")
def _():
    with server_context() as (srv, _manager, _media):
        names, prompt = asyncio.run(srv._select_targets("Family speaker group"))
        want(prompt is None and names == ["Family speaker group"], f"gọi nhóm theo tên: {names}")


@check("say_without_choice_plays_nothing")
def _():
    """Điểm an toàn quan trọng nhất: thiếu lựa chọn thì KHÔNG phát ra tiếng nào."""
    with server_context() as (srv, manager, _media):
        fake_tts, calls = _fake_tts_module(srv)
        with swap(srv, "tts", fake_tts):
            out = asyncio.run(srv.say("Cơm đã chín rồi"))
        want(out["status"] == "needs_speaker_selection", f"trạng thái sai: {out['status']}")
        want(manager.cast_calls == [], f"KHÔNG được cast gì cả, đã cast: {manager.cast_calls}")
        want(calls == [], "cũng không nên tổng hợp giọng khi chưa biết phát ở đâu")


@check("say_casts_to_chosen_speaker")
def _():
    with server_context() as (srv, manager, _media):
        fake_tts, calls = _fake_tts_module(srv)
        with swap(srv, "tts", fake_tts):
            out = asyncio.run(srv.say("Cơm đã chín rồi", "Kitchen speaker"))
        want(out["status"] == "ok", f"phải thành công: {out}")
        want(len(manager.cast_calls) == 1, f"phải cast đúng một lần: {manager.cast_calls}")
        name, url, ctype, title = manager.cast_calls[0]
        want(name == "Kitchen speaker", f"sai loa: {name}")
        want(ctype == "audio/mpeg", f"phải khai báo audio/mpeg, được {ctype}")
        want(url.startswith("http://"), f"loa cần URL HTTP tải được, được {url}")
        want(out["voice"] == "vi-VN-HoaiMyNeural", f"giọng mặc định sai: {out['voice']}")
        want(calls and calls[0][0] == "Cơm đã chín rồi", "văn bản phải đi tới bộ tổng hợp")


@check("say_isolates_one_broken_speaker")
def _():
    """Một phần tử hỏng không được kéo đổ cả lượt phát."""
    with server_context(fail_for=["Ghost speaker"]) as (srv, manager, _media):
        fake_tts, _calls = _fake_tts_module(srv)
        with swap(srv, "tts", fake_tts):
            out = asyncio.run(srv.say("thử", "Kitchen speaker,Ghost speaker"))
        by_name = {r["speaker"]: r for r in out["results"]}
        want(out["status"] == "ok", f"còn loa phát được thì tổng thể vẫn ok: {out['status']}")
        want(by_name["Kitchen speaker"]["status"] == "playing", "loa tốt phải phát được")
        want(by_name["Ghost speaker"]["status"] == "error", "loa hỏng phải báo lỗi riêng")
        want("error" in by_name["Ghost speaker"], "phải kèm nội dung lỗi")


@check("say_all_broken_is_failed")
def _():
    with server_context(fail_for=[s["friendly_name"] for s in SPEAKERS]) as (srv, _m, _media):
        fake_tts, _calls = _fake_tts_module(srv)
        with swap(srv, "tts", fake_tts):
            out = asyncio.run(srv.say("thử", "all"))
        want(out["status"] == "failed", f"không loa nào phát được thì phải là failed: {out['status']}")


@check("server_exposes_thirteen_tools")
def _():
    from googlecast_mcp import server as srv

    tools = asyncio.run(srv.mcp.list_tools())
    names = sorted(t.name for t in tools)
    expected = sorted(
        [
            "say",
            "discover_devices",
            "list_speakers",
            "list_devices",
            "get_status",
            "play_media",
            "play",
            "pause",
            "stop",
            "seek",
            "set_volume",
            "set_muted",
            "quit_app",
        ]
    )
    want(names == expected, f"tập công cụ phải khớp đúng danh sách.\ncó : {names}\ncần: {expected}")


@check("tool_descriptions_are_present")
def _():
    from googlecast_mcp import server as srv

    tools = asyncio.run(srv.mcp.list_tools())
    thin = [t.name for t in tools if not (t.description or "").strip()]
    want(thin == [], f"LLM chọn công cụ bằng mô tả; các công cụ thiếu mô tả: {thin}")


# ==========================================================================
# __main__ — an ninh vận chuyển và CORS
# ==========================================================================


@contextlib.contextmanager
def main_with_lan(ip="192.168.1.128"):
    from googlecast_mcp import __main__ as entry

    with swap(entry, "lan_ip", lambda: ip):
        yield entry


@check("security_allows_lan_address")
def _():
    """Client ở máy khác bị trả 421 nếu địa chỉ LAN không nằm trong allowlist."""
    with main_with_lan() as entry:
        s = entry._transport_security("0.0.0.0", [], [])
    want("192.168.1.128" in s.allowed_hosts, f"thiếu địa chỉ LAN: {s.allowed_hosts}")
    want("127.0.0.1" in s.allowed_hosts, "vẫn phải cho loopback")


@check("security_allows_bare_host_without_port")
def _():
    """Proxy ở cổng mặc định gửi Host KHÔNG kèm ':port'."""
    with main_with_lan() as entry:
        s = entry._transport_security("0.0.0.0", ["google-cast.adrec.cloud"], [])
    want(
        "google-cast.adrec.cloud" in s.allowed_hosts,
        f"thiếu dạng host trần: {s.allowed_hosts}",
    )
    want(
        "google-cast.adrec.cloud:*" in s.allowed_hosts,
        f"thiếu dạng host kèm cổng: {s.allowed_hosts}",
    )


@check("security_allows_https_origin_behind_proxy")
def _():
    with main_with_lan() as entry:
        s = entry._transport_security("0.0.0.0", ["google-cast.adrec.cloud"], [])
    want(
        "https://google-cast.adrec.cloud" in s.allowed_origins,
        f"proxy kết thúc TLS nên phải chấp nhận origin https: {s.allowed_origins}",
    )
    want("http://192.168.1.128:*" in s.allowed_origins, "thiếu origin LAN kèm cổng")


@check("security_wildcard_bind_is_not_an_address")
def _():
    """0.0.0.0 là cách bind, không phải địa chỉ client gõ vào."""
    with main_with_lan() as entry:
        s = entry._transport_security("0.0.0.0", [], [])
    want("0.0.0.0" not in s.allowed_hosts, f"không được đưa 0.0.0.0 vào allowlist: {s.allowed_hosts}")
    with main_with_lan() as entry:
        s2 = entry._transport_security("192.168.1.99", [], [])
    want("192.168.1.99" in s2.allowed_hosts, "bind một địa chỉ cụ thể thì phải cho nó qua")


@check("security_browser_origin_passes_through")
def _():
    """Origin của trang web (vd llama-server webui) phải qua được cả tầng SDK."""
    with main_with_lan() as entry:
        s = entry._transport_security("0.0.0.0", [], ["http://192.168.1.99:8383"])
    want(
        "http://192.168.1.99:8383" in s.allowed_origins,
        f"thiếu origin trình duyệt: {s.allowed_origins}",
    )


@check("cors_exposes_session_header")
def _():
    """Không expose Mcp-Session-Id thì trình duyệt không đọc được session id và
    chỉ báo 'Failed to fetch'."""
    from googlecast_mcp import __main__ as entry

    ran = {}

    def fake_run(app, host=None, port=None, log_level=None):
        ran["app"] = app

    fake_uvicorn = types.SimpleNamespace(run=fake_run)
    # uvicorn được import BÊN TRONG hàm, nên phải tráo ở sys.modules; khôi phục
    # nguyên trạng ngay sau đó.
    old = sys.modules.get("uvicorn")
    sys.modules["uvicorn"] = fake_uvicorn
    try:
        entry._run_with_cors(["http://192.168.1.99:8383"])
    finally:
        if old is None:
            sys.modules.pop("uvicorn", None)
        else:
            sys.modules["uvicorn"] = old

    want("app" in ran, "phải dựng và chạy ứng dụng HTTP")
    cors = [m for m in ran["app"].user_middleware if "CORS" in repr(m)]
    want(cors, f"phải gắn CORSMiddleware: {ran['app'].user_middleware}")
    kwargs = getattr(cors[0], "kwargs", {})
    exposed = [h.lower() for h in kwargs.get("expose_headers", [])]
    want("mcp-session-id" in exposed, f"phải expose Mcp-Session-Id, đang expose {exposed}")
    want(
        "OPTIONS" in kwargs.get("allow_methods", []),
        f"preflight OPTIONS phải được cho phép: {kwargs.get('allow_methods')}",
    )
    want(
        "http://192.168.1.99:8383" in kwargs.get("allow_origins", []),
        f"origin phải đi vào middleware: {kwargs.get('allow_origins')}",
    )


@check("cli_defaults_are_safe")
def _():
    """Mặc định phải là stdio; mở cổng ra LAN phải là lựa chọn có ý thức."""
    from googlecast_mcp import __main__ as entry

    seen = {}

    def fake_run(transport=None):
        seen["transport"] = transport

    def fake_ctx(bind_host, extra, origins):
        seen["security"] = (bind_host, list(extra), list(origins))
        return "settings-object"

    fake_mcp = types.SimpleNamespace(
        settings=types.SimpleNamespace(
            host=None, port=None, transport_security=None,
            json_response=None, stateless_http=None,
        ),
        run=fake_run,
    )
    stopped = []
    fake_media = types.SimpleNamespace(
        stop=lambda: stopped.append("media"), set_port=lambda p: seen.__setitem__("media_port", p)
    )
    fake_manager = types.SimpleNamespace(close=lambda: stopped.append("manager"))

    # Tráo TRỌN BỘ những gì main() chạm tới, rồi khôi phục.
    with swap(entry, "mcp", fake_mcp), swap(entry, "_media_server", fake_media), \
            swap(entry, "_manager", fake_manager), swap(sys, "argv", ["googlecast-mcp"]):
        entry.main()

    want(seen.get("transport") == "stdio", f"transport mặc định phải là stdio: {seen}")
    want(
        fake_mcp.settings.host is None,
        f"chạy stdio thì không được đụng tới cài đặt HTTP: host={fake_mcp.settings.host}",
    )
    want(sorted(stopped) == ["manager", "media"], f"thoát phải dọn tài nguyên: {stopped}")


@check("cli_http_binds_loopback_by_default")
def _():
    from googlecast_mcp import __main__ as entry

    seen = {}
    fake_mcp = types.SimpleNamespace(
        settings=types.SimpleNamespace(
            host=None, port=None, transport_security=None,
            json_response=None, stateless_http=None,
        ),
        run=lambda transport=None: seen.__setitem__("transport", transport),
    )
    fake_media = types.SimpleNamespace(stop=lambda: None, set_port=lambda p: seen.__setitem__("media_port", p))
    fake_manager = types.SimpleNamespace(close=lambda: None)

    argv = ["googlecast-mcp", "--transport", "http", "--media-port", "8766"]
    with main_with_lan(), swap(entry, "mcp", fake_mcp), swap(entry, "_media_server", fake_media), \
            swap(entry, "_manager", fake_manager), swap(sys, "argv", argv):
        entry.main()

    want(seen.get("transport") == "streamable-http", f"tên transport gửi cho SDK: {seen}")
    want(
        fake_mcp.settings.host == "127.0.0.1",
        f"không nêu --host thì phải là loopback, được {fake_mcp.settings.host}",
    )
    want(fake_mcp.settings.port == 8000, f"cổng mặc định: {fake_mcp.settings.port}")
    want(seen.get("media_port") == 8766, f"--media-port phải được ghim: {seen}")
    want(
        fake_mcp.settings.json_response is False and fake_mcp.settings.stateless_http is False,
        "mặc định phải giữ SSE + có session id",
    )
    hosts = fake_mcp.settings.transport_security.allowed_hosts
    want("192.168.1.128" in hosts, f"địa chỉ LAN phải tự động được cho qua: {hosts}")


# ==========================================================================
# Tầng --online: gọi dịch vụ edge-tts thật
# ==========================================================================


@check("online_renders_real_vietnamese_audio", tier="online")
def _():
    from googlecast_mcp import tts

    with tmpdir() as d:
        path = asyncio.run(tts.synthesize("Cơm đã chín rồi", cache_dir=d))
        size = path.stat().st_size
        head = path.read_bytes()[:2]
        want(size > 2000, f"file audio thật phải có kích thước đáng kể, được {size} byte")
        # Hoặc thẻ ID3, hoặc frame sync của MPEG: 11 bit 1 đầu tiên, tức là
        # byte đầu 0xFF và ba bit cao của byte sau đều là 1 (ISO/IEC 11172-3
        # §2.4.1.2 syncword). Không nới thành "có byte nào cũng được".
        is_id3 = head == b"ID3"[:2]
        is_frame = head[0] == 0xFF and (head[1] & 0xE0) == 0xE0
        want(is_id3 or is_frame, f"không giống mp3: {head!r}")


@check("online_serializes_a_burst", tier="online")
def _():
    """Sáu yêu cầu dồn cùng lúc: trước khi tuần tự hoá chỉ đạt 4/6."""
    from googlecast_mcp import tts

    async def burst(cache):
        texts = [f"Câu thử số {i} của bài kiểm" for i in range(6)]
        return await asyncio.gather(
            *(tts.synthesize(t, cache_dir=cache) for t in texts), return_exceptions=True
        )

    with tmpdir() as d:
        started = time.monotonic()
        results = asyncio.run(burst(d))
        elapsed = time.monotonic() - started
        errors = [r for r in results if isinstance(r, BaseException)]
        good = [r for r in results if not isinstance(r, BaseException) and r.stat().st_size > 0]
        empty = [p.name for p in d.iterdir() if p.stat().st_size == 0]
        print(f"    [online] 6 yêu cầu dồn: {len(good)}/6 đạt trong {elapsed:.1f}s")
    want(not errors, f"không được có lỗi: {errors}")
    want(len(good) == 6, f"phải đủ 6/6, được {len(good)}")
    want(empty == [], f"không được đọng file 0 byte: {empty}")


@check("online_two_event_loops", tier="online")
def _():
    """Hai asyncio.run() có tranh chấp trên dịch vụ thật."""
    from googlecast_mcp import tts

    async def pair(cache, salt):
        return await asyncio.gather(
            tts.synthesize(f"Vòng lặp {salt} câu một", cache_dir=cache),
            tts.synthesize(f"Vòng lặp {salt} câu hai", cache_dir=cache),
        )

    with tmpdir() as d:
        asyncio.run(pair(d, 1))
        asyncio.run(pair(d, 2))
        made = [p for p in d.iterdir() if p.stat().st_size > 0]
    want(len(made) == 4, f"cả hai vòng lặp phải render được, chỉ có {len(made)}/4")


# ==========================================================================
# Tầng --hardware: PHÁT TIẾNG THẬT ra loa
# ==========================================================================


def _hardware_speaker():
    name = os.environ.get("GOOGLECAST_MCP_TEST_SPEAKER")
    if not name:
        raise RuntimeError(
            "đặt GOOGLECAST_MCP_TEST_SPEAKER=<tên loa> trước khi chạy --hardware"
        )
    return name


@check("hardware_discovers_real_speakers", tier="hardware")
def _():
    from googlecast_mcp import server as srv

    speakers = asyncio.run(srv.list_speakers())
    names = [s["friendly_name"] for s in speakers]
    want(speakers, "phải tìm ra ít nhất một loa thật trên mạng")
    want(_hardware_speaker() in names, f"không thấy loa thử nghiệm trong {names}")
    want(
        all(s["cast_type"] in ("audio", "group") for s in speakers),
        f"list_speakers lẫn thiết bị hình ảnh: {[(s['friendly_name'], s['cast_type']) for s in speakers]}",
    )


@check("hardware_says_on_real_speaker", tier="hardware")
def _():
    """Cast thật. Bằng chứng phải BỀN: content_id khớp URL và duration > 0 —
    player_state đọc ngay lúc trả về có thể đã hết hạn (clip ngắn phát xong)."""
    from googlecast_mcp import server as srv

    name = _hardware_speaker()
    out = asyncio.run(srv.say("Đây là bài kiểm tra tự động", name))
    want(out["status"] == "ok", f"phải phát được: {out}")
    want(out["results"][0]["status"] == "playing", f"kết quả từng loa: {out['results']}")
    url = out["audio_url"]

    # Bằng chứng bền, nhưng vẫn cần MỐC CHỜ: `content_id` xuất hiện ngay khi
    # thiết bị nhận lệnh, còn `duration` chỉ có sau khi nó TẢI và đọc xong file.
    # Đọc cả hai tại cùng một khoảnh khắc là đo `duration` quá sớm — đúng cái
    # luật "mốc chờ + bằng chứng bền" cảnh báo, chỉ khác là hụt nửa sau.
    media = {}
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        media = asyncio.run(srv.get_status(name))["media"]
        if media.get("content_id") == url and (media.get("duration") or 0) > 0:
            break
        time.sleep(1.0)
    want(
        media.get("content_id") == url,
        f"loa phải đang giữ đúng URL vừa cast.\ncó : {media.get('content_id')}\ncần: {url}",
    )
    want(
        (media.get("duration") or 0) > 0,
        f"thiết bị phải đọc được thời lượng trong 20s (tức là đã TẢI file): "
        f"duration={media.get('duration')}",
    )


@check("hardware_all_never_doubles_a_speaker", tier="hardware")
def _():
    """'all' không được gửi tới cả nhóm lẫn thành viên: cùng một loa vật lý sẽ
    nhận hai luồng, mà API vẫn báo 'playing' cho cả bốn. Dấu vết duy nhất phân
    biệt được là host trùng nhau."""
    from googlecast_mcp import server as srv

    names, prompt = asyncio.run(srv._select_targets("all"))
    want(prompt is None, "'all' phải là lựa chọn hợp lệ")
    speakers = {s["friendly_name"]: s for s in asyncio.run(srv.list_speakers())}
    chosen = [speakers[n] for n in names if n in speakers]
    want(
        all(s["cast_type"] != "group" for s in chosen),
        f"'all' vẫn còn nhóm loa: {[(s['friendly_name'], s['cast_type']) for s in chosen]}",
    )
    # So TẬP kỳ vọng tường minh, không so kích thước: `len(x) == len(set(x))`
    # vẫn xanh khi `chosen` co lại còn một phần tử (hoặc rỗng), tức là xanh
    # đúng vào lúc lựa chọn hỏng nặng nhất. Đây là dạng test giả v1.9 nêu tên.
    want(len(chosen) >= 2, f"phải chọn được ít nhất 2 loa để phép kiểm có nghĩa: {names}")
    want(
        {s["friendly_name"] for s in chosen}
        == {s["friendly_name"] for s in speakers.values() if s["cast_type"] != "group"},
        f"'all' phải đúng bằng tập loa không-phải-nhóm: {sorted(s['friendly_name'] for s in chosen)}",
    )
    hosts = [s["host"] for s in chosen]
    want(
        sorted(hosts) == sorted(set(hosts)),
        f"hai mục trỏ cùng một máy loa: {hosts}",
    )


@check("hardware_volume_round_trip", tier="hardware")
def _():
    from googlecast_mcp import server as srv

    name = _hardware_speaker()
    before = asyncio.run(srv.get_status(name))["app"]["volume_level"]
    try:
        asyncio.run(srv.set_volume(name, 0.25))
        time.sleep(1.5)
        got = asyncio.run(srv.get_status(name))["app"]["volume_level"]
        want(abs(got - 0.25) < 0.05, f"âm lượng phải đổi thật: {got}")
    finally:
        if before is not None:
            asyncio.run(srv.set_volume(name, before))


# ==========================================================================
# Bộ chạy
# ==========================================================================


def run(tiers, only, quiet=False, as_json=False):
    registered = [
        (i, t, f) for (i, t, f) in REGISTRY if t in tiers and (not only or any(o in i for o in only))
    ]
    total = len(registered)
    ran = 0
    passed, failed, errored = [], [], []

    for item_id, tier, fn in registered:
        started = time.monotonic()
        outcome = "ERROR"
        detail = ""
        try:
            fn()
            outcome = "PASS"
        except AssertionError as exc:
            outcome = "FAIL"
            detail = str(exc)
        except BaseException as exc:  # noqa: BLE001 - hạ tầng hỏng là ERROR, không nuốt
            outcome = "ERROR"
            detail = f"{type(exc).__name__}: {exc}\n" + textwrap_indent(
                traceback.format_exc(), "        "
            )
        finally:
            # Đếm ĐÃ CHẠY ở đây, trước khi biết xanh hay đỏ.
            ran += 1
        took = time.monotonic() - started
        {"PASS": passed, "FAIL": failed, "ERROR": errored}[outcome].append(item_id)
        if not quiet or outcome != "PASS":
            print(f"  [{outcome:5}] {item_id} ({tier}, {took:.2f}s)")
            if detail:
                print(f"        {detail}")

    if as_json:
        print(
            "JSON " + json.dumps(
                {
                    "ran": ran,
                    "total": total,
                    "pass": passed,
                    "fail": failed,
                    "error": errored,
                },
                ensure_ascii=False,
            )
        )
    print()
    print(f"đã chạy {ran}/{total} mục đăng ký")
    print(f"  xanh {len(passed)} · đỏ {len(failed)} · lỗi hạ tầng {len(errored)}")
    if failed:
        print(f"  đỏ : {', '.join(failed)}")
    if errored:
        print(f"  lỗi: {', '.join(errored)}")

    if total == 0:
        print("KHÔNG ĐẠT — không mục nào khớp bộ lọc (khớp 0 case không phải là đạt)")
        return 2
    if ran < total:
        print(f"KHÔNG ĐẠT — chỉ chạy {ran}/{total} mục; bài kiểm đã sập giữa chừng")
        return 2
    if failed or errored:
        print("KHÔNG ĐẠT")
        return 1
    print("ĐẠT")
    return 0


def textwrap_indent(text, prefix):
    return "".join(prefix + line for line in text.splitlines(keepends=True))


def main():
    ap = argparse.ArgumentParser(description="Bài kiểm googlecast-mcp")
    ap.add_argument("--online", action="store_true", help="thêm tầng gọi edge-tts thật")
    ap.add_argument(
        "--hardware",
        action="store_true",
        help="thêm tầng CAST THẬT — phát tiếng ra loa; phải xin phép trước",
    )
    ap.add_argument("--only", default="", help="chỉ chạy các mục có id chứa chuỗi này (cách phẩy)")
    ap.add_argument("--list", action="store_true", help="liệt kê id các mục rồi thoát")
    ap.add_argument("-q", "--quiet", action="store_true", help="chỉ in mục không xanh")
    ap.add_argument("--json", action="store_true", help="in thêm một dòng JSON tổng hợp")
    args = ap.parse_args()

    if args.list:
        for item_id, tier, _fn in REGISTRY:
            print(f"{tier:8} {item_id}")
        return 0

    tiers = {"offline"}
    if args.online:
        tiers.add("online")
    if args.hardware:
        tiers.add("hardware")
        print("!! tầng --hardware sẽ PHÁT TIẾNG THẬT ra loa.")
        print(f"!! loa thử nghiệm: {os.environ.get('GOOGLECAST_MCP_TEST_SPEAKER', '(chưa đặt)')}")

    only = [s.strip() for s in args.only.split(",") if s.strip()]
    if only:
        print(f"(lượt RÚT GỌN: chỉ chạy mục khớp {only} — không phải lượt đầy đủ)")
    print(f"tầng: {', '.join(sorted(tiers))}")
    print()
    return run(tiers, only, args.quiet, args.json)


if __name__ == "__main__":
    sys.exit(main())
