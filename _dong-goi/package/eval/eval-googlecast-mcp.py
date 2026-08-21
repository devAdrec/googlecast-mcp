#!/usr/bin/env python3
"""Evaluation harness for googlecast-mcp.

Three tiers, chosen so the default one is safe to run anywhere:

    (default)     offline  — no network, no sound, no real device touched
    --online      adds checks that need internet (edge-tts synthesis)
    --hardware    adds checks that cast to REAL speakers and make REAL sound

A test nobody dares run is worth nothing, so everything that can be checked
without a side effect is checked in the default tier. Casting is opt-in.

Run:
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --online
    uv run python _dong-goi/package/eval/eval-googlecast-mcp.py --hardware --speaker "Kitchen speaker"

Exit code 0 when every selected check passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Point the device store and the audio cache at throwaway directories BEFORE
# importing the server: importing it constructs the store and the cache dir,
# and an eval run must never read or rewrite the real ~/.googlecast-mcp file.
_SANDBOX = Path(tempfile.mkdtemp(prefix="googlecast-mcp-eval-"))
os.environ["GOOGLECAST_MCP_STORE"] = str(_SANDBOX / "speakers.json")
os.environ["GOOGLECAST_MCP_CACHE"] = str(_SANDBOX / "cache")

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


# --------------------------------------------------------------------------
# Tiny test runner: no pytest dependency, so the harness runs from a bare
# checkout the moment `uv sync` has finished.
# --------------------------------------------------------------------------

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}" + (f"  — {detail}" if detail else ""))


def section(title: str) -> None:
    print(f"\n[{title}]")


# --------------------------------------------------------------------------
# Fixtures — a speaker layout that reproduces the real house, including the
# case that caused the original bug: a group and one of its members are the
# SAME physical speaker, so they share a host address.
# --------------------------------------------------------------------------

FIXTURE_SPEAKERS = [
    {
        "friendly_name": "Family speaker group",
        "uuid": "00000000-0000-0000-0000-0000000000g1",
        "model_name": "Google Cast Group",
        "manufacturer": "Google Inc.",
        "host": "192.168.1.22",
        "port": 32000,
        "cast_type": "group",
    },
    {
        "friendly_name": "Kitchen speaker",
        "uuid": "00000000-0000-0000-0000-000000000001",
        "model_name": "Google Nest Mini",
        "manufacturer": "Google Inc.",
        "host": "192.168.1.22",
        "port": 8009,
        "cast_type": "audio",
    },
    {
        "friendly_name": "Bedroom speaker",
        "uuid": "00000000-0000-0000-0000-000000000002",
        "model_name": "Google Nest Mini",
        "manufacturer": "Google Inc.",
        "host": "192.168.1.23",
        "port": 8009,
        "cast_type": "audio",
    },
    {
        "friendly_name": "Office speaker",
        "uuid": "00000000-0000-0000-0000-000000000003",
        "model_name": "Google Home",
        "manufacturer": "Google Inc.",
        "host": "192.168.1.24",
        "port": 8009,
        "cast_type": "audio",
    },
]

FIXTURE_VIDEO = {
    "friendly_name": "Working display",
    "uuid": "00000000-0000-0000-0000-0000000000v1",
    "model_name": "Google Nest Hub",
    "manufacturer": "Google Inc.",
    "host": "192.168.1.25",
    "port": 8009,
    "cast_type": "cast",
}

HOST_BY_NAME = {d["friendly_name"]: d["host"] for d in FIXTURE_SPEAKERS}


class FakeCast:
    """Records every cast attempt instead of talking to a device."""

    def __init__(self, broken: set[str] | None = None) -> None:
        self.calls: list[tuple[str, str]] = []  # (speaker name, url)
        self.broken = broken or set()

    def play_media(self, name, url, content_type=None, title=None):
        if name in self.broken:
            raise RuntimeError(f"Device {name!r} did not respond.")
        self.calls.append((name, url))
        return {"device": {"friendly_name": name}}

    @property
    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


# The offline tier replaces tts.synthesize on the MODULE object, which every
# other importer of it shares. Keep the real one so the online tier measures
# real synthesis instead of silently re-measuring the fake.
_REAL_SYNTHESIZE = None


def install_fakes(monkey_targets, cast: FakeCast, tts_calls: list) -> None:
    """Redirect the server's speaker list, casting, and TTS to fakes."""
    global _REAL_SYNTHESIZE
    server = monkey_targets
    if _REAL_SYNTHESIZE is None:
        _REAL_SYNTHESIZE = server.tts.synthesize

    server._manager.list_speakers = lambda: list(FIXTURE_SPEAKERS)
    server._manager.list_cached = lambda: [*FIXTURE_SPEAKERS, FIXTURE_VIDEO]
    server._manager.play_media = cast.play_media
    server._media_server.url_for = lambda path: "http://192.168.1.128:8766/fake.mp3"

    async def fake_synthesize(text, voice=None, rate="+0%", **kwargs):
        if not text or not text.strip():
            raise ValueError("text must not be empty")
        tts_calls.append((text, voice, rate))
        return Path("/dev/null")

    server.tts.synthesize = fake_synthesize


