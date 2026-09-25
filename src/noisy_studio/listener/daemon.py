"""Always-on listener daemon: mic -> VAD -> Grok STT -> localhost queue.

Run with: noisy-studio-listener
The Claude Code hooks poll GET /drain on the HTTP API to pick up transcripts.
"""

import os
import queue
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx
import numpy as np
import sounddevice as sd

from noisy_studio.config_dir import CONFIG_DIR
from noisy_studio import providers
from noisy_studio.listener import speech, stt
import json

from noisy_studio.listener.http_api import (
    CHARACTER_FILE,
    DAEMON_VERSION,
    VOICE_CLAIMS_FILE,
    DEFAULT_PORT,
    PORT_ENV_VAR,
    SETTINGS_FILE,
    start_http_api,
    SPEAKER_COLORS_FILE,
    save_characters,
    save_settings,
)
from noisy_studio.listener.identity import canonical_identity, is_transcript_path
from noisy_studio.listener.state import ListenerState
from noisy_studio.listener.microphone_history import MicrophoneHistory
from noisy_studio.listener.state_stream import start_state_stream
from noisy_studio.listener.vad import UtteranceSegmenter, VadConfig

STT_LANGUAGE_ENV_VAR = "NOISY_STUDIO_STT_LANGUAGE"
MODE_ENV_VAR = "NOISY_STUDIO_MODE"
# Source defaults; saved settings (newer intent) override them.
INPUT_DEVICE_ENV_VAR = "NOISY_STUDIO_INPUT_DEVICE"
# Set by the desktop app to its own pid; the engine exits when that process dies.
PARENT_PID_ENV_VAR = "NOISY_STUDIO_PARENT_PID"


def _parent_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
MANAGEMENT_KEY_ENV_VAR = "NOISY_STUDIO_MANAGEMENT_KEY"
TEAM_ID_ENV_VAR = "NOISY_STUDIO_TEAM_ID"
CREDITS_POLL_SECONDS = 60.0
# Display gain for the dashboard mic level: int16 speech RMS is small
# (~0.02-0.08 full-scale), this maps it into a readable 0..1 range.
MIC_LEVEL_GAIN = 12.0
# While the push-to-talk lease is held, silence must never close the
# utterance — the button release is the only end-of-turn signal.
PTT_NEVER_CLOSE_MS = 10**9
# Check selected recognition readiness periodically instead of on every frame.
# A completed download or newly configured key becomes usable within this time.
RECOGNITION_READY_CHECK_SECONDS = 2.0
# A healthy mic feeds the callback ~30 frames/s; a multi-second starvation
# means the machine slept or the device vanished — after either, a
# long-lived PortAudio stream can come back degraded (wrong device /
# resampling), which garbles STT. Reopen instead of trusting it.
AUDIO_GAP_REOPEN_SECONDS = 5.0
# While the user's preferred microphone cannot be opened and we run on the
# fallback, retry the pick this often (#41).
PICK_RETRY_SECONDS = 10.0
# And when the stream dies OUTRIGHT (device disappears mid-utterance),
# frames stop arriving at all — the loop must not block forever waiting
# for one, or `recording` wedges True and the speech gate never releases.
FRAME_WAIT_SECONDS = 2.0
# Conversation history persistence: the log used to live only in memory,
# so every daemon restart wiped the conversation from the dashboard.
HISTORY_FILE = CONFIG_DIR / "history.json"
# Transcripts waiting for an agent (#76): they used to live only in memory,
# so every restart silently ate whatever the user had just said to a tab
# that was not listening at that moment.
PENDING_FILE = CONFIG_DIR / "pending.json"
HISTORY_SAVE_SECONDS = 5.0


