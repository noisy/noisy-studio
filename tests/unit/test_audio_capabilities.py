import json
from types import SimpleNamespace
import pytest
from noisy_studio import providers
from noisy_studio.listener.audio_capabilities import audio_capabilities
from noisy_studio.providers.base import STTError
from noisy_studio.providers.grok import GrokSTT, GrokTTS
from noisy_studio.providers.local import LocalSTT, LocalTTS


def test_grok_metadata_separates_language_formatting_from_synthesis():
    stt = GrokSTT().capabilities
    tts = GrokTTS({}).capabilities
    assert {
        'stt_purpose': stt.languages.purpose,
        'stt_polish': 'pl' in stt.languages.codes,
        'tts_purpose': tts.languages.purpose,
        'tts_exhaustive': tts.languages.exhaustive,
        'smart_turn_modes': stt.smart_turn.modes,
        'tts_smart_turn': tts.smart_turn,
    } == {'stt_purpose': 'formatting', 'stt_polish': True, 'tts_purpose': 'synthesis',
          'tts_exhaustive': False, 'smart_turn_modes': ('live',), 'tts_smart_turn': None}


@pytest.mark.parametrize('model,english_only,cantonese', [('base.en', True, False), ('base', False, False), ('large-v3', False, True)])
def test_whisper_language_contract_matches_selected_model(model, english_only, cantonese):
    caps = LocalSTT({'stt_model': model}).capabilities
    assert {'english_only': caps.languages.codes == ('en',), 'cantonese': 'yue' in caps.languages.codes,
            'auto': caps.languages.auto_detect, 'modes': caps.modes, 'smart': caps.smart_turn} == {
        'english_only': english_only, 'cantonese': cantonese, 'auto': not english_only, 'modes': ('batch',), 'smart': None}


def test_custom_whisper_model_does_not_claim_a_language_list():
    caps = LocalSTT({'stt_model': '/custom/model'}).capabilities
    assert (caps.languages.codes, caps.languages.auto_detect) == (None, None)


@pytest.mark.parametrize('engine,codes,selectable,purpose', [
    ('kokoro', ('en', 'en-US', 'en-GB'), True, 'synthesis'), ('say', None, False, 'voice'),
])
def test_local_speech_metadata_reflects_integration_limits(engine, codes, selectable, purpose):
    caps = LocalTTS({'tts_engine': engine}).capabilities
    assert (caps.languages.codes, caps.languages.selectable, caps.languages.purpose, caps.modes) == (codes, selectable, purpose, ('batch',))


def test_status_contract_serializes_provider_facts_and_local_turn_controls(monkeypatch):
    caps = LocalSTT({'stt_model': 'base.en'}).capabilities
    monkeypatch.setattr(providers, 'active_stt', lambda: SimpleNamespace(name='test-stt', capabilities=caps))
    monkeypatch.setattr(providers, 'active_tts', lambda: SimpleNamespace(name='test-tts', capabilities=caps))
    result = json.loads(json.dumps(audio_capabilities()))
    assert {'provider': result['stt']['provider'], 'model': result['stt']['model'],
            'languages': result['stt']['languages']['codes'], 'turn': result['turn_detection']} == {
        'provider': 'test-stt', 'model': 'base.en', 'languages': ['en'],
        'turn': {'owner': 'application', 'modes': ['auto', 'ptt']}}


def test_unavailable_direction_does_not_hide_the_other_provider(monkeypatch):
    def unavailable():
        raise STTError('Not configured')
    monkeypatch.setattr(providers, 'active_stt', unavailable)
    monkeypatch.setattr(providers, 'active_tts', lambda: LocalTTS({'tts_engine': 'say'}))
    result = audio_capabilities()
    assert (result['stt'], result['tts']['model']) == (None, 'say')
