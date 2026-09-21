"""Play synthesized audio through the local speakers."""

import asyncio
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


# Currently-running player processes, so an interrupting speak can kill them.
_active_players: set[asyncio.subprocess.Process] = set()


def register_player(process: asyncio.subprocess.Process) -> None:
    _active_players.add(process)


def unregister_player(process: asyncio.subprocess.Process) -> None:
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
    global _paused
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
        # returncode is negative when killed by an interrupt — not an error.
        if process.returncode and process.returncode > 0:
            raise PlaybackError(
                f"Audio player exited with code {process.returncode}: {stderr.decode(errors='replace')[:200]}"
            )
    finally:
        audio_path.unlink(missing_ok=True)
