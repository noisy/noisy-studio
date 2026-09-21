"""Pausing playback must free the microphone.

Capture is muted while the agent speaks so the mic does not hear the
speakers. A paused clip makes no sound, so the reason is gone - and the
user pauses PRECISELY in order to say something. Leaving the mute on gave
a dashboard that said RECORDING while nothing was captured.
"""
from noisy_studio.listener.state import ListenerState


def test_pause_clears_the_echo_mute():
    state = ListenerState()
    state.set_claude_speaking(True, "agent")
    state.set_paused(True)          # echo mute, as speech begins
    assert state.paused is True

    state.set_paused(False)          # what /playback-pause now does
    assert state.paused is False, "a paused clip must not keep the mic muted"


def test_resume_restores_the_mute_while_still_speaking():
    state = ListenerState()
    state.set_claude_speaking(True, "agent")
    state.set_paused(False)          # paused by the user
    # Resuming: audio is about to play again, so the echo mute comes back.
    if state.claude_speaking:
        state.set_paused(True)
    assert state.paused is True


def test_user_mute_is_not_overridden_by_resuming():
    """The explicit dashboard mute is the user's, not ours to clear."""
    state = ListenerState()
    state.set_user_muted(True)
    state.set_paused(False)
    assert state.paused is True, "user mute must survive a playback resume"
