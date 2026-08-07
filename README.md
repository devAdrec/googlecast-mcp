# googlecast-mcp

An [MCP](https://modelcontextprotocol.io) server for discovering and controlling
Google Cast (Chromecast) devices on your local network, built on
[`pychromecast`](https://github.com/home-assistant-libs/pychromecast).

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
| `discover_devices(timeout=5.0)` | Scan the network for Cast devices. **Run this first.** |
| `list_devices()` | List devices already discovered this session (no re-scan). |
| `get_status(target)` | Current app + media status of a device. |
| `play_media(target, url, content_type?, title?)` | Cast a media URL and start playback. |
| `play(target)` / `pause(target)` / `stop(target)` | Playback control. |
| `seek(target, position_seconds)` | Seek to an absolute position. |
| `set_volume(target, level)` | Set volume (0.0–1.0, clamped). |
| `set_muted(target, muted)` | Mute / unmute. |
| `quit_app(target)` | Stop the running app; return device to idle. |

`target` is a device **friendly name** (e.g. `"Living Room TV"`) or its **uuid**,
as returned by `discover_devices`.

### Notes

- `play_media` URLs must be **publicly reachable by the Cast device** — the
  device fetches the media itself, not this server.
- `content_type` is guessed from the URL extension when omitted; pass it
  explicitly for streams without a recognizable extension (e.g. HLS behind a
  query string).

## Architecture

- `cast_manager.py` — thread-safe wrapper over `pychromecast`; owns discovery,
  the connected-device cache, and synchronous control methods.
- `server.py` — FastMCP tool definitions; offloads each blocking call to a
  worker thread via `asyncio.to_thread`.
- `__main__.py` — CLI entrypoint; selects transport and handles clean shutdown.

## License

MIT
