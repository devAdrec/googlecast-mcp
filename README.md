# googlecast-mcp

An [MCP](https://modelcontextprotocol.io) server that finds the Google speakers
on your local network and **speaks text out loud on them, in Vietnamese**, built
on [`pychromecast`](https://github.com/home-assistant-libs/pychromecast) and
[`edge-tts`](https://github.com/rany2/edge-tts).

```
say("Cơm đã chín rồi", target="Kitchen speaker")
```

It also exposes the usual Cast media controls (play a URL, pause, volume, …).

## Requirements

- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- The machine running the server must be on the **same local network** as the
  Cast devices (discovery uses mDNS/zeroconf).

## Install & run

```bash
uv sync

# stdio transport (default — for Claude Desktop/Code and most MCP clients)
uv run googlecast-mcp

# streamable HTTP transport
uv run googlecast-mcp --transport http --host 0.0.0.0 --port 8000

# legacy SSE transport
uv run googlecast-mcp --transport sse
```

## Client configuration (stdio)

Add to your MCP client config (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "googlecast": {
      "command": "uv",
      "args": ["run", "--directory", "/storage/apps/mcp/googlecast_mcp", "googlecast-mcp"]
    }
  }
}
```

## Tools

| Tool | Purpose |
|------|---------|
| `say(text, target?, voice="female", rate="+0%")` | **Speak text out loud.** Omit `target` to be asked which speaker. |
| `discover_devices(timeout=5.0)` | Scan the network for Cast devices and save them. |
| `list_speakers()` | Saved speakers and speaker groups only (no TVs); scans if empty. |
| `list_devices()` | All known devices, live + saved. |
| `get_status(target)` | Current app + media status of a device. |
| `play_media(target, url, content_type?, title?)` | Cast a media URL and start playback. |
| `play(target)` / `pause(target)` / `stop(target)` | Playback control. |
| `seek(target, position_seconds)` | Seek to an absolute position. |
| `set_volume(target, level)` | Set volume (0.0–1.0, clamped). |
| `set_muted(target, muted)` | Mute / unmute. |
| `quit_app(target)` | Stop the running app; return device to idle. |

`target` is a device **friendly name** (e.g. `"Living Room TV"`) or its **uuid**,
as returned by `discover_devices`.

### Speaking text (`say`)

- `target` accepts one speaker, several separated by commas, or `"all"` /
  `"tất cả"` for every speaker.
- **Omitting `target` never plays anything.** The tool returns the speaker list
  and asks the client to have the user pick one.
- `voice` is `"female"` (`vi-VN-HoaiMyNeural`, default), `"male"`
  (`vi-VN-NamMinhNeural`), or any full edge-tts voice id.
- Synthesis needs internet access (Microsoft Edge neural voices, no API key).
  Rendered mp3s are cached, so repeating a phrase is instant.
- The speaker fetches the audio from a small HTTP server this process starts on
  your LAN address, on a random port. Your firewall must allow that port from
  the local network.

### Notes

- `play_media` URLs must be **publicly reachable by the Cast device** — the
  device fetches the media itself, not this server.
- `content_type` is guessed from the URL extension when omitted; pass it
  explicitly for streams without a recognizable extension (e.g. HLS behind a
  query string).

## Architecture

- `cast_manager.py` — thread-safe wrapper over `pychromecast`; owns discovery,
  the connected-device cache, and synchronous control methods.
- `speaker_store.py` — persists discovered devices to
  `~/.googlecast-mcp/speakers.json` (override with `GOOGLECAST_MCP_STORE`), so a
  fresh process still knows the speakers.
- `tts.py` — Vietnamese text → mp3 via edge-tts, cached on disk (override the
  cache location with `GOOGLECAST_MCP_CACHE`).
- `media_server.py` — background HTTP server on the LAN address; Cast devices
  cannot read local file paths, so the audio must be served to them.
- `server.py` — FastMCP tool definitions; offloads each blocking call to a
  worker thread via `asyncio.to_thread`.
- `__main__.py` — CLI entrypoint; selects transport and handles clean shutdown.

## License

MIT
