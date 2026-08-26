#!/usr/bin/env python3
"""Eval harness for googlecast-mcp.

Layers
------
offline (default)   no network, no hardware, no side effects outside a temp dir
--online            reaches the edge-tts service on the internet
--hardware          casts real audio to real speakers -- ASK BEFORE RUNNING

Contract this harness holds itself to
-------------------------------------
1. Every registered item calls into product code. An item that no seeded fault
   can turn red is a structural suspect, and reverse-check.py reports it.
2. Items are counted before they are graded. The report prints
   "da chay X/Y muc dang ky"; X < Y is a global FAIL, even if every item that
   did run was green. An infrastructure error is an ERROR, never a silent skip.
3. Expected values are explicit SETS, never sizes. len(a) == len(b) stays green
   while both collapse to one element.
4. Mocks are restored after every item, and a residue guard re-checks the
   originals between items. A leaked patch fails the item that leaked it, not
   some innocent item three layers later.
5. Waiting on async work asserts a durable trace (a file, a recorded call, a
   counter), never a transient state that may already have passed.

Run:
    PYTHONPATH=<repo>/src python eval-googlecast-mcp.py [--online] [--hardware]
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import contextlib
import inspect
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------
# Sandbox the product's on-disk state BEFORE importing it: server.py resolves
# the TTS cache directory at import time.
# --------------------------------------------------------------------------
_SANDBOX = Path(tempfile.mkdtemp(prefix="googlecast-eval-"))
os.environ["GOOGLECAST_MCP_CACHE"] = str(_SANDBOX / "cache")
os.environ["GOOGLECAST_MCP_STORE"] = str(_SANDBOX / "store" / "speakers.json")
os.environ.setdefault("GOOGLECAST_MCP_MEDIA_PORT", "0")

# Root of the product tree, so file-level items (pyproject, scripts) can be
# pointed at a patched copy by reverse-check.py.
PRODUCT_ROOT = Path(
    os.environ.get("GOOGLECAST_MCP_EVAL_ROOT")
    or Path(__file__).resolve().parents[3]
)

import edge_tts  # noqa: E402
from googlecast_mcp import __main__ as entry  # noqa: E402
from googlecast_mcp import cast_manager, media_server, server, speaker_store, tts  # noqa: E402
from googlecast_mcp.cast_manager import CastManager, DeviceNotFoundError  # noqa: E402
from googlecast_mcp.media_server import MediaServer  # noqa: E402
from googlecast_mcp.speaker_store import SpeakerStore  # noqa: E402

# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
REGISTRY: list[dict] = []


def check(item_id: str, layer: str = "offline", desc: str = ""):
    def wrap(fn):
        REGISTRY.append({"id": item_id, "layer": layer, "desc": desc or fn.__doc__ or "", "fn": fn})
        return fn

    return wrap


class CheckFailure(AssertionError):
    pass


def expect_set(actual, expected, what: str) -> None:
    """Compare explicit sets. Never compare sizes -- both can collapse together."""
    a, e = set(actual), set(expected)
    if a != e:
        raise CheckFailure(
            f"{what}: missing={sorted(e - a)!r} unexpected={sorted(a - e)!r}"
        )


def expect_eq(actual, expected, what: str) -> None:
    if actual != expected:
        raise CheckFailure(f"{what}: expected {expected!r}, got {actual!r}")


def expect_true(cond, what: str) -> None:
    if not cond:
        raise CheckFailure(what)


@contextlib.contextmanager
def swap(obj, name: str, value):
    """Replace an attribute and always put the original back."""
    missing = object()
    original = getattr(obj, name, missing)
    setattr(obj, name, value)
    try:
        yield value
    finally:
        if original is missing:
            with contextlib.suppress(AttributeError):
                delattr(obj, name)
        else:
            setattr(obj, name, original)


@contextlib.contextmanager
def swap_item(mapping: dict, key, value):
    """Replace a dict entry (e.g. sys.modules) and always put the original back."""
    missing = object()
    original = mapping.get(key, missing)
    mapping[key] = value
    try:
        yield value
    finally:
        if original is missing:
            mapping.pop(key, None)
        else:
            mapping[key] = original


@contextlib.contextmanager
def fast_backoff(delays: list):
    """Record the retry backoff instead of really sleeping through it.

    The item still proves a growing delay exists -- it just does not spend it.
    """
    real = asyncio.sleep

    async def record(seconds, *a, **k):
        delays.append(seconds)
        return await real(0)

    with swap(asyncio, "sleep", record):
        yield delays


@contextlib.contextmanager
def tmpdir():
    path = Path(tempfile.mkdtemp(prefix="gc-eval-item-", dir=_SANDBOX))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


# --------------------------------------------------------------------------
# Residue guard: identities that no item may leave patched.
# --------------------------------------------------------------------------
_GUARDED = [
    (tts, "synthesize"),
    (tts, "resolve_voice"),
    (tts, "default_cache_dir"),
    (edge_tts, "Communicate"),
    (server, "_manager"),
    (server, "_media_server"),
    (cast_manager, "pychromecast"),
    (media_server, "lan_ip"),
    (asyncio, "sleep"),
    (CastManager, "discover"),
    (CastManager, "list_speakers"),
]
_ORIGINALS = {(id(o), n): getattr(o, n) for o, n in _GUARDED}


def residue_report() -> list[str]:
    leaked = []
    for obj, name in _GUARDED:
        if getattr(obj, name, None) is not _ORIGINALS[(id(obj), name)]:
            leaked.append(f"{getattr(obj, '__name__', obj)}.{name}")
    return leaked


def restore_guarded() -> None:
    for obj, name in _GUARDED:
        setattr(obj, name, _ORIGINALS[(id(obj), name)])


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------
class FakeInfo:
    def __init__(self, name, uuid, cast_type="audio", host="10.0.0.9", port=8009):
        self.friendly_name = name
        self.uuid = uuid
        self.model_name = "Fake Model"
        self.manufacturer = "Fake Corp"
        self.host = host
        self.port = port
        self.cast_type = cast_type


class FakeMediaController:
    def __init__(self):
        self.calls: list[tuple] = []
        self.status = type(
            "S",
            (),
            {
                "player_state": "IDLE",
                "title": None,
                "content_id": None,
                "content_type": None,
                "duration": None,
                "current_time": None,
            },
        )()

    def play_media(self, url, content_type, title=None):
        self.calls.append(("play_media", url, content_type, title))
        self.status.content_id = url
        self.status.content_type = content_type
        self.status.player_state = "PLAYING"

    def block_until_active(self, timeout=10):
        self.calls.append(("block_until_active", timeout))

    def play(self):
        self.calls.append(("play",))

    def pause(self):
        self.calls.append(("pause",))

    def stop(self):
        self.calls.append(("stop",))

    def seek(self, pos):
        self.calls.append(("seek", pos))


class FakeCast:
    def __init__(self, name="Kitchen speaker", uuid="11111111-1111-1111-1111-111111111111",
                 cast_type="audio"):
        self.cast_info = FakeInfo(name, uuid, cast_type)
        self.media_controller = FakeMediaController()
        self.status = type(
            "C", (), {"display_name": "Default Media Receiver", "app_id": "CC1AD845",
                      "is_active_input": None, "volume_level": 0.5, "volume_muted": False}
        )()
        self.volume_calls: list = []
        self.muted_calls: list = []
        self.quit_calls = 0
        self.waited = 0

    def wait(self, timeout=10):
        self.waited += 1

    def set_volume(self, level):
        self.volume_calls.append(level)

    def set_volume_muted(self, muted):
        self.muted_calls.append(muted)

    def quit_app(self):
        self.quit_calls += 1

    def disconnect(self, blocking=False):
        pass


class RecordingManager:
    """Stands in for CastManager inside server-level items."""

    def __init__(self, speakers: list[dict], fail_for: set[str] | None = None):
        self._speakers = speakers
        self._fail_for = fail_for or set()
        self.play_calls: list[tuple] = []
        self.discover_calls = 0

    def list_speakers(self):
        return list(self._speakers)

    def list_cached(self):
        return list(self._speakers)

    def discover(self, timeout=5.0):
        self.discover_calls += 1
        return list(self._speakers)

    def play_media(self, name, url, content_type=None, title=None):
        if name in self._fail_for:
            raise RuntimeError(f"Execution of wait timed out after 10 s ({name})")
        self.play_calls.append((name, url, content_type, title))
        return {"ok": True}


class FakeMediaServerStub:
    def __init__(self, url="http://10.0.0.1:8766/fake.mp3"):
        self._url = url
        self.calls: list[Path] = []

    def url_for(self, path):
        self.calls.append(path)
        return self._url

    def stop(self):
        pass


def fake_communicate_factory(behaviour="ok", concurrency=None, attempts=None,
                             payload=b"ID3fake-audio-bytes" + b"\x00" * 64):
    """Build a stand-in for edge_tts.Communicate.

    behaviour:
      "ok"        write payload
      "raise"     create a zero-byte file, then raise (the real failure mode)
      "empty"     create a zero-byte file and return without raising
      "flaky:N"   raise for the first N attempts, then succeed
    """
    state = {"n": 0, "live": 0, "max_live": 0}

    class Fake:
        def __init__(self, text, voice, rate="+0%", volume="+0%"):
            self.text, self.voice, self.rate, self.volume = text, voice, rate, volume

        async def save(self, path):
            state["n"] += 1
            if attempts is not None:
                attempts.append((self.text, self.voice, self.rate))
            state["live"] += 1
            state["max_live"] = max(state["max_live"], state["live"])
            try:
                await asyncio.sleep(0.02)
                mode = behaviour
                if behaviour.startswith("flaky:"):
                    limit = int(behaviour.split(":", 1)[1])
                    mode = "raise" if state["n"] <= limit else "ok"
                if mode == "ok":
                    Path(path).write_bytes(payload)
                elif mode == "raise":
                    Path(path).write_bytes(b"")
                    raise RuntimeError("Cannot connect to host speech.platform.bing.com")
                elif mode == "empty":
                    Path(path).write_bytes(b"")
            finally:
                state["live"] -= 1

    if concurrency is not None:
        concurrency.append(state)
    Fake.state = state
    return Fake


SPEAKERS = [
    {"friendly_name": "Kitchen speaker", "uuid": "u-kitchen", "cast_type": "audio",
     "host": "192.168.1.22", "port": 8009, "model_name": "Google Home"},
    {"friendly_name": "Bedroom speaker", "uuid": "u-bedroom", "cast_type": "audio",
     "host": "192.168.1.23", "port": 8009, "model_name": "Google Home Mini"},
    {"friendly_name": "Family speaker group", "uuid": "u-group", "cast_type": "group",
     "host": "192.168.1.22", "port": 8009, "model_name": "Google Cast Group"},
]
VIDEO_DEVICE = {"friendly_name": "Working display", "uuid": "u-hub", "cast_type": "cast",
                "host": "192.168.1.30", "port": 8009, "model_name": "Nest Hub"}


# ==========================================================================
# speaker_store
# ==========================================================================
@check("store.is_speaker", desc="audio and group are speakers; video casts are not")
def _():
    cases = {
        ("audio",): True,
        ("group",): True,
        ("cast",): False,
        ("cast_lite",): False,
    }
    for (cast_type,), expected in cases.items():
        expect_eq(speaker_store.is_speaker({"cast_type": cast_type}), expected,
                  f"is_speaker(cast_type={cast_type!r})")
    expect_eq(speaker_store.is_speaker({}), False, "is_speaker({}) with no cast_type")
    expect_eq(speaker_store.is_speaker({"cast_type": None}), False, "is_speaker(None)")


@check("store.merge_keeps_missed", desc="a device missed by one scan survives the next save")
def _():
    with tmpdir() as d:
        store = SpeakerStore(d / "s.json")
        store.save(SPEAKERS)
        store.save([VIDEO_DEVICE])  # a later scan that saw only the hub
        expect_set([x["uuid"] for x in store.load()],
                   {"u-kitchen", "u-bedroom", "u-group", "u-hub"},
                   "uuids after a partial second scan")


@check("store.merge_updates_fields", desc="a re-saved device keeps old fields and takes new ones")
def _():
    with tmpdir() as d:
        store = SpeakerStore(d / "s.json")
        store.save([{"uuid": "u-kitchen", "friendly_name": "Kitchen speaker",
                     "host": "192.168.1.22", "cast_type": "audio"}])
        store.save([{"uuid": "u-kitchen", "host": "192.168.1.77"}])
        got = {d_["uuid"]: d_ for d_ in store.load()}["u-kitchen"]
        expect_eq(got["host"], "192.168.1.77", "host after re-save")
        expect_eq(got["friendly_name"], "Kitchen speaker", "friendly_name preserved")


@check("store.speakers_filter", desc="speakers() drops video casts by name")
def _():
    with tmpdir() as d:
        store = SpeakerStore(d / "s.json")
        store.save(SPEAKERS + [VIDEO_DEVICE])
        expect_set([s["friendly_name"] for s in store.speakers()],
                   {"Kitchen speaker", "Bedroom speaker", "Family speaker group"},
                   "speakers() result")


@check("store.corrupt_json", desc="a truncated store reads as empty, not as a crash")
def _():
    with tmpdir() as d:
        path = d / "s.json"
        path.write_text('{"devices": [{"uuid": "u-a"', encoding="utf-8")
        expect_eq(SpeakerStore(path).load(), [], "load() of a truncated file")
        expect_eq(SpeakerStore(d / "absent.json").load(), [], "load() of a missing file")


@check("store.path_env", desc="GOOGLECAST_MCP_STORE overrides the store location")
def _():
    with tmpdir() as d:
        with swap(os.environ, "GOOGLECAST_MCP_STORE", str(d / "custom.json")):
            os.environ["GOOGLECAST_MCP_STORE"] = str(d / "custom.json")
            expect_eq(speaker_store.default_store_path(), d / "custom.json",
                      "default_store_path with the env var set")


# ==========================================================================
# cast_manager
# ==========================================================================
@check("cast.guess_content_type", desc="MIME table maps extensions; unknown falls back to video/mp4")
def _():
    expected = {
        "http://h/a.mp3": "audio/mpeg",
        "http://h/a.m4a": "audio/mp4",
        "http://h/a.flac": "audio/flac",
        "http://h/a.wav": "audio/wav",
        "http://h/a.ogg": "audio/ogg",
        "http://h/a.aac": "audio/aac",
        "http://h/v.mp4": "video/mp4",
        "http://h/v.webm": "video/webm",
        "http://h/v.mkv": "video/x-matroska",
        "http://h/p.jpg": "image/jpeg",
        "http://h/p.png": "image/png",
        "http://h/s.m3u8": "application/x-mpegURL",
        "http://h/stream": "video/mp4",
    }
    got = {url: cast_manager._guess_content_type(url) for url in expected}
    expect_set(got.items(), expected.items(), "content-type table")
    expect_eq(cast_manager._guess_content_type("http://h/a.MP3"), "audio/mpeg",
              "uppercase extension")
    expect_eq(cast_manager._guess_content_type("http://h/a.mp3?token=1"), "audio/mpeg",
              "extension behind a query string")


@check("cast.volume_clamped", desc="set_volume clamps to 0.0-1.0 and reports what it applied")
def _():
    fake = FakeCast()
    mgr = CastManager(SpeakerStore(_SANDBOX / "unused.json"))
    mgr._connected = lambda t: fake  # only the lookup is stubbed; the logic is real
    expected = [(2.0, 1.0), (-1.0, 0.0), (0.35, 0.35), (0.0, 0.0), (1.0, 1.0)]
    for asked, want in expected:
        expect_eq(mgr.set_volume("Kitchen speaker", asked), want, f"set_volume({asked}) return")
    expect_eq(fake.volume_calls, [w for _a, w in expected], "levels handed to the device")


@check("cast.resolve_error_lists_known", desc="an unknown device names the ones that are known")
def _():
    with tmpdir() as d:
        store = SpeakerStore(d / "s.json")
        store.save(SPEAKERS)
        mgr = CastManager(store)
        mgr._connect_saved = lambda t: None
        mgr.discover = lambda timeout=5.0: []
        try:
            mgr._resolve("Ghost speaker")
        except DeviceNotFoundError as exc:
            message = str(exc)
        else:
            raise CheckFailure("_resolve did not raise DeviceNotFoundError")
        for name in ("Kitchen speaker", "Bedroom speaker", "Family speaker group"):
            expect_true(name in message, f"error message should name {name!r}: {message!r}")


@check("cast.resolve_locally", desc="live cache matches uuid and friendly name, case-insensitively")
def _():
    mgr = CastManager(SpeakerStore(_SANDBOX / "unused.json"))
    fake = FakeCast("Kitchen speaker", "AAAA-BBBB")
    mgr._devices["AAAA-BBBB"] = fake
    for probe in ("AAAA-BBBB", "aaaa-bbbb", "Kitchen speaker", "  kitchen SPEAKER "):
        expect_true(mgr._resolve_locally(probe) is fake, f"lookup by {probe!r}")
    expect_true(mgr._resolve_locally("Nobody") is None, "lookup of an unknown name")


@check("cast.status_shape", desc="status() reports the device, app and media blocks")
def _():
    fake = FakeCast()
    mgr = CastManager(SpeakerStore(_SANDBOX / "unused.json"))
    mgr._connected = lambda t: fake
    status = mgr.status("Kitchen speaker")
    expect_set(status.keys(), {"device", "app", "media"}, "status top-level keys")
    expect_set(status["media"].keys(),
               {"player_state", "title", "content_id", "content_type", "duration", "current_time"},
               "media keys")
    expect_set(status["device"].keys(),
               {"friendly_name", "uuid", "model_name", "manufacturer", "host", "port", "cast_type"},
               "device keys")
    expect_eq(status["device"]["friendly_name"], "Kitchen speaker", "device name")


@check("cast.play_media_guesses_mime", desc="play_media fills in the MIME type when none is given")
def _():
    fake = FakeCast()
    mgr = CastManager(SpeakerStore(_SANDBOX / "unused.json"))
    mgr._connected = lambda t: fake
    mgr.play_media("Kitchen speaker", "http://10.0.0.1:8766/abc.mp3", None, "hello")
    played = [c for c in fake.media_controller.calls if c[0] == "play_media"]
    expect_eq(len(played), 1, "one play_media call")
    expect_eq(played[0][2], "audio/mpeg", "guessed content type for an .mp3 url")
    expect_true(("block_until_active", 10) in fake.media_controller.calls,
                "play_media must wait for the receiver to become active")


@check("cast.play_media_explicit_mime", desc="an explicit MIME type is passed through untouched")
def _():
    fake = FakeCast()
    mgr = CastManager(SpeakerStore(_SANDBOX / "unused.json"))
    mgr._connected = lambda t: fake
    mgr.play_media("Kitchen speaker", "http://10.0.0.1:8766/stream", "application/x-mpegURL", None)
    played = [c for c in fake.media_controller.calls if c[0] == "play_media"][0]
    expect_eq(played[2], "application/x-mpegURL", "explicit content type")


@check("cast.controls_reach_device", desc="play/pause/stop/seek/mute/quit reach the device object")
def _():
    fake = FakeCast()
    mgr = CastManager(SpeakerStore(_SANDBOX / "unused.json"))
    mgr._connected = lambda t: fake
    mgr.play("k"); mgr.pause("k"); mgr.stop("k"); mgr.seek("k", 12.5)
    mgr.set_muted("k", True); mgr.quit_app("k")
    expect_set([c[0] for c in fake.media_controller.calls],
               {"play", "pause", "stop", "seek"}, "media controller verbs")
    expect_true(("seek", 12.5) in fake.media_controller.calls, "seek position forwarded")
    expect_eq(fake.muted_calls, [True], "mute forwarded")
    expect_eq(fake.quit_calls, 1, "quit_app forwarded")


# ==========================================================================
# media_server
# ==========================================================================
@check("media.binds_wildcard_advertises_lan",
       desc="listen on 0.0.0.0 but advertise the address the speaker can reach")
def _():
    with tmpdir() as d:
        (d / "hello.mp3").write_bytes(b"x")
        srv = MediaServer(d, host="192.168.1.128", port=8798)
        try:
            url = srv.url_for(d / "hello.mp3")
            expect_eq(url, "http://192.168.1.128:8798/hello.mp3", "advertised URL")
            expect_eq(srv._httpd.server_address[0], "0.0.0.0",
                      "bind address (must not follow the advertised host)")
        finally:
            srv.stop()


@check("media.quotes_filenames", desc="a name needing escaping produces a usable URL")
def _():
    with tmpdir() as d:
        name = "ban tin.mp3"
        (d / name).write_bytes(b"x")
        srv = MediaServer(d, host="10.1.1.1", port=0)
        try:
            expect_true(srv.url_for(d / name).endswith("/ban%20tin.mp3"),
                        f"URL should percent-escape the space: {srv.url_for(d / name)!r}")
        finally:
            srv.stop()


@check("media.serves_bytes", desc="the speaker's fetch really returns the file (durable evidence)")
def _():
    with tmpdir() as d:
        payload = b"ID3" + bytes(range(256)) * 4
        (d / "clip.mp3").write_bytes(payload)
        srv = MediaServer(d, host="127.0.0.1", port=8799)
        try:
            url = srv.url_for(d / "clip.mp3")
            with urllib.request.urlopen(url, timeout=10) as resp:
                body = resp.read()
                code = resp.status
            expect_eq(code, 200, "HTTP status for the audio fetch")
            expect_eq(body, payload, "bytes returned to the speaker")
        finally:
            srv.stop()


@check("media.port_pin_before_start", desc="the port cannot be re-pinned once clients rely on it")
def _():
    with tmpdir() as d:
        srv = MediaServer(d, host="127.0.0.1", port=0)
        try:
            srv.set_port(8799)
            expect_eq(srv.port, 8799, "port before start reflects the pin")
            srv.start()
            try:
                srv.set_port(9000)
            except RuntimeError:
                pass
            else:
                raise CheckFailure("set_port must refuse while the server is running")
        finally:
            srv.stop()


@check("media.stop_is_idempotent", desc="stop() twice is safe and frees the port")
def _():
    with tmpdir() as d:
        srv = MediaServer(d, host="127.0.0.1", port=8799)
        srv.start()
        srv.stop()
        srv.stop()
        again = MediaServer(d, host="127.0.0.1", port=8799)
        try:
            again.start()  # would raise "address in use" if the port leaked
        finally:
            again.stop()


# ==========================================================================
# tts
# ==========================================================================
@check("tts.resolve_voice", desc="female/male aliases, full ids, and the default")
def _():
    expected = {
        "female": "vi-VN-HoaiMyNeural",
        "male": "vi-VN-NamMinhNeural",
        "  MALE  ": "vi-VN-NamMinhNeural",
        "en-US-AriaNeural": "en-US-AriaNeural",
    }
    got = {k: tts.resolve_voice(k) for k in expected}
    expect_set(got.items(), expected.items(), "voice resolution table")
    expect_eq(tts.resolve_voice(None), "vi-VN-HoaiMyNeural", "default voice")
    expect_eq(tts.resolve_voice(""), "vi-VN-HoaiMyNeural", "empty voice falls back to default")


@check("tts.cache_dir_env", desc="GOOGLECAST_MCP_CACHE redirects the cache and creates it")
def _():
    with tmpdir() as d:
        wanted = d / "nested" / "cache"
        with swap(os.environ, "GOOGLECAST_MCP_CACHE", str(wanted)):
            os.environ["GOOGLECAST_MCP_CACHE"] = str(wanted)
            expect_eq(tts.default_cache_dir(), wanted, "cache dir from the env var")
            expect_true(wanted.is_dir(), "cache dir is created")


@check("tts.empty_text_rejected", desc="empty or blank text is refused before any network call")
async def _():
    with tmpdir() as d:
        called = []
        with swap(edge_tts, "Communicate", fake_communicate_factory(attempts=called)):
            for bad in ("", "   ", "\n\t"):
                try:
                    await tts.synthesize(bad, cache_dir=d)
                except ValueError:
                    continue
                raise CheckFailure(f"synthesize({bad!r}) should raise ValueError")
        expect_eq(called, [], "no synthesis attempt may be made for empty text")


@check("tts.cache_hit_skips_service", desc="a second render of the same text never calls the service")
async def _():
    with tmpdir() as d:
        first_calls: list = []
        with swap(edge_tts, "Communicate", fake_communicate_factory(attempts=first_calls)):
            path = await tts.synthesize("Cơm đã chín rồi", voice="female", cache_dir=d)
        expect_eq(len(first_calls), 1, "first render calls the service once")
        expect_true(path.exists() and path.stat().st_size > 0, "first render wrote audio")

        def boom(*a, **k):
            raise CheckFailure("cache hit must not construct a synthesis request")

        with swap(edge_tts, "Communicate", boom):
            again = await tts.synthesize("Cơm đã chín rồi", voice="female", cache_dir=d)
        expect_eq(again, path, "cached path returned")


@check("tts.distinct_voice_distinct_file", desc="voice and rate are part of the cache key")
async def _():
    with tmpdir() as d:
        with swap(edge_tts, "Communicate", fake_communicate_factory()):
            a = await tts.synthesize("xin chào", voice="female", cache_dir=d)
            b = await tts.synthesize("xin chào", voice="male", cache_dir=d)
            c = await tts.synthesize("xin chào", voice="female", rate="-20%", cache_dir=d)
    expect_eq(len({a, b, c}), 3, f"three distinct cache files, got {sorted({a.name, b.name, c.name})}")


@check("tts.retries_then_succeeds", desc="a transient refusal is retried, not surfaced")
async def _():
    with tmpdir() as d:
        calls: list = []
        delays: list = []
        with fast_backoff(delays), \
                swap(edge_tts, "Communicate", fake_communicate_factory("flaky:2", attempts=calls)):
            path = await tts.synthesize("thử lại", cache_dir=d)
        expect_eq(len(calls), 3, "two failures then one success")
        # 0.02 entries come from the stand-in's own await; the product's own
        # backoff is what matters here.
        expect_eq([d for d in delays if d >= 1], [2, 4],
                  "growing backoff between retry attempts")
        expect_true(path.stat().st_size > 0, "the recovered render is not empty")


@check("tts.no_zero_byte_residue", desc="a total failure raises and leaves no empty mp3 behind")
async def _():
    with tmpdir() as d:
        calls: list = []
        with fast_backoff([]), \
                swap(edge_tts, "Communicate", fake_communicate_factory("raise", attempts=calls)):
            try:
                await tts.synthesize("hỏng hẳn", cache_dir=d)
            except RuntimeError as exc:
                expect_true("3 attempts" in str(exc), f"error should mention the retries: {exc}")
            else:
                raise CheckFailure("synthesize must raise when every attempt fails")
        expect_eq(len(calls), 3, "three attempts were made")
        leftovers = [p.name for p in d.glob("*.mp3")]
        expect_set(leftovers, set(), "mp3 files left behind after a total failure")


@check("tts.empty_render_is_failure", desc="a save that writes nothing counts as a failure")
async def _():
    with tmpdir() as d:
        with fast_backoff([]), swap(edge_tts, "Communicate", fake_communicate_factory("empty")):
            try:
                await tts.synthesize("im lặng", cache_dir=d)
            except RuntimeError:
                pass
            else:
                raise CheckFailure("a zero-byte render must not be returned as success")
        expect_set([p.name for p in d.glob("*.mp3")], set(), "no empty file kept")


@check("tts.renders_are_serialised",
       desc="a fan-out of announcements renders one at a time and all of them survive")
async def _():
    with tmpdir() as d:
        probe: list = []
        fake = fake_communicate_factory(concurrency=probe)
        texts = [f"thông báo số {i}" for i in range(6)]
        with swap(edge_tts, "Communicate", fake):
            paths = await asyncio.gather(*(tts.synthesize(t, cache_dir=d) for t in texts))
        state = probe[0]
        expect_eq(state["max_live"], 1,
                  "concurrent renders in flight (retrying alone does not fix an overlap)")
        expect_eq(len(set(paths)), 6, "six distinct renders")
        for p in paths:
            expect_true(p.exists() and p.stat().st_size > 0, f"{p.name} is a real file")


# ==========================================================================
# server: target selection
# ==========================================================================
@check("server.no_target_asks", desc="omitting the target plays nothing and returns the speaker list")
async def _():
    manager = RecordingManager(SPEAKERS)
    with swap(server, "_manager", manager):
        names, prompt = await server._select_targets(None)
    expect_eq(names, [], "no speaker is selected")
    expect_eq(prompt["status"], "needs_speaker_selection", "prompt status")
    expect_set([s["friendly_name"] for s in prompt["speakers"]],
               {"Kitchen speaker", "Bedroom speaker", "Family speaker group"},
               "speakers offered to the user")
    expect_eq(manager.play_calls, [], "nothing may be cast")


@check("server.no_speakers_found", desc="an empty network says so instead of asking to pick")
async def _():
    manager = RecordingManager([])
    with swap(server, "_manager", manager):
        names, prompt = await server._select_targets(None)
    expect_eq(names, [], "no speaker selected")
    expect_eq(prompt["status"], "no_speakers_found", "prompt status on an empty network")
    expect_true(manager.discover_calls >= 1, "an empty list triggers a scan first")


@check("server.all_excludes_groups",
       desc="'all' skips speaker groups so no physical speaker gets two streams")
async def _():
    manager = RecordingManager(SPEAKERS)
    for keyword in ("all", "tất cả", "ALL", " everyone "):
        with swap(server, "_manager", manager):
            names, prompt = await server._select_targets(keyword)
        expect_eq(prompt, None, f"{keyword!r} needs no prompt")
        expect_set(names, {"Kitchen speaker", "Bedroom speaker"},
                   f"speakers chosen by {keyword!r} (the group must be excluded)")


@check("server.comma_list", desc="several speakers may be named at once")
async def _():
    manager = RecordingManager(SPEAKERS)
    with swap(server, "_manager", manager):
        names, prompt = await server._select_targets("  Kitchen speaker , Bedroom speaker ,, ")
    expect_eq(prompt, None, "an explicit list needs no prompt")
    expect_set(names, {"Kitchen speaker", "Bedroom speaker"}, "parsed names")


@check("server.group_by_name_still_reachable", desc="naming a group directly still works")
async def _():
    manager = RecordingManager(SPEAKERS)
    with swap(server, "_manager", manager):
        names, _ = await server._select_targets("Family speaker group")
    expect_set(names, {"Family speaker group"}, "an explicitly named group")


# ==========================================================================
# server: say()
# ==========================================================================
@contextlib.contextmanager
def say_environment(speakers, fail_for=None, url="http://192.168.1.128:8766/clip.mp3"):
    manager = RecordingManager(speakers, fail_for)
    stub = FakeMediaServerStub(url)
    fake = fake_communicate_factory()
    with swap(server, "_manager", manager), swap(server, "_media_server", stub), \
            swap(edge_tts, "Communicate", fake):
        yield manager, stub


@check("say.without_target_plays_nothing", desc="say() with no target casts nothing at all")
async def _():
    with say_environment(SPEAKERS) as (manager, stub):
        result = await server.say("Cơm đã chín rồi")
    expect_eq(result["status"], "needs_speaker_selection", "say() result status")
    expect_eq(manager.play_calls, [], "no cast may happen")
    expect_eq(stub.calls, [], "no audio may even be published")


@check("say.casts_audio_mpeg",
       desc="requirement 2: the rendered speech is cast to the speaker as mp3 audio")
async def _():
    with say_environment(SPEAKERS) as (manager, stub):
        result = await server.say("Cơm đã chín rồi", "Kitchen speaker")
    expect_eq(result["status"], "ok", "say() overall status")
    expect_eq(len(manager.play_calls), 1, "one cast")
    name, url, content_type, title = manager.play_calls[0]
    expect_eq(name, "Kitchen speaker", "speaker cast to")
    expect_eq(url, "http://192.168.1.128:8766/clip.mp3", "URL handed to the speaker")
    # server.py:134 hands "audio/mpeg" straight to play_media rather than going
    # through cast_manager._guess_content_type. The expectation follows the
    # requirement (speech must arrive as mp3 audio), not the table.
    expect_eq(content_type, "audio/mpeg", "MIME type for synthesized speech")
    expect_eq(title, "Cơm đã chín rồi", "title shown on the device")
    expect_eq(len(stub.calls), 1, "the audio file was published exactly once")


@check("say.reports_resolved_voice", desc="say() echoes the real voice id it used")
async def _():
    with say_environment(SPEAKERS) as (manager, _stub):
        result = await server.say("xin chào", "Kitchen speaker", voice="male")
    expect_eq(result["voice"], "vi-VN-NamMinhNeural", "resolved voice in the reply")


@check("say.one_bad_speaker_does_not_sink_the_rest",
       desc="a dead speaker is reported per-speaker; the live one still gets its audio")
async def _():
    with say_environment(SPEAKERS, fail_for={"Ghost speaker"}) as (manager, _stub):
        result = await server.say("Cơm đã chín rồi", "Kitchen speaker, Ghost speaker")
    expect_eq(result["status"], "ok", "one live speaker keeps the call successful")
    by_name = {r["speaker"]: r for r in result["results"]}
    expect_set(by_name.keys(), {"Kitchen speaker", "Ghost speaker"}, "per-speaker results")
    expect_eq(by_name["Kitchen speaker"]["status"], "playing", "the live speaker")
    expect_eq(by_name["Ghost speaker"]["status"], "error", "the dead speaker")
    # Durable evidence: the recorded cast, not a transient player state that
    # may already have finished by the time we look.
    expect_set([c[0] for c in manager.play_calls], {"Kitchen speaker"}, "speakers actually cast to")


@check("say.every_speaker_failing_is_a_failure", desc="say() reports failure when nothing played")
async def _():
    with say_environment(SPEAKERS, fail_for={"Kitchen speaker", "Bedroom speaker"}) as (mgr, _s):
        result = await server.say("Cơm đã chín rồi", "Kitchen speaker, Bedroom speaker")
    expect_eq(result["status"], "failed", "status when no speaker played")
    expect_eq(mgr.play_calls, [], "nothing was cast")
    expect_set([r["status"] for r in result["results"]], {"error"}, "per-speaker statuses")


@check("say.all_casts_once_per_speaker", desc="'all' casts to each speaker exactly once")
async def _():
    with say_environment(SPEAKERS) as (manager, _stub):
        result = await server.say("Cơm đã chín rồi", "all")
    expect_eq(result["status"], "ok", "say(all) status")
    expect_set([c[0] for c in manager.play_calls], {"Kitchen speaker", "Bedroom speaker"},
               "speakers cast to for 'all'")
    expect_eq(len(manager.play_calls), 2, "no speaker may be cast to twice")


# ==========================================================================
# server: tool surface
# ==========================================================================
EXPECTED_TOOLS = {
    "say", "discover_devices", "list_speakers", "list_devices", "get_status",
    "play_media", "play", "pause", "stop", "seek", "set_volume", "set_muted", "quit_app",
}


@check("server.tool_surface", desc="the MCP client sees exactly the 13 documented tools")
async def _():
    tools = await server.mcp.list_tools()
    expect_set([t.name for t in tools], EXPECTED_TOOLS, "tools advertised over MCP")


@check("server.say_schema", desc="say()'s target is optional and its text is required")
async def _():
    tools = {t.name: t for t in await server.mcp.list_tools()}
    schema = tools["say"].inputSchema
    expect_set(schema.get("required", []), {"text"}, "required arguments of say()")
    expect_set(schema["properties"].keys(), {"text", "target", "voice", "rate"},
               "arguments of say()")


# ==========================================================================
# __main__: transport security and CORS
# ==========================================================================
@check("entry.trusts_lan_and_proxy_domain",
       desc="a remote client and a TLS proxy are trusted; a wildcard bind is not an address")
def _():
    with swap(media_server, "lan_ip", lambda: "192.168.1.128"), \
            swap(entry, "lan_ip", lambda: "192.168.1.128"):
        settings = entry._transport_security("0.0.0.0", ["google-cast.adrec.cloud"], [])
    hosts = set(settings.allowed_hosts)
    for wanted in ("192.168.1.128", "192.168.1.128:*", "google-cast.adrec.cloud",
                   "google-cast.adrec.cloud:*", "127.0.0.1", "localhost"):
        expect_true(wanted in hosts, f"allowed_hosts must contain {wanted!r}: {sorted(hosts)}")
    for unwanted in ("0.0.0.0", "0.0.0.0:*"):
        expect_true(unwanted not in hosts, f"a wildcard bind is not a Host clients send: {unwanted!r}")
    origins = set(settings.allowed_origins)
    expect_true("https://google-cast.adrec.cloud" in origins,
                "the https origin of the proxied domain must be allowed")
    expect_true("http://192.168.1.128:*" in origins, "LAN origins with a port must be allowed")


@check("entry.browser_origin_passthrough", desc="a browser client's origin is allowed verbatim")
def _():
    with swap(media_server, "lan_ip", lambda: "192.168.1.128"), \
            swap(entry, "lan_ip", lambda: "192.168.1.128"):
        settings = entry._transport_security("0.0.0.0", [], ["http://192.168.1.99:8383"])
    expect_true("http://192.168.1.99:8383" in set(settings.allowed_origins),
                "the exact browser origin must be allowed")


@check("entry.cors_exposes_session_header",
       desc="a browser cannot continue a session unless Mcp-Session-Id is exposed")
def _():
    captured: dict = {}

    class FakeUvicorn:
        @staticmethod
        def run(app, host=None, port=None, log_level=None):
            captured["app"] = app

    with swap_item(sys.modules, "uvicorn", FakeUvicorn):
        entry._run_with_cors(["http://192.168.1.99:8383"])
    app = captured.get("app")
    expect_true(app is not None, "the CORS path must start the streamable-HTTP app")
    cors = [m for m in app.user_middleware if "CORS" in m.cls.__name__]
    expect_eq(len(cors), 1, "exactly one CORS middleware")
    kwargs = cors[0].kwargs
    expect_true(any(h.lower() == "mcp-session-id" for h in kwargs.get("expose_headers", [])),
                f"expose_headers must include Mcp-Session-Id: {kwargs.get('expose_headers')!r}")
    expect_set(kwargs.get("allow_origins", []), {"http://192.168.1.99:8383"}, "allowed origins")
    expect_true("OPTIONS" in kwargs.get("allow_methods", []),
                "the preflight method must be allowed, or the browser reports only 'Failed to fetch'")


# ==========================================================================
# Shipped artefacts (product files, not just product code)
# ==========================================================================
@check("ship.mcp_pin", desc="the SDK stays below the unrelated 'mcp' 2.0.0 on PyPI")
def _():
    text = (PRODUCT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    expect_true('"mcp[cli]>=1.13,<2"' in text,
                "pyproject must pin mcp[cli]>=1.13,<2 (2.0.0 is a different package)")


@check("ship.service_restarts", desc="installing over a running service must replace the process")
def _():
    text = (PRODUCT_ROOT / "scripts" / "service.sh").read_text(encoding="utf-8")
    expect_true("systemctl restart" in text,
                "install must restart explicitly; 'enable --now' leaves the old process running")
    for verb in ("install", "remove", "start", "stop", "restart", "status", "logs"):
        expect_true(f"{verb})" in text, f"service.sh must handle '{verb}'")
    expect_true("/proc/$pid/cmdline" in text,
                "status must print the command line the process actually runs")


@check("ship.nginx_no_buffering", desc="a buffering proxy makes the client hang with no error")
def _():
    text = (PRODUCT_ROOT / "scripts" / "nginx-googlecast-mcp.conf").read_text(encoding="utf-8")
    expect_true("proxy_buffering off" in text, "proxy_buffering must be off")
    expect_true("proxy_read_timeout" in text, "the streaming response needs a long read timeout")


# ==========================================================================
# --online layer
# ==========================================================================
@check("online.real_render", layer="online", desc="edge-tts really returns Vietnamese mp3 audio")
async def _():
    with tmpdir() as d:
        path = await tts.synthesize("Cơm đã chín rồi", voice="female", cache_dir=d)
        data = path.read_bytes()
    expect_true(len(data) > 2000, f"a real render should be more than 2 kB, got {len(data)}")
    expect_true(data[:3] == b"ID3" or data[0] == 0xFF, f"not mp3 framing: {data[:4]!r}")


@check("online.voices_differ", layer="online", desc="the male and female voices are really different")
async def _():
    with tmpdir() as d:
        female = (await tts.synthesize("xin chào buổi sáng", voice="female", cache_dir=d)).read_bytes()
        male = (await tts.synthesize("xin chào buổi sáng", voice="male", cache_dir=d)).read_bytes()
    expect_true(female != male, "female and male renders must not be byte-identical")
    expect_true(len(male) > 2000, "the male render is real audio")


@check("online.fanout_all_survive", layer="online",
       desc="six announcements at once all render (the failure the lock was added for)")
async def _():
    with tmpdir() as d:
        texts = [f"thông báo số {i}" for i in range(6)]
        started = time.monotonic()
        paths = await asyncio.gather(*(tts.synthesize(t, cache_dir=d) for t in texts))
        elapsed = time.monotonic() - started
        # Inside the block on purpose: the evidence is the files on disk, and
        # the temp directory is gone the moment this block ends.
        good = [p for p in paths if p.exists() and p.stat().st_size > 0]
        expect_eq(len(good), 6, f"renders that produced audio (took {elapsed:.1f}s)")
        expect_set([p.name for p in d.glob("*.mp3") if p.stat().st_size == 0], set(),
                   "zero-byte files left behind")
        print(f"      fan-out of 6 finished in {elapsed:.1f}s")


# ==========================================================================
# --hardware layer  (casts audible sound: ask the user first)
# ==========================================================================
@check("hardware.discovers_speakers", layer="hardware", desc="mDNS finds at least one speaker")
def _():
    mgr = CastManager()
    try:
        mgr.discover(8.0)
        speakers = mgr.list_speakers()
        expect_true(len(speakers) >= 1, "no speaker answered mDNS")
        print("      speakers: " + ", ".join(s["friendly_name"] for s in speakers))
    finally:
        mgr.close()


@check("hardware.say_leaves_durable_trace", layer="hardware",
       desc="the speaker really fetched and played the announcement")
async def _():
    # Deliberately query through the SAME manager that cast: media status is
    # per-connection, and a second connection reports UNKNOWN forever. Assert a
    # trace that survives playback finishing (content_id + duration), not a
    # transient PLAYING that a short clip may already have left.
    manager = CastManager()
    # The module-level media server was built for the cache directory that
    # existed at import time, while each item runs against its own cache.
    # Swapping only the manager leaves url_for() looking at the wrong
    # directory, which fails as an opaque ValueError. Give this tier its own
    # media server, pointed at the cache actually in use — and keep it alive
    # until the check ends, since the speaker fetches the audio from it.
    media_srv = media_server.MediaServer(tts.default_cache_dir())
    try:
        speakers = await asyncio.to_thread(manager.list_speakers)
        if not speakers:
            await asyncio.to_thread(manager.discover, 8.0)
            speakers = await asyncio.to_thread(manager.list_speakers)
        expect_true(bool(speakers), "no speaker to cast to")
        name = next(s["friendly_name"] for s in speakers if s["cast_type"] != "group")
        with swap(server, "_manager", manager), swap(server, "_media_server", media_srv):
            result = await server.say("Đây là bài kiểm tra tự động", name)
        expect_eq(result["status"], "ok", f"say() to {name}: {result}")
        audio_url = result["audio_url"]
        deadline = time.monotonic() + 30
        seen = None
        while time.monotonic() < deadline:
            seen = await asyncio.to_thread(manager.status, name)
            media = seen["media"]
            if media.get("content_id") == audio_url and (media.get("duration") or 0) > 0:
                print(f"      {name}: duration={media['duration']}s state={media['player_state']}")
                return
            await asyncio.sleep(1.0)
        raise CheckFailure(f"no durable trace of {audio_url} within 30s; last status={seen}")
    finally:
        media_srv.stop()
        manager.close()


# ==========================================================================
# Runner
# ==========================================================================
_RESULTS: list[dict] = []
_REPORT_PRINTED = False


def _summary(registered: int) -> tuple[int, int, int, int]:
    ran = len(_RESULTS)
    failed = sum(1 for r in _RESULTS if r["outcome"] == "FAIL")
    errored = sum(1 for r in _RESULTS if r["outcome"] == "ERROR")
    passed = ran - failed - errored
    return ran, passed, failed, errored


def print_report(registered: int, selected: list[dict], final: bool) -> bool:
    global _REPORT_PRINTED
    _REPORT_PRINTED = True
    ran, passed, failed, errored = _summary(registered)
    total = len(selected)
    print()
    print("=" * 72)
    print(f"da chay {ran}/{total} muc dang ky")
    print(f"  dat   : {passed}")
    print(f"  hong  : {failed}")
    print(f"  loi   : {errored}")
    incomplete = ran < total
    if incomplete:
        done = {r["id"] for r in _RESULTS}
        missing = [c["id"] for c in selected if c["id"] not in done]
        print(f"  KHONG CHAY: {missing}")
        print("  -> FAIL toan cuc: bo kiem dung giua chung, ket qua xanh khong co gia tri.")
    if not final:
        print("  -> FAIL toan cuc: bo kiem thoat bat thuong truoc khi bao cao.")
    for r in _RESULTS:
        if r["outcome"] != "PASS":
            print(f"\n[{r['outcome']}] {r['id']}\n    {r['detail']}")
    ok = final and not incomplete and failed == 0 and errored == 0
    print("=" * 72)
    print("KET QUA: " + ("XANH" if ok else "DO"))
    if os.environ.get("GOOGLECAST_MCP_EVAL_JSON"):
        Path(os.environ["GOOGLECAST_MCP_EVAL_JSON"]).write_text(
            json.dumps({"ran": ran, "total": total, "ok": ok, "results": [
                {"id": r["id"], "outcome": r["outcome"]} for r in _RESULTS]}, indent=2),
            encoding="utf-8")
    return ok


def run(layers: set[str]) -> int:
    selected = [c for c in REGISTRY if c["layer"] in layers]
    ids = [c["id"] for c in selected]
    if len(ids) != len(set(ids)):
        print("duplicate item ids in the registry", file=sys.stderr)
        return 2

    # If the process dies before the real report, still print the tally: a
    # harness that stops half-way must not look like a clean run.
    atexit.register(lambda: None if _REPORT_PRINTED else print_report(len(REGISTRY), selected, False))

    print(f"googlecast-mcp eval -- layers: {', '.join(sorted(layers))}")
    print(f"dang ky {len(selected)} muc\n")
    # One event loop for the whole run, as the real server has. tts holds a
    # module-level asyncio.Lock, which binds to the first loop that contends on
    # it; a fresh asyncio.run() per item would break it from the second item on.
    # See technical-docs.md, "loop-bound synthesis lock".
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for item in selected:
        started = time.monotonic()
        outcome, detail = "PASS", ""
        try:
            fn = item["fn"]
            if inspect.iscoroutinefunction(fn):
                loop.run_until_complete(fn())
            else:
                fn()
            leaked = residue_report()
            if leaked:
                outcome = "ERROR"
                detail = f"mock leaked out of this item: {leaked}"
        except CheckFailure as exc:
            outcome, detail = "FAIL", str(exc)
        except AssertionError as exc:
            outcome, detail = "FAIL", str(exc)
        except BaseException as exc:  # infrastructure faults are ERROR, never skipped
            outcome, detail = "ERROR", "".join(
                traceback.format_exception_only(type(exc), exc)
            ).strip() + "\n    " + traceback.format_exc(limit=6).splitlines()[-3].strip()
        finally:
            restore_guarded()
        elapsed = time.monotonic() - started
        _RESULTS.append({"id": item["id"], "outcome": outcome, "detail": detail})
        mark = {"PASS": "  ok ", "FAIL": " HONG", "ERROR": "  LOI"}[outcome]
        print(f"{mark}  {item['id']:<45} {elapsed:5.2f}s")
        if outcome != "PASS" and detail:
            print(f"        {detail.splitlines()[0]}")

    loop.close()
    asyncio.set_event_loop(None)
    ok = print_report(len(REGISTRY), selected, True)
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="googlecast-mcp eval harness")
    parser.add_argument("--online", action="store_true",
                        help="also run items that reach the edge-tts service")
    parser.add_argument("--hardware", action="store_true",
                        help="also cast REAL AUDIO to REAL SPEAKERS -- ask the user first")
    parser.add_argument("--list", action="store_true", help="print the registry and exit")
    args = parser.parse_args()

    if args.list:
        for c in REGISTRY:
            print(f"{c['layer']:<9} {c['id']:<45} {c['desc'].strip().splitlines()[0]}")
        return 0

    layers = {"offline"}
    if args.online:
        layers.add("online")
    if args.hardware:
        layers.add("hardware")
    try:
        return run(layers)
    finally:
        shutil.rmtree(_SANDBOX, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
