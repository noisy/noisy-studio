"""Render TTS and play it aloud — the daemon's side of speak/announce.

Speech is a two-stage pipeline. The synth stage renders utterances to
audio AHEAD of playback, so clip N+1 is ready the instant clip N leaves
the speaker; the playback stage plays strictly in submit order — one voice
at a time, still gated on the user's turn. Each stage is its own
single-worker executor and submit() enqueues into both at once, so
playback order is submit order no matter how synthesis timing lands.

Rendered audio also lands in a bounded cache (see audio_cache): replaying
a card reuses the bytes instead of paying Grok for the same clip again.
"""

import asyncio
import itertools
import os
import re
import threading
import time
from collections import deque
from concurrent.futures import Future
from dataclasses import dataclass

from noisy_coding import playback, providers, tts
from noisy_coding.listener import audio_cache
from noisy_coding.listener.state import ListenerState

DEFAULT_VOICE_ENV_VAR = "NOISY_CODING_DEFAULT_VOICE"
DEFAULT_LANGUAGE_ENV_VAR = "NOISY_CODING_DEFAULT_LANGUAGE"
TTS_MODE_ENV_VAR = "NOISY_CODING_TTS_MODE"
FALLBACK_VOICE = "eve"
# Physical echo guard, not turn-taking: the room's sound tail after the
# player exits would land in the just-unmuted mic and get transcribed.
ECHO_TAIL_SECONDS = 0.25
# Conversational courtesy (Krzysztof's spec: "~2s max"): when his utterance
# has JUST ended, give him a beat to tack on a follow-up thought before we
# take the speaker. Counts from the actual end of recording, so speech long
# after silence starts instantly.
POST_TURN_GRACE_SECONDS = 1.5


EMPHASIS_PATTERN = re.compile(r"\*\*(.+?)\*\*")

class _SerialWorker:
    """Daemon worker(s) starting jobs in strict submit order — with a fast
    lane.

    Fresh speech appends to the tail; a user's replay click means "play
    this NOW", so it jumps ahead of everything still queued (but never cuts
    into the job already running — one voice at a time stays inviolable).
    Replays keep click order among themselves: a jump lands behind earlier
    jumps, not in front of them, so CATCH UP replays a backlog in sequence.

    `workers` > 1 keeps the START order strict but lets jobs overlap — the
    synth stage uses this so a whole queued burst renders concurrently
    (the clip closest to playing always starts first). is_next() is only
    meaningful on a single-worker instance (the playback stage).
    """

    def __init__(self, name: str, workers: int = 1) -> None:
        self._jobs: deque[tuple[int, object, tuple, Future, bool]] = deque()
        self._cond = threading.Condition()
        self._current: int | None = None
        self._stopping = False
        for index in range(workers):
            thread_name = f"{name}-{index}" if workers > 1 else name
            threading.Thread(target=self._run, name=thread_name, daemon=True).start()

    def submit(self, seq, fn, *args, jump_queue: bool = False) -> Future:
        future: Future = Future()
        job = (seq, fn, args, future, jump_queue)
        with self._cond:
            if jump_queue:
                behind_earlier_jumps = 0
                for queued in self._jobs:
                    if not queued[4]:
                        break
                    behind_earlier_jumps += 1
                self._jobs.insert(behind_earlier_jumps, job)
            else:
                self._jobs.append(job)
            self._cond.notify()
        return future

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._jobs and not self._stopping:
                    self._cond.wait()
                if self._stopping:
                    return
                seq, fn, args, future, _ = self._jobs.popleft()
                self._current = seq
            try:
                if future.set_running_or_notify_cancel():
                    try:
                        future.set_result(fn(*args))
                    except BaseException as error:  # delivered via future.result()
                        future.set_exception(error)
            finally:
                with self._cond:
                    self._current = None

    def is_next(self, seq: int) -> bool:
        """Is `seq` the job this worker runs now, or the very next one?"""
        with self._cond:
            if self._current is not None:
                return self._current == seq
            return bool(self._jobs) and self._jobs[0][0] == seq

    def shutdown(self) -> None:
        with self._cond:
            self._stopping = True
            self._cond.notify()


