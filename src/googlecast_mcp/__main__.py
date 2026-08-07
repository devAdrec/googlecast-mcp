"""CLI entrypoint. Selects the MCP transport and runs the server.

Usage:
    googlecast-mcp                       # stdio (default)
    googlecast-mcp --transport http      # streamable HTTP on :8000
    googlecast-mcp --transport sse       # legacy SSE on :8000
    googlecast-mcp --transport http --host 0.0.0.0 --port 9000
"""

from __future__ import annotations

import argparse

from mcp.server.transport_security import TransportSecuritySettings

from .media_server import lan_ip
from .server import _manager, _media_server, mcp


def _run_with_cors(origins: list[str]) -> None:
    """Serve the streamable-HTTP app with CORS headers attached.

    The SDK builds no CORS response, so a browser-based client fails its
    preflight and reports only "Failed to fetch". Wrapping the Starlette app
    adds the headers, including exposing Mcp-Session-Id — a browser cannot
    read that header, and so cannot continue a session, unless it is exposed.
    """
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware

    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id", "mcp-session-id"],
    )
    uvicorn.run(app, host=mcp.settings.host, port=mcp.settings.port, log_level="info")


def _transport_security(
    bind_host: str, extra_hosts: list[str], origins: list[str] | None = None
) -> TransportSecuritySettings:
    """Allow LAN clients through the SDK's DNS-rebinding protection.

    The SDK only trusts loopback by default, so a remote MCP client is
    answered with 421 Misdirected Request. Rather than disabling the check,
    this widens it to the addresses this host is actually reachable at.
    """
    hosts = ["127.0.0.1", "localhost", "[::1]", lan_ip()]
    # A wildcard bind is not itself an address clients connect to.
    if bind_host not in ("0.0.0.0", "::"):
        hosts.append(bind_host)
    hosts.extend(extra_hosts)

    unique = list(dict.fromkeys(h for h in hosts if h))
    allowed_origins = [
        f"{scheme}://{h}{suffix}"
        for h in unique
        for scheme in ("http", "https")
        for suffix in ("", ":*")
    ]
    allowed_origins.extend(origins or [])
    return TransportSecuritySettings(
        # Bare host too: a proxy on the default port sends no ":port" suffix.
        allowed_hosts=[p for h in unique for p in (h, f"{h}:*")],
        # https as well, for when a reverse proxy terminates TLS in front.
        allowed_origins=list(dict.fromkeys(allowed_origins)),
    )


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
    parser.add_argument(
        "--media-port",
        type=int,
        default=None,
        help=(
            "Fixed port for the HTTP server that hands TTS audio to speakers "
            "(default: a random free port). Pin it to write one firewall rule."
        ),
    )
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        metavar="HOST",
        help=(
            "Extra hostname or IP that clients may use to reach this server "
            "(repeatable). Loopback and this machine's LAN address are always "
            "allowed."
        ),
    )
    parser.add_argument(
        "--json-response",
        action="store_true",
        help=(
            "Reply with plain JSON instead of an SSE-framed body. Simple MCP "
            "clients that cannot parse 'event: message' framing need this."
        ),
    )
    parser.add_argument(
        "--stateless",
        action="store_true",
        help=(
            "Do not require clients to carry an Mcp-Session-Id between "
            "requests. Needed by clients that ignore the session header."
        ),
    )
    parser.add_argument(
        "--cors-origin",
        action="append",
        default=[],
        metavar="ORIGIN",
        help=(
            "Browser origin allowed to call this server, e.g. "
            "http://192.168.1.128:8080 (repeatable, '*' for any). Needed by "
            "browser-based MCP clients; without it the browser blocks the "
            "request and reports only 'Failed to fetch'."
        ),
    )
    args = parser.parse_args()

    if args.media_port is not None:
        _media_server.set_port(args.media_port)

    if args.transport in ("http", "sse"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        # A browser sends its page origin, which must pass the SDK's check too.
        mcp.settings.transport_security = _transport_security(
            args.host, args.allow_host, args.cors_origin
        )
        mcp.settings.json_response = args.json_response
        mcp.settings.stateless_http = args.stateless

    if args.transport == "http" and args.cors_origin:
        _run_with_cors(args.cors_origin)
        return

    transport = "streamable-http" if args.transport == "http" else args.transport
    try:
        mcp.run(transport=transport)
    finally:
        _media_server.stop()
        _manager.close()


if __name__ == "__main__":
    main()
