"""Agent provider contract: no hook events, output formats or listener leases."""
from unittest.mock import Mock

import pytest

from noisy_coding.harness.agent_provider import AgentProvider, AgentProviders
from noisy_coding.harness.base import Event, Observation
from noisy_coding.harness.provider import Availability, ProviderCapabilities, Receipt, Registration, Speech
from noisy_coding.listener.state import ListenerState


@pytest.fixture
def provider_world():
    state = ListenerState()
    transport = Mock()
    transport.attach.return_value = Availability(True)
    transport.availability.return_value = Availability(True)
    transport.submit.side_effect = lambda speech: Receipt(speech.utterance_id, speech.conversation, 'sent', 'unconfirmed')
    provider = AgentProvider('test-agent', 'Test agent', transport, ProviderCapabilities(True, True, True, 'transport'))
    state.conversations.providers = AgentProviders(state.conversations, {provider.name: provider})
    for key in ('session-1', 'session-2'):
        provider.attach(Registration(key, key))
        state.conversations.observe(provider, Observation(key, (Event('session_started', key),)))
    return state, provider, transport


def test_core_submits_to_the_recording_recipient_even_after_active_tab_changes(provider_world):
    state, _provider, transport = provider_world
    utterance = state.create_utterance('user', 'transcribing', agent='session-1')
    state.register_agent('session-2', 'Second session')
    state.set_active_agent('session-2')

    state.add_transcript('the original recipient', utterance)

    submitted = transport.submit.call_args.args[0]
    assert (submitted.utterance_id, submitted.conversation, submitted.text, submitted.provenance) == (
        utterance, 'session-1', 'the original recipient', 'user speech transcribed by Noisy Studio',
    )
    assert (state.queued_count, len(state.snapshot_transcripts())) == (0, 1)  # Retained, but no longer waiting to send.


def test_participant_cannot_replace_the_parent_connection(provider_world):
    _state, provider, transport = provider_world
    transport.attach.reset_mock()

    provider.attach(Registration('session-1', 'child-session', connection=object(), participant='child-1'))

    transport.attach.assert_not_called()


@pytest.mark.parametrize('outcome', ['queued', 'sent', 'accepted', 'confirmed', 'rejected', 'unavailable', 'uncertain'])
def test_provider_preserves_observed_receipt_strength_and_correlation(provider_world, outcome):
    _state, provider, transport = provider_world
    speech = Speech(7, 'session-1', 'hello', 123.0)
    expected = Receipt(7, 'session-1', outcome, 'observed result', message_id='message-1', turn_id='turn-1')
    transport.submit.side_effect = None
    transport.submit.return_value = expected

    assert provider.submit(speech) == expected


def test_unregistered_session_never_uses_another_sessions_transport(provider_world):
    _state, provider, transport = provider_world

    result = provider.submit(Speech(8, 'session-3', 'hello', 124.0))

    assert result == Receipt(8, 'session-3', 'unavailable', 'Open this conversation in your agent and type and send any message to reconnect voice delivery. No special command is needed.')
    transport.submit.assert_not_called()


def test_conversation_status_uses_provider_readiness(provider_world):
    state, _provider, transport = provider_world
    assert state.conversations.status('session-1') == 'idle'
    transport.availability.return_value = Availability(False, 'register again', True)

    assert state.conversations.status('session-1') == 'deaf'


def test_legacy_provider_identifiers_resolve_to_the_same_provider():
    state = ListenerState()
    providers = state.conversations.providers

    assert providers.get('claude') is providers.get('claude-hooks')
    assert providers.get('codex') is providers.get('codex-hooks')


def test_confirmation_retires_only_its_original_pending_utterance(provider_world):
    state, _provider, transport = provider_world
    first = state.create_utterance('user', 'transcribing', agent='session-1')
    second = state.create_utterance('user', 'transcribing', agent='session-2')
    state.add_transcript('first', first)
    speech = transport.submit.call_args.args[0]
    state.add_transcript('second', second)

    state.record_delivery(speech, Receipt(first, 'session-1', 'confirmed'))

    assert [(row['utterance_id'], row['addressee']) for row in state.snapshot_transcripts()] == [(second, 'session-2')]


def test_mismatched_receipt_cannot_retire_someone_elses_speech(provider_world):
    state, _provider, _transport = provider_world

    with pytest.raises(ValueError, match='does not match'):
        state.record_delivery(Speech(1, 'session-1', 'first', 1), Receipt(1, 'session-2', 'confirmed'))


def test_legacy_hook_cannot_consume_a_push_providers_queue(provider_world):
    from noisy_coding.harness.hook_gateway import drain
    state, _provider, _transport = provider_world
    utterance = state.create_utterance('user', 'transcribing', agent='session-1')
    state.add_transcript('for the push provider', utterance)

    result = drain(state, 'session-1', None)

    assert (result, state.queued_count) == ({'transcripts': [], 'nudge': None, 'stand_down': True}, 0)
