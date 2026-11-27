"""Snoozed conversations: settled now, back by themselves at a set time
(POST /snooze-agent and the daemon's periodic wake_snoozed)."""

from __future__ import annotations

import http.client
import json
import time

import pytest

from noisy_studio.harness.base import Capabilities, Event, Observation
from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.http_api import start_http_api, wake_snoozed
from noisy_studio.listener.settled import settled_conversations
from noisy_studio.listener.state import ListenerState
from noisy_studio.listener.workspace import WorkspaceCache

EVENTS = Capabilities("none", None, "events", False, False)
LATER = 3600.0


class _Clock:
    def __init__(self, now: float):
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return _Clock(time.time())


@pytest.fixture
def state(tmp_path, clock):
    state = ListenerState()
    state.conversations = ConversationRegistry(clock=clock, path=tmp_path / "conversations.json")
    for key in ("a", "b"):
        state.conversations.adopt(key, key.upper(), "fake")
        state.register_agent(key, key.upper())
    return state


@pytest.fixture
def post(state):
    server = start_http_api(state, 0)
    port = server.server_address[1]

    def _post(path: str, body: dict) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("POST", path, body=json.dumps(body))
        response = connection.getresponse()
        return response.status, json.loads(response.read())

    yield _post
    server.shutdown()


def test_snoozing_settles_the_conversation_until_the_wake_time(state, post, clock):
    until = clock.now + LATER

    status, body = post("/snooze-agent", {"name": "b", "until": until})

    assert (status, body) == (200, {"snoozed": "b", "snoozed_until": until})
    assert ("b" in state.agents, state.conversations.get("b").hidden, state.conversations.snoozed_until("b")) == (False, True, until)


def test_the_settled_list_shows_when_a_snoozed_conversation_wakes(state, post, clock):
    post("/snooze-agent", {"name": "b", "until": clock.now + LATER})

    settled = settled_conversations(state.conversations, WorkspaceCache(reader=lambda cwd: None), state.agents)

    assert settled["items"][0]["snoozed_until"] == clock.now + LATER


def test_snoozing_the_mic_conversation_hands_the_mic_on(state, post, clock):
    state.set_active_agent("a")

    post("/snooze-agent", {"name": "a", "until": clock.now + LATER})

    assert state.active_agent == "b"


@pytest.mark.parametrize("until", [0, "tomorrow", True])
def test_a_wake_time_that_is_not_in_the_future_is_refused(state, post, until):
    status, _ = post("/snooze-agent", {"name": "a", "until": until})

    assert (status, "a" in state.agents) == (400, True)


def test_snoozing_an_unknown_conversation_is_404(post, clock):
    assert post("/snooze-agent", {"name": "nobody", "until": clock.now + LATER}) == (404, {"error": "unknown conversation"})


def test_cancelling_a_snooze_leaves_the_conversation_settled(state, post, clock):
    post("/snooze-agent", {"name": "b", "until": clock.now + LATER})

    status, body = post("/snooze-agent", {"name": "b", "until": None})

    assert (status, body) == (200, {"snoozed": "b", "snoozed_until": None})
    assert (state.conversations.snoozed_until("b"), state.conversations.get("b").hidden) == (None, True)


def test_a_due_snooze_brings_the_conversation_back_to_its_project(state, post, clock):
    state.conversations.apply("fake", Observation("b", (Event("session_ended", "b"),)), EVENTS)
    post("/snooze-agent", {"name": "b", "until": clock.now + LATER})
    clock.now += LATER

    woken = wake_snoozed(state)

    assert woken == ["b"]
    assert ("b" in state.agents, state.conversations.kept_in_project("b"), state.conversations.snoozed_until("b")) == (True, True, None)
    assert state.events_since(0)[-1]["detail"] == "'B' is back (snooze ended)"


def test_a_snooze_that_is_not_due_yet_keeps_sleeping(state, post, clock):
    post("/snooze-agent", {"name": "b", "until": clock.now + LATER})
    clock.now += LATER - 1

    assert (wake_snoozed(state), "b" in state.agents) == ([], False)


def test_restoring_a_snoozed_conversation_cancels_the_snooze(state, post, clock):
    post("/snooze-agent", {"name": "b", "until": clock.now + LATER})

    post("/restore-agent", {"name": "b"})

    assert ("b" in state.agents, state.conversations.snoozed_until("b")) == (True, None)


def test_its_session_speaking_brings_it_back_early(state, post, clock):
    post("/snooze-agent", {"name": "b", "until": clock.now + LATER})

    state.conversations.apply("fake", Observation("b", (Event("turn_started", "b"),)), EVENTS)

    assert (state.conversations.get("b").hidden, state.conversations.snoozed_until("b")) == (False, None)


def test_snoozes_survive_a_restart(state, post, clock, tmp_path):
    post("/snooze-agent", {"name": "b", "until": clock.now + LATER})

    reloaded = ConversationRegistry(path=tmp_path / "conversations.json")

    assert reloaded.snoozed_until("b") == clock.now + LATER


def test_a_malformed_saved_snooze_is_dropped(tmp_path):
    path = tmp_path / "conversations.json"
    registry = ConversationRegistry(path=path)
    registry.adopt("a", "A")
    saved = json.loads(path.read_text())
    path.write_text(json.dumps({**saved, "snoozed_until": {"a": "soon", "gone": 5}}))

    assert ConversationRegistry(path=path).snoozed_until("a") is None