# One playback worker = one utterance at a time; every speak in the whole
# system queues here, so two voices can never overlap. The synth workers
# run AHEAD of it: while clip N plays, the queued clips render concurrently
# (closest to playing starts first), so back-to-back announces play with no
# dead air between them.
_SYNTH_WORKERS = 2  # network-bound renders; 2 keeps a burst ahead of playback
_synth_worker = _SerialWorker("tts-synth", workers=_SYNTH_WORKERS)
_playback_worker = _SerialWorker("playback")

# Rendered clips by card + render options — replays and catch-ups play
# these bytes instead of paying Grok for the same audio again.
_audio_cache = audio_cache.AudioCache()

_queue_seq = itertools.count(1)

# An old message either plays or it doesn't — replays of the same bubble
# must not stack up in the queue when the user clicks repeatedly. New
# speech (fresh cards) may queue freely; a replay source may be in flight
# only once.
_pending_replays: set[int] = set()
_pending_lock = threading.Lock()


@dataclass(frozen=True)
class _PreparedSpeech:
    """What the synth stage hands the playback stage for one utterance."""

    voice: str
    language: str
    speed: float
    audio: tts.SynthesizedAudio | None = None  # rendered ahead (or cached)
    cached: bool = False  # bytes came from the cache — nothing was paid
    stream: bool = False  # render coupled to playback (live TTS at queue head)
    provider: providers.TTSProvider | None = None  # backend picked at synth time
    # audio=None with stream=False means the synth stage skipped rendering
    # (voice was muted then); the playback stage decides at its turn.


def submit(
    state: ListenerState,
    text: str,
    agent: str | None = None,
    card: bool = True,
    source_id: int = 0,
    role: str = "claude",
    speaker: str | None = None,
    voice_override: str | None = None,
) -> Future | None:
    """Queue an utterance for playback; resolves to the voice actually used.

    Requests carry only text — voice, speed and language are the daemon's
    business (see resolve_options), so a stale caller can't override what
    the user configured on the dashboard.

    The dashboard card is created HERE, at enqueue: the timeline shows when
    Claude decided to speak (creation order) — a reply composed before the
    user's last words shouldn't display as if it answered them. Delivery
    order lives in the card's status (queued → waiting → playing → played).
    card=False plays without a card — replaying an old bubble shouldn't
    duplicate it in the log (utterance_id 0 makes every update a no-op).
    Returns None when this source is already queued/playing (deduped).

    role="daemon" is for Noisy Studio speaking for ITSELF (setup
    confirmations) — same pipeline, but the card is never attributed to
    Claude. Internal call sites only; /speak never exposes it.
    """
    if source_id:
        with _pending_lock:
            if source_id in _pending_replays:
                return None
            _pending_replays.add(source_id)
    # Plain text on the card — no decorative quotes, no voice tag.
    # A replay (card=False) adopts the ORIGINAL card via source_id: its
    # status walks the normal chain (synthesizing → playing → played), so
    # an UNHEARD card becomes played once caught up on.
    # Every card records the voice it will be spoken with — the dashboard
    # renders that voice's portrait next to the bubble. The final say still
    # belongs to _prepare_audio (same resolution, later in time).
    card_voice = voice_override or (
        resolve_options(state, agent)[0] if role in ("claude", "daemon") else None
    )
    utterance_id = (
        state.create_utterance(
            role, "queued", text=text, agent=agent,
            speaker=speaker, voice=card_voice,
        )
        if card
        else source_id
    )
    # Which card the playback "belongs to" on the dashboard: a replay
    # (card=False) points back at the original bubble via source_id, so the
    # UI can offer STOP on it while it plays.
    canonical_id = source_id or utterance_id
    seq = next(_queue_seq)
    # A replay is the user's click: it takes the fast lane in BOTH stages
    # (synthesis too — its cache lookup must not sit behind pending renders).
    jump_queue = bool(source_id)
    synth_future = _synth_worker.submit(
        seq, _prepare_audio, state, text, agent, utterance_id, canonical_id, seq,
        voice_override,
        jump_queue=jump_queue,
    )
    future = _playback_worker.submit(
        seq, _play_prepared, state, text, agent, utterance_id, canonical_id, synth_future,
        jump_queue=jump_queue,
    )
    if source_id:
        future.add_done_callback(lambda _f: _discard_pending_replay(source_id))
    return future


