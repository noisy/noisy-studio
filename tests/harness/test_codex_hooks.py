"""Codex-specific facts the contract suite cannot know."""

from __future__ import annotations

from noisy_studio.harness.codex_hooks.adapter import CodexHooks


def _title(payload, index_text=""):
    events = CodexHooks(agent_label="Codex", read_index=lambda: index_text).interpret(payload).events
    started = [e for e in events if e.kind == "session_started"]
    if started and started[0].title:
        return started[0].title
    titled = [e for e in events if e.kind == "title_changed"]
    return titled[0].title if titled else ""


def test_codex_tab_has_no_name_until_codex_names_the_thread():
    # No project, no id, no prefix: an unnamed thread yields no title at all,
    # and the registry shows its neutral placeholder instead.
    assert _title({"hook_event_name": "SessionStart",
                   "session_id": "codex-0a1b2c3d", "cwd": "/Users/dev/noisy-studio"}) == ""


def test_codex_tab_takes_the_threads_own_name_when_codex_has_one():
    index = "\n".join([
        '{"id":"01a07a7e-538f","thread_name":"AstraWork","updated_at":"2026-09-10T12:41:06Z"}',
        '{"id":"other-thread","thread_name":"Something else","updated_at":"2026-09-10T12:50:00Z"}',
        '{"id":"01a07a7e-538f","thread_name":"package_bundle","updated_at":"2026-09-10T13:11:47Z"}',
        'not json at all',
    ])
    title = _title({"hook_event_name": "SessionStart", "session_id": "01a07a7e-538f", "cwd": "/w/Work"}, index)
    assert title == "package_bundle"  # the LAST name wins, no prefix, no project fallback
    assert _title({"hook_event_name": "SessionStart", "session_id": "unnamed-1", "cwd": "/w/Work"}, index) == ""


def test_codex_keys_by_session_id_and_never_drains_a_participant():
    result = CodexHooks(read_index=lambda: "").interpret(
        {"hook_event_name": "PostToolUse", "session_id": "codex-x", "agent_id": "sub-1", "cwd": "/w/p"})
    assert result.conversation == "codex-x"
    assert result.participant == "sub-1"
    assert result.may_drain is False


def test_codex_listener_bound_admits_the_installers_full_hour():
    # Regression (2026-09-10): the daemon clamps the hook's listen_seconds to
    # the adapter bound, so a bound below install_codex.py's 3600 max silently
    # turned a configured hour into half a minute and left the tab deaf.
    assert CodexHooks().capabilities.max_idle_seconds >= 3600
