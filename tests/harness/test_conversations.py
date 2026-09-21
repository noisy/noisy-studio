"""The ten scenarios from docs/agent-integration-analysis.md §6, in-process.

FakeSession produces what a client would send, FakeHarness interprets it,
ConversationRegistry is the thing under test. A fake clock makes an hour
pass in a line.
"""

from __future__ import annotations

import pytest

from noisy_studio.harness.base import Capabilities
from noisy_studio.harness.fake.adapter import FakeHarness, FakeSession
from noisy_studio.listener.conversations import ConversationRegistry


class Clock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def world(tmp_path):
    clock = Clock()
    harness = FakeHarness()
    registry = ConversationRegistry(clock=clock, path=tmp_path / "conversations.json")

    def feed(payload: dict):
        result = harness.interpret(payload)
        registry.apply(harness.name, result, harness.capabilities)
        return result

    return clock, harness, registry, feed


def test_01_speak_before_any_hook_is_unknown_not_a_new_tab(world):
    _clock, _harness, registry, feed = world
    session = FakeSession()
    assert registry.resolve(session.session_id) is None
    assert registry.keys() == []
    feed(session.start())
    assert registry.resolve(session.session_id) == session.conversation
    assert registry.keys() == [session.conversation]


def test_02_resume_with_a_rotated_id_lands_on_the_same_tab(world):
    _clock, _harness, registry, feed = world
    session = FakeSession()
    feed(session.start())
    old_id = session.session_id
    feed(session.prompt())
    feed(session.stop())
    new_id = session.rotate_id()
    feed(session.start(source="resume"))
    assert registry.keys() == [session.conversation]
    assert registry.resolve(old_id) == session.conversation
    assert registry.resolve(new_id) == session.conversation
    assert registry.get(session.conversation).aliases == [old_id, new_id]


def test_03_daemon_restart_keeps_tabs_order_titles_and_aliases(world, tmp_path):
    clock, harness, registry, feed = world
    first, second = FakeSession(title="alpha"), FakeSession(title="beta")
    feed(first.start())
    feed(second.start())
    feed(first.rename("alpha renamed"))
    registry.reorder([second.conversation, first.conversation])
    reborn = ConversationRegistry(clock=clock, path=tmp_path / "conversations.json")
    assert reborn.keys() == [second.conversation, first.conversation]
    assert reborn.get(first.conversation).title == "alpha renamed"
    assert reborn.resolve(first.session_id) == first.conversation
    # Nobody is listening yet after a restart, and the tab says so.
    assert reborn.status(first.conversation) == "deaf"
    assert reborn.deaf_reason(first.conversation) == "daemon restarted"


def test_04_agent_restart_in_the_same_conversation_reuses_the_tab(world):
    _clock, _harness, registry, feed = world
    session = FakeSession()
    feed(session.start())
    feed(session.end())
    assert registry.status(session.conversation) == "ended"
    session.rotate_id()
    feed(session.start(source="startup"))
    assert registry.keys() == [session.conversation]
    assert registry.status(session.conversation) != "ended"


def test_05_subagent_is_a_participant_and_never_drains(world):
    _clock, _harness, registry, feed = world
    session = FakeSession()
    feed(session.start())
    feed(session.prompt())
    feed(session.subagent_start("sub-1"))
    child = feed(session.tool_done(participant="sub-1"))
    parent = feed(session.tool_done())
    assert child.may_drain is False and parent.may_drain is True
    assert child.conversation == parent.conversation == session.conversation
    assert registry.get(session.conversation).participants == {"sub-1": pytest.approx(1000.0)}
    feed(session.subagent_stop("sub-1"))
    assert registry.get(session.conversation).participants == {}
    assert registry.keys() == [session.conversation]


def test_06_two_sessions_are_two_tabs_the_newer_on_the_right(world):
    _clock, _harness, registry, feed = world
    first, second = FakeSession(), FakeSession()
    feed(first.start())
    feed(second.start())
    assert registry.keys() == [first.conversation, second.conversation]
    assert registry.resolve(first.session_id) != registry.resolve(second.session_id)


