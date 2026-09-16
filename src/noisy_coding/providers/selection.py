"""Task-oriented speech choices; preparation never changes the active engine."""

import hashlib
import json
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


def revision() -> str:
    return hashlib.sha256(json.dumps(config._read(), sort_keys=True).encode()).hexdigest()[:16]


def choices() -> list[dict]:
    result = []
    for direction in ('stt', 'tts'):
        result.append(dict(id=f'grok:{direction}', provider='grok', direction=direction,
                           label='Grok', location='Online', model='', live=True,
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
    return result


def choice(choice_id: str) -> dict:
    found = next((c for c in choices() if c['id'] == choice_id), None)
    if found is None:
        raise ValueError('This speech engine is not available.')
    return found


def options_for(candidate: dict) -> dict:
    options = dict(config.local_options())
    if candidate['provider'] == 'local':
        options['stt_model' if candidate['direction'] == 'stt' else 'tts_engine'] = candidate['model']
    return options


def readiness(candidate: dict) -> tuple[str, str]:
    if candidate['provider'] == 'grok':
        return ('ready', 'Connection is checked when you try a sample.') if credentials.api_key() else (
            'setup', 'Add your xAI API key in System settings to use Grok.')
    direction = candidate['direction']
    dependency = 'faster_whisper' if direction == 'stt' else 'kokoro_onnx'
    if find_spec(dependency) is None:
        return 'setup', 'This installation is missing offline speech support. Install the current desktop release.'
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
    if candidate['provider'] == 'grok':
        from noisy_coding.listener.state import VOICE_POOL
        return [dict(id=v, label=v.title()) for v in VOICE_POOL]
    return [dict(id=v, label=v.split('_', 1)[1].title() + (' · UK' if v.startswith('b') else ' · US')) for v in KOKORO_VOICES]


def assignments(candidate: dict, identities: list[str]) -> dict[str, str]:
    available = [v['id'] for v in voices(candidate)]
    saved = config.local_options().get('voice_bindings', {}) if candidate['provider'] == 'local' else {}
    result = {identity: saved[identity] for identity in identities if saved.get(identity) in available}
    for identity in identities:
        if identity in result:
            continue
        result[identity] = identity if identity in available else next(
            (v for v in available if v not in result.values()), available[len(result) % len(available)])
    return result


def snapshot(identities: list[str]) -> dict:
    engines = []
    for candidate in choices():
        state, detail = readiness(candidate)
        engines.append({**candidate, 'state': state, 'detail': detail,
                        'voices': voices(candidate),
                        'bindings': assignments(candidate, identities) if candidate['direction'] == 'tts' else {}})
    return dict(revision=revision(), active=active_choices(), engines=engines, downloads=local.download_status())


def prepare(candidate: dict) -> None:
    state, detail = readiness(candidate)
    if state == 'setup':
        raise ValueError(detail)
    if state in ('ready', 'downloading'):
        return
    if candidate['provider'] == 'local':
        accepted = local.prefetch_models(
            tts=candidate['direction'] == 'tts',
            stt=candidate['direction'] == 'stt',
            options=options_for(candidate),
        )
        if not accepted:
            raise ValueError('Another model is being prepared. Wait for it to finish, then retry this download.')


def apply(candidate: dict, expected_revision: str, bindings: dict, identities: list[str], language: str = "auto") -> None:
    with config._lock:
        if expected_revision != revision():
            raise ValueError('Speech settings changed in another window. Reload and try again.')
        state, detail = readiness(candidate)
        if state != 'ready':
            raise ValueError(detail)
        if candidate['id'] == 'kokoro:1' and language not in ('', 'auto', 'en', 'en-US', 'en-GB'):
            raise ValueError('Kokoro currently supports English in this app. Keep your current engine for this language.')
        options = options_for(candidate)
        if not isinstance(bindings, dict):
            raise ValueError('Review the voice assignments before switching.')
        if candidate['direction'] == 'tts':
            allowed = {v['id'] for v in voices(candidate)}
            if set(bindings) != set(identities) or any(v not in allowed for v in bindings.values()):
                raise ValueError('Review the voice for every speaker before switching.')
            if candidate['provider'] == 'local':
                options['voice_bindings'] = {**options.get('voice_bindings', {}), **bindings}
        config.save(**{candidate['direction']: candidate['provider']}, **options)


def active_voice_labels() -> dict[str, str]:
    """Keep dashboard portraits stable while naming the voice actually heard."""
    if config.tts_provider_name() != 'local':
        return {}
    provider = local.LocalTTS()
    from noisy_coding.listener.state import VOICE_POOL
    if provider.options.get('tts_engine') == 'say':
        label = provider.options.get('tts_voice') or 'macOS system voice'
        return {identity: label for identity in VOICE_POOL}
    bindings = provider.options.get('voice_bindings', {})
    fallback = provider.options.get('tts_voice') or local.DEFAULT_KOKORO_VOICE
    bindings = {identity: bindings.get(identity, fallback) for identity in VOICE_POOL}
    labels = {v['id']: v['label'] for v in voices(choice('kokoro:1'))}
    return {identity: labels.get(voice, voice) for identity, voice in bindings.items()}
