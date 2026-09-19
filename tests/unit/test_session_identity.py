"""One session must never hold two identities (#107).

The bugs these guard against were all silent: a voice that changed
mid-conversation, a filesystem path rendered as a tab label on a
livestream, and a ledger that grew two entries per human until every voice
in the pool was doubled.
"""

import pytest

from noisy_coding.listener.identity import (
    canonical_identity,
    fold_by_identity,
    is_transcript_path,
)
from noisy_coding.harness.claude_hooks.adapter import ClaudeHooks

SESSION = "6e8a75dc-57f8-4329-bf87-509bd223a573"
TRANSCRIPT = f"/Users/someone/.claude/projects/-a-project/{SESSION}.jsonl"


def test_transcript_path_resolves_to_its_session_id():
    assert canonical_identity(TRANSCRIPT) == SESSION


def test_a_plain_name_is_left_alone():
    # Named agents ("chat", "workout") must survive untouched, or the fold
    # would rename the very speakers it is meant to protect.
    assert canonical_identity("chat") == "chat"
    assert canonical_identity(SESSION) == SESSION
    assert not is_transcript_path("chat")


def test_windows_separators_resolve_too():
    assert canonical_identity(rf"C:\users\x\{SESSION}.jsonl") == SESSION


def test_a_path_with_no_stem_is_returned_unchanged():
    # Inventing a key is worse than keeping a useless one.
    assert canonical_identity("/.jsonl") == "/.jsonl"


def test_folding_keeps_the_session_id_entry_and_drops_its_twin():
    folded, collapsed = fold_by_identity({SESSION: "lux", TRANSCRIPT: "zagan"})
    assert folded == {SESSION: "lux"}
    assert collapsed == 1


def test_folding_renames_a_path_only_entry_rather_than_losing_it():
    # A speaker heard under the path spelling keeps the voice they had.
    folded, collapsed = fold_by_identity({TRANSCRIPT: "zagan"})
    assert folded == {SESSION: "zagan"}
    assert collapsed == 1


def test_folding_is_order_independent():
    first, _ = fold_by_identity({SESSION: "lux", TRANSCRIPT: "zagan"})
    second, _ = fold_by_identity({TRANSCRIPT: "zagan", SESSION: "lux"})
    assert first == second == {SESSION: "lux"}


def test_adapter_keys_on_the_session_id_and_aliases_the_path():
    adapter = ClaudeHooks(read_text=lambda _path: "")
    result = adapter.interpret(
        {
            "hook_event_name": "SessionStart",
            "session_id": SESSION,
            "transcript_path": TRANSCRIPT,
        }
    )
    event = result.events[0]
    assert event.conversation == SESSION, "the session id is canonical"
    assert TRANSCRIPT in event.aliases, "the path must still resolve to it"


def test_adapter_falls_back_to_the_path_when_there_is_no_session_id():
    # Better a path-keyed tab than no tab: a lost session is invisible.
    adapter = ClaudeHooks(read_text=lambda _path: "")
    result = adapter.interpret(
        {"hook_event_name": "SessionStart", "transcript_path": TRANSCRIPT}
    )
    assert result.events[0].conversation == TRANSCRIPT


def test_adapter_still_refuses_a_payload_that_names_no_session():
    adapter = ClaudeHooks(read_text=lambda _path: "")
    with pytest.raises(Exception):
        adapter.interpret({"hook_event_name": "SessionStart"})
