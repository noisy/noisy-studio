"""Talk keys: what may be assigned, and which conversation a key reaches."""

from __future__ import annotations

import pytest

from noisy_studio.harness.base import Capabilities, Event, Observation
from noisy_studio.listener import talk_keys
from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.state import ListenerState

CAPABILITIES = Capabilities("none", None, "events", False, False)


@pytest.fixture
def state(tmp_path):
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / "conversations.json")
    for key in ("a", "b", "c", "d", "e", "f"):
        state.conversations.adopt(key, key.upper(), "fake")
        state.register_agent(key, key.upper())
    return state


def test_assign_stores_the_canonical_chord(state):
    change = talk_keys.assign(state.conversations, {}, "a", "Cmd+f13")

    assert change == talk_keys.TalkKeyChange("a", "cmd+F13", None, None)
    assert state.conversations.talk_keys() == {"a": "cmd+F13"}


def test_assign_moves_a_chord_another_conversation_owns(state):
    talk_keys.assign(state.conversations, {}, "a", "F13")

    change = talk_keys.assign(state.conversations, {}, "b", "F13")

    assert change == talk_keys.TalkKeyChange("b", "F13", "a", None)
    assert state.conversations.talk_keys() == {"b": "F13"}


def test_assign_refuses_a_chord_a_global_action_holds_and_keeps_the_old_key(state):
    talk_keys.assign(state.conversations, {}, "a", "F13")

    change = talk_keys.assign(state.conversations, {"tab1": "F16"}, "a", "F16")

    assert change == talk_keys.TalkKeyChange(
        "a", "F13", None, {"kind": "collision", "detail": "F16 is already bound to tab1"}
    )
    assert change.refused
    assert state.conversations.talk_keys() == {"a": "F13"}


def test_assign_refuses_the_double_press_of_an_action_chord(state):
    change = talk_keys.assign(state.conversations, {"hold": "F8"}, "a", "F8 x2")

    assert (change.refused, state.conversations.talk_keys()) == (True, {})


def test_assign_refuses_an_unparseable_chord(state):
    change = talk_keys.assign(state.conversations, {}, "a", "F99")

    assert (change.problem["kind"], change.refused, change.talk_key) == ("invalid", True, "")


def test_assign_stores_a_system_shortcut_with_its_warning(state):
    change = talk_keys.assign(state.conversations, {}, "a", "cmd+space")

    assert (change.talk_key, change.problem["kind"], change.refused) == ("cmd+space", "system", False)


def test_assign_with_an_empty_chord_clears(state):
    talk_keys.assign(state.conversations, {}, "a", "F13")

    change = talk_keys.assign(state.conversations, {}, "a", "")

    assert change == talk_keys.TalkKeyChange("a", "", None, None)
    assert state.conversations.talk_keys() == {}


def test_display_names_word_a_talk_key_by_its_conversations_label(state):
    talk_keys.assign(state.conversations, {}, "b", "F13")

    assert talk_keys.display_names(state.conversations) == {"talk:b": "the conversation 'B'"}


def test_a_conversation_with_its_own_key_drops_out_of_the_tab_numbering(state):
    state.conversations.set_talk_key("b", "F13")

    assert state.tab_shortcuts() == {"a": 1, "c": 2, "d": 3, "e": 4}


def test_talk_to_conversation_hands_it_the_mic_wherever_it_sits(state):
    assert state.talk_to_conversation("f") and state.active_agent == "f"


def test_talk_to_conversation_resolves_an_alias(state):
    rotated = Observation("e", (Event("activity", "e", aliases=("old-id",)),))
    state.conversations.apply("fake", rotated, CAPABILITIES)

    assert state.talk_to_conversation("old-id") and state.active_agent == "e"


def test_talk_to_a_closed_conversation_brings_it_back(state):
    state.dismiss_agent("c", force=True)
    state.conversations.hide("c")

    assert state.talk_to_conversation("c") and state.active_agent == "c"
    assert "c" in state.conversations.visible_keys()


def test_talk_to_an_unknown_conversation_changes_nothing(state):
    state.set_active_agent("a")

    assert state.talk_to_conversation("nobody") is False and state.active_agent == "a"
