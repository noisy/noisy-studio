import socket
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from noisy_studio.harness.claude.socket_transport import WriteResult
from noisy_studio.harness.hook_gateway import _apply_harness_event, drain
from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.state import ListenerState

SESSION = '00000000-0000-4000-8000-000000000001'


@pytest.fixture
def connected(tmp_path):
    endpoint = socket.socket(socket.AF_UNIX)
    socket_directory = tempfile.TemporaryDirectory(prefix='nr-', dir='/tmp')
    path = socket_directory.name + '/inbox'
    endpoint.bind(path)
    endpoint.listen()
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    _apply_harness_event(state, 'claude', {
        'hook_event_name': 'SessionStart', 'session_id': SESSION,
        'noisy_studio_connection': {'socket': path, 'hook_protocol': 2},
    }, listen_seconds=0)
    yield state
    endpoint.close()
    socket_directory.cleanup()


def restart(state):
    restored = ListenerState()
    restored.conversations = ConversationRegistry(path=state.conversations._path)
    provider = restored.conversations.providers.get('claude')
    waker = provider._implementation.waker
    waker._send = Mock(return_value=WriteResult('sent', 'written'))
    waker._clock = lambda: 10**12
    waker.start = Mock()
    restored.conversations.providers.start(restored.record_delivery, restored.reserve_speech,
                                          lambda: False, restored.restore_delivery)
    return restored, provider, waker


def queue(state):
    utterance = state.create_utterance('user', 'transcribing', agent=SESSION)
    state.add_transcript('Please confirm recovery.', utterance)
    return utterance


@pytest.mark.parametrize('queued_before_restart', [False, True])
def test_restart_recovers_voice_without_a_fresh_hook(connected, queued_before_restart):
    if queued_before_restart:
        queue(connected)
    restored, provider, waker = restart(connected)
    assert provider.availability(SESSION).ready is True
    waker._send.assert_not_called()
    if not queued_before_restart:
        queue(restored)
    waker.tick(restored.record_delivery)
    prompt = waker._send.call_args.args[1]
    assert provider.accept_wake(SESSION, prompt) is True
    assert [row['text'] for row in drain(restored, SESSION, None)['transcripts']] == ['Please confirm recovery.']
    again, _, next_waker = restart(restored)
    next_waker.tick(again.record_delivery)
    next_waker._send.assert_not_called()


def test_restart_keeps_pending_wake_and_accepts_its_late_arrival(connected):
    queue(connected)
    provider = connected.conversations.providers.get('claude')
    waker = provider._implementation.waker
    waker._send = Mock(return_value=WriteResult('uncertain', 'write interrupted'))
    waker.wake(SESSION)
    prompt = waker._send.call_args.args[1]
    restored, provider, waker = restart(connected)
    waker.tick(restored.record_delivery)
    waker._send.assert_not_called()
    assert provider.accept_wake(SESSION, prompt) is True
    drain(restored, SESSION, None)
    assert provider.accept_wake(SESSION, prompt) is True
    assert drain(restored, SESSION, None)['transcripts'] == []


@pytest.mark.parametrize('condition', ['hidden', 'ended', 'missing_socket', 'old_protocol', 'corrupt_record'])
def test_restart_does_not_restore_an_unusable_connection(connected, condition):
    provider = connected.conversations.providers.get('claude')
    journal = provider._implementation.journal
    registration = journal.registrations()[0]
    if condition == 'hidden':
        connected.conversations.hide(SESSION)
    elif condition == 'ended':
        _apply_harness_event(connected, 'claude', {'hook_event_name': 'SessionEnd', 'session_id': SESSION})
    elif condition == 'missing_socket':
        Path(registration.connection['socket']).unlink()
    elif condition == 'old_protocol':
        registration.connection['hook_protocol'] = 1
        journal.save_registration(registration)
    else:
        journal._db().execute("UPDATE registrations SET registration='invalid json'")
        journal._db().commit()
    restored, provider, waker = restart(connected)
    assert provider.availability(SESSION).ready is False
    assert waker.wake(SESSION).state == 'unavailable'
    waker._send.assert_not_called()


def test_speech_waiting_for_missing_registration_survives_another_restart(connected):
    journal = connected.conversations.providers.get('claude')._implementation.journal
    journal.forget_registration(SESSION)
    restored, _, _ = restart(connected)
    queue(restored)
    again, _, _ = restart(restored)
    assert [row['text'] for row in again.snapshot_transcripts()] == ['Please confirm recovery.']
