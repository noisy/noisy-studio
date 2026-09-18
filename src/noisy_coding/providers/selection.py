"""Task-oriented speech choices; preparation never changes the active engine."""

import hashlib
import json

from noisy_coding.providers import config, local, engine_registry
from noisy_coding.providers.builtin_selection import WHISPER_MODELS




def revision() -> str:
    return hashlib.sha256(json.dumps(config._read(), sort_keys=True).encode()).hexdigest()[:16]


def choices() -> list[dict]:
    return [candidate for adapter in engine_registry.adapters.values() for candidate in adapter.choices()]


def choice(choice_id: str) -> dict:
    found = next((c for c in choices() if c['id'] == choice_id), None)
    if found is None:
        raise ValueError('This speech engine is not available.')
    return found


def options_for(candidate: dict) -> dict:
    return engine_registry.adapter(candidate['provider']).options(candidate)


def readiness(candidate: dict) -> tuple[str, str]:
    return engine_registry.adapter(candidate['provider']).readiness(candidate)


def active_choices() -> dict:
    result = {}
    for direction, name in [('stt', config.stt_provider_name()), ('tts', config.tts_provider_name())]:
        adapter = engine_registry.adapters.get(name)
        result[direction] = adapter.active_choice(direction) if adapter else f'unavailable:{name}:{direction}'
    return result


def voices(candidate: dict) -> list[dict]:
    return engine_registry.adapter(candidate['provider']).voices(candidate)


def assignments(candidate: dict, identities: list[str]) -> dict[str, str]:
    available = [v['id'] for v in voices(candidate)]
    options = config.provider_options(candidate['provider'])
    saved = options.get('voice_bindings_by_engine', {}).get(candidate['id'], options.get('voice_bindings', {}))
    if not available:
        return {}
    result = {identity: saved[identity] for identity in identities if saved.get(identity) in available}
    for identity in identities:
        if identity in result:
            continue
        result[identity] = identity if identity in available else next(
            (v for v in available if v not in result.values()), available[len(result) % len(available)])
    return result


def snapshot(identities: list[str], language: str = "auto") -> dict:
    engines = []
    for candidate in choices():
        state, detail = readiness(candidate)
        try:
            engine_registry.adapter(candidate['provider']).validate_language(candidate, language)
        except ValueError as error:
            state, detail = 'unsupported', str(error)
        engines.append({**candidate, 'state': state, 'detail': detail,
                        'voices': voices(candidate),
                        'bindings': assignments(candidate, identities) if candidate['direction'] == 'tts' else {}})
    return dict(revision=revision(), active=active_choices(), current_voice_labels=active_voice_labels(),
                engines=engines, downloads=local.download_status())


def prepare(candidate: dict) -> None:
    state, detail = readiness(candidate)
    if state == 'setup':
        raise ValueError(detail)
    if state not in ('ready', 'downloading'):
        engine_registry.adapter(candidate['provider']).prepare(candidate)


def apply(candidate: dict, expected_revision: str, bindings: dict, identities: list[str], language: str = "auto") -> None:
    with config._lock:
        if expected_revision != revision():
            raise ValueError('Speech settings changed in another window. Reload and try again.')
        state, detail = readiness(candidate)
        if state != 'ready':
            raise ValueError(detail)
        engine_registry.adapter(candidate['provider']).validate_language(candidate, language)
        options = options_for(candidate)
        if not isinstance(bindings, dict):
            raise ValueError('Review the voice assignments before switching.')
        if candidate['direction'] == 'tts':
            allowed = {v['id'] for v in voices(candidate)}
            if set(bindings) != set(identities) or any(v not in allowed for v in bindings.values()):
                raise ValueError('Review the voice for every speaker before switching.')
            options['voice_bindings'] = {**options.get('voice_bindings', {}), **bindings}
            options['voice_bindings_by_engine'] = {
                **options.get('voice_bindings_by_engine', {}),
                candidate['id']: options['voice_bindings'],
            }
        config.save_selection(candidate['direction'], candidate['provider'], options)


def active_voice_labels() -> dict[str, str]:
    """Keep dashboard portraits stable while naming the voice actually heard."""
    name = config.tts_provider_name()
    adapter = engine_registry.adapters.get(name)
    if not adapter:
        return {}
    if adapter.active_voice_labels is not None:
        return adapter.active_voice_labels()
    candidate = next((c for c in adapter.choices() if c['id'] == adapter.active_choice('tts')), None)
    if not candidate:
        return {}
    labels = {v['id']: v['label'] for v in adapter.voices(candidate)}
    return {identity: labels.get(voice, voice)
            for identity, voice in config.provider_options(name).get('voice_bindings', {}).items()}
