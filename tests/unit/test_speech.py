import asyncio
import time
import threading

import pytest

from noisy_studio import tts
from noisy_studio.listener import audio_cache, speech
from noisy_studio.listener.state import ListenerState


@pytest.fixture
def batch_pipeline(monkeypatch):
    """Batch TTS with a fresh in-memory cache — the deterministic pipeline."""
    monkeypatch.setattr(speech, "_audio_cache", audio_cache.AudioCache(directory=None))
    monkeypatch.setattr(speech, "_tts_streaming", lambda _state, _provider: False)
    monkeypatch.setattr(speech, "ECHO_TAIL_SECONDS", 0)


def _install_fake_synth(monkeypatch, calls, delay_s=0.0):
    async def fake_synthesize(text, voice, language, speed):
        started = time.monotonic()
        if delay_s:
            await asyncio.sleep(delay_s)
        calls.append({"text": text, "voice": voice, "started": started})
        return tts.SynthesizedAudio(b"mp3-bytes", "audio/mpeg", 0.0)

    monkeypatch.setattr(speech.tts, "synthesize", fake_synthesize)


def _install_fake_play(monkeypatch, intervals, delay_s=0.0):
    async def fake_play(_state, _audio, _cached, _utterance_id):
        started = time.monotonic()
        if delay_s:
            await asyncio.sleep(delay_s)
        intervals.append((started, time.monotonic()))

    monkeypatch.setattr(speech, "_play_audio", fake_play)


def test_playing_an_utterance_resets_the_narration_nudge_clock(monkeypatch, batch_pipeline):
    """A spoken utterance must reset the #16 silence clock. Regression guard:
    the reset used to live only in the HTTP /event handler, which the real
    playback path never crosses, so speaking never reset the clock."""
    state = ListenerState()
    state.register_agent("a")
    # Pin the clock's start far in the past so any reset is unmistakable.
    state._agent_last_spoke["a"] = time.time() - 10_000
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, [])

    speech.submit(state, "hello", agent="a").result(timeout=5)

    assert state.nudge_clocks()["a"]["silence"] < 5  # clock was reset on play


def test_muted_utterance_does_not_reset_the_narration_nudge_clock(monkeypatch, batch_pipeline):
    """Nothing was said aloud — the silence clock must keep running."""
    state = ListenerState()
    state.register_agent("a")
    state._agent_last_spoke["a"] = time.time() - 10_000
    state.set_voice_muted(True)
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, [])

    speech.submit(state, "hello", agent="a").result(timeout=5)

    assert state.nudge_clocks()["a"]["silence"] > 5_000  # unheard — not reset


def test_playback_queue_serializes_concurrent_speaks(monkeypatch, batch_pipeline):
    state = ListenerState()
    intervals = []
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, intervals, delay_s=0.1)

    futures = [speech.submit(state, f"utterance {i}") for i in range(2)]
    for future in futures:
        future.result(timeout=5)

    first_end = min(end for _, end in intervals)
    last_start = max(start for start, _ in intervals)
    assert last_start >= first_end


def test_next_clip_synthesizes_while_previous_still_plays(monkeypatch, batch_pipeline):
    state = ListenerState()
    synth_calls = []
    play_intervals = []
    _install_fake_synth(monkeypatch, synth_calls, delay_s=0.05)
    _install_fake_play(monkeypatch, play_intervals, delay_s=0.3)

    futures = [speech.submit(state, "first"), speech.submit(state, "second")]
    deadline = time.monotonic() + 2
    ready_seen = False
    while not ready_seen and time.monotonic() < deadline:
        statuses = {u["text"]: u["status"] for u in state.utterances()}
        ready_seen = statuses.get("second") == "ready — waiting for the speaker"
        time.sleep(0.01)
    for future in futures:
        future.result(timeout=5)

    second_synth_started = synth_calls[1]["started"]
    first_play_ended = play_intervals[0][1]
    assert second_synth_started < first_play_ended
    assert ready_seen  # the prefetched card said READY, not a stale "synthesizing"


