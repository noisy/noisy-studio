"""xAI endpoint capabilities, checked 2026-09-22.

https://docs.x.ai/developers/model-capabilities/audio/text-to-speech
https://docs.x.ai/developers/model-capabilities/audio/speech-to-text
The adapters omit model, so report service-default rather than claim a pin.
"""
from .capabilities import AudioCapabilities, LanguageCapabilities, SmartTurnCapabilities

TTS_LANGUAGES = ('en', 'ar-EG', 'ar-SA', 'ar-AE', 'bn', 'zh', 'fr', 'de', 'hi', 'id', 'it', 'ja', 'ko', 'pt-BR', 'pt-PT', 'ru', 'es-MX', 'es-ES', 'tr', 'vi')
STT_LANGUAGES = ('ar', 'cs', 'da', 'nl', 'en', 'fil', 'fr', 'de', 'hi', 'id', 'it', 'ja', 'ko', 'mk', 'ms', 'fa', 'pl', 'pt', 'ro', 'ru', 'es', 'sv', 'th', 'tr', 'vi')


def tts_capabilities(streaming: bool) -> AudioCapabilities:
    return AudioCapabilities(
        model='service-default', modes=('batch', 'live') if streaming else ('batch',),
        languages=LanguageCapabilities(TTS_LANGUAGES, True, exhaustive=False, purpose='synthesis',
            note='Documented language codes. Other languages may work with varying accuracy; this is not a rejection list.'),
    )


def stt_capabilities() -> AudioCapabilities:
    return AudioCapabilities(
        model='service-default', modes=('batch', 'live'),
        languages=LanguageCapabilities(STT_LANGUAGES, True, purpose='formatting',
            note='Recognition detects speech language automatically. The language parameter selects text formatting.'),
        smart_turn=SmartTurnCapabilities(),
    )
