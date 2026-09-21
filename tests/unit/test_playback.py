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
