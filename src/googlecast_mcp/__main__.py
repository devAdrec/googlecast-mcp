"""CLI entrypoint. Selects the MCP transport and runs the server.

Usage:
    googlecast-mcp                       # stdio (default)
    googlecast-mcp --transport http      # streamable HTTP on :8000
    googlecast-mcp --transport sse       # legacy SSE on :8000
    googlecast-mcp --transport http --host 0.0.0.0 --port 9000
"""

from __future__ import annotations

import argparse

from .server import _manager, _media_server, mcp


def main() -> None:
    parser = argparse.ArgumentParser(prog="googlecast-mcp")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="MCP transport to serve (default: stdio).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for http/sse transports (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for http/sse transports (default: 8000).",
    )
    args = parser.parse_args()

    if args.transport in ("http", "sse"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port

    transport = "streamable-http" if args.transport == "http" else args.transport
    try:
        mcp.run(transport=transport)
    finally:
        _media_server.stop()
        _manager.close()


if __name__ == "__main__":
    main()
