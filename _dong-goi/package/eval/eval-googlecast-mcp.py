#!/usr/bin/env python3
"""Bài kiểm cho googlecast-mcp.

Ba tầng tác dụng phụ:
  (mặc định)   offline  — không mạng, không thiết bị. Mọi thứ chạm ngoài đều bị thay thế.
  --online              — gọi edge-tts thật (cần internet). Không phát ra loa nào.
  --hardware            — cast thật ra loa: PHÁT RA TIẾNG. Chỉ chạy khi đã xin phép.

Nguyên tắc của bài kiểm này:
  1. ĐẾM ĐỦ TRƯỚC KHI ĐẾM XANH. Mỗi mục đăng ký trong CHECKS được chạy riêng,
     bọc riêng. Báo cáo in "đã chạy X/Y mục đăng ký"; X < Y là FAIL toàn cục,
     kể cả khi mọi mục đã chạy đều xanh. Sập giữa chừng không thể giả dạng ĐẠT.
  2. MỌI MỤC PHẢI GỌI VÀO MÃ SẢN PHẨM. Không có mục nào chỉ kiểm chính nó.
  3. Mỗi mục phải nằm trong ít nhất một danh sách kỳ-vọng-đỏ của reverse-check.py.
     Mục mà không lỗi gieo nào làm đỏ được là nghi phạm cấu trúc.
  4. So TẬP kỳ vọng tường minh, không so KÍCH THƯỚC.

Chạy:
    python eval-googlecast-mcp.py
    python eval-googlecast-mcp.py --online
    python eval-googlecast-mcp.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import socket
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
from contextlib import contextmanager
from pathlib import Path

# Mã sản phẩm: bản sao do reverse-check.py chỉ định (qua PYTHONPATH /
# GOOGLECAST_MCP_SRC), nếu không thì cây thật cạnh gói này.
_DEFAULT_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, os.environ.get("GOOGLECAST_MCP_SRC", str(_DEFAULT_SRC)))

from googlecast_mcp import cast_manager as cm  # noqa: E402
from googlecast_mcp import media_server as ms  # noqa: E402
from googlecast_mcp import server as srv  # noqa: E402
from googlecast_mcp import speaker_store as st  # noqa: E402
from googlecast_mcp import tts  # noqa: E402
from googlecast_mcp import __main__ as entry  # noqa: E402

# --------------------------------------------------------------------------
# Sổ đăng ký
# --------------------------------------------------------------------------

CHECKS: list[tuple[str, str, object]] = []  # (id, tầng, hàm)


def check(check_id: str, tier: str = "offline"):
    def deco(fn):
        CHECKS.append((check_id, tier, fn))
        return fn

    return deco


# --------------------------------------------------------------------------
# Dụng cụ dựng bối cảnh
# --------------------------------------------------------------------------


def is_mp3(data: bytes) -> bool:
    """Đúng khung mp3: hoặc thẻ ID3, hoặc từ đồng bộ MPEG (11 bit 1 đầu tiên).

    Đừng so mấy byte đầu với một danh sách tiền tố cứng: edge-tts trả về nhiều
    biến thể (fff3, fffb, ...) và so nhầm ĐỘ DÀI thì phép so không bao giờ
    đúng — bài kiểm đỏ trong khi sản phẩm không sao.
    """
    if data[:3] == b"ID3":
        return True
    return len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


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
        self.status = type("S", (), {})()
        self.status.player_state = "PLAYING"
        self.status.title = None
        self.status.content_id = None
        self.status.content_type = None
        self.status.duration = 2.0
        self.status.current_time = 0.0
        self.calls: list[tuple] = []

    def play_media(self, url, content_type, title=None):
        self.calls.append(("play_media", url, content_type, title))
        self.status.content_id = url
        self.status.content_type = content_type
        self.status.title = title

    def block_until_active(self, timeout=10):
        pass

    def play(self):
        self.calls.append(("play",))

    def pause(self):
        self.calls.append(("pause",))

    def stop(self):
        self.calls.append(("stop",))

    def seek(self, pos):
        self.calls.append(("seek", pos))


class FakeCast:
    def __init__(self, name, uuid, cast_type="audio", host="192.168.1.22"):
        self.cast_info = FakeCastInfo(name, uuid, cast_type, host)
        self.media_controller = FakeMediaController()
        self.status = type("A", (), {})()
        self.status.display_name = "Default Media Receiver"
        self.status.app_id = "CC1AD845"
        self.status.is_active_input = None
        self.status.volume_level = 0.5
        self.status.volume_muted = False
        self.calls: list[tuple] = []
        self.waited = False

    def wait(self, timeout=10):
        self.waited = True

    def set_volume(self, level):
        self.calls.append(("set_volume", level))

    def set_volume_muted(self, muted):
        self.calls.append(("set_volume_muted", muted))

    def quit_app(self):
        self.calls.append(("quit_app",))

    def disconnect(self, blocking=False):
        self.calls.append(("disconnect",))


def make_manager(devices, store_path):
    """CastManager đã nạp sẵn thiết bị giả, dùng store trong thư mục tạm."""
    mgr = cm.CastManager(store=st.SpeakerStore(Path(store_path)))
    for cast in devices:
        mgr._devices[str(cast.cast_info.uuid)] = cast
    mgr._store.save([cm.CastManager._info(c) for c in devices])
    return mgr


@contextmanager
def swapped_server(devices, *, cache_dir=None):
    """Tráo TRỌN BỘ bối cảnh của server: manager + media server + thư mục cache.

    Tráo nửa vời nguy hơn không tráo: nếu chỉ thay _manager mà để nguyên
    _media_server, url_for() nhận file nằm ngoài thư mục nó phục vụ và ném
    ValueError ở một chỗ chẳng liên quan gì tới điều đang kiểm.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cache = Path(cache_dir) if cache_dir else tmp_path / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        old_manager, old_media = srv._manager, srv._media_server
        old_env = os.environ.get("GOOGLECAST_MCP_CACHE")
        os.environ["GOOGLECAST_MCP_CACHE"] = str(cache)
        srv._manager = make_manager(devices, tmp_path / "speakers.json")
        srv._media_server = ms.MediaServer(cache, host="127.0.0.1", port=0)
        try:
            yield srv._manager, srv._media_server, cache
        finally:
            srv._media_server.stop()
            srv._manager, srv._media_server = old_manager, old_media
            if old_env is None:
                os.environ.pop("GOOGLECAST_MCP_CACHE", None)
            else:
                os.environ["GOOGLECAST_MCP_CACHE"] = old_env


