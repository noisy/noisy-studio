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
    monkeypatch.setattr(selection.local, 'prefetch_models', lambda **kwargs: calls.append(kwargs) or True)

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


def test_busy_download_reports_rejection_without_changing_settings(settings_file, monkeypatch):
    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('download', 'Download first'))
    monkeypatch.setattr(selection.local, 'prefetch_models', lambda **kwargs: False)
    original = selection.revision()

    with pytest.raises(ValueError, match='Another model is being prepared'):
        selection.prepare(selection.choice('whisper:small'))

    assert selection.revision() == original


@pytest.mark.parametrize('state', ['ready', 'downloading'])
def test_preparing_an_available_or_in_progress_engine_is_idempotent(settings_file, monkeypatch, state):
    monkeypatch.setattr(selection, 'readiness', lambda candidate: (state, ''))
    def unexpected_download(**kwargs):
        pytest.fail('An available or in-progress model must not start another download')
    monkeypatch.setattr(selection.local, 'prefetch_models', unexpected_download)

    selection.prepare(selection.choice('whisper:small'))


def test_third_provider_uses_the_shared_selection_lifecycle(settings_file, monkeypatch):
    from noisy_coding.providers import engine_registry
    candidate = dict(id='example:voice', provider='example', direction='tts')
    prepared = []
    engine = engine_registry.EngineAdapter(
        choices=lambda: [candidate],
        options=lambda choice: {'model': 'voice-v2'},
        readiness=lambda choice: ('ready', ''),
        voices=lambda choice: [{'id': 'voice-a', 'label': 'Voice A'}],
        prepare=lambda choice: prepared.append(choice['id']),
        active_choice=lambda direction: 'example:voice',
        validate_language=lambda choice, language: None,
    )
    monkeypatch.setitem(engine_registry.adapters, 'example', engine)

    selected = selection.choice('example:voice')
    selection.apply(selected, selection.revision(), {'lux': 'voice-a'}, ['lux'])

    assert {
        'labels': selection.active_voice_labels(),
        'active': selection.active_choices()['tts'],
        'bindings': selection.assignments(selected, ['lux']),
        'options': config.provider_options('example'),
    } == {
        'labels': {'lux': 'Voice A'},
        'active': 'example:voice',
        'bindings': {'lux': 'voice-a'},
        'options': {'model': 'voice-v2', 'voice_bindings': {'lux': 'voice-a'}, 'voice_bindings_by_engine': {'example:voice': {'lux': 'voice-a'}}},
    }


def test_existing_macos_voice_is_selectable_without_model_download(settings_file, monkeypatch):
    from noisy_coding.providers import builtin_selection
    config.save(tts='local', tts_engine='say', tts_voice='Samantha')
    monkeypatch.setattr(builtin_selection.shutil, 'which', lambda command: '/usr/bin/say')
    candidate = selection.choice(selection.active_choices()['tts'])

    assert {
        'id': candidate['id'],
        'readiness': selection.readiness(candidate)[0],
        'voices': selection.voices(candidate),
        'bindings': selection.assignments(candidate, ['lux', 'rex']),
    } == {
        'id': 'macos:say',
        'readiness': 'ready',
        'voices': [{'id': 'Samantha', 'label': 'Samantha'}],
        'bindings': {'lux': 'Samantha', 'rex': 'Samantha'},
    }


def test_switching_local_engines_restores_each_engines_reviewed_voices(settings_file, monkeypatch):
    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('ready', ''))
    identities = ['lux', 'rex']
    original = {'lux': 'bf_emma', 'rex': 'am_adam'}
    selection.apply(selection.choice('kokoro:1'), selection.revision(), original, identities)
    selection.apply(selection.choice('macos:say'), selection.revision(), {'lux': 'system', 'rex': 'system'}, identities)

    assert selection.assignments(selection.choice('kokoro:1'), identities) == original


def test_catalog_explains_language_mismatch_before_apply(settings_file, monkeypatch):
    monkeypatch.setattr(selection, 'readiness', lambda candidate: ('ready', ''))
    monkeypatch.setattr(selection.local, 'download_status', lambda: [])
    engines = selection.snapshot(['lux'], language='pl')['engines']
    kokoro = next(engine for engine in engines if engine['id']=='kokoro:1')
    assert (kokoro['state'], 'English' in kokoro['detail']) == ('unsupported', True)


@pytest.mark.parametrize('engine, voice, expected', [
    ('kokoro', 'bf_emma', 'Emma · UK'),
    ('say', 'Samantha', 'Samantha'),
])
def test_local_voice_labels_preserve_legacy_voice_without_loading_models(settings_file, monkeypatch, engine, voice, expected):
    from noisy_coding.providers import local
    config.save(tts='local', tts_engine=engine, tts_voice=voice)
    monkeypatch.setattr(local._KokoroEngine, 'model', lambda: pytest.fail('Labels must not load model weights'))

    labels = selection.active_voice_labels()

    assert labels['lux'] == expected
