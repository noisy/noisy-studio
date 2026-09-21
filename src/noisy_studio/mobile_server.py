"""Standalone mobile dashboard server.

Runs as its own process (default port 8770), independent of the listener
daemon — restart it freely without forcing agents to reconnect. Serves the
mobile page and proxies /api/status and /api/active-agent to the daemon
(127.0.0.1:8765), so it can be exposed via ngrok without exposing the daemon.

Run: uv run noisy-studio-mobile   (then: ngrok http 8770)
"""

import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from noisy_studio.listener.mobile import MOBILE_HTML

MOBILE_PORT = int(os.environ.get("NOISY_STUDIO_MOBILE_PORT", "8770"))
DAEMON = f"http://127.0.0.1:{os.environ.get('NOISY_STUDIO_LISTENER_PORT', '8765')}"


def _daemon_get(path: str) -> bytes:
    with urllib.request.urlopen(f"{DAEMON}{path}", timeout=1.0) as r:
        return r.read()


def _daemon_post(path: str, body: bytes) -> bytes:
    req = urllib.request.Request(f"{DAEMON}{path}", data=body, method="POST")
    with urllib.request.urlopen(req, timeout=1.0) as r:
        return r.read()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._send(200, "text/html; charset=utf-8", MOBILE_HTML.encode())
        elif self.path == "/api/status":
            self._proxy(lambda: _daemon_get("/status"))
        else:
            self._send(404, "application/json", b'{"error":"not found"}')

    def do_POST(self) -> None:
        if self.path == "/api/active-agent":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b"{}"
            self._proxy(lambda: _daemon_post("/active-agent", body))
        else:
            self._send(404, "application/json", b'{"error":"not found"}')

    def _proxy(self, call) -> None:
        try:
            self._send(200, "application/json", call())
        except (urllib.error.URLError, OSError):
            self._send(502, "application/json", b'{"error":"daemon unreachable"}')

    def _send(self, status: int, ctype: str, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        pass


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", MOBILE_PORT), Handler)
    print(f"noisy-studio-mobile on http://0.0.0.0:{MOBILE_PORT} → daemon {DAEMON}", flush=True)
    print(f"Expose it:  ngrok http {MOBILE_PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
