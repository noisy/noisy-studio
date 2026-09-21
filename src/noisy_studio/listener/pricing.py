"""Grok Voice API pricing (July 2026) and cost helpers.

Sources: x.ai pricing announcements — STT batch $0.10 per audio hour,
TTS $4.20 per million characters.
"""

STT_USD_PER_AUDIO_HOUR = 0.10
STT_STREAMING_USD_PER_AUDIO_HOUR = 0.20
TTS_USD_PER_MILLION_CHARS = 4.20


def stt_cost_usd(audio_seconds: float) -> float:
    return audio_seconds / 3600 * STT_USD_PER_AUDIO_HOUR


def stt_streaming_cost_usd(audio_seconds: float) -> float:
    return audio_seconds / 3600 * STT_STREAMING_USD_PER_AUDIO_HOUR


def tts_cost_usd(characters: int) -> float:
    return characters / 1_000_000 * TTS_USD_PER_MILLION_CHARS