class FakeCommunicate:
    """Thay edge_tts.Communicate. Ghi lại lời gọi, viết ra file mp3 giả."""

    calls: list[tuple] = []
    behaviour = "ok"  # ok | fail | empty | fail_once
    _attempts: dict[str, int] = {}

    def __init__(self, text, voice, rate="+0%", volume="+0%"):
        self.text, self.voice, self.rate, self.volume = text, voice, rate, volume
        FakeCommunicate.calls.append((text, voice, rate, volume))

    async def save(self, path):
        await asyncio.sleep(0.01)
        mode = FakeCommunicate.behaviour
        if mode == "fail_once":
            n = FakeCommunicate._attempts.get(path, 0)
            FakeCommunicate._attempts[path] = n + 1
            if n == 0:
                Path(path).write_bytes(b"")  # để lại file 0 byte rồi ném lỗi
                raise ConnectionError("Cannot connect to host")
        elif mode == "fail":
            Path(path).write_bytes(b"")
            raise ConnectionError("Cannot connect to host")
        elif mode == "empty":
            Path(path).write_bytes(b"")
            return
        Path(path).write_bytes(b"ID3fake-audio-bytes")


class _FastSleepAsyncio:
    """Proxy quanh module asyncio, chỉ rút ngắn giãn cách giữa các lần thử lại.

    Gán thẳng asyncio.sleep = lambda: asyncio.sleep(0) là tự trỏ vào chính nó
    (tts.asyncio VÀ asyncio của bài kiểm là CÙNG một đối tượng module) — vòng
    lặp vô hạn hiện ra ở một chỗ chẳng liên quan. Proxy giữ nguyên module thật.
    """

    def __getattr__(self, name):
        return getattr(asyncio, name)

    async def sleep(self, _delay, *a, **k):
        await asyncio.sleep(0)


@contextmanager
def fake_tts(behaviour="ok", fast_retry=False):
    real = tts.edge_tts.Communicate
    real_asyncio = tts.asyncio
    FakeCommunicate.calls = []
    FakeCommunicate._attempts = {}
    FakeCommunicate.behaviour = behaviour
    tts.edge_tts.Communicate = FakeCommunicate
    if fast_retry:
        tts.asyncio = _FastSleepAsyncio()
    try:
        yield FakeCommunicate
    finally:
        tts.edge_tts.Communicate = real
        tts.asyncio = real_asyncio


@contextmanager
def fake_pychromecast(casts=None, from_host=None):
    """Tráo TRỌN cửa ngõ pychromecast của cast_manager."""
    real_get = cm.pychromecast.get_chromecasts
    real_host = cm.pychromecast.get_chromecast_from_host
    seen = {"discover": 0, "from_host": []}

    def _get(timeout=5.0):
        seen["discover"] += 1
        return (list(casts or []), object())

    def _from_host(info, tries=1, timeout=5):
        seen["from_host"].append(info)
        if from_host is None:
            raise OSError("no route")
        return from_host

    cm.pychromecast.get_chromecasts = _get
    cm.pychromecast.get_chromecast_from_host = _from_host
    try:
        yield seen
    finally:
        cm.pychromecast.get_chromecasts = real_get
        cm.pychromecast.get_chromecast_from_host = real_host


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ==========================================================================
# speaker_store.py
# ==========================================================================


@check("store.is_speaker.audio")
def _():
    assert st.is_speaker({"cast_type": "audio"}) is True


@check("store.is_speaker.group")
def _():
    assert st.is_speaker({"cast_type": "group"}) is True


@check("store.is_speaker.video_excluded")
def _():
    assert st.is_speaker({"cast_type": "cast"}) is False
    assert st.is_speaker({}) is False


@check("store.default_path.env_override")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["GOOGLECAST_MCP_STORE"] = f"{tmp}/x.json"
        try:
            assert st.default_store_path() == Path(tmp) / "x.json"
        finally:
            os.environ.pop("GOOGLECAST_MCP_STORE")
    os.environ.pop("GOOGLECAST_MCP_STORE", None)
    assert st.default_store_path() == Path.home() / ".googlecast-mcp" / "speakers.json"


@check("store.load.missing_file_is_empty")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        assert st.SpeakerStore(Path(tmp) / "nope.json").load() == []


@check("store.load.corrupt_file_is_empty")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "s.json"
        p.write_text("{not json", encoding="utf-8")
        assert st.SpeakerStore(p).load() == []


@check("store.save.roundtrip")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        store = st.SpeakerStore(Path(tmp) / "s.json")
        store.save([{"uuid": "u1", "friendly_name": "Kitchen", "cast_type": "audio"}])
        loaded = store.load()
        assert [d["uuid"] for d in loaded] == ["u1"]
        assert loaded[0]["friendly_name"] == "Kitchen"


