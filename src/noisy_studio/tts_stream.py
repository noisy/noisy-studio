"""Streaming text-to-speech over the Grok (xAI) TTS websocket.

Sends the whole text in one text.delta / text.done, then pipes the
returned audio.delta chunks straight into a player process (ffmpeg/mpv or
afplay via a temp file) so playback starts before synthesis finishes.
"""

import asyncio
import base64
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable

import websockets

from noisy_studio import playback, tts
from noisy_studio.providers.base import TTSError

STREAM_URL_BASE = "wss://api.x.ai/v1/tts"


class GrokTTSStreamError(TTSError):
    """Raised when the streaming TTS session fails."""


def _stream_player_command() -> list[str] | None:
    """A player that can read an MP3 stream from stdin, or None if absent.

    mpv first: ffplay proved fragile against CoreAudio device changes
    (robotic/distorted output after sleep-wake with a different default
    output device), while mpv recovers cleanly.
    """
    if shutil.which("mpv"):
        return ["mpv", "--no-video", "--really-quiet", "-"]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-"]
    return None


async def _play_from_stream(
    chunks: asyncio.Queue[bytes | None],
    on_playback_complete: Callable[[], None] | None = None,
) -> None:
    """Feed audio chunks into a streaming player as they arrive."""
    command = _stream_player_command()
    if command is None:
        # No stdin-streaming player (e.g. bare macOS): buffer to a temp file
        # and play once. Loses the streaming latency win but stays correct.
        await _play_buffered(chunks, on_playback_complete)
        return

    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    assert process.stdin is not None
    playback.register_player(process)
    try:
        while True:
            chunk = await chunks.get()
            if chunk is None:
                break
            if process.returncode is not None:
                break  # player was killed by an interrupt
            try:
                process.stdin.write(chunk)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                break
        if process.returncode is None:
            process.stdin.close()
            await process.wait()
    finally:
        playback.unregister_player(process)
    _report_playback_completion(process.returncode, on_playback_complete)


def _report_playback_completion(returncode, callback) -> None:
    if returncode == 0:
        if callback:
            callback()
    elif returncode is not None and returncode > 0:
        raise playback.PlaybackError(f"Streaming audio player exited with code {returncode}")


async def _play_buffered(
    chunks: asyncio.Queue[bytes | None],
    on_playback_complete: Callable[[], None] | None = None,
) -> None:
    buffer = bytearray()
    while True:
        chunk = await chunks.get()
        if chunk is None:
            break
        buffer.extend(chunk)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
        audio_file.write(buffer)
        path = Path(audio_file.name)
    try:
        process = await asyncio.create_subprocess_exec(
            "afplay", str(path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        playback.register_player(process)
        try:
            await process.wait()
        finally:
            playback.unregister_player(process)
        _report_playback_completion(process.returncode, on_playback_complete)
    finally:
        path.unlink(missing_ok=True)


async def speak_streaming(
    text: str,
    voice_id: str,
    language: str,
    speed: float,
    on_first_audio: Callable[[float], None] | None = None,
    on_audio_chunk: Callable[[bytes], None] | None = None,
    on_playback_complete: Callable[[], None] | None = None,
) -> None:
    """Synthesize and play `text`, streaming audio as it is generated.

    `on_first_audio` fires once with the seconds from request to the first
    audio chunk — the perceived render latency of the streaming path.
    `on_audio_chunk` fires with every audio chunk as it arrives, so the
    caller can keep the complete clip (the audio cache does).
    """
    api_key = tts._api_key()
    started = time.monotonic()
    first_audio_seen = False

    def mark_first_audio() -> None:
        nonlocal first_audio_seen
        if not first_audio_seen:
            first_audio_seen = True
            if on_first_audio:
                on_first_audio(time.monotonic() - started)
    query = (
        f"language={language or 'auto'}&voice={voice_id}"
        f"&codec=mp3&speed={speed}&optimize_streaming_latency=1"
    )
    chunks: asyncio.Queue[bytes | None] = asyncio.Queue()

    try:
        async with websockets.connect(
            f"{STREAM_URL_BASE}?{query}",
            additional_headers={"Authorization": f"Bearer {api_key}"},
            open_timeout=10,
        ) as ws:
            await ws.send(json.dumps({"type": "text.delta", "delta": text}))
            await ws.send(json.dumps({"type": "text.done"}))

            player = asyncio.create_task(_play_from_stream(chunks, on_playback_complete))
            async for message in ws:
                if isinstance(message, bytes):
                    mark_first_audio()
                    if on_audio_chunk:
                        on_audio_chunk(message)
                    await chunks.put(message)
                    continue
                payload = json.loads(message)
                kind = payload.get("type")
                if kind == "audio.delta":
                    mark_first_audio()
                    chunk = base64.b64decode(payload["delta"])
                    if on_audio_chunk:
                        on_audio_chunk(chunk)
                    await chunks.put(chunk)
                elif kind == "audio.done":
                    break
                elif kind == "error":
                    raise GrokTTSStreamError(str(payload)[:300])
            await chunks.put(None)
            await player
    except (OSError, websockets.WebSocketException) as error:
        raise GrokTTSStreamError(f"Streaming TTS failed: {error}") from error


def streaming_available() -> bool:
    """True if a stdin-streaming player exists (else we buffer-and-play)."""
    return _stream_player_command() is not None or bool(
        os.environ.get("NOISY_STUDIO_ALLOW_BUFFERED_STREAM")
    )
