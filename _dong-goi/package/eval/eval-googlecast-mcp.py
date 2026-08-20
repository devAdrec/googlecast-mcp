#!/usr/bin/env python3
"""Eval harness for googlecast-mcp.

Two tiers, split by side effect:

  default        offline. No network cast, no sound, no speaker required.
                 Safe on any machine, any time, in CI.
  --online       adds the edge-tts synthesis check. Needs internet. Still
                 makes no sound and touches no speaker.
  --hardware     adds real casting to a real speaker. THIS MAKES NOISE in
                 someone's home. Opt-in only, never the default.

Run:
    uv run --directory <repo> python _dong-goi/package/eval/eval-googlecast-mcp.py
    ... --online
    ... --hardware --speaker "Kitchen speaker"

Exit code 0 if every check passed, 1 otherwise.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"FAIL  {name}  {detail}")


def check_raises(name: str, fn, exc: type[BaseException]) -> None:
    try:
        fn()
    except exc:
        check(name, True)
    except BaseException as other:  # noqa: BLE001
        check(name, False, f"raised {type(other).__name__}, expected {exc.__name__}")
    else:
        check(name, False, f"did not raise {exc.__name__}")


# --------------------------------------------------------------------------
# Fixtures: a fake speaker list shaped exactly like the real store's records.
# "Family speaker group" and "Kitchen speaker" share a host on purpose — that
# is the real-world condition that made the "all" duplicate-stream bug audible.
# --------------------------------------------------------------------------

KITCHEN = {
    "friendly_name": "Kitchen speaker",
    "uuid": "11111111-1111-1111-1111-111111111111",
    "cast_type": "audio",
    "host": "192.168.1.22",
    "port": 8009,
}
WORKING = {
    "friendly_name": "Working display",
    "uuid": "22222222-2222-2222-2222-222222222222",
    "cast_type": "audio",
    "host": "192.168.1.23",
    "port": 8009,
}
GROUP = {
    "friendly_name": "Family speaker group",
    "uuid": "33333333-3333-3333-3333-333333333333",
    "cast_type": "group",
    "host": "192.168.1.22",
    "port": 8009,
}
TV = {
    "friendly_name": "Living room TV",
    "uuid": "44444444-4444-4444-4444-444444444444",
    "cast_type": "cast",
    "host": "192.168.1.24",
    "port": 8009,
}
FAKE_SPEAKERS = [KITCHEN, WORKING, GROUP]


class Spy:
    """Records calls so a check can assert something did NOT happen."""

    def __init__(self, result=None, fail_for=None):
        self.calls: list[tuple] = []
        self._result = result
        self._fail_for = fail_for or set()

    async def async_call(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self._result

    def sync_call(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if args and args[0] in self._fail_for:
            raise RuntimeError(f"wait timed out after 10 s: {args[0]}")
        return self._result


# --------------------------------------------------------------------------
# Tier 1 — offline
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


def run_offline() -> None:
    # 1. The package imports at all — a broken import is the cheapest failure
    #    to catch and the one that takes a service down hardest.
    import googlecast_mcp.server as server  # noqa: PLC0415
    from googlecast_mcp import tts  # noqa: PLC0415
    from googlecast_mcp.cast_manager import _guess_content_type  # noqa: PLC0415
    from googlecast_mcp.speaker_store import is_speaker  # noqa: PLC0415
    from googlecast_mcp.__main__ import _transport_security  # noqa: PLC0415

    check("import: server module loads", True)

    # 2. Tool surface — the contract every MCP client sees.
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    check("tools: exactly 13 registered", len(tools) == 13, f"got {len(tools)}")
    check("tools: names match the documented set", names == EXPECTED_TOOLS,
          f"missing={EXPECTED_TOOLS - names} extra={names - EXPECTED_TOOLS}")
    check("tools: every tool has a description",
          all((t.description or "").strip() for t in tools))

    # 3. No speaker chosen => ask, and cause NO side effect. This is the
    #    behavioural requirement #3, and the one with physical consequences.
    tts_spy = Spy(result=Path("/tmp/never.mp3"))
    cast_spy = Spy()
    orig_synth, orig_play = tts.synthesize, server._manager.play_media
    orig_list = server.list_speakers
    try:
        tts.synthesize = tts_spy.async_call
        server.tts.synthesize = tts_spy.async_call
        server._manager.play_media = cast_spy.sync_call

        async def fake_list():
            return list(FAKE_SPEAKERS)

        server.list_speakers = fake_list

        res = asyncio.run(server.say("Cơm đã chín rồi"))
        check("say without a speaker: returns needs_speaker_selection",
              res.get("status") == "needs_speaker_selection", str(res.get("status")))
        check("say without a speaker: lists the speakers to choose from",
              len(res.get("speakers", [])) == 3)
        check("say without a speaker: does NOT synthesize", not tts_spy.calls)
        check("say without a speaker: does NOT cast", not cast_spy.calls)

        # 4. No speakers known at all => a different, actionable answer.
        async def empty_list():
            return []

        server.list_speakers = empty_list
        res = asyncio.run(server.say("xin chào"))
        check("say with no speakers on the network: no_speakers_found",
              res.get("status") == "no_speakers_found", str(res.get("status")))
        check("say with no speakers: still no side effect",
              not tts_spy.calls and not cast_spy.calls)

        server.list_speakers = fake_list

        # 5. "all" must not hit a group and its members at once. The group and
        #    Kitchen share host 192.168.1.22; sending to both plays two streams
        #    through one physical speaker while the API reports "playing" for
        #    all of them — the API cannot see this, only an ear can.
        picked, prompt = asyncio.run(server._select_targets("all"))
        check("all: no speaker group included",
              "Family speaker group" not in picked, str(picked))
        check("all: every individual speaker included",
              set(picked) == {"Kitchen speaker", "Working display"}, str(picked))
        check("all: no duplicate physical device",
              len(picked) == len(set(picked)))
        check("all: returns no prompt", prompt is None)

        picked, _ = asyncio.run(server._select_targets("tất cả"))
        check("all: Vietnamese 'tất cả' means the same thing",
              set(picked) == {"Kitchen speaker", "Working display"}, str(picked))

        # 6. A group is still usable when asked for by name.
        picked, _ = asyncio.run(server._select_targets("Family speaker group"))
        check("group by name: still reachable",
              picked == ["Family speaker group"], str(picked))

        # 7. Comma-separated list.
        picked, _ = asyncio.run(
            server._select_targets("Kitchen speaker, Working display")
        )
        check("comma list: both speakers selected",
              picked == ["Kitchen speaker", "Working display"], str(picked))

        # 8. One dead speaker must not sink the rest.
        tts_spy2 = Spy(result=Path("/tmp/fake.mp3"))
        server.tts.synthesize = tts_spy2.async_call
        cast_spy2 = Spy(fail_for={"Ghost speaker"})
        server._manager.play_media = cast_spy2.sync_call
        server._media_server.url_for = lambda p: "http://192.168.1.128:8766/fake.mp3"
        res = asyncio.run(
            server.say("thử", "Kitchen speaker, Ghost speaker")
        )
        by_name = {r["speaker"]: r for r in res["results"]}
        check("failure isolation: overall status stays ok", res["status"] == "ok",
              str(res["status"]))
        check("failure isolation: the reachable speaker plays",
              by_name["Kitchen speaker"]["status"] == "playing")
        check("failure isolation: the dead one is reported, not raised",
              by_name["Ghost speaker"]["status"] == "error")
    finally:
        tts.synthesize = orig_synth
        server.tts.synthesize = orig_synth
        server._manager.play_media = orig_play
        server.list_speakers = orig_list

    # 9. Speaker vs video-device filter.
    check("is_speaker: audio is a speaker", is_speaker(KITCHEN))
    check("is_speaker: group is a speaker", is_speaker(GROUP))
    check("is_speaker: video cast is NOT a speaker", not is_speaker(TV))
    check("is_speaker: unknown record is not a speaker", not is_speaker({}))

    # 10. Content-type guessing.
    check("content type: .mp3 -> audio/mpeg",
          _guess_content_type("http://h/a.mp3") == "audio/mpeg")
    check("content type: .mp4 -> video/mp4",
          _guess_content_type("http://h/a.mp4") == "video/mp4")
    check("content type: query string ignored",
          _guess_content_type("http://h/a.mp3?x=1") == "audio/mpeg")
    check("content type: uppercase extension handled",
          _guess_content_type("http://h/A.MP3") == "audio/mpeg")
    check("content type: unknown falls back to video/mp4",
          _guess_content_type("http://h/a.qqq") == "video/mp4")

    # 11. Voice resolution.
    check("voice: default is the female Vietnamese voice",
          tts.resolve_voice(None) == "vi-VN-HoaiMyNeural")
    check("voice: 'female'", tts.resolve_voice("female") == "vi-VN-HoaiMyNeural")
    check("voice: 'male'", tts.resolve_voice("male") == "vi-VN-NamMinhNeural")
    check("voice: full id passes through",
          tts.resolve_voice("en-US-AriaNeural") == "en-US-AriaNeural")
    check("voice: empty string falls back to default",
          tts.resolve_voice("") == "vi-VN-HoaiMyNeural")

    # 12. Transport security. Both of these were real 421/403 outages:
    #     a TLS-terminating proxy changes the scheme to https, and a proxy on
    #     port 443 sends a Host header with no ":port" suffix.
    ts = _transport_security(
        "0.0.0.0", ["google-cast.adrec.cloud"], ["http://192.168.1.99:8383"]
    )
    hosts, origins = list(ts.allowed_hosts), list(ts.allowed_origins)
    check("allowlist: bare host with no port is allowed",
          "google-cast.adrec.cloud" in hosts, str(hosts))
    check("allowlist: host with any port is allowed",
          "google-cast.adrec.cloud:*" in hosts, str(hosts))
    check("allowlist: https origin present (proxy terminates TLS)",
          "https://google-cast.adrec.cloud" in origins, str(origins))
    check("allowlist: http origin present",
          "http://google-cast.adrec.cloud" in origins)
    check("allowlist: loopback still allowed", "127.0.0.1" in hosts)
    check("allowlist: wildcard bind is not itself an allowed host",
          "0.0.0.0" not in hosts, str(hosts))
    check("allowlist: browser origin passed through verbatim",
          "http://192.168.1.99:8383" in origins)

    # 13. Empty text must fail before anything is served or cast.
    check_raises("tts: empty text raises ValueError",
                 lambda: asyncio.run(tts.synthesize("")), ValueError)
    check_raises("tts: whitespace-only text raises ValueError",
                 lambda: asyncio.run(tts.synthesize("   ")), ValueError)


# --------------------------------------------------------------------------
# Tier 2 — online (internet, still silent)
# --------------------------------------------------------------------------


def run_online() -> None:
    import tempfile  # noqa: PLC0415

    from googlecast_mcp import tts  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        path = asyncio.run(
            tts.synthesize("Xin chào, đây là bài kiểm tra.", cache_dir=Path(tmp))
        )
        check("tts online: produced a non-empty mp3",
              path.exists() and path.stat().st_size > 0,
              f"{path} size={path.stat().st_size if path.exists() else 'missing'}")
        first = path.stat().st_mtime_ns
        again = asyncio.run(
            tts.synthesize("Xin chào, đây là bài kiểm tra.", cache_dir=Path(tmp))
        )
        check("tts online: identical text is served from cache",
              again == path and again.stat().st_mtime_ns == first)


# --------------------------------------------------------------------------
# Tier 3 — hardware (MAKES NOISE — opt-in only)
# --------------------------------------------------------------------------


def run_hardware(speaker: str) -> None:
    import googlecast_mcp.server as server  # noqa: PLC0415

    speakers = asyncio.run(server.list_speakers())
    names = [s["friendly_name"] for s in speakers]
    check("hardware: at least one speaker discovered", bool(speakers), str(names))
    check("hardware: the requested speaker is known", speaker in names, str(names))
    if speaker not in names:
        return
    res = asyncio.run(server.say("Đây là bài kiểm tra tự động.", speaker))
    check("hardware: say reports ok", res.get("status") == "ok", str(res))
    played = [r for r in res.get("results", []) if r["status"] == "playing"]
    check("hardware: the speaker is playing", len(played) == 1, str(res.get("results")))
    status = asyncio.run(server.get_status(speaker))
    check("hardware: device reports a player state",
          status["media"]["player_state"] is not None, str(status["media"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true",
                        help="also run the edge-tts check (needs internet, silent).")
    parser.add_argument("--hardware", action="store_true",
                        help="ALSO CAST TO A REAL SPEAKER — this makes noise.")
    parser.add_argument("--speaker", default="Kitchen speaker",
                        help="speaker name for --hardware.")
    args = parser.parse_args()

    print("== offline tier ==")
    run_offline()
    if args.online:
        print("== online tier (internet, no sound) ==")
        run_online()
    if args.hardware:
        print("== hardware tier (MAKES NOISE) ==")
        run_hardware(args.speaker)

    total = len(PASSED) + len(FAILED)
    print(f"\n{len(PASSED)}/{total} passed")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
