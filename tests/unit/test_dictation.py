"""Dictate anywhere: sessions, the permission gate, and transcripts that
go into the focused app instead of to any agent."""

from __future__ import annotations

import pytest

from noisy_studio.listener.dictation import MUTED_HINT, PERMISSION_HINT, Dictation
from noisy_studio.listener.state import ListenerState
from noisy_studio.listener.text_insertion import Insertion, InsertionError


class _Inline:
    """Runs submitted work at once, so the tests need no threads."""

    def submit(self, fn, *args):
        fn(*args)


class _Inserter:
    def __init__(self, error: Exception | None = None):
        self.texts: list[str] = []
        self.error = error

    def insert(self, text):
        if self.error:
            raise self.error
        self.texts.append(text)
        return Insertion(app="iTerm2")


class _Permission:
    def __init__(self, status="granted", after_request=None):
        self.value = status
        self.after_request = after_request or status
        self.requests = 0

    def status(self):
        return self.value

    def request(self):
        self.requests += 1
        self.value = self.after_request
        return self.value


@pytest.fixture
def state():
    return ListenerState()


def _dictation(state, inserter=None, permission=None):
    permission = permission or _Permission()
    controller = Dictation(
        state,
        lambda _msg: None,
        inserter=inserter or _Inserter(),
        status=permission.status,
        request=permission.request,
        executor=_Inline(),
    )
    state.dictation = controller
    return controller


def _status(state, utterance_id):
    return next(u for u in state.utterances() if u["id"] == utterance_id)["status"]


def test_a_session_number_is_stamped_on_the_state_until_stopped(state):
    dictation = _dictation(state)

    assert dictation.start() is True
    during = state.dictation_session
    dictation.stop()
    dictation.start()

    assert (during, state.dictation_session) == (1, 2)
    dictation.stop()
    assert (state.dictation_session, dictation.active) == (0, False)


def test_missing_accessibility_is_requested_and_blocks_the_session(state):
    permission = _Permission("missing")
    dictation = _dictation(state, permission=permission)

    assert dictation.start() is False

    assert (permission.requests, state.dictation_session) == (1, 0)
    assert state.events_since(0)[-1]["detail"] == PERMISSION_HINT


def test_granting_from_the_prompt_starts_the_session(state):
    dictation = _dictation(state, permission=_Permission("missing", after_request="granted"))
    assert dictation.start() is True


def test_a_muted_microphone_blocks_the_session(state):
    state.set_user_muted(True)
    dictation = _dictation(state)
    assert dictation.start() is False
    assert state.events_since(0)[-1]["detail"] == MUTED_HINT


def test_a_dictated_transcript_is_inserted_and_never_queued_for_an_agent(state):
    state.register_agent("tab-a", "Alpha")
    state.set_active_agent("tab-a")
    inserter = _Inserter()
    _dictation(state, inserter)
    utterance = state.create_utterance("user", "recording…", dictation=1)

    state.add_transcript("ls -la", utterance)

    row = next(u for u in state.utterances() if u["id"] == utterance)
    assert {
        "inserted": inserter.texts,
        "queued": state.drain("tab-a"),
        "agent": row["agent"],
        "status": row["status"],
        "text": row["text"],
    } == {
        "inserted": ["ls -la"],
        "queued": [],
        "agent": "",
        "status": "dictation — inserted into iTerm2",
        "text": "ls -la",
    }


def test_later_segments_of_one_session_get_a_leading_space(state):
    inserter = _Inserter()
    _dictation(state, inserter)
    first = state.create_utterance("user", "recording…", dictation=1)
    second = state.create_utterance("user", "recording…", dictation=1)
    next_session = state.create_utterance("user", "recording…", dictation=2)

    state.add_transcript("one", first)
    state.add_transcript("two", second)
    state.add_transcript("three", next_session)

    assert inserter.texts == ["one", " two", "three"]


def test_an_insertion_failure_is_shown_on_the_card(state):
    _dictation(state, _Inserter(InsertionError("Accessibility permission missing")))
    utterance = state.create_utterance("user", "recording…", dictation=1)

    state.add_transcript("hello", utterance)

    assert _status(state, utterance) == "dictation — not inserted: Accessibility permission missing"


def test_without_a_controller_the_dictation_is_still_never_queued(state):
    state.register_agent("tab-a", "Alpha")
    state.set_active_agent("tab-a")
    utterance = state.create_utterance("user", "recording…", dictation=1)

    state.add_transcript("hello", utterance)

    assert (state.drain("tab-a"), _status(state, utterance)) == (
        [], "dictation — not inserted: dictation is off",
    )


def test_ordinary_speech_still_goes_to_the_agent(state):
    state.register_agent("tab-a", "Alpha")
    state.set_active_agent("tab-a")
    inserter = _Inserter()
    _dictation(state, inserter)
    utterance = state.create_utterance("user", "recording…")

    state.add_transcript("hi agent", utterance)

    assert ([t.text for t in state.drain("tab-a")], inserter.texts) == (["hi agent"], [])


def test_snapshot_reports_permission_and_session(state):
    dictation = _dictation(state, permission=_Permission("missing"))
    assert dictation.snapshot() == {"permission": "missing", "active": False}
