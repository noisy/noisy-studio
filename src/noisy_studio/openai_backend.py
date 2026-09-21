"""OpenAI voice backend — alternative to the xAI (Grok) TTS/STT engine.

Reference: voice-mode.dev (github.com/mbailey/voicemode) — OpenAI-compatible
endpoints so cloud and local voice services swap freely.

  - TTS: POST https://api.openai.com/v1/audio/speech   (gpt-4o-mini-tts)
  - STT: POST https://api.openai.com/v1/audio/transcriptions  (gpt-4o-transcribe)

Mirrors noisy_studio.tts.synthesize / listener.stt.transcribe so the daemon's
playback queue and STT loop stay untouched.

STATUS: work in progress.
"""

import os

import httpx

OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
TTS_MODEL = "gpt-4o-mini-tts"
STT_MODEL = "gpt-4o-transcribe"


def _api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return key


async def synthesize(text: str, voice_id: str, language: str, speed: float):
    """Batch TTS via OpenAI /v1/audio/speech. Returns raw audio bytes."""
    payload = {
        "model": TTS_MODEL,
        "input": text,
        "voice": voice_id if voice_id in OPENAI_VOICES else "nova",
        "speed": speed,
        "response_format": "mp3",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{OPENAI_API_BASE}/audio/speech",
            headers={"Authorization": f"Bearer {_api_key()}"},
            json=payload,
        )
    if response.status_code != httpx.codes.OK:
        raise RuntimeError(
            f"OpenAI TTS failed with HTTP {response.status_code}: {response.text[:500]}"
        )
    return response.content


def transcribe(wav_bytes: bytes, language: str = "") -> str:
    """Batch STT via OpenAI /v1/audio/transcriptions. Mirrors stt.transcribe."""
    data = {"model": STT_MODEL}
    if language:
        data["language"] = language
    response = httpx.post(
        f"{OPENAI_API_BASE}/audio/transcriptions",
        headers={"Authorization": f"Bearer {_api_key()}"},
        files={"file": ("utterance.wav", wav_bytes, "audio/wav")},
        data=data,
        timeout=60.0,
    )
    if response.status_code != httpx.codes.OK:
        raise RuntimeError(
            f"OpenAI STT failed with HTTP {response.status_code}: {response.text[:500]}"
        )
    return response.json().get("text", "").strip()
