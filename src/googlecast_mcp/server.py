"""FastMCP server exposing Google Cast controls as MCP tools.

pychromecast calls are blocking, so every tool offloads them to a worker
thread via ``asyncio.to_thread`` to keep the MCP event loop responsive.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from .cast_manager import CastManager

mcp = FastMCP("googlecast-mcp")
_manager = CastManager()


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
