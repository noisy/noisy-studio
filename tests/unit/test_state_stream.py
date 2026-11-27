import json

import pytest

from noisy_studio.listener.state_stream import (
    STATE_VOLATILE_INTERVAL_SECONDS,
    StateBroadcaster,
    diff_status,
    diff_utterances,
    requested_version,
)


class FakeSocket:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send(self, payload):
        if self.fail:
            raise ConnectionError("gone")
        self.sent.append(json.loads(payload))


class FakeDaemon:
    """The two things the broadcaster reads: a snapshot and the event log."""

    def __init__(self):
        self.status = {"agents": {"a": 1}, "active_agent": "a", "nudge_clocks": {"a": 1}}
        self.utterances = [{"id": 1, "text": "hi"}]
        self.events = []
        self.builds = 0
        self.now = 100.0

    def snapshot(self):
        self.builds += 1
        return {"type": "snapshot", "status": json.loads(json.dumps(self.status)),
                "utterances": json.loads(json.dumps(self.utterances))}

    def events_since(self, seq):
        return [e for e in self.events if e["seq"] > seq]

    def broadcaster(self):
        return StateBroadcaster(self.snapshot, self.events_since, clock=lambda: self.now)


@pytest.fixture
def daemon():
    return FakeDaemon()


def test_status_diff_reaches_into_nested_dicts_and_replaces_everything_else():
    old = {"conversations": {"a": {"state": "live", "label": "A"}, "b": {}}, "agents": ["a"], "gone": 1}
    new = {"conversations": {"a": {"state": "idle", "label": "A"}, "c": {}}, "agents": ["a", "b"], "active_agent": None}

    assert diff_status(old, new) == [
        [["conversations", "a", "state"], "idle"],
        [["conversations", "c"], {}],
        [["conversations", "b"]],
        [["agents"], ["a", "b"]],
        [["active_agent"], None],
        [["gone"]],
    ]


def test_status_diff_is_empty_for_equal_states():
    assert diff_status({"a": {"b": [1]}}, {"a": {"b": [1]}}) == []


@pytest.mark.parametrize(
    "old, new, expected",
    [
        ([{"id": 1}], [{"id": 1}], None),
        (
            [{"id": 1, "s": "rec"}, {"id": 2}],
            [{"id": 1, "s": "done"}, {"id": 2}, {"id": 3}],
            {"remove": [], "upsert": [{"id": 1, "s": "done"}, {"id": 3}]},
        ),
        ([{"id": 1}, {"id": 2}], [{"id": 2}, {"id": 3}], {"remove": [1], "upsert": [{"id": 3}]}),
        ([{"id": 1}, {"id": 2}], [{"id": 2}, {"id": 1}], {"replace": [{"id": 2}, {"id": 1}]}),
        ([{"id": 1}], [{"id": 1}, {"id": 1, "x": 1}], {"replace": [{"id": 1}, {"id": 1, "x": 1}]}),
    ],
    ids=["unchanged", "edit-and-append", "trimmed-head", "reordered", "duplicate-ids"],
)
def test_utterance_diff(old, new, expected):
    assert diff_utterances(old, new) == expected


@pytest.mark.parametrize(
    "path, expected",
    [("/state?v=2", 2), ("/state", 1), ("/state?v=9", 2), ("/state?v=x", 1), ("/", None), ("/stateful", None)],
)
def test_requested_version(path, expected):
    assert requested_version(path) == expected


def test_new_client_gets_everything_once_then_only_the_change(daemon):
    daemon.events = [{"seq": 1, "kind": "stt_error"}]
    broadcaster = daemon.broadcaster()
    client = FakeSocket()
    broadcaster.attach(client, 2)
    broadcaster.tick()  # nothing changed: no message
    daemon.status["active_agent"] = "b"
    daemon.utterances.append({"id": 2, "text": "new"})
    broadcaster.tick()

    assert client.sent == [
        {"type": "snapshot", "v": 2, "seq": 0, "status": daemon.status | {"active_agent": "a"},
         "utterances": [{"id": 1, "text": "hi"}], "events": [{"seq": 1, "kind": "stt_error"}]},
        {"type": "patch", "v": 2, "seq": 1, "status": [[["active_agent"], "b"]],
         "utterances": {"remove": [], "upsert": [{"id": 2, "text": "new"}]}},
    ]


def test_a_volatile_only_change_waits_for_the_relaxed_cadence(daemon):
    broadcaster = daemon.broadcaster()
    client = FakeSocket()
    broadcaster.attach(client, 2)
    daemon.status["nudge_clocks"] = {"a": 2}
    broadcaster.tick()
    daemon.now += STATE_VOLATILE_INTERVAL_SECONDS
    broadcaster.tick()

    assert client.sent[1:] == [{"type": "patch", "v": 2, "seq": 1, "status": [[["nudge_clocks", "a"], 2]]}]


