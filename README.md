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

## Running as a service

On a home server that stays on, run it as a systemd service over HTTP so
clients on other machines can use it:

```bash
./scripts/service.sh install     # write the unit, enable at boot, start it
./scripts/service.sh status      # is it running?
./scripts/service.sh logs        # follow the journal
./scripts/service.sh stop        # / start / restart
./scripts/service.sh remove      # stop, disable, delete the unit
```

`install` needs `sudo` (it writes `/etc/systemd/system/`) and defaults to MCP
on port `8765` and audio on port `8766`. Override with environment variables:

```bash
MCP_PORT=9000 MEDIA_PORT=9001 ./scripts/service.sh install
```

The service must run on a machine on the **same LAN as the speakers**:
discovery uses mDNS, and the speakers fetch the audio back from it. Allow both
ports through the firewall if one is active.

## Client configuration (remote, over HTTP)

Point the client at the service's LAN address:

```
http://<server-ip>:8765/mcp
```

Claude Desktop's **Add custom connector** field only accepts `https` URLs, so a
plain-HTTP server on the LAN cannot be pasted there. Bridge it with the
`mcp-remote` stdio proxy instead — add this to `claude_desktop_config.json`
(**Settings → Developer → Edit Config**) on the client machine:

```json
{
  "mcpServers": {
    "googlecast": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://<server-ip>:8765/mcp", "--allow-http"]
    }
  }
}
```

This needs Node.js on the client machine. Restart Claude Desktop afterwards.

The MCP SDK rejects requests whose `Host` header it does not trust (a
DNS-rebinding defence), answering `421 Misdirected Request`. Loopback and this
machine's LAN address are allowed automatically; if clients reach the server
under another name, add it with `--allow-host myserver.local`.

## Client configuration (local, stdio)

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
  your LAN address. The port is random by default; pin it with `--media-port`
  (or `GOOGLECAST_MCP_MEDIA_PORT`) so a firewall rule can be written once.

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
- `__main__.py` — CLI entrypoint; selects transport, widens the SDK's trusted
  hosts to the LAN, and handles clean shutdown.
- `scripts/service.sh` — systemd install/remove/start/stop/restart/status/logs.

## License

MIT
