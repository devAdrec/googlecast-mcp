"""Persistent storage for discovered Cast devices.

Discovery is slow and mDNS is not always reliable, so the devices found by a
scan are written to a small JSON file. That way a fresh server process still
knows which speakers exist on the LAN without scanning first.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

# Cast types that are speakers (as opposed to video Chromecasts / TVs).
SPEAKER_CAST_TYPES = ("audio", "group")


def default_store_path() -> Path:
    """Where the device list lives; override with GOOGLECAST_MCP_STORE."""
    override = os.environ.get("GOOGLECAST_MCP_STORE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".googlecast-mcp" / "speakers.json"


def is_speaker(device: dict[str, Any]) -> bool:
    """True for audio devices and speaker groups."""
    return device.get("cast_type") in SPEAKER_CAST_TYPES


class SpeakerStore:
    """Reads and writes the cached device list, keyed by device uuid."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or default_store_path()
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> list[dict[str, Any]]:
        """Return the saved devices, or an empty list if nothing is stored."""
        with self._lock:
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return []
        devices = raw.get("devices") if isinstance(raw, dict) else None
        return devices if isinstance(devices, list) else []

    def save(self, devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge ``devices`` into the store by uuid and persist the result.

        Merging (rather than replacing) keeps devices that were simply asleep
        or missed by a single mDNS scan.
        """
        merged: dict[str, dict[str, Any]] = {}
        for device in self.load() + devices:
            uuid = device.get("uuid")
            if uuid:
                merged[uuid] = {**merged.get(uuid, {}), **device}

        payload = {
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "devices": list(merged.values()),
        }
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # Write-then-rename so a crash cannot leave a truncated file.
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)
        return payload["devices"]

    def speakers(self) -> list[dict[str, Any]]:
        """Saved devices that are speakers or speaker groups."""
        return [d for d in self.load() if is_speaker(d)]
