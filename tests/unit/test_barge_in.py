"""Push-to-talk beats the echo mute (#61, #64)."""

from noisy_studio.listener.daemon import _ptt_barge_in
from noisy_studio.listener.state import ListenerState


def test_held_key_lifts_the_mute_and_parks_the_cut_clip_as_unheard():
    state = ListenerState()
    state.register_agent("tab-a", "Alpha")
    clip = state.create_utterance("claude", "playing through speakers…", text="long answer", agent="tab-a")
    state.set_playing_utterance_id(clip)
    state.set_claude_speaking(True, "tab-a")
    state.set_paused(True)  # the echo mute the speech thread sets while playing

    assert _ptt_barge_in(state) is True

    assert state.paused is False  # capture may proceed on this very frame
    card = next(u for u in state.utterances() if u["id"] == clip)
    assert card["status"] == "unheard — interrupted by push-to-talk"  # replayable, not "played"
    assert state.playing_utterance_id == 0


def test_barge_in_with_nothing_playing_only_lifts_the_mute():
    state = ListenerState()
    state.set_paused(True)
    assert _ptt_barge_in(state) is False
    assert state.paused is False


def test_user_mute_is_not_overridden_by_the_key():
    # The loop only calls barge-in when the pause is the echo mute, never the
    # user's explicit mute; the helper itself never touches user_muted.
    state = ListenerState()
    state.set_user_muted(True)
    state.set_paused(True)
    _ptt_barge_in(state)
    assert state.user_muted is True
    assert state.paused is True  # paused property includes the user mute



def test_the_interrupt_is_remembered_until_the_playback_thread_consumes_it():
    state = ListenerState()
    clip = state.create_utterance("claude", "playing through speakers…", text="x")
    state.set_playing_utterance_id(clip)
    state.interrupt_playing_as_unheard("interrupted by push-to-talk")
    # Streaming bookkeeping overwrites the card after the cut...
    state.update_utterance(clip, status="playing through speakers…")
    # ...and the playback thread, finishing, re-applies the interrupt exactly once.
    assert state.consume_interrupted(clip) == "unheard — interrupted by push-to-talk"
    assert state.consume_interrupted(clip) is None


def test_daemon_boot_helpers_are_importable():
    # A NameError at boot took the dev daemon down on stream (2026-09-13):
    # rehome_default_voice_copies() called save_characters() that daemon.py
    # never imported. Keep every boot-time helper resolvable.
    from noisy_studio.listener import daemon
    for name in ("save_characters", "_load_history", "_save_history", "_ptt_barge_in"):
        assert callable(getattr(daemon, name))



def test_barge_in_parks_the_addressees_clip_but_requeues_another_agents(monkeypatch):
    from noisy_studio.listener import daemon, speech

    requeued = []
    monkeypatch.setattr(speech, "submit", lambda state, text, **kw: requeued.append((text, kw)) or None)

    # Case 1: the agent you are talking to is speaking -> obsolete-able -> UNHEARD, no requeue.
    state = ListenerState()
    state.register_agent("me", "Me"); state.register_agent("other", "Other")
    state.set_active_agent("me")
    clip = state.create_utterance("claude", "playing…", text="old answer", agent="me")
    state.set_playing_utterance_id(clip); state.set_paused(True)
    assert daemon._ptt_barge_in(state) is True
    assert state.playing_clip() is None
    assert next(u for u in state.utterances() if u["id"] == clip)["status"] == "unheard — interrupted by push-to-talk"
    assert requeued == []

    # Case 2: a DIFFERENT agent is speaking -> still valid -> waits and replays from the start.
    clip2 = state.create_utterance("claude", "playing…", text="valid update", agent="other")
    state.set_playing_utterance_id(clip2); state.set_paused(True)
    assert daemon._ptt_barge_in(state) is True
    card = next(u for u in state.utterances() if u["id"] == clip2)
    assert card["status"] == "unheard — waiting — you were speaking"
    assert requeued == [("valid update", {"agent": "other", "card": False, "source_id": clip2})]



def test_the_stop_button_settles_the_clip_as_skipped_not_unheard():
    state = ListenerState()
    clip = state.create_utterance("claude", "playing through speakers…", text="x", agent="a")
    state.set_playing_utterance_id(clip)
    state.interrupt_playing_as_unheard("stopped by you", label="skipped")
    card = next(u for u in state.utterances() if u["id"] == clip)
    assert card["status"] == "skipped — stopped by you"
    assert state.utterance_is_unheard(clip) is False          # never counted for catch-up
    assert state.consume_interrupted(clip) == "skipped — stopped by you"  # and stays so after bookkeeping
