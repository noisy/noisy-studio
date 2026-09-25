"""Shared, thread-safe state between the audio loop and the HTTP API."""

import threading
import time
import zlib
from collections import deque
from collections.abc import Callable
from dataclasses import replace, asdict, dataclass

from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.microphone_sample import MicrophoneSample
from noisy_studio.listener.history import ConversationHistory
from noisy_studio.harness.provider import Receipt, Speech
from noisy_studio.listener.character_traits import canonical_character_traits
from noisy_studio.listener.conversation_labels import UNNAMED_CONVERSATION, conversation_label
from noisy_studio.listener.vad import (
    DEFAULT_MIC_SENSITIVITY,
    DEFAULT_MAX_UTTERANCE_MS,
    MIN_MAX_UTTERANCE_MS,
    MAX_MAX_UTTERANCE_MS,
    MAX_MIC_SENSITIVITY,
    MIN_MIC_SENSITIVITY,
)

EVENT_LOG_SIZE = 300
# On the segmented dials values land on 20-point stops, so the defaults sit
# on a stop too (50 fell between ticks). Sensible starting persona rather than
# everything mid-scale: a little humour, fairly frank, fairly brief, moderately
# talkative — nothing maxed out.
DEFAULT_CHARACTER = {"humor": 20, "honesty": 60, "verbosity": 40, "talkative": 40}
DEFAULT_VOICE = "carina"
# Voices handed out exclusively - to agent tabs (#54) and named speakers
# (#22) alike - through the claim ledger. A name's hash only picks the
# starting point; the ledger guarantees no two get the same voice while the
# pool holds out.
VOICE_POOL = (
    "ara", "carina", "eve", "iris", "luna", "celeste", "ursa", "liora", "aurora",
    "altair", "atlas", "kepler", "rex", "cosmo", "helios", "leo", "sirius",
    "castor", "helix", "lumen", "lux", "naksh", "orion", "perseus", "rigel",
    "sal", "zagan", "zenith",
)


from noisy_studio.listener.identity import canonical_identity, fold_by_identity


def speaker_key(name: str) -> str:
    """Ledger key for a speaker or agent name: case-insensitive, trimmed.

    Viewers speak as their display name ("WootDragon") while the ledger
    once held them lowercased ("wootdragon"); a case-sensitive lookup then
    never found the entry and re-claimed a voice on every reload - the
    second mid-conversation voice change of 2026-09-13. Display casing is
    for reading aloud; identity is case-insensitive.
    """
    return str(name).strip().casefold()


def hash_pick(seed: str, pool: tuple[str, ...]) -> str:
    # crc32, not hash(): stable across daemon restarts (PYTHONHASHSEED).
    return pool[zlib.crc32(seed.encode()) % len(pool)]
DEFAULT_SPEED = 1.0
MIN_SPEED, MAX_SPEED = 0.7, 1.5
DEFAULT_END_SILENCE_MS = 2000
MIN_END_SILENCE_MS, MAX_END_SILENCE_MS = 0, 10000
# An agent with NO sign of life for this long is shown OFFLINE — never
# deleted (#11). The flip back to online is immediate on the next
# heartbeat, and a brief hiccup must not bounce a tab out of the active
# group (which would scramble its position).
#
# 30s was far too short and produced the "no listener" lie in live use
# (2026-09-05): the two signs of life are the drain heartbeat and the
# activity line, and BOTH go quiet during a single long operation - one
# lengthy tool call, a long think, or an agent speaking a paragraph. A
# 57-second utterance was stamped undelivered while its addressee was
# mid-sentence. With two independent signals a generous window is safe:
# an agent that has neither polled nor reported activity for three
# minutes really is gone.
AGENT_OFFLINE_AFTER_SECONDS = 180.0
DEFAULT_SMART_TURN = 0.0  # 0 = off (pure VAD); 0.5-0.9 = semantic endpointing
# Push-to-talk hold is a LEASE, not a latch: the UI renews it (~2×/s) while
# the button is physically held, so a crashed page or lost connection can
# never leave the daemon stuck recording. Structural safety, not a timer
# guessing at human behavior.
PTT_LEASE_SECONDS = 2.0
# Talkative-driven silence limits, interpolated between anchors; zero disables nudges.
TALKATIVE_NUDGE_ANCHORS = ((25, 600.0), (50, 300.0), (75, 120.0), (100, 75.0))
# Only nudge agents whose live activity moved recently.
NUDGE_ACTIVITY_FRESH_SECONDS = 30.0


@dataclass(frozen=True)
class Transcript:
    text: str
    timestamp: float
    utterance_id: int = 0
    # Which agent this speech was addressed TO — the agent active when the
    # utterance STARTED (#17). Switching tabs while a sentence is finishing
    # or transcribing must not reroute it. Empty = legacy/unstamped.
    addressee: str = ""
    delivery_state: str = "queued"


def user_turn_wait_seconds(
    recording: bool, lease_remaining: float, seconds_since_end: float, grace_s: float,
) -> float | None:
    """None waits for capture, a duration waits for lease/grace, zero may play."""
    if recording:
        return None
    if lease_remaining > 0:
        return lease_remaining
    return max(0.0, grace_s - seconds_since_end)


