"""Per-utterance streaming transcription over the Grok STT websocket.

One session per utterance: opened when VAD detects speech, fed raw PCM
frames while the user talks, closed with audio.done when VAD closes.
Partial transcripts arrive during speech via the on_partial callback.
"""

import json
import os
import threading
from collections.abc import Callable

from websockets.sync.client import connect

from noisy_studio import tts
from noisy_studio.providers.base import STTError

STREAM_URL_BASE = "wss://api.x.ai/v1/stt"
CONNECT_TIMEOUT_SECONDS = 5.0
FINISH_TIMEOUT_SECONDS = 10.0
EMPTY_FINISH_TIMEOUT_SECONDS = 1.5


class GrokStreamError(STTError):
    """Raised when the streaming STT session cannot be established."""


def _extract_text(payload: dict) -> str:
    for key in ("text", "transcript"):
        if isinstance(payload.get(key), str):
            return payload[key]
    return ""


class StreamingSession:
    """A live websocket transcription of a single utterance."""

    def __init__(
        self,
        sample_rate: int,
        language: str,
        on_partial: Callable[[str], None],
        smart_turn: float = 0.0,
        on_turn_end: Callable[[], None] | None = None,
    ) -> None:
        query = f"sample_rate={sample_rate}&encoding=pcm&interim_results=true"
        if language:
            query += f"&language={language}"
        if os.environ.get("NOISY_STUDIO_STT_DEBUG"):
            print(f"[stt-debug] connecting lang={language!r} query={query}", flush=True)
        # smart_turn > 0 asks the server for prosody/semantics-aware end-of-turn
        # detection; it flags speech_final when it judges the thought complete.
        if smart_turn > 0:
            query += f"&smart_turn={smart_turn}"
        try:
            self._ws = connect(
                f"{STREAM_URL_BASE}?{query}",
                additional_headers={"Authorization": f"Bearer {tts._api_key()}"},
                open_timeout=CONNECT_TIMEOUT_SECONDS,
            )
        except Exception as error:
            # The handshake rejection's HTTP body names the actual reason
            # ("Incorrect API key", quota, …) — surface it like batch STT
            # does, or live-mode failures stay undiagnosable one-liners.
            body = getattr(getattr(error, "response", None), "body", b"")
            detail = str(error)
            if body:
                detail += f" — {body[:500].decode(errors='replace')}"
            raise GrokStreamError(
                f"Cannot open streaming STT session: {detail}"
            ) from error

        self._on_partial = on_partial
        self._on_turn_end = on_turn_end
        # Segment texts keyed by their start time: the server revises segments
        # in place (same start, new text) and sometimes merges neighbours.
        self._segments: dict[float, str] = {}
        self._done = threading.Event()
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _full_text(self) -> str:
        return " ".join(self._segments[start] for start in sorted(self._segments))

    def _store_segment(self, start: float, text: str) -> None:
        # A revision may swallow later segments (merge); drop absorbed ones.
        for other_start in list(self._segments):
            if other_start > start and self._segments[other_start].lower() in text.lower():
                del self._segments[other_start]
        self._segments[start] = text

    def send(self, pcm_bytes: bytes) -> None:
        try:
            self._ws.send(pcm_bytes)
        except Exception:
            self._done.set()

    def _read_loop(self) -> None:
        try:
            for message in self._ws:
                if isinstance(message, bytes):
                    continue
                payload = json.loads(message)
                kind = payload.get("type", "")
                if os.environ.get("NOISY_STUDIO_STT_DEBUG"):
                    print(f"[stt-debug] {message}", flush=True)
                if kind == "transcript.partial":
                    text = _extract_text(payload)
                    if text:
                        self._store_segment(float(payload.get("start", 0.0)), text)
                        self._on_partial(self._full_text())
                    # smart_turn verdict: the model judged the thought complete.
                    if payload.get("speech_final") and self._on_turn_end:
                        self._on_turn_end()
                elif kind == "transcript.done":
                    # done carries no text; the stored segments are the answer.
                    done_text = _extract_text(payload)
                    if done_text and len(done_text) > len(self._full_text()):
                        self._segments = {0.0: done_text}
                    self._done.set()
                    return
                elif kind == "error":
                    self._done.set()
                    return
        except Exception:
            pass
        self._done.set()

    def finish(self) -> str:
        """Signal end of audio and wait for the final transcript.

        If nothing was transcribed yet, don't block the full timeout — an
        empty utterance (noise/silence) may never get a clean final, and the
        card would hang in a live status until then.
        """
        try:
            self._ws.send(json.dumps({"type": "audio.done"}))
        except Exception:
            pass
        timeout = FINISH_TIMEOUT_SECONDS if self._full_text() else EMPTY_FINISH_TIMEOUT_SECONDS
        self._done.wait(timeout)
        try:
            self._ws.close()
        except Exception:
            pass
        return self._full_text().strip()

    def abort(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass
