# Handoff — googlecast-mcp scaffold

**Date:** 2026-08-07 11:57 (Asia/Saigon) · **Branch:** main · **Git:** no commits yet (all files untracked) · **Purpose:** resume in VS Code extension session.

## What this is
MCP server to discover + control Google Cast (Chromecast) devices on the LAN.
Stack: **Python 3.12 · uv · official MCP SDK `mcp[cli]` 1.29.0 (FastMCP) · pychromecast 14 · stdio + HTTP/SSE transports.**

## Current state: scaffolded + smoke-verified, NOT hardware-tested, NOT committed

### Files (all new, untracked)
```
pyproject.toml               # uv project; requires-python >=3.11; script entry: googlecast-mcp
.python-version              # 3.12
README.md                    # install, client config, tool table, architecture
uv.lock                      # resolved lockfile
src/googlecast_mcp/
  __init__.py                # __version__ = 0.1.0
  cast_manager.py            # CastManager: thread-safe pychromecast wrapper (discovery, device cache, controls) + _guess_content_type + DeviceNotFoundError
  server.py                  # FastMCP `mcp` + module-level `_manager`; 11 @mcp.tool()s; blocking calls via asyncio.to_thread
  __main__.py                # main(): argparse --transport {stdio,http,sse} --host --port; maps http->streamable-http; _manager.close() in finally
```

### 11 tools (server.py)
discover_devices, list_devices, get_status, play_media, play, pause, stop, seek, set_volume, set_muted, quit_app.
`target` arg = device friendly_name or uuid (resolved case-insensitively against discovered cache).

### Verified
- `uv sync` clean; all 11 tools register via real FastMCP (`mcp.list_tools()`).
- `_guess_content_type` cases pass; resolving unknown device raises DeviceNotFoundError.
- CLI `--help` works; HTTP transport binds `:8765`, `/mcp` alive (406 w/o Accept header = expected); clean shutdown. No leftover bg processes.

## ⚠️ Supply-chain issue (resolved — do not regress)
`mcp[cli]>=1.2.0` originally resolved to a **PyPI impostor `mcp` 2.0.0** (no `mcp.server.fastmcp`; pulls `httpx2` typosquat + `mcp-types`). Fixed by pinning **`mcp[cli]>=1.13,<2`** in pyproject.toml (comment explains why). Verified real SDK now depends on `httpx` not `httpx2`. Also in project memory: `pypi-mcp-impostor.md`. **Keep the `<2` pin.**

## How to run
```bash
uv run googlecast-mcp                      # stdio (default)
uv run googlecast-mcp --transport http --port 8000
uv run googlecast-mcp --transport sse
```
Client (stdio) config example is in README.md.

## Next steps (none started)
1. **Initial git commit** — user asked; awaiting go. Suggested: `feat: scaffold google cast mcp server`. `.gitignore` already ignores `.claude/`; consider adding `__pycache__/`, `.venv/`.
2. **Live hardware test** on a LAN with a real Chromecast (discovery/play_media unverified against hardware).
3. Optional: unit tests mocking pychromecast; playlist/queue support; play/pause toggle.

## Open questions
- Commit now or adjust tool set first? (unanswered)
- `.gitignore` currently only `.claude/` — add `.venv/`, `__pycache__/` before committing?
