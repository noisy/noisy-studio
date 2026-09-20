from unittest.mock import Mock

import pytest

from noisy_coding.harness.claude.journal import Journal
from noisy_coding.harness.claude.socket_transport import WriteResult
from noisy_coding.harness.hook_gateway import _apply_harness_event, drain
from noisy_coding.listener.conversations import ConversationRegistry
from noisy_coding.listener.state import ListenerState

SESSION = '00000000-0000-4000-8000-000000000001'
OTHER = '00000000-0000-4000-8000-000000000002'


@pytest.fixture
def world(tmp_path):
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    _apply_harness_event(state, 'claude-hooks', {
        'hook_event_name': 'SessionStart', 'session_id': SESSION,
        'noisy_studio_connection': {'socket': str(tmp_path / 'inbox'), 'hook_protocol': 2},
    }, listen_seconds=0)
    provider = state.conversations.providers.get('claude')
    waker = provider._implementation.waker
    waker._send = Mock(return_value=WriteResult('sent', 'wake written'))
    waker._clock = lambda: 10**12
    return state, provider, waker


def queue(state, text='Actual user speech'):
    utterance = state.create_utterance('user', 'transcribing', agent=SESSION)
    state.add_transcript(text, utterance)
    return utterance


def receive(state, prompt, session=SESSION):
    return _apply_harness_event(state, 'claude-hooks', {
        'hook_event_name': 'UserPromptSubmit', 'session_id': session, 'prompt': prompt,
        'noisy_studio_connection': {'socket': 'registered-test-endpoint', 'hook_protocol': 2},
    })


def test_socket_carries_only_a_wake_and_hook_delivers_grouped_speech_once(world):
    state, provider, waker = world
    queue(state, 'first part')
    queue(state, 'second part')

    waker.tick(state.record_delivery)
    waker.tick(state.record_delivery)
    prompt = waker._send.call_args.args[1]
    assert prompt.startswith('Noisy Studio is waking Claude')
    assert 'first part' not in prompt and 'second part' not in prompt
    assert len(state.snapshot_transcripts()) == 2
    response = receive(state, prompt)

    assert 'first part' in response['wake_delivery']['context']
    assert 'second part' in response['wake_delivery']['context']
    assert 'Receipt IDs' not in response['wake_delivery']['context']
    assert state.snapshot_transcripts() == []
    assert receive(state, prompt)['suppress_empty_wake'] is True
    assert [r.state for _, r in provider._implementation.journal.entries()] == ['confirmed', 'confirmed']
    waker._send.assert_called_once()


def test_normal_hook_pickup_needs_no_socket_and_racing_wake_is_empty(world):
    state, provider, waker = world
    queue(state)
    picked_up = drain(state, SESSION, None)
    waker.tick(state.record_delivery)
    assert len(picked_up['transcripts']) == 1
    waker._send.assert_not_called()

    queue(state, 'second message')
    waker.tick(state.record_delivery)
    prompt = waker._send.call_args.args[1]
    drain(state, SESSION, None)

    assert receive(state, prompt)['suppress_empty_wake'] is True


def test_wake_cannot_consume_another_sessions_speech(world):
    state, provider, waker = world
    queue(state)
    waker.tick(state.record_delivery)
    prompt = waker._send.call_args.args[1]

    response = receive(state, prompt, OTHER)

    assert 'wake_delivery' not in response
    assert len(state.snapshot_transcripts()) == 1


def test_pending_wake_survives_restart_without_a_duplicate_write(world):
    from noisy_coding.harness.claude.socket_wake import SocketWake
    from noisy_coding.harness.provider import Registration
    state, provider, waker = world
    queue(state)
    waker.tick(state.record_delivery)
    prompt = waker._send.call_args.args[1]
    restored = SocketWake(Journal(provider._implementation.journal._path), sender=Mock())
    restored.attach(Registration(SESSION, SESSION, {'socket': 'same-session', 'hook_protocol': 2}))

    assert restored.wake(SESSION).state == 'pending'
    restored._send.assert_not_called()
    assert restored.accept_wake(SESSION, prompt) is True


def test_cancelled_speech_and_hidden_sessions_are_not_woken(world):
    state, provider, waker = world
    utterance = queue(state)
    assert state.cancel_transcript(utterance) is True
    waker.tick(state.record_delivery)
    queue(state, 'hidden message')
    state.conversations.hide(SESSION)
    waker.tick(state.record_delivery)

    waker._send.assert_not_called()


def test_continuation_window_allows_normal_pickup_before_waking(world):
    state, provider, waker = world
    queue(state)
    created = provider._implementation.journal.entries()[0][0].created_at
    waker._clock = lambda: created + 2.9
    waker.tick(state.record_delivery)
    waker._send.assert_not_called()

    waker._clock = lambda: created + 3
    waker.tick(state.record_delivery)

    waker._send.assert_called_once()


def test_recording_extends_wake_delay_but_not_beyond_the_continuation_cap(world):
    state, provider, waker = world
    queue(state)
    created = provider._implementation.journal.entries()[0][0].created_at
    waker._clock = lambda: created + 10
    waker.tick(state.record_delivery, recording=lambda: True)
    waker._send.assert_not_called()

    waker._clock = lambda: created + 20
    waker.tick(state.record_delivery, recording=lambda: True)

    waker._send.assert_called_once()


def test_explicit_session_restart_allows_new_control_but_not_duplicate_speech(world):
    from noisy_coding.harness.base import Event
    state, provider, waker = world
    queue(state)
    waker.tick(state.record_delivery)
    old_prompt = waker._send.call_args.args[1]
    waker.observe([Event('session_started', SESSION)])
    waker.tick(state.record_delivery)
    new_prompt = waker._send.call_args.args[1]

    assert receive(state, new_prompt)['wake_delivery'] is not None
    assert receive(state, old_prompt)['suppress_empty_wake'] is True
    assert state.snapshot_transcripts() == []


def test_old_hook_is_not_sent_a_wake_it_cannot_consume(world):
    state, provider, waker = world
    queue(state)
    _apply_harness_event(state, 'claude-hooks', {
        'hook_event_name': 'UserPromptSubmit', 'session_id': SESSION,
        'noisy_studio_connection': {'socket': 'old-hook-endpoint'},
    })

    waker.tick(state.record_delivery)

    waker._send.assert_not_called()
    assert 'Update Noisy Studio hooks' in waker.availability(SESSION).reason
    assert len(state.snapshot_transcripts()) == 1