def replay_in_flight(source_id: int) -> bool:
    """Whether this bubble already has a replay queued or playing — callers
    use it to skip BEFORE side effects like interrupt (repeated clicks must
    not stack replays, nor cut down the one already in flight)."""
    with _pending_lock:
        return source_id in _pending_replays


def _discard_pending_replay(source_id: int) -> None:
    with _pending_lock:
        _pending_replays.discard(source_id)


def shutdown() -> None:
    _synth_worker.shutdown()
    _playback_worker.shutdown()


def _emphasis_to_speech_tags(text: str) -> str:
    """Markdown **bold** becomes vocal emphasis for the TTS engine."""
    return EMPHASIS_PATTERN.sub(r"<loud>\1</loud>", text)


def resolve_options(
    state: ListenerState, agent: str | None = None
) -> tuple[str, str, float]:
    """Voice/language/speed for an utterance — decided by the daemon alone.

    The dashboard's per-agent character supplies voice and speed, the
    daemon's language setting supplies language, env vars are the fallback.
    Speak requests carry none of this by design; an agent that wants a
    different voice must change its character (the `change_voice` tool /
    POST /voice), which the user then sees on the dashboard.
    """
    character = state.character(agent)
    voice = character.get("voice") or os.environ.get(DEFAULT_VOICE_ENV_VAR, FALLBACK_VOICE)
    language = state.language or os.environ.get(DEFAULT_LANGUAGE_ENV_VAR) or "auto"
    speed = float(character.get("speed") or 1.0)
    return voice, language, speed


def _log(message: str) -> None:
    print(message, flush=True)


# Failures deterministic for this text/config — the same retry WILL fail.
FATAL_SPEECH_MARKERS = (
    "characters; the API accepts",  # text over the TTS limit
    "No xAI API key",  # nothing to speak with until the key is set
)

# xAI's voice endpoints fail transiently — dropped responses mid-body,
# momentary 5xx, stray 400 key rejections (issues #2/#3). Retry in code
# before ever showing the user an ERROR: the first retry is immediate
# (catches dropped connections), the second takes one breath (momentary
# upstream blips). Deterministic failures never retry.
SYNTH_RETRY_DELAYS_SECONDS = (0.0, 1.0)


def _is_fatal_speech_error(error: Exception) -> bool:
    return any(marker in str(error) for marker in FATAL_SPEECH_MARKERS)


async def _synthesize_with_retry(
    state: ListenerState,
    provider: providers.TTSProvider,
    speech_text: str,
    voice: str,
    language: str,
    speed: float,
) -> tts.SynthesizedAudio:
    for attempt, delay in enumerate(SYNTH_RETRY_DELAYS_SECONDS):
        try:
            return await provider.synthesize(speech_text, voice, language, speed)
        except Exception as error:
            if _is_fatal_speech_error(error):
                raise
            _log(f"[speak] transient synth error (attempt {attempt + 1}): {error}")
            state.add_event("speak_retry", str(error)[:160])
            if delay:
                await asyncio.sleep(delay)
    return await provider.synthesize(speech_text, voice, language, speed)


def _error_card_fields(error: Exception) -> dict:
    """Status + detail for a failed card: say WHY, and whether ↻ is worth it.

    Most speech failures are transient — a dropped websocket, a 5xx, xAI's
    intermittent key rejections — so the default wording invites a retry.
    Only failures that cannot succeed on a second attempt say so.
    """
    fields = {"detail": str(error)[:160]}
    if any(marker in str(error) for marker in FATAL_SPEECH_MARKERS):
        return fields | {"status": "error — retry won't help"}
    return fields | {"status": "error — likely transient, tap ↻ to retry"}


