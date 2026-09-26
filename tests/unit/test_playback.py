from pathlib import Path

import pytest

from noisy_studio import playback


def test_player_command_uses_afplay_on_macos(monkeypatch):
    monkeypatch.setattr(playback.sys, "platform", "darwin")

    command = playback._player_command(Path("/tmp/audio.mp3"))

    assert command == ["afplay", "/tmp/audio.mp3"]


def test_player_command_raises_when_no_player_available(monkeypatch):
    monkeypatch.setattr(playback.sys, "platform", "linux")
    monkeypatch.setattr(playback.shutil, "which", lambda _: None)

    with pytest.raises(playback.PlaybackError, match="No audio player found"):
        playback._player_command(Path("/tmp/audio.mp3"))


def test_interrupt_cancels_a_player_registered_after_connection_finishes():
    from unittest.mock import Mock

    process = Mock()
    events = []
    with playback.playback_scope(on_event=lambda kind, detail: events.append((kind, detail))):
        playback.stop_all_players()
        playback.register_player(process)
    process.kill.assert_called_once_with()
    assert events[0][0] == "playback_rejected"
    assert "scope_generation=" in events[0][1]

    next_process = Mock()
    with playback.playback_scope():
        playback.register_player(next_process)
    try:
        next_process.kill.assert_not_called()
    finally:
        playback.unregister_player(next_process)