def test_synthesis_runs_while_the_user_is_still_speaking(monkeypatch, batch_pipeline):
    state = ListenerState()
    state.set_recording(True)
    synth_calls = []
    _install_fake_synth(monkeypatch, synth_calls)
    _install_fake_play(monkeypatch, [])

    future = speech.submit(state, "prefetch me")
    deadline = time.monotonic() + 2
    while not synth_calls and time.monotonic() < deadline:
        time.sleep(0.01)

    assert synth_calls  # rendered during the user's turn — only playback waits
    state.set_recording(False)
    future.result(timeout=5)


def test_utterance_cards_appear_at_enqueue_in_creation_order(monkeypatch, batch_pipeline):
    state = ListenerState()
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, [], delay_s=0.2)

    futures = [speech.submit(state, "first"), speech.submit(state, "second")]
    texts = [u["text"] for u in state.utterances() if u["role"] == "claude"]

    assert texts == ["first", "second"]  # both visible before either played
    for future in futures:
        future.result(timeout=5)


def test_submit_without_card_plays_but_leaves_no_utterance(monkeypatch, batch_pipeline):
    state = ListenerState()
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, [])

    voice = speech.submit(state, "replayed message", card=False).result(timeout=5)

    assert voice  # played end to end
    assert state.utterances() == []  # replay must not duplicate the bubble


def test_daemon_speech_is_never_attributed_to_claude(monkeypatch, batch_pipeline):
    state = ListenerState()
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, [])

    speech.submit(state, "setup confirmation", role="daemon").result(timeout=5)

    card = state.utterances()[0]
    assert card["role"] == "daemon"
    assert card["status"] == "played"  # same pipeline, different byline


def test_voice_muted_parks_speech_as_unheard(monkeypatch, batch_pipeline):
    state = ListenerState()
    state.set_voice_muted(True)
    synth_calls = []
    played = []
    _install_fake_synth(monkeypatch, synth_calls)
    _install_fake_play(monkeypatch, played)

    voice = speech.submit(state, "hello there").result(timeout=5)

    assert voice  # resolves immediately — blocking speak must not hang
    assert synth_calls == []  # deferred = costs nothing until played
    assert played == []
    assert state.utterances()[0]["status"] == "unheard — voice muted"


def test_replay_with_source_walks_the_original_card_to_played(monkeypatch, batch_pipeline):
    state = ListenerState()
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, [])
    card_id = state.create_utterance("claude", "unheard — voice muted", text="parked")

    speech.submit(state, "parked", card=False, source_id=card_id).result(timeout=5)

    assert len(state.utterances()) == 1  # no duplicate card
    assert state.utterances()[0]["status"] == "played"


def test_replay_plays_from_cache_without_second_synthesis(monkeypatch, batch_pipeline):
    state = ListenerState()
    synth_calls = []
    _install_fake_synth(monkeypatch, synth_calls)
    _install_fake_play(monkeypatch, [])

    speech.submit(state, "say it once").result(timeout=5)
    card_id = state.utterances()[0]["id"]
    speech.submit(state, "say it once", card=False, source_id=card_id).result(timeout=5)

    assert len(synth_calls) == 1  # the replay reused the cached clip
    assert state.utterances()[0]["status"] == "played"


def test_replay_after_voice_change_resynthesizes(monkeypatch, batch_pipeline):
    state = ListenerState()
    synth_calls = []
    _install_fake_synth(monkeypatch, synth_calls)
    _install_fake_play(monkeypatch, [])

    speech.submit(state, "say it twice").result(timeout=5)
    card_id = state.utterances()[0]["id"]
    state.set_character({"voice": "rex"})
    speech.submit(state, "say it twice", card=False, source_id=card_id).result(timeout=5)

    assert [call["voice"] for call in synth_calls] == ["carina", "rex"]


def test_queued_clips_synthesize_concurrently_closest_first(monkeypatch, batch_pipeline):
    state = ListenerState()
    synth_calls = []
    _install_fake_synth(monkeypatch, synth_calls, delay_s=0.15)
    _install_fake_play(monkeypatch, [], delay_s=0.4)

    futures = [speech.submit(state, f"clip {i}") for i in (1, 2, 3)]
    for future in futures:
        future.result(timeout=5)

    # Synth windows overlap instead of queueing one behind the other:
    # clips 1 and 2 grab both workers at once (their exact start order is
    # scheduler noise), clip 3 must wait for a worker to free up.
    starts = {call["text"].split()[-1]: call["started"] for call in synth_calls}
    ends = {clip: started + 0.15 for clip, started in starts.items()}
    assert starts["2"] < ends["1"]  # 2 rendered alongside 1, not after it
    assert starts["3"] >= min(ends["1"], ends["2"])  # 3 queued for a free worker