def test_07_after_the_listener_expires_the_tab_is_deaf_not_silent(world):
    clock, _harness, registry, feed = world
    session = FakeSession()
    feed(session.start())
    listener = registry.listener_started(session.conversation)
    assert registry.status(session.conversation) == "idle"
    clock.advance(61 * 60)
    assert registry.listener_alive(session.conversation, listener) is False
    assert registry.status(session.conversation) == "deaf"
    registry.listener_stopped(session.conversation, listener, reason="timeout")
    assert registry.deaf_reason(session.conversation) == "timeout"
    # A push harness never goes deaf.
    push = FakeHarness(Capabilities("push", None, "events", True, False))
    pushed = FakeSession()
    registry.apply(push.name, push.interpret(pushed.start()), push.capabilities)
    clock.advance(24 * 3600)
    assert registry.status(pushed.conversation) == "idle"


def test_08_an_id_of_one_conversation_never_resolves_to_another(world):
    _clock, _harness, registry, feed = world
    a, b = FakeSession(), FakeSession()
    feed(a.start())
    feed(b.start())
    b.rotate_id()
    feed(b.start(source="resume"))
    assert registry.resolve(a.session_id) == a.conversation
    for alias in registry.get(b.conversation).aliases:
        assert registry.resolve(alias) == b.conversation


def test_09_manual_order_and_hidden_tabs_survive(world, tmp_path):
    clock, _harness, registry, feed = world
    a, b, c = FakeSession(), FakeSession(), FakeSession()
    for s in (a, b, c):
        feed(s.start())
    registry.reorder([c.conversation, a.conversation])
    assert registry.keys() == [c.conversation, a.conversation, b.conversation]
    registry.hide(a.conversation)
    assert registry.visible_keys() == [c.conversation, b.conversation]
    registry.unhide(a.conversation)
    assert registry.visible_keys() == [c.conversation, b.conversation, a.conversation]
    reborn = ConversationRegistry(clock=clock, path=tmp_path / "conversations.json")
    assert reborn.keys() == registry.keys()


def test_10_a_stale_listener_stands_down_when_a_newer_one_starts(world):
    _clock, _harness, registry, feed = world
    session = FakeSession()
    feed(session.start())
    first = registry.listener_started(session.conversation)
    feed(session.prompt())
    feed(session.stop())
    second = registry.listener_started(session.conversation)
    assert registry.listener_alive(session.conversation, first) is False
    assert registry.listener_alive(session.conversation, second) is True
    # The stale one stopping must not blind the current one.
    registry.listener_stopped(session.conversation, first, reason="stood down")
    assert registry.listener_alive(session.conversation, second) is True
    assert registry.status(session.conversation) == "idle"


def test_status_live_while_a_turn_is_open_and_heuristic_activity_counts(world):
    clock, _harness, registry, feed = world
    session = FakeSession()
    feed(session.start())
    feed(session.prompt())
    assert registry.status(session.conversation) == "live"
    feed(session.stop())
    assert registry.status(session.conversation) == "deaf"  # no listener yet
    heuristic = FakeHarness(Capabilities("long_poll", 60.0, "heuristic", True, False))
    busy = FakeSession()
    registry.apply(heuristic.name, heuristic.interpret(busy.start()), heuristic.capabilities)
    registry.apply(heuristic.name, heuristic.interpret(busy.tool("Edit")), heuristic.capabilities)
    assert registry.status(busy.conversation) == "live"
    clock.advance(200)
    assert registry.status(busy.conversation) == "deaf"


def test_snapshot_carries_what_a_tab_needs(world):
    _clock, _harness, registry, feed = world
    session = FakeSession(title="reksio")
    feed(session.start())
    registry.listener_started(session.conversation)
    tab = registry.snapshot()[session.conversation]
    assert tab["label"] == "reksio"
    assert tab["status"] == "idle"
    assert tab["listening_until"] == pytest.approx(1060.0)
    assert tab["aliases"] == [session.session_id]
