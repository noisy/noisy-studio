import threading
import time

from noisy_coding.listener import state as state_module
from noisy_coding.listener.state import VOICE_POOL, ListenerState


def _finishes_within(fn, seconds: float) -> bool:
    done = threading.Event()

    def run() -> None:
        fn()
        done.set()

    threading.Thread(target=run, daemon=True).start()
    return done.wait(seconds)


def test_drain_returns_transcripts_in_order_and_empties_queue():
    state = ListenerState()
    state.add_transcript("first")
    state.add_transcript("second")

    drained = state.drain()

    assert [t.text for t in drained] == ["first", "second"]
    assert state.drain() == []


def test_events_since_returns_only_newer_events_including_drain_delivery():
    state = ListenerState()
    state.add_event("recording")
    state.add_transcript("hello")
    seen = state.events_since(0)
    state.drain()

    fresh = state.events_since(seen[-1]["seq"])

    assert [e["kind"] for e in seen] == ["recording", "transcript"]
    assert [(e["kind"], e["detail"]) for e in fresh] == [("delivered", "hello")]


def test_last_transcript_at_tracks_newest_transcript():
    state = ListenerState()
    assert state.last_transcript_at == 0.0

    state.add_transcript("hello")

    assert state.last_transcript_at > 0.0


def test_wait_for_user_silence_returns_immediately_when_user_is_quiet():
    state = ListenerState()

    assert _finishes_within(state.wait_for_user_silence, seconds=1.0)


def test_wait_for_user_silence_blocks_until_recording_ends():
    state = ListenerState()
    state.set_recording(True)
    done = threading.Event()
    threading.Thread(
        target=lambda: (state.wait_for_user_silence(), done.set()), daemon=True
    ).start()

    assert not done.wait(0.15)
    state.set_recording(False)
    assert done.wait(1.0)


def test_wait_for_user_silence_treats_muted_mic_as_silence():
    state = ListenerState()
    state.set_recording(True)
    state.set_user_muted(True)

    assert _finishes_within(state.wait_for_user_silence, seconds=1.0)


def test_wait_for_user_silence_wakes_when_mic_gets_muted_mid_wait():
    state = ListenerState()
    state.set_recording(True)
    done = threading.Event()
    threading.Thread(
        target=lambda: (state.wait_for_user_silence(), done.set()), daemon=True
    ).start()

    assert not done.wait(0.15)
    state.set_user_muted(True)
    assert done.wait(1.0)


def test_wait_for_user_silence_grace_lets_the_user_add_a_thought():
    state = ListenerState()
    state.set_recording(True)
    state.set_recording(False)
    done = threading.Event()
    threading.Thread(
        target=lambda: (state.wait_for_user_silence(grace_s=0.3), done.set()),
        daemon=True,
    ).start()

    assert not done.wait(0.1)  # utterance just ended — still inside the grace
    state.set_recording(True)  # the user adds a follow-up thought
    assert not done.wait(0.35)  # held again, even though grace has elapsed
    state.set_recording(False)
    assert done.wait(1.0)


def test_user_utterance_commits_when_the_transcript_is_ready():
    state = ListenerState()
    utterance_id = state.create_utterance("user", "recording…")
    assert state.utterances()[0]["committed_at"] == 0.0  # still composing

    state.add_transcript("finished thought", utterance_id)

    assert state.utterances()[0]["committed_at"] > 0.0


def test_claude_utterance_commits_on_creation():
    state = ListenerState()
    state.create_utterance("claude", "queued")

    assert state.utterances()[0]["committed_at"] > 0.0


def test_input_device_defaults_to_system_and_remembers_the_pick():
    state = ListenerState()
    assert state.input_device == ""

    assert state.set_input_device("AirPods Pro") == "AirPods Pro"
    assert state.input_device == "AirPods Pro"

    assert state.set_input_device("") == ""  # back to system default


