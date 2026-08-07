"""Thread-safe wrapper around pychromecast for device discovery and control.

pychromecast is a blocking, thread-based library that maintains persistent
socket connections to each device. This module centralizes discovery, caches
connected devices, and exposes small synchronous control methods. The MCP
server calls these from a worker thread (via ``asyncio.to_thread``) so the
event loop is never blocked.
"""

from __future__ import annotations

import threading
from typing import Any

import pychromecast


def _guess_content_type(url: str) -> str:
    """Best-effort MIME type from a media URL's extension."""
    lowered = url.lower().split("?", 1)[0]
    mapping = {
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
        ".mov": "video/quicktime",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".wav": "audio/wav",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".m3u8": "application/x-mpegURL",
    }
    for ext, mime in mapping.items():
        if lowered.endswith(ext):
            return mime
    return "video/mp4"


class DeviceNotFoundError(Exception):
    """Raised when a target device cannot be resolved among known devices."""


class CastManager:
    """Discovers and controls Google Cast devices, caching live connections."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # uuid (str) -> Chromecast
        self._devices: dict[str, Any] = {}
        self._browser: Any = None

    # -- discovery ---------------------------------------------------------

    def discover(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        """Scan the local network and refresh the cached device list.

        Returns a list of device info dicts. Devices already connected keep
        their existing connection; new ones are added to the cache.
        """
        casts, browser = pychromecast.get_chromecasts(timeout=timeout)
        with self._lock:
            # Stop any prior browser before replacing it.
            self._stop_browser_locked()
            self._browser = browser
            for cast in casts:
                uuid = str(cast.cast_info.uuid)
                # Keep an already-connected instance if we have one.
                self._devices.setdefault(uuid, cast)
            return [self._info(cast) for cast in self._devices.values()]

    def list_cached(self) -> list[dict[str, Any]]:
        """Return info for devices discovered so far without re-scanning."""
        with self._lock:
            return [self._info(cast) for cast in self._devices.values()]

    # -- resolution --------------------------------------------------------

    def _resolve(self, target: str) -> Any:
        """Find a cached device by UUID or (case-insensitive) friendly name."""
        with self._lock:
            if target in self._devices:
                return self._devices[target]
            lowered = target.strip().lower()
            for cast in self._devices.values():
                if str(cast.cast_info.uuid).lower() == lowered:
                    return cast
                if cast.cast_info.friendly_name.lower() == lowered:
                    return cast
        raise DeviceNotFoundError(
            f"Device {target!r} not found. Run discover_devices first, "
            "then use its friendly name or uuid."
        )

    def _connected(self, target: str) -> Any:
        """Resolve a device and ensure its connection is established."""
        cast = self._resolve(target)
        cast.wait(timeout=10)
        return cast

    # -- control -----------------------------------------------------------

    def status(self, target: str) -> dict[str, Any]:
        cast = self._connected(target)
        mc = cast.media_controller
        cast_status = cast.status
        media = mc.status
        return {
            "device": self._info(cast),
            "app": {
                "display_name": getattr(cast_status, "display_name", None),
                "app_id": getattr(cast_status, "app_id", None),
                "is_active_input": getattr(cast_status, "is_active_input", None),
                "volume_level": getattr(cast_status, "volume_level", None),
                "volume_muted": getattr(cast_status, "volume_muted", None),
            },
            "media": {
                "player_state": getattr(media, "player_state", None),
                "title": getattr(media, "title", None),
                "content_id": getattr(media, "content_id", None),
                "content_type": getattr(media, "content_type", None),
                "duration": getattr(media, "duration", None),
                "current_time": getattr(media, "current_time", None),
            },
        }

    def play_media(
        self,
        target: str,
        url: str,
        content_type: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        cast = self._connected(target)
        mc = cast.media_controller
        mc.play_media(
            url,
            content_type or _guess_content_type(url),
            title=title,
        )
        mc.block_until_active(timeout=10)
        return self.status(target)

    def play(self, target: str) -> None:
        self._connected(target).media_controller.play()

    def pause(self, target: str) -> None:
        self._connected(target).media_controller.pause()

    def stop(self, target: str) -> None:
        self._connected(target).media_controller.stop()

    def seek(self, target: str, position_seconds: float) -> None:
        self._connected(target).media_controller.seek(position_seconds)

    def set_volume(self, target: str, level: float) -> float:
        """Set volume to an absolute level in the range 0.0-1.0."""
        clamped = max(0.0, min(1.0, level))
        self._connected(target).set_volume(clamped)
        return clamped

    def set_muted(self, target: str, muted: bool) -> None:
        self._connected(target).set_volume_muted(muted)

    def quit_app(self, target: str) -> None:
        self._connected(target).quit_app()

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _info(cast: Any) -> dict[str, Any]:
        info = cast.cast_info
        return {
            "friendly_name": info.friendly_name,
            "uuid": str(info.uuid),
            "model_name": info.model_name,
            "manufacturer": info.manufacturer,
            "host": info.host,
            "port": info.port,
            "cast_type": info.cast_type,
        }

    def _stop_browser_locked(self) -> None:
        if self._browser is not None:
            try:
                self._browser.stop_discovery()
            except Exception:
                pass
            self._browser = None

    def close(self) -> None:
        """Disconnect all devices and stop discovery. Safe to call twice."""
        with self._lock:
            self._stop_browser_locked()
            for cast in self._devices.values():
                try:
                    cast.disconnect(blocking=False)
                except Exception:
                    pass
            self._devices.clear()