def _ptt_barge_in(state: ListenerState) -> bool:
    """The held push-to-talk key wins over the echo mute (#61, #64).

    Capture is muted while the agent speaks so the microphone does not hear
    the speakers - and the capture loop dropped every frame while that mute
    was set, even with the key physically held. The key responded, the hum
    played, nothing was captured. Holding the key is a deliberate act, so
    it preempts: stop native playback, park the cut clip
    as UNHEARD so it can be replayed, lift the mute, and let this frame reach
    the segmenter. Auto (VAD) detection never does this - a cough must not
    cut the agent off. Returns True when a clip was actually interrupted.
    """
    from noisy_studio import playback

    clip = state.playing_clip()
    playback.stop_all_players()
    # Whose clip did we cut? Krzysztof's rule (2026-09-13): when the user
    # talks, everyone goes quiet - but only the ADDRESSEE's message may have
    # become obsolete by what the user is about to say, so it parks as
    # UNHEARD (replay or skip). Another agent's message is still valid: it
    # waits and plays again, from the start, once the user has finished.
    addressee = state.active_agent
    owner = (clip or {}).get("agent") or addressee
    if clip and owner != addressee:
        interrupted = state.interrupt_playing_as_unheard("waiting — you were speaking")
        text = str(clip.get("text") or "")
        if interrupted and text:
            try:
                speech.submit(state, text, agent=owner, card=False, source_id=interrupted)
            except Exception:
                pass  # worst case the card stays unheard and is replayable
    else:
        interrupted = state.interrupt_playing_as_unheard("interrupted by push-to-talk")
    state.set_paused(False)
    return bool(interrupted)


def _load_history(state: ListenerState) -> None:
    try:
        items = json.loads(HISTORY_FILE.read_text())
        if isinstance(items, list):
            state.load_utterances(items)
    except (OSError, ValueError):
        pass
    try:
        pending = json.loads(PENDING_FILE.read_text())
        if isinstance(pending, list) and pending:
            restored = state.load_transcripts(pending)
            if restored:
                _log(f"[history] restored {restored} waiting message(s) from the previous run")
    except (OSError, ValueError):
        pass


def _save_history(state: ListenerState) -> None:
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(state.snapshot_utterances()))
        PENDING_FILE.write_text(json.dumps(state.snapshot_transcripts()))
    except OSError:
        pass


def _history_saver(state: ListenerState) -> None:
    last_saved = ""
    while True:
        threading.Event().wait(HISTORY_SAVE_SECONDS)
        snapshot = json.dumps([state.snapshot_utterances(), state.snapshot_transcripts()])
        if snapshot != last_saved:
            _save_history(state)
            last_saved = snapshot


def _poll_credits(state: ListenerState) -> None:
    """Refresh the team's remaining prepaid credits once a minute."""
    management_key = os.environ.get(MANAGEMENT_KEY_ENV_VAR)
    team_id = os.environ.get(TEAM_ID_ENV_VAR)
    url = f"https://management-api.x.ai/v1/billing/teams/{team_id}/prepaid/balance"
    while True:
        try:
            response = httpx.get(
                url, headers={"Authorization": f"Bearer {management_key}"}, timeout=10
            )
            if response.status_code == httpx.codes.OK:
                cents = float(response.json().get("total", {}).get("val", 0))
                state.set_credits_usd(abs(cents) / 100)
        except (httpx.HTTPError, ValueError):
            pass
        threading.Event().wait(CREDITS_POLL_SECONDS)


def _log(message: str) -> None:
    print(message, flush=True)


@dataclass(frozen=True)
class RecognitionRequest:
    provider: providers.STTProvider
    language: str

    @classmethod
    def capture(cls, state: ListenerState) -> "RecognitionRequest":
        return cls(providers.active_stt(), state.language)


def _transcribe_and_enqueue(
    samples: np.ndarray,
    sample_rate: int,
    state: ListenerState,
    utterance_id: int,
    request: RecognitionRequest,
) -> None:
    provider = request.provider
    seconds = len(samples) / sample_rate
    cost = provider.cost_usd(seconds)
    state.add_cost("user", cost)
    state.add_usage("stt_seconds", seconds)
    _log(f"[transcribing] {seconds:.1f}s of audio (batch)")
    state.add_event("transcribing", f"{seconds:.1f}s")
    state.update_utterance(
        utterance_id,
        status=f"transcribing ({provider.label})…",
        detail=f"{seconds:.1f}s audio",
        cost_usd=cost,
        duration_s=round(seconds, 1),
    )
    stt_started = time.monotonic()
    wav_bytes = stt.encode_wav(samples, sample_rate)
    try:
        text = provider.transcribe(wav_bytes, request.language)
        state.set_latency("stt", (time.monotonic() - stt_started) * 1000)
    except providers.STTError as error:
        _log(f"[stt-error] {error}")
        state.add_event("stt_error", str(error)[:200])
        state.update_utterance(utterance_id, status="transcription error")
        return
    if not text:
        _log(f"[dropped] {seconds:.1f}s of audio transcribed to nothing")
        state.add_event("dropped", f"{seconds:.1f}s of audio, no speech")
        state.update_utterance(utterance_id, status="empty — no speech")
        return
    state.add_transcript(text, utterance_id)
    _log(f"[queued] ({seconds:.1f}s) {text}")