def _hold_for_user_turn(state: ListenerState, utterance_id: int) -> None:
    """Wait out an in-progress user utterance before taking the speaker.

    Speaking now would talk over the user AND lose their words (the mic is
    muted during playback). The daemon's VAD alone decides when their turn
    is over — no debounce, no timeout, no polling; see
    ListenerState.wait_for_user_silence for why this can't deadlock.
    """
    user_was_speaking = state.recording
    if user_was_speaking:
        detail = "user is speaking — holding playback"
        state.add_event("speak_wait", detail)
        state.update_utterance(utterance_id, status="queued — waiting for you to finish")
        _log(f"[speak] {detail}")
    held_since = time.monotonic()
    state.wait_for_user_silence(grace_s=POST_TURN_GRACE_SECONDS)
    if user_was_speaking:
        _log(f"[speak] user finished — held playback {time.monotonic() - held_since:.1f}s")


def _streaming_available(state: ListenerState, provider: providers.TTSProvider) -> bool:
    # Native playback supports streaming when the provider does.
    return provider.supports_streaming


def _tts_streaming(state: ListenerState, provider: providers.TTSProvider) -> bool:
    """Whether to stream TTS: env override wins, else the daemon's tts_mode."""
    if not _streaming_available(state, provider):
        return False
    if os.environ.get(TTS_MODE_ENV_VAR, "").lower() == "live":
        return True
    return state.tts_mode == "live"


def output_status(state: ListenerState) -> dict:
    """Describe the same playback decision the speech worker makes."""
    try:
        provider = providers.active_tts()
    except providers.TTSError:
        return {"speech_live_available": False, "speech_output_mode": "unavailable"}
    return {
        "speech_live_available": _streaming_available(state, provider),
        "speech_output_mode": "live" if _tts_streaming(state, provider) else "batch",
    }


def _next_to_play(seq: int) -> bool:
    return _playback_worker.is_next(seq)


def _cache_key(
    source_id: int, text: str, voice: str, language: str, speed: float, provider=None
) -> str | None:
    return audio_cache.key(source_id, text, voice, language, speed,
                           getattr(provider, "cache_identity", getattr(provider, "name", "grok")))


def _prepare_audio(
    state: ListenerState,
    text: str,
    agent: str | None,
    utterance_id: int,
    source_id: int,
    seq: int,
    voice_override: str | None = None,
) -> _PreparedSpeech:
    """Synth stage: produce audio bytes ahead of playback (synth worker).

    Touches neither the speaker nor the mic, so it is free to run while an
    earlier clip is still playing or while the user is talking. Everything
    playback-owned — turn-taking, echo muting, the STOP claim — happens in
    _play_prepared.
    """
    voice, language, speed = resolve_options(state, agent)
    provider = providers.active_tts()
    if voice_override:
        voice = voice_override  # a subagent's own persona (#22)
    if state.voice_muted or state.agent_muted(agent):
        # Deferred = costs nothing until played: render nothing while the
        # speaker is muted. _play_prepared parks the card (or renders at
        # its turn, should the user unmute in the meantime).
        return _PreparedSpeech(voice, language, speed, provider=provider)
    cached = _audio_cache.get_audio(_cache_key(source_id, text, voice, language, speed, provider))
    if cached is not None:
        audio = cached
        _mark_ready(state, utterance_id)
        return _PreparedSpeech(
            voice, language, speed, audio=audio, cached=True, provider=provider
        )
    if _tts_streaming(state, provider) and _next_to_play(seq):
        # Nothing plays before this one — stream it, audio starts fastest.
        # Clips queued BEHIND a playing one batch-render right here instead:
        # ready-to-play the instant the speaker frees, no dead air between.
        return _PreparedSpeech(voice, language, speed, stream=True, provider=provider)
    audio = _synthesize_now(
        state, provider, text, voice, language, speed, utterance_id, source_id
    )
    _mark_ready(state, utterance_id)
    return _PreparedSpeech(voice, language, speed, audio=audio, provider=provider)