def test_replay_clicks_jump_queued_speech_but_keep_click_order(monkeypatch, batch_pipeline):
    state = ListenerState()
    played_ids = []

    async def fake_play(_state, _audio, _cached, utterance_id):
        played_ids.append(utterance_id)
        await asyncio.sleep(0.2)

    _install_fake_synth(monkeypatch, [])
    monkeypatch.setattr(speech, "_play_audio", fake_play)
    old_a = state.create_utterance("claude", "played", text="old message a")
    old_b = state.create_utterance("claude", "played", text="old message b")

    fresh = [speech.submit(state, "fresh one"), speech.submit(state, "fresh two")]
    deadline = time.monotonic() + 2
    while not played_ids and time.monotonic() < deadline:
        time.sleep(0.01)  # replay clicks land while "fresh one" is mid-play
    replays = [
        speech.submit(state, "old message a", card=False, source_id=old_a),
        speech.submit(state, "old message b", card=False, source_id=old_b),
    ]
    for future in fresh + replays:
        future.result(timeout=5)

    fresh_one_id = old_b + 1
    fresh_two_id = old_b + 2
    assert played_ids == [fresh_one_id, old_a, old_b, fresh_two_id]


def test_transient_synthesis_error_invites_a_retry(monkeypatch, batch_pipeline):
    state = ListenerState()

    async def failing_synthesize(*_args):
        raise tts.GrokTTSError("Grok TTS request failed with HTTP 500: upstream sad")

    monkeypatch.setattr(speech.tts, "synthesize", failing_synthesize)
    _install_fake_play(monkeypatch, [])

    future = speech.submit(state, "doomed")
    with pytest.raises(tts.GrokTTSError):
        future.result(timeout=5)

    card = state.utterances()[0]
    assert card["status"] == "error — likely transient, tap ↻ to retry"
    assert "HTTP 500" in card["detail"]


def test_fatal_synthesis_error_says_retry_wont_help(monkeypatch, batch_pipeline):
    state = ListenerState()

    async def failing_synthesize(*_args):
        raise tts.GrokTTSError("Text is 20000 characters; the API accepts at most 15000.")

    monkeypatch.setattr(speech.tts, "synthesize", failing_synthesize)
    _install_fake_play(monkeypatch, [])

    future = speech.submit(state, "way too long")
    with pytest.raises(tts.GrokTTSError):
        future.result(timeout=5)

    assert state.utterances()[0]["status"] == "error — retry won't help"


def test_transient_synth_error_retries_automatically(monkeypatch, batch_pipeline):
    state = ListenerState()
    monkeypatch.setattr(speech, "SYNTH_RETRY_DELAYS_SECONDS", (0.0, 0.0))
    attempts = []

    async def flaky_synthesize(text, voice, language, speed):
        attempts.append(text)
        if len(attempts) < 3:
            raise tts.GrokTTSError("peer closed connection without sending complete message body")
        return tts.SynthesizedAudio(b"mp3-bytes", "audio/mpeg", 0.0)

    monkeypatch.setattr(speech.tts, "synthesize", flaky_synthesize)
    _install_fake_play(monkeypatch, [])

    speech.submit(state, "self-healing").result(timeout=5)

    assert len(attempts) == 3  # two transparent retries, then success
    assert state.utterances()[0]["status"] == "played"
    retry_events = [e for e in state.events_since(0) if e["kind"] == "speak_retry"]
    assert len(retry_events) == 2  # the log still tells the story


def test_fatal_synth_error_never_retries(monkeypatch, batch_pipeline):
    state = ListenerState()
    monkeypatch.setattr(speech, "SYNTH_RETRY_DELAYS_SECONDS", (0.0, 0.0))
    attempts = []

    async def oversized(text, voice, language, speed):
        attempts.append(text)
        raise tts.GrokTTSError("Text is 20000 characters; the API accepts at most 15000.")

    monkeypatch.setattr(speech.tts, "synthesize", oversized)
    _install_fake_play(monkeypatch, [])

    with pytest.raises(tts.GrokTTSError):
        speech.submit(state, "way too long").result(timeout=5)

    assert len(attempts) == 1  # the same request cannot ever succeed


