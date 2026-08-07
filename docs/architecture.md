# Architecture and technical notes

How `googlecast-mcp` turns a sentence of text into sound coming out of a Google
speaker, why each piece exists, and what bites in production.

## The core problem

A Cast device is not a speaker you write bytes to. It is a networked player
that **fetches media itself over HTTP**. That single fact shapes the design:

- A local file path is useless to it — `file:///tmp/hello.mp3` means nothing on
  the device.
- The audio must be reachable from the device, at an address on its network.
- So a server that speaks text must also *host* the audio it produced.

Everything below follows from that.

## Request flow

```
MCP client                                    (Claude Desktop / Claude Code)
    │  say("Cơm đã chín rồi", target="Kitchen speaker")
    ▼
server.py            resolve the target, or ask the user which speaker
    │
    ▼
tts.py               edge-tts renders Vietnamese → mp3, cached by content hash
    │                     /tmp/googlecast-mcp-tts/<sha256>.mp3
    ▼
media_server.py      start (once) an HTTP server on the LAN address
    │                     → http://192.168.1.128:8766/<sha256>.mp3
    ▼
cast_manager.py      pychromecast: connect, play_media(url, "audio/mpeg")
    │
    ▼
Speaker              fetches the URL itself ──────► back to media_server.py
```

The final arrow is the one people miss: the speaker opens a connection *back*
to this machine. If the audio port is unreachable, the cast still "succeeds"
and the speaker stays silent.

## Modules

| Module | Responsibility | Why it is separate |
|---|---|---|
| `cast_manager.py` | pychromecast wrapper: discovery, live connection cache, controls | pychromecast is blocking and thread-based; isolating it keeps that off the event loop |
| `speaker_store.py` | Persist devices to JSON, classify speakers vs video devices | Discovery is slow and mDNS is lossy; a restart should not lose the device list |
| `tts.py` | Vietnamese text → mp3, on-disk cache | The TTS backend is the most likely thing to be swapped |
| `media_server.py` | Serve the audio cache on the LAN address | The speakers need somewhere to fetch from |
| `server.py` | MCP tool surface, target selection, fan-out to several speakers | Thin: policy only, no protocol details |
| `__main__.py` | Transport selection, host trust, clean shutdown | Deployment concerns, not application logic |

### Threading model

pychromecast keeps persistent sockets and blocks. Every tool is `async`, and
every call into `CastManager` goes through `asyncio.to_thread`, so a slow or
unreachable device never stalls the MCP event loop. `CastManager` guards its
device cache with an `RLock`; `MediaServer` runs on a daemon thread.

Casting to several speakers uses `asyncio.gather`, so `target="all"` takes as
long as the slowest device, not the sum. One unreachable speaker returns an
error entry for itself and does not fail the others.

### Caching

TTS output is keyed by `sha256(voice|rate|volume|text)`. Repeating an
announcement costs nothing and needs no network. A zero-byte file is treated as
a failed render and deleted rather than served.

### Device resolution

`target` matches a uuid or a friendly name, case-insensitively. If nothing
matches in the live cache, resolution triggers **one** rescan and retries, so
callers working from the saved list never have to discover explicitly. The
error message lists the known devices instead of only saying "not found".

Speakers are distinguished from video devices by `cast_type`: `audio` and
`group` are speakers, `cast` is a Chromecast, Nest Hub, or TV.

## Deployment

Currently deployed on the LAN host `192.168.1.128`:

| Piece | Value |
|---|---|
| systemd unit | `googlecast-mcp.service`, enabled at boot |
| Command | `uv run --directory /storage/apps/mcp/googlecast_mcp googlecast-mcp --transport http --host 0.0.0.0 --port 8765 --allow-host google-cast.adrec.cloud` |
| MCP port | `8765` (proxied) |
| Audio port | `8766`, fixed via `GOOGLECAST_MCP_MEDIA_PORT` (**not** proxied) |
| Public URL | `https://google-cast.adrec.cloud/mcp`, Let's Encrypt |
| nginx vhost | `/etc/nginx/conf.d/adrec_cloud.conf` |
| Device list | `~/.googlecast-mcp/speakers.json` |

Manage it with `scripts/service.sh install|remove|start|stop|restart|status|logs`.

### Ports

Both must be reachable **from the speakers' network**. The audio port is the
one people forget, because nothing complains loudly when it is blocked — the
cast is accepted and the speaker simply plays nothing.

## Things that bite

**The MCP SDK only trusts loopback.** It ships DNS-rebinding protection and
answers `421 Misdirected Request` to any `Host` it does not recognise. Serving
on `0.0.0.0` is not enough; the allowlist is widened at startup to this
machine's LAN address, plus anything passed with `--allow-host`. Both `http`
and `https` origins are allowed, since a TLS-terminating proxy changes the
scheme the client reports.

**nginx buffering breaks streaming.** Streamable HTTP holds the response open
and pushes events. With default buffering the client hangs with no error at
all. `proxy_buffering off` plus long `proxy_read_timeout` is required.

**Underscores make https impossible.** Public CAs refuse to issue certificates
for hostnames containing `_`, so a name like `google_cast.example.com` can
never be used where https is required — as it is in Claude Desktop's
custom-connector field. Use a hyphen.

**Cast devices can wedge.** A device can answer mDNS and ping while refusing
TCP on port 8009, which surfaces as `Execution of wait timed out after 10 s`.
Observed on two Nest Hubs simultaneously; a reboot restored both. Check with
`nc -z <ip> 8009` before suspecting this code.

**`mcp[cli]` must stay pinned below 2.0.** An unrelated package also named
`mcp` occupies version 2.0.0 on PyPI, with a different layout and typosquatted
dependencies (`httpx2`, `mcp-types`). The pin in `pyproject.toml` is
deliberate.

## Security model

There is **none at the application layer**. Any client that reaches `/mcp` can
enumerate the devices and play audio in the house. That is acceptable on a
trusted LAN and not acceptable on a public domain.

The deployed hostname resolves publicly, so access should be restricted at the
proxy:

```nginx
allow 192.168.0.0/16;
deny  all;
```

If remote access is genuinely needed, add authentication at the proxy (a bearer
token or mTLS) rather than leaving the endpoint open.

The audio server serves a single directory of generated mp3 files and is not
otherwise hardened; it should not be exposed beyond the LAN.

## Possible next steps

Not implemented, in rough order of usefulness:

- Unit tests with a mocked `pychromecast` — currently verification is manual
  against real hardware.
- Restore the previous volume and resume interrupted media after an
  announcement.
- An offline TTS fallback (Piper) for when the internet is down.
- Pruning the TTS cache, which currently grows without bound.
