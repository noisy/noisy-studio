"""#41: a microphone that fails to open must not overwrite the user's pick."""

from __future__ import annotations

import pytest

from noisy_coding.listener import daemon
from noisy_coding.listener.state import ListenerState
from noisy_coding.listener.vad import VadConfig


class _Stream:
    def __init__(self, **kw):
        self.kw = kw
        self.started = False

    def start(self):
        self.started = True


def _fake_input_stream(fail_for: set[str | None]):
    def factory(**kw):
        device = kw.get("device")
        if device in fail_for:
            raise daemon.sd.PortAudioError(f"cannot open {device!r}")
        return _Stream(**kw)
    return factory


def test_failed_pick_falls_back_for_now_but_keeps_the_preference(monkeypatch):
    state = ListenerState()
    state.set_input_device("Jabra Link 380")
    monkeypatch.setattr(daemon.sd, "InputStream", _fake_input_stream({"Jabra Link 380"}))
    stream, opened = daemon._open_input_stream(state, VadConfig(), on_audio=lambda *a: None, history=daemon.MicrophoneHistory(state))
    assert isinstance(stream, _Stream) and stream.started
    assert opened == ""                                   # system default for now
    assert state.input_device == "Jabra Link 380"          # the pick survives
    assert state.active_input_device == ""
    rows = [u["text"] for u in state.utterances() if u["role"] == "system"]
    assert rows == ["MIC → system default (waiting for 'Jabra Link 380')"]


def test_pick_opens_when_available(monkeypatch):
    state = ListenerState()
    state.set_input_device("Jabra Link 380")
    monkeypatch.setattr(daemon.sd, "InputStream", _fake_input_stream(set()))
    _stream, opened = daemon._open_input_stream(state, VadConfig(), on_audio=lambda *a: None, history=daemon.MicrophoneHistory(state))
    assert opened == "Jabra Link 380"
    assert state.active_input_device == "Jabra Link 380"


def test_no_hardware_at_all_uses_the_browser_tab_without_rewriting_the_pick(monkeypatch):
    state = ListenerState()  # pick = system default
    monkeypatch.setattr(daemon.sd, "InputStream", _fake_input_stream({None}))
    stream, opened = daemon._open_input_stream(state, VadConfig(), on_audio=lambda *a: None, history=daemon.MicrophoneHistory(state))
    assert stream is None and opened == "browser"
    assert state.input_device == ""                        # preference untouched
    assert state.active_input_device == "browser"
