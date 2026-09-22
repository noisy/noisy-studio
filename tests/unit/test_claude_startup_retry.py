import importlib
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def retry(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'hooks'))
    module = importlib.import_module('_registration_retry')
    clock = [0.0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    monkeypatch.setattr(module, '_socket_identity', Mock(return_value=(1, 2)))
    monkeypatch.setattr(module._client, 'post', Mock())
    return module


@pytest.fixture
def registration():
    return {'harness': 'claude-hooks', 'payload': {
        'hook_event_name': 'SessionStart',
        'session_id': '00000000-0000-4000-8000-000000000001',
        'noisy_studio_connection': {'socket': '/test/inbox', 'hook_protocol': 2},
    }}


def test_startup_recovers_when_daemon_becomes_available(retry, registration):
    response = {'conversation': registration['payload']['session_id'], 'listener': 'start'}
    retry._client.post.side_effect = [None, response]

    assert retry.wait_for_daemon(registration, 10) == response
    assert retry._client.post.call_args.args == (
        '/harness/event', {**registration, 'listen_seconds': 6.0})


@pytest.mark.parametrize('event', ['PreToolUse', 'UserPromptSubmit', 'Stop', 'SessionEnd'])
def test_normal_hooks_never_wait_for_startup(retry, registration, event):
    registration['payload']['hook_event_name'] = event

    assert retry.wait_for_daemon(registration) is None
    retry._client.post.assert_not_called()


@pytest.mark.parametrize('identity', [None, (1, 3)])
def test_closed_or_replaced_socket_stops_retry(retry, registration, identity):
    retry._socket_identity.side_effect = [(1, 2), identity]

    assert retry.wait_for_daemon(registration) is None
    retry._client.post.assert_not_called()


def test_explicit_rejection_is_not_retried(retry, registration):
    retry._client.post.return_value = {'error': 'rejected', 'status': 422}

    assert retry.wait_for_daemon(registration) == {'error': 'rejected', 'status': 422}
    retry._client.post.assert_called_once()


def test_wait_is_bounded(retry, registration):
    retry._client.post.return_value = None

    assert retry.wait_for_daemon(registration, 5) is None
    assert retry.time.monotonic() == 5
    assert retry._client.post.call_count == 2


def test_socket_validation_rejects_regular_files(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'hooks'))
    module = importlib.import_module('_registration_retry')
    path = tmp_path / 'not-a-socket'
    path.write_text('')

    assert module._socket_identity(str(path)) is None


def test_hook_startup_registers_after_outage_and_enables_wake(retry, registration, monkeypatch):
    from noisy_studio.harness.claude.socket_transport import WriteResult
    from noisy_studio.harness.hook_gateway import _apply_harness_event, drain
    from noisy_studio.listener.state import ListenerState
    flow = importlib.import_module('_hook_flow')
    state = ListenerState()
    monkeypatch.setattr(flow, '_listen', Mock(return_value=0))
    attempts = []

    def post(path, body):
        attempts.append(path)
        if len(attempts) == 1:
            return None
        return _apply_harness_event(state, body['harness'], body['payload'], listen_seconds=0)

    retry._client.post.side_effect = post
    assert flow.run('claude-hooks', registration['payload']) == 0
    session = registration['payload']['session_id']
    waker = state.conversations.providers.get('claude')._implementation.waker
    waker._send = Mock(return_value=WriteResult('sent', 'written'))
    utterance = state.create_utterance('user', 'transcribing', agent=session)
    state.add_transcript('Are you there?', utterance)

    assert waker.wake(session).state == 'requested'
    assert [row['text'] for row in drain(state, session, None)['transcripts']] == ['Are you there?']
    assert drain(state, session, None)['transcripts'] == []
