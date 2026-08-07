"""Vietnamese text-to-speech via edge-tts.

edge-tts uses Microsoft Edge's online neural voices: no API key, no account,
and the Vietnamese voices are the most natural of the free options. Rendered
mp3 files are cached on disk, keyed by a hash of the text and voice settings,
so repeating the same announcement does not re-synthesize it.
"""

from __future__ import annotations

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

    communicate = edge_tts.Communicate(text, resolved, rate=rate, volume=volume)
    await communicate.save(str(path))
    if not path.exists() or path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        raise RuntimeError(f"TTS produced no audio for voice {resolved!r}")
    return path
