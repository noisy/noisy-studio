"""The harness contract, enforced on every registered harness.

Runs against recorded payload fixtures in tests/fixtures/harness/<name>/,
so a harness is "supported" when this file is green for it - no daemon,
no agent, no microphone. Invariants are numbered as in the spec
(docs/superpowers/specs/2026-09-10-agent-harness-contract-design.md).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from noisy_coding import harness
from noisy_coding.harness.base import HarnessError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "harness"
REQUIRED = ("session.jsonl", "resume.jsonl", "title.jsonl")


def _rows(name: str, scenario: str) -> list[dict]:
    path = FIXTURES / name / scenario
    if not path.exists():
        pytest.skip(f"{name} ships no {scenario}")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture(params=harness.names())
def named(request):
    return request.param, harness.get(request.param)


def test_every_registered_harness_ships_the_required_fixtures(named):
    name, _adapter = named
    missing = [f for f in REQUIRED if not (FIXTURES / name / f).exists()]
    assert not missing, f"{name} is not supported until it ships {missing}"


def test_1_one_session_interprets_to_one_conversation_key(named):
    name, adapter = named
    for scenario in ("session.jsonl", "participant.jsonl"):
        rows = _rows(name, scenario) if (FIXTURES / name / scenario).exists() else []
        keys = {adapter.interpret(row).conversation for row in rows}
        assert len(keys) <= 1, f"{name}/{scenario}: {keys}"


def test_2_participants_never_drain_and_belong_to_the_parent(named):
    name, adapter = named
    rows = _rows(name, "participant.jsonl")
    parent_keys = {adapter.interpret(r).conversation for r in rows if not r.get("agent_id")}
    seen = False
    for row in rows:
        if not row.get("agent_id"):
            continue
        seen = True
        result = adapter.interpret(row)
        assert result.may_drain is False
        assert result.participant == row["agent_id"]
        assert result.conversation in parent_keys
        assert result.speech_identity in (None, result.conversation)
    assert seen, "participant.jsonl has no participant rows"


def test_3_resume_keeps_the_key_and_records_the_id_as_alias(named):
    name, adapter = named
    original = adapter.interpret(_rows(name, "session.jsonl")[0])
    for row in _rows(name, "resume.jsonl"):
        resumed = adapter.interpret(row)
        assert resumed.conversation == original.conversation
        presented = str(row.get("session_id") or "")
        aliases = {alias for event in resumed.events for alias in event.aliases}
        assert presented in aliases or presented == resumed.conversation


def test_4_a_title_is_reported_exactly_once_per_payload(named):
    name, adapter = named
    titled = 0
    for row in _rows(name, "title.jsonl"):
        events = adapter.interpret(row).events
        with_title = [e for e in events if e.title]
        assert len(with_title) <= 1, events
        titled += len(with_title)
    assert titled >= 1, f"{name}/title.jsonl never yields a title"


def test_5_capabilities_are_internally_consistent(named):
    name, adapter = named
    caps = adapter.capabilities
    if caps.wake == "long_poll":
        assert caps.max_idle_seconds and caps.max_idle_seconds > 0
    else:
        assert caps.max_idle_seconds is None
    stops = [adapter.interpret(r) for r in _rows(name, "session.jsonl")
             if r.get("hook_event_name") == "Stop"]
    if caps.wake == "none":
        assert all(s.listener == "none" for s in stops)
    if caps.wake == "long_poll":
        assert stops and all(s.listener in ("start", "poll") for s in stops)


def test_6_delivery_wakes_with_exit_2_and_carries_every_message_once(named):
    name, adapter = named
    messages = ["first thing", "second thing"]
    wake = adapter.deliver(messages, "wake")
    mid = adapter.deliver(messages, "mid_turn")
    if adapter.capabilities.wake == "long_poll":
        assert wake.exit_code == 2
    assert mid.exit_code == 0
    for delivery in (wake, mid):
        for message in messages:
            assert delivery.context.count(message) == 1
        assert delivery.system_message


def test_7_speech_identity_comes_from_the_session_not_the_environment(named, monkeypatch):
    name, adapter = named
    monkeypatch.setenv("NOISY_CODING_AGENT_NAME", "forged")
    monkeypatch.chdir(Path(__file__).parent)
    speak_rows = [r for r in _rows(name, "session.jsonl")
                  if r.get("hook_event_name") == "PreToolUse"
                  and "speak" in str(r.get("tool_name", ""))]
    assert speak_rows, f"{name}/session.jsonl has no speak call"
    for row in speak_rows:
        stripped = {k: v for k, v in row.items() if k != "cwd"}
        identity = adapter.interpret(stripped).speech_identity
        assert identity and identity != "forged"
        assert identity == adapter.interpret(row).conversation
    ordinary = [r for r in _rows(name, "session.jsonl")
                if r.get("hook_event_name") == "PreToolUse" and r not in speak_rows]
    for row in ordinary:
        assert adapter.interpret(row).speech_identity is None


def test_payload_without_a_session_fails_closed(named):
    _name, adapter = named
    with pytest.raises(HarnessError):
        adapter.interpret({"hook_event_name": "PreToolUse", "tool_name": "mcp__noisy-coding__speak"})
    with pytest.raises(HarnessError):
        adapter.interpret("not an object")  # type: ignore[arg-type]