def test_system_rows_commit_on_creation():
    state = ListenerState()
    state.create_utterance("system", "", text="MIC → Jabra Link 380")

    row = state.utterances()[0]
    assert row["role"] == "system"
    assert row["committed_at"] > 0.0  # joins the timeline immediately


def test_usage_accumulates_audio_seconds_and_characters():
    state = ListenerState()
    assert state.usage == {"stt_seconds": 0.0, "tts_chars": 0}

    state.add_usage("stt_seconds", 7.5)
    state.add_usage("stt_seconds", 2.5)
    state.add_usage("tts_chars", 120)

    assert state.usage == {"stt_seconds": 10.0, "tts_chars": 120}


def test_latency_tracking_keeps_the_last_measurement_per_kind():
    state = ListenerState()
    assert state.latency_ms == {"stt": None, "tts": None}

    state.set_latency("stt", 412.7)
    state.set_latency("tts", 380.2)
    state.set_latency("stt", 350.0)

    assert state.latency_ms == {"stt": 350, "tts": 380}


def test_cancel_transcript_recalls_a_queued_message():
    state = ListenerState()
    utterance_id = state.create_utterance("user", "recording…")
    state.add_transcript("take this back", utterance_id)

    assert state.cancel_transcript(utterance_id) is True
    assert state.drain() == []
    statuses = {u["id"]: u["status"] for u in state.utterances()}
    assert statuses[utterance_id] == "cancelled by you"


def test_cancel_transcript_is_too_late_after_drain():
    state = ListenerState()
    utterance_id = state.create_utterance("user", "recording…")
    state.add_transcript("already delivered", utterance_id)
    state.drain()

    assert state.cancel_transcript(utterance_id) is False


def test_ptt_hold_is_a_lease_renewed_and_released():
    state = ListenerState()
    assert state.ptt_held is False

    state.refresh_ptt_hold()
    assert state.ptt_held is True

    state.release_ptt()
    assert state.ptt_held is False


def test_ptt_lease_expires_without_renewal(monkeypatch):
    monkeypatch.setattr(state_module, "PTT_LEASE_SECONDS", 0.05)
    state = ListenerState()
    state.refresh_ptt_hold()

    time.sleep(0.1)

    assert state.ptt_held is False


def test_detection_mode_accepts_only_known_values():
    state = ListenerState()
    assert state.set_detection_mode("ptt") == "ptt"
    assert state.set_detection_mode("nonsense") == "ptt"
    assert state.set_detection_mode("auto") == "auto"


def test_wait_for_user_silence_skips_grace_when_user_finished_long_ago():
    state = ListenerState()
    state.set_recording(True)
    state.set_recording(False)
    time.sleep(0.35)

    assert _finishes_within(
        lambda: state.wait_for_user_silence(grace_s=0.3), seconds=0.2
    )


def test_new_agent_never_steals_the_active_slot():
    state = ListenerState()
    state.register_agent("first")
    state.register_agent("second")

    assert state.active_agent == "first"


def test_stale_active_agent_keeps_the_mic_and_stays_visible(monkeypatch):
    monkeypatch.setattr(state_module, "AGENT_OFFLINE_AFTER_SECONDS", 0.05)
    state = ListenerState()
    state.register_agent("mine")
    state.register_agent("other")
    time.sleep(0.1)
    state.drain("other")  # only "other" keeps polling

    # Switching is the user's conscious act: the quiet active agent stays
    # active AND visible; its speech queues until it returns.
    assert state.active_agent == "mine"
    assert "mine" in state.agents
    assert state.drain("other") == []  # not their turn — speech is not rerouted


def test_silent_agents_go_offline_but_are_never_deleted(monkeypatch):
    monkeypatch.setattr(state_module, "AGENT_OFFLINE_AFTER_SECONDS", 0.05)
    state = ListenerState()
    state.register_agent("mine")
    state.register_agent("other")
    time.sleep(0.1)
    state.drain("mine")  # only the active one keeps polling

    meta = state.agents_meta
    assert "other" in state.agents  # known agents survive silence
    assert meta["other"]["online"] is False
    assert meta["other"]["offline_since"] is not None
    assert meta["mine"]["online"] is True


