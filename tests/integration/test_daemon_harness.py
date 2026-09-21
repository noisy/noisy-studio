"""The daemon wired to the harness contract, driven over HTTP.

Real ListenerState + registry + HTTP handler; payloads are the recorded
Claude Code fixtures. This proves the wiring - the logic is proven by
tests/harness/.
"""

from __future__ import annotations

import http.client
import json
from pathlib import Path

import pytest

from noisy_studio.listener import http_api
from noisy_studio.listener.http_api import start_http_api
from noisy_studio.listener.state import ListenerState

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "harness" / "claude-hooks"


def _rows(name: str) -> list[dict]:
    return [json.loads(l) for l in (FIXTURES / name).read_text().splitlines() if l.strip()]


@pytest.fixture
def daemon(tmp_path, monkeypatch):
    monkeypatch.setattr(http_api, "DIST_DIR", tmp_path / "missing")
    state = ListenerState()
    server = start_http_api(state, 0)
    port = server.server_address[1]

    def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        payload = json.dumps(body).encode() if body is not None else None
        connection.request(method, path, body=payload,
                           headers={"Content-Type": "application/json"} if payload else {})
        response = connection.getresponse()
        return response.status, json.loads(response.read() or b"{}")

    def event(payload: dict) -> dict:
        status, body = call("POST", "/harness/event", {"harness": "claude-hooks", "payload": payload})
        assert status == 200, body
        return body

    yield state, call, event
    server.shutdown()


def test_session_start_creates_the_tab_before_any_message(daemon):
    state, call, event = daemon
    start = _rows("session.jsonl")[0]
    response = event(start)
    key = response["conversation"]
    assert key == start["transcript_path"]
    assert response["listener"] == "start" and response["listener_id"]
    _status, body = call("GET", "/status")
    tab = body["conversations"][key]
    assert tab["label"] == "New conversation"  # a name, never an id
    assert tab["status"] == "idle"
    assert tab["aliases"] == [start["session_id"]]
    assert key in body["agents"]


def test_subagent_never_takes_the_parents_message(daemon):
    state, call, event = daemon
    rows = _rows("participant.jsonl")
    event(rows[0])  # SessionStart
    key = rows[0]["transcript_path"]
    state.add_transcript("reset the counter")
    child = next(r for r in rows if r.get("agent_id") and r["hook_event_name"] == "PostToolUse")
    response = event(child)
    assert response["may_drain"] is False
    assert response["participant"] == child["agent_id"]
    # Only ONE tab exists, and the message is still queued for the parent.
    _status, body = call("GET", "/status")
    assert list(body["conversations"]) == [key]
    parent = next(r for r in rows if not r.get("agent_id") and r["hook_event_name"] == "PostToolUse")
    assert event(parent)["may_drain"] is True
    _status, drained = call("GET", f"/drain?conversation={key}")
    assert [t["text"] for t in drained["transcripts"]] == ["reset the counter"]
    assert drained["delivery"]["exit_code"] == 0
    assert "reset the counter" in drained["delivery"]["context"]


def test_a_stale_listener_stands_down_and_the_current_one_wakes(daemon):
    state, call, event = daemon
    rows = _rows("session.jsonl")
    event(rows[0])
    key = rows[0]["transcript_path"]
    stop = next(r for r in rows if r["hook_event_name"] == "Stop")
    first = event(stop)["listener_id"]
    second = event(stop)["listener_id"]
    utterance_id = state.create_utterance("user", "recording…", agent=key)
    state.add_transcript("are you there", utterance_id)
    _s, stale = call("GET", f"/drain?conversation={key}&listener={first}")
    assert stale == {"transcripts": [], "nudge": None, "stand_down": True}
    _s, current = call("GET", f"/drain?conversation={key}&listener={second}")
    assert current["stand_down"] is False
    assert current["delivery"]["exit_code"] == 2
    assert current["transcripts"][0]["text"] == "are you there"
    assert state.utterances()[-1]["status"] == "delivered to New conversation"  # the recipient is named, never an id