class ListenerState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Conversations as the harness contract sees them (keys, aliases,
        # listener lease, status). The daemon swaps in a persisted one at
        # boot; tests get an in-memory registry.
        self.conversations = ConversationRegistry()
        # Signals every change to the recording/paused/muted flags, so
        # waiters (the playback gate) block on a condition instead of polling.
        self._turn_cond = threading.Condition(self._lock)
        self._transcripts: list[Transcript] = []
        # Multi-agent: registered agents by name, and which one is active.
        # Transcripts are only delivered to the active agent (see drain).
        self._agents: dict[str, float] = {}  # name -> last-seen time
        self._agent_labels: dict[str, str] = {}  # name -> human label (rename title)
        # name -> when the agent last BECAME online (offline->online edge).
        # Orders the active tab group: new arrivals join on the right.
        self._agent_activated: dict[str, float] = {}
        # name -> user-pinned position (drag & drop). Within each tab group,
        # pinned agents come first in pinned order; unpinned follow in the
        # group's natural order.
        self._agent_manual_pos: dict[str, int] = {}
        # Narration nudges (#16): when the agent last spoke (speak/announce
        # SUBMITTED — intent counts, playback may lag) and when we last
        # nudged it, so one silence stretch gets exactly one nudge.
        self._agent_last_spoke: dict[str, float] = {}
        self._agent_last_nudge: dict[str, float] = {}
        # When we last LOGGED an idle-skip for a stretch, so the /logs view
        # gets one "waiting on user" line per stretch — NOT the nudge budget,
        # so an agent that resumes work mid-stretch still earns its nudge.
        self._agent_last_idle_log: dict[str, float] = {}
        self._active_agent: str | None = None
        self._paused = False  # transient echo-mute while Claude speaks
        self.microphone_sample = MicrophoneSample()
        self._active_input_device = ""  # what is actually open right now (#41)
        self._user_muted = False  # explicit mute from the dashboard
        self._voice_muted = False  # speaker-side mute: Claude's speech parks as UNHEARD
        # Per-conversation mute: these agents' speech parks as UNHEARD
        # while everyone else keeps talking (#per-tab-mute).
        self._muted_agents: set[str] = set()
        self._claude_speaking = False  # any agent playing audio right now
        self._speaking_agents: set[str] = set()  # which agents are speaking now
        self._recording = False
        self._mic_level = 0.0  # live mic RMS 0..1, for the dashboard oscilloscope
        self._activity: dict[str, dict] = {}  # agent -> current tool one-liner
        self._playing_utterance_id = 0  # which card is on the speakers right now
        # id -> reason for clips cut short by the user; the playback thread
        # consumes it when it finishes bookkeeping, so a cut clip can never
        # be relabelled "played" by the code that did not know it was cut.
        self._interrupted: dict[int, str] = {}
        self._latency_ms: dict = {"stt": None, "tts": None}  # last measured
        self._last_recording_end = float("-inf")  # monotonic time of last utterance end
        self._last_transcript_at = 0.0
        self._events: deque[dict] = deque(maxlen=EVENT_LOG_SIZE)
        self._event_seq = 0
        self._utterances = ConversationHistory()
        self._utterance_seq = 0
        self._session_cost_usd = {"user": 0.0, "claude": 0.0}
        # Volume behind the costs: audio seconds transcribed, chars spoken.
        self._usage = {"stt_seconds": 0.0, "tts_chars": 0}
        self._credits_usd: float | None = None
        self._mode = "live"
        self._tts_mode = "live"
        self._end_silence_ms = DEFAULT_END_SILENCE_MS
        self._max_utterance_ms = DEFAULT_MAX_UTTERANCE_MS
        self._mic_sensitivity = DEFAULT_MIC_SENSITIVITY
        self._diagnostic_checks: dict | None = None  # live xAI check results
        self._smart_turn = DEFAULT_SMART_TURN
        self._smart_turn_mode = "soft"
        # Global PTT hotkeys (#25): key NAMES from hotkey.KEYCODES, "" = off.
        # Global hotkeys (#104): {action: chord text}. The legacy ptt_*_key
        # views below read hold / toggle / scratch out of this map.
        self._hotkeys: dict[str, str] = {}
        # Scratch-my-words (#30 follow-up): set by the cancel hotkey or the
        # /abort-recording endpoint, consumed by the audio loop.
        self._recording_abort_requested = False
        # Graceful shutdown (#35): epoch when the daemon may exit; 0 = no
        # shutdown scheduled. The countdown lives here so /status can render
        # the dashboard banner.
        self._shutdown_at = 0.0
        self._detection_mode = "auto"  # auto (VAD) | ptt (push-to-talk)
        self._ptt_last_hold = float("-inf")  # monotonic time of last lease renewal
        self._last_ptt_end = float("-inf")
        self._language = ""  # "" = auto-detect
        self._input_device = ""  # "" = system default microphone
        # Character is now PER AGENT: {agent_name: character_dict}. The special
        # key "" holds the character used in single-agent mode (no agents
        # registered) and as the template for a newly seen agent.
        self._characters: dict[str, dict] = {"": self._default_character()}
        # Voice CLAIMS for named speakers: {speaker_name: voice}. A claim is
        # exclusive - two speakers sharing one voice are indistinguishable by
        # ear, which is the whole point of handing them different ones.
        self._voice_claims: dict[str, str] = {}
        self._voice_claims_dirty = False
        # Bubble color per named speaker: chat platforms get their brand
        # color (twitch=purple, youtube=red), everything else the default
        # guest green. A fixed palette, not free RGB - four states the UI
        # styles deliberately beat a color picker nobody calibrates.
        self._speaker_colors: dict[str, str] = {}
        self._speaker_labels: dict[str, str] = {}

    @staticmethod
    def _default_character() -> dict:
        return dict(DEFAULT_CHARACTER) | {"voice": DEFAULT_VOICE, "speed": DEFAULT_SPEED}

    def _character_bucket(self, agent: str | None) -> str:
        # No agent given → use the active agent's bucket, else the shared one.
        key = agent if agent is not None else (self._active_agent or "")
        if key not in self._characters:
            # Seed a new agent from the shared/default character - but NOT
            # its voice: a straight copy gave every new conversation the same
            # voice and face (#54). The voice comes from the same exclusive
            # ledger named speakers use, so tabs are told apart by ear.
            seeded = dict(self._characters[""])
            if key:
                seeded["voice"] = self._claim_voice_locked(key, VOICE_POOL, hash_pick)
            self._characters[key] = seeded
        return key

    def character(self, agent: str | None = None) -> dict:
        with self._lock:
            return dict(self._characters[self._character_bucket(agent)])

    def set_character(self, values: dict, agent: str | None = None) -> dict:
        values = canonical_character_traits(values)
        with self._lock:
            key = self._character_bucket(agent)
            char = self._characters[key]
            for trait in DEFAULT_CHARACTER:
                if trait in values:
                    char[trait] = max(0, min(100, int(values[trait])))
            voice = values.get("voice")
            if isinstance(voice, str) and voice.isalpha():
                char["voice"] = voice.lower()
                if key:
                    # The ledger is the record of who sounds like what; a
                    # chosen voice must be claimed there too, or the voice
                    # claimed at seeding stays marked taken while the tab
                    # actually uses another (#54).
                    if self._voice_claims.get(speaker_key(key)) != char["voice"]:
                        self._voice_claims[speaker_key(key)] = char["voice"]
                        self._voice_claims_dirty = True
            if "speed" in values:
                try:
                    char["speed"] = max(MIN_SPEED, min(MAX_SPEED, float(values["speed"])))
                except (TypeError, ValueError):
                    pass
            return dict(char)

    def rehome_default_voice_copies(self, pool: tuple[str, ...] = VOICE_POOL) -> list[str]:
        """Move agent tabs that merely COPIED the shared default voice onto
        exclusive voices (#54 for tabs created before the fix). The shared
        bucket keeps the default. Returns the agents that were moved. Runs
        once at boot after characters are loaded; idempotent afterwards."""
        moved = []
        with self._lock:
            default_voice = self._characters.get("", {}).get("voice", DEFAULT_VOICE)
            present = set(self.conversations.visible_keys()) | set(self._agents)
            seen: set[str] = set()
            for key, char in self._characters.items():
                if not key:
                    continue
                voice = char.get("voice", "")
                # Two reasons to move: a plain copy of the shared default, or
                # a duplicate among the tabs that are actually on the strip.
                duplicate = key in present and voice in seen
                if voice != default_voice and not duplicate:
                    if key in present:
                        seen.add(voice)
                    continue
                self._voice_claims.pop(speaker_key(key), None)  # re-claim from the free set
                free = tuple(v for v in pool if v != default_voice and v not in seen)
                new_voice = self._claim_voice_locked(key, free or pool, hash_pick)
                if new_voice != voice:
                    char["voice"] = new_voice
                    moved.append(key)
                if key in present:
                    seen.add(new_voice)
        return moved

    def all_characters(self) -> dict:
        with self._lock:
            return {k: dict(v) for k, v in self._characters.items()}

    # --- speaker bubble style (color + free title) -------------------------
    #
    # Color stays a FIXED palette - four looks the UI styles deliberately:
    #   normal  the main agent's violet bubble (e.g. the chat moderator)
    #   green   the guest default (plain subagent personas)
    #   purple  Twitch chat viewers
    #   red     YouTube chat viewers
    # "default" is the CLEAR operation, not a fifth look: it drops the entry
    # and the speaker falls back to guest green.
    #
    # The TITLE is free text ("YouTube · someRandomGuy", "Luna - chat agent");
    # an empty label clears it and the UI falls back to "<SPEAKER> · CLAUDE".

    SPEAKER_PALETTE = ("default", "normal", "green", "purple", "red")

    def speaker_colors(self) -> dict[str, str]:
        with self._lock:
            return dict(self._speaker_colors)

    def speaker_labels(self) -> dict[str, str]:
        with self._lock:
            return dict(self._speaker_labels)

    def set_speaker_style(
        self, speaker: str, color: str | None = None, label: str | None = None
    ) -> bool:
        """Set a named speaker's bubble color (palette) and/or free title."""
        speaker = (speaker or "").strip()
        if not speaker:
            return False
        if color is not None and color not in self.SPEAKER_PALETTE:
            return False
        with self._lock:
            if color == "default":
                self._speaker_colors.pop(speaker, None)
            elif color is not None:
                self._speaker_colors[speaker] = color
            if label is not None:
                label = label.strip()[:80]
                if label:
                    self._speaker_labels[speaker] = label
                else:
                    self._speaker_labels.pop(speaker, None)
        return True

    def set_speaker_color(self, speaker: str, color: str) -> bool:
        return self.set_speaker_style(speaker, color=color)

    def load_speaker_styles(self, data: dict) -> None:
        # Two formats on disk: the original flat {speaker: color} and the
        # current {"colors": {...}, "labels": {...}}.
        colors = data.get("colors", data) if isinstance(data, dict) else {}
        labels = data.get("labels", {}) if isinstance(data, dict) else {}
        with self._lock:
            self._speaker_colors = {
                str(k): str(v) for k, v in colors.items()
                if str(v) in self.SPEAKER_PALETTE
            }
            self._speaker_labels = {
                str(k): str(v)[:80] for k, v in labels.items() if str(v).strip()
            }

    # Back-compat alias (older callers/tests).
    def load_speaker_colors(self, colors: dict) -> None:
        self.load_speaker_styles(colors)

    # --- voice claims ----------------------------------------------------
    #
    # A named speaker (subagent persona, chat viewer) must keep ONE voice for
    # its whole life, and no two speakers may share one. Hashing the name
    # alone gives the first property but not the second: over a pool of N
    # voices, two of ~sqrt(N) speakers collide about half the time. So the
    # hash only picks a STARTING POINT and the claim ledger decides.

    def _taken_voices(self) -> set[str]:
        """Voices that are spoken for - claimed, or in use by a LIVE agent.

        Liveness matters: character buckets outlive the sessions that made
        them, and a session that ended months ago must not go on denying its
        voice to someone here now. Only claims are permanent; an agent holds
        a voice for exactly as long as it is around to speak with it. The
        shared "" bucket always counts - that is the voice in use right now.
        """
        now = time.time()
        live = {""} | {
            name
            for name, seen in self._agents.items()
            if now - seen <= AGENT_OFFLINE_AFTER_SECONDS
        }
        # Named speakers (viewers, subagent personas) hold their claim for
        # good - they come back after weeks and must sound the same. An
        # AGENT TAB's claim counts only while the tab is live: a dormant or
        # closed session must not squat on a voice (#54 made tab voices
        # ledger claims too).
        # A tab that is on the strip (visible in the registry) holds its
        # voice even between heartbeats - at boot nobody has polled yet, and
        # two restored tabs must not be handed the same voice. Only a tab the
        # user closed, or a session long gone from the registry, lets go.
        present = live | set(self.conversations.visible_keys())
        agents = {speaker_key(k) for k in self._characters} | {speaker_key(k) for k in self._agents}
        present_keys = {speaker_key(k) for k in present}
        taken = {
            voice for name, voice in self._voice_claims.items()
            if name not in agents or name in present_keys
        }
        taken.update(
            char.get("voice", "")
            for name, char in self._characters.items()
            if name in live
        )
        return taken

    def take_voice_claims_dirty(self) -> bool:
        """True once after the ledger changes - lets the caller persist it."""
        with self._lock:
            dirty, self._voice_claims_dirty = self._voice_claims_dirty, False
            return dirty

    def voice_claims(self) -> dict[str, str]:
        with self._lock:
            return dict(self._voice_claims)

    def load_voice_claims(self, claims: dict, pool: tuple[str, ...] = VOICE_POOL) -> None:
        """Restore claims from disk, keeping the ledger self-consistent.

        A name whose voice duplicates an earlier entry used to be DROPPED,
        so it re-claimed from scratch at its next speak and drew whatever was
        free - a regular's voice changed mid-stream (2026-09-13). Duplicates
        are now RE-HOMED onto a free pool voice, deterministically, so the
        entry survives the reload; only once the pool is exhausted does a
        duplicate keep its (shared) voice. The check is case-insensitive.
        """
        with self._lock:
            # Fold first (#107): a session that appears under both its id
            # and its transcript path is ONE speaker, and leaving the twin
            # in place is what made a duplicate - and therefore a re-home -
            # inevitable on every single load.
            claims, collapsed = fold_by_identity(
                {k: v for k, v in claims.items() if isinstance(v, str)}
            )
            if collapsed:
                self._voice_claims_dirty = True
            seen: set[str] = set()
            for raw_name, voice in claims.items():
                if not (isinstance(voice, str) and voice.isalpha()):
                    continue
                name = speaker_key(canonical_identity(raw_name))
                if name in self._voice_claims:
                    continue  # a case variant of a name already restored: first one wins
                voice = voice.lower()
                if voice in seen:
                    free = tuple(v for v in pool if v not in seen)
                    if free:
                        voice = hash_pick(str(name), free)
                        self._voice_claims_dirty = True
                self._voice_claims[name] = voice
                seen.add(voice)

    def claim_voice(self, name: str, pool: tuple[str, ...], hash_pick) -> str:
        """The voice for `name`, claiming a free one on first sight.

        Stable: a name already in the ledger always gets the same answer.
        Exclusive while the pool holds out; once every voice is claimed the
        ledger stops being able to help and we fall back to the plain hash,
        because a duplicate voice still beats no voice at all.
        """
        with self._lock:
            return self._claim_voice_locked(name, pool, hash_pick)

    def _claim_voice_locked(self, name: str, pool: tuple[str, ...], hash_pick) -> str:
        key = speaker_key(name)
        claimed = self._voice_claims.get(key)
        if claimed:
            return claimed
        free = [v for v in pool if v not in self._taken_voices()]
        voice = hash_pick(key, tuple(free)) if free else hash_pick(key, pool)
        self._voice_claims[key] = voice
        self._voice_claims_dirty = True
        return voice

    def set_voice_claim(self, name: str, voice: str, pool: tuple[str, ...]) -> str:
        """Move `name` onto `voice` by request. Returns the outcome.

        "ok" | "unknown" (not a voice we can hand out) | "taken" (someone
        else holds it - first come, first served, no stealing).
        """
        voice = str(voice).strip().lower()
        name = speaker_key(name)
        with self._lock:
            if voice not in pool:
                return "unknown"
            if self._voice_claims.get(name) == voice:
                return "ok"
            if voice in self._taken_voices():
                return "taken"
            self._voice_claims[name] = voice
            self._voice_claims_dirty = True
            return "ok"

    @property
    def mode(self) -> str:
        with self._lock:
            return self._mode

    def set_mode(self, mode: str) -> None:
        with self._lock:
            self._mode = mode

    @property
    def tts_mode(self) -> str:
        with self._lock:
            return self._tts_mode

    def set_tts_mode(self, mode: str) -> None:
        with self._lock:
            self._tts_mode = mode

    @property
    def max_utterance_ms(self) -> int:
        with self._lock:
            return self._max_utterance_ms

    def set_max_utterance_ms(self, value: int) -> int:
        with self._lock:
            self._max_utterance_ms = max(
                MIN_MAX_UTTERANCE_MS, min(MAX_MAX_UTTERANCE_MS, int(value))
            )
            return self._max_utterance_ms

    @property
    def end_silence_ms(self) -> int:
        with self._lock:
            return self._end_silence_ms

    def set_end_silence_ms(self, value: int) -> int:
        with self._lock:
            self._end_silence_ms = max(
                MIN_END_SILENCE_MS, min(MAX_END_SILENCE_MS, int(value))
            )
            return self._end_silence_ms

    def set_diagnostic_checks(self, checks: dict | None) -> None:
        """Live per-endpoint xAI check results (partial while running) —
        the dashboard polls these to show verdicts landing one by one."""
        with self._lock:
            self._diagnostic_checks = (
                {name: dict(result) for name, result in checks.items()}
                if checks is not None
                else None
            )

    @property
    def diagnostic_checks(self) -> dict | None:
        with self._lock:
            if self._diagnostic_checks is None:
                return None
            return {name: dict(r) for name, r in self._diagnostic_checks.items()}

    @property
    def mic_sensitivity(self) -> int:
        with self._lock:
            return self._mic_sensitivity

    def set_mic_sensitivity(self, value: int) -> int:
        with self._lock:
            self._mic_sensitivity = max(
                MIN_MIC_SENSITIVITY, min(MAX_MIC_SENSITIVITY, int(value))
            )
            return self._mic_sensitivity

    @property
    def smart_turn(self) -> float:
        with self._lock:
            return self._smart_turn

    def set_smart_turn(self, value: float) -> float:
        with self._lock:
            self._smart_turn = max(0.0, min(1.0, float(value)))
            return self._smart_turn

    @property
    def language(self) -> str:
        with self._lock:
            return self._language

    def set_language(self, language: str) -> str:
        with self._lock:
            self._language = language
            return self._language

    @property
    def input_device(self) -> str:
        with self._lock:
            return self._input_device

    def set_input_device(self, name: str) -> str:
        """The user's PREFERENCE (persisted). What is actually open lives in
        active_input_device - a failed open must never rewrite the pick (#41).
        Old browser selections migrate to the native system microphone."""
        with self._lock:
            name = str(name)
            if name == "browser":
                name = ""
            self._input_device = name
            return self._input_device

    @property
    def active_input_device(self) -> str:
        with self._lock:
            return self._active_input_device

    def set_active_input_device(self, name: str) -> None:
        with self._lock:
            self._active_input_device = str(name)

    @property
    def detection_mode(self) -> str:
        with self._lock:
            return self._detection_mode

    def set_detection_mode(self, mode: str) -> str:
        with self._lock:
            if mode in ("auto", "ptt"):
                self._detection_mode = mode
            return self._detection_mode

    def refresh_ptt_hold(self) -> None:
        with self._lock:
            self._ptt_last_hold = time.monotonic()
            self._turn_cond.notify_all()

    def release_ptt(self) -> None:
        with self._lock:
            self._last_ptt_end = max(
                self._last_ptt_end,
                min(time.monotonic(), self._ptt_last_hold + PTT_LEASE_SECONDS),
            )
            self._ptt_last_hold = float("-inf")
            self._turn_cond.notify_all()

    @property
    def ptt_held(self) -> bool:
        with self._lock:
            return time.monotonic() - self._ptt_last_hold < PTT_LEASE_SECONDS

    @property
    def smart_turn_mode(self) -> str:
        with self._lock:
            return self._smart_turn_mode

    @property
    def shutdown_at(self) -> float:
        with self._lock:
            return self._shutdown_at

    def schedule_shutdown(self, delay_seconds: float) -> float:
        with self._lock:
            self._shutdown_at = time.time() + max(0.0, delay_seconds)
            return self._shutdown_at

    def postpone_shutdown(self, seconds: float) -> float:
        """Push a scheduled shutdown further out; no-op when none is set."""
        with self._lock:
            if self._shutdown_at:
                self._shutdown_at += max(0.0, seconds)
            return self._shutdown_at

    def cancel_shutdown(self) -> None:
        with self._lock:
            self._shutdown_at = 0.0

    @property
    def hotkeys(self) -> dict[str, str]:
        with self._lock:
            return dict(self._hotkeys)

    def set_hotkeys(self, patch: dict[str, str]) -> dict[str, str]:
        """Merge {action: chord text}. "" is kept as an explicit OFF: the user
        cleared it on purpose, so a default must not refill it at boot."""
        with self._lock:
            for action, text in patch.items():
                self._hotkeys[action] = str(text or "")
            return dict(self._hotkeys)

    def fill_default_hotkeys(self, defaults: dict[str, str]) -> None:
        """Actions the user never touched get the default (boot only)."""
        with self._lock:
            for action, chord in defaults.items():
                self._hotkeys.setdefault(action, chord)

    @property
    def ptt_hold_key(self) -> str:
        with self._lock:
            return self._hotkeys.get("hold", "")

    @property
    def ptt_toggle_key(self) -> str:
        with self._lock:
            return self._hotkeys.get("toggle", "")

    @property
    def ptt_cancel_key(self) -> str:
        with self._lock:
            return self._hotkeys.get("scratch", "")

    def set_ptt_keys(
        self, hold: str | None, toggle: str | None, cancel: str | None = None
    ) -> tuple[str, str, str]:
        patch = {}
        if hold is not None:
            patch["hold"] = hold
        if toggle is not None:
            patch["toggle"] = toggle
        if cancel is not None:
            patch["scratch"] = cancel
        self.set_hotkeys(patch)
        return self.ptt_hold_key, self.ptt_toggle_key, self.ptt_cancel_key

    def talk_to_tab(self, index: int) -> bool:
        """The tabN hotkey: hand the mic to the index-th visible conversation
        (1-based, left to right on the strip). False when there is no such tab."""
        registry = getattr(self, "conversations", None)
        keys = registry.visible_keys() if registry is not None else []
        if index < 1 or index > len(keys):
            return False
        return self.set_active_agent(keys[index - 1]) == keys[index - 1]

    def request_recording_abort(self) -> None:
        with self._lock:
            self._recording_abort_requested = True

    def consume_recording_abort(self) -> bool:
        with self._lock:
            was = self._recording_abort_requested
            self._recording_abort_requested = False
            return was

    def set_smart_turn_mode(self, mode: str) -> str:
        with self._lock:
            if mode in ("soft", "hard"):
                self._smart_turn_mode = mode
            return self._smart_turn_mode

    def add_cost(self, role: str, usd: float) -> None:
        with self._lock:
            self._session_cost_usd[role] = self._session_cost_usd.get(role, 0.0) + usd

    @property
    def session_cost_usd(self) -> dict:
        with self._lock:
            return dict(self._session_cost_usd)

    def add_usage(self, kind: str, amount: float) -> None:
        with self._lock:
            self._usage[kind] = self._usage.get(kind, 0) + amount

    @property
    def usage(self) -> dict:
        with self._lock:
            return dict(self._usage)

    @property
    def credits_usd(self) -> float | None:
        with self._lock:
            return self._credits_usd

    def set_credits_usd(self, credits: float | None) -> None:
        with self._lock:
            self._credits_usd = credits

    def add_event(self, kind: str, detail: str = "") -> None:
        with self._lock:
            self._add_event_locked(kind, detail)

    def _add_event_locked(self, kind: str, detail: str) -> None:
        self._event_seq += 1
        self._events.append(
            {"seq": self._event_seq, "ts": time.time(), "kind": kind, "detail": detail}
        )

    def events_since(self, since_seq: int) -> list[dict]:
        with self._lock:
            return [e for e in self._events if e["seq"] > since_seq]

    def create_utterance(
        self,
        role: str,
        status: str,
        text: str = "",
        agent: str | None = None,
        speaker: str | None = None,
        voice: str | None = None,
    ) -> int:
        with self._lock:
            self._utterance_seq += 1
            self._utterances.append(
                {
                    "id": self._utterance_seq,
                    "role": role,
                    "status": status,
                    "text": text,
                    "detail": "",
                    "cost_usd": 0.0,
                    # Which agent this utterance belongs to. Claude's speech
                    # passes its own agent explicitly (it may no longer be the
                    # active one by the time it speaks); user speech defaults
                    # to the active agent it was delivered to.
                    "agent": agent if agent is not None else self._active_agent,
                    # #22: a subagent's speech stays in the parent conversation
                    # but carries its own persona (name shown in the header +
                    # the voice whose portrait the bubble renders).
                    "speaker": speaker or "",
                    "voice": voice or "",
                    "started_at": time.time(),
                    "updated_at": time.time(),
                    # When the message ENTERED the conversation, iMessage
                    # style: Claude's (and system rows') counts on arrival;
                    # the user's counts when their utterance is finished
                    # (0 until then — still in the composer).
                    "committed_at": 0.0 if role == "user" else time.time(),
                }
            )
            return self._utterance_seq

    def update_transcription_partial(self, utterance_id: int, text: str) -> None:
        """A late provider callback must not reopen a completed or cancelled turn."""
        with self._lock:
            for utterance in self._utterances:
                if utterance["id"] == utterance_id:
                    if str(utterance.get("status", "")).startswith(("recording", "transcribing")):
                        self._update_utterance_locked(utterance_id, text=text, status="transcribing (live)…")
                    return

    def update_utterance(self, utterance_id: int, **fields: str) -> None:
        with self._lock:
            self._update_utterance_locked(utterance_id, **fields)

    def _update_utterance_locked(self, utterance_id: int, **fields: str) -> None:
        for utterance in self._utterances:
            if utterance["id"] == utterance_id:
                utterance.update(fields)
                utterance["updated_at"] = time.time()
                return

    def latest_utterance_id(self, role: str, agent: str | None = None) -> int:
        with self._lock:
            for utterance in reversed(self._utterances):
                if utterance["role"] == role and (
                    agent is None or utterance.get("agent") == agent
                ):
                    return utterance["id"]
            return 0

    def snapshot_utterances(self) -> list[dict]:
        with self._lock:
            return [dict(u) for u in self._utterances]

    def snapshot_history(self) -> dict:
        with self._lock:
            return self._utterances.snapshot(self._utterance_seq)

    def history_trimmed(self) -> dict[str, int]:
        with self._lock:
            return dict(self._utterances.trimmed)

    def load_history(self, saved: list | dict) -> None:
        if isinstance(saved, list):
            self.load_utterances(saved)
            return
        if not isinstance(saved, dict) or saved.get("version") != 2:
            return
        rows = list(saved.get("system", []))
        for cards in saved.get("conversations", {}).values():
            rows.extend(cards)
        self.load_utterances(sorted(rows, key=lambda row: row.get("id", 0)))
        with self._lock:
            self._utterance_seq = max(self._utterance_seq, int(saved.get("sequence", 0)))
            for agent, count in saved.get("trimmed", {}).items():
                self._utterances.trimmed[agent] = self._utterances.trimmed.get(agent, 0) + int(count)

    def snapshot_transcripts(self) -> list[dict]:
        """The transcripts still waiting for an agent, for persistence (#76)."""
        with self._lock:
            return [asdict(t) for t in self._transcripts]

    def load_transcripts(self, items: list[dict]) -> int:
        """Restore transcripts a previous daemon run had not delivered yet.

        Call AFTER load_utterances: the cards these belong to were coerced to
        'dropped — daemon restart' there, and here they go back to awaiting
        pickup, because the new process CAN deliver them. Returns how many
        were restored.
        """
        restored = 0
        with self._lock:
            for item in items:
                try:
                    transcript = Transcript(
                        text=str(item["text"]),
                        timestamp=float(item.get("timestamp", 0.0)),
                        utterance_id=int(item.get("utterance_id", 0)),
                        addressee=str(item.get("addressee", "") or ""),
                        delivery_state=str(item.get("delivery_state", "queued")),
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                self._transcripts.append(transcript)
                restored += 1
                for utterance in self._utterances:
                    if utterance.get("id") == transcript.utterance_id and utterance.get("role") == "user":
                        utterance["status"] = (
                            "delivery unknown" if transcript.delivery_state == "unknown" else
                            "delivery uncertain — not retried" if transcript.delivery_state in ("sent", "accepted", "uncertain")
                            else "ready — awaiting pickup"
                        )
            if restored:
                self._add_event_locked("restored", f"{restored} waiting message(s) survived the restart")
        return restored

    def load_utterances(self, items: list[dict]) -> None:
        """Restore history saved by a previous daemon run.

        In-flight statuses are coerced to terminal ones — their work died
        with the old process: a half-recorded user utterance is dropped
        (hidden as noise), Claude speech that never played becomes UNHEARD
        (still replayable via catch-up).
        """
        with self._lock:
            for item in items:
                utterance = dict(item)
                status = str(utterance.get("status", "")).lower()
                role = utterance.get("role")
                if role == "user" and any(
                    k in status for k in ("recording", "transcribing", "ready")
                ):
                    # "ready" too: the transcript queue is in-memory, so an
                    # awaiting-pickup card can never be delivered by the new
                    # process — without this it shows AWAITING CLAUDE forever.
                    utterance["status"] = "dropped — daemon restart"
                if role in ("claude", "daemon") and any(
                    k in status
                    for k in ("queued", "synthesizing", "ready", "playing", "waiting")
                ):
                    utterance["status"] = "unheard — daemon restarted"
                self._utterances.append(utterance)
                self._utterance_seq = max(self._utterance_seq, int(utterance.get("id", 0)))

    def utterances(self, agent: str | None = None) -> list[dict]:
        with self._lock:
            items = [dict(u) for u in self._utterances]
            for item in items:
                label = self._agent_labels.get(item.get("agent"))
                if label:
                    item["agent_label"] = label
        if agent is not None:
            items = [u for u in items if u.get("agent") == agent]
        return items

    def add_transcript(self, text: str, utterance_id: int = 0) -> None:
        with self._lock:
            now = time.time()
            # Address the transcript to the agent stamped on its utterance
            # card — that card was created at RECORDING START, so this is
            # "who the user started talking to" (#17), not whoever's tab is
            # active by the time transcription finishes.
            addressee = ""
            for utterance in self._utterances:
                if utterance["id"] == utterance_id:
                    addressee = str(utterance.get("agent") or "")
                    break
            if not addressee:
                addressee = self._active_agent or ""
            self._transcripts.append(
                Transcript(
                    text=text,
                    timestamp=now,
                    utterance_id=utterance_id,
                    addressee=addressee,
                )
            )
            self._last_transcript_at = now
            self._add_event_locked("transcript", text)
            # Speaking into a dead tab must be LOUD, not a silent queue: if
            # the addressee's session has stopped draining (offline), say so
            # on the card. The transcript itself stays queued — a session
            # that reconnects still receives it and the card flips to
            # delivered (the invariant: the reply appears where the question
            # was asked, or the user is told immediately that it cannot).
            addressee_online = True
            if addressee:
                addressee_online = self._agent_alive_locked(addressee, now)
            status = (
                "ready — awaiting pickup"
                if addressee_online
                else "undelivered — no listener on this tab (session offline)"
            )
            if not addressee_online:
                self._add_event_locked(
                    "no_listener",
                    f"utterance {utterance_id} addressed to an offline session",
                )
            self._update_utterance_locked(
                utterance_id,
                status=status,
                text=text,
                committed_at=now,
            )

        # Provider calls may perform I/O. Never hold the audio/state lock across them.
        self.submit_speech(Speech(utterance_id, addressee, text, now))

    def submit_speech(self, speech: Speech) -> Receipt:
        receipt = self.conversations.providers.submit(speech)
        self.record_delivery(speech, receipt)
        return receipt

    def record_delivery(self, speech: Speech, receipt: Receipt) -> None:
        if receipt.conversation != speech.conversation or receipt.utterance_id != speech.utterance_id:
            raise ValueError("provider receipt does not match the submitted utterance")
        if not self.conversations.providers.for_conversation(speech.conversation):
            return
        with self._lock:
            if receipt.state != "confirmed" and any(
                u.get("id") == speech.utterance_id and u.get("delivery_state") == "confirmed"
                for u in self._utterances
            ):
                return  # An acknowledgement can beat completion of the socket write.
            self._transcripts = [replace(t, delivery_state=receipt.state) if (
                t.utterance_id == speech.utterance_id and t.addressee == speech.conversation
                and t.timestamp == speech.created_at
            ) else t for t in self._transcripts]
            if receipt.state == "queued":
                return
            # Only a confirmed receipt retires pending speech. Sent/accepted
            # describe weaker observations and must remain distinguishable.
            if receipt.state in ("confirmed", "cancelled"):
                self._transcripts = [t for t in self._transcripts if not (
                    t.utterance_id == speech.utterance_id and t.addressee == speech.conversation
                    and t.timestamp == speech.created_at
                )]
            self._update_utterance_locked(
                speech.utterance_id, delivery_state=receipt.state,
                delivery_detail=receipt.detail,
                status={"unknown": "delivery unknown", "sent": "sent — unconfirmed", "uncertain": "delivery uncertain — not retried",
                        "unavailable": "unavailable — action needed", "rejected": "delivery rejected",
                        "accepted": "accepted — awaiting confirmation", "confirmed": "delivery confirmed", "cancelled": "cancelled by you"}[receipt.state],
            )

    def restore_delivery(self, speech: Speech, receipt: Receipt) -> None:
        """Recover journaled speech even when the periodic history save lagged."""
        with self._lock:
            if not any(t.utterance_id == speech.utterance_id and t.addressee == speech.conversation
                       and t.timestamp == speech.created_at for t in self._transcripts):
                self._transcripts.append(Transcript(speech.text, speech.created_at, speech.utterance_id,
                                                    speech.conversation, receipt.state))
            if speech.utterance_id and not any(u['id'] == speech.utterance_id for u in self._utterances):
                self._utterances.append({
                    'id': speech.utterance_id, 'role': 'user', 'status': 'ready — awaiting pickup',
                    'text': speech.text, 'detail': '', 'cost_usd': 0.0, 'agent': speech.conversation,
                    'speaker': '', 'voice': '', 'started_at': speech.created_at,
                    'updated_at': time.time(), 'committed_at': speech.created_at,
                })
                self._utterance_seq = max(self._utterance_seq, speech.utterance_id)
        self.record_delivery(speech, receipt)

    def reserve_speech(self, speeches: list[Speech]) -> list[Speech]:
        """Atomically protect pending speech from cancellation once a send starts."""
        reserved = []
        with self._lock:
            for speech in speeches:
                conversation = self.conversations.get(speech.conversation)
                if conversation and (conversation.hidden or conversation.ended):
                    continue
                for i, transcript in enumerate(self._transcripts):
                    if (transcript.utterance_id == speech.utterance_id
                            and transcript.addressee == speech.conversation
                            and transcript.timestamp == speech.created_at
                            and transcript.delivery_state in ("queued", "unavailable")):
                        self._transcripts[i] = replace(transcript, delivery_state="uncertain")
                        reserved.append(speech)
                        break
        return reserved

    def mark_utterance_cancelled(self, utterance_id: int) -> None:
        """Scratch-my-words: the in-progress card ends as 'cancelled by
        you' - same wording as a recall, it IS the same user intent."""
        with self._lock:
            self._add_event_locked("cancelled", f"utterance {utterance_id} scratched")
            self._update_utterance_locked(utterance_id, status="cancelled by you")

    def cancel_transcript(self, utterance_id: int) -> bool:
        """Drop a queued transcript before it reaches Claude.

        Only possible while it still sits in the queue — once drained it's
        Claude's; we return False and the card keeps its delivered status.
        """
        with self._lock:
            candidates = [t for t in self._transcripts if t.utterance_id == utterance_id
                          and t.delivery_state not in ("sent", "accepted", "uncertain", "unknown")]
        cancelled_items = []
        for transcript in candidates:
            provider = self.conversations.providers.for_conversation(transcript.addressee)
            speech = Speech(transcript.utterance_id, transcript.addressee, transcript.text, transcript.timestamp)
            try:
                if provider is None or provider.cancel(speech):
                    cancelled_items.append(transcript)
            except Exception:
                self.update_utterance(utterance_id, delivery_detail="Cancellation could not be saved; speech remains pending")
                return False  # A cancellation that could not be persisted must not claim success.
        with self._lock:
            cancelled_items = [t for t in cancelled_items if t in self._transcripts]
            self._transcripts = [t for t in self._transcripts if t not in cancelled_items]
            if cancelled_items:
                self._add_event_locked("cancelled", f"utterance {utterance_id} recalled")
                self._update_utterance_locked(utterance_id, status="cancelled by you")
        return bool(cancelled_items)

    def drain(self, agent: str | None = None, touch: bool = True) -> list[Transcript]:
        with self._lock:
            # Register/refresh the caller. No agent given → single-agent
            # mode (everyone drains everything). touch=False for a listener
            # whose tab the user CLOSED: its poller may keep draining, but a
            # poll is not a reason to put the tab back on the strip.
            if agent is not None:
                if touch:
                    self._touch_agent_locked(agent)
                if self._active_agent is None and touch:
                    self._active_agent = agent  # first to register wins by default
                # Deliver by ADDRESSEE (stamped at recording start, #17).
                # Unstamped transcripts keep the old rule: active agent only.
                transcripts = [
                    t
                    for t in self._transcripts
                    if (t.addressee == agent or (not t.addressee and agent == self._active_agent))
                    and t.delivery_state not in ("sent", "accepted", "uncertain", "unknown")
                ]
                if not transcripts:
                    return []
                delivered_ids = {id(t) for t in transcripts}
                self._transcripts = [
                    t for t in self._transcripts if id(t) not in delivered_ids
                ]
            else:
                transcripts = [t for t in self._transcripts if t.delivery_state not in ("sent", "accepted", "uncertain", "unknown")]
                self._transcripts = [t for t in self._transcripts if t.delivery_state in ("sent", "accepted", "uncertain", "unknown")]
            if transcripts:
                self._add_event_locked(
                    "delivered", " ".join(t.text for t in transcripts)
                )
                recipient = self._agent_labels.get(agent or "", "") or "Claude"
                for transcript in transcripts:
                    self._update_utterance_locked(
                        transcript.utterance_id, status=f"delivered to {recipient}"
                    )
            return transcripts

    def _touch_agent_locked(self, name: str) -> None:
        # Heartbeat. An offline->online edge re-stamps activated_at, which
        # places the tab at the right end of the active group (#11).
        now = time.time()
        seen = self._agents.get(name)
        if seen is None or now - seen > AGENT_OFFLINE_AFTER_SECONDS:
            self._agent_activated[name] = now
        self._agents[name] = now

    @property
    def agents(self) -> dict:
        # Known agents are never pruned (#11): a silent agent is shown
        # offline by the dashboard, deleted only by an explicit dismiss.
        with self._lock:
            return dict(self._agents)

    @property
    def agent_labels(self) -> dict:
        # Legacy names can be paths, even without a transcript suffix.
        with self._lock:
            return {n: conversation_label(self._agent_labels.get(n, ""), n) for n in self._agents}

    @property
    def agents_meta(self) -> dict:
        """Tab data for the dashboard: online state and group ordering keys.

        online: heartbeat within AGENT_OFFLINE_AFTER_SECONDS (hysteresis: the
        threshold is generous, the return is instant on the next heartbeat).
        activated_at orders the active group (arrival order); offline_since
        orders the offline group (most recently ended first).
        """
        now = time.time()
        with self._lock:
            meta = {}
            for name, seen in self._agents.items():
                # Same two-signal rule as the delivery check: a session busy
                # thinking stops polling, and greying out its tab mid-turn is
                # the same lie as stamping its messages 'no listener'.
                online = self._agent_alive_locked(name, now)
                meta[name] = {
                    "label": conversation_label(self._agent_labels.get(name, ""), name),
                    "online": online,
                    "activated_at": self._agent_activated.get(name, seen),
                    "offline_since": None if online else seen + AGENT_OFFLINE_AFTER_SECONDS,
                    "manual_pos": self._agent_manual_pos.get(name),
                }
            return meta

    @property
    def queued_by_agent(self) -> dict:
        """Utterances WAITING TO BE HEARD per agent — the tab WAIT counter.

        Counts the agent→user direction (speech queued, synthesizing or
        parked unheard — everything except the clip playing right now),
        which is what "messages are waiting" means to the user watching
        the dashboard. The user→agent transcript queue is a different
        thing and deliberately not mixed in.
        """
        waiting_markers = ("queued", "synthesizing", "waiting", "unheard")
        with self._lock:
            counts: dict[str, int] = {}
            for utterance in self._utterances:
                if utterance.get("role") not in ("claude", "daemon"):
                    continue
                if utterance["id"] == self._playing_utterance_id:
                    continue
                status = str(utterance.get("status", ""))
                if any(marker in status for marker in waiting_markers):
                    key = str(utterance.get("agent") or "")
                    counts[key] = counts.get(key, 0) + 1
            return counts

    @property
    def latest_version(self) -> str | None:
        """Newest published release, refreshed by the background check."""
        with self._lock:
            return getattr(self, "_latest_version", None)

    def set_latest_version(self, version: str) -> None:
        with self._lock:
            self._latest_version = version

    @property
    def muted_agents(self) -> list:
        with self._lock:
            return sorted(self._muted_agents)

    def set_agent_muted(self, agent: str, muted: bool) -> list:
        with self._lock:
            if muted:
                self._muted_agents.add(agent)
            else:
                self._muted_agents.discard(agent)
            return sorted(self._muted_agents)

    def agent_muted(self, agent: str | None) -> bool:
        """Whether this agent's speech should park. Utterances without an
        agent belong to the active conversation — judge them by it."""
        with self._lock:
            key = agent or self._active_agent
            return key in self._muted_agents if key else False

    def note_agent_spoke(self, agent: str | None) -> None:
        """A speak/announce arrived — reset this agent's silence clock."""
        with self._lock:
            key = agent or self._active_agent
            if key:
                self._agent_last_spoke[key] = time.time()
                self._add_event_locked("nudge", f"clock reset — '{key}' spoke")

    @staticmethod
    def _nudge_threshold_seconds(talkative: int) -> float | None:
        """Silence budget for a talkative level; None = never nudge."""
        if talkative <= 0:
            return None
        anchors = TALKATIVE_NUDGE_ANCHORS
        if talkative <= anchors[0][0]:
            return anchors[0][1]
        for (lo_c, lo_s), (hi_c, hi_s) in zip(anchors, anchors[1:]):
            if talkative <= hi_c:
                fraction = (talkative - lo_c) / (hi_c - lo_c)
                return lo_s + (hi_s - lo_s) * fraction
        return anchors[-1][1]

    def nudge_clocks(self) -> dict[str, dict]:
        """Read-only snapshot of every known agent's silence clock, for the
        dashboard's live counter (#16). Pure: mutates nothing, so it is safe
        to call on every /status poll. Per agent: how long it's been silent,
        its talkative budget (None = nudging off), and whether its activity line
        is fresh enough to be nudge-eligible right now."""
        now = time.time()
        with self._lock:
            clocks: dict[str, dict] = {}
            for agent in self._agent_activated:
                character = self._characters.get(agent, self._characters[""])
                talkative = int(character.get("talkative", 50))
                started = self._agent_last_spoke.get(
                    agent, self._agent_activated.get(agent, now)
                )
                activity = self._activity.get(agent)
                fresh = bool(activity) and now - activity.get("at", 0) <= NUDGE_ACTIVITY_FRESH_SECONDS
                clocks[agent] = {
                    "silence": round(now - started, 1),
                    "threshold": self._nudge_threshold_seconds(talkative),
                    "fresh": fresh,
                }
            return clocks

    def pop_due_nudge(self, agent: str) -> str | None:
        """A [SYSTEM] narration reminder, when this agent has earned one.

        Fires only while the agent is ACTIVELY working (fresh activity
        line), after a silence longer than its talkative budget, and at most
        once per silence stretch. The model has no sense of elapsed time —
        this is the daemon lending it a clock (#16).
        """
        now = time.time()
        with self._lock:
            character = self._characters.get(agent, self._characters[""])
            talkative = int(character.get("talkative", 50))
            verbosity = int(character.get("verbosity", 50))
            threshold = self._nudge_threshold_seconds(talkative)
            if threshold is None:
                return None
            silence_started = self._agent_last_spoke.get(
                agent, self._agent_activated.get(agent, now)
            )
            silence = now - silence_started
            # Below budget: the common every-poll case. Stay silent in the
            # event log — only decisions AT/PAST the budget are worth logging.
            if silence < threshold:
                return None
            # Past budget from here: log the outcome exactly once per silence
            # stretch (dedup on the same guard the nudge itself uses), so the
            # /logs view shows WHY a due nudge did or didn't fire without the
            # 0.5s stop-hook poll flooding it.
            already_nudged = self._agent_last_nudge.get(agent, 0) > silence_started
            activity = self._activity.get(agent)
            is_fresh = bool(activity) and now - activity.get("at", 0) <= NUDGE_ACTIVITY_FRESH_SECONDS
            if not is_fresh:
                # Log the idle-skip once per stretch, but do NOT spend the
                # nudge budget — resuming work later in this stretch must
                # still fire a real nudge.
                if self._agent_last_idle_log.get(agent, 0) <= silence_started:
                    self._agent_last_idle_log[agent] = now
                    self._add_event_locked(
                        "nudge",
                        f"skipped — idle {round(silence)}s (activity stale/absent), "
                        f"waiting on user",
                    )
                return None  # idle or between turns — never nag a waiting agent
            if already_nudged:
                return None  # this stretch was already nudged once
            self._agent_last_nudge[agent] = now
            minutes = max(1, round(silence / 60))
            self._add_event_locked(
                "nudge",
                f"SENT — silent {round(silence)}s ≥ {round(threshold)}s "
                f"budget (talkative {talkative})",
            )
            # talkative decides WHEN to speak up; verbosity decides HOW LONG the
            # update gets to be — a 10-minute stretch may deserve more than
            # one line when the user runs high verbosity.
            return (
                f"[SYSTEM] You have been working silently for ~{minutes} min and the "
                f"user's talkative setting is {talkative}/100 — give a spoken progress "
                f"update (announce), sized to the user's verbosity setting "
                f"({verbosity}/100), then continue working."
            )

    def reorder_agents(self, order: list[str]) -> None:
        """Pin a user-chosen tab order (drag & drop). The dashboard sends the
        full resulting order of ONE group; unknown names are ignored."""
        with self._lock:
            for position, name in enumerate(order):
                if name in self._agents:
                    self._agent_manual_pos[name] = position

    def dismiss_agent(self, name: str, force: bool = False) -> bool:
        """Drop an agent's tab. Never the active one (that would silently
        reroute the user's speech). Without `force`, the legacy heartbeat
        guard applies; the registry-aware /dismiss-agent passes force=True
        because liveness is the registry's call, not a heartbeat's."""
        with self._lock:
            seen = self._agents.get(name)
            if seen is None:
                return False
            if name == self._active_agent:
                if not force:
                    return False
                self._active_agent = None  # caller has already handed the mic on
            if not force and time.time() - seen <= AGENT_OFFLINE_AFTER_SECONDS:
                return False
            del self._agents[name]
            self._agent_labels.pop(name, None)
            self._agent_activated.pop(name, None)
            self._agent_manual_pos.pop(name, None)
            self._muted_agents.discard(name)
            self._agent_last_spoke.pop(name, None)
            self._agent_last_nudge.pop(name, None)
            self._agent_last_idle_log.pop(name, None)
            self._activity.pop(name, None)
            return True

    @property
    def active_agent(self) -> str | None:
        with self._lock:
            return self._active_agent

    def register_agent(self, name: str, label: str = "") -> None:
        # THE LAST LINE OF DEFENCE (#107). Whatever a producer sends, a tab
        # is never keyed by a transcript path: the path is not identity, it
        # renders as the tab's label when there is no title, and it puts an
        # absolute filesystem path on screen. Fixing the adapter stopped the
        # main producer; canonicalising here stops every other one, present
        # or future, without having to find them first.
        name = canonical_identity(name)
        with self._lock:
            self._touch_agent_locked(name)
            if label:
                label = conversation_label(label, name)
                # A fallback label (the shortened agent id) must not evict a
                # real title: hooks re-register on every call, and the ones
                # that cannot read the transcript would otherwise keep
                # reverting the tab to the bare hash.
                is_fallback = label in (name, name[:8], UNNAMED_CONVERSATION)
                if not (is_fallback and self._agent_labels.get(name)):
                    self._agent_labels[name] = label
            if self._active_agent is None:
                self._active_agent = name

    def set_active_agent(self, name: str) -> str | None:
        """Hand the mic to `name`. Returns who actually holds it.

        A tab the user can SEE must be selectable. Requiring membership in
        `_agents` silently dropped the request for an agent that had a tab
        but no live heartbeat, so the click did nothing while the dashboard
        happily showed it as selected - and the mic kept feeding whoever was
        active before. Any agent we still know a tab for is fair game.
        """
        with self._lock:
            if name in self._agents:
                self._active_agent = name
            elif name in self._agent_labels:
                self._agents.setdefault(name, time.time())
                self._active_agent = name
            return self._active_agent

    def clear_active_agent(self) -> None:
        """No conversation receives the mic (the last tab was closed)."""
        with self._lock:
            self._active_agent = None

    def restore_active_agent(self, name: str) -> None:
        """Carry the user's chosen agent across a daemon restart.

        Registered as a (possibly not-yet-returned) agent so its tab stays
        visible and later registrations can't win the empty-slate race that
        used to hand the mic to whichever agent polled first after boot.
        """
        with self._lock:
            self._agents.setdefault(name, time.time())
            self._active_agent = name

    @property
    def queued_count(self) -> int:
        with self._lock:
            return sum(t.delivery_state in ("queued", "unavailable") for t in self._transcripts)

    @property
    def last_transcript_at(self) -> float:
        with self._lock:
            return self._last_transcript_at

    def set_latency(self, kind: str, milliseconds: float) -> None:
        with self._lock:
            self._latency_ms[kind] = int(milliseconds)

    @property
    def latency_ms(self) -> dict:
        with self._lock:
            return dict(self._latency_ms)

    def _agent_alive_locked(self, agent: str, now: float) -> bool:
        """Is anyone home on this tab? Call with the lock held.

        Two independent signs of life, because the obvious one lies. The
        drain heartbeat only ticks when the session POLLS, and a session
        that is thinking or running a long tool does not poll - so a busy
        agent looked dead after 30s and the user's message was stamped
        'no listener' while the agent was very much alive and picked it up
        moments later. Live activity (the tool/thinking one-liner the hooks
        push) proves the process is running even while it is not polling.
        """
        if self.conversations.providers.for_conversation(agent) is not None:
            return self.conversations.status(agent) in ("live", "idle")
        seen = self._agents.get(agent)
        if seen is not None and now - seen <= AGENT_OFFLINE_AFTER_SECONDS:
            return True
        activity = self._activity.get(agent)
        return bool(
            activity
            and activity.get("text")
            and now - activity.get("at", 0.0) <= AGENT_OFFLINE_AFTER_SECONDS
        )

    def set_activity(self, agent: str, text: str) -> None:
        """What an agent is doing right now (one line from the hooks)."""
        with self._lock:
            if text:
                self._activity[agent] = {"text": text, "at": time.time()}
            else:
                self._activity.pop(agent, None)  # turn ended — idle

    @property
    def activity(self) -> dict:
        with self._lock:
            return {agent: dict(entry) for agent, entry in self._activity.items()}

    @property
    def playing_utterance_id(self) -> int:
        with self._lock:
            return self._playing_utterance_id

    def interrupt_playing_as_unheard(
        self, reason: str, agent: str | None = None, label: str = "unheard"
    ) -> int:
        """Mute pressed mid-clip: park the playing utterance as UNHEARD.

        The clip was cut short, so it must not read "played" — catch-up
        should replay it in full. With `agent` given, only fires when the
        playing clip belongs to that conversation (agent-less clips count
        as the active one). Returns the interrupted id, 0 if none.
        """
        with self._lock:
            utterance_id = self._playing_utterance_id
            if not utterance_id:
                return 0
            for utterance in self._utterances:
                if utterance["id"] != utterance_id:
                    continue
                owner = utterance.get("agent") or self._active_agent
                if agent is not None and owner != agent:
                    return 0
                # label: "unheard" = may still be worth hearing (counts for
                # catch-up); "skipped" = the user dismissed it deliberately
                # (the stop button) - final, never counted again.
                utterance["status"] = f"{label} — {reason}"
                utterance["updated_at"] = time.time()
                break
            self._interrupted[utterance_id] = f"{label} — {reason}"
            self._playing_utterance_id = 0
            return utterance_id

    def complete_playback(self, utterance_id: int, duration_s: float) -> bool:
        """Settle only the still-owned playback; an earlier interruption wins."""
        with self._lock:
            if not utterance_id or self._playing_utterance_id != utterance_id:
                return False
            self._playing_utterance_id = 0
            for utterance in self._utterances:
                if utterance["id"] == utterance_id:
                    utterance.update(status="played", duration_s=duration_s,
                                     updated_at=time.time())
                    break
            return True

    def playing_clip(self) -> dict | None:
        """A copy of the card on the speakers right now, or None."""
        with self._lock:
            utterance_id = self._playing_utterance_id
            if not utterance_id:
                return None
            for utterance in self._utterances:
                if utterance["id"] == utterance_id:
                    return dict(utterance)
            return None

    def consume_interrupted(self, utterance_id: int) -> str | None:
        """Was this clip cut short by the user? Returns its final status once."""
        with self._lock:
            return self._interrupted.pop(utterance_id, None)

    def skip_unheard(self, agent: str | None = None) -> int:
        """Skip-all: settle every parked UNHEARD card without playing it.

        The user's explicit "I don't want to hear these" - the words stay
        readable in the log, but the catch-up counter empties. Only the
        given conversation (default: the active one) is touched. Returns
        how many cards were settled.
        """
        with self._lock:
            target = agent or self._active_agent
            skipped = 0
            for utterance in self._utterances:
                if utterance.get("role") not in ("claude", "daemon"):
                    continue
                owner = utterance.get("agent") or self._active_agent
                if owner != target:
                    continue
                if "unheard" in str(utterance.get("status", "")):
                    utterance["status"] = "skipped — dismissed by you"
                    utterance["updated_at"] = time.time()
                    skipped += 1
            # History persistence is the daemon's periodic save - the
            # status flip above is picked up on its next tick.
            return skipped

    def utterance_is_unheard(self, utterance_id: int) -> bool:
        with self._lock:
            for utterance in self._utterances:
                if utterance["id"] == utterance_id:
                    return "unheard" in str(utterance.get("status", ""))
            return False

    def set_playing_utterance_id(self, utterance_id: int) -> None:
        with self._lock:
            self._playing_utterance_id = utterance_id

    @property
    def mic_level(self) -> float:
        with self._lock:
            return self._mic_level

    def set_mic_level(self, level: float) -> None:
        with self._lock:
            self._mic_level = max(0.0, min(1.0, float(level)))

    @property
    def recording(self) -> bool:
        with self._lock:
            return self._recording

    def set_recording(self, recording: bool) -> None:
        with self._lock:
            if self._recording and not recording:
                self._last_recording_end = time.monotonic()
            self._recording = recording
            self._turn_cond.notify_all()

    def user_turn_status(self, grace_s: float = 0.0) -> dict:
        """One locked snapshot for playback arbitration and its diagnostics."""
        with self._lock:
            return self._user_turn_status_locked(grace_s)

    def _user_turn_status_locked(self, grace_s: float) -> dict:
        now = time.monotonic()
        lease_end = self._ptt_last_hold + PTT_LEASE_SECONDS
        lease_remaining = lease_end - now if self._detection_mode == "ptt" else 0.0
        turn_end = self._last_recording_end
        if self._detection_mode == "ptt":
            turn_end = max(turn_end, self._last_ptt_end, lease_end)
        wait_s = user_turn_wait_seconds(
            self._recording, lease_remaining, now - turn_end, grace_s,
        )
        return {
            "decision": "play" if wait_s == 0 else "hold",
            "recording": self._recording,
            "paused": self._paused,
            "user_muted": self._user_muted,
            "ptt_held": lease_remaining > 0,
            "ms_since_recording_end": (
                round((now - self._last_recording_end) * 1000)
                if self._last_recording_end != float("-inf") else None
            ),
            "wait_s": wait_s,
        }

    def wait_for_user_silence(
        self, grace_s: float = 0.0, *, on_ready: Callable[[], int] | None = None,
        claim_playback: bool = False,
    ) -> int | None:
        """Wait for capture completion AND PTT release, then conversational grace.

        Echo pause is not an end-of-turn signal. The capture loop owns the
        recording flag, including finalization after an explicit mic mute.
        Lease expiry uses a timed wake so a disconnected PTT client cannot
        block the speaker forever; renewals and release notify immediately.
        """
        with self._turn_cond:
            while True:
                wait_s = self._user_turn_status_locked(grace_s)["wait_s"]
                if wait_s == 0:
                    # Capture the playback cancellation token before a new
                    # PTT lease can slip between the decision and handoff.
                    generation = on_ready() if on_ready is not None else None
                    if claim_playback:
                        # Enable capture-loop barge-in at the same handoff,
                        # including hotkeys that only renew the PTT lease.
                        self._paused = True
                    return generation
                self._turn_cond.wait(timeout=wait_s)

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused or self._user_muted

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._paused = paused
            self._turn_cond.notify_all()

    @property
    def claude_speaking(self) -> bool:
        with self._lock:
            return self._claude_speaking

    @property
    def speaking_agents(self) -> list:
        with self._lock:
            return sorted(self._speaking_agents)

    def set_claude_speaking(self, speaking: bool, agent: str | None = None) -> None:
        with self._lock:
            self._claude_speaking = speaking
            if agent:
                if speaking:
                    self._speaking_agents.add(agent)
                else:
                    self._speaking_agents.discard(agent)

    @property
    def voice_muted(self) -> bool:
        with self._lock:
            return self._voice_muted

    def set_voice_muted(self, muted: bool) -> None:
        with self._lock:
            self._voice_muted = muted

    @property
    def user_muted(self) -> bool:
        with self._lock:
            return self._user_muted

    def set_user_muted(self, muted: bool) -> None:
        with self._lock:
            self._user_muted = muted
            self._turn_cond.notify_all()