@check("store.save.merges_by_uuid")
def _():
    """Quét mDNS sót thiết bị không được xoá thiết bị đã biết."""
    with tempfile.TemporaryDirectory() as tmp:
        store = st.SpeakerStore(Path(tmp) / "s.json")
        store.save([{"uuid": "u1", "friendly_name": "Kitchen", "cast_type": "audio"}])
        store.save([{"uuid": "u2", "friendly_name": "Bed", "cast_type": "audio"}])
        assert {d["uuid"] for d in store.load()} == {"u1", "u2"}


@check("store.save.update_keeps_old_fields")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        store = st.SpeakerStore(Path(tmp) / "s.json")
        store.save([{"uuid": "u1", "friendly_name": "Kitchen", "cast_type": "audio"}])
        store.save([{"uuid": "u1", "host": "192.168.1.9"}])
        d = store.load()[0]
        assert d["friendly_name"] == "Kitchen" and d["host"] == "192.168.1.9"


@check("store.save.no_tmp_left_behind")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        store = st.SpeakerStore(Path(tmp) / "s.json")
        store.save([{"uuid": "u1", "cast_type": "audio"}])
        assert {p.name for p in Path(tmp).iterdir()} == {"s.json"}


@check("store.save.creates_parent_dir")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        store = st.SpeakerStore(Path(tmp) / "deep" / "er" / "s.json")
        store.save([{"uuid": "u1", "cast_type": "audio"}])
        assert store.path.exists()


@check("store.speakers.filters_video")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        store = st.SpeakerStore(Path(tmp) / "s.json")
        store.save(
            [
                {"uuid": "a", "friendly_name": "Kitchen", "cast_type": "audio"},
                {"uuid": "g", "friendly_name": "Family group", "cast_type": "group"},
                {"uuid": "v", "friendly_name": "Living room TV", "cast_type": "cast"},
            ]
        )
        assert {d["friendly_name"] for d in store.speakers()} == {
            "Kitchen",
            "Family group",
        }


# ==========================================================================
# tts.py
# ==========================================================================


@check("tts.resolve_voice.female")
def _():
    assert tts.resolve_voice("female") == "vi-VN-HoaiMyNeural"


@check("tts.resolve_voice.male")
def _():
    assert tts.resolve_voice("male") == "vi-VN-NamMinhNeural"


@check("tts.resolve_voice.default_when_blank")
def _():
    assert tts.resolve_voice(None) == "vi-VN-HoaiMyNeural"
    assert tts.resolve_voice("") == "vi-VN-HoaiMyNeural"


@check("tts.resolve_voice.passthrough_full_id")
def _():
    assert tts.resolve_voice("en-US-AriaNeural") == "en-US-AriaNeural"


@check("tts.synthesize.empty_text_rejected")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ("", "   "):
                try:
                    await tts.synthesize(bad, cache_dir=Path(tmp))
                except ValueError:
                    continue
                raise AssertionError(f"chữ rỗng {bad!r} lẽ ra phải bị từ chối")

    asyncio.run(run())


@check("tts.synthesize.writes_file")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts():
            p = await tts.synthesize("xin chào", cache_dir=Path(tmp))
            assert p.exists() and p.stat().st_size > 0
            assert p.suffix == ".mp3"

    asyncio.run(run())


@check("tts.synthesize.cache_hit_skips_render")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts() as fc:
            await tts.synthesize("xin chào", cache_dir=Path(tmp))
            await tts.synthesize("xin chào", cache_dir=Path(tmp))
            assert len(fc.calls) == 1, f"lẽ ra render 1 lần, thực tế {len(fc.calls)}"

    asyncio.run(run())


@check("tts.synthesize.cache_key_varies_by_voice")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts():
            a = await tts.synthesize("xin chào", voice="female", cache_dir=Path(tmp))
            b = await tts.synthesize("xin chào", voice="male", cache_dir=Path(tmp))
            assert a != b

    asyncio.run(run())


@check("tts.synthesize.cache_key_varies_by_rate")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts():
            a = await tts.synthesize("xin chào", rate="+0%", cache_dir=Path(tmp))
            b = await tts.synthesize("xin chào", rate="-20%", cache_dir=Path(tmp))
            assert a != b

    asyncio.run(run())


@check("tts.synthesize.cache_key_varies_by_text")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts():
            a = await tts.synthesize("một", cache_dir=Path(tmp))
            b = await tts.synthesize("hai", cache_dir=Path(tmp))
            assert a != b

    asyncio.run(run())


@check("tts.synthesize.zero_byte_is_not_a_cache_hit")
def _():
    """File 0 byte của lần hỏng trước KHÔNG được coi là bản render hợp lệ."""

    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts() as fc:
            p = await tts.synthesize("xin chào", cache_dir=Path(tmp))
            p.write_bytes(b"")
            again = await tts.synthesize("xin chào", cache_dir=Path(tmp))
            assert len(fc.calls) == 2, "file 0 byte bị nhầm là cache hợp lệ"
            assert again.stat().st_size > 0

    asyncio.run(run())


@check("tts.synthesize.retries_then_succeeds")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts("fail_once", fast_retry=True) as fc:
            p = await tts.synthesize("xin chào", cache_dir=Path(tmp))
            assert len(fc.calls) == 2, f"lẽ ra thử lại lần 2, thực tế {len(fc.calls)}"
            assert p.stat().st_size > 0

    asyncio.run(run())


@check("tts.synthesize.gives_up_after_three_attempts")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts("fail", fast_retry=True) as fc:
            try:
                await tts.synthesize("xin chào", cache_dir=Path(tmp))
            except RuntimeError as exc:
                assert "3 attempts" in str(exc)
                assert len(fc.calls) == 3, f"lẽ ra thử 3 lần, thực tế {len(fc.calls)}"
                return
            raise AssertionError("hỏng cả 3 lần mà vẫn không báo lỗi")

    asyncio.run(run())


