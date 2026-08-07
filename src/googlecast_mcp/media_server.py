"""Small HTTP server that hands rendered audio files to Cast devices.

A Cast device fetches media over the network by itself, so a local file path
is useless to it. This serves the TTS cache directory on the machine's LAN
address and produces URLs the speaker can actually reach.
"""

from __future__ import annotations

import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote


def lan_ip() -> str:
    """Best-effort LAN address of this machine, as seen by other devices.

    Opens a UDP socket toward a public address to learn which local interface
    the kernel would route through. No packets are actually sent.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class _QuietHandler(SimpleHTTPRequestHandler):
    """File handler that does not write a request log to stderr.

    stderr is part of the stdio MCP transport's channel, so noise there is
    worth avoiding.
    """

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


class MediaServer:
    """Serves a directory over HTTP on the LAN. Started lazily, once."""

    def __init__(self, directory: Path, host: str | None = None, port: int = 0) -> None:
        self._directory = directory
        self._host = host or lan_ip()
        self._requested_port = port
        self._lock = threading.Lock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the server if it is not already running."""
        with self._lock:
            if self._httpd is not None:
                return
            self._directory.mkdir(parents=True, exist_ok=True)
            handler = partial(_QuietHandler, directory=str(self._directory))
            # Bind all interfaces: the advertised host is only how the speaker
            # reaches us, and it may differ from the routing interface.
            self._httpd = ThreadingHTTPServer(("0.0.0.0", self._requested_port), handler)
            self._thread = threading.Thread(
                target=self._httpd.serve_forever,
                name="googlecast-mcp-media",
                daemon=True,
            )
            self._thread.start()

    @property
    def port(self) -> int:
        """Actual bound port (meaningful only after start())."""
        if self._httpd is None:
            return self._requested_port
        return self._httpd.server_address[1]

    def url_for(self, path: Path) -> str:
        """Public URL for a file inside the served directory."""
        self.start()
        relative = path.relative_to(self._directory)
        return f"http://{self._host}:{self.port}/{quote(relative.as_posix())}"

    def stop(self) -> None:
        """Shut the server down. Safe to call when not running."""
        with self._lock:
            if self._httpd is None:
                return
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
            self._thread = None