UTTERANCE_AUDIO_DIR = CONFIG_DIR / "utterance_audio"
UTTERANCE_AUDIO_KEEP = 200


def _archive_utterance_audio(utterance_id: int, wav_bytes: bytes) -> None:
    """Save one utterance's WAV; keep only the newest UTTERANCE_AUDIO_KEEP."""
    try:
        UTTERANCE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        (UTTERANCE_AUDIO_DIR / f"{stamp}-u{utterance_id}.wav").write_bytes(wav_bytes)
        stale = sorted(UTTERANCE_AUDIO_DIR.glob("*.wav"))[:-UTTERANCE_AUDIO_KEEP]
        for path in stale:
            path.unlink(missing_ok=True)
    except OSError:
        pass  # archiving is best-effort; transcription must not suffer


def _start_stream(
    segmenter, config: VadConfig, state: ListenerState, utterance_id: int,
    request: RecognitionRequest,
) -> providers.STTStreamSession | None:
    provider = request.provider
    if not provider.supports_streaming:
        return None  # batch-only backend (e.g. local) — the caller batches
    longest_shown = 0
    language = request.language

    def on_partial(text: str) -> None:
        # Server-side revisions can briefly shrink the text; never show that.
        nonlocal longest_shown
        if len(text) < longest_shown:
            return
        longest_shown = len(text)
        state.update_transcription_partial(utterance_id, text)

    smart_turn = state.smart_turn

    def on_turn_end() -> None:
        # smart_turn judged the thought complete: close the utterance now
        # instead of waiting for the VAD silence timer.
        segmenter.request_close()

    try:
        session = provider.open_stream(
            config.sample_rate,
            language,
            on_partial,
            smart_turn=smart_turn,
            on_turn_end=on_turn_end if smart_turn > 0 else None,
        )
    except providers.STTError as error:
        _log(f"[stream-error] {error} — falling back to batch for this utterance")
        return None
    if session is None:
        return None
    for frame in segmenter.recording_frames:
        session.send(frame.tobytes())
    return session


def _finalize_stream(
    session: providers.STTStreamSession,
    seconds: float,
    state: ListenerState,
    utterance_id: int,
    request: RecognitionRequest,
) -> None:
    cost = request.provider.streaming_cost_usd(seconds)
    state.add_cost("user", cost)
    state.add_usage("stt_seconds", seconds)
    state.update_utterance(
        utterance_id,
        detail=f"{seconds:.1f}s audio · live",
        cost_usd=cost,
        duration_s=round(seconds, 1),
    )
    finish_started = time.monotonic()
    text = session.finish()
    state.set_latency("stt", (time.monotonic() - finish_started) * 1000)
    if not text:
        _log(f"[dropped] {seconds:.1f}s live stream transcribed to nothing")
        state.update_utterance(utterance_id, status="empty — no speech")
        return
    state.add_transcript(text, utterance_id)
    _log(f"[queued/live] ({seconds:.1f}s) {text}")


def _open_input_stream(state, config, on_audio, *, history: MicrophoneHistory):
    wanted = state.input_device
    stream, opened = _open_selected_input_stream(state, config, on_audio, wanted=wanted)
    state.set_active_input_device(opened)
    effective = opened or 'system default'
    if stream is not None:
        try:
            effective = str(sd.query_devices(stream.device, 'input')['name'])
        except (AttributeError, KeyError, TypeError, ValueError, sd.PortAudioError):
            pass  # Keep the known selection if device metadata is unavailable.
    if stream is not None:
        history.record(effective, opened, wanted)
    return stream, opened