@check("tts.synthesize.no_zero_byte_file_left_after_failure")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts("fail", fast_retry=True):
            try:
                await tts.synthesize("xin chào", cache_dir=Path(tmp))
            except RuntimeError:
                pass
            leftovers = [p for p in Path(tmp).iterdir() if p.stat().st_size == 0]
            assert not leftovers, f"còn đọng file 0 byte: {leftovers}"

    asyncio.run(run())


@check("tts.synthesize.empty_render_is_failure_not_success")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts("empty", fast_retry=True):
            try:
                await tts.synthesize("xin chào", cache_dir=Path(tmp))
            except RuntimeError as exc:
                assert "no audio" in str(exc) or "3 attempts" in str(exc)
                return
            raise AssertionError("save() không tạo audio nào mà vẫn báo thành công")

    asyncio.run(run())


@check("tts.fanout.six_concurrent_all_succeed")
def _():
    """Dồn 6 yêu cầu song song: tuần tự hoá phải giữ cho cả 6 cùng thành công.

    Khẳng định nằm TRONG vòng đời của thư mục tạm — đếm sau khi tmpdir đóng
    là đếm vào chỗ trống, đỏ bừa mà không phải lỗi sản phẩm.
    """

    async def run():
        with tempfile.TemporaryDirectory() as tmp, fake_tts():
            paths = await asyncio.gather(
                *(tts.synthesize(f"câu số {i}", cache_dir=Path(tmp)) for i in range(6))
            )
            ok = [p for p in paths if p.exists() and p.stat().st_size > 0]
            assert len(ok) == 6, f"chỉ {len(ok)}/6 render thành công"
            assert len({p.name for p in paths}) == 6

    asyncio.run(run())


@check("tts.lock.is_per_event_loop_under_contention")
def _():
    """Khoá phải theo TỪNG vòng lặp.

    Điều kiện thật để lộ lỗi không phải "gọi asyncio.run() hai lần" — mà là
    vòng lặp thứ nhất THỰC SỰ CÓ TRANH CHẤP trên khoá. Đường nhanh của
    Lock.acquire() trả về trước khi chạm _get_loop(), nên một khoá mức module
    chỉ tự gắn vào vòng lặp khi có hai render chồng nhau. Phải gây tranh chấp
    ở vòng 1 rồi mới thử vòng 2.
    """
    with tempfile.TemporaryDirectory() as tmp, fake_tts():

        async def contended(tag):
            return await asyncio.gather(
                *(tts.synthesize(f"{tag}-{i}", cache_dir=Path(tmp)) for i in range(2))
            )

        first = asyncio.run(contended("v1"))
        second = asyncio.run(contended("v2"))  # RuntimeError nếu khoá gắn nhầm vòng lặp
        assert len(first) == 2 and len(second) == 2
        assert all(p.stat().st_size > 0 for p in first + second)


@check("tts.cache_dir.env_override")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        old = os.environ.get("GOOGLECAST_MCP_CACHE")
        os.environ["GOOGLECAST_MCP_CACHE"] = f"{tmp}/c"
        try:
            d = tts.default_cache_dir()
            assert d == Path(tmp) / "c" and d.is_dir()
        finally:
            if old is None:
                os.environ.pop("GOOGLECAST_MCP_CACHE", None)
            else:
                os.environ["GOOGLECAST_MCP_CACHE"] = old


# ==========================================================================
# media_server.py
# ==========================================================================


@check("media.lan_ip.returns_ipv4")
def _():
    ip = ms.lan_ip()
    parts = ip.split(".")
    assert len(parts) == 4 and all(p.isdigit() for p in parts), ip


@check("media.url_for.shape")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "a.mp3"
        f.write_bytes(b"x")
        server = ms.MediaServer(Path(tmp), host="10.0.0.5", port=0)
        try:
            url = server.url_for(f)
            # Cổng phải là cổng ĐÃ BIND thật. So url với chính server.port là
            # tự so với chính mình: server chưa chạy thì cả hai cùng bằng 0 và
            # phép so vẫn xanh — đúng một dạng test giả.
            assert server.port != 0, "url_for() chưa khởi động server, cổng vẫn là 0"
            assert url == f"http://10.0.0.5:{server.port}/a.mp3", url
        finally:
            server.stop()


@check("media.url_for.percent_encodes")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "cơm chín.mp3"
        f.write_bytes(b"x")
        server = ms.MediaServer(Path(tmp), host="10.0.0.5", port=0)
        try:
            url = server.url_for(f)
            assert " " not in url and url.endswith(".mp3"), url
            assert "%20" in url, url
        finally:
            server.stop()


@check("media.url_for.starts_server_lazily")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "a.mp3"
        f.write_bytes(b"x")
        server = ms.MediaServer(Path(tmp), host="127.0.0.1", port=0)
        try:
            assert server._httpd is None
            server.url_for(f)
            assert server._httpd is not None
        finally:
            server.stop()


@check("media.serves_file_over_http")
def _():
    """Thiết bị Cast TỰ đi tải file — phải tải được thật, không chỉ dựng URL."""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "a.mp3"
        f.write_bytes(b"ID3fake-audio-bytes")
        server = ms.MediaServer(Path(tmp), host="127.0.0.1", port=free_port())
        try:
            url = server.url_for(f)
            with urllib.request.urlopen(url, timeout=5) as resp:
                assert resp.status == 200
                assert resp.read() == b"ID3fake-audio-bytes"
        finally:
            server.stop()


@check("media.binds_all_interfaces")
def _():
    """Bind 0.0.0.0 nhưng quảng bá host riêng — hai thứ KHÁC NHAU."""
    with tempfile.TemporaryDirectory() as tmp:
        server = ms.MediaServer(Path(tmp), host="10.0.0.5", port=0)
        try:
            server.start()
            assert server._httpd.server_address[0] == "0.0.0.0"
            assert server._host == "10.0.0.5"
        finally:
            server.stop()