def test_exhausted_retries_surface_the_error(monkeypatch, batch_pipeline):
    state = ListenerState()
    monkeypatch.setattr(speech, "SYNTH_RETRY_DELAYS_SECONDS", (0.0, 0.0))
    attempts = []

    async def always_down(text, voice, language, speed):
        attempts.append(text)
        raise tts.GrokTTSError("Grok TTS request failed with HTTP 503")

    monkeypatch.setattr(speech.tts, "synthesize", always_down)
    _install_fake_play(monkeypatch, [])

    with pytest.raises(tts.GrokTTSError):
        speech.submit(state, "doomed").result(timeout=5)

    assert len(attempts) == 3  # all attempts spent before giving up
    assert state.utterances()[0]["status"].startswith("error — likely transient")


def test_errored_card_replays_through_the_normal_path(monkeypatch, batch_pipeline):
    # Auto-retry off: this exercises the MANUAL ↻ path on a card that
    # already exhausted its chances and landed in ERROR.
    monkeypatch.setattr(speech, "SYNTH_RETRY_DELAYS_SECONDS", ())
    state = ListenerState()
    attempts = []

    async def flaky_synthesize(text, voice, language, speed):
        attempts.append(text)
        if len(attempts) == 1:
            raise tts.GrokTTSError("Grok TTS request failed with HTTP 502")
        return tts.SynthesizedAudio(b"mp3-bytes", "audio/mpeg", 0.0)

    monkeypatch.setattr(speech.tts, "synthesize", flaky_synthesize)
    _install_fake_play(monkeypatch, [])

    first = speech.submit(state, "flaky message")
    with pytest.raises(tts.GrokTTSError):
        first.result(timeout=5)
    card_id = state.utterances()[0]["id"]
    speech.submit(state, "flaky message", card=False, source_id=card_id).result(timeout=5)

    assert len(attempts) == 2  # the retry re-synthesized and succeeded
    assert state.utterances()[0]["status"] == "played"


def test_live_mode_streams_the_head_and_prefetches_the_queue(monkeypatch):
    state = ListenerState()
    monkeypatch.setattr(speech, "_audio_cache", audio_cache.AudioCache(directory=None))
    monkeypatch.setattr(speech, "_tts_streaming", lambda _state, _provider: True)
    monkeypatch.setattr(speech, "ECHO_TAIL_SECONDS", 0)
    synth_calls = []
    streamed = []
    _install_fake_synth(monkeypatch, synth_calls)
    _install_fake_play(monkeypatch, [])

    async def fake_stream_and_play(_state, text, _prepared, _utterance_id, _source_id, on_playback_complete):
        await asyncio.sleep(0.2)
        streamed.append(text)

    monkeypatch.setattr(speech, "_stream_and_play", fake_stream_and_play)

    futures = [speech.submit(state, "head"), speech.submit(state, "queued behind")]
    for future in futures:
        future.result(timeout=5)

    assert streamed == ["head"]  # the head streams for the fastest first audio
    assert [call["text"] for call in synth_calls] == ["queued behind"]  # batch prefetch
    statuses = [u["status"] for u in state.utterances()]
    assert statuses == ["played", "played"]


def test_render_waits_for_the_user_to_finish_before_playing(monkeypatch, batch_pipeline):
    state = ListenerState()
    state.set_recording(True)
    play_started_at = []

    async def fake_play(_state, _audio, _cached, _utterance_id):
        play_started_at.append(time.monotonic())

    _install_fake_synth(monkeypatch, [])
    monkeypatch.setattr(speech, "_play_audio", fake_play)

    future = speech.submit(state, "hold me")
    time.sleep(0.15)
    assert not play_started_at
    user_finished_at = time.monotonic()
    state.set_recording(False)
    future.result(timeout=5)

    assert play_started_at[0] >= user_finished_at


def test_resolve_options_reads_voice_and_speed_from_character_and_daemon_language():
    state = ListenerState()
    state.set_character({"voice": "rex", "speed": 1.2})
    state.set_language("pl")

    resolved = speech.resolve_options(state)

    assert resolved == ("rex", "pl", 1.2)