def _mark_ready(state: ListenerState, utterance_id: int) -> None:
    """The card's audio is in hand — say so instead of leaving a stale
    "synthesizing" on a clip that is merely waiting for the speaker.
    Safe from the synth stage: the playback stage touches this card's
    status only after the synth future resolves, never concurrently."""
    state.update_utterance(utterance_id, status="ready — waiting for the speaker")


def _charge_synthesis(
    state: ListenerState,
    provider: providers.TTSProvider,
    text: str,
    utterance_id: int,
) -> None:
    cost = provider.cost_usd(len(text))
    state.add_cost("claude", cost)
    state.add_usage("tts_chars", len(text))
    state.update_utterance(utterance_id, cost_usd=cost)


def _synthesize_now(
    state: ListenerState,
    provider: providers.TTSProvider,
    text: str,
    voice: str,
    language: str,
    speed: float,
    utterance_id: int,
    source_id: int,
) -> tts.SynthesizedAudio:
    """One paid batch render, cached so this exact clip is never paid twice."""
    state.update_utterance(utterance_id, status=f"synthesizing ({provider.label})…")
    _charge_synthesis(state, provider, text, utterance_id)
    synth_started = time.monotonic()
    audio = asyncio.run(
        _synthesize_with_retry(
            state, provider, text, voice, language, speed
        )
    )
    state.set_latency("tts", (time.monotonic() - synth_started) * 1000)
    _audio_cache.put_audio(_cache_key(source_id, text, voice, language, speed, provider), audio)
    return audio


def _play_prepared(
    state: ListenerState,
    text: str,
    agent: str | None,
    utterance_id: int,
    source_id: int,
    synth_future: Future,
) -> str:
    """Playback stage: wait our turn on the speaker, then play.

    Runs on the single playback worker — one voice at a time; fresh speech
    plays in submit order, replays take the fast lane (see _SerialWorker).
    """
    try:
        prepared = synth_future.result()
    except Exception as error:
        _log(f"[speak] error: {error}")
        state.add_event("speak_error", str(error)[:200])
        state.update_utterance(utterance_id, **_error_card_fields(error))
        raise
    if state.voice_muted or state.agent_muted(agent):
        # Speaker muted globally or this conversation muted: park as
        # UNHEARD and return at once so agents' blocking speak never
        # hangs on it. Audio prefetched before the mute landed is
        # already cached — catching up on this card later is free.
        _log(f"[speak] unheard (voice muted): „{text[:60]}”")
        state.add_event("speak_unheard", f"„{text}”")
        reason = "voice muted" if state.voice_muted else "conversation muted"
        state.update_utterance(utterance_id, status=f"unheard — {reason}")
        return prepared.voice
    _hold_for_user_turn(state, utterance_id)

    # This is the real "the agent spoke aloud" moment — reset its
    # narration-nudge silence clock here, in-process (#16). The clock used to
    # be reset only in the HTTP /event handler, which this playback path never
    # crosses, so speaking never actually reset it. An unheard (muted)
    # utterance returned above without reaching here — nothing was said, so
    # the clock correctly keeps running.
    state.note_agent_spoke(agent)
    # The event log keeps the voice (diagnostics); the card does NOT — a
    # replay speaks with the CURRENT voice, so a voice tag on the bubble
    # would go stale the moment the user picks another one.
    state.add_event("speak", f"[{prepared.voice}] „{text}”")
    _log(f"[speak] playing [{prepared.voice}] ({len(text)} chars) „{text[:60]}”")
    playing_since = time.monotonic()
    # Claim the card the moment its playback is committed: the UI's
    # button must flip to STOP now, not when audio actually starts.
    state.set_playing_utterance_id(source_id)
    # Native speakers require echo muting during playback.
    try:
        audio = prepared.audio
        if audio is None and not prepared.stream:
            # The synth stage skipped this one (voice was muted then)
            # but it is audible now — render at our turn, exactly like
            # the pre-pipeline flow did.
            audio = _synthesize_now(
                state, prepared.provider or providers.active_tts(), text,
                prepared.voice, prepared.language, prepared.speed,
                utterance_id, source_id,
            )
        state.set_paused(True)
        state.set_claude_speaking(True, agent)
        if prepared.stream:
            asyncio.run(_stream_and_play(state, text, prepared, utterance_id, source_id))
        else:
            asyncio.run(_play_audio(state, audio, prepared.cached, utterance_id))
        time.sleep(ECHO_TAIL_SECONDS)  # let the room echo die before unmuting
    except Exception as error:
        _log(f"[speak] error: {error}")
        state.add_event("speak_error", str(error)[:200])
        state.update_utterance(utterance_id, **_error_card_fields(error))
        raise
    finally:
        state.set_playing_utterance_id(0)
        state.set_claude_speaking(False, agent)
        state.set_paused(False)
    played_seconds = time.monotonic() - playing_since
    _log(f"[speak] done in {played_seconds:.1f}s")
    state.add_event("speak_done", f"głos '{prepared.voice}'")
    # A mute, the stop button or a push-to-talk barge-in kills the player and
    # parks the card as unheard - the cut-short clip must not be relabeled
    # "played" here. The streaming path keeps writing progress after the
    # cut, so the mark alone was not enough: the interrupt is recorded and
    # re-applied once this thread is done (#61, #64).
    final_status = state.consume_interrupted(utterance_id)
    if final_status:
        state.update_utterance(utterance_id, status=final_status)
    elif not state.utterance_is_unheard(utterance_id):
        state.update_utterance(
            utterance_id, status="played", duration_s=round(played_seconds, 1)
        )
    return prepared.voice