@check("media.set_port.pins_port")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        port = free_port()
        server = ms.MediaServer(Path(tmp), host="127.0.0.1", port=0)
        try:
            server.set_port(port)
            server.start()
            assert server.port == port
        finally:
            server.stop()


@check("media.set_port.rejected_while_running")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        server = ms.MediaServer(Path(tmp), host="127.0.0.1", port=0)
        try:
            server.start()
            try:
                server.set_port(free_port())
            except RuntimeError:
                return
            raise AssertionError("đổi cổng lúc đang chạy lẽ ra phải bị từ chối")
        finally:
            server.stop()


@check("media.start_is_idempotent")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        server = ms.MediaServer(Path(tmp), host="127.0.0.1", port=0)
        try:
            server.start()
            first = server.port
            server.start()
            assert server.port == first
        finally:
            server.stop()


@check("media.stop_is_safe_when_not_running")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        ms.MediaServer(Path(tmp)).stop()  # không được ném lỗi


@check("media.creates_directory")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "chua-co"
        server = ms.MediaServer(d, host="127.0.0.1", port=0)
        try:
            server.start()
            assert d.is_dir()
        finally:
            server.stop()


# ==========================================================================
# cast_manager.py
# ==========================================================================


@check("cast.guess_content_type.audio")
def _():
    assert cm._guess_content_type("http://h/a.mp3") == "audio/mpeg"
    assert cm._guess_content_type("http://h/a.flac") == "audio/flac"


@check("cast.guess_content_type.video")
def _():
    assert cm._guess_content_type("http://h/a.mp4") == "video/mp4"
    assert cm._guess_content_type("http://h/a.webm") == "video/webm"


@check("cast.guess_content_type.ignores_query_string")
def _():
    assert cm._guess_content_type("http://h/a.mp3?token=1") == "audio/mpeg"


@check("cast.guess_content_type.case_insensitive")
def _():
    assert cm._guess_content_type("http://h/A.MP3") == "audio/mpeg"


@check("cast.resolve.by_friendly_name_case_insensitive")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = make_manager([FakeCast("Kitchen speaker", "u1")], Path(tmp) / "s.json")
        assert mgr._resolve_locally("kitchen SPEAKER") is not None


@check("cast.resolve.by_uuid")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = make_manager([FakeCast("Kitchen speaker", "u1")], Path(tmp) / "s.json")
        assert mgr._resolve_locally("u1") is not None


@check("cast.resolve.unknown_is_none")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = make_manager([FakeCast("Kitchen speaker", "u1")], Path(tmp) / "s.json")
        assert mgr._resolve_locally("Không có") is None


@check("cast.resolve.saved_address_tried_before_rescan")
def _():
    """mDNS bỏ sót thiết bị ĐÃ LƯU không được thành DeviceNotFoundError."""
    with tempfile.TemporaryDirectory() as tmp:
        saved = FakeCast("Kitchen speaker", "11111111-1111-1111-1111-111111111111")
        mgr = make_manager([saved], Path(tmp) / "s.json")
        mgr._devices.clear()  # mDNS đã sót nó khỏi lần quét này
        with fake_pychromecast(casts=[], from_host=saved) as seen:
            found = mgr._resolve("Kitchen speaker")
            assert found is saved
            assert seen["from_host"], "chưa hề thử địa chỉ đã lưu"
            assert seen["discover"] == 0, "quét lại dù địa chỉ đã lưu vẫn dùng được"


@check("cast.resolve.raises_with_known_devices_listed")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = make_manager([FakeCast("Kitchen speaker", "u1")], Path(tmp) / "s.json")
        with fake_pychromecast(casts=[], from_host=None):
            try:
                mgr._resolve("Ma quái")
            except cm.DeviceNotFoundError as exc:
                assert "Kitchen speaker" in str(exc), str(exc)
                return
            raise AssertionError("thiết bị không tồn tại mà không báo lỗi")


@check("cast.set_volume.clamps_range")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        c = FakeCast("Kitchen speaker", "u1")
        mgr = make_manager([c], Path(tmp) / "s.json")
        assert mgr.set_volume("Kitchen speaker", 5.0) == 1.0
        assert mgr.set_volume("Kitchen speaker", -3.0) == 0.0
        assert mgr.set_volume("Kitchen speaker", 0.4) == 0.4
        assert [lv for name, lv in c.calls if name == "set_volume"] == [1.0, 0.0, 0.4]


@check("cast.play_media.guesses_type_and_returns_status")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        c = FakeCast("Kitchen speaker", "u1")
        mgr = make_manager([c], Path(tmp) / "s.json")
        out = mgr.play_media("Kitchen speaker", "http://h/a.mp3", None, "chào")
        assert c.media_controller.calls[0] == (
            "play_media",
            "http://h/a.mp3",
            "audio/mpeg",
            "chào",
        )
        assert out["media"]["content_id"] == "http://h/a.mp3"


@check("cast.status.shape")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = make_manager([FakeCast("Kitchen speaker", "u1")], Path(tmp) / "s.json")
        s = mgr.status("Kitchen speaker")
        assert set(s) == {"device", "app", "media"}
        assert set(s["media"]) == {
            "player_state",
            "title",
            "content_id",
            "content_type",
            "duration",
            "current_time",
        }


@check("cast.info.fields")
def _():
    info = cm.CastManager._info(FakeCast("Kitchen speaker", "u1", "audio", "192.168.1.22"))
    assert set(info) == {
        "friendly_name",
        "uuid",
        "model_name",
        "manufacturer",
        "host",
        "port",
        "cast_type",
    }
    assert info["host"] == "192.168.1.22" and info["cast_type"] == "audio"


