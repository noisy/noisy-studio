"""Capabilities of the local integrations, rather than the entire upstream model.

Whisper codes: https://github.com/openai/whisper/blob/main/whisper/tokenizer.py
Only large-v3 models add Cantonese to the original 99 language tokens.
Custom model paths are unknown without loading weights; do not guess.
"""
from .capabilities import AudioCapabilities, LanguageCapabilities

WHISPER_LANGUAGES = tuple('en zh de es ru ko fr ja pt tr pl ca nl ar sv it id hi fi vi he uk el ms cs ro da hu ta no th ur hr bg lt la mi ml cy sk te fa lv bn sr az sl kn et mk br eu is hy ne mn bs kk sq sw gl mr pa si km sn yo so af oc ka be tg sd gu am yi lo uz fo ht ps tk nn mt sa lb my bo tl mg as tt haw ln ha ba jw su'.split())
WHISPER_MODELS = {'tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large-v3-turbo', 'turbo', 'large'}


def stt_capabilities(model: str) -> AudioCapabilities:
    english = model in {'tiny.en', 'base.en', 'small.en', 'medium.en'}
    codes = ('en',) if english else WHISPER_LANGUAGES if model in WHISPER_MODELS else None
    if model in {'large', 'large-v3', 'large-v3-turbo', 'turbo'}:
        codes = WHISPER_LANGUAGES + ('yue',)
    return AudioCapabilities(model=model, modes=('batch',), languages=LanguageCapabilities(
        codes, (not english) if codes is not None else None, note='Custom model language support is unknown until its metadata is available.' if codes is None else '',
    ))


def tts_capabilities(engine: str) -> AudioCapabilities:
    if engine == 'say':
        return AudioCapabilities(model=engine, modes=('batch',), languages=LanguageCapabilities(
            None, False, selectable=False, exhaustive=False, purpose='voice',
            note='Language depends on the installed system voice. This adapter does not pass a language override.',
        ))
    return AudioCapabilities(model=engine, modes=('batch',), languages=LanguageCapabilities(
        ('en', 'en-US', 'en-GB'), False, purpose='synthesis',
        note='This integration exposes English Kokoro voices. An unspecified language uses the selected English voice.',
    ))
