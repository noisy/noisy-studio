"""Live dashboard snapshots; this WebSocket never carries audio."""
from __future__ import annotations
import json
import os
import threading
from collections.abc import Callable

STATE_PORT_OFFSET = 1  # WS lives one port above the HTTP API
STATE_PATH = "/state"   # same port, this path: the pushed state stream (#73)
STATE_PUSH_INTERVAL_SECONDS = 0.1
# Fields that change on every tick by nature (clocks, meter levels). A change
# in ONLY these is not "something happened"; they ride along with real
# changes and otherwise refresh at this relaxed cadence.
STATE_VOLATILE_KEYS = frozenset({"nudge_clocks", "mic_level"})
STATE_VOLATILE_INTERVAL_SECONDS = 1.0


def snapshot_digest(snapshot: dict) -> int:
    """Identity of a snapshot with the volatile fields masked out - equal
    digests mean nothing the dashboard should redraw for has changed."""
    status = snapshot.get("status") or {}
    stable = {k: v for k, v in status.items() if k not in STATE_VOLATILE_KEYS}
    return hash(json.dumps({"status": stable, "utterances": snapshot.get("utterances")}, sort_keys=True, default=str))


class StateStream:
    def __init__(self, snapshot: Callable[[], dict]):
        self._snapshot = snapshot

    def _handle(self, ws):
        if getattr(getattr(ws, 'request', None), 'path', '') != STATE_PATH:
            ws.close(code=1008, reason='Only dashboard state updates are supported')
            return
        self._serve_state(ws)

    def _serve_state(self, ws) -> None:  # pragma: no cover — thin I/O shell
        """Push the daemon's whole state whenever it changes (#73).

        The dashboard used to poll /status and merge; every stale-strip bug
        came from that merge. Here the client gets a full snapshot on connect
        and a new full snapshot whenever anything differs, and renders
        exactly that. A JSON digest decides "differs", so no state mutation
        anywhere has to remember to signal - correctness over cleverness.
        Cadence is bounded by STATE_PUSH_INTERVAL_SECONDS.
        """
        if self._snapshot is None:
            ws.send(json.dumps({"type": "error", "reason": "state stream not configured"}))
            return
        import time as _time

        last_digest = None
        last_sent_at = 0.0
        while True:
            try:
                snapshot = self._snapshot()
                digest = snapshot_digest(snapshot)
                payload = json.dumps(snapshot)
            except Exception as error:  # a broken builder must not kill the state stream
                payload = json.dumps({"type": "error", "reason": str(error)[:200]})
                digest = None
            now = _time.monotonic()
            meaningful = digest != last_digest
            volatile_due = now - last_sent_at >= STATE_VOLATILE_INTERVAL_SECONDS
            if meaningful or volatile_due:
                ws.send(payload)
                last_digest = digest
                last_sent_at = now
            try:
                # Client messages are heartbeats or nothing; a closed socket
                # raises here and ends the loop.
                ws.recv(timeout=STATE_PUSH_INTERVAL_SECONDS)
            except TimeoutError:
                continue
            except Exception:
                return

    def serve_forever(self, port: int) -> None:  # pragma: no cover — thread shell
        from websockets.sync.server import serve

        # Same bind rule as the HTTP API: loopback by default, explicitly overridable.
        host = os.environ.get("NOISY_STUDIO_BIND", "127.0.0.1")
        with serve(self._handle, host, port) as server:
            server.serve_forever()


def start_state_stream(http_port: int, snapshot: Callable[[], dict]) -> StateStream:
    stream = StateStream(snapshot)
    threading.Thread(target=stream.serve_forever, args=(http_port + STATE_PORT_OFFSET,), daemon=True).start()
    return stream
