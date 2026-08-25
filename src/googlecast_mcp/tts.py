"""Vietnamese text-to-speech via edge-tts.

edge-tts uses Microsoft Edge's online neural voices: no API key, no account,
and the Vietnamese voices are the most natural of the free options. Rendered
mp3 files are cached on disk, keyed by a hash of the text and voice settings,
so repeating the same announcement does not re-synthesize it.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path

import edge_tts

# Vietnamese neural voices offered by edge-tts.
VOICES = {
    "female": "vi-VN-HoaiMyNeural",
    "male": "vi-VN-NamMinhNeural",
}
DEFAULT_VOICE = VOICES["female"]

# Renders run one at a time: the upstream service refuses connections that
# arrive together, and a fan-out of announcements would otherwise mostly fail.
_synthesis_lock = asyncio.Lock()


def resolve_voice(voice: str | None) -> str:
    """Map "female"/"male" (or a full voice id) to an edge-tts voice name."""
    if not voice:
        return DEFAULT_VOICE
    return VOICES.get(voice.strip().lower(), voice)


def default_cache_dir() -> Path:
    """Directory holding rendered mp3 files; the media server serves it."""
    override = os.environ.get("GOOGLECAST_MCP_CACHE")
    base = Path(override).expanduser() if override else Path(tempfile.gettempdir()) / "googlecast-mcp-tts"
    base.mkdir(parents=True, exist_ok=True)
    return base


async def synthesize(
    text: str,
    voice: str | None = None,
    rate: str = "+0%",
    volume: str = "+0%",
    cache_dir: Path | None = None,
) -> Path:
    """Render ``text`` to an mp3 file and return its path.

    Args:
        text: The text to speak (Vietnamese, but any language its voice supports).
        voice: "female", "male", or a full edge-tts voice id.
        rate: Speaking rate adjustment, e.g. "-20%" or "+10%".
        volume: Synthesis volume adjustment, e.g. "+10%".
        cache_dir: Where to write the mp3 (defaults to the shared cache).
    """
    if not text or not text.strip():
        raise ValueError("text must not be empty")

    resolved = resolve_voice(voice)
    directory = cache_dir or default_cache_dir()
    key = hashlib.sha256(f"{resolved}|{rate}|{volume}|{text}".encode()).hexdigest()[:32]
    path = directory / f"{key}.mp3"

    # Reuse an existing render; a zero-byte file means a previous run failed.
    if path.exists() and path.stat().st_size > 0:
        return path

    # The service refuses connections that arrive together, so retrying alone
    # is not enough — the attempts have to stop overlapping. One at a time,
    # then back off between attempts. A partial file is always cleared first,
    # since save() can create the file and then fail, leaving an empty one.
    async with _synthesis_lock:
        # Another caller may have rendered it while we waited for the lock.
        if path.exists() and path.stat().st_size > 0:
            return path

        last_error: Exception | None = None
        for attempt in range(3):
            if attempt:
                await asyncio.sleep(2 * attempt)
            communicate = edge_tts.Communicate(text, resolved, rate=rate, volume=volume)
            try:
                await communicate.save(str(path))
            except Exception as exc:  # noqa: BLE001 - the library raises several types
                last_error = exc
                path.unlink(missing_ok=True)
                continue
            if path.exists() and path.stat().st_size > 0:
                return path
            path.unlink(missing_ok=True)
            last_error = RuntimeError(f"TTS produced no audio for voice {resolved!r}")

    raise RuntimeError(
        f"TTS failed for voice {resolved!r} after 3 attempts: {last_error}"
    ) from last_error
