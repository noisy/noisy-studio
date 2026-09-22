"""Dashboard contract combining provider facts with local turn controls."""
from dataclasses import asdict
from noisy_studio import providers
from noisy_studio.providers.base import STTError, TTSError


def audio_capabilities() -> dict:
    directions = {}
    for direction, factory in (('stt', providers.active_stt), ('tts', providers.active_tts)):
        try:
            provider = factory()
            directions[direction] = {'provider': provider.name, **asdict(provider.capabilities)}
        except (STTError, TTSError):
            directions[direction] = None
    return {
        'version': 1,
        **directions,
        'turn_detection': {'owner': 'application', 'modes': ['auto', 'ptt']},
        'end_silence': {'owner': 'application', 'minimum_ms': 0, 'maximum_ms': 10000, 'modes': ['auto']},
    }
