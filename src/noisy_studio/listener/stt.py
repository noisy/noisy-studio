"""Client for the Grok (xAI) batch speech-to-text API."""

import io
import wave

import httpx
import numpy as np

from noisy_studio import tts
from noisy_studio.providers.base import STTError

REQUEST_TIMEOUT_SECONDS = 60.0


class GrokSTTError(STTError):
    """Raised when the Grok STT API cannot transcribe audio."""


def encode_wav(samples: np.ndarray, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.astype(np.int16).tobytes())
    return buffer.getvalue()


def transcribe(wav_bytes: bytes, language: str = "") -> str:
    """Transcribe a WAV utterance; returns the transcript text ("" if silence)."""
    data = {"language": language, "format": "true"} if language else {}
    response = httpx.post(
        f"{tts.XAI_API_BASE}/stt",
        headers={"Authorization": f"Bearer {tts._api_key()}"},
        files={"file": ("utterance.wav", wav_bytes, "audio/wav")},
        data=data,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != httpx.codes.OK:
        raise GrokSTTError(
            f"Grok STT request failed with HTTP {response.status_code}: {response.text[:500]}"
        )
    return response.json().get("text", "").strip()
