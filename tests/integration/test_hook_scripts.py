"""The thin hook scripts against a real daemon, as subprocesses.

What Claude Code / Codex see: stdout JSON, stderr text and the exit code.
The daemon is the real HTTP handler on a random port; speech never plays.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from noisy_studio.listener import http_api
from noisy_studio.listener.http_api import start_http_api
from noisy_studio.listener.state import ListenerState

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "harness" / "claude-hooks"
CLAUDE_HOOK = REPO / "hooks" / "claude_hook.py"
CODEX_HOOK = REPO / "hooks" / "codex_hook.py"
GROK_HOOK = REPO / "hooks" / "grok_hook.py"


def _rows(name: str) -> list[dict]:
    return [json.loads(l) for l in (FIXTURES / name).read_text().splitlines() if l.strip()]


@pytest.fixture
def daemon(tmp_path, monkeypatch):
    # Retained hook implementation remains independently executable for rollback.
    from noisy_studio.harness import agent_provider
    monkeypatch.setattr(agent_provider, "CLAUDE_DELIVERY", "hooks")
    monkeypatch.setattr(http_api, "DIST_DIR", tmp_path / "missing")
    monkeypatch.setattr(http_api, "SETTINGS_FILE", tmp_path / "settings.json")
    state = ListenerState()
    server = start_http_api(state, 0)
    yield state, server.server_address[1]
    server.shutdown()


def _run(script: Path, payload: dict, port: int, env_extra: dict | None = None, timeout: float = 10.0):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("NOISY_STUDIO_")}
    environment.update(NOISY_STUDIO_LISTENER_PORT=str(port), NOISY_STUDIO_REWAKE_GRACE_SECONDS="0")
    environment.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(script)], input=json.dumps(payload), capture_output=True,
        text=True, env=environment, timeout=timeout,
    )


def _queue(state: ListenerState, key: str, text: str) -> int:
    utterance_id = state.create_utterance("user", "recording…", agent=key)
    state.add_transcript(text, utterance_id)
    return utterance_id


def test_session_start_registers_the_tab_and_listens_until_the_window_ends(daemon):
    state, port = daemon
    start = _rows("session.jsonl")[0]
    began = time.time()
    result = _run(CLAUDE_HOOK, start, port, {"NOISY_STUDIO_REWAKE_WAIT_SECONDS": "1"})
    assert result.returncode == 0 and result.stdout == ""
    assert 1.0 <= time.time() - began < 5.0
    key = start["session_id"]
    assert state.agent_labels[key] == "New conversation"
    # The window ran out: the tab is deaf and says so.
    assert state.conversations.status(key) == "deaf"
    assert state.conversations.deaf_reason(key) == "timeout"


def test_post_tool_use_delivers_queued_voice_as_context(daemon):
    state, port = daemon
    rows = _rows("session.jsonl")
    _run(CLAUDE_HOOK, rows[0], port, {"NOISY_STUDIO_REWAKE_WAIT_SECONDS": "0"})
    key = rows[0]["session_id"]
    _queue(state, key, "please add a test")
    post = next(r for r in rows if r["hook_event_name"] == "PostToolUse")
    result = _run(CLAUDE_HOOK, post, port)
    output = json.loads(result.stdout)
    assert "please add a test" in output["hookSpecificOutput"]["additionalContext"]
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "please add a test" in output["systemMessage"]
    assert state.utterances()[-1]["status"] == "delivered to New conversation"  # the recipient is named, never an id


def test_a_subagents_post_tool_use_leaves_the_parents_queue_alone(daemon):
    state, port = daemon
    rows = _rows("participant.jsonl")
    _run(CLAUDE_HOOK, rows[0], port, {"NOISY_STUDIO_REWAKE_WAIT_SECONDS": "0"})
    key = rows[0]["session_id"]
    _queue(state, key, "for the main thread only")
    child = next(r for r in rows if r.get("agent_id") and r["hook_event_name"] == "PostToolUse")
    result = _run(CLAUDE_HOOK, child, port)
    assert result.returncode == 0 and result.stdout == ""
    assert state.queued_count == 1
    assert list(state.agents) == [key]


def test_stop_wakes_the_model_with_the_spoken_text(daemon):
    state, port = daemon
    rows = _rows("session.jsonl")
    _run(CLAUDE_HOOK, rows[0], port, {"NOISY_STUDIO_REWAKE_WAIT_SECONDS": "0"})
    key = rows[0]["session_id"]
    _queue(state, key, "what did you change")
    stop = next(r for r in rows if r["hook_event_name"] == "Stop")
    result = _run(CLAUDE_HOOK, stop, port, {"NOISY_STUDIO_REWAKE_WAIT_SECONDS": "5"})
    assert result.returncode == 2
    assert "[VOICE] The user said (spoken): what did you change" in result.stderr
    assert "what did you change" in json.loads(result.stdout.splitlines()[0])["systemMessage"]
    assert state.activity[key]["text"] == "THINKING…"


def test_a_stale_stop_listener_stands_down_when_a_newer_one_starts(daemon):
    state, port = daemon
    rows = _rows("session.jsonl")
    _run(CLAUDE_HOOK, rows[0], port, {"NOISY_STUDIO_REWAKE_WAIT_SECONDS": "0"})
    key = rows[0]["session_id"]
    stop = next(r for r in rows if r["hook_event_name"] == "Stop")
    environment = {k: v for k, v in os.environ.items() if not k.startswith("NOISY_STUDIO_")}
    environment.update(NOISY_STUDIO_LISTENER_PORT=str(port), NOISY_STUDIO_REWAKE_WAIT_SECONDS="20",
                       NOISY_STUDIO_REWAKE_GRACE_SECONDS="0")
    stale = subprocess.Popen([sys.executable, str(CLAUDE_HOOK)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
    stale.stdin.write(json.dumps(stop)); stale.stdin.close()
    deadline = time.time() + 5
    while state.conversations.get(key).listener is None:  # SessionStart with window 0 started none
        assert time.time() < deadline
        time.sleep(0.05)
    # A new turn ended: a fresh listener takes over.
    fresh = subprocess.Popen([sys.executable, str(CLAUDE_HOOK)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
    fresh.stdin.write(json.dumps(stop)); fresh.stdin.close()
    assert stale.wait(timeout=5) == 0
    assert (stale.stdout.read(), stale.stderr.read()) == ("", "")
    _queue(state, key, "only the fresh one hears this")
    assert fresh.wait(timeout=10) == 2
    assert "only the fresh one hears this" in fresh.stderr.read()


def test_pre_tool_use_injects_the_conversation_identity_into_speak(daemon):
    _state, port = daemon
    rows = _rows("session.jsonl")
    speak = next(r for r in rows if r["hook_event_name"] == "PreToolUse" and "speak" in r["tool_name"])
    forged = {**speak, "tool_input": {**speak["tool_input"], "agent_id": "forged"}}
    result = _run(CLAUDE_HOOK, forged, port)
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert output["hookSpecificOutput"]["updatedInput"]["agent_id"] == speak["session_id"]
    assert output["hookSpecificOutput"]["updatedInput"]["text"] == "Hello from the fixture"
    assert "Hello from the fixture" in output["systemMessage"]
    ordinary = next(r for r in rows if r["hook_event_name"] == "PreToolUse" and r["tool_name"] == "Agent")
    assert _run(CLAUDE_HOOK, ordinary, port).stdout == ""


def test_without_a_daemon_every_hook_is_silent_and_exits_zero():
    for row in _rows("session.jsonl"):
        result = _run(CLAUDE_HOOK, row, 1, {"NOISY_STUDIO_REWAKE_WAIT_SECONDS": "1"}, timeout=5)
        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_speech_without_session_identity_is_blocked(daemon):
    _state, port = daemon
    result = _run(CLAUDE_HOOK, {"hook_event_name": "PreToolUse", "tool_name": "mcp__noisy-studio__speak",
                                "tool_input": {"text": "x"}}, port)
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "session" in output["systemMessage"]


def test_codex_hook_reads_its_endpoint_from_the_settings_file(daemon, tmp_path):
    state, port = daemon
    settings = tmp_path / "codex.json"
    settings.write_text(json.dumps({"port": port, "listen_seconds": 1}))
    env = {"NOISY_STUDIO_CODEX_CONFIG": str(settings), "HOME": str(tmp_path)}
    payload = {"hook_event_name": "SessionStart", "session_id": "codex-abc12345", "cwd": str(tmp_path)}
    # The port comes from the settings file; the env var is only an override.
    result = _run(CODEX_HOOK, payload, port, env)
    assert result.returncode == 0
    # Named by project (the cwd basename) plus a short id, not a bare hash.
    assert state.agent_labels["codex-abc12345"] == "New conversation"
    _queue(state, "codex-abc12345", "codex, are you there")
    began = time.time()
    result = _run(CODEX_HOOK, {**payload, "hook_event_name": "Stop"}, port, env)
    assert result.returncode == 2 and "codex, are you there" in result.stderr
    assert time.time() - began < 3.0
    assert not (tmp_path / ".config/noisy-studio/sessions.json").exists()


def test_grok_hook_injects_identity_and_delivers_voice_without_a_person(daemon, tmp_path):
    state, port = daemon
    settings = tmp_path / "grok.json"
    settings.write_text(json.dumps({"port": port, "listen_seconds": 1}))
    env = {"NOISY_STUDIO_GROK_CONFIG": str(settings)}
    session = "grok-session-1"
    start = {
        "hookEventName": "session_start",
        "hook_event_name": "SessionStart",
        "sessionId": session,
        "cwd": str(tmp_path),
        "source": "startup",
        "sessionTitle": "Grok voice",
    }
    assert _run(GROK_HOOK, start, port, env).returncode == 0
    assert state.agent_labels[session] == "Grok voice"

    speak = {
        "hookEventName": "pre_tool_use",
        "hook_event_name": "PreToolUse",
        "sessionId": session,
        "toolName": "noisy-studio-dev__speak",
        "toolInput": {"text": "hello there", "agent_id": "forged"},
    }
    injected = json.loads(_run(GROK_HOOK, speak, port, env).stdout)
    assert injected["hookSpecificOutput"]["updatedInput"]["agent_id"] == session
    assert injected["hookSpecificOutput"]["updatedInput"]["text"] == "hello there"

    _queue(state, session, "are you receiving this")
    delivered = _run(GROK_HOOK, {
        "hook_event_name": "PostToolUse",
        "sessionId": session,
        "toolName": "read_file",
    }, port, env)
    assert delivered.returncode == 0
    assert "are you receiving this" in delivered.stdout

    _queue(state, session, "still here after the turn")
    woke = _run(GROK_HOOK, {
        "hook_event_name": "Stop",
        "sessionId": session,
        "reason": "end_turn",
    }, port, env)
    assert woke.returncode == 0
    assert "still here after the turn" in woke.stdout
    assert json.loads(woke.stdout)["decision"] == "block"

    closing = _run(GROK_HOOK, {
        "hook_event_name": "Stop",
        "sessionId": session,
        "reason": "shutdown",
    }, port, {**env, "NOISY_STUDIO_REWAKE_WAIT_SECONDS": "30"})
    assert closing.returncode == 0
    assert closing.stdout == ""