async def _stream_and_play(
    state: ListenerState,
    text: str,
    prepared: _PreparedSpeech,
    utterance_id: int,
    source_id: int,
) -> None:
    """Live TTS: play audio as Grok generates it — and keep the bytes.

    A finished stream is a complete clip, so replays stay free in live
    mode too; a stream that errors out caches nothing (partial audio must
    never be replayed as the full message).
    """
    provider = prepared.provider or providers.active_tts()
    _charge_synthesis(state, provider, text, utterance_id)
    detail = f"streaming from {provider.label}"
    state.add_event("speak_audio", detail)
    state.update_utterance(
        utterance_id, status="playing through speakers…", detail=detail
    )
    chunks = bytearray()
    for attempt, delay in enumerate((*SYNTH_RETRY_DELAYS_SECONDS, None)):
        try:
            await provider.speak_streaming(
                text,
                prepared.voice,
                prepared.language,
                prepared.speed,
                on_first_audio=lambda seconds: state.set_latency("tts", seconds * 1000),
                on_audio_chunk=chunks.extend,
            )
            break
        except Exception as error:
            # Retry only while NOTHING has reached the speaker yet — once
            # audio played, a restarted stream would repeat it aloud.
            if chunks or delay is None or _is_fatal_speech_error(error):
                raise
            _log(f"[speak] transient stream error (attempt {attempt + 1}): {error}")
            state.add_event("speak_retry", str(error)[:160])
            if delay:
                await asyncio.sleep(delay)
    _audio_cache.put_audio(
        _cache_key(source_id, text, prepared.voice, prepared.language, prepared.speed, provider),
        tts.SynthesizedAudio(bytes(chunks), getattr(provider, "stream_content_type", "audio/mpeg"), 0.0),
    )


async def _play_audio(
    state: ListenerState,
    audio: tts.SynthesizedAudio,
    cached: bool,
    utterance_id: int,
) -> None:
    origin = "cache — no re-synthesis" if cached else "fresh synthesis"
    detail = f"{len(audio.audio) / 1024:.0f} kB audio from {origin}"
    state.add_event("speak_audio", detail)
    state.update_utterance(
        utterance_id, status="playing through speakers…", detail=detail
    )
    await playback.play(audio.audio, audio.content_type)
