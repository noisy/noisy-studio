"""Settled conversations: listed for the dashboard (bounded, newest first)
and brought back with POST /restore-agent."""

from __future__ import annotations

import http.client
import json
import itertools

import pytest

from noisy_studio.harness.base import Capabilities, Event, Observation
from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.http_api import start_http_api, status_payload
from noisy_studio.listener.settled import settled_conversations
from noisy_studio.listener.state import ListenerState
from noisy_studio.listener.workspace import Workspace, WorkspaceCache

EVENTS = Capabilities("none", None, "events", False, False)


class _Clock:
    """Every call is one second later, so last activity orders the rows."""

    def __init__(self):
        self._ticks = itertools.count(1000)

    def __call__(self) -> float:
        return float(next(self._ticks))


def _end(registry: ConversationRegistry, key: str) -> None:
    registry.apply("fake", Observation(key, (Event("session_ended", key),)), EVENTS)


def _start_turn(registry: ConversationRegistry, key: str) -> None:
    registry.apply("fake", Observation(key, (Event("turn_started", key),)), EVENTS)


@pytest.fixture
def state(tmp_path):
    state = ListenerState()
    state.conversations = ConversationRegistry(clock=_Clock(), path=tmp_path / "conversations.json")
    for key in ("a", "b", "c"):
        state.conversations.adopt(key, key.upper(), "fake")
        state.register_agent(key, key.upper())
    return state


def _settle(state: ListenerState, key: str) -> None:
    state.dismiss_agent(key, force=True)
    state.conversations.hide(key)


@pytest.fixture
def post(state):
    server = start_http_api(state, 0)
    port = server.server_address[1]

    def _post(body: dict) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("POST", "/restore-agent", body=json.dumps(body))
        response = connection.getresponse()
        return response.status, json.loads(response.read())

    yield _post
    server.shutdown()


def test_restoring_a_settled_conversation_puts_it_back_in_the_list(state, post):
    _settle(state, "b")

    status, body = post({"name": "b"})

    assert (status, body) == (200, {"restored": "b"})
    assert ("b" in state.agents, state.conversations.get("b").hidden) == (True, False)
    assert state.events_since(0)[-1]["detail"] == "'B' restored"


def test_restore_resolves_an_alias(state, post):
    state.conversations.apply("fake", Observation("a", (Event("activity", "a", aliases=("old-id",)),)), EVENTS)
    _settle(state, "a")

    _, body = post({"name": "old-id"})

    assert (body, "a" in state.agents) == ({"restored": "a"}, True)


def test_restoring_an_unknown_conversation_is_404(post):
    assert post({"name": "nobody"}) == (404, {"error": "unknown conversation"})


def test_a_restored_ended_conversation_stays_in_its_project_until_it_starts_again(state, post):
    _end(state.conversations, "b")
    _settle(state, "b")

    post({"name": "b"})
    kept_after_restore = status_payload(state)["agents_meta"]["b"]["kept"]
    _start_turn(state.conversations, "b")

    assert (kept_after_restore, status_payload(state)["agents_meta"]["b"]["kept"]) == (True, False)


def test_restoring_an_ended_row_still_listed_keeps_it_in_its_project(state, post):
    _end(state.conversations, "c")

    status, _ = post({"name": "c"})

    assert (status, status_payload(state)["agents_meta"]["c"]["kept"]) == (200, True)


def test_settling_a_kept_conversation_lets_it_fold_again(state, post):
    _end(state.conversations, "c")
    post({"name": "c"})

    _settle(state, "c")

    assert state.conversations.kept_in_project("c") is False


def test_kept_conversations_survive_a_restart(state, post, tmp_path):
    _end(state.conversations, "c")
    post({"name": "c"})

    reloaded = ConversationRegistry(path=tmp_path / "conversations.json")

    assert reloaded.kept_in_project("c") is True


def test_settled_lists_the_newest_settled_conversations_with_their_workspace(state):
    state.conversations.apply("fake", Observation("a", cwd="/repos/app"), EVENTS)
    _end(state.conversations, "a")
    _settle(state, "a")
    state.conversations.set_talk_key("b", "F13")
    _settle(state, "b")
    workspaces = WorkspaceCache(reader=lambda cwd: Workspace(project="app", branch="main"))

    _start_turn(state.conversations, "b")  # b spoke last, so it is listed first
    state.conversations.hide("b")
    seen = {key: state.conversations.get(key).last_event_at for key in ("a", "b")}

    settled = settled_conversations(state.conversations, workspaces, state.agents)

    assert settled == {"total": 2, "items": [
        {"name": "b", "label": "B", "project": None, "branch": None, "last_active_at": seen["b"], "ended": False, "talk_key": "F13", "snoozed_until": None},
        {"name": "a", "label": "A", "project": "app", "branch": "main", "last_active_at": seen["a"], "ended": True, "talk_key": None, "snoozed_until": None},
    ]}


def test_settled_is_bounded_and_counts_every_settled_conversation(state):
    for index in range(5):
        state.conversations.adopt(f"old-{index}", f"Old {index}", "fake")
        _settle(state, f"old-{index}")

    settled = settled_conversations(state.conversations, WorkspaceCache(reader=lambda cwd: None), state.agents, limit=2)

    assert (settled["total"], [row["name"] for row in settled["items"]]) == (5, ["old-4", "old-3"])


def test_status_carries_the_settled_conversations(state):
    _settle(state, "a")

    assert status_payload(state)["settled_agents"]["total"] == 1