def test_agent_reactivation_restamps_its_arrival_into_the_active_group(monkeypatch):
    monkeypatch.setattr(state_module, "AGENT_OFFLINE_AFTER_SECONDS", 0.05)
    state = ListenerState()
    state.register_agent("early")
    state.register_agent("late")
    first_stamp = state.agents_meta["early"]["activated_at"]
    time.sleep(0.1)  # both go offline

    state.drain("early")  # "early" comes back → rejoins the actives LAST

    meta = state.agents_meta
    assert meta["early"]["online"] is True
    assert meta["early"]["activated_at"] > first_stamp
    assert meta["early"]["activated_at"] > meta["late"]["activated_at"]


def test_heartbeat_within_tolerance_keeps_the_activation_stamp():
    state = ListenerState()
    state.register_agent("steady")
    stamp = state.agents_meta["steady"]["activated_at"]

    state.drain("steady")  # normal heartbeat, no offline gap

    assert state.agents_meta["steady"]["activated_at"] == stamp


def test_transcript_follows_the_agent_the_user_started_talking_to():
    # Recording starts with A active; the user switches to B before the
    # transcription lands (#17). The speech belongs to A: B must not see
    # it, and A gets it even though A is no longer active.
    state = ListenerState()
    state.register_agent("a")
    state.register_agent("b")
    assert state.active_agent == "a"
    utterance_id = state.create_utterance("user", "recording…")

    state.set_active_agent("b")
    state.add_transcript("meant for a", utterance_id)

    assert state.drain("b") == []
    delivered = state.drain("a")
    assert [t.text for t in delivered] == ["meant for a"]
    assert state.drain("a") == []  # delivered once


def test_unstamped_transcript_keeps_the_active_agent_rule():
    state = ListenerState()
    state.register_agent("a")
    state.register_agent("b")

    state.add_transcript("no card", utterance_id=0)  # falls back to active=a

    assert state.drain("b") == []
    assert [t.text for t in state.drain("a")] == ["no card"]


def test_reorder_pins_manual_positions_for_known_agents_only():
    state = ListenerState()
    state.register_agent("a")
    state.register_agent("b")

    state.reorder_agents(["b", "ghost", "a"])

    meta = state.agents_meta
    assert meta["b"]["manual_pos"] == 0
    assert meta["a"]["manual_pos"] == 2
    assert "ghost" not in state.agents


def test_dismiss_removes_only_offline_non_active_agents(monkeypatch):
    monkeypatch.setattr(state_module, "AGENT_OFFLINE_AFTER_SECONDS", 0.05)
    state = ListenerState()
    state.register_agent("mine")
    state.register_agent("other")

    assert state.dismiss_agent("other") is False  # still online
    time.sleep(0.1)
    assert state.dismiss_agent("mine") is False  # active, even when silent
    assert state.dismiss_agent("ghost") is False  # unknown

    assert state.dismiss_agent("other") is True
    assert "other" not in state.agents
    assert "mine" in state.agents


def test_restore_active_agent_survives_the_first_to_register_race():
    state = ListenerState()
    state.restore_active_agent("mine")  # daemon restart restored the pick

    state.register_agent("interloper")  # polls first after the restart

    assert state.active_agent == "mine"
    assert "mine" in state.agents  # visible as a tab even before it returns


def test_mic_sensitivity_defaults_to_mid_and_clamps():
    state = ListenerState()

    assert state.mic_sensitivity == 50
    assert state.set_mic_sensitivity(250) == 100
    assert state.set_mic_sensitivity(-5) == 0
    assert state.set_mic_sensitivity(75) == 75


def test_tab_mic_requires_both_the_flag_and_a_live_lease():
    state = ListenerState()
    assert state.tab_mic_live is False

    state.set_tab_mic(True)
    assert state.tab_mic_live is False  # a dead lease can't have a live mic

    state.refresh_tab_audio()
    assert state.tab_mic_live is True

    state.release_tab_audio()
    assert state.tab_mic_live is False  # release clears the mic flag too