def _open_selected_input_stream(
    state: ListenerState, config: VadConfig, on_audio, *, wanted: str | None = None
) -> tuple["sd.InputStream | None", str]:
    """Open the wanted microphone, falling back to the system default.

    Returns (stream, opened) where `opened` is the device actually in use:
    the wanted name or "" for the system default. A missing native device
    returns no stream and is retried by the capture loop.

    The user's PICK is never rewritten here (#41): a device that is missing
    right now - unplugged headphones, a dock mid-switch, PortAudio refusing
    to reopen during a hardware change - falls back for the moment, and the
    capture loop keeps retrying the pick until it comes back. Rewriting the
    pick with the fallback is what made the selection lose the user’s intended microphone.
    """
    selected = state.input_device if wanted is None else wanted
    options = {"device": selected} if selected else {}
    input_stream = None
    try:
        input_stream = sd.InputStream(
            samplerate=config.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=config.frame_samples,
            callback=on_audio,
            **options,
        )
        input_stream.start()
    except (sd.PortAudioError, ValueError) as error:
        if input_stream is not None:
            input_stream.close()
        if not selected:
            _log(f"[mic] no native microphone available ({error}) — will retry")
            state.add_event("mic_error", "No native microphone is available. Connect a microphone or check system permissions; Noisy Studio will retry.")
            return None, ""
        _log(f"[mic] cannot open '{selected}': {error} — using system default for now, will retry")
        state.add_event("mic_error", f"cannot open '{selected}' — system default for now, retrying")
        stream, opened = _open_selected_input_stream(state, config, on_audio, wanted="")
        return stream, opened
    _log(f"[mic] listening on {selected or 'system default'}")
    return input_stream, selected


def load_saved_characters(state: ListenerState) -> None:
    """Restore legacy or per-session characters and persist their canonical shape."""
    try:
        saved_chars = json.loads(CHARACTER_FILE.read_text())
        # New format: {agent: character}. Old format: a single character dict.
        if saved_chars and all(isinstance(v, dict) for v in saved_chars.values()):
            # Fold path-keyed buckets onto their session id (#107). A
            # session used to be saved under both spellings, so restoring
            # the file as-is handed the same tab two characters - and the
            # one that won decided which voice you heard after a restart.
            by_identity: dict[str, dict] = {}
            for agent_key, char in saved_chars.items():
                key = canonical_identity(agent_key)
                # The id-keyed bucket is the one the hooks keep writing, so
                # it wins; a path-only bucket is simply renamed.
                if key in by_identity and is_transcript_path(agent_key):
                    continue
                by_identity[key] = char
            if len(by_identity) != len(saved_chars):
                _log(f"[character] folded {len(saved_chars) - len(by_identity)} duplicate identity bucket(s) (#107)")
            for agent_key, char in by_identity.items():
                state.set_character(char, agent_key)
        else:
            state.set_character(saved_chars)
        moved = state.rehome_default_voice_copies()
        if moved:
            _log(f"[character] {len(moved)} tab(s) moved off the shared default voice (#54)")
        if moved or state.all_characters() != saved_chars:
            save_characters(state)
    except (OSError, ValueError, AttributeError):
        pass


def migrate_audio_settings(state: ListenerState, saved: dict) -> None:
    if isinstance(saved, dict) and (saved.get("input_device") == "browser" or "output_device" in saved):
        if saved.get("input_device") == "browser":
            state.set_input_device("")
        save_settings(state)
        state.add_event("settings_migrated", "Audio settings updated to native microphone and system speakers")