def test_resolve_options_uses_auto_language_when_nothing_configured(monkeypatch):
    monkeypatch.delenv(speech.DEFAULT_LANGUAGE_ENV_VAR, raising=False)
    state = ListenerState()

    resolved = speech.resolve_options(state)

    assert resolved == ("carina", "auto", 1.0)


def test_resolve_options_uses_the_speaking_agents_character():
    state = ListenerState()
    state.set_character({"voice": "rex"}, "agent-a")
    state.set_character({"voice": "ara"}, "agent-b")

    resolved = speech.resolve_options(state, agent="agent-b")

    assert resolved[0] == "ara"


@pytest.mark.parametrize('supports_streaming, preference, override, expected', [
    (False, 'live', 'live', {'speech_live_available':False,'speech_output_mode':'batch'}),
    (True, 'batch', '', {'speech_live_available':True,'speech_output_mode':'batch'}),
    (True, 'batch', 'live', {'speech_live_available':True,'speech_output_mode':'live'}),
])
def test_output_status_matches_the_playback_path(monkeypatch, supports_streaming, preference, override, expected):
    from types import SimpleNamespace
    state = ListenerState()
    state.set_tts_mode(preference)
    monkeypatch.setenv(speech.TTS_MODE_ENV_VAR, override)
    monkeypatch.setattr(speech.providers, 'active_tts', lambda: SimpleNamespace(supports_streaming=supports_streaming))

    assert speech.output_status(state) == expected


def test_ptt_barge_in_before_capture_holds_queued_clip_through_recording_and_grace(monkeypatch, batch_pipeline):
    state = ListenerState()
    state.set_detection_mode("ptt")
    state.set_paused(True)
    state.refresh_ptt_hold()
    _install_fake_synth(monkeypatch, [])
    waiting = threading.Event()
    played = threading.Event()
    wait_for_silence = state.wait_for_user_silence

    def wait(grace_s, **kwargs):
        waiting.set()
        return wait_for_silence(grace_s, **kwargs)

    async def play(*args):
        played.set()

    monkeypatch.setattr(state, "wait_for_user_silence", wait)
    monkeypatch.setattr(speech, "POST_TURN_GRACE_SECONDS", 0.1)
    monkeypatch.setattr(speech, "_play_audio", play)
    future = speech.submit(state, "queued reply")
    try:
        assert waiting.wait(2)
        assert not played.wait(0.05)
        state.set_paused(False)
        state.set_recording(True)
        state.release_ptt()
        assert not played.wait(0.15)
        state.set_recording(False)
        assert not played.wait(0.04)
        future.result(timeout=2)
        assert played.is_set()
        decisions = [e["detail"] for e in state.events_since(0) if e["kind"] == "speak_turn"]
        assert len(decisions) == 2
        assert "decision=hold recording=False paused=True user_muted=False ptt_held=True" in decisions[0]
        assert "decision=play held_ms=" in decisions[1]
    finally:
        state.release_ptt()
        state.set_recording(False)
        future.result(timeout=2)


def test_immediate_playback_logs_the_turn_flags(monkeypatch, batch_pipeline):
    state = ListenerState()
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, [])

    speech.submit(state, "ready reply").result(timeout=2)

    decisions = [e["detail"] for e in state.events_since(0) if e["kind"] == "speak_turn"]
    assert len(decisions) == 1
    assert "decision=play recording=False paused=False user_muted=False ptt_held=False" in decisions[0]


def test_user_starting_during_deferred_synthesis_is_waited_for(monkeypatch, batch_pipeline):
    state = ListenerState()
    waiting = threading.Event()
    played = threading.Event()
    monkeypatch.setattr(speech, "POST_TURN_GRACE_SECONDS", 0)
    monkeypatch.setattr(speech, "_prepare_audio", lambda *args: speech._PreparedSpeech("eve", "en", 1))

    def synthesize(*args):
        state.set_recording(True)
        return tts.SynthesizedAudio(b"mp3-bytes", "audio/mpeg", 0)

    wait_for_silence = state.wait_for_user_silence

    def wait(grace_s, **kwargs):
        waiting.set()
        return wait_for_silence(grace_s, **kwargs)

    async def play(*args):
        played.set()

    monkeypatch.setattr(speech, "_synthesize_now", synthesize)
    monkeypatch.setattr(state, "wait_for_user_silence", wait)
    monkeypatch.setattr(speech, "_play_audio", play)
    future = speech.submit(state, "rendered after unmute")
    try:
        assert waiting.wait(2)
        assert not played.wait(0.05)
        state.set_recording(False)
        future.result(timeout=2)
        assert played.is_set()
    finally:
        state.set_recording(False)
        future.result(timeout=2)


