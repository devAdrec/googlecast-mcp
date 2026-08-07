"""FastMCP server exposing Google Cast controls as MCP tools.

pychromecast calls are blocking, so every tool offloads them to a worker
thread via ``asyncio.to_thread`` to keep the MCP event loop responsive.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import tts
from .cast_manager import CastManager
from .media_server import MediaServer

mcp = FastMCP("googlecast-mcp")
_manager = CastManager()
# Port 0 picks a free port; pin it (env var or --media-port) when running
# behind a firewall so the rule can be written once.
_media_server = MediaServer(
    tts.default_cache_dir(),
    port=int(os.environ.get("GOOGLECAST_MCP_MEDIA_PORT", "0")),
)

# Targets that mean "every speaker", in English and Vietnamese.
_ALL_KEYWORDS = {"all", "tất cả", "tat ca", "everyone", "*"}


@mcp.tool()
async def discover_devices(timeout: float = 5.0) -> list[dict[str, Any]]:
    """Scan the local network for Google Cast devices.

    Run this first. Returns each device's friendly_name, uuid, model, and
    address. Other tools accept either the friendly_name or uuid as ``target``.

    Args:
        timeout: Seconds to wait for devices to respond (default 5).
    """
    return await asyncio.to_thread(_manager.discover, timeout)


@mcp.tool()
async def list_devices() -> list[dict[str, Any]]:
    """List devices already discovered this session without re-scanning."""
    return await asyncio.to_thread(_manager.list_cached)


@mcp.tool()
async def list_speakers() -> list[dict[str, Any]]:
    """List known Google speakers and speaker groups (excludes video Chromecasts).

    Reads the saved device list, so it works without re-scanning. Scans once
    automatically if nothing has been discovered yet.
    """
    speakers = await asyncio.to_thread(_manager.list_speakers)
    if not speakers:
        await asyncio.to_thread(_manager.discover, 5.0)
        speakers = await asyncio.to_thread(_manager.list_speakers)
    return speakers


async def _select_targets(target: str | None) -> tuple[list[str], dict[str, Any] | None]:
    """Turn a ``target`` argument into concrete speaker names.

    Returns ``(names, prompt)``. When ``target`` is missing, ``names`` is empty
    and ``prompt`` holds the speaker list for the caller to ask the user about.
    """
    speakers = await list_speakers()
    names = [s["friendly_name"] for s in speakers]

    if target and target.strip():
        cleaned = target.strip()
        if cleaned.lower() in _ALL_KEYWORDS:
            return names, None
        # Accept a comma-separated list of devices.
        return [part.strip() for part in cleaned.split(",") if part.strip()], None

    if not names:
        return [], {
            "status": "no_speakers_found",
            "speakers": [],
            "message": "No Google speaker found on the network. Run discover_devices.",
        }

    return [], {
        "status": "needs_speaker_selection",
        "speakers": speakers,
        "message": (
            "No target given. Ask the user which speaker to play on, then call "
            "this tool again with target=<friendly_name>, a comma-separated "
            "list of names, or 'all' to play on every speaker. "
            f"Available: {', '.join(names)}."
        ),
    }


@mcp.tool()
async def say(
    text: str,
    target: str | None = None,
    voice: str = "female",
    rate: str = "+0%",
) -> dict[str, Any]:
    """Speak text out loud on Google speakers (Vietnamese supported).

    Converts the text to speech, serves the audio from this machine, and casts
    it to the chosen speakers. If ``target`` is omitted, no audio is played:
    the tool returns the list of speakers so you can ask the user which one to
    use (or "all").

    Args:
        text: What to say, e.g. Vietnamese text like "Cơm đã chín rồi".
        target: Speaker friendly_name or uuid, several separated by commas, or
            "all" for every speaker. Omit to be asked which speaker to use.
        voice: "female" (default), "male", or a full edge-tts voice id.
        rate: Speaking speed adjustment, e.g. "-20%" for slower, "+10%" faster.
    """
    targets, prompt = await _select_targets(target)
    if prompt is not None:
        return prompt

    audio_path = await tts.synthesize(text, voice=voice, rate=rate)
    url = await asyncio.to_thread(_media_server.url_for, audio_path)

    async def cast_to(name: str) -> dict[str, Any]:
        try:
            await asyncio.to_thread(
                _manager.play_media, name, url, "audio/mpeg", text[:60]
            )
            return {"speaker": name, "status": "playing"}
        except Exception as exc:  # one unreachable speaker must not fail the rest
            return {"speaker": name, "status": "error", "error": str(exc)}

    results = await asyncio.gather(*(cast_to(name) for name in targets))
    played = [r for r in results if r["status"] == "playing"]
    return {
        "status": "ok" if played else "failed",
        "text": text,
        "voice": tts.resolve_voice(voice),
        "audio_url": url,
        "results": list(results),
    }


@mcp.tool()
async def get_status(target: str) -> dict[str, Any]:
    """Get the current app and media status of a device.

    Args:
        target: Device friendly_name or uuid.
    """
    return await asyncio.to_thread(_manager.status, target)


@mcp.tool()
async def play_media(
    target: str,
    url: str,
    content_type: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Cast a media URL to a device and start playback.

    Args:
        target: Device friendly_name or uuid.
        url: Publicly reachable media URL (the device fetches it directly).
        content_type: MIME type, e.g. "video/mp4". Guessed from the URL if omitted.
        title: Optional title shown on the device.
    """
    return await asyncio.to_thread(
        _manager.play_media, target, url, content_type, title
    )


@mcp.tool()
async def play(target: str) -> str:
    """Resume playback on a device.

    Args:
        target: Device friendly_name or uuid.
    """
    await asyncio.to_thread(_manager.play, target)
    return "playing"


@mcp.tool()
async def pause(target: str) -> str:
    """Pause playback on a device.

    Args:
        target: Device friendly_name or uuid.
    """
    await asyncio.to_thread(_manager.pause, target)
    return "paused"


@mcp.tool()
async def stop(target: str) -> str:
    """Stop the current media on a device.

    Args:
        target: Device friendly_name or uuid.
    """
    await asyncio.to_thread(_manager.stop, target)
    return "stopped"


@mcp.tool()
async def seek(target: str, position_seconds: float) -> str:
    """Seek to an absolute position in the current media.

    Args:
        target: Device friendly_name or uuid.
        position_seconds: Position from the start, in seconds.
    """
    await asyncio.to_thread(_manager.seek, target, position_seconds)
    return f"seeked to {position_seconds}s"


@mcp.tool()
async def set_volume(target: str, level: float) -> str:
    """Set the device volume to an absolute level between 0.0 and 1.0.

    Args:
        target: Device friendly_name or uuid.
        level: Volume from 0.0 (silent) to 1.0 (max); values are clamped.
    """
    applied = await asyncio.to_thread(_manager.set_volume, target, level)
    return f"volume set to {applied:.2f}"


@mcp.tool()
async def set_muted(target: str, muted: bool) -> str:
    """Mute or unmute a device.

    Args:
        target: Device friendly_name or uuid.
        muted: True to mute, False to unmute.
    """
    await asyncio.to_thread(_manager.set_muted, target, muted)
    return "muted" if muted else "unmuted"


@mcp.tool()
async def quit_app(target: str) -> str:
    """Stop the running app and return the device to its idle screen.

    Args:
        target: Device friendly_name or uuid.
    """
    await asyncio.to_thread(_manager.quit_app, target)
    return "app quit"