def test_events_reach_each_client_exactly_once(daemon):
    broadcaster = daemon.broadcaster()
    early = FakeSocket()
    broadcaster.attach(early, 2)
    daemon.events.append({"seq": 1, "kind": "tts_error"})
    broadcaster.tick()
    late = FakeSocket()
    broadcaster.attach(late, 2)
    daemon.events.append({"seq": 2, "kind": "stt_error"})
    broadcaster.tick()

    delivered = lambda client: [e["seq"] for m in client.sent for e in m.get("events", [])]  # noqa: E731
    assert (delivered(early), delivered(late)) == ([1, 2], [1, 2])


def test_one_build_serves_every_client_and_a_dead_one_is_dropped(daemon):
    broadcaster = daemon.broadcaster()
    healthy, dying = FakeSocket(), FakeSocket()
    broadcaster.attach(healthy, 2)
    broadcaster.attach(dying, 2)
    dying.fail = True
    builds_before = daemon.builds
    daemon.status["active_agent"] = "b"
    broadcaster.tick()

    assert (daemon.builds - builds_before, len(healthy.sent), broadcaster.client_count) == (1, 2, 1)


def test_legacy_client_gets_full_snapshots_on_change(daemon):
    broadcaster = daemon.broadcaster()
    legacy = FakeSocket()
    broadcaster.attach(legacy, 1)
    daemon.status["active_agent"] = "b"
    broadcaster.tick()

    assert legacy.sent[-1] == {"type": "snapshot", "status": daemon.status, "utterances": daemon.utterances}


def test_no_client_means_no_build(daemon):
    broadcaster = daemon.broadcaster()
    broadcaster.tick()
    assert daemon.builds == 0


def test_character_change_updates_status_and_stream():
    from noisy_studio.listener.http_api import state_snapshot, status_payload
    from noisy_studio.listener.state import ListenerState

    state = ListenerState()
    state.register_agent("a1")
    before = state_snapshot(state)
    saved = state.set_character({"voice": "iris", "humor": 80}, "a1")
    after = state_snapshot(state)

    changed_paths = [op[0][:2] for op in diff_status(before["status"], after["status"])]
    assert (after["status"]["agent_characters"]["a1"], status_payload(state)["agent_characters"]["a1"],
            ["agent_characters", "a1"] in changed_paths) == (saved, saved, True)


def test_provider_capability_change_reaches_status_and_stream(monkeypatch):
    from noisy_studio.listener import http_api
    from noisy_studio.listener.state import ListenerState

    capabilities = {'version': 1, 'stt': {'model': 'model-a'}, 'tts': None}
    monkeypatch.setattr(http_api, 'audio_capabilities', lambda: dict(capabilities))
    state = ListenerState()
    before = http_api.state_snapshot(state)
    capabilities['stt'] = {'model': 'model-b'}
    after = http_api.state_snapshot(state)

    assert (http_api.status_payload(state)['audio_capabilities'],
            diff_status(before['status'], after['status'])) == (
        capabilities, [[['audio_capabilities', 'stt', 'model'], 'model-b']])


def test_status_distinguishes_idle_capture_from_an_unconsumed_recording_abort(monkeypatch):
    from noisy_studio.listener import http_api
    from noisy_studio.listener.state import ListenerState

    monkeypatch.setattr(http_api, '_maybe_refresh_latest_version', lambda state: None)
    state = ListenerState()
    before = http_api.status_payload(state)
    state.request_recording_abort()
    requested = http_api.status_payload(state)
    state.consume_recording_abort()
    consumed = http_api.status_payload(state)

    assert [
        (snapshot['recording'], snapshot['recording_abort_pending'])
        for snapshot in (before, requested, consumed)
    ] == [(False, False), (False, True), (False, False)]


def test_real_socket_receives_snapshot_then_patch(daemon):
    import threading

    from websockets.sync.client import connect
    from websockets.sync.server import serve

    from noisy_studio.listener.state_stream import StateStream

    stream = StateStream(daemon.snapshot, daemon.events_since)
    with serve(stream._handle, "127.0.0.1", 0) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.socket.getsockname()[1]
        with connect(f"ws://127.0.0.1:{port}/state?v=2") as client:
            snapshot = json.loads(client.recv(timeout=2))
            daemon.status["active_agent"] = "b"
            stream.broadcaster.tick()
            patch = json.loads(client.recv(timeout=2))
        server.shutdown()

    assert ((snapshot["type"], snapshot["seq"]), patch) == (
        ("snapshot", 0), {"type": "patch", "v": 2, "seq": 1, "status": [[["active_agent"], "b"]]})