# --------------------------------------------------------------------------
# Offline tier
# --------------------------------------------------------------------------


async def run_offline() -> None:
    section("import and tool surface")

    import googlecast_mcp
    from googlecast_mcp import server as srv
    from googlecast_mcp import tts as tts_mod
    from googlecast_mcp.__main__ import _transport_security
    from googlecast_mcp.cast_manager import _guess_content_type
    from googlecast_mcp.speaker_store import SpeakerStore, is_speaker

    check("package imports", googlecast_mcp is not None)

    tools = await srv.mcp.list_tools()
    tool_names = sorted(t.name for t in tools)
    expected_tools = sorted(
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
    check("13 tools registered", len(tools) == 13, f"got {len(tools)}")
    check("tool names match the documented set", tool_names == expected_tools,
          f"got {tool_names}")
    check("every tool carries a description",
          all((t.description or "").strip() for t in tools))

    # -- content type guessing -------------------------------------------
    section("content type guessing")
    check("mp3 is audio/mpeg", _guess_content_type("http://h/a.mp3") == "audio/mpeg")
    check("query string is ignored",
          _guess_content_type("http://h/a.mp3?x=1") == "audio/mpeg")
    check("uppercase extension still matches",
          _guess_content_type("http://h/A.MP3") == "audio/mpeg")
    check("mp4 is video/mp4", _guess_content_type("http://h/a.mp4") == "video/mp4")
    check("hls is x-mpegURL",
          _guess_content_type("http://h/a.m3u8") == "application/x-mpegURL")
    check("unknown extension falls back to video/mp4",
          _guess_content_type("http://h/a.zzz") == "video/mp4")

    # -- speaker classification ------------------------------------------
    section("speaker classification")
    check("audio device is a speaker", is_speaker({"cast_type": "audio"}))
    check("speaker group is a speaker", is_speaker({"cast_type": "group"}))
    check("video cast is NOT a speaker", not is_speaker({"cast_type": "cast"}))
    check("missing cast_type is NOT a speaker", not is_speaker({}))

    # -- voices -----------------------------------------------------------
    section("voice resolution")
    check("default voice is the female Vietnamese one",
          tts_mod.resolve_voice(None) == "vi-VN-HoaiMyNeural")
    check("'female' maps to HoaiMy",
          tts_mod.resolve_voice("female") == "vi-VN-HoaiMyNeural")
    check("'male' maps to NamMinh",
          tts_mod.resolve_voice("male") == "vi-VN-NamMinhNeural")
    check("case and spaces are tolerated",
          tts_mod.resolve_voice("  Male ") == "vi-VN-NamMinhNeural")
    check("a full voice id passes through",
          tts_mod.resolve_voice("en-US-AriaNeural") == "en-US-AriaNeural")

    # -- transport security ----------------------------------------------
    # These two properties are exactly what cost days of 421 debugging.
    section("transport security allowlist")
    sec = _transport_security("0.0.0.0", ["google-cast.adrec.cloud"],
                              ["http://192.168.1.99:8383"])
    hosts = list(sec.allowed_hosts)
    origins = list(sec.allowed_origins)
    check("the extra --allow-host domain is trusted",
          "google-cast.adrec.cloud" in hosts, f"hosts={hosts}")
    check("bare host with NO :port is allowed (proxy on 443 sends no port)",
          "google-cast.adrec.cloud" in hosts)
    check("host with wildcard port is allowed",
          "google-cast.adrec.cloud:*" in hosts)
    check("https origin is allowed (TLS terminated by the proxy)",
          "https://google-cast.adrec.cloud" in origins, f"origins={origins}")
    check("https origin with wildcard port is allowed",
          "https://google-cast.adrec.cloud:*" in origins)
    check("loopback stays allowed", "127.0.0.1" in hosts)
    check("the wildcard bind address is NOT itself an allowed host",
          "0.0.0.0" not in hosts, f"hosts={hosts}")
    check("an explicit browser origin is carried through",
          "http://192.168.1.99:8383" in origins)

    sec_bind = _transport_security("192.168.1.128", [], [])
    check("an explicit bind host is trusted",
          "192.168.1.128" in list(sec_bind.allowed_hosts))

    # -- store round trip -------------------------------------------------
    section("device store")
    store = SpeakerStore(_SANDBOX / "store-test.json")
    check("an empty store loads as an empty list", store.load() == [])
    store.save([*FIXTURE_SPEAKERS, FIXTURE_VIDEO])
    check("saved devices come back", len(store.load()) == 5)
    store.save([{**FIXTURE_SPEAKERS[1], "host": "192.168.1.99"}])
    reloaded = {d["uuid"]: d for d in store.load()}
    check("a re-save merges by uuid instead of duplicating", len(reloaded) == 5)
    check("a merged device keeps the newest address",
          reloaded[FIXTURE_SPEAKERS[1]["uuid"]]["host"] == "192.168.1.99")
    check("the store filters speakers from video casts",
          len(store.speakers()) == 4)

    # -- say(): target selection -----------------------------------------
    section("say(): no target means no sound")
    cast = FakeCast()
    tts_calls: list = []
    install_fakes(srv, cast, tts_calls)

    result = await srv.say(text="Cơm đã chín rồi")
    check("omitting the speaker returns needs_speaker_selection",
          result.get("status") == "needs_speaker_selection", str(result)[:120])
    check("omitting the speaker casts to NOTHING", cast.calls == [])
    check("omitting the speaker does NOT synthesize audio", tts_calls == [])
    check("the prompt lists the speakers for the model to ask about",
          len(result.get("speakers", [])) == 4)
    check("the prompt names the speakers in its message",
          "Kitchen speaker" in result.get("message", ""))

    section("say(): 'all'")
    cast = FakeCast()
    tts_calls = []
    install_fakes(srv, cast, tts_calls)
    result = await srv.say(text="Xin chào", target="all")
    names = cast.names
    check("'all' reaches at least one speaker", len(names) > 0)
    check("'all' excludes speaker groups",
          "Family speaker group" not in names, f"cast to {names}")
    # The false-green lesson: comparing NAMES cannot see this bug, because a
    # group and its member have different names. Compare PHYSICAL devices.
    hosts_hit = [HOST_BY_NAME[n] for n in names if n in HOST_BY_NAME]
    check("'all' hits no physical device twice (compared by host, not name)",
          len(hosts_hit) == len(set(hosts_hit)),
          f"hosts={hosts_hit} from {names}")
    check("'all' still reaches every individual speaker",
          set(names) == {"Kitchen speaker", "Bedroom speaker", "Office speaker"},
          f"got {names}")
    check("'all' synthesizes the audio exactly once", len(tts_calls) == 1)
    check("every speaker gets the same audio url",
          len({url for _, url in cast.calls}) == 1)
    check("'all' reports ok", result.get("status") == "ok")

    section("say(): Vietnamese and alias keywords for 'all'")
    for keyword in ("tất cả", "tat ca", "everyone", "*", "ALL"):
        cast = FakeCast()
        install_fakes(srv, cast, [])
        await srv.say(text="Xin chào", target=keyword)
        check(f"{keyword!r} means every speaker, groups excluded",
              set(cast.names) == {"Kitchen speaker", "Bedroom speaker",
                                  "Office speaker"},
              f"got {cast.names}")

    section("say(): explicit targets")
    cast = FakeCast()
    install_fakes(srv, cast, [])
    await srv.say(text="Xin chào", target="Family speaker group")
    check("a group named explicitly IS still cast to",
          cast.names == ["Family speaker group"], f"got {cast.names}")

    cast = FakeCast()
    install_fakes(srv, cast, [])
    await srv.say(text="Xin chào",
                     target="Kitchen speaker, Bedroom speaker")
    check("a comma-separated list reaches both speakers",
          cast.names == ["Kitchen speaker", "Bedroom speaker"], f"got {cast.names}")

    cast = FakeCast()
    install_fakes(srv, cast, [])
    await srv.say(text="Xin chào",
                     target=" Kitchen speaker ,, Bedroom speaker ")
    check("stray spaces and empty list items are dropped",
          cast.names == ["Kitchen speaker", "Bedroom speaker"], f"got {cast.names}")

    section("say(): one broken speaker must not sink the rest")
    cast = FakeCast(broken={"Ghost speaker"})
    install_fakes(srv, cast, [])
    result = await srv.say(text="Xin chào",
                              target="Kitchen speaker, Ghost speaker")
    by_speaker = {r["speaker"]: r for r in result["results"]}
    check("the working speaker still plays",
          by_speaker["Kitchen speaker"]["status"] == "playing")
    check("the broken speaker is reported as an error",
          by_speaker["Ghost speaker"]["status"] == "error")
    check("the broken speaker carries its reason",
          "error" in by_speaker["Ghost speaker"])
    check("the call still reports ok when at least one speaker played",
          result["status"] == "ok")

    cast = FakeCast(broken={"Kitchen speaker"})
    install_fakes(srv, cast, [])
    result = await srv.say(text="Xin chào", target="Kitchen speaker")
    check("the call reports failed when nothing played",
          result["status"] == "failed", str(result)[:120])

    section("say(): empty text")
    cast = FakeCast()
    install_fakes(srv, cast, [])
    raised = False
    try:
        await srv.say(text="   ", target="Kitchen speaker")
    except ValueError:
        raised = True
    check("blank text raises ValueError", raised)
    check("blank text casts nothing", cast.calls == [])

    section("say(): no speaker exists at all")
    srv._manager.list_speakers = lambda: []
    srv._manager.discover = lambda timeout=5.0: []
    cast = FakeCast()
    srv._manager.play_media = cast.play_media
    result = await srv.say(text="Xin chào")
    check("an empty network returns no_speakers_found",
          result.get("status") == "no_speakers_found", str(result)[:120])
    check("an empty network casts nothing", cast.calls == [])


# --------------------------------------------------------------------------
# Online tier — needs internet, still makes no sound
# --------------------------------------------------------------------------


async def run_online() -> None:
    section("online: real TTS synthesis (internet, no sound)")
    import importlib

    tts_mod = importlib.import_module("googlecast_mcp.tts")
    # Undo the offline tier's module-level fake before measuring anything.
    if _REAL_SYNTHESIZE is not None:
        tts_mod.synthesize = _REAL_SYNTHESIZE
    check("the online tier is testing the real synthesize, not the fake",
          tts_mod.synthesize.__module__ == "googlecast_mcp.tts",
          tts_mod.synthesize.__module__)
    cache = _SANDBOX / "online-cache"
    cache.mkdir(parents=True, exist_ok=True)

    path = await tts_mod.synthesize("Cơm đã chín rồi", voice="female",
                                    cache_dir=cache)
    check("synthesis writes a file", path.exists())
    size = path.stat().st_size if path.exists() else 0
    check("the mp3 is not empty", size > 1000, f"{size} bytes")
    head = path.read_bytes()[:4]
    # Either an ID3 tag, or a bare MPEG frame: 11 sync bits set.
    check("the file really is an mp3",
          head[:3] == b"ID3" or (head[0] == 0xFF and head[1] & 0xE0 == 0xE0),
          repr(head))

    again = await tts_mod.synthesize("Cơm đã chín rồi", voice="female",
                                     cache_dir=cache)
    check("a repeat of the same text reuses the cached file", again == path)

    male = await tts_mod.synthesize("Cơm đã chín rồi", voice="male",
                                    cache_dir=cache)
    check("a different voice renders to a different file", male != path)
    check("the male voice file is not empty", male.stat().st_size > 1000)

    slow = await tts_mod.synthesize("Cơm đã chín rồi", voice="female",
                                    rate="-20%", cache_dir=cache)
    check("a different rate renders to a different file", slow != path)
    check("the slowed file is not empty", slow.stat().st_size > 1000)

    raised = False
    try:
        await tts_mod.synthesize("", cache_dir=cache)
    except ValueError:
        raised = True
    check("empty text raises before any network call", raised)


# --------------------------------------------------------------------------
# Hardware tier — REAL SOUND. Opt-in only.
# --------------------------------------------------------------------------


async def run_hardware(speaker: str) -> None:
    section(f"hardware: casting real audio to {speaker!r} — THIS MAKES SOUND")
    import importlib

    srv = importlib.import_module("googlecast_mcp.server")
    # This tier must see the real network, so drop the sandboxed store.
    os.environ.pop("GOOGLECAST_MCP_STORE", None)
    importlib.reload(importlib.import_module("googlecast_mcp.speaker_store"))

    # The offline tier stubbed list_speakers/discover onto the module-level
    # manager and never put them back, so this tier would "discover" the empty
    # network that test set up. Build a real manager instead of trusting it.
    from googlecast_mcp.cast_manager import CastManager

    srv._manager = CastManager()

    # Guard: prove this tier measures the real thing, not a leftover stub.
    check("hardware tier holds a real manager, not an offline stub",
          type(srv._manager.list_speakers).__name__ == "method",
          f"list_speakers is {type(srv._manager.list_speakers).__name__}")

    speakers = await asyncio.to_thread(srv._manager.list_speakers)
    check("a real speaker is discoverable", len(speakers) > 0,
          "no speaker answered mDNS")
    if not speakers:
        return

    result = await srv.say(text="Đây là bài kiểm tra tự động",
                              target=speaker)
    check("the real cast reports ok", result.get("status") == "ok", str(result)[:200])
    played = [r for r in result.get("results", []) if r["status"] == "playing"]
    check("the chosen speaker is playing", len(played) == 1, str(result)[:200])

    await asyncio.sleep(4)
    status = await asyncio.to_thread(srv._manager.status, speaker)
    check("the device reports a media state after the announcement",
          status["media"]["player_state"] is not None, str(status)[:200])
    srv._media_server.stop()
    srv._manager.close()


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true",
                        help="also run checks that need internet (no sound).")
    parser.add_argument("--hardware", action="store_true",
                        help="also cast to a REAL speaker. Makes REAL sound.")
    parser.add_argument("--speaker", default="Kitchen speaker",
                        help="speaker used by the --hardware tier.")
    args = parser.parse_args()

    print("googlecast-mcp evaluation")
    print(f"tiers: offline"
          + (" + online" if args.online else "")
          + (" + hardware" if args.hardware else ""))

    asyncio.run(run_offline())
    if args.online:
        asyncio.run(run_online())
    if args.hardware:
        asyncio.run(run_hardware(args.speaker))

    total = len(PASSED) + len(FAILED)
    print(f"\n{len(PASSED)}/{total} checks passed")
    if FAILED:
        print("\nfailed:")
        for name, detail in FAILED:
            print(f"  - {name}" + (f"  ({detail})" if detail else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
