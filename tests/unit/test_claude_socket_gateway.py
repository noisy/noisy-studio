from unittest.mock import Mock

import pytest

from noisy_studio.harness import agent_provider
from noisy_studio.harness.claude.socket_transport import WriteResult
from noisy_studio.harness.hook_gateway import _apply_harness_event, drain
from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.state import ListenerState

SESSION = '00000000-0000-4000-8000-000000000001'


@pytest.fixture(autouse=True)
def direct_socket_selection(monkeypatch):
    monkeypatch.setattr(agent_provider, 'CLAUDE_DELIVERY', 'socket')


def register(state, endpoint, **extra):
    return _apply_harness_event(state, 'claude-hooks', {
        'hook_event_name': 'SessionStart', 'session_id': SESSION,
        'noisy_studio_connection': {'socket': str(endpoint)}, **extra,
    })


def test_socket_selection_disables_start_stop_and_posttool_consumers_but_keeps_identity(tmp_path):
    state = ListenerState()
    started = register(state, tmp_path / 'inbox')
    stopped = _apply_harness_event(state, 'claude-hooks', {'hook_event_name': 'Stop', 'session_id': SESSION})
    post = _apply_harness_event(state, 'claude-hooks', {'hook_event_name': 'PostToolUse', 'session_id': SESSION})
    identity = _apply_harness_event(state, 'claude-hooks', {
        'hook_event_name': 'PreToolUse', 'session_id': SESSION, 'tool_name': 'mcp__noisy_studio__speak',
    })

    assert (started['listener'], stopped['listener'], post['may_drain'], identity['speech_identity']) == ('none', 'none', False, SESSION)
    assert 'acknowledge_delivery' in started['registration_context']
    assert 'registration_context' not in post
    assert drain(state, SESSION, 'old-listener')['stand_down'] is True
    assert drain(state, None, None)['stand_down'] is True


def test_participant_registration_cannot_replace_parent_endpoint(tmp_path):
    state = ListenerState()
    register(state, tmp_path / 'parent')
    register(state, tmp_path / 'child', agent_id='child-1')
    implementation = state.conversations.providers.get('claude')._implementation

    assert implementation._endpoints[SESSION].path == str(tmp_path / 'parent')


def test_daemon_restart_requires_registration_and_never_replays_written_speech(tmp_path):
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    register(state, tmp_path / 'inbox')
    implementation = state.conversations.providers.get('claude')._implementation
    implementation._send = Mock(return_value=WriteResult('sent', 'unconfirmed'))
    implementation._clock = lambda: 10**12
    utterance = state.create_utterance('user', 'transcribing', agent=SESSION)
    state.add_transcript('only once', utterance)
    implementation.flush(state.record_delivery, state.reserve_speech)
    restored = ListenerState()
    restored.load_utterances(state.snapshot_utterances())
    restored.load_transcripts(state.snapshot_transcripts())
    restored.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    provider = restored.conversations.providers.get('claude')
    assert provider.availability(SESSION).interaction_required is True
    register(restored, tmp_path / 'new-inbox')
    provider._implementation._send = Mock()
    provider._implementation._clock = lambda: 10**12

    provider._implementation.flush(restored.record_delivery, restored.reserve_speech)

    provider._implementation._send.assert_not_called()
    assert (len(restored.snapshot_transcripts()), restored.cancel_transcript(utterance)) == (1, False)


@pytest.mark.parametrize('expire', [False, True], ids=['sent', 'unknown'])
def test_deliberate_hook_rollback_preserves_identity_and_holds_unconfirmed_speech(tmp_path, monkeypatch, expire):
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    register(state, tmp_path / 'inbox')
    implementation = state.conversations.providers.get('claude')._implementation
    implementation._send = Mock(return_value=WriteResult('sent', 'unconfirmed'))
    implementation._clock = lambda: 10**12
    utterance = state.create_utterance('user', 'transcribing', agent=SESSION)
    state.add_transcript('do not resend', utterance)
    implementation.flush(state.record_delivery, state.reserve_speech)
    implementation._clock = lambda: 10**12 + (60 if expire else 0)
    implementation.flush(state.record_delivery, state.reserve_speech)
    assert state.cancel_transcript(utterance) is False
    monkeypatch.setattr(agent_provider, 'CLAUDE_DELIVERY', 'hooks')
    restored = ListenerState()
    restored.load_utterances(state.snapshot_utterances())
    restored.load_transcripts(state.snapshot_transcripts())
    restored.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    restored.conversations.providers.start(restored.record_delivery, restored.reserve_speech, lambda: False)

    response = register(restored, tmp_path / 'unused-inbox')
    picked_up = drain(restored, SESSION, response['listener_id'])

    assert (restored.conversations.keys(), response['listener'], picked_up['transcripts']) == ([SESSION], 'start', [])
    assert restored.conversations.get(SESSION).harness == 'claude'


def test_journal_recovers_pending_speech_missing_from_periodic_history(tmp_path):
    from noisy_studio.harness.provider import Speech
    from noisy_studio.harness.claude.journal import Journal
    speech = Speech(23, SESSION, 'preserve this pending message', 100)
    Journal(tmp_path / 'claude-delivery.sqlite3').add(speech)
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    register(state, tmp_path / 'inbox')
    provider = state.conversations.providers.get('claude')

    provider._implementation.start(state.record_delivery, state.reserve_speech, lambda: False, state.restore_delivery)
    provider._implementation.stop()

    assert [(r['utterance_id'], r['text']) for r in state.snapshot_transcripts()] == [(23, speech.text)]
    assert state.snapshot_utterances()[0]['id'] == 23


def test_durable_cancellation_removes_an_older_history_copy_on_restart(tmp_path):
    from noisy_studio.harness.provider import Speech
    from noisy_studio.harness.claude.journal import Journal
    speech = Speech(23, SESSION, 'cancelled message', 100)
    journal = Journal(tmp_path / 'claude-delivery.sqlite3')
    journal.add(speech)
    journal.cancel(speech)
    state = ListenerState()
    state.load_transcripts([{'utterance_id': 23, 'text': speech.text, 'timestamp': 100, 'addressee': SESSION}])
    state.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    register(state, tmp_path / 'inbox')
    provider = state.conversations.providers.get('claude')

    provider._implementation.start(state.record_delivery, state.reserve_speech, lambda: False, state.restore_delivery)
    provider._implementation.stop()

    assert state.snapshot_transcripts() == []


def test_hook_pickup_during_rollback_is_not_replayed_when_sockets_return(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_provider, 'CLAUDE_DELIVERY', 'hooks')
    state = ListenerState()
    state.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    response = register(state, tmp_path / 'unused')
    utterance = state.create_utterance('user', 'transcribing', agent=SESSION)
    state.add_transcript('one pickup', utterance)
    assert len(drain(state, SESSION, response['listener_id'])['transcripts']) == 1
    monkeypatch.setattr(agent_provider, 'CLAUDE_DELIVERY', 'socket')
    restored = ListenerState()
    restored.conversations = ConversationRegistry(path=tmp_path / 'conversations.json')
    register(restored, tmp_path / 'inbox')
    implementation = restored.conversations.providers.get('claude')._implementation
    implementation._send = Mock()
    implementation._clock = lambda: 10**12

    implementation.flush(restored.record_delivery, restored.reserve_speech)

    implementation._send.assert_not_called()
