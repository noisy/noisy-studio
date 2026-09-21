"""Client for the Grok (xAI) batch text-to-speech API."""

import base64

import httpx

from noisy_studio import credentials
from noisy_studio.providers.base import SynthesizedAudio, TTSError

__all__ = ["GrokTTSError", "SynthesizedAudio", "synthesize", "list_voices"]

XAI_API_BASE = "https://api.x.ai/v1"
REQUEST_TIMEOUT_SECONDS = 60.0
MAX_TEXT_LENGTH = 15_000


class GrokTTSError(TTSError):
    """Raised when the Grok TTS API cannot produce audio."""


def _api_key() -> str:
    api_key = credentials.api_key()
    if not api_key:
        raise GrokTTSError(
            "No xAI API key configured yet — set it on the dashboard (SETTINGS panel)."
        )
    return api_key


async def synthesize(
    text: str,
    voice_id: str,
    language: str,
    speed: float,
) -> SynthesizedAudio:
    if len(text) > MAX_TEXT_LENGTH:
        raise GrokTTSError(
            f"Text is {len(text)} characters; the API accepts at most {MAX_TEXT_LENGTH}."
        )

    payload = {
        "text": text,
        "voice_id": voice_id,
        "language": language,
        "speed": speed,
        "output_format": {"codec": "mp3"},
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{XAI_API_BASE}/tts",
            headers={"Authorization": f"Bearer {_api_key()}"},
            json=payload,
        )

    if response.status_code != httpx.codes.OK:
        raise GrokTTSError(
            f"Grok TTS request failed with HTTP {response.status_code}: {response.text[:500]}"
        )

    # The API answers with raw audio bytes (content-type: audio/mpeg) by
    # default, or JSON with base64 audio (e.g. when timestamps are requested).
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    if content_type == "application/json":
        body = response.json()
        return SynthesizedAudio(
            audio=base64.b64decode(body["audio"]),
            content_type=body.get("content_type", "audio/mpeg"),
            duration_seconds=body.get("duration", 0.0),
        )
    return SynthesizedAudio(
        audio=response.content,
        content_type=content_type or "audio/mpeg",
        duration_seconds=0.0,
    )


async def list_voices() -> list[dict]:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.get(
            f"{XAI_API_BASE}/tts/voices",
            headers={"Authorization": f"Bearer {_api_key()}"},
        )

    if response.status_code != httpx.codes.OK:
        raise GrokTTSError(
            f"Grok voices request failed with HTTP {response.status_code}: {response.text[:500]}"
        )

    body = response.json()
    return body.get("voices", body) if isinstance(body, dict) else body