@check("cast.connect_waits_before_control")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        c = FakeCast("Kitchen speaker", "u1")
        mgr = make_manager([c], Path(tmp) / "s.json")
        mgr.pause("Kitchen speaker")
        assert c.waited, "điều khiển thiết bị trước khi kết nối xong"
        assert ("pause",) in c.media_controller.calls


@check("cast.list_speakers.filters_video")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = make_manager(
            [
                FakeCast("Kitchen speaker", "u1", "audio"),
                FakeCast("Living room TV", "u2", "cast"),
            ],
            Path(tmp) / "s.json",
        )
        assert {d["friendly_name"] for d in mgr.list_speakers()} == {"Kitchen speaker"}


@check("cast.discover.persists_to_store")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "s.json"
        mgr = cm.CastManager(store=st.SpeakerStore(path))
        with fake_pychromecast(casts=[FakeCast("Kitchen speaker", "u1")]):
            mgr.discover(0.1)
        assert st.SpeakerStore(path).load()[0]["friendly_name"] == "Kitchen speaker"


# ==========================================================================
# server.py — chọn loa, say()
# ==========================================================================

TOOL_NAMES = {
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
}


@check("server.tools.exact_set")
def _():
    """So TẬP tên tường minh, không so số lượng."""
    names = {t.name for t in asyncio.run(srv.mcp.list_tools())}
    assert names == TOOL_NAMES, f"thừa {names - TOOL_NAMES}, thiếu {TOOL_NAMES - names}"


@check("server.say.without_a_speaker_choice_plays_nothing")
def _():
    """Yêu cầu gốc #3: không chọn loa thì HỎI, tuyệt đối không phát."""

    async def run():
        speakers = [
            FakeCast("Kitchen speaker", "u1", "audio"),
            FakeCast("Bedroom speaker", "u2", "audio"),
        ]
        with swapped_server(speakers), fake_tts() as fc:
            out = await srv.say("Cơm đã chín rồi")
            assert out["status"] == "needs_speaker_selection", out["status"]
            assert {s["friendly_name"] for s in out["speakers"]} == {
                "Kitchen speaker",
                "Bedroom speaker",
            }
            assert fc.calls == [], "đã render TTS dù chưa chọn loa"
            for c in speakers:
                assert c.media_controller.calls == [], "đã phát dù chưa chọn loa"

    asyncio.run(run())


@check("server.say.no_speakers_on_network")
def _():
    async def run():
        with swapped_server([]), fake_pychromecast(casts=[]), fake_tts():
            out = await srv.say("Cơm đã chín rồi")
            assert out["status"] == "no_speakers_found", out["status"]

    asyncio.run(run())


@check("server.say.single_named_speaker")
def _():
    async def run():
        kitchen = FakeCast("Kitchen speaker", "u1", "audio")
        other = FakeCast("Bedroom speaker", "u2", "audio")
        with swapped_server([kitchen, other]), fake_tts():
            out = await srv.say("Cơm đã chín rồi", "Kitchen speaker")
            assert out["status"] == "ok", out
            assert out["results"] == [{"speaker": "Kitchen speaker", "status": "playing"}]
            assert len(kitchen.media_controller.calls) == 1
            assert other.media_controller.calls == []

    asyncio.run(run())


@check("server.say.comma_separated_list")
def _():
    async def run():
        a = FakeCast("Kitchen speaker", "u1", "audio")
        b = FakeCast("Bedroom speaker", "u2", "audio")
        with swapped_server([a, b]), fake_tts():
            out = await srv.say("Chào", "Kitchen speaker, Bedroom speaker")
            assert {r["speaker"] for r in out["results"]} == {
                "Kitchen speaker",
                "Bedroom speaker",
            }
            assert all(r["status"] == "playing" for r in out["results"])

    asyncio.run(run())


@check("server.say.all_excludes_speaker_groups")
def _():
    """Nhóm phát QUA thành viên: gộp cả nhóm lẫn thành viên = chồng luồng.

    API không phân biệt được (cả hai đều 'playing'); dấu vết duy nhất quan sát
    được ở tầng này là TẬP tên đã cast — nên phải so đúng tập đó.
    """

    async def run():
        group = FakeCast("Family speaker group", "g1", "group", host="192.168.1.22")
        member = FakeCast("Kitchen speaker", "u1", "audio", host="192.168.1.22")
        other = FakeCast("Bedroom speaker", "u2", "audio", host="192.168.1.23")
        with swapped_server([group, member, other]), fake_tts():
            out = await srv.say("Chào", "all")
            assert {r["speaker"] for r in out["results"]} == {
                "Kitchen speaker",
                "Bedroom speaker",
            }, out["results"]
            assert group.media_controller.calls == [], "nhóm bị cast chồng lên thành viên"

    asyncio.run(run())


@check("server.say.vietnamese_all_keyword")
def _():
    async def run():
        a = FakeCast("Kitchen speaker", "u1", "audio")
        b = FakeCast("Bedroom speaker", "u2", "audio")
        with swapped_server([a, b]), fake_tts():
            out = await srv.say("Chào", "tất cả")
            assert {r["speaker"] for r in out["results"]} == {
                "Kitchen speaker",
                "Bedroom speaker",
            }

    asyncio.run(run())


@check("server.say.broken_element_does_not_sink_the_rest")
def _():
    async def run():
        kitchen = FakeCast("Kitchen speaker", "u1", "audio")
        with swapped_server([kitchen]), fake_tts(), fake_pychromecast(
            casts=[], from_host=None
        ):
            out = await srv.say("Chào", "Kitchen speaker, Loa Ma")
            by_name = {r["speaker"]: r for r in out["results"]}
            assert by_name["Kitchen speaker"]["status"] == "playing"
            assert by_name["Loa Ma"]["status"] == "error"
            assert out["status"] == "ok", "một phần tử hỏng không được đánh sập cả lệnh"

    asyncio.run(run())


