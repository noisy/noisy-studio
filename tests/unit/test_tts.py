import base64
import json

import pytest
import respx
from httpx import Response

from noisy_studio import credentials, tts

FAKE_AUDIO = b"fake-mp3-bytes"


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(credentials, "api_key", lambda: "xai-test-key")


@respx.mock
async def test_synthesize_returns_raw_bytes_from_audio_response():
    respx.post(f"{tts.XAI_API_BASE}/tts").mock(
        return_value=Response(
            200, content=FAKE_AUDIO, headers={"content-type": "audio/mpeg"}
        )
    )

    result = await tts.synthesize("hello", voice_id="eve", language="en", speed=1.0)

    assert result == tts.SynthesizedAudio(
        audio=FAKE_AUDIO,
        content_type="audio/mpeg",
        duration_seconds=0.0,
    )


@respx.mock
async def test_synthesize_decodes_base64_audio_from_json_response():
    respx.post(f"{tts.XAI_API_BASE}/tts").mock(
        return_value=Response(
            200,
            json={
                "audio": base64.b64encode(FAKE_AUDIO).decode(),
                "content_type": "audio/mpeg",
                "duration": 1.5,
            },
        )
    )

    result = await tts.synthesize("hello", voice_id="eve", language="en", speed=1.0)

    assert result == tts.SynthesizedAudio(
        audio=FAKE_AUDIO,
        content_type="audio/mpeg",
        duration_seconds=1.5,
    )


@respx.mock
async def test_synthesize_sends_text_voice_language_and_mp3_format():
    route = respx.post(f"{tts.XAI_API_BASE}/tts").mock(
        return_value=Response(200, json={"audio": "", "content_type": "audio/mpeg"})
    )

    await tts.synthesize("hello", voice_id="rex", language="pl", speed=1.2)

    assert json.loads(route.calls.last.request.content) == {
        "text": "hello",
        "voice_id": "rex",
        "language": "pl",
        "speed": 1.2,
        "output_format": {"codec": "mp3"},
    }


@respx.mock
async def test_synthesize_raises_on_http_error_with_status_and_body():
    respx.post(f"{tts.XAI_API_BASE}/tts").mock(
        return_value=Response(403, text="no credits")
    )

    with pytest.raises(tts.GrokTTSError, match="HTTP 403.*no credits"):
        await tts.synthesize("hello", voice_id="eve", language="en", speed=1.0)


async def test_synthesize_rejects_text_over_api_limit_without_calling_api():
    with pytest.raises(tts.GrokTTSError, match="at most 15000"):
        await tts.synthesize(
            "x" * (tts.MAX_TEXT_LENGTH + 1), voice_id="eve", language="en", speed=1.0
        )


async def test_synthesize_raises_when_api_key_is_missing(monkeypatch):
    monkeypatch.setattr(credentials, "api_key", lambda: "")

    with pytest.raises(tts.GrokTTSError, match="No xAI API key configured"):
        await tts.synthesize("hello", voice_id="eve", language="en", speed=1.0)
