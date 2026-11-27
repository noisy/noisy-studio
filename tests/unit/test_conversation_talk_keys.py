"""Per-conversation talk keys live in the registry and follow the conversation."""

from __future__ import annotations

import json

import pytest

from noisy_studio.listener.conversations import ConversationRegistry


@pytest.fixture
def path(tmp_path):
    return tmp_path / "conversations.json"


@pytest.fixture
def registry(path):
    registry = ConversationRegistry(path=path)
    for key in ("a", "b", "c"):
        registry.adopt(key, key.upper(), "fake")
    return registry


def test_assigning_a_talk_key_records_it_per_conversation(registry):
    registry.set_talk_key("a", "F13")
    registry.set_talk_key("b", "cmd+F14")

    assert registry.talk_keys() == {"a": "F13", "b": "cmd+F14"}


def test_assigning_a_chord_another_conversation_holds_moves_it(registry):
    registry.set_talk_key("a", "F13")

    lost = registry.set_talk_key("b", "F13")

    assert (lost, registry.talk_keys()) == ("a", {"b": "F13"})


def test_reassigning_your_own_chord_loses_nothing(registry):
    registry.set_talk_key("a", "F13")

    assert registry.set_talk_key("a", "F13") is None


def test_empty_chord_clears_the_talk_key(registry):
    registry.set_talk_key("a", "F13")

    registry.set_talk_key("a", "")

    assert registry.talk_keys() == {}


def test_unknown_conversation_cannot_own_a_talk_key(registry):
    with pytest.raises(KeyError):
        registry.set_talk_key("nobody", "F13")


def test_talk_keys_survive_a_restart_and_hidden_or_ended_conversations_keep_them(registry, path):
    registry.set_talk_key("a", "F13")
    registry.set_talk_key("b", "F14")
    registry.hide("a")

    reborn = ConversationRegistry(path=path)

    assert reborn.talk_keys() == {"a": "F13", "b": "F14"}


def test_a_path_keyed_conversation_keeps_its_talk_key_when_folded_onto_its_session_id(path):
    transcript = "/Users/someone/.claude/projects/x/session-1.jsonl"
    registry = ConversationRegistry(path=path)
    registry.adopt(transcript, "Old", "fake")
    registry.set_talk_key(transcript, "F13")

    reborn = ConversationRegistry(path=path)

    assert reborn.talk_keys() == {"session-1": "F13"}


def test_a_talk_key_whose_conversation_is_gone_is_dropped_on_load(registry, path):
    data = json.loads(path.read_text())
    data["talk_keys"] = {"a": "F13", "ghost": "F14"}
    path.write_text(json.dumps(data))

    assert ConversationRegistry(path=path).talk_keys() == {"a": "F13"}


def test_snapshot_shows_each_conversations_talk_key(registry):
    registry.set_talk_key("b", "F13")

    assert {k: tab["talk_key"] for k, tab in registry.snapshot().items()} == {"a": "", "b": "F13", "c": ""}
