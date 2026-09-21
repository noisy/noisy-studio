"""Bounded store of synthesized speech — replay without re-paying Grok.

Every rendered clip (batch or streamed) lands here, keyed by the card it
belongs to plus everything that shaped the audio (text, voice, language,
speed) — change any of those and the key misses, so a replay after a voice
switch re-synthesizes with the new voice, exactly like a fresh utterance.

Two tiers: a small in-memory map for instant hits, and a spill directory
under CONFIG_DIR so history cards stay replayable for free across daemon
restarts. Both are bounded by clip count and total bytes; oldest clips go
first.
"""

import hashlib
import json

from noisy_studio.providers.base import SynthesizedAudio
import threading
from collections import OrderedDict
from pathlib import Path

from noisy_studio.config_dir import CONFIG_DIR

CONTENT_TYPE = "audio/mpeg"  # every render requests the mp3 codec
DEFAULT_DIRECTORY = CONFIG_DIR / "audio_cache"
MEMORY_MAX_CLIPS = 50
MEMORY_MAX_BYTES = 50 * 1024 * 1024
DISK_MAX_CLIPS = 100
DISK_MAX_BYTES = 100 * 1024 * 1024


def key(source_id: int, text: str, voice: str, language: str, speed: float, provider: str = "grok") -> str | None:
    """Cache key for a clip, or None when the utterance has no stable card
    identity to key on (cardless one-off plays must never collide)."""
    if source_id <= 0:
        return None
    fingerprint = hashlib.sha256(
        f"v2|{provider}|{voice}|{language}|{speed}|{text}".encode()
    ).hexdigest()[:16]
    return f"{source_id}-{fingerprint}"


class AudioCache:
    def __init__(self, directory: Path | None = DEFAULT_DIRECTORY) -> None:
        self._lock = threading.Lock()
        self._clips: OrderedDict[str, bytes] = OrderedDict()
        self._directory = directory

    def get_audio(self, clip_key: str | None) -> SynthesizedAudio | None:
        payload = self.get(clip_key)
        if payload is None:
            return None
        try:
            metadata, audio = payload.split(b"\n", 1)
            info = json.loads(metadata)
            return SynthesizedAudio(audio, info["content_type"], info["duration_seconds"])
        except (ValueError, KeyError, TypeError):
            return None  # legacy/raw clips have no trustworthy format metadata

    def put_audio(self, clip_key: str | None, audio: SynthesizedAudio) -> None:
        if not audio.audio:
            return
        metadata = json.dumps({"content_type": audio.content_type,
                               "duration_seconds": audio.duration_seconds}).encode()
        self.put(clip_key, metadata + b"\n" + audio.audio)

    def get(self, clip_key: str | None) -> bytes | None:
        if clip_key is None:
            return None
        with self._lock:
            audio = self._clips.get(clip_key)
            if audio is not None:
                self._clips.move_to_end(clip_key)  # keep hot clips in memory longest
                return audio
            return self._read_from_disk(clip_key)

    def put(self, clip_key: str | None, audio: bytes) -> None:
        if clip_key is None or not audio:
            return
        with self._lock:
            self._clips[clip_key] = audio
            self._clips.move_to_end(clip_key)
            self._evict_memory()
            self._write_to_disk(clip_key, audio)

    # -- memory tier ---------------------------------------------------------

    def _evict_memory(self) -> None:
        while len(self._clips) > MEMORY_MAX_CLIPS or self._memory_bytes() > MEMORY_MAX_BYTES:
            self._clips.popitem(last=False)

    def _memory_bytes(self) -> int:
        return sum(len(audio) for audio in self._clips.values())

    # -- disk tier -----------------------------------------------------------

    def _clip_path(self, clip_key: str) -> Path:
        return self._directory / f"{clip_key}.mp3"

    def _read_from_disk(self, clip_key: str) -> bytes | None:
        if self._directory is None:
            return None
        try:
            audio = self._clip_path(clip_key).read_bytes()
        except OSError:
            return None
        self._clips[clip_key] = audio  # promote: the next replay skips the disk
        self._evict_memory()
        return audio

    def _write_to_disk(self, clip_key: str, audio: bytes) -> None:
        if self._directory is None:
            return
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            self._clip_path(clip_key).write_bytes(audio)
            self._evict_disk()
        except OSError:
            pass  # a full or read-only disk must never break speech itself

    def _evict_disk(self) -> None:
        clips = sorted(self._directory.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
        sizes = {clip: clip.stat().st_size for clip in clips}
        total = sum(sizes.values())
        while clips and (len(clips) > DISK_MAX_CLIPS or total > DISK_MAX_BYTES):
            oldest = clips.pop(0)
            total -= sizes[oldest]
            oldest.unlink(missing_ok=True)