def test_queued_by_agent_counts_speech_waiting_to_be_heard():
    state = ListenerState()
    state.register_agent("a")
    state.register_agent("b")
    playing = state.create_utterance("claude", "queued", agent="a")
    state.create_utterance("claude", "queued", agent="a")
    state.create_utterance("claude", "synthesizing (Grok TTS)…", agent="b")
    state.create_utterance("claude", "unheard — muted", agent="b")
    state.create_utterance("claude", "played", agent="b")  # done — not waiting
    state.create_utterance("user", "queued", agent="a")  # user rows never count
    state.set_playing_utterance_id(playing)  # the live clip isn't "waiting"

    assert state.queued_by_agent == {"a": 1, "b": 2}


def test_mute_mid_clip_parks_the_playing_utterance_as_unheard():
    state = ListenerState()
    state.register_agent("a")
    playing = state.create_utterance("claude", "playing…", agent="a")
    state.set_playing_utterance_id(playing)

    interrupted = state.interrupt_playing_as_unheard("voice muted")

    assert interrupted == playing
    assert state.utterance_is_unheard(playing) is True
    assert state.playing_utterance_id == 0
    # The play pipeline consults this flag and must NOT relabel it played.


def test_agent_mute_only_interrupts_that_conversations_clip():
    state = ListenerState()
    state.register_agent("a")
    state.register_agent("b")
    playing = state.create_utterance("claude", "playing…", agent="a")
    state.set_playing_utterance_id(playing)

    # Muting the OTHER conversation must not touch a's clip.
    assert state.interrupt_playing_as_unheard("conversation muted", agent="b") == 0
    assert state.utterance_is_unheard(playing) is False
    assert state.playing_utterance_id == playing

    assert state.interrupt_playing_as_unheard("conversation muted", agent="a") == playing
    assert state.utterance_is_unheard(playing) is True


def test_interrupt_with_nothing_playing_is_a_noop():
    state = ListenerState()
    assert state.interrupt_playing_as_unheard("voice muted") == 0


def _make_working_agent(state, name, chatty=100, brevity=50):
    state.register_agent(name)
    state.set_character({"chatty": chatty, "brevity": brevity}, agent=name)
    state.set_activity(name, "Bash · building")  # actively working


def test_nudge_thresholds_interpolate_and_zero_disables():
    t = ListenerState._nudge_threshold_seconds
    assert t(0) is None
    assert t(25) == 600.0
    assert t(50) == 300.0
    assert t(100) == 75.0
    assert t(60) == 300.0 + (120.0 - 300.0) * (10 / 25)  # between anchors


def test_nudge_fires_once_per_silence_stretch_and_resets_on_speak(monkeypatch):
    state = ListenerState()
    _make_working_agent(state, "a", chatty=100, brevity=30)
    # Silence started at registration; fast-forward past the 75 s budget.
    state._agent_activated["a"] -= 100
    state._activity["a"]["at"] = __import__("time").time()

    nudge = state.pop_due_nudge("a")
    assert nudge is not None and "brevity setting (30/100)" in nudge
    assert state.pop_due_nudge("a") is None  # same stretch — no repeat

    state.note_agent_spoke("a")
    assert state.pop_due_nudge("a") is None  # fresh silence, budget not spent
    # Simulate the next stretch running out: the speak (and the old nudge)
    # happened 100 s ago, keeping real chronology nudge < speak < now.
    state._agent_last_spoke["a"] -= 100
    state._agent_last_nudge["a"] -= 200
    assert state.pop_due_nudge("a") is not None


def test_nudge_never_targets_idle_or_quiet_chatty_agents():
    state = ListenerState()
    _make_working_agent(state, "busy", chatty=0)
    state._agent_activated["busy"] -= 10_000
    assert state.pop_due_nudge("busy") is None  # chatty 0 = never

    state.register_agent("idle")
    state.set_character({"chatty": 100}, agent="idle")
    state._agent_activated["idle"] -= 10_000
    assert state.pop_due_nudge("idle") is None  # no fresh activity line


