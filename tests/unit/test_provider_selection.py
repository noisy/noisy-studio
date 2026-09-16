import pytest

from noisy_coding.providers import config, selection


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / 'providers.json'
    monkeypatch.setattr(config, 'PROVIDERS_FILE', path)
    return path


def test_failed_preparation_preserves_the_working_provider(settings_file, monkeypatch):
    config.save(tts='grok')
    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('download', 'Download first'))

    with pytest.raises(ValueError, match='Download first'):
        selection.apply(selection.choice('kokoro:1'), selection.revision(), {'lux': 'af_sarah'}, ['lux'])

    assert config.tts_provider_name() == 'grok'


def test_local_recognition_preparation_does_not_switch_or_download_speech(settings_file, monkeypatch):
    calls = []
    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('download', 'Download first'))
    monkeypatch.setattr(selection.local, 'prefetch_models', lambda **kwargs: calls.append(kwargs))

    selection.prepare(selection.choice('whisper:small'))

    assert (calls, config.stt_provider_name()) == ([{'tts': False, 'stt': True, 'options': {'stt_model': 'small'}}], 'grok')


def test_switching_back_preserves_local_voice_assignments(settings_file, monkeypatch):
    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('ready', ''))
    selection.apply(selection.choice('kokoro:1'), selection.revision(), {'lux': 'af_sarah', 'rex': 'am_adam'}, ['lux', 'rex'])
    selection.apply(selection.choice('grok:tts'), selection.revision(), {'lux': 'lux', 'rex': 'rex'}, ['lux', 'rex'])

    assert selection.assignments(selection.choice('kokoro:1'), ['lux', 'rex']) == {'lux': 'af_sarah', 'rex': 'am_adam'}


def test_stale_window_cannot_overwrite_a_new_selection(settings_file, monkeypatch):
    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('ready', ''))
    revision = selection.revision()
    config.save(stt='local')

    with pytest.raises(ValueError, match='another window'):
        selection.apply(selection.choice('grok:stt'), revision, {}, [])

    assert config.stt_provider_name() == 'local'


def test_new_speakers_receive_distinct_suggestions(settings_file):
    result = selection.assignments(selection.choice('kokoro:1'), ['lux', 'rex', 'luna'])

    assert len(set(result.values())) == 3


def test_local_speech_rejects_an_unsupported_language(settings_file, monkeypatch):
    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('ready', ''))

    with pytest.raises(ValueError, match='supports English'):
        selection.apply(selection.choice('kokoro:1'), selection.revision(), {'lux':'af_sarah'}, ['lux'], 'pl')

    assert config.tts_provider_name() == 'grok'


def test_provider_settings_http_applies_only_the_requested_direction(settings_file, monkeypatch):
    import http.client
    import json
    from noisy_coding.listener.http_api import start_http_api
    from noisy_coding.listener.state import ListenerState

    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('ready', ''))
    monkeypatch.setattr(selection.local, 'download_status', lambda: [])
    state = ListenerState()
    server = start_http_api(state, 0)
    connection = http.client.HTTPConnection('127.0.0.1', server.server_address[1])
    try:
        connection.request('POST', '/speech-settings', json.dumps({'operation':'apply','choice':'whisper:base','revision':selection.revision(),'bindings':{}}))
        response = connection.getresponse()
        body = json.loads(response.read())
        assert (response.status, body['active'], state.drain()) == (200, {'stt':'whisper:base','tts':'grok:tts'}, [])
    finally:
        connection.close()
        server.shutdown()
