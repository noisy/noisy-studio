"""Grok-specific facts the contract suite cannot know."""

from __future__ import annotations

from noisy_studio.harness.grok_hooks.adapter import GrokHooks, title_from_summary


def _interpret(payload, summary=""):
    return GrokHooks(read_summary=lambda _session, _cwd: summary).interpret(payload)


def test_camel_case_session_is_the_conversation_and_speak_uses_it():
    result = _interpret({
        "hookEventName": "pre_tool_use",
        "sessionId": "01a0c70e-12a5-7c40-b332-9b55175c4bff",
        "toolName": "noisy-studio-dev__speak",
        "toolInput": {"text": "hi", "agent_id": "forged"},
    })

    assert result.conversation == "01a0c70e-12a5-7c40-b332-9b55175c4bff"
    assert result.speech_identity == result.conversation
    assert result.participant is None


def test_ordinary_tool_has_no_speech_identity():
    result = _interpret({
        "hook_event_name": "PreToolUse",
        "sessionId": "grok-1",
        "toolName": "run_terminal_command",
        "toolInput": {"command": "ls"},
    })

    assert result.speech_identity is None


def test_subagent_does_not_drain_or_listen():
    result = _interpret({
        "hook_event_name": "PostToolUse",
        "sessionId": "grok-1",
        "subagentType": "explore",
        "toolName": "grep",
    })

    assert (result.conversation, result.participant, result.may_drain, result.listener) == (
        "grok-1", "explore", False, "none",
    )


def test_turn_end_listens_and_session_end_does_not():
    listening = _interpret({"hook_event_name": "Stop", "sessionId": "grok-1", "reason": "end_turn"})
    closing = _interpret({"hook_event_name": "Stop", "sessionId": "grok-1", "reason": "shutdown"})

    assert listening.listener == "poll"
    assert [event.kind for event in listening.events if event.kind == "turn_ended"] == ["turn_ended"]
    assert closing.listener == "none"
    assert [event.kind for event in closing.events if event.kind == "session_ended"] == ["session_ended"]


def test_summary_title_is_used_when_the_payload_has_none():
    summary = '{"generated_title": "Wire the voice hooks", "custom_title": "On stream"}'
    result = _interpret(
        {"hook_event_name": "UserPromptSubmit", "sessionId": "grok-1", "cwd": "/work"},
        summary,
    )

    assert title_from_summary(summary) == "On stream"
    assert [event.title for event in result.events if event.title] == ["On stream"]


def test_listener_bound_admits_the_installers_full_hour():
    assert GrokHooks().capabilities.max_idle_seconds >= 3600