def test_listener_timeout_makes_the_tab_deaf_and_loud(daemon):
    state, call, event = daemon
    rows = _rows("session.jsonl")
    event(rows[0])
    key = rows[0]["transcript_path"]
    listener = event(next(r for r in rows if r["hook_event_name"] == "Stop"))["listener_id"]
    status, body = call("POST", "/harness/listener",
                        {"conversation": rows[0]["session_id"], "listener_id": listener, "reason": "timeout"})
    assert status == 200 and body["status"] == "deaf"
    _s, snapshot = call("GET", "/status")
    assert snapshot["conversations"][key]["status"] == "deaf"
    assert snapshot["conversations"][key]["deaf_reason"] == "timeout"
    assert any(e["kind"] == "deaf" for e in state.events_since(0))


def test_speak_with_a_session_id_lands_on_the_transcript_keyed_tab(daemon, monkeypatch):
    state, call, event = daemon
    rows = _rows("session.jsonl")
    event(rows[0])
    key = rows[0]["transcript_path"]
    submitted = {}

    def fake_submit(_state, text, **kwargs):
        submitted.update(text=text, **kwargs)
        return None  # "dedup raced us" path: responds skipped, no audio

    monkeypatch.setattr(http_api.speech, "submit", fake_submit)
    status, body = call("POST", "/speak", {"text": "hello", "agent": rows[0]["session_id"], "wait": False})
    assert status == 200 and body == {"skipped": True}
    assert submitted["agent"] == key
    assert list(state.agents) == [key]  # no hash tab was conjured


def test_title_from_the_hook_renames_the_tab(daemon):
    state, call, event = daemon
    rows = _rows("title.jsonl")
    event(rows[0])
    key = rows[0]["transcript_path"]
    assert state.agent_labels[key] == "reksio"
    _s, body = call("GET", "/status")
    assert body["conversations"][key]["label"] == "reksio"


def test_bad_payloads_fail_closed(daemon):
    _state, call, _event = daemon
    status, _ = call("POST", "/harness/event", {"harness": "nope", "payload": {}})
    assert status == 400
    status, body = call("POST", "/harness/event", {"harness": "claude-hooks", "payload": {"hook_event_name": "Stop"}})
    assert status == 422 and "session" in body["error"]


def test_tab_order_is_stable_across_a_daemon_restart(daemon):
    """The first conversation stays first even if it polls last after boot."""
    state, call, event = daemon
    first = _rows("session.jsonl")[0]
    second = {**first, "session_id": "22222222-0000-0000-0000-000000000000",
              "transcript_path": "/Users/dev/.claude/projects/p/22222222.jsonl"}
    event(first)
    event(second)
    # Simulate the post-restart race: the SECOND tab heartbeats first, then the first.
    state.register_agent(second["transcript_path"])
    state.register_agent(first["transcript_path"])
    _s, body = call("GET", "/status")
    meta = body["agents_meta"]
    assert meta[first["transcript_path"]]["activated_at"] < meta[second["transcript_path"]]["activated_at"]


def test_tab_liveness_comes_from_the_registry_not_heartbeats(daemon):
    state, call, event = daemon
    rows = _rows("session.jsonl")
    event(rows[0])
    key = rows[0]["transcript_path"]
    listener = event(next(r for r in rows if r["hook_event_name"] == "Stop"))["listener_id"]
    call("POST", "/harness/listener", {"conversation": key, "listener_id": listener, "reason": "timeout"})
    _s, body = call("GET", "/status")
    tab = body["agents_meta"][key]
    # Deaf is still alive (session running, just not listening) - never greyed as ended.
    assert tab["online"] is True and tab["status"] == "deaf"
    event({**rows[0], "hook_event_name": "SessionEnd"})
    _s, body = call("GET", "/status")
    assert body["agents_meta"][key]["online"] is False
    assert body["agents_meta"][key]["status"] == "ended"