@check("server.say.all_broken_reports_failed")
def _():
    async def run():
        with swapped_server([FakeCast("Kitchen speaker", "u1", "audio")]), fake_tts(), (
            fake_pychromecast(casts=[], from_host=None)
        ):
            out = await srv.say("Chào", "Loa Ma")
            assert out["status"] == "failed", out["status"]

    asyncio.run(run())


@check("server.say.audio_url_is_fetchable_by_the_speaker")
def _():
    """URL trao cho loa phải TẢI ĐƯỢC thật — loa tự đi lấy file."""

    async def run():
        kitchen = FakeCast("Kitchen speaker", "u1", "audio")
        with swapped_server([kitchen]) as (_m, media, _c), fake_tts():
            media._host = "127.0.0.1"
            out = await srv.say("Cơm đã chín rồi", "Kitchen speaker")
            url = out["audio_url"]
            with urllib.request.urlopen(url, timeout=5) as resp:
                assert resp.status == 200
                assert len(resp.read()) > 0
            cast_url = kitchen.media_controller.calls[0][1]
            assert cast_url == url, "URL cast đi khác URL báo về"

    asyncio.run(run())


@check("server.say.casts_as_audio_mpeg")
def _():
    async def run():
        kitchen = FakeCast("Kitchen speaker", "u1", "audio")
        with swapped_server([kitchen]), fake_tts():
            await srv.say("Chào", "Kitchen speaker")
            assert kitchen.media_controller.calls[0][2] == "audio/mpeg"

    asyncio.run(run())


@check("server.say.reports_resolved_voice")
def _():
    async def run():
        with swapped_server([FakeCast("Kitchen speaker", "u1", "audio")]), fake_tts():
            out = await srv.say("Chào", "Kitchen speaker", voice="male")
            assert out["voice"] == "vi-VN-NamMinhNeural", out["voice"]

    asyncio.run(run())


@check("server.list_speakers.scans_once_when_store_is_empty")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            old = srv._manager
            srv._manager = cm.CastManager(store=st.SpeakerStore(Path(tmp) / "s.json"))
            try:
                with fake_pychromecast(
                    casts=[FakeCast("Kitchen speaker", "u1", "audio")]
                ) as seen:
                    out = await srv.list_speakers()
                    assert seen["discover"] == 1, f"quét {seen['discover']} lần"
                    assert [s["friendly_name"] for s in out] == ["Kitchen speaker"]
            finally:
                srv._manager = old

    asyncio.run(run())


# ==========================================================================
# __main__.py — an ninh vận chuyển / CORS
# ==========================================================================


@check("entry.security.allows_lan_address")
def _():
    s = entry._transport_security("0.0.0.0", [])
    assert ms.lan_ip() in s.allowed_hosts


@check("entry.security.wildcard_bind_not_treated_as_address")
def _():
    s = entry._transport_security("0.0.0.0", [])
    assert "0.0.0.0" not in s.allowed_hosts
    assert "::" not in s.allowed_hosts


@check("entry.security.bare_host_and_port_suffix")
def _():
    """Proxy ở cổng mặc định gửi Host KHÔNG kèm ':port' — phải chấp nhận cả hai."""
    s = entry._transport_security("0.0.0.0", ["google-cast.adrec.cloud"])
    assert "google-cast.adrec.cloud" in s.allowed_hosts
    assert "google-cast.adrec.cloud:*" in s.allowed_hosts


@check("entry.security.https_origin_for_tls_proxy")
def _():
    s = entry._transport_security("0.0.0.0", ["google-cast.adrec.cloud"])
    assert "https://google-cast.adrec.cloud" in s.allowed_origins
    assert "http://google-cast.adrec.cloud" in s.allowed_origins


@check("entry.security.loopback_always_allowed")
def _():
    s = entry._transport_security("0.0.0.0", [])
    assert {"127.0.0.1", "localhost", "[::1]"} <= set(s.allowed_hosts)


@check("entry.security.browser_origin_passes_through")
def _():
    s = entry._transport_security("0.0.0.0", [], ["http://192.168.1.99:8383"])
    assert "http://192.168.1.99:8383" in s.allowed_origins


@check("entry.security.explicit_bind_host_allowed")
def _():
    s = entry._transport_security("192.168.1.128", [])
    assert "192.168.1.128" in s.allowed_hosts


# ==========================================================================
# Tầng --online: edge-tts thật, không phát ra loa nào
# ==========================================================================


@check("online.tts.real_render_produces_audio", tier="online")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            p = await tts.synthesize("Cơm đã chín rồi", cache_dir=Path(tmp))
            assert p.stat().st_size > 1000, f"file quá nhỏ: {p.stat().st_size} byte"
            assert is_mp3(p.read_bytes()), p.read_bytes()[:4].hex()

    asyncio.run(run())


@check("online.tts.real_male_voice", tier="online")
def _():
    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            p = await tts.synthesize("Xin chào", voice="male", cache_dir=Path(tmp))
            assert p.stat().st_size > 1000

    asyncio.run(run())


