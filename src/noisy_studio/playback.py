"""Play synthesized audio through the local speakers."""

import asyncio
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable
import signal
import shutil
import sys
import tempfile
from pathlib import Path

SUFFIX_BY_CONTENT_TYPE = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}


class PlaybackError(RuntimeError):
    """Raised when no audio player is available or playback fails."""


class PlaybackInterrupted(PlaybackError):
    """Playback was cancelled by a deliberate interruption."""


# Currently-running player processes, so an interrupting speak can kill them.
_active_players: set[asyncio.subprocess.Process] = set()
_player_lock = threading.Lock()
_interrupt_generation = 0
_playback_generation: ContextVar[int | None] = ContextVar("playback_generation", default=None)


_playback_events: ContextVar[Callable[[str, str], None] | None] = ContextVar("playback_events", default=None)


def report_completion(returncode: int | None) -> None:
    reporter = _playback_events.get()
    generation = _playback_generation.get()
    interrupted = generation is not None and was_interrupted(generation)
    if reporter:
        reporter("playback_exit", f"returncode={returncode} interrupted={interrupted}")
    if interrupted:
        raise PlaybackInterrupted(f"Audio playback interrupted (returncode={returncode})")
    if returncode != 0:
        raise PlaybackError(f"Audio player failed (returncode={returncode})")


def interruption_generation() -> int:
    with _player_lock:
        return _interrupt_generation


def was_interrupted(generation: int) -> bool:
    with _player_lock:
        return generation != _interrupt_generation


@contextmanager
def playback_scope(generation: int | None = None, on_event=None):
    """An interrupt also cancels players still connecting or buffering."""
    with _player_lock:
        token = _playback_generation.set(
            _interrupt_generation if generation is None else generation
        )
    event_token = _playback_events.set(on_event)
    try:
        yield
    finally:
        _playback_events.reset(event_token)
        _playback_generation.reset(token)


def register_player(process: asyncio.subprocess.Process) -> None:
    rejected = None
    with _player_lock:
        generation = _playback_generation.get()
        if generation is not None and generation != _interrupt_generation:
            rejected = (generation, _interrupt_generation)
            try:
                process.kill()
            except ProcessLookupError:
                pass
        else:
            _active_players.add(process)
    # The event sink may take the state lock: never call it under the player lock.
    reporter = _playback_events.get()
    if rejected is not None and reporter:
        reporter("playback_rejected", f"scope_generation={rejected[0]} current_generation={rejected[1]}")


def unregister_player(process: asyncio.subprocess.Process) -> None:
    with _player_lock:
        _active_players.discard(process)


# Transport pause (dashboard ⏸): the player process is frozen in place
# with SIGSTOP, so resume continues the very sample it stopped on. State
# is daemon-global - there is at most one thing on the speakers anyway.
_paused = False


def toggle_pause() -> bool:
    """Freeze/unfreeze the current player; returns the new paused state.

    No active player: reports unpaused - nothing to freeze, and a stale
    "paused" flag would wedge the NEXT clip's UI.
    """
    with _player_lock:
        global _paused
        want_paused = not _paused
        signalled = False
        for process in list(_active_players):
            try:
                process.send_signal(signal.SIGSTOP if want_paused else signal.SIGCONT)
                signalled = True
            except ProcessLookupError:
                _active_players.discard(process)
        _paused = want_paused if signalled else False
        return _paused


def stop_all_players() -> None:
    """Terminate every playing audio process (used by interrupt=True)."""
    with _player_lock:
        global _paused, _interrupt_generation
        _interrupt_generation += 1
        _paused = False
        for process in list(_active_players):
            try:
                # A SIGSTOPped process still dies to SIGKILL, but wake it first
                # so its communicate() unblocks promptly.
                process.send_signal(signal.SIGCONT)
                process.kill()
            except ProcessLookupError:
                pass
            _active_players.discard(process)


def _player_command(audio_path: Path) -> list[str]:
    if sys.platform == "darwin":
        return ["afplay", str(audio_path)]
    for candidate in ("mpv", "ffplay"):
        if shutil.which(candidate):
            if candidate == "ffplay":
                return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(audio_path)]
            return ["mpv", "--no-video", "--really-quiet", str(audio_path)]
    raise PlaybackError("No audio player found (need afplay, mpv, or ffplay).")


async def play(audio: bytes, content_type: str) -> None:
    suffix = SUFFIX_BY_CONTENT_TYPE.get(content_type, ".mp3")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as audio_file:
        audio_file.write(audio)
        audio_path = Path(audio_file.name)

    try:
        process = await asyncio.create_subprocess_exec(
            *_player_command(audio_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        register_player(process)
        try:
            _, stderr = await process.communicate()
        finally:
            unregister_player(process)
        report_completion(process.returncode)
    finally:
        audio_path.unlink(missing_ok=True)
