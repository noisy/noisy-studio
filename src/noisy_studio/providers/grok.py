"""Grok (xAI) provider — a thin adapter over the existing clients.

The wire clients stay where they were (tts.py, tts_stream.py,
listener/stt.py, listener/stt_stream.py); this module only gives them
the provider shape, so the daemon can stop naming Grok directly.
"""

from collections.abc import Callable
import re
import json
from noisy_studio.providers.capabilities import AudioCapabilities
from noisy_studio.providers import config, grok_capabilities

from noisy_studio import tts, tts_stream
from noisy_studio.listener import pricing, stt, stt_stream
from noisy_studio.providers.base import STTStreamSession, SynthesizedAudio


class GrokTTS:
    name = "grok"
    label = "Grok TTS"

    def __init__(self, options: dict | None = None):
        self.options = config.provider_options("grok") if options is None else dict(options)
        self.bindings = dict(self.options.get("voice_bindings", {}))
        self.cache_identity = "grok:" + json.dumps(self.options, sort_keys=True)

    @property
    def capabilities(self) -> AudioCapabilities:
        return grok_capabilities.tts_capabilities(self.supports_streaming)

    def _voice(self, identity: str) -> str:
        return self.bindings.get(identity, identity)

    @property
    def supports_streaming(self) -> bool:
        return tts_stream.streaming_available()

    async def synthesize(
        self, text: str, voice_id: str, language: str, speed: float
    ) -> SynthesizedAudio:
        return await tts.synthesize(_speech_text(text), self._voice(voice_id), language, speed)

    async def speak_streaming(
        self,
        text: str,
        voice_id: str,
        language: str,
        speed: float,
        on_first_audio: Callable[[float], None] | None = None,
        on_audio_chunk: Callable[[bytes], None] | None = None,
        on_playback_complete: Callable[[], None] | None = None,
    ) -> None:
        await tts_stream.speak_streaming(
            _speech_text(text), self._voice(voice_id), language, speed,
            on_first_audio=on_first_audio, on_audio_chunk=on_audio_chunk,
            on_playback_complete=on_playback_complete,
        )

    async def list_voices(self) -> list[dict]:
        return await tts.list_voices()

    def cost_usd(self, text_chars: int) -> float:
        return pricing.tts_cost_usd(text_chars)


class GrokSTT:
    name = "grok"
    label = "Grok STT"
    supports_streaming = True

    @property
    def capabilities(self) -> AudioCapabilities:
        return grok_capabilities.stt_capabilities()

    def transcribe(self, wav_bytes: bytes, language: str = "") -> str:
        return stt.transcribe(wav_bytes, language)

    def open_stream(
        self,
        sample_rate: int,
        language: str,
        on_partial: Callable[[str], None],
        smart_turn: float = 0.0,
        on_turn_end: Callable[[], None] | None = None,
    ) -> STTStreamSession | None:
        return stt_stream.StreamingSession(
            sample_rate, language, on_partial,
            smart_turn=smart_turn, on_turn_end=on_turn_end,
        )

    def cost_usd(self, audio_seconds: float) -> float:
        return pricing.stt_cost_usd(audio_seconds)

    def streaming_cost_usd(self, audio_seconds: float) -> float:
        return pricing.stt_streaming_cost_usd(audio_seconds)


def _speech_text(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<loud>\1</loud>", text)
