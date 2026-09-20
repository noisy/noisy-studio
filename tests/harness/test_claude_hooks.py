"""Claude-specific facts the contract suite cannot know."""

from __future__ import annotations

import json

from noisy_coding.harness.claude_hooks.adapter import ClaudeHooks, title_from_transcript

PAYLOAD = {
    "session_id": "6eef14ed-f7a3-4bf5-b268-03eba86b85f3",
    "transcript_path": "/Users/dev/.claude/projects/p/6eef14ed.jsonl",
    "cwd": "/Users/dev/project",
}


def test_the_session_id_is_the_key_and_the_transcript_an_alias():
    result = ClaudeHooks(read_text=lambda _p: "").interpret({**PAYLOAD, "hook_event_name": "Stop"})
    assert result.conversation == PAYLOAD["session_id"]
    assert result.events[0].aliases == (PAYLOAD["transcript_path"],)
    assert result.short_id == "6eef14ed"


def test_a_rename_in_the_transcript_becomes_a_title_change():
    transcript = "\n".join(
        json.dumps(row)
        for row in (
            {"type": "user", "message": "hi"},
            {"type": "custom-title", "customTitle": "first name"},
            {"type": "custom-title", "customTitle": "reksio"},
        )
    )
    assert title_from_transcript(transcript) == "reksio"
    adapter = ClaudeHooks(read_text=lambda path: transcript if path == PAYLOAD["transcript_path"] else "")
    events = adapter.interpret({**PAYLOAD, "hook_event_name": "PostToolUse"}).events
    assert [e.title for e in events if e.kind == "title_changed"] == ["reksio"]


def test_session_start_carries_source_and_asks_for_a_listener():
    adapter = ClaudeHooks(read_text=lambda _p: "")
    started = adapter.interpret({**PAYLOAD, "hook_event_name": "SessionStart", "source": "resume"})
    assert started.listener == "start"
    assert started.events[0].kind == "session_started"
    assert started.events[0].source == "resume"


def test_subagent_payload_is_a_participant_of_the_parent():
    adapter = ClaudeHooks(read_text=lambda _p: "")
    result = adapter.interpret(
        {**PAYLOAD, "hook_event_name": "PostToolUse", "agent_id": "ae5366ae", "agent_type": "general-purpose"}
    )
    assert result.conversation == PAYLOAD["session_id"]
    assert result.participant == "ae5366ae"
    assert result.may_drain is False
    assert all(e.participant == "ae5366ae" for e in result.events)


def test_speak_identity_is_the_conversation_key_for_every_server_name():
    adapter = ClaudeHooks(read_text=lambda _p: "")
    for tool in ("mcp__noisy-coding__speak", "mcp__noisy-coding-dev__announce",
                 "mcp__plugin_noisy-coding_noisy-coding__change_voice",
                 "mcp__noisy-coding__acknowledge_delivery"):
        result = adapter.interpret({**PAYLOAD, "hook_event_name": "PreToolUse", "tool_name": tool,
                                    "tool_input": {"text": "x"}})
        assert result.speech_identity == PAYLOAD["session_id"]
    other = adapter.interpret({**PAYLOAD, "hook_event_name": "PreToolUse", "tool_name": "Bash",
                               "tool_input": {"command": "ls -la"}})
    assert other.speech_identity is None
    assert other.events[0].detail == "Bash · ls -la"


def test_claude_auto_summary_title_is_a_name_until_the_user_renames():
    transcript = "\n".join([
        json.dumps({"type": "user", "message": "hi"}),
        json.dumps({"type": "summary", "summary": "Fix the tab naming"}),
    ])
    assert title_from_transcript(transcript) == "Fix the tab naming"
    renamed = transcript + "\n" + json.dumps({"type": "custom-title", "customTitle": "reksio"})
    assert title_from_transcript(renamed) == "reksio"  # /rename wins over the auto title


def test_identity_tools_accept_both_plugin_prefixes():
    """The rename must not cost an installed plugin its voice (#122).

    The plugin is noisy-studio now; a user who has not reinstalled still
    has noisy-coding registered. If identity injection stopped matching
    the old prefix, their agent would simply stop speaking as itself, with
    nothing on screen explaining why.
    """
    from noisy_coding.harness.hook_common import IDENTITY_TOOLS

    for tool in (
        "mcp__noisy-studio__speak",
        "mcp__noisy-coding__speak",
        "mcp__noisy-studio-dev__announce",
        "mcp__noisy-coding-dev__announce",
        "mcp__plugin_noisy-studio_noisy-studio__change_voice",
        "mcp__plugin_noisy-coding_noisy-coding__change_voice",
    ):
        assert IDENTITY_TOOLS.match(tool), tool

    for tool in ("mcp__other__speak", "mcp__noisy-studio__read", "Bash"):
        assert not IDENTITY_TOOLS.match(tool), tool