# --- voice claims -------------------------------------------------------
#
# The bug these cover: a pure hash gives every speaker a STABLE voice but
# not a UNIQUE one, so two viewers regularly ended up indistinguishable.


def _pick_first(seed: str, pool: tuple[str, ...]) -> str:
    """Worst-case hash: always returns the same voice, so any uniqueness
    in the result comes from the ledger rather than from luck."""
    return pool[0]


def test_claim_voice_is_stable_for_the_same_speaker():
    state = ListenerState()
    pool = ("ara", "atlas", "luna")

    first = state.claim_voice("xfuroo", pool, _pick_first)

    assert state.claim_voice("xfuroo", pool, _pick_first) == first


def test_claim_voice_never_hands_two_speakers_the_same_voice():
    state = ListenerState()
    pool = ("ara", "atlas", "luna")

    voices = [state.claim_voice(name, pool, _pick_first) for name in ("a", "b", "c")]

    assert sorted(voices) == ["ara", "atlas", "luna"]


def test_claim_voice_falls_back_to_the_hash_once_the_pool_is_exhausted():
    state = ListenerState()
    pool = ("ara",)
    state.claim_voice("first", pool, _pick_first)

    # A duplicate voice still beats no voice at all.
    assert state.claim_voice("second", pool, _pick_first) == "ara"


def test_claim_voice_avoids_a_voice_a_live_agent_is_already_using():
    state = ListenerState()
    state.register_agent("some-agent")  # heartbeat = live
    state.set_character({"voice": "atlas"}, "some-agent")
    pool = ("atlas", "luna")

    assert state.claim_voice("viewer", pool, _pick_first) == "luna"


def test_a_dormant_session_does_not_squat_on_its_voice():
    state = ListenerState()
    # A character bucket outlives the session that made it. This one never
    # sent a heartbeat, so it is long gone and must not deny anyone its voice.
    state.set_character({"voice": "lux"}, "session-from-july")
    pool = ("lux", "luna")

    assert state.claim_voice("viewer", pool, _pick_first) == "lux"
    assert state.set_voice_claim("other", "luna", pool) == "ok"


def test_the_voice_in_use_right_now_is_never_handed_out():
    state = ListenerState()
    state.set_character({"voice": "zenith"})  # the shared "" bucket
    pool = ("zenith", "luna")

    assert state.claim_voice("viewer", pool, _pick_first) == "luna"
    assert state.set_voice_claim("viewer2", "zenith", pool) == "taken"


def test_set_voice_claim_grants_a_free_voice():
    state = ListenerState()
    pool = ("ara", "atlas")

    assert state.set_voice_claim("xfuroo", "atlas", pool) == "ok"
    assert state.voice_claims()["xfuroo"] == "atlas"


def test_set_voice_claim_refuses_one_someone_else_holds():
    state = ListenerState()
    pool = ("ara", "atlas")
    state.set_voice_claim("first", "atlas", pool)

    assert state.set_voice_claim("second", "atlas", pool) == "taken"
    assert "second" not in state.voice_claims()


def test_set_voice_claim_rejects_a_voice_outside_the_pool():
    state = ListenerState()

    assert state.set_voice_claim("xfuroo", "nonesuch", ("ara",)) == "unknown"


def test_set_voice_claim_is_idempotent_for_the_current_holder():
    state = ListenerState()
    pool = ("ara", "atlas")
    state.set_voice_claim("xfuroo", "atlas", pool)

    assert state.set_voice_claim("xfuroo", "atlas", pool) == "ok"


