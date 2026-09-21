from unittest.mock import Mock

import numpy as np
import pytest

from noisy_studio import providers
from noisy_studio.listener import daemon, stt
from noisy_studio.listener.state import ListenerState


@pytest.fixture
def captured_recognition(monkeypatch):
    state = ListenerState()
    state.set_language('en')
    original = Mock(label='Original recognizer')
    original.cost_usd.return_value = 0.1
    original.streaming_cost_usd.return_value = 0.2
    original.transcribe.return_value = 'Keep this recording on its original engine.'
    monkeypatch.setattr(providers, 'active_stt', lambda: original)
    request = daemon.RecognitionRequest.capture(state)
    state.set_language('pl')
    replacement = Mock()
    monkeypatch.setattr(providers, 'active_stt', lambda: replacement)
    return state, request, original, replacement


def test_batch_turn_uses_engine_and_language_captured_before_settings_changed(captured_recognition):
    state, request, original, replacement = captured_recognition
    samples = np.zeros(1600, dtype=np.int16)
    utterance = state.create_utterance('user', 'recording…')

    daemon._transcribe_and_enqueue(samples, 16000, state, utterance, request)

    original.transcribe.assert_called_once_with(stt.encode_wav(samples, 16000), 'en')
    replacement.transcribe.assert_not_called()


def test_streamed_turn_charges_the_captured_engine_after_settings_changed(captured_recognition):
    state, request, original, replacement = captured_recognition
    utterance = state.create_utterance('user', 'recording…')
    session = Mock()
    session.finish.return_value = 'The original stream finished.'

    daemon._finalize_stream(session, 2.0, state, utterance, request)

    original.streaming_cost_usd.assert_called_once_with(2.0)
    replacement.streaming_cost_usd.assert_not_called()