def test_close_hides_a_live_background_tab_until_the_user_talks_there_again(daemon):
    state, call, event = daemon
    rows = _rows("session.jsonl")
    first = rows[0]
    second = {**first, "session_id": "22222222-0000-0000-0000-000000000000",
              "transcript_path": "/Users/dev/.claude/projects/p/22222222.jsonl"}
    event(first)
    event(second)  # live, background (first is active)
    status, body = call("POST", "/dismiss-agent", {"name": second["session_id"]})  # alias works
    assert status == 200 and body["dismissed"] == second["transcript_path"]
    assert second["transcript_path"] not in state.agents
    # A routine hook from the still-running session does NOT bring it back...
    event({**second, "hook_event_name": "PostToolUse", "tool_name": "Bash"})
    assert second["transcript_path"] not in state.agents
    # ...but the user typing there does.
    event({**second, "hook_event_name": "UserPromptSubmit"})
    assert second["transcript_path"] in state.agents
    # Closing the mic's tab hands the mic to the next visible conversation.
    assert state.active_agent == first["transcript_path"]
    status, body = call("POST", "/dismiss-agent", {"name": first["transcript_path"]})
    assert status == 200
    assert body["active_agent"] == second["transcript_path"] == state.active_agent
    assert first["transcript_path"] not in state.agents
    # Closing the last one releases the mic entirely.
    status, body = call("POST", "/dismiss-agent", {"name": second["transcript_path"]})
    assert status == 200 and body["active_agent"] is None


def test_a_closed_tab_that_speaks_comes_back_as_itself_not_as_a_hash(daemon, monkeypatch):
    state, call, event = daemon
    rows = _rows("title.jsonl")  # a session with a real title ("reksio")
    event(rows[0])
    key = rows[0]["transcript_path"]
    other = {**rows[0], "session_id": "33333333-0000-0000-0000-000000000000",
             "transcript_path": "/Users/dev/.claude/projects/p/33333333.jsonl", "session_title": "other"}
    event(other)  # so "reksio" is not the active tab and may be closed
    status, _ = call("POST", "/active-agent", {"name": other["transcript_path"]})
    status, _ = call("POST", "/dismiss-agent", {"name": key})
    assert status == 200 and key not in state.agents
    monkeypatch.setattr(http_api.speech, "submit", lambda *_a, **_k: None)
    # The closed session speaks, presenting its session id (an alias).
    status, _ = call("POST", "/speak", {"text": "still here", "agent": rows[0]["session_id"], "wait": False})
    assert status == 200
    assert key in state.agents                      # same key, back on the strip
    assert state.agent_labels[key] == "reksio"      # same title - no hash tab
    assert rows[0]["session_id"] not in state.agents  # and no second tab under the alias


def test_a_closed_tabs_listener_polling_does_not_resurrect_it(daemon):
    state, call, event = daemon
    rows = _rows("session.jsonl")
    event(rows[0])
    key = rows[0]["transcript_path"]
    other = {**rows[0], "session_id": "44444444-0000-0000-0000-000000000000",
             "transcript_path": "/Users/dev/.claude/projects/p/44444444.jsonl"}
    event(other)
    call("POST", "/active-agent", {"name": other["transcript_path"]})
    listener = event(next(r for r in rows if r["hook_event_name"] == "Stop"))["listener_id"]
    status, _ = call("POST", "/dismiss-agent", {"name": key})
    assert status == 200 and key not in state.agents
    # The session's Stop poller keeps polling for up to an hour...
    for _ in range(3):
        _s, body = call("GET", f"/drain?conversation={key}&listener={listener}")
        assert body["stand_down"] is False  # it is still the current listener
    # ...and the closed tab stays closed - no hash tab, no legacy re-register.
    assert key not in state.agents
    assert key not in call("GET", "/status")[1]["agents_meta"]


def test_a_tab_registered_by_old_hook_scripts_is_persisted_and_keeps_its_rename(daemon, tmp_path):
    state, call, event = daemon
    # Legacy path: no harness event, just /register with a session id and a title.
    call("POST", "/register", {"name": "legacy-session-1", "label": "stream-day-8"})
    call("POST", "/register", {"name": "legacy-session-1", "label": "stream-day-9"})  # /rename
    call("POST", "/register", {"name": "legacy-session-1", "label": "legacy-s"})       # fallback label must not win
    conversation = state.conversations.get("legacy-session-1")
    assert conversation is not None and conversation.title == "stream-day-9"
    _s, body = call("GET", "/status")
    assert body["agents_meta"]["legacy-session-1"]["label"] == "stream-day-9"
    assert body["conversations"]["legacy-session-1"]["label"] == "stream-day-9"


