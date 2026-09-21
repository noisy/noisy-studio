"""Provider contracts for speech synthesis (TTS) and transcription (STT).

The daemon speaks through *whatever provider is active* — Grok today,
OpenAI or a fully local model tomorrow — without the speech pipeline
knowing which. Two rules keep that swap safe:

- Voice identity stays in the daemon: providers receive a voice_id and
  never push voice/speed/language decisions back up the stack.
- Capabilities are explicit: a provider that cannot stream says so, and
  the pipeline falls back to its batch path instead of failing.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = [
    "SynthesizedAudio",
    "TTSError",
    "STTError",
    "TTSProvider",
    "STTProvider",
    "STTStreamSession",
]


@dataclass(frozen=True)
class SynthesizedAudio:
    audio: bytes
    content_type: str
    duration_seconds: float


class TTSError(RuntimeError):
    """A provider could not synthesize speech."""


class STTError(RuntimeError):
    """A provider could not transcribe audio."""


@runtime_checkable
class STTStreamSession(Protocol):
    """A live transcription of one utterance (PCM in, partials out)."""

    def send(self, pcm_bytes: bytes) -> None: ...

    def finish(self) -> str:
        """Signal end of audio; block briefly and return the final text."""
        ...

    def abort(self) -> None: ...


class TTSProvider(Protocol):
    name: str  # registry key ("grok", "local", ...)
    label: str  # human wording for status cards ("Grok TTS", "local TTS")
    supports_streaming: bool

    async def synthesize(
        self, text: str, voice_id: str, language: str, speed: float
    ) -> SynthesizedAudio: ...

    async def speak_streaming(
        self,
        text: str,
        voice_id: str,
        language: str,
        speed: float,
        on_first_audio: Callable[[float], None] | None = None,
        on_audio_chunk: Callable[[bytes], None] | None = None,
    ) -> None:
        """Synthesize and play as audio arrives. Only called when
        supports_streaming is True."""
        ...

    async def list_voices(self) -> list[dict]: ...

    def cost_usd(self, text_chars: int) -> float: ...


class STTProvider(Protocol):
    name: str
    label: str
    supports_streaming: bool

    def transcribe(self, wav_bytes: bytes, language: str = "") -> str: ...

    def open_stream(
        self,
        sample_rate: int,
        language: str,
        on_partial: Callable[[str], None],
        smart_turn: float = 0.0,
        on_turn_end: Callable[[], None] | None = None,
    ) -> STTStreamSession | None:
        """A live session, or None when this provider cannot stream —
        the daemon then batches the utterance instead."""
        ...

    def cost_usd(self, audio_seconds: float) -> float: ...

    def streaming_cost_usd(self, audio_seconds: float) -> float: ...