def run(config: VadConfig | None = None) -> None:
    config = config or VadConfig()
    port = int(os.environ.get(PORT_ENV_VAR, str(DEFAULT_PORT)))

    state = ListenerState()
    state.microphone_sample.sample_rate = config.sample_rate
    state.set_mode(os.environ.get(MODE_ENV_VAR, "live"))
    state.set_language(os.environ.get(STT_LANGUAGE_ENV_VAR, ""))
    state.set_input_device(os.environ.get(INPUT_DEVICE_ENV_VAR, ""))
    load_saved_characters(state)
    # A voice a speaker earned is theirs across restarts too - the ledger is
    # only meaningful if it outlives the process that wrote it.
    try:
        state.load_voice_claims(json.loads(VOICE_CLAIMS_FILE.read_text()))
    except (OSError, ValueError, AttributeError):
        pass
    # Chat-platform bubble colors follow the same rule.
    try:
        state.load_speaker_colors(json.loads(SPEAKER_COLORS_FILE.read_text()))
    except (OSError, ValueError, AttributeError):
        pass
    saved = {}
    # Saved tuning (pause-split, smart_turn, mode) survives restarts and
    # overrides the env default for mode, since it reflects newer intent.
    try:
        saved = json.loads(SETTINGS_FILE.read_text())
        if "max_utterance_ms" in saved:
            state.set_max_utterance_ms(saved["max_utterance_ms"])
        if "end_silence_ms" in saved:
            state.set_end_silence_ms(saved["end_silence_ms"])
        if "mic_sensitivity" in saved:
            state.set_mic_sensitivity(saved["mic_sensitivity"])
        if "smart_turn" in saved:
            state.set_smart_turn(saved["smart_turn"])
        if saved.get("mode") in ("batch", "live"):
            state.set_mode(saved["mode"])
        if saved.get("tts_mode") in ("batch", "live"):
            state.set_tts_mode(saved["tts_mode"])
        if saved.get("smart_turn_mode") in ("soft", "hard"):
            state.set_smart_turn_mode(saved["smart_turn_mode"])
        if saved.get("detection_mode") in ("auto", "ptt"):
            state.set_detection_mode(saved["detection_mode"])
        if isinstance(saved.get("hotkeys"), dict):
            state.set_hotkeys({str(a): str(t or "") for a, t in saved["hotkeys"].items()})
        else:
            # Pre-#104 settings: the three named keys become the map.
            state.set_ptt_keys(
                str(saved.get("ptt_hold_key", "")),
                str(saved.get("ptt_toggle_key", "")),
                str(saved.get("ptt_cancel_key", "")),
            )
        if "input_device" in saved:
            state.set_input_device(str(saved["input_device"]))
        if "language" in saved:
            state.set_language(saved["language"])
        if saved.get("active_agent"):
            # The user's chosen agent survives restarts: without this, the
            # first agent to poll after boot would win the mic — and the
            # user would unknowingly talk to the wrong Claude (P1).
            state.restore_active_agent(str(saved["active_agent"]))
    except (OSError, ValueError):
        pass
    migrate_audio_settings(state, saved)
    _load_history(state)
    threading.Thread(target=_history_saver, args=(state,), daemon=True).start()
    # Conversations (the harness-contract view of the tabs) persist across
    # restarts: keys, aliases, titles and order come back; every tab starts
    # deaf until its session's next hook proves someone is listening.
    from noisy_studio.listener.conversations import ConversationRegistry

    state.conversations = ConversationRegistry(path=CONFIG_DIR / "conversations.json")
    for key in state.conversations.visible_keys():
        conversation = state.conversations.get(key)
        if conversation is not None:
            state.register_agent(key, conversation.label())
    # Providers own integration I/O; the core supplies queue ownership and receipts.
    from noisy_studio.harness.provider import Speech
    for item in state.snapshot_transcripts():
        state.submit_speech(Speech(item["utterance_id"], item["addressee"], item["text"], item["timestamp"]))
    state.conversations.providers.start(state.record_delivery, state.reserve_speech, lambda: state.recording, state.restore_delivery)
    # Global PTT hotkeys (#25): armed only when a key is configured. The
    # listener hangs off the state so the /settings endpoint can rearm it.
    from noisy_studio.listener import hotkey as hotkey_mod
    from noisy_studio.listener.hotkey import HotkeyListener

    hotkeys = HotkeyListener(state, _log)
    state.hotkey_listener = hotkeys
    state.fill_default_hotkeys(hotkey_mod.DEFAULT_HOTKEYS)  # never overrides a stored value
    hotkeys.configure_bindings(state.hotkeys)  # boot never prompts (#97)

    def _parent_watchdog() -> None:
        # The app that spawned us may die without SIGTERM (crash, force
        # quit). "Not detached" does not protect against that: the engine
        # would live on as an orphan holding the microphone. Exit when the
        # parent named in the environment is gone.
        import time as _time

        parent = os.environ.get(PARENT_PID_ENV_VAR, "")
        if not parent.isdigit():
            return
        while _parent_alive(int(parent)):
            _time.sleep(2)
        _log("[daemon] parent process gone - shutting down")
        state.schedule_shutdown(0)
        _time.sleep(5)  # the shutdown watcher lets a recording finish; then hard stop
        os._exit(0)

    threading.Thread(target=_parent_watchdog, daemon=True, name="parent-watchdog").start()

    def _shutdown_watcher() -> None:
        # Graceful shutdown (#35): exit only past the deadline AND never
        # mid-recording - an in-flight utterance gets to finish first.
        import time as _time

        while True:
            _time.sleep(0.5)
            at = state.shutdown_at
            if not at or _time.time() < at:
                continue
            if state.recording or state.claude_speaking:
                # Mid-sentence speech is safe in BOTH directions: the
                # user's recording finishes, and Claude's clip on the
                # speakers plays out (a killed clip would resurrect as a
                # duplicate via the MCP retry).
                continue
            _log("[shutdown] graceful exit (requested via /shutdown)")
            _save_history(state)
            os._exit(0)

    threading.Thread(target=_shutdown_watcher, daemon=True).start()
    server = start_http_api(state, port)
    if os.environ.get(MANAGEMENT_KEY_ENV_VAR) and os.environ.get(TEAM_ID_ENV_VAR):
        threading.Thread(target=_poll_credits, args=(state,), daemon=True).start()
    segmenter = UtteranceSegmenter(config)
    frames: queue.Queue[np.ndarray] = queue.Queue()
    stt_executor = ThreadPoolExecutor(max_workers=1)
    # Push dashboard snapshots independently of native audio capture.
    from noisy_studio.listener.http_api import state_snapshot

    start_state_stream(port, snapshot=lambda: state_snapshot(state))

    def on_audio(indata: np.ndarray, *_args: object) -> None:
        if state.user_muted:
            state.microphone_sample.feed(indata[:, 0].tobytes())
        frames.put(indata[:, 0].copy())

    _log(f"noisy-studio-listener: mic on, API at http://127.0.0.1:{port}")
    _log("Endpoints: GET /drain /status, POST /speak /pause /resume. Ctrl+C to stop.")

    microphone_history = MicrophoneHistory(state, CONFIG_DIR / "microphone-state.json")
    active_input, active_device = _open_input_stream(state, config, on_audio, history=microphone_history)
    wanted_device = state.input_device  # the pick we last acted on
    last_pick_retry = time.monotonic()
    try:
        try:
            current_utterance_id = 0
            recognition_request: RecognitionRequest | None = None
            stream: providers.STTStreamSession | None = None
            recognition_ready = False
            recognition_check_at = 0.0
            last_frame_at = time.monotonic()

            def reopen_input(reason: str, kind: str = "mic") -> None:
                nonlocal active_input, active_device, wanted_device, last_pick_retry, segmenter, stream, last_frame_at
                _log(f"[mic] {reason} — reopening input stream")
                state.add_event(kind, f"input reopened: {reason}")
                # New stream = new acoustics: the adaptive noise floor
                # calibrated on the old device is void — a dead device's
                # digital silence anchors it near zero, after which every
                # ambient sound reads as speech and the utterance never
                # closes. Fresh segmenter; a half-recorded utterance is
                # closed out honestly.
                if segmenter.is_recording:
                    state.update_utterance(
                        current_utterance_id, status="dropped — mic changed"
                    )
                if stream is not None:
                    stream.abort()
                    stream = None
                segmenter = UtteranceSegmenter(config)
                state.set_recording(False)
                if active_input is not None:  # No stream while native hardware is unavailable
                    active_input.stop()
                    active_input.close()
                # PortAudio enumerates devices ONCE per initialization, so a
                # microphone plugged in after daemon start is invisible to
                # this process even though /devices (a fresh subprocess)
                # lists it - the root of issue #41. With our only input
                # stream now closed, re-initializing PortAudio is safe and
                # refreshes the device table, so the reopen below can find
                # the newcomer. A concurrent TTS playback stream would make
                # the reinit throw - then we keep the old instance and log.
                try:
                    sd._terminate()
                    sd._initialize()
                    _log("[mic] PortAudio reinitialized - device table refreshed")
                except Exception as error:  # noqa: BLE001 - keep the old instance
                    _log(f"[mic] PortAudio reinit skipped: {error}")
                active_input, active_device = _open_input_stream(state, config, on_audio, history=microphone_history)
                wanted_device = state.input_device
                last_pick_retry = time.monotonic()
                last_frame_at = time.monotonic()

            def finalize_open_segment() -> None:
                """Close the in-progress utterance NOW with the audio it
                holds when capture stops and no further frame will arrive."""
                nonlocal stream
                utterance = segmenter.flush()
                state.set_recording(False)
                if stream is not None:
                    seconds = (
                        len(utterance) / config.sample_rate
                        if utterance is not None
                        else config.min_utterance_ms / 1000
                    )
                    stt_executor.submit(
                        _finalize_stream, stream, seconds, state, current_utterance_id, recognition_request
                    )
                    stream = None
                elif utterance is not None:
                    stt_executor.submit(
                        _transcribe_and_enqueue,
                        utterance,
                        config.sample_rate,
                        state,
                        current_utterance_id,
                        recognition_request,
                    )
                else:
                    state.update_utterance(
                        current_utterance_id, status="dropped — too short"
                    )

            while True:
                try:
                    frame = frames.get(timeout=FRAME_WAIT_SECONDS)
                except queue.Empty:
                    if state.input_device != wanted_device:
                        reopen_input("input device switched")
                    elif active_device != state.input_device and time.monotonic() - last_pick_retry >= PICK_RETRY_SECONDS:
                        reopen_input("retrying the preferred microphone")
                    elif active_input is not None or time.monotonic() - last_pick_retry >= PICK_RETRY_SECONDS:
                        reopen_input("no audio frames (stream stalled)", kind="mic_error")
                    continue
                now = time.monotonic()
                frame_gap = now - last_frame_at
                last_frame_at = now
                if state.input_device != wanted_device:
                    reopen_input("microphone switched")
                    continue  # this frame may still be the old stream's
                if active_device != state.input_device and now - last_pick_retry >= PICK_RETRY_SECONDS:
                    # Running on the fallback while the user's pick is
                    # missing: try the pick again - it comes back by itself
                    # when the headset or dock reappears (#41).
                    reopen_input("retrying the preferred microphone")
                    continue
                # A long gap means stale PortAudio buffers after sleep/wake.
                if frame_gap > AUDIO_GAP_REOPEN_SECONDS:
                    reopen_input(f"{frame_gap:.0f}s audio gap (sleep/device change?)")
                    continue
                if now >= recognition_check_at:
                    recognition_ready = providers.direction_ready('stt')
                    recognition_check_at = now + RECOGNITION_READY_CHECK_SECONDS
                if (
                    state.paused
                    and not state.user_muted
                    and state.detection_mode == "ptt"
                    and state.ptt_held
                ):
                    # Echo mute vs a HELD key: the key wins (#61, #64).
                    if _ptt_barge_in(state):
                        _log("[recording] push-to-talk interrupted the agent")
                        state.add_event("barge_in", "push-to-talk interrupted the agent's speech")
                if state.paused:
                    # A muted mic isn't listening — the oscilloscope must
                    # flatline instead of showing our own playback echo.
                    state.set_mic_level(0.0)
                    # And it must never CLAIM to be recording (#61): the UI
                    # read a stale flag while no frame reached the segmenter.
                    if not segmenter.is_recording:
                        state.set_recording(False)
                    # A muted mic must not stay recording either: paused
                    # frames never reach the segmenter, so an utterance
                    # open at mute time would freeze in "transcribing…"
                    # until unmute. Mute is the hardest end-of-turn signal
                    # there is — close the segment NOW with the audio it
                    # already holds. Only for the user's explicit mute:
                    # the transient echo-pause during playback must not
                    # cut a PTT barge-in recording short.
                    if segmenter.is_recording and state.user_muted:
                        _log("[recording] closed by mic mute")
                        state.add_event("recording_done", "closed by mic mute")
                        finalize_open_segment()
                    continue
                # Live level for the dashboard oscilloscope: frame RMS in
                # 0..1, scaled so normal speech lands around 0.2-0.8.
                rms = float(np.sqrt(np.mean((frame / 32768.0) ** 2)))
                state.set_mic_level(min(1.0, rms * MIC_LEVEL_GAIN))
                # Unprepared recognition stays idle, but local speech needs no
                # cloud key. An in-progress turn retains its captured engine.
                if not recognition_ready and not segmenter.is_recording:
                    state.set_recording(False)
                    continue
                # Scratch-my-words: the cancel hotkey (or /abort-recording)
                # kills the utterance in progress in ANY mode - audio
                # dropped, card marked cancelled, stream torn down.
                if state.consume_recording_abort() and segmenter.is_recording:
                    segmenter.discard()
                    state.set_recording(False)
                    if stream is not None:
                        stream.abort()
                        stream = None
                    if current_utterance_id:
                        state.mark_utterance_cancelled(current_utterance_id)
                    _log("[recording] scratched by the cancel hotkey")
                    state.add_event("recording_done", "scratched — cancel hotkey")
                    continue
                # Push-to-talk: the held button IS the turn signal. Idle =
                # cold mic (nothing captured); held = the utterance never
                # closes on silence; release = close it right now.
                ptt = state.detection_mode == "ptt"
                ptt_held = ptt and state.ptt_held
                if ptt and not ptt_held and not segmenter.is_recording:
                    state.set_recording(False)
                    continue
                if ptt_held:
                    segmenter.end_silence_ms_override = PTT_NEVER_CLOSE_MS
                else:
                    segmenter.end_silence_ms_override = state.end_silence_ms
                    if ptt and segmenter.is_recording:
                        segmenter.request_close()
                segmenter.max_utterance_ms_override = state.max_utterance_ms
                segmenter.smart_turn_mode = state.smart_turn_mode
                segmenter.mic_sensitivity_override = state.mic_sensitivity
                was_recording = segmenter.is_recording
                utterance = segmenter.feed(frame)
                state.set_recording(segmenter.is_recording)
                if segmenter.is_recording and not was_recording:
                    _log("[recording] user started speaking")
                    state.add_event("recording")
                    current_utterance_id = state.create_utterance("user", "recording…")
                    try:
                        recognition_request = RecognitionRequest.capture(state)
                    except providers.STTError as error:
                        segmenter.discard()
                        state.set_recording(False)
                        state.update_utterance(current_utterance_id, status="recognition unavailable")
                        state.add_event("stt_error", str(error)[:200])
                        continue
                    if state.mode == "live":
                        stream = _start_stream(
                            segmenter, config, state, current_utterance_id, recognition_request
                        )
                elif segmenter.is_recording and stream is not None:
                    stream.send(frame.tobytes())
                elif was_recording and not segmenter.is_recording:
                    silence_note = (
                        f"{state.end_silence_ms / 1000:.1f}s of silence — closing utterance"
                    )
                    _log(f"[recording] done — {silence_note}")
                    state.add_event("recording_done", silence_note)
                    if utterance is None:
                        if stream is not None:
                            # A short clip may still hold real words — let the
                            # stream finalize; only truly empty ones are dropped.
                            stt_executor.submit(
                                _finalize_stream,
                                stream,
                                config.min_utterance_ms / 1000,
                                state,
                                current_utterance_id,
                                recognition_request,
                            )
                            stream = None
                        else:
                            state.update_utterance(
                                current_utterance_id, status="dropped — too short"
                            )
                if utterance is not None:
                    seconds = len(utterance) / config.sample_rate
                    # Archive in BOTH modes: the segmenter hands back the
                    # full utterance even when a live stream transcribed it,
                    # and live mode is precisely where the mangled
                    # transcripts happen - the evidence must cover it.
                    _archive_utterance_audio(
                        current_utterance_id,
                        stt.encode_wav(utterance, config.sample_rate),
                    )
                    if stream is not None:
                        stt_executor.submit(
                            _finalize_stream, stream, seconds, state, current_utterance_id, recognition_request
                        )
                        stream = None
                    else:
                        stt_executor.submit(
                            _transcribe_and_enqueue,
                            utterance,
                            config.sample_rate,
                            state,
                            current_utterance_id,
                            recognition_request,
                        )
        except KeyboardInterrupt:
            _log("\nnoisy-studio-listener: stopping")
        finally:
            _save_history(state)
            server.shutdown()
            stt_executor.shutdown(wait=False)
            speech.shutdown()
    finally:
        active_input.stop()
        active_input.close()


def main() -> None:
    if "--version" in sys.argv[1:]:
        # Lets a build assert what it froze (#100) without opening audio.
        print(DAEMON_VERSION)
        return
    if "--list-devices" in sys.argv[1:]:
        # The frozen daemon's device probe (see http_api._device_probe_command):
        # a fresh PortAudio instance, JSON on stdout, no server, no mic.
        import json as _json

        devices = sd.query_devices()
        default_in = sd.default.device[0]
        print(_json.dumps([
            {"name": d["name"], "default": i == default_in}
            for i, d in enumerate(devices) if d["max_input_channels"] > 0
        ]))
        return
    try:
        run()
    except sd.PortAudioError as error:
        print(f"Cannot open microphone: {error}", file=sys.stderr)
        print(
            "Hint: check microphone permission in System Settings, reconnect your "
            "microphone, and select an available input device in Noisy Studio.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