def test_old_hook_registration_and_activity_do_not_reopen_a_closed_tab(daemon):
    state, call, event = daemon
    first = _rows("session.jsonl")[0]
    event(first)
    call("POST", "/register", {"name": "legacy-2", "label": "old path"})
    status, _ = call("POST", "/dismiss-agent", {"name": "legacy-2"})
    assert status == 200 and "legacy-2" not in state.agents
    # Every tool call of an old-script session re-registers and reports activity...
    call("POST", "/register", {"name": "legacy-2", "label": "old path renamed"})
    call("POST", "/activity", {"agent": "legacy-2", "text": "Bash · ls"})
    # ...the tab stays closed, but its name is kept current for when it returns.
    assert "legacy-2" not in state.agents
    assert state.conversations.get("legacy-2").hidden is True
    assert state.conversations.get("legacy-2").title == "old path renamed"


def test_strip_order_is_the_persisted_registry_position(daemon):
    state, call, event = daemon
    rows = _rows("session.jsonl")
    a = rows[0]
    b = {**a, "session_id": "55555555-0000-0000-0000-000000000000", "transcript_path": "/Users/dev/.claude/projects/p/5.jsonl"}
    c = {**a, "session_id": "66666666-0000-0000-0000-000000000000", "transcript_path": "/Users/dev/.claude/projects/p/6.jsonl"}
    for r in (a, b, c):
        event(r)
    call("POST", "/reorder-agents", {"order": [c["transcript_path"], a["transcript_path"], b["transcript_path"]]})
    _s, body = call("GET", "/status")
    by_pos = sorted(body["agents_meta"], key=lambda k: body["agents_meta"][k]["manual_pos"])
    assert by_pos == [c["transcript_path"], a["transcript_path"], b["transcript_path"]]


def test_state_snapshot_is_the_same_data_as_status_plus_utterances(daemon):
    state, call, event = daemon
    event(_rows("session.jsonl")[0])
    snapshot = http_api.state_snapshot(state)
    assert snapshot["type"] == "snapshot"
    _s, status = call("GET", "/status")
    assert set(snapshot["status"]) == set(status)  # one builder, one shape
    assert snapshot["status"]["conversations"].keys() == status["conversations"].keys()
    assert snapshot["utterances"] == state.utterances()


def test_an_agents_interrupt_flag_cuts_only_its_own_speech(daemon, monkeypatch):
    state, call, event = daemon
    stops = []
    monkeypatch.setattr(http_api.playback, "stop_all_players", lambda: stops.append("stop"))
    monkeypatch.setattr(http_api.speech, "submit", lambda *_a, **_k: None)
    rows = _rows("session.jsonl")
    event(rows[0])
    me = rows[0]["transcript_path"]
    other = {**rows[0], "session_id": "77777777-0000-0000-0000-000000000000",
             "transcript_path": "/Users/dev/.claude/projects/p/7.jsonl"}
    event(other)
    # Another conversation is on the speakers.
    clip = state.create_utterance("claude", "playing…", text="theirs", agent=other["transcript_path"])
    state.set_playing_utterance_id(clip)
    call("POST", "/speak", {"text": "mine, urgent", "agent": me, "interrupt": True, "wait": False})
    assert stops == []                                   # not cut
    assert state.playing_clip()["id"] == clip            # still theirs
    assert any(e["detail"].startswith("interrupt ignored") for e in state.events_since(0))
    # Its own clip on the speakers: the interrupt applies.
    state.set_playing_utterance_id(state.create_utterance("claude", "playing…", text="mine, stale", agent=me))
    call("POST", "/speak", {"text": "mine, newer", "agent": me, "interrupt": True, "wait": False})
    assert stops == ["stop"]
    assert state.playing_clip() is None