def test_load_voice_claims_rehomes_duplicates_from_a_corrupted_file():
    # Formerly "drops duplicates": dropping made the speaker re-claim a random
    # free voice at their next speak. Re-homing keeps every name and keeps the
    # ledger exclusive.
    state = ListenerState()
    state.load_voice_claims({"a": "atlas", "b": "atlas", "c": 3, "d": "not a voice!"})
    claims = state.voice_claims()
    assert claims["a"] == "atlas"
    assert "c" not in claims and "d" not in claims           # garbage rows are still skipped
    assert claims["b"] != "atlas" and claims["b"] in VOICE_POOL  # duplicate re-homed, not dropped


def test_pending_transcripts_survive_a_restart_and_are_delivered_by_the_new_process():
    old = ListenerState()
    old.register_agent("tab-a", "Alpha")
    card = old.create_utterance("user", "recording…", agent="tab-a")
    old.add_transcript("still here after the restart", card)
    saved_history = old.snapshot_utterances()
    saved_pending = old.snapshot_transcripts()
    assert saved_pending[0]["addressee"] == "tab-a"

    new = ListenerState()
    new.register_agent("tab-a", "Alpha")
    new.load_utterances(saved_history)
    # load_utterances alone would have written the message off...
    assert new.utterances()[-1]["status"] == "dropped — daemon restart"
    # ...restoring the queue brings the card back to awaiting pickup and the
    # message is delivered to the addressee like nothing happened.
    assert new.load_transcripts(saved_pending) == 1
    assert new.utterances()[-1]["status"] == "ready — awaiting pickup"
    assert [t.text for t in new.drain("tab-a")] == ["still here after the restart"]
    assert new.utterances()[-1]["status"].startswith("delivered to")
    assert new.load_transcripts([{"garbage": True}]) == 0  # a bad row is skipped, not fatal



def test_new_agent_tabs_get_distinct_voices_not_a_copy_of_the_default():
    state = ListenerState()
    default_voice = state.character()["voice"]
    voices = [state.character(agent)["voice"] for agent in ("tab-a", "tab-b", "tab-c")]
    assert len(set(voices)) == 3, voices          # told apart by ear
    assert default_voice not in voices             # the shared voice is live, so it is taken
    assert state.character()["voice"] == default_voice  # the shared bucket is untouched
    # Stable: asking again returns the same voice, no reshuffle.
    assert state.character("tab-a")["voice"] == voices[0]


def test_an_explicitly_chosen_agent_voice_is_kept():
    state = ListenerState()
    state.set_character({"voice": "orion"}, agent="tab-a")
    assert state.character("tab-a")["voice"] == "orion"
    assert state.character("tab-b")["voice"] != "orion"  # first come, first served



def test_reloading_the_ledger_rehomes_duplicates_instead_of_dropping_them():
    state = ListenerState()
    # Two names on one voice (a capitalised duplicate used to slip past the check).
    state.load_voice_claims({"frank": "castor", "betangle": "Castor", "cat": "cosmo"})
    claims = state.voice_claims()
    assert set(claims) == {"frank", "betangle", "cat"}          # nobody is dropped
    assert claims["frank"] == "castor"                           # first keeps its voice
    assert claims["betangle"] not in ("castor", "cosmo")         # duplicate re-homed onto a free voice
    assert len(set(claims.values())) == 3                        # still exclusive
    assert state.take_voice_claims_dirty() is True               # and the repair gets saved


def test_reloading_keeps_duplicates_only_when_the_pool_is_exhausted():
    state = ListenerState()
    pool = ("ara", "luna")
    state.load_voice_claims({"a": "ara", "b": "luna", "c": "ara"}, pool=pool)
    claims = state.voice_claims()
    assert claims == {"a": "ara", "b": "luna", "c": "ara"}  # shared voice beats no voice



