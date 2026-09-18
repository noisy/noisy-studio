"""Setup behavior for the existing Grok and local adapters."""
import shutil
from importlib.util import find_spec
from noisy_coding import credentials
from noisy_coding.providers import config, downloads, local
from noisy_coding.providers.manifest import KOKORO_VOICES

WHISPER_MODELS = {
    'base': 'Compact · lower memory use',
    'small': 'Larger · more recognition capacity',
    'medium': 'Large · needs more memory and processing',
    'large-v3': 'Largest · try on this Mac before choosing',
    'tiny': 'Smallest · intended for quick experiments',
}

def choices() -> list[dict]:
    result = []
    for direction in ('stt', 'tts'):
        result.append(dict(id=f'grok:{direction}', provider='grok', direction=direction,
                           label='Grok', location='Online', model='', live=True, setup_action='system-settings',
                           description='Text appears while you speak.' if direction == 'stt'
                           else 'Replies begin playing as audio arrives.', languages='Multilingual'))
    for model, description in WHISPER_MODELS.items():
        result.append(dict(id=f'whisper:{model}', provider='local', direction='stt',
                           label=f'Whisper {model}', location='On this Mac', model=model,
                           live=False, description=description, languages='Multilingual'))
    result.append(dict(id='kokoro:1', provider='local', direction='tts', label='Kokoro',
                       location='On this Mac', model='kokoro', live=False,
                       description='The full reply is generated before playback.',
                       languages='English voices in this integration'))
    result.append(dict(id='macos:say', provider='local', direction='tts', label='macOS voice',
                       location='On this Mac', model='say', live=False,
                       description='Uses the system voice. All agents share one voice.',
                       languages='Depends on the selected macOS voice'))
    return result


def options_for(candidate: dict) -> dict:
    options = config.provider_options(candidate['provider'])
    if candidate['provider'] == 'local':
        options['stt_model' if candidate['direction'] == 'stt' else 'tts_engine'] = candidate['model']
        if candidate['model'] == 'say' and options.get('tts_voice') in KOKORO_VOICES:
            options['tts_voice'] = ''
    return options


def readiness(candidate: dict) -> tuple[str, str]:
    if candidate['provider'] == 'grok':
        return ('ready', 'Connection is checked when you try a sample.') if credentials.api_key() else (
            'setup', 'Add your xAI API key in System settings to use Grok.')
    direction = candidate['direction']
    if candidate['model'] == 'say':
        return ('ready', 'Uses the installed macOS voice; no model download.') if shutil.which('say') else ('setup', 'macOS speech is unavailable on this computer.')
    dependency = 'faster_whisper' if direction == 'stt' else 'kokoro_onnx'
    if find_spec(dependency) is None:
        return 'setup', 'This installation is missing offline speech support. Use a desktop build with offline support, or keep your current engine.'
    if local.models_present(tts=direction == 'tts', stt=direction == 'stt', options=options_for(candidate)):
        return 'ready', 'Model files are on this Mac. Try a sample before switching.'
    names = {f"whisper-{candidate['model']}"} if direction == 'stt' else {'kokoro-v1.0.onnx', 'voices-v1.0.bin'}
    relevant = [d for d in downloads.status() if d['name'] in names]
    if any(d['state'] == 'downloading' for d in relevant):
        return 'downloading', 'Preparing this model. Your current setup stays active.'
    if any(d['state'] == 'error' for d in relevant):
        return 'error', 'The download did not finish. Retry when your connection is available.'
    return 'download', 'Download once, then use without an internet connection.'


def active_choices() -> dict:
    options = config.local_options()
    return {
        'stt': 'grok:stt' if config.stt_provider_name() == 'grok' else f"whisper:{options.get('stt_model') or config.DEFAULT_LOCAL_STT_MODEL}",
        'tts': 'grok:tts' if config.tts_provider_name() == 'grok' else ('kokoro:1' if options.get('tts_engine', 'kokoro') == 'kokoro' else 'macos:say'),
    }


def voices(candidate: dict) -> list[dict]:
    if candidate['direction'] != 'tts':
        return []
    if candidate['model'] == 'say':
        voice = options_for(candidate).get('tts_voice') or 'system'
        return [dict(id=voice, label=voice if voice != 'system' else 'macOS system voice')]
    if candidate['provider'] == 'grok':
        from noisy_coding.listener.state import VOICE_POOL
        return [dict(id=v, label=v.title()) for v in VOICE_POOL]
    return [dict(id=v, label=v.split('_', 1)[1].title() + (' · UK' if v.startswith('b') else ' · US')) for v in KOKORO_VOICES]


def prepare(candidate: dict) -> None:
    if candidate['provider'] == 'local':
        accepted = local.prefetch_models(
            tts=candidate['direction'] == 'tts',
            stt=candidate['direction'] == 'stt',
            options=options_for(candidate),
        )
        if not accepted:
            raise ValueError('Another model is being prepared. Wait for it to finish, then retry this download.')


def validate_language(candidate: dict, language: str) -> None:
    if candidate['id'] == 'kokoro:1' and language not in ('', 'auto', 'en', 'en-US', 'en-GB'):
        raise ValueError('Kokoro currently supports English in this app. Keep your current engine for this language.')


def local_voice_labels() -> dict[str, str]:
    """Include legacy defaults and newly assigned identities without loading weights."""
    from noisy_coding.listener.state import VOICE_POOL

    provider = local.LocalTTS()
    if provider.options.get('tts_engine') == 'say':
        label = provider.options.get('tts_voice') or 'macOS system voice'
        return {identity: label for identity in VOICE_POOL}
    bindings = provider.options.get('voice_bindings', {})
    fallback = provider.options.get('tts_voice') or local.DEFAULT_KOKORO_VOICE
    labels = {voice['id']: voice['label'] for voice in voices({'direction': 'tts', 'provider': 'local', 'model': 'kokoro'})}
    return {identity: labels.get(bindings.get(identity, fallback), bindings.get(identity, fallback))
            for identity in VOICE_POOL}
