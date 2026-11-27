"""POST /conversation-hotkey: give any conversation its own talk key."""

from __future__ import annotations

import http.client
import json

import pytest

from noisy_studio.harness.base import Capabilities, Event, Observation
from noisy_studio.listener import http_api
from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.http_api import start_http_api
from noisy_studio.listener.state import ListenerState


class _Listener:
    def __init__(self):
        self.talk_key_calls = []
        self.binding_calls = []

    def configure_talk_keys(self, talk_keys, *, may_prompt=False):
        self.talk_key_calls.append((dict(talk_keys), may_prompt))

    def configure_bindings(self, bindings, *, talk_keys=None, may_prompt=False):
        self.binding_calls.append(dict(bindings))


@pytest.fixture
def state(tmp_path):
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / "conversations.json")
    state.hotkey_listener = _Listener()
    for key in ("a", "b", "c"):
        state.conversations.adopt(key, key.upper(), "fake")
        state.register_agent(key, key.upper())
    return state


@pytest.fixture
def post(state):
    server = start_http_api(state, 0)
    port = server.server_address[1]

    def _post(body: dict) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("POST", "/conversation-hotkey", body=json.dumps(body))
        response = connection.getresponse()
        return response.status, json.loads(response.read())

    yield _post
    server.shutdown()


def test_assigning_a_talk_key_stores_it_and_arms_it(state, post):
    status, body = post({"conversation": "b", "chord": "f13"})

    assert (status, body) == (200, {"conversation": "b", "talk_key": "F13", "moved_from": None, "problem": None})
    assert state.hotkey_listener.talk_key_calls == [({"b": "F13"}, True)]


def test_assigning_a_chord_another_conversation_owns_moves_it(state, post):
    post({"conversation": "a", "chord": "F13"})

    _, body = post({"conversation": "c", "chord": "F13"})

    assert (body["moved_from"], state.conversations.talk_keys()) == ("a", {"c": "F13"})


def test_a_chord_a_global_action_holds_is_refused(state, post):
    state.set_hotkeys({"tab1": "F16"})

    status, body = post({"conversation": "a", "chord": "F16"})

    assert (status, body) == (200, {
        "conversation": "a", "talk_key": None, "moved_from": None,
        "problem": {"kind": "collision", "detail": "F16 is already bound to tab1"},
    })
    assert state.hotkey_listener.talk_key_calls == []


def test_clearing_disarms_without_a_permission_prompt(state, post):
    post({"conversation": "a", "chord": "F13"})

    _, body = post({"conversation": "a", "chord": None})

    assert body["talk_key"] is None
    assert state.hotkey_listener.talk_key_calls[-1] == ({}, False)


def test_an_alias_reaches_its_conversation(state, post):
    rotated = Observation("b", (Event("activity", "b", aliases=("rotated-id",)),))
    state.conversations.apply("fake", rotated, Capabilities("none", None, "events", False, False))

    _, body = post({"conversation": "rotated-id", "chord": "F13"})

    assert (body["conversation"], state.conversations.talk_keys()) == ("b", {"b": "F13"})


def test_unknown_or_missing_conversation_is_an_error(post):
    assert (post({"conversation": "nobody", "chord": "F13"})[0], post({"chord": "F13"})[0]) == (404, 400)


def test_a_global_action_cannot_take_a_conversations_talk_key(state):
    state.conversations.set_talk_key("b", "F13")

    stored, problems = http_api._apply_hotkeys(state, {"toggle": "F13"})

    assert (stored, problems) == (
        {"toggle": ""},
        {"toggle": {"kind": "collision", "detail": "F13 is already bound to the conversation 'B'"}},
    )


def test_agents_meta_shows_the_talk_key_and_drops_the_tab_number(state):
    state.conversations.set_talk_key("a", "F13")

    meta = http_api._stable_agents_meta(state)

    assert {k: (m["talk_key"], m["shortcut"]) for k, m in meta.items()} == {
        "a": ("F13", None), "b": (None, 1), "c": (None, 2),
    }