def test_tabs_that_copied_the_default_voice_are_rehomed_once_the_shared_bucket_keeps_it():
    state = ListenerState()
    default_voice = state.character()["voice"]
    # Pre-fix persisted characters: every tab a copy of the shared one.
    for agent in ("tab-a", "tab-b"):
        state.set_character({"voice": default_voice, "humor": 70}, agent=agent)
    state.set_character({"voice": "orion"}, agent="tab-c")  # a real choice
    moved = state.rehome_default_voice_copies()
    assert set(moved) == {"tab-a", "tab-b"}
    voices = {a: state.character(a)["voice"] for a in ("tab-a", "tab-b", "tab-c")}
    assert voices["tab-c"] == "orion"                     # explicit choice untouched
    assert default_voice not in voices.values()            # copies moved off
    assert len(set(voices.values())) == 3                  # and are distinct
    assert state.character()["voice"] == default_voice     # shared bucket keeps it
    assert state.character("tab-a")["humor"] == 70         # only the voice changed
    assert state.rehome_default_voice_copies() == []       # idempotent


def test_choosing_a_voice_for_a_tab_updates_its_ledger_claim():
    state = ListenerState()
    seeded = state.character("tab-a")["voice"]            # claimed at seeding
    state.set_character({"voice": "orion"}, agent="tab-a")
    assert state.voice_claims()["tab-a"] == "orion"
    assert seeded not in state.voice_claims().values() or seeded == "orion"



def test_restored_tabs_on_the_strip_never_share_a_voice_even_before_they_poll():
    from noisy_coding.harness.base import Capabilities
    from noisy_coding.harness.fake.adapter import FakeHarness, FakeSession

    state = ListenerState()
    harness = FakeHarness()
    tabs = []
    for _ in range(4):
        session = FakeSession()
        state.conversations.apply(harness.name, harness.interpret(session.start()), harness.capabilities)
        tabs.append(session.conversation)
    default_voice = state.character()["voice"]
    # Pre-fix persistence: every tab a copy of the default; nobody has polled yet.
    for key in tabs:
        state.set_character({"voice": default_voice}, agent=key)
    state.rehome_default_voice_copies()
    voices = [state.character(k)["voice"] for k in tabs]
    assert len(set(voices)) == 4, voices
    assert default_voice not in voices
    # A second run with two tabs colliding by hand still resolves to distinct voices.
    state.set_character({"voice": voices[0]}, agent=tabs[1])
    state.rehome_default_voice_copies()
    voices = [state.character(k)["voice"] for k in tabs]
    assert len(set(voices)) == 4, voices



def test_speaker_names_are_matched_case_insensitively_in_the_ledger():
    state = ListenerState()
    first = state.claim_voice("wootdragon", VOICE_POOL, _pick_first)
    assert state.claim_voice("WootDragon", VOICE_POOL, _pick_first) == first   # same person, same voice
    assert state.claim_voice(" WOOTDRAGON ", VOICE_POOL, _pick_first) == first
    assert state.set_voice_claim("WootDragon", "orion", VOICE_POOL) == "ok"
    assert state.claim_voice("wootdragon", VOICE_POOL, _pick_first) == "orion"
    # A file holding both casings restores ONE entry, the first one wins.
    fresh = ListenerState()
    fresh.load_voice_claims({"wootdragon": "helios", "WootDragon": "rex"})
    assert fresh.voice_claims() == {"wootdragon": "helios"}


def test_late_streaming_partial_cannot_replace_a_final_transcript():
    state = ListenerState()
    utterance = state.create_utterance('user', 'recording…')
    state.update_transcription_partial(utterance, 'A partial sentence')
    assert state.snapshot_utterances()[-1]['text'] == 'A partial sentence'
    state.add_transcript('The final corrected sentence.', utterance)
    finalized = state.snapshot_utterances()

    state.update_transcription_partial(utterance, 'An obsolete partial arriving after finalization')

    assert state.snapshot_utterances() == finalized


def test_late_streaming_partial_cannot_reopen_a_cancelled_recording():
    state = ListenerState()
    utterance = state.create_utterance('user', 'recording…')
    state.mark_utterance_cancelled(utterance)
    cancelled = state.snapshot_utterances()

    state.update_transcription_partial(utterance, 'Late words')

    assert state.snapshot_utterances() == cancelled