@check("online.tts.real_fanout_six_all_succeed", tier="online")
def _():
    """Bằng chứng bền theo THỜI GIAN và PHẠM VI: đếm khi tmpdir còn sống."""

    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            started = time.monotonic()
            paths = await asyncio.gather(
                *(
                    tts.synthesize(f"Câu số {i}", cache_dir=Path(tmp))
                    for i in range(6)
                ),
                return_exceptions=True,
            )
            elapsed = time.monotonic() - started
            errors = [p for p in paths if isinstance(p, Exception)]
            assert not errors, f"{len(errors)}/6 hỏng: {errors[:1]}"
            ok = [p for p in paths if p.stat().st_size > 1000]
            assert len(ok) == 6, f"chỉ {len(ok)}/6 có audio"
            zero = [p for p in Path(tmp).iterdir() if p.stat().st_size == 0]
            assert not zero, f"đọng file 0 byte: {zero}"
            print(f"      (dồn 6 yêu cầu thật: {elapsed:.1f}s)")

    asyncio.run(run())


@check("online.tts.real_lock_survives_two_loops", tier="online")
def _():
    with tempfile.TemporaryDirectory() as tmp:

        async def contended(tag):
            return await asyncio.gather(
                *(tts.synthesize(f"{tag} {i}", cache_dir=Path(tmp)) for i in range(2))
            )

        first = asyncio.run(contended("vòng một"))
        second = asyncio.run(contended("vòng hai"))
        assert all(p.stat().st_size > 1000 for p in first + second)


@check("online.end_to_end.tts_then_http_fetch", tier="online")
def _():
    """TTS thật → media server thật → tải về thật. Không chạm thiết bị nào."""

    async def run():
        kitchen = FakeCast("Kitchen speaker", "u1", "audio")
        with swapped_server([kitchen]) as (_m, media, _c):
            media._host = "127.0.0.1"
            out = await srv.say("Cơm đã chín rồi", "Kitchen speaker")
            assert out["status"] == "ok"
            with urllib.request.urlopen(out["audio_url"], timeout=10) as resp:
                body = resp.read()
            assert resp.status == 200 and len(body) > 1000, len(body)
            assert is_mp3(body), body[:4].hex()

    asyncio.run(run())


# ==========================================================================
# Tầng --hardware: PHÁT RA TIẾNG THẬT. Chỉ chạy khi đã xin phép.
# ==========================================================================


@check("hardware.say.plays_on_a_real_speaker", tier="hardware")
def _():
    """Bằng chứng bền: content_id khớp URL vừa cast + duration > 0.

    Không được đòi thấy player_state == 'PLAYING': đo được say() mất 5.4s
    trong khi clip chỉ 2.26s, tức lúc say() trả về loa đã phát xong — đòi
    'PLAYING' là đòi một trạng thái đã hết hạn.

    Media server phải còn SỐNG cho tới khi loa tải xong file: dừng nó ngay
    sau say() là cắt nguồn ngay giữa lúc loa đang lấy dữ liệu.
    """

    async def run():
        name = os.environ.get("GOOGLECAST_MCP_TEST_SPEAKER")
        assert name, "đặt GOOGLECAST_MCP_TEST_SPEAKER=<tên loa> trước khi chạy"
        out = await srv.say("Đây là bài kiểm tra", name)
        assert out["status"] == "ok", out
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            status = await asyncio.to_thread(srv._manager.status, name)
            media = status["media"]
            if media.get("content_id") == out["audio_url"] and (media.get("duration") or 0) > 0:
                return
            await asyncio.sleep(1)
        raise AssertionError("loa không hề nhận đúng URL vừa cast trong 30s")

    asyncio.run(run())


# ==========================================================================
# Bộ chạy
# ==========================================================================


def run_checks(tiers: set[str], as_json: bool) -> int:
    registered = [c for c in CHECKS if c[1] in tiers]
    total = len(registered)
    results: list[dict] = []
    ran = 0

    for check_id, tier, fn in registered:
        started = time.monotonic()
        try:
            out = fn()
            if inspect.isawaitable(out):
                asyncio.run(out)
            status, detail = "PASS", ""
        except AssertionError as exc:
            status, detail = "FAIL", str(exc) or "khẳng định sai"
        except Exception:
            # Lỗi hạ tầng là ERROR, không được nuốt thành PASS.
            status, detail = "ERROR", traceback.format_exc(limit=3).strip()
        ran += 1
        results.append(
            {
                "id": check_id,
                "tier": tier,
                "status": status,
                "detail": detail,
                "seconds": round(time.monotonic() - started, 3),
            }
        )
        if not as_json:
            mark = {"PASS": "  ok  ", " ": ""}.get(status, f" {status} ")
            print(f"{mark:>7} {check_id}")
            if detail and status != "PASS":
                for line in detail.splitlines():
                    print(f"         {line}")

    failed = [r for r in results if r["status"] != "PASS"]
    complete = ran == total
    ok = complete and not failed

    if as_json:
        print(
            json.dumps(
                {
                    "registered": total,
                    "ran": ran,
                    "passed": len(results) - len(failed),
                    "complete": complete,
                    "ok": ok,
                    "results": results,
                },
                ensure_ascii=False,
            )
        )
    else:
        print()
        print(f"đã chạy {ran}/{total} mục đăng ký")
        if not complete:
            print("FAIL TOÀN CỤC: chạy thiếu mục — sập giữa chừng không phải là ĐẠT")
        print(f"xanh {len(results) - len(failed)}/{ran}")
        for r in failed:
            print(f"  hỏng: {r['id']} ({r['status']})")
        print("KẾT QUẢ: ĐẠT" if ok else "KẾT QUẢ: KHÔNG ĐẠT")

    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="thêm tầng gọi edge-tts thật")
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="thêm tầng cast thật: PHÁT RA TIẾNG. Xin phép trước khi dùng.",
    )
    parser.add_argument("--json", action="store_true", help="in kết quả dạng JSON")
    args = parser.parse_args()

    tiers = {"offline"}
    if args.online:
        tiers.add("online")
    if args.hardware:
        tiers.add("hardware")
    return run_checks(tiers, args.json)


if __name__ == "__main__":
    sys.exit(main())
