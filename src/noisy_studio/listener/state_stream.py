"""Live dashboard state over WebSocket (#73); this socket never carries audio.

One broadcaster per daemon builds the state at most every
STATE_PUSH_INTERVAL_SECONDS while a dashboard is connected, compares it with
what it sent last, and pushes only what changed to every client.

Protocol v2 (requested with ``/state?v=2``):

- on connect: ``{"type": "snapshot", "v": 2, "seq": n, "status": {...},
  "utterances": [...], "events": [...]}`` - everything, once;
- afterwards: ``{"type": "patch", "v": 2, "seq": n + 1, ...}`` with any of
  ``status`` (ops: ``[path, value]`` sets, ``[path]`` deletes; dicts are
  diffed key by key, anything else is replaced whole), ``utterances``
  (``{"remove": [ids], "upsert": [items]}`` or ``{"replace": [...]}``) and
  ``events`` (new log entries). A client that sees a seq gap reconnects.

Protocol v1 (no ``v``): a full snapshot on every change, as before, so a
dashboard bundle older than the daemon keeps working.

The status is whatever GET /status returns - the stream never names a field,
so new /status fields reach the dashboard with no change here.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

STATE_PORT_OFFSET = 1  # WS lives one port above the HTTP API
STATE_PATH = "/state"   # same port, this path: the pushed state stream (#73)
STATE_PROTOCOL_VERSION = 2
LEGACY_PROTOCOL_VERSION = 1
STATE_PUSH_INTERVAL_SECONDS = 0.1
# Fields that change on every tick by nature (clocks, meter levels). A change
# in ONLY these is not "something happened"; they ride along with real
# changes and otherwise refresh at this relaxed cadence.
STATE_VOLATILE_KEYS = frozenset({"nudge_clocks", "mic_level"})
STATE_VOLATILE_INTERVAL_SECONDS = 1.0

StatusOp = list  # [path, value] sets, [path] deletes
Snapshot = Callable[[], dict]
EventsSince = Callable[[int], list[dict]]


def diff_status(old: Any, new: Any, path: tuple = ()) -> list[StatusOp]:
    """The ops that turn ``old`` into ``new``. Dicts recurse so a change deep
    in ``conversations`` costs one entry, not the whole registry; lists and
    scalars are replaced whole."""
    if isinstance(old, dict) and isinstance(new, dict):
        ops: list[StatusOp] = []
        for key, value in new.items():
            if key not in old:
                ops.append([[*path, key], value])
            elif old[key] != value:
                ops.extend(diff_status(old[key], value, (*path, key)))
        ops.extend([[*path, key]] for key in old if key not in new)
        return ops
    return [] if old == new else [[list(path), new]]


def diff_utterances(old: list[dict], new: list[dict]) -> dict | None:
    """None when nothing changed. Otherwise removals and upserts by id, as
    long as the list only lost items and grew at the end; any other reshape
    (or duplicate ids) is sent whole, so the client can never reorder wrong."""
    if old == new:
        return None
    old_ids = [u.get("id") for u in old]
    new_ids = [u.get("id") for u in new]
    if len(set(old_ids)) != len(old_ids) or len(set(new_ids)) != len(new_ids):
        return {"replace": new}
    new_set = set(new_ids)
    removed = [i for i in old_ids if i not in new_set]
    kept = [i for i in old_ids if i in new_set]
    if new_ids[: len(kept)] != kept:
        return {"replace": new}
    previous = {u.get("id"): u for u in old}
    upsert = [u for u in new if previous.get(u.get("id")) != u]
    return {"remove": removed, "upsert": upsert}


def requested_version(request_path: str) -> int | None:
    """The protocol a client asked for: None for a path this socket does not
    serve, v1 when it named none, never more than this daemon speaks."""
    url = urlparse(request_path or "")
    if url.path != STATE_PATH:
        return None
    try:
        asked = int(parse_qs(url.query).get("v", [LEGACY_PROTOCOL_VERSION])[0])
    except ValueError:
        asked = LEGACY_PROTOCOL_VERSION
    return max(LEGACY_PROTOCOL_VERSION, min(asked, STATE_PROTOCOL_VERSION))


class StateBroadcaster:
    """Builds the state once per tick for all clients and sends each one the
    change since the last message it got. Thread-safe: connection handlers
    attach/detach, one ticker thread calls ``tick``."""

    def __init__(self, snapshot: Snapshot, events_since: EventsSince = lambda _seq: [],
                 clock: Callable[[], float] = time.monotonic):
        self._snapshot = snapshot
        self._events_since = events_since
        self._clock = clock
        self._lock = threading.Lock()
        self._clients: dict[Any, int] = {}
        self._status: dict | None = None
        self._utterances: list[dict] = []
        self._event_seq = 0
        self._seq = 0
        self._volatile_sent_at = 0.0

    def attach(self, ws, version: int) -> bool:
        """Bring the shared state up to date, then hand the newcomer all of
        it. False when the socket died before it got its snapshot."""
        with self._lock:
            self._refresh()
            try:
                ws.send(json.dumps(self._full_message(version, with_events=True)))
            except Exception:
                return False
            self._clients[ws] = version
            return True

    def detach(self, ws) -> None:
        with self._lock:
            self._clients.pop(ws, None)

    def tick(self) -> None:
        with self._lock:
            if self._clients:
                self._refresh()

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def _refresh(self) -> None:
        built = self._snapshot()
        status, utterances = built.get("status") or {}, built.get("utterances") or []
        events = self._events_since(self._event_seq)
        if self._status is None:  # first build: nothing to diff against yet
            self._adopt(status, utterances, events)
            return
        ops = diff_status(self._status, status)
        meaningful = [op for op in ops if not op[0] or op[0][0] not in STATE_VOLATILE_KEYS]
        utterance_patch = diff_utterances(self._utterances, utterances)
        now = self._clock()
        volatile_due = now - self._volatile_sent_at >= STATE_VOLATILE_INTERVAL_SECONDS
        if not (meaningful or utterance_patch or events or (ops and volatile_due)):
            return  # nothing worth a message; the base keeps the old clocks
        self._adopt(status, utterances, events)
        self._volatile_sent_at = now
        self._seq += 1
        patch: dict[str, Any] = {"type": "patch", "v": STATE_PROTOCOL_VERSION, "seq": self._seq}
        if ops:
            patch["status"] = ops
        if utterance_patch:
            patch["utterances"] = utterance_patch
        if events:
            patch["events"] = events
        self._broadcast(patch)

    def _adopt(self, status: dict, utterances: list[dict], events: list[dict]) -> None:
        self._status, self._utterances = status, utterances
        if events:
            self._event_seq = events[-1].get("seq", self._event_seq)

    def _full_message(self, version: int, with_events: bool = False) -> dict:
        message = {"type": "snapshot", "status": self._status, "utterances": self._utterances}
        if version >= STATE_PROTOCOL_VERSION:
            message["v"] = STATE_PROTOCOL_VERSION
            message["seq"] = self._seq
            if with_events:
                # Only what the patches have not covered yet would be a
                # duplicate later, so cut at what the broadcaster has seen.
                message["events"] = [e for e in self._events_since(0)
                                     if e.get("seq", 0) <= self._event_seq]
        return message

    def _broadcast(self, patch: dict) -> None:
        encoded: dict[int, str] = {}  # serialize once per protocol version
        for ws, version in list(self._clients.items()):
            if version not in encoded:
                message = patch if version >= STATE_PROTOCOL_VERSION else self._full_message(version)
                encoded[version] = json.dumps(message)
            try:
                ws.send(encoded[version])
            except Exception:  # the dashboard went away mid-send
                self._clients.pop(ws, None)


class StateStream:
    def __init__(self, snapshot: Snapshot, events_since: EventsSince = lambda _seq: []):
        self.broadcaster = StateBroadcaster(snapshot, events_since)

    def _handle(self, ws):
        version = requested_version(getattr(getattr(ws, 'request', None), 'path', ''))
        if version is None:
            ws.close(code=1008, reason='Only dashboard state updates are supported')
            return
        if not self.broadcaster.attach(ws, version):
            return
        try:
            while True:
                # Client messages are heartbeats or nothing; a closed socket
                # raises here and ends the connection.
                ws.recv()
        except Exception:
            pass
        finally:
            self.broadcaster.detach(ws)

    def run_ticker(self) -> None:  # pragma: no cover — thread shell
        while True:
            time.sleep(STATE_PUSH_INTERVAL_SECONDS)
            try:
                self.broadcaster.tick()
            except Exception:  # a broken builder must not kill the stream
                continue

    def serve_forever(self, port: int) -> None:  # pragma: no cover — thread shell
        from websockets.sync.server import serve

        # Same bind rule as the HTTP API: loopback by default, explicitly overridable.
        host = os.environ.get("NOISY_STUDIO_BIND", "127.0.0.1")
        with serve(self._handle, host, port) as server:
            server.serve_forever()


def start_state_stream(http_port: int, snapshot: Snapshot,
                       events_since: EventsSince = lambda _seq: []) -> StateStream:
    stream = StateStream(snapshot, events_since)
    threading.Thread(target=stream.serve_forever, args=(http_port + STATE_PORT_OFFSET,), daemon=True).start()
    threading.Thread(target=stream.run_ticker, daemon=True).start()
    return stream
