#!/usr/bin/env python3
"""Eval harness for googlecast-mcp.

Three tiers, chosen by flag:

    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py
        offline only. No network, no internet, no sound. Safe anywhere.

    ... --online
        offline + real edge-tts synthesis (needs internet, still silent).

    ... --hardware
        offline + online + a real cast to a real speaker. MAKES NOISE.
        Never run this without asking the person who owns the speakers.

Design rule that this file exists to obey (learned the hard way, twice):
a mock must never leak past the tier that created it.

  * Every patch goes through ``patched()``, which restores in ``finally``.
  * ``assert_pristine()`` runs after every tier and fails loudly if any
    module attribute is still a stand-in.
  * The online and hardware tiers do not reuse the shared module singletons
    at all. They build a fresh CastManager / MediaServer of their own, so a
    leak upstream cannot silently make them measure a fake.

Exit code 0 = every check passed.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import socket
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

PASSED = 0
FAILED: list[str] = []
CURRENT_TIER = "offline"


def check(condition: object, name: str) -> bool:
    """Record one assertion. Returns the boolean so callers can branch."""
    global PASSED
    ok = bool(condition)
    if ok:
        PASSED += 1
        print(f"  ok   [{CURRENT_TIER}] {name}")
    else:
        FAILED.append(f"[{CURRENT_TIER}] {name}")
        print(f"  FAIL [{CURRENT_TIER}] {name}")
    return ok


def section(title: str) -> None:
    print(f"\n-- {title}")


@contextlib.contextmanager
def patched(obj: object, attr: str, value: object):
    """Temporarily replace ``obj.attr``, restoring even if the body raises."""
    sentinel = object()
    original = getattr(obj, attr, sentinel)
    setattr(obj, attr, value)
    try:
        yield value
    finally:
        if original is sentinel:
            delattr(obj, attr)
        else:
            setattr(obj, attr, original)


class Tripwire:
    """Callable that fails the run if it is ever called.

    Used to prove a code path did NOT happen (no TTS, no cast) rather than
    merely that the return value looked right.
    """

    def __init__(self, label: str) -> None:
        self.label = label
        self.called = False

    def __call__(self, *args: object, **kwargs: object):
        self.called = True
        raise AssertionError(f"{self.label} must not be called here")


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

# Two entries share host 192.168.1.22 on purpose: "Family speaker group" is a
# Cast group whose only member is "Kitchen speaker". Filtering by NAME looks
# correct here and is a fake test; the real property is that no physical HOST
# appears twice in the fan-out set.
FIXTURE_DEVICES = [
    {
        "friendly_name": "Kitchen speaker",
        "uuid": "11111111-1111-1111-1111-111111111111",
        "model_name": "Google Nest Mini",
        "manufacturer": "Google Inc.",
        "host": "192.168.1.22",
        "port": 8009,
        "cast_type": "audio",
    },
    {
        "friendly_name": "Office speaker",
        "uuid": "22222222-2222-2222-2222-222222222222",
        "model_name": "Google Nest Mini",
        "manufacturer": "Google Inc.",
        "host": "192.168.1.23",
        "port": 8009,
        "cast_type": "audio",
    },
    {
        "friendly_name": "Family speaker group",
        "uuid": "33333333-3333-3333-3333-333333333333",
        "model_name": "Google Cast Group",
        "manufacturer": "Google Inc.",
        "host": "192.168.1.22",
        "port": 32123,
        "cast_type": "group",
    },
    {
        "friendly_name": "Working display",
        "uuid": "44444444-4444-4444-4444-444444444444",
        "model_name": "Google Nest Hub",
        "manufacturer": "Google Inc.",
        "host": "192.168.1.24",
        "port": 8009,
        "cast_type": "cast",  # video device: must never be treated as a speaker
    },
]

HOST_BY_NAME = {d["friendly_name"]: d["host"] for d in FIXTURE_DEVICES}


class FakeManager:
    """Stand-in CastManager that records casts instead of performing them."""

    def __init__(self, devices: list[dict], failing: set[str] | None = None) -> None:
        self._devices = devices
        self._failing = failing or set()
        self.casts: list[tuple[str, str]] = []

    def list_cached(self) -> list[dict]:
        return list(self._devices)

    def list_speakers(self) -> list[dict]:
        return [d for d in self._devices if d["cast_type"] in ("audio", "group")]

    def discover(self, timeout: float = 5.0) -> list[dict]:
        return list(self._devices)

    def play_media(self, name, url, content_type=None, title=None):
        if name in self._failing:
            raise RuntimeError(f"{name} did not respond")
        self.casts.append((name, url))
        return {"device": {"friendly_name": name}}


class FakeMediaServer:
    """Stand-in MediaServer: builds a URL, binds nothing."""

    def __init__(self) -> None:
        self.requests: list[Path] = []

    def url_for(self, path: Path) -> str:
        self.requests.append(path)
        return f"http://192.168.1.128:8766/{path.name}"

    def stop(self) -> None:
        pass


# --------------------------------------------------------------------------
# hygiene guard
# --------------------------------------------------------------------------

_PRISTINE: dict[str, object] = {}


def snapshot_pristine() -> None:
    """Remember the genuine module attributes before any tier runs."""
    from googlecast_mcp import server, tts
    from googlecast_mcp.cast_manager import CastManager
    from googlecast_mcp.media_server import MediaServer

    _PRISTINE["tts.synthesize"] = tts.synthesize
    _PRISTINE["server.tts"] = server.tts
    _PRISTINE["manager_type"] = CastManager
    _PRISTINE["media_type"] = MediaServer


def assert_pristine(where: str) -> None:
    """Fail if a mock outlived the tier that installed it."""
    from googlecast_mcp import server, tts
    from googlecast_mcp.cast_manager import CastManager
    from googlecast_mcp.media_server import MediaServer

    check(tts.synthesize is _PRISTINE["tts.synthesize"], f"{where}: tts.synthesize restored")
    check(server.tts is _PRISTINE["server.tts"], f"{where}: server.tts module restored")
    check(
        type(server._manager) is _PRISTINE["manager_type"],
        f"{where}: server._manager is a real CastManager",
    )
    check(
        type(server._media_server) is _PRISTINE["media_type"],
        f"{where}: server._media_server is a real MediaServer",
    )


# --------------------------------------------------------------------------
# offline tier
# --------------------------------------------------------------------------

EXPECTED_TOOLS = {
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


async def tier_offline() -> None:
    global CURRENT_TIER
    CURRENT_TIER = "offline"

    section("imports and tool surface")
    from googlecast_mcp import server, tts
    from googlecast_mcp.cast_manager import _guess_content_type
    from googlecast_mcp.speaker_store import SpeakerStore, is_speaker

    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    check(names == EXPECTED_TOOLS, f"exactly the 13 expected tools are registered ({len(names)})")
    check(all(t.description for t in tools), "every tool carries a description for the LLM")

    say_tool = next(t for t in tools if t.name == "say")
    say_props = say_tool.inputSchema.get("properties", {})
    check("text" in say_props, "say exposes a text parameter")
    check(
        "target" not in say_tool.inputSchema.get("required", []),
        "say does not require a speaker up front (so it can ask instead)",
    )

    section("device classification")
    check(is_speaker(FIXTURE_DEVICES[0]), "audio device counts as a speaker")
    check(is_speaker(FIXTURE_DEVICES[2]), "speaker group counts as a speaker")
    check(not is_speaker(FIXTURE_DEVICES[3]), "video Nest Hub is not a speaker")
    check(not is_speaker({}), "device with no cast_type is not a speaker")

    section("content type guessing")
    check(_guess_content_type("http://h/a.mp3") == "audio/mpeg", "mp3 -> audio/mpeg")
    check(_guess_content_type("http://h/a.MP3?x=1") == "audio/mpeg", "uppercase + query string")
    check(_guess_content_type("http://h/a.m3u8") == "application/x-mpegURL", "hls playlist")
    check(_guess_content_type("http://h/a.png") == "image/png", "png -> image/png")
    check(_guess_content_type("http://h/unknown") == "video/mp4", "unknown extension falls back")

    section("voice resolution")
    check(tts.resolve_voice("female") == "vi-VN-HoaiMyNeural", "female -> HoaiMy")
    check(tts.resolve_voice("MALE") == "vi-VN-NamMinhNeural", "male is case-insensitive")
    check(tts.resolve_voice(None) == tts.DEFAULT_VOICE, "no voice -> default")
    check(tts.resolve_voice("en-US-AriaNeural") == "en-US-AriaNeural", "full voice id passes through")

    section("empty text is refused before any network call")
    tripwire = Tripwire("edge_tts.Communicate")
    import edge_tts

    with patched(edge_tts, "Communicate", tripwire):
        err: Exception | None = None
        try:
            await tts.synthesize("   ")
        except Exception as exc:  # catch broadly so a wrong error type reads as red
            err = exc
        check(isinstance(err, ValueError), f"blank text raises ValueError (got {err!r})")
        check(not tripwire.called, "blank text never reaches the TTS backend")

    section("speaker store round trip")
    with tempfile.TemporaryDirectory() as tmp:
        store = SpeakerStore(Path(tmp) / "speakers.json")
        check(store.load() == [], "missing store file reads as empty, not an error")
        store.save(FIXTURE_DEVICES[:2])
        store.save([FIXTURE_DEVICES[2]])
        saved = {d["friendly_name"] for d in store.load()}
        check(saved == {"Kitchen speaker", "Office speaker", "Family speaker group"},
              "save merges instead of replacing (a lossy mDNS scan must not delete)")
        check({d["friendly_name"] for d in store.speakers()} == saved,
              "speakers() filters to speakers only")
        (Path(tmp) / "speakers.json").write_text("{ not json", encoding="utf-8")
        check(store.load() == [], "corrupt store file degrades to empty, not a crash")

    section("say with no speaker chosen: asks, plays nothing")
    fake_mgr = FakeManager(FIXTURE_DEVICES)
    tts_tripwire = Tripwire("tts.synthesize")
    with patched(server, "_manager", fake_mgr), \
         patched(server, "_media_server", FakeMediaServer()), \
         patched(server.tts, "synthesize", tts_tripwire):
        result = await server.say("Cơm đã chín rồi")
        check(result["status"] == "needs_speaker_selection", "status asks for a speaker")
        check(not fake_mgr.casts, "nothing was cast")
        check(not tts_tripwire.called, "no audio was synthesized")
        listed = {s["friendly_name"] for s in result["speakers"]}
        check(listed == {"Kitchen speaker", "Office speaker", "Family speaker group"},
              "the speaker list handed back excludes video devices")
        check("all" in result["message"], "the message tells the LLM that 'all' is an option")

    with patched(server, "_manager", FakeManager([])), \
         patched(server, "_media_server", FakeMediaServer()), \
         patched(server.tts, "synthesize", Tripwire("tts.synthesize")):
        empty = await server.say("xin chào")
        check(empty["status"] == "no_speakers_found", "empty network gets its own status")

    section("target selection")

    async def select(value):
        fake = FakeManager(FIXTURE_DEVICES)
        with patched(server, "_manager", fake):
            names_, prompt = await server._select_targets(value)
        return names_, prompt

    chosen, prompt = await select("all")
    check(prompt is None, "'all' resolves without asking")
    check("Family speaker group" not in chosen, "'all' excludes the Cast group")
    check("Working display" not in chosen, "'all' excludes video devices")
    # Not "no duplicates" — that stays green when 'all' wrongly resolves to a
    # single entry. The property is exact coverage: one cast per distinct
    # physical speaker host, no more and no fewer.
    speaker_hosts = sorted({d["host"] for d in FIXTURE_DEVICES if is_speaker(d)})
    hosts = sorted(HOST_BY_NAME[n] for n in chosen)
    check(hosts == speaker_hosts,
          f"'all' hits each physical host exactly once ({hosts} vs {speaker_hosts})")
    check(set(chosen) == {"Kitchen speaker", "Office speaker"}, "'all' = the two real speakers")

    viet, _ = await select("tất cả")
    check(set(viet) == set(chosen), "Vietnamese 'tất cả' behaves like 'all'")

    grp, _ = await select("Family speaker group")
    check(grp == ["Family speaker group"], "a group named explicitly is still allowed")

    multi, _ = await select("Kitchen speaker, Office speaker")
    check(multi == ["Kitchen speaker", "Office speaker"], "comma-separated list is split")

    spaced, _ = await select("  Kitchen speaker ,, Office speaker  ")
    check(spaced == ["Kitchen speaker", "Office speaker"], "stray spaces and empty items dropped")

    blank, blank_prompt = await select("   ")
    check(blank == [] and blank_prompt is not None, "whitespace-only target is treated as absent")

    section("say fan-out and failure isolation")

    async def fake_synth(text, voice=None, rate="+0%", **kw):
        path = Path(tempfile.gettempdir()) / "googlecast-eval-fake.mp3"
        path.write_bytes(b"\x00")
        return path

    fake_mgr = FakeManager(FIXTURE_DEVICES)
    media = FakeMediaServer()
    with patched(server, "_manager", fake_mgr), \
         patched(server, "_media_server", media), \
         patched(server.tts, "synthesize", fake_synth):
        res = await server.say("Cơm đã chín rồi", target="all")
        check(res["status"] == "ok", "casting to all reports ok")
        check(len(fake_mgr.casts) == 2, "exactly two casts were issued")
        cast_hosts = sorted(HOST_BY_NAME[n] for n, _ in fake_mgr.casts)
        check(cast_hosts == speaker_hosts,
              f"each physical speaker received exactly one stream ({cast_hosts})")
        check(len({u for _, u in fake_mgr.casts}) == 1, "every speaker got the same audio URL")
        check(res["voice"] == "vi-VN-HoaiMyNeural", "the resolved voice is reported back")

    broken = FakeManager(FIXTURE_DEVICES, failing={"Office speaker"})
    with patched(server, "_manager", broken), \
         patched(server, "_media_server", FakeMediaServer()), \
         patched(server.tts, "synthesize", fake_synth):
        res = await server.say("xin chào", target="Kitchen speaker, Office speaker")
        by_name = {r["speaker"]: r for r in res["results"]}
        check(by_name["Kitchen speaker"]["status"] == "playing", "healthy speaker still plays")
        check(by_name["Office speaker"]["status"] == "error", "broken speaker reports its own error")
        check(res["status"] == "ok", "one dead speaker does not fail the whole call")

    all_broken = FakeManager(FIXTURE_DEVICES, failing={"Kitchen speaker"})
    with patched(server, "_manager", all_broken), \
         patched(server, "_media_server", FakeMediaServer()), \
         patched(server.tts, "synthesize", fake_synth):
        res = await server.say("xin chào", target="Kitchen speaker")
        check(res["status"] == "failed", "every speaker failing reports failed, not ok")

    section("transport security allowlist")
    from googlecast_mcp.__main__ import _transport_security

    settings = _transport_security(
        "0.0.0.0",
        ["google-cast.adrec.cloud"],
        ["http://192.168.1.99:8383"],
    )
    hosts_allowed = list(settings.allowed_hosts or [])
    origins_allowed = list(settings.allowed_origins or [])
    check("google-cast.adrec.cloud" in hosts_allowed,
          "bare host with no :port is allowed (a proxy on 443 sends no port)")
    check("google-cast.adrec.cloud:*" in hosts_allowed, "host with any port is allowed")
    check("0.0.0.0" not in hosts_allowed, "the wildcard bind address is not itself an allowed host")
    check("127.0.0.1" in hosts_allowed, "loopback stays allowed")
    check("https://google-cast.adrec.cloud" in origins_allowed,
          "https origin is allowed (TLS terminates at the reverse proxy)")
    check("http://google-cast.adrec.cloud" in origins_allowed, "http origin is allowed too")
    check("http://192.168.1.99:8383" in origins_allowed,
          "an explicit --cors-origin is carried into the allowlist")
    check(len(origins_allowed) == len(set(origins_allowed)), "no duplicate origins")

    named = _transport_security("192.168.1.128", [], None)
    check("192.168.1.128" in (named.allowed_hosts or []), "an explicit bind host is allowed")

    section("media URL construction")
    from googlecast_mcp.media_server import MediaServer, lan_ip

    ip = lan_ip()
    check(isinstance(ip, str) and ip.count(".") == 3, f"lan_ip returns an IPv4 address ({ip})")
    with tempfile.TemporaryDirectory() as tmp:
        ms = MediaServer(Path(tmp), host="192.168.1.128", port=0)
        f = Path(tmp) / "chào bạn.mp3"
        f.write_bytes(b"\x00")
        try:
            url = ms.url_for(f)
            check(url.startswith("http://192.168.1.128:"), "URL advertises the LAN host, not the bind host")
            check("%" in url.rsplit("/", 1)[-1], "non-ASCII filenames are percent-encoded")
            check(ms.port not in (0, None), "a real port was bound")
            bound = socket.socket()
            bound.settimeout(2)
            reachable = bound.connect_ex(("127.0.0.1", ms.port)) == 0
            bound.close()
            check(reachable, "the media server actually accepts connections")
        finally:
            ms.stop()
        check(ms.port == 0, "stop() releases the server")


# --------------------------------------------------------------------------
# online tier  (internet, still silent)
# --------------------------------------------------------------------------

async def tier_online() -> None:
    """Real edge-tts synthesis. Builds its own objects; shares no mock."""
    global CURRENT_TIER
    CURRENT_TIER = "online"
    section("real text-to-speech")

    import googlecast_mcp.tts as tts_mod

    # Do NOT reload the module here. Reloading would rebind the attribute to a
    # brand-new function object, which destroys the only handle we have on the
    # genuine one and makes the leak check unable to tell real from fake.
    # Instead, compare against the snapshot taken before any tier ran: this is
    # the check that would have caught the offline tier leaving a stand-in
    # behind and this tier silently measuring it.
    check(tts_mod.synthesize is _PRISTINE["tts.synthesize"],
          "synthesize under test is the genuine function, not a stand-in")

    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        path = await tts_mod.synthesize("Cơm đã chín rồi", voice="female", cache_dir=cache)
        size = path.stat().st_size if path.exists() else 0
        check(path.exists(), "an mp3 file was written")
        check(size > 1000, f"the mp3 is real audio, not an empty file ({size} bytes)")
        head = path.read_bytes()[:4]
        # Either an ID3 tag or a raw MPEG frame sync (0xFF followed by three
        # set bits). edge-tts emits the latter, and the exact second byte
        # varies with bitrate, so matching a fixed pair would be brittle.
        is_mp3 = head[:3] == b"ID3" or (head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
        check(is_mp3, f"the file looks like mp3 (header {head.hex()})")

        again = await tts_mod.synthesize("Cơm đã chín rồi", voice="female", cache_dir=cache)
        check(again == path, "the same text and voice reuse the cached render")

        slower = await tts_mod.synthesize("Cơm đã chín rồi", voice="female", rate="-20%", cache_dir=cache)
        check(slower != path, "a different rate is cached separately")
        check(slower.stat().st_size > 1000, "the slower render is real audio too")

        male = await tts_mod.synthesize("Xin chào", voice="male", cache_dir=cache)
        check(male.stat().st_size > 1000, "the male voice synthesizes (not judged by ear here)")


# --------------------------------------------------------------------------
# hardware tier  (MAKES NOISE)
# --------------------------------------------------------------------------

async def tier_hardware(speaker: str | None) -> None:
    """Cast for real. Builds a brand new CastManager and MediaServer.

    Nothing here touches googlecast_mcp.server's singletons, precisely so a
    mock installed by an earlier tier cannot make this tier lie in either
    direction (fake success, or a fake "no speaker answered mDNS").
    """
    global CURRENT_TIER
    CURRENT_TIER = "hardware"
    section("real discovery and cast")

    from googlecast_mcp import tts as tts_mod
    from googlecast_mcp.cast_manager import CastManager
    from googlecast_mcp.media_server import MediaServer

    check(tts_mod.synthesize is _PRISTINE["tts.synthesize"], "TTS is un-mocked before casting")

    manager = CastManager()  # fresh instance, not server._manager
    media = MediaServer(tts_mod.default_cache_dir())
    try:
        devices = await asyncio.to_thread(manager.discover, 8.0)
        check(devices, f"mDNS found devices ({len(devices)})")
        speakers = await asyncio.to_thread(manager.list_speakers)
        check(speakers, f"at least one speaker is on the LAN ({len(speakers)})")
        if not speakers:
            return

        name = speaker or speakers[0]["friendly_name"]
        info = next((s for s in speakers if s["friendly_name"] == name), None)
        check(info is not None, f"requested speaker {name!r} is known")
        if info is None:
            return

        sock = socket.socket()
        sock.settimeout(3)
        open_8009 = sock.connect_ex((info["host"], info["port"])) == 0
        sock.close()
        check(open_8009, f"{name} accepts TCP on {info['host']}:{info['port']} (device not hung)")

        audio = await tts_mod.synthesize("Đây là bài kiểm tra tự động", voice="female")
        check(audio.stat().st_size > 1000, "audio for the real cast is non-empty")

        url = await asyncio.to_thread(media.url_for, audio)
        status = await asyncio.to_thread(manager.play_media, name, url, "audio/mpeg", "eval")
        # play_media returns once the receiver app is up, which is earlier than
        # the moment playback starts — reading the state right here catches the
        # device still IDLE. Poll for the transition instead of assuming it has
        # already happened; a short clip can also finish before we look.
        player = status["media"]["player_state"]
        for _ in range(10):
            if player in ("PLAYING", "BUFFERING"):
                break
            await asyncio.sleep(1)
            player = (await asyncio.to_thread(manager.status, name))["media"]["player_state"]
        check(player in ("PLAYING", "BUFFERING"),
              f"{name} starts playing (last seen: {player})")
        await asyncio.sleep(6)
        after = await asyncio.to_thread(manager.status, name)
        check(after["media"]["player_state"] in ("IDLE", "PLAYING", "PAUSED"),
              "the speaker reached a sane state after playback")
    finally:
        media.stop()
        await asyncio.to_thread(manager.close)


# --------------------------------------------------------------------------

async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="also run the real-TTS tier")
    parser.add_argument("--hardware", action="store_true", help="also cast for real (MAKES NOISE)")
    parser.add_argument("--speaker", default=None, help="speaker name for the hardware tier")
    parser.add_argument("--json", action="store_true", help="print a machine-readable summary")
    args = parser.parse_args()

    snapshot_pristine()

    print("== googlecast-mcp eval ==")
    await tier_offline()
    assert_pristine("after offline")

    if args.online or args.hardware:
        await tier_online()
        assert_pristine("after online")

    if args.hardware:
        await tier_hardware(args.speaker)
        assert_pristine("after hardware")

    total = PASSED + len(FAILED)
    print(f"\n{PASSED}/{total} checks passed")
    for f in FAILED:
        print(f"  FAILED: {f}")
    if args.json:
        print(json.dumps({"passed": PASSED, "total": total, "failures": FAILED}))
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