def test_ptt_interrupt_during_stream_connection_cancels_the_late_player(monkeypatch, batch_pipeline):
    from unittest.mock import Mock
    from noisy_studio import playback
    from noisy_studio.listener import daemon

    state = ListenerState()
    state.set_detection_mode("ptt")
    connecting = threading.Event()
    continue_connection = threading.Event()
    process = Mock()
    monkeypatch.setattr(speech, "_tts_streaming", lambda *args: True)

    async def connect_then_play(*args):
        connecting.set()
        assert await asyncio.to_thread(continue_connection.wait, 2)
        playback.register_player(process)
        playback.unregister_player(process)

    monkeypatch.setattr(speech, "_stream_and_play", connect_then_play)
    future = speech.submit(state, "connecting reply")
    try:
        assert connecting.wait(2)
        state.refresh_ptt_hold()
        assert daemon._ptt_barge_in(state)
        continue_connection.set()
        future.result(timeout=2)
        process.kill.assert_called_once_with()
        assert state.utterances()[0]["status"] == "unheard — interrupted by push-to-talk"
    finally:
        continue_connection.set()
        state.release_ptt()
        future.result(timeout=2)


def test_ptt_between_turn_hold_and_playback_scope_cancels_late_player(monkeypatch, batch_pipeline):
    from unittest.mock import Mock
    from noisy_studio import playback
    from noisy_studio.listener import daemon

    state = ListenerState()
    state.set_detection_mode("ptt")
    _install_fake_synth(monkeypatch, [])
    process = Mock()

    def press_ptt_after_hold(*args):
        state.refresh_ptt_hold()
        # Hotkeys renew the lease; the next capture frame invokes barge-in.
        assert state.paused
        daemon._ptt_barge_in(state)

    async def play(*args):
        playback.register_player(process)
        playback.unregister_player(process)

    monkeypatch.setattr(state, "note_agent_spoke", press_ptt_after_hold)
    monkeypatch.setattr(speech, "_play_audio", play)
    speech.submit(state, "reply losing the handoff race").result(timeout=2)

    process.kill.assert_called_once_with()
    assert state.utterances()[0]["status"].startswith("unheard")


@pytest.mark.parametrize("failure", [BrokenPipeError, OSError])
def test_failed_log_after_turn_claim_releases_capture(monkeypatch, batch_pipeline, failure):
    state = ListenerState()
    _install_fake_synth(monkeypatch, [])
    _install_fake_play(monkeypatch, [])

    def fail_log(message):
        if message.startswith("[speak] playing"):
            assert state.paused
            raise failure("diagnostic output unavailable")

    monkeypatch.setattr(speech, "_log", fail_log)
    with pytest.raises(failure, match="diagnostic output unavailable"):
        speech.submit(state, "reply").result(timeout=2)

    assert (state.paused, state.claude_speaking, state.playing_clip()) == (False, False, None)


def test_failed_release_diagnostic_inside_hold_releases_capture(monkeypatch, batch_pipeline):
    state = ListenerState()
    state.set_recording(True)
    _install_fake_synth(monkeypatch, [])
    wait_for_silence = state.wait_for_user_silence
    add_event = state.add_event
    monkeypatch.setattr(speech, "POST_TURN_GRACE_SECONDS", 0)

    def finish_recording_then_wait(grace_s, **kwargs):
        state.set_recording(False)
        return wait_for_silence(grace_s, **kwargs)

    def fail_release_event(kind, detail):
        if "held_ms=" in detail:
            assert state.paused
            raise OSError("release diagnostic failed")
        return add_event(kind, detail)

    monkeypatch.setattr(state, "wait_for_user_silence", finish_recording_then_wait)
    monkeypatch.setattr(state, "add_event", fail_release_event)
    with pytest.raises(OSError, match="release diagnostic failed"):
        speech.submit(state, "held reply").result(timeout=2)

    assert (state.paused, state.claude_speaking, state.playing_clip()) == (False, False, None)
